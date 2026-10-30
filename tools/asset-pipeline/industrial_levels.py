"""Authored whole-layer interfaces, with explicit rigid machinery placements.

One Blender height unit equals one Timberborn grid layer. These are design
coordinates, not rounded bounds or an export-time correction. Supports, floors
and stairs are built from the named levels. Existing machinery retains its
local dimensions when attached to the new floor.
"""
from mathutils import Vector
from frontier_architecture import Geometry

# Compact pass (2026-10-30): one layer per storey, the crusher's machine
# floor is layer 1 (was 2).
CRUSHER_DECK=1
KILN_DECK=2
FACTORY_ENTRANCE=0
FACTORY_PORCH_ROOF=1
QUARRY_ENTRANCE=0
CRUSHER_MACHINE_DATUM=1.50
KILN_MACHINE_DATUM=1.29
# The factories are not walked on above the ground door (user decision,
# 2026-10-21): CRUSHER_DECK/KILN_DECK are now the machine-floor layers the
# machinery stands on, and the quarry's layer 1 is a solid process plinth.
LEVELS={
    'StoneCrusher':{'entranceLayer':FACTORY_ENTRANCE,'porchRoofLayer':FACTORY_PORCH_ROOF,
                    'machineFloorLayer':CRUSHER_DECK,'walkableDeckLayers':[],'stairs':[],'access':'Ground door only','heightEnvelopeLayers':3},
    # Compact 5x3x4 (2026-10-30): the drum stands on ground plinths.
    'CementKiln':{'entranceLayer':FACTORY_ENTRANCE,'porchRoofLayer':FACTORY_PORCH_ROOF,
                  'machineFloorLayer':0,'walkableDeckLayers':[],'stairs':[],'access':'Ground door only','heightEnvelopeLayers':4},
    # Compact 8x6x5 (2026-10-30): no ladder mast.
    'MineralQuarry':{'entranceLayer':QUARRY_ENTRANCE,'plinthTopLayer':1,
                     'walkableDeckLayers':[],'stairs':[],'access':'Ground door only',
                     'heightEnvelopeLayers':5},
}


class MountedMachinery(Geometry):
    """Author a rigid assembly in its declared reference frame at a floor.

No scale change or bounds inspection occurs. Moving parts get the same explicit
placement for both their vertices and pivots. Lower walls/piers/stairs must be
authored independently from the whole-layer floor; they are not stretched.
"""
    def __init__(self,target,reference_floor,floor_layer):
        if floor_layer!=int(floor_layer):raise ValueError('Factory floor must be a whole grid layer')
        self.target=target;self.offset=Vector((0,0,floor_layer-reference_floor))
    def add(self,vertices,faces,mat):
        self.target.add([Vector(v)+self.offset for v in vertices],faces,mat)
    def moving_part(self,name,origin):
        target=Geometry(name,Vector(origin)+self.offset)
        return PartFrame(target,self.offset),target
    def emitter(self,kind,x,y,z,radius):
        """Record a vanilla smoke/steam mouth authored in this frame on the
        target art (lategame_kit.emitter), placed like the vertices. Adds no
        geometry."""
        from lategame_kit import emitter
        p=Vector((x,y,z))+self.offset
        emitter(self.target,kind,p.x,p.y,p.z,radius)


class PartFrame(Geometry):
    """Explicit rigid placement for a component pivot; never a grid interface."""
    def __init__(self,target,offset):self.target=target;self.offset=offset
    def add(self,vertices,faces,mat):self.target.add([Vector(v)+self.offset for v in vertices],faces,mat)
