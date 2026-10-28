"""PrecisionMachineWorks: precision parts and components (6 workers, 2200 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the loose yard stock and barrels.

HERO: a long north-light sawtooth machine hall with an open belt bay, an
      overhead travelling crane over its yard and a 13-layer square brick
      chimney bound with iron bands.
ROOF: a north-light sawtooth roof (three teal plank teeth with glazed north
      faces) on the tall machine shop, a lean-to on the forge, a flat
      parapeted roof on the gate office.

Plan (11 x 9 tiles): the two-storey gate office with the door front-right,
carrying the works' riveted compressed-air receiver on a braced steel frame;
the machine shop behind with a big open belt bay in its front wall showing
the line shaft, pulleys, belts and three lathes; the forge lean-to and its
tall square brick chimney on the left; an overhead travelling crane over the
lathe yard and steam hammer on the right.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, CYAN, GLOW, LAYER_GAP
import lategame_industry_parts as P
from industrial_facades import building_portal
from architectural_windows import window

IDENT = 'PrecisionMachineWorks'
FOOTPRINT = (11, 9)
HEIGHT = 14
FRAME_END = 121
HERO = ('Long north-light sawtooth machine hall under an overhead travelling crane, with a 13-layer square '
        'brick chimney bound in iron and a compressed-air receiver on a steel frame.')

SHOP = (1.1, 2.1, 6.9, 8.9)   # plinth (walls + .1) on tiles 1..7 x 2..9
SHOP_EAVE = 5.2
BAY = (2.05, 6.25, 4.25)      # open belt bay: x0, x1, head height
BAY_BACK = 3.85
OFFICE = (7.0, .15, 10.0, 1.95)  # gate office: front (door) face .15 off the edge; back .05 short of y = 2
DOOR_X = 8.5


def frame(g, axis, plane, start, end, bottom, top, out, **kw):
    K.frame_wall(g, axis, plane, start, end, bottom, top, outward=out, **kw)


# ---------------------------------------------------------------- machine shop

def sawtooth(g, x0, y0, x1, y1, base, teeth=3, rise=1.1):
    d = (y1 - y0) / teeth
    for i in range(teeth):
        ya, yb = y0 + i * d, y0 + (i + 1) * d
        last = i == teeth - 1
        wall_back = y1 + .04 if last else yb
        wall_front = y1 - .05 if last else yb - .06
        wc = (wall_back + wall_front) / 2
        P.plank_slope(g, 'X', ya - (0 if i == 0 else .03), wc, base, base + rise, x0, x1,
                      overhang=.22 if i == 0 else .0, end_overhang=.16, plank=.32, fascia=i == 0)
        # Glazed north-light face.
        g.box(((x0 + x1) / 2, wc, base + rise / 2 + .01), (x1 - x0 + .06, wall_back - wall_front, rise + .06), FORGED)
        for k in range(6):
            x = x0 + .5 + k * (x1 - x0 - 1) / 5
            window(g, x, wall_back, base + rise / 2 + .02, .95, 'back', 'factory')
        g.box(((x0 + x1) / 2, wc, base + rise + .13), (x1 - x0 + .34, .16, .07), IRON)
        for plane, out in ((x0, -1), (x1, 1)):
            prof = [(ya + (.0 if i == 0 else -.02), base - .01), (wall_front, base - .01),
                    (wall_front, base + rise * (wall_front - ya) / (wc - ya + 1e-9) - .07)]
            P.end_prism(g, 'X', plane, out, prof, ORANGE)


def shop(g, parts):
    x0, y0, x1, y1 = SHOP
    top = P.plinth(g, x0 - .1, y0 - .1, x1 + .1, y1 + .1, 1.0)
    bottom, eave = top, SHOP_EAVE
    bx0, bx1, bz = BAY
    fw = dict(infill=FORGED, post=IRON, post_w=.16, window_style='factory', window_scale=.9)
    # Front wall in three pieces around the open belt bay.
    frame(g, 'X', y0, x0 - .05, bx0, bottom, eave + .03, -1, windows=[(1.6, 2.3), (1.6, 4.1)], bays=1, **fw)
    frame(g, 'X', y0, bx1, x1 + .05, bottom, eave + .03, -1, windows=[((bx1 + x1) / 2, 2.3), ((bx1 + x1) / 2, 4.1)],
          bays=1, **fw)
    # Riveted plate girder over the bay, plaster infill above it.
    g.box(((bx0 + bx1) / 2, y0, bz + .28), (bx1 - bx0 + .2, .26, .56), PAINTED)
    for k in range(12):
        x = bx0 + .2 + k * (bx1 - bx0 - .4) / 11
        for z in (bz + .08, bz + .48):
            K.stud(g, (x, y0 - .13 - .01, z), 'Y', .022)
    g.box(((bx0 + bx1) / 2, y0, (bz + .56 + eave + .03) / 2), (bx1 - bx0 - .16, .1, eave + .03 - bz - .56), ORANGE)
    g.box(((bx0 + bx1) / 2, y0 - .0975, eave - .04), (bx1 - bx0 - .16, .095, .11), IRON)
    for k in range(1, 4):
        x = bx0 + k * (bx1 - bx0) / 4
        g.box((x, y0 - .085, (bz + .56 + eave + .03) / 2), (.14, .07, eave + .03 - bz - .56), IRON)
    frame(g, 'X', y1, x0 - .05, x1 + .05, bottom, eave + .03, 1,
          windows=[(x0 + .5 + k, z) for k in range(6) for z in (2.3, 4.1)], bays=6, **fw)
    frame(g, 'Y', x0, y0 + .05, y1 - .05, bottom, eave + .03, -1,
          windows=[(y0 + (k + .5) * (y1 - y0) / 6, 4.1) for k in range(6)], bays=6, **fw)
    frame(g, 'Y', x1, y0 + .05, y1 - .05, bottom, eave + .03, 1,
          windows=[(y0 + (k + .5) * (y1 - y0) / 6, z) for k in range(6) for z in (2.3, 4.1)], bays=6, **fw)
    sawtooth(g, x0, y0, x1, y1, eave, teeth=3, rise=1.1)
    belt_bay(g, parts)


def belt_bay(g, parts):
    x0, y0 = SHOP[0], SHOP[1]
    bx0, bx1, bz = BAY
    floor = 1.012
    # Shallow closed bay: plaster back wall, timber-lined sides, soffit.
    g.box(((bx0 + bx1) / 2, BAY_BACK + .05, (floor + bz) / 2 + .01), (bx1 - bx0, .1, bz - floor + .02), CONCRETE)
    for x in [bx0 + .55 + k * (bx1 - bx0 - 1.1) / 3 for k in range(4)]:
        g.box((x, BAY_BACK - .035, (floor + bz) / 2), (.14, .07, bz - floor), WOOD)
    for x, s in ((bx0, 1), (bx1, -1)):
        g.box((x + s * .05, (y0 + .05 + BAY_BACK + .1) / 2, (floor + bz) / 2 + .01), (.1, BAY_BACK + .05 - y0, bz - floor + .02),
              GREYPLANK)
    g.box(((bx0 + bx1) / 2, (y0 + .14 + BAY_BACK + .1) / 2, bz - .03), (bx1 - bx0, BAY_BACK + .1 - y0 - .14, .1), WOOD)
    g.box(((bx0 + bx1) / 2, y0 + .02, floor + .015), (bx1 - bx0 - .2, .3, .03), IRON)
    # Line shaft with pulleys (one spinning part) on hangers.
    sy, sz = 3.4, 3.75
    for x in (bx0 + .35, (bx0 + bx1) / 2, bx1 - .35):
        g.box((x, sy, (sz + bz - .08) / 2 + .03), (.06, .06, bz - .08 - sz), IRON)
        g.box((x, sy, sz + .02), (.12, .14, .14), PAINTED)
    shaft = Geometry('PrecisionMachineWorks.LineShaft', ((bx0 + bx1) / 2, sy, sz))
    P.tube(shaft, (bx0 + .12, sy, sz), (bx1 - .12, sy, sz), .04, IRON, segments=10)
    lathes = (2.75, 3.85, 4.95)
    for x in lathes:
        P.pulley(shaft, (x - .62, sy, sz), .2, .12, 'X', PAINTED)
        P.lathe(shaft, (x - .62, sy, sz), [(.07, -.075), (.07, .075)], IRON, axis='X', segments=10)
    P.pulley(shaft, (5.75, sy, sz), .34, .14, 'X', IRON)
    for k in range(6):
        a = k * math.pi / 3
        shaft.beam((5.75, sy, sz), (5.75, sy + math.cos(a) * .3, sz + math.sin(a) * .3), .04, mat=IRON)
    parts.append((shaft, 'SPIN_X', 2))
    # Drive engine on the bay floor, belted up to the big pulley.
    g.box((5.75, 3.45, floor + .2), (.6, .5, .4), CONCRETE)
    P.motor(g, (5.75, 3.45, floor + .62), .2, .5, axis='X')
    for dy in (-.2, .2):
        g.beam((5.75, 3.45 + dy * .5, floor + .62), (5.75, sy + dy * 1.7, sz), .1, .02, WOOD)
    # Three lathes with spinning chucks, belted up to the shaft.
    for i, x in enumerate(lathes):
        ly, lz = 3.25, floor + .78
        for dx in (-.42, .42):
            g.box((x + dx, ly, floor + .32), (.14, .3, .62), IRON)
        g.box((x, ly, floor + .68), (1.1, .26, .1), IRON)
        g.box((x - .38, ly, lz + .06), (.26, .3, .3), PAINTED)
        g.box((x + .38, ly, lz - .01), (.16, .2, .16), IRON)
        P.tube(g, (x + .3, ly, lz), (x + .1, ly, lz), .025, IRON, segments=8)
        c = Geometry(f'PrecisionMachineWorks.Chuck{i + 1}', (x - .2, ly, lz))
        P.lathe(c, (x - .2, ly, lz), [(.11, -.04), (.11, .04)], IRON, axis='X', segments=12)
        for k in range(3):
            a = k * 2 * math.pi / 3
            c.box((x - .2, ly + math.cos(a) * .09, lz + math.sin(a) * .09), (.1, .05, .05), BRASS)
        P.tube(c, (x - .16, ly, lz), (x + .05, ly, lz), .045, CONCRETE, segments=8)
        P.pulley(c, (x - .62, ly, lz + .06), .1, .08, 'X', PAINTED)
        P.tube(c, (x - .52, ly, lz + .06), (x - .7, ly, lz + .06), .03, IRON, segments=8)
        parts.append((c, 'SPIN_X', 6))
        # Flat belt from the headstock pulley up to its shaft pulley.
        for dy in (-1, 1):
            g.beam((x - .62, ly + dy * .1, lz + .06), (x - .62, sy + dy * .19, sz), .07, .02, WOOD)
    for x in (2.35, 4.15, 5.95):
        K.lamp(g, x, BAY_BACK, 3.2, face='front')
    P.gauge(g, 5.75 - .32, 3.45 - .25, floor + .3, 'front', .07)


# ---------------------------------------------------------------- forge

def forge(g, parts):
    x0, y0, x1, y1 = 0.0, 3.0, SHOP[0] - .05 - .02, 7.0
    # Tiles 0..1 x 3..7; the right face stops .05 short so its foot clears the shop plinth's.
    top = P.plinth(g, x0, y0, .95, y1, .6, pilasters=False)
    room_x1 = x1 - .05
    fw = dict(infill=ORANGE, post=WOOD, post_w=.15, window_style='grand', window_scale=.7)
    frame(g, 'X', y0 + .12, x0 + .07, room_x1, top, 2.83, -1, bays=1, **fw)
    frame(g, 'X', y1 - .12, x0 + .07, room_x1, top, 2.83, 1, bays=1, **fw)
    frame(g, 'Y', x0 + .12, y0 + .17, y1 - .17, top, 2.83, -1, bays=4, windows=[(3.6, 1.75), (5.0, 1.75), (6.4, 1.75)],
          **fw)
    P.plank_slope(g, 'Y', x0 + .12, SHOP[0] - .04, 2.8, 3.55, y0 + .12, y1 - .12, overhang=.2, plank=.3)
    # Firebox door with a glowing slot on the front.
    g.box((.5, y0 + .12 - .09, 1.05), (.5, .06, .5), IRON)
    g.box((.5, y0 + .12 - .125, 1.0), (.3, .02, .05), GLOW)
    for dx in (-.2, .2):
        K.stud(g, (.5 + dx, y0 + .12 - .125, 1.25), 'Y', .02)
    # Tall square tapered brick chimney behind the forge (orange plaster
    # reads as brick), on a cast base and bound with iron bands.
    cx, cy = .45, 8.15
    base_r = .68
    top = 12.7
    taper = .3
    def r_at(z):
        return base_r * (1 - taper * (z - 1.0) / (top - 1.0))
    P.lathe(g, (cx, cy, 0), [(base_r * 1.05, 0), (base_r * 1.05, .9), (base_r, 1.0)], CONCRETE,
            segments=4, phase=math.pi / 4)
    P.lathe(g, (cx, cy, 0), [(r_at(1.0 + (top - 1.0) * k / 12), 1.0 + (top - 1.0) * k / 12) for k in range(13)],
            ORANGE, segments=4, phase=math.pi / 4, cap_start=False)
    for z in (2.6, 4.6, 6.6, 8.6, 10.6, 12.2):
        P.lathe(g, (cx, cy, 0), [(r_at(z) + .035, z - .06), (r_at(z) + .035, z + .06)], IRON, segments=4,
                phase=math.pi / 4)
    rt = r_at(top)
    P.lathe(g, (cx, cy, 0), [(rt + .06, top - .15), (rt + .06, top + .15)], IRON, segments=4, phase=math.pi / 4)
    g.box((cx, cy, top + .16), (rt * .9, rt * .9, .02), IRON)
    K.emitter(g, 'smoke', cx, cy, top + .17, rt * .45)   # forge smoke from the dark mouth plate
    # Flue from the forge into the chimney.
    P.pipe(g, [(.45, y1 - .12, 2.2), (.45, cy - .5, 2.2)], .12, flanges=False)


# ---------------------------------------------------------------- gate office

def gate_office(g, parts):
    """Two-storey works office at the gate; the compressed-air receiver for
    the shop's pneumatic tools rides on a braced steel frame on its roof."""
    x0, y0, x1, y1 = OFFICE
    top = P.plinth(g, x0, y0, x1, y1, 1.2, door=(DOOR_X, 1.0, 1.0))
    building_portal(g, DOOR_X, y0 - .12, 0)
    g.doorways.append({'id': 'Entrance', 'position': [DOOR_X, y0, 0], 'outward': [0, -1]})
    g.box((DOOR_X, y0 - .1, 1.32), (1.3, .2, .12), CONCRETE)
    for dx in (-.65, .65):
        K.lamp(g, DOOR_X + dx, y0 - .02, 1.0, face='front')
    # Timber-framed office storey with plaster infill and tall windows.
    wx0, wy0, wx1, wy1 = x0 + .12, y0 + .12, x1 - .12, y1 - .12
    eave = 3.2
    fw = dict(infill=ORANGE, post=WOOD, post_w=.15, window_style='grand', window_scale=.72)
    frame(g, 'X', wy0, wx0 - .05, wx1 + .05, top, eave, -1, bays=3,
          windows=[(7.55, 2.2), (DOOR_X, 2.2), (9.45, 2.2)], **fw)
    frame(g, 'X', wy1, wx0 - .05, wx1 + .05, top, eave, 1, bays=3, windows=[(7.55, 2.2), (9.45, 2.2)], **fw)
    frame(g, 'Y', wx0, wy0 + .05, wy1 - .05, top, eave, -1, bays=1, windows=[((wy0 + wy1) / 2, 2.2)], **fw)
    frame(g, 'Y', wx1, wy0 + .05, wy1 - .05, top, eave, 1, bays=1, windows=[((wy0 + wy1) / 2, 2.2)], **fw)
    K.flat_roof(g, wx0, wy0, wx1, wy1, eave, overhang=.12, parapet_height=.3)
    roof = eave + .16
    # Braced steel frame carrying the riveted air receiver.
    fz = roof + 1.2
    ty, tz, tr = (wy0 + wy1) / 2, fz + .5 + .1, .5
    for x in (7.6, 9.4):
        for y in (ty - .3, ty + .3):
            g.box((x, y, (roof + fz) / 2), (.12, .12, fz - roof), IRON)
            g.box((x, y, roof + .03), (.22, .22, .06), IRON)
        g.beam((x, ty - .3, roof + .12), (x, ty + .3, fz - .12), .06, mat=IRON)
    for y in (ty - .3, ty + .3):
        g.beam((7.66, y, roof + .12), (9.34, y, fz - .14), .06, mat=IRON)
        g.box((8.5, y, fz + .05), (1.98, .14, .1), IRON)
    for x in (7.9, 9.1):
        g.box((x, ty, fz + .16), (.18, .78, .12), PAINTED)
    P.lathe(g, (8.5, ty, tz), [(0, -1.15), (.3, -1.12), (.44, -1.03), (tr, -.88), (tr, .88), (.44, 1.03),
                               (.3, 1.12), (0, 1.15)], PAINTED, axis='X', segments=16)
    for x in (7.75, 8.5, 9.25):
        P.hoop(g, (x, ty, tz), tr + .02, .04, .06, IRON, axis='X', segments=16)
    g.cylinder((8.15, ty, tz + tr + .06), .12, .12, IRON, 'Z', 12)
    g.cylinder((8.15, ty, tz + tr + .13), .15, .03, BRASS, 'Z', 12)
    g.cylinder((8.95, ty, tz + tr + .1), .045, .2, BRASS, 'Z', 8)
    P.gauge(g, 9.0, ty - tr - .005, tz, 'front', .09)
    # Air main from the receiver across to the machine shop's front wall.
    P.pipe(g, [(7.38, ty, tz), (6.7, ty, tz), (6.7, SHOP[1] - .08, tz)], .06)
    K.ladder(g, 9.52, ty, roof, fz + .1, face='right', cage=False)


# ---------------------------------------------------------------- crane yard

def crane_yard(g, parts):
    xa, xb = 7.9, 10.65
    ys = (3.2, 5.9, 8.55)
    rz = 4.4
    for x in (xa, xb):
        for y in ys:
            P.pier(g, x, y, 0, .35, .32)
            g.box((x, y, (.4 + rz) / 2), (.2, .2, rz - .4), IRON)
        g.box((x, (ys[0] + ys[-1]) / 2, rz + .15), (.22, ys[-1] - ys[0] + .3, .3), PAINTED)
        g.box((x, (ys[0] + ys[-1]) / 2, rz + .33), (.08, ys[-1] - ys[0] + .3, .06), IRON)
        for y in ys:
            for s in (-1, 1):
                if (y == ys[0] and s < 0) or (y == ys[-1] and s > 0):
                    continue
                g.beam((x, y + s * .1, rz - .5), (x, y + s * .55, rz - .01), .08, mat=IRON)
    # Travelling bridge with trolley and hook block (one sliding part).
    y = 3.75
    bz = rz + .36
    br = Geometry('PrecisionMachineWorks.CraneBridge', ((xa + xb) / 2, y, bz))
    for dy in (-.22, .22):
        br.box(((xa + xb) / 2, y + dy, bz + .2), (xb - xa + .1, .14, .36), PAINTED)
    for x in (xa, xb):
        br.box((x, y, bz + .1), (.26, .9, .2), IRON)
        for dy in (-.3, .3):
            br.cylinder((x, y + dy, bz + .02), .08, .1, IRON, 'X', 10)
    tx = (xa + xb) / 2 - .3
    br.box((tx, y, bz + .48), (.6, .62, .2), IRON)
    P.lathe(br, (tx, y, bz + .64), [(.14, -.22), (.14, .22)], PAINTED, axis='X', segments=12)
    for dy in (-.06, .06):
        br.box((tx + .1, y + dy, bz - .55), (.012 + .01, .02, 1.5), IRON)
    br.box((tx + .1, y, bz - 1.38), (.2, .22, .26), PAINTED)
    P.hoop(br, (tx + .1, y, bz - 1.62), .1, .03, .04, IRON, axis='Y', segments=12)
    parts.append((br, 'SLIDE_Y', 3.9))
    # Steam hammer at the back of the yard.
    hx, hy = 10.0, 7.5
    top = P.plinth(g, hx - 1.0, hy - .5, hx + 1.0, hy + .5, .3, pilasters=False)   # tiles 9..11 x 7..8
    for dx in (-.5, .5):
        g.box((hx + dx, hy, top + 1.25), (.22, .4, 2.5), PAINTED)
    g.box((hx, hy, top + 2.6), (1.3, .44, .24), PAINTED)
    P.lathe(g, (hx, hy, top + 2.72), [(.24, 0), (.24, .7), (.2, .78)], IRON, segments=16)
    for z in (top + 2.95, top + 3.3):
        K.band(g, (hx, hy, 0), .24, z, .06, BRASS, segments=16)
    g.box((hx, hy, top + .3), (.5, .5, .6), IRON)
    g.box((hx, hy, top + .65), (.34, .3, .1), IRON)
    ram = Geometry('PrecisionMachineWorks.HammerRam', (hx, hy, top + 1.2))
    ram.box((hx, hy, top + .95), (.36, .3, .4), IRON)
    P.tube(ram, (hx, hy, top + 1.15), (hx, hy, top + 2.45), .05, IRON, segments=8)
    parts.append((ram, 'PISTON_Z', .42))
    P.pipe(g, [(hx + .24, hy, top + 3.2), (hx + .6, hy, top + 3.2), (hx + .6, hy, top + 4.0)], .05, flanges=False)
    P.valve(g, (hx + .6, hy, top + 3.6), 'right', .1)
    # Big roll lathe in the yard, turning a long shaft under the crane.
    ly, lz = 5.55, .95
    g.box((9.3, ly, .1), (2.28, .66, .2), CONCRETE)
    for x in (8.35, 9.3, 10.25):
        g.box((x, ly, .45), (.22, .36, .5), IRON)
    g.box((9.3, ly, .76), (2.2, .42, .12), IRON)
    g.box((8.47, ly, lz + .05), (.5, .54, .56), PAINTED)
    P.motor(g, (8.45, ly + .1, lz + .55), .15, .4, axis='X')
    g.box((10.2, ly, lz - .02), (.3, .34, .3), PAINTED)
    P.tube(g, (10.05, ly, lz), (9.98, ly, lz), .05, IRON, segments=8)
    g.box((9.42, ly - .12, .9), (.3, .24, .16), IRON)
    g.box((9.42, ly - .16, 1.02), (.12, .1, .1), BRASS)
    roll = Geometry('PrecisionMachineWorks.YardLatheRoll', (9.3, ly, lz))
    P.lathe(roll, (9.3, ly, lz), [(.3, -.6), (.3, -.54), (.2, -.54), (.2, .4), (.14, .4), (.14, .7)], IRON,
            axis='X', segments=16)
    for k in range(4):
        a = k * math.pi / 2
        roll.box((8.735, ly + math.cos(a) * .26, lz + math.sin(a) * .26), (.09, .07, .07), BRASS)
    parts.append((roll, 'SPIN_X', 2))
    # (Loose yard stock and barrels removed: only the crane, hammer and lathe stay.)


def build(g, parts):
    shop(g, parts)
    forge(g, parts)
    gate_office(g, parts)
    crane_yard(g, parts)
