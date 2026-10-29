"""DeepWell: powered boost rig that stands over a map water source (no workers).

HERO: a slim tapered steel drilling derrick hanging over the water source,
crowned by a crown block and beacon, driven from a riveted engine house.
ROOF: teal plank lean-to over the engine house.

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

IDENT = 'DeepWell'
FOOTPRINT = (1, 2)
HEIGHT = 5
FRAME_END = 121
HERO = 'Slim tapered steel drilling derrick hanging over the water source, crowned by a crown block and beacon.'

# The game cell over the water source (deep_well_content.mjs reads it).
DRILL = {'cell': [0, 1, 0]}

DOOR_X = .5
HOUSE = (.04, .14, .96, .96)       # engine house walls (x0, y0, x1, y1)
FLOOR = 1.2                        # plinth top = drill floor
WELL = (.5, 1.5)                   # wellhead / kelly axis
BASE = (.1, .9, 1.1, 1.9)          # derrick legs at the ground (x0, x1, y0, y1)
TOP = (.34, .66, 1.34, 1.66)       # derrick legs at the crown deck
ZT = 4.5                           # crown deck


def frame_at(z):
    t = z / ZT
    return tuple(BASE[i] + (TOP[i] - BASE[i]) * t for i in range(4))


def engine_house(g, parts):
    x0, y0, x1, y1 = HOUSE
    # The portal's wall insert spans the whole tile at y0; the plinth stands
    # 2 cm behind it so their faces never share a plane.
    top = P.plinth(g, x0, y0 + .02, x1, y1, FLOOR, door=(DOOR_X, .62, 1.0), pilasters=False)
    building_portal(g, DOOR_X, y0 - .12, 0)
    g.doorways.append({'id': 'Entrance', 'position': [DOOR_X, y0, 0], 'outward': [0, -1]})
    # Riveted upper storey on the plinth.
    eave = 2.1
    C.framed_block(g, x0 + .04, y0 + .04, x1 - .04, y1 - .04, top + .002, eave, infill=FORGED, frame=IRON, pitch=1.0,
                   faces=('front', 'left', 'right'))
    atlas_window(g, DOOR_X, y0 + .04, 1.68, .26, 'front', 'slit')
    for x, face in ((x0 + .04, 'left'), (x1 - .04, 'right')):
        atlas_window(g, x, .55, 1.68, .26, face, 'slit')
    # Hazard band under the eave on the front.
    n = 5
    w = (x1 - x0 - .2) / n
    for i in range(n):
        a = x0 + .1 + i * w
        blk(g, a, y0 + .04 - .055, 1.96, a + w, y0 + .04 - .015, 2.02, ORANGE if i % 2 == 0 else IRON)
    lean_to(g, x0 + .04, x1 - .04, y0 + .04, y1 - .04, eave + .02, eave + .32, low_side='front', overhang=.07, seed=7)
    # Drawworks on the back eave: steel cradle, drum and its motor.
    dz = 2.6
    dy = .84
    for x in (.2, .8):
        blk(g, x - .04, dy - .1, eave + .33, x + .04, dy + .1, dz - .02, IRON)
    blk(g, .13, dy - .12, eave + .3, .87, dy + .12, eave + .36, IRON)
    drum = Geometry('DeepWell.Drawworks', (.5, dy, dz))
    P.lathe(drum, (.5, dy, dz), [(.15, -.25), (.15, -.21), (.1, -.21), (.1, .21), (.15, .21), (.15, .25)], PAINTED,
            axis='X', segments=12)
    for k in range(6):
        a = k * math.pi / 3
        drum.box((.5, dy + math.cos(a) * .102, dz + math.sin(a) * .102), (.4, .03, .03), BRASS)
    parts.append((drum, 'SPIN_X', 2))
    g.cylinder((.5, dy, dz), .03, .62, IRON, 'X', 8)
    P.motor(g, (.5, dy - .36, eave + .52), .1, .3, axis='X')


def derrick(g):
    corners = lambda z: (lambda f: [(f[0], f[2]), (f[1], f[2]), (f[1], f[3]), (f[0], f[3])])(frame_at(z))
    # Footing pads round the source and the four legs.
    for (x, y), (xt, yt) in zip(corners(0), corners(ZT)):
        blk(g, x - .08, y - .08, -.03, x + .08, y + .08, .1, CONCRETE)
        g.beam((x, y, .08), (xt, yt, ZT - .02), .07, mat=IRON)
    levels = [FLOOR, 2.3, 3.4, ZT - .08]
    for k, z in enumerate(levels):
        fx0, fx1, fy0, fy1 = frame_at(z)
        for y in (fy0, fy1):
            blk(g, fx0 + .04, y - .025, z - .025, fx1 - .04, y + .025, z + .025, IRON)
        for x in (fx0, fx1):
            blk(g, x - .025, fy0 + .04, z + .005, x + .025, fy1 - .04, z + .055, IRON)
    faces = {
        'front': (lambda f: ((f[0], f[2]), (f[1], f[2])), (0, -1)),
        'right': (lambda f: ((f[1], f[2]), (f[1], f[3])), (1, 0)),
        'back': (lambda f: ((f[1], f[3]), (f[0], f[3])), (0, 1)),
        'left': (lambda f: ((f[0], f[3]), (f[0], f[2])), (-1, 0)),
    }
    spans = [(.12, FLOOR)] + list(zip(levels, levels[1:]))
    for fi, (face, (ends, nrm)) in enumerate(faces.items()):
        for k, (za, zb) in enumerate(spans):
            if face == 'front' and k == 1:
                continue   # cable and kelly side kept open above the floor
            off = .05 if k % 2 == 0 else .062
            (pa, qa), (pb, qb) = ends(frame_at(za)), ends(frame_at(zb))
            if (k + fi) % 2:
                a, b = (pa[0] + nrm[0] * off, pa[1] + nrm[1] * off, za + .04), (qb[0] + nrm[0] * off, qb[1] + nrm[1] * off, zb - .04)
            else:
                a, b = (qa[0] + nrm[0] * off, qa[1] + nrm[1] * off, za + .04), (pb[0] + nrm[0] * off, pb[1] + nrm[1] * off, zb - .04)
            g.beam(a, b, .035, .04, IRON)


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
    kelly.box((wx, wy, (FLOOR + .2 + 3.25) / 2), (.07, .07, 3.25 - FLOOR - .2), IRON)
    kelly.box((wx, wy, FLOOR + .14), (.16, .16, .05), BRASS)
    P.lathe(kelly, (wx, wy, 3.25), [(.07, 0), (.07, .16), (.04, .22)], PAINTED, segments=8)
    parts.append((kelly, 'SPIN_Z', 2))
    # Travelling block and hook, the hoist line to the crown and the fast line
    # down to the drawworks drum.
    blk(g, wx - .09, wy - .06, 3.55, wx + .09, wy + .06, 3.9, PAINTED)
    blk(g, wx - .015, wy - .015, 3.47, wx + .015, wy + .015, 3.55, IRON)
    g.cylinder((wx, wy, 3.5), .05, .04, IRON, 'Y', 8)
    for dx in (-.05, .05):
        g.beam((wx + dx, wy, 3.9), (wx + dx, wy, ZT - .1), .016, mat=IRON)
    g.beam((.5, .9, 2.74), (.5, TOP[2] + .02, ZT - .14), .018, mat=IRON)


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


def monkey_board(g):
    """Derrickman's platform on the back of the derrick, a mud hose from the
    standpipe to the swivel. Nothing stands outside the 1-tile width, so
    Deep Wells on a line of 1x1 sources stand side by side."""
    z = 3.3
    fx0, fx1, fy0, fy1 = frame_at(z)
    y0, y1 = fy1 - .1, 1.95
    P.grating(g, fx0 + .02, y0, fx1 - .02, y1, z, along='Y')
    for x in (fx0 + .06, fx1 - .06):
        g.beam((x, fy1 + .02, z - .3), (x, y1 - .04, z - .09), .03, mat=IRON)
    P.rail(g, [(fx0 + .05, y0 + .05), (fx0 + .05, y1 - .04), (fx1 - .05, y1 - .04), (fx1 - .05, y0 + .05)], z, height=.45)
    # Standpipe up the right back leg and the mud hose loop to the swivel.
    sx, sy = .74, 1.72
    P.pipe(g, [(sx, sy, FLOOR + .02), (sx, sy, 2.6)], .03, flanges=False, segments=6)
    for a, b in (((sx, sy, 2.6), (.68, 1.64, 2.95)), ((.68, 1.64, 2.95), (.6, 1.56, 3.32)), ((.6, 1.56, 3.32), (WELL[0] + .05, WELL[1], 3.42))):
        g.beam(a, b, .045, mat=PAINTED)


def build(g, parts):
    engine_house(g, parts)
    derrick(g)
    drill_floor(g, parts)
    monkey_board(g)
    crown(g, parts)
