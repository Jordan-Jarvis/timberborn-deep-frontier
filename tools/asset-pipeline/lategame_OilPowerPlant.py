"""OilPowerPlant: oil-fired turbine power station (20,000 hp, 4 workers).

Designed 2026-10-22 as the late industrial generator between the Coal Power
Plant (5,000 hp) and the Nuclear Reactor: a 6 x 6 plant, smaller than the
late-game giants. The footprint ends at the walls on all four sides; nothing
stands on ground outside them.

HERO: a riveted heat-recovery boiler tower with twin exhaust stacks behind a
      barrel-vaulted turbine hall, with fin-fan coolers spinning over the
      crude-oil day tanks.
ROOF: teal native plank barrel vault (along X) on the turbine hall; flat
      parapet roof on the boiler tower; open fan cowls on the cooler bank.

Plan (6 x 6 tiles):
- turbine hall on tiles 0..6 x 0..4: cast-concrete lower storey (layer 0,
  the workers' door at x 1.5) and riveted steel-sheet walls on a steel frame
  up to the vault springing at 4.0; door face 0.18 behind the y = 0 edge;
- tank bund on tiles 0..4 x 3..6: concrete bund with its floor at layer 1,
  two banded day tanks, the transfer pump, and the fin-fan cooler bank on
  four steel columns above the tanks;
- boiler tower on tiles 3..6 x 3..6: concrete base and a riveted steel tower
  to 5.6 with a parapet roof and two exhaust stacks to 8.8.

Animated: two cooler fans (SPIN_Z) and the transfer-pump coupling (SPIN_Y).
Emitters: one vanilla 'smoke' plume per exhaust stack; oil burns cleaner than
coal, so the stacks are narrow and tools/smog_content.json gives a smaller
smog disc.
Power: shafts meet the walls on the tile edges (left and right of the
turbine hall, left and back of the bund, right and back of the boiler tower).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, LAYER_GAP
import lategame_industry_parts as P
import lategame_mining_parts as M
from lategame_mining_parts import bx

IDENT = 'OilPowerPlant'
FOOTPRINT = (6, 6)
HEIGHT = 9
FRAME_END = 121
HERO = ('Riveted heat-recovery boiler tower with twin exhaust stacks behind a barrel-vaulted turbine hall, '
        'with fin-fan coolers spinning over the crude-oil day tanks.')

HALL = (.05, 5.95, .3, 3.45)      # core x0, x1, y0, y1 (plinth course .05 proud: tiles 0..6 x 0..3.5)
HALL_TOP = 4.0                    # vault springing
STOREY = 1.0                      # concrete lower storey and bund floor (whole layer)
RISE = 1.0
DOOR_X = 1.5
BACK_Y = 3.5                      # back of the hall plinth course
BUND = (0.0, 3.4, BACK_Y, 6.0)
TOWER = (3.5, 5.95, 3.45, 5.95)   # steel boiler tower above its concrete base
TOWER_TOP = 5.6
TANKS = ((.9, 5.1), (2.45, 5.1))
TANK_R = .6
COOLER = (.15, 3.25, 3.65, 5.9, 4.1, 4.5)   # x0, x1, y0, y1, z0, z1
FANS = ((.92, 4.78), (2.48, 4.78))


def turbine_hall(g):
    x0, x1, y0, y1 = HALL
    M.hall(g, x0, x1, y0, y1, HALL_TOP, plinth=STOREY, infill=FORGED, frame=IRON, doors=[DOOR_X],
           posts=('front', 'left', 'right'), style='factory', wscale=.8,
           windows={'front': [(.54, 2.5), (3.49, 2.5), (4.475, 2.5), (5.46, 2.5)],
                    'left': [(1.875, 2.5)], 'right': [(1.875, 2.5)]},
           lamps=[('front', .86, .78), ('front', 2.14, .78)])
    P.plank_vault(g, x0, y0, x1, y1, HALL_TOP, RISE, overhang=.1, plank=.34, segments=12, ribs=5)
    half = (y1 - y0) / 2
    cy = (y0 + y1) / 2
    pts = [(cy + math.cos(math.pi * k / 12) * (half + .04), HALL_TOP + math.sin(math.pi * k / 12) * (RISE - .1))
           for k in range(13)]
    prof = [(y0 - .04, HALL_TOP - .03), (y1 + .04, HALL_TOP - .03)] + pts[1:-1]
    for plane, out in ((x0, -1), (x1, 1)):
        P.end_prism(g, 'X', plane, out, prof, ORANGE)
    # Roof ventilator on the crown.
    crown = HALL_TOP + RISE + .02
    for x in (1.85, 4.15):
        bx(g, x - .25, x + .25, cy - .25, cy + .25, crown - .12, crown + .2, FORGED)
        bx(g, x - .31, x + .31, cy - .31, cy + .31, crown + .2, crown + .28, IRON)


def bund(g, parts):
    x0, x1, y0, y1 = BUND
    bx(g, x0, x1, y0, y1, 0, STOREY, CONCRETE)
    # Low kerb on the outer edges (the hall and tower close the other two).
    k = .12
    bx(g, x0, x0 + k, y0, y1 - k, STOREY, STOREY + .25, CONCRETE)
    bx(g, x0, x1, y1 - k, y1, STOREY, STOREY + .25, CONCRETE)
    for x, y in TANKS:
        K.tank(g, x, y, STOREY, TANK_R, 2.2, mat=PAINTED, bands=3, roof='dome', segments=16)
    # Transfer pump between the tanks and the oil main into the hall.
    px, py, pz = 1.65, 4.1, STOREY + .25
    bx(g, px - .3, px + .3, py - .22, py + .22, STOREY, STOREY + .12, IRON)
    P.motor(g, (px + .12, py, pz), .14, .3, axis='X')
    g.cylinder((px - .2, py, pz), .13, .16, PAINTED, 'X', 12)
    c = Geometry('OilPowerPlant.PumpCoupling', (px - .06, py, pz))
    P.lathe(c, (px - .06, py, pz), [(.08, -.05), (.08, .05)], BRASS, axis='X', segments=10)
    for i in range(4):
        a = i * math.pi / 2
        c.box((px - .06, py + math.cos(a) * .08, pz + math.sin(a) * .08), (.09, .03, .03), IRON)
    parts.append((c, 'SPIN_X', 4))
    (ax, ay), (bx_, by) = TANKS
    P.pipe(g, [(ax, ay - TANK_R + .02, pz), (ax, py, pz), (px - .25, py, pz)], .06, flanges=False)
    P.pipe(g, [(bx_, by - TANK_R + .02, 1.6), (bx_, 4.38, 1.6), (ax, 4.38, 1.6), (ax, 4.38, pz + .05)], .06,
           flanges=False)
    # Discharge from the pump body up and into the hall's back wall.
    P.pipe(g, [(px - .2, py, pz + .1), (px - .2, py, 1.85), (px - .2, HALL[3] - .02, 1.85)], .07, flanges=False)
    P.valve(g, (px - .2, py, 1.65), 'front', .1)
    # Fin-fan cooler bank on four steel columns.
    cx0, cx1, cy0, cy1, cz0, cz1 = COOLER
    for x in (.27, 3.13):
        for y in (3.75, 5.74):
            M.column(g, x, y, STOREY, cz0, .12)
    bx(g, cx0, cx1, cy0, cy1, cz0, cz1, PAINTED)
    P.louvre(g, 'X', cy0, cx0 + .1, cx1 - .1, cz0 + .04, cz1 - .04, -1, mat=IRON)
    for (x, y), name in zip(FANS, ('OilPowerPlant.CoolerFan1', 'OilPowerPlant.CoolerFan2')):
        K.hollow_revolve(g, (x, y, cz1), [(.66, 0), (.66, .3)], .06, PAINTED, segments=16, inner_mat=IRON)
        P.hoop(g, (x, y, cz1 + .26), .69, .05, .05, IRON, segments=16)
        bx(g, x - .62, x + .62, y - .02, y + .02, cz1 + .26, cz1 + .29, IRON)
        fan = P.fan(name, x, y, cz1 + .14, .52, blades=6, pitch=.45, mat=FORGED)
        parts.append((fan, 'SPIN_Z', 3))


def boiler_tower(g):
    bx(g, BUND[1], 6.0, BACK_Y, 6.0, 0, STOREY, CONCRETE)
    x0, x1, y0, y1 = TOWER
    bx(g, x0, x1, y0, y1, STOREY, TOWER_TOP, FORGED)
    # Corner angles: the back pair from the base, the front pair above the vault.
    for x in (x0, x1):
        bx(g, x - .07, x + .07, y1 - .07, y1 + .07, STOREY, TOWER_TOP - .02, IRON)
        bx(g, x - .07, x + .07, y0 + .02, y0 + .16, 4.45, TOWER_TOP - .02, IRON)
    for z in (2.4, 3.7):
        bx(g, x0 - .025, x1 + .025, y0 + .14, y1 + .025, z - .05, z + .05, IRON)
    P.louvre(g, 'Y', x0, y0 + .4, y1 - .4, 1.4, 2.2, -1)
    M.flat_roof(g, x0, x1, y0, y1, TOWER_TOP, t=.16, overhang=.04, parapet=.25)
    for x in (4.15, 5.3):
        K.stack(g, x, 4.75, TOWER_TOP + .16, 2.9, emits='smoke', r=.26, taper=.85, mat=IRON, bands=3)
    P.gauge(g, x1, 4.2, 1.6, 'right', .09)


def build(g, parts):
    turbine_hall(g)
    bund(g, parts)
    boiler_tower(g)
