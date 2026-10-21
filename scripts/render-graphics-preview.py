# SPDX-License-Identifier: GPL-3.0-or-later
"""Render actual editable v2 Blender sources for visual inspection, without saving them."""
from pathlib import Path
import bpy
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
for name in ['field', 'stadium']:
    with bpy.data.libraries.load(str(root / f'assets/blender/v2/{name}.blend'), link=False) as (source, target):
        target.objects = source.objects
    for obj in target.objects:
        if obj:
            bpy.context.collection.objects.link(obj)
bpy.ops.object.light_add(type='SUN', location=(10,-20,60))
bpy.context.object.data.energy=2.5
bpy.context.object.rotation_euler=(.35,-.3,-.4)
bpy.ops.object.camera_add(location=(75,-100,90))
camera=bpy.context.object
camera.rotation_euler=(Vector((0,0,0))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=165
scene=bpy.context.scene;scene.camera=camera
scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.device='CPU'
scene.world=bpy.data.worlds.new('PreviewWorld');scene.world.color=(.18,.18,.18)
scene.render.resolution_x=960;scene.render.resolution_y=640;scene.render.resolution_percentage=100
output=root/'frontend/test-results/graphics-native.png';output.parent.mkdir(parents=True,exist_ok=True)
scene.render.filepath=str(output)
bpy.ops.render.render(write_still=True)
print('NATIVE_SOURCE_PREVIEW',output)
