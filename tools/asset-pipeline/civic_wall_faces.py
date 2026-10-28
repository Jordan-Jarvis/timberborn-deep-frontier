"""Measure which horizontal cell faces an authored civic wall actually closes.

Same contract as measure_wall_faces.py / industrial_wall_faces.py, for the
grid-structure civic buildings (Restaurant, Hospital). Reads the saved
<Model>-ReferenceStudy.blend at frame 1 with evaluated modifiers and writes
outputs/civic-integration/<Model>-wall-faces.json: a face of cell (x, y, z)
toward Left/Right/Down/Up is a wall when outward-facing static surfaces
within WALL_DEPTH behind the cell plane (or up to FRONT proud of it) cover at
least WALL_COVER of SAMPLES x SAMPLES rays. Rails, native props, liquids and
animated parts are not walls. The record carries the scene's SHA256 so the
content generator can reject a stale measurement. Never saves the scene.

blender -b --python-exit-code 1 --python civic_wall_faces.py -- --model Restaurant [--source <abs blend>] [--output <abs json>]
"""
import argparse, hashlib, json, sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).parent))
ROOT = Path(__file__).resolve().parents[2]
WALL_DEPTH = .12
WALL_COVER = .6
SAMPLES = 8
FRONT = .02
DIRECTIONS = (('Left', (-1, 0)), ('Right', (1, 0)), ('Down', (0, -1)), ('Up', (0, 1)))
MODELS = ('Restaurant', 'Hospital')


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
    parser.add_argument('--model', required=True, choices=MODELS)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path)
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    layout = json.loads((ROOT / 'tools/civic-layouts.json').read_text())[cli.model]
    ox, oy, oz = layout['origin']
    base_z = layout['baseZ']
    sx, sy, sz = layout['size']
    source = cli.source or ROOT / 'src/DeepFrontier/Art/Source' / f'{cli.model}-ReferenceStudy.blend'
    target = cli.output or ROOT / 'outputs/civic-integration' / f'{cli.model}-wall-faces.json'
    if not source.is_absolute() or not target.is_absolute():
        raise ValueError('Wall-face source and output must be absolute paths')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
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
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise RuntimeError('Scene changed while measuring')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({
        'model': cli.model, 'source': str(source), 'sourceSha256': digest, 'frame': 1,
        'coordinateSystem': 'Native grid XYZ; cell (x,y,z) covers [x,x+1)x[y,y+1)x[z,z+1)',
        'rule': f'outward static surfaces within {WALL_DEPTH} behind the face plane (or up to {FRONT} proud) '
                f'cover >= {WALL_COVER:.0%} of {SAMPLES}x{SAMPLES} samples',
        'excluded': 'rail posts/panels, native props, liquids, animated parts',
        'objects': len(used), 'walls': walls}, indent=1) + '\n')
    print('WALL FACES', cli.model, len(walls), target, flush=True)


if __name__ == '__main__':
    main()
