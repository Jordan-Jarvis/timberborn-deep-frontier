"""DeepMine: late-game deep-ore shaft mine (Iron Teeth, Deep Frontier).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the east ore yard (track, ore tubs and stockpile) and the post lamps.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "the mines need to have a lot of tlc", one layer per floor, flat
roofs): 10x11x16 -> 7x6x7, inside the old footprint with the same origin,
door, native entrance and Deep Ore Vein core (tiles x 2-6, y 1-5), so saved
mines and map placements keep their vein. Removed: the 13-layer open lattice
headframe (zigzag bracing, gusset plates, raked lattice backstays and their
struts, maintenance gantry, caged ladder), the separate winding-drum shed with
its lean-to, the two-storey monitor-roofed engine house, the raised ore bin on
stilts with its tipple deck and head-house, and the gabled bath house.

Shrunk again 2026-11-01 (user: "the thing that sits on top of the
permanent veins and the limestone and sandstone all need to fit in 5x5"):
7x6x7 -> 5x5x6, exactly the Deep Ore Vein's 5x5 core, so GRID_ORIGIN moved
to the core's corner (artwork 2, 1). The shaft house (tiles 4..7 x 1..6)
carries a headframe one layer lower (head deck on layer 4, wind 1.5); the
brick lamp house with the door is on tiles 2..4 x 1..3, the boarded ore bin
beside the shaft house now stands on the ground behind it (the chute leaves
the headframe's left plating), and the bath-house annex is on tiles 2..4 x
4..6. Every ground cell is building mass over the vein (all 25 are Top on
Ground, as under vanilla EfficientMine, the doorstep included). Saved mines
are moved onto their vein at load (MineFootprintSaveMigration.cs).

HERO: a compact plated steel headframe on a low concrete shaft house: solid
corrugated sides and back, open front showing both skips riding their timber
guides, two box-girder backstays and two counter-rotating sheave wheels on the
head deck. The winding drum and flywheel sit in the open on the shaft-house
deck behind it, their ropes running up to the sheaves.

Ore flow: the skips tip into a chute through the headframe's side, into a
boarded ore bin beside the shaft house.

Parts: low concrete shaft house (one layer) carrying the steel deck; brick
lamp house with the door under a front-gabled roof of native barracks roof
planks; one-layer bath-house annex with a timber plank deck and its chimney
rising from the ground up its back wall (roof variety, no roof vents: user,
2026-10-30). No clutter on buildable space (user, 2026-10-30): every ground
cell holds building mass and the flat roofs stay clear.

Animated (8): two sheave wheels, two skips, their two hoist ropes (stretch),
winding drum and engine flywheel.
"""
from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK
import lategame_mining_parts as P
from lategame_mining_parts import bx

IDENT = 'DeepMine'
# Artwork keeps the old frame (vein core on tiles x 2..6, y 1..5); the
# footprint is exactly that core, so its (0, 0) corner is artwork (2, 1).
FOOTPRINT = (5, 5)
GRID_ORIGIN = (2, 1)
HEIGHT = 6
HERO = 'Compact plated steel headframe on a low brick shaft house, both skips in its open front, twin sheaves on top'
FRAME_END = 121

BASE = 1.0                     # shaft-house deck layer
BASE_ON = BASE + .012          # top of the deck grating bars
LEGS_X = (4.3, 6.7)
LEGS_Y = (1.5, 3.3)
TOP = 4.0                      # head deck layer
SHAFT_Y = 2.4
WHEEL_R = .5
WHEEL_Y = SHAFT_Y + WHEEL_R
WHEEL_Z = TOP + .62
SKIPS = (4.9, 6.1)
TRAVEL = 1.5
SKIP_LOW = .2                  # inside the shaft house at the bottom of the wind
SKIP_H = 1.65                  # skip bottom to rope shackle
DRUM = (5.2, 4.7, BASE + .66)
GIRTS = (2.1, 3.1)
BIN = (2.15, 3.85, 3.12, 3.88, 2.4)   # x0, x1, y0, y1, top


# ------------------------------------------------------------------ shaft house

def shaft_house(g):
    """Low brick shaft house (concrete base course and pilasters) on tiles 4..7 x 1..6 (over the vein); its roof is the deck."""
    small = lambda u: (u, .52, 'factory', .4)
    P.concrete_house(g, 4.12, 6.95, 1.05, 5.95, BASE - .16, base=.2, pitch=1.3, record_doors=False, wall=P.BRICK,
                     windows={'front': [small(4.8), small(6.3)],
                              'right': [small(1.66), small(2.89), small(4.11), small(5.34)],
                              'back': [small(4.8), small(6.3)]})
    bx(g, 4.1, 7.0, 1.0, 6.0, BASE - .16, BASE - .08, CONCRETE)
    P.deck(g, 4.1, 7.0, 1.0, 6.0, BASE)   # an open platform edge to edge (user, 2026-10-31)
    # Shaft cover plate the skips pass through.
    bx(g, 4.5, 6.5, 1.95, 2.85, BASE_ON, BASE_ON + .02, IRON)


# ------------------------------------------------------------------ headframe

def headframe(g):
    for x in LEGS_X:
        for y in LEGS_Y:
            P.column(g, x, y, BASE_ON, TOP - .08, .24)
    # Corrugated plating on the sides and back; the front stays open.
    z0, z1 = BASE_ON + .1, TOP - .1
    bx(g, LEGS_X[0] - .03, LEGS_X[0] + .03, LEGS_Y[0] + .05, LEGS_Y[1] - .05, z0, z1, PAINTED)
    bx(g, LEGS_X[1] - .03, LEGS_X[1] + .03, LEGS_Y[0] + .05, LEGS_Y[1] - .05, z0, z1, PAINTED)
    bx(g, LEGS_X[0] - .05, LEGS_X[1] + .05, LEGS_Y[1] - .03, LEGS_Y[1] + .03, z0, z1, PAINTED)
    # Steel girts outside the plating; the back ones 30 mm higher.
    for z in GIRTS:
        bx(g, LEGS_X[0] - .1, LEGS_X[0] - .03, LEGS_Y[0], LEGS_Y[1], z - .06, z + .06, IRON)
        bx(g, LEGS_X[1] + .03, LEGS_X[1] + .1, LEGS_Y[0], LEGS_Y[1], z - .06, z + .06, IRON)
        bx(g, LEGS_X[0], LEGS_X[1], LEGS_Y[1] + .03, LEGS_Y[1] + .1, z - .03, z + .09, IRON)
    # Front lintel under the head deck.
    bx(g, LEGS_X[0], LEGS_X[1], LEGS_Y[0] - .1, LEGS_Y[0], TOP - .35, TOP - .2, IRON)
    # Timber skip guides on steel buntons to the back plating.
    for sx in SKIPS:
        for gx in (sx - .42, sx + .42):
            bx(g, gx - .04, gx + .04, SHAFT_Y - .05, SHAFT_Y + .05, BASE_ON + .02, TOP - .08, WOOD)
            for z in (1.9, 2.9):
                bx(g, gx - .03, gx + .03, SHAFT_Y + .05, LEGS_Y[1] - .03, z - .04, z + .04, IRON)
    # Open head deck, no rails (user, 2026-10-31: "lets remove the railings").
    P.deck(g, LEGS_X[0] - .25, LEGS_X[1] + .25, LEGS_Y[0] - .25, LEGS_Y[1] + .2, TOP)
    zd = TOP + .012
    for sx in SKIPS:
        for px in (sx - .3, sx + .3):
            bx(g, px - .06, px + .06, WHEEL_Y - .18, WHEEL_Y + .18, zd, WHEEL_Z + .07, PAINTED)
            bx(g, px - .08, px + .08, WHEEL_Y - .13, WHEEL_Y + .13, WHEEL_Z + .07, WHEEL_Z + .15, BRASS)
    # Box-girder backstays down to the deck beside the winding drum.
    for x in LEGS_X:
        bx(g, x - .2, x + .2, 5.45, 5.85, BASE_ON, BASE_ON + .15, IRON)
        g.beam((x, LEGS_Y[1] + .05, TOP - .25), (x, 5.65, BASE_ON + .15), .22, .22, PAINTED)
    # Ladder up the right plating from the deck, and a work lamp in the open front.
    K.ladder(g, LEGS_X[1] + .03, SHAFT_Y, BASE_ON, TOP, face='right', width=.3, cage=False)
    K.lamp(g, (SKIPS[0] + SKIPS[1]) / 2, LEGS_Y[1] - .03, 2.9, face='front')
    # Dump chute from the skip tipping point out through the left plating
    # down into the ore bin beside the shaft house.
    x0, x1, y0, y1, top = BIN
    P.slab_quad(g, [(4.3, 2.95, 3.05), (4.3, 3.3, 3.05), (3.7, 3.3, top + .08), (3.7, 2.95, top + .08)],
                (-.6, 0, .9), .06, FORGED)
    for y in (2.92, 3.33):
        P.slab_quad(g, [(4.3, y, 3.0), (3.7, y, top + .03), (3.7, y, top + .28), (4.3, y, 3.25)],
                    (0, -1 if y < 3.1 else 1, 0), .05, PAINTED)


def sheave(name, x, turns):
    w = P.spoked_wheel(name, (x, WHEEL_Y, WHEEL_Z), WHEEL_R, 'X', rim_t=.07, rim_w=.13, spokes=8,
                       hub_r=.11, double=True)
    w.cylinder((x, WHEEL_Y, WHEEL_Z), .055, .56, IRON, 'X', 12)
    return w, 'SPIN_X', turns


def skip(name, x, low):
    bottom = SKIP_LOW if low else SKIP_LOW + TRAVEL
    s = Geometry(name, (x, SHAFT_Y, bottom + .6))
    y = SHAFT_Y
    bx(s, x - .32, x + .32, y - .36, y + .36, bottom, bottom + 1.2, FORGED)
    for z in (bottom + .12, bottom + 1.08):
        bx(s, x - .345, x + .345, y - .385, y + .385, z - .05, z + .05, PAINTED)
    for xa, xb in ((x - .38, x - .32), (x + .32, x + .38)):
        for za, zb in ((.2, .45), (.8, .98)):
            bx(s, xa, xb, y - .05, y + .05, bottom + za, bottom + zb, IRON)
    for sx in (-1, 1):
        s.beam((x + sx * .28, y, bottom + 1.2), (x + sx * .06, y, bottom + SKIP_H - .08), .06, mat=IRON)
    bx(s, x - .1, x + .1, y - .06, y + .06, bottom + SKIP_H - .12, bottom + SKIP_H, PAINTED)
    for i in range(5):
        s.rock((x - .18 + i * .09, y + (-.1 if i % 2 else .12), bottom + 1.2 + .01 * i), (.16 + i * .01, .15, .12),
               IRON, 40 + i)
    return s


def rope(name, x, low):
    top = WHEEL_Z
    bottom = (SKIP_LOW if low else SKIP_LOW + TRAVEL) + SKIP_H
    r = Geometry(name, (x, SHAFT_Y, top))
    bx(r, x - .02, x + .02, SHAFT_Y - .02, SHAFT_Y + .02, bottom - .04, top, IRON)
    return r


# ------------------------------------------------------------------ winding engine

def winding_engine(g, parts):
    cx, cy, cz = DRUM
    for x0 in (4.45, 5.8):
        bx(g, x0, x0 + .15, cy - .25, cy + .25, BASE_ON, cz + .08, CONCRETE)
        bx(g, x0 - .02, x0 + .17, cy - .14, cy + .14, cz + .08, cz + .16, BRASS)
    d = Geometry('WindingDrum', DRUM)
    d.cylinder(DRUM, .4, 1.2, IRON, 'X', 16)
    for x in (cx - .6, cx, cx + .6):
        d.cylinder((x, cy, cz), .55, .08, PAINTED, 'X', 16)
    for x in (cx - .3, cx + .3):
        for k in range(2):
            d.ring((x - .08 + k * .16, cy, cz), .43, .04, .11, IRON, 'X', 16)
    d.cylinder(DRUM, .1, 1.7, IRON, 'X', 12)
    for x in (cx - .6, cx + .6):
        bx(d, x - .035, x + .035, cy - .05, cy + .05, cz + .47, cz + .57, BRASS)
    parts.append((d, 'SPIN_X', -1))
    # Hoist ropes from the drum to the back of the sheaves (A over the top, B from below).
    g.beam((SKIPS[0], cy, cz + .44), (SKIPS[0], WHEEL_Y + WHEEL_R * .94, WHEEL_Z + WHEEL_R * .3), .04, mat=IRON)
    g.beam((SKIPS[1], cy - .44, cz), (SKIPS[1], WHEEL_Y + WHEEL_R * .94, WHEEL_Z - WHEEL_R * .3), .04, mat=IRON)
    # Flywheel on the drum shaft's extension, between concrete bearing blocks.
    g.cylinder((6.2, cy, cz), .09, .7, IRON, 'X', 12)
    for xa, xb in ((6.05, 6.14), (6.62, 6.71)):
        bx(g, xa, xb, cy - .26, cy + .26, BASE_ON, cz + .06, CONCRETE)
    fly = P.spoked_wheel('Flywheel', (6.38, cy, cz), .5, 'X', rim_t=.12, rim_w=.2, spokes=6, groove=False,
                         hub_r=.14, mat=IRON, hub_mat=PAINTED)
    parts.append((fly, 'SPIN_X', 2))
    # Steam cylinder and bed between the backstays, behind the drum.
    bx(g, 4.75, 5.85, 5.4, 5.9, BASE_ON, BASE_ON + .36, PAINTED)
    g.cylinder((5.3, 5.65, BASE_ON + .56), .18, .45, PAINTED, 'Y', 12)


# ------------------------------------------------------------------ ore bin

def ore_bin(g):
    """Boarded ore bin beside the shaft house, fed by the chute."""
    x0, x1, y0, y1, top = BIN
    core = (x0, x1, y0, y1)
    bx(g, x0, x1, y0, y1, 0, top, PLANK)
    for face in ('front', 'back', 'left'):
        P.boards(g, face, core, 0, top, width=.26, t=.06, mat=PLANK)
    for z in (.5, 1.3, 2.05):
        bx(g, x0 - .1, x1 + .02, y0 - .1, y0 - .06, z - .06, z + .06, IRON)
        bx(g, x0 - .1, x1 + .02, y1 + .06, y1 + .1, z - .06, z + .06, IRON)
        bx(g, x0 - .1, x0 - .06, y0 - .06, y1 + .06, z - .04, z + .08, IRON)
    # Ore lumps rest on the bin's top (lowest ring clears it; see the
    # 2026-10-30 hidden-geometry fix).
    for i in range(6):
        g.rock((2.5 + (i % 3) * .45, 3.32 + (i // 3) * .36, top + .066 + .004 * i), (.22, .2, .14), IRON, 70 + i)


# ------------------------------------------------------------------ lamp house and bath house

def lamp_house(g):
    # Brick hall on tiles 2..4 x 1..3, its right wall on the tile line the
    # shaft house stands beside (from 4.12). The core front at 1.12 puts the
    # native portal's face on the footprint edge y = 1.
    P.hall(g, 2.05, 4.0, 1.12, 2.95, 1.84, plinth=.5, doors=[3.5], pitch=1.0,
           windows={'front': [(2.5, 1.15, 'grand', .55)],
                    'left': [(1.59, 1.15, 'grand', .55), (2.48, 1.15, 'grand', .55)]})
    K.lamp(g, 2.92, 1.12, 1.15, face='front')
    # A real front-gabled roof in the native barracks roof planks (roof variety,
    # user 2026-10-30: "some buildings can have actual roofs").
    P.plank_gable(g, 2.05, 4.0, 1.12, 2.95, 1.84, 2.55, ridge_axis='Y', overhang=.05, seed=21)


def bath_house(g):
    """One-layer annex on tiles 2..4 x 4..6 with its chimney in the back corner."""
    small = lambda u: (u, .52, 'factory', .4)
    # Core ends at 3.93 so its corner pilasters meet the shaft house's on an edge, not a face.
    P.concrete_house(g, 2.05, 3.93, 4.05, 5.95, BASE - .16, base=.2, pitch=1.3, record_doors=False, wall=P.BRICK,
                     windows={'left': [small(4.6), small(5.4)], 'back': [small(2.8)]})
    # Timber plank deck on the annex roof (roof variety, user 2026-10-30).
    P.plank_deck(g, 2.0, 4.0, 4.0, 6.0, BASE, seed=23)
    # The chimney rises from the ground up the back wall, not from the roof
    # ("no roof vents", user 2026-10-30), in the deck cell's outer band.
    K.wall_stack(g, 2.4, 5.84, K.GROUND_SINK, BASE + 2.6 - K.GROUND_SINK, emits='smoke', r=.11, bands=3)


def build(g, parts):
    shaft_house(g)
    headframe(g)
    parts.append(sheave('SheaveA', SKIPS[0], 2))
    parts.append(sheave('SheaveB', SKIPS[1], -2))
    parts.append((skip('SkipA', SKIPS[0], True), 'CUSTOM_SKIP', TRAVEL))
    parts.append((skip('SkipB', SKIPS[1], False), 'CUSTOM_SKIP', -TRAVEL))
    parts.append((rope('RopeA', SKIPS[0], True), 'CUSTOM_ROPE', TRAVEL))
    parts.append((rope('RopeB', SKIPS[1], False), 'CUSTOM_ROPE', -TRAVEL))
    winding_engine(g, parts)
    ore_bin(g)
    lamp_house(g)
    bath_house(g)


KEYS = ((0.0, 0.0), (.42, 1.0), (.5, 1.0), (.92, 0.0), (1.0, 0.0))


def animate(obj, kind, value, frame_end):
    """Counterbalanced winding: skips and their ropes share one linear timeline."""
    span = frame_end - 1
    if kind == 'CUSTOM_SKIP':
        base = obj.location.z
        for f, t in KEYS:
            obj.location.z = base + value * t
            obj.keyframe_insert(data_path='location', index=2, frame=1 + span * f)
        obj.location.z = base
    elif kind == 'CUSTOM_ROPE':
        name = obj.name
        low = name.endswith('A')
        bottom = (SKIP_LOW if low else SKIP_LOW + TRAVEL) + SKIP_H
        length = WHEEL_Z - bottom + .04
        for f, t in KEYS:
            obj.scale = (1, 1, (length - value * t) / length)
            obj.keyframe_insert(data_path='scale', frame=1 + span * f)
    else:
        raise ValueError('Unknown custom animation ' + kind)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
