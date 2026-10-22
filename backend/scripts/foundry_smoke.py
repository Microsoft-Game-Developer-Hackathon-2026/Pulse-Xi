"""One-shot, admin-operated Foundry validation; --check-only never makes a request."""
import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents import TRACES, configured, run_specialists
from app.evidence import insights_for, verify
from app.simulator import FIXTURES, generate


def _evidence_hash(match, events, insight) -> str:
    packet = {
        "match_id": match.match_id,
        "insight": insight.model_dump(mode="json"),
        "source_events": [event.model_dump(mode="json", by_alias=True)
                          for event in events if event.event_id in insight.supporting_event_ids],
    }
    encoded = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _safe_report(trace: dict, result: dict, evidence_hash: str) -> dict:
    """Whitelist metadata only; never print endpoint, credentials, prompts, or raw errors."""
    return {
        "invocation_id": trace.get("invocation_id"),
        "trace_id": trace.get("trace_id"),
        "provider": trace.get("provider", "microsoft_foundry_agent_framework"),
        "provider_status": trace.get("provider_status", "unknown"),
        "workflow_status": trace.get("status", "unknown"),
        "model": trace.get("model") or os.getenv("FOUNDRY_MODEL"),
        "evidence_packet_sha256": evidence_hash,
        "audit_verdict": trace.get("audit_verdict", "not_reported"),
        "elapsed_ms": trace.get("elapsed_ms"),
        "token_usage": trace.get("usage_details"),
        "output_status": result.get("status") if isinstance(result, dict) else None,
        "output_hash": trace.get("output_hash"),
        "error_code": trace.get("error_type") or trace.get("error_code"),
    }


def check_sdk_compatibility() -> dict:
    """Import and construct the pinned workflow without authenticating or calling Foundry."""
    from agent_framework.foundry import FoundryChatClient
    from agent_framework.orchestrations import SequentialBuilder
    from azure.identity import AzureCliCredential

    client = FoundryChatClient(
        project_endpoint="https://offline-validation.invalid",
        model="offline-validation-only",
        credential=AzureCliCredential(),
    )
    analyst = client.as_agent(name="TacticalAnalyst", instructions="Offline compatibility check.")
    editor = client.as_agent(name="StoryEditor", instructions="Offline compatibility check.")
    workflow = SequentialBuilder(participants=[analyst, editor]).build()
    if workflow is None:
        raise RuntimeError("Agent Framework did not build the sequential workflow")
    return {"status": "sdk_compatibility_ok", "network_call": False, "authenticated": False}


async def run_one_workflow(fixture: str, timeout_seconds: int) -> dict:
    if not configured():
        raise RuntimeError("Foundry configuration is incomplete; no request was made")
    match, events = generate(fixture)
    insight = next((item for item in insights_for(match, events) if verify(item, match, events)), None)
    if insight is None:
        raise RuntimeError("No verified synthetic evidence packet is available")

    evidence_hash = _evidence_hash(match, events, insight)
    previous_trace_id = TRACES[-1].get("trace_id") if TRACES else None
    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            run_specialists(match, events, insight),
            timeout=timeout_seconds,
        )
    except Exception as error:
        trace = TRACES[-1] if TRACES and TRACES[-1].get("trace_id") != previous_trace_id else {
            "provider": "microsoft_foundry_agent_framework",
            "provider_status": "error",
            "status": "failed",
            "error_type": type(error).__name__,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
        }
        trace.setdefault("elapsed_ms", round((time.perf_counter() - started) * 1000, 1))
        if trace.get("status") == "running":
            trace["status"] = "failed"
            trace["provider_status"] = "error"
            trace["error_type"] = type(error).__name__
        report = _safe_report(trace, {}, evidence_hash)
        report["workflow_status"] = "failed"
        return report

    trace = TRACES[-1] if TRACES and TRACES[-1].get("trace_id") != previous_trace_id else {}
    trace.setdefault("elapsed_ms", round((time.perf_counter() - started) * 1000, 1))
    return _safe_report(trace, result, evidence_hash)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-only", action="store_true",
                      help="validate pinned SDK imports and workflow construction without inference")
    mode.add_argument("--confirm-cost", action="store_true",
                      help="authorize one hosted workflow invocation; may incur Azure charges")
    parser.add_argument("--fixture", choices=sorted(FIXTURES), default="late-winner")
    parser.add_argument("--timeout-seconds", type=int, default=45)
    args = parser.parse_args(argv)

    if not 5 <= args.timeout_seconds <= 120:
        parser.error("--timeout-seconds must be between 5 and 120")
    if args.check_only:
        try:
            report = check_sdk_compatibility()
        except Exception as error:
            print(json.dumps({"status": "sdk_compatibility_failed",
                              "error_code": type(error).__name__}, sort_keys=True))
            return 1
        print(json.dumps(report, sort_keys=True))
        return 0

    if not configured():
        print(json.dumps({"status": "not_configured", "request_made": False}, sort_keys=True))
        return 2
    try:
        report = asyncio.run(run_one_workflow(args.fixture, args.timeout_seconds))
    except Exception as error:
        # Provider messages can contain request data or endpoint details; expose only the type.
        report = {"status": "preflight_failed", "request_made": False,
                  "error_code": type(error).__name__}
        print(json.dumps(report, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["provider_status"] == "authenticated_success" and report["audit_verdict"] == "approved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
