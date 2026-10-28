"""Shared parts for the Deep Frontier nuclear fuel chain (late-game studies).

Used by lategame_UraniumProcessingPlant, lategame_RadioactiveWasteRefinery and
lategame_RadioactiveWasteVault. Only native material slots (lategame_kit
NATIVE_SLOTS) plus tiny CYAN/GLOW accents. Every helper keeps parallel
surfaces at least LAYER_GAP apart or buries one inside a solid.

Artwork coordinates: X across, Y back, Z up; one unit is one tile / layer.
`face` names the outward normal of a wall-mounted part: front (-Y),
back (+Y), left (-X), right (+X).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
from lategame_kit import (stud, CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, CYAN, GLOW,
                          LAYER_GAP, TRIM_PROUD, revolve, band, dome, oriented_polygon,
                          extrude_profile, bolt_row)

NORMALS = {'front': (0, -1), 'back': (0, 1), 'left': (-1, 0), 'right': (1, 0)}


def bx(g, x0, y0, z0, x1, y1, z1, mat):
    """Axis-aligned box from its two corners."""
    if x1 <= x0 or y1 <= y0 or z1 <= z0:
        raise ValueError(f'Box needs positive extents: {(x0, y0, z0, x1, y1, z1)}')
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), mat)


class Facer:
    """Maps wall-local (u along the wall, v up, d outward) to artwork space."""

    def __init__(self, x, y, z, face):
        self.x, self.y, self.z = x, y, z
        self.n = NORMALS[face]
        self.t = (-self.n[1], self.n[0])
        self.face = face

    def p(self, u, v, d):
        return (self.x + self.t[0] * u + self.n[0] * d,
                self.y + self.t[1] * u + self.n[1] * d, self.z + v)

    def axis(self):
        return 'Y' if self.face in ('front', 'back') else 'X'

    def size(self, du, dv, dd):
        return (du, dd, dv) if self.face in ('front', 'back') else (dd, du, dv)

    def box(self, g, u, v, d, du, dv, dd, mat):
        """Box centred at local (u, v, d) with local extents."""
        g.box(self.p(u, v, d), self.size(du, dv, dd), mat)


def prism(g, f, poly, d0, d1, mat):
    """Extrude a CCW (u, v) polygon outward from depth d0 to d1 on Facer f."""
    if d1 <= d0:
        raise ValueError('Prism depth must increase outward')
    back = [f.p(u, v, d0) for u, v in poly]
    front = [f.p(u, v, d1) for u, v in poly]
    n3 = (f.n[0], f.n[1], 0)
    oriented_polygon(g, front, n3, mat)
    oriented_polygon(g, list(reversed(back)), (-n3[0], -n3[1], 0), mat)
    for i in range(len(poly)):
        j = (i + 1) % len(poly)
        du, dv = poly[j][0] - poly[i][0], poly[j][1] - poly[i][1]
        # Outward edge normal of a CCW polygon is (dv, -du) in (u, v).
        nu, nv = dv, -du
        normal = (f.t[0] * nu, f.t[1] * nu, nv)
        oriented_polygon(g, [back[i], back[j], front[j], front[i]], normal, mat)


def trefoil(g, x, y, z, *, face='front', r=.28):
    """Radiation warning sign: painted plate, orange disc, dark trefoil."""
    f = Facer(x, y, z, face)
    s = 2 * r + .12
    f.box(g, 0, 0, .02, s, s, .04, PAINTED)
    for u in (-s / 2 + .045, s / 2 - .045):
        for v in (-s / 2 + .045, s / 2 - .045):
            stud(g, f.p(u, v, .04 + .004), f.axis(), .018)
    # Orange disc proud of the plate.
    segs = 12
    disc = [(math.cos(i * 2 * math.pi / segs) * r, math.sin(i * 2 * math.pi / segs) * r) for i in range(segs)]
    prism(g, f, disc, .03, .06, ORANGE)
    # Three 60-degree blades and a hub, proud of the disc.
    ri, ro = r * .26, r * .86
    for k in range(3):
        a0 = math.pi / 2 + k * 2 * math.pi / 3 - math.pi / 6
        a1 = a0 + math.pi / 3
        outer = [(math.cos(a0 + (a1 - a0) * i / 5) * ro, math.sin(a0 + (a1 - a0) * i / 5) * ro) for i in range(6)]
        inner = [(math.cos(a1 - (a1 - a0) * i / 5) * ri, math.sin(a1 - (a1 - a0) * i / 5) * ri) for i in range(6)]
        prism(g, f, outer + inner, .05, .075, IRON)
    hub = [(math.cos(i * 2 * math.pi / 10) * r * .16, math.sin(i * 2 * math.pi / 10) * r * .16) for i in range(10)]
    prism(g, f, hub, .05, .075, IRON)


def gauge(g, x, y, z, *, face='front', r=.1):
    """Pressure gauge: iron body, white dial, brass bezel, cyan needle."""
    f = Facer(x, y, z, face)
    ax = f.axis()
    g.cylinder(f.p(0, 0, .04), r, .08, IRON, ax, 8)
    g.cylinder(f.p(0, 0, .087), r * .8, .014, CONCRETE, ax, 8)
    g.ring(f.p(0, 0, .085), r + .015, .035, .035, BRASS, ax, 8)
    g.beam(f.p(0, 0, .1), f.p(r * .5, r * .45, .1), .018, .012, CYAN)
    # Stem back to the pipe or wall it reads.
    g.beam(f.p(0, -r - .12, .04), f.p(0, -r + .02, .04), .035, mat=BRASS)


def drum(g, x, y, z, *, r=.19, h=.46, mat=PAINTED, lid=IRON):
    """Steel process drum (yellowcake), banded, with a lid ring."""
    revolve(g, (x, y, z), [(r, 0), (r, h)], mat, segments=10)
    for zz in (z + h * .28, z + h * .72):
        band(g, (x, y, 0), r, zz, .045, IRON, segments=10)
    revolve(g, (x, y, z + h), [(r + .015, 0), (r + .015, .03)], lid, segments=10)
    g.cylinder((x + r * .45, y, z + h + .045), .03, .03, BRASS, 'Z', 8)


def riveted_panel(g, f, u0, u1, v0, v1, d0, d1, mat=FORGED, *, rivets=True, pitch=.32):
    """Proud riveted plate on Facer f from (u0, v0) to (u1, v1)."""
    f.box(g, (u0 + u1) / 2, (v0 + v1) / 2, (d0 + d1) / 2, u1 - u0, v1 - v0, d1 - d0, mat)
    if not rivets:
        return
    n = max(2, round((u1 - u0) / pitch))
    for v in (v0 + .06, v1 - .06):
        bolt_row(g, f.p(u0, v, d1 + .004), f.p(u1, v, d1 + .004), n, axis=f.axis(), r=.019)


def hazard_stripes(g, f, u0, u1, v, d0, d1, *, height=.14, n=6):
    """Alternating orange and dark chevron band (proud blocks)."""
    w = (u1 - u0) / n
    for i in range(n):
        f.box(g, u0 + (i + .5) * w, v, (d0 + d1) / 2, w - .004 if i % 2 else w, height,
              d1 - d0 + (0 if i % 2 else .01), ORANGE if i % 2 == 0 else IRON)


def pipe_flange(g, p, r, axis):
    g.ring(p, r * 1.7, r * .9, .05, BRASS, axis, 8)


def straight_pipe(g, a, b, r=.07, *, mat=IRON, flanges=True, segments=8):
    """Axis-aligned cylindrical pipe between two points with end flanges."""
    axis = 'XYZ'[max(range(3), key=lambda i: abs(b[i] - a[i]))]
    length = abs(b['XYZ'.index(axis)] - a['XYZ'.index(axis)])
    mid = tuple((a[i] + b[i]) / 2 for i in range(3))
    g.cylinder(mid, r, length, mat, axis, segments)
    if flanges and length > .5:
        for t in (.12 / length, 1 - .12 / length):
            pipe_flange(g, tuple(a[i] + (b[i] - a[i]) * t for i in range(3)), r, axis)


def elbow(g, p, r):
    """Faceted ball joint at a pipe corner."""
    revolve(g, p, [(0, -r * 1.25), (r * 1.1, -r * .7), (r * 1.25, 0), (r * 1.1, r * .7), (0, r * 1.25)], IRON,
            segments=8)


def pipe_path(g, points, r=.07, *, mat=IRON, flanges=True):
    for a, b in zip(points, points[1:]):
        straight_pipe(g, a, b, r, mat=mat, flanges=flanges)
    for p in points[1:-1]:
        elbow(g, p, r)


def valve(g, p, r, axis, *, wheel_face='front'):
    """Inline gate valve body with a hand wheel on a short stem."""
    x, y, z = p
    g.box(p, (r * 2.6, r * 2.6, r * 2.6), PAINTED)
    if wheel_face == 'up':
        g.cylinder((x, y, z + r * 1.3 + .1), .025, .2, IRON, 'Z', 8)
        _flat_wheel(g, (x, y, z + r * 1.3 + .22), .13)
    else:
        n = NORMALS[wheel_face]
        stem_end = (x + n[0] * (r * 1.3 + .16), y + n[1] * (r * 1.3 + .16), z)
        g.beam((x + n[0] * r * 1.3, y + n[1] * r * 1.3, z), stem_end, .04, mat=IRON)
        g.wheel(stem_end, .13, 'Y' if wheel_face in ('front', 'back') else 'X', IRON, BRASS)


def _flat_wheel(g, p, r):
    """Hand wheel lying flat (axis Z)."""
    g.ring(p, r, .045, .05, IRON, 'Z', 16)
    g.cylinder(p, .05, .07, BRASS, 'Z', 8)
    for i in range(4):
        a = i * math.pi / 2
        g.beam(p, (p[0] + math.cos(a) * r * .92, p[1] + math.sin(a) * r * .92, p[2]), .035, mat=IRON)


def manipulator_port(g, x, y, z, *, face='front', reach=.55):
    """Hot-cell master-slave manipulator through a shield wall: brass ball
    joint in an iron port ring, two jointed arms and tongs hanging outside."""
    f = Facer(x, y, z, face)
    ax = f.axis()
    g.cylinder(f.p(0, 0, .03), .2, .06, IRON, ax, 16)
    g.ring(f.p(0, 0, .065), .215, .05, .05, BRASS, ax, 16)
    revolve_ball = [(0, -.11), (.09, -.07), (.11, 0), (.09, .07), (0, .11)]
    # Ball joint (revolved about local outward axis approximated by Z then placed).
    c = f.p(0, 0, .1)
    revolve(g, c, revolve_ball, IRON, segments=10)
    elbow_p = f.p(0, -.12, .1 + reach * .55)
    wrist = f.p(0, -.42, .1 + reach * .62)
    g.beam(c, elbow_p, .07, mat=IRON)
    g.beam(elbow_p, wrist, .055, mat=PAINTED)
    g.cylinder(elbow_p, .055, .1, BRASS, 'Z', 8)
    for s in (-1, 1):
        g.beam(wrist, f.p(s * .05, -.55, .1 + reach * .64), .025, mat=IRON)


def lit_window_slit(g, f, u, v, w, h, d):
    """Tiny warm lit slit (GLOW accent) set in a dark iron frame."""
    f.box(g, u, v, d + .01, w + .08, h + .08, .02, IRON)
    f.box(g, u, v, d + .025, w, h, .02, GLOW)


def battered_wall(g, axis, x0, x1, y_face, depth, z0, z1, batter, mat=CONCRETE, *, outward=-1):
    """Sloped (battered) retaining wall along X or Y.

    For axis 'X' the wall runs x0..x1; its outer face leans from y_face at
    z0 back by `batter` at z1, `outward` -1 (front) or +1 (back).
    """
    if axis == 'X':
        if outward == -1:
            prof = [(y_face, z0), (y_face + depth, z0), (y_face + depth, z1), (y_face + batter, z1)]
        else:
            prof = [(y_face - depth, z0), (y_face, z0), (y_face - batter, z1), (y_face - depth, z1)]
        extrude_profile(g, prof, x0, x1, mat, axis='X')
    else:
        if outward == -1:
            prof = [(y_face, z0), (y_face + depth, z0), (y_face + depth, z1), (y_face + batter, z1)]
        else:
            prof = [(y_face - depth, z0), (y_face, z0), (y_face - batter, z1), (y_face - depth, z1)]
        extrude_profile(g, prof, x0, x1, mat, axis='Y')


def plank_slope(g, prof, lo, hi, *, axis='X', pitch=.34, gap=.012, lift=.012, mat=ROOF):
    """Sloped roof sheet split into native-scale planks running down the slope.

    `prof` is the CCW (u, z) cross-section quad of the sheet, extruded along
    `axis` from lo to hi. Each plank is its own solid with its own atlas strip;
    alternate planks are lifted by `lift` so neighbouring tops never share a
    plane, and a `gap` seam separates their ends.
    """
    n = max(1, math.ceil((hi - lo) / pitch))
    w = (hi - lo) / n
    for i in range(n):
        a, b = lo + i * w + gap / 2, lo + (i + 1) * w - gap / 2
        dz = lift if i % 2 else 0.0
        extrude_profile(g, [(u, z + dz) for u, z in prof], a, b, mat, axis=axis)


def slope_quad(u0, z0, u1, z1, t):
    """CCW (u, z) quad of a sheet from (u0, z0) to (u1, z1), thickness t."""
    if u1 > u0:
        return [(u0, z0), (u1, z1), (u1, z1 + t), (u0, z0 + t)]
    return [(u1, z1), (u0, z0), (u0, z0 + t), (u1, z1 + t)]


def plank_gable(g, x0, y0, x1, y1, eave, ridge, *, overhang=.16, t=.08, gable_mat=PLANK, straps=2):
    """Native-style gable roof with its ridge along X: plank sheets, timber
    fascia, solid plank gable ends, iron ridge cap and cross straps."""
    mid = (y0 + y1) / 2
    k = (ridge - eave) / (mid - y0)
    ye0, ye1 = y0 - overhang, y1 + overhang
    ze = eave - overhang * k
    lo, hi = x0 - overhang, x1 + overhang
    plank_slope(g, slope_quad(ye0, ze, mid, ridge, t), lo, hi, axis='X')
    plank_slope(g, slope_quad(mid, ridge, ye1, ze, t), lo, hi, axis='X')
    for ye, s in ((ye0, -1), (ye1, 1)):
        bx(g, lo + .03, ye - .03 if s < 0 else ye - .03, ze - .1, hi - .03, ye + .03, ze + .015, WOOD)
    # Vertical board gable ends just inside the roof ends.
    for x in (x0, x1):
        board_gable(g, x, [(y0, mid, eave - .02, ridge - .05), (mid, y1, ridge - .05, eave - .02)], eave - .12,
                    mat=gable_mat)
        bx(g, x - .07, mid - .06, eave - .06, x + .07, mid + .06, ridge - .08, WOOD)
    bx(g, lo - .02, mid - .09, ridge + t - .02, hi + .02, mid + .09, ridge + t + .07, IRON)
    for j in range(straps):
        f = (j + 1) / (straps + 1)
        for s in (-1, 1):
            y = mid + s * (mid - ye0) * f
            z = ridge - (ridge - ze) * f + t + .012 + .03
            g.box(((lo + hi) / 2, y, z), (hi - lo - .06, .06, .05), IRON)


def board_gable(g, x, regions, bottom, *, pitch=.3, mat=PLANK, thick=(.08, .1)):
    """Gable or end wall of vertical boards in the plane x (normal along X).

    `regions` is a list of (ya, yb, za, zb): within ya..yb the board tops run
    linearly from za to zb. Each board is its own solid with its own atlas
    strip; alternate boards differ in thickness so their seams read.
    """
    k = 0
    for ya, yb, za, zb in regions:
        n = max(1, round((yb - ya) / pitch))
        for i in range(n):
            a = ya + (yb - ya) * i / n
            b = ya + (yb - ya) * (i + 1) / n
            ta = za + (zb - za) * (a - ya) / (yb - ya)
            tb = za + (zb - za) * (b - ya) / (yb - ya)
            if min(ta, tb) <= bottom + .01:
                raise ValueError('Board gable tops must clear the board bottom')
            t = thick[k % 2]
            k += 1
            extrude_profile(g, [(a, bottom), (b, bottom), (b, tb), (a, ta)], x - t / 2, x + t / 2, mat, axis='X')


def frustum(g, x0, y0, x1, y1, z0, z1, flare, mat=CONCRETE, *, top=True, bottom=True, flare_y=None):
    """Battered block: footprint x0..x1, y0..y1 at z1, widened by `flare` at z0."""
    fy = flare if flare_y is None else flare_y
    lo = [(x0 - flare, y0 - fy, z0), (x1 + flare, y0 - fy, z0), (x1 + flare, y1 + fy, z0), (x0 - flare, y1 + fy, z0)]
    hi = [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    if bottom:
        oriented_polygon(g, lo, (0, 0, -1), mat)
    if top:
        oriented_polygon(g, hi, (0, 0, 1), mat)
    for i, n in enumerate(((0, -1, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0))):
        j = (i + 1) % 4
        oriented_polygon(g, [lo[i], lo[j], hi[j], hi[i]], (n[0], n[1], .3), mat)


def obox(g, c, angle, su, sv, sz, mat):
    """Box rotated about Z by `angle`: local u along angle, v = z x u."""
    ux, uy = math.cos(angle), math.sin(angle)
    vx, vy = -uy, ux
    a, b, h = su / 2, sv / 2, sz / 2
    pts = []
    for dz in (-h, h):
        for du, dv in ((-a, -b), (a, -b), (a, b), (-a, b)):
            pts.append((c[0] + ux * du + vx * dv, c[1] + uy * du + vy * dv, c[2] + dz))
    g.add(pts, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], mat)


def board_wall(g, axis, plane, a0, a1, bottom, top_fn, *, pitch=.3, mat=PLANK, thick=(.08, .1)):
    """Vertical boards in a wall plane. axis 'X': plane is x, boards run along Y;
    axis 'Y': plane is y, boards run along X. top_fn(u) gives the top height;
    each board top is the chord between its edges."""
    n = max(1, round((a1 - a0) / pitch))
    for i in range(n):
        a = a0 + (a1 - a0) * i / n
        b = a0 + (a1 - a0) * (i + 1) / n
        ta, tb = top_fn(a), top_fn(b)
        if min(ta, tb) <= bottom + .01:
            raise ValueError('Board tops must clear the board bottom')
        t = thick[i % 2]
        extrude_profile(g, [(a, bottom), (b, bottom), (b, tb), (a, ta)], plane - t / 2, plane + t / 2, mat,
                        axis='X' if axis == 'X' else 'Y')


def plank_barrel(g, x0, x1, y0, y1, spring, rise, *, t=.08, overhang=.15, pitch=.32, ribs=3, end_boards=True):
    """Barrel vault along Y in native roof planks (each facet one plank run),
    with proud iron ribs and vertical board end walls under the arch."""
    cx, half = (x0 + x1) / 2, (x1 - x0) / 2 + overhang
    lo, hi = y0 - overhang, y1 + overhang
    arc = math.pi * (half + rise) / 2
    n = max(6, math.ceil(arc / pitch))
    zs = spring - overhang * .35

    def pt(k, dr):
        a = math.pi * k / n
        return (cx + math.cos(a) * (half + dr), zs + math.sin(a) * (rise + (spring - zs) + dr))
    for k in range(n):
        quad = [pt(k, -t), pt(k, 0), pt(k + 1, 0), pt(k + 1, -t)]
        area = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(quad, quad[1:] + quad[:1]))
        if area < 0:
            quad.reverse()
        extrude_profile(g, quad, lo, hi, ROOF, axis='Y')
    for i in range(ribs):
        s = lo + .25 + (hi - lo - .5) * i / max(1, ribs - 1)
        outer = [pt(k, .03) for k in range(n + 1)]
        inner = [pt(k, 0) for k in range(n + 1)]
        extrude_profile(g, outer + list(reversed(inner)), s - .045, s + .045, IRON, axis='Y')
    if end_boards:
        rr = rise + (spring - zs)

        def top(x):
            q = max(0.0, 1 - ((x - cx) / (half - t)) ** 2)
            return zs + (rr - t) * math.sqrt(q) - .02
        for y in (y0, y1):
            board_wall(g, 'Y', y, x0, x1, spring, top)


def ring_parapet(g, x0, y0, x1, y1, z, h, *, t=.16, mat=CONCRETE, cap=IRON):
    """Closed parapet ring with mitred iron caps (no lid over the roof)."""
    bx(g, x0, y0, z, x1, y0 + t, z + h, mat)
    bx(g, x0, y1 - t, z, x1, y1, z + h, mat)
    bx(g, x0, y0 + t, z, x0 + t, y1 - t, z + h, mat)
    bx(g, x1 - t, y0 + t, z, x1, y1 - t, z + h, mat)
    o = .03
    bx(g, x0 - o, y0 - o, z + h, x1 + o, y0 + t + .015, z + h + .05, cap)
    bx(g, x0 - o, y1 - t - .015, z + h, x1 + o, y1 + o, z + h + .05, cap)
    bx(g, x0 - o, y0 + t + .015, z + h, x0 + t + .015, y1 - t - .015, z + h + .05, cap)
    bx(g, x1 - t - .015, y0 + t + .015, z + h, x1 + o, y1 - t - .015, z + h + .05, cap)


def cask(g, x, y, z, *, r=.45, h=1.3, yoke=True):
    """Shielded transport cask with cooling fins, trunnions and lifting yoke.
    Returns the yoke top height (or the lid top without a yoke)."""
    revolve(g, (x, y, z), [(r, 0), (r, h)], PAINTED, segments=12)
    for k in range(12):
        a = k * math.pi / 6 + math.pi / 12
        obox(g, (x + math.cos(a) * (r + .045), y + math.sin(a) * (r + .045), z + h / 2), a, .11, .035, h - .36, IRON)
    for zz in (z + .1, z + h - .1):
        band(g, (x, y, 0), r, zz, .08, BRASS, segments=12)
    revolve(g, (x, y, z + h), [(r + .02, 0), (r + .02, .08), (r * .55, .13), (r * .55, .16)], IRON, segments=12)
    for s in (-1, 1):
        g.cylinder((x, y + s * (r + .06), z + h - .25), .09, .14, IRON, 'Y', 10)
    if not yoke:
        return z + h + .16
    for s in (-1, 1):
        bx(g, x - .07, y + s * (r + .13) - .03, z + h - .3, x + .07, y + s * (r + .13) + .03, z + h + .42, IRON)
    bx(g, x - .09, y - r - .19, z + h + .42, x + .09, y + r + .19, z + h + .56, PAINTED)
    bx(g, x - .12, y - .14, z + h + .56, x + .12, y + .14, z + h + .74, IRON)
    return z + h + .74
