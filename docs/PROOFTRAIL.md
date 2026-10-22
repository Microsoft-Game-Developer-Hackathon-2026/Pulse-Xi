# Sandbox ProofTrail v1

The authenticated authoritative sandbox runtime already records immutable checkpoints, branch ancestry, interventions, replayable command logs and verification manifests. This contract adds a branch comparison that is computed from those records; it does not modify the legacy match replay or insight routes.

## Endpoint

The browser comparison form holds credentials only in memory. Clear, changes to
any comparison field (including credentials), and unmount cancel pending requests.
Existing results are invalidated on edits; late success or failure responses cannot
replace the cleared or edited state. A new explicit comparison can be submitted
after cancellation. This does not revoke server credentials or undo server work.

`GET /api/sandbox/sessions/{branch_session_id}/prooftrail?baseline_session_id={session_id}&intervention_id={operation_id}&at_tick={tick}`

The endpoint uses the existing sandbox bearer-token authentication. Both sessions and the referenced checkpoint must belong to the authenticated operator; cross-owner identities remain concealed as 404. A caller cannot submit metric values or evidence IDs.

The service:

1. Loads the branch and baseline from the same owner's durable runtime store.
2. independently verifies both replay manifests against the current engine implementation.
3. proves the branch descends from a checkpoint created by the selected baseline session, matching the checkpoint ID and snapshot hash.
4. requires the named intervention to exist on the branch and take effect after the checkpoint.
5. checks that `effective_tick < at_tick` and that both sessions reached the requested tick.
6. recomputes metrics from authoritative events in both branches.

Errors use the established sandbox `{"detail":{"code":"..."}}` form: 403 unauthorized, concealed 404 for inaccessible sessions/checkpoints, 409 for invalid manifests or checkpoint mismatch, and 422 for unrelated baselines, wrong scenario, missing intervention, or invalid windows.

## Response: `sandbox-prooftrail/1`

The response identifies scenario, branch, baseline, checkpoint, intervention and a digest of both verified manifests. It contains a pre-intervention context window and a shared post-intervention match-time window for each session. Every event used in a metric calculation is cited as `{session_id}-{sequence}` within its corresponding window.

For each team, the v1 metrics count goals, shots, recoveries, turnovers, passes and carries in half-open intervals `[start_tick, end_tick)`. The before window is the same duration as the post window where match time permits, ending at the intervention's effective tick. At the beginning of a match it is clipped to tick zero and reports its actual bounds.

`metric_deltas_by_team` is descriptive difference-in-differences:

`(branch post - branch pre) - (baseline post - baseline pre)`

It is calculated from per-team event counts; it is not a calibrated treatment effect. The response explicitly states that it is a single-run synthetic-engine association, not a real-world causal prediction. One deterministic run per branch provides no statistical uncertainty estimate. This contract does not manufacture confidence intervals or claim multiple-trial evidence.

The verifier rejects fabricated or stale claims at source: callers cannot provide claims, and both complete manifests are independently replayed before comparison. The endpoint reports the exact source verification state and manifest digest. It does not claim that downstream narrative text has been verified; the response is numeric and rule-computed.

## Limits and security

The endpoint inherits existing runtime limits (20,000 events per session, 32 checkpoint ancestors, bounded request bodies), owner scoping, and transactionally persisted source history. The response is capped at 4,000 cited metric events across the four context/comparison windows; larger windows return an actionable 422 and should be narrowed. It does not expose other sessions, hidden branches, token values, or local paths. A future narrative explainer must consume this verified packet and undergo separate claim verification; no model or provider is invoked here.

## Verification coverage

`backend/tests/test_prooftrail.py` exercises a real checkpoint fork and intervention, verifies both manifests, checks source citations and uncertainty language, confirms the authenticated route, rejects missing authentication and rejects a baseline that is not an ancestor. The existing authoritative engine suite continues to cover deterministic replay, checkpoint restoration, intervention immutability, manifest tampering and owner isolation.

The Sandbox Lab includes a read-only comparison form for operator-provided baseline session ID, branch session ID, intervention operation ID and cutoff tick. The bearer token is held only in component memory, sent to the same-origin authenticated endpoint, and never placed in a URL or localStorage. Session IDs must be obtained from the existing authenticated runtime workflow. The view shows before/after windows, metric deltas, manifest digest, verification status and event citations. It does not create sessions, branches, interventions, or approval state.

Authenticated branch comparison responses use `Cache-Control: no-store` alongside owner-scoped access and browser request cancellation. Private comparison results must not be reused from HTTP caches after credential changes.
