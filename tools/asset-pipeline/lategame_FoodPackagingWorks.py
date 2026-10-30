"""FoodPackagingWorks: cannery for canned fish, packaged and medical food
(3 workers, 140 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the forecourt barrels, crates, post lamp and planting.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size", "one layer per floor", "make
the roof flat on more of our buildings", "no roof vents"): 10x7x12 -> 7x5x7, inside the old
footprint with the same origin, door and native entrance (cell 2, -1).
Removed: the cannery's gable, the conveyor bridge's steel portal
and braced side frames, the feed-water tank on its legs, the boiler house's
second bay and the 12-layer stack (now six layers). Storeys are one layer
each.

HERO: a riveted-steel cannery hall of three one-layer storeys crowned by a
glazed monitor lantern, beside a tall boiler stack.
ROOF: flat corrugated-metal roof with a steel curb on the cannery (its front
and back rows placeable) under the glazed monitor's flat steel cap; a hipped
roof of native teal planks on the boiler house with the stack through it; a
flat timber roof on the warehouse. No roof vents.

Parts: concrete ground storey with a loading bay showing the canning line;
orange-and-steel upper storeys with factory glazing; three vertical
retorts with a jib crane on a concrete pad; two set boilers with a feed
pump in front of the boiler house; its stack; a short covered conveyor
bridge on layer 1 carrying crates to a plank-clad warehouse.

Animated (5, names unchanged): cans on the canning line (CUSTOM_LOOP_X),
seamer turret (SPIN_Z), crates on the bridge belt (CUSTOM_LOOP_Y), boiler
feed-pump rod (PISTON_Z), retort crane hook (PISTON_Z). The two turbine
ventilators are gone (user: "no roof vents").
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED
import lategame_civic_parts as P
from lategame_civic_parts import blk, animate  # noqa: F401
import compact_industry_parts as Q

IDENT = 'FoodPackagingWorks'
# Artwork keeps its original coordinates (cannery front y = 1); GRID_ORIGIN is
# the footprint's (0, 0) corner.
FOOTPRINT = (7, 5)
GRID_ORIGIN = (0, 1)
HEIGHT = 7
HERO = ('Riveted-steel cannery hall of three storeys crowned by a glazed monitor lantern, '
        'beside a tall boiler stack.')
FRAME_END = 121

CX0, CY0, CX1, CY1 = 1.0, 1.0, 5.0, 4.0     # cannery on tiles 1..5 x 1..4
CANNERY_LAYERS = 3
BAY0, BAY1, BAY_D, BAY_H = 3.3, 4.7, .85, .9
DOOR_X = 2.5
BOILERS = (5.0, 1.0, 7.0, 4.0)              # set boilers in front of the boiler house
HOUSE = (5.0, 4.0, 7.0, 6.0)                # boiler house on whole tiles
WAREHOUSE = (0.0, 5.0, 3.0, 6.0)
BRIDGE = (1.6, 2.4)                         # covered bridge x span on layer 1


def cannery(g, parts):
    # Ground storey around the loading bay; one coping ring over all of it
    # (the coping is the bay head), one foot course.
    top = 1.0
    blk(g, CX0, CY0, 0, BAY0, CY1, top - .03, CONCRETE)
    blk(g, BAY1, CY0, 0, CX1, CY1, top - .03, CONCRETE)
    blk(g, BAY0, CY0 + BAY_D, 0, BAY1, CY1, top - .03, CONCRETE)
    # Foot and coping stop short at the back-right corner, where the boiler
    # house's own (proud of x = 5, y = 4) take over.
    blk(g, CX0 - .03, CY0 - .03, -.03, CX1 + .03, CY1 - .03, .14, CONCRETE)
    blk(g, CX0 - .03, CY1 - .03, -.03, CX1 - .03, CY1 + .03, .14, CONCRETE)
    blk(g, CX0 - .05, CY0 - .05, BAY_H, CX1 + .05, CY1 - .05, top, CONCRETE)
    blk(g, CX0 - .05, CY1 - .05, BAY_H, CX1 - .05, CY1 + .05, top, CONCRETE)
    P.door(g, DOOR_X, CY0, 0, 'Door0')
    P.native_window(g, 1.5, CY0, .52, .55, 'front', 'factory')
    P.native_window(g, CX0, 2.5, .52, .6, 'left', 'factory')
    P.native_window(g, CX1, 3.5, .52, .6, 'right', 'factory')
    K.lamp(g, DOOR_X - .66, CY0 - .01, .78, face='front')
    # Bay lining: steel back plate, side plates and a half-raised roller shutter.
    yb = CY0 + BAY_D
    floor = .14
    blk(g, BAY0 + .02, yb - .03, floor, BAY1 - .02, yb, BAY_H - .02, IRON)
    for x in (BAY0 + .03, BAY1 - .03):
        blk(g, x - .03, CY0, floor, x + .03, yb - .03, BAY_H - .02, IRON)
    for k in range(3):
        z = BAY_H - .12 - k * .05
        blk(g, BAY0 + .06, CY0 + .04, z, BAY1 - .06, CY0 + .09, z + .045, FORGED)
    K.lamp(g, (BAY0 + BAY1) / 2, yb - .03, .7, face='front')
    # Canning line: filler, belt, seamer.
    zb = .42
    blk(g, BAY0 + .08, 1.35, floor, BAY0 + .4, 1.75, .72, PAINTED)
    blk(g, BAY0 + .06, 1.33, .72, BAY0 + .42, 1.77, .77, IRON)
    blk(g, BAY0 + .4, 1.44, zb - .05, BAY1 - .4, 1.62, zb, IRON)
    for x in (BAY0 + .55, BAY1 - .55):
        blk(g, x - .025, 1.51, floor, x + .025, 1.56, zb - .05, IRON)
    blk(g, BAY1 - .4, 1.34, floor, BAY1 - .06, 1.74, .48, PAINTED)
    blk(g, BAY1 - .42, 1.32, .48, BAY1 - .04, 1.76, .53, IRON)
    seamer = Geometry('SeamerTurret', (BAY1 - .23, 1.54, .62))
    K.revolve(seamer, (BAY1 - .23, 1.54, .53), [(.15, 0), (.15, .08), (.06, .2)], BRASS, segments=12)
    for i in range(6):
        a = i * math.pi / 3
        seamer.cylinder((BAY1 - .23 + math.cos(a) * .12, 1.54 + math.sin(a) * .12, .66), .025, .09, IRON, 'Z', 6)
    parts.append((seamer, 'SPIN_Z', 2))
    cans = Geometry('CanningLine', ((BAY0 + BAY1) / 2, 1.53, zb))
    pitch = .16
    for k in range(4):
        x = BAY0 + .5 + k * pitch
        cans.cylinder((x, 1.53, zb + .055), .045, .11, BRASS, 'Z', 8)
    parts.append((cans, 'CUSTOM_LOOP_X', pitch))
    # Upper storeys (one layer each): orange plaster in a steel frame.
    roof = float(CANNERY_LAYERS)
    xs = [x + .5 for x in range(1, 5)]
    ys = [y + .5 for y in range(1, 4)]
    P.framed_block(g, CX0 + .05, CY0 + .05, CX1 - .05, CY1 - .05, top, roof - .06, infill=ORANGE, frame=IRON,
                   floors=(2.0,),
                   windows={'front': [(x, z, .58, 'factory') for x in xs for z in (1.5, 2.5)],
                            'back': [(x, 2.5, .58, 'factory') for x in xs[::2]] + [(x, 1.5, .58, 'factory') for x in xs[1::2]],
                            'left': [(y, z, .58, 'factory') for y in ys for z in (1.5, 2.5)],
                            'right': [(y, 2.5, .58, 'factory') for y in ys]})
    Q.flat_roof(g, CX0 + .05, CY0 + .05, CX1 - .05, CY1 - .05, roof, overhang=.11, mat=PAINTED, curb_mat=IRON,
                boards=True)
    # Glazed monitor lantern (daylight for the canning floors) with a flat steel cap.
    mx0, my0, mx1, my1 = 1.6, 2.0, 4.4, 3.0
    mz = roof + .55
    P.framed_block(g, mx0, my0, mx1, my1, roof, mz, infill=FORGED, frame=IRON, pitch=.7,
                   faces=('front', 'back'), sink=.02,
                   windows={'front': [(mx0 + .35 + k * .7, roof + .28, .4, 'factory') for k in range(4)],
                            'back': [(mx0 + .35 + k * .7, roof + .28, .4, 'factory') for k in range(4)]})
    blk(g, mx0 - .08, my0 - .08, mz - .02, mx1 + .08, my1 + .08, mz + .08, IRON)
    # Painted sign board over the bay.
    blk(g, 3.3, CY0 - .03, 1.12, 4.7, CY0 + .052, 1.38, WOOD)
    blk(g, 3.36, CY0 - .045, 1.16, 4.64, CY0 - .03, 1.34, PAINTED)
    for x in (3.7, 4.0, 4.3):
        g.cylinder((x, CY0 - .065, 1.25), .06, .04, BRASS, 'Y', 10)


def retorts(g, parts):
    P.podium(g, 0.0, 1.0, 1.0, 4.0, .3, joints=False, foot=False)   # retort bed on tiles 0..1 x 1..4
    rx = .5
    for y in (1.55, 2.45, 3.35):
        top = K.tank(g, rx, y, .3, .3, 1.0, bands=2, roof='dome')
        g.ring((rx, y, top), .34, .05, .07, BRASS, 'Z', 16)
        g.cylinder((rx, y, top + .17), .04, .08, IRON, 'Z', 8)
        P.gauge(g, rx, y - .31, 1.0, 'front')
        P.flanged_pipe(g, [(rx + .3, y, .85), (CX0 + .02, y, .85)], .045)
    # Jib crane over the retort lids.
    blk(g, .2, 3.82, .3, .38, 3.98, 2.3, IRON)
    g.beam((.29, 3.9, 2.22), (.29, 1.25, 2.22), .1, .13, IRON)
    g.beam((.29, 3.82, 1.65), (.29, 3.1, 2.16), .06, mat=IRON)
    blk(g, .2, 2.35, 2.07, .38, 2.55, 2.16, PAINTED)
    hook = Geometry('RetortHook', (.29, 2.45, 1.75))
    hook.box((.29, 2.45, 1.86), (.02, .02, .4), IRON)
    hook.box((.29, 2.45, 1.63), (.12, .09, .07), PAINTED)
    hook.ring((.29, 2.45, 1.54), .05, .02, .03, IRON, 'Y', 10)
    parts.append((hook, 'PISTON_Z', -.25))


def boilers(g, parts):
    x0, y0, x1, y1 = BOILERS
    # Two boiler settings, one tile each, on a shared foot; drums run into the house.
    blk(g, x0 + .1, y0 + .1, -.03, x1 - .03, y1 - .05, .1, CONCRETE)
    for x in (5.6, 6.5):
        blk(g, x - .42, y0 + .15, 0, x + .42, y1 - .1, .5, CONCRETE)
        blk(g, x - .26, y0 + .12, .14, x + .26, y0 + .15, .4, IRON)
        for xx in (x - .15, x + .15):
            K.stud(g, (xx, y0 + .105, .27), 'Y', .025)
        P.horizontal_vessel(g, y0 + .3, y1 + .02, x, .86, .36, axis='Y', bands=3, saddles=False)
        g.cylinder((x, 2.6, 1.3), .13, .24, IRON, 'Z', 12)
        g.ring((x, 2.6, 1.43), .16, .05, .04, BRASS, 'Z', 12)
        P.flanged_pipe(g, [(x, 2.6, 1.42), (x, 2.6, 1.75)], .06)
        P.gauge(g, x + .2, y0 + .45, .86, 'front')
    # Steam header into the cannery's right wall.
    P.flanged_pipe(g, [(6.5, 2.6, 1.75), (CX1 + .02, 2.6, 1.75)], .07)
    K.valve_wheel(g, 5.3, 2.47, 1.75, face='front', r=.11)
    # Feed pump with a reciprocating rod, between the boiler fronts.
    px, py = 6.05, 1.4
    g.cylinder((px, py, .72), .09, .44, PAINTED, 'Z', 12)
    g.ring((px, py, .94), .12, .035, .035, BRASS, 'Z', 12)
    blk(g, px - .08, py - .08, 1.38, px + .08, py + .08, 1.43, IRON)
    for x in (px - .065, px + .065):
        blk(g, x - .015, py - .015, .94, x + .015, py + .015, 1.38, IRON)
    rod = Geometry('FeedPumpRod', (px, py, 1.05))
    rod.cylinder((px, py, 1.05), .025, .3, IRON, 'Z', 8)
    rod.box((px, py, 1.2), (.14, .06, .04), BRASS)   # crosshead ends run inside the guides
    parts.append((rod, 'PISTON_Z', .1))
    P.flanged_pipe(g, [(px, py, 1.43), (px, py, 1.6), (px, 3.95, 1.6)], .035)


def boiler_house(g):
    x0, y0, x1, y1 = HOUSE
    top = Q.storey_block(g, x0, y0, x1, y1, 2, infill=ORANGE, frame=WOOD, roof=False,
                         ground_windows={'right': [(5.0, .55, 'grand')], 'back': [(6.0, .55, 'grand')]},
                         windows={'front': [(5.5, 1.5, .52, 'grand'), (6.5, 1.5, .52, 'grand')],
                                  'right': [(4.5, 1.5, .52, 'grand'), (5.5, 1.5, .52, 'grand')],
                                  'back': [(5.5, 1.5, .52, 'grand'), (6.5, 1.5, .52, 'grand')]})
    # Hipped roof of native teal roof planks, the boiler stack rising through it.
    P.hip_roof(g, x0 + .05, y0 + .05, x1 - .05, y1 - .05, top, .7, overhang=.14)
    K.stack(g, 6.0, 5.0, top - .2, 4.85, emits='smoke', r=.26, bands=4)


def warehouse_and_bridge(g, parts):
    x0, y0, x1, y1 = WAREHOUSE
    Q.storey_block(g, x0, y0, x1, y1, 2, infill=PLANK, frame=WOOD, roof_mat=PLANK, curb_mat=WOOD, roof_boards=True,
                   ground_windows={'back': [(.5, .55, 'factory'), (2.5, .55, 'factory')],
                                   'left': [(5.5, .55, 'factory')]},
                   windows={'back': [(x + .5, 1.5, .55, 'factory') for x in range(3)],
                            'left': [(5.5, 1.5, .55, 'factory')],
                            'front': [(.5, 1.5, .55, 'factory')]})
    # Covered conveyor bridge on layer 1 from the cannery to the warehouse.
    bx0, bx1 = BRIDGE
    ya, yb = CY1 + .05, y0 + .05
    z = 1.0
    blk(g, bx0, ya, z - .15, bx1, yb - .1, z - .03, IRON)   # between the two copings, under their tops
    for x in (bx0 + .03, bx1 - .03):
        blk(g, x - .03, ya, z, x + .03, yb, z + .06, IRON)
        blk(g, x - .025, ya, z + .66, x + .025, yb, z + .71, IRON)
        for k in range(3):
            yy = ya + .1 + k * (yb - ya - .2) / 2
            blk(g, x - .02, yy - .025, z + .06, x + .02, yy + .025, z + .66, IRON)
    blk(g, bx0 - .06, ya - .02, z + .71, bx1 + .06, yb + .02, z + .77, IRON)
    for y in ((ya + yb) / 2 - .15, (ya + yb) / 2 + .15):
        blk(g, bx0 + .1, y - .03, z + .06, bx1 - .1, y + .03, z + .09, IRON)
    belt = Geometry('BridgeCrates', ((bx0 + bx1) / 2, (ya + yb) / 2, z + .2))
    pitch = .45
    for k in range(3):
        y = ya + .05 + k * pitch
        blk(belt, 1.84, y - .13, z + .09, 2.16, y + .13, z + .37, WOOD)
        blk(belt, 1.82, y - .035, z + .12, 2.18, y + .035, z + .34, PLANK)
    parts.append((belt, 'CUSTOM_LOOP_Y', pitch))


def build(g, parts):
    cannery(g, parts)
    retorts(g, parts)
    boilers(g, parts)
    boiler_house(g)
    warehouse_and_bridge(g, parts)
