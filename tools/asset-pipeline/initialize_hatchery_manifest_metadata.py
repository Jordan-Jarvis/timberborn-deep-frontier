"""Explicit metadata migration for the just-created candidate; no mesh builds."""
import json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from blender_components import object_digest
from hatchery_manifests import write_manifests
out=ROOT/'outputs/hatchery-platform-candidate'
if Path(bpy.data.filepath)!=out/'FishHatchery-ReferenceStudy.blend':raise ValueError('Open the candidate only')
c=bpy.data.collections['FishHatchery.ReferenceStudy'];a=c.objects['FishHatchery.Architecture']
before={o.name:object_digest(o) for o in bpy.data.objects if o!=a}
a['df_native_assembly']=(out/'FishHatchery-native-assembly.json').read_text()
a['df_native_object_digests']=json.dumps({o.name:object_digest(o) for o in c.objects if 'native_resource' in o or 'liquid_surface' in o})
a['df_rail_manifest']=(out/'FishHatchery-rail-manifest.json').read_text()
print('MANIFESTS',write_manifests(out,c))
if any(object_digest(bpy.data.objects[n])!=digest for n,digest in before.items()):raise ValueError('Metadata update changed scene geometry')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'FishHatchery-ReferenceStudy.blend'))
