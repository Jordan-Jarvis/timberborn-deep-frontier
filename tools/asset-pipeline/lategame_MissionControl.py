"""Mission Control: the civic and scientific heart of the space program.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the terrace barrels, shrubs and street lamps.

Hero: a launch-control tower rising from a grand control hall: a tapering
octagonal concrete shaft carrying a cantilevered, outward-leaning glazed
control cab with an antenna mast and beacon, flanked by a teal-domed telescope
observatory with a rotating slit and a big white steerable radio dish.
Roof types: flat concrete roof with a parapet over the hall; flat overhanging
cab roof with an equipment drum; ribbed teal observatory dome.

Parts: a cast concrete podium with the main entrance under the tower and a
terrace with REDIC lamps; the control hall with dark timber pilasters,
orange plaster and two tiers of native grand windows; the control tower with
iron-banded shaft, slot windows, a corbelled cab floor, a ring of factory
glazing between steel mullions and an antenna mast with crossbars and a
beacon; the observatory drum and dome with slit shutters
and a brass telescope; the dish on a yoke turret; two lattice antenna masts
with a wire aerial, one carrying a rotating radar bar; cable trays.

Animated: observatory dome (slews back and forth), dish turret (yaw) and dish
(yaw + elevation), radar bar (spin), tower and mast beacons (spin).
"""
import math

from mathutils import Quaternion, Vector

from lategame_kit import *
from frontier_architecture import Geometry
from architectural_windows import window
from native_building_assets import barrel, plant
from lategame_space_parts import (bx, door_block, pilasters, coping_ring, gauge, ball, pipe, rail, lattice,
                                  tube, arc_bar, place, BURY, animate)
from lategame_civic_parts import octagon_frustum, facet_window

IDENT = 'MissionControl'
FOOTPRINT = (12, 10)
HEIGHT = 16
FRAME_END = 121
HERO = ('Launch-control tower with a cantilevered, outward-leaning glazed cab and antenna mast, between a teal '
        'telescope dome and a big steerable radio dish')

POD = (0.0, 1.0, 12.0, 10.0)   # whole tiles to the footprint edges
POD_TOP = 1.0                  # terrace on a whole layer
HALL = (3.4, 2.6, 7.6, 8.0)
HALL_TOP = 6.4
STRING = 4.5
TOWER = (4.7, 1.7, 6.3, 3.3)
SHAFT_TOP = 9.4             # control-tower shaft top (corbel above)
CAB_FLOOR, CAB_TOP = 10.0, 11.35
OBS = (2.08, 5.6)
OBS_R = 1.35
DRUM_TOP = 4.9
DISH = (9.6, 6.1)
PIVOT_Z = 5.3
PED_TOP = 2.92                 # dish service platform (coping top) on layer 3


def parapet_ring(g, x0, y0, x1, y1, z, *, h=.35, t=.14, mat=CONCRETE, skip_front=None):
    """Closed parapet with a separate steel cap on each run (no lid over the roof)."""
    runs = [(x0, y0, x1, y0 + t), (x0, y1 - t, x1, y1), (x0, y0 + t, x0 + t, y1 - t), (x1 - t, y0 + t, x1, y1 - t)]
    for (a, b, c, d) in runs:
        if skip_front and b == y0 and d == y0 + t:
            for (sa, sc) in ((a, skip_front[0]), (skip_front[1], c)):
                if sc - sa > .05:
                    bx(g, sa, b, z, sc, d, z + h, mat)
                    bx(g, sa - .03 * (sa == a), b - .03, z + h - .01, sc + .03 * (sc == c), d + .03, z + h + .05, IRON)
            continue
        bx(g, a, b, z, c, d, z + h, mat)
    bx(g, x0 - .03, y1 - t - .03, z + h - .01, x1 + .03, y1 + .03, z + h + .05, IRON)
    bx(g, x0 - .03, y0 + t + .03, z + h - .01, x0 + t + .03, y1 - t - .03, z + h + .05, IRON)
    bx(g, x1 - t - .03, y0 + t + .03, z + h - .01, x1 + .03, y1 - t - .03, z + h + .05, IRON)
    if not skip_front:
        bx(g, x0 - .03, y0 - .03, z + h - .01, x1 + .03, y0 + t + .03, z + h + .05, IRON)


def podium(g, parts):
    x0, y0, x1, y1 = POD
    door_block(g, x0, y0, x1, y1, 0, POD_TOP, 5.5, CONCRETE, door_id='MissionControlEntrance')
    # The door is a full storey: the coping band is split over the portal
    # head and a thin coping strip, lifted clear of the portal top, closes
    # the door notch under the terrace edge.
    w, pr, h = .22, .04, .14
    zb, zt = POD_TOP - h + .04, POD_TOP + .04
    bx(g, 5.0 - LAYER_GAP, y0 - pr, POD_TOP + LAYER_GAP, 6.0 + LAYER_GAP, y0 + .2, zt, CONCRETE)
    for a, b in ((x0 - pr, 5.0 - LAYER_GAP), (6.0 + LAYER_GAP, x1 + pr)):
        bx(g, a, y0 - pr, zb, b, y0 - pr + w, zt, CONCRETE)
    bx(g, x0 - pr, y1 + pr - w, zb, x1 + pr, y1 + pr, zt, CONCRETE)
    bx(g, x0 - pr, y0 - pr + w, zb, x0 - pr + w, y1 + pr - w, zt, CONCRETE)
    bx(g, x1 + pr - w, y0 - pr + w, zb, x1 + pr, y1 + pr - w, zt, CONCRETE)
    pilasters(g, 'X', y0, x0, x1, .05, POD_TOP - .12, -1, skip=[(5.0, 6.0)])
    pilasters(g, 'Y', x0, y0, y1, .05, POD_TOP - .12, -1)
    pilasters(g, 'Y', x1, y0, y1, .05, POD_TOP - .12, 1)
    pilasters(g, 'X', y1, x0, x1, .05, POD_TOP - .12, 1)
    # Terrace balustrade along the front and sides (open at the tower).
    z = POD_TOP + .04
    for xa, xb in ((x0 + .1, 4.3), (6.7, x1 - .1)):
        bx(g, xa, y0 + .06, z - .02, xb, y0 + .2, z + .3, CONCRETE)
        bx(g, xa - .03, y0 + .03, z + .29, xb + .03, y0 + .23, z + .35, IRON)
    # Door canopy: steel brackets under a small teal awning.
    extrude_profile(g, [(y0 - .45, 1.22), (y0 + .02, 1.1), (y0 + .02, 1.18), (y0 - .45, 1.3)][::-1], 4.85, 6.15,
                    ROOF, axis='X')
    for x in (4.95, 6.05):
        g.beam((x, y0 + .01, .85), (x, y0 - .4, 1.2), .06, mat=IRON)
    lamp(g, 4.85, y0, .95, face='front')
    lamp(g, 6.15, y0, .95, face='front')


def hall(g):
    x0, y0, x1, y1 = HALL
    bx(g, x0, y0, POD_TOP - BURY, x1, y1, HALL_TOP, CONCRETE)
    # Concrete plinth band, proud of the framed walls.
    for (a, b, c, d) in ((x0 + .1, y0 - .08, x1 - .1, y0 + .1), (x0 + .1, y1 - .1, x1 - .1, y1 + .08),
                         (x0 - .08, y0 - .08, x0 + .1, y1 + .08), (x1 - .1, y0 - .08, x1 + .08, y1 + .08)):
        bx(g, a, b, POD_TOP + .02, c, d, 1.6, CONCRETE)   # walls start on its top
    tx0, _, tx1, _ = TOWER
    # Two storeys: tall paired windows below a concrete string course, one tier above.
    for lo, hi, zw in ((1.6, STRING, (2.5, 3.8)), (STRING + .12, HALL_TOP, (5.45,))):
        frame_wall(g, 'X', y0, x0 - .05, tx0, lo, hi, outward=-1, infill=ORANGE, post=WOOD, bays=1,
                   windows=[((x0 + tx0) / 2, z) for z in zw], window_style='grand')
        frame_wall(g, 'X', y0, tx1, x1 + .05, lo, hi, outward=-1, infill=ORANGE, post=WOOD, bays=1,
                   windows=[((tx1 + x1) / 2, z) for z in zw], window_style='grand')
        n = 5
        ys = [y0 + .1 + (y1 - y0 - .2) * (k + .5) / n for k in range(n)]
        frame_wall(g, 'Y', x1, y0 + .1, y1 - .1, lo, hi, outward=1, infill=ORANGE, post=WOOD, bays=n,
                   windows=[(y, z) for y in ys for z in zw], window_style='grand')
        frame_wall(g, 'Y', x0, y0 + .1, y1 - .1, lo, hi, outward=-1, infill=ORANGE, post=WOOD, bays=n,
                   windows=[(y, z) for y in ys for z in zw if lo > 4 or y < 4.0 or y > 7.2], window_style='grand')
        xs = [x0 + .1 + (x1 - x0 - .2) * (k + .5) / 3 for k in range(3)]
        frame_wall(g, 'X', y1, x0 + .1, x1 - .1, lo, hi, outward=1, infill=ORANGE, post=WOOD, bays=3,
                   windows=[(x, z) for x in xs for z in zw], window_style='grand')
    bx(g, x0 - .16, y0 - .16, STRING - .02, x1 + .16, y1 + .16, STRING + .14, CONCRETE)
    # Cornice and flat roof with parapet.
    bx(g, x0 - .14, y0 - .14, HALL_TOP - .02, x1 + .14, y1 + .14, HALL_TOP + .16, CONCRETE)
    parapet_ring(g, x0 - .1, y0 - .1, x1 + .1, y1 + .1, HALL_TOP + .14, h=.32, skip_front=(TOWER[0] - .1, TOWER[2] + .1))
    # Roof equipment: vents and an instrument hut.
    for x, y in ((4.0, 7.3), (7.0, 7.3)):
        revolve(g, (x, y, HALL_TOP + .12), [(.16, 0), (.16, .45), (.24, .5), (.24, .56), (0, .62)], IRON, segments=12)
    # Raised control-room monitor with a band of factory windows.
    mx0, my0, mx1, my1 = 4.0, 5.2, 7.0, 7.4
    bx(g, mx0, my0, HALL_TOP + .1, mx1, my1, HALL_TOP + 1.15, FORGED)
    for x in (mx0 + .5 + k * 1.0 for k in range(3)):
        window(g, x, my0, HALL_TOP + .62, .7, 'front', 'factory')
    for y in (my0 + .55, my1 - .55):
        window(g, mx0, y, HALL_TOP + .62, .7, 'left', 'factory')
        window(g, mx1, y, HALL_TOP + .62, .7, 'right', 'factory')
    for x in (mx0, mx1):
        for y in (my0, my1):
            bx(g, x - .06, y - .06, HALL_TOP + .1, x + .06, y + .06, HALL_TOP + 1.13, WOOD)
    bx(g, mx0 - .14, my0 - .14, HALL_TOP + 1.13, mx1 + .14, my1 + .14, HALL_TOP + 1.27, CONCRETE)
    bx(g, 6.6, 4.0, HALL_TOP + .12, 7.2, 5.0, HALL_TOP + .75, FORGED)
    bx(g, 6.55, 3.95, HALL_TOP + .74, 7.25, 5.05, HALL_TOP + .82, IRON)
    gauge(g, 6.9, 4.0, HALL_TOP + .45, 'front', .1)


def tower(g, parts):
    """Launch-control tower: octagonal shaft, cantilevered glazed cab, mast."""
    x0, y0, x1, y1 = TOWER
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ap = (x1 - x0) / 2                       # shaft apothem: flat side facets on x0 / x1
    # Octagonal shaft: straight to the hall roof, then tapering to the corbel.
    octagon_frustum(g, cx, cy, POD_TOP - BURY, HALL_TOP + .2, ap, ap, CONCRETE, cap_top=False)
    octagon_frustum(g, cx, cy, HALL_TOP + .2, SHAFT_TOP, ap, ap - .14, CONCRETE, cap_bottom=False, cap_top=False)
    for z in (3.4, 5.0, 8.2):
        a_z = ap if z < HALL_TOP + .2 else ap - .14 * (z - HALL_TOP - .2) / (SHAFT_TOP - HALL_TOP - .2)
        octagon_frustum(g, cx, cy, z - .05, z + .05, a_z + .03, a_z + .03, IRON)
    # Slot windows up the front and front-diagonal facets.
    for z in (2.6, 4.2, 5.8):
        facet_window(g, cx, cy, 270, ap, z - .5, ap, z + .5, .5, .55, 'factory')
    for ang in (225, 315):
        facet_window(g, cx, cy, ang, ap, 4.2 - .5, ap, 4.2 + .5, .5, .45, 'factory')
    zt0 = HALL_TOP + .2
    facet_window(g, cx, cy, 270, ap, zt0, ap - .14, SHAFT_TOP, .55, .55, 'factory')
    # Corbelled cab floor: the cantilever soffit flares out to the cab.
    octagon_frustum(g, cx, cy, SHAFT_TOP, CAB_FLOOR, ap - .14, 1.42, CONCRETE, cap_bottom=False)
    octagon_frustum(g, cx, cy, CAB_FLOOR, CAB_FLOOR + .12, 1.5, 1.5, CONCRETE)
    # Outward-leaning glazed cab: dark steel core, one factory light per facet,
    # steel mullions on the eight corners.
    za, zb, ra, rb = CAB_FLOOR + .12, CAB_TOP, 1.4, 1.62
    octagon_frustum(g, cx, cy, za, zb, ra, rb, IRON)
    for i in range(8):
        facet_window(g, cx, cy, 45 * i, ra, za, rb, zb, .5, 1.18, 'factory')
    k = 1 / math.cos(math.pi / 8)
    for i in range(8):
        a = math.radians(22.5 + 45 * i)
        p = (cx + math.cos(a) * (ra * k + .02), cy + math.sin(a) * (ra * k + .02), za + .01)
        q = (cx + math.cos(a) * (rb * k + .02), cy + math.sin(a) * (rb * k + .02), zb - .01)
        g.beam(p, q, .08, .06, PAINTED)
    # Overhanging cab roof, equipment drum, antenna mast with crossbars, beacons.
    octagon_frustum(g, cx, cy, CAB_TOP, CAB_TOP + .14, 1.75, 1.75, CONCRETE)
    octagon_frustum(g, cx, cy, CAB_TOP + .14, CAB_TOP + .62, .62, .55, FORGED)
    octagon_frustum(g, cx, cy, CAB_TOP + .62, CAB_TOP + .7, .66, .66, IRON)
    pivot = beacon(g, cx + .9, cy - .9, CAB_TOP + .14)
    parts.append((beacon_shutter(*pivot, 'MissionControl.CabBeacon'), 'SPIN_Z', 3))
    bx(g, cx - .04, cy - .04, CAB_TOP + .7, cx + .04, cy + .04, 15.45, IRON)
    for z, w in ((13.0, .45), (13.8, .36), (14.6, .26)):
        bx(g, cx - w, cy - .02, z - .02, cx + w, cy + .02, z + .02, IRON)
        bx(g, cx - .02, cy - w, z + .04, cx + .02, cy + w, z + .08, IRON)
    pivot = beacon(g, cx, cy, 15.45)
    parts.append((beacon_shutter(*pivot, 'MissionControl.TowerBeacon'), 'SPIN_Z', 2))


def observatory(g, parts):
    cx, cy = OBS
    revolve(g, (cx, cy, POD_TOP - BURY), [(OBS_R, 0), (OBS_R, DRUM_TOP - POD_TOP + BURY)], CONCRETE, segments=16)
    band(g, (cx, cy, 0), OBS_R, DRUM_TOP - .06, .16, CONCRETE, segments=16, proud=.06)
    band(g, (cx, cy, 0), OBS_R, POD_TOP + .12, .2, CONCRETE, segments=16, proud=.05)
    # Ribs on the drum.
    for i in range(10):
        a = (i + .5) * 2 * math.pi / 10
        px, py = cx + math.cos(a) * (OBS_R + .02), cy + math.sin(a) * (OBS_R + .02)
        g.beam((px, py, POD_TOP + .22), (px, py, DRUM_TOP - .16), .1, mat=CONCRETE)
    # Link block to the hall, with a small window.
    bx(g, cx + 1.0, 4.4, POD_TOP - BURY, HALL[0] + .05, 6.0, 3.2, CONCRETE)
    bx(g, cx + .95, 4.35, 3.18, HALL[0] + .05, 6.05, 3.3, IRON)
    window(g, (cx + 1.0 + HALL[0]) / 2 + .05, 4.4, 2.3, .6, 'front', 'grand')
    # Rotating dome with slit shutters and the telescope (animated as one).
    zc = DRUM_TOP + .02
    dm = Geometry('MissionControl.ObservatoryDome', (cx, cy, zc))
    R = OBS_R + .06
    revolve(dm, (cx, cy, zc), [(R, 0), (R, .12)], IRON, segments=16, cap_bottom=True, cap_top=False)
    dome(dm, (cx, cy, zc + .12), R, ROOF, segments=16, rings=8)
    az = -math.pi / 2 - .5           # slit faces the front-left at rest
    for k in range(8):
        a = az + (k + .5) * 2 * math.pi / 8
        if abs(math.cos(a - az)) > .9 and math.cos(a - az) > 0:
            continue
        arc_bar(dm, (cx, cy, zc + .12), R - .02, R + .05, .04, a, .12, math.pi / 2 - .02, IRON, steps=8)
    arc_bar(dm, (cx, cy, zc + .12), R - .03, R + .035, .2, az, -.25, math.pi / 2 - .02, IRON, steps=12)
    for s in (-1, 1):
        arc_bar(dm, (cx, cy, zc + .12), R - .02, R + .09, .05, az + s * .19, .32, math.pi / 2 - .02, BRASS, steps=10)
    el = .75
    dvec = Vector((math.sin(el) * math.cos(az), math.sin(el) * math.sin(az), math.cos(el)))
    base = Vector((cx, cy, zc + .25))
    tube(dm, tuple(base - dvec * .3), tuple(base + dvec * (R + .55)), .17, IRON, segments=14)
    for f in (.4, 1.0, 1.6):
        tube(dm, tuple(base + dvec * (f - .04)), tuple(base + dvec * (f + .04)), .21, BRASS, segments=14)
    tube(dm, tuple(base + dvec * (R + .55)), tuple(base + dvec * (R + .6)), .2, IRON, segments=14)
    parts.append((dm, 'CUSTOM_YAW_OSC', (.85, 1)))


def dish(g, parts):
    cx, cy = DISH
    # Concrete pedestal with a riveted service door and stair-free ladder.
    pt = PED_TOP
    bx(g, cx - .85, cy - .85, POD_TOP - BURY, cx + .85, cy + .85, pt, CONCRETE)
    bx(g, cx - .91, cy - .91, pt - .1, cx + .91, cy + .91, pt + .08, CONCRETE)
    for k in range(2):
        z = POD_TOP + .8 + k * .9
        bx(g, cx - .91, cy - .91, z - .05, cx + .91, cy + .91, z + .05, CONCRETE)
    door_x = cx - .3
    bx(g, door_x - .25, cy - .91, POD_TOP + .02, door_x + .25, cy - .84, POD_TOP + .7, FORGED)
    window(g, cx + .4, cy - .85, POD_TOP + 1.3, .5, 'front', 'factory')
    ladder(g, cx + .85, cy, POD_TOP + .02, pt + .08, face='right', cage=True)
    revolve(g, (cx, cy, pt + .06), [(.7, 0), (.7, .16)], IRON, segments=12)
    g.ring((cx, cy, pt + .2), .74, .05, .06, BRASS, 'Z', 12)
    # Turret: yaw bearing, yoke arms and trunnions (animated yaw).
    yaw = .35
    zt = pt + .24
    tur = Geometry('MissionControl.DishTurret', (cx, cy, zt))
    revolve(tur, (cx, cy, zt), [(.62, 0), (.62, .32), (.48, .42)], PAINTED, segments=12)
    for s in (-1, 1):
        x = cx + s * .7
        tur.box((x, cy, (zt + .3 + PIVOT_Z) / 2), (.16, .38, PIVOT_Z - zt - .3 + .22), IRON)
        tur.beam((cx + s * .35, cy, zt + .35), (x, cy, zt + .8), .13, mat=IRON)
        tur.cylinder((x, cy, PIVOT_Z), .18, .22, BRASS, 'X', 12)
    tur.box((cx, cy + .38, zt + .55), (.55, .3, .45), FORGED)
    gauge(tur, cx, cy + .53, zt + .6, 'back', .09)
    parts.append((tur, 'CUSTOM_DISH_YAW', (yaw, 0)))
    # Dish: white parabolic face, painted back ribs, tripod and feed horn.
    tilt = Quaternion((1, 0, 0), math.radians(50))
    def build(t):
        R, f = 1.7, 1.1
        prof = [(r, r * r / (4 * f)) for r in (.28, .45, .7, .95, 1.2, R)]
        hollow_revolve(t, (0, 0, .3), prof, .06, IRON, segments=16, inner_mat=CONCRETE)
        band(t, (0, 0, 0), R, .3 + R * R / (4 * f), .06, BRASS, segments=16, proud=.015)
        revolve(t, (0, 0, .12), [(.34, 0), (.34, .22), (.3, .26)], IRON, segments=16)
        for i in range(8):
            a = i * math.pi / 4
            for r0, r1 in ((.3, .7), (.7, 1.1), (1.1, R - .04)):
                p0 = (math.cos(a) * r0, math.sin(a) * r0, .3 + r0 * r0 / (4 * f) - .07)
                p1 = (math.cos(a) * r1, math.sin(a) * r1, .3 + r1 * r1 / (4 * f) - .07)
                t.beam(p0, p1, .05, mat=PAINTED)
        t.box((0, 0, .08), (1.1, .2, .16), IRON)
        for i in range(3):
            a = math.pi / 2 + i * 2 * math.pi / 3
            rim = (math.cos(a) * (R - .1), math.sin(a) * (R - .1), .3 + (R - .1) ** 2 / (4 * f) + .03)
            t.beam(rim, (0, 0, .3 + f - .05), .035, mat=IRON)
        revolve(t, (0, 0, .3 + f - .1), [(.11, 0), (.11, .08), (.07, .3), (0, .32)], BRASS, segments=10)
    dg = Geometry('MissionControl.Dish', (cx, cy, PIVOT_Z))
    # Local dish axis +Z tipped 50 degrees toward the front (-Y), about the trunnion axis.
    place(dg, build, tilt.inverted(), (cx, cy, PIVOT_Z))
    parts.append((dg, 'CUSTOM_DISH', (yaw, .22)))
    # Cable tray from the pedestal to the hall roof.
    cable_tray(g, (HALL[2] + .14, 6.1), (cx - .93, 6.1), 2.9)


def masts(g, parts):
    pts = []
    for x, y in ((.85, 9.15), (11.15, 9.15)):
        lattice(g, x - .25, y - .25, x + .25, y + .25, POD_TOP - .02, 11.6, bays=8, w=.09, feet=False)
        bx(g, x - .36, y - .36, POD_TOP - BURY, x + .36, y + .36, POD_TOP + .22, CONCRETE)
        bx(g, x - .04, y - .04, 11.6, x + .04, y + .04, 12.1, IRON)
        pts.append((x, y))
    # Wire aerial between the masts, with insulators.
    (ax, ay), (bx_, by) = pts
    g.beam((ax + .05, ay, 11.4), (bx_ - .05, by, 11.4), .022, mat=IRON)
    for x in (2.0, 10.0):
        g.cylinder((x, ay, 11.4), .05, .14, CONCRETE, 'X', 8)
    for x in (4.0, 7.0):
        g.beam((x, ay, 11.38), (x, HALL[3] - .3, HALL_TOP + .5), .018, mat=IRON)
    pivot = beacon(g, ax, ay, 12.1)
    parts.append((beacon_shutter(*pivot, 'MissionControl.MastBeacon'), 'SPIN_Z', 3))
    # Rotating radar bar on the east mast.
    rz = 12.3
    rd = Geometry('MissionControl.Radar', (bx_, by, rz))
    rd.cylinder((bx_, by, rz - .1), .12, .2, PAINTED, 'Z', 12)
    rd.box((bx_, by, rz + .08), (1.3, .08, .16), IRON)
    for k in range(7):
        x = bx_ - .6 + k * .2
        rd.box((x, by - .05, rz + .08), (.05, .04, .26), BRASS)
    rd.box((bx_, by + .08, rz + .08), (.3, .1, .1), FORGED)
    parts.append((rd, 'SPIN_Z', 1))


def build(g, parts):
    podium(g, parts)
    hall(g)
    tower(g, parts)
    observatory(g, parts)
    dish(g, parts)
    masts(g, parts)
