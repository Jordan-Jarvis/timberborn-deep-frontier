"""Authored geometry of the Deep Frontier map objects and stockpile good models.

Native style (tools/STATUS.md, map objects): faceted low-poly rock and mineral
forms like the vanilla water source, badwater source and blockage, textured
only with shipped native materials that MaterialCollection.Common (or Deep
Frontier's MapResources collection) registers:

  ROCK  WaterSource              CliffDetail rock (vanilla source rocks)
  DARK  UndergroundRuinsCliff    the same rock, darker (vanilla ruin cliffs)
  ORE   BaseMetal.IronTeeth      worn metal plate tile: metallic ore faces
  GOODS BeaverCarryingModels     goods atlas: steel and rusted bar strips
  SAND  Plaster_Orange.IronTeeth pebbled plaster tile: sandstone
  LIME  Plaster_White.IronTeeth  pebbled plaster tile: limestone
  RUIN  Ruins                    old-world concrete slabs and rebar
  VAULT UnstableCore             old-world bronze panels and hatch ring

Every face gets an explicit UV island inside the tile of its material (the
atlases mix unrelated sheets; the UnstableCore lens and plate glow and are
never addressed). Units are tiles: x across, y back (0 = front, entrance
side), z up in layers; Geometry stores the exporter's source coordinates.
No bevel: the native atlases paint the edges. Nothing here is resized to fit.
"""
import math
import random
import sys
from pathlib import Path

import bmesh
from mathutils import Vector, Matrix

sys.path.insert(0, str(Path(__file__).parent))
from frontier_architecture import Geometry  # noqa: E402

MATERIALS = {
    'ROCK': 'WaterSource',
    'DARK': 'UndergroundRuinsCliff',
    'ORE': 'BaseMetal.IronTeeth',
    'GOODS': 'BeaverCarryingModels',
    'SAND': 'Plaster_Orange.IronTeeth',
    'LIME': 'Plaster_White.IronTeeth',
    'RUIN': 'Ruins',
    'VAULT': 'UnstableCore',
}
# Atlas tiles (u0, v0, u1, v1) and the world tiles one UV unit spans (uniform
# texel density on both axes; square textures). Measured on the shipped
# textures (outputs/map-objects/native/preview). Seamless tiles are
# world-projected across faces; the others get one island per face inside
# their tile, shrunk only when a face is larger than the tile.
TILES = {
    'rock': ((0, 0, 1, 1), 1.2, True),             # CliffDetail (WaterSource, UndergroundRuinsCliff)
    'ore': ((.02, .52, .48, .98), 1.5, False),      # BaseMetal upper-left plate
    'steel': ((.818, .51, .897, .9), 4.0, False),   # BeaverCarryingModels grey bar
    'rust': ((.909, .51, .993, .9), 4.0, False),    # BeaverCarryingModels rusted bar
    'steelcap': ((.818, .915, .897, .995), 4.0, False),
    'sack': ((.515, .53, .74, .97), 3.0, False),     # BeaverCarryingModels sack: dark rough cloth
    'plaster': ((0, .515, 1, .985), 1.5, False),    # Plaster top band (two repeats across)
    'slab': ((.16, .888, .44, .92), 8.0, False),  # Ruins: the long top concrete slab
    'slab2': ((.075, .39, .39, .422), 8.0, False),
    'rebar': ((.617, .02, .631, .98), 1.7, False),  # Ruins vertical rebar rod
    'panel': ((.02, .52, .48, .98), 1.2, False),    # UnstableCore plain bronze panel
    'ribs': ((.01, .01, .49, .49), 1.0, False),     # UnstableCore ribbed slats
    'plate': ((.515, .265, .735, .485), 1.0, False),
    'ring': ((.757, .507, .993, .743), None, False),  # UnstableCore hatch ring (mapped whole)
    'hex': ((.758, .262, .995, .415), 1.0, False),
    'squares': ((.758, .005, .995, .243), 1.0, False),
}


BUILDER_METHODS = {'add', 'hull', 'rock', 'prism', 'crystal', 'lump', 'box', 'cylinder', 'panels', 'island'}


class Builder:
    """Collects faces per material key with explicit UVs, then builds them
    into a frontier_architecture.Geometry with only the materials used."""

    def __init__(self, name, seed):
        self.name = name
        self.rng = random.Random(seed)
        self.parts = []   # (vertices, faces, face_uvs, material key)

    # ---- UV islands -------------------------------------------------------
    def island(self, points, normal, tile, scale=None, along=None):
        rect, span_tiles, seamless = TILES[tile]
        u0, v0, u1, v1 = rect
        n = Vector(normal).normalized()
        if along is None:
            edges = [points[(i + 1) % len(points)] - p for i, p in enumerate(points)]
            along = max(edges, key=lambda e: e.length_squared)
            # Upright faces keep the texture upright (strata run horizontally).
            if abs(n.z) < .7:
                along = Vector((0, 0, 1)).cross(n)
        along = Vector(along)
        along = (along - n * along.dot(n)).normalized()
        across = n.cross(along).normalized()
        coords = [(p.dot(along), p.dot(across)) for p in points]
        if tile == 'ring':
            lo = [min(c[i] for c in coords) for i in range(2)]
            hi = [max(c[i] for c in coords) for i in range(2)]
            return [(u0 + (c[0] - lo[0]) / (hi[0] - lo[0]) * (u1 - u0), v0 + (c[1] - lo[1]) / (hi[1] - lo[1]) * (v1 - v0)) for c in coords]
        if seamless:
            k = 1 / (span_tiles * (scale or 1))
            ou, ov = self.rng.random(), self.rng.random()
            return [(ou + c[0] * k, ov + c[1] * k) for c in coords]
        lo = [min(c[i] for c in coords) for i in range(2)]
        size = [max(c[i] for c in coords) - lo[i] for i in range(2)]
        width, height = (u1 - u0), (v1 - v0)
        k = 1 / (span_tiles * (scale or 1))   # UV units per world tile, both axes
        su, sv = size[0] * k, size[1] * k
        if su > width or sv > height:
            shrink = min(width / su if su else 1, height / sv if sv else 1) * .999
            k *= shrink
            su, sv = su * shrink, sv * shrink
        ou = u0 + self.rng.random() * (width - su)
        ov = v0 + self.rng.random() * (height - sv)
        return [(ou + (c[0] - lo[0]) * k, ov + (c[1] - lo[1]) * k) for c in coords]

    def add(self, vertices, faces, key, tile, scale=None, along=None, tiles=None):
        vertices = [Vector(v) for v in vertices]
        uvs = []
        for index, face in enumerate(faces):
            points = [vertices[i] for i in face]
            normal = (points[1] - points[0]).cross(points[2] - points[0])
            for i in range(2, len(points) - 1):
                normal += (points[i] - points[0]).cross(points[i + 1] - points[0])
            if normal.length < 1e-12:
                raise ValueError(f'{self.name}: degenerate face')
            face_tile = tiles[index] if tiles else tile
            uvs.append(self.island(points, normal, face_tile, scale, along))
        frame, chain = sys._getframe(1), []
        while frame is not None and len(chain) < 3:
            if frame.f_code.co_filename != __file__ or frame.f_code.co_name not in BUILDER_METHODS:
                chain.append(f'{Path(frame.f_code.co_filename).name}:{frame.f_lineno}:{frame.f_code.co_name}')
            frame = frame.f_back
        self.parts.append(([tuple(v) for v in vertices], [tuple(f) for f in faces], uvs, key, ' > '.join(chain)))

    # ---- primitives ---------------------------------------------------------
    def hull(self, points, key, tile, cut=0.0, scale=None):
        """Faceted convex rock through the given points; faces entirely at or
        below z=cut that face down are dropped (they sit in the ground)."""
        bm = bmesh.new()
        for p in points:
            bm.verts.new(p)
        result = bmesh.ops.convex_hull(bm, input=bm.verts)
        for geom in result.get('geom_interior', []):
            if isinstance(geom, bmesh.types.BMVert):
                bm.verts.remove(geom)
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(2), verts=bm.verts, edges=bm.edges)
        bm.verts.index_update()
        verts = [v.co.copy() for v in bm.verts]
        faces = []
        for f in bm.faces:
            if f.normal.z < -.6 and all(v.co.z <= cut + 1e-6 for v in f.verts):
                continue
            faces.append([v.index for v in f.verts])
        bm.free()
        used = sorted({i for f in faces for i in f})
        remap = {old: new for new, old in enumerate(used)}
        self.add([verts[i] for i in used], [[remap[i] for i in f] for f in faces], key, tile, scale)

    def rock(self, center, radii, key='ROCK', tile='rock', points=11, sink=.05, flat_top=None, scale=None):
        """A faceted boulder: jittered ellipsoid points plus a ring just below
        ground; flat_top clips the crown to a table (sedimentary blocks)."""
        cx, cy, cz = center
        rx, ry, rz = radii
        pts = []
        for _ in range(points):
            while True:
                d = Vector((self.rng.gauss(0, 1), self.rng.gauss(0, 1), abs(self.rng.gauss(0, 1)) * .9 + .1))
                if d.length > .2:
                    break
            d.normalize()
            r = self.rng.uniform(.82, 1.04)
            z = cz + d.z * rz * r
            if flat_top is not None:
                z = min(z, cz + flat_top)
            pts.append((cx + d.x * rx * r, cy + d.y * ry * r, z))
        base = cz - sink
        for i in range(6):
            a = (i + self.rng.uniform(-.25, .25)) * math.tau / 6
            pts.append((cx + math.cos(a) * rx * .82, cy + math.sin(a) * ry * .82, base))
        self.hull(pts, key, tile, cut=base, scale=scale)

    def prism(self, outline, z0, z1, key, tile, inset=0.0, top_key=None, top_tile=None, skew=(0, 0), scale=None, top=True, dome=0.0):
        """Vertical-sided slab over a 2D outline (counter-clockwise from above),
        its top inset by `inset` toward the centroid (a chamfer) and shifted
        by `skew` (a tilted bedding plane). No bottom face."""
        n = len(outline)
        cx = sum(p[0] for p in outline) / n
        cy = sum(p[1] for p in outline) / n
        top = []
        for x, y in outline:
            dx, dy = x - cx, y - cy
            length = math.hypot(dx, dy) or 1
            f = max(0.0, 1 - inset / length)
            top.append((cx + dx * f + skew[0], cy + dy * f + skew[1]))
        top_pts = top
        vertices = [(x, y, z0) for x, y in outline] + [(x, y, z1) for x, y in top]
        sides = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.add(vertices, sides, key, tile, scale)
        if top and dome:
            # A low faceted crown: a fan to a raised point off the centroid.
            tx = sum(p[0] for p in top_pts) / n + self.rng.uniform(-.08, .08)
            ty = sum(p[1] for p in top_pts) / n + self.rng.uniform(-.08, .08)
            crown = vertices + [(tx, ty, z1 + dome)]
            self.add(crown, [(n + i, n + (i + 1) % n, 2 * n) for i in range(n)], top_key or key, top_tile or tile, scale)
        elif top:
            self.add(vertices, [tuple(range(n, 2 * n))], top_key or key, top_tile or tile, scale)

    def crystal(self, base, radius, height, key='ORE', tile='ore', sides=5, lean=(0, 0), twist=0.0):
        """A pointed mineral prism rising from below the surface."""
        bx, by, bz = base
        axis = Vector((lean[0], lean[1], 1)).normalized()
        rot = axis.to_track_quat('Z', 'Y').to_matrix()
        ring_lo, ring_hi = [], []
        for i in range(sides):
            a = twist + i * math.tau / sides
            r = radius * self.rng.uniform(.85, 1.1)
            local = Vector((math.cos(a) * r, math.sin(a) * r, 0))
            ring_lo.append(Vector(base) + rot @ (local + Vector((0, 0, -.05))))
            ring_hi.append(Vector(base) + rot @ (local * .92 + Vector((0, 0, height * .68))))
        tip = Vector(base) + rot @ Vector((radius * .15, 0, height))
        vertices = ring_lo + ring_hi + [tip]
        faces = [(i, (i + 1) % sides, sides + (i + 1) % sides, sides + i) for i in range(sides)]
        faces += [(sides + i, sides + (i + 1) % sides, 2 * sides) for i in range(sides)]
        self.add(vertices, faces, key, tile)

    def lump(self, center, radii, key, tile):
        """A rough ore nugget for pile goods: a hull of a wide 4-point base and
        a 3-point crown, open below (about 8 triangles, so a full level of
        eight nuggets matches the 64 triangles of vanilla 4ScrapMetals)."""
        cx, cy, cz = center
        rx, ry, rz = radii
        pts = []
        for i in range(4):
            a = (i + .5 + self.rng.uniform(-.15, .15)) * math.tau / 4
            pts.append((cx + math.cos(a) * rx * 1.2, cy + math.sin(a) * ry * 1.2, cz))
        pts.append((cx - rx * self.rng.uniform(.3, .6), cy + self.rng.uniform(-.45, .45) * ry, cz + rz * self.rng.uniform(.75, 1)))
        pts.append((cx + rx * self.rng.uniform(.2, .55), cy + self.rng.uniform(-.45, .45) * ry, cz + rz * self.rng.uniform(.8, 1)))
        pts.append((cx + self.rng.uniform(-.5, .5) * rx, cy + ry * self.rng.choice((-.6, .6)), cz + rz * self.rng.uniform(.45, .7)))
        self.hull(pts, key, tile, cut=cz)

    def box(self, center, size, key, tile, yaw=0.0, tiles=None, scale=None, bottom=False):
        cx, cy, cz = center
        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        rot = Matrix.Rotation(yaw, 3, 'Z')
        corners = [Vector(center) + rot @ Vector((x * hx, y * hy, z * hz)) for z in (-1, 1) for y in (-1, 1) for x in (-1, 1)]
        faces = [(4, 5, 7, 6), (0, 1, 5, 4), (1, 3, 7, 5), (3, 2, 6, 7), (2, 0, 4, 6)]
        if bottom:
            faces.append((0, 2, 3, 1))
        self.add(corners, faces, key, tile, scale, tiles=tiles)

    def cylinder(self, center, radius, length, key, tile, axis='Z', segments=10, caps=(False, True), cap_tile=None, radius2=None):
        radius2 = radius if radius2 is None else radius2
        c = Vector(center)
        directions = {'X': (Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))),
                      'Y': (Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, 1, 0))),
                      'Z': (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))}
        a, b, w = directions[axis]
        lo = [c - w * length / 2 + (a * math.cos(i * math.tau / segments) + b * math.sin(i * math.tau / segments)) * radius for i in range(segments)]
        hi = [c + w * length / 2 + (a * math.cos(i * math.tau / segments) + b * math.sin(i * math.tau / segments)) * radius2 for i in range(segments)]
        vertices = lo + hi
        sides = [(i, (i + 1) % segments, segments + (i + 1) % segments, segments + i) for i in range(segments)]
        self.add(vertices, sides, key, tile)
        if caps[1]:
            self.add(vertices, [tuple(range(segments, 2 * segments))], key, cap_tile or tile)
        if caps[0]:
            self.add(vertices, [tuple(reversed(range(segments)))], key, cap_tile or tile)

    def panels(self, corners, nu, nv, key, tiles):
        """A quad split into nu x nv cast panels, each with its own island
        (large faces would otherwise stretch a narrow atlas strip)."""
        a, b, c, d = [Vector(p) for p in corners]
        for i in range(nu):
            for j in range(nv):
                def at(u, v):
                    return a.lerp(b, u).lerp(d.lerp(c, u), v)
                quad = [at(i / nu, j / nv), at((i + 1) / nu, j / nv), at((i + 1) / nu, (j + 1) / nv), at(i / nu, (j + 1) / nv)]
                self.add(quad, [(0, 1, 2, 3)], key, tiles[(i + j) % len(tiles)])

    def blob_outline(self, cx, cy, rx, ry, count, jitter=.12, phase=0.0):
        pts = []
        for i in range(count):
            a = phase + i * math.tau / count
            r = 1 + self.rng.uniform(-jitter, jitter)
            pts.append((cx + math.cos(a) * rx * r, cy + math.sin(a) * ry * r))
        return pts

    # ---- build ----------------------------------------------------------------
    def geometry(self):
        keys = list(dict.fromkeys(part[3] for part in self.parts))
        g = Geometry(self.name)
        for vertices, faces, uvs, key, source in self.parts:
            g.add(vertices, faces, keys.index(key))
            g.face_uvs[-len(faces):] = uvs
            g.face_sources[-len(faces):] = [source] * len(faces)
        return g, [MATERIALS[k] for k in keys]


def _check_outline(outline, w, d, margin=.03):
    for x, y in outline:
        if not (margin <= x <= w - margin and margin <= y <= d - margin):
            raise ValueError(f'outline point {x:.3f},{y:.3f} leaves the {w}x{d} footprint')


def _clip(polygon, normal, offset):
    """Keep the part of a convex polygon with dot(p, normal) <= offset."""
    out = []
    for i, p in enumerate(polygon):
        q = polygon[(i + 1) % len(polygon)]
        dp = p[0] * normal[0] + p[1] * normal[1] - offset
        dq = q[0] * normal[0] + q[1] * normal[1] - offset
        if dp <= 0:
            out.append(p)
        if (dp <= 0) != (dq <= 0):
            t = dp / (dp - dq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def voronoi(sites, lo, hi, joint):
    """Convex Voronoi cells of the sites inside the rectangle lo..hi, each
    pulled back joint/2 from every bisector (so neighbours are joint apart).
    Counter-clockwise outlines with their site; empty cells are dropped."""
    cells = []
    for i, (sx, sy) in enumerate(sites):
        polygon = [(lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1])]
        for j, (ox, oy) in enumerate(sites):
            if i == j:
                continue
            nx, ny = ox - sx, oy - sy
            length = math.hypot(nx, ny)
            nx, ny = nx / length, ny / length
            mx, my = (sx + ox) / 2, (sy + oy) / 2
            polygon = _clip(polygon, (nx, ny), mx * nx + my * ny - joint / 2)
            if len(polygon) < 3:
                break
        if len(polygon) >= 3:
            cleaned = [p for k, p in enumerate(polygon) if math.dist(p, polygon[k - 1]) > .015]
            if len(cleaned) >= 3:
                cells.append(((sx, sy), cleaned))
    return cells


def patch_boundary(rng, w, d, margin, corner):
    """Half-planes of a convex chamfered rectangle (a natural patch edge that
    still reads as the w x d site): (normal, offset) pairs for _clip."""
    pts = [(margin + corner * rng.uniform(.7, 1.2), margin), (w - margin - corner * rng.uniform(.7, 1.2), margin),
           (w - margin, margin + corner * rng.uniform(.7, 1.2)), (w - margin, d - margin - corner * rng.uniform(.7, 1.2)),
           (w - margin - corner * rng.uniform(.7, 1.2), d - margin), (margin + corner * rng.uniform(.7, 1.2), d - margin),
           (margin, d - margin - corner * rng.uniform(.7, 1.2)), (margin, margin + corner * rng.uniform(.7, 1.2))]
    planes = []
    for i, (ax, ay) in enumerate(pts):
        bx, by = pts[(i + 1) % len(pts)]
        nx, ny = by - ay, -(bx - ax)
        length = math.hypot(nx, ny)
        nx, ny = nx / length, ny / length
        planes.append(((nx, ny), ax * nx + ay * ny))
    return planes


def clip_to(outline, planes):
    for normal, offset in planes:
        outline = _clip(outline, normal, offset)
        if len(outline) < 3:
            return []
    return [p for k, p in enumerate(outline) if math.dist(p, outline[k - 1]) > .015]


def jittered_sites(rng, lo, hi, nx, ny, jitter):
    sx, sy = (hi[0] - lo[0]) / nx, (hi[1] - lo[1]) / ny
    return [(lo[0] + (i + .5 + rng.uniform(-jitter, jitter)) * sx, lo[1] + (j + .5 + rng.uniform(-jitter, jitter)) * sy)
            for i in range(nx) for j in range(ny)]


def _seam_path(b, start, end, steps, wander):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        inner = 0 < i < steps
        pts.append((start[0] + (end[0] - start[0]) * t + (b.rng.uniform(-wander, wander) if inner else 0),
                    start[1] + (end[1] - start[1]) * t + (b.rng.uniform(-wander, wander) if inner else 0)))
    return pts


def _distance_to_path(p, path):
    best = 1e9
    for a, c in zip(path, path[1:]):
        ax, ay = c[0] - a[0], c[1] - a[1]
        t = max(0, min(1, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay)))
        best = min(best, math.dist(p, (a[0] + ax * t, a[1] + ay * t)))
    return best


def _on_path(path, t):
    seg = min(int(t * (len(path) - 1)), len(path) - 2)
    f = t * (len(path) - 1) - seg
    return (path[seg][0] + (path[seg + 1][0] - path[seg][0]) * f, path[seg][1] + (path[seg + 1][1] - path[seg][1]) * f)


def ore_cluster(b, center, count, size, spread=.09):
    """A burst of metallic crystals leaning outward from a common root."""
    cx, cy, cz = center
    for i in range(count):
        a = i * math.tau / count + b.rng.uniform(-.4, .4)
        lean = (math.cos(a) * b.rng.uniform(.25, .6), math.sin(a) * b.rng.uniform(.25, .6))
        r = spread * b.rng.uniform(.2, .8)
        b.crystal((cx + math.cos(a) * r, cy + math.sin(a) * r, cz), size * b.rng.uniform(.28, .4),
                  size * b.rng.uniform(.8, 1.2), sides=5, lean=lean, twist=b.rng.random())


# ---------------------------------------------------------------------------
# Deep ore vein (5x5x1): the Deep Mine's understructure. A fractured bedrock
# pavement (Voronoi plates, some tilted) split along a diagonal fissure: dark
# rock in the fissure with bursts of metallic ore crystals and rusted ore.
# Low (<= 0.3) so the mine's floor covers it; fills the 5x5 so the site reads.
# ---------------------------------------------------------------------------
def deep_ore_vein():
    b = Builder('DeepOreVeinGeology', 'DeepOreVein')
    w = d = 5.0
    path = _seam_path(b, (.35, .55), (4.6, 4.45), 5, .25)
    sites = jittered_sites(b.rng, (.1, .1), (4.9, 4.9), 5, 5, .38)
    edge = patch_boundary(b.rng, w, d, .08, .45)
    # Bedrock under the plates: the joints show dark rock, not grass.
    b.prism(clip_to([(.1, .1), (4.9, .1), (4.9, 4.9), (.1, 4.9)], edge), -.05, .02, 'DARK', 'rock')
    for (sx, sy), outline in voronoi(sites, (.08, .08), (4.92, 4.92), .07):
        outline = clip_to(outline, edge)
        if len(outline) < 3:
            continue
        _check_outline(outline, w, d)
        near = _distance_to_path((sx, sy), path)
        if near < .42:
            # Fissure floor: low dark rock between the plates.
            continue   # the fissure is the bedrock floor
        top = b.rng.uniform(.06, .16) - (.03 if near > 2 else 0)
        tilt = (b.rng.uniform(-.04, .04), b.rng.uniform(-.04, .04))
        b.prism(outline, -.05, top, 'ROCK' if b.rng.random() < .75 else 'DARK', 'rock', inset=.06, skew=tilt, dome=.035)
    # The exposed ore band: metallic nuggets crowded along the fissure floor.
    for i in range(20):
        x, y = _on_path(path, (i + b.rng.random()) / 20)
        x, y = x + b.rng.uniform(-.11, .11), y + b.rng.uniform(-.11, .11)
        b.rock((x, y, .04), (b.rng.uniform(.06, .095), b.rng.uniform(.06, .095), b.rng.uniform(.05, .08)), 'ORE', 'ore', points=6, sink=.05)
    # Ore bursts along the fissure, largest in the middle.
    for i, t in enumerate((.12, .3, .5, .68, .86)):
        x, y = _on_path(path, t)
        size = .225 if i == 2 else (.2 if i in (1, 3) else .17)
        ore_cluster(b, (x, y, .035), 6 if i == 2 else 5, size, spread=.12)
    # Single crystals breaking through joints away from the fissure.
    for x, y in [(1.2, 3.4), (3.6, 1.3), (2.4, .7), (4.2, 2.6), (.8, 2.2), (3.0, 4.3)]:
        b.crystal((x, y, .02), .045, .16, sides=5, lean=(b.rng.uniform(-.3, .3), b.rng.uniform(-.3, .3)), twist=b.rng.random())
    # Loose and rusted ore lumps in the fissure.
    for i in range(10):
        x, y = _on_path(path, b.rng.random())
        x, y = x + b.rng.uniform(-.22, .22), y + b.rng.uniform(-.22, .22)
        rusty = i % 3 == 0
        b.rock((x, y, .05), (b.rng.uniform(.06, .09), b.rng.uniform(.06, .09), .07), 'GOODS' if rusty else 'ORE',
               'rust' if rusty else 'ore', points=7, sink=.08)
    return b


# ---------------------------------------------------------------------------
# Sandstone seam (5x5x1): warm stepped bedding terraces. Three beds of
# Voronoi blocks, each bed smaller and higher, with a thin dark parting under
# the upper beds and a few rounded blocks weathered off the ledges.
# Limestone seam: a grey single-level pavement of clints split by deep,
# wide grikes, two blocks toppled out. The clint tops are weathered native
# cliff rock; only the freshly broken grike walls show the pale limestone
# (2026-10-30, bricks pass: the all-white clints read as gems). Distinct in
# colour, relief (terraces against a pavement) and joint pattern.
# ---------------------------------------------------------------------------
def sandstone_seam():
    b = Builder('SandstoneSeamGeology', 'SandstoneSeam')
    w = d = 5.0
    sites = jittered_sites(b.rng, (.1, .1), (4.9, 4.9), 4, 4, .35)
    centre = (2.35, 2.6)
    edge = patch_boundary(b.rng, w, d, .1, .5)
    b.prism(clip_to([(.12, .12), (4.88, .12), (4.88, 4.88), (.12, 4.88)], edge), -.05, .03, 'DARK', 'rock')
    for (sx, sy), outline in voronoi(sites, (.1, .1), (4.9, 4.9), .035):
        outline = clip_to(outline, edge)
        if len(outline) < 3:
            continue
        _check_outline(outline, w, d)
        r = math.dist((sx, sy), centre)
        b.prism(outline, -.05, .085 + b.rng.uniform(-.01, .01), 'SAND', 'plaster', inset=.03)
        if r < 1.75:
            inner = [(sx + (x - sx) * .86, sy + (y - sy) * .86) for x, y in outline]
            b.prism(inner, .07, .1, 'DARK', 'rock', top=False)
            b.prism(inner, .1, .19 + b.rng.uniform(-.01, .015), 'SAND', 'plaster', inset=.03)
            if r < 1.0:
                top = [(sx + (x - sx) * .7, sy + (y - sy) * .7) for x, y in outline]
                b.prism(top, .18, .29 + b.rng.uniform(-.01, .01), 'SAND', 'plaster', inset=.035)
    for center, radii in [((.7, .62, .1), (.22, .18, .12)), ((4.35, 4.3, .1), (.2, .24, .12)), ((4.3, .7, .08), (.16, .15, .1))]:
        b.rock(center, radii, 'SAND', 'plaster', points=12)
    b.rock((1.1, 4.3, .06), (.14, .12, .08), 'ROCK', points=9)
    return b


def limestone_seam():
    b = Builder('LimestoneSeamGeology', 'LimestoneSeam')
    w = d = 5.0
    # Clints: cells from a 4x5 jittered grid, deep 0.09 grikes, the outer
    # ring lower so the pavement domes.
    sites = jittered_sites(b.rng, (.12, .12), (4.88, 4.88), 4, 5, .22)
    cells = voronoi(sites, (.12, .12), (4.88, 4.88), .09)
    edge = patch_boundary(b.rng, w, d, .12, .4)
    b.prism(clip_to([(.14, .14), (4.86, .14), (4.86, 4.86), (.14, 4.86)], edge), -.05, .03, 'DARK', 'rock')
    toppled = {3, 14}
    for index, ((sx, sy), outline) in enumerate(cells):
        outline = clip_to(outline, edge)
        if len(outline) < 3:
            continue
        _check_outline(outline, w, d)
        if index in toppled:
            b.box((sx + .1, sy - .05, .1), (.5, .38, .24), 'ROCK', 'rock', yaw=b.rng.uniform(-.6, .6))
            b.rock((sx - .25, sy + .2, .02), (.08, .08, .05), 'DARK', points=7)
            continue
        rim = min(sx, sy, w - sx, d - sy) < .8
        top = (.14 if rim else .24) + b.rng.uniform(-.03, .03)
        b.prism(outline, -.05, top, 'LIME', 'plaster', inset=.05, dome=.025, top_key='ROCK', top_tile='rock')
    return b


def sandstone_outcrop():
    b = Builder('SandstoneOutcropGeology', 'SandstoneOutcrop')
    # Three rounded beds stacked off-centre and tilted, a dark parting.
    b.prism(b.blob_outline(.5, .5, .38, .33, 11, .1), -.05, .2, 'SAND', 'plaster', inset=.04, skew=(.02, -.01))
    parting = b.blob_outline(.53, .53, .3, .26, 10, .1, .3)
    b.prism(parting, .19, .23, 'DARK', 'rock', top=False)
    b.prism(parting, .23, .42, 'SAND', 'plaster', inset=.05, skew=(-.02, .02))
    b.prism(b.blob_outline(.46, .6, .17, .15, 8, .1, .1), .4, .57, 'SAND', 'plaster', inset=.05)
    b.rock((.16, .2, .04), (.07, .06, .05), 'SAND', 'plaster', points=7)
    b.rock((.84, .82, .03), (.06, .06, .04), 'ROCK', points=7)
    return b


def limestone_outcrop():
    b = Builder('LimestoneOutcropGeology', 'LimestoneOutcrop')
    # Flat weathered beds of grey native cliff rock (2026-10-30, bricks pass:
    # the rotated pale cuboids read as a crystal). Three level beds, each
    # smaller, with dark partings; pale limestone shows only where a block
    # has freshly broken off the front of the middle bed and as one chip.
    b.prism(b.blob_outline(.5, .5, .4, .36, 11, .08), -.05, .16, 'ROCK', 'rock', inset=.035)
    parting = b.blob_outline(.48, .53, .32, .28, 10, .08, .25)
    b.prism(parting, .15, .19, 'DARK', 'rock', top=False)
    b.prism(parting, .19, .31, 'ROCK', 'rock', inset=.04, top_key='ROCK', top_tile='rock')
    upper = b.blob_outline(.53, .55, .19, .17, 9, .08, .6)
    b.prism(upper, .3, .33, 'DARK', 'rock', top=False)
    b.prism(upper, .33, .42, 'ROCK', 'rock', inset=.035)
    # Fresh break: a pale scar set into the front of the middle bed.
    b.box((.42, .29, .245), (.15, .05, .07), 'LIME', 'plaster', yaw=.18)
    b.rock((.22, .2, .03), (.07, .06, .045), 'LIME', 'plaster', points=7)
    b.rock((.84, .78, .03), (.07, .06, .05), 'DARK', points=7)
    return b


# ---------------------------------------------------------------------------
# Deep ore source (2x2x2 stockpile, entrance below the front at x 1-2): a
# rock mound split open by metallic ore, with a worked front face and spilled
# ore; the access lane in front of x 1.2-1.8 stays clear.
# ---------------------------------------------------------------------------
def deep_ore_source():
    b = Builder('DeepOreSourceGeology', 'DeepOreSource')
    b.rock((1.0, 1.32, .5), (.7, .52, .58), 'ROCK', points=14, sink=.06)
    b.rock((.48, .78, .26), (.4, .38, .32), 'DARK', points=11)
    b.rock((1.58, .92, .3), (.36, .34, .32), 'ROCK', points=11)
    b.rock((1.62, 1.62, .36), (.32, .28, .38), 'DARK', points=10)
    ore_cluster(b, (1.02, 1.2, .78), 6, .42, spread=.12)
    ore_cluster(b, (.62, .66, .38), 4, .3)
    ore_cluster(b, (1.55, .78, .4), 4, .28)
    ore_cluster(b, (1.4, 1.62, .6), 3, .26)
    for i, (x, y) in enumerate([(.42, .24), (.7, .2), (.9, .34), (.28, .44), (1.86, .28), (1.8, .5), (.6, .42), (1.05, .5)]):
        rusty = i % 3 == 1
        b.rock((x, y, .05), (.1, .085, .08), 'GOODS' if rusty else 'ORE', 'rust' if rusty else 'ore', points=7, sink=.07)
    return b


# ---------------------------------------------------------------------------
# Radioactive spring (1x1): a natural vent. A ring of dark rock round a
# crater pool, with stepped sinter crusts spilling outward. The pool and
# crusts are one node, RadioactiveGlow, that RadioactiveSpringVisual draws
# with the radioactive material; the rock keeps the native source material.
# ---------------------------------------------------------------------------
def radioactive_spring():
    rock = Builder('RadioactiveSpringRock', 'RadioactiveSpringRock')
    glow = Builder('RadioactiveGlow', 'RadioactiveGlow')
    ring = 7
    for i in range(ring):
        a = i * math.tau / ring + .2
        r = .31 + rock.rng.uniform(-.03, .03)
        rock.rock((.5 + math.cos(a) * r, .5 + math.sin(a) * r, .14), (.13, .12, .2 if i % 2 else .26), 'DARK' if i == 3 else 'ROCK', points=9)
    # Crater floor below the pool, so the pool never shows terrain beneath.
    rock.prism(rock.blob_outline(.5, .5, .3, .3, 10, .05), -.05, .11, 'DARK', 'rock')
    glow.prism(glow.blob_outline(.5, .5, .22, .21, 10, .06), .11, .15, 'ROCK', 'rock')
    # Sinter terraces stepping down and out between the rocks, toward the front.
    glow.prism(glow.blob_outline(.48, .3, .32, .2, 10, .1), -.04, .07, 'ROCK', 'rock')
    glow.prism(glow.blob_outline(.56, .16, .3, .13, 9, .12), -.04, .035, 'ROCK', 'rock')
    for x, y in [(.2, .18), (.83, .25), (.7, .82)]:
        glow.crystal((x, y, .02), .025, .09, key='ROCK', tile='rock', sides=4, lean=(glow.rng.uniform(-.3, .3), .2))
    return rock, glow


# ---------------------------------------------------------------------------
# Human record cache (3x2): an old-world records vault half buried. A sloped
# concrete bunker with a round bronze hatch in a recessed frame, rebar from a
# broken corner, two sealed record canisters and a cracked concrete apron.
# Concrete and bronze, not the vanilla relics' scrap heaps.
# ---------------------------------------------------------------------------
def human_record_cache():
    b = Builder('HumanRecordCacheVault', 'HumanRecordCache')
    # Apron: two cracked slabs, slightly tilted, sunk at the front.
    b.prism([(.2, .12), (1.45, .1), (1.5, .62), (.18, .6)], -.04, .045, 'RUIN', 'slab', inset=.02, skew=(0, .01))
    b.prism([(1.56, .14), (2.82, .18), (2.8, .62), (1.6, .6)], -.04, .03, 'RUIN', 'slab2', inset=.02, skew=(.01, 0))
    # Bunker: a wedge rising from 0.32 at the front wall to 0.78 at the back.
    x0, x1, y0, y1 = .45, 2.55, .7, 1.85
    front, back = .5, .8
    v = [(x0, y0, -.04), (x1, y0, -.04), (x1, y1, -.04), (x0, y1, -.04),
         (x0, y0, front), (x1, y0, front), (x1, y1, back), (x0, y1, back)]
    # Cast concrete (the pebbled white plaster tile), in poured panels.
    b.panels([v[4], v[5], v[6], v[7]], 4, 2, 'LIME', ['plaster'])
    b.panels([v[0], v[1], v[5], v[4]], 4, 1, 'LIME', ['plaster'])
    b.panels([v[1], v[2], v[6], v[5]], 2, 1, 'LIME', ['plaster'])
    b.panels([v[2], v[3], v[7], v[6]], 4, 1, 'LIME', ['plaster'])
    b.panels([v[3], v[0], v[4], v[7]], 2, 1, 'LIME', ['plaster'])
    # Hatch frame proud of the front wall (its back sinks into the wall), the
    # round hatch disc on it and a locking wheel through the disc.
    b.box((1.5, y0 - .02, .24), (.7, .06, .44), 'VAULT', 'panel', tiles=['panel', 'plate', 'plate', 'plate', 'plate'])
    b.cylinder((1.5, y0 - .07, .24), .18, .04, 'VAULT', 'panel', axis='Y', segments=12, caps=(True, False), cap_tile='ring')
    b.cylinder((1.5, y0 - .1, .24), .035, .03, 'VAULT', 'plate', axis='Y', segments=6, caps=(True, False))
    b.box((1.5, y0 - .095, .24), (.025, .02, .26), 'VAULT', 'plate')
    b.box((1.5, y0 - .102, .24), (.26, .02, .025), 'VAULT', 'plate')   # proud of the upright spoke: no coplanar cross
    # Old-world bronze lintel along the front edge; earth and rock banked
    # against the back and sides, so the vault reads as half buried.
    b.box(((x0 + x1) / 2, y0 - .0275, front - .055), (x1 - x0 + .04, .065, .09), 'VAULT', 'plate')
    for x, y, r, h in [(.75, 1.95, .38, .42), (1.45, 1.98, .42, .5), (2.2, 1.95, .38, .44), (.38, 1.25, .2, .3), (2.65, 1.45, .2, .32)]:
        b.rock((x, y - .16, h * .45), (r, .17, h * .55), 'ROCK', points=10)
    # Roof vent on the slope.
    b.box((2.05, 1.5, .7), (.22, .22, .16), 'VAULT', 'hex', tiles=['hex', 'ribs', 'ribs', 'ribs', 'ribs'])
    # Broken corner with rebar at the back left.
    for i, (x, y, lean) in enumerate([(.5, 1.75, (-.3, .2)), (.62, 1.8, (.1, .35)), (.5, 1.6, (-.4, -.1))]):
        top = Vector((x + lean[0] * .25, y + lean[1] * .25, back + .06 + i * .02))
        b.add([(x - .012, y - .012, back - .05), (x + .012, y - .012, back - .05), (x + .012, y + .012, back - .05), (x - .012, y + .012, back - .05),
               (top.x - .012, top.y - .012, top.z), (top.x + .012, top.y - .012, top.z), (top.x + .012, top.y + .012, top.z), (top.x - .012, top.y + .012, top.z)],
              [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)], 'RUIN', 'rebar')
    b.rock((.45, 1.82, .66), (.16, .12, .12), 'LIME', 'plaster', points=8, sink=.02)
    # Sealed record canisters: one upright, one fallen on the apron.
    b.cylinder((2.75, 1.2, .2), .12, .4, 'VAULT', 'ribs', segments=8, cap_tile='ring')
    b.cylinder((.32, .38, .1), .1, .36, 'VAULT', 'ribs', axis='X', segments=8, caps=(True, True), cap_tile='plate')
    # Rubble.
    for x, y in [(2.7, .7), (2.3, .45), (.25, 1.3), (2.65, 1.75)]:
        b.rock((x, y, .04), (.08, .07, .06), 'DARK', points=7)
    return b


# ---------------------------------------------------------------------------
# Stockpile good models (single material: the native goods atlas, as the
# vanilla GoodVisualization blueprints use). One item spans 0.78 across,
# 0.15 deep and hangs 0.17 below its origin, like 1ScrapMetal/1MetalBlock.
# ---------------------------------------------------------------------------
def deep_ore_item(builder, offset_y):
    """Two rounded dark ore nuggets lying across the cell."""
    for i in range(2):
        x = -.19 + i * .38 + builder.rng.uniform(-.015, .015)
        builder.lump((x, offset_y + builder.rng.uniform(-.012, .012), -.17),
                     (builder.rng.uniform(.15, .185), builder.rng.uniform(.065, .08), builder.rng.uniform(.09, .14)),
                     'GOODS', 'sack' if (i + round(offset_y * 10)) % 3 else 'steel')


def deep_alloy_item(builder, offset_y):
    """One trapezoid ingot with a bevelled top, rotated against MetalBlock's square bar."""
    l, w0, w1, h = .39, .075, .05, .15
    v = [(-l, offset_y - w0, -.17), (l, offset_y - w0, -.17), (l, offset_y + w0, -.17), (-l, offset_y + w0, -.17),
         (-l + .04, offset_y - w1, -.17 + h), (l - .04, offset_y - w1, -.17 + h), (l - .04, offset_y + w1, -.17 + h), (-l + .04, offset_y + w1, -.17 + h)]
    builder.add(v, [(4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6)], 'GOODS', 'steel')
    builder.add(v, [(1, 2, 6, 5), (3, 0, 4, 7)], 'GOODS', 'steelcap')


def good_models():
    """name -> Builder, for every stockpile good mesh in tools/map_objects.json."""
    out = {}
    for name, item, count in [('1DeepOre', deep_ore_item, 1), ('4DeepOres', deep_ore_item, 4),
                              ('1DeepAlloy', deep_alloy_item, 1), ('4DeepAlloys', deep_alloy_item, 4)]:
        b = Builder(name, name)
        for i in range(count):
            item(b, (i - (count - 1) / 2) * .2)
        out[name] = b
    return out


MODELS = {
    'DeepOreVein': deep_ore_vein,
    'DeepOreSource': deep_ore_source,
    'SandstoneSeam': sandstone_seam,
    'LimestoneSeam': limestone_seam,
    'SandstoneOutcrop': sandstone_outcrop,
    'LimestoneOutcrop': limestone_outcrop,
    'RadioactiveSpringSource': radioactive_spring,
    'HumanRecordCache': human_record_cache,
}
