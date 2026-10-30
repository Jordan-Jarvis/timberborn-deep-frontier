"""Measure each Deep Frontier building's visible material mix from its exported
finished model, for the material cost rule (docs/progression.md, "Material
cost rule"; tools/building_construction_costs.json materialRule).

    python tools/asset-pipeline/measure_building_materials.py [dataRoot]

Reads the generated data (default src/DeepFrontier/Data): every building in
the Deep Frontier Iron Teeth template collection that has a BuildingSpec,
except the structural modules (tools/structural_content.json, which are named
for and priced in their material). Its finished model is the blueprint's
Children["#Finished"].TimbermeshSpec.Model, decoded with the official
Timbermesh schema (timbermesh-plugin/model_pb2.py). Nested native props are
shipped game models and are not measured.

Area is triangle area (node scale applied) per material key, grouped into the
families of materialRule.materials. Details.IronTeeth is split by atlas region
(materialRule.detailsAtlas). Each stone tile is assigned to the reference stone
(materialRule.stoneTiles.references) whose baked BaseColor is nearest in
chromaticity, so brightness does not decide the stone. An unclassified
material, a missing model or a missing texture fails; nothing is defaulted.

Writes tools/building_material_mix.json (model path, sha256, areas per
material key and per family). tools/audit_progression.mjs fails when a
recorded sha256 no longer matches the generated model.
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
from PIL import Image  # noqa: E402

DATA = (ROOT / sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'src/DeepFrontier/Data'
RULE = json.loads((ROOT / 'tools/building_construction_costs.json').read_text(encoding='utf-8'))['materialRule']
MATERIALS = RULE['materials']
DETAILS = RULE['detailsAtlas']
STONE = RULE['stoneTiles']
TEXTURES = ROOT / STONE['textureFolder']
OUT = ROOT / 'tools/building_material_mix.json'
FAMILIES = set(RULE['families']) | {'unpriced'}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def chromaticity(tile):
    path = TEXTURES / f'{tile}.BaseColor.png'
    if not path.is_file():
        raise FileNotFoundError(f'stone tile texture missing: {path}')
    r, g, b = Image.open(path).convert('RGB').resize((1, 1), Image.BOX).getpixel((0, 0))
    total = r + g + b
    if total == 0:
        raise ValueError(f'{tile}: black texture has no chromaticity')
    return (r / total, g / total)


def stone_families():
    """Stone tile -> family of the nearest reference stone by chromaticity."""
    refs = {family: chromaticity(tile) for family, tile in STONE['references'].items()}
    out = {}
    for tile in STONE['tiles']:
        c = chromaticity(tile)
        out[tile] = min(refs, key=lambda f: math.dist(c, refs[f]))
    return out


def details_family(u, v):
    for region in DETAILS['regions']:
        if 'vMin' in region and v < region['vMin']:
            continue
        if 'uMin' in region and u < region['uMin']:
            continue
        if 'vBands' in region and not any(lo <= v <= hi for lo, hi in region['vBands']):
            continue
        return region['family']
    return DETAILS['otherwise']


def family_of(material, stones):
    if material in stones:
        return stones[material]
    if material not in MATERIALS:
        raise ValueError(f'material {material} is not classified in materialRule.materials')
    family = MATERIALS[material]
    if family == 'stone':
        raise ValueError(f'{material} is a stone tile but not listed in materialRule.stoneTiles.tiles')
    return family


def measure(path, stones):
    model = model_pb2.Model()
    model.ParseFromString(zlib.decompress(path.read_bytes()))
    areas, families = {}, {}
    for node in model.nodes:
        if not node.meshes:
            continue
        props = {p.name: p for p in node.vertexProperties}
        if 'position' not in props or 'uv0' not in props:
            raise ValueError(f'{path}: node {node.name} lacks position/uv0')
        pos = struct.unpack(f'<{len(props["position"].data) // 4}f', props['position'].data)
        uv = struct.unpack(f'<{len(props["uv0"].data) // 4}f', props['uv0'].data)
        scale = (node.scale.x, node.scale.y, node.scale.z)
        for mesh in node.meshes:
            details = mesh.material == DETAILS['material']
            family = None if details else family_of(mesh.material, stones)
            idx = mesh.indices
            for t in range(0, len(idx), 3):
                tri = idx[t:t + 3]
                p = [[pos[3 * i + k] * scale[k] for k in range(3)] for i in tri]
                e1 = [p[1][k] - p[0][k] for k in range(3)]
                e2 = [p[2][k] - p[0][k] for k in range(3)]
                cross = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
                area = math.sqrt(sum(c * c for c in cross)) / 2
                if area == 0:
                    continue
                if details:
                    f = details_family(sum(uv[2 * i] for i in tri) / 3, sum(uv[2 * i + 1] for i in tri) / 3)
                    key = f'{mesh.material}#{f}'
                else:
                    f, key = family, mesh.material
                if f not in FAMILIES:
                    raise ValueError(f'{key}: family {f} is not a materialRule family')
                areas[key] = areas.get(key, 0) + area
                families[f] = families.get(f, 0) + area
    return areas, families


def main():
    stones = stone_families()
    structures = {b['id'] for b in read_json(ROOT / 'tools/structural_content.json')['buildings']}
    collection = read_json(DATA / 'TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json')
    paths = collection['TemplateCollectionSpec']['Blueprints#append']
    out = {}
    for rel in paths:
        bp = read_json(DATA / (rel + '.json'))
        ident = bp['TemplateSpec']['TemplateName'].removesuffix('.IronTeeth')
        if not bp.get('BuildingSpec', {}).get('BuildingCost') or ident in structures:
            continue
        model_name = bp['Children']['#Finished']['TimbermeshSpec']['Model']
        model = DATA / (model_name + '.timbermesh')
        if not model.is_file():
            raise FileNotFoundError(f'{ident}: finished model {model_name} is not Deep Frontier data')
        areas, families = measure(model, stones)
        out[ident] = {'model': model_name, 'sha256': hashlib.sha256(model.read_bytes()).hexdigest(),
                      'areas': {k: round(v, 4) for k, v in sorted(areas.items())},
                      'families': {k: round(v, 4) for k, v in sorted(families.items())}}
        print(ident, {k: round(v, 1) for k, v in sorted(families.items())}, flush=True)
    record = {'_comment': 'Generated by tools/asset-pipeline/measure_building_materials.py from the exported finished '
                          'models; do not edit. Areas are model-space triangle areas (tile units squared). '
                          'Stone tiles: ' + ', '.join(f'{t} -> {f}' for t, f in sorted(stones.items())) + '.',
              'stoneTiles': stones, 'buildings': dict(sorted(out.items()))}
    OUT.write_text(json.dumps(record, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(f'Wrote {len(out)} buildings to {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
