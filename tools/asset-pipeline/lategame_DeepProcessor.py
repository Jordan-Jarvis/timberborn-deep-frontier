"""DeepProcessor: late-game Deep Alloy smelting works (Iron Teeth, Deep Frontier).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the ingot yard with its gantry crane and ingot stacks, and the post
lamp.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; one layer per floor, flat roofs): 11x10x14 -> 7x6x8, inside the old
footprint with the same origin, door and native entrance. Removed: the open
column-and-brace frame round the furnace, the 60-degree lattice skip bridge
with its support bents, the third hot-blast stove and the stove catwalk, the
gabled casting bay and the gabled blower house.

Second shrink 2026-11-01 (a YouTuber called the late-game buildings
"massive"; user: "we need to shrink the buildings down even more"):
7x6x8 -> 5x4x6, inside the old footprint with the same origin, door tile and
native entrance (1, -1). Saved processors stay valid: every new block is a
block the old processor occupied (or one over its solid machinery, where
nothing of the player's can stand); the furnace, the hoist and the chimney
stand on the back-right tiles where the old furnace stood, the blower house,
stove shed and casting bay keep the old two-layer roof height, so paths and
platforms on those old roof decks keep their support. The back-left tiles
(0..2 x 3) stay open ground, as before. Removed: the dust catcher and its
downcomer (no room), one storey of furnace height, the furnace top
platform's overhang; the stoves are squat and stand in an open shed.

HERO: a riveted blast furnace on a one-layer brick hearth, charged by a
plated vertical skip hoist beside it, with two squat hot-blast stoves in an
open shed, their chimney, and a casting bay.

Plan (5 x 4 tiles): the two-storey blower house front-left (tiles 0..3 x
0..2, the door, a wall blower fan); the open stove shed behind it (0..3 x
2..3, two domed stoves, the hot-blast main running low to the furnace); the
casting bay front-right (3..5 x 0..2: runner, tilting ladle, pig moulds);
the furnace on its hearth at the back-right tile (4, 3), the skip hoist on
tile (3, 3) and the stove chimney in the corner of tile (4, 2). The blower
house, stove shed and casting bay roofs form one deck on layer 2 (painted
sheet, plank, riveted steel plate: roof variety, user 2026-10-30), open edge
to edge.

Animated (5, same names): skip car in the hoist, charging distributor,
tilting ladle, pour stream flicker, blower fan on the blower house's left wall.
"""
import math

from mathutils import Vector

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW
import lategame_mining_parts as P
from lategame_mining_parts import bx
from lategame_roofdeck_parts import deck_slab
import compact_industry_parts as Q

IDENT = 'DeepProcessor'
FOOTPRINT = (5, 4)
HEIGHT = 6
HERO = 'Riveted blast furnace on a brick hearth, charged by a plated vertical skip hoist, with squat stoves and a casting bay'
FRAME_END = 121

F = (4.5, 3.5)
HEARTH = (4.05, 4.97, 3.05, 3.97, 1.0)      # x0, x1, y0, y1, top (tile 4, 3)
TOPDECK = 4
ZT = 4.35                                   # furnace throat top
DECK = 2.0
# Skip hoist: vertical shaft on tile (3, 3).
HOIST = (3.5, 3.5)
SKIP_LOW, SKIP_HIGH = .55, 4.55             # skip-car centre at the bottom and top of the wind
T = Vector((HOIST[0], HOIST[1], SKIP_HIGH))
B = Vector((HOIST[0], HOIST[1], SKIP_LOW))
D = (B - T).normalized()                    # down the hoist
PERP = Vector((1, 0, 0))
NUP = PERP.cross(D).normalized()
CHIMNEY = (4.76, 2.3)
MAIN_Z = .95                                # hot-blast main, low under the shed and across tile (3, 2)


def r_shell(z):
    """Furnace outer radius at height z."""
    pts = [(1.0, .4), (1.4, .4), (1.9, .47), (4.1, .32), (4.35, .2)]
    for (za, ra), (zb, rb) in zip(pts, pts[1:]):
        if za <= z <= zb:
            return ra + (rb - ra) * (z - za) / (zb - za)
    raise ValueError(z)


# ------------------------------------------------------------------ furnace

def hearth(g):
    x0, x1, y0, y1, top = HEARTH
    bx(g, x0 - .04, x1 + .02, y0 - .04, y1 + .02, 0, .3, CONCRETE)
    bx(g, x0, x1, y0, y1, .3, top - .12, P.BRICK)   # brick hearth walls under a concrete course (2026-10-31)
    bx(g, x0 - .03, x1 + .02, y0 - .03, y1 + .02, top - .12, top, CONCRETE)
    P.window(g, x1, 3.5, .6, 'right', .35, 'factory')


def furnace(g, parts):
    cx, cy = F
    K.revolve(g, (cx, cy, 1.0), [(.4, 0), (.4, .4)], PAINTED, segments=16)
    K.revolve(g, (cx, cy, 1.4), [(.4, 0), (.47, .5)], FORGED, segments=16)
    K.revolve(g, (cx, cy, 1.9), [(.47, 0), (.32, 2.2)], IRON, segments=16)
    K.revolve(g, (cx, cy, 4.1), [(.32, 0), (.2, .25)], IRON, segments=16)
    K.band(g, (cx, cy, 0), .4, 1.2, .07, IRON, segments=16)
    for z in (2.5, 3.2, 3.85):
        K.band(g, (cx, cy, 0), r_shell(z), z, .07, PAINTED, segments=16)
    K.revolve(g, (cx, cy, 1.86), [(.5, 0), (.5, .08)], IRON, segments=16)
    # Bustle main and tuyere stocks.
    g.ring((cx, cy, 1.62), .46, .08, .14, IRON, 'Z', 16)
    for k in range(6):
        a = 2 * math.pi * (k + .5) / 6
        c, s = math.cos(a), math.sin(a)
        g.beam((cx + c * .42, cy + s * .42, 1.56), (cx + c * .38, cy + s * .38, 1.25), .05, mat=IRON)
    # Taphole with a glowing tap, facing the casting bay.
    bx(g, cx - .14, cx + .14, cy - .47, cy - .38, 1.0, 1.3, IRON)
    bx(g, cx - .05, cx + .05, cy - .485, cy - .47, 1.06, 1.2, GLOW)
    # Small open top platform round the throat on brackets (no rails, 2026-10-31).
    bx(g, cx - .44, cx + .44, cy - .44, cy + .44, TOPDECK - .07, TOPDECK, IRON)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        c, s = math.cos(a), math.sin(a)
        g.beam((cx + c * .3, cy + s * .3, 3.35), (cx + c * .55, cy + s * .55, TOPDECK - .08), .06, mat=IRON)
    # Rotating charging distributor and hopper on the furnace top.
    dist = Geometry('ChargingDistributor', (cx, cy, ZT))
    K.revolve(dist, (cx, cy, ZT), [(.22, 0), (.22, .08), (.36, .36), (.36, .42)], IRON, segments=12)
    for k in range(4):
        a = k * math.pi / 2
        bx(dist, cx + math.cos(a) * .33 - .04, cx + math.cos(a) * .33 + .04,
           cy + math.sin(a) * .33 - .04, cy + math.sin(a) * .33 + .04, ZT + .12, ZT + .3, BRASS)
    for i in range(4):
        dist.rock((cx - .12 + i * .08, cy + (.06 if i % 2 else -.06), ZT + .44 + .01 * i), (.11, .1, .08), IRON, 70 + i)
    parts.append((dist, 'SPIN_Z', 1))
    # Uptakes into a junction and the bleeder (the dust catcher went with the old back yard).
    J = (4.5, 3.82, 4.85)
    for a in (60, 120):
        r = math.radians(a)
        P.tube(g, (cx + math.cos(r) * .16, cy + math.sin(r) * .16, ZT - .12), J, .06, IRON, 10)
    K.revolve(g, J, [(.08, -.12), (.14, -.05), (.14, .06), (.08, .12)], PAINTED, segments=12)
    P.tube(g, (J[0], J[1], J[2] + .12), (J[0], J[1], 5.45), .05, IRON, 10)
    g.cylinder((J[0], J[1], 5.48), .07, .06, BRASS, 'Z', 12)


# ------------------------------------------------------------------ stoves

def stove_shed(g):
    """Open shed behind the blower house (tiles 0..3 x 2..3): two squat domed
    stoves under a plank deck on layer 2, open at the back and the sides."""
    xs = (.75, 2.25)
    for x in xs:
        K.tank(g, x, 2.5, 0, .4, 1.15, mat=PAINTED, bands=2, roof='dome', segments=16)
        P.gauge(g, x - .22, 2.5 - .35, .75, 'front', .06)
    # Hot-blast main from both stoves, low across tile (3, 2) to the bustle pipe.
    P.tube(g, (.75, 2.5, MAIN_Z), (4.3, 2.5, MAIN_Z), .1, IRON, 12)
    P.tube(g, (4.3, 2.5, MAIN_Z), (4.3, 3.05, 1.55), .09, IRON, 12)
    for x in xs:
        g.cylinder((x + .45, 2.5, MAIN_Z), .14, .06, BRASS, 'X', 12)
    # Low flue from both stoves to the chimney.
    P.tube(g, (.75, 2.85, .55), (4.76, 2.85, .55), .07, IRON, 10)
    P.tube(g, (4.76, 2.85, .55), (CHIMNEY[0], CHIMNEY[1] + .1, .55), .07, IRON, 10)
    # Shed posts on the open back corners; the front rests on the blower house.
    for x in (.12, 2.88):
        bx(g, x - .07, x + .07, 2.88 - .07, 2.88 + .07, 0, DECK - .28, IRON)
        bx(g, x - .1, x + .1, 2.78, 2.98, -.03, .1, CONCRETE)
    bx(g, .05, 2.95, 2.8, 2.96, DECK - .28, DECK - .16, IRON)
    deck_slab(g, 0.0, 2.06, 3.0, 3.0, DECK, 'timber', base=IRON)   # meets the blower house roof's eave


def chimney(g):
    """Stove chimney in the back corner of tile (4, 2), from the ground."""
    K.stack(g, CHIMNEY[0], CHIMNEY[1], .12, 4.78, emits='smoke', r=.16, bands=3)   # on the bay floor


# ------------------------------------------------------------------ skip hoist

def hoist(g, parts):
    x, y = HOIST
    bx(g, 3.0, 4.0, 3.0, 4.0, 0, .2, CONCRETE)
    # Plated hoist shaft on the tile edges: sides and back closed, front open over the skip.
    z0, z1 = .2, 4.95
    for px in (3.03, 3.97):
        bx(g, px - .03, px + .03, 3.03, 3.94, z0, z1, PAINTED)
    bx(g, 3.03, 3.97, 3.94, 4.0, z0, z1, PAINTED)
    for z in (1.5, 3.0, 4.5):
        bx(g, 3.06, 3.94, 3.0, 3.06, z - .05, z + .05, IRON)
    for gx in (x - .32, x + .32):
        bx(g, gx - .03, gx + .03, y + .28, y + .36, z0, z1, IRON)
    # Head frame: cap plate, sheave on two pedestals, and the chute to the furnace hopper.
    bx(g, 2.98, 4.02, 2.98, 4.02, z1, z1 + .07, IRON)
    for px in (x - .2, x + .2):
        bx(g, px - .04, px + .04, y - .1, y + .1, z1 + .07, z1 + .42, PAINTED)
    g.cylinder((x, y, z1 + .36), .035, .5, IRON, 'X', 10)
    g.ring((x, y, z1 + .36), .24, .05, .08, IRON, 'X', 16)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        g.beam((x, y + math.cos(a) * .04, z1 + .36 + math.sin(a) * .04),
               (x, y + math.cos(a) * .2, z1 + .36 + math.sin(a) * .2), .03, mat=IRON)
    P.slab_quad(g, [(3.95, 3.3, 4.9), (3.95, 3.7, 4.9), (4.3, 3.62, 4.78), (4.3, 3.38, 4.78)],
                (.33, 0, 1), .04, FORGED)
    # Skip car.
    c0 = B + NUP * .1
    car = Geometry('SkipCar', tuple(c0))
    P.oriented_box(car, c0, D, PERP, NUP, (.34, .27, .22), FORGED)
    P.oriented_box(car, c0 - D * .32, D, PERP, NUP, (.04, .3, .25), PAINTED)
    for sd in (-1, 1):
        for sp in (-1, 1):
            w = c0 + D * sd * .24 + PERP * sp * .3 + NUP * .16
            P.oriented_box(car, w, D, PERP, NUP, (.08, .025, .06), IRON)
    for i in range(3):
        car.rock(tuple(c0 - D * .37 + PERP * (i - 1) * .13), (.13, .11, .1), IRON, 90 + i)
    parts.append((car, 'CUSTOM_INCLINE', SKIP_HIGH - SKIP_LOW))


# ------------------------------------------------------------------ casting bay

def casting_bay(g, parts):
    bx(g, 3.0, 5.0, 0.0, 3.0, 0, .12, CONCRETE)   # bay floor on tiles 3..5 x 0..3
    for x, y in ((4.8, .2), (4.8, 1.8)):
        P.column(g, x, y, .12, 1.72, .16)
    for y in (.2, 1.8):
        bx(g, 3.0, 4.9, y - .06, y + .06, 1.72, 1.84, IRON)
    deck_slab(g, 3.06, 0.0, 5.0, 2.0, DECK, 'forged', base=IRON)  # riveted steel plates (roof variety)
    # Runner trough from the taphole down to the ladle.
    y0, z0, y1, z1 = F[1] - .47, 1.2, 1.25, 1.12
    xr = F[0] - .1
    P.slab_quad(g, [(xr - .1, y1, z1), (xr + .1, y1, z1), (xr + .1, y0, z0), (xr - .1, y0, z0)], (0, .08, 1), .06, FORGED)
    P.slab_quad(g, [(xr - .04, y1 + .04, z1 + .004), (xr + .04, y1 + .04, z1 + .004), (xr + .04, y0, z0 + .004),
                    (xr - .04, y0, z0 + .004)], (0, .08, 1), .004, GLOW)
    for yy in (2.0, 2.7):
        g.beam((xr, yy, .12), (xr, yy, z1 + (z0 - z1) * (yy - y1) / (y0 - y1) - .05), .07, mat=IRON)
    # Ladle stand and tilting ladle.
    lc = (4.2, 1.05, .98)
    for x in (3.78, 4.62):
        g.beam((x, .78, .12), (x, 1.05, 1.0), .07, mat=IRON)
        g.beam((x, 1.32, .12), (x, 1.05, 1.0), .06, mat=IRON)
        bx(g, x - .05, x + .05, .92, 1.18, .88, 1.1, BRASS)
    lad = Geometry('Ladle', lc)
    K.revolve(lad, (4.2, 1.05, .48), [(.22, 0), (.3, .2), (.33, .48), (.35, .56)], PAINTED, segments=12)
    lad.cylinder((4.2, 1.05, 1.02), .31, .02, GLOW, 'Z', 16)
    for z in (.62, .86):
        K.band(lad, (4.2, 1.05, 0), .31 if z < .75 else .34, z, .04, IRON, segments=12)
    lad.cylinder(lc, .04, .8, IRON, 'X', 10)
    bx(lad, 4.15, 4.25, .64, .73, .97, 1.065, PAINTED)
    parts.append((lad, 'SWAY_X', .18))
    stream = Geometry('PourStream', (4.2, .66, .9))
    bx(stream, 4.17, 4.23, .63, .69, .3, .9, GLOW)
    parts.append((stream, 'FLAME', 0))
    # Pig moulds on a casting line along the bay front.
    for side in (.24, .56):
        bx(g, 3.2, 4.8, side - .025, side + .025, .12, .2, IRON)
    for i in range(5):
        x = 4.0 + (i - 2) * .33
        bx(g, x - .13, x + .13, .26, .54, .2, .33, IRON)
        if i in (1, 2, 3):
            bx(g, x - .09, x + .09, .3, .5, .33, .35, GLOW)
        else:
            bx(g, x - .09, x + .09, .3, .5, .33, .36, IRON)
    K.lamp(g, 4.8, .12, 1.3, face='front')


def blower_house(g, parts):
    """Two one-layer storeys on tiles 0..3 x 0..2 (concrete ground storey with
    the door, brick upper storey in a steel frame), painted-sheet roof deck on
    layer 2, the blower intake fan on the left wall."""
    Q.storey_block(g, 0.0, 0.0, 3.0, 2.0, 2, infill=P.BRICK, frame=IRON, door=1.5, door_id='Door0',
                   roof_mat=PAINTED, slab_mat=IRON, roof_boards=True,
                   ground_windows={'front': [(.5, .55, 'grand'), (2.5, .55, 'grand')]},
                   windows={'front': [(.5, 1.5, .5, 'grand'), (1.5, 1.5, .5, 'grand'), (2.5, 1.5, .5, 'grand')],
                            'left': [(1.5, 1.5, .5, 'grand')]})
    K.lamp(g, .9, -.01, .8, face='front')
    g.ring((-.01, .6, .55), .3, .05, .08, IRON, 'X', 16)
    parts.append((P.rotor('GableFan', (-.03, .6, .55), .24, 'X', 6), 'SPIN_X', 4))


def build(g, parts):
    hearth(g)
    furnace(g, parts)
    stove_shed(g)
    chimney(g)
    hoist(g, parts)
    casting_bay(g, parts)
    blower_house(g, parts)


def animate(obj, kind, value, frame_end):
    """Skip car: haul up the hoist, tip, return."""
    if kind != 'CUSTOM_INCLINE':
        raise ValueError('Unknown custom animation ' + kind)
    span = frame_end - 1
    base = obj.location.copy()
    up = -D * value
    for f, t in ((0, 0), (.42, 1), (.52, 1), (.94, 0), (1, 0)):
        obj.location = (base.x - up.x * t, base.y - up.y * t, base.z + up.z * t)
        obj.keyframe_insert(data_path='location', frame=1 + span * f)
    obj.location = base
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
