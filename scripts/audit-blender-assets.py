# SPDX-License-Identifier: GPL-3.0-or-later
"""Inspect trusted project sources without executing embedded scripts; no saves.

Run with Blender --background --factory-startup --disable-autoexec
--python-exit-code 1 --python scripts/audit-blender-assets.py.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from asset_contract import validate_manifest


def geometry():
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    assert objects, 'no meshes'
    points = [o.matrix_world @ Vector(corner) for o in objects for corner in o.bound_box]
    assert all(math.isfinite(v) for o in objects for vertex in o.data.vertices for v in vertex.co)
    return {'polygons': sum(len(o.data.polygons) for o in objects),
            'bounds': [[min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)],
            'materials': sorted({m.name for o in objects for m in o.data.materials if m})}


validate_manifest(ROOT)
records = []
for asset in json.loads((ROOT / 'assets/manifest.json').read_text())['assets']:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / asset['source']), load_ui=False, use_scripts=False)
    assert not bpy.data.libraries, 'linked library'
    assert not bpy.data.images, 'unexpected image dependency'
    assert not bpy.data.sounds and not bpy.data.movieclips, 'unexpected media dependency'
    assert not bpy.data.texts, 'embedded script/text requires manual review'
    assert not any(block.animation_data and block.animation_data.drivers
                   for group in (bpy.data.objects, bpy.data.materials, bpy.data.scenes)
                   for block in group), 'driver requires review'
    source = geometry()
    assert source['polygons'] == asset['source_polygons'], asset['name']
    assert source['materials'] == sorted(asset['materials']), asset['name']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / asset['output']))
    imported = geometry()
    for before, after in zip(source['bounds'], imported['bounds']):
        assert all(abs(a - b) < .001 for a, b in zip(before, after)), asset['name']
    records.append({'name': asset['name'], 'source': source, 'reimport': imported,
                    'external_resources': [], 'embedded_texts': 0, 'linked_libraries': 0})
report = {'blender': bpy.app.version_string, 'assets': records}
output = ROOT / 'test-results/asset-review/native-audit.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
