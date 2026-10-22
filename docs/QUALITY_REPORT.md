> Current release evidence: [release readiness](RELEASE_READINESS.md). The dated results below remain historical; do not use them as current test counts.

> Historical report: statuses and counts below describe the dated build. See [current handoff](SATVIK_INDEPENDENT_HANDOFF.md) and [project status](PROJECT_STATUS.md) for the integrated baseline.

## Issue #22 follow-up verification - 2026-10-22

Starting baseline: `origin/main` at `175b7ce` (merge of release verification PR #72). The merged release report already covers 297 backend tests, 66 Playwright cases, current engine/checkpoint/storage/security regressions and prior measured runtime benchmarks. This follow-up adds a focused request-boundary regression where coverage was still thin: malformed/overlong command operation IDs, intervention cutoff beyond match time, oversized tick batch and invalid command shape must return 422 without advancing or writing a command receipt. No engine, storage or API implementation changed.

- Focused test: `cd backend && python -m pytest tests/test_authoritative_engine.py::test_invalid_runtime_commands_are_rejected_without_mutation -q -p no:cacheprovider` ? **1 passed**.
- Final local candidate suite: `cd backend && python -m pytest tests -q -p no:cacheprovider` ? **298 passed** in **69.61 seconds**, one upstream Starlette/httpx `TestClient` deprecation warning. The run used Python 3.14.5 on Windows 10.0.26200; Python 3.13 was unavailable on this host. Tests use per-test temporary SQLite files.
- Existing browser baseline in the merged release PR: **66 Playwright Chromium tests passed** on tested head `14f676b38618287441b3318bb9ae0deaad9f126d` (documented in [PR #72](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/72)). They were not rerun for this candidate because Node/npm is absent here. Attempts to run `npm ci`, `npm run build`, `npm run validate:assets` and `npm run test:e2e` each stopped immediately because `npm` is not recognized. No candidate browser pass is claimed.
- Benchmark: `python scripts/sandbox-benchmark.py --samples 5`; raw output: [issue-22-sandbox-benchmark-win-python314.json](release-evidence/issue-22-sandbox-benchmark-win-python314.json). The harness now discards one warm-up per construction case and per preset. It measured 20 full-time runs (five seeds for each of four presets), all at 5,400 seconds with engine `zone-engine/1`, Python 3.14.5, Windows 10.0.26200, AMD Ryzen 7 8745HX. Run-time median **276.6 ms**, nearest-rank p95 **329.9 ms** (20 samples, so this tail estimate resolves to the maximum), event-throughput median **7,434.8 events/s**. Default scenario construction: 1,000 samples, median **0.141 ms**, p95 **0.245 ms**; maximal-name/attribute construction: 1,000 samples, median **0.147 ms**, p95 **0.253 ms**. cProfile reported 777 decisions and 142.3 microseconds mean cumulative time per decision. Peak memory was not measured. These are local observations, not service targets; no before/after claim is made.

The CI workflow runs backend tests, frontend build/assets, Playwright and the isolated release smoke journey. This local candidate was not pushed, so there is no exact-candidate CI result or review. The merged release PR's results are evidence for its tested head only.

# Quality report — first vertical slice

- `python -m pytest tests -q -p no:cacheprovider`: 6 passed (fixture invariants, golden scores, REST/WebSocket, idempotent out-of-order ingest, ProofTrail/overlay/recap, guarded agent auditor).
- TypeScript `tsc -b`: passed during local frontend build.
- The initial offline lockfile caused `npm ci` to fail in the first GitHub Actions run. After regenerating it from the public npm registry and adding the documented React/Tailwind Vite plugins, `npm ci` passed locally (83 packages), followed by `npm run build` (1,673 modules transformed; JS 241.94 KB, CSS 16.72 KB). [GitHub Actions run 38533210814](https://github.com/satvikp-coder/pulse-xi/actions/runs/38533210814) passed both frontend and backend jobs.
- Local HTTP smoke test: `/`, `/assets/main.js`, `/health`, `/api/matches`, `/metrics`, and `/overlays` returned 200 from an actual Uvicorn process.
- Browser visual test and cloud deployment: not yet run.
- No model inference, real match validation, or production latency measurement has occurred.

## Phase 2 verified slice — 2026-10-14

- Backend: `python -m pytest -q` — **8 passed**. Added tactical API and verifier checks for team attribution, supporting-event completeness, fabricated values and future timestamps. SQLite ingest test uses a temporary database and confirms recovery through a fresh connection. A replay-clock personalization test covers team/player focus and rejects unknown teams.
- Frontend: `npm run test:e2e` — production TypeScript/Vite build succeeded, **3 Playwright Chromium tests passed**. Tests load the real FastAPI-served app, seek through score and insight changes, open evidence, change matches, play/pause, check 390 px layout overflow, verify recap focus and toggle broadcast overlays.
- Optional Microsoft SDK: `agent-framework-foundry==1.13.0`, `agent-framework-orchestrations==1.3.1`, and `azure-identity==1.26.0` installed. Imports and offline two-agent workflow construction passed. No authenticated request or paid inference was made.
- [GitHub Actions run 38581351513](https://github.com/satvikp-coder/pulse-xi/actions/runs/38581351513) completed successfully: backend, frontend build and Chromium browser jobs all passed on `main`.
- Remaining: full interface localization, richer producer controls, an accessibility audit, live Foundry invocation with authorized credentials and Azure deployment.
