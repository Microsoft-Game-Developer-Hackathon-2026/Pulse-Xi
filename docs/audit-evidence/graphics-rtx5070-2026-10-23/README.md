# Physical RTX 5070 bounded probe - 2026-10-23

[Raw report](report.json) records clean candidate source
`e927785eb05f1dd09a9d4c20019c656f340a28d2`, 04:30:57.771 to 04:32:40.150 UTC,
status `passed`. The served production application is unchanged from main
`07da294514f36820a7cf7d7c2dfacaab1adc735d`; candidate changes are probe/docs/CI only.
Fresh inventory: RTX 5070 Laptop GPU, NVIDIA driver 617.42, 8151 MiB total VRAM,
Core Ultra 9 275HX / 24 logical CPUs, 33,752,997,888 visible RAM bytes,
Windows 11 Home Single Language 10.0.26300. Chromium 156.0.8078.4 reports ANGLE
NVIDIA RTX 5070 D3D11; this is physical RTX evidence, not Iris Xe or SwiftShader.

All seven manifest GLB hashes were recomputed; the production kit was loaded,
not procedural-only. Seeded built-in comeback-1107 at cutoff 3500 was used for
profiles. Switching subsequently changes the cutoff as recorded by the script.
Viewport 1366x768, DPR approximately 1.0. Each profile has five seconds warmup
and three five-second active free-camera samples, followed by 12 camera/profile/
seek actions, three 2D/3D cycles and 30 seconds idle. No OS cache purge: fresh
browser/page loading followed by in-page warm reuse. GPU utilization, allocated
VRAM, GPU timer queries, power state and forced-GC leak conclusions are unavailable.

| Profile | RAF pacing FPS range (3 samples) | Median / p95 RAF interval | Draw calls / triangles |
|---|---:|---:|---:|
| Low | 165.09-165.12 | 6.1 / 6.2 ms | 15 / 5,556 |
| Medium (`standard`) | 165.09-165.10 | 6.1 / 6.2 ms | 25 / 19,380 |
| High | 165.10-165.17 | 6.1 / 6.2 ms | 34 / 33,044 |

These are browser RAF pacing observations on this display/workload, not renderer
throughput limits or GPU execution FPS. Do not compare directly with earlier
procedural scenes/software renderers. No before/after performance improvement is
claimed: rendering code and assets were not changed. A preceding candidate
probe at 8904f1d also completed; this report is the final instrumented workload.

Heap before/after interaction/after idle: 15,510,474 / 22,272,648 / 17,027,866
bytes; no forced GC. Zero page errors. A bounded observation cannot establish
absence of leaks, nor satisfy the proposed 15-minute stability session.

Screenshots were captured and visually inspected: geometry/materials were visible,
controls wrapped at narrow widths and the pitch remained visible; no renderer
failure or horizontal clipping was observed in these captures. Scrolling is
needed for controls/content larger than the viewport. This is not a full browser,
zoom or accessibility certification. Existing 102 browser regressions separately
cover missing/corrupt/slow assets, WebGL loss/unavailability, keyboard/reduced
motion and mobile fallback.

- Profiles: [Low](low.png), [Medium](standard.png), [High](high.png).
- Viewports: [1920x1080](viewport-1920x1080.png),
  [1366x768](viewport-1366x768.png), [1024x768](viewport-1024x768.png),
  [768x1024](viewport-768x1024.png), [390x844](viewport-390x844.png),
  [360x800](viewport-360x800.png).

The prior session's page closure was not reproduced in these two completed runs;
its triggering cause is unproven. The confirmed reporting defect was reproduced:
the original script leaves no report when startup fails. The new regression fails
against that original and passes with atomic per-run failure reporting; additional
tests cover page-closed exceptions, runtime errors and successful completion.
No renderer fix or universal elimination of page loss is claimed.

Satvik: reproduce on physical Iris Xe using the same source, assets and
[commands/workload](../../GRAPHICS_BENCHMARK.md), changing expected GPU to the
actual Iris renderer. Preserve a separate raw report. Issue #34 stays open until
its remaining physical cross-hardware/review and stability gates are met; #13
NO-GO and #23 human release/rights gates remain. No paid service was used.
