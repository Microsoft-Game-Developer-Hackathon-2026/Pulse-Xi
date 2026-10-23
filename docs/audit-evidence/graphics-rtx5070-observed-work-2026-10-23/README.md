# Revised RTX observed-work attempt — FAILED, 23 October 2026

The requested 900-second observed-work run **did not complete**. Both root and
stability status in [the unchanged raw report](report.json) are `failed`; the
process exited 1. Do not present the partial measurements as a successful soak.

## Source and machine

- Clean probe source: `5246c08f84de88627ebd3dbdf91826382332c28c`.
- Production application source: `0f45ca024bdcae294b74410023ff9533202416ed`.
  Application/observer code, assets and package manifests are unchanged between
  these commits. [Served build hashes](build-hashes.json) identify the built HTML,
  JavaScript and CSS; no rebuild occurred during measurement.
- Physical RTX 5070 Laptop GPU, ANGLE NVIDIA D3D11, driver 617.42, total VRAM
  8,151 MiB; Chromium 156.0.8078.4.
- Core Ultra 9 275HX, 24 logical CPUs, 33,752,997,888 bytes reported RAM,
  Windows `10.0.26300`; initial viewport 1366×768, DPR approximately 1.
- Fixed `comeback-1107`, cutoff 3500. Original production GLBs loaded in 383.9 ms.
  The raw report contains all seven validated asset hashes. The Windows CRLF
  manifest-byte hash is `5339ea3a2d76d159fbf6a9c66e1909fb347d6118252e6bc099c3973663075144`.

## Actual outcome

UTC start/end: `2026-10-23T09:24:31.156Z` / `2026-10-23T09:38:42.920Z`.
The completed observations recorded **780,165.3053 ms observedWorkMs** and
**784,956.4662 ms elapsedMs**, with **153 completed cycles/samples**. The work
counter excludes checkpoint I/O and unfinished work; total elapsed phase time
also includes the unfinished step that ended in failure. Browser work includes
the documented five-second observation waits, rather than continuous camera motion.

The page closed at `09:38:42.918Z` during a five-second wait. The failure is
`page.waitForTimeout: Target page, context or browser has been closed`.
No interrupt signal, page crash, page error or renderer change was recorded.
All completed renderer observations identify NVIDIA RTX 5070 D3D11. Diagnostic
browser logs show normal cleanup starting at `09:38:42.923Z`, after the page
closure, followed by process exit code 0. The probe itself exited 1. These facts
do **not** establish why the page closed. The raw debug log contains local paths
and is retained outside Git; no speculative cause or renderer repair is claimed.

Observed JS heap ranged from 16,587,095 to 40,492,577 bytes. This is not a
forced-GC leak assessment. GPU execution time, utilization and allocated VRAM
remain unavailable. Three five-second active RAF samples per profile completed
before the extended phase; their raw intervals are browser pacing measurements.

## Artifacts and limits

`low.png`, `standard.png` and `high.png` were opened and visually inspected. They
show the actual production kit and recorded pass `comeback-1107-e0245` at 58:20.
They were captured before the extended phase. The six final viewport screenshots,
final 30-second idle observation and final resource summaries were **NOT RUN**
because the page closed. No old screenshot or successful status was substituted.

The earlier [906.109-second total-phase report](../graphics-rtx5070-extended-2026-10-23/README.md)
retains its original source and interpretation. It predates the work-budget fix;
this failed revised run does not turn either report into a verified 900-second
observed-work pass. The earlier page-closure trigger also remains unproven.

## Reproduction and pending acceptance

Use the temporary-database production startup in
[GRAPHICS_BENCHMARK.md](../../GRAPHICS_BENCHMARK.md), Foundry disabled, then from
`frontend`:

```powershell
$env:PULSE_GRAPHICS_URL='http://127.0.0.1:8877'
$env:PULSE_GRAPHICS_HARDWARE='1'
$env:PULSE_GRAPHICS_EXPECT_GPU='RTX 5070'
$env:PULSE_GRAPHICS_STABILITY_SECONDS='900'
npm.cmd run measure:graphics
```

#34 remains open/optional: investigate the page closure in a controlled local
session, complete the revised RTX workload, obtain independent technical review,
and obtain Satvik's current-build physical Intel Iris Xe result on the specified
i7-1355U/16 GB laptop. The historical Iris Xe GLB result is separate evidence for
its recorded build. RTX and software results do not substitute for that device.
No cloud operation, paid service, Unreal work or human release approval occurred.
