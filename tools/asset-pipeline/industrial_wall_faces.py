"""Wall faces for the crusher, kiln, mixer and quarry: where an authored wall closes a cell face.

Same rule, constants and exclusions as measure_wall_faces.py (imported, not
re-derived): a horizontal face of cell (x, y, z) is a wall when outward
static surfaces within WALL_DEPTH behind the face plane (or up to FRONT proud
of it) cover at least WALL_COVER of SAMPLES x SAMPLES rays. Rails, native
props, liquids and animated parts are not walls. Reads the saved
<Model>-ReferenceStudy.blend (frame 1, evaluated modifiers) with the
registration in industrial_layouts.py and writes
outputs/industrial-integration/<Model>-wall-faces.json, recording the scene's
SHA-256 so the content generator can refuse a stale list. Never saves.

blender -b --python-exit-code 1 --python industrial_wall_faces.py -- --models StoneCrusher,CementKiln,ConcreteMixer
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).parent))
from industrial_layouts import LAYOUTS
from measure_wall_faces import WALL_DEPTH, WALL_COVER, SAMPLES, FRONT, DIRECTIONS, excluded

ROOT = Path(__file__).resolve().parents[2]
MODELS = ('StoneCrusher', 'CementKiln', 'ConcreteMixer', 'MineralQuarry')


def measure(model, source_dir, out_dir):
    layout = LAYOUTS[model]
    ox, oy, oz = layout['origin']
    base_z = layout['baseZ']
    sx, sy, sz = layout['size']
    source = source_dir / f'{model}-ReferenceStudy.blend'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    scene.frame_set(1)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    vertices, polygons, used = [], [], []
    for obj in bpy.data.collections[model + '.ReferenceStudy'].all_objects:
        if excluded(obj):
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        start = len(vertices)
        # Blender scene -> native grid: (-x + ox, -y + oy, z + oz + baseZ),
        # a rotation by 180 degrees about Z, so windings keep their sense.
        for v in mesh.vertices:
            w = evaluated.matrix_world @ v.co
            vertices.append(Vector((-w.x + ox, -w.y + oy, w.z + oz + base_z)))
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
                            hit, hit_normal, _, _ = tree.ray_cast(p + normal * FRONT, -normal, FRONT + WALL_DEPTH)
                            if hit is not None and hit_normal.dot(normal) > .6:
                                covered += 1
                    if covered >= WALL_COVER * SAMPLES * SAMPLES:
                        walls.append([x, y, z, name])
    target = out_dir / f'{model}-wall-faces.json'
    target.write_text(json.dumps({
        'model': model, 'source': source.name, 'sourceSha256': digest, 'frame': 1,
        'coordinateSystem': 'Native grid XYZ; cell (x,y,z) covers [x,x+1)x[y,y+1)x[z,z+1)',
        'rule': f'outward static surfaces within {WALL_DEPTH} behind the face plane (or up to {FRONT} proud) '
                f'cover >= {WALL_COVER:.0%} of {SAMPLES}x{SAMPLES} samples (measure_wall_faces.py)',
        'excluded': 'rail posts/panels, native props, liquids, animated parts',
        'objects': len(used), 'walls': walls}, indent=1) + '\n')
    print('WALL FACES', model, len(walls), target, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', required=True)
    parser.add_argument('--source-dir', type=Path, default=ROOT / 'src/DeepFrontier/Art/Source')
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'outputs/industrial-integration')
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if not cli.source_dir.is_absolute() or not cli.out_dir.is_absolute():
        raise ValueError('Source and output directories must be absolute')
    for model in cli.models.split(','):
        if model not in MODELS:
            raise ValueError('Not a grid-registered industrial model: ' + model)
        measure(model, cli.source_dir, cli.out_dir)


if __name__ == '__main__':
    main()
