"""DeepProcessor: late-game Deep Alloy smelting works (Iron Teeth, Deep Frontier).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the ingot yard with its gantry crane and ingot stacks, and the post
lamp.

HERO: a riveted blast-furnace tower on a concrete hearth podium: banded bosh and
tapering stack, bustle main with tuyeres, top platform with a rotating charging
distributor, three uptakes into a gooseneck downcomer and twin bleeder stacks,
fed by a 60-degree steel skip bridge rising diagonally from the ore bunkers.
Roofs: teal plank gable over the open casting bay, plank gable on the blower
house, domed caps on the hot-blast stoves.

Parts: concrete podium; three domed hot-blast stoves with stove chimney, flue
and hot-blast main; dust catcher; blower house with gable fan; open casting bay
with runner, tilting ladle and pig moulds (small GLOW accents only); ingot yard
with travelling gantry crane; ore bunkers and skip pit.

Animated (6): skip car on the incline, charging distributor, tilting ladle,
pour stream flicker, gantry crane bridge, blower-house gable fan.
"""
import math

from mathutils import Vector

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW
import lategame_mining_parts as P
from lategame_mining_parts import bx

IDENT = 'DeepProcessor'
FOOTPRINT = (11, 10)
HEIGHT = 14
HERO = 'Riveted blast-furnace tower with gooseneck downcomer and bleeders, fed by a diagonal 60-degree skip bridge'
FRAME_END = 121

F = (5.0, 5.8)
PODIUM = (3.06, 7.94, 4.06, 7.94, 2.0)      # x0, x1, y0, y1, top (base course on tiles 3..8 x 4..8)
TOPDECK = 10
# Skip incline: top end over the hopper, falling toward the back-right corner.
T = Vector((5.55, 6.1, 12.0))
U = Vector((.821, .572, 0)).normalized()
DROP = 11.5
PLAN = 6.11
B = T + U * PLAN + Vector((0, 0, -DROP))
L3 = (B - T).length / PLAN                   # incline length per plan unit
D = (B - T).normalized()                     # down-slope unit vector
PERP = Vector((-U.y, U.x, 0))
NUP = PERP.cross(D).normalized()
if NUP.z < 0:
    NUP = -NUP


def on_incline(s):
    """Point on the incline centreline at plan distance s from the top end."""
    return T + U * s + Vector((0, 0, -DROP * s / PLAN))


def r_shell(z):
    """Furnace outer radius at height z."""
    pts = [(2.0, 1.1), (3.0, 1.1), (4.2, 1.38), (10.0, .86), (10.6, .56)]
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
    for x in (4.0, 6.4):
        P.face_member(g, 'front', (x0, x1, y0, y1), x - .12, x + .12, -.01, .05, .3, top - .12, CONCRETE)
    for x in (4.6, 5.8):
        P.window(g, x, y0, 1.05, 'front', .6, 'factory')
    for y in (5.0, 6.6):
        P.window(g, x0, y, 1.05, 'left', .6, 'factory')
        P.window(g, x1, y, 1.05, 'right', .6, 'factory')


def furnace(g, parts):
    cx, cy = F
    K.revolve(g, (cx, cy, 2.0), [(1.1, 0), (1.1, 1.0)], PAINTED, segments=16)
    K.revolve(g, (cx, cy, 3.0), [(1.1, 0), (1.38, 1.2)], FORGED, segments=16)
    K.revolve(g, (cx, cy, 4.2), [(1.38, 0), (.86, 5.8)], IRON, segments=16)
    K.revolve(g, (cx, cy, 10.0), [(.86, 0), (.56, .6)], IRON, segments=16)
    for z in (2.25, 2.75):
        K.band(g, (cx, cy, 0), 1.1, z, .1, IRON, segments=16)
    for z in (5.2, 6.3, 7.4, 8.5, 9.5):
        K.band(g, (cx, cy, 0), r_shell(z), z, .09, PAINTED, segments=16)
    # Mantle ring carried by the four columns.
    K.revolve(g, (cx, cy, 4.14), [(1.62, 0), (1.62, .16)], IRON, segments=16)
    # Bustle main and tuyere stocks.
    g.ring((cx, cy, 3.62), 1.7, .28, .32, IRON, 'Z', 16)
    for k in range(10):
        a = 2 * math.pi * (k + .5) / 10
        c, s = math.cos(a), math.sin(a)
        g.beam((cx + c * 1.5, cy + s * 1.5, 3.5), (cx + c * 1.05, cy + s * 1.05, 2.75), .09, mat=IRON)
    # Taphole with a glowing tap, runner across the podium to the casting bay.
    bx(g, cx - .25, cx + .25, cy - 1.2, cy - 1.05, 2.0, 2.55, IRON)
    bx(g, cx - .08, cx + .08, cy - 1.215, cy - 1.19, 2.12, 2.3, GLOW)
    bx(g, cx - .2, cx + .2, PODIUM[2] - .05, cy - 1.2, 2.0, 2.14, FORGED)
    bx(g, cx - .07, cx + .07, PODIUM[2] - .02, cy - 1.22, 2.14, 2.155, GLOW)
    # Top platform: open quadrant at the back-right for the skip bridge.
    for x0, x1, y0, y1 in ((3.4, 6.7, 4.1, 4.85), (3.4, 4.05, 4.85, 7.5), (4.05, 5.9, 6.75, 7.5),
                           (5.95, 6.7, 4.85, 5.9)):
        bx(g, x0, x1, y0, y1, TOPDECK - .08, TOPDECK, IRON)
    zr = TOPDECK
    for a, b, ss, se, dz in (((3.44, 4.14), (6.66, 4.14), False, False, 0),
                             ((3.44, 4.14), (3.44, 4.68), True, False, -.011),
                             ((3.44, 5.1), (3.44, 5.32), False, False, -.011),
                             ((3.44, 6.25), (3.44, 7.46), False, True, -.011),
                             ((3.44, 7.46), (5.86, 7.46), False, False, 0),
                             ((6.66, 4.14), (6.66, 5.86), True, False, -.011)):
        P.rail(g, a, b, zr, skip_start=ss, skip_end=se, dz=dz)
    for x, y in ((3.5, 4.3), (6.5, 4.3), (3.5, 7.3)):
        P.column(g, x, y, 2.0, TOPDECK - .08, .26)
    # Bracing between the columns (front and left faces).
    for (ax, ay), (bxx, by), n in (((3.5, 4.3), (6.5, 4.3), (0, -1)), ((3.5, 7.3), (3.5, 4.3), (-1, 0))):
        for k, (za, zb) in enumerate(((4.4, 7.1), (7.1, 9.8))):
            pa, pb = ((ax, ay), (bxx, by)) if k % 2 else ((bxx, by), (ax, ay))
            off = .16 + .02 * k
            g.beam((pa[0] + n[0] * off, pa[1] + n[1] * off, za), (pb[0] + n[0] * off, pb[1] + n[1] * off, zb),
                   .06, .1, IRON)
    for z in (7.1,):
        bx(g, 3.64, 6.36, 4.23, 4.37, z - .07, z + .07, IRON)
        bx(g, 3.43, 3.57, 4.44, 7.16, z - .04, z + .1, IRON)
    K.ladder(g, 3.3, 4.9, PODIUM[4], TOPDECK, face='left', width=.34, cage=True)
    # Rotating charging distributor and hopper on the furnace top.
    zt = 10.6
    dist = Geometry('ChargingDistributor', (cx, cy, zt))
    K.revolve(dist, (cx, cy, zt), [(.5, 0), (.5, .12), (.78, .62), (.78, .72)], IRON, segments=12)
    for k in range(4):
        a = k * math.pi / 2
        bx(dist, cx + math.cos(a) * .72 - .06, cx + math.cos(a) * .72 + .06,
           cy + math.sin(a) * .72 - .06, cy + math.sin(a) * .72 + .06, zt + .2, zt + .5, BRASS)
    for i in range(6):
        dist.rock((cx - .3 + i * .12, cy + (.15 if i % 2 else -.15), zt + .74 + .01 * i), (.2, .18, .14), IRON, 70 + i)
    parts.append((dist, 'SPIN_Z', 1))
    # Uptakes, junction, bleeders and the gooseneck downcomer to the dust catcher.
    J = (4.1, 5.8, 12.2)
    for a in (150, 180, 210):
        r = math.radians(a)
        P.tube(g, (cx + math.cos(r) * .6, cy + math.sin(r) * .6, 10.3), J, .15, IRON, 12)
    K.revolve(g, J, [(.2, -.3), (.36, -.12), (.36, .14), (.2, .3)], PAINTED, segments=16)
    for y in (5.65, 5.95):
        P.tube(g, (J[0], y, 12.4), (J[0], y, 13.5), .1, IRON, 10)
        g.cylinder((J[0], y, 13.55), .14, .1, BRASS, 'Z', 12)
    dc = (1.4, 5.6, 5.45)
    P.tube(g, J, dc, .26, IRON, 14)
    for f in (.3, .62):
        p = [J[i] + (dc[i] - J[i]) * f for i in range(3)]
        d = Vector(dc) - Vector(J)
        P.tube(g, Vector(p) - d.normalized() * .04, Vector(p) + d.normalized() * .04, .33, BRASS, 14)
    # Dust catcher.
    bx(g, .75, 2.05, 4.95, 6.25, 0, 1.2, CONCRETE)
    K.revolve(g, (1.4, 5.6, 1.2), [(.62, 0), (.62, 3.6), (.3, 4.2), (.26, 4.4)], IRON, segments=12)
    for z in (2.2, 3.4, 4.5):
        K.band(g, (1.4, 5.6, 0), .62, z, .08, PAINTED, segments=12)
    P.gauge(g, 1.4, 4.97, 2.0, 'front', .09)


# ------------------------------------------------------------------ stoves

def stoves(g):
    xs = (1.2, 2.85, 4.5)
    for x in xs:
        K.tank(g, x, 8.9, 0, .72, 8.3, mat=PAINTED, bands=6, roof='dome')
        P.gauge(g, x - .35, 8.9 - .66, 1.5, 'front', .08)
    # Hot-blast main to the bustle pipe, with a valve per stove.
    P.tube(g, (.95, 7.9, 3.62), (5.0, 7.9, 3.62), .2, IRON, 14)
    P.tube(g, (5.0, 7.9, 3.62), (5.0, 7.4, 3.62), .2, IRON, 14)
    g.cylinder((.93, 7.9, 3.62), .27, .06, BRASS, 'X', 14)
    g.cylinder((5.0, 7.9, 3.62), .24, .5, PAINTED, 'Z', 14)
    for x in xs:
        P.tube(g, (x, 7.95, 3.62), (x, 8.4, 3.62), .17, IRON, 12)
        g.cylinder((x, 8.08, 3.62), .26, .12, BRASS, 'Y', 14)
        K.valve_wheel(g, x, 7.96, 4.15, face='front', r=.16)
        P.tube(g, (x, 7.95, 3.9), (x, 7.95, 4.12), .03, IRON, 6)
    # Cold blast from the blower house; gas from the dust catcher.
    P.tube(g, (.45, 3.5, 2.6), (.45, 8.4, 2.6), .17, IRON, 12)
    P.tube(g, (.45, 8.4, 2.6), (.95, 8.4, 2.6), .17, IRON, 12)
    g.cylinder((.45, 8.4, 2.6), .21, .44, PAINTED, 'Z', 12)
    for y in (4.3, 6.3):
        g.cylinder((.45, y, 2.6), .25, .06, BRASS, 'Y', 12)
    K.pipe_run(g, [(1.9, 5.6, 4.6), (2.85, 5.6, 4.6), (2.85, 8.4, 4.6)], .14)
    # Stove chimney and flue.
    K.stack(g, 6.2, 9.3, 0, 11.0, emits='smoke', r=.3, bands=5)
    P.tube(g, (1.2, 9.75, 1.2), (6.1, 9.75, 1.2), .16, IRON, 12)
    # Service catwalk between the stoves at mid height.
    P.deck(g, .9, 4.8, 7.7, 8.15, 6, rails=('front',), bars=False)
    for x in (2.05, 3.7):
        g.beam((x, 8.3, 5.2), (x, 7.8, 5.9), .07, mat=IRON)


# ------------------------------------------------------------------ incline

def incline(g, parts):
    s_top, s_bot = .05, PLAN - .35
    for side in (-1, 1):
        off = PERP * side * .42
        a, b = on_incline(s_top) + off, on_incline(s_bot - .1) + off
        g.beam(a, b, .16, .3, PAINTED)                                   # top chord girder
        g.beam(a - NUP * .85, b - NUP * .85 + D * 0, .12, .16, IRON)      # bottom chord
        n = 12
        for k in range(n + 1):
            pa = a + (b - a) * k / n
            g.beam(pa - NUP * .1, pa - NUP * .8, .1, .1, IRON)            # verticals
            if k < n:
                pb = a + (b - a) * (k + 1) / n
                q = (pa - NUP * .78) if k % 2 == 0 else (pa - NUP * .12)
                r = (pb - NUP * .12) if k % 2 == 0 else (pb - NUP * .78)
                st = .07 if k % 2 == 0 else .09
                g.beam(q + PERP * side * st, r + PERP * side * st, .05, .08, IRON)
        # Track rail on the girder.
        g.beam(a + NUP * .17, b + NUP * .17, .05, .04, IRON)
    for k in range(13):
        c = on_incline(s_top + (s_bot - s_top - .1) * k / 12) - NUP * .25
        g.beam(c - PERP * .42, c + PERP * .42, .08, .08, IRON)
    # Support bents under the bottom chords: top one on the podium, lower on piers.
    for sb, base in ((2.4, PODIUM[4]), (4.0, 0)):
        feet = []
        for side in (-1, 1):
            q = on_incline(sb) + PERP * side * .42 - NUP * .85
            if math.hypot(q.x - F[0], q.y - F[1]) < 2.0:
                raise ValueError('Incline bent collides with the furnace')
            if base == 0:
                P.pier(g, q.x, q.y, 0, .5, .36)
                P.column(g, q.x, q.y, .55, q.z - .06, .2)
            else:
                if not (PODIUM[0] + .15 < q.x < PODIUM[1] - .15 and PODIUM[2] + .15 < q.y < PODIUM[3] - .15):
                    raise ValueError(f'Upper incline bent is off the podium: {q}')
                P.column(g, q.x, q.y, base, q.z - .06, .2)
            feet.append(q)
        q0, q1 = feet
        zl = q0.z - .3
        g.beam((q0.x, q0.y, zl), (q1.x, q1.y, zl), .14, mat=IRON)
        g.beam((q0.x, q0.y, base + .6), (q1.x, q1.y, zl - .15), .08, mat=IRON)
    # Skip pit and ore bunkers at the foot.
    # Skip pit and three bunkers, one tile each along the back edge.
    bx(g, 10.0, 11.0, 9.0, 10.0, 0, .5, CONCRETE)
    for x0, x1 in ((7.0, 8.0), (8.0, 9.0), (9.0, 10.0)):
        bx(g, x0, x1, 9.0, 10.0, 0, .25, CONCRETE)
        bx(g, x0, x1, 9.82, 10.0, .25, 1.3, CONCRETE)
        bx(g, x0 + .02, x0 + .14, 9.0, 9.82, .25, 1.1, CONCRETE)
        bx(g, x1 - .14, x1 - .02, 9.0, 9.82, .25, 1.1, CONCRETE)
        P.ore_heap(g, (x0 + x1) / 2, 9.42, .25, .4, .32, h=.7, mats=(IRON, IRON, BRASS), seed=int(x0 * 10))
    # Skip car.
    s0 = PLAN - .95
    c0 = on_incline(s0) + NUP * .6
    car = Geometry('SkipCar', tuple(c0))
    P.oriented_box(car, c0, D, PERP, NUP, (.42, .34, .3), FORGED)
    P.oriented_box(car, c0 + NUP * .28, D, PERP, NUP, (.45, .37, .05), PAINTED)
    for sd in (-1, 1):
        for sp in (-1, 1):
            w = c0 + D * sd * .3 + PERP * sp * .38 - NUP * .3
            P.oriented_box(car, w, D, PERP, NUP, (.1, .03, .1), IRON)
    for i in range(5):
        car.rock(tuple(c0 + NUP * .36 + D * (i - 2) * .15), (.2, .18, .14), IRON, 90 + i)
    parts.append((car, 'CUSTOM_INCLINE', (s0 - .45) * L3))


# ------------------------------------------------------------------ casting & yard

def casting_bay(g, parts):
    bx(g, 3.0, 7.0, 0.0, 4.0, 0, .2, CONCRETE)   # bay floor on tiles 3..7 x 0..4
    for x in (3.2, 5.0, 6.8):
        for y in (.45, 3.55):
            P.column(g, x, y, .2, 3.76, .18)
            g.beam((x, y, 3.72), (x, 2.0, 4.6), .1 if y < 1 else .09, .12, IRON)
        bx(g, x - .08, x + .08, 1.8, 2.2, 4.42, 4.68, PAINTED)
        bx(g, x - .06, x + .06, .5, 3.5, 3.0, 3.12, IRON)
    P.plank_gable(g, 3.1, 6.9, .45, 3.55, 3.85, 4.75, ridge_axis='X', seed=81, gable=False)
    # Back wall of the bay (plank boards on a solid core) toward the podium.
    # Runner trough down from the podium to the ladle.
    y0, z0, y1, z1 = PODIUM[2] - .05, 2.0, 3.25, 1.62
    P.slab_quad(g, [(4.8, y1, z1), (5.2, y1, z1), (5.2, y0, z0), (4.8, y0, z0)], (0, .4, 1), .1, FORGED)
    P.slab_quad(g, [(4.93, y1 + .05, z1 + .006), (5.07, y1 + .05, z1 + .006), (5.07, y0, z0 + .006),
                    (4.93, y0, z0 + .006)], (0, .4, 1), .005, GLOW)
    g.beam((5.0, 3.8, .2), (5.0, 3.8, 1.75), .12, mat=IRON)
    # Ladle stand and tilting ladle.
    lc = (5.0, 2.75, 1.45)
    for x in (4.45, 5.55):
        g.beam((x, 2.35, .2), (x, 2.75, 1.48), .1, mat=IRON)
        g.beam((x, 3.15, .2), (x, 2.75, 1.48), .09, mat=IRON)
        bx(g, x - .07, x + .07, 2.55, 2.95, 1.3, 1.62, BRASS)
    lad = Geometry('Ladle', lc)
    K.revolve(lad, (5.0, 2.75, .82), [(.3, 0), (.42, .25), (.45, .62), (.47, .72)], PAINTED, segments=12)
    lad.cylinder((5.0, 2.75, 1.555), .43, .02, GLOW, 'Z', 16)
    for z in (1.0, 1.3):
        K.band(lad, (5.0, 2.75, 0), .44 if z < 1.2 else .46, z, .06, IRON, segments=12)
    lad.cylinder((5.0, 2.75, 1.45), .05, 1.06, IRON, 'X', 10)
    bx(lad, 4.93, 5.07, 2.22, 2.35, 1.42, 1.52, PAINTED)
    parts.append((lad, 'SWAY_X', .18))
    stream = Geometry('PourStream', (5.0, 2.24, 1.4))
    bx(stream, 4.97, 5.03, 2.21, 2.27, .52, 1.4, GLOW)
    parts.append((stream, 'FLAME', 0))
    # Pig moulds on a casting line.
    for side in (1.74, 2.26):
        bx(g, 3.5, 6.5, side - .03, side + .03, .2, .32, IRON)
    for i in range(7):
        x = 5.0 + (i - 3) * .42
        bx(g, x - .17, x + .17, 1.66, 2.34, .32, .5, IRON)
        if i in (2, 3, 4):
            bx(g, x - .12, x + .12, 1.73, 2.27, .5, .52, GLOW)
        else:
            bx(g, x - .12, x + .12, 1.73, 2.27, .5, .54, IRON)
    K.lamp(g, 3.2, .36, 2.6, face='front')
    K.lamp(g, 6.8, .36, 2.6, face='front')


def blower_house(g, parts):
    # Plinth course (core + .05) on tiles 0..3 x 0..4; door face stays .18.
    P.hall(g, .05, 2.95, .3, 3.95, 3.6, plinth=.6, doors=[1.5], pitch=1.0,
           windows={'left': [(.76, 2.1), (1.67, 2.1), (2.58, 2.1)], 'right': [(.76, 2.1), (3.49, 2.1)],
                    'back': [(2.55, 2.1)]},
           lamps=[('front', .78, 1.35), ('front', 2.22, 1.35)])
    P.plank_gable(g, .05, 2.95, .3, 3.95, 3.6, 5.0, ridge_axis='Y', seed=91)
    g.ring((1.5, .18, 4.0), .42, .07, .14, IRON, 'Y', 16)
    parts.append((P.rotor('GableFan', (1.5, .2, 4.0), .34, 'Y', 6), 'SPIN_Y', 4))
    K.stack(g, 2.4, 4.3, 0, 6.0, emits='smoke', r=.17, bands=3)


def build(g, parts):
    podium(g)
    furnace(g, parts)
    stoves(g)
    incline(g, parts)
    casting_bay(g, parts)
    blower_house(g, parts)


def animate(obj, kind, value, frame_end):
    """Skip car: haul up the incline, tip, return."""
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
