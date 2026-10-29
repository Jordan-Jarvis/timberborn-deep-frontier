"""Rebuild only explicitly selected assets in an existing Blender source.

--initialize separates known legacy portal faces once, without generating a
building. All regular edits require existing named component objects.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from building_components import recipes,legacy_door,UV_PROFILES
from blender_components import object_digest,separate_components
from industrial_budget import MODELS as BUDGET_MODELS,BEVEL as BUDGET_BEVEL
from enclosed_cull import SHELL_MODELS
from industrial_kit import LEAN_MODELS


def initialize(model,builders,architecture):
    sources=json.loads(architecture['df_source_locations'])
    attribute=architecture.data.attributes['df_source']
    portal_faces={p.index for p in architecture.data.polygons
                  if ':building_portal' in sources[attribute.data[p.index].value]}
    components=[];claimed=set()
    # This is an explicit one-time migration using source provenance and the
    # canonical door definitions. Ambiguous/missing faces stop the migration.
    for key,builder in builders.items():
        g=legacy_door(model,key);points=[Vector(v) for v in g.vertices]
        low=Vector(tuple(min(v[a] for v in points)-2e-6 for a in range(3)))
        high=Vector(tuple(max(v[a] for v in points)+2e-6 for a in range(3)))
        indices=[i for i in sorted(portal_faces) if all(
            all(low[a]<=architecture.data.vertices[v].co[a]<=high[a] for a in range(3))
            for v in architecture.data.polygons[i].vertices)]
        if len(indices)!=len(g.faces) or indices!=list(range(indices[0],indices[-1]+1)):
            raise ValueError('Legacy component is missing, ambiguous or noncontiguous: '+key)
        if claimed.intersection(indices):raise ValueError('Legacy components overlap')
        claimed.update(indices)
        # Validate the exact expected face shape/material before splitting.
        for index,face,material in zip(indices,g.faces,g.materials,strict=True):
            polygon=architecture.data.polygons[index]
            if polygon.material_index!=material or len(polygon.vertices)!=len(face):
                raise ValueError('Legacy door topology differs: '+key)
            actual=[architecture.data.vertices[i].co for i in polygon.vertices]
            expected=[points[i] for i in face]
            if any(min((p-q).length for q in actual)>2e-6 for p in expected):
                raise ValueError('Legacy door placement differs: '+key)
        components.append({'name':g.name,'faceRange':[indices[0],indices[-1]+1]})
    if claimed!=portal_faces:raise ValueError('Unowned legacy door faces remain')
    return separate_components(architecture,components)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',required=True)
    parser.add_argument('--components',required=True,help='Exact comma-separated component IDs; no all/default selection')
    parser.add_argument('--initialize',action='store_true',help='Explicit one-time lossless separation of legacy authored doors')
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if not args.report.is_absolute():raise ValueError('Component rebuild report must be an absolute path')
    builders=recipes(args.model);selected=args.components.split(',')
    if len(selected)!=len(set(selected)) or any(key not in builders for key in selected):
        raise ValueError('Choose unique authored components: '+', '.join(builders))
    path=ROOT/'src/DeepFrontier/Art/Source'/f'{args.model}-ReferenceStudy.blend'
    before_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    started=time.perf_counter();bpy.ops.wm.open_mainfile(filepath=str(path))
    collection=bpy.data.collections[args.model+'.ReferenceStudy']
    architecture=bpy.data.objects[args.model+'.Architecture']
    migration=None
    if args.initialize:
        migration=initialize(args.model,builders,architecture)
    expected_names={args.model+'.'+key for key in builders}
    actual_names={obj.name for obj in collection.objects if 'df_component' in obj}
    if expected_names!=actual_names:raise ValueError('Scene component registry differs from source; initialize it explicitly')
    replaced_names={args.model+'.'+key for key in selected}
    untouched={obj.name:object_digest(obj) for obj in bpy.data.objects if obj.name not in replaced_names}
    face_counts={}
    for key in selected:
        name=args.model+'.'+key;old=bpy.data.objects[name]
        if old['df_component']!=name or old.parent is not None or tuple(old.location)!=(0,0,0):
            raise ValueError('Unexpected authored component transform: '+name)
        g=builders[key]();materials=list(architecture.data.materials)
        old_mesh=old.data
        bpy.data.objects.remove(old,do_unlink=True)
        if old_mesh.users==0:bpy.data.meshes.remove(old_mesh)
        # Triangle-budget models (industrial_budget.py) carry no bevel modifier.
        bevel=BUDGET_BEVEL if args.model in BUDGET_MODELS else 0 if args.model in SHELL_MODELS else .012
        # and are built as shells, as render_reference_studies.py builds them
        # (a component is culled only by its own volumes, so this matches).
        if args.model in BUDGET_MODELS or args.model in SHELL_MODELS:g.cull_enclosed=True
        g.cull_small_hidden=args.model in SHELL_MODELS or args.model in LEAN_MODELS
        obj=g.build(collection,materials,bevel,UV_PROFILES[args.model]);obj['df_component']=name
        if args.model=='FishHatchery':
            obj['df_structural_parts']=json.dumps(g.structural_parts)
            obj['df_window_mounts']=json.dumps(g.window_mounts)
        face_counts[key]=len(obj.data.polygons)
    if set(bpy.data.objects.keys())!=set(untouched)|replaced_names:
        raise RuntimeError('Targeted rebuild changed the scene object inventory')
    changed=[name for name,digest in untouched.items() if object_digest(bpy.data.objects[name])!=digest]
    if changed:raise RuntimeError('Targeted rebuild changed unselected objects: '+str(changed))
    if hashlib.sha256(path.read_bytes()).hexdigest()!=before_sha:
        raise RuntimeError('Another process changed this source while it was open; refusing to overwrite its work')
    manifests=None
    if args.model=='FishHatchery':
        from hatchery_manifests import write_manifests
        manifests=write_manifests(ROOT/'outputs/reference-studies',collection)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    report={'schema':1,'model':args.model,'source':str(path),'beforeSha256':before_sha,
            'afterSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'selectedComponents':selected,'generatedFaces':face_counts,
            'untouchedObjectsVerified':len(untouched),'unchangedObjectDigests':untouched,
            'migration':migration,'manifests':manifests,'elapsedSeconds':round(time.perf_counter()-started,3),
            'wholeBuildingGeneratorCalled':False,'renderedFrames':0}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='unchangedObjectDigests'}),flush=True)


if __name__=='__main__':main()
