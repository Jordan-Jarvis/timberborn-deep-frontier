"""PublicHealthLab: civic water and sanitation laboratory (3 workers, 100 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the water-testing forecourt (basin, fountain, sampling hoist, dosing
tanks), planting and post lamp.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "public health lab needs to shrink a decent amount", "one layer
per floor"): 8x6x12 -> 6x4x4, inside the old footprint with the same origin,
door and native entrance. Removed: the two-layer podium, the second plaster
storey, the mansard with its dormers, the octagonal observation lantern and
its rails, the eight-layer ventilation tower with its floor bands, ladder,
top rails, cowls and duct bridge, the header tank on its stand and the
fume-cupboard flue. The lab is two one-layer storeys under a real roof.
Roof variety (user, 2026-10-30: "some buildings can have actual roofs", "no
roof vents"): a teal gabled roof of native roof planks (as on the Iron Teeth
barracks) instead of a flat deck; no vent shaft or cowls.

HERO: a pale plaster laboratory in a grey timber frame under a teal plank
gabled roof, a brass anemometer and a weathervane on the ridge ends.
ROOF: gabled roof of separate native roof planks (RoofPlanks.IronTeeth) with
iron battens and ridge cap; grey boarded gable ends.

Plan (6 x 4 tiles; front y = 0; one layer per storey):
  - ground storey (layer 0): cast-concrete walls with factory windows and the
    native door centred on x = 4.5, face on the y = 0 tile edge;
  - upper storey (layer 1): pale plaster laboratory in a grey timber frame
    with a lancet window in every bay; walls up to layer 2;
  - gabled roof from layer 2, ridge along x.

Animated: anemometer (SPIN_Z, name unchanged) and weathervane (SPIN_Z) on
the ridge ends. The tower cowls left with the tower.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN
import lategame_civic_parts as P
from lategame_civic_parts import blk, animate  # noqa: F401
import native_building_assets as N
from lategame_mining_parts import plank_gable

IDENT = 'PublicHealthLab'
FOOTPRINT = (6, 4)
HEIGHT = 4
HERO = ('Pale plaster laboratory in a grey timber frame under a teal plank gabled roof, with a brass anemometer '
        'and a weathervane on the ridge.')
FRAME_END = 121

W, D = FOOTPRINT
STOREY = 1.0                    # one layer per storey
WALL_TOP = 2.0
DOOR_X = 4.5
WALL = (.1, .1, W - .1, D - .1)
ROOF_RISE = 1.15
OVERHANG = .14


def ground_storey(g):
    # Brick ground storey (2026-10-30, bricks pass; was cast concrete with
    # pilaster joints): brick courses between the foot and the coping, open
    # around the door, lamps and windows.
    P.podium(g, 0, 0, W, D, STOREY, skip=[(DOOR_X - .5, DOOR_X + .5)], joints=False)
    box = lambda fn: features.append(P.authored_box(g, fn))
    features = []
    box(lambda g: P.door(g, DOOR_X, 0, 0, 'Door0'))
    box(lambda g: K.lamp(g, DOOR_X - .64, 0, .5, face='front'))
    box(lambda g: K.lamp(g, DOOR_X + .64, 0, .5, face='front'))
    for x in (.5, 1.5, 2.5, 3.5, 5.5):
        box(lambda g, x=x: P.native_window(g, x, 0, .47, .55, 'front', 'factory'))
    for x in (.5, 1.5, 2.5, 3.5, 4.5, 5.5):
        box(lambda g, x=x: P.native_window(g, x, D, .47, .55, 'back', 'factory'))
    for y in (.5, 1.5, 2.5, 3.5):
        box(lambda g, y=y: P.native_window(g, 0, y, .47, .55, 'left', 'factory'))
        box(lambda g, y=y: P.native_window(g, W, y, .47, .55, 'right', 'factory'))
    P.brick_skin(g, 0, 0, W, D, .14, STOREY - .10, features=features)


def upper_storey(g):
    x0, y0, x1, y1 = WALL
    xs = [x0 + (x1 - x0) * (i + .5) / W for i in range(W)]
    ys = [y0 + (y1 - y0) * (i + .5) / D for i in range(D)]
    P.framed_block(g, x0, y0, x1, y1, STOREY, WALL_TOP, infill=CONCRETE, frame=GREYWOOD, pitch=1.0 - .2 / W,
                   corner=.16, post=.1,
                   windows={'front': [(x, 1.41, .72, 'lancet') for x in xs],
                            'back': [(x, 1.41, .72, 'lancet') for x in xs],
                            'left': [(y, 1.41, .72, 'lancet') for y in ys],
                            'right': [(y, 1.41, .72, 'lancet') for y in ys]})
    plank_gable(g, x0, x1, y0, y1, WALL_TOP, WALL_TOP + ROOF_RISE, ridge_axis='X', overhang=OVERHANG,
                gable_mat=GREYPLANK, seed=11)


def ridge_finials(g, parts):
    """Weathervane and anemometer on brass finials at the two ridge ends."""
    x0, y0, x1, y1 = WALL
    ridge_z = WALL_TOP + ROOF_RISE + .07 + .022 + .05      # top of the ridge cap
    cy = (y0 + y1) / 2
    ends = (x0 + .25, x1 - .25)
    for x in ends:
        K.revolve(g, (x, cy, ridge_z - .02), [(.07, 0), (.07, .08), (.045, .12), (.025, .4)], BRASS, segments=10)
    # Weathervane (west end).
    vx, vz = ends[0], ridge_z + .45
    vane = Geometry('Weathervane', (vx, cy, vz))
    vane.cylinder((vx, cy, vz - .01), .04, .06, BRASS, 'Z', 8)
    vane.beam((vx - .3, cy, vz), (vx + .28, cy, vz), .03, mat=IRON)
    for order in ((0, 1, 2, 3), (3, 2, 1, 0)):
        vane.add([(vx - .3, cy, vz - .04), (vx - .12, cy, vz - .04), (vx - .12, cy, vz + .09), (vx - .3, cy, vz + .05)],
                 [order], IRON)
    for order in ((0, 1, 2), (2, 1, 0)):
        vane.add([(vx + .28, cy - .05, vz), (vx + .38, cy, vz), (vx + .28, cy + .05, vz)], [order], BRASS)
    parts.append((vane, 'SPIN_Z', 1))
    # Anemometer (east end).
    ax, az = ends[1], ridge_z + .45
    an = Geometry('Anemometer', (ax, cy, az))
    an.cylinder((ax, cy, az - .03), .045, .07, BRASS, 'Z', 8)
    for i in range(3):
        a = i * 2 * math.pi / 3
        tip = (ax + math.cos(a) * .24, cy + math.sin(a) * .24, az - .01)
        an.beam((ax, cy, az - .01), tip, .022, mat=IRON)
        K.revolve(an, (tip[0], tip[1], tip[2] - .05), [(.001, 0), (.065, .035), (.065, .085), (.001, .1)], BRASS,
                  segments=8)
    parts.append((an, 'SPIN_Z', 2))


def build(g, parts):
    ground_storey(g)
    upper_storey(g)
    ridge_finials(g, parts)
