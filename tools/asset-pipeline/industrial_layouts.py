"""Explicit game-grid registration for the reviewed artwork. No bounds fitting.

All points use artwork XYZ (Z up); origins are authored translations, not scales.
Routes enumerate safe lanes, not every empty-looking space in a bounding box.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def layout(origin, size, entrance, idle, *, deck_mode):
    if deck_mode not in ('BuiltInWalkways','PlayerPlacedPaths','None'):raise ValueError('Unknown authored deck mode '+str(deck_mode))
    return dict(origin=origin,size=size,baseZ=0,entrance=entrance,idle=idle,nodes=[],edges=[],ports=[],deckMode=deck_mode)

def node(d,cell,point):
    old=[n for n in d['nodes'] if n['cell']==list(cell)]
    if old:
        assert old[0]['point']==list(point), (cell,old,point)
    else:d['nodes'].append(dict(cell=list(cell),point=list(point)))

def edge(d,a,b):
    assert a!=b
    d['edges'].append([list(a),list(b)])

def lane(d,cells,points):
    assert len(cells)==len(points)
    for c,p in zip(cells,points):node(d,c,p)
    for a,b in zip(cells,cells[1:]):edge(d,a,b)

def grid_lane(d,cells):
    """Author a flat lane at native cell centers; artwork must clear this lane."""
    lane(d,cells,[(x+.5-d['origin'][0],y+.5-d['origin'][1],z) for x,y,z in cells])

def ground_door(d,position,outward):
    """Native grid door contract checked by industrial_building_content.mjs:
    centred on a tile, whole layer, face within 0.15 of its tile edge; the
    doorstep is the cell behind the face and the entrance the cell in front."""
    d['door']=dict(position=list(position),outward=list(outward))

def port(d,ident,inside,outside,run):
    assert list(inside) in [n['cell'] for n in d['nodes']]
    approach=next(n['point'].copy() for n in d['nodes'] if n['cell']==list(inside))
    tangent=1 if inside[0]!=outside[0] else 0
    approach[tangent]=inside[tangent]+.5-d['origin'][tangent]
    d['ports'].append(dict(id=ident,inside=list(inside),outside=list(outside),run=run,approach=approach))

def decorative_port(d,ident,inside,outside,run):
    """Rail visibility binding, independent of suggested paths or building roads."""
    if outside[2]!=inside[2] or abs(outside[0]-inside[0])+abs(outside[1]-inside[1])!=1:
        raise ValueError('Decorative rail opening requires adjacent cells at one level')
    if any(p['id']==ident for p in d['ports']):raise ValueError('Duplicate decorative rail '+ident)
    approach=[inside[0]+.5-d['origin'][0],inside[1]+.5-d['origin'][1],inside[2]-d['origin'][2]]
    d['ports'].append(dict(id=ident,inside=list(inside),outside=list(outside),run=run,approach=approach))

# User decision 2026-10-21: the crusher, kiln, mixer and quarries have no
# walkable decks, balconies or railed walkways. Registration has no lanes,
# edges or rail ports (deck mode 'None'); beavers use only the ground door.
# Each door is centred on a tile and its idle slot stands 0.08 in front of
# the door face.

# 2026-10-22: every footprint ends at the building's walls (front, sides and
# back); no apron, yard or decoration occupies tiles beyond them, and each
# door's entrance is the open cell in front of the footprint edge.

# Crusher artwork = native grid + (1,2): the walls are artwork x 1..5, y 2..6.
C=layout([-1,-2,0],[4,4,5],[1,-1,0],[[2.50,2.02,0]],deck_mode='None')
ground_door(C,(1.50,.10,0),(0,-1))

# Kiln artwork = native grid - (0,1). Compact 5x3x4 (2026-10-30): the old
# 7x5x6 registration's origin, entrance and door are kept.
K=layout([0,1,0],[5,3,4],[3,-1,0],[[3.50,-.94,0]],deck_mode='None')
ground_door(K,(3.50,.14,0),(0,-1))

# Quarry artwork = native grid + (0,1). The workshop and control-room doors on
# the stone plinth are facade details; only the ground cabin door is used.
Q=layout([0,-1,0],[11,7,9],[1,-1,0],[[1.50,1.06,0]],deck_mode='None')
ground_door(Q,(1.50,.14,0),(0,-1))

# Native entrance = the path cell in front of the door (vanilla convention);
# the door cell (1,0,0) is the occupied doorstep.
# Compact 4x3x3 (2026-10-30): the old 7x5x7 origin, entrance and door kept.
M=layout([0,0,0],[4,3,3],[1,-1,0],[[1.50,.04,0]],deck_mode='None')
ground_door(M,(1.50,.12,0),(0,-1))

LAYOUTS={'StoneCrusher':C,'CementKiln':K,'MineralQuarry':Q,'ConcreteMixer':M}

if __name__=='__main__':
    target=ROOT/'tools/industrial-layouts.json'
    target.write_text(json.dumps(LAYOUTS,indent=2)+'\n')
    print(target)
