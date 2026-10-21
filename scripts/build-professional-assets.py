# SPDX-License-Identifier: GPL-3.0-or-later
"""Original v2 scenery; Blender CLI only. Retains the complete original v1 kit.

blender --background --factory-startup --python-exit-code 1 --python scripts/build-professional-assets.py
Optional: -- --pitch-length 105 --pitch-width 68 (international reference range).
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from asset_contract import read_glb, sha256, validate_manifest
from glb_indices import canonicalize_indices

parser = argparse.ArgumentParser()
parser.add_argument('--pitch-length', type=float, default=105)
parser.add_argument('--pitch-width', type=float, default=68)
parser.add_argument('--only', nargs='+', choices=['field','stadium','ball','player-marker'])
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
if not 100 <= args.pitch_length <= 110 or not 64 <= args.pitch_width <= 75:
    parser.error('Reference dimensions must be 100..110 by 64..75.')
SX, SY = 100 / args.pitch_length, 64 / args.pitch_width
SOURCE = ROOT / 'assets/blender/v2'
OUTPUT = ROOT / 'frontend/src/features/observer/assets/v2'
SOURCE.mkdir(parents=True, exist_ok=True)
OUTPUT.mkdir(parents=True, exist_ok=True)


def material(name, color, roughness=.8, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Roughness'].default_value = roughness
    node.inputs['Metallic'].default_value = metallic
    return mat


def finish(obj, name, mat):
    obj.name = name
    obj.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return obj


def box(name, at, dimensions, mat):
    x,y,z=(value/2 for value in dimensions)
    mesh=bpy.data.meshes.new(name+'Geometry')
    offsets=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    vertices=[tuple(at[i]+point[i] for i in range(3)) for point in offsets]
    mesh.from_pydata(vertices,[],[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
    uv=mesh.uv_layers.new(name='UVMap')
    for polygon in mesh.polygons:
        for index,coordinate in zip(polygon.loop_indices,[(0,0),(1,0),(1,1),(0,1)]): uv.data[index].uv=coordinate
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def rod(name, start, end, radius, mat, sides=6):
    delta = Vector(end) - Vector(start)
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides, radius=radius, depth=delta.length,
                                      location=(Vector(start) + Vector(end)) / 2)
    obj = bpy.context.object
    obj.rotation_euler = delta.to_track_quat('Z', 'Y').to_euler()
    return finish(obj, name, mat)


def merge():
    groups = {}
    for obj in list(bpy.context.scene.objects):
        if obj.type == 'MESH' and len(obj.data.materials) == 1:
            # PlayingSurface identity is protected for runtime scale validation.
            key = ('surface' if obj.name == 'PlayingSurface' else obj.data.materials[0].name)
            groups.setdefault(key, []).append(obj)
    for objects in groups.values():
        if len(objects) < 2:
            continue
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()


def field():
    turf = material('Turf', (.045, .21, .075), .97)
    band = material('CuttingBands', (.05, .225, .08), .95)
    white = material('FieldWhite', (.85, .9, .78), .8)
    net = material('GoalNet', (.36, .43, .4), .9)
    base = material('Runoff', (.025, .065, .045), 1)
    flag = material('FlagTeal', (.08, .52, .43), .7)
    box('PlayingSurface', (0, 0, -.025), (100, 64, .03), turf)
    box('Runoff', (0, 0, -.17), (114, 78, .25), base)
    for i in range(10):
        box('CuttingStripe', (-45 + i * 10, 0, -.002), (5, 64, .006), band)

    def line(a, b, width=.105):
        # Flat paint ribbons preserve physical reference widths after mapping.
        x1, y1, x2, y2 = a[0] * SX, a[1] * SY, b[0] * SX, b[1] * SY
        dx, dy = x2 - x1, y2 - y1
        obj = box('Paint', ((x1+x2)/2, (y1+y2)/2, .012), (math.hypot(dx,dy), width, .012), white)
        # finish() applied transforms, so rotate the baked ribbon around its center.
        center = Vector(((x1+x2)/2, (y1+y2)/2, .012))
        angle = math.atan2(dy, dx)
        for vertex in obj.data.vertices:
            p = vertex.co - center
            vertex.co = center + Vector((p.x*math.cos(angle)-p.y*math.sin(angle), p.x*math.sin(angle)+p.y*math.cos(angle), p.z))

    def arc(cx, cy, radius, start, end, segments=48):
        for i in range(segments):
            a, b = start+(end-start)*i/segments, start+(end-start)*(i+1)/segments
            line((cx+radius*math.cos(a),cy+radius*math.sin(a)), (cx+radius*math.cos(b),cy+radius*math.sin(b)))

    L, W = args.pitch_length/2, args.pitch_width/2
    for a,b in [((-L,-W),(L,-W)),((-L,W),(L,W)),((-L,-W),(-L,W)),((L,-W),(L,W)),((0,-W),(0,W))]:
        line(a,b)
    arc(0,0,9.15,0,math.tau,64)
    for side in [-1,1]:
        for depth, halfwidth in [(16.5,20.16),(5.5,9.16)]:
            line((side*L,-halfwidth),(side*(L-depth),-halfwidth))
            line((side*(L-depth),-halfwidth),(side*(L-depth),halfwidth))
            line((side*(L-depth),halfwidth),(side*L,halfwidth))
        cx=side*(L-11)
        angle=math.acos(5.5/9.15)
        arc(cx,0,9.15,math.pi-angle if side==1 else -angle,math.pi+angle if side==1 else angle,32)
        for px,py in [(cx,0),(0,0)]:
            bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.12,depth=.014,location=(px*SX,py*SY,.018))
            finish(bpy.context.object,'Spot',white)
        for end in [-1,1]:
            start={(1,1):math.pi, (1,-1):math.pi/2,(-1,1):-math.pi/2,(-1,-1):0}[(side,end)]
            arc(side*L,end*W,1,start,start+math.pi/2,12)
            x,y=side*50,end*32
            rod('FlagPole',(x,y,.03),(x,y,1.6),.035,white)
            box('CornerFlag',(x+.22,y,1.38),(.44,.025,.35),flag)
        x=side*50; back=x+side*2.2
        post_halfwidth=3.66*SY+.055
        for y in [-post_halfwidth,post_halfwidth]:
            rod('GoalPost',(x,y,.03),(x,y,2.495),.055,white,10)
            rod('GoalSupport',(x,y,2.495),(back,y,.1),.035,net)
        rod('Crossbar',(x,-post_halfwidth,2.495),(x,post_halfwidth,2.495),.055,white,10)
        for i in range(19):
            y=(-3.66+i*7.32/18)*SY
            rod('NetMesh',(x,y,2.43),(back,y,.1),.012,net,4)
        for i in range(1,9):
            t=i/9
            rod('NetMesh',(x+side*2.2*t,-3.66*SY,2.43*(1-t)),(x+side*2.2*t,3.66*SY,2.43*(1-t)),.012,net,4)
    merge()


def stadium():
    concrete=material('StadiumConcrete',(.025,.05,.065),.95)
    roof=material('RoofMetal',(.09,.15,.18),.55,.45)
    seat=material('SeatingTeal',(.04,.20,.22),.75)
    pale=material('SeatingSilver',(.30,.42,.43),.8)
    board=material('OriginalNeutralBoards',(.015,.06,.075),.6)
    lamps=material('LampPanels',(.6,.75,.8),.5)
    lamp_node=lamps.node_tree.nodes.get('Principled BSDF')
    lamp_node.inputs['Emission Color'].default_value=(.6,.75,.8,1)
    lamp_node.inputs['Emission Strength'].default_value=2.3
    for side in [-1,1]:
        for row in range(8):
            y=side*(41+row*1.1);height=.7+row*.8
            box('Terrace',(0,y,height/2),(114,1.35,height),concrete)
            for column in range(64):
                mat=pale if (column//5+row)%7==0 else seat
                box('Seat',((column-31.5)*1.7,y,height+.35),(.92,.72,.65),mat)
        box('Canopy',(0,side*47,10.7),(120,13,.38),roof)
        box('PerimeterBoard',(0,side*37,.7),(110,.35,1.4),board)
        # End stands create a bowl silhouette without detailed crowds.
        for row in range(5):
            box('EndTerrace',(side*(60+row*1.2),0,1+row*.7),(1.3,78,2+row*1.4),concrete)
        for column in range(9):
            rod('RoofSupport',((column-4)*13,side*50,0),((column-4)*13,side*50,10.7),.10,roof)
        for end in [-1,1]:
            x,y=end*63,side*44
            rod('FloodlightMast',(x,y,0),(x,y,24),.20,roof,8)
            box('FloodlightBank',(x,y,24),(6,.45,2.2),lamps)
    merge()


def ball():
    ivory=material('BallIvory',(.88,.91,.85),.48)
    dark=material('BallPanels',(.012,.022,.03),.6)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4,radius=.11)
    obj=finish(bpy.context.object,'Football',ivory);obj.data.materials.append(dark)
    phi=(1+math.sqrt(5))/2
    axes=[Vector(v).normalized() for a in [-1,1] for b in [-phi,phi] for v in [(0,a,b),(a,b,0),(b,0,a)]]
    for face in obj.data.polygons:
        # Original geometric panel motif, not a commercial ball design.
        center=sum((obj.data.vertices[i].co for i in face.vertices),Vector()).normalized()
        face.material_index=1 if max(center.dot(axis) for axis in axes)>.94 else 0
        face.use_smooth=True


def marker():
    accent=material('TeamAccent',(.12,.5,.43),.6)
    neutral=material('MarkerNeutral',(.67,.75,.72),.75)
    dark=material('Boots',(.012,.025,.03),.7)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.8,depth=.12,location=(0,0,.06))
    finish(bpy.context.object,'SelectionPlinth',accent)
    box('Torso',(0,0,1.15),(.58,.34,.66),accent)
    for side in [-1,1]:
        rod('Leg',(side*.16,0,.75),(side*.18,0,.18),.11,neutral,8)
        rod('Arm',(side*.37,0,1.42),(side*.48,0,.92),.09,accent,8)
        box('Boot',(side*.18,-.08,.14),(.23,.42,.20),dark)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.22,location=(0,0,1.76))
    obj=finish(bpy.context.object,'NeutralHead',neutral)
    for face in obj.data.polygons: face.use_smooth=True
    merge()


manifest=json.loads((ROOT/'assets/manifest.json').read_text(encoding='utf-8'))
manifest['assets']=[asset for asset in manifest['assets'] if asset['version']=='1.0' or args.only and asset['name'].removesuffix('-v2') not in args.only]
for name,build,byte_budget,triangle_budget in [('field',field,450000,14000),('stadium',stadium,850000,24000),('ball',ball,80000,2000),('player-marker',marker,80000,2000)]:
    if args.only and name not in args.only:
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    build()
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and any(mat.name in ('Turf','CuttingBands') for mat in obj.data.materials):
            # One shared world-space texel scale across ground and mowing bands.
            uv=obj.data.uv_layers.active
            for loop in obj.data.loops:
                point=obj.data.vertices[loop.vertex_index].co
                uv.data[loop.index].uv=(point.x/100+.5,point.y/64+.5)
    bpy.context.scene['pulse_provenance']='Original PULSE XI v2 procedural scenery; no third-party assets'
    bpy.context.scene['reference_pitch_metres']=[args.pitch_length,args.pitch_width]
    bpy.context.scene['event_coordinates']='Normalized display frame; no measured event distances'
    source=SOURCE/f'{name}.blend';output=OUTPUT/f'{name}.glb'
    polygons=sum(len(o.data.polygons) for o in bpy.context.scene.objects if o.type=='MESH')
    materials=sorted(m.name for m in bpy.data.materials if m.users)
    bpy.ops.wm.save_as_mainfile(filepath=str(source),compress=True)
    # Keep editable UVs in .blend; strip unused export channels. Only Turf
    # receives a runtime-generated albedo map, so it retains its UV contract.
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and not any(mat.name in ('Turf', 'CuttingBands') for mat in obj.data.materials):
            for layer in list(obj.data.uv_layers):
                obj.data.uv_layers.remove(layer)
        if obj.type == 'MESH':
            # Preserve editable source quads; use fixed export diagonals instead
            # of session-dependent quad tessellation in the glTF exporter.
            mesh=bmesh.new();mesh.from_mesh(obj.data)
            bmesh.ops.triangulate(mesh,faces=list(mesh.faces),quad_method='FIXED',ngon_method='EAR_CLIP')
            mesh.to_mesh(obj.data);mesh.free()
    bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',export_yup=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True,export_copyright='PULSE XI original procedural artwork - CC0-1.0')
    canonicalize_indices(output)
    info=read_glb(output)
    # Verify a clean import, not only container metadata.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(output))
    assert any(o.type=='MESH' for o in bpy.context.scene.objects)
    manifest['assets'].append({'name':f'{name}-v2','version':'2.0','author':'Satvik Patel / PULSE XI procedural source','license':'CC0-1.0','source':source.relative_to(ROOT).as_posix(),'output':output.relative_to(ROOT).as_posix(),'source_sha256':sha256(source),'output_sha256':sha256(output),'source_bytes':source.stat().st_size,'source_polygons':polygons,'materials':materials,'bytes':info['bytes'],'triangles':info['triangles'],'draw_primitives':info['primitives'],'textures':info['textures'],'texture_resolution':None,'budget_bytes':byte_budget,'budget_triangles':triangle_budget,'target':'Optional event snapshot scenery; positions remain event-derived'})
manifest['professional_generator']='scripts/build-professional-assets.py'
manifest['reference_pitch_metres']=[args.pitch_length,args.pitch_width]
(ROOT/'assets/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(validate_manifest(ROOT),indent=2))
