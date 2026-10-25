# Final hackathon readiness report - 2026-10-22

## A. Executive assessment

**DEMO READY, SUBMISSION BLOCKED**, for the bounded deterministic hero journey.
This is a completed replay-stability engineering milestone and a scoped product
review, not certification that every issue sub-requirement or every interaction
has been exhaustively audited. A maximum-history local performance failure and
uncompleted profiling work remain. No overall invented completion percentage is
assigned.

Starting main: `d19a898492f8c4a303caa576a9370411b21093ff`.
[Exact-main CI](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/39766286652)
is successful. Audit source commit: `adc4a57` on
`audit/hackathon-final-readiness`; this increment is not on main until reviewed
and merged. Backend source diff is empty; engine, RNG, schema, hashes and API
contracts have not been changed by this branch.

## B. Requirements and completion

The [35-row requirements matrix](FINAL_REQUIREMENTS_AUDIT.md) traces source,
frontend, backend, persistence, test, runtime evidence, status and next action.
The five deterministic ingest/interpret/explain/render/personalize stages work;
model-backed execution is separately blocked, so challenge coverage is5/6
(83.3%) under the explicitly defined matrix decomposition. This is not an
eligibility verdict or predicted judging score.

| Category | Verified / total | Evidence boundary |
|---|---:|---|
| Mandatory challenge decomposition | 5/6 | Hosted AI proof remains absent |
| Frontend workflows | 4/5 | Runtime Control vs Chaos awaits PR76 |
| Backend core | 2/2 | Scoped engine and native-analysis requirements |
| Persistence / experiment requirements | 4/5 | Ordinary ForkCast works; maximum-history local latency fails |
| Security / provenance | 2/3 | Technical tests do not establish rights or release permission |
| Agent requirements | 2/3 | Offline bounded tools and failure paths; no actual hosted trace |
| UI/UX | 1/2 | Responsive/focus coverage; full Profiler/Web Vitals/heap study outstanding |
| Submission requirements | 2/6 | Public source and written package verified; actual video/access/submission not |

## C. Real integration evidence

| Feature | Frontend / backend / storage | Executed evidence | Result |
|---|---|---|---|
| Replay/intelligence | App + analytics/evidence + fixtures | Real browser seeks, score/event/evidence parity | Passed |
| Data Hub | MatchDataHub + authenticated import/lifecycle + library SQLite | Preview/import/reimport/lifecycle/export browser cases | Passed |
| Scenarios | RuntimeRoom + scenario API + separate runtime SQLite | Save/list/archive/import/create in real HTTP and browser | Passed |
| Checkpoints | Inspector + metadata sidecar + schema4 | Original UTC, restore hash, migration/retry/corruption/security suite | Passed |
| ForkCast | Runtime UI + paired server trials + immutable history | Real bounded experiment, source comparison and both CLI verifiers | Passed for ordinary journey; maximum-history latency fails locally |
| ProofTrail | Branch consumer + authenticated comparison service | Clear/credential/branch/cutoff/unmount/late-error races | Passed |
| FanDNA/broadcast | Persona/locale + deterministic recap/cue service | Same source across stories, cue proof and JSON exports | Passed |
| Observer | Real committed GLBs + recorded event positions | Missing/corrupt/slow assets, cameras, context loss and2D fallback | Passed |

Temporary databases were used. Backend tests verify transaction rollback,
restart/reopen, migrations, ownership, revisions, corruption and backup. This is
not a claim of a forensic SQL/network/React trace for every individual control.

## D. Confirmed defects and changes

| Defect | Reproducer / cause | Correction | Regression/result |
|---|---|---|---|
| Recap disappears/starves | 200ms playback cancels220ms debounce; state cleared on every tick | Independent1Hz analysis cadence; no per-tick clear | Desktop/mobile all-speed replay probe passed |
| Metrics/tactics blank | Exact response-time equality invalidated every next tick | Same-source past-only retention, actual cutoff shown | No missing metric samples; backward future packet concealed |
| Control vs Chaos collapses | Large tree removed whenever clock advanced | Same-window retained response, labelled source cutoff, bounded reader | Existing windows/evidence tests + stable anchor passed |
| Pass detail collapses | New visible-pass key discarded previous geometry result | Public recorded-source past cache; runtime private exact-key path unchanged | Existing pass tests + replay probe passed |
| Analyst team changes while reading | Passive current pass fed explicit-selection effect | No passive selected-event propagation into analyst selector | All-speed anchor test passed |
| Narrative/coverage wrapping moves lower sections | Variable text/list heights | Focusable overflow readers and minimum caption space; no clipping/max height on tactical copy | Zero measured studio-anchor/scroll displacement in200 observations |
| Stale README/judging claims | Merged native/analytics/agent/UI PRs still listed pending | Current audit addenda and corrected README availability | Version/ancestry checked against GitHub |
| Maximum-history comparison slow | Completed10-branch experiment, table absent after90seconds | Root path identified: repeated full manifest replay; not changed here | Dedicated test failed; Diyan review/profile required |

The previous viewport-floor fix protects occupied scroll extent but did not stop
panel collapse. This increment fixes the content lifecycle rather than calling
scrollTo during playback. Reading regions scroll locally and retain keyboard
access; explicit source navigation still scrolls intentionally.

## E. Performance and UI

See [performance audit](PERFORMANCE_AUDIT.md) and raw JSON in
[audit-evidence](audit-evidence/). Thirteen HTTP endpoints have20 warm samples
each, first-request data separately recorded. Local recap P50/P95:23.45/33.70ms;
export34.35/36.88ms. These are local measurements with uncontrolled background
processes, not remote guarantees. The eight short replay windows have0px
unintended anchor and document-scroll displacement, with no missing metrics or
recap. Request counts cover metrics/tactics/recap only.

Atelier's neutral typography, team cyan/coral, mint selections and existing
material hierarchy remain. No new decorative animation or library was added.
Four routes were captured at1440/390 and responsive tests cover seven sizes.
Desktop Match Intelligence/Data Hub and mobile Sandbox/Control Room screenshots
were visually inspected; this does not certify all zoom, screen-reader or
physical Safari combinations. [Screenshots](audit-evidence/) contain no operator
credentials. Existing [Atelier before/after images](images/atelier/) preserve the
larger design history.

No full React Profiler, long-session heap, LCP/INP/CLS study or physical GPU
benchmark was completed. Bounds sampling is not equivalent to those measurements.

## F. Innovation and Microsoft AI

The memorable existing differentiator is event-to-evidence-to-personalized-story-
to-timed-cue, plus reproducible tactical experiments. The audit strengthened its
reading experience instead of duplicating Mahir's engines or adding an artificial
agent chain.

Microsoft Agent Framework/Foundry provider code and evidence-scoped role tools
are merged. Tactical Analyst and Story Editor are optional model-backed roles;
Broadcast Director/Fan Personalizer deterministic formatting and the independent
evidence auditor are not additional hosted model agents. CI uses mocks/adapters
and deterministic tools. No live hosted invocation, tokens, cost or authenticated
provider trace was generated. Scenario-comparison agent capability remains
unavailable even though ForkCast exists. That adapter needs its own safe contract.

## G. Tests and exact scope

- Backend: **344 passed** in206.21s; includes security, native analysis, migrations,
  transactions, restart, ownership, evidence, agent tool/fallback and exports.
- Ordinary Playwright: **94 passed** in3.6min, including three new replay regressions.
- Dedicated maximum-history ForkCast: **1 failed** at unchanged90s comparison wait.
  Do not report this as95 passing tests.
- TypeScript and production Vite build: passed. Existing lazy3D chunk warning remains.
- Asset validator: seven GLBs, zero errors/warnings; informational unused UV entries.
- Independent example manifest and experiment CLIs: both `verified:true`.
- Real HTTP release smoke: passed in9.15s; isolated stores, real paired trials and two verifiers.
- Optional SDK `foundry_smoke.py --check-only`: `sdk_compatibility_ok`,
  `authenticated:false`, `network_call:false`.
- `pip check`: no broken requirements. Base pinned `pip-audit`: no known vulnerabilities.
  `npm audit`: zero vulnerabilities. This is not a legal/license clearance.
- `git diff --check`: passed. No dependency or backend source modifications.
- Cross-browser material/route smoke: **6 passed** (Chromium, Firefox, Playwright WebKit).
  This is not physical Safari/iPhone certification. Exact-head CI is recorded in the PR.

These are fresh candidate results, not borrowed counts from historical main CI.
The small final text-separator correction does not alter request/state behavior;
fresh CI must rebuild and test the final delivery head.

## H. Submission readiness and owners

Deadline verified against official rules: **October27,2026 at23:59 Pacific =
October28 at06:59UTC /12:29IST**. User confirmed timely registration. Individual
eligibility and representative authority remain the team's responsibility.

| Mandatory remaining deliverable | State / owner |
|---|---|
| Public source | Verified PUBLIC repository |
| Accurate English pitch/architecture/limitations | Written package exists; current status corrected |
| Final real video <120s + approved public platform URL | Not evidenced; recording/upload approval and execution still needed |
| Working judge access through judging period | Local app tested; public/test-build access not independently verified; Vishwam |
| Rights-holder authority, root/helper licenses, release decision | #23 open; Vishwam + actual rights holders |
| Actual hosted AI evidence if advertised | #14/#15; Mahir + explicit credentials/cost permission |
| Submission confirmation | #25 remains open; authorized representative must submit |

No paid service, cloud resource, public deployment, video upload or final
submission occurred. No release/rights approval was invented. Strongest category
alignment must follow actual executed agent evidence; no category prize claim is
supported merely by installing an SDK.

## I. Reproducible hero journey

Use built-in `comeback-1107`: seek3500, inspect the0:2 score and actual source
insight; open its evidence from a verified broadcast cue; switch audience/locale
while retaining the same facts; preview/export cue JSON. Then enter an isolated
operator runtime with the documented120-second balanced seed7 scenario, step30,
checkpoint, restore a new branch and run one30-second paired treatment trial.
Compare and independently verify its bundle. These bounded paths were exercised;
do not use the maximum-history stress case as a timed demo promise.

See [submission package](HACKATHON_SUBMISSION_PACKAGE.md) and
[runbook](SUBMISSION_RUNBOOK.md). A script is not a completed recording.

## J. Next action and resume point

Worktree: `C:\Users\satvi\Desktop\Microsoft\pulse_xi_audit`.
Branch: `audit/hackathon-final-readiness`. Source increment: `adc4a57`.
Review the replay correction and audit evidence, then merge only with actual
required approval and exact-head checks. Separately profile the repeated
ForkCast replay path with Diyan, resolve PR76's integration conflicts, and protect
time for rights/access/video/submission. The broad forensic/performance audit is
not complete; the remaining profiling tasks are explicitly listed rather than
silently marked done.

## K. Subsequent runtime analytics reconciliation

After the baseline audit delivery in PR77, PR76 was reconciled with current main
and then stacked on PR77. Its old conflict status above describes the initial
inspection, not the final review path. Normal merge99f4eb5 retained current-main
schema4/UI/features; mergea4f1622 combined the replay change with strict private
runtime request/revision boundaries. No contributor history was rewritten.

PR76 code at `a4f1622a525ac3b1210adc384911d93497921cb8` passed **354 backend tests**
in268.79s and **97 ordinary browser tests** in3.8min, plus TypeScript/build.
The native-only parameter, short/full durations, invalid projection, owner denial,
captured source hashes, partial windows and delayed session switching are covered.
These counts are for the combined candidate, not current main. Engine, canonical
serializers, RNG and shared metric formula files remain unchanged.

PR76 now targets `audit/hackathon-final-readiness` for a focused stacked review.
Review/merge77 first, then retarget76 to main and verify its checks again. Both
PRs were mergeable at delivery and Diyan/Mahir reviews were requested; no submitted
human approval or merge is claimed. PR77 exact delivery headb1c2216 has two green
Actions runs:39771331806 and39771346571, including344 backend/95 browser on Linux.
PR76 exact-head checks and final delivery SHA are available on its GitHub page.

The local maximum-history Windows timeout remains unresolved; Linux PR77 CI passes
that same test. No weakened assertion or new hosted-performance guarantee is made.
The remaining profiler/memory/rights/video/access/submission work still applies.

## L. Subsequent GitHub integration and performance verification

GitHub now confirms PRs #76, #77 and #78 merged. Main at 7a8cccf9b9a3b6a6217c5188468493725d01129c has successful Actions run 39790628382. Earlier review-path and unresolved-conflict statements above are historical evidence. PR #78 merged at an intermediate optimization; the remaining verified correction is proposed separately in PR #79, preserving normal history and review.

The combined local validation tree at 7c34dbc7dd0feeb7d3928e32663e709fa1a2ce2e includes the replay fix, native runtime adapter and final performance source. It passed 367 backend tests in 242.42 seconds, TypeScript/production build, both independent committed example verifiers, pip check and seven GLB validations (zero errors/warnings; informational unused UV notices). Real isolated HTTP release smoke passed in 11.57 seconds with both verifiers and recorded original checkpoint UTC; no hosted inference occurred.

The unchanged Windows maximum-history browser case passed separately in 2.7 minutes. The full combined 98-browser suite is still being verified; its final result belongs in PR #79's evidence comment. Shared-prefix proof reuse is bounded to one bundle and requires identical independently checked records/scenario/ancestry. No claimed final state is trusted. Verifier source fingerprints change by contract; only build fingerprint fields in examples changed, with canonical events/state hashes and results preserved.

Release classification remains DEMO READY, SUBMISSION BLOCKED. Rights/release approval (#23), functioning public judge access, actual public video under two minutes and submission confirmation (#25) remain external gates. Hosted Foundry execution is not verified or authorized. The remaining broad profiler, long-session and forensic trace gaps remain explicit; this is not a claim of exhaustive product certification.

### Final combined browser result

All 98 Playwright tests passed in 6.0 minutes on the combined validation tree, including the unchanged maximum-history comparison/download/offline-verification case. Backend/frontend application source is identical to the PR79 delivery; subsequent differences are documentation only. This verifies the candidate locally, not a merge or successful remote CI. The candidate ledger now records frontend5/5 and persistence5/5 verified matrix rows. These are scoped row counts, not a whole-project or official judging score.

## M. Demo-readiness session, 2026-10-24

Status: **DEMO READY, SUBMISSION BLOCKED** (unchanged). Superseded for merge state and final results by section N: PRs #104, #105 and #106 are merged.

**Refs.** `main` = `0729d3f`. PR [#104](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/104)
`audit/replay-stability` head `298828a`: exact-head CI all green (documentation, backend,
frontend, browser, container, deployment-template); review requested from two teammates,
none submitted. PR [#105](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/105)
`feat/one-moment-three-stories` (stacked on #104, base `audit/replay-stability`): review
requested; exact-head CI was all green on `3cc00fa`. A later commit on the same branch adds
the browser-metrics probe, design-token cleanup and the performance write-up (see its CI).

**Tests run locally.** Backend `pytest tests`: 541 passed, 0 failed, 0 skipped (281 s, base
`0729d3f`). Playwright full suite on the #105 head before the route-health file: 112 passed
(6.5 min); `route-health.spec.ts` adds 10 (passed on its own). `scripts/release-smoke.py`:
passed. `scripts/validate_docs.py`: passed. `npm audit --omit=dev`: 0 vulnerabilities.
Strict TypeScript (`tsc -b`) and production build: clean.

**Defect ledger (judge-visible).**

| Defect | Severity | Root cause | Fix | Regression test |
|---|---|---|---|---|
| Fan Lens fetched every 200 ms tick during replay (61 req / 12 s) | medium | effect keyed to the raw replay clock | use the shared 1 Hz analysis cutoff (13 req) | `replay-stability-metrics.spec.ts` (measures; request counts reported, not asserted) |
| Event Wire panel grew 137 → ~560 px, pushing content (CLS 0.27 at 4x) | high | list height depended on item count | fixed seven-row viewport, internal scroll | same file: panel bounds constant, page CLS excl. wire < 0.01 |
| Event Wire reserved height off by 4 px (490 vs 494) | low | min-height guess | exact height | same file |
| "One Moment/Three Stories exists" claim in the audit was false | medium (honesty) | no UI/test existed | built it; corrected the audit | `three-stories.spec.ts` |
| PR #100 CI timeout | n/a | not reproduced | none; evidence recorded | n/a |

Routes (Match Intelligence, Sandbox Lab, Control Room, Data Hub, Director Studio) loaded
cleanly at 1440/390 px on the real backend. No new defect was found there by this sweep;
that is a smoke result, not an exhaustive interaction audit. Deeper per-control audits of
Sandbox, Control Room and Data Hub were not repeated; their existing browser suites pass.

**Integration evidence.** `scripts/release-smoke.py` drives real loopback HTTP with
disposable SQLite stores: scenario create, run, checkpoint, restore, paired comparison,
two independent CLI verifiers, 4 audit records. Backend suites cover migrations,
rollback, corruption, ownership denial (403/401 paths), determinism and restore
(`test_authoritative_engine.py`, `test_reproduction.py`, `test_scenario_library.py`,
`test_security_boundary.py`, `test_release_security.py`). Remaining non-durable areas:
bounded process-local agent traces and browser-local notes/preferences.

**Added later in the session.** `browser-metrics.spec.ts` (LCP, long tasks, heap over a
full-match replay, synthetic interaction latency; two runs with large variance, see
[PERFORMANCE_AUDIT.md](PERFORMANCE_AUDIT.md)). The Three Stories CSS now uses design tokens
(`--px-warning`, `--px-error`, `--px-glass-border`, `--px-radius-sm`).

**Not done / not verified.** A screenshot-based colour consistency review of every route
(only the proof drawer was captured and inspected); field INP and React Profiler counts;
per-control audit of every route; accessibility re-run beyond the existing suite; hosted Foundry/Agent Framework run
(no authorization); public judge access, video, rights sign-off, submission.

### Demo scripts (verified features only; deterministic fixture `comeback-1107`)

Run: `.\scripts\start.ps1` then open `http://127.0.0.1:8000`. Reset: reload (replay state
is browser-local; the fixture regenerates identically). Fallback if 3D fails: stay on the
2D pitch, which is the default view; the 3D observer is optional.

**Video cut, under 120 s (the official limit; judges need not watch longer).**
0:00 one sentence: football dashboards report outcomes but cannot show why or what-if.
0:10 Match Intelligence: press play at 4×, scroll to analysis; panels stay still. 0:30 seek
to 16:40, open the goal's evidence: One Moment · Three Stories, same 2 source events, cue
labelled PROPOSED. 1:00 Control Room: 120 s seed-7 scenario, step, checkpoint, restore a
branch. 1:25 ForkCast comparison and independent verification. 1:45 say plainly that
explanations are rule-based and deterministic. Do not say "AI-powered".

**Five-minute live walkthrough.** (1) Problem and what is different, 30 s. (2) Replay at
1×/4×, Event Wire and stable panels, 60 s. (3) Fan Lens metric + alert while playing, 45 s.
(4) Goal cue → ProofTrail → Three Stories → switch persona/locale, same facts, 75 s.
(5) Control Room scenario → checkpoint → intervention branch → ForkCast, 75 s.
(6) Verify bundle independently, then state limits (synthetic data, rule-based text, no
hosted model), 15 s. Skip the maximum-history ForkCast case; it is a known slow path.

Commands: backend `cd backend; python -m pytest -q tests`; frontend `cd frontend; npm ci;
npm run build; npx playwright test`; smoke `python scripts/release-smoke.py` (after build).

Final full Playwright run on this branch after the last code change: **123 passed** (8.0 min), including route-health (10) and browser-metrics (1).

## N. Final release state, 2026-10-25

**Classification: DEMO READY, SUBMISSION BLOCKED.** Engineering for the issues that can be
finished in code is complete and merged; what remains is the video (Diyan), judge access, human
licence/rights decisions, and an authorized hosted-model run, none of which code can supply.

**Code state.** `main` = `92d05ed` (merge of [#106](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/106)),
containing [#104](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/104)
(replay stability) and [#105](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/105)
(One Moment · Three Stories, merged by the repository owner). Post-merge CI run
[40185354081](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/40185354081)
on `92d05ed`: all six jobs green. No branch protection or ruleset exists, so no review was
technically required; reviews on #104/#105 were requested from teammates and none was submitted.

**Verification run on the #106 head (pre-merge, same content as `92d05ed`).** Backend `pytest tests`: 547 passed,
0 failed, 0 skipped (311 s). Playwright full suite: 141 passed (6.4 min), including 13 axe-core
WCAG A/AA scans, 10 route-health checks, 5 highlight-reel tests, 3 Three Stories tests and the
replay-stability gates. `scripts/release-smoke.py` passed on the earlier branch head. `npm audit
--omit=dev`: 0; `pip_audit` on both requirement files: none; docs validator passed.

**Defects found and fixed this round.** Axe found three real accessibility defects (critical:
table rows without cell/columnheader roles; serious: aria-label on a role-less div; serious:
scrollable table not keyboard-focusable). The earlier round fixed Fan Lens 200 ms polling and the
Event Wire growth. A security note in issue #23 was corrected after verification: the highlights
GET is unmetered (the public quota covers only `POST /recap`).

**Issue disposition (GitHub numbers; the task prompt used title IDs, so prompt #13 = GitHub #14, and so on).**

| Issue | Title ID | State | Evidence or blocker |
|---|---|---|---|
| #17 Director AI studio | 16 | **Closed** | `test_director_studio.py`, `replay.spec.ts` Studio journey, axe-clean route |
| #20 FanDNA localization/voice/accessibility | 19 | **Closed** | en/es/hi catalog + backend templates, five modes, 13 axe tests; operator routes English only (stated in the closing comment) |
| #18 Remotion highlights | 17 | **Open** | Manifest, player, renderer and rendered example exist; Remotion not adopted (licence eligibility unresolved); no in-app render job, audio or MP4 |
| #14 Foundry live validation | 13 | **Open, blocked** | No credentials in this environment; billable call needs written owner approval |
| #15 Multi-agent orchestration | 14 | **Open** | Offline workflow verified; live-run acceptance depends on #14 |
| #23 Security/legal/provenance | 22 | **Open** | Audits re-run clean; needs rights-holder CC0 declaration, a root `LICENSE` decision (none exists) and independent release approval |
| #25 Demo video and submission | 24 | **Open, assigned to `diyan07-ctrl`** | Storyboard and checklist posted; video not recorded |
| #1 Epic | - | **Open** | Stays open until #25 and submission |

So the video is **not** the only remaining item: #14/#15 (credentials and cost approval), #23
(human decisions) and #18 (licence call) are also open, and judge access is unresolved.

### Official criteria (rules section 6.2, equal weight), internal self-assessment

No numeric score is given; this is an evidence review, not a prediction.

| Criterion | Strongest evidence | Weakness |
|---|---|---|
| Technological Implementation | Deterministic engine, checkpoint/restore/ForkCast with independent verifiers, SQLite schema 4, 547 backend + 141 browser tests, API p50 6.6-34.6 ms (40 samples) | No hosted Microsoft service is executed; Azure template is compiled in CI but not provisioned |
| Agentic Design and Innovation | Role-scoped tools, deterministic Evidence Auditor, staged workflow with traces, tested failure paths | Never run against a hosted model; Three Stories and highlights are rule-based. Weakest criterion |
| Real-World Impact | Evidence-linked explanations, audience framing with identical facts, reproducible experiments | Synthetic only; no public deployment; local-first |
| User Experience and Presentation | Stable replay (page CLS < 0.001, zero scroll drift), axe-clean routes in three locales, one-click evidence drawer | No final video; Event Wire rows still move inside their panel (animated, reduced-motion aware); no screen-reader pass |
| Adherence to Category | Five-stage pipeline works end to end on synthetic events | The AI-powered element is unproven until #14/#15 run |

### Submission eligibility

| Requirement | Status |
|---|---|
| Fits the challenge (ingest, interpret, explain, render, personalize) | PASS (rule-based; see AI row) |
| Synthetic, football-realistic data; no real footage | PASS (seeded generator; reel uses no footage) |
| Working product runs on its platform | PASS (local run; CI and smoke) |
| Real Microsoft/Azure technology use | PARTIAL: Agent Framework optional and offline-verified; Foundry and Azure not executed (BLOCKED on #14) |
| Public GitHub repository | PASS |
| Judge access without charge through Nov 10 | BLOCKED: no deployment; repository checkout is the only route |
| Licence and provenance | BLOCKED: #23 human decisions; no root LICENSE |
| Pitch, description, technology list in English | PASS (docs/HACKATHON_SUBMISSION_PACKAGE.md; needs final read-through) |
| Video under two minutes, public URL | BLOCKED: not recorded (#25) |
| Submitted before Oct 27 11:59 PM Pacific | NOT DONE |

**Judge-experience rehearsal.** The exact storyboard path (play at 4x, first goal cue, Inspect
evidence, Three Stories, persona/language switch, highlight reel, Control Room via runbook) is
covered by the browser tests listed above, and the reel and a pinned frame were rendered and
inspected. The Control Room portion needs a locally generated operator token and about a minute
of real time, so it must be prepared before recording. A full human rehearsal with a microphone
was not performed.

## O. Final completion pass, 2026-10-25 (late)

**Classification: DEMO READY, SUBMISSION BLOCKED.** Unchanged, and now with every blocker named and
owned. The video is **not** the only open item.

**What changed in code (branch `release/judge-access`).**
1. *Judge-experience defect:* the public recap quota (30/min, shared by all visitors) was exhausted by one
   viewer in about 30 s because the client posted a recap per second. Recap POSTs fell from 11 to 1 per 12 s
   of playback; the deployed-URL suite plays 35 s at 4x with zero HTTP 429.
2. *Public-mode clarity:* `GET /api/deployment` (read-only, reveals only the mode) and a notice on the Control Room,
   Data Hub and Director Studio routes explaining that operator tools are disabled on the public demo; absent in local mode (tested both ways).
3. *Deployment readiness:* `render.yaml` (free plan, public read-only, auto-deploy off) and `docs/JUDGE_ACCESS_DEPLOYMENT.md`
   with the provider decision from official documentation; the deployed-URL suite (`frontend/tests-deployed`) now covers the
   judge journey, highlight reel, axe scan and the public security boundary (nine protected paths return 403).
4. *Test determinism:* `glass-layout` raced the tactics response (17 momentum buttons appeared between two control snapshots) in a loaded run;
   it now waits for them. No assertion was loosened.
5. *Docs:* README status rewritten (it was dated 2026-10-23 and described merged PRs as pending), licence memo, third-party licence inventory, performance evidence.

**Verification (final head of this branch).** Backend `pytest tests`: **549 passed, 0 failed, 0 skipped** (504 s). Playwright full suite:
**142 passed** (9.2 min, clean run). Deployed-URL suite against the production configuration (public-readonly, container flags, loopback): **4 passed**.
`tsc -b` clean; production build clean; `npm audit --omit=dev`: 0 vulnerabilities; `pip_audit` on `requirements.txt` and `requirements-runtime.txt`: none;
docs validator passed; `foundry_smoke.py --check-only`: `sdk_compatibility_ok`, `authenticated: false`, `network_call: false`. Post-merge CI on `d7bb7a7`
(the previous docs merge) was green; CI for this branch is recorded in the PR.

**Not run / not verified:** any hosted deployment (none exists); Docker image build (daemon not running locally; the CI container job builds it);
a screen-reader pass; a human rehearsal of the video; GitHub-side secret scanning (API returned 404 for this account).

### Gates and owners (nothing here is complete)

| Gate | State | Owner and next action |
|---|---|---|
| Judge-access URL | BLOCKED: no URL; Blueprint and tests ready | [#108](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/issues/108), satvikp-coder (provisional): apply `render.yaml`, run the deployed suite, record the URL |
| Demo video, public URL, < 2:00 | BLOCKED | [#25](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/issues/25), diyan07-ctrl: record, publish, post URL |
| Final submission | BLOCKED: Representative unconfirmed | [#109](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/issues/109): confirm the Representative (rules 4.10), then submit |
| Live Foundry validation | BLOCKED: no credentials, cost approval needed | [#14](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/issues/14), satvikp-coder: supply endpoint and deployment, approve cost in writing, run `foundry_smoke.py --confirm-cost` |
| Multi-agent live run | Offline verified; live item depends on #14 | [#15](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/issues/15) |
| Remotion decision | OPEN: CLI + WebM shipped, Remotion not adopted | [#18](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/issues/18): accept the deviation or confirm licence eligibility |
| CC0 declaration, root licence, independent review | OPEN | [#23](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/issues/23): author confirms CC0; four contributors choose a licence; `vishwam17-ctrl` reviews ([memo](LICENSE_AND_RIGHTS_DECISIONS.md)) |
| Screen-reader pass | NOT DONE | Human task: NVDA + Chrome (or VoiceOver + Safari) over Match Intelligence, the proof drawer and Three Stories |

### Category recommendation (the selection itself belongs to the Representative)

Rules section 4.2 lists Best Use of Microsoft Foundry, Best Enterprise Solution, Best Multi-Agent System and Best Azure Cloud Native Integration.
The best-supported by verified evidence today is **Best Multi-Agent System** (distinct staged roles, tool allowlists, a deterministic Evidence Auditor,
observed-stage traces and tested failure paths), but its rule asks for a *demonstration* and the only hosted-model run is blocked on #14, so it is conditional.
**Best Enterprise Solution** is the credible second (read-only public boundary, 549 + 142 tests, six CI jobs, threat model, deployment template).
Foundry and Azure Cloud Native are not supportable until #14 or an Azure deployment exists. No selection was made.
