# Original asset pipeline (#12)

The committed generator builds a stylized field with markings/goalposts, schematic football and neutral generic player marker from Blender primitives. No external geometry, textures, fonts, add-ons, logos or real-player likenesses are used. Blender 5.2.2 LTS was actually executed and all three editable `.blend` files and GLB exports were produced.

## Rebuild and validate

From repository root on this machine:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python scripts/build-blender-assets.py
python scripts/asset_contract.py
```

On another machine use its Blender executable with the same flags. Blender is an offline authoring tool; the website needs only the exported GLBs. The script writes only its named outputs and manifest; it does not download assets or install add-ons. Blender 5.2 emits a `Material.use_nodes` deprecation notice for its future 6.0 removal; exports succeed on the verified version.

`assets/manifest.json` records versions, author, source/output paths and SHA-256 hashes, source polygon count, exported triangles/size, materials, texture absence, budgets and pending release review. Builds reproduce the procedural geometry and are validated against the semantic contract; byte-identical `.blend` output across Blender versions or sessions is not promised.

## Coordinates and materials

Blender source uses Z up; glTF export uses Y up (`export_yup=True`). Blender `(x,y,z)` maps to glTF `(x,z,-y)`. Transforms are baked before export, with pitch center at the origin. The named PlayingSurface spans 100×64 display units, not measured metres. The decorative plinth spans 108×72. Runtime Box3 checks verify the exported surface's X/Z size and thin Y extent; a mismatch triggers procedural fallback.

The field uses four untextured rough PBR materials: turf, alternating bands, plinth and field white. Objects sharing a material are joined to reduce draw calls. The player uses neutral details and TeamAccent; the runtime clones only its materials before changing team color, preserving cached source assets and geometry groups. Standard mode shows the generic actor marker at a recorded origin and the stylized ball at a recorded endpoint. Low power uses a sphere at the recorded origin. These remain event symbols, not continuous actor or ball tracking.

## Budgets and measured output

| Asset | GLB bytes | Exported triangles | Draw primitives | Budget |
|---|---:|---:|---:|---|
| field | 68,452 | 920 | 4 | <=102,400 bytes / 5,000 triangles |
| ball | 10,556 | 80 | 2 | <=30,720 bytes / 1,500 triangles |
| player-marker | 17,108 | 216 | 2 | <=30,720 bytes / 1,500 triangles |

The entire kit is 96,116 bytes without textures. The standard browser event scene measured 9 draw calls and 1,216 triangles; low power replaces the figure with a simpler marker. The test renderer reports one internal texture even though GLB files contain none. A concurrent-suite headless Chromium/SwiftShader run measured first ready at 1,074 ms with one additional frame during its first 500 ms sample. This is software-renderer timing, not physical GPU FPS. GLB activation timing is also shown directly in the observer.

Final asset integration build: default JS 274.62 kB / 85.35 kB gzip; optional renderer + GLTFLoader 956.18 kB / 259.02 kB gzip; CSS 30.16 kB / 7.79 kB gzip. GLBs are hashed Vite assets, loaded only in the optional 3D view. No default page asset download is required. The >500 kB optional-chunk warning remains visible.

## Failure handling and tests

While GLBs load, a procedural pitch is rendered. Missing/invalid GLBs use the procedural field and recorded markers, and 2D remains available. A style selector can explicitly choose primitives. Context loss still falls back to 2D. The small three-asset loader cache is bounded for the app session; pending resource loads may finish into that cache after the observer closes, while no stale scene is displayed. Cloned marker materials are disposed on replacement and the renderer is disposed on unmount.

`asset_contract.py` and pytest check hashes, container metadata, self-contained resources, triangle/file budgets, provenance, corruption and path confinement. Chromium tests load the actual GLBs, check transformed scale, verify material cloning, exercise missing/slow asset recovery, and test mobile reduced-motion defaults. Actual exported scenes and browser screenshots were inspected. Full local validation: **27 backend tests, production TypeScript build and 19 browser tests passed**.

## Review handoff

Audit on 2026-10-16: Blender 5.2.2 reopened all three editable sources without missing external images. Source polygon counts were field 460, ball 80 and marker 102, matching the manifest. No assets were regenerated or changed. The standard-library validator now also checks BIN chunk bounds/type, embedded buffer size, buffer-view ranges, source file bytes and measured draw primitive counts. Corrupt BIN lengths and changed metadata reproduced failures in the prior validator; seven asset tests now pass. This is a kit-specific structural check, not a complete Khronos glTF conformance certification.

Artwork is declared CC0-1.0 in `assets/LICENSE.md`. The offline bpy generator is GPL-3.0-or-later and is not imported into the website. Blender's [official license/output guidance](https://www.blender.org/about/license/) distinguishes generated artwork from the authoring software. The export uses the [documented glTF operator](https://docs.blender.org/api/main/bpy.ops.export_scene.html).

Vishwam should review the source/provenance/license manifest under #23 before release approval; it currently says `pending-team-review`. No teammate issue was changed or approval assumed. Deployment continues to serve generated `/assets/` through Vite/FastAPI, without Blender, a rendering service or a GPU server.
