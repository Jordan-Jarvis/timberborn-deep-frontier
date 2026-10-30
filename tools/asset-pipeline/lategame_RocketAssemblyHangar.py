"""Rocket Assembly Hangar: the vertical assembly hall of the space program.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the east parts yard with its bridge crane and stacked parts, the track
apron and transporter in front, and the projecting hoist hood.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; outputs/compaction/BRIEF.md): 8x9x14 -> 7x8x9, inside the old
footprint with the same origin, workshop door (x 1.5) and native entrance.
The hall is 5 tiles wide and springs its vault at layer 7 (it was 11); the
bay holds the first stage of the 0.8-scale Launch Pad rocket. The ridge
walkway with its rails and the bay's two work-platform tiers are gone, and
the workshop's mono-pitch roof is now flat. The barrel vault stays: it is the
hangar's defining silhouette.

Hero: a barrel-vaulted assembly hall whose riveted sliding doors stand partly
open on a dark bay holding a rocket stage.
Roof types: teal barrel vault with steel ribs (the defining silhouette);
flat timber-decked roof with a parapet ring over the one-storey workshop (a
usable roof deck); no roof vents or roof stack (roof-variety pass): the forge
flue rises from the ground in the workshop's left wall.

Animated (names unchanged): right door leaf (slide X), two vault beacons
(the workshop roof ventilator rotors are gone).
"""
import math

from lategame_kit import *
from frontier_architecture import Geometry
from architectural_windows import window
from lategame_space_parts import (bx, door_block, pilasters, gauge, rail, BURY, animate)
from lategame_roofdeck_parts import parapet_ring
from lategame_sheet_roofs import plate_deck

IDENT = 'RocketAssemblyHangar'
FOOTPRINT = (7, 8)
HEIGHT = 9
FRAME_END = 121
HERO = 'Barrel-vaulted assembly hall with riveted sliding doors ajar on a rocket stage'

HX0, HX1 = 2.0, 6.88         # hall walls (right base course .12 proud, on x = 7)
HY0, HY1 = 0.0, 7.88         # front on y = 0; back base course on the footprint edge
SPRING, RISE = 7.0, 1.4
BASE = 1.0                   # concrete lower storey of the hall
TIER = 4.0                   # forged tier below, orange plaster tier above
BAY = (3.9, 6.4)             # open assembly bay behind the doors
BAY_TOP = 6.1
BAY_BACK = 2.0
STAGE = (5.15, 1.0)
STAGE_R = .68                # the 0.8-scale rocket's first-stage radius
LEAN = (0.0, 0.0, HX0, 7.0)  # one-storey workshop on tiles 0..2 x 0..7
LEAN_TOP = 1.84              # its roof slab bottom; the roof top is layer 2


def hall(g):
    bx0, bx1 = BAY
    bx(g, HX0, HY0, 0, bx0, HY1, SPRING - .03, IRON)
    bx(g, bx1, HY0, 0, HX1, HY1, SPRING - .03, IRON)
    bx(g, bx0, HY0, BAY_TOP, bx1, HY1, SPRING - .03, IRON)
    bx(g, bx0, BAY_BACK, 0, bx1, HY1, BAY_TOP, IRON)
    # Concrete base course on the exposed sides and back.
    bx(g, HX1, HY0 + .3, -BURY, HX1 + .12, HY1 + .12, BASE, CONCRETE)
    bx(g, HX0 - .12, HY1, -BURY, HX1, HY1 + .12, BASE, CONCRETE)
    bx(g, HX1 - .02, HY0 + .3, BASE - .06, HX1 + .17, HY1 + .17, BASE + .08, CONCRETE)
    bx(g, HX0 - .17, HY1 - .02, BASE - .06, HX1 - .02, HY1 + .17, BASE + .08, CONCRETE)
    ys = [HY0 + .3 + (HY1 - HY0 - .3) * (k + .5) / 5 for k in range(5)]
    xs = [HX0 + .8 + 1.6 * k for k in range(3)]
    pilasters(g, 'Y', HX1 + .12, HY0 + .3, HY1 + .12, .1, BASE - .1, 1, pitch=1.5, w=.16)
    pilasters(g, 'X', HY1 + .12, HX0 - .12, HX1 + .12, .1, BASE - .1, 1, pitch=1.6, w=.16)
    for lo, hi, infill, zs in ((BASE + .06, TIER, FORGED, (2.5,)), (TIER, SPRING, ORANGE, (5.5,))):
        frame_wall(g, 'Y', HX1, HY0 + .3, HY1, lo, hi, outward=1, infill=infill, bays=5,
                   windows=[(y, z) for y in ys for z in zs], window_scale=.75)
        frame_wall(g, 'X', HY1, HX0 + .055, HX1 - .055, lo, hi, outward=1, infill=infill, bays=3,
                   windows=[(x, z) for x in xs for z in zs], window_scale=.75)
    frame_wall(g, 'Y', HX0, HY0 + .3, HY1, LEAN_TOP + .3, TIER, outward=-1, infill=FORGED, bays=5,
               windows=[(y, 3.0) for y in ys], window_scale=.75)
    frame_wall(g, 'Y', HX0, HY0 + .3, HY1, TIER, SPRING, outward=-1, infill=ORANGE, bays=5,
               windows=[(y, 5.5) for y in ys], window_scale=.75)
    barrel_roof(g, HX0, HY0, HX1, HY1, SPRING, RISE, axis='Y', segments=12, ribs=4, overhang=.14)
    half = (HX1 - HX0) / 2
    cx = (HX0 + HX1) / 2
    for y, out in ((HY0, -1), (HY1, 1)):
        arch_infill(g, 'Y', y, cx, half + .08, SPRING, RISE - .04, out, ORANGE, segments=12)
    window(g, cx - 1.0, HY1, SPRING + .55, .6, 'back', 'grand')
    window(g, cx + 1.0, HY1, SPRING + .55, .6, 'back', 'grand')
    window(g, cx - 1.2, HY0, SPRING + .5, .55, 'front', 'grand')
    for y, s in ((HY0, -1), (HY1, 1)):
        for x in (cx - 1.9, cx + 1.9):
            bx(g, x - .05, y - (.07 if s < 0 else 0), SPRING - .02, x + .05, y + (.07 if s > 0 else 0),
               SPRING + .5, WOOD)
    for x, y in ((HX1, HY1), (HX0, HY1)):
        bx(g, x - .13, y - .13, .01, x + .13, y + .13, SPRING - .05, IRON)
    bx(g, HX0 - .1, HY0 - .12, LEAN_TOP + .3, HX0 + .4, HY0 + .3, SPRING - .05, IRON)
    bx(g, HX1 - .1, HY0 - .12, BASE, HX1 + .15, HY0 + .3, SPRING - .05, IRON)
    bx(g, HX1 - .1, HY0 - .12, .01, HX1 + .15, HY0 + .3, BASE, CONCRETE)
    # Door header: riveted girder carrying the overhead track.
    bx(g, HX0 - .08, HY0 - .14, BAY_TOP + .2, HX1 + .1, HY0 + .05, SPRING - .06, FORGED)
    bx(g, HX0 - .12, HY0 - .18, SPRING - .18, HX1 + .12, HY0 + .05, SPRING, IRON)
    gauge(g, 3.4, HY0 - .14, BAY_TOP + .55, 'front', .1)


def bay(g):
    """Dark open bay with the first rocket stage upright on its dolly."""
    bx0, bx1 = BAY
    sx, sy = STAGE
    r = STAGE_R
    bx(g, bx0, HY0, -BURY, bx1, BAY_BACK, .04, CONCRETE)
    bx(g, sx - .8, sy - .7, .04, sx + .8, sy + .7, .34, PAINTED)
    for x in (sx - .6, sx + .6):
        for y in (sy - .45, sy + .45):
            g.cylinder((x, y, .17), .14, .1, IRON, 'X', 12)
    # The rocket's first stage (0.8 scale): banded teal and steel courses.
    z = .34
    for mat, h in ((IRON, .36), (IRON, .96), (PAINTED, 1.04), (IRON, .4), (PAINTED, 1.04), (IRON, .72)):
        revolve(g, (sx, sy, z), [(r, 0), (r, h)], mat, segments=16, cap_bottom=z == .34)
        z += h
    for zz in (1.66, 2.7, 3.1, 4.14):
        band(g, (sx, sy, 0), r, zz, .07, BRASS, segments=16, proud=.025)
    revolve(g, (sx, sy, z), [(r, 0), (r * .82, .2), (r * .82, .24)], IRON, segments=16, cap_bottom=False)
    top = z + .24
    bx(g, sx - .62, sy - .07, top - .02, sx + .62, sy + .07, top + .12, BRASS)
    for x, dy in ((sx - .5, -.035), (sx + .5, .035)):
        g.beam((x, sy + dy, top + .1), (sx, sy + dy, top + .62), .05, mat=IRON)
    g.ring((sx, sy, top + .7), .1, .035, .05, IRON, 'Y', 12)
    g.beam((sx, sy, top + .75), (sx, sy, BAY_TOP - .01), .03, mat=IRON)
    lamp(g, sx, BAY_BACK, 5.4, face='front')
    for z in (1.8, 4.2):
        lamp(g, bx1, HY0 + .5, z, face='left')
        lamp(g, bx0, HY0 + .7, z, face='right')


def door_track(g):
    bx(g, HX0 + .45, -.29, BAY_TOP + .08, HX1 + .05, -.18, BAY_TOP + .38, IRON)
    bx(g, HX0 + .45, -.29, -.035, HX1 + .05, -.2, .04, IRON)


def doors(g, parts):
    """Two riveted sliding leaves; the right one stands ajar and slides further."""
    def leaf(name, x0, x1):
        d = Geometry(name, ((x0 + x1) / 2, -.2, BAY_TOP / 2))
        y0, y1 = -.16, -.04
        top = BAY_TOP + .05
        n = round((x1 - x0 - .12) / .33)
        for k in range(n):
            xa = x0 + .06 + (x1 - x0 - .12) * k / n
            xb = x0 + .06 + (x1 - x0 - .12) * (k + 1) / n
            bx(d, xa, y0 + .02, .1, xb, y1 - .02, top - .06, GREYPLANK)
        for x in (x0 + .07, (x0 + x1) / 2, x1 - .07):
            bx(d, x - .07, y0 - .01, .06, x + .07, y0 + .06, top, IRON)
        for z in (.15, 2.1, 4.1, top - .1):
            bx(d, x0 + .14, y0 - .03, z - .06, x1 - .14, y0 + .05, z + .06, IRON)
        for (xa, xb) in ((x0 + .14, (x0 + x1) / 2 - .07), ((x0 + x1) / 2 + .07, x1 - .14)):
            d.beam((xa, y0 - .015, .22), (xb, y0 - .015, 2.0), .06, mat=IRON)
        for x in (((x0 * 3 + x1) / 4 + .02, (x0 + 3 * x1) / 4 - .02) if x1 - x0 > 2 else ((x0 + x1) / 2,)):
            window(d, x, y0 + .02, 5.0, .7, 'front', 'factory')
        for x in (x0 + .35, x1 - .35):
            bx(d, x - .05, -.27, top - .03, x + .05, -.21, BAY_TOP + .15, IRON)
            d.cylinder((x, -.245, .11), .06, .09, IRON, 'Y', 10)
        hx = x0 + .22 if name.endswith('Right') else x1 - .22
        bx(d, hx - .03, y0 - .1, .8, hx + .03, y0 - .04, 1.55, BRASS)
        return d
    left = leaf('RocketAssemblyHangar.DoorLeft', HX0 + .4, 4.05)
    parts.append((left, 'STATIC', 0))
    right = leaf('RocketAssemblyHangar.DoorRight', 5.8, 6.85)
    parts.append((right, 'SLIDE_X', -.5))


def workshop(g, parts):
    x0, y0, x1, y1 = LEAN
    door_block(g, x0, y0, x1, y1, 0, 1.2, 1.5, CONCRETE, door_id='WorkshopDoor')
    bx(g, x0 - .05, y0 - .05, 1.12, x1, y1 + .05, 1.3, CONCRETE)
    bx(g, x0, y0, 1.3, x1, y1, LEAN_TOP, ORANGE)
    for y in [y0 + .02] + [y0 + 1.4 * k for k in range(1, 5)] + [y1 - .02]:
        bx(g, x0 - .05, y - .06, 1.3, x0 + .02, y + .06, LEAN_TOP - .03, WOOD)
    bx(g, x0 - .06, y0 + .12, 1.32, x0 + .02, y1 - .12, 1.4, WOOD)
    for x in (x0 + .03, x1 - .35):
        bx(g, x - .06, y0 - .05, 1.3, x + .06, y0 + .02, LEAN_TOP - .03, WOOD)
    for k in range(4):
        window(g, x0, y0 + .9 + 1.6 * k, 1.58, .4, 'left', 'grand')
    lamp(g, .7, y0, 1.0, face='front')
    bx(g, x0 - .05, y0 - .05, LEAN_TOP, x1, y1 + .05, LEAN_TOP + .12, CONCRETE)
    plate_deck(g, x0 - .05, y0 - .05, x1, y1 + .05, LEAN_TOP + .16, mat=PLANK, t=.04)   # timber decking
    roof = LEAN_TOP + .16
    parapet_ring(g, x0 - .05, y0 - .05, x1, y1 + .05, roof, height=.24, open_sides=('right',))
    # The forge flue rises from the ground in the workshop's left wall (no roof
    # stack), within the edge band so the roof deck beside it stays platformable.
    stack(g, x0 + .14, 6.3, -BURY, 3.5 + BURY, emits='smoke', r=.14, taper=.85, bands=3)



def track(g):
    sx = STAGE[0]
    for k in range(6):
        y = HY0 + .15 + k * .32
        bx(g, sx - .95, y - .07, .005, sx + .95, y + .07, .07, WOOD)
    for x in (sx - .6, sx + .6):
        bx(g, x - .04, HY0 + .05, .05, x + .04, BAY_BACK - .02, .13, IRON)


def build(g, parts):
    hall(g)
    bay(g)
    door_track(g)
    doors(g, parts)
    workshop(g, parts)
    track(g)
    cx = (HX0 + HX1) / 2
    zc = SPRING + RISE
    for k, y in enumerate((HY0 + .45, HY1 - .45)):
        bx(g, cx - .07, y - .07, zc - .06, cx + .07, y + .07, zc + .2, IRON)
        pivot = beacon(g, cx, y, zc + .2)
        parts.append((beacon_shutter(*pivot, 'RocketAssemblyHangar.Beacon%d' % k), 'SPIN_Z', 2 + k))
