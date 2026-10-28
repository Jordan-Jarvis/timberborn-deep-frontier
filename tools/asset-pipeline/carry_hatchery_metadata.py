"""Carry the Hatchery's migration metadata onto a regenerated scene.

The FishHatchery scene was last shaped by explicit migrations
(migrate_hatchery_platform.py, migrate_hatchery_grid_rails.py, ...), which
store component metadata as object properties that render_reference_studies.py
does not write: df_native_assembly, df_native_object_digests, df_rail_manifest
(on FishHatchery.Architecture), df_structural_parts (room and deck
components) and df_window_mounts (FishHatchery.Headhouse.Windows).

After a regeneration (same generator, shell build), this copies the rail
manifest, structural parts and window mounts from the previous saved scene,
but only when what they describe is unchanged: the rail manifest must own
exactly the current rail objects, and every carried object must exist. The
native assembly is the regenerated one (--native-assembly, written by
render_reference_studies.py with the scene) and its preview-prop digests are
taken from the new scene, as initialize_hatchery_manifest_metadata.py does.
hatchery_manifests.write_manifests then re-checks the whole contract and
refreshes the manifests, as a selected rebuild does. Nothing else in either
scene is changed.

Run: blender -b --python-exit-code 1 --python carry_hatchery_metadata.py --
        --previous OLD.blend --scene NEW.blend --native-assembly NEW-native-assembly.json
"""
import argparse
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from blender_components import object_digest

KEYS = ('df_rail_manifest', 'df_structural_parts', 'df_window_mounts')
COLLECTION = 'FishHatchery.ReferenceStudy'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--native-assembly', type=Path, required=True)
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if not (cli.previous.is_absolute() and cli.scene.is_absolute() and cli.native_assembly.is_absolute()):
        raise ValueError('Scene paths must be absolute')
    bpy.ops.wm.open_mainfile(filepath=str(cli.previous))
    carried = {}
    for obj in bpy.data.collections[COLLECTION].all_objects:
        values = {k: obj[k] for k in KEYS if k in obj}
        if values:
            carried[obj.name] = values
    if not set(KEYS) <= set(k for v in carried.values() for k in v):
        raise ValueError('The previous scene does not hold the complete Hatchery migration metadata')
    bpy.ops.wm.open_mainfile(filepath=str(cli.scene))
    collection = bpy.data.collections[COLLECTION]
    for name, values in carried.items():
        if name not in collection.all_objects:
            raise ValueError('Carried metadata names a missing object: ' + name)
        if any(k in collection.all_objects[name] for k in values):
            raise ValueError('The regenerated scene already holds migration metadata on ' + name)
    root = carried['FishHatchery.Architecture']
    rails = json.loads(root['df_rail_manifest'])
    current = {o.name for o in collection.all_objects if o.name.startswith('WalkwayRail.FishHatchery.')}
    if set(rails['nodes']) != current:
        raise ValueError('The rail manifest does not own the regenerated rail objects')
    for name, values in carried.items():
        for key, value in values.items():
            collection.all_objects[name][key] = value
    architecture = collection.all_objects['FishHatchery.Architecture']
    architecture['df_native_assembly'] = cli.native_assembly.read_text(encoding='utf-8')
    architecture['df_native_object_digests'] = json.dumps({o.name: object_digest(o) for o in collection.objects
                                                           if 'native_resource' in o or 'liquid_surface' in o})
    from hatchery_manifests import write_manifests
    manifests = write_manifests(ROOT / 'outputs/reference-studies', collection)
    bpy.ops.wm.save_as_mainfile(filepath=str(cli.scene))
    print('HATCHERY METADATA CARRIED', json.dumps({'objects': sorted(carried), 'manifests': manifests}, default=str), flush=True)


if __name__ == '__main__':
    main()
