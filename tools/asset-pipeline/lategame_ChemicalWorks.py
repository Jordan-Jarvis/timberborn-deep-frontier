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

Second shrink 2026-11-01 (a YouTuber called the late-game buildings
"massive"; user: "we need to shrink the buildings down even more"):
5x5x8 -> 4x3x5, inside the old footprint with the same origin, door and
native entrance (cell 1, -1). Every new block is one the old works occupied
or one over its solid machinery: the hall keeps the old two-layer roof over
the front rows, the reactors keep their column (one tile left), and the
column now rises from the back row's tile 1, over the old cooler house's
fan cell, where nothing of the player's could stand. Removed: the cooler
house on the hall roof (a one-tile cooler house with two small fans now
stands in the back row), the column's knee-braced platform (a small ring
remains), two layers of column height.

HERO: a riveted fractionating column with a small ring platform and a
      ladder, its vapour line dropping to a fin-fan cooler house, beside a
      short flare stack with a live flame.
ROOF: flat corrugated-metal roof on the reactor hall, open edge to edge,
      every cell placeable; the cooler house's flat steel-plate top carries
      its two fans. No roof vents.

Plan (4 x 3 tiles): the reactor hall on tiles 0..3 x 0..2 (door front-left);
three agitated reactors in a row on a concrete apron along its right wall
(tile column 3); the back row: the flare stack, the column, the cooler
house and the third reactor.

Animated (6, names unchanged): three agitator couplings, two cooler fans,
the flare flame, the column beacon.
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
FOOTPRINT = (4, 3)
HEIGHT = 5
FRAME_END = 121
HERO = ('A riveted fractionating column with a ring platform and a ladder, its vapour line dropping to a '
        'fin-fan cooler house, beside a flare stack with a live flame.')

DOOR_X = 1.5
HALL = (0.0, 0.0, 3.0, 2.0)      # two storeys on whole tiles
ROOF_Z = 2.0
COLUMN = (1.5, 2.48)
COLUMN_R = .36
COLUMN_TOP = 4.2
PLATFORM_Z = 3
REACTOR_X = 3.5
REACTORS_Y = (.5, 1.5, 2.5)
REACTOR_R = .33
COOLER = (2.06, 2.08, 2.94, 2.94)
FLARE = (.5, 2.5)


# ---------------------------------------------------------------- reactor hall

def hall(g):
    x0, y0, x1, y1 = HALL
    Q.storey_block(g, x0, y0, x1, y1, 2, infill=FORGED, frame=IRON, door=DOOR_X, door_id='Entrance',
                   roof_mat=PAINTED, slab_mat=IRON, roof_boards=True,
                   ground_windows={'left': [(1.0, .6, 'factory')]},
                   windows={'front': [(.5, 1.5, .55, 'factory'), (1.5, 1.5, .55, 'factory'),
                                      (2.5, 1.5, .55, 'factory')],
                            'left': [(y + .5, 1.5, .55, 'factory') for y in range(2)],
                            'back': [(.5, 1.5, .55, 'factory'), (2.5, 1.5, .55, 'factory')]})
    K.lamp(g, DOOR_X - .66, y0 - .01, .8, face='front')
    # Instrument board beside the door: gauges and indicator lights.
    blk(g, 2.4, y0 - .06, .32, 2.8, y0 - .004, .78, PAINTED)
    for gx in (2.5, 2.7):
        P.gauge(g, gx, y0 - .06, .64, 'front', .07)
    for k, lx in enumerate((2.48, 2.6, 2.72)):
        g.cylinder((lx, y0 - .075, .42), .02, .03, CYAN if k % 2 == 0 else IRON, 'Y', 8)


def roof_plant(g, parts):
    """Fin-fan cooler house on the back row's tile 2: two layers of louvred
    forged sides with a flat steel-plate top on layer 2 carrying the two fans
    side by side."""
    x0, y0, x1, y1 = COOLER
    top = ROOF_Z
    C.podium(g, x0, y0, x1, y1, .2, joints=False)
    blk(g, x0 + .04, y0 + .04, .2, x1 - .04, y1 - .04, top - .1, FORGED)
    for x, y in ((x0 + .04, y0 + .04), (x1 - .04, y0 + .04), (x1 - .04, y1 - .04), (x0 + .04, y1 - .04)):
        blk(g, x - .05, y - .05, .2, x + .05, y + .05, top - .1, IRON)
    for k in range(5):
        zz = .45 + k * .26
        blk(g, x0 + .1, y0 + .01, zz, x1 - .1, y0 + .04, zz + .06, IRON)
        blk(g, x1 - .04, y0 + .1, zz, x1 - .01, y1 - .1, zz + .06, IRON)
    Q.flat_roof(g, x0, y0, x1, y1, top, overhang=0.0, mat=IRON, slab_mat=IRON, boards=True)
    for i, x in enumerate((2.28, 2.72)):
        cy = 2.51
        P.hoop(g, (x, cy, top + .1), .2, .03, .18, IRON, segments=12)
        P.hoop(g, (x, cy, top + .2), .215, .04, .04, PAINTED, segments=12)
        blk(g, x - .17, cy - .025, top, x + .17, cy + .025, top + .04, IRON)
        g.cylinder((x, cy, top + .08), .04, .08, IRON, 'Z', 10)
        parts.append((P.fan(f'ChemicalWorks.CoolerFan{i + 1}', x, cy, top + .13, .17, blades=5),
                      'SPIN_Z', 4 if i else -4))


# ---------------------------------------------------------------- reactors

def reactors(g, parts):
    """Three agitated reactors in a row along the hall's right wall, on a
    concrete apron that fills tile column 3; manways face outward."""
    base = .3
    C.podium(g, 3.06, 0.0, 4.0, 3.0, base, joints=False, foot=False)   # the hall's foot course meets it
    x = REACTOR_X
    for i, y in enumerate(REACTORS_Y):
        top = K.tank(g, x, y, base, REACTOR_R, 1.15, mat=PAINTED, bands=2, roof='dome')
        dome_top = top + (REACTOR_R + .03) * .45
        mz = base + .65
        g.cylinder((x + REACTOR_R + .03, y, mz), .13, .06, IRON, 'X', 12)
        P.disc(g, (x + REACTOR_R + .065, y, mz), .15, .03, BRASS, axis='X', segments=12)
        P.gauge(g, x + REACTOR_R - .05, y - .2, base + 1.0, 'right', .06)
        # Agitator drive: saddle, gearbox, spinning coupling, motor.
        sz = dome_top - .02
        blk(g, x - .18, y - .22, sz, x + .18, y + .22, sz + .07, IRON)
        blk(g, x - .12, y - .12, sz + .07, x + .12, y + .12, sz + .28, PAINTED)
        P.motor(g, (x, y, sz + .68), .11, .3, axis='Z')
        c = Geometry(f'ChemicalWorks.Agitator{i + 1}', (x, y, sz + .4))
        P.lathe(c, (x, y, sz + .4), [(.045, -.11), (.045, -.05), (.12, -.05), (.12, -.02),
                                     (.045, -.02), (.045, .02), (.12, .02), (.12, .05),
                                     (.045, .05), (.045, .11)], IRON, segments=8)
        for k in range(4):
            a = k * math.pi / 2
            c.box((x + math.cos(a) * .085, y + math.sin(a) * .085, sz + .4), (.035, .035, .12), BRASS)
        parts.append((c, 'SPIN_Z', 3))
        # Vapour nozzle from the dome across to the header on the hall wall.
        if i < 2:
            P.pipe(g, [(x - .1, y + .2, dome_top - .1), (x - .1, y + .2, 1.75), (3.08, y + .2, 1.75)], .045,
                   flanges=False)
    # Vapour header along the hall's right wall, into its upper storey.
    P.pipe(g, [(3.08, REACTORS_Y[0] + .2, 1.75), (3.08, REACTORS_Y[1] + .2, 1.75)], .06, flanges=False)


# ---------------------------------------------------------------- column

def column(g, parts):
    cx, cy = COLUMN
    r = COLUMN_R
    # Octagonal concrete footing and flared steel skirt.
    K.revolve(g, (cx, cy, 0), [(.48, 0), (.48, .25), (.43, .32)], CONCRETE, segments=8, phase=math.pi / 8)
    K.revolve(g, (cx, cy, .32), [(r + .07, 0), (r + .07, .22), (r, .4)], IRON, segments=12)
    K.revolve(g, (cx, cy, .72), [(r, 0), (r, COLUMN_TOP - .72)], IRON, segments=12, cap_bottom=False, cap_top=False)
    K.dome(g, (cx, cy, COLUMN_TOP), r + .025, IRON, segments=12, squash=.55)
    for z in (1.1, 1.6, 3.85):
        K.band(g, (cx, cy, 0), r, z, .06, PAINTED, segments=12)
    # Timber-lagged insulation jacket round the hot middle section, strapped.
    K.revolve(g, (cx, cy, 1.9), [(r + .04, 0), (r + .04, 1.0)], FORGED, segments=12, phase=math.pi / 24)
    for z in (2.1, 2.7):
        K.band(g, (cx, cy, 0), r + .04, z, .06, IRON, segments=12, phase=math.pi / 24)
    # One small open ring platform on layer 3 (no rail), the ladder up its back.
    z = PLATFORM_Z
    P.annulus(g, (cx, cy), r - .08, .5, z - .07, z, IRON, segments=16)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        g.beam((cx + math.cos(a) * r, cy + math.sin(a) * r, z - .4),
               (cx + math.cos(a) * .44, cy + math.sin(a) * .44, z - .08), .05, mat=IRON)
    K.ladder(g, cx, cy + .44, 0, z + .5, face='back', width=.26, cage=False)
    P.gauge(g, cx - .18, cy - r - .015, 1.4, 'front', .07)
    # Vapour line: out of the crown and down to the cooler house.
    vz = COLUMN_TOP + .4
    P.pipe(g, [(cx, cy, COLUMN_TOP + .15), (cx, cy, vz), (1.94, cy, vz), (1.94, cy, ROOF_Z + .6),
               (2.28, cy, ROOF_Z + .6), (2.28, cy, ROOF_Z + .42)], .065)
    # Beacon on a short mast at the crown.
    blk(g, cx - .25, cy - .04, COLUMN_TOP, cx - .19, cy + .02, COLUMN_TOP + .45, IRON)
    pivot = K.beacon(g, cx - .22, cy - .01, COLUMN_TOP + .45)
    parts.append((K.beacon_shutter(*pivot, 'ChemicalWorks.Beacon'), 'SPIN_Z', 2))


# ---------------------------------------------------------------- flare

def flare(g, parts):
    """Short flare stack on its own footing in the back row's tile 0."""
    cx, cy = FLARE
    K.revolve(g, (cx, cy, 0), [(.22, 0), (.22, .25), (.18, .3)], CONCRETE, segments=8, phase=math.pi / 8)
    tip = 2.3
    K.revolve(g, (cx, cy, .3), [(.08, 0), (.08, tip - .3)], IRON, segments=12)
    K.revolve(g, (cx, cy, tip), [(.09, 0), (.13, .07), (.13, .25), (.11, .29)], IRON, segments=12)
    g.ring((cx, cy, tip + .22), .14, .035, .05, BRASS, 'Z', 12)
    for zz in (1.2, 1.9):
        K.band(g, (cx, cy, 0), .08, zz, .05, PAINTED, segments=12)
    flame = Geometry('ChemicalWorks.FlareFlame', (cx, cy, tip + .29))
    K.revolve(flame, (cx, cy, tip + .29), [(.09, 0), (.1, .08), (.06, .25), (.025, .36), (0, .42)], GLOW, segments=8)
    parts.append((flame, 'FLAME', 0))
    K.emitter(g, 'smoke', cx, cy, tip + .29 + .42, .1)


def build(g, parts):
    hall(g)
    roof_plant(g, parts)
    reactors(g, parts)
    column(g, parts)
    flare(g, parts)
