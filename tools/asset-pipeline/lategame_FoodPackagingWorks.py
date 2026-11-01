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

Second shrink 2026-11-01 (a YouTuber called the late-game buildings
"massive"; user: "we need to shrink the buildings down even more"):
7x5x7 -> 4x3x4, inside the old footprint with the same origin, door and
native entrance (cell 2, -1). Every new block is one the old works
occupied: the cannery keeps the old three-layer roof height and its
monitor lantern's flat cap sits on layer 4 over the middle row, where the
old one was, so things on those old roofs keep their support. Removed: the
warehouse and the covered conveyor bridge (the crates now ride a short
roller belt out of the loading bay), the second boiler and the two-storey
boiler house (one boiler now, in a one-storey house with the stack).

HERO: a riveted-steel cannery hall of three one-layer storeys crowned by a
glazed monitor lantern, beside its retorts and a small boiler house with
its stack.
ROOF: flat corrugated-metal roof on the cannery, open edge to edge, its
front and back rows placeable, and the glazed monitor's flat steel cap on
layer 4 (placeable too); a hipped roof of native teal planks on the boiler
house with the stack through it. No roof vents.

Plan (4 x 3 tiles; artwork y = grid y + 1): the retort bed with three
vertical retorts and the jib crane on tiles 0..1; the cannery on tiles 1..3
(the door front-right, the loading bay front-left with the canning line and
the crate belt); the boiler strip on tiles 3..4: one set boiler with its
feed pump in front of the one-storey boiler house and its stack.

Animated (5, names unchanged): cans on the canning line (CUSTOM_LOOP_X),
seamer turret (SPIN_Z), crates on the bay's roller belt (CUSTOM_LOOP_Y),
boiler feed-pump rod (PISTON_Z), retort crane hook (PISTON_Z).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, BRICK
import lategame_civic_parts as P
from lategame_civic_parts import blk, animate  # noqa: F401
import compact_industry_parts as Q

IDENT = 'FoodPackagingWorks'
# Artwork keeps its original coordinates (cannery front y = 1); GRID_ORIGIN is
# the footprint's (0, 0) corner.
FOOTPRINT = (4, 3)
GRID_ORIGIN = (0, 1)
HEIGHT = 4
HERO = ('Riveted-steel cannery hall of three storeys crowned by a glazed monitor lantern, '
        'beside its retorts and a small boiler house with a stack.')
FRAME_END = 121

CX0, CY0, CX1, CY1 = 1.0, 1.0, 3.0, 4.0     # cannery on tiles 1..3 x 1..4
CANNERY_LAYERS = 3
BAY0, BAY1, BAY_D, BAY_H = 1.08, 1.95, .85, .9
DOOR_X = 2.5
BOILER_X = 3.5
HOUSE = (3.1, 3.0, 4.0, 4.0)                # one-storey boiler house on the back tile


def cannery(g, parts):
    # Ground storey around the loading bay; one coping ring over all of it
    # (the coping is the bay head), one foot course.
    top = 1.0
    # Brick walls (2026-10-31: brick as a main wall material).
    blk(g, BAY1, CY0, 0, CX1, CY1, top - .03, BRICK)
    blk(g, CX0, CY0 + BAY_D, 0, BAY1, CY1, top - .03, BRICK)
    blk(g, CX0, CY0, 0, BAY0, CY0 + BAY_D, top - .03, BRICK)
    blk(g, CX0 - .03, CY0 - .03, -.03, CX1 + .03, CY1 + .03, .14, CONCRETE)
    blk(g, CX0 - .05, CY0 - .05, BAY_H, CX1 + .05, CY1 + .05, top, CONCRETE)
    features = [((BAY0, CY0, 0), (BAY1, CY0 + BAY_D, BAY_H))]
    box = lambda fn: features.append(P.authored_box(g, fn))
    box(lambda g: P.door(g, DOOR_X, CY0, 0, 'Door0'))
    box(lambda g: P.native_window(g, CX0, 2.5, .52, .6, 'left', 'factory'))
    box(lambda g: P.native_window(g, CX0, 3.5, .52, .6, 'left', 'factory'))
    box(lambda g: K.lamp(g, DOOR_X + .55, CY0 - .01, .78, face='front'))
    P.brick_skin(g, CX0, CY0, CX1, CY1, .14, BAY_H, features=features)
    # Bay lining: steel back plate, side plates and a half-raised roller shutter.
    yb = CY0 + BAY_D
    floor = .14
    blk(g, BAY0 + .02, yb - .03, floor, BAY1 - .02, yb, BAY_H - .02, IRON)
    for x in (BAY0 + .03, BAY1 - .03):
        blk(g, x - .03, CY0, floor, x + .03, yb - .03, BAY_H - .02, IRON)
    for k in range(3):
        z = BAY_H - .12 - k * .05
        blk(g, BAY0 + .06, CY0 + .04, z, BAY1 - .06, CY0 + .09, z + .045, FORGED)
    # Canning line across the bay's back: filler, belt, seamer.
    zb = .42
    ly = 1.66
    blk(g, BAY0 + .07, ly - .13, floor, BAY0 + .3, ly + .13, .66, PAINTED)
    blk(g, BAY0 + .06, ly - .14, .66, BAY0 + .31, ly + .14, .7, IRON)
    blk(g, BAY0 + .3, ly - .07, zb - .05, BAY1 - .3, ly + .07, zb, IRON)
    blk(g, BAY1 - .3, ly - .13, floor, BAY1 - .07, ly + .13, .46, PAINTED)
    blk(g, BAY1 - .31, ly - .14, .46, BAY1 - .06, ly + .14, .5, IRON)
    seamer = Geometry('SeamerTurret', (BAY1 - .185, ly, .58))
    K.revolve(seamer, (BAY1 - .185, ly, .5), [(.11, 0), (.11, .07), (.05, .16)], BRASS, segments=12)
    for i in range(6):
        a = i * math.pi / 3
        seamer.cylinder((BAY1 - .185 + math.cos(a) * .085, ly + math.sin(a) * .085, .61), .02, .07, IRON, 'Z', 6)
    parts.append((seamer, 'SPIN_Z', 2))
    cans = Geometry('CanningLine', ((BAY0 + BAY1) / 2, ly, zb))
    pitch = .11
    for k in range(2):
        x = BAY0 + .38 + k * pitch
        cans.cylinder((x, ly, zb + .045), .035, .09, BRASS, 'Z', 8)
    parts.append((cans, 'CUSTOM_LOOP_X', pitch))
    # Crates out of the bay on a short roller belt (was the conveyor bridge).
    bx = (BAY0 + BAY1) / 2
    blk(g, bx - .2, 1.04, floor, bx + .2, 1.5, .2, IRON)
    belt = Geometry('BridgeCrates', (bx, 1.27, .32))
    pitch = .22
    for k in range(2):
        y = 1.12 + k * pitch
        blk(belt, bx - .11, y - .08, .2, bx + .11, y + .08, .36, WOOD)
        blk(belt, bx - .12, y - .025, .22, bx + .12, y + .025, .34, PLANK)
    parts.append((belt, 'CUSTOM_LOOP_Y', pitch))
    # Upper storeys (one layer each): brick in a steel frame.
    roof = float(CANNERY_LAYERS)
    xs = [1.5, 2.5]
    ys = [1.5, 2.5, 3.5]
    P.framed_block(g, CX0 + .05, CY0 + .05, CX1 - .05, CY1 - .05, top, roof - .06, infill=BRICK, frame=IRON,
                   floors=(2.0,),
                   windows={'front': [(x, z, .58, 'factory') for x in xs for z in (1.5, 2.5)],
                            'back': [(1.5, 2.5, .58, 'factory'), (2.5, 1.5, .58, 'factory')],
                            'left': [(y, z, .58, 'factory') for y in ys for z in (1.5, 2.5)],
                            'right': [(1.5, 2.5, .58, 'factory'), (2.5, 2.5, .58, 'factory')]})
    Q.flat_roof(g, CX0 + .05, CY0 + .05, CX1 - .05, CY1 - .05, roof, overhang=.11, mat=PAINTED, slab_mat=IRON,
                boards=True)
    # Glazed monitor lantern (daylight for the canning floors); its flat steel
    # cap is a roof deck on layer 4, where the old lantern cap was.
    mx0, my0, mx1, my1 = 1.2, 2.06, 2.8, 2.94
    mz = 3.92
    P.framed_block(g, mx0, my0, mx1, my1, roof, mz, infill=FORGED, frame=IRON, pitch=.8,
                   faces=('front', 'back'), sink=.02,
                   windows={'front': [(mx0 + .4 + k * .8, roof + .45, .45, 'factory') for k in range(2)],
                            'back': [(mx0 + .4 + k * .8, roof + .45, .45, 'factory') for k in range(2)]})
    blk(g, mx0 - .08, my0 - .05, mz - .02, mx1 + .08, my1 + .05, mz + .08, IRON)
    # Painted sign board over the bay.
    blk(g, BAY0, CY0 - .03, 1.12, BAY1, CY0 + .052, 1.38, WOOD)
    blk(g, BAY0 + .06, CY0 - .045, 1.16, BAY1 - .06, CY0 - .03, 1.34, PAINTED)
    for x in (1.3, 1.52, 1.74):
        g.cylinder((x, CY0 - .065, 1.25), .05, .04, BRASS, 'Y', 10)


def retorts(g, parts):
    P.podium(g, 0.0, 1.0, .95, 4.0, .3, joints=False, foot=False)   # retort bed on tiles 0..1 x 1..4 (its coping meets the cannery)
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


def boiler(g, parts):
    """One set boiler on tiles 3..4 x 1..3, its drum running into the boiler
    house, the feed pump at its front and a steam header into the cannery."""
    x = BOILER_X
    blk(g, 3.1, 1.08, -.03, 3.97, 2.9, .1, CONCRETE)
    blk(g, x - .4, 1.15, 0, x + .4, 2.86, .5, CONCRETE)
    blk(g, x - .25, 1.12, .14, x + .25, 1.15, .4, IRON)
    for xx in (x - .14, x + .14):
        K.stud(g, (xx, 1.105, .27), 'Y', .025)
    P.horizontal_vessel(g, 1.3, 3.02, x, .86, .34, axis='Y', bands=3, saddles=False)
    g.cylinder((x, 2.4, 1.28), .12, .22, IRON, 'Z', 12)
    g.ring((x, 2.4, 1.4), .15, .05, .04, BRASS, 'Z', 12)
    P.flanged_pipe(g, [(x, 2.4, 1.39), (x, 2.4, 1.7), (CX1 + .02, 2.4, 1.7)], .06)
    K.valve_wheel(g, 3.25, 2.27, 1.7, face='front', r=.1)
    P.gauge(g, x + .22, 1.42, .86, 'front')
    # Feed pump with a reciprocating rod beside the boiler front.
    px, py = 3.84, 1.3
    g.cylinder((px, py, .72), .08, .44, PAINTED, 'Z', 12)
    g.ring((px, py, .94), .11, .03, .035, BRASS, 'Z', 12)
    blk(g, px - .07, py - .07, 1.38, px + .07, py + .07, 1.43, IRON)
    for xx in (px - .055, px + .055):
        blk(g, xx - .013, py - .013, .94, xx + .013, py + .013, 1.38, IRON)
    rod = Geometry('FeedPumpRod', (px, py, 1.05))
    rod.cylinder((px, py, 1.05), .022, .3, IRON, 'Z', 8)
    rod.box((px, py, 1.2), (.12, .05, .04), BRASS)   # crosshead ends run inside the guides
    parts.append((rod, 'PISTON_Z', .1))
    P.flanged_pipe(g, [(px, py, 1.43), (px, py, 1.55), (px, 2.95, 1.55)], .03)


def boiler_house(g):
    x0, y0, x1, y1 = HOUSE
    top = Q.storey_block(g, x0, y0, x1, y1, 1, ground_windows={'right': [(3.5, .5, 'grand')]})
    # Hipped roof of native teal roof planks, the boiler stack rising through it.
    P.hip_roof(g, x0 + .05, y0 + .05, x1 - .05, y1 - .05, top, .55, overhang=.08)
    K.stack(g, 3.55, 3.5, top - .2, 2.0, emits='smoke', r=.2, bands=3)


def build(g, parts):
    cannery(g, parts)
    retorts(g, parts)
    boiler(g, parts)
    boiler_house(g)
