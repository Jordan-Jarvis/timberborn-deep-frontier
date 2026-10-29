"""Radioactive Waste Refinery: late-game study (Iron Teeth, Deep Frontier).

HERO: a goliath gantry crane, two 10-layer A-frame steel legs on rail bogies
carrying a riveted twin-girder bridge, which lifts a finned spent-fuel cask
out of the cooling pond and lowers it into the roof hatch of the hot cells.
ROOF: flat cast roofs with mitred parapets on the stepped hot-cell monolith,
and a teal plank barrel vault on the vitrification hall.

Supporting masses: the hot-cell monolith with five shielded windows and
master-slave manipulator ports under a plank lean-to, the cooling pond in
native water with submerged racks and a circulating pump, the vitrification
furnace with its glowing pour mouth, canister turntable and stack, two
dissolver towers with an access lattice, and a vitrified-canister rack.

Animated: crane trolley (CUSTOM_TROLLEY), cask on its yoke (CUSTOM_CASK) and
hoist cables (CUSTOM_CABLE) following one shared lift-travel-lower cycle,
pond pump flywheel (SPIN_X), furnace glow (FLAME), canister turntable
(SPIN_Z), dissolver agitator drives (SPIN_Z), two crane beacons (SPIN_Z).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import (CONCRETE, ORANGE, FORGED, PAINTED, CYAN, GLOW, plinth, frame_wall, revolve, band,
                          dome, tank, stack, hollow_revolve, catwalk, steel_rail, ladder, lamp, beacon,
                          beacon_shutter, bolt_row, lattice_tower)
from lategame_nuclear_parts import (bx, Facer, trefoil, gauge, riveted_panel, straight_pipe, pipe_path, valve,
                                    plank_slope, slope_quad, manipulator_port, frustum, obox, plank_barrel,
                                    ring_parapet, cask, board_wall)
from industrial_facades import building_portal
from architectural_windows import window

IDENT = 'RadioactiveWasteRefinery'
FOOTPRINT = (12, 11)
HEIGHT = 12
HERO = ('Goliath gantry crane: twin A-frame steel legs on rail bogies carry a riveted 10-layer bridge '
        'that lifts a finned spent-fuel cask from the cooling pond into the hot-cell roof hatch.')
FRAME_END = 121

# Hot-cell monolith
# Tiles 1..7 x 1..7 (world); front (door) face .15 off the tile edge after DY.
# HX0 sits .04 inside x = 1: the kit plinth needs its face clear of the
# door notch edge at x 1.0 (it meets the crane rail beam there).
HX0, HY0, HX1, HY1 = .96, 2.15, 7.0, 8.0
LOW_TOP = 4.5
UX0, UY0, UX1, UY1 = 1.6, 3.0, 6.4, 7.4
UP_TOP = 6.3
# Crane
BY = 4.1                    # bridge centreline (trolley travel line)
LX0, LX1 = .5, 11.5         # leg planes, centred on one-tile rail beams
GIRDER_BOT, GIRDER_TOP = 9.2, 10.0
RAIL_TOP = GIRDER_TOP + .05
POND_X, CELL_X = 9.45, 3.8  # cask pick and set-down stations
CASK_H = 1.3
# Cask cycle: (loop fraction, trolley x, cask bottom z)
CYCLE = [(0, POND_X, .35), (.2, POND_X, 7.0), (.38, CELL_X, 7.0), (.48, CELL_X, 6.62), (.56, CELL_X, 6.62),
         (.66, CELL_X, 7.0), (.84, POND_X, 7.0), (1.0, POND_X, .35)]
POND = (8.0, 2.0, 11.0, 6.0)     # world tiles 8..11 x 1..5
VH = (8.0, 8.0, 11.0, 12.0)     # vitrification hall, world tiles 8..11 x 7..11


def hot_cells(g, parts):
    plinth(g, HX0, HY0, HX1, HY1, LOW_TOP, door=(1.5, 1.0, 1.0))
    building_portal(g, 1.5, HY0 - .12, 0)
    g.doorways.append({'id': 'Main', 'position': [1.5, HY0, 0], 'outward': [0, -1]})
    lamp(g, 1.5, HY0, 1.3, face='front')
    # Shielded windows: deep cast surrounds, native factory glazing, and a
    # pair of master-slave manipulators above each.
    for x in (2.4, 3.4, 4.4, 5.4, 6.4):
        window(g, x, HY0, 1.7, .86, 'front', 'factory')
        f = Facer(x, HY0, 0, 'front')
        f.box(g, -.36, 1.7, .11, .1, 1.0, .22, CONCRETE)
        f.box(g, .36, 1.7, .11, .1, 1.0, .22, CONCRETE)
        f.box(g, 0, 1.18, .12, .86, .1, .24, CONCRETE)
        f.box(g, 0, 2.24, .115, .86, .1, .23, CONCRETE)
        for u in (-.22, .22):
            manipulator_port(g, x + u, HY0, 2.52, face='front', reach=.5)
    # Operator gallery lean-to in native planks on steel brackets.
    plank_slope(g, slope_quad(HY0 - 1.05, 3.55, HY0 + .1, 4.0, .075), 1.95, HX1 + .12, axis='X')
    bx(g, 1.95, HY0 - 1.08, 3.45, HX1 + .12, HY0 - 1.02, 3.6, WOOD)
    for x in (2.0, 2.9, 3.9, 4.9, 5.9, 6.8):
        g.beam((x, HY0, 2.95), (x, HY0 - .95, 3.55), .05, mat=IRON)
        g.beam((x, HY0, 3.55), (x, HY0 - .95, 3.57), .07, mat=IRON)
    # Upper shield storey: setback cast block clad in lead sheet.
    bx(g, UX0, UY0, LOW_TOP, UX1, UY1, UP_TOP, CONCRETE)
    bx(g, UX0 - .06, UY0 - .06, UP_TOP - .1, UX1 + .06, UY1 + .06, UP_TOP + .02, CONCRETE)
    front = Facer(UX0, UY0, 0, 'front')
    for u0, u1 in ((.15, 1.35), (1.55, 2.6), (3.6, 4.65)):
        riveted_panel(g, front, u0, u1, LOW_TOP + .35, UP_TOP - .35, 0, .05, FORGED)
    trefoil(g, UX0 + 3.1, UY0, LOW_TOP + .95, face='front', r=.32)
    side = Facer(UX1, UY0, 0, 'right')
    for u0, u1 in ((.2, 1.4), (1.6, 2.8), (3.0, 4.2)):
        riveted_panel(g, side, u0, u1, LOW_TOP + .35, UP_TOP - .35, 0, .05, FORGED)
    ring_parapet(g, UX0 - .06, UY0 - .06, UX1 + .06, UY1 + .06, UP_TOP + .02, .38)
    # Lower roof terrace parapet around the setback.
    ring_parapet(g, HX0 - .04, HY0 - .04, HX1 + .04, HY1 + .04, LOW_TOP + .012, .3)
    # Roof hatch collar at the cask set-down station.
    hollow_revolve(g, (CELL_X, BY, UP_TOP + .02), [(.78, 0), (.78, .5)], .13, IRON, segments=16)
    g.ring((CELL_X, BY, UP_TOP + .42), .8, .04, .06, BRASS, 'Z', 16)
    revolve(g, (CELL_X, BY, UP_TOP + .032), [(.66, 0), (.66, .02)], IRON, segments=16)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        obox(g, (CELL_X + math.cos(a) * .9, BY + math.sin(a) * .9, UP_TOP + .2), a, .26, .1, .36, IRON)
    # Roof filter house and vent stacks, clear of the cask path.
    bx(g, 1.9, 5.6, UP_TOP + .02, 3.3, 7.0, UP_TOP + .9, FORGED)
    bx(g, 1.84, 5.54, UP_TOP + .9, 3.36, 7.06, UP_TOP + .98, IRON)
    for x in (2.25, 2.95):
        revolve(g, (x, 6.3, UP_TOP + .98), [(.14, 0), (.14, .55), (.24, .57), (.24, .63), (0, .72)], IRON,
                segments=12)
    pipe_path(g, [(3.3, 6.3, UP_TOP + .5), (5.4, 6.3, UP_TOP + .5), (5.4, 6.3, UP_TOP + 1.2)], .12)
    # Back face: dissolver feed pipes and a shield plug door on the right.
    for x in (2.4, 4.4):
        window(g, x, HY1, 2.9, .62, 'back', 'factory')
    f = Facer(HX1, 6.2, 0, 'right')
    f.box(g, 0, 1.215, .08, 1.8, 2.37, .16, IRON)
    for u in (-.42, .42):
        riveted_panel(g, f, u - .38, u + .38, .15, 2.25, .16, .22, FORGED)
    K.wheel(g, f.p(0, 1.2, .32), .22, 'X')
    g.cylinder(f.p(0, 1.2, .26), .05, .08, IRON, 'X', 8)
    lamp(g, HX1, 7.6, 2.8, face='right')
    trefoil(g, HX1, 3.9, 2.0, face='right', r=.26)


def crane(g, parts):
    for lx in (LX0, LX1):
        # Concrete rail beam with an iron rail.
        # One-tile rail beam on the footprint edge (world y 0..7); the west
        # beam's inner face stops at .93, clear of the hot cells' plinth foot.
        a, b = (lx - .5, lx + .43) if lx < 6 else (lx - .5, lx + .5)
        bx(g, a, 1.0, 0, b, 8.0, .16, CONCRETE)
        bx(g, lx - .05, 1.0, .16, lx + .05, 8.0, .23, IRON)
        for y in (1.1, 7.9):
            bx(g, lx - .12, y - .05, .23, lx + .12, y + .05, .4, IRON)
        # Bogies and sill.
        for y in (BY - 1.3, BY + 1.3):
            bx(g, lx - .2, y - .45, .23, lx + .2, y + .45, .62, PAINTED)
            for dy in (-.25, .25):
                g.cylinder((lx, y + dy, .38), .14, .44, IRON, 'X', 14)
        bx(g, lx - .18, BY - 1.6, .62, lx + .18, BY + 1.6, .9, IRON)
        # A-frame leg: two raking posts, ties and diagonals.
        top = GIRDER_BOT
        p0a, p0b = (lx, BY - 1.35, .9), (lx, BY - .42, top)
        p1a, p1b = (lx, BY + 1.35, .9), (lx, BY + .42, top)
        g.beam(p0a, p0b, .24, mat=IRON)
        g.beam(p1a, p1b, .24, mat=IRON)

        def at(a, b, z):
            t = (z - a[2]) / (b[2] - a[2])
            return (a[0], a[1] + (b[1] - a[1]) * t, z)
        levels = (3.0, 5.2, 7.3)
        for z in levels:
            a, b = at(p0a, p0b, z), at(p1a, p1b, z)
            g.box((lx, (a[1] + b[1]) / 2, z), (.14, b[1] - a[1] - .1, .14), IRON)
        prev = .9
        for k, z in enumerate(levels + (top - .3,)):
            a0, b0 = at(p0a, p0b, prev + .15), at(p1a, p1b, prev + .15)
            a1, b1 = at(p0a, p0b, z - .12), at(p1a, p1b, z - .12)
            off = .1 if lx == LX0 else -.1
            if k % 2:
                g.beam((lx + off, a0[1] + .1, a0[2]), (lx + off, b1[1] - .1, b1[2]), .07, mat=IRON)
            else:
                g.beam((lx + off, b0[1] - .1, b0[2]), (lx + off, a1[1] + .1, a1[2]), .07, mat=IRON)
            prev = z
        ladder(g, lx, BY + .15, .9, top, face='left' if lx == LX0 else 'right', width=.3, cage=False)
        # End carriage on the leg head.
        bx(g, lx - .24, BY - .75, top, lx + .24, BY + .75, GIRDER_TOP + .1, PAINTED)
        bolt_row(g, (lx - .1, BY - .756, top + .45), (lx + .1, BY - .756, top + .45), 2, r=.03)
    # Twin riveted plate girders.
    for y in (BY - .45, BY + .45):
        bx(g, LX0 + .24, y - .09, GIRDER_BOT + .08, LX1 - .24, y + .09, GIRDER_TOP - .08, FORGED)
        for z0, z1 in ((GIRDER_BOT, GIRDER_BOT + .08), (GIRDER_TOP - .08, GIRDER_TOP)):
            bx(g, LX0 + .24, y - .14, z0, LX1 - .24, y + .14, z1, IRON)
        s = -1 if y < BY else 1
        for x in [LX0 + .6 + i * .9 for i in range(12)]:
            if s < 0 and 4.75 < x < 7.25:
                continue
            ya, yb = sorted((y + s * .09, y + s * .115))
            bx(g, x - .03, ya, GIRDER_BOT + .08, x + .03, yb, GIRDER_TOP - .08, IRON)
        bx(g, LX0 + .3, y - .04, GIRDER_TOP, LX1 - .3, y + .04, RAIL_TOP, IRON)
    # Walkway along the front girder at layer 11 with a rail.
    catwalk(g, LX0 + .3, BY - .95, LX1 - .3, BY - .6, 10, rails=('front',), brackets=None)
    for x in [LX0 + .8 + i * 1.6 for i in range(7)]:
        g.beam((x, BY - .6, GIRDER_TOP - .5), (x, BY - .9, GIRDER_TOP - .09), .06, mat=IRON)
    # Board on the bridge.
    f = Facer(6.0, BY - .54, 0, 'front')
    riveted_panel(g, f, -1.1, 1.1, GIRDER_BOT + .18, GIRDER_TOP - .18, 0, .04, ORANGE)
    trefoil(g, 6.0, BY - .58, (GIRDER_BOT + GIRDER_TOP) / 2, face='front', r=.22)
    for lx, name in ((LX0, 'CraneBeaconW'), (LX1, 'CraneBeaconE')):
        px, py, pz = beacon(g, lx, BY + .5, GIRDER_TOP + .1)
        parts.append((beacon_shutter(px, py, pz, name), 'SPIN_Z', 2))
    # Trolley, cask and cables share one cycle (see animate).
    x0 = CYCLE[0][1]
    t = Geometry('CraneTrolley', (x0, BY, RAIL_TOP))
    bx(t, x0 - .6, BY - .62, RAIL_TOP + .12, x0 + .6, BY + .62, RAIL_TOP + .3, PAINTED)
    for y in (BY - .45, BY + .45):
        for dx in (-.4, .4):
            t.cylinder((x0 + dx, y, RAIL_TOP + .1), .1, .12, IRON, 'Y', 12)
    t.cylinder((x0, BY, RAIL_TOP + .58), .26, .9, IRON, 'Y', 16)
    for y in (BY - .48, BY + .48):
        bx(t, x0 - .32, y - .04, RAIL_TOP + .3, x0 + .32, y + .04, RAIL_TOP + .92, IRON)
    t.ring((x0, BY - .2, RAIL_TOP + .58), .28, .04, .06, BRASS, 'Y', 16)
    t.ring((x0, BY + .2, RAIL_TOP + .58), .28, .04, .06, BRASS, 'Y', 16)
    bx(t, x0 + .3, BY - .3, RAIL_TOP + .3, x0 + .58, BY + .3, RAIL_TOP + .72, PAINTED)
    t.cylinder((x0 + .44, BY, RAIL_TOP + .75), .12, .06, IRON, 'Z', 10)
    bx(t, x0 - .58, BY - .3, RAIL_TOP + .3, x0 - .3, BY + .3, RAIL_TOP + .62, FORGED)
    parts.append((t, 'CUSTOM_TROLLEY', 0))
    zb = CYCLE[0][2]
    c = Geometry('SpentFuelCask', (x0, BY, zb))
    yoke = cask(c, x0, BY, zb, h=CASK_H)
    parts.append((c, 'CUSTOM_CASK', 0))
    length = RAIL_TOP + .12 - yoke
    cab = Geometry('HoistCables', (x0, BY, RAIL_TOP + .12))
    for y in (BY - .1, BY + .1):
        cab.box((x0, y, RAIL_TOP + .12 - length / 2), (.03, .03, length), IRON)
    parts.append((cab, 'CUSTOM_CABLE', length))


def pond(g, parts):
    x0, y0, x1, y1 = POND
    w = .3
    bx(g, x0, y0, 0, x1, y0 + w, 1.1, CONCRETE)
    bx(g, x0, y1 - w, 0, x1, y1, 1.1, CONCRETE)
    bx(g, x0, y0 + w, 0, x0 + w, y1 - w, 1.1, CONCRETE)
    bx(g, x1 - w, y0 + w, 0, x1, y1 - w, 1.1, CONCRETE)
    bx(g, x0 + w, y0 + w, .03, x1 - w, y1 - w, .2, CONCRETE)
    # Coping kerb (mitred) and rails.
    for a in ((x0 - .03, y0 - .03, x1 + .03, y0 + w + .01), (x0 - .03, y1 - w - .01, x1 + .03, y1 + .03),
              (x0 - .03, y0 + w + .01, x0 + w + .01, y1 - w - .01), (x1 - w - .01, y0 + w + .01, x1 + .03, y1 - w - .01)):
        bx(g, a[0], a[1], 1.1, a[2], a[3], 1.16, CONCRETE)
    steel_rail(g, (x0 + .1, y0 + .1), (x1 - .1, y0 + .1), 1.16, pitch=.6)
    steel_rail(g, (x1 - .1, y0 + .3), (x1 - .1, y1 - .1), 1.16, pitch=.6)
    g.liquid_surfaces.append(dict(name='CoolingPond', shape='Rectangle', center=[(x0 + x1) / 2, (y0 + y1) / 2],
                                  bottom=.2, top=.95, scale=[x1 - x0 - 2 * w, y1 - y0 - 2 * w], flowOnly=False))
    # Submerged fuel racks either side of the cask station.
    for rx0, rx1 in ((x0 + .45, POND_X - .75), (POND_X + .75, x1 - .45)):
        for ry0, ry1 in ((y0 + .5, BY - .2), (BY + .5, y1 - .5)):
            bx(g, rx0, ry0, .2, rx1, ry1, .3, IRON)
            n = max(2, round((rx1 - rx0) / .32))
            for i in range(n + 1):
                x = rx0 + (rx1 - rx0) * i / n
                bx(g, x - .02, ry0, .3, x + .02, ry1, .82, IRON)
            m = max(2, round((ry1 - ry0) / .32))
            for j in range(m + 1):
                y = ry0 + (ry1 - ry0) * j / m
                bx(g, rx0 + .02, y - .02, .3, rx1 - .02, y + .02, .78, IRON)
    # Circulating pump with a flywheel on the front apron.
    px, py = 8.5, y0 - .5
    bx(g, px - .5, py - .5, 0, px + .5, py + .5, .35, CONCRETE)   # pump bed, world tile 8 x 0
    revolve(g, (px + .15, py, .35), [(.22, 0), (.22, .5), (.12, .58), (.12, .66)], PAINTED, segments=14)
    bx(g, px - .45, py - .18, .35, px - .08, py + .18, .72, IRON)
    g.cylinder((px + .625 - .7, py, .56), .05, .06, IRON, 'X', 8)
    wheel = Geometry('PumpFlywheel', (px - .5, py, .62))
    K.wheel(wheel, (px - .5, py, .62), .26, 'X')
    parts.append((wheel, 'SPIN_X', 3))
    pipe_path(g, [(px + .15, py, 1.0), (px + .15, py, 1.95), (px + .15, y0 + .5, 1.95), (px + .15, y0 + .5, .9)], .08)
    gauge(g, px + .15, py - .22, .6, face='front', r=.08)


def vitrification(g, parts):
    x0, y0, x1, y1 = VH
    bx(g, x0, y0, 0, x1, y1, 2.0, CONCRETE)
    bx(g, x0 - .05, y0 - .05, 1.92, x1 + .05, y1 + .05, 2.012, CONCRETE)
    frame_wall(g, 'X', y0 + .1, x0 + .05, x1 - .05, 2.012, 4.8, outward=-1, infill=ORANGE, bays=3,
               windows=[(8.13, 3.5), (10.07, 3.5)], window_style='factory', window_scale=.9)
    frame_wall(g, 'X', y1 - .1, x0 + .05, x1 - .05, 2.012, 4.8, outward=1, infill=ORANGE, bays=3,
               windows=[(9.1, 3.5)], window_style='factory', window_scale=.9)
    for xp, out in ((x0 + .1, -1), (x1 - .1, 1)):
        frame_wall(g, 'Y', xp, y0 + .15, y1 - .15, 2.012, 4.8, outward=out, infill=ORANGE, bays=4,
                   windows=[(y0 + .15 + (i + .5) * (y1 - y0 - .3) / 4, 3.5) for i in range(4)],
                   window_style='factory', window_scale=.9)
    plank_barrel(g, x0 + .1, x1 - .1, y0 + .1, y1 - .1, 4.8, 1.35, overhang=.18)
    # Furnace block with a glowing pour mouth facing the pond.
    fx0, fx1, fy0 = 8.2, 10.0, y0 - .45
    bx(g, fx0, fy0, 0, fx1, y0, 2.5, CONCRETE)
    bx(g, fx0 - .05, fy0 - .05, 2.42, fx1 + .05, y0 + .05, 2.55, IRON)
    mouth = Facer(9.1, fy0, 0, 'front')
    mouth.box(g, 0, 1.55, .05, .8, .1, .1, IRON)
    for u in (-.45, .45):
        mouth.box(g, u, 1.15, .05, .1, .9, .1, IRON)
    mouth.box(g, 0, 1.1, .015, .8, .8, .03, IRON)
    flame = Geometry('FurnaceGlow', (9.1, fy0 - .03, .8))
    bx(flame, 8.8, fy0 - .07, .8, 9.4, fy0 - .03, 1.4, GLOW)
    parts.append((flame, 'FLAME', 0))
    # Pour spout ledge and the glowing glass stream.
    bx(g, 8.95, fy0 - .32, 1.0, 9.25, fy0, 1.08, IRON)
    bx(g, 9.06, fy0 - .19, .9, 9.14, fy0 - .11, 1.0, GLOW)
    pipe_path(g, [(9.58, fy0 + .2, 2.5), (9.58, fy0 + .2, 4.3), (9.58, y0 + .2, 4.3)], .1)
    # Canister turntable below the spout.
    tx, ty = 9.1, fy0 - .45
    revolve(g, (tx, ty, .015), [(.5, 0), (.5, .235)], CONCRETE, segments=12)
    turn = Geometry('CanisterTurntable', (tx, ty, .25))
    revolve(turn, (tx, ty, .262), [(.48, 0), (.48, .06)], IRON, segments=12)
    for k in range(4):
        a = k * math.pi / 2
        cxx, cyy = tx + math.cos(a) * .3, ty + math.sin(a) * .3
        revolve(turn, (cxx, cyy, .322), [(.11, 0), (.11, .48), (.07, .54), (.07, .58)], IRON, segments=10)
        band(turn, (cxx, cyy, 0), .11, .5, .04, BRASS, segments=10)
    parts.append((turn, 'SPIN_Z', 1))
    # Stack beside the hall.
    sx, sy = 11.5, 8.5
    bx(g, sx - .5, sy - .5, 0, sx + .5, sy + .5, 1.4, CONCRETE)   # stack base, world tile 11 x 7
    bx(g, sx - .55, sy - .55, 1.32, sx + .48, sy + .55, 1.44, CONCRETE)
    stack(g, sx - .05, sy, 1.44, 7.8, emits='steam', r=.4, taper=.8, bands=4)   # scrubbed off-gas
    pipe_path(g, [(x1 - .15, sy, 4.35), (sx - .05, sy, 4.35)], .15)
    ladder(g, sx - .05, sy + .4, 1.44, 9.1, face="back", width=.28)


def dissolvers(g, parts):
    for x, y, r, h, name in ((1.5, 10.4, .6, 8.2, 'AgitatorA'), (3.25, 10.75, .48, 7.0, 'AgitatorB')):
        revolve(g, (x, y, 0), [(r + .12, 0), (r + .12, .3)], CONCRETE, segments=12)
        revolve(g, (x, y, .3), [(r, 0), (r, h - .3)], FORGED if r > .5 else IRON, segments=12)
        for k in range(5):
            band(g, (x, y, 0), r, .9 + k * (h - 1.6) / 4, .07, IRON if r > .5 else PAINTED, segments=12)
        dome(g, (x, y, h), r + .02, IRON, segments=12, squash=.45)
        top = h + (r + .02) * .45
        bx(g, x - .14, y - .14, top - .05, x + .14, y + .14, top + .3, PAINTED)
        a = Geometry(name, (x, y, top + .3))
        a.cylinder((x, y, top + .38), .08, .16, IRON, 'Z', 10)
        a.box((x, y, top + .45), (.4, .06, .05), BRASS)
        parts.append((a, 'SPIN_Z', 2))
        pipe_path(g, [(x, y - r + .05, 2.2), (x, HY1 - .1, 2.2)], .09)
        gauge(g, x + .2, y - r - .01, 1.6, face='front', r=.09)
    # Access lattice tower with platforms between the dissolvers and the cells.
    # 110 mm members: the diagonals' faces stay clear of the catwalk rail faces.
    lattice_tower(g, 4.4, 9.4, 5.2, 10.2, 0, 7.92, bays=5, w=.11)
    for z in (4, 8):
        catwalk(g, 4.3, 9.3, 5.3, 10.3, z, rails=('front', 'back'), brackets=None)
        # Side rail kept clear of the corner rails (the kit's corner runs overlap).
        steel_rail(g, (5.3 - .035, 9.3 + .035 + .05), (5.3 - .035, 10.3 - .035 - .05), z, skip_start=True,
                   skip_end=True)
    catwalk(g, 1.7, 9.55, 4.3, 10.05, 4, rails=('front', 'back'), brackets=None)
    ladder(g, 4.8, 10.2, 0, 8, face='back', width=.3)


def canister_rack(g, parts):
    x0, y0, x1, y1 = 6.0, 9.0, 8.0, 12.0   # world tiles 6..8 x 8..11
    bx(g, x0, y0, 0, x1, y1, .25, CONCRETE)
    for i in range(4):
        for j in range(6):
            x = x0 + .4 + i * .4
            y = y0 + .55 + j * .38
            revolve(g, (x, y, .25), [(.13, 0), (.13, .9), (.08, .96), (.08, 1.02)], IRON, segments=10)
    for x in (x0 + .05, x1 - .05):
        for y in (y0 + .05, y1 - .05):
            bx(g, x - .05, y - .05, .25, x + .05, y + .05, 2.2, IRON)
    # The high eave stops short of the vitrification hall wall (x 8.05).
    plank_slope(g, slope_quad(x0 - .15, 2.15, x1 - .02, 2.45 - .3 * .17 / (x1 - x0 + .3), .07),
                y0 - .15, y1 + .15, axis='Y')
    for y in (y0 + .05, y1 - .05):
        g.beam((x0 - .05, y, 2.1), (x1 + .05, y, 2.4), .08, mat=IRON)


DY = 1.0   # the layout below is authored one tile deeper; build() shifts it forward


def build(g, parts):
    # Shift every authored vertex, and every animated part's pivot, forward by
    # DY as it is added. The vertices reach Geometry.add already shifted, so
    # the extents the harness records for grid registration are the placed
    # art (an origin offset would leave them one tile deep).
    add, init = Geometry.add, Geometry.__init__

    def shifted_add(self, vertices, faces, mat):
        return add(self, [(p[0], p[1] - DY, p[2]) for p in vertices], faces, mat)

    def shifted_init(self, name, origin=(0, 0, 0)):
        init(self, name, (origin[0], origin[1] - DY, origin[2]))
    Geometry.add, Geometry.__init__ = shifted_add, shifted_init
    try:
        hot_cells(g, parts)
        crane(g, parts)
        pond(g, parts)
        vitrification(g, parts)
        dissolvers(g, parts)
        canister_rack(g, parts)
    finally:
        Geometry.add, Geometry.__init__ = add, init
    for d in g.doorways:
        d['position'][1] -= DY
    for w in g.liquid_surfaces:
        w['center'][1] -= DY
    for m in g.window_mounts:
        m['anchor'][1] -= DY
        for edge in m['rearEdges']:
            for i, q in enumerate(edge):
                edge[i] = (q[0], q[1] - DY, q[2])


def _keys(obj, path, index, values, frame_end):
    span = frame_end - 1
    for (t, _, _), v in zip(CYCLE, values):
        setattr_vec(obj, path, index, v)
        obj.keyframe_insert(data_path=path, index=index, frame=1 + span * t)


def setattr_vec(obj, path, index, v):
    getattr(obj, path)[index] = v


def animate(obj, kind, value, frame_end):
    """Shared crane cycle. Artwork X maps to Blender -X; Z is unchanged."""
    bx0, bz0 = obj.location.x, obj.location.z
    xs = [bx0 - (x - CYCLE[0][1]) for _, x, _ in CYCLE]
    if kind == 'CUSTOM_TROLLEY':
        _keys(obj, 'location', 0, xs, frame_end)
    elif kind == 'CUSTOM_CASK':
        _keys(obj, 'location', 0, xs, frame_end)
        _keys(obj, 'location', 2, [bz0 + (z - CYCLE[0][2]) for _, _, z in CYCLE], frame_end)
    elif kind == 'CUSTOM_CABLE':
        _keys(obj, 'location', 0, xs, frame_end)
        # Cable hangs from the trolley; its length tracks the cask yoke.
        _keys(obj, 'scale', 2, [(value - (z - CYCLE[0][2])) / value for _, _, z in CYCLE], frame_end)
    else:
        raise ValueError(kind)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'BEZIER'
            key.handle_left_type = key.handle_right_type = 'AUTO_CLAMPED'
