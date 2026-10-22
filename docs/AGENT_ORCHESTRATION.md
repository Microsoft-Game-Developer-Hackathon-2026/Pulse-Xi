# Evidence-scoped agent workflow

The optional workflow in `backend/app/agents.py` is explicitly invoked through
the existing admin-gated `POST /api/insights/{id}/agent-run` endpoint. It
constructs two Microsoft Agent Framework roles—Tactical Analyst followed by
Story Editor—when the optional provider configuration is enabled. A
deterministic verifier gates the resulting copy. Broadcast cue drafting and
fan recap formatting remain deterministic.

## Tool contract

`backend/app/agent_tools.py` exposes strict, extra-forbidden request models
and per-role allowlists. Tools read only the in-memory authoritative match,
events, verified insight packets, and deterministic overlay calculations. They
do not accept URLs, SQL, arbitrary tool names, or model-supplied metric values.

- `get_match_metrics` computes event metrics in a bounded `(start, end]`
  window and returns source event IDs and a formula version.
- `find_key_moments` returns only verified deterministic insight candidates.
- `get_evidence_for_insight` returns a verified packet and its source events.
- `prepare_broadcast_cue` produces a draft marked `publishing: false`.
- `compare_scenarios` remains explicitly unavailable. ForkCast is now merged,
  but an owner-authorized, bounded, verified branch-evidence tool adapter has not
  been implemented; the engine alone does not enable this tool.

Tool inputs reject unknown fields, mismatched match IDs, out-of-cutoff clocks,
invalid windows, and unverified insights. Each invocation is bounded to eight
tool calls per workflow. Per-role allowlists expose metrics and candidate search
to Tactical Analyst, evidence retrieval to Story Editor, and draft preparation
to Broadcast Director. A call not allowed for a role fails closed.

## Trace and fallback

The admin-gated `GET /api/agent-traces` endpoint returns process-local traces
with schema version, run and source IDs, provider status, executed stages,
actual tool calls, safe normalized arguments, call timings, output hash, audit
verdict, and fallback reason code. It omits prompts, credentials, model tokens,
and raw provider errors. Traces are capped at the latest 50 runs and are not
durable storage. A stage is listed only once the workflow reaches it; the trace
does not claim a hosted call when configuration or invocation fails.

The model output is rejected if it has an invalid shape, unsupported event
references, duplicated IDs, or numeric prose. Failure returns deterministic
verified content. The final evidence audit cannot be overridden by an agent.
There are no automatic model retries (`max_model_attempts: 1`), and execution
has a 30-second timeout. This avoids retry cost and duplicate inference while
keeping the deterministic fallback available.

## Verification status and provider setup

Tests should use deterministic adapters and mocks only; routine CI must not make
hosted calls. A real authenticated Foundry run is still a separate acceptance
step requiring valid deployment credentials and explicit cost approval under
issue #14. No hosted run, provider latency, token use, or cost is claimed by
this implementation. Scenario comparison awaits its scoped tool adapter, while producer approval
and cue publishing remain with the broadcast studio work in #17.

The integration follows Microsoft's documented
[Foundry provider](https://learn.microsoft.com/en-us/agent-framework/agents/providers/microsoft-foundry)
and [function tool](https://learn.microsoft.com/en-us/agent-framework/agents/tools/function-tools)
patterns. Verify compatibility against the repository's pinned optional
dependencies before enabling a deployment.
