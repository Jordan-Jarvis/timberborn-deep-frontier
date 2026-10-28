"""Launch Pad: the endgame launch site of the Deep Frontier space program.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the loose barrels on the deck.

Hero: a riveted, banded teal-and-steel beaver rocket standing on a steel
launch mount over a water-deluged flame trench, beside a tall lattice service
tower with swing arms and a timber crew cabin at the capsule.
Roof types: open concrete launch deck; small teal gable roofs on the timber
pump house, crew cabin and the winch house that caps the service tower.

Parts: a 2-layer cast concrete pad with a covered flame trench running out to
the front, where the native deluge water spills from an arched mouth; a steel
flame deflector inside; a launch mount on concrete pedestals; the service
tower with grating platforms, an elevator, two swinging umbilical arms and a
fixed crew access arm; a deluge pump house with a flywheel; frost-white
cryogenic bullet tanks feeding insulated lines up the tower; two lightning
masts with beacons and a catenary wire; transporter rails from the back edge.

Animated: elevator car (slide Z), two umbilical swing arms (yaw), pump
flywheel (spin), winch sheave (spin), two beacon shutters (spin).

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
from native_building_assets import barrel
from lategame_space_parts import (bx, door_block, pilasters, coping_ring, gauge, ball, pipe, pipe_support,
                                  h_tank, grating_ring, timber_hut, rocket, rail, lattice, BURY)
from lategame_space_parts import animate as space_animate

IDENT = 'LaunchPad'
FOOTPRINT = (12, 12)
HEIGHT = 18
FRAME_END = 121
HERO = 'Banded teal beaver rocket on a deluged flame trench beside a lattice service tower with swing arms'

DECK = 2.0
PAD = (0.0, 1.0, 12.0, 12.0)          # x0, y0, x1, y1: whole tiles to the footprint edges
TRENCH = (3.6, 6.4)                   # trench x span; runs from the front face back to TRENCH_BACK
TRENCH_BACK = 8.2
TRENCH_FLOOR = .3
SLAB = 1.55                           # underside of the deck slab over the trench
ROCKET = (5.0, 6.0)
HOLE = (4.1, 5.1, 5.9, 6.9)           # opening in the deck under the mount
MOUNT_TOP = 2.75
ROCKET_BASE = 3.1
TOWER = (7.4, 5.0, 9.4, 7.0)
TOWER_TOP = 15.0
LEVELS = (6, 9, 12)
DOOR_X = 9.5
ROCKET_NODE = 'LaunchPad.Rocket'
EXHAUST_NODE = 'LaunchPad.RocketExhaust'


def pad(g):
    x0, y0, x1, y1 = PAD
    tx0, tx1 = TRENCH
    # Solid pours either side of the trench, and behind it.
    bx(g, x0, y0, 0, tx0, y1, DECK, CONCRETE)
    door_block(g, tx1, y0, x1, y1, 0, DECK, DOOR_X, door_id='PadBlockhouseDoor')
    bx(g, tx0, TRENCH_BACK, 0, tx1, y1, DECK, CONCRETE)
    # Trench floor and the slab roofing it, with the opening under the mount.
    bx(g, tx0, y0 - 1.0, -BURY, tx1, TRENCH_BACK, TRENCH_FLOOR, CONCRETE)
    hx0, hy0, hx1, hy1 = HOLE
    bx(g, tx0, y0, SLAB, tx1, hy0, DECK, CONCRETE)
    bx(g, tx0, hy1, SLAB, tx1, TRENCH_BACK, DECK, CONCRETE)
    bx(g, tx0, hy0, SLAB, hx0, hy1, DECK, CONCRETE)
    bx(g, hx1, hy0, SLAB, tx1, hy1, DECK, CONCRETE)
    # Heavy lintel over the trench mouth with riveted blast plate.
    bx(g, tx0 - .25, y0 - .12, SLAB - .25, tx1 + .25, y0 + .02, DECK - .14, CONCRETE)
    bx(g, tx0 + .1, y0 - .16, SLAB - .2, tx1 - .1, y0 - .12, SLAB + .12, FORGED)
    bolt_row(g, (tx0 + .2, y0 - .17, SLAB - .04), (tx1 - .2, y0 - .17, SLAB - .04), 9, axis='Y', r=.02)
    # Spillway walls carry the deluge out over the front apron.
    for xa, xb in ((math.floor(tx0), tx0), (tx1, math.ceil(tx1))):   # out to the tile edges
        bx(g, xa, 0.0, -BURY, xb, y0, .75, CONCRETE)
        bx(g, xa - .03, -.03, .72, xb + .03, y0 - .03, .82, CONCRETE)
    coping_ring(g, x0, y0, x1, y1, DECK)
    skip_front = [(tx0 - .3, tx1 + .3), (DOOR_X - .5, DOOR_X + .5)]
    pilasters(g, 'X', y0, x0, x1, .1, DECK - .14, -1, skip=skip_front)
    pilasters(g, 'X', y1, x0, x1, .1, DECK - .14, 1)
    pilasters(g, 'Y', x0, y0, y1, .1, DECK - .14, -1, skip=[(2.2, 3.4)])
    pilasters(g, 'Y', x1, y0, y1, .1, DECK - .14, 1)
    # Deluge: native water filling the trench and spilling to the apron.
    g.liquid_surfaces.append(dict(name='Deluge', shape='Rectangle', center=[(tx0 + tx1) / 2, (.12 + TRENCH_BACK) / 2],
                                  bottom=TRENCH_FLOOR, top=.58, scale=[tx1 - tx0 - .02, TRENCH_BACK - .14],
                                  flowOnly=False))
    # Flame deflector: riveted steel wedge sloping out toward the mouth.
    prof = [(4.7, TRENCH_FLOOR - .05), (TRENCH_BACK - .02, TRENCH_FLOOR - .05), (TRENCH_BACK - .02, 1.45), (6.8, 1.45)]
    extrude_profile(g, prof, tx0 + .05, tx1 - .05, FORGED, axis='X')
    for k in range(4):
        x = tx0 + .4 + k * (tx1 - tx0 - .8) / 3
        g.beam((x, 4.72, TRENCH_FLOOR + .02), (x, 6.82, 1.47), .08, mat=IRON)
    # Blast plates on the deck around the mount.
    for (a, b, c, d) in ((3.2, 4.3, 6.8, 4.6), (3.2, 7.4, 6.8, 7.7)):
        bx(g, a, b, DECK - BURY, c, d, DECK + .04, FORGED)
    # Expansion joints: steel strips, proud of the deck.
    for x in (1.9, 8.1, 10.2):
        bx(g, x - .04, y0 + .3, DECK - BURY, x + .04, y1 - .3, DECK + .018, IRON)


def mount(g):
    hx0, hy0, hx1, hy1 = HOLE
    cx, cy = ROCKET
    # Four concrete pedestals straddling the opening carry a steel table.
    for x in (3.85, 6.15):
        for y in (4.85, 7.15):
            bx(g, x - .3, y - .3, DECK - BURY, x + .3, y + .3, MOUNT_TOP - .3, CONCRETE)
            bx(g, x - .34, y - .34, MOUNT_TOP - .32, x + .34, y + .34, MOUNT_TOP - .28, IRON)
    t0, t1 = MOUNT_TOP - .28, MOUNT_TOP
    bx(g, 3.5, 4.5, t0, 6.5, hy0, t1, FORGED)
    bx(g, 3.5, hy1, t0, 6.5, 7.5, t1, FORGED)
    bx(g, 3.5, hy0, t0, hx0, hy1, t1, FORGED)
    bx(g, hx1, hy0, t0, 6.5, hy1, t1, FORGED)
    # Girder edge flanges, proud of the table.
    for y in (4.48, 7.52):
        bx(g, 3.48, y - .03, t0 - .04, 6.52, y + .03, t1 + .02, IRON)
    for x in (3.48, 6.52):
        bx(g, x - .03, 4.51, t0 - .04, x + .03, 7.49, t1 + .02, IRON)
    bolt_row(g, (3.6, 4.44, t0 + .14), (6.4, 4.44, t0 + .14), 10, axis='Y', r=.02)
    # Hold-down posts with clamp arms reaching the skirt.
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        px, py = cx + math.cos(a) * 1.05, cy + math.sin(a) * 1.05
        bx(g, px - .14, py - .14, t1 - BURY, px + .14, py + .14, ROCKET_BASE + .1, IRON)
        g.beam((px, py, ROCKET_BASE + .02), (cx + math.cos(a) * .86, cy + math.sin(a) * .86, ROCKET_BASE + .18),
               .1, mat=IRON)
        bx(g, px - .17, py - .17, ROCKET_BASE + .08, px + .17, py + .17, ROCKET_BASE + .14, BRASS)
    # Tail service masts: short umbilical posts at the base.
    for sx in (-1, 1):
        x = cx + sx * 1.25
        bx(g, x - .09, 7.35, t1 - BURY, x + .09, 7.53, ROCKET_BASE + 1.4, IRON)
        g.beam((x, 7.44, ROCKET_BASE + 1.3), (cx + sx * .5, cy + .72, ROCKET_BASE + 1.3), .07, mat=IRON)


def tower(g, parts):
    x0, y0, x1, y1 = TOWER
    lattice(g, x0, y0, x1, y1, DECK - BURY, TOWER_TOP - .1, bays=11, w=.16)
    # Elevator guide rails inside, and the winch cables.
    for x in (7.95, 8.85):
        bx(g, x - .03, 6.42, DECK, x + .03, 6.48, TOWER_TOP - .1, IRON)
    for x in (8.15, 8.65):
        g.beam((x, 6.0, 3.2), (x, 6.0, TOWER_TOP + .6), .02, mat=IRON)
    hole = (7.7, 5.3, 9.1, 6.7)
    for z in LEVELS:
        grating_ring(g, 7.05, 4.65, 9.95, 7.35, z, hole, rails=('front', 'back', 'right', 'left'),
                     rail_gap=('left', 5.4, 6.6))
    grating_ring(g, 7.1, 4.7, 9.7, 7.3, int(TOWER_TOP), (8.2, 5.8, 8.6, 6.2), rails=('front', 'back', 'right', 'left'))
    # Timber winch house capping the tower.
    timber_hut(g, 7.55, 5.15, 9.25, 6.85, TOWER_TOP, TOWER_TOP + 1.05, TOWER_TOP + 1.65, ridge_axis='Y',
               infill=PLANK, windows=((8.4, 5.19, TOWER_TOP + .55, 'front', .55, 'factory'),))
    # Sheave wheel on the hut's right wall (animated).
    sheave = Geometry('LaunchPad.WinchSheave', (9.36, 6.0, TOWER_TOP + .55))
    sheave.wheel((9.36, 6.0, TOWER_TOP + .55), .34, 'X', IRON, BRASS)
    parts.append((sheave, 'SPIN_X', 2))
    bx(g, 9.25 - .02, 5.9, TOWER_TOP + .45, 9.29, 6.1, TOWER_TOP + .65, IRON)
    # Lightning rod with beacon on the hut ridge.
    bx(g, 8.36, 5.96, TOWER_TOP + 1.6, 8.44, 6.04, 17.35, IRON)
    pivot = beacon(g, 8.4, 6.0, 17.35)
    parts.append((beacon_shutter(*pivot, 'LaunchPad.TowerBeacon'), 'SPIN_Z', 3))
    # Ladder on the back face between platforms.
    ladder(g, 8.4, y1, DECK, TOWER_TOP + .7, face='back', cage=True)
    # Elevator car (animated, slides up to the crew level and back).
    car = Geometry('LaunchPad.ElevatorCar', (8.4, 6.0, DECK + .05))
    cz = DECK + .06
    bx(car, 7.85, 5.45, cz, 8.95, 6.38, cz + .08, IRON)
    bx(car, 7.85, 5.45, cz + 1.0, 8.95, 6.38, cz + 1.08, IRON)
    for x in (7.89, 8.91):
        for y in (5.49, 6.34):
            bx(car, x - .04, y - .04, cz + .08, x + .04, y + .04, cz + 1.0, IRON)
    bx(car, 7.93, 6.28, cz + .08, 8.87, 6.36, cz + 1.0, FORGED)
    bx(car, 7.9, 5.47, cz + .5, 8.9, 5.51, cz + .56, IRON)
    car.cylinder((8.4, 6.0, cz + 1.12), .06, .08, BRASS)
    parts.append((car, 'SLIDE_Z', LEVELS[-1] - DECK))


def swing_arm(name, z, length, *, pipes=True):
    """Truss umbilical arm pivoting on the tower's left face, pointing -X."""
    px, py = TOWER[0] - .08, 6.0
    arm = Geometry(name, (px, py, z))
    xe = px - length
    for dy in (-.18, .18):
        for dz in (0, .42):
            arm.box(((px + xe) / 2, py + dy, z + dz), (length, .07, .07), IRON)
    n = max(2, round(length / .4))
    for k in range(n):
        xa = px - length * k / n
        xb = px - length * (k + 1) / n
        for dy in (-.18, .18):
            arm.beam((xa, py + dy, z + .04), (xb, py + dy, z + .38), .045, mat=IRON)
        arm.box((xb, py, z + .21), (.05, .4, .05), IRON)
    # Hinge post and umbilical plate.
    arm.box((px + .02, py, z + .21), (.1, .44, .6), IRON)
    arm.box((xe - .04, py, z + .21), (.08, .5, .55), ORANGE)
    arm.box((xe - .1, py, z + .21), (.06, .4, .45), IRON)
    if pipes:
        for dy, mat in ((-.08, CONCRETE), (.08, PAINTED)):
            arm.cylinder(((px + xe) / 2 + .02, py + dy, z - .1), .05, length - .12, mat, 'X', 10)
            arm.ring((xe + .25, py + dy, z - .1), .075, .04, .05, BRASS, 'X', 10)
    return arm


def crew_arm(g, z):
    """Fixed crew access arm with a timber white-room cabin at the capsule hatch."""
    x0 = TOWER[0] - .02
    xe = ROCKET[0] + .92
    bx(g, xe + .7, 5.62, z - .08, 7.05, 6.38, z, IRON)
    for y in (5.66, 6.34):
        rail(g, (xe + .75, y), (7.0, y), z, pitch=.5)
    for k, y in enumerate((5.7, 6.3)):
        x = xe + .95 + k * .3
        g.beam((x0, y, z - 1.1), (x, y, z - .1), .07, mat=IRON)
    # White room: small plank cabin with a teal roof, butted to the capsule.
    timber_hut(g, xe - .04, 5.45, xe + .72, 6.55, z - .1, z + 1.0, z + 1.4, ridge_axis='X', infill=GREYPLANK)


def pump_house(g, parts):
    """Deluge pump house on the deck: concrete base, timber upper, teal roof."""
    x0, y0, x1, y1 = .7, 2.0, 2.9, 4.4
    bx(g, x0, y0, DECK - BURY, x1, y1, DECK + 1.0, CONCRETE)
    coping_ring(g, x0, y0, x1, y1, DECK + 1.0, w=.16, proud=.03, h=.12)
    timber_hut(g, x0 + .1, y0 + .1, x1 - .1, y1 - .1, DECK + 1.04, DECK + 2.2, DECK + 3.0, ridge_axis='Y',
               infill=PLANK, windows=((x0 + .14, 3.2, DECK + 1.65, 'left', .6, 'factory'),
                                      (1.8, y0 + .14, DECK + 1.65, 'front', .6, 'factory')))
    window(g, 1.8, y0, DECK + .5, .55, 'front', 'factory')
    # Flywheel and drive housing on the right side (animated wheel).
    bx(g, x1, 2.85, DECK - BURY, x1 + .35, 3.55, DECK + .55, PAINTED)
    bx(g, x1 + .33, 2.95, DECK + .3, x1 + .45, 3.45, DECK + .5, IRON)
    fly = Geometry('LaunchPad.PumpFlywheel', (x1 + .55, 3.2, DECK + .62))
    fly.wheel((x1 + .55, 3.2, DECK + .62), .52, 'X', IRON, BRASS)
    fly.cylinder((x1 + .55, 3.2, DECK + .62), .12, .22, PAINTED, 'X', 12)
    parts.append((fly, 'SPIN_X', 3))
    bx(g, x1 + .5, 2.95, DECK - BURY, x1 + .6, 3.05, DECK + .62, IRON)
    bx(g, x1 + .5, 3.35, DECK - BURY, x1 + .6, 3.45, DECK + .62, IRON)
    # Big inlet main rising through the deck into the pump house (the pad's
    # left face is now the footprint edge).
    pipe(g, [(.3, 2.8, DECK - .1), (.3, 2.8, DECK + .4), (x0 + .05, 2.8, DECK + .4)], r=.13, mat=IRON)
    # Valve on the main: bonnet on the riser, gauge on the house's left wall.
    bx(g, .14, 2.64, DECK + .06, .46, 2.96, DECK + .22, BRASS)
    gauge(g, x0, 2.3, DECK + .55, "left", .1)
    # Discharge lines into the trench roof.
    pipe(g, [(x1 - .2, 2.5, DECK + .35), (3.4, 2.5, DECK + .35), (3.4, 2.5, DECK - .1)], r=.08, mat=PAINTED)


def cryo_farm(g):
    """Frost-white insulated bullet tanks feeding the tower."""
    for y, r in ((1.85, .55), (3.25, .55)):
        h_tank(g, 6.9, 11.3, y, DECK + .78, r, mat=CONCRETE, band_mat=IRON, bands=6, saddles=3, ground=DECK)
    # Header pipes rising to the tower, then up a leg.
    for x, mat in ((7.65, CONCRETE), (9.15, PAINTED)):
        pipe(g, [(x, 3.25 + .5, DECK + .78), (x, 4.7, DECK + .78), (x, 4.7, LEVELS[1] - .25),
                 (x, 5.6, LEVELS[1] - .25)], r=.07, mat=mat)
    for z in (4.0, 6.5):
        for x in (7.65, 9.15):
            bx(g, x - .05, 4.78, z - .04, x + .05, 4.93, z + .04, IRON)
    gauge(g, 7.95, 4.6, DECK + .9, 'front', .1)
    valve_wheel(g, 7.65, 4.55, DECK + 1.3, face='front', r=.13)
    valve_wheel(g, 9.15, 4.55, DECK + 1.3, face='front', r=.13)
    # Vent stack with brass cap between the tanks.
    bx(g, 11.38, 2.4, DECK - BURY, 11.62, 2.7, DECK + 2.2, IRON)
    revolve(g, (11.5, 2.55, DECK + 2.2), [(.15, 0), (.15, .1), (.05, .25), (0, .27)], BRASS, segments=12)


def mast(g, parts, x, y, name):
    lattice(g, x - .25, y - .25, x + .25, y + .25, DECK - BURY, 16.8, bays=12, w=.09, feet=False)
    bx(g, x - .38, y - .38, DECK - BURY, x + .38, y + .38, DECK + .25, CONCRETE)
    bx(g, x - .04, y - .04, 16.8, x + .04, y + .04, 17.4, IRON)
    pivot = beacon(g, x, y, 17.4)
    parts.append((beacon_shutter(*pivot, name), 'SPIN_Z', 2))
    return (x, y, 17.2)


def water_tower(g):
    """Elevated deluge water tank on a steel trestle, feeding the trench."""
    cx, cy = 2.0, 9.7
    lattice(g, 1.2, 8.9, 2.8, 10.5, DECK - BURY, 7.02, bays=4, w=.15)
    bx(g, .95, 8.65, 7.0, 3.05, 10.75, 7.14, IRON)
    for y in (8.62, 10.78):
        bx(g, .92, y - .03, 6.98, 3.08, y + .03, 7.18, IRON)
    revolve(g, (cx, cy, 7.12), [(1.02, 0), (1.02, 2.3)], FORGED, segments=16, cap_bottom=False)
    for z in (7.4, 8.15, 8.9):
        band(g, (cx, cy, 0), 1.02, z, .08, IRON, segments=16, proud=.03)
    revolve(g, (cx, cy, 9.42), [(1.14, 0), (1.14, .07), (.12, .78), (0, .84)], ROOF, segments=16)
    revolve(g, (cx, cy, 10.2), [(.13, 0), (.13, .2), (0, .26)], BRASS, segments=10)
    # Down-comer through the trestle into the trench roof, with a valve.
    pipe(g, [(cx, cy - .3, 7.02), (cx, cy - .3, DECK - .1)], r=.15, mat=IRON)
    g.wheel((cx, cy - .54, 3.4), .2, 'Y', IRON, BRASS)
    bx(g, cx - .15, cy - .46, 3.25, cx + .15, cy - .36, 3.55, BRASS)
    pipe(g, [(cx, cy - .3, DECK + .3), (3.0, cy - .3, DECK + .3), (3.0, 7.9, DECK + .3), (3.0, 7.9, DECK - .1)],
         r=.11, mat=PAINTED)
    ladder(g, cx + 1.0, cy + .2, 7.14, 9.4, face='right', cage=False)
    gauge(g, cx, cy - 1.05, 8.5, 'front', .12)


def deluge_manifold(g):
    """Spray bars around the launch mount, fed from the pump house."""
    z = DECK + .22
    pipe(g, [(3.12, 7.55, z), (3.12, 4.12, z), (6.88, 4.12, z), (6.88, 7.0, z)], r=.075, mat=PAINTED)
    pipe(g, [(2.75, 4.12, DECK + .62), (3.12, 4.12, DECK + .62), (3.12, 4.12, z)], r=.075, mat=PAINTED,
         flanges=False)
    for k in range(6):
        x = 3.5 + k * .6
        g.cylinder((x, 4.24, z + .05), .03, .14, BRASS, 'Y', 8)
    for k in range(5):
        y = 4.6 + k * .6
        g.cylinder((3.24, y, z + .05), .03, .14, BRASS, 'X', 8)
        if y < 6.9:
            g.cylinder((6.76, y, z + .05), .03, .14, BRASS, 'X', 8)
    for x, y in ((3.12, 5.8), (6.88, 5.8), (4.6, 4.12), (5.6, 4.12)):
        bx(g, x - .08, y - .08, DECK - BURY, x + .08, y + .08, z - .07, IRON)


def rails(g):
    """Transporter rails from the back edge to the mount."""
    for k in range(13):
        y = 7.75 + k * .32
        bx(g, 3.8, y - .07, DECK - BURY, 6.2, y + .07, DECK + .07, WOOD)
    for x in (4.2, 5.8):
        bx(g, x - .04, 7.7, DECK + .06, x + .04, 11.75, DECK + .15, IRON)
    for x in (4.2, 5.8):
        bx(g, x - .12, 11.45, DECK + .06, x + .12, 11.7, DECK + .4, PAINTED)


def rocket_exhaust(origin):
    """Bright engine plume from just under the four bells (z 2.45) down
    through the mount opening into the flame trench (z 0.3), widening as it
    billows into the trench below the deck slab."""
    ex = Geometry(EXHAUST_NODE, origin)
    cx, cy = ROCKET
    z0 = TRENCH_FLOOR
    # Radius stays inside the 1.8 deck opening above the slab underside
    # (z 1.55) and inside the 2.8 trench below it.
    prof = [(1.05, 0), (.98, .35), (.84, .8), (.66, 1.22), (.5, 1.62), (.42, 1.82), (.5, 1.98), (.46, 2.15)]
    revolve(ex, (cx, cy, z0), prof, GLOW, segments=16)
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
    # The rocket and its exhaust are separate named nodes for the rocket
    # program: origin at the rocket base (5.0, 6.0, 3.1), Z up.
    origin = (*ROCKET, ROCKET_BASE)
    r = Geometry(ROCKET_NODE, origin)
    h = rocket(r, *ROCKET, ROCKET_BASE, primary=PAINTED, secondary=IRON)
    parts.append((r, 'CUSTOM_ROCKET', 0))
    parts.append((rocket_exhaust(origin), 'CUSTOM_ROCKET_EXHAUST', 0))
    tower(g, parts)
    parts.append((swing_arm('LaunchPad.UmbilicalArmLow', LEVELS[0] + .85, 1.6), 'CUSTOM_YAW_SWING', -1.1))
    parts.append((swing_arm('LaunchPad.UmbilicalArmHigh', LEVELS[1] + .85, 1.75), 'CUSTOM_YAW_SWING', 1.0))
    crew_arm(g, LEVELS[2])
    pump_house(g, parts)
    cryo_farm(g)
    rails(g)
    b = mast(g, parts, 11.0, 10.9, 'LaunchPad.MastBeacon')
    water_tower(g)
    deluge_manifold(g)
    # Catenary wire from the mast to the tower's lightning rod.
    g.beam((b[0] - .1, b[1], b[2]), (8.45, 6.0, 17.2), .025, mat=IRON)
    # Lamps on the pad edge and blockhouse.
    for x in (8.6, 10.4):
        lamp(g, x, 1.0, 1.45, face='front')
