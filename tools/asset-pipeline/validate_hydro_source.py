"""Inspect the saved turbine study, not its authoring constants or game behavior."""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from native_uv_contract import valid_native_uv

root=Path(__file__).resolve().parents[2]
source=root/'src/DeepFrontier/Art/Source/ReinforcedHydroTurbine-ReferenceStudy.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
scene=bpy.context.scene
collection=bpy.data.collections['ReinforcedHydroTurbine.ReferenceStudy']
scene.frame_set(1);scene.view_layers[0].update()
vertices=[];faces=[];owners=[];uv_corners=0
for obj in collection.objects:
    if obj.type!='MESH':continue
    offset=len(vertices)
    vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
    faces.extend(tuple(offset+i for i in face.vertices) for face in obj.data.polygons)
    owners.extend([obj.name]*len(obj.data.polygons))
    assert len(obj.material_slots)==32 and obj.data.uv_layers, obj.name
    for face in obj.data.polygons:
        # Details.IronTeeth is labels, sacks and crates, not brass fittings.
        assert face.material_index!=7, (obj.name,'Decorative-label material on turbine hardware')
        if face.material_index in (0,1,2,3,27,28,29):
            for i in face.loop_indices:
                assert valid_native_uv(obj.material_slots[face.material_index].material.name,obj.data.uv_layers.active.data[i].uv), obj.name
                uv_corners+=1
tree=BVHTree.FromPolygons(vertices,faces)
routes=[
    ((4.5,4.5,2),(7.5,4.5,2)),
    ((7.5,4.5,2),(7.5,9.5,2)),
    ((7.5,9.5,2),(4.5,9.5,2)),
    # Door spur up to the casing face (y=6) less the 0.2 body radius; the
    # forward sample then reaches the face, not the native lintel inside it.
    ((6.5,4.5,2),(6.5,5.8,2)),
]
failures=[];route_samples=0
for a,b in routes:
    a,b=Vector(a),Vector(b);count=math.ceil((b-a).length/.08)
    for i in range(count+1):
        x,y,z=a+(b-a)*i/count
        floor=0
        for dx in (-.035,0,.035):
            hit=tree.ray_cast(Vector((-x-dx,-y,z+.08)),Vector((0,0,-1)),.12)[0]
            if hit is not None and abs(hit.z-z)<.005:floor+=1
        if floor<2:failures.append(f'Missing terrace at {x:.2f},{y:.2f}')
        for dx,dy in ((0,0),(.2,0),(-.2,0),(0,.2),(0,-.2)):
            hit=tree.ray_cast(Vector((-x-dx,-y-dy,z+.01)),Vector((0,0,1)),1.09)
            if hit[0] is not None:
                failures.append(f'Headroom at {x:.2f},{y:.2f}: {owners[hit[2]]}')
        route_samples+=1
support_samples=0
for x in (.3,.7,1.3,1.7,2.3,2.7,3.3,3.7):
    for y in (2.3,2.7,3.3,3.7):
        hit=tree.ray_cast(Vector((-x,-y,6.1)),Vector((0,0,-1)),.2)[0]
        assert hit is not None and abs(hit.z-6)<.005, ('Missing cap support',x,y)
        support_samples+=1
animations=[]
for name in ('Hydro.GeneratorCoupling','Hydro.TurbineRunner'):
    obj=bpy.data.objects[name]
    assert obj.animation_data is not None, name
    transforms=[]
    for frame in range(1,122):
        scene.frame_set(frame);scene.view_layers[0].update()
        transforms.append(obj.matrix_world.copy())
        if name=='Hydro.TurbineRunner':
            # Actual animated vertices remain within the continuous bore.
            for v in obj.data.vertices:
                p=obj.matrix_world@v.co
                x,y,z=-p.x,-p.y,p.z
                assert 1.05<x<2.95 and 4.70<y<5.13 and .10<z<1.98, (name,frame,list(p))
    assert max(abs(transforms[0][i][j]-transforms[-1][i][j])
               for i in range(4) for j in range(4))<1e-5, (name,'Loop seam')
    assert max(abs(transforms[0][i][j]-transforms[15][i][j])
               for i in range(3) for j in range(3))>.1, (name,'No motion')
    animations.append(name)
scene.frame_set(1)
report={
    'scope':'Saved Blender study only; no native footprint, power, water control or walking claim',
    'source':str(source),'routeSamples':route_samples,'bodyRadius':.2,'headroom':1.1,
    'damCapSupportSamples':support_samples,'nativeUvCorners':uv_corners,
    'animatedParts':animations,'framesInspectedPerPart':121,
    'boundsMin':[min(p[a] for p in vertices) for a in range(3)],
    'boundsMax':[max(p[a] for p in vertices) for a in range(3)],
    'failures':failures,
}
target=root/'outputs/hydro-source-checks.json'
target.write_text(json.dumps(report,indent=2)+'\n')
if failures:raise ValueError(str(failures[:20]))
print(json.dumps(report))
