# Revised RTX diagnostic run — observed-work budget passed

This instrumented attempt passed both root and stability checks in
[the unchanged raw report](report.json). It follows the separate
[failed 780-second observed-work attempt](../graphics-rtx5070-observed-work-2026-10-23/README.md).
Both outcomes must be retained. A later pass does not explain or erase that failure.

## Provenance

- Clean probe source: `1023a27762c18ff03a9bb4cb2a8cb920e6a7ab2f`. Probe code is
  byte-identical to `5246c08f84de88627ebd3dbdf91826382332c28c`; the intervening
  commit adds the preceding failed run's evidence only.
- Served production application: `0f45ca024bdcae294b74410023ff9533202416ed`.
  Application/observer code, assets and package manifests are unchanged. The
  [served build hashes](build-hashes.json) match the preceding attempt; no rebuild
  occurred during either measurement.
- Physical NVIDIA RTX 5070 Laptop GPU, driver 617.42, total VRAM 8,151 MiB;
  every collected renderer sample identifies ANGLE NVIDIA D3D11.
- Chromium 156.0.8078.4; Core Ultra 9 275HX, 24 logical CPUs, 33,752,997,888 bytes
  reported RAM, Windows `10.0.26300`; initial viewport 1366×768, DPR approximately 1.
- Fixed `comeback-1107`, cutoff 3500, production original GLB kit. First GLB
  readiness: 409.9 ms. The raw report contains all seven validated asset hashes.
  Windows CRLF manifest-byte hash:
  `5339ea3a2d76d159fbf6a9c66e1909fb347d6118252e6bc099c3973663075144`.

## Measured result and limits

UTC start/end: `2026-10-23T09:46:17.647Z` / `2026-10-23T10:03:00.866Z`.

| Field | Actual value |
|---|---:|
| Requested browser-work budget | 900,000 ms |
| Completed `observedWorkMs` | 903,125.2334 ms |
| Total extended-phase `elapsedMs` | 903,385.9376 ms |
| Completed cycles / samples | 177 / 177 |
| Recorded page errors | 0 |
| JS heap observations | 16,447,555–37,717,460 bytes |

The work counter excludes JSON checkpoint I/O and requires completed browser
steps/samples. The workload rotates Low/Medium/High and five camera controls,
with 2D/3D remounts every six cycles and five-second observation waits. These
waits are part of the documented switching workload; this is not continuous
15-minute active camera rendering. All completed samples recorded visible
document state and the same physical renderer. The final 30-second idle phase,
resource collection and six viewport captures also completed. The process exited 0.

`DEBUG=pw:browser,pw:protocol` was enabled to investigate the earlier closure.
Protocol messages were actually captured, but this run did not reproduce the
premature closure, so its cause remains **UNPROVEN**. Diagnostic logging adds
instrumentation overhead; do not use this result as an uninstrumented performance
comparison. Raw logs contain local paths and are retained outside Git.

The separate three five-second active RAF samples per profile recorded median
intervals around 6.1 ms and p95 around 6.1–6.2 ms. RAF pacing is not GPU execution
timing. GPU utilization/allocated VRAM and GPU timer queries remain unavailable;
heap samples do not establish leak absence. The earlier 906.109-second report
retains its original total-phase interpretation and source.

## Visual evidence and reproduction

All nine screenshots were opened and inspected: `low.png`, `standard.png`,
`high.png`, and `viewport-1920x1080.png`, `viewport-1366x768.png`,
`viewport-1024x768.png`, `viewport-768x1024.png`, `viewport-390x844.png`,
`viewport-360x800.png`. Assets and recorded event markers render; narrow-screen
controls wrap. The three profile captures precede the extended phase, and six
viewport captures follow it. Selected event: `comeback-1107-e0245`, 58:20.
These captures do not replace the separate browser fallback/accessibility tests.

Use [GRAPHICS_BENCHMARK.md](../../GRAPHICS_BENCHMARK.md) for production startup
with fresh temporary databases and Foundry disabled. From `frontend`:

```powershell
$env:PULSE_GRAPHICS_URL='http://127.0.0.1:8877'
$env:PULSE_GRAPHICS_HARDWARE='1'
$env:PULSE_GRAPHICS_EXPECT_GPU='RTX 5070'
$env:PULSE_GRAPHICS_STABILITY_SECONDS='900'
$env:DEBUG='pw:browser,pw:protocol'
npm.cmd run measure:graphics
```

#34 remains OPEN/optional. Current-build physical Iris Xe on the specified
i7-1355U/16 GB laptop and independent technical review remain pending. Satvik
must retain actual device/driver/browser/renderer, CPU/RAM/OS, source and all seven
asset hashes, workload/viewport/DPR, profile samples, observed/total duration,
raw JSON, screenshots and unavailable metrics. For a directly comparable diagnostic
run retain the logging setting; ordinary uninstrumented timings are a separate
measurement. No RTX or software result substitutes for the physical Iris Xe target.
No Azure operation, paid service, hosted inference, Unreal or release approval occurred.
