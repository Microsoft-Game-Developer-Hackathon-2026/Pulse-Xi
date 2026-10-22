# Performance audit - 2026-10-22

## Environment and measurement limits

Baseline `d19a898492f8c4a303caa576a9370411b21093ff`; backend bytes unchanged
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

The maximum-history failure above records the initial audit, not the final candidate. PR #79 follows the earlier PR #78 merge with atomic current-boundary capture, request-local independently proven prefix reuse and idle observer revision reads. At source 743916c the unchanged Windows bounded-forkcast test passed in 2.7 minutes, including offline verification. The same copied disposable dense store measured 102.57 seconds before the later increments and 30.06 seconds afterward; one observation per revision, not a latency percentile. See [detailed method and raw measurements](FORKCAST_COMPARISON_PERFORMANCE.md). No timeout or verification gate was weakened. Broad React Profiler, Web Vitals and long-session memory measurements remain outstanding.
