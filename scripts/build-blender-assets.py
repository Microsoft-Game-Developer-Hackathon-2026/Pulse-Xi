# SPDX-License-Identifier: GPL-3.0-or-later
"""Original PULSE XI geometry. Run in Blender background mode, not system Python.

blender --background --factory-startup --python scripts/build-blender-assets.py
"""
import json
import sys
from math import pi
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from asset_contract import read_glb, sha256, validate_manifest

SOURCE = ROOT / "assets/blender"
OUTPUT = ROOT / "frontend/src/features/observer/assets"
SOURCE.mkdir(parents=True, exist_ok=True)
OUTPUT.mkdir(parents=True, exist_ok=True)


def material(name, color):
    value = bpy.data.materials.new(name)
    value.diffuse_color = (*color, 1)
    value.use_nodes = True
    bsdf = value.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = .85
    return value


def finish(obj, name, mat):
    obj.name = name
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return obj


def box(name, location, dimensions, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.dimensions = dimensions
    return finish(obj, name, mat)


def merge_material_objects():
    groups = {}
    for obj in list(bpy.context.scene.objects):
        if obj.type == "MESH" and len(obj.data.materials) == 1:
            groups.setdefault(obj.data.materials[0].name, []).append(obj)
    for objects in groups.values():
        if len(objects) < 2:
            continue
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()


def field():
    green = material("Turf", (.025, .15, .105))
    band = material("TurfBands", (.035, .20, .14))
    base = material("Plinth", (.018, .05, .06))
    white = material("FieldWhite", (.65, .78, .68))
    box("PlayingSurface", (0, 0, -.02), (100, 64, .03), green)
    box("Plinth", (0, 0, -.65), (108, 72, 1.2), base)
    for x in (-45, -25, -5, 15, 35):
        box("TurfBand", (x, 0, 0), (10, 64, .012), band)

    def line(x, y, width, height):
        box("Markings", (x, y, .025), (width, height, .02), white)

    def rectangle(x, y, width, height):
        line(x + width / 2, y, width, .24)
        line(x + width / 2, y + height, width, .24)
        line(x, y + height / 2, .24, height)
        line(x + width, y + height / 2, .24, height)

    rectangle(-50, -32, 100, 64)
    line(0, 0, .24, 64)
    rectangle(-50, -20, 16, 40); rectangle(34, -20, 16, 40)
    rectangle(-50, -9, 5.5, 18); rectangle(44.5, -9, 5.5, 18)
    bpy.ops.mesh.primitive_torus_add(major_segments=64, minor_segments=4,
        major_radius=9.15, minor_radius=.12, location=(0, 0, .14))
    finish(bpy.context.object, "CenterCircle", white)
    for x in (-50, 50):
        for y in (-3.66, 3.66):
            box("Goalpost", (x, y, 1.25), (.3, .3, 2.5), white)
        box("Crossbar", (x, 0, 2.5), (.3, 7.62, .3), white)
    merge_material_objects()


def ball():
    white = material("BallIvory", (.82, .86, .78))
    dark = material("BallPanels", (.025, .045, .05))
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=.65)
    obj = finish(bpy.context.object, "SchematicBall", white)
    obj.data.materials.append(dark)
    for face in obj.data.polygons:
        face.material_index = 1 if face.index % 5 == 0 else 0


def marker():
    accent = material("TeamAccent", (.25, .45, .42))
    neutral = material("MarkerNeutral", (.65, .74, .67))
    bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=.65, radius2=.45, depth=1.9, location=(0, 0, 1.35))
    finish(bpy.context.object, "GenericBody", accent)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=.5, location=(0, 0, 2.8))
    finish(bpy.context.object, "GenericHead", neutral)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=1.1, depth=.18, location=(0, 0, .09))
    finish(bpy.context.object, "MarkerBase", accent)
    merge_material_objects()


assets = []
for name, build, budget_bytes, budget_triangles in (
        ("field", field, 102400, 5000), ("ball", ball, 30720, 1500), ("player-marker", marker, 30720, 1500)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    build()
    bpy.context.scene["pulse_provenance"] = "Original procedural fictional football artwork; no external assets"
    bpy.context.scene["pulse_units"] = "Display units, not measured metres; export Y up"
    source = SOURCE / f"{name}.blend"
    output = OUTPUT / f"{name}.glb"
    polygons = sum(len(obj.data.polygons) for obj in bpy.context.scene.objects if obj.type == "MESH")
    materials = sorted(mat.name for mat in bpy.data.materials if mat.users)
    bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
    bpy.ops.export_scene.gltf(filepath=str(output), export_format="GLB", export_yup=True,
        export_animations=False, export_cameras=False, export_lights=False, export_extras=True,
        export_copyright="PULSE XI original procedural artwork — CC0-1.0")
    info = read_glb(output)
    assets.append({"name": name, "version": "1.0", "author": "Satvik Patel / PULSE XI procedural source",
        "license": "CC0-1.0", "source": source.relative_to(ROOT).as_posix(),
        "output": output.relative_to(ROOT).as_posix(), "source_sha256": sha256(source),
        "output_sha256": sha256(output), "bytes": info["bytes"], "triangles": info["triangles"],
        "source_polygons": polygons, "source_bytes": source.stat().st_size, "materials": materials,
        "draw_primitives": info["primitives"], "textures": 0, "texture_resolution": None,
        "budget_bytes": budget_bytes, "budget_triangles": budget_triangles,
        "target": "Optional static event observer; procedural fallback and low-detail markers available"})

manifest = {"schema_version": "1.0", "generator": "scripts/build-blender-assets.py",
    "blender_version": bpy.app.version_string, "release_approval": "pending-team-review",
    "coordinate_system": "glTF Y-up; X length; Z width; origin pitch center; display units, not metres",
    "external_assets": [], "assets": assets}
(ROOT / "assets/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps(validate_manifest(ROOT), indent=2))
