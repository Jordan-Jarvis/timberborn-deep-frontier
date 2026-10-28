"""Hospital: two long ward wings, central pavilion and a rear roof garden.

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
"""
ORIGIN=[-1,-2,0]
ROOMS={
    'WestWardLower':[0,1,0,4,8,2], 'WestWardUpper':[0,1,2,4,8,4],
    'EastWardLower':[8,1,0,12,8,2], 'EastWardUpper':[8,1,2,12,8,4],
    'CentralLower':[4,0,0,8,8,2], 'CentralMiddle':[4,0,2,8,8,4],
    'CentralUpper':[4,0,4,8,8,6], 'RoofStairhead':[6,4,6,7,5,8],
}
EXTERIOR_WALLS={
    'WestWardLower':{'front':[(0,4)],'back':[(0,4)],'left':[(1,8)],'right':[]},
    'WestWardUpper':{'front':[(0,4)],'back':[(0,4)],'left':[(1,8)],'right':[]},
    'EastWardLower':{'front':[(8,12)],'back':[(8,12)],'left':[],'right':[(1,8)]},
    'EastWardUpper':{'front':[(8,12)],'back':[(8,12)],'left':[],'right':[(1,8)]},
    'CentralLower':{'front':[(4,8)],'back':[(4,8)],'left':[(0,1)],'right':[(0,1)]},
    'CentralMiddle':{'front':[(4,8)],'back':[(4,8)],'left':[(0,1)],'right':[(0,1)]},
    'CentralUpper':{'front':[(4,8)],'back':[(4,8)],'left':[(0,8)],'right':[(0,8)]},
    'RoofStairhead':{'front':[(6,7)],'back':[(6,7)],'left':[(4,5)],'right':[(4,5)]},
}
PLATFORMS={
    'WestFront':[0,0,0,4,1,2], 'WestRear':[0,8,0,4,9,2],
    'EastFront':[8,0,0,12,1,2], 'EastRear':[8,8,0,12,9,2],
    'RearConnector':[4,8,0,8,9,2],
    'UpperRear':[3,8,2,9,9,4], 'RoofGarden':[4,4,4,8,8,6],
}
# Outer balcony corners stand on short posts; the ward walls carry the rest.
SUPPORTS={
    'WestFront':[([0,0],[-1,-1],0)],
    'WestRear':[([0,8],[-1,1],0),([1,8],[1,1],0)],
    'EastFront':[([11,0],[1,-1],0)],
    'EastRear':[([10,8],[1,1],0),([11,8],[1,1],0)],
    'RearConnector':[([5,8],[1,1],0),([7,8],[1,1],0)],
    'UpperRear':[([3,8],[-1,1],2),([6,8],[1,1],2),([8,8],[1,1],2)],
    'RoofGarden':[],
}
DOORS={
    'GroundDoor':{'position':[6.5,0,0],'outward':[0,-1],'width':1.0},
    'WestWardDoor':{'position':[2.5,1,2],'outward':[0,-1],'width':1.0},
    'EastWardDoor':{'position':[9.5,1,2],'outward':[0,-1],'width':1.0},
    'RearDeckDoor':{'position':[6.5,8,2],'outward':[0,1],'width':1.0},
    'RearWardDoor':{'position':[6.5,8,4],'outward':[0,1],'width':1.0},
    'RoofTerraceDoor':{'position':[6.5,5,6],'outward':[0,1],'width':1.0},
}
RESERVATIONS=[
    [0,1,4,4,8,5],[1,1,5,3,8,6],
    [8,1,4,12,8,5],[9,1,5,11,8,6],
    [4,0,6,8,4,7],[4,1,7,8,3,8],
    [1,6,4,2,7,7],[9,6,4,10,7,7],
    [6,4,8,7,5,9],
]

def source(point):
    return tuple(v-o for v,o in zip(point,ORIGIN,strict=True))
