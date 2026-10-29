"""Shared parts for the Deep Frontier deep-mining chain.

Used by lategame_DeepDrill.py, lategame_DeepMine.py and lategame_DeepProcessor.py.
Artwork coordinates as in frontier_architecture.Geometry: X across, Y back, Z up,
one unit per tile and per height layer. Native material slots only.

Surface discipline (docs/art/lategame-style.md, zfight_audit.py --epsilon .004):
- Boxes that share volume never share a same-facing plane; stacked boxes meet
  exactly (opposite faces), so stacking is used in preference to burying.
- Only one face per plan area touches the ground (z = 0).
- Proud members keep >= 10 mm between parallel faces.

Kit workarounds (kit not edited; see the final review notes):
- lategame_kit.plinth / concrete_pier / lattice_tower put two overlapping faces
  on the ground plane, and steel_rail's top rail sits 2.5 mm off the post sides;
  fan blades are coplanar beyond the hub. Replacements live here.
- lategame_kit.gable_roof is one stretched board per slope (a single UV strip);
  plank_gable() builds separate native roof planks and boarded gables.
"""
import math
import random

from mathutils import Vector

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import (CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN,
                          oriented_polygon, extrude_profile, revolve, band)

EPS = 1e-6


# ------------------------------------------------------------------ basics

def bx(g, x0, x1, y0, y1, z0, z1, mat):
    """Axis-aligned box by bounds."""
    if x1 - x0 <= EPS or y1 - y0 <= EPS or z1 - z0 <= EPS:
        raise ValueError(f'Empty box x {x0:.3f}..{x1:.3f} y {y0:.3f}..{y1:.3f} z {z0:.3f}..{z1:.3f}')
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), mat)


def notched_block(g, x0, x1, y0, y1, z0, z1, mat, doors=(), depth=.08, door_h=1.0):
    """Solid block whose front (y0) face is notched for one-tile native portals.

    `doors` are (x_centre, bottom). The notch is `depth` deep; the native portal
    (industrial_facades.building_portal at y0 - .12) closes it.
    """
    cuts = sorted((dx - .5, dx + .5, zb) for dx, zb in doors if zb < z1 - EPS and zb + door_h > z0 + EPS)
    u = x0
    for a, b, zb in cuts:
        if a < x0 - EPS or b > x1 + EPS:
            raise ValueError('Door notch leaves the block face')
        if a > u + EPS:
            bx(g, u, a, y0, y1, z0, z1, mat)
        lo, hi = max(z0, zb), min(z1, zb + door_h)
        if lo > z0 + EPS:
            bx(g, a, b, y0, y1, z0, lo, mat)
        if hi < z1 - EPS:
            bx(g, a, b, y0, y1, hi, z1, mat)
        bx(g, a, b, y0 + depth, y1, lo, hi, mat)
        u = b
    if u < x1 - EPS:
        bx(g, u, x1, y0, y1, z0, z1, mat)


def plinth_course(g, x0, x1, y0, y1, z0, z1, mat, doors, *, proud=.05, door_z=None):
    """Concrete course proud of a core (x0..x1, y0..y1) on all sides, with door notches.

    industrial_facades.building_portal is an inward-facing recess occupying
    x +/- .5, y0 - .12..y0, door_z..door_z + 1. The course behind the wall plane
    is notched exactly at the portal edges (they only share an edge); its proud
    front lip keeps a 12 mm clearance from the portal's side and head panels so
    no two same-facing faces coincide.
    """
    door_z = z0 if door_z is None else door_z
    notched_block(g, x0 - proud, x1 + proud, y0, y1 + proud, z0, z1, mat, [(d, door_z) for d in doors], depth=.08)
    gap = .012
    u = x0 - proud
    for d in sorted(doors):
        a, b = d - .5 - gap, d + .5 + gap
        if a > u + EPS:
            bx(g, u, a, y0 - proud, y0, z0, z1, mat)
        if z1 > door_z + 1 + gap + EPS:
            bx(g, a, b, y0 - proud, y0, door_z + 1 + gap, z1, mat)
        u = b
    if u < x1 + proud - EPS:
        bx(g, u, x1 + proud, y0 - proud, y0, z0, z1, mat)


def portal(g, x, wall_y, bottom, *, record=True, ident=None):
    """Native one-tile Barrack door on a front-facing wall plane."""
    from industrial_facades import building_portal
    if abs((x % 1) - .5) > .01:
        raise ValueError('Doors are centred on a tile')
    building_portal(g, x, wall_y - .12, bottom)
    if record:
        g.doorways.append({'id': ident or f'Door{len(g.doorways)}', 'position': [x, round(wall_y - .12, 4), bottom],
                           'outward': [0, -1]})


def window(g, x, y, z, face, scale=.8, style='grand'):
    from architectural_windows import window as native_window
    native_window(g, x, y, z, scale, face, style)


# Face frames: u runs along the wall, n is the outward distance from its plane.
def _face(face, rect):
    x0, x1, y0, y1 = rect
    if face == 'front':
        return (lambda u, n, z: (u, y0 - n, z)), (lambda du, dn, dz: (du, dn, dz)), (x0, x1)
    if face == 'back':
        return (lambda u, n, z: (u, y1 + n, z)), (lambda du, dn, dz: (du, dn, dz)), (x0, x1)
    if face == 'left':
        return (lambda u, n, z: (x0 - n, u, z)), (lambda du, dn, dz: (dn, du, dz)), (y0, y1)
    if face == 'right':
        return (lambda u, n, z: (x1 + n, u, z)), (lambda du, dn, dz: (dn, du, dz)), (y0, y1)
    raise ValueError('Unknown face ' + face)


def face_member(g, face, rect, ua, ub, na, nb, za, zb, mat):
    at, size, _ = _face(face, rect)
    g.box(at((ua + ub) / 2, (na + nb) / 2, (za + zb) / 2), size(ub - ua, nb - na, zb - za), mat)


def wall_point(face, rect, u, n=0.0):
    at, _, _ = _face(face, rect)
    x, y, _ = at(u, n, 0)
    return x, y


# ------------------------------------------------------------------ native hall

def hall(g, x0, x1, y0, y1, top, *, z0=0.0, plinth=.45, infill=ORANGE, frame=WOOD,
         doors=(), windows=None, braces=None, rails=None, pitch=1.0, plinth_mat=CONCRETE,
         posts=('front', 'back', 'left', 'right'), post_skip=None, lamps=(), style='grand', wscale=.78,
         record_doors=True):
    """Iron Teeth timber-framed hall on a concrete plinth course.

    Opaque solid core with proud timber posts, rails and braces. `doors` are x
    positions on the front face (bottom z0). `windows`: {face: [(u, z), ...]}
    (`style`/`wscale` default, or (u, z, style, scale)). `braces`: {face: [(ua, ub)]}
    diagonal braces between plinth top and top plate. `rails`: extra rail heights.
    Returns the plinth top height.
    """
    rect = (x0, x1, y0, y1)
    zp = z0 + plinth
    # A recorded door stands on its whole layer; a decorative upper-floor door
    # is lifted 15 mm so the portal's threshold panel clears the floor below.
    dz = z0 if record_doors else z0 + .015
    plinth_course(g, x0, x1, y0, y1, z0, zp, plinth_mat, doors, door_z=dz)
    notched_block(g, x0, x1, y0, y1, zp, top, infill, [(d, dz) for d in doors], depth=.08)
    for d in doors:
        portal(g, d, y0, dz, record=record_doors)
    post_skip = post_skip or {}
    # Corner posts: square, proud of both faces, plinth top to top plate.
    for cx, cy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        bx(g, cx - .09, cx + .09, cy - .09, cy + .09, zp, top - .03, frame)
    rail_z = [zp + .09, top - .11] + list(rails or [])
    windows = windows or {}
    braces = braces or {}
    for face in posts:
        _, _, (ua, ub) = _face(face, rect)
        door_spans = [(d - .62, d + .62) for d in doors] if face == 'front' else []
        count = max(1, round((ub - ua) / pitch))
        for i in range(1, count):
            u = ua + (ub - ua) * i / count
            if any(a < u < b for a, b in door_spans) or any(abs(u - s) < .05 for s in post_skip.get(face, ())):
                continue
            face_member(g, face, rect, u - .07, u + .07, -.03, .06, zp, top - .03, frame)
        for z in rail_z:
            spans = [(ua + .05, ub - .05)]
            for a, b in door_spans:
                if z < z0 + 1.08:
                    spans = [piece for s in spans for piece in ((s[0], min(s[1], a)), (max(s[0], b), s[1]))
                             if piece[1] - piece[0] > .05]
            for a, b in spans:
                face_member(g, face, rect, a, b, -.02, .035, z - .05, z + .05, frame)
        for ua_b, ub_b in braces.get(face, ()):
            a = _face(face, rect)[0](ua_b, .02, zp + .12)
            b = _face(face, rect)[0](ub_b, .02, top - .16)
            g.beam(a, b, .05, .1, frame)
        for spec in windows.get(face, ()):
            u, z = spec[0], spec[1]
            st = spec[2] if len(spec) > 2 else style
            sc = spec[3] if len(spec) > 3 else wscale
            wx, wy = wall_point(face, rect, u)
            window(g, wx, wy, z, face, sc, st)
    for face, u, z in lamps:
        wx, wy = wall_point(face, rect, u)
        K.lamp(g, wx, wy, z, face=face)
    return zp


# ------------------------------------------------------------------ roofs

def plank_slope(g, ridge_axis, side, lo, hi, x_eave, z_eave, x_ridge, z_ridge, *, t=.07, width=.26,
                seed=0, battens=2, batten_mat=IRON):
    """One roof slope of separate native planks running eave to ridge.

    For ridge_axis 'Y', u is X and the slope runs from x_eave to x_ridge.
    """
    rng = random.Random(seed)
    n = max(1, round((hi - lo) / width))
    for i in range(n):
        a = lo + (hi - lo) * i / n
        b = lo + (hi - lo) * (i + 1) / n
        tt = t + rng.choice((0, .012, .022))
        prof = [(x_eave, z_eave), (x_ridge, z_ridge), (x_ridge, z_ridge + tt), (x_eave, z_eave + tt)]
        if (x_ridge - x_eave) < 0:
            prof = list(reversed(prof))
        extrude_profile(g, prof, a, b, ROOF, axis=ridge_axis)
    # Metal battens across the planks (proud of the thickest plank).
    top_t = t + .022
    for k in range(battens):
        f = (k + 1) / (battens + 1)
        u = x_eave + (x_ridge - x_eave) * f
        z = z_eave + (z_ridge - z_eave) * f + top_t
        slope = math.atan2(z_ridge - z_eave, abs(x_ridge - x_eave))
        dz = .03 / math.cos(slope)
        # Batten base follows the slope, seated 4 mm into the thickest planks.
        s = (z_ridge - z_eave) / (x_ridge - x_eave)
        prof = [(u - .05, z - .05 * s - .004), (u + .05, z + .05 * s - .004),
                (u + .05, z + .05 * s + dz), (u - .05, z - .05 * s + dz)]
        extrude_profile(g, prof, lo + .03, hi - .03, batten_mat, axis=ridge_axis)


def plank_gable(g, x0, x1, y0, y1, eave, ridge, *, ridge_axis='Y', overhang=.16, gable=True,
                gable_mat=PLANK, seed=0, ridge_cap=IRON, t=.07):
    """Native Iron Teeth plank roof: two slopes of planks, ridge cap, boarded gables."""
    if ridge_axis == 'Y':
        mid = (x0 + x1) / 2
        half = (x1 - x0) / 2
        lo, hi = y0 - overhang, y1 + overhang
    else:
        mid = (y0 + y1) / 2
        half = (y1 - y0) / 2
        lo, hi = x0 - overhang, x1 + overhang
    slope = (ridge - eave) / half
    ze = eave - slope * overhang
    a0 = (x0 if ridge_axis == 'Y' else y0) - overhang
    a1 = (x1 if ridge_axis == 'Y' else y1) + overhang
    plank_slope(g, ridge_axis, -1, lo, hi, a0, ze, mid, ridge, t=t, seed=seed)
    plank_slope(g, ridge_axis, 1, lo, hi, a1, ze, mid, ridge, t=t, seed=seed + 7)
    # Ridge cap.
    cap_z = ridge + t + .022
    if ridge_axis == 'Y':
        bx(g, mid - .09, mid + .09, lo - .02, hi + .02, cap_z - .03, cap_z + .05, ridge_cap)
    else:
        bx(g, lo - .02, hi + .02, mid - .09, mid + .09, cap_z - .03, cap_z + .05, ridge_cap)
    # Fascia boards under the eaves.
    for side, a in ((-1, a0), (1, a1)):
        f0, f1 = (a + .02, a + .08) if side < 0 else (a - .08, a - .02)
        if ridge_axis == 'Y':
            bx(g, f0, f1, lo, hi, ze - .12, ze - .005, WOOD)
        else:
            bx(g, lo, hi, f0, f1, ze - .12, ze - .005, WOOD)
    if gable:
        ends = (y0, y1) if ridge_axis == 'Y' else (x0, x1)
        for e, inward in ((ends[0], 1), (ends[1], -1)):
            boarded_gable(g, ridge_axis, e, inward, (x0, x1) if ridge_axis == 'Y' else (y0, y1),
                          eave, ridge, mat=gable_mat)


def boarded_gable(g, ridge_axis, plane, inward, span, eave, ridge, *, mat=PLANK, t=.07, width=.22):
    """Vertical boards closing a gable end; their outer face lies on `plane`."""
    a, b = span
    mid = (a + b) / 2
    half = (b - a) / 2
    slope = (ridge - eave) / half
    n = max(2, round((b - a) / width))
    def zr(u):
        return ridge - slope * abs(u - mid) - .015
    edge = .03 / slope
    for i in range(n):
        ua = max(a + edge, a + (b - a) * i / n)
        ub = min(b - edge, a + (b - a) * (i + 1) / n)
        prof = [(ua, eave), (ub, eave), (ub, zr(ub))]
        if ua + 1e-4 < mid < ub - 1e-4:
            prof.append((mid, zr(mid)))
        prof.append((ua, zr(ua)))
        start, end = (plane, plane + t) if inward > 0 else (plane - t, plane)
        # extrude_profile wants (u, z) counter-clockwise with u to the right.
        # Ridge along Y: gable in the X-Z plane, boards extruded through Y.
        extrude_profile(g, prof, start, end, mat, axis='Y' if ridge_axis == 'Y' else 'X')
    # King post and collar tie, proud of the boards.
    out = -1 if inward > 0 else 1
    if ridge_axis == 'Y':
        y_a, y_b = sorted((plane, plane + out * .05))
        bx(g, mid - .06, mid + .06, y_a, y_b, eave + .01, ridge - .08, WOOD)
        bx(g, a + .1, b - .1, y_a - (.012 if out < 0 else 0), y_b + (.012 if out > 0 else 0),
           eave + .02, eave + .14, WOOD)
    else:
        x_a, x_b = sorted((plane, plane + out * .05))
        bx(g, x_a, x_b, mid - .06, mid + .06, eave + .01, ridge - .08, WOOD)
        bx(g, x_a - (.012 if out < 0 else 0), x_b + (.012 if out > 0 else 0), a + .1, b - .1,
           eave + .02, eave + .14, WOOD)


def lean_to(g, x0, x1, y0, y1, z_low, z_high, *, low_side='front', overhang=.12, seed=0):
    """Mono-pitch plank roof. `low_side` is the eave side ('front','back','left','right')."""
    if low_side in ('front', 'back'):
        lo, hi = x0 - overhang, x1 + overhang
        if low_side == 'front':
            ae, ar = y0 - overhang, y1 + overhang
        else:
            ae, ar = y1 + overhang, y0 - overhang
        s = (z_high - z_low) / (y1 - y0)
        plank_slope(g, 'X', 0, lo, hi, ae, z_low - s * overhang, ar, z_high + s * overhang, seed=seed, battens=1)
    else:
        lo, hi = y0 - overhang, y1 + overhang
        if low_side == 'left':
            ae, ar = x0 - overhang, x1 + overhang
        else:
            ae, ar = x1 + overhang, x0 - overhang
        s = (z_high - z_low) / (x1 - x0)
        plank_slope(g, 'Y', 0, lo, hi, ae, z_low - s * overhang, ar, z_high + s * overhang, seed=seed, battens=1)


def flat_roof(g, x0, x1, y0, y1, z, *, t=.16, overhang=.08, parapet=.3, pt=.14, coping=IRON):
    """Concrete roof slab with an open parapet ring and steel coping."""
    a0, a1, b0, b1 = x0 - overhang, x1 + overhang, y0 - overhang, y1 + overhang
    bx(g, a0, a1, b0, b1, z, z + t, CONCRETE)
    if not parapet:
        return z + t
    zt = z + t
    bx(g, a0, a1, b0, b0 + pt, zt, zt + parapet, CONCRETE)
    bx(g, a0, a1, b1 - pt, b1, zt, zt + parapet, CONCRETE)
    bx(g, a0, a0 + pt, b0 + pt, b1 - pt, zt, zt + parapet, CONCRETE)
    bx(g, a1 - pt, a1, b0 + pt, b1 - pt, zt, zt + parapet, CONCRETE)
    zc = zt + parapet
    c = .02
    bx(g, a0 - c, a1 + c, b0 - c, b0 + pt + c, zc, zc + .05, coping)
    bx(g, a0 - c, a1 + c, b1 - pt - c, b1 + c, zc, zc + .05, coping)
    bx(g, a0 - c, a0 + pt + c, b0 + pt + c, b1 - pt - c, zc, zc + .05, coping)
    bx(g, a1 - pt - c, a1 + c, b0 + pt + c, b1 - pt - c, zc, zc + .05, coping)
    return zt


# ------------------------------------------------------------------ concrete & steel

def pier(g, x, y, z0, z1, w=.4, *, cap=True, mat=CONCRETE):
    """Concrete pier: wider footing course, shaft, steel bearing plate."""
    bx(g, x - w / 2 - .06, x + w / 2 + .06, y - w / 2 - .06, y + w / 2 + .06, z0, z0 + .14, mat)
    bx(g, x - w / 2, x + w / 2, y - w / 2, y + w / 2, z0 + .14, z1, mat)
    if cap:
        bx(g, x - w / 2 - .03, x + w / 2 + .03, y - w / 2 - .03, y + w / 2 + .03, z1, z1 + .05, IRON)
    return z1 + (.05 if cap else 0)


def column(g, x, y, z0, z1, w=.2, *, mat=IRON, base=True):
    """Steel column on a bolted base plate."""
    zb = z0
    if base:
        bx(g, x - w / 2 - .07, x + w / 2 + .07, y - w / 2 - .07, y + w / 2 + .07, z0, z0 + .05, IRON)
        for sx in (-1, 1):
            for sy in (-1, 1):
                K.stud(g, (x + sx * (w / 2 + .035), y + sy * (w / 2 + .035), z0 + .059), 'Z', .02)
        zb = z0 + .05
    bx(g, x - w / 2, x + w / 2, y - w / 2, y + w / 2, zb, z1, mat)


def rail(g, a, b, z, *, h=.62, pitch=.7, mat=IRON, skip_start=False, skip_end=False, dz=0.0):
    """Steel handrail: posts plus top and mid rails, faces >= 7 mm apart."""
    a, b = Vector(a), Vector(b)
    count = max(1, math.ceil((b - a).length / pitch))
    for i in range(count + 1):
        if (i == 0 and skip_start) or (i == count and skip_end):
            continue
        p = a + (b - a) * i / count
        bx(g, p.x - .03, p.x + .03, p.y - .03, p.y + .03, z, z + h, mat)
    for zz, w in ((z + h - .005 + dz, .045), (z + h * .5 + dz, .035)):
        g.beam((a.x, a.y, zz), (b.x, b.y, zz), w, mat=mat)


def deck(g, x0, x1, y0, y1, z, *, t=.08, rails=('front', 'back', 'left', 'right'), gaps=None,
         bars=True, mat=IRON, rail_h=.62):
    """Steel grating deck at whole layer z with handrails on the listed edges.

    `gaps`: {edge: [(u0, u1)]} leaves rail openings (ladder heads, bridges).
    """
    bx(g, x0, x1, y0, y1, z - t, z, mat)
    if bars:
        along_x = (x1 - x0) >= (y1 - y0)
        if along_x:
            n = max(2, int((y1 - y0 - .08) / .2))
            for i in range(n):
                y = y0 + .04 + (y1 - y0 - .08) * (i + .5) / n
                bx(g, x0 + .04, x1 - .04, y - .015, y + .015, z, z + .012, IRON)
        else:
            n = max(2, int((x1 - x0 - .08) / .2))
            for i in range(n):
                x = x0 + .04 + (x1 - x0 - .08) * (i + .5) / n
                bx(g, x - .015, x + .015, y0 + .04, y1 - .04, z, z + .012, IRON)
    gaps = gaps or {}
    i = .04
    runs = {'front': ((x0 + i, y0 + i), (x1 - i, y0 + i), 0), 'back': ((x0 + i, y1 - i), (x1 - i, y1 - i), 0),
            'left': ((x0 + i, y0 + i), (x0 + i, y1 - i), 1), 'right': ((x1 - i, y0 + i), (x1 - i, y1 - i), 1)}
    for name in rails:
        a, b, side = runs[name]
        has_front = 'front' in rails
        has_back = 'back' in rails
        pieces = [(0.0, 1.0)]
        length = (Vector(b) - Vector(a)).length
        for g0, g1 in gaps.get(name, ()):
            # gap positions in absolute u along the run's axis
            ua = (a[0] if side == 0 else a[1])
            t0, t1 = (g0 - ua) / length, (g1 - ua) / length
            pieces = [p for s in pieces for p in ((s[0], min(s[1], t0)), (max(s[0], t1), s[1])) if p[1] - p[0] > .02]
        for t0, t1 in pieces:
            pa = Vector(a) + (Vector(b) - Vector(a)) * t0
            pb = Vector(a) + (Vector(b) - Vector(a)) * t1
            ss = side == 1 and t0 == 0 and has_front
            se = side == 1 and t1 == 1 and has_back
            rail(g, pa, pb, z + .012 if bars else z, h=rail_h, skip_start=ss, skip_end=se,
                 dz=-.011 if side == 1 else 0)


def bracket(g, wall_pt, deck_pt, w=.07):
    """Single diagonal steel knee bracket from a wall to a deck underside."""
    g.beam(wall_pt, deck_pt, w, mat=IRON)


def slab_quad(g, pts, normal, t, mat):
    """Planar quad plate: outer face `pts` facing `normal`, thickness t inward."""
    n = Vector(normal).normalized()
    outer = [Vector(p) for p in pts]
    inner = [p - n * t for p in outer]
    c = sum(outer + inner, Vector()) / 8
    oriented_polygon(g, [tuple(p) for p in outer], tuple(n), mat)
    oriented_polygon(g, [tuple(p) for p in inner], tuple(-n), mat)
    for i in range(4):
        j = (i + 1) % 4
        quad = [outer[i], outer[j], inner[j], inner[i]]
        mid = sum(quad, Vector()) / 4
        oriented_polygon(g, [tuple(p) for p in quad], tuple(mid - c), mat)


# ------------------------------------------------------------------ machinery details

def gauge(g, x, y, z, face='front', r=.1):
    """Brass-bezelled pressure gauge: plaster dial, steel needle (no glass)."""
    n = {'front': (0, -1, 0), 'back': (0, 1, 0), 'left': (-1, 0, 0), 'right': (1, 0, 0)}[face]
    axis = 'Y' if n[1] else 'X'
    def p(d):
        return (x + n[0] * d, y + n[1] * d, z)
    g.cylinder(p(.024), r, .04, BRASS, axis, 8)
    g.cylinder(p(.047), r * .78, .014, CONCRETE, axis, 8)
    q = p(.058)
    if axis == 'Y':
        g.beam((q[0] - r * .1, q[1], q[2] - r * .1), (q[0] + r * .5, q[1], q[2] + r * .42), .008, .022, IRON)
    else:
        g.beam((q[0], q[1] - r * .1, q[2] - r * .1), (q[0], q[1] + r * .5, q[2] + r * .42), .008, .022, IRON)


def bolt_ring(g, c, r, count, axis, offset, rr=.02):
    """Rivet heads on a circle (flange bolts) facing +axis at `offset`."""
    for i in range(count):
        a = 2 * math.pi * (i + .5) / count
        if axis == 'X':
            p = (c[0] + offset, c[1] + math.cos(a) * r, c[2] + math.sin(a) * r)
        elif axis == 'Y':
            p = (c[0] + math.cos(a) * r, c[1] + offset, c[2] + math.sin(a) * r)
        else:
            p = (c[0] + math.cos(a) * r, c[1] + math.sin(a) * r, c[2] + offset)
        K.stud(g, p, axis, rr)


def spoked_wheel(name, c, r, axis='X', *, rim_t=.09, rim_w=.14, spokes=8, mat=IRON, hub_mat=PAINTED,
                 hub_r=.16, groove=True, accent=BRASS, double=False):
    """Separate animated spoked wheel (sheave, flywheel) centred on c."""
    w = Geometry(name, c)
    # 16 sides (22.5 degree facets, smooth-shaded) read round at game zoom.
    w.ring(c, r, rim_t, rim_w, mat, axis, 16)
    if groove:
        # Rope-groove flanges just proud of the rim faces.
        for s in (-1, 1):
            off = s * (rim_w / 2 + .012)
            pc = _along(c, axis, off)
            w.ring(pc, r + .05, .07, .024, accent, axis, 16)
    w.cylinder(c, hub_r, rim_w + .1, hub_mat, axis, 12)
    w.cylinder(c, hub_r * .55, rim_w + .16, IRON, axis, 12)
    planes = (-rim_w * .22, rim_w * .22) if double else (0,)
    for k in range(spokes):
        a = 2 * math.pi * k / spokes
        for off in planes:
            p0 = _radial(c, axis, a, hub_r - .02, off)
            p1 = _radial(c, axis, a, r - rim_t + .015, off)
            w.beam(p0, p1, .07 if not double else .045, .05, mat)
    return w


def _along(c, axis, d):
    i = 'XYZ'.index(axis)
    p = list(c)
    p[i] += d
    return tuple(p)


def _radial(c, axis, a, rr, off):
    if axis == 'X':
        return (c[0] + off, c[1] + math.cos(a) * rr, c[2] + math.sin(a) * rr)
    if axis == 'Y':
        return (c[0] + math.cos(a) * rr, c[1] + off, c[2] + math.sin(a) * rr)
    return (c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr, c[2] + off)


def rotor(name, c, r, axis='Z', blades=5, mat=IRON, pitch_w=.3):
    """Fan rotor whose blades start outside the hub (no coplanar blade overlap)."""
    f = Geometry(name, c)
    hub = r * .22
    f.cylinder(c, hub, .14, PAINTED, axis, 12)
    for i in range(blades):
        a = 2 * math.pi * i / blades
        p0 = _radial(c, axis, a, hub - .01, 0)
        p1 = _radial(c, axis, a, r, 0)
        f.beam(p0, p1, r * pitch_w, .03, mat)
    return f


def ore_heap(g, cx, cy, z, rx, ry, *, h=.5, mats=(IRON,), seed=1, count=None, base_mat=None):
    """Lumpy Deep Ore pile: a low irregular mound buried under many lumps."""
    rng = random.Random(seed)
    base_mat = base_mat if base_mat is not None else mats[0]
    segs = 14
    rings = [(1.0, 0.0), (.78, h * .32), (.45, h * .55), (.15, h * .62)]
    verts = []
    for f, dz in rings:
        for i in range(segs):
            a = 2 * math.pi * i / segs
            j = 1 + rng.uniform(-.08, .08) if f < 1 else 1
            verts.append((cx + math.cos(a) * rx * f * j, cy + math.sin(a) * ry * f * j, z + dz))
    faces = []
    for k in range(len(rings) - 1):
        for i in range(segs):
            j = (i + 1) % segs
            # Jittered rings make these quads non-planar: author them as
            # two planar triangles (same triangles as before) so the exact
            # enclosed-face cull tests the surface that is actually drawn.
            faces.append((k * segs + i, k * segs + j, (k + 1) * segs + j))
            faces.append((k * segs + i, (k + 1) * segs + j, (k + 1) * segs + i))
    faces.append(tuple(range(3 * segs, 4 * segs)))
    faces.append(tuple(reversed(range(segs))))
    g.add(verts, faces, base_mat)
    count = count or max(10, int(rx * ry * 40))
    for i in range(count):
        a = rng.uniform(0, 2 * math.pi)
        d = math.sqrt(rng.uniform(0, 1)) * .9
        surface = z + h * .62 * max(0.0, 1 - d ** 1.5)
        s = rng.uniform(.16, .32) * (1.15 - .4 * d)
        sz = s * rng.uniform(.6, .85)
        zc = max(surface + s * .12, z + .46 * sz + .005) + i * .0007
        g.rock((cx + math.cos(a) * rx * d, cy + math.sin(a) * ry * d, zc),
               (s, s * rng.uniform(.75, 1), sz), rng.choice(mats), seed * 1000 + i)


def track(g, a, b, *, z=0.0, gauge_w=.5, sleepers=True):
    """Mine rail track along X or Y on a concrete ballast strip."""
    ax = 'X' if abs(b[0] - a[0]) > abs(b[1] - a[1]) else 'Y'
    if ax == 'X':
        x0, x1 = sorted((a[0], b[0]))
        y = a[1]
        bx(g, x0, x1, y - .42, y + .42, z, z + .05, CONCRETE)
        n = max(2, int((x1 - x0) / .36))
        for i in range(n):
            x = x0 + (x1 - x0) * (i + .5) / n
            bx(g, x - .07, x + .07, y - .38, y + .38, z + .05, z + .1, WOOD)
        for s in (-1, 1):
            bx(g, x0 + .01, x1 - .01, y + s * gauge_w / 2 - .03, y + s * gauge_w / 2 + .03, z + .1, z + .17, IRON)
    else:
        y0, y1 = sorted((a[1], b[1]))
        x = a[0]
        bx(g, x - .42, x + .42, y0, y1, z, z + .05, CONCRETE)
        n = max(2, int((y1 - y0) / .36))
        for i in range(n):
            y = y0 + (y1 - y0) * (i + .5) / n
            bx(g, x - .38, x + .38, y - .07, y + .07, z + .05, z + .1, WOOD)
        for s in (-1, 1):
            bx(g, x + s * gauge_w / 2 - .03, x + s * gauge_w / 2 + .03, y0 + .01, y1 - .01, z + .1, z + .17, IRON)
    return z + .17


def ore_cart(g, x, y, z, *, axis='X', seed=3, full=True, body=PAINTED):
    """Riveted mine tub on four wheels; z is the rail top."""
    L, W, H = .8, .56, .42
    zb = z + .14
    if axis == 'X':
        prof = [(y - W / 2 + .05, zb), (y + W / 2 - .05, zb), (y + W / 2, zb + H), (y - W / 2, zb + H)]
        extrude_profile(g, list(reversed(prof)), x - L / 2, x + L / 2, body, axis='X')
        bx(g, x - L / 2 - .02, x + L / 2 + .02, y - W / 2 - .02, y + W / 2 + .02, zb + H - .06, zb + H + .012, IRON)
        for sx in (-.26, .26):
            for sy in (-1, 1):
                g.cylinder((x + sx, y + sy * .25, z + .09), .09, .05, IRON, 'Y', 12)
        bx(g, x - L / 2 + .06, x + L / 2 - .06, y - .2, y + .2, z + .06, zb, IRON)
    else:
        prof = [(x - W / 2 + .05, zb), (x + W / 2 - .05, zb), (x + W / 2, zb + H), (x - W / 2, zb + H)]
        extrude_profile(g, prof, y - L / 2, y + L / 2, body, axis='Y')
        bx(g, x - W / 2 - .02, x + W / 2 + .02, y - L / 2 - .02, y + L / 2 + .02, zb + H - .06, zb + H + .012, IRON)
        for sy in (-.26, .26):
            for sx in (-1, 1):
                g.cylinder((x + sx * .25, y + sy, z + .09), .09, .05, IRON, 'X', 12)
        bx(g, x - .2, x + .2, y - L / 2 + .06, y + L / 2 - .06, z + .06, zb, IRON)
    if full:
        rng = random.Random(seed)
        for i in range(7):
            s = rng.uniform(.14, .22)
            g.rock((x + rng.uniform(-.22, .22), y + rng.uniform(-.14, .14), zb + H - .02 + s * .12 + i * .003),
                   (s, s * .9, s * .7), rng.choice((IRON, IRON, BRASS)), seed * 100 + i)


def tube(g, a, b, r, mat=IRON, segs=8, caps=True):
    """Capped round tube between two points (pipes, drill pipe, rods)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    if d.length < 1e-5:
        raise ValueError('Zero-length tube')
    rot = d.to_track_quat('Z', 'Y')
    verts = [tuple(p + rot @ Vector((math.cos(i * 2 * math.pi / segs) * r, math.sin(i * 2 * math.pi / segs) * r, 0)))
             for p in (a, b) for i in range(segs)]
    faces = [(i, (i + 1) % segs, (i + 1) % segs + segs, i + segs) for i in range(segs)]
    if caps:
        faces.append(tuple(reversed(range(segs))))
        faces.append(tuple(range(segs, 2 * segs)))
    g.add(verts, faces, mat)


def ibeam(g, axis, a0, a1, c, z0, z1, w, *, mat=IRON, web=.36, flange=.06):
    """Steel I-beam along X or Y: stacked flanges and web (no shared planes)."""
    if axis == 'X':
        bx(g, a0, a1, c - w / 2, c + w / 2, z0, z0 + flange, mat)
        bx(g, a0, a1, c - w * web / 2, c + w * web / 2, z0 + flange, z1 - flange, mat)
        bx(g, a0, a1, c - w / 2, c + w / 2, z1 - flange, z1, mat)
    else:
        bx(g, c - w / 2, c + w / 2, a0, a1, z0, z0 + flange, mat)
        bx(g, c - w * web / 2, c + w * web / 2, a0, a1, z0 + flange, z1 - flange, mat)
        bx(g, c - w / 2, c + w / 2, a0, a1, z1 - flange, z1, mat)


def concrete_house(g, x0, x1, y0, y1, top, *, doors=(), windows=None, pitch=1.3, base=.3, style='factory',
                   wscale=.8, record_doors=True, z0=0.0):
    """Cast-concrete storey: base course, proud pilasters, native windows and doors."""
    plinth_course(g, x0, x1, y0, y1, z0, z0 + base, CONCRETE, doors)
    notched_block(g, x0, x1, y0, y1, z0 + base, top, CONCRETE, [(d, z0) for d in doors], depth=.08)
    for d in doors:
        portal(g, d, y0, z0, record=record_doors)
    rect = (x0, x1, y0, y1)
    for face in ('front', 'back', 'left', 'right'):
        _, _, (ua, ub) = _face(face, rect)
        count = max(1, round((ub - ua) / pitch))
        for i in range(count + 1):
            u = ua + (ub - ua) * i / count
            if face == 'front' and any(abs(u - d) < .66 for d in doors):
                continue
            if i in (0, count):
                # Corner pilasters belong to the front/back faces only.
                if face in ('left', 'right'):
                    continue
                u = ua + .06 if i == 0 else ub - .06
                face_member(g, face, rect, u - .12, u + .12, -.01, .05, z0 + base, top, CONCRETE)
                continue
            face_member(g, face, rect, u - .1, u + .1, -.01, .04, z0 + base, top, CONCRETE)
    for face, specs in (windows or {}).items():
        for spec in specs:
            u, z = spec[0], spec[1]
            wx, wy = wall_point(face, rect, u)
            window(g, wx, wy, z, face, spec[3] if len(spec) > 3 else wscale, spec[2] if len(spec) > 2 else style)


def frustum(g, top_rect, z_top, bot_rect, z_bot, mat):
    """Closed four-sided frustum (hopper bottoms, chute mouths); rects are (x0, x1, y0, y1)."""
    def ring(r, z):
        return [Vector((r[0], r[2], z)), Vector((r[1], r[2], z)), Vector((r[1], r[3], z)), Vector((r[0], r[3], z))]
    top, bot = ring(top_rect, z_top), ring(bot_rect, z_bot)
    c = sum(top + bot, Vector()) / 8
    oriented_polygon(g, [tuple(p) for p in top], (0, 0, 1 if z_top > z_bot else -1), mat)
    oriented_polygon(g, [tuple(p) for p in bot], (0, 0, -1 if z_top > z_bot else 1), mat)
    for i in range(4):
        j = (i + 1) % 4
        quad = [top[i], top[j], bot[j], bot[i]]
        mid = sum(quad, Vector()) / 4
        oriented_polygon(g, [tuple(p) for p in quad], tuple(mid - c), mat)


def boards(g, face, rect, z0, z1, *, width=.24, t=.06, mat=PLANK, u_range=None):
    """Vertical native boards proud of a solid core face (one board per UV strip)."""
    _, _, (ua, ub) = _face(face, rect)
    if u_range:
        ua, ub = u_range
    n = max(1, round((ub - ua) / width))
    for i in range(n):
        a = ua + (ub - ua) * i / n
        b = ua + (ub - ua) * (i + 1) / n
        face_member(g, face, rect, a, b, 0, t, z0, z1, mat)


def oriented_box(g, c, d, p, n, half, mat):
    """Box centred at c with orthonormal axes d, p, n and half extents (hd, hp, hn)."""
    c, d, p, n = Vector(c), Vector(d).normalized(), Vector(p).normalized(), Vector(n).normalized()
    hd, hp, hn = half
    corners = {}
    for sd in (-1, 1):
        for sp in (-1, 1):
            for sn in (-1, 1):
                corners[(sd, sp, sn)] = c + d * sd * hd + p * sp * hp + n * sn * hn
    for axis, vec in ((0, d), (1, p), (2, n)):
        for s in (-1, 1):
            quad_keys = []
            others = [i for i in range(3) if i != axis]
            for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                key = [0, 0, 0]
                key[axis] = s
                key[others[0]] = a
                key[others[1]] = b
                quad_keys.append(tuple(key))
            oriented_polygon(g, [tuple(corners[k]) for k in quad_keys], tuple(vec * s), mat)
