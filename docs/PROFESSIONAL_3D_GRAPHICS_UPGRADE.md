# Professional football graphics upgrade

## Environment and integration

Inspected on Windows 11 Home 10.0.26300: Intel Core i7-1355U, 16GB installed RAM, Intel Iris Xe integrated graphics, driver 32.0.101.7088, 512GB NVMe SSD. WMI reports about 2GB adapter memory; this is not a measurement of dedicated VRAM. C: had approximately 124GB decimal free at inspection. The Python launcher lists Python 3.13.

| Tool | Version/status | Integration and verification |
|---|---|---|
| Blender / bpy | 5.2.2 LTS, already installed | `C:/Program Files/Blender Foundation/Blender 5.2/blender.exe`; background scripts, editable sources, export and clean reimport executed |
| Codex CLI | 0.162.1 | Direct CLI execution verified; no unverified MCP/server/plugin installation |
| Python / Node / npm | 3.13.14 / 24.12.0 / 11.6.2 | Existing runtime/toolchain retained |
| Git / Git LFS | 2.53.0.windows.2 / 3.7.1 | Existing tools retained; these small sources do not require LFS |
| Three / React Three Fiber | 0.186.1 / 9.4.0 | Existing exact versions retained, lazy browser renderer verified |
| Khronos glTF Validator | 2.0.0-dev.3.10 | Official repository/package verified; exact development dependency added; seven exports checked |
| glTF Transform | Not installed | No measured need for another optimization/decoder pipeline |
| Meshopt / Draco | Export bridges bundled with Blender | Availability logged by Blender; compression not enabled, browser requires no decoder |
| KTX2 / Basis utilities | Not installed | No external texture payload; generated 128px albedo does not justify this dependency |
| Unreal Engine | No Editor installation found | Epic Launcher 20.1.4 exists; no Unreal project/editor connection claimed |

Unreal is optional here. This integrated-GPU/16GB system is below Epic's [recommended 32GB RAM / 8GB graphics-memory development configuration](https://dev.epicgames.com/documentation/en-us/unreal-engine/hardware-and-software-specifications-for-unreal-engine). Installing a large Editor solely for optional cinematics was not justified. A future Editor installation would use the existing official Launcher, account/license flow and a reviewed storage allocation. No Pixel Streaming, GPU server or paid service was introduced.

`scripts/blender.ps1` discovers official installations or `PULSE_BLENDER_PATH`. `scripts/verify-blender.py` creates a temporary mesh, PBR material, point light and camera; exports/reimports GLB, checks content and removes temporary files. It uses `--python-exit-code 1` so Blender script errors cannot masquerade as success. The initial area-light probe correctly exposed glTF's unsupported area-light export; the supported point-light round trip passes. bpy runs inside Blender, not the FastAPI Python environment.

## Graphics implementation

- **Field:** original 105×68 reference geometry, configurable within international-reference ranges via CLI; 16.5 penalty/5.5 goal area depth, 9.15 centre/penalty arcs, 11 penalty marks, corner arcs, spots, nets, flags and 7.32×2.44 goal opening reference. The field maps into the existing 100×64 display frame. Normalized event coordinates/distances are never renamed metres. This is reference scenery, not a certified surveyed playing field.
- **Materials:** original deterministic grass albedo; consistent world-relative UV density across mowing bands; sRGB color, rough PBR turf, filtered/mipmapped microdetail and restrained metal/paint materials. Marking outlines derive from the actual exported white geometry to stay legible at subpixel scales. No HDRI, downloaded material, branded model or geometry-based grass.
- **Stadium:** original bowl silhouette, terraces, 1,024 simple seats, canopies, supports, neutral perimeter boards, end stands and emissive floodlight banks. Seats are scenery, not observed spectators. Medium/High load the original stadium GLB; Low skips it. A procedural stadium remains available while assets load or fail.
- **Indicators:** original neutral humanoid with team-tinted materials, selection ring, directional pass arrow and panelled football. Ball source radius is 0.11 reference units, enlarged 2.7× for legibility; vertical placement is illustrative. Only recorded event X/Z origins/endpoints are used. No invented actor trajectories, speed, defenders or continuous tracking.
- **Lighting:** hemisphere/key illumination, explicit ACES/sRGB handling, restrained distance fog; High adds a bounded directional shadow map. Roofs do not receive self-shadows that obscured their surfaces. No bloom/postprocessing chain.
- **Cameras:** Broadcast, Tactical aerial, Isometric, Event focus and Free. Presets ease for 420ms and stop; reduced motion snaps. Free camera supports mouse/touch orbit, zoom and canvas-scoped arrow-key pan, bounded distance/polar angle/target. Reset is deterministic. Quality changes preserve one canvas and current camera state.
- **Evidence:** selected actor, outcome, clock and normalized coordinates are visible. Pass difficulty comes from the existing read-only backend scorer, with event/match/cutoff/bounds checks, request cancellation and an evidence link. The graphics layer does not invent a score or modify shared analytics.
- **Reliability:** lazy renderer, stable-parent context-loss capture, recoverable 2D fallback, procedural GLB fallback and explicit unsupported/loading states remain. Cloned materials retain single/array shape and are disposed independently; cached source geometry is not mutated.

## Quality profiles

| Profile | DPR | Stadium | Shadows | Intended use |
|---|---:|---|---|---|
| Low / Performance | 1 | Not requested on a cold Low start | Off | Mobile, reduced motion, limited hardware |
| Medium / Balanced (`standard` compatibility token) | 1.25 | Original bowl | Off | Default desktop analysis |
| High / Cinematic | 1.5 | Original bowl | 1024px directional map | Close inspection and presentation |

The GPU context's antialias allocation is chosen at creation; profile changes update DPR, scene content and shadows without replacing the canvas. Loaded geometry/shadow resources can remain cached until leaving 3D; Low is not a promise to purge every allocation from an earlier High session. The cache is bounded to this original kit, and renderer teardown remains owned by R3F.

## Asset pipeline and provenance

Editable sources: `assets/blender/v2/{field,stadium,ball,player-marker}.blend`. Original v1 sources and GLBs are unchanged. Runtime files are self-contained glTF 2.0 GLBs under `frontend/src/features/observer/assets/v2/`; Vite emits hashed URLs. No authoring executable is needed by a viewer or Azure deployment.

```powershell
python scripts/verify-blender.py
./scripts/blender.ps1 --background --factory-startup --python-exit-code 1 --python scripts/build-professional-assets.py
# Optional: append -- --pitch-length 105 --pitch-width 68 --only field
python scripts/asset_contract.py
cd frontend
npm run validate:assets
```

Sources retain editable quads/UVs; delivery copies remove unused channels and use fixed triangulation plus winding-preserving canonical ordering for opaque triangle indices. An actual repeat-export discrepancy was isolated to marker index order, not vertices/materials; the canonical-order regression proves reordered equivalent triangles produce identical bytes. Two full fresh-process rebuilds matched all seven GLB hashes. This is verified on Blender 5.2.2, not a promise of .blend byte identity or compatibility with every future Blender version.

The first operator-based stadium build was stopped after 160.9s. Direct mesh construction reduced a complete successful build to 22.67s; later repeat builds took 28.87/54.13s under varying concurrent load. These timings are not controlled speedup benchmarks. Unused export UV removal reduced the initial stadium export from 913,692 to 705,404 bytes before floodlight additions; the final stadium is 714,308 bytes. No compression decoder was added.

`assets/manifest.json` records all seven source/output hashes, source polygons/bytes, exported triangles/primitives/bytes, author/license and budgets. Original artwork is CC0; offline Blender scripts are GPL-3.0-or-later. Khronos Validator is an Apache-2.0 development tool. No third-party geometry, footage, logos or real-player likenesses. `release_approval` remains `pending-team-review` for Vishwam's #23 review.

## Performance evidence

Before values below are the unchanged original-kit measurements from the preceding verified audit. After values are actual local Chromium/SwiftShader measurements. All are event snapshot scenes; physical Iris Xe FPS/GPU memory bytes have not been measured.

| Item | Before | After |
|---|---:|---:|
| Default JS gzip | 86.39kB | approximately 87.13kB |
| Lazy renderer gzip | 258.94kB | approximately 265.7kB |
| Active original GLB kit | 96,116 bytes | 989,084 bytes including stadium |
| Cold Low GLB kit | N/A | 274,776 bytes, stadium omitted |
| Standard scene draw calls | 9 | Medium 21 |
| Standard scene triangles | 1,216 | Medium 18,820 |
| Low active calls / triangles | N/A | 13 / 5,324 |
| High calls / triangles, including shadows | N/A | 30 / 32,484 |

Final v2 exports: field 224,368 bytes / 3,772 triangles; stadium 714,308 / 13,168; ball 30,736 / 1,280; marker 19,672 / 496. The old kit remains in Git, but is not downloaded by the current observer. The optional chunk warning remains visible. Default 2D makes no renderer/GLB requests.

The repeatable `npm run measure:graphics` probe uses the running application (`PULSE_GRAPHICS_URL` optional), records actual GPU renderer identity, profiles, request counts and heap samples under root `test-results/graphics/`. In the recorded SwiftShader run: first-ready 637.3ms (a later remount reported 946.9ms); renderer and each GLB requested once; zero runtime errors; mature idle samples zero additional frames per 500ms. Twelve rapid camera/quality/replay changes and three 2D/3D cycles completed, followed by 30s idle. JS heap samples were 20,917,542 before interaction, 17,668,198 afterward and 15,222,745 after idle. No forced GC was used; this bounded observation does not prove absence of leaks. GPU texture counts were two in Medium and four with High shadow resources; these are counts, not VRAM byte measurements.

## Testing and visual evidence

- Renderer branch production build and 21 application/browser/transport cases pass without requiring child assets.
- Asset branch final full run: 28 cases pass. Coverage includes actual v2 GLB material visibility/source-color preservation, three profiles, five cameras/reset/free input, selected pass score identity, replay cutoffs, six viewport sizes, no default 3D download, cold Low stadium omission, missing/corrupt/slow GLB, no WebGL and context-loss recovery. Additional focused observer/graphics runs also passed.
- Backend: 34 tests pass, including eight asset/hash/budget/binary/canonical-order cases. No unrelated backend functionality changed.
- Khronos Validator: seven assets, zero errors and zero warnings; informational unused-UV notices remain for archived v1 assets and v2 terrain UVs used at runtime.
- CLI/bpy mesh/material/light/camera/export/import probe passes and cleans its temporary files. Every generated v2 GLB was reimported into a fresh scene.
- All six requested browser viewports were captured and visually inspected: 1920×1080, 1366×768, 1024×768, 768×1024, 390×844 and 360×800. Actual Low/Medium/High captures were also inspected. A CPU Cycles render of the editable sources was inspected; run `scripts/render-graphics-preview.py` through Blender to reproduce it without saving changes to sources.
- One recap assertion exceeded its 5s deadline while a CPU Cycles render ran concurrently with six browser workers. After that authoring render finished, full suites passed without weakened assertions/retries. Windows Proactor connection-reset callbacks still occur during deliberate request cancellation; they were not suppressed.

Local screenshots/measurements are ignored test artifacts, not fabricated or committed product assets. Headless software results do not certify a physical GPU frame rate, multi-hour soak, every browser engine or arbitrary third-party GLB.

## GitHub delivery and demo

Rendering changes belong to [PR #30](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/30), including commits `83e01aa`, `430662c` and `bade6a2`. Versioned assets/tooling belong to [PR #31](https://github.com/Microsoft-Game-Developer-Hackathon-2026/Pulse-Xi/pull/31), including `27d6314`. Common rendering changes are present in the parent; the child keeps its asset integration diff. Normal merges propagate the stack to #32/#33. No force push, main mutation, PR merge, issue closure, paid inference or deployment. Current-head CI outcomes are verified from GitHub at final handoff; PR check pages remain authoritative for later changes.

From the root, run `./scripts/start.ps1` and open `http://127.0.0.1:8000/#/sandbox`. Select a fictional fixture/seed, seek and select a pass, open 3D, inspect the score/evidence, choose cameras and profiles, then return to 2D. For reproducible graphics measurements, build/start first, then run `npm run measure:graphics` in frontend. No new credential is needed. `PULSE_BLENDER_PATH` and `PULSE_GRAPHICS_URL` are optional local tool paths/URLs, not secrets.

The result is an original stylized football arena for evidence-backed event visualization, not a football video game or photoreal tracking system. Unreal cinematics, real modeled observer frames, physical GPU benchmarking and teammate release approval remain optional or external gates. Existing checkpoint/ForkCast preparations remain unimplemented engine contracts; graphics do not fabricate those capabilities.
