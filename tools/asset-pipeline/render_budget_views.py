"""Render matched review views of one saved study for before/after comparison.

Cameras are orthographic at a game-like 45 degree pitch: two 'normal' views
framing the whole building (front-left, rear-right) and two 'close' views
4.5 tiles wide, the game's closest zoom (front and rear facade at mid-height).
The first run (--write-cameras) derives the cameras from that scene's bounds
and writes them to JSON; later runs (--cameras) reuse them exactly, so a
before and an after render share every pixel's ray.

Run: blender -b --python-exit-code 1 --python render_budget_views.py --
        --study FisheryWorks --blend X.blend --out DIR --label before
        (--write-cameras CAMS.json | --cameras CAMS.json) [--resolution 1000]
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PITCH = 45


def bounds(collection):
    deps = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e9, 1e9, 1e9))
    hi = -lo
    for o in collection.all_objects:
        if o.type != 'MESH':
            continue
        for corner in o.evaluated_get(deps).bound_box:
            w = o.matrix_world @ Vector(corner)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def cameras(lo, hi):
    center = (lo + hi) / 2
    extent = max(hi - lo)
    out = []
    for name, azimuth, focus, scale in (
            ('normal-front', 52, center, extent * 1.25),
            ('normal-rear', 232, center, extent * 1.25),
            ('close-front', 52, Vector((center.x, hi.y - (hi.y - lo.y) * .2, lo.z + (hi.z - lo.z) * .45)), 4.5),
            ('close-rear', 232, Vector((center.x, lo.y + (hi.y - lo.y) * .2, lo.z + (hi.z - lo.z) * .45)), 4.5)):
        a, p = math.radians(azimuth), math.radians(PITCH)
        d = Vector((math.cos(p) * math.cos(a), math.cos(p) * math.sin(a), math.sin(p)))
        out.append({'name': name, 'location': list(focus + d * 60), 'target': list(focus), 'scale': scale})
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', required=True)
    parser.add_argument('--blend', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--cameras')
    parser.add_argument('--write-cameras')
    parser.add_argument('--resolution', type=int, default=1000)
    parser.add_argument('--frame', type=int, default=1)
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    bpy.ops.wm.open_mainfile(filepath=cli.blend)
    scene = bpy.context.scene
    scene.frame_set(cli.frame)
    collection = bpy.data.collections[cli.study + '.ReferenceStudy']
    for other in list(scene.collection.children):
        if other != collection:
            scene.collection.children.unlink(other)
    if cli.write_cameras:
        cams = cameras(*bounds(collection))
        Path(cli.write_cameras).write_text(json.dumps(cams, indent=1))
    else:
        cams = json.loads(Path(cli.cameras).read_text())
    rig = bpy.data.collections.new('BudgetReviewRig')
    scene.collection.children.link(rig)
    cam_data = bpy.data.cameras.new('BudgetCam')
    cam_data.type = 'ORTHO'
    cam_data.clip_start, cam_data.clip_end = .1, 400
    camera = bpy.data.objects.new('BudgetCam', cam_data)
    rig.objects.link(camera)
    scene.camera = camera
    sun_data = bpy.data.lights.new('BudgetSun', 'SUN')
    sun_data.energy = 3.2
    sun_data.angle = math.radians(3)
    sun = bpy.data.objects.new('BudgetSun', sun_data)
    sun.rotation_euler = (math.radians(42), 0, math.radians(35))
    rig.objects.link(sun)
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -.03))
    ground = bpy.context.object
    for c in list(ground.users_collection):
        c.objects.unlink(ground)
    rig.objects.link(ground)
    mat = bpy.data.materials.new('BudgetGround')
    mat.use_nodes = True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.20, .19, .16, 1)
    ground.data.materials.append(mat)
    world = scene.world or bpy.data.worlds.new('BudgetWorld')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.55, .60, .68, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .9
    scene.view_settings.view_transform = 'AgX'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.cycles.seed = 0
    scene.cycles.transparent_max_bounces = 32
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    gpus = [d for d in prefs.devices if d.type == 'OPTIX' and d.name == 'NVIDIA GeForce RTX 2060']
    if len(gpus) != 1:
        raise RuntimeError('RTX 2060 OptiX device required')
    for d in prefs.devices:
        d.use = d in gpus
    scene.cycles.device = 'GPU'
    # Denoise on the GPU too: OIDN on the CPU used ~85 of the ~95 CPU-seconds of a 1200 px render.
    if not prefs.has_oidn_gpu_devices():
        raise RuntimeError('RTX 2060 OIDN GPU denoising unavailable')
    scene.cycles.denoising_use_gpu = True
    scene.render.resolution_x = scene.render.resolution_y = cli.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    out = Path(cli.out)
    out.mkdir(parents=True, exist_ok=True)
    for cam in cams:
        camera.location = cam['location']
        camera.rotation_euler = (Vector(cam['target']) - Vector(cam['location'])).to_track_quat('-Z', 'Y').to_euler()
        cam_data.ortho_scale = cam['scale']
        scene.render.filepath = str(out / f"{cli.study}-{cam['name']}-{cli.label}.png")
        bpy.ops.render.render(write_still=True)
        print('BUDGET VIEW', cli.study, cam['name'], cli.label, flush=True)


if __name__ == '__main__':
    main()
