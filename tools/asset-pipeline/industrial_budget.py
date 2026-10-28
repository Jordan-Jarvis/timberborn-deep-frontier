"""Triangle-budget detail kit for the industrial family.

CementKiln, ConcreteMixer, StoneCrusher, MineralQuarry and the two mineral
pits. Loading pre-builds a preview of every building and the prefab optimizer
keeps several copies of each mesh, so these models are held to about 40k
triangles (tools/asset-pipeline/triangle-budget.json, validate_triangle_budget.py).

The functions mirror the shared helpers in industrial_geometry.py and
reference_details.py with the same signatures, so a generator switches by
importing them from here. The shared helpers are unchanged: other families
still use them. What differs, by construction rather than by later repair:

- Shells, not solids. A fastener head has only its outward cap; a plate drops
  the face that lies on the member it is bolted to; a band drops its inner
  face, which lies inside the shell it wraps.
- Round parts use native-like side counts: 4 for small fastener heads, 6-8
  for pins, pipes and lamps, 12-24 for the large drums and tyres.
- Fewer fasteners (two per collar plate, not four), and no sub-centimetre
  scratches or chips: at game zoom those were sub-pixel, and the native
  atlases already paint wear and edge highlights.

No bevel modifier is used on these models (see BEVEL below): the native
Iron Teeth atlases paint their edge highlights, as vanilla meshes do.
"""
import math
import random
from mathutils import Vector
from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
from reference_materials import CRUSHER_STEEL, GLOW, WATER

# Scene models built with this kit. Their source meshes carry no bevel modifier.
MODELS = ('CementKiln', 'ConcreteMixer', 'StoneCrusher', 'MineralQuarry', 'SandstonePit', 'LimestonePit')
BEVEL = 0

_FACES = {'-z': (0, 3, 2, 1), '+z': (4, 5, 6, 7), '-y': (0, 1, 5, 4), '+x': (1, 2, 6, 5), '+y': (2, 3, 7, 6), '-x': (3, 0, 4, 7)}


def open_box(g, p, size, mat, skip=()):
    """Geometry.box without the faces in skip ('-x', '+z', ...): they lie on
    or inside another authored surface."""
    if not set(skip) <= set(_FACES):
        raise ValueError('Unknown box face: ' + str(skip))
    x, y, z = p
    a, b, c = [v / 2 for v in size]
    g.add([(x - a, y - b, z - c), (x + a, y - b, z - c), (x + a, y + b, z - c), (x - a, y + b, z - c),
           (x - a, y - b, z + c), (x + a, y - b, z + c), (x + a, y + b, z + c), (x - a, y + b, z + c)],
          [f for k, f in _FACES.items() if k not in skip], mat)


def prism(g, p, r, length, mat, axis='Z', n=8, caps=(True, True), r2=None, phase=0.0):
    """Geometry.cylinder with explicit side count, start angle and caps.
    caps=(negative end, positive end) along the axis."""
    if r2 is None:
        r2 = r

    def point(a, b, c):
        return ((p[0] + c, p[1] + a, p[2] + b) if axis == 'X' else
                (p[0] + a, p[1] + c, p[2] + b) if axis == 'Y' else (p[0] + a, p[1] + b, p[2] + c))
    v = [point(math.cos(phase + i * 2 * math.pi / n) * radius, math.sin(phase + i * 2 * math.pi / n) * radius, z)
         for radius, z in ((r, -length / 2), (r2, length / 2)) for i in range(n)]
    f = []
    if caps[0]:
        f.append(tuple(reversed(range(n))))
    if caps[1]:
        f.append(tuple(range(n, 2 * n)))
    f.extend((i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n))
    g.add(v, [tuple(reversed(face)) for face in f] if axis == 'Y' else f, mat)


def band(g, p, r, t, width, mat=IRON, axis='Z', segments=24, inner=False):
    """Geometry.ring without its inner face, which lies inside the wrapped
    shell (inner=True keeps it for a free-standing ring such as a hand wheel)."""
    def point(a, b, c):
        return ((p[0] + c, p[1] + a, p[2] + b) if axis == 'X' else
                (p[0] + a, p[1] + c, p[2] + b) if axis == 'Y' else (p[0] + a, p[1] + b, p[2] + c))
    n = segments
    v = [point(math.cos(i * 2 * math.pi / n) * radius, math.sin(i * 2 * math.pi / n) * radius, z)
         for radius, z in ((r, -width / 2), (r, width / 2), (r - t, -width / 2), (r - t, width / 2)) for i in range(n)]
    f = []
    for i in range(n):
        j = (i + 1) % n
        f.extend([(i, j, j + n, i + n), (i, i + 2 * n, j + 2 * n, j), (i + n, j + n, j + 3 * n, i + 3 * n)])
        if inner:
            f.append((i + 2 * n, i + 3 * n, j + 3 * n, j + 2 * n))
    g.add(v, [tuple(reversed(face)) for face in f] if axis == 'Y' else f, mat)


# Fastener style (head length, square heads set diagonally). SHARED keeps the
# steel_bolt nut's end planes (length .031) and axis-aligned square heads, as
# the other families import them. The industrial family uses INDUSTRIAL
# (industrial_kit.py): built without a bevel modifier, caps that stood 0.5 mm
# off a neighbouring face (the bevel had shrunk them below the z-fight
# audit's area) stand 3 mm clear at length .037, and diagonal square heads
# keep their sides out of the planes of the plates and beams around them.
FASTENERS_SHARED = (.031, False)
FASTENERS_INDUSTRIAL = (.037, True)


def bolt(g, p, axis='Y', r=.022, outward=None, n=6, *, fasteners=FASTENERS_SHARED):
    """One fastener head where steel_bolt had a 12-sided washer plus a 6-sided
    nut. Same centre as that nut, radius between the two. outward=+1/-1 keeps
    only the cap on that side of the axis: the other end is inside the plate."""
    length, diagonal = fasteners
    caps = (True, True) if outward is None else ((outward < 0), (outward > 0))
    phase = 0 if (n == 4 and diagonal) else math.pi / n
    prism(g, p, r * 1.3, length, CRUSHER_STEEL, axis, n, caps, phase=phase)


def steel_bolt(g, p, axis='Y', r=.022, *, fasteners=FASTENERS_SHARED):
    """Drop-in for industrial_geometry.steel_bolt (both caps: direction unknown)."""
    bolt(g, p, axis, r, fasteners=fasteners)


def square_nut(g, p, axis, r, outward, *, fasteners=FASTENERS_SHARED):
    bolt(g, p, axis, r, outward, n=4, fasteners=fasteners)


def bracket(g, x, y, z, w=.22, *, fasteners=FASTENERS_SHARED):
    """Folded corner collar: same four plates as industrial_geometry.bracket,
    two square nuts per plate (diagonal) instead of four round bolts. The
    plates' inner faces lie on the column; the Y plates' ends meet the X
    plates' inner faces."""
    for dx in (-1, 1):
        xx = x + dx * (w / 2 + .012)
        open_box(g, (xx, y, z), (.028, w + .052, .23), IRON, ('-x' if dx > 0 else '+x',))
        for dy, dz in ((-w * .30, -.068), (w * .30, .068)):
            square_nut(g, (xx + dx * .018, y + dy * dx, z + dz), 'X', .018, dx, fasteners=fasteners)
    for dy in (-1, 1):
        yy = y + dy * (w / 2 + .012)
        open_box(g, (x, yy, z), (w - .004, .028, .23), IRON, ('-y' if dy > 0 else '+y', '-x', '+x'))
        for dx, dz in ((-w * .30, -.068), (w * .30, .068)):
            square_nut(g, (x + dx * dy, yy + dy * .018, z + dz), 'Y', .018, dy, fasteners=fasteners)


def timber_column(g, x, y, bottom, top, w=.19, *, fasteners=FASTENERS_SHARED):
    g.box((x, y, (bottom + top) / 2), (w, w, top - bottom), WOOD)
    collar_levels = ((bottom + top) / 2,) if top - bottom < .46 else (bottom + .115, top - .115)
    for level in collar_levels:
        bracket(g, x, y, level, w, fasteners=fasteners)


def beam_joint(g, a, b, w=.18, depth=.18, *, fasteners=FASTENERS_SHARED):
    g.beam(a, b, w, depth, WOOD)
    span = math.dist(a, b)
    plate_stations = () if span < .30 else ((.5,) if span < .60 else (.12, .88))
    for t in plate_stations:
        p = tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
        if abs(b[0] - a[0]) >= abs(b[1] - a[1]):
            g.box((p[0], p[1] - .12, p[2]), (.27, .035, depth + .06), IRON)
            for dx in (-.075, .075):
                square_nut(g, (p[0] + dx, p[1] - .15, p[2]), 'Y', .022, -1, fasteners=fasteners)
        else:
            g.box((p[0] - .12, p[1], p[2]), (.035, .27, depth + .06), IRON)
            for dy in (-.075, .075):
                square_nut(g, (p[0] - .15, p[1] + dy, p[2]), 'X', .022, -1, fasteners=fasteners)


def sheet_roof(g, x0, y0, x1, y1, z0, z1, seed, *, fasteners=FASTENERS_SHARED):
    """industrial_geometry.sheet_roof: same panels, edging, straps and corner
    shoes; edge bolts on alternate panels; no 6 mm scratch slivers."""
    count = math.ceil((x1 - x0) / .28)
    slope = (z1 - z0) / (y1 - y0)
    for i in range(count):
        x = x0 + (i + .5) * (x1 - x0) / count
        g.beam((x, y0, z0), (x, y1, z1), (x1 - x0) / count, .045, ROOF)
        if i % 2 == 0:
            for t in (.08, .92):
                bolt(g, (x, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t + .035), 'Z', .015, 1, 4, fasteners=fasteners)
    for x in (x0, x1):
        g.beam((x, y0, z0 - .035), (x, y1, z1 - .035), .13, .14, WOOD)
    for y, z in ((y0, z0), (y1, z1)):
        g.beam((x0, y, z - .055), (x1, y, z - .055), .15, .16, WOOD)
        for x in (x0, x1):
            bracket(g, x, y, z - .07, .16, fasteners=fasteners)
            open_box(g, (x, y, z + .050), (.22, .22, .025), IRON, ('-z',))
            bolt(g, (x, y, z + .071), 'Z', .024, 1, fasteners=fasteners)
    for t in (.35, .72):
        y = y0 + (y1 - y0) * t
        z = z0 + (z1 - z0) * t + .03
        g.beam((x0, y, z), (x1, y, z), .06, .018, IRON)
        for x in (x0 + .08, x1 - .08):
            bolt(g, (x, y, z + .015), 'Z', .016, 1, 4, fasteners=fasteners)
    del slope, seed


def rock(g, p, size, mat, seed, n=6):
    """Rounded cobble: n-sided, three rings and a broad flat top (Geometry.rock
    is 7-sided with four rings)."""
    rng = random.Random(seed)
    v = []
    for z, factor in ((-.45, .72), (0, 1), (.43, .64)):
        for i in range(n):
            a = 2 * math.pi * (i + rng.uniform(-.12, .12)) / n
            jitter = rng.uniform(.86, 1.08)
            v.append((p[0] + math.cos(a) * size[0] * factor * jitter / 2,
                      p[1] + math.sin(a) * size[1] * factor * jitter / 2, p[2] + z * size[2]))
    # Jittered rings make non-planar quads and caps; author planar triangles
    # (the same triangles the export makes) so every face has one exact plane.
    f = [(0, i + 1, i) for i in range(1, n - 1)] + [(2 * n, 2 * n + i, 2 * n + i + 1) for i in range(1, n - 1)]
    for level in range(2):
        for i in range(n):
            a, b = level * n + i, level * n + (i + 1) % n
            f.extend([(a, b, b + n), (a, b + n, a + n)])
    g.add(v, f, mat)


def rock_heap(g, x0, y0, x1, y1, z, mat, seed, count, size=(.12, .24)):
    """A loose heap of chunky rocks on a surface at z (bins, hoppers)."""
    rng = random.Random(seed)
    for i in range(count):
        s = rng.uniform(*size)
        rock(g, (rng.uniform(x0, x1), rng.uniform(y0, y1), z + s * .3), (s, s * .9, s * .8), mat, seed * 100 + i)


def bin(g, p, size, stone=None, seed=0, *, proud_rivets=False, fasteners=FASTENERS_SHARED):
    """frontier_architecture.bin: same floor, side planks and corner irons;
    one square rivet per post face instead of two 14-sided rivets; a stone
    load of fewer, chunkier rocks."""
    x, y, z = p
    w, d, h = size
    rivet_offset = .058 if proud_rivets else .05
    rows = max(2, math.ceil(h / .15))
    g.box((x, y, z + .045), (w - .12, d - .12, .09), WOOD)
    for j in range(rows):
        level = z + (j + .5) * h / rows
        for xx in (x - w / 2 + .03, x + w / 2 - .03):
            g.box((xx, y, level), (.06, d - .12, h / rows - .01), PLANK)
        for yy in (y - d / 2 + .03, y + d / 2 - .03):
            g.box((x, yy, level), (w, .06, h / rows - .01), PLANK)
    for xx in (x - w / 2 + .055, x + w / 2 - .055):
        for yy in (y - d / 2 + .055, y + d / 2 - .055):
            g.box((xx, yy, z + h / 2), (.09, .09, h + .03), IRON)
            square_nut(g, (xx, yy - rivet_offset, z + h - .06), 'Y', .019 / 1.3, -1, fasteners=fasteners)
    if stone is not None:
        rock_heap(g, x - w * .35, y - d * .32, x + w * .35, y + d * .32, z + h * .80, stone, seed,
                  max(5, int(w * d * 9)), (.14, .26))


def cask(g, p, r=.43, h=1.0, water=False):
    """reference_details.cask: 12 tapered staves, three hoops, lid and rim.
    The 30 hoop rivets and four 9 mm lid slats were sub-pixel."""
    x, y, z = p
    n = 12
    levels = [(0, r * .88), (.13 * h, r * .96), (.50 * h, r), (h * .87, r * .96), (h, r * .88)]
    for i in range(n):
        a0 = (i + .025) * 2 * math.pi / n
        a1 = (i + .975) * 2 * math.pi / n
        v = []
        for zz, rr in levels:
            v.extend([(x + math.cos(a0) * rr, y + math.sin(a0) * rr, z + zz), (x + math.cos(a1) * rr, y + math.sin(a1) * rr, z + zz)])
        g.add(v, [(j * 2, j * 2 + 1, j * 2 + 3, j * 2 + 2) for j in range(len(levels) - 1)], PLANK)
    for zz, rr in ((.12 * h, r * .96), (.50 * h, r), (.88 * h, r * .96)):
        band(g, (x, y, z + zz), rr + .015, .032, .075, IRON, 'Z', n)
    if water:
        prism(g, (x, y, z + h - .07), r * .85, .025, WATER, 'Z', 16, (False, True))
    else:
        prism(g, (x, y, z + h - .014), r * .88, .035, PLANK, 'Z', n, (False, True))
        band(g, (x, y, z + h), r * .89, .025, .045, IRON, 'Z', n)


def round_pipe(g, points, r=.055):
    """reference_details.round_pipe: 8-sided tubing, chunky elbow knuckles."""
    for a, b in zip(points, points[1:]):
        a, b = Vector(a), Vector(b)
        rotation = (b - a).to_track_quat('Z', 'Y')
        n = 8
        verts = [q + rotation @ Vector((math.cos(i * 2 * math.pi / n) * r, math.sin(i * 2 * math.pi / n) * r, 0)) for q in (a, b) for i in range(n)]
        g.add(verts, [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)], IRON)
    for q in points[1:-1]:
        rock(g, q, (r * 2.22, r * 2.22, r * 2.22), IRON, 12, 6)


def cage_lamp(g, x, y, z):
    """reference_details.cage_lamp with 6-sided glass and caps."""
    g.beam((x, y + .05, z + .16), (x, y - .13, z + .16), .035, mat=IRON)
    prism(g, (x, y - .13, z), .06, .19, GLOW, 'Z', 6)
    for zz in (z - .12, z + .12):
        prism(g, (x, y - .13, zz), .085, .025, IRON, 'Z', 6)
    for dx, dy in ((-.052, -.052), (.052, .052)):
        g.beam((x + dx, y - .13 + dy, z - .12), (x + dx, y - .13 + dy, z + .12), .012, mat=IRON)


def machinery_shell(g, p, profile, axis='Y', segments=16, fastener_material=BRASS):
    """reference_details.machinery_shell: 16-sided shell, banded joints with
    six square fasteners each (was 24 sides, twelve 6-sided pins)."""
    x, y, z = p

    def point(a, b, c):
        return (x + c, y + a, z + b) if axis == 'X' else (x + a, y + c, z + b)
    verts = [point(math.cos(i * math.pi * 2 / segments) * r, math.sin(i * math.pi * 2 / segments) * r, t) for t, r in profile for i in range(segments)]
    faces = [tuple(reversed(range(segments))), tuple(range((len(profile) - 1) * segments, len(profile) * segments))]
    for level in range(len(profile) - 1):
        for i in range(segments):
            faces.append((level * segments + i, level * segments + (i + 1) % segments, (level + 1) * segments + (i + 1) % segments, (level + 1) * segments + i))
    if axis == 'Y':
        faces = [tuple(reversed(f)) for f in faces]
    g.add(verts, faces, IRON)
    for t, r in profile[1:-1]:
        pp = point(0, 0, t)
        band(g, pp, r + .018, .035, .075, IRON, axis, segments)
        for i in range(6):
            a = i * math.pi / 3
            q = point(math.cos(a) * (r + .024), math.sin(a) * (r + .024), t)
            prism(g, q, .021, .035, fastener_material, axis, 4)


def open_beam(g, a, b, width=.12, depth=None, mat=WOOD, start=False, end=True):
    """Geometry.beam whose start (or end) cap is omitted when it is buried in
    the member it springs from (gear teeth, spokes)."""
    if depth is None:
        depth = width
    a, b = Vector(a), Vector(b)
    direction = b - a
    if direction.length < .00001:
        raise ValueError('Zero-length authored beam')
    rotation = direction.to_track_quat('Z', 'Y')
    corners = [a + rotation @ Vector((x * width / 2, y * depth / 2, z * direction.length)) for z in (0, 1) for y in (-1, 1) for x in (-1, 1)]
    faces = [(1, 5, 4, 0), (6, 7, 3, 2), (4, 6, 2, 0), (3, 7, 5, 1)]
    if start:
        faces.insert(0, (2, 3, 1, 0))
    if end:
        faces.insert(1 if start else 0, (5, 7, 6, 4))
    g.add(corners, faces, mat)


def wheel(g, p, r, axis='X', mat=IRON, accent=BRASS):
    """Geometry.wheel: 16-sided rims, 8-sided hub, eight spokes without their
    buried hub ends."""
    band(g, p, r, .055, .08, mat, axis, 16, inner=True)
    band(g, p, r * .77, .025, .06, accent, axis, 16, inner=True)
    prism(g, p, .09, .17, IRON, axis, 8)
    for i in range(8):
        a = i * math.pi / 4
        end = (p[0], p[1] + math.cos(a) * r * .95, p[2] + math.sin(a) * r * .95) if axis == 'X' else (p[0] + math.cos(a) * r * .95, p[1], p[2] + math.sin(a) * r * .95)
        start = (p[0], p[1] + math.cos(a) * .08, p[2] + math.sin(a) * .08) if axis == 'X' else (p[0] + math.cos(a) * .08, p[1], p[2] + math.sin(a) * .08)
        open_beam(g, start, end, .045, mat=mat, end=False)


def gauge(g, x, y, z, r=.09, rim_material=BRASS):
    """industrial_facades.gauge: 12-sided case and glass with their front
    caps (the back is on the panel), needle and seven scale ticks."""
    from reference_materials import GLASS
    from industrial_facades import CYAN
    prism(g, (x, y, z), r, .045, rim_material, 'Y', 12, (True, False))
    prism(g, (x, y - .03, z), r * .79, .016, GLASS, 'Y', 12, (True, False))
    g.beam((x, y - .046, z), (x + r * .48, y - .046, z + r * .42), .009, mat=CYAN)
    for a in range(7):
        angle = a * math.pi / 5 - .3
        g.beam((x + math.cos(angle) * r * .57, y - .047, z + math.sin(angle) * r * .57),
               (x + math.cos(angle) * r * .68, y - .047, z + math.sin(angle) * r * .68), .006, mat=IRON)
