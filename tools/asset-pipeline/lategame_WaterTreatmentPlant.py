"""WaterTreatmentPlant: badwater treatment (4 workers, 500 hp).

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size", "one layer per floor", "make
the roof flat on more of our buildings", "no clutter on buildable space"):
12x11x13 -> 9x5x7, inside the old footprint with the same origin. The door
moved from the filter house front inside the old yard (entrance cell 8, 3)
to the front edge on the same tile column (entrance cell 8, -1), where a
placed plant's access path entered the old footprint; the map sites' door
approach stays where it was. The treated-water Timber Pipes outlet moved
from the right-hand face (cell 11, 1, 0, Right) to the front of the water
tower (cell 4, 0, 0, Down; OUTLET, tools/coolant_pipe_ports.json).
Removed: the water tower's braced lattice trestle (the tank now stands on a
solid round concrete shaft), the filter house's barrel vault, the pump
shed's gable and both digesters; the clarifiers are smaller, and the
chlorine contact tower now stands on a one-storey chemical house.

HERO: an elevated riveted water tower with a railed balcony and a lapped teal
      cone roof, on a solid concrete shaft, over two round clarifiers whose
      scraper bridges sweep slowly round the water.
ROOF: the water tower's cone stays (its defining silhouette); a pitched
      gable of native teal roof planks on the filter house; a flat
      corrugated-metal roof with a steel curb on the pump shed and a flat
      concrete roof on the chemical house (both placeable). No roof vents.

Plan (9 x 5 tiles): the primary and secondary clarifiers with native water on
the left; the water tower front-centre with the outlet socket on its front;
the two-storey filter house front-right with the door; the stepped aeration
cascade and the one-storey chemical house (chlorine contact tower on its
roof) behind the tower; the pump shed behind the filter house, open to the
right edge, with two flywheel pumps.

Animated (6, names unchanged; the pump flywheels now turn about Y): two
scraper bridges, aerator rotor, two pump flywheels, beacon.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
import compact_industry_parts as Q

IDENT = 'WaterTreatmentPlant'
FOOTPRINT = (9, 5)
HEIGHT = 7
FRAME_END = 121
HERO = ('An elevated riveted water tower with a railed balcony and a teal cone roof on a solid shaft, '
        'over two round clarifiers whose scraper bridges sweep round the water.')

# Primary clarifier tangent to tiles 0..3 x 0..3, secondary to tiles 0..2 x 3..5: (cx, cy, rim, water radius).
CLARIFIERS = ((1.5, 1.5, 1.5, 1.0), (1.0, 4.08, .92, .6))
RIM_TOP = .8
FILTER = (5.0, 0.0, 9.0, 3.0)           # two storeys on whole tiles; door face on y = 0
DOOR_X = 8.5                            # entrance (8, -1): the old access path's tile column
ROOF_Z = 2.0
SHED = (5.0, 3.0, 9.0, 5.0)              # open to the right edge, behind the filter house
CHEM = (3.0, 3.0, 5.0, 5.0)              # one-storey chemical house, chlorine tower on its roof
TOWER = (4.0, 1.0)
OUTLET = {'cell': [4, 0, 0], 'direction': 'Down', 'state': 'OpenOut'}   # tools/coolant_pipe_ports.json
SHAFT_R, TANK_R = .45, .8
SHAFT_TOP = 4.0


# ---------------------------------------------------------------- clarifiers

def clarifier(g, parts, idx, cx, cy, RIM_OUT, RIM_IN):
    # Concrete basin: broad walkway rim (hides the square water's corners).
    K.hollow_revolve(g, (cx, cy, 0), [(RIM_OUT, 0), (RIM_OUT, RIM_TOP)], RIM_OUT - RIM_IN, CONCRETE, segments=20)
    P.hoop(g, (cx, cy, RIM_TOP - .08), RIM_OUT + .03, .05, .1, CONCRETE, segments=20)
    K.revolve(g, (cx, cy, 0), [(RIM_IN - .02, 0), (RIM_IN - .02, .2)], CONCRETE, segments=20)
    # Effluent launder round the inside of the wall, feed well and centre pier.
    K.hollow_revolve(g, (cx, cy, 0), [(RIM_IN, .56), (RIM_IN, .72)], .12, CONCRETE, segments=20)
    K.hollow_revolve(g, (cx, cy, 0), [(RIM_IN * .42, .42), (RIM_IN * .42, .86)], .04, IRON, segments=12)
    K.revolve(g, (cx, cy, .2), [(.2, 0), (.2, .7), (.25, .75), (.25, .86)], CONCRETE, segments=16)
    K.revolve(g, (cx, cy, 1.06), [(.18, 0), (.18, .18), (.08, .24)], PAINTED, segments=16)
    g.liquid_surfaces.append(dict(name=f'Clarifier{idx}', shape='Rectangle', center=[cx, cy], bottom=.2, top=.64,
                                  scale=[2 * RIM_IN, 2 * RIM_IN], flowOnly=False))
    P.ring_rail(g, (cx, cy), RIM_OUT - .08, RIM_TOP, height=.5, posts=16 if RIM_OUT > 1.2 else 12)
    # Rotating full-diameter scraper bridge on the centre turntable.
    z = 1.4
    b = Geometry(f'WaterTreatmentPlant.ScraperBridge{idx}', (cx, cy, z))
    r1 = RIM_OUT - .22
    for dy in (-.15, .15):
        b.box((cx, cy + dy, z), (2 * r1, .07, .13), IRON)
    n = 7 if r1 > 1 else 5
    for k in range(n):
        x = cx - r1 + .12 + k * (2 * r1 - .24) / (n - 1)
        b.box((x, cy, z - .04), (.05, .28, .05), IRON)
    b.box((cx, cy, z + .085), (2 * r1 - .04, .24, .04), FORGED)
    for dy in (-.15, .15):
        P.rail(b, [(cx - r1 + .05, cy + dy), (cx + r1 - .05, cy + dy)], z + .1, height=.42, pitch=.45)
    P.lathe(b, (cx, cy, 0), [(.22, 1.3), (.22, 1.35), (.14, 1.37)], PAINTED, segments=16)
    for side in (-1, 1):
        ex = cx + side * (RIM_OUT - .27)
        b.box((ex, cy, z - .11), (.24, .4, .1), PAINTED)
        for dy in (-.13, .13):
            b.box((ex, cy + dy, (RIM_TOP + .12 + z - .16) / 2), (.07, .07, z - .16 - RIM_TOP - .12), IRON)
        b.box((ex, cy, RIM_TOP + .1), (.18, .36, .05), IRON)
        b.cylinder((ex, cy, RIM_TOP + .06), .06, .07, IRON, 'Y', 12)
        b.box((ex - side * .02, cy + .26, z - .08), (.18, .12, .15), IRON)
        # Scraper arm and blade sweeping the basin floor.
        f = RIM_IN / 1.0
        b.beam((cx + side * .5 * f, cy, z - .07), (cx + side * .75 * f, cy, .36), .05, mat=IRON)
        b.beam((cx + side * .95 * f, cy, z - .07), (cx + side * .75 * f, cy, .36), .05, mat=IRON)
        b.box((cx + side * .62 * f, cy + side * .03, .31), (.6 * f, .045, .1), PAINTED)
    parts.append((b, 'SPIN_Z', 1 if idx == 1 else -1))


# ---------------------------------------------------------------- aeration cascade

def cascade(g):
    x0, x1 = 2.0, 3.0   # one tile wide, y 3..5, stepping down into the filter house's back wall
    steps = [(4.9, 4.25, 1.1), (4.25, 3.65, .8), (3.65, 3.08, .5)]
    for k, (yb, ya, floor) in enumerate(steps):
        g.box(((x0 + x1) / 2, (ya + yb) / 2, floor / 2), (x1 - x0 - .26, yb - ya, floor), CONCRETE)
        for x in (x0 + .065, x1 - .065):
            g.box((x, (ya + yb) / 2, (floor + .36) / 2), (.13, yb - ya, floor + .36), CONCRETE)
        g.box(((x0 + x1) / 2, ya + .05, floor + .12), (x1 - x0 - .26, .1, .24), CONCRETE)
        g.box(((x0 + x1) / 2, ya + .05, floor + .25), (x1 - x0 - .26 - .02, .12, .02), BRASS)
        g.liquid_surfaces.append(dict(name=f'Cascade{k + 1}', shape='Rectangle',
                                      center=[(x0 + x1) / 2, (ya + .1 + yb) / 2], bottom=floor,
                                      top=floor + .2, scale=[x1 - x0 - .26, yb - ya - .1], flowOnly=False))
    # Back head wall.
    g.box(((x0 + x1) / 2, steps[0][0] + .05, 1.6 / 2), (x1 - x0, .1, 1.6), CONCRETE)
    # Feed pipe from the secondary clarifier over the head wall.
    cx, cy, ro, _ = CLARIFIERS[1]
    P.pipe(g, [(cx + ro - .1, 4.55, RIM_TOP + .2), (x0 + .3, 4.55, RIM_TOP + .2), (x0 + .3, 4.55, 1.5)], .06)


def aerator(parts):
    x0, x1 = 2.0, 3.0
    cy, cz = 4.6, 1.1 + .2
    a = Geometry('WaterTreatmentPlant.AeratorRotor', ((x0 + x1) / 2, cy, cz))
    P.tube(a, (x0 + .16, cy, cz), (x1 - .16, cy, cz), .04, IRON, segments=10)
    for k in range(6):
        ang = k * math.pi / 3
        for x in (x0 + .3, x1 - .3):
            a.box((x, cy + math.cos(ang) * .16, cz + math.sin(ang) * .16),
                  (.2, .03 + .15 * abs(math.sin(ang)), .03 + .15 * abs(math.cos(ang))), PAINTED)
    parts.append((a, 'SPIN_X', 3))


# ---------------------------------------------------------------- filter house

def filter_house(g):
    x0, y0, x1, y1 = FILTER
    top = Q.storey_block(g, x0, y0, x1, y1, 2, infill=ORANGE, frame=WOOD, door=DOOR_X, door_id='Entrance', roof=False,
                         ground_windows={'front': [(5.5, .55, 'grand'), (6.5, .55, 'grand'), (7.5, .55, 'grand')],
                                         'right': [(1.5, .55, 'grand')]},
                         windows={'front': [(x + .5, 1.5, .55, 'grand') for x in range(5, 9)],
                                  'left': [(2.5, 1.5, .55, 'grand')],
                                  'right': [(.5, 1.5, .55, 'grand'), (1.5, 1.5, .55, 'grand'), (2.5, 1.5, .55, 'grand')]})
    K.lamp(g, DOOR_X - .66, y0 - .01, .8, face='front')
    # Pitched gable of native teal roof planks, ridge along X (roof variety).
    P.plank_roof(g, x0 + .05, y0 + .05, x1 - .05, y1 - .05, top, top + .8, ridge_axis='X', overhang=.08, plank=.3,
                 gable_mat=ORANGE)
    # Cascade outfall into the back wall and the dosing gauge.
    P.gauge(g, x0 + .3, y1, 1.5, 'back', .08)


# ---------------------------------------------------------------- chlorine tower

def chemical_house(g):
    """One-storey dosing house behind the filter house; the chlorine contact
    tower stands on its roof's back-right corner, the rest of the roof is open."""
    x0, y0, x1, y1 = CHEM
    # On its right (x = 5) the coping and foot stop short of the filter
    # house's, which stand proud of that corner.
    top = 1.0
    blk(g, x0, y0, 0, x1, y1, top - .03, CONCRETE)
    blk(g, x0 - .03, y0 - .03, -.03, x1 - .03, y1 + .03, .14, CONCRETE)
    blk(g, x0 - .05, y0 - .05, top - .1, x1 - .05, y1 + .05, top, CONCRETE)
    w = Q.CURB_W
    blk(g, x0 - .05, y1 + .05 - w, top, x1 - .05, y1 + .05, top + Q.CURB, CONCRETE)
    blk(g, x0 - .05, y0 - .05, top, x0 - .05 + w, y1 + .05 - w, top + Q.CURB, CONCRETE)
    blk(g, x0 - .05 + w, y0 - .05, top, x1 - .05, y0 - .05 + w, top + Q.CURB, CONCRETE)
    blk(g, 3.95, y1, .14, 4.05, y1 + .025, top - .1, CONCRETE)
    C.native_window(g, 4.5, y1, .52, .55, 'back', 'factory')
    cx, cy = 4.55, 4.55
    K.revolve(g, (cx, cy, top - .02), [(.36, 0), (.36, .2)], CONCRETE, segments=16)
    K.revolve(g, (cx, cy, top + .18), [(.26, 0), (.26, 2.0)], IRON, segments=12)
    for z in (top + .8, top + 1.6):
        K.band(g, (cx, cy, 0), .26, z, .06, PAINTED, segments=12)
    K.revolve(g, (cx, cy, top + 2.18), [(.3, 0), (.3, .05), (.07, .28), (0, .3)], ROOF, segments=12)
    g.cylinder((cx, cy, top + 2.55), .04, .12, IRON, 'Z', 8)
    P.gauge(g, cx - .18, cy - .25, top + 1.0, 'front', .055)
    # Chlorine gas cylinders against the house's back wall.
    for k, x in enumerate((3.3, 3.55, 3.8)):
        g.cylinder((x, y1 + .1, .45), .09, .8, PAINTED, 'Z', 12)
        g.cylinder((x, y1 + .1, .9), .045, .1, BRASS, 'Z', 8)
    blk(g, 3.12, y1 + .01, .55, 3.98, y1 + .03, .6, IRON)
    # Dosing line from the tower down into the house's roof.
    P.pipe(g, [(cx - .26, cy, top + 1.3), (cx - .45, cy, top + 1.3), (cx - .45, cy, top - .04)], .04, flanges=False)


# ---------------------------------------------------------------- water tower

def water_tower(g, parts):
    cx, cy = TOWER
    # Solid round concrete shaft on a footing, with a door-height base course.
    K.revolve(g, (cx, cy, 0), [(SHAFT_R + .15, 0), (SHAFT_R + .15, .3), (SHAFT_R, .38)], CONCRETE, segments=16)
    K.revolve(g, (cx, cy, .38), [(SHAFT_R, 0), (SHAFT_R, SHAFT_TOP - .38)], CONCRETE, segments=16, cap_top=False)
    for z in (1.0, 2.0, 3.0):
        K.band(g, (cx, cy, 0), SHAFT_R, z, .06, IRON, segments=16)
    # Corbel ring and balcony at the whole layer 4.
    K.revolve(g, (cx, cy, SHAFT_TOP - .4), [(SHAFT_R, 0), (TANK_R - .05, .32), (TANK_R - .05, .4)], CONCRETE,
              segments=16, cap_bottom=False)
    R = TANK_R
    P.annulus(g, (cx, cy), R - .1, R + .2, SHAFT_TOP - .08, SHAFT_TOP, IRON, segments=16)
    P.ring_rail(g, (cx, cy), R + .17, SHAFT_TOP, height=.5, posts=14, gap=(math.pi * 1.1, math.pi * 1.3))
    # Riveted shell, banded, with a lapped cone roof of teal boards.
    K.revolve(g, (cx, cy, SHAFT_TOP), [(R, 0), (R, 1.5)], IRON, segments=16, cap_bottom=False, cap_top=False)
    for z in (SHAFT_TOP + .45, SHAFT_TOP + 1.05):
        K.band(g, (cx, cy, 0), R, z, .07, PAINTED, segments=16)
    rz = SHAFT_TOP + 1.5
    K.revolve(g, (cx, cy, rz - .05), [(R + .08, 0), (R + .08, .08)], WOOD, segments=16)
    P.lathe(g, (cx, cy, 0), [(R + .16, rz), (R * .55, rz + .45)], ROOF, segments=16)
    P.lathe(g, (cx, cy, 0), [(R * .55 + .06, rz + .45), (0, rz + .95)], ROOF, segments=16)
    pivot = K.beacon(g, cx, cy, rz + .92)
    parts.append((K.beacon_shutter(*pivot, 'WaterTreatmentPlant.Beacon'), 'SPIN_Z', 2))
    # Ladder up the shaft to the balcony, through its rail gap.
    K.ladder(g, cx - SHAFT_R, cy - .3, .38, SHAFT_TOP, face='left', width=.3, cage=True)
    K.lamp(g, cx + R + .02, cy, SHAFT_TOP + .7, face='right')
    # Riser from the filter house into the shaft.
    P.pipe(g, [(FILTER[0], 1.25, 1.4), (cx + SHAFT_R - .03, 1.25, 1.4)], .08)
    # Treated-water outlet: a flanged socket on the front face of the site,
    # in front of the shaft, for the Timber Pipes OpenOut port (OUTLET).
    oz = .55
    P.pipe(g, [(cx, cy - SHAFT_R + .03, oz), (cx, .38, oz)], .09)
    P.lathe(g, (cx, .22, oz), [(.2, -.16), (.2, -.1), (.16, -.1), (.16, .12), (.12, .16)], IRON, axis='Y',
            segments=16)
    for k in range(8):
        a = k * math.pi / 4
        K.stud(g, (cx + math.cos(a) * .17, .053, oz + math.sin(a) * .17), 'Y', .018)
    g.cylinder((cx, .054, oz), .1, .012, IRON, 'Y', 16)
    P.pier(g, cx, .25, 0, oz - .21, .24)
    P.valve(g, (cx, .5, oz), 'up', .11)
    P.gauge(g, cx + .25, cy - SHAFT_R + .03, 1.5, 'front', .07)


# ---------------------------------------------------------------- pump shed

def pump_shed(g, parts):
    """Pump shed behind the filter house, open to the right edge: framed back
    wall, steel posts and lintel on the open side, flat roof level with the
    filter house's; two flywheel pumps lift into the filters."""
    x0, y0, x1, y1 = SHED
    base = .2
    blk(g, x0 + .05, y0 + .05, -.02, x1, y1, base, CONCRETE)   # floor slab, behind the filter house's foot
    C.framed_block(g, x0 + .12, y1 - .3, x1 - .05, y1 - .05, base, ROOF_Z - .03, infill=FORGED, frame=IRON,
                   faces=('back',), sink=.02,
                   windows={'back': [(6.5, 1.3, .5, 'factory'), (7.5, 1.3, .5, 'factory')]})
    for y in (y0 + .2, (y0 + y1) / 2):
        blk(g, x1 - .17, y - .07, base, x1 - .03, y + .07, ROOF_Z - .1, IRON)
    blk(g, x1 - .16, y0 + .1, ROOF_Z - .26, x1 - .04, y1 - .3, ROOF_Z - .1, IRON)
    # Flat roof slab beside the filter house's (its curb stays the edge).
    blk(g, x0 + .05, y0 + .07, ROOF_Z - Q.ROOF_T, x1 + .06, y1 + .06, ROOF_Z, PAINTED)   # corrugated metal
    w = Q.CURB_W
    blk(g, x0 + .05, y1 + .06 - w, ROOF_Z, x1 + .06, y1 + .06, ROOF_Z + Q.CURB, IRON)
    blk(g, x1 + .06 - w, y0 + .07, ROOF_Z, x1 + .06, y1 + .06 - w, ROOF_Z + Q.CURB, IRON)
    # Two flywheel pumps, axes along Y.
    for i, x in enumerate((6.6, 7.8)):
        py = 4.0
        blk(g, x - .28, py - .3, base, x + .28, py + .3, base + .22, CONCRETE)
        P.lathe(g, (x, py, base + .58), [(0, -.13), (.27, -.11), (.3, -.05), (.3, .05), (.27, .11), (0, .13)],
                PAINTED, axis='Y', segments=18)
        P.motor(g, (x, py + .38, base + .5), .14, .3, axis='Y')
        P.pipe(g, [(x, py, base + .88), (x, py, 1.6), (x, y0 + .02, 1.6)], .07, flanges=False)
        P.gauge(g, x + .15, py - .2, base + .95, 'front', .06)
        fw_ = P.flywheel(f'WaterTreatmentPlant.PumpFlywheel{i + 1}', (x, py - .42, base + .55), .3, axis='Y', spokes=6)
        parts.append((fw_, 'SPIN_Y', 2 if i == 0 else -2))
        blk(g, x - .03, py - .44, base, x + .03, py - .38, base + .25, IRON)
    K.lamp(g, 7.2, y1 - .2, 1.55, face='front')


def build(g, parts):
    for i, (cx, cy, ro, ri) in enumerate(CLARIFIERS):
        clarifier(g, parts, i + 1, cx, cy, ro, ri)
    cascade(g)
    aerator(parts)
    filter_house(g)
    chemical_house(g)
    water_tower(g, parts)
    pump_shed(g, parts)
