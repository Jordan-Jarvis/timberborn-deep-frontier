"""One-time, hash-checked selective migration into a separate candidate scene."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from blender_components import object_digest,surface_digest,separate_components
from hatchery_components import recipes,rails
from hatchery_structure import ORIGIN,BASE_Z,SOURCE_ORIGIN,DOORS,source
from hatchery_layout import H

RANGES={
 'Deck.MainFrontApron':[0,192],'Deck.MainApron':[192,384],
 'Headhouse.Shell':[384,10399],'Headhouse.DoorLamps':[10399,10531],
 'Headhouse.RoofBearing':[10531,10535],'Headhouse.Roof':[10535,14590],
 'Headhouse.Windows':[14590,14954],'Headhouse.RoofVent':[14954,15002],
 'Deck.LeftDock':[15454,15496],'Deck.CentreDock':[15496,15544],
 'Deck.RightDock':[15544,15628],'Deck.RearDock':[15628,15790],
 'Dock.Supports':[15790,22612],'Legacy.DockCrossbeams':[22612,22824],
 'Deck.CanopyFrontApron':[28528,28612],'Deck.CanopyBaseApron':[28612,28696],
 'Dock.Lamps':[42660,44356],
}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def box(bounds):
    return {'center':[(bounds[i]+bounds[i+3])/2 for i in range(3)],
            'size':[bounds[i+3]-bounds[i] for i in range(3)]}

def payload_hash(obj,start,end):
    sources=json.loads(obj['df_source_locations']);attr=obj.data.attributes['df_source'];payload=[]
    for f in list(obj.data.polygons)[start:end]:
        points=[obj.matrix_world@obj.data.vertices[i].co for i in f.vertices]
        coords=[(-v.x,-v.y,v.z) for v in points]
        uv=[list(obj.data.uv_layers.active.data[i].uv) for i in f.loop_indices]
        payload.append([coords,uv,obj.data.materials[f.material_index].name,sources[attr.data[f.index].value]])
    return hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-source-sha256',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=a.output
    if not out.is_absolute():raise ValueError('Absolute candidate output directory required')
    source_path=ROOT/'src/DeepFrontier/Art/Source/FishHatchery-ReferenceStudy.blend'
    if sha(source_path)!=a.expected_source_sha256:raise ValueError('Canonical source changed before migration')
    if (out/'FishHatchery-ReferenceStudy.blend').exists():raise ValueError('Candidate already exists; rebuild its explicitly selected component instead')
    out.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(source_path));bpy.context.scene.frame_set(1)
    collection=bpy.data.collections['FishHatchery.ReferenceStudy'];arch=bpy.data.objects['FishHatchery.Architecture']
    reference=json.loads((ROOT/'outputs/next-building-audit/hatchery-source-provenance.json').read_text())
    audited=next(o for o in reference['objects'] if o['name']==arch.name)
    if len(arch.data.polygons)!=audited['faces']:raise ValueError('Architecture face inventory changed')
    for record in audited['extractionRanges']:
        if payload_hash(arch,*record['rangeExclusive'])!=record['facePayloadSha256']:
            raise ValueError('Saved source provenance/UV/geometry changed: '+record['name'])
    original={o.name:object_digest(o) for o in bpy.data.objects}
    old_rails={o.name for o in collection.objects if o.name.startswith('WalkwayRail.FishHatchery.')}
    if len(old_rails)!=65:raise ValueError('Expected the audited 65 legacy rail objects')
    move_name='NativeBarrel1'
    untouched={name:d for name,d in original.items() if name not in old_rails|{arch.name,'FishHatchery.Door.Door0',move_name}}
    separation=separate_components(arch,[{'name':'FishHatchery.'+k,'faceRange':v} for k,v in RANGES.items()])
    retained=surface_digest(arch)
    obsolete=bpy.data.objects['FishHatchery.Legacy.DockCrossbeams'];bpy.data.objects.remove(obsolete,do_unlink=True)
    materials=list(arch.data.materials);parts=[];mounts=[];generated={}
    for key,builder in recipes().items():
        name='FishHatchery.'+key;old=bpy.data.objects[name];mesh=old.data
        bpy.data.objects.remove(old,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
        g=builder();obj=g.build(collection,materials,.012,'civic-native');obj['df_component']=name
        if g.window_mounts:obj['df_window_mounts']=json.dumps(g.window_mounts)
        if g.structural_parts:obj['df_structural_parts']=json.dumps(g.structural_parts)
        parts.extend(g.structural_parts);mounts.extend(g.window_mounts);generated[key]=len(g.faces)
    for name in old_rails:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    rail=rails()
    for g in rail.meshes:g.build(collection,materials,.012,'civic-native')
    # This explicit, approved prop translation is the only retained-object move.
    moved=bpy.data.objects[move_name];moved.location.y=0
    if surface_digest(arch)!=retained:raise ValueError('Retained pens/machinery surfaces changed')
    for name,digest in untouched.items():
        if object_digest(bpy.data.objects[name])!=digest:raise ValueError('Unselected object changed: '+name)
    arch['df_components']=json.dumps(['FishHatchery.'+k for k in recipes()])
    assembly=json.loads((ROOT/'outputs/reference-studies/FishHatchery-native-assembly.json').read_text())
    barrel=next(p for p in assembly['props'] if p['name']=='NativeBarrel1')
    if barrel['position']!=[3.65,.3,.29865744]:raise ValueError('Barrel source placement changed')
    barrel['position']=[3.65,0,.29865744]
    arch['df_native_assembly']=json.dumps(assembly)
    arch['df_native_object_digests']=json.dumps({obj.name:object_digest(obj) for obj in collection.objects if 'native_resource' in obj or 'liquid_surface' in obj})
    arch['df_rail_manifest']=json.dumps(rail.manifest())
    from hatchery_selection import parts as picking_parts
    parts.extend(picking_parts())
    write(out/'FishHatchery-structure.json',{'schema':1,'coordinateSystem':'Native grid XYZ, Z up, before BaseZ','parts':parts})
    write(out/'FishHatchery-window-mounts.json',mounts)
    write(out/'FishHatchery-native-assembly.json',assembly)
    write(out/'FishHatchery-rail-manifest.json',rail.manifest())
    write(out/'FishHatchery-layout.json',H)
    visitor=json.loads((ROOT/'outputs/reference-studies/FishHatchery-visitor-manifest.json').read_text())
    visitor['doors']=[{'id':'Door0','position':list(source(DOORS['Door0']['position'])),'outward':[0,-1],'width':1.,'internalConnection':'BuildingInterior'}]
    write(out/'FishHatchery-visitor-manifest.json',visitor)
    bpy.context.view_layer.update()
    vertices=[obj.matrix_world@v.co for obj in collection.objects if obj.type=='MESH' for v in obj.data.vertices]
    study=json.loads((ROOT/'outputs/reference-studies/FishHatchery-study.json').read_text())
    study['boundsMin']=[min(v[i] for v in vertices) for i in range(3)];study['boundsMax']=[max(v[i] for v in vertices) for i in range(3)]
    write(out/'FishHatchery-study.json',study)
    from hatchery_manifests import write_manifests
    write_manifests(out,collection)
    if sha(source_path)!=a.expected_source_sha256:raise ValueError('Canonical source changed during candidate creation')
    candidate=out/'FishHatchery-ReferenceStudy.blend';bpy.ops.wm.save_as_mainfile(filepath=str(candidate))
    report={'source':str(source_path),'sourceSha256':a.expected_source_sha256,'candidate':str(candidate),
            'candidateSha256':sha(candidate),'wholeBuildingGeneratorCalled':False,'renderedFrames':0,
            'separation':separation,'retainedArchitectureSurfaceSha256':retained,
            'unchangedObjectDigests':untouched,'preservedObjectsVerified':len(untouched),
            'changedComponents':generated,'removedObsoleteComponents':['Legacy.DockCrossbeams'],
            'oldRailObjects':len(old_rails),'newRailObjects':len(rail.meshes),
            'explicitNativePropMove':{'name':move_name,'sourceDelta':[0,-.30,0]}}
    write(out/'migration-report.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('unchangedObjectDigests','separation')}),flush=True)

if __name__=='__main__':main()
