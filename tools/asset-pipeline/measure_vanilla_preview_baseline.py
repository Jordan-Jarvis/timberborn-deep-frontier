"""Measure the preview render cost of every shipped Iron Teeth building.

Reads the installed game's resources.assets (UnityPy 1.25.4): each model a
vanilla Iron Teeth (or faction-neutral) placeable blueprint names through a
TimbermeshSpec is the Timbermesh payload of that prefab's model component.
Writes tools/asset-pipeline/vanilla-preview-baseline.json, which
validate_preview_budget_exports.py derives its ceiling from. A placement
preview instantiates every model of the blueprint (finished, construction
stage, props), and native highlighting walks all of their renderers, so the
counts are per blueprint. Re-run after a game update.

Run: python measure_vanilla_preview_baseline.py
"""
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dev_environment as dev
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/unitypy'))
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import UnityPy  # noqa: E402
import model_pb2  # noqa: E402

if UnityPy.__version__ != '1.25.4':
    raise RuntimeError('Use the inspected UnityPy 1.25.4 API')
GAME = dev.game_data()
VANILLA = ROOT / 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources'
OUT = ROOT / 'tools/asset-pipeline/vanilla-preview-baseline.json'


def model_counts(model):
    nodes = [n for n in model.nodes if n.vertexCount > 0]
    return {'renderers': len(nodes), 'slots': sum(len(n.meshes) for n in nodes),
            'triangles': sum(len(m.indices) for n in nodes for m in n.meshes) // 3}


def main():
    env = UnityPy.load(str(GAME / 'globalgamemanagers'), str(GAME / 'resources.assets'))
    manager = next(o for o in env.objects if o.type.name == 'ResourceManager')
    container = {path: pointer for path, pointer in manager.parse_as_dict()['m_Container']}
    resources = next(f for f in env.assets if f.name.lower().endswith('resources.assets'))
    if manager.assets_file.externals[4].path != 'resources.assets':
        raise RuntimeError('ResourceManager file index 5 is no longer resources.assets')
    objects = resources.objects

    def payload(resource):
        pointer = container[resource.lower()]
        if pointer['m_FileID'] != 5:
            raise RuntimeError(f'{resource}: not in resources.assets')
        prefab = objects[pointer['m_PathID']]
        if prefab.type.name == 'Mesh':
            # A plain Unity mesh asset (single renderer, no Timbermesh node tree).
            mesh = prefab.parse_as_dict()
            return {'renderers': 1, 'slots': len(mesh['m_SubMeshes']),
                    'triangles': sum(s['indexCount'] for s in mesh['m_SubMeshes']) // 3}
        if prefab.type.name != 'GameObject':
            raise RuntimeError(f'{resource}: unexpected {prefab.type.name}')
        for component in prefab.parse_as_dict()['m_Component']:
            target = objects[component['component']['m_PathID']]
            if target.type.name != 'MonoBehaviour':
                continue
            data = target.get_raw_data()
            # Unity MonoBehaviour header (32 bytes for an unnamed component),
            # then the BinaryData._bytes array: int32 length + bytes
            # (read_native_civic_models.py uses the same layout).
            if len(data) < 36:
                continue
            length = struct.unpack_from('<I', data, 32)[0]
            if 36 + length > len(data):
                continue
            try:
                model = model_pb2.Model()
                model.ParseFromString(zlib.decompress(data[36:36 + length]))
            except (zlib.error, ValueError):
                continue
            return model_counts(model)
        raise RuntimeError(f'{resource}: no Timbermesh payload on its prefab')

    def models(blueprint, found):
        if 'TimbermeshSpec' in blueprint:
            found.append(blueprint['TimbermeshSpec']['Model'])
        for child in blueprint.get('Children', {}).values():
            models(child, found)
        return found

    buildings, measured = [], {}
    for path in sorted((VANILLA / 'Buildings').rglob('*.blueprint.json')):
        if '.Folktails.' in path.name:
            continue
        blueprint = json.loads(path.read_text(encoding='utf-8-sig'))
        if 'PlaceableBlockObjectSpec' not in blueprint:
            continue
        total = {'renderers': 0, 'slots': 0, 'triangles': 0}
        for resource in models(blueprint, []):
            if resource not in measured:
                measured[resource] = payload(resource)
            for key, value in measured[resource].items():
                total[key] += value
        buildings.append({'building': path.name[:-len('.blueprint.json')], **total})
    record = {
        'source': 'Installed Timberborn resources.assets via UnityPy 1.25.4; models named by vendor blueprints',
        'resourcesAssetsSha256': hashlib.sha256((GAME / 'resources.assets').read_bytes()).hexdigest(),
        'max': {key: max(b[key] for b in buildings) for key in ('renderers', 'slots', 'triangles')},
        'buildings': buildings,
        'models': dict(sorted(measured.items())),
    }
    OUT.write_text(json.dumps(record, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'buildings': len(buildings), 'max': record['max']}))


if __name__ == '__main__':
    main()
