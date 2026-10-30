"""SmogScrubber: compact powered air scrubber (200 hp, no workers).

Compacted 2026-10-30 (light touch, outputs/compaction/BRIEF.md): 3x3x6 ->
3x3x5. The ring catwalk and its ladder are gone; the plinth is one layer
(it was 1.2) and the plenum, column and cowl stand a layer lower; the plank
lean-to over the front filter cartridges is a flat steel cap. Footprint,
door, emitter and animated parts unchanged.

HERO: a riveted steel wet-scrubber column on a louvred intake plenum, crowned
by a wide open fan cowl that breathes out clean vapour.
ROOF: open fan cowl; flat steel cap over the filter cartridges.

Plan (3 x 3 tiles): cast-concrete plinth with the builders' door on the
front; square steel intake plenum with louvres on all four faces; round
scrubber column; the fan
cowl on top; filter-cartridge racks along the front and the west side; a
recirculation pump at the west.

Animated: cowl fan (SPIN_Z), recirculation pump coupling (SPIN_X).
Emitter: broad vapour plume (towerSteam) at the cowl mouth; never smoke.
Power: the plinth's west and back faces lie on the tile edges, so shafts
connect there; the door is for builders only.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN, LAYER_GAP
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
from lategame_mining_parts import lean_to
from industrial_facades import building_portal
import lategame_mining_parts as M

IDENT = 'SmogScrubber'
FOOTPRINT = (3, 3)
HEIGHT = 5
FRAME_END = 121
HERO = 'Riveted steel wet-scrubber column on a louvred intake plenum, crowned by a wide open fan cowl.'

DOOR_X = 1.5
CX, CY = 1.5, 1.7
PLINTH_TOP = 1.0
PLENUM = (.55, .75, 2.45, 2.65)
PLENUM_TOP = 2.0
COL_R = .78
COL_TOP = 3.9
COWL_R = 1.02
COWL_TOP = 4.72


def plinth(g):
    M.plinth_course(g, .05, 2.95, .27, 2.95, 0, PLINTH_TOP, CONCRETE, [DOOR_X])
    M.portal(g, DOOR_X, .27, 0, ident='Entrance')
    K.lamp(g, DOOR_X + .62, .22, .75, face='front')
    return PLINTH_TOP + .012


def plenum(g, top):
    x0, y0, x1, y1 = PLENUM
    blk(g, x0, y0, top - .02, x1, y1, PLENUM_TOP, FORGED)
    for x in (x0, x1):
        for y in (y0, y1):
            blk(g, x - .06, y - .06, top, x + .06, y + .06, PLENUM_TOP + .04, IRON)
    zl, zh = top + .25, PLENUM_TOP - .15
    P.louvre(g, 'X', y0, x0 + .15, x1 - .15, zl, zh, -1)
    P.louvre(g, 'X', y1, x0 + .15, x1 - .15, zl, zh, 1)
    P.louvre(g, 'Y', x0, y0 + .15, y1 - .15, zl, zh, -1)
    P.louvre(g, 'Y', x1, y0 + .15, y1 - .15, zl, zh, 1)
    blk(g, x0 - .05, y0 - .05, PLENUM_TOP + .04, x1 + .05, y1 + .05, PLENUM_TOP + .12, IRON)


def column(g, parts):
    z0 = PLENUM_TOP + .1
    K.revolve(g, (CX, CY, z0), [(COL_R, 0), (COL_R, COL_TOP - z0)], IRON, segments=16)
    for z in (2.45, 3.0, 3.55):
        K.band(g, (CX, CY, 0), COL_R, z, .08, PAINTED, segments=16)
    for i in range(8):
        a = i * math.pi / 4 + math.pi / 8
        K.bolt_row(g, (CX + math.cos(a) * (COL_R + .01), CY + math.sin(a) * (COL_R + .01), z0 + .1),
                   (CX + math.cos(a) * (COL_R + .01), CY + math.sin(a) * (COL_R + .01), COL_TOP - .1), 6, axis='X',
                   r=.018)
    # Inspection hatch and spray-header inlet on the front.
    P.tube(g, (CX, CY - COL_R + .05, 2.75), (CX, CY - COL_R - .05, 2.75), .2, IRON, segments=16)
    P.pipe(g, [(.28, .83, PLINTH_TOP + .42), (.28, .83, 3.75), (CX - .45, CY - COL_R + .2, 3.75)], .05,
           flanges=False)
    # Fan cowl: transition, open drum, guard bars, and the fan.
    K.revolve(g, (CX, CY, COL_TOP - .02), [(COL_R, 0), (COWL_R - .02, .22)], IRON, segments=16)
    cz = COL_TOP + .15
    K.hollow_revolve(g, (CX, CY, cz), [(COWL_R, 0), (COWL_R + .03, COWL_TOP - cz)], .07, PAINTED, segments=16,
                     inner_mat=IRON)
    for z in (cz + .12, COWL_TOP - .1):
        P.hoop(g, (CX, CY, z), COWL_R + .015 * (z - cz) / (COWL_TOP - cz) + .03, .06, .06, IRON, segments=16)
    g.cylinder((CX, CY, COL_TOP + .32), .16, .2, IRON, 'Z', 12)
    for a in (0, math.pi / 2):
        d = (math.cos(a), math.sin(a))
        g.beam((CX - d[0] * (COWL_R - .03), CY - d[1] * (COWL_R - .03), COWL_TOP - .06),
               (CX + d[0] * (COWL_R - .03), CY + d[1] * (COWL_R - .03), COWL_TOP - .06), .04, mat=IRON)
    fan = P.fan('SmogScrubber.Fan', CX, CY, COL_TOP + .5, .88, blades=6, pitch=.5, mat=FORGED)
    parts.append((fan, 'SPIN_Z', 3))
    K.emitter(g, 'towerSteam', CX, CY, COWL_TOP, COWL_R - .07)


def cartridges(g, parts, top):
    # Front rack: four upright cartridges in a steel frame under a lean-to.
    x0, x1, y0, y1 = .45, 2.55, .28, .66
    for x in (x0 + .045, x1 - .045):
        for y in (y0 + .045, y1 - .045):
            blk(g, x - .03, y - .03, top, x + .03, y + .03, 1.9, IRON)
    blk(g, x0, y0, top + .02, x1, y1, top + .08, IRON)
    blk(g, x0, y0, 1.7, x1, y1, 1.76, IRON)
    for x in (.7, 1.1, 1.9, 2.3):
        g.cylinder((x, (y0 + y1) / 2, (top + .08 + 1.7) / 2), .12, 1.7 - top - .08, PAINTED, 'Z', 12)
        g.cylinder((x, (y0 + y1) / 2, 1.7 - .1), .135, .06, BRASS, 'Z', 12)
    blk(g, x0 - .06, y0 - .06, 1.9, x1 + .06, y1 + .06, 1.96, IRON)
    # West rack and the recirculation pump.
    for y in (1.75, 2.15, 2.55):
        g.cylinder((.28, y, (top + .06 + 1.7) / 2), .11, 1.7 - top - .06, PAINTED, 'Z', 12)
    blk(g, .12, 1.5, top, .44, 2.8, top + .06, IRON)
    blk(g, .12, 1.5, 1.7, .44, 2.8, 1.76, IRON)
    for y in (1.55, 2.75):
        blk(g, .25, y - .03, top, .31, y + .03, 1.75, IRON)
    px, py = .28, 1.05
    blk(g, px - .18, py - .25, top, px + .18, py + .25, top + .1, IRON)
    P.motor(g, (px, py + .1, top + .3), .14, .3, axis='Y')
    g.cylinder((px, py - .22, top + .3), .13, .16, PAINTED, 'Y', 12)
    c = Geometry('SmogScrubber.PumpCoupling', (px, py - .08, top + .3))
    P.lathe(c, (px, py - .08, top + .3), [(.08, -.06), (.08, .06)], BRASS, axis='Y', segments=10)
    for k in range(4):
        a = k * math.pi / 2
        c.box((px + math.cos(a) * .08, py - .08, top + .3 + math.sin(a) * .08), (.03, .1, .03), IRON)
    parts.append((c, 'SPIN_Y', 3))


def build(g, parts):
    top = plinth(g)
    plenum(g, top)
    column(g, parts)
    cartridges(g, parts, top)
