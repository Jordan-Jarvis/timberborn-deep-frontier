"""Hold every Deep Frontier building model to its triangle ceiling.

Loading a save pre-builds a placement preview of every building tool, and the
game keeps each model's meshes in memory; the heaviest Deep Frontier models
were 10-30x the largest vanilla Iron Teeth building. This check reads the
exported Timbermesh files (the triangles the game builds) and fails when a
model's finished mesh, its construction-stage mesh, or the total exceeds the
ceiling recorded in tools/asset-pipeline/triangle-budget.json.

Ceilings are the achieved counts after the triangle-budget pass (no visible
loss, see outputs/triangle-budget/), so they stop regressions; the targets in
the same file (TARGETS, from the measured vanilla buildings) are reported,
not enforced. A model that is not listed fails: add it deliberately.

Which file is measured: each model's owning exporter writes its candidate
export (OWNERS). Exporters that write the active Data tree directly
(industrial) are read from --data.

Run:
  python validate_triangle_budget.py              # check against the ceilings
  python validate_triangle_budget.py --measure OUT.json   # write a measurement only
  python validate_triangle_budget.py --record A,B   # set A and B's ceilings to their current counts
"""
import argparse
import json
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2  # noqa: E402

BUDGET = ROOT / 'tools/asset-pipeline/triangle-budget.json'
BASELINE = ROOT / 'tools/asset-pipeline/vanilla-preview-baseline.json'
OUTPUTS = ROOT / 'outputs'

# Targets (triangles of the finished model): from the installed vanilla Iron
# Teeth buildings (largest finished model 20,440, HydroponicGarden; largest
# blueprint 27,906, EarthRepopulator, vanilla-preview-baseline.json). Halved
# on 2026-10-29 (user approval; was grand 40k, workshop 20k): a grand building
# now stays within the largest vanilla model, an ordinary one well under it.
TARGETS = {'grand': 20000, 'workshop': 12000, 'small': 8000,
           # Map objects: the largest vanilla map-object model (UndergroundRuins 2,466;
           # outputs/map-objects/vanilla). Pile goods: one full level of vanilla
           # 4ScrapMetals (64), the per-level cost a pile multiplies.
           'mapobject': 2500, 'pilegood': 64}
CONSTRUCTION_TARGET_SHARE = .25

# Model id -> (family, budget class, candidate export root). None = --data.
CIVIC = OUTPUTS / 'civic-integration/Data'
LATE = OUTPUTS / 'lategame-integration/Data'
OWNERS = {
    'FisheryWorks': ('civic', 'grand', CIVIC),
    'FishHatchery': ('civic', 'grand', CIVIC),
    'Restaurant': ('civic', 'grand', CIVIC),
    'Hospital': ('civic', 'grand', CIVIC),
    'GroceryStore': ('grocery', 'grand', LATE),
    'MaterialsLaboratory': ('research', 'grand', OUTPUTS / 'research-integration/Data'),
    'ReinforcedHydroTurbine': ('hydro', 'grand', OUTPUTS / 'hydro-integration/Data'),
    # Late-game classes by footprint: grand from 90 tiles (10x9) up, ordinary
    # ('workshop', 20k) below that, small utilities (<= 30 tiles) 8k.
    **{name: ('lategame', 'grand', LATE) for name in (
        'NuclearReactor', 'UraniumProcessingPlant', 'DeepMine', 'RadioactiveWasteRefinery',
        'CryogenicLiquefactionPlant', 'ChemicalWorks', 'LaunchPad', 'DeepDrill', 'ElectrolysisPlant',
        'DeepProcessor', 'WaterTreatmentPlant', 'SteelMill', 'ArchiveExcavation',
        'RocketAssemblyHangar', 'CryogenicTankFarm', 'RadioactiveWasteVault',
        'PrecisionMachineWorks', 'MissionControl')},
    **{name: ('lategame', 'workshop', LATE) for name in (
        'FertilizerWorks', 'FoodPackagingWorks', 'TownPlaza', 'ObservationDeck', 'PublicHealthLab',
        'Bathhouse', 'Greenhouse', 'TechnicalSchool', 'CoalPowerPlant', 'OilPowerPlant', 'DeepWell')},
    **{name: ('lategame', 'small', LATE) for name in (
        'SmogScrubber', 'RadioactiveWasteExport', 'RadioactiveSludgeRecoveryPump', 'RadioactiveSludgeOutfall',
        'ReactorChargingBay')},
    **{name: ('industrial', 'workshop', None) for name in (
        'CementKiln', 'ConcreteMixer', 'StoneCrusher', 'SandstoneQuarry', 'LimestoneQuarry',
        'SandstonePit', 'LimestonePit')},
    **{name: ('structural', 'small', OUTPUTS / 'structural-integration/Data') for name in (
        'ConcreteBlock', 'ConcreteOverflowDam', 'ConcreteOverhang8x1', 'ConcreteScaffold3x3',
        'ConcreteScaffold3x3H1', 'ConcreteScaffold3x3H2', 'ConcreteScaffold4x4H1', 'ConcreteScaffold4x4H2',
        'ConcreteScaffold4x4H3', 'ConcreteScaffold5x5H1', 'ConcreteScaffold5x5H2', 'ConcreteScaffold5x5H3',
        'ConcreteSidePlatform3x3', 'ConcreteSidePlatform4x4', 'ConcreteSidePlatform5x5',
        'LimestoneMasonryBlock', 'ReinforcedDamBlock', 'SandstoneMasonryBlock',
        'SteelCantilever10x1', 'SteelCantilever12x1', 'SteelCantilever15x1',
        'SteelBridge8x1', 'SteelBridge10x1', 'SteelBridge12x1', 'SteelBridge15x1',
        'SteelColumnH1', 'SteelColumnH2', 'SteelColumnH3', 'SteelColumnH4', 'SteelColumnH5', 'SteelColumnH6',
        'SteelDeck3x3', 'SteelDeck5x5')},
}
# Map objects and pile goods (tools/map_objects.json, build_map_objects.py):
# measured from their candidate exports, like the other families.
MAP_OBJECTS = json.loads((ROOT / 'tools/map_objects.json').read_text(encoding='utf-8'))
# Where each model's native-prop placements are recorded (study name).
STUDY = {'GroceryStore': 'GroceryMarket', 'SandstoneQuarry': 'MineralQuarry', 'LimestoneQuarry': 'MineralQuarry'}


def decode(path):
    model = model_pb2.Model()
    model.ParseFromString(zlib.decompress(path.read_bytes()))
    return model


def measure_file(path):
    model = decode(path)
    nodes, materials = [], {}
    for node in model.nodes:
        if node.vertexCount <= 0:
            continue
        tris = sum(len(m.indices) for m in node.meshes) // 3
        nodes.append({'node': node.name, 'triangles': tris, 'vertices': node.vertexCount, 'slots': len(node.meshes)})
        for m in node.meshes:
            materials[m.material] = materials.get(m.material, 0) + len(m.indices) // 3
    file = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    return {'file': str(file).replace('\\', '/'), 'bytes': path.stat().st_size,
            'triangles': sum(n['triangles'] for n in nodes), 'vertices': sum(n['vertices'] for n in nodes),
            'renderers': len(nodes), 'slots': sum(n['slots'] for n in nodes), 'materials': len(materials),
            'nodes': sorted(nodes, key=lambda n: -n['triangles']),
            'byMaterial': dict(sorted(materials.items(), key=lambda kv: -kv[1]))}


_native_cache = {}


def native_prop_triangles(ident, blueprint):
    """Native props the export's study places (its native-assembly manifest,
    written with the scene and promoted with the export), so a candidate
    export is measured with its own props, not the active blueprint's."""
    manifest = OUTPUTS / f'reference-studies/{STUDY.get(ident, ident)}-native-assembly.json'
    if not manifest.is_file():
        if blueprint.get('NativeBuildingPropsSpec', {}).get('Props'):
            raise SystemExit(f'{ident}: blueprint has native props but {manifest.name} is missing')
        return 0, 0
    props = json.loads(manifest.read_text(encoding='utf-8'))['props']
    total = 0
    for entry in props:
        path = (Path(entry['sourceFile']) if 'dependency' in entry
                else OUTPUTS / 'native-civic-assets' / (entry['model'] + '.timbermesh'))
        if path not in _native_cache:
            _native_cache[path] = measure_file(path)['triangles']
        total += _native_cache[path]
    return total, len(props)


def models_of(blueprint):
    finished = blueprint.get('Children', {}).get('#Finished', {}).get('TimbermeshSpec', {}).get('Model')
    stages = []
    for name, child in sorted(blueprint.get('Children', {}).get('#Unfinished', {}).get('Children', {}).items()):
        if 'TimbermeshSpec' in child:
            stages.append(child['TimbermeshSpec']['Model'])
    return finished, stages


def measure(data):
    rows, problems = {}, []
    for path in sorted((data / 'Buildings').rglob('*.IronTeeth.blueprint.json')):
        blueprint = json.loads(path.read_text(encoding='utf-8-sig'))
        if 'PlaceableBlockObjectSpec' not in blueprint:
            continue
        ident = path.name[:-len('.IronTeeth.blueprint.json')]
        finished, stages = models_of(blueprint)
        if finished is None or not (data / (finished + '.timbermesh')).is_file():
            continue  # vanilla model: shipped content, not ours
        if ident not in OWNERS:
            problems.append(f'{ident}: own model {finished} has no triangle-budget owner (add it to OWNERS)')
            continue
        family, klass, root = OWNERS[ident]
        root = root or data
        resolved = []
        for resource in [finished] + stages:
            file = root / (resource + '.timbermesh')
            if not file.is_file():
                problems.append(f'{ident}: {file.relative_to(ROOT)} is missing')
                break
            resolved.append(file)
        else:
            fin = measure_file(resolved[0])
            con = [measure_file(f) for f in resolved[1:]]
            try:
                props, prop_count = native_prop_triangles(ident, blueprint)
            except SystemExit as error:
                problems.append(str(error))
                props, prop_count = 0, 0
            rows[ident] = {'family': family, 'class': klass, 'target': TARGETS[klass],
                           'finished': fin, 'construction': con, 'nativeProps': {'count': prop_count, 'triangles': props},
                           'constructionIdenticalToFinished': all(f.read_bytes() == resolved[0].read_bytes() for f in resolved[1:]),
                           'blueprintTriangles': fin['triangles'] + sum(c['triangles'] for c in con)}
    exports = ROOT / MAP_OBJECTS['exportRoot']
    entries = [(ident, 'mapobject', exports / 'Data' / (spec['resource'] + '.timbermesh')) for ident, spec in MAP_OBJECTS['models'].items()]
    entries += [(resource.rsplit('/', 1)[1], 'pilegood', exports / 'AssetBundles/Resources' / (resource + '.timbermesh'))
                for good, spec in MAP_OBJECTS['goods'].items() if good != 'note' for resource in (spec['primary'], spec['secondary'])]
    for ident, klass, file in entries:
        if not file.is_file():
            problems.append(f'{ident}: {file.relative_to(ROOT)} is missing')
            continue
        fin = measure_file(file)
        rows[ident] = {'family': 'mapobjects', 'class': klass, 'target': TARGETS[klass], 'finished': fin, 'construction': [],
                       'nativeProps': {'count': 0, 'triangles': 0}, 'constructionIdenticalToFinished': True,
                       'blueprintTriangles': fin['triangles']}
    return rows, problems


def vanilla_reference():
    baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
    finished = {k: v['triangles'] for k, v in baseline['models'].items()
                if k.startswith('Buildings/') and k.endswith('.Model') and 'ConstructionStage' not in k}
    top = sorted(finished.items(), key=lambda kv: -kv[1])[:5]
    blue = sorted(baseline['buildings'], key=lambda b: -b['triangles'])[:5]
    return {'source': 'tools/asset-pipeline/vanilla-preview-baseline.json (installed resources.assets, UnityPy)',
            'largestFinishedModels': [{'model': k, 'triangles': v} for k, v in top],
            'largestBlueprints': [{'building': b['building'], 'triangles': b['triangles']} for b in blue]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default=str(ROOT / 'src/DeepFrontier/Data'))
    parser.add_argument('--measure', help='write a measurement to this JSON path and exit')
    parser.add_argument('--record', help='comma-separated model ids: set their ceilings in triangle-budget.json '
                        'to the counts measured now (after a reviewed reduction), then check')
    cli = parser.parse_args()
    rows, problems = measure(Path(cli.data))
    if cli.measure:
        out = Path(cli.measure)
        out.parent.mkdir(parents=True, exist_ok=True)
        total = sum(r['blueprintTriangles'] for r in rows.values())
        out.write_text(json.dumps({'vanilla': vanilla_reference(), 'targets': TARGETS,
                                   'constructionTargetShare': CONSTRUCTION_TARGET_SHARE,
                                   'totalBlueprintTriangles': total,
                                   'totalFinishedTriangles': sum(r['finished']['triangles'] for r in rows.values()),
                                   'models': rows, 'problems': problems}, indent=1) + '\n', encoding='utf-8')
        print(json.dumps({'measured': len(rows), 'totalBlueprintTriangles': total, 'problems': len(problems)}))
        return
    budget = json.loads(BUDGET.read_text(encoding='utf-8')) if BUDGET.is_file() else {'models': {}, 'totalBlueprintTriangles': 0}
    if cli.record:
        for ident in cli.record.split(','):
            if ident not in rows:
                raise SystemExit(f'{ident}: no exported model measured to record')
            row = rows[ident]
            budget['models'][ident] = {'family': row['family'], 'class': row['class'], 'target': row['target'],
                                       'finished': row['finished']['triangles'], 'vertices': row['finished']['vertices'],
                                       'construction': max([c['triangles'] for c in row['construction']] or [0]),
                                       'file': row['finished']['file']}
        budget['models'] = dict(sorted(budget['models'].items()))
        budget['totalBlueprintTriangles'] = sum(r['blueprintTriangles'] for i, r in rows.items() if i in budget['models'])
        budget['note'] = ('Ceilings are the counts achieved by the triangle-budget pass (outputs/triangle-budget); '
                          'targets are reported, not enforced. Raise a ceiling only with a reviewed render sheet.')
        BUDGET.write_text(json.dumps(budget, indent=1) + '\n', encoding='utf-8')
    failures = list(problems)
    for ident, row in sorted(rows.items()):
        limit = budget['models'].get(ident)
        if limit is None:
            failures.append(f'{ident}: no ceiling in {BUDGET.name}')
            continue
        if row['finished']['triangles'] > limit['finished']:
            failures.append(f"{ident}: finished model {row['finished']['triangles']} triangles exceed its ceiling {limit['finished']}")
        if row['finished']['vertices'] > limit['vertices']:
            failures.append(f"{ident}: finished model {row['finished']['vertices']} vertices exceed its ceiling {limit['vertices']}")
        for stage in row['construction']:
            if stage['triangles'] > limit['construction']:
                failures.append(f"{ident}: construction stage {stage['triangles']} triangles exceed its ceiling {limit['construction']}")
    for ident in sorted(set(budget['models']) - set(rows)):
        failures.append(f'{ident}: ceiling listed but no exported model measured')
    total = sum(r['blueprintTriangles'] for i, r in rows.items() if i in budget['models'])
    if total > budget['totalBlueprintTriangles']:
        failures.append(f"total {total} blueprint triangles exceed the ceiling {budget['totalBlueprintTriangles']}")
    if failures:
        print('\n'.join('FAIL ' + f for f in failures))
        raise SystemExit(f'Triangle budget validation failed ({len(failures)})')
    over = sorted((ident for ident, r in rows.items() if r['finished']['triangles'] > r['target']),
                  key=lambda i: -rows[i]['finished']['triangles'])
    print(json.dumps({'status': 'triangle-budget-checked', 'models': len(rows), 'totalBlueprintTriangles': total,
                      'ceiling': budget['totalBlueprintTriangles'], 'aboveTarget': len(over),
                      'largest': over[:5]}))


if __name__ == '__main__':
    main()
