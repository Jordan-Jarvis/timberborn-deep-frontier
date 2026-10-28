"""Geometry diagnostics for authored flat route segments, independently of navmesh."""
import json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from industrial_layouts import ROOT,LAYOUTS
reports=[]
for ident,d in LAYOUTS.items():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'src/DeepFrontier/Art/Source'/(ident+'-Game.blend')))
    collection=bpy.data.collections[ident+'.ReferenceStudy'];bpy.context.scene.frame_set(1)
    vertices=[];faces=[];face_names=[]
    for obj in collection.objects:
        if obj.type!='MESH' or obj.name.startswith('WalkwayJoin.'):continue
        offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in p.vertices) for p in obj.data.polygons)
        face_names.extend([obj.name]*len(obj.data.polygons))
    tree=BVHTree.FromPolygons(vertices,faces)
    points={tuple(n['cell']):n['point'] for n in d['nodes']};issues=[];checked=0
    for a,b in d['edges']:
        if a[2]!=b[2]:continue
        p,q=Vector(points[tuple(a)]),Vector(points[tuple(b)])
        count=math.ceil((q-p).length/.12)
        edgeIssues=[]
        for i in range(count+1):
            x,y,z=p+(q-p)*i/count
            if ident=='MineralQuarry' and z>=3 and 2.12<x<2.88 and 7.12<y<7.88:continue
            x+=d['origin'][0];y+=d['origin'][1];z+=d['origin'][2]
            hits=0
            for dx in [-.035,0,.035]:
                hit=tree.ray_cast(Vector((-x-dx,-y,z+.08)),Vector((0,0,-1)),.12)
                if hit[0] is not None and abs(hit[0].z-z)<.006:hits+=1
            if hits<2:edgeIssues.append(dict(issue='floor',point=[x,y,z]))
            for dx,dy in [(0,0),(.2,0),(-.2,0),(0,.2),(0,-.2)]:
                hit=tree.ray_cast(Vector((-x-dx,-y-dy,z+.01)),Vector((0,0,1)),1.09)
                if hit[0] is not None:edgeIssues.append(dict(issue='clearance',point=[x,y,z],hit=list(hit[0]),object=face_names[hit[2]]))
            checked+=1
        if edgeIssues:issues.append(dict(edge=[a,b],issueCount=len(edgeIssues),examples=edgeIssues[:4]))
    reports.append(dict(model=ident,samples=checked,issues=issues))
target=ROOT/'outputs/industrial-integration/route-clearance-diagnostics.json'
target.write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports),flush=True)
