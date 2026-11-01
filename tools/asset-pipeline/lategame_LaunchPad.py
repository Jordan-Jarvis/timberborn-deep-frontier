"""Launch Pad: the endgame launch site of the Deep Frontier space program.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the loose barrels on the deck.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; outputs/compaction/BRIEF.md): 12x12x18 -> 10x9x12. The lattice
service tower became a closed riveted tower, the lattice lightning mast and
water tower went, and the pad became one layer high.

Shrunk again 2026-11-01 (user: "we need to shrink the buildings down even
more"): 10x9x12 -> 7x7x9, inside the old footprint with the same origin.
The blockhouse door stays on the last tile of the deck's front face (x 9.5
-> 6.5), so the native entrance moves from (9,0,0) to (6,0,0). The rocket is
built at 0.55 scale (was 0.8) so that it still stands whole on the pad
(base 1.65) and matches the stage in the Rocket Assembly Hangar; the mount,
trench, tower (top 6.6), swing arms, crew cabin, pump house and bullet tanks
shrink with it.

Hero: a riveted, banded teal-and-steel beaver rocket on a steel launch mount
over a water-deluged flame trench, beside a closed riveted service tower with
swing arms and a timber crew cabin at the capsule.
Roof types: open concrete launch deck (a roof deck); teal native plank
gables on the pump house and the crew cabin; flat teal plank cap on the
winch house atop the tower (roof variety).

Animated (names unchanged): elevator car (slide Z), two umbilical swing arms
(yaw), pump flywheel (spin), winch sheave (spin), tower beacon (spin).

Runtime nodes (un-animated here; the rocket program drives them): the rocket
is its own part, LaunchPad.Rocket, with its origin at the rocket base, and its
engine flame, LaunchPad.RocketExhaust, is a child of it. The game hides the
rocket when idle, shows it from the start of preparation and raises it on
launch. Both are declared in the study's animatedParts (kinds CUSTOM_ROCKET
and CUSTOM_ROCKET_EXHAUST, which add no keyframes) so the code can require them.
"""
import math

from lategame_kit import *
from frontier_architecture import Geometry
from architectural_windows import window
from lategame_space_parts import (bx, door_block, pilasters, coping_ring, gauge, pipe, h_tank, timber_hut,
                                  rocket, rail, BURY)
from lategame_space_parts import animate as space_animate

IDENT = 'LaunchPad'
FOOTPRINT = (7, 7)
HEIGHT = 9
FRAME_END = 121
HERO = 'Banded teal beaver rocket on a deluged flame trench beside a closed riveted service tower with swing arms'

DECK = 1.0
PAD = (0.0, 1.0, 7.0, 7.0)            # x0, y0, x1, y1: whole tiles to the footprint edges
TRENCH = (2.1, 3.9)                   # trench x span; runs from the front face back to TRENCH_BACK
TRENCH_BACK = 5.0
TRENCH_FLOOR = .12
SLAB = .7                             # underside of the deck slab over the trench
ROCKET = (3.0, 4.0)
SCALE = .55                           # rocket scale (it stands whole within HEIGHT; the hangar's stage matches)
HOLE = (2.65, 3.65, 3.35, 4.35)       # opening in the deck under the mount
MOUNT_TOP = 1.4
ROCKET_BASE = 1.65
TOWER = (4.4, 3.4, 5.6, 4.6)
TOWER_TOP = 6.6
LEVELS = (3, 4, 6)                    # swing arms (+0.85) and crew arm (deck) layers
DOOR_X = 6.5
ROCKET_NODE = 'LaunchPad.Rocket'
EXHAUST_NODE = 'LaunchPad.RocketExhaust'


def pad(g):
    x0, y0, x1, y1 = PAD
    tx0, tx1 = TRENCH
    bx(g, x0, y0, 0, tx0, y1, DECK, CONCRETE)
    door_block(g, tx1, y0, x1, y1, 0, DECK, DOOR_X, door_id='PadBlockhouseDoor')
    bx(g, tx0, TRENCH_BACK, 0, tx1, y1, DECK, CONCRETE)
    bx(g, tx0, y0 - 1.0, -BURY, tx1, TRENCH_BACK, TRENCH_FLOOR, CONCRETE)
    hx0, hy0, hx1, hy1 = HOLE
    bx(g, tx0, y0, SLAB, tx1, hy0, DECK, CONCRETE)
    bx(g, tx0, hy1, SLAB, tx1, TRENCH_BACK, DECK, CONCRETE)
    bx(g, tx0, hy0, SLAB, hx0, hy1, DECK, CONCRETE)
    bx(g, hx1, hy0, SLAB, tx1, hy1, DECK, CONCRETE)
    # Heavy lintel over the trench mouth with a riveted blast plate.
    bx(g, tx0 - .15, y0 - .12, SLAB - .14, tx1 + .15, y0 + .02, DECK - .1, CONCRETE)
    bx(g, tx0 + .1, y0 - .16, SLAB - .1, tx1 - .1, y0 - .12, SLAB + .08, FORGED)
    # Spillway walls carry the deluge out over the front strip.
    for xa, xb in ((math.floor(tx0), tx0), (tx1, math.ceil(tx1))):
        bx(g, xa, 0.0, -BURY, xb, y0, .5, CONCRETE)
        bx(g, xa - .03, -.03, .47, xb + .03, y0 - .03, .56, CONCRETE)
    # Proud cast coping band on the deck's edge faces, its top 12 mm under the
    # deck: no cap strip stands on the deck (roofs are platforms).
    coping_ring(g, x0, y0, x1, y1, DECK - .052)
    skip_front = [(tx0 - .3, tx1 + .3), (DOOR_X - .5, DOOR_X + .5)]
    pilasters(g, 'X', y0, x0, x1, .1, DECK - .14, -1, skip=skip_front)
    pilasters(g, 'X', y1, x0, x1, .1, DECK - .14, 1)
    pilasters(g, 'Y', x0, y0, y1, .1, DECK - .14, -1)
    pilasters(g, 'Y', x1, y0, y1, .1, DECK - .14, 1)
    g.liquid_surfaces.append(dict(name='Deluge', shape='Rectangle', center=[(tx0 + tx1) / 2, (.12 + TRENCH_BACK) / 2],
                                  bottom=TRENCH_FLOOR, top=.4, scale=[tx1 - tx0 - .02, TRENCH_BACK - .14],
                                  flowOnly=False))
    # Flame deflector: riveted steel wedge sloping out toward the mouth.
    prof = [(3.0, TRENCH_FLOOR - .04), (TRENCH_BACK - .02, TRENCH_FLOOR - .04), (TRENCH_BACK - .02, SLAB - .08),
            (4.5, SLAB - .08)]
    extrude_profile(g, prof, tx0 + .05, tx1 - .05, FORGED, axis='X')
    # Blast plates on the deck around the mount.
    for (a, b, c, d) in ((1.95, 2.95, 4.05, 3.15), (1.95, 4.85, 4.05, 5.05)):
        bx(g, a, b, DECK - BURY, c, d, DECK + .04, FORGED)


def mount(g):
    hx0, hy0, hx1, hy1 = HOLE
    cx, cy = ROCKET
    for x in (cx - .75, cx + .75):
        for y in (cy - .75, cy + .75):
            bx(g, x - .18, y - .18, DECK - BURY, x + .18, y + .18, MOUNT_TOP - .18, CONCRETE)
            bx(g, x - .2, y - .2, MOUNT_TOP - .2, x + .2, y + .2, MOUNT_TOP - .16, IRON)
    t0, t1 = MOUNT_TOP - .16, MOUNT_TOP
    a0, a1 = cx - .95, cx + .95
    b0, b1 = cy - .95, cy + .95
    bx(g, a0, b0, t0, a1, hy0, t1, FORGED)
    bx(g, a0, hy1, t0, a1, b1, t1, FORGED)
    bx(g, a0, hy0, t0, hx0, hy1, t1, FORGED)
    bx(g, hx1, hy0, t0, a1, hy1, t1, FORGED)
    for y in (b0 - .02, b1 + .02):
        bx(g, a0 - .02, y - .025, t0 - .03, a1 + .02, y + .025, t1 + .015, IRON)
    for x in (a0 - .02, a1 + .02):
        bx(g, x - .025, b0 + .005, t0 - .03, x + .025, b1 - .005, t1 + .015, IRON)
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        px, py = cx + math.cos(a) * .62, cy + math.sin(a) * .62
        bx(g, px - .09, py - .09, t1 - BURY, px + .09, py + .09, ROCKET_BASE + .06, IRON)
        g.beam((px, py, ROCKET_BASE + .02), (cx + math.cos(a) * .48, cy + math.sin(a) * .48, ROCKET_BASE + .12),
               .06, mat=IRON)
        bx(g, px - .11, py - .11, ROCKET_BASE + .04, px + .11, py + .11, ROCKET_BASE + .08, BRASS)


def tower(g, parts):
    """Closed riveted service tower: forged shaft on a concrete base, timber
    winch house on top, elevator on the back face."""
    x0, y0, x1, y1 = TOWER
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bx(g, x0, y0, DECK - BURY, x1, y1, DECK + .5, CONCRETE)
    bx(g, x0 + .05, y0 + .05, DECK + .5, x1 - .05, y1 - .05, TOWER_TOP, FORGED)
    for x in (x0 + .05, x1 - .05):
        for y in (y0 + .05, y1 - .05):
            bx(g, x - .07, y - .07, DECK + .5, x + .07, y + .07, TOWER_TOP - .02, IRON)
    for z in LEVELS[:2] + (5.5,):
        bx(g, x0 - .01, y0 - .01, z - .05, x1 + .01, y1 + .01, z + .05, IRON)
    for z in (2.3, 3.6, 4.8, 6.0):
        window(g, cx, y0 + .05, z, .38, 'front', 'factory')
    bx(g, x0 - .04, y0 - .04, TOWER_TOP, x1 + .04, y1 + .04, TOWER_TOP + .1, IRON)
    # Elevator guide rails and car on the back face (animated, slides up and back).
    for x in (cx - .32, cx + .32):
        bx(g, x - .03, y1, DECK + .5, x + .03, y1 + .05, TOWER_TOP - .1, IRON)
    car = Geometry('LaunchPad.ElevatorCar', (cx, y1 + .28, DECK + .55))
    cz = DECK + .56
    bx(car, cx - .36, y1 + .06, cz, cx + .36, y1 + .5, cz + .06, IRON)
    bx(car, cx - .36, y1 + .06, cz + .8, cx + .36, y1 + .5, cz + .86, IRON)
    for x in (cx - .33, cx + .33):
        bx(car, x - .03, y1 + .44, cz + .06, x + .03, y1 + .48, cz + .8, IRON)
    bx(car, cx - .31, y1 + .08, cz + .06, cx + .31, y1 + .12, cz + .8, FORGED)
    car.cylinder((cx, y1 + .28, cz + .89), .045, .06, BRASS)
    parts.append((car, 'SLIDE_Z', LEVELS[1] - DECK - .5))
    # Timber winch house on the tower top, flat roofed.
    hz = TOWER_TOP + .1
    bx(g, x0 + .12, y0 + .12, hz, x1 - .12, y1 - .12, hz + .66, PLANK)
    for x in (x0 + .12, x1 - .12):
        for y in (y0 + .12, y1 - .12):
            bx(g, x - .045, y - .045, hz, x + .045, y + .045, hz + .66, WOOD)
    window(g, cx, y0 + .12, hz + .33, .34, 'front', 'factory')
    bx(g, x0 + .04, y0 + .04, hz + .66, x1 - .04, y1 - .04, hz + .76, ROOF)
    sheave = Geometry('LaunchPad.WinchSheave', (x1 - .04, cy, hz + .33))
    wheel(sheave, (x1 + .02, cy, hz + .33), .22, 'X')
    parts.append((sheave, 'SPIN_X', 2))
    bx(g, cx - .035, cy - .035, hz + .76, cx + .035, cy + .035, 8.1, IRON)
    pivot = beacon(g, cx, cy, 8.1)
    parts.append((beacon_shutter(*pivot, 'LaunchPad.TowerBeacon'), 'SPIN_Z', 3))


def swing_arm(name, z, length, *, pipes=True):
    """Truss umbilical arm pivoting on the tower's left face, pointing -X."""
    px, py = TOWER[0] - .05, ROCKET[1]
    arm = Geometry(name, (px, py, z))
    xe = px - length
    for dy in (-.12, .12):
        for dz in (0, .28):
            arm.box(((px + xe) / 2, py + dy, z + dz), (length, .05, .05), IRON)
    n = max(2, round(length / .35))
    for k in range(n):
        xa = px - length * k / n
        xb = px - length * (k + 1) / n
        for dy in (-.12, .12):
            arm.beam((xa, py + dy, z + .025), (xb, py + dy, z + .255), .035, mat=IRON)
        arm.box((xb, py, z + .14), (.04, .26, .04), IRON)
    arm.box((px + .02, py, z + .14), (.07, .32, .42), IRON)
    arm.box((xe - .03, py, z + .14), (.06, .34, .38), ORANGE)
    arm.box((xe - .07, py, z + .14), (.04, .28, .32), IRON)
    if pipes:
        for dy, mat in ((-.06, CONCRETE), (.06, PAINTED)):
            arm.cylinder(((px + xe) / 2 + .02, py + dy, z - .07), .035, length - .1, mat, 'X', 10)
    return arm


def crew_arm(g, z):
    """Fixed crew access arm with a timber white-room cabin at the capsule hatch."""
    x0 = TOWER[0] - .02
    xe = ROCKET[0] + .5
    cy = ROCKET[1]
    bx(g, xe + .5, cy - .28, z - .06, x0, cy + .28, z, IRON)
    for y in (cy - .25, cy + .25):
        rail(g, (xe + .48, y), (x0 - .04, y), z, pitch=.4, height=.5)
    timber_hut(g, xe - .03, cy - .38, xe + .48, cy + .38, z - .07, z + .75, z + 1.0, ridge_axis='X', infill=GREYPLANK)


def pump_house(g, parts):
    """Deluge pump house on the deck: concrete base, timber upper, plank gable."""
    x0, y0, x1, y1 = .3, 1.35, 1.65, 2.75
    bx(g, x0, y0, DECK - BURY, x1, y1, DECK + .7, CONCRETE)
    coping_ring(g, x0, y0, x1, y1, DECK + .7, w=.12, proud=.03, h=.09)
    bx(g, x0 + .08, y0 + .08, DECK + .74, x1 - .08, y1 - .08, DECK + 1.6, PLANK)
    for x in (x0 + .08, x1 - .08):
        for y in (y0 + .08, y1 - .08):
            bx(g, x - .045, y - .045, DECK + .74, x + .045, y + .045, DECK + 1.6, WOOD)
    window(g, (x0 + x1) / 2, y0 + .08, DECK + 1.15, .42, 'front', 'factory')
    import lategame_mining_parts as M
    M.plank_gable(g, x0 + .08, x1 - .08, y0 + .08, y1 - .08, DECK + 1.6, DECK + 2.08, ridge_axis='Y', overhang=.08, seed=23)
    window(g, (x0 + x1) / 2, y0, DECK + .38, .38, 'front', 'factory')
    # Flywheel and drive housing on the right side (animated wheel).
    my = (y0 + y1) / 2
    bx(g, x1, my - .25, DECK - BURY, x1 + .22, my + .25, DECK + .4, PAINTED)
    fly = Geometry('LaunchPad.PumpFlywheel', (x1 + .32, my, DECK + .42))
    wheel(fly, (x1 + .32, my, DECK + .42), .3, 'X')
    fly.cylinder((x1 + .32, my, DECK + .42), .08, .16, PAINTED, 'X', 12)
    parts.append((fly, 'SPIN_X', 3))
    pipe(g, [(x1 - .12, y0 + .3, DECK + .25), (1.95, y0 + .3, DECK + .25), (1.95, y0 + .3, DECK - .1)], r=.06, mat=PAINTED)
    gauge(g, x0, my, DECK + .4, 'left', .08)


def cryo_farm(g):
    """Frost-white insulated bullet tanks feeding the tower."""
    for y in (1.55, 2.45):
        h_tank(g, 4.5, 6.75, y, DECK + .5, .36, mat=CONCRETE, band_mat=IRON, bands=3, saddles=2, ground=DECK)
    for x, mat in ((4.75, CONCRETE), (5.35, PAINTED)):
        pipe(g, [(x, 2.45 + .34, DECK + .5), (x, 3.2, DECK + .5), (x, 3.2, LEVELS[1] - .2),
                 (x, 3.38, LEVELS[1] - .2)], r=.05, mat=mat)
    gauge(g, 5.05, 2.8, DECK + .58, 'front', .07)


def deluge_manifold(g):
    """Spray bars around the launch mount, fed from the pump house."""
    z = DECK + .16
    cx, cy = ROCKET
    pipe(g, [(cx - 1.05, cy + .9, z), (cx - 1.05, cy - 1.05, z), (cx + 1.05, cy - 1.05, z), (cx + 1.05, cy + .6, z)],
         r=.05, mat=PAINTED)
    for k in range(4):
        g.cylinder((cx - .6 + k * .4, cy - .97, z + .035), .022, .1, BRASS, 'Y', 8)


def rails(g):
    """Transporter rails from the back edge to the mount."""
    cx = ROCKET[0]
    for k in range(7):
        y = 5.15 + k * .27
        bx(g, cx - .55, y - .05, DECK - BURY, cx + .55, y + .05, DECK + .05, WOOD)
    for x in (cx - .25, cx + .25):   # rails on the tile line's edge band: the deck cells stay placeable
        bx(g, x - .03, 5.13, DECK + .04, x + .03, 6.9, DECK + .11, IRON)


def rocket_exhaust(origin):
    """Engine plume from just under the bells down through the mount opening
    into the flame trench, widening below the deck slab."""
    ex = Geometry(EXHAUST_NODE, origin)
    cx, cy = ROCKET
    z0 = TRENCH_FLOOR
    prof = [(.65, 0), (.44, .4), (.3, .75), (.3, 1.0), (.27, 1.1)]
    revolve(ex, (cx, cy, z0), prof, GLOW, segments=8)
    return ex


def animate(obj, kind, value, frame_end):
    """Rocket nodes carry no keyframes (the rocket program moves them); the
    exhaust sits at the rocket's origin as its child so it lifts with it.
    Every other custom kind is the shared space-program set."""
    if kind == 'CUSTOM_ROCKET':
        return
    if kind == 'CUSTOM_ROCKET_EXHAUST':
        import bpy
        rocket_obj = bpy.data.objects[ROCKET_NODE]
        if tuple(obj.location) != tuple(rocket_obj.location):
            raise ValueError('The rocket exhaust must share the rocket origin')
        obj.parent = rocket_obj
        obj.location = (0, 0, 0)
        return
    space_animate(obj, kind, value, frame_end)


def build(g, parts):
    pad(g)
    mount(g)
    origin = (*ROCKET, ROCKET_BASE)
    r = Geometry(ROCKET_NODE, origin)
    rocket(r, *ROCKET, ROCKET_BASE, scale=SCALE, primary=PAINTED, secondary=IRON)
    parts.append((r, 'CUSTOM_ROCKET', 0))
    parts.append((rocket_exhaust(origin), 'CUSTOM_ROCKET_EXHAUST', 0))
    tower(g, parts)
    parts.append((swing_arm('LaunchPad.UmbilicalArmLow', LEVELS[0] + .85, .8), 'CUSTOM_YAW_SWING', -1.1))
    parts.append((swing_arm('LaunchPad.UmbilicalArmHigh', LEVELS[1] + .85, .9), 'CUSTOM_YAW_SWING', 1.0))
    crew_arm(g, LEVELS[2])
    pump_house(g, parts)
    cryo_farm(g)
    rails(g)
    deluge_manifold(g)
    for x in (5.5,):
        lamp(g, x, 1.0, .65, face='front')
