"""CoalPowerPlant: coal-fired steam power station (5,000 hp, 3 workers).

Designed 2026-10-22 as the mid-game generator between the vanilla Steam
Engine (400 hp) and the Oil Power Plant (20,000 hp).

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; outputs/compaction/BRIEF.md): 5x5x10 -> 4x4x6, inside the old
footprint with the same origin, door (x 1.5) and native entrance. One layer
per floor: a concrete ground storey (layer 0) and one steel-clad storey
(layer 1) under a flat concrete roof whose top is layer 3. The plank gable is
gone; the chimney is 4 layers shorter.

HERO: a banded riveted chimney on a square concrete base, smoking over a
      flat-roofed steel-clad boiler house, with an open horizontal steam
      engine whose spoked flywheel turns beside the boiler house.
ROOF: pitched corrugated-metal gable (ridge front to back) on the boiler
      house, riveted steel gable ends; a plank lean-to over the engine
      (roof-variety pass: no roof deck, no roof bunker).

Plan (4 x 4 tiles):
- boiler house on tiles 0..3 x 0..4: cast-concrete ground storey (the
  workers' door at x 1.5, face 0.18 behind the y = 0 edge, door rule) and
  riveted steel-sheet walls on a steel frame up to the roof slab at 2.84;
- engine deck on tile column 3 x 0..2: concrete bed with its top at layer 1,
  carrying the cylinder, crosshead guides, crankshaft and flywheel;
- chimney base on tile column 3 x 2..4: concrete block with its top at
  layer 1 and the chimney rising to 5.9; a riveted breeching duct joins it
  to the boiler-house wall.

Animated (names unchanged): flywheel (SPIN_X, two turns per loop) and piston
rod with its crosshead (PISTON_Y, two strokes per loop).
Emitter: one vanilla 'smoke' plume at the chimney mouth.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, FORGED, PAINTED, LAYER_GAP
import lategame_industry_parts as P
import lategame_mining_parts as M
from lategame_mining_parts import bx
from lategame_sheet_roofs import sheet_gable

IDENT = 'CoalPowerPlant'
FOOTPRINT = (4, 4)
HEIGHT = 6
FRAME_END = 121
HERO = ('Banded riveted chimney smoking over a flat-roofed steel-clad boiler house, beside an open horizontal '
        'steam engine with a spoked flywheel.')

HALL = (.05, 2.95, .3, 3.95)      # core x0, x1, y0, y1 (plinth course .05 proud: tiles 0..3 x 0..4)
STOREY = 1.0                      # concrete ground storey (whole layer)
ROOF_Z = 2.6                      # eaves
RIDGE = 3.45
DOOR_X = 1.5
DECK = (3.05, 4.0, 0.0, 2.05)     # engine bed, top at layer 1
BASE = (3.05, 4.0, 2.05, 4.0)     # chimney base, top at layer 1
STACK = (3.52, 3.02)
STACK_R = .34
ENGINE_X = 3.42                   # cylinder / crosshead axis
CRANK_Y, CRANK_Z = 1.62, 1.62
WHEEL_X = 3.72


def boiler_house(g):
    x0, x1, y0, y1 = HALL
    M.hall(g, x0, x1, y0, y1, ROOF_Z, plinth=STOREY, infill=FORGED, frame=IRON, doors=[DOOR_X],
           posts=('front', 'back', 'left'), style='factory', wscale=.62,
           windows={'front': [(.55, 1.92), (2.45, 1.92)],
                    'left': [(1.2, 1.92), (2.85, 1.92)],
                    'back': [(1.5, 1.92)]},
           lamps=[('front', .86, .78), ('front', 2.14, .78)])
    # Pitched corrugated-metal roof, ridge front to back.
    sheet_gable(g, x0, y0, x1, y1, ROOF_Z, RIDGE, ridge_axis='Y', overhang=.1, mat=PAINTED)


def engine_deck(g, parts):
    x0, x1, y0, y1 = DECK
    bx(g, x0, x1, y0, y1, 0, STOREY, CONCRETE)
    # Proud shadow strips on the open faces of the bed.
    M.face_member(g, 'front', DECK, 3.47, 3.59, -.01, .03, .12, STOREY - .1, CONCRETE)
    M.face_member(g, 'right', DECK, .96, 1.08, -.01, .03, .12, STOREY - .1, CONCRETE)
    z = STOREY
    # Engine bed and cylinder.
    bx(g, ENGINE_X - .28, ENGINE_X + .28, .2, 1.85, z, z + .2, CONCRETE)
    zb = z + .2
    bx(g, ENGINE_X - .17, ENGINE_X + .17, .35, .85, zb, zb + .12, IRON)
    cz = 1.55
    P.lathe(g, (ENGINE_X, .6, cz), [(.22, -.3), (.26, -.27), (.26, .27), (.22, .3)], PAINTED, axis='Y', segments=12)
    for y in (.38, .82):
        P.hoop(g, (ENGINE_X, y, cz), .29, .05, .05, IRON, axis='Y', segments=12)
    g.cylinder((ENGINE_X, .27, cz), .12, .06, BRASS, 'Y', 10)
    # Steam main from the boiler house into the steam chest.
    P.pipe(g, [(x0 - .1, .6, 2.3), (ENGINE_X, .6, 2.3), (ENGINE_X, .6, cz + .25)], .07)
    P.valve(g, (ENGINE_X, .6, 2.02), 'right', .1)
    # Crosshead guides on their stand.
    bx(g, ENGINE_X - .16, ENGINE_X + .16, 1.0, 1.45, zb, zb + .16, IRON)
    for dx in (-.11, .11):
        bx(g, ENGINE_X + dx - .025, ENGINE_X + dx + .025, .95, 1.5, zb + .16, cz + .04, IRON)
    # Crankshaft and its two bearing pedestals.
    for x, zf in ((ENGINE_X, zb), (3.88, z)):
        bx(g, x - .08, x + .08, 1.48, 1.76, zf, CRANK_Z - .07, IRON)
        bx(g, x - .1, x + .1, 1.46, 1.78, CRANK_Z - .07, CRANK_Z + .07, BRASS)
    g.cylinder((3.65, CRANK_Y, CRANK_Z), .055, .5, IRON, 'X', 8)
    P.gauge(g, x0 - .1, 1.25, 1.95, 'right', .08)
    # Piston rod and crosshead (moves back and forth along Y).
    rod = Geometry('CoalPowerPlant.PistonRod', (ENGINE_X, 1.1, cz))
    P.tube(rod, (ENGINE_X, .86, cz), (ENGINE_X, 1.3, cz), .032, IRON, segments=8)
    rod.box((ENGINE_X, 1.35, cz), (.14, .12, .13), BRASS)
    parts.append((rod, 'PISTON_Y', .14))
    # Flywheel on the crankshaft.
    wheel = P.flywheel('CoalPowerPlant.Flywheel', (WHEEL_X, CRANK_Y, CRANK_Z), .4, axis='X', spokes=6, width=.12)
    wheel.cylinder((WHEEL_X + .065, CRANK_Y + .2, CRANK_Z), .045, .13, BRASS, 'X', 8)
    parts.append((wheel, 'SPIN_X', 2))
    # Lean-to over the engine on two steel posts at the open side.
    for y in (.12, 1.93):
        M.column(g, 3.91, y, z, 2.12, .11)
    bx(g, 3.85, 3.97, .06, 1.99, 2.12, 2.2, IRON)
    M.lean_to(g, HALL[1] + .02, 3.95, .05, 2.0, 2.2, 2.55, low_side='right', overhang=.04, seed=43)


def chimney(g):
    x0, x1, y0, y1 = BASE
    bx(g, x0, x1, y0, y1, 0, STOREY, CONCRETE)
    bx(g, x0 - .03, x1 + .03, y0 - .03, y1 + .03, STOREY - .02, STOREY + .08, CONCRETE)
    # Ash-pit door on the right face.
    bx(g, x1, x1 + .03, 2.75, 3.3, .15, .8, IRON)
    K.stack(g, STACK[0], STACK[1], STOREY + .08, 4.72, emits='smoke', r=STACK_R, taper=.78, mat=IRON, bands=4)
    # Riveted breeching duct from the boiler house into the chimney.
    bx(g, HALL[1], STACK[0] - .27, 2.8, 3.24, 1.95, 2.4, FORGED)
    bx(g, 3.08, 3.14, 2.77, 3.27, 1.92, 2.43, IRON)


def build(g, parts):
    boiler_house(g)
    engine_deck(g, parts)
    chimney(g)
