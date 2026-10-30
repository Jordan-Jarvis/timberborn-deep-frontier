"""ArchiveExcavation: digs relics of the vanished humans out of the ground

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the columned portico and the planting.
(RecoveredArtifact) and catalogues them (ArchiveData).

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; one layer per floor, flat roofs, no clutter on buildable space):
10x9x11 -> 7x6x6, inside the old footprint with the same origin, door,
doorstep and native entrance (the free tile in front of the door). Removed:
the steep gable on the 8-layer archive stack (now a 4-layer flat-roofed
tower), the hall's gable roof and glazed reading lantern, the catalogue
wing's lean-to, the tall 8-layer tripod derrick (now 5 layers) and the
sorting table; the dig, the sieving shed and the winch are smaller.

HERO: an excavation pit inside concrete retaining walls, exposing a giant
rusted human cogwheel half-buried in spoil beside a broken fluted column,
laid out with an archaeologist's string grid and worked by a riveted steel
tripod derrick with a hoist bucket.
ROOFS (roof variety, user 2026-10-30): a gabled roof of native barracks roof
planks on the archive hall; flat parapet roofs on the archive stack tower
(concrete) and the catalogue wing (timber plank deck); a flat roof over the
open sieving shed. No roof vents: the stove flue rises up the tower's corner.

Plan (7 x 6 tiles): archive hall front-left with the door (the tile in front
of it is the entrance); the archive stack tower and catalogue wing behind it;
the pit across the right (tiles 4..7 x 1..6) with the winch on its thick back
wall; the open sieving shed along the front right, fed by a spoil belt on
the pit rim.

Distinct from the quarries and pits (timber box headframe and winding drum,
gallows crane): a three-legged steel derrick, a terraced dig with shoring
and string lines, and an exposed ruin instead of a rock face.

Animated (9, same names): hoist bucket (SLIDE_Z) with its paying-out rope
(CUSTOM_CABLE), crown sheave (SPIN_X), winch drum and flywheel (SPIN_X), two
shaking sieves (PISTON_X), spoil belt (CUSTOM_LOOP_X), derrick beacon
(SPIN_Z).

No pipe port: neither recipe uses a liquid.
Smoke: the archive stack's stove flue is a kit wall stack (from the podium).
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
import lategame_mining_parts as MP
from lategame_roofdeck_parts import parapet_ring
from native_window_atlas import atlas_window
import native_building_assets as N

IDENT = 'ArchiveExcavation'
FOOTPRINT = (7, 6)
HEIGHT = 6
FRAME_END = 121
HERO = ('Excavation pit exposing a giant rusted human cogwheel half-buried beside a broken fluted column, '
        'laid out with string lines and worked by a steel tripod derrick and hoist bucket.')

HALL = (0.0, 1.0, 4.0, 4.0)        # archive hall podium (whole tiles)
HALL_TOP, HALL_EAVE = .5, 1.84
REAR = (0.0, 4.1, 4.0, 6.0)        # stack tower + catalogue wing podium (coping meets the hall's on an edge)
REAR_TOP = .5
TOWER_X1 = 2.0
TOWER_EAVE = 3.84
WING_EAVE = 1.84
ROOF_T = .16
RIM = 1.0                          # pit retaining wall top
LEDGE = .4                         # inner terrace
SHED_Y1 = 1.0
CROSS = (5.2, 5.9, 3.0, 3.5, 4.55, 4.75)     # derrick crosshead x0 x1 y0 y1 z0 z1
SHEAVE = (5.55, 3.25, 4.2)
SHEAVE_R = .26
BUCKET = (5.55, SHEAVE[1] - SHEAVE_R)      # rope line under the front of the sheave
BUCKET_REST, BUCKET_TRAVEL = 2.75, 2.6
WINCH = (4.85, 5.7, RIM + .4)
GEAR = (5.1, 4.45, 1.0)
GEAR_R = 1.0


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


def bays(a, b, pitch):
    return max(1, round((b - a) / pitch))


def flat_roof(g, x0, y0, x1, y1, z, open_sides=(), deck='concrete'):
    """Roof slab on the block's top, concrete or a timber plank deck (roof
    variety, user 2026-10-30), and a ring parapet (no lid), so the roof stays
    a usable deck (lategame_roofdeck_parts)."""
    if deck == 'concrete':
        blk(g, x0 - .05, y0 - .05, z, x1 + .05, y1 + .05, z + ROOF_T, CONCRETE)
    elif deck == 'timber':
        MP.plank_deck(g, x0 - .05, x1 + .05, y0 - .05, y1 + .05, z + ROOF_T, t=ROOF_T, seed=37)
    else:
        raise ValueError(f'Unknown archive roof deck {deck!r}')
    parapet_ring(g, x0 - .05, y0 - .05, x1 + .05, y1 + .05, z + ROOF_T, open_sides=open_sides)


# ---------------------------------------------------------------- archive hall

def hall(g, parts):
    x0, y0, x1, y1 = HALL
    C.podium(g, x0, y0, x1, y1, HALL_TOP, skip=[(2.0, 3.0)])
    C.door(g, 2.5, y0, 0, 'Door0')
    for x in (.6, 3.4):
        atlas_window(g, x, y0, .3, .32, 'front', 'grid9')
    for y in (1.5, 2.5, 3.5):
        atlas_window(g, x0, y, .3, .32, 'left', 'grid9')
    bx0, by0, bx1, by1 = x0 + .05, y0 + .05, x1 - .05, y1 - .05
    nx, ny = bays(bx0, bx1, .98), bays(by0, by1, .98)
    fx = gaps(bx0, bx1, nx, .11, .17)
    fy = gaps(by0, by1, ny, .11, .17)
    z = 1.17
    C.framed_block(g, bx0, by0, bx1, by1, HALL_TOP, HALL_EAVE, infill=ORANGE, frame=WOOD, pitch=.98,
                   windows={'front': [(fx[0], z, .85, 'lancet'), (fx[-1], z, .85, 'lancet')],
                            'left': [(y, z, .85, 'lancet') for y in fy],
                            'right': [(fy[0], z, .85, 'lancet')]})
    # A real gabled roof in the native barracks roof planks over the hall
    # (roof variety, user 2026-10-30: "some buildings can have actual roofs").
    MP.plank_gable(g, bx0, bx1, by0, by1, HALL_EAVE, 2.75, ridge_axis='X', overhang=.05, seed=31)
    # No wall lamps beside the door: they would claim the open tiles (1, 0) and (3, 0).


# ---------------------------------------------------------------- stack tower and catalogue wing

def stacks(g, parts):
    x0, y0, x1, y1 = REAR
    C.podium(g, x0, y0, x1, y1, REAR_TOP, foot=False)
    for y in (4.5, 5.5):
        atlas_window(g, x0, y, .3, .32, 'left', 'grid9')
    for x in (.5, 1.5, 2.5, 3.5):
        atlas_window(g, x, y1, .3, .32, 'back', 'grid9')
    # Stack tower: concrete frame, orange infill, a floor band per layer, paired slits.
    tx0, ty0, tx1, ty1 = x0 + .05, y0 + .05, TOWER_X1, y1 - .05
    C.framed_block(g, tx0, ty0, tx1, ty1, REAR_TOP, TOWER_EAVE, infill=ORANGE, frame=CONCRETE, pitch=.95,
                   corner=.2, floors=(1.84, 2.84))
    fx = gaps(tx0, tx1, bays(tx0, tx1, .95), .11, .2)
    fy = gaps(ty0, ty1, bays(ty0, ty1, .95), .11, .2)
    for z in (1.2, 2.35, 3.35):
        for y in fy:
            for d in (-.14, .14):
                atlas_window(g, tx0, y + d, z, .2, 'left', 'slit')
        for x in fx:
            for d in (-.14, .14):
                atlas_window(g, x + d, ty1, z, .2, 'back', 'slit')
    for z in (2.35, 3.35):
        for x in fx:
            for d in (-.14, .14):
                atlas_window(g, x + d, ty0, z, .2, 'front', 'slit')
        for y in fy:
            for d in (-.14, .14):
                atlas_window(g, tx1, y + d, z, .2, 'right', 'slit')
    flat_roof(g, tx0, ty0, tx1, ty1, TOWER_EAVE)
    # Stove flue up the tower's back-left corner from the podium (no roof vents,
    # user 2026-10-30), in the roof cell's outer band, mouth at its old height.
    K.wall_stack(g, .16, 5.84, REAR_TOP, TOWER_EAVE + ROOF_T + 1.0 - REAR_TOP, emits='smoke', r=.11, bands=3)
    # Catalogue wing: card-index grid of nine-pane windows facing the dig.
    wx0, wx1 = TOWER_X1, x1 - .05
    wy0 = ty0 + .08
    C.framed_block(g, wx0, wy0, wx1, ty1, REAR_TOP, WING_EAVE, infill=ORANGE, frame=WOOD, pitch=.95,
                   faces=('front', 'back', 'right'))
    for y in gaps(wy0, ty1, bays(wy0, ty1, .95), .11, .17):
        atlas_window(g, wx1, y, 1.17, .5, 'right', 'grid9')
    for x in gaps(wx0, wx1, bays(wx0, wx1, .95), .11, .17):
        atlas_window(g, x, ty1, 1.17, .5, 'back', 'grid9')
    flat_roof(g, wx0 + .05, wy0, wx1, ty1, WING_EAVE, open_sides=('left',), deck='timber')


# ---------------------------------------------------------------- dig

def pit(g, parts):
    # Retaining walls on the tile edges; the archive podiums close the west side.
    # The back wall is thick: the winch stands on it.
    blk(g, 4.0, SHED_Y1, 0, 7.0, SHED_Y1 + .3, RIM, CONCRETE)
    blk(g, 6.7, SHED_Y1 + .3, 0, 7.0, 5.3, RIM, CONCRETE)
    blk(g, 4.0, 5.3, 0, 7.0, 6.0, RIM, CONCRETE)
    # Inner terrace ledge, a step down toward the dig floor.
    ix0, iy0, ix1, iy1 = 4.4, 1.7, 6.3, 4.95
    blk(g, 4.0, SHED_Y1 + .3, 0, 6.7, iy0, LEDGE, CONCRETE)
    blk(g, 4.0, iy0, 0, ix0, iy1, LEDGE, CONCRETE)
    blk(g, ix1, iy0, 0, 6.7, iy1, LEDGE, CONCRETE)
    blk(g, 4.0, iy1, 0, 6.7, 5.3, LEDGE, CONCRETE)
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
    wy0, wx1, wy1 = SHED_Y1 + .3, 6.7, 5.3
    for x in (4.6, 5.4, 6.2):
        blk(g, x - .05, wy0, LEDGE, x + .05, wy0 + .06, RIM - .02, WOOD)
        blk(g, x - .05, wy1 - .06, LEDGE, x + .05, wy1, RIM - .02, WOOD)
    for y in (2.1, 2.9, 3.7, 4.5):
        blk(g, wx1 - .06, y - .05, LEDGE, wx1, y + .05, RIM - .02, WOOD)
    blk(g, 4.0, wy0, LEDGE + .06, wx1, wy0 + .02, RIM - .08, GREYPLANK)
    blk(g, 4.0, wy1 - .02, LEDGE + .06, wx1, wy1, RIM - .08, GREYPLANK)
    blk(g, wx1 - .02, wy0 + .02, LEDGE + .06, wx1, wy1 - .02, RIM - .08, GREYPLANK)
    # Safety rail on the right rim.
    C.rail(g, (6.85, SHED_Y1 + .5), (6.85, 5.15), RIM)
    relics(g)
    string_grid(g)


def relics(g):
    """The vanished humans' ruin: a giant cogwheel standing on edge in a
    spoil mound, a broken fluted column with rebar and a fallen drum."""
    cx, cy, cz = GEAR
    r = GEAR_R
    P.hoop(g, (cx, cy, cz), r - .08, .13, .18, IRON, axis='X', segments=16)
    teeth = 16
    for k in range(teeth):
        a = (k + .5) * 2 * math.pi / teeth
        if math.sin(a) * (r - .02) + cz < .3:
            continue
        p = (cx, cy + math.cos(a) * (r - .11), cz + math.sin(a) * (r - .11))
        q = (cx, cy + math.cos(a) * (r + .05), cz + math.sin(a) * (r + .05))
        g.beam(p, q, .14, .11, IRON)
    P.lathe(g, (cx, cy, cz), [(.2, -.13), (.2, .13)], IRON, axis='X', segments=16)
    P.lathe(g, (cx, cy, cz), [(.08, -.17), (.08, .17)], BRASS, axis='X', segments=10)
    for k in range(5):
        a = k * 2 * math.pi / 5 + .3
        g.beam((cx, cy + math.cos(a) * .18, cz + math.sin(a) * .18),
               (cx, cy + math.cos(a) * (r - .18), cz + math.sin(a) * (r - .18)), .08, .13, IRON)
    ore_heap(g, cx, cy, 0, .55, .45, h=1.0, mats=(GREYPLANK, IRON, CONCRETE), seed=31)
    # Broken fluted column with rebar.
    px, py = 6.0, 2.25
    K.revolve(g, (px, py, 0), [(.3, 0), (.3, .1), (.25, .15)], CONCRETE, segments=16)
    K.revolve(g, (px, py, .15), [(.23, 0), (.23, .8)], CONCRETE, segments=16)
    for k in range(8):
        a = k * math.pi / 4
        blk(g, px + math.cos(a) * .22 - .03, py + math.sin(a) * .22 - .03, .17,
            px + math.cos(a) * .22 + .03, py + math.sin(a) * .22 + .03, .9 + (k % 3) * .1, CONCRETE)
    blk(g, px - .16, py - .13, .92, px + .08, py + .15, 1.1, CONCRETE)
    for dx, dy, tx, ty, tz in ((-.1, -.06, -.25, -.16, 1.55), (.06, .08, .2, .25, 1.45), (.08, -.1, .28, -.12, 1.35)):
        g.beam((px + dx, py + dy, .85), (px + tx, py + ty, tz), .025, mat=IRON)
    # Fallen column drum and the bucket landing boards.
    g.cylinder((5.95, 3.4, .23), .23, .65, CONCRETE, 'X', 16)
    blk(g, 5.15, 2.55, 0, 5.95, 3.2, .05, GREYWOOD)
    for k in range(4):
        blk(g, 5.19 + k * .19, 2.57, .05, 5.33 + k * .19, 3.18, .065, WOOD)


def string_grid(g):
    xs = (4.6, 5.0, 5.4)
    ys = (1.85, 2.2)
    z = .27
    for x in xs:
        for y in ys:
            blk(g, x - .02, y - .02, LEDGE, x + .02, y + .02, LEDGE + .33, WOOD)
    for y in ys:
        g.beam((xs[0] + .02, y, LEDGE + z), (xs[-1] - .02, y, LEDGE + z), .016, mat=CONCRETE)
    for x in xs:
        g.beam((x, ys[0] + .02, LEDGE + z + .025), (x, ys[-1] - .02, LEDGE + z + .025), .016, mat=CONCRETE)


# ---------------------------------------------------------------- derrick

def derrick(g, parts):
    feet = ((4.25, SHED_Y1 + .15), (6.85, SHED_Y1 + .15), (5.55, 5.65))
    x0, x1, y0, y1, z0, z1 = CROSS
    tops = ((x0 + .08, y0 + .08, z0), (x1 - .08, y0 + .08, z0), ((x0 + x1) / 2, y1 - .08, z0))
    for (fx, fy), top in zip(feet, tops):
        blk(g, fx - .14, fy - .12, RIM, fx + .14, fy + .12, RIM + .1, IRON)
        P.tube(g, (fx, fy, RIM + .05), top, .08, IRON, segments=12)
        for t in (.35, .7):
            p = tuple(a + (b - a) * t for a, b in zip((fx, fy, RIM + .05), top))
            d = [b - a for a, b in zip((fx, fy, RIM + .05), top)]
            L = math.sqrt(sum(v * v for v in d))
            P.tube(g, tuple(p[i] - d[i] / L * .035 for i in range(3)), tuple(p[i] + d[i] / L * .035 for i in range(3)),
                   .1, PAINTED, segments=12)
    # Crosshead, sheave yoke and beacon.
    blk(g, x0, y0, z0, x1, y1, z1, FORGED)
    blk(g, x0 - .03, y0 - .03, z1, x1 + .03, y1 + .03, z1 + .05, IRON)
    sx, sy, sz = SHEAVE
    for dx in (-.12, .12):
        blk(g, sx + dx - .02, sy - .17, sz - .1, sx + dx + .02, sy + .17, z0, IRON)
    g.cylinder((sx, sy, sz), .045, .32, IRON, 'X', 10)
    sheave = P.flywheel('ArchiveExcavation.Sheave', (sx, sy, sz), SHEAVE_R, axis='X', spokes=6, rim_mat=IRON,
                        width=.09)
    parts.append((sheave, 'SPIN_X', -2))
    pivot = K.beacon(g, sx, sy, z1 + .05)
    parts.append((K.beacon_shutter(*pivot, 'ArchiveExcavation.Beacon'), 'SPIN_Z', 2))
    # Hoist bucket and its rope.
    bx, by = BUCKET
    b = Geometry('ArchiveExcavation.HoistBucket', (bx, by, BUCKET_REST))
    z = BUCKET_REST
    P.lathe(b, (bx, by, z), [(.17, 0), (.24, .42), (.27, .42), (.27, .47)], IRON, segments=16)
    K.band(b, (bx, by, 0), .2, z + .21, .045, PAINTED, segments=16)
    for s in (-1, 1):
        b.cylinder((bx + s * .26, by, z + .36), .035, .07, IRON, 'X', 8)
        b.beam((bx + s * .28, by, z + .36), (bx + s * .045, by, z + .7), .026, mat=IRON)
    b.beam((bx - .05, by, z + .7), (bx + .05, by, z + .7), .035, mat=IRON)
    P.hoop(b, (bx, by, z + .75), .05, .018, .018, IRON, axis='Y', segments=10)
    b.rock((bx, by, z + .47), (.3, .26, .14), GREYPLANK, 5)
    parts.append((b, 'SLIDE_Z', -BUCKET_TRAVEL))
    hook = BUCKET_REST + .79
    rope = Geometry('ArchiveExcavation.HoistRope', (bx, by, sz))
    blk(rope, bx - .015, by - .015, hook, bx + .015, by + .015, sz, IRON)
    parts.append((rope, 'CUSTOM_CABLE', (BUCKET_TRAVEL, sz - hook)))
    # Winch on the thick back wall and its rope to the sheave.
    wx, wy, wz = WINCH
    for x in (wx - .28, wx + .28):
        blk(g, x - .03, wy - .16, RIM, x + .03, wy + .16, wz + .07, IRON)
    blk(g, wx - .34, wy - .2, RIM, wx + .34, wy + .2, RIM + .09, IRON)
    drum = Geometry('ArchiveExcavation.WinchDrum', (wx, wy, wz))
    P.lathe(drum, (wx, wy, wz), [(.27, -.24), (.27, -.2), (.2, -.2), (.2, .2), (.27, .2), (.27, .24)], PAINTED,
            axis='X', segments=18)
    for k in range(6):
        drum.box((wx, wy + math.cos(k * math.pi / 3) * .205, wz + math.sin(k * math.pi / 3) * .205),
                 (.36, .022, .022), IRON)
    parts.append((drum, 'SPIN_X', 2))
    g.cylinder((wx + .45, wy, wz), .045, .45, IRON, 'X', 10)
    blk(g, wx + .65, wy - .11, RIM, wx + .71, wy + .11, wz + .05, IRON)
    fly = P.flywheel('ArchiveExcavation.WinchFlywheel', (wx + .56, wy, wz), .33, axis='X', spokes=6)
    parts.append((fly, 'SPIN_X', 2))
    blk(g, wx + .9, wy - .22, RIM, wx + 1.5, wy + .22, RIM + .45, PAINTED)
    P.motor(g, (wx + 1.2, wy, RIM + .6), .15, .36, axis='X')
    g.beam((sx, sy + SHEAVE_R, sz), (wx, wy - .05, wz + .2), .03, mat=IRON)


# ---------------------------------------------------------------- sieving shed

def shed(g, parts):
    base = .15
    blk(g, 4.05, 0, -.02, 7.0, SHED_Y1, base, CONCRETE)
    posts = ((4.2, .15), (6.85, .15))
    roof_lo = 1.84
    for x, y in posts:
        P.pier(g, x, y, base - .03, base + .25, .22)
        blk(g, x - .06, y - .06, base + .3, x + .06, y + .06, roof_lo - .12, IRON)
    blk(g, 4.1, .08, roof_lo - .12, 6.95, .22, roof_lo, IRON)
    blk(g, 4.0, 0.0, roof_lo, 7.0, SHED_Y1, roof_lo + ROOF_T, CONCRETE)
    for i, cx in enumerate((4.85, 6.15)):
        sieve(g, parts, i, cx, .55, base)
    # Spoil belt on the pit rim and its chute into the far sieve.
    y = SHED_Y1 + .15
    bx0, bx1 = 5.25, 6.45
    for x in (bx0 + .1, bx1 - .1):
        blk(g, x - .04, y - .1, RIM, x + .04, y + .1, RIM + .12, IRON)
    blk(g, bx0, y - .13, RIM + .12, bx1, y + .13, RIM + .2, IRON)
    blk(g, bx0 + .02, y - .1, RIM + .2, bx1 - .02, y + .1, RIM + .22, PAINTED)
    C.hopper(g, bx0 + .15, y, RIM + .22, RIM + .5, .18, .09)
    belt = Geometry('ArchiveExcavation.SpoilBelt', (5.85, y, RIM + .22))
    pitch = .3
    for k in range(3):
        belt.rock((bx0 + .32 + k * pitch, y, RIM + .27), (.15, .12, .09), GREYPLANK if k % 2 else CONCRETE, 40 + k)
    parts.append((belt, 'CUSTOM_LOOP_X', pitch))
    g.beam((bx1 + .04, y, RIM + .2), (6.35, .8, 1.05), .18, .05, FORGED)


def sieve(g, parts, i, cx, cy, base):
    for dx in (-.42, .42):
        for dy in (-.24, .24):
            blk(g, cx + dx - .03, cy + dy - .03, base, cx + dx + .03, cy + dy + .03, .8, GREYWOOD)
        blk(g, cx + dx - .035, cy - .28, .76, cx + dx + .035, cy + .28, .81, GREYWOOD)
    blk(g, cx - .22, cy - .18, base, cx + .22, cy + .18, .48, WOOD)
    ore_heap(g, cx, cy, .48, .15, .12, h=.18, mats=(GREYPLANK,), seed=50 + i, count=4)
    t = Geometry(f'ArchiveExcavation.Sieve{i + 1}', (cx, cy, .89))
    w, d = .54, .32
    for s in (-1, 1):
        blk(t, cx - w, cy + s * d - .03, .82, cx + w, cy + s * d + .03, .96, GREYWOOD)
        blk(t, cx + s * w - .03, cy - d + .03, .82, cx + s * w + .03, cy + d - .03, .96, GREYWOOD)
    for k in range(9):
        x = cx - w + .1 + k * (2 * w - .2) / 8
        blk(t, x - .01, cy - d + .03, .86, x + .01, cy + d - .03, .875, IRON)
    blk(t, cx - w + .03, cy - .01, .875, cx + w - .03, cy + .01, .89, IRON)
    t.rock((cx - .13, cy, .91), (.26, .2, .07), GREYPLANK, 60 + i)
    parts.append((t, 'PISTON_X', .05))


def build(g, parts):
    hall(g, parts)
    stacks(g, parts)
    pit(g, parts)
    derrick(g, parts)
    shed(g, parts)
