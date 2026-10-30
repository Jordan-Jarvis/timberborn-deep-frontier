"""Explicit restaurant structural edges in native XYZ; upper bounds exclusive.

2026-10-22 (user): no forced decoration beyond the walls. The ground service
counters, their awnings and the barrel under the dining balcony are gone, and
the empty first row and column left the footprint (10x8 -> 9x7): native x and
y are 1 less, ORIGIN -1, artwork unchanged. The dining balconies stay as part
of the building; the ground under them is open between their posts.

2026-10-30 compaction (user: "needs to be shortened but footprint needs to
stay the same"; "currently we have two layers between floors, we should
reduce it to one"). The 9x7 footprint, origin and ground door are unchanged.
Every storey is one layer: ground hall, kitchen and vestibule 0-1, middle hall
and the first dining balcony at 1, upper hall and the second at 2, and a flat
roof at 3 (the main roof and the roof terrace bays one continuous slab). The
gabled roof, dormers and roof lantern are gone; the roof stairhead is one
layer with a flat cap. Height 9 -> 5.

This is the authoring contract for meshes, occupied cells and picking volumes.
Decorative trim, lanterns and furniture retain their independent dimensions.
"""
# y is the double just above -0.85: with -0.85 itself no source coordinate
# sums exactly to the native rail boundary y=4 (walkway_geometry.run_grid
# needs exact cell cuts). The 1e-16 artwork offset is immaterial.
ORIGIN = [-.8, -.8499999999999999, 0]
SIZE = [9, 7, 5]
PLATFORMS = {
    'EntranceVestibuleCap': [0,2,0,1,3,1],
    'DiningFront': [0,0,0,6,2,1],
    'DiningSideFront': [6,1,0,7,2,1],
    'DiningSide': [5,2,0,7,7,1],
    'DiningRear': [1,5,0,5,7,1],
    'UpperDiningFront': [0,0,1,6,2,2],
    'UpperDiningSideFront': [6,1,1,7,2,2],
    'UpperDiningSide': [5,2,1,7,7,2],
    'UpperDiningRear': [1,5,1,5,7,2],
    # The flat main roof over the upper hall: a cast slab with timber decking,
    # one level with the roof terrace bays beside it.
    'MainRoof': [1,2,2,5,5,3],
    'RoofTerraceInner': [5,2,2,7,5,3],
    'RoofTerraceOuter': [7,2,2,9,5,3],
}
# Explicit short posts: (native occupied tile, corner signs, bottom level).
# Main rooms and shared beams carry the inner deck edges. The outer roof bay
# is cantilevered from the inner terrace and has no ground-reaching legs.
SUPPORTS = {
    'EntranceVestibuleCap': [],
    'DiningFront': [([0,0],[-1,-1],0),([3,0],[1,-1],0),([5,0],[1,-1],0)],
    'DiningSideFront': [([6,1],[1,-1],0)],
    'DiningSide': [([6,3],[1,1],0),([6,6],[1,1],0)],
    'DiningRear': [],
    'UpperDiningFront': [([0,0],[-1,-1],1),([3,0],[1,-1],1),([5,0],[1,-1],1)],
    'UpperDiningSideFront': [([6,1],[1,-1],1)],
    'UpperDiningSide': [([6,3],[1,1],1),([6,6],[1,1],1)],
    'UpperDiningRear': [([1,6],[-1,1],1),([4,6],[1,1],1)],
    'MainRoof': [],
    'RoofTerraceInner': [([6,2],[1,-1],2),([6,4],[1,1],2)],
    'RoofTerraceOuter': [],
}
ROOMS = {
    'GroundHall': [1,2,0,5,5,1],
    'MiddleHall': [1,2,1,5,5,2],
    'UpperHall': [1,2,2,5,5,3],
    'EntranceVestibule': [0,1,0,3,3,1],
    'Kitchen': [1,5,0,5,7,1],
    'RoofStairhead': [4,3,3,6,4,4],
}
# Render only exposed facades. Shared room partitions have no mesh, posts or
# trim. These exact authored spans are independent of native room occupation.
EXTERIOR_WALLS = {
    'GroundHall': {'front':[(3,5)],'back':[],'left':[(3,5)],'right':[(2,5)]},
    'MiddleHall': {'front':[(1,5)],'back':[(1,5)],'left':[(2,5)],'right':[(2,5)]},
    'UpperHall': {'front':[(1,5)],'back':[(1,5)],'left':[(2,5)],'right':[(2,5)]},
    'EntranceVestibule': {'front':[(0,3)],'back':[(0,1)],'left':[(1,3)],'right':[(1,2)]},
    'Kitchen': {'front':[],'back':[(1,5)],'left':[(5,7)],'right':[(5,7)]},
}
DOORS = {
    'GroundDoor': {'position':[1.5,1,0], 'outward':[0,-1], 'width':1.0},
    'MiddleDoor': {'position':[3.5,2,1], 'outward':[0,-1], 'width':1.0},
    'UpperDoor': {'position':[3.5,2,2], 'outward':[0,-1], 'width':1.0},
    'RoofTerraceDoor': {'position':[6,3.5,3], 'outward':[1,0], 'width':1.0},
}
# Fixed roof equipment and furniture. Their picking volumes come from the
# actual parts; these cells are never public paths or stackable roof.
RESERVATIONS = [
    [4,3,4,5,4,5],  # the kitchen stack on the roof stairhead's cap
    [0,0,1,6,1,2], [0,0,2,6,1,3], # fixed dining furniture, never public paths
    [6,1,1,7,6,2], # side tables and chairs
]
# Walking clearance above a deck or floor, below the beams of the deck one
# layer above (their underside is 0.77 over the floor below).
HEADROOM = .72

def source(point):
    return tuple(v-o for v,o in zip(point,ORIGIN,strict=True))
