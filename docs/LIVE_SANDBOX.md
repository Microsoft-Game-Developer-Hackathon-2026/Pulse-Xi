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

## Existing analysis integration

The Control Room's **Recorded-event analysis, bookmarks and 3D** section reuses
the existing pass heuristic, deterministic ProofTrail rules, statistics, browser
bookmarks, CSV/JSON exports and lazy observer. All new reads remain under
`/api/sandbox/sessions/{id}` and require the same owner-scoped Bearer credential:

- `GET /analysis?at_second=N`: one committed runtime boundary, projected events,
  cutoff statistics and existing verified insights (`runtime-analysis/1`).
- `GET /pass-difficulty?at_second=N&cursor=0&limit=200`: existing versioned scorer.
- `GET /passes/{event_id}/difficulty` and `/difficulty/evidence`: selected pass
  and independently reconstructed source evidence, with the same cutoff query.
- `GET /analysis-export?at_second=N&category=events|pass|metrics&format=json|csv`:
  existing bounded export service; optional event/team/type filters are unchanged.

Cutoffs after the committed engine tick are rejected (422); wrong-owner identities
remain concealed (404). Reads do not step the engine or copy private runtime data
into the public match library. Analysis responses are no-store. The engine's
default v1 projection supports **5400-second scenarios only**. The explicit native
projection below supplies short-scenario analysis without rescaling time or periods.

The projection preserves engine-generated event identities and each team's
attacking coordinate frame. The observer shows discrete event coordinates only.
Pressure remains excluded from the unchanged pass heuristic; engine positions do
not automatically establish the coverage required by that formula.

Exports include actual scenario/session identity, revision, engine version, cursor,
seed and boundary hashes. These hashes identify the captured authoritative runtime,
which may be later than the inspection cutoff; they are not hashes of a rewound
state or a substitute for the separately downloaded manifest. CSV receives the
same runtime metadata and existing formula-injection escaping. Existing size limits
still reject oversized exports instead of truncating them.

Bookmarks retain only local references and unverified notes, with an additive
`source: runtime` namespace. They require operator reauthentication after refresh;
no token is saved. Runtime and public-match notes cannot overwrite one another
when identifiers coincide. The public Data Hub checker skips private references;
an event beyond the inspection cutoff is not declared deleted. No private runtime
deep link or public note synchronization is claimed.

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

Runtime analysis revision refreshes preserve unsaved event notes and observer
choices within the mounted session. Old-boundary controls are hidden until
the refreshed response arrives. Changing session or credential does not reuse
the previous session's analysis. Unsaved notes are still memory-only; bookmark
or update a note to persist it in this browser.

This supplies the local live Sandbox/Checkpoint/ForkCast product path. It does
not publish an Azure deployment, provision public accounts, run paid Foundry
inference, integrate Blender assets awaiting review, make Unreal cinematics or
submit the team video. Those are separate issues/review/service requirements.
Provisioned operator authentication and deployment gateway rate limits remain
necessary. The simulation's documented football-model limitations still apply.
Shared contract review and normal PR/CI approval remain required before merge.

## Native-period analysis

Optional `projection=native` applies to the existing authenticated analysis, pass
list/detail/evidence and analysis-export routes. Omitting it retains legacy behavior.
No engine transition, RNG, snapshot, state version or canonical hash is changed.

`runtime-native-analysis/1` reports session/scenario/branch identity, revision,
committed cursor, boundary hashes, cutoff and `clock`: actual duration, native
halftime, current engine period and inspection period, in authoritative match
seconds. At halftime inspection switches to period 2, while the halftime event
retains period 1 as emitted before the engine's switch. Either period can occur
exactly at that boundary. `runtime-match/1` preserves roster and duration;
`runtime-event/1` preserves scoped IDs (`session_id-sequence`), sequence, native
tick/match_second, period and observations. Its validator checks native boundaries.
Away x uses the existing attacking-frame transform. Calendar generation time is
null: no observed calendar timestamp exists. Native events are not import packages.

Metrics reuse existing event-count calculations. The response adds cutoff score,
per-team type counts (including carries) and explicit unavailable reasons. Existing
goal/activity insight rules and their verifier use source counts/score and retain
their published definitions. The legacy match-state phase and continuous tracking
remain unavailable. Native
pass geometry reuses synthetic-pass-difficulty/1.0 and its independent verifier;
`runtime-pass-evidence/1` embeds native events. Branch ProofTrail/ForkCast remain
separate and unchanged. No pressure coverage or tactical causality is invented.

Exports reuse analysis-export/1, CSV escaping and existing budgets. Provenance
adds analysis_projection, duration_seconds and halftime_tick; event CSV includes
native fields. Hashes identify the captured boundary, potentially later than the
inspection cutoff, not a rewound state. Future source events are excluded.
The UI chooses native projection for short scenarios and legacy for 5400 seconds.
It reuses event selection, pass evidence, bookmarks, draft preservation, exports
and 2D/3D. Tokens stay memory-only; saved notes restore after re-authentication.

Backend tests run actual engines at 60/120/300/600/1800/2700/5400 seconds, checking
halftime/fulltime, identities, counts, geometry, hashes, JSON/CSV, owner isolation,
concurrent reads and stale mutations. Browser tests create and step a 120-second
runtime, inspect native periods, verify evidence, bookmark/export, switch 2D/3D
and refresh. Use standard backend pytest and frontend test:e2e commands. This
dependent branch requires runtime-forward and native-contract review before main.
## Checkpoint inspection and experiment acceptance

Saved checkpoint inspection uses the existing authenticated checkpoint endpoint.
The Control Room shows the original runtime/scenario, saved tick, revision/cursor,
engine/schema versions, saved state hash, score, possession, actor/pending-action
counts and every RNG stream counter. It downloads the unchanged server envelope;
this is not a client-side serializer or a new upload/restore format. Creation UTC
is unavailable in the current contract and is not invented. Inspection failures
can be retried; changing checkpoint, owner or session invalidates pending reads.
"Inspect saved checkpoint tick" changes only the event inspection cutoff.

Completed/cancelled sessions may save checkpoints because the engine explicitly
permits that operation. A checkpoint with no remaining time cannot start ForkCast;
the UI explains that an earlier checkpoint is required. Restoring a terminal
checkpoint preserves its terminal state and does not create additional play.

Completed ForkCast results support "Verify experiment independently", which gets
the actual experiment bundle and invokes the existing independent verifier.
Verification failure is reported, never relabeled as success. Cited event
drilldown checks sequence, tick, type and actor before offering navigation to
the exact source branch and inspection tick. Runtime and experiment manifests
remain separate from imported-match packages and database backups.

### Reproducible local resource measurements

Run `python scripts/benchmark-runtime-acceptance.py --iterations 3` from the
repository root. It creates disposable SQLite data, checks restored hashes and
independently verifies every measured experiment. It never opens a user database.

Observed 2026-10-21 on Windows 11 10.0.26300, Python 3.13.14, Intel64 family 6
model 186, seed 7, 5,400-second scenario, three samples per boundary:

| Tick | Events | Snapshot bytes | Median save ms | Median restore ms |
|---|---:|---:|---:|---:|
| 0 | 1 | 5,957 | 23.988 | 32.517 |
| 2,700 | 918 | 198,410 | 70.977 | 81.954 |
| 5,400 | 1,819 | 389,573 | 76.414 | 91.178 |

Read-only history at tick 5,399: median 373.793 ms, maximum 434.039 ms. A 120-second
ForkCast horizon took median 718.403 ms for one pair and 1,914.376 ms for three
pairs, with peak traced Python allocations 251,811 and 2,181,750 bytes respectively.
Experiment timing includes `tracemalloc` overhead; these are not process RSS or
HTTP timings. Backend/browser tests were also running on the laptop, so these
load-sensitive samples are acceptance evidence, not a controlled benchmark or
deployment guarantee. The canonical engine is unchanged from runtime base
`fed64f3`; no performance optimization or budget increase was justified.

### Physical Intel Iris Xe verification

The existing headed graphics probe ran against the production build at
`c03435772fa03f988b075ee3d382777544c8be23` on Windows 11, Intel Iris Xe driver
32.0.101.7088, Chromium 156.0.8078.4, viewport 1366×768 and DPR approximately 1.
The actual renderer was ANGLE Intel Iris Xe Direct3D11, not SwiftShader.
[Raw measurements](benchmarks/iris-xe-runtime-acceptance.json) record five-second
active-orbit rAF pacing for Low/Medium/High: 60.18/60.15/60.10 callbacks per second,
median 16.7 ms throughout, p95 17.0/17.0/16.9 ms. Draw calls were 19/39/69 and
triangles 656/10,100/16,764 for the sampled recorded pass.

This probe exercised the recorded-fixture observer served by the runtime build,
not continuous actor simulation or a live-runtime GPU benchmark. It inspected
all profile screenshots, rapid camera/quality changes, three 2D/3D cycles and
30 seconds idle. Errors were empty, the lazy renderer loaded once and no GLB
loaded; #31 remains separate. First renderer-ready was 551.8 ms. Heap before /
after interactions / after idle: 12,970,464 / 21,673,764 / 13,556,690 bytes.
These are browser pacing and bounded heap samples, not GPU timer queries, VRAM
measurements or proof of long-session leak freedom. Keep existing quality defaults.

Reproduce after build/start: set `PULSE_GRAPHICS_HARDWARE=1` and
`PULSE_GRAPHICS_URL=http://127.0.0.1:<local-port>`, then run
`npm run measure:graphics` from `frontend`. The hardware path rejects software
renderer identity. Use isolated databases for verification.

### Disconnect and uncertain operations

An interrupted mutation response may leave a safe retry receipt in browser
memory while the server has already committed it. Staying connected preserves
the explicit idempotent retry. Disconnect clears that private retry body and
comparison/evidence state; reconnect reads the actual owned runtime again.
Disconnect does not undo or cancel committed server work. New commands then
use the refreshed revision rather than replaying a previous operator's request.

The committed observer also offers "Inspect historical engine state". It calls
`GET /sessions/{id}/history?at_tick=N` with the operator credential, presenting
its read-only snapshot, native period, historical state hash and captured source
revision. Replay is performed by the server using its owned checkpoint and
command history. The frontend neither synthesizes states nor rewinds the live
runtime. Cutoff/session/credential changes cancel obsolete requests; the original
response can be downloaded as source evidence, not as a new checkpoint format.
