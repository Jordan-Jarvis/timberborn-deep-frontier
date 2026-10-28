"""Render matched game-like views of map objects and good models for review.

Each entry of the JSON spec is rendered alone on native grass terrain with
faint tile lines, at the game's 45 degree orthographic pitch, framed by its
blueprint footprint so before and after renders of one object share a camera:

  {"entries": [{"id": "DeepOreVein", "size": [5, 5, 1],
                "files": [{"path": "src/.../DeepOreVein.Model.timbermesh", "offset": [0, 0, 0]}],
                "tintNodes": [], "tintAll": false, "zoom": 1.0}]}

Paths are relative to the repository. Offsets are in tiles (x across, y back,
z up). Writes <out>/<id>-<label>.png and <out>/<label>-stats.json.

Run: blender -b --factory-startup --python-exit-code 1 --python render_map_object_views.py --
        --spec SPEC.json --out DIR --label before [--resolution 700]
"""
import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
import map_object_preview as preview  # noqa: E402

ROOT = preview.ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--resolution', type=int, default=700)
    parser.add_argument('--only')
    parser.add_argument('--close', action='store_true', help='also render a close view (-close suffix)')
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    spec = json.loads(Path(cli.spec).read_text())
    out = Path(cli.out)
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    preview.setup_render(scene, cli.resolution)
    rig = bpy.data.collections.new('PreviewRig')
    scene.collection.children.link(rig)
    camera = preview.rig(rig)
    scene.camera = camera
    stats = {}
    wanted = set(cli.only.split(',')) if cli.only else None
    for entry in spec['entries']:
        if wanted and entry['id'] not in wanted:
            continue
        holder = bpy.data.collections.new(entry['id'])
        scene.collection.children.link(holder)
        w, d, h = entry['size']
        entry_stats = {'files': []}
        for item in entry['files']:
            ox, oy, oz = item.get('offset', (0, 0, 0))
            if 'liquid' in item:
                # A tank's liquid surface: the native liquid material on a plane
                # inside a dark tank rim (stockpile plane visualization stand-in).
                mesh = bpy.data.meshes.new(item['liquid'])
                r = .42
                mesh.from_pydata([(-r, -r, 0), (r, -r, 0), (r, r, 0), (-r, r, 0)], [], [(0, 1, 2, 3)])
                mesh.uv_layers.new(name='uv0')
                for loop, uv in zip(mesh.uv_layers[0].data, ((0, 0), (1, 0), (1, 1), (0, 1))):
                    loop.uv = uv
                mesh.materials.append(preview.material(item['liquid']))
                obj = bpy.data.objects.new(item['liquid'], mesh)
                holder.objects.link(obj)
                obj.location = (-ox, -oy, oz)
                bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=.6, depth=oz, location=(-ox, -oy, oz / 2 - .002))
                rim = bpy.context.object
                for c in list(rim.users_collection):
                    c.objects.unlink(rim)
                holder.objects.link(rim)
                rim.data.materials.append(preview.material('BaseMetal.IronTeeth'))
                entry_stats['files'].append({'path': 'liquid:' + item['liquid'], 'triangles': 2})
                continue
            if 'nativeMesh' in item:
                _, s = preview.import_native_mesh(item['nativeMesh'], item['material'], holder, (-ox, -oy, oz), item.get('yaw', 0))
                entry_stats['files'].append({'path': 'native:' + item['nativeMesh'], **s})
                continue
            _, s = preview.import_timbermesh(ROOT / item['path'], holder, (-ox, -oy, oz),
                                             tint_nodes=tuple(entry.get('tintNodes', ())), tint_all=entry.get('tintAll', False),
                                             yaw=item.get('yaw', 0))
            entry_stats['files'].append({'path': item['path'], **s})
        pad = 2.5
        ground = preview.ground(holder, (-w / 2, -d / 2), (w + 2 * pad, d + 2 * pad))
        extent = (max(w, d) * 1.5 + 1) / entry.get('zoom', 1)
        # Framed by the footprint only, so before and after share every ray.
        target = (-w / 2, -d / 2, entry.get('focusHeight', min(h, 2) * .2))
        views = [('', extent, target)]
        if cli.close:
            views.append(('-close', min(extent, 3.2 if max(w, d) > 2 else 2.0), target))
        for suffix, scale, target in views:
            preview.aim(camera, target, scale)
            scene.render.filepath = str(out / f"{entry['id']}{suffix}-{cli.label}.png")
            bpy.ops.render.render(write_still=True)
        print('MAP OBJECT VIEW', entry['id'], cli.label, json.dumps({k: v['triangles'] for k, v in
                                                                    zip(range(len(entry_stats['files'])), entry_stats['files'])}), flush=True)
        stats[entry['id']] = entry_stats
        for obj in list(holder.all_objects):
            bpy.data.objects.remove(obj)
        bpy.data.collections.remove(holder)
    (out / f'{cli.label}-stats.json').write_text(json.dumps(stats, indent=1) + '\n')


if __name__ == '__main__':
    main()
