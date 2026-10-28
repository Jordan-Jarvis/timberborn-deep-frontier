"""Refresh Hatchery manifests from saved components; never rebuild geometry."""
import hashlib,json,math,zlib
from pathlib import Path
from hatchery_structure import DOORS,PLATFORMS,ROOMS,ACCESS,TERRACE,RAIL_RUNS,BANK_APRON_SURFACE,source
from hatchery_layout import H
from hatchery_selection import parts as picking_parts

def write_manifests(output,collection):
    """Requires component metadata stored when each selected mesh is rebuilt."""
    from blender_components import object_digest
    root=collection.objects['FishHatchery.Architecture']
    from native_building_assets import CACHE,model_pb2
    assembly=json.loads(root['df_native_assembly'])
    for definition in assembly['props']:
        prop=collection.objects[definition['name']]
        x,y,z=definition['position']
        if max(abs(a-b) for a,b in zip(prop.location,(-x,-y,z),strict=True))>1e-6:
            raise ValueError('Native runtime/preview root placement differs: '+prop.name)
        if max(abs(v-definition['scale']) for v in prop.scale)>1e-6 or abs(prop.rotation_euler.z+math.radians(definition['yaw']))>1e-6:
            raise ValueError('Native runtime/preview root scale or yaw differs: '+prop.name)
        model=model_pb2.Model();model.ParseFromString(zlib.decompress((CACHE/(definition['model']+'.timbermesh')).read_bytes()))
        for index,node in enumerate(model.nodes):
            if node.nodeAnimations:raise ValueError('Hatchery manifest validator requires its static native props')
            child=collection.objects[prop.name+'.'+node.name]
            transform=node
            expected_position=(-transform.position.x,-transform.position.z,transform.position.y)
            expected_scale=(transform.scale.x,transform.scale.z,transform.scale.y)
            expected_rotation=(transform.rotation.w,transform.rotation.x,transform.rotation.z,-transform.rotation.y)
            expected_parent=prop.name if node.parent==-1 else prop.name+'.'+model.nodes[node.parent].name
            if child.parent.name!=expected_parent or max(abs(a-b) for a,b in zip(child.location,expected_position,strict=True))>1e-6 or max(abs(a-b) for a,b in zip(child.scale,expected_scale,strict=True))>1e-6 or max(abs(a-b) for a,b in zip(child.rotation_quaternion,expected_rotation,strict=True))>1e-6:
                raise ValueError('Native child transform differs from original resource: '+child.name)
    expected=json.loads(root['df_native_object_digests'])
    for name,digest in expected.items():
        if object_digest(collection.objects[name])!=digest:raise ValueError('Native preview prop changed independently of its source placement: '+name)
    structures=[]
    for key in ('Headhouse.Shell',*('Deck.'+k for k in PLATFORMS)):
        obj=collection.objects['FishHatchery.'+key]
        structures.extend(json.loads(obj['df_structural_parts']))
    for name,bounds in {**ROOMS,**PLATFORMS}.items():
        matches=[p for p in structures if p['id']==name]
        if len(matches)!=1 or matches[0]['bounds']!=bounds:raise ValueError('Structural source/scene mismatch: '+name)
        if name in ('MainFrontApron','CanopyFrontApron'):
            if matches[0]['floorHeight']!=BANK_APRON_SURFACE['nativeFloor'] or matches[0]['wearingSurfaceHeight']!=BANK_APRON_SURFACE['wearingTop'] or matches[0]['backingSurfaceHeight']!=BANK_APRON_SURFACE['backingTop']:
                raise ValueError('Bank apron surface metadata requires its selected component rebuild: '+name)
    mounts=json.loads(collection.objects['FishHatchery.Headhouse.Windows']['df_window_mounts'])
    if len(mounts)!=7:raise ValueError('Expected seven explicitly mounted Hatchery windows')
    rails=json.loads(root['df_rail_manifest'])
    if len(rails['runs'])!=len(RAIL_RUNS):raise ValueError('Saved rail source contract is stale')
    for saved,(name,a,b,count) in zip(rails['runs'],RAIL_RUNS,strict=True):
        if saved['id']!=name or len(saved['panels'])!=count:raise ValueError('Saved rail segmentation differs: '+name)
        for i,panel in enumerate(saved['panels']):
            axis=next(j for j in range(3) if a[j]!=b[j])
            step=1 if b[axis]>a[axis] else -1
            first=[a[j]+(step*i if j==axis else 0) for j in range(3)]
            last=[a[j]+(step*(i+1) if j==axis else 0) for j in range(3)]
            if panel['gridAxis']!=axis or panel['gridCell']!=min(first[axis],last[axis]) or panel['gridStart']!=first or panel['gridEnd']!=last:
                raise ValueError('Native rail cell identity differs: '+name)
            from hatchery_structure import SOURCE_ORIGIN
            if panel['gridOrigin']!=SOURCE_ORIGIN:raise ValueError('Native rail source origin differs: '+name)
            for key,t in (('start',i/count),('end',(i+1)/count)):
                expected=source(tuple(a[j]+(b[j]-a[j])*t for j in range(3)))
                if panel[key]!=list(expected):
                    raise ValueError('Rail bounds changed without a selected rail migration: '+name)
    if set(rails['nodes'])!={obj.name for obj in collection.objects if obj.name.startswith('WalkwayRail.FishHatchery.')}:
        raise ValueError('Saved rail manifest does not own the exact current rail objects')
    def write(suffix,data):
        (output/('FishHatchery-'+suffix+'.json')).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    write('structure',{'schema':1,'coordinateSystem':'Native grid XYZ, Z up, before BaseZ','parts':structures+picking_parts()})
    write('layout',H);write('window-mounts',mounts);write('rail-manifest',rails)
    write('native-assembly',assembly)
    door={'id':'Door0','position':list(source(DOORS['Door0']['position'])),'outward':[0,-1],'width':1.,'internalConnection':'BuildingInterior'}
    write('visitor-manifest',{'scope':'Authored source positions; native verification follows installation',
        'doors':[door],'internalDoorNetwork':'BuildingInterior','requireAllDoorsConnectedInternally':True,'visitorSeats':[]})
    write('access-manifest',ACCESS)
    write('terrace-manifest',TERRACE)
    points=[obj.matrix_world@v.co for obj in collection.objects if obj.type=='MESH' for v in obj.data.vertices]
    low=[min(v[a] for v in points) for a in range(3)];high=[max(v[a] for v in points) for a in range(3)]
    write('study',{'scope':'Saved selective candidate scene; source bounds only','boundsMin':low,'boundsMax':high})
    write('height-manifest',{'units':'1 Blender Z unit = 1 Timberborn grid layer','baseZ':1,
        'scope':'Source geometry; native paths pending integration','walkableDeckLayers':[0],'entranceLayers':[0],'artHeight':high[2]})
    return {'structuralParts':len(structures)+len(picking_parts()),'windows':len(mounts),'railObjects':len(rails['nodes'])}
