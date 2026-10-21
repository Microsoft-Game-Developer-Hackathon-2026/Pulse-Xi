"""Verify official Blender CLI/bpy/glTF round trip in an isolated temporary folder."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--blender', default=os.getenv('PULSE_BLENDER_PATH') or shutil.which('blender'))
args = parser.parse_args()
if not args.blender:
    candidates = sorted((Path(os.getenv('ProgramFiles', 'C:/Program Files')) / 'Blender Foundation').glob('Blender */blender.exe'), reverse=True)
    args.blender = str(candidates[0]) if candidates else None
if not args.blender or not Path(args.blender).is_file():
    parser.error('Install official Blender or provide --blender / PULSE_BLENDER_PATH.')

probe = '''import bpy
from pathlib import Path
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
obj=bpy.context.object
material=bpy.data.materials.new('ProbePBR'); material.use_nodes=True
obj.data.materials.append(material)
bpy.ops.object.light_add(type='POINT', location=(0,0,5))
bpy.context.object.data.energy=100
bpy.ops.object.camera_add(location=(4,-4,4)); bpy.context.scene.camera=bpy.context.object
output=Path(__file__).with_name('probe.glb')
bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',export_cameras=True,export_lights=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(output))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
assert len(meshes)==1 and len(meshes[0].data.polygons)>0 and len(meshes[0].data.materials)==1
assert any(o.type=='CAMERA' for o in bpy.context.scene.objects)
assert any(o.type=='LIGHT' for o in bpy.context.scene.objects)
print('BLENDER_PROBE_PASS',bpy.app.version_string,output.stat().st_size)
'''
with tempfile.TemporaryDirectory(prefix='pulse-blender-probe-') as folder:
    script = Path(folder) / 'probe.py'
    script.write_text(probe, encoding='utf-8')
    subprocess.run([args.blender, '--background', '--factory-startup', '--python-exit-code', '1', '--python', str(script)], check=True, timeout=120)
print('PASS: temporary mesh/material/light/camera/export/import probe; temporary files cleaned.')
