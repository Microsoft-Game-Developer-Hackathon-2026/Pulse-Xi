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

Agent Framework middleware now records each actual specialist invocation from
running to completed, failed or cancelled, with duration and input/output hashes.
The final response must be attributed to StoryEditor and both observed specialist
stages must complete before the output gate. No stage is inferred from its prompt.
Provider HTTP status is retained only when supplied as a numeric status; raw
exception text remains excluded. Tool preflight denials are recorded and repeated
denials are counted in one row per reason, keeping trace size bounded. An unexpected
tool exception is failed, rather than completed. Rejected model copy still falls
back; unverified source evidence is rejected before any provider invocation.

The local smoke report includes actual run ID, UTC timestamp, Git revision/dirty
state when available, evidence hash, observed handoff hashes, tool statuses and
returned integer usage counters. A missing Git repository or usage value remains
unavailable. It excludes raw arguments, prompts, provider objects and endpoint
credentials. Accepted-model and fallback cue metadata both retain draft-only,
non-publishing flags, and deterministic recap/cue calculations use the insight cutoff.
Response digests identify `response-canonical-json/1`: UTF-8 JSON with sorted keys,
compact separators and unescaped Unicode, over the returned packet. Verified facts
are serialized records, not Python object representations. Stage digests separately
identify the message-role/text scope; tool output digests cover their deterministic packets.

The model output is rejected if it has an invalid shape, unsupported event
references, duplicated IDs, or numeric prose. Failure returns deterministic
verified content. The final evidence audit cannot be overridden by an agent.
There is one application workflow attempt (`max_workflow_attempts: 1`) and a
30-second execution timeout. Legacy `max_model_attempts: 1` is retained for trace
compatibility and refers to that workflow attempt, not a count of network calls.
The two specialists and tool turns can make multiple model requests; provider SDK
transport retries are not certified by this field. Owner cost approval must cover
the workflow, and only returned usage counters are reported. Cancellation records
its actual state and propagates rather than leaving a running trace.

The output gate validates shape, IDs, numeric-prose exclusion and deterministic
facts; it is not a semantic proof of arbitrary prose. Model copy remains labelled
opinion, separate from verified facts, and needs release review before public use.

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

`python scripts/foundry_smoke.py --check-only` also exercises the pinned SDK's
real sequential/middleware/output contract with an in-memory chat transport.
The Foundry client is constructed but never invoked. This is offline compatibility
evidence with `authenticated: false`, not a hosted inference result.
