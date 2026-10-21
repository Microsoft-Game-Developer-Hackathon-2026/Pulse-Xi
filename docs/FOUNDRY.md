# Optional Microsoft Foundry workflow

Privileged trace inspection (`GET /api/agent-traces`) requires the current
`PULSE_FOUNDRY_ADMIN_TOKEN` through the `X-Admin-Token` header. Missing/empty server
configuration returns 503; absent or invalid credentials return 403 without
trace records. Removing configuration also denies access to traces retained in
the process. Authorized reads do not start inference. This change fixes Issue #44;
it does not introduce a public trace viewer or prove hosted-provider execution.

The normal local application uses verified rule-based narratives and makes **zero hosted model calls**. `/health` reports `not_configured`. The optional code path in `backend/app/agents.py` uses Microsoft Agent Framework's `FoundryChatClient` and `SequentialBuilder` per [Microsoft Foundry provider guidance](https://learn.microsoft.com/en-us/agent-framework/agents/providers/microsoft-foundry) and [sequential workflow documentation](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential).

When explicitly enabled, Tactical Analyst and Story Editor run as separate Foundry-backed agents. Their output passes a deterministic Evidence Auditor that checks cited IDs and rejects prose containing invented numeric claims. A rule-based Broadcast Director links the approved packet to a timed cue, and the Fan Personalizer returns verified templates. The trace records these stages and whether they succeeded. The model-generated text is labeled **opinion with verified references**, while score facts remain authoritative deterministic output.

Install optional dependencies with `python -m pip install -r backend/requirements-foundry.txt`. Supply server-side `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL`, `PULSE_FOUNDRY_ADMIN_TOKEN`, and `PULSE_ENABLE_FOUNDRY=true`, then authenticate to Azure with `az login` for local development. Only an explicit `POST /api/insights/{id}/agent-run` with the `X-Admin-Token` header starts a hosted workflow. Inference can incur Azure charges. Never set these secrets in frontend files or commit them.

On 2026-10-14, the optional packages were installed locally. Imports of `FoundryChatClient`, `SequentialBuilder`, and `AzureCliCredential` succeeded, and a two-agent `SequentialBuilder(...).build()` completed without making a network inference call. The check found that `agent-framework-orchestrations` is a separate dependency; it is now pinned in `requirements-foundry.txt`. This matches the [current Microsoft sequential workflow example](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential) and [Foundry provider guide](https://learn.microsoft.com/en-us/agent-framework/agents/providers/microsoft-foundry). No Foundry project, deployment, credentials, authenticated invocation, model trace, latency or cost measurement is available. The application does not claim that a model has run.
