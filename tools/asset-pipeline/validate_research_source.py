"""Validate authored terrace clearance, native atlas islands and all three loops."""
import json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from research_layouts import LAB
from native_uv_contract import valid_native_uv
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'src/DeepFrontier/Art/Source/MaterialsLaboratory-ReferenceStudy.blend'))
scene=bpy.context.scene;scene.frame_set(1);scene.view_layers[0].update()
model=bpy.data.collections['MaterialsLaboratory.ReferenceStudy']
vertices=[];faces=[];owners=[]
for obj in model.objects:
    if obj.type!='MESH':continue
    start=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
    faces.extend(tuple(start+i for i in p.vertices) for p in obj.data.polygons)
    owners.extend([obj.name]*len(obj.data.polygons))
tree=BVHTree.FromPolygons(vertices,faces)
points={tuple(n['cell']):n['point'] for n in LAB['nodes']}
interior={tuple(c) for c in LAB['interiorCells']}
failures=[];samples=0
for a,b in LAB['edges']:
    # The terrace is layer 1 since the one-layer storeys (2026-10-30; was 2).
    if tuple(a) in interior or tuple(b) in interior or a[2]!=1 or b[2]!=1:continue
    p,q=Vector(points[tuple(a)]),Vector(points[tuple(b)])
    count=math.ceil((q-p).length/.1)
    for i in range(count+1):
        x,y,z=p+(q-p)*i/count
        for dx,dy in ((0,0),(.18,0),(-.18,0),(0,.18),(0,-.18)):
            # Terrace planks have 29 mm joints over the slab: as in the turbine
            # check, two of three samples 35 mm apart across the planks must
            # meet the whole-layer floor.
            floor=0
            for ex in (-.035,0,.035):
                hit=tree.ray_cast(Vector((-x-dx-ex,-y-dy,z+.08)),Vector((0,0,-1)),.12)
                if hit[0] is not None and abs(hit[0].z-z)<=.005:floor+=1
            if floor<2:failures.append(f'Floor {x+dx:.2f},{y+dy:.2f},{z}')
            hit=tree.ray_cast(Vector((-x-dx,-y-dy,z+.01)),Vector((0,0,1)),1.09)
            if hit[0] is not None:failures.append(f'Clearance {x+dx:.2f},{y+dy:.2f}: {owners[hit[2]]}')
        samples+=1
uv_count=0
for obj in model.objects:
    if obj.type!='MESH' or 'native_resource' in obj:continue
    if len(obj.material_slots)!=32:raise ValueError('Research palette must have 32 slots')
    uv=obj.data.uv_layers.active.data
    for p in obj.data.polygons:
        if p.material_index in (0,1,2,3,7,27,28,29,30):
            for loop in p.loop_indices:
                if not valid_native_uv(obj.material_slots[p.material_index].material.name,uv[loop].uv):raise ValueError('UV outside authored/native contract: '+obj.name)
                if p.material_index==7:
                    u,v=uv[loop].uv
                    if not .6199<=u<=.8801 or not .3289<=v<=.3481:raise ValueError('Laboratory band left the native metal strip')
                uv_count+=1
animated=[]
for suffix in ('PressScrew','TestRam','Flywheel'):
    obj=bpy.data.objects['MaterialsLaboratory.'+suffix]
    if obj.animation_data is None:raise ValueError('Missing laboratory animation: '+suffix)
    matrices=[]
    for frame in (1,31,61,121):
        scene.frame_set(frame);scene.view_layers[0].update();matrices.append(obj.matrix_world.copy())
    distance=lambda a,b:max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))
    if distance(matrices[0],matrices[-1])>1e-5:raise ValueError('Non-looping part '+suffix)
    if distance(matrices[0],matrices[1])<.1:raise ValueError('Static part '+suffix)
    animated.append(obj.name)
scene.frame_set(1)
result={'scope':'Source geometry and animations only; native operation remains to test',
    'terraceSamples':samples,'nativeUvCorners':uv_count,'animatedParts':animated,
    'railPorts':len(LAB['ports']),'terraceLayer':1,'failures':failures}
(ROOT/'outputs/materials-laboratory-source-validation.json').write_text(json.dumps(result,indent=2)+'\n')
if failures:raise ValueError(f'{len(failures)} source failures: '+str(failures[:16]))
print(json.dumps(result))
