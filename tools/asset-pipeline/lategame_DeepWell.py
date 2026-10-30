"""DeepWell: powered boost rig that stands over a map water source (no workers).

Compacted 2026-10-30 (light touch, outputs/compaction/BRIEF.md): 1x2x5 ->
1x2x4. The open lattice derrick is now plated on its left, right and back
faces (open at the front for the hoist line) and ends at layer 3 (crown 3.2,
was 4.5); the monkey board, its rail and the standpipe are gone. One layer
per floor: the drill floor and the engine house's concrete storey are one
layer (they were 1.2), the forged storey above is one layer, and the plank
lean-to is a flat roof carrying the drawworks. Footprint, door, DRILL cell
and animated parts unchanged.

HERO: a slim tapered plated drilling derrick hanging over the water source,
crowned by a crown block and beacon, driven from a riveted engine house.
ROOF: flat steel-capped roof on the engine house, carrying the drawworks.

Plan (1 x 2 tiles, the source under the back tile):
- front tile (the anchor, on ground or on a seep / badwater-source cell):
  concrete lower storey with the builders' and haulers' door on the front,
  riveted forged upper storey, lean-to roof, the drawworks drum on its back
  eave with its motor;
- back tile (the DRILL cell): the game block over the source is empty
  (deep_well_content.mjs makes it MatterBelow Any, Occupations None), so the
  derrick legs stand on four footing pads at the cell corners round the
  source and the wellhead stack sits on the source itself. The drill floor
  at the engine-house floor level carries the rotary table and the kelly; the
  derrick tapers to the crown block at layer 4.

Animated: kelly and rotary bushing (SPIN_Z), drawworks drum (SPIN_X), crown
beacon shutter (SPIN_Z). The DeepWell component plays them only while the
well is boosting.
No smoke or steam emitter (electric drive; nothing polluting).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, LAYER_GAP
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
from lategame_mining_parts import lean_to
from industrial_facades import building_portal
from native_window_atlas import atlas_window
from lategame_mining_parts import slab_quad

IDENT = 'DeepWell'
FOOTPRINT = (1, 2)
HEIGHT = 4
FRAME_END = 121
HERO = 'Slim tapered steel drilling derrick hanging over the water source, crowned by a crown block and beacon.'

# The game cell over the water source (deep_well_content.mjs reads it).
DRILL = {'cell': [0, 1, 0]}

DOOR_X = .5
HOUSE = (.04, .14, .96, .96)       # engine house walls (x0, y0, x1, y1)
FLOOR = 1.0                        # plinth top = drill floor (layer 1)
WELL = (.5, 1.5)                   # wellhead / kelly axis
BASE = (.1, .9, 1.1, 1.9)          # derrick legs at the ground (x0, x1, y0, y1)
TOP = (.34, .66, 1.34, 1.66)       # derrick legs at the crown deck
ZT = 3.2                           # crown deck


def frame_at(z):
    t = z / ZT
    return tuple(BASE[i] + (TOP[i] - BASE[i]) * t for i in range(4))


def engine_house(g, parts):
    x0, y0, x1, y1 = HOUSE
    # The portal's wall insert spans the whole tile at y0; the plinth stands
    # 2 cm behind it so their faces never share a plane.
    # One-layer concrete storey: two piers either side of the door and the
    # block behind its recess (the door is the storey's full height).
    yb = y0 + .02
    dl, dr = DOOR_X - .31, DOOR_X + .31
    blk(g, x0, yb, 0, dl, y1, FLOOR, CONCRETE)
    blk(g, dr, yb, 0, x1, y1, FLOOR, CONCRETE)
    blk(g, dl, yb + .25, 0, dr, y1, FLOOR, CONCRETE)
    blk(g, dl + .006, yb + .24, .006, dr - .006, yb + .25, FLOOR - .006, IRON)
    blk(g, x0 - .04, yb - .04, FLOOR - .08, x1 + .04, y1 + .04, FLOOR + .012, CONCRETE)
    top = FLOOR + .012
    building_portal(g, DOOR_X, y0 - .12, 0)
    g.doorways.append({'id': 'Entrance', 'position': [DOOR_X, y0, 0], 'outward': [0, -1]})
    # Riveted upper storey on the plinth.
    eave = 1.84
    C.framed_block(g, x0 + .04, y0 + .04, x1 - .04, y1 - .04, top + .002, eave, infill=FORGED, frame=IRON, pitch=1.0,
                   faces=('front', 'left', 'right'))
    atlas_window(g, DOOR_X, y0 + .04, 1.42, .22, 'front', 'slit')
    for x, face in ((x0 + .04, 'left'), (x1 - .04, 'right')):
        atlas_window(g, x, .55, 1.42, .22, face, 'slit')
    # Hazard band under the eave on the front.
    n = 5
    w = (x1 - x0 - .2) / n
    for i in range(n):
        a = x0 + .1 + i * w
        blk(g, a, y0 + .04 - .055, 1.1, a + w, y0 + .04 - .015, 1.16, ORANGE if i % 2 == 0 else IRON)
    blk(g, x0 - .01, y0 - .01, eave, x1 + .01, y1 + .01, eave + .1, IRON)
    roof = eave + .1
    # Drawworks on the roof: steel cradle, drum and its motor.
    dz = roof + .3
    dy = .7
    for x in (.2, .8):
        blk(g, x - .04, dy - .1, roof + .06, x + .04, dy + .1, dz - .02, IRON)
    blk(g, .13, dy - .12, roof, .87, dy + .12, roof + .06, IRON)
    drum = Geometry('DeepWell.Drawworks', (.5, dy, dz))
    P.lathe(drum, (.5, dy, dz), [(.15, -.25), (.15, -.21), (.1, -.21), (.1, .21), (.15, .21), (.15, .25)], PAINTED,
            axis='X', segments=12)
    for k in range(6):
        a = k * math.pi / 3
        drum.box((.5, dy + math.cos(a) * .102, dz + math.sin(a) * .102), (.4, .03, .03), BRASS)
    parts.append((drum, 'SPIN_X', 2))
    g.cylinder((.5, dy, dz), .03, .62, IRON, 'X', 8)
    P.motor(g, (.5, dy - .36, roof + .16), .1, .3, axis='X')


def derrick(g):
    corners = lambda z: (lambda f: [(f[0], f[2]), (f[1], f[2]), (f[1], f[3]), (f[0], f[3])])(frame_at(z))
    # Footing pads round the source and the four legs.
    for (x, y), (xt, yt) in zip(corners(0), corners(ZT)):
        blk(g, x - .08, y - .08, -.03, x + .08, y + .08, .1, CONCRETE)
        g.beam((x, y, .08), (xt, yt, ZT - .02), .07, mat=IRON)
    levels = [FLOOR, 2.1, ZT - .08]
    for k, z in enumerate(levels):
        fx0, fx1, fy0, fy1 = frame_at(z)
        for y in (fy0, fy1):
            blk(g, fx0 + .04, y - .025, z - .025, fx1 - .04, y + .025, z + .025, IRON)
        for x in (fx0, fx1):
            blk(g, x - .025, fy0 + .04, z + .005, x + .025, fy1 - .04, z + .055, IRON)
    # Riveted plating inside the legs on the left, right and back faces, from
    # the drill floor to the crown (the front stays open for the hoist line).
    za, zb = FLOOR + .06, ZT - .12
    fa, fb = frame_at(za), frame_at(zb)
    slope = (TOP[0] - BASE[0]) / ZT
    slab_quad(g, [(fa[0] + .04, fa[3] - .05, za), (fa[0] + .04, fa[2] + .05, za),
                  (fb[0] + .04, fb[2] + .05, zb), (fb[0] + .04, fb[3] - .05, zb)], (-1, 0, slope), .03, FORGED)
    slab_quad(g, [(fa[1] - .04, fa[2] + .05, za), (fa[1] - .04, fa[3] - .05, za),
                  (fb[1] - .04, fb[3] - .05, zb), (fb[1] - .04, fb[2] + .05, zb)], (1, 0, slope), .03, FORGED)
    slab_quad(g, [(fa[1] - .05, fa[3] - .04, za), (fa[0] + .05, fa[3] - .04, za),
                  (fb[0] + .05, fb[3] - .04, zb), (fb[1] - .05, fb[3] - .04, zb)], (0, 1, slope), .03, FORGED)


def drill_floor(g, parts):
    fx0, fx1, fy0, fy1 = frame_at(FLOOR)
    P.grating(g, fx0 + .03, fy0 + .03, fx1 - .03, fy1 - .03, FLOOR, along='X')
    P.rail(g, [(fx1 - .04, fy0 + .06), (fx1 - .04, fy1 - .04), (fx0 + .04, fy1 - .04), (fx0 + .04, fy0 + .06)], FLOOR)
    wx, wy = WELL
    # Wellhead stack on the source below the floor: base flange, spool, rams.
    P.lathe(g, (wx, wy, 0), [(.2, -.02), (.2, .08), (.12, .1), (.12, .36), (.17, .38), (.17, .58), (.11, .6),
                              (.11, FLOOR - .1)], PAINTED, segments=12)
    P.hoop(g, (wx, wy, .48), .19, .04, .05, BRASS, segments=12)
    for side in (-1, 1):
        P.tube(g, (wx + side * .12, wy, .22), (wx + side * .3, wy, .22), .045, IRON, segments=8)
        g.cylinder((wx + side * .3, wy, .22), .06, .05, BRASS, 'X', 8)
        K.valve_wheel(g, wx + side * .24, wy, .36, face='left' if side < 0 else 'right', r=.07)
    # Rotary table on the floor.
    P.lathe(g, (wx, wy, FLOOR - .02), [(.2, 0), (.2, .1), (.12, .12), (.12, .14)], PAINTED, segments=12)
    K.band(g, (wx, wy, 0), .2, FLOOR + .04, .03, ORANGE, segments=12)
    kelly = Geometry('DeepWell.Kelly', (wx, wy, FLOOR + .2))
    P.lathe(kelly, (wx, wy, FLOOR + .11), [(.1, 0), (.1, .08), (.06, .1)], IRON, segments=8)
    kelly.box((wx, wy, (FLOOR + .2 + 2.3) / 2), (.07, .07, 2.3 - FLOOR - .2), IRON)
    kelly.box((wx, wy, FLOOR + .14), (.16, .16, .05), BRASS)
    P.lathe(kelly, (wx, wy, 2.3), [(.07, 0), (.07, .14), (.04, .2)], PAINTED, segments=8)
    parts.append((kelly, 'SPIN_Z', 2))
    # Travelling block and hook, the hoist line to the crown and the fast line
    # down to the drawworks drum.
    blk(g, wx - .09, wy - .06, 2.55, wx + .09, wy + .06, 2.82, PAINTED)
    blk(g, wx - .015, wy - .015, 2.5, wx + .015, wy + .015, 2.55, IRON)
    g.cylinder((wx, wy, 2.52), .05, .04, IRON, 'Y', 8)
    for dx in (-.05, .05):
        g.beam((wx + dx, wy, 2.82), (wx + dx, wy, ZT - .1), .016, mat=IRON)
    g.beam((.5, .82, 2.32), (.5, TOP[2] + .02, ZT - .14), .018, mat=IRON)


def crown(g, parts):
    fx0, fx1, fy0, fy1 = frame_at(ZT)
    blk(g, fx0 - .04, fy0 - .04, ZT - .06, fx1 + .04, fy1 + .04, ZT + .04, IRON)
    for y in (fy0 - .045, fy1 + .045):
        blk(g, fx0 - .02, min(y, y + .01), ZT - .03, fx1 + .02, max(y, y + .01), ZT + .01, ORANGE)
    g.cylinder((.5, WELL[1], ZT + .1), .09, .22, PAINTED, 'X', 10)
    for x in (.37, .63):
        blk(g, x - .02, WELL[1] - .07, ZT + .04, x + .02, WELL[1] + .07, ZT + .2, IRON)
    bx, by, bz = .5, WELL[1] + .12, ZT + .16
    blk(g, bx - .07, by - .07, ZT + .04, bx + .07, by + .07, bz, IRON)
    pivot = K.beacon(g, bx, by, bz)
    parts.append((K.beacon_shutter(*pivot, 'DeepWell.Beacon'), 'SPIN_Z', 1))


def build(g, parts):
    engine_house(g, parts)
    derrick(g)
    drill_floor(g, parts)
    crown(g, parts)
