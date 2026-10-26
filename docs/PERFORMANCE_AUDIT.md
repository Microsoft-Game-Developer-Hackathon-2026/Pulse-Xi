# Performance audit - 2026-10-22

Historical measurements retain their original build and renderer identity.
They are not RTX 5070 or production-GLB Iris Xe certification. See the current
[release evidence ledger](RELEASE_EVIDENCE_LEDGER.md) and
[graphics probe instructions](GRAPHICS_BENCHMARK.md).

## Environment and measurement limits

Baseline `7d7a467307186f16396eb1c5b517721b03356c91`; backend bytes unchanged
in the candidate. Frontend numbers apply to the audit source increment, identified
by its PR commits. Raw evidence is in [audit-evidence](audit-evidence/).
This is a local laptop benchmark, not a hosted SLA or a physical GPU benchmark.

- OS: Windows-11-10.0.26300-SP0
- CPU identifier: Intel64 Family 6 Model 186 Stepping 3, GenuineIntel
- Python: 3.13.14

- API: new temporary SQLite stores, one loopback Uvicorn process, persistent HTTP
  client, concurrency 1, built-in first fixture, cutoff 3500. Twenty warm requests
  per endpoint plus one separately recorded first request. Other local processes
  were present; background load was not controlled. No remote/cloud measurements.
- A first request is not process-cold: fixture and OS caches can already be warm.
  P95 is nearest rank over 20 warm samples. No statistically credible P99 claim.
- Browser: Playwright Chromium, software WebGL where needed; 1280?844 / 390?844,
  reduced motion for the deterministic stability probe. Four replay speeds,
  25 observations roughly 100 ms apart per speed/viewport, starting at second1000.
  This is not React Profiler, INP, long-task or rendered-frame-rate measurement.

## HTTP latency

Reproduce from repository root:

```powershell
python scripts/benchmark-public-api.py --output .codex-progress/api-latency.json --samples 20
```

| Endpoint | Warm P50 ms | Warm P95 ms | Payload bytes | Samples |
|---|---:|---:|---:|---:|
| health | 0.96 | 1.60 | 78 | 20 |
| matches | 3.78 | 5.11 | 6296 | 20 |
| match | 4.15 | 5.00 | 2097 | 20 |
| events | 5.58 | 6.78 | 176206 | 20 |
| state | 3.35 | 4.65 | 182 | 20 |
| metrics | 3.75 | 4.34 | 448 | 20 |
| tactics | 6.59 | 8.74 | 14575 | 20 |
| insights | 9.12 | 11.65 | 5451 | 20 |
| overlays | 11.84 | 15.79 | 3483 | 20 |
| control-chaos | 11.18 | 14.91 | 21379 | 20 |
| recap | 23.45 | 33.70 | 738 | 20 |
| data-hub | 19.38 | 22.35 | 8373 | 20 |
| export | 34.35 | 36.88 | 171523 | 20 |

The separate real HTTP release smoke passed in 9.15 s under concurrent test load:
startup-to-health2573.4 ms, first scenario creation15.05 ms. These are individual
observations, not distributions. It created/imported a scenario, stepped a real
runtime, saved original UTC, restored an isolated branch, applied an intervention,
ran a paired experiment and invoked both independent verifiers. No dedicated
runtime mutation/large-library/provider percentile study was performed.

## Reproduced replay defects and correction

| Observation | Before | Candidate |
|---|---|---|
| Recap debounce | 220 ms debounce repeatedly cancelled by 200 ms tick | Analysis samples at 1 Hz while playing; exact paused cutoff |
| Missing metrics during first 0.5? probe | 19/25 desktop observations; 16/25 mobile observations | 0/25 at each of four speeds on each viewport |
| Recap content | Cleared on every clock update | Same-audience, same-source past packet retained with actual cutoff |
| Control vs Chaos | Exact-clock gating unmounted its large content tree | Previous valid same-window packet retained; source cutoff labelled |
| Pass Difficulty | New pass boundary replaced detail with loading line | Public same-source past packet retained; private runtime exact-key behavior unchanged |
| Tactical selection | Playback pass could change selected analyst team | Passive playback no longer changes the inspected team |
| Variable text/rows | Moving section boundaries | Focusable local readers; short tactical copy reserves four lines without clipping |

After correction, **all 200 sampled observations** had visible metrics and recap,
zero document-scroll displacement and **0 px studio-anchor displacement**, across
0.5?/1?/2?/4? and both viewports. Each 2.5 s window issued6?9 combined
metrics/tactics/recap requests (only those three endpoints were counted). These
short samples do not establish long-session memory stability or every fixture's
layout behavior. The old failing probe output is retained in the ignored journal
evidence; the raw complete baseline frame/request series was not captured.
No unmeasured numeric request-reduction claim is made.

Retained packets cannot exceed the current cutoff; backward seeks hide them.
Recaps also require identical locale/persona/favorites. Metrics and tactics are
public recorded-source reads; no private owner data was added to this cache.
Late responses remain guarded by AbortController/active checks. Explicit navigation
can still scroll, and internal readers remain keyboard accessible.

## Bundle and rendering observations

Production build: entry JS387.97 kB (119.08 kB gzip), CSS90.64 kB (18.92 kB gzip),
lazy scene983.87 kB (265.44 kB gzip). Prior main's Atelier evidence records entry
~386.89 kB and CSS90.00 kB; the increment is approximately1.08 kB JS /0.64 kB CSS.
The lazy 3D scene size is unchanged. No dependency or second renderer was added.
The existing >500kB scene warning remains; hiding that warning is not an optimization.

The full browser run reported25 draw calls,19380 triangles,22 geometries and2
textures for its observer case; first-ready1160.9 ms under software rendering and
parallel test load. One demand-rendered frame in a500 ms idle sample is **not** a
1?2 FPS performance claim. No new physical Iris Xe/RTX5090 comparison was run.

## Remaining measurements

- React render/commit profile and actual event-to-paint trace decomposition.
- Long-session heap trends, long tasks, LCP/CLS/INP under realistic user load.
- Dense imported libraries and concurrent authenticated command latency.
- Public judging access/cold start and authorized hosted provider latency/cost.
- Large-history ForkCast probe is reported separately; ordinary bounded smoke
  success is not proof of the maximum-history latency bound.

## Maximum-history result

The dedicated test failed locally on this candidate at the unchanged90-second
comparison-table wait after a completed10-branch experiment. It passed no false
success and showed no API alert. The same symptom is recorded in the earlier
unchanged-main baseline. Source inspection identifies repeated full histories:
`bundle()` reconstructs branches, `verify_bundle()` invokes `verify_manifest()`
and reconstructs again for parent/comparison checks, and `comparison()` reconstructs
once more. This is a concrete profiling target, not a completed optimization.
Changing verifier/experiment source also changes the versioned implementation
hash. A Diyan-reviewed reuse of already verified states/comparison is needed;
this frontend correction intentionally does not alter canonical engine behavior,
verifiers or hash-bound source. No test timeout was increased or test skipped.

## Subsequent performance delivery

The maximum-history failure above records the initial audit, not the final candidate. PR #79 follows the earlier PR #78 merge with atomic current-boundary capture, request-local independently proven prefix reuse and idle observer revision reads. At source 974a6bc the unchanged Windows bounded-forkcast test passed in 2.7 minutes, including offline verification. The same copied disposable dense store measured 102.57 seconds before the later increments and 30.06 seconds afterward; one observation per revision, not a latency percentile. See [detailed method and raw measurements](FORKCAST_COMPARISON_PERFORMANCE.md). No timeout or verification gate was weakened. Broad React Profiler, Web Vitals and long-session memory measurements remain outstanding.

## Passive replay stability (2026-10-24, base `3648587`)

Workload: built-in recorded match, 12 s wall-clock of uninterrupted playback after the
analysis panels had settled, Chromium (software rendering), local backend, one run per
configuration (`frontend/tests/replay-stability-metrics.spec.ts`, which now enforces the
thresholds below). Requests are counted while playing. These are single-run local
numbers, not percentiles.

| Viewport / speed | Fan Lens requests (before → after) | Metrics / Tactics / Recap / Control-Chaos | Page CLS excl. Event Wire | Document scroll drift |
|---|---|---|---|---|
| 1280px / 1× | 61 → 13 | 11 / 11 / 11 / 11 | 0.00006 | 0 px |
| 1280px / 4× | 61 → 13 | 12 / 11 / 11 / 11 | 0.0004 | 0 px |
| 390px / 2× | 61 → 13 | 11 / 11 / 11 / 11 | 0.0005 | 0 px |

Findings and fixes:

- **Fan Lens fetched on every 200 ms replay tick** (61 requests / 12 s) while all other
  analytics used the 1 Hz analysis cutoff. It now uses the same cutoff (paused seeks stay
  exact); alert windows are evaluated against that cutoff, never a future second.
- **Event Wire grew from 137 px to ~560 px** as the first seven events arrived. Its list
  now reserves seven rows, so the panel's bounds are constant from the first frame.
- **Row motion inside the Event Wire is content-driven**: inserting a new event moves the
  existing rows down inside the fixed-size panel (CLS contribution 0.019 at 1×, 0.266 at
  4×, reported separately as `eventWireRowShift`). It is not page movement; nothing outside
  the panel shifts, and the test gates page-level shift below 0.01. The Event Wire is now a
  fixed seven-row viewport (exact height, internal scroll) and existing rows glide 220 ms
  into place via transform (`useFlipList`); the glide is skipped under
  `prefers-reduced-motion`. The browser's layout-shift API still reports the underlying row
  position change, so `eventWireRowShift` is unchanged; the glide is a presentation change,
  not a reduction in that metric. A test asserts constant bounds, newest-first order, no
  future events, and zero animations under reduced motion.

Not measured here: INP, LCP, heap growth, long tasks, React Profiler render counts.
Pass-difficulty requests (10–37 / 12 s) are keyed to the last visible pass, not the clock.

## PR #100 CI timeout (investigated 2026-10-24)

`tests/test_deployment_provisioning.py::test_provision_requires_digest_before_contacting_azure`
failed once on main run 40017120238 with `subprocess.TimeoutExpired` (20 s limit while the
test launches `powershell -NoProfile ...`); that run and two others were pushed within ~70 s
of each other. The next main run (#102) passed, and the complete local backend suite on
`3648587` passed: **541 passed, 0 failed, 0 skipped** (281 s). Not reproduced; classified as a
probable runner-load stall on PowerShell cold start, not proven. No timeout, assertion or
production code was changed. If it recurs, capture runner CPU/queue data before changing the test.

## API latency, local loopback (2026-10-24)

Command: `python scripts/benchmark-public-api.py --output docs/benchmarks/public-api-2026-10-24.json --samples 40`.
Source `388ea9a` (PR #105 head). Windows 11, Intel Family 6 Model 186 (12 logical CPUs),
15.7 GB RAM, Python 3.13.14. Empty temporary SQLite stores, built-in fixture, concurrency 1,
sequential requests, no provider calls. The first request is **not** a process-cold estimate.
40 warm samples per endpoint: p50/p95 are reported, p99 is not (too few samples). Raw
samples are in the JSON. All 13 endpoints returned successfully.

| Endpoint | Samples | p50 ms | p95 ms | Max ms | Bytes |
|---|---:|---:|---:|---:|---:|
| health | 40 | 6.6 | 8.7 | 23.2 | 78 |
| matches | 40 | 17.1 | 29.4 | 43.4 | 6296 |
| match | 40 | 22.6 | 31.0 | 32.8 | 2097 |
| events | 40 | 26.1 | 46.9 | 60.5 | 176206 |
| state | 40 | 17.7 | 21.1 | 30.7 | 182 |
| metrics | 40 | 17.5 | 27.4 | 28.0 | 448 |
| tactics | 40 | 27.0 | 38.7 | 44.3 | 14575 |
| insights | 40 | 28.3 | 47.1 | 54.1 | 5451 |
| overlays | 40 | 34.6 | 41.3 | 45.4 | 3483 |
| control-chaos | 40 | 20.4 | 28.2 | 75.5 | 21379 |
| recap (POST) | 40 | 34.2 | 47.5 | 47.8 | 738 |
| data-hub | 40 | 11.4 | 32.8 | 34.7 | 8373 |
| export | 40 | 20.0 | 29.6 | 31.3 | 171523 |

Not covered by this benchmark: runtime/Control Room mutations, checkpoint save/restore,
ForkCast. `scripts/release-smoke.py` ran those once on disposable stores (cold scenario
create 17.6 ms, 4 audit records, comparison available, both independent verifiers passed);
that is a single run, not a distribution. Maximum-history ForkCast remains the known slow
path documented above.

## Other measurements (2026-10-24)

- Route health (`frontend/tests/route-health.spec.ts`): 5 routes x 1440/390 px, real
  backend; each route's own heading is visible, no console errors, no `pageerror`, no
  HTTP 5xx from `/api/`, horizontal overflow <= 1 px. 10/10 passed. This is a smoke
  check, not a Web Vitals measurement.
- Production bundle: 2.5 MB of `dist/assets` in total (largest: `SceneCanvas` chunk, then
  the stadium GLB, then the main `index` chunk; Vite warns a chunk exceeds 500 kB).
- `npm audit --omit=dev`: 0 vulnerabilities. No credential-shaped strings in the built
  bundle; the only match for `PULSE_*TOKEN` is an environment variable *name* in the
  disabled-imports help text.
- Still unmeasured: field INP and React Profiler render counts.

## Browser metrics, one run (2026-10-24)

Command: `PULSE_WRITE_BENCHMARK=../docs/benchmarks/browser-metrics-2026-10-24.json npx playwright test tests/browser-metrics.spec.ts --project=regression`.
Chromium via Playwright on software rendering, local backend, fixture `comeback-1107`,
same machine as the API table. **Two runs, the second reported**: no percentiles across runs. Raw JSON:
[browser-metrics-2026-10-24.json](benchmarks/browser-metrics-2026-10-24.json).

| Measure | Result |
|---|---|
| Panels and recap populated (wall clock from `goto`) | 1201 ms |
| DOMContentLoaded / load | 472 ms / 472 ms |
| LCP | 1048 ms (software rendering, local server; not a field number) |
| API requests during initial load | 11 |
| Synthetic interaction (speed-button click → two animation frames), 30 samples | p50 25.8 ms, p95 30.7 ms, max 42.2 ms. **Not field INP** |
| Long tasks (>50 ms) over the whole session | 2 tasks, 208 ms total, longest 154 ms |
| Replay at 4×, 60 s wall | reached 5400 s (match end 5400 s); 359 API requests |
| JS heap after forced GC, samples every 15 s | 4.9, 5.8, 5.9, 6.2, 6.2 MB |
| DOM nodes at end | 1457 |

Run-to-run variance is large: an earlier identical run measured ready 2258 ms, LCP 1732 ms,
6 long tasks (longest 274 ms) and interaction p95 39.4 ms, on the same machine minutes
apart. The table is the second run; treat all timings as roughly +/-2x until repeated.

Limits: the replay reached the end of the match after roughly 45 s, so the last heap
samples are end-state, not mid-playback; heap growth of 1.3 MB over one match is a short
horizon, not a leak test. The 154 ms long task was not attributed to a component. The
test asserts only sanity bounds (clock advanced, heap growth under 25 MB).

## Public-demo mode: request budget and capacity (2026-10-25)

Environment: Windows 11, 12 logical CPUs, Python 3.13; `uvicorn` with the container's flags
(`PULSE_DEPLOYMENT_MODE=public-readonly`, `--limit-concurrency 32`, `--no-access-log`) on loopback,
built frontend, empty disposable SQLite. Not measured on Render or any hosted provider.

**Recap request budget (a real judge-experience defect, fixed).** Public mode shares one
30-per-minute quota across all visitors for `POST .../recap` and `POST /api/matches/generate`. Before
this change the client posted a recap about once per second while playing (11 per 12 s, measured
earlier in this document), so one viewer exhausted the whole budget in about 30 s and everyone then
saw "recap limited". The client now refreshes the recap only when a new verified moment appears,
every 10 s while playing, or immediately on a paused or backward seek (`useRecapCutoff`; never a
future cutoff). Measured with the replay-stability test: **1 recap POST per 12 s** of playback at
1x, 4x and mobile 2x (asserted <= 5). The deployed-URL suite plays 35 s at 4x against the production
configuration and asserts zero HTTP 429; that is more POSTs than the budget under the old cadence.

**Highlights endpoint under load** (`GET /api/matches/comeback-1107/highlights?limit=12`, one
keep-alive connection per client, public mode):

| Clients | Requests | Status | p50 | p95 | Throughput |
|---:|---:|---|---:|---:|---:|
| 1 | 100 | 200 x100 | 23.7 ms | 26.1 ms | 31/s |
| 8 | 400 | 200 x400 | 160 ms | 199 ms | 40/s |
| 32 | 800 | 200 x656, 503 x144 | 586 ms | 739 ms | 42/s |
| 64 | 640 | 200 x243, 503 x397 | 556 ms | 951 ms | 33/s |

Reading: the single process saturates near 40 requests/s on this machine (about 24 ms of CPU per
call); above 32 concurrent connections the server sheds load with 503 by design. The GET is not
covered by the public quota, which applies only to the two POSTs above. A first attempt that opened a
new connection per request reported 777 ms p50; that was Windows loopback connection setup in the load
script, not server time, and is discarded. Comparable single-client p50 across endpoints, public vs
local mode: health 3.5/3.1 ms, matches 5.3/14.3, events 12.6/22.1, metrics 4.1/13.4, insights
20.5/23.5, highlights 17.8/30.7 (15 sequential requests each, medians only).

**Risk to state plainly:** Render's free instance has far less CPU than this machine. A few concurrent
judges should be fine; a crowd would see slow or shed (503) requests. Free instances also sleep after
15 idle minutes (about a minute to wake). See [JUDGE_ACCESS_DEPLOYMENT.md](JUDGE_ACCESS_DEPLOYMENT.md).
