"""Correct the candidate's explicitly authorized barrel placement at its root."""
import hashlib,json,sys,zlib
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from blender_components import object_digest
from native_building_assets import CACHE,model_pb2,transform
from hatchery_manifests import write_manifests
folder=ROOT/'outputs/hatchery-platform-candidate'
path=folder/'FishHatchery-ReferenceStudy.blend'
expected='a9c075e23a0ff1450e7436aa46432dfee3f5f3d7310e45ee26ae9b94fbd756f5'
if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Candidate changed before explicit prop correction')
bpy.ops.wm.open_mainfile(filepath=str(path));collection=bpy.data.collections['FishHatchery.ReferenceStudy']
arch=collection.objects['FishHatchery.Architecture'];prop=collection.objects['NativeBarrel1'];child=collection.objects['NativeBarrel1.Barrel']
before={obj.name:object_digest(obj) for obj in collection.objects if obj.name not in (arch.name,prop.name,child.name)}
model=model_pb2.Model();model.ParseFromString(zlib.decompress((CACHE/'Barrel.timbermesh').read_bytes()))
if len(model.nodes)!=1 or model.nodes[0].name!='Barrel':raise ValueError('Native Barrel resource hierarchy changed')
transform(child,model.nodes[0])
prop.location=(-3.65,0,.29865744)
bpy.context.view_layer.update()
arch['df_native_object_digests']=json.dumps({obj.name:object_digest(obj) for obj in collection.objects if 'native_resource' in obj or 'liquid_surface' in obj})
write_manifests(folder,collection)
for name,digest in before.items():
    if object_digest(collection.objects[name])!=digest:raise ValueError('Unselected object changed: '+name)
bpy.ops.wm.save_as_mainfile(filepath=str(path))
report={'beforeSha256':expected,'afterSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'rootSourcePosition':[3.65,0,.29865744],'nativeChildTransformRestored':True,
        'unselectedObjectsPreserved':len(before),'geometryRebuilt':False}
(folder/'barrel-root-correction.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
