"""Shared authoring kit for Deep Frontier late-game buildings.

See docs/art/lategame-style.md. Units: one Blender unit is one tile across and
one height layer up; X across, Y back, Z up, in the same artwork coordinates as
`frontier_architecture.Geometry`. Every helper keeps parallel surfaces at least
LAYER_GAP apart, or buries one of them inside a solid. Do not add depth bias or
post-hoc mesh cleanup to hide an overlap; fix the producing call instead.

Material slots follow the 35-slot late-game palette assembled in
`render_lategame_studies.py`: the 32-slot civic/research palette plus native
PaintedMetal.IronTeeth (32), BaseWood_Grey.IronTeeth (33) and
IrregularPlanks_Grey.IronTeeth (34). Use only native game materials for
surfaces (see NATIVE_SLOTS). GLOW and CYAN are allowed only as small emissive
accents (lamp bulbs, indicator lights).
"""
import math
from mathutils import Vector

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, SAND, LIME, GREY, BRASS
from reference_materials import (GLOW, GLASS, LEAF, WATER, CLOTH, CRUSHER_STEEL, KILN_STONE,
                                 KILN_SOOT, KILN_EMBER, KILN_FLAME, KILN_SHELL, KILN_RUST,
                                 CIVIC_CONCRETE, CIVIC_ORANGE_PANEL, CIVIC_FORGED_PANEL)
from industrial_facades import CYAN, RUBBER

CONCRETE = CIVIC_CONCRETE        # Plaster_White.IronTeeth: cast concrete
ORANGE = CIVIC_ORANGE_PANEL      # Plaster_Orange.IronTeeth: native infill
FORGED = CIVIC_FORGED_PANEL      # IrregularPlanks_MetalForged.IronTeeth: riveted sheet
WINDOW = 30                      # WindowsAtlas.IronTeeth (native window pieces only)
FOLK_WOOD = 31                   # BaseWood_Brown.Folktails (native rails)
PAINTED = 32                     # PaintedMetal.IronTeeth: painted machinery and tanks
GREYWOOD = 33                    # BaseWood_Grey.IronTeeth: weathered grey timber
GREYPLANK = 34                   # IrregularPlanks_Grey.IronTeeth: grey cladding
STEEL = IRON                     # Machined steel parts use native BaseMetal
DARK = IRON                      # Shadowed recesses use native dark metal

# Every slot here resolves to a shipped Timberborn material and texture.
NATIVE_SLOTS = {WOOD: 'BaseWood_DarkBrown.IronTeeth', PLANK: 'IrregularPlanks_DarkBrown.IronTeeth',
                IRON: 'BaseMetal.IronTeeth', ROOF: 'RoofPlanks.IronTeeth', BRASS: 'Details.IronTeeth',
                WATER: 'Water', CONCRETE: 'Plaster_White.IronTeeth', ORANGE: 'Plaster_Orange.IronTeeth',
                FORGED: 'IrregularPlanks_MetalForged.IronTeeth', WINDOW: 'WindowsAtlas.IronTeeth',
                FOLK_WOOD: 'BaseWood_Brown.Folktails', PAINTED: 'PaintedMetal.IronTeeth',
                GREYWOOD: 'BaseWood_Grey.IronTeeth', GREYPLANK: 'IrregularPlanks_Grey.IronTeeth'}
ACCENT_SLOTS = {GLOW, CYAN}   # Tiny emissive accents only; never broad surfaces.

LAYER_GAP = .012   # Minimum separation between parallel overlapping surfaces.

# Triangle budget (outputs/triangle-budget/, docs/art/lategame-style.md): the
# game keeps several mesh copies of every building's placement preview, so
# curved parts use few sides. Shapes are smooth-shaded by angle at build time
# (render_lategame_studies.py), so 16 sides read as round at game zoom.
GROUND_SINK = .03  # Inner solids start this far up, buried in their footing.
TRIM_PROUD = .02   # Minimum projection of trim, bands and plates from their host.


class shifted:
    """Author a group of existing calls moved by (dx, dy) in plan, e.g. an
    assembly pulled back inside the footprint when its yard was removed:

        with shifted(g, 0, .5):
            engine_yard_contents(g, parts)

    Every Geometry.add (any part) and every part pivot made inside the block
    moves, and so do emitters and native/dependency props recorded on `g`.
    """
    def __init__(self, g, dx, dy):
        self.g, self.dx, self.dy = g, dx, dy

    def __enter__(self):
        dx, dy = self.dx, self.dy
        self.add, self.init = add, init = Geometry.add, Geometry.__init__
        self.counts = {k: len(self._records(k)) for k in ('emitters', 'native_props', 'lategame_props')}

        def moved_add(geo, vertices, faces, mat):
            return add(geo, [(p[0] + dx, p[1] + dy, p[2]) for p in vertices], faces, mat)

        def moved_init(geo, name, origin=(0, 0, 0)):
            init(geo, name, (origin[0] + dx, origin[1] + dy, origin[2]))
        Geometry.add, Geometry.__init__ = moved_add, moved_init
        return self

    def _records(self, key):
        return self.g.native_props if key == 'native_props' else self.g.__dict__.setdefault(key, [])

    def __exit__(self, *exc):
        Geometry.add, Geometry.__init__ = self.add, self.init
        for key, start in self.counts.items():
            for record in self._records(key)[start:]:
                p = record['position']
                record['position'] = [p[0] + self.dx, p[1] + self.dy] + list(p[2:])
        return False


def _check_positive(*values, what='extent'):
    for v in values:
        if v <= 0:
            raise ValueError(f'Late-game kit requires a positive {what}, got {v}')


# ---------------------------------------------------------------- primitives

def oriented_polygon(g, points, normal, mat):
    """Planar polygon whose winding is chosen to face `normal` (Newell)."""
    n = [0.0, 0.0, 0.0]
    for (x0, y0, z0), (x1, y1, z1) in zip(points, points[1:] + points[:1]):
        n[0] += (y0 - y1) * (z0 + z1)
        n[1] += (z0 - z1) * (x0 + x1)
        n[2] += (x0 - x1) * (y0 + y1)
    if sum(a * b for a, b in zip(n, normal)) == 0:
        raise ValueError('Polygon is degenerate or edge-on to its intended normal')
    order = list(range(len(points)))
    if sum(a * b for a, b in zip(n, normal)) < 0:
        order.reverse()
    g.add(points, [tuple(order)], mat)


def hollow_revolve(g, center, profile, thickness, mat, *, segments=16, inner_mat=None):
    """Open-topped shell of revolution (towers, silos, stacks) with real wall
    thickness: outer face, inward-facing inner face and annular rims."""
    _check_positive(thickness)
    cx, cy, cz = center
    inner_mat = mat if inner_mat is None else inner_mat
    def ring(r, z):
        return [(cx + math.cos(i * 2 * math.pi / segments) * r,
                 cy + math.sin(i * 2 * math.pi / segments) * r, cz + z) for i in range(segments)]
    outer = [ring(r, z) for r, z in profile]
    inner = [ring(r - thickness, z) for r, z in profile]
    if any(r - thickness <= 0 for r, _ in profile):
        raise ValueError('Shell thickness exceeds its radius')
    for rows, m, outward in ((outer, mat, True), (inner, inner_mat, False)):
        base = len(g.vertices)
        verts = [p for row in rows for p in row]
        faces = []
        for k in range(len(rows) - 1):
            for i in range(segments):
                j = (i + 1) % segments
                q = (k * segments + i, k * segments + j, (k + 1) * segments + j, (k + 1) * segments + i)
                faces.append(q if outward else tuple(reversed(q)))
        g.add(verts, faces, m)
    for k, up in ((0, False), (len(profile) - 1, True)):
        for i in range(segments):
            j = (i + 1) % segments
            pts = [outer[k][i], outer[k][j], inner[k][j], inner[k][i]]
            oriented_polygon(g, pts, (0, 0, 1 if up else -1), mat)
    g.__dict__.setdefault('_revolves', []).append((cx, cy, [(r, cz + z) for r, z in profile], segments, 0.0))


def arch_infill(g, axis, plane, center, half, spring, rise, outward, mat, *, segments=12):
    """Closes the end of a barrel vault: a half-ellipse wall in its end plane."""
    pts = []
    for k in range(segments + 1):
        a = math.pi * k / segments
        u, z = center + math.cos(a) * half, spring + math.sin(a) * rise
        pts.append((plane, u, z) if axis == 'X' else (u, plane, z))
    normal = (outward, 0, 0) if axis == 'X' else (0, outward, 0)
    oriented_polygon(g, pts, normal, mat)


def revolve(g, center, profile, mat, *, segments=16, cap_bottom=True, cap_top=True, phase=0.0):
    """Closed surface of revolution about a vertical axis.

    `profile` is a list of (radius, z) pairs from bottom to top, with z rising
    strictly. A zero radius closes the surface at that point without a cap.
    Faces wind outward.
    """
    if len(profile) < 2:
        raise ValueError('Revolve profile needs at least two points')
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        if z1 <= z0:
            raise ValueError('Revolve profile z must rise strictly')
        if r0 < 0 or r1 < 0:
            raise ValueError('Revolve radius must be non-negative')
    cx, cy, cz = center
    n = segments
    verts = []
    rows = []
    for r, z in profile:
        if r == 0:
            rows.append([len(verts)] * n)
            verts.append((cx, cy, cz + z))
        else:
            row = []
            for i in range(n):
                a = phase + i * 2 * math.pi / n
                row.append(len(verts))
                verts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, cz + z))
            rows.append(row)
    faces = []
    for lower, upper in zip(rows, rows[1:]):
        for i in range(n):
            j = (i + 1) % n
            quad = [lower[i], lower[j], upper[j], upper[i]]
            unique = list(dict.fromkeys(quad))
            if len(unique) >= 3:
                faces.append(tuple(unique))
    if cap_bottom and profile[0][0] > 0:
        faces.append(tuple(reversed(rows[0])))
    if cap_top and profile[-1][0] > 0:
        faces.append(tuple(rows[-1]))
    g.add(verts, faces, mat)
    # Hosts for band(): a hoop must keep its faces clear of this surface.
    g.__dict__.setdefault('_revolves', []).append(
        (cx, cy, [(r, cz + z) for r, z in profile], n, phase))


def _host_radius(profile, z):
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        if z0 <= z <= z1 and z1 > z0:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return None


def band(g, center, r, z, height, mat=IRON, *, segments=16, proud=TRIM_PROUD, phase=0.0):
    """Solid hoop proud of a cylinder of radius r (its inner face is buried).

    The hoop's flat faces must clear its host: either the host revolve has
    the same side count and phase (nested polygons), or the hoop's apothem
    clears the host's circumscribed circle. Otherwise the host's corners
    would pierce the hoop; that fails here instead of in review.
    """
    cx, cy = center[0], center[1]
    hosts = [(n, ph) for hx, hy, prof, n, ph in g.__dict__.get('_revolves', [])
             if abs(hx - cx) < 1e-6 and abs(hy - cy) < 1e-6
             and any(abs((_host_radius(prof, zz) or -9) - r) < .003 for zz in (z - height / 2, z, z + height / 2))]
    nested = any(n == segments and abs(ph - phase) < 1e-9 for n, ph in hosts)
    if not nested and (r + proud) * math.cos(math.pi / segments) <= r + .002:
        raise ValueError(f'band at {tuple(center[:2])} z {z:.2f}: {segments} sides with proud {proud} cut into its '
                         f'radius-{r} host (host sides {[n for n, _ in hosts] or "unknown"})')
    revolve(g, center, [(r + proud, z - height / 2), (r + proud, z + height / 2)], mat, segments=segments,
            phase=phase)


def dome(g, center, r, mat, *, segments=16, rings=4, squash=1.0, base_z=0.0):
    """Hemispherical cap with its rim at center z + base_z."""
    profile = []
    for k in range(rings + 1):
        t = k / rings * math.pi / 2
        profile.append((r * math.cos(t), base_z + r * squash * math.sin(t)))
    profile[-1] = (0, profile[-1][1])
    revolve(g, center, profile, mat, segments=segments, cap_bottom=True, cap_top=False)


def extrude_profile(g, profile, start, end, mat, *, axis='Y', close=True):
    """Prism of a 2D (u, z) profile along X or Y, from `start` to `end`.

    For axis 'Y' the profile u is X; for axis 'X' the profile u is Y. List
    the profile counter-clockwise in (u, z) with u to the right and z up,
    for either axis. Concave profiles are allowed (end caps are n-gons).
    """
    if end <= start:
        raise ValueError('Extrusion must run toward increasing coordinate')
    if axis not in ('X', 'Y'):
        raise ValueError('Profile extrusion axis must be X or Y')
    n = len(profile)
    verts = []
    for t in (start, end):
        for u, z in profile:
            verts.append((u, t, z) if axis == 'Y' else (t, u, z))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        if not close and j == 0:
            continue
        faces.append((i, i + n, j + n, j) if axis == 'Y' else (i, j, j + n, i + n))
    if close:
        if axis == 'Y':
            faces.append(tuple(range(n)))
            faces.append(tuple(range(2 * n - 1, n - 1, -1)))
        else:
            faces.append(tuple(range(n - 1, -1, -1)))
            faces.append(tuple(range(n, 2 * n)))
    g.add(verts, faces, mat)


def stud(g, p, axis='Y', r=.022):
    """One six-sided steel bolt head, centred on its host face (half buried).

    Replaces Geometry.rivet (48 triangles) in late-game art: at game zoom a
    bolt head is one or two pixels, so a single hexagonal prism (20
    triangles, no bevel) reads the same.
    """
    g.cylinder(p, r * 1.2, .024, IRON, axis, 6)


def bolt_row(g, a, b, count, *, axis='Y', r=.022):
    """Evenly spaced bolt heads between two points, facing `axis`.

    (industrial_geometry.steel_bolt uses a custom steel slot; avoid it here.)
    """
    for i in range(count):
        t = (i + .5) / count
        stud(g, tuple(a[k] + (b[k] - a[k]) * t for k in range(3)), axis, r)


# ---------------------------------------------------------------- masonry

def plinth(g, x0, y0, x1, y1, top, *, coping=True, mat=CONCRETE, door=None):
    """Cast concrete podium: solid core, proud coping, recessed panel joints.

    `door` = (x_center, width, height) cuts a front (y0) opening and backs
    it with a dark recess; the native portal is added by the caller.
    """
    _check_positive(x1 - x0, y1 - y0, top)
    # Solid blocks start GROUND_SINK above ground, buried in the foot course,
    # so no two bottom faces share the ground plane.
    zb = GROUND_SINK
    if door is None:
        g.box(((x0 + x1) / 2, (y0 + y1) / 2, (zb + top) / 2), (x1 - x0, y1 - y0, top - zb), mat)
    else:
        dx, dw, dh = door
        left, right = dx - dw / 2, dx + dw / 2
        if left <= x0 or right >= x1 or dh >= top:
            raise ValueError('Plinth door must sit inside the plinth face')
        depth = y1 - y0
        g.box(((x0 + left) / 2, (y0 + y1) / 2, (zb + top) / 2), (left - x0, depth, top - zb), mat)
        g.box(((right + x1) / 2, (y0 + y1) / 2, (zb + top) / 2), (x1 - right, depth, top - zb), mat)
        g.box((dx, (y0 + y1) / 2, (dh + top) / 2), (dw, depth, top - dh), mat)
        g.box((dx, y0 + .25 + depth / 2, (zb + dh) / 2), (dw, depth - .5, dh - zb), mat)
        g.box((dx, y0 + .24, dh / 2), (dw - LAYER_GAP, .02, dh - LAYER_GAP), DARK)
    if coping:
        # Overhanging cap: proud on all sides and raised above the core top.
        g.box(((x0 + x1) / 2, (y0 + y1) / 2, top - .04 + LAYER_GAP / 2),
              (x1 - x0 + .08, y1 - y0 + .08, .08 + LAYER_GAP), mat)
        # Plinth foot: a slightly wider base course, buried below its top.
        # It stops short of a door so the native portal's sill owns the
        # ground plane there.
        if door is None:
            g.box(((x0 + x1) / 2, (y0 + y1) / 2, .06), (x1 - x0 + .05, y1 - y0 + .05, .12), mat)
        else:
            dl, dr = door[0] - .5 - LAYER_GAP, door[0] + .5 + LAYER_GAP
            for a, b in ((x0 - .025, dl), (dr, x1 + .025)):
                g.box(((a + b) / 2, (y0 + y1) / 2, .06), (b - a, y1 - y0 + .05, .12), mat)
            # Set back behind the portal's wall panels (no shared front plane).
            g.box(((dl + dr) / 2, (y0 + .03 + y1 + .025) / 2, .06), (dr - dl, y1 + .025 - y0 - .03, .12), mat)
    # Vertical shadow joints: proud pilaster strips at regular spacing.
    pitch = 1.0
    for x in _stations(x0, x1, pitch):
        if door is not None and abs(x - door[0]) < door[1] / 2 + .12:
            continue
        for y, s in ((y0, -1), (y1, 1)):
            g.box((x, y + s * .015, (top - .05) / 2 + .06), (.10, .03, top - .22), mat)
    for y in _stations(y0, y1, pitch):
        for x, s in ((x0, -1), (x1, 1)):
            g.box((x + s * .015, y, (top - .05) / 2 + .06), (.03, .10, top - .22), mat)


def _stations(a, b, pitch):
    count = max(1, round((b - a) / pitch))
    return [a + (b - a) * i / count for i in range(1, count)]


def concrete_pier(g, x, y, bottom, top, w=.36):
    """Square concrete pier with a steel bearing cap, for decks and frames."""
    _check_positive(top - bottom, w)
    g.box((x, y, (bottom + GROUND_SINK + top) / 2), (w, w, top - bottom - GROUND_SINK), CONCRETE)
    g.box((x, y, bottom + .06), (w + .06, w + .06, .12), CONCRETE)
    g.box((x, y, top + .025), (w + .05, w + .05, .05), IRON)


# ---------------------------------------------------------------- walls

def frame_wall(g, axis, plane, start, end, bottom, top, *, outward, infill=FORGED,
               bays=None, post=IRON, post_w=.16, windows=None, window_style='factory',
               window_scale=1.0, door=None):
    """Steel-framed wall: proud posts and rails, recessed infill, native windows.

    `axis` 'X' runs along X at y=plane; 'Y' runs along Y at x=plane.
    `outward` is -1 or +1 along the wall normal. `windows` is a list of
    (position_along, z) pairs. `door` is a position along the wall for a
    native one-tile portal at `bottom` (front/back walls only).
    """
    _check_positive(end - start, top - bottom)
    if outward not in (-1, 1):
        raise ValueError('Wall outward must be -1 or +1')
    length = end - start
    if bays is None:
        bays = max(1, round(length / 1.0))
    infill_t = .10
    # Infill sits behind the frame face; frame members project TRIM_PROUD+.
    def at(u, n, z):
        return (u, plane + n, z) if axis == 'X' else (plane + n, u, z)
    def size(du, dn, dz):
        return (du, dn, dz) if axis == 'X' else (dn, du, dz)
    # Infill panels between posts, cut around a door.
    door_lo = door_hi = None
    if door is not None:
        if axis != 'X':
            raise ValueError('frame_wall doors are authored on X-running walls')
        door_lo, door_hi = door - .5, door + .5
    for i in range(bays):
        a = start + i * length / bays
        b = start + (i + 1) * length / bays
        spans = [(a, b, bottom, top)]
        if door is not None and a < door_hi and b > door_lo:
            spans = []
            if a < door_lo:
                spans.append((a, door_lo, bottom, top))
            if b > door_hi:
                spans.append((door_hi, b, bottom, top))
            spans.append((max(a, door_lo), min(b, door_hi), bottom + 1, top))
        for lo, hi, zb, zt in spans:
            if hi - lo > .01 and zt - zb > .01:
                g.box(at((lo + hi) / 2, 0, (zb + zt) / 2), size(hi - lo, infill_t, zt - zb), infill)
    face = infill_t / 2
    # Posts and rails stand on the infill face (opposite-facing contact, no
    # shared same-facing plane); rails project .025 beyond the posts and run
    # .03 past the end posts so no end cap is coplanar with a post side.
    for i in range(bays + 1):
        u = start + i * length / bays
        if door is not None and door_lo - post_w / 2 < u < door_hi + post_w / 2:
            continue
        g.box(at(u, outward * (face + .035), (bottom + top) / 2),
              size(post_w, .07, top - bottom), post)
    # Rails run between the end posts so walls meeting at a corner never
    # share a rail plane; their end caps butt against the post sides.
    for z in (bottom + .06, top - .07):
        g.box(at((start + end) / 2, outward * (face + .0475), z),
              size(length - post_w, .095, .11), post)
    if door is not None:
        from industrial_facades import building_portal
        if axis != 'X' or outward != -1:
            raise ValueError('Portals are authored on front-facing X walls only')
        building_portal(g, door, plane - face - .12, bottom)
    if windows:
        from architectural_windows import window
        face_name = ({('X', -1): 'front', ('X', 1): 'back', ('Y', -1): 'left', ('Y', 1): 'right'})[(axis, outward)]
        for u, z in windows:
            wx, wy, _ = at(u, outward * face, z)
            window(g, wx, wy, z, window_scale, face_name, window_style)


def parapet(g, x0, y0, x1, y1, z, height=.35, mat=CONCRETE):
    """Closed parapet ring standing on a flat roof slab."""
    t = .14
    g.box(((x0 + x1) / 2, y0 + t / 2, z + height / 2), (x1 - x0, t, height), mat)
    g.box(((x0 + x1) / 2, y1 - t / 2, z + height / 2), (x1 - x0, t, height), mat)
    g.box((x0 + t / 2, (y0 + y1) / 2, z + height / 2), (t, y1 - y0 - 2 * t, height), mat)
    g.box((x1 - t / 2, (y0 + y1) / 2, z + height / 2), (t, y1 - y0 - 2 * t, height), mat)
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, z + height + .025), (x1 - x0 + .06, y1 - y0 + .06, .05), IRON)


def flat_roof(g, x0, y0, x1, y1, z, *, thickness=.16, overhang=.10, parapet_height=None):
    """Concrete roof slab; optional parapet ring."""
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, z + thickness / 2),
          (x1 - x0 + 2 * overhang, y1 - y0 + 2 * overhang, thickness), CONCRETE)
    if parapet_height:
        parapet(g, x0 - overhang, y0 - overhang, x1 + overhang, y1 + overhang, z + thickness, parapet_height)


# ---------------------------------------------------------------- roofs

def gable_roof(g, x0, y0, x1, y1, eave, ridge, *, ridge_axis='Y', overhang=.14, gable_mat=PLANK):
    """Teal native roof with closed gable ends, a steel ridge and plain fascia.

    Restraint is deliberate: one ridge cap, timber fascia, no corner plates.
    """
    _check_positive(ridge - eave)
    t = .07
    if ridge_axis == 'Y':
        mid = (x0 + x1) / 2
        lo, hi = y0 - overhang, y1 + overhang
        for side in (-1, 1):
            xe = x0 - overhang if side < 0 else x1 + overhang
            # Roof sheet as one thick sloped slab, extended past the eave.
            prof = [(xe, eave - .02), (mid, ridge), (mid, ridge + t), (xe, eave - .02 + t)]
            if side > 0:
                prof = list(reversed(prof))
            extrude_profile(g, prof, lo, hi, ROOF, axis='Y')
            # Fascia board tucked under the eave edge, inset behind it.
            g.box((xe - side * .05, (lo + hi) / 2, eave - .05), (.06, hi - lo, .12), WOOD)
        # Gable infill: triangle under the roof, just inside each roof end.
        for y in (y0, y1):
            g.add([(x0, y, eave), (x1, y, eave), (mid, y, ridge - .02)],
                  [(0, 1, 2) if y == y0 else (2, 1, 0)], gable_mat)
            g.add([(x0, y + (.08 if y == y0 else -.08), eave), (x1, y + (.08 if y == y0 else -.08), eave),
                   (mid, y + (.08 if y == y0 else -.08), ridge - .02)],
                  [(2, 1, 0) if y == y0 else (0, 1, 2)], gable_mat)
            for k in (0, 1):
                a = (x0, eave) if k == 0 else (x1, eave)
                vs = [(a[0], y, a[1]), (mid, y, ridge - .02),
                      (mid, y + (.08 if y == y0 else -.08), ridge - .02), (a[0], y + (.08 if y == y0 else -.08), a[1])]
                g.add(vs, [(0, 1, 2, 3) if (k == 0) == (y == y0) else (3, 2, 1, 0)], gable_mat)
            g.box((mid, y, (eave + ridge) / 2), (.10, .12, ridge - eave), WOOD)
        g.box((mid, (lo + hi) / 2, ridge + t + .03), (.14, hi - lo + .04, .07), IRON)
    elif ridge_axis == 'X':
        mid = (y0 + y1) / 2
        lo, hi = x0 - overhang, x1 + overhang
        for side in (-1, 1):
            ye = y0 - overhang if side < 0 else y1 + overhang
            prof = [(ye, eave - .02), (mid, ridge), (mid, ridge + t), (ye, eave - .02 + t)]
            if side > 0:
                prof = list(reversed(prof))
            extrude_profile(g, prof, lo, hi, ROOF, axis='X')
            g.box(((lo + hi) / 2, ye - side * .05, eave - .05), (hi - lo, .06, .12), WOOD)
        for x in (x0, x1):
            inward = .08 if x == x0 else -.08
            g.add([(x, y0, eave), (x, y1, eave), (x, mid, ridge - .02)],
                  [(2, 1, 0) if x == x0 else (0, 1, 2)], gable_mat)
            g.add([(x + inward, y0, eave), (x + inward, y1, eave), (x + inward, mid, ridge - .02)],
                  [(0, 1, 2) if x == x0 else (2, 1, 0)], gable_mat)
            for k in (0, 1):
                ay = y0 if k == 0 else y1
                vs = [(x, ay, eave), (x, mid, ridge - .02), (x + inward, mid, ridge - .02), (x + inward, ay, eave)]
                g.add(vs, [(3, 2, 1, 0) if (k == 0) == (x == x0) else (0, 1, 2, 3)], gable_mat)
            g.box((x, mid, (eave + ridge) / 2), (.12, .10, ridge - eave), WOOD)
        g.box(((lo + hi) / 2, mid, ridge + t + .03), (hi - lo + .04, .14, .07), IRON)
    else:
        raise ValueError('ridge_axis must be X or Y')


def barrel_roof(g, x0, y0, x1, y1, spring, rise, *, axis='Y', segments=12, ribs=4, overhang=.12):
    """Vaulted roof running along `axis`, with proud steel ribs and end arches."""
    _check_positive(rise)
    t = .08
    if axis == 'Y':
        cx, half = (x0 + x1) / 2, (x1 - x0) / 2 + overhang
        lo, hi = y0 - overhang, y1 + overhang
    else:
        cx, half = (y0 + y1) / 2, (y1 - y0) / 2 + overhang
        lo, hi = x0 - overhang, x1 + overhang
    outer, inner = [], []
    for k in range(segments + 1):
        a = math.pi * k / segments
        outer.append((cx + math.cos(a) * half, spring + math.sin(a) * rise))
        inner.append((cx + math.cos(a) * (half - t), spring + math.sin(a) * (rise - t)))
    prof = outer + list(reversed(inner))
    extrude_profile(g, prof, lo, hi, ROOF, axis=axis)
    for i in range(ribs + 1):
        s = lo + .1 + (hi - lo - .2) * i / ribs
        rib_out = [(cx + math.cos(math.pi * k / segments) * (half + .025),
                    spring + math.sin(math.pi * k / segments) * (rise + .025)) for k in range(segments + 1)]
        rib = rib_out + list(reversed(outer))
        extrude_profile(g, rib, s - .04, s + .04, IRON, axis=axis)


def sawtooth_roof(g, x0, y0, x1, y1, base, *, teeth=3, rise=.9, axis='X', glazing=True):
    """North-light factory roof: sloped teal sheets with glazed vertical faces."""
    _check_positive(teeth, rise)
    if axis != 'X':
        raise ValueError('Sawtooth teeth step along Y and run along X')
    depth = (y1 - y0) / teeth
    for i in range(teeth):
        ya, yb = y0 + i * depth, y0 + (i + 1) * depth
        prof = [(ya, base), (yb, base + rise), (yb, base + rise + .07), (ya, base + .07)]
        extrude_profile(g, prof, x0 - .08, x1 + .08, ROOF, axis='X')
        # Vertical north-light face at the high edge: forged sheet with a row
        # of native factory-grid windows seated on it.
        g.box(((x0 + x1) / 2, yb - .03, base + rise / 2), (x1 - x0, .06, rise - .02), FORGED)
        if glazing and rise >= .7:
            from architectural_windows import window
            for x in _stations(x0, x1, .9) or [(x0 + x1) / 2]:
                window(g, x, yb, base + rise / 2, min(1.0, (rise - .1) / .9), 'back', 'factory')
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, base - .04), (x1 - x0, y1 - y0, .08), CONCRETE)


# ---------------------------------------------------------------- steelwork

def lattice_tower(g, x0, y0, x1, y1, bottom, top, *, bays=None, w=.10, mat=IRON):
    """Four-legged steel tower with horizontal girts and alternating X bracing."""
    _check_positive(x1 - x0, y1 - y0, top - bottom)
    if bays is None:
        bays = max(1, round((top - bottom) / 1.2))
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for x, y in corners:
        g.box((x, y, (bottom + GROUND_SINK + top) / 2), (w, w, top - bottom - GROUND_SINK), mat)
        g.box((x, y, bottom + .04), (w + .12, w + .12, .08), CONCRETE)
    for k in range(bays + 1):
        z = bottom + (top - bottom) * k / bays
        for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
            inset = w / 2 + .01
            if ax == bx:
                g.box((ax, (ay + by) / 2, z), (w * .7, abs(by - ay) - 2 * inset, w * .7), mat)
            else:
                g.box(((ax + bx) / 2, ay, z), (abs(bx - ax) - 2 * inset, w * .7, w * .7), mat)
    for k in range(bays):
        za = bottom + (top - bottom) * k / bays
        zb = bottom + (top - bottom) * (k + 1) / bays
        for idx, ((ax, ay), (bx, by)) in enumerate(zip(corners, corners[1:] + corners[:1])):
            # Diagonals sit just outside the girt plane so they never coincide.
            nx = 0 if ax != bx else (-1 if ax == x0 else 1)
            ny = 0 if ay != by else (-1 if ay == y0 else 1)
            # Alternate bays stand LAYER_GAP further out: consecutive
            # diagonals meet at a joint, where their outer faces would share
            # a plane.
            off = w * .55 + (LAYER_GAP if k % 2 else 0)
            p = (ax + nx * off, ay + ny * off)
            q = (bx + nx * off, by + ny * off)
            if (k + idx) % 2:
                g.beam((p[0], p[1], za), (q[0], q[1], zb), w * .5, mat=mat)
            else:
                g.beam((q[0], q[1], za), (p[0], p[1], zb), w * .5, mat=mat)


def portal_frame(g, x0, x1, y, bottom, top, *, w=.18, mat=IRON):
    """Two steel columns and a lintel with knee braces, in the plane y."""
    _check_positive(x1 - x0, top - bottom)
    for x in (x0, x1):
        g.box((x, y, (bottom + GROUND_SINK + top) / 2), (w, w, top - bottom - GROUND_SINK), mat)
        concrete_pier(g, x, y, bottom, bottom + .3, w + .16)
    g.box(((x0 + x1) / 2, y, top + w / 2 + LAYER_GAP), (x1 - x0 + w, w * 1.1, w), mat)
    # Knee braces stop short of mid-span on narrow frames so they never meet.
    reach = min(.5, (x1 - x0) / 2 - w * .75)
    if reach > w:
        for x, s in ((x0, 1), (x1, -1)):
            g.beam((x + s * w / 2, y, top - .45), (x + s * reach, y, top), w * .5, mat=mat)


def steel_rail(g, a, b, z, *, height=.62, pitch=.6, mat=IRON, skip_ends=None,
               skip_start=False, skip_end=False):
    """Industrial handrail: square posts, top rail and mid rail."""
    a, b = Vector(a), Vector(b)
    count = max(1, math.ceil((b - a).length / pitch))
    for i in range(count + 1):
        if (i == 0 and skip_start) or (i == count and skip_end):
            continue
        p = a + (b - a) * i / count
        g.box((p.x, p.y, z + height / 2), (.05, .05, height), mat)
    # Top rail is 15 mm proud of the 50 mm posts; the mid rail is buried in them.
    for h, w in ((height, .08), (height * .5, .03)):
        g.beam((a.x, a.y, z + h), (b.x, b.y, z + h), w, mat=mat)


def catwalk(g, x0, y0, x1, y1, z, *, rails=('front', 'back', 'left', 'right'), brackets='wall',
            wall_side='back'):
    """Steel grating walkway at integer layer z with rails and support.

    `brackets` is 'wall' (knee brackets back to the `wall_side` face) or
    'piers' (concrete piers to the ground at the corners).
    """
    if z != int(z):
        raise ValueError('Catwalk floors sit on whole height layers')
    _check_positive(x1 - x0, y1 - y0)
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, z - .04), (x1 - x0, y1 - y0, .08), IRON)
    # Grating bars, proud of the deck top.
    span_x = x1 - x0 >= y1 - y0
    count = max(2, round((x1 - x0 if span_x else y1 - y0) / .24))
    for i in range(count):
        if span_x:
            x = x0 + (i + .5) * (x1 - x0) / count
            g.box((x, (y0 + y1) / 2, z + .006), (.03, y1 - y0 - .04, .012), STEEL)
        else:
            y = y0 + (i + .5) * (y1 - y0) / count
            g.box(((x0 + x1) / 2, y, z + .006), (x1 - x0 - .04, .03, .012), STEEL)
    inset = .035
    lines = {'front': ((x0 + inset, y0 + inset), (x1 - inset, y0 + inset)),
             'back': ((x0 + inset, y1 - inset), (x1 - inset, y1 - inset)),
             'left': ((x0 + inset, y0 + inset), (x0 + inset, y1 - inset)),
             'right': ((x1 - inset, y0 + inset), (x1 - inset, y1 - inset))}
    for name in rails:
        if name not in lines:
            raise ValueError('Unknown catwalk rail edge ' + name)
        a, b = lines[name]
        # Corner posts belong to the front/back runs only, so no two posts coincide.
        skip = name in ('left', 'right') and any(o in rails for o in ('front', 'back'))
        steel_rail(g, a, b, z, skip_ends=skip and 'both' or None,
                   skip_start='front' in rails if skip else False, skip_end='back' in rails if skip else False)
    if brackets == 'wall':
        if wall_side in ('back', 'front'):
            wy = y1 if wall_side == 'back' else y0
            oy = y0 if wall_side == 'back' else y1
            for x in [x0 + .15] + _stations(x0, x1, 1.2) + [x1 - .15]:
                g.beam((x, wy, z - .7), (x, oy + (.1 if wall_side == 'back' else -.1), z - .09), .07, mat=IRON)
        else:
            wx = x1 if wall_side == 'right' else x0
            ox = x0 if wall_side == 'right' else x1
            for y in [y0 + .15] + _stations(y0, y1, 1.2) + [y1 - .15]:
                g.beam((wx, y, z - .7), (ox + (.1 if wall_side == 'right' else -.1), y, z - .09), .07, mat=IRON)
    elif brackets == 'piers':
        for x, y in ((x0 + .2, y0 + .2), (x1 - .2, y0 + .2), (x1 - .2, y1 - .2), (x0 + .2, y1 - .2)):
            concrete_pier(g, x, y, 0, z - .135, .3)
    elif brackets is not None:
        raise ValueError('Catwalk support must be wall, piers or None')


def ladder(g, x, y, bottom, top, *, face='front', width=.36, cage=True):
    """Steel ladder with optional safety cage, standing off a wall."""
    _check_positive(top - bottom)
    n = {'front': (0, -1), 'back': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[face]
    t = (-n[1], n[0])
    off = .12
    for s in (-1, 1):
        p = (x + t[0] * s * width / 2 + n[0] * off, y + t[1] * s * width / 2 + n[1] * off)
        # Stiles stop LAYER_GAP short of the top: a ladder ends at a deck,
        # whose top face the stile tops would otherwise share.
        g.box((p[0], p[1], (bottom + top - LAYER_GAP) / 2), (.04, .04, top - bottom - LAYER_GAP), IRON)
    for k in range(int((top - bottom) / .25) + 1):
        z = bottom + .12 + k * .25
        if z > top - .05:
            break
        a = (x - t[0] * width / 2 + n[0] * off, y - t[1] * width / 2 + n[1] * off, z)
        b = (x + t[0] * width / 2 + n[0] * off, y + t[1] * width / 2 + n[1] * off, z)
        g.beam(a, b, .025, mat=STEEL)
    if cage and top - bottom > 1.6:
        for k in range(int((top - bottom - 1.2) / .6) + 1):
            z = bottom + 1.2 + k * .6
            pts = []
            for i in range(5):
                a = math.pi * i / 4
                pts.append((x + n[0] * off + t[0] * math.cos(a) * width * .75 + n[0] * math.sin(a) * width * .9,
                            y + n[1] * off + t[1] * math.cos(a) * width * .75 + n[1] * math.sin(a) * width * .9, z))
            for p, q in zip(pts, pts[1:]):
                g.beam(p, q, .025, mat=IRON)


# ---------------------------------------------------------------- vessels & services

def tank(g, x, y, bottom, r, height, *, mat=IRON, bands=3, roof='dome', legs=False, segments=16):
    """Riveted vertical tank on a concrete ring footing, banded, with a roof."""
    _check_positive(r, height)
    base = bottom
    if legs:
        for i in range(4):
            a = math.pi / 4 + i * math.pi / 2
            g.box((x + math.cos(a) * r * .75, y + math.sin(a) * r * .75, bottom + .45), (.14, .14, .9), IRON)
            g.box((x + math.cos(a) * r * .75, y + math.sin(a) * r * .75, bottom + .05), (.3, .3, .1), CONCRETE)
        base = bottom + .9
    else:
        revolve(g, (x, y, bottom), [(r + .1, 0), (r + .1, .22)], CONCRETE, segments=segments)
        base = bottom + .22
    revolve(g, (x, y, base), [(r, 0), (r, height)], mat, segments=segments, cap_bottom=legs)
    for k in range(bands):
        z = base + height * (k + .5) / bands
        band(g, (x, y, 0), r, z, .07, IRON if mat != IRON else PAINTED, segments=segments)
    top = base + height
    if roof == 'dome':
        dome(g, (x, y, top), r + .03, mat, segments=segments, squash=.45)
    elif roof == 'cone':
        revolve(g, (x, y, top), [(r + .04, 0), (r + .04, .04), (.08, r * .55), (0, r * .58)], ROOF, segments=segments)
    elif roof == 'flat':
        revolve(g, (x, y, top), [(r + .04, 0), (r + .04, .06)], IRON, segments=segments)
    else:
        raise ValueError('Tank roof must be dome, cone or flat')
    return top


# Vanilla particle effects at flue mouths (tools/vanilla_smoke.mjs maps each
# kind to a shipped prefab): 'smoke' combustion flues, 'steam' process and
# vapour stacks, 'towerSteam' cooling-tower mouths, 'fountainSpray' the
# vanilla Fountain of Joy water over that native fountain prop.
EMITTER_KINDS = ('smoke', 'steam', 'towerSteam', 'fountainSpray')


def emitter(g, kind, x, y, z, radius):
    """Record a vanilla smoke/steam emitter at a flue mouth (centre x, y; top
    z; mouth radius). Adds no geometry: render_lategame_studies.py writes the
    static art's emitters into the registration (smokeEmitters) and rejects
    emitters on animated parts, which would leave their plume behind."""
    if kind not in EMITTER_KINDS:
        raise ValueError(f'Unknown emitter kind {kind!r}; expected one of {EMITTER_KINDS}')
    _check_positive(radius, what='emitter radius')
    g.__dict__.setdefault('emitters', []).append(
        {'kind': kind, 'position': [round(x, 4), round(y, 4), round(z, 4)], 'radius': round(radius, 4)})


def stack(g, x, y, bottom, height, *, emits, r=.22, taper=.8, mat=IRON, bands=4):
    """Tapered riveted smokestack with sooted rim. `emits` is the vanilla
    effect at its mouth (an EMITTER_KINDS entry), or None for a vent stack
    that shows none; every caller decides explicitly."""
    _check_positive(height, r)
    if emits is not None and emits not in EMITTER_KINDS:
        raise ValueError(f'Unknown stack emitter {emits!r}')
    revolve(g, (x, y, bottom), [(r * 1.35, 0), (r * 1.35, .3), (r, .3001 + .01), (r * taper, height)], mat, segments=12)
    for k in range(bands):
        z = bottom + .5 + (height - .7) * k / max(1, bands - 1)
        rr = r + (r * taper - r) * (z - bottom) / height
        band(g, (x, y, 0), rr, z, .06, PAINTED, segments=12)
    rr = r * taper
    g.ring((x, y, bottom + height + .04), rr + .05, .07, .12, IRON, 'Z', 12)
    g.cylinder((x, y, bottom + height + .02), rr - .02, .02, DARK, 'Z', 12)
    if emits is not None:
        emitter(g, emits, x, y, bottom + height + .10, rr)   # top of the rim ring


def pipe_sides(r):
    """Side count for a round pipe of radius r (vanilla pipes use 6-12)."""
    return 8 if r < .3 else 12   # no 6: a flat top face would meet the next run coplanar at elbows


def pipe_run(g, points, r=.06, *, flanges=True, mat=IRON):
    """Orthogonal pipe with flanges near each joint and faceted elbows.

    Same layout as reference_details.round_pipe (open tubes between joints,
    a faceted knuckle at each bend), with pipe_sides(r) sides.
    """
    n = pipe_sides(r)
    for a, b in zip(points, points[1:]):
        a, b = Vector(a), Vector(b)
        rotation = (b - a).to_track_quat('Z', 'Y')
        verts = [p + rotation @ Vector((math.cos(i * 2 * math.pi / n) * r, math.sin(i * 2 * math.pi / n) * r, 0))
                 for p in (a, b) for i in range(n)]
        g.add(verts, [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)], IRON)
    for p in points[1:-1]:
        g.rock(p, (r * 2.22, r * 2.22, r * 2.22), IRON, 12)
    if not flanges:
        return
    for a, b in zip(points, points[1:]):
        axis = 'XYZ'[max(range(3), key=lambda i: abs(b[i] - a[i]))]
        length = math.dist(a, b)
        if length < .4:
            continue
        for f in (.18 / length, 1 - .18 / length):
            p = tuple(a[i] + (b[i] - a[i]) * f for i in range(3))
            g.ring(p, r * 1.6, r * .8, .05, BRASS, axis, n)


def valve_wheel(g, x, y, z, *, face='front', r=.14):
    """Hand wheel: a 10-sided rim, a hub and four spokes (Geometry.wheel's
    two 24-sided rims and eight spokes are 540 triangles for a few pixels)."""
    axis = 'Y' if face in ('front', 'back') else 'X'
    p = (x, y, z)
    g.ring(p, r, .045, .07, IRON, axis, 10)
    g.cylinder(p, .06, .14, BRASS, axis, 6)
    for i in range(4):
        a = i * math.pi / 2 + math.pi / 4
        end = ((x, y + math.cos(a) * (r - .03), z + math.sin(a) * (r - .03)) if axis == 'X'
               else (x + math.cos(a) * (r - .03), y, z + math.sin(a) * (r - .03)))
        g.beam(p, end, .04, mat=IRON)


def lamp(g, x, y, z, *, face='front'):
    """Caged bulkhead lamp bracketed off a wall."""
    n = {'front': (0, -1), 'back': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[face]
    g.beam((x, y, z + .14), (x + n[0] * .18, y + n[1] * .18, z + .14), .035, mat=IRON)
    g.cylinder((x + n[0] * .18, y + n[1] * .18, z), .065, .18, GLOW, 'Z', 8)
    g.ring((x + n[0] * .18, y + n[1] * .18, z), .075, .02, .04, IRON, 'Z', 8)


def beacon(g, x, y, z):
    """Static base and glass of a rotating warning beacon; returns shutter pivot."""
    revolve(g, (x, y, z), [(.12, 0), (.12, .06)], IRON, segments=8)
    revolve(g, (x, y, z + .06), [(.08, 0), (.08, .16)], CYAN, segments=8)
    revolve(g, (x, y, z + .22), [(.10, 0), (.10, .04), (0, .1)], IRON, segments=8)
    return (x, y, z + .14)


def beacon_shutter(x, y, z, name):
    """Rotating half-shroud around a beacon: animate with SPIN_Z."""
    s = Geometry(name, (x, y, z))
    for i in range(6):
        a0 = i * math.pi / 6
        a1 = (i + 1) * math.pi / 6
        r = .105
        s.add([(x + math.cos(a0) * r, y + math.sin(a0) * r, z - .085), (x + math.cos(a1) * r, y + math.sin(a1) * r, z - .085),
               (x + math.cos(a1) * r, y + math.sin(a1) * r, z + .085), (x + math.cos(a0) * r, y + math.sin(a0) * r, z + .085)],
              [(0, 1, 2, 3)], IRON)
    return s


def fan(g_name, x, y, z, r, *, axis='Z', blades=5, mat=IRON):
    """Separate animated fan rotor centred at (x,y,z): animate with SPIN_<axis>."""
    f = Geometry(g_name, (x, y, z))
    f.cylinder((x, y, z), r * .3, .1, STEEL, axis, 8)
    # Blades start inside the hub, clear of each other (no shared planes).
    width = min(r * .26, 2 * math.pi * r * .3 / blades * .8)
    for i in range(blades):
        a = i * 2 * math.pi / blades
        def at(rr):
            if axis == 'Z':
                return (x + math.cos(a) * rr, y + math.sin(a) * rr, z)
            if axis == 'Y':
                return (x + math.cos(a) * rr, y, z + math.sin(a) * rr)
            return (x, y + math.cos(a) * rr, z + math.sin(a) * rr)
        f.beam(at(r * .22), at(r), width, .025, mat)
    return f


def cable_tray(g, a, b, z, *, w=.16):
    """Steel cable tray on hangers between two plan points at height z."""
    g.beam((a[0], a[1], z), (b[0], b[1], z), w, .05, IRON)
    for p in (a, b):
        g.box((p[0], p[1], z + .2), (.04, .04, .4), IRON)
    for k in range(3):
        off = (k - 1) * .045
        g.beam((a[0], a[1] + off, z + .04), (b[0], b[1] + off, z + .04), .03, mat=PAINTED)


# ---------------------------------------------------------------- REDIC New Building Styles

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # tools/: dev_environment.py
import dev_environment as _dev
REDIC_ROOT = str(_dev.workshop() / '3723883597')
# Iron Teeth models in the required Redic.NewStyles 0.1 dependency. They use
# only shipped Iron Teeth materials. Runtime references the dependency's own
# resource; the preview imports the installed timbermesh read-only.
REDIC_MODELS = {
    'Lamp': 'Buildings/Decor/Lamp.Ironteeth',
    'Cyprus': 'Buildings/Decor/Cyprus.Ironteeth',
    'Stringlights1111': 'Buildings/Decor/Stringlights1111.Ironteeth',
    'Stringlights0011': 'Buildings/Decor/Stringlights0011.Ironteeth',
    'FlatRoof1x2': 'Buildings/Roofs/FlatRoof1x2.IronTeeth',
    'FlatRoof3x2': 'Buildings/Roofs/FlatRoof3x2.IronTeeth',
    'FlatRoof3x3': 'Buildings/Roofs/FlatRoof3x3.IronTeeth',
    'TubewayStop': 'Buildings/Tubeway/TubewayStop.IronTeeth',
    'Flat': 'Buildings/Flats/Flat.IronTeeth',
    'TallFlat': 'Buildings/Flats/TallFlat.IronTeeth',
    'WideFlat': 'Buildings/Flats/WideFlat.IronTeeth',
}


def redic_prop(g, name, model, position, scale=1.0, yaw=0):
    """Place a whole REDIC New Building Styles model as a native prop.

    `position` is the model origin in artwork coordinates (native models use a
    corner origin at their first occupied tile). Use sparingly for lamps,
    string lights and decor; whole REDIC buildings are scale references only.
    """
    if model not in REDIC_MODELS:
        raise ValueError('Unregistered REDIC model ' + model)
    props = g.__dict__.setdefault('lategame_props', [])
    if any(p['name'] == name for p in props):
        raise ValueError('Duplicate REDIC prop ' + name)
    props.append(dict(name=name, model=model, resource=REDIC_MODELS[model], dependency='Redic.NewStyles',
                      position=list(position), scale=scale, yaw=yaw))
