"""Nuclear Reactor: the endgame Deep Frontier power station.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the yard post lamps.

Hero: a giant banded concrete containment tube under a painted steel dome,
flanked by twin hyperboloid cooling towers standing in their own basins.
Roof types: domed containment, barrel-vaulted turbine hall, flat parapet
fuel building, open hyperboloid towers.

Water supply: an elevated concrete aqueduct along the back carries native
water past two native water wheels, then spills over stepped weirs into each
cooling basin. A riser feeds the elevated water tower. Riveted feed-water
tanks stand at the front left.
"""
import math

from lategame_kit import *
from frontier_architecture import Geometry
from industrial_facades import building_portal
from architectural_windows import window
from native_building_assets import prop

IDENT = 'NuclearReactor'
FOOTPRINT = (20, 15)
HEIGHT = 22
FRAME_END = 301
FPS = 24   # native CompactWaterWheel clip rate
HERO = 'Giant banded containment tube and dome between twin hyperboloid cooling towers'
# Coolant arrives by Timber Pipes. The live blueprint port is in
# tools/coolant_pipe_ports.json (current 3x3x3 footprint); when this study is
# integrated its inlet moves to this intake socket, facing the front edge.
PIPE_INLET = {'cell': [0, 0, 0], 'direction': 'Down', 'state': 'OpenIn', 'good': 'ReactorCoolantWater',
              'socket': [.5, .16, .45]}

CORE = (10.0, 7.4)          # containment centre
DRUM_R, TUBE_R = 3.6, 3.0   # concrete drum base and main tube radii
DRUM_TOP, TUBE_TOP = 2.0, 16.0
TOWERS = ((3.0, 10.0), (17.0, 10.0))   # basins on whole tiles 0..6 / 14..20 x 7..13
TOWER_BASE, TOWER_WAIST, TOWER_TOP = 2.5, 1.75, 13.6
SHELL_START = 1.6
BASIN_HALF = 3.0


# ---------------------------------------------------------------- details

def gauge(g, x, y, z, r=.12, face='front'):
    # Eight sides, no bezel ring: a gauge is a few pixels at game zoom.
    axis = 'Y' if face in ('front', 'back') else 'X'
    n = {'front': -1, 'back': 1, 'left': -1, 'right': 1}[face]
    if axis == 'Y':
        g.cylinder((x, y, z), r, .04, IRON, 'Y', 8)
        g.beam((x, y + n * .03, z), (x + r * .55, y + n * .03, z + r * .45), .012, mat=CYAN)
    else:
        g.cylinder((x, y, z), r, .04, IRON, 'X', 8)
        g.beam((x + n * .03, y, z), (x + n * .03, y + r * .55, z + r * .45), .012, mat=CYAN)


def tower_radius(z):
    """Hyperboloid of one sheet through base, waist and (approximately) top."""
    zw = 9.5
    c = (TOWER_BASE ** 2 - TOWER_WAIST ** 2) / (zw - SHELL_START) ** 2
    return math.sqrt(TOWER_WAIST ** 2 + c * (z - zw) ** 2)


def ring_gallery(g, cx, cy, z, r_in, r_out, *, posts=8):
    """Circular steel walkway at a whole layer, bracketed off a cylinder:
    24 sides, a top rail on 8 posts (the mid rail was sub-pixel); the 24
    knee brackets carry the deck (and its grid occupancy) below."""
    # Solid deck plate: its inner edge is buried in the tube, so no inner
    # wall is needed. 24 sides, like the rail, so the deck still covers its
    # rim cells' roof faces.
    revolve(g, (cx, cy, z - .08), [(r_out, 0), (r_out, .08)], IRON, segments=24)
    g.ring((cx, cy, z + .62), r_out - .035, .045, .055, IRON, 'Z', 24)
    for i in range(posts):
        a = i * 2 * math.pi / posts
        x, y = cx + math.cos(a) * (r_out - .035), cy + math.sin(a) * (r_out - .035)
        g.box((x, y, z + .31), (.05, .05, .62), IRON)
    for i in range(24):
        a = i * 2 * math.pi / 24
        # Knee bracket back to the wall below the deck.
        g.beam((cx + math.cos(a) * (r_in + .02), cy + math.sin(a) * (r_in + .02), z - .75),
               (cx + math.cos(a) * (r_out - .12), cy + math.sin(a) * (r_out - .12), z - .1), .07, mat=IRON)


def trefoil(g, x, y, z, r=.42):
    """Radiation emblem: brass trefoil on a dark steel roundel (front face)."""
    g.cylinder((x, y + .03, z), r, .04, IRON, 'Y', 12)
    g.cylinder((x, y - .01, z), r * .17, .03, BRASS, 'Y', 8)
    for k in range(3):
        a0 = math.pi / 2 + k * 2 * math.pi / 3 - math.pi / 6
        a1 = a0 + math.pi / 3
        pts = []
        for j in range(7):
            a = a0 + (a1 - a0) * j / 6
            pts.append((x + math.cos(a) * r * .86, y - .012, z + math.sin(a) * r * .86))
        for j in range(6, -1, -1):
            a = a0 + (a1 - a0) * j / 6
            pts.append((x + math.cos(a) * r * .28, y - .012, z + math.sin(a) * r * .28))
        oriented_polygon(g, pts, (0, -1, 0), BRASS)


# ---------------------------------------------------------------- containment

def containment(g, parts):
    cx, cy = CORE
    # Stepped concrete drum with a proud coping ring and radial buttresses.
    revolve(g, (cx, cy, 0), [(DRUM_R + .12, 0), (DRUM_R + .12, .25)], CONCRETE, segments=24)
    revolve(g, (cx, cy, .25), [(DRUM_R, 0), (DRUM_R, DRUM_TOP - .25)], CONCRETE, segments=24)
    revolve(g, (cx, cy, DRUM_TOP - .1), [(DRUM_R + .08, 0), (DRUM_R + .08, .12)], CONCRETE, segments=24)
    for i in range(16):
        a = (i + .5) * 2 * math.pi / 16
        p = (cx + math.cos(a) * (DRUM_R + .14), cy + math.sin(a) * (DRUM_R + .14))
        g.beam((p[0], p[1], .25), (p[0], p[1], DRUM_TOP - .12), .34, mat=CONCRETE)
    # The great tube.
    revolve(g, (cx, cy, DRUM_TOP + .02), [(TUBE_R, 0), (TUBE_R, TUBE_TOP - DRUM_TOP - .02)], CONCRETE, segments=24)
    # Vertical pilaster ribs between lead bands.
    for i in range(12):
        a = i * 2 * math.pi / 12
        p = (cx + math.cos(a) * (TUBE_R + .05), cy + math.sin(a) * (TUBE_R + .05))
        g.beam((p[0], p[1], DRUM_TOP + .05), (p[0], p[1], TUBE_TOP - .3), .2, mat=CONCRETE)
    # Lead tension bands, proud of the ribs (their rivet lines were
    # sub-pixel on a six-tile drum).
    # The bands' end discs inside the tube are flat shaft and pipe faces
    # of their cells (outputs/connection-faces), so all eight stay.
    for z in (3.6, 5.4, 7.2, 9.0, 10.8, 12.6, 14.4, 15.4):
        band(g, (cx, cy, 0), TUBE_R + .1, z, .2, IRON, segments=24, proud=.03)
    # Crown cornice, dome and ventilating lantern.
    revolve(g, (cx, cy, TUBE_TOP - .3), [(TUBE_R + .22, 0), (TUBE_R + .22, .32)], CONCRETE, segments=24)
    revolve(g, (cx, cy, TUBE_TOP + .02), [(TUBE_R + .1, 0), (TUBE_R + .1, .14)], IRON, segments=24)
    dome(g, (cx, cy, TUBE_TOP + .16), TUBE_R + .04, PAINTED, segments=24, rings=4, squash=.55)
    dome_top = TUBE_TOP + .16 + (TUBE_R + .04) * .55
    # Dome ribs: proud steel meridians (six, four facets each).
    for i in range(6):
        a = i * 2 * math.pi / 6
        prev = None
        for k in range(5):
            t = k / 4 * math.pi / 2
            rr = (TUBE_R + .07) * math.cos(t)
            pz = TUBE_TOP + .16 + (TUBE_R + .07) * .55 * math.sin(t)
            p = (cx + math.cos(a) * rr, cy + math.sin(a) * rr, pz)
            if prev:
                g.beam(prev, p, .07, mat=IRON)
            prev = p
    revolve(g, (cx, cy, dome_top - .25), [(.85, 0), (.85, .7)], CONCRETE, segments=16)
    for i in range(8):
        a = i * 2 * math.pi / 8
        g.box((cx + math.cos(a) * .87, cy + math.sin(a) * .87, dome_top + .1), (.08, .08, .5), IRON)
    revolve(g, (cx, cy, dome_top + .45), [(1.0, 0), (1.0, .06), (.2, .5), (0, .55)], ROOF, segments=16)
    pivot = beacon(g, cx, cy, dome_top + 1.0)
    parts.append((beacon_shutter(*pivot, 'NuclearReactor.BeaconShutter'), 'SPIN_Z', 2))
    # Galleries.
    ring_gallery(g, cx, cy, 8, TUBE_R + .14, TUBE_R + .85)
    ring_gallery(g, cx, cy, 16, TUBE_R + .24, TUBE_R + .95)
    # Ladder between the galleries on the front-right face.
    a = -math.pi / 3
    lx, ly = cx + math.cos(a) * (TUBE_R + .2), cy + math.sin(a) * (TUBE_R + .2)
    ladder(g, lx, ly, 8, 16, face='front', cage=True)
    # Four primary steam risers up the front faces into the cornice.
    for a in (-math.pi * .62, -math.pi * .38, math.pi * .62, math.pi * .38):
        rx, ry = cx + math.cos(a) * (TUBE_R + .42), cy + math.sin(a) * (TUBE_R + .42)
        pipe_run(g, [(rx, ry, DRUM_TOP + .1), (rx, ry, TUBE_TOP - .45)], .2)
        for z in (4.5, 13.5):
            g.beam((cx + math.cos(a) * (TUBE_R + .12), cy + math.sin(a) * (TUBE_R + .12), z),
                   (rx, ry, z), .1, mat=IRON)
    # Reactor coolant pumps on the drum ledge: casing, valve and moving crosshead.
    for k, a in enumerate((-math.pi * .78, -math.pi * .22, math.pi * .3, math.pi * .7)):
        px, py = cx + math.cos(a) * 3.32, cy + math.sin(a) * 3.32
        revolve(g, (px, py, DRUM_TOP + .02), [(.26, 0), (.26, .55), (.18, .6)], PAINTED, segments=12)
        for dx, dy in ((-.16, 0), (.16, 0)):
            g.box((px + dx, py + dy, DRUM_TOP + 1.0), (.05, .05, .8), IRON)
        g.box((px, py, DRUM_TOP + 1.42), (.44, .12, .08), IRON)
        head = Geometry(f'NuclearReactor.CoolantPump{k}', (px, py, DRUM_TOP + .95))
        head.box((px, py, DRUM_TOP + .95), (.26, .1, .12), BRASS)
        head.box((px, py, DRUM_TOP + .77), (.06, .06, .3), IRON)
        parts.append((head, 'PISTON_Z', .18))


# ---------------------------------------------------------------- cooling towers

def cooling_tower(g, parts, cx, cy, index, inlet=None):
    # Square cooling basin with native water; `inlet` notches the front wall.
    h = BASIN_HALF
    g.box((cx, cy, .05), (2 * h, 2 * h, .1), CONCRETE)
    front = [(cx - h, cx + h)] if inlet is None else [(cx - h, inlet[0]), (inlet[1], cx + h)]
    for a, b in front:
        if b - a > .01:
            g.box(((a + b) / 2, cy - h + .125, .3), (b - a, .25, .4), CONCRETE)
            g.box(((a + b) / 2, cy - h + .125, .53), (b - a, .31, .06), IRON)
    for (x, y, sx, sy) in ((cx, cy + h - .125, 2 * h, .25),
                           (cx - h + .125, cy, .25, 2 * h - .5), (cx + h - .125, cy, .25, 2 * h - .5)):
        g.box((x, y, .3), (sx, sy, .4), CONCRETE)
    g.box((cx, cy + h - .125, .53), (2 * h + .06, .31, .06), IRON)
    g.liquid_surfaces.append(dict(name=f'CoolingBasin{index}', shape='Rectangle', center=[cx, cy],
                                  bottom=.1, top=.38, scale=[2 * h - .5, 2 * h - .5], flowOnly=False))
    # Ring footing and V legs carrying the shell above an open air intake.
    # Tower parts use 16 sides (22.5 degree facets, smooth-shaded).
    hollow_revolve(g, (cx, cy, .1), [(TOWER_BASE + .25, 0), (TOWER_BASE + .25, .3)], .5, CONCRETE, segments=16)
    legs = 6
    for i in range(legs):
        a = i * 2 * math.pi / legs
        top = (cx + math.cos(a) * (TOWER_BASE - .07), cy + math.sin(a) * (TOWER_BASE - .07), SHELL_START + .02)
        for d in (-1, 1):
            b = a + d * math.pi / legs
            foot = (cx + math.cos(b) * TOWER_BASE, cy + math.sin(b) * TOWER_BASE, .4)
            g.beam(foot, top, .15, mat=CONCRETE)
    # The shell with real thickness, top cornice and stiffening bands.
    zs = [SHELL_START + (TOWER_TOP - SHELL_START) * k / 5 for k in range(6)]
    # Its rims sit inside the base ring and under the cornice.
    hollow_revolve(g, (cx, cy, 0), [(tower_radius(z), z) for z in zs], .14, CONCRETE, segments=16,
                   rims=(False, False))
    hollow_revolve(g, (cx, cy, SHELL_START - .1), [(TOWER_BASE + .08, 0), (TOWER_BASE + .08, .12)], .26, CONCRETE, segments=16)
    rt = tower_radius(TOWER_TOP)
    hollow_revolve(g, (cx, cy, TOWER_TOP - .08), [(rt + .1, 0), (rt + .1, .2)], .3, IRON, segments=16)
    # Vanilla steam plume from the mouth (top of the cornice) while generating.
    emitter(g, 'towerSteam', cx, cy, TOWER_TOP + .12, rt)
    for z in (TOWER_TOP - .9,):
        r = tower_radius(z)
        # Underside never seen; the top tucks under the flaring shell.
        hollow_revolve(g, (cx, cy, z - .06), [(r + .04, 0), (r + .02, .12)], .06, IRON, segments=16,
                       rims=(False, False))
    # Mechanical draft fan in the throat, visible from above.
    zf = TOWER_TOP - 1.4
    rf = tower_radius(zf) - .28
    for i in range(4):
        a = i * math.pi / 2 + math.pi / 4
        g.beam((cx + math.cos(a) * (tower_radius(zf) - .1), cy + math.sin(a) * (tower_radius(zf) - .1), zf - .12),
               (cx, cy, zf - .12), .1, mat=IRON)
    g.cylinder((cx, cy, zf - .05), .22, .2, IRON, 'Z', 8)
    parts.append((fan(f'NuclearReactor.TowerFan{index}', cx, cy, zf + .08, rf, blades=6), 'SPIN_Z', 3))
    # Service ladder and lamp at the intake.
    side = 1 if cx < CORE[0] else -1
    lamp(g, cx - side * (TOWER_BASE + .1), cy - 1.4, 1.2, face='left' if side > 0 else 'right')


# ---------------------------------------------------------------- water supply

def aqueduct(g, parts):
    """Ground-level cooling-water race along the back edge.

    Native water flows along X past two native CompactWaterWheels (3x1x3,
    turning about Y), and is sluiced into each cooling basin.
    """
    y0, y1 = 13.8, 14.98   # 1.18 deep: a clear one-tile race for the native wheels
    x0, x1 = 0.0, 20.0
    floor, wall = .06, .72
    inner0, inner1 = y0 + .08, y1 - .08
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, floor / 2), (x1 - x0, y1 - y0, floor), CONCRETE)
    # Back wall continuous; front wall notched at each basin sluice.
    g.box(((x0 + x1) / 2, y1 - .04, (floor + wall) / 2), (x1 - x0, .08, wall - floor), CONCRETE)
    notches = [(tx - .5, tx + .5) for tx, _ in TOWERS]
    edges = [x0] + [v for n in notches for v in n] + [x1]
    for a, b in zip(edges[::2], edges[1::2]):
        g.box(((a + b) / 2, y0 + .04, (floor + wall) / 2), (b - a, .08, wall - floor), CONCRETE)
    for x in (x1 - .04,):
        g.box((x, (y0 + y1) / 2, (floor + wall) / 2), (.08, inner1 - inner0, wall - floor), CONCRETE)
    for a, b in zip(edges[::2], edges[1::2]):
        g.box(((a + b) / 2, y0 + .04, wall + .03), (b - a, .14, .06), IRON)
    g.box(((x0 + x1) / 2, y1 - .04, wall + .03), (x1 - x0, .14, .06), IRON)
    g.liquid_surfaces.append(dict(name='CoolingRace', shape='Rectangle', center=[(x0 + x1) / 2, (inner0 + inner1) / 2],
                                  bottom=floor, top=.44, scale=[x1 - x0 - .1, inner1 - inner0], flowOnly=True))
    # Sluices from the race into each basin, with lifting gates.
    for k, (tx, ty) in enumerate(TOWERS):
        g.box((tx, (ty + BASIN_HALF - .25 + y0) / 2, (GROUND_SINK + .1) / 2),
              (1.0, y0 - (ty + BASIN_HALF - .25) + .02, .1 - GROUND_SINK), CONCRETE)
        for sx in (tx - .56, tx + .56):   # faces clear of the race wall ends at tx -/+ .5
            g.box((sx, 13.6, (GROUND_SINK + .8) / 2), (.1, .5, .8 - GROUND_SINK), CONCRETE)
        g.liquid_surfaces.append(dict(name=f'Sluice{k}', shape='Rectangle', center=[tx, 13.6],
                                      bottom=.1, top=.41, scale=[1.0, .5], flowOnly=True))
        portal_frame(g, tx - .5, tx + .5, 13.84, wall + .06, 2.2, w=.12)
        gate = Geometry(f'NuclearReactor.SluiceGate{k}', (tx, 13.84, .95))
        gate.box((tx, 13.84, .95), (.9, .06, .5), FORGED)
        gate.box((tx, 13.84, 1.6), (.04, .04, .8), IRON)
        parts.append((gate, 'SLIDE_Z', .3))
        valve_wheel(g, tx, 13.72, 2.5, face='front', r=.22)
    # Intake sluice at the left end.
    g.box((x0 + .04, (y0 + y1) / 2, (floor + wall) / 2 + .1), (.08, inner1 - inner0, wall - floor - .2), FORGED)
    for y in (inner0 + .1, inner1 - .1):
        g.box((x0 + .04, y, 1.3), (.12, .12, 2.5), IRON)
    g.box((x0 + .04, (y0 + y1) / 2, 2.6), (.16, y1 - y0, .14), IRON)
    valve_wheel(g, x0 + .2, (y0 + y1) / 2, 2.15, face='left', r=.3)
    # Native water wheels turning in the race.
    for k, x in enumerate((5.6, 12.2)):
        prop(g, f'RaceWheel{k}', 'CompactWaterWheel.IronTeeth', (x, inner0 + .01, floor - .03), 1.0)


def water_tower(g, parts):
    x, y = 10.0, 13.05
    lattice_tower(g, x - .7, y - .55, x + .7, y + .55, 0, 8.0, bays=2, w=.12)
    g.box((x, y, 8.05), (1.7, 1.4, .1), IRON)
    top = tank(g, x, y, 8.1, .95, 2.0, mat=PAINTED, bands=3, roof='cone')
    # Riser from the aqueduct pump to the tank.
    pipe_run(g, [(x + .85, 13.95, .5), (x + .85, y + .3, .5), (x + .85, y + .3, 8.6), (x + .5, y + .3, 8.6)], .1,
             flanges='ends')
    ladder(g, x - .2, y - .6, 0, 8.0, face='front')


def feed_tanks(g):
    # Two riveted feed-water tanks with dome roofs and a connecting manifold.
    ax, ay, bx, by = 3.05, 2.3, 3.05, 5.75
    tank(g, ax, ay, 0, 1.5, 4.4, mat=PAINTED, bands=4, roof='dome', segments=16)
    tank(g, bx, by, 0, 1.1, 3.2, mat=IRON, bands=3, roof='cone', segments=12)
    ladder(g, ax, ay - 1.55, 0, 4.6, face='front')
    steel_rail(g, (ax - .9, ay - 1.2), (ax + .9, ay - 1.2), 4.85)
    pipe_run(g, [(4.6, ay, .7), (HALL[0], ay, .7)], .14)
    pipe_run(g, [(bx + 1.1, by, .55), (4.85, by, .55), (4.85, ay + 1.0, .55)], .1, flanges='ends')
    pipe_run(g, [(1.05, 4.2, .6), (2.2, 4.2, .6), (2.2, 4.2, 1.4), (2.6, 3.6, 1.4)], .09, flanges='ends')
    valve_wheel(g, 5.2, ay - .2, 1.05)
    gauge(g, ax, ay - 1.55, 1.5)


def intake_canal(g, parts):
    """Open concrete intake channel from the front edge into the left
    cooling basin, with a sluice gate and a native water wheel."""
    x0, x1, y0, y1 = 0.0, 1.0, .15, TOWERS[0][1] - BASIN_HALF   # canal on tile column 0
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, .04), (x1 - x0, y1 - y0, .08), CONCRETE)
    for x in (x0 + .07, x1 - .07):
        g.box((x, (y0 + y1) / 2, .38), (.14, y1 - y0, .6), CONCRETE)
        g.box((x, (y0 + y1) / 2, .71), (.2, y1 - y0, .06), IRON)
    # The channel water runs on through the basin wall notch.
    g.liquid_surfaces.append(dict(name='IntakeCanal', shape='Rectangle', center=[(x0 + x1) / 2, (y0 + y1 + .25) / 2],
                                  bottom=.08, top=.42, scale=[x1 - x0 - .28, y1 + .25 - y0], flowOnly=True))
    portal_frame(g, x0 + .07, x1 - .07, y0 + .35, .74, 2.6, w=.14)
    g.box(((x0 + x1) / 2, y0 + .35, 1.05), (x1 - x0 - .3, .07, .5), FORGED)
    valve_wheel(g, (x0 + x1) / 2, y0 + .22, 2.85, face='front', r=.28)
    # Coolant pipe socket: the Timber Pipes inlet face at the canal mouth.
    sx, sy, sz = PIPE_INLET['socket']
    g.box((sx, sy + .12, sz), (.5, .2, .5), PAINTED)
    g.cylinder((sx, sy - .02, sz), .16, .12, IRON, 'Y', 8)
    g.cylinder((sx, sy - .085, sz), .21, .04, BRASS, 'Y', 8)
    bolt_row(g, (sx - .17, sy - .11, sz + .14), (sx + .17, sy - .11, sz + .14), 3, r=.016)



# ---------------------------------------------------------------- turbine hall

# Tiles 6..15 x 0..3; door face .15 off the front edge. The east face stops
# .05 short of x = 15 so the plinth foot never overlaps the fuel building's.
HALL = (6.0, .15, 14.95, 3.0)


def turbine_hall(g, parts):
    x0, y0, x1, y1 = HALL
    base, top, rise = 1.8, 5.2, 1.35
    plinth(g, x0, y0, x1, y1, base, door=(10.5, 1.0, 1.0))
    building_portal(g, 10.5, y0 - .12, 0)
    g.doorways.append({'id': 'TurbineHallDoor', 'position': [10.5, y0, 0], 'outward': [0, -1], 'width': 1.0,
                       'internalConnection': 'BuildingInterior'})
    w0 = base + LAYER_GAP
    bay = (x1 - x0) / 10
    wins = [(x0 + (k + .5) * bay, 3.45) for k in (0, 1, 2, 3, 6, 7, 8)]
    frame_wall(g, 'X', y0 + .05, x0, x1, w0, top, outward=-1, bays=10, infill=FORGED,
               windows=wins, window_style='grand', window_scale=1.15)
    frame_wall(g, 'X', y1 - .05, x0, x1, w0, top, outward=1, bays=5, infill=FORGED)
    frame_wall(g, 'Y', x0 + .05, y0 + .1, y1 - .1, w0, top, outward=-1, bays=3, infill=FORGED,
               windows=[(1.9, 3.45)], window_style='lancet')
    frame_wall(g, 'Y', x1 - .05, y0 + .1, y1 - .1, w0, top, outward=1, bays=3, infill=FORGED,
               windows=[(1.9, 3.45)], window_style='lancet')
    # Frieze closing the wall top under the vault.
    for y in (y0 + .05, y1 - .05):
        g.box(((x0 + x1) / 2, y, top + .12), (x1 - x0 - .2, .14, .24), FORGED)
    barrel_roof(g, x0, y0, x1, y1, top + .02, rise, axis='X', segments=8, ribs=2)
    half = (y1 - y0) / 2 + .12
    for x, s in ((x0 - .02, -1), (x1 + .02, 1)):
        arch_infill(g, 'X', x, (y0 + y1) / 2, half - .08, top + .02, rise - .08, s, PLANK)
    # Emblem and lettering band over the door.
    g.box((10.5, y0 - .14, 4.55), (2.4, .06, .95), CONCRETE)
    trefoil(g, 10.5, y0 - .2, 4.55)
    for x in (8.2, 12.8):
        lamp(g, x, y0 - .14, 2.6)
    # Roof ventilators along the crown.
    for k, x in enumerate((6.8, 10.0, 13.2)):
        z = top + rise + .02
        revolve(g, (x, (y0 + y1) / 2, z - .1), [(.42, 0), (.42, .35)], IRON, segments=8)
        g.ring((x, (y0 + y1) / 2, z + .3), .45, .05, .1, BRASS, 'Z', 8)
        parts.append((fan(f'NuclearReactor.HallVent{k}', x, (y0 + y1) / 2, z + .32, .36, blades=5), 'SPIN_Z', 4))
    # Main steam lines from the containment into the hall's back wall.
    for x in (8.4, 9.4, 10.6, 11.6):
        pipe_run(g, [(x, CORE[1] - TUBE_R + .1, 4.4), (x, y1 + .1, 4.4)], .18)
    # Exposed generator exciter at the west end.
    gx, gy, gz = x0 - .45, 1.9, 1.05
    g.box((gx, gy, .3), (.5, 1.1, .6), CONCRETE)
    g.cylinder((gx + .3125, gy, gz), .1, .425, IRON, 'X', 8)   # shaft end buried in the flywheel hub
    fly = Geometry('NuclearReactor.ExciterFlywheel', (gx, gy, gz))
    # Heavy rim, hub and six spokes (Geometry.wheel's double 24-sided rim
    # and eight spokes were 540 triangles inside this rim).
    fly.ring((gx, gy, gz), .66, .12, .16, IRON, 'X', 12)
    fly.cylinder((gx, gy, gz), .09, .17, IRON, 'X', 8)
    for i in range(6):
        a = i * math.pi / 3
        fly.beam((gx, gy, gz), (gx, gy + math.cos(a) * .58, gz + math.sin(a) * .58), .045, mat=IRON)
    parts.append((fly, 'SPIN_X', 3))
    # Cable trays from the hall to the switch gear on the fuel building.
    cable_tray(g, (x1 - .3, y0 + .6), (FUEL[0] + .02, y0 + .6), top - .4)


# ---------------------------------------------------------------- fuel building

# Tiles 15..20 x 0..7; door face .15 off the front edge; the back face
# stops .05 short of the cooling basin wall on y = 7 (feet never overlap).
FUEL = (15.0, .15, 20.0, 6.95)


def fuel_building(g, parts):
    x0, y0, x1, y1 = FUEL
    base, top = 2.0, 4.8
    plinth(g, x0, y0, x1, y1, base, door=(17.5, 1.0, 1.0))
    building_portal(g, 17.5, y0 - .12, 0)
    g.doorways.append({'id': 'FuelDoor', 'position': [17.5, y0, 0], 'outward': [0, -1], 'width': 1.0,
                       'internalConnection': 'BuildingInterior'})
    w0 = base + LAYER_GAP
    # Lead-clad upper storey: forged sheet between heavy steel posts.
    # Front and back runs start clear of the turbine hall's corner post (the
    # two buildings now share the x = 15 tile edge).
    frame_wall(g, 'X', y0 + .05, x0 + .16, x1, w0, top, outward=-1, bays=4, infill=FORGED,
               windows=[(16.0, 3.4), (19.0, 3.4)], window_style='factory', window_scale=.95)
    frame_wall(g, 'X', y1 - .05, x0 + .16, x1, w0, top, outward=1, bays=2, infill=FORGED)
    frame_wall(g, 'Y', x0 + .05, y0 + .1, y1 - .1, w0, top, outward=-1, bays=5, infill=FORGED)
    frame_wall(g, 'Y', x1 - .05, y0 + .1, y1 - .1, w0, top, outward=1, bays=5, infill=FORGED,
               windows=[(2.0, 3.4), (4.4, 3.4)], window_style='factory', window_scale=.95)
    # Shielded cask door: a heavy lead slab on rails, proud of the plinth.
    g.box((16.15, y0 - .07, .95), (1.3, .1, 1.7), FORGED)
    for x in (15.45, 16.85):
        g.box((x, y0 - .09, 1.0), (.12, .16, 1.95), IRON)
    g.box((16.15, y0 - .1, 2.0), (1.6, .2, .14), IRON)
    bolt_row(g, (15.6, y0 - .125, 1.75), (16.7, y0 - .125, 1.75), 5)
    bolt_row(g, (15.6, y0 - .125, .2), (16.7, y0 - .125, .2), 5)
    trefoil(g, 18.7, y0 - .1, 1.3, .3)
    flat_roof(g, x0, y0, x1, y1, top, parapet_height=.4)
    roof = top + .16
    # Crane runway and moving gantry with its hook block.
    for y in (y0 + .55, y1 - .55):
        g.box(((x0 + x1) / 2, y, roof + .52), (x1 - x0 - .3, .14, .12), IRON)
        for x in (x0 + .35, (x0 + x1) / 2, x1 - .35):
            g.box((x, y, roof + .23), (.14, .14, .46), IRON)
    gantry = Geometry('NuclearReactor.FuelCrane', (x0 + 1.0, (y0 + y1) / 2, roof + 1.6))
    gx = x0 + 1.0
    for y in (y0 + .55, y1 - .55):
        gantry.box((gx, y, roof + 1.1), (.16, .16, .9), PAINTED)
        gantry.box((gx, y, roof + .66), (.4, .24, .1), IRON)
    gantry.box((gx, (y0 + y1) / 2, roof + 1.62), (.3, y1 - y0 - .9, .16), PAINTED)
    gantry.box((gx, (y0 + y1) / 2, roof + 1.45), (.36, .42, .2), IRON)
    gantry.box((gx, (y0 + y1) / 2, roof + 1.05), (.03, .03, .6), IRON)
    gantry.box((gx, (y0 + y1) / 2, roof + .72), (.24, .18, .12), BRASS)
    parts.append((gantry, 'SLIDE_X', 2.2))
    # Lead fuel casks on the roof deck under the crane.
    for i, (x, y) in enumerate(((16.5, 2.0), (18.3, 2.0), (16.5, 4.8), (18.3, 4.8))):
        # Plain lead casks with brass lids (their bands were a pixel wide).
        revolve(g, (x, y, roof), [(.3, 0), (.3, .72), (.22, .78)], IRON, segments=12)
        g.cylinder((x, y, roof + .8), .14, .05, BRASS, 'Z', 8)
    # Ventilation stack with an intake cowl.
    stack(g, 19.0, 5.8, roof, 3.2, emits=None, r=.2, bands=2)   # ventilation: no plume


# ---------------------------------------------------------------- vent stack & coolant links

def vent_stack(g):
    x, y = 12.6, 12.7
    lattice_tower(g, x - .55, y - .55, x + .55, y + .55, 0, 12.5, bays=4, w=.12)
    stack(g, x, y, 0, 18.2, emits=None, r=.34, taper=.75, bands=4)   # ventilation: no plume
    for z in (6.0, 12.5):
        steel_rail(g, (x - .6, y - .6), (x + .6, y - .6), z + .05)
        g.box((x, y, z + .01), (1.25, 1.25, .08), IRON)
    pipe_run(g, [(CORE[0] + 1.9, CORE[1] + 2.1, 11.0), (x - .2, y - .4, 11.0), (x - .2, y - .2, 11.0)], .16,
             flanges='ends')


def steam_bridge(g):
    """High steam main from the containment to the fuel building roof."""
    cx, cy = CORE
    a = -math.pi / 7
    sx, sy = cx + math.cos(a) * (TUBE_R + .05), cy + math.sin(a) * (TUBE_R + .05)
    lattice_tower(g, 14.3, 4.9, 14.7, 5.5, 0, 8.6, bays=3, w=.1)
    g.box((14.5, 5.2, 8.66), (.6, .8, .12), IRON)
    for dy, r in ((-.3, .2), (.32, .13)):
        pipe_run(g, [(sx, sy + dy, 9.0), (17.6, sy + dy, 9.0), (17.6, sy + dy, 5.6)], r)
    revolve(g, (17.6, 5.2, 5.12), [(.36, 0), (.36, .5)], PAINTED, segments=12)
    valve_wheel(g, 17.6, 4.78, 5.55)


def coolant_links(g):
    cx, cy = CORE
    for tx, ty in TOWERS:
        s = 1 if tx > cx else -1
        start = cx + s * (TUBE_R + .05)
        end = tx - s * (tower_radius(5.6) - .05)
        for dy, z in ((-.45, 5.6), (.45, 6.4)):
            pipe_run(g, [(start, ty - .8 + dy, z), (end, ty - .8 + dy, z)], .22)
        # Pipe bridge trestle standing just outside the basin wall.
        bx = tx - s * (BASIN_HALF + .25)
        for dy in (-.75, .75):
            g.box((bx, ty - .8 + dy, 2.9), (.18, .18, 5.6), IRON)
        g.box((bx, ty - .8, 5.3), (.3, 1.7, .16), IRON)
        g.box((bx, ty - .8, 6.1), (.3, 1.7, .16), IRON)


# ---------------------------------------------------------------- assembly

def build(g, parts):
    containment(g, parts)
    for k, (tx, ty) in enumerate(TOWERS):
        cooling_tower(g, parts, tx, ty, k, inlet=(0.0, 1.0) if k == 0 else None)
    coolant_links(g)
    intake_canal(g, parts)
    steam_bridge(g)
    aqueduct(g, parts)
    water_tower(g, parts)
    feed_tanks(g)
    turbine_hall(g, parts)
    fuel_building(g, parts)
    vent_stack(g)
