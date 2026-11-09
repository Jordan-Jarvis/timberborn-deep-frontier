"""Cache the native references the More Fluids art is authored against.

Reads the installed Timberborn resources.assets (read-only) and writes, under
outputs/more-fluids-art/native/ (local review inputs, never mod payload):
  - materials.json + textures/: the Folktails, Iron Teeth and Common materials
    the More Fluids models name, in the record layout of
    export_map_object_references.py so map_object_preview.py can preview them;
  - <Name>.timbermesh + <Name>-model.json: vanilla models the More Fluids
    buildings and map objects are compared with (pumps, tanks, sources).
The runtime always references the original resources by name.

Run: python more_fluids_native_refs.py
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dev_environment as dev  # noqa: E402
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/unitypy'))
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline'))
import UnityPy  # noqa: E402
import extract_native_models  # noqa: E402

OUT = ROOT / 'outputs/more-fluids-art/native'
FACTION_MATERIALS = {
    'Folktails': ['BaseMetal', 'BaseWood_Brown', 'BaseWood_LightBrown', 'BaseWood_White', 'BaseWood_Yellow',
                  'Details', 'IrregularPlanks_Brown', 'IrregularPlanks_LightBrown', 'IrregularPlanks_Mossy',
                  'IrregularPlanks_White', 'IrregularPlanks_Yellow', 'PaintedMetal', 'Paper', 'Plaster_White',
                  'PlasteredWood_White', 'ThatchedRoof', 'WindowsAtlas', 'Moss'],
    'IronTeeth': ['BaseMetal', 'BaseWood_DarkBrown', 'BaseWood_Grey', 'BaseWood_Indigo', 'Details',
                  'IrregularPlanks_DarkBrown', 'IrregularPlanks_Grey', 'IrregularPlanks_Indigo',
                  'IrregularPlanks_MetalForged', 'PaintedMetal', 'Paper', 'Plaster_Orange', 'Plaster_White',
                  'PlasteredWood_Orange', 'RoofPlanks', 'WindowsAtlas'],
}
COMMON = ['WaterSource', 'BadwaterSource', 'Cliff', 'CliffEdge', 'Dirt', 'DirtCommon', 'Grass', 'Moss.Folktails',
          'BaseWoodCommon', 'BaseWoodCommon_Amber', 'Ruins', 'UndergroundRuinsCliff', 'Water', 'FountainWater',
          'Antidote', 'Coffee', 'Badwater', 'BeaverCarryingModels', 'UnstableCore', 'Blockage', 'Ivy',
          'PaperCommon', 'Sand.Folktails', 'Path.Folktails', 'Path.IronTeeth', 'Dam.Folktails', 'Dam.IronTeeth']
MATERIALS = {f'{m}.{f}' for f, names in FACTION_MATERIALS.items() for m in names} | set(COMMON)
MODELS = ['WaterPump.Folktails', 'LargeWaterPump.Folktails', 'MechanicalPump.Folktails',
          'DeepWaterPump.IronTeeth', 'DeepMechanicalPump.IronTeeth', 'CompactMechanicalPump.Folktails',
          'CompactMechanicalPump.IronTeeth', 'Centrifuge.Folktails', 'Centrifuge.IronTeeth',
          'Discharge.Folktails', 'Discharge.IronTeeth', 'SmallTank.Folktails', 'SmallTank.IronTeeth',
          'BadwaterPump.Folktails', 'DeepBadwaterPump.IronTeeth', 'Shower.Folktails', 'DoubleShower.IronTeeth',
          'AquiferDrill.Folktails', 'AquiferDrill.IronTeeth', 'WaterSource', 'BadwaterSource',
          'Lodge.Folktails', 'Barrack.IronTeeth']


def materials():
    env = UnityPy.load(str(dev.resources_assets()))
    objects = {o.path_id: o for o in env.objects}
    (OUT / 'textures').mkdir(parents=True, exist_ok=True)
    manifest = {}
    for obj in env.objects:
        if obj.type.name != 'Material':
            continue
        data = obj.parse_as_dict()
        name = data['m_Name']
        if name not in MATERIALS:
            continue
        if name in manifest:
            raise SystemExit(f'{name}: more than one native material of this name')
        shader = data['m_Shader']
        record = {'id': obj.path_id,
                  'shader': objects[shader['m_PathID']].parse_as_dict().get('m_ParsedForm', {}).get('m_Name')
                  if shader['m_FileID'] == 0 and shader['m_PathID'] in objects else f'external {shader}',
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
    missing = sorted(MATERIALS - set(manifest))
    if missing:
        raise SystemExit(f'Not in resources.assets: {missing}')
    (OUT / 'materials.json').write_text(json.dumps(manifest, indent=1) + '\n')
    print('materials', len(manifest), flush=True)


def models(names):
    extract_native_models.OUT = OUT
    extract_native_models.main(names)


if __name__ == '__main__':
    args = sys.argv[1:]
    if args[:1] == ['--models']:
        models(args[1:])
    else:
        materials()
        models(MODELS)
