"""RadioactiveSludgeOutfall: releases radioactive sludge into the world
(docs/radiation.md: 0.6 units per cycle at its output cell).

HERO: a stepped concrete spillway with a lifting sluice gate, running from a
small steel valve house down to a cantilevered, hazard-striped lip.
ROOF: teal plank mono-pitch on the concrete valve house.

Plan (4 x 3 tiles): valve house on the left with the builders' door and the
Timber Pipes inlet on the front; the sluice chamber and spillway on the
right, running toward the back edge; the lip overhangs the last cell, which
is where the sludge leaves (SLUDGE_OUTPUT).

Accents: no yellow-green native material exists (brass renders grey), so the
hazard band and trefoil use native orange plaster, as on the nuclear chain.

Animated: sluice gate (SLIDE_Z), gate handwheel (SPIN_Y).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN, LAYER_GAP
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
from lategame_nuclear_parts import Facer, prism
from industrial_facades import building_portal
from lategame_mining_parts import lean_to
from native_window_atlas import atlas_window

IDENT = 'RadioactiveSludgeOutfall'
FOOTPRINT = (4, 3)
HEIGHT = 4
FRAME_END = 121
HERO = 'Stepped concrete spillway with a lifting sluice gate, from a steel valve house to a striped cantilevered lip.'

PIPE_INLET = {'cell': [0, 0, 0], 'direction': 'Down', 'state': 'OpenIn', 'good': 'RadioactiveSludge',
              'socket': [.5, .06, .55]}
# Sludge leaves over the lip into this cell (RadioactiveSludgeOutfallSpec.OutputCoordinates).
SLUDGE_OUTPUT = {'cell': [3, 2, 0], 'lip': [3.25, 3.0, .3]}

DOOR_X = 1.5
CH = (2.65, 3.85)              # channel inner faces (x)
HEAD = (0.0, 1.0)               # sluice chamber (y)
SLOPE = ((1.0, .97), (2.4, .42))
LIP = (2.4, 3.0, .3, .42)


def floor_z(y):
    (y0, z0), (y1, z1) = SLOPE
    return z0 + (z1 - z0) * (y - y0) / (y1 - y0)


def rad_sign(g, x, y, z, face='front', r=.2):
    f = Facer(x, y, z, face)
    s = 2 * r + .1
    f.box(g, 0, 0, .02, s, s, .04, IRON)
    segs = 12
    prism(g, f, [(math.cos(i * 2 * math.pi / segs) * r, math.sin(i * 2 * math.pi / segs) * r)
                 for i in range(segs)], .03, .06, ORANGE)
    ri, ro = r * .26, r * .86
    for k in range(3):
        a0 = math.pi / 2 + k * 2 * math.pi / 3 - math.pi / 6
        a1 = a0 + math.pi / 3
        outer = [(math.cos(a0 + (a1 - a0) * i / 5) * ro, math.sin(a0 + (a1 - a0) * i / 5) * ro) for i in range(6)]
        inner = [(math.cos(a1 - (a1 - a0) * i / 5) * ri, math.sin(a1 - (a1 - a0) * i / 5) * ri) for i in range(6)]
        prism(g, f, outer + inner, .05, .075, IRON)


def valve_house(g, parts):
    x0, y0, x1, y1 = 0.0, .15, 2.5, 2.0
    top = P.plinth(g, x0, y0, x1, y1, 1.2, door=(DOOR_X, 1.0, 1.0))
    building_portal(g, DOOR_X, y0 - .12, 0)
    g.doorways.append({'id': 'Door0', 'position': [DOOR_X, y0, 0], 'outward': [0, -1]})
    K.lamp(g, DOOR_X + .62, y0 - .04, 1.05, face='front')
    # Inlet socket on the plinth front.
    sx, sy, sz = PIPE_INLET['socket']
    blk(g, sx - .25, sy + .03, sz - .25, sx + .25, y0 + .02, sz + .2, PAINTED)
    g.cylinder((sx, sy + .02, sz), .15, .08, IRON, 'Y', 16)
    P.hoop(g, (sx, sy - .03, sz), .2, .05, .04, BRASS, axis='Y', segments=16)
    K.bolt_row(g, (sx - .16, sy - .06, sz + .14), (sx + .16, sy - .06, sz + .14), 3, r=.016)
    bx0, by0, bx1, by1 = x0 + .1, y0 + .1, x1 - .1, y1 - .1
    eave = 2.75
    C.framed_block(g, bx0, by0, bx1, by1, top + .02, eave, infill=CONCRETE, frame=IRON, pitch=.95, sink=.03,
                   windows={'front': [(.6, 2.0, .75, 'factory')], 'left': [(1.47, 2.0, .75, 'factory')]})
    rad_sign(g, 1.7, by0 - .055, 2.05, 'front', .2)
    # Mono-pitch roof falling toward the back, closed at both ends.
    high = eave + .6
    lean_to(g, bx0, bx1, by0, by1, eave, high, low_side='back', overhang=.12, seed=5)
    tri = [(by0 + .1, eave - .01), (by1, eave - .01), (by0 + .1, high - .02 - .1 * .6 / (by1 - by0))]
    K.extrude_profile(g, tri, bx0 + .01, bx0 + .09, CONCRETE, axis='X')
    K.extrude_profile(g, tri, bx1 - .09, bx1 - .01, CONCRETE, axis='X')
    blk(g, bx0, by0, eave - .01, bx1, by0 + .1, high - .02, CONCRETE)
    atlas_window(g, (bx0 + bx1) / 2, by0, (eave + high) / 2 - .02, .9, 'front', 'ribbon', reveal=IRON)
    # The delivery main runs through the shared wall into the sluice chamber.


def spillway(g, parts):
    xa, xb = CH
    # Sluice chamber at the head.
    blk(g, xa - .15, HEAD[0], 0, xb + .15, HEAD[1], 1.3, CONCRETE)
    blk(g, xa - .18, HEAD[0] - .03, 1.3, xb + .18, HEAD[1] + .03, 1.36, IRON)
    # Sloped channel floor and its side walls, then the cantilevered lip.
    (y0, z0), (y1, z1) = SLOPE
    K.extrude_profile(g, [(y0 - .01, 0), (y1, 0), (y1, z1), (y0 - .01, z0)], xa, xb, CONCRETE, axis='X')
    for wa, wb in ((xa - .15, xa), (xb, xb + .15)):
        K.extrude_profile(g, [(y0 - .01, 0), (y1, 0), (y1, z1 + .4), (y0 - .01, z0 + .4)], wa, wb, CONCRETE,
                          axis='X')
    ly0, ly1, lz0, lz1 = LIP
    blk(g, xa - .15, ly0, lz0, xb + .15, ly1 - .02, lz1, CONCRETE)
    for x in (xa - .1, xb + .1):
        blk(g, x - .05, ly0, lz1, x + .05, ly1 - .06, lz1 + .22, CONCRETE)
    # Hazard band on the lip edge, under-lip corbels.
    w = (xb + .15 - (xa - .15)) / 8
    for i in range(8):
        a = xa - .15 + i * w
        if i % 2 == 0:
            blk(g, a, ly1 - .02, lz0 + .02, a + w, ly1, lz1 - .02, ORANGE)
        else:
            blk(g, a + .002, ly1 - .016, lz0 + .03, a + w - .002, ly1 - .004, lz1 - .03, IRON)
    for x in (xa + .1, xb - .1):
        g.beam((x, ly0 - .1, .02), (x, ly0 + .35, lz0 + .01), .1, mat=CONCRETE)
    # Baffle steps on the chute.
    for y in (1.45, 1.85, 2.2):
        z = floor_z(y)
        blk(g, xa + .02, y - .06, z - .08, xb - .02, y + .06, z + .1, CONCRETE)
    # Sluice gate in guide channels at the chamber's back face, handwheel in front.
    gy = HEAD[1]
    for x in (xa - .04, xb + .04):
        blk(g, x - .05, gy, .9, x + .05, gy + .08, 2.0, IRON)
    blk(g, xa - .1, gy, 2.0, xb + .1, gy + .08, 2.1, IRON)
    g.cylinder(((xa + xb) / 2, gy + .04, 2.25), .03, .3, IRON, 'Z', 8)
    gate = Geometry('RadioactiveSludgeOutfall.SluiceGate', ((xa + xb) / 2, gy + .04, 1.15))
    blk(gate, xa + .02, gy + .015, .95, xb - .02, gy + .065, 1.42, FORGED)
    for z in (1.05, 1.32):
        blk(gate, xa + .04, gy + .065, z - .03, xb - .04, gy + .085, z + .03, IRON)
    blk(gate, (xa + xb) / 2 - .03, gy + .02, 1.42, (xa + xb) / 2 + .03, gy + .06, 1.9, IRON)
    parts.append((gate, 'SLIDE_Z', .35))
    # Gate handwheel on a pedestal on the chamber roof.
    wx, wy, wz = (xa + xb) / 2, .45, 1.72
    blk(g, wx - .08, wy - .08, 1.36, wx + .08, wy + .08, wz + .05, IRON)
    g.cylinder((wx, wy - .1, wz), .04, .2, IRON, 'Y', 8)
    wheel = Geometry('RadioactiveSludgeOutfall.Handwheel', (wx, wy - .2, wz))
    wheel.wheel((wx, wy - .2, wz), .2, 'Y', IRON, BRASS)
    parts.append((wheel, 'SPIN_Y', 1))


def build(g, parts):
    valve_house(g, parts)
    spillway(g, parts)
