"""CPU ray coverage tests for explicitly opaque architectural surfaces.

These are source-authoring checks, not placement/native shader acceptance.
Open decks, machinery, nursery baskets and conduit mouths are not enclosures.
Run with Blender --background --python-exit-code 1 --python this_file.py.
"""
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).parent))
from frontier_architecture import Geometry, wall, roof
from industrial_geometry import sheet_roof
from factory_facade_details import crusher_facades, kiln_facades
from materials_laboratory_geometry import concrete_course, slope_facade, shed_roof
from pit_isometric_geometry import enclosure
from mixer_isometric_geometry import operator_room
from quarry_isometric_geometry import room as quarry_room
from quarry_isometric_geometry import workshops as quarry_workshops
from crusher_sheet_geometry import workshop as crusher_workshop
from kiln_isometric_geometry import porch as kiln_porch
from hydro_isometric_geometry import cast_conduit
from structural_geometry import MODELS as STRUCTURAL_MODELS
from civic_isometric_geometry import framed_room,gabled_roof,roof_bearing
from industrial_facades import building_portal

ROOT=Path(__file__).resolve().parents[2]
reports=[]


def authored(v):
    return Vector((-v[0],-v[1],v[2]))


def check(name, builder, patches):
    g=Geometry(name);builder(g)
    bvh=BVHTree.FromPolygons(g.vertices,g.faces,all_triangles=False)
    failures=[];count=0
    for patch in patches:
        p0,u,v,normal=map(Vector,patch[:4])
        nu,nv=patch[4:6]
        for i in range(nu):
            for j in range(nv):
                p=p0+u*((i+.37)/nu)+v*((j+.43)/nv)
                start=authored(p+normal*.65);direction=authored(-normal)
                hit,hit_normal,index,distance=bvh.ray_cast(start,direction,.90)
                count+=1
                if hit is None or hit_normal.dot(direction)>=0:
                    failures.append([round(c,6) for c in p])
    reports.append({'name':name,'samples':count,'missingOrBackfacing':len(failures),'examples':failures[:12]})
    print(f'{name}: {count} samples, {len(failures)} missing/backfacing',flush=True)


check('shared plank wall',lambda g:wall(g,0,0,3,2,0),[
    ((.01,-.035,.01),(2.98,0,0),(0,0,1.98),(0,-1,0),301,41)])
check('shared pitched roof',lambda g:roof(g,0,0,3,3,2,3),[
    ((.08,.08,2+.08/1.5),(1.34,0,1.34/1.5),(0,2.84,0),(0,0,1),31,301)])
check('shared industrial sheet roof',lambda g:sheet_roof(g,0,0,3,3,2,3,12),[
    ((.08,.08,2+.08/3),(2.84,0,0),(0,2.84,2.84/3),(0,0,1),301,41)])
for height in (1.55,1.84,2.0,2.82,6.24):
    def framed(g,h=height):
        framed_room(g,0,0,3,4,0,h,3,(1.5,1.0,1.0))
        building_portal(g,1.5,-.16,0)
    check(f'civic framed room height {height}',framed,[
        ((-.05,-.06,.003),(3.10,0,0),(0,0,height-.006),(0,-1,0),301,101),
        ((-.06,-.05,.003),(0,4.10,0),(0,0,height-.006),(-1,0,0),301,101),
        ((3.06,-.05,.003),(0,4.10,0),(0,0,height-.006),(1,0,0),301,101),
        ((-.05,4.06,.003),(3.10,0,0),(0,0,height-.006),(0,1,0),301,101)])
check('civic roof sheets and gables',lambda g:gabled_roof(g,0,0,3,4,2,3,12),[
    ((.06,.06,2.04),(1.35,0,.9),(0,3.88,0),(0,0,1),51,401),
    ((1.59,.06,2.94),(1.35,0,-.9),(0,3.88,0),(0,0,1),51,401),
    ((.4,0,2.01),(2.2,0,0),(0,0,.24),(0,-1,0),301,61),
    ((.4,4,2.01),(2.2,0,0),(0,0,.24),(0,1,0),301,61)])
check('laboratory concrete courses',lambda g:concrete_course(g,0,0,3,4,2),[
    ((.15,-.075,.05),(2.7,0,0),(0,0,1.75),(0,-1,0),301,101),
    ((3.075,.15,.05),(0,3.7,0),(0,0,1.75),(1,0,0),301,101)])
check('laboratory sloped facade',lambda g:slope_facade(g,0,4,0,2,6,4,12,False),[
    ((.12,-.055,2.1),(3.76,0,0),(0,0,1.6),(0,-1,0),401,51)])
check('laboratory shed roof',lambda g:shed_roof(g,0,4,0,3,6,4,12),[
    ((.12,.12,5.94),(3.76,0,-1.88),(0,2.76,0),(0,0,1),41,301)])
check('pit storeroom',lambda g:enclosure(g,limestone=False),[
    ((.2625,1.28,.6),(0,2.25,0),(0,0,1.4),(-1,0,0),301,51),
    ((.44,3.74,.4),(.96,0,0),(0,0,2.25),(0,1,0),151,101),
    ((.2625,1.25,2.18),(0,2.2,.53),(0,0,.05),(-1,0,0),151,31)])
check('mixer operator room',operator_room,[
    ((.4525,1.28,.5),(0,2.25,0),(0,0,1.2),(-1,0,0),301,51),
    ((.56,3.7175,.4),(2.03,0,0),(0,0,1.2),(0,1,0),301,51),
    ((.49,.46,.1),(.58,0,0),(0,0,.8),(0,-1,0),151,51),
    ((.55,1.15,1.15),(2.15,0,0),(0,0,.65),(0,-1,0),151,51),
    ((.58,1.25,1.86),(2.10,0,0),(0,2.25,0),(0,0,1),151,101),
    ((.4525,.57,.05),(0,.50,0),(0,0,.95),(-1,0,0),81,101)])
check('crusher right wall',crusher_facades,[
    ((3.6375,1.35,.4),(0,2.10,0),(0,0,1.2),(1,0,0),301,51)])
check('kiln operator side walls',kiln_facades,[
    ((2.8425,.40,.4),(0,2.70,0),(0,0,1.2),(-1,0,0),301,51)])
check('quarry workshop side infill',lambda g:quarry_room(g,.35,4.30,1.92,6.56,3.25,710,'left'),[
    ((.315,4.45,1.08),(0,1.95,0),(0,0,.5),(-1,0,0),301,31),
    ((.35,4.45,3.15),(0,1.95,0),(0,0,.22),(-1,0,0),151,41)])
check('quarry ground cabin',quarry_workshops,[
    ((.77,1.43,.02),(0,.48,0),(0,0,1.24),(-1,0,0),91,101),
    ((1.96,1.43,.02),(0,.48,0),(0,0,1.24),(1,0,0),91,101)])
check('crusher porch header and side curb',crusher_workshop,[
    ((.61,.39,1.01),(1.0,0,0),(0,0,.1),(0,-1,0),151,31),
    ((.56,.48,1.10),(0,.55,0),(0,0,.05),(-1,0,0),151,31)])
check('kiln porch header and side curb',kiln_porch,[
    ((2.99,-.79,1.01),(.92,0,0),(0,0,.09),(0,-1,0),151,31),
    ((2.95,-.68,1.10),(0,.85,0),(0,0,.05),(-1,0,0),151,31)])
check('hydro concrete conduit joints',cast_conduit,[
    ((.08,.18,.45),(0,5.64,0),(0,0,.42),(-1,0,0),601,31),
    ((2.55,.18,2.839),(0,5.64,0),(.10,0,-.03),(0,0,1),601,11)])
for name in ('SandstoneMasonryBlock','LimestoneMasonryBlock','ConcreteBlock','ReinforcedDamBlock','ConcreteOverflowDam'):
    height=.55 if name=='ConcreteOverflowDam' else .80
    check(name,lambda g,n=name:STRUCTURAL_MODELS[n](g,[]),[
        ((.04,-.01,.04),(.92,0,0),(0,0,height),(0,-1,0),101,61),
        ((1.01,.04,.04),(0,.92,0),(0,0,height),(1,0,0),101,61)])

result={'scope':'Explicit CPU source surface coverage, not native/render or whole-building closure acceptance','checks':reports}
out=ROOT/'outputs/catalog-surface-coverage.json';out.write_text(json.dumps(result,indent=2)+'\n')
assert all(r['missingOrBackfacing']==0 for r in reports),f'Exterior source gaps: inspect {out}'
print('PASS explicit opaque source surfaces')
