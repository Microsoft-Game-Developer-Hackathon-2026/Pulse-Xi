# Satvik independent development phase — 2026-10-16

The starting tree at 2bc43f7 was clean. PR #28 and draft #29 were green, without human reviews; organization main remained 888a2a9. The initial 23 backend / 10 browser tests and production build passed. Teammate engine branches or contract comments were not available. All work stays on Satvik feature/preparation branches; nothing is merged or closed.

## Delivered and prepared

| Issue | Status | Work and review boundary |
|---|---|---|
| #27 | Implemented; review required | Scoring/evidence/API review found no reason to change the formula. #29 integrates timeline selection and caches geometry-only packets at visible pass boundaries. Existing tamper, missing-data, cutoff and summary tests remain. PR #28 is still open. |
| #10 | Partially complete | PR #29 now includes paginated event loading, connection retry preserving the clock, request cancellation and synchronized team/pitch/pass selection. Real live scenario/restore/intervention integration remains blocked. |
| #11 | Read-only portion implemented; review required | PR #30: lazy R3F snapshot view, validated coordinates/IDs/cutoff, cameras, low-power/reduced-motion defaults, source labels, diagnostics and 2D fallback. Actual modeled observer frames are not connected. |
| #12 | Implemented; release review required | PR #31: original Blender sources, GLBs, generator, hashes/budgets/licenses, real asset loading/scale/material tests and procedural fallback. #23 approval remains pending. |
| #6 | Prepared; engine implementation blocked | PR #32: proposal metadata, typed UI states, focused checks and real-engine save/restore/idempotency/concurrency test gates. No checkpoint endpoint or continuation result is claimed. |
| #8 | Prepared; real experiments blocked | Proposed typed comparison DTO, consistency checks and responsive read-only component in an isolated development test harness. No production branch runner or fake API exists. |

Each PR is stacked on its predecessor for a combined local preview, with a focused diff against its explicit feature base. Review/merge parents in order and retarget children deliberately; do not merge the entire stack blindly or force-push.

## Validation and measured limits

- Backend: 27 tests passed, including original regressions and asset hash/container/budget/provenance tests.
- Production build and strict TypeScript passed. Separate contract TypeScript checks also pass.
- Main real-API browser/contract suite: **22 tests passed**, including the production-harness isolation assertion. It includes two checkpoint **metadata-only** tests, not engine continuation tests.
- Development comparison suite: 4 tests passed, covering contradiction/provenance checks, mobile, keyboard evidence and distinct loading/error/empty/zero/unavailable states. Actual development-only screenshots were inspected.
- Three original assets total 96,116 GLB bytes; field 920, ball 80 and marker 216 triangles. Standard scene: 9 draw calls / 1,216 triangles. Software-renderer first-ready samples vary with test concurrency (approximately 0.3–1.5 seconds); this is not a physical GPU FPS claim.
- Latest combined production build: default JS 274.84 kB / 85.46 kB gzip, optional renderer/loader 956.00 kB / 258.94 kB gzip, CSS 30.47 kB / 7.85 kB gzip. Optional chunk warning is retained. 2D does not fetch renderer or GLBs by default.
- CI exposed a canvas replacement/context-loss race. Stable-parent capture fixes the actual lifecycle gap; the original fast failure-injection assertion remains. A single-material clone regression was also fixed and tested so original GLB marker meshes remain visible.

## Handoffs and remaining gates

Diyan: review [checkpoint proposal](CHECKPOINT_INTEGRATION_PROPOSAL.md), [observer scope/frame requirements](3D_OBSERVER.md) and [comparison proposal](FORKCAST_DISPLAY_PROPOSAL.md). Supply the real complete state/RNG/queue, clock/revision/session, intervention, manifest and paired-trial contracts. No competing engine state or provenance implementation has been added.

Mahir: selected event ID and replay cutoff now synchronize with the pass inspector. The existing [pass evidence adapter](PASS_DIFFICULTY.md) remains isolated from shared Insight categories. Comparison evidence is proposed branch/trial/window-scoped metadata; the backend deterministic auditor must establish factual validity before model/broadcast publication.

Vishwam: pinned Three.js/Fiber/type dependencies and the lockfile are committed. The website uses static hashed GLBs with no runtime Blender/GPU service. Review [asset licenses/provenance and measurements](BLENDER_ASSETS.md) before release approval. CI adds the isolated contract test command; no paid service or cloud configuration changes were made.

## Local commands

Use `./scripts/start.ps1` from the repository root and open `http://127.0.0.1:8000/#/sandbox`. Manual backend: `python -m uvicorn app.main:app --reload --port 8000` in backend; frontend: `npm run dev` in frontend. No new environment variables are needed.

Tests: backend `python -m pytest tests -q -p no:cacheprovider`; frontend `npm run test:e2e` and `npm run test:contracts`; root `python scripts/asset_contract.py`. Blender rebuild instructions are in BLENDER_ASSETS.md. No separate lint script is configured.

Demo: generate seed → play/seek → select timeline pass → inspect evidence → open optional 3D → switch cameras/quality/style → return to 2D. Actual checkpoint→intervene→fork→compare remains blocked; the explicitly labeled comparison fixture is accessible only through the separate development harness, never the production FastAPI application.
