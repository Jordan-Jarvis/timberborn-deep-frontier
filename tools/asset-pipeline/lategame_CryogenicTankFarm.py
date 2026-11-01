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

Shrunk again 2026-11-01 (a YouTuber called it "massive"; user: "we need
to shrink the buildings down even more"): 7x6x7 -> 4x4x5, inside the old
footprint with the same origin, door and native entrance (cell 1, -1). The
sockets moved with the manifold from cells (5, 0, 0) and (6, 0, 0) to
(2, 0, 0) and (3, 0, 0), still on the front edge facing Down. The LOX tank
(radius 0.78) stands on its own ring base in the back-right corner; the two
bullets lie side by side along X in a small bund behind the hut; the
spiral stair became a caged ladder up the tank's left side to the narrow
gallery; two vaporizers (were four) and the compressor share the front
right slab with the manifold.

HERO: a frost-white double-walled flat-bottom oxygen tank with a ribbed
steel dome, a caged ladder up to a narrow gallery round its crown on a whole
layer (no rail: user, 2026-10-31, "lets remove the railings"), with a
boil-off vent and a relief valve on its crown.
ROOF: steel dome on the LOX tank (its defining silhouette); dished heads on
the hydrogen bullets; a pitched gable of native teal roof planks on the
two-storey control hut (roof variety).

Plan (4 x 4 tiles): the two-storey control hut with the door on the front
left 2x2 tiles; behind it a low cast-concrete bund holds two horizontal
vacuum-jacketed hydrogen bullets on concrete saddles; the LOX tank on the
back right; on the front right a cast slab carries the valve manifold with
the two sockets on the front edge, two star-finned ambient vaporizers and
the boil-off compressor skid with its flywheel. The insulated lines run from
the bullets and the tank into the vaporizer headers.

Distinct from CryogenicLiquefactionPlant (cold box tower, banded column,
twin Horton spheres on legs): no sphere, no tower; the squat domed tank,
the bullets and the finned vaporizers carry the silhouette.

Animated (4, names unchanged): beacon (SPIN_Z), relief valve cap popping
(PISTON_Z), compressor flywheel (SPIN_X since 2026-11-01, at the skid's
end), compressor piston rod (PISTON_X).
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
FOOTPRINT = (4, 4)
HEIGHT = 5
FRAME_END = 121
HERO = ('Squat frost-white double-walled oxygen tank under a ribbed steel dome, with a caged ladder to a '
        'gallery round its crown and a boil-off vent on top.')

# Timber Pipes sockets on the manifold's front face (local block coordinates,
# facing the front edge, Down = -Y). Storage both fills and draws through
# these; the port State is set when the blueprint is authored.
PIPE_SOCKETS = (
    {'cell': [2, 0, 0], 'direction': 'Down', 'good': 'LiquidHydrogen', 'socket': [2.5, .16, .5]},
    {'cell': [3, 0, 0], 'direction': 'Down', 'good': 'LiquidOxygen', 'socket': [3.5, .16, .5]},
)

BUND = (0.0, 2.06, 2.06, 4.0)       # around the bullets only; the tank stands on its own ring
BUND_T, BUND_H = .15, .4
TANK = (2.95, 2.98)
TANK_R = .78
SHELL_TOP = 2.85
DOME_BASE = 2.95
DOME_RISE = .5
GALLERY_Z = 3.0
GAL_IN, GAL_OUT = TANK_R + .1, TANK_R + .26
BULLET_X = (.32, 1.7)
BULLETS_Y = (2.6, 3.47)
BULLET_Z, BULLET_R = .78, .34
HUT = (0.0, 0.0, 2.0, 2.0)
DOOR_X = 1.5
VAPS = ((2.5, 1.0), (3.5, 1.0))
VAP_TOP = 1.8
COMP_Y, COMP_Z = 1.55, .6


def dome_z(r):
    """Height of the LOX tank dome surface at radius r from its axis."""
    R = TANK_R + .03
    t = math.acos(min(1.0, r / R))
    return DOME_BASE + DOME_RISE * math.sin(t)


# ---------------------------------------------------------------- bund

def bund(g):
    x0, y0, x1, y1 = BUND
    t, h = BUND_T, BUND_H
    blk(g, x0, y1 - t, 0, x1, y1, h, CONCRETE)
    blk(g, x0, y0, 0, x0 + t, y1 - t, h, CONCRETE)
    blk(g, x1 - t, y0, 0, x1, y1 - t, h, CONCRETE)
    blk(g, x0 + t, y0, 0, x1 - t, y0 + t, h * .5, CONCRETE)
    # Steel coping strips proud of the wall tops, kept clear of each other.
    blk(g, x0 + .02, y1 - t + .02, h, x1 - .02, y1 - .02, h + .04, IRON)
    blk(g, x0 + .02, y0 + .02, h, x0 + t - .02, y1 - t - .02, h + .04, IRON)
    blk(g, x1 - t + .02, y0 + .02, h, x1 - .02, y1 - t - .02, h + .04, IRON)


# ---------------------------------------------------------------- LOX tank

def lox_tank(g, parts):
    cx, cy = TANK
    R = TANK_R
    K.revolve(g, (cx, cy, 0), [(R + .1, 0), (R + .1, .18)], CONCRETE, segments=20)
    K.revolve(g, (cx, cy, .16), [(R, 0), (R, SHELL_TOP - .16)], CONCRETE, segments=20, cap_bottom=False)
    for z in (.9, 1.8):
        K.band(g, (cx, cy, 0), R, z, .08, IRON, segments=20, proud=.03)
    for i in range(10):
        a = (i + .5) * 2 * math.pi / 10
        g.beam((cx + math.cos(a) * (R + .02), cy + math.sin(a) * (R + .02), .22),
               (cx + math.cos(a) * (R + .02), cy + math.sin(a) * (R + .02), SHELL_TOP - .1), .045, .04, PAINTED)
    K.revolve(g, (cx, cy, SHELL_TOP - .02), [(R + .05, 0), (R + .05, DOME_BASE - SHELL_TOP + .02)], IRON,
              segments=20)
    K.dome(g, (cx, cy, DOME_BASE), R + .03, CONCRETE, segments=20, rings=6, squash=DOME_RISE / (R + .03))
    for i in range(8):
        a = i * 2 * math.pi / 8
        prev = None
        for k in range(6):
            r = (R + .05) * math.cos(k / 6 * math.pi / 2)
            p = (cx + math.cos(a) * r, cy + math.sin(a) * r, dome_z(min(r, R + .03)) + .03)
            if prev:
                g.beam(prev, p, .045, mat=IRON)
            prev = p
    # Manway on the shell, facing the front yard.
    a = math.radians(-60)
    P.tube(g, (cx + math.cos(a) * (R - .05), cy + math.sin(a) * (R - .05), .62),
           (cx + math.cos(a) * (R + .05), cy + math.sin(a) * (R + .05), .62), .17, IRON, segments=16)
    gallery(g)
    # Caged ladder up the shell's left side to the gallery.
    K.ladder(g, cx - R, cy, .16, GALLERY_Z, face='left', width=.3, cage=True)
    crown(g, parts)


def gallery(g):
    cx, cy = TANK
    z = GALLERY_Z
    P.annulus(g, (cx, cy), GAL_IN, GAL_OUT, z - .07, z, IRON, segments=20)
    for i in range(8):
        a = (i + .5) * 2 * math.pi / 8
        g.beam((cx + math.cos(a) * (TANK_R + .03), cy + math.sin(a) * (TANK_R + .03), z - .45),
               (cx + math.cos(a) * (GAL_OUT - .06), cy + math.sin(a) * (GAL_OUT - .06), z - .09), .05, mat=IRON)


def crown(g, parts):
    cx, cy = TANK
    top = dome_z(0)
    # Boil-off vent: a flanged pipe with a flared mouth, guyed to the dome.
    P.lathe(g, (cx, cy, top - .08), [(.16, 0), (.16, .14), (.1, .2), (.1, 1.1), (.14, 1.2), (.14, 1.26)], IRON,
            segments=16)
    mouth = top - .08 + 1.26
    g.cylinder((cx, cy, mouth + .01), .1, .02, IRON, 'Z', 16)
    P.hoop(g, (cx, cy, top + .6), .12, .04, .045, BRASS, segments=16)
    for i in range(3):
        a = i * 2 * math.pi / 3 + 1.0
        r = .62
        g.beam((cx + math.cos(a) * .11, cy + math.sin(a) * .11, top + .85),
               (cx + math.cos(a) * r, cy + math.sin(a) * r, dome_z(r) + .02), .02, mat=IRON)
    K.emitter(g, 'steam', cx, cy, mouth + .02, .1)
    # Relief valve with a popping cap and a beacon mast.
    vx, vy = cx + .36, cy - .2
    vz = dome_z(math.hypot(vx - cx, vy - cy))
    g.cylinder((vx, vy, vz + .08), .08, .22, IRON, 'Z', 12)
    P.hoop(g, (vx, vy, vz + .18), .12, .04, .04, BRASS, segments=12)
    g.cylinder((vx, vy, vz + .27), .06, .18, PAINTED, 'Z', 12)
    cap = Geometry('CryogenicTankFarm.ReliefCap', (vx, vy, vz + .4))
    cap.cylinder((vx, vy, vz + .39), .085, .045, IRON, 'Z', 12)
    cap.cylinder((vx, vy, vz + .44), .03, .06, BRASS, 'Z', 8)
    parts.append((cap, 'PISTON_Z', .05))
    bx, by = cx - .32, cy + .3
    bz = dome_z(math.hypot(bx - cx, by - cy))
    blk(g, bx - .035, by - .035, bz - .1, bx + .035, by + .035, bz + .45, IRON)
    pivot = K.beacon(g, bx, by, bz + .45)
    parts.append((K.beacon_shutter(*pivot, 'CryogenicTankFarm.Beacon'), 'SPIN_Z', 1))


# ---------------------------------------------------------------- hydrogen bullets

def bullets(g):
    x0, x1 = BULLET_X
    for y in BULLETS_Y:
        C.horizontal_vessel(g, x0, x1, y, BULLET_Z, BULLET_R, mat=CONCRETE, bands=2, axis='X', segments=16)
        for x in (x0 + .35, x1 - .4):
            g.cylinder((x, y, BULLET_Z + BULLET_R + .045), .06, .12, IRON, 'Z', 10)
            P.hoop(g, (x, y, BULLET_Z + BULLET_R + .1), .085, .03, .03, BRASS, segments=10)
    # Cross-over between the two bullet tops.
    x = x1 - .4
    P.pipe(g, [(x, BULLETS_Y[0], BULLET_Z + BULLET_R + .12), (x, BULLETS_Y[0], 1.5),
               (x, BULLETS_Y[1], 1.5), (x, BULLETS_Y[1], BULLET_Z + BULLET_R + .12)], .04, flanges=False)


# ---------------------------------------------------------------- control hut

def hut(g):
    x0, y0, x1, y1 = HUT
    top = Q.storey_block(g, x0, y0, x1, y1, 2, infill=ORANGE, frame=WOOD, door=DOOR_X, door_id='Door0', roof=False,
                         ground_windows={'left': [(1.0, .55, 'grand')]},
                         windows={'front': [(.5, 1.5, .52, 'grand'), (1.5, 1.5, .52, 'grand')],
                                  'left': [(.5, 1.5, .52, 'grand'), (1.5, 1.5, .52, 'grand')],
                                  'right': [(1.0, 1.5, .52, 'grand')]})
    # Pitched gable of native teal roof planks, ridge along Y (roof variety).
    P.plank_roof(g, x0 + .05, y0 + .05, x1 - .05, y1 - .05, top, top + .7, ridge_axis='Y', overhang=.1, plank=.28)
    K.lamp(g, DOOR_X - .66, y0 - .01, .8, face='front')


# ---------------------------------------------------------------- compressor

def compressor(g, parts):
    # One cast slab under the compressor, vaporizers and manifold.
    blk(g, 2.06, 0.0, -.02, 4.0, 1.94, .25, CONCRETE)
    base = .25
    cy, cz = COMP_Y, COMP_Z
    for x in (2.3, 2.66):
        blk(g, x - .09, cy - .16, base - .02, x + .09, cy + .16, cz - .15, CONCRETE)
    g.cylinder((2.48, cy, cz), .21, .52, PAINTED, 'X', 18)
    for x in (2.24, 2.72):
        g.cylinder((x, cy, cz), .24, .045, IRON, 'X', 18)
    # Crosshead guide: open frame so the rod shows.
    blk(g, 2.75, cy - .1, cz - .15, 3.2, cy + .1, cz - .1, IRON)
    blk(g, 2.75, cy - .1, cz + .1, 3.2, cy + .1, cz + .15, IRON)
    for x in (2.79, 3.16):
        blk(g, x - .025, cy - .1, base - .02, x + .025, cy + .1, cz - .15, IRON)
    rod = Geometry('CryogenicTankFarm.PistonRod', (2.92, cy, cz))
    rod.cylinder((2.84, cy, cz), .028, .4, IRON, 'X', 8)
    blk(rod, 2.95, cy - .07, cz - .07, 3.08, cy + .07, cz + .07, PAINTED)
    parts.append((rod, 'PISTON_X', .07))
    # Flywheel on its bearing pedestals at the end of the skid (axis along X).
    fx, fy, fz = 3.62, cy, .62
    for x in (fx - .13, fx + .13):
        blk(g, x - .03, fy - .07, base - .02, x + .03, fy + .07, fz + .05, IRON)
    g.cylinder((fx, fy, fz), .04, .36, IRON, 'X', 10)
    g.cylinder((3.33, fy, fz), .04, .26, IRON, 'X', 10)
    fly = P.flywheel('CryogenicTankFarm.Flywheel', (fx, fy, fz), .3, axis='X', spokes=6)
    parts.append((fly, 'SPIN_X', 1))


# ---------------------------------------------------------------- vaporizers

def vaporizers(g):
    base = .25
    for x, y in VAPS:
        blk(g, x - .09, y - .09, base - .02, x + .09, y + .09, base + .07, IRON)
        g.cylinder((x, y, (base + .07 + VAP_TOP) / 2), .055, VAP_TOP - base - .07, IRON, 'Z', 10)
        for k in range(8):
            a = k * math.pi / 4
            c = (x + math.cos(a) * .14, y + math.sin(a) * .14, (base + .16 + VAP_TOP - .1) / 2)
            C.obox(g, c, (math.cos(a), math.sin(a), 0), (-math.sin(a), math.cos(a), 0), (0, 0, 1),
                   .085, .01, (VAP_TOP - base - .26) / 2, CONCRETE)
        g.cylinder((x, y, VAP_TOP + .035), .08, .07, IRON, 'Z', 10)


# ---------------------------------------------------------------- manifold and lines

def manifold(g):
    x0, y0, x1, y1 = 2.08, .32, 3.97, .74
    blk(g, x0, y0, .22, x1, y1, .5, CONCRETE)
    blk(g, x0 - .03, y0 - .03, .5, x1 + .02, y1 + .02, .56, IRON)
    for s in PIPE_SOCKETS:
        sx, sy, sz = s['socket']
        blk(g, sx - .23, sy + .04, sz - .23, sx + .23, y0 + .02, sz + .18, PAINTED)
        g.cylinder((sx, sy + .02, sz), .14, .08, IRON, 'Y', 16)
        P.hoop(g, (sx, sy - .03, sz), .18, .045, .04, BRASS, axis='Y', segments=16)
        K.bolt_row(g, (sx - .15, sy - .06, sz + .13), (sx + .15, sy - .06, sz + .13), 3, r=.015)
    # Vaporizer outlets down into the manifold, each with its valve.
    for x, y in VAPS:
        P.pipe(g, [(x, y - .09, .4), (x, y1 - .1, .4)], .04, flanges=False)
        P.valve(g, (x + .22, y1 + .02, .68), 'back', .08)
    P.gauge(g, 3.0, y0, .32, 'front', .07)


def lines(g):
    """Insulated lines from the bullets and the tank, low over the bund wall,
    into the vaporizer headers."""
    # LH2: from the front bullet's right head nozzle round the hut's back
    # corner to the left vaporizer.
    x = BULLET_X[1] - .4
    y = BULLETS_Y[0]
    P.pipe(g, [(x, y, BULLET_Z + BULLET_R + .12), (x, y, 1.95), (2.24, y, 1.95), (2.24, 1.0, 1.95),
               (VAPS[0][0], 1.0, 1.95), (VAPS[0][0], 1.0, VAP_TOP + .07)], .055, CONCRETE, flanges=False)
    # LOX: from the tank's foot to the right vaporizer.
    cx, cy = TANK
    P.pipe(g, [(cx, cy - TANK_R + .05, .55), (cx, 2.06, .55), (cx, 2.06, 1.95), (VAPS[1][0], 2.06, 1.95),
               (VAPS[1][0], 1.0, 1.95), (VAPS[1][0], 1.0, VAP_TOP + .07)], .055, CONCRETE, flanges=False)
    for px, py, pz in ((2.24, 1.5, 1.95), (3.5, 1.5, 1.95)):
        P.hoop(g, (px, py, pz), .075, .022, .04, IRON, axis='Y', segments=12)


def build(g, parts):
    bund(g)
    lox_tank(g, parts)
    bullets(g)
    hut(g)
    compressor(g, parts)
    vaporizers(g)
    manifold(g)
    lines(g)
