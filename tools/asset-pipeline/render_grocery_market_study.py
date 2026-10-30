"""Standalone art study of the Grocery Market (grocery_market_geometry.py).

Builds the 32-slot civic palette, the authored geometry, its rails, animated
parts and native preview props, saves the scene and renders isometric views.
Renders go to outputs/grocery-market-study/; the scene is saved as
src/DeepFrontier/Art/Source/GroceryMarket-ReferenceStudy.blend.

  blender -b --python render_grocery_market_study.py -- --resolution 900 --samples 24
  ... -- --workbench-cull          (back-face-culled Workbench hole check)
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import gpu_render_lock
from frontier_architecture import Geometry, sway
from reference_materials import create_reference_materials, civic_native_materials
from industrial_facades import extra_materials
from native_building_assets import build_native_assembly, CACHE
from grocery_market_geometry import grocery_market, ACCESS, FOOTPRINT, STOCK_FOODS, STOCK_STAGES

IDENT = 'GroceryMarket'
OUT = ROOT / 'outputs/grocery-market-study'
FRAMES = 121
FPS = 30
VIEWS = {'front-left': (7, 9, 6.2), 'front-right': (-7, 9, 6.2),
         'back-left': (7, -9, 6.2), 'back-right': (-7, -9, 6.5)}


def _cycle(frame):
    """Smooth 0..1..0 hoist profile over the 121-frame loop."""
    t = (frame - 1) / (FRAMES - 1)
    return (1 - math.cos(2 * math.pi * t)) / 2


def animate(obj, kind, value):
    if kind == 'SWAY':
        sway(obj, value, FRAMES)
        return
    if kind == 'HOIST_LOAD':
        base = obj.location.z
        for f in range(1, FRAMES + 1):
            obj.location.z = base + value * _cycle(f)
            obj.keyframe_insert(data_path='location', index=2, frame=f)
    elif kind == 'HOIST_ROPE':
        travel, length = value
        for f in range(1, FRAMES + 1):
            obj.scale.z = (length - travel * _cycle(f)) / length
            obj.keyframe_insert(data_path='scale', index=2, frame=f)
    elif kind == 'HOIST_WHEEL':
        travel, radius = value
        obj.rotation_mode = 'QUATERNION'
        # Authored +X is Blender -X. Rope pays in on the +Y (Blender -Y) side.
        for f in range(1, FRAMES + 1):
            obj.rotation_quaternion = Quaternion((-1, 0, 0), travel * _cycle(f) / radius)
            obj.keyframe_insert(data_path='rotation_quaternion', frame=f)
    else:
        raise ValueError('Unknown animated part kind: ' + kind)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'


def window_glow(materials, strength):
    """Preview-only night glow from the shipped WindowsAtlas lighting map.
    The game supplies this glow natively; the saved scene keeps it off."""
    mat = materials[30]
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bs = nodes['Principled BSDF']
    record = json.loads((CACHE / 'materials.json').read_text())['WindowsAtlas.IronTeeth']
    image = bpy.data.images.load(str(CACHE / record['textures']['_LightingMap']['file']), check_existing=True)
    image.colorspace_settings.name = 'Non-Color'
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = image
    uv = nodes.new('ShaderNodeTexCoord')
    links.new(uv.outputs['UV'], tex.inputs['Vector'])
    tint = nodes.new('ShaderNodeMixRGB')
    tint.blend_type = 'MULTIPLY'
    tint.inputs[0].default_value = 1
    tint.inputs[2].default_value = (1.0, .40, .08, 1)
    links.new(tex.outputs['Color'], tint.inputs[1])
    links.new(tint.outputs[0], bs.inputs['Emission Color'])
    bs.inputs['Emission Strength'].default_value = strength
    return bs


def build(cli):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end, scene.render.fps = 1, FRAMES, FPS
    materials = create_reference_materials('kiln') + extra_materials()
    materials = civic_native_materials(materials)
    if len(materials) != 32:
        raise ValueError('Expected the 32-slot civic palette')
    model = bpy.data.collections.new(IDENT + '.ReferenceStudy')
    scene.collection.children.link(model)
    # Triangle budget: built as a shell, like the civic family
    # (render_reference_studies.SHELL_MODELS): no bevel modifier, enclosed
    # faces removed at build (enclosed_cull.py).
    static = Geometry(IDENT + '.Architecture')
    static.cull_enclosed = static.cull_small_hidden = True
    parts = []
    rails = grocery_market(static, parts)
    static.build(model, materials, 0, 'civic-native')
    for geo in rails.meshes:
        geo.build(model, materials, 0, 'civic-native')
    animated = []
    for geo, kind, value in parts:
        # Moving parts: only their exact (rotation-invariant) self-enclosure.
        geo.cull_enclosed = True
        obj = geo.build(model, materials, 0, 'civic-native')
        animate(obj, kind, value)
        animated.append({'name': geo.name, 'kind': kind, 'value': value})
    # Static fill-stage objects, one per food and stage, exported as named
    # nodes for GroceryStockDisplay.cs (never animated, never prefixed).
    stock = {}
    for (food, stage), geo in sorted(static.stock_parts.items()):
        geo.cull_enclosed = geo.cull_small_hidden = True
        stock[(food, stage)] = geo.build(model, materials, 0, 'civic-native')
        if stock[(food, stage)].name != geo.name:
            raise ValueError('Stock node name changed in Blender: ' + geo.name)
    native_animated = build_native_assembly(static, model, FRAMES)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    static.stock_objects = stock
    return scene, model, materials, static, animated + [{'name': n, 'kind': 'native'} for n in native_animated]


def stock_level(percent):
    """Stage count shown for a fill percentage, as GroceryStockDisplay.cs
    computes it: none when empty, then 1-33 / 34-66 / 67-100 %."""
    return 0 if percent <= 0 else min(STOCK_STAGES, math.ceil(percent * STOCK_STAGES / 100 - 1e-9))


def show_stock(static, levels):
    for (food, stage), obj in static.stock_objects.items():
        obj.hide_render = stage > levels.get(food, STOCK_STAGES)


def bounds(model):
    pts = [o.matrix_world @ Vector(c) for o in model.objects if o.type == 'MESH' for c in o.bound_box]
    low = Vector(tuple(min(v[a] for v in pts) for a in range(3)))
    high = Vector(tuple(max(v[a] for v in pts) for a in range(3)))
    return low, high


def studio(scene, low, high, lamps=()):
    rig = bpy.data.collections.new('Studio')
    scene.collection.children.link(rig)
    def move(o):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        rig.objects.link(o)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    move(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    center = (low + high) / 2
    # The reference studio's three area lights, plus one soft warm fill on the
    # market front and left side, which the reference rig leaves unlit.
    for p, energy, size, color in [((1, 2, 12), 2200, 7, (1, 1, 1)), ((-11, 1, 9), 1300, 7, (1, 1, 1)),
                                   ((-7, -12, 12), 2000, 7, (1, 1, 1)), ((8, 11, 5), 1100, 8, (1, .86, .68))]:
        bpy.ops.object.light_add(type='AREA', location=p)
        light = bpy.context.object
        move(light)
        light.data.energy, light.data.size, light.data.color = energy, size, color
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.04))
    ground = bpy.context.object
    move(ground)
    mat = bpy.data.materials.new('Studio warm grey')
    mat.use_nodes = True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.18, .165, .135, 1)
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .9
    ground.data.materials.append(mat)
    # Studio illumination of the authored lanterns (preview only, like the
    # CementKiln study's ember lights); these lights live outside the model.
    for x, y, z in lamps:
        bpy.ops.object.light_add(type='POINT', location=(-x, -y, z))
        light = bpy.context.object
        move(light)
        light.data.energy, light.data.color, light.data.shadow_soft_size = 25, (1, .52, .18), .06
    scene.world.color = (.28, .28, .28)
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = .25
    return camera


def render_views(scene, camera, low, high, cli, suffix=''):
    center = (low + high) / 2
    target = Vector((center.x, center.y, center.z * .85))
    extent = max(high - low)
    scene.render.resolution_x = scene.render.resolution_y = cli.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    paths = []
    for view in cli.views.split(','):
        scene.frame_set(cli.frame)
        camera.location = target + Vector(VIEWS[view])
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = extent * 1.30
        path = OUT / f'{IDENT}-{view}{suffix}.png'
        scene.render.filepath = str(path)
        gpu_render_lock.render(write_still=True)
        paths.append(str(path.relative_to(ROOT)))
        print('GROCERY STUDY RENDERED', path, flush=True)
    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resolution', type=int, default=900)
    parser.add_argument('--samples', type=int, default=24)
    parser.add_argument('--views', default='front-left,front-right,back-left,back-right')
    parser.add_argument('--frame', type=int, default=1)
    parser.add_argument('--glow', type=float, default=3.0, help='Preview-only window night glow')
    parser.add_argument('--workbench-cull', action='store_true')
    parser.add_argument('--suffix', default='')
    parser.add_argument('--save-only', action='store_true')
    parser.add_argument('--stock', default='', help='Preview stock as Food=percent,... (default: every stage shown)')
    parser.add_argument('--blend', type=Path, default=ROOT / f'src/DeepFrontier/Art/Source/{IDENT}-ReferenceStudy.blend',
                        help='Scene path (absolute); the default is the art source of record')
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    for view in cli.views.split(','):
        if view not in VIEWS:
            raise ValueError('Unknown view ' + view)
    OUT.mkdir(parents=True, exist_ok=True)
    scene, model, materials, static, animated = build(cli)
    low, high = bounds(model)
    camera = studio(scene, low, high, getattr(static, 'lamp_points', ()))
    levels = {}
    for item in filter(None, cli.stock.split(',')):
        food, percent = item.split('=')
        if food not in STOCK_FOODS:
            raise ValueError('Unknown stock food ' + food)
        levels[food] = stock_level(float(percent))
    show_stock(static, levels)
    renders = []
    if not cli.save_only:
        if cli.workbench_cull:
            scene.render.engine = 'BLENDER_WORKBENCH'
            shading = scene.display.shading
            shading.light = 'STUDIO'
            shading.color_type = 'MATERIAL'
            shading.show_backface_culling = True
            shading.show_cavity = True
            renders = render_views(scene, camera, low, high, cli, cli.suffix or '-culled')
        else:
            bs = window_glow(materials, cli.glow)
            scene.render.engine = 'CYCLES'
            scene.cycles.samples = cli.samples
            scene.cycles.use_denoising = True
            scene.cycles.transparent_max_bounces = 32
            prefs = bpy.context.preferences.addons['cycles'].preferences
            prefs.compute_device_type = 'OPTIX'
            prefs.get_devices()
            required = [d for d in prefs.devices if d.type == 'OPTIX' and d.name == 'NVIDIA GeForce RTX 2060']
            if len(required) != 1:
                raise RuntimeError('Required RTX 2060 OptiX render device is unavailable')
            for device in prefs.devices:
                device.use = device in required
            scene.cycles.device = 'GPU'
            # Denoise on the GPU too: OIDN on the CPU used ~85 of the ~95 CPU-seconds of a 1200 px render.
            if not prefs.has_oidn_gpu_devices():
                raise RuntimeError('RTX 2060 OIDN GPU denoising unavailable')
            scene.cycles.denoising_use_gpu = True
            renders = render_views(scene, camera, low, high, cli, cli.suffix)
            bs.inputs['Emission Strength'].default_value = 0
    show_stock(static, {})   # the saved source shows every stage
    scene.frame_set(1)
    tris = sum(len(o.data.polygons) for o in model.objects if o.type == 'MESH')
    (OUT / f'{IDENT}-study.json').write_text(json.dumps({
        'status': 'Blender art study; not exported, promoted or installed',
        'sourceReference': 'docs/art/concepts/Grocery Store.png (four isometric views and detail panels)',
        'footprint': list(FOOTPRINT),
        'authoredBoundsMin': [-high.x, -high.y, low.z], 'authoredBoundsMax': [-low.x, -low.y, high.z],
        'access': ACCESS, 'doors': static.doorways,
        'animatedParts': animated, 'animationFrames': FRAMES, 'animationFps': FPS,
        'faces': tris, 'renders': renders, 'previewStock': levels,
        'stockNodes': sorted(o.name for o in static.stock_objects.values()),
        'windowGlow': 'Preview only, from the shipped WindowsAtlas lighting map; off in the saved scene',
    }, indent=2, default=list) + '\n')
    # Art source of record, exported by export_lategame_models.py (GroceryStore).
    blend = cli.blend
    if not blend.is_absolute():
        raise ValueError('--blend must be an absolute path')
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print('GROCERY STUDY SAVED', blend, 'faces', tris, 'bounds', tuple(low), tuple(high), flush=True)


if __name__ == '__main__':
    main()
