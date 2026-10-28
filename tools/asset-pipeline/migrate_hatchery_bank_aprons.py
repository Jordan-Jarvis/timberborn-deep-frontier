"""Rebuild only the two bank aprons with authored terrain clearance."""
import hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from blender_components import object_digest
from hatchery_components import recipe
from hatchery_structure import BANK_APRON_SURFACE
from hatchery_manifests import write_manifests
candidate=ROOT/'outputs/hatchery-platform-candidate'
jobs=[(candidate/'FishHatchery-ReferenceStudy.blend',candidate,'112ea285cde3ee68abf30eba50300fe5bcfcdc42075b449482c68adb738d0082'),
      (ROOT/'src/DeepFrontier/Art/Source/FishHatchery-ReferenceStudy.blend',ROOT/'outputs/reference-studies','cd9492161f43ee655cd445ff16c8957fbc1428bc91f7c66612c991003d515cff')]
keys=('Deck.MainFrontApron','Deck.CanopyFrontApron');names={'FishHatchery.'+key for key in keys}
for scene,_,expected in jobs:
    if hashlib.sha256(scene.read_bytes()).hexdigest()!=expected:raise ValueError('Scene changed before selected apron rebuild: '+str(scene))
reports=[]
for scene,output,expected in jobs:
    bpy.ops.wm.open_mainfile(filepath=str(scene));bpy.context.scene.frame_set(1)
    collection=bpy.data.collections['FishHatchery.ReferenceStudy']
    untouched={obj.name:object_digest(obj) for obj in bpy.data.objects if obj.name not in names}
    for key in keys:
        old=collection.objects['FishHatchery.'+key];materials=list(old.data.materials);mesh=old.data
        bpy.data.objects.remove(old,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
        g=recipe(key);obj=g.build(collection,materials,.012,'civic-native')
        obj['df_component']=obj.name;obj['df_structural_parts']=json.dumps(g.structural_parts)
    bpy.context.view_layer.update();write_manifests(output,collection)
    for name,digest in untouched.items():
        if object_digest(bpy.data.objects[name])!=digest:raise ValueError('Unselected object changed: '+name)
    bpy.ops.wm.save_as_mainfile(filepath=str(scene))
    reports.append({'scene':str(scene),'sourceSha256Before':expected,'sourceSha256After':hashlib.sha256(scene.read_bytes()).hexdigest(),
                    'rebuiltComponents':list(keys),'unselectedObjectsPreserved':len(untouched),'surfaceContract':BANK_APRON_SURFACE})
(candidate/'bank-apron-migration.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports))
