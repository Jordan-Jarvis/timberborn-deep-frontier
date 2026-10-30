"""OilPowerPlant: oil-fired turbine power station (20,000 hp, 4 workers).

Designed 2026-10-22 as the late industrial generator between the Coal Power
Plant (5,000 hp) and the Nuclear Reactor.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; outputs/compaction/BRIEF.md): 6x6x9 -> 5x4x6, inside the old
footprint with the same origin, door (x 1.5) and native entrance. One layer
per floor: a concrete ground storey (layer 0) and one steel-clad storey
(layer 1) under a flat concrete roof whose top is layer 3. The plank barrel
vault is gone, and the fin-fan coolers now sit in cowls on that roof instead
of on four steel columns over the tanks.

HERO: a riveted heat-recovery boiler tower with twin exhaust stacks behind a
      flat-roofed turbine hall whose roof carries two spinning fin-fan
      coolers, beside the banded crude-oil day tanks.
ROOF: pitched corrugated-metal gable (ridge along the hall) on the turbine
      hall; flat riveted-steel roof on the boiler tower (roof-variety pass:
      the fin-fan cooler unit stands on the tank bund, not on a roof).

Plan (5 x 4 tiles):
- turbine hall on tiles 0..5 x 0..2: cast-concrete ground storey (the
  workers' door at x 1.5, face 0.18 behind the y = 0 edge) and riveted
  steel-sheet walls up to the roof slab at 2.84;
- tank bund on tiles 0..3 x 2..4: concrete bund with its floor at layer 1,
  two banded day tanks and the transfer pump;
- boiler tower on tiles 3..5 x 2..4: concrete base and a riveted steel tower
  to layer 4 with two exhaust stacks to 5.9.

Animated (names unchanged): two cooler fans (SPIN_Z) and the transfer-pump
coupling (SPIN_X).
Emitters: one vanilla 'smoke' plume per exhaust stack.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, LAYER_GAP
import lategame_industry_parts as P
import lategame_mining_parts as M
from lategame_mining_parts import bx
from lategame_sheet_roofs import sheet_gable
from lategame_roofdeck_parts import deck_slab, parapet_ring

IDENT = 'OilPowerPlant'
FOOTPRINT = (5, 4)
HEIGHT = 6
FRAME_END = 121
HERO = ('Riveted heat-recovery boiler tower with twin exhaust stacks behind a flat-roofed turbine hall carrying '
        'two spinning fin-fan coolers, beside the crude-oil day tanks.')

HALL = (.05, 4.95, .3, 1.95)      # core x0, x1, y0, y1 (plinth course .05 proud: tiles 0..5 x 0..2)
ROOF_Z = 2.6                      # hall eaves
RIDGE = 3.3
STOREY = 1.0                      # concrete ground storey and bund floor (whole layer)
DOOR_X = 1.5
BACK_Y = 2.0                      # back of the hall plinth course
BUND = (0.0, 3.0, BACK_Y, 4.0)
TOWER = (3.05, 4.95, 2.0, 3.95)   # steel boiler tower above its concrete base
TOWER_ROOF = 3.84                 # tower roof slab bottom; its top is layer 4
TANKS = ((.78, 3.05),)
TANK_R = .52
FANS = ((2.25, 2.62), (2.25, 3.42))   # fin-fan cooler unit on the bund


def turbine_hall(g, parts):
    x0, x1, y0, y1 = HALL
    M.hall(g, x0, x1, y0, y1, ROOF_Z, plinth=STOREY, infill=FORGED, frame=IRON, doors=[DOOR_X],
           posts=('front', 'left', 'right'), style='factory', wscale=.62,
           windows={'front': [(.55, 1.92), (2.6, 1.92), (3.55, 1.92), (4.5, 1.92)],
                    'left': [(1.12, 1.92)], 'right': [(1.12, 1.92)]},
           lamps=[('front', .86, .78), ('front', 2.14, .78)])
    # Pitched corrugated-metal roof along the hall.
    sheet_gable(g, x0, y0, x1, y1, ROOF_Z, RIDGE, ridge_axis='X', overhang=.1, mat=PAINTED)


def bund(g, parts):
    x0, x1, y0, y1 = BUND
    bx(g, x0, x1, y0, y1, 0, STOREY, CONCRETE)
    # Low kerb on the outer edges (the hall and tower close the other two).
    k = .12
    bx(g, x0, x0 + k, y0, y1 - k, STOREY, STOREY + .25, CONCRETE)
    bx(g, x0, x1, y1 - k, y1, STOREY, STOREY + .25, CONCRETE)
    for x, y in TANKS:
        K.tank(g, x, y, STOREY, TANK_R, 1.55, mat=PAINTED, bands=3, roof='dome', segments=16)
    # Fin-fan cooler unit on the bund: a louvred housing with two fans on top.
    bx(g, 1.62, 2.88, 2.2, 3.84, STOREY, STOREY + .75, PAINTED)
    P.louvre(g, 'Y', 2.88, 2.3, 3.74, STOREY + .1, STOREY + .65, 1, mat=IRON)
    for (x, y), name in zip(FANS, ('OilPowerPlant.CoolerFan1', 'OilPowerPlant.CoolerFan2')):
        K.hollow_revolve(g, (x, y, STOREY + .75), [(.36, 0), (.36, .2)], .04, PAINTED, segments=16, inner_mat=IRON)
        bx(g, x - .38, x + .38, y - .02, y + .02, STOREY + .94, STOREY + .97, IRON)   # fan guard bar through the ring lip
        fan = P.fan(name, x, y, STOREY + .86, .3, blades=6, pitch=.45, mat=FORGED)
        parts.append((fan, 'SPIN_Z', 3))
    # Transfer pump between the tank and the oil main into the hall.
    px, py, pz = 1.15, 2.3, STOREY + .22
    bx(g, px - .28, px + .28, py - .17, py + .17, STOREY, STOREY + .1, IRON)
    P.motor(g, (px + .12, py, pz), .12, .26, axis='X')
    g.cylinder((px - .19, py, pz), .11, .14, PAINTED, 'X', 12)
    c = Geometry('OilPowerPlant.PumpCoupling', (px - .06, py, pz))
    P.lathe(c, (px - .06, py, pz), [(.07, -.045), (.07, .045)], BRASS, axis='X', segments=10)
    for i in range(4):
        a = i * math.pi / 2
        c.box((px - .06, py + math.cos(a) * .07, pz + math.sin(a) * .07), (.08, .025, .025), IRON)
    parts.append((c, 'SPIN_X', 4))
    (ax, ay), = TANKS
    P.pipe(g, [(ax, ay - TANK_R + .02, pz), (ax, py, pz), (px - .24, py, pz)], .05, flanges=False)
    # Discharge from the pump body up and into the hall's back wall.
    P.pipe(g, [(px - .19, py, pz + .09), (px - .19, py, 1.85), (px - .19, HALL[3] - .02, 1.85)], .06, flanges=False)
    P.valve(g, (px - .19, py, 1.62), 'front', .09)


def boiler_tower(g):
    bx(g, BUND[1], 5.0, BACK_Y, 4.0, 0, STOREY, CONCRETE)
    x0, x1, y0, y1 = TOWER
    bx(g, x0, x1, y0 + .05, y1, STOREY, TOWER_ROOF, FORGED)
    # Corner angles: the back pair from the base, the front pair above the hall roof.
    for x in (x0, x1):
        bx(g, x - .07, x + .07, y1 - .07, y1 + .07, STOREY, TOWER_ROOF - .02, IRON)
        bx(g, x - .07, x + .07, y0 + .07, y0 + .21, 3.3, TOWER_ROOF - .02, IRON)
    for z in (2.0,):
        bx(g, x0 - .025, x1 + .025, y0 + .21, y1 + .025, z - .05, z + .05, IRON)
    P.louvre(g, 'Y', x0, y0 + .4, y1 - .4, 1.25, 1.85, -1)
    # Riveted steel plate roof deck (separate plates) inside an open parapet ring.
    deck_slab(g, x0 - .04, y0 + .01, x1 + .04, y1 + .04, TOWER_ROOF + .16, 'forged')
    parapet_ring(g, x0 - .04, y0 + .01, x1 + .04, y1 + .04, TOWER_ROOF + .16, height=.25)
    # The twin exhaust stacks rise from the tower's base through its roof.
    for x in (3.55, 4.45):
        bx(g, x - .22, x + .22, 2.88, 3.32, STOREY, TOWER_ROOF + .2, IRON)
        K.stack(g, x, 3.1, TOWER_ROOF + .16, 1.74, emits='smoke', r=.22, taper=.85, mat=IRON, bands=2)
    P.gauge(g, x1, 2.6, 1.6, 'right', .09)


def build(g, parts):
    turbine_hall(g, parts)
    bund(g, parts)
    boiler_tower(g)
