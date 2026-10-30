"""Explicit native-grid nursery structure; Z includes its submerged BaseZ layer.

2026-10-26 (user): compact early-game footprint. The perimeter docks around
the pens (LeftDock x=0, RearDock y=7, RightDock x=6..7 at y=4..7) and the
walkway column beside the headhouse are gone: 8x8 -> 7x7. Grid x moved by -1
(SOURCE_ORIGIN x 1.2 -> 0.2), so every kept part keeps its source position.
The front walkway (row 3) and the centre dock between the pens still reach
the pens from the headhouse side.

2026-10-30 compaction (user: "currently we have two layers between floors,
we should reduce it to one"; flat roofs): the headhouse is one layer tall
(native z 1..2) under a flat cast roof, and the pump canopy is one layer
under a flat roof too. The gabled roofs and the roof vent are gone. The 7x7
footprint, origin, BaseZ, door, pens, decks and rails are unchanged; the
height is 5 -> 3."""
ORIGIN=[.2,.75,0]
BASE_Z=1
SOURCE_ORIGIN=[.2,.75,1]
SIZE=[7,7,3]
ROOMS={'Headhouse':[0,1,1,4,3,2]}
PLATFORMS={
    'MainFrontApron':[0,0,0,5,1,1], 'MainApron':[0,1,0,5,4,1],
    'CentreDock':[2,4,0,3,7,1],
    'CanopyFrontApron':[5,0,0,7,1,1], 'CanopyBaseApron':[5,1,0,7,4,1],
}
SUPPORTS={name:[] for name in PLATFORMS}
# The six fixed-length short posts are replaced by AdaptiveSupportsSpec piles
# (tools/waterside_sites.json) that reach the bed at any depth up to six layers.
DOORS={'Door0':{'position':[1.5,1,1],'outward':[0,-1],'width':1.0}}
PENS=[[0,4,0,2,7,1],[3,4,0,5,7,1]]
RESERVATIONS=[
    *PENS,
    [4,1,1,7,3,2],  # one-layer pump canopy and its machinery
    [4,3,1,5,4,2], [6,3,1,7,4,2], # Retained rear canopy posts and pipe bend.
    # Bank-row header tank (the reservoir stock). The barrels and sacks that
    # reserved (3..4,0) and (7,0) went with the forced decoration (2026-10-22).
    [5,0,1,6,1,2],
]
DOOR_LINKS=[{'Interior':[1,1,1],'Exterior':[1,0,1]}]
SHAFT_PORTS=[
    {'Coordinates':{'X':0,'Y':1,'Z':1},'Directions':'Left, Bottom','ReverseRotation':False},
    {'Coordinates':{'X':2,'Y':2,'Z':1},'Directions':'Up','ReverseRotation':False},
    {'Coordinates':{'X':6,'Y':1,'Z':1},'Directions':'Right, Bottom','ReverseRotation':False},
]
BARREL_MOVE={'name':'NativeBarrel1','sourceDelta':[0,-.30,0]}
BANK_APRON_SURFACE={'nativeFloor':1,'terrainTop':1.01,'bottom':.894,'backingTop':1.016,'wearingTop':1.020}
# Only the deck edges that still face open water carry rails: the left end of
# the front walkway, the end of the centre dock and the canopy deck's rear
# edge beside its retained rear post.
RAIL_RUNS=[('NurseryLeft',(0,3,1),(0,4,1),1),
           ('NurseryBack',(2,7,1),(3,7,1),1),
           ('NurseryRight',(5,4,1),(6,4,1),1)]

def source(point):
    return tuple(v-o for v,o in zip(point,SOURCE_ORIGIN,strict=True))

# Gallery routes cover only the water-side deck platforms, whose boards stand
# within the civic gallery tolerance of native Z1. The y=0 bank row
# (MainFrontApron/CanopyFrontApron) is ground: its wearing top is
# BANK_APRON_SURFACE['wearingTop'] (Z1.020) to clear measured terrain (Z1.010),
# so its terrain clearance is checked by check_hatchery_ground.py and its
# floor/headroom by check_hatchery_candidate.py, not as a layer-0 deck gallery.
GALLERY_ROUTES=[[(0,3),(3,3)],[(2,3),(2,6)]]
for _route in GALLERY_ROUTES:
    for (_ax,_ay),(_bx,_by) in zip(_route,_route[1:]):
        if _ax!=_bx and _ay!=_by:raise ValueError('Hatchery gallery routes are axis-aligned cell runs')
        for _name in ('MainFrontApron','CanopyFrontApron'):
            _x0,_y0,_,_x1,_y1,_=PLATFORMS[_name]
            if min(_ax,_bx)<_x1 and max(_ax,_bx)>=_x0 and min(_ay,_by)<_y1 and max(_ay,_by)>=_y0:
                raise ValueError('Hatchery gallery route crosses raised bank apron '+_name)
ACCESS={'entrance':list(source(DOORS['Door0']['position'])),'balconyLayers':[0],
        'routes':[[list(source((x+.5,y+.5,1)))[:2] for x,y in route] for route in GALLERY_ROUTES],
        'stairBays':[],'headroom':1.09}
# Centre dock between the pens; the pen frames' beams sit at its long edges.
TERRACE={'scope':'Clear centre dock; supported native construction required',
         'bounds':[1.8,3.25,2.8,6.25],'layer':0,'clearArea':[1.9,3.4,2.6,6.1]}

def deck_cells():
    cells={(x,y,1) for b in PLATFORMS.values() for x in range(b[0],b[3]) for y in range(b[1],b[4])}
    for b in [*ROOMS.values(),*RESERVATIONS]:
        if b[2]<=1<b[5]:cells-={(x,y,1) for x in range(b[0],b[3]) for y in range(b[1],b[4])}
    return sorted(cells)
