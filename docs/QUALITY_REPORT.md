# Quality report — first vertical slice

- `python -m pytest tests -q -p no:cacheprovider`: 4 passed (fixture invariants, golden scores, REST/WebSocket, idempotent out-of-order ingest).
- TypeScript `tsc -b`: passed during local frontend build.
- Direct esbuild production bundle: `main.js` 232.7 KB and `main.css` 7.6 KB, generated successfully in the Windows sandbox.
- Normal Vite build: blocked here by `spawn EPERM` when Vite launches esbuild from Node. The direct bundler path proves the React source compiles but does not replace a normal Vite CI build.
- Browser visual test and cloud deployment: not yet run.
- No model inference, real match validation, or production latency measurement has occurred.
