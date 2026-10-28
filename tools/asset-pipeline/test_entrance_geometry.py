"""Run in Blender: enforce the one-tile exterior doorway authoring contract."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from frontier_architecture import Geometry
from industrial_facades import building_portal,building_portal_side
from grid_structure import room
from mathutils import Vector
from mathutils.bvhtree import BVHTree

for side in (False,True):
    g=Geometry('Entrance contract')
    (building_portal_side if side else building_portal)(g,0,0,0)
    points=g.vertices
    axis=1 if side else 0
    low=min(p[axis] for p in points);high=max(p[axis] for p in points)
    assert abs(high-low-1)<1e-6,(side,low,high)
    assert abs(min(p[2] for p in points))<1e-6
    assert abs(max(p[2] for p in points)-1)<1e-6
    assert len(g.face_sources)==len(g.faces)
    # Bounds alone did not catch the old arch's transparent corner wedges.
    # Every point inside the full insert must hit its opaque outward surface.
    tree=BVHTree.FromPolygons([Vector(p) for p in points],g.faces,all_triangles=False)
    for i in range(100):
        for j in range(100):
            across=-.5+(i+.5)/100;height=(j+.5)/100
            origin=Vector((1,across,height) if side else (across,1,height))
            direction=Vector((-1,0,0) if side else (0,-1,0))
            hit,normal,face,distance=tree.ray_cast(origin,direction,2)
            assert hit is not None,(side,'open doorway panel',across,height)
            assert normal.dot(direction)<0,(side,'inward doorway face',face)
    # Rays enter just inside the facade cutout, then travel out through a
    # recessed edge. They miss a bare rear sheet and catch missing returns.
    for entry,direction in (((.49,0,.9),(.6,1,0)),((-.49,0,.9),(-.6,1,0)),
            ((.45,0,.99),(0,1,.6)),((-.45,0,.99),(0,1,.6)),
            ((.45,0,.01),(0,1,-.6)),((-.45,0,.01),(0,1,-.6))):
        entry=Vector((-entry[0],-entry[1],entry[2]))
        direction=Vector((-direction[0],-direction[1],direction[2])).normalized()
        if side:
            entry=Vector((entry.y,entry.x,entry.z))
            direction=Vector((direction.y,direction.x,direction.z))
        hit=tree.ray_cast(entry-direction,direction,1.2)
        assert hit[0] is not None,('Open oblique insert perimeter',entry,direction)
        assert hit[1].dot(direction)<-1e-6,('Back-facing oblique insert perimeter',entry,direction,hit[1],hit[2])

# A doorway as wide as its cell has no shoulder infill. It must not create
# reversed/negative boxes when the opening is subtracted from the wall.
g=Geometry('Single cell stairhead')
original_box=g.box
def positive_box(center,size,material):
    assert min(size)>0,(center,size)
    original_box(center,size,material)
g.box=positive_box
room(g,'Stairhead',[0,0,0,1,2,2],[0,0,0],(.5,1.0),
     exterior={'front':[(0,1)],'back':[(0,1)],'left':[(0,2)],'right':[(0,2)]})
tree=BVHTree.FromPolygons([Vector(p) for p in g.vertices],g.faces,all_triangles=False)
for i in range(100):
    for j in range(60):
        x=(i+.5)/100;z=1.01+(j+.5)*.98/60
        hit=tree.ray_cast(Vector((-x,1,z)),Vector((0,-1,0)),1.3)
        assert hit[0] is not None,('Gap above one-cell door',x,z)
print('PASS: 1x1 front/side doors; 20,000 opaque front samples; twelve outward-facing angled seam probes; 6,000 closed upper-stairhead samples; positive room geometry')
