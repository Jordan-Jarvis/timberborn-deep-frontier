"""CryogenicTankFarm: pipe-fed storage for LiquidHydrogen and LiquidOxygen.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size", "one layer per floor", "make
the roof flat on more of our buildings"): 11x10x11 -> 7x6x7, inside the old
footprint with the same origin, door and native entrance (cell 1, -1). The
two Timber Pipes sockets moved with the manifold from cells (9, 0, 0) and
(10, 0, 0) to (5, 0, 0) and (6, 0, 0), still on the front edge facing Down.
Removed: the pipe rack on its bents and piers, the valve platform between
the bullet heads with its ladder, and the control hut's gable. The LOX tank,
its spiral stair and gallery, the bullets and the vaporizer bank are smaller.

HERO: a frost-white double-walled flat-bottom oxygen tank with a ribbed
steel dome, wound by a riveted spiral stair up to a roof-edge gallery on a
whole layer, with a boil-off vent and a relief valve on its crown.
ROOF: steel dome on the LOX tank (its defining silhouette); dished heads on
the hydrogen bullets; flat concrete roof with a low curb on the two-storey
control hut.

Plan (7 x 6 tiles): a cast-concrete bund across the back holds the LOX tank
(right) and two horizontal vacuum-jacketed hydrogen bullets on concrete
saddles (left). Along the front: the control hut with the door, the
boil-off compressor skid with its flywheel, four star-finned ambient
vaporizers and the valve manifold with the two sockets on the front edge.
The insulated lines run low over the bund wall.

Distinct from CryogenicLiquefactionPlant (cold box tower, banded column,
twin Horton spheres on legs): no sphere, no tower; the squat domed tank with
its spiral stair, the long bullets and the finned vaporizers carry the
silhouette.

Animated (4, names unchanged): beacon (SPIN_Z), relief valve cap popping
(PISTON_Z), compressor flywheel (SPIN_Y), compressor piston rod (PISTON_X).
Emitters: steam at the boil-off vent mouth (no smoke: nothing burns here).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
import compact_industry_parts as Q

IDENT = 'CryogenicTankFarm'
FOOTPRINT = (7, 6)
HEIGHT = 7
FRAME_END = 121
HERO = ('Squat frost-white double-walled oxygen tank under a ribbed steel dome, wound by a riveted spiral '
        'stair to a roof-edge gallery, with a boil-off vent on its crown.')

# Timber Pipes sockets on the manifold's front face (local block coordinates,
# facing the front edge, Down = -Y). Storage both fills and draws through
# these; the port State is set when the blueprint is authored.
PIPE_SOCKETS = (
    {'cell': [5, 0, 0], 'direction': 'Down', 'good': 'LiquidHydrogen', 'socket': [5.5, .16, .5]},
    {'cell': [6, 0, 0], 'direction': 'Down', 'good': 'LiquidOxygen', 'socket': [6.5, .16, .5]},
)

BUND = (0.0, 2.0, 7.0, 6.0)
BUND_T, BUND_H = .2, .45
TANK = (4.85, 3.9)
TANK_R = 1.3
SHELL_TOP = 3.85
DOME_BASE = 3.95
DOME_RISE = .72
GALLERY_Z = 4.0
GAL_IN, GAL_OUT = TANK_R + .05, TANK_R + .4
STAIR_IN, STAIR_OUT = TANK_R + .45, TANK_R + .81
STAIR_A0, STAIR_A1 = math.radians(-40), math.radians(200)
STAIR_STEPS = 20
BULLETS_X = (.72, 1.85)
BULLET_Y = (2.55, 5.55)
BULLET_Z, BULLET_R = 1.0, .5
HUT = (0.0, 0.0, 2.0, 2.0)
DOOR_X = 1.5


def dome_z(r):
    """Height of the LOX tank dome surface at radius r from its axis."""
    R = TANK_R + .03
    t = math.acos(min(1.0, r / R))
    return DOME_BASE + DOME_RISE * math.sin(t)


# ---------------------------------------------------------------- bund

def bund(g):
    x0, y0, x1, y1 = BUND
    t, h = BUND_T, BUND_H
    blk(g, x0, y0, 0, x1, y0 + t, h, CONCRETE)
    blk(g, x0, y1 - t, 0, x1, y1, h, CONCRETE)
    blk(g, x0, y0 + t, 0, x0 + t, y1 - t, h, CONCRETE)
    blk(g, x1 - t, y0 + t, 0, x1, y1 - t, h, CONCRETE)
    # Steel coping strips proud of the wall tops, kept clear of each other.
    blk(g, x0 + .02, y0 + .02, h, x1 - .02, y0 + t - .02, h + .04, IRON)
    blk(g, x0 + .02, y1 - t + .02, h, x1 - .02, y1 - .02, h + .04, IRON)
    blk(g, x0 + .02, y0 + t + .02, h, x0 + t - .02, y1 - t - .02, h + .04, IRON)
    blk(g, x1 - t + .02, y0 + t + .02, h, x1 - .02, y1 - t - .02, h + .04, IRON)


# ---------------------------------------------------------------- LOX tank

def lox_tank(g, parts):
    cx, cy = TANK
    R = TANK_R
    K.revolve(g, (cx, cy, 0), [(R + .15, 0), (R + .15, .2)], CONCRETE, segments=20)
    K.revolve(g, (cx, cy, .18), [(R, 0), (R, SHELL_TOP - .18)], CONCRETE, segments=20, cap_bottom=False)
    for z in (1.0, 2.0, 3.0):
        K.band(g, (cx, cy, 0), R, z, .09, IRON, segments=20, proud=.03)
    for i in range(12):
        a = (i + .5) * 2 * math.pi / 12
        g.beam((cx + math.cos(a) * (R + .02), cy + math.sin(a) * (R + .02), .25),
               (cx + math.cos(a) * (R + .02), cy + math.sin(a) * (R + .02), SHELL_TOP - .1), .05, .045, PAINTED)
    K.revolve(g, (cx, cy, SHELL_TOP - .02), [(R + .06, 0), (R + .06, DOME_BASE - SHELL_TOP + .02)], IRON,
              segments=20)
    K.dome(g, (cx, cy, DOME_BASE), R + .03, CONCRETE, segments=20, rings=6, squash=DOME_RISE / (R + .03))
    for i in range(10):
        a = i * 2 * math.pi / 10
        prev = None
        for k in range(6):
            r = (R + .06) * math.cos(k / 6 * math.pi / 2)
            p = (cx + math.cos(a) * r, cy + math.sin(a) * r, dome_z(min(r, R + .03)) + .03)
            if prev:
                g.beam(prev, p, .05, mat=IRON)
            prev = p
    # Manway on the shell, facing the yard.
    a = math.radians(-70)
    P.tube(g, (cx + math.cos(a) * (R - .05), cy + math.sin(a) * (R - .05), .75),
           (cx + math.cos(a) * (R + .05), cy + math.sin(a) * (R + .05), .75), .2, IRON, segments=16)
    gallery(g)
    spiral_stair(g)
    crown(g, parts)


def gallery(g):
    cx, cy = TANK
    z = GALLERY_Z
    P.annulus(g, (cx, cy), GAL_IN, GAL_OUT, z - .08, z, IRON, segments=20)
    end = STAIR_A1 % (2 * math.pi)
    P.ring_rail(g, (cx, cy), GAL_OUT - .04, z, posts=20, gap=(end - .25, end + .25))
    for i in range(10):
        a = (i + .5) * 2 * math.pi / 10
        g.beam((cx + math.cos(a) * (TANK_R + .03), cy + math.sin(a) * (TANK_R + .03), z - .55),
               (cx + math.cos(a) * (GAL_OUT - .08), cy + math.sin(a) * (GAL_OUT - .08), z - .1), .06, mat=IRON)


def spiral_stair(g):
    """Riveted steel stair wound two-thirds round the shell, clear of the
    front yard, up to the gallery on layer 4."""
    cx, cy = TANK
    steps = STAIR_STEPS
    rise = GALLERY_Z / steps
    rm = (STAIR_IN + STAIR_OUT) / 2
    half_r = (STAIR_OUT - STAIR_IN) / 2
    da = (STAIR_A1 - STAIR_A0) / steps
    half_t = da * rm / 2 - .02
    outer, inner = [], []
    for k in range(steps):
        a = STAIR_A0 + (k + .5) * da
        z = rise * (k + 1)
        radial, tang = (math.cos(a), math.sin(a), 0), (-math.sin(a), math.cos(a), 0)
        C.obox(g, (cx + radial[0] * rm, cy + radial[1] * rm, z - .03), radial, tang, (0, 0, 1),
               half_r, half_t, .03, IRON)
        outer.append((cx + radial[0] * (STAIR_OUT - .03), cy + radial[1] * (STAIR_OUT - .03), z - .1))
        inner.append((cx + radial[0] * (STAIR_IN + .03), cy + radial[1] * (STAIR_IN + .03), z - .1))
        if k % 4 == 1 and k > 2:
            g.beam((cx + radial[0] * (TANK_R + .02), cy + radial[1] * (TANK_R + .02), z - .5),
                   (cx + radial[0] * (STAIR_OUT - .1), cy + radial[1] * (STAIR_OUT - .1), z - .08), .05, mat=IRON)
        if k % 3 == 0:
            p = outer[-1]
            g.box((p[0], p[1], z + .29), (.04, .04, .58), IRON)
    for line in (outer, inner):
        for p, q in zip(line, line[1:]):
            g.beam(p, q, .06, mat=IRON)
    for p, q in zip(outer[::3], outer[3::3]):
        g.beam((p[0], p[1], p[2] + .68), (q[0], q[1], q[2] + .68), .045, mat=IRON)
    # Foot of the stair: a concrete landing block.
    a = STAIR_A0
    blk(g, cx + math.cos(a) * rm - .25, cy + math.sin(a) * rm - .3, 0, cx + math.cos(a) * rm + .25,
        cy + math.sin(a) * rm + .05, .06, CONCRETE)


def crown(g, parts):
    cx, cy = TANK
    top = dome_z(0)
    # Boil-off vent: a flanged pipe with a flared mouth, guyed to the dome.
    P.lathe(g, (cx, cy, top - .1), [(.2, 0), (.2, .18), (.12, .24), (.12, 1.9), (.17, 2.02), (.17, 2.1)], IRON,
            segments=16)
    mouth = top - .1 + 2.1
    g.cylinder((cx, cy, mouth + .01), .12, .02, IRON, 'Z', 16)
    P.hoop(g, (cx, cy, top + .9), .15, .045, .05, BRASS, segments=16)
    for i in range(3):
        a = i * 2 * math.pi / 3 + 1.0
        r = 1.0
        g.beam((cx + math.cos(a) * .13, cy + math.sin(a) * .13, top + 1.4),
               (cx + math.cos(a) * r, cy + math.sin(a) * r, dome_z(r) + .02), .022, mat=IRON)
    K.emitter(g, 'steam', cx, cy, mouth + .02, .12)
    # Relief valve with a popping cap and a beacon mast.
    vx, vy = cx + .5, cy - .25
    vz = dome_z(math.hypot(vx - cx, vy - cy))
    g.cylinder((vx, vy, vz + .1), .1, .26, IRON, 'Z', 12)
    P.hoop(g, (vx, vy, vz + .22), .14, .045, .045, BRASS, segments=12)
    g.cylinder((vx, vy, vz + .33), .07, .22, PAINTED, 'Z', 12)
    cap = Geometry('CryogenicTankFarm.ReliefCap', (vx, vy, vz + .48))
    cap.cylinder((vx, vy, vz + .47), .1, .05, IRON, 'Z', 12)
    cap.cylinder((vx, vy, vz + .53), .035, .07, BRASS, 'Z', 8)
    parts.append((cap, 'PISTON_Z', .05))
    bx, by = cx - .45, cy + .4
    bz = dome_z(math.hypot(bx - cx, by - cy))
    blk(g, bx - .04, by - .04, bz - .1, bx + .04, by + .04, bz + .7, IRON)
    pivot = K.beacon(g, bx, by, bz + .7)
    parts.append((K.beacon_shutter(*pivot, 'CryogenicTankFarm.Beacon'), 'SPIN_Z', 1))


# ---------------------------------------------------------------- hydrogen bullets

def bullets(g):
    y0, y1 = BULLET_Y
    for x in BULLETS_X:
        C.horizontal_vessel(g, y0, y1, x, BULLET_Z, BULLET_R, mat=CONCRETE, bands=2, axis='Y', segments=16)
        for y in (y0 + .45, y1 - .6):
            g.cylinder((x, y, BULLET_Z + BULLET_R + .05), .07, .14, IRON, 'Z', 10)
            P.hoop(g, (x, y, BULLET_Z + BULLET_R + .12), .1, .035, .035, BRASS, segments=10)
        g.cylinder((x + BULLET_R + .04, (y0 + y1) / 2, BULLET_Z), .08, .12, IRON, 'X', 10)
    # Cross-over between the two bullet tops.
    P.pipe(g, [(BULLETS_X[0], y0 + .45, BULLET_Z + BULLET_R + .14), (BULLETS_X[0], y0 + .45, 1.8),
               (BULLETS_X[1], y0 + .45, 1.8), (BULLETS_X[1], y0 + .45, BULLET_Z + BULLET_R + .14)], .045,
           flanges=False)


# ---------------------------------------------------------------- control hut

def hut(g):
    x0, y0, x1, y1 = HUT
    Q.storey_block(g, x0, y0, x1, y1, 2, infill=ORANGE, frame=WOOD, door=DOOR_X, door_id='Door0',
                   ground_windows={'left': [(1.0, .55, 'grand')]},
                   windows={'front': [(.5, 1.5, .52, 'grand'), (1.5, 1.5, .52, 'grand')],
                            'left': [(.5, 1.5, .52, 'grand'), (1.5, 1.5, .52, 'grand')],
                            'right': [(1.0, 1.5, .52, 'grand')]})
    K.lamp(g, DOOR_X - .66, y0 - .01, .8, face='front')


# ---------------------------------------------------------------- compressor

def compressor(g, parts):
    # One cast slab under the compressor, vaporizers and manifold.
    blk(g, 2.05, 0.0, -.02, 7.0, 1.95, .25, CONCRETE)
    base = .25
    cy, cz = .75, .62
    for x in (2.35, 2.75):
        blk(g, x - .1, cy - .18, base - .02, x + .1, cy + .18, cz - .16, CONCRETE)
    g.cylinder((2.55, cy, cz), .24, .6, PAINTED, 'X', 18)
    for x in (2.27, 2.83):
        g.cylinder((x, cy, cz), .27, .05, IRON, 'X', 18)
    # Crosshead guide: open frame so the rod shows.
    blk(g, 2.86, cy - .11, cz - .16, 3.36, cy + .11, cz - .11, IRON)
    blk(g, 2.86, cy - .11, cz + .11, 3.36, cy + .11, cz + .16, IRON)
    for x in (2.9, 3.32):
        blk(g, x - .025, cy - .11, base - .02, x + .025, cy + .11, cz - .16, IRON)
    rod = Geometry('CryogenicTankFarm.PistonRod', (3.05, cy, cz))
    rod.cylinder((2.95, cy, cz), .03, .45, IRON, 'X', 8)
    blk(rod, 3.08, cy - .08, cz - .08, 3.22, cy + .08, cz + .08, PAINTED)
    parts.append((rod, 'PISTON_X', .08))
    # Flywheel on its bearing pedestals behind the guide.
    fx, fy, fz = 3.15, 1.5, .78
    for y in (fy - .14, fy + .14):
        blk(g, fx - .08, y - .035, base - .02, fx + .08, y + .035, fz + .05, IRON)
    g.cylinder((fx, fy, fz), .045, .42, IRON, 'Y', 10)
    fly = P.flywheel('CryogenicTankFarm.Flywheel', (fx, fy, fz), .42, axis='Y', spokes=6)
    parts.append((fly, 'SPIN_Y', 1))
    P.motor(g, (2.45, 1.5, base + .17), .17, .42, axis='X')


# ---------------------------------------------------------------- vaporizers

def vaporizers(g):
    base = .25
    xs = (3.85, 4.6)
    ys = (.6, 1.35)
    top = 2.1
    for y in ys:
        for x in xs:
            blk(g, x - .1, y - .1, base - .02, x + .1, y + .1, base + .08, IRON)
            g.cylinder((x, y, (base + .08 + top) / 2), .06, top - base - .08, IRON, 'Z', 10)
            for k in range(8):
                a = k * math.pi / 4
                c = (x + math.cos(a) * .15, y + math.sin(a) * .15, (base + .18 + top - .1) / 2)
                C.obox(g, c, (math.cos(a), math.sin(a), 0), (-math.sin(a), math.cos(a), 0), (0, 0, 1),
                       .09, .01, (top - base - .28) / 2, CONCRETE)
            g.cylinder((x, y, top + .035), .085, .07, IRON, 'Z', 10)
        P.pipe(g, [(xs[0] - .2, y, top + .17), (xs[-1] + .2, y, top + .17)], .05, flanges=False)
        for x in xs:
            g.cylinder((x, y, top + .08), .035, .12, IRON, 'Z', 8)
    P.pipe(g, [(xs[-1] + .2, ys[0], top + .17), (xs[-1] + .36, ys[0], top + .17), (xs[-1] + .36, ys[1], top + .17),
               (xs[-1] + .2, ys[1], top + .17)], .05, flanges=False)


# ---------------------------------------------------------------- manifold and lines

def manifold(g):
    x0, y0, x1, y1 = 5.05, .32, 6.97, 1.93
    blk(g, x0, y0, .22, x1, y1, .5, CONCRETE)
    blk(g, x0 - .03, y0 - .03, .5, x1 + .02, y1 + .02, .56, IRON)
    for s in PIPE_SOCKETS:
        sx, sy, sz = s['socket']
        blk(g, sx - .25, sy + .04, sz - .25, sx + .25, y0 + .02, sz + .2, PAINTED)
        g.cylinder((sx, sy + .02, sz), .15, .08, IRON, 'Y', 16)
        P.hoop(g, (sx, sy - .03, sz), .2, .05, .04, BRASS, axis='Y', segments=16)
        K.bolt_row(g, (sx - .16, sy - .06, sz + .14), (sx + .16, sy - .06, sz + .14), 3, r=.016)
        P.valve(g, (sx, 1.0, 1.1), 'front', .11)
    P.gauge(g, 6.0, y0, .3, 'front', .08)


def lines(g):
    """Insulated lines from the bullets and the tank, low over the bund wall,
    down into the manifold risers."""
    # LH2: from the front bullet's top nozzle to the left socket's riser.
    x = BULLETS_X[1]
    P.pipe(g, [(x, BULLET_Y[0] + .45, 1.8), (x, 2.1, 1.8), (5.5, 2.1, 1.8), (5.5, 1.0, 1.8), (5.5, 1.0, .56)],
           .065, CONCRETE, flanges=False)
    # LOX: from the tank's foot, over the bund wall, to the right socket's riser.
    cx, cy = TANK
    P.pipe(g, [(cx, cy - TANK_R + .05, .7), (cx, 2.32, .7), (cx, 2.32, 1.95), (6.5, 2.32, 1.95), (6.5, 1.0, 1.95),
               (6.5, 1.0, .56)], .065, CONCRETE, flanges=False)
    for px, py, pz in ((3.2, 2.1, 1.8), (5.8, 2.32, 1.95)):
        P.hoop(g, (px, py, pz), .085, .025, .045, IRON, axis='X', segments=12)


def build(g, parts):
    bund(g)
    lox_tank(g, parts)
    bullets(g)
    hut(g)
    compressor(g, parts)
    vaporizers(g)
    manifold(g)
    lines(g)
