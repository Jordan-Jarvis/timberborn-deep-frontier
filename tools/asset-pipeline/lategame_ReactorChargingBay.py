"""ReactorChargingBay: charging station for Reactor Bots (super bots).

Native contract (tools/super_bot_content.mjs): a powered goods-consuming
attraction (vanilla DecontaminationPod / MudBath) serving only the
ReactorCharge need; 5,000 hp; burns enriched fuel while a bot charges; no
workers. Two bots charge at once, standing in the two open cradles.

HERO: a riveted steel reactor core between two open charging cradles, with a
banded fuel-rod cask and a cooling fan on its roof and coolant headers
dropping onto each cradle canopy.
ROOF: flat steel canopies over the cradles on outer steel posts.

Plan (3 x 2 tiles): the central core (x 1..2) holds the builders' door on
the front; left and right cradles (x 0..1, 2..3) are open to the front on a
low concrete apron with a steel grating floor. Each cradle's back is a
charging cabinet with a glowing coil and an overhead coupler arm; the
cabinet carries the back of the canopy. The fuel cask stands on the core
roof behind the fan cowl; a beacon mast rises from the right canopy.

Bots charge at CHARGE_SLOTS (native '#Slot#Spot<i>' empties written by
export_lategame_models.py; TransformSlotInitializerSpec SlotKeyword 'Spot',
Charging animation), facing out of the cradle.

Animated: core cooling fan (SPIN_Z), beacon shutter (SPIN_Z).
Power: shafts meet the core's back wall and the cabinets' back faces; the
door face is excluded by the generator.
"""
from frontier_architecture import IRON, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GLOW
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
from lategame_nuclear_parts import trefoil

IDENT = 'ReactorChargingBay'
FOOTPRINT = (3, 2)
HEIGHT = 3
FRAME_END = 121
HERO = 'Riveted steel reactor core between two open charging cradles, crowned by a banded fuel-rod cask and a cooling fan.'

DOOR_X = 1.5
CORE = (1.0, .15, 2.0, 1.9)        # back wall on the cell face: shafts meet it
CORE_TOP = 2.05
APRON_TOP = .10              # concrete apron walking surface
FLOOR = .12                  # grating top, where the bots stand
CRADLE_BACK = 1.42           # front face of the charging cabinets
CABINET_BACK = 1.92          # cabinet backs on the cell face: shafts meet them
CANOPY_Z = 1.62              # canopy deck underside
# (x, y, z, facing x, facing y): one bot per cradle, on the grating, facing out.
CHARGE_SLOTS = [(.5, .78, FLOOR, 0, -1), (2.5, .78, FLOOR, 0, -1)]
# Cradle x ranges: (outer edge, inner edge toward the core).
CRADLES = ((0.0, .97), (3.0, 2.03))


def span(a, b):
    return min(a, b), max(a, b)


def apron(g):
    for outer, inner in CRADLES:
        x0, x1 = span(outer + (.06 if outer < inner else -.06), inner - (.05 if outer < inner else -.05))
        # Cast slab with a proud coping; no face shares the ground plane with
        # the core's posts (slab from 0.01, coping underside at 0.03).
        blk(g, x0, .1, .01, x1, 1.86, APRON_TOP - .03, CONCRETE)
        blk(g, x0 - .04, .06, .03, x1 + .04, 1.9, APRON_TOP, CONCRETE)
        P.grating(g, x0 + .06, .16, x1 - .06, CRADLE_BACK - .02, FLOOR)


def core(g):
    x0, y0, x1, y1 = CORE
    C.framed_block(g, x0, y0, x1, y1, 0.0, CORE_TOP, infill=FORGED, frame=IRON, pitch=.85,
                   faces=('back', 'left', 'right'), floors=(1.2,))
    C.door(g, DOOR_X, y0, 0, 'Door0')
    trefoil(g, DOOR_X, y0 - .015, 1.5, face='front', r=.2)
    blk(g, x0 + .1, y0 - .06, 1.86, x1 - .1, y0 + .02, 1.96, IRON)
    # Roof deck: steel cap with a proud rim.
    blk(g, x0 - .05, y0 - .05, CORE_TOP - .02, x1 + .05, y1 + .05, CORE_TOP + .08, IRON)
    # Hazard band across the back wall.
    n = 6
    w = (x1 - x0 - .3) / n
    for i in range(n):
        a = x0 + .15 + i * w
        blk(g, a, y1 + .06, .62, a + w, y1 + .09, .74, ORANGE if i % 2 == 0 else IRON)


def cask_and_fan(g, parts):
    # Banded fuel-rod cask on the back half of the core roof.
    top = K.tank(g, 1.5, 1.36, CORE_TOP + .08, .3, .5, mat=PAINTED, bands=2, roof='dome', segments=16)
    g.cylinder((1.5, 1.36, top + .1), .05, .12, IRON, 'Z', 8)
    # Cooling fan in an open cowl on the front half of the roof.
    cx, cy, cz = 1.5, .56, CORE_TOP + .08
    K.hollow_revolve(g, (cx, cy, cz - .01), [(.33, 0), (.35, .3)], .05, IRON, segments=16, inner_mat=PAINTED)
    blk(g, cx - .3, cy - .03, cz, cx + .3, cy + .03, cz + .06, IRON)
    blk(g, cx - .03, cy - .3, cz, cx + .03, cy - .031, cz + .06, IRON)
    blk(g, cx - .03, cy + .031, cz, cx + .03, cy + .3, cz + .06, IRON)
    parts.append((P.fan('ReactorChargingBay.Fan', cx, cy, cz + .18, .28, blades=5, pitch=.45, mat=FORGED), 'SPIN_Z', 3))


def cradle(g, outer, inner):
    """Charging cabinet across the back of one cradle, its coupler arm and the
    canopy over it (outer post at the footprint edge, back on the cabinet)."""
    x0, x1 = span(outer, inner)
    cx = (x0 + x1) / 2
    out = -1 if outer < inner else 1
    # Cabinet: painted steel box with a recessed coil window and vents; its
    # cap is buried in the canopy deck so the canopy bears on it.
    blk(g, x0 + .04, CRADLE_BACK, APRON_TOP - .04, x1 - .04, CABINET_BACK, CANOPY_Z - .08, PAINTED)
    blk(g, x0 + .03, CRADLE_BACK - .03, CANOPY_Z - .08, x1 - .03, CABINET_BACK + .03, CANOPY_Z + .02, IRON)
    C.gauge(g, cx + .3, CRADLE_BACK, .78, face='front')
    C.gauge(g, cx - .3, CRADLE_BACK, .78, face='front')
    blk(g, cx - .2, CRADLE_BACK - .025, .42, cx + .2, CRADLE_BACK + .01, 1.02, IRON)
    # One glowing coil slot (emissive accents stay a few faces).
    blk(g, cx - .05, CRADLE_BACK - .04, .5, cx + .05, CRADLE_BACK - .02, .94, GLOW)
    for z in (.47, .97):
        blk(g, cx - .14, CRADLE_BACK - .05, z - .02, cx + .14, CRADLE_BACK - .02, z + .02, BRASS)
    P.louvre(g, 'X', CRADLE_BACK, cx - .3, cx + .3, 1.1, 1.38, -1)
    # Overhead coupler arm reaching out above the bot.
    blk(g, cx - .05, .9, 1.26, cx + .05, CRADLE_BACK + .02, 1.34, IRON)
    g.cylinder((cx, .96, 1.2), .07, .14, BRASS, 'Z', 10)
    g.cylinder((cx, .96, 1.105), .045, .06, IRON, 'Z', 8)
    # Canopy: outer front post, steel deck, front and outer rims.
    px = outer - out * .1
    blk(g, px - .055, .15, APRON_TOP - .04, px + .055, .26, CANOPY_Z + .02, IRON)
    blk(g, x0 + .02, .14, CANOPY_Z, x1 - .02, CABINET_BACK + .02, CANOPY_Z + .09, FORGED)
    # Front rim in hazard stripes.
    n = 5
    for i in range(n):
        a = x0 + i * (x1 - x0) / n
        blk(g, a, .1, CANOPY_Z + .06, a + (x1 - x0) / n, .18, CANOPY_Z + .16, ORANGE if i % 2 == (0 if out < 0 else 1) else IRON)
    ox0, ox1 = span(outer, outer - out * .1)
    blk(g, ox0, .18, CANOPY_Z + .06, ox1, CABINET_BACK + .04, CANOPY_Z + .15, IRON)


def coolant(g):
    # Headers from the cask out over each canopy, dropping onto it.
    for x in (.6, 2.4):
        start = 1.5 + (-.27 if x < 1.5 else .27)
        P.pipe(g, [(start, 1.55, CORE_TOP + .36), (x, 1.55, CORE_TOP + .36), (x, 1.55, CANOPY_Z + .07)],
               .045, flanges=False, segments=8)
        P.hoop(g, (x, 1.55, CANOPY_Z + .14), .07, .04, .05, BRASS, segments=8)
    # Power feed: two insulators on the core roof's back corners.
    for x in (1.12, 1.88):
        P.insulator(g, x, 1.8, CORE_TOP + .08, height=.36, r=.07, discs=3)


def beacon_mast(g, parts):
    x, y = 2.6, 1.62
    blk(g, x - .09, y - .09, CANOPY_Z + .06, x + .09, y + .09, CANOPY_Z + .17, IRON)
    blk(g, x - .05, y - .05, CANOPY_Z + .12, x + .05, y + .05, 2.5, IRON)
    pivot = K.beacon(g, x, y, 2.5)
    parts.append((K.beacon_shutter(*pivot, 'ReactorChargingBay.Beacon'), 'SPIN_Z', 2))


def build(g, parts):
    apron(g)
    core(g)
    cask_and_fan(g, parts)
    for outer, inner in CRADLES:
        cradle(g, outer, inner)
    coolant(g)
    beacon_mast(g, parts)
