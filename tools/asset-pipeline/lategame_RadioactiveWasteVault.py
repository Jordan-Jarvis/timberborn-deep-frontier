"""Radioactive Waste Vault: late-game study (Iron Teeth, Deep Frontier).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the west cask yard (stored casks, jib crane, cask cart), the cutting
walls, paved forecourt, post beacons, shrubs and yard lamp.

HERO: a monumental half-sunk bunker: three battered concrete berm courses
stepping up to a ribbed concrete dome on a buttressed drum, entered through a
gatehouse set in a cutting between sloping retaining walls, flanked by two
ventilation towers with slowly turning cowls.
ROOF: shallow ribbed concrete dome with a turning lantern ventilator; teal
plank gable on the gatehouse; plank lean-to over the cask yard.

Supporting masses: the gatehouse with parked lead-sheet blast-door leaves on
a steel track, a cask yard with stored finned casks on sleepers, a slewing jib
crane carrying a cask, a rail cart shuttling a cask to the shielded cask port
in the berm, and warning beacons. No workers and no power: the machinery is
the vault's passive ventilation and its cask handling.

Animated: two tower cowls and the dome lantern (SPIN_Z), slewing jib crane
with its cask (CUSTOM_SLEW), cask cart (SLIDE_X), four warning beacons
(SPIN_Z).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import (CONCRETE, ORANGE, FORGED, PAINTED, CYAN, GLOW, revolve, band, dome, extrude_profile,
                          steel_rail, ladder, lamp, beacon, beacon_shutter, bolt_row, redic_prop)
from lategame_nuclear_parts import (bx, Facer, trefoil, gauge, riveted_panel, pipe_path, frustum, obox, cask,
                                    plank_gable, plank_slope, slope_quad, hazard_stripes)
from industrial_facades import building_portal
import native_building_assets as native

IDENT = 'RadioactiveWasteVault'
# Footprint ends at the walls: berm foot (x = 4, back and east edges) and
# the gatehouse front (y = 2.15). The west cask yard and the forecourt were
# removed. GRID_ORIGIN is the footprint's (0, 0) corner in the artwork
# coordinates used below.
FOOTPRINT = (9, 10)
GRID_ORIGIN = (4, 2)
HEIGHT = 12
HERO = ('Half-sunk monumental bunker: three battered concrete berm courses stepping up to a ribbed '
        'concrete dome, entered through a gatehouse in a cutting, with two turning-cowl vent towers.')
FRAME_END = 121

BERM = (4.0, 3.0, 13.0, 12.0)       # outer foot of the lowest course: tiles 4..13 x 3..12
COURSE_H = 1.2
CX, CY = 8.5, 7.5                   # dome centre (berm centre)
DRUM_R, DOME_R = 2.65, 2.5
DOOR_X = 8.5
GATE = (7.0, 2.15, 10.0)            # gatehouse x0, front (door) y .15 off the tile edge, x1


def berm(g):
    x0, y0, x1, y1 = BERM
    # Three battered courses, each set back on a ledge from the one below.
    rects = []
    for k in range(3):
        inset = .35
        tx0, ty0, tx1, ty1 = x0 + inset, y0 + inset, x1 - inset, y1 - inset
        frustum(g, tx0, ty0, tx1, ty1, k * COURSE_H, (k + 1) * COURSE_H, inset, CONCRETE, bottom=(k == 0))
        rects.append((tx0, ty0, tx1, ty1))
        if k > 0:
            berm_ribs(g, (x0, y0, x1, y1), k * COURSE_H, (k + 1) * COURSE_H, inset)
        else:
            berm_vents(g, (x0, y0, x1, y1), inset)
        x0, y0, x1, y1 = tx0 + .15, ty0 + .15, tx1 - .15, ty1 - .15
    return rects


def berm_vents(g, rect, inset):
    """Iron vent hoods projecting from the lowest battered course."""
    x0, y0, x1, y1 = rect
    zc, f = .6, inset * .6 / COURSE_H
    for i in range(5):
        x = x0 + .9 + i * (x1 - x0 - 1.8) / 4
        if not (GATE[0] - .9 < x < GATE[2] + .9):
            bx(g, x - .28, y0 + f - .1, zc - .17, x + .28, y0 + f + .2, zc + .17, IRON)
            bx(g, x - .32, y0 + f - .14, zc + .17, x + .32, y0 + f + .2, zc + .23, IRON)
        bx(g, x - .28, y1 - f - .2, zc - .17, x + .28, y1 - f + .1, zc + .17, IRON)
        bx(g, x - .32, y1 - f - .2, zc + .17, x + .32, y1 - f + .14, zc + .23, IRON)
    for i in range(5):
        y = y0 + .9 + i * (y1 - y0 - 1.8) / 4
        if not (5.4 < y < 7.7):
            bx(g, x0 + f - .1, y - .28, zc - .17, x0 + f + .2, y + .28, zc + .17, IRON)
            bx(g, x0 + f - .14, y - .32, zc + .17, x0 + f + .2, y + .32, zc + .23, IRON)
        bx(g, x1 - f - .2, y - .28, zc - .17, x1 - f + .1, y + .28, zc + .17, IRON)
        bx(g, x1 - f - .2, y - .32, zc + .17, x1 - f + .14, y + .32, zc + .23, IRON)


def berm_ribs(g, rect, z0, z1, inset, *, proud=.1, depth=.6, w=.3):
    """Battered buttress ribs on a course's four faces (clear of the gate and port)."""
    x0, y0, x1, y1 = rect
    zt = z1 - .1
    run = inset * (zt - z0) / (z1 - z0)
    p = proud

    def stations(a, b):
        n = max(1, round((b - a) / 1.3))
        return [a + (b - a) * (i + .5) / n for i in range(n)]
    for x in stations(x0 + .3, x1 - .3):
        if not (GATE[0] - .9 < x < GATE[2] + .9):
            extrude_profile(g, [(y0 - p, z0), (y0 + depth, z0), (y0 + depth, zt), (y0 - p + run, zt)],
                            x - w / 2, x + w / 2, CONCRETE, axis='X')
        extrude_profile(g, [(y1 - depth, z0), (y1 + p, z0), (y1 + p - run, zt), (y1 - depth, zt)],
                        x - w / 2, x + w / 2, CONCRETE, axis='X')
    for y in stations(y0 + .3, y1 - .3):
        if not (5.4 < y < 7.7):
            extrude_profile(g, [(x0 - p, z0), (x0 + depth, z0), (x0 + depth, zt), (x0 - p + run, zt)],
                            y - w / 2, y + w / 2, CONCRETE, axis='Y')
        extrude_profile(g, [(x1 - depth, z0), (x1 + p, z0), (x1 + p - run, zt), (x1 - depth, zt)],
                        y - w / 2, y + w / 2, CONCRETE, axis='Y')


def dome_block(g, parts, top):
    # Buttressed drum with vent grilles.
    revolve(g, (CX, CY, top), [(DRUM_R + .12, 0), (DRUM_R + .12, .16), (DRUM_R, .17), (DRUM_R, 1.0)], CONCRETE,
            segments=18)
    g.ring((CX, CY, top + .92), DRUM_R + .03, .06, .1, IRON, 'Z', 18)
    for k in range(12):
        a = k * math.pi / 6
        obox(g, (CX + math.cos(a) * (DRUM_R + .06), CY + math.sin(a) * (DRUM_R + .06), top + .55), a,
             .2, .24, .8, CONCRETE)
        b = a + math.pi / 12
        obox(g, (CX + math.cos(b) * (DRUM_R + .01), CY + math.sin(b) * (DRUM_R + .01), top + .55), b,
             .04, .5, .3, IRON)
    base = top + 1.0
    squash = .55
    dome(g, (CX, CY, base), DOME_R, CONCRETE, segments=18, rings=7, squash=squash)
    # Meridian ribs on dome vertices (never parallel to a facet).
    rings = 7
    for k in range(12):
        a = k * 2 * math.pi / 12
        pts = []
        for i in range(rings):
            t = i / rings * math.pi / 2
            r = DOME_R * math.cos(t) + .02
            pts.append((CX + math.cos(a) * r, CY + math.sin(a) * r, base + DOME_R * squash * math.sin(t) + .02))
        for p, q in zip(pts, pts[1:-1]):
            g.beam(p, q, .1, mat=IRON)
    # Lantern ventilator on the crown.
    crown = base + DOME_R * squash
    lz = crown - .12
    revolve(g, (CX, CY, lz), [(.75, 0), (.75, .25), (.62, .26), (.62, .32)], CONCRETE, segments=12)
    revolve(g, (CX, CY, lz + .32), [(.42, 0), (.42, .55)], IRON, segments=16)
    vent = Geometry('LanternVent', (CX, CY, lz + .32))
    for k in range(8):
        a = k * math.pi / 4
        obox(vent, (CX + math.cos(a) * .5, CY + math.sin(a) * .5, lz + .6), a + .6, .26, .04, .5, PAINTED)
    vent.ring((CX, CY, lz + .87), .6, .1, .06, IRON, 'Z', 16)
    vent.ring((CX, CY, lz + .33), .6, .1, .04, IRON, 'Z', 16)
    revolve(vent, (CX, CY, lz + .87), [(.66, 0), (.66, .05), (.1, .42), (0, .45)], ROOF, segments=16)
    parts.append((vent, 'SPIN_Z', .5))


def gatehouse(g, parts, rects):
    gx0, gy0, gx1 = GATE
    gy1 = BERM[1]
    gtop = 3.4
    # Cast gatehouse with a native door opening.
    dw, dh = 1.0, 1.0
    left, right = DOOR_X - dw / 2, DOOR_X + dw / 2
    bx(g, gx0, gy0, 0, left, gy1, gtop, CONCRETE)
    bx(g, right, gy0, 0, gx1, gy1, gtop, CONCRETE)
    bx(g, left, gy0, dh, right, gy1, gtop, CONCRETE)
    bx(g, left, gy0 + .25, 0, right, gy1, dh, CONCRETE)
    bx(g, left + .006, gy0 + .24, .006, right - .006, gy0 + .25, dh - .006, IRON)
    bx(g, gx0, gy1, .03, gx1, gy1 + 1.0, gtop, CONCRETE)
    bx(g, gx0 - .05, gy0 - .05, gtop - .1, gx1 + .05, gy1 + 1.0, gtop + .02, CONCRETE)
    building_portal(g, DOOR_X, gy0 - .12, 0)
    g.doorways.append({'id': 'Main', 'position': [DOOR_X, gy0, 0], 'outward': [0, -1]})
    # Parked lead-sheet blast-door leaves on a steel track.
    f = Facer(gx0, gy0, 0, 'front')
    for u0 in (0, gx1 - gx0 - .6):
        riveted_panel(g, f, u0, u0 + .6, .06, 2.3, 0, .09, FORGED)
        f.box(g, u0 + .3, 1.2, .1, .06, 1.9, .02, IRON)
    bx(g, gx0 - .12, gy0 - .2, 2.4, gx1 + .12, gy0 - .1, 2.55, IRON)
    for x in (gx0 + .1, gx1 - .1):
        g.beam((x, gy0, 2.2), (x, gy0 - .15, 2.42), .05, mat=IRON)
    trefoil(g, DOOR_X, gy0, 1.75, face='front', r=.3)
    for x in (DOOR_X - .9, DOOR_X + .9):
        lamp(g, x, gy0, 2.85, face='front')
    # Teal plank gable roof, ridge across the front.
    plank_gable(g, gx0 + .05, gy0 + .05, gx1 - .05, gy1 + .8, gtop + .02, gtop + .85, overhang=.2)
    # (The cutting's wing walls, paved forecourt and post beacons in front
    # of the gatehouse were removed: the footprint ends at the gatehouse front.)

def vent_tower(g, parts, x, y, z0, top, name):
    h = .45
    bx(g, x - h, y - h, z0, x + h, y + h, top, CONCRETE)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bx(g, x + sx * h - .05, y + sy * h - .05, z0 + .2, x + sx * h + .05, y + sy * h + .05, top - .1, IRON)
    # Forged band and louvred head.
    bx(g, x - h - .04, y - h - .04, top - 2.2, x + h + .04, y + h + .04, top - 1.9, FORGED)
    for k in range(5):
        z = top - 1.3 + k * .2
        for face in ('front', 'back', 'left', 'right'):
            f = Facer(x + {'left': -h, 'right': h}.get(face, 0), y + {'front': -h, 'back': h}.get(face, 0), 0, face)
            f.box(g, 0, z, .04, 2 * h - .12, .07, .08, IRON)
    bx(g, x - h - .08, y - h - .08, top, x + h + .08, y + h + .08, top + .12, CONCRETE)
    revolve(g, (x, y, top + .12), [(.18, 0), (.18, .3)], IRON, segments=12)
    # Turning cowl: hooded drum on the spindle.
    c = Geometry(name, (x, y, top + .42))
    revolve(c, (x, y, top + .42), [(.36, 0), (.36, .5)], PAINTED, segments=16)
    for k in range(8):
        a = k * math.pi / 4
        obox(c, (x + math.cos(a) * .38, y + math.sin(a) * .38, top + .67), a + .5, .2, .03, .46, IRON)
    revolve(c, (x, y, top + .92), [(.42, 0), (.42, .05), (.08, .36), (0, .38)], ROOF, segments=16)
    c.box((x + .48, y, top + .65), (.14, .3, .34), IRON)
    parts.append((c, 'SPIN_Z', 1))
    return top + .12


def cask_port(g, parts):
    # Shielded port block on the berm's left face with a forged plug door.
    px0, px1, py0, py1 = BERM[0] + .3, 5.4, 5.75, 7.35   # set into the berm foot
    bx(g, px0, py0, .03, px1, py1, 2.7, CONCRETE)
    bx(g, px0 - .05, py0 - .05, 2.62, px1, py1 + .05, 2.76, CONCRETE)
    f = Facer(px0, (py0 + py1) / 2, 0, 'left')
    f.box(g, 0, 1.15, .06, 1.25, 1.85, .12, IRON)
    riveted_panel(g, f, -.55, .55, .3, 2.0, .12, .2, FORGED)
    K.wheel(g, f.p(0, 1.15, .27), .18, 'X')
    hazard_stripes(g, f, -.6, .6, 2.2, .0, .03, height=.12, n=8)


def build(g, parts):
    rects = berm(g)
    top = 3 * COURSE_H
    dome_block(g, parts, top)
    gatehouse(g, parts, rects)
    tx0, ty0, tx1, ty1 = rects[-1]
    for x, ht, name in ((tx0 + .55, 8.6, 'CowlWest'), (tx1 - .55, 9.6, 'CowlEast')):
        cap = vent_tower(g, parts, x, ty1 - .55, top, ht, name)
        px, py, pz = beacon(g, x - .4, ty1 - .95, cap)
        parts.append((beacon_shutter(px, py, pz, name + 'Beacon'), 'SPIN_Z', 2))
    cask_port(g, parts)


def animate(obj, kind, value, frame_end):
    """CUSTOM_SLEW: jib slews from the cask racks (-Y) round to the cart rail (+Y)."""
    if kind != 'CUSTOM_SLEW':
        raise ValueError(kind)
    span = frame_end - 1
    obj.rotation_mode = 'XYZ'
    for frame, t in ((1, -1), (1 + span * .3, 1), (1 + span * .5, 1), (1 + span * .8, -1), (frame_end, -1)):
        obj.rotation_euler[2] = value * t
        obj.keyframe_insert(data_path='rotation_euler', index=2, frame=frame)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'BEZIER'
