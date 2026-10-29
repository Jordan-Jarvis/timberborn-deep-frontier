"""Shared parts for the heavy chemistry and industry late-game buildings.

Owned by the ChemicalWorks / ElectrolysisPlant / PrecisionMachineWorks /
WaterTreatmentPlant modules. Native material slots only (lategame_kit
NATIVE_SLOTS); GLOW and CYAN only as tiny accents. Every helper keeps parallel
surfaces apart by at least lategame_kit.LAYER_GAP or buries one of them, and
winds faces outward.

Artwork coordinates: X across, Y back, Z up; one unit = one tile / one layer.
"""
import math
from mathutils import Vector

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import (CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, WINDOW,
                          CYAN, GLOW, LAYER_GAP, revolve, hollow_revolve, oriented_polygon)

FACES = {'front': (0, -1, 0), 'back': (0, 1, 0), 'left': (-1, 0, 0), 'right': (1, 0, 0),
         'up': (0, 0, 1), 'down': (0, 0, -1)}


# ---------------------------------------------------------------- lathe

def lathe(g, center, profile, mat, *, axis='Z', segments=12, cap_start=True, cap_end=True, phase=0.0):
    """Closed surface of revolution about an X, Y or Z axis through `center`.

    `profile` is (radius, t) pairs with t rising along the axis (equal t
    makes a flat annular step).
    A zero radius closes the surface. Faces wind outward (cyclic axis map).
    """
    for (r0, t0), (r1, t1) in zip(profile, profile[1:]):
        if t1 < t0 or (t1 == t0 and r1 == r0):
            raise ValueError('Lathe profile must rise along its axis (flat steps allowed)')
    cx, cy, cz = center
    def world(u, v, w):
        if axis == 'Z':
            return (cx + u, cy + v, cz + w)
        if axis == 'X':
            return (cx + w, cy + u, cz + v)
        if axis == 'Y':
            return (cx + v, cy + w, cz + u)
        raise ValueError('Lathe axis must be X, Y or Z')
    n = segments
    verts, rows = [], []
    for r, t in profile:
        if r == 0:
            rows.append([len(verts)] * n)
            verts.append(world(0, 0, t))
        else:
            row = []
            for i in range(n):
                a = phase + i * 2 * math.pi / n
                row.append(len(verts))
                verts.append(world(math.cos(a) * r, math.sin(a) * r, t))
            rows.append(row)
    faces = []
    for lower, upper in zip(rows, rows[1:]):
        for i in range(n):
            j = (i + 1) % n
            quad = list(dict.fromkeys([lower[i], lower[j], upper[j], upper[i]]))
            if len(quad) >= 3:
                faces.append(tuple(quad))
    if cap_start and profile[0][0] > 0:
        faces.append(tuple(reversed(rows[0])))
    if cap_end and profile[-1][0] > 0:
        faces.append(tuple(rows[-1]))
    g.add(verts, faces, mat)
    if axis == 'Z':   # a host for lategame_kit.band (same record as K.revolve)
        g.__dict__.setdefault('_revolves', []).append((cx, cy, [(r, cz + t) for r, t in profile], n, phase))


def sphere(g, center, r, mat, *, segments=12, rings=6, squash=1.0):
    profile = []
    for k in range(rings + 1):
        a = -math.pi / 2 + math.pi * k / rings
        profile.append((0 if k in (0, rings) else r * math.cos(a), r * squash * math.sin(a)))
    lathe(g, center, profile, mat, segments=segments)


def hoop(g, center, r, t, width, mat=IRON, *, axis='Z', segments=12):
    """Solid rectangular-section hoop: outer radius r, radial depth t."""
    cx, cy, cz = center
    profile = [(r, -width / 2), (r, width / 2)]
    if axis == 'Z':
        hollow_revolve(g, center, profile, t, mat, segments=segments)
    else:
        # Rebuild with lathe for horizontal axes: outer, inner, two rims.
        lathe(g, center, [(r, -width / 2), (r, width / 2)], mat, axis=axis, segments=segments,
              cap_start=False, cap_end=False)
        _inner_shell(g, center, r - t, width, mat, axis, segments)
        _rims(g, center, r, r - t, width, mat, axis, segments)


def _axis_world(center, axis):
    cx, cy, cz = center
    if axis == 'X':
        return lambda u, v, w: (cx + w, cy + u, cz + v)
    if axis == 'Y':
        return lambda u, v, w: (cx + v, cy + w, cz + u)
    return lambda u, v, w: (cx + u, cy + v, cz + w)


def _inner_shell(g, center, r, width, mat, axis, segments):
    world = _axis_world(center, axis)
    n = segments
    verts = [world(math.cos(i * 2 * math.pi / n) * r, math.sin(i * 2 * math.pi / n) * r, t)
             for t in (-width / 2, width / 2) for i in range(n)]
    faces = [tuple(reversed((i, (i + 1) % n, (i + 1) % n + n, i + n))) for i in range(n)]
    g.add(verts, faces, mat)


def _rims(g, center, ro, ri, width, mat, axis, segments):
    world = _axis_world(center, axis)
    n = segments
    for t, sign in ((-width / 2, -1), (width / 2, 1)):
        for i in range(n):
            a0, a1 = i * 2 * math.pi / n, (i + 1) * 2 * math.pi / n
            pts = [world(math.cos(a0) * ro, math.sin(a0) * ro, t), world(math.cos(a1) * ro, math.sin(a1) * ro, t),
                   world(math.cos(a1) * ri, math.sin(a1) * ri, t), world(math.cos(a0) * ri, math.sin(a0) * ri, t)]
            nrm = world(0, 0, sign)
            c = world(0, 0, 0)
            oriented_polygon(g, pts, tuple(nrm[k] - c[k] for k in range(3)), mat)


def disc(g, center, r, width, mat=BRASS, *, axis='Z', segments=8):
    """Solid flange disc on a pipe (the bore inside it is never seen): 28
    triangles at 8 sides, where a 16-sided hollow hoop was 128."""
    lathe(g, center, [(r, -width / 2), (r, width / 2)], mat, axis=axis, segments=segments)


def annulus(g, center, r_in, r_out, z0, z1, mat=IRON, *, segments=12):
    """Flat ring deck (platform round a column)."""
    hollow_revolve(g, (center[0], center[1], 0), [(r_out, z0), (r_out, z1)], r_out - r_in, mat,
                   segments=segments)


def ring_rail(g, center, r, z, *, height=.6, posts=12, mat=IRON, gap=None):
    """Circular handrail on a round platform: posts and two ring rails.

    `gap` = (a0, a1) radians leaves an opening (for a ladder head)."""
    cx, cy = center[0], center[1]
    for i in range(posts):
        a = i * 2 * math.pi / posts
        if gap and gap[0] <= a <= gap[1]:
            continue
        g.box((cx + math.cos(a) * r, cy + math.sin(a) * r, z + height / 2 - .01), (.04, .04, height - .02), mat)
    for h, w in ((height, .06), (height * .5, .028)):
        if gap:
            _arc_bar(g, (cx, cy), r, z + h, w, gap[1], gap[0] + 2 * math.pi, mat)
        else:
            hollow_revolve(g, (cx, cy, 0), [(r + w / 2, z + h - w / 2), (r + w / 2, z + h + w / 2)], w, mat,
                           segments=max(12, posts))


def _arc_bar(g, c, r, z, w, a0, a1, mat, steps=12):
    pts = [(c[0] + math.cos(a0 + (a1 - a0) * k / steps) * r, c[1] + math.sin(a0 + (a1 - a0) * k / steps) * r)
           for k in range(steps + 1)]
    for k, (p, q) in enumerate(zip(pts, pts[1:])):
        # Alternate a hair in height so neighbouring tops never share a plane.
        # Square bar segments: a round 8-sided tube per segment was 28
        # triangles for a rail two pixels thick.
        dz = .004 if k % 2 else 0
        g.beam((p[0], p[1], z + dz), (q[0], q[1], z + dz), w, mat=mat)


# ---------------------------------------------------------------- pipes

def tube(g, a, b, r, mat=IRON, *, segments=8, caps=True):
    """Round tube between two points, capped, faces outward."""
    a, b = Vector(a), Vector(b)
    d = b - a
    if d.length < 1e-5:
        raise ValueError('Zero-length tube')
    q = d.to_track_quat('Z', 'Y')
    n = segments
    ring = lambda p: [p + q @ Vector((math.cos(i * 2 * math.pi / n) * r, math.sin(i * 2 * math.pi / n) * r, 0))
                      for i in range(n)]
    verts = [tuple(v) for v in ring(a) + ring(b)]
    faces = [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    if caps:
        faces.append(tuple(reversed(range(n))))
        faces.append(tuple(range(n, 2 * n)))
    g.add(verts, faces, mat)


def pipe(g, points, r=.07, mat=IRON, *, flanges=True, flange_mat=BRASS, segments=8, elbow_mat=None):
    """Polyline pipe with ball elbows and bolted flanges near each joint."""
    for a, b in zip(points, points[1:]):
        tube(g, a, b, r, mat, segments=segments)
    for p in points[1:-1]:
        sphere(g, p, r * 1.18, elbow_mat if elbow_mat is not None else mat, segments=segments, rings=4)
    if not flanges:
        return
    for a, b in zip(points, points[1:]):
        delta = [b[i] - a[i] for i in range(3)]
        axis = max(range(3), key=lambda i: abs(delta[i]))
        if any(abs(delta[i]) > 1e-6 for i in range(3) if i != axis):
            continue
        length = abs(delta[axis])
        if length < .7:
            continue
        for f in (.28 / length, 1 - .28 / length):
            p = tuple(a[i] + delta[i] * f for i in range(3))
            disc(g, p, r * 1.65, .06, flange_mat, axis='XYZ'[axis], segments=segments)


def valve(g, p, axis_dir='front', r=.12, *, stem=.14):
    """Gate valve body on a pipe with a handwheel on its stem."""
    nx, ny, nz = FACES[axis_dir]
    x, y, z = p
    tip = (x + nx * stem, y + ny * stem, z + nz * stem)
    tube(g, p, tip, .022, IRON, segments=8)
    ax = 'X' if nx else ('Y' if ny else 'Z')
    hoop(g, tip, r, .03, .035, PAINTED, axis=ax, segments=8)
    for k in range(3):
        a = k * math.pi / 3
        if ax == 'Y':
            e = (math.cos(a) * r * .92, 0, math.sin(a) * r * .92)
        elif ax == 'X':
            e = (0, math.cos(a) * r * .92, math.sin(a) * r * .92)
        else:
            e = (math.cos(a) * r * .92, math.sin(a) * r * .92, 0)
        tube(g, (tip[0] - e[0], tip[1] - e[1], tip[2] - e[2]), (tip[0] + e[0], tip[1] + e[1], tip[2] + e[2]),
             .014, IRON, segments=6)


def gauge(g, x, y, z, face='front', r=.1):
    """Pressure gauge on a wall plane at (x, y, z): iron body, white dial
    and a tiny cyan needle (no glass). Eight sides; the 16-sided brass
    bezel hoop (128 triangles) was a one-pixel ring at game zoom."""
    nx, ny, _ = FACES[face]
    ax = 'Y' if ny else 'X'
    def at(d):
        return (x + nx * d, y + ny * d, z)
    g.cylinder(at(.03), r, .06, IRON, ax, 8)
    g.cylinder(at(.065), r * .84, .03, CONCRETE, ax, 8)
    # Needle: thin bar proud of the dial.
    tx, ty = -ny, nx
    a = (x + nx * .088, y + ny * .088, z)
    b = (x + nx * .088 + tx * r * .55, y + ny * .088 + ty * r * .55, z + r * .45)
    g.beam(a, b, .016, mat=CYAN)


# ---------------------------------------------------------------- walls & rails

def rail(g, points, z, *, height=.62, pitch=.6, mat=IRON):
    """Straight-run handrail through plan points. Corner posts are taller
    newels; rails butt into them, so no two rail tops overlap."""
    newel = .075
    for p in points:
        g.box((p[0], p[1], z + (height + .06) / 2), (newel, newel, height + .06), mat)
    for a, b in zip(points, points[1:]):
        a, b = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
        d = b - a
        length = d.length
        u = d / length
        count = max(1, math.ceil(length / pitch))
        for i in range(1, count):
            p = a + d * i / count
            g.box((p.x, p.y, z + height / 2 - .01), (.04, .04, height - .02), mat)
        s, e = a + u * newel / 2, b - u * newel / 2
        # Post .04, top rail .06, mid rail .028: faces at least 6 mm apart.
        for h, w in ((height, .06), (height * .5, .028)):
            g.beam((s.x, s.y, z + h - w / 2), (e.x, e.y, z + h - w / 2), w, mat=mat)


def grating(g, x0, y0, x1, y1, z, *, along='X'):
    """Steel grating deck plate whose top is at whole layer z."""
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, z - .04), (x1 - x0, y1 - y0, .08), IRON)
    if along == 'X':
        count = max(2, round((y1 - y0) / .14))
        for i in range(count):
            y = y0 + (i + .5) * (y1 - y0) / count
            g.box(((x0 + x1) / 2, y, z + .007), (x1 - x0 - .05, .03, .014), FORGED)
    else:
        count = max(2, round((x1 - x0) / .14))
        for i in range(count):
            x = x0 + (i + .5) * (x1 - x0) / count
            g.box((x, (y0 + y1) / 2, z + .007), (.03, y1 - y0 - .05, .014), FORGED)


def knee(g, base, tip, w=.07):
    """Diagonal steel bracket strut."""
    g.beam(base, tip, w, mat=IRON)


def timber_frame_wall(g, axis, plane, start, end, bottom, top, *, outward, infill=ORANGE,
                      bays=None, windows=(), window_style='grand', window_scale=.8, door=None, brace=False):
    """Iron Teeth timber frame: dark posts and rails proud of plaster infill."""
    K.frame_wall(g, axis, plane, start, end, bottom, top, outward=outward, infill=infill, bays=bays,
                 post=WOOD, post_w=.15, windows=list(windows), window_style=window_style,
                 window_scale=window_scale, door=door)


def louvre(g, axis, plane, start, end, bottom, top, outward, *, mat=FORGED, pitch=.16):
    """Proud louvre slats on a wall plane (vents)."""
    n = max(2, int((top - bottom) / pitch))
    for k in range(n):
        z = bottom + (k + .5) * (top - bottom) / n
        d = outward * .03
        if axis == 'X':
            g.beam(((start), plane + d, z + .03), (end, plane + d, z + .03), .05, .06, mat)
        else:
            g.beam((plane + d, start, z + .03), (plane + d, end, z + .03), .05, .06, mat)


# ---------------------------------------------------------------- electrical

def insulator(g, x, y, z, height=.5, r=.09, discs=4):
    """Porcelain disc insulator stack (white plaster discs on an iron rod;
    each disc is open where the rod passes through it)."""
    g.cylinder((x, y, z + height / 2), r * .35, height, IRON, 'Z', 8)
    for k in range(discs):
        zz = z + .06 + (height - .12) * k / max(1, discs - 1)
        revolve(g, (x, y, zz), [(r * .4, -.02), (r, 0), (r * .4, .03)], CONCRETE, segments=8,
                cap_bottom=False, cap_top=False)
    g.cylinder((x, y, z + height + .02), r * .5, .04, BRASS, 'Z', 10)


def motor(g, p, r=.18, length=.4, *, axis='Z', mat=PAINTED):
    """Electric motor: finned painted body, end bell and terminal box."""
    x, y, z = p
    lathe(g, p, [(r * .9, -length / 2), (r, -length / 2 + .04), (r, length / 2 - .04), (r * .8, length / 2),
                 (r * .3, length / 2 + .05)], mat, axis=axis, segments=12)
    for k in range(3):
        t = -length / 2 + length * (k + 1) / 4
        c = (x + t, y, z) if axis == 'X' else ((x, y + t, z) if axis == 'Y' else (x, y, z + t))
        # Solid cooling fin (its core lies in the body): 44 triangles, a
        # hollow hoop was 96.
        disc(g, c, r + .03, .035, IRON, axis=axis, segments=12)
    if axis == 'Z':
        g.box((x + r + .05, y, z), (.1, .14, .14), IRON)
    else:
        g.box((x, y, z + r + .05), (.14, .14, .1), IRON)


def lamp_post(g, x, y, z, height=1.3):
    g.box((x, y, z + height / 2), (.07, .07, height), IRON)
    K.lamp(g, x, y + .0, z + height - .25, face='front')


# ---------------------------------------------------------------- animated

def flywheel(name, center, r, *, axis='X', spokes=6, mat=IRON, rim_mat=PAINTED, width=.12):
    """Spoked flywheel as an animated part (SPIN_<axis>)."""
    f = Geometry(name, center)
    hoop(f, center, r, .07, width, rim_mat, axis=axis, segments=12)
    lathe(f, center, [(r * .2, -width * .7), (r * .2, width * .7)], mat, axis=axis, segments=12)
    x, y, z = center
    for k in range(spokes):
        a = k * 2 * math.pi / spokes
        c, s = math.cos(a) * (r - .05), math.sin(a) * (r - .05)
        e = (x, y + c, z + s) if axis == 'X' else ((x + c, y, z + s) if axis == 'Y' else (x + c, y + s, z))
        h = (x, y + c * .2, z + s * .2) if axis == 'X' else ((x + c * .2, y, z + s * .2) if axis == 'Y' else (x + c * .2, y + s * .2, z))
        f.beam(h, e, .05, mat=mat)
    return f


def pulley(f, center, r, width, axis='X', mat=IRON):
    lathe(f, center, [(r * .9, -width / 2), (r, -width / 2 + .02), (r, width / 2 - .02), (r * .9, width / 2)],
          mat, axis=axis, segments=12)


# ---------------------------------------------------------------- fixed kit variants
# The kit versions of these put two bottom faces on the same ground plane (or
# overlap blades / legs); these keep one face of each pair below ground or apart.

def plinth(g, x0, y0, x1, y1, top, *, door=None, mat=CONCRETE, pilasters=True):
    """Cast concrete podium (kit API). Returns the walking surface height."""
    if door is None:
        g.box(((x0 + x1) / 2, (y0 + y1) / 2, top / 2), (x1 - x0, y1 - y0, top), mat)
        g.box(((x0 + x1) / 2, (y0 + y1) / 2, .035), (x1 - x0 + .05, y1 - y0 + .05, .13), mat)
    else:
        dx, dw, dh = door
        left, right = dx - dw / 2, dx + dw / 2
        if left <= x0 + .1 or right >= x1 - .1 or dh >= top:
            raise ValueError('Plinth door must sit inside the plinth face')
        depth = y1 - y0
        g.box(((x0 + left) / 2, (y0 + y1) / 2, top / 2), (left - x0, depth, top), mat)
        g.box(((right + x1) / 2, (y0 + y1) / 2, top / 2), (x1 - right, depth, top), mat)
        g.box((dx, (y0 + y1) / 2, (dh + top) / 2), (dw, depth, top - dh), mat)
        g.box((dx, y0 + .25 + depth / 2, dh / 2), (dw, depth - .5, dh), mat)
        g.box((dx, y0 + .24, dh / 2), (dw - LAYER_GAP, .02, dh - LAYER_GAP), IRON)
        for a, b in ((x0 - .025, left - .03), (right + .03, x1 + .025)):
            g.box(((a + b) / 2, (y0 + y1) / 2, .035), (b - a, y1 - y0 + .05, .13), mat)
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, top - .034), (x1 - x0 + .08, y1 - y0 + .08, .092), mat)
    if pilasters:
        for x in K._stations(x0, x1, 1.0):
            if door is not None and abs(x - door[0]) < door[1] / 2 + .12:
                continue
            for y, sgn in ((y0, -1), (y1, 1)):
                g.box((x, y + sgn * .015, (top + .07) / 2), (.10, .03, top - .21), mat)
        for y in K._stations(y0, y1, 1.0):
            for x, sgn in ((x0, -1), (x1, 1)):
                g.box((x + sgn * .015, y, (top + .07) / 2), (.03, .10, top - .21), mat)
    return top + .012


def pier(g, x, y, bottom, top, w=.36):
    """Square concrete pier with a steel bearing cap (foot sunk below base)."""
    g.box((x, y, (bottom + top) / 2), (w, w, top - bottom), CONCRETE)
    g.box((x, y, bottom + .035), (w + .06, w + .06, .13), CONCRETE)
    g.box((x, y, top + .025), (w + .05, w + .05, .05), IRON)
    return top + .05


def lattice_tower(g, x0, y0, x1, y1, bottom, top, *, bays=None, w=.10, mat=IRON, pads=True):
    """Four-legged braced steel tower; leg pads are sunk below the base."""
    if bays is None:
        bays = max(1, round((top - bottom) / 1.2))
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for x, y in corners:
        g.box((x, y, (bottom + top) / 2), (w, w, top - bottom), mat)
        if pads:
            g.box((x, y, bottom + .025), (w + .14, w + .14, .11), CONCRETE)
    for k in range(1, bays + 1):
        z = bottom + (top - bottom) * k / bays - (w * .35 if k == bays else 0)
        for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
            inset = w / 2 + .01
            if ax == bx:
                g.box((ax, (ay + by) / 2, z), (w * .7, abs(by - ay) - 2 * inset, w * .7), mat)
            else:
                g.box(((ax + bx) / 2, ay, z), (abs(bx - ax) - 2 * inset, w * .7, w * .7), mat)
    for k in range(bays):
        za = bottom + (top - bottom) * k / bays + (.15 if k == 0 else 0)
        zb = bottom + (top - bottom) * (k + 1) / bays
        for idx, ((ax, ay), (bx, by)) in enumerate(zip(corners, corners[1:] + corners[:1])):
            nx = 0 if ax != bx else (-1 if ax == x0 else 1)
            ny = 0 if ay != by else (-1 if ay == y0 else 1)
            # Alternate bays sit 20 mm apart so diagonals meeting at a girt
            # never share a face plane.
            off = w * .55 + (k % 2) * .02
            p = (ax + nx * off, ay + ny * off)
            q = (bx + nx * off, by + ny * off)
            if (k + idx) % 2:
                g.beam((p[0], p[1], za), (q[0], q[1], zb), w * .5, mat=mat)
            else:
                g.beam((q[0], q[1], za), (p[0], p[1], zb), w * .5, mat=mat)


def _add_oriented(g, verts, faces, mat, inside):
    """Add a convex solid's faces, each wound to face away from `inside`."""
    for face in faces:
        pts = [verts[i] for i in face]
        c = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
        oriented_polygon(g, pts, tuple(c[k] - inside[k] for k in range(3)), mat)


def fan(name, x, y, z, r, *, blades=5, pitch=.35, mat=IRON, hub_mat=PAINTED):
    """Animated axial fan about Z (SPIN_Z): pitched blades from a solid hub."""
    f = Geometry(name, (x, y, z))
    hub = r * .24
    lathe(f, (x, y, z), [(hub, -.06), (hub, .05), (hub * .5, .09)], hub_mat, segments=12)
    for i in range(blades):
        a = i * 2 * math.pi / blades
        c, s_ = math.cos(a), math.sin(a)
        pts = []
        for rr, half in ((hub * .85, r * .13), (r, r * .2)):
            for side in (-1, 1):
                tx, ty = -s_ * half * side * math.cos(pitch), c * half * side * math.cos(pitch)
                pts.append((x + c * rr + tx, y + s_ * rr + ty, z + half * side * math.sin(pitch)))
        th = .012
        verts = [(p[0], p[1], p[2] + th) for p in pts] + [(p[0], p[1], p[2] - th) for p in pts]
        faces = [(0, 1, 3, 2), (6, 7, 5, 4), (0, 2, 6, 4), (1, 5, 7, 3), (2, 3, 7, 6), (0, 4, 5, 1)]
        _add_oriented(f, verts, faces, mat, (x + c * r * .6, y + s_ * r * .6, z))
    return f


def plank_roof(g, x0, y0, x1, y1, eave, ridge, *, ridge_axis='Y', overhang=.16, plank=.3,
               gable_mat=PLANK, wall_skin=.05, trim=WOOD, cap=IRON, gables=(True, True)):
    """Gable roof of separate native roof planks (each its own board island)
    over a dark sarking sheet, with solid gable prisms, barge boards, fascia
    and a steel ridge cap. (x0..x1, y0..y1) are the wall centre planes; the
    walls have outer skins `wall_skin` outside them and rise to eave + .03.
    """
    if ridge_axis == 'Y':
        u0, u1, v0, v1 = x0, x1, y0, y1
        W = lambda u, v, z: (u, v, z)
        S = lambda du, dv, dz: (du, dv, dz)
    else:
        u0, u1, v0, v1 = y0, y1, x0, x1
        W = lambda u, v, z: (v, u, z)
        S = lambda du, dv, dz: (dv, du, dz)
    mid = (u0 + u1) / 2
    half = (u1 - u0) / 2
    s = (ridge - eave) / half
    ang = math.atan(s)
    t = .07
    lift = t / 2 / math.cos(ang)
    vlo, vhi = v0 - overhang, v1 + overhang
    n = max(2, math.ceil((vhi - vlo) / plank))
    width = (vhi - vlo) / n
    ze = eave - overhang * s
    def extrude(profile, a, b, mat):
        # extrude_profile takes counter-clockwise (u, z) for either axis.
        K.extrude_profile(g, profile, a, b, mat, axis=ridge_axis)
    for side in (-1, 1):
        ue = mid + side * (half + overhang)
        for i in range(n):
            v = vlo + (i + .5) * width
            ext = .05 if i % 3 == 1 else 0
            a = W(ue + side * ext, v, ze - ext * s + lift + .012)
            b = W(mid - side * .02, v, ridge + .02 * s + lift + .012)
            # The two slopes' planks cross at the ridge: the far slope's are
            # 12 mm narrower so their side faces never share a plane there.
            g.beam(a, b, width - (.014 if side < 0 else .026), t, ROOF)
        prof = [(ue, ze), (mid, ridge), (mid, ridge + .012), (ue, ze + .012)]
        if side > 0:
            prof = list(reversed(prof))
        extrude(prof, vlo + .006, vhi - .006, trim)
        g.box(W(ue - side * .025, (vlo + vhi) / 2, ze - .05), S(.04, vhi - vlo - .02, .1), trim)
    for (v, out), keep in zip(((v0, -1), (v1, 1)), gables):
        outer = v + out * (wall_skin - .025)
        inner = v - out * .06
        lo_, hi_ = min(outer, inner), max(outer, inner)
        if keep:
            zb = eave - .01
            tri = [(u0 - wall_skin + .01, zb), (u1 + wall_skin - .01, zb), (mid, ridge - .03)]
            extrude(tri, lo_, hi_, gable_mat)
            kp = W(mid, outer + out * .03, (eave + ridge) / 2 - .05)
            g.box(kp, S(.12, .06, ridge - eave - .2), trim)
        vb = (vlo if out < 0 else vhi) + out * .035
        for side in (-1, 1):
            ue = mid + side * (half + overhang)
            # The two rakes sit 10 mm apart where they cross at the apex.
            vs = vb + out * (.01 if side > 0 else 0)
            g.beam(W(ue, vs, ze + lift + .03), W(mid, vs, ridge + lift + .03), .05, .14, trim)
    g.box(W(mid, (vlo + vhi) / 2, ridge + 2 * lift + .04), S(.18, vhi - vlo + .1, .07), cap)
    return ridge + 2 * lift + .075


def plank_slope(g, along, u_low, u_high, z_low, z_high, v0, v1, *, overhang=.16, plank=.3, trim=WOOD,
                end_overhang=None, fascia=True):
    """One roof slope of separate native planks rising from the eave line
    (u_low, z_low) to (u_high, z_high); v runs along `along` ('X' or 'Y').
    The given line is the sarking underside through the wall-top edge. The
    high edge ends at u_high (bury it in the wall it meets)."""
    if along == 'X':
        W = lambda u, v, z: (v, u, z)
        S = lambda du, dv, dz: (dv, du, dz)
    else:
        W = lambda u, v, z: (u, v, z)
        S = lambda du, dv, dz: (du, dv, dz)
    sign = 1 if u_high > u_low else -1
    s = (z_high - z_low) / abs(u_high - u_low)
    t = .07
    lift = t / 2 / math.cos(math.atan(s))
    ue, ze = u_low - sign * overhang, z_low - overhang * s
    eo = overhang if end_overhang is None else end_overhang
    vlo, vhi = v0 - eo, v1 + eo
    n = max(2, math.ceil((vhi - vlo) / plank))
    width = (vhi - vlo) / n
    for i in range(n):
        v = vlo + (i + .5) * width
        ext = .05 if i % 3 == 1 else 0
        g.beam(W(ue - sign * ext, v, ze - ext * s + lift + .012), W(u_high, v, z_high + lift + .012),
               width - .014, t, ROOF)
    prof = [(ue, ze), (u_high, z_high), (u_high, z_high + .012), (ue, ze + .012)]
    if sign < 0:
        prof = list(reversed(prof))
    K.extrude_profile(g, prof, vlo + .006, vhi - .006, trim, axis=along)
    if fascia:
        g.box(W(ue + sign * .025, (vlo + vhi) / 2, ze - .05), S(.04, vhi - vlo - .02, .1), trim)
    for v, out in ((vlo, -1), (vhi, 1)):
        g.beam(W(ue, v + out * .035, ze + lift + .03), W(u_high, v + out * .035, z_high + lift + .03),
               .05, .14, trim)
    return z_high + 2 * lift + .012


def end_prism(g, along, plane, out, profile, mat, *, inset=.025, depth=.085):
    """Solid closure in a wall end plane (profile CCW in (u, z)), set back
    `inset` from the wall skin at plane + out*.05."""
    outer = plane + out * (.05 - inset)
    inner = outer - out * depth
    K.extrude_profile(g, profile, min(outer, inner), max(outer, inner), mat, axis=along)


def plank_vault(g, x0, y0, x1, y1, spring, rise, *, overhang=.14, plank=.34, segments=8, ribs=5,
                trim=WOOD, rib_mat=IRON):
    """Barrel vault along X built from separate native roof planks (one
    profile slice each) over a dark sarking skin, with proud steel ribs
    centred on planks so no rib face meets a plank joint."""
    cy, half = (y0 + y1) / 2, (y1 - y0) / 2 + overhang
    t = .08
    def arc(h, r):
        return [(cy + math.cos(math.pi * k / segments) * h, spring + math.sin(math.pi * k / segments) * r)
                for k in range(segments + 1)]
    outer, inner = arc(half, rise), arc(half - t, rise - t)
    prof = outer + list(reversed(inner))
    lo, hi = x0 - overhang, x1 + overhang
    n = max(2, math.ceil((hi - lo) / plank))
    w = (hi - lo) / n
    for i in range(n):
        K.extrude_profile(g, prof, lo + i * w + .007, lo + (i + 1) * w - .007, ROOF, axis='X')
    sark = inner + list(reversed(arc(half - t - .015, rise - t - .015)))
    K.extrude_profile(g, sark, lo + .003, hi - .003, trim, axis='X')
    picks = sorted({round(i * (n - 1) / ribs) for i in range(ribs + 1)})
    for i in picks:
        s = lo + (i + .5) * w
        rib = arc(half + .03, rise + .03) + list(reversed(outer))
        K.extrude_profile(g, rib, s - .045, s + .045, rib_mat, axis='X')
    return spring + rise
