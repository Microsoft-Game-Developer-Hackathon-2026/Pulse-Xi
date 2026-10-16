# Satvik independent integration handoff — 2026-10-17

## Executive status: CONDITIONALLY READY

Working independent replay, pass intelligence and procedural 3D are integrated through normal GitHub PR merges. The original asset kit still requires Vishwam's explicit release approval; checkpoint/ForkCast preparations remain stacked behind it. No engine or authenticated AI completion is claimed.

Starting main: `888a2a937667e6a5cfcc8b984bc7ca2825065835`. Integrated feature baseline: `79d1211a6cf8bda2486ce770cb2be3475f6a9bcf`. This document is delivered by a separate documentation PR; its merge commit is the subsequent canonical main revision, discoverable from GitHub/history. No direct main push, force push, branch deletion or teammate change was performed.

## PR merge-readiness matrix

All six heads were inspected for diff scope, ancestry, comments, reviews, draft state, mergeability and checks. No human reviews/comments were recorded. Repository rulesets returned an empty list; the main protection endpoint returned 404. No admin bypass was used. The authorized agent reviewed the implementation and tests; that is not a fabricated human approval.

| PR / issue | Source → target at inspection | Head | Decision and result |
|---|---|---|---|
| #28 / #27 | feat/27-pass-difficulty → main | fdd0de1 | Verified read-only scoring/evidence; merged `6fe9ccd` |
| #29 / #10 | feat/10-sandbox-control-room → #28 branch | 5eea5cf | Ready for stable fixture subset; clarified scope, marked ready, retargeted main, merged `5c63adf` |
| #30 / #11 | feat/11-three-d-observer → #29 branch | bade6a2 | Verified procedural event observer; retargeted main, merged `79d1211` |
| #31 / #12 | feat/12-blender-assets → #30 branch | ee74d14 initially | Retargeted main; OPEN pending Vishwam #23 approval. Hardware probe tooling added in `4d0a24f` |
| #32 / #6 | prep/6-checkpoint-contracts → #31 branch | c7eebe1 initially | DRAFT; safe metadata preparation, but inherits unapproved assets. No real continuation |
| #33 / #8 | prep/8-forkcast-comparison → #32 branch | 62c2978 initially | DRAFT; isolated comparison preparation, inherits #31. No real experiments |

Successive retargeted diffs were inspected before merging #29/#30; normal merge commits preserve ancestry. Existing feature branches are retained. Issues #6/#8/#10 remain incomplete and open. #31 approval is a real gate, not a technical justification to bypass review. Extracting tiny preparation-only PRs now would add review overhead without unlocking engine execution; keep the existing stack until review arrives.

## Feature inventory

| Feature | Main | Remaining boundary |
|---|---|---|
| Pass difficulty | Implemented/verified geometry heuristic, replay cutoff, evidence recomputation, player summaries | Pressure unavailable; future branch-scoped adapter requires engine contracts |
| Sandbox Lab | Useful fixture generation/replay, pagination, event selection, error recovery, pass evidence | Not authoritative runtime pause/step/tactics |
| 3D observer | Procedural stadium/pitch, five cameras, three profiles, evidence, lazy loading and fallback | Sparse event locations only; no continuous modeled frames |
| Blender pipeline | Not merged; seven source/export records verified on #31 | Vishwam licensing/provenance release review |
| Checkpoints | Not merged; metadata/proposal tests on #32 | Complete engine state, RNG/queue and isolated continuation unavailable |
| ForkCast | Not merged; isolated fixture display/contract tests on #33 | Checkpoints, interventions, paired trials, manifests and auditor unavailable |

## Prior QA evidence

The comprehensive bounded audit was actually executed and committed, not inferred from a prompt. `DEEP_AUDIT_REPORT.md` on #33 records 12 reproduced fixes: pass attribution 422 handling, replay-page validation, same-second event stepping, pitch keyboard interaction, evidence dialog focus/cancellation, responsive overflow, observer identity validation, asset binary/metadata validation, checkpoint unknown-input/calendar validation, comparison consistency, generated-match evidence lookup and canonical seed identity.

Relevant fixes from #28–#30 are included on main. Asset/contract fixes remain in the child stack. The graphics measurement tool is shared into this integration PR with procedural-scene support; it creates no engine API or asset dependency. The old reports are historical evidence, not current status or a claim that all tests were repeated on every revision.

## Verification evidence

Fresh initial combined stack `62c2978`: backend **34 passed (2.44s)**; application/API/metadata/material/browser suite **32 passed (42.9s)**; isolated comparison suite **5 passed (6.4s)**; strict production/contract TypeScript passed. Seven Khronos GLBs: zero errors/warnings, informational unused-UV notices retained. These are different scopes, not 71 independent rendered journeys.

Clean main-based worktree setup used `npm ci` (109 packages, zero reported advisory vulnerabilities) and repository requirements. Main excludes asset and comparison preparation tests, so its counts are intentionally lower. The clean feature-main worktree passed 26 backend tests (21.34s) and 21 application/browser/transport cases (33.0s), including strict build. No assertions were weakened. Commands:

```powershell
# backend
python -m pytest tests -q -p no:cacheprovider
# frontend
npm ci
npm run test:e2e
```

`test:e2e` builds with strict TypeScript then runs real FastAPI-backed Chromium flows plus pure transport/observer cases. Main does not define `test:contracts`, `validate:assets` or asset_contract.py. Do not call their absence a passing test. They passed only on the combined child branch.

Screenshots are actual ignored test artifacts, inspected locally rather than generated marketing evidence. Existing tests cover six viewport sizes, pass/cutoff correctness, seed generation/recovery, keyboard focus, network failure/retry, camera/profile switching and no-WebGL/context loss. Physical GPU measurements are separate from software-rendered CI. No full formal security certification is implied.

## Physical Intel Iris Xe evidence

Machine: Windows 11, i7-1355U, 16GB RAM, Intel Iris Xe driver **32.0.101.7088**. Headed Chromium **156.0.8078.4**, viewport **1366×768**, device DPR approximately **1**; scene profile DPR is separately bounded. Actual renderer:

`ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x0000A7A1) Direct3D11 vs_5_0 ps_5_0, D3D11)`

Measured asset-enabled application runtime was built from `62c2978` (same runtime as #31 `ee74d14`); tooling subsequently committed as `4d0a24f`. No SwiftShader launch flag was used for this headed run. Each profile used a five-second active orbit workload, followed by 12 camera/profile/replay interactions, three 2D/3D cycles and 30s idle. The figures below measure browser requestAnimationFrame pacing during input, not GPU timer queries or guaranteed presentation FPS:

| Profile | Frame callbacks/sec | Median interval | p95 interval | Calls / triangles |
|---|---:|---:|---:|---:|
| Low | 60.20 | 16.7ms | 17.0ms | 13 / 5,324 |
| Medium | 60.12 | 16.7ms | 16.9ms | 21 / 18,820 |
| High | 60.10 | 16.7ms | 16.9ms | 30 / 32,484 incl. shadow pass |

First renderer-ready sample 736.4ms is not full asset completion. Each model and renderer chunk requested once, errors `[]`. JS heap before/after/idle: 19,721,152 / 18,774,358 / 15,343,092 bytes; no forced GC, no proof against longer-lived leaks. Dedicated VRAM, GPU utilization and direct GPU frame time unavailable. Keep Medium desktop default, Low for constrained/mobile cases; do not increase defaults based on this short run. No optimization was justified by this measurement.

Reproduction (available on main through this integration PR, and on #31): build/start the application, then in frontend set `$env:PULSE_GRAPHICS_HARDWARE='1'`, `$env:PULSE_GRAPHICS_URL='http://127.0.0.1:8000'`, and run `npm run measure:graphics`. It opens a headed browser, rejects software renderer identity and writes ignored `test-results/graphics/intel-hardware.json`; without the opt-in it retains the headless probe. RTX #34 remains Diyan's separate optional task; these results do not satisfy his workstation benchmarks.

## Diyan integration matrix

No remote engine implementation/branch or `backend/app/sandbox/` package was available at inspection. The following are requirements to agree, not guessed API signatures.

| Dependency | Required data/behavior | Consumer | Required integration test | Owner/status |
|---|---|---|---|---|
| Resolved scenario | Validated configuration, seed derivation, IDs, versions, supported tactics | SandboxSetup/API adapter | Same resolved inputs produce same events | Diyan #2/#3, unavailable |
| Authoritative clock/state | Tick/period, revision, cursor, score, possession, actor/tactical state | Sandbox control state and replay transport | One clock, same-second order, stale response rejected | Diyan #4/#5, unavailable |
| Runtime controls | Legal pause/resume/step boundaries; conflict and recovery semantics | Sandbox controls | Duplicate request/lost response reconciliation, no second client clock | Diyan, unavailable |
| Event stream | Scenario/branch identity, ordered sequence/cursor, snapshot/delta gap recovery | replayApi/EventTimeline/observer | Cursor gaps, reconnect, foreign/future events rejected | Diyan, unavailable |
| Exact snapshot | Complete engine-owned state, all RNG streams/counters, pending queue, cursor, hashes/versions | #6 checkpoint adapter | Save→continue vs isolated restore→same inputs yields identical events/state/RNG | Diyan hooks, Satvik consumer; blocked |
| Persistence/restore | Atomic immutable snapshot/event boundary, ownership, idempotency, compatible versions | #6 checkpoint UI | Corruption, stale revision, concurrent restore, interrupted transaction rejected safely | Diyan contract/Satvik implementation; blocked |
| Interventions | Valid bounds, prior/next values, effective tick, actor/origin, branch and revision | Tactics and branch runner | Only future events change; intervention replay matches | Diyan #7, blocked on agreed restore hooks |
| Branch/trials | Immutable parent, independent state/streams, paired seed/trial IDs, quotas/cancel/progress | #8 comparison adapter | Parent unchanged, no contamination, paired repeated hashes | Diyan/Satvik, blocked |
| Manifest | Canonical inputs, ancestry, runtime/build versions and hashes | Checkpoint/ForkCast provenance | Independent hash recomputation and mismatch diagnostics | Diyan #9, unavailable |
| Evidence | Branch/trial/time-scoped event IDs, actual metric calculations and audit status | Mahir ProofTrail/tools; ForkCast UI | Tampering/future/wrong-branch claims rejected server-side | Mahir #16, contract coordination needed |
| Optional observer frames | Authoritative tick/sequence, scenario/branch/frame identity, defined coordinate frame and positions | eventSnapshot/SceneCanvas future adapter | Gap resync, seek/restore isolation, invalid frame rejection | Diyan; absent, keep event snapshots |

Prepared definitions remain proposals: #32 `checkpointContract.ts` and `CHECKPOINT_INTEGRATION_PROPOSAL.md`; #33 `comparisonContract.ts` and `FORKCAST_DISPLAY_PROPOSAL.md`. They cannot replace actual engine-owned state or confer evidence verification.

## Next integration sequence

1. Agree engine state/clock/revision/cursor and scenario contracts with Diyan; review actual code/tests before consuming them.
2. Add a typed adapter to existing Sandbox API/replay transport, preserving fixture mode and request cancellation. Connect only enforceable controls.
3. Implement immutable checkpoint persistence around complete engine snapshot hooks; prove deterministic isolated continuation before exposing restore.
4. Integrate intervention effective ticks and auditable log with those restore semantics.
5. Build bounded isolated paired branches using Diyan's canonical manifests; independently recalculate comparison metrics/hashes.
6. Connect #33 display only to auditor-approved real outputs; remove no safety labels without evidence. Integrate Mahir's branch-scoped ProofTrail.
7. Verify full create→pause→checkpoint→intervene→fork→compare journey, ownership/resource limits, reconnect and no-future leakage. Optional modeled observer frames come later.

## Documentation, demonstration and reviews

README and PROJECT_STATUS describe actual main, not unmerged features. SATVIK_IMPLEMENTATION/QUALITY_REPORT are historical with current-status links. This handoff is a narrow integration deliverable, not Vishwam's final submission documentation.

Launch from the desired checkout: `.\scripts\start.ps1`. Open `http://127.0.0.1:8000/#/sandbox`; generate seed, play/pause/seek, select pass and inspect verified factors, switch 3D camera/quality, return to 2D, continue, refresh and recover fixture identity. Replay resets to kickoff on refresh. No credentials or authoring tool is required.

Pending external gates: Vishwam #23 approval for #31 assets; Diyan state/clock/RNG/queue/intervention/manifest contracts; Mahir branch evidence agreement before publishing experiments. No missing required human approval was invented or bypassed. Remaining risk is integration incompleteness and review latency, not a demonstrated defect in the merged independent slice.


## Actual merged procedural main: physical GPU and launch verification

The main-based clean worktree was launched through the real `scripts/start.ps1 -Port 8769`: dependencies, strict build and real FastAPI startup succeeded. Port 8000 was already occupied by an existing process, which was not terminated. The optional validated Port argument preserves the default 8000 command and reports a nonzero server exit as an error.

A second headed Intel session exercised the **actual procedural main runtime 79d1211**, distinct from the asset branch above. It generated custom-0 through the API, played/paused, sought forward/backward, selected a real pass, matched its inspector identity, verified no 3D requests in 2D, used all camera modes, switched profiles, toggled 2D/3D three times, resumed replay and refreshed to the saved fixture at kickoff. Runtime errors: zero. No GLB request occurred; the lazy renderer was requested once.

Same verified Intel renderer, driver/browser/viewport as above. Five-second active-orbit rAF pacing: Low 60.04 callbacks/s, median 16.7ms, p95 16.9ms; Medium 60.04, median 16.7ms, p95 17.0ms; High 60.11, median 16.7ms, p95 17.1ms. Main geometry counters: Low 19 calls/656 triangles; Medium 39/10,100; High 67/16,740 including shadows. These differ from the unmerged GLB kit by design. First renderer-ready probe 636.9ms; no asset completion timing applies to procedural main. Browser pacing is not direct GPU execution time or a long-session performance guarantee. GPU utilization/VRAM unavailable. Recommended profile remains Medium, Low for constrained devices.

Raw results and actual inspected profile screenshots live in ignored `test-results/main-intel/` in the clean release worktree. Main production bundles: default JS 86.88kB gzip, optional renderer 250.39kB gzip. The optional >500kB uncompressed chunk warning remains visible; default 2D does not fetch it.

Repository hygiene: tracked .env.example only, no tracked SQLite/build/test-output artifacts; focused private-key/token pattern scan found no matches. This is a bounded safety check, not Vishwam's formal audit. README relative documentation links are checked for actual files. Full localization, billable inference, cloud deployment and final submission remain separate teammate work.
