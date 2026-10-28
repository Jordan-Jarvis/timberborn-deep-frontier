"""TownPlaza: late-game paved civic square (wellbeing).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the corner planter beds, shrubs, lamp standards and post lamps; the
statue and flagpoles stand on the paving.

HERO: the shipped Fountain of Joy (native prop, scaled to the 3 x 3 fountain
tiles) on the square's axis, framed by a round iron bandstand under a teal
bell roof and the shipped Iron Teeth beaver statue (native prop).
ROOF: only the bandstand's bell roof; the square itself is open sky.

Plan (9 x 9 tiles; front y = 0). Everything walkable is thin paving:
  - Paving: a 30 mm dark iron bed with basket-weave concrete flags and a
    ring of orange terracotta tiles round the fountain, 55 mm high in all.
    The harness claims a cell only when a part reaches 0.15 into it, so the
    paved cells stay free (Occupations None) and the square is walkable.
  - x 3..6, y 2..5  fountain basin (cells occupied).
  - x 3..6, y 6..9  bandstand: rusticated kiosk podium (top exactly layer 1)
                    with the door centred on x = 4.5, face on the y = 6 tile
                    edge; its path cell (4,5,0) lies on the free paving.
  - 2 x 2 corner beds (perimeter only): statue garden front-left, lamp bed
    front-right, flagpole beds at the two back corners.
  - REDIC Lamp props stand on grid lines at the open sides, never mid-tile.

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
FOOTPRINT = (9, 9)
HEIGHT = 6
FRAME_END = 121
HERO = ('The native Fountain of Joy on the square axis, framed by a round iron bandstand under a teal bell roof '
        'and the native Iron Teeth beaver statue.')

BED = .03            # iron paving bed top
FLAG = .055          # flag (paving) top: below the 0.15 occupancy inset
FOUNTAIN = (3, 2, 6, 5)
STAND = (3, 6, 6, 9)
BEDS = {'statue': (0, 0, 2, 2), 'lamps': (7, 0, 9, 2), 'flagsL': (0, 7, 2, 9), 'flagsR': (7, 7, 9, 9)}
FC = (4.5, 3.5)
STATUE_SCALE, STATUE_YAW = 1.4, 0     # native BeaverStatue.IronTeeth prop, facing the front
FOUNTAIN_SCALE = .6                    # native FountainOfJoy.Folktails prop (5 x 5 -> 3 x 3)
PLINTH = .2                            # fountain plinth top (occupies the fountain tiles)
DOOR_X = 4.5
# Walkable square: every footprint cell not claimed by the fountain, the
# bandstand or a corner bed. Registration must leave these free.
def _blocked(x, y):
    rects = [FOUNTAIN, STAND] + list(BEDS.values())
    return any(a <= x < c and b <= y < d for a, b, c, d in rects)
WALKABLE = [[x, y, 0] for y in range(9) for x in range(9) if not _blocked(x, y)]


# ---------------------------------------------------------------- paving

def paving(g):
    # Bed inset 2 cm from the footprint so its edges never share a plane
    # with planter or podium faces standing on the tile lines.
    blk(g, .02, .02, 0, 8.98, 8.98, BED, IRON)
    ring = {(x, y) for x in range(2, 7) for y in range(1, 6)} - {(x, y) for x in range(3, 6) for y in range(2, 5)}
    for x in range(9):
        for y in range(9):
            if _blocked(x, y):
                continue
            z0 = BED - .015
            if (x, y) in ring:
                # Terracotta: four square tiles per cell.
                for i in range(2):
                    for j in range(2):
                        blk(g, x + .04 + i * .48, y + .04 + j * .48, z0, x + .48 + i * .48, y + .48 + j * .48, FLAG,
                            ORANGE)
            elif (x, y) == (int(DOOR_X), STAND[1] - 1):
                # Entrance cell: flags stop short of the door recess.
                blk(g, x + .04, y + .04, z0, x + .47, y + .85, FLAG, CONCRETE)
                blk(g, x + .53, y + .04, z0, x + .96, y + .85, FLAG, CONCRETE)
            elif (x + y) % 2 == 0:
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
    FountainOfJoyWater effect (spray and the bucket pour) at the vanilla
    attachment point scaled with the model. The plinth keeps the fountain
    tiles occupied, so visitors stand on the ring round it."""
    x0, y0, x1, y1 = FOUNTAIN
    blk(g, x0 + .02, y0 + .02, BED - .01, x1 - .02, y1 - .02, PLINTH, CONCRETE)
    blk(g, x0 - .02, y0 - .02, PLINTH - .06, x1 + .02, y1 + .02, PLINTH + .02, CONCRETE)
    s = FOUNTAIN_SCALE
    cx, cy = FC
    # Native models put their origin on the first tile's corner.
    N.prop(g, 'PlazaFountain', 'FountainOfJoy.Folktails', (cx - 2.5 * s, cy - 2.5 * s, PLINTH + .02), s, 0)
    # Vanilla attachment: Position (2.5, 2.6, 2.5) of the 5 x 5 model.
    K.emitter(g, 'fountainSpray', cx, cy, PLINTH + .02 + 2.6 * s, 2.5 * s)

# ---------------------------------------------------------------- bandstand

def bandstand(g, parts):
    x0, y0, x1, y1 = STAND
    P.podium(g, x0, y0, x1, y1, 1.0, skip=[(DOOR_X - .5, DOOR_X + .5)], base=BED - .01, foot=False)
    P.door(g, DOOR_X, y0, 0, 'Door0')
    # Lamp standards on the podium's front corners (layer 1): wall lamps at
    # the door would claim the walkable cells either side of its path cell.
    for lx in (x0 + .16, x1 - .16):
        W.lamp_standard(g, lx, y0 + .16, 1.0, 1.05)
    for y in (6.6, 8.4):
        P.native_window(g, x0, y, .55, .55, 'left', 'factory')
        P.native_window(g, x1, y, .55, .55, 'right', 'factory')
    P.native_window(g, 3.6, y1, .55, .55, 'back', 'factory')
    P.native_window(g, 5.4, y1, .55, .55, 'back', 'factory')
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # Round stage furniture on the podium top (layer 1): iron columns, a
    # round balustrade and the bell roof. The deck itself stays the podium top.
    z0 = 1.0
    zr = 2.95
    R = 1.22
    for k in range(8):
        a = math.pi / 8 + k * math.pi / 4
        px, py = cx + math.cos(a) * R, cy + math.sin(a) * R
        K.revolve(g, (px, py, z0 - .01), [(.1, 0), (.1, .08), (.06, .12), (.045, .2), (.045, zr - z0 - .2),
                                          (.07, zr - z0 - .12), (.11, zr - z0 - .06), (.11, zr - z0 - .0)],
                  IRON, segments=10)
    I.ring_rail(g, (cx, cy), R, z0, height=.5, posts=16)
    K.hollow_revolve(g, (cx, cy, zr), [(R + .14, 0), (R + .14, .12)], .3, IRON, segments=16)
    roof = [(1.54, 0), (1.54, .07), (1.3, .2), (.97, .42), (.6, .78), (.32, 1.1), (.22, 1.3), (.24, 1.36),
            (.0, 1.42)]
    K.revolve(g, (cx, cy, zr + .12), roof, ROOF, segments=16)
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
            pts.append((cx + ca * (r + nr * .02), cy + sa * (r + nr * .02), zr + .12 + z + nz * .02))
            sides.append((-sa, ca, 0))
            ups.append((ca * nr, sa * nr, nz))
        W.sweep(g, pts, sides, ups, .03, .03, IRON)
    # Finial and weathervane.
    ft = zr + .12 + 1.42
    K.revolve(g, (cx, cy, ft - .04), [(.06, 0), (.06, .1), (.1, .14), (.1, .2), (.03, .26), (.03, .5)], BRASS,
              segments=10)
    vz = ft + .52
    vane = Geometry('TownPlaza.Weathervane', (cx, cy, vz))
    vane.cylinder((cx, cy, vz - .01), .04, .06, BRASS, 'Z', 8)
    vane.beam((cx - .32, cy, vz), (cx + .3, cy, vz), .03, mat=IRON)
    for order in ((0, 1, 2, 3), (3, 2, 1, 0)):
        vane.add([(cx - .32, cy, vz - .04), (cx - .12, cy, vz - .04), (cx - .12, cy, vz + .1), (cx - .32, cy, vz + .06)],
                 [order], IRON)
    for order in ((0, 1, 2), (2, 1, 0)):
        vane.add([(cx + .3, cy - .05, vz), (cx + .4, cy, vz), (cx + .3, cy + .05, vz)], [order], BRASS)
    parts.append((vane, 'SPIN_Z', 1))


# ---------------------------------------------------------------- statue


def statue_garden(g):
    """The shipped Iron Teeth Beaver Statue (a beaver raising a hammer on a
    gear pedestal, Buildings/Decoration/BeaverStatue) as a native prop on a
    low concrete plinth in the front-left corner, facing into the square."""
    x0, y0, x1, y1 = BEDS['statue']
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    blk(g, cx - .5, cy - .5, BED - .01, cx + .5, cy + .5, .32, CONCRETE)
    blk(g, cx - .54, cy - .54, .26, cx + .54, cy + .54, .34, IRON)
    # Native models put their origin on the first tile's corner: rotate and
    # offset so the statue stands centred on the plinth, facing the front.
    scale, yaw = STATUE_SCALE, STATUE_YAW
    a = math.radians(yaw); c, s_ = math.cos(a), math.sin(a)
    N.prop(g, 'PlazaStatue', 'BeaverStatue.IronTeeth',
           (cx - .5 * scale * (c + s_), cy - .5 * scale * (c - s_), .34), scale, yaw)

# ---------------------------------------------------------------- beds and lamps

def corner_beds(g, parts):
    """Flagpoles at the two back corners, standing on the paving. (The
    planter beds, shrubs, lamp standards and post lamps were removed.)"""
    for name, phase_base, sx in (('flagsL', 0.0, 1), ('flagsR', 1.3, -1)):
        x0, y0, x1, y1 = BEDS[name]
        poles = [(x0 + .5 if sx > 0 else x1 - .5, y1 - .5, 4.3), (x0 + 1.25 if sx > 0 else x1 - 1.25, y0 + .75, 3.6)]
        for i, (px, py, hh) in enumerate(poles):
            W.flagpole(g, parts, f'TownPlaza.Flag{name[-1]}{i}', px, py, BED - .01, hh, flag_w=.72, flag_h=.44,
                       phase=phase_base + i * .9, direction=sx)


def build(g, parts):
    paving(g)
    fountain(g, parts)
    bandstand(g, parts)
    statue_garden(g)
    corner_beds(g, parts)
