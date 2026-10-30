"""Launch Pad: the endgame launch site of the Deep Frontier space program.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the loose barrels on the deck.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; outputs/compaction/BRIEF.md): 12x12x18 -> 10x9x12, inside the old
footprint with the same origin, blockhouse door (x 9.5, face on y 1) and
native entrance (9,0,0). It stays the space program's landmark but loses its
scaffolding: the 15-layer lattice service tower is now a closed riveted tower
with the elevator on its back face, and the lattice lightning mast with its
catenary, the lattice water tower and its down-comer are gone. The pad is one
layer high (it was two), and the rocket is built at 0.8 scale so that it
still stands whole on the pad (base 1.95, top 11.99) and matches the stage in
the Rocket Assembly Hangar.

Hero: a riveted, banded teal-and-steel beaver rocket on a steel launch mount
over a water-deluged flame trench, beside a closed riveted service tower with
swing arms and a timber crew cabin at the capsule.
Roof types: open concrete launch deck (a roof deck); teal native plank
gables on the pump house and the crew cabin; flat teal plank cap on the
winch house atop the tower (roof variety).

Animated (names unchanged): elevator car (slide Z), two umbilical swing arms
(yaw), pump flywheel (spin), winch sheave (spin), tower beacon (spin). The
mast beacon went with the lattice mast.

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
FOOTPRINT = (10, 9)
HEIGHT = 12
FRAME_END = 121
HERO = 'Banded teal beaver rocket on a deluged flame trench beside a closed riveted service tower with swing arms'

DECK = 1.0
PAD = (0.0, 1.0, 10.0, 9.0)           # x0, y0, x1, y1: whole tiles to the footprint edges
TRENCH = (3.1, 5.9)                   # trench x span; runs from the front face back to TRENCH_BACK
TRENCH_BACK = 6.6
TRENCH_FLOOR = .12
SLAB = .7                             # underside of the deck slab over the trench
ROCKET = (4.5, 5.0)
SCALE = .8                            # rocket scale (it stands whole within HEIGHT)
HOLE = (3.75, 4.25, 5.25, 5.75)       # opening in the deck under the mount
MOUNT_TOP = 1.6
ROCKET_BASE = 1.95
TOWER = (6.45, 4.2, 8.05, 5.8)
TOWER_TOP = 9.0
LEVELS = (4, 6, 9)                    # swing arms (+0.85) and crew arm (deck) layers
DOOR_X = 9.5
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
    bx(g, tx0 - .2, y0 - .12, SLAB - .14, tx1 + .2, y0 + .02, DECK - .1, CONCRETE)
    bx(g, tx0 + .1, y0 - .16, SLAB - .1, tx1 - .1, y0 - .12, SLAB + .08, FORGED)
    # Spillway walls carry the deluge out over the front strip.
    for xa, xb in ((math.floor(tx0), tx0), (tx1, math.ceil(tx1))):
        bx(g, xa, 0.0, -BURY, xb, y0, .5, CONCRETE)
        bx(g, xa - .03, -.03, .47, xb + .03, y0 - .03, .56, CONCRETE)
    coping_ring(g, x0, y0, x1, y1, DECK)
    skip_front = [(tx0 - .3, tx1 + .3), (DOOR_X - .5, DOOR_X + .5)]
    pilasters(g, 'X', y0, x0, x1, .1, DECK - .14, -1, skip=skip_front)
    pilasters(g, 'X', y1, x0, x1, .1, DECK - .14, 1)
    pilasters(g, 'Y', x0, y0, y1, .1, DECK - .14, -1)
    pilasters(g, 'Y', x1, y0, y1, .1, DECK - .14, 1)
    g.liquid_surfaces.append(dict(name='Deluge', shape='Rectangle', center=[(tx0 + tx1) / 2, (.12 + TRENCH_BACK) / 2],
                                  bottom=TRENCH_FLOOR, top=.4, scale=[tx1 - tx0 - .02, TRENCH_BACK - .14],
                                  flowOnly=False))
    # Flame deflector: riveted steel wedge sloping out toward the mouth.
    prof = [(4.0, TRENCH_FLOOR - .04), (TRENCH_BACK - .02, TRENCH_FLOOR - .04), (TRENCH_BACK - .02, SLAB - .08),
            (5.7, SLAB - .08)]
    extrude_profile(g, prof, tx0 + .05, tx1 - .05, FORGED, axis='X')
    # Blast plates on the deck around the mount.
    for (a, b, c, d) in ((2.75, 3.6, 6.25, 3.9), (2.75, 6.1, 6.25, 6.4)):
        bx(g, a, b, DECK - BURY, c, d, DECK + .04, FORGED)


def mount(g):
    hx0, hy0, hx1, hy1 = HOLE
    cx, cy = ROCKET
    for x in (3.45, 5.55):
        for y in (3.95, 6.05):
            bx(g, x - .25, y - .25, DECK - BURY, x + .25, y + .25, MOUNT_TOP - .24, CONCRETE)
            bx(g, x - .28, y - .28, MOUNT_TOP - .26, x + .28, y + .28, MOUNT_TOP - .22, IRON)
    t0, t1 = MOUNT_TOP - .22, MOUNT_TOP
    bx(g, 3.15, 3.65, t0, 5.85, hy0, t1, FORGED)
    bx(g, 3.15, hy1, t0, 5.85, 6.35, t1, FORGED)
    bx(g, 3.15, hy0, t0, hx0, hy1, t1, FORGED)
    bx(g, hx1, hy0, t0, 5.85, hy1, t1, FORGED)
    for y in (3.63, 6.37):
        bx(g, 3.13, y - .03, t0 - .04, 5.87, y + .03, t1 + .02, IRON)
    for x in (3.13, 5.87):
        bx(g, x - .03, 3.66, t0 - .04, x + .03, 6.34, t1 + .02, IRON)
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        px, py = cx + math.cos(a) * .88, cy + math.sin(a) * .88
        bx(g, px - .12, py - .12, t1 - BURY, px + .12, py + .12, ROCKET_BASE + .08, IRON)
        g.beam((px, py, ROCKET_BASE + .02), (cx + math.cos(a) * .7, cy + math.sin(a) * .7, ROCKET_BASE + .15),
               .08, mat=IRON)
        bx(g, px - .14, py - .14, ROCKET_BASE + .06, px + .14, py + .14, ROCKET_BASE + .11, BRASS)


def tower(g, parts):
    """Closed riveted service tower: forged shaft on a concrete base, timber
    winch house on top, elevator on the back face."""
    x0, y0, x1, y1 = TOWER
    bx(g, x0, y0, DECK - BURY, x1, y1, DECK + .6, CONCRETE)
    bx(g, x0 + .05, y0 + .05, DECK + .6, x1 - .05, y1 - .05, TOWER_TOP, FORGED)
    for x in (x0 + .05, x1 - .05):
        for y in (y0 + .05, y1 - .05):
            bx(g, x - .08, y - .08, DECK + .6, x + .08, y + .08, TOWER_TOP - .02, IRON)
    for z in LEVELS[:2] + (7.5,):
        bx(g, x0 - .01, y0 - .01, z - .06, x1 + .01, y1 + .01, z + .06, IRON)
    for z in (3.0, 5.0, 7.0, 8.4):
        window(g, (x0 + x1) / 2, y0 + .05, z, .45, 'front', 'factory')
    bx(g, x0 - .04, y0 - .04, TOWER_TOP, x1 + .04, y1 + .04, TOWER_TOP + .1, IRON)
    # Elevator guide rails and car on the back face (animated, slides up and back).
    for x in (6.85, 7.65):
        bx(g, x - .03, y1, DECK + .6, x + .03, y1 + .06, TOWER_TOP - .1, IRON)
    car = Geometry('LaunchPad.ElevatorCar', (7.25, y1 + .35, DECK + .65))
    cz = DECK + .66
    bx(car, 6.8, y1 + .07, cz, 7.7, y1 + .62, cz + .07, IRON)
    bx(car, 6.8, y1 + .07, cz + .9, 7.7, y1 + .62, cz + .97, IRON)
    for x in (6.84, 7.66):
        bx(car, x - .035, y1 + .55, cz + .07, x + .035, y1 + .6, cz + .9, IRON)
    bx(car, 6.86, y1 + .09, cz + .07, 7.64, y1 + .14, cz + .9, FORGED)
    car.cylinder((7.25, y1 + .35, cz + 1.0), .05, .07, BRASS)
    parts.append((car, 'SLIDE_Z', LEVELS[1] - DECK - .6))
    # Timber winch house on the tower top, flat roofed.
    hz = TOWER_TOP + .1
    bx(g, x0 + .15, y0 + .15, hz, x1 - .15, y1 - .15, hz + .78, PLANK)
    for x in (x0 + .15, x1 - .15):
        for y in (y0 + .15, y1 - .15):
            bx(g, x - .05, y - .05, hz, x + .05, y + .05, hz + .78, WOOD)
    window(g, (x0 + x1) / 2, y0 + .15, hz + .38, .4, 'front', 'factory')
    bx(g, x0 + .05, y0 + .05, hz + .78, x1 - .05, y1 - .05, hz + .9, ROOF)
    sheave = Geometry('LaunchPad.WinchSheave', (x1 - .05, 5.0, hz + .38))
    wheel(sheave, (x1 + .02, 5.0, hz + .38), .26, 'X')
    parts.append((sheave, 'SPIN_X', 2))
    bx(g, 7.21, 4.96, hz + .9, 7.29, 5.04, 11.0, IRON)
    pivot = beacon(g, 7.25, 5.0, 11.0)
    parts.append((beacon_shutter(*pivot, 'LaunchPad.TowerBeacon'), 'SPIN_Z', 3))


def swing_arm(name, z, length, *, pipes=True):
    """Truss umbilical arm pivoting on the tower's left face, pointing -X."""
    px, py = TOWER[0] - .06, 5.0
    arm = Geometry(name, (px, py, z))
    xe = px - length
    for dy in (-.15, .15):
        for dz in (0, .34):
            arm.box(((px + xe) / 2, py + dy, z + dz), (length, .06, .06), IRON)
    n = max(2, round(length / .4))
    for k in range(n):
        xa = px - length * k / n
        xb = px - length * (k + 1) / n
        for dy in (-.15, .15):
            arm.beam((xa, py + dy, z + .03), (xb, py + dy, z + .31), .04, mat=IRON)
        arm.box((xb, py, z + .17), (.045, .32, .045), IRON)
    arm.box((px + .02, py, z + .17), (.08, .4, .5), IRON)
    arm.box((xe - .035, py, z + .17), (.07, .42, .46), ORANGE)
    arm.box((xe - .085, py, z + .17), (.05, .34, .38), IRON)
    if pipes:
        for dy, mat in ((-.07, CONCRETE), (.07, PAINTED)):
            arm.cylinder(((px + xe) / 2 + .02, py + dy, z - .08), .04, length - .1, mat, 'X', 10)
    return arm


def crew_arm(g, z):
    """Fixed crew access arm with a timber white-room cabin at the capsule hatch."""
    x0 = TOWER[0] - .02
    xe = ROCKET[0] + .62
    bx(g, xe + .63, 4.66, z - .07, x0, 5.34, z, IRON)
    for y in (4.7, 5.3):
        rail(g, (xe + .6, y), (x0 - .05, y), z, pitch=.5, height=.55)
    timber_hut(g, xe - .03, 4.55, xe + .58, 5.45, z - .08, z + .85, z + 1.15, ridge_axis='X', infill=GREYPLANK)


def pump_house(g, parts):
    """Deluge pump house on the deck: concrete base, timber upper, flat roof."""
    x0, y0, x1, y1 = .55, 1.6, 2.45, 3.4
    bx(g, x0, y0, DECK - BURY, x1, y1, DECK + .8, CONCRETE)
    coping_ring(g, x0, y0, x1, y1, DECK + .8, w=.14, proud=.03, h=.1)
    bx(g, x0 + .1, y0 + .1, DECK + .84, x1 - .1, y1 - .1, DECK + 1.88, PLANK)
    for x in (x0 + .1, x1 - .1):
        for y in (y0 + .1, y1 - .1):
            bx(g, x - .05, y - .05, DECK + .84, x + .05, y + .05, DECK + 1.88, WOOD)
    window(g, 1.5, y0 + .1, DECK + 1.3, .5, 'front', 'factory')
    import lategame_mining_parts as M
    M.plank_gable(g, x0 + .1, x1 - .1, y0 + .1, y1 - .1, DECK + 1.88, DECK + 2.45, ridge_axis='Y', overhang=.1, seed=23)
    window(g, 1.5, y0, DECK + .42, .45, 'front', 'factory')
    # Flywheel and drive housing on the right side (animated wheel).
    bx(g, x1, 2.25, DECK - BURY, x1 + .3, 2.85, DECK + .48, PAINTED)
    fly = Geometry('LaunchPad.PumpFlywheel', (x1 + .42, 2.55, DECK + .55))
    wheel(fly, (x1 + .42, 2.55, DECK + .55), .42, 'X')
    fly.cylinder((x1 + .42, 2.55, DECK + .55), .1, .2, PAINTED, 'X', 12)
    parts.append((fly, 'SPIN_X', 3))
    pipe(g, [(x1 - .15, 2.0, DECK + .3), (2.95, 2.0, DECK + .3), (2.95, 2.0, DECK - .1)], r=.07, mat=PAINTED)
    gauge(g, x0, 2.0, DECK + .45, 'left', .09)


def cryo_farm(g):
    """Frost-white insulated bullet tanks feeding the tower."""
    for y, r in ((2.0, .45), (3.15, .45)):
        h_tank(g, 6.7, 9.6, y, DECK + .62, r, mat=CONCRETE, band_mat=IRON, bands=3, saddles=2, ground=DECK)
    for x, mat in ((6.75, CONCRETE), (7.75, PAINTED)):
        pipe(g, [(x, 3.15 + .42, DECK + .62), (x, 4.12, DECK + .62), (x, 4.12, LEVELS[1] - .2),
                 (x, 4.45, LEVELS[1] - .2)], r=.06, mat=mat)
    gauge(g, 7.25, 3.62, DECK + .7, 'front', .08)


def deluge_manifold(g):
    """Spray bars around the launch mount, fed from the pump house."""
    z = DECK + .18
    pipe(g, [(2.9, 6.5, z), (2.9, 3.48, z), (6.1, 3.48, z), (6.1, 6.0, z)], r=.06, mat=PAINTED)
    for k in range(5):
        g.cylinder((3.3 + k * .6, 3.58, z + .04), .025, .12, BRASS, 'Y', 8)


def rails(g):
    """Transporter rails from the back edge to the mount."""
    for k in range(9):
        y = 6.65 + k * .27
        bx(g, 3.75, y - .06, DECK - BURY, 5.25, y + .06, DECK + .06, WOOD)
    for x in (4.1, 4.9):
        bx(g, x - .035, 6.6, DECK + .05, x + .035, 8.9, DECK + .13, IRON)


def rocket_exhaust(origin):
    """Engine plume from just under the bells down through the mount opening
    into the flame trench, widening below the deck slab."""
    ex = Geometry(EXHAUST_NODE, origin)
    cx, cy = ROCKET
    z0 = TRENCH_FLOOR
    prof = [(.9, 0), (.62, .45), (.42, .85), (.42, 1.2), (.38, 1.32)]
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
    parts.append((swing_arm('LaunchPad.UmbilicalArmLow', LEVELS[0] + .85, 1.0), 'CUSTOM_YAW_SWING', -1.1))
    parts.append((swing_arm('LaunchPad.UmbilicalArmHigh', LEVELS[1] + .85, 1.2), 'CUSTOM_YAW_SWING', 1.0))
    crew_arm(g, LEVELS[2])
    pump_house(g, parts)
    cryo_farm(g)
    rails(g)
    deluge_manifold(g)
    for x in (8.5,):
        lamp(g, x, 1.0, .65, face='front')
