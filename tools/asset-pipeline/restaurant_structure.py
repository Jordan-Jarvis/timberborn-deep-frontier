"""Explicit restaurant structural edges in native XYZ; upper bounds exclusive.

2026-10-22 (user): no forced decoration beyond the walls. The ground service
counters, their awnings and the barrel under the dining balcony are gone, and
the empty first row and column left the footprint (10x8 -> 9x7): native x and
y are 1 less, ORIGIN -1, artwork unchanged. The dining balconies stay as part
of the building; the ground under them is open between their posts.

This is the authoring contract for meshes, occupied cells and picking volumes.
Decorative roofs, lanterns and furniture retain their independent dimensions.
"""
# y is the double just above -0.85: with -0.85 itself no source coordinate
# sums exactly to the native rail boundary y=4 (walkway_geometry.run_grid
# needs exact cell cuts). The 1e-16 artwork offset is immaterial.
ORIGIN = [-.8, -.8499999999999999, 0]
PLATFORMS = {
    'EntranceVestibuleCap': [0,2,0,1,3,2],
    'DiningFront': [0,0,0,6,2,2],
    'DiningSideFront': [6,1,0,7,2,2],
    'DiningSide': [5,2,0,7,7,2],
    'DiningRear': [1,5,0,5,7,2],
    'UpperDiningFront': [0,0,2,6,2,4],
    'UpperDiningSideFront': [6,1,2,7,2,4],
    'UpperDiningSide': [5,2,2,7,7,4],
    'UpperDiningRear': [1,5,2,5,7,4],
    'RoofTerraceInner': [5,2,4,7,5,6],
    'RoofTerraceOuter': [7,2,5,9,5,6],
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
    'UpperDiningFront': [([0,0],[-1,-1],2),([3,0],[1,-1],2),([5,0],[1,-1],2)],
    'UpperDiningSideFront': [([6,1],[1,-1],2)],
    'UpperDiningSide': [([6,3],[1,1],2),([6,6],[1,1],2)],
    'UpperDiningRear': [([1,6],[-1,1],2),([4,6],[1,1],2)],
    'RoofTerraceInner': [([6,2],[1,-1],4),([6,4],[1,1],4)],
    'RoofTerraceOuter': [],
}
ROOMS = {
    'GroundHall': [1,2,0,5,5,2],
    'MiddleHall': [1,2,2,5,5,4],
    'UpperHall': [1,2,4,5,5,6],
    'EntranceVestibule': [0,1,0,3,3,2],
    'Kitchen': [1,5,0,5,7,2],
    'RoofStairhead': [4,3,6,6,4,8],
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
    'MiddleDoor': {'position':[3.5,2,2], 'outward':[0,-1], 'width':1.0},
    'UpperDoor': {'position':[3.5,2,4], 'outward':[0,-1], 'width':1.0},
    'RoofTerraceDoor': {'position':[6,3.5,6], 'outward':[1,0], 'width':1.0},
}
# Roof silhouettes/equipment are intentionally authored separately from rooms.
# Their picking volumes are generated from the actual roof and equipment parts.
RESERVATIONS = [
    [0,1,6,6,5,7], [1,2,7,5,4,8], [2,2,8,4,4,9],
    [4,4,6,5,5,9], [1,2,6,2,4,9],  # two stacks above the enclosed rooms
    [0,0,2,6,1,3], [0,0,4,6,1,5], # fixed dining furniture, never public paths
    [6,1,2,7,6,3], # side tables and chairs
]

def source(point):
    return tuple(v-o for v,o in zip(point,ORIGIN,strict=True))
