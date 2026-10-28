"""Cache the native references the map-object and goods art is authored against.

Reads the installed Timberborn resources.assets (read-only) and writes, under
outputs/map-objects/native/ (review inputs, never mod payload):
  - materials.json + textures/: every natural, relic and goods material the
    Deep Frontier map objects use or are compared with (same record layout as
    export_native_civic_materials.py, so native_building_assets-style previews
    can read it);
  - meshes/<name>.json: the native stockpile and carried-goods Unity meshes
    (vertices, normals, uv0, triangles per submesh) that the vanilla
    GoodVisualization blueprints name, for size and style comparison.
The runtime always references the original resources.

Run: python export_map_object_references.py
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dev_environment as dev
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/unitypy'))
import UnityPy  # noqa: E402
from UnityPy.helpers.MeshHelper import MeshHandler  # noqa: E402

GAME = dev.game_data()
OUT = ROOT / 'outputs/map-objects/native'
MATERIALS = {
    # Natural terrain, cliff and source materials (MaterialCollection.Common).
    'Cliff', 'CliffEdge', 'SlopeCliff', 'SlopeCliffEdge', 'SlopeSand', 'Blockage', 'UndergroundRuinsCliff',
    'Ruins', 'WaterSource', 'BadwaterSource', 'UnstableCore', 'DirtCommon', 'DirtUnderground',
    # Relic and goods atlas; stockpile good materials.
    'BeaverCarryingModels', 'Box', 'DirtPile',
    # Liquid goods materials (tank surfaces).
    'CanolaOil', 'Coffee', 'Grease', 'BioFuel', 'Extract', 'Antidote', 'Badwater', 'Catalyst',
    # Iron Teeth metal atlas used by the human cache's fittings.
    'BaseMetal.IronTeeth', 'PaintedMetal.IronTeeth',
}
MESHES = {'1ScrapMetal', '4ScrapMetals', '1MetalBlock', '4MetalBlocks'}


def main():
    env = UnityPy.load(str(GAME / 'resources.assets'))
    objects = {o.path_id: o for o in env.objects}
    (OUT / 'textures').mkdir(parents=True, exist_ok=True)
    (OUT / 'meshes').mkdir(parents=True, exist_ok=True)
    manifest, meshes = {}, {}
    for obj in env.objects:
        if obj.type.name == 'Material':
            data = obj.parse_as_dict()
            name = data['m_Name']
            if name not in MATERIALS:
                continue
            if name in manifest:
                raise SystemExit(f'{name}: more than one native material of this name')
            shader = data['m_Shader']
            record = {'id': obj.path_id, 'shader': objects[shader['m_PathID']].parse_as_dict().get('m_ParsedForm', {}).get('m_Name')
                      if shader['m_FileID'] == 0 and shader['m_PathID'] in objects else f"external {shader}",
                      'keywords': data.get('m_ValidKeywords', data.get('m_ShaderKeywords')),
                      'properties': data['m_SavedProperties'], 'textures': {}}
            for slot, info in data['m_SavedProperties']['m_TexEnvs']:
                pointer = info['m_Texture']
                if pointer['m_PathID'] == 0:
                    continue
                if pointer['m_FileID'] != 0:
                    record['textures'][slot] = {'external': pointer}
                    continue
                texture = objects[pointer['m_PathID']].parse_as_object()
                path = OUT / 'textures' / f"{pointer['m_PathID']}-{texture.m_Name}.png"
                if not path.is_file():
                    texture.image.save(path)
                record['textures'][slot] = {'file': str(path.relative_to(OUT)).replace('\\', '/'),
                                            'size': [texture.m_Width, texture.m_Height],
                                            'scale': info['m_Scale'], 'offset': info['m_Offset'],
                                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            manifest[name] = record
        elif obj.type.name == 'Mesh':
            mesh = obj.parse_as_object()
            if mesh.m_Name not in MESHES:
                continue
            if mesh.m_Name in meshes:
                raise SystemExit(f'{mesh.m_Name}: more than one native mesh of this name')
            handler = MeshHandler(mesh)
            handler.process()
            vertices = [list(v[:3]) for v in handler.m_Vertices]
            normals = [list(v[:3]) for v in handler.m_Normals or []]
            uv0 = [list(v) for v in handler.m_UV0 or []]
            submeshes = [[list(t) for t in sub] for sub in handler.get_triangles()]
            low = [min(v[i] for v in vertices) for i in range(3)]
            high = [max(v[i] for v in vertices) for i in range(3)]
            meshes[mesh.m_Name] = {'vertices': vertices, 'normals': normals, 'uv0': uv0, 'submeshes': submeshes,
                                   'boundsMin': low, 'boundsMax': high,
                                   'triangles': sum(len(s) for s in submeshes)}
    missing = sorted(MATERIALS - set(manifest)) + sorted(MESHES - set(meshes))
    if missing:
        raise SystemExit(f'Not in resources.assets: {missing}')
    (OUT / 'materials.json').write_text(json.dumps(manifest, indent=1) + '\n')
    for name, mesh in meshes.items():
        (OUT / 'meshes' / f'{name}.json').write_text(json.dumps(mesh) + '\n')
    print(json.dumps({'materials': len(manifest), 'meshes': {k: [v['triangles'], v['boundsMin'], v['boundsMax']]
                                                             for k, v in meshes.items()}}))


if __name__ == '__main__':
    main()
