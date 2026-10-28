"""Rocket Assembly Hangar: the vertical assembly hall of the space program.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the east parts yard with its bridge crane and stacked parts, the track
apron and transporter in front, and the projecting hoist hood; the door track
stops at the east wall.

Hero: a cathedral-scale, barrel-vaulted assembly hall whose giant riveted
sliding doors stand partly open on a dark bay holding a rocket stage, with
a timber hoist hood projecting from the vault's orange lunette.
Roof types: teal barrel vault with steel ribs and a ridge walkway; a teal
mono-pitch lean-to over the orange-plaster workshop; open crane yard.

Parts: a concrete-based steel-framed hall (forged infill, clerestory
windows); two 9-layer sliding door leaves on an overhead track; the open
bay with work platforms around an upright stage; a rail track and a stage
transporter carrying an engine section out front; the workshop lean-to with
roof ventilators and a stack; a parts yard with an overhead bridge crane
over stacked tank rings, fin sets and engine bells.

Animated: right door leaf (slide X), bridge crane bridge, trolley and hook
(synchronised paths), two roof ventilator rotors, two vault beacons, hoist
pulley.
"""
import math

from lategame_kit import *
from frontier_architecture import Geometry
from architectural_windows import window
from native_building_assets import barrel
from lategame_space_parts import (bx, door_block, pilasters, coping_ring, gauge, ball, pipe, h_tank,
                                  grating_ring, timber_hut, rail, lattice, BURY, animate)

IDENT = 'RocketAssemblyHangar'
# Footprint ends at the walls: hall front y = 3, workshop lean-to west,
# hall east wall x = 8. The east crane yard with its stacked parts and the
# track apron and flatcar in front were removed. GRID_ORIGIN is the
# footprint's (0, 0) corner in the artwork coordinates used below.
FOOTPRINT = (8, 9)
GRID_ORIGIN = (0, 3)
HEIGHT = 14
FRAME_END = 121
HERO = 'Cathedral-scale barrel-vaulted assembly hall with giant sliding doors ajar on a rocket stage'

HX0, HX1 = 2.0, 7.88         # hall walls (right base course .12 proud, on x = 8)
HY0, HY1 = 3.0, 11.88        # front on y = 3; back base course on the footprint edge
SPRING, RISE = 11.0, 1.85
BASE = 3.0                    # concrete lower storey of the hall
TIER = 7.0                    # forged middle tier below, orange plaster upper tier above
BAY = (4.9, 7.4)              # open assembly bay behind the doors
BAY_TOP = 9.4
BAY_BACK = 5.1
STAGE = (6.15, 4.05)
LEAN = (0.0, 3.0, HX0, 11.0)  # workshop lean-to on tiles 0..2 x 3..11
LEAN_LO, LEAN_HI = 2.95, 4.15
YARD = (8.0, 0.0, 12.0, 12.0)   # whole tiles to the footprint edges
CRANE_Z = 5.0


def hall(g):
    bx0, bx1 = BAY
    # Dark steel core, split around the open bay (its faces line the bay).
    bx(g, HX0, HY0, 0, bx0, HY1, SPRING - .03, IRON)
    bx(g, bx1, HY0, 0, HX1, HY1, SPRING - .03, IRON)
    bx(g, bx0, HY0, BAY_TOP, bx1, HY1, SPRING - .03, IRON)
    bx(g, bx0, BAY_BACK, 0, bx1, HY1, BAY_TOP, IRON)
    # Concrete base course on the exposed sides and back.
    bx(g, HX1, HY0 + .3, -BURY, HX1 + .12, HY1 + .12, BASE, CONCRETE)
    bx(g, HX0 - .12, HY1, -BURY, HX1, HY1 + .12, BASE, CONCRETE)
    bx(g, HX1 - .02, HY0 + .3, BASE - .06, HX1 + .17, HY1 + .17, BASE + .08, CONCRETE)
    bx(g, HX0 - .17, HY1 - .02, BASE - .06, HX1 - .02, HY1 + .17, BASE + .08, CONCRETE)
    # Concrete storey: pilasters and native factory windows.
    ys = [HY0 + .3 + (HY1 - HY0 - .3) * (k + .5) / 6 for k in range(6)]
    xs = [HX0 + .75 + 1.5 * k for k in range(4)]
    pilasters(g, 'Y', HX1 + .12, HY0 + .3, HY1 + .12, .1, BASE - .1, 1, pitch=1.45, w=.16)
    pilasters(g, 'X', HY1 + .12, HX0 - .12, HX1 + .12, .1, BASE - .1, 1, pitch=1.5, w=.16)
    for y in ys:
        window(g, HX1 + .12, y, 1.75, .85, 'right', 'factory')
    for x in xs:
        window(g, x, HY1 + .12, 1.75, .85, 'back', 'factory')
    # Steel-framed walls: riveted forged tier, orange plaster upper tier.
    for lo, hi, infill, zs in ((BASE + .06, TIER, FORGED, (5.0,)), (TIER, SPRING, ORANGE, (8.0, 9.9))):
        frame_wall(g, 'Y', HX1, HY0 + .3, HY1, lo, hi, outward=1, infill=infill, bays=6,
                   windows=[(y, z) for y in ys for z in zs], window_scale=.9)
        frame_wall(g, 'X', HY1, HX0 + .055, HX1 - .055, lo, hi, outward=1, infill=infill, bays=4,
                   windows=[(x, z) for x in xs for z in zs], window_scale=.9)
    frame_wall(g, 'Y', HX0, HY0 + .3, HY1, LEAN_HI - .1, TIER, outward=-1, infill=FORGED, bays=6,
               windows=[(y, 5.4) for y in ys], window_scale=.9)
    frame_wall(g, 'Y', HX0, HY0 + .3, HY1, TIER, SPRING, outward=-1, infill=ORANGE, bays=6,
               windows=[(y, z) for y in ys for z in (8.0, 9.9)], window_scale=.9)
    # Barrel vault with ribs, closed by orange lunettes.
    barrel_roof(g, HX0, HY0, HX1, HY1, SPRING, RISE, axis='Y', segments=14, ribs=5, overhang=.14)
    half = (HX1 - HX0) / 2
    cx = (HX0 + HX1) / 2
    for y, out in ((HY0, -1), (HY1, 1)):
        arch_infill(g, 'Y', y, cx, half + .08, SPRING, RISE - .04, out, ORANGE, segments=14)
    # Lunette windows and timber mullion posts on the orange ends.
    window(g, cx - 1.35, HY1, SPRING + .7, .8, 'back', 'grand')
    window(g, cx + 1.35, HY1, SPRING + .7, .8, 'back', 'grand')
    window(g, cx - 1.6, HY0, SPRING + .62, .75, 'front', 'grand')
    for y, s in ((HY0, -1), (HY1, 1)):
        for x in (cx - 2.4, cx + 2.4):
            bx(g, x - .06, y + s * .0 - (.07 if s < 0 else 0), SPRING - .02, x + .06,
               y + (.07 if s > 0 else 0), SPRING + .75, WOOD)
    # Corner columns of the hall (proud steel), front left pier.
    for x, y in ((HX1, HY1), (HX0, HY1)):
        bx(g, x - .15, y - .15, .01, x + .15, y + .15, SPRING - .05, IRON)
    bx(g, HX0 - .1, HY0 - .12, .01, HX0 + .45, HY0 + .3, SPRING - .05, IRON)
    bx(g, HX1 - .1, HY0 - .12, BASE, HX1 + .15, HY0 + .3, SPRING - .05, IRON)
    bx(g, HX1 - .1, HY0 - .12, .01, HX1 + .15, HY0 + .3, BASE, CONCRETE)
    # Concrete facing where the hall's flank shows behind the lean-to (the
    # lean-to front is now flush with the hall front).
    bx(g, HX0 - .12, LEAN[3], -BURY, HX0, HY1 - .15, LEAN_HI - .14, CONCRETE)
    # Door header: riveted girder carrying the overhead track.
    bx(g, HX0 - .08, HY0 - .14, BAY_TOP + .25, HX1 + .1, HY0 + .05, SPRING - .06, FORGED)
    bx(g, HX0 - .12, HY0 - .18, SPRING - .2, HX1 + .12, HY0 + .05, SPRING, IRON)
    bolt_row(g, (HX0 + .1, HY0 - .19, SPRING - .11), (HX1 - .1, HY0 - .19, SPRING - .11), 22, axis='Y', r=.02)
    gauge(g, 4.4, HY0 - .14, BAY_TOP + .75, 'front', .12)


def bay(g):
    """Dark open bay: work platforms around an upright stage under assembly."""
    bx0, bx1 = BAY
    sx, sy = STAGE
    # Floor slab and the stage dolly on the track.
    bx(g, bx0, HY0, -BURY, bx1, BAY_BACK, .04, CONCRETE)
    bx(g, sx - .95, sy - .9, .04, sx + .95, sy + .9, .4, PAINTED)
    for x in (sx - .75, sx + .75):
        for y in (sy - .6, sy + .6):
            g.cylinder((x, y - .0, .2), .17, .12, IRON, 'X', 12)
    # Upright stage: banded teal and steel courses with a lifting yoke on top.
    z = .4
    for mat, h in ((IRON, .5), (PAINTED, 1.6), (CONCRETE, .5), (PAINTED, 1.8), (CONCRETE, .45), (PAINTED, 1.6), (IRON, .4)):
        revolve(g, (sx, sy, z), [(.8, 0), (.8, h)], mat, segments=16, cap_bottom=z == .4)
        z += h
    for zz in (.9, 2.5, 3.0, 4.8, 5.25, 6.85):
        band(g, (sx, sy, 0), .8, zz, .08, BRASS, segments=16, proud=.025)
    revolve(g, (sx, sy, z), [(.8, 0), (.66, .25), (.66, .3)], IRON, segments=16, cap_bottom=False)
    top = z + .3
    bx(g, sx - .75, sy - .08, top - .02, sx + .75, sy + .08, top + .14, BRASS)
    for x, dy in ((sx - .6, -.04), (sx + .6, .04)):
        g.beam((x, sy + dy, top + .12), (sx, sy + dy, top + .8), .06, mat=IRON)
    g.ring((sx, sy, top + .9), .12, .04, .06, IRON, 'Y', 12)
    g.beam((sx, sy, top + .96), (sx, sy, BAY_TOP - .01), .03, mat=IRON)
    # Work platforms bracketed off the bay side walls.
    for zp in (3, 6):
        for xa, xb in ((bx0, sx - .85), (sx + .85, bx1)):
            bx(g, xa, HY0 + .2, zp - .08, xb, BAY_BACK, zp, IRON)
            rail(g, ((xa + .05) if xa == bx0 else xa + .04, HY0 + .24), ((xb - .04) if xb != bx1 else xb - .05, HY0 + .24),
                 zp, pitch=.45)
            wall_x = xa if xa == bx0 else xb
            g.beam((wall_x, HY0 + .5, zp - .7), ((xa + xb) / 2, HY0 + .5, zp - .09), .06, mat=IRON)
    # Bay lamp.
    lamp(g, sx, BAY_BACK, 8.4, face='front')
    for z in (2.2, 5.2, 8.2):
        lamp(g, bx1, HY0 + .6, z, face='left')
        lamp(g, bx0, HY0 + .9, z, face='right')


def door_track(g):
    # Enclosed overhead door track on brackets across the hall front (it
    # stops at the east wall). Authored at the first layout; build() sets the
    # whole door assembly 0.2 closer to the hall so it stays within 0.3 of
    # the footprint edge.
    bx(g, HX0 + .2, 2.54, BAY_TOP + .1, HX1 + .05, 2.7, BAY_TOP + .45, IRON)
    # (Set back against the hall front, the track needs no brackets.)
    bolt_row(g, (HX0 + .4, 2.53, BAY_TOP + .28), (HX1 - .2, 2.53, BAY_TOP + .28), 15, axis='Y', r=.018)
    # Floor rail for the door rollers.
    bx(g, HX0 + .2, 2.58, -.035, HX1 + .05, 2.7, .04, IRON)


def doors(g, parts):
    """Two riveted sliding leaves; the right one stands ajar and slides further."""
    def leaf(name, x0, x1):
        d = Geometry(name, ((x0 + x1) / 2, 2.8, BAY_TOP / 2))
        y0, y1 = 2.74, 2.86
        top = BAY_TOP + .05
        n = round((x1 - x0 - .12) / .33)
        for k in range(n):
            xa = x0 + .06 + (x1 - x0 - .12) * k / n
            xb = x0 + .06 + (x1 - x0 - .12) * (k + 1) / n
            bx(d, xa, y0 + .02, .1, xb, y1 - .02, top - .06, GREYPLANK)
        for x in (x0 + .07, (x0 + x1) / 2, x1 - .07):
            bx(d, x - .07, y0 - .01, .06, x + .07, y0 + .06, top, IRON)
        for z in (.15, 3.1, 6.2, top - .1):
            bx(d, x0 + .14, y0 - .03, z - .06, x1 - .14, y0 + .05, z + .06, IRON)
        # Diagonal braces in the lower panels.
        for (xa, xb) in ((x0 + .14, (x0 + x1) / 2 - .07), ((x0 + x1) / 2 + .07, x1 - .14)):
            d.beam((xa, y0 - .015, .22), (xb, y0 - .015, 3.0), .07, mat=IRON)
        # Band of native factory windows high on the leaf.
        # Two windows on a full leaf, one on the narrow right leaf.
        for x in (((x0 * 3 + x1) / 4 + .02, (x0 + 3 * x1) / 4 - .02) if x1 - x0 > 2 else ((x0 + x1) / 2,)):
            window(d, x, y0 + .02, 7.65, .85, 'front', 'factory')
        bolt_row(d, (x0 + .2, y0 - .02, 4.65), (x1 - .2, y0 - .02, 4.65), 8, axis='Y', r=.02)
        # Hangers rising into the enclosed track; floor guide rollers.
        for x in (x0 + .4, x1 - .4):
            bx(d, x - .05, 2.59, top - .03, x + .05, 2.65, BAY_TOP + .2, IRON)
            d.cylinder((x, 2.64, .11), .07, .1, IRON, 'Y', 10)
        # Pull handle.
        hx = x0 + .25 if name.endswith('Right') else x1 - .25
        bx(d, hx - .03, y0 - .1, 1.0, hx + .03, y0 - .04, 1.9, BRASS)
        return d
    left = leaf('RocketAssemblyHangar.DoorLeft', HX0 + .35, 5.05)
    parts.append((left, 'STATIC', 0))
    # The right leaf stands ajar inside the hall's width and slides toward
    # the bay (it no longer runs out past the east wall).
    right = leaf('RocketAssemblyHangar.DoorRight', 6.6, 7.85)
    parts.append((right, 'SLIDE_X', -.6))


def workshop(g, parts):
    x0, y0, x1, y1 = LEAN
    door_block(g, x0, y0, x1, y1, 0, 1.2, 1.5, CONCRETE, door_id='WorkshopDoor')
    bx(g, x0 - .05, y0 - .05, 1.12, x1, y1 + .05, 1.3, CONCRETE)
    prof = [(x0, 1.28), (x1, 1.28), (x1, LEAN_HI), (x0, LEAN_LO)]
    extrude_profile(g, prof, y0, y1, ORANGE, axis='Y')
    # Mono-pitch teal roof sheet with fascia.
    t = .08
    xe = x0 - .16
    slope = (LEAN_HI - LEAN_LO) / (x1 - x0)
    zlo = LEAN_LO - slope * .16
    extrude_profile(g, [(xe, zlo), (x1, LEAN_HI), (x1, LEAN_HI + t), (xe, zlo + t)], y0 - .16, y1 + .16, ROOF, axis='Y')
    bx(g, xe + .02, y0 - .16, zlo - .14, xe + .08, y1 + .16, zlo + .02, WOOD)
    # Timber framing on the plaster: posts, sill and plate.
    for y in [y0 + .02] + [y0 + 1.6 * k for k in range(1, 5)] + [y1 - .02]:
        bx(g, x0 - .05, y - .06, 1.3, x0 + .02, y + .06, LEAN_LO - .03, WOOD)
    bx(g, x0 - .06, y0 + .12, 1.32, x0 + .02, y1 - .12, 1.42, WOOD)
    bx(g, x0 - .06, y0 + .12, LEAN_LO - .22, x0 + .02, y1 - .12, LEAN_LO - .12, WOOD)
    for x in (x0 + .03, x1 - .35):
        top = LEAN_LO + (x - x0) * slope - .03
        bx(g, x - .06, y0 - .05, 1.3, x + .06, y0 + .02, top, WOOD)
    for k in range(5):
        y = y0 + .8 + 1.6 * k
        window(g, x0, y, 2.2, .62, 'left', 'grand')
    window(g, (x0 + x1) / 2 - .1, y0, 2.2, .55, 'front', 'grand')
    lamp(g, 1.0, y0, 1.55, face='front')
    # Roof ventilators (animated rotors) and a soot-capped stack.
    for k, y in enumerate((5.4, 8.4)):
        x = 1.05
        zr = LEAN_LO + (x - x0) * slope + t
        revolve(g, (x, y, zr - .12), [(.22, 0), (.22, .42), (.26, .46), (.26, .5)], IRON, segments=14)
        g.ring((x, y, zr + .2), .225, .03, .06, PAINTED, 'Z', 14)
        parts.append((fan('RocketAssemblyHangar.Vent%d' % k, x, y, zr + .43, .19, axis='Z', blades=5),
                      'SPIN_Z', 3 + k))
        bx(g, x - .2, y - .02, zr + .48, x + .2, y + .02, zr + .52, IRON)
    zr = LEAN_LO + (.75 - x0) * slope + t
    stack(g, .75, 10.2, zr - .15, 1.6, emits='smoke', r=.16)


def track_and_transporter(g):
    """Transporter track inside the open assembly bay (the track apron and
    flatcar in front of the doors were removed: the footprint ends at the
    hall front, y = HY0)."""
    sx = STAGE[0]
    for k in range(13):
        y = HY0 + .15 + k * .34
        if y > BAY_BACK - .1:
            break
        bx(g, sx - 1.05, y - .07, .005, sx + 1.05, y + .07, .07, WOOD)
    for x in (sx - .75, sx + .75):
        bx(g, x - .04, HY0 + .05, .05, x + .04, BAY_BACK - .02, .13, IRON)


def build(g, parts):
    hall(g)
    bay(g)
    with shifted(g, 0, .2):
        door_track(g)
        doors(g, parts)
    workshop(g, parts)
    track_and_transporter(g)
    # Ridge walkway along the vault crown with beacons at each end.
    cx = (HX0 + HX1) / 2
    zc = SPRING + RISE
    bx(g, cx - .35, HY0 + .3, 12.92, cx + .35, HY1 - .3, 13.0, IRON)
    for k in range(6):
        y = HY0 + .5 + k * (HY1 - HY0 - 1.0) / 5
        bx(g, cx - .05, y - .05, zc - .05, cx + .05, y + .05, 12.92, IRON)
    for x in (cx - .31, cx + .31):
        rail(g, (x, HY0 + .34), (x, HY1 - .34), 13.0, pitch=.9, height=.5)
    for k, y in enumerate((HY0 + .5, HY1 - .5)):
        bx(g, cx - .08, y - .08, 13.0, cx + .08, y + .08, 13.45, IRON)
        pivot = beacon(g, cx, y, 13.45)
        parts.append((beacon_shutter(*pivot, 'RocketAssemblyHangar.Beacon%d' % k), 'SPIN_Z', 2 + k))
