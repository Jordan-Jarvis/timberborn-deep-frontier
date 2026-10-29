"""DeepDrill: late-game deep-ore drilling rig (Iron Teeth, Deep Frontier).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the gate post lamp.

HERO: a 16-layer tapered steel lattice derrick standing on a raised concrete
substructure, timber windwall boards at its base, Lambda-braced V-door, crown
block with gin pole and beacon. Roofs: teal plank gables on the doghouse and
the power house; concrete flat roof on the pump house.

Parts: concrete substructure with steel I-beam floor and cellar BOP stack;
drill floor with rotary table, drawworks, pipe setback and monkey board; V-door
pipe ramp and catwalk; pipe rack with racked drill pipe; concrete pump house with
the timber doghouse on its roof; triplex mud pump; banded mud tanks; power house
with stacks and radiator fan.

Animated (7): travelling block and hook (hoist), its drill lines (stretch),
kelly (descends while turning), rotary table, drawworks drum, mud-pump pistons
and bull wheel, radiator fan, crown beacon.
"""
import math

from mathutils import Quaternion

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK
import lategame_mining_parts as P
from lategame_mining_parts import bx

IDENT = 'DeepDrill'
FOOTPRINT = (11, 9)
HEIGHT = 16
HERO = 'Sixteen-layer tapered steel lattice derrick on a concrete substructure, crowned by a crown block and beacon'
FRAME_END = 121

FLOOR = 3.0                   # drill floor layer
ON = FLOOR + .012             # top of the floor grating bars
WELL = (5.2, 4.5)             # well centre
BASE = (3.3, 7.1, 2.6, 6.4)   # derrick leg footprint at the floor (x0, x1, y0, y1)
TOP = (4.65, 5.75, 3.95, 5.05)
ZT = 15.0                     # crown deck layer
STROKE = 2.6                  # hoist travel per loop
BLOCK_TOP = 9.25              # travelling block top at its highest


def frame_at(z):
    t = (z - FLOOR) / (ZT - FLOOR)
    return tuple(BASE[i] + (TOP[i] - BASE[i]) * t for i in range(4))


# ------------------------------------------------------------------ derrick

def derrick(g):
    corners = lambda z: (lambda f: [(f[0], f[2]), (f[1], f[2]), (f[1], f[3]), (f[0], f[3])])(frame_at(z))
    # Leg shoes and legs.
    for (x, y), (xt, yt) in zip(corners(FLOOR), corners(ZT)):
        bx(g, x - .17, x + .17, y - .17, y + .17, ON, ON + .16, IRON)
        bx(g, x - .12, x + .12, y - .12, y + .12, ON + .16, ON + .2, PAINTED)
        g.beam((x, y, ON + .1), (xt, yt, ZT - .04), .18, mat=IRON)
    levels = [ON + .2, 4.5, 6.0, 7.5, 9.0, 10.5, 12.0, 13.5, ZT - .1]
    # Girts: front/back at the level, left/right raised 30 mm so corners never coincide.
    for k, z in enumerate(levels[1:-1], 1):
        x0, x1, y0, y1 = frame_at(z)
        for y, face in ((y0, 'front'), (y1, 'back')):
            if face == 'front' and z < 7:
                continue   # V-door opening
            bx(g, x0 + .07, x1 - .07, y - .05, y + .05, z - .05, z + .05, IRON)
        for x in (x0, x1):
            bx(g, x - .05, x + .05, y0 + .07, y1 - .07, z - .02, z + .08, IRON)
    # Diagonals, one per bay, alternating, standing off the legs (alternate
    # stand-off per bay so consecutive braces never share a plane at a joint).
    faces = {
        'front': (lambda f: ((f[0], f[2]), (f[1], f[2])), (0, -1)),
        'right': (lambda f: ((f[1], f[2]), (f[1], f[3])), (1, 0)),
        'back': (lambda f: ((f[1], f[3]), (f[0], f[3])), (0, 1)),
        'left': (lambda f: ((f[0], f[3]), (f[0], f[2])), (-1, 0)),
    }
    for fi, (face, (ends, n)) in enumerate(faces.items()):
        for k in range(len(levels) - 1):
            za, zb = levels[k], levels[k + 1]
            if face == 'front' and k < 3:
                continue
            off = .115 if k % 2 == 0 else .13
            (pa, qa), (pb, qb) = ends(frame_at(za)), ends(frame_at(zb))
            if (k + fi) % 2:
                a, b = (pa[0] + n[0] * off, pa[1] + n[1] * off, za + .06), (qb[0] + n[0] * off, qb[1] + n[1] * off, zb - .06)
            else:
                a, b = (qa[0] + n[0] * off, qa[1] + n[1] * off, za + .06), (pb[0] + n[0] * off, pb[1] + n[1] * off, zb - .06)
            g.beam(a, b, .06, .075, IRON)
    # Lambda brace framing the V-door, meeting at a bolted gusset.
    apex_z = 7.5
    f = frame_at(apex_z)
    apex = (WELL[0], f[2])
    for (x, y), off in (((BASE[0], BASE[2]), .115), ((BASE[1], BASE[2]), .13)):
        g.beam((x, y - off, ON + .3), (apex[0], apex[1] - off, apex_z), .06, .09, IRON)
    bx(g, apex[0] - .2, apex[0] + .2, apex[1] - .19, apex[1] - .06, apex_z - .2, apex_z + .12, PAINTED)
    P.bolt_ring(g, (apex[0], apex[1] - .19, apex_z - .04), .1, 4, 'Y', -.008, .018)
    # Timber windwall boards inside the legs on the left, right and back faces.
    boards = 10
    zs = [ON + .2 + (6.0 - ON - .2) * i / boards for i in range(boards + 1)]
    for face in ('left', 'right', 'back'):
        for za, zb in zip(zs, zs[1:]):
            fa, fb = frame_at(za), frame_at(zb)
            if face == 'left':
                pts = [(fa[0] + .05, fa[3] - .06, za), (fa[0] + .05, fa[2] + .06, za),
                       (fb[0] + .05, fb[2] + .06, zb), (fb[0] + .05, fb[3] - .06, zb)]
                normal = (-1, 0, (TOP[0] - BASE[0]) / (ZT - FLOOR))
            elif face == 'right':
                pts = [(fa[1] - .05, fa[2] + .06, za), (fa[1] - .05, fa[3] - .06, za),
                       (fb[1] - .05, fb[3] - .06, zb), (fb[1] - .05, fb[2] + .06, zb)]
                normal = (1, 0, (BASE[1] - TOP[1]) / (ZT - FLOOR))
            else:
                pts = [(fa[1] - .06, fa[3] - .05, za), (fa[0] + .06, fa[3] - .05, za),
                       (fb[0] + .06, fb[3] - .05, zb), (fb[1] - .06, fb[3] - .05, zb)]
                normal = (0, 1, (BASE[3] - TOP[3]) / (ZT - FLOOR))
            P.slab_quad(g, pts, normal, .05, PLANK)
    # Windwall cap rail (timber) above the boards.
    # Monkey board with fingerboard, bracketed to the front legs.
    mz = 10
    P.deck(g, 4.4, 6.0, 3.45, 4.15, mz, rails=('front', 'left', 'right'), bars=False)
    for i in range(6):
        x = 5.42 + i * .1
        bx(g, x - .02, x + .02, 3.56, 4.1, mz, mz + .05, IRON)
    fz = frame_at(9.2)
    for x, xl in ((4.45, fz[0]), (5.95, fz[1])):
        g.beam((x, 3.5, mz - .09), (xl + (.07 if xl < 5 else -.07), fz[2] + .05, 9.2), .06, mat=IRON)
    # Pipe setback: racked stands leaning into the fingerboard.
    bx(g, 5.95, 6.85, 2.8, 3.55, ON, ON + .08, WOOD)
    stands = [(6.1, 2.95), (6.3, 2.95), (6.5, 2.95), (6.7, 2.95), (6.2, 3.2), (6.4, 3.2), (6.6, 3.2), (6.4, 3.42)]
    for i, (x, y) in enumerate(stands):
        tx = 5.5 + (i % 4) * .1 + (.05 if i >= 4 else 0)
        ty = 3.62 + (i // 4) * .2
        P.tube(g, (x, y, ON + .08), (tx, ty, 10.55 + (i % 3) * .05), .05, IRON, 8)
    # Crown deck, crown block and gin pole with beacon.
    P.deck(g, 4.4, 6.0, 3.7, 5.3, ZT, rails=('front', 'back', 'left', 'right'))
    zc = ZT + .012
    bx(g, 4.7, 5.7, 4.15, 4.85, zc, zc + .1, IRON)
    for x in (4.75, 5.6):
        bx(g, x, x + .1, 4.2, 4.8, zc + .1, zc + .66, PAINTED)
    g.cylinder((5.2, 4.5, zc + .4), .06, 1.04, IRON, 'X', 12)
    for x in (4.98, 5.13, 5.28, 5.43):
        g.ring((x, 4.5, zc + .4), .26, .05, .09, IRON, 'X', 12)
        g.ring((x, 4.5, zc + .4), .2, .03, .06, BRASS, 'X', 16)
    for y in (3.82, 5.18):
        g.beam((4.62, y, zc), (4.62, 4.5, 15.52), .07, mat=IRON)
    bx(g, 4.54, 4.7, 4.38, 4.62, 15.45, 15.58, PAINTED)
    K.beacon(g, 4.62, 4.5, 15.58)
    # Inclined ladder up the left face to the monkey board.
    ladder_face(g, 5.95, ON, 9.9)


def ladder_face(g, y, z0, z1, w=.32):
    """Ladder following the inclined left face of the derrick, standing off it."""
    def xl(z):
        return frame_at(z)[0] - .16
    for s in (-1, 1):
        g.beam((xl(z0), y + s * w / 2, z0), (xl(z1), y + s * w / 2, z1), .045, mat=IRON)
    z = z0 + .2
    while z < z1 - .1:
        g.beam((xl(z), y - w / 2 + .02, z), (xl(z), y + w / 2 - .02, z), .03, mat=IRON)
        z += .3
    for z in (z0 + 2.0, z0 + 4.5):
        g.beam((xl(z), y, z), (frame_at(z)[0] - .04, y, z), .05, mat=IRON)


def drill_lines():
    """Reeved drill lines from the crown to the travelling block; they stretch."""
    top = ZT + .2
    lines = Geometry('DrillLines', (WELL[0], WELL[1], top))
    for i, x in enumerate((4.98, 5.13, 5.28, 5.43)):
        y = 4.46 if i % 2 else 4.54
        lines.box((x, y, (top + BLOCK_TOP - .05) / 2), (.03, .03, top - BLOCK_TOP + .05), IRON)
    return lines


def travelling_block():
    blk = Geometry('TravellingBlock', (WELL[0], WELL[1], 8.0))
    x, y = WELL
    bx(blk, x - .28, x + .28, y - .18, y + .18, 8.45, BLOCK_TOP - .12, PAINTED)
    bx(blk, x - .24, x + .24, y - .15, y + .15, BLOCK_TOP - .12, BLOCK_TOP, PAINTED)
    for sx in (-1, 1):
        bx(blk, x + sx * .28 - (.0 if sx > 0 else .025), x + sx * .28 + (.025 if sx > 0 else 0),
           y - .12, y + .12, 8.6, 9.0, BRASS)
    for yy, face in ((y - .18, 'Y'),):
        P.bolt_ring(blk, (x, yy, 8.85), .16, 6, 'Y', -.008, .02)
    bx(blk, x - .08, x + .08, y - .06, y + .06, 8.3, 8.45, IRON)
    # Hook.
    K.revolve(blk, (x, y, 7.95), [(.07, 0), (.12, .08), (.12, .3), (.08, .4)], IRON, segments=12)
    blk.beam((x, y, 7.98), (x + .16, y, 7.86), .07, mat=IRON)
    blk.beam((x + .16, y, 7.86), (x + .2, y, 8.04), .06, mat=IRON)
    # Swivel and bail.
    K.revolve(blk, (x, y, 7.25), [(.1, 0), (.17, .1), (.2, .3), (.16, .5), (.1, .6)], PAINTED, segments=14)
    for sx in (-1, 1):
        blk.beam((x + sx * .2, y, 7.55), (x + sx * .06, y, 8.0), .04, mat=IRON)
    P.tube(blk, (x, y - .1, 7.7), (x, y - .32, 7.95), .045, BRASS, 8)
    return blk


def kelly():
    k = Geometry('Kelly', (WELL[0], WELL[1], 5.0))
    x, y = WELL
    bx(k, x - .09, x + .09, y - .09, y + .09, ON + .2, 7.2, IRON)
    bx(k, x - .12, x + .12, y - .12, y + .12, 6.95, 7.12, BRASS)
    k.cylinder((x, y, 7.19), .11, .12, PAINTED, 'Z', 12)
    return k


def rotary(g, parts):
    x, y = WELL
    bx(g, x - .65, x + .65, y - .65, y + .65, ON, ON + .2, IRON)
    bx(g, x + .65, x + .95, y - .25, y + .25, ON, ON + .14, PAINTED)
    zc = ON + .26
    t = Geometry('RotaryTable', (x, y, zc))
    t.cylinder((x, y, zc), .52, .12, PAINTED, 'Z', 16)
    t.ring((x, y, zc), .55, .05, .07, BRASS, 'Z', 16)
    bx(t, x - .23, x + .23, y - .23, y + .23, zc + .06, zc + .2, IRON)
    for sx in (-1, 1):
        for sy in (-1, 1):
            K.stud(t, (x + sx * .15, y + sy * .15, zc + .209), 'Z', .025)
    bx(t, x + .42, x + .56, y - .05, y + .05, zc + .06, zc + .12, BRASS)
    parts.append((t, 'SPIN_Z', 3))


# ------------------------------------------------------------------ substructure

def substructure(g):
    # Concrete piers, three a side, and a back wall.
    for y0, y1 in ((2.4, 3.2), (5.0, 5.8), (7.6, 8.4)):
        for x0, x1 in ((3.1, 3.9), (6.5, 7.3)):
            bx(g, x0 - .04, x1 + .04, y0 - .04, y1 + .04, 0, .3, CONCRETE)
            bx(g, x0, x1, y0, y1, .3, 2.48, CONCRETE)
            bx(g, x0 - .05, x1 + .05, y0 - .05, y1 + .05, 2.48, 2.6, CONCRETE)
    bx(g, 3.94, 6.46, 7.86, 8.4, 0, .3, CONCRETE)
    bx(g, 3.86, 6.54, 7.9, 8.36, .3, 2.48, CONCRETE)
    for x in (4.6, 5.8):
        P.window(g, x, 8.36, 1.5, 'back', .7, 'factory')
    # Steel I-beam floor frame and drill floor deck.
    for c in (3.5, 6.9):
        P.ibeam(g, 'Y', 2.4, 8.4, c, 2.6, 2.92, .6)
    for c in (2.8, 3.7, 5.3, 6.9, 8.0):
        P.ibeam(g, 'X', 3.8, 6.6, c, 2.62, 2.92, .3)
    P.deck(g, 3.1, 7.3, 2.4, 8.4, FLOOR, gaps={'front': [(4.8, 5.6)], 'left': [(3.0, 3.8)]})
    # Cellar collar, dark well and BOP stack.
    x, y = WELL
    bx(g, 4.3, 6.1, 3.6, 4.0, 0, .4, CONCRETE)
    bx(g, 4.3, 6.1, 5.0, 5.4, 0, .4, CONCRETE)
    bx(g, 4.3, 4.7, 4.0, 5.0, 0, .4, CONCRETE)
    bx(g, 5.7, 6.1, 4.0, 5.0, 0, .4, CONCRETE)
    bx(g, 4.7, 5.7, 4.0, 5.0, 0, .08, IRON)
    g.cylinder((x, y, .38), .2, .6, IRON, 'Z', 12)
    g.cylinder((x, y, .71), .3, .06, BRASS, 'Z', 12)
    K.revolve(g, (x, y, .74), [(.42, 0), (.47, .2), (.4, .42), (.22, .52)], PAINTED, segments=12)
    g.cylinder((x, y, 1.29), .3, .06, BRASS, 'Z', 12)
    for z0 in (1.32, 1.76):
        bx(g, x - .5, x + .5, y - .25, y + .25, z0, z0 + .38, PAINTED)
        for sx in (-1, 1):
            g.cylinder((x + sx * .65, y, z0 + .19), .15, .3, IRON, 'X', 12)
            K.valve_wheel(g, x + sx * .84, y, z0 + .19, face='left', r=.13)
    g.cylinder((x, y, 1.73), .28, .06, IRON, 'Z', 12)
    g.cylinder((x, y, 2.17), .3, .06, BRASS, 'Z', 12)
    g.cylinder((x, y, 2.56), .18, .72, IRON, 'Z', 12)
    # Choke line to a valve block with gauge.
    K.pipe_run(g, [(x + .2, y + .2, 1.5), (x + .2, 5.7, 1.5), (6.3, 5.7, 1.5)], .07)
    bx(g, 6.2, 6.45, 5.5, 5.9, 1.2, 1.85, PAINTED)
    P.gauge(g, 6.32, 5.5, 1.62, 'front', .09)
    K.valve_wheel(g, 6.32, 5.42, 1.35, face='front', r=.12)


def ramp(g):
    """Catwalk and V-door ramp for pipe handling."""
    for px in (4.75, 5.65):
        P.pier(g, px, .55, 0, .87, .34)
    P.deck(g, 4.5, 5.9, .1, 1.0, 1, rails=('front', 'left', 'right'))
    # Trough ramp from the catwalk up to the drill floor edge.
    y0, z0, y1, z1 = 1.0, 1.0, 2.4, FLOOR
    rise = (z1 - z0) / (y1 - y0)
    n = (0, -rise, 1)
    P.slab_quad(g, [(4.85, y0, z0), (5.55, y0, z0), (5.55, y1, z1), (4.85, y1, z1)], n, .06, IRON)
    for xo, s in ((4.79, -1), (5.61, 1)):
        P.slab_quad(g, [(xo, y0, z0 - .06), (xo, y1, z1 - .06), (xo, y1, z1 + .2), (xo, y0, z0 + .2)],
                    (s, 0, 0), .06, PAINTED)
    for x in (4.95, 5.45):
        g.beam((x, 1.75, .04), (x, 1.75, z0 + (1.75 - y0) * rise - .08), .1, mat=IRON)
    bx(g, 4.8, 5.6, 1.6, 1.9, 0, .12, CONCRETE)
    # A joint of drill pipe on the ramp.
    P.tube(g, (5.2, .3, 1.075), (5.2, 1.02, 1.075), .06, IRON, 8)


def pipe_rack(g):
    for y in (.55, 1.9, 3.25):
        for x in (7.95, 10.45):
            P.pier(g, x, y, 0, .45, .3, cap=False)
        P.ibeam(g, 'X', 7.75, 10.65, y, .45, .66, .22)
        for x in (7.82, 10.58):
            bx(g, x - .04, x + .04, y - .06, y + .06, .66, 1.25, IRON)
    r = .085
    rows = [(12, 0.0), (11, .5), (9, 1.0)]
    for row, (count, shift) in enumerate(rows):
        z = .66 + r + row * r * 1.62
        for i in range(count):
            x = 8.0 + (i + shift) * .205
            # 32 joints in a stack: eight-sided pipe, six-sided thread protectors.
            g.cylinder((x, 1.9, z), r, 3.3, IRON, 'Y', 8)
            for yy in (.3 + row * .17, 3.5 - row * .17):
                g.cylinder((x, yy, z), .1, .12, PAINTED, 'Y', 6)


# ------------------------------------------------------------------ houses

def pump_house(g):
    # Plinth course (core + .05) on tiles 0..3 x 0..4; door face stays .18.
    P.hall(g, .05, 2.95, .3, 3.95, 2.84, plinth=1.5, doors=[1.5], pitch=1.3,
           windows={'front': [(.95, 2.2, 'grand', .6), (2.25, 2.2, 'grand', .6)],
                    'left': [(.9, 2.2, 'grand', .6), (2.1, 2.2, 'grand', .6), (3.3, 2.2, 'grand', .6)],
                    'right': [(.9, 2.2, 'grand', .6)], 'back': [(1.6, 2.2, 'grand', .6)]})
    for y in (1.2, 2.6):
        P.window(g, 0.0, y, .85, 'left', .7, 'factory')
    K.lamp(g, .78, .25, 1.15, face='front')
    K.lamp(g, 2.22, .25, 1.15, face='front')
    P.flat_roof(g, .05, 2.95, .3, 3.95, 2.84, parapet=0)
    zr = FLOOR
    for a, b, ss, se, dz in (((.03, .28), (2.97, .28), False, False, 0), ((.03, .28), (.03, 3.97), True, True, -.011),
                             ((.03, 3.97), (2.97, 3.97), False, False, 0), ((2.97, .28), (2.97, 2.95), True, False, -.011),
                             ((2.97, 3.85), (2.97, 3.97), False, True, -.011)):
        P.rail(g, a, b, zr, skip_start=ss, skip_end=se, dz=dz)
    # Bridge plate to the drill floor.
    bx(g, 2.97, 3.18, 3.0, 3.8, 2.96, 3.03, IRON)
    # Doghouse: timber-framed cabin on the pump house roof.
    P.hall(g, .55, 2.65, 1.75, 3.7, 5.0, z0=zr, plinth=.22, doors=[1.5], record_doors=False,
           windows={'left': [(3.21, 4.1)], 'right': [(3.21, 4.1)], 'back': [(1.075, 4.1)]},
           pitch=1.05)
    P.plank_gable(g, .55, 2.65, 1.75, 3.7, 5.0, 5.85, ridge_axis='X', seed=11)
    K.lamp(g, 2.15, 1.75, 4.3, face='front')
    # Stove pipe through the roof.
    P.tube(g, (1.0, 3.2, 5.2), (1.0, 3.2, 6.35), .07, IRON, 10)
    g.cylinder((1.0, 3.2, 6.4), .11, .1, IRON, 'Z', 10)


def mud_pump(g, parts):
    bx(g, 0.0, 3.0, 4.0, 6.0, 0, .3, CONCRETE)   # pump bed on whole tiles
    # Fluid end with three valve covers.
    bx(g, .5, 1.1, 4.4, 5.45, .3, 1.12, IRON)
    for y in (4.6, 4.92, 5.24):
        g.cylinder((.47, y, .78), .11, .08, BRASS, 'X', 12)
        K.stud(g, (.425, y, .78), 'X', .03)
    # Liner frame between fluid and power ends.
    for y in (4.45, 5.4):
        bx(g, 1.1, 1.52, y - .04, y + .04, .45, .55, IRON)
        bx(g, 1.1, 1.52, y - .04, y + .04, 1.0, 1.08, IRON)
    # Power end crankcase with a rounded cover.
    bx(g, 1.52, 2.6, 4.45, 5.4, .3, 1.05, PAINTED)
    g.cylinder((2.06, 4.925, 1.05), .48, .9, PAINTED, 'Y', 18)
    rods = Geometry('MudPumpPistons', (1.3, 4.92, .78))
    for y in (4.6, 4.92, 5.24):
        rods.cylinder((1.3, y, .78), .045, .7, IRON, 'X', 10)
        bx(rods, 1.24, 1.38, y - .07, y + .07, .71, .85, BRASS)
    parts.append((rods, 'PISTON_X', .14))
    wheel = P.spoked_wheel('MudPumpBullWheel', (2.06, 4.28, .98), .5, 'Y', rim_t=.08, rim_w=.1,
                           spokes=6, groove=False, hub_r=.12)
    parts.append((wheel, 'SPIN_Y', 2))
    # Suction from the mud tanks and discharge up to the standpipe.
    K.pipe_run(g, [(.8, 5.4, .95), (.8, 7.02, .95)], .08)
    K.pipe_run(g, [(.8, 4.9, 1.0), (.8, 4.9, 2.2), (2.9, 4.9, 2.2), (2.9, 5.4, 2.2), (3.3, 5.4, 2.2)], .08)
    P.gauge(g, .5, 5.2, 1.0, 'left', .08)


def mud_tanks(g):
    for x in (.9, 2.3):
        K.tank(g, x, 7.5, 0, .6, 3.1, mat=PAINTED, bands=4, roof='dome')
    K.ladder(g, .9, 6.86, 0, 3.35, face='front', width=.3, cage=True)
    P.gauge(g, 2.3, 6.88, 1.2, 'front', .09)
    # Flow line from the cellar back to the tanks; standpipe up the derrick.
    K.pipe_run(g, [(5.2, 4.6, 2.3), (5.2, 6.2, 2.3), (2.3, 6.2, 2.3), (2.3, 7.02, 2.3)], .07)
    P.tube(g, (3.62, 6.12, ON + .05), (4.15, 5.6, 8.6), .07, IRON, 10)
    P.tube(g, (4.15, 5.6, 8.6), (4.5, 5.25, 8.85), .07, IRON, 10)
    for z, (cx, cy) in ((4.0, (3.71, 6.03)), (6.5, (3.9, 5.84))):
        g.ring((cx, cy, z), .11, .05, .06, BRASS, 'Z', 12)


def power_house(g, parts):
    w = 'grand'
    # Plinth course (core + .05) on tiles 8..10 x 4..8, clear of the
    # substructure piers on the left and the radiator inside the footprint.
    # The core's left face stays on x = 8 so the side door's notch fits.
    P.hall(g, 8.0, 9.95, 4.05, 7.95, 4.6, plinth=.6, doors=[8.5], record_doors=False, rails=[2.75],
           windows={'front': [(9.5, 1.85, w, .7), (9.5, 3.6, w, .7), (8.5, 3.6, w, .7)],
                    'right': [(4.5, 1.85), (7.5, 1.85), (4.5, 3.6), (6.0, 3.6), (7.5, 3.6)],
                    'back': [(8.49, 1.85), (8.49, 3.6)],
                    'left': [(5.5, 1.85), (6.5, 1.85), (4.5, 3.6), (5.5, 3.6), (6.5, 3.6), (7.5, 3.6)]},
           post_skip={'right': [6.0]}, pitch=1.0,
           lamps=[('front', 9.12, 1.4)])
    P.plank_gable(g, 8.0, 9.95, 4.05, 7.95, 4.6, 6.05, ridge_axis='Y', seed=21)
    for x in (8.45, 9.55):
        K.stack(g, x, 8.45, 0, 7.4, emits='smoke', r=.2, bands=4)
        K.pipe_run(g, [(x, 7.95, 3.15), (x, 8.33, 3.15)], .08, flanges=False)
    # Radiator and fan on the right wall.
    bx(g, 9.95, 10.3, 5.3, 6.7, .8, 2.3, PAINTED)
    for z in (.95, 2.15):
        bx(g, 10.3, 10.35, 5.35, 6.65, z - .04, z + .04, IRON)
    g.ring((10.36, 6.0, 1.55), .58, .07, .12, IRON, 'X', 16)
    parts.append((P.rotor('RadiatorFan', (10.45, 6.0, 1.55), .5, 'X', 6), 'SPIN_X', 4))
    P.gauge(g, 9.5, 4.05, 1.15, 'front', .08)


def drawworks(g, parts):
    for x0 in (3.75, 6.45):
        bx(g, x0, x0 + .2, 6.85, 8.15, ON, ON + 1.25, PAINTED)
        bx(g, x0 - .03, x0 + .23, 7.3, 7.7, ON + 1.25, ON + 1.4, BRASS)
    bx(g, 3.95, 6.45, 6.95, 8.05, ON, ON + .14, IRON)
    c = (5.2, 7.5, ON + .8)
    d = Geometry('DrawworksDrum', c)
    d.cylinder(c, .42, 2.3, IRON, 'X', 16)
    for x in (4.045, 6.355):
        d.cylinder((x, c[1], c[2]), .62, .09, PAINTED, 'X', 16)
    for x in (4.6, 5.0, 5.4, 5.8):
        d.ring((x, c[1], c[2]), .45, .04, .14, IRON, 'X', 16)
    d.cylinder(c, .1, 2.8, IRON, 'X', 12)
    for x in (4.0, 6.4):
        # (The flange bolt circles were sub-pixel; the brass index lug shows the turn.)
        bx(d, x - .035, x + .035, c[1] - .05, c[1] + .05, c[2] + .62, c[2] + .7, BRASS)
    parts.append((d, 'SPIN_X', 2))
    # Drive motor and chain case.
    bx(g, 6.68, 7.22, 7.1, 7.9, ON, ON + .2, IRON)
    g.cylinder((6.95, 7.5, ON + .5), .3, .5, PAINTED, 'X', 18)
    # Fast line up to the crown.
    g.beam((5.1, 7.5, c[2] + .42), (5.05, 4.62, ZT + .35), .035, mat=IRON)
    # Dead-line anchor.
    bx(g, 4.0, 4.3, 6.5, 6.8, ON, ON + .3, PAINTED)
    g.beam((4.15, 6.65, ON + .3), (5.4, 4.4, ZT + .35), .035, mat=IRON)


def build(g, parts):
    substructure(g)
    derrick(g)
    rotary(g, parts)
    ramp(g)
    pipe_rack(g)
    pump_house(g)
    mud_pump(g, parts)
    mud_tanks(g)
    power_house(g, parts)
    drawworks(g, parts)
    parts.append((travelling_block(), 'CUSTOM_HOIST', STROKE))
    parts.append((drill_lines(), 'CUSTOM_LINES', STROKE))
    parts.append((kelly(), 'CUSTOM_KELLY', STROKE))
    parts.append((K.beacon_shutter(4.62, 4.5, 15.72, 'CrownBeaconShutter'), 'SPIN_Z', 2))


def animate(obj, kind, value, frame_end):
    """Hoist cycle: slow descent while drilling, quick pull back to the top."""
    span = frame_end - 1
    keys = ((1, 0.0), (1 + span * .78, 1.0), (frame_end, 0.0))
    base_z = obj.location.z
    if kind == 'CUSTOM_LINES':
        length = ZT + .2 - BLOCK_TOP + .05
        for frame, t in keys:
            obj.scale = (1, 1, (length + value * t) / length)
            obj.keyframe_insert(data_path='scale', frame=frame)
    elif kind in ('CUSTOM_HOIST', 'CUSTOM_KELLY'):
        for frame, t in keys:
            obj.location.z = base_z - value * t
            obj.keyframe_insert(data_path='location', index=2, frame=frame)
        if kind == 'CUSTOM_KELLY':
            obj.rotation_mode = 'QUATERNION'
            steps = 48
            for k in range(steps + 1):
                obj.rotation_quaternion = Quaternion((0, 0, 1), 3 * 2 * math.pi * k / steps)
                obj.keyframe_insert(data_path='rotation_quaternion', frame=1 + span * k / steps)
    else:
        raise ValueError('Unknown custom animation ' + kind)
    obj.location.z = base_z
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
