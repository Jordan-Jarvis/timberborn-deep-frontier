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
"""
ORIGIN=[-5,-2,0]
SIZE=[4,9,9]
ROOMS={
    'CentralLower':[0,0,0,4,8,2], 'CentralMiddle':[0,0,2,4,8,4],
    'CentralUpper':[0,0,4,4,8,6], 'RoofStairhead':[2,4,6,3,5,8],
}
# The pavilion's side walls were joined to the wards below layer 4; with the
# wings gone every pavilion wall is exterior.
EXTERIOR_WALLS={
    'CentralLower':{'front':[(0,4)],'back':[(0,4)],'left':[(0,8)],'right':[(0,8)]},
    'CentralMiddle':{'front':[(0,4)],'back':[(0,4)],'left':[(0,8)],'right':[(0,8)]},
    'CentralUpper':{'front':[(0,4)],'back':[(0,4)],'left':[(0,8)],'right':[(0,8)]},
    'RoofStairhead':{'front':[(2,3)],'back':[(2,3)],'left':[(4,5)],'right':[(4,5)]},
}
PLATFORMS={
    'RearConnector':[0,8,0,4,9,2],
    'UpperRear':[0,8,2,4,9,4], 'RoofGarden':[0,4,4,4,8,6],
}
# Outer balcony corners stand on short posts; the pavilion's back wall
# carries the rest. The rear decks end at the pavilion's corners now.
SUPPORTS={
    'RearConnector':[([0,8],[-1,1],0),([1,8],[1,1],0),([3,8],[1,1],0)],
    'UpperRear':[([0,8],[-1,1],2),([2,8],[1,1],2),([3,8],[1,1],2)],
    'RoofGarden':[],
}
DOORS={
    'GroundDoor':{'position':[2.5,0,0],'outward':[0,-1],'width':1.0},
    'RearDeckDoor':{'position':[2.5,8,2],'outward':[0,1],'width':1.0},
    'RearWardDoor':{'position':[2.5,8,4],'outward':[0,1],'width':1.0},
    'RoofTerraceDoor':{'position':[2.5,5,6],'outward':[0,1],'width':1.0},
}
RESERVATIONS=[
    [0,0,6,4,4,7],[0,1,7,4,3,8],
    [2,4,8,3,5,9],
]

def source(point):
    return tuple(v-o for v,o in zip(point,ORIGIN,strict=True))
