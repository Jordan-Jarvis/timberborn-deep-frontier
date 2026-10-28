"""CoalPowerPlant: coal-fired steam power station (5,000 hp, 3 workers).

Designed 2026-10-22 as the mid-game generator between the vanilla Steam
Engine (400 hp) and the Oil Power Plant (20,000 hp): a compact 5 x 5 plant,
deliberately smaller than the late-game giants. The footprint ends at the
walls on all four sides; nothing stands on ground outside them.

HERO: a tall banded riveted chimney on a square concrete base, smoking over
      a steel-clad boiler house, with an open horizontal steam engine whose
      spoked flywheel turns beside the boiler house.
ROOF: teal native plank gable (ridge front to back) on the boiler house with
      a riveted coal bunker rising through its back half; a plank lean-to
      over the engine deck.

Plan (5 x 5 tiles):
- boiler house on tiles 0..3 x 0..5: cast-concrete lower storey (layer 0,
  the workers' door at x 1.5) and riveted steel-sheet walls on a steel frame
  up to the eaves at 4.6; door face 0.18 behind the y = 0 edge (door rule);
- engine deck on tiles 3..5 x 0..3: concrete bed with its top at layer 1,
  carrying the cylinder, crosshead guides, crankshaft and flywheel;
- chimney base on tiles 3..5 x 3..5: concrete block with its top at layer 2
  and the chimney rising to 9.9; a riveted breeching duct joins it to the
  boiler house wall.

Animated: flywheel (SPIN_X, two turns per loop) and piston rod with its
crosshead (PISTON_Y, two strokes per loop, in step with the flywheel).
Emitter: one vanilla 'smoke' plume at the chimney mouth (coal is the dirtier
fuel; tools/smog_content.json gives it the wider smog disc).
Power: shafts meet the walls on the tile edges (left and back of the boiler
house, front and right of the engine bed, right and back of the chimney base).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, FORGED, PAINTED, LAYER_GAP
import lategame_industry_parts as P
import lategame_mining_parts as M
from lategame_mining_parts import bx

IDENT = 'CoalPowerPlant'
FOOTPRINT = (5, 5)
HEIGHT = 10
FRAME_END = 121
HERO = ('Tall banded riveted chimney smoking over a steel-clad boiler house, beside an open horizontal '
        'steam engine with a spoked flywheel.')

HALL = (.05, 3.0, .3, 4.95)       # core x0, x1, y0, y1 (plinth course .05 proud: tiles 0..3 x 0..5)
HALL_TOP = 4.6                    # eaves
STOREY = 1.0                      # concrete lower storey (whole layer)
RIDGE = 5.9
DOOR_X = 1.5
DECK = (3.05, 5.0, 0.0, 2.95)     # engine bed, top at layer 1
BASE = (3.05, 5.0, 2.95, 5.0)     # chimney base, top at layer 2
STACK = (4.02, 3.98)
STACK_R = .42
ENGINE_X = 3.8                    # cylinder / crosshead axis
CRANK_Y, CRANK_Z = 2.25, 1.72
WHEEL_X = 4.55


def boiler_house(g):
    x0, x1, y0, y1 = HALL
    M.hall(g, x0, x1, y0, y1, HALL_TOP, plinth=STOREY, infill=FORGED, frame=IRON, doors=[DOOR_X],
           posts=('front', 'back', 'left'), style='factory', wscale=.8,
           windows={'front': [(.62, 2.75), (2.42, 2.75)],
                    'left': [(1.695, 2.75), (3.555, 2.75)],
                    'back': [(1.52, 2.75)]},
           lamps=[('front', .86, .78), ('front', 2.14, .78)])
    M.plank_gable(g, x0, x1, y0, y1, HALL_TOP, RIDGE, ridge_axis='Y', overhang=.1, seed=41)
    # Clerestory windows on the right wall, above the engine lean-to (no posts on that wall).
    for y in (1.0, 2.2):
        M.window(g, x1, y, 4.02, 'right', .55, 'factory')
    # Coal bunker rising through the back half of the roof.
    bx(g, .62, 2.43, 3.45, 4.55, 5.0, 6.55, FORGED)
    for x in (.62, 2.43):
        for y in (3.45, 4.55):
            bx(g, x - .05, x + .05, y - .05, y + .05, 5.0, 6.6, IRON)
    bx(g, .52, 2.53, 3.35, 4.65, 6.6, 6.68, IRON)
    M.frustum(g, (1.0, 2.05, 3.7, 4.3), 6.95, (.68, 2.37, 3.5, 4.5), 6.68, IRON)
    for x in (1.0, 1.52, 2.05):
        K.stud(g, (x, 3.45 - .006, 6.2), 'Y', .02)


def engine_deck(g, parts):
    x0, x1, y0, y1 = DECK
    bx(g, x0, x1, y0, y1, 0, STOREY, CONCRETE)
    # Proud shadow strips on the open faces of the bed.
    M.face_member(g, 'front', DECK, 3.94, 4.06, -.01, .03, .12, STOREY - .1, CONCRETE)
    for y in (1.0, 2.0):
        M.face_member(g, 'right', DECK, y - .06, y + .06, -.01, .03, .12, STOREY - .1, CONCRETE)
    z = STOREY
    # Engine bed and cylinder.
    bx(g, ENGINE_X - .35, ENGINE_X + .35, .35, 2.6, z, z + .25, CONCRETE)
    zb = z + .25
    bx(g, ENGINE_X - .2, ENGINE_X + .2, .55, 1.15, zb, zb + .15, IRON)
    cz = 1.62
    P.lathe(g, (ENGINE_X, .85, cz), [(.26, -.4), (.3, -.36), (.3, .36), (.26, .4)], PAINTED, axis='Y', segments=12)
    for y in (.6, 1.1):
        P.hoop(g, (ENGINE_X, y, cz), .33, .05, .05, IRON, axis='Y', segments=12)
    g.cylinder((ENGINE_X, .43, cz), .14, .06, BRASS, 'Y', 10)
    # Steam main from the boiler house into the steam chest.
    P.pipe(g, [(x0 - .05, .85, 2.75), (ENGINE_X, .85, 2.75), (ENGINE_X, .85, cz + .3)], .07)
    P.valve(g, (ENGINE_X, .85, 2.3), 'right', .11)
    # Crosshead guides on their stand.
    bx(g, ENGINE_X - .18, ENGINE_X + .18, 1.3, 1.95, zb, zb + .2, IRON)
    for dx in (-.12, .12):
        bx(g, ENGINE_X + dx - .025, ENGINE_X + dx + .025, 1.25, 2.08, zb + .2, cz + .04, IRON)
    # Crankshaft, bearing pedestals and the governor post.
    for x, zf in ((ENGINE_X, zb), (4.3, z)):
        bx(g, x - .1, x + .1, 2.1, 2.4, zf, CRANK_Z - .07, IRON)
        bx(g, x - .12, x + .12, 2.08, 2.42, CRANK_Z - .07, CRANK_Z + .08, BRASS)
    g.cylinder((4.2, CRANK_Y, CRANK_Z), .06, .96, IRON, 'X', 8)
    P.gauge(g, x0 - .05, 1.7, 2.25, 'right', .09)
    # Piston rod and crosshead (moves back and forth along Y).
    rod = Geometry('CoalPowerPlant.PistonRod', (ENGINE_X, 1.25, cz))
    P.tube(rod, (ENGINE_X, .95, cz), (ENGINE_X, 1.72, cz), .035, IRON, segments=8)
    rod.box((ENGINE_X, 1.78, cz), (.15, .14, .14), BRASS)
    parts.append((rod, 'PISTON_Y', .22))
    # Flywheel on the crankshaft.
    wheel = P.flywheel('CoalPowerPlant.Flywheel', (WHEEL_X, CRANK_Y, CRANK_Z), .62, axis='X', spokes=6, width=.12)
    wheel.cylinder((WHEEL_X + .065, CRANK_Y + .3, CRANK_Z), .05, .13, BRASS, 'X', 8)
    parts.append((wheel, 'SPIN_X', 2))
    # Lean-to over the engine on two steel posts at the open side.
    for y in (.15, 2.8):
        M.column(g, 4.86, y, z, 2.88, .12)
    bx(g, 4.8, 4.92, .06, 2.89, 2.88, 2.96, IRON)
    M.lean_to(g, x0, 4.95, .05, 2.9, 2.95, 3.45, low_side='right', overhang=.05, seed=43)


def chimney(g):
    x0, x1, y0, y1 = BASE
    # Lower block meets the boiler-house plinth course; the upper block meets its wall.
    bx(g, x0, x1, y0, y1, 0, STOREY, CONCRETE)
    bx(g, HALL[1], x1, y0, y1, STOREY, 1.92, CONCRETE)
    bx(g, HALL[1], x1 + .03, y0 - .03, y1 + .03, 1.92, 2.0, CONCRETE)
    # Ash-pit door on the right face.
    bx(g, x1, x1 + .03, 3.7, 4.3, .2, .85, IRON)
    K.stack(g, STACK[0], STACK[1], 2.0, 7.8, emits='smoke', r=STACK_R, taper=.78, mat=IRON, bands=5)
    # Riveted breeching duct from the boiler house into the chimney.
    bx(g, HALL[1], STACK[0] - .32, 3.74, 4.22, 3.2, 3.76, FORGED)
    for x in (3.2, 3.45):
        bx(g, x - .03, x + .03, 3.71, 4.25, 3.17, 3.79, IRON)


def build(g, parts):
    boiler_house(g)
    engine_deck(g, parts)
    chimney(g)
