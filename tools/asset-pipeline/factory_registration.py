"""Native-grid registration helpers for the crusher, kiln and mixer artwork.

Structural interfaces (deck edges, walls facing open cells, rails, footings,
doors) are authored directly in native grid XY (origin 0 unless the layout
says otherwise; Z is the whole-layer height). Reviewed assemblies that were
authored in an earlier artwork frame keep their exact local dimensions and are
placed rigidly with RigidPlacement: vertices and animation pivots move by the
same explicit offset. Nothing is scaled, rounded or fitted to bounds.
"""
import math
from mathutils import Vector
from frontier_architecture import Geometry

# Post half-width of the native Double Lodge rail kit (housing_railing.post):
# +-0.070 across X and +-0.081 across Y. Rails run 0.08 inside the tile edge,
# so their outer face is on the boundary (within 1 cm). Posts on whole-cell
# boundaries stay when a cell opens; corner posts sit 0.08 inside the corner
# cell, so the exporter (which hides posts more than 0.075 inside an opened
# cell) removes them together with that cell's corner return: no lone post.
RAIL_INSET = .08


class RigidPlacement(Geometry):
    """Place an assembly authored in an earlier artwork frame on the grid frame.

    Only translation. Moving parts get the same offset for vertices and
    pivots. Window-mount records are translated with their vertices.
    """
    def __init__(self, target, offset):
        self.target = target
        self.offset = Vector(offset)
        self.window_mounts = _TranslatedMounts(target, self.offset)

    def add(self, vertices, faces, mat):
        self.target.add([Vector(v) + self.offset for v in vertices], faces, mat)

    # Face-indexed records (native UV islands, provenance) belong to the
    # target mesh. Position-bearing records (doorways, native props) are not
    # delegated: authoring them through a placement is an error.
    def __getattr__(self, name):
        if name in ('faces', 'face_uvs', 'face_sources', 'materials'):
            return getattr(self.target, name)
        raise AttributeError(f'RigidPlacement does not delegate {name!r}')

    def moving_part(self, name, origin):
        part = Geometry(name, Vector(origin) + self.offset)
        return RigidPlacement(part, self.offset), part

    def include_component(self, component):
        raise ValueError('Components are authored in the registered grid frame; include them on the target')


class _TranslatedMounts:
    def __init__(self, target, offset):
        self.target, self.offset = target, offset

    def append(self, mount):
        dx, dy, dz = self.offset
        mount = dict(mount)
        mount['anchor'] = [mount['anchor'][0] + dx, mount['anchor'][1] + dy, mount['anchor'][2] + dz]
        mount['rearEdges'] = [[tuple(Vector(p) + self.offset) for p in edge] for edge in mount['rearEdges']]
        self.target.window_mounts.append(mount)


def cell_rails(rails, prefix, axis, line, start, end, z, *, per_cell=2, cell_offset=0):
    """One rail run per native cell along a tile edge, posts on cell boundaries.

    axis 'X': the rail runs along X at Y=line; 'Y': along Y at X=line.
    start/end are the run's endpoints along that axis (the first/last may be
    inset corner positions). Interior breakpoints are the whole-cell
    boundaries between them (the layout origin must be integer). Run IDs are
    prefix + native cell index (artwork cell + cell_offset, the layout origin
    on that axis), which is what the layout's rail ports reference.
    """
    if axis not in ('X', 'Y') or end <= start:
        raise ValueError('Cell rails need an axis and increasing endpoints')
    cuts = [start] + [k for k in range(math.floor(start) + 1, math.ceil(end)) if start < k < end] + [end]
    runs = []
    for a, b in zip(cuts, cuts[1:]):
        cell = math.floor((a + b) / 2)
        ident = f'{prefix}{cell + cell_offset}'
        p, q = ((a, line), (b, line)) if axis == 'X' else ((line, a), (line, b))
        segments = max(1, round((b - a) * per_cell)) if b - a > .3 else 1
        rails.run(ident, p, q, z, segments=segments)
        runs.append(ident)
    return runs


def machine_slab(g, x0, y0, x1, y1, top, thickness=.20, mat=None):
    """Solid cap or plinth (not a walking deck): machinery housings and
    process floors stand on it. Edges are authored on tile lines where they
    are outer faces; top is a whole layer. `mat` defaults to concrete; the
    pre-concrete buildings pass stone masonry or metal (user 2026-10-30: a
    building that unlocks before concrete must not show concrete)."""
    from reference_materials import CIVIC_CONCRETE
    if x1 <= x0 or y1 <= y0 or thickness <= 0:
        raise ValueError('Machine slab needs a positive extent')
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, top - thickness / 2), (x1 - x0, y1 - y0, thickness),
          CIVIC_CONCRETE if mat is None else mat)


def masonry_box(g, center, size, *, course=.25, seed=0):
    """Solid block of coursed stone masonry: courses of grey and pale kiln
    masonry (KILN_STONE / KILN_STONE_LIGHT), every other course 6 mm proud,
    so the joints read at game zoom. For footings, piers and pedestals of the
    buildings that unlock before concrete exists (user 2026-10-30)."""
    from reference_materials import KILN_STONE, KILN_STONE_LIGHT
    (cx, cy, cz), (sx, sy, sz) = center, size
    if min(sx, sy, sz) <= 0:
        raise ValueError('Masonry block needs a positive size')
    n = max(1, round(sz / course))
    z0 = cz - sz / 2
    for i in range(n):
        a, b = z0 + sz * i / n, z0 + sz * (i + 1) / n
        proud = .006 if (i + seed) % 2 else 0
        g.box((cx, cy, (a + b) / 2), (sx + 2 * proud, sy + 2 * proud, b - a),
              KILN_STONE_LIGHT if (i + seed) % 2 else KILN_STONE)


def flagstone_slab(g, x0, y0, x1, y1, top, thickness=.20, *, stone=.5, seed=0):
    """machine_slab in stone: a grey masonry body under a top course of
    flagstones about `stone` across, alternating grey and pale, their tops at
    most 6 mm below `top` (one flat plane)."""
    import random
    from reference_materials import KILN_STONE, KILN_STONE_LIGHT
    if x1 <= x0 or y1 <= y0 or thickness <= .07:
        raise ValueError('Flagstone slab needs a positive extent')
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, top - .06 - (thickness - .06) / 2), (x1 - x0, y1 - y0, thickness - .06), KILN_STONE)
    rng = random.Random(seed)
    nx, ny = max(1, round((x1 - x0) / stone)), max(1, round((y1 - y0) / stone))
    for i in range(nx):
        for j in range(ny):
            a, b = x0 + (x1 - x0) * i / nx, x0 + (x1 - x0) * (i + 1) / nx
            c, d = y0 + (y1 - y0) * j / ny, y0 + (y1 - y0) * (j + 1) / ny
            h = .06 - rng.choice((0, .003, .006))
            g.box(((a + b) / 2, (c + d) / 2, top - .06 + h / 2), (b - a, d - c, h),
                  KILN_STONE_LIGHT if (i + j) % 2 else KILN_STONE)


def brick_box(g, center, size, *, faces=('front', 'back', 'left', 'right'), cap=.04):
    """Solid block faced with running-bond bricks (2026-10-30, bricks pass;
    it replaces masonry_box on the mixer): a cement-dust mortar core
    (DFIndustrial24) set back by the brick depth on the bricked faces, bricks
    in the native brick-red plaster (Plaster_Orange.IronTeeth) and a grey
    kiln-masonry cap (DFIndustrial14) across the full top, so the block's
    extents and its standing surface are unchanged. Front and back courses
    run corner to corner; the side courses stop short of them."""
    from reference_materials import KILN_STONE, KILN_DUST, CIVIC_ORANGE_PANEL
    from lategame_mining_parts import _brick_runs, BRICK_COURSE, BRICK_JOINT, BRICK_PROUD, BRICK_EMBED
    (cx, cy, cz), (sx, sy, sz) = center, size
    if min(sx, sy, sz) <= 0 or sz <= cap:
        raise ValueError('Brick block needs a positive size taller than its cap')
    x0, x1, y0, y1, z0, z1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz - sz / 2, cz + sz / 2
    d, e, j = BRICK_PROUD, BRICK_EMBED, BRICK_JOINT
    ca, cb = x0 + (d if 'left' in faces else 0), x1 - (d if 'right' in faces else 0)
    da, db = y0 + (d if 'front' in faces else 0), y1 - (d if 'back' in faces else 0)
    top = z1 - cap
    g.box(((ca + cb) / 2, (da + db) / 2, (z0 + top) / 2), (cb - ca, db - da, top - z0), KILN_DUST)
    g.box((cx, cy, z1 - cap / 2), (sx, sy, cap), KILN_STONE)
    n = max(1, round((top - z0) / BRICK_COURSE))
    pitch = (top - z0) / n
    side = (da + e + j if 'front' in faces else da, db - e - j if 'back' in faces else db)
    runs = {'front': (x0, x1), 'back': (x0, x1), 'left': side, 'right': side}
    for row in range(n):
        za, zb = z0 + row * pitch + j / 2, z0 + (row + 1) * pitch - j / 2
        for face in faces:
            for u, v in _brick_runs(*runs[face], row % 2):
                u, v = u + j / 2, v - j / 2
                if face == 'front':
                    lo, hi = (u, y0, za), (v, da + e, zb)
                elif face == 'back':
                    lo, hi = (u, db - e, za), (v, y1, zb)
                elif face == 'left':
                    lo, hi = (x0, u, za), (ca + e, v, zb)
                else:
                    lo, hi = (cb - e, u, za), (x1, v, zb)
                g.box(tuple((lo[i] + hi[i]) / 2 for i in range(3)), tuple(hi[i] - lo[i] for i in range(3)), CIVIC_ORANGE_PANEL)
