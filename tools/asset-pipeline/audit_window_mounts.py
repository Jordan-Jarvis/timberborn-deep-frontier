"""Report explicit native window mounts whose rear plane lacks nearby wall.

All window faces are excluded from backing rays. This diagnoses source mount
positions; it never moves, snaps, fills or normalizes an assembly.
"""
import inspect
import json
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
import architectural_windows
original=architectural_windows.window
geometries={}


def backing_distances(tree,w):
    distances=[]
    for u_fraction,z_fraction in ((.5,.5),(.25,.35),(.75,.35),(.25,.65),(.75,.65)):
        u=w['u0']+(w['u1']-w['u0'])*u_fraction;z=w['z0']+(w['z1']-w['z0'])*z_fraction
        p=w['normal']*(w['rear']-.001)+w['tangent']*u+Vector((0,0,z))
        hit=tree.ray_cast(p,w['normal'],.40)
        distances.append(None if hit[0] is None else round(hit[3]-.001,6))
    return distances


# Regress the source-axis ray direction and both positive/missing findings.
# These fixtures deliberately have no native window geometry to self-hit.
fixture=BVHTree.FromPolygons([(-1,0,0),(1,0,0),(1,0,2),(-1,0,2)],[(0,1,2,3)])
probe={'normal':Vector((0,-1,0)),'tangent':Vector((1,0,0)),
       'rear':0,'u0':-.2,'u1':.2,'z0':.7,'z1':1.3}
assert backing_distances(fixture,probe)==[0]*5
assert backing_distances(fixture,probe|{'rear':-.02})==[.02]*5
assert backing_distances(fixture,probe|{'u0':2,'u1':3})==[None]*5


def record(g,x,y,z,scale=1,face='front',style='grand'):
    start=len(g.faces);start_vertex=len(g.vertices)
    original(g,x,y,z,scale,face,style)
    # Geometry.add stores (-x,-y,z) relative to its authored origin. Rays,
    # anchors and existing vertices must all use that same source coordinate
    # system; normal points from the exterior through the wall.
    normal=Vector({'front':(0,-1,0),'back':(0,1,0),'left':(-1,0,0),'right':(1,0,0)}[face])
    anchor=Vector((g.origin.x-x,g.origin.y-y,z-g.origin.z))
    tangent=Vector((-normal.y,normal.x,0))
    points=[Vector(p) for p in g.vertices[start_vertex:]]
    depths=[p.dot(normal) for p in points];us=[p.dot(tangent) for p in points];zs=[p.z for p in points]
    stack=[]
    for frame in inspect.stack()[1:5]:stack.append(f'{Path(frame.filename).name}:{frame.lineno}:{frame.function}')
    definition={'position':[x,y,z],'face':face,'style':style,'scale':scale,'source':' > '.join(stack),
        'firstFace':start,'endFace':len(g.faces),'rear':anchor.dot(normal),'u0':min(us),'u1':max(us),'z0':min(zs),'z1':max(zs),
        'normal':normal,'tangent':tangent}
    geometries.setdefault(id(g),{'geometry':g,'windows':[]})['windows'].append(definition)


architectural_windows.window=record
from render_reference_studies import MODELS

models=['GroceryStore','FisheryWorks','FishHatchery','ReinforcedHydroTurbine','MaterialsLaboratory',
        'StoneCrusher','CementKiln','MineralQuarry','ConcreteMixer','SandstonePit','LimestonePit']
reports=[]
for model in models:
    geometries.clear()
    from frontier_architecture import Geometry
    g=Geometry(model);MODELS[model](g,[])
    findings=[];count=0
    for entry in geometries.values():
        geo=entry['geometry'];windows=entry['windows'];excluded=set()
        for w in windows:excluded.update(range(w['firstFace'],w['endFace']))
        faces=[f for i,f in enumerate(geo.faces) if i not in excluded]
        tree=BVHTree.FromPolygons(geo.vertices,faces,all_triangles=False)
        for w in windows:
            count+=1;distances=backing_distances(tree,w)
            if any(d is None or d>.001 for d in distances):
                findings.append({k:v for k,v in w.items() if k in ('position','face','style','scale','source')}|{'backingDistances':distances})
    reports.append({'model':model,'windows':count,'mountFindings':findings})
    print(model,count,'windows',len(findings),'mount findings',flush=True)
out=ROOT/'outputs/window-mount-audit.json'
out.write_text(json.dumps({'scope':__doc__,'models':reports},indent=2)+'\n')
print('Window mount report:',out)
assert all(not r['mountFindings'] for r in reports),'Missing or detached window backing; inspect mount report'
