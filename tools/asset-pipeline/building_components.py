"""Explicit, independently callable building asset recipes.

The registry is the authoring contract. Unknown models/components fail; no
whole-building generator is called by a component rebuild.
"""
from frontier_architecture import Geometry
from industrial_facades import building_portal
from restaurant_structure import DOORS as RESTAURANT_DOORS, ORIGIN as RESTAURANT_ORIGIN
from hospital_structure import DOORS as HOSPITAL_DOORS, ORIGIN as HOSPITAL_ORIGIN
import industrial_door_components as industrial
import pit_apron_components as pit_aprons
import hatchery_components as hatchery
from industrial_layouts import LAYOUTS as INDUSTRIAL_LAYOUTS
from pit_layouts import LAYOUTS as PIT_LAYOUTS
from hydro_layout import LAYOUTS as HYDRO_LAYOUTS

DOOR_LAYOUTS={
    'Restaurant':(RESTAURANT_DOORS,RESTAURANT_ORIGIN),
    'Hospital':(HOSPITAL_DOORS,HOSPITAL_ORIGIN),
    'FishHatchery':({'Door0':{'position':[1.3,.25,0],'outward':[0,-1]}},[0,0,0]),
    'FisheryWorks':({
        'Door0':{'position':[3.90,3.12,2],'outward':[0,-1],'panelDepth':.10},
        'Door1':{'position':[2.0,1.55,0],'outward':[0,-1],'panelDepth':.11},
        'RoofTerraceDoor':{'position':[1.22,5.55,2],'outward':[-1,0],'panelDepth':.09},
    },[0,0,0]),
    'GroceryStore':({
        'Door0':{'position':[4.08,2.87,2],'outward':[0,-1],'panelDepth':.10},
        'Door1':{'position':[4.10,2.87,4],'outward':[0,-1],'panelDepth':.10},
        'Door2':{'position':[1.60,1.65,0],'outward':[0,-1],'panelDepth':.11},
        'RoofTerraceDoor':{'position':[6.78,4.70,6],'outward':[1,0],'panelDepth':.09},
    },[0,0,0]),
}
FACADES={'Restaurant':'grid','Hospital':'grid','FishHatchery':'grid',
         'FisheryWorks':'framed','GroceryStore':'framed'}
LEGACY_FACADES={name:'recessed' for name in DOOR_LAYOUTS}
UV_PROFILES={name:'civic-native' for name in DOOR_LAYOUTS}
# Exported model coordinates, distinct from worker idle or native BaseZ cells.
# FisheryWorks: its layout origin (fishery_layout.py); y -2 since the
# 12x10 -> 11x8 footprint (2026-10-22).
EXPORT_OFFSETS={'Restaurant':[0,0,0],'Hospital':[0,0,0],
                'FishHatchery':[.2,.75,0],'FisheryWorks':[1.25,-1.30,0],
                'GroceryStore':[.4,0,0]}
_industrial_layouts={**INDUSTRIAL_LAYOUTS,**PIT_LAYOUTS,**HYDRO_LAYOUTS}
for _model in industrial.MODELS:
    if _model in DOOR_LAYOUTS:raise ValueError('Duplicate component owner: '+_model)
    DOOR_LAYOUTS[_model]=(industrial.DOORS[_model],[0,0,0])
    FACADES[_model]='recessed'
    LEGACY_FACADES[_model]='recessed'
    UV_PROFILES[_model]=industrial.UV_PROFILES[_model]
    EXPORT_OFFSETS[_model]=_industrial_layouts[_model]['origin']

CULLING_CONTEXTS={model:[model+'.Architecture'] for model in DOOR_LAYOUTS}
CULLING_CONTEXTS['FishHatchery']=['FishHatchery.Architecture','FishHatchery.Headhouse.Shell']


def door_component(model,ident,door,origin,*,facade):
    g=Geometry(f'{model}.Door.{ident}')
    if facade=='framed':building_portal(g,0,0,0,facade=facade,panel_depth=door['panelDepth'])
    else:building_portal(g,0,0,0,facade=facade)
    x,y,z=[p-o for p,o in zip(door['position'],origin,strict=True)]
    nx,ny=door['outward'];tx,ty=-ny,nx
    if (nx,ny) not in ((0,-1),(1,0),(0,1),(-1,0)):
        raise ValueError('Door needs an explicit cardinal orientation')
    # Tangent and inward depth are an orthonormal rotation, never a scale or
    # coordinate repair. Geometry is stored in Blender's (-X,-Y,Z) basis.
    g.vertices=[(-(x-vx*tx+vy*nx),-(y-vx*ty+vy*ny),z+vz)
                for vx,vy,vz in g.vertices]
    return g


def recipes(model):
    if model=='FishHatchery':return hatchery.recipes()
    if model in industrial.MODELS:
        builders=industrial.recipes(model)
        if model in pit_aprons.BOUNDS:
            builders['Apron']=lambda:pit_aprons.recipe(model)
        return builders
    doors,origin=DOOR_LAYOUTS[model]
    return {f'Door.{ident}':(lambda ident=ident,door=door:
            door_component(model,ident,door,origin,facade=FACADES[model]))
            for ident,door in doors.items()}


def recipe(model,component):
    return recipes(model)[component]()


def legacy_door(model,component):
    if model=='FishHatchery':
        raise ValueError('Hatchery structural migration uses migrate_hatchery_platform.py; the door-only initializer is not its migration contract')
    if model in industrial.MODELS:return industrial.legacy_door(model,component)
    if component not in recipes(model):
        raise ValueError('No legacy component migration authored: '+model+'/'+component)
    doors,origin=DOOR_LAYOUTS[model]
    ident=component.removeprefix('Door.')
    return door_component(model,ident,doors[ident],origin,facade=LEGACY_FACADES[model])


def exported_doors(model):
    doors,_=DOOR_LAYOUTS[model];offset=EXPORT_OFFSETS[model]
    return {ident:{**door,'position':[a+b for a,b in zip(door['position'],offset,strict=True)]}
            for ident,door in doors.items()}
