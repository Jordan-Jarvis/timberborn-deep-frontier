"""Hospital: central pavilion with rear decks and a roof garden (the two ward
wings were removed on 2026-10-30).

Native grid XYZ, exclusive upper bounds. Separate roof silhouettes.

2026-10-21 (user): the side (gable) balconies are removed; only the front and
back balconies remain. The footprint loses its two side deck columns, so it is
12 tiles wide. Artwork keeps its source coordinates: source = native - ORIGIN,
i.e. the old native frame, so ORIGIN is [-1,0,0]. Each ward gains a layer-2
door onto its own front balcony, and the central pavilion a layer-2 door onto
the back balcony, so every deck keeps a building connection.

2026-10-22 (user): no forced decoration or apron beyond the walls. The two
front rows held only planters and the entrance canopy, so the footprint ends
at the pavilion's front wall (12x11 -> 12x9): native y is 2 less, ORIGIN y -2,
and artwork keeps its source coordinates. The ground door is on the footprint
edge with its doorstep outside. The canopy is a vanilla-sized overhang now,
so its layer-1 reservation is gone.

2026-10-30 (user, compaction pass): "keep it as it is, but remove the right
and left wings, just keeping the center." The central pavilion keeps its
storeys, roof, materials and doors exactly; the two ward wings, their front
balconies, rear balcony ends, ward roofs, flues and ward doors are gone. The
footprint is the pavilion with its rear decks (12x9 -> 4x9, height 9): native
x is 4 less, ORIGIN x -4, and artwork keeps its source coordinates.

2026-11-01 (user, second shrink pass: "we can also shrink the hospital
more", heights down a lot, one layer per floor): 4x9x9 -> 4x4x4, inside the
old footprint with the same origin, ground door and entrance cell. Two
one-layer storeys (wards at layers 0 and 1) carry a front-facing gabled roof
over the front half (the medical cross in its gable) and an open concrete
roof garden at layer 2 over the back half, reached through a one-layer
stairhead on the back-right corner. The rear decks and their doors (layers
2 and 4) went with the old back half.
"""
ORIGIN=[-5,-2,0]
SIZE=[4,4,4]
ROOMS={
    'CentralLower':[0,0,0,4,4,1], 'CentralUpper':[0,0,1,4,4,2],
    'RoofStairhead':[3,3,2,4,4,3],
}
EXTERIOR_WALLS={
    'CentralLower':{'front':[(0,4)],'back':[(0,4)],'left':[(0,4)],'right':[(0,4)]},
    'CentralUpper':{'front':[(0,4)],'back':[(0,4)],'left':[(0,4)],'right':[(0,4)]},
    'RoofStairhead':{'front':[(3,4)],'back':[(3,4)],'left':[(3,4)],'right':[(3,4)]},
}
# The roof garden slab tops the upper storey's back half (deck at layer 2).
PLATFORMS={'RoofGarden':[0,2,0,4,4,2]}
SUPPORTS={'RoofGarden':[]}
DOORS={
    'GroundDoor':{'position':[2.5,0,0],'outward':[0,-1],'width':1.0},
    'RoofTerraceDoor':{'position':[3.5,3,2],'outward':[0,-1],'width':1.0},
}
# Front gabled roof (eave 2.15, ridge 3.70 over native x 2) and the
# stairhead's gabled cap.
RESERVATIONS=[
    [0,0,2,4,2,3],[1,0,3,3,2,4],
    [3,3,3,4,4,4],
]

def source(point):
    return tuple(v-o for v,o in zip(point,ORIGIN,strict=True))
