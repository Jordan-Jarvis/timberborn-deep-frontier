"""Generate Deep Frontier source art and exportable Blender collections.

Run with Blender in background mode.  The scene intentionally uses new geometry
for every Deep Frontier model; no vanilla building mesh is imported or reused.
The Timbermesh exporter serializes material names, so the mesh uses the Iron
Teeth material names that the game already resolves while the PNGs provide the
mod's authored icon and texture source artwork for the custom material pass.
"""

import math
import os
import sys
import argparse

import bpy
from mathutils import Vector


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ART_ROOT = os.path.join(ROOT, "src", "DeepFrontier", "Art")
SOURCE_ROOT = os.path.join(ART_ROOT, "Source")
TEXTURE_ROOT = os.path.join(ART_ROOT, "Textures")
ICON_ROOT = os.path.join(ROOT, "src", "DeepFrontier", "Data")
PLUGIN_ROOT = os.path.join(ROOT, "tools", "asset-pipeline", "timbermesh-plugin")
sys.path.insert(0,os.path.dirname(__file__))
from prototype_native_uv import author_primitive_uv


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)
    root = bpy.context.scene.collection
    for collection in list(root.children):
        root.children.unlink(collection)


def material(name, color, metallic=0.0, roughness=0.65):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


# Use distinct materials that already exist in the Iron Teeth material
# collection. Keeping the names game-resolved avoids a custom shader dependency
# while preserving separate teal, orange, metal, wood, and stone surfaces.
METAL = material("BaseMetal.IronTeeth", (0.16, 0.18, 0.20), 0.85, 0.32)
PAINT = material("PaintedMetal.IronTeeth", (0.10, 0.24, 0.30), 0.65, 0.40)
WOOD = material("BaseWood_DarkBrown.IronTeeth", (0.20, 0.11, 0.06), 0.0, 0.78)
GLOW = material("Plaster_Orange.IronTeeth", (0.88, 0.30, 0.05), 0.35, 0.28)
ROCK = material("Plaster_White.IronTeeth", (0.07, 0.09, 0.10), 0.1, 0.95)


def link(obj, collection):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def cube(collection, name, location, scale, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (scale[0] / 2, scale[1] / 2, scale[2] / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("EdgeBevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.data.materials.append(mat)
    author_primitive_uv(obj,mat.name)
    return link(obj, collection)


def cylinder(collection, name, location, radius, depth, mat, rotation=(0, 0, 0), vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    author_primitive_uv(obj,mat.name)
    return link(obj, collection)


def torus(collection, name, location, major, minor, mat, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=16, minor_segments=6, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    author_primitive_uv(obj,mat.name)
    return link(obj, collection)


def ico(collection, name, location, scale, mat):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    author_primitive_uv(obj,mat.name)
    return link(obj, collection)


def new_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def drill_model(collection, deep=False):
    # 5x5 footprint: frame, cutter housing, drum, and a visible extraction throat.
    cube(collection, "Foundation", (2.5, 0.25, 2.5), (5.0, 0.5, 5.0), WOOD, 0.10)
    cube(collection, "DriveHousing", (2.5, 1.55, 2.5), (3.6, 2.0, 2.6), PAINT, 0.12)
    cube(collection, "RearCounterweight", (2.5, 2.2, 4.1), (2.4, 1.0, 1.2), METAL, 0.08)
    cylinder(collection, "DriveDrum", (2.5, 2.0, 1.05), 1.1, 0.65, METAL, rotation=(math.pi / 2, 0, 0))
    torus(collection, "DriveRing", (2.5, 2.0, 1.0), 0.86, 0.13, GLOW, rotation=(math.pi / 2, 0, 0))
    for x in (0.55, 4.45):
        cylinder(collection, f"FramePost{x}", (x, 2.4, 3.7), 0.16, 3.4, METAL)
        cylinder(collection, f"FramePost{x}Rear", (x, 2.4, 1.0), 0.16, 1.5, METAL)
    cylinder(collection, "BoreShaft", (2.5, 0.20, 2.5), 0.7, 0.45, GLOW)
    if deep:
        torus(collection, "DeepRing", (2.5, 2.0, 1.0), 0.60, 0.07, GLOW, rotation=(math.pi / 2, 0, 0))


def processor_model(collection):
    cube(collection, "Foundation", (1.0, 0.25, 2.0), (2.0, 0.5, 4.0), WOOD, 0.08)
    cube(collection, "Furnace", (1.0, 1.4, 2.0), (1.55, 2.0, 3.2), PAINT, 0.12)
    cube(collection, "Hopper", (1.0, 2.5, 2.0), (1.2, 0.8, 2.2), METAL, 0.08)
    cylinder(collection, "FurnaceDrum", (1.0, 1.5, 0.55), 0.42, 1.0, GLOW, rotation=(math.pi / 2, 0, 0))
    for x in (0.35, 1.65):
        cylinder(collection, f"Support{x}", (x, 1.1, 3.1), 0.10, 1.4, METAL)
    torus(collection, "FrontWheel", (1.0, 1.65, 2.0), 0.58, 0.09, METAL, rotation=(math.pi / 2, 0, 0))


def animate_spin(obj, axis=2, turns=1.0, start=1, end=61):
    """Add a compact looping node animation understood by Timbermesh."""
    if obj is None:
        return
    obj.rotation_mode = "XYZ"
    start_rotation = obj.rotation_euler.copy()
    obj.keyframe_insert(data_path="rotation_euler", frame=start, index=-1)
    finish_rotation = start_rotation.copy()
    finish_rotation[axis] += math.tau * turns
    obj.rotation_euler = finish_rotation
    obj.keyframe_insert(data_path="rotation_euler", frame=end, index=-1)
    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = "LINEAR"


def animate_bob(obj, axis=1, amount=0.10, start=1, mid=31, end=61):
    if obj is None:
        return
    base = obj.location.copy()
    obj.keyframe_insert(data_path="location", frame=start, index=-1)
    raised = base.copy()
    raised[axis] += amount
    obj.location = raised
    obj.keyframe_insert(data_path="location", frame=mid, index=-1)
    obj.location = base
    obj.keyframe_insert(data_path="location", frame=end, index=-1)
    if obj.animation_data and obj.animation_data.action:
        for fcurve in obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = "SINE"


def animate_collection(collection, kind=None):
    """Give each machine a restrained readable motion cue.

    The exporter serializes these as node animations in the single Default
    clip. Construction collections intentionally never call this function.
    """
    for obj in collection.objects:
        name = obj.name
        if name.startswith(("DriveDrum", "DriveRing", "FurnaceDrum", "FrontWheel", "WaterDrum", "ProcessVessel", "StatusRing", "RocketCore", "RocketRing", "Drum")):
            animate_spin(obj, axis=2, turns=1.0)
        elif name.startswith(("Vent", "Pipe", "ServiceLamp")):
            animate_bob(obj, amount=0.05)
        elif name.startswith("ControlPanel"):
            animate_spin(obj, axis=1, turns=0.25)


def vein_model(collection):
    cube(collection, "VeinBase", (1.5, 0.15, 1.5), (3.0, 0.3, 3.0), ROCK, 0.06)
    for i, location in enumerate(((0.75, 0.55, 0.75), (2.10, 0.55, 0.80), (1.10, 0.65, 2.00), (2.25, 0.48, 2.10), (1.45, 0.80, 1.35))):
        ico(collection, f"OreShard{i}", location, (0.45, 0.35, 0.45), GLOW if i % 2 == 0 else ROCK)


def expansion_factory_model(collection, kind, footprint=(3.0, 3.0), height=3.0):
    """Create a compact, low-poly Iron Teeth factory silhouette.

    The pieces deliberately reuse the same authored palette as the first
    Deep Frontier machines: dark timber foundations, teal painted housings,
    matte metal drums, and one orange status/heat accent. The collection name
    identifies the machine; no vanilla mesh is imported.
    """
    width, depth = footprint
    cube(collection, "Foundation", (width / 2, 0.22, depth / 2), (width, 0.44, depth), WOOD, 0.08)
    body_height = max(1.2, height - 0.75)
    cube(collection, "Housing", (width / 2, 0.55 + body_height / 2, depth / 2), (width - 0.35, body_height, depth - 0.35), PAINT, 0.10)
    cube(collection, "TopRail", (width / 2, height - 0.25, depth / 2), (width - 0.6, 0.18, depth - 0.6), METAL, 0.04)
    for x in (0.32, width - 0.32):
        cylinder(collection, f"CornerPost{x}", (x, height / 2, 0.32), 0.08, height - 0.45, METAL)
    for x in (0.32, width - 0.32):
        cylinder(collection, f"RearPost{x}", (x, height / 2, depth - 0.32), 0.08, height - 0.45, METAL)

    if kind in ("fish", "fertilizer", "greenhouse", "food", "fishery"):
        for x in (width * 0.32, width * 0.68):
            cube(collection, f"Tray{x}", (x, max(0.75, height - 0.42), depth / 2), (0.62, 0.16, depth - 0.9), GLOW, 0.04)
        cylinder(collection, "WaterDrum", (width * 0.18, 1.35, depth + 0.12), 0.34, 0.95, METAL, rotation=(math.pi / 2, 0, 0))
        torus(collection, "WaterDrumRing", (width * 0.18, 1.35, depth + 0.62), 0.28, 0.06, GLOW)
        if kind in ("fish", "fishery"):
            cube(collection, "TankWindow", (width * 0.66, 1.25, depth + 0.14), (0.72, 0.48, 0.12), GLOW, 0.04)
        if kind == "greenhouse":
            for x in (width * 0.28, width * 0.50, width * 0.72):
                cube(collection, f"RoofGlass{x}", (x, height + 0.08, depth / 2), (0.12, 0.10, depth - 0.6), GLOW, 0.02)
    elif kind in ("reactor", "uranium", "waste", "chemical", "cryo"):
        cylinder(collection, "ProcessVessel", (width / 2, 1.55, depth + 0.16), min(width, depth) * 0.27, 1.85, METAL, rotation=(math.pi / 2, 0, 0))
        torus(collection, "StatusRing", (width / 2, 1.55, depth + 0.25), min(width, depth) * 0.24, 0.09, GLOW)
        cylinder(collection, "Vent", (width / 2, height + 0.2, depth / 2), 0.14, 0.5, ROCK)
        for z in (0.72, depth - 0.72):
            cylinder(collection, f"Pipe{z}", (width * 0.25, 1.2, depth + 0.08), 0.08, width * 0.65, GLOW, rotation=(0, math.pi / 2, 0))
        if kind in ("reactor", "uranium"):
            cube(collection, "ControlPanel", (width * 0.18, 1.1, depth + 0.18), (0.28, 0.52, 0.12), GLOW, 0.03)
    elif kind in ("rocket", "launch", "mission"):
        for x in (0.55, width - 0.55):
            for z in (0.55, depth - 0.55):
                cylinder(collection, f"Frame{x}{z}", (x, height / 2, z), 0.10, height - 0.3, METAL)
        cylinder(collection, "RocketCore", (width / 2, height + 0.85, depth / 2), 0.42, 1.7, GLOW, rotation=(math.pi / 2, 0, 0))
        torus(collection, "RocketRing", (width / 2, height - 0.70, depth + 0.16), 0.58, 0.08, METAL)
    elif kind in ("school", "health", "grocery", "restaurant"):
        cube(collection, "ServiceCounter", (width / 2, 1.0, depth + 0.10), (width - 0.8, 0.65, 0.24), WOOD, 0.05)
        for x in (width * 0.3, width * 0.7):
            cylinder(collection, f"ServiceLamp{x}", (x, height - 0.35, depth + 0.16), 0.09, 0.45, GLOW)
    else:
        for x in (width * 0.28, width * 0.72):
            cylinder(collection, f"Drum{x}", (x, 1.35, depth + 0.12), 0.35, 1.1, METAL, rotation=(math.pi / 2, 0, 0))
        cube(collection, "ControlPanel", (width / 2, 1.45, depth + 0.18), (0.6, 0.55, 0.16), GLOW, 0.03)


def expansion_construction_model(collection, footprint=(3.0, 3.0), height=3.0):
    width, depth = footprint
    cube(collection, "ConstructionBase", (width / 2, 0.22, depth / 2), (width, 0.44, depth), WOOD, 0.08)
    for x in (0.35, width - 0.35):
        cylinder(collection, f"ConstructionFrame{x}", (x, max(0.7, height * 0.45), depth / 2), 0.12, max(0.8, height * 0.75), WOOD)
    cube(collection, "ConstructionCrossbar", (width / 2, max(0.9, height * 0.65), depth / 2), (width - 0.7, 0.14, 0.14), WOOD, 0.03)


def make_texture(path, base, accent, diagonal=False):
    image = bpy.data.images.new(os.path.basename(path), width=128, height=128)
    pixels = []
    for y in range(128):
        for x in range(128):
            stripe = ((x + y) // 16) % 2 if diagonal else (x // 16) % 2
            c = accent if stripe else base
            noise = ((x * 17 + y * 31) % 9) / 255.0
            pixels.extend((min(1, c[0] + noise), min(1, c[1] + noise), min(1, c[2] + noise), 1.0))
    image.pixels = pixels
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()


def save_scene():
    ensure_dir(SOURCE_ROOT)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SOURCE_ROOT, "DeepFrontierModels.blend"))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--geometry-only',action='store_true',help='Rebuild owned source geometry without rewriting raster textures')
    cli=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    clear_scene()
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 61
    bpy.context.scene.render.fps = 30
    ensure_dir(SOURCE_ROOT)
    ensure_dir(TEXTURE_ROOT)
    for path in [
        os.path.join(ICON_ROOT, "Buildings", "Metal", "DeepDrill"),
        os.path.join(ICON_ROOT, "Buildings", "Metal", "DeepMine"),
        os.path.join(ICON_ROOT, "Buildings", "Metal", "DeepProcessor"),
        os.path.join(ICON_ROOT, "MapEditor", "Objects", "DeepOreVein"),
        os.path.join(ICON_ROOT, "MapEditor", "Objects", "DeepOreSource"),
        os.path.join(ICON_ROOT, "Sprites", "Goods"),
    ]:
        ensure_dir(path)

    collections = {
        "DeepDrill.IronTeeth.Model": new_collection("DeepDrill.IronTeeth.Model"),
        "DeepDrill.IronTeeth.ConstructionStage0.Model": new_collection("DeepDrill.IronTeeth.ConstructionStage0.Model"),
        "DeepDrill.IronTeeth.Underground": new_collection("DeepDrill.IronTeeth.Underground"),
        "DeepMine.IronTeeth.Model": new_collection("DeepMine.IronTeeth.Model"),
        "DeepMine.IronTeeth.ConstructionStage0.Model": new_collection("DeepMine.IronTeeth.ConstructionStage0.Model"),
        "DeepMine.IronTeeth.Underground": new_collection("DeepMine.IronTeeth.Underground"),
        "DeepProcessor.IronTeeth.Model": new_collection("DeepProcessor.IronTeeth.Model"),
        "DeepProcessor.IronTeeth.ConstructionStage0.Model": new_collection("DeepProcessor.IronTeeth.ConstructionStage0.Model"),
        "DeepOreVein.Model": new_collection("DeepOreVein.Model"),
    }
    drill_model(collections["DeepDrill.IronTeeth.Model"])
    cube(collections["DeepDrill.IronTeeth.ConstructionStage0.Model"], "ConstructionBase", (2.5, 0.25, 2.5), (5, 0.5, 5), WOOD, 0.1)
    cube(collections["DeepDrill.IronTeeth.ConstructionStage0.Model"], "ConstructionFrame", (2.5, 1.0, 2.5), (3.0, 1.0, 2.5), WOOD, 0.1)
    cube(collections["DeepDrill.IronTeeth.Underground"], "UndergroundShaft", (2.5, -0.2, 2.5), (2.6, 0.4, 2.6), ROCK, 0.05)
    drill_model(collections["DeepMine.IronTeeth.Model"], deep=True)
    cube(collections["DeepMine.IronTeeth.ConstructionStage0.Model"], "ConstructionBase", (2.5, 0.25, 2.5), (5, 0.5, 5), WOOD, 0.1)
    cube(collections["DeepMine.IronTeeth.ConstructionStage0.Model"], "ConstructionFrame", (2.5, 1.1, 2.5), (4.0, 1.6, 3.0), WOOD, 0.1)
    cube(collections["DeepMine.IronTeeth.Underground"], "UndergroundShaft", (2.5, -0.2, 2.5), (3.0, 0.4, 3.0), ROCK, 0.05)
    processor_model(collections["DeepProcessor.IronTeeth.Model"])
    cube(collections["DeepProcessor.IronTeeth.ConstructionStage0.Model"], "ConstructionBase", (1.0, 0.25, 2.0), (2, 0.5, 4), WOOD, 0.08)
    cube(collections["DeepProcessor.IronTeeth.ConstructionStage0.Model"], "ConstructionFrame", (1.0, 0.9, 2.0), (1.6, 1.0, 3.0), WOOD, 0.08)
    vein_model(collections["DeepOreVein.Model"])
    animate_collection(collections["DeepDrill.IronTeeth.Model"])
    animate_collection(collections["DeepMine.IronTeeth.Model"])
    animate_collection(collections["DeepProcessor.IronTeeth.Model"])

    # Expansion machines use the same authored low-poly language as the
    # vertical slice. The dimensions mirror the compact prototype blueprints;
    # balancing can change a footprint without changing the art generator API.
    expansion_models = {
        "FertilizerWorks.IronTeeth": ("fertilizer", (2.0, 2.0), 3.0),
        "FoodPackagingWorks.IronTeeth": ("food", (3.0, 3.0), 3.0),
        "PublicHealthLab.IronTeeth": ("health", (2.0, 2.0), 3.0),
        "Greenhouse.IronTeeth": ("greenhouse", (3.0, 3.0), 1.0),
        "ChemicalWorks.IronTeeth": ("chemical", (3.0, 3.0), 3.0),
        "PrecisionMachineWorks.IronTeeth": ("precision", (3.0, 3.0), 2.0),
        "WaterTreatmentPlant.IronTeeth": ("water", (3.0, 3.0), 3.0),
        "TechnicalSchool.IronTeeth": ("school", (2.0, 2.0), 3.0),
        "UraniumProcessingPlant.IronTeeth": ("uranium", (3.0, 3.0), 3.0),
        "RadioactiveWasteRefinery.IronTeeth": ("waste", (3.0, 3.0), 3.0),
        "ElectrolysisPlant.IronTeeth": ("chemical", (3.0, 3.0), 3.0),
        "RocketAssemblyHangar.IronTeeth": ("rocket", (3.0, 3.0), 3.0),
        "MissionControl.IronTeeth": ("mission", (2.0, 2.0), 3.0),
        "LaunchPad.IronTeeth": ("launch", (3.0, 3.0), 3.0),
        "RadioactiveWasteVault.IronTeeth": ("vault", (3.0, 3.0), 2.0),
    }
    for name, (kind, footprint, height) in expansion_models.items():
        model_collection = new_collection(f"{name}.Model")
        construction_collection = new_collection(f"{name}.ConstructionStage0.Model")
        expansion_factory_model(model_collection, kind, footprint, height)
        expansion_construction_model(construction_collection, footprint, height)
        animate_collection(model_collection, kind)

    if cli.geometry_only:
        save_scene()
        return
    make_texture(os.path.join(TEXTURE_ROOT, "DeepFrontierMetal.png"), (0.10, 0.15, 0.18), (0.24, 0.38, 0.42))
    make_texture(os.path.join(TEXTURE_ROOT, "DeepFrontierOre.png"), (0.07, 0.08, 0.09), (0.80, 0.22, 0.04), diagonal=True)
    make_texture(os.path.join(TEXTURE_ROOT, "DeepFrontierHazard.png"), (0.08, 0.11, 0.12), (0.92, 0.36, 0.03), diagonal=True)
    # UI icons (DeepDrill/DeepMine/DeepProcessor, DeepOre/DeepAlloy, deep-ore map objects)
    # are authored SVGs rendered by tools/create_frontier_expansion_icons.mjs.
    save_scene()


if __name__ == "__main__":
    main()
