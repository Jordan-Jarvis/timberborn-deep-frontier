"""Mesh clearance for the explicitly authored waterfront game-grid routes."""
import json,sys,math
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from fishery_layout import F

collection=bpy.data.collections['FisheryWorks.ReferenceStudy']
bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
vertices=[];faces=[];owners=[]
for obj in collection.objects:
    if obj.type!='MESH':continue
    offset=len(vertices)
    vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
    faces.extend(tuple(offset+i for i in p.vertices) for p in obj.data.polygons)
    owners.extend([obj.name]*len(obj.data.polygons))
tree=BVHTree.FromPolygons(vertices,faces)
inside={tuple(c) for c in F['interiorCells']+F['doorNodes']}
points={tuple(n['cell']):Vector(n['point']) for n in F['nodes']}
samples=[]
for cell,point in points.items():
    if cell not in inside and cell[2]>0:samples.append(point)
for a,b in F['edges']:
    a,b=tuple(a),tuple(b)
    if a in inside or b in inside or a[2]==0 or b[2]==0:continue
    p,q=points[a],points[b];count=math.ceil((q-p).length/.10)
    samples.extend(p+(q-p)*(i/count) for i in range(1,count))
failures=[]
for x,y,z in samples:
    contacts=0
    for dx in (-.035,0,.035):
        hit=tree.ray_cast(Vector((-x-dx,-y,z+.08)),Vector((0,0,-1)),.12)
        if hit[0] is not None and abs(hit[0].z-z)<.005:contacts+=1
    if contacts<2:failures.append(f'Floor {x:.3f},{y:.3f},{z}')
    for dx,dy in ((0,0),(.20,0),(-.20,0),(0,.20),(0,-.20)):
        # One-layer storeys since 2026-10-30 (civic_isometric_geometry
        # CIVIC_ACCESS FisheryWorks headroom): clear up to the roof's eave timbers.
        hit=tree.ray_cast(Vector((-x-dx,-y-dy,z+.01)),Vector((0,0,1)),.85)
        if hit[0] is not None:failures.append(f'Body {x+dx:.3f},{y+dy:.3f},{hit[0].z:.3f}: {owners[hit[2]]}')
report={'scope':'Source mesh against authored game-route waypoints; native movement still requires playtesting',
        'size':F['size'],'origin':F['origin'],'exteriorSamples':len(samples),'failures':failures}
(ROOT/'outputs/fishery-reference-redesign/game-route-clearance.json').write_text(json.dumps(report,indent=2)+'\n')
if failures:raise ValueError('\n'.join(failures[:30]))
print('WATERFRONT GAME ROUTE GEOMETRY PASSED',len(samples))
