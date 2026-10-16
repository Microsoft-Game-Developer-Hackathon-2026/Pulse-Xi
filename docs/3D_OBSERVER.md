# Read-only event observer (#11)

The optional Sandbox Lab 3D view consumes the same selected match event and replay clock as the 2D pitch. It displays one recorded event origin and optional endpoint/path. It does not animate players, synthesize trajectories, infer speed, combine opposite coordinate frames or start a simulation. Missing locations leave the pitch visible with an explicit unavailable message.

## Library decision and delivery

Three.js 0.186.1 and React Three Fiber 9.4.0 are pinned; Fiber v9 supports the existing React 19 app ([official compatibility guide](https://r3f.docs.pmnd.rs/getting-started/installation)). Fiber was chosen for a small declarative scene, React lifecycle cleanup and demand rendering without an extra camera-control library. The renderer is dynamically imported only after selecting 3D. The default 2D app does not download the renderer chunk.

The scene uses [Canvas demand rendering, fallback and renderer ownership](https://r3f.docs.pmnd.rs/api/canvas). No idle animation loop or interpolation runs. Camera presets move immediately and are keyboard-accessible HTML buttons. Reduced-motion/mobile preferences default to low power; there is no automatic motion in either mode. Low power uses DPR 1; standard caps DPR at 1.5. Shadows, postprocessing and remote textures are absent. GPU/context loss or chunk failure is contained by an error boundary; the recorded 2D view remains available. Probe contexts and renderer resources are released on teardown.

## Coordinate and asset contract

Three.js uses Y up, X along the pitch and Z across it. The field spans X `[-50,50]`, Z `[-32,32]`; world units are display units, **not metres**. A valid normalized event point maps to `(x-50, 0.8, y*0.64-32)`. The event's team attacking frame is named in the UI. There is no cross-team transform in v1, so opposing events are not overlaid as if they shared tracking coordinates.

Original procedural pitch geometry contains sidelines, halfway line, center circle, penalty/goal areas and generic goalposts. Recorded origins use the team color; recorded endpoints use a neutral marker. Marker size is schematic. A static field GLB may replace only the procedural ground/goals after #12's validated export; failure must fall back to primitives. Keep a marker-only option and no runtime Blender requirement. Export contract: glTF 2.0, Y up, origin at pitch center, scale baked, field bounds 100×64 display units, neutral reusable materials, no external URLs/textures. Proposed budgets: complete field <=100 KiB GLB / 5,000 triangles; marker kit <=30 KiB / 1,500 triangles. Every asset requires a source/hash/license entry and #23 review before release approval.

## Data and future engine integration

`eventSnapshot.ts` is a pure validated adapter. It rejects future/cross-match events, unknown actor/recipient IDs and invalid coordinates. Props carry `ObserverScope {match_id, scenario_id?, branch_id?}` for a future authorized branch adapter. Optional IDs do not create branches or enforce backend session isolation; the production fixture path supplies only match_id.

Diyan's future frame needs an engine-owned schema with scenario/branch/match IDs, authoritative tick, revision, monotonic cursor, coordinate frame/units, modeled actor and ball positions, action/source IDs and provenance. Confirm lineup membership and snapshot/delta semantics. A cursor gap, branch change, revision rollback or missing base snapshot must trigger a real resnapshot before displaying interpolated frames. No such stream is currently connected. Do not map sparse v1 events into invented continuous frames.

Mahir receives the selected event ID, exact replay cutoff and existing pass-evidence DTO; the observer does not create new analytical claims. Vishwam receives the lockfile, lazy chunk budget, software-renderer tests and static asset contract. Deployment uses existing Vite assets and FastAPI; no GPU server or paid service is needed.

## Measured validation

Initial local production build: main JavaScript 273.52 kB / 85.04 kB gzip; optional renderer 906.58 kB / 244.05 kB gzip; CSS 30.16 kB / 7.79 kB gzip. Compared with the preceding workspace build, default JavaScript increased by 6.34 kB (2.26 kB gzip). Vite reports the optional chunk's >500 kB warning; the chunk remains gated by explicit 3D activation and the warning is not suppressed.

Actual headless Chromium/SwiftShader test on Windows 11, Intel64 Family 6 Model 186: first scene reported 17 draw calls, 552 triangles, 17 geometries and 1 renderer texture, with 768 ms from open to first ready. One additional frame occurred in the initial 500 ms sample. These are software-renderer startup/sample measurements, not physical GPU FPS or a cloud SLA. Diagnostics read Three.js renderer counters. A real rendered screenshot was inspected.

Run `npm run test:e2e` in frontend. Tests cover coordinate boundaries, wrong IDs/match, missing positions, future leakage, lazy loading, camera/keyboard operations, quality selection, replay sync, context loss and no-WebGL mobile fallback. CI explicitly enables Chromium's software renderer for repeatable WebGL coverage; that launch flag is test-only.
