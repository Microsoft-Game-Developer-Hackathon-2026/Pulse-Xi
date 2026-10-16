> Historical report: statuses and counts below describe the dated build. See [current handoff](SATVIK_INDEPENDENT_HANDOFF.md) and [project status](PROJECT_STATUS.md) for the integrated baseline.

# Satvik implementation audit and integration handoff

Audit date: 2026-10-16. Base: `888a2a9` on organization `main`. The local working tree was clean; organization main matched it, no teammate branches or open PRs were available, and no `backend/app/sandbox/` package existed. The live descriptions of #6, #8, #10, #11, #12 and #27 were read. Prerequisites #2–#5, #7 and #9 remained open without an engine implementation in the repository.

Baseline commands passed: 8 backend tests, strict TypeScript/Vite build, 3 Chromium browser tests. Python 3.13.14, Node 24.12.0, npm 11.6.2. Blender is installed at `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe` and reports 5.2.2 LTS; it is not on PATH. No asset production or export has been claimed.

## Issue plan and current scope

| Issue | Readiness / complexity | Implemented or next files | Contracts and tests |
|---|---|---|---|
| #27 Pass difficulty | Independent fixture slice implemented; M | `backend/app/pass_difficulty.py`, read-only routes in `main.py`, `frontend/src/features/passes/`, focused pytest and browser tests | Versioned reduced geometry formula and independent verifier; see `PASS_DIFFICULTY.md`. Branch adapter awaits engine contracts. |
| #10 Control Room | Partial working fixture workspace; XL overall | `frontend/src/features/sandbox/`, narrow integration in `App.tsx`, `sandbox.spec.ts` | Existing `/generate`, match detail/events, replay metrics, evidence and cues. Full live scenario flow awaits engine APIs. |
| #6 Checkpoint/restore | Blocked by #3/#4/#5; L | Proposed `backend/app/sandbox/checkpoints.py` only after state contract is reviewed | Need complete state, RNG/queue serialization, legal tick boundaries and ownership. Then add isolated save/restore and continuation parity tests. |
| #8 ForkCast | Blocked by #6/#7/#9; XL | Experiment API/UI after checkpoint/intervention/manifest contracts | Paired trials, branch isolation, recomputable comparisons and cancellation tests. |
| #11 3D observer | Deferred until core sandbox works; L | Lazy observer isolated from 2D when the observer contract exists | Sparse fixtures permit discrete event markers only. Need authoritative frames for any continuous movement, gap/reconnect and fallback tests. |
| #12 Blender pipeline | Deferred after #11 asset contract and #23 rights review; M | Original generator/export script, source/export assets and manifest | Blender executable is available. Need orientation/scale/LOD budgets agreed with observer, real exports and measured load tests. |

The #27 branch is `feat/27-pass-difficulty`, PR #28. The #10 branch is `feat/10-sandbox-control-room`, stacked on #27 for a combined local preview. The #10 PR should target the #27 feature branch until #28 is merged; its diff must contain only the workspace changes. Neither PR authorizes a merge or issue closure.

## What the Sandbox Lab currently does

Use `/#/sandbox`. Generate a precomputed fictional replay from a validated seed through `POST /api/matches/generate`. The currently supported generator fixes the teams; no unenforceable formation or tactic options are shown. Existing match replay, pitch, metrics, ProofTrail, pass inspector and studio remain shared components. The new timeline filters recorded events by team/type, supports keyboard selection and seeks to the event clock. It shows only events already available at that clock. Goal markers and cue information in this workspace are also bounded by the replay clock.

The saved custom match ID can be resolved again after refresh through the real match endpoint. The seed identifies a reproducible fixture on this build; this is **not** a complete experiment manifest. Replay transport remains the existing browser view of immutable events. It does not claim to pause a running server simulator or save RNG state. A visible availability explanation identifies the live controls that are not connected.

Match and replay requests are aborted when superseded. Metrics, tactics and recaps render only when their returned match/cutoff matches the selected view, preventing a late response from overwriting current data. Generation prevents duplicate submissions, aborts on navigation or match change, and preserves the current replay on failure.

## Contracts required from Diyan

These are proposed integration requirements, not implemented routes or an alternative engine design. Confirm names and shapes against #2 before adding production DTOs:

- Scenario creation/resolution from #3: complete validated configuration, seed derivation, scenario ID, engine/schema version and supported tactical bounds. Do not use the legacy fixture generator as a substitute.
- State snapshot from #4/#5: authoritative tick/period, revision, event cursor, score, possession, ball state, lineups/actors, tactical state, complete RNG state/counters and pending action queue. Provide an immutable serializable snapshot plus restore/advance hooks. The serializer must capture the **actual engine's complete state**, not a guessed subset.
- Runtime operations: legal pause/step/seek/resume boundaries and whether speed is a presentation control or a server action. Responses must include authoritative tick/revision/cursor; stale writes need a stable conflict code.
- #7 interventions: allowed operation schema, ownership, effective tick, prior/next values, stale-revision semantics and deterministic intervention log. #7 depends on #6 restore behavior; agree the engine adapter first to avoid a circular implementation dependency.
- #9 canonicalization and manifest: hash algorithm, resolved inputs, version compatibility, branch ancestry and paired-seed derivation. Checkpoints should reuse that format rather than introduce a second provenance scheme.
- Ownership/session boundaries: how an isolated runtime is created and authorized. Checkpoint restore and experiments cannot expose mutable shared demo sessions.

Illustrative response shape only: `{scenario_id, branch_id, tick, revision, event_cursor, engine_version, schema_version, state, provenance}`. `state` must be defined by the engine and include RNG/pending queue. A checkpoint envelope can then bind this exact serialized state to its event boundary and content hash. No save/restore API is exposed until exact continuation can be demonstrated.

## Cross-team integration

Mahir receives pass DTOs/verifier now; branch comparison metadata follows #8 and the shared #16 evidence format. This work does not alter his Insight categories or agent code. Vishwam can use the current FastAPI/Vite launch path and existing environment configuration; no new paid service, deployment or secret is required. The cold-start SQLite migration race discovered by parallel browser tests was repaired in #28 with a writer lock and bounded WAL promotion retry.

## Validation and local journey

From the repository root, `./scripts/start.ps1` uses the existing local startup. For manual development, run `python -m uvicorn app.main:app --reload --port 8000` in `backend` and `npm run dev` in `frontend`.

Run backend tests with `python -m pytest tests -q -p no:cacheprovider` in `backend`. Run `npm run test:e2e` in `frontend` for production build, strict TypeScript and Chromium journeys. No separate lint/format script is configured. Test fixtures and browser failure injection use real application endpoints; unavailable live-engine journeys are not marked passed.

Working journey: open Sandbox Lab → generate seed 0 → seek/step/play recorded match → filter/select a pass → inspect difficulty and evidence → change Favorite Player lens → reload the same custom replay. Checkpoint, intervention and fork journeys remain blocked and are not represented as completed actions.

Combined branch validation on 2026-10-16: **23 backend tests and 10 Chromium browser tests passed**, with the browser suite using a newly created temporary SQLite database and three workers. Production build output: JavaScript 266.08 kB (82.43 kB gzip), CSS 28.42 kB (7.43 kB gzip). The fixture setup screenshot was generated by the actual browser test and inspected. Windows Uvicorn logged a connection-reset callback during the deliberately aborted request test; the client cancellation and all assertions passed. No live-engine continuation, branch experiment, 3D performance or Blender export test has run.

Independent phase follow-up: the fixture API is now paginated rather than truncated at 1,000 events. Retry connection preserves the replay clock and cancels superseded reads. Selecting a timeline pass synchronizes the team, pitch and difficulty inspector; selecting a pass in the inspector seeks the shared replay. Geometry-only v1 pass packets are cached at the last visible pass boundary, so a replay tick with no new pass does not refetch the same score list. Future boundaries remain hidden on backward seek. The formula and backend contracts in #28 were reviewed without a scoring change. Production build and **12 browser tests pass** for this increment.

The independent read-only portion of #11 is now implemented on `feat/11-three-d-observer`, stacked on #29. It uses recorded event snapshots only and has camera presets, lazy loading, quality controls and resilient 2D fallback. Full combined validation: **23 backend and 15 browser tests passed**. See [3D observer contract and measured results](3D_OBSERVER.md). This supersedes the earlier deferral of event-only 3D; modeled actor frames and all live simulation operations remain unavailable.
# Replay audit corrections — 2026-10-16

Replay pagination now validates page shape, bounded page size, unique event IDs, strictly increasing sequence cursors, nondecreasing clocks and finite normalized coordinates before publishing a complete stream. The browser caps one replay at 100,000 events and rejects an aborted read even if a transport finishes late. Tied timestamps remain valid. Streams that change during pagination still require a future server revision/snapshot contract; this client check does not create one.

The tactical pass map supports pointer and keyboard inspection; shots support Enter/Space seeking. Event stepping preserves source identity through events sharing a timestamp instead of skipping them. Replay-time metrics still include all events at that timestamp. Proof drawers now contain keyboard focus, close on Escape, restore focus to the opener and cancel superseded proof requests.

Generated replay proof uses `GET /api/matches/{match_id}/insights/{insight_id}/evidence?at_second=N`. It resolves the selected match through the existing match access path and rejects wrong-match or future insights. The legacy global explain endpoint remains available. This repairs custom fixture proof lookup without modifying shared evidence calculations or agent contracts.
