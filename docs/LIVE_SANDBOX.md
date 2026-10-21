# Live Sandbox, checkpoints and ForkCast

Main `d1d099e` integrated the real Control Room at
`/#/runtime` and implements the remaining server progression, observer and paired
experiment contracts. Other feature PRs retain their own scope and review boundaries.
Existing fixture replay remains at
`/#/sandbox`, with all previous analysis/data-hub features preserved.

## Saved scenario library and archives

The existing `ScenarioConfig` (`sandbox/1`, `zone-engine/1`) is still the sole
simulation input. `build_scenario` resolves defaults once, hashes its complete
JSON payload and derives `scenario-<sha256>`. Names, colors and the preset label
are already part of that payload, alongside all gameplay parameters. Sorted keys,
compact separators, ASCII escaping and rejection of nonfinite numbers define the
canonical JSON. Whitespace and object-key ordering do not affect identity.

`ScenarioArchive` in `app/sandbox/scenario_archive.py` is a separate portable
record, not a field in EngineState. It contains:

| Field | Contract |
|---|---|
| archive_version | `scenario-archive/1` |
| scenario | Existing Scenario: content-derived scenario_id, config_hash, complete resolved config |
| scenario.config | Engine/schema versions, seed, preset origin, fictional rosters, tactics, even duration, neutral-dry assumption |
| rng_algorithm | `sha256-counter/1` |
| rng_derivation | `sha256(engine_version:seed:stream); sha256(key:counter)` |
| rng_streams | Exactly `actor`, `decision`, `duel`, `finish`, in that order |
| created_at_utc | ISO UTC string with `Z`, or null when original creation time was not recorded |

Creation UTC and the archive wrapper never enter configuration/state/event hashes.
The algorithm and named streams are the existing engine mechanism: SHA-256 of
UTF-8 `engine_version:seed:stream` supplies a stream key; SHA-256 of ASCII
`key:counter`, interpreted big-endian modulo the requested bound, supplies a draw.
Only that stream's counter advances. No mutable global RNG or alternate engine
is added. Supported-build reproducibility is tested; broader platform guarantees
and real-football prediction accuracy are not claimed.

### Scenario API

All paths below begin `/api/sandbox` and require the existing operator bearer
credential. Ownership is taken from the validated credential, never JSON input.
Foreign-owner IDs are concealed as 404, including content-derived IDs.

| Method/path | Input -> success response (200) | Consumer |
|---|---|---|
| GET /presets | none -> four resolved ScenarioConfig values (unchanged) | Preset selector |
| POST /scenarios | ScenarioConfig -> Scenario (unchanged) | Save builder/create runtime |
| GET /scenarios/{id} | none -> Scenario (unchanged) | Existing clients |
| GET /scenarios | none -> ScenarioSummary[] | Saved library, independent of runtime sessions |
| POST /scenarios/import | ScenarioArchive or raw ScenarioConfig -> persisted ScenarioArchive | Text/file import |
| GET /scenarios/{id}/archive | none -> persisted ScenarioArchive | Load/review/download |

The list is ordered by scenario ID, limited to 100, and returns only owned IDs,
hashes, seeds, preset labels and creation times. The existing **global** runtime
capacity remains 100 scenario records, including identical content under different
owners. There is no new table of configs or scenario deletion operation. The new
list/import/archive responses use `Cache-Control: no-store`.

Import rebuilds Scenario from its validated config and compares both its hash and
ID; mismatches return 409 `scenario_hash_mismatch`. A different stored payload at
the same owned ID returns 409 `scenario_conflict`. Identical imports are idempotent
and return the first stored record, retaining its creation metadata even if the
incoming timestamp differs. They work at capacity; new content returns 429
`scenario_limit`. Unsupported versions/streams, unknown fields, invalid timestamps
and invalid config return located FastAPI 422 errors. Malformed JSON returns 422;
duplicate keys, nonfinite numbers and excessive nesting return 400. Bodies over
2,000,000 bytes return 413 before schema parsing. Authentication failures retain
403/503; SQLite write failures retain 503. These validation/boundary errors do not
all use the runtime `{detail: {code}}` family; clients handle located arrays and
string details as well.

Archives are unsigned: recomputing identity proves configuration consistency,
not authorship, football truth or the authenticity of an imported timestamp.
Owner IDs, credentials, sessions, checkpoints, analyst notes and agent traces are
not exported. Raw-config POST remains supported. The UI sends original import
text without parsing/restringifying, preserving server duplicate-key detection.

### Persistence and recovery

Runtime SQLite advances through atomic `0 -> 1 -> 2 -> 3` steps. Schema 3 adds
`scenario_metadata(owner,id,created_at_utc)` referencing the existing composite
scenario key. Old scenario/session/command/event/checkpoint/run/experiment bytes
are preserved. Migrated scenarios receive null timestamps, never invented dates.
API-created records receive server UTC; archive imports retain source provenance.
Scenario and metadata inserts share the same `BEGIN IMMEDIATE` transaction; a
metadata failure rolls both back. Concurrent identical saves retain one timestamp.

The migration DDL/backfill/version marker commit together. Interrupted schema-3
migration rolls back to schema 2 and retries on next open; an earlier completed
migration step can remain committed. Trusted offline runtime backup accepts
versions 1/2/3 and validates the added metadata. Old backups remain readable and
migrate on application open. Older schema-2 binaries reject schema 3; rollback
requires matching pre-upgrade backups/builds, not an automatic down-migration.
Imported-match SQLite remains separate, at library schema 2, with its own backup
and transaction semantics.

### Builder and policy limits

Connect in `/#/runtime`, choose/edit a preset and **Save scenario** to persist
without creating a session. **Saved scenario** and **Load saved scenario** work
without finding a runtime first. Review the saved config/provenance; download
always fetches that persisted archive, not a possibly edited draft. Save draft
changes before exporting them. Upload or paste an archive/raw config and explicitly
validate/load it through the backend. Full fictional rosters remain editable via
**Copy builder into JSON editor**; both teams have visual formation/tactic controls.
Refresh clears credentials; reconnect to reload the owner-scoped library.

Ranges remain: seed 0..2147483647, 11 players per team and 22 unique player IDs,
passing/finishing/defending and every numeric tactic 0..100, formations 4-3-3 /
4-4-2 / 3-5-2, even duration 60..5400. Only neutral/dry conditions are modeled;
there is no separate weather, pitch physics or intensity scalar. Tempo affects
decision spacing; server progression rate affects scheduling, not outcomes.

Presets are complete configs: Balanced uses defaults (50 tactics); High Press
sets home press 90/tempo 80/risk 65; Late Comeback sets home 3-5-2/directness 85/
tempo 90/risk 90; Stalemate sets both compactness 90/tempo 20/risk 10. All other
values remain defaults. Late Comeback is an aggressive kickoff strategy, not a
forced late-game score. No preset guarantees a result. The preset label is
provenance, not a server-side hidden override of submitted tactics.

The existing tactical model reads only current state: roles weight actor selection;
pressing gates pressure attempts; compactness affects opponent pass completion;
directness affects progress; tempo affects decision intervals; risk affects shot
selection and pass completion. Interventions apply at the next tick before restart,
period boundaries and decisions. `policy_revision`, intervention receipts, RNG
state and replayable command manifests identify the active policy; no new hidden
future-state reader is introduced. Substitutions and tracking motion remain absent.
At most ten eligible non-goalkeeper candidates per team are inspected (weighted
list at most 30 entries), and a command advances at most 300 integer seconds.

### Reproducible verification

Retain `test_authoritative_engine.py` (fulltime/goldens, v1 references/score parity,
ordering, checkpoints, paired seeds) and `test_runtime_integration.py` (jobs,
ownership, observer, migrations/recovery). `test_scenario_library.py` adds archive
roundtrip into a fresh DB, key-order/hash/RNG isolation, version/roster/tampering
rejection, owner lists/capacity, atomic metadata writes/migrations and backup tests.
`frontend/tests/scenario-library.spec.ts` exercises real save/list/reload, all four
presets, file import/export, errors and equal event hashes from two fresh sessions.
No golden fixture was rewritten.

Run backend pytest, both file verifiers and pip check as documented below. Frontend
`npm.cmd run test:e2e` runs strict TypeScript, production build and Playwright;
also run `npm.cmd run validate:assets` and `npm.cmd audit --json`. For offline
measurements without rewriting goldens: `python scripts/sandbox-benchmark.py --samples 5`
from the repository root. Local 2026-10-21 Python 3.13.15 measurements: 20 fulltime
runs across four presets/five seeds took 0.084..0.147 s each; configuration build
p95 was 0.057 ms (default) and 0.058 ms (maximum supported names/attributes).
A profiled run evaluated 777 decisions, mean cumulative 53 microseconds each.
Profiler overhead is included. These measurements do not establish deployment
SLAs; work/capacity limits and cancellation remain tested separately.

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
current v1 projection supports **5400-second scenarios only**. Shortened scenarios
keep their native controls/checkpoints/ForkCast; this panel explicitly reports
unavailability rather than rescaling timestamps or periods.

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
