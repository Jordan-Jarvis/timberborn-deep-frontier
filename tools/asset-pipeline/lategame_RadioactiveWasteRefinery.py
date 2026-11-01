"""Radioactive Waste Refinery: late-game study (Iron Teeth, Deep Frontier).

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; outputs/compaction/BRIEF.md): 12x11x12 -> 9x7x7.

Shrunk again 2026-11-01 (user: "we need to shrink the buildings down even
more"; second shrink pass): 9x7x7 -> 5x5x5, inside the old footprint with
the same origin, door (x 1.5, face 0.15 behind the front edge) and native
entrance (1,-1). The hot cells are a 3x3 block, the cooling pond 2x2 in
front of the vitrification hall, the dissolver bund 3x2 behind the hot
cells. The process platform and the canister rack are gone; the pond pump
stands on the pond's back wall, the furnace mouth and the canister
turntable face the bund, and the stack rises from the ground through a
one-layer filter house at the back right. The crane is one layer lower.

HERO: the cask crane, a riveted twin-girder bridge on a concrete pier and a
roof pedestal, which lifts a finned spent-fuel cask out of the cooling pond
and lowers it into the roof hatch of the shielded hot cells.
ROOF: flat concrete roof, open edge to edge, on the hot cells (layer 2) and
the filter house (layer 1); a pitched corrugated-metal gable on the
vitrification hall; no roof vents.

Animated (names unchanged): crane trolley (CUSTOM_TROLLEY), cask on its
yoke (CUSTOM_CASK) and hoist cables (CUSTOM_CABLE) following one shared
lift-travel-lower cycle, pond pump flywheel (SPIN_X), furnace glow (FLAME),
canister turntable (SPIN_Z), dissolver agitator drives (SPIN_Z), two crane
beacons (SPIN_Z).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import (CONCRETE, ORANGE, FORGED, PAINTED, CYAN, GLOW, frame_wall, revolve, band,
                          dome, stack, hollow_revolve, flat_roof, lamp, beacon, beacon_shutter)
from lategame_nuclear_parts import (bx, Facer, trefoil, gauge, riveted_panel, pipe_path, manipulator_port,
                                    obox, cask)
from architectural_windows import window
from lategame_sheet_roofs import sheet_gable
import lategame_mining_parts as M

IDENT = 'RadioactiveWasteRefinery'
FOOTPRINT = (5, 5)
HEIGHT = 5
HERO = ('Cask crane: a riveted twin-girder bridge on a concrete pier lifts a finned spent-fuel cask from '
        'the cooling pond into the hot-cell roof hatch.')
FRAME_END = 121

# Hot cells: tiles 0..3 x 0..3, door face .15 off the front edge.
HX0, HY0, HX1, HY1 = 0.0, .15, 3.0, 3.0
CELL_TOP = 1.84            # roof slab bottom; its top is layer 2
ROOF = 2.0
# Crane
BY = 1.0                   # bridge centreline (trolley travel line)
GX0, GX1 = .3, 4.97        # girder ends
GIRDER_BOT, GIRDER_TOP = 3.9, 4.28
RAIL_TOP = GIRDER_TOP + .05
POND_X, CELL_X = 4.0, 1.5  # cask pick and set-down stations
CASK_R, CASK_H = .3, .72
# Cask cycle: (loop fraction, trolley x, cask bottom z)
CYCLE = [(0, POND_X, .3), (.2, POND_X, 2.32), (.38, CELL_X, 2.32), (.48, CELL_X, 2.06), (.56, CELL_X, 2.06),
         (.66, CELL_X, 2.32), (.84, POND_X, 2.32), (1.0, POND_X, .3)]
POND = (3.0, 0.0, 5.0, 2.0)    # tiles 3..5 x 0..2
POND_BACK = .4                 # back wall carries the pump
VH = (3.0, 2.0, 5.0, 4.0)      # vitrification hall, tiles 3..5 x 2..4
VH_WALL = 1.84
FILTER = (3.0, 4.0, 5.0, 5.0)  # filter house, tiles 3..5 x 4..5, roof top layer 1
PLAT = 1.0                     # dissolver bund top (layer 1)


def hot_cells(g, parts):
    # One-storey shielded block: proud concrete course notched for the door.
    M.plinth_course(g, HX0 + .05, HX1 - .05, HY0 + .12, HY1 - .05, 0, CELL_TOP, CONCRETE, [1.5])
    M.portal(g, 1.5, HY0 + .12, 0, ident='Main')
    wall = HY0 + .07
    lamp(g, .75, wall, .8, face='front')
    # Shielded window with its cast surround and a master-slave manipulator.
    x = 2.45
    window(g, x, wall, .95, .5, 'front', 'factory')
    f = Facer(x, wall, 0, 'front')
    f.box(g, -.27, .95, .08, .08, .62, .16, CONCRETE)
    f.box(g, .27, .95, .08, .08, .62, .16, CONCRETE)
    f.box(g, 0, .6, .09, .62, .08, .18, CONCRETE)
    manipulator_port(g, x, wall, 1.45, face='front', reach=.3)
    trefoil(g, 1.5, wall, 1.45, face='front', r=.18)
    # Left wall: a second shielded window.
    window(g, HX0 + .05, 1.8, .95, .5, 'left', 'factory')
    flat_roof(g, HX0 + .05, HY0 + .05, HX1 - .05, HY1 - .05, CELL_TOP, overhang=.05)
    # Roof hatch collar at the cask set-down station.
    hollow_revolve(g, (CELL_X, BY, ROOF), [(.5, 0), (.5, .24)], .1, IRON, segments=16)
    g.ring((CELL_X, BY, ROOF + .21), .52, .035, .05, BRASS, 'Z', 16)
    revolve(g, (CELL_X, BY, ROOF + .012), [(.42, 0), (.42, .02)], IRON, segments=16)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        obox(g, (CELL_X + math.cos(a) * .58, BY + math.sin(a) * .58, ROOF + .12), a, .16, .07, .2, IRON)


def crane(g, parts):
    # Solid concrete pier on the pond's right wall and the pedestal on the
    # hot-cell roof carry the end carriages.
    bx(g, 4.65, BY - .3, .07, 4.97, BY + .3, GIRDER_BOT - .22, CONCRETE)
    bx(g, 4.6, BY - .35, GIRDER_BOT - .27, 4.99, BY + .35, GIRDER_BOT - .18, CONCRETE)
    bx(g, GX0 - .02, BY - .3, ROOF, GX0 + .34, BY + .3, GIRDER_BOT - .22, CONCRETE)
    bx(g, GX0 - .05, BY - .35, GIRDER_BOT - .27, GX0 + .37, BY + .35, GIRDER_BOT - .18, CONCRETE)
    for x in (GX0 + .16, 4.81):
        bx(g, x - .17, BY - .52, GIRDER_BOT - .18, x + .17, BY + .52, GIRDER_TOP + .08, PAINTED)
    # Twin riveted plate girders.
    for y in (BY - .34, BY + .34):
        bx(g, GX0 + .33, y - .07, GIRDER_BOT + .06, 4.64, y + .07, GIRDER_TOP - .06, FORGED)
        for z0, z1 in ((GIRDER_BOT, GIRDER_BOT + .06), (GIRDER_TOP - .06, GIRDER_TOP)):
            bx(g, GX0 + .33, y - .1, z0, 4.64, y + .1, z1, IRON)
        s = -1 if y < BY else 1
        for x in [GX0 + .8 + i * .8 for i in range(5)]:
            if s < 0 and 2.2 < x < 3.4:
                continue
            ya, yb = sorted((y + s * .07, y + s * .09))
            bx(g, x - .03, ya, GIRDER_BOT + .06, x + .03, yb, GIRDER_TOP - .06, IRON)
        bx(g, GX0 + .38, y - .03, GIRDER_TOP, 4.59, y + .03, RAIL_TOP, IRON)
    # Board on the bridge.
    f = Facer(2.8, BY - .41, 0, 'front')
    riveted_panel(g, f, -.55, .55, GIRDER_BOT + .08, GIRDER_TOP - .08, 0, .035, ORANGE)
    trefoil(g, 2.8, BY - .45, (GIRDER_BOT + GIRDER_TOP) / 2, face='front', r=.13)
    for x, name in ((GX0 + .16, 'CraneBeaconW'), (4.81, 'CraneBeaconE')):
        px, py, pz = beacon(g, x, BY + .34, GIRDER_TOP + .08)
        parts.append((beacon_shutter(px, py, pz, name), 'SPIN_Z', 2))
    # Trolley, cask and cables share one cycle (see animate).
    x0 = CYCLE[0][1]
    t = Geometry('CraneTrolley', (x0, BY, RAIL_TOP))
    bx(t, x0 - .42, BY - .47, RAIL_TOP + .08, x0 + .42, BY + .47, RAIL_TOP + .22, PAINTED)
    for y in (BY - .34, BY + .34):
        for dx in (-.26, .26):
            t.cylinder((x0 + dx, y, RAIL_TOP + .08), .08, .09, IRON, 'Y', 12)
    t.cylinder((x0, BY, RAIL_TOP + .4), .18, .62, IRON, 'Y', 16)
    for y in (BY - .35, BY + .35):
        bx(t, x0 - .22, y - .03, RAIL_TOP + .22, x0 + .22, y + .03, RAIL_TOP + .62, IRON)
    t.ring((x0, BY - .14, RAIL_TOP + .4), .2, .03, .045, BRASS, 'Y', 16)
    t.ring((x0, BY + .14, RAIL_TOP + .4), .2, .03, .045, BRASS, 'Y', 16)
    bx(t, x0 + .22, BY - .22, RAIL_TOP + .22, x0 + .4, BY + .22, RAIL_TOP + .5, PAINTED)
    bx(t, x0 - .4, BY - .22, RAIL_TOP + .22, x0 - .22, BY + .22, RAIL_TOP + .44, FORGED)
    parts.append((t, 'CUSTOM_TROLLEY', 0))
    zb = CYCLE[0][2]
    c = Geometry('SpentFuelCask', (x0, BY, zb))
    yoke = cask(c, x0, BY, zb, r=CASK_R, h=CASK_H)
    parts.append((c, 'CUSTOM_CASK', 0))
    length = RAIL_TOP + .08 - yoke
    cab = Geometry('HoistCables', (x0, BY, RAIL_TOP + .08))
    for y in (BY - .08, BY + .08):
        cab.box((x0, y, RAIL_TOP + .08 - length / 2), (.03, .03, length), IRON)
    parts.append((cab, 'CUSTOM_CABLE', length))


def pond(g, parts):
    x0, y0, x1, y1 = POND
    w = .25
    top = .8
    bx(g, x0, y0, 0, x1, y0 + w, top, CONCRETE)
    bx(g, x0, y1 - POND_BACK, 0, x1, y1, top, CONCRETE)
    bx(g, x0, y0 + w, 0, x0 + w, y1 - POND_BACK, top, CONCRETE)
    bx(g, x1 - w, y0 + w, 0, x1, y1 - POND_BACK, top, CONCRETE)
    bx(g, x0 + w, y0 + w, .03, x1 - w, y1 - POND_BACK, .2, CONCRETE)
    for a in ((x0 + .02, y0 - .03, x1 - .02, y0 + w + .01), (x0 + .02, y1 - POND_BACK - .01, x1 - .02, y1 - .02),
              (x0 + .02, y0 + w + .01, x0 + w + .01, y1 - POND_BACK - .01),
              (x1 - w - .01, y0 + w + .01, x1 - .02, y1 - POND_BACK - .01)):
        bx(g, a[0], a[1], top, a[2], a[3], top + .06, CONCRETE)
    g.liquid_surfaces.append(dict(name='CoolingPond', shape='Rectangle',
                                  center=[(x0 + x1) / 2, (y0 + w + y1 - POND_BACK) / 2],
                                  bottom=.2, top=.68, scale=[x1 - x0 - 2 * w, y1 - POND_BACK - y0 - w], flowOnly=False))
    # Submerged fuel racks either side of the cask station.
    for rx0, rx1 in ((x0 + .35, POND_X - .45), (POND_X + .45, x1 - .35)):
        for ry0, ry1 in ((y0 + .35, BY - .38), (BY + .38, y1 - POND_BACK - .1)):
            bx(g, rx0, ry0, .2, rx1, ry1, .28, IRON)
            n = max(2, round((rx1 - rx0) / .25))
            for i in range(n + 1):
                x = rx0 + (rx1 - rx0) * i / n
                bx(g, x - .02, ry0, .28, x + .02, ry1, .55, IRON)
    # Circulating pump on the pond's back wall, its pipe into the hall.
    px, py, pz = 3.75, y1 - POND_BACK / 2, top + .06
    revolve(g, (px + .45, py, pz), [(.15, 0), (.15, .34), (.08, .39), (.08, .46)], PAINTED, segments=14)
    bx(g, px - .2, py - .13, pz, px + .2, py + .13, pz + .26, IRON)
    g.cylinder((px + .25, py, pz + .15), .04, .1, IRON, 'X', 8)
    wheel = Geometry('PumpFlywheel', (px - .28, py, pz + .2))
    K.wheel(wheel, (px - .28, py, pz + .2), .18, 'X')
    parts.append((wheel, 'SPIN_X', 3))
    pipe_path(g, [(px + .45, py, pz + .46), (px + .45, py, pz + .6), (px + .45, y1 + .02, pz + .6)], .06)
    gauge(g, px + .45, py - .16, pz + .18, face='front', r=.06)


def vitrification(g, parts):
    x0, y0, x1, y1 = VH
    bx(g, x0, y0, 0, x1, y1, .92, CONCRETE)
    bx(g, x0 - .03, y0 - .03, .92, x1, y1, 1.012, CONCRETE)
    frame_wall(g, 'X', y0 + .1, x0 + .05, x1 - .05, 1.012, VH_WALL, outward=-1, infill=ORANGE, bays=2,
               windows=[(4.5, 1.45)], window_style='factory', window_scale=.5)
    frame_wall(g, 'Y', x1 - .1, y0 + .15, y1 - .05, 1.012, VH_WALL, outward=1, infill=ORANGE, bays=2,
               windows=[(3.0, 1.45)], window_style='factory', window_scale=.5)
    frame_wall(g, 'Y', x0 + .1, y0 + .15, y1 - .05, 1.012, VH_WALL, outward=-1, infill=ORANGE, bays=2)
    frame_wall(g, 'X', y1 - .1, x0 + .15, x1 - .15, 1.012, VH_WALL, outward=1, infill=ORANGE, bays=2)
    bx(g, x0 + .2, y0 + .25, 1.012, x1 - .2, y1 - .25, VH_WALL, IRON)   # solid hall room
    sheet_gable(g, x0 + .05, y0 + .05, x1 - .05, y1, VH_WALL, VH_WALL + .85, ridge_axis='Y', overhang=.1,
                mat=PAINTED, gable_mat=ORANGE)
    # Furnace hood on the hall's left wall with a glowing pour mouth facing the bund.
    fy0, fy1, fx0 = 2.95, 3.85, x0 - .4
    bx(g, fx0, fy0, PLAT - .02, x0 + .05, fy1, 2.1, CONCRETE)
    bx(g, fx0 - .05, fy0 - .05, 2.02, x0 + .05, fy1 + .05, 2.14, IRON)
    yc = (fy0 + fy1) / 2
    mouth = Facer(fx0, yc, 0, 'left')
    mouth.box(g, 0, PLAT + .78, .05, .6, .09, .1, IRON)
    for u in (-.34, .34):
        mouth.box(g, u, PLAT + .5, .05, .09, .66, .1, IRON)
    mouth.box(g, 0, PLAT + .45, .015, .6, .56, .03, IRON)
    flame = Geometry('FurnaceGlow', (fx0 - .03, yc, PLAT + .25))
    bx(flame, fx0 - .07, yc - .22, PLAT + .25, fx0 - .03, yc + .22, PLAT + .68, GLOW)
    parts.append((flame, 'FLAME', 0))
    bx(g, fx0 - .26, yc - .1, PLAT + .4, fx0, yc + .1, PLAT + .47, IRON)
    bx(g, fx0 - .17, yc - .03, PLAT + .31, fx0 - .11, yc + .03, PLAT + .4, GLOW)
    # Canister turntable on the bund below the spout.
    tx, ty = fx0 - .5, yc
    revolve(g, (tx, ty, PLAT - .02), [(.4, 0), (.4, .1)], CONCRETE, segments=12)
    turn = Geometry('CanisterTurntable', (tx, ty, PLAT + .08))
    revolve(turn, (tx, ty, PLAT + .092), [(.38, 0), (.38, .05)], IRON, segments=12)
    for k in range(4):
        a = k * math.pi / 2
        cxx, cyy = tx + math.cos(a) * .23, ty + math.sin(a) * .23
        revolve(turn, (cxx, cyy, PLAT + .142), [(.09, 0), (.09, .38), (.055, .42), (.055, .45)], IRON, segments=10)
        band(turn, (cxx, cyy, 0), .09, PLAT + .3, .04, BRASS, segments=10)
    parts.append((turn, 'SPIN_Z', 1))


def filter_house(g, parts):
    x0, y0, x1, y1 = FILTER
    bx(g, x0 + .05, y0, 0, x1 - .05, y1 - .05, .84, CONCRETE)
    flat_roof(g, x0 + .05, y0, x1 - .05, y1 - .05, .84, overhang=.03)
    window(g, 3.5, y1 - .05, .45, .4, 'back', 'factory')
    # Off-gas stack rising from the ground through the filter house corner.
    sx, sy = 4.5, 4.5
    bx(g, sx - .32, sy - .32, 0.03, sx + .32, sy + .32, 2.2, CONCRETE)
    stack(g, sx, sy, 2.2, 2.4, emits='steam', r=.22, taper=.8, bands=2)


def dissolvers(g, parts):
    # Concrete bund (tiles 0..3 x 3..5, top layer 1) carrying both tanks.
    bx(g, 0.0, 3.0, 0, 3.0, 4.97, PLAT - .1, CONCRETE)
    bx(g, 0.0, 3.0, PLAT - .1, 3.0, 5.0, PLAT, CONCRETE)
    for x in (.5, 1.5, 2.5):
        bx(g, x - .05, 4.97, .12, x + .05, 5.0, PLAT - .2, CONCRETE)
    for x, y, r, h, name in ((.7, 4.1, .5, 2.9, 'AgitatorA'), (1.75, 4.35, .4, 2.6, 'AgitatorB')):
        revolve(g, (x, y, PLAT), [(r + .07, 0), (r + .07, .14)], CONCRETE, segments=12)
        revolve(g, (x, y, PLAT + .14), [(r, 0), (r, h - PLAT - .14)], FORGED if r > .45 else IRON, segments=12)
        for k in range(2):
            band(g, (x, y, 0), r, PLAT + .4 + k * (h - PLAT - .8), .07, IRON if r > .45 else PAINTED, segments=12)
        dome(g, (x, y, h), r + .02, IRON, segments=12, squash=.45)
        top = h + (r + .02) * .45
        bx(g, x - .12, y - .12, top - .05, x + .12, y + .12, top + .24, PAINTED)
        a = Geometry(name, (x, y, top + .24))
        a.cylinder((x, y, top + .31), .065, .14, IRON, 'Z', 10)
        a.box((x, y, top + .37), (.32, .05, .045), BRASS)
        parts.append((a, 'SPIN_Z', 2))
        pipe_path(g, [(x, y - r + .05, PLAT + .5), (x, HY1 + .02, PLAT + .5)], .07)
        gauge(g, x + .18, y - r - .01, PLAT + .9, face='front', r=.07)


def build(g, parts):
    hot_cells(g, parts)
    crane(g, parts)
    pond(g, parts)
    vitrification(g, parts)
    filter_house(g, parts)
    dissolvers(g, parts)


def _keys(obj, path, index, values, frame_end):
    span = frame_end - 1
    for (t, _, _), v in zip(CYCLE, values):
        getattr(obj, path)[index] = v
        obj.keyframe_insert(data_path=path, index=index, frame=1 + span * t)


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
