# Optional Microsoft Foundry workflow

Privileged trace inspection (`GET /api/agent-traces`) requires the current
`PULSE_FOUNDRY_ADMIN_TOKEN` through the `X-Admin-Token` header. Missing/empty server
configuration returns 503; absent or invalid credentials return 403 without
trace records. Removing configuration also denies access to traces retained in
the process. Authorized reads do not start inference. Successful and denied trace reads use `Cache-Control: no-store`. This change fixes Issue #44;
it does not introduce a public trace viewer or prove hosted-provider execution.

The normal local application uses verified rule-based narratives and makes **zero hosted model calls**. `/health` reports `not_configured`. The optional code path in `backend/app/agents.py` uses Microsoft Agent Framework's `FoundryChatClient` and `SequentialBuilder` per [Microsoft Foundry provider guidance](https://learn.microsoft.com/en-us/agent-framework/agents/providers/microsoft-foundry) and [sequential workflow documentation](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential).

When explicitly enabled, Tactical Analyst and Story Editor run as separate Foundry-backed agents. Their output passes a deterministic Evidence Auditor that checks cited IDs and rejects prose containing invented numeric claims. A rule-based Broadcast Director links the approved packet to a timed cue, and the Fan Personalizer returns verified templates. The trace records these stages and whether they succeeded. The model-generated text is labeled **opinion with verified references**, while score facts remain authoritative deterministic output.

Install optional dependencies with `python -m pip install -r backend/requirements-foundry.txt`. Supply server-side `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL`, `PULSE_FOUNDRY_ADMIN_TOKEN`, and `PULSE_ENABLE_FOUNDRY=true`, then authenticate to Azure with `az login` for local development. Only an explicit `POST /api/insights/{id}/agent-run` with the `X-Admin-Token` header starts a hosted workflow. Inference can incur Azure charges. Never set these secrets in frontend files or commit them.

On 2026-10-14, the optional packages were installed locally. Imports of `FoundryChatClient`, `SequentialBuilder`, and `AzureCliCredential` succeeded, and a two-agent `SequentialBuilder(...).build()` completed without making a network inference call. The check found that `agent-framework-orchestrations` is a separate dependency; it is now pinned in `requirements-foundry.txt`. This matches the [current Microsoft sequential workflow example](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential) and [Foundry provider guide](https://learn.microsoft.com/en-us/agent-framework/agents/providers/microsoft-foundry). No Foundry project, deployment, credentials, authenticated invocation, model trace, latency or cost measurement is available. The application does not claim that a model has run.


## Issue #14 validation path

Run the pinned SDK compatibility job with `python backend/scripts/foundry_smoke.py --check-only`.
It installs the optional Foundry dependencies, imports the configured client and
orchestration APIs, and builds the two-agent workflow without obtaining a token
or sending a request. The `foundry-compat` GitHub Actions workflow runs only this
no-inference check.

A hosted check requires complete server-side configuration and an explicit
operator confirmation:

```sh
cd backend
python scripts/foundry_smoke.py --confirm-cost --fixture late-winner
```

This starts the existing Tactical Analyst → Story Editor workflow over one
verified synthetic insight. Since the workflow contains two model-backed agent
stages, one run may issue more than one billable model request. The script does
not retry, accepts a 5–120 second timeout (45 seconds by default), and prints
only an allowlisted redacted report: invocation/trace IDs, model deployment
name, evidence packet hash, actual provider and audit status, elapsed time, and
token counts if returned by Agent Framework. It never prints the endpoint,
credentials, prompts, raw provider errors, or raw completion. The SDK does not
provide a dependable per-call cost value here; cost must be checked in the
Foundry/Azure billing view and must not be inferred from tokens.

The command is not a substitute for approval. Do not pass `--confirm-cost`
until the operator has explicitly approved the expected charge. Missing
configuration exits before dispatch. Failed or timed-out calls report a
redacted error type and preserve the deterministic application fallback. A
successful authenticated run and its report must be reviewed and attached to
the issue before it can be closed.

The current [Microsoft Agent Framework response API](https://learn.microsoft.com/en-us/python/api/agent-framework-core/agent_framework.chatresponse?view=agent-framework-python-latest)
exposes optional `usage_details`; this change records only nonnegative integer
input/output/total token counters when returned. It does not claim that every
Foundry deployment returns usage or billing data.

The privileged agent-run route uses the same byte-safe constant-time credential comparison as trace reads. Malformed non-ASCII header bytes are denied rather than raising TypeError. Authorization regressions replace only the provider boundary with a local test function; no hosted inference is invoked. Removing the token revokes dispatch and trace access immediately.

Python dependency verification found older installed AnyIO 4.12.1, certifi 2025.11.12, Pygments 2.19.2 and python-dotenv 1.2.1 affected by PYSEC-2026-4025/4024, PYSEC-2026-4320, PYSEC-2026-2987 and PYSEC-2026-2270 respectively. Requirements now pin the minimal patched compatible versions 4.14.2, 2026.10.19, 2.20.0 and 1.2.2. Apply requirements before testing; a clean resolver scan alone does not certify an older installed environment. Dotenv file-rewriting and the affected Pygments lexer are not public application operations; AnyIO/TLS and CA-bundle findings concern applicable outbound/development paths. No exploit of a hosted deployment is claimed.

## Verified state, 2026-10-25

`python backend/scripts/foundry_smoke.py --check-only` (pinned `requirements-foundry.txt`) returned
`{"authenticated": false, "network_call": false, "offline_stage_order_verified": true, "status": "sdk_compatibility_ok"}`.
No `FOUNDRY_*`, `AZURE_*` or `PULSE_*` variable is set in the development environment and the Azure CLI
is not installed, so no authenticated request was possible. Live validation (#14) remains blocked on
an endpoint, a deployment and written cost approval; the one-shot procedure above is unchanged.
