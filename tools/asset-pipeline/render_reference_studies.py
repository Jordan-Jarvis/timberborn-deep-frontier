"""Model and render reference art without reading or modifying game tile data."""
import argparse
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
import gpu_render_lock
from frontier_architecture import Geometry,spin,sway
from reference_materials import create_reference_materials,civic_native_materials
from crusher_sheet_geometry import crusher
from mixer_isometric_geometry import mixer, ACCESS as MIXER_ACCESS
from kiln_isometric_geometry import kiln
from quarry_isometric_geometry import quarry,animate_hoist,ACCESS
from quarry_process_details import animate_process,PROCESS
from industrial_facades import extra_materials
from industrial_levels import LEVELS
from civic_isometric_geometry import hospital,restaurant,grocery,fishery,CIVIC_ACCESS,CIVIC_TERRACES
from hatchery_isometric_geometry import hatchery
from pit_isometric_geometry import sandstone_pit,limestone_pit,animate_pit
from structural_geometry import MODELS as STRUCTURAL_MODELS
from hydro_isometric_geometry import hydro
from materials_laboratory_geometry import laboratory, animate_press
from native_building_assets import build_native_assembly
from industrial_budget import MODELS as BUDGET_MODELS,BEVEL as BUDGET_BEVEL
# Triangle budget, civic/hydro/research/waterside family: built as shells. No
# bevel modifier (the native atlases paint edge highlights, as vanilla meshes
# do), and faces enclosed by solid parts or sealed rooms are removed at build
# (enclosed_cull.py; verified by audit_hidden_geometry.py --culled).
from enclosed_cull import SHELL_MODELS
# The lean industrial models (industrial_kit.LEAN_MODELS, 12k cap) also ray-test small faces.
from industrial_kit import LEAN_MODELS
PITS=('SandstonePit','LimestonePit')

MODELS={'StoneCrusher':crusher,'CementKiln':kiln,'MineralQuarry':quarry,'ConcreteMixer':mixer,'ReinforcedHydroTurbine':hydro,'MaterialsLaboratory':laboratory,
        'Hospital':hospital,'Restaurant':restaurant,'GroceryStore':grocery,'FisheryWorks':fishery,'FishHatchery':hatchery,
        'SandstonePit':sandstone_pit,'LimestonePit':limestone_pit}
MODELS.update(STRUCTURAL_MODELS)
PALETTES={'StoneCrusher':'crusher','CementKiln':'kiln','MineralQuarry':'kiln','ConcreteMixer':'kiln',
          'Hospital':'kiln','Restaurant':'kiln','GroceryStore':'kiln','FisheryWorks':'kiln','FishHatchery':'kiln',
          'SandstonePit':'kiln','LimestonePit':'kiln','ReinforcedHydroTurbine':'kiln','MaterialsLaboratory':'kiln'}
PALETTES.update({ident:'kiln' for ident in STRUCTURAL_MODELS})
# Orthographic framing per structural model, as a multiple of its largest extent.
STRUCTURAL_CAMERA_SCALE={'SandstoneMasonryBlock':1.9,'LimestoneMasonryBlock':1.9,
                         'ConcreteBlock':1.9,'ConcreteOverhang8x1':1.0,
                         'ConcreteScaffold3x3':1.7,'ReinforcedDamBlock':1.9,
                         'ConcreteOverflowDam':1.9,
                         'ConcreteScaffold3x3H1':1.7,'ConcreteScaffold3x3H2':1.7,
                         'ConcreteScaffold4x4H1':1.7,'ConcreteScaffold4x4H2':1.7,
                         'ConcreteScaffold4x4H3':1.7,'ConcreteScaffold5x5H1':1.7,
                         'ConcreteScaffold5x5H2':1.7,'ConcreteScaffold5x5H3':1.7,
                         'ConcreteSidePlatform3x3':1.6,'ConcreteSidePlatform4x4':1.6,
                         'ConcreteSidePlatform5x5':1.6,
                         'SteelCantilever10x1':1.0,'SteelCantilever12x1':1.0,'SteelCantilever15x1':1.0,
                         'SteelBridge8x1':1.0,'SteelBridge10x1':1.0,'SteelBridge12x1':1.0,'SteelBridge15x1':1.0,
                         'SteelColumnH1':2.2,'SteelColumnH2':1.9,'SteelColumnH3':1.7,'SteelColumnH4':1.6,
                         'SteelColumnH5':1.5,'SteelColumnH6':1.45,'SteelDeck3x3':1.7,'SteelDeck5x5':1.6}
if set(STRUCTURAL_CAMERA_SCALE)!=set(STRUCTURAL_MODELS):
    raise ValueError('Every structural model needs an explicit camera scale')
REFERENCES={
    'MaterialsLaboratory':('Materials Laboratory v1.png',['front-left isometric','rear-right isometric']),
    'ReinforcedHydroTurbine':('Reinforced Hydro Turbine v1.png',['front-left isometric','rear-right isometric']),
    'SandstonePit':('01-mining-and-sources-concept-v1.png',['sandstone pit front isometric','sandstone pit rear isometric']),
    'LimestonePit':('01-mining-and-sources-concept-v1.png',['limestone pit front isometric','limestone pit rear isometric']),
    'MineralQuarry':('01-mining-and-sources-concept-v1.png',['permanent quarry front isometric','permanent quarry rear isometric']),
    'StoneCrusher':('02-concrete-production-concept-v1.png',['isometric building']),
    'CementKiln':('Cement Kiln 3D Reference Sheet.png',['Front Left','Front Right','Back Left']),
    'ConcreteMixer':('02-concrete-production-concept-v1.png',['isometric building']),
    'Hospital':('Hospital.png',['Front Left','Front Right','Back Left','Back Right']),
    'Restaurant':('Resturaunt.png',['Front Left','Front Right','Back Left','Back Right']),
    'GroceryStore':('Grocery Store.png',['Front Left','Front Right','Back Left','Back Right']),
    'FisheryWorks':('Fishery.png',['Front Left','Front Right','Back Left','Back Right']),
    'FishHatchery':('Fishery.png',['Front Left waterfront construction details','Front Right waterfront construction details'])}

def fire_motion(obj,phase,frame_end):
    # The flame is visual only. Mesh scale pulses around its base, then loops.
    values=[1,.81,1.12,.92,1.05,.87,1]
    if (frame_end-1)%60!=0:raise ValueError('Fire timeline must contain whole 60-frame cycles')
    for cycle in range((frame_end-1)//60):
        for i,frame in enumerate((1,11,21,31,41,51,61)):
            value=values[(i+phase)%6] if i<6 else values[phase]
            obj.scale=(1+(1-value)*.22,1+(1-value)*.16,value)
            obj.keyframe_insert(data_path='scale',frame=frame+cycle*60)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:key.interpolation='LINEAR'

def render_model(ident,cli):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):bpy.data.collections.remove(c)
    for mesh in list(bpy.data.meshes):bpy.data.meshes.remove(mesh)
    for material in list(bpy.data.materials):bpy.data.materials.remove(material)
    scene=bpy.context.scene;scene.frame_start=1
    scene.frame_end={'CementKiln':241,'MineralQuarry':481,'StoneCrusher':61,'ConcreteMixer':121,
                     'Hospital':61,'Restaurant':61,'GroceryStore':61,'FisheryWorks':301,'FishHatchery':61,
                     'SandstonePit':121,'LimestonePit':121,'ReinforcedHydroTurbine':121,'MaterialsLaboratory':121,
                     **{name:1 for name in STRUCTURAL_MODELS}}[ident]
    scene.render.fps=24 if ident=='FisheryWorks' else 30
    materials=create_reference_materials(PALETTES[ident])
    if ident in ('MineralQuarry','StoneCrusher','CementKiln','ConcreteMixer','ReinforcedHydroTurbine','MaterialsLaboratory') or ident in CIVIC_ACCESS or ident in PITS or ident in STRUCTURAL_MODELS:
        materials.extend(extra_materials())
    if ident in CIVIC_ACCESS:
        from reference_materials import GLASS
        pane=materials[GLASS].node_tree.nodes['Principled BSDF']
        pane.inputs['Emission Strength'].default_value=1.1
    model=bpy.data.collections.new(ident+'.ReferenceStudy');scene.collection.children.link(model)
    # Structural pieces (structural_geometry.py) take the same no-bevel, culled build.
    # The industrial family (industrial_budget.MODELS) too.
    shell=ident in SHELL_MODELS or ident in STRUCTURAL_MODELS or ident in BUDGET_MODELS
    static=Geometry(ident+'.Architecture');static.cull_enclosed=shell;static.cull_small_hidden=ident in SHELL_MODELS or ident in LEAN_MODELS;parts=[];rail_assembly=MODELS[ident](static,parts)
    materials=civic_native_materials(materials)
    uv_profile='civic-native'
    if ident=='MaterialsLaboratory':uv_profile='research-native'
    # Triangle-budget models (industrial_budget.py) carry no bevel modifier.
    static_bevel,part_bevel=(BUDGET_BEVEL,BUDGET_BEVEL) if ident in BUDGET_MODELS else (0,0) if shell else (.012,.006)
    static.build(model,materials,static_bevel,uv_profile)
    if ident in ('StoneCrusher','CementKiln','MineralQuarry','ConcreteMixer','ReinforcedHydroTurbine','MaterialsLaboratory') or ident in CIVIC_ACCESS:
        for geo in rail_assembly.meshes:geo.build(model,materials,static_bevel,uv_profile)
    for geo,axis,speed in parts:
        # Parts can move: only their exact (rotation-invariant) self-enclosure.
        geo.cull_enclosed=shell
        obj=geo.build(model,materials,part_bevel,uv_profile)
        if axis=='STATIC':pass
        elif axis=='LAB_PRESS':animate_press(obj,scene.frame_end)
        elif axis in ('PIT_DRUM','PIT_BASKET','PIT_CABLE'):animate_pit(obj,axis,scene.frame_end)
        elif axis in ('HOIST_DRUM','HOIST_SHEAVE','HOIST_LIFT','HOIST_CABLE','HOIST_TIP','HOIST_LOAD','SIEVE'):animate_hoist(obj,axis,scene.frame_end)
        elif axis in ('BELT_SLAT','POUR_STONE','BELT_STONE','SCREEN_STONE'):animate_process(obj,axis,speed,scene.frame_end)
        elif axis=='SWAY':sway(obj,speed,scene.frame_end if ident in CIVIC_ACCESS else 61)
        elif axis=='FLAME':fire_motion(obj,speed,scene.frame_end)
        else:spin(obj,axis,speed,frame_end=scene.frame_end)
    native_animated=build_native_assembly(static,model,scene.frame_end)
    scene.frame_set(1);bpy.context.view_layer.update()
    vertices=[o.matrix_world@Vector(corner) for o in model.objects if o.type=='MESH' for corner in o.bound_box]
    low=Vector(tuple(min(v[a] for v in vertices) for a in range(3)))
    high=Vector(tuple(max(v[a] for v in vertices) for a in range(3)))
    # Record authored bounds only; no tile envelope or automatic scaling is applied.
    output=cli.output_dir;output.mkdir(exist_ok=True,parents=True)
    if static.structural_parts:
        (output/(ident+'-structure.json')).write_text(json.dumps({
            'schema':1,'coordinateSystem':'Native grid XYZ, Z up, before BaseZ',
            'parts':static.structural_parts},indent=2)+'\n')
    if ident in CIVIC_ACCESS:
        from civic_validation import validate_civic_walks
        clearance=validate_civic_walks(ident,model,scene)
    (output/(ident+'-native-assembly.json')).write_text(json.dumps({
        'scope':'Local preview copies; game references the original shipped resources',
        'props':static.native_props,'liquids':static.liquid_surfaces},indent=2)+'\n')
    if ident in CIVIC_ACCESS:
        access=CIVIC_ACCESS[ident]
        (output/(ident+'-clearance-check.json')).write_text(json.dumps(clearance,indent=2)+'\n')
        (output/(ident+'-rail-manifest.json')).write_text(json.dumps(rail_assembly.manifest(),indent=2)+'\n')
        (output/(ident+'-access-manifest.json')).write_text(json.dumps(access,indent=2)+'\n')
        (output/(ident+'-terrace-manifest.json')).write_text(json.dumps({
            'scope':'Authored clear roof area; native support cells and stairs pending integration',
            **CIVIC_TERRACES[ident]},indent=2)+'\n')
        expected_door_layers={0,*access['balconyLayers'],CIVIC_TERRACES[ident]['layer']}
        if {door['position'][2] for door in static.doorways}!=expected_door_layers:
            raise ValueError('Civic doors must reach every occupied/gallery level')
        (output/(ident+'-visitor-manifest.json')).write_text(json.dumps({
            'scope':'Authored door and seating positions; native visitor behavior not integrated',
            'doors':static.doorways,'internalDoorNetwork':'BuildingInterior',
            'requireAllDoorsConnectedInternally':True,'visitorSeats':static.visitor_seats,
            'restaurantBehavior':'Native attraction visit, reserved Sitting slot, meal consumption during visit'},indent=2)+'\n')
        (output/(ident+'-height-manifest.json')).write_text(json.dumps({
            'units':'1 Blender Z unit = 1 Timberborn grid layer',
            'scope':'Source geometry only; native occupancy and paths not bound',
            'walkableDeckLayers':sorted({*access['balconyLayers'],CIVIC_TERRACES[ident]['layer']}),
            'entranceLayers':sorted(expected_door_layers), 'artHeight':high.z},indent=2)+'\n')
    if ident in ('StoneCrusher','CementKiln','MineralQuarry'):
        (output/(ident+'-rail-manifest.json')).write_text(json.dumps(rail_assembly.manifest(),indent=2)+'\n')
        levels=LEVELS[ident]
        if high.z>levels['heightEnvelopeLayers']:
            raise ValueError(f'{ident} exceeds its authored whole-layer height envelope')
        (output/(ident+'-height-manifest.json')).write_text(json.dumps({
            'units':'1 Blender Z unit = 1 Timberborn grid layer',
            'scope':'Authored vertical contract; horizontal grid/collision/native routes not yet bound',
            **levels},indent=2)+'\n')
    if ident=='MineralQuarry':
        (output/(ident+'-access-manifest.json')).write_text(json.dumps(ACCESS,indent=2)+'\n')
        (output/(ident+'-process-manifest.json')).write_text(json.dumps(PROCESS,indent=2)+'\n')
    if ident=='ConcreteMixer':
        (output/(ident+'-rail-manifest.json')).write_text(json.dumps(rail_assembly.manifest(),indent=2)+'\n')
        (output/(ident+'-access-manifest.json')).write_text(json.dumps(MIXER_ACCESS,indent=2)+'\n')
    if ident=='ReinforcedHydroTurbine':
        (output/(ident+'-rail-manifest.json')).write_text(json.dumps(rail_assembly.manifest(),indent=2)+'\n')
        (output/(ident+'-access-manifest.json')).write_text(json.dumps({
            'scope':'Source art only; water, supports, navigation and gameplay not registered',
            'doors':static.doorways,'deckLayer':2,'capLayer':6,
            'externalStairs':'Player-built native stairs',
            'runtimeWater':'Native world water; no authored substitute water mesh',
        },indent=2)+'\n')
    if ident=='MaterialsLaboratory':
        (output/(ident+'-rail-manifest.json')).write_text(json.dumps(rail_assembly.manifest(),indent=2)+'\n')
        (output/(ident+'-access-manifest.json')).write_text(json.dumps({
            'scope':'Authored source geometry; native registration is a separate step',
            'doors':static.doorways,'deckLayer':2,'clearTerrace':[0,0,3,2.5],
            'externalStairs':'Player-built native stairs','internalConnection':'BuildingInterior',
        },indent=2)+'\n')
    if ident in PITS:
        (output/(ident+'-rail-manifest.json')).write_text(json.dumps(rail_assembly.manifest(),indent=2)+'\n')
        (output/(ident+'-access-manifest.json')).write_text(json.dumps({
            'scope':'Reference study; exact native footprint/entrance integration pending',
            'doors':static.doorways,'walkableDeckLayers':[0],'internalStairs':False,
        },indent=2)+'\n')
    if ident in STRUCTURAL_MODELS:
        (output/(ident+'-rail-manifest.json')).write_text(json.dumps(rail_assembly.manifest(),indent=2)+'\n')
    (output/(ident+'-study.json')).write_text(json.dumps({'status':'Blender art study; not exported or installed',
        'boundsMin':list(low),'boundsMax':list(high),
        'sourceReference':('tools/asset-pipeline/structural_geometry.py' if ident in STRUCTURAL_MODELS else 'docs/art/concepts/'+REFERENCES[ident][0]),
        'selectedReferenceViews':([] if ident in STRUCTURAL_MODELS else REFERENCES[ident][1]),
        'referenceProjection':'Current authoring policy: isometric concept only; top-down reference excluded',
        'animatedParts':[g.name for g,axis,_ in parts if axis!='STATIC']+native_animated,
        'animationFrames':scene.frame_end,'animationFps':scene.render.fps,'tileDimensions':None},indent=2)+'\n')
    rig=bpy.data.collections.new('Studio');scene.collection.children.link(rig)
    def move(o):
        for c in list(o.users_collection):c.objects.unlink(o)
        rig.objects.link(o)
    bpy.ops.object.camera_add();camera=bpy.context.object;move(camera);scene.camera=camera;camera.data.type='ORTHO'
    center=(low+high)/2;target=Vector((center.x,center.y,center.z*.85))
    lights=[((2.5,3.5,8),1100,5),((-6,2,5),420,5),((-2,-6,7),1000,4)]
    if ident=='MineralQuarry':lights=[((1,2,14),2100,8),((-12,1,10),1100,7),((-7,-13,13),2400,7)]
    if ident in CIVIC_ACCESS or ident=='MaterialsLaboratory':lights=[((1,2,12),2200,7),((-11,1,9),1300,7),((-7,-12,12),2000,7)]
    for p,energy,size in lights:
        bpy.ops.object.light_add(type='AREA',location=p);light=bpy.context.object;move(light)
        light.data.energy=energy;light.data.size=size
        light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
    if ident=='CementKiln':
        # Studio illumination of authored lanterns and embers, not runtime effects.
        for x,y,z,energy in ((1.58,1.02,2.58,7),(5.65,1.02,2.56,9),
                             (.20,.03,.84,4),(4.60,.03,.84,4),
                             (1.58,3.52,2.72,7),(5.65,3.52,2.81,8),
                             (6.16,.99,.78,16)):
            bpy.ops.object.light_add(type='POINT',location=(-x,-y,z));light=bpy.context.object;move(light)
            light.data.energy=energy;light.data.color=(1,.26,.025);light.data.shadow_soft_size=.12
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-1.04 if ident=='FishHatchery' else -.04));ground=bpy.context.object;move(ground)
    mat=bpy.data.materials.new('Studio warm grey');mat.use_nodes=True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.18,.165,.135,1)
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.9;ground.data.materials.append(mat)
    if ident=='FishHatchery':
        # Studio-only view of world water through the open cages. This object
        # lives outside the model collection and cannot enter its export.
        from native_building_assets import native_material
        bpy.ops.mesh.primitive_plane_add(size=2,location=(-2.8,-4.9,-.28))
        water=bpy.context.object;water.name='Studio.WorldWater';move(water)
        water.scale=(4.2,3.6,1);water.data.materials.append(native_material('Water'))
    scene.world.color=(.28,.28,.28);scene.view_settings.view_transform='AgX'
    scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
    # Layered native leaf cards need more than Cycles' default eight transparent
    # intersections; otherwise flower centres render black despite valid alpha.
    scene.cycles.transparent_max_bounces=32
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    required=[d for d in prefs.devices if d.type=='OPTIX' and d.name=='NVIDIA GeForce RTX 2060']
    if len(required)!=1:raise RuntimeError('Required RTX 2060 OptiX render device is unavailable')
    for device in prefs.devices:device.use=device in required
    scene.cycles.device='GPU'
    # Denoise on the GPU too: OIDN on the CPU used ~85 of the ~95 CPU-seconds of a 1200 px render.
    if not prefs.has_oidn_gpu_devices():raise RuntimeError('RTX 2060 OIDN GPU denoising unavailable')
    scene.cycles.denoising_use_gpu=True
    scene.render.resolution_x=cli.resolution;scene.render.resolution_y=cli.resolution;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    extent=max(high-low);directions={'front':(7,9,6.2),'front-right':(-7,9,6.2),
        'back-left':(7,-9,6.2),'rear':(-7,-9,6.5),'detail':(6,8,4.5),
        'process':(-7,9,6.2),'facade':(-7,9,2.8)}
    for view in ([] if cli.save_only else cli.views.split(',')):
        scene.frame_set(220 if view=='process' and ident=='MineralQuarry' else 1)
        direction=directions[view];scale=extent*(1.55 if view!='detail' else .86)
        if ident in STRUCTURAL_MODELS:
            scale=extent*STRUCTURAL_CAMERA_SCALE[ident]
        focus=target if view!='detail' else Vector((center.x,center.y*.72,center.z*1.10))
        if ident=='StoneCrusher' and view=='detail':focus=Vector((-1.75,-1.70,2.05));scale=3.65
        if ident=='CementKiln' and view=='detail':focus=Vector((-4.25,-1.45,1.85));scale=5.10
        if ident=='CementKiln' and view!='detail':scale=extent*1.31
        if ident=='MineralQuarry' and view=='detail':focus=Vector((-4.9,-5.2,6.5));scale=5.3
        if ident=='MineralQuarry' and view!='detail':scale=extent*1.34
        if ident in CIVIC_ACCESS and view!='detail':scale=extent*(1.55 if ident=='FishHatchery' else 1.34)
        if ident=='MaterialsLaboratory' and view!='detail':scale=extent*1.39
        if ident=='MineralQuarry' and view=='process':focus=Vector((-6.3,-4.1,4.4));scale=6.4
        if ident=='StoneCrusher' and view=='facade':focus=Vector((-2.0,-1.8,.95));scale=5.5
        if ident=='CementKiln' and view=='facade':
            focus=Vector((-3.45,-.75,1.0));scale=4.5;direction=(7,9,2.5)
        camera.location=focus+Vector(direction);camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.ortho_scale=scale
        scene.render.filepath=str(output/f'{ident}-{view}.png');gpu_render_lock.render(write_still=True)
        print('REFERENCE STUDY RENDERED',ident,view,flush=True)
    camera.location=target+Vector((7,9,6.2));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.frame_set(1)
    camera.data.ortho_scale=extent*({'CementKiln':1.31,'MineralQuarry':1.34}[ident] if ident in ('CementKiln','MineralQuarry') else 1.55)
    if ident in CIVIC_ACCESS:camera.data.ortho_scale=extent*(1.55 if ident=='FishHatchery' else 1.34)
    if ident=='MaterialsLaboratory':camera.data.ortho_scale=extent*1.39
    if ident in STRUCTURAL_MODELS:
        camera.data.ortho_scale=extent*STRUCTURAL_CAMERA_SCALE[ident]
    cli.blend_dir.mkdir(exist_ok=True,parents=True)
    blend=cli.blend_dir/(ident+'-ReferenceStudy.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print('ART STUDY SAVED; NO GAME PACKAGE WAS CHANGED',flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resolution',type=int,default=1600)
    parser.add_argument('--models',required=True,help='Explicit full-scene creation targets. Use rebuild_components.py for existing asset edits.')
    parser.add_argument('--views',default='front')
    parser.add_argument('--save-only',action='store_true',help='Build and save the authored scene/metadata without rendering stills')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs/reference-studies')
    parser.add_argument('--blend-dir',type=Path,default=ROOT/'src/DeepFrontier/Art/Source')
    cli=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if not cli.output_dir.is_absolute() or not cli.blend_dir.is_absolute():
        raise ValueError('Output and Blender scene directories must be absolute paths')
    for view in cli.views.split(','):
        if view not in ('front','front-right','back-left','rear','detail','process','facade'):raise ValueError('Use only angled review views: '+view)
        if view=='process' and cli.models!='MineralQuarry':raise ValueError('This close-up is authored only for MineralQuarry')
        if view=='facade' and any(name not in ('StoneCrusher','CementKiln') for name in cli.models.split(',')):
            raise ValueError('Facade close-ups are authored only for StoneCrusher and CementKiln')
    for ident in cli.models.split(','):render_model(ident,cli)

if __name__=='__main__':main()
