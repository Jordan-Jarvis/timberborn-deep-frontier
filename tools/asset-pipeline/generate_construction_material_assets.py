"""Author original mineral industry meshes, UVs and animation (UI icons are authored SVGs; see tools/native_icon_style.mjs).

Blender source uses Z-up and negative X/Y, as required by the official
exporter's (-x, z, -y) conversion. No post-export axis repair is applied.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/DeepFrontier"
DATA = SOURCE / "Data"
CATALOG = json.loads((ROOT / "tools/construction_materials.json").read_text())
PLUGIN = ROOT / "tools/asset-pipeline/timbermesh-plugin"
sys.path[:0] = [str(PLUGIN), str(PLUGIN / "timbermesh_blender_plugin")]
from timbermesh_blender_plugin import timbermesh_exporter

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
scene = bpy.context.scene
scene.frame_start, scene.frame_end, scene.render.fps = 1, 61, 30

def material(name, color, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    shader = mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = 0.7
    return mat

WOOD = material("BaseWood_DarkBrown.IronTeeth", (0.30, 0.16, 0.075))
METAL = material("BaseMetal.IronTeeth", (0.24, 0.25, 0.25), 0.5)
PAINT = material("PaintedMetal.IronTeeth", (0.16, 0.28, 0.29), 0.2)
SAND = material("Plaster_Orange.IronTeeth", (0.68, 0.43, 0.22))
LIME = material("Plaster_White.IronTeeth", (0.72, 0.71, 0.62))

def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c

def finish(c, name, mat):
    obj = bpy.context.object
    obj.name = name
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    c.objects.link(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=0.03)
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj

def box(c, name, pos, size, mat):
    x, y, z = pos
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-x, -y, z))
    bpy.context.object.scale = size
    return finish(c, name, mat)

def cylinder(c, name, pos, radius, length, mat, rotation=(0, 0, 0)):
    x, y, z = pos
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=length,
        location=(-x, -y, z), rotation=rotation)
    return finish(c, name, mat)

def rock(c, name, pos, scale, mat):
    x, y, z = pos
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1, location=(-x, -y, z))
    bpy.context.object.scale = scale
    return finish(c, name, mat)

def spin(obj):
    initial = obj.rotation_euler.to_quaternion()
    obj.rotation_mode = 'QUATERNION'
    for frame in range(1,62):
        obj.rotation_quaternion = initial @ Quaternion((0,0,1), 2*math.pi*(frame-1)/60)
        obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    obj.rotation_quaternion = initial
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"

exports = []
icons = []
for b in CATALOG["buildings"]:
    ident, kind = b["id"], b["kind"]
    if kind in ("crusher","kiln","quarry","mixer"):
        # Reviewed reference scenes own these models and icons. This prototype
        # generator must never replace them with primitive geometry.
        folder=DATA/"Buildings"/"Metal"/ident
        for filename in (ident+".IronTeeth.Model.timbermesh",
                         ident+".IronTeeth.ConstructionStage0.Model.timbermesh","Icon.png"):
            if not (folder/filename).is_file():
                raise FileNotFoundError("Build the reviewed reference asset first: "+str(folder/filename))
        continue
    w, d, h = b["size"]
    stone = SAND if b["good"] in ("Sandstone", "Aggregate") else LIME
    c = collection(ident + ".IronTeeth.Model")
    box(c, "TimberFoundation", (w/2, d/2, 0.15), (w, d, 0.3), WOOD)
    for x in (0.15, w-0.15):
        for y in (0.15, d-0.15):
            box(c, "IronCorner", (x, y, 0.25), (0.25, 0.25, 0.5), METAL)
    if kind == "pit":
        box(c, "SortingBench", (w/2, d*0.65, 0.65), (1.6, 0.65, 0.35), WOOD)
        for i in range(4):
            rock(c, "StoneSample", (0.45+i*0.34, d*0.65, 0.94), (0.22, 0.23, 0.2), stone)
        for x in (0.2, w-0.2):
            box(c, "GantryPost", (x, d*0.65, 1), (0.16, 0.16, 1.7), WOOD)
        box(c, "GantryBeam", (w/2, d*0.65, 1.8), (w, 0.24, 0.24), WOOD)
        moving = cylinder(c, "HoistWheel", (w/2, d*0.65, 1.52), 0.26, 0.15, METAL, (math.pi/2, 0, 0))
        spin(moving)
    elif kind == "quarry":
        box(c, "ShaftRim", (w/2, d/2, 0.5), (3.3, 3.3, 0.4), METAL)
        box(c, "ShaftOpening", (w/2, d/2, 0.72), (2.6, 2.6, 0.1), PAINT)
        for x in (1, 4):
            box(c, "Headframe", (x, 2.8, 1.95), (0.3, 0.4, 3.4), WOOD)
        box(c, "HeadframeCrossbeam", (2.5, 2.8, 3.6), (3.5, 0.5, 0.35), METAL)
        box(c, "DriveHousing", (1.05, 0.8, 1.1), (1.5, 1.1, 1.4), PAINT)
        cylinder(c, "ExtractionPipe", (4.2, 3.8, 1.4), 0.18, 2.4, METAL)
        moving = cylinder(c, "WindingDrum", (2.5, 2.8, 3), 0.55, 1, METAL, (math.pi/2, 0, 0))
        spin(moving)
        for i in range(5):
            rock(c, "OreBin", (3.2+i*0.2, 0.6, 0.6), (0.3, 0.35, 0.25), stone)
    elif kind == "crusher":
        box(c, "CrusherHousing", (1.5, 1.65, 0.9), (2.2, 1.7, 1.1), PAINT)
        for y in (1.2, 2.0):
            moving = cylinder(c, "CrushingRoller", (1.5, y, 1.5), 0.35, 1.7, METAL, (0, math.pi/2, 0))
            spin(moving)
        box(c, "OutputTray", (1.5, 0.35, 0.55), (1.8, 0.65, 0.15), WOOD)
        for i in range(6):
            rock(c, "Aggregate", (0.8+i*0.28, 0.4, 0.72), (0.15, 0.2, 0.14), SAND)
    elif kind == "kiln":
        for y in (1, 3):
            box(c, "KilnSupport", (1.5, y, 0.7), (2.3, 0.4, 0.9), WOOD)
        moving = cylinder(c, "RotaryKiln", (1.5, 2, 1.5), 0.76, 2.8, METAL, (math.pi/2, 0, 0))
        spin(moving)
        for y in (0.8, 3.2):
            cylinder(c, "KilnCollar", (1.5, y, 1.5), 0.81, 0.18, PAINT, (math.pi/2, 0, 0))
        cylinder(c, "Exhaust", (2.6, 3.4, 1.7), 0.22, 2.5, METAL)
        box(c, "FuelHopper", (0.5, 3.2, 0.9), (0.7, 0.9, 0.9), WOOD)
    elif kind == "mixer":
        for x in (0.5, 2.5):
            box(c, "MixerFrame", (x, 1.5, 1), (0.25, 1.6, 1.6), WOOD)
        moving = cylinder(c, "MixingDrum", (1.5, 1.5, 1.6), 0.85, 1.3, PAINT, (math.pi/2, 0, 0))
        spin(moving)
        for angle in range(0, 360, 60):
            a = math.radians(angle)
            rib = box(c, "DrumRib", (1.5+math.cos(a)*0.86, 1.5, 1.6+math.sin(a)*0.86), (0.09, 1.35, 0.09), METAL)
            matrix = rib.matrix_world.copy()
            rib.parent = moving
            rib.matrix_world = matrix
        cylinder(c, "WaterFeed", (2.6, 2.5, 1.4), 0.12, 2.3, METAL)
        box(c, "DischargeChute", (1.5, 0.4, 0.7), (1.2, 0.8, 0.15), METAL)
    else:
        raise ValueError(kind)
    path = DATA / f"Buildings/Metal/{ident}"
    exports.append((c, path / f"{ident}.IronTeeth.Model.timbermesh"))
    # Native-style SVG icons are owned by tools/create_construction_icons.mjs.
    unfinished = collection(ident + ".IronTeeth.ConstructionStage0.Model")
    box(unfinished, "Foundation", (w/2, d/2, 0.15), (w, d, 0.3), WOOD)
    for x in (0.15, w-0.15):
        box(unfinished, "Scaffold", (x, d/2, h*0.3), (0.15, d-0.3, h*0.6), WOOD)
    exports.append((unfinished, path / f"{ident}.IronTeeth.ConstructionStage0.Model.timbermesh"))

# Map-editor sources and the deep ore vein/source are owned by build_map_objects.py
# (tools/map_objects.json); this generator writes no MapEditor models.

for g in CATALOG["goods"]:
    c = collection(g["id"] + ".IconSource")
    stone = SAND if g["id"] in ("Sandstone", "Aggregate") else LIME
    if g["id"] in ("Sandstone", "Limestone", "Aggregate"):
        for x,y,z,s in [(0.3,0.3,0.3,0.3),(0.7,0.6,0.35,0.35),(0.25,0.7,0.23,0.23)]:
            rock(c,"Stone",(x,y,z),(s,s,s),stone)
    elif g["id"] == "Cement":
        box(c,"CementBag",(0.5,0.5,0.4),(0.7,0.55,0.8),LIME)
        box(c,"Band",(0.5,0.5,0.4),(0.72,0.57,0.16),PAINT)
    else:
        for z in (0.15,0.45):
            box(c,"PrecastBlock",(0.5,0.5,z),(0.9,0.6,0.25),LIME)
    # Goods icons are authored SVGs, not colored renders of these props.

settings = timbermesh_exporter.ExportSettings(bpy.context, False, True, False)
scene.frame_set(1)
for c, path in exports:
    path.parent.mkdir(parents=True, exist_ok=True)
    timbermesh_exporter.Exporter.export_collection(c, str(path), settings)

scene.render.engine = "CYCLES"
scene.cycles.samples = 16
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.world.color = (0.4, 0.4, 0.4)
lighting = collection("PreviewRig")
bpy.ops.object.camera_add()
camera = bpy.context.object
scene.camera = camera
camera.data.type = "ORTHO"
for c in list(camera.users_collection): c.objects.unlink(camera)
lighting.objects.link(camera)
bpy.ops.object.light_add(type="AREA", location=(-3, 4, 9))
light = bpy.context.object
light.data.energy, light.data.shape, light.data.size = 1800, "DISK", 7
light.rotation_euler = (Vector((-2,-2,0))-light.location).to_track_quat('-Z','Y').to_euler()
for c in list(light.users_collection): c.objects.unlink(light)
lighting.objects.link(light)
for c, path, resolution, size in icons:
    for candidate in scene.collection.children:
        candidate.hide_render = candidate not in (c, lighting)
    w,d,h = size
    target = Vector((-w/2,-d/2,h*0.42))
    camera.location = target + Vector((7,9,7))
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale = max(w,d,h)*1.55
    scene.render.resolution_x = scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    Path(str(path)+".meta.json").write_text(json.dumps({"isSprite":True,"generateMipMaps":True},indent=2))
for c in scene.collection.children: c.hide_render = False
blend = SOURCE / "Art/Source/ConstructionMaterials.blend"
blend.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
print(f"Authored {len(exports)} meshes and {len(icons)} rendered icons with UV maps.")
