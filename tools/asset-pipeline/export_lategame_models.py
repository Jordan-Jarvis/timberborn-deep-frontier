"""Official Timbermesh export of late-game studies into a candidate folder.

Reads src/DeepFrontier/Art/Source/<Ident>-ReferenceStudy.blend (written by
render_lategame_studies.py) and its outputs/lategame-studies/<Ident>-registration.json.
Writes outputs/lategame-integration/Data/<model path>.timbermesh and its
ConstructionStage0 copy at the paths the existing blueprint already names.
lategame_building_content.mjs promotes them together with the new blueprint
data; the active package is not touched here.

Never moves, scales or repairs artwork. Native/dependency props are removed
from the payload (the blueprint references the original resources); preview
water planes stay as static native Water surfaces.

The Grocery Store exports from the approved Grocery Market study
(GroceryMarket-ReferenceStudy.blend, 32-slot civic palette, registration by
register_grocery_market.py).

Run: blender -b --python-exit-code 1 --python export_lategame_models.py -- --models A,B
"""
import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import timbermesh_exporter as exporter
from reference_materials import NATIVE_INDUSTRIAL_MATERIALS
import static_mesh_merge

OUT = ROOT / 'outputs/lategame-integration/Data'
ART = ROOT / 'src/DeepFrontier/AssetBundles/Resources/Materials/DeepFrontierIndustrial'
# Native names for slots that resolve to shipped (or dependency) materials.
NATIVE = dict(NATIVE_INDUSTRIAL_MATERIALS)
NATIVE.update({2: 'BaseMetal.IronTeeth', 7: 'Details.IronTeeth', 11: 'Water',
               27: 'Plaster_White.IronTeeth', 28: 'Plaster_Orange.IronTeeth',
               29: 'IrregularPlanks_MetalForged.IronTeeth', 30: 'WindowsAtlas.IronTeeth',
               31: 'BaseWood_Brown.Folktails', 32: 'PaintedMetal.IronTeeth',
               33: 'BaseWood_Grey.IronTeeth', 34: 'IrregularPlanks_Grey.IronTeeth'})


# Building id -> (study name, palette size). Late-game studies share their id.
STUDIES = {'GroceryStore': ('GroceryMarket', 32)}

# Model paths of studies whose generator writes a new blueprint (build 122
# integration). The active blueprint does not exist yet (SteelMill,
# ArchiveExcavation, CryogenicTankFarm, SmogScrubber) or still names a vanilla
# placeholder model (the three radiation buildings). Each must equal the path
# its generator writes (create_frontier_expansion_content.mjs buildingDefinitions,
# radiation_content.mjs RADIATION_BUILDINGS); once the active blueprint names
# its own model, it must agree with this entry.
DECLARED_MODELS = {
    'SteelMill': 'Buildings/Metal/SteelMill/SteelMill.IronTeeth.Model',
    'ArchiveExcavation': 'Buildings/Science/ArchiveExcavation/ArchiveExcavation.IronTeeth.Model',
    'CryogenicTankFarm': 'Buildings/Storage/CryogenicTankFarm/CryogenicTankFarm.IronTeeth.Model',
    'SmogScrubber': 'Buildings/Wellbeing/SmogScrubber/SmogScrubber.IronTeeth.Model',
    'RadioactiveWasteExport': 'Buildings/Water/RadioactiveWasteExport/RadioactiveWasteExport.IronTeeth.Model',
    'RadioactiveSludgeOutfall': 'Buildings/Water/RadioactiveSludgeOutfall/RadioactiveSludgeOutfall.IronTeeth.Model',
    'RadioactiveSludgeRecoveryPump': 'Buildings/Water/RadioactiveSludgeRecoveryPump/RadioactiveSludgeRecoveryPump.IronTeeth.Model',
    'Bathhouse': 'Buildings/Wellbeing/Bathhouse/Bathhouse.IronTeeth.Model',
    'TownPlaza': 'Buildings/Wellbeing/TownPlaza/TownPlaza.IronTeeth.Model',
    'ObservationDeck': 'Buildings/Wellbeing/ObservationDeck/ObservationDeck.IronTeeth.Model',
    'CoalPowerPlant': 'Buildings/Power/CoalPowerPlant/CoalPowerPlant.IronTeeth.Model',
    'OilPowerPlant': 'Buildings/Power/OilPowerPlant/OilPowerPlant.IronTeeth.Model',
}

# Visitor slots of the open-air wellbeing attractions: native slot empties
# '#Slot#Spot<i>' (TransformSlotInitializerSpec SlotKeyword 'Spot'), placed on
# the study's own walking surfaces and facing what the visitor looks at. The
# count is written to outputs/lategame-integration/<Ident>-visitor-slots.json,
# which the generator reads for the attraction capacity. The Bathhouse seats
# its first bathers in the outdoor pool and the rest inside the hall.
VISITOR_SLOT_KEYWORD = 'Spot'


def town_plaza_slots(registration):
    """The paving ring round the fountain basin (lategame_TownPlaza.FOUNTAIN),
    facing the jet (FC), on the flag top (FLAG); the door path cell stays free."""
    import lategame_TownPlaza as M
    x0, y0, x1, y1 = M.FOUNTAIN
    walkable = {tuple(c) for c in M.WALKABLE}
    door = {tuple(d['entrance']) for d in registration['doors']}
    slots = []
    for y in range(y0 - 1, y1 + 1):
        for x in range(x0 - 1, x1 + 1):
            if x0 <= x < x1 and y0 <= y < y1:
                continue
            cell = (x, y, 0)
            if cell in door:
                continue
            if cell not in walkable:
                raise ValueError(f'TownPlaza: fountain ring cell {cell} is not walkable paving')
            cx, cy = x + .5, y + .5
            slots.append(((cx, cy, M.FLAG), (M.FC[0] - cx, M.FC[1] - cy)))
    return slots


def observation_deck_slots(registration):
    """The outer ring of the layer-12 deck (lategame_ObservationDeck.TERRACE),
    each visitor facing out over the rail."""
    import lategame_ObservationDeck as M
    w, h = registration['footprint']
    occupied = {tuple(c) for c in registration['occupied']}
    slots = []
    for x, y, z in M.TERRACE['cells']:
        if (x, y, z) in occupied or (x, y, z - 1) not in occupied:
            raise ValueError(f'ObservationDeck: terrace cell {(x, y, z)} is not a free cell on the deck slab')
        if x not in (0, w - 1) and y not in (0, h - 1):
            continue
        cx, cy = x + .5, y + .5
        slots.append(((cx, cy, float(M.DECK)), (cx - w / 2, cy - h / 2)))
    return slots


def bathhouse_slots(registration):
    """Bathers seated in the outdoor plunge pool (lategame_Bathhouse.BATH_SEATS,
    first, so visitors fill them first), then the rest of the native capacity
    seated inside the closed hall (HALL_SEATS), unseen."""
    import lategame_Bathhouse as M
    w, h = registration['footprint']
    slots = []
    for x, y, z, fx, fy in M.BATH_SEATS + M.HALL_SEATS:
        if not (0 < x < w and 0 < y < h):
            raise ValueError(f'Bathhouse: seat {(x, y)} lies outside the footprint')
        slots.append(((x, y, z), (fx, fy)))
    return slots


VISITOR_SLOTS = {'TownPlaza': town_plaza_slots, 'ObservationDeck': observation_deck_slots,
                 'Bathhouse': bathhouse_slots}


def model_path(ident):
    """The model resource path named by the active blueprint (unchanged), or
    the declared path of a study whose blueprint is written by this integration."""
    matches = list((ROOT / 'src/DeepFrontier/Data/Buildings').rglob(f'{ident}.IronTeeth.blueprint.json'))
    if len(matches) > 1:
        raise ValueError(f'{ident}: expected at most one active blueprint, found {len(matches)}')
    path = None
    if matches:
        blueprint = json.loads(matches[0].read_text(encoding='utf-8-sig'))
        path = blueprint['Children']['#Finished']['TimbermeshSpec']['Model']
    if ident in DECLARED_MODELS:
        declared = DECLARED_MODELS[ident]
        if path is not None and path.endswith(f'/{ident}.IronTeeth.Model') and path != declared:
            raise ValueError(f'{ident}: active blueprint names {path}, declared {declared}')
        return declared
    if path is None:
        raise ValueError(f'{ident}: no active blueprint and no declared model path')
    if not path.endswith(f'/{ident}.IronTeeth.Model'):
        raise ValueError(f'{ident}: unexpected model path {path}')
    return path


def export_model(ident):
    study, slots = STUDIES.get(ident, (ident, 35))
    registration = json.loads((ROOT / f'outputs/lategame-studies/{study}-registration.json').read_text())
    if registration['ident'] != ident:
        raise ValueError(f'{study} registration belongs to {registration["ident"]}, not {ident}')
    blend = ROOT / f'src/DeepFrontier/Art/Source/{study}-ReferenceStudy.blend'
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    collection = bpy.data.collections[study + '.ReferenceStudy']
    for obj in list(collection.all_objects):
        if 'native_resource' in obj:
            bpy.data.objects.remove(obj, do_unlink=True)
    catalog = json.loads((ART / 'material-catalog.json').read_text())
    if len(catalog) != 27:
        raise ValueError('The industrial custom-tile catalog must have exactly 27 slots')
    renamed = set()
    for obj in collection.all_objects:
        if obj.type != 'MESH' or 'liquid_surface' in obj:
            continue
        materials = obj.data.materials
        if len(materials) != slots:
            raise ValueError(f'{ident}/{obj.name}: expected the {slots}-slot palette, got {len(materials)}')
        for index, material in enumerate(materials):
            if index in NATIVE:
                if material.name != NATIVE[index]:
                    raise ValueError(f'{ident}: slot {index} is {material.name}, expected native {NATIVE[index]}')
            elif material.name not in renamed:
                entry = catalog[index]
                if entry['name'] != f'DFIndustrial{index:02d}':
                    raise ValueError('Industrial custom-tile catalog order changed')
                material.name = entry['name']
                renamed.add(material.name)
    for obj in collection.all_objects:
        if 'liquid_surface' in obj and [m.name for m in obj.data.materials] != ['Water']:
            raise ValueError(f'{ident}/{obj.name}: water surfaces must use the native Water material')
    # Native worker idle slots just inside each ground door.
    ground = [d for d in registration['doors'] if d['position'][2] == 0]
    if not ground:
        raise ValueError(f'{ident}: no ground door registered')
    for i, door in enumerate(ground):
        x, y, z = door['position']
        ox, oy = door['outward']
        empty = bpy.data.objects.new(f'#Slot#Entrance{i}', None)
        collection.objects.link(empty)
        empty.location = (-(x - ox * .12), -(y - oy * .12), z)
        empty.rotation_euler = (0, 0, math.atan2(-ox, oy))
    visitor_slots = VISITOR_SLOTS[ident](registration) if ident in VISITOR_SLOTS else []
    for i, ((x, y, z), (fx, fy)) in enumerate(visitor_slots):
        # Same frame as the door slots above.
        empty = bpy.data.objects.new(f'#Slot#{VISITOR_SLOT_KEYWORD}{i}', None)
        collection.objects.link(empty)
        empty.location = (-x, -y, z)
        empty.rotation_euler = (0, 0, math.atan2(-fx, fy))
    root = bpy.data.objects.new('LategameGridOrigin', None)
    collection.objects.link(root)
    for obj in list(collection.objects):
        if obj != root and obj.parent is None:
            obj.parent = root
        if obj.animation_data and obj.animation_data.action:
            if obj.name.startswith('#'):
                raise ValueError('Study parts must use unprefixed names')
            obj.name = '#' + obj.name
    if ident == 'GroceryStore':
        # Fill-stage nodes for GroceryStockDisplay.cs: static objects that the
        # exporter writes as their own nodes under their exact names.
        foods = json.loads((ROOT / 'tools/frontier_progression.json').read_text())['groceryStore']['stock']
        expected = sorted(f'GroceryStock.{f}.{n}' for f in foods for n in (1, 2, 3))
        stock = sorted(o.name for o in collection.all_objects if 'GroceryStock.' in o.name)
        if stock != expected:
            raise ValueError(f'{ident}: grocery stock nodes differ: {sorted(set(stock) ^ set(expected))}')
        if any(collection.all_objects[n].type != 'MESH' or collection.all_objects[n].animation_data for n in expected):
            raise ValueError(f'{ident}: grocery stock nodes must be static meshes')
    # Preview cost: each static part was its own node and MeshRenderer
    # (static_mesh_merge.py). Named, animated and glass parts stay separate.
    merge = static_mesh_merge.merge_static_meshes(collection, root, static_mesh_merge.referenced_names())
    settings = exporter.ExportSettings(bpy.context, False, True, False)
    base = OUT / (model_path(ident) + '.timbermesh')
    base.parent.mkdir(parents=True, exist_ok=True)
    exporter.Exporter.export_collection(collection, str(base), settings)
    stage = base.with_name(f'{ident}.IronTeeth.ConstructionStage0.Model.timbermesh')
    shutil.copyfile(base, stage)
    (OUT.parent / f'{ident}-static-merge.json').write_text(
        json.dumps({'ident': ident, 'model': model_path(ident), **merge}, indent=2) + '\n')
    if visitor_slots:
        record = OUT.parent / f'{ident}-visitor-slots.json'
        record.write_text(json.dumps({'ident': ident, 'model': model_path(ident), 'keyword': VISITOR_SLOT_KEYWORD,
                                      'count': len(visitor_slots), 'sourceHash': registration['sourceHash']}, indent=2) + '\n')
    print('LATEGAME EXPORTED', ident, base, f'visitor slots {len(visitor_slots)}', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', required=True)
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    for ident in cli.models.split(','):
        export_model(ident)


if __name__ == '__main__':
    main()
