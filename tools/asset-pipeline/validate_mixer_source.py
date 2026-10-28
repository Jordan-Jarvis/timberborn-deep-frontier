"""Check source-art walks, UVs, native tank identity and the full drum loop."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0,str(Path(__file__).parent))
from industrial_layouts import M
from native_building_assets import RESOURCES
from native_uv_contract import valid_native_uv

parser=argparse.ArgumentParser()
parser.add_argument('--scene',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
cli=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if not cli.scene.is_absolute() or not cli.report.is_absolute():
    raise ValueError('Source and report paths must be absolute')
bpy.ops.wm.open_mainfile(filepath=str(cli.scene))
scene=bpy.context.scene
model=bpy.data.collections['ConcreteMixer.ReferenceStudy']
scene.frame_set(1);scene.view_layers[0].update()
vertices=[];faces=[];owners=[]
for obj in model.objects:
    if obj.type!='MESH':continue
    start=len(vertices)
    vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
    faces.extend(tuple(start+i for i in p.vertices) for p in obj.data.polygons)
    owners.extend([obj.name]*len(obj.data.polygons))
tree=BVHTree.FromPolygons(vertices,faces)
points={tuple(n['cell']):n['point'] for n in M['nodes']}
failures=[];samples=0
for a,b in M['edges']:
    p,q=Vector(points[tuple(a)]),Vector(points[tuple(b)])
    count=math.ceil((q-p).length/.10)
    for i in range(count+1):
        x,y,z=p+(q-p)*i/count
        floor=0
        for dx in (-.035,0,.035):
            hit=tree.ray_cast(Vector((-x-dx,-y,z+.08)),Vector((0,0,-1)),.12)
            if hit[0] is not None and abs(hit[0].z-z)<.005:floor+=1
        if floor<2:failures.append(f'Floor: {x:.2f},{y:.2f},{z}')
        for dx,dy in ((0,0),(.2,0),(-.2,0),(0,.2),(0,-.2)):
            hit=tree.ray_cast(Vector((-x-dx,-y-dy,z+.01)),Vector((0,0,1)),1.09)
            if hit[0] is not None:
                failures.append(f'Clearance: {x:.2f},{y:.2f},{z} in {owners[hit[2]]} at {list(hit[0])}')
        samples+=1
uv_count=0
for obj in model.objects:
    if obj.type!='MESH':continue
    if 'native_resource' in obj or 'liquid_surface' in obj:
        if not obj.data.uv_layers:raise ValueError('Native prop UVs absent: '+obj.name)
        continue
    if len(obj.material_slots)!=32:raise ValueError('Expected explicit 32-slot material contract')
    uv=obj.data.uv_layers.active.data
    for p in obj.data.polygons:
        if p.material_index in (0,1,2,3,7,27,28,29,30):
            for loop in p.loop_indices:
                if not valid_native_uv(obj.material_slots[p.material_index].material.name,uv[loop].uv):
                    raise ValueError('Unbounded native atlas UV: '+obj.name)
                uv_count+=1
animated=[]
for name in ('Mixer.Drum','Mixer.Drive'):
    obj=bpy.data.objects[name]
    if obj.animation_data is None:raise ValueError('Animation absent: '+name)
    matrices=[]
    for frame in (1,16,31,61,121):
        scene.frame_set(frame);scene.view_layers[0].update()
        matrices.append(obj.matrix_world.copy())
    if max(abs(matrices[0][i][j]-matrices[-1][i][j]) for i in range(4) for j in range(4))>1e-5:
        raise ValueError('Animation does not loop: '+name)
    if max(abs(matrices[0][i][j]-matrices[1][i][j]) for i in range(3) for j in range(3))<.1:
        raise ValueError('Animated part does not move: '+name)
    animated.append(name)
scene.frame_set(1);scene.view_layers[0].update()
tanks=[o for o in model.objects if o.get('native_resource')==RESOURCES['SmallTank.IronTeeth']]
if not tanks:raise ValueError('Native tank preview absent')
result={'scope':'Source geometry only; native placement and walking remain to test',
        'routeCells':len(M['nodes']),'railPorts':len(M['ports']),
        'floorAndHeadroomSamples':samples,'bodyRadius':.2,'headroom':1.10,
        'nativeAtlasUvCornersChecked':uv_count,'loopingAnimatedParts':animated,
        'animationFrames':scene.frame_end,'failures':failures}
cli.report.write_text(json.dumps(result,indent=2)+'\n')
if failures:raise ValueError(f'{len(failures)} route failures: '+str(failures[:12]))
print(json.dumps(result))
