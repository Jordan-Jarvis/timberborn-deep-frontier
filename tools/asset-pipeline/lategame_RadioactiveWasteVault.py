"""Radioactive Waste Vault: late-game study (Iron Teeth, Deep Frontier).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the west cask yard (stored casks, jib crane, cask cart), the cutting
walls, paved forecourt, post beacons, shrubs and yard lamp.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; outputs/compaction/BRIEF.md): 9x10x12 -> 8x7x6, inside the old
footprint with the same origin (the old GRID_ORIGIN corner), door (grid x
4.5, face 0.15 behind the front edge) and native entrance. Two berm courses
of one layer each instead of three, a lower dome on a short drum, vent towers
that end 4 layers lower, and a lower plank-gabled gatehouse. The dome is the building's defining silhouette and stays.

HERO: a half-sunk bunker: two battered concrete berm courses stepping up to a
ribbed concrete dome on a buttressed drum, entered through a cast gatehouse,
flanked by two ventilation towers with slowly turning cowls.
ROOF: shallow ribbed concrete dome closed by a cast concrete crown cap (the
turning lantern ventilator is gone: roof-variety pass, no roof vents); a teal
native plank gable on the gatehouse.

Supporting masses: the gatehouse with parked lead-sheet blast-door leaves on
a steel track, the shielded cask port in the berm's left face, and warning
beacons. No workers and no power: the machinery is the vault's passive
ventilation.

Animated (names unchanged): two tower cowls (SPIN_Z) on towers rising from
the ground, two warning beacons (SPIN_Z).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import (CONCRETE, ORANGE, FORGED, PAINTED, CYAN, GLOW, revolve, band, dome, extrude_profile,
                          flat_roof, lamp, beacon, beacon_shutter)
from lategame_nuclear_parts import (bx, Facer, trefoil, riveted_panel, frustum, obox, hazard_stripes)
from industrial_facades import building_portal
from lategame_roofdeck_parts import parapet_ring
import lategame_mining_parts as M

IDENT = 'RadioactiveWasteVault'
FOOTPRINT = (8, 7)
HEIGHT = 6
HERO = ('Half-sunk bunker: two battered concrete berm courses stepping up to a ribbed concrete dome, '
        'entered through a cast gatehouse, with two turning-cowl vent towers.')
FRAME_END = 121

BERM = (0.0, 1.0, 8.0, 7.0)         # outer foot of the lowest course: tiles 0..8 x 1..7
COURSE_H = 1.0                      # one layer per course
COURSES = 2
CX, CY = 4.0, 4.0                   # dome centre (berm centre)
DRUM_R, DOME_R = 1.95, 1.85
DRUM_H = .6
DOOR_X = 4.5
GATE = (3.0, .15, 6.0)              # gatehouse x0, front (door) y .15 off the tile edge, x1
GATE_TOP = 1.84                     # gatehouse roof slab bottom; its top is layer 2
PORT_Y = (3.4, 4.6)


def berm(g):
    x0, y0, x1, y1 = BERM
    rects = []
    for k in range(COURSES):
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
    zc, f = .5, inset * .5 / COURSE_H
    for i in range(4):
        x = x0 + .9 + i * (x1 - x0 - 1.8) / 3
        if not (GATE[0] - .6 < x < GATE[2] + .6):
            bx(g, x - .24, y0 + f - .1, zc - .15, x + .24, y0 + f + .2, zc + .15, IRON)
            bx(g, x - .28, y0 + f - .14, zc + .15, x + .28, y0 + f + .2, zc + .21, IRON)
        bx(g, x - .24, y1 - f - .2, zc - .15, x + .24, y1 - f + .1, zc + .15, IRON)
        bx(g, x - .28, y1 - f - .2, zc + .15, x + .28, y1 - f + .14, zc + .21, IRON)
    for i in range(3):
        y = y0 + .9 + i * (y1 - y0 - 1.8) / 2
        if not (PORT_Y[0] - .5 < y < PORT_Y[1] + .5):
            bx(g, x0 + f - .1, y - .24, zc - .15, x0 + f + .2, y + .24, zc + .15, IRON)
            bx(g, x0 + f - .14, y - .28, zc + .15, x0 + f + .2, y + .28, zc + .21, IRON)
        bx(g, x1 - f - .2, y - .24, zc - .15, x1 - f + .1, y + .24, zc + .15, IRON)
        bx(g, x1 - f - .2, y - .28, zc + .15, x1 - f + .14, y + .28, zc + .21, IRON)


def berm_ribs(g, rect, z0, z1, inset, *, proud=.1, depth=.5, w=.26):
    """Battered buttress ribs on a course's four faces (clear of the gate and port)."""
    x0, y0, x1, y1 = rect
    zt = z1 - .1
    run = inset * (zt - z0) / (z1 - z0)
    p = proud

    def stations(a, b):
        n = max(1, round((b - a) / 1.3))
        return [a + (b - a) * (i + .5) / n for i in range(n)]
    for x in stations(x0 + .3, x1 - .3):
        if not (GATE[0] - .6 < x < GATE[2] + .6):
            extrude_profile(g, [(y0 - p, z0), (y0 + depth, z0), (y0 + depth, zt), (y0 - p + run, zt)],
                            x - w / 2, x + w / 2, CONCRETE, axis='X')
        extrude_profile(g, [(y1 - depth, z0), (y1 + p, z0), (y1 + p - run, zt), (y1 - depth, zt)],
                        x - w / 2, x + w / 2, CONCRETE, axis='X')
    for y in stations(y0 + .3, y1 - .3):
        if not (PORT_Y[0] - .5 < y < PORT_Y[1] + .5):
            extrude_profile(g, [(x0 - p, z0), (x0 + depth, z0), (x0 + depth, zt), (x0 - p + run, zt)],
                            y - w / 2, y + w / 2, CONCRETE, axis='Y')
        extrude_profile(g, [(x1 - depth, z0), (x1 + p, z0), (x1 + p - run, zt), (x1 - depth, zt)],
                        y - w / 2, y + w / 2, CONCRETE, axis='Y')


def dome_block(g, parts, top):
    # Buttressed drum with vent grilles.
    revolve(g, (CX, CY, top), [(DRUM_R + .1, 0), (DRUM_R + .1, .14), (DRUM_R, .15), (DRUM_R, DRUM_H)], CONCRETE,
            segments=18)
    g.ring((CX, CY, top + DRUM_H - .07), DRUM_R + .03, .05, .09, IRON, 'Z', 18)
    for k in range(12):
        a = k * math.pi / 6
        obox(g, (CX + math.cos(a) * (DRUM_R + .05), CY + math.sin(a) * (DRUM_R + .05), top + .33), a,
             .17, .2, .46, CONCRETE)
        b = a + math.pi / 12
        obox(g, (CX + math.cos(b) * (DRUM_R + .01), CY + math.sin(b) * (DRUM_R + .01), top + .33), b,
             .04, .4, .22, IRON)
    base = top + DRUM_H
    squash = .5
    rings = 6
    dome(g, (CX, CY, base), DOME_R, CONCRETE, segments=18, rings=rings, squash=squash)
    # Meridian ribs on dome vertices (never parallel to a facet).
    for k in range(12):
        a = k * 2 * math.pi / 12
        pts = []
        for i in range(rings):
            t = i / rings * math.pi / 2
            r = DOME_R * math.cos(t) + .02
            pts.append((CX + math.cos(a) * r, CY + math.sin(a) * r, base + DOME_R * squash * math.sin(t) + .02))
        for p, q in zip(pts, pts[1:-1]):
            g.beam(p, q, .09, mat=IRON)
    # Cast concrete crown cap closing the dome (no lantern ventilator).
    crown = base + DOME_R * squash
    lz = crown - .1
    revolve(g, (CX, CY, lz), [(.6, 0), (.6, .2), (.5, .21), (.5, .26), (.3, .3), (0, .31)], CONCRETE, segments=12)


def gatehouse(g, parts):
    gx0, gy0, gx1 = GATE
    gy1 = BERM[1]
    gtop = GATE_TOP
    dw, dh = 1.0, 1.0
    left, right = DOOR_X - dw / 2, DOOR_X + dw / 2
    bx(g, gx0, gy0, 0, left, gy1, gtop, CONCRETE)
    bx(g, right, gy0, 0, gx1, gy1, gtop, CONCRETE)
    bx(g, left, gy0, dh, right, gy1, gtop, CONCRETE)
    bx(g, left, gy0 + .25, 0, right, gy1, dh, CONCRETE)
    bx(g, left + .006, gy0 + .24, .006, right - .006, gy0 + .25, dh - .006, IRON)
    bx(g, gx0, gy1, .03, gx1, gy1 + .8, gtop, CONCRETE)
    M.plank_gable(g, gx0, gx1, gy0, gy1 + .8, gtop, gtop + .7, ridge_axis='Y', overhang=.12, seed=31)
    building_portal(g, DOOR_X, gy0 - .12, 0)
    g.doorways.append({'id': 'Main', 'position': [DOOR_X, gy0, 0], 'outward': [0, -1]})
    # Parked lead-sheet blast-door leaves on a steel track.
    f = Facer(gx0, gy0, 0, 'front')
    for u0 in (.05, gx1 - gx0 - .55):
        riveted_panel(g, f, u0, u0 + .5, .06, 1.55, 0, .07, FORGED)
        f.box(g, u0 + .25, .8, .08, .05, 1.3, .02, IRON)
    bx(g, gx0 - .08, gy0 - .17, 1.6, gx1 + .08, gy0 - .07, 1.72, IRON)
    trefoil(g, 3.5, gy0, 1.25, face='front', r=.17)
    lamp(g, DOOR_X + .75, gy0, 1.3, face='front')


def vent_tower(g, parts, x, y, z0, top, name):
    h = .4
    bx(g, x - h, y - h, z0, x + h, y + h, top, CONCRETE)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bx(g, x + sx * h - .05, y + sy * h - .05, z0 + .15, x + sx * h + .05, y + sy * h + .05, top - .1, IRON)
    bx(g, x - h - .04, y - h - .04, top - 1.4, x + h + .04, y + h + .04, top - 1.2, FORGED)
    for k in range(4):
        z = top - .9 + k * .2
        for face in ('front', 'back', 'left', 'right'):
            f = Facer(x + {'left': -h, 'right': h}.get(face, 0), y + {'front': -h, 'back': h}.get(face, 0), 0, face)
            f.box(g, 0, z, .04, 2 * h - .12, .07, .08, IRON)
    bx(g, x - h - .07, y - h - .07, top, x + h + .07, y + h + .07, top + .1, CONCRETE)
    revolve(g, (x, y, top + .1), [(.15, 0), (.15, .24)], IRON, segments=12)
    c = Geometry(name, (x, y, top + .34))
    revolve(c, (x, y, top + .34), [(.3, 0), (.3, .4)], PAINTED, segments=16)
    for k in range(8):
        a = k * math.pi / 4
        obox(c, (x + math.cos(a) * .32, y + math.sin(a) * .32, top + .54), a + .5, .17, .03, .36, IRON)
    revolve(c, (x, y, top + .74), [(.35, 0), (.35, .04), (.07, .3), (0, .32)], ROOF, segments=16)
    c.box((x + .4, y, top + .53), (.12, .26, .28), IRON)
    parts.append((c, 'SPIN_Z', 1))
    return top + .1


def cask_port(g, parts):
    # Shielded port block set into the berm's left face with a forged plug door.
    px0, px1 = BERM[0] + .3, 1.3
    py0, py1 = PORT_Y
    bx(g, px0, py0, .03, px1, py1, 1.75, CONCRETE)
    bx(g, px0 - .05, py0 - .05, 1.67, px1, py1 + .05, 1.8, CONCRETE)
    f = Facer(px0, (py0 + py1) / 2, 0, 'left')
    f.box(g, 0, .8, .05, .95, 1.4, .1, IRON)
    riveted_panel(g, f, -.4, .4, .2, 1.4, .1, .16, FORGED)
    K.wheel(g, f.p(0, .8, .22), .15, 'X')
    hazard_stripes(g, f, -.45, .45, 1.55, .0, .03, height=.1, n=6)


def build(g, parts):
    rects = berm(g)
    top = COURSES * COURSE_H
    dome_block(g, parts, top)
    gatehouse(g, parts)
    tx0, ty0, tx1, ty1 = rects[-1]
    for x, ht, name in ((tx0 + .5, 4.4, 'CowlWest'), (tx1 - .5, 4.9, 'CowlEast')):
        cap = vent_tower(g, parts, x, ty1 - .5, top, ht, name)
        px, py, pz = beacon(g, x - .34, ty1 - .84, cap)
        parts.append((beacon_shutter(px, py, pz, name + 'Beacon'), 'SPIN_Z', 2))
    cask_port(g, parts)
