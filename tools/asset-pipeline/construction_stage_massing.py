"""Massing of a Deep Frontier construction site (2026-11-02), no Blender needed.

Shared by build_construction_stages.py (which builds the stage from it) and
tools/asset-pipeline/validate_construction_exports.py (which recomputes it and compares it
with the generated manifest). Inputs, all explicit:

  - the building blueprint: BlockObjectSpec Size, BaseZ and Blocks give the
    footprint (columns with an occupied block), the grounded cells (the lowest
    block of the column stands on Ground, GroundOrStackable or Stackable) and
    the main body height (the top of the highest layer holding
    mainBodyShare of the widest layer's cells, as status_icon_content.mjs);
  - the finished model (the blueprint's #Finished Timbermesh in the Data
    tree): the vertical extent of its triangles over each cell, clamped to the
    column's occupied layers, so a deck slab, a bridge span or a pile in the
    water keeps its real height;
  - the BuildingCost: a metal frame when it costs one of metalFrameCostGoods
    (vanilla Centrifuge, BotPartFactory, BotAssembler and MetalPlatform cost
    MetalBlock and have BaseMetal frames), otherwise timber.

The stage is cut flat at ceil(stageHeightFraction x main body) layers above
the lowest layer: the frame stands to that height over the building's plan
(lower parts to their own height). Columns are grouped into box bays of equal
extent. Coordinates: x = block X, y = block Y, heights in model units (layer
BaseZ at 0). Nothing is fitted or repaired: a building without finished
geometry or grounded cells fails.
"""
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2  # noqa: E402

CONFIG = json.loads((ROOT / 'tools/construction_stages.json').read_text(encoding='utf-8'))
VANILLA = ROOT / 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources'


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def blocks_sha(spec):
    """sha256 of the block contract the stage is built on; construction_stage_content.mjs
    computes the same string (JSON.stringify of the same nested arrays)."""
    size = spec['Size']
    payload = [[size['X'], size['Y'], size['Z']], spec.get('BaseZ', 0),
               [[b['Occupations'], b['MatterBelow']] for b in spec['Blocks']]]
    return hashlib.sha256(json.dumps(payload, separators=(',', ':')).encode('utf-8')).hexdigest()


def classify(ident):
    if ident in CONFIG['authored']:
        return 'authored'
    if any(ident.startswith(prefix) for prefix in CONFIG['previewOnly']):
        return 'previewOnly'
    return 'generated'


def buildings(data_root):
    """Every Deep Frontier building template: TemplateCollection.Buildings.IronTeeth
    entries with a BuildingModelSpec whose finished model is in this Data tree."""
    data_root = Path(data_root)
    collection = read_json(data_root / 'TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json')
    paths = collection['TemplateCollectionSpec']['Blueprints#append']
    found = []
    for path in paths:
        file = data_root / f'{path}.json'
        blueprint = read_json(file)
        if 'BuildingModelSpec' not in blueprint:
            continue
        ident = Path(path).name.replace('.IronTeeth.blueprint', '')
        finished = blueprint['Children'][blueprint['BuildingModelSpec']['FinishedModelName']]
        model = finished.get('TimbermeshSpec', {}).get('Model')
        if model is None:
            if classify(ident) != 'previewOnly':
                raise ValueError(f'{ident}: the finished model has no TimbermeshSpec')
        elif not (data_root / f'{model}.timbermesh').is_file():
            continue  # a vanilla model: shipped content with its own vanilla stage
        found.append({'id': ident, 'file': file, 'blueprint': blueprint, 'finished': model, 'kind': classify(ident)})
    return found


def stage_resource(finished):
    if not finished.endswith('.IronTeeth.Model'):
        raise ValueError(f'Unexpected finished model name {finished}')
    return finished[:-len('.Model')] + '.ConstructionStage0.Model'


def _vectors(prop):
    return list(struct.iter_unpack('<' + 'f' * prop.scalarTypeDimension, prop.data))


def _rotate(q, v):
    x, y, z, w = q.x, q.y, q.z, q.w
    ix = w * v[0] + y * v[2] - z * v[1]
    iy = w * v[1] + z * v[0] - x * v[2]
    iz = w * v[2] + x * v[1] - y * v[0]
    iw = -x * v[0] - y * v[1] - z * v[2]
    return (ix * w + iw * -x + iy * -z - iz * -y, iy * w + iw * -y + iz * -x - ix * -z,
            iz * w + iw * -z + ix * -y - iy * -x)


def triangles(path):
    """World-space (Unity) triangles of a Timbermesh at rest, without the nodes
    (and their children) named by excludedFinishedNodePrefixes: the adaptive
    support templates parked underground in the finished model."""
    model = model_pb2.Model()
    model.ParseFromString(zlib.decompress(Path(path).read_bytes()))
    nodes = model.nodes
    excluded = set()
    for i, node in enumerate(nodes):
        if any(node.name.startswith(p) for p in CONFIG['excludedFinishedNodePrefixes']) or node.parent in excluded:
            excluded.add(i)
    result = []
    for i, node in enumerate(nodes):
        if i in excluded or not node.meshes:
            continue
        positions = {p.name: p for p in node.vertexProperties}['position']
        local = _vectors(positions)
        world = []
        for v in local:
            j = i
            while j != -1:
                n = nodes[j]
                v = (v[0] * n.scale.x, v[1] * n.scale.y, v[2] * n.scale.z)
                v = _rotate(n.rotation, v)
                v = (v[0] + n.position.x, v[1] + n.position.y, v[2] + n.position.z)
                j = n.parent
            world.append(v)
        for mesh in node.meshes:
            idx = mesh.indices
            for k in range(0, len(idx), 3):
                result.append((world[idx[k]], world[idx[k + 1]], world[idx[k + 2]]))
    return result


def finished_extents(path, width, depth):
    """{(x, y): [low, high]} height range of the finished triangles whose
    footprint (x/z bounds) overlaps cell (x, y)."""
    eps = 1e-4
    extents = {}
    for tri in triangles(path):
        xs = [p[0] for p in tri]
        zs = [p[2] for p in tri]
        ys = [p[1] for p in tri]
        x0, x1 = max(0, math.floor(min(xs) + eps)), min(width - 1, math.floor(max(xs) - eps))
        y0, y1 = max(0, math.floor(min(zs) + eps)), min(depth - 1, math.floor(max(zs) - eps))
        if max(xs) - min(xs) < 2 * eps:   # a face in a cell-boundary plane: both cells
            x0, x1 = max(0, math.floor(min(xs) - eps)), min(width - 1, math.floor(max(xs) + eps))
        if max(zs) - min(zs) < 2 * eps:
            y0, y1 = max(0, math.floor(min(zs) - eps)), min(depth - 1, math.floor(max(zs) + eps))
        lo, hi = min(ys), max(ys)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                e = extents.setdefault((x, y), [lo, hi])
                e[0] = min(e[0], lo)
                e[1] = max(e[1], hi)
    return extents


def snap(value, step, mode):
    q = value / step
    q = math.floor(q + 1e-6) if mode == 'down' else math.ceil(q - 1e-6) if mode == 'up' else math.floor(q + .5)
    return round(q * step, 4)


def boxes_of(columns):
    """Greedy maximal rectangles of columns with equal (low, top), scanned by y then x."""
    left = dict(columns)
    boxes = []
    while left:
        x0, y0 = min(left, key=lambda c: (c[1], c[0]))
        key = left[(x0, y0)]
        x1 = x0
        while left.get((x1 + 1, y0)) == key:
            x1 += 1
        y1 = y0
        while all(left.get((x, y1 + 1)) == key for x in range(x0, x1 + 1)):
            y1 += 1
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                del left[(x, y)]
        boxes.append([x0, y0, x1 + 1, y1 + 1, key[0], key[1]])
    return boxes


def choose_base(grounded, width, depth):
    """The largest vanilla ConstructionBase lying on grounded cells of one height."""
    heights = sorted(set(grounded.values()))
    best = None
    cx = sum(c[0] + .5 for c in grounded) / len(grounded)
    cy = sum(c[1] + .5 for c in grounded) / len(grounded)
    candidates = [(name, False) for name in CONFIG['vanillaBases']['plain']]
    candidates += [(name, True) for name in CONFIG['vanillaBases']['withoutCorners']]
    for name, without in candidates:
        bw, bd = (int(v) for v in name.split('x'))
        for h in heights:
            for ox in range(width - bw + 1):
                for oy in range(depth - bd + 1):
                    cells = [(ox + i, oy + j) for i in range(bw) for j in range(bd)
                             if not (without and i in (0, bw - 1) and j in (0, bd - 1))]
                    if all(grounded.get(c) == h for c in cells):
                        dist = math.hypot(ox + bw / 2 - cx, oy + bd / 2 - cy)
                        score = (len(cells), -round(dist, 4), -h)
                        blueprint = f'ConstructionBase{name}' + ('WithoutCorners' if without else '')
                        if best is None or score > best[0]:
                            best = (score, blueprint, [ox, oy, h])
    if best is None:
        raise ValueError('No vanilla construction base fits the grounded cells')
    blueprint = best[1]
    path = f'ConstructionBases/{blueprint}/{blueprint}.blueprint'
    if not (VANILLA / f'{path}.json').is_file():
        raise ValueError(f'Vanilla construction base {path} does not exist')
    return {'name': blueprint, 'blueprint': path, 'offset': best[2]}


def massing(entry, data_root):
    """The construction site of one generated building (see the module docstring)."""
    ident, blueprint = entry['id'], entry['blueprint']
    spec = blueprint['BlockObjectSpec']
    width, depth, height = spec['Size']['X'], spec['Size']['Y'], spec['Size']['Z']
    base_z = spec.get('BaseZ', 0)
    blocks = spec['Blocks']
    if len(blocks) != width * depth * height:
        raise ValueError(f'{ident}: BlockObjectSpec Size/Blocks mismatch')
    layers, column_blocks = {}, {}
    for i, block in enumerate(blocks):
        if block['Occupations'] == 'None':
            continue
        z, rest = divmod(i, width * depth)
        y, x = divmod(rest, width)
        layers[z] = layers.get(z, 0) + 1
        column_blocks.setdefault((x, y), []).append((z, block))
    if not layers:
        raise ValueError(f'{ident}: no occupied block')
    widest = max(layers.values())
    main_top = max(z for z, n in layers.items() if n >= CONFIG['mainBodyShare'] * widest) + 1
    lowest = min(layers)
    cut = lowest + math.ceil(CONFIG['stageHeightFraction'] * (main_top - lowest) - 1e-9) - base_z
    extents = finished_extents(data_root / f"{entry['finished']}.timbermesh", width, depth)
    frame = CONFIG['frame']
    columns, grounded = {}, {}
    for (x, y), stack in sorted(column_blocks.items()):
        stack.sort(key=lambda s: s[0])
        block_low, block_high = stack[0][0] - base_z, stack[-1][0] + 1 - base_z
        is_grounded = stack[0][1]['MatterBelow'] in CONFIG['groundedMatter']
        if is_grounded:
            grounded[(x, y)] = block_low
        if (x, y) not in extents:
            continue
        low_g, high_g = extents[(x, y)]
        high = min(high_g, block_high)
        if is_grounded:
            low = block_low
            top = min(snap(high, 1, 'round'), cut)
        else:
            # A slab (deck, span, pile cap) on the slabSnap grid, at least
            # minimumSlab deep inside its own layers, so a sill and a top
            # girt fit one above the other.
            step = frame['slabSnap']
            low = snap(max(low_g, block_low), step, 'down')
            top = min(snap(high, step, 'round'), cut)
            if top - low < frame['minimumSlab'] - 1e-9:
                low = max(block_low, top - frame['minimumSlab'])
            if top - low < frame['minimumSlab'] - 1e-9:
                top = min(low + frame['minimumSlab'], block_high, cut)
        if top - low >= frame['minimumHeight'] - 1e-9:
            columns[(x, y)] = (low, top)
    if not columns:
        raise ValueError(f'{ident}: no finished geometry under the stage cut')
    if not grounded:
        raise ValueError(f'{ident}: no grounded cell for the construction base')
    cost = [c['Id'] for c in blueprint.get('BuildingSpec', {}).get('BuildingCost', [])]
    material = 'metal' if set(cost) & set(CONFIG['metalFrameCostGoods']) else 'wood'
    boxes = boxes_of(columns)
    colliders = [{'Center': {'X': (b[0] + b[2]) / 2, 'Y': round((b[4] + b[5]) / 2, 4), 'Z': (b[1] + b[3]) / 2},
                  'Size': {'X': b[2] - b[0], 'Y': round(b[5] - b[4], 4), 'Z': b[3] - b[1]}} for b in boxes]
    return {
        'id': ident,
        'stage': stage_resource(entry['finished']),
        'finished': entry['finished'],
        'blocksSha': blocks_sha(spec),
        'size': [width, depth, height],
        'baseZ': base_z,
        'cut': cut,
        'frame': material,
        'columns': [[x, y, low, top] for (x, y), (low, top) in sorted(columns.items())],
        'boxes': boxes,
        'dirt': sorted([x, y, h] for (x, y), h in grounded.items()),
        'base': choose_base(grounded, width, depth),
        'colliders': colliders,
    }


GEOMETRY_KEYS = ('stage', 'blocksSha', 'size', 'baseZ', 'cut', 'frame', 'columns', 'boxes', 'dirt', 'base', 'colliders')
