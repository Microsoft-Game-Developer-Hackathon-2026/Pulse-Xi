# Quality report — first vertical slice

- `python -m pytest tests -q -p no:cacheprovider`: 6 passed (fixture invariants, golden scores, REST/WebSocket, idempotent out-of-order ingest, ProofTrail/overlay/recap, guarded agent auditor).
- TypeScript `tsc -b`: passed during local frontend build.
- The initial offline lockfile caused `npm ci` to fail in the first GitHub Actions run. After regenerating it from the public npm registry and adding the documented React/Tailwind Vite plugins, `npm ci` passed locally (83 packages), followed by `npm run build` (1,673 modules transformed; JS 241.94 KB, CSS 16.72 KB). The updated GitHub Actions run is pending.
- Local HTTP smoke test: `/`, `/assets/main.js`, `/health`, `/api/matches`, `/metrics`, and `/overlays` returned 200 from an actual Uvicorn process.
- Browser visual test and cloud deployment: not yet run.
- No model inference, real match validation, or production latency measurement has occurred.
