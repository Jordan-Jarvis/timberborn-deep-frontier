"""Rebuild only the41 Hatchery rails with exact authored grid identity."""
import hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from blender_components import object_digest
from hatchery_components import rails
from hatchery_manifests import write_manifests
expected='a0e772dc6c3d9a428a7138f9eb53258f5c2b23d9b5ac821ead659fe9a117a171'
candidate=ROOT/'outputs/hatchery-platform-candidate'
jobs=[(candidate/'FishHatchery-ReferenceStudy.blend',candidate),
      (ROOT/'src/DeepFrontier/Art/Source/FishHatchery-ReferenceStudy.blend',ROOT/'outputs/reference-studies')]
for scene,_ in jobs:
    if hashlib.sha256(scene.read_bytes()).hexdigest()!=expected:raise ValueError('Hatchery scene changed before rail migration: '+str(scene))
reports=[]
for scene,output in jobs:
    bpy.ops.wm.open_mainfile(filepath=str(scene));bpy.context.scene.frame_set(1)
    collection=bpy.data.collections['FishHatchery.ReferenceStudy'];arch=collection.objects['FishHatchery.Architecture']
    old=[obj for obj in collection.objects if obj.name.startswith('WalkwayRail.FishHatchery.')]
    if len(old)!=41:raise ValueError('Expected the41 reviewed rail objects')
    untouched={obj.name:object_digest(obj) for obj in bpy.data.objects if obj not in old and obj!=arch}
    rail=rails();expected_names={g.name for g in rail.meshes}
    if expected_names!={obj.name for obj in old}:raise ValueError('Rail object identity changed')
    materials=list(arch.data.materials)
    for obj in old:
        mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
    for g in rail.meshes:g.build(collection,materials,.012,'civic-native')
    arch['df_rail_manifest']=json.dumps(rail.manifest())
    bpy.context.view_layer.update();write_manifests(output,collection)
    for name,digest in untouched.items():
        if object_digest(bpy.data.objects[name])!=digest:raise ValueError('Non-rail object changed: '+name)
    bpy.ops.wm.save_as_mainfile(filepath=str(scene))
    reports.append({'scene':str(scene),'sourceSha256Before':expected,'sourceSha256After':hashlib.sha256(scene.read_bytes()).hexdigest(),
        'rebuiltRailObjects':41,'authoredGridPanels':20,'unselectedObjectsPreserved':len(untouched)})
(candidate/'grid-rail-migration.json').write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps(reports))
