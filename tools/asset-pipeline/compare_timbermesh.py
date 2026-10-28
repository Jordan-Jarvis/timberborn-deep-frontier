"""Compare two .timbermesh files by content, not bytes.

python tools/asset-pipeline/compare_timbermesh.py A.timbermesh B.timbermesh

The official exporter's output is not byte-stable (two exports of one unchanged
scene differ), so this decodes both files (zlib-compressed Model protobuf, the
official schema in timbermesh-plugin/model_pb2.py) and compares every node by
name: its fields, meshes (material, indices) and vertex property data. Prints
the first differences and exits 1 if the models differ. Vertex data compare as
float32 within 1e-4 (normals and tangents carry float noise between exports).
"""
import base64, struct, sys, zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'timbermesh-plugin' / 'timbermesh_blender_plugin'))
import model_pb2
from google.protobuf.json_format import MessageToDict


def load(path):
    model = model_pb2.Model()
    model.ParseFromString(zlib.decompress(Path(path).read_bytes()))
    return MessageToDict(model, preserving_proto_field_name=True)


def by_name(model):
    nodes = model.get('nodes', [])
    names = [n.get('name', '') for n in nodes]
    if len(set(names)) != len(names):
        # Keep duplicates distinct by their order of appearance among equal names.
        seen = {}
        keyed = {}
        for n in nodes:
            k = n.get('name', ''); seen[k] = seen.get(k, 0) + 1
            keyed[f'{k}#{seen[k]}'] = n
        return keyed
    return {n.get('name', ''): n for n in nodes}


def diff(a, b, path, out):
    if len(out) > 20:
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f'{path}.{k}: only in {"B" if k not in a else "A"}')
            else:
                diff(a[k], b[k], f'{path}.{k}', out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f'{path}: length {len(a)} vs {len(b)}')
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f'{path}[{i}]', out)
    elif path.endswith('.data') and isinstance(a, str) and isinstance(b, str):
        # Vertex property payloads: little-endian float32 arrays (base64 in the dict form).
        fa, fb = base64.b64decode(a), base64.b64decode(b)
        if len(fa) != len(fb) or len(fa) % 4:
            out.append(f'{path}: {len(fa)} vs {len(fb)} bytes')
            return
        xa, xb = struct.unpack(f'<{len(fa) // 4}f', fa), struct.unpack(f'<{len(fb) // 4}f', fb)
        worst = max((abs(x - y) for x, y in zip(xa, xb)), default=0.0)
        if worst > 1e-4:
            out.append(f'{path}: {len(xa)} floats differ, max {worst:.6g}')
    elif isinstance(a, float) or isinstance(b, float):
        if abs(float(a) - float(b)) > 1e-5:
            out.append(f'{path}: {a} vs {b}')
    elif a != b:
        out.append(f'{path}: {str(a)[:60]} vs {str(b)[:60]}')


a, b = load(sys.argv[1]), load(sys.argv[2])
top = {k: v for k, v in a.items() if k != 'nodes'}, {k: v for k, v in b.items() if k != 'nodes'}
out = []
diff(top[0], top[1], 'model', out)
na, nb = by_name(a), by_name(b)
diff(na, nb, 'nodes', out)
print(f'nodes A={len(na)} B={len(nb)}')
for line in out[:20]:
    print('  ' + line)
print('IDENTICAL CONTENT' if not out else f'DIFFERENT ({len(out)}+ differences)')
sys.exit(1 if out else 0)
