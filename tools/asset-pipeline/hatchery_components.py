"""Independently rebuildable nursery room, floor and decorative assets."""
from frontier_architecture import Geometry,WOOD,PLANK,IRON,ROOF
from reference_materials import CIVIC_FORGED_PANEL,CIVIC_CONCRETE
from grid_structure import platform,room
from hatchery_structure import SOURCE_ORIGIN,ROOMS,PLATFORMS,SUPPORTS,DOORS,RAIL_RUNS,BANK_APRON_SURFACE,source

# 2026-10-30 compaction: the headhouse is one layer tall (native z 1..2)
# with a flat cast roof; the roof bearing, gabled roof and roof vent are gone.
def shell(g):
    room(g,'Headhouse',ROOMS['Headhouse'],SOURCE_ORIGIN,(1.5,1.,1.),
         exterior={'front':[(0,4)],'back':[(0,4)],'left':[(1,3)],'right':[(1,3)]},wall_style='storey')

def lamps(g):
    from civic_isometric_geometry import wall_lamp
    for x in (.88,2.12):wall_lamp(g,*source((x,1.04,1.50)))

def roof(g):
    """Flat roof on the tile lines: a cast slab over the one-layer walls,
    timber decking set in from its edges and a forged drip strip."""
    x0,y0,_,x1,y1,z1=ROOMS['Headhouse']
    cx,cy,_=source(((x0+x1)/2,(y0+y1)/2,0))
    top=source((0,0,z1))[2]
    g.box((cx,cy,top-.07),(x1-x0,y1-y0,.14),CIVIC_CONCRETE)
    g.box((cx,cy,top+.01),(x1-x0-.30,y1-y0-.30,.02),PLANK)
    for dy in (-(y1-y0)/2+.06,(y1-y0)/2-.06):g.box((cx,cy+dy,top+.015),(x1-x0-.02,.08,.03),IRON)
    for dx in (-(x1-x0)/2+.06,(x1-x0)/2-.06):g.box((cx+dx,cy,top+.015),(.08,y1-y0-.20,.03),IRON)

def windows(g):
    from architectural_windows import window
    for x in (2.52,3.35):window(g,*source((x,1.04,1.46)),.50,'front','grand')
    for x in (.65,2.,3.35):window(g,*source((x,2.96,1.46)),.50,'back','grand')
    window(g,*source((.04,1.85,1.46)),.55,'left','lancet')
    window(g,*source((3.96,1.85,1.46)),.55,'right','lancet')

# Dock piles are runtime AdaptiveSupports clones of the exported
# #SupportSegment/#SupportFoot templates (waterside_supports.py); the former
# fixed-length 'Dock.Supports' short posts were removed from the saved scene by
# migrate_hatchery_adaptive_supports.py.

# 2026-10-22 (user): no lamps on posts outside the walls; the two dock
# lamps (component Dock.Lamps) are gone.

def door(g):
    from industrial_facades import building_portal
    building_portal(g,*source(DOORS['Door0']['position']),facade='grid')

def bank_apron(g,ident):
    """Backing clears the native terrain maximum by 6mm; boards add 4mm."""
    x0,y0,z0,x1,y1,z1=PLATFORMS[ident]
    floor=BANK_APRON_SURFACE['nativeFloor'];low=BANK_APRON_SURFACE['bottom']
    backing=BANK_APRON_SURFACE['backingTop'];top=BANK_APRON_SURFACE['wearingTop']
    for row in range(5):
        g.box(source(((x0+x1)/2,y0+(row+.5)*.2,(backing+top)/2)),(x1-x0,.194,top-backing),PLANK)
    slab=[source((x,y,z)) for z in (low,backing) for y in (y0,y1) for x in (x0,x1)]
    for face in ((0,2,3,1),(4,5,7,6),(0,1,5,4),(1,3,7,5),(3,2,6,7),(2,0,4,6)):
        g.add([slab[i] for i in face],[(0,1,2,3)],PLANK)
    g.structural_parts.append({'id':ident,'kind':'platform','bounds':PLATFORMS[ident],
        'floorHeight':floor,'wearingSurfaceHeight':top,'backingSurfaceHeight':backing,'supports':[],
        'pickingBoxes':[{'center':[(x0+x1)/2,(y0+y1)/2,(low+top)/2],'size':[x1-x0,y1-y0,top-low]}]})

BUILDERS={'Headhouse.Shell':shell,'Headhouse.DoorLamps':lamps,
          'Headhouse.Roof':roof,'Headhouse.Windows':windows,
          'Door.Door0':door}

def recipe(key):
    g=Geometry('FishHatchery.'+key)
    if key.startswith('Deck.'):
        ident=key.removeprefix('Deck.')
        if ident in ('MainFrontApron','CanopyFrontApron'):
            bank_apron(g,ident)
        else:platform(g,ident,PLATFORMS[ident],SOURCE_ORIGIN,SUPPORTS[ident])
    else:BUILDERS[key](g)
    return g

def recipes():
    keys=[*BUILDERS,*('Deck.'+name for name in PLATFORMS)]
    return {key:(lambda key=key:recipe(key)) for key in keys}

def include(g,key):
    part=recipe(key);offset=len(g.faces)
    g.include_component(part)
    g.structural_parts.extend(part.structural_parts)
    for mount in part.window_mounts:
        g.window_mounts.append({**mount,'faceRange':[v+offset for v in mount['faceRange']]})

def rails():
    from walkway_geometry import RailAssembly
    r=RailAssembly('WalkwayRail.FishHatchery')
    for name,a,b,count in RAIL_RUNS:
        if sum(abs(x-y) for x,y in zip(a,b,strict=True))!=count:raise ValueError('Hatchery rail count differs from authored native cells')
        r.run_cells(name,a,b,SOURCE_ORIGIN)
    return r
