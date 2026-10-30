"""ChemicalWorks: oil-derived resins, plastics and sulfur (8 workers, 3500 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the barrel store.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size", "one layer per floor", "make
the roof flat on more of our buildings", "no clutter on buildable space"): 10x9x14 -> 5x5x8, inside the old
footprint with the same origin, door and native entrance (cell 1, -1).
Removed: the lattice flare tower and its knock-out drum, the pipe-rack
catwalk on its bents, the fin-fan cooler on its piers, the spherical product
tank, the column's lower two ring platforms and the gabled roofs. The
reactor hall is one solid two-storey block (one layer per storey) with a flat
roof that carries the cooler, its ventilators and the flare stack; its front
two rows stay open.

HERO: a riveted fractionating column (seven layers) with one ring platform
      and a caged ladder, its vapour line dropping to the fin-fan cooler on
      the hall roof, beside a short flare stack with a live flame.
ROOF: flat corrugated-metal roof with a steel curb on the reactor hall,
      its front two rows placeable; the one-layer fin-fan cooler house on
      its back rows has a flat steel-plate top, placeable except the two fan
      cells and the middle cell; steel dome on the column. No roof vents
      (user: "no roof vents. they just get in the way").

Plan (5 x 5 tiles): the reactor hall on the left (door front-left), three
agitated reactors in a row on a concrete apron along its right wall, the
column behind them.

Animated (6, names unchanged): three agitator couplings, two cooler fans,
the flare flame, the column beacon (the three roof ventilators went in the
roof follow-up: "no roof vents").
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, CYAN, GLOW
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
import compact_industry_parts as Q

IDENT = 'ChemicalWorks'
FOOTPRINT = (5, 5)
HEIGHT = 8
FRAME_END = 121
HERO = ('A seven-layer riveted fractionating column with a ring platform and a caged ladder, its vapour line '
        'dropping to a fin-fan cooler on the flat hall roof, beside a flare stack with a live flame.')

DOOR_X = 1.5
HALL = (0.0, 0.0, 3.0, 5.0)      # two storeys on whole tiles
ROOF_Z = 2.0
COLUMN = (4.0, 3.95)
COLUMN_R = .48
COLUMN_TOP = 6.4
PLATFORM_Z = 5
REACTOR_X = 4.0
REACTORS_Y = (.55, 1.5, 2.45)
REACTOR_R = .36
FLARE = (2.84, 4.84)   # on the cooler house's back corner, clear of its cell's middle


# ---------------------------------------------------------------- reactor hall

def hall(g):
    x0, y0, x1, y1 = HALL
    Q.storey_block(g, x0, y0, x1, y1, 2, infill=FORGED, frame=IRON, door=DOOR_X, door_id='Entrance',
                   roof_mat=PAINTED, curb_mat=IRON, roof_boards=True,
                   ground_windows={'left': [(1.5, .6, 'factory'), (3.5, .6, 'factory')],
                                   'back': [(1.5, .6, 'factory')],
                                   'right': [(3.0, .6, 'factory')]},
                   windows={'front': [(.5, 1.5, .55, 'factory'), (1.5, 1.5, .55, 'factory'),
                                      (2.5, 1.5, .55, 'factory')],
                            'left': [(y + .5, 1.5, .55, 'factory') for y in range(5)],
                            'back': [(.5, 1.5, .55, 'factory'), (2.5, 1.5, .55, 'factory')],
                            'right': [(y + .5, 1.5, .55, 'factory') for y in (2, 3, 4)]})
    K.lamp(g, DOOR_X - .66, y0 - .01, .8, face='front')
    K.lamp(g, DOOR_X + .66, y0 - .01, .8, face='front')
    # Instrument board beside the door: gauges and indicator lights.
    blk(g, 2.55, y0 - .06, .32, 2.95, y0 - .004, .78, PAINTED)
    for gx in (2.65, 2.85):
        P.gauge(g, gx, y0 - .06, .64, 'front', .07)
    for k, lx in enumerate((2.63, 2.75, 2.87)):
        g.cylinder((lx, y0 - .075, .42), .02, .03, CYAN if k % 2 == 0 else IRON, 'Y', 8)


def roof_plant(g, parts):
    """Fin-fan cooler house: one layer on the back three rows of the hall roof
    (tiles 0..3 x 2..5) with louvred forged sides and a flat top on layer 3.
    The two fans stand in the middle of its front and back cells; the top's
    other cells and the hall roof's front two rows are platformable (user: "all flat roof
    tiles should be placeable areas")."""
    z = ROOF_Z
    x0, y0, x1, y1 = .06, 2.0, 2.94, 4.94   # inside the hall roof's curb
    top = z + 1.0
    blk(g, x0 + .06, y0 + .06, z - .02, x1 - .06, y1 - .06, top - .1, FORGED)
    for x, y in ((x0 + .06, y0 + .06), (x1 - .06, y0 + .06), (x1 - .06, y1 - .06), (x0 + .06, y1 - .06)):
        blk(g, x - .07, y - .07, z, x + .07, y + .07, top - .1, IRON)
    # Louvre bands on the long sides and the front, proud of the fin bank.
    for k in range(3):
        zz = z + .22 + k * .22
        blk(g, x0 + .13, y0 + .03, zz, x1 - .13, y0 + .06, zz + .06, IRON)
        blk(g, x0 + .03, y0 + .13, zz, x0 + .06, y1 - .13, zz + .06, IRON)
        blk(g, x1 - .06, y0 + .13, zz, x1 - .03, y1 - .13, zz + .06, IRON)
    Q.flat_roof(g, x0, y0, x1, y1, top, overhang=0.0, mat=IRON, curb_mat=IRON, boards=True)
    for i, y in enumerate((2.5, 4.5)):
        cx = 1.5
        P.hoop(g, (cx, y, top + .16), .4, .04, .3, IRON, segments=12)
        P.hoop(g, (cx, y, top + .32), .43, .06, .05, PAINTED, segments=12)
        blk(g, cx - .38, y - .03, top, cx + .38, y + .03, top + .06, IRON)
        g.cylinder((cx, y, top + .12), .07, .12, IRON, 'Z', 10)
        parts.append((P.fan(f'ChemicalWorks.CoolerFan{i + 1}', cx, y, top + .22, .34, blades=5),
                      'SPIN_Z', 4 if i else -4))


# ---------------------------------------------------------------- reactors

def reactors(g, parts):
    """Three agitated reactors in a row along the hall's right wall, on a
    concrete apron that fills tiles 3..5 x 0..3; manways face outward."""
    base = .3
    C.podium(g, 3.0, 0.0, 5.0, 3.0, base, joints=False, foot=False)   # the hall's foot course meets it
    x = REACTOR_X
    for i, y in enumerate(REACTORS_Y):
        top = K.tank(g, x, y, base, REACTOR_R, 1.3, mat=PAINTED, bands=2, roof='dome')
        dome_top = top + (REACTOR_R + .03) * .45
        # Bolted manway, bottom outlet and sight gauge on the outer (+X) side.
        mz = base + .75
        g.cylinder((x + REACTOR_R + .03, y, mz), .15, .06, IRON, 'X', 12)
        P.disc(g, (x + REACTOR_R + .065, y, mz), .17, .03, BRASS, axis='X', segments=12)
        P.pipe(g, [(x + .2, y - .2, base + .4), (x + .2, y - .52, base + .4)], .045, flanges=False)
        P.valve(g, (x + .2, y - .44, base + .4), 'up', .08, stem=.15)
        P.gauge(g, x + REACTOR_R - .05, y - .22, base + 1.15, 'right', .065)
        # Agitator drive: saddle, gearbox, spinning coupling, motor.
        sz = dome_top - .02
        blk(g, x - .2, y - .25, sz, x + .2, y + .25, sz + .08, IRON)
        blk(g, x - .14, y - .14, sz + .08, x + .14, y + .14, sz + .32, PAINTED)
        P.motor(g, (x, y, sz + .78), .13, .34, axis='Z')
        c = Geometry(f'ChemicalWorks.Agitator{i + 1}', (x, y, sz + .46))
        P.lathe(c, (x, y, sz + .46), [(.05, -.13), (.05, -.06), (.14, -.06), (.14, -.02),
                                       (.05, -.02), (.05, .02), (.14, .02), (.14, .06),
                                       (.05, .06), (.05, .13)], IRON, segments=8)
        for k in range(4):
            a = k * math.pi / 2
            c.box((x + math.cos(a) * .1, y + math.sin(a) * .1, sz + .46), (.04, .04, .14), BRASS)
        parts.append((c, 'SPIN_Z', 3))
        # Vapour nozzle from the dome across to the header on the hall wall.
        P.pipe(g, [(x - .12, y + .22, dome_top - .1), (x - .12, y + .22, 2.35), (3.25, y + .22, 2.35)], .05,
               flanges=False)
    # Vapour header along the hall's right wall, into its upper storey.
    P.pipe(g, [(3.25, REACTORS_Y[0] + .22, 2.35), (3.25, REACTORS_Y[-1] + .22, 2.35)], .07, flanges=False)
    P.pipe(g, [(3.25, 1.5, 2.35), (3.25, 1.5, 1.6), (3.0, 1.5, 1.6)], .07, flanges=False)


# ---------------------------------------------------------------- column

def column(g, parts):
    cx, cy = COLUMN
    r = COLUMN_R
    # Octagonal concrete footing and flared steel skirt.
    K.revolve(g, (cx, cy, 0), [(.78, 0), (.78, .3), (.7, .38)], CONCRETE, segments=8, phase=math.pi / 8)
    K.revolve(g, (cx, cy, .38), [(r + .12, 0), (r + .12, .3), (r, .55)], IRON, segments=12)
    K.revolve(g, (cx, cy, .93), [(r, 0), (r, COLUMN_TOP - .93)], IRON, segments=12, cap_bottom=False, cap_top=False)
    K.dome(g, (cx, cy, COLUMN_TOP), r + .025, IRON, segments=12, squash=.55)
    # Painted tray-section bands below and above the insulated middle.
    for z in (1.4, 2.1, 5.6):
        K.band(g, (cx, cy, 0), r, z, .07, PAINTED, segments=12)
    # Timber-lagged insulation jacket round the hot middle section, strapped.
    K.revolve(g, (cx, cy, 2.5), [(r + .045, 0), (r + .045, 2.2)], FORGED, segments=12, phase=math.pi / 24)
    for z in (2.7, 3.6, 4.5):
        K.band(g, (cx, cy, 0), r + .045, z, .07, IRON, segments=12, phase=math.pi / 24)
    # One ring platform on a whole layer, knee brackets, rail open at the ladder.
    z = PLATFORM_Z
    P.annulus(g, (cx, cy), r - .1, .98, z - .08, z, IRON, segments=16)
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        g.beam((cx + math.cos(a) * r, cy + math.sin(a) * r, z - .6),
               (cx + math.cos(a) * .9, cy + math.sin(a) * .9, z - .1), .06, mat=IRON)
    P.ring_rail(g, (cx, cy), .94, z, height=.6, posts=12, gap=(-math.pi * .14, math.pi * .14))
    K.ladder(g, cx + .98, cy, 0, z + .6, face='right', width=.3, cage=False)
    # Side-draw nozzles and a reflux line down the right side.
    for zz, a in ((1.8, -.3), (3.2, .4), (4.1, -.7)):
        px, py = cx + math.cos(a) * r, cy + math.sin(a) * r
        P.pipe(g, [(px - .02, py, zz), (cx + math.cos(a) * (r + .26), cy + math.sin(a) * (r + .26), zz)], .05)
    P.pipe(g, [(cx + r + .26, cy + .25, 4.1), (cx + r + .26, cy + .25, .7), (cx + r - .05, cy + .25, .7)], .045)
    P.gauge(g, cx - .2, cy - r - .015, 1.75, 'front', .08)
    # Bolted manway facing the yard.
    a = 1.3 * math.pi
    ux, uy = math.cos(a), math.sin(a)
    at = lambda d: (cx + ux * d, cy + uy * d, 1.3)
    P.tube(g, at(r - .08), at(r + .08), .16, IRON, segments=8)
    P.tube(g, at(r + .08), at(r + .13), .2, PAINTED, segments=8)
    # Vapour line: out of the crown and down to the cooler on the hall roof.
    vz = COLUMN_TOP + .5
    vx = cx - .7
    P.pipe(g, [(cx, cy, COLUMN_TOP + .2), (cx, cy, vz), (vx, cy, vz), (vx, cy, ROOF_Z + .3),
               (2.92, cy, ROOF_Z + .3)], .08)
    for zz in (3.0, 4.4):
        blk(g, vx + .05, cy - .04, zz - .04, cx - r + .02, cy + .04, zz + .04, IRON)
    # Beacon on a short mast at the crown.
    blk(g, cx + .22, cy + .2, COLUMN_TOP, cx + .29, cy + .27, COLUMN_TOP + .9, IRON)
    pivot = K.beacon(g, cx + .255, cy + .235, COLUMN_TOP + .9)
    parts.append((K.beacon_shutter(*pivot, 'ChemicalWorks.Beacon'), 'SPIN_Z', 2))


# ---------------------------------------------------------------- flare

def flare(g, parts):
    """Short flare stack standing on the hall roof's back-right corner."""
    cx, cy = FLARE
    z = ROOF_Z + 1.0
    blk(g, cx - .08, cy - .08, z - .02, cx + .08, cy + .08, z + .2, CONCRETE)   # inside the roof's edges
    tip = 5.3
    K.revolve(g, (cx, cy, z + .2), [(.07, 0), (.07, tip - z - .2)], IRON, segments=12)
    K.revolve(g, (cx, cy, tip), [(.08, 0), (.13, .08), (.13, .3), (.11, .34)], IRON, segments=12)
    g.ring((cx, cy, tip + .26), .14, .035, .05, BRASS, 'Z', 12)
    for zz in (3.8, 4.6):
        K.band(g, (cx, cy, 0), .07, zz, .05, PAINTED, segments=12)
    flame = Geometry('ChemicalWorks.FlareFlame', (cx, cy, tip + .34))
    K.revolve(flame, (cx, cy, tip + .34), [(.1, 0), (.12, .1), (.07, .32), (.03, .48), (0, .56)], GLOW, segments=8)
    parts.append((flame, 'FLAME', 0))
    K.emitter(g, 'smoke', cx, cy, tip + .34 + .56, .12)


def build(g, parts):
    hall(g)
    roof_plant(g, parts)
    reactors(g, parts)
    column(g, parts)
    flare(g, parts)
