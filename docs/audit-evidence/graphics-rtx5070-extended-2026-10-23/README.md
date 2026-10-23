# Physical RTX 5070 extended stability evidence — 23 October 2026

This is a local physical-GPU observation, not release approval or Intel Iris Xe certification.
The original bounded RTX report from PR #95 remains unchanged.

## Provenance and result

- Probe source: `0c532018e8990bed4b0fa2e84864de3f33a7cb18`, clean tree.
- Served production application: current main `0f45ca024bdcae294b74410023ff9533202416ed`.
  `frontend/src`, `backend/app`, assets and package manifests are unchanged between these commits.
- [Raw successful report](report.json): root and stability status **passed**.
- UTC start/end: 06:59:31.086 / 07:16:18.891. Extended phase alone:
  **906.109 seconds**, requested 900 seconds, **145 completed cycles / samples**.
- Physical NVIDIA RTX 5070 Laptop GPU; ANGLE NVIDIA D3D11 renderer throughout;
  driver 617.42; reported total VRAM 8,151 MiB. Chromium 156.0.8078.4.
- Core Ultra 9 275HX, 24 logical CPUs, 33,752,997,888 bytes reported RAM,
  Windows `10.0.26300`; initial viewport 1366×768, DPR 1.
- Fixed `comeback-1107`, cutoff 3500. Original production GLBs were ready;
  all seven file hashes and manifest bytes are recorded in the raw report.
  Windows CRLF manifest hash: `5339ea3a2d76d159fbf6a9c66e1909fb347d6118252e6bc099c3973663075144`.
- Cycles rotate Low/Medium/High and five camera controls, with 2D/3D remounts
  every six cycles. Each cycle waits five seconds and checks renderer/asset readiness.
- No recorded page errors, interruption, or renderer change. Every stability sample
  recorded visible document state. Browser debug diagnostics ended with exit code 0
  after normal cleanup; the raw debug log is excluded because it contains local paths.
- Observable JS heap range: 16,524,190–34,486,748 bytes. This bounded range is not
  a forced-GC leak assessment. GPU utilization, allocated VRAM and GPU timer queries
  are unavailable. The separate three five-second active samples per profile measure
  browser RAF intervals, not GPU execution FPS or continuous 15-minute active rendering.
  The extended phase includes demand-rendered idle waits between control changes.

## Failed attempt retained

[Attempt 1](attempt-1-failed.json), clean probe `bd8f5068c2f6d49b4c506b80bee892e4906b5e3d`,
failed after **35.008 seconds**, six cycles, when its page/context closed during a wait.
It must not be counted as a completed stability session. The trigger remains unknown.
The later instrumentation adds signal/disconnect diagnostics; one subsequent pass does
not prove that the earlier trigger was fixed or identify its cause.

## Reproduction and handoff

Use the isolated temporary-database startup and production build instructions in
[GRAPHICS_BENCHMARK.md](../../GRAPHICS_BENCHMARK.md), with the probe source above
and the application source above. Foundry must remain disabled. Then in PowerShell:

```powershell
$env:PULSE_GRAPHICS_URL='http://127.0.0.1:8877'
$env:PULSE_GRAPHICS_HARDWARE='1'
$env:PULSE_GRAPHICS_EXPECT_GPU='RTX 5070'
$env:PULSE_GRAPHICS_STABILITY_SECONDS='900'
npm.cmd --prefix frontend run measure:graphics
```

For Satvik's physical Iris Xe rerun, select the actual Intel device, replace the
expected GPU string with `Iris`, and retain independent raw output and machine metadata.
Do not substitute SwiftShader. Historical physical GLB Iris Xe evidence already exists
at source `42feb9ea146b392590475ba27116c0a99533b331`; it is a separate bounded report,
not this current-build extended result. Technical review and current matching Iris Xe
acceptance remain pending. Unreal remains NO-GO. No cloud services were used.

## Visual inspection

All nine new screenshots were opened and inspected: `low.png`, `standard.png`,
`high.png`, and `viewport-1920x1080.png`, `viewport-1366x768.png`,
`viewport-1024x768.png`, `viewport-768x1024.png`, `viewport-390x844.png`,
`viewport-360x800.png`. The pitch/assets/event markers render in all; controls wrap
on narrow screens. The three profile images precede the extended phase; six viewport
captures follow it. These are viewport/observer captures, not full-page accessibility
certification. Existing automated browser coverage remains separate.

## Subsequent helper review

The recorded probe predates the `observedWorkMs` completion guard. Its 906.109
seconds are total extended-phase elapsed time, including checkpoint writes; the
report does not separately measure checkpoint time. Its 145 actual observations
remain bounded switching evidence. The revised helper excludes checkpoint I/O
from its completion budget and rejects missing sample objects. Do not relabel this
historical run as a measurement made by that revised source or infer an exact
900 seconds of browser work from its elapsed time alone. A new hardware run is
not supplied by these offline regressions. The earlier page-closure cause remains
unproven.
