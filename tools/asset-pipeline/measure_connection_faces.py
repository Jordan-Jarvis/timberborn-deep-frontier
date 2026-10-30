"""Measure the flat exterior cell faces of every Deep Frontier building model.

A building accepts native power shafts and Timber Pipes on every flat
exterior surface (user direction, 2026-10-23). This measures the geometry the
game draws: each model's exported finished Timbermesh (the owning export of
validate_triangle_budget.OWNERS), in the native grid frame of its blueprint
(Unity X, Y, Z -> grid x = X, y = Z, z = Y + BaseZ; CoordinateSystem.GridToWorld).

For every cell of the blueprint's Size and each of its six faces (Left/Right/
Down/Up horizontal, Bottom/Top vertical) it casts SAMPLES x SAMPLES rays along
the face normal, starting FRONT outside the face plane and pointing inward:

- flat:     one flat plane parallel to the cell face covers it (user rule,
            2026-10-23: "we don't want to be able to connect to the curved
            edges, just the flat ones"). The samples whose nearest static
            surface (opaque or glass: flat glazing is a flat wall, user
            2026-10-26, the Greenhouse) lies within WALL_DEPTH behind the plane
            (or up to FRONT proud of it) are the covering surface.
            * No curve or slope, even partly: every covering normal lies
              within AXIS_ANGLE of the face's outward axis and within
              NORMAL_SPREAD of the covering mean. Domes, cylinders, tanks,
              rounded corners, pitched or curved roofs, faceted curves and
              bevels anywhere on the face disqualify it.
            * One plane: the samples of a single wall plane (depths within
              PLANE_SPREAD of each other) cover at least COVER of the face;
              parallel relief on the rest (trim, a plinth step) is allowed. The
              plane may be the glazing or the wall it is set in (windows proud
              of or recessed from a flat wall do not break the wall).
              PLANE_SPREAD is 0.05, not 0.02: timber frames stand 0.03-0.04
              proud of their infill on the Fishery, Hospital and crusher walls
              that carry the in-game-tested shaft sockets, and requiring the
              whole covering area within 0.02 left the crusher with no face.
            Back faces are invisible from outside and never cover a face.
- animated: geometry of an animated node (or a descendant of one) stands in
            front of the face, within the outward neighbour cell, on any sample.
            A shaft or pipe there would cut through moving parts.

Window glass covers a face like any other static surface: flat glazing
qualifies, curved glass (domes) fails the curve test like curved metal. Lamp
glass of wall lanterns is not a wall surface. Excluded from the surfaces: the native liquid
material (Water), walkway rails (WalkwayRail.*) and animated nodes. Native props are not in the
model (NativeBuildingPropsSpec) and are therefore never walls.

For roofs it also records, per flat horizontal roof face (Top), what stands on
it. 'roof.blocked' lists the flat roof faces with static geometry of the
building (any side of any triangle, glass included) inside the inner box of the
cell above: its middle, 0.31 in from every cell edge (railings, trim and
walls standing near the cell boundary do not block), from ROOF_LIP over the roof
plane to the top of that cell, probed along all three axes so vertical panels
count too (a stack, mast, tank, vent or frame would cut through anything built
there). 'roof.covered' lists those whose inner area does not see the sky (an
overhang or upper storey somewhere above). 'roof.animated' are flat roof faces
dropped for an animated part above.
tools/roof_deck_content.mjs makes the clear ones platformable.

The result is geometric only. tools/connection_content.mjs decides which of
these faces are exterior (occupied cell, neighbour open to the outside) and
which are doors or access cells. Writes outputs/connection-faces/<Template>.json
with the measured export's SHA-256, so generation refuses a stale record.

  python measure_connection_faces.py --data <generated Data root> [--only A,B] [--out DIR]

validate_connection_exports.py re-measures and compares (validate_all exports-connection).
"""
import argparse
import hashlib
import json
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2  # noqa: E402
from validate_triangle_budget import OWNERS, models_of  # noqa: E402

SAMPLES = 8
WALL_DEPTH = .35     # flat walls set back by trim or a plinth still count (user choice)
COVER = .6
FRONT = .02
AXIS_ANGLE = 5.      # degrees between a covering normal and the face axis
NORMAL_SPREAD = 1.   # degrees between a covering normal and the covering mean
PLANE_SPREAD = .05   # depth band of the one plane that must cover COVER of the face (timber frame relief)
CURVE_NORMALS = 3    # distinct off-axis normal directions that make a face curved (reported)
OLD_DEPTH, OLD_FACING = .12, .6   # the superseded depth-band rule, reported only
ANIMATED_REACH = 1.  # the whole outward neighbour cell
ROOF_LIP = .1        # roof trim and lips up to 0.1 above a roof plane do not block it
# static_mesh_merge.LIGHTING_MATERIALS: window glazing (the window atlas, DFIndustrial09
# ReferenceWindow) covers a wall like any surface; lamp glass (DFIndustrial08
# ReferenceWarmLight) belongs to faceted wall lanterns standing off the wall, so it
# never makes a wall curved (it still blocks a roof cell, as any geometry does).
GLASS = frozenset({'WindowsAtlas.IronTeeth', 'DFIndustrial09'})
LAMP_GLASS = frozenset({'DFIndustrial08'})
LIQUIDS = frozenset({'Water'})
DIRECTIONS = (('Left', 0, -1), ('Right', 0, 1), ('Down', 1, -1), ('Up', 1, 1), ('Bottom', 2, -1), ('Top', 2, 1))
RULE = (f'{SAMPLES}x{SAMPLES} rays per face; covering surface = nearest opaque static surface within {WALL_DEPTH} behind '
        f'(or {FRONT} proud of) the face plane; every covering normal within {AXIS_ANGLE} deg of the outward axis and '
        f'{NORMAL_SPREAD} deg of the covering mean; one plane (depths within {PLANE_SPREAD}) covers >= {COVER:.0%}; glass counts '
        f'as a surface; no animated geometry within {ANIMATED_REACH} in front')
OUT = ROOT / 'outputs/connection-faces'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_matrix(node):
    x, y, z, w = node.rotation.x, node.rotation.y, node.rotation.z, node.rotation.w
    rotation = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    matrix = np.eye(4)
    matrix[:3, :3] = rotation * np.array([node.scale.x, node.scale.y, node.scale.z])
    matrix[:3, 3] = (node.position.x, node.position.y, node.position.z)
    return matrix


_TRIANGLES = {}


def triangles(path, base_z):
    """Grid-frame triangles by kind: opaque, glass, animated. Outward normals
    follow -cross(v1 - v0, v2 - v0) in the grid frame (the Unity winding seen
    through the Y/Z swap); checked on every model's outer left wall.

    Decoded once per file version and BaseZ per process: the pure-Python
    protobuf decode is most of validate_connection_exports' time, and it
    reads every export two or three times. The arrays are read-only."""
    stat = Path(path).stat()
    key = (str(Path(path).resolve()), base_z, stat.st_size, stat.st_mtime_ns)
    if key not in _TRIANGLES:
        kinds = _decode_triangles(path, base_z)
        for array in kinds.values():
            array.setflags(write=False)
        _TRIANGLES[key] = kinds
    return _TRIANGLES[key]


def _decode_triangles(path, base_z):
    model = model_pb2.Model()
    model.ParseFromString(zlib.decompress(path.read_bytes()))
    animated = set()
    for i, node in enumerate(model.nodes):
        k, chain = node, []
        while True:
            chain.append(k)
            if k.parent == -1:
                break
            k = model.nodes[k.parent]
        if any(c.nodeAnimations or c.vertexAnimations for c in chain):
            animated.add(i)
    kinds = {'opaque': [], 'glass': [], 'lamp': [], 'animated': []}
    for i, node in enumerate(model.nodes):
        if node.vertexCount <= 0:
            continue
        # Rest pose: parent ... local, each node T * R * S (Unity space).
        matrix, k = np.eye(4), node
        while True:
            matrix = local_matrix(k) @ matrix
            if k.parent == -1:
                break
            k = model.nodes[k.parent]
        position = next(p for p in node.vertexProperties if p.name == 'position')
        local = np.frombuffer(position.data, dtype='<f4').reshape(-1, 3).astype(np.float64)
        unity = local @ matrix[:3, :3].T + matrix[:3, 3]
        grid = np.column_stack((unity[:, 0], unity[:, 2], unity[:, 1] + base_z))
        rail = node.name.startswith('WalkwayRail.')
        for mesh in node.meshes:
            if len(mesh.indices) % 3:
                raise ValueError(f'{path.name}: {node.name} is not triangulated')
            indices = np.asarray(mesh.indices, dtype=np.int64).reshape(-1, 3)
            if np.linalg.det(matrix[:3, :3]) < 0:   # a mirrored node reverses its winding
                indices = indices[:, ::-1]
            tris = grid[indices]
            if i in animated:
                kinds['animated'].append(tris)
            elif mesh.material in GLASS:
                kinds['glass'].append(tris)
            elif mesh.material in LAMP_GLASS:
                kinds['lamp'].append(tris)
            elif mesh.material in LIQUIDS or rail:
                continue
            else:
                kinds['opaque'].append(tris)
    return {k: (np.concatenate(v) if v else np.zeros((0, 3, 3))) for k, v in kinds.items()}


class AxisHits:
    """All triangle crossings of the axis-parallel sample rays of one axis.
    Sample (iu, iv) sits at ((iu + .5) / SAMPLES, (iv + .5) / SAMPLES) in the
    two perpendicular axes; each crossing records its depth along the axis and
    its outward normal component along that axis."""

    def __init__(self, tris, axis, size, sign):
        b, c = [a for a in range(3) if a != axis]
        self.axis, self.b, self.c = axis, b, c
        self.nu, self.nv = size[b] * SAMPLES, size[c] * SAMPLES
        self.keys = np.zeros(0)
        self.depth = np.zeros(0)
        self.normal = np.zeros((0, 3))
        if not len(tris):
            return
        normal = -np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        length = np.linalg.norm(normal, axis=1)
        P = tris[:, :, [b, c]] * SAMPLES - .5          # sample-index space
        area = (P[:, 1, 0] - P[:, 0, 0]) * (P[:, 2, 1] - P[:, 0, 1]) - (P[:, 2, 0] - P[:, 0, 0]) * (P[:, 1, 1] - P[:, 0, 1])
        # Only triangles facing an outside viewer on this side (sign) can be
        # seen, so only they cover a face; back faces are culled in game.
        keep = (np.abs(area) > 1e-9) & (length > 1e-12) & ((normal[:, axis] * sign > 0) | (sign == 0))
        tris, normal, length, P, area = tris[keep], normal[keep], length[keep], P[keep], area[keep]
        u0 = np.clip(np.ceil(P[:, :, 0].min(1) - 1e-9), 0, None).astype(np.int64)
        u1 = np.clip(np.floor(P[:, :, 0].max(1) + 1e-9), None, self.nu - 1).astype(np.int64)
        v0 = np.clip(np.ceil(P[:, :, 1].min(1) - 1e-9), 0, None).astype(np.int64)
        v1 = np.clip(np.floor(P[:, :, 1].max(1) + 1e-9), None, self.nv - 1).astype(np.int64)
        wu, wv = u1 - u0 + 1, v1 - v0 + 1
        ok = (wu > 0) & (wv > 0)
        counts = np.where(ok, wu * wv, 0)
        tri = np.repeat(np.arange(len(tris)), counts)
        if not len(tri):
            return
        start = np.repeat(np.cumsum(counts) - counts, counts)
        local = np.arange(len(tri)) - start
        iu = u0[tri] + local % wu[tri]
        iv = v0[tri] + local // wu[tri]
        p = P[tri]
        # Barycentric weights of the sample in the projected triangle.
        w1 = ((iu - p[:, 0, 0]) * (p[:, 2, 1] - p[:, 0, 1]) - (p[:, 2, 0] - p[:, 0, 0]) * (iv - p[:, 0, 1])) / area[tri]
        w2 = ((p[:, 1, 0] - p[:, 0, 0]) * (iv - p[:, 0, 1]) - (iu - p[:, 0, 0]) * (p[:, 1, 1] - p[:, 0, 1])) / area[tri]
        w0 = 1 - w1 - w2
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        tri, iu, iv, w0, w1, w2 = tri[inside], iu[inside], iv[inside], w0[inside], w1[inside], w2[inside]
        z = tris[tri][:, :, axis]
        depth = w0 * z[:, 0] + w1 * z[:, 1] + w2 * z[:, 2]
        sample = iu * self.nv + iv
        order = np.lexsort((depth, sample))
        self.sample = sample[order]
        self.depth = depth[order]
        self.normal = (normal[tri] / length[tri, None])[order]
        # Depth lies within (-8, 56) for every building (heights <= 25 plus
        # supports below BaseZ), so sample * 64 + depth + 8 keeps samples apart.
        if len(self.depth) and (self.depth.min() < -8 or self.depth.max() > 56):
            raise ValueError('Geometry depth outside the measured range')
        self.keys = self.sample * 64.0 + self.depth + 8

    def sample_ids(self, cells):
        """(cells x SAMPLES^2) sample ids of the face of each cell."""
        i = np.arange(SAMPLES)
        iu = cells[:, self.b, None, None] * SAMPLES + i[None, :, None]
        iv = cells[:, self.c, None, None] * SAMPLES + i[None, None, :]
        return (iu * self.nv + iv).reshape(len(cells), -1)

    def nearest(self, ids, start, sign):
        """Nearest crossing met by a ray from depth `start` moving against
        `sign`: the deepest crossing <= start (sign > 0) or the shallowest
        >= start (sign < 0). Returns (found, depth, unit normal)."""
        found = np.zeros(ids.shape, bool)
        depth = np.zeros(ids.shape)
        normal = np.zeros(ids.shape + (3,))
        if not len(self.keys):
            return found, depth, normal
        q = ids * 64.0 + start[:, None] + 8
        if sign > 0:
            j = np.searchsorted(self.keys, q, side='right') - 1
        else:
            j = np.searchsorted(self.keys, q, side='left')
        valid = (j >= 0) & (j < len(self.keys))
        jj = np.clip(j, 0, len(self.keys) - 1)
        found = valid & (self.sample[jj] == ids)
        return found, np.where(found, self.depth[jj], 0), np.where(found[..., None], self.normal[jj], 0)

    def any_between(self, ids, lo, hi):
        """Whether any crossing of the sample lies in [lo, hi]."""
        if not len(self.keys):
            return np.zeros(ids.shape, bool)
        a = np.searchsorted(self.keys, ids * 64.0 + lo[:, None] + 8, side='left')
        b = np.searchsorted(self.keys, ids * 64.0 + hi[:, None] + 8, side='right')
        return b > a


def covering(hits, cells, axis, sign):
    """The covering surface of each cell's face: the share of samples covered,
    the largest angle (deg) between a covering normal and the outward axis,
    the largest angle to the covering mean normal, the covering depth spread,
    and whether the superseded depth-band rule accepted the face."""
    plane = cells[:, axis] + (1 if sign > 0 else 0)
    ids = hits.sample_ids(cells)
    found, depth, normal = hits.nearest(ids, plane + sign * FRONT, sign)
    behind = (plane[:, None] - depth) * sign
    facing = normal[..., axis] * sign
    old = (found & (behind <= OLD_DEPTH) & (behind >= -FRONT) & (facing > OLD_FACING)).sum(1) >= COVER * SAMPLES ** 2
    within = found & (behind <= WALL_DEPTH) & (behind >= -FRONT)
    count = within.sum(1)
    axis_angle = np.degrees(np.arccos(np.clip(np.where(within, facing, 1), -1, 1))).max(1)
    mean = (normal * within[..., None]).sum(1)
    mean /= np.maximum(np.linalg.norm(mean, axis=1, keepdims=True), 1e-12)
    spread_angle = np.degrees(np.arccos(np.clip(np.where(within, (normal * mean[:, None]).sum(2), 1), -1, 1))).max(1)
    lo = np.where(within, behind, np.inf).min(1)
    hi = np.where(within, behind, -np.inf).max(1)
    depth_spread = np.where(count > 0, hi - lo, 0)
    # Curved or faceted: the off-axis covering normals take at least CURVE_NORMALS
    # distinct directions (rounded to whole degrees about the face axis), as a
    # tessellated cylinder, dome or rounded edge does; one off-axis direction is
    # a single slope, bevel or back face.
    off = within & (np.degrees(np.arccos(np.clip(facing, -1, 1))) > AXIS_ANGLE)
    b, c2 = [a for a in range(3) if a != axis]
    keyed = np.round(np.degrees(np.arctan2(normal[..., b], normal[..., c2]))) * 1000 + np.round(np.degrees(np.arccos(np.clip(facing, -1, 1))))
    keyed = np.where(off, keyed, np.nan)
    srt = np.sort(keyed, axis=1)
    distinct = (np.isfinite(srt) & np.concatenate([np.isfinite(srt[:, :1]), srt[:, 1:] != srt[:, :-1]], axis=1)).sum(1)
    # Largest single plane: most samples whose depths lie within PLANE_SPREAD.
    d = np.where(within, behind, np.nan)
    band = (d[:, None, :] >= d[:, :, None] - 1e-9) & (d[:, None, :] <= d[:, :, None] + PLANE_SPREAD + 1e-9)
    plane_share = band.sum(2).max(1) / SAMPLES ** 2
    return {'ids': ids, 'plane': plane, 'share': count / SAMPLES ** 2, 'axisAngle': axis_angle,
            'normalSpread': spread_angle, 'depthSpread': depth_spread, 'planeShare': plane_share, 'old': old,
            'curve': distinct >= CURVE_NORMALS}


def face_test(solid, opaque, cells, axis, sign):
    """covering() over every static surface (glass included), with planeShare the
    larger of that and the opaque surfaces' alone: a flat wall with windows set in
    or proud of it is one wall."""
    c = covering(solid, cells, axis, sign)
    c['planeShare'] = np.maximum(c['planeShare'], covering(opaque, cells, axis, sign)['planeShare'])
    return c


def planar(c):
    return (c['planeShare'] >= COVER) & (c['axisAngle'] <= AXIS_ANGLE) & (c['normalSpread'] <= NORMAL_SPREAD)


def measure(path, size, base_z):
    """Flat faces of a model over a blueprint Size, the counts behind them, and
    the faces the superseded depth-band rule accepted that sit on a curved or
    faceted surface (a covering normal off the axis or off the mean)."""
    kinds = triangles(path, base_z)
    size = tuple(size)
    cells = np.array([(x, y, z) for z in range(size[2]) for y in range(size[1]) for x in range(size[0])], dtype=np.int64)
    flat, curved, animated_faces, multi, old_count, set_back = [], [], 0, 0, 0, 0
    roof = {'blocked': [], 'covered': [], 'animated': []}
    solid_tris = np.concatenate([kinds['opaque'], kinds['glass']])
    solid = [AxisHits(np.concatenate([solid_tris, kinds['lamp']]), a, size, 0) for a in range(3)]   # anything blocks a roof cell
    inner = slice(SAMPLES // 4, SAMPLES - SAMPLES // 4)   # samples 0.31..0.69: railings and trim within 0.31 of a cell edge do not block
    hits = {'solid': {(a, s): AxisHits(solid_tris, a, size, s) for a in range(3) for s in (-1, 1)},
            'opaque': {(a, s): AxisHits(kinds['opaque'], a, size, s) for a in range(3) for s in (-1, 1)},
            'animated': [AxisHits(kinds['animated'], a, size, 0) for a in range(3)]}
    face = lambda cell, name: [int(cell[0]), int(cell[1]), int(cell[2]), name]
    for name, axis, sign in DIRECTIONS:
        c = face_test(hits['solid'][(axis, sign)], hits['opaque'][(axis, sign)], cells, axis, sign)
        ids, plane = c['ids'], c['plane']
        lo, hi = (plane - FRONT, plane + ANIMATED_REACH) if sign > 0 else (plane - ANIMATED_REACH, plane + FRONT)
        moving = hits['animated'][axis].any_between(ids, lo, hi).any(1)
        good = planar(c)
        bent = (c['axisAngle'] > AXIS_ANGLE) | (c['normalSpread'] > NORMAL_SPREAD)
        old_count += int(c['old'].sum())
        multi += int((c['old'] & ~bent & ~good).sum())
        animated_faces += int((good & moving).sum())
        for cell, curve in zip(cells[c['old'] & bent], c['curve'][c['old'] & bent]):
            curved.append(face(cell, name) + ['curve' if curve else 'slope'])
        for cell in cells[good & ~moving]:
            flat.append(face(cell, name))
        if name == 'Top' and (good & ~moving).any():
            kept = cells[good & ~moving]
            over = kept + np.array([0, 0, 1])
            top = kept[:, 2] + 1
            vertical = solid[2].sample_ids(kept).reshape(-1, SAMPLES, SAMPLES)[:, inner, inner].reshape(len(kept), -1)
            blocked = solid[2].any_between(vertical, top + ROOF_LIP, top + 1.).any(1)
            covered = solid[2].any_between(vertical, top + ROOF_LIP, np.full(len(top), 55.)).any(1)   # 55: top of the key range
            inside = over[:, 2] < size[2]          # horizontal rays exist inside the Size only
            for a in ((0, 1) if inside.any() else ()):
                ids_a = solid[a].sample_ids(over[inside]).reshape(-1, SAMPLES, SAMPLES)[:, inner, inner].reshape(int(inside.sum()), -1)
                lo, hi = over[inside, a] + 2.5 / SAMPLES, over[inside, a] + 1 - 2.5 / SAMPLES   # the band the vertical samples cover
                blocked[inside] |= solid[a].any_between(ids_a, lo, hi).any(1)
            roof['blocked'] += [face(cell, name)[:3] for cell in kept[blocked]]
            roof['covered'] += [face(cell, name)[:3] for cell in kept[covered]]
        if name == 'Top':
            roof['animated'] += [face(cell, name)[:3] for cell in cells[good & moving]]
        set_back += int((good & ~moving & ~c['old']).sum())
    order = {n: i for i, (n, _, _) in enumerate(DIRECTIONS)}
    key = lambda f: (f[2], f[1], f[0], order[f[3]])
    flat.sort(key=key)
    curved.sort(key=key)
    counts = {k: int(len(v)) for k, v in kinds.items()}
    return flat, {'triangles': counts, 'flatButAnimated': animated_faces,
                  'oldRuleFaces': old_count, 'oldRuleCurveExcluded': sum(f[4] == 'curve' for f in curved),
                  'oldRuleSlopeExcluded': sum(f[4] == 'slope' for f in curved), 'oldRuleMultiPlaneExcluded': multi,
                  'newSetBackFaces': set_back}, curved, roof


def buildings(data, only):
    """(template, blueprint path, model resource, owning export file) of every
    Deep Frontier building with its own finished model."""
    rows = []
    for path in sorted((data / 'Buildings').rglob('*.IronTeeth.blueprint.json')):
        blueprint = json.loads(path.read_text(encoding='utf-8-sig'))
        if 'PlaceableBlockObjectSpec' not in blueprint:
            continue
        ident = path.name[:-len('.IronTeeth.blueprint.json')]
        if only and ident not in only:
            continue
        finished, _ = models_of(blueprint)
        if finished is None or not (data / (finished + '.timbermesh')).is_file():
            continue
        if ident not in OWNERS:
            raise ValueError(f'{ident}: no owning export in validate_triangle_budget.OWNERS')
        root = OWNERS[ident][2] or data
        export = root / (finished + '.timbermesh')
        if not export.is_file():
            raise ValueError(f'{ident}: owning export {export} is missing')
        spec = blueprint['BlockObjectSpec']
        rows.append((ident, blueprint, finished, export, [spec['Size']['X'], spec['Size']['Y'], spec['Size']['Z']], spec['BaseZ']))
    if only and {r[0] for r in rows} != set(only):
        raise ValueError('Unknown or model-less templates: ' + ', '.join(sorted(set(only) - {r[0] for r in rows})))
    return rows


def relative(path):
    path = Path(path).resolve()
    for base in (ROOT,):
        if path.is_relative_to(base):
            return path.relative_to(base).as_posix()
    # A generated Data root outside the repository (scratch mirror): name the
    # file by its path under src/DeepFrontier/Data, which is where it lives in
    # every checkout.
    parts = path.as_posix().split('/src/DeepFrontier/Data/')
    if len(parts) != 2:
        raise ValueError(f'{path} is neither in the repository nor under a src/DeepFrontier/Data root')
    return 'src/DeepFrontier/Data/' + parts[1]


def record(ident, finished, export, size, base_z):
    faces, stats, curved, roof = measure(export, size, base_z)
    return {'template': ident, 'model': finished, 'export': relative(export), 'exportSha256': sha256(export),
            'size': size, 'baseZ': base_z,
            'coordinateSystem': 'Native grid XYZ, Z up, blueprint block indices; cell (x,y,z) covers [x,x+1)x[y,y+1)x[z,z+1)',
            'rule': RULE, 'excluded': 'Water, WalkwayRail nodes, animated nodes; native props are not in the model; glass counts as a surface',
            'stats': stats, 'curvedFaces': curved, 'roof': roof, 'faces': faces}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True, help='generated Data root whose blueprints give Size/BaseZ/model')
    parser.add_argument('--only', help='comma-separated templates')
    parser.add_argument('--out', type=Path, default=OUT)
    cli = parser.parse_args()
    only = set(cli.only.split(',')) if cli.only else None
    cli.out.mkdir(parents=True, exist_ok=True)
    for ident, _, finished, export, size, base_z in buildings(cli.data, only):
        fresh = record(ident, finished, export, size, base_z)
        target = cli.out / f'{ident}.json'
        target.write_text(json.dumps(fresh, separators=(',', ':')).replace('],[', '],\n[') + '\n', encoding='utf-8')
        print('CONNECTION FACES', ident, len(fresh['faces']), fresh['stats'], flush=True)


if __name__ == '__main__':
    main()
