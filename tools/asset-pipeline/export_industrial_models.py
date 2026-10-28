"""Official Timbermesh export of reviewed scenes, with explicit grid rail cuts.

Never moves a door or scales artwork. Grid origin, safe routes and openings are
authored in industrial_layouts.py. Studio objects are excluded from exports.
"""
import argparse, json, math, sys, shutil
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
PLUGIN=ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'
sys.path.insert(0,str(PLUGIN))
import timbermesh_exporter as exporter
from industrial_layouts import LAYOUTS
from civic_layouts import LAYOUTS as CIVIC_LAYOUTS
from pit_layouts import LAYOUTS as PIT_LAYOUTS
from structural_layouts import LAYOUTS as STRUCTURAL_LAYOUTS
from hydro_layout import LAYOUTS as HYDRO_LAYOUTS
from research_layouts import LAYOUTS as RESEARCH_LAYOUTS
from frontier_architecture import Geometry, WOOD
from quarry_isometric_geometry import platform
from reference_materials import NATIVE_INDUSTRIAL_MATERIALS
from housing_railing import panel as housing_panel
import static_mesh_merge

OUT=ROOT/'outputs/industrial-integration'
ART=ROOT/'src/DeepFrontier/AssetBundles/Resources/Materials/DeepFrontierIndustrial'

def bake_materials(materials):
    """Bake the authored base-color shader into repeatable material tiles."""
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    devices=[d for d in prefs.devices if d.type=='OPTIX' and d.name=='NVIDIA GeForce RTX 2060']
    if len(devices)!=1:raise RuntimeError('RTX 2060 OptiX device required')
    for d in prefs.devices:d.use=d in devices
    scene.cycles.device='GPU'
    bpy.ops.mesh.primitive_plane_add(size=1,location=(0,0,-50));plane=bpy.context.object
    catalog=[]
    for i,source in enumerate(materials):
        name=f'DFIndustrial{i:02d}';mat=source.copy();mat.name=name+'.Bake'
        plane.data.materials.clear();plane.data.materials.append(mat)
        nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes['Principled BSDF']
        color=bs.inputs['Base Color'];output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
        emit=nodes.new('ShaderNodeEmission')
        if color.is_linked:links.new(color.links[0].from_socket,emit.inputs['Color'])
        else:emit.inputs['Color'].default_value=color.default_value
        links.new(emit.outputs[0],output.inputs['Surface'])
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.new(name,512,512,alpha=False)
        nodes.active=tex
        bpy.ops.object.select_all(action='DESELECT');plane.select_set(True);bpy.context.view_layer.objects.active=plane
        bpy.ops.object.bake(type='EMIT',margin=8)
        tex.image.filepath_raw=str(ART/(name+'.BaseColor.png'));tex.image.file_format='PNG';tex.image.save()
        original=source.node_tree.nodes['Principled BSDF']
        catalog.append(dict(name=name,source=source.name,
            metallic=original.inputs['Metallic'].default_value,
            smoothness=1-original.inputs['Roughness'].default_value,
            emission=original.inputs['Emission Strength'].default_value))
        print('BAKED',name,source.name,flush=True)
        bpy.data.materials.remove(mat)
    bpy.data.objects.remove(plane,do_unlink=True)
    (ART/'material-catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')

def export_model(ident,bake):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'src/DeepFrontier/Art/Source'/(ident+'-ReferenceStudy.blend')))
    collection=bpy.data.collections[ident+'.ReferenceStudy']
    # Preview copies of shipped assets are not mod payloads. The blueprint
    # points to their original game resources and creates reservoir planes.
    for obj in list(collection.objects):
        if 'native_resource' in obj or 'liquid_surface' in obj:
            bpy.data.objects.remove(obj,do_unlink=True)
    civic=ident in CIVIC_LAYOUTS
    structural=ident in STRUCTURAL_LAYOUTS
    hydro=ident in HYDRO_LAYOUTS
    research=ident in RESEARCH_LAYOUTS
    extended_native=civic or structural or hydro or research or ident=='ConcreteMixer' or ident in PIT_LAYOUTS
    layouts={**LAYOUTS,**CIVIC_LAYOUTS,**PIT_LAYOUTS,**STRUCTURAL_LAYOUTS,**HYDRO_LAYOUTS,**RESEARCH_LAYOUTS}
    if len(layouts)!=len(LAYOUTS)+len(CIVIC_LAYOUTS)+len(PIT_LAYOUTS)+len(STRUCTURAL_LAYOUTS)+len(HYDRO_LAYOUTS)+len(RESEARCH_LAYOUTS):
        raise ValueError('Duplicate canonical model registration')
    layout=layouts[ident];ox,oy,oz=layout['origin']
    deck_mode=layout['deckMode']
    if deck_mode not in ('PlayerPlacedPaths','BuiltInWalkways','None'):
        raise ValueError('Unsupported authored deck mode '+str(deck_mode))
    if deck_mode=='None' and any(layout[key] for key in ('nodes','edges','ports')):
        raise ValueError('No-deck registration contains walking routes: '+ident)
    base_z=layout['baseZ']
    architecture=bpy.data.objects[ident+'.Architecture']
    materials=list(architecture.data.materials)
    expected=32
    if len(materials)!=expected:raise ValueError(f'Expected {expected} source materials, got {len(materials)}')
    if bake:raise ValueError('The 32-slot native style reuses existing custom tiles and original game materials; do not bake native atlases')
    catalog=json.loads((ART/'material-catalog.json').read_text())
    if len(catalog)!=27:raise ValueError('The industrial palette requires exactly 27 ordered slots')
    native=dict(NATIVE_INDUSTRIAL_MATERIALS)
    native.update({2:'BaseMetal.IronTeeth',7:'Details.IronTeeth',11:'Water',27:'Plaster_White.IronTeeth',28:'Plaster_Orange.IronTeeth',29:'IrregularPlanks_MetalForged.IronTeeth',30:'WindowsAtlas.IronTeeth',31:'BaseWood_Brown.Folktails'})
    for index,material in enumerate(materials):
        if index>=27:
            if material.name!=native[index]:raise ValueError('Civic native material changed at source')
            continue
        entry=catalog[index]
        if entry['name']!=f'DFIndustrial{index:02d}':raise ValueError('Industrial palette slot ID mismatch')
        if index in native:
            if material.name!=native[index]:raise ValueError('Native material binding changed at source')
        else:material.name=entry['name']
    rails=json.loads((ROOT/'outputs/reference-studies'/(ident+'-rail-manifest.json')).read_text())
    # Split horizontal beam spans at exact authored grid boundaries. Existing
    # posts and all architecture stay in their reviewed positions.
    by_run={};post_positions={}
    for run in rails['runs']:
        chunks=[]
        for panel in run['panels']:
            a,b=panel['start'],panel['end'];axis=0 if a[0]!=b[0] else 1
            if a[1-axis]!=b[1-axis]:raise ValueError('Only axis-aligned guardrails are authored')
            offset=layout['origin'][axis];cuts=[a[axis],b[axis]]
            grid_fields={'gridStart','gridEnd','gridOrigin','gridAxis','gridCell'}
            authored_grid=grid_fields.intersection(panel)
            if authored_grid:
                if authored_grid!=grid_fields:raise ValueError('Incomplete authored native-cell rail contract')
                ga,gb=panel['gridStart'],panel['gridEnd'];go=panel['gridOrigin']
                if go!=[ox,oy,oz+base_z]:raise ValueError('Rail native/source origin differs from its building registration')
                if len(ga)!=3 or len(gb)!=3 or any(type(v) is not int for v in ga+gb):
                    raise ValueError('Native-cell rail endpoints must be authored integer coordinates')
                if sum(abs(v-w) for v,w in zip(ga,gb,strict=True))!=1 or ga[2]!=gb[2]:
                    raise ValueError('Native-cell rail must span exactly one horizontal grid edge')
                if a!=[v-o for v,o in zip(ga,go,strict=True)] or b!=[v-o for v,o in zip(gb,go,strict=True)]:
                    raise ValueError('Rail artwork endpoints differ from their authored native-cell endpoints')
                if panel['gridAxis']!=axis or type(panel['gridCell']) is not int or panel['gridCell']!=min(ga[axis],gb[axis]):
                    raise ValueError('Rail native-cell identity differs from its authored endpoints')
                # Already authored as a whole native cell. Preserve that
                # identity; do not infer cuts from float32 preview vertices.
                chunk_cells=[panel['gridCell']]
            else:
                for k in range(math.floor(min(a[axis],b[axis])+offset)+1,math.ceil(max(a[axis],b[axis])+offset)):
                    cuts.append(k-offset)
                cuts=sorted(cuts,reverse=b[axis]<a[axis])
                chunk_cells=[math.floor((lo+hi)/2+offset) for lo,hi in zip(cuts,cuts[1:])]
            bpy.data.objects.remove(bpy.data.objects[panel['node']],do_unlink=True)
            for i,(lo,hi) in enumerate(zip(cuts,cuts[1:])):
                p=list(a);q=list(b);p[axis]=lo;q[axis]=hi
                name=panel['node']+f'.CellPart{i}'
                g=Geometry(name)
                housing_panel(g,p[:2],q[:2],p[2])
                g.build(collection,materials,0,'civic-native')
                chunks.append(dict(name=name,axis=axis,cell=chunk_cells[i],a=p,b=q))
            post_positions[panel['startPost']]=a;post_positions[panel['endPost']]=b
        by_run[run['id']]=chunks
    openings=[]
    for p in layout['ports']:
        inside=p['inside'];outside=p['outside'];dx=outside[0]-inside[0];dy=outside[1]-inside[1]
        tangent=1 if dx else 0;cell=inside[tangent]
        chunks=[c for c in by_run[p['run']] if c['cell']==cell]
        if not chunks:raise ValueError(f'{ident}/{p["id"]} has no rail segments')
        names=[c['name'] for c in chunks]
        # A corner cell can contain portions of two runs. Open only the pieces
        # contained in this cell, including its short perpendicular return.
        for run_chunks in by_run.values():
            for c in run_chunks:
                mid=[(c['a'][a]+c['b'][a])/2+layout['origin'][a] for a in range(2)]
                if inside[0]<mid[0]<inside[0]+1 and inside[1]<mid[1]<inside[1]+1 and abs(c['a'][2]+oz+base_z-inside[2])<.001:
                    names.append(c['name'])
        # Posts strictly inside an open cell disappear. Boundary/corner posts stay.
        for name,pos in post_positions.items():
            t=pos[tangent]+layout['origin'][tangent]
            if cell+.075<t<cell+.925 and any(abs(pos[1-tangent]-c['a'][1-tangent])<.001 and abs(pos[2]+oz+base_z-inside[2])<.001 for c in chunks):
                names.append(name)
            if all(inside[a]+.075<pos[a]+layout['origin'][a]<inside[a]+.925 for a in range(2)) and abs(pos[2]+oz+base_z-inside[2])<.001:
                names.append(name)
        # A connection-only plank lip joins the reviewed deck to the tile edge.
        # It never extends into the neighbor's tile or changes the building layout.
        normal=1-tangent;rail=chunks[0]['a'][normal]+layout['origin'][normal]
        boundary=inside[normal]+(1 if dx+dy>0 else 0)
        approach=p['approach']
        shown=[]
        if deck_mode=='BuiltInWalkways':
            lane=next(n['point'] for n in layout['nodes'] if n['cell']==inside)
            low=min(rail,boundary,lane[normal]+layout['origin'][normal]);high=max(rail,boundary,lane[normal]+layout['origin'][normal])
            if high-low>.025:
                center=[0,0,inside[2]-base_z-oz-.045];extent=[0,0,.09]
                center[tangent]=cell+.5-layout['origin'][tangent];extent[tangent]=.98
                center[normal]=(low+high)/2-layout['origin'][normal];extent[normal]=high-low+.03
                g=Geometry('WalkwayJoin.'+p['id']);g.box(center,extent,WOOD);g.build(collection,materials,.012);shown=[g.name]
        openings.append(dict(Id=p['id'],Inside=xyz(inside),Outside=xyz(outside),ApproachPosition=xyz([approach[0]+ox,approach[2]+oz,approach[1]+oy]),HiddenNodes=sorted(set(names)),ShownNodes=shown))
    # Empty transforms retain native worker idle slots, using existing doorways.
    for i,point in enumerate(layout['idle']):
        empty=bpy.data.objects.new(f'#Slot#Entrance{i}',None);collection.objects.link(empty)
        empty.location=(-point[0],-point[1],point[2]);empty.rotation_euler=(0,0,math.pi)
        if ident in ('FisheryWorks','FishHatchery'):
            facing=layout['idleFacing'][i]
            empty.rotation_euler=(0,0,math.atan2(-facing[0],facing[1]))
    if civic:
        visitors=json.loads((ROOT/'outputs/reference-studies'/(ident+'-visitor-manifest.json')).read_text())
        for seat in visitors['visitorSeats']:
            empty=bpy.data.objects.new('#Slot#'+seat['id'],None);collection.objects.link(empty)
            x,y,z=seat['position'];empty.location=(-x,-y,z)
            empty.rotation_euler=(0,0,math.atan2(-seat['facing'][0],seat['facing'][1]))
        for i,(x,y,z) in enumerate(layout['staffSlots']):
            empty=bpy.data.objects.new(f'#Slot#Staff{i}',None);collection.objects.link(empty)
            empty.location=(-x,-y,z);empty.rotation_euler=(0,0,math.pi)
    # AdaptiveSupports runtime templates: exactly one #SupportSegment and one
    # #SupportFoot node, origin at a cell's bottom centre. They are parked at
    # an authored anchor buried below a land cell: the finished model hides
    # them, and the copied construction-stage model keeps them underground.
    import waterside_supports
    if ident in waterside_supports.models():
        for node,g,anchor in waterside_supports.templates(ident):
            if node in bpy.data.objects:raise ValueError('Support template node name already used: '+node)
            obj=g.build(collection,materials,.012,'civic-native')
            if obj.name!=node:raise ValueError('Support template must export as exactly '+node)
            ax,ay,az=anchor
            obj.location=(ox-(ax+.5),oy-(ay+.5),az-base_z-oz)
    root=bpy.data.objects.new('IndustrialGridOrigin',None);collection.objects.link(root)
    root.location=(-ox,-oy,oz)
    for obj in list(collection.objects):
        if obj!=root and obj.parent is None:obj.parent=root
        if obj.animation_data and obj.animation_data.action:
            # Official exporter contract: '#' identifies an independent animated
            # root even when it has the shared grid-origin parent.
            if obj.name.startswith('#'):raise ValueError('Review scene must use canonical, unprefixed part names')
            obj.name='#'+obj.name
    targets={'MineralQuarry':['SandstoneQuarry','LimestoneQuarry'],'StoneCrusher':['StoneCrusher'],'CementKiln':['CementKiln'],'ConcreteMixer':['ConcreteMixer'],'Restaurant':['Restaurant'],'FisheryWorks':['FisheryWorks'],'FishHatchery':['FishHatchery'],'Hospital':['Hospital'],'GroceryStore':['GroceryStore'],'SandstonePit':['SandstonePit'],'LimestonePit':['LimestonePit'],**{name:[name] for name in STRUCTURAL_LAYOUTS},**{name:[name] for name in HYDRO_LAYOUTS},**{name:[name] for name in RESEARCH_LAYOUTS}}[ident]
    # Preview cost: each static part was its own node and MeshRenderer
    # (static_mesh_merge.py). Rail and join parts that every opening toggles
    # together become one node, and the walkway spec written below names it.
    scene_objects=len(collection.objects)
    rail_groups,rail_remap=static_mesh_merge.opening_groups(openings,'WalkwayGroup.'+ident)
    rail_joined=static_mesh_merge.join_groups(collection,root,rail_groups)
    static_mesh_merge.remap_openings(openings,rail_remap,rail_joined)
    # Route/opening checks (check_industrial_*.py) read the -Game.blend scene
    # object by object with the spec's rail names, so it is saved before the
    # remaining static parts are joined.
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'src/DeepFrontier/Art/Source'/(ident+'-Game.blend')))
    rail_nodes=[name for o in openings for name in o['HiddenNodes']+o['ShownNodes']]
    merge=static_mesh_merge.merge_static_meshes(collection,root,static_mesh_merge.referenced_names(rail_nodes))
    merge['railGroups']={group:dict(parts=rail_groups[group],nodes=nodes) for group,nodes in rail_joined.items()}
    settings=exporter.ExportSettings(bpy.context,False,True,False)
    exported=None
    for target in targets:
        # Civic exports remain an integration artifact until their behavior and
        # occupancy blueprints pass. Never pair a grand mesh with the old 3x3 data.
        civic_categories={'Restaurant':'Food','FisheryWorks':'Food','FishHatchery':'Food','Hospital':'Wellbeing','GroceryStore':'Food'}
        folder=(ROOT/'outputs/civic-integration/Data/Buildings'/civic_categories[ident]/target if civic
                else ROOT/'outputs/structural-integration/Data/Buildings/Platforms'/target if structural
                else ROOT/'outputs/hydro-integration/Data/Buildings/Power'/target if hydro
                else ROOT/'outputs/research-integration/Data/Buildings/Science'/target if research
                else ROOT/'src/DeepFrontier/Data/Buildings/Metal'/target)
        folder.mkdir(parents=True,exist_ok=True)
        for suffix in ['Model','ConstructionStage0.Model']:
            destination=folder/(target+'.IronTeeth.'+suffix+'.timbermesh')
            if exported is None:
                exporter.Exporter.export_collection(collection,str(destination),settings)
                exported=destination
            else:shutil.copyfile(exported,destination)
    if deck_mode=='PlayerPlacedPaths':
        spec=dict(Openings=openings,Doors=[{k:xyz(v) for k,v in d.items()} for d in layout['doorLinks']])
        spec_suffix='platform-deck'
    else:
        spec=dict(Openings=openings,Waypoints=[dict(Cell=xyz(n['cell']),Position=xyz([n['point'][0]+ox,n['point'][2]+oz,n['point'][1]+oy])) for n in layout['nodes']])
        spec_suffix='walkway'
    output=ROOT/'outputs/civic-integration' if civic else ROOT/'outputs/structural-integration' if structural else ROOT/'outputs/hydro-integration' if hydro else ROOT/'outputs/research-integration' if research else OUT
    output.mkdir(parents=True,exist_ok=True)
    (output/(ident+'-'+spec_suffix+'.json')).write_text(json.dumps(spec,indent=2)+'\n')
    (output/(ident+'-export.json')).write_text(json.dumps(dict(source=ident,targets=targets,origin=layout['origin'],size=layout['size'],openings=len(openings),objects=scene_objects,animationFrames=bpy.context.scene.frame_end),indent=2)+'\n')
    (output/(ident+'-static-merge.json')).write_text(json.dumps(dict(source=ident,targets=targets,**merge),indent=2)+'\n')
    print('EXPORTED',ident,flush=True)

def xyz(p):return dict(X=p[0],Y=p[1],Z=p[2])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--models',default='StoneCrusher,CementKiln,MineralQuarry');parser.add_argument('--bake',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);OUT.mkdir(parents=True,exist_ok=True);ART.mkdir(parents=True,exist_ok=True)
    for i,ident in enumerate(args.models.split(',')):export_model(ident,args.bake and i==0)
