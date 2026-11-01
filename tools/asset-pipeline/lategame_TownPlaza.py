"""TownPlaza: late-game paved civic square (wellbeing).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the corner planter beds, shrubs, lamp standards and post lamps; the
statue and flagpoles stand on the paving.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale): 9x9x6 -> 7x8x4 (bandstand on a 3 x 2 one-layer podium).

Second shrink 2026-11-01 (user: "shrink the buildings down even more"):
7x8x4 -> 5x5x3, inside the old footprint with the same origin. The bandstand
is a one-tile kiosk on the square's back-right corner with its door facing
into the square; its native entrance is the paving cell (4, 3, 0) in front of
it (was (4, 5, 0), now just outside the square: native entrances always face
local south, so a door facing back onto the old cell is not possible). The
native Fountain of Joy keeps
its 3 x 3 basin, centred in the square; the shipped beaver statue stands on
the front-left corner tile; the four flagpoles stand on the fountain plinth's
corners, flying over the basin; the 15 visitors' places ring the fountain on
the free paving.

HERO: the shipped Fountain of Joy (native prop, scaled to the 3 x 3 fountain
tiles) in the middle of the square, with a round iron bandstand kiosk under a
teal bell roof and the shipped Iron Teeth beaver statue.
ROOF: only the kiosk's bell roof (its defining silhouette); the square itself
is open sky.

Plan (5 x 5 tiles; front y = 0). Everything walkable is thin paving:
  - Paving: a 30 mm dark iron bed with basket-weave concrete flags and a
    ring of orange terracotta tiles round the fountain, 55 mm high in all.
    The harness claims a cell only when a part reaches 0.15 into it, so the
    paved cells stay free (Occupations None) and the square is walkable.
  - x 1..4, y 1..4  fountain basin (cells occupied), flagpoles on its corners.
  - x 4..5, y 4..5  bandstand kiosk: rusticated podium (top exactly layer 1)
                    with the door centred on x = 4.5, face on the y = 4 tile
                    edge; its path cell (4,3,0) lies on the free paving; iron
                    columns and the bell roof on the podium.
  - statue plinth on tile (0, 0).

Animated: four flags (CUSTOM_YAW_OSC), the native fountain effect,
bandstand weathervane (SPIN_Z).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN, WATER, LAYER_GAP
import lategame_civic_parts as P
from lategame_civic_parts import blk, obox
import lategame_industry_parts as I
import native_building_assets as N
import civic_wellbeing_parts as W
from civic_wellbeing_parts import animate  # noqa: F401  (CUSTOM_ kinds)

IDENT = 'TownPlaza'
FOOTPRINT = (5, 5)
HEIGHT = 3
FRAME_END = 121
HERO = ('The native Fountain of Joy in the middle of the square, with a round iron bandstand kiosk under a teal '
        'bell roof and the native Iron Teeth beaver statue.')

BED = .03            # iron paving bed top
FLAG = .055          # flag (paving) top: below the 0.15 occupancy inset
FOUNTAIN = (1, 1, 4, 4)
STAND = (4, 4, 5, 5)
BEDS = {'statue': (0, 0, 1, 1)}
FC = (2.5, 2.5)
STATUE_SCALE, STATUE_YAW = .9, 0     # native BeaverStatue.IronTeeth prop, facing the front
FOUNTAIN_SCALE = .6                    # native FountainOfJoy.Folktails prop (5 x 5 -> 3 x 3)
PLINTH = .17                           # fountain plinth top (occupies the fountain tiles; .2 until 2026-11-01: HEIGHT 3)
DOOR_X = 4.5
# Walkable square: every footprint cell not claimed by the fountain, the
# kiosk or the statue. Registration must leave these free.
def _blocked(x, y):
    rects = [FOUNTAIN, STAND] + list(BEDS.values())
    return any(a <= x < c and b <= y < d for a, b, c, d in rects)
WALKABLE = [[x, y, 0] for y in range(FOOTPRINT[1]) for x in range(FOOTPRINT[0]) if not _blocked(x, y)]
DOOR_CELL = (4, 3)
# The 15 visitors' places (capacity unchanged): the centre of every free
# fountain-ring cell but the kiosk door's path cell, and two places side by
# side on the front-middle and left-middle tiles.
VISITOR_PLACES = ([(x + .5, y + .5) for x, y, _ in WALKABLE if (x, y) not in ((2, 0), (0, 2), DOOR_CELL)]
                  + [(2.3, .5), (2.7, .5), (.5, 2.3), (.5, 2.7)])


# ---------------------------------------------------------------- paving

def paving(g):
    # Bed inset 2 cm from the footprint so its edges never share a plane
    # with plinth or podium faces standing on the tile lines.
    W_, H_ = FOOTPRINT
    blk(g, .02, .02, 0, W_ - .02, H_ - .02, BED, IRON)
    x0, y0, x1, y1 = FOUNTAIN
    ring = {(x, y) for x in range(x0 - 1, x1 + 1) for y in range(y0 - 1, y1 + 1)}
    for x in range(W_):
        for y in range(H_):
            if _blocked(x, y):
                continue
            z0 = BED - .015
            if (x, y) in ring and (x + y) % 2 == 1:
                # Terracotta: four square tiles per cell, alternating with the flags.
                for i in range(2):
                    for j in range(2):
                        blk(g, x + .04 + i * .48, y + .04 + j * .48, z0, x + .48 + i * .48, y + .48 + j * .48, FLAG,
                            ORANGE)
            elif (x + y) % 4 == 0:
                blk(g, x + .04, y + .04, z0, x + .96, y + .47, FLAG, CONCRETE)
                blk(g, x + .04, y + .53, z0, x + .96, y + .96, FLAG, CONCRETE)
            else:
                blk(g, x + .04, y + .04, z0, x + .47, y + .96, FLAG, CONCRETE)
                blk(g, x + .53, y + .04, z0, x + .96, y + .96, FLAG, CONCRETE)


# ---------------------------------------------------------------- fountain

def fountain(g, parts):
    """The shipped Fountain of Joy model (Folktails monument, 5 x 5 tiles:
    tiered round basins with two carved beavers tipping a bucket) as a native
    prop at FOUNTAIN_SCALE on a low concrete plinth over the 3 x 3 fountain
    tiles, with its own native FountainWater surfaces and the vanilla
    FountainOfJoyWater effect at the vanilla attachment point scaled with the
    model. The plinth keeps the fountain tiles occupied, so visitors stand on
    the ring round it."""
    x0, y0, x1, y1 = FOUNTAIN
    blk(g, x0 + .02, y0 + .02, BED - .01, x1 - .02, y1 - .02, PLINTH, CONCRETE)
    blk(g, x0 - .02, y0 - .02, PLINTH - .06, x1 + .02, y1 + .02, PLINTH + .02, CONCRETE)
    s = FOUNTAIN_SCALE
    cx, cy = FC
    # Native models put their origin on the first tile's corner.
    N.prop(g, 'PlazaFountain', 'FountainOfJoy.Folktails', (cx - 2.5 * s, cy - 2.5 * s, PLINTH + .02), s, 0)
    # Vanilla attachment: Position (2.5, 2.6, 2.5) of the 5 x 5 model.
    K.emitter(g, 'fountainSpray', cx, cy, PLINTH + .02 + 2.6 * s, 2.5 * s)


def flagpoles(g, parts):
    """Flagpoles on the fountain plinth's four corners (inside the occupied
    fountain tiles), each flag flying in over the basin."""
    x0, y0, x1, y1 = FOUNTAIN
    for name, phase_base, px, d in (('L', 0.0, x0 + .17, 1), ('R', 1.3, x1 - .17, -1)):
        for i, (py, hh) in enumerate(((y1 - .17, 2.2), (y0 + .17, 1.9))):
            W.flagpole(g, parts, f'TownPlaza.Flag{name}{i}', px, py, PLINTH + .02, hh, flag_w=.55, flag_h=.34,
                       phase=phase_base + i * .9, direction=d)


# ---------------------------------------------------------------- bandstand kiosk

def bandstand(g, parts):
    x0, y0, x1, y1 = STAND
    P.podium(g, x0, y0, x1, y1, 1.0, skip=[(DOOR_X - .5, DOOR_X + .5)], base=BED - .01, foot=False)
    P.door(g, DOOR_X, y0, 0, 'Door0')
    P.native_window(g, x0, 4.5, .5, .45, 'left', 'factory')
    P.native_window(g, x1, 4.5, .5, .45, 'right', 'factory')
    P.native_window(g, 4.5, y1, .5, .45, 'back', 'factory')
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # Round stage furniture on the podium top (layer 1): iron columns and the
    # bell roof, no balustrade (user, 2026-10-31: "lets remove the railings").
    z0 = 1.0
    zr = 1.85
    R = .36
    for k in range(6):
        a = math.pi / 6 + k * math.pi / 3
        px, py = cx + math.cos(a) * R, cy + math.sin(a) * R
        K.revolve(g, (px, py, z0 - .01), [(.06, 0), (.06, .06), (.04, .09), (.03, .14), (.03, zr - z0 - .14),
                                          (.05, zr - z0 - .09), (.07, zr - z0 - .05), (.07, zr - z0 - .0)],
                  IRON, segments=10)
    K.hollow_revolve(g, (cx, cy, zr), [(R + .1, 0), (R + .1, .09)], .2, IRON, segments=16)
    rs = .36                               # bell roof scale (2026-10-22 profile)
    roof = [(r * rs, z * rs) for r, z in ((1.54, 0), (1.54, .07), (1.3, .2), (.97, .42), (.6, .78), (.32, 1.1),
                                         (.22, 1.3), (.24, 1.36), (.0, 1.42))]
    K.revolve(g, (cx, cy, zr + .09), roof, ROOF, segments=16)
    # Iron ribs on the bell roof, 2 cm proud along the surface normal.
    prof = roof[2:7]
    for k in range(8):
        a = k * math.pi / 4
        ca, sa = math.cos(a), math.sin(a)
        pts, sides, ups = [], [], []
        for i, (r, z) in enumerate(prof):
            j0, j1 = max(0, i - 1), min(len(prof) - 1, i + 1)
            dr, dz = prof[j1][0] - prof[j0][0], prof[j1][1] - prof[j0][1]
            m = math.hypot(dr, dz)
            nr, nz = dz / m, -dr / m
            pts.append((cx + ca * (r + nr * .015), cy + sa * (r + nr * .015), zr + .09 + z + nz * .015))
            sides.append((-sa, ca, 0))
            ups.append((ca * nr, sa * nr, nz))
        W.sweep(g, pts, sides, ups, .018, .018, IRON)
    # Finial and weathervane.
    ft = zr + .09 + 1.42 * rs
    K.revolve(g, (cx, cy, ft - .03), [(.04, 0), (.04, .06), (.06, .08), (.06, .12), (.02, .15), (.02, .28)], BRASS,
              segments=10)
    vz = ft + .3
    vane = Geometry('TownPlaza.Weathervane', (cx, cy, vz))
    vane.cylinder((cx, cy, vz - .01), .03, .05, BRASS, 'Z', 8)
    vane.beam((cx - .24, cy, vz), (cx + .22, cy, vz), .025, mat=IRON)
    for order in ((0, 1, 2, 3), (3, 2, 1, 0)):
        vane.add([(cx - .24, cy, vz - .03), (cx - .09, cy, vz - .03), (cx - .09, cy, vz + .08), (cx - .24, cy, vz + .05)],
                 [order], IRON)
    for order in ((0, 1, 2), (2, 1, 0)):
        vane.add([(cx + .22, cy - .04, vz), (cx + .3, cy, vz), (cx + .22, cy + .04, vz)], [order], BRASS)
    parts.append((vane, 'SPIN_Z', 1))


# ---------------------------------------------------------------- statue


def statue_garden(g):
    """The shipped Iron Teeth Beaver Statue (a beaver raising a hammer on a
    gear pedestal, Buildings/Decoration/BeaverStatue) as a native prop on a
    low concrete plinth inside one tile, the square's front-left corner,
    facing the front."""
    x0, y0, x1, y1 = BEDS['statue']
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    blk(g, cx - .4, cy - .4, BED - .01, cx + .4, cy + .4, .32, CONCRETE)
    blk(g, cx - .43, cy - .43, .26, cx + .43, cy + .43, .34, IRON)
    # Native models put their origin on the first tile's corner: rotate and
    # offset so the statue stands centred on the plinth, facing the front.
    scale, yaw = STATUE_SCALE, STATUE_YAW
    a = math.radians(yaw); c, s_ = math.cos(a), math.sin(a)
    N.prop(g, 'PlazaStatue', 'BeaverStatue.IronTeeth',
           (cx - .5 * scale * (c + s_), cy - .5 * scale * (c - s_), .34), scale, yaw)


def build(g, parts):
    paving(g)
    fountain(g, parts)
    flagpoles(g, parts)
    bandstand(g, parts)
    statue_garden(g)
