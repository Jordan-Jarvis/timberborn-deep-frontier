"""Shared parts for the late-game civic wellbeing studies.

Owned by lategame_Bathhouse / lategame_TownPlaza / lategame_ObservationDeck.
Deliberately not named lategame_*_parts.py: render_lategame_studies.source_hash
globs that pattern, so a new file there would change every study's hash. The
consequence is that `--skip-unchanged` does not see edits to this file; rebuild
the three owning studies explicitly after changing it.

Artwork coordinates: X across, Y back, Z up; one unit = one tile / one layer.
Native material slots only (lategame_kit.NATIVE_SLOTS); GLOW/CYAN as tiny
accents. Every helper keeps same-facing parallel surfaces at least LAYER_GAP
apart or buries one inside a solid, and winds faces outward.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import (CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, WINDOW, WATER,
                          GLOW, CYAN, LAYER_GAP, oriented_polygon)
from lategame_civic_parts import blk, obox
import native_window_atlas as A

FACE_FRAMES = {'front': ((0, -1), (1, 0)), 'back': ((0, 1), (-1, 0)),
               'left': ((-1, 0), (0, -1)), 'right': ((1, 0), (0, 1))}
# face: (outward normal, tangent u to the right seen from outside)


def _dedupe(points):
    out = []
    for p in points:
        if not out or max(abs(p[i] - out[-1][i]) for i in range(3)) > 1e-9:
            out.append(p)
    if len(out) > 2 and max(abs(out[0][i] - out[-1][i]) for i in range(3)) <= 1e-9:
        out.pop()
    return out


def _ellipse(u, half, rise):
    return rise * math.sqrt(max(0.0, 1 - (u / half) ** 2))


def _normalize(v):
    m = math.sqrt(sum(c * c for c in v))
    return tuple(c / m for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


# ---------------------------------------------------------------- sweeps

def sweep(g, points, sides, ups, a, b, mat, *, caps=True):
    """One continuous rectangular-section bar along a polyline.

    At each point the section spans +-a along `sides[i]` and +-b along
    `ups[i]`. Consecutive sections share their vertices, so bent bands have no
    overlapping same-plane faces at the joints (unlike chained boxes).
    """
    if len(points) < 2 or len(points) != len(sides) or len(points) != len(ups):
        raise ValueError('Sweep needs matching points, sides and ups')
    verts = []
    for p, s, u in zip(points, sides, ups):
        s, u = _normalize(s), _normalize(u)
        for ka, kb in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            verts.append(tuple(p[i] + ka * a * s[i] + kb * b * u[i] for i in range(3)))
    faces = []
    n = len(points)
    for k in range(n - 1):
        o, q = 4 * k, 4 * (k + 1)
        mid = [(points[k][i] + points[k + 1][i]) / 2 for i in range(3)]
        for i in range(4):
            j = (i + 1) % 4
            f = [o + i, o + j, q + j, q + i]
            fc = [sum(verts[v][c] for v in f) / 4 for c in range(3)]
            nn = _newell([verts[v] for v in f])
            if sum(nn[c] * (fc[c] - mid[c]) for c in range(3)) < 0:
                f.reverse()
            faces.append(tuple(f))
    if caps:
        for k, sign in ((0, -1), (n - 1, 1)):
            f = [4 * k, 4 * k + 1, 4 * k + 2, 4 * k + 3]
            tan = ([points[1][i] - points[0][i] for i in range(3)] if k == 0
                   else [points[-1][i] - points[-2][i] for i in range(3)])
            nn = _newell([verts[v] for v in f])
            if sum(nn[c] * tan[c] for c in range(3)) * sign < 0:
                f.reverse()
            faces.append(tuple(f))
    g.add(verts, faces, mat)


def _newell(pts):
    n = [0.0, 0.0, 0.0]
    for (x0, y0, z0), (x1, y1, z1) in zip(pts, pts[1:] + pts[:1]):
        n[0] += (y0 - y1) * (z0 + z1)
        n[1] += (z0 - z1) * (x0 + x1)
        n[2] += (x0 - x1) * (y0 + y1)
    return n


# ---------------------------------------------------------------- groin vault

REGIONS = {'front': ((1, 0), (0, -1)), 'back': ((-1, 0), (0, 1)),
           'left': ((0, -1), (-1, 0)), 'right': ((0, 1), (1, 0))}


def groin_vault(g, cx, cy, half, spring, rise, *, overhang=.12, t=.1, segments=16, mat=ROOF,
                band=IRON, ridge=IRON):
    """Square cross (groin) vault: four elliptic barrel quarters meeting in
    valley groins, each ending in a proud arch over its wall's lunette.

    `half` is the half-width at the wall planes; the arches overhang by
    `overhang`. Shell thickness `t`. The shell springs from the four corners
    at z = spring; those corner zones (where inner and outer shells part) must
    be covered by corner piers. Returns the inner (half, rise) of the arches
    for lunette infills.
    """
    H = half + overhang
    Hi, ri = H - t, rise - t
    us = [-H + 2 * H * k / segments for k in range(segments + 1)]
    for name, ((ux, uy), (wx, wy)) in REGIONS.items():
        def P(u, w, z):
            return (cx + ux * u + wx * w, cy + uy * u + wy * w, z)
        for half_, rise_, sgn in ((H, rise, 1), (Hi, ri, -1)):
            ks = [-half_ + 2 * half_ * k / segments for k in range(segments + 1)]
            for u0, u1 in zip(ks, ks[1:]):
                z0, z1 = spring + _ellipse(u0, half_, rise_), spring + _ellipse(u1, half_, rise_)
                pts = _dedupe([P(u0, abs(u0), z0), P(u1, abs(u1), z1), P(u1, H, z1), P(u0, H, z0)])
                um, zm = (u0 + u1) / 2, (z0 + z1) / 2
                nu, nz = um / half_ ** 2, max(1e-6, (zm - spring)) / rise_ ** 2
                normal = (sgn * ux * nu, sgn * uy * nu, sgn * nz)
                oriented_polygon(g, pts, normal, mat)
        # End ring in the plane w = H.
        for k in range(segments):
            uo0, uo1 = us[k], us[k + 1]
            ui0, ui1 = uo0 * Hi / H, uo1 * Hi / H
            pts = [P(uo0, H, spring + _ellipse(uo0, H, rise)), P(uo1, H, spring + _ellipse(uo1, H, rise)),
                   P(ui1, H, spring + _ellipse(ui1, Hi, ri)), P(ui0, H, spring + _ellipse(ui0, Hi, ri))]
            oriented_polygon(g, _dedupe(pts), (wx, wy, 0), mat)
        # Proud iron band round the arch face: half buried in the ring.
        if band is not None:
            # The band stops one step above the springing: the two bands
            # meeting at a corner never end in a shared (horizontal) cap.
            n = 24
            pts, sides, ups = [], [], []
            for k in range(1, n):
                a = math.pi * k / n
                hb, rb = H + .005, rise + .005
                u, z = -math.cos(a) * hb, spring + math.sin(a) * rb
                pts.append(P(u, H + .012, z))
                sides.append((wx, wy, 0))
                gu, gz = u / hb ** 2, (z - spring) / rb ** 2 + 1e-9
                ups.append((ux * gu, uy * gu, gz))
            sweep(g, pts, sides, ups, .03, .045, band)
    if ridge is not None:
        top = spring + rise
        # Two crossing ridge caps; the second sits 15 mm lower so their tops
        # never share a plane at the crossing.
        g.box((cx, cy, top + .035), (.12, 2 * H + .04, .07), ridge)
        g.box((cx, cy, top + .02), (2 * H + .04, .11, .07), ridge)
    return Hi, ri


def thermal_window(g, face, x, y, z0, R, *, lights=3, frame=IRON, sill=CONCRETE, keystone=CONCRETE,
                   depth=A.MOUNT_DEPTH):
    """Semicircular 'thermal' (Diocletian) window: native glass in three lights
    under an iron arch band, on the wall skin at (x, y), sill at z0."""
    (nx, ny), (tx, ty) = FACE_FRAMES[face]
    def p(u, z, d):
        return (x + u * tx + d * nx, y + u * ty + d * ny, z)
    u0g, u1g, v0g, v1g = A.cell_rect('glass')
    m = .04
    steps = 18
    bounds = [-R + 2 * R * j / lights for j in range(lights + 1)]
    for j in range(lights):
        ua = bounds[j] + (m if j > 0 else 0)
        ub = bounds[j + 1] - (m if j < lights - 1 else 0)
        arc = []
        for k in range(steps + 1):
            u = ub + (ua - ub) * k / steps
            arc.append((u, z0 + math.sqrt(max(0.0, R * R - u * u))))
        ring = [(ua, z0), (ub, z0)] + arc
        uv_pts = []
        ztop = max(z for _, z in ring)
        pts = []
        for u, z in ring:
            pts.append(p(u, z, depth))
            uv_pts.append((u0g + (u - ua) / (ub - ua) * (u1g - u0g), v0g + (z - z0) / (ztop - z0) * (v1g - v0g)))
        # Remove duplicate corners (outer lights meet the sill at a point).
        clean_p, clean_uv = [], []
        for q, uv in zip(pts, uv_pts):
            if clean_p and max(abs(q[i] - clean_p[-1][i]) for i in range(3)) < 1e-9:
                continue
            clean_p.append(q)
            clean_uv.append(uv)
        if max(abs(clean_p[0][i] - clean_p[-1][i]) for i in range(3)) < 1e-9:
            clean_p.pop()
            clean_uv.pop()
        nn = _newell(clean_p)
        order = list(range(len(clean_p)))
        if nn[0] * nx + nn[1] * ny < 0:
            order.reverse()
        g.native_piece([clean_p[i] for i in order], [tuple(range(len(order)))], [clean_uv[i] for i in order], WINDOW)
    # Reveal: the window box stands `depth` proud of the skin (like the atlas
    # windows); its sides face away from the opening.
    for k in range(steps * 2):
        a0, a1 = math.pi * k / (steps * 2), math.pi * (k + 1) / (steps * 2)
        q0 = (R * math.cos(a0), z0 + R * math.sin(a0))
        q1 = (R * math.cos(a1), z0 + R * math.sin(a1))
        quad = [p(q0[0], q0[1], 0), p(q1[0], q1[1], 0), p(q1[0], q1[1], depth), p(q0[0], q0[1], depth)]
        am = (a0 + a1) / 2
        oriented_polygon(g, quad, (math.cos(am) * tx, math.cos(am) * ty, math.sin(am)), WOOD)
    oriented_polygon(g, [p(-R, z0, 0), p(R, z0, 0), p(R, z0, depth), p(-R, z0, depth)], (0, 0, -1), WOOD)
    # Iron arch band, mullions, sill and keystone, all proud of the glass.
    n = 26
    pts, sides, ups = [], [], []
    for k in range(n + 1):
        a = math.pi * k / n
        rr = R + .015
        pts.append(p(-math.cos(a) * rr, z0 + math.sin(a) * rr, depth + .012))
        sides.append((nx, ny, 0))
        ups.append((-math.cos(a) * tx, -math.cos(a) * ty, math.sin(a)))
    sweep(g, pts, sides, ups, .03, .05, frame)
    for j in range(1, lights):
        u = bounds[j]
        top = z0 + math.sqrt(max(0.0, R * R - u * u)) + .01
        # 10 mm shy of the band's front face so the two never share a plane.
        c = p(u, (z0 + top) / 2, depth + .012)
        g.box(c, (abs(.07 * tx) + abs(.04 * nx), abs(.07 * ty) + abs(.04 * ny), top - z0), frame)
    c = p(0, z0 - .05, .06)
    g.box(c, (abs((2 * R + .3) * tx) + abs(.2 * nx), abs((2 * R + .3) * ty) + abs(.2 * ny), .1), sill)
    c = p(0, z0 + R + .06, depth + .03)
    g.box(c, (abs(.2 * tx) + abs(.1 * nx), abs(.2 * ty) + abs(.1 * ny), .2), keystone)


# ---------------------------------------------------------------- columns

def column(g, x, y, z0, z1, *, w=.24, base=.3, cap=.36, mat=CONCRETE, cap_mat=IRON):
    """Square civic column on a grid line: base, shaft with a fluted iron
    band, capital. With base <= 0.3 it never claims a grid cell (the harness
    needs 15 cm of a cell), so path cells between columns stay free."""
    blk(g, x - base / 2, y - base / 2, z0, x + base / 2, y + base / 2, z0 + .12, mat)
    blk(g, x - w / 2, y - w / 2, z0 + .1, x + w / 2, y + w / 2, z1 - .1, mat)
    for zz in (z0 + .45, z1 - .35):
        blk(g, x - w / 2 - .02, y - w / 2 - .02, zz - .03, x + w / 2 + .02, y + w / 2 + .02, zz + .03, cap_mat)
    blk(g, x - cap / 2, y - cap / 2, z1 - .12, x + cap / 2, y + cap / 2, z1, cap_mat)


# ---------------------------------------------------------------- props

def planter(g, x0, y0, x1, y1, h=.45, *, z0=0.0, shrubs=(), soil=PLANK):
    """Low cast-concrete planter trough with a proud coping, a sunk soil bed
    and native shrubs. `z0` is the trough bottom (bury it in any paving so
    only one solid owns the ground plane)."""
    import native_building_assets as N
    t = .1
    blk(g, x0, y0, z0, x1, y1, h - .06, CONCRETE)                        # solid trough
    # Coping ring (four bars) round a soil bed 4 cm below the coping top.
    for a in ((x0 - .025, y0 - .025, x1 + .025, y0 + t), (x0 - .025, y1 - t, x1 + .025, y1 + .025),
              (x0 - .025, y0 + t, x0 + t, y1 - t), (x1 - t, y0 + t, x1 + .025, y1 - t)):
        blk(g, a[0], a[1], h - .06, a[2], a[3], h, CONCRETE)
    blk(g, x0 + t, y0 + t, h - .1, x1 - t, y1 - t, h - .04, soil)
    for sx, sy, s in shrubs:
        N.plant(g, 'Shrub.IronTeeth', (sx, sy, h - .045), s)


def flagpole(g, parts, name, x, y, z0, h, *, flag_w=.75, flag_h=.45, phase=0.0, mat=ORANGE, direction=1):
    """Steel flagpole on a concrete socket; the flag (flying toward
    `direction` = +1/-1 along X) is a separate part that swings about the
    pole (CUSTOM_YAW_OSC)."""
    if direction not in (-1, 1):
        raise ValueError('Flag direction must be +1 or -1 along X')
    blk(g, x - .12, y - .12, z0, x + .12, y + .12, z0 + .18, CONCRETE)
    K.revolve(g, (x, y, z0 + .16), [(.045, 0), (.03, h - .2)], IRON, segments=10)
    K.revolve(g, (x, y, z0 + h - .06), [(.001, 0), (.06, .04), (.06, .09), (.001, .13)], BRASS, segments=10)
    top = z0 + h - .15
    f = Geometry(name, (x, y, top))
    # Halyard collar, flag cloth (one face each way, 12 mm apart) and an
    # iron gear emblem proud of both faces.
    f.cylinder((x, y, top - flag_h / 2), .05, flag_h + .06, IRON, 'Z', 8)
    za, zb = top - flag_h, top
    wave = .05
    n = 6
    pts = []
    for k in range(n + 1):
        u = k / n
        pts.append((x + direction * (.05 + flag_w * u), y + math.sin(u * math.pi * 1.5 + phase) * wave * u))
    for side in (-1, 1):
        for pa, pb in zip(pts, pts[1:]):
            quad = [(pa[0], pa[1] + side * .006, za), (pb[0], pb[1] + side * .006, za),
                    (pb[0], pb[1] + side * .006, zb), (pa[0], pa[1] + side * .006, zb)]
            oriented_polygon(f, quad, (0, side, 0), mat)
    u = .45
    cx, cz = x + direction * (.05 + flag_w * u), (za + zb) / 2
    yy = y + math.sin(u * math.pi * 1.5 + phase) * wave * u
    f.ring((cx, yy, cz), flag_h * .28, .035, .03, IRON, 'Y', 16)
    parts.append((f, 'CUSTOM_YAW_OSC', (.32, 2)))


def lamp_standard(g, x, y, z0, h=1.5, *, arms=1):
    """Cast-iron street lamp standard (for plinths and piers)."""
    K.revolve(g, (x, y, z0), [(.09, 0), (.09, .1), (.05, .16), (.035, h - .25)], IRON, segments=10)
    zl = z0 + h - .3
    K.revolve(g, (x, y, zl), [(.06, 0), (.06, .05), (.1, .1)], IRON, segments=8)      # collar, capped at .1
    K.revolve(g, (x, y, zl + .1), [(.08, 0), (.08, .13)], GLOW, segments=8)            # lit glass
    K.revolve(g, (x, y, zl + .23), [(.11, 0), (.11, .03), (.001, .11)], IRON, segments=8)  # hood
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        g.box((x + math.cos(a) * .088, y + math.sin(a) * .088, zl + .165), (.02, .02, .13), IRON)


# ---------------------------------------------------------------- animation

def animate(obj, kind, value, frame_end):
    """Custom kinds of the civic wellbeing studies.

    CUSTOM_YAW_OSC  value = (amplitude rad, cycles): sinusoidal swing about Z.
    CUSTOM_JET      value = (amplitude, cycles): water jet height pulse
                    (Z scale 1 +- amplitude about the part origin, slight
                    opposite XY breathing). Whole cycles close the loop.
    """
    span = frame_end - 1
    frames = list(range(1, frame_end, 4)) + [frame_end]
    if kind == 'CUSTOM_YAW_OSC':
        amp, cycles = value
        obj.rotation_mode = 'XYZ'
        for f in frames:
            t = (f - 1) / span
            obj.rotation_euler = (0, 0, amp * math.sin(2 * math.pi * cycles * t))
            obj.keyframe_insert(data_path='rotation_euler', frame=f)
    elif kind == 'CUSTOM_JET':
        amp, cycles = value
        for f in frames:
            t = (f - 1) / span
            s = math.sin(2 * math.pi * cycles * t) + .35 * math.sin(6 * math.pi * cycles * t)
            obj.scale = (1 - .05 * s, 1 - .05 * s, 1 + amp * s / 1.35)
            obj.keyframe_insert(data_path='scale', frame=f)
    else:
        raise ValueError('Unknown custom animation ' + kind)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
