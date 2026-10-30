"""Nuclear Reactor: the endgame Deep Frontier power station.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the yard post lamps.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; outputs/compaction/BRIEF.md): 20x15x22 -> 14x11x11, inside the old
footprint with the same origin, turbine-hall door (x 10.5, face 0.15 behind
the front edge), native entrance and coolant pipe inlet (cell 0,0,0 facing
the front). It stays the largest power landmark, but loses its scaffolding:
the two containment ring galleries and their ladder, the lattice water tower,
the lattice vent stack, the steam-bridge trestle, the coolant pipe-bridge
trestles, the fuel-building crane gantry and the roof casks are gone. One
layer per floor: the turbine hall, fuel store and feed house are a concrete
ground storey with one steel storey above at most, all under flat roofs
(the barrel vault is gone). The domed containment and the hyperboloid towers
are the building's defining silhouette and keep their curves.

Hero: a banded concrete containment tube under a painted steel dome,
flanked by twin hyperboloid cooling towers standing in their own basins.
Roof types: domed containment, open hyperboloid towers; flat roofs in two
finishes: riveted steel plate on the turbine hall, concrete on the feed
house and fuel store; no roof vents (roof-variety pass).

Water supply: a ground-level concrete race along the back carries native
water past two native water wheels and is sluiced into each cooling basin.
The feed house at the front left takes the piped coolant (Timber Pipes inlet
on its front face) and carries the two feed-water tanks on its roof.

Heat, meltdown and cooling: the meltdown acts on the footprint
(docs/meltdown.md); the tower mouths keep their 'towerSteam' emitters and the
coolant inlet keeps its cell and direction (tools/coolant_pipe_ports.json).
"""
import math

from lategame_kit import *
from frontier_architecture import Geometry
from industrial_facades import building_portal
from architectural_windows import window
from native_building_assets import prop
from lategame_roofdeck_parts import parapet_ring
from lategame_sheet_roofs import plate_deck
import lategame_mining_parts as M

IDENT = 'NuclearReactor'
FOOTPRINT = (14, 11)
HEIGHT = 11
FRAME_END = 301
FPS = 24   # native CompactWaterWheel clip rate
HERO = 'Banded containment tube and dome between twin hyperboloid cooling towers'
# Coolant arrives by Timber Pipes: the live blueprint port is
# tools/coolant_pipe_ports.json (cell 0,0,0 facing the front edge); this is
# the socket on the feed house front wall.
PIPE_INLET = {'cell': [0, 0, 0], 'direction': 'Down', 'state': 'OpenIn', 'good': 'ReactorCoolantWater',
              'socket': [.5, .15, .45]}

CORE = (7.0, 6.6)           # containment centre
DRUM_R, TUBE_R = 2.6, 2.15  # concrete drum base and main tube radii
DRUM_TOP, TUBE_TOP = 1.2, 7.4
TOWERS = ((2.0, 7.0), (12.0, 7.0))     # basins on whole tiles 0..4 / 10..14 x 5..9
TOWER_BASE, TOWER_WAIST, TOWER_TOP = 1.65, 1.2, 7.5
SHELL_START = 1.1
BASIN_HALF = 2.0
HALL = (4.0, .15, 14.0, 3.0)        # turbine hall: tiles 4..14 x 0..3
HALL_ROOF = 2.84                    # slab bottom; its top is layer 3
FEED = (0.0, .15, 4.0, 5.0)         # feed house: tiles 0..4 x 0..5
FEED_ROOF = .84                     # one storey: its roof top is layer 1
FUEL = (10.0, 3.0, 14.0, 5.0)       # fuel store behind the hall's east end
FUEL_ROOF = 1.84


# ---------------------------------------------------------------- details

def gauge(g, x, y, z, r=.12, face='front'):
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
    zw = 5.4
    c = (TOWER_BASE ** 2 - TOWER_WAIST ** 2) / (zw - SHELL_START) ** 2
    return math.sqrt(TOWER_WAIST ** 2 + c * (z - zw) ** 2)


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
    revolve(g, (cx, cy, 0), [(DRUM_R + .1, 0), (DRUM_R + .1, .22)], CONCRETE, segments=24)
    revolve(g, (cx, cy, .22), [(DRUM_R, 0), (DRUM_R, DRUM_TOP - .22)], CONCRETE, segments=24)
    revolve(g, (cx, cy, DRUM_TOP - .1), [(DRUM_R + .07, 0), (DRUM_R + .07, .12)], CONCRETE, segments=24)
    for i in range(16):
        a = (i + .5) * 2 * math.pi / 16
        p = (cx + math.cos(a) * (DRUM_R + .12), cy + math.sin(a) * (DRUM_R + .12))
        g.beam((p[0], p[1], .22), (p[0], p[1], DRUM_TOP - .12), .28, mat=CONCRETE)
    revolve(g, (cx, cy, DRUM_TOP + .02), [(TUBE_R, 0), (TUBE_R, TUBE_TOP - DRUM_TOP - .02)], CONCRETE, segments=24)
    for i in range(12):
        a = i * 2 * math.pi / 12
        p = (cx + math.cos(a) * (TUBE_R + .05), cy + math.sin(a) * (TUBE_R + .05))
        g.beam((p[0], p[1], DRUM_TOP + .05), (p[0], p[1], TUBE_TOP - .3), .18, mat=CONCRETE)
    for z in (2.6, 3.9, 5.2, 6.5):
        band(g, (cx, cy, 0), TUBE_R + .09, z, .18, IRON, segments=24, proud=.03)
    revolve(g, (cx, cy, TUBE_TOP - .28), [(TUBE_R + .2, 0), (TUBE_R + .2, .3)], CONCRETE, segments=24)
    revolve(g, (cx, cy, TUBE_TOP + .02), [(TUBE_R + .09, 0), (TUBE_R + .09, .12)], IRON, segments=24)
    dome(g, (cx, cy, TUBE_TOP + .14), TUBE_R + .03, PAINTED, segments=24, rings=4, squash=.55)
    dome_top = TUBE_TOP + .14 + (TUBE_R + .03) * .55
    for i in range(6):
        a = i * 2 * math.pi / 6
        prev = None
        for k in range(5):
            t = k / 4 * math.pi / 2
            rr = (TUBE_R + .06) * math.cos(t)
            pz = TUBE_TOP + .14 + (TUBE_R + .06) * .55 * math.sin(t)
            p = (cx + math.cos(a) * rr, cy + math.sin(a) * rr, pz)
            if prev:
                g.beam(prev, p, .06, mat=IRON)
            prev = p
    revolve(g, (cx, cy, dome_top - .22), [(.65, 0), (.65, .55)], CONCRETE, segments=16)
    for i in range(8):
        a = i * 2 * math.pi / 8
        g.box((cx + math.cos(a) * .67, cy + math.sin(a) * .67, dome_top + .07), (.07, .07, .42), IRON)
    revolve(g, (cx, cy, dome_top + .33), [(.78, 0), (.78, .05), (.16, .4), (0, .44)], ROOF, segments=16)
    pivot = beacon(g, cx, cy, dome_top + .77)
    parts.append((beacon_shutter(*pivot, 'NuclearReactor.BeaconShutter'), 'SPIN_Z', 2))
    # Emblem on the tube above the turbine hall.
    trefoil(g, cx, cy - TUBE_R - .06, 4.55, r=.38)
    # Four primary steam risers up the faces into the cornice.
    for a in (-math.pi * .7, -math.pi * .3, math.pi * .62, math.pi * .38):
        rx, ry = cx + math.cos(a) * (TUBE_R + .36), cy + math.sin(a) * (TUBE_R + .36)
        pipe_run(g, [(rx, ry, DRUM_TOP + .1), (rx, ry, TUBE_TOP - .4)], .17)
        for z in (3.2, 6.0):
            g.beam((cx + math.cos(a) * (TUBE_R + .1), cy + math.sin(a) * (TUBE_R + .1), z), (rx, ry, z), .09, mat=IRON)
    # Reactor coolant pumps on the drum ledge: casing, valve and moving crosshead.
    for k, a in enumerate((-math.pi * .86, -math.pi * .14, math.pi * .2, math.pi * .8)):
        px, py = cx + math.cos(a) * 2.38, cy + math.sin(a) * 2.38
        revolve(g, (px, py, DRUM_TOP + .02), [(.2, 0), (.2, .45), (.14, .5)], PAINTED, segments=12)
        for dx in (-.13, .13):
            g.box((px + dx, py, DRUM_TOP + .82), (.045, .045, .64), IRON)
        g.box((px, py, DRUM_TOP + 1.16), (.36, .1, .07), IRON)
        head = Geometry(f'NuclearReactor.CoolantPump{k}', (px, py, DRUM_TOP + .78))
        head.box((px, py, DRUM_TOP + .78), (.21, .09, .1), BRASS)
        head.box((px, py, DRUM_TOP + .62), (.05, .05, .26), IRON)
        parts.append((head, 'PISTON_Z', .14))


# ---------------------------------------------------------------- cooling towers

def cooling_tower(g, parts, cx, cy, index):
    h = BASIN_HALF
    g.box((cx, cy, .05), (2 * h, 2 * h, .1), CONCRETE)
    for (x, y, sx, sy) in ((cx, cy - h + .11, 2 * h, .22), (cx, cy + h - .11, 2 * h - 1.0 if False else 2 * h, .22),
                           (cx - h + .11, cy, .22, 2 * h - .44), (cx + h - .11, cy, .22, 2 * h - .44)):
        g.box((x, y, .28), (sx, sy, .36), CONCRETE)
    g.box((cx, cy - h + .11, .49), (2 * h + .05, .27, .05), IRON)
    g.liquid_surfaces.append(dict(name=f'CoolingBasin{index}', shape='Rectangle', center=[cx, cy],
                                  bottom=.1, top=.34, scale=[2 * h - .44, 2 * h - .44], flowOnly=False))
    hollow_revolve(g, (cx, cy, .1), [(TOWER_BASE + .2, 0), (TOWER_BASE + .2, .26)], .4, CONCRETE, segments=16)
    legs = 6
    for i in range(legs):
        a = i * 2 * math.pi / legs
        top = (cx + math.cos(a) * (TOWER_BASE - .06), cy + math.sin(a) * (TOWER_BASE - .06), SHELL_START + .02)
        for d in (-1, 1):
            b = a + d * math.pi / legs
            foot = (cx + math.cos(b) * TOWER_BASE, cy + math.sin(b) * TOWER_BASE, .36)
            g.beam(foot, top, .12, mat=CONCRETE)
    zs = [SHELL_START + (TOWER_TOP - SHELL_START) * k / 5 for k in range(6)]
    hollow_revolve(g, (cx, cy, 0), [(tower_radius(z), z) for z in zs], .12, CONCRETE, segments=16,
                   rims=(False, False))
    hollow_revolve(g, (cx, cy, SHELL_START - .08), [(TOWER_BASE + .07, 0), (TOWER_BASE + .07, .1)], .22, CONCRETE,
                   segments=16)
    rt = tower_radius(TOWER_TOP)
    hollow_revolve(g, (cx, cy, TOWER_TOP - .07), [(rt + .09, 0), (rt + .09, .17)], .26, IRON, segments=16)
    emitter(g, 'towerSteam', cx, cy, TOWER_TOP + .1, rt)
    z = TOWER_TOP - .7
    r = tower_radius(z)
    hollow_revolve(g, (cx, cy, z - .05), [(r + .035, 0), (r + .02, .1)], .05, IRON, segments=16, rims=(False, False))
    zf = TOWER_TOP - 1.1
    rf = tower_radius(zf) - .24
    for i in range(4):
        a = i * math.pi / 2 + math.pi / 4
        g.beam((cx + math.cos(a) * (tower_radius(zf) - .09), cy + math.sin(a) * (tower_radius(zf) - .09), zf - .1),
               (cx, cy, zf - .1), .08, mat=IRON)
    g.cylinder((cx, cy, zf - .04), .18, .16, IRON, 'Z', 8)
    parts.append((fan(f'NuclearReactor.TowerFan{index}', cx, cy, zf + .06, rf, blades=6), 'SPIN_Z', 3))


# ---------------------------------------------------------------- water supply

def race(g, parts):
    """Ground-level cooling-water race along the back edge: native water flows
    along X past two native CompactWaterWheels (3x1x3, turning about Y) and is
    sluiced into each cooling basin."""
    y0, y1 = 9.82, 11.0
    x0, x1 = 0.0, 14.0
    floor, wall = .06, .66
    inner0, inner1 = y0 + .08, y1 - .08
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, floor / 2), (x1 - x0, y1 - y0, floor), CONCRETE)
    g.box(((x0 + x1) / 2, y1 - .04, (floor + wall) / 2), (x1 - x0, .08, wall - floor), CONCRETE)
    notches = [(tx - .5, tx + .5) for tx, _ in TOWERS]
    edges = [x0] + [v for n in notches for v in n] + [x1]
    for a, b in zip(edges[::2], edges[1::2]):
        g.box(((a + b) / 2, y0 + .04, (floor + wall) / 2), (b - a, .08, wall - floor), CONCRETE)
        g.box(((a + b) / 2, y0 + .04, wall + .03), (b - a, .14, .06), IRON)
    g.box((x1 - .04, (y0 + y1) / 2, (floor + wall) / 2), (.08, inner1 - inner0, wall - floor), CONCRETE)
    g.box(((x0 + x1) / 2, y1 - .04, wall + .03), (x1 - x0, .14, .06), IRON)
    g.liquid_surfaces.append(dict(name='CoolingRace', shape='Rectangle', center=[(x0 + x1) / 2, (inner0 + inner1) / 2],
                                  bottom=floor, top=.42, scale=[x1 - x0 - .1, inner1 - inner0], flowOnly=True))
    for k, (tx, ty) in enumerate(TOWERS):
        b0 = ty + BASIN_HALF
        g.box((tx, (b0 + y0) / 2, (GROUND_SINK + .1) / 2), (1.0, y0 - b0 + .02, .1 - GROUND_SINK), CONCRETE)
        for sx in (tx - .56, tx + .56):
            g.box((sx, (b0 + y0) / 2, (GROUND_SINK + .66) / 2), (.1, y0 - b0, .66 - GROUND_SINK), CONCRETE)
        g.liquid_surfaces.append(dict(name=f'Sluice{k}', shape='Rectangle', center=[tx, (b0 + y0) / 2],
                                      bottom=.1, top=.38, scale=[1.0, y0 - b0], flowOnly=True))
        portal_frame(g, tx - .5, tx + .5, y0 + .04, wall + .06, 1.7, w=.11)
        gate = Geometry(f'NuclearReactor.SluiceGate{k}', (tx, y0 + .04, .85))
        gate.box((tx, y0 + .04, .8), (.84, .06, .44), FORGED)
        gate.box((tx, y0 + .04, 1.3), (.04, .04, .46), IRON)
        parts.append((gate, 'SLIDE_Z', .26))
        valve_wheel(g, tx, y0 - .08, 1.95, face='front', r=.18)
    # Intake sluice at the left end.
    g.box((x0 + .04, (y0 + y1) / 2, (floor + wall) / 2 + .08), (.08, inner1 - inner0, wall - floor - .16), FORGED)
    for k, x in enumerate((4.6, 8.6)):
        prop(g, f'RaceWheel{k}', 'CompactWaterWheel.IronTeeth', (x, inner0 + .01, floor - .03), 1.0)


def feed_house(g, parts):
    """One-storey concrete feed house on the front left: the piped coolant
    inlet on its front wall, the two feed-water tanks on its roof."""
    x0, y0, x1, y1 = FEED
    plinth(g, x0, y0, x1, y1, FEED_ROOF + .16, coping=False)
    roof = FEED_ROOF + .16
    parapet_ring(g, x0, y0, x1, y1, roof, height=.24, open_sides=('right',))
    for x in (1.5, 2.5):
        window(g, x, y0, .55, .45, 'front', 'factory')
    lamp(g, 3.3, y0, .65, face='front')
    # Feed-water tanks on the roof with a connecting manifold.
    tank(g, 1.05, 2.0, roof, .78, 2.3, mat=PAINTED, bands=3, roof='dome', segments=16)
    tank(g, 2.75, 3.15, roof, .62, 1.8, mat=IRON, bands=3, roof='cone', segments=12)
    pipe_run(g, [(1.83, 2.0, roof + .55), (3.6, 2.0, roof + .55), (3.6, 2.0, 1.75), (HALL[0] + .05, 2.0, 1.75)],
             .1, flanges='ends')
    pipe_run(g, [(2.75, 2.53, roof + .5), (2.75, 2.0, roof + .5)], .08, flanges='ends')
    valve_wheel(g, 3.3, 1.88, roof + .55, face='front', r=.13)
    gauge(g, 1.05, 2.0 - .79, roof + 1.1)
    # Coolant pipe socket: the Timber Pipes inlet face on the front wall.
    sx, sy, sz = PIPE_INLET['socket']
    g.box((sx, sy - .06, sz), (.44, .12, .44), PAINTED)
    g.cylinder((sx, sy - .14, sz), .14, .1, IRON, 'Y', 8)
    g.cylinder((sx, sy - .2, sz), .19, .03, BRASS, 'Y', 8)
    # Exciter flywheel on its own ground plinth behind the turbine hall.
    gx, gy, gz = 9.6, 3.55, .75
    g.box((gx, gy, .23), (.4, .7, .4), CONCRETE)
    g.cylinder((gx + .25, gy, gz), .06, .5, IRON, 'X', 8)
    fly = Geometry('NuclearReactor.ExciterFlywheel', (gx, gy, gz))
    fly.ring((gx, gy, gz), .5, .1, .14, IRON, 'X', 12)
    fly.cylinder((gx, gy, gz), .08, .15, IRON, 'X', 8)
    for i in range(6):
        a = i * math.pi / 3
        fly.beam((gx, gy, gz), (gx, gy + math.cos(a) * .43, gz + math.sin(a) * .43), .04, mat=IRON)
    parts.append((fly, 'SPIN_X', 3))


# ---------------------------------------------------------------- turbine hall

def turbine_hall(g, parts):
    x0, y0, x1, y1 = HALL
    base, top = 1.0, HALL_ROOF
    # One-storey concrete base: a solid core with a proud course, notched for
    # the native one-tile door; the steel storey stands on it.
    M.plinth_course(g, x0 + .05, x1 - .05, y0 + .12, y1 - .05, 0, base, CONCRETE, [10.5])
    building_portal(g, 10.5, y0, 0)
    g.doorways.append({'id': 'TurbineHallDoor', 'position': [10.5, y0, 0], 'outward': [0, -1], 'width': 1.0,
                       'internalConnection': 'BuildingInterior'})
    y0 = y0 + .12
    w0 = base + LAYER_GAP
    bay = (x1 - x0) / 10
    wins = [(x0 + (k + .5) * bay, 1.92) for k in (0, 1, 2, 3, 4, 7, 8, 9)]
    frame_wall(g, 'X', y0 + .05, x0, x1, w0, top, outward=-1, bays=10, infill=FORGED,
               windows=wins, window_style='grand', window_scale=.7)
    frame_wall(g, 'X', y1 - .05, x0, x1, w0, top, outward=1, bays=5, infill=FORGED)
    frame_wall(g, 'Y', x1 - .05, y0 + .1, y1 - .1, w0, top, outward=1, bays=3, infill=FORGED,
               windows=[(1.6, 1.92)], window_style='lancet', window_scale=.7)
    frame_wall(g, 'Y', x0 + .05, y0 + .1, y1 - .1, w0, top, outward=-1, bays=3, infill=FORGED)
    plate_deck(g, x0, y0, x1, y1, top + .16, mat=FORGED)   # riveted steel plate roof
    roof = top + .16
    parapet_ring(g, x0, y0, x1, y1, roof, height=.26, open_sides=('front',))
    # The hall is a solid room (its cells are the building's, not free space).
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, (w0 + top) / 2), (x1 - x0 - .4, y1 - y0 - .3, top - w0), IRON)
    # Emblem board and lamps over the door.
    g.box((10.5, y0 - .03, 1.55), (1.2, .06, .5), CONCRETE)
    for x in (9.6, 11.4):
        lamp(g, x, y0 - .05, .75, face='front')
    # Main steam lines from the containment into the hall's back wall.
    for x in (6.0, 6.7, 7.3, 8.0):
        pipe_run(g, [(x, CORE[1] - TUBE_R + .1, 2.3), (x, y1 + .05, 2.3)], .14)


def fuel_store(g, parts):
    """Shielded fuel store behind the hall's east end: one storey to layer 2
    with a lead cask door and a vent stack."""
    x0, y0, x1, y1 = FUEL
    plinth(g, x0, y0, x1, y1, FUEL_ROOF + .16, coping=False)
    roof = FUEL_ROOF + .16
    parapet_ring(g, x0, y0, x1, y1, roof, height=.24, open_sides=('front',))
    # Shielded cask door on the right face.
    g.box((x1 + .05, 4.0, .85), (.1, 1.1, 1.5), FORGED)
    for y in (3.4, 4.6):
        g.box((x1 + .07, y, .9), (.14, .1, 1.7), IRON)
    g.box((x1 + .08, 4.0, 1.75), (.16, 1.4, .12), IRON)


def coolant_links(g):
    cx, cy = CORE
    for tx, ty in TOWERS:
        s = 1 if tx > cx else -1
        start = cx + s * (TUBE_R + .04)
        end = tx - s * (tower_radius(3.4) - .04)
        for dy, z in ((-.35, 3.2), (.35, 3.75)):
            pipe_run(g, [(start, ty - .9 + dy, z), (end, ty - .9 + dy, z)], .16)


# ---------------------------------------------------------------- assembly

def build(g, parts):
    containment(g, parts)
    for k, (tx, ty) in enumerate(TOWERS):
        cooling_tower(g, parts, tx, ty, k)
    coolant_links(g)
    race(g, parts)
    feed_house(g, parts)
    turbine_hall(g, parts)
    fuel_store(g, parts)
