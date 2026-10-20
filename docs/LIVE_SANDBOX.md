# Live Sandbox, checkpoints and ForkCast

This follow-up to the engine foundation connects the real Control Room at
`/#/runtime` and implements the remaining server progression, observer and paired
experiment contracts for #3/#4/#6/#7/#8/#9/#10. It is a separate integration
branch; PRs #31/#32/#33 are untouched. Existing fixture replay remains at
`/#/sandbox`, with all previous analysis/data-hub features preserved.

## Start and use

Provision an operator credential before starting the existing app:

```powershell
$env:PULSE_RUNTIME_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
.\scripts\start.ps1
```

Open `http://127.0.0.1:8000/#/runtime`, enter that credential and connect. For
multiple operators use the owner-to-distinct-token `PULSE_RUNTIME_TOKENS` mapping
described in [the core contract](AUTHORITATIVE_ENGINE.md). Every runtime HTTP
route and observer connection is authenticated and owner-scoped. No server token
is bundled into JavaScript. Credentials stay in component memory, never URLs,
localStorage, sessionStorage or downloaded artifacts. Reconnect requires entering
the credential again; only the last non-secret runtime ID is remembered.

1. Open Scenario builder. Choose a preset, seed, duration, fictional team names,
   formation and initial home tactics. Advanced JSON supports full individual
   rosters/attributes and away tactics, with authoritative server validation.
2. Create a scenario; it opens a paused runtime at kickoff. Step by 1..300 seconds
   or choose a server progression rate and Run on server.
3. Pause, save an exact checkpoint, change a tactic, step to its effective tick.
   The audit shows the previous/new value and effective time.
4. Restore the checkpoint as a new branch. The parent's state/history is retained.
   Switch between owned runtimes through Runtime / branch.
5. Select a checkpoint, variation, 1..5 paired trials and 1..600 seconds of future
   play, then Run paired ForkCast. The baseline is unchanged; the variation uses
   the team/field/value displayed in the form. The parent is never advanced.
6. Inspect means, ranges and differences; open a source event or a trial branch.
   Download runtime/experiment manifests and independently verify them.

The committed-event time slider only inspects events already emitted at or before
the cutoff. It does not rewind the authoritative clock. The 2D pitch shows actual
discrete event origins/endpoints; it does not fabricate continuous player frames.
Controls are keyboard usable, responsive and respect reduced motion. Pending
mutations are single-flight. An uncertain network/server response retains the
original request/operation ID for safe retry; a new mutation cannot overwrite an
unresolved operation. Stale revisions are explicit and can refresh current state.

## Server progression and lifecycle

The FastAPI lifespan starts a bounded worker when runtime authentication is
configured. `PULSE_RUNTIME_DRIVER=0` explicitly disables it for offline/testing
use. It polls durable run/experiment rows at 250 ms intervals, processing at most
four run commands and two experiment commands per pass. Fair ordering favors
less-progressed jobs. UI timers only fetch state; they do not advance football.

A run specifies a target tick and 1..60 match seconds per server update. Every
advance is an ordinary revision-checked, durably recorded engine command. The
server may pace slower under load; wall-clock delay never decides a football
outcome. Accepted runs continue if the browser closes and recover after server
restart. Pause cancels the current run driver and pauses its runtime. Re-running
uses a new job from the current revision. External mutations cause a stale job
to stop rather than silently adopt a different state.

The server checks the remaining 2048-command budget before accepting a run or
trial plan. An overlong low-rate run fails with run_exceeds_command_budget before
changing state; choose a larger seconds-per-update value. Existing history is
never discarded to make room for more commands.

Each job command ID is derived from its job and progress index. Progress updates
use SQL compare-and-swap. Multiple server processes can retry the same command;
only one engine mutation commits. A crash after the engine commit but before the
job progress commit reuses the original receipt. Cancellation prevents future
scheduled work; a currently executing bounded command can finish before the
pause/cancel acknowledgment. It cannot append gameplay after a successfully
committed terminal cancellation. Completed/cancelled evidence is retained.

## Additional HTTP and WebSocket routes

All HTTP routes use `Authorization: Bearer <operator-token>` and the
`/api/sandbox` prefix, alongside the [foundation routes](AUTHORITATIVE_ENGINE.md).

| Method | Path | Behavior |
|---|---|---|
| GET | `/sessions` | Owner's bounded runtime/branch summaries |
| GET | `/sessions/{id}/checkpoints` | Exact checkpoint markers for that owned runtime |
| GET | `/sessions/{id}/history?at_tick=75` | Read-only state from nearest checkpoint plus deterministic input replay; rejects future ticks |
| POST | `/sessions/{id}/runs` | Create/reconcile a durable bounded server run |
| GET | `/sessions/{id}/runs` | Recover owned run jobs after reconnect |
| GET | `/runs/{id}` | Run state/progress/error |
| POST | `/runs/{id}/cancel` | Cancel driver and pause runtime |
| POST | `/experiments` | Create/reconcile paired-trial job |
| GET | `/experiments` | Recover the owner's experiment jobs/results |
| GET | `/experiments/{id}` | Experiment status, branch IDs and progress |
| POST | `/experiments/{id}/cancel` | Cancel job and terminally cancel its existing child runtimes |
| GET | `/experiments/{id}/comparison` | Recomputed and independently verified comparison |
| GET | `/experiments/{id}/manifest` | Complete file-verifiable experiment bundle |
| POST | `/experiments/verify` | Independently verify an uploaded bundle (existing 2 MB HTTP body limit) |
| WS | `/sessions/{id}/observe?cursor=0` | Authenticated authoritative snapshot/delta stream |

Run request example (revision must be current):

```json
{"operation_id":"run-1","expected_revision":3,"target_tick":5400,"ticks_per_step":15}
```

Experiment request example (revision belongs to the immutable paused checkpoint):

```json
{"operation_id":"experiment-1","checkpoint_id":"<owned checkpoint ID>","expected_revision":3,"trials":3,"horizon":300,"baseline":[],"variation":[{"team_id":"home","field":"pressing","value":100}]}
```

Run/experiment replies include authoritative session identity, tick, revision and
event cursor, plus job progress. Exact duplicate creation requests reconcile to
the same job's current progress; changed reuse conflicts. Job errors are explicit,
including stale_revision, invalid boundaries, capacity and field_already_pending.
Limits per DB: 100 runs and 10 experiments, in addition to existing session and
checkpoint limits. Failed/cancelled partial trials never produce a verified table.

WebSocket first frame must be exactly `{"token":"<operator-token>"}` within five
seconds and 4096 characters. The token is never in a URL. Origin must match this
server or the configured local development origins; origin alone grants no
authorization. Credentials are revalidated while connected, including revocation.
An initial `{kind:"snapshot",view:RuntimeView}` includes committed history. A
subsequent `{kind:"delta",view,from_cursor,events}` has the latest state without its
duplicate events array and only events after from_cursor. Append only when the
local cursor agrees; otherwise refetch authoritative state. Reconnect sends a
fresh snapshot. The UI falls back to authenticated state polling. Vite proxies
WebSocket upgrades for `/api`. No credentials are exposed to observers before
authentication, and inaccessible sessions close without exposing state.

## Trial derivation and independent verification

Each arm restores the same immutable checkpoint. Before future decisions it
records a `trial` command with trial_index 0..4. This explicitly skips
`trial_index * 4096` counters in each owned RNG stream, preserving keys, seed and
all other checkpoint state. Both arms of a pair receive the same offset. The
maximum 600-second horizon consumes fewer than 4096 draws per stream, so the
future blocks for different trials do not overlap. These are paired future RNG
blocks, not falsely relabelled new initial scenario seeds. Offsets, initial seed,
actual commands, checkpoint ancestry and output hashes appear in the bundle.

Per team, the comparison calculates possessions (event-derived distinct possession
IDs), pressures, recoveries, turnovers, successful final-third entries, shots,
goals, activity and actor involvement. Activity weights pass/carry/pressure as 1,
recovery as 2 and shot as 3; it is a transparent synthetic activity proxy.
Player involvement counts attributed events per trial. Means use six decimal
places; min/max are observed trial counts; difference is variation minus
baseline. No significance, confidence interval or calibrated probability is
invented. A measured zero remains zero, with no fabricated source references.

Source references contain trial, arm, runtime ID, event sequence, tick, type,
actor and contribution. Calculations use all actual source events. A metric's
interactive evidence preview is capped at 40 references and reports whether it
is truncated. Full branch manifests/events remain available for verification.

The comparison uses the exact committed end revision of every trial. Subsequent
manual progression of a child runtime cannot rewrite its previous experiment
result. Historical manifests reconstruct that boundary from recorded commands.
The UI recovers active runs and the selected parent's latest experiment after
re-authentication or switching back to that parent runtime.
The experiment verifier checks the parent snapshot, each branch's independent
replay, exact arm command plans, paired offsets, ancestry and recalculated
comparison hash. An additional implementation digest binds the trial planner and
comparison code. Bundles are integrity/reproducibility evidence, not signatures.

```powershell
# From backend; no DB, operator token or network required
python -m app.sandbox.verify_manifest ../docs/examples/sandbox/experiment.json
python -m app.sandbox.verify_experiment ../docs/examples/sandbox/forkcast.json
```

The experiment CLI accepts files up to 20 MB. Large valid downloads may exceed
the conservative 2 MB HTTP verification limit; use the independent CLI in that
case. Executed examples include forkcast.json and comparison.json, regenerated
by `python scripts/engine-evidence.py` using actual engine/API/worker execution.

## Migration, backup and validation

Runtime schema 1 migrates atomically to schema 2, adding runs and experiments.
Sessions/events/checkpoints/receipts remain intact, including original retry
fingerprints. The data-hub DB stays schema 2 and is never reinterpreted. Back up
the separate runtime file before upgrading; older runtime code rejects schema 2.
The runtime backup utility supports schemas 1 and 2, validates control records,
and preserves durable jobs across verified restore to a NEW file. Preserve the
operator mapping and restart clients at the restored authoritative boundary.

Validation commands:

```powershell
cd backend
python -m pytest tests -q -p no:cacheprovider
cd ../frontend
npm run test:e2e
```

Tests cover real UI/API workflows, server progress without a browser clock,
resume across process restart, concurrent workers, lost progress commits,
cancellation, stale external mutations, snapshot/delta/revocation, exact seeks,
paired reruns, independent bundle replay/tampering, zero results, immutable
comparison cutoffs, atomic schema upgrade, backup recovery, keyboard/mobile
behavior, credential non-persistence, duplicate blocking and the full previous
application regression suite.

## Remaining project boundaries

This supplies the local live Sandbox/Checkpoint/ForkCast product path. It does
not publish an Azure deployment, provision public accounts, run paid Foundry
inference, integrate Blender assets awaiting review, make Unreal cinematics or
submit the team video. Those are separate issues/review/service requirements.
Provisioned operator authentication and deployment gateway rate limits remain
necessary. The simulation's documented football-model limitations still apply.
Shared contract review and normal PR/CI approval remain required before merge.
