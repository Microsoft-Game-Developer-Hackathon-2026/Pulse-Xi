import pytest

from app.agent_tools import ToolContext, ToolFailure, execute_tool
from app.evidence import insights_for, overlays_for
from app.simulator import generate


def context(fixture="late-winner"):
    match, events = generate(fixture)
    insight = next(item for item in insights_for(match, events) if item.category == "goal")
    trace = {"tool_calls": []}
    return match, events, insight, ToolContext(match, events, insight, trace)


def test_metrics_tool_is_deterministic_and_uses_exclusive_start():
    match, events, insight, ctx = context()
    seconds = min(300, insight.match_second)
    result = execute_tool(ctx, "TacticalAnalyst", "get_match_metrics", {
        "match_id": match.match_id,
        "at_second": insight.match_second,
        "window_start": 0,
        "window_seconds": seconds,
    })

    assert result["schema_version"] == "pulse-xi-agent-tools/1"
    assert result["formula_version"] == "pulse-xi-event-metrics/1"
    assert result["window"] == {"start": 0, "end": seconds, "semantics": "(start,end]"}
    assert result["source_event_ids"] == [
        event.event_id for event in events if 0 < event.match_second <= seconds
    ]
    assert len(result["output_hash"]) == 64


def test_tool_inputs_reject_extra_fields_future_cutoffs_and_cross_match_ids():
    match, _, insight, ctx = context()
    base = {"match_id": match.match_id, "at_second": insight.match_second,
            "window_start": 0, "window_seconds": min(60, insight.match_second)}

    with pytest.raises(ToolFailure, match="invalid_tool_arguments"):
        execute_tool(ctx, "TacticalAnalyst", "get_match_metrics", {**base, "url": "https://example.com"})
    with pytest.raises(ToolFailure, match="match_mismatch"):
        execute_tool(ctx, "TacticalAnalyst", "get_match_metrics", {**base, "match_id": "other-match"})
    with pytest.raises(ToolFailure, match="future_cutoff"):
        execute_tool(ctx, "TacticalAnalyst", "get_match_metrics", {**base, "at_second": insight.match_second + 1})


def test_role_allowlist_and_call_limit_are_enforced():
    match, _, insight, ctx = context()
    request = {"match_id": match.match_id, "at_second": insight.match_second,
               "window_start": 0, "window_seconds": min(60, insight.match_second)}
    with pytest.raises(ToolFailure, match="tool_not_allowed"):
        execute_tool(ctx, "StoryEditor", "get_match_metrics", request)

    for _ in range(ctx.max_calls):
        execute_tool(ctx, "TacticalAnalyst", "get_match_metrics", request)
    with pytest.raises(ToolFailure, match="tool_call_limit"):
        execute_tool(ctx, "TacticalAnalyst", "get_match_metrics", request)


def test_evidence_tool_returns_only_verified_insight_sources():
    match, events, insight, ctx = context()
    result = execute_tool(ctx, "StoryEditor", "get_evidence_for_insight", {
        "match_id": match.match_id, "insight_id": insight.insight_id,
        "at_second": insight.match_second,
    })

    assert result["verification_status"] == "verified"
    assert result["insight"]["insight_id"] == insight.insight_id
    assert result["source_event_ids"] == insight.supporting_event_ids
    assert all(event_id in {event.event_id for event in events} for event_id in result["source_event_ids"])


def test_broadcast_cue_tool_only_returns_a_verified_draft():
    match, _, insight, ctx = context()
    cue = next(item for item in overlays_for(match, ctx.events, insight.match_second)
               if item.insight_id == insight.insight_id)
    result = execute_tool(ctx, "BroadcastDirector", "prepare_broadcast_cue", {
        "match_id": match.match_id, "insight_id": insight.insight_id,
        "at_second": insight.match_second, "target_time": cue.start_match_second,
        "template": cue.visual_template,
    })

    assert result["verification_status"] == "draft_only"
    assert result["approval_state"] == "draft_only"
    assert result["publishing"] is False
    assert result["cue"]["evidence_event_ids"] == insight.supporting_event_ids
