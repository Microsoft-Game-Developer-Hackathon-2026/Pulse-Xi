import asyncio
from types import SimpleNamespace

import pytest

from app.agents import _safe_usage_details
from scripts import foundry_smoke


def test_usage_report_keeps_only_documented_integer_counters():
    outputs = [
        SimpleNamespace(usage_details=SimpleNamespace(
            input_token_count=12, output_token_count=7, total_token_count=19,
            raw_request="private",
        )),
        SimpleNamespace(usage_details={
            "input_token_count": 3, "output_token_count": 2,
            "total_token_count": 5, "endpoint": "https://secret.invalid",
        }),
    ]

    assert _safe_usage_details(outputs) == {
        "input_token_count": 15, "output_token_count": 9, "total_token_count": 24,
    }


def test_smoke_report_redacts_raw_provider_data(monkeypatch):
    monkeypatch.setenv("FOUNDRY_MODEL", "deployment-a")
    trace = {
        "invocation_id": "run-id", "trace_id": "trace-id",
        "provider_status": "authenticated_success", "status": "approved",
        "audit_verdict": "approved", "elapsed_ms": 120.5,
        "usage_details": {"total_token_count": 19},
        "output_hash": "a" * 64,
        "endpoint": "https://private.example",
        "credential": "do-not-print",
        "prompt": "private prompt",
    }
    report = foundry_smoke._safe_report(trace, {"status": "approved_model_opinion",
                                                "commentary": "not included"}, "b" * 64)
    serialized = str(report)

    assert report["provider_status"] == "authenticated_success"
    assert report["token_usage"] == {"total_token_count": 19}
    assert report["evidence_packet_sha256"] == "b" * 64
    assert "private.example" not in serialized
    assert "do-not-print" not in serialized
    assert "private prompt" not in serialized
    assert "commentary" not in serialized


def test_paid_smoke_requires_explicit_confirmation(monkeypatch):
    called = False

    async def forbidden_call(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("must not dispatch")

    monkeypatch.setattr(foundry_smoke, "run_one_workflow", forbidden_call)
    monkeypatch.setattr(foundry_smoke, "configured", lambda: True)

    with pytest.raises(SystemExit) as error:
        foundry_smoke.main(["--fixture", "late-winner"])

    assert error.value.code == 2
    assert not called


def test_sdk_check_only_is_separate_from_paid_invocation(monkeypatch):
    monkeypatch.setattr(foundry_smoke, "check_sdk_compatibility",
                        lambda: {"status": "sdk_compatibility_ok", "network_call": False,
                                 "authenticated": False})
    monkeypatch.setattr(foundry_smoke, "configured", lambda: False)

    assert foundry_smoke.main(["--check-only"]) == 0


def test_timed_out_smoke_returns_redacted_failure(monkeypatch):
    monkeypatch.setattr(foundry_smoke, "configured", lambda: True)
    monkeypatch.setattr(foundry_smoke, "TRACES", [])

    async def timeout(coro, timeout):
        coro.close()
        raise asyncio.TimeoutError()

    monkeypatch.setattr(foundry_smoke.asyncio, "wait_for", timeout)
    report = asyncio.run(foundry_smoke.run_one_workflow("late-winner", 5))

    assert report["provider_status"] == "error"
    assert report["workflow_status"] == "failed"
    assert report["error_code"] == "TimeoutError"


def test_smoke_preserves_safe_handoffs_and_drops_nested_secrets():
    trace = {"run_id": "actual-run", "source_revision": "c" * 40,
             "started_at_utc": "2026-10-23T10:00:00+00:00",
             "usage_details": {"total_token_count": 6, "api_key": "SENTINEL_SECRET"},
             "stages": [{"role": "StoryEditor", "kind": "foundry_agent", "status": "completed",
                         "input_hash": "a" * 64, "output_hash": "b" * 64,
                         "duration_ms": 3.0, "prompt": "SENTINEL_SECRET"}],
             "tool_calls": [{"role": "StoryEditor", "tool_name": "get_evidence_for_insight",
                             "status": "completed", "output_hash": "d" * 64,
                             "arguments": {"credential": "SENTINEL_SECRET"}}]}
    report = foundry_smoke._safe_report(trace, {}, "e" * 64)
    assert report["invocation_id"] == "actual-run"
    assert report["source_revision"] == "c" * 40
    assert report["started_at_utc"] == trace["started_at_utc"]
    assert report["stages"][0]["output_hash"] == "b" * 64
    assert report["tool_calls"][0]["tool_name"] == "get_evidence_for_insight"
    assert report["token_usage"] == {"total_token_count": 6}
    assert "SENTINEL_SECRET" not in str(report)
