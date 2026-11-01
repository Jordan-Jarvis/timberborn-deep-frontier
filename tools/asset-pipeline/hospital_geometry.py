"""Hospital pavilion, authored from isometric references only.

The hospital has a transverse central roof over its tall entrance pavilion.
There are no interior floors, furniture or rooms visible behind the windows.

2026-10-30 (user): "keep it as it is, but remove the right and left wings,
just keeping the center." The pavilion's artwork is unchanged; the ward
wings, ward roofs and flues, front ward balconies and the rear balcony ends
are removed. Source coordinates are unchanged (hospital_structure.ORIGIN).

2026-11-01 (second shrink pass): 4x4x4. Two one-layer storeys (`storey`
walls, half-scale windows), a front-facing gabled roof over the front half
with the medical cross in its gable, the concrete roof garden at layer 2 over
the back half and a one-layer stairhead on the back-right corner.
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
    # One-layer storeys (2026-11-01): the storey infill and door lamps under
    # the room's head fascia, as civic component_doorway_storey.
    style='storey' if z1-z0==1 else 'banded'
    lamp_z=.36 if z1-z0==1 else 1.20
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
                  joined_ends=joins,joined_post_inset=.008 if joins else 0.0,wall_style=style)
        # Portals are independent assets; keep their neighboring lamps in the
        # existing ward decoration so a door edit does not regenerate it.
        for dx in (-.62,.62):wall_lamp(part,cx+dx,.17,lamp_z)
        if name=='RoofStairhead':glazing(part,.5,.04,1.43,.72,style='diamond')
        # Native bounds -> source artwork coordinates (source = native - ORIGIN).
        sx1,sy1,sz0=source((x1,y1,z0))
        append_transformed(g,part,lambda p:(sx1-p[0],sy1-p[1],sz0+p[2]))
        g.structural_parts.append({'id':name,'kind':'room','bounds':b,
            'pickingBoxes':[{'center':[(x0+x1)/2,(y0+y1)/2,(z0+z1)/2],'size':[w,depth,height]}]})
    else:
        joins={}
        grid_room(part,name,b,ORIGIN,(d['position'][0],1) if d else None,exterior=EXTERIOR_WALLS[name],joined_ends=joins,
                  joined_post_inset=.008,wall_style=style)
        if d and x1-x0>1:
            # A one-tile stairhead (2026-11-01) has no wall beside its door
            # for the lamps.
            x,y,z=source(d['position'])
            for dx in (-.62,.62):wall_lamp(part,x+dx,y+.17,z+lamp_z)
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


def medical_banner_storey(g,parts,x,y,z):
    """medical_banner for a one-layer storey (2026-11-01): the same insignia
    at .55 scale under the storey's head fascia; same node name."""
    s=.55
    m=Geometry('Hospital.WardBanner'+str(x),(x,y,z+.72*s))
    m.box((x,y,z),(.40*s,.045,1.20*s),ROOF)
    m.add([(x-.20*s,y,z-.60*s),(x+.20*s,y,z-.60*s),(x,y,z-.78*s)],[(0,1,2)],ROOF)
    m.beam((x,y-.03,z-.35*s),(x,y-.03,z+.43*s),.028*s,mat=LIME)
    for i in range(8):
        a=i*math.pi/2;b=(i+1)*math.pi/2
        m.beam((x+math.sin(a)*.08*s,y-.035,z+(-.32+i*.08)*s),
               (x+math.sin(b)*.08*s,y-.035,z+(-.32+(i+1)*.08)*s),.021*s,mat=LIME)
    parts.append((m,'SWAY',.009))
    g.beam((x-.29*s,y,z+.73*s),(x+.29*s,y,z+.73*s),.065*s,mat=BRASS)
    g.beam((x,y+.033,z+.73*s),(x,y+.35,z+.73*s),.065*s,mat=IRON)


def hospital(g,parts):
    """4x4x4 (2026-11-01). Source coordinates: native + (5,2,0)."""
    from civic_isometric_geometry import (
        gabled_roof,roof_bearing,glazing,wall_lamp,framed_cross,CIVIC_TERRACES)
    r=RailAssembly('WalkwayRail.Hospital')
    entrances={'CentralLower':'GroundDoor','RoofStairhead':'RoofTerraceDoor'}
    for name in ROOMS:hospital_room(g,name,entrances.get(name))

    # Front-facing gable over the front half (native y 0..2): the ridge runs
    # front to back at native x 2, eaves overhang the side walls by .16 and
    # the gable stands .04 ahead of the front wall. Its back end meets the
    # roof garden at native y 2, as the transverse roof met it before.
    roof_bearing(g,5,2,9,4,2,2.15)
    gabled_roof(g,4.84,1.96,9.16,4.00,2.15,3.70,732)
    # The medical cross identifies the entrance from a distance, in the gable.
    framed_cross(g,7.0,1.86,2.76)
    # Ground storey (layer 0): door at source x 7.5 (7.0..8.0), lamps at
    # 6.88 and 8.12; half-scale windows as on the other one-layer storeys.
    for x in (5.75,6.40,8.60):glazing(g,x,2.04,.48,.50,style='factory')
    # Upper ward storey (layer 1).
    for x in (5.70,6.35,7.65,8.30):glazing(g,x,2.04,1.46,.50,style='lancet')
    glazing(g,7.0,2.04,1.46,.50,style='grand')
    for x in (5.18,8.82):medical_banner_storey(g,parts,x,1.75,1.45)
    # Rear care wing rhythm, and the side lancets on both storeys.
    for x in (5.8,7.0,8.2):
        glazing(g,x,5.96,.48,.50,'back','factory')
        glazing(g,x,5.96,1.46,.50,'back','lancet')
    for x,face in ((5.04,'left'),(8.96,'right')):
        for y in (3.0,4.0,5.0):
            for z in (.48,1.46):glazing(g,x,y,z,.50,face,'lancet')

    for name,b in PLATFORMS.items():
        # 10 mm board relief: 4 mm sat on the strict 0.004 overlap tolerance.
        grid_platform(g,name,b,ORIGIN,SUPPORTS[name],CIVIC_CONCRETE if name=='RoofGarden' else PLANK,board_relief=.010)
    # No deck rails (2026-10-31 roof pass): the roof garden is open to its
    # tile edges. The stairhead closes with a small gabled cap.
    roof_bearing(g,8,5,9,6,3,3.05)
    gabled_roof(g,7.96,5.04,9.04,5.96,3.05,3.45,748)
    CIVIC_TERRACES['Hospital']['accessDoor']=g.doorways[-1]
    # A vanilla-sized entrance canopy, 0.25 deep, over the one-layer door.
    entrance_canopy(g,6.20,1.75,8.80,2.0,.90,.98)
    return r
