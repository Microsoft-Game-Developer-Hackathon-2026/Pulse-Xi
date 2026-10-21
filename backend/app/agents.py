"""Optional, explicitly invoked Microsoft Agent Framework + Foundry workflow.

No hosted call is made during startup, ingestion, tests, or deterministic replay.
"""
import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from uuid import uuid4

from .evidence import overlays_for, recap_for, verify
from .models import Insight, Match, MatchEvent

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


def audit_model_packet(packet: dict, insight: Insight, match: Match, events: list[MatchEvent]) -> bool:
    """Gate model copy as an opinion and preserve authoritative event facts."""
    if not verify(insight, match, events):
        return False
    if set(packet) != {"headline", "commentary", "event_ids"}:
        return False
    if not isinstance(packet["headline"], str) or not isinstance(packet["commentary"], str):
        return False
    if not isinstance(packet["event_ids"], list) or not packet["event_ids"]:
        return False
    if not set(packet["event_ids"]).issubset(insight.supporting_event_ids):
        return False
    if len(packet["headline"]) > 120 or len(packet["commentary"]) > 500:
        return False
    # Numbers are only delivered from the deterministic factual packet, never from model prose.
    if re.search(r"\d", packet["headline"] + packet["commentary"]):
        return False
    return True


async def run_specialists(match: Match, events: list[MatchEvent], insight: Insight) -> dict:
    if not configured():
        raise RuntimeError("Foundry is not enabled/configured")
    # Lazy imports keep local deterministic operation dependency-free.
    from agent_framework.foundry import FoundryChatClient
    from agent_framework.orchestrations import SequentialBuilder
    from azure.identity import AzureCliCredential

    started = time.perf_counter()
    invocation_id = str(uuid4())
    trace = {"invocation_id": invocation_id, "trace_id": f"trace-{invocation_id}",
             "started_at_utc": datetime.now(timezone.utc).isoformat(),
             "provider": "microsoft_foundry_agent_framework",
             "provider_status": "authenticated_inference_pending",
             "model": os.getenv("FOUNDRY_MODEL"), "status": "running", "stages": [],
             "usage_details": None}
    TRACES.append(trace)
    TRACES[:] = TRACES[-50:]
    try:
        client = FoundryChatClient(project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
                                   model=os.environ["FOUNDRY_MODEL"], credential=AzureCliCredential())
        analyst = client.as_agent(name="TacticalAnalyst", instructions=(
            "Analyze only the supplied synthetic evidence. Propose a qualitative observation. "
            "Never invent a metric, player action, cause, or event ID. Avoid digits in prose."))
        editor = client.as_agent(name="StoryEditor", instructions=(
            "Turn the previous observation into broadcast-safe JSON with exactly keys headline, commentary, event_ids. "
            "event_ids must be selected from the supplied approved event IDs. No digits in headline or commentary. "
            "Avoid causal certainty; keep uncertainty visible. Output JSON only."))
        prompt = json.dumps({"synthetic": True, "verified_insight": insight.model_dump(mode="json"),
                             "source_events": [e.model_dump(mode="json", by_alias=True) for e in events
                                               if e.event_id in insight.supporting_event_ids]}, ensure_ascii=False)
        workflow = SequentialBuilder(participants=[analyst, editor]).build()
        result = await workflow.run(prompt)
        outputs = result.get_outputs()
        trace["usage_details"] = _safe_usage_details(outputs)
        trace["provider_status"] = "authenticated_success"
        if not outputs or not outputs[0].messages:
            raise ValueError("Agent Framework returned no output")
        raw = outputs[0].messages[-1].text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
        packet = json.loads(raw)
        trace["stages"] = [
            {"role": "TacticalAnalyst", "kind": "foundry_agent", "status": "completed"},
            {"role": "StoryEditor", "kind": "foundry_agent", "status": "completed"},
        ]
        if not audit_model_packet(packet, insight, match, events):
            trace["stages"].append({"role": "EvidenceAuditor", "kind": "deterministic_gate", "status": "rejected"})
            trace["status"] = "rejected"
            return {"status": "rejected", "reason": "unsupported model packet", "trace_id": trace["trace_id"]}
        trace["stages"].append({"role": "EvidenceAuditor", "kind": "deterministic_gate", "status": "approved"})
        cue = next(cue for cue in overlays_for(match, events) if cue.insight_id == insight.insight_id)
        trace["stages"].append({"role": "BroadcastDirector", "kind": "deterministic_scheduler", "status": "completed"})
        recap = recap_for(match, events, "en", "casual")
        trace["stages"].append({"role": "FanPersonalizer", "kind": "verified_template", "status": "completed"})
        trace["status"] = "approved"
        return {"status": "approved_model_opinion", "provider": "microsoft_foundry_agent_framework",
                "headline": packet["headline"], "commentary": packet["commentary"],
                "supporting_event_ids": packet["event_ids"], "verified_facts": insight.factual_claims,
                "overlay_cue_id": cue.cue_id, "recap_provider": recap["provider"], "trace_id": trace["trace_id"]}
    except Exception as error:
        trace["status"] = "failed"
        trace["provider_status"] = "error"
        trace["error_type"] = type(error).__name__
        raise
    finally:
        trace["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
