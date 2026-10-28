"""One-time removal of the Hatchery's fixed-length dock short posts.

AdaptiveSupportsSpec piles replace them at runtime (tools/waterside_sites.json,
waterside_supports.py). Only the exact legacy 'FishHatchery.Dock.Supports'
object is removed; every other object is digest-checked before saving. No
building generator, render or other geometry rebuild is invoked.

blender -b --python-exit-code 1 --python migrate_hatchery_adaptive_supports.py -- --report <absolute json>
"""
import argparse,hashlib,json,sys,time
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from blender_components import object_digest
from hatchery_components import recipes

NAME='FishHatchery.Dock.Supports'
# Exact legacy recipe: six posts at these native-grid X/Y positions, each a
# timber post with two iron collars (centre/size in native-grid coordinates).
LEGACY_POSTS=[(.10,3.90),(.10,7.90),(3.10,6.90),(7.90,3.90),(7.90,7.90),(5.90,7.90)]
LEGACY_BOXES=[{'center':[x,y,z],'size':size} for x,y in LEGACY_POSTS
              for z,size in ((.495,[.16,.16,.55]),(.265,[.18,.18,.07]),(.725,[.18,.18,.07]))]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if not args.report.is_absolute():raise ValueError('Report path must be absolute')
    path=ROOT/'src/DeepFrontier/Art/Source/FishHatchery-ReferenceStudy.blend'
    before=hashlib.sha256(path.read_bytes()).hexdigest();started=time.perf_counter()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    collection=bpy.data.collections['FishHatchery.ReferenceStudy']
    expected={'FishHatchery.'+key for key in recipes()}
    actual={obj.name for obj in collection.objects if 'df_component' in obj}
    if actual!=expected|{NAME} or NAME in expected:
        raise ValueError('Scene components are not the exact pre-migration registry plus legacy short posts')
    legacy=bpy.data.objects[NAME]
    parts=json.loads(legacy['df_structural_parts'])
    if parts!=[{'id':'DockShortPosts','kind':'posts','pickingBoxes':LEGACY_BOXES}]:
        raise ValueError('Legacy short-post component differs from its recorded recipe')
    if legacy.parent is not None or tuple(legacy.location)!=(0,0,0) or len(legacy.data.polygons)!=18*6:
        raise ValueError('Legacy short-post object transform/topology differs')
    arch=bpy.data.objects['FishHatchery.Architecture']
    untouched={obj.name:object_digest(obj) for obj in bpy.data.objects if obj.name not in (NAME,arch.name)}
    arch_before=object_digest(arch);old_components=arch.get('df_components')
    removed={'name':NAME,'faces':len(legacy.data.polygons),'digest':object_digest(legacy)}
    mesh=legacy.data;bpy.data.objects.remove(legacy,do_unlink=True)
    if mesh.users==0:bpy.data.meshes.remove(mesh)
    if 'df_components' in arch:
        names=json.loads(arch['df_components'])
        if NAME not in names:raise ValueError('Architecture component list lacks the legacy short posts')
        arch['df_components']=json.dumps([n for n in names if n!=NAME])
    if set(bpy.data.objects.keys())!=set(untouched)|{arch.name}:raise RuntimeError('Object inventory changed beyond the legacy posts')
    changed=[n for n,d in untouched.items() if object_digest(bpy.data.objects[n])!=d]
    # The architecture object may differ only by its component list.
    new_components=arch.get('df_components')
    if old_components is not None:arch['df_components']=old_components
    if object_digest(arch)!=arch_before:changed.append(arch.name)
    if new_components is not None:arch['df_components']=new_components
    if changed:raise RuntimeError('Unselected objects changed: '+str(changed))
    if {obj.name for obj in collection.objects if 'df_component' in obj}!=expected:raise RuntimeError('Registry mismatch after removal')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=before:
        raise RuntimeError('Another process changed this source while it was open; refusing to overwrite its work')
    from hatchery_manifests import write_manifests
    manifests=write_manifests(ROOT/'outputs/reference-studies',collection)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    report={'schema':1,'model':'FishHatchery','source':str(path),'beforeSha256':before,
            'afterSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'removed':removed,
            'untouchedObjectsVerified':len(untouched)+1,'manifests':manifests,
            'elapsedSeconds':round(time.perf_counter()-started,3),'wholeBuildingGeneratorCalled':False,'renderedFrames':0}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
