"""Inspect authored pit door clearance, UVs and moving hoist geometry."""
import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from native_uv_contract import valid_native_uv

parser=argparse.ArgumentParser()
parser.add_argument('--source-dir',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
cli=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if not cli.source_dir.is_absolute() or not cli.report.is_absolute():
    raise ValueError('Source and report paths must be absolute')


def tree_for(objects):
    vertices=[];faces=[]
    for obj in objects:
        start=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(start+i for i in p.vertices) for p in obj.data.polygons)
    return BVHTree.FromPolygons(vertices,faces)


results=[]
for ident in ('SandstonePit','LimestonePit'):
    bpy.ops.wm.open_mainfile(filepath=str(cli.source_dir/(ident+'-ReferenceStudy.blend')))
    scene=bpy.context.scene
    model=bpy.data.collections[ident+'.ReferenceStudy']
    meshes=[o for o in model.objects if o.type=='MESH']
    scene.frame_set(1);bpy.context.view_layer.update()
    static=[o for o in meshes if o.animation_data is None]
    tree=tree_for(static)
    failures=[];uv_count=0;door_samples=0
    # The ground approach ends at the authored arch, not inside its closed room.
    # A set-back door's approach runs over the yard floor (sandstone); a door
    # on the footprint edge opens onto native ground outside the building
    # (limestone, 2026-10-22): no authored floor there, only clear headroom.
    from pit_layouts import LAYOUTS as PIT_LAYOUTS
    yard_approach=PIT_LAYOUTS[ident]['approachFloor'] is not None
    for i in range(10):
        y=.30+i*.68/9
        for dx,dy in ((0,0),(-.20,0),(.20,0),(0,.15),(0,-.15)):
            p=Vector((-(.93+dx),-(y+dy),.10))
            floor=tree.ray_cast(p,Vector((0,0,-1)),.12)
            # Inside the footprint (artwork y > -origin y) the doorstep has
            # the yard floor either way.
            on_floor=yard_approach or y+dy>-PIT_LAYOUTS[ident]['origin'][1]
            if on_floor and (floor[0] is None or not -.005<=floor[0].z<=.035):
                failures.append(f'Unsupported door approach: {list(p)}')
                continue
            if not on_floor and floor[0] is not None:
                failures.append(f'Authored floor in front of an edge door: {list(floor[0])}')
                continue
            base=floor[0].z if on_floor else 0.0
            head=tree.ray_cast(Vector((p.x,p.y,base+.015)),Vector((0,0,1)),1.10)
            if head[0] is not None:
                failures.append(f'Door approach obstruction: {list(head[0])}')
            door_samples+=1
    for obj in meshes:
        if not obj.data.uv_layers:
            raise ValueError('Missing UVs: '+obj.name)
        if 'native_resource' in obj:
            continue
        if len(obj.material_slots)!=32:
            raise ValueError('Unexpected source material contract: '+obj.name)
        for polygon in obj.data.polygons:
            if polygon.material_index not in (0,1,2,3,7,27,28,29,30):
                continue
            for index in polygon.loop_indices:
                uv=obj.data.uv_layers.active.data[index].uv
                if not valid_native_uv(obj.material_slots[polygon.material_index].material.name,uv):
                    failures.append('Native atlas UV outside its sheet: '+obj.name)
                uv_count+=1
    moving={name:bpy.data.objects[name] for name in (
        'Pit.Winch','Pit.HoistedBasket','Pit.HoistCable')}
    first={name:o.matrix_world.copy() for name,o in moving.items()}
    if scene.frame_end!=121 or scene.render.fps!=30:
        raise ValueError('Unexpected pit animation timing')
    cable_tops=[];cable_bottoms=[];basket_tops=[];collisions=0
    for frame in range(1,122):
        scene.frame_set(frame);bpy.context.view_layer.update()
        rope=[moving['Pit.HoistCable'].matrix_world@v.co for v in moving['Pit.HoistCable'].data.vertices]
        basket=[moving['Pit.HoistedBasket'].matrix_world@v.co for v in moving['Pit.HoistedBasket'].data.vertices]
        cable_tops.append(max(v.z for v in rope))
        cable_bottoms.append(min(v.z for v in rope))
        basket_tops.append(max(v.z for v in basket))
        collisions+=len(tree.overlap(tree_for([moving['Pit.HoistedBasket']])))
    if collisions:
        failures.append(f'Basket/static triangle intersections across loop: {collisions}')
    if max(cable_tops)-min(cable_tops)>1e-5:
        failures.append('Cable upper attachment moves')
    if max(basket_tops)-min(basket_tops)<.30:
        failures.append('Basket does not lift')
    for bottom,top in zip(cable_bottoms,basket_tops):
        if abs(top-bottom-.04)>1e-5:
            failures.append('Cable and basket eye separate during animation')
            break
    for name,obj in moving.items():
        if obj.animation_data is None:
            failures.append('Missing animation: '+name)
        error=max(abs(first[name][i][j]-obj.matrix_world[i][j]) for i in range(4) for j in range(4))
        if error>1e-5:
            failures.append('Loop seam: '+name)
    results.append({'model':ident,'doorClearanceSamples':door_samples,
        'headroom':1.10,'bodyRadius':.20,'nativeAtlasUvCornersChecked':uv_count,
        'animationFramesInspected':121,'basketLift':max(basket_tops)-min(basket_tops),
        'basketStaticIntersections':collisions,'failures':failures})

report={'scope':'Blender source checks; native placement, gathering and animation remain to test',
        'models':results}
cli.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
if any(r['failures'] for r in results):
    raise ValueError('Pit source validation failed; inspect the report')
