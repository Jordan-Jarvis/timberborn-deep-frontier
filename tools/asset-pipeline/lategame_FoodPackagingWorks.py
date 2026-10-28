"""FoodPackagingWorks: cannery for canned fish, packaged and medical food

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the forecourt barrels, crates, post lamp and planting.
(3 workers, 140 hp).

HERO: a tall riveted-steel cannery hall crowned by a glazed monitor roof, with
a 12-layer boiler stack beside it.
ROOF: teal gable with a raised glazed monitor (clerestory) along the ridge;
hipped boiler house; flat parapet roof on the warehouse.

Parts: concrete ground storey with a deep loading bay showing the canning line;
orange-and-steel upper storeys with factory glazing; monitor with turbine
ventilators; three vertical retorts with a jib crane on a concrete pad; boiler
house with two set boilers, steam header and feed pump; tall banded stack with
flue duct; open conveyor bridge carrying crates to a timber warehouse block.

Animated: cans on the canning line (CUSTOM_LOOP_X), seamer turret (SPIN_Z),
crates on the bridge belt (CUSTOM_LOOP_Y), two turbine ventilators (SPIN_Z),
boiler feed-pump rod (PISTON_Z), retort crane hook (PISTON_Z).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN
import lategame_civic_parts as P
from lategame_civic_parts import blk, animate  # noqa: F401
import native_building_assets as N

IDENT = 'FoodPackagingWorks'
# Footprint ends at the walls (cannery front y = 1): forecourt barrels,
# crates, post lamp and planting were removed. GRID_ORIGIN is the
# footprint's (0, 0) corner in the artwork coordinates used below.
FOOTPRINT = (10, 7)
GRID_ORIGIN = (0, 1)
HEIGHT = 12
HERO = 'Tall riveted-steel cannery hall crowned by a glazed monitor roof with turbine ventilators, beside a 12-layer boiler stack.'
FRAME_END = 121

CX0, CY0, CX1, CY1 = 1.0, 1.0, 6.0, 5.0     # cannery on tiles 1..6 x 1..5
BAY0, BAY1, BAY_D, BAY_H = 3.6, 5.6, 1.1, 1.15


def cannery(g, parts):
    top = 1.4
    # Ground storey around a deep loading bay.
    blk(g, CX0, CY0, 0, BAY0, CY1, top - .03, CONCRETE)
    blk(g, BAY1, CY0, 0, CX1, CY1, top - .03, CONCRETE)
    blk(g, BAY0, CY0 + BAY_D, 0, BAY1, CY1, top - .03, CONCRETE)
    blk(g, BAY0, CY0, BAY_H, BAY1, CY0 + BAY_D, top - .03, CONCRETE)
    blk(g, CX0 - .03, CY0 - .03, -.03, CX1 + .03, CY1 + .03, .14, CONCRETE)
    blk(g, CX0 - .05, CY0 - .05, top - .1, CX1 + .05, CY1 + .05, top, CONCRETE)
    for x in (CX0 + 1.0, (BAY1 + CX1) / 2):
        blk(g, x - .05, CY0 - .025, .14, x + .05, CY0, top - .1, CONCRETE)
    for y in (2.0, 3.0, 4.0):
        for x, s in ((CX0, -1), (CX1, 1)):
            blk(g, min(x, x + s * .025), y - .05, .14, max(x, x + s * .025), y + .05, top - .1, CONCRETE)
    P.door(g, 2.5, CY0, 0, 'Door0')
    P.native_window(g, 1.75, CY0, .72, .7, 'front', 'factory')
    P.native_window(g, CX0, 2.4, .72, .7, 'left', 'factory')
    P.native_window(g, CX0, 3.6, .72, .7, 'left', 'factory')
    # Bay interior: steel back plate, side plates, lintel beam and a
    # half-raised roller shutter.
    yb = CY0 + BAY_D
    blk(g, BAY0 + .02, yb - .03, .14, BAY1 - .02, yb, BAY_H - .02, IRON)
    blk(g, BAY0 - .08, CY0 - .06, BAY_H - .14, BAY1 + .08, CY0 + .02, BAY_H + .02, IRON)
    for x in (BAY0 + .01, BAY1 - .01):
        blk(g, x - .05, CY0 - .05, .14, x + .05, CY0 + .02, BAY_H - .14, IRON)
    for k in range(3):
        z = BAY_H - .2 - k * .065
        blk(g, BAY0 + .03, CY0 + .04, z, BAY1 - .03, CY0 + .1, z + .055, FORGED)
    for x in (4.0, 5.2):
        K.lamp(g, x, yb - .03, .95, face='front')
    # Canning line: filler, belt, seamer.
    zb = .55
    blk(g, BAY0 + .05, 1.55, .14, BAY0 + .5, 2.05, 1.0, PAINTED)
    blk(g, BAY0 + .03, 1.53, 1.0, BAY0 + .52, 2.07, 1.06, IRON)
    P.gauge(g, BAY0 + .27, 1.55, .8, 'front')
    blk(g, BAY0 + .5, 1.6, zb - .06, BAY1 - .55, 1.84, zb, IRON)
    for x in (BAY0 + .7, BAY1 - .75):
        blk(g, x - .03, 1.69, .14, x + .03, 1.75, zb - .06, IRON)
    blk(g, BAY1 - .55, 1.5, .14, BAY1 - .05, 2.05, .62, PAINTED)
    blk(g, BAY1 - .57, 1.48, .62, BAY1 - .03, 2.07, .68, IRON)
    seamer = Geometry('SeamerTurret', (BAY1 - .3, 1.78, .8))
    K.revolve(seamer, (BAY1 - .3, 1.78, .68), [(.2, 0), (.2, .1), (.08, .26)], BRASS, segments=12)
    for i in range(6):
        a = i * math.pi / 3
        seamer.cylinder((BAY1 - .3 + math.cos(a) * .16, 1.78 + math.sin(a) * .16, .84), .03, .12, IRON, 'Z', 6)
    parts.append((seamer, 'SPIN_Z', 2))
    cans = Geometry('CanningLine', (4.6, 1.72, zb))
    pitch = .2
    for k in range(9):
        x = BAY0 + .42 + k * pitch
        cans.cylinder((x, 1.72, zb + .07), .055, .14, BRASS, 'Z', 8)
    parts.append((cans, 'CUSTOM_LOOP_X', pitch))
    # Upper storeys: orange plaster in a steel frame, factory glazing.
    xs = [CX0 + .05 + (CX1 - CX0 - .1) * (i + .5) / 5 for i in range(5)]
    ys = [CY0 + .05 + (CY1 - CY0 - .1) * (i + .5) / 4 for i in range(4)]
    P.framed_block(g, CX0 + .05, CY0 + .05, CX1 - .05, CY1 - .05, top, 4.6, infill=ORANGE, frame=IRON,
                   pitch=.98, floors=(3.0,),
                   windows={'front': [(x, z, .85, 'factory') for x in xs for z in (2.2, 3.8)],
                            'back': [(x, 2.2, .85, 'factory') for x in xs[::2]],
                            'left': [(y, z, .85, 'factory') for y in ys for z in (2.2, 3.8)],
                            'right': [(y, 3.8, .85, 'factory') for y in ys[1:]]})
    for x in xs[1::2]:
        for y in (CY0 + .05,):
            K.stud(g, (x - .42, y - .057, 3.0), 'Y', .03)
    # Main gable roof along X and the glazed monitor.
    K.gable_roof(g, CX0 + .05, CY0 + .05, CX1 - .05, CY1 - .05, 4.6, 5.9, ridge_axis='X', overhang=.16)
    my0, my1 = (CY0 + CY1) / 2 - .5, (CY0 + CY1) / 2 + .5
    mx0, mx1 = CX0 + .55, CX1 - .55
    P.framed_block(g, mx0, my0, mx1, my1, 5.0, 6.5, infill=FORGED, frame=IRON, pitch=.78,
                   faces=('front', 'back'), sink=0,
                   windows={'front': [(mx0 + .39 + k * .78, 6.0, .8, 'factory') for k in range(5)],
                            'back': [(mx0 + .39 + k * .78, 6.0, .8, 'factory') for k in range(5)]})
    K.gable_roof(g, mx0, my0, mx1, my1, 6.5, 7.0, ridge_axis='X', overhang=.14, gable_mat=FORGED)
    vy = (my0 + my1) / 2
    for i, x in enumerate((mx0 + .65, mx1 - .65)):
        g.cylinder((x, vy, 7.12), .1, .14, IRON, 'Z', 12)
        vent = Geometry(f'TurbineVent{i}', (x, vy, 7.4))
        K.revolve(vent, (x, vy, 7.19), [(.12, 0), (.24, .1), (.24, .32), (.12, .42), (0, .46)], FORGED, segments=10)
        for k in range(10):
            a = k * 2 * math.pi / 10
            vent.beam((x + math.cos(a) * .245, vy + math.sin(a) * .245, 7.29),
                      (x + math.cos(a + .5) * .245, vy + math.sin(a + .5) * .245, 7.51), .03, .03, IRON)
        parts.append((vent, 'SPIN_Z', 2 if i == 0 else -2))
    # Painted sign board over the bay.
    blk(g, 3.9, CY0 - .03, 1.48, 5.3, CY0 + .052, 1.9, WOOD)
    blk(g, 3.97, CY0 - .045, 1.54, 5.23, CY0 - .03, 1.84, PAINTED)
    for x in (4.25, 4.6, 4.95):
        g.cylinder((x, CY0 - .065, 1.69), .07, .04, BRASS, 'Y', 10)


def retorts(g, parts):
    P.podium(g, 0.0, 1.0, 1.0, 5.0, .3, joints=False, foot=False)   # retort bed on tiles 0..1 x 1..5
    rx = .5
    for y in (1.75, 2.8, 3.85):
        top = K.tank(g, rx, y, .3, .36, 1.25, bands=2, roof='dome')
        g.ring((rx, y, top), .41, .06, .09, BRASS, 'Z', 16)
        for k in range(8):
            a = k * math.pi / 4
            g.box((rx + math.cos(a) * .4, y + math.sin(a) * .4, top + .02), (.06, .06, .1), IRON)
        g.cylinder((rx, y, top + .2), .05, .1, IRON, 'Z', 8)
        P.gauge(g, rx, y - .37, 1.2, 'front')
        P.flanged_pipe(g, [(rx + .36, y, 1.0), (CX0 + .02, y, 1.0)], .05)
    P.flanged_pipe(g, [(.3, 1.4, 1.95), (.3, 4.2, 1.95)], .06)
    for y in (1.75, 2.8, 3.85):
        g.cylinder((.3, y, 1.75), .04, .4, IRON, 'Z', 8)
        g.cylinder((.3 + .18, y, 1.58), .04, .3, IRON, 'X', 8)
    K.valve_wheel(g, .3, 1.32, 1.95, face='front', r=.1)
    # Jib crane over the retort lids.
    blk(g, .2, 4.65, .3, .4, 4.85, 3.0, IRON)   # jib post stands on the retort bed
    g.beam((.3, 4.75, 2.9), (.3, 1.4, 2.9), .12, .16, IRON)
    g.beam((.3, 4.65, 2.2), (.3, 3.7, 2.82), .07, mat=IRON)
    blk(g, .2, 2.68, 2.72, .4, 2.92, 2.82, PAINTED)
    hook = Geometry('RetortHook', (.3, 2.8, 2.3))
    hook.box((.3, 2.8, 2.45), (.02, .02, .5), IRON)
    hook.box((.3, 2.8, 2.18), (.14, .1, .08), PAINTED)
    hook.ring((.3, 2.8, 2.08), .06, .02, .03, IRON, 'Y', 10)
    parts.append((hook, 'PISTON_Z', -.35))


def boilers(g, parts):
    # Boiler house.
    bx0, by0, bx1, by1 = 7.0, 3.0, 10.0, 6.0   # whole tiles
    P.podium(g, bx0, by0, bx1, by1, 1.2, joints=True)
    P.framed_block(g, bx0 + .05, by0 + .05, bx1 - .05, by1 - .05, 1.2, 3.1, infill=ORANGE, pitch=.92,
                   windows={'front': [(7.25, 2.15, 1.0, 'grand'), (9.15, 2.15, 1.0, 'grand')],
                            'right': [(4.4, 2.15, 1.0, 'grand'), (5.6, 2.15, 1.0, 'grand')],
                            'left': [(5.6, 2.15, 1.0, 'grand')]})
    P.hip_roof(g, bx0 + .05, by0 + .05, bx1 - .05, by1 - .05, 3.1, 1.0)
    # Two set boilers in front, drums running into the house.
    # Two boiler settings, one tile each, on tiles 7..9 x 1..3; one shared foot.
    blk(g, 6.97, .97, -.03, 9.03, by0 - .04, .1, CONCRETE)
    for x in (7.5, 8.5):
        blk(g, x - .5, 1.0, 0, x + .5, by0, .62, CONCRETE)
        blk(g, x - .3, .97, .16, x + .3, 1.0, .48, IRON)
        for xx in (x - .18, x + .18):
            K.stud(g, (xx, .955, .32), 'Y', .03)
        P.horizontal_vessel(g, 1.2, by0 + .02, x, .98, .45, axis='Y', bands=3, saddles=False)
        g.cylinder((x, 2.4, 1.57), .16, .3, IRON, 'Z', 12)
        g.ring((x, 2.4, 1.73), .2, .06, .05, BRASS, 'Z', 12)
        g.cylinder((x, 1.7, 1.5), .06, .2, BRASS, 'Z', 8)
        P.flanged_pipe(g, [(x, 2.4, 1.72), (x, 2.4, 2.6)], .07)
        P.gauge(g, x + .25, 1.18, 1.0, 'front')
    # Steam header into the cannery.
    P.flanged_pipe(g, [(9.0, 2.4, 2.6), (CX1 + .02, 2.4, 2.6)], .08)
    K.valve_wheel(g, 6.5, 2.27, 2.6, face='front', r=.13)
    # Feed pump with a reciprocating rod.
    P.pier(g, 9.65, 1.55, 0, .25, .28)
    g.cylinder((9.65, 1.55, .55), .12, .55, PAINTED, 'Z', 12)
    g.ring((9.65, 1.55, .83), .15, .04, .04, BRASS, 'Z', 12)
    blk(g, 9.55, 1.45, 1.4, 9.75, 1.65, 1.46, IRON)
    for x in (9.57, 9.73):
        blk(g, x - .02, 1.53, .82, x + .02, 1.57, 1.4, IRON)
    rod = Geometry('FeedPumpRod', (9.65, 1.55, 1.0))
    rod.cylinder((9.65, 1.55, 1.0), .03, .36, IRON, 'Z', 8)
    rod.box((9.65, 1.55, 1.2), (.18, .08, .05), BRASS)   # crosshead ends run inside the guides
    parts.append((rod, 'PISTON_Z', .14))
    P.flanged_pipe(g, [(9.65, 1.55, 1.46), (9.65, 1.55, 1.8), (9.65, by0 + .05, 1.8)], .04)
    # Stack rising through the hipped roof; feed-water tank on steel legs.
    K.stack(g, 8.2, 5.0, 3.2, 8.5, emits='smoke', r=.34, bands=6)
    P.raised_tank(g, 9.05, 7.2, .55, 1.3, stand=1.0)
    P.flanged_pipe(g, [(9.05, 6.62, 1.6), (9.05, by1 + .05, 1.6)], .05)
    K.ladder(g, 9.05, 7.76, 0, 2.2, face='back', cage=False)


def warehouse_and_bridge(g, parts):
    wx0, wy0, wx1, wy1 = 0.0, 6.0, 5.0, 8.0   # whole tiles
    P.podium(g, wx0, wy0, wx1, wy1, 1.0)
    P.framed_block(g, wx0 + .05, wy0 + .05, wx1 - .05, wy1 - .05, 1.0, 3.6, infill=PLANK, pitch=.88,
                   floors=(2.3,),
                   windows={'back': [(x, 1.65, .8, 'factory') for x in (1.0, 2.6, 4.2)] +
                                     [(x, 2.95, .8, 'factory') for x in (1.0, 2.6, 4.2)],
                            'left': [(6.9, 2.95, .8, 'factory')],
                            'front': [(1.0, 2.95, .8, 'factory'), (4.2, 2.95, .8, 'factory')]})
    K.sawtooth_roof(g, wx0 - .02, wy0 - .02, wx1 + .02, wy1 + .02, 3.63, teeth=2, rise=.85)
    # Open conveyor bridge at layer 3 from cannery to warehouse.
    x0, x1, y0, y1, z = 2.4, 3.4, CY1 - .05, wy0 + .05, 3
    blk(g, x0, y0, z - .14, x1, y1, z, IRON)
    for x in (x0 + .03, x1 - .03):
        blk(g, x - .03, y0, z, x + .03, y1, z + .07, IRON)
        blk(g, x - .025, y0, z + .78, x + .025, y1, z + .84, IRON)
        for k in range(4):
            ya = y0 + .15 + k * (y1 - y0 - .3) / 3
            blk(g, x - .02, ya - .025, z + .07, x + .02, ya + .025, z + .78, IRON)
        for k in range(3):
            ya = y0 + .15 + k * (y1 - y0 - .3) / 3
            yb = y0 + .15 + (k + 1) * (y1 - y0 - .3) / 3
            g.beam((x, ya, z + .1), (x, yb, z + .75), .03, mat=IRON)
    K.gable_roof(g, x0, y0 + .05, x1, y1 - .05, z + .84, z + 1.15, ridge_axis='Y', overhang=.1, gable_mat=FORGED)
    for y in ((y0 + y1) / 2 - .2, (y0 + y1) / 2 + .2):
        blk(g, x0 + .1, y - .04, z + .07, x1 - .1, y + .04, z + .1, IRON)
    belt = Geometry('BridgeCrates', (2.9, 5.3, z + .2))
    pitch = .55
    for k in range(5):
        y = 4.1 + k * pitch
        blk(belt, 2.72, y - .16, z + .1, 3.08, y + .16, z + .42, WOOD)
        blk(belt, 2.7, y - .04, z + .14, 3.1, y + .04, z + .38, PLANK)
    parts.append((belt, 'CUSTOM_LOOP_Y', pitch))
    # Steel portal under the bridge.
    py = (y0 + y1) / 2
    for x in (x0 + .12, x1 - .12):
        blk(g, x - .07, py - .07, .1, x + .07, py + .07, z - .14, IRON)
        P.pier(g, x, py, 0, .1, .2)
    blk(g, x0 + .02, py - .08, z - .3, x1 - .02, py + .08, z - .14, IRON)


def door_lamp(g):
    # Wall lamp by the door (no forecourt props or planting).
    K.lamp(g, 2.0, CY0, 1.1, face='front')


def build(g, parts):
    cannery(g, parts)
    retorts(g, parts)
    boilers(g, parts)
    warehouse_and_bridge(g, parts)
    door_lamp(g)
