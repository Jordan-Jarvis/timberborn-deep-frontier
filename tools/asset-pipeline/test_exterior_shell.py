"""Check the authored restaurant exterior against its closed room volumes."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from mathutils import Vector
from frontier_architecture import Geometry,facade_panel,PLANK
from restaurant_structure import ROOMS,EXTERIOR_WALLS

# Derive expected exposed unit faces only for validation. The mesh generator
# uses the explicit source spans and performs no automatic geometry cleanup.
cells=set()
for name in EXTERIOR_WALLS:
    x0,y0,z0,x1,y1,z1=ROOMS[name]
    cells.update((x,y,z) for x in range(x0,x1) for y in range(y0,y1) for z in range(z0,z1))
expected=set()
for x,y,z in cells:
    for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
        if (x+dx,y+dy,z) not in cells:expected.add((x,y,z,dx,dy))
authored=[]
for name,walls in EXTERIOR_WALLS.items():
    x0,y0,z0,x1,y1,z1=ROOMS[name]
    for side,spans in walls.items():
        for a,b in spans:
            for t in range(a,b):
                for z in range(z0,z1):
                    authored.append({'front':(t,y0,z,0,-1),'back':(t,y1-1,z,0,1),
                        'left':(x0,t,z,-1,0),'right':(x1-1,t,z,1,0)}[side])
assert len(authored)==len(set(authored)),'Duplicate exterior wall spans'
assert set(authored)==expected,(expected-set(authored),set(authored)-expected)
for axis in ('X','Y'):
    for positive in (False,True):
        g=Geometry('Facade shell test')
        facade_panel(g,axis,0,0,1,0,1,positive,PLANK)
        assert len(g.faces)==1 and len(g.vertices)==4
        a,b,c=[Vector(g.vertices[i]) for i in g.faces[0][:3]]
        normal=(b-a).cross(c-a).normalized()
        index=0 if axis=='X' else 1
        # Blender source coordinates negate authored X/Y.
        assert abs(normal[index]-(-1 if positive else 1))<1e-6
print(f'PASS: {len(expected)} exterior unit faces; no shared partitions; outward single-face wall panels')
