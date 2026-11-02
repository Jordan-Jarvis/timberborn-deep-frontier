"""Geometry of a Deep Frontier construction stage (2026-11-02).

Builds construction_stage_massing.massing() into one frontier_architecture
Geometry, in the native look of the vanilla Iron Teeth ConstructionStage0
models (Smelter, LargeWarehouse, BotPartFactory, Centrifuge, MetalPlatform3x3:
an open frame on a Dirt patch, nothing else):

  - the frame follows the plan of the stage at every height. Each column is
    an interval [low, top]. At every member level (a column's low, each whole
    layer above it and its top) the cells that level crosses form a plan;
    a sill (at a low) or a girt (just under a layer line or top) runs round
    that plan's outline, inset by half a post so nothing leaves the
    footprint. Posts stand at the outline corners and every postSpacing
    tiles (clear of the corners), each over its own column from low to top;
    roof joists cross each top level on the short side between face posts;
    the bottom bays of grounded walls carry diagonal braces. Girts, joists
    and braces are thinner than the posts and end inside them, member levels
    are at least a quarter layer apart, so no two faces are coplanar;
  - timber (BaseWood_DarkBrown.IronTeeth, the board strips the vanilla stages
    use: u .5-.75, v .5-1) or a metal frame (BaseMetal.IronTeeth girder
    strips, u 0-.5, v 0-.5, as BotPartFactory's stage) on timber sills;
  - the Dirt patch over the grounded cells: the vanilla DirtURP contract, a
    rim fading from v 0 at `outside` beyond the footprint edge to v 1 at `rim`
    inside it, v 1 over the rest (concave corners mitred, convex corners
    squared, no two pieces overlap).

Every face has one explicit UV island inside its atlas tile. Units: x = block
X, y = block Y, z = model height; frontier_architecture stores the exporter's
source coordinates.
"""
import math
import sys
from pathlib import Path

from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from frontier_architecture import Geometry  # noqa: E402
from construction_stage_massing import CONFIG  # noqa: E402

MATERIALS = CONFIG['materials']
WOOD, METAL, DIRT = range(3)
TILES = {
    # BaseWood_1K_D_Grey: the upper-right board strips the vanilla stages use.
    **{f'wood{k}': (WOOD, (.5 + k / 16 + .004, .505, .5 + (k + 1) / 16 - .004, .995)) for k in range(4)},
    'woodEnd': (WOOD, (.637, .137, .743, .243)),        # log end rings
    # BaseMetal_D2: the girder strips of the lower-left quadrant.
    **{f'metal{k}': (METAL, (k / 16 + .006, .01, (k + 1) / 16 - .006, .49)) for k in range(1, 8)},
    'metalEnd': (METAL, (.06, .56, .16, .66)),           # plain plate
}
EPS = 1e-6


class Kit:
    def __init__(self, name):
        self.g = Geometry(name)
        self.turn = 0

    def strip(self, material):
        self.turn += 1
        return f'wood{self.turn % 4}' if material == WOOD else f'metal{1 + self.turn % 7}'

    def face(self, points, tile, along):
        material, (u0, v0, u1, v1) = TILES[tile]
        pts = [Vector(p) for p in points]
        normal = Vector((0, 0, 0))
        for i in range(1, len(pts) - 1):
            normal += (pts[i] - pts[0]).cross(pts[i + 1] - pts[0])
        if normal.length < 1e-12:
            raise ValueError(f'{self.g.name}: degenerate face {points}')
        normal.normalize()
        a = Vector(along)
        a = a - normal * a.dot(normal)
        if a.length < 1e-6:
            a = Vector((1, 0, 0)) - normal * normal.x
        a.normalize()
        across = normal.cross(a)
        coords = [(p.dot(across), p.dot(a)) for p in pts]
        lo = [min(c[i] for c in coords) for i in range(2)]
        span = [max(c[i] for c in coords) - lo[i] for i in range(2)]
        if min(span) < 1e-9:
            raise ValueError(f'{self.g.name}: face without area {points}')
        uvs = [(u0 + (c[0] - lo[0]) / span[0] * (u1 - u0), v0 + (c[1] - lo[1]) / span[1] * (v1 - v0)) for c in coords]
        self.g.native_piece([tuple(p) for p in pts], [tuple(range(len(pts)))], uvs, material)

    def bar(self, a, b, width, depth, material, up=(0, 0, 1), skip_bottom=False):
        """A rectangular bar from a to b (open ends: they lie inside posts), grain
        along it; `width` across, `depth` along `up`'s component normal to the bar."""
        a, b = Vector(a), Vector(b)
        axis = b - a
        if axis.length < 1e-6:
            raise ValueError(f'{self.g.name}: zero-length bar at {tuple(a)}')
        axis.normalize()
        side = axis.cross(Vector(up))
        if side.length < 1e-6:
            side = axis.cross(Vector((1, 0, 0)))
        side.normalize()
        normal = side.cross(axis).normalized()
        w, d = side * width / 2, normal * depth / 2
        ring = [-w - d, w - d, w + d, -w + d]
        lo = [a + r for r in ring]
        hi = [b + r for r in ring]
        tile = self.strip(material)
        for i in range(4):
            j = (i + 1) % 4
            face = [lo[i], lo[j], hi[j], hi[i]]
            if skip_bottom and all(p.z < min(a.z, b.z) - 1e-6 for p in face):
                continue
            self.face(face, tile, axis)

    def post(self, x, y, z0, z1, size, material, grounded):
        """A vertical post centred on (x, y): no bottom face on the ground."""
        h = size / 2
        corners = [(x - h, y - h), (x + h, y - h), (x + h, y + h), (x - h, y + h)]
        tile = self.strip(material)
        for i in range(4):
            (ax, ay), (bx, by) = corners[i], corners[(i + 1) % 4]
            self.face([(ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1)], tile, (0, 0, 1))
        end = 'woodEnd' if material == WOOD else 'metalEnd'
        self.face([(cx, cy, z1) for cx, cy in corners], end, (1, 0, 0))
        if not grounded:
            self.face([(cx, cy, z0) for cx, cy in reversed(corners)], end, (1, 0, 0))

    def dirt_quad(self, points, uvs):
        self.g.native_piece([tuple(p) for p in points], [tuple(range(len(points)))], uvs, DIRT)


def unit_edges(cells):
    """Boundary unit edges of a cell set: (axis, line, side, unit). axis 'x':
    on the line y = line, covering x in [unit, unit + 1]; side +1 when the
    region lies on the + side of the line."""
    out = set()
    for (x, y) in cells:
        if (x, y - 1) not in cells:
            out.add(('x', y, 1, x))
        if (x, y + 1) not in cells:
            out.add(('x', y + 1, -1, x))
        if (x - 1, y) not in cells:
            out.add(('y', x, 1, y))
        if (x + 1, y) not in cells:
            out.add(('y', x + 1, -1, y))
    return out


def corner_count(cells, vx, vy):
    return sum(c in cells for c in ((vx - 1, vy - 1), (vx, vy - 1), (vx - 1, vy), (vx, vy)))


def outline(cells, m):
    """Inset outline runs of a cell set: dicts with axis, line, side, the inset
    coordinate `at`, the run's start/end along its axis and its units."""
    groups = {}
    for axis, line, side, unit in unit_edges(cells):
        groups.setdefault((axis, line, side), []).append(unit)
    runs = []
    for (axis, line, side), units in sorted(groups.items()):
        units.sort()
        start = units[0]
        for i, u in enumerate(units):
            if i + 1 == len(units) or units[i + 1] != u + 1:
                ends = []
                for v, sign in ((start, 1), (u + 1, -1)):
                    vx, vy = (v, line) if axis == 'x' else (line, v)
                    count = corner_count(cells, vx, vy)
                    # Convex (1) or diagonal (2): trim by half a post; concave (3): extend.
                    ends.append(v + sign * m if count != 3 else v - sign * m)
                runs.append({'axis': axis, 'line': line, 'side': side, 'at': line + side * m,
                             'start': ends[0], 'end': ends[1], 'units': list(range(start, u + 1))})
                if i + 1 < len(units):
                    start = units[i + 1]
    return runs


def plan_point(run, s):
    return (s, run['at']) if run['axis'] == 'x' else (run['at'], s)


def frame(kit, columns, frame_kind, dims, ground):
    """The outline frame over {(x, y): (low, top)}; ground: {(x, y): height}."""
    material = METAL if frame_kind == 'metal' else WOOD
    p, b, inset = dims['post'], dims['beam'], dims['inset']
    bw, bd = dims['brace']
    m = p / 2
    spacing = CONFIG['frame']['postSpacing']
    clearance = CONFIG['frame']['spacingClearance']
    min_level_gap = CONFIG['frame']['minimumHeight']
    levels = set()
    for low, top in columns.values():
        levels.add(('sill', low))
        levels.add(('girt', top))
        for k in range(math.ceil(low + min_level_gap - EPS), math.floor(top + EPS) + 1):
            levels.add(('girt', float(k)))
    rings = []   # (kind, level, cells, runs)
    for kind, level in sorted(levels, key=lambda l: (l[1], l[0])):
        if kind == 'sill':
            cells = {c for c, (low, top) in columns.items() if abs(low - level) < EPS}
        else:
            cells = {c for c, (low, top) in columns.items() if low + min_level_gap - EPS <= level <= top + EPS}
        if cells:
            rings.append((kind, level, cells, outline(cells, m)))
    # Posts: every run end, and spacing points clear of every run end on the
    # same line. A post stands on its column's low and rises to the highest
    # member that meets it: a girt's level, or just over a sill (a node).
    def member_top(kind, level):
        return level + .01 + b + .02 if kind == 'sill' else level

    reach = {}
    vertices = set()
    for kind, level, _, runs in rings:
        for run in runs:
            for s in (run['start'], run['end']):
                point = tuple(round(c, 6) for c in plan_point(run, s))
                vertices.add(point)
                reach[point] = max(reach.get(point, -1e9), member_top(kind, level))
    for kind, level, _, runs in rings:
        for run in runs:
            k = math.floor(run['start'] / spacing) + 1
            while k * spacing < run['end'] - clearance + EPS:
                s = k * spacing
                k += 1
                if s < run['start'] + clearance - EPS:
                    continue
                point = tuple(round(c, 6) for c in plan_point(run, s))
                index = 0 if run['axis'] == 'x' else 1
                if any(abs(v[1 - index] - point[1 - index]) < EPS and abs(v[index] - point[index]) < clearance - EPS
                       for v in vertices):
                    continue
                reach[point] = max(reach.get(point, -1e9), member_top(kind, level))
    posts = set(reach)
    post_span = {}
    for x, y in sorted(posts):
        cell = (math.floor(x), math.floor(y))
        if cell not in columns:
            raise ValueError(f'{kit.g.name}: post at {(x, y)} outside the stage columns')
        low, top = columns[cell]
        span = (low, min(top, reach[(x, y)]))
        post_span[(x, y)] = span
        kit.post(x, y, span[0], span[1], p, material, ground.get(cell) == low)
    # Sills and girts round every ring.
    for kind, level, cells, runs in rings:
        z = level + .01 + b / 2 if kind == 'sill' else level - inset - b / 2
        grounded_sill = kind == 'sill'
        for run in runs:
            a = plan_point(run, run['start'])
            e = plan_point(run, run['end'])
            if kind == 'sill':
                on_ground = all(ground.get(c) == level for c in cells)
            kit.bar((*a, z), (*e, z), b, b, WOOD if kind == 'sill' else material,
                    skip_bottom=grounded_sill and on_ground)
    # Roof joists over each top, across its short side, between face posts.
    tops = sorted({top for _, top in columns.values()})
    for top in tops:
        region = {c for c, (low, t) in columns.items() if abs(t - top) < EPS}
        xs = [c[0] for c in region]
        ys = [c[1] for c in region]
        along = 'y' if max(xs) - min(xs) >= max(ys) - min(ys) else 'x'   # joist direction
        z = top - inset - b / 2
        lines = {}
        for (x, y) in posts:
            key = x if along == 'y' else y
            if abs(key - round(key)) < EPS:
                lines.setdefault(round(key), []).append((x, y))
        for key, points in sorted(lines.items()):
            points.sort(key=lambda q: q[1] if along == 'y' else q[0])
            for q0, q1 in zip(points, points[1:]):
                s0, s1 = (q0[1], q1[1]) if along == 'y' else (q0[0], q1[0])
                if s1 - s0 < .5 or post_span[q0][1] < top - EPS or post_span[q1][1] < top - EPS:
                    continue
                # Both cells either side of the joist line, under its whole span, top out here.
                cells = [(key - 1, j) for j in range(math.floor(s0), math.ceil(s1))] + \
                        [(key, j) for j in range(math.floor(s0), math.ceil(s1))]
                if along == 'x':
                    cells = [(c[1], c[0]) for c in cells]
                if all(abs(columns.get(c, (0, -1))[1] - top) < EPS for c in cells):
                    kit.bar((*q0, z), (*q1, z), b, b, material)
    # Braces in the bottom bays of grounded walls: where the sill ring at the
    # ground and the girt ring one layer up share an outline edge.
    sill_edges, girt_edges = set(), set()
    for kind, level, cells, runs in rings:
        if kind == 'sill' and abs(level) < EPS:
            sill_edges |= unit_edges(cells)
        if kind == 'girt' and abs(level - 1) < EPS:
            girt_edges |= unit_edges(cells)
    braced = sill_edges & girt_edges
    if braced:
        z0, z1 = .01 + b / 2, 1 - inset - b / 2
        turn = 0
        lines = {}
        for axis, line, side, unit in braced:
            lines.setdefault((axis, line, side), set()).add(unit)
        for (axis, line, side), units in sorted(lines.items()):
            at = line + side * m
            index = 0 if axis == 'x' else 1
            on_line = sorted(q for q in posts if abs(q[1 - index] - at) < EPS)
            for q0, q1 in zip(on_line, on_line[1:]):
                s0, s1 = q0[index], q1[index]
                if s1 - s0 < .6 or post_span[q0][0] != 0 or post_span[q1][0] != 0 or min(post_span[q0][1], post_span[q1][1]) < 1 - EPS:
                    continue
                if not all(u in units for u in range(math.floor(s0), math.ceil(s1))):
                    continue
                turn += 1
                lo_end, hi_end = (q0, q1) if turn % 2 else (q1, q0)
                kit.bar((*lo_end, z0), (*hi_end, z1), bw, bd, material, up=(0, 1, 0) if axis == 'x' else (1, 0, 0))


def dirt(kit, cells, outside, rim, lift):
    """The Dirt patch over grounded cells {(x, y): model height}."""
    by_height = {}
    for (x, y), h in cells.items():
        by_height.setdefault(h, set()).add((x, y))
    edge_v = outside / (outside + rim)
    for h, region in sorted(by_height.items()):
        z = h + lift
        edges = []   # boundary unit segments with the outward normal
        for (x, y) in region:
            if (x - 1, y) not in region:
                edges.append(((x, y), (x, y + 1), (-1, 0)))
            if (x + 1, y) not in region:
                edges.append(((x + 1, y), (x + 1, y + 1), (1, 0)))
            if (x, y - 1) not in region:
                edges.append(((x, y), (x + 1, y), (0, -1)))
            if (x, y + 1) not in region:
                edges.append(((x, y + 1), (x + 1, y + 1), (0, 1)))

        def distance(px, py):
            best = 1e9
            for (ax, ay), (bx, by), _ in edges:
                cx = min(max(px, min(ax, bx)), max(ax, bx))
                cy = min(max(py, min(ay, by)), max(ay, by))
                best = min(best, math.hypot(px - cx, py - cy))
            return best

        def v_inside(px, py):
            return min(1.0, (outside + distance(px, py)) / (outside + rim))

        def concave(px, py):
            return corner_count(region, px, py) == 3

        for (x, y) in sorted(region):
            near = [(x - 1, y) not in region, (x + 1, y) not in region, (x, y - 1) not in region, (x, y + 1) not in region]
            xcuts = [0.0, 1.0]
            ycuts = [0.0, 1.0]
            if near[0] or concave(x, y) or concave(x, y + 1):
                xcuts.insert(1, rim)
            if near[1] or concave(x + 1, y) or concave(x + 1, y + 1):
                xcuts.insert(len(xcuts) - 1, 1 - rim)
            if near[2] or concave(x, y) or concave(x + 1, y):
                ycuts.insert(1, rim)
            if near[3] or concave(x, y + 1) or concave(x + 1, y + 1):
                ycuts.insert(len(ycuts) - 1, 1 - rim)
            for i in range(len(xcuts) - 1):
                for j in range(len(ycuts) - 1):
                    u0, u1, w0, w1 = xcuts[i], xcuts[i + 1], ycuts[j], ycuts[j + 1]
                    quad = [(x + u0, y + w0), (x + u1, y + w0), (x + u1, y + w1), (x + u0, y + w1)]
                    kit.dirt_quad([(px, py, z) for px, py in quad], [(px - x, v_inside(px, py)) for px, py in quad])
        # The fade beyond the edge: a strip `outside` wide, mitred at concave
        # corners; convex corners get a square.
        for (ax, ay), (bx, by), (nx, ny) in edges:
            tx, ty = bx - ax, by - ay
            pull_a = outside if concave(ax, ay) else 0.0
            pull_b = outside if concave(bx, by) else 0.0
            a_out = (ax + nx * outside + tx * pull_a, ay + ny * outside + ty * pull_a)
            b_out = (bx + nx * outside - tx * pull_b, by + ny * outside - ty * pull_b)
            quad = [((ax, ay), edge_v), ((bx, by), edge_v), (b_out, 0.0), (a_out, 0.0)]
            if nx > 0 or ny < 0:   # keep the face up: counter-clockwise seen from above
                quad.reverse()
            kit.dirt_quad([(px, py, z) for (px, py), _ in quad],
                          [(min(1.0, max(0.0, (px - ax) * tx + (py - ay) * ty)), v) for (px, py), v in quad])
            if nx == 0:
                continue   # each convex corner once, from its edge with an x normal
            for (px, py) in ((ax, ay), (bx, by)):
                around = [(px - 1, py - 1), (px, py - 1), (px - 1, py), (px, py)]
                inside = [c for c in around if c in region]
                if len(inside) != 1:
                    continue
                sx = -1 if inside[0][0] == px else 1
                sy = -1 if inside[0][1] == py else 1
                square = [(px, py), (px + sx * outside, py), (px + sx * outside, py + sy * outside), (px, py + sy * outside)]
                if sx * sy < 0:
                    square.reverse()
                kit.dirt_quad([(qx, qy, z) for qx, qy in square],
                              [(0.0, edge_v if (qx, qy) == (px, py) else 0.0) for qx, qy in square])


def build(massing):
    kit = Kit(f"{massing['id']}.ConstructionStage0")
    dims = CONFIG['frame'][massing['frame']]
    ground = {(x, y): h for x, y, h in massing['dirt']}
    columns = {(x, y): (low, top) for x, y, low, top in massing['columns']}
    frame(kit, columns, massing['frame'], dims, ground)
    d = CONFIG['dirt']
    dirt(kit, ground, d['outside'], d['rim'], d['height'])
    return kit.g
