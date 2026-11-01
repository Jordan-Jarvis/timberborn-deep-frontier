"""Mission Control: the civic and scientific heart of the space program.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the terrace barrels, shrubs and street lamps.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; outputs/compaction/BRIEF.md): 12x10x16 -> 8x7x9. One layer per floor:
the podium is one storey and the control hall two storeys of one layer each
under a plank gable.

Shrunk again 2026-11-01 (user: "we need to shrink the buildings down even
more"): 8x7x9 -> 5x5x7, inside the old footprint with the same origin. The
door moves from x 5.5 (outside a 5-wide footprint) to x 3.5, under the
tower (at x 4.5 its portal frame stood past the corner), so the native
entrance moves two tiles left ((5,-1) -> (3,-1)). The control hall is 3x3 on
the podium's back-right tiles, the tower rises through its front wall, the
observatory and the dish share the left column; cab, dish and dome are
smaller and the tower two layers lower.

Hero: a launch-control tower rising from the control hall: an octagonal
concrete shaft carrying a cantilevered, outward-leaning glazed control cab
with an antenna mast and beacon, beside a teal-domed telescope observatory
with a rotating slit and a white steerable radio dish.
Roof types: a teal native plank gable over the control hall (the tower
rises through its front); flat overhanging cab roof with the turning radar on
its equipment drum; ribbed teal observatory dome; flat terrace on the podium
(roof-variety pass: no roof posts or vents).

Animated (names unchanged): observatory dome (slews back and forth), dish
turret (yaw) and dish (yaw + elevation), radar bar (spin, on the cab
roof's equipment drum), cab, tower and mast beacons (spin).
"""
import math

from mathutils import Quaternion, Vector

from lategame_kit import *
from frontier_architecture import Geometry
from architectural_windows import window
from lategame_space_parts import (bx, door_block, pilasters, gauge, tube, arc_bar, place, BURY, animate)
from lategame_civic_parts import octagon_frustum, facet_window

IDENT = 'MissionControl'
FOOTPRINT = (5, 5)
HEIGHT = 7
FRAME_END = 121
HERO = ('Launch-control tower with a cantilevered, outward-leaning glazed cab and antenna mast, beside a teal '
        'telescope dome and a steerable radio dish')

POD = (0.0, .15, 5.0, 5.0)     # podium; front (door) face .15 off the tile edge
POD_TOP = 1.0                  # terrace on a whole layer
HALL = (2.0, 2.0, 5.0, 5.0)    # control hall on the podium, tiles 2..5 x 2..5
HALL_TOP = 2.84                # roof slab bottom; its top is layer 3
STRING = 2.0                   # one layer per storey
DOOR_X = 3.5
TOWER = (3.0, 1.4, 4.2, 2.6)   # octagonal shaft bounds (apothem .6)
SHAFT_TOP = 4.0                # control-tower shaft top (corbel above)
CAB_FLOOR, CAB_TOP = 4.35, 5.4
OBS = (1.05, 3.9)
OBS_R = .85
DRUM_TOP = 2.4
DISH = (1.2, 1.2)
PIVOT_Z = 2.75
PED_TOP = 1.92                 # dish pedestal top (coping top) on layer 2


def podium(g, parts):
    x0, y0, x1, y1 = POD
    door_block(g, x0, y0, x1, y1, 0, POD_TOP, DOOR_X, CONCRETE, door_id='MissionControlEntrance')
    pilasters(g, 'X', y0, x0, x1, .05, POD_TOP - .12, -1, skip=[(DOOR_X - .5, DOOR_X + .5)])
    pilasters(g, 'Y', x0, y0, y1, .05, POD_TOP - .12, -1)
    pilasters(g, 'Y', x1, y0, y1, .05, POD_TOP - .12, 1)
    pilasters(g, 'X', y1, x0, x1, .05, POD_TOP - .12, 1)
    # The terrace is an open platform edge to edge (no parapet: user, 2026-10-31).
    lamp(g, DOOR_X - .7, y0, .7, face='front')
    lamp(g, DOOR_X + .7, y0, .7, face='front')


def hall(g):
    x0, y0, x1, y1 = HALL
    bx(g, x0, y0, POD_TOP - BURY, x1 - .07, y1 - .07, HALL_TOP - .02, CONCRETE)
    for (a, b, c, d) in ((x0 + .1, y0 - .08, x1 - .1, y0 + .1), (x0 - .08, y0 - .08, x0 + .1, y1 - .1)):
        bx(g, a, b, POD_TOP + .02, c, d, 1.3, CONCRETE)   # walls start on its top
    tx0, _, tx1, _ = TOWER
    # Two storeys of one layer each: tall windows below the string course, one tier above.
    for lo, hi, zw in ((1.3, STRING, (1.62,)), (STRING + .12, HALL_TOP, (2.47,))):
        frame_wall(g, 'X', y0, x0 - .05, tx0, lo, hi, outward=-1, infill=ORANGE, post=WOOD, bays=1,
                   windows=[((x0 + tx0) / 2, z) for z in zw], window_style='grand', window_scale=.62)
        frame_wall(g, 'X', y0, tx1, x1 - .1, lo, hi, outward=-1, infill=ORANGE, post=WOOD, bays=1,
                   windows=[((tx1 + x1 - .1) / 2, z) for z in zw], window_style='grand', window_scale=.5)
        n = 3
        ys = [y0 + .1 + (y1 - .15 - y0 - .2) * (k + .5) / n for k in range(n)]
        frame_wall(g, 'Y', x0, y0 + .1, y1 - .2, lo, hi, outward=-1, infill=ORANGE, post=WOOD, bays=n,
                   windows=[(y, z) for y in ys for z in zw if not (3.3 < y < 4.5) or lo > 2], window_style='grand',
                   window_scale=.62)
        # Right and back walls on the footprint edges (outer infill faces on x 8 / y 7).
        frame_wall(g, 'Y', x1 - .05, y0 + .1, y1 - .15, lo, hi, outward=1, infill=ORANGE, post=WOOD, bays=n,
                   windows=[(y, z) for y in ys for z in zw], window_style='grand', window_scale=.62)
        xs = [x0 + .1 + (x1 - .25 - x0) * (k + .5) / 3 for k in range(3)]
        frame_wall(g, 'X', y1 - .05, x0 + .1, x1 - .15, lo, hi, outward=1, infill=ORANGE, post=WOOD, bays=3,
                   windows=[(x, z) for x in xs for z in zw], window_style='grand', window_scale=.62)
    bx(g, x0 - .15, y0 - .15, STRING - .02, x1 + .03, y1 + .03, STRING + .12, CONCRETE)
    # Plank gable over the hall (roof variety); its front end sits just behind
    # the tower's front face, which rises through it.
    import lategame_mining_parts as M
    M.plank_gable(g, x0 - .1, x1 - .12, y0 - .08, y1 - .12, HALL_TOP, HALL_TOP + 1.0, ridge_axis='Y',
                  overhang=.08, seed=17)


def tower(g, parts):
    """Launch-control tower: octagonal shaft, cantilevered glazed cab, mast."""
    x0, y0, x1, y1 = TOWER
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ap = (x1 - x0) / 2
    octagon_frustum(g, cx, cy, POD_TOP - BURY, HALL_TOP + .2, ap, ap, CONCRETE, cap_top=False)
    octagon_frustum(g, cx, cy, HALL_TOP + .2, SHAFT_TOP, ap, ap - .1, CONCRETE, cap_bottom=False, cap_top=False)
    for z in (2.0, 3.6):
        a_z = ap if z < HALL_TOP + .2 else ap - .1 * (z - HALL_TOP - .2) / (SHAFT_TOP - HALL_TOP - .2)
        octagon_frustum(g, cx, cy, z - .05, z + .05, a_z + .03, a_z + .03, IRON)
    facet_window(g, cx, cy, 270, ap, 1.15, ap, 1.95, .5, .45, 'factory')
    facet_window(g, cx, cy, 270, ap, HALL_TOP + .2, ap - .1, SHAFT_TOP, .5, .45, 'factory')
    # Corbelled cab floor: the cantilever soffit flares out to the cab.
    octagon_frustum(g, cx, cy, SHAFT_TOP, CAB_FLOOR, ap - .1, .92, CONCRETE, cap_bottom=False)
    octagon_frustum(g, cx, cy, CAB_FLOOR, CAB_FLOOR + .1, .98, .98, CONCRETE)
    za, zb, ra, rb = CAB_FLOOR + .1, CAB_TOP, .9, 1.06
    octagon_frustum(g, cx, cy, za, zb, ra, rb, IRON)
    for i in range(8):
        facet_window(g, cx, cy, 45 * i, ra, za, rb, zb, .5, .8, 'factory')
    k = 1 / math.cos(math.pi / 8)
    for i in range(8):
        a = math.radians(22.5 + 45 * i)
        p = (cx + math.cos(a) * (ra * k + .02), cy + math.sin(a) * (ra * k + .02), za + .01)
        q = (cx + math.cos(a) * (rb * k + .02), cy + math.sin(a) * (rb * k + .02), zb - .01)
        g.beam(p, q, .07, .05, PAINTED)
    octagon_frustum(g, cx, cy, CAB_TOP, CAB_TOP + .12, 1.16, 1.16, CONCRETE)
    octagon_frustum(g, cx, cy, CAB_TOP + .12, CAB_TOP + .45, .42, .38, FORGED)
    octagon_frustum(g, cx, cy, CAB_TOP + .45, CAB_TOP + .52, .45, .45, IRON)
    pivot = beacon(g, cx + .6, cy - .6, CAB_TOP + .12)
    parts.append((beacon_shutter(*pivot, 'MissionControl.CabBeacon'), 'SPIN_Z', 3))
    mast_top = 6.6
    bx(g, cx - .035, cy - .035, CAB_TOP + .52, cx + .035, cy + .035, mast_top, IRON)
    for z, w in ((5.85, .26), (6.25, .18)):
        bx(g, cx - w, cy - .02, z - .02, cx + w, cy + .02, z + .02, IRON)
        bx(g, cx - .02, cy - w, z + .04, cx + .02, cy + w, z + .08, IRON)
    pivot = beacon(g, cx, cy, mast_top)
    parts.append((beacon_shutter(*pivot, 'MissionControl.TowerBeacon'), 'SPIN_Z', 2))


def observatory(g, parts):
    cx, cy = OBS
    revolve(g, (cx, cy, POD_TOP - BURY), [(OBS_R, 0), (OBS_R, DRUM_TOP - POD_TOP + BURY)], CONCRETE, segments=16)
    band(g, (cx, cy, 0), OBS_R, DRUM_TOP - .06, .14, CONCRETE, segments=16, proud=.05)
    band(g, (cx, cy, 0), OBS_R, POD_TOP + .1, .16, CONCRETE, segments=16, proud=.04)
    for i in range(8):
        a = (i + .5) * 2 * math.pi / 8
        px, py = cx + math.cos(a) * (OBS_R + .02), cy + math.sin(a) * (OBS_R + .02)
        g.beam((px, py, POD_TOP + .18), (px, py, DRUM_TOP - .13), .09, mat=CONCRETE)
    # Link block to the hall, with a small window.
    bx(g, cx + .6, 3.4, POD_TOP - BURY, HALL[0] + .05, 4.4, 2.0, CONCRETE)
    bx(g, cx + .55, 3.35, 1.98, HALL[0] + .05, 4.45, 2.08, IRON)
    zc = DRUM_TOP + .02
    dm = Geometry('MissionControl.ObservatoryDome', (cx, cy, zc))
    R = OBS_R + .05
    revolve(dm, (cx, cy, zc), [(R, 0), (R, .1)], IRON, segments=16, cap_bottom=True, cap_top=False)
    dome(dm, (cx, cy, zc + .1), R, ROOF, segments=16, rings=8)
    az = -math.pi / 2 - .5
    for k in range(8):
        a = az + (k + .5) * 2 * math.pi / 8
        if abs(math.cos(a - az)) > .9 and math.cos(a - az) > 0:
            continue
        arc_bar(dm, (cx, cy, zc + .1), R - .02, R + .04, .035, a, .12, math.pi / 2 - .02, IRON, steps=8)
    arc_bar(dm, (cx, cy, zc + .1), R - .03, R + .03, .16, az, -.25, math.pi / 2 - .02, IRON, steps=12)
    for s in (-1, 1):
        arc_bar(dm, (cx, cy, zc + .1), R - .02, R + .07, .04, az + s * .17, .32, math.pi / 2 - .02, BRASS, steps=10)
    el = .75
    dvec = Vector((math.sin(el) * math.cos(az), math.sin(el) * math.sin(az), math.cos(el)))
    base = Vector((cx, cy, zc + .2))
    tube(dm, tuple(base - dvec * .2), tuple(base + dvec * (R + .3)), .12, IRON, segments=14)
    for f in (.3, .7, 1.05):
        tube(dm, tuple(base + dvec * (f - .035)), tuple(base + dvec * (f + .035)), .15, BRASS, segments=14)
    tube(dm, tuple(base + dvec * (R + .3)), tuple(base + dvec * (R + .35)), .14, IRON, segments=14)
    parts.append((dm, 'CUSTOM_YAW_OSC', (.85, 1)))


def dish(g, parts):
    cx, cy = DISH
    pt = PED_TOP
    bx(g, cx - .55, cy - .55, POD_TOP - BURY, cx + .55, cy + .55, pt, CONCRETE)
    bx(g, cx - .6, cy - .6, pt - .08, cx + .6, cy + .6, pt + .06, CONCRETE)
    bx(g, cx - .6, cy - .6, POD_TOP + .42, cx + .6, cy + .6, POD_TOP + .5, CONCRETE)
    window(g, cx + .25, cy - .55, POD_TOP + .62, .32, 'front', 'factory')
    revolve(g, (cx, cy, pt + .04), [(.46, 0), (.46, .14)], IRON, segments=12)
    g.ring((cx, cy, pt + .16), .5, .04, .05, BRASS, 'Z', 12)
    yaw = .35
    zt = pt + .2
    tur = Geometry('MissionControl.DishTurret', (cx, cy, zt))
    revolve(tur, (cx, cy, zt), [(.42, 0), (.42, .24), (.32, .31)], PAINTED, segments=12)
    for s in (-1, 1):
        x = cx + s * .47
        tur.box((x, cy, (zt + .24 + PIVOT_Z) / 2), (.13, .3, PIVOT_Z - zt - .24 + .18), IRON)
        tur.beam((cx + s * .24, cy, zt + .26), (x, cy, zt + .56), .09, mat=IRON)
        tur.cylinder((x, cy, PIVOT_Z), .12, .16, BRASS, 'X', 12)
    tur.box((cx, cy + .26, zt + .4), (.38, .2, .3), FORGED)
    gauge(tur, cx, cy + .36, zt + .44, 'back', .07)
    parts.append((tur, 'CUSTOM_DISH_YAW', (yaw, 0)))
    tilt = Quaternion((1, 0, 0), math.radians(50))

    def build(t):
        R, f = .85, .56
        prof = [(r, r * r / (4 * f)) for r in (.16, .25, .38, .52, .67, R)]
        hollow_revolve(t, (0, 0, .24), prof, .05, IRON, segments=16, inner_mat=CONCRETE)
        band(t, (0, 0, 0), R, .24 + R * R / (4 * f), .05, BRASS, segments=16, proud=.015)
        revolve(t, (0, 0, .1), [(.22, 0), (.22, .16), (.2, .2)], IRON, segments=16)
        for i in range(8):
            a = i * math.pi / 4
            for r0, r1 in ((.18, .38), (.38, .6), (.6, R - .04)):
                p0 = (math.cos(a) * r0, math.sin(a) * r0, .24 + r0 * r0 / (4 * f) - .06)
                p1 = (math.cos(a) * r1, math.sin(a) * r1, .24 + r1 * r1 / (4 * f) - .06)
                t.beam(p0, p1, .04, mat=PAINTED)
        t.box((0, 0, .06), (.7, .14, .12), IRON)
        for i in range(3):
            a = math.pi / 2 + i * 2 * math.pi / 3
            rim = (math.cos(a) * (R - .08), math.sin(a) * (R - .08), .24 + (R - .08) ** 2 / (4 * f) + .03)
            t.beam(rim, (0, 0, .24 + f - .04), .03, mat=IRON)
        revolve(t, (0, 0, .24 + f - .08), [(.09, 0), (.09, .07), (.06, .24), (0, .26)], BRASS, segments=10)
    dg = Geometry('MissionControl.Dish', (cx, cy, PIVOT_Z))
    place(dg, build, tilt.inverted(), (cx, cy, PIVOT_Z))
    parts.append((dg, 'CUSTOM_DISH', (yaw, .22)))


def radar(g, parts):
    """Turning radar bar on the cab roof's equipment drum, round the mast."""
    x0, y0, x1, y1 = TOWER
    x, y = (x0 + x1) / 2, (y0 + y1) / 2
    rz = CAB_TOP + .66
    rd = Geometry('MissionControl.Radar', (x, y, rz))
    rd.cylinder((x, y, rz - .07), .09, .14, PAINTED, 'Z', 12)
    rd.box((x, y, rz + .06), (.8, .09, .12), IRON)
    for k in range(5):
        rd.box((x - .32 + k * .16, y - .06, rz + .06), (.045, .035, .19), BRASS)
    rd.box((x, y + .065, rz + .06), (.22, .07, .07), FORGED)
    parts.append((rd, 'SPIN_Z', 1))


def build(g, parts):
    podium(g, parts)
    hall(g)
    tower(g, parts)
    observatory(g, parts)
    dish(g, parts)
    radar(g, parts)
