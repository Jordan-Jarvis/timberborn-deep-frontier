"""Measure which horizontal cell faces an authored wall actually closes.

Reads the saved <Model>-ReferenceStudy.blend (frame 1, evaluated modifiers)
and writes <integration>/<Model>-wall-faces.json for the content generator:
a face of cell (x, y, z) toward Left/Right/Down/Up is a wall when outward-
facing static surfaces within WALL_DEPTH behind the cell plane cover at least
WALL_COVER of it (SAMPLES x SAMPLES rays). Rails, native props, liquids and
animated parts are not walls. The result is geometric only: the generator
still decides which occupied faces are exposed. Never saves the scene.

blender -b --python-exit-code 1 --python measure_wall_faces.py -- --model ReinforcedHydroTurbine
"""
import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).parent))
from hydro_layout import LAYOUTS as HYDRO_LAYOUTS
from research_layouts import LAYOUTS as RESEARCH_LAYOUTS

ROOT = Path(__file__).resolve().parents[2]
WALL_DEPTH = .12   # same contract as render_lategame_studies.registration()
WALL_COVER = .6
SAMPLES = 8
FRONT = .02        # trim standing up to 2 cm proud of the plane still counts
TARGETS = {**{k: 'hydro-integration' for k in HYDRO_LAYOUTS},
           **{k: 'research-integration' for k in RESEARCH_LAYOUTS}}
DIRECTIONS = (('Left', (-1, 0)), ('Right', (1, 0)), ('Down', (0, -1)), ('Up', (0, 1)))


def animated(obj):
    while obj is not None:
        if obj.animation_data and obj.animation_data.action:
            return True
        obj = obj.parent
    return False


def excluded(obj):
    name = obj.name
    return (obj.type != 'MESH' or obj.hide_render or 'native_resource' in obj or 'liquid_surface' in obj
            or ('Rail' in name and ('.Post' in name or '.Panel' in name)) or animated(obj))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True, choices=sorted(TARGETS))
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    layout = {**HYDRO_LAYOUTS, **RESEARCH_LAYOUTS}[cli.model]
    ox, oy, oz = layout['origin']
    base_z = layout['baseZ']
    sx, sy, sz = layout['size']
    source = ROOT / 'src/DeepFrontier/Art/Source' / f'{cli.model}-ReferenceStudy.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    scene.frame_set(1)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    vertices, polygons, used = [], [], []
    for obj in bpy.data.collections[cli.model + '.ReferenceStudy'].all_objects:
        if excluded(obj):
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        start = len(vertices)
        # Blender scene -> native grid: (-x + ox, -y + oy, z + oz + baseZ).
        for v in mesh.vertices:
            w = evaluated.matrix_world @ v.co
            vertices.append(Vector((-w.x + ox, -w.y + oy, w.z + oz + base_z)))
        # The X/Y mirror is a rotation by 180 degrees about Z: windings keep
        # their outward sense, so polygon order is copied unchanged.
        polygons.extend(tuple(start + i for i in p.vertices) for p in mesh.polygons)
        evaluated.to_mesh_clear()
        used.append(obj.name)
    tree = BVHTree.FromPolygons(vertices, polygons)
    walls = []
    for z in range(sz):
        for y in range(sy):
            for x in range(sx):
                for name, (nx, ny) in DIRECTIONS:
                    normal = Vector((nx, ny, 0))
                    plane = (x + 1 if nx > 0 else x) if nx else (y + 1 if ny > 0 else y)
                    covered = 0
                    for i in range(SAMPLES):
                        for j in range(SAMPLES):
                            u, v = (i + .5) / SAMPLES, (j + .5) / SAMPLES
                            p = Vector((plane, y + u, z + v)) if nx else Vector((x + u, plane, z + v))
                            hit, hit_normal, _, distance = tree.ray_cast(p + normal * FRONT, -normal, FRONT + WALL_DEPTH)
                            if hit is not None and hit_normal.dot(normal) > .6:
                                covered += 1
                    if covered >= WALL_COVER * SAMPLES * SAMPLES:
                        walls.append([x, y, z, name])
    target = ROOT / 'outputs' / TARGETS[cli.model] / f'{cli.model}-wall-faces.json'
    target.write_text(json.dumps({
        'model': cli.model, 'source': str(source.relative_to(ROOT)), 'frame': 1,
        'coordinateSystem': 'Native grid XYZ; cell (x,y,z) covers [x,x+1)x[y,y+1)x[z,z+1)',
        'rule': f'outward static surfaces within {WALL_DEPTH} behind the face plane (or up to {FRONT} proud) '
                f'cover >= {WALL_COVER:.0%} of {SAMPLES}x{SAMPLES} samples',
        'excluded': 'rail posts/panels, native props, liquids, animated parts',
        'objects': len(used), 'walls': walls}, indent=1) + '\n')
    print('WALL FACES', cli.model, len(walls), target, flush=True)


if __name__ == '__main__':
    main()
