import os
import sys

import bpy


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SOURCE_ROOT = os.path.join(ROOT, "src", "DeepFrontier")
BLEND_PATH = os.path.join(SOURCE_ROOT, "Art", "Source", "DeepFrontierModels.blend")
PLUGIN_ROOT = os.path.join(ROOT, "tools", "asset-pipeline", "timbermesh-plugin")
PLUGIN_PACKAGE = os.path.join(PLUGIN_ROOT, "timbermesh_blender_plugin")
sys.path.insert(0, PLUGIN_ROOT)
sys.path.insert(0, PLUGIN_PACKAGE)

from timbermesh_blender_plugin import timbermesh_exporter


EXPORTS = {
    "DeepDrill.IronTeeth.Model": "Data/Buildings/Metal/DeepDrill/DeepDrill.IronTeeth.Model.timbermesh",
    "DeepDrill.IronTeeth.ConstructionStage0.Model": "Data/Buildings/Metal/DeepDrill/DeepDrill.IronTeeth.ConstructionStage0.Model.timbermesh",
    "DeepDrill.IronTeeth.Underground": "Data/Buildings/Metal/DeepDrill/DeepDrill.IronTeeth.Underground.timbermesh",
    "DeepMine.IronTeeth.Model": "Data/Buildings/Metal/DeepMine/DeepMine.IronTeeth.Model.timbermesh",
    "DeepMine.IronTeeth.ConstructionStage0.Model": "Data/Buildings/Metal/DeepMine/DeepMine.IronTeeth.ConstructionStage0.Model.timbermesh",
    "DeepMine.IronTeeth.Underground": "Data/Buildings/Metal/DeepMine/DeepMine.IronTeeth.Underground.timbermesh",
    "DeepProcessor.IronTeeth.Model": "Data/Buildings/Metal/DeepProcessor/DeepProcessor.IronTeeth.Model.timbermesh",
    "DeepProcessor.IronTeeth.ConstructionStage0.Model": "Data/Buildings/Metal/DeepProcessor/DeepProcessor.IronTeeth.ConstructionStage0.Model.timbermesh",
}

# Every expansion building has its own authored finished and construction
# collection. Keep the export paths in the same namespace as the blueprints so
# a model can be swapped without changing the data schema.
EXPANSION_BUILDINGS = {
    "FertilizerWorks": "Data/Buildings/Food/FertilizerWorks",
    "FoodPackagingWorks": "Data/Buildings/Food/FoodPackagingWorks",
    "PublicHealthLab": "Data/Buildings/Wellbeing/PublicHealthLab",
    "Greenhouse": "Data/Buildings/Food/Greenhouse",
    "ChemicalWorks": "Data/Buildings/Metal/ChemicalWorks",
    "PrecisionMachineWorks": "Data/Buildings/Metal/PrecisionMachineWorks",
    "WaterTreatmentPlant": "Data/Buildings/Water/WaterTreatmentPlant",
    "TechnicalSchool": "Data/Buildings/Science/TechnicalSchool",
    "UraniumProcessingPlant": "Data/Buildings/Metal/UraniumProcessingPlant",
    "RadioactiveWasteRefinery": "Data/Buildings/Metal/RadioactiveWasteRefinery",
    "ElectrolysisPlant": "Data/Buildings/Metal/ElectrolysisPlant",
    "RocketAssemblyHangar": "Data/Buildings/Metal/RocketAssemblyHangar",
    "MissionControl": "Data/Buildings/Science/MissionControl",
    "LaunchPad": "Data/Buildings/Metal/LaunchPad",
    "RadioactiveWasteVault": "Data/Buildings/Storage/RadioactiveWasteVault",
}

# Late-game studies own these models once integrated; never overwrite them.
import json as _json
_INTEGRATED = set(_json.loads(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lategame_batches.json"), encoding="utf-8").read())["integrated"])

for collection_name in list(EXPORTS):
    if collection_name.split(".")[0] in _INTEGRATED:
        del EXPORTS[collection_name]

for building_id, output_dir in EXPANSION_BUILDINGS.items():
    if building_id in _INTEGRATED:
        continue
    EXPORTS[f"{building_id}.IronTeeth.Model"] = f"{output_dir}/{building_id}.IronTeeth.Model.timbermesh"
    EXPORTS[f"{building_id}.IronTeeth.ConstructionStage0.Model"] = f"{output_dir}/{building_id}.IronTeeth.ConstructionStage0.Model.timbermesh"


def main():
    bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)
    # Keep object nodes separate so the official exporter can serialize the
    # authored drum, fan, pump, and status-ring animations. Construction meshes
    # remain static because their collections have no keyed objects.
    settings = timbermesh_exporter.ExportSettings(bpy.context, False, True, False)
    for collection_name, relative_path in EXPORTS.items():
        collection = bpy.data.collections.get(collection_name)
        if collection is None:
            raise RuntimeError(f"Missing collection: {collection_name}")
        path = os.path.join(SOURCE_ROOT, relative_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        timbermesh_exporter.Exporter.export_collection(collection, path, settings)
        print(f"Exported {collection_name} -> {path}")


if __name__ == "__main__":
    main()
