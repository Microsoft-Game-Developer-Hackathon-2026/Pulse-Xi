# Quality report — first vertical slice

- `python -m pytest tests -q -p no:cacheprovider`: 6 passed (fixture invariants, golden scores, REST/WebSocket, idempotent out-of-order ingest, ProofTrail/overlay/recap, guarded agent auditor).
- TypeScript `tsc -b`: passed during local frontend build.
- Direct esbuild production bundle: `main.js` 238.9 KB and `main.css` 12.5 KB, generated successfully in the Windows sandbox. The final source passed `tsc -b`.
- Normal Vite build: blocked here by `spawn EPERM` when Vite launches esbuild from Node. The direct bundler path proves the React source compiles but does not replace a normal Vite CI build.
- Local HTTP smoke test: `/`, `/assets/main.js`, `/health`, `/api/matches`, `/metrics`, and `/overlays` returned 200 from an actual Uvicorn process.
- Browser visual test and cloud deployment: not yet run.
- No model inference, real match validation, or production latency measurement has occurred.
