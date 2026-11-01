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

Second shrink pass (2026-11-01; a YouTuber called it "massive"; user: "shrink
the buildings down even more"): 9x7x5 -> 6x5x3, same origin, ground door and
Entrance. Two one-layer storeys: the vestibule and a 5x3 ground hall whose
east end is the kitchen (bake oven in its back wall) at 0; the 3x3 dining room at 1 with the front dining balcony (three
tables) and a side balcony over the kitchen (one table); at 2 open flat roof
decks: the roof over the front balcony (two open-air tables), the main roof
and the roof over the side balcony (one table), with a one-layer roof
stairhead. The upper hall, the rear and outer side decks and the 3x3 roof
terrace are gone. Seven tables and fourteen seats as before. Height 5 -> 3.

This is the authoring contract for meshes, occupied cells and picking volumes.
Decorative trim, lanterns and furniture retain their independent dimensions.
"""
# y is the double just above -0.85: with -0.85 itself no source coordinate
# sums exactly to the native rail boundary y=4 (walkway_geometry.run_grid
# needs exact cell cuts). The 1e-16 artwork offset is immaterial.
ORIGIN = [-.8, -.8499999999999999, 0]
SIZE = [6, 5, 3]
PLATFORMS = {
    'EntranceVestibuleCap': [0,2,0,1,3,1],
    'DiningFront': [0,0,0,6,2,1],
    # Over the kitchen end of the ground hall.
    'DiningSide': [4,2,0,6,5,1],
    'UpperDiningFront': [0,0,1,6,2,2],
    'UpperDiningSide': [4,2,1,6,5,2],
    # The flat main roof over the dining room: a cast slab with timber
    # decking, one level with the open roof decks beside it.
    'MainRoof': [1,2,1,4,5,2],
}
# Explicit short posts: (native occupied tile, corner signs, bottom level).
# Main rooms and shared beams carry the inner deck edges; the kitchen walls
# carry the side balcony.
SUPPORTS = {
    'EntranceVestibuleCap': [],
    'DiningFront': [([0,0],[-1,-1],0),([3,0],[1,-1],0),([5,0],[1,-1],0)],
    'DiningSide': [],
    'UpperDiningFront': [([0,0],[-1,-1],1),([3,0],[1,-1],1),([5,0],[1,-1],1)],
    'UpperDiningSide': [([5,2],[1,-1],1),([5,4],[1,1],1)],
    'MainRoof': [],
}
ROOMS = {
    # The kitchen is the hall's east end (x 4..6) under the side balcony.
    'GroundHall': [1,2,0,6,5,1],
    'MiddleHall': [1,2,1,4,5,2],
    'EntranceVestibule': [0,1,0,3,3,1],
    'RoofStairhead': [2,3,2,4,4,3],
}
# Render only exposed facades. Shared room partitions have no mesh, posts or
# trim. These exact authored spans are independent of native room occupation.
EXTERIOR_WALLS = {
    'GroundHall': {'front':[(3,6)],'back':[(1,6)],'left':[(3,5)],'right':[(2,5)]},
    'MiddleHall': {'front':[(1,4)],'back':[(1,4)],'left':[(2,5)],'right':[(2,5)]},
    'EntranceVestibule': {'front':[(0,3)],'back':[(0,1)],'left':[(1,3)],'right':[(1,2)]},
}
DOORS = {
    'GroundDoor': {'position':[1.5,1,0], 'outward':[0,-1], 'width':1.0},
    # Centre tile of the 3-tile dining room front (2026-11-01; was x 3.5).
    'MiddleDoor': {'position':[2.5,2,1], 'outward':[0,-1], 'width':1.0},
    'RoofTerraceDoor': {'position':[4,3.5,2], 'outward':[1,0], 'width':1.0},
}
# Fixed furniture. Their picking volumes come from the actual parts; these
# cells are never public paths or stackable roof. The upper front furniture
# row ends at x 5: its last cell (5,0,2) holds no furniture. The side tables
# stand on x 5, y 2..3 at layers 1 and 2.
RESERVATIONS = [
    [0,0,1,6,1,2], [0,0,2,5,1,3], # fixed dining furniture, never public paths
    [5,2,1,6,4,2], [5,2,2,6,4,3], # side tables and chairs
]
# Walking clearance above a deck or floor, below the beams of the deck one
# layer above (their underside is 0.77 over the floor below).
HEADROOM = .72
DECK_BEAM_UNDERSIDE = .77
# Dining (2026-10-31, user: "the resturaunt chairs and tables are a tad too tall,
# and beavers heads are clipping the ceiling when they dine"). The native adult
# beaver playing the Sitting slot animation reaches 0.51 above its slot (highest
# vertex over the 149-frame BeaverAdult_sitting loop, measured locally from the
# installed game's BeaverAdult.Model; the same mesh for both factions). With the
# slot on a 0.3375 seat its head stood at 0.8475, above the 0.77 deck beams over
# the lower dining balcony. Chairs and tables drop 0.1375 together: the seat
# surface (and slot) is 0.20 over the deck, as the vanilla RooftopTerrace seat,
# the head 0.71, 0.06 under the beams. Plan positions are unchanged.
SEATED_HEAD = .51
TABLE_DROP = .1375

def source(point):
    return tuple(v-o for v,o in zip(point,ORIGIN,strict=True))
