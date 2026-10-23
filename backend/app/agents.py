"""Optional, explicitly invoked Microsoft Agent Framework + Foundry workflow.

No hosted call is made during startup, ingestion, tests, or deterministic replay.
"""
import asyncio
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .evidence import overlays_for, recap_for, verify
from .models import Insight, Match, MatchEvent
from .agent_tools import ToolContext, execute_tool, framework_tools, UNAVAILABLE_CAPABILITIES

TRACES: list[dict] = []


def configured() -> bool:
    return (os.getenv("PULSE_ENABLE_FOUNDRY") == "true"
            and bool(os.getenv("FOUNDRY_PROJECT_ENDPOINT"))
            and bool(os.getenv("FOUNDRY_MODEL")))


def _safe_usage_details(outputs: list) -> dict | None:
    """Aggregate only documented integer token counters; never serialize provider objects."""
    fields = ("input_token_count", "output_token_count", "total_token_count")
    totals: dict[str, int] = {}
    for output in outputs:
        usage = getattr(output, "usage_details", None)
        if usage is None:
            continue
        for field in fields:
            value = usage.get(field) if isinstance(usage, dict) else getattr(usage, field, None)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                totals[field] = totals.get(field, 0) + value
    return totals or None


def evidence_packet_hash(match: Match, events: list[MatchEvent], insight: Insight) -> str:
    packet = {"match_id": match.match_id, "insight": insight.model_dump(mode="json"),
              "source_events": [e.model_dump(mode="json", by_alias=True) for e in events
                                if e.event_id in insight.supporting_event_ids]}
    return hashlib.sha256(json.dumps(packet, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def _source_revision() -> str | None:
    try:
        value = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                        cwd=Path(__file__).resolve().parents[2], text=True,
                                        timeout=2, stderr=subprocess.DEVNULL).strip()
        return value if re.fullmatch(r"[0-9a-f]{40}", value) else None
    except (OSError, subprocess.SubprocessError):
        return None


def _source_dirty() -> bool | None:
    try:
        return bool(subprocess.check_output(["git", "status", "--porcelain"],
                                            cwd=Path(__file__).resolve().parents[2], text=True,
                                            timeout=2, stderr=subprocess.DEVNULL).strip())
    except (OSError, subprocess.SubprocessError):
        return None


def _message_hash(messages) -> str:
    texts = [{"role": str(getattr(m, "role", "")), "text": getattr(m, "text", "")}
             for m in messages]
    return hashlib.sha256(json.dumps(texts, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def _http_status(error: Exception) -> int | None:
    value = getattr(error, "status_code", None)
    if value is None:
        value = getattr(getattr(error, "response", None), "status_code", None)
    return value if isinstance(value, int) and not isinstance(value, bool) and 100 <= value <= 599 else None


def _stage_middleware(trace: dict, role: str):
    """Observe actual non-streaming agent invocations through the pinned SDK."""
    from agent_framework import AgentMiddleware

    class ObservedStage(AgentMiddleware):
        async def process(self, context, call_next):
            started = time.perf_counter()
            stage = {"role": role, "kind": "foundry_agent", "status": "running",
                     "hash_scope": "message-role-and-text/1", "input_hash": _message_hash(context.messages)}
            trace["stages"].append(stage)
            try:
                if context.stream:
                    raise ValueError("Workflow tracing requires non-streaming agent execution")
                await call_next()
                if context.result is None or not context.result.messages:
                    raise ValueError("Agent returned no messages")
                stage["output_hash"] = _message_hash(context.result.messages)
                stage["status"] = "completed"
                trace["provider_response_received"] = True
                usage = _safe_usage_details([context.result])
                if usage:
                    totals = trace["usage_details"] or {}
                    for key, value in usage.items():
                        totals[key] = totals.get(key, 0) + value
                    trace["usage_details"] = totals
            except asyncio.CancelledError:
                stage.update(status="cancelled", error_code="CancelledError")
                raise
            except Exception as error:
                stage.update(status="failed", error_code=type(error).__name__)
                if (status := _http_status(error)) is not None:
                    stage["http_status"] = status
                raise
            finally:
                stage["duration_ms"] = round((time.perf_counter() - started) * 1000, 1)
                stage["tool_names"] = sorted({c["tool_name"] for c in trace["tool_calls"]
                                              if c["role"] == role})

    return ObservedStage()


def _parse_model_packet(raw: str) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate model output key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("Nonfinite model output")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)


def audit_model_packet(packet: dict, insight: Insight, match: Match, events: list[MatchEvent]) -> bool:
    """Gate model copy as an opinion and preserve authoritative event facts."""
    if not verify(insight, match, events):
        return False
    if not isinstance(packet, dict) or set(packet) != {"headline", "commentary", "event_ids"}:
        return False
    if not isinstance(packet["headline"], str) or not isinstance(packet["commentary"], str):
        return False
    if (not isinstance(packet["event_ids"], list) or not packet["event_ids"]
            or len(packet["event_ids"]) > 20
            or any(not isinstance(event_id, str) for event_id in packet["event_ids"])):
        return False
    if len(set(packet["event_ids"])) != len(packet["event_ids"]):
        return False
    if not set(packet["event_ids"]).issubset(insight.supporting_event_ids):
        return False
    if len(packet["headline"]) > 120 or len(packet["commentary"]) > 500:
        return False
    # Numbers are only delivered from the deterministic factual packet, never from model prose.
    if re.search(r"\d", packet["headline"] + packet["commentary"]):
        return False
    return True


def _new_trace(match: Match, insight: Insight) -> dict:
    """Create the versioned trace envelope before crossing the provider boundary."""
    run_id = str(uuid4())
    return {
        "schema_version": "pulse-xi-workflow-trace/1",
        "run_id": run_id,
        "trace_id": f"trace-{run_id}",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": _source_revision(),
        "source_dirty": _source_dirty(),
        "match_id": match.match_id,
        "insight_id": insight.insight_id,
        "provider": "microsoft_foundry_agent_framework",
        "provider_status": "authenticated_inference_pending",
        "provider_response_received": False,
        "model": os.getenv("FOUNDRY_MODEL"),
        "status": "running",
        "max_model_attempts": 1,
        "max_workflow_attempts": 1,
        "max_tool_calls": 8,
        "unavailable_capabilities": UNAVAILABLE_CAPABILITIES,
        "tool_calls": [],
        "stages": [],
        "usage_details": None,
    }


async def run_specialists(match: Match, events: list[MatchEvent], insight: Insight) -> dict:
    if not configured():
        raise RuntimeError("Foundry is not enabled/configured")
    # Lazy imports keep local deterministic operation dependency-free.
    started = time.perf_counter()
    trace = _new_trace(match, insight)
    trace["evidence_packet_sha256"] = evidence_packet_hash(match, events, insight)
    TRACES.append(trace)
    TRACES[:] = TRACES[-50:]
    if not verify(insight, match, events):
        trace.update(status="rejected", provider_status="not_invoked",
                     audit_verdict="rejected_source", error_code="UnverifiedSource",
                     elapsed_ms=round((time.perf_counter() - started) * 1000, 1))
        raise ValueError("A verified source insight is required before provider invocation")
    ctx = ToolContext(match=match, events=events, insight=insight, trace=trace)
    try:
        from agent_framework.foundry import FoundryChatClient
        from agent_framework.orchestrations import SequentialBuilder
        from azure.identity import AzureCliCredential

        client = FoundryChatClient(project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
                                   model=os.environ["FOUNDRY_MODEL"], credential=AzureCliCredential())
        analyst = client.as_agent(name="TacticalAnalyst", instructions=(
            "Analyze only supplied synthetic evidence. Before making an observation, use get_match_metrics, "
            "find_key_moments, and get_evidence_for_insight as needed. Use only the supplied match and the "
            "insight's at_second cutoff. Never invent a metric, player action, cause, or event ID. Avoid digits in prose."),
            tools=framework_tools(ctx, "TacticalAnalyst"),
            middleware=[_stage_middleware(trace, "TacticalAnalyst")])
        editor = client.as_agent(name="StoryEditor", instructions=(
            "Use get_evidence_for_insight to verify the source before editing. Turn the evidence into "
            "broadcast-safe JSON with exactly keys headline, commentary, event_ids. event_ids must be selected "
            "from the verified source event IDs. No digits in headline or commentary. Avoid causal certainty; "
            "keep uncertainty visible. Output JSON only."),
            tools=framework_tools(ctx, "StoryEditor"),
            middleware=[_stage_middleware(trace, "StoryEditor")])
        prompt = json.dumps({"synthetic": True, "verified_insight": insight.model_dump(mode="json"),
                             "source_events": [e.model_dump(mode="json", by_alias=True) for e in events
                                               if e.event_id in insight.supporting_event_ids],
                             "event_cutoff": insight.match_second}, ensure_ascii=False)
        workflow = SequentialBuilder(participants=[analyst, editor]).build()
        result = await asyncio.wait_for(workflow.run(prompt), timeout=30)
        outputs = result.get_outputs()
        trace["usage_details"] = trace["usage_details"] or _safe_usage_details(outputs)
        if not outputs or not outputs[0].messages:
            raise ValueError("Agent Framework returned no output")
        if (len(outputs) != 1 or outputs[0].messages[-1].author_name != "StoryEditor"
                or [(s["role"], s["status"]) for s in trace["stages"]] != [
                    ("TacticalAnalyst", "completed"), ("StoryEditor", "completed")]):
            raise ValueError("Missing specialist execution evidence or final editor output")
        raw = outputs[0].messages[-1].text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
        if len(raw) > 16_000:
            raise ValueError("Agent Framework output exceeded the response limit")
        packet = _parse_model_packet(raw)
        if not audit_model_packet(packet, insight, match, events):
            trace["audit_verdict"] = "rejected"
            trace["stages"].append({"role": "EvidenceAuditor", "kind": "deterministic_gate", "status": "rejected"})
            trace["status"] = "fallback"
            trace["provider_status"] = "fallback"
            return _fallback_result(match, events, insight, trace, "audit_rejected")
        trace["audit_verdict"] = "approved"
        trace["stages"].append({"role": "EvidenceAuditor", "kind": "deterministic_gate", "status": "approved"})
        cue = next((cue for cue in overlays_for(match, events, at_second=insight.match_second)
                    if cue.insight_id == insight.insight_id), None)
        cue_draft = None
        if cue is not None:
            draft = execute_tool(ctx, "BroadcastDirector", "prepare_broadcast_cue", {
                "match_id": match.match_id,
                "insight_id": insight.insight_id,
                "at_second": insight.match_second,
                "target_time": cue.start_match_second,
                "template": cue.visual_template,
            })
            cue_draft = {**draft["cue"], "approval_state": draft["approval_state"],
                         "publishing": draft["publishing"]}
        trace["stages"].append({"role": "BroadcastDirector", "kind": "deterministic_draft", "status": "completed" if cue_draft else "unavailable"})
        recap = recap_for(match, events, "en", "casual", at_second=insight.match_second)
        trace["stages"].append({"role": "FanPersonalizer", "kind": "verified_template", "status": "completed"})
        trace["status"] = "approved"
        trace["provider_status"] = "authenticated_success"
        result_packet = {"status": "approved_model_opinion", "provider": "microsoft_foundry_agent_framework",
                "headline": packet["headline"], "commentary": packet["commentary"],
                "supporting_event_ids": packet["event_ids"],
                "verified_facts": [c.model_dump(mode="json", by_alias=True) for c in insight.factual_claims],
                "broadcast_cue_draft": cue_draft, "recap_provider": recap["provider"], "trace_id": trace["trace_id"]}
        trace["audit_verdict"] = "approved"
        trace["output_hash_scope"] = "response-canonical-json/1"
        trace["output_hash"] = hashlib.sha256(json.dumps(result_packet, ensure_ascii=False, sort_keys=True,
                                                          separators=(",", ":")).encode()).hexdigest()
        return result_packet
    except asyncio.CancelledError:
        trace.update(status="cancelled", provider_status="error", error_code="CancelledError")
        raise
    except Exception as error:
        trace["status"] = "fallback"
        trace["provider_status"] = "error"
        trace["error_code"] = type(error).__name__
        if (status := _http_status(error)) is not None:
            trace["http_status"] = status
        return _fallback_result(match, events, insight, trace, type(error).__name__)
    finally:
        trace["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)


def _fallback_result(match: Match, events: list[MatchEvent], insight: Insight,
                     trace: dict, reason: str) -> dict:
    """Return only deterministic verified content after a provider/tool/audit failure."""
    recap = recap_for(match, events, "en", "casual", at_second=insight.match_second)
    cue = next((cue for cue in overlays_for(match, events, insight.match_second)
                if cue.insight_id == insight.insight_id), None)
    trace["fallback_reason"] = reason
    trace["audit_verdict"] = "rejected_model_output" if reason == "audit_rejected" else "not_run"
    trace["stages"].append({"role": "DeterministicFallback", "kind": "verified_rule_based_templates", "status": "completed"})
    result_packet = {
        "status": "deterministic_fallback",
        "provider": "verified_rule_based_templates",
        "headline": insight.title,
        "commentary": insight.explanation,
        "supporting_event_ids": insight.supporting_event_ids,
        "verified_facts": [c.model_dump(mode="json", by_alias=True) for c in insight.factual_claims],
        "broadcast_cue_draft": None if cue is None else {
            "approval_state": "draft_only",
            "source_insight_id": insight.insight_id,
            "evidence_event_ids": cue.supporting_event_ids,
            "start_match_second": cue.start_match_second,
            "end_match_second": cue.end_match_second,
            "visual_template": cue.visual_template,
            "safe_area": cue.safe_area,
            "publishing": False,
        },
        "recap_provider": recap["provider"],
        "trace_id": trace["trace_id"],
    }
    trace["output_hash_scope"] = "response-canonical-json/1"
    trace["output_hash"] = hashlib.sha256(json.dumps(result_packet, ensure_ascii=False, sort_keys=True,
                                                      separators=(",", ":")).encode()).hexdigest()
    return result_packet
