"""Prove a static-joined Timbermesh export draws what the previous export drew.

For each (before, after) pair of .timbermesh files: every triangle of a node
that is static (no node animation on itself or an ancestor) is taken to model
space through the node transform chain, and per material the multisets of
triangles (position, normal and uv0 per corner, cyclic order kept so winding
counts) must match within tolerance. Zero-area triangles are skipped.
Animated nodes must keep their names, parents' names, transforms, tracks
and materials, and the same triangles in node space (vertex order and count
may differ: the exporter de-duplicates vertices by MikkTSpace tangents,
which Blender recomputes with float noise on every export). Reports renderer,
slot and triangle counts before and after.

Run: python compare_merged_exports.py BEFORE AFTER [BEFORE AFTER ...]
"""
import json
import sys
import zlib
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2  # noqa: E402

POSITION, NORMAL, UV = 1e-4, 2e-3, 1e-4


def load(path):
    model = model_pb2.Model()
    model.ParseFromString(zlib.decompress(Path(path).read_bytes()))
    return model


def matrix(node):
    x, y, z, w = node.rotation.x, node.rotation.y, node.rotation.z, node.rotation.w
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4)
    m[:3, :3] = r @ np.diag([node.scale.x, node.scale.y, node.scale.z])
    m[:3, 3] = [node.position.x, node.position.y, node.position.z]
    return m


def world(model, index):
    m = np.eye(4)
    while index >= 0:
        m = matrix(model.nodes[index]) @ m
        index = model.nodes[index].parent
    return m


def animated(model, index):
    while index >= 0:
        if model.nodes[index].nodeAnimations or model.nodes[index].vertexAnimations:
            return True
        index = model.nodes[index].parent
    return False


def prop(node, name, width):
    data = next(p.data for p in node.vertexProperties if p.name == name)
    return np.frombuffer(data, dtype='<f4').reshape(-1, width).astype(np.float64)


def node_triangles(node, m, result):
    """Add node's triangles, taken through matrix m, to result per material."""
    pos = prop(node, 'position', 3) @ m[:3, :3].T + m[:3, 3]
    normal_matrix = np.linalg.inv(m[:3, :3]).T
    nrm = prop(node, 'normal', 3) @ normal_matrix.T
    length = np.linalg.norm(nrm, axis=1, keepdims=True)
    nrm = np.divide(nrm, length, out=np.zeros_like(nrm), where=length > 0)
    uv = prop(node, 'uv0', 2)
    key = np.hstack([np.round(pos / POSITION), np.round(nrm / NORMAL), np.round(uv / UV)]).astype(np.int64)
    for mesh in node.meshes:
        corners = np.asarray(mesh.indices, dtype=np.int64).reshape(-1, 3)
        counter = result.setdefault(mesh.material, Counter())
        for a, b, c in corners:
            # Zero-area triangles are never rasterized; Blender gives
            # their corners an arbitrary normal, so they are not compared.
            if (key[a, :3] == key[b, :3]).all() or (key[b, :3] == key[c, :3]).all() or (key[a, :3] == key[c, :3]).all():
                continue
            tri = [tuple(key[a]), tuple(key[b]), tuple(key[c])]
            start = tri.index(min(tri))
            counter[tuple(tri[start:] + tri[:start])] += 1
    return result


def triangles(model):
    """{material: Counter of canonical corner tuples} for static nodes, model space."""
    result = {}
    for i, node in enumerate(model.nodes):
        if node.vertexCount and not animated(model, i):
            node_triangles(node, world(model, i), result)
    return result


def animated_nodes(model):
    return {n.name: (i, n) for i, n in enumerate(model.nodes) if animated(model, i)}


def animated_differences(before, after):
    """Animated nodes must be the same node: parent, transform, tracks and,
    in node space, the same triangles (the exporter's vertex de-duplication
    compares MikkTSpace tangents, which Blender recomputes with float noise,
    so vertex order and count may differ)."""
    a, b = animated_nodes(before), animated_nodes(after)
    if set(a) != set(b):
        return [f'animated node set differs: {sorted(set(a) ^ set(b))}']
    problems = []
    for name in sorted(a):
        (_, x), (_, y) = a[name], b[name]
        pa = before.nodes[x.parent].name if x.parent >= 0 else None
        pb = after.nodes[y.parent].name if y.parent >= 0 else None
        same = (pa == pb and x.position == y.position and x.rotation == y.rotation and x.scale == y.scale
                and list(x.nodeAnimations) == list(y.nodeAnimations)
                and [m.material for m in x.meshes] == [m.material for m in y.meshes])
        if same and x.vertexCount:
            ta, tb = node_triangles(x, np.eye(4), {}), node_triangles(y, np.eye(4), {})
            same = all(unmatched(ta.get(k, Counter()), tb.get(k, Counter())) == (0, 0) for k in set(ta) | set(tb))
        if not same:
            problems.append(f'animated node {name} changed')
    return problems


def unmatched(ta, tb):
    """Triangles left after exact matching, then matched again allowing one
    rounding step per component (values that straddle a rounding boundary)."""
    missing, extra = list((ta - tb).elements()), list((tb - ta).elements())
    left = []
    pool = [np.array(t) for t in extra]
    for t in missing:
        t = np.array(t)
        hit = next((k for k, e in enumerate(pool) if np.abs(e - t).max() <= 1), None)
        if hit is None:
            left.append(t)
        else:
            pool.pop(hit)
    return len(left), len(pool)


def counts(model):
    nodes = [n for n in model.nodes if n.vertexCount]
    return {'renderers': len(nodes), 'slots': sum(len(n.meshes) for n in nodes),
            'triangles': sum(len(m.indices) for n in nodes for m in n.meshes) // 3, 'nodes': len(model.nodes)}


def compare(before_path, after_path):
    before, after = load(before_path), load(after_path)
    failures = []
    a, b = triangles(before), triangles(after)
    for material in sorted(set(a) | set(b)):
        missing, extra = unmatched(a.get(material, Counter()), b.get(material, Counter()))
        if missing or extra:
            failures.append(f'{material}: {missing} triangles missing, {extra} new')
    failures.extend(animated_differences(before, after))
    return {'before': str(before_path), 'after': str(after_path), 'beforeCounts': counts(before),
            'afterCounts': counts(after), 'failures': failures}


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or len(args) % 2:
        raise SystemExit('usage: compare_merged_exports.py BEFORE AFTER [BEFORE AFTER ...]')
    reports = [compare(args[i], args[i + 1]) for i in range(0, len(args), 2)]
    print(json.dumps(reports, indent=1))
    if any(r['failures'] for r in reports):
        raise SystemExit('Merged export geometry differs from the previous export')
