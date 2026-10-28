"""Quarry visual material handling and enclosed industrial rooms.

Internal belts and ore are original animated artwork, not Conveyor Belt entities.
Authored directions and openings join the bucket, receiver, screen and stock bin.
"""
import math
import random
from mathutils import Vector,Quaternion
from frontier_architecture import Geometry,WOOD,PLANK,IRON,ROOF,SAND,BRASS,deck,wall,facade_panel
from industrial_geometry import steel_bolt,timber_column
from reference_details import round_pipe,cage_lamp
from industrial_kit import open_beam, wheel, gauge
from industrial_kit import steel_bolt,timber_column,round_pipe,cage_lamp,band,prism,bolt,square_nut,open_box,rock
from reference_materials import GLASS,GLOW,KILN_SOOT,KILN_RUST,CRUSHER_STEEL
from industrial_facades import extra_materials,side_window,window_y,gauge,CYAN,RUBBER
from industrial_door_components import recipe as door_recipe
from industrial_levels import QUARRY_ENTRANCE

BELT_A=Vector((7.9,4.82,2.35))
BELT_B=Vector((7.9,3.75,2.02))
BELT_R=.105
PROCESS={
    'scope':'Visual process choreography; no item creation or dependency belt entities',
    'route':['lift bucket','side tipping receiver','enclosed gravity chute',
             'short powered slat conveyor','vibrating screen','discharge chute','stone bin'],
    'receiver':[6.15,4.18,5.65],
    'beltStart':list(BELT_A),'beltEnd':list(BELT_B),
    'collectionBin':[8.0,1.91,1.0],
    'cycleSeconds':16,'maximumBucketTipDegrees':40,
    'enclosedSections':['left repair workshop','right engine room','rear control room'],
    'interiors':'Closed opaque facades; no visible interiors or character props',
    'doorwayIdleAnchors':[
        {'section':'repair workshop','position':[.685,4.175,1.0],'facing':[0,-1,0]},
        {'section':'engine room','position':[8.915,4.975,1.0],'facing':[0,-1,0]},
        {'section':'rear control room','position':[3.37,7.34,1.0],'facing':[-1,0,0]},
        {'section':'front operator cabin','position':[1.50,1.06,QUARRY_ENTRANCE],'facing':[0,-1,0]}],
    'doorwayStatus':'Artwork anchors only; native transform slots and navigation not exported',
    'artDirection':'Worn timber and teal metal with restrained cyan instrumentation, flanged pipes and cable runs'
}




def lift_state(t):
    def smooth(v):return .5-.5*math.cos(math.pi*v)
    if t<.36:lift=3.6*smooth(t/.36)
    elif t<.56:lift=3.6
    elif t<.91:lift=3.6*(1-smooth((t-.56)/.35))
    else:lift=0
    if t<.37:tip=0
    elif t<.44:tip=math.radians(40)*smooth((t-.37)/.07)
    elif t<.49:tip=math.radians(40)
    elif t<.55:tip=math.radians(40)*(1-smooth((t-.49)/.06))
    else:tip=0
    return lift,tip


def belt_pose(phase):
    direction=(BELT_B-BELT_A).normalized();normal=Vector((0,direction.z,-direction.y))
    length=(BELT_B-BELT_A).length;arc=math.pi*BELT_R;distance=phase*(2*length+2*arc)
    if distance<length:return BELT_A+direction*distance+normal*BELT_R,direction
    if distance<length+arc:
        angle=(distance-length)/BELT_R
        return BELT_B+BELT_R*(normal*math.cos(angle)+direction*math.sin(angle)),(-normal*math.sin(angle)+direction*math.cos(angle))
    if distance<2*length+arc:return BELT_B-direction*(distance-length-arc)-normal*BELT_R,-direction
    angle=(distance-2*length-arc)/BELT_R
    return BELT_A-BELT_R*(normal*math.cos(angle)+direction*math.sin(angle)),normal*math.sin(angle)-direction*math.cos(angle)


def chute(g,a,b,width,height=.25,covered=False):
    a,b=Vector(a),Vector(b);direction=(b-a).normalized()
    side=Vector((-direction.y,direction.x,0)).normalized()*width/2
    # All channels have actual floors and walls, not a solid beam blocking flow.
    vertices=[a-side,a+side,b+side,b-side]
    g.add(vertices,[(0,1,2,3)],IRON)
    for s in (-side,side):
        g.add([a+s,b+s,b+s+Vector((0,0,height)),a+s+Vector((0,0,height))],[(0,1,2,3)],ROOF)
        g.beam(a+s+Vector((0,0,height)),b+s+Vector((0,0,height)),.048,mat=IRON)
    if covered:
        g.add([v+Vector((0,0,height)) for v in vertices],[(3,2,1,0)],ROOF)
        for fraction in (.08,.32,.56,.80,.97):
            p=a+(b-a)*fraction
            g.beam(p-side+Vector((0,0,height+.02)),p+side+Vector((0,0,height+.02)),.055,mat=IRON)
            for s in (-side,side):square_nut(g,p+s+Vector((0,0,height+.055)),'Z',.02,1)


def material_flow(g,parts):
    # A receiver immediately beside the raised bucket feeds a steep, enclosed
    # gravity chute outside the headframe, then a short belt ahead of the engine.
    chute(g,(5.76,4.18,5.72),(6.52,4.18,5.45),1.18,.38)
    chute(g,(6.52,4.18,5.45),(7.90,4.65,2.54),.66,.34,True)
    for p in ((6.52,4.18,5.45),(7.90,4.65,2.54)):
        g.box((p[0],p[1],p[2]-.16),(.95,.42,.13),IRON)
    # Small upper inspection hatch with hinges and a positive latch.
    g.box((7.18,4.55,4.32),(.38,.30,.04),IRON)
    for x in (7.03,7.33):prism(g,(x,4.55,4.36),.025,.19,BRASS,'Y',6)
    g.box((7.18,4.55,4.40),(.15,.06,.04),CYAN)
    # Belt side rails, supported bearings, two drums, and separately animated cleats.
    for x in (7.37,8.43):
        g.beam((x,BELT_A.y,BELT_A.z),(x,BELT_B.y,BELT_B.z),.11,.18,IRON)
        for p in (BELT_A,BELT_B):
            g.box((x,p.y,(1+p.z)/2),(.09,.12,p.z-1),WOOD)
            square_nut(g,(x-.08,p.y,p.z),'X',.024,-1)
    for i,p in enumerate((BELT_A,BELT_B)):
        roller=Geometry(f'Quarry.BeltRoller{i}',p);prism(roller,p,BELT_R,.94,RUBBER,'X',12)
        for dx in (-.51,.51):prism(roller,p+Vector((dx,0,0)),.13,.065,IRON,'X',10)
        parts.append((roller,'X',-8))
    for i in range(22):
        cleat=Geometry(f'Quarry.BeltSlat{i:02d}')
        cleat.box((0,0,0),(.88,.085,.045),WOOD)
        cleat.box((0,0,.035),(.84,.024,.035),IRON)
        parts.append((cleat,'BELT_SLAT',i/22))
    # Screen feed and discharge connect directly into the visible stone box.
    chute(g,(7.90,3.72,2.10),(7.90,3.58,1.92),.85,.13)
    chute(g,(7.90,2.80,1.53),(7.90,2.50,1.47),1.85,.10)
    rng=random.Random(2291)
    for i in range(6):
        pebble=Geometry(f'Quarry.PourStone{i:02d}')
        rock(pebble,(0,0,0),(.10,.09,.075),SAND,311+i)
        parts.append((pebble,'POUR_STONE',i))
    for i in range(7):
        pebble=Geometry(f'Quarry.BeltStone{i:02d}')
        rock(pebble,(0,0,0),(.085,.08,.07),SAND,333+i)
        parts.append((pebble,'BELT_STONE',i))
    for i in range(6):
        pebble=Geometry(f'Quarry.ScreenStone{i:02d}')
        rock(pebble,(0,0,0),(.09,.08,.065),SAND,355+i)
        parts.append((pebble,'SCREEN_STONE',i))


def animate_process(obj,kind,phase,frame_end):
    if frame_end!=481:raise ValueError('Quarry process uses a 16-second loop')
    # The official exporter constructs rest meshes at frame zero, outside the
    # playable 1..481 clip. The rest pose must have an invertible transform.
    if kind in ('POUR_STONE','BELT_STONE','SCREEN_STONE'):
        obj.scale=(1,1,1);obj.keyframe_insert(data_path='scale',frame=0)
    for frame in range(1,frame_end+1):
        t=(frame-1)/480
        if kind=='BELT_SLAT':
            p,d=belt_pose((t*4+phase)%1)
            obj.location=(-p.x,-p.y,p.z);obj.rotation_mode='XYZ'
            obj.rotation_euler.x=math.atan2(-d.z,d.y)
            obj.keyframe_insert(data_path='location',frame=frame);obj.keyframe_insert(data_path='rotation_euler',frame=frame)
        else:
            if kind=='POUR_STONE':
                start=.43+phase*.009;u=(t-start)/.075;visible=0<=u<1
                p=Vector((5.93,4.18+(phase-2.5)*.085,5.92))
                if visible:p+=Vector((u*.52,0,-.15*u-.32*u*u))
            elif kind=='BELT_STONE':
                u=(t-.47-phase*.007)/.105;visible=0<=u<1
                p=BELT_A+Vector(((phase%3-1)*.21,0,.20))
                if visible:p+=(BELT_B-BELT_A)*u
            elif kind=='SCREEN_STONE':
                u=(t-.57-phase*.009)/.13;visible=0<=u<1
                p=Vector((7.9+(phase%3-1)*.30,3.72,2.01))
                if visible:p+=Vector((0,-1.20*u,-.50*u))
            else:raise ValueError('Unknown process animation: '+kind)
            obj.location=(-p.x,-p.y,p.z);obj.scale=(1,1,1) if visible else (0,0,0)
            obj.keyframe_insert(data_path='location',frame=frame);obj.keyframe_insert(data_path='scale',frame=frame)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:key.interpolation='LINEAR'








def enclosed_rooms(g):
    # Enclosed opaque facades and dark arched entrances, following the user's
    # native-building direction. The door is not an exposed furnished interior.
    for x0,x1,y,top,door_side,door_center,door_id in (
            (.185,1.92,4.30,3.25,'left',.685,'LeftWorkshopDoor'),
            (7.44,9.415,5.10,3.10,'right',8.915,'RightWorkshopDoor')):
        door_width=1.0
        door_x=door_center-door_width/2
        if door_side=='left':window_start=door_x+door_width;window_end=x1
        else:window_start=x0;window_end=door_x
        window_x=(window_start+window_end)/2
        # Outer structural corners already belong to the workshop shell.
        jambs=(window_start,) if door_side=='left' else (window_end,)
        for x in jambs:timber_column(g,x,y,1,top,.12)
        g.box(((x0+x1)/2,y,top-.15),(x1-x0,.08,.28),PLANK)
        wall(g,window_start,y,window_end,top-.27,1.02)
        window_y(g,window_x,y-.035,2.13,1)
        g.include_component(door_recipe('MineralQuarry','Door.'+door_id))
        # Exterior cladding between the door head and roof; the structural
        # corner stile already supplies its depth, so no buried box end caps.
        facade_panel(g,'Y',y-.04,door_x,door_x+door_width,2.0,top-.30,False,PLANK)
        g.box(((x0+x1)/2,y-.08,top-.25),(.64,.09,.14),IRON)
        g.box(((x0+x1)/2,y-.135,top-.25),(.51,.014,.036),CYAN)
    # Closed control-room volume under the lowest rear gallery. Windows use
    # opaque glass. The access opening is recessed and dark like native housing.
    # Set .15 forward (2026-10-22) so its rear windows end on the plinth's
    # rear face, the footprint edge.
    front,rear=6.77,7.85
    for x in (3.45,6.43):
        for y in (front,rear):timber_column(g,x,y,1.0,2.85,.14)
    for y in (front,rear):
        wall(g,3.45,y,6.43,2.85,1.04)
        for x in (3.95,4.94,5.93):window_y(g,x,y+(.035 if y==rear else -.035),2.10,1,'back' if y==rear else 'front')
    # End doorway joins the reserved ladder-access side. Upper/lower wall
    # segments deliberately leave the opening empty.
    g.box((3.45,7.34,2.425),(.08,1.0,.85),WOOD)
    g.box((6.43,7.34,1.94),(.07,1.0,1.80),PLANK)
    g.include_component(door_recipe('MineralQuarry','Door.ControlRoomDoor'))
    # A real roof cap bears on the 2.85-high walls. Its exposed top is not
    # coplanar with the wall-plank caps or column bracket tops.
    g.box((4.94,7.31,2.90),(3.05,1.15,.10),ROOF)
    # Corner posts flank the one-tile door; its header is authored once above.
    # Roof-mounted service manifold, compressed-air vessel, conduits and valves.
    for x,y,z in ((.63,5.60,3.60),(8.94,6.40,3.54)):
        prism(g,(x,y,z),.20,1.05,IRON,'Y',12)
        for yy in (y-.43,y+.43):band(g,(x,yy,z),.225,.028,.06,BRASS,'Y',12)
        for yy in (y-.36,y+.36):g.box((x,yy,z-.18),(.43,.10,.15),WOOD)
        round_pipe(g,[(x,y-.54,z),(x,y-.74,z),(x,y-.74,2.70),(x+.15,y-.74,2.70)],.055)
    # Fixed pipe runs hug the building structure; the walkway corridor stays open.
    for offset in (0,.17):
        # Rises from the plinth top, inside the x=0 tile edge.
        round_pipe(g,[(.13+offset,5.0,1.0),(.13+offset,5.0,2.90+offset),
                      (.13+offset,6.72,2.90+offset),(1.55,6.72,2.90+offset)],.062)
        round_pipe(g,[(9.31+offset,5.1,1.35),(9.31+offset,5.1,2.80+offset),
                      (9.31+offset,7.38,2.80+offset),(8.9,7.38,2.80+offset)],.055)
    for x,y,z in ((.13,5.0,2.3),(9.31,5.1,2.10)):
        prism(g,(x,y,z),.11,.075,BRASS,'Z',8)
        band(g,(x-.11,y,z),.15,.022,.035,IRON,'X',10,inner=True)
    # Exposed cable bundles on the mast, protected indicator housings, motor fins.
    for offset in (0,.035,.07):
        round_pipe(g,[(3.19+offset,7.86,1.1),(3.19+offset,7.86,6.65+offset),(3.85+offset,7.86,6.65+offset)],.012)
    for z in (2.62,4.62,6.62):
        g.box((3.14,7.94,z),(.20,.10,.22),IRON)
        g.box((3.14,7.99,z),(.055,.015,.14),CYAN)
    for x in (7.69,8.02,8.35):gauge(g,x,5.08,2.78,.075)
