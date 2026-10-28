"""Require real architecture behind every authored Restaurant window reveal."""
import json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from frontier_architecture import Geometry
from civic_isometric_geometry import restaurant
g=Geometry('Restaurant window contact check');restaurant(g,[])
window_faces={i for mount in g.window_mounts for i in range(*mount['faceRange'])}
tree=BVHTree.FromPolygons([Vector(v) for v in g.vertices],
    [face for i,face in enumerate(g.faces) if i not in window_faces],all_triangles=False)
def blend(p):return Vector((-p[0],-p[1],p[2]))
failures=[];samples=0
for index,mount in enumerate(g.window_mounts):
    normal=Vector(mount['outward'])
    for a,b in mount['rearEdges']:
        for t in (.02,.25,.50,.75,.98):
            p=Vector(a).lerp(Vector(b),t);samples+=1
            start=blend(p+normal*.10);direction=blend(-normal)
            hit=tree.ray_cast(start,direction,.104)
            if hit[0] is None:
                failures.append({'window':index,'style':mount['style'],'anchor':mount['anchor'],
                                 'point':list(p),'outward':list(normal)})
report={'scope':'Authored geometry; every tested window/reveal excluded from backing tree',
        'windows':len(g.window_mounts),'samples':samples,'failureCount':len(failures),'failures':failures}
(ROOT/'outputs/restaurant-window-contacts.json').write_text(json.dumps(report,indent=2)+'\n')
print('RESTAURANT WINDOW CONTACTS',report['windows'],'windows',samples,'probes',len(failures),'missing')
if failures:raise AssertionError('Native windows lack physical wall backing: '+str(failures[:5]))
