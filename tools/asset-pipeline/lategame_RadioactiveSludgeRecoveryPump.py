"""RadioactiveSludgeRecoveryPump: pumps world sludge back into barrels
(docs/radiation.md: native intake pipe, 0.2 units per 0.5 h cycle).

Compacted 2026-10-30 (light touch, outputs/compaction/BRIEF.md): 3x3x5 ->
3x3x3. One layer per floor: a concrete ground storey (layer 0, the door and
the pipe outlet) and one forged storey (layer 1) under its plank gable, a
layer lower; the roof ventilator cowl is gone (roof variety: real roof, no
roof vents). Footprint, door, pipe outlet, intake cell and the pool deck are
unchanged.

HERO: a hazard-banded steel pump house whose vertical pump on a pool-side
deck drops a strainer intake pipe down into the pool.
ROOF: teal native plank gable (ridge front to back), no ventilator.

Plan (3 x 3 tiles): concrete plinth with the builders' door and the Timber
Pipes outlet on the front; the forged pump house on it; the steel deck
cantilevered over the water along the back row, carrying the vertical pump
and the intake pipe (INTAKE: the game's native intake segments continue
below the strainer). Only the intake cell is a building block in the back
row, so any straight bank fits (revised 2026-10-24; the piers needed a
one-cell water notch).

Accents: no yellow or yellow-green native material exists (brass renders
grey), so the hazmat bands, trefoil disc and pump ring use native orange
plaster, sparingly; the house body stays forged steel.

Animated: pump coupling (SPIN_Z), delivery-valve handwheel (SPIN_X).
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
from native_window_atlas import atlas_window
from lategame_roofdeck_parts import parapet_ring
import lategame_mining_parts as M

IDENT = 'RadioactiveSludgeRecoveryPump'
FOOTPRINT = (3, 3)
HEIGHT = 3
FRAME_END = 121
HERO = 'Hazard-banded steel pump house whose vertical pump on a pool-side deck drops a strainer intake into the pool.'

PIPE_OUTLET = {'cell': [2, 0, 0], 'direction': 'Down', 'state': 'OpenOut', 'good': 'RadioactiveSludge',
               'socket': [2.5, .06, .55]}
# Native WaterInputPipe intake column (strainer top at pipeTop; segments continue down).
INTAKE = {'cell': [1, 2, 0], 'pipeTop': [1.5, 2.5, .35]}

DOOR_X = 1.5
PUMP = (1.5, 2.5)
DECK_Z = 1


def rad_sign(g, x, y, z, face='front', r=.18):
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


def house(g, parts):
    x0, y0, x1, y1 = 0.0, .15, 3.0, 2.0
    M.plinth_course(g, x0 + .05, x1 - .05, y0 + .12, y1 - .05, 0, 1.0, CONCRETE, [DOOR_X])
    M.portal(g, DOOR_X, y0 + .12, 0, ident='Door0')
    top = 1.0
    K.lamp(g, DOOR_X - .62, y0 + .07, .75, face='front')
    sx, sy, sz = PIPE_OUTLET['socket']
    blk(g, sx - .25, sy + .03, sz - .25, sx + .25, y0 + .09, sz + .2, PAINTED)
    g.cylinder((sx, sy + .02, sz), .15, .08, IRON, 'Y', 16)
    P.hoop(g, (sx, sy - .03, sz), .2, .05, .04, BRASS, axis='Y', segments=16)
    K.bolt_row(g, (sx - .16, sy - .06, sz + .14), (sx + .16, sy - .06, sz + .14), 3, r=.016)
    bx0, by0, bx1, by1 = x0 + .1, y0 + .1, x1 - .1, y1 - .1
    eave = 1.84
    C.framed_block(g, bx0, by0, bx1, by1, top + .012, eave, infill=FORGED, frame=IRON, pitch=.93, sink=.03,
                   windows={'left': [(1.29, 1.42, .45, 'factory')], 'right': [(1.29, 1.42, .45, 'factory'), (.62, 1.42, .45, 'factory')]})
    # Hazmat bands: brass and dark blocks wrapped round the front and sides.
    def band_x(y, out):
        n = 13
        w = (bx1 - bx0 - .24) / n
        for i in range(n):
            a = bx0 + .12 + i * w
            d0, d1 = (y - .085, y - .055) if out < 0 else (y + .055, y + .085)
            if i % 2 == 0:
                blk(g, a, d0, 1.06, a + w, d1, 1.16, ORANGE)
            else:
                blk(g, a + .002, d0 + .006, 1.066, a + w - .002, d1 - .006, 1.154, IRON)
    band_x(by0, -1)
    rad_sign(g, .62, by0 - .055, 1.48, 'front', .16)
    rad_sign(g, bx0 - .055, .62, 1.48, 'left', .16)
    atlas_window(g, 2.25, by0, 1.48, .2, 'front', 'slit')
    ridge = P.plank_roof(g, bx0, by0, bx1, by1, eave, eave + .7, ridge_axis='Y', overhang=.16, plank=.28)


def deck(g, parts):
    # Cantilevered from the plinth on steel joists, with nothing standing in
    # the back row: only the intake cell is a building block there, so the
    # pump sits on any straight bank with the whole back row over the water
    # (as the vanilla DeepBadwaterPump). Joists stay above the 0.15 inset of
    # the ground layer so they claim no ground cell.
    x0, x1, y0, y1 = .3, 2.7, 2.05, 2.95
    for x in (x0 + .25, 1.5 - .32, 1.5 + .32, x1 - .25):
        blk(g, x - .04, 1.88, DECK_Z - .14, x + .04, y1 - .03, DECK_Z - .08, IRON)
    blk(g, x0 + .02, y1 - .1, DECK_Z - .145, x1 - .02, y1 - .02, DECK_Z - .081, IRON)   # edge beam (joist ends buried)
    P.grating(g, x0, y0, x1, y1, DECK_Z)
    P.rail(g, [(x0 + .04, y0 + .04), (x0 + .04, y1 - .04), (x1 - .04, y1 - .04), (x1 - .04, y0 + .04)], DECK_Z)
    px, py = PUMP
    # Vertical pump: casing, brass ring, coupling, motor.
    P.lathe(g, (px, py, DECK_Z), [(.26, 0), (.26, .06), (.21, .1), (.21, .4), (.15, .48)], PAINTED, segments=16)
    K.band(g, (px, py, 0), .21, DECK_Z + .25, .08, ORANGE, segments=16, proud=.03)
    c = Geometry('RadioactiveSludgeRecoveryPump.Coupling', (px, py, DECK_Z + .56))
    P.lathe(c, (px, py, DECK_Z + .56), [(.1, -.08), (.1, .08)], IRON, segments=12)
    for k in range(4):
        a = k * math.pi / 2
        c.box((px + math.cos(a) * .1, py + math.sin(a) * .1, DECK_Z + .56), (.04, .04, .14), BRASS)
    parts.append((c, 'SPIN_Z', 3))
    g.cylinder((px, py, DECK_Z + .56), .04, .2, IRON, 'Z', 8)
    P.motor(g, (px, py, DECK_Z + .87), .17, .38, axis='Z')
    # Intake pipe down to the strainer bell in the pool.
    P.pipe(g, [(px, py, DECK_Z + .02), (px, py, .35)], .08, flanges=False)
    P.hoop(g, (px, py, .7), .13, .05, .05, BRASS, segments=12)
    P.lathe(g, (px, py, .02), [(.2, 0), (.2, .12), (.1, .3)], IRON, segments=14)
    for k in range(8):
        a = k * math.pi / 4
        g.box((px + math.cos(a) * .19, py + math.sin(a) * .19, .08), (.03, .03, .09), IRON)
    # Delivery line from the casing into the house.
    P.pipe(g, [(px, py - .2, DECK_Z + .3), (px, 1.89, DECK_Z + .3)], .06, flanges=False)
    g.cylinder((px + .1, 2.15, DECK_Z + .3), .04, .12, IRON, 'X', 8)
    v = Geometry('RadioactiveSludgeRecoveryPump.ValveWheel', (px + .19, 2.15, DECK_Z + .3))
    K.wheel(v, (px + .19, 2.15, DECK_Z + .3), .11, 'X')
    parts.append((v, 'SPIN_X', 1))


def build(g, parts):
    house(g, parts)
    deck(g, parts)
