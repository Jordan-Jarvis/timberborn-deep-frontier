"""Radioactive Waste Refinery: late-game study (Iron Teeth, Deep Frontier).

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; outputs/compaction/BRIEF.md): 12x11x12 -> 9x7x7, inside the old
footprint with the same origin, door (x 1.5, face 0.15 behind the front
edge) and native entrance. The 10-layer goliath gantry (open A-frame legs on
rail bogies, leg ladders, girder catwalk) is replaced by a short riveted box
girder that rests on one solid concrete pier in the pond and a concrete
pedestal on the hot-cell roof. Also removed: the hot cells' raised setback
storey and plank lean-to, the dissolver access lattice tower and catwalks,
the canister shed on posts and the 9-layer stack. The vitrification hall's
plank barrel vault is now a pitched corrugated-metal gable, and the stack
rises from the ground (roof-variety pass). One layer per floor throughout.

HERO: the cask crane, a riveted twin-girder bridge on a concrete pier and a
roof pedestal, which lifts a finned spent-fuel cask out of the cooling pond
and lowers it into the roof hatch of the shielded hot cells.
ROOF: flat concrete roof with an open parapet ring on the hot cells (layer
2); a pitched corrugated-metal gable on the vitrification hall; no roof vents
(roof-variety pass).

Supporting masses: the hot-cell block with shielded windows and
master-slave manipulator ports, the cooling pond in native water with
submerged racks and a circulating pump, the vitrification furnace with its
glowing pour mouth and canister turntable, two dissolver tanks with their
agitators, and a vitrified-canister rack.

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
                          dome, stack, hollow_revolve, flat_roof, steel_rail, lamp, beacon, beacon_shutter)
from lategame_nuclear_parts import (bx, Facer, trefoil, gauge, riveted_panel, pipe_path, manipulator_port,
                                    obox, cask)
from architectural_windows import window
from lategame_roofdeck_parts import parapet_ring
from lategame_sheet_roofs import sheet_gable
import lategame_mining_parts as M

IDENT = 'RadioactiveWasteRefinery'
FOOTPRINT = (9, 7)
HEIGHT = 7
HERO = ('Cask crane: a riveted twin-girder bridge on a concrete pier lifts a finned spent-fuel cask from '
        'the cooling pond into the hot-cell roof hatch.')
FRAME_END = 121

# Hot cells: tiles 0..4 x 0..4, door face .15 off the front edge.
HX0, HY0, HX1, HY1 = 0.0, .15, 4.0, 4.0
CELL_TOP = 1.84            # roof slab bottom; its top is layer 2
ROOF = 2.0
# Crane
BY = 1.5                   # bridge centreline (trolley travel line)
GX0, GX1 = .35, 8.95       # girder ends
GIRDER_BOT, GIRDER_TOP = 4.5, 5.0
RAIL_TOP = GIRDER_TOP + .05
POND_X, CELL_X = 7.5, 2.5  # cask pick and set-down stations
CASK_R, CASK_H = .38, 1.0
# Cask cycle: (loop fraction, trolley x, cask bottom z)
CYCLE = [(0, POND_X, .35), (.2, POND_X, 2.6), (.38, CELL_X, 2.6), (.48, CELL_X, 2.32), (.56, CELL_X, 2.32),
         (.66, CELL_X, 2.6), (.84, POND_X, 2.6), (1.0, POND_X, .35)]
POND = (6.0, 0.0, 9.0, 3.0)    # tiles 6..9 x 0..3
VH = (4.0, 3.0, 9.0, 7.0)      # vitrification hall, tiles 4..9 x 3..7
VH_ROOF = 2.84
PLAT = 1.0                 # process platform and dissolver bund tops (layer 1)


def hot_cells(g, parts):
    # One-storey shielded block: proud concrete course notched for the door.
    M.plinth_course(g, HX0 + .05, HX1 - .05, HY0 + .12, HY1 - .05, 0, CELL_TOP, CONCRETE, [1.5])
    M.portal(g, 1.5, HY0 + .12, 0, ident='Main')
    wall = HY0 + .07
    lamp(g, .85, wall, .8, face='front')
    # Shielded windows: deep cast surrounds, native factory glazing, and a
    # pair of master-slave manipulators beside each.
    for x in (2.6, 3.45):
        window(g, x, wall, .95, .5, 'front', 'factory')
        f = Facer(x, wall, 0, 'front')
        f.box(g, -.27, .95, .08, .08, .62, .16, CONCRETE)
        f.box(g, .27, .95, .08, .08, .62, .16, CONCRETE)
        f.box(g, 0, .6, .09, .62, .08, .18, CONCRETE)
        manipulator_port(g, x, wall, 1.45, face='front', reach=.35)
    trefoil(g, 1.5, wall, 1.45, face='front', r=.2)
    flat_roof(g, HX0 + .05, HY0 + .05, HX1 - .05, HY1 - .05, CELL_TOP, overhang=.05)
    parapet_ring(g, HX0, HY0, HX1, HY1, ROOF, height=.26)
    # Roof hatch collar at the cask set-down station.
    hollow_revolve(g, (CELL_X, BY, ROOF), [(.62, 0), (.62, .3)], .12, IRON, segments=16)
    g.ring((CELL_X, BY, ROOF + .27), .64, .04, .05, BRASS, 'Z', 16)
    revolve(g, (CELL_X, BY, ROOF + .012), [(.52, 0), (.52, .02)], IRON, segments=16)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        obox(g, (CELL_X + math.cos(a) * .72, BY + math.sin(a) * .72, ROOF + .15), a, .2, .08, .26, IRON)
    # Back face: shielded window.
    window(g, 1.6, HY1, .95, .5, 'back', 'factory')


def crane(g, parts):
    # Solid concrete pier on the pond's back-right wall and the pedestal on
    # the hot-cell roof carry the end carriages.
    bx(g, 8.62, BY - .35, .07, 8.97, BY + .35, GIRDER_BOT - .25, CONCRETE)
    bx(g, 8.56, BY - .41, GIRDER_BOT - .3, 8.99, BY + .41, GIRDER_BOT - .2, CONCRETE)
    bx(g, GX0 - .02, BY - .35, ROOF, GX0 + .4, BY + .35, GIRDER_BOT - .25, CONCRETE)
    bx(g, GX0 - .05, BY - .41, GIRDER_BOT - .3, GX0 + .43, BY + .41, GIRDER_BOT - .2, CONCRETE)
    for x in (GX0 + .19, 8.79):
        bx(g, x - .2, BY - .62, GIRDER_BOT - .2, x + .2, BY + .62, GIRDER_TOP + .1, PAINTED)
    # Twin riveted plate girders.
    for y in (BY - .4, BY + .4):
        bx(g, GX0 + .39, y - .08, GIRDER_BOT + .07, 8.59, y + .08, GIRDER_TOP - .07, FORGED)
        for z0, z1 in ((GIRDER_BOT, GIRDER_BOT + .07), (GIRDER_TOP - .07, GIRDER_TOP)):
            bx(g, GX0 + .39, y - .12, z0, 8.59, y + .12, z1, IRON)
        s = -1 if y < BY else 1
        for x in [GX0 + 1.0 + i * 1.0 for i in range(8)]:
            if s < 0 and 4.0 < x < 6.0:
                continue
            ya, yb = sorted((y + s * .08, y + s * .1))
            bx(g, x - .03, ya, GIRDER_BOT + .07, x + .03, yb, GIRDER_TOP - .07, IRON)
        bx(g, GX0 + .45, y - .035, GIRDER_TOP, 8.53, y + .035, RAIL_TOP, IRON)
    # Board on the bridge.
    f = Facer(5.0, BY - .48, 0, 'front')
    riveted_panel(g, f, -.85, .85, GIRDER_BOT + .1, GIRDER_TOP - .1, 0, .04, ORANGE)
    trefoil(g, 5.0, BY - .52, (GIRDER_BOT + GIRDER_TOP) / 2, face='front', r=.17)
    for x, name in ((GX0 + .19, 'CraneBeaconW'), (8.79, 'CraneBeaconE')):
        px, py, pz = beacon(g, x, BY + .4, GIRDER_TOP + .1)
        parts.append((beacon_shutter(px, py, pz, name), 'SPIN_Z', 2))
    # Trolley, cask and cables share one cycle (see animate).
    x0 = CYCLE[0][1]
    t = Geometry('CraneTrolley', (x0, BY, RAIL_TOP))
    bx(t, x0 - .5, BY - .55, RAIL_TOP + .1, x0 + .5, BY + .55, RAIL_TOP + .26, PAINTED)
    for y in (BY - .4, BY + .4):
        for dx in (-.32, .32):
            t.cylinder((x0 + dx, y, RAIL_TOP + .09), .09, .1, IRON, 'Y', 12)
    t.cylinder((x0, BY, RAIL_TOP + .5), .22, .76, IRON, 'Y', 16)
    for y in (BY - .41, BY + .41):
        bx(t, x0 - .27, y - .035, RAIL_TOP + .26, x0 + .27, y + .035, RAIL_TOP + .8, IRON)
    t.ring((x0, BY - .17, RAIL_TOP + .5), .24, .035, .05, BRASS, 'Y', 16)
    t.ring((x0, BY + .17, RAIL_TOP + .5), .24, .035, .05, BRASS, 'Y', 16)
    bx(t, x0 + .26, BY - .26, RAIL_TOP + .26, x0 + .48, BY + .26, RAIL_TOP + .62, PAINTED)
    bx(t, x0 - .48, BY - .26, RAIL_TOP + .26, x0 - .26, BY + .26, RAIL_TOP + .54, FORGED)
    parts.append((t, 'CUSTOM_TROLLEY', 0))
    zb = CYCLE[0][2]
    c = Geometry('SpentFuelCask', (x0, BY, zb))
    yoke = cask(c, x0, BY, zb, r=CASK_R, h=CASK_H)
    parts.append((c, 'CUSTOM_CASK', 0))
    length = RAIL_TOP + .1 - yoke
    cab = Geometry('HoistCables', (x0, BY, RAIL_TOP + .1))
    for y in (BY - .09, BY + .09):
        cab.box((x0, y, RAIL_TOP + .1 - length / 2), (.03, .03, length), IRON)
    parts.append((cab, 'CUSTOM_CABLE', length))


def pond(g, parts):
    x0, y0, x1, y1 = POND
    w = .3
    top = .8
    bx(g, x0, y0, 0, x1, y0 + w, top, CONCRETE)
    bx(g, x0, y1 - w, 0, x1, y1, top, CONCRETE)
    bx(g, x0, y0 + w, 0, x0 + w, y1 - w, top, CONCRETE)
    bx(g, x1 - w, y0 + w, 0, x1, y1 - w, top, CONCRETE)
    bx(g, x0 + w, y0 + w, .03, x1 - w, y1 - w, .2, CONCRETE)
    for a in ((x0 - .03, y0 - .03, x1 + .03, y0 + w + .01), (x0 - .03, y1 - w - .01, x1 + .03, y1 + .03),
              (x0 - .03, y0 + w + .01, x0 + w + .01, y1 - w - .01), (x1 - w - .01, y0 + w + .01, x1 + .03, y1 - w - .01)):
        bx(g, a[0], a[1], top, a[2], a[3], top + .06, CONCRETE)
    steel_rail(g, (x0 + .1, y0 + .1), (x1 - .1, y0 + .1), top + .06, pitch=.6)
    g.liquid_surfaces.append(dict(name='CoolingPond', shape='Rectangle', center=[(x0 + x1) / 2, (y0 + y1) / 2],
                                  bottom=.2, top=.68, scale=[x1 - x0 - 2 * w, y1 - y0 - 2 * w], flowOnly=False))
    # Submerged fuel racks either side of the cask station.
    for rx0, rx1 in ((x0 + .45, POND_X - .6), (POND_X + .6, x1 - .45)):
        for ry0, ry1 in ((y0 + .45, BY - .45), (BY + .45, y1 - .45)):
            bx(g, rx0, ry0, .2, rx1, ry1, .28, IRON)
            n = max(2, round((rx1 - rx0) / .3))
            for i in range(n + 1):
                x = rx0 + (rx1 - rx0) * i / n
                bx(g, x - .02, ry0, .28, x + .02, ry1, .58, IRON)
    # Process platform (tiles 4..6 x 0..3): a solid one-layer concrete block
    # carrying the circulating pump, the turntable and the furnace.
    bx(g, 4.0, 0.0, 0, 6.0, 2.95, PLAT - .1, CONCRETE)
    bx(g, 3.98, -.02, PLAT - .1, 6.0, 2.95, PLAT, CONCRETE)
    for x in (4.5, 5.5):
        bx(g, x - .05, -.04, .12, x + .05, 0, PLAT - .2, CONCRETE)
    px, py, pz = 4.75, .55, PLAT
    revolve(g, (px + .15, py, pz), [(.2, 0), (.2, .44), (.11, .5), (.11, .58)], PAINTED, segments=14)
    bx(g, px - .4, py - .16, pz, px - .08, py + .16, pz + .32, IRON)
    g.cylinder((px - .1, py, pz + .2), .045, .06, IRON, 'X', 8)
    wheel = Geometry('PumpFlywheel', (px - .48, py, pz + .25))
    K.wheel(wheel, (px - .48, py, pz + .25), .23, 'X')
    parts.append((wheel, 'SPIN_X', 3))
    pipe_path(g, [(px + .15, py, pz + .58), (px + .15, py, pz + .75), (6.15, py, pz + .75), (6.15, py, .75)], .07)
    gauge(g, px + .15, py - .2, pz + .22, face='front', r=.07)


def vitrification(g, parts):
    x0, y0, x1, y1 = VH
    bx(g, x0, y0, 0, x1, y1, .92, CONCRETE)
    bx(g, x0 - .05, y0 - .05, .92, x1 + .05, y1, 1.012, CONCRETE)
    frame_wall(g, 'X', y0 + .1, x0 + .05, x1 - .05, 1.012, VH_ROOF, outward=-1, infill=ORANGE, bays=5,
               windows=[(6.5, 1.95), (7.5, 1.95), (8.5, 1.95)], window_style='factory', window_scale=.6)
    frame_wall(g, 'X', y1 - .1, x0 + .05, x1 - .05, 1.012, VH_ROOF, outward=1, infill=ORANGE, bays=5,
               windows=[(5.5, 1.95), (7.0, 1.95)], window_style='factory', window_scale=.6)
    for xp, out in ((x0 + .1, -1), (x1 - .1, 1)):
        frame_wall(g, 'Y', xp, y0 + .15, y1 - .15, 1.012, VH_ROOF, outward=out, infill=ORANGE, bays=4,
                   windows=[(4.0, 1.95), (6.0, 1.95)] if out > 0 else [], window_style='factory', window_scale=.6)
    bx(g, x0 + .2, y0 + .25, 1.012, x1 - .2, y1 - .25, VH_ROOF, IRON)   # solid hall room
    sheet_gable(g, x0 + .05, y0 + .05, x1 - .05, y1 - .05, VH_ROOF, VH_ROOF + 1.0, ridge_axis='Y', overhang=.1,
                mat=PAINTED, gable_mat=ORANGE)
    # Furnace block with a glowing pour mouth facing the front.
    fx0, fx1, fy0 = 4.5, 5.9, y0 - .45
    bx(g, fx0, fy0, PLAT - .02, fx1, y0, 2.45, CONCRETE)
    bx(g, fx0 - .05, fy0 - .05, 2.37, fx1 + .05, y0 - .05, 2.5, IRON)
    mouth = Facer(5.2, fy0, 0, 'front')
    mouth.box(g, 0, PLAT + .95, .05, .7, .1, .1, IRON)
    for u in (-.4, .4):
        mouth.box(g, u, PLAT + .6, .05, .1, .8, .1, IRON)
    mouth.box(g, 0, PLAT + .55, .015, .7, .7, .03, IRON)
    flame = Geometry('FurnaceGlow', (5.2, fy0 - .03, PLAT + .3))
    bx(flame, 4.95, fy0 - .07, PLAT + .3, 5.45, fy0 - .03, PLAT + .8, GLOW)
    parts.append((flame, 'FLAME', 0))
    bx(g, 5.08, fy0 - .3, PLAT + .45, 5.32, fy0, PLAT + .53, IRON)
    bx(g, 5.17, fy0 - .19, PLAT + .35, 5.23, fy0 - .13, PLAT + .45, GLOW)
    # Canister turntable below the spout.
    tx, ty = 5.2, fy0 - .55
    revolve(g, (tx, ty, PLAT - .02), [(.46, 0), (.46, .12)], CONCRETE, segments=12)
    turn = Geometry('CanisterTurntable', (tx, ty, PLAT + .1))
    revolve(turn, (tx, ty, PLAT + .112), [(.44, 0), (.44, .05)], IRON, segments=12)
    for k in range(4):
        a = k * math.pi / 2
        cxx, cyy = tx + math.cos(a) * .27, ty + math.sin(a) * .27
        revolve(turn, (cxx, cyy, PLAT + .162), [(.1, 0), (.1, .42), (.065, .47), (.065, .5)], IRON, segments=10)
        band(turn, (cxx, cyy, 0), .1, PLAT + .33, .04, BRASS, segments=10)
    parts.append((turn, 'SPIN_Z', 1))
    # Off-gas stack rising from the ground at the hall's back corner.
    sx, sy = 8.35, 6.35
    bx(g, sx - .4, sy - .4, 0.03, sx + .4, sy + .4, 3.3, CONCRETE)
    stack(g, sx, sy, 3.3, 3.2, emits='steam', r=.28, taper=.8, bands=3)


def dissolvers(g, parts):
    # Concrete bund (tiles 0..4 x 4..7, top layer 1) carrying both tanks and the rack.
    bx(g, 0.0, 4.0, 0, 4.0, 7.0, PLAT - .1, CONCRETE)
    bx(g, 0.0, 4.0, PLAT - .1, 4.0, 7.03, PLAT, CONCRETE)
    for x in (.5, 1.5, 2.5, 3.5):
        bx(g, x - .05, 7.0, .12, x + .05, 7.04, PLAT - .2, CONCRETE)
    for x, y, r, h, name in ((.9, 5.5, .55, 3.0, 'AgitatorA'), (2.25, 5.65, .45, 2.7, 'AgitatorB')):
        revolve(g, (x, y, PLAT), [(r + .08, 0), (r + .08, .15)], CONCRETE, segments=12)
        revolve(g, (x, y, PLAT + .15), [(r, 0), (r, h - PLAT - .15)], FORGED if r > .5 else IRON, segments=12)
        for k in range(3):
            band(g, (x, y, 0), r, PLAT + .4 + k * (h - PLAT - .9) / 2, .07, IRON if r > .5 else PAINTED, segments=12)
        dome(g, (x, y, h), r + .02, IRON, segments=12, squash=.45)
        top = h + (r + .02) * .45
        bx(g, x - .13, y - .13, top - .05, x + .13, y + .13, top + .26, PAINTED)
        a = Geometry(name, (x, y, top + .26))
        a.cylinder((x, y, top + .33), .07, .14, IRON, 'Z', 10)
        a.box((x, y, top + .39), (.36, .05, .045), BRASS)
        parts.append((a, 'SPIN_Z', 2))
        pipe_path(g, [(x, y - r + .05, PLAT + .5), (x, HY1 - .1, PLAT + .5)], .08)
        gauge(g, x + .2, y - r - .01, PLAT + .9, face='front', r=.08)


def canister_rack(g, parts):
    x0, y0, x1, y1 = 3.0, 4.25, 3.9, 6.9   # on the bund, tile 3 x 4..7
    bx(g, x0, y0, PLAT - .02, x1, y1, PLAT + .08, IRON)
    for i in range(2):
        for j in range(6):
            revolve(g, (x0 + .25 + i * .4, y0 + .25 + j * .43, PLAT + .08), [(.13, 0), (.13, .8), (.08, .86), (.08, .92)],
                    IRON, segments=10)


def build(g, parts):
    hot_cells(g, parts)
    crane(g, parts)
    pond(g, parts)
    vitrification(g, parts)
    dissolvers(g, parts)
    canister_rack(g, parts)


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
