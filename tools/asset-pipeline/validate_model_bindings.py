"""Check blueprint visual bindings against the actual authored Timbermesh nodes."""
import json
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src/DeepFrontier/Data"
VANILLA = ROOT / "vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources"
sys.path.insert(0, str(ROOT / "tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin"))
import model_pb2

# Native prop models are extracted preview assets. Their resource-to-file
# mapping is recorded by the producing assembly, never inferred from a miss.
native_models = {}
for manifest in (ROOT / "outputs/reference-studies").glob("*-native-assembly.json"):
    for prop in json.loads(manifest.read_text(encoding="utf-8"))["props"]:
        # Dependency-mod props (e.g. Redic.NewStyles) record the installed file.
        path = (Path(prop["sourceFile"]) if "dependency" in prop
                else ROOT / "outputs/native-civic-assets" / (prop["model"] + ".timbermesh"))
        if prop["resource"] in native_models and native_models[prop["resource"]] != path:
            raise ValueError("Conflicting native resource registration: " + prop["resource"])
        native_models[prop["resource"]] = path

materials = {"Common": set(), "IronTeeth": set()}
for material_root in (VANILLA, DATA):
    for path in (material_root / "MaterialCollections").glob("*.blueprint.json"):
        spec = json.loads(path.read_text(encoding="utf-8"))["MaterialCollectionSpec"]
        if spec["CollectionId"] in materials:
            materials[spec["CollectionId"]].update(Path(name).name for name in spec["Materials"])


# Vanilla model resources that a Deep Frontier placeholder blueprint reuses
# unchanged (e.g. the radiation buildings clone vanilla Discharge and
# DeepBadwaterPump until their art is authored). Only models a shipped
# vanilla blueprint itself binds qualify; anything else must exist in Data.
def _vanilla_models(blueprint, found):
    if "TimbermeshSpec" in blueprint:
        found.add(blueprint["TimbermeshSpec"]["Model"])
    for child in blueprint.get("Children", {}).values():
        _vanilla_models(child, found)
    return found


VANILLA_MODELS = set()
# Buildings and map-editor objects (the Human Record Cache reuses MediumRelic).
for _path in list((VANILLA / "Buildings").rglob("*.blueprint.json")) + list((VANILLA / "MapEditor").rglob("*.blueprint.json")):
    _vanilla_models(json.loads(_path.read_text(encoding="utf-8-sig")), VANILLA_MODELS)
vanilla_placeholders = set()


def model_nodes(blueprint, allowed_materials, native_nodes, native_resource=False):
    names = set()
    if "TimbermeshSpec" in blueprint:
        resource = blueprint["TimbermeshSpec"]["Model"]
        path = native_models[resource] if native_resource else DATA / (resource + ".timbermesh")
        if not native_resource and not path.exists() and resource in VANILLA_MODELS:
            vanilla_placeholders.add(resource)
            resource = None
        if resource is not None:
            model = model_pb2.Model()
            model.ParseFromString(zlib.decompress(path.read_bytes()))
            names.update(node.name for node in model.nodes)
            for node in model.nodes:
                for mesh in node.meshes:
                    material = mesh.material
                    if material not in allowed_materials:
                        raise ValueError(f"{path}: material {material} is not registered for this context")
    if "Children" in blueprint:
        for name, child in blueprint["Children"].items():
            names.add(name)
            names.update(model_nodes(child, allowed_materials, native_nodes, name in native_nodes))
    return names


# Particle attachments (TemplateAttachments, Timberborn 1.1): the prefab must
# be a shipped one, every controller may run only declared attachments (the
# game throws KeyNotFoundException otherwise), every attachment needs a
# controller, and a '#Finished' attachment must sit within the building's
# block volume (Position X across, Y up, Z depth), which catches template
# positions that survived onto a different model.
PARTICLE_CONTROLLERS = ("WorkshopParticleControllerSpec", "WindParticleControllerSpec",
                        "PowerGeneratorParticleControllerSpec", "EnterableParticleControllerSpec",
                        "BlockableObjectParticleControllerSpec", "MechanicalNodeParticlesControllerSpec")
RUNNING_CONTROLLERS = tuple(c for c in PARTICLE_CONTROLLERS if c != "WindParticleControllerSpec")
VANILLA_PREFABS = {attachment["Prefab"]
                   for path in VANILLA.rglob("*.blueprint.json")
                   for attachment in json.loads(path.read_text(encoding="utf-8-sig")).get("TemplateAttachmentsSpec", {}).get("Attachments", [])}


def particle_failures(blueprint):
    failures = []
    attachments = blueprint.get("TemplateAttachmentsSpec", {}).get("Attachments", [])
    declared = {a["AttachmentId"] for a in attachments}
    running = set()
    for spec_name in PARTICLE_CONTROLLERS:
        for attachment_id in blueprint.get(spec_name, {}).get("AttachmentIds", []):
            if attachment_id not in declared:
                failures.append(f"{spec_name} runs undeclared attachment {attachment_id}")
            if spec_name in RUNNING_CONTROLLERS:
                running.add(attachment_id)
    if "WorkshopParticleControllerSpec" in blueprint and "WorkshopSpec" not in blueprint:
        failures.append("workshop particles require a workshop")
    if "EnterableParticleControllerSpec" in blueprint and "EnterableSpec" not in blueprint:
        failures.append("enterable particles require an enterable")
    if "MechanicalNodeParticlesControllerSpec" in blueprint and not (blueprint.get("MechanicalNodeSpec", {}).get("PowerInput", 0) > 0):
        failures.append("mechanical-node particles require a powered building")
    if "PowerGeneratorParticleControllerSpec" in blueprint and not (blueprint.get("MechanicalNodeSpec", {}).get("PowerOutput", 0) > 0):
        failures.append("power-generator particles require a generator")
    size = blueprint.get("BlockObjectSpec", {}).get("Size")
    for a in attachments:
        if a["Prefab"] not in VANILLA_PREFABS and not a["Prefab"].startswith("Fireworks/"):
            failures.append(f"attachment {a['AttachmentId']} uses unknown prefab {a['Prefab']}")
        if a["AttachmentId"] not in running and a["AttachmentId"] != blueprint.get("FireSpec", {}).get("AttachmentId"):
            failures.append(f"attachment {a['AttachmentId']} is run by no particle controller")
        if a["Parent"] == "#Finished" and size:
            p = a["Position"]
            if not (0 <= p["X"] <= size["X"] and 0 <= p["Z"] <= size["Y"] and 0 <= p["Y"] <= size["Z"] + .5):
                failures.append(f"attachment {a['AttachmentId']} at {p} lies outside the {size} block volume")
    return failures


def references(blueprint):
    refs = []
    if "ManufactoryProgressVisualizerSpec" in blueprint:
        for step in blueprint["ManufactoryProgressVisualizerSpec"]["ProgressSteps"]:
            refs.extend(step["ModelNames"])
    if "ManufactoryRecipeVisualizerSpec" in blueprint:
        spec = blueprint["ManufactoryRecipeVisualizerSpec"]
        refs.append(spec["InitialModelName"])
        refs.extend(recipe["ModelName"] for recipe in spec["RecipeModels"])
    if "TemplateAttachmentsSpec" in blueprint:
        refs.extend(attachment["Parent"] for attachment in blueprint["TemplateAttachmentsSpec"]["Attachments"])
    for spec_name in ("BuildingModelSpec", "BlockObjectModelSpec"):
        if spec_name in blueprint:
            refs.extend(value for key, value in blueprint[spec_name].items() if key.endswith("ModelName") and value)
    return refs


# Optional: check generated candidate blueprints (JSON files holding one
# blueprint or an {id: blueprint} map) against the particle rules only.
if len(sys.argv) > 1:
    candidate_failures = []
    for name in sys.argv[1:]:
        loaded = json.loads(Path(name).read_text(encoding="utf-8"))
        candidates = {name: loaded} if "TemplateSpec" in loaded or "BlockObjectSpec" in loaded else loaded
        for ident, blueprint in candidates.items():
            candidate_failures.extend(f"{ident}: {f}" for f in particle_failures(blueprint))
    if candidate_failures:
        raise SystemExit("\n".join(candidate_failures))
    print(json.dumps({"status": "candidate-particles-checked", "files": len(sys.argv) - 1}))
    raise SystemExit(0)

checked = 0
failures = []
for folder in (DATA / "Buildings", DATA / "MapEditor/Objects"):
    for path in folder.rglob("*.blueprint.json"):
        blueprint = json.loads(path.read_text(encoding="utf-8"))
        if "ManufactorySpec" in blueprint and "GoodConsumingBuildingSpec" in blueprint:
            failures.append(f"{path.relative_to(DATA)}: Manufactory and GoodConsumingBuilding both implement IGoodProcessor")
        if "WorkshopPoweredGeneratorSpec" in blueprint:
            for required in ("WorkshopSpec", "ManufactorySpec", "MechanicalNodeSpec", "SimpleManufactoryBehaviorsSpec"):
                if required not in blueprint:
                    failures.append(f"{path.relative_to(DATA)}: workshop generator requires {required}")
        failures.extend(f"{path.relative_to(DATA)}: {f}" for f in particle_failures(blueprint))
        if "WorkshopWorkerHiderSpec" in blueprint and "WorkplaceSlotManagerSpec" not in blueprint:
            failures.append(f"{path.relative_to(DATA)}: worker hider requires a workplace slot manager")
        if "ConstructionSiteProgressVisualizerSpec" in blueprint:
            unfinished = blueprint["BuildingModelSpec"]["UnfinishedModelName"]
            stages = blueprint["Children"][unfinished]["Children"]
            thresholds = blueprint["ConstructionSiteProgressVisualizerSpec"]["ProgressThresholds"]
            if len(thresholds) != len(stages) - 1:
                failures.append(f"{path.relative_to(DATA)}: {len(thresholds)} construction thresholds for {len(stages)} stages; must equal stages minus base")
        allowed_materials = materials["Common"] if "MapEditor" in path.parts else materials["Common"] | materials["IronTeeth"]
        native_nodes = {p["Node"] for p in blueprint["NativeBuildingPropsSpec"]["Props"]} if "NativeBuildingPropsSpec" in blueprint else set()
        names = model_nodes(blueprint, allowed_materials, native_nodes)
        for name in references(blueprint):
            if name not in names:
                failures.append(f"{path.relative_to(DATA)}: absent model node {name}")
        checked += 1
if failures:
    raise SystemExit("\n".join(failures))
print(json.dumps({"status": "model-bindings-checked", "templates": checked,
                  "vanillaPlaceholderModels": sorted(vanilla_placeholders)}))
