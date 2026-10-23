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


def test_preflight_rejections_are_visible_and_bounded():
    _, _, _, ctx = context()
    for _ in range(50):
        with pytest.raises(ToolFailure, match="tool_not_allowed"):
            execute_tool(ctx, "StoryEditor", "get_match_metrics", {})
    assert len(ctx.trace["tool_calls"]) == 1
    row = ctx.trace["tool_calls"][0]
    assert row["status"] == "rejected"
    assert row["error_code"] == "tool_not_allowed"
    assert row["rejected_count"] == 50
    assert ctx.call_count == 0


def test_unexpected_tool_failure_is_not_recorded_as_completed(monkeypatch):
    from app import agent_tools
    match, _, insight, ctx = context()

    def fail(*args):
        raise RuntimeError("SENTINEL_SECRET")

    monkeypatch.setattr(agent_tools, "metrics_at", fail)
    with pytest.raises(RuntimeError):
        execute_tool(ctx, "TacticalAnalyst", "get_match_metrics", {
            "match_id": match.match_id, "at_second": insight.match_second,
            "window_start": 0, "window_seconds": min(60, insight.match_second)})
    row = ctx.trace["tool_calls"][-1]
    assert row["status"] == "failed" and row["error_code"] == "RuntimeError"
    assert "SENTINEL_SECRET" not in str(ctx.trace)


@pytest.mark.parametrize("start,seconds,expected", [(0, 10, [10]), (10, 10, [20]),
                                                   (0, 20, [10, 20]), (21, 1, [])])
def test_metric_boundary_ids_and_counts_agree(start, seconds, expected):
    match, events, insight, ctx = context()
    sample = next(e for e in events if e.event_type.value == "pass")
    ctx.events = [sample.model_copy(update={"match_second": t, "event_id": f"boundary-{t}",
                                          "sequence": n}) for n, t in enumerate((0, 10, 20, 21))]
    result = execute_tool(ctx, "TacticalAnalyst", "get_match_metrics", {
        "match_id": match.match_id, "at_second": insight.match_second,
        "window_start": start, "window_seconds": seconds})
    assert result["source_event_ids"] == [f"boundary-{t}" for t in expected]
    assert result["metrics"]["home"]["passes"] + result["metrics"]["away"]["passes"] == len(expected)


@pytest.mark.parametrize("change,code", [({"window_start": -1}, "invalid_tool_arguments"),
                                        ({"window_seconds": 0}, "invalid_tool_arguments"),
                                        ({"window_start": 5399, "window_seconds": 2}, "invalid_window"),
                                        ({"at_second": 5401}, "invalid_tool_arguments")])
def test_metric_bounds_fail_closed(change, code):
    match, _, insight, ctx = context()
    request = {"match_id": match.match_id, "at_second": insight.match_second,
               "window_start": 0, "window_seconds": 10, **change}
    with pytest.raises(ToolFailure, match=code):
        execute_tool(ctx, "TacticalAnalyst", "get_match_metrics", request)
    assert ctx.trace["tool_calls"][-1]["status"] == "rejected"


def test_parallel_tool_calls_cannot_overspend_the_execution_budget():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    import time

    class YieldingContext(ToolContext):
        def __getattribute__(self, name):
            value = super().__getattribute__(name)
            if name == "call_count":
                time.sleep(0.005)  # force a legal scheduler switch between read/check/update
            return value

    match, events, insight, _ = context()
    ctx = YieldingContext(match, events, insight, {"tool_calls": []}, max_calls=1)
    gate = Barrier(2, timeout=3)

    def invoke(_):
        gate.wait()
        try:
            execute_tool(ctx, "TacticalAnalyst", "get_match_metrics", {
                "match_id": match.match_id, "at_second": insight.match_second,
                "window_start": 0, "window_seconds": 10})
            return True
        except ToolFailure as error:
            assert error.code == "tool_call_limit"
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(invoke, range(2)))
    assert outcomes.count(True) == 1
    assert ctx.call_count == 1
