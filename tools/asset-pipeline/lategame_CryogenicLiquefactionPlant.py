"""Cryogenic Liquefaction Plant: makes the frost-cold propellants for launch.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the loose barrels.

Hero: a tall frost-white insulated cold box tower lashed to a slender banded
distillation column, rising over two Horton storage spheres on steel legs.
Roof types: north-light sawtooth roof over the compressor house; flat steel
caps on the cold box and column; open fin-fan cooler deck.

Parts: the compressor house (concrete storey with the main door, forged and
windowed steel frame above, sawtooth teal roof with native factory lights);
an open engine bed on its flank with two big flywheels and two vertical
compressor cylinders; a fin-fan heat-exchanger deck on concrete piers with
three fans over finned tube banks; a pipe rack carrying frost-white insulated
lines with flanges, valves and gauges to the cold box, column and spheres;
an insulated vertical product tank; cold box platforms and caged ladder;
vent stack and beacon.

Animated: two flywheels (spin), two compressor piston rods (piston Z),
three cooler fans (spin), cold box vent cowl rotor (spin), beacon (spin).
"""
import math

from lategame_kit import *
from frontier_architecture import Geometry
from architectural_windows import window
from native_building_assets import barrel
from lategame_space_parts import (bx, door_block, pilasters, coping_ring, gauge, ball, pipe, pipe_support,
                                  sphere_tank, h_tank, grating_ring, rail, lattice, tube, BURY, animate)

IDENT = 'CryogenicLiquefactionPlant'
FOOTPRINT = (12, 11)
HEIGHT = 16
FRAME_END = 121
HERO = 'Frost-white cold box tower lashed to a banded distillation column above twin Horton spheres'

HOUSE = (1.0, 1.0, 7.0, 5.0)          # whole tiles
HOUSE_BASE = 1.4
SAW = 3.4
COLD = (7.12, 5.12, 9.88, 7.88)       # plinth (+.12) on tiles 7..10 x 5..8
COLD_TOP = 12.5
COLUMN = (10.9, 7.0)
COLUMN_R = .5
COLUMN_TOP = 14.0
DECK = (9.0, .6, 11.8, 4.6)
DECK_Z = 3
RACK_Y = (5.55, 5.87, 6.19)
RACK_Z = 2.75


def compressor_house(g, parts):
    x0, y0, x1, y1 = HOUSE
    door_block(g, x0, y0, x1, y1, 0, HOUSE_BASE, 3.5, CONCRETE, door_id='CompressorHouseDoor')
    coping_ring(g, x0, y0, x1, y1, HOUSE_BASE, w=.2, proud=.04, h=.14)
    pilasters(g, 'X', y0, x0, x1, .05, HOUSE_BASE - .12, -1, pitch=1.3, skip=[(3.0, 4.0)])
    pilasters(g, 'X', y1, x0, x1, .05, HOUSE_BASE - .12, 1, pitch=1.3)
    pilasters(g, 'Y', x1, y0, y1, .05, HOUSE_BASE - .12, 1, pitch=1.27)
    for x in (2.2, 4.8, 5.8):
        window(g, x, y0, .75, .55, 'front', 'factory')
    # Steel-framed upper storey under the sawtooth.
    bx(g, x0 + .06, y0 + .06, HOUSE_BASE, x1 - .06, y1 - .06, SAW - .03, IRON)
    top = SAW - .03
    frame_wall(g, 'X', y0, x0, x1, HOUSE_BASE + .04, top, outward=-1, infill=FORGED, bays=4,
               windows=[(x0 + (x1 - x0) * (k + .5) / 4, 2.4) for k in range(4)], window_scale=.9)
    frame_wall(g, 'X', y1, x0, x1, HOUSE_BASE + .04, top, outward=1, infill=FORGED, bays=4,
               windows=[(x0 + (x1 - x0) * (k + .5) / 4, 2.4) for k in range(4)], window_scale=.9)
    frame_wall(g, 'Y', x1, y0 + .1, y1 - .1, HOUSE_BASE + .04, top, outward=1, infill=FORGED, bays=3,
               windows=[(y0 + .1 + (y1 - y0 - .2) * (k + .5) / 3, 2.4) for k in range(3)], window_scale=.9)
    frame_wall(g, 'Y', x0, y0 + .1, y1 - .1, HOUSE_BASE + .04, top, outward=-1, infill=ORANGE, bays=3)
    # North-light sawtooth roof with closed tooth ends.
    teeth = 3
    rise = .9
    sawtooth_roof(g, x0 - .02, y0, x1 + .02, y1, SAW, teeth=teeth, rise=rise, axis='X', glazing=True)
    depth = (y1 - y0) / teeth
    for i in range(teeth):
        ya, yb = y0 + i * depth, y0 + (i + 1) * depth
        for x, nx in ((x0 - .06, -1), (x1 + .06, 1)):
            oriented_polygon(g, [(x, ya + .02, SAW + .01), (x, yb - .06, SAW + .01), (x, yb - .06, SAW + rise - .05)],
                             (nx, 0, 0), ORANGE)
    # Roof vents on the ridges.
    for k, x in enumerate((2.4, 5.2)):
        revolve(g, (x, y0 + depth * 1 - .35, SAW + rise * .72), [(.14, 0), (.14, .45), (.22, .5), (.22, .56), (0, .62)],
                IRON, segments=12)


def engine_bed(g, parts):
    """Open engine bed on the house's west flank: flywheels and compressors."""
    x0, x1 = 0.0, HOUSE[0]   # bed on whole tiles beside the house
    y0, y1 = HOUSE[1], HOUSE[3]
    bx(g, x0, y0, -BURY, x1, y1, .4, CONCRETE)
    bx(g, x0 + .03, y0 + .03, .36, x1, y1 - .03, .46, IRON)
    for k, y in enumerate((1.75, 4.05)):
        zc = 1.15
        for x in (.18, .82):
            bx(g, x - .09, y - .18, .44, x + .09, y + .18, zc + .05, PAINTED)
            g.cylinder((x, y, zc), .1, .2, BRASS, 'X', 10)
        g.cylinder((.5, y, zc), .06, .9, IRON, 'X', 10)
        fw = Geometry('CryogenicLiquefactionPlant.Flywheel%d' % k, (.5, y, zc))
        wheel(fw, (.5, y, zc), .66, 'X')
        fw.cylinder((.5, y, zc), .16, .26, PAINTED, 'X', 12)
        fw.box((.5, y, zc - .38), (.14, .16, .14), BRASS)
        parts.append((fw, 'SPIN_X', 2 + k))
    # Vertical compressor cylinders with reciprocating piston rods.
    for k, x in enumerate((.3, .7)):
        y = 2.9
        revolve(g, (x, y, .44), [(.17, 0), (.17, 1.0), (.21, 1.04), (.21, 1.12), (.1, 1.16)], IRON, segments=14)
        band(g, (x, y, 0), .17, .7, .06, BRASS, segments=14, proud=.02)
        pr = Geometry('CryogenicLiquefactionPlant.Piston%d' % k, (x, y, 1.9))
        pr.cylinder((x, y, 1.85), .045, .9, IRON, 'Z', 8)
        pr.box((x, y, 2.32), (.24, .14, .1), PAINTED)
        parts.append((pr, 'PISTON_Z', .22 if k == 0 else -.22))
    # Rocker frame over the cylinders.
    for x in (.05, .95):
        bx(g, x - .035, 2.82, .44, x + .035, 2.98, 2.62, IRON)
    bx(g, .01, 2.8, 2.62, .99, 3.0, 2.72, IRON)
    gauge(g, .5, 2.75, .8, 'front', .1)
    pipe(g, [(.5, 3.1, .9), (.5, 3.1, 1.8), (HOUSE[0] + .02, 3.1, 1.8)], r=.06, mat=PAINTED, flanges=False)


def cooler_deck(g, parts):
    """Fin-fan heat exchangers on a grating deck carried by concrete piers."""
    x0, y0, x1, y1 = DECK
    for x in (x0 + .25, x1 - .25):
        for y in (y0 + .25, (y0 + y1) / 2, y1 - .25):
            concrete_pier(g, x, y, 0, DECK_Z - .3, .32)
            bx(g, x - .08, y - .08, DECK_Z - .3 + .05, x + .08, y + .08, DECK_Z - .08, IRON)
    grating_ring(g, x0, y0, x1, y1, DECK_Z, (x0 + .5, y0 + .3, x1 - .5, y1 - .3),
                 rails=('front', 'right', 'back'))
    # Finned tube bundles slung under the deck.
    for k in range(6):
        z = DECK_Z - .55 + (k % 2) * .16
        y = y0 + .5 + k * (y1 - y0 - 1.0) / 5
        g.cylinder(((x0 + x1) / 2, y, z), .07, x1 - x0 - 1.1, IRON, 'X', 10)
        for j in range(5):
            xx = x0 + .8 + j * (x1 - x0 - 1.6) / 4
            g.ring((xx, y, z), .12, .05, .05, PAINTED, 'X', 10)
    for x in (x0 + .5, x1 - .5):
        g.cylinder((x, (y0 + y1) / 2, DECK_Z - .47), .2, y1 - y0 - .6, CONCRETE, 'Y', 14)
    # Three fan housings with animated rotors.
    for k in range(3):
        cy = y0 + .7 + k * (y1 - y0 - 1.4) / 2
        cx = (x0 + x1) / 2
        hollow_revolve(g, (cx, cy, DECK_Z + .02), [(.6, 0), (.6, .45), (.66, .52)], .05, PAINTED, segments=12,
                       inner_mat=IRON)
        for a in range(4):
            ang = math.pi / 4 + a * math.pi / 2
            px, py = cx + math.cos(ang) * .62, cy + math.sin(ang) * .62
            bx(g, px - .05, py - .05, DECK_Z - .01, px + .05, py + .05, DECK_Z + .5, IRON)
        bx(g, cx - .58, cy - .03, DECK_Z + .1, cx + .58, cy + .03, DECK_Z + .14, IRON)
        bx(g, cx - .06, cy - .06, DECK_Z + .14, cx + .06, cy + .06, DECK_Z + .3, IRON)
        parts.append((fan('CryogenicLiquefactionPlant.CoolerFan%d' % k, cx, cy, DECK_Z + .36, .52, axis='Z', blades=6),
                      'SPIN_Z', 3))
    ladder(g, x0 + .3, y0, 0, DECK_Z + .7, face='front', cage=False)


def cold_box(g, parts):
    x0, y0, x1, y1 = COLD
    # Concrete plinth, then frost-grey insulated cladding in banded courses.
    bx(g, x0 - .12, y0 - .12, -BURY, x1 + .12, y1 + .12, 1.0, CONCRETE)
    bx(g, x0 - .16, y0 - .16, .92, x1 + .16, y1 + .16, 1.08, CONCRETE)
    bx(g, x0 + .06, y0 + .06, 1.0, x1 - .06, y1 - .06, COLD_TOP, IRON)
    courses = [1.08, 2.5, 4.0, 5.5, 7.0, 8.5, 10.0, 11.5, COLD_TOP]
    n = 6
    for za, zb in zip(courses, courses[1:]):
        for k in range(n):
            xa, xb = x0 + .06 + (x1 - x0 - .12) * k / n, x0 + .06 + (x1 - x0 - .12) * (k + 1) / n
            ya, yb = y0 + .06 + (y1 - y0 - .12) * k / n, y0 + .06 + (y1 - y0 - .12) * (k + 1) / n
            bx(g, xa, y0, za, xb, y0 + .07, zb, CONCRETE)
            bx(g, xa, y1 - .07, za, xb, y1, zb, CONCRETE)
            bx(g, x0, ya, za, x0 + .07, yb, zb, CONCRETE)
            bx(g, x1 - .07, ya, za, x1, yb, zb, CONCRETE)
    for x in (x0, x1):
        for y in (y0, y1):
            bx(g, x - .09, y - .09, 1.06, x + .09, y + .09, COLD_TOP + .06, IRON)
    for z in courses[1:-1]:
        bx(g, x0 - .05, y0 - .05, z - .05, x1 + .05, y1 + .05, z + .05, IRON)
    for x in (x0 + .55, (x0 + x1) / 2, x1 - .55):
        bolt_row(g, (x, y0 - .05, 1.3), (x, y0 - .05, COLD_TOP - .2), 22, axis='Y', r=.018)
    # Crown: steel cap, vent stack with an animated cowl rotor, beacon.
    bx(g, x0 - .14, y0 - .14, COLD_TOP, x1 + .14, y1 + .14, COLD_TOP + .14, IRON)
    stack(g, x0 + .55, y0 + .6, COLD_TOP + .12, 1.6, emits='steam', r=.18)   # cold-box vapour
    vx, vy = x1 - .55, y1 - .55
    revolve(g, (vx, vy, COLD_TOP + .12), [(.26, 0), (.26, .5), (.3, .55), (.3, .62)], PAINTED, segments=14)
    parts.append((fan('CryogenicLiquefactionPlant.VentRotor', vx, vy, COLD_TOP + .7, .24, axis='Z', blades=4),
                  'SPIN_Z', 4))
    bx(g, vx - .27, vy - .02, COLD_TOP + .74, vx + .27, vy + .02, COLD_TOP + .78, IRON)
    bx(g, x0 + .9, y1 - .5, COLD_TOP + .12, x0 + .98, y1 - .42, 14.5, IRON)
    pivot = beacon(g, x0 + .94, y1 - .46, 14.5)
    parts.append((beacon_shutter(*pivot, 'CryogenicLiquefactionPlant.Beacon'), 'SPIN_Z', 2))
    # Maintenance platforms on the front face, caged ladder, gauges.
    for z in (6, 11):
        bx(g, x0 - .1, y0 - .85, z - .08, x1 + .1, y0, z, IRON)
        rail(g, (x0 - .06, y0 - .81), (x1 + .06, y0 - .81), z, pitch=.55)
        for x in (x0 + .2, x1 - .2):
            g.beam((x, y0 - .02, z - .8), (x, y0 - .78, z - .1), .07, mat=IRON)
    ladder(g, x1 + .02, (y0 + y1) / 2, 1.08, 11.7, face='right', cage=True)
    for z in (6.5, 11.5):
        gauge(g, x0 + .6, y0, z, 'front', .12)
        gauge(g, x1 - .6, y0, z, 'front', .12)
        valve_wheel(g, (x0 + x1) / 2, y0 - .06, z, face='front', r=.15)


def column(g):
    cx, cy = COLUMN
    r = COLUMN_R
    revolve(g, (cx, cy, -.035), [(r + .18, 0), (r + .18, .31)], CONCRETE, segments=12)
    revolve(g, (cx, cy, .28), [(r, 0), (r, COLUMN_TOP - .28)], CONCRETE, segments=12, cap_bottom=False)
    for k in range(9):
        band(g, (cx, cy, 0), r, 1.2 + k * 1.4, .08, IRON, segments=12, proud=.03)
    dome(g, (cx, cy, COLUMN_TOP), r + .02, IRON, segments=12, squash=.55)
    pipe(g, [(cx, cy, COLUMN_TOP + .2), (cx, cy, COLUMN_TOP + .95), (cx - .35, cy, COLUMN_TOP + .95)],
         r=.07, mat=IRON, flanges=False)
    # Ties back to the cold box.
    for z in (3.5, 7.5, 11.0):
        g.beam((COLD[2] + .05, cy, z), (cx - r + .02, cy, z), .09, mat=IRON)
        g.ring((cx, cy, z), r + .07, .06, .1, PAINTED, 'Z', 12)
    # Insulated transfer line from the column top down into the cold box.
    pipe(g, [(cx - .2, cy - .55, 12.6), (cx - .2, cy - .55, 9.2), (COLD[2] - .1, cy - .55, 9.2)], r=.09, mat=CONCRETE)


def spheres(g):
    for x in (2.35, 5.55):
        sphere_tank(g, x, 8.55, 2.35, 1.42, mat=CONCRETE, legs=8, ground=0)
        revolve(g, (x, 8.55, 3.72), [(.22, 0), (.22, .14), (0, .2)], IRON, segments=12)
        g.ring((x, 8.55, 3.8), .3, .05, .06, BRASS, 'Z', 12)
    # Riser and top walkway between the spheres.
    bx(g, 2.35, 8.45, 3.76, 5.55, 8.65, 3.84, IRON)
    rail(g, (3.0, 8.42), (4.9, 8.42), 3.84, pitch=.5, height=.45)
    ladder(g, 3.95, 8.55, 0, 3.8, face='front', cage=True)


def product_tank(g):
    top = tank(g, 10.45, 9.6, 0, .9, 5.2, mat=CONCRETE, bands=5, roof='dome')
    revolve(g, (10.45, 9.6, top + .38), [(.16, 0), (.16, .2), (0, .26)], BRASS, segments=10)
    ladder(g, 10.45 - .9, 9.6, .25, top, face='left', cage=True)


def pipe_rack(g):
    xs = (1.9, 4.3, 6.7)
    for x in xs:
        for y in (RACK_Y[0] - .22, RACK_Y[-1] + .22):
            concrete_pier(g, x, y, 0, .3, .26)
            bx(g, x - .07, y - .07, .34, x + .07, y + .07, RACK_Z - .2, IRON)
        bx(g, x - .08, RACK_Y[0] - .3, RACK_Z - .2, x + .08, RACK_Y[-1] + .3, RACK_Z - .08, IRON)
    mats = ((CONCRETE, .1), (PAINTED, .08), (CONCRETE, .08))
    for (mat, r), y in zip(mats, RACK_Y):
        z = RACK_Z - .08 + r
        pipe(g, [(HOUSE[0] + .1, y, z), (COLD[0] + .02, y, z)], r=r, mat=mat, flanges=True)
    # Drops: rack to the house's back wall, rack up into the cold box.
    pipe(g, [(2.5, RACK_Y[0], RACK_Z + .02), (2.5, HOUSE[3] + .0, RACK_Z + .02)], r=.1, mat=CONCRETE, flanges=False)
    pipe(g, [(5.2, RACK_Y[1], RACK_Z), (5.2, RACK_Y[1], 1.6), (5.2, HOUSE[3], 1.6)], r=.08, mat=PAINTED,
         flanges=False)
    # Feed lines to the spheres.
    for x in (2.35, 5.55):
        pipe(g, [(x + .6, RACK_Y[2], RACK_Z), (x + .6, 7.5, RACK_Z), (x + .6, 7.5, 1.55), (x + .6, 7.6, 1.55)],
             r=.08, mat=CONCRETE, flanges=False)
        bx(g, x + .5, 7.0, RACK_Z - .1, x + .7, 7.2, RACK_Z + .12, BRASS)
    # Line from the cooler deck to the cold box.
    pipe(g, [(DECK[0] + .4, DECK[3] - .05, DECK_Z - .47), (DECK[0] + .4, COLD[1] + .02, DECK_Z - .47)],
         r=.12, mat=CONCRETE, flanges=True)
    gauge(g, 6.0, RACK_Y[0] - .14, RACK_Z + .2, 'front', .1)
    bx(g, 5.96, RACK_Y[0] - .1, RACK_Z - .08, 6.04, RACK_Y[0] - .02, RACK_Z + .1, IRON)


def loading_bay(g, parts):
    """Tanker loading bay: apron, frost-white tank wagon, gantry and swing arm."""
    bx(g, 7.0, 0.0, -BURY, 9.0, 3.0, .08, CONCRETE)
    cx = 8.05
    bx(g, cx - .6, .5, .3, cx + .6, 2.7, .45, IRON)
    for x in (cx - .55, cx + .55):
        for y in (.9, 2.3):
            xw = x + (.08 if x > cx else -.08)
            g.cylinder((xw, y, .26), .18, .1, IRON, 'X', 12)
            g.cylinder((xw + (.06 if x > cx else -.06), y, .26), .07, .04, BRASS, 'X', 8)
    bx(g, cx - .08, .3, .33, cx + .08, .5, .42, IRON)
    h_tank(g, .62, 2.6, cx, 1.06, .52, mat=CONCRETE, band_mat=IRON, bands=4, saddles=2, ground=.45, axis='Y')
    revolve(g, (cx, 1.3, 1.5), [(.16, 0), (.16, .14), (.2, .16), (.2, .2)], IRON, segments=12)
    portal_frame(g, 7.25, 8.85, 1.6, .08, 3.0, w=.16)
    # Feed from the pipe rack along the gantry.
    pipe(g, [(7.25, RACK_Y[0], RACK_Z + .02), (7.25, 1.85, RACK_Z + .02), (7.25, 1.85, 3.45)], r=.08, mat=CONCRETE,
         flanges=False)
    valve_wheel(g, 7.25, 1.7, 3.0, face='front', r=.13)
    # Swinging loading arm with a drop pipe to the tank hatch (animated).
    px, py, pz = 7.25, 1.6, 3.55
    arm = Geometry('CryogenicLiquefactionPlant.LoadingArm', (px, py, pz))
    arm.cylinder((px, py, pz), .12, .2, BRASS, 'Z', 12)
    dy = 1.3
    arm.cylinder(((px + cx) / 2, py, pz), .08, cx - px, CONCRETE, 'X', 10)
    arm.ring((cx - .3, py, pz), .12, .05, .05, BRASS, 'X', 10)
    ball(arm, (cx, py, pz), .1, IRON, segments=10, rings=6)
    arm.cylinder((cx, (py + dy) / 2, pz), .07, py - dy, CONCRETE, 'Y', 10)
    ball(arm, (cx, dy, pz), .1, IRON, segments=10, rings=6)
    arm.cylinder((cx, dy, (pz + 1.82) / 2), .07, pz - 1.82, CONCRETE, 'Z', 10)
    arm.ring((cx, dy, 2.0), .11, .05, .06, BRASS, 'Z', 10)
    arm.beam((px + .1, py, pz + .1), (cx - .2, py, pz + .45), .04, mat=IRON)
    arm.beam((cx - .2, py, pz + .45), (cx, py, pz + .1), .04, mat=IRON)
    parts.append((arm, 'CUSTOM_YAW_SWING', .9))
    lamp(g, 8.85, 1.6, 2.4, face='right')


def build(g, parts):
    loading_bay(g, parts)
    compressor_house(g, parts)
    engine_bed(g, parts)
    cooler_deck(g, parts)
    cold_box(g, parts)
    column(g)
    spheres(g)
    product_tank(g)
    pipe_rack(g)
    for x in (4.6, 5.6):
        lamp(g, x, HOUSE[1], 1.15, face='front')
