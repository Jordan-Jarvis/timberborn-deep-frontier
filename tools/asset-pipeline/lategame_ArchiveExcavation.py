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

Second shrink 2026-11-01 (a YouTuber called the late-game buildings
"massive"; user: "we need to shrink the buildings down even more"):
7x6x6 -> 4x4x3, inside the old footprint with the same origin, door,
doorstep (2, 1) and native entrance (2, 0): the front row stays open ground
(the entrance tile and the free tiles (1, 0) and (3, 0) beside it, as
before), so the building stands on tiles 0..4 x 1..4, which the old archive
hall covered, and keeps within the hall's three layers. Every new block is
one the old excavation occupied. The dig moved behind the hall: a smaller
pit with the cogwheel and the broken column, a shorter tripod derrick and
the winch on its back wall; the two sieves stand in a one-tile shed beside
the door, fed by the spoil belt on the pit's front rim.

HERO: an excavation pit inside concrete retaining walls, exposing a giant
rusted human cogwheel half-buried in spoil beside a broken fluted column,
worked by a riveted steel tripod derrick with a hoist bucket.
ROOFS (roof variety, user 2026-10-30): a gabled roof of native barracks roof
planks on the one-storey archive hall; flat open roofs (no parapets) on the
archive stack tower (concrete, layer 3) and the sieving shed (timber plank
deck, layer 2). No roof vents: the stove flue rises up the tower's corner.

Plan (4 x 4 tiles): the front row (y 0) open; the archive hall on tiles
0..3 x 1..2 with the door (doorstep (2, 1)); the sieving shed on tile (3, 1);
the stack tower on tiles 0..1 x 2..4; the pit on tiles 1..4 x 2..4 with the
derrick over it and the winch on its back wall.

Distinct from the quarries and pits (timber box headframe and winding drum,
gallows crane): a three-legged steel derrick, a dig with shoring, and an
exposed ruin instead of a rock face.

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
from native_window_atlas import atlas_window
import native_building_assets as N

IDENT = 'ArchiveExcavation'
FOOTPRINT = (4, 4)
HEIGHT = 3
FRAME_END = 121
HERO = ('Excavation pit exposing a giant rusted human cogwheel half-buried beside a broken fluted column, '
        'worked by a steel tripod derrick and hoist bucket.')

HALL = (0.0, 1.0, 3.0, 2.0)        # archive hall podium (whole tiles); door at x 2.5 on y = 1
HALL_TOP, HALL_EAVE = .3, 1.0
SHED = (3.0, 1.0, 4.0, 2.0)
TOWER = (0.0, 2.12, 1.0, 4.0)      # stack tower podium (its coping clears the hall's)
TOWER_TOP = .3
TOWER_EAVE = 1.84
ROOF_T = .16
RIM = .8                           # pit retaining wall top
LEDGE = .3                         # inner terrace
PIT = (1.0, 2.08, 4.0, 4.0)
CROSS = (2.3, 2.8, 2.82, 3.22, 2.46, 2.62)   # derrick crosshead x0 x1 y0 y1 z0 z1
SHEAVE = (2.55, 3.02, 2.2)
SHEAVE_R = .18
BUCKET = (2.55, SHEAVE[1] - SHEAVE_R)      # rope line under the front of the sheave
BUCKET_REST, BUCKET_TRAVEL = 1.25, 1.0
WINCH = (3.0, 3.82, RIM + .3)
GEAR = (1.55, 3.05, .55)
GEAR_R = .6


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


def flat_roof(g, x0, y0, x1, y1, z, deck='concrete'):
    """Roof slab on the block's top, concrete or a timber plank deck (roof
    variety, user 2026-10-30): an open platform edge to edge, no parapet
    (user, 2026-10-31), so paths join across abutting roofs."""
    if deck == 'concrete':
        blk(g, x0 - .05, y0 - .05, z, x1 + .05, y1 + .05, z + ROOF_T, CONCRETE)
    elif deck == 'timber':
        MP.plank_deck(g, x0 - .05, x1 + .05, y0 - .05, y1 + .05, z + ROOF_T, t=ROOF_T, seed=37)
    else:
        raise ValueError(f'Unknown archive roof deck {deck!r}')


# ---------------------------------------------------------------- archive hall

def hall(g, parts):
    """One-storey hall on tiles 0..3 x 1..2 under a gable of native barracks
    roof planks (ridge along X, its top under layer 3)."""
    x0, y0, x1, y1 = HALL
    C.podium(g, x0, y0, x1, y1, HALL_TOP, skip=[(2.0, 3.0)])
    C.door(g, 2.5, y0, 0, 'Door0')
    atlas_window(g, .6, y0, .13, .16, 'front', 'grid9')
    atlas_window(g, x0, 1.5, .13, .16, 'left', 'grid9')
    bx0, by0, bx1, by1 = x0 + .05, y0 + .05, x1 - .05, y1 - .05
    C.framed_block(g, bx0, by0, bx1, by1, HALL_TOP, HALL_EAVE + .45, infill=ORANGE, frame=WOOD, pitch=.98,
                   windows={'front': [(1.2, .95, .6, 'lancet')], 'left': [(1.5, .95, .6, 'lancet')]})
    MP.plank_gable(g, bx0, bx1, by0, by1, HALL_EAVE + .45, 2.2, ridge_axis='X', overhang=.05, seed=31)
    # No wall lamps beside the door: they would claim the open tiles (1, 0) and (3, 0).


# ---------------------------------------------------------------- stack tower

def stacks(g, parts):
    """Archive stack tower on tiles 0..1 x 2..4: two one-layer storeys with
    paired slits and a flat concrete roof on layer 2; the stove flue rises
    against its right wall from the pit ledge, its mouth above the roof."""
    x0, y0, x1, y1 = TOWER
    C.podium(g, x0, y0, x1, y1, TOWER_TOP, foot=False)
    tx0, ty0, tx1, ty1 = x0 + .05, y0 + .05, x1 - .05, y1 - .05
    C.framed_block(g, tx0, ty0, tx1, ty1, TOWER_TOP, TOWER_EAVE, infill=ORANGE, frame=CONCRETE, pitch=.95,
                   corner=.2, floors=(1.0,))
    fy = gaps(ty0, ty1, bays(ty0, ty1, .95), .11, .2)
    for z in (.65, 1.45):
        for y in fy:
            for d in (-.12, .12):
                atlas_window(g, tx0, y + d, z, .18, 'left', 'slit')
        for d in (-.12, .12):
            atlas_window(g, .5 + d, ty1, z, .18, 'back', 'slit')
    for d in (-.12, .12):
        atlas_window(g, .5 + d, ty0, 1.45, .18, 'front', 'slit')
    flat_roof(g, tx0, ty0, tx1, ty1, TOWER_EAVE)
    # Stove flue against the tower's right wall, from the pit ledge (no roof
    # vents), its mouth a layer above the tower roof.
    K.wall_stack(g, 1.1, 3.35, LEDGE, 2.86 - LEDGE, emits='smoke', r=.09, bands=3)


# ---------------------------------------------------------------- dig

def pit(g, parts):
    """Retaining walls on the tile edges behind the hall; the tower closes the
    west side. The back wall is thick: the winch stands on it."""
    x0, y0, x1, y1 = PIT
    blk(g, x0 + .06, y0, 0, x1, y0 + .22, RIM, CONCRETE)          # front wall behind the hall
    blk(g, x1 - .25, y0 + .22, 0, x1, y1 - .5, RIM, CONCRETE)      # right wall
    blk(g, x0 + .06, y1 - .5, 0, x1, y1, RIM, CONCRETE)           # thick back wall
    ix0, iy0, ix1, iy1 = 1.35, 2.55, 3.45, 3.3
    blk(g, x0 + .06, y0 + .22, 0, x1 - .25, iy0, LEDGE, CONCRETE)
    blk(g, x0 + .06, iy0, 0, ix0, iy1, LEDGE, CONCRETE)
    blk(g, ix1, iy0, 0, x1 - .25, iy1, LEDGE, CONCRETE)
    blk(g, x0 + .06, iy1, 0, x1 - .25, y1 - .5, LEDGE, CONCRETE)

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
    wy0, wx1, wy1 = y0 + .22, x1 - .25, y1 - .5
    for x in (1.6, 2.4, 3.2):
        blk(g, x - .04, wy0, LEDGE, x + .04, wy0 + .05, RIM - .02, WOOD)
        blk(g, x - .04, wy1 - .05, LEDGE, x + .04, wy1, RIM - .02, WOOD)
    blk(g, wx1 - .05, 2.9, LEDGE, wx1, 3.0, RIM - .02, WOOD)
    relics(g)


def relics(g):
    """The vanished humans' ruin: a giant cogwheel standing on edge in a
    spoil mound, a broken fluted column with rebar and a fallen drum."""
    cx, cy, cz = GEAR
    r = GEAR_R
    P.hoop(g, (cx, cy, cz), r - .06, .1, .14, IRON, axis='X', segments=16)
    teeth = 14
    for k in range(teeth):
        a = (k + .5) * 2 * math.pi / teeth
        if math.sin(a) * (r - .02) + cz < .3:
            continue
        p = (cx, cy + math.cos(a) * (r - .08), cz + math.sin(a) * (r - .08))
        q = (cx, cy + math.cos(a) * (r + .04), cz + math.sin(a) * (r + .04))
        g.beam(p, q, .11, .09, IRON)
    P.lathe(g, (cx, cy, cz), [(.14, -.1), (.14, .1)], IRON, axis='X', segments=16)
    P.lathe(g, (cx, cy, cz), [(.06, -.13), (.06, .13)], BRASS, axis='X', segments=10)
    for k in range(5):
        a = k * 2 * math.pi / 5 + .3
        g.beam((cx, cy + math.cos(a) * .13, cz + math.sin(a) * .13),
               (cx, cy + math.cos(a) * (r - .13), cz + math.sin(a) * (r - .13)), .06, .1, IRON)
    ore_heap(g, cx, cy, .02, .38, .3, h=.5, mats=(GREYPLANK, IRON, CONCRETE), seed=31)
    # Broken fluted column with rebar.
    px, py = 3.15, 2.85
    K.revolve(g, (px, py, 0.0), [(.2, 0), (.2, .07), (.17, .1)], CONCRETE, segments=16)
    K.revolve(g, (px, py, 0.0 + .1), [(.15, 0), (.15, .5)], CONCRETE, segments=16)
    for k in range(8):
        a = k * math.pi / 4
        blk(g, px + math.cos(a) * .145 - .02, py + math.sin(a) * .145 - .02, 0.0 + .11,
            px + math.cos(a) * .145 + .02, py + math.sin(a) * .145 + .02, 0.0 + .56 + (k % 3) * .06, CONCRETE)
    for dx, dy, tx, ty, tz in ((-.06, -.04, -.16, -.1, 0.0 + .95), (.04, .05, .13, .16, 0.0 + .88)):
        g.beam((px + dx, py + dy, 0.0 + .55), (px + tx, py + ty, tz), .02, mat=IRON)
    # Bucket landing boards on the dig floor.
    blk(g, 2.25, 2.62, 0, 2.85, 3.0, .04, GREYWOOD)
    for k in range(3):
        blk(g, 2.29 + k * .19, 2.64, .04, 2.43 + k * .19, 2.98, .055, WOOD)


# ---------------------------------------------------------------- derrick

def derrick(g, parts):
    feet = ((1.2, 2.25), (3.6, 2.25), (1.9, 3.75))
    x0, x1, y0, y1, z0, z1 = CROSS
    tops = ((x0 + .06, y0 + .06, z0), (x1 - .06, y0 + .06, z0), ((x0 + x1) / 2 - .1, y1 - .06, z0))
    for (fx, fy), top in zip(feet, tops):
        blk(g, fx - .11, fy - .1, RIM, fx + .11, fy + .1, RIM + .08, IRON)
        P.tube(g, (fx, fy, RIM + .04), top, .06, IRON, segments=12)
        p = tuple(a + (b - a) * .5 for a, b in zip((fx, fy, RIM + .04), top))
        d = [b - a for a, b in zip((fx, fy, RIM + .04), top)]
        L = math.sqrt(sum(v * v for v in d))
        P.tube(g, tuple(p[i] - d[i] / L * .03 for i in range(3)), tuple(p[i] + d[i] / L * .03 for i in range(3)),
               .08, PAINTED, segments=12)
    # Crosshead, sheave yoke and beacon.
    blk(g, x0, y0, z0, x1, y1, z1, FORGED)
    blk(g, x0 - .02, y0 - .02, z1, x1 + .02, y1 + .02, z1 + .04, IRON)
    sx, sy, sz = SHEAVE
    for dx in (-.1, .1):
        blk(g, sx + dx - .02, sy - .13, sz - .08, sx + dx + .02, sy + .13, z0, IRON)
    g.cylinder((sx, sy, sz), .035, .26, IRON, 'X', 10)
    sheave = P.flywheel('ArchiveExcavation.Sheave', (sx, sy, sz), SHEAVE_R, axis='X', spokes=6, rim_mat=IRON,
                        width=.07)
    parts.append((sheave, 'SPIN_X', -2))
    pivot = K.beacon(g, x1 - .1, y1 - .1, z1 + .04)
    parts.append((K.beacon_shutter(*pivot, 'ArchiveExcavation.Beacon'), 'SPIN_Z', 2))
    # Hoist bucket and its rope.
    bx, by = BUCKET
    b = Geometry('ArchiveExcavation.HoistBucket', (bx, by, BUCKET_REST))
    z = BUCKET_REST
    P.lathe(b, (bx, by, z), [(.12, 0), (.17, .3), (.19, .3), (.19, .34)], IRON, segments=16)
    K.band(b, (bx, by, 0), .145, z + .15, .035, PAINTED, segments=16)
    for s in (-1, 1):
        b.cylinder((bx + s * .185, by, z + .26), .025, .05, IRON, 'X', 8)
        b.beam((bx + s * .2, by, z + .26), (bx + s * .035, by, z + .5), .02, mat=IRON)
    b.beam((bx - .04, by, z + .5), (bx + .04, by, z + .5), .028, mat=IRON)
    P.hoop(b, (bx, by, z + .54), .04, .014, .014, IRON, axis='Y', segments=10)
    b.rock((bx, by, z + .34), (.22, .19, .1), GREYPLANK, 5)
    parts.append((b, 'SLIDE_Z', -BUCKET_TRAVEL))
    hook = BUCKET_REST + .57
    rope = Geometry('ArchiveExcavation.HoistRope', (bx, by, sz))
    blk(rope, bx - .012, by - .012, hook, bx + .012, by + .012, sz, IRON)
    parts.append((rope, 'CUSTOM_CABLE', (BUCKET_TRAVEL, sz - hook)))
    # Winch on the thick back wall and its rope to the sheave.
    wx, wy, wz = WINCH
    for x in (wx - .22, wx + .22):
        blk(g, x - .025, wy - .12, RIM, x + .025, wy + .12, wz + .06, IRON)
    blk(g, wx - .27, wy - .15, RIM, wx + .27, wy + .15, RIM + .07, IRON)
    drum = Geometry('ArchiveExcavation.WinchDrum', (wx, wy, wz))
    P.lathe(drum, (wx, wy, wz), [(.2, -.19), (.2, -.16), (.15, -.16), (.15, .16), (.2, .16), (.2, .19)], PAINTED,
            axis='X', segments=18)
    for k in range(6):
        drum.box((wx, wy + math.cos(k * math.pi / 3) * .155, wz + math.sin(k * math.pi / 3) * .155),
                 (.28, .018, .018), IRON)
    parts.append((drum, 'SPIN_X', 2))
    g.cylinder((wx + .35, wy, wz), .035, .32, IRON, 'X', 10)
    blk(g, wx + .52, wy - .09, RIM, wx + .57, wy + .09, wz + .04, IRON)
    fly = P.flywheel('ArchiveExcavation.WinchFlywheel', (wx + .44, wy, wz), .24, axis='X', spokes=6)
    parts.append((fly, 'SPIN_X', 2))
    P.motor(g, (wx - .55, wy, RIM + .15), .11, .26, axis='X')
    g.beam((sx, sy + SHEAVE_R, sz), (wx, wy - .05, wz + .15), .025, mat=IRON)


# ---------------------------------------------------------------- sieving shed

def shed(g, parts):
    """Open one-tile sieving shed beside the door under a timber deck on
    layer 2, fed by the spoil belt on the pit's front rim."""
    x0, y0, x1, y1 = SHED
    base = .15
    blk(g, x0 + .06, y0, -.02, x1, y1, base, CONCRETE)
    for x, y in ((x1 - .16, y0 + .16), (x0 + .2, y0 + .16), (x1 - .16, y1 - .16)):
        P.pier(g, x, y, base - .03, base + .2, .18)
        blk(g, x - .05, y - .05, base + .25, x + .05, y + .05, 1.72, IRON)
    blk(g, x0 + .1, y0 + .06, 1.72, x1 - .04, y0 + .18, 1.84, IRON)
    MP.plank_deck(g, x0 + .06, x1, y0, y1, 2.0, t=ROOF_T, seed=37)
    for i, cx in enumerate((3.3, 3.72)):
        sieve(g, parts, i, cx, 1.5, base)
    # Spoil belt on the pit's front rim and its chute down into the shed.
    y = 2.19
    bx0, bx1 = 2.2, 3.4
    for x in (bx0 + .1, bx1 - .1):
        blk(g, x - .03, y - .08, RIM, x + .03, y + .08, RIM + .1, IRON)
    blk(g, bx0, y - .1, RIM + .1, bx1, y + .1, RIM + .16, IRON)
    blk(g, bx0 + .02, y - .08, RIM + .16, bx1 - .02, y + .08, RIM + .18, PAINTED)
    C.hopper(g, bx0 + .12, y, RIM + .18, RIM + .42, .14, .07)
    belt = Geometry('ArchiveExcavation.SpoilBelt', (2.8, y, RIM + .18))
    pitch = .3
    for k in range(3):
        belt.rock((bx0 + .3 + k * pitch, y, RIM + .22), (.12, .1, .07), GREYPLANK if k % 2 else CONCRETE, 40 + k)
    parts.append((belt, 'CUSTOM_LOOP_X', pitch))
    g.beam((bx1 + .03, y, RIM + .16), (3.55, 1.75, 1.0), .14, .04, FORGED)


def sieve(g, parts, i, cx, cy, base):
    for dx in (-.15, .15):
        for dy in (-.18, .18):
            blk(g, cx + dx - .025, cy + dy - .025, base, cx + dx + .025, cy + dy + .025, .7, GREYWOOD)
        blk(g, cx + dx - .03, cy - .21, .66, cx + dx + .03, cy + .21, .71, GREYWOOD)
    blk(g, cx - .1, cy - .12, base, cx + .1, cy + .12, .42, WOOD)
    ore_heap(g, cx, cy, .42, .08, .07, h=.12, mats=(GREYPLANK,), seed=50 + i, count=3)
    t = Geometry(f'ArchiveExcavation.Sieve{i + 1}', (cx, cy, .79))
    w, d = .17, .24
    for s in (-1, 1):
        blk(t, cx - w, cy + s * d - .025, .72, cx + w, cy + s * d + .025, .84, GREYWOOD)
        blk(t, cx + s * w - .025, cy - d + .025, .72, cx + s * w + .025, cy + d - .025, .84, GREYWOOD)
    for k in range(4):
        x = cx - w + .07 + k * (2 * w - .14) / 3
        blk(t, x - .008, cy - d + .025, .76, x + .008, cy + d - .025, .772, IRON)
    t.rock((cx - .04, cy, .8), (.14, .14, .05), GREYPLANK, 60 + i)
    parts.append((t, 'PISTON_X', .03))


def build(g, parts):
    hall(g, parts)
    stacks(g, parts)
    pit(g, parts)
    derrick(g, parts)
    shed(g, parts)
