"""ArchiveExcavation: digs relics of the vanished humans out of the ground

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the columned portico and the planting.
(RecoveredArtifact) and catalogues them (ArchiveData).

HERO: an excavation pit inside stepped concrete retaining walls, exposing a
giant rusted human cogwheel half-buried in spoil beside a broken fluted
column, laid out with an archaeologist's string grid and worked by a tall
riveted steel tripod derrick with a hoist bucket.
ROOF: teal hip roof with a glazed reading-room lantern on the archive hall;
small pedimented portico; steep teal gable on the tall archive stack; lean-to
on the catalogue wing and the sieving shed.

Plan (10 x 9 tiles): archive hall front-left with a columned museum portico
and the door; the archive stack tower and catalogue wing behind it; the pit
across the right and back (its left side is the archive podiums); the open
sieving shed along the front right, fed by a spoil belt on the pit rim.

Distinct from the quarries and pits (timber box headframe and winding drum,
gallows crane): a three-legged steel derrick, a terraced dig with shoring
and string lines, and an exposed ruin instead of a rock face.

Animated: hoist bucket (SLIDE_Z) with its paying-out rope (CUSTOM_CABLE),
crown sheave (SPIN_X), winch drum and flywheel (SPIN_X), two shaking
sieves (PISTON_X), spoil belt (CUSTOM_LOOP_X), derrick beacon (SPIN_Z).

No pipe port: neither recipe uses a liquid.
Smoke: the archive stack's stove flue is a kit stack.
"""
import math
import random

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN, LAYER_GAP
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
from lategame_mining_parts import ore_heap, lean_to
from native_window_atlas import atlas_window, glass_curtain
import native_building_assets as N

IDENT = 'ArchiveExcavation'
FOOTPRINT = (10, 9)
HEIGHT = 11
FRAME_END = 121
HERO = ('Terraced excavation pit exposing a giant rusted human cogwheel half-buried beside a broken '
        'fluted column, laid out with string lines and worked by a tall steel tripod derrick and hoist bucket.')

HALL = (0.0, 1.0, 5.0, 5.0)        # archive hall podium (whole tiles)
HALL_TOP, HALL_EAVE = 1.2, 4.4
REAR = (0.0, 5.0, 5.0, 9.0)        # stack tower + catalogue wing podium
REAR_TOP = 1.3
TOWER_X1 = 2.95
TOWER_EAVE = 8.2
RIM = 1.0                          # pit retaining wall top
LEDGE = .4                         # inner terrace
SHED_Y1 = 2.0
CROSS = (7.0, 8.0, 5.0, 5.6, 7.95, 8.2)      # derrick crosshead x0 x1 y0 y1 z0 z1
SHEAVE = (7.5, 5.3, 7.55)
SHEAVE_R = .32
BUCKET = (7.5, SHEAVE[1] - SHEAVE_R)        # rope line under the front of the sheave
BUCKET_REST, BUCKET_TRAVEL = 4.9, 4.75
WINCH = (7.5, 8.45, RIM + .45)
GEAR = (6.5, 6.0, 1.3)
GEAR_R = 1.3


def animate(obj, kind, value, frame_end):
    """CUSTOM_CABLE: the hoist rope stretches down from the sheave in step
    with the bucket's SLIDE_Z (same keys and easing), value (travel, length).
    CUSTOM_LOOP_<axis>: conveyor items (lategame_civic_parts.animate)."""
    if kind == 'CUSTOM_CABLE':
        travel, length = value
        span = frame_end - 1
        for frame, t in ((1, 0), (1 + span * .4, 1), (1 + span * .5, 1), (1 + span * .9, 0), (frame_end, 0)):
            obj.scale = (1, 1, 1 + travel * t / length)
            obj.keyframe_insert(data_path='scale', frame=frame)
        for curve in obj.animation_data.action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'BEZIER'
        return
    C.animate(obj, kind, value, frame_end)


def gaps(a, b, n, post, corner):
    """Centres of the clear bays between framed_block bay posts."""
    stations = [a + (b - a) * i / n for i in range(1, n)]
    edges = [a + corner / 2] + [s for st in stations for s in (st - post / 2, st + post / 2)] + [b - corner / 2]
    return [(edges[2 * i] + edges[2 * i + 1]) / 2 for i in range(n)]


def plank_gable(g, x0, y0, x1, y1, eave, ridge, *, overhang, gable_mat):
    """Plank gable with the ridge along X, plus apex finials that close the
    crossing plank ends at both gables."""
    P.plank_roof(g, x0, y0, x1, y1, eave, ridge, ridge_axis='X', overhang=overhang, plank=.3,
                 gable_mat=gable_mat)
    for x, s in ((x0 - overhang, -1), (x1 + overhang, 1)):
        blk(g, min(x + s * .005, x + s * .085), (y0 + y1) / 2 - .075, ridge - .08,
            max(x + s * .005, x + s * .085), (y0 + y1) / 2 + .075, ridge + .2, WOOD)


def bays(a, b, pitch):
    return max(1, round((b - a) / pitch))


# ---------------------------------------------------------------- archive hall

def hall(g, parts):
    x0, y0, x1, y1 = HALL
    C.podium(g, x0, y0, x1, y1, HALL_TOP, skip=[(2.0, 3.0)])
    C.door(g, 2.5, y0, 0, 'Door0')
    for x in (.6, 4.4):
        atlas_window(g, x, y0, .6, .45, 'front', 'grid9')
    for y in (1.5, 2.5, 3.5, 4.5):
        atlas_window(g, x0, y, .6, .45, 'left', 'grid9')
    bx0, by0, bx1, by1 = x0 + .05, y0 + .05, x1 - .05, y1 - .05
    nx, ny = bays(bx0, bx1, .98), bays(by0, by1, .98)
    fx = gaps(bx0, bx1, nx, .11, .17)
    fy = gaps(by0, by1, ny, .11, .17)
    z = 2.75
    C.framed_block(g, bx0, by0, bx1, by1, HALL_TOP, HALL_EAVE, infill=ORANGE, frame=WOOD, pitch=.98,
                   windows={'front': [(fx[0], z, 1.55, 'lancet'), (fx[-1], z, 1.55, 'lancet')],
                            'left': [(y, z, 1.55, 'lancet') for y in fy],
                            'right': [(y, z, 1.55, 'lancet') for y in fy],
                            'back': [(fx[0], z, 1.55, 'lancet')]})
    plank_gable(g, bx0, by0, bx1, by1, HALL_EAVE, HALL_EAVE + 1.4, overhang=.16, gable_mat=ORANGE)
    reading_lantern(g)
    portico(g)


def reading_lantern(g):
    lx0, lx1, ly0, ly1 = 1.72, 3.28, 2.6, 3.4
    zb, zt = 5.1, 6.5
    blk(g, lx0, ly0, zb, lx1, ly1, zt, PLANK)
    for x in (lx0, lx1):
        for y in (ly0, ly1):
            blk(g, x - .06, y - .06, 5.45, x + .06, y + .06, zt - .02, IRON)
    glass_curtain(g, 2.5, ly0, 5.85, 6.38, 1.4, 'front', cols=4, rows=1)
    glass_curtain(g, 2.5, ly1, 5.85, 6.38, 1.4, 'back', cols=4, rows=1)
    glass_curtain(g, lx0, 3.0, 6.0, 6.38, .62, 'left', cols=2, rows=1)
    glass_curtain(g, lx1, 3.0, 6.0, 6.38, .62, 'right', cols=2, rows=1)
    plank_gable(g, lx0, ly0, lx1, ly1, zt, zt + .5, overhang=.12, gable_mat=PLANK)


def portico(g):
    """Wall lamps either side of the door. (The columned museum portico in
    front of the hall was removed: the hall front is the footprint edge.)"""
    for x in (1.12, 3.88):
        K.lamp(g, x, HALL[1], 1.0, face='front')

# ---------------------------------------------------------------- stack tower and catalogue wing

def stacks(g, parts):
    x0, y0, x1, y1 = REAR
    C.podium(g, x0, y0, x1, y1, REAR_TOP, foot=False)
    for y in (5.5, 6.5, 7.5, 8.5):
        atlas_window(g, x0, y, .65, .45, 'left', 'grid9')
    for x in (.5, 1.5, 3.5, 4.5):
        atlas_window(g, x, y1, .65, .45, 'back', 'grid9')
    # Stack tower: concrete frame, orange infill, floor bands, paired slits.
    tx0, ty0, tx1, ty1 = x0 + .05, y0 + .05, TOWER_X1, y1 - .05
    C.framed_block(g, tx0, ty0, tx1, ty1, REAR_TOP, TOWER_EAVE, infill=ORANGE, frame=CONCRETE, pitch=.95,
                   corner=.2, floors=(3.1, 4.8, 6.5))
    fx = gaps(tx0, tx1, bays(tx0, tx1, .95), .11, .2)
    fy = gaps(ty0, ty1, bays(ty0, ty1, .95), .11, .2)
    storeys = (2.2, 3.95, 5.65, 7.35)
    for z in storeys:
        for y in fy:
            for d in (-.14, .14):
                atlas_window(g, tx0, y + d, z, .2, 'left', 'slit')
        for x in fx:
            for d in (-.14, .14):
                atlas_window(g, x + d, ty1, z, .2, 'back', 'slit')
    for z in storeys[2:]:
        for x in fx:
            for d in (-.14, .14):
                atlas_window(g, x + d, ty0, z, .2, 'front', 'slit')
        for y in fy:
            for d in (-.14, .14):
                atlas_window(g, tx1, y + d, z, .2, 'right', 'slit')
    ridge = TOWER_EAVE + 1.5
    P.plank_roof(g, tx0, ty0, tx1, ty1, TOWER_EAVE, ridge, ridge_axis='Y', overhang=.18, plank=.3,
                 gable_mat=ORANGE)
    for y, face in ((ty0 - .025, 'front'), (ty1 + .025, 'back')):
        for d in (-.52, .52):
            atlas_window(g, (tx0 + tx1) / 2 + d, y, 8.62, .36, face, 'porthole')
    # Stove flue on the east slope.
    sx, sy = 2.3, 8.2
    slope_z = TOWER_EAVE + (tx1 - sx) * (ridge - TOWER_EAVE) / ((tx1 - tx0) / 2)
    K.stack(g, sx, sy, slope_z - .1, 1.15, emits='smoke', r=.12, taper=.9, bands=2)
    P.hoop(g, (sx, sy, slope_z + .12), .2, .06, .06, IRON, segments=14)
    # Catalogue wing: card-index grid of nine-pane windows facing the dig.
    wx0, wx1 = TOWER_X1, x1 - .05
    eave = 3.6
    wy0 = ty0 + .08
    C.framed_block(g, wx0, wy0, wx1, ty1, REAR_TOP, eave, infill=ORANGE, frame=WOOD, pitch=.95,
                   faces=('front', 'back', 'right'))
    for y in gaps(wy0, ty1, bays(wy0, ty1, .95), .11, .17):
        for z in (2.0, 2.95):
            atlas_window(g, wx1, y, z, .5, 'right', 'grid9')
    for x in gaps(wx0, wx1, bays(wx0, wx1, .95), .11, .17):
        atlas_window(g, x, ty1, 2.45, .5, 'back', 'grid9')
    high = 4.35
    lean_to(g, wx0, wx1, wy0, ty1, eave, high, low_side='right', overhang=.12, seed=3)
    tri = [(wx0, eave - .01), (wx1, eave - .01), (wx0, high - .02)]
    K.extrude_profile(g, tri, wy0 + .01, wy0 + .09, ORANGE, axis='Y')
    K.extrude_profile(g, tri, ty1 - .09, ty1 - .01, ORANGE, axis='Y')


# ---------------------------------------------------------------- dig

def pit(g, parts):
    # Retaining walls on the tile edges; the archive podiums close the west side.
    blk(g, 5.0, SHED_Y1, 0, 10.0, SHED_Y1 + .3, RIM, CONCRETE)
    blk(g, 9.7, SHED_Y1 + .3, 0, 10.0, 8.1, RIM, CONCRETE)
    blk(g, 5.0, 8.1, 0, 10.0, 9.0, RIM, CONCRETE)
    # Inner terrace ledge, a step down toward the dig floor.
    ix0, iy0, ix1, iy1 = 5.45, 2.75, 9.25, 7.65
    blk(g, 5.0, SHED_Y1 + .3, 0, 9.7, iy0, LEDGE, CONCRETE)
    blk(g, 5.0, iy0, 0, ix0, iy1, LEDGE, CONCRETE)
    blk(g, ix1, iy0, 0, 9.7, iy1, LEDGE, CONCRETE)
    blk(g, 5.0, iy1, 0, 9.7, 8.1, LEDGE, CONCRETE)
    # Timber shoring: boards on the ledge faces, soldier posts and lagging
    # on the walls above it.
    def boards_x(y, xa, xb, z0, z1, out):
        n = max(2, round((xb - xa) / .26))
        w = (xb - xa) / n
        for i in range(n):
            a = xa + i * w + .01
            blk(g, a, min(y, y + out * .03), z0, a + w - .02, max(y, y + out * .03), z1, GREYPLANK)
    def boards_y(x, ya, yb, z0, z1, out):
        n = max(2, round((yb - ya) / .26))
        w = (yb - ya) / n
        for i in range(n):
            a = ya + i * w + .01
            blk(g, min(x, x + out * .03), a, z0, max(x, x + out * .03), a + w - .02, z1, GREYPLANK)
    boards_x(iy0, ix0, ix1, .03, LEDGE - .03, 1)
    boards_x(iy1, ix0, ix1, .03, LEDGE - .03, -1)
    boards_y(ix0, iy0 + .03, iy1 - .03, .03, LEDGE - .03, 1)
    boards_y(ix1, iy0 + .03, iy1 - .03, .03, LEDGE - .03, -1)
    wy0, wx1, wy1 = SHED_Y1 + .3, 9.7, 8.1
    for x in (5.7, 6.5, 8.3, 9.1):
        blk(g, x - .05, wy0, LEDGE, x + .05, wy0 + .06, RIM - .02, WOOD)
    for x in (5.7, 6.5, 7.3, 8.1, 8.9):
        blk(g, x - .05, wy1 - .06, LEDGE, x + .05, wy1, RIM - .02, WOOD)
    for y in (3.1, 3.9, 4.7, 5.5, 6.3, 7.1, 7.8):
        blk(g, wx1 - .06, y - .05, LEDGE, wx1, y + .05, RIM - .02, WOOD)
    blk(g, 5.0, wy0, LEDGE + .06, wx1, wy0 + .02, RIM - .08, GREYPLANK)
    blk(g, 5.0, wy1 - .02, LEDGE + .06, wx1, wy1, RIM - .08, GREYPLANK)
    blk(g, wx1 - .02, wy0 + .02, LEDGE + .06, wx1, wy1 - .02, RIM - .08, GREYPLANK)
    # Safety rails on the rim.
    C.rail(g, (5.95, SHED_Y1 + .15), (7.25, SHED_Y1 + .15), RIM)
    C.rail(g, (9.85, SHED_Y1 + .5), (9.85, 7.95), RIM)
    relics(g)
    string_grid(g)


def relics(g):
    """The vanished humans' ruin: a giant cogwheel standing on edge in a
    spoil mound, a broken fluted column with rebar and a fallen drum."""
    cx, cy, cz = GEAR
    r = GEAR_R
    P.hoop(g, (cx, cy, cz), r - .1, .16, .22, IRON, axis='X', segments=16)
    teeth = 18
    for k in range(teeth):
        a = (k + .5) * 2 * math.pi / teeth
        if math.sin(a) * (r - .02) + cz < .3:
            continue
        p = (cx, cy + math.cos(a) * (r - .14), cz + math.sin(a) * (r - .14))
        q = (cx, cy + math.cos(a) * (r + .06), cz + math.sin(a) * (r + .06))
        g.beam(p, q, .17, .14, IRON)
    P.lathe(g, (cx, cy, cz), [(.24, -.16), (.24, .16)], IRON, axis='X', segments=16)
    P.lathe(g, (cx, cy, cz), [(.1, -.2), (.1, .2)], BRASS, axis='X', segments=10)
    for k in range(5):
        a = k * 2 * math.pi / 5 + .3
        g.beam((cx, cy + math.cos(a) * .22, cz + math.sin(a) * .22),
               (cx, cy + math.cos(a) * (r - .22), cz + math.sin(a) * (r - .22)), .1, .16, IRON)
    ore_heap(g, cx, cy, 0, .7, 1.5, h=1.3, mats=(GREYPLANK, IRON, CONCRETE), seed=31)
    # Spoil heaps and duckboards on the dig floor.
    ore_heap(g, 8.85, 3.25, 0, .3, .35, h=.5, mats=(GREYPLANK, CONCRETE), seed=32)
    ore_heap(g, 9.0, 4.0, 0, .2, .2, h=.45, mats=(GREYPLANK, IRON), seed=35)
    for k in range(5):
        y = 3.0 + k * .28
        blk(g, 7.5, y, 0, 8.4, y + .22, .045, GREYWOOD)
    # Broken fluted column with rebar.
    px, py = 8.6, 6.9
    K.revolve(g, (px, py, 0), [(.36, 0), (.36, .12), (.3, .18)], CONCRETE, segments=16)
    K.revolve(g, (px, py, .18), [(.28, 0), (.28, .95)], CONCRETE, segments=16)
    for k in range(8):
        a = k * math.pi / 4
        blk(g, px + math.cos(a) * .27 - .035, py + math.sin(a) * .27 - .035, .2,
            px + math.cos(a) * .27 + .035, py + math.sin(a) * .27 + .035, 1.08 + (k % 3) * .12, CONCRETE)
    blk(g, px - .2, py - .16, 1.1, px + .1, py + .18, 1.33, CONCRETE)
    blk(g, px - .05, py - .2, 1.1, px + .2, py + .1, 1.22, CONCRETE)
    for k, (dx, dy, tx, ty, tz) in enumerate(((-.12, -.08, -.3, -.2, 1.85), (.08, .1, .25, .3, 1.75),
                                              (.1, -.12, .35, -.15, 1.6), (-.1, .12, -.2, .35, 1.9))):
        g.beam((px + dx, py + dy, 1.0), (px + tx, py + ty, tz), .03, mat=IRON)
    # Fallen column drum and scattered finds.
    g.cylinder((8.35, 5.6, .28), .28, .8, CONCRETE, 'X', 16)
    for k in range(6):
        a = k * math.pi / 3
        g.box((8.35, 5.6 + math.cos(a) * .27, .28 + math.sin(a) * .27), (.82, .05, .05), CONCRETE)
    blk(g, 7.15, 4.55, 0, 7.95, 5.4, .05, GREYWOOD)      # bucket landing boards
    for k in range(4):
        blk(g, 7.19 + k * .19, 4.57, .05, 7.33 + k * .19, 5.38, .065, WOOD)


def string_grid(g):
    xs = (5.65, 6.1, 6.55, 7.0)
    ys = (2.95, 3.45, 3.95, 4.45)
    z = .27
    for x in xs:
        for y in ys:
            blk(g, x - .02, y - .02, 0, x + .02, y + .02, .33, WOOD)
    for y in ys:
        g.beam((xs[0] + .02, y, z), (xs[-1] - .02, y, z), .016, mat=CONCRETE)
    for x in xs:
        g.beam((x, ys[0] + .02, z + .025), (x, ys[-1] - .02, z + .025), .016, mat=CONCRETE)
    # Finds lifted in two squares: a brass cog and a riveted casing.
    P.lathe(g, (5.88, 3.2, 0), [(.11, 0), (.11, .05)], BRASS, segments=12)
    blk(g, 6.65, 3.6, 0, 6.9, 3.8, .12, PAINTED)
    blk(g, 6.2, 4.1, 0, 6.45, 4.3, .08, IRON)


# ---------------------------------------------------------------- derrick

def derrick(g, parts):
    feet = ((5.6, SHED_Y1 + .15), (9.4, SHED_Y1 + .15), (7.0, 8.55))
    x0, x1, y0, y1, z0, z1 = CROSS
    tops = ((x0 + .08, y0 + .08, z0), (x1 - .08, y0 + .08, z0), ((x0 + x1) / 2, y1 - .08, z0))
    for (fx, fy), top in zip(feet, tops):
        blk(g, fx - .17, fy - .14, RIM, fx + .17, fy + .14, RIM + .12, IRON)
        P.tube(g, (fx, fy, RIM + .06), top, .1, IRON, segments=12)
        for t in (.25, .55, .8):
            p = tuple(a + (b - a) * t for a, b in zip((fx, fy, RIM + .06), top))
            d = [b - a for a, b in zip((fx, fy, RIM + .06), top)]
            L = math.sqrt(sum(v * v for v in d))
            P.tube(g, tuple(p[i] - d[i] / L * .04 for i in range(3)), tuple(p[i] + d[i] / L * .04 for i in range(3)),
                   .125, PAINTED, segments=12)
    # Crosshead, sheave yoke and beacon.
    blk(g, x0, y0, z0, x1, y1, z1, FORGED)
    blk(g, x0 - .03, y0 - .03, z1, x1 + .03, y1 + .03, z1 + .05, IRON)
    sx, sy, sz = SHEAVE
    for dx in (-.14, .14):
        blk(g, sx + dx - .02, sy - .2, sz - .12, sx + dx + .02, sy + .2, z0, IRON)
    g.cylinder((sx, sy, sz), .05, .37, IRON, 'X', 10)
    sheave = P.flywheel('ArchiveExcavation.Sheave', (sx, sy, sz), SHEAVE_R, axis='X', spokes=6, rim_mat=IRON,
                        width=.1)
    parts.append((sheave, 'SPIN_X', -2))
    pivot = K.beacon(g, sx, sy, z1 + .05)
    parts.append((K.beacon_shutter(*pivot, 'ArchiveExcavation.Beacon'), 'SPIN_Z', 2))
    # Hoist bucket and its rope.
    bx, by = BUCKET
    b = Geometry('ArchiveExcavation.HoistBucket', (bx, by, BUCKET_REST))
    z = BUCKET_REST
    P.lathe(b, (bx, by, z), [(.2, 0), (.28, .5), (.31, .5), (.31, .55)], IRON, segments=16)
    K.band(b, (bx, by, 0), .24, z + .25, .05, PAINTED, segments=16)
    for s in (-1, 1):
        b.cylinder((bx + s * .3, by, z + .42), .04, .08, IRON, 'X', 8)
        b.beam((bx + s * .32, by, z + .42), (bx + s * .05, by, z + .8), .03, mat=IRON)
    b.beam((bx - .06, by, z + .8), (bx + .06, by, z + .8), .04, mat=IRON)
    P.hoop(b, (bx, by, z + .86), .06, .02, .02, IRON, axis='Y', segments=10)
    b.rock((bx, by, z + .55), (.36, .3, .16), GREYPLANK, 5)
    parts.append((b, 'SLIDE_Z', -BUCKET_TRAVEL))
    hook = BUCKET_REST + .9
    rope = Geometry('ArchiveExcavation.HoistRope', (bx, by, sz))
    blk(rope, bx - .015, by - .015, hook, bx + .015, by + .015, sz, IRON)
    parts.append((rope, 'CUSTOM_CABLE', (BUCKET_TRAVEL, sz - hook)))
    # Winch on the back wall and its rope to the sheave.
    wx, wy, wz = WINCH
    for x in (wx - .3, wx + .3):
        blk(g, x - .03, wy - .18, RIM, x + .03, wy + .18, wz + .08, IRON)
    blk(g, wx - .36, wy - .22, RIM, wx + .36, wy + .22, RIM + .1, IRON)
    drum = Geometry('ArchiveExcavation.WinchDrum', (wx, wy, wz))
    P.lathe(drum, (wx, wy, wz), [(.3, -.26), (.3, -.22), (.22, -.22), (.22, .22), (.3, .22), (.3, .26)], PAINTED,
            axis='X', segments=18)
    for k in range(6):
        drum.box((wx, wy + math.cos(k * math.pi / 3) * .225, wz + math.sin(k * math.pi / 3) * .225),
                 (.4, .025, .025), IRON)
    parts.append((drum, 'SPIN_X', 2))
    g.cylinder((wx + .5, wy, wz), .05, .5, IRON, 'X', 10)
    blk(g, wx + .72, wy - .12, RIM, wx + .78, wy + .12, wz + .06, IRON)
    fly = P.flywheel('ArchiveExcavation.WinchFlywheel', (wx + .62, wy, wz), .38, axis='X', spokes=6)
    parts.append((fly, 'SPIN_X', 2))
    blk(g, wx + 1.0, wy - .25, RIM, wx + 1.7, wy + .25, RIM + .55, PAINTED)
    P.motor(g, (wx + 1.35, wy, RIM + .72), .17, .4, axis='X')
    g.beam((sx, sy + SHEAVE_R, sz), (wx, wy - .05, wz + .22), .03, mat=IRON)


# ---------------------------------------------------------------- sieving shed

def shed(g, parts):
    base = .15
    blk(g, 5.05, 0, -.02, 10.0, SHED_Y1, base, CONCRETE)
    posts = ((5.35, .3), (7.6, .3), (9.7, .3), (5.35, 1.75), (9.7, 1.75))
    z_lo, z_hi = 2.4, 2.75
    for x, y in posts:
        P.pier(g, x, y, base - .03, base + .25, .26)
        top = z_lo + (z_hi - z_lo) * (y - .3) / 1.45
        blk(g, x - .07, y - .07, base + .3, x + .07, y + .07, top - .02, IRON)
    blk(g, 5.25, .23, z_lo - .02, 9.8, .37, z_lo + .1, IRON)
    blk(g, 5.25, 1.68, z_hi - .02, 9.8, 1.82, z_hi + .1, IRON)
    lean_to(g, 5.25, 9.8, .3, 1.75, z_lo + .1, z_hi + .1, low_side='front', overhang=.12, seed=7)
    for i, cx in enumerate((6.3, 8.6)):
        sieve(g, parts, i, cx, 1.0, base)
    # Sorting table with finds between the sieves.
    tx0, tx1, ty0, ty1 = 7.08, 7.82, .72, 1.28
    for x in (tx0 + .05, tx1 - .05):
        for y in (ty0 + .05, ty1 - .05):
            blk(g, x - .03, y - .03, base, x + .03, y + .03, .68, GREYWOOD)
    blk(g, tx0, ty0, .68, tx1, ty1, .74, GREYWOOD)
    P.lathe(g, (7.25, .9, .74), [(.09, 0), (.09, .04)], BRASS, segments=12)
    blk(g, 7.4, .82, .74, 7.7, 1.02, .86, PAINTED)
    blk(g, 7.2, 1.06, .74, 7.36, 1.2, .82, IRON)
    # Spoil belt on the pit rim and its chute into the far sieve.
    y = SHED_Y1 + .15
    bx0, bx1 = 7.75, 9.1
    for x in (bx0 + .1, bx1 - .1):
        blk(g, x - .04, y - .1, RIM, x + .04, y + .1, RIM + .12, IRON)
    blk(g, bx0, y - .13, RIM + .12, bx1, y + .13, RIM + .2, IRON)
    blk(g, bx0 + .02, y - .1, RIM + .2, bx1 - .02, y + .1, RIM + .22, PAINTED)
    C.hopper(g, bx0 + .15, y, RIM + .22, RIM + .54, .2, .1)
    belt = Geometry('ArchiveExcavation.SpoilBelt', (8.4, y, RIM + .22))
    pitch = .34
    for k in range(4):
        belt.rock((bx0 + .35 + k * pitch, y, RIM + .27), (.16, .13, .1), GREYPLANK if k % 2 else CONCRETE, 40 + k)
    parts.append((belt, 'CUSTOM_LOOP_X', pitch))
    g.beam((bx1 + .05, y, RIM + .2), (8.95, 1.35, 1.05), .2, .06, FORGED)
    # Lamp at the shed corner.
    K.lamp(g, 9.7, .23, 1.9, face='front')


def sieve(g, parts, i, cx, cy, base):
    for dx in (-.5, .5):
        for dy in (-.28, .28):
            blk(g, cx + dx - .035, cy + dy - .035, base, cx + dx + .035, cy + dy + .035, .84, GREYWOOD)
        blk(g, cx + dx - .04, cy - .32, .8, cx + dx + .04, cy + .32, .85, GREYWOOD)
    blk(g, cx - .25, cy - .2, base, cx + .25, cy + .2, .5, WOOD)
    ore_heap(g, cx, cy, .5, .18, .14, h=.2, mats=(GREYPLANK,), seed=50 + i, count=4)
    t = Geometry(f'ArchiveExcavation.Sieve{i + 1}', (cx, cy, .93))
    w, d = .62, .36
    for s in (-1, 1):
        blk(t, cx - w, cy + s * d - .03, .86, cx + w, cy + s * d + .03, 1.0, GREYWOOD)
        blk(t, cx + s * w - .03, cy - d + .03, .86, cx + s * w + .03, cy + d - .03, 1.0, GREYWOOD)
    for k in range(11):
        x = cx - w + .1 + k * (2 * w - .2) / 10
        blk(t, x - .01, cy - d + .03, .9, x + .01, cy + d - .03, .915, IRON)
    blk(t, cx - w + .03, cy - .01, .915, cx + w - .03, cy + .01, .93, IRON)
    t.rock((cx - .15, cy, .95), (.3, .22, .08), GREYPLANK, 60 + i)
    parts.append((t, 'PISTON_X', .05))


# ---------------------------------------------------------------- yard

def build(g, parts):
    hall(g, parts)
    stacks(g, parts)
    pit(g, parts)
    derrick(g, parts)
    shed(g, parts)
