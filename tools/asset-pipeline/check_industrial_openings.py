"""Inspect physical clearance from authored lane points through opened rails."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from industrial_layouts import ROOT, LAYOUTS

reports=[]
for ident,d in LAYOUTS.items():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'src/DeepFrontier/Art/Source'/(ident+'-Game.blend')))
    bpy.context.scene.frame_set(1)
    objects=[]
    for obj in bpy.data.collections[ident+'.ReferenceStudy'].objects:
        if obj.type!='MESH':continue
        objects.append((obj.name,[obj.matrix_world@v.co for v in obj.data.vertices],[tuple(p.vertices) for p in obj.data.polygons]))
    spec=json.loads((ROOT/'outputs/industrial-integration'/(ident+'-walkway.json')).read_text())
    points={tuple(n['cell']):n['point'] for n in d['nodes']}
    results=[]
    for port,opening in zip(d['ports'],spec['Openings']):
        assert port['id']==opening['Id']
        hidden=set(opening['HiddenNodes']);shown=set(opening['ShownNodes'])
        vertices=[];faces=[];face_names=[]
        for name,vs,fs in objects:
            if name in hidden or (name.startswith('WalkwayJoin.') and name not in shown):continue
            offset=len(vertices);vertices.extend(vs);faces.extend(tuple(offset+i for i in f) for f in fs);face_names.extend([name]*len(fs))
        tree=BVHTree.FromPolygons(vertices,faces)
        p=Vector(points[tuple(port['inside'])])+Vector(d['origin'])
        q=Vector(port['outside'])+Vector((.5,.5,0))
        axis=0 if port['inside'][0]!=port['outside'][0] else 1
        boundary=port['inside'][axis]+(1 if q[axis]>p[axis] else 0)
        approach=Vector(port['approach'])+Vector(d['origin'])
        t=(boundary-approach[axis])/(q[axis]-approach[axis]);end=approach+(q-approach)*t
        samples=[]
        for a,b in [(p,approach),(approach,end)]:
            count=max(1,math.ceil((b-a).length/.10))
            samples.extend(a+(b-a)*i/count for i in range(count+1))
        issues=[]
        for x,y,z in samples:
            support=0
            for dx in [-.035,0,.035]:
                floor=tree.ray_cast(Vector((-x-dx,-y,z+.08)),Vector((0,0,-1)),.12)
                if floor[0] is not None and abs(floor[0].z-z)<.006:support+=1
            if support<2:issues.append(dict(kind='floor',point=[x,y,z]))
            for dx,dy in [(0,0),(.2,0),(-.2,0),(0,.2),(0,-.2)]:
                hit=tree.ray_cast(Vector((-x-dx,-y-dy,z+.01)),Vector((0,0,1)),1.09)
                if hit[0] is not None:issues.append(dict(kind='clearance',point=[x,y,z],hit=list(hit[0]),object=face_names[hit[2]]))
        results.append(dict(port=port['id'],samples=len(samples),issueCount=len(issues),examples=issues[:3]))
    reports.append(dict(model=ident,ports=results))
target=ROOT/'outputs/industrial-integration/opening-clearance-diagnostics.json'
target.write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps([dict(model=r['model'],failed=[p for p in r['ports'] if p['issueCount']]) for r in reports]))
