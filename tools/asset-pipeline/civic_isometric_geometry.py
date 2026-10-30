"""Surface-colony buildings authored from the four individual isometric sheets.

Only the front/rear isometric illustrations are references. No plan views,
printed tile counts, existing blueprint sizes or mesh scaling are used here.
Ground entrances are layer 0; public balconies have floors at layers 2 and 4.
The outer access bays intentionally accept separately built vanilla stairs.
"""
import math
import random
from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, SAND, LIME, GREY, BRASS, deck, wall, facade_panel
from reference_materials import GLOW, GLASS, LEAF, WATER, CLOTH, KILN_SOOT, KILN_STONE, KILN_STONE_LIGHT, KILN_WOOD_WEAR, KILN_WOOD_SPLIT
from reference_materials import CIVIC_CONCRETE, CIVIC_ORANGE_PANEL, CIVIC_FORGED_PANEL
# Triangle budget: the civic, hydro, research and waterside families use the
# shell-only fastener and container kit (industrial_budget.py): 2 square nuts per
# collar plate, no buried caps or plate backs, 8-sided pipes.
from industrial_budget import bin, prism, open_box
from reference_materials import CRUSHER_STEEL


def steel_bolt(g,p,axis='Y',r=.022):
    """Fastener head for the civic family: one square nut (4 sides, both caps;
    the cap buried in the plate is removed by the enclosed-face cull) where
    industrial_geometry.steel_bolt had a 12-sided washer and a 6-sided nut."""
    # Turned 45 degrees (a diamond): its sides never share a plane with the
    # axis-aligned plates and boards it is bolted to.
    prism(g,p,r*1.3,.031,CRUSHER_STEEL,axis,4)


# Triangle budget, 20k grand cap (2026-10-29): the civic shell family
# (FisheryWorks, Restaurant, Hospital, ReinforcedHydroTurbine,
# MaterialsLaboratory) drops its fastener heads. A 4 cm square nut is one or
# two pixels at normal zoom, and there were hundreds per building (a quarter
# to a third of each model's triangles). Plates, collars and straps stay.
def collar(g,x,y,z,w):
    """Iron collar on a timber member: one box with the outline of
    industrial_budget.bracket's four folded plates (w+.052 square, .23 tall),
    without its eight square nuts (80 of its 112 triangles)."""
    g.box((x,y,z),(w+.052,w+.052,.23),IRON)


def lean_bin(g,p,size):
    """industrial_budget.bin for the civic shell family: the same floor, side
    boards and corner irons, the boards in rows of up to 30 cm (was 15) and
    no rivet heads."""
    x,y,z=p
    w,d,h=size
    rows=max(1,math.ceil(h/.30))
    g.box((x,y,z+.045),(w-.12,d-.12,.09),WOOD)
    for j in range(rows):
        level=z+(j+.5)*h/rows
        for xx in (x-w/2+.03,x+w/2-.03):g.box((xx,y,level),(.06,d-.12,h/rows-.01),PLANK)
        for yy in (y-d/2+.03,y+d/2-.03):g.box((x,yy,level),(w,.06,h/rows-.01),PLANK)
    for xx in (x-w/2+.055,x+w/2-.055):
        for yy in (y-d/2+.055,y+d/2-.055):g.box((xx,yy,z+h/2),(.09,.09,h+.03),IRON)


def lean_sheet_roof(g,x0,y0,x1,y1,z0,z1):
    """industrial_budget.sheet_roof for the civic shell family: the same side
    and end beams, corner shoes and straps; sheets about 40 cm wide (was 28),
    plain corner collars and no fastener heads."""
    count=math.ceil((x1-x0)/.40)
    for i in range(count):
        x=x0+(i+.5)*(x1-x0)/count
        g.beam((x,y0,z0),(x,y1,z1),(x1-x0)/count,.045,ROOF)
    for x in (x0,x1):
        g.beam((x,y0,z0-.035),(x,y1,z1-.035),.13,.14,WOOD)
    for y,z in ((y0,z0),(y1,z1)):
        g.beam((x0,y,z-.055),(x1,y,z-.055),.15,.16,WOOD)
        for x in (x0,x1):
            collar(g,x,y,z-.07,.16)
            open_box(g,(x,y,z+.050),(.22,.22,.025),IRON,('-z',))
    for t in (.35,.72):
        y=y0+(y1-y0)*t
        z=z0+(z1-z0)*t+.03
        g.beam((x0,y,z),(x1,y,z),.06,.018,IRON)


def handwheel(g,p,r,axis='Y',mat=IRON,accent=BRASS):
    """Geometry.wheel for the civic shell family: one 12-sided rim (was two
    24-sided rings), a hub in the accent material and four spokes (was
    eight). A 25 cm valve wheel is about 10 px across at normal zoom."""
    g.ring(p,r,.045,.07,mat,axis,12)
    g.cylinder(p,.06,.12,accent,axis,8)
    for i in range(4):
        a=i*math.pi/2+math.pi/4
        end=((p[0],p[1]+math.cos(a)*r*.95,p[2]+math.sin(a)*r*.95) if axis=='X'
             else (p[0]+math.cos(a)*r*.95,p[1],p[2]+math.sin(a)*r*.95))
        g.beam(p,end,.035,mat=mat)


def gauge(g,x,y,z,r=.09,rim_material=BRASS):
    """industrial_facades.gauge for the civic shell family: 12-sided case and
    glass (was 24) and the needle, without the seven 6 mm scale ticks."""
    g.cylinder((x,y,z),r,.045,rim_material,'Y',12)
    g.cylinder((x,y-.03,z),r*.79,.016,GLASS,'Y',12)
    g.beam((x,y-.046,z),(x+r*.48,y-.046,z+r*.42),.009,mat=CYAN)
from industrial_facades import building_portal, DOOR_OUTER_WIDTH, arched_portal, building_portal_side, CYAN
from industrial_budget import round_pipe
from native_building_assets import barrel,water_barrel,prop,plant
from reference_civic import side_wall, fish
from walkway_geometry import RailAssembly
from grid_structure import gallery as grid_gallery, platform as grid_platform, room as grid_room
from restaurant_structure import ORIGIN as RESTAURANT_ORIGIN, PLATFORMS as RESTAURANT_PLATFORMS, SUPPORTS as RESTAURANT_SUPPORTS, ROOMS as RESTAURANT_ROOMS, DOORS as RESTAURANT_DOORS, source as restaurant_source
from restaurant_structure import EXTERIOR_WALLS as RESTAURANT_WALLS, HEADROOM as RESTAURANT_HEADROOM
from hatchery_structure import ACCESS as HATCHERY_ACCESS, TERRACE as HATCHERY_TERRACE
from lategame_kit import emitter


# Source-space lane centerlines. Furniture, flowers, gutters and roof supports
# must clear these lanes; these are geometry checks, not a native navmesh claim.
CIVIC_ACCESS={
    'FishHatchery':HATCHERY_ACCESS,
    'Hospital':{'entrance':[7.5,2,0], 'balconyLayers':[2,4], 'headroom':1.09,
                'routes':[[(5.5,10.5),(8.5,10.5)]],
                # Source coordinates (native + 5 in X since the wings were
                # removed, 2026-10-30): one bay behind the rear deck.
                'stairBays':[[5,11,6,13]]},
    # 2026-10-30: one layer per storey; walking clearance stops under the
    # beams of the deck one layer above (restaurant_structure.HEADROOM).
    'Restaurant':{'entrance':[2.3,1.85,0], 'balconyLayers':[1,2], 'headroom':RESTAURANT_HEADROOM,
                  'routes':[[(1.3,2.35),(6.3,2.35),(6.3,7.35),(2.3,7.35)],[(2.3,6.35),(2.3,7.35)]],
                  'stairBays':[[6.2,0.2,7.2,2.2]]},
    'GroceryStore':{'entrance':[1.6,1.65,0], 'balconyLayers':[2,4], 'headroom':1.09,
                    'routes':[[(1.3,2.35),(7.0,2.35),(7.0,6.5),(2.0,6.5)]],
                    'stairBays':[[6.5,0.35,7.5,2.35]]},
    # One layer per storey since 2026-10-30: galleries at layer 1, open to
    # the sky except under the main roof's eave timbers (from 1.93).
    'FisheryWorks':{'entrance':[2.0,1.55,0], 'balconyLayers':[1], 'headroom':.85,
                    'routes':[[(1.66,6.90),(1.66,7.80),(7.35,7.80),(7.35,2.50)],[(3.55,2.50),(7.35,2.50)]],
                    'stairBays':[[6.85,.30,7.85,2.30]]},
}

# Modelled as usable surfaces first; native buildable/support cells are bound
# during game integration, not inferred by shrinking the art to a tile count.
CIVIC_TERRACES={
    'FishHatchery':HATCHERY_TERRACE,
    'Hospital':{'bounds':[5,6,9,10], 'layer':6, 'clearArea':[5.3,7.3,8.7,9.7]},
    'Restaurant':{'bounds':[5.8,2.85,9.8,5.85], 'layer':3, 'clearArea':[7.05,3.10,9.55,5.60]},
    'GroceryStore':{'bounds':[6.48,3.25,9.68,6.15], 'layer':6, 'clearArea':[7.2,3.7,9.2,5.7]},
    'FisheryWorks':{'bounds':[-1.25,4.00,1.40,7.10], 'layer':1, 'clearArea':[-.95,4.45,.65,6.15]},
}


def roof_terrace(g,rails,ident):
    terrace=CIVIC_TERRACES[ident];x0,y0,x1,y1=terrace['bounds'];z=terrace['layer']
    # Cast roof plate with expansion-joint strips, exposed steel edge girders
    # and independent railing panels. The middle stays empty for player props.
    if ident=='Restaurant':
        # Cast concrete roof slab carrying native timber decking, closed by a
        # steel edge channel on its exposed tile edges. The outer bay is a
        # steel-framed cantilever off the inner bay; it has no ground legs.
        for name in ('RoofTerraceInner','RoofTerraceOuter'):
            grid_platform(g,name,RESTAURANT_PLATFORMS[name],RESTAURANT_ORIGIN,RESTAURANT_SUPPORTS[name],PLANK,
                          slab_material=CIVIC_CONCRETE,support_style='pier',fascia=RESTAURANT_FASCIA[name],
                          fascia_material=IRON,beam_material=IRON if name=='RoofTerraceOuter' else WOOD,
                          beam_depth=.20 if name=='RoofTerraceOuter' else .12,board_relief=.010)
    else:
        g.box(((x0+x1)/2,(y0+y1)/2,z-.09),(x1-x0,y1-y0,.18),CIVIC_CONCRETE)
        support_x=(x0+.12,) if ident=='GroceryStore' else (x0+.12,x1-.12)
        for x in support_x:
            for y in (y0+.12,y1-.12):timber_column(g,x,y,z-2,z-.36,.20)
        if ident=='GroceryStore':grocery_terrace_brackets(g)
        if ident=='GroceryStore':
            # The perimeter uses butt joints. The former crossing beams had
            # duplicate underside patches hidden behind the dangling posts.
            for y in (y0,y1):beam_joint(g,(x0-.09,y,z-.24),(x1+.09,y,z-.24),.18,.24)
            for x in (x0,x1):beam_joint(g,(x,y0+.09,z-.24),(x,y1-.09,z-.24),.18,.24)
        else:
            for y in (y0,y1):beam_joint(g,(x0,y,z-.24),(x1,y,z-.24),.18,.24)
            for x in (x0,x1):beam_joint(g,(x,y0,z-.24),(x,y1,z-.24),.18,.24)
    if ident!='Restaurant':
        for i in range(1,3):
            x=x0+(x1-x0)*i/3
            g.box((x,(y0+y1)/2,z-.006),(.014,y1-y0-.09,.01),IRON)
    inset=.10 if ident=='Restaurant' else 0
    for side,a,b in [('Front',(x0+inset,y0+inset),(x1-inset,y0+inset)),('Rear',(x0+inset,y1-inset),(x1-inset,y1-inset)),
                     ('Left',(x0+inset,y0+inset),(x0+inset,y1-inset)),('Right',(x1-inset,y0+inset),(x1-inset,y1-inset))]:
        # Restaurant rail posts stand on tile boundaries: an opened section
        # leaves exactly its own tile open.
        if ident=='Restaurant':rails.run_grid('RoofTerrace'+side,a,b,z,RESTAURANT_ORIGIN)
        else:rails.run('RoofTerrace'+side,a,b,z)
    # The restaurant's existing roof slab is player-owned space. No fixed
    # furniture or shrubs consume its three-by-three construction area.
    if ident!='Restaurant':
        shrub_scale=.40 if ident=='GroceryStore' else .46
        shrub_x=(x0+.65,x1-.36) if ident=='Hospital' else (x0+.36,x1-.36)
        for x in shrub_x:plant(g,'Shrub.IronTeeth',(x,y1-.23,z),shrub_scale)
        bench_x=(x0+x1)/2
        for yy in (y1-.39,y1-.25):g.box((bench_x,yy,z+.38),(.84,.12,.06),PLANK)
        for x in (bench_x-.34,bench_x+.34):
            g.box((x,y1-.32,z+.18),(.055,.27,.36),IRON)
            g.box((x,y1-.17,z+.45),(.05,.05,.53),IRON)
        g.box((bench_x,y1-.17,z+.62),(.84,.06,.16),PLANK)
    # Open, external stair landing; no baked stair or decor in the build zone.
    terrace['stairApproach']=[x1+.5,y0+.5,z]
    if ident=='Restaurant':restaurant_roof_stairhead(g,terrace)
    else:terrace_access_house(g,terrace,left_facing=ident=='FisheryWorks',model=ident)


def restaurant_door(g,ident):
    d=RESTAURANT_DOORS[ident];p=restaurant_source(d['position'])
    from building_components import recipe
    g.include_component(recipe('Restaurant','Door.'+ident))
    g.doorways.append({'id':ident,'position':list(p),'outward':d['outward'],
                      'width':d['width'],'internalConnection':'BuildingInterior'})
    x,y,z=p
    # One-layer storeys (2026-10-30): the lamps flank the door at its own
    # storey, below the head fascia.
    for dx in (-.62,.62):wall_lamp(g,x+dx,y+.17,z+.50)


def restaurant_roof_stairhead(g,terrace):
    # 2026-10-30 compaction: one layer tall with a flat cast cap.
    part=Geometry('Restaurant roof stairhead')
    grid_room(part,'RoofStairhead',[0,0,0,1,2,1],[0,0,0],(.5,1.0),
              exterior={'front':[(0,1)],'back':[(0,1)],'left':[(0,2)],'right':[(0,2)]},wall_style='storey')
    # The portal is a separate asset. Its adjacent lamps remain part of the
    # stairhead decoration, so repairing a door does not rebuild them.
    for dx in (-.62,.62):wall_lamp(part,.5+dx,.17,.50)
    # Explicit quarter-turn: this is the right-facing face at native X=6, Y=3.5.
    # Geometry stores Blender's (-X,-Y,Z); compose in authored coordinates.
    local=[(-v[0],-v[1],v[2]) for v in part.vertices]
    points=[restaurant_source((6-y,3+x,3+z)) for x,y,z in local]
    face_offset=len(g.faces)
    for face,material,uv,source in zip(part.faces,part.materials,part.face_uvs,part.face_sources,strict=True):
        g.add([points[i] for i in face],[tuple(range(len(face)))],material)
        g.face_uvs[-1]=uv
        g.face_sources[-1]=source
    for mount in part.window_mounts:
        transform=lambda p:restaurant_source((6-p[1],3+p[0],3+p[2]))
        g.window_mounts.append({**mount,'anchor':transform(mount['anchor']),
            'outward':[-mount['outward'][1],mount['outward'][0],mount['outward'][2]],
            'faceRange':[v+face_offset for v in mount['faceRange']],
            'rearEdges':[[transform(p) for p in edge] for edge in mount['rearEdges']]})
    b=RESTAURANT_ROOMS['RoofStairhead']
    g.structural_parts.append({'id':'RoofStairhead','kind':'room','bounds':b,
        'pickingBoxes':[{'center':[5,3.5,3.5],'size':[2,1,1]}]})
    d=RESTAURANT_DOORS['RoofTerraceDoor']
    from building_components import recipe
    g.include_component(recipe('Restaurant','Door.RoofTerraceDoor'))
    door={'id':'RoofTerraceDoor','position':list(restaurant_source(d['position'])),
          'outward':d['outward'],'width':d['width'],'internalConnection':'BuildingInterior'}
    g.doorways.append(door);terrace['accessDoor']=door
    # Flat cap: a cast slab on the tile lines over the one-layer walls, with
    # a forged steel drip strip set in along its edges.
    cx,cy,_=restaurant_source((5,3.5,0))
    g.box((cx,cy,3.93),(2,1,.14),CIVIC_CONCRETE)
    for dy in (-.43,.43):g.box((cx,cy+dy,4.015),(1.94,.06,.03),IRON)
    for dx in (-.97,.97):g.box((cx+dx,cy,4.015),(.06,.80,.03),IRON)


def terrace_access_house(g,terrace,left_facing,model,*,storey=False):
    """Closed stairhead joined to the upper hall, opening onto the roof deck.

    `storey=True` (2026-10-30 compaction) builds it one layer tall: a .95
    room, lamps beside the door at its storey, a low gable and a small rear
    window."""
    x0,y0,x1,y1=terrace['bounds'];z=terrace['layer'];cy=(y0+y1)/2
    face=x1-.18 if left_facing else x0+.30
    part=Geometry('Terrace stairhead')
    base_spans={'front':[(-.64,.64)],'back':[],'left':[(.25,.73)],'right':[(.25,.73)]} if left_facing else None
    height,lamp_z,ridge,window=(.95,.50,.38,(.48,.45)) if storey else (1.55,1.20,.50,(.82,.8))
    framed_room(part,-.64,.15,.64,1.35,z,z+height,2,(0,1.0,1.0),base_spans=base_spans,
                wall_style='storey' if storey else 'banded')
    for dx in (-.62,.62):wall_lamp(part,dx,.17,z+lamp_z)
    roof_bearing(part,-.64,.15,.64,1.35,z+height,z+height+.07)
    gabled_roof(part,-.78,-.10,.78,1.49,z+height+.07,z+height+.07+ridge,855)
    glazing(part,0,1.41,z+window[0],window[1],'back')
    vertices=[]
    for vx,vy,vz in part.vertices:
        x,y=-vx,-vy
        vertices.append((face+y,cy-x,vz) if left_facing else (face-y,cy+x,vz))
    face_offset=len(g.faces)
    for polygon,material,uv,source in zip(part.faces,part.materials,part.face_uvs,part.face_sources,strict=True):
        g.add([vertices[i] for i in polygon],[tuple(range(len(polygon)))],material)
        g.face_uvs[-1]=uv
        g.face_sources[-1]=source
    for mount in part.window_mounts:
        transform=lambda p:(face+p[1],cy-p[0],p[2]) if left_facing else (face-p[1],cy+p[0],p[2])
        nx,ny,nz=mount['outward']
        g.window_mounts.append({**mount,'anchor':transform(mount['anchor']),
            'outward':[ny,-nx,nz] if left_facing else [-ny,nx,nz],
            'faceRange':[v+face_offset for v in mount['faceRange']],
            'rearEdges':[[transform(p) for p in edge] for edge in mount['rearEdges']]})
    from building_components import recipe
    g.include_component(recipe(model,'Door.RoofTerraceDoor'))
    door={'id':'RoofTerraceDoor','position':[face,cy,z],'outward':[-1,0] if left_facing else [1,0],
          'width':1.0,'internalConnection':'BuildingInterior'}
    g.doorways.append(door);terrace['accessDoor']=door


def civic_service_details(g,x0,y0,x1,y1):
    """Useful-looking exterior machinery and signage instead of more windows."""
    # Blue service duct, access hatch, louvres, pressure lines and wall meters.
    for x in (x0+.22,x1-.22):
        round_pipe(g,[(x,y1+.13,.65),(x,y1+.13,3.65),(x+.16,y1+.13,3.65)],.055)
        for z in (.8,1.7,2.8,3.5):g.box((x,y1+.13,z),(.18,.14,.05),IRON)
    cx=(x0+x1)/2
    g.box((cx,y1+.09,1.12),(.72,.17,.76),ROOF)
    g.box((cx,y1+.19,1.12),(.59,.035,.63),CIVIC_FORGED_PANEL)
    for i in range(5):g.box((cx,y1+.23,.94+i*.09),(.45,.065,.027),IRON)
    gauge(g,x1-.20,y1+.23,2.65,.10)
    # Projecting facade ventilation and small blue metal labels below windows.
    for x in (x0+.4,x1-.4):
        g.box((x,y0-.12,2.48),(.38,.09,.24),ROOF)
        for z in (2.43,2.50,2.57):g.box((x,y0-.175,z),(.29,.025,.02),IRON)


def timber_column(g,x,y,bottom,top,w=.19,*,steel_channels=True,collars=True):
    """Timber core with visible steel channels, concrete feet and anchor bolts."""
    core_bottom=.53 if bottom==0 else bottom
    g.box((x,y,(core_bottom+top)/2),(w,w,top-core_bottom),WOOD)
    if steel_channels:
        for side in (-1,1):
            g.box((x+side*w*.44,y,(core_bottom+top)/2),(.035,w+.05,top-core_bottom-.04),IRON)
    if bottom==0:
        g.box((x,y,.24),(w+.11,w+.11,.48),CIVIC_CONCRETE)
        g.box((x,y,.50),(w+.13,w+.13,.06),IRON)
    if not collars:return
    # The collars stay 5 mm inside the column ends: a collar box face flush
    # with an end would overlap the column's end face.
    collar_levels=((core_bottom+top)/2,) if top-core_bottom<.46 else (core_bottom+.12,top-.12)
    for level in collar_levels:collar(g,x,y,level,w)


def beam_joint(g,a,b,w=.18,depth=.18,*,plates=True):
    """Riveted steel girder: flat flanges and dark forged web."""
    g.beam(a,b,w,depth,WOOD)
    # End plates sit within the beam span, clear of the adjoining corner plate.
    span=math.dist(a,b)
    # Short tenons need no plate; short lintels have one central plate.
    # The .27-wide plates need a .30 end setback at a right-angle joint.
    # Percentage-based stations put plates across one another on short rooms.
    plate_stations=() if span<.30 or not plates else ((span/2,) if span<.90 else (.30,span-.30))
    for distance in plate_stations:
        t=distance/span
        p=tuple(a[i]+(b[i]-a[i])*t for i in range(3))
        if abs(b[0]-a[0])>=abs(b[1]-a[1]):
            g.box((p[0],p[1]-.12,p[2]),(.27,.035,depth+.06),IRON)
        else:
            g.box((p[0]-.12,p[1],p[2]),(.035,.27,depth+.06),IRON)


def facade_band(g,x0,y0,x1,y1,z,height,material,door=None):
    ranges=[(x0,x1)] if door is None else [(x0,door[0]-door[1]/2),(door[0]+door[1]/2,x1)]
    for a,b in ranges:g.box(((a+b)/2,y0-.047,z),(b-a,.09,height),material)
    g.box(((x0+x1)/2,y1+.047,z),(x1-x0,.09,height),material)
    for x,sign in ((x0,-1),(x1,1)):
        g.box((x+sign*.049,(y0+y1)/2,z),(.09,y1-y0,height),material)


def framed_room(g,x0,y0,x1,y1,bottom,top,bays=3,front_door=None,infill=CIVIC_ORANGE_PANEL,*,base_spans=None,trim='full',wall_style='banded'):
    """Opaque timber shell with visible individual cladding and bolted framing.

    `wall_style='storey'` (opt-in, 2026-10-30 compaction) dresses a room of
    about one layer like a storey: a base course, the infill and a forged
    head band, instead of the single plank band the default gives a room under
    1.5 tall."""
    # Each wall face is authored once. Material bands meet at their edges;
    # plaster is not a second skin laid over a full wooden wall.
    # The shell extends to its exact floor and ceiling. The framing is a
    # projecting physical member, not a substitute for a sealed wall edge:
    # its softened bottom/top edges previously left 2–4 cm open ribbons.
    lo,hi=bottom,top
    if wall_style not in ('banded','storey'):raise ValueError('Unknown framed room wall style '+str(wall_style))
    bands=[(lo,hi,PLANK)] if top-bottom<=1.5 else [
        (lo,bottom+.53,CIVIC_CONCRETE if bottom==0 else PLANK),
        (bottom+.53,top-.36,infill),(top-.36,hi,CIVIC_FORGED_PANEL)]
    if wall_style=='storey':
        if not .8<=top-bottom<=1.1:raise ValueError('Storey framed rooms are about one layer tall')
        bands=[(lo,bottom+.22,CIVIC_CONCRETE if bottom==0 else PLANK),(bottom+.22,top-.20,infill),(top-.20,hi,CIVIC_FORGED_PANEL)]
    for low,high,material in bands:
        for y,sign,door in ((y0,-1,front_door),(y1,1,None)):
            runs=[(x0-.06,x1+.06)]
            if door is not None and low<bottom+door[2]:
                left,right=door[0]-door[1]/2,door[0]+door[1]/2
                runs=[(x0-.06,left),(right,x1+.06)]
            for a,b in runs:
                if b>a:facade_panel(g,'Y',y+sign*.06,a,b,low,high,sign>0,material)
            if door is not None and low<bottom+door[2]<high:
                head=bottom+door[2]
                facade_panel(g,'Y',y+sign*.06,door[0]-door[1]/2,door[0]+door[1]/2,head,high,sign>0,material)
        for x,sign in ((x0,-1),(x1,1)):
            facade_panel(g,'X',x+sign*.06,y0-.06,y1+.06,low,high,sign>0,material)
    # Joined wings declare the exposed base spans explicitly. This authors
    # proper intersections instead of overlapping complete room frames.
    if base_spans is None:
        base_spans={'front':[(x0,x1)],'back':[(x0,x1)],'left':[(y0+.10,y1-.10)],'right':[(y0+.10,y1-.10)]}
    if set(base_spans)!={'front','back','left','right'}:raise ValueError('Declare all room base edges')
    if trim not in ('full','restrained'):raise ValueError('Unknown framing trim '+str(trim))
    # Restrained trim keeps the frame members but drops repeated plates and
    # folded collars; small roof rooms read as one joined timber frame.
    plates=trim=='full'
    for side,y in (('front',y0),('back',y1)):
        for lo,hi in base_spans[side]:
            runs=[(lo,hi)]
            if side=='front' and front_door is not None:
                cx,width,height=front_door
                runs=[(a,b) for a,b in ((lo,min(hi,cx-width/2)),(max(lo,cx+width/2),hi)) if b>a]
            for a,b in runs:beam_joint(g,(a,y,bottom+.12),(b,y,bottom+.12),.20,.20,plates=plates)
        beam_joint(g,(x0,y,top-.14),(x1,y,top-.14),.20,.20,plates=plates)
        for i in range(bays+1):
            xx=x0+(x1-x0)*i/bays
            post_bottom=bottom+.22
            if y==y0 and front_door is not None and abs(xx-front_door[0])<front_door[1]/2+.13:
                post_bottom=bottom+front_door[2]
            # One-layer storey posts are too short for two collars.
            if post_bottom<top-.24:timber_column(g,xx,y,post_bottom,top-.24,.20,steel_channels=False,collars=plates and wall_style!='storey')
    for side,x in (('left',x0),('right',x1)):
        for a,b in base_spans[side]:beam_joint(g,(x,a,bottom+.12),(x,b,bottom+.12),.20,.20,plates=plates)
        beam_joint(g,(x,y0+.10,top-.14),(x,y1-.10,top-.14),.20,.20,plates=plates)
        for i in range(1,bays):timber_column(g,x,y0+(y1-y0)*i/bays,bottom+.22,top-.24,.19,steel_channels=False,collars=plates and wall_style!='storey')
    # The cast facade plinth supports the wall frame; do not duplicate it
    # with overlapping corner footings where adjacent rooms meet.
    # Wood grain/wear comes from the native atlas. The former tiny splinter
    # beams lay behind the opaque wall plane and were never visible.
    # The sealed room interior (opaque windows, component doors) is a hidden
    # volume for the enclosed-face cull: the inner halves of its posts,
    # collars and beams are never seen. Its top stays below the head beams
    # (deck-board joints above), and the doorway recess stays visible.
    exposed=[]
    if front_door is not None:
        cx,width,height=front_door
        exposed.append(((cx-width/2-.2,y0-.08,bottom-.01),(cx+width/2+.2,y0+.9,bottom+height+.3)))
    g.declare_hidden_volume((x0-.06,y0-.06,bottom),(x1+.06,y1+.06,top-.25),exposed)


def gabled_roof(g,x0,y0,x1,y1,eave,ridge,seed,*,trim='full',sheet=.42):
    """Joined roof panels, separate iron straps, gable cladding and ridge cap.

    `trim='restrained'` keeps every sheet, strap, bargeboard and the iron ridge
    cap, but omits the folded corner brackets and repeated beam plates. A roof
    cluster then reads at game zoom as a few bold timber lines.
    """
    if trim not in ('full','restrained'):raise ValueError('Unknown roof trim '+str(trim))
    plates=trim=='full'
    # Sheets about `sheet` wide (42 cm; was 27): triangle budget, 20k grand
    # cap (2026-10-29). The gable boards stay 15 cm: their stepped tops set
    # how much of each gable cell face is flat wall, and the connection-face
    # measurement (measure_connection_faces.py) registers shaft/pipe sockets
    # from it.
    mid=(x0+x1)/2;n=math.ceil((y1-y0)/sheet)
    # Real under-roof sheathing closes the sheet joints. The visible sheets
    # retain their individual edges, but their 12 mm joints no longer open
    # into an empty attic. This is a distinct physical layer below their
    # 55 mm thickness, not coplanar faces or a shader depth offset.
    for x in (x0,x1):
        points=[(x,y0,eave-.055),(mid,y0,ridge-.055),
                (mid,y1,ridge-.055),(x,y1,eave-.055)]
        g.add(points,[(0,1,2,3) if x==x0 else (3,2,1,0)],ROOF)
    # Only the outward soffit is drawn. There is no ceiling/interior mesh
    # inside the room. It closes the overhanging eaves from an oblique view.
    g.add([(x0,y0,eave-.10),(x1,y0,eave-.10),(x1,y1,eave-.10),(x0,y1,eave-.10)],
          [(3,2,1,0)],PLANK)
    for y,sign in ((y0,1),(y1,-1)):
        plane=y+sign*.055
        g.add([(x0,plane,eave-.10),(x1,plane,eave-.10),(mid,plane,ridge-.055)],
              [(0,1,2) if sign==1 else (2,1,0)],PLANK)
    for i in range(n):
        y=y0+(i+.5)*(y1-y0)/n
        for x in (x0,x1):
            g.beam((x,y,eave),(mid,y,ridge),(y1-y0)/n-.012,.055,ROOF)
    for y in (y0,y1):
        count=math.ceil((x1-x0)/.15)
        for i in range(count):
            x=x0+(i+.5)*(x1-x0)/count;z=eave+(ridge-eave)*(1-abs(x-mid)/((x1-x0)/2))
            g.box((x,y,(z+eave)/2),((x1-x0)/count-.008,.09,z-eave+.015),PLANK)
        beam_joint(g,(x0,y,eave-.05),(x1,y,eave-.05),.21,.20,plates=plates)
        for x in (x0,x1):
            # The bargeboard starts 12 mm down-slope of the eave line: its end
            # cap was coplanar with the first and last sheets' end caps, which
            # the folded corner brackets had covered.
            run=math.hypot(mid-x,ridge-eave)
            start=(x-(mid-x)*.012/run,y,eave-(ridge-eave)*.012/run)
            g.beam(start,(mid,y,ridge),.17,.18,WOOD)
            if plates:collar(g,x,y,eave,.23)
            # One plain timber block closes each eave joint instead of a
            # four-plate, sixteen-bolt bracket.
            else:g.box((x,y,eave),(.27,.27,.21),WOOD)
        if plates:collar(g,mid,y,ridge,.22)
        else:g.box((mid,y,ridge),(.24,.24,.22),WOOD)
    for x in (x0,x1):beam_joint(g,(x,y0,eave-.06),(x,y1,eave-.06),.19,.20,plates=plates)
    g.beam((mid,y0-.03,ridge+.05),(mid,y1+.03,ridge+.05),.15,.09,IRON)
    for t in (.27,.72):
        y=y0+(y1-y0)*t
        for x in (x0,x1):g.beam((x,y,eave+.04),(mid,y,ridge+.04),.07,.023,IRON)
    # Triangle budget: the 28 random 7x4 mm wear scratches were sub-pixel at
    # the closest game zoom; the native RoofPlanks atlas paints the wear.


def roof_bearing(g,x0,y0,x1,y1,ceiling,eave):
    """Exterior attic curb joining a whole-height room to its roof."""
    if eave<=ceiling:raise ValueError('Roof bearing requires an explicit positive attic rise')
    for y,positive in ((y0,False),(y1,True)):
        facade_panel(g,'Y',y,x0,x1,ceiling,eave,positive,PLANK)
    for x,positive in ((x0,False),(x1,True)):
        facade_panel(g,'X',x,y0,y1,ceiling,eave,positive,PLANK)


def dormer(g,x,y,z,w=1.0,*,trim='full'):
    framed_room(g,x-w/2,y,x+w/2,y+.75,z,z+.65,1,trim=trim)
    glazing(g,x,y-.06,z+.36,0.70,style='diamond')
    roof_bearing(g,x-w/2,y,x+w/2,y+.75,z+.65,z+.68)
    gabled_roof(g,x-w/2-.12,y-.13,x+w/2+.12,y+.85,z+.68,z+.99,91,trim=trim)


def chimney(g,x,y,bottom,height,*,emits):
    """Masonry stack with an iron top frame. `emits` is the vanilla effect at
    its mouth (a lategame_kit.EMITTER_KINDS entry, see tools/vanilla_smoke.mjs)
    or None for no effect; every caller decides explicitly. The emitter adds
    no geometry: register_smoke_emitters.py writes it into the building's
    smoke registration."""
    n=math.ceil(height/.30)
    for i in range(n):
        z=bottom+(i+.5)*height/n
        g.box((x,y,z),(.46,.47,height/n-.015),KILN_STONE if i%3 else KILN_STONE_LIGHT)
        if i%2==0:
            g.box((x,y,z),(.50,.51,.06),IRON)
    for xx in (x-.24,x+.24):g.box((xx,y,bottom+height),(.08,.55,.16),IRON)
    # The cross rails end on the side rails' inner faces (x +-.20): with no
    # bevel modifier their tops would otherwise overlap coplanar by 1 cm.
    for yy in (y-.24,y+.24):g.box((x,yy,bottom+height),(.40,.08,.16),IRON)
    g.box((x,y,bottom+height+.006),(.40,.40,.012),KILN_SOOT)
    if emits is not None:
        # Mouth: top of the iron frame; its inner opening is 0.40 square.
        emitter(g,emits,x,y,bottom+height+.08,.20)


def balcony(g,rails,ident,x0,y0,x1,y1,z=2,edges=('front','back','left','right'),support_corners=((-1,-1),(-1,1),(1,-1),(1,1))):
    deck(g,x0,y0,x1,y1,z-.07)
    for sx,sy in support_corners:
        x=x0+.12 if sx==-1 else x1-.12
        y=y0+.12 if sy==-1 else y1-.12
        timber_column(g,x,y,z-2,z-.16,.18)
        for dx in (-1,1):
            xx=x+dx*.40
            if x0<xx<x1:g.beam((x,y,z-.60),(xx,y,z-.14),.10,mat=WOOD)
    endpoints={'front':((x0,y0),(x1,y0)),'back':((x0,y1),(x1,y1)),
               'left':((x0,y0),(x0,y1)),'right':((x1,y0),(x1,y1))}
    for side in edges:rails.run(ident+side,*endpoints[side],z)


def balcony_storey(g,rails,ident,x0,y0,x1,y1,z=1,edges=('front','back','left','right'),support_corners=((-1,-1),(-1,1),(1,-1),(1,1))):
    """balcony for a one-layer storey (2026-10-30 compaction): its corner
    posts rise one layer from the floor below (balcony's are two), with the
    knee braces lower to suit."""
    deck(g,x0,y0,x1,y1,z-.07)
    for sx,sy in support_corners:
        x=x0+.12 if sx==-1 else x1-.12
        y=y0+.12 if sy==-1 else y1-.12
        timber_column(g,x,y,z-1,z-.16,.18)
        for dx in (-1,1):
            xx=x+dx*.32
            if x0<xx<x1:g.beam((x,y,z-.45),(xx,y,z-.14),.09,mat=WOOD)
    endpoints={'front':((x0,y0),(x1,y0)),'back':((x0,y1),(x1,y1)),
               'left':((x0,y0),(x0,y1)),'right':((x1,y0),(x1,y1))}
    for side in edges:rails.run(ident+side,*endpoints[side],z)


def planter(g,x,y,z,width=.86,seed=1,side=False,species='DandelionMature',mount=None,depth=.32):
    # The lean bin has no rivet heads, so no strict-mode proud rivets either.
    lean_bin(g,(x,y,z),(width,depth,.27) if not side else (depth,width,.27))
    if mount is not None:
        nx,ny={'front':(0,1),'left':(1,0),'right':(-1,0)}[mount]
        for offset in (-width*.35,width*.35):
            xx=x+(0 if side else offset);yy=y+(offset if side else 0)
            g.beam((xx,yy,z-.025),(xx+nx*.35,yy+ny*.35,z-.025),.035,mat=IRON)
            g.beam((xx+nx*.35,yy+ny*.35,z-.025),(xx+nx*.35,yy+ny*.35,z-.30),.035,mat=IRON)
    # Whole original leaf/stem meshes, original UVs and vertex colours. The
    # uniform .29 scale fits the authored planter depth without distorting leaves.
    count=math.floor((width-.10)/.24)
    if count<1:raise ValueError('Planter is too narrow for an authored native plant')
    g.box((x,y,z+.23),(width-.06,depth-.06,.035) if not side else (depth-.06,width-.06,.035),KILN_SOOT)
    for i in range(count):
        along=(i-(count-1)/2)*.24
        xx=x+(0 if side else along);yy=y+(along if side else 0)
        plant(g,species,(xx,yy,z+.245),.29,((seed+i)%4)*90)


def crate(g,x,y,z,w=.55,h=.5,*,proud_rivets=False):
    bin(g,(x,y,z),(w,w*.85,h),None,proud_rivets=proud_rivets)
    for i in range(4):g.box((x-w*.375+i*w*.25,y,z+h+.035),(w*.24,w*.85,.05),PLANK)
    for yy in (y-w*.28,y+w*.28):g.box((x,yy,z+h+.085),(w+.04,.06,.05),WOOD)
    # Strict mode (proud_rivets) stands the brace 1 cm clear of the corner irons.
    brace_y=y-w*.44-(.01 if proud_rivets else 0)
    g.beam((x-w*.39,brace_y,z+.08),(x+w*.39,brace_y,z+h-.07),.055,.025,WOOD)


def supply_pile(g,x,y,z,medical=False,*,proud_rivets=False):
    crate(g,x,y,z,.58,.53,proud_rivets=proud_rivets);crate(g,x+.61,y+.04,z,.50,.45,proud_rivets=proud_rivets)
    # Strict mode sets the top crate 2 cm back so its corner irons are not
    # coplanar with the lid batten of the crate below.
    crate(g,x+.22,y+(.04 if proud_rivets else .02),z+.59,.43,.38,proud_rivets=proud_rivets)
    if medical:
        for xx,zz in ((x,z+.27),(x+.22,z+.78)):
            g.box((xx,y-.28,zz),(.12,.018,.30),LIME);g.box((xx,y-.29,zz),(.29,.02,.12),LIME)


def plate(g,x,y,z,meal=True):
    # 8 sides, the rim as the plate's own edge and one portion (was a 12-side
    # plate, a 12-side rim ring and two portions, about 240 triangles): a 24 cm
    # plate is under 10 px wide at normal zoom.
    g.cylinder((x,y,z+.002),.12,.026,LIME,'Z',8)
    if meal:
        # One low block portion (12 triangles; a 7-sided rock was 52).
        g.box((x+.01,y,z+.034),(.12,.09,.04),SAND)


def terrace_table(g,x,y,z=2,chair_axis='Y'):
    if chair_axis not in ('X','Y'):raise ValueError('Dining chairs require an explicit X or Y axis')
    g.box((x,y,z+.58),(.65,.53,.065),PLANK)
    for dx in (-.25,.25):
        for dy in (-.19,.19):g.box((x+dx,y+dy,z+.285),(.055,.055,.57),WOOD)
    for sign in (-1,1):
        cx=x+(sign*.65 if chair_axis=='X' else 0)
        cy=y+(sign*.65 if chair_axis=='Y' else 0)
        facing=[-sign,0] if chair_axis=='X' else [0,-sign]
        g.visitor_seats.append({'id':'Seat'+str(len(g.visitor_seats)),'position':[cx,cy,z+.3375],
            'seatSurfaceHeight':z+.3375,'deckHeight':z,'facing':facing,'animation':'Sitting',
            'chairBounds':[[cx-(.145 if chair_axis=='X' else .165),cy-(.165 if chair_axis=='X' else .145)],
                           [cx+(.145 if chair_axis=='X' else .165),cy+(.165 if chair_axis=='X' else .145)]],
            'tableCenter':[x,y,z+.58]})
        # Local Y points towards the chair back. Rotate the complete chair,
        # including its anchor, instead of changing only the visual seat.
        def chair_box(dx,dy,dz,sx,sy,sz,mat):
            if chair_axis=='X':g.box((cx+dy,cy+dx,z+dz),(sy,sx,sz),mat)
            else:g.box((cx+dx,cy+dy,z+dz),(sx,sy,sz),mat)
        chair_box(0,0,.31,.33,.29,.055,PLANK)
        for dx in (-.13,.13):
            for dy in (-.10,.10):chair_box(dx,dy,.135,.043,.043,.27,WOOD)
        # Back posts stand 7.5 mm inside the seat edge; at .12 their faces
        # were 2.5 mm from the seat's and overlapped it.
        for dx in (-.13,.13):chair_box(dx,sign*.115,.47,.043,.045,.40,WOOD)
        # One back rail (was two): triangle budget, 20k grand cap.
        chair_box(0,sign*.115,.57,.217,.045,.07,PLANK)
    g.box((x,y,z+.623),(.57,.47,.009),CLOTH)
    for dx in (-.17,.17):plate(g,x+dx,y,z+.64)
    g.cylinder((x,y+.11,z+.70),.034,.13,BRASS,'Z',6)


def sign_emblem(g,x,y,z,kind,scale=1):
    s=scale
    if kind=='Hospital':
        g.cylinder((x,y,z),.38*s,.025,ROOF,'Y',24)
        g.box((x,y-.025,z),(.17*s,.025,.56*s),LIME);g.box((x,y-.028,z),(.56*s,.025,.17*s),LIME)
    elif kind=='Restaurant':
        points=[(-.34,.04),(-.23,-.18),(0,-.25),(.23,-.18),(.34,.04)]
        for a,b in zip(points,points[1:]):g.beam((x+a[0]*s,y,z+a[1]*s),(x+b[0]*s,y,z+b[1]*s),.045*s,mat=LIME)
        g.beam((x-.34*s,y,z+.04*s),(x+.34*s,y,z+.04*s),.04*s,mat=LIME)
        for dx in (-.18,0,.18):
            g.beam((x+dx*s,y,z+.13*s),(x+(dx-.045)*s,y,z+.24*s),.027*s,mat=LIME)
            g.beam((x+(dx-.045)*s,y,z+.24*s),(x+(dx+.025)*s,y,z+.37*s),.027*s,mat=LIME)
        g.beam((x+.20*s,y,z-.12*s),(x+.42*s,y,z+.27*s),.05*s,mat=LIME)
    elif kind=='GroceryStore':
        for yy in (-.16,-.06,.04):g.beam((x-.28*s,y,z+yy*s),(x+.28*s,y,z+yy*s),.028*s,mat=LIME)
        for dx in (-.27,-.14,0,.14,.27):g.beam((x+dx*s,y,z-.20*s),(x+dx*s,y,z+.10*s),.025*s,mat=LIME)
        g.ring((x,y,z+.12*s),.25*s,.027*s,.02,LIME,'Y',24)
        g.box((x,y+.01,z+.03*s),(.60*s,.025,.06*s),LIME)
        for dx in (-.13,.06,.19):g.rock((x+dx*s,y-.03,z+.17*s),(.15*s,.035,.15*s),LIME,34+int(dx*100))
    elif kind=='FisheryWorks':
        outline=[(-.4,0),(-.22,.19),(.12,.17),(.27,.07),(.48,.25),(.48,-.22),(.27,-.07),(.12,-.18),(-.22,-.16)]
        g.add([(x+a*s,y,z+b*s) for a,b in outline],[tuple(range(len(outline)))],LIME)
        g.cylinder((x-.25*s,y-.02,z+.04*s),.028*s,.02,IRON,'Y',12)
        g.beam((x-.13*s,y-.025,z-.11*s),(x-.10*s,y-.025,z+.13*s),.025*s,mat=WOOD)
    else:raise ValueError(kind)


def hanging_board(g,parts,kind,x,y,z,w=1.1):
    # Large carved board with restrained pendulum movement, attached by rings.
    beam_joint(g,(x-w*.63,y+.34,z+.63),(x+w*.63,y+.34,z+.63),.15,.15)
    for xx in (x-w*.36,x+w*.36):
        g.beam((xx,y+.36,z+.63),(xx,y-.05,z+.63),.09,mat=IRON)
        for i in range(4):g.ring((xx,y-.05,z+.50-i*.055),.044,.013,.024,IRON,'Y' if i%2 else 'X',6)
    m=Geometry(kind+'.CarvedSign',(x,y,z+.52))
    for i in range(5):m.box((x,y,z-.38+i*.19),(w,.10,.185),PLANK)
    for xx in (x-w/2,x+w/2):
        m.box((xx,y-.025,z),(.07,.13,1.0),WOOD)
    sign_emblem(m,x,y-.09,z,kind,w*.77)
    parts.append((m,'SWAY',.018))


def hanging_board_storey(g,parts,kind,x,y,z,w=1.1,name=None):
    """hanging_board for a one-layer storey (2026-10-30 compaction): three
    carved boards (.57 tall, was five, .95) on two links per ring chain, the
    beam .40 above the board centre (was .63). Appended beside hanging_board,
    whose buildings keep it unchanged."""
    beam_joint(g,(x-w*.63,y+.34,z+.40),(x+w*.63,y+.34,z+.40),.15,.15)
    for xx in (x-w*.36,x+w*.36):
        g.beam((xx,y+.36,z+.40),(xx,y-.05,z+.40),.09,mat=IRON)
        for i in range(2):g.ring((xx,y-.05,z+.32-i*.055),.044,.013,.024,IRON,'Y' if i%2 else 'X',6)
    m=Geometry(name or kind+'.CarvedSign',(x,y,z+.29))
    for i in range(3):m.box((x,y,z-.19+i*.19),(w,.10,.185),PLANK)
    for xx in (x-w/2,x+w/2):
        m.box((xx,y-.025,z),(.07,.13,.60),WOOD)
    sign_emblem(m,x,y-.09,z,kind,w*.55)
    parts.append((m,'SWAY',.018))


def awning(g,x0,y0,x1,y1,front_z,back_z,striped=False):
    if not striped:
        lean_sheet_roof(g,x0,y0,x1,y1,front_z,back_z)
        return
    n=math.ceil((x1-x0)/.24)
    for i in range(n):
        a=x0+i*(x1-x0)/n;b=x0+(i+1)*(x1-x0)/n-.004
        mid_y=y0+(y1-y0)*.4;mid_z=front_z+(back_z-front_z)*.63
        v=[(x,y,z) for y,z in ((y0,front_z),(mid_y,mid_z),(y1,back_z)) for x in (a,b)]
        g.add(v,[(0,1,3,2),(2,3,5,4)],CLOTH if i%2 else LIME)
        # Valances start 2 mm in from each stripe's edge: the first one's end
        # face otherwise shares the front beam's end-cap plane (no bevel).
        g.box(((a+b)/2+.001,y0,front_z-.08),(b-a-.002,.025,.16),CLOTH if i%2 else LIME)
    for x in (x0,x1):g.beam((x,y0,front_z),(x,y1,back_z),.055,mat=IRON)
    g.beam((x0,y0,front_z),(x1,y0,front_z),.06,mat=WOOD)


def component_doorway(g,model,ident):
    from building_components import DOOR_LAYOUTS,recipe
    door=DOOR_LAYOUTS[model][0][ident]
    x,y,z=door['position']
    if door['outward']!=[0,-1]:raise ValueError('Front doorway lamps require a front-facing component')
    # The native ground/deck provides this doorway's flush threshold surface.
    g.include_component(recipe(model,'Door.'+ident))
    g.doorways.append({'id':ident,'position':[x,y,z],'outward':[0,-1],
                      'width':DOOR_OUTER_WIDTH,'internalConnection':'BuildingInterior'})
    for dx in (-.62,.62):wall_lamp(g,x+dx,y+.17,z+1.20)


def component_doorway_storey(g,model,ident):
    """component_doorway for a one-layer storey (2026-10-30 compaction): the
    flanking lamps hang at the door's own storey (.36 up, was 1.20), under
    a one-layer framed room's head beam."""
    from building_components import DOOR_LAYOUTS,recipe
    door=DOOR_LAYOUTS[model][0][ident]
    x,y,z=door['position']
    if door['outward']!=[0,-1]:raise ValueError('Front doorway lamps require a front-facing component')
    g.include_component(recipe(model,'Door.'+ident))
    g.doorways.append({'id':ident,'position':[x,y,z],'outward':[0,-1],
                      'width':DOOR_OUTER_WIDTH,'internalConnection':'BuildingInterior'})
    for dx in (-.62,.62):wall_lamp(g,x+dx,y+.17,z+.36)


def wall_lamp(g,x,y,z,face='front'):
    nx,ny={'front':(0,-1),'back':(0,1),'left':(-1,0),'right':(1,0)}[face]
    xx,yy=x+nx*.21,y+ny*.21
    # 40 mm back plate (was 35): its face now stands clear of window frames
    # it is mounted beside (coplanar once the bevel modifier is gone).
    g.box((x,y,z+.12),(.12 if ny else .04,.04 if ny else .12,.22),IRON)
    # The arm starts 1 cm out, inside the back plate, and ends 1 cm short of
    # the lantern axis, inside the lamp: neither end cap lies on the wall or
    # lantern plane (coplanar with window frames there once the bevel
    # modifier is gone).
    g.beam((x+nx*.01,y+ny*.01,z+.16),(xx-nx*.01,yy-ny*.01,z+.16),.035,mat=IRON)
    # Six sides and no 12 mm cage bars (sub-pixel at normal zoom; triangle
    # budget, 20k grand cap, 2026-10-29).
    g.cylinder((xx,yy,z),.060,.19,GLOW,'Z',6)
    for zz in (z-.12,z+.12):g.cylinder((xx,yy,zz),.085,.025,IRON,'Z',6)


def deck_lamp(g,x,y,floor=2,face='right',*,collars=True,steel_channels=True):
    timber_column(g,x,y,floor,floor+1.04,.10,collars=collars,steel_channels=steel_channels)
    wall_lamp(g,x,y,floor+.85,face)


def glazing(g,x,y,z,scale=1,face='front',style='grand'):
    from architectural_windows import window
    window(g,x,y,z,scale,face,style)


def wall_windows(g,xs,y,z,scale=1,plants=False,face='front',style='grand'):
    for i,x in enumerate(xs):
        glazing(g,x,y,z,scale,face,style)
        if plants:planter(g,x,y-.22,z-.471*scale/2-.25,.471*scale+.14,11+i)


def roof_services(g,x,y,z):
    barrel(g,(x,y,z),3.5)
    round_pipe(g,[(x+.32,y,z+.83),(x+.58,y,z+.83),(x+.58,y,z-.40),(x+.58,y-.40,z-.40)],.055)
    gauge(g,x+.57,y-.46,z-.27,.09)


def framed_cross(g,x,y,z):
    g.box((x,y,z),(1.02,.12,1.06),WOOD)
    g.box((x,y-.075,z),(.88,.035,.92),PLANK)
    sign_emblem(g,x,y-.105,z,'Hospital',1.05)


def upper_hall(g,x0,y0,x1,y1,door_x,model,door_id):
    """A full third storey, individually framed small windows and cornices."""
    framed_room(g,x0,y0,x1,y1,4,6,5,(door_x,1.0,1.0))
    component_doorway(g,model,door_id)
    count=math.floor((x1-x0)/.62)
    for i in range(count):
        x=x0+(i+.5)*(x1-x0)/count
        if abs(x-door_x)>.62:glazing(g,x,y0-.06,4.97,1.0,style='lancet')
        glazing(g,x,y1+.06,4.97,1.0,'back','lancet')
        glazing(g,x,y0-.06,5.73,0.5,style='diamond')
        glazing(g,x,y1+.06,5.73,0.5,'back','diamond')
    for x,face in ((x0-.06,'left'),(x1+.06,'right')):
        count=math.floor((y1-y0)/.66)
        for i in range(count):
            y=y0+(i+.5)*(y1-y0)/count
            glazing(g,x,y,4.97,1.0,face,'lancet')
            glazing(g,x,y,5.73,0.5,face,'diamond')
    for z in (4.20,5.48,6.02):
        for y in (y0-.04,y1+.04):g.box(((x0+x1)/2,y,z),(x1-x0+.18,.14,.09),WOOD)
        for x in (x0-.04,x1+.04):g.box((x,(y0+y1)/2,z),(.14,y1-y0-.06,.09),WOOD)


def roof_lantern(g,x,y,z,w=1.4,depth=1.8,*,trim='full'):
    """Small glazed roof pavilion with its own two-stage roof, not an interior."""
    framed_room(g,x-w/2,y,x+w/2,y+depth,z,z+.85,2,trim=trim)
    for dx in (-.28,.28):
        glazing(g,x+dx,y-.06,z+.44,0.80,style='lancet')
        glazing(g,x+dx,y+depth+.06,z+.44,0.80,'back','lancet')
    for yy in (y+.40,y+depth-.4):
        glazing(g,x-w/2-.06,yy,z+.44,0.80,'left','lancet')
        glazing(g,x+w/2+.06,yy,z+.44,0.80,'right','lancet')
    roof_bearing(g,x-w/2,y,x+w/2,y+depth,z+.85,z+.91)
    gabled_roof(g,x-w/2-.19,y-.16,x+w/2+.19,y+depth+.16,z+.91,z+1.43,600,trim=trim)
    for xx in (x-w/2,x+w/2):g.cylinder((xx,y+.08,z+1.02),.038,.36,BRASS,'Z',8)


def hospital(g,parts):
    # Separate authoring module: two genuine ward wings and a central pavilion.
    from hospital_geometry import hospital as build_hospital
    return build_hospital(g,parts)


def service_counter(g,x,y,z=0,width=1.30,*,proud_rivets=False):
    bin(g,(x,y,z),(width,.62,.72),None,proud_rivets=proud_rivets)
    g.box((x,y,z+.78),(width+.10,.70,.10),PLANK)
    for i in range(4):
        xx=x-width*.34+i*width*.23
        plate(g,xx,y-.09,z+.85)
        g.ring((xx,y+.20,z+.90),.10,.025,.08,IRON,'Z',12)


# Exposed restaurant deck edges, as native (side, start, end) spans. Joined
# edges (another platform at the same height, or a room wall) carry no fascia.
RESTAURANT_FASCIA={
    'DiningFront':[('front',0,6),('left',0,1),('right',0,1)],
    'DiningSideFront':[('front',6,7),('right',1,2)],
    'DiningSide':[('right',2,7),('back',5,7)],
    'DiningRear':[],
    'UpperDiningFront':[('front',0,6),('left',0,2),('right',0,1)],
    'UpperDiningSideFront':[('front',6,7),('right',1,2)],
    'UpperDiningSide':[('right',2,7),('back',5,7)],
    'UpperDiningRear':[('back',1,5),('left',5,7)],
    # The main roof's edges carry the parapet; the room fascia closes below.
    'MainRoof':[],
    'RoofTerraceInner':[('front',5,7),('back',5,7)],
    'RoofTerraceOuter':[('front',7,9),('back',7,9),('right',2,5)],
}


def restaurant_roof_sign(g,parts):
    """Carved restaurant sign swinging from a steel gantry on the flat roof.

    2026-10-30 compaction: the front gable it hung from is gone. Two forged
    posts stand on the front parapet and carry a cross beam; the board hangs
    between them over the parapet, facing the street. Gantry and swing stay in
    the parapet's edge strip (native y 2.0..2.13, 2 <= x < 4, z 3-4), so the
    roof cells behind stay buildable (no-clutter rule).
    """
    x=restaurant_source((3,0,0))[0];y=restaurant_source((0,2.08,0))[1];w=1.42;z=3.52
    for xx in (x-.80,x+.80):
        g.box((xx,y,(3.23+3.77)/2),(.09,.09,3.77-3.23),IRON)
        g.box((xx,y,3.255),(.10,.10,.05),IRON)
    g.beam((x-.86,y,3.82),(x+.86,y,3.82),.10,.10,WOOD)
    for xx in (x-w*.36,x+w*.36):
        g.box((xx,y,3.755),(.035,.035,.03),IRON)
    m=Geometry('Restaurant.CarvedSign',(x,y,3.74))
    for i in range(4):m.box((x,y,z-.20+i*.13),(w,.09,.125),PLANK)
    for xx in (x-w/2,x+w/2):
        # The side rails stop 1 cm under the gantry beam and stay 1 cm
        # thinner than it, so no face meets the beam's.
        m.box((xx,y,z),(.07,.08,.48),WOOD)
    for xx in (x-w*.36,x+w*.36):m.box((xx,y,3.705),(.03,.03,.07),IRON)
    sign_emblem(m,x,y-.055,z,'Restaurant',w*.50)
    parts.append((m,'SWAY',.012))


def kitchen_hearth(g):
    """Stone bake oven built into the kitchen's rear wall (one-layer storey).

    Native y = 7 is the footprint edge, so the oven face stays on the wall
    plane. Depths (source y, outward +y) are as before: wall infill 7.81, soot
    back 7.818, embers 7.824, grate 7.831..7.837, stone face 7.840, iron
    lintel and stone hood 7.849. 2026-10-30: the whole oven sits below the
    head fascia (z .72 of the one-layer kitchen), so its stone face never
    meets the fascia plane (7.836).
    """
    back=7.70;face=7.840;proud=7.849
    L,R=3.45,4.15;oL,oR=3.62,3.98
    def stone(x0,x1,z0,z1,i,front=face):
        g.box(((x0+x1)/2,(front+back)/2,(z0+z1)/2),(x1-x0-.008,front-back,z1-z0-.008),
              KILN_STONE_LIGHT if i%3==1 else KILN_STONE)
    stone(L,R,.20,.27,0)
    stone(L,oL,.27,.47,1);stone(oR,R,.27,.47,2)
    g.box(((oL+oR)/2,(proud+back)/2,.485),(.40,proud-back,.03),IRON)
    for i,(z0,z1,cuts) in enumerate(((.50,.58,(3.80,)),(.58,.65,(3.66,3.94)))):
        edges=[L,*cuts,R]
        for j,(a,b) in enumerate(zip(edges,edges[1:])):stone(a,b,z0,z1,i+j)
    stone(3.42,4.18,.65,.70,2,front=proud)
    g.add([(oL,7.818,.27),(oR,7.818,.27),(oR,7.818,.47),(oL,7.818,.47)],[(3,2,1,0)],KILN_SOOT)
    g.add([(oL+.02,7.824,.28),(oR-.02,7.824,.28),(oR-.02,7.824,.40),(oL+.02,7.824,.40)],[(3,2,1,0)],GLOW)
    for xx in (3.68,3.76,3.84,3.92):g.box((xx,7.834,.375),(.02,.006,.19),IRON)


def restaurant_parapet(g,runs,z=3):
    """Low cast parapet on the flat main roof's exposed edges (native spans).

    Its outer face is the tile line; it stands on the deck boards and stays
    within 0.12 of the edge, so the roof cells inside it stay buildable.
    """
    for side,a,b,line in runs:
        if side in ('front','back'):
            cx,cy,_=restaurant_source(((a+b)/2,line+(.06 if side=='front' else -.06),0));size=(b-a,.12)
        elif side=='left':
            cx,cy,_=restaurant_source((line+.06,(a+b)/2,0));size=(.12,b-a)
        else:raise ValueError('Restaurant parapet side '+side)
        g.box((cx,cy,z+.10),(*size,.20),CIVIC_CONCRETE)
        g.box((cx,cy,z+.215),(*size,.03),IRON)


def restaurant(g,parts):
    # 2026-10-30 compaction: one layer per storey and a flat roof (see
    # restaurant_structure.py). Footprint, ground door, dining balconies,
    # tables and chairs are unchanged in plan.
    r=RailAssembly('WalkwayRail.Restaurant')
    grid_room(g,'GroundHall',RESTAURANT_ROOMS['GroundHall'],RESTAURANT_ORIGIN,exterior=RESTAURANT_WALLS['GroundHall'],wall_style='storey')
    for name,door in (('MiddleHall','MiddleDoor'),('UpperHall','UpperDoor'),('EntranceVestibule','GroundDoor')):
        d=RESTAURANT_DOORS[door]
        grid_room(g,name,RESTAURANT_ROOMS[name],RESTAURANT_ORIGIN,(d['position'][0],d['width']),exterior=RESTAURANT_WALLS[name],wall_style='storey')
        restaurant_door(g,door)
    # This exposed one-cell corner is neither under the front gallery nor
    # inside the main hall. It needs its own roof; an open-topped vestibule
    # showed through from the left and rear even with all wall faces present.
    grid_platform(g,'EntranceVestibuleCap',RESTAURANT_PLATFORMS['EntranceVestibuleCap'],
                  RESTAURANT_ORIGIN,RESTAURANT_SUPPORTS['EntranceVestibuleCap'],ROOF,board_relief=.010)
    # Windows follow the rooms behind them, one row per one-layer storey,
    # inside the plaster band (z0+.20 .. z0+.72).
    from native_window_atlas import atlas_window, glass_curtain
    # Upper private dining: tall lancets toward the front balcony, framed
    # crosses on the sides, three-pane verticals over the kitchen side.
    for x in (2.3,3.3,5.3):
        glazing(g,x,2.89,2.46,.50,style='grand')
        atlas_window(g,x,5.81,2.46,.21,'back','triple')
    for x,face in ((1.84,'left'),(5.76,'right')):
        for y in (3.35,4.35,5.35):
            atlas_window(g,x,y,2.46,.40,face,'cross')
    # Flat main roof: the cast slab and timber decking of the roof terrace,
    # one level with it, a low parapet on its three street edges.
    grid_platform(g,'MainRoof',RESTAURANT_PLATFORMS['MainRoof'],RESTAURANT_ORIGIN,RESTAURANT_SUPPORTS['MainRoof'],PLANK,
                  slab_material=CIVIC_CONCRETE,fascia=RESTAURANT_FASCIA['MainRoof'],fascia_material=IRON,board_relief=.010)
    restaurant_parapet(g,[('front',1,5,2),('back',1,5,5),('left',2.12,4.88,1)])
    restaurant_roof_sign(g,parts)
    # Two storeys of dining balconies: every authored post stands on a cast
    # pier (ground) or bearing plate (deck) with knee braces into the beams it
    # carries, and exposed deck edges get a timber fascia on the tile line.
    # Rail posts stand on tile boundaries, so an opened section is one tile.
    for prefix in ('Dining','UpperDining'):
        for side,edges in (('Front',('front','left')),('SideFront',()),('Side',()),('Rear',())):
            name=prefix+side
            grid_gallery(g,r,name,RESTAURANT_PLATFORMS[name],RESTAURANT_ORIGIN,edges,RESTAURANT_SUPPORTS[name],
                         grid_rails=True,support_style='pier',fascia=RESTAURANT_FASCIA[name],board_relief=.010)
        z=1 if prefix=='Dining' else 2
        r.run_grid(prefix+'Sideright',(7.70,1.95),(7.70,7.75),z,RESTAURANT_ORIGIN)
        r.run_grid(prefix+'Rearback',(1.90,7.75),(7.70,7.75),z,RESTAURANT_ORIGIN)
        r.run_grid(prefix+'Rearleft',(1.90,5.95),(1.90,7.75),z,RESTAURANT_ORIGIN)
    for x in (1.95,5.20):terrace_table(g,x,1.55,2,chair_axis='X')
    r.run_grid('StairAccess',(6.80,1.95),(7.70,1.95),1,RESTAURANT_ORIGIN)
    # Main dining room: a wide warm picture window over the dining balcony,
    # timber-mullioned like the reference's dining windows; the narrow pier
    # right of the door keeps a grand window. The sides keep grand windows.
    glass_curtain(g,2.9,2.89,1.22,1.70,1.62,'front',cols=3,rows=1,mullion=.07,frame=WOOD)
    wall_windows(g,[5.28],2.89,1.46,.50)
    for y in (3.55,4.83):
        glazing(g,5.76,y,1.46,.50,'right')
        glazing(g,1.84,y,1.46,.50,'left')
    # The lower first bay is inside the projecting entrance vestibule. It has
    # no exterior wall and must not carry a hidden/floating window assembly.
    atlas_window(g,1.84,4.83,.48,.40,'left','single')
    # Kitchen-side service room: plain nine-pane grids, between the wall
    # posts (tile centres) so no reveal meets a post face.
    for x in (2.8,3.8,4.8):atlas_window(g,x,5.81,1.46,.40,'back','grid9')
    wall_windows(g,[4.28,5.28],2.89,.48,.50,style='factory')
    for x in (1.95,3.60,5.20):terrace_table(g,x,1.55,1,chair_axis='X')
    for y in (3.4,5.1):terrace_table(g,7.04,y,1)
    # Balcony planters stand on the deck inside the rails, in front of the
    # reserved table row, instead of hanging over neighbouring tiles.
    for z in (1,2):
        for x in (1.95,3.60,5.20):planter(g,x,1.13,z,.70,134+int(x*10)+z,depth=.24)
    for y in (2.35,3.85,5.85):planter(g,7.56,y,1,.74,146+int(y*10),True,species='CoffeeBushMature',depth=.24)
    # Lamps sit inside each storey, clear of the deck beams above (their
    # underside is 0.77 over each floor).
    wall_lamp(g,4.78,2.90,.44)
    for y in (2.85,4.85,6.85):
        timber_column(g,7.58,y,1,1.70,.10,collars=False,steel_channels=False)
        wall_lamp(g,7.58,y,1.48,'front')
    # Enclosed kitchen annex with a stone bake oven in its rear wall.
    grid_room(g,'Kitchen',RESTAURANT_ROOMS['Kitchen'],RESTAURANT_ORIGIN,exterior=RESTAURANT_WALLS['Kitchen'],wall_style='storey')
    kitchen_hearth(g)
    # The kitchen stack rises from the roof stairhead's cap (one solid core,
    # no-clutter rule): the main roof's cells stay buildable. It carries the
    # kitchen and hearth smoke while the kitchen works.
    x,y,_=restaurant_source((4.5,3.5,0))
    chimney(g,x,y,3.95,.90,emits='smoke')
    # Forged steel plates on two exposed kitchen infill panels. The rear
    # wall's orange face is recessed, so these real projecting plates have
    # thickness and do not share its depth plane.
    for x in (2.80,4.80):
        g.box((x,7.825,.46),(.65,.035,.44),CIVIC_FORGED_PANEL)
        for z in (.32,.42,.52,.62):g.box((x,7.85,z),(.43,.038,.035),IRON)
    # Steel straps bridge the rear gallery beam/post junctions. Their edges
    # stay below the floor and away from player paths and adaptive handrails.
    for z in (1,2):
        for x in (2.3,5.3,7.3):
            g.box((x,7.80,z-.23),(.40,.045,.18),IRON)
    roof_terrace(g,r,'Restaurant')
    return r


def produce_stall(g,x,y,kind,z=0):
    bin(g,(x,y,z),(.91,.67,.53),None)
    g.box((x,y,z+.52),(.80,.55,.035),CLOTH)
    rng=random.Random(170+kind)
    for i in range(20):
        xx=x-.34+(i%5)*.17;yy=y-.22+(i//5)*.14
        mat=[SAND,LEAF,LIME,PLANK][kind%4]
        size=(.15,.13,.14) if kind%4!=3 else (.11,.22,.08)
        g.rock((xx,yy,z+.61+rng.uniform(-.01,.03)),size,mat,kind*90+i)
        if kind%4==1:g.beam((xx,yy,z+.68),(xx+.025,yy,z+.74),.014,mat=WOOD)


def grocery_terrace_brackets(g):
    """Steel cantilevers join the roof terrace to actual upper-hall columns.

    Their lowest outside edge is above 5.0, preserving the one-beaver-high
    clearance over the level-4 gallery. No unsupported outer posts or new
    ground legs are introduced; the existing terrace footprint is unchanged.
    """
    for anchor_y,tip_y in ((3.03,3.37),(5.85,6.03)):
        root=(6.4,anchor_y,5.68);tip=(9.56,tip_y,5.68)
        g.beam(root,tip,.20,.24,IRON)
        g.beam((6.4,anchor_y,5.24),tip,.16,.18,IRON)
        # These wall plates wrap existing corner posts, clear of window bays.
        g.box((6.515,anchor_y,5.46),(.06,.22,.56),IRON)
        for z in (5.26,5.64):steel_bolt(g,(6.558,anchor_y,z),'X',.026)


def grocery(g,parts):
    r=RailAssembly('WalkwayRail.GroceryStore')
    framed_room(g,1.3,2.95,6.40,5.85,0,2,4,base_spans={
        'front':[(2.58,6.40)],'back':[(1.3,6.40)],'left':[(3.45,5.75)],'right':[(3.05,5.75)]})
    framed_room(g,1.8,3.03,6.40,5.85,2,4,3,(4.08,1.0,1.0))
    component_doorway(g,'GroceryStore','Door0')
    upper_hall(g,1.8,3.03,6.40,5.85,4.1,'GroceryStore','Door1')
    framed_room(g,.75,1.82,2.48,3.35,0,1.8,2,(1.6,1.0,1.0))
    roof_bearing(g,1.8,3.03,6.40,5.85,6.065,6.25)
    gabled_roof(g,1.52,2.77,6.65,6.07,6.25,7.50,200)
    # Long luminous clerestory is distinctive to the store, not a hotel dormer.
    # Corner posts carry this short clerestory; intermediate posts would pass
    # through its continuous row of three original narrow window assemblies.
    framed_room(g,3.15,3.20,5.18,5.75,7.18,7.98,1)
    for x in (3.48,4.17,4.85):glazing(g,x,3.14,7.61,.85,style='lancet')
    for y in (3.65,4.4,5.2):
        glazing(g,3.09,y,7.61,.85,'left','lancet')
        glazing(g,5.24,y,7.61,.85,'right','lancet')
    roof_bearing(g,3.15,3.20,5.18,5.75,7.98,8.06)
    gabled_roof(g,2.96,3.02,5.37,5.93,8.06,8.66,650)
    for x in (2.42,5.88):
        dormer(g,x,2.49,6.53,.83);dormer(g,x,4.85,6.53,.83)
    balcony(g,r,'ShopFront',.8,1.55,6.48,2.96,edges=('front','left'),support_corners=((-1,-1),(1,-1)))
    balcony(g,r,'ShopSide',6.48,2.05,7.55,7.0,edges=('front','right'),support_corners=((1,-1),(1,1)))
    balcony(g,r,'ShopRear',1.55,6.02,6.48,7.0,edges=('back',),support_corners=((-1,1),(1,1)))
    balcony(g,r,'UpperShopFront',.8,1.55,6.48,3.03,4,edges=('front','left'),support_corners=((-1,-1),(1,-1)))
    balcony(g,r,'UpperShopSide',6.48,2.05,7.55,7.0,4,edges=('front','right'),support_corners=((1,-1),(1,1)))
    balcony(g,r,'UpperShopRear',1.55,6.02,6.48,7.0,4,edges=('back',),support_corners=((-1,1),(1,1)))
    wall_windows(g,[2.55,5.63],2.97,3.12,1)
    for y in (3.7,5.0):
        glazing(g,6.46,y,3.13,1,'right')
        glazing(g,1.74,y,3.13,1,'left')
        glazing(g,1.24,y,.98,1,'left')
    wall_windows(g,[2.55,4.08,5.63],5.91,3.12,1,face='back')
    for x in (3.10,4.35,5.65):glazing(g,x,2.89,1.02,1.15,style='factory')
    component_doorway(g,'GroceryStore','Door2')
    awning(g,.56,1.00,2.66,2.88,1.37,1.78)
    # Broad striped awning covers richly stocked exterior displays.
    awning(g,2.70,.77,6.50,2.83,1.35,1.80,True)
    for i,x in enumerate((3.2,4.2,5.2,6.2)):produce_stall(g,x,1.05,i)
    for y,kind in ((3.6,1),(4.65,0),(5.7,2)):produce_stall(g,7.0,y,kind)
    for x in (2.5,4.1,5.65):planter(g,x,1.36,2.30,.95,220+int(x*10),mount='front')
    for y in (3.65,5.0,6.40):planter(g,7.75,y,2.30,.70,250+int(y*10),True,species='BlueberryBushMature',mount='right')
    for x in (2.7,4.2,5.9):
        wall_lamp(g,x,3.03,3.72);wall_lamp(g,x,2.95,1.5)
    hanging_board(g,parts,'GroceryStore',.60,1.72,2.70,1.03)
    # A high service canopy supports the tank above the rear gallery; its posts
    # flank the walking lane and the whole assembly clears the roof build area.
    g.box((6.1,6.55,6.51),(1.20,.96,.18),CIVIC_CONCRETE)
    # Wall-side supports carry the short tank canopy. The terrace's existing
    # frame carries its other edge; no duplicate post in the public aisle.
    for y in (6.20,6.98):timber_column(g,5.48,y,4,6.42,.10)
    # Retired gallery store; the Grocery Market records its own chimney steam.
    roof_services(g,6.1,6.55,6.60);chimney(g,5.92,5.18,6.8,1.52,emits=None)
    supply_pile(g,2.4,7.35,0);supply_pile(g,4.1,7.35,0)
    for x in (.60,1.20):barrel(g,(x,6.5,0),2.4)
    for x in (5.3,5.8):
        for i in range(3):g.rock((x,7.22,.14+i*.22),(.48,.45,.24),CLOTH,300+i)
    for i in range(5):
        x=6.85;yy=5.30+i*.15
        g.cylinder((x,yy,.98),.055,.18,GLASS,'Z',12);g.cylinder((x,yy,1.08),.058,.035,BRASS,'Z',12)
    roof_terrace(g,r,'GroceryStore');civic_service_details(g,1.80,3.03,6.40,5.85)
    return r


def fishing_net(g,x,y,z,width=.85,height=.90):
    for direction in (-1,1):
        for k in range(-6,7):
            # Each strand runs between the net's side edges (u = k/10 +
            # direction*t in 0..1) in up to six segments (was 20 steps): the
            # sag still reads at a third of the strand triangles. The density
            # stays: the nets cover registered rear-wall connection faces
            # (measure_connection_faces.py), which a sparser net would open.
            lo,hi=(max(0,-k/10),min(1,1-k/10)) if direction>0 else (max(0,k/10-1),min(1,k/10))
            if hi-lo<1e-9:continue
            steps=max(1,round(6*(hi-lo)))
            a=[]
            for j in range(steps+1):
                t=lo+(hi-lo)*j/steps;xx=x-width/2+(k/10+direction*t)*width
                a.append((xx,y+.06*math.sin(t*math.pi),z-height*t))
            for p,q in zip(a,a[1:]):g.beam(p,q,.010,mat=CLOTH)
    g.beam((x-width/2,y,z),(x+width/2,y,z),.04,mat=WOOD)


def basin(g,x0,y0,x1,y1,z=.0):
    lean_bin(g,((x0+x1)/2,(y0+y1)/2,z),(x1-x0,y1-y0,.53))
    g.liquid_surfaces.append(dict(name='FisheryBasin'+str(len(g.liquid_surfaces)),shape='Rectangle',
        center=[(x0+x1)/2,(y0+y1)/2],bottom=z+.10,top=z+.44,
        scale=[x1-x0-.13,y1-y0-.13],flowOnly=False))
    for x in (x0+.07,x1-.07):
        for y in (y0+.07,y1-.07):timber_column(g,x,y,z+.10,z+.72,.16)


def fishery(g,parts):
    # The user's Fishery.png isometric building is a waterfront processing
    # works: dominant long roof, offset floors, nets and a visible wheel.
    # It must not reuse the three-storey civic hall and duplicate balcony ring.
    # 2026-10-30 compaction: one layer per storey (processing floor 0-1,
    # upper hall and working galleries at 1). The long gabled roof stays as
    # the works' defining silhouette, lower; the lean-to awnings under the
    # galleries, the wall service ducts and the roof cowl are gone.
    r=RailAssembly('WalkwayRail.FisheryWorks')
    framed_room(g,1.65,3.05,6.50,7.15,0,.95,4,base_spans={
        'front':[(3.10,6.50)],'back':[(1.65,6.50)],'left':[(3.65,7.05)],'right':[(3.15,7.05)]},wall_style='storey')
    framed_room(g,2.05,3.28,6.05,7.15,1,2.02,3,(3.90,1.0,1.0),infill=CIVIC_FORGED_PANEL,base_spans={
        'front':[(2.05,6.05)],'back':[(2.05,6.05)],'left':[(3.38,4.81),(6.29,7.05)],'right':[(3.38,7.05)]},wall_style='storey')
    component_doorway_storey(g,'FisheryWorks','Door0')
    framed_room(g,1.30,1.72,3.0,3.55,0,.85,2,(2.0,1.0,1.0),wall_style='storey')
    component_doorway_storey(g,'FisheryWorks','Door1')
    # Longer main roof and an offset lower entrance gable.
    roof_bearing(g,2.05,3.28,6.05,7.15,2.02,2.12)
    gabled_roof(g,1.78,3.03,6.32,7.43,2.12,3.12,310)
    roof_bearing(g,1.30,1.72,3.0,3.55,.85,.98)
    gabled_roof(g,1.12,1.50,3.21,3.65,.98,1.43,311)
    glazing(g,4.05,2.985,2.55,.60,style='diamond')
    balcony_storey(g,r,'FishLeft',.40,3.55,1.95,8.40,edges=('front',),support_corners=((-1,-1),(-1,1)))
    # The warehouse roof and left gallery are one continuous working deck.
    # Rail only their outside boundary; never fence across their shared floor.
    r.run('FishLeftSouth',(.40,3.55),(.40,4.00),1)
    r.run('FishLeftNorth',(.40,7.10),(.40,8.40),1)
    balcony_storey(g,r,'FishRight',6.15,2.05,7.85,8.40,edges=('front','right'),support_corners=((1,-1),))
    balcony_storey(g,r,'FishRear',1.95,7.20,6.15,8.40,edges=(),support_corners=((-1,1),(1,1)))
    r.run('FishBack',(.40,8.40),(7.85,8.40),1)
    balcony_storey(g,r,'FishFront',3.15,2.05,6.15,3.28,1,edges=('front',),support_corners=((-1,-1),(1,-1)))
    for x in (2.62,5.32):glazing(g,x,3.22,1.48,.50,style='factory')
    for y in (3.85,5.15,6.46):
        glazing(g,6.11,y,1.48,.50,'right','factory')
        glazing(g,1.59,y,.48,.50,'left','factory')
    for x in (2.7,4.05,5.4):glazing(g,x,7.21,1.48,.50,'back','lancet')
    # 2026-10-22 (user): no forced decoration beyond the walls. The outdoor
    # fish tables, fish bins and drying hooks in front are gone; the wall
    # keeps its washdown splashbacks and drains.
    for x in (3.80,5.35):
        g.box((x,2.91,.47),(1.22,.06,.40),CIVIC_FORGED_PANEL)
        round_pipe(g,[(x-.44,2.70,.34),(x-.44,2.70,.58),(x-.25,2.70,.58)],.027)
    hanging_board_storey(g,parts,'FisheryWorks',.76,1.42,.85,1.13)
    for x in (1.75,3.1,4.5,6.3):wall_lamp(g,x,3.0,.46)
    # The left lamp went: the entrance roof's ridge stands in front of it.
    wall_lamp(g,5.94,3.23,1.48)
    for y in (3.3,5.1,7.5):deck_lamp(g,7.76,y,floor=1)
    for x in (2.65,4.18,5.55):fishing_net(g,x,7.27,1.90,1.0,.78)
    # The net drying frames on the warehouse roof terrace are gone too: the
    # terrace is the player's (2026-10-22).
    # Water wheel, header and low basins form one visibly connected water route.
    prop(g,'FisheryNativeWheel','CompactWaterWheel.IronTeeth',(8.15,6.50,.03),1,90)
    basin(g,8.10,3.25,9.55,6.58);basin(g,8.10,1.30,9.55,3.10)
    # The header basin sits just above the native wheel (1.69 tall).
    basin(g,8.28,5.15,9.02,6.60,1.72)
    flow=Geometry('FisheryCascade')
    flow.add([(8.40,5.15,2.16),(8.90,5.15,2.16),(8.38,4.72,1.90),(8.92,4.72,1.90),
              (8.36,3.75,.64),(8.94,3.75,.64)],[(0,1,3,2),(2,3,5,4)],WATER)
    parts.append((flow,'STATIC',0))
    round_pipe(g,[(8.65,6.35,2.16),(8.65,6.70,2.16),(8.65,6.70,.55),(6.55,6.70,.55)],.10)
    # Small crane on the rear gallery carries a modeled rope net, not a beaver.
    timber_column(g,7.65,8.15,0,2.90,.24)
    beam_joint(g,(7.65,8.15,2.85),(9.15,8.15,2.85),.20,.23)
    g.beam((7.65,8.15,1.95),(8.64,8.15,2.85),.13,mat=WOOD)
    g.cylinder((7.65,8.15,1.35),.24,.44,IRON,'Y',20)
    g.ring((7.65,7.90,1.35),.28,.045,.06,BRASS,'Y',20)
    load=Geometry('FisheryWorks.CraneNet',(9.10,8.15,2.77))
    load.beam((9.10,8.15,2.77),(9.10,8.15,1.41),.02,mat=CLOTH)
    for i in range(8):
        a=i*math.pi/4
        load.beam((9.10,8.15,1.48),(9.10+math.cos(a)*.27,8.15+math.sin(a)*.27,1.07),.016,mat=CLOTH)
        load.beam((9.10+math.cos(a)*.27,8.15+math.sin(a)*.27,1.07),(9.10,8.15,.92),.016,mat=CLOTH)
    for z,rr in ((1.00,.16),(1.10,.26),(1.21,.20)):load.ring((9.10,8.15,z),rr,.010,.015,CLOTH,'Z',16)
    for i in range(6):load.rock((8.96+(i%3)*.13,8.09+(i//3)*.13,1.12),(.16,.16,.13),SAND,500+i)
    parts.append((load,'SWAY',.025))
    # Fish-oil rendering vents steam, not combustion smoke (no smog). The
    # stack's foot sinks into the main roof (2.38 at x 5.72).
    chimney(g,5.72,6.65,2.25,1.05,emits='steam')
    # The two rear water tanks are the Timber Pipes inlet (aquaculture pipe
    # port), so they stay; the loose barrels and the supply pile are gone.
    # 2026-10-30 (no-clutter rule): they stand under the rear gallery now,
    # not on their own row behind it.
    for i,x in enumerate((2.3,3.0)):water_barrel(g,'FisheryWaterBarrel'+str(i),(x,7.80,0),.62)
    # A single-storey offset warehouse carries the working roof at layer 1.
    # The open middle remains available for player platforms and decorations.
    t=CIVIC_TERRACES['FisheryWorks'];x0,y0,x1,y1=t['bounds']
    framed_room(g,x0+.12,y0+.12,x1-.12,y1-.12,0,.90,3,wall_style='storey')
    g.box(((x0+.40)/2,(y0+y1)/2,.85),(.40-x0-.06,y1-y0-.06,.02),IRON)
    deck(g,x0,y0,.40,y1,.93)
    for side,a,b in [('Front',(x0,y0),(.40,y0)),('Rear',(x0,y1),(.40,y1)),('Left',(x0,y0),(x0,y1))]:r.run('RoofTerrace'+side,a,b,1)
    terrace_access_house(g,t,left_facing=True,model='FisheryWorks',storey=True)
    for x in (x0+.55,x0+1.55):
        glazing(g,x,y0+.06,.48,.50)
    return r
