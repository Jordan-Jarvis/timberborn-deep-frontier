"""CryogenicTankFarm: pipe-fed storage for LiquidHydrogen and LiquidOxygen.

HERO: a big frost-white double-walled flat-bottom oxygen tank with a ribbed
steel dome, wound by a riveted spiral stair up to a roof-edge gallery, with
a tall boil-off vent and relief valves on its crown.
ROOF: steel dome on the LOX tank; dished heads on the hydrogen bullets; teal
plank gable on the control hut.

Plan (11 x 10 tiles): a cast-concrete bund across the back holds the LOX tank
(right) and two horizontal vacuum-jacketed hydrogen bullets on concrete
saddles (left). Along the front: the timber control hut with the door, the
boil-off compressor skid with its flywheel, a bank of star-finned ambient
vaporizers, and the valve manifold with the two Timber Pipes sockets on the
front edge. A pipe rack carries the insulated lines over the bund wall.

Distinct from CryogenicLiquefactionPlant (cold box tower, banded column,
twin Horton spheres on legs, sawtooth compressor house): no sphere, no
tower; the squat domed tank with its spiral stair, the long bullets and the
finned vaporizers carry the silhouette.

Animated: beacon (SPIN_Z), relief valve cap popping (PISTON_Z), compressor
flywheel (SPIN_Y), compressor piston rod (PISTON_X).
Emitters: steam at the boil-off vent mouth (no smoke: nothing burns here).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN, LAYER_GAP
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
from native_window_atlas import atlas_window

IDENT = 'CryogenicTankFarm'
FOOTPRINT = (11, 10)
HEIGHT = 11
FRAME_END = 121
HERO = ('Squat frost-white double-walled oxygen tank under a ribbed steel dome, wound by a riveted spiral '
        'stair to a roof-edge gallery, with a tall boil-off vent on its crown.')

# Timber Pipes sockets on the manifold's front face (local block coordinates,
# facing the front edge, Down = -Y). Storage both fills and draws through
# these; the port State is set when the blueprint is authored.
PIPE_SOCKETS = (
    {'cell': [9, 0, 0], 'direction': 'Down', 'good': 'LiquidHydrogen', 'socket': [9.5, .16, .5]},
    {'cell': [10, 0, 0], 'direction': 'Down', 'good': 'LiquidOxygen', 'socket': [10.5, .16, .5]},
)

BUND = (0.0, 3.0, 11.0, 10.0)
BUND_T, BUND_H = .2, .55
TANK = (7.6, 6.5)
TANK_R = 2.2
SHELL_TOP = 5.85
DOME_BASE = 5.95
DOME_RISE = .99
GALLERY_Z = 6.0
GAL_IN, GAL_OUT = 2.25, 2.65
STAIR_IN, STAIR_OUT = 2.7, 3.1
STAIR_A0, STAIR_A1 = math.radians(-100), math.radians(170)
BULLETS_X = (1.35, 3.45)
BULLET_Y = (4.6, 8.8)
BULLET_Z, BULLET_R = 1.4, .85
DOOR_X = 1.5


def dome_z(r):
    """Height of the LOX tank dome surface at radius r from its axis."""
    R = TANK_R + .03
    t = math.acos(min(1.0, r / R))
    return DOME_BASE + R * (DOME_RISE / R) * math.sin(t)


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
    # Hazard plaque and gauge board on the front of the bund.
    blk(g, 5.6, y0 - .03, .12, 6.3, y0, .45, PAINTED)
    P.gauge(g, 5.78, y0 - .03, .3, 'front', .07)
    P.gauge(g, 6.12, y0 - .03, .3, 'front', .07)


# ---------------------------------------------------------------- LOX tank

def lox_tank(g, parts):
    cx, cy = TANK
    R = TANK_R
    K.revolve(g, (cx, cy, 0), [(R + .18, 0), (R + .18, .25)], CONCRETE, segments=20)
    K.revolve(g, (cx, cy, .22), [(R, 0), (R, SHELL_TOP - .22)], CONCRETE, segments=20, cap_bottom=False)
    for z in (1.2, 2.4, 3.6, 4.8):
        K.band(g, (cx, cy, 0), R, z, .1, IRON, segments=20, proud=.03)
    for i in range(16):
        a = (i + .5) * 2 * math.pi / 16
        g.beam((cx + math.cos(a) * (R + .02), cy + math.sin(a) * (R + .02), .3),
               (cx + math.cos(a) * (R + .02), cy + math.sin(a) * (R + .02), SHELL_TOP - .1), .06, .05, PAINTED)
    K.revolve(g, (cx, cy, SHELL_TOP - .02), [(R + .07, 0), (R + .07, DOME_BASE - SHELL_TOP + .02)], IRON,
              segments=20)
    K.dome(g, (cx, cy, DOME_BASE), R + .03, CONCRETE, segments=20, rings=8, squash=DOME_RISE / (R + .03))
    for i in range(12):
        a = i * 2 * math.pi / 12
        prev = None
        for k in range(8):
            r = (R + .06) * math.cos(k / 8 * math.pi / 2)
            p = (cx + math.cos(a) * r, cy + math.sin(a) * r, dome_z(min(r, R + .03) - .0) + .03)
            if prev:
                g.beam(prev, p, .06, mat=IRON)
            prev = p
    # Manway, level gauge and bottom outlet on the shell.
    a = math.radians(-60)
    mx, my = cx + math.cos(a) * (R + .05), cy + math.sin(a) * (R + .05)
    P.tube(g, (cx + math.cos(a) * (R - .05), cy + math.sin(a) * (R - .05), .9), (mx, my, .9), .26, IRON, segments=16)
    gallery(g, parts)
    spiral_stair(g)
    crown(g, parts)


def gallery(g, parts):
    cx, cy = TANK
    z = GALLERY_Z
    P.annulus(g, (cx, cy), GAL_IN, GAL_OUT, z - .08, z, IRON, segments=20)
    gap = (STAIR_A1 % (2 * math.pi)) - .2, (STAIR_A1 % (2 * math.pi)) + .2
    P.ring_rail(g, (cx, cy), GAL_OUT - .04, z, posts=28, gap=gap)
    for i in range(14):
        a = (i + .5) * 2 * math.pi / 14
        g.beam((cx + math.cos(a) * (TANK_R + .03), cy + math.sin(a) * (TANK_R + .03), z - .75),
               (cx + math.cos(a) * (GAL_OUT - .1), cy + math.sin(a) * (GAL_OUT - .1), z - .1), .07, mat=IRON)


def spiral_stair(g):
    """Riveted steel stair wound once three-quarters round the shell."""
    cx, cy = TANK
    steps = 30
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
        if k % 4 == 1 and k > 4:
            g.beam((cx + radial[0] * (TANK_R + .02), cy + radial[1] * (TANK_R + .02), z - .6),
                   (cx + radial[0] * (STAIR_OUT - .12), cy + radial[1] * (STAIR_OUT - .12), z - .08), .06, mat=IRON)
        if k % 3 == 0:
            p = outer[-1]
            g.box((p[0], p[1], z + .31), (.045, .045, .62), IRON)
    for line in (outer, inner):
        for p, q in zip(line, line[1:]):
            g.beam(p, q, .07, mat=IRON)
    for p, q in zip(outer[::3], outer[3::3]):
        g.beam((p[0], p[1], p[2] + .72), (q[0], q[1], q[2] + .72), .05, mat=IRON)
    # Foot of the stair: a concrete landing block.
    a = STAIR_A0
    blk(g, cx + math.cos(a) * rm - .3, cy + math.sin(a) * rm - .35, 0, cx + math.cos(a) * rm + .3,
        cy + math.sin(a) * rm + .05, .06, CONCRETE)


def crown(g, parts):
    cx, cy = TANK
    top = dome_z(0)
    # Boil-off vent: a tall flanged pipe with a flared mouth, guyed to the dome.
    P.lathe(g, (cx, cy, top - .1), [(.24, 0), (.24, .2), (.14, .26), (.14, 3.6), (.2, 3.75), (.2, 3.85)], IRON,
            segments=16)
    mouth = top - .1 + 3.85
    g.cylinder((cx, cy, mouth + .01), .14, .02, IRON, 'Z', 16)
    for z in (top + 1.0, top + 2.2):
        P.hoop(g, (cx, cy, z), .18, .05, .06, BRASS, segments=16)
    for i in range(3):
        a = i * 2 * math.pi / 3 + 1.0
        r = 1.6
        g.beam((cx + math.cos(a) * .15, cy + math.sin(a) * .15, top + 2.6),
               (cx + math.cos(a) * r, cy + math.sin(a) * r, dome_z(r) + .02), .025, mat=IRON)
    K.emitter(g, 'steam', cx, cy, mouth + .02, .14)
    # Relief valve with a popping cap and a beacon mast.
    vx, vy = cx + .7, cy - .3
    vz = dome_z(math.hypot(vx - cx, vy - cy))
    g.cylinder((vx, vy, vz + .1), .12, .3, IRON, 'Z', 12)
    P.hoop(g, (vx, vy, vz + .25), .17, .05, .05, BRASS, segments=12)
    g.cylinder((vx, vy, vz + .38), .08, .26, PAINTED, 'Z', 12)
    cap = Geometry('CryogenicTankFarm.ReliefCap', (vx, vy, vz + .55))
    cap.cylinder((vx, vy, vz + .54), .12, .06, IRON, 'Z', 12)
    cap.cylinder((vx, vy, vz + .61), .04, .08, BRASS, 'Z', 8)
    parts.append((cap, 'PISTON_Z', .05))
    bx, by = cx - .6, cy + .5
    bz = dome_z(math.hypot(bx - cx, by - cy))
    blk(g, bx - .05, by - .05, bz - .1, bx + .05, by + .05, bz + .9, IRON)
    pivot = K.beacon(g, bx, by, bz + .9)
    parts.append((K.beacon_shutter(*pivot, 'CryogenicTankFarm.Beacon'), 'SPIN_Z', 1))


# ---------------------------------------------------------------- hydrogen bullets

def bullets(g):
    y0, y1 = BULLET_Y
    for x in BULLETS_X:
        C.horizontal_vessel(g, y0, y1, x, BULLET_Z, BULLET_R, mat=CONCRETE, bands=2, axis='Y', segments=16)
        # Top nozzles and a vacuum port on each jacket.
        for y in (y0 + .6, y1 - .9):
            g.cylinder((x, y, BULLET_Z + BULLET_R + .06), .09, .16, IRON, 'Z', 10)
            P.hoop(g, (x, y, BULLET_Z + BULLET_R + .14), .13, .04, .04, BRASS, segments=10)
        g.cylinder((x + BULLET_R + .05, (y0 + y1) / 2, BULLET_Z), .1, .14, IRON, 'X', 10)
    # Valve platform between the bullet heads, with a ladder.
    px0, px1, py0, py1 = 1.95, 2.85, 3.35, 3.95
    for x in (px0 + .1, px1 - .1):
        for y in (py0 + .1, py1 - .1):
            P.pier(g, x, y, 0, .3, .2)
            blk(g, x - .05, y - .05, .35, x + .05, y + .05, 1.92, IRON)
    P.grating(g, px0, py0, px1, py1, 2)
    P.rail(g, [(px0 + .04, py1 - .04), (px0 + .04, py0 + .04), (2.2, py0 + .04)], 2)
    P.rail(g, [(2.6, py0 + .04), (px1 - .04, py0 + .04), (px1 - .04, py1 - .04)], 2)
    K.ladder(g, px0 + .45, py0, 0, 2.0, face='front', cage=False)
    for x in BULLETS_X:
        s = 1 if x < 2.4 else -1
        P.pipe(g, [(x, y0 + .6, BULLET_Z + BULLET_R + .14), (x, y0 + .6, 2.45), (x + s * .5, y0 + .6, 2.45),
                   (x + s * .5, py1 - .1, 2.45)], .05, flanges=False)


# ---------------------------------------------------------------- control hut

def hut(g):
    x0, y0, x1, y1 = 0.0, .15, 3.0, 2.95
    C.podium(g, x0, y0, x1, y1, 1.2, skip=[(1.0, 2.0)])
    C.door(g, DOOR_X, y0, 0, 'Door0')
    atlas_window(g, 2.4, y0, .6, .42, 'front', 'grid9')
    atlas_window(g, x0, 1.55, .6, .42, 'left', 'grid9')
    bx0, by0, bx1, by1 = x0 + .05, y0 + .05, x1 - .05, y1 - .05
    eave = 2.8
    C.framed_block(g, bx0, by0, bx1, by1, 1.2, eave, infill=ORANGE, frame=WOOD, pitch=.95,
                   windows={'front': [(.56, 1.95, .95, 'grand'), (2.44, 1.95, .95, 'grand')],
                            'left': [(1.55, 1.95, .95, 'grand')],
                            'right': [(.65, 1.95, .95, 'grand'), (2.45, 1.95, .95, 'grand')]})
    P.plank_roof(g, bx0, by0, bx1, by1, eave, eave + 1.05, ridge_axis='Y', overhang=.16, plank=.28)
    K.lamp(g, DOOR_X - .62, y0, .95, face='front')
    K.lamp(g, DOOR_X + .62, y0, .95, face='front')
    K.stack(g, .7, 2.2, eave + .4, .9, emits=None, r=.09, taper=.95, bands=1)


# ---------------------------------------------------------------- compressor

def compressor(g, parts):
    # One cast slab under the compressor, vaporizers and manifold.
    blk(g, 3.05, 0.0, -.02, 11.0, 2.95, .3, CONCRETE)
    base = .3
    cy, cz = 1.0, .78
    for x in (3.55, 4.1):
        blk(g, x - .12, cy - .22, base - .02, x + .12, cy + .22, cz - .2, CONCRETE)
    g.cylinder((3.85, cy, cz), .3, .8, PAINTED, 'X', 18)
    for x in (3.47, 4.23):
        g.cylinder((x, cy, cz), .34, .06, IRON, 'X', 18)
    # Crosshead guide: open frame so the rod shows.
    blk(g, 4.25, cy - .14, cz - .2, 4.95, cy + .14, cz - .14, IRON)
    blk(g, 4.25, cy - .14, cz + .14, 4.95, cy + .14, cz + .2, IRON)
    for x in (4.3, 4.9):
        blk(g, x - .03, cy - .14, base - .02, x + .03, cy + .14, cz - .2, IRON)
    rod = Geometry('CryogenicTankFarm.PistonRod', (4.5, cy, cz))
    rod.cylinder((4.35, cy, cz), .035, .6, IRON, 'X', 8)
    blk(rod, 4.55, cy - .1, cz - .1, 4.72, cy + .1, cz + .1, PAINTED)
    parts.append((rod, 'PISTON_X', .1))
    # Flywheel on its bearing pedestals behind the guide.
    fx, fy, fz = 4.75, 1.85, .95
    for y in (fy - .17, fy + .17):
        blk(g, fx - .1, y - .04, base - .02, fx + .1, y + .04, fz + .06, IRON)
    g.cylinder((fx, fy, fz), .05, .5, IRON, 'Y', 10)
    fly = P.flywheel('CryogenicTankFarm.Flywheel', (fx, fy, fz), .52, axis='Y', spokes=6)
    parts.append((fly, 'SPIN_Y', 1))
    P.motor(g, (3.7, 1.95, base + .2), .2, .5, axis='X')


# ---------------------------------------------------------------- vaporizers

def vaporizers(g):
    base = .3
    xs = (5.95, 7.0, 8.05)
    ys = (.9, 2.05)
    top = 3.25
    for y in ys:
        for x in xs:
            blk(g, x - .12, y - .12, base - .02, x + .12, y + .12, base + .1, IRON)
            g.cylinder((x, y, (base + .1 + top) / 2), .07, top - base - .1, IRON, 'Z', 10)
            for k in range(8):
                a = k * math.pi / 4
                c = (x + math.cos(a) * .18, y + math.sin(a) * .18, (base + .2 + top - .1) / 2)
                C.obox(g, c, (math.cos(a), math.sin(a), 0), (-math.sin(a), math.cos(a), 0), (0, 0, 1),
                       .115, .012, (top - base - .3) / 2, CONCRETE)
            g.cylinder((x, y, top + .04), .1, .08, IRON, 'Z', 10)
        P.pipe(g, [(xs[0] - .25, y, top + .2), (xs[-1] + .25, y, top + .2)], .06, flanges=False)
        for x in xs:
            g.cylinder((x, y, top + .095), .04, .15, IRON, 'Z', 8)
    P.pipe(g, [(xs[-1] + .25, ys[0], top + .2), (xs[-1] + .45, ys[0], top + .2), (xs[-1] + .45, ys[1], top + .2),
               (xs[-1] + .25, ys[1], top + .2)], .06, flanges=False)


# ---------------------------------------------------------------- manifold and rack

def manifold(g):
    x0, y0, x1, y1 = 9.0, .32, 10.97, 2.93
    blk(g, x0, y0, .27, x1, y1, .5, CONCRETE)
    blk(g, x0 - .03, y0 - .03, .5, x1 + .02, y1 + .02, .56, IRON)
    for s in PIPE_SOCKETS:
        sx, sy, sz = s['socket']
        blk(g, sx - .25, sy + .04, sz - .25 + .0, sx + .25, y0 + .02, sz + .2, PAINTED)
        g.cylinder((sx, sy + .02, sz), .15, .08, IRON, 'Y', 16)
        P.hoop(g, (sx, sy - .03, sz), .2, .05, .04, BRASS, axis='Y', segments=16)
        K.bolt_row(g, (sx - .16, sy - .06, sz + .14), (sx + .16, sy - .06, sz + .14), 3, r=.016)
        # Riser to the header with a valve wheel.
        P.pipe(g, [(sx, 1.0, .56), (sx, 1.0, 1.7)], .07, flanges=False)
        P.valve(g, (sx, 1.0, 1.15), 'front', .12)
    P.pipe(g, [(9.5, 1.0, 1.7), (9.5, 2.85, 1.7), (9.5, 2.85, 3.85)], .07, flanges=False)
    P.pipe(g, [(10.5, 1.0, 1.7), (10.5, 3.1, 1.7), (10.5, 3.1, 3.91)], .07, flanges=False)
    P.gauge(g, 10.0, y0, .3, 'front', .08)


def rack(g):
    """Insulated lines from the tanks over the bund wall to the manifold."""
    bents = (3.35, 5.35, 7.4, 9.0)
    ya, yb = 2.75, 3.1
    zt = 3.75
    for x in bents:
        P.pier(g, x, 2.85, .27, .55, .2)
        blk(g, x - .07, 2.78, .6, x + .07, 2.92, zt - .02, IRON)
        blk(g, x - .07, ya - .1, zt - .02, x + .07, yb + .15, zt + .08, IRON)
        g.beam((x, 2.85, zt - .5), (x, yb + .1, zt - .05), .06, mat=IRON)
    # LH2 line (front) and LOX line (back) on the rack, frost-lagged.
    P.pipe(g, [(3.45, BULLET_Y[1] - .9, 2.39), (3.45, BULLET_Y[1] - .9, 3.85), (3.45, 2.85, 3.85), (9.5, 2.85, 3.85)], .08, CONCRETE,
           flanges=False)
    lx = TANK[0] + math.cos(math.radians(-118)) * TANK_R
    ly = TANK[1] + math.sin(math.radians(-118)) * TANK_R
    P.pipe(g, [(lx, ly + .1, .7), (lx, 3.5, .7), (lx, 3.5, 3.91), (lx, 3.1, 3.91), (10.5, 3.1, 3.91)], .08, CONCRETE,
           flanges=False)
    for x, y, z in ((4.4, 2.85, 3.85), (6.1, 2.85, 3.85), (8.2, 2.85, 3.85), (7.5, 3.1, 3.91), (8.6, 3.1, 3.91)):
        P.hoop(g, (x, y, z), .1, .03, .05, IRON, axis='X', segments=12)


def build(g, parts):
    bund(g)
    lox_tank(g, parts)
    bullets(g)
    hut(g)
    compressor(g, parts)
    vaporizers(g)
    manifold(g)
    rack(g)
