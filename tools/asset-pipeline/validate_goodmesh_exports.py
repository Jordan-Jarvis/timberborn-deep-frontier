"""Every GoodVisualization mesh must resolve to a Mesh asset the game can load.

GoodVisualizationSpec.PrimaryMesh/SecondaryMesh are AssetRef<Mesh>
(Timberborn.StockpileVisualization, 1.1.2.8; GoodPileVariantsService.Load
throws "Failed to load asset" otherwise, which stopped every load of build
167). A path resolves when it is a vanilla stockpile mesh (named by a vanilla
GoodVisualization blueprint) or a Deep Frontier bundle resource:
  - static (default, validate_all `exports-goodmesh`): the source file is
    src/DeepFrontier/AssetBundles/Resources/<path>.timbermesh under the
    folder the editor step imports with the Timbermesh importer's
    _createMeshAsset (DeepFrontierMaterials.ImportPileMeshes), or a .asset;
  - --bundle <deepfrontier_win> (tools/verify_deep_frontier_package.ps1): the
    built bundle's container holds a UnityEngine.Mesh at that path, readable
    with one submesh.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/DeepFrontier'
VANILLA = ROOT / 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/GoodVisualization'
BUNDLE_ROOT = 'assets/mods/deepfrontier/assetbundles/resources/'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def visualization_meshes(data):
    out = {}
    for path in sorted((data / 'GoodVisualization').glob('*.blueprint.json')) if (data / 'GoodVisualization').is_dir() else []:
        spec = read(path)['GoodVisualizationSpec']
        for key in ('PrimaryMesh', 'SecondaryMesh'):
            if spec.get(key):
                out.setdefault(spec[key], []).append(f'{path.name}:{key}')
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default=str(SOURCE / 'Data'))
    parser.add_argument('--bundle', help='built deepfrontier_win asset bundle to check instead of the sources')
    cli = parser.parse_args()
    vanilla = set()
    for path in VANILLA.glob('*.blueprint.json'):
        spec = read(path)['GoodVisualizationSpec']
        vanilla.update(v for v in (spec.get('PrimaryMesh'), spec.get('SecondaryMesh')) if v)
    meshes = visualization_meshes(Path(cli.data))
    ours = {m: users for m, users in meshes.items() if m not in vanilla}
    failures, report = [], {}
    if cli.bundle:
        sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/unitypy'))
        import UnityPy  # noqa: E402
        env = UnityPy.load(cli.bundle)
        objects = {o.path_id: o for o in env.objects}
        container = {}
        for o in env.objects:
            if o.type.name == 'AssetBundle':
                for name, info in o.parse_as_dict()['m_Container']:
                    target = objects.get(info['asset']['m_PathID'])
                    container.setdefault(name.rsplit('.', 1)[0], []).append(target)
        for mesh, users in ours.items():
            entries = container.get(BUNDLE_ROOT + mesh.lower(), [])
            found = [e for e in entries if e is not None and e.type.name == 'Mesh']
            if len(found) != 1:
                failures.append(f'{mesh} ({", ".join(users)}): bundle holds {[e.type.name for e in entries if e]} at that path, not one Mesh')
                continue
            parsed = found[0].read()
            if not parsed.m_IsReadable or len(parsed.m_SubMeshes) != 1:
                failures.append(f'{mesh}: bundled Mesh must be readable with one submesh')
            report[mesh] = {'bundle': 'Mesh', 'name': parsed.m_Name, 'submeshes': len(parsed.m_SubMeshes)}
    else:
        editor = (SOURCE / 'Editor/DeepFrontierMaterials.cs').read_text(encoding='utf-8')
        pile_root = 'Assets/Mods/DeepFrontier/AssetBundles/Resources/StockpileGoodModels'
        if f'PileMeshRoot = "{pile_root}"' not in editor or '_createMeshAsset' not in editor or 'ImportPileMeshes();' not in editor:
            failures.append('DeepFrontierMaterials.cs must import StockpileGoodModels with the Timbermesh importer _createMeshAsset option')
        for mesh, users in ours.items():
            resources = SOURCE / 'AssetBundles/Resources'
            candidates = [p for p in (resources / f'{mesh}.timbermesh', resources / f'{mesh}.asset') if p.is_file()]
            if len(candidates) != 1:
                failures.append(f'{mesh} ({", ".join(users)}): no single bundled source (.timbermesh or .asset) under AssetBundles/Resources')
                continue
            if candidates[0].suffix == '.timbermesh' and not mesh.startswith('StockpileGoodModels/'):
                failures.append(f'{mesh}: a .timbermesh pile mesh must sit under StockpileGoodModels, where the editor step creates its Mesh asset')
            report[mesh] = {'source': str(candidates[0].relative_to(ROOT)).replace('\\', '/')}
    if failures:
        print('\n'.join('FAIL ' + f for f in failures))
        raise SystemExit(f'GoodVisualization mesh check failed ({len(failures)})')
    print(json.dumps({'status': 'good-visualization-meshes-resolve', 'mode': 'bundle' if cli.bundle else 'source',
                      'vanilla': sorted(m for m in meshes if m in vanilla), 'deepFrontier': report}))


if __name__ == '__main__':
    main()
