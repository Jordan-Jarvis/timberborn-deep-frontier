"""Cryogenic Liquefaction Plant: makes the frost-cold propellants for launch.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the loose barrels.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size", "one layer per floor", "make
the roof flat on more of our buildings"): 12x11x16 -> 8x6x9, inside the old
footprint with the same origin. The door stays at x 3.5 but moved from the
house front at y 1 to the footprint edge (entrance cell 3, 0 -> 3, -1).
Removed: the fin-fan deck on its six concrete piers, the pipe rack on its
bents, the tanker loading bay with its gantry, tank wagon and swinging
loading arm, the product tank, the cold box's two maintenance platforms,
the sphere-top walkway and the sawtooth roof. The fin-fan coolers now sit
on the compressor house's flat roof.

Hero: a frost-white insulated cold box tower lashed to a slender banded
distillation column, over two Horton storage spheres on steel legs.
Roof types: flat steel-plate roof with a steel curb on the two-storey
compressor house (the cooler bank and its three fans cover it); a flat
steel cap on layer 7 on the cold box, all nine cells placeable; a dome on
the column. No vent cowls or roof stacks (the cold-box vent rotor is gone).

Parts: the compressor house (concrete ground storey with the door, forged
steel-framed upper storey, one layer each); the open engine bed on its west
flank with two flywheels and two vertical compressor cylinders; the cold
box with a caged ladder and a flat, placeable cap; the column in front of it, with the vapour vent
off-take and the beacon on its top;
the two spheres behind the house, fed from its back wall.

Animated (8; the loading arm went with the loading bay and the vent rotor
with the roof follow-up, no roof vents): two flywheels (spin), two
compressor piston rods (piston Z), three cooler fans (spin), beacon (spin).
"""
import math

from lategame_kit import *
from frontier_architecture import Geometry
import lategame_civic_parts as C
import compact_industry_parts as Q
from lategame_space_parts import bx, gauge, ball, pipe, sphere_tank, BURY
from lategame_roofdeck_parts import deck_slab

IDENT = 'CryogenicLiquefactionPlant'
FOOTPRINT = (8, 6)
HEIGHT = 9
FRAME_END = 121
HERO = 'Frost-white cold box tower lashed to a banded distillation column above twin Horton spheres'

HOUSE = (1.0, 0.0, 5.0, 3.0)          # whole tiles, two storeys
DOOR_X = 3.5
COLD = (5.22, 2.12, 7.88, 4.88)       # plinth (+.12) on tiles 5..8 x 2..5
COLD_TOP = 6.86                       # its steel cap's top lies on layer 7: a placeable roof
COLUMN = (6.6, 1.05)
COLUMN_R = .42
COLUMN_TOP = 7.5
SPHERES = ((1.2, 4.55), (3.35, 4.55))
SPHERE_R, SPHERE_Z = .92, 1.5


def compressor_house(g, parts):
    x0, y0, x1, y1 = HOUSE
    top = Q.storey_block(g, x0, y0, x1, y1, 2, infill=FORGED, frame=IRON, door=DOOR_X, door_id='CompressorHouseDoor',
                         roof_mat=IRON, curb_mat=IRON, roof_boards=True,
                         ground_windows={'front': [(1.5, .55, 'factory'), (2.5, .55, 'factory'),
                                                   (4.5, .55, 'factory')],
                                         'back': [(2.25, .55, 'factory')]},
                         windows={'front': [(x + .5, 1.5, .58, 'factory') for x in range(1, 5)],
                                  'back': [(x + .5, 1.5, .58, 'factory') for x in range(1, 5)],
                                  'right': [(.5, 1.5, .58, 'factory'), (1.5, 1.5, .58, 'factory')]})
    for x in (DOOR_X - .66, DOOR_X + .66):
        lamp(g, x, y0 - .01, .8, face='front')
    # Fin-fan heat exchangers on the flat roof: one forged fin bank, three fans.
    fx0, fy0, fx1, fy1 = 1.4, .55, 4.6, 2.45
    bx(g, fx0, fy0, top - .02, fx1, fy1, top + .12, IRON)
    bx(g, fx0 + .08, fy0 + .06, top + .12, fx1 - .08, fy1 - .06, top + .48, FORGED)
    for y in (fy0 + .02, fy1 - .18):
        bx(g, fx0 - .02, y, top + .12, fx1 + .02, y + .16, top + .54, PAINTED)
    cy = (fy0 + fy1) / 2
    for k in range(3):
        cx = fx0 + .55 + k * (fx1 - fx0 - 1.1) / 2
        hollow_revolve(g, (cx, cy, top + .48), [(.46, 0), (.46, .3), (.5, .36)], .05, PAINTED, segments=12,
                       inner_mat=IRON)
        bx(g, cx - .44, cy - .03, top + .52, cx + .44, cy + .03, top + .56, IRON)
        bx(g, cx - .05, cy - .05, top + .56, cx + .05, cy + .05, top + .66, IRON)
        parts.append((fan('CryogenicLiquefactionPlant.CoolerFan%d' % k, cx, cy, top + .7, .4, axis='Z', blades=6),
                      'SPIN_Z', 3))


def engine_bed(g, parts):
    """Open engine bed on the house's west flank: flywheels and compressors."""
    x0, x1 = 0.0, HOUSE[0]
    y0, y1 = HOUSE[1], HOUSE[3]
    bx(g, x0, y0, -BURY, x1, y1, .4, CONCRETE)
    bx(g, x0 + .03, y0 + .03, .36, x1 - .02, y1 - .03, .46, IRON)
    for k, y in enumerate((.62, 2.38)):
        zc = 1.0
        for x in (.18, .82):
            bx(g, x - .09, y - .16, .44, x + .09, y + .16, zc + .05, PAINTED)
            g.cylinder((x, y, zc), .09, .2, BRASS, 'X', 10)
        g.cylinder((.5, y, zc), .055, .9, IRON, 'X', 10)
        fw = Geometry('CryogenicLiquefactionPlant.Flywheel%d' % k, (.5, y, zc))
        wheel(fw, (.5, y, zc), .48, 'X')
        fw.cylinder((.5, y, zc), .14, .24, PAINTED, 'X', 12)
        fw.box((.5, y, zc - .3), (.12, .14, .12), BRASS)
        parts.append((fw, 'SPIN_X', 2 + k))
    # Vertical compressor cylinders with reciprocating piston rods.
    for k, x in enumerate((.3, .7)):
        y = 1.5
        revolve(g, (x, y, .44), [(.15, 0), (.15, .9), (.19, .94), (.19, 1.02), (.09, 1.06)], IRON, segments=14)
        band(g, (x, y, 0), .15, .65, .06, BRASS, segments=14, proud=.02)
        pr = Geometry('CryogenicLiquefactionPlant.Piston%d' % k, (x, y, 1.75))
        pr.cylinder((x, y, 1.72), .04, .8, IRON, 'Z', 8)
        pr.box((x, y, 2.14), (.22, .12, .09), PAINTED)
        parts.append((pr, 'PISTON_Z', .2 if k == 0 else -.2))
    # Rocker frame over the cylinders.
    for x in (.05, .95):
        bx(g, x - .035, 1.42, .44, x + .035, 1.58, 2.42, IRON)
    bx(g, .01, 1.4, 2.42, .99, 1.6, 2.52, IRON)
    gauge(g, .5, 1.24, .8, 'front', .09)
    pipe(g, [(.5, 1.8, .85), (.5, 1.8, 1.6), (HOUSE[0] + .02, 1.8, 1.6)], r=.055, mat=PAINTED, flanges=False)


def cold_box(g, parts):
    x0, y0, x1, y1 = COLD
    # Concrete plinth, then frost-grey insulated cladding in banded courses.
    bx(g, x0 - .12, y0 - .12, -BURY, x1 + .12, y1 + .12, 1.0, CONCRETE)
    bx(g, x0 - .16, y0 - .16, .92, x1 + .16, y1 + .16, 1.08, CONCRETE)
    bx(g, x0 + .06, y0 + .06, 1.0, x1 - .06, y1 - .06, COLD_TOP, IRON)
    courses = [1.08, 2.5, 4.0, 5.3, COLD_TOP]
    n = 5
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
    for x in (x0 + .55, x1 - .55):
        bolt_row(g, (x, y0 - .05, 1.3), (x, y0 - .05, COLD_TOP - .2), 14, axis='Y', r=.018)
    # Crown: a flat steel cap on layer 7 with a low curb, clear of props, so
    # its nine cells are placeable (the vent, rotor and beacon moved to the
    # column top).
    zt = COLD_TOP + .14
    # Laid as separate steel plates (no stretched texture over the cap).
    deck_slab(g, x0 - .14, y0 - .14, x1 + .14, y1 + .14, zt, 'steel', thickness=.14, base=IRON)
    w = .12
    bx(g, x0 - .14, y0 - .14, zt, x1 + .14, y0 - .14 + w, zt + .1, IRON)
    bx(g, x0 - .14, y1 + .14 - w, zt, x1 + .14, y1 + .14, zt + .1, IRON)
    bx(g, x0 - .14, y0 - .14 + w, zt, x0 - .14 + w, y1 + .14 - w, zt + .1, IRON)
    bx(g, x1 + .14 - w, y0 - .14 + w, zt, x1 + .14, y1 + .14 - w, zt + .1, IRON)
    # Caged ladder up the back face to the crown; gauges and a valve station.
    ladder(g, (x0 + x1) / 2 + .5, y1 + .02, 1.08, COLD_TOP + .1, face='back', cage=True)
    for z in (2.0, 4.6):
        gauge(g, x0 + .45, y0, z, 'front', .1)
    gauge(g, x0, 3.5, 1.7, 'left', .1)
    valve_wheel(g, x0 - .06, 4.2, 1.7, face='left', r=.13)


def column(g, parts):
    cx, cy = COLUMN
    r = COLUMN_R
    revolve(g, (cx, cy, -.035), [(r + .16, 0), (r + .16, .3)], CONCRETE, segments=12)
    revolve(g, (cx, cy, .265), [(r, 0), (r, COLUMN_TOP - .265)], CONCRETE, segments=12, cap_bottom=False)
    for k in range(6):
        band(g, (cx, cy, 0), r, 1.0 + k * 1.15, .08, IRON, segments=12, proud=.03)
    dome(g, (cx, cy, COLUMN_TOP), r + .02, IRON, segments=12, squash=.55)
    # Ties back to the cold box.
    for z in (2.2, 4.4, 6.2):
        g.beam((cx, cy + r - .02, z), (cx, COLD[1] + .03, z), .09, mat=IRON)
        g.ring((cx, cy, z), r + .07, .06, .1, PAINTED, 'Z', 12)
    # Insulated transfer line from the column's upper section into the cold box.
    pipe(g, [(cx + .25, cy + r - .05, 6.55), (cx + .25, COLD[1] + .05, 6.55)], r=.08, mat=CONCRETE, flanges=False)
    # Crown: the vapour off-take's open flanged mouth (steam) and the beacon.
    revolve(g, (cx, cy, COLUMN_TOP + .2), [(.08, 0), (.08, .32), (.12, .36), (.12, .42)], IRON, segments=12)
    emitter(g, 'steam', cx, cy, COLUMN_TOP + .43, .1)   # cold-box vapour
    bx(g, cx + .3, cy - .04, COLUMN_TOP - .4, cx + .38, cy + .04, COLUMN_TOP + .55, IRON)
    pivot = beacon(g, cx + .34, cy, COLUMN_TOP + .55)
    parts.append((beacon_shutter(*pivot, 'CryogenicLiquefactionPlant.Beacon'), 'SPIN_Z', 2))
    gauge(g, cx - .2, cy - r - .01, 1.5, 'front', .09)
    # Feed from the compressor house's right wall to the column foot.
    pipe(g, [(HOUSE[2], 1.05, 1.5), (cx - r + .02, 1.05, 1.5)], r=.08, mat=CONCRETE, flanges=True)


def spheres(g):
    for x, y in SPHERES:
        sphere_tank(g, x, y, SPHERE_Z, SPHERE_R, mat=CONCRETE, legs=8, ground=0)
        top = SPHERE_Z + SPHERE_R
        revolve(g, (x, y, top - .03), [(.18, 0), (.18, .14), (0, .2)], IRON, segments=12)
        g.ring((x, y, top + .09), .25, .05, .06, BRASS, 'Z', 12)
    # Fill lines from the house's back wall into each sphere's side.
    for x, _ in SPHERES:
        pipe(g, [(x, HOUSE[3], 1.0), (x, 3.84, 1.0)], r=.07, mat=CONCRETE, flanges=False)
    # Header between the sphere crowns.
    pipe(g, [(SPHERES[0][0], SPHERES[0][1], SPHERE_Z + SPHERE_R + .22),
             (SPHERES[1][0], SPHERES[1][1], SPHERE_Z + SPHERE_R + .22)], r=.06, mat=IRON, flanges=False)


def build(g, parts):
    compressor_house(g, parts)
    engine_bed(g, parts)
    cold_box(g, parts)
    column(g, parts)
    spheres(g)
