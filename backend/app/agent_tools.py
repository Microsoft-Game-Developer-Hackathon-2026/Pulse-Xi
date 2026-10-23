"""Schema-checked, read-only tools for evidence-scoped agent workflows.

No tool accepts URLs, SQL, caller-provided metric values, or a branch identifier.
"""
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .analytics import metrics_at, window_events
from .evidence import insights_for, overlays_for, verify
from .models import Insight, Match, MatchEvent


TOOL_SCHEMA_VERSION = "pulse-xi-agent-tools/1"
METRICS_FORMULA_VERSION = "pulse-xi-event-metrics/1"
ROLE_ALLOWLIST = {
    "TacticalAnalyst": frozenset({"get_match_metrics", "find_key_moments", "get_evidence_for_insight"}),
    "StoryEditor": frozenset({"get_evidence_for_insight"}),
    "BroadcastDirector": frozenset({"prepare_broadcast_cue"}),
    "FanPersonalizer": frozenset({"get_evidence_for_insight", "find_key_moments"}),
}
UNAVAILABLE_CAPABILITIES = {
    "compare_scenarios": {"status": "unavailable", "dependency": "#8 ForkCast contract"},
}


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class MetricsInput(StrictInput):
    match_id: str = Field(min_length=1, max_length=160)
    at_second: int = Field(ge=0, le=5400)
    window_start: int = Field(ge=0, le=5400)
    window_seconds: int = Field(ge=1, le=300)


class MomentsInput(StrictInput):
    match_id: str = Field(min_length=1, max_length=160)
    at_second: int = Field(ge=0, le=5400)
    rule_set: Literal["verified_insights/1"] = "verified_insights/1"
    limit: int = Field(ge=1, le=10)


class EvidenceInput(StrictInput):
    match_id: str = Field(min_length=1, max_length=160)
    insight_id: str = Field(min_length=1, max_length=160)
    at_second: int = Field(ge=0, le=5400)


class CueInput(StrictInput):
    match_id: str = Field(min_length=1, max_length=160)
    insight_id: str = Field(min_length=1, max_length=160)
    at_second: int = Field(ge=0, le=5400)
    target_time: int = Field(ge=0, le=5400)
    template: Literal["score_lower_third", "tactical_lower_third"]


class ToolOutput(StrictInput):
    schema_version: Literal["pulse-xi-agent-tools/1"] = TOOL_SCHEMA_VERSION
    tool_name: str
    match_id: str
    event_cutoff: int = Field(ge=0, le=5400)
    provenance: str
    verification_status: Literal["verified", "draft_only"]
    output_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


@dataclass
class ToolContext:
    match: Match
    events: list[MatchEvent]
    insight: Insight
    trace: dict
    max_calls: int = 8
    call_count: int = 0
    called_tools: set[str] = field(default_factory=set)

    @property
    def cutoff(self) -> int:
        return self.insight.match_second


class ToolFailure(Exception):
    def __init__(self, code: str, status: int = 422):
        self.code = code
        self.status = status
        super().__init__(code)


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _envelope(name: str, match_id: str, cutoff: int, provenance: str,
              verification_status: Literal["verified", "draft_only"], payload: dict) -> dict:
    core = {
        "schema_version": TOOL_SCHEMA_VERSION,
        "tool_name": name,
        "match_id": match_id,
        "event_cutoff": cutoff,
        "provenance": provenance,
        "verification_status": verification_status,
        **payload,
    }
    core["output_hash"] = hashlib.sha256(_json(core).encode("utf-8")).hexdigest()
    return ToolOutput.model_validate({key: core[key] for key in ToolOutput.model_fields if key in core}).model_dump() | {
        key: value for key, value in core.items() if key not in ToolOutput.model_fields
    }


def _visible_insight(ctx: ToolContext, insight_id: str, cutoff: int) -> Insight:
    if cutoff > ctx.cutoff:
        raise ToolFailure("future_cutoff")
    insight = next((item for item in insights_for(ctx.match, ctx.events, cutoff)
                    if item.insight_id == insight_id), None)
    if insight is None or not verify(insight, ctx.match, ctx.events):
        raise ToolFailure("unverified_or_unknown_insight", 404)
    return insight


def _execute(ctx: ToolContext, role: str, name: str, raw_args: dict) -> dict:
    started = time.perf_counter()
    safe_args = {}
    status = "completed"
    error_code = None
    charged = False
    result = None
    try:
        if name not in ROLE_ALLOWLIST.get(role, frozenset()):
            raise ToolFailure("tool_not_allowed", 403)
        if ctx.call_count >= ctx.max_calls:
            raise ToolFailure("tool_call_limit", 429)
        ctx.call_count += 1
        charged = True
        if name == "get_match_metrics":
            request = MetricsInput.model_validate(raw_args)
            safe_args = request.model_dump()
            if request.match_id != ctx.match.match_id:
                raise ToolFailure("match_mismatch", 404)
            if request.at_second > ctx.cutoff:
                raise ToolFailure("future_cutoff")
            end = request.window_start + request.window_seconds
            if end > request.at_second or end > ctx.match.duration_seconds:
                raise ToolFailure("invalid_window")
            source_events = window_events(ctx.events, request.window_start, end)
            calculated = metrics_at(ctx.match, source_events, end)
            payload = {
                "formula_version": METRICS_FORMULA_VERSION,
                "window": {"start": request.window_start, "end": end, "semantics": "(start,end]"},
                "metrics": calculated.model_dump(mode="json"),
                "source_event_ids": [event.event_id for event in source_events],
            }
            result = _envelope(name, request.match_id, request.at_second, "deterministic event metrics",
                               "verified", payload)
        elif name == "find_key_moments":
            request = MomentsInput.model_validate(raw_args)
            safe_args = request.model_dump()
            if request.match_id != ctx.match.match_id:
                raise ToolFailure("match_mismatch", 404)
            if request.at_second > ctx.cutoff:
                raise ToolFailure("future_cutoff")
            candidates = [item for item in insights_for(ctx.match, ctx.events, request.at_second)
                          if verify(item, ctx.match, ctx.events)]
            result = _envelope(name, request.match_id, request.at_second, "verified deterministic insight rules",
                               "verified", {"rule_set": request.rule_set, "candidates": [
                                   {"insight_id": item.insight_id, "category": item.category,
                                    "match_second": item.match_second, "team_id": item.team_id,
                                    "event_ids": item.supporting_event_ids, "explanation": item.explanation}
                                   for item in candidates[:request.limit]]})
        elif name == "get_evidence_for_insight":
            request = EvidenceInput.model_validate(raw_args)
            safe_args = request.model_dump()
            if request.match_id != ctx.match.match_id:
                raise ToolFailure("match_mismatch", 404)
            insight = _visible_insight(ctx, request.insight_id, request.at_second)
            source_ids = set(insight.supporting_event_ids)
            source_events = [event for event in ctx.events if event.event_id in source_ids]
            result = _envelope(name, request.match_id, request.at_second, "deterministic evidence verifier",
                               "verified", {"insight": insight.model_dump(mode="json"),
                                   "claims": [claim.model_dump(mode="json") for claim in insight.factual_claims],
                                   "source_event_ids": [event.event_id for event in source_events],
                                   "source_events": [event.model_dump(mode="json", by_alias=True) for event in source_events]})
        elif name == "prepare_broadcast_cue":
            request = CueInput.model_validate(raw_args)
            safe_args = request.model_dump()
            if request.match_id != ctx.match.match_id:
                raise ToolFailure("match_mismatch", 404)
            if request.target_time < request.at_second or request.target_time > ctx.match.duration_seconds:
                raise ToolFailure("invalid_target_time")
            insight = _visible_insight(ctx, request.insight_id, request.at_second)
            cue = next((item for item in overlays_for(ctx.match, ctx.events, request.at_second)
                        if item.insight_id == insight.insight_id and item.visual_template == request.template), None)
            if cue is None:
                raise ToolFailure("cue_unavailable", 404)
            duration = cue.show_duration_seconds
            if request.target_time + duration > ctx.match.duration_seconds:
                raise ToolFailure("cue_out_of_bounds")
            result = _envelope(name, request.match_id, request.at_second, "verified insight; deterministic cue template",
                               "draft_only", {"approval_state": "draft_only", "publishing": False,
                                   "cue": {"source_insight_id": insight.insight_id,
                                       "evidence_event_ids": insight.supporting_event_ids,
                                       "start_match_second": request.target_time,
                                       "end_match_second": request.target_time + duration,
                                       "visual_template": request.template,
                                       "safe_area": cue.safe_area, "text": cue.text}})
        else:
            raise ToolFailure("unknown_tool", 404)
        return result
    except (ValidationError, TypeError, ValueError) as error:
        status = "rejected"
        error_code = "invalid_tool_arguments"
        raise ToolFailure("invalid_tool_arguments") from error
    except ToolFailure as error:
        status = "rejected"
        error_code = error.code
        raise error
    except Exception as error:
        status = "failed"
        error_code = type(error).__name__
        raise
    finally:
        row = {
            "role": role, "tool_name": name, "arguments": safe_args,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            "status": status, "error_code": error_code, "budget_charged": charged,
            "input_hash": hashlib.sha256(_json(safe_args).encode()).hexdigest(),
            "output_hash": result.get("output_hash") if result else None,
        }
        calls = ctx.trace.setdefault("tool_calls", [])
        # Preserve all budgeted calls and one counted row per preflight denial
        # reason; repeated forbidden requests cannot grow trace memory.
        previous = next((c for c in calls if not c.get("budget_charged", True)
                         and c.get("error_code") == error_code), None) if not charged else None
        if previous:
            previous["rejected_count"] += 1
        else:
            if not charged:
                row["rejected_count"] = 1
            calls.append(row)
        if charged:
            ctx.called_tools.add(name)


def execute_tool(ctx: ToolContext, role: str, name: str, raw_args: dict) -> dict:
    """Public deterministic adapter entry point, also used by unit tests."""
    return _execute(ctx, role, name, raw_args)


def framework_tools(ctx: ToolContext, role: str):
    """Build only the least-privilege Agent Framework functions for one role."""
    from agent_framework import tool

    functions = []
    if "get_match_metrics" in ROLE_ALLOWLIST.get(role, frozenset()):
        def get_match_metrics(match_id: str, at_second: int, window_start: int, window_seconds: int) -> str:
            """Read deterministic event metrics for a bounded, past-only match window."""
            return _json(_execute(ctx, role, "get_match_metrics", {
                "match_id": match_id, "at_second": at_second,
                "window_start": window_start, "window_seconds": window_seconds,
            }))
        functions.append(tool(name="get_match_metrics", description=get_match_metrics.__doc__)(get_match_metrics))
    if "find_key_moments" in ROLE_ALLOWLIST.get(role, frozenset()):
        def find_key_moments(match_id: str, at_second: int, rule_set: str = "verified_insights/1", limit: int = 5) -> str:
            """Find salient moments produced by deterministic verified insight rules."""
            return _json(_execute(ctx, role, "find_key_moments", {
                "match_id": match_id, "at_second": at_second, "rule_set": rule_set, "limit": limit,
            }))
        functions.append(tool(name="find_key_moments", description=find_key_moments.__doc__)(find_key_moments))
    if "get_evidence_for_insight" in ROLE_ALLOWLIST.get(role, frozenset()):
        def get_evidence_for_insight(match_id: str, insight_id: str, at_second: int) -> str:
            """Retrieve a verified insight and its exact cited source events."""
            return _json(_execute(ctx, role, "get_evidence_for_insight", {
                "match_id": match_id, "insight_id": insight_id, "at_second": at_second,
            }))
        functions.append(tool(name="get_evidence_for_insight", description=get_evidence_for_insight.__doc__)(get_evidence_for_insight))
    if "prepare_broadcast_cue" in ROLE_ALLOWLIST.get(role, frozenset()):
        def prepare_broadcast_cue(match_id: str, insight_id: str, at_second: int,
                                  target_time: int, template: str) -> str:
            """Prepare a verified broadcast cue draft; this tool never publishes it."""
            return _json(_execute(ctx, role, "prepare_broadcast_cue", {
                "match_id": match_id, "insight_id": insight_id, "at_second": at_second,
                "target_time": target_time, "template": template,
            }))
        functions.append(tool(name="prepare_broadcast_cue", description=prepare_broadcast_cue.__doc__)(prepare_broadcast_cue))
    return functions
