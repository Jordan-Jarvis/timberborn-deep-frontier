"""Exact removal of faces that no camera can see because solid lies in front.

A face is culled only when the space immediately in front of every point of
it (EPS along its normal) lies inside an opaque closed volume authored in the
same Geometry part:

- a closed convex primitive (box, beam, prism, hex head...) recorded by
  Geometry.add: every edge shared by exactly two of its faces with opposite
  winding, and every vertex on the inner side of every face plane;
- an explicitly declared hidden volume (Geometry.declare_hidden_volume), for
  example the inside of a room whose walls, floor, ceiling and sealed doors
  and opaque windows close it completely.

Coverage is computed exactly in the face's plane: each volume's cross-section
there is a convex polygon, shrunk by a margin (MARGIN plus the part's bevel
width, which the bevel modifier removes from the volume's edges), and the face
is removed when those polygons cover it completely (convex polygon
difference). Faces are never split, moved or merged. A face is never removed
by its own primitive, by a volume in another component, or when it carries
explicit native UVs (imported native pieces), or uses an excluded material.

The ray check in audit_hidden_geometry.py (--culled) then verifies against the
saved scene that every removed face stays occluded from every camera
direction, so a wrong declaration shows up as a failure, not a hole.
"""
import math

# Scenes built as shells by render_reference_studies.py and rebuilt the same
# way by rebuild_components.py: no bevel modifier, cull_enclosed on.
SHELL_MODELS = ('FisheryWorks', 'FishHatchery', 'Restaurant', 'Hospital', 'ReinforcedHydroTurbine', 'MaterialsLaboratory')

EPS = 2e-5          # how far in front of the face the solid must reach (float32 contact noise is ~1e-6)
MARGIN = -2e-6      # cross-section inset; negative = grown by float32 noise, so flush contact counts
PARALLEL = 1 - 1e-9  # |cos| above which a volume plane is parallel to the face


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    length = math.sqrt(_dot(a, a))
    return None if length < 1e-12 else (a[0] / length, a[1] / length, a[2] / length)


def newell(points):
    n = [0.0, 0.0, 0.0]
    for i, p in enumerate(points):
        q = points[(i + 1) % len(points)]
        n[0] += (p[1] - q[1]) * (p[2] + q[2])
        n[1] += (p[2] - q[2]) * (p[0] + q[0])
        n[2] += (p[0] - q[0]) * (p[1] + q[1])
    return _unit(n)


def convex_planes(vertices, faces):
    """Outward planes (n, d), n.x <= d inside, of a closed convex polyhedron,
    or None when the faces do not close a convex volume."""
    edges = {}
    for face in faces:
        for i, a in enumerate(face):
            b = face[(i + 1) % len(face)]
            if (a, b) in edges:
                return None
            edges[(a, b)] = True
    if any((b, a) not in edges for a, b in edges):
        return None
    planes = []
    for face in faces:
        points = [vertices[i] for i in face]
        n = newell(points)
        if n is None:
            return None
        d = _dot(n, points[0])
        if any(abs(_dot(n, p) - d) > 1e-6 for p in points):
            return None
        planes.append((n, d))
    used = {i for face in faces for i in face}
    for n, d in planes:
        if any(_dot(n, vertices[i]) > d + 1e-6 for i in used):
            return None
    return planes


def box_planes(lo, hi):
    return [((1, 0, 0), hi[0]), ((-1, 0, 0), -lo[0]), ((0, 1, 0), hi[1]), ((0, -1, 0), -lo[1]),
            ((0, 0, 1), hi[2]), ((0, 0, -1), -lo[2])]


def _clip(poly, a, b, c):
    """Keep a*x + b*y <= c."""
    out = []
    count = len(poly)
    for i in range(count):
        p, q = poly[i], poly[(i + 1) % count]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if (fp < 0 < fq) or (fq < 0 < fp):
            t = fp / (fp - fq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def _area(poly):
    return abs(sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(poly, poly[1:] + poly[:1]))) / 2


def _convex2d(poly):
    sign = 0
    for i in range(len(poly)):
        p, q, r = poly[i], poly[(i + 1) % len(poly)], poly[(i + 2) % len(poly)]
        z = (q[0] - p[0]) * (r[1] - q[1]) - (q[1] - p[1]) * (r[0] - q[0])
        if abs(z) < 1e-14:
            continue
        s = 1 if z > 0 else -1
        if sign and s != sign:
            return False
        sign = s
    return True


class Volume:
    __slots__ = ('planes', 'lo', 'hi', 'margin', 'owner', 'group', 'declared')

    def __init__(self, planes, points, margin, owner, group, declared=False):
        self.declared = declared
        self.planes = planes
        self.lo = tuple(min(p[i] for p in points) for i in range(3))
        self.hi = tuple(max(p[i] for p in points) for i in range(3))
        self.margin = margin
        self.owner = owner
        self.group = group


def section(volume, n, offset, origin, u, v):
    """Half-planes (a, b, c), a*s + b*t <= c in the face plane basis, of the
    volume's cross-section with the plane n.x = offset, shrunk by its margin.
    None when the plane misses the volume."""
    lines = []
    for m, d in volume.planes:
        cos = _dot(m, n)
        a, b = _dot(m, u), _dot(m, v)
        length = math.hypot(a, b)
        if abs(cos) > PARALLEL or length < 1e-9:
            # Constant over the plane: inside everywhere or nowhere.
            if cos * offset > d - 1e-9:
                return None
            continue
        c = d - _dot(m, origin)
        lines.append((a / length, b / length, c / length - volume.margin))
    return lines


def covered(points, volumes):
    """True when the face polygon (3D points, outward winding) is covered by
    the cross-sections of volumes taken EPS in front of it."""
    n = newell(points)
    if n is None:
        return False
    u = _unit(_sub(points[1], points[0]))
    if u is None:
        return False
    v = _cross(n, u)
    offset = _dot(n, points[0]) + EPS
    origin = (n[0] * offset, n[1] * offset, n[2] * offset)
    face = [(_dot(_sub(p, origin), u), _dot(_sub(p, origin), v)) for p in points]
    if not _convex2d(face):
        return False
    whole = _area(face)
    if whole < 1e-12:
        return False
    tiny = max(1e-10, whole * 1e-7)
    pieces = [face]
    for volume in volumes:
        lines = section(volume, n, offset, origin, u, v)
        if lines is None:
            continue
        remaining = []
        for piece in pieces:
            rest = piece
            for a, b, c in lines:
                outside = _clip(rest, -a, -b, -c)
                if len(outside) >= 3 and _area(outside) > tiny:
                    remaining.append(outside)
                rest = _clip(rest, a, b, c)
                if len(rest) < 3 or _area(rest) <= tiny:
                    break
        pieces = remaining
        if not pieces:
            return True
    return sum(_area(p) for p in pieces) <= tiny


def cull(vertices, faces, face_owner, face_group, volumes, eligible):
    """Faces fully covered by volumes of their own group: (by solids alone,
    exact; needing a declared hidden volume, to be ray-verified).

    vertices: mesh coordinates; faces: vertex index tuples; face_owner: the
    volume index that authored each face (or -1); face_group: component index
    per face; volumes: [Volume]; eligible(i): whether face i may be removed."""
    cell = .5
    grid = {}
    for index, volume in enumerate(volumes):
        for x in range(math.floor(volume.lo[0] / cell), math.floor(volume.hi[0] / cell) + 1):
            for y in range(math.floor(volume.lo[1] / cell), math.floor(volume.hi[1] / cell) + 1):
                for z in range(math.floor(volume.lo[2] / cell), math.floor(volume.hi[2] / cell) + 1):
                    grid.setdefault((x, y, z), []).append(index)
    removed, declared = [], []
    for i, face in enumerate(faces):
        if not eligible(i):
            continue
        points = [vertices[k] for k in face]
        lo = [min(p[a] for p in points) - EPS * 2 for a in range(3)]
        hi = [max(p[a] for p in points) + EPS * 2 for a in range(3)]
        found = set()
        for x in range(math.floor(lo[0] / cell), math.floor(hi[0] / cell) + 1):
            for y in range(math.floor(lo[1] / cell), math.floor(hi[1] / cell) + 1):
                for z in range(math.floor(lo[2] / cell), math.floor(hi[2] / cell) + 1):
                    found.update(grid.get((x, y, z), ()))
        candidates = []
        for index in sorted(found):
            volume = volumes[index]
            if index == face_owner[i] or volume.group != face_group[i]:
                continue
            if any(volume.hi[a] < lo[a] or volume.lo[a] > hi[a] for a in range(3)):
                continue
            candidates.append(volume)
        if not candidates:
            continue
        solids = [v for v in candidates if not v.declared]
        if solids and covered(points, solids):
            removed.append(i)
        elif len(solids) < len(candidates) and covered(points, candidates):
            declared.append(i)
    return removed, declared


# Orbit camera directions (the game camera never looks from below), shared
# with audit_hidden_geometry.py.
ELEVATIONS = (12, 30, 48, 66, 84)
AZIMUTHS = 16


def directions():
    out = []
    for e in ELEVATIONS:
        for i in range(AZIMUTHS):
            a = 2 * math.pi * (i + .5 * (e // 18 % 2)) / AZIMUTHS
            ce = math.cos(math.radians(e))
            out.append((ce * math.cos(a), ce * math.sin(a), math.sin(math.radians(e))))
    return out


# A face is seen from a direction only when it faces it by more than FACING
# (cos): within 0.6 degrees of edge-on it projects to under 1% of its area.
FACING = .01
SMALL_AREA = .0025   # m2: a 5 x 5 cm face
SMALL_EDGE = .10


def small(points):
    """Faces small enough for the sampled hidden-face test (Geometry.cull_small_hidden)."""
    n = len(points)
    if max(math.dist(points[i], points[(i + 1) % n]) for i in range(n)) > SMALL_EDGE:
        return False
    c = points[0]
    area = 0
    for i in range(1, n - 1):
        cross = _cross(_sub(points[i], c), _sub(points[i + 1], c))
        area += math.sqrt(_dot(cross, cross)) / 2
    return area <= SMALL_AREA


def samples(points, spacing=None):
    """Centroid, corners and edge midpoints pulled 3% inwards, and a
    barycentric grid of at most `spacing` over each fan triangle (8 cm, or
    2 cm for small faces)."""
    if spacing is None:
        spacing = .02 if small(points) else .08
    c = tuple(sum(p[a] for p in points) / len(points) for a in range(3))
    pull = lambda p, t: tuple(c[a] + (p[a] - c[a]) * t for a in range(3))
    out = [c]
    for i, p in enumerate(points):
        q = points[(i + 1) % len(points)]
        mid = tuple((p[a] + q[a]) / 2 for a in range(3))
        out += [pull(p, .97), pull(p, .95), pull(mid, .97), pull(p, .5)]
        length = max(math.dist(c, p), math.dist(p, q), math.dist(q, c))
        n = math.ceil(length / spacing)
        if n > 1:
            for j in range(1, n):
                for k in range(1, n - j):
                    u, v = j / n, k / n
                    out.append(pull(tuple(c[a] + (p[a] - c[a]) * u + (q[a] - c[a]) * v for a in range(3)), .97))
    return out


def visible(tree, points, dirs):
    """True when some sample of the polygon sees open sky along a camera
    direction it faces (tree: mathutils BVHTree of everything kept)."""
    from mathutils import Vector
    n = newell(points)
    if n is None:
        return False
    n = Vector(n)
    for s in samples(points):
        s = Vector(s)
        for d in dirs:
            if n.dot(d) <= FACING:
                continue
            origin = s + n * 2e-4 + d * 2e-4
            for _ in range(64):
                hit = tree.ray_cast(origin, d, 500.0)
                if hit[0] is None:
                    return True
                if hit[1].dot(d) > 0 or any(m.dot(d) > 0 for _, m, _, _ in tree.find_nearest_range(hit[0], 2e-5)):
                    break
                origin = hit[0] + d * 2e-4
    return False
