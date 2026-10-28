"""Write the Hatchery's component metadata onto a regenerated scene from its recipes.

For an intentional redesign (2026-10-26 compact footprint) the room, deck and
rail contracts change, so carry_hatchery_metadata.py (which only carries
unchanged metadata) does not apply. This writes, from the same source recipes
the regeneration just built, with no mesh build or edit:
  - df_structural_parts on every 'Headhouse.*'/'Deck.*'/'Door.*' component and
    df_window_mounts on them (hatchery_components.recipe(key));
  - df_rail_manifest (hatchery_components.rails().manifest()), which must own
    exactly the regenerated rail objects;
  - df_native_assembly (the regeneration's native-assembly.json) and the
    preview-prop digests, as initialize_hatchery_manifest_metadata.py does.
Every object digest, apart from these keys, must be unchanged after.
hatchery_manifests.write_manifests then checks the whole contract and writes
the manifests to --output.

Run: blender -b --python-exit-code 1 --python refresh_hatchery_metadata.py --
        --scene NEW.blend --native-assembly NEW-native-assembly.json --output DIR
"""
import argparse
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from blender_components import object_digest
from hatchery_components import recipes, rails

COLLECTION = 'FishHatchery.ReferenceStudy'
WRITTEN = ('df_structural_parts', 'df_window_mounts', 'df_rail_manifest', 'df_native_assembly', 'df_native_object_digests')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--native-assembly', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if not (cli.scene.is_absolute() and cli.native_assembly.is_absolute() and cli.output.is_absolute()):
        raise ValueError('Paths must be absolute')
    bpy.ops.wm.open_mainfile(filepath=str(cli.scene))
    collection = bpy.data.collections[COLLECTION]
    before = {o.name: object_digest(o) for o in bpy.data.objects}
    components = {o['df_component']: o for o in collection.all_objects if 'df_component' in o}
    expected = {'FishHatchery.' + key for key in recipes()}
    if set(components) != expected:
        raise ValueError(f'Scene components differ from the recipes: {sorted(set(components) ^ expected)}')
    for key, build in recipes().items():
        g = build()
        obj = components['FishHatchery.' + key]
        if any(k in obj for k in ('df_structural_parts', 'df_window_mounts')):
            raise ValueError('Regenerated component already holds metadata: ' + obj.name)
        obj['df_structural_parts'] = json.dumps(g.structural_parts)
        obj['df_window_mounts'] = json.dumps(g.window_mounts)
    rail = rails()
    names = {o.name for o in collection.all_objects if o.name.startswith('WalkwayRail.FishHatchery.')}
    if {g.name for g in rail.meshes} != names:
        raise ValueError('Rail recipe does not own exactly the regenerated rail objects')
    architecture = collection.all_objects['FishHatchery.Architecture']
    if any(k in architecture for k in ('df_rail_manifest', 'df_native_assembly')):
        raise ValueError('Regenerated architecture already holds metadata')
    architecture['df_rail_manifest'] = json.dumps(rail.manifest())
    architecture['df_native_assembly'] = cli.native_assembly.read_text(encoding='utf-8')
    architecture['df_native_object_digests'] = json.dumps({o.name: object_digest(o) for o in collection.objects
                                                           if 'native_resource' in o or 'liquid_surface' in o})
    def unmarked(obj):
        # The digest covers custom properties; compare without the keys written here.
        saved = {k: obj[k] for k in WRITTEN if k in obj}
        for k in saved:
            del obj[k]
        digest = object_digest(obj)
        for k, v in saved.items():
            obj[k] = v
        return digest
    changed = [n for n, d in before.items() if unmarked(bpy.data.objects[n]) != d]
    if changed:
        raise RuntimeError('Metadata write changed scene geometry: ' + str(changed))
    from hatchery_manifests import write_manifests
    cli.output.mkdir(parents=True, exist_ok=True)
    manifests = write_manifests(cli.output, collection)
    bpy.ops.wm.save_as_mainfile(filepath=str(cli.scene))
    print('HATCHERY METADATA REFRESHED', json.dumps({'components': sorted(components), 'manifests': manifests}), flush=True)


if __name__ == '__main__':
    main()
