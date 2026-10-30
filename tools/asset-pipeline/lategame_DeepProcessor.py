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

HERO: a riveted blast furnace on a one-layer concrete hearth podium: banded
bosh and tapering stack, bustle main with tuyeres, a small top platform with
the rotating charging distributor, uptakes into a downcomer to the dust
catcher and a bleeder, charged by a plated vertical skip hoist from the ore
pit behind it.

Parts: concrete hearth podium; two domed hot-blast stoves with their chimney
and hot-blast main; dust catcher; flat-roofed open casting bay with runner,
tilting ladle and pig moulds (small GLOW accents only) under a riveted steel
plate roof; brick blower house with the door, a painted metal sheet roof deck
and a wall blower fan (roof variety, user 2026-10-30); skip hoist over its ore pit. Flat roofs stay
clear (user, 2026-10-30: no clutter on buildable space).

Animated (5, same names): skip car in the hoist, charging distributor,
tilting ladle, pour stream flicker, blower fan (now on the blower house's left wall).
"""
import math

from mathutils import Vector

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW
import lategame_mining_parts as P
from lategame_mining_parts import bx
from lategame_roofdeck_parts import deck_slab

IDENT = 'DeepProcessor'
FOOTPRINT = (7, 6)
HEIGHT = 8
HERO = 'Riveted blast furnace on a low hearth podium, charged by a plated vertical skip hoist, with stoves and a casting bay'
FRAME_END = 121

F = (5.0, 3.5)
PODIUM = (3.06, 6.94, 2.06, 4.94, 1.0)     # x0, x1, y0, y1, top (base course on tiles 3..7 x 2..5)
TOPDECK = 6
ZT = 6.35                                   # furnace throat top
# Skip hoist: vertical shaft on the back-right corner tile (6, 5).
HOIST = (6.5, 5.5)
SKIP_LOW, SKIP_HIGH = .75, 6.65             # skip-car centre at the bottom and top of the wind
T = Vector((HOIST[0], HOIST[1], SKIP_HIGH))
B = Vector((HOIST[0], HOIST[1], SKIP_LOW))
D = (B - T).normalized()                    # down the hoist
PERP = Vector((1, 0, 0))
NUP = PERP.cross(D).normalized()


def r_shell(z):
    """Furnace outer radius at height z."""
    pts = [(1.0, .78), (1.6, .78), (2.4, .98), (6.0, .6), (6.35, .38)]
    for (za, ra), (zb, rb) in zip(pts, pts[1:]):
        if za <= z <= zb:
            return ra + (rb - ra) * (z - za) / (zb - za)
    raise ValueError(z)


# ------------------------------------------------------------------ furnace

def podium(g):
    x0, x1, y0, y1, top = PODIUM
    bx(g, x0 - .06, x1 + .06, y0 - .06, y1 + .06, 0, .3, CONCRETE)
    bx(g, x0, x1, y0, y1, .3, top - .12, CONCRETE)
    bx(g, x0 - .05, x1 + .05, y0 - .05, y1 + .05, top - .12, top, CONCRETE)
    for x in (4.0, 6.0):
        P.face_member(g, 'front', (x0, x1, y0, y1), x - .12, x + .12, -.01, .05, .3, top - .12,
                      CONCRETE)
    for y in (3.0, 4.0):
        P.window(g, x1, y, .6, 'right', .4, 'factory')


def furnace(g, parts):
    cx, cy = F
    K.revolve(g, (cx, cy, 1.0), [(.78, 0), (.78, .6)], PAINTED, segments=16)
    K.revolve(g, (cx, cy, 1.6), [(.78, 0), (.98, .8)], FORGED, segments=16)
    K.revolve(g, (cx, cy, 2.4), [(.98, 0), (.6, 3.6)], IRON, segments=16)
    K.revolve(g, (cx, cy, 6.0), [(.6, 0), (.38, .35)], IRON, segments=16)
    for z in (1.2, 1.45):
        K.band(g, (cx, cy, 0), .78, z, .08, IRON, segments=16)
    for z in (3.2, 4.1, 5.0, 5.75):
        K.band(g, (cx, cy, 0), r_shell(z), z, .08, PAINTED, segments=16)
    K.revolve(g, (cx, cy, 2.36), [(1.12, 0), (1.12, .12)], IRON, segments=16)
    # Bustle main and tuyere stocks.
    g.ring((cx, cy, 2.05), 1.25, .22, .26, IRON, 'Z', 16)
    for k in range(8):
        a = 2 * math.pi * (k + .5) / 8
        c, s = math.cos(a), math.sin(a)
        g.beam((cx + c * 1.08, cy + s * 1.08, 1.95), (cx + c * .74, cy + s * .74, 1.42), .08, mat=IRON)
    # Taphole with a glowing tap.
    bx(g, cx - .2, cx + .2, cy - .9, cy - .76, 1.0, 1.42, IRON)
    bx(g, cx - .07, cx + .07, cy - .915, cy - .9, 1.08, 1.24, GLOW)
    # Top platform round the throat on brackets from the shell.
    bx(g, cx - .85, cx + .85, cy - .85, cy + .85, TOPDECK - .08, TOPDECK, IRON)
    zr = TOPDECK
    for a, b, ss, se, dz in (((cx - .81, cy - .81), (cx + .81, cy - .81), False, False, 0),
                             ((cx - .81, cy - .81), (cx - .81, cy + .81), True, True, -.011),
                             ((cx - .81, cy + .81), (cx + .81, cy + .81), False, False, 0),
                             ((cx + .81, cy - .81), (cx + .81, cy + .2), True, False, -.011)):
        P.rail(g, a, b, zr, skip_start=ss, skip_end=se, dz=dz)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        c, s = math.cos(a), math.sin(a)
        g.beam((cx + c * .72, cy + s * .72, 4.9), (cx + c * 1.1, cy + s * 1.1, TOPDECK - .1), .09, mat=IRON)
    # Rotating charging distributor and hopper on the furnace top.
    dist = Geometry('ChargingDistributor', (cx, cy, ZT))
    K.revolve(dist, (cx, cy, ZT), [(.36, 0), (.36, .1), (.58, .5), (.58, .58)], IRON, segments=12)
    for k in range(4):
        a = k * math.pi / 2
        bx(dist, cx + math.cos(a) * .53 - .05, cx + math.cos(a) * .53 + .05,
           cy + math.sin(a) * .53 - .05, cy + math.sin(a) * .53 + .05, ZT + .16, ZT + .4, BRASS)
    for i in range(5):
        dist.rock((cx - .2 + i * .1, cy + (.1 if i % 2 else -.1), ZT + .6 + .01 * i), (.16, .14, .11), IRON, 70 + i)
    parts.append((dist, 'SPIN_Z', 1))
    # Uptakes, junction, bleeder and the downcomer to the dust catcher.
    J = (4.35, 3.75, 6.85)
    for a in (160, 200):
        r = math.radians(a)
        P.tube(g, (cx + math.cos(r) * .42, cy + math.sin(r) * .42, ZT - .2), J, .1, IRON, 10)
    K.revolve(g, J, [(.14, -.2), (.24, -.08), (.24, .1), (.14, .2)], PAINTED, segments=12)
    P.tube(g, (J[0], J[1], J[2] + .2), (J[0], J[1], 7.6), .08, IRON, 10)
    g.cylinder((J[0], J[1], 7.64), .11, .08, BRASS, 'Z', 12)
    dc = (3.5, 5.5, 3.7)
    P.tube(g, J, dc, .16, IRON, 12)
    # Dust catcher on its own base behind the podium.
    bx(g, 3.0, 4.0, 5.0, 6.0, 0, .9, CONCRETE)
    K.revolve(g, (3.5, 5.5, .9), [(.38, 0), (.38, 2.4), (.2, 2.8), (.17, 2.95)], IRON, segments=12)
    for z in (1.6, 2.5):
        K.band(g, (3.5, 5.5, 0), .38, z, .07, PAINTED, segments=12)
    P.gauge(g, 3.5, 5.12, 1.4, 'front', .07)


# ------------------------------------------------------------------ stoves

def stoves(g):
    xs = (.8, 2.2)
    for x in xs:
        K.tank(g, x, 4.6, 0, .55, 4.0, mat=PAINTED, bands=4, roof='dome', segments=16)
        P.gauge(g, x - .3, 4.6 - .5, 1.2, 'front', .07)
    # Hot-blast main to the bustle pipe, with a valve per stove.
    P.tube(g, (.6, 3.5, 2.05), (3.8, 3.5, 2.05), .15, IRON, 12)
    g.cylinder((.58, 3.5, 2.05), .2, .05, BRASS, 'X', 12)
    for x in xs:
        P.tube(g, (x, 3.55, 2.05), (x, 4.1, 2.05), .12, IRON, 10)
        g.cylinder((x, 3.8, 2.05), .19, .1, BRASS, 'Y', 12)
        K.valve_wheel(g, x, 3.62, 2.45, face='front', r=.13)
        P.tube(g, (x, 3.62, 2.12), (x, 3.62, 2.42), .025, IRON, 6)
    # Stove chimney with a low flue from both stoves.
    K.stack(g, 1.5, 5.62, 0, 6.3, emits='smoke', r=.22, bands=4)
    P.tube(g, (.8, 5.15, .7), (2.2, 5.15, .7), .1, IRON, 10)
    P.tube(g, (1.5, 5.2, .7), (1.5, 5.4, .7), .08, IRON, 10)


# ------------------------------------------------------------------ skip hoist

def hoist(g, parts):
    x, y = HOIST
    # Ore pit inside the shaft foot (no bunker outside it: the ground beside stays buildable).
    bx(g, 6.0, 7.0, 5.0, 6.0, 0, .25, CONCRETE)
    # Plated hoist shaft on the tile edges: sides and back closed, front open over the skip.
    z0, z1 = .25, 7.15
    for px in (6.0, 7.0):
        bx(g, px - .03, px + .03, 5.0, 5.94, z0, z1, PAINTED)
    bx(g, 6.0, 7.0, 5.94, 6.0, z0, z1, PAINTED)
    for z in (2.0, 4.0, 6.0):
        bx(g, 6.03, 6.97, 4.98, 5.06, z - .05, z + .05, IRON)
    # Guide rails for the skip car.
    for gx in (x - .4, x + .4):
        bx(g, gx - .03, gx + .03, y + .3, y + .38, z0, z1, IRON)
    # Head frame: cap plate, sheave on two pedestals, and the chute to the furnace hopper.
    bx(g, 5.95, 7.05, 4.95, 6.05, z1, z1 + .08, IRON)
    for px in (x - .25, x + .25):
        bx(g, px - .05, px + .05, y - .12, y + .12, z1 + .08, z1 + .52, PAINTED)
    g.cylinder((x, y, z1 + .45), .04, .62, IRON, 'X', 10)
    g.ring((x, y, z1 + .45), .3, .06, .1, IRON, 'X', 16)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        g.beam((x, y + math.cos(a) * .05, z1 + .45 + math.sin(a) * .05),
               (x, y + math.cos(a) * .25, z1 + .45 + math.sin(a) * .25), .035, mat=IRON)
    P.slab_quad(g, [(6.05, 5.2, 7.05), (6.05, 4.8, 7.05), (5.4, 3.9, 6.98), (5.4, 4.3, 6.98)],
                (.12, -.07, 1), .05, FORGED)
    # Skip car.
    c0 = B + NUP * .1
    car = Geometry('SkipCar', tuple(c0))
    P.oriented_box(car, c0, D, PERP, NUP, (.42, .34, .28), FORGED)
    P.oriented_box(car, c0 - D * .4, D, PERP, NUP, (.05, .37, .31), PAINTED)
    for sd in (-1, 1):
        for sp in (-1, 1):
            w = c0 + D * sd * .3 + PERP * sp * .37 + NUP * .2
            P.oriented_box(car, w, D, PERP, NUP, (.1, .03, .08), IRON)
    for i in range(4):
        car.rock(tuple(c0 - D * .46 + PERP * (i - 1.5) * .14), (.16, .14, .12), IRON, 90 + i)
    parts.append((car, 'CUSTOM_INCLINE', SKIP_HIGH - SKIP_LOW))


# ------------------------------------------------------------------ casting bay

def casting_bay(g, parts):
    bx(g, 3.0, 7.0, 0.0, 2.0, 0, .12, CONCRETE)   # bay floor on tiles 3..7 x 0..2
    for x in (3.25, 6.75):
        for y in (.25, 1.75):
            P.column(g, x, y, .12, 1.72, .18)
    for y in (.25, 1.75):
        bx(g, 3.1, 6.9, y - .07, y + .07, 1.72, 1.84, IRON)
    deck_slab(g, 3.0, 0.0, 7.0, 2.0, 2.0, 'forged', base=IRON)  # flat roof: riveted steel plates (roof variety, 2026-10-30)
    # Runner trough from the taphole over the podium edge to the ladle.
    y0, z0, y1, z1 = F[1] - .9, 1.36, 1.45, 1.24
    P.slab_quad(g, [(4.86, y1, z1), (5.14, y1, z1), (5.14, y0, z0), (4.86, y0, z0)], (0, .1, 1), .08, FORGED)
    P.slab_quad(g, [(4.95, y1 + .05, z1 + .005), (5.05, y1 + .05, z1 + .005), (5.05, y0, z0 + .005),
                    (4.95, y0, z0 + .005)], (0, .1, 1), .004, GLOW)
    g.beam((5.0, 1.75, .12), (5.0, 1.75, 1.18), .1, mat=IRON)
    # Ladle stand and tilting ladle.
    lc = (5.0, 1.0, 1.08)
    for x in (4.45, 5.55):
        g.beam((x, .65, .12), (x, 1.0, 1.1), .08, mat=IRON)
        g.beam((x, 1.35, .12), (x, 1.0, 1.1), .07, mat=IRON)
        bx(g, x - .06, x + .06, .85, 1.15, .96, 1.22, BRASS)
    lad = Geometry('Ladle', lc)
    K.revolve(lad, (5.0, 1.0, .5), [(.26, 0), (.36, .22), (.39, .55), (.41, .64)], PAINTED, segments=12)
    lad.cylinder((5.0, 1.0, 1.15), .37, .02, GLOW, 'Z', 16)
    for z in (.68, .95):
        K.band(lad, (5.0, 1.0, 0), .37 if z < .8 else .4, z, .05, IRON, segments=12)
    lad.cylinder(lc, .045, .96, IRON, 'X', 10)
    bx(lad, 4.94, 5.06, .52, .63, 1.06, 1.15, PAINTED)
    parts.append((lad, 'SWAY_X', .18))
    stream = Geometry('PourStream', (5.0, .56, 1.0))
    bx(stream, 4.97, 5.03, .53, .59, .32, 1.0, GLOW)
    parts.append((stream, 'FLAME', 0))
    # Pig moulds on a casting line.
    for side in (.3, .82):
        bx(g, 3.55, 6.45, side - .03, side + .03, .12, .22, IRON)
    for i in range(7):
        x = 5.0 + (i - 3) * .4
        bx(g, x - .16, x + .16, .33, .79, .22, .38, IRON)
        if i in (2, 3, 4):
            bx(g, x - .11, x + .11, .38, .74, .38, .4, GLOW)
        else:
            bx(g, x - .11, x + .11, .38, .74, .38, .42, IRON)
    K.lamp(g, 3.25, .16, 1.3, face='front')
    K.lamp(g, 6.75, .16, 1.3, face='front')


def blower_house(g, parts):
    # Brick hall on tiles 0..3 x 0..3. The core front at .12 puts the native
    # portal's face on the tile edge y = 0.
    P.hall(g, .05, 2.95, .12, 2.95, 1.84, plinth=.5, doors=[1.5], pitch=1.0,
           posts=('front', 'left', 'back'),
           windows={'front': [(.45, 1.15, 'grand', .55), (2.55, 1.15, 'grand', .55)],
                    'left': [(.59, 1.15, 'grand', .55), (2.48, 1.15, 'grand', .55)]})
    K.lamp(g, .78, .12, 1.15, face='front')
    K.lamp(g, 2.22, .12, 1.15, face='front')
    # Painted metal sheet roof deck (roof variety, user 2026-10-30).
    P.flat_roof(g, .05, 2.95, .12, 2.95, 1.84, overhang=.05, parapet=.25, deck='painted')
    # Blower intake fan on the left wall (the flat roof stays clear and buildable).
    g.ring((-.01, 1.535, 1.15), .34, .06, .1, IRON, 'X', 16)
    parts.append((P.rotor('GableFan', (-.03, 1.535, 1.15), .28, 'X', 6), 'SPIN_X', 4))


def build(g, parts):
    podium(g)
    furnace(g, parts)
    stoves(g)
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
