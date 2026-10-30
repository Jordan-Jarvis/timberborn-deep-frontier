"""TownPlaza: late-game paved civic square (wellbeing).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the corner planter beds, shrubs, lamp standards and post lamps; the
statue and flagpoles stand on the paving.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size", "one layer per floor"):
9x9x6 -> 7x8x4, inside the old footprint with the same origin, door,
native entrance cell and the same 15 visitor places round the fountain. The
right paving strips and the back corners are gone; the bandstand stands on a
3 x 2 podium one layer high with columns one layer tall under a smaller bell
roof. No clutter on buildable paving (BRIEF, user: "clutter that leaves most
of a tile open but makes it un buildable is not great"): the four flagpoles
stand on the bandstand podium's corners instead of the paving, and the statue
plinth fits one tile, so every paved cell outside the fountain stays free.

HERO: the shipped Fountain of Joy (native prop, scaled to the 3 x 3 fountain
tiles) on the square's axis, framed by a round iron bandstand under a teal
bell roof and the shipped Iron Teeth beaver statue (native prop).
ROOF: only the bandstand's bell roof (kept: it is the bandstand's defining
silhouette); the square itself is open sky.

Plan (7 x 8 tiles; front y = 0). Everything walkable is thin paving:
  - Paving: a 30 mm dark iron bed with basket-weave concrete flags and a
    ring of orange terracotta tiles round the fountain, 55 mm high in all.
    The harness claims a cell only when a part reaches 0.15 into it, so the
    paved cells stay free (Occupations None) and the square is walkable.
  - x 3..6, y 2..5  fountain basin (cells occupied).
  - x 3..6, y 6..8  bandstand: rusticated kiosk podium (top exactly layer 1)
                    with the door centred on x = 4.5, face on the y = 6 tile
                    edge; its path cell (4,5,0) lies on the free paving;
                    flagpoles on the podium's four corners.
  - statue plinth on tile (1, 1), front-left of the fountain ring.

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
FOOTPRINT = (7, 8)
HEIGHT = 4
FRAME_END = 121
HERO = ('The native Fountain of Joy on the square axis, framed by a round iron bandstand under a teal bell roof '
        'and the native Iron Teeth beaver statue.')

BED = .03            # iron paving bed top
FLAG = .055          # flag (paving) top: below the 0.15 occupancy inset
FOUNTAIN = (3, 2, 6, 5)
STAND = (3, 6, 6, 8)
BEDS = {'statue': (1, 1, 2, 2)}
FC = (4.5, 3.5)
STATUE_SCALE, STATUE_YAW = .9, 0     # native BeaverStatue.IronTeeth prop, facing the front
FOUNTAIN_SCALE = .6                    # native FountainOfJoy.Folktails prop (5 x 5 -> 3 x 3)
PLINTH = .2                            # fountain plinth top (occupies the fountain tiles)
DOOR_X = 4.5
# Walkable square: every footprint cell not claimed by the fountain, the
# bandstand or a corner bed. Registration must leave these free.
def _blocked(x, y):
    rects = [FOUNTAIN, STAND] + list(BEDS.values())
    return any(a <= x < c and b <= y < d for a, b, c, d in rects)
WALKABLE = [[x, y, 0] for y in range(FOOTPRINT[1]) for x in range(FOOTPRINT[0]) if not _blocked(x, y)]


# ---------------------------------------------------------------- paving

def paving(g):
    # Bed inset 2 cm from the footprint so its edges never share a plane
    # with planter or podium faces standing on the tile lines.
    W_, H_ = FOOTPRINT
    blk(g, .02, .02, 0, W_ - .02, H_ - .02, BED, IRON)
    ring = {(x, y) for x in range(2, 7) for y in range(1, 6)} - {(x, y) for x in range(3, 6) for y in range(2, 5)}
    for x in range(W_):
        for y in range(H_):
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
    for y in (6.5, 7.5):
        P.native_window(g, x0, y, .5, .5, 'left', 'factory')
        P.native_window(g, x1, y, .5, .5, 'right', 'factory')
    P.native_window(g, 3.6, y1, .5, .5, 'back', 'factory')
    P.native_window(g, 5.4, y1, .5, .5, 'back', 'factory')
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # Round stage furniture on the podium top (layer 1): iron columns, a
    # round balustrade and the bell roof. The deck itself stays the podium top.
    z0 = 1.0
    zr = 2.0
    R = .78
    for k in range(8):
        a = math.pi / 8 + k * math.pi / 4
        px, py = cx + math.cos(a) * R, cy + math.sin(a) * R
        K.revolve(g, (px, py, z0 - .01), [(.08, 0), (.08, .07), (.05, .1), (.038, .16), (.038, zr - z0 - .16),
                                          (.06, zr - z0 - .1), (.09, zr - z0 - .05), (.09, zr - z0 - .0)],
                  IRON, segments=10)
    I.ring_rail(g, (cx, cy), R, z0, height=.42, posts=12)
    K.hollow_revolve(g, (cx, cy, zr), [(R + .12, 0), (R + .12, .1)], .24, IRON, segments=16)
    rs = .68                               # bell roof scale (2026-10-22 profile)
    roof = [(r * rs, z * rs) for r, z in ((1.54, 0), (1.54, .07), (1.3, .2), (.97, .42), (.6, .78), (.32, 1.1),
                                         (.22, 1.3), (.24, 1.36), (.0, 1.42))]
    K.revolve(g, (cx, cy, zr + .1), roof, ROOF, segments=16)
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
            pts.append((cx + ca * (r + nr * .02), cy + sa * (r + nr * .02), zr + .1 + z + nz * .02))
            sides.append((-sa, ca, 0))
            ups.append((ca * nr, sa * nr, nz))
        W.sweep(g, pts, sides, ups, .025, .025, IRON)
    # Finial and weathervane.
    ft = zr + .1 + 1.42 * rs
    K.revolve(g, (cx, cy, ft - .04), [(.05, 0), (.05, .08), (.08, .11), (.08, .16), (.025, .2), (.025, .38)], BRASS,
              segments=10)
    vz = ft + .4
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
    low concrete plinth inside one tile, front-left of the fountain ring,
    facing into the square."""
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

# ---------------------------------------------------------------- beds and lamps

def corner_beds(g, parts):
    """Flagpoles on the four corners of the bandstand podium (layer 1), each
    flag flying outward; nothing stands on the paving. (The planter beds,
    shrubs, lamp standards and post lamps were removed on 2026-10-22; the
    poles left the corner paving on 2026-10-30.)"""
    x0, y0, x1, y1 = STAND
    for name, phase_base, sx, px in (('L', 0.0, -1, x0 + .17), ('R', 1.3, 1, x1 - .17)):
        for i, (py, hh) in enumerate(((y1 - .17, 2.2), (y0 + .17, 1.9))):
            W.flagpole(g, parts, f'TownPlaza.Flag{name}{i}', px, py, 1.0, hh, flag_w=.6, flag_h=.36,
                       phase=phase_base + i * .9, direction=sx)


def build(g, parts):
    paving(g)
    fountain(g, parts)
    bandstand(g, parts)
    statue_garden(g)
    corner_beds(g, parts)
