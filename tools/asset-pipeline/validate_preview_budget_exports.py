"""Cap the per-building cost of a native placement preview.

Every frame a preview is shown, Timberborn 1.1.2.8 PreviewPlacer.ShowPreviews
re-highlights it (Highlighter -> HighlightableObject.UpdateColorAndHighlight
twice -> MaterialColorer over every MeshRenderer and material slot, inactive
construction stage included, and HighlightRenderingService over every
renderer). One Timbermesh node with vertices is one MeshRenderer and each of
its meshes one material slot (StaticMeshBuilder). For every Deep Frontier
placeable blueprint this sums renderers and slots over every model the
blueprint instantiates: its own models in Data, native props (resolved
through the native-assembly manifests, as validate_model_bindings.py does)
and vanilla models (tools/asset-pipeline/vanilla-preview-baseline.json,
measured from the installed game by measure_vanilla_preview_baseline.py).

Ceiling: RENDERER_FACTOR x and SLOT_FACTOR x the largest shipped Iron Teeth
building in that baseline. It is a regression ceiling: the civic exports
before the static joins (static_mesh_merge.py) carried up to 333 renderers
and 412 slots and fail it; the largest building after the joins sits
below it. The report also lists the block volume and the auto-wall edges the
native preview navmesh rebuilds every frame (BlockObjectPreviewNavMesh ->
NavMeshObjectUpdater), which this check reports but does not cap.

Run: python validate_preview_budget_exports.py [--data DIR]
"""
import argparse
import json
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2  # noqa: E402

RENDERER_FACTOR = 5
SLOT_FACTOR = 4
BASELINE = ROOT / 'tools/asset-pipeline/vanilla-preview-baseline.json'


def native_models():
    found = {}
    for manifest in (ROOT / 'outputs/reference-studies').glob('*-native-assembly.json'):
        for prop in json.loads(manifest.read_text(encoding='utf-8'))['props']:
            path = (Path(prop['sourceFile']) if 'dependency' in prop
                    else ROOT / 'outputs/native-civic-assets' / (prop['model'] + '.timbermesh'))
            found[prop['resource']] = path
    return found


def counts(path):
    model = model_pb2.Model()
    model.ParseFromString(zlib.decompress(path.read_bytes()))
    nodes = [n for n in model.nodes if n.vertexCount > 0]
    return {'renderers': len(nodes), 'slots': sum(len(n.meshes) for n in nodes),
            'triangles': sum(len(m.indices) for n in nodes for m in n.meshes) // 3}


def models(blueprint, found):
    if 'TimbermeshSpec' in blueprint:
        found.append(blueprint['TimbermeshSpec']['Model'])
    for child in blueprint.get('Children', {}).values():
        models(child, found)
    return found


def nav_auto_wall_edges(spec, nav):
    """Blocked edges per nav group that NavMeshObjectUpdater.Update builds from
    the occupied blocks (Timberborn 1.1.2.8), for the report only."""
    size = spec['Size']
    sx, sy = size['X'], size['Y']
    bottom, top = set(), set()
    for i, block in enumerate(spec['Blocks']):
        z, rest = divmod(i, sx * sy)
        y, x = divmod(rest, sx)
        flags = {f.strip() for f in block.get('Occupations', 'None').split(',')}
        if flags & {'Bottom', 'All'}:
            bottom.add((x, y, z))
        if flags & {'Top', 'All'}:
            top.add((x, y, z))
    edges = {(c, (c[0], c[1], c[2] + 1)) for c in top}
    if (nav or {}).get('NoAutoWalls'):
        return len(edges)
    entrance = spec.get('Entrance', {}).get('HasEntrance')
    for c in bottom:
        if not entrance:
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                n = (c[0] + dx, c[1] + dy, c[2])
                if n in bottom:
                    edges.add((c, n))
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            n = (c[0] + dx, c[1] + dy, c[2])
            if n in bottom:
                continue
            px, py = dy, dx
            edges.update({(c, n), (c, (n[0] + px, n[1] + py, n[2])), (c, (n[0] - px, n[1] - py, n[2])),
                          ((c[0] + px, c[1] + py, c[2]), n), ((c[0] - px, c[1] - py, c[2]), n)})
    return len(edges)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default=str(ROOT / 'src/DeepFrontier/Data'))
    data = Path(parser.parse_args().data)
    baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
    ceiling = {'renderers': RENDERER_FACTOR * baseline['max']['renderers'],
               'slots': SLOT_FACTOR * baseline['max']['slots']}
    natives = native_models()
    rows, failures = [], []
    for path in sorted((data / 'Buildings').rglob('*.blueprint.json')):
        blueprint = json.loads(path.read_text(encoding='utf-8-sig'))
        if 'PlaceableBlockObjectSpec' not in blueprint:
            continue
        total = {'renderers': 0, 'slots': 0, 'triangles': 0}
        own = 0
        for resource in models(blueprint, []):
            file = data / (resource + '.timbermesh')
            if file.is_file():
                measured = counts(file)
                own += 1
            elif resource in natives:
                measured = counts(natives[resource])
            elif resource in baseline['models']:
                measured = baseline['models'][resource]
            else:
                failures.append(f'{path.name}: model {resource} is neither in Data, a native prop nor the vanilla baseline')
                continue
            for key in total:
                total[key] += measured[key]
        if not own:
            continue  # vanilla models only: shipped content, not ours
        spec = blueprint['BlockObjectSpec']
        row = {'building': path.name[:-len('.blueprint.json')], **total, 'blocks': len(spec['Blocks']),
               'occupiedBlocks': sum(1 for b in spec['Blocks'] if b.get('Occupations', 'None') != 'None'),
               'previewNavAutoWallEdgesPerGroup': nav_auto_wall_edges(spec, blueprint.get('BlockObjectNavMeshSettingsSpec'))}
        rows.append(row)
        for key in ('renderers', 'slots'):
            if total[key] > ceiling[key]:
                failures.append(f"{row['building']}: {total[key]} preview {key} exceed the ceiling {ceiling[key]} "
                                f"({RENDERER_FACTOR if key == 'renderers' else SLOT_FACTOR}x vanilla max {baseline['max'][key]})")
    rows.sort(key=lambda r: -r['slots'])
    report = {'ceiling': ceiling, 'vanillaMax': baseline['max'], 'buildings': len(rows), 'rows': rows}
    out = ROOT / 'outputs/preview-budget.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    if failures:
        print('\n'.join('FAIL ' + f for f in failures))
        raise SystemExit(f'Preview budget validation failed ({len(failures)})')
    worst = rows[0] if rows else None
    print(json.dumps({'status': 'preview-budget-checked', 'buildings': len(rows), 'ceiling': ceiling,
                      'vanillaMax': baseline['max'], 'largestSlots': worst and {k: worst[k] for k in ('building', 'renderers', 'slots')},
                      'largestNavEdges': max(rows, key=lambda r: r['previewNavAutoWallEdgesPerGroup'])['building'] if rows else None}))


if __name__ == '__main__':
    main()
