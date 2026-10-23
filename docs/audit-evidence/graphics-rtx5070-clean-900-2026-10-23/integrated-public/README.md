# Integrated public-mode RTX pass — 23 October UTC / 24 October IST

This is an additional physical run of the corrected application/probe combination,
not a relabelling of the two [main-derived clean repetitions](../README.md).
Measured clean source: `bbcce072ab6f1100eb89cc88c958648d7605d617` on the
non-main `audit/cross-owner-integration` source archive. It combines open #98-#102,
including #100's recap-cooldown fix at `15f1ec2` and #101's trace fixes at `985520b`.
Its [six exact-source CI jobs passed](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/actions/runs/40008018221)
with 541 backend, 104 browser and 13 graphics-report tests. No combined PR was
opened; none of those focused PRs was merged or independently approved by this run.

## Physical result

- Root and stability status: **passed**, process exit 0.
- Requested observed work: 900,000 ms; completed **902,233.1052 ms**.
- Total stability phase: **902,493.3331 ms**; **177 completed cycles/samples**.
- Overall UTC start/end: `2026-10-23T19:02:52.028Z` / `2026-10-23T19:19:34.008Z`.
  Overall probe wall time includes setup, the three profile trials, a separate
  30-second idle/resource observation and final captures; it is not the phase field.
- [Unchanged raw report](report.json), SHA-256
  `ffa9350867be8c331ec31e8751d2f28b0a40c69e5434acec122bfa14180669f1`.
  All screenshots/report bytes were copied unchanged; the inventory verifies them.
- Zero recorded page errors, no page closure during measurement and no observed
  renderer change. Every completed renderer sample identifies NVIDIA RTX 5070 D3D11.
  The earlier uncommanded page-closure cause remains **unproven**, not fixed by a pass.

NVIDIA RTX 5070 Laptop GPU, driver 617.42, 8,151 MiB total VRAM; actual ANGLE
NVIDIA D3D11 renderer; Chromium 156.0.8078.4. CPU Core Ultra 9 275HX, 24 logical
CPUs, 33,752,997,888 reported RAM bytes, Windows 11 kernel `10.0.26300`.
Initial viewport 1366x768/DPR 1. Seven GLB manifest hashes were verified; the four
active v2 production GLBs loaded. [Build hashes](build-hashes.json) identify the
served production HTML/JS/CSS/assets after the recap fix. No build/source changed
during this measurement. OS/driver caches were not purged.

Fixture `comeback-1107`, cutoff 3500, all three profiles and five cameras; 2D/3D
remount every sixth extended cycle. Each completed step includes its controls,
ready assets/matching quality/visible canvas, five-second wait and actual sample.
177 completed cycles imply 30 extended remount steps in that fixed schedule.
`observedWorkMs` excludes checkpoint I/O and incomplete steps, but includes the
prescribed waits, browser interaction, scheduling and IPC. `elapsedMs` includes
checkpoint overhead. Neither is continuous GPU rendering or GPU execution timing.

Three five-second active RAF samples per profile follow five-second warmup.
These are browser frame-pacing samples, not GPU FPS or three 60-second trials.
The nine recorded RAF rates range from 165.035 to 165.137 callbacks/s; median
intervals are about 6.1 ms and p95 about 6.2 ms. Extended JS heap samples range
from 16,521,454 to 41,082,344 bytes without forced collection.
GPU execution timers, utilization/allocated VRAM and forced-GC leak assessment
remain unavailable. Bounded heap samples do not certify absence of memory leaks.

All nine physical PNGs were opened and inspected: Low/Medium/High and six viewports
1920x1080, 1366x768, 1024x768, 768x1024, 390x844, 360x800. The production geometry,
recorded pass/evidence and wrapped mobile controls are visible. Coordinates remain
recorded normalized samples, not fabricated tracking or continuous player motion.

## Separate local public-mode UI acceptance

The server used `PULSE_DEPLOYMENT_MODE=public-readonly`, driver 0, Foundry disabled,
privileged token/provider variables unset, distinct disposable Temp database paths,
loopback port 8882 and concurrency 32. [Sanitized configuration](server-configuration.json)
records the setup. This is a Windows process, not a claim about its container UID,
Azure identity, HTTPS ingress or cloud resources. A separate headless 2D browser
exercised the quota while the physical extended phase continued; this is not an
isolated peak-throughput comparison.

[UI report](public-ui-report.json) and `public-ui-limited.png` /
`public-ui-recovered.png` are **headless 2D HTTP/WS evidence**, not physical-GPU
measurements or Iris Xe evidence. The real server returned Retry-After 31; the UI
made zero recap requests during that cooldown, recovered, paused at cutoff 3000,
generated seed 123, retained 403 for private writes/traces and received the fixture
WebSocket snapshot. No page errors were recorded. Both screenshots were inspected
after waiting for the existing scroll-reveal opacity to settle; no renderer or
animation workaround was added. Earlier auxiliary path/capture attempts remain
outside Git and are not promoted as these settled captures.

The deployed Playwright configuration intentionally requires HTTPS and was NOT RUN
against loopback HTTP. These local observations do not satisfy public HTTPS/WSS,
Azure restart/rollback/cleanup, cost authorization or rights/release acceptance.
No Azure lookup/mutation, model invocation, paid GPU service, Unreal or submission
operation occurred. Physical Iris Xe was excluded from this sprint at user request;
its historical evidence and original issue gate are not rewritten.

Reproduce with the [benchmark method](../../../GRAPHICS_BENCHMARK.md), a production
build of the recorded source, the public-mode temporary-database setup above,
`PULSE_GRAPHICS_URL=http://127.0.0.1:8882`, hardware/expected RTX 5070 flags and
`PULSE_GRAPHICS_STABILITY_SECONDS=900`. Use the published original JSON/PNG and
their inventory; never substitute another source, old success or software GPU.
