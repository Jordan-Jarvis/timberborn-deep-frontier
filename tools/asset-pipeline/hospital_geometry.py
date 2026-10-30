"""Hospital pavilion, authored from isometric references only.

The hospital has a transverse central roof over its tall entrance pavilion.
There are no interior floors, furniture or rooms visible behind the windows.

2026-10-30 (user): "keep it as it is, but remove the right and left wings,
just keeping the center." The pavilion's artwork is unchanged; the ward
wings, ward roofs and flues, front ward balconies and the rear balcony ends
are removed. Source coordinates are unchanged (hospital_structure.ORIGIN).
"""
import math
import random
from frontier_architecture import Geometry,WOOD,PLANK,IRON,ROOF,LIME,BRASS
from reference_materials import CIVIC_CONCRETE,CIVIC_ORANGE_PANEL,CIVIC_FORGED_PANEL
from grid_structure import room as grid_room,platform as grid_platform
from hospital_structure import ORIGIN,ROOMS,EXTERIOR_WALLS,PLATFORMS,SUPPORTS,DOORS,source
from walkway_geometry import RailAssembly
from industrial_budget import round_pipe
from native_building_assets import barrel


def append_transformed(g,part,transform):
    first_face=len(g.faces)
    points=[transform((-v[0],-v[1],v[2])) for v in part.vertices]
    for face,material,uv,source in zip(part.faces,part.materials,part.face_uvs,part.face_sources,strict=True):
        g.add([points[i] for i in face],[tuple(range(len(face)))],material)
        g.face_uvs[-1]=uv;g.face_sources[-1]=source
    for mount in part.window_mounts:
        anchor=transform(mount['anchor'])
        tip=transform([a+b for a,b in zip(mount['anchor'],mount['outward'],strict=True)])
        outward=[a-b for a,b in zip(tip,anchor,strict=True)]
        face={(0,-1,0):'front',(0,1,0):'back',(-1,0,0):'left',(1,0,0):'right'}[tuple(outward)]
        g.window_mounts.append({**mount,'anchor':list(anchor),'outward':outward,'face':face,
            'faceRange':[first_face+i for i in mount['faceRange']],
            'rearEdges':[[list(transform(point)) for point in edge] for edge in mount['rearEdges']]})


def gable_window_seat(g,x,y,z,scale,face):
    """Solid timber seat bridges the deliberate joints in gable planks.

    Its front is six millimeters ahead of the plank skin. Its back penetrates
    the continuous gable sheathing; the native pane outline defines the seat.
    This is authored joinery, not a movement or rescaling of the native window.
    """
    from architectural_windows import KIT,PANES
    assembly=KIT['windowAssemblies']['diamond'];pane=KIT['parts'][PANES['diamond']]
    origin=assembly['origin'];tangent=assembly['tangent']
    nx,ny={'front':(0,-1),'back':(0,1)}[face];tx,ty=-ny,nx
    def point(p,depth):
        delta=[p[i]-origin[i] for i in range(3)]
        u=sum(a*b for a,b in zip(delta,tangent,strict=True))*scale
        return (x+tx*u+nx*depth,y+ty*u+ny*depth,z+delta[1]*scale)
    front=[point(p,0) for p in pane['vertices']]
    g.add(front,pane['faces'],WOOD)
    edges={}
    for polygon in pane['faces']:
        for ia,ib in zip(polygon,polygon[1:]+polygon[:1]):
            a=tuple(pane['vertices'][ia]);b=tuple(pane['vertices'][ib])
            edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
    for uses in edges.values():
        if len(uses)==2:continue
        if len(uses)!=1:raise ValueError('Hospital gable seat needs a manifold native pane')
        a,b=uses[0]
        g.add([point(a,0),point(b,0),point(b,-.13),point(a,-.13)],[(0,1,2,3)],WOOD)


def hospital_room(g,name,door_id=None):
    """Closed grid shell, with deliberate pale ward infill and native portals."""
    from civic_isometric_geometry import wall_lamp,glazing
    from building_components import recipe
    b=ROOMS[name];x0,y0,z0,x1,y1,z1=b
    d=DOORS[door_id] if door_id else None
    rear=d is not None and d['outward']==[0,1]
    part=Geometry('Hospital '+name)
    if rear:
        # Half-turn the complete authored shell, doorway and original native
        # UVs. No post-export coordinate repair or orientation guessing.
        w=x1-x0;depth=y1-y0;height=z1-z0
        exterior=EXTERIOR_WALLS[name]
        converted={
            'front':[(x1-hi,x1-lo) for lo,hi in exterior['back']],
            'back':[(x1-hi,x1-lo) for lo,hi in exterior['front']],
            'left':[(y1-hi,y1-lo) for lo,hi in exterior['right']],
            'right':[(y1-hi,y1-lo) for lo,hi in exterior['left']],
        }
        cx=x1-d['position'][0]
        # No joined ends since the wards were removed (2026-10-30).
        joins={}
        grid_room(part,name,[0,0,0,w,depth,height],[0,0,0],(cx,1),exterior=converted,
                  joined_ends=joins,joined_post_inset=.008 if joins else 0.0)
        # Portals are independent assets; keep their neighboring lamps in the
        # existing ward decoration so a door edit does not regenerate it.
        for dx in (-.62,.62):wall_lamp(part,cx+dx,.17,1.20)
        if name=='RoofStairhead':glazing(part,.5,.04,1.43,.72,style='diamond')
        # Native bounds -> source artwork coordinates (source = native - ORIGIN).
        sx1,sy1,sz0=source((x1,y1,z0))
        append_transformed(g,part,lambda p:(sx1-p[0],sy1-p[1],sz0+p[2]))
        g.structural_parts.append({'id':name,'kind':'room','bounds':b,
            'pickingBoxes':[{'center':[(x0+x1)/2,(y0+y1)/2,(z0+z1)/2],'size':[w,depth,height]}]})
    else:
        joins={}
        grid_room(part,name,b,ORIGIN,(d['position'][0],1) if d else None,exterior=EXTERIOR_WALLS[name],joined_ends=joins,
                  joined_post_inset=.008)
        if d:
            x,y,z=source(d['position'])
            for dx in (-.62,.62):wall_lamp(part,x+dx,y+.17,z+1.20)
        append_transformed(g,part,lambda p:p)
        g.structural_parts.extend(part.structural_parts)
    if d:
        g.include_component(recipe('Hospital','Door.'+door_id))
        g.doorways.append({'id':door_id,'position':list(source(d['position'])),'outward':d['outward'],
                          'width':1.0,'internalConnection':'BuildingInterior'})


def transverse_roof(g,x0,y0,x1,y1,eave,ridge,seed):
    from civic_isometric_geometry import gabled_roof
    part=Geometry('Hospital transverse pavilion roof')
    gabled_roof(part,0,0,y1-y0,x1-x0,eave,ridge,seed)
    append_transformed(g,part,lambda p:(x0+p[1],y1-p[0],p[2]))


def entrance_canopy(g,x0,y0,x1,y1,z0,z1):
    """The entrance's sheet canopy (industrial sheet_roof form) with its
    corner shoes but without folded corner brackets; their plates sat 4 mm
    from the shoes, inside the strict overlap tolerance. No fastener heads
    (civic shell family, triangle budget 2026-10-29)."""
    rng=random.Random(41);count=math.ceil((x1-x0)/.28)
    for i in range(count):
        x=x0+(i+.5)*(x1-x0)/count
        g.beam((x,y0,z0),(x,y1,z1),(x1-x0)/count,.045,ROOF)
    for x in (x0,x1):g.beam((x,y0,z0-.035),(x,y1,z1-.035),.13,.14,WOOD)
    for y,z in ((y0,z0),(y1,z1)):
        # Cross beams end inside the side beams, not on the outer sheet plane.
        g.beam((x0+.03,y,z-.055),(x1-.03,y,z-.055),.15,.16,WOOD)
        for x in (x0,x1):
            g.box((x,y,z+.050),(.22,.22,.025),IRON)
    for t in (.35,.72):
        y=y0+(y1-y0)*t;z=z0+(z1-z0)*t+.03
        g.beam((x0,y,z),(x1,y,z),.06,.018,IRON)
    # Triangle budget: no 6x4 mm scratch slivers (sub-pixel at game zoom).
    del rng


def medical_banner(g,parts,x,y,z):
    """Hanging ward insignia, deliberately below the ward's roofline."""
    m=Geometry('Hospital.WardBanner'+str(x),(x,y,z+.72))
    m.box((x,y,z),(.40,.045,1.20),ROOF)
    m.add([(x-.20,y,z-.60),(x+.20,y,z-.60),(x,y,z-.78)],[(0,1,2)],ROOF)
    m.beam((x,y-.03,z-.35),(x,y-.03,z+.43),.028,mat=LIME)
    for i in range(8):
        a=i*math.pi/2;b=(i+1)*math.pi/2
        m.beam((x+math.sin(a)*.08,y-.035,z-.32+i*.08),
               (x+math.sin(b)*.08,y-.035,z-.32+(i+1)*.08),.021,mat=LIME)
    parts.append((m,'SWAY',.009))
    g.beam((x-.29,y,z+.73),(x+.29,y,z+.73),.065,mat=BRASS)
    g.beam((x,y+.033,z+.73),(x,y+.56,z+.73),.065,mat=IRON)


# Each boundary is authored once, avoiding corner post piles and automatic
# per-module joins across the open hospital balconies. Runs stay 0.10 inside
# the deck edge; intermediate posts stand on tile boundaries (2026-10-21), so
# opening one cell's section leaves exactly that tile open. Source artwork
# coordinates (native + 1 in X). Front and back balconies only: short end
# rails close each balcony at the building corners.
# 2026-10-30: the rear balconies end at the pavilion's corners (source x 5
# and 9) since the wings were removed; the front ward balconies are gone.
HOSPITAL_RAIL_RUNS=[
    ('RearOuter',(5.10,10.90),(8.90,10.90),2),
    ('RearLeft',(5.10,10.10),(5.10,10.90),2),
    ('RearRight',(8.90,10.10),(8.90,10.90),2),
    ('UpperRearOuter',(5.10,10.90),(8.90,10.90),4),
    ('UpperRearLeft',(5.10,10.10),(5.10,10.90),4),
    ('UpperRearRight',(8.90,10.10),(8.90,10.90),4),
    ('RoofGardenLeft',(5.10,7.10),(5.10,9.90),6),
    ('RoofGardenRight',(8.90,7.10),(8.90,9.90),6),
    ('RoofGardenRear',(5.10,9.90),(8.90,9.90),6),
]


def hospital_rails(r):
    """Author every hospital rail run; also used by the selective rail rebuild."""
    for name,a,b,z in HOSPITAL_RAIL_RUNS:r.run_grid(name,a,b,z,ORIGIN)
    return r


def hospital(g,parts):
    from civic_isometric_geometry import (
        gabled_roof,roof_bearing,glazing,planter,wall_lamp,framed_cross,
        chimney,supply_pile,awning,CIVIC_TERRACES)
    r=RailAssembly('WalkwayRail.Hospital')
    entrances={'CentralLower':'GroundDoor','CentralMiddle':'RearDeckDoor','CentralUpper':'RearWardDoor','RoofStairhead':'RoofTerraceDoor'}
    for name in ROOMS:hospital_room(g,name,entrances.get(name))

    roof_bearing(g,5,2,9,6,6,6.15)
    transverse_roof(g,4.84,1.84,9.16,6.00,6.15,7.70,732)
    # The main cross and paired lancets identify the medical entrance from
    # a distance. These are original native window meshes and exact UVs.
    framed_cross(g,7.0,1.89,3.23)
    for x in (5.65,6.50,8.50):glazing(g,x,2.04,1.10,1.35,style='lancet')
    for x in (5.85,8.15):glazing(g,x,2.04,3.10,1.45,style='lancet')
    # Banners hang 0.25 off the facade (was 0.54), inside the overhang allowance.
    for x in (5.18,8.82):medical_banner(g,parts,x,1.75,3.16)
    for x in (6.0,8.0):glazing(g,x,2.04,5.10,1.50,style='grand')
    glazing(g,7.0,2.04,5.10,1.30,style='lancet')
    # Rear care wing: a different window rhythm around the upper access door.
    for x in (5.8,7.0,8.2):
        glazing(g,x,9.96,1.08,1.40,'back','factory')
        if x!=7.0:glazing(g,x,9.96,5.10,1.30,'back','lancet')
    # Layer 2 has the back-balcony door at source x 7.5 (7.0..8.0) with its
    # lamps at 6.88 and 8.12; the windows stand clear of both.
    glazing(g,5.95,9.96,3.08,1.40,'back','factory')
    glazing(g,8.50,9.96,3.08,1.20,'back','lancet')
    for x,face in ((5.04,'left'),(8.96,'right')):
        for y in (2.50,6.75,8.05,9.25):glazing(g,x,y,5.05,1.30,face,'lancet')
        # The lower two storeys' side walls faced the wards until 2026-10-30;
        # they carry the upper storey's lancet rhythm now.
        for z in (1.10,3.10):
            for y in (2.50,6.75,8.05,9.25):glazing(g,x,y,z,1.30,face,'lancet')

    for name,b in PLATFORMS.items():
        # 10 mm board relief: 4 mm sat on the strict 0.004 overlap tolerance.
        grid_platform(g,name,b,ORIGIN,SUPPORTS[name],CIVIC_CONCRETE if name=='RoofGarden' else PLANK,board_relief=.010)
    hospital_rails(r)
    # Access house closes the central rear roof, with a small metal cap and
    # a proper opaque attic accent above its one-tile native arch.
    roof_bearing(g,7,6,8,7,8,8.05)
    gabled_roof(g,6.96,6.04,8.04,6.96,8.05,8.45,748)
    CIVIC_TERRACES['Hospital']['accessDoor']=g.doorways[-1]
    # The ward steriliser flues went with the wings (2026-10-30). One steam
    # flue keeps the hospital's steam: it rises through the transverse roof's
    # rear slope near the left gable (roof 6.35..6.70 under it), so no roof
    # garden cell is given up (no-clutter rule). Steam does not pollute.
    chimney(g,5.50,5.50,6.25,1.42,emits='steam')

    # 2026-10-22 (user): no forced decoration beyond the walls. The facade
    # planters, the rear supply pile and barrel are gone, and the footprint
    # ends at the pavilion front wall (source y 2). The entrance canopy is a
    # vanilla-sized overhang: 0.25 deep, no ground tile, still over the door.
    entrance_canopy(g,6.20,1.75,8.80,2.0,1.66,1.82)
    for x in (5.45,8.55):wall_lamp(g,x,10.0,1.35,'back')
    # External clean-water line and steel ventilation equipment reinforce the
    # hospital's function and distinguish it from public dining architecture.
    for x in (5.2,8.8):
        round_pipe(g,[(x,10.12,.40),(x,10.12,1.55),(x,10.12,3.75)],.055)
        for z in (.6,1.5,2.7,3.5):g.box((x,10.12,z),(.15,.14,.06),IRON)
    return r
