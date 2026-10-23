# Two clean RTX 900-second observed-work passes

Recorded 23 October 2026 UTC, completing 24 October IST. These are separate
uninstrumented repetitions, not replacements for either earlier failed attempt.
Both root reports and stability sections passed, and both probe processes exited 0.

| Attempt | Observed browser work | Total stability phase | Completed cycles/samples | Raw report |
|---|---:|---:|---:|---|
| 1 | 902,543.8727 ms | 902,889.0666 ms | 177 | [JSON](attempt-1/report.json) |
| 2 | 902,502.8011 ms | 902,742.0357 ms | 177 | [JSON](attempt-2/report.json) |

A separate [integrated public-mode pass](integrated-public/README.md) includes
the later recap-cooldown change at archived source `bbcce072`, with 902,233.1052 ms
observed work, 902,493.3331 ms phase time and 177 samples. Its raw report, build
hashes, nine inspected physical screenshots and separate headless public-mode UI
check retain their own source/configuration. It does not relabel either trial above.

Probe/application snapshot: clean at launch
`dc13f74e73c71927c7eddf17aaf010097ca6dd3d`. Application/observer code, asset
sources and dependency manifests are unchanged from main
`0f45ca024bdcae294b74410023ff9533202416ed`. This snapshot does not contain the
later PR #100 recap-cooldown UI change; an integrated-build measurement must be
identified separately. No production/probe/build file changed during these runs.

The production build was served by an isolated loopback FastAPI process with
separate temporary database paths, Foundry disabled and no cloud service.
Both requests used a fresh Chromium browser/profile against the same running
server/build. OS/driver caches were not purged; attempt 2 reused a warm server.
No protocol-debug logging was enabled. Other offline validation ran on the
workstation, so this is not an isolated peak-throughput benchmark.

## Hardware and workload

- NVIDIA RTX 5070 Laptop GPU; actual ANGLE NVIDIA D3D11 renderer in both reports.
  Driver 617.42; 8,151 MiB total VRAM, not measured allocation/utilization.
- Core Ultra 9 275HX, 24 logical CPUs, 33,752,997,888 RAM bytes reported by Node;
  Windows kernel `10.0.26300`; Chromium `156.0.8078.4`.
- Initial viewport 1366x768, DPR 1; fixture `comeback-1107`, cutoff 3500.
- Seven manifest GLB hashes validated; the four active v2 production GLBs loaded.
  Each attempt includes served HTML/JS/CSS/asset hashes and an artifact inventory.
- Low/Medium (`standard`)/High: five-second warmup and three five-second active
  free-camera samples each. RAF samples were approximately 165 callbacks/s,
  with 6.1 ms median and 6.2 ms p95 intervals. These are browser pacing metrics.
- Extended cycles alternate all three profiles and five cameras, remounting
  2D/3D every sixth cycle. Each completed cycle awaits the controls, ready assets,
  matching quality and visible canvas, then a five-second observation and sample.
  177 completed cycles imply 30 completed extended remount steps by this fixed
  schedule; that is derived from completed steps, not a GPU timer.
- `observedWorkMs` excludes JSON/checkpoint I/O and unfinished steps, but includes
  browser interaction, scheduling/IPC and the prescribed observation waits.
  `elapsedMs` includes checkpoint overhead; neither is continuous GPU execution.

Both runs recorded zero page errors, no page close during measurement and no
observed renderer change. All completed renderer samples identify the same RTX
5070 D3D11 device. All six final viewport captures and the separate 30-second idle
phase completed. All nine PNGs in each attempt were opened and visually inspected:
three quality captures, 1920x1080, 1366x768, 1024x768, 768x1024, 390x844 and 360x800.
They show the production field/stadium, recorded pass markers/evidence and wrapped
mobile controls. No screenshot was substituted from another run or edited.

The reports and PNGs were copied byte-for-byte. `artifact-inventory.json` records
their hashes/lengths and the build metadata; it does not recursively hash itself.
The seven original GLBs and every previous failed/successful report remain intact.
An evidence-specific `.gitattributes` rule keeps these new JSON files at LF on
Windows and Linux. A checkout-inventory test reproduced the earlier Windows
line-ending/hash mismatch and now verifies every published artifact's byte length
and SHA-256. Newly generated metadata was serialized with explicit LF; the original
Node report bytes and PNGs were not changed. Historical evidence is outside the rule.

## Limits and the unexplained closure

The earlier [clean failed run](../graphics-rtx5070-observed-work-2026-10-23/README.md)
stopped at 780.165 seconds observed work / 784.956 seconds phase time / 153 samples,
during a page wait. Its page closed without a recorded interruption, crash, page
error or browser disconnect before cleanup. The
[diagnostic pass](../graphics-rtx5070-observed-work-diagnostic-2026-10-23/README.md)
retains its original source and logging overhead. These new passes crossed the
old failure point without reproducing it; **the root cause is still unproven**.
No speculative renderer/lifecycle workaround is claimed.

Thirteen report regressions now include deliberate real Playwright page, context
and browser closure during an outstanding wait. They verify failed root/stability
status and preservation of completed observations. Deliberate closure is failure
injection, not reproduction of an uncommanded closure.

These runs do not measure GPU execution FPS/timer queries, utilization, allocated
VRAM, forced-GC leak absence, three 60-second performance trials or universal
hardware compatibility. Physical Iris Xe was intentionally excluded from this
sprint at the user's direction; no substitute result is claimed. Independent
technical/release review and the remaining issue acceptance gates still apply.

Use [the benchmark method](../../GRAPHICS_BENCHMARK.md) with
`PULSE_GRAPHICS_HARDWARE=1`, `PULSE_GRAPHICS_EXPECT_GPU=RTX 5070`,
`PULSE_GRAPHICS_STABILITY_SECONDS=900` and `npm.cmd run measure:graphics`.
No Azure, hosted inference, paid GPU, Unreal or submission operation occurred.
