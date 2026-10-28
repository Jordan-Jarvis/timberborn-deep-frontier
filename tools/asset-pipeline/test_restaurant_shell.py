"""Sample the evaluated exterior shell, including bevels and face orientation.

Run in Blender. These are near-surface probes, not rays through the building:
a wall on the far side cannot hide an open seam in the wall being checked.
Each failure retains its exact source-space segment and nearest mesh face.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from restaurant_structure import ORIGIN,ROOMS,EXTERIOR_WALLS,PLATFORMS

parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
scene_path=ROOT/'src/DeepFrontier/Art/Source/Restaurant-ReferenceStudy.blend'
bpy.ops.wm.open_mainfile(filepath=str(scene_path))
deps=bpy.context.evaluated_depsgraph_get()
vertices=[];faces=[];records=[]
for obj in bpy.data.collections['Restaurant.ReferenceStudy'].all_objects:
    if obj.type!='MESH':continue
    evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh()
    offset=len(vertices)
    vertices.extend(evaluated.matrix_world@v.co for v in mesh.vertices)
    for p in mesh.polygons:
        faces.append(tuple(offset+i for i in p.vertices))
        records.append({'object':obj.name,'polygon':p.index,'material':mesh.materials[p.material_index].name})
    evaluated.to_mesh_clear()
tree=BVHTree.FromPolygons(vertices,faces,all_triangles=False)
failures=[];counts={}

def blend(p):return Vector((-p[0],-p[1],p[2]))
def probe(label,point,outward,tangent=(0,0,0),interior_offset=(0,0,0)):
    counts[label]=counts.get(label,0)+1
    point=Vector(point);outward=Vector(outward);tangent=Vector(tangent)
    start=point+outward*.30+tangent*.20
    end=point-outward*.20+Vector(interior_offset)
    a=blend(start);b=blend(end);direction=(b-a).normalized();limit=(b-a).length
    cursor=a;remaining=limit;first=None
    # Renderers cull inward-facing polygons. Skip them explicitly so a rear
    # wall or inward sheet cannot make a broken exterior appear covered.
    for _ in range(16):
        hit,normal,index,distance=tree.ray_cast(cursor,direction,remaining)
        if hit is None:break
        if first is None:first=records[index]
        if normal.dot(direction)<-1e-6:return
        step=distance+.00005;cursor+=direction*step;remaining-=step
        if remaining<=0:break
    failures.append({'part':label,'point':list(point),'outward':list(outward),
                     'start':list(start),'end':list(end),'firstFace':first})

def samples(a,b,spacing=.04):
    n=math.ceil((b-a)/spacing)
    return [a+(i+.5)*(b-a)/n for i in range(n)]

for ident,walls in EXTERIOR_WALLS.items():
    x0,y0,z0,x1,y1,z1=ROOMS[ident]
    for side,runs in walls.items():
        normal={'front':(0,-1,0),'back':(0,1,0),'left':(-1,0,0),'right':(1,0,0)}[side]
        for a,b in runs:
            # Corner rays finish inside the room, so the adjoining facade
            # must close them. A straight ray5mm from the nominal tile edge
            # can lie wholly outside an intentionally recessed14mm frame.
            for along in [a+.005,*samples(a,b),b-.005]:
                inset=.06 if along==a+.005 else -.06 if along==b-.005 else 0
                interior=(inset,0,0) if side in ('front','back') else (0,inset,0)
                for z in samples(z0+.005,z1-.005):
                    p=(along,y0 if side=='front' else y1,z) if side in ('front','back') else (x0 if side=='left' else x1,along,z)
                    p=tuple(v-o for v,o in zip(p,ORIGIN,strict=True))
                    probe(ident+'/'+side,p,normal,interior_offset=interior)
            # Oblique grazing views near every course and storey joint expose
            # gaps caused by recessed panels meeting bevelled beams.
            heights=[z0+.005,z0+.20,z0+.45,z0+.53,z1-.36,z1-.33,z1-.28,z1-.005]
            for along in samples(a+.005,b-.005,.08):
                for z in heights:
                    p=(along,y0 if side=='front' else y1,z) if side in ('front','back') else (x0 if side=='left' else x1,along,z)
                    p=tuple(v-o for v,o in zip(p,ORIGIN,strict=True))
                    for slope in (-1,1):
                        # A camera below the ground is not an exterior wall
                        # view; ground-level shells intentionally have no
                        # hidden room floor. Keep those probes above terrain.
                        if z0==0 and z+slope*.20<0:continue
                        probe(ident+'/'+side+'/joint',p,normal,(0,0,slope))

# The rotated rooftop stairhead has a complete exterior on all four sides.
for side,axis,plane,a,b,normal in [('front',1,3.85,4.8,6.8,(0,-1,0)),
        ('back',1,4.85,4.8,6.8,(0,1,0)),('left',0,4.8,3.85,4.85,(-1,0,0)),
        ('door',0,6.8,3.85,4.85,(1,0,0))]:
    for across in [a+.005,*samples(a,b),b-.005]:
        inset=.06 if across==a+.005 else -.06 if across==b-.005 else 0
        interior=(inset,0,0) if axis==1 else (0,inset,0)
        for z in samples(6.005,8.075):
            p=(across,plane,z) if axis==1 else (plane,across,z)
            probe('RoofStairhead/'+side,p,normal,interior_offset=interior)

roofs=[('MainRoof',1.37,2.62,6.24,5.99,6.31,7.80),
       ('StairheadRoof',4.7,3.75,6.9,4.85,8.08,8.55)]
for label,x0,y0,x1,y1,eave,ridge in roofs:
    mid=(x0+x1)/2
    for x in samples(x0+.02,x1-.02):
        height=eave+(ridge-eave)*(1-abs(x-mid)/((x1-x0)/2))
        for y in samples(y0+.02,y1-.02,.027):
            probe(label+'/slope',(x,y,height),(0,0,1))
    for y,normal in ((y0,(0,-1,0)),(y1,(0,1,0))):
        for x in samples(x0+.02,x1-.02,.019):
            high=eave+(ridge-eave)*(1-abs(x-mid)/((x1-x0)/2))
            for z in samples(eave+.01,high):probe(label+'/gable',(x,y,z),normal)

# Explicit platform edges and board-joint lines. Testing only the center of
# each tile missed the previous backing inset and adjoining slab bevel holes.
for label,bounds in PLATFORMS.items():
    x0,y0,z0,x1,y1,z1=bounds
    nx=math.ceil((x1-x0)/.05);ny=math.ceil((y1-y0)/.20)
    for i in range(nx+1):
        # A ray precisely tangent to a polygon boundary has no defined area
        # coverage. Probe half a millimetre inside the outer slab edges while
        # retaining exact interior board-joint positions.
        x=x0+.0005 if i==0 else x1-.0005 if i==nx else x0+(x1-x0)*i/nx
        for j in range(ny+1):
            y=y0+.0005 if j==0 else y1-.0005 if j==ny else y0+(y1-y0)*j/ny
            p=(x-ORIGIN[0],y-ORIGIN[1],z1)
            probe(label+'/deck-joints',p,(0,0,1))

report={'scope':'Evaluated Blender near-surface coverage with outward-face culling; not a native shader test',
        'sourceSha256':hashlib.sha256(scene_path.read_bytes()).hexdigest(),
        'samples':sum(counts.values()),'byPart':counts,'failureCount':len(failures),'failures':failures}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(report,indent=2)+'\n')
print('RESTAURANT SHELL',report['samples'],'samples;',len(failures),'uncovered;',args.output,flush=True)
if failures:raise AssertionError('Exterior shell coverage failed; exact source segments are in '+str(args.output))
