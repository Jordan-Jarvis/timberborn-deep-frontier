"""Validate the exported late-game study models against their active blueprints.

For every id in tools/lategame_batches.json: the blueprint's finished and
construction-stage meshes exist in src/DeepFrontier/Data and are the official
export (byte-identical to outputs/lategame-integration/Data), every animated
study part is an animated node, and every TransformSlotInitializerSpec keyword
has slot nodes. Attractions with exported visitor slots
(outputs/lategame-integration/<Id>-visitor-slots.json) must hold exactly as
many '#Slot#<keyword><i>' nodes as their native capacity, inside the block
volume. Static evidence only; native slot use is an in-game check.
"""
import json
import re
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2  # noqa: E402

DATA = ROOT / 'src/DeepFrontier/Data'
EXPORTS = ROOT / 'outputs/lategame-integration'
failures, report = [], []


def fail(message):
    failures.append(message)


blueprints = {}
for path in (DATA / 'Buildings').rglob('*.IronTeeth.blueprint.json'):
    blueprints[path.name[:-len('.IronTeeth.blueprint.json')]] = path

for ident in json.loads((ROOT / 'tools/lategame_batches.json').read_text(encoding='utf-8'))['integrated']:
    if ident not in blueprints:
        fail(f'{ident}: no active blueprint')
        continue
    bp = json.loads(blueprints[ident].read_text(encoding='utf-8'))
    model_path = bp['Children']['#Finished']['TimbermeshSpec']['Model']
    stage_path = bp['Children']['#Unfinished']['Children']['ConstructionStage0']['TimbermeshSpec']['Model']
    meshes = {}
    for resource in (model_path, stage_path):
        active = DATA / (resource + '.timbermesh')
        export = EXPORTS / 'Data' / (resource + '.timbermesh')
        if not active.is_file() or not export.is_file():
            fail(f'{ident}: {resource} missing (active {active.is_file()}, export {export.is_file()})')
            continue
        if active.read_bytes() != export.read_bytes():
            fail(f'{ident}: {resource} in Data is not the official export')
        meshes[resource] = active
    if model_path not in meshes:
        continue
    model = model_pb2.Model()
    model.ParseFromString(zlib.decompress(meshes[model_path].read_bytes()))
    names = [n.name for n in model.nodes]
    registration = json.loads((ROOT / f'outputs/lategame-studies/{ident}-registration.json').read_text(encoding='utf-8'))
    for part in registration.get('animatedParts', []):
        # The exporter prefixes '#' to animated study parts; parts the
        # runtime finds by name (LaunchPad.Rocket) keep their own names.
        # Parts inside a native prop (CompactWaterWheel '<prop>.#Empty#...')
        # leave with the prop, which the blueprint references instead.
        if '.#' in part:
            continue
        if '#' + part not in names and part not in names:
            fail(f'{ident}: animated part {part} is not an exported node')
    slots = bp.get('TransformSlotInitializerSpec', {}).get('Slots', [])
    for slot in slots:
        if not any(n.startswith('#Slot#' + slot['SlotKeyword']) for n in names):
            fail(f'{ident}: no #Slot#{slot["SlotKeyword"]} node for TransformSlotInitializerSpec')
    record = EXPORTS / f'{ident}-visitor-slots.json'
    visitors = 0
    if record.is_file():
        visitor = json.loads(record.read_text(encoding='utf-8'))
        pattern = re.compile(r'^#Slot#' + re.escape(visitor['keyword']) + r'\d+$')
        visitors = sum(1 for n in names if pattern.match(n))
        capacity = bp.get('EnterableSpec', {}).get('CapacityFinished')
        if visitor['model'] != model_path or visitors != visitor['count'] or capacity != visitors:
            fail(f'{ident}: {visitors} exported visitor slots, record {visitor["count"]}, capacity {capacity}')
        if [s['SlotKeyword'] for s in slots] != [visitor['keyword']]:
            fail(f'{ident}: TransformSlotInitializerSpec does not use the exported visitor keyword {visitor["keyword"]}')
        if visitor['sourceHash'] != registration['sourceHash']:
            fail(f'{ident}: visitor slots were exported from another study revision')
    elif bp.get('AttractionSpec') and slots:
        fail(f'{ident}: attraction slots without an exported visitor-slot record')
    report.append({'building': ident, 'nodes': len(names), 'animatedParts': len(registration.get('animatedParts', [])),
                   'slotKeywords': [s['SlotKeyword'] for s in slots], 'visitorSlots': visitors})

if failures:
    print('\n'.join('FAIL ' + f for f in failures))
    raise SystemExit(f'Late-game export validation failed ({len(failures)})')
print(json.dumps({'status': 'lategame-exports-checked', 'buildings': len(report), 'report': report}))
