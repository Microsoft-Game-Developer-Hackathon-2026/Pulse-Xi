# Final requirements audit - 2026-10-22

Historical snapshot: the baseline and coverage counts below apply to the dated
audit, not current main. See the [release evidence ledger](RELEASE_EVIDENCE_LEDGER.md)
for integration changes, exact-head CI and remaining external acceptance gates.
Issue #34's current Diyan target is the physical RTX 5070 Laptop GPU, alongside
Satvik's physical Iris Xe; the old RTX5090 requirement below was unverified.

## Scope and method

Baseline main: `d19a898492f8c4a303caa576a9370411b21093ff`.
Official source: [competition rules](https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md), checked again in this session.
Full issue bodies were downloaded; acceptance/DoD sections for the release,
agent, analytics, persistence and submission work were reviewed against source.
This matrix decomposes the product into 35 auditable requirements. It is not a
claim that every button, every hostile input or every original issue sub-bullet
has received an independent manual test. Named automated flows and real HTTP
execution are distinguished from missing live-provider/release evidence.

`verified` means the stated scoped behavior has executable evidence, not that
its entire parent GitHub issue is closable. `partial` includes a real implemented
slice with unmet acceptance. No legal/provider/submission gate is marked verified
because a mock or CI job passes. Test file names below are relative to
`backend/tests` or `frontend/tests`; frontend paths are under `frontend/src` and
backend paths under `backend/app` unless stated otherwise.

| ID | Category | Original source | Required behavior | Frontend | Backend | Persistence | Tests | Runtime evidence | Status | Severity | Next action |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | challenge | Rules 4.1(a); #5/#9 | Ingest/replay valid synthetic events | App.tsx; MatchDataHub.tsx | main.py; data_hub.py | fixtures + library SQLite | test_data_hub.py; data-hub.spec.ts | real import/preview/replay/export browser journey | verified | high | retain regression |
| C2 | challenge | Rules 4.1(b); #4/#26/#27 | Derive bounded statistics from source events | TacticalLab.tsx; ControlChaos.tsx; PassInspector.tsx | analytics.py; pass_difficulty.py | stateless derived output | test_control_chaos.py; test_pass_difficulty.py; replay.spec.ts | source counts, window boundaries and pass evidence tests | verified | high | preserve formula versions |
| C3 | challenge | Rules 4.1(c); #16 | Explain a moment with inspectable source facts | App.tsx proof drawer | evidence.py | source events; deterministic packets | test_simulation.py; broadcast-proof.spec.ts | real cue-to-proof-to-source browser flow | verified | high | deterministic explanations are not model inference |
| C4 | challenge | Rules 4.1(d); #17 | Render synchronized machine-readable cues | App.tsx studio/overlay | evidence.py; main.py overlays | derived JSON | broadcast-proof.spec.ts | real timed cue, same source references and JSON export | verified | high | producer editing is a separate incomplete requirement |
| C5 | challenge | Rules 4.1(e); #20 | Different audience presentations with identical facts | App.tsx; fandna.ts | evidence.py | browser preferences; derived recap | test_fandna_locales.py; fandna browser tests | locale/persona/preferences and cue evidence parity | verified | high | runtime controls remain English |
| C6 | challenge | Rules 4.1 AI-powered challenge; #14/#15 | Demonstrate genuinely executed model-backed workflow | existing admin invocation/trace surface | agents.py | bounded process-local traces | test_agent_tools.py; test_foundry_smoke.py | offline adapters tested; no hosted call authorized | blocked | high | Mahir: approved credentials/cost and actual verified trace |
| F1 | frontend | User replay defect; #68 | Passive replay keeps panels/scroll stable at all speeds | App.tsx; useReplayAnalysisCutoff.ts | existing unchanged read APIs | in-memory public packets | replay-refresh.spec.ts; viewport-stability.spec.ts | new failing baseline probe and candidate measurements | verified | high | see performance evidence and sampling limits |
| F2 | frontend | #10 | Authenticated Control Room workflow | runtime/RuntimeRoom.tsx | sandbox/api.py; sandbox/storage.py | runtime schema 4 SQLite | runtime.spec.ts; scenario-library.spec.ts | real scenario/run/checkpoint/ForkCast/reconnect flows | verified | high | keep operator credentials memory-only |
| F3 | frontend | #11/#12/#66 | Source-linked observer, quality/camera and fallbacks | observer/ObserverSwitch.tsx; SceneCanvas.tsx | recorded/native events only | local quality/view preference | observer.spec.ts; observer-sync.spec.ts; graphics.spec.ts | actual GLB loading and failed graphics recovery | verified | medium | no new physical GPU/FPS claim |
| F4 | frontend | #16/#54 | Branch ProofTrail request isolation | sandbox/ProofTrail.tsx | sandbox/prooftrail.py | runtime DB; transient result | prooftrail.spec.ts; test_sandbox/prooftrail.py | clear/credential/branch/cutoff/unmount/late error cases | verified | high | do not expose private events to public agent tools |
| F5 | frontend | #58/#76 | Authenticated runtime Control vs Chaos | runtime/RuntimeAnalysis.tsx | sandbox/analysis.py | owner-scoped runtime | test_runtime_control.py; runtime-control.spec.ts | PR76 merged; native projection, ownership, cutoffs and delayed private responses tested | verified | medium | preserve strict private revision boundaries |
| B1 | backend | #4 | Deterministic clock, RNG, halftime, terminal state | Control Room consumer | sandbox/engine.py | hashed engine state | test_authoritative_engine.py | fresh backend suite; goldens and independent verifiers | verified | high | preserve engine semantics |
| B2 | backend | #57 | Native duration analysis without future leakage | runtime/RuntimeAnalysis.tsx | native analysis adapters | runtime source identity | test_native_analysis.py; test_runtime_analysis.py | fresh backend duration/cutoff/identity regressions | verified | high | do not conflate legacy projection with native |
| P1 | persistence | #3/#64 | Saved scenario/archive identity and owner isolation | runtime/RuntimeRoom.tsx | sandbox/scenario_archive.py; storage.py | runtime SQLite | test_scenario_library.py; browser scenario suite | real HTTP archive round trip and browser reload | verified | high | schema 4 and source identity retained |
| P2 | persistence | #6/#70 | Atomic checkpoint UTC, retries, restore and exact continuation | runtime checkpoint inspector | sandbox/checkpoint_metadata.py; storage.py | schema 4 sidecar + immutable snapshot | test_checkpoint_metadata.py; checkpoint-source.spec.ts | fresh tests + actual HTTP UTC/hash/isolated restore | verified | high | legacy timestamps remain unknown |
| P3 | persistence | #8 | Paired ForkCast trials and independent bundle verification | runtime ForkCast comparison | sandbox/experiments.py | persisted trials and immutable parent | test_reproduction.py; runtime.spec.ts; forkcast-limit.spec.ts | combined candidate: 98 browser tests pass including unchanged dense/offline case; both CLI verifiers pass | verified | high | PR79 review and exact-head CI required before main integration |
| P4 | persistence | #9 | Data Hub import, revisions, lifecycle and backup | sandbox/MatchDataHub.tsx | storage.py; database_backup.py; main.py | separate imported library SQLite | test_storage_startup.py; test_library_lifecycle.py; data-hub.spec.ts | fresh migration/rollback/corruption plus real browser import/lifecycle | verified | high | personal databases untouched |
| P5 | persistence | #7/#10 | Browser notes/preferences and private disconnect recovery | analysisStorage.ts; RuntimeRoom.tsx | owner-authorized reads | browser-local notes; memory-only credentials | analysis-workspace.spec.ts; runtime.spec.ts | refresh, stale source and disconnect/reconnect regressions | verified | high | no server token persistence |
| S1 | security | #23/#44/#72 | Owner denial, hostile inputs, no-store and fail-closed admin | existing API clients | security dependencies; main.py | scoped SQLite and no private cache | test_security_boundary.py; test_release_security.py; test_foundry_command_auth.py | all backend security cases executed with full suite | verified | high | not an independent penetration-test certification |
| S2 | security | #12/#23 | Asset hashes and valid GLB structure | observer assets | scripts/asset_contract.py | 7 manifest records + source/export files | test_asset_contract.py; validate-assets.mjs | 7 GLBs: zero errors/warnings; informational unused UV entries | verified | medium | rights approval remains separate |
| S3 | security | #23; Rules 4.6 | Rights-holder authority, root/helper licensing and release approval | not applicable | not applicable | manifest pending-team-review | human decision required | no genuine release sign-off supplied | blocked | high | Vishwam and actual rights holders must decide |
| A1 | agents | #15/#55 | Strict scoped tools, role allowlists and deterministic audit | existing trace consumer | agent_tools.py; agents.py | latest 50 process-local traces | test_agent_tools.py; test_simulation.py | fresh offline allowlist/false-claim/failure tests | verified | high | tool tests do not prove live model handoffs |
| A2 | agents | #14/#56 | Optional SDK path fails closed without live calls | not applicable | backend/scripts/foundry_smoke.py | redacted offline report | test_foundry_smoke.py | fresh offline test coverage; optional SDK check separate | verified | high | no cost flag or credential upload |
| A3 | agents | #14/#15 | Actual authenticated hosted handoffs and measured provider cost | optional trace surface | agents.py | genuine redacted provider trace missing | not executed | no billable call authorized | blocked | high | Mahir + cost authorization |
| U1 | ux | HIG; #71 | Responsive navigation, focus, reduced motion, all routes | precision-glass.css; useAtelierMotion.ts | unchanged | browser preferences | glass-layout.spec.ts; glass-accessibility.spec.ts | 7 sizes / 4 routes; actual screenshot artifacts | verified | medium | new physical Safari/zoom audit not claimed |
| U2 | ux | User audit request | React Profiler, long-session memory and Web Vitals characterization | App.tsx full render tree | not applicable | diagnostic only | not yet comprehensively instrumented | bounds/network probe is narrower than a React profile | partial | medium | measure long tasks/INP/memory before making broad performance claims |
| D1 | submission | Rules 4.4 | Public source repository | GitHub | GitHub | public repository | gh repo view visibility | PUBLIC verified via GitHub | verified | high | retain public source through judging |
| D2 | submission | Rules 1/3/4 | Registration confirmation and authorized team representative | not applicable | not applicable | user confirmation | registration confirmed by user | registration confirmation retained; individual eligibility not independently audited | partial | high | representative verifies all legal eligibility |
| D3 | submission | Rules 4.4 video; #25 | Real video <120 seconds at allowed public URL | real app capture | not applicable | final video missing | public playback not executed | script/screenshots are not final video | blocked | high | record, authorize upload, verify public playback |
| D4 | submission | Rules 4.8; #21 | Accessible functioning judge build and clean-browser instructions | full application | approved hosting/test build | judge access not provisioned | public URL acceptance missing | local smoke is not public judge access | blocked | high | Vishwam: approve lowest-risk access path |
| D5 | submission | Rules 4.4; #24/#25 | Accurate English pitch, architecture and limitations | README and submission docs | documented architecture | version-controlled docs | documentation source review | existing package updated; stale merged-feature claims corrected | verified | medium | freeze final SHA before capture |
| D6 | submission | Rules 1/4; #25 | Submit by Oct27 23:59 Pacific and retain confirmation | submission portal | external | confirmation missing | not submitted | no submission action authorized/executed | blocked | high | authorized representative submits and verifies |
| O1 | optional | #17/#50 | Producer editing, approvals and conflict-safe cue publishing | preview only | contract proposal merged | no production approval store | contract tests are not producer workflow | preview/JSON exists; advanced studio not complete | partial | low | defer from advertised hero path |
| O2 | optional | #18 | Event-derived downloadable Remotion MP4 | not implemented as product action | not implemented | none | no production render acceptance | browser recording is not a Remotion product pipeline | missing | low | defer; record real demo instead |
| O3 | optional | #34 | Physical RTX5090/Iris Xe comparative validation | existing observer | not applicable | historical evidence only | no new physical measurements | software browser rendering is not hardware certification | partial | low | owner with actual hardware; not core demo blocker |

## Transparent completion ledger

Only `verified` counts in the numerator. Optional rows do not enter mandatory challenge coverage. These are matrix-row counts, not an official score or whole-project percentage.

| Category | Verified | Total | Coverage |
|---|---:|---:|---:|
| challenge | 5 | 6 | 83.3% |
| frontend | 5 | 5 | 100.0% |
| backend | 2 | 2 | 100.0% |
| persistence | 5 | 5 | 100.0% |
| security | 2 | 3 | 66.7% |
| agents | 2 | 3 | 66.7% |
| ux | 1 | 2 | 50.0% |
| submission | 2 | 6 | 33.3% |
| optional | 0 | 3 | 0.0% |

The five deterministic pipeline stages are exercised; the separate model-backed
AI evidence requirement is blocked. Do not advertise this as fully demonstrated
hosted AI. The ledger cannot establish rights, business adoption, or judge access.

## Innovation decision

Evidence-to-Broadcast Inspector already had a real implementation and browser evidence.
The earlier version of this section also claimed One Moment/Three Stories existed; a
2026-10-24 re-audit found no UI or test for it (the agent-run route is admin-only and
unused by the frontend), so that claim was incorrect. A small version now ships in the
ProofTrail drawer (`frontend/src/ThreeStories.tsx`, `frontend/tests/three-stories.spec.ts`):
one `insight_id`, three lenses (analyst from the insight and its claims, fan from a casual
recap fetched at the moment's own clock, director from the matching cue), a computed
source-ID consistency line, and an explicit PROPOSED label because approval requires the
producer token in Director Studio. All text is rule-based; no model is invoked. It adds no
analytics engine and no new backend route.

## Persistence and ownership boundary

Built-in fixtures regenerate deterministically; imported datasets use the library
SQLite store; scenarios/runtime commands/checkpoints/experiments use a separate
schema-4 database. Backend tests exercise migrations, restart, rollback, corruption,
revision races and ownership. The release smoke creates temporary stores and uses
real authenticated HTTP, then invokes independent CLIs. Browser notes/preferences
are local; runtime credentials remain memory-only. No personal database was used.
A simultaneous browser + server-process restart + SQL query capture for every
feature has not been performed; do not confuse the combined suites with that
additional forensic trace.

## Subsequent ledger update

PR76 is now merged into main7a8cccf; F5 and its scoped frontend numerator are updated accordingly. The original P3 maximum-history failure was subsequently fixed in the PR79 candidate and passed the unchanged standalone Windows test. Its full combined browser result and review/merge boundary are recorded in PR79; candidate verification must not be mistaken for main integration. All percentages describe this finite matrix, not exhaustive feature certification.

Final combined validation passed 98 browser tests in 6.0 minutes and 367 backend tests. P3 now counts as verified on the PR79 candidate; it remains pending main integration. Frontend5/5 and persistence5/5 are scoped matrix-row counts. Broader profiler/security/release/submission limitations remain unchanged.
