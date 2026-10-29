"""Shared parts for the Deep Frontier space program (late-game studies).

Used by lategame_LaunchPad, lategame_RocketAssemblyHangar, lategame_MissionControl
and lategame_CryogenicLiquefactionPlant. Artwork coordinates: X across, Y back,
Z up; one unit is one tile / one height layer. Only native material slots.

Contact rule used throughout: a part resting on a surface starts LAYER_GAP-ish
below it (its bottom is buried), so no two faces share a plane where they meet.
"""
import math

from mathutils import Quaternion, Vector

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
from lategame_kit import (CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, CYAN, GLOW,
                          WINDOW, LAYER_GAP, TRIM_PROUD, revolve, band, dome, oriented_polygon,
                          extrude_profile, hollow_revolve)

BURY = .02   # how far resting parts sink into their support


# ---------------------------------------------------------------- basics

def bx(g, x0, y0, z0, x1, y1, z1, mat):
    """Axis-aligned box from bounds."""
    if x1 <= x0 or y1 <= y0 or z1 <= z0:
        raise ValueError(f'Empty box {x0},{y0},{z0} .. {x1},{y1},{z1}')
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), mat)


def door_block(g, x0, y0, x1, y1, z0, z1, door_x, mat=CONCRETE, door_id=None):
    """Solid block with a native one-tile portal on its front (y0) face.

    The block is split around a 1x1 notch whose back face is set 0.2 deep;
    the portal's orange insert sits on the y0 plane and closes the notch.
    """
    lo, hi = door_x - .5, door_x + .5
    if lo < x0 - 1e-6 or hi > x1 + 1e-6 or z1 < z0 + 1:
        raise ValueError('Door notch must fit inside the block face')
    if lo > x0 + 1e-6:
        bx(g, x0, y0, z0, lo, y1, z1, mat)
    if x1 > hi + 1e-6:
        bx(g, hi, y0, z0, x1, y1, z1, mat)
    if z1 > z0 + 1 + 1e-6:
        bx(g, lo, y0, z0 + 1, hi, y1, z1, mat)
    bx(g, lo, y0 + .2, z0, hi, y1, z0 + 1, mat)
    portal(g, door_x, y0, z0, door_id)


def portal(g, door_x, wall_y, z0, door_id=None):
    from industrial_facades import building_portal
    building_portal(g, door_x, wall_y - .12, z0)
    g.doorways.append({'id': door_id or 'Door' + str(len(g.doorways)), 'position': [door_x, wall_y, z0],
                       'outward': [0, -1], 'width': 1.0, 'internalConnection': 'BuildingInterior'})


def pilasters(g, axis, plane, start, end, z0, z1, outward, *, pitch=1.0, skip=(), w=.10, mat=CONCRETE):
    """Proud vertical casting strips on a concrete face (axis 'X': face at y=plane)."""
    count = max(1, round((end - start) / pitch))
    for i in range(1, count):
        u = start + (end - start) * i / count
        if any(a - w <= u <= b + w for a, b in skip):
            continue
        if axis == 'X':
            bx(g, u - w / 2, plane + (-.03 if outward < 0 else -.01), z0, u + w / 2,
               plane + (.03 if outward > 0 else .01), z1, mat)
        else:
            bx(g, plane + (-.03 if outward < 0 else -.01), u - w / 2, z0,
               plane + (.03 if outward > 0 else .01), u + w / 2, z1, mat)


def coping_ring(g, x0, y0, x1, y1, top, *, w=.28, proud=.04, h=.16, mat=CONCRETE):
    """Proud cap band around the top edge of a concrete mass (top rises above `top`)."""
    zb, zt = top - h + .04, top + .04
    bx(g, x0 - proud, y0 - proud, zb, x1 + proud, y0 - proud + w, zt, mat)
    bx(g, x0 - proud, y1 + proud - w, zb, x1 + proud, y1 + proud, zt, mat)
    bx(g, x0 - proud, y0 - proud + w, zb, x0 - proud + w, y1 + proud - w, zt, mat)
    bx(g, x1 + proud - w, y0 - proud + w, zb, x1 + proud, y1 + proud - w, zt, mat)


# ---------------------------------------------------------------- steelwork
# Local replacements for two kit helpers: lategame_kit.steel_rail puts its
# .055 top rail only 2.5 mm proud of its .05 posts, and lategame_kit.
# lattice_tower lays consecutive diagonals in one plane where they meet.

def rail(g, a, b, z, *, height=.62, pitch=.6, mat=IRON, skip_start=False, skip_end=False):
    """Handrail: .05 posts, .08 top rail (15 mm proud), .032 mid rail (buried in posts)."""
    a, b = Vector(a), Vector(b)
    count = max(1, math.ceil((b - a).length / pitch))
    for i in range(count + 1):
        if (i == 0 and skip_start) or (i == count and skip_end):
            continue
        p = a + (b - a) * i / count
        g.box((p.x, p.y, z + (height - .02) / 2), (.05, .05, height - .02), mat)
    g.beam((a.x, a.y, z + height), (b.x, b.y, z + height), .08, mat=mat)
    g.beam((a.x, a.y, z + height * .5), (b.x, b.y, z + height * .5), .032, mat=mat)


def lattice(g, x0, y0, x1, y1, bottom, top, *, bays=None, w=.12, mat=IRON, feet=True):
    """Four-legged lattice tower. Diagonals of alternate bays sit in planes
    35 mm apart, so where they meet at a leg they cross instead of overlapping."""
    if bays is None:
        bays = max(1, round((top - bottom) / 1.2))
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for x, y in corners:
        g.box((x, y, (bottom + top) / 2), (w, w, top - bottom), mat)
        if feet:
            g.box((x, y, bottom + .07), (w + .14, w + .14, .14), CONCRETE)
    for k in range(bays + 1):
        z = bottom + (top - bottom) * k / bays
        if k == 0:
            z += .2
        if k == bays:
            z -= w * .4
        for (ax, ay), (bx_, by) in zip(corners, corners[1:] + corners[:1]):
            inset = w / 2 + .01
            if ax == bx_:
                g.box((ax, (ay + by) / 2, z), (w * .7, abs(by - ay) - 2 * inset, w * .7), mat)
            else:
                g.box(((ax + bx_) / 2, ay, z), (abs(bx_ - ax) - 2 * inset, w * .7, w * .7), mat)
    for k in range(bays):
        za = bottom + (top - bottom) * k / bays + (.2 if k == 0 else 0)
        zb = bottom + (top - bottom) * (k + 1) / bays - (w * .4 if k == bays - 1 else 0)
        for idx, ((ax, ay), (bx_, by)) in enumerate(zip(corners, corners[1:] + corners[:1])):
            nx = 0 if ax != bx_ else (-1 if ax == x0 else 1)
            ny = 0 if ay != by else (-1 if ay == y0 else 1)
            off = w * .55 + (.035 if k % 2 else 0)
            p = (ax + nx * off, ay + ny * off)
            q = (bx_ + nx * off, by + ny * off)
            if (k + idx) % 2:
                g.beam((p[0], p[1], za), (q[0], q[1], zb), w * .45, mat=mat)
            else:
                g.beam((q[0], q[1], za), (p[0], p[1], zb), w * .45, mat=mat)


# ---------------------------------------------------------------- free-oriented parts

def tube(g, a, b, r, mat, *, segments=8, r2=None):
    """Capped round tube between two arbitrary points (outward winding)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    if d.length < 1e-6:
        raise ValueError('Zero-length tube')
    q = d.to_track_quat('Z', 'Y')
    r2 = r if r2 is None else r2
    verts = []
    for p, rr in ((a, r), (b, r2)):
        for i in range(segments):
            t = i * 2 * math.pi / segments
            verts.append(tuple(p + q @ Vector((math.cos(t) * rr, math.sin(t) * rr, 0))))
    n = segments
    faces = [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    faces.append(tuple(reversed(range(n))))
    faces.append(tuple(range(n, 2 * n)))
    g.add(verts, faces, mat)


def arc_bar(g, center, r_in, r_out, half_w, azimuth, t0, t1, mat, *, steps=10):
    """Curved bar following a sphere meridian (polar angle t0..t1 from +Z)."""
    c = Vector(center)
    e = Vector((-math.sin(azimuth), math.cos(azimuth), 0))
    def d(t):
        return Vector((math.sin(t) * math.cos(azimuth), math.sin(t) * math.sin(azimuth), math.cos(t)))
    rings = []
    for k in range(steps + 1):
        t = t0 + (t1 - t0) * k / steps
        rings.append([c + d(t) * r_in - e * half_w, c + d(t) * r_in + e * half_w,
                      c + d(t) * r_out + e * half_w, c + d(t) * r_out - e * half_w])
    for k in range(steps):
        tm = t0 + (t1 - t0) * (k + .5) / steps
        mid = c + d(tm) * (r_in + r_out) / 2
        for i in range(4):
            j = (i + 1) % 4
            quad = [tuple(rings[k][i]), tuple(rings[k][j]), tuple(rings[k + 1][j]), tuple(rings[k + 1][i])]
            centre = sum((Vector(p) for p in quad), Vector()) / 4
            oriented_polygon(g, quad, tuple(centre - mid), mat)
    for k, sgn in ((0, -1), (steps, 1)):
        t = t0 if k == 0 else t1
        tangent = Vector((math.cos(t) * math.cos(azimuth), math.cos(t) * math.sin(azimuth), -math.sin(t)))
        oriented_polygon(g, [tuple(p) for p in rings[k]], tuple(tangent * sgn * (1 if t1 > t0 else -1)), mat)


def place(dst, build_fn, rotation, offset):
    """Author parts with build_fn(tmp) around the origin, then rotate (a mathutils
    Quaternion/Matrix in artwork axes) and translate them into `dst`."""
    tmp = Geometry('tmp')
    build_fn(tmp)
    pts = [rotation @ Vector((-v[0], -v[1], v[2])) + Vector(offset) for v in tmp.vertices]
    groups = {}
    for face, mat in zip(tmp.faces, tmp.materials):
        groups.setdefault(mat, []).append(face)
    for mat, faces in groups.items():
        used = sorted({i for f in faces for i in f})
        remap = {i: k for k, i in enumerate(used)}
        dst.add([tuple(pts[i]) for i in used], [tuple(remap[i] for i in f) for f in faces], mat)


# ---------------------------------------------------------------- services

def gauge(g, x, y, z, face='front', r=.11):
    """Pressure gauge: iron case, white dial, tiny cyan needle. Eight sides;
    the brass bezel ring (112 triangles) was a one-pixel line at game zoom."""
    n = {'front': (0, -1), 'back': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[face]
    axis = 'Y' if n[0] == 0 else 'X'
    def at(d):
        return (x + n[0] * d, y + n[1] * d, z)
    g.cylinder(at(.03), r, .06, IRON, axis, 8)
    g.cylinder(at(.065), r - .02, .01, CONCRETE, axis, 8)
    tip = (x + n[0] * .075 + (r * .55 if axis == 'Y' else 0), y + n[1] * .075 + (r * .55 if axis == 'X' else 0), z + r * .4)
    g.beam(at(.075), tip, .014, .008, CYAN)


def ball(g, center, r, mat, *, segments=12, rings=6):
    cx, cy, cz = center
    prof = [(0, -r)] + [(r * math.sin(math.pi * k / rings), -r * math.cos(math.pi * k / rings))
                        for k in range(1, rings)] + [(0, r)]
    revolve(g, (cx, cy, cz), prof, mat, segments=segments)


def pipe(g, points, r=.07, mat=IRON, *, flange=BRASS, flanges=True, elbow=None):
    """Orthogonal capped pipe with ball elbows and flange rings near joints.

    Segment ends stop inside the elbow balls, so no caps are exposed except
    at the two run ends (which should be buried in a wall or tank)."""
    elbow = mat if elbow is None else elbow
    sides = 8 if r <= .1 else 12   # small pipes 8 sides, mains 12 (smooth-shaded)
    for a, b in zip(points, points[1:]):
        d = [b[i] - a[i] for i in range(3)]
        axis_i = max(range(3), key=lambda i: abs(d[i]))
        if sum(1 for v in d if abs(v) > 1e-6) != 1:
            raise ValueError(f'pipe segments must be axis-aligned: {a} -> {b}')
        length = abs(d[axis_i])
        mid = tuple((a[i] + b[i]) / 2 for i in range(3))
        g.cylinder(mid, r, length, mat, 'XYZ'[axis_i], sides)
        if flanges and length > .7:
            for f in (.25 / length, 1 - .25 / length):
                p = tuple(a[i] + d[i] * f for i in range(3))
                # Solid flange disc (the bore inside it is never seen).
                g.cylinder(p, r + .035, .06, flange, 'XYZ'[axis_i], sides)
    for p in points[1:-1]:
        ball(g, p, r * 1.22, elbow, segments=sides, rings=4)


def pipe_support(g, x, y, z_pipe, r, *, axis='X', ground=0.0):
    """Concrete sleeper with a steel saddle under a horizontal pipe."""
    if axis == 'X':
        bx(g, x - .12, y - .2, ground - BURY, x + .12, y + .2, z_pipe - r - .03, CONCRETE)
        bx(g, x - .04, y - r - .04, z_pipe - r - .05, x + .04, y + r + .04, z_pipe - r * .2, IRON)
    else:
        bx(g, x - .2, y - .12, ground - BURY, x + .2, y + .12, z_pipe - r - .03, CONCRETE)
        bx(g, x - r - .04, y - .04, z_pipe - r - .05, x + r + .04, y + .04, z_pipe - r * .2, IRON)


def h_tank(g, x0, x1, y, zc, r, *, mat=CONCRETE, band_mat=IRON, bands=3, saddles=2, ground=0.0,
           axis='X', segments=12):
    """Horizontal bullet tank (axis X or Y) with dished heads, bands and concrete saddles."""
    length = x1 - x0
    mid = (x0 + x1) / 2
    def P(u, v=None):
        return (u, y, zc) if axis == 'X' else (y, u, zc)
    g.cylinder(P(mid), r, length, mat, axis, segments)
    # Dished heads: shallow cones closing each end.
    for end, s in ((x0, -1), (x1, 1)):
        g.cylinder(P(end + s * .05), r * .92, .12, mat, axis, segments)
        g.cylinder(P(end + s * .15), r * .62, .1, mat, axis, segments)
        g.cylinder(P(end + s * .23), r * .22, .06, band_mat, axis, 10)
    for k in range(bands):
        u = x0 + length * (k + .5) / bands
        # Solid band (its core lies inside the shell): 44 triangles at 12
        # sides, where a hollow ring was 96.
        g.cylinder(P(u), r + .03, .08, band_mat, axis, segments)
    for k in range(saddles):
        u = x0 + length * (k + .5) / saddles
        if axis == 'X':
            bx(g, u - .14, y - r * .8, ground - BURY, u + .14, y + r * .8, zc - r * .55, CONCRETE)
            bx(g, u - .06, y - r * .85, zc - r * .7, u + .06, y + r * .85, zc - r * .35, IRON)
        else:
            bx(g, y - r * .8, u - .14, ground - BURY, y + r * .8, u + .14, zc - r * .55, CONCRETE)
            bx(g, y - r * .85, u - .06, zc - r * .7, y + r * .85, u + .06, zc - r * .35, IRON)


def sphere_tank(g, x, y, z_center, r, *, mat=CONCRETE, legs=8, ground=0.0, equator=IRON, segments=12):
    """Horton sphere on a ring of steel legs with an equator girder."""
    ball(g, (x, y, z_center), r, mat, segments=segments, rings=8)
    band(g, (x, y, 0), r, z_center, .14, equator, segments=segments, proud=.03)
    for i in range(legs):
        a = (i + .5) * 2 * math.pi / legs
        lx, ly = x + math.cos(a) * r * .98, y + math.sin(a) * r * .98
        bx(g, lx - .07, ly - .07, ground, lx + .07, ly + .07, z_center, IRON)
        bx(g, lx - .14, ly - .14, ground - BURY, lx + .14, ly + .14, ground + .18, CONCRETE)
    # Cross bracing between neighbouring legs.
    for i in range(legs):
        a0 = (i + .5) * 2 * math.pi / legs
        a1 = (i + 1.5) * 2 * math.pi / legs
        p0 = (x + math.cos(a0) * r * 1.0, y + math.sin(a0) * r * 1.0)
        p1 = (x + math.cos(a1) * r * 1.0, y + math.sin(a1) * r * 1.0)
        zt = z_center - r * .45
        if i % 2 == 0:
            g.beam((p0[0], p0[1], ground + .2), (p1[0], p1[1], zt), .04, mat=IRON)
        else:
            g.beam((p1[0], p1[1], ground + .2), (p0[0], p0[1], zt), .04, mat=IRON)


def grating_ring(g, x0, y0, x1, y1, z, hole, *, rails=('front', 'back', 'left', 'right'), rail_gap=None):
    """Steel grating platform at whole layer z with a rectangular hole (hx0, hy0, hx1, hy1).

    `rail_gap` = (edge, a, b): leave that stretch of rail open (arm access)."""
    steel_rail = rail
    hx0, hy0, hx1, hy1 = hole
    t = .08
    bx(g, x0, y0, z - t, x1, hy0, z, IRON)
    bx(g, x0, hy1, z - t, x1, y1, z, IRON)
    bx(g, x0, hy0, z - t, hx0, hy1, z, IRON)
    bx(g, hx1, hy0, z - t, x1, hy1, z, IRON)
    # Proud grating bars along X (front/back strips) and Y (side strips),
    # every 20 cm.
    for (a0, b0, a1, b1, along) in ((x0, y0, x1, hy0, 'X'), (x0, hy1, x1, y1, 'X'),
                                    (x0, hy0, hx0, hy1, 'Y'), (hx1, hy0, x1, hy1, 'Y')):
        if along == 'X':
            n = max(1, int((b1 - b0) / .2))
            for k in range(n):
                yy = b0 + (k + .5) * (b1 - b0) / n
                bx(g, a0 + .03, yy - .017, z - .004, a1 - .03, yy + .017, z + .014, IRON)   # 34 mm: faces clear of tower diagonals
        else:
            n = max(1, int((a1 - a0) / .2))
            for k in range(n):
                xx = a0 + (k + .5) * (a1 - a0) / n
                bx(g, xx - .017, b0 + .03, z - .004, xx + .017, b1 - .03, z + .014, IRON)
    ins = .04
    lines = {'front': ((x0 + ins, y0 + ins), (x1 - ins, y0 + ins)),
             'back': ((x0 + ins, y1 - ins), (x1 - ins, y1 - ins)),
             'left': ((x0 + ins, y0 + ins + .06), (x0 + ins, y1 - ins - .06)),
             'right': ((x1 - ins, y0 + ins + .06), (x1 - ins, y1 - ins - .06))}
    for name in rails:
        a, b = lines[name]
        if rail_gap and rail_gap[0] == name:
            ga, gb = rail_gap[1], rail_gap[2]
            horiz = name in ('front', 'back')
            u0, u1 = (a[0], b[0]) if horiz else (a[1], b[1])
            for s0, s1 in ((u0, ga), (gb, u1)):
                if s1 - s0 > .2:
                    pa = (s0, a[1]) if horiz else (a[0], s0)
                    pb = (s1, a[1]) if horiz else (a[0], s1)
                    steel_rail(g, pa, pb, z + .014)
            continue
        steel_rail(g, a, b, z + .014)


# ---------------------------------------------------------------- timber

def timber_hut(g, x0, y0, x1, y1, z0, eave, ridge, *, ridge_axis='X', infill=PLANK, windows=(),
               door=None, posts=WOOD):
    """Small beaver-built timber hut: corner posts, plank walls, teal gable roof."""
    from lategame_kit import gable_roof
    t = .08
    # Plank wall faces sit inside the post line; posts stand proud at corners.
    bx(g, x0 + .04, y0 + .04, z0, x1 - .04, y1 - .04, eave, infill)
    for x in (x0, x1):
        for y in (y0, y1):
            bx(g, x - .07 + (x == x0) * .06, y - .07 + (y == y0) * .06, z0 - BURY,
               x + .07 - (x == x1) * .06, y + .07 - (y == y1) * .06, eave - .03, posts)
    # Sill and plate beams, proud of the planks.
    for z in (z0 + .06, eave - .1):
        bx(g, x0 + .1, y0 + .01, z - .05, x1 - .1, y0 + .05, z + .05, WOOD)
        bx(g, x0 + .1, y1 - .05, z - .05, x1 - .1, y1 - .01, z + .05, WOOD)
        bx(g, x0 + .01, y0 + .1, z - .05, x0 + .05, y1 - .1, z + .05, WOOD)
        bx(g, x1 - .05, y0 + .1, z - .05, x1 - .01, y1 - .1, z + .05, WOOD)
    gable_roof(g, x0 + .04, y0 + .04, x1 - .04, y1 - .04, eave, ridge, ridge_axis=ridge_axis, overhang=.16)
    from architectural_windows import window
    for (wx, wy, wz, face, scale, style) in windows:
        window(g, wx, wy, wz, scale, face, style)


# ---------------------------------------------------------------- rocket

def rocket(g, cx, cy, z0, *, r1=.85, scale=1.0, stages=2, escape_tower=True, fins=True, segments=16,
           primary=PAINTED, secondary=IRON):
    """Riveted beaver-built rocket: banded teal and forged-steel stages, fins,
    a porthole capsule and an escape tower. Returns a dict of key heights.

    Built bottom up from closed revolve sections; each upper section rests
    on the cap of the one below (its own bottom cap omitted)."""
    s = scale
    c = (cx, cy, z0)
    z = z0
    heights = {}
    def section(r_lo, r_hi, h, mat, cap_bottom=False):
        nonlocal z
        revolve(g, (cx, cy, z), [(r_lo, 0), (r_hi, h)], mat, segments=segments, cap_bottom=cap_bottom)
        z += h
    # Engine bells under the thrust skirt.
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        ex, ey = cx + math.cos(a) * r1 * .42 * s, cy + math.sin(a) * r1 * .42 * s
        revolve(g, (ex, ey, z0 - .62 * s), [(.24 * s, 0), (.16 * s, .3 * s), (.1 * s, .5 * s), (.12 * s, .64 * s)],
                IRON, segments=12)
        g.ring((ex, ey, z0 - .6 * s), .245 * s, .03, .05, BRASS, 'Z', 12)
    revolve(g, (cx, cy, z0 - .06), [(r1 * .7 * s, 0), (r1 * .7 * s, .08)], IRON, segments=segments)
    # Stage 1: skirt, then a long banded tank.
    section(r1 * 1.06 * s, r1 * 1.0 * s, .45 * s, IRON, cap_bottom=True)
    stage1 = [(secondary, 1.2), (primary, 1.3), (secondary, .5), (primary, 1.3), (secondary, .9)]
    zb1 = z
    for mat, h in stage1:
        section(r1 * s, r1 * s, h * s, mat)
    heights['stage1_top'] = z
    for k, zz in enumerate([zb1 + .02 * s] + [zb1 + sum(h for _, h in stage1[:i + 1]) * s for i in range(len(stage1) - 1)]):
        if k:
            band(g, (cx, cy, 0), r1 * s, zz, .1 * s, BRASS, segments=segments, proud=.03)
    # Interstage: orange-banded taper.
    r2 = r1 * .8 * s
    section(r1 * s, r1 * s, .1 * s, IRON)
    section(r1 * s, r2, .45 * s, secondary)
    band(g, (cx, cy, 0), r2, z + .1 * s, .14 * s, ORANGE, segments=segments, proud=.035)
    heights['interstage'] = z
    if stages >= 2:
        zb2 = z
        stage2 = [(primary, 1.0), (secondary, .4), (primary, 1.2)]
        for mat, h in stage2:
            section(r2, r2, h * s, mat)
        acc = zb2
        for _, h in stage2[:-1]:
            acc += h * s
            band(g, (cx, cy, 0), r2, acc, .09 * s, IRON, segments=segments, proud=.03)
    heights['stage2_top'] = z
    # Capsule: service ring, cone with portholes, brass nose.
    section(r2, r2 * 1.04, .25 * s, IRON)
    band(g, (cx, cy, 0), r2 * 1.04, z - .05 * s, .08 * s, BRASS, segments=segments, proud=.02)
    zc = z
    cone_h = 1.6 * s
    revolve(g, (cx, cy, z), [(r2 * 1.04, 0), (r2 * .92, .3 * s), (r2 * .55, cone_h * .72), (r2 * .3, cone_h)],
            PAINTED, segments=segments, cap_bottom=False)
    heights['capsule_base'] = zc
    # Portholes facing the crew arm (+X) and the front (-Y).
    for ang in (0, -math.pi / 2, math.pi):
        rr = r2 * .86
        zz = zc + .45 * s
        px, py = cx + math.cos(ang) * rr, cy + math.sin(ang) * rr
        ax = 'X' if abs(math.cos(ang)) > .5 else 'Y'
        g.ring((px, py, zz), .14 * s, .045, .06, BRASS, ax, 12)
        g.cylinder((px, py, zz), .1 * s, .05, IRON, ax, 12)
        g.cylinder((px + math.cos(ang) * .02, py + math.sin(ang) * .02, zz), .06 * s, .02, CYAN, ax, 8)
    z = zc + cone_h
    revolve(g, (cx, cy, z), [(r2 * .3, 0), (r2 * .3, .08 * s), (.06 * s, .3 * s), (0, .36 * s)], BRASS,
            segments=16, cap_bottom=False)
    z += .36 * s
    heights['nose'] = z
    if escape_tower:
        # Lattice escape tower with a small banded motor on top.
        base = z - .2 * s
        top = base + 1.1 * s
        for i in range(3):
            a = i * 2 * math.pi / 3
            p = (cx + math.cos(a) * .2 * s, cy + math.sin(a) * .2 * s)
            q = (cx + math.cos(a) * .07 * s, cy + math.sin(a) * .07 * s)
            g.beam((p[0], p[1], base - .25 * s), (q[0], q[1], top), .035, mat=IRON)
        for k in range(1, 4):
            zz = base + (top - base) * k / 4
            g.ring((cx, cy, zz), (.2 - .13 * k / 4) * s + .02, .02, .03, IRON, 'Z', 8)
        revolve(g, (cx, cy, top - .02), [(.09 * s, 0), (.09 * s, .45 * s), (.04 * s, .62 * s), (0, .66 * s)],
                PAINTED, segments=12)
        band(g, (cx, cy, 0), .09 * s, top + .12 * s, .05 * s, ORANGE, segments=12, proud=.02)
        z = top + .64 * s
    heights['top'] = z
    if fins:
        rr = r1 * s
        zl = z0 + .08 * s
        for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            root, tip = rr - .06, rr + .72 * s
            lo, mid, hi = zl, zl + .85 * s, zl + 2.5 * s
            if sx:
                xr, xt = cx + sx * root, cx + sx * tip
                prof = [(xr, lo), (xt, lo - .25 * s), (xt, mid), (xr, hi)]
                if sx < 0:
                    prof = [(xt, lo - .25 * s), (xr, lo), (xr, hi), (xt, mid)]
                extrude_profile(g, prof, cy - .05, cy + .05, PAINTED, axis='Y')
                # Forged leading-edge strap, proud of the fin faces.
                g.beam((xt + sx * .02, cy, lo - .25 * s), (xt + sx * .02, cy, mid + .05), .06, .14, IRON)
                g.beam((xt, cy, mid), (xr + sx * .02, cy, hi + .02), .05, .13, IRON)
            else:
                yr, yt = cy + sy * root, cy + sy * tip
                prof = [(yr, lo), (yt, lo - .25 * s), (yt, mid), (yr, hi)]
                if sy < 0:
                    prof = [(yt, lo - .25 * s), (yr, lo), (yr, hi), (yt, mid)]
                extrude_profile(g, prof, cx - .05, cx + .05, PAINTED, axis='X')
                g.beam((cx, yt + sy * .02, lo - .25 * s), (cx, yt + sy * .02, mid + .05), .14, .06, IRON)
                g.beam((cx, yt, mid), (cx, yr + sy * .02, hi + .02), .13, .05, IRON)
    return heights


# ---------------------------------------------------------------- animation

def _key_curve(obj, frame_end, fn, *, step=4):
    """Sample fn(t) -> (loc_delta_artwork, rot_z, rot_x) at regular frames, linear."""
    span = frame_end - 1
    base = obj.location.copy()
    obj.rotation_mode = 'XYZ'
    frames = list(range(1, frame_end, step)) + [frame_end]
    for f in frames:
        t = (f - 1) / span
        d, rz, rx = fn(t)
        obj.location = (base.x - d[0], base.y - d[1], base.z + d[2])
        obj.rotation_euler = (rx, 0, rz)
        obj.keyframe_insert(data_path='location', frame=f)
        obj.keyframe_insert(data_path='rotation_euler', frame=f)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'


def _hold(t, pattern=((0, 0), (.4, 1), (.5, 1), (.9, 0), (1, 0))):
    """Eased out-and-back hold curve in 0..1."""
    for (t0, v0), (t1, v1) in zip(pattern, pattern[1:]):
        if t0 <= t <= t1:
            u = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            u = u * u * (3 - 2 * u)
            return v0 + (v1 - v0) * u
    return pattern[-1][1]


def animate(obj, kind, value, frame_end):
    """Custom kinds shared by the space-program modules.

    CUSTOM_YAW_SWING  value = angle (rad): eased swing about Z and back, with holds.
    CUSTOM_YAW_OSC    value = (amplitude, cycles): sinusoidal oscillation about Z.
    CUSTOM_PATH       value = [(t, dx, dy, dz), ...] artwork offsets, eased between keys.
    CUSTOM_DISH       value = (yaw_amp, el_amp): yaw about Z plus elevation about local X.
    """
    if kind == 'CUSTOM_YAW_SWING':
        _key_curve(obj, frame_end, lambda t: ((0, 0, 0), value * _hold(t), 0))
    elif kind == 'CUSTOM_YAW_OSC':
        amp, cycles = value
        _key_curve(obj, frame_end, lambda t: ((0, 0, 0), amp * math.sin(2 * math.pi * cycles * t), 0))
    elif kind == 'CUSTOM_PATH':
        keys = value
        def fn(t):
            for (t0, *a), (t1, *b) in zip(keys, keys[1:]):
                if t0 <= t <= t1:
                    u = 0 if t1 == t0 else (t - t0) / (t1 - t0)
                    u = u * u * (3 - 2 * u)
                    return tuple(a[i] + (b[i] - a[i]) * u for i in range(3)), 0, 0
            return tuple(keys[-1][1:]), 0, 0
        _key_curve(obj, frame_end, fn)
    elif kind == 'CUSTOM_DISH':
        yaw, el = value
        _key_curve(obj, frame_end, lambda t: ((0, 0, 0), yaw * math.sin(2 * math.pi * t),
                                              el * (.5 - .5 * math.cos(4 * math.pi * t))))
    elif kind == 'CUSTOM_DISH_YAW':
        yaw, _ = value
        _key_curve(obj, frame_end, lambda t: ((0, 0, 0), yaw * math.sin(2 * math.pi * t), 0))
    else:
        raise ValueError('Unknown custom animation ' + kind)
