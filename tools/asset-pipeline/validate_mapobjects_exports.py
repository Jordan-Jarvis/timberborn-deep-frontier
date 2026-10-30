"""Validate the map-object and pile-good models against tools/map_objects.json.

For every map object: the active Data mesh exists and is the official export
(byte-identical to outputs/mapobjects-integration/Data); its triangles stay
under the contract ceiling; it stays inside its footprint and height band;
every material it names is registered for the editor (vanilla
MaterialCollection.Common or Deep Frontier's DeepFrontierMapResources); each
blueprint that shows it binds the resource with the contract collider; the
spring's glow node exists and is the node RadioactiveSpringVisual tints.

For every pile good: the asset-bundle mesh exists and is the export, holds one
untransformed node with the native goods atlas, hangs one level below its
origin within the item length, and stays under its ceiling; its
GoodVisualization blueprint names the meshes; the good uses that
visualization; and every Iron Teeth pile patch appends it. Static evidence;
how the models look and load is checked in game.
"""
import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2  # noqa: E402

CONTRACT = json.loads((ROOT / 'tools/map_objects.json').read_text(encoding='utf-8'))
SOURCE = ROOT / 'src/DeepFrontier'
DATA = SOURCE / 'Data'
EXPORTS = ROOT / CONTRACT['exportRoot']
VANILLA = ROOT / 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources'
PILE_PATCHES = ['Buildings/Storage/SmallIndustrialPile/SmallIndustrialPile.IronTeeth.blueprint.json',
                'Buildings/Storage/LargeIndustrialPile/LargeIndustrialPile.IronTeeth.blueprint.json',
                'MapEditor/Objects/ReservePile/ReservePile.blueprint.json']
failures, report = [], {}


def fail(message):
    failures.append(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def decode(path):
    model = model_pb2.Model()
    model.ParseFromString(zlib.decompress(Path(path).read_bytes()))
    return model


def positions(node):
    for prop in node.vertexProperties:
        if prop.name == 'position':
            return list(struct.iter_unpack('<fff', prop.data))
    return []


def measure(model):
    tris, materials, lo, hi = 0, set(), [1e9] * 3, [-1e9] * 3
    for node in model.nodes:
        if not node.meshes:
            continue
        for mesh in node.meshes:
            tris += len(mesh.indices) // 3
            materials.add(mesh.material)
        for x, y, z in positions(node):
            p = (x + node.position.x, y + node.position.y, z + node.position.z)
            lo = [min(a, b) for a, b in zip(lo, p)]
            hi = [max(a, b) for a, b in zip(hi, p)]
    return tris, materials, lo, hi


def collider(ident):
    w, d, _ = CONTRACT['models'][ident]['size']
    h = round(CONTRACT['models'][ident]['maxHeight'] * 1000) / 1000
    return {'BoxColliders': [{'Center': {'X': w / 2, 'Y': h / 2, 'Z': d / 2}, 'Size': {'X': w, 'Y': h, 'Z': d}}],
            'SphereColliders': [], 'CapsuleColliders': []}


def same_collider(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(json.loads(json.dumps(b)), sort_keys=True) or (
        len(a.get('BoxColliders', [])) == 1 and all(
            abs(a['BoxColliders'][0][k][axis] - b['BoxColliders'][0][k][axis]) < 1e-6 for k in ('Center', 'Size') for axis in 'XYZ')
        and not a.get('SphereColliders') and not a.get('CapsuleColliders'))


common = {p.rsplit('/', 1)[1] for p in read(VANILLA / 'MaterialCollections/MaterialCollection.Common.blueprint.json')['MaterialCollectionSpec']['Materials']}
resources = read(DATA / 'MaterialCollections/MaterialCollection.DeepFrontierMapResources.blueprint.json')['MaterialCollectionSpec']
if resources['CollectionId'] != 'Common':
    fail('DeepFrontierMapResources must extend the Common collection the map editor loads')
editor_materials = common | {p.rsplit('/', 1)[1] for p in resources['Materials']}

for ident, spec in CONTRACT['models'].items():
    active = DATA / (spec['resource'] + '.timbermesh')
    export = EXPORTS / 'Data' / (spec['resource'] + '.timbermesh')
    if not active.is_file() or not export.is_file():
        fail(f'{ident}: {active.relative_to(ROOT)} or its export {export.relative_to(ROOT)} is missing')
        continue
    if active.read_bytes() != export.read_bytes():
        fail(f'{ident}: active mesh differs from the official export (promote {export.relative_to(ROOT)})')
    model = decode(active)
    tris, materials, lo, hi = measure(model)
    w, d, _ = spec['size']
    # Unity axes: x across, y up, z back.
    if lo[0] < -1e-3 or lo[2] < -1e-3 or hi[0] > w + 1e-3 or hi[2] > d + 1e-3:
        fail(f'{ident}: mesh {lo}..{hi} leaves its {w}x{d} footprint')
    if hi[1] > spec['maxHeight'] + 1e-3 or lo[1] < spec['minZ'] - 1e-3:
        fail(f'{ident}: mesh height {lo[1]:.3f}..{hi[1]:.3f} outside {spec["minZ"]}..{spec["maxHeight"]}')
    if tris > spec['triangles']:
        fail(f'{ident}: {tris} triangles exceed the ceiling {spec["triangles"]}')
    missing = sorted(materials - editor_materials)
    if missing:
        fail(f'{ident}: materials not registered for the map editor: {missing}')
    if spec.get('glowNode'):
        glow = [n for n in model.nodes if n.name == spec['glowNode'] and n.meshes]
        if len(glow) != 1:
            fail(f'{ident}: needs exactly one mesh node {spec["glowNode"]}')
        script = (SOURCE / 'Scripts/Radiation/RadioactiveSpring.cs').read_text(encoding='utf-8')
        if f'GlowNode = "{spec["glowNode"]}"' not in script:
            fail(f'{ident}: RadioactiveSpringVisual does not tint the {spec["glowNode"]} node')
    for blueprint in [spec['blueprint']] + spec.get('alsoBoundBy', []):
        path = DATA / blueprint
        if not path.is_file():
            fail(f'{ident}: blueprint {blueprint} missing')
            continue
        value = read(path)
        children = [c for c in value.get('Children', {}).values() if c.get('TimbermeshSpec', {}).get('Model') == spec['resource']]
        if len(children) != 1:
            fail(f'{ident}: {blueprint} must bind {spec["resource"]} exactly once')
            continue
        if not same_collider(children[0].get('CollidersSpec', {}), collider(ident)):
            fail(f'{ident}: {blueprint} collider {children[0].get("CollidersSpec")} differs from the contract')
        size = value['BlockObjectSpec']['Size']
        if [size['X'], size['Y'], size['Z']] != spec['size']:
            fail(f'{ident}: {blueprint} footprint {size} differs from the contract {spec["size"]}')
    report[ident] = {'triangles': tris, 'materials': sorted(materials), 'boundsMin': [round(v, 3) for v in lo],
                     'boundsMax': [round(v, 3) for v in hi]}

names = {}
for path in (SOURCE / 'AssetBundles/Resources').rglob('*'):
    if path.is_file():
        stem = str(path.relative_to(SOURCE / 'AssetBundles/Resources').with_suffix('')).replace('\\', '/')
        names.setdefault(stem, []).append(path.name)
for good, spec in CONTRACT['goods'].items():
    if good == 'note':
        continue
    for resource, ceiling, count in ((spec['primary'], spec['triangles'][0], 1), (spec['secondary'], spec['triangles'][1], spec['items'])):
        active = SOURCE / 'AssetBundles/Resources' / (resource + '.timbermesh')
        export = EXPORTS / 'AssetBundles/Resources' / (resource + '.timbermesh')
        if not active.is_file() or not export.is_file():
            fail(f'{good}: {active.relative_to(ROOT)} or its export is missing')
            continue
        if active.read_bytes() != export.read_bytes():
            fail(f'{good}: bundled mesh {resource} differs from the official export')
        if len(names.get(resource, [])) != 1:
            fail(f'{good}: bundled resource name {resource} is not unique: {names.get(resource)}')
        model = decode(active)
        meshes = [n for n in model.nodes if n.meshes]
        if len(model.nodes) != 1 or len(meshes) != 1 or len(meshes[0].meshes) != 1:
            fail(f'{good}: {resource} must be one node with one mesh (a Unity Mesh asset)')
            continue
        node = meshes[0]
        if (node.position.x, node.position.y, node.position.z) != (0, 0, 0) or (node.rotation.x, node.rotation.y, node.rotation.z) != (0, 0, 0) or (node.scale.x, node.scale.y, node.scale.z) != (1, 1, 1):
            fail(f'{good}: {resource} node is transformed; the Mesh asset would drop it')
        tris, materials, lo, hi = measure(model)
        if materials != {'BeaverCarryingModels'}:
            fail(f'{good}: {resource} must use only the native goods atlas, not {sorted(materials)}')
        half = spec['itemLength'] / 2
        if lo[0] < -half - 1e-3 or hi[0] > half + 1e-3 or hi[1] > 1e-3 or lo[1] < -spec['levelHeight'] - 1e-3:
            fail(f'{good}: {resource} bounds {lo}..{hi} do not hang one level below its origin')
        width = hi[2] - lo[2]
        expected = (count - 1) * spec['itemSpacing']
        if width < expected or width > expected + .2:
            fail(f'{good}: {resource} spans {width:.3f} across items, expected {count} items {spec["itemSpacing"]} apart')
        if tris > ceiling:
            fail(f'{good}: {resource} has {tris} triangles, ceiling {ceiling}')
        report[resource] = {'triangles': tris, 'boundsMin': [round(v, 3) for v in lo], 'boundsMax': [round(v, 3) for v in hi]}
    vis_path = DATA / f'GoodVisualization/GoodVisualization.{good}.blueprint.json'
    if not vis_path.is_file():
        fail(f'{good}: {vis_path.relative_to(ROOT)} missing')
    else:
        vis = read(vis_path)['GoodVisualizationSpec']
        if (vis['Id'], vis['PrimaryMesh'], vis['SecondaryMesh'], vis['LimitingAmount']) != (spec['visualization'], spec['primary'], spec['secondary'], spec['items']):
            fail(f'{good}: GoodVisualization does not name the contract meshes: {vis}')
        if vis['Material'] != 'Materials/Goods/BeaverCarryingModels/BeaverCarryingModels':
            fail(f'{good}: GoodVisualization material {vis["Material"]} is not the native goods atlas')
    good_spec = read(DATA / f'Goods/Good.{good}.blueprint.json')['GoodSpec']
    if good_spec['StockpileVisualization'] != spec['visualization']:
        fail(f'{good}: StockpileVisualization {good_spec["StockpileVisualization"]} is not {spec["visualization"]}')
    for patch in PILE_PATCHES:
        path = DATA / patch
        listed = read(path).get('StockpileGoodPileVisualizerSpec', {}).get('GoodPileVisualizations#append', []) if path.is_file() else []
        if spec['visualization'] not in listed:
            fail(f'{good}: pile {patch} does not append the {spec["visualization"]} visualization')

out = ROOT / 'outputs/mapobjects-integration/validation.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({'models': report, 'failures': failures}, indent=1) + '\n', encoding='utf-8')
if failures:
    print('\n'.join('FAIL ' + f for f in failures))
    raise SystemExit(f'Map object export validation failed ({len(failures)})')
print(json.dumps({'status': 'map-object-exports-checked', 'models': len(CONTRACT['models']),
                  'pileMeshes': sum(1 for k in report if k.startswith('StockpileGoodModels')),
                  'triangles': {k: v['triangles'] for k, v in report.items()}}))
