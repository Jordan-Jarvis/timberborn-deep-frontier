"""SteelMill: electric steelworks making Flux, HighGradeSteel and Alloy.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the slag strip with its slag pot car and heap, and the post lamp.

HERO: an electric-arc melt shop whose three graphite electrodes rise on mast
arms through a forged roof penthouse, with a fat fume duct running over the
roof into a 14-layer riveted steel flue.
ROOF: long teal plank gable (ridge along X) with a glazed monitor lantern on
the melt shop; flat parapet roof with a beacon on the control pulpit; open
plank gable canopy over the rolling line.

Plan (12 x 10 tiles): control pulpit front-left with the door; open rolling
mill canopy along the front (reheat furnace, roller table, three two-high
mill stands) running onto a cooling bed at the front right; the melt shop
across the back left; the crane bay at the back right with a travelling
ladle crane, a tilting teeming ladle pouring into ingot moulds on a car, and
scrap / coal / ore bunkers; a slag pot and slag heap in the strip between.

Distinct from DeepProcessor (blast-furnace tower, skip bridge, stave
bunkers): no shaft furnace, no skip; the electrodes, the duct and the open
roll line carry the silhouette.

Animated: electrode masts (PISTON_Z), ladle crane bridge with its ladle
(SLIDE_Y), teeming ladle rocking on its trunnions (SWAY_X), pour stream
(PULSE), six mill rolls (SPIN_Y), hot bar running through the stands
(CUSTOM_LOOP_X), tap-hole and reheat-furnace glow (PULSE), pulpit beacon
(SPIN_Z).

No pipe port: none of the mill's recipes uses a liquid.
Smoke: the melt shop flue and the reheat furnace stovepipe are kit stacks.
"""
import math
import random

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN, LAYER_GAP
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
from lategame_mining_parts import ore_heap
from industrial_facades import building_portal
from native_window_atlas import atlas_window

IDENT = 'SteelMill'
FOOTPRINT = (12, 10)
HEIGHT = 15
FRAME_END = 121
HERO = ('Electric-arc melt shop whose three graphite electrodes rise on mast arms through a forged roof '
        'penthouse, with a fat fume duct over the roof into a 14-layer riveted steel flue.')

DOOR_X = 1.5
MELT = (0.0, 4.0, 7.0, 10.0)          # melt shop plinth on whole tiles
MELT_TOP = 1.5
EAVE, RIDGE = 6.5, 7.9
PENT = (.9, 5.7, 3.1, 8.7)             # electrode penthouse plan
PENT_TOP = 9.1
ELECTRODES = ((1.55, 6.55), (2.45, 6.55), (2.0, 7.35))
MAST_Y = 7.95
STACK = (8.0, 9.35)
BAY_COLS_X = (7.3, 11.62)
BAY_COLS_Y = (4.4, 6.5, 8.6)
RUNWAY_TOP = 5.55
LADLE = (9.6, 5.0, 2.0)                # teeming ladle trunnion axis
LADLE_TILT = .45                       # authored forward tilt (radians)
LADLE_SWAY = .08
ROLL_LINE_Y = 1.5
STANDS = (5.72, 7.17, 8.55)
BAR_Z = (.63, .71)


def animate(obj, kind, value, frame_end):
    C.animate(obj, kind, value, frame_end)


def centres(a, b, n):
    return [a + (b - a) * (k + .5) / n for k in range(n)]


def room(g, x0, y0, x1, y1, bottom, top, *, infill, post, post_w=.16, windows=None, style='factory',
         scale=.8, bays=None):
    """Four framed walls meeting at closed corners (front/back walls run past
    the side walls, side walls butt into them)."""
    windows = windows or {}
    for name, axis, plane, start, end, out in (
            ('front', 'X', y0, x0 - .05, x1 + .05, -1), ('back', 'X', y1, x0 - .05, x1 + .05, 1),
            ('left', 'Y', x0, y0 + .05, y1 - .05, -1), ('right', 'Y', x1, y0 + .05, y1 - .05, 1)):
        K.frame_wall(g, axis, plane, start, end, bottom, top, outward=out, infill=infill, post=post,
                     post_w=post_w, windows=windows.get(name), window_style=style, window_scale=scale,
                     bays=(bays or {}).get(name))


def copy_rotated_x(dst, src, pivot, angle):
    """Copy every face of `src` (built about the artwork origin) into `dst`,
    rotated about the X-parallel axis through `pivot`."""
    verts = [C.rot_x((-x, -y, z), pivot, angle) for x, y, z in src.vertices]
    for face, mat in zip(src.faces, src.materials):
        dst.add([verts[i] for i in face], [tuple(range(len(face)))], mat)


# ---------------------------------------------------------------- ground

def ground(g):
    """Concrete yard slabs (one owner of the ground per spot)."""
    blk(g, 3.0, 0.0, -.02, 9.5, 3.0, .2, CONCRETE)             # rolling line (the cooling bed owns 9.5..12)
    blk(g, 7.05, 3.05, -.02, 12.0, 10.0, .2, CONCRETE)         # crane bay


# ---------------------------------------------------------------- control pulpit

def pulpit(g, parts):
    x0, y0, x1, y1 = 0.0, .15, 2.95, 3.0
    top = P.plinth(g, x0, y0, x1, y1, 1.3, door=(DOOR_X, 1.0, 1.0))
    building_portal(g, DOOR_X, y0 - .12, 0)
    g.doorways.append({'id': 'Entrance', 'position': [DOOR_X, y0, 0], 'outward': [0, -1]})
    for x in (.5, 2.5):
        atlas_window(g, x, y0, .72, .42, 'front', 'grid9', reveal=IRON)
    atlas_window(g, x0, 1.6, .72, .42, 'left', 'grid9', reveal=IRON)
    # Steel-framed operating floor with a long ribbon window over the mill.
    bx0, by0, bx1, by1 = x0 + .12, y0 + .12, x1 - .12, y1 - .12
    z0, z1 = top + .02, 3.4
    C.framed_block(g, bx0, by0, bx1, by1, z0, z1, infill=FORGED, frame=IRON, pitch=.92, sink=.03,
                   windows={'front': [(.57, 2.35, .8, 'factory'), (2.38, 2.35, .8, 'factory')],
                            'left': [(1.6, 2.35, .8, 'factory')], 'back': [(1.45, 2.35, .8, 'factory')]},
                   skip={'right': [(.5, 2.7)]})
    atlas_window(g, bx1, 1.6, 2.35, 1.95, 'right', 'ribbon', reveal=IRON)
    K.flat_roof(g, bx0, by0, bx1, by1, z1, thickness=.16, overhang=.1, parapet_height=.32)
    # Roof siren and beacon.
    blk(g, 2.1, 2.0, z1 + .16, 2.3, 2.2, z1 + .8, IRON)
    pivot = K.beacon(g, 2.2, 2.1, z1 + .8)
    parts.append((K.beacon_shutter(*pivot, 'SteelMill.PulpitBeacon'), 'SPIN_Z', 2))
    g.box((.75, 2.1, z1 + .3), (.36, .3, .28), PAINTED)
    K.lamp(g, DOOR_X - .62, y0 - .04, 1.1, face='front')
    K.lamp(g, DOOR_X + .62, y0 - .04, 1.1, face='front')


# ---------------------------------------------------------------- melt shop

def melt_shop(g, parts):
    x0, y0, x1, y1 = MELT
    top = P.plinth(g, x0, y0, x1, y1, MELT_TOP)
    wx0, wy0, wx1, wy1 = x0 + .1, y0 + .1, x1 - .1, y1 - .1
    bottom = top + .01
    xs = centres(wx0 - .05, wx1 + .05, 7)
    ys = centres(wy0 + .05, wy1 - .05, 6)
    room(g, wx0, wy0, wx1, wy1, bottom, EAVE + .03, infill=FORGED, post=IRON, post_w=.18, style='factory',
         scale=.95,
         windows={'front': [(x, 5.0) for x in xs] + [(x, 2.9) for x in xs[::2]],
                  'back': [(x, 5.0) for x in xs[::2]] + [(x, 2.9) for x in xs[1::2]],
                  'left': [(y, z) for y in ys for z in (2.9, 5.0)],
                  'right': [(y, 4.6) for y in (ys[0], ys[2], ys[4])]},
         bays={'front': 7, 'back': 7, 'left': 6, 'right': 6})
    # Plinth windows (factory grids).
    for y in (5.5, 7.5, 9.5):
        atlas_window(g, x0, y, .8, .5, 'left', 'grid9', reveal=IRON)
    for x in (1.5, 3.5, 5.5):
        atlas_window(g, x, y1, .8, .5, 'back', 'grid9', reveal=IRON)
    # Tap hole on the bay wall: dark iron frame, glowing throat, spout.
    ty, tz = ys[3], 2.55
    blk(g, wx1 + .05, ty - .34, tz - .32, wx1 + .14, ty + .34, tz + .32, IRON)
    blk(g, wx1 + .14, ty - .22, tz - .2, wx1 + .16, ty + .22, tz + .2, CONCRETE)
    glow = Geometry('SteelMill.TapGlow', (wx1 + .18, ty, tz))
    glow.box((wx1 + .18, ty, tz), (.04, .3, .26), GLOW)
    parts.append((glow, 'PULSE', .08))
    g.beam((wx1 + .16, ty, tz - .3), (wx1 + .8, ty, tz - .5), .16, .1, IRON)
    P.plank_roof(g, wx0, wy0, wx1, wy1, EAVE, RIDGE, ridge_axis='X', overhang=.2, plank=.32, gable_mat=FORGED)
    # Apex finials close the crossing plank ends at both gables.
    for x, s in ((wx0 - .2, -1), (wx1 + .2, 1)):
        blk(g, min(x + s * .005, x + s * .085), (wy0 + wy1) / 2 - .075, RIDGE - .08,
            max(x + s * .005, x + s * .085), (wy0 + wy1) / 2 + .075, RIDGE + .2, WOOD)
    lantern(g)
    penthouse(g, parts)


def lantern(g):
    """Glazed monitor lantern astride the ridge over the east half."""
    lx0, lx1, ly0, ly1 = 3.95, 6.5, 6.45, 7.55
    zb, zt = 7.35, 8.45
    blk(g, lx0, ly0, zb, lx1, ly1, zt, FORGED)
    for x in (lx0, lx1):
        for y in (ly0, ly1):
            blk(g, x - .06, y - .06, zb + .2, x + .06, y + .06, zt - .02, IRON)
    for x in (4.4, 5.2, 6.0):
        atlas_window(g, x, ly0, 8.0, .7, 'front', 'ribbon', reveal=IRON)
        atlas_window(g, x, ly1, 8.0, .7, 'back', 'ribbon', reveal=IRON)
    P.plank_roof(g, lx0, ly0, lx1, ly1, zt, zt + .42, ridge_axis='X', overhang=.12, plank=.3, gable_mat=FORGED)


def penthouse(g, parts):
    px0, py0, px1, py1 = PENT
    blk(g, px0, py0, 6.6, px1, py1, PENT_TOP, FORGED)
    for x in (px0, px1):
        for y in (py0, py1):
            blk(g, x - .07, y - .07, 7.0, x + .07, y + .07, PENT_TOP - .01, IRON)
    for z in (7.75, 8.45):
        blk(g, px0 + .07, py0 - .03, z, px1 - .07, py0 + .002, z + .08, IRON)
        blk(g, px0 - .03, py0 + .07, z, px0 + .002, py1 - .07, z + .08, IRON)
    P.louvre(g, 'X', py0, px0 + .25, px1 - .25, 7.85, 8.4, -1)
    P.louvre(g, 'Y', px0, py0 + .3, py1 - .3, 7.85, 8.4, -1)
    cap = PENT_TOP + .12
    blk(g, px0 - .08, py0 - .08, PENT_TOP, px1 + .08, py1 + .08, cap, IRON)
    # Electrode collars (static rings, clear of the moving electrodes).
    for ex, ey in ELECTRODES:
        P.hoop(g, (ex, ey, cap + .06), .29, .08, .12, BRASS, segments=16)
    # Mast guide sleeves.
    for ex, _ in ELECTRODES:
        blk(g, ex - .13, MAST_Y - .13, cap - .02, ex + .13, MAST_Y + .13, 10.35, IRON)
        blk(g, ex - .16, MAST_Y - .16, 10.35, ex + .16, MAST_Y + .16, 10.43, PAINTED)
    # Moving assembly: electrodes, clamps, arms and mast heads.
    m = Geometry('SteelMill.Electrodes', (2.0, 7.0, 10.0))
    arm_z = {0: 10.95, 1: 10.95, 2: 11.15}
    for i, (ex, ey) in enumerate(ELECTRODES):
        az = arm_z[i]
        m.cylinder((ex, ey, (8.7 + 12.25) / 2), .16, 12.25 - 8.7, IRON, 'Z', 16)
        m.cylinder((ex, ey, 12.27), .12, .04, IRON, 'Z', 16)
        for zj in (10.1, 11.75):
            P.hoop(m, (ex, ey, zj), .185, .05, .07, BRASS, segments=16)
        blk(m, ex - .22, ey - .22, az - .17, ex + .22, ey + .22, az + .17, PAINTED)
        blk(m, ex - .08, ey + .22, az - .1, ex + .08, MAST_Y - .07, az + .1, IRON)
        blk(m, ex - .07, MAST_Y - .07, 9.55, ex + .07, MAST_Y + .07, az + .22, IRON)
        blk(m, ex - .1, MAST_Y - .1, az + .22, ex + .1, MAST_Y + .1, az + .3, PAINTED)
        # Flexible cable loops from the clamp to the mast (heavy bus).
        for s in (-1, 1):
            m.beam((ex + s * .1, ey + .25, az - .15), (ex + s * .1, MAST_Y - .12, az - .45), .05, mat=BRASS)
    parts.append((m, 'PISTON_Z', .22))
    # Fume duct over the roof to the flue.
    duct_y, duct_z = 8.35, 8.6
    P.pipe(g, [(px1 - .05, duct_y, duct_z), (STACK[0], duct_y, duct_z), (STACK[0], STACK[1] - .2, duct_z)],
           .3, IRON, flanges=False, elbow_mat=IRON, segments=16)
    for x in (3.6, 5.0, 6.4, 7.4):
        P.hoop(g, (x, duct_y, duct_z), .335, .06, .1, PAINTED, axis='X', segments=16)
    for x in (4.3, 5.7):
        roof_z = EAVE + (MELT[3] - .1 - duct_y) * (RIDGE - EAVE) / 2.9
        blk(g, x - .06, duct_y - .06, roof_z - .1, x + .06, duct_y + .06, duct_z - .28, IRON)
        blk(g, x - .2, duct_y - .05, duct_z - .32, x + .2, duct_y + .05, duct_z - .27, IRON)


def flue(g):
    sx, sy = STACK
    K.revolve(g, (sx, sy, .17), [(.6, 0), (.6, .5), (.52, .58)], CONCRETE, segments=8, phase=math.pi / 8)
    K.stack(g, sx, sy, .72, 13.75, emits='smoke', r=.42, taper=.78, mat=IRON, bands=5)


# ---------------------------------------------------------------- crane bay

def crane_bay(g, parts):
    base = .2
    for x in BAY_COLS_X:
        for y in BAY_COLS_Y:
            P.pier(g, x, y, base - .03, base + .35, .36)
            blk(g, x - .11, y - .11, base + .4, x + .11, y + .11, RUNWAY_TOP - .36, IRON)
            # Knee braces under the runway.
            for s in (-1, 1):
                if (y == BAY_COLS_Y[0] and s < 0) or (y == BAY_COLS_Y[-1] and s > 0):
                    continue
                g.beam((x, y + s * .1, RUNWAY_TOP - 1.1), (x, y + s * .62, RUNWAY_TOP - .38), .08, mat=IRON)
        # Runway girder: stacked flanges and web, crane rail on top.
        ya, yb = BAY_COLS_Y[0] - .2, BAY_COLS_Y[-1] + .2
        blk(g, x - .14, ya, RUNWAY_TOP - .36, x + .14, yb, RUNWAY_TOP - .3, IRON)
        blk(g, x - .04, ya + .01, RUNWAY_TOP - .3, x + .04, yb - .01, RUNWAY_TOP - .06, IRON)
        blk(g, x - .12, ya, RUNWAY_TOP - .06, x + .12, yb, RUNWAY_TOP, IRON)
        blk(g, x - .03, ya + .02, RUNWAY_TOP, x + .03, yb - .02, RUNWAY_TOP + .05, PAINTED)
    # Ladle crane: bridge, end trucks, trolley, ropes, hook and a full ladle.
    yc, zc = 8.0, RUNWAY_TOP + .05
    c = Geometry('SteelMill.LadleCrane', (9.6, yc, zc))
    xa, xb = BAY_COLS_X[0] - .15, BAY_COLS_X[1] + .15
    for x in BAY_COLS_X:
        blk(c, x - .13, yc - .45, zc + .01, x + .13, yc + .45, zc + .24, PAINTED)
        for s in (-1, 1):
            c.cylinder((x, yc + s * .3, zc + .07), .07, .2, IRON, 'X', 10)
    for s in (-1, 1):
        y = yc + s * .26
        blk(c, xa + .15, y - .09, zc + .24, xb - .15, y + .09, zc + .62, IRON)
        blk(c, xa + .17, y - .12, zc + .62, xb - .17, y + .12, zc + .67, IRON)
        for k in range(7):
            x = xa + .5 + k * (xb - xa - 1.0) / 6
            K.stud(c, (x, y + s * .091, zc + .43), 'Y', .02)
    tx = LADLE[0]
    blk(c, tx - .45, yc - .4, zc + .68, tx + .45, yc + .4, zc + 1.0, PAINTED)
    c.cylinder((tx, yc, zc + 1.18), .22, .7, IRON, 'X', 14)
    blk(c, tx - .52, yc - .42, zc + 1.0, tx + .52, yc + .42, zc + 1.04, IRON)
    hook_z = 4.0
    for dx in (-.12, .12):
        for dy in (-.08, .08):
            c.beam((tx + dx, yc + dy, zc + .7), (tx + dx * .6, yc + dy * .6, hook_z + .2), .025, mat=IRON)
    blk(c, tx - .2, yc - .14, hook_z - .1, tx + .2, yc + .14, hook_z + .2, PAINTED)
    c.cylinder((tx, yc, hook_z - .2), .07, .22, IRON, 'Y', 10)
    # Bail and ladle hung from the hook.
    lz0, lz1 = 2.3, 3.3
    for s in (-1, 1):
        c.beam((tx + s * .1, yc, hook_z - .2), (tx + s * .62, yc, 3.0), .07, mat=IRON)
        c.cylinder((tx + s * .56, yc, 3.0), .07, .2, IRON, 'X', 10)
    P.lathe(c, (tx, yc, lz0), [(.42, 0), (.5, lz1 - lz0), (.56, lz1 - lz0), (.56, lz1 - lz0 + .06)], IRON,
            segments=18)
    for z in (2.55, 2.95):
        K.band(c, (tx, yc, 0), .42 + .08 * (z - lz0) / (lz1 - lz0), z, .06, PAINTED, segments=18)
    rim = lz1 + .06
    c.cylinder((tx, yc, rim + .01), .5, .02, IRON, 'Z', 18)
    c.cylinder((tx, yc, rim + .0275), .3, .015, GLOW, 'Z', 12)
    parts.append((c, 'SLIDE_Y', -1.8))
    teeming(g, parts)
    bunkers(g)


def teeming(g, parts):
    lx, ly, lz = LADLE
    base = .2
    for s in (-1, 1):
        x = lx + s * .72
        blk(g, x - .17, ly - .4, base - .03, x + .17, ly + .4, lz - .25, CONCRETE)
        blk(g, x - .2, ly - .43, base - .03, x + .2, ly + .43, base + .12, CONCRETE)
        blk(g, x - .14, ly - .16, lz - .25, x + .14, ly + .16, lz - .06, IRON)
    # Tilting ladle, authored upright then tilted forward on its trunnions.
    src = Geometry('ladle source')
    z0, z1 = lz - .65, lz + .45
    P.lathe(src, (lx, ly, z0), [(.45, 0), (.55, z1 - z0), (.6, z1 - z0), (.6, z1 - z0 + .06)], IRON, segments=12)
    for z in (z0 + .22, z0 + .78):
        K.band(src, (lx, ly, 0), .45 + .1 * (z - z0) / (z1 - z0), z, .07, PAINTED, segments=12)
    src.cylinder((lx, ly, z1 + .07), .52, .02, IRON, 'Z', 12)
    src.cylinder((lx, ly, z1 + .0875), .3, .015, GLOW, 'Z', 12)
    blk(src, lx - .12, ly - .72, z1 - .06, lx + .12, ly - .5, z1 + .02, IRON)      # pouring nose
    for s in (-1, 1):
        src.cylinder((lx + s * .6, ly, lz), .09, .14, IRON, 'X', 12)
        src.cylinder((lx + s * .55, ly, lz), .14, .05, PAINTED, 'X', 12)
    ladle = Geometry('SteelMill.TeemingLadle', (lx, ly, lz))
    copy_rotated_x(ladle, src, (lx, ly, lz), LADLE_TILT)
    parts.append((ladle, 'SWAY_X', LADLE_SWAY))
    # Pour stream from the nose into the mould below.
    nose = C.rot_x((lx, ly - .66, z1 - .02), (lx, ly, lz), LADLE_TILT)
    mould_top = 1.08
    stream = Geometry('SteelMill.PourStream', (lx, nose[1], nose[2]))
    K.revolve(stream, (lx, nose[1], mould_top - .1), [(.06, 0), (.055, .3), (.045, nose[2] + .06 - mould_top + .1)],
              GLOW, segments=8)
    parts.append((stream, 'PULSE', .06))
    # Ingot moulds on a car running along the bay front.
    track_y = nose[1]
    for s in (-1, 1):
        blk(g, 7.6, track_y + s * .25 - .03, base, 11.3, track_y + s * .25 + .03, base + .07, IRON)
    for k in range(6):
        x = 7.8 + k * .66
        blk(g, x - .05, track_y - .38, base - .01, x + .05, track_y + .38, base + .025, WOOD)
    for k, x in enumerate((lx - .75, lx, lx + .75)):
        blk(g, x - .32, track_y - .3, base + .2, x + .32, track_y + .3, base + .3, IRON)
        for sx in (-.22, .22):
            for sy in (-1, 1):
                g.cylinder((x + sx, track_y + sy * .25, base + .15), .08, .05, IRON, 'Y', 10)
        K.revolve(g, (x, track_y, base + .3), [(.22, 0), (.19, mould_top - base - .3)], PAINTED, segments=4,
                  phase=math.pi / 4)
        if k == 1:
            blk(g, x - .1, track_y - .1, mould_top - .02, x + .1, track_y + .1, mould_top + .012, GLOW)


def bunkers(g):
    base = .2
    y0, y1 = 8.95, 9.97
    xs = (8.72, 9.8, 10.88, 11.97)
    blk(g, xs[0] - .08, y1 - .15, base - .03, xs[-1], y1, 1.35, CONCRETE)
    for x in xs:
        blk(g, x - .08, y0, base - .03, min(x + .08, 11.97), y1 - .15, 1.2, CONCRETE)
    blk(g, xs[0] - .1, y1 - .17, 1.35, xs[-1], y1 + .02, 1.4, IRON)
    # Scrap, coal and ore heaps.
    rng = random.Random(7)
    cx = (xs[0] + xs[1]) / 2
    ore_heap(g, cx, 9.4, base, .38, .32, h=.55, mats=(IRON, PAINTED, FORGED), seed=11)
    for i in range(9):
        a = rng.uniform(0, math.pi)
        c = (cx + rng.uniform(-.25, .25), 9.4 + rng.uniform(-.2, .2), base + .307 + i * .017)
        C.obox(g, c, (math.cos(a), math.sin(a), 0), (-math.sin(a), math.cos(a), 0), (0, 0, 1),
               .16, .03, .03, rng.choice((IRON, PAINTED, FORGED)))
    ore_heap(g, (xs[1] + xs[2]) / 2, 9.4, base, .4, .34, h=.6, mats=(IRON,), seed=12)
    ore_heap(g, (xs[2] + xs[3]) / 2, 9.4, base, .4, .34, h=.6, mats=(GREYPLANK, IRON), seed=13)


# ---------------------------------------------------------------- rolling line

def rolling_line(g, parts):
    base = .2
    x0, x1, ya, yb = 3.4, 9.3, .38, 2.62
    cols = (3.55, 5.0, 6.45, 7.9, 9.15)
    eave = 3.45
    for x in cols:
        for y in (ya, yb):
            P.pier(g, x, y, base - .03, base + .3, .3)
            blk(g, x - .08, y - .08, base + .35, x + .08, y + .08, eave - .02, IRON)
    for y in (ya, yb):
        blk(g, x0 + .05, y - .09, eave - .02, x1 - .05, y + .09, eave + .12, IRON)
    for x in cols[1:-1]:
        g.beam((x, ya + .06, eave - .55), (x, ya + .5, eave - .02), .07, mat=IRON)
        g.beam((x, yb - .06, eave - .55), (x, yb - .5, eave - .02), .07, mat=IRON)
    P.plank_roof(g, x0 + .05, ya, x1 - .05, yb, eave + .12, eave + 1.0, ridge_axis='X', overhang=.3, plank=.3,
                 gables=(False, False))
    # Reheat furnace at the head of the line.
    fx0, fx1, fy0, fy1 = 3.55, 4.65, .75, 2.25
    blk(g, fx0, fy0, base - .03, fx1, fy1, 1.45, CONCRETE)
    blk(g, fx0 - .04, fy0 - .04, 1.45, fx1 + .04, fy1 + .04, 1.53, IRON)
    for x in (fx0 + .2, (fx0 + fx1) / 2, fx1 - .2):
        blk(g, x - .05, fy0 - .04, base + .1, x + .05, fy0, 1.45, IRON)
        blk(g, x - .05, fy1, base + .1, x + .05, fy1 + .04, 1.45, IRON)
    blk(g, 3.75, fy0 - .05, .5, 4.45, fy0 - .02, 1.1, IRON)                 # charging door
    blk(g, 3.8, fy0 - .07, 1.0, 4.4, fy0 - .05, 1.04, BRASS)
    blk(g, fx1, ROLL_LINE_Y - .3, .55, fx1 + .03, ROLL_LINE_Y + .3, .82, IRON)
    glow = Geometry('SteelMill.ReheatGlow', (fx1 + .04, ROLL_LINE_Y, .67))
    glow.box((fx1 + .04, ROLL_LINE_Y, .67), (.02, .4, .16), GLOW)
    parts.append((glow, 'PULSE', .1))
    K.stack(g, 4.1, 1.05, 1.53, 3.35, emits='smoke', r=.12, taper=.9, bands=3)
    P.hoop(g, (4.1, 1.05, 4.25), .2, .07, .06, IRON, segments=14)
    # Roller table, interrupted at the stands.
    tx0, tx1 = fx1 + .04, 9.4
    cuts = [tx0] + [v for s in STANDS for v in (s - .36, s + .36)] + [tx1]
    for a, b in zip(cuts[::2], cuts[1::2]):
        for y in (ROLL_LINE_Y - .3, ROLL_LINE_Y + .3):
            blk(g, a, y - .035, .42, b, y + .035, .6, IRON)
    for x in (5.0, 6.45, 7.9, 9.3):
        for y in (ROLL_LINE_Y - .3, ROLL_LINE_Y + .3):
            blk(g, x - .04, y - .04, base - .02, x + .04, y + .04, .42, IRON)
    x = tx0 + .2
    while x < tx1 - .1:
        if all(abs(x - s) > .4 for s in STANDS):
            g.cylinder((x, ROLL_LINE_Y, .555), .07, .53, IRON, 'Y', 10)
        x += .3
    for i, sx in enumerate(STANDS):
        mill_stand(g, parts, i, sx)
    # Hot bar segments travel one pitch per loop through the stands.
    pitch = .9
    bar = Geometry('SteelMill.HotBar', (6.9, ROLL_LINE_Y, BAR_Z[0]))
    for k in range(6):
        xa = 4.35 + k * pitch
        blk(bar, xa, ROLL_LINE_Y - .09, BAR_Z[0] + .003, xa + .68, ROLL_LINE_Y + .09, BAR_Z[1] - .003, GLOW)
    parts.append((bar, 'CUSTOM_LOOP_X', pitch))
    K.lamp(g, cols[0], ya - .09, 2.6, face='front')
    K.lamp(g, cols[2], ya - .09, 2.6, face='front')


def mill_stand(g, parts, i, sx):
    y = ROLL_LINE_Y
    lo, hi = .43, .91
    for side in (-1, 1):
        py = y + side * .52
        for dx in (-.22, .22):
            blk(g, sx + dx - .07, py - .07, .2, sx + dx + .07, py + .07, 1.5, IRON)
        blk(g, sx - .32, py - .09, 1.5, sx + .32, py + .09, 1.68, PAINTED)
        blk(g, sx - .34, py - .1, .17, sx + .34, py + .1, .3, IRON)
        # Screw-down column on the crosshead.
        g.cylinder((sx, py, 1.8), .05, .24, IRON, 'Z', 8)
    g.wheel((sx, y - .52, 1.98), .16, 'Y', IRON, BRASS)
    blk(g, sx - .3, y - .44, 1.6, sx + .3, y + .44, 1.66, IRON)
    # Spindles back to a pinion box and motor behind the line.
    for z in (lo, hi):
        g.cylinder((sx, y + .69, z), .06, .24, IRON, 'Y', 10)
    blk(g, sx - .25, 2.2, .2, sx + .25, 2.5, 1.15, PAINTED)
    blk(g, sx - .18, 2.5, .2, sx + .18, 2.72, .28, IRON)
    P.motor(g, (sx, 2.49, .48), .2, .32, axis='Y')
    for z, name, turns in ((lo, 'Lower', 2), (hi, 'Upper', -2)):
        r = Geometry(f'SteelMill.Stand{i + 1}{name}Roll', (sx, y, z))
        r.cylinder((sx, y, z), .2, .9, IRON, 'Y', 16)
        r.cylinder((sx, y, z), .085, 1.24, IRON, 'Y', 10)
        for k in range(4):
            a = k * math.pi / 2
            r.box((sx + math.cos(a) * .1, y + .6, z + math.sin(a) * .1), (.05, .05, .05), BRASS)
        parts.append((r, 'SPIN_Y', turns))


def cooling_bed(g):
    base = .2
    x0, x1, y0, y1 = 9.5, 12.0, 0.0, 3.0
    blk(g, x0, y0, -.02, x1, y1, .36, CONCRETE)
    n = 8
    for k in range(n):
        x = x0 + .12 + k * (x1 - x0 - .24) / (n - 1)
        blk(g, x - .03, y0 + .25, .36, x + .03, y1 - .25, .52, IRON)
        for j in range(7):
            yy = y0 + .45 + j * .35
            blk(g, x - .025, yy - .02, .52, x + .025, yy + .02, .58, IRON)
    for j in range(7):
        yy = y0 + .53 + j * .35
        g.cylinder(((x0 + x1) / 2, yy, .6), .045, x1 - x0 - .2, PAINTED if j % 2 else IRON, 'X', 8)


# ---------------------------------------------------------------- slag yard

def build(g, parts):
    ground(g)
    pulpit(g, parts)
    melt_shop(g, parts)
    flue(g)
    crane_bay(g, parts)
    rolling_line(g, parts)
    cooling_bed(g)
