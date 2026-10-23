"""Provider doubles only: these tests must never authenticate or make a request."""
import asyncio
import json
import sys
from types import SimpleNamespace

import pytest

from app import agents
from app.evidence import insights_for
from app.simulator import generate


@pytest.fixture
def provider(monkeypatch):
    match, events = generate("late-winner")
    insight = next(i for i in insights_for(match, events) if i.category == "goal")
    packet = {"headline": "A decisive moment", "commentary": "An opportunity to reflect.",
              "event_ids": insight.supporting_event_ids}
    state = {"packet": packet, "raw": None, "error": None, "author": "StoryEditor", "called": []}

    class Client:
        def __init__(self, **kwargs):
            pass

        def as_agent(self, **kwargs):
            return SimpleNamespace(**kwargs)

    class Builder:
        def __init__(self, participants):
            self.participants = participants

        def build(self):
            return self

        async def run(self, prompt):
            for participant in self.participants:
                context = SimpleNamespace(messages=[SimpleNamespace(text=prompt, role="user")],
                                          result=None, stream=False)

                async def call_next():
                    state["called"].append(participant.name)
                    if participant.name == "StoryEditor" and state["error"]:
                        raise state["error"]
                    text = (state["raw"] or json.dumps(state["packet"])) if participant.name == "StoryEditor" else "analysis"
                    context.result = SimpleNamespace(messages=[SimpleNamespace(
                        text=text, role="assistant", author_name=participant.name)],
                        usage_details={"input_token_count": 2, "output_token_count": 3})

                middleware = getattr(participant, "middleware", [])
                if middleware:
                    await middleware[0].process(context, call_next)
                else:
                    await call_next()
            context.result.messages[-1].author_name = state["author"]
            return SimpleNamespace(get_outputs=lambda: [context.result])

    monkeypatch.setitem(sys.modules, "agent_framework", SimpleNamespace(AgentMiddleware=object))
    monkeypatch.setitem(sys.modules, "agent_framework.foundry", SimpleNamespace(FoundryChatClient=Client))
    monkeypatch.setitem(sys.modules, "agent_framework.orchestrations", SimpleNamespace(SequentialBuilder=Builder))
    monkeypatch.setitem(sys.modules, "azure.identity", SimpleNamespace(AzureCliCredential=lambda: object()))
    monkeypatch.setattr(agents, "framework_tools", lambda *args: [])
    monkeypatch.setattr(agents, "configured", lambda: True)
    monkeypatch.setattr(agents, "TRACES", [])
    monkeypatch.setenv("FOUNDRY_PROJECT_ENDPOINT", "https://offline.invalid")
    monkeypatch.setenv("FOUNDRY_MODEL", "offline-model")
    return match, events, insight, state


def test_observed_stage_order_hashes_and_all_provider_usage(provider):
    match, events, insight, state = provider
    result = asyncio.run(agents.run_specialists(match, events, insight))
    assert result["status"] == "approved_model_opinion"
    trace = agents.TRACES[-1]
    assert state["called"] == ["TacticalAnalyst", "StoryEditor"]
    for stage in trace["stages"][:2]:
        assert stage["status"] == "completed"
        assert len(stage["input_hash"]) == len(stage["output_hash"]) == 64
        assert stage["duration_ms"] >= 0
    assert trace["usage_details"] == {"input_token_count": 4, "output_token_count": 6}
    assert result["broadcast_cue_draft"]["approval_state"] == "draft_only"
    assert result["broadcast_cue_draft"]["publishing"] is False


def test_editor_failure_preserves_actual_completed_and_failed_stages(provider):
    match, events, insight, state = provider
    state["error"] = RuntimeError("SENTINEL_SECRET https://private.invalid")
    result = asyncio.run(agents.run_specialists(match, events, insight))
    trace = agents.TRACES[-1]
    assert result["status"] == "deterministic_fallback"
    assert [(s["role"], s["status"]) for s in trace["stages"][:2]] == [
        ("TacticalAnalyst", "completed"), ("StoryEditor", "failed")]
    assert trace["provider_status"] == "error"
    assert "SENTINEL_SECRET" not in json.dumps(trace)


def test_cancelled_workflow_cannot_leave_a_running_trace(provider):
    match, events, insight, state = provider
    state["error"] = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(agents.run_specialists(match, events, insight))
    assert agents.TRACES[-1]["status"] == "cancelled"
    assert agents.TRACES[-1]["stages"][1]["status"] == "cancelled"


def test_accepted_output_uses_only_cutoff_scoped_deterministic_consumers(provider, monkeypatch):
    match, events, insight, _ = provider
    calls = []
    for name in ("overlays_for", "recap_for"):
        original = getattr(agents, name)

        def scoped(*args, _name=name, _original=original, **kwargs):
            calls.append((_name, kwargs.get("at_second")))
            return _original(*args, **kwargs)

        monkeypatch.setattr(agents, name, scoped)
    assert asyncio.run(agents.run_specialists(match, events, insight))["status"] == "approved_model_opinion"
    assert calls and all(cutoff == insight.match_second for _, cutoff in calls)


def test_final_output_must_belong_to_story_editor(provider):
    match, events, insight, state = provider
    state["author"] = "TacticalAnalyst"
    result = asyncio.run(agents.run_specialists(match, events, insight))
    assert result["status"] == "deterministic_fallback"
    assert agents.TRACES[-1]["provider_status"] == "error"


def test_rejected_editor_output_never_reaches_model_acceptance(provider):
    match, events, insight, state = provider
    state["packet"]["event_ids"] = ["fabricated-event"]
    result = asyncio.run(agents.run_specialists(match, events, insight))
    trace = agents.TRACES[-1]
    assert result["status"] == "deterministic_fallback"
    assert trace["audit_verdict"] == "rejected_model_output"
    assert not any(s["role"] == "BroadcastDirector" for s in trace["stages"])


def test_ambiguous_editor_json_is_rejected(provider):
    match, events, insight, state = provider
    state["raw"] = json.dumps(state["packet"]).replace(
        '"headline":', '"headline":"overwritten copy","headline":', 1)
    assert asyncio.run(agents.run_specialists(match, events, insight))["status"] == "deterministic_fallback"


def test_unverified_source_never_invokes_provider_or_returns_verified_fallback(provider):
    match, events, insight, state = provider
    invalid = insight.model_copy(deep=True)
    invalid.factual_claims[0].value += 1
    with pytest.raises(ValueError, match="verified source"):
        asyncio.run(agents.run_specialists(match, events, invalid))
    assert not state["called"]
    assert agents.TRACES[-1]["provider_status"] == "not_invoked"


@pytest.mark.parametrize("error", [TimeoutError("SENTINEL_SECRET"),
                                    type("RateLimitError", (RuntimeError,), {"status_code": 429})("SENTINEL_SECRET")])
def test_provider_timeout_and_rate_limit_remain_visible_without_raw_errors(provider, error):
    match, events, insight, state = provider
    state["error"] = error
    assert asyncio.run(agents.run_specialists(match, events, insight))["status"] == "deterministic_fallback"
    trace = agents.TRACES[-1]
    assert trace["error_code"] == type(error).__name__
    if getattr(error, "status_code", None):
        assert trace["http_status"] == 429
    assert "SENTINEL_SECRET" not in json.dumps(trace)
