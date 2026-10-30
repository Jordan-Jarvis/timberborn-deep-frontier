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

HERO: a compact plated steel headframe on a low concrete shaft house: solid
corrugated sides and back, open front showing both skips riding their timber
guides, two box-girder backstays and two counter-rotating sheave wheels on the
head deck. The winding drum and flywheel sit in the open on the shaft-house
deck behind it, their ropes running up to the sheaves.

Ore flow: the skips tip into a chute through the headframe's side, into a
boarded ore bin on the deck.

Parts: low concrete shaft house (one layer) carrying the steel deck; brick
lamp house with the door (flat roof, parapet); one-layer bath-house annex with
its chimney. No clutter on buildable space (user, 2026-10-30): the front strip
of the footprint is open ground and the flat roofs stay clear.

Animated (8): two sheave wheels, two skips, their two hoist ropes (stretch),
winding drum and engine flywheel.
"""
from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK
import lategame_mining_parts as P
from lategame_mining_parts import bx

IDENT = 'DeepMine'
FOOTPRINT = (7, 6)
HEIGHT = 7
HERO = 'Compact plated steel headframe on a low concrete shaft house, both skips in its open front, twin sheaves on top'
FRAME_END = 121

BASE = 1.0                     # shaft-house deck layer
BASE_ON = BASE + .012          # top of the deck grating bars
LEGS_X = (3.3, 5.7)
LEGS_Y = (1.5, 3.3)
TOP = 5.0                      # head deck layer
SHAFT_Y = 2.4
WHEEL_R = .6
WHEEL_Y = SHAFT_Y + WHEEL_R
WHEEL_Z = TOP + .72
SKIPS = (3.9, 5.1)
TRAVEL = 2.6
SKIP_LOW = .2                  # inside the shaft house at the bottom of the wind
SKIP_H = 1.65                  # skip bottom to rope shackle
DRUM = (4.5, 4.7, BASE + .68)
GIRTS = (2.4, 3.5)


# ------------------------------------------------------------------ shaft house

def shaft_house(g):
    """Low concrete shaft house on tiles 3..7 x 1..6 (over the vein); its roof is the deck."""
    small = lambda u: (u, .52, 'factory', .4)
    P.concrete_house(g, 3.05, 6.95, 1.05, 5.95, BASE - .16, base=.2, pitch=1.3, record_doors=False,
                     windows={'front': [small(3.72), small(5.0), small(6.28)],
                              'right': [small(1.66), small(2.89), small(4.11), small(5.34)],
                              'back': [small(3.72), small(5.0), small(6.28)]})
    bx(g, 3.0, 7.0, 1.0, 6.0, BASE - .16, BASE - .08, CONCRETE)
    P.deck(g, 3.0, 7.0, 1.0, 6.0, BASE, rails=('front', 'back', 'right'))
    # Shaft cover plate the skips pass through.
    bx(g, 3.5, 5.5, 1.95, 2.85, BASE_ON, BASE_ON + .02, IRON)


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
            for z in (2.2, 3.4, 4.5):
                bx(g, gx - .03, gx + .03, SHAFT_Y + .05, LEGS_Y[1] - .03, z - .04, z + .04, IRON)
    # Head deck, sheave pedestals and bearing caps.
    # No back rail: the hoist ropes come in over the back edge to the sheaves.
    P.deck(g, LEGS_X[0] - .25, LEGS_X[1] + .25, LEGS_Y[0] - .25, LEGS_Y[1] + .2, TOP,
           rails=('front', 'left', 'right'), gaps={'left': [(SHAFT_Y - .2, SHAFT_Y + .2)]})
    zd = TOP + .012
    for sx in SKIPS:
        for px in (sx - .3, sx + .3):
            bx(g, px - .06, px + .06, WHEEL_Y - .2, WHEEL_Y + .2, zd, WHEEL_Z + .08, PAINTED)
            bx(g, px - .08, px + .08, WHEEL_Y - .14, WHEEL_Y + .14, WHEEL_Z + .08, WHEEL_Z + .16, BRASS)
    # Box-girder backstays down to the deck behind the winding drum.
    for x in LEGS_X:
        bx(g, x - .2, x + .2, 5.45, 5.85, BASE_ON, BASE_ON + .15, IRON)
        g.beam((x, LEGS_Y[1] + .05, TOP - .25), (x, 5.65, BASE_ON + .15), .22, .22, PAINTED)
    # Ladder up the left plating from the deck, and a work lamp in the open front.
    K.ladder(g, LEGS_X[0] - .03, SHAFT_Y, BASE_ON, TOP, face='left', width=.34, cage=False)
    K.lamp(g, (SKIPS[0] + SKIPS[1]) / 2, LEGS_Y[1] - .03, 3.6, face='front')
    # Dump chute from the skip tipping point through the right plating to the ore bin.
    P.slab_quad(g, [(5.58, 2.15, 3.9), (5.58, 2.65, 3.9), (6.4, 2.65, 3.15), (6.4, 2.15, 3.15)],
                (.75, 0, .82), .06, FORGED)
    for y in (2.1, 2.7):
        P.slab_quad(g, [(5.58, y, 3.85), (6.4, y, 3.1), (6.4, y, 3.35), (5.58, y, 4.1)],
                    (0, -1 if y < 2.4 else 1, 0), .05, PAINTED)


def sheave(name, x, turns):
    w = P.spoked_wheel(name, (x, WHEEL_Y, WHEEL_Z), WHEEL_R, 'X', rim_t=.08, rim_w=.14, spokes=8,
                       hub_r=.12, double=True)
    w.cylinder((x, WHEEL_Y, WHEEL_Z), .06, .6, IRON, 'X', 12)
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
    for x0 in (3.45, 5.4):
        bx(g, x0, x0 + .15, cy - .25, cy + .25, BASE_ON, cz + .08, CONCRETE)
        bx(g, x0 - .02, x0 + .17, cy - .14, cy + .14, cz + .08, cz + .16, BRASS)
    d = Geometry('WindingDrum', DRUM)
    d.cylinder(DRUM, .42, 1.6, IRON, 'X', 16)
    for x in (3.75, 4.5, 5.25):
        d.cylinder((x, cy, cz), .58, .08, PAINTED, 'X', 16)
    for x in SKIPS:
        for k in range(3):
            d.ring((x - .2 + k * .2, cy, cz), .45, .04, .12, IRON, 'X', 16)
    d.cylinder(DRUM, .1, 2.2, IRON, 'X', 12)
    for x in (3.75, 5.25):
        bx(d, x - .035, x + .035, cy - .05, cy + .05, cz + .5, cz + .6, BRASS)
    parts.append((d, 'SPIN_X', -1))
    # Hoist ropes from the drum to the back of the sheaves (A over the top, B from below).
    g.beam((SKIPS[0], cy, cz + .46), (SKIPS[0], WHEEL_Y + WHEEL_R * .94, WHEEL_Z + WHEEL_R * .3), .04, mat=IRON)
    g.beam((SKIPS[1], cy - .46, cz), (SKIPS[1], WHEEL_Y + WHEEL_R * .94, WHEEL_Z - WHEEL_R * .3), .04, mat=IRON)
    # Flywheel on the drum shaft's extension, between concrete bearing blocks.
    g.cylinder((6.05, cy, cz), .1, .9, IRON, 'X', 12)
    for xa, xb in ((5.85, 5.95), (6.45, 6.55)):
        bx(g, xa, xb, cy - .3, cy + .3, BASE_ON, cz + .06, CONCRETE)
    fly = P.spoked_wheel('Flywheel', (6.2, cy, cz), .6, 'X', rim_t=.14, rim_w=.24, spokes=6, groove=False,
                         hub_r=.16, mat=IRON, hub_mat=PAINTED)
    parts.append((fly, 'SPIN_X', 2))
    # Steam cylinder and bed behind the flywheel; exhaust stack.
    bx(g, 6.05, 6.95, 5.35, 5.9, BASE_ON, BASE_ON + .4, PAINTED)
    g.cylinder((6.5, 5.62, BASE_ON + .62), .2, .5, PAINTED, 'Y', 12)


# ------------------------------------------------------------------ ore bin and tub

def ore_bin(g, parts):
    core = (6.1, 6.9, 1.15, 2.75)
    bx(g, core[0], core[1], core[2], core[3], BASE_ON, 3.0, PLANK)
    for face in ('front', 'back', 'right'):
        P.boards(g, face, core, BASE_ON, 3.0, width=.26, t=.06, mat=PLANK)
    for z in (1.6, 2.3, 2.85):
        bx(g, core[0] - .02, core[1] + .1, core[2] - .1, core[2] - .06, z - .06, z + .06, IRON)
        bx(g, core[0] - .02, core[1] + .1, core[3] + .06, core[3] + .1, z - .06, z + .06, IRON)
        bx(g, core[1] + .06, core[1] + .1, core[2] - .06, core[3] + .06, z - .04, z + .08, IRON)
    for i in range(6):
        g.rock((6.25 + (i % 3) * .2, 1.6 + (i // 3) * .5, 3.04 + .01 * i), (.22, .2, .14), IRON, 70 + i)


# ------------------------------------------------------------------ lamp house and bath house

def lamp_house(g):
    # Brick hall on tiles 0..3 x 0..3. The core front at .12 puts the native
    # portal's face on the tile edge y = 0.
    P.hall(g, .05, 2.95, .12, 2.95, 1.84, plinth=.5, doors=[1.5], pitch=1.0,
           windows={'front': [(.45, 1.15, 'grand', .55), (2.55, 1.15, 'grand', .55)],
                    'left': [(.59, 1.15, 'grand', .55), (1.535, 1.15, 'grand', .55), (2.48, 1.15, 'grand', .55)],
                    'right': [(.9, 1.42, 'grand', .5), (2.1, 1.42, 'grand', .5)],
                    'back': [(.8, 1.42, 'grand', .5)]})
    K.lamp(g, .78, .12, 1.15, face='front')
    K.lamp(g, 2.22, .12, 1.15, face='front')
    P.flat_roof(g, .05, 2.95, .12, 2.95, 1.84, overhang=.05, parapet=.25)


def bath_house(g):
    """One-layer annex on tiles 0..3 x 3..6 with its chimney in the back corner."""
    small = lambda u: (u, .52, 'factory', .4)
    # Core ends at 2.93 so its corner pilasters meet the shaft house's on an edge, not a face.
    P.concrete_house(g, .05, 2.93, 3.05, 5.95, BASE - .16, base=.2, pitch=1.3, record_doors=False,
                     windows={'left': [small(3.8), small(5.2)], 'back': [small(.8), small(2.2)]})
    bx(g, 0.0, 3.0, 3.0, 6.0, BASE - .16, BASE, CONCRETE)
    K.stack(g, .55, 5.45, BASE, 3.2, emits='smoke', r=.18, bands=3)


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
    ore_bin(g, parts)
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
