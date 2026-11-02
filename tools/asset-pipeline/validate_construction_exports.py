"""Check every Deep Frontier construction site against the native contract (2026-11-02).

For every building template with its own finished model (construction_stage_massing.buildings):

  generated (all but tools/construction_stages.json authored and previewOnly):
    - #Unfinished has exactly two children, in this order: the vanilla
      ConstructionBase the manifest names (nested by BlueprintPath, offset as
      recorded, existing in the vendor resources) and ConstructionStage0;
      ProgressThresholds equals progressThresholds ([0.0], as every vanilla
      Iron Teeth workshop): base until the first material, then the stage;
    - the stage model is the manifest's, in Data byte-identical to the
      official export and its recorded hash, and is not the finished model
      (nor byte-identical to it);
    - the massing recomputed from the current blueprint and finished model
      equals the manifest (a stale stage fails: rebuild it);
    - the stage Timbermesh: one node, only the native stage materials, at
      most triangleCeiling triangles; colliders as recorded;
  authored (the Fisher Flag): a ConstructionBase and a ConstructionStage0
    that is not the finished model, ProgressThresholds [0.0];
  previewOnly (steel leg deck tools, never built): the unfinished child
    names a model that is none of the finished models.

The manifest lists no other building. Mutations of a real site (stage set to
the finished model, base removed, thresholds emptied, base swapped) must each
fail. Exemptions are only the two lists in tools/construction_stages.json,
each with its reason.

Run: python validate_construction_exports.py [--data DIR]
"""
import argparse
import copy
import hashlib
import json
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import construction_stage_massing as massing_module  # noqa: E402
import model_pb2  # noqa: E402  (path added by construction_stage_massing)

ROOT = massing_module.ROOT
CONFIG = massing_module.CONFIG
VANILLA = massing_module.VANILLA
UNFINISHED = '#Unfinished'


def finished_models(blueprint):
    found = []

    def walk(node):
        if 'TimbermeshSpec' in node:
            found.append(node['TimbermeshSpec']['Model'])
        for child in node.get('Children', {}).values():
            walk(child)
    walk(blueprint['Children'][blueprint['BuildingModelSpec']['FinishedModelName']])
    return found


def check_generated(ident, blueprint, entry, data, export_root):
    problems = []
    children = blueprint['Children'].get(UNFINISHED, {}).get('Children', {})
    names = list(children)
    base = entry['base']
    if names != [f"{base['name']}#nested", 'ConstructionStage0']:
        problems.append(f'#Unfinished children {names}, expected [{base["name"]}#nested, ConstructionStage0]')
        return problems
    nested = children[names[0]]
    if nested.get('BlueprintPath') != base['blueprint'] or not (VANILLA / f"{base['blueprint']}.json").is_file():
        problems.append(f'base {nested.get("BlueprintPath")} is not the vanilla {base["blueprint"]}')
    x, y, h = base['offset']
    position = nested.get('Modification', {}).get('TransformSpec', {}).get('Position', {'X': 0, 'Y': 0, 'Z': 0})
    if [position.get('X'), position.get('Y'), position.get('Z')] != [x, h, y]:
        problems.append(f'base offset {position}, expected X {x} Y {h} Z {y}')
    thresholds = blueprint.get('ConstructionSiteProgressVisualizerSpec', {}).get('ProgressThresholds')
    if thresholds != CONFIG['progressThresholds']:
        problems.append(f'ProgressThresholds {thresholds}, expected {CONFIG["progressThresholds"]}')
    stage = children['ConstructionStage0']
    model = stage.get('TimbermeshSpec', {}).get('Model')
    finished = finished_models(blueprint)
    if model != entry['stage']:
        problems.append(f'stage model {model}, expected {entry["stage"]}')
    if model in finished:
        problems.append(f'the stage is the finished model {model}')
    stage_file = data / f'{model}.timbermesh'
    export_file = export_root / 'Data' / f"{entry['stage']}.timbermesh"
    if not stage_file.is_file() or not export_file.is_file():
        problems.append(f'stage files missing (Data {stage_file.is_file()}, export {export_file.is_file()})')
        return problems
    stage_bytes = stage_file.read_bytes()
    if stage_bytes != export_file.read_bytes() or hashlib.sha256(stage_bytes).hexdigest() != entry['exportSha256']:
        problems.append('the stage in Data is not the recorded official export')
    for resource in finished:
        own = data / f'{resource}.timbermesh'   # vanilla props under #Finished are not in Data
        if own.is_file() and own.read_bytes() == stage_bytes:
            problems.append(f'the stage is byte-identical to the finished model {resource}')
    colliders = stage.get('CollidersSpec', {})
    if colliders.get('BoxColliders') != entry['colliders'] or colliders.get('SphereColliders') or colliders.get('CapsuleColliders'):
        problems.append('stage colliders differ from the manifest')
    mesh = model_pb2.Model()
    mesh.ParseFromString(zlib.decompress(stage_bytes))
    meshes = [n for n in mesh.nodes if n.meshes]
    materials = {m.material for n in meshes for m in n.meshes}
    triangles = sum(len(m.indices) for n in meshes for m in n.meshes) // 3
    if len(meshes) != 1:
        problems.append(f'{len(meshes)} mesh nodes, expected one merged node')
    if not materials <= set(CONFIG['materials']) or 'Dirt' not in materials:
        problems.append(f'materials {sorted(materials)} outside the native stage set or without Dirt')
    if triangles > CONFIG['triangleCeiling'] or triangles != entry['triangles']:
        problems.append(f'{triangles} triangles (manifest {entry["triangles"]}, ceiling {CONFIG["triangleCeiling"]})')
    return problems


def check_massing(item, entry, data):
    current = massing_module.massing(item, data)
    return [f'{key} changed since the stage was generated; run build_construction_stages.py -- --models {item["id"]}'
            for key in massing_module.GEOMETRY_KEYS if json.loads(json.dumps(current[key])) != entry[key]]


def check_authored(ident, blueprint):
    children = blueprint['Children'].get(UNFINISHED, {}).get('Children', {})
    names = list(children)
    problems = []
    if len(names) != 2 or not names[0].startswith('ConstructionBase') or names[1] != 'ConstructionStage0':
        problems.append(f'authored site children {names}')
        return problems
    model = children['ConstructionStage0'].get('TimbermeshSpec', {}).get('Model')
    if model in finished_models(blueprint):
        problems.append('the authored stage is the finished model')
    if blueprint.get('ConstructionSiteProgressVisualizerSpec', {}).get('ProgressThresholds') != CONFIG['progressThresholds']:
        problems.append('authored site thresholds differ from progressThresholds')
    return problems


def check_preview(ident, blueprint):
    children = blueprint['Children'].get(UNFINISHED, {}).get('Children', {})
    models = [c.get('TimbermeshSpec', {}).get('Model') for c in children.values()]
    if not models or any(m in finished_models(blueprint) for m in models):
        return [f'preview-only unfinished models {models} repeat a finished model']
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default=str(ROOT / 'src/DeepFrontier/Data'))
    data = Path(parser.parse_args().data)
    export_root = ROOT / CONFIG['exportRoot']
    manifest = json.loads((ROOT / CONFIG['manifest']).read_text(encoding='utf-8'))
    failures = []
    items = massing_module.buildings(data)
    generated = {i['id'] for i in items if i['kind'] == 'generated'}
    for ident in sorted(set(manifest['stages']) - generated):
        failures.append(f'{ident}: manifest stage for a building that is not generated here')
    counts = {'generated': 0, 'authored': 0, 'previewOnly': 0}
    sample = None
    for item in items:
        ident, blueprint, kind = item['id'], item['blueprint'], item['kind']
        counts[kind] += 1
        if kind == 'authored':
            problems = check_authored(ident, blueprint)
        elif kind == 'previewOnly':
            problems = check_preview(ident, blueprint)
        elif ident not in manifest['stages']:
            problems = ['no generated construction stage in the manifest']
        else:
            entry = manifest['stages'][ident]
            problems = check_generated(ident, blueprint, entry, data, export_root)
            if not problems:
                problems = check_massing(item, entry, data)
                sample = sample or (ident, blueprint, entry)
        failures.extend(f'{ident}: {p}' for p in problems)
    # Mutations of a passing site must fail.
    if sample is None:
        failures.append('no passing generated site to mutate')
    else:
        ident, blueprint, entry = sample
        stage = blueprint['Children'][UNFINISHED]['Children']['ConstructionStage0']
        finished = blueprint['Children'][blueprint['BuildingModelSpec']['FinishedModelName']]['TimbermeshSpec']['Model']

        def mutated(change):
            b = copy.deepcopy(blueprint)
            change(b)
            return b
        mutations = {
            'stage is the finished model': mutated(lambda b: b['Children'][UNFINISHED]['Children']['ConstructionStage0'].update(TimbermeshSpec={'Model': finished})),
            'base removed': mutated(lambda b: b['Children'][UNFINISHED]['Children'].pop(f"{entry['base']['name']}#nested")),
            'thresholds emptied': mutated(lambda b: b['ConstructionSiteProgressVisualizerSpec'].update(ProgressThresholds=[])),
            'base swapped': mutated(lambda b: b['Children'][UNFINISHED]['Children'][f"{entry['base']['name']}#nested"].update(BlueprintPath='ConstructionBases/ConstructionBase1x1/Missing.blueprint')),
        }
        for name, b in mutations.items():
            if not check_generated(ident, b, entry, data, export_root):
                failures.append(f'mutation not caught on {ident}: {name}')
        del stage
    if failures:
        print('\n'.join('FAIL ' + f for f in failures))
        raise SystemExit(f'Construction stage validation failed ({len(failures)})')
    print(json.dumps({'status': 'construction-stages-checked', **counts, 'mutations': 4,
                      'exemptions': {'authored': list(CONFIG['authored']), 'previewOnly': list(CONFIG['previewOnly'])}}))


if __name__ == '__main__':
    main()
