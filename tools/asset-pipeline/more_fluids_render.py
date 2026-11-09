"""Review renders of More Fluids models (and the vanilla models they sit beside).

Each spec entry is rendered alone on native grass with faint tile lines, at
the game's 45 degree orthographic pitch, from several sides, framed by its
blueprint footprint. Uses map_object_preview.py's native material previews,
extended with the Folktails/Iron Teeth/Common records cached by
more_fluids_native_refs.py (outputs/more-fluids-art/native).

  {"entries": [{"id": "FluidExtractor.Folktails", "size": [2, 3, 3],
                "files": [{"path": "src/MoreFluids/Data/.../X.Model.timbermesh", "offset": [0, 0, 0]}],
                "views": ["front", "left", "rear"], "close": true}]}

Paths are relative to the repository (or absolute). Writes <out>/<id>-<view>.png.

Run: blender -b --factory-startup --python-exit-code 1 --python more_fluids_render.py --
        --spec SPEC.json --out DIR [--resolution 900] [--only id,id]
"""
import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
import gpu_render_lock  # noqa: E402
import map_object_preview as preview  # noqa: E402

ROOT = preview.ROOT
NATIVE = ROOT / 'outputs/more-fluids-art/native'
for _name, _record in json.loads((NATIVE / 'materials.json').read_text()).items():
    preview._records.setdefault(_name, (NATIVE, _record))

# Camera azimuths (degrees, Blender): the blueprint front (entrance side) is
# Blender +Y; 'front' is the game's default front-right view.
VIEWS = {'front': 62, 'left': 118, 'rear': 242, 'right': -28, 'back-left': 152}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--resolution', type=int, default=900)
    parser.add_argument('--samples', type=int, default=32)
    parser.add_argument('--only')
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    spec = json.loads(Path(cli.spec).read_text())
    out = Path(cli.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    preview.setup_render(scene, cli.resolution)
    scene.cycles.samples = cli.samples
    rig = bpy.data.collections.new('PreviewRig')
    scene.collection.children.link(rig)
    camera = preview.rig(rig)
    scene.camera = camera
    wanted = set(cli.only.split(',')) if cli.only else None
    stats = {}
    for entry in spec['entries']:
        if wanted and entry['id'] not in wanted:
            continue
        holder = bpy.data.collections.new(entry['id'])
        scene.collection.children.link(holder)
        w, d, h = entry['size']
        entry_stats = []
        for item in entry['files']:
            ox, oy, oz = item.get('offset', (0, 0, 0))
            path = Path(item['path'])
            path = path if path.is_absolute() else ROOT / path
            _, s = preview.import_timbermesh(path, holder, (-ox, -oy, oz), yaw=item.get('yaw', 0))
            entry_stats.append({'path': item['path'], **s})
        pad = entry.get('pad', 2.5)
        preview.ground(holder, (-w / 2, -d / 2), (w + 2 * pad, d + 2 * pad))
        extent = (max(w, d, h * .8) * 1.45 + 1) / entry.get('zoom', 1)
        target = (-w / 2, -d / 2, entry.get('focusHeight', min(h, 3) * .3))
        for view in entry.get('views', ['front', 'left', 'rear']):
            preview.aim(camera, target, extent, azimuth=VIEWS[view])
            scene.render.filepath = str(out / f"{entry['id']}-{view}.png")
            gpu_render_lock.render(write_still=True)
        if entry.get('close'):
            preview.aim(camera, target, extent * .62, azimuth=VIEWS['front'], pitch=35)
            scene.render.filepath = str(out / f"{entry['id']}-close.png")
            gpu_render_lock.render(write_still=True)
        stats[entry['id']] = entry_stats
        print('MORE FLUIDS VIEW', entry['id'], json.dumps([s['triangles'] for s in entry_stats]), flush=True)
        for obj in list(holder.all_objects):
            bpy.data.objects.remove(obj)
        bpy.data.collections.remove(holder)
    (out / 'render-stats.json').write_text(json.dumps(stats, indent=1) + '\n')


if __name__ == '__main__':
    main()
