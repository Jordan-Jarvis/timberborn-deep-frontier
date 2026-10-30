"""Quarry visual material handling (compact 8x6x5 quarry, 2026-10-30).

Internal belts and ore are original animated artwork, not Conveyor Belt entities.
Authored directions and openings join the bucket, receiver, screen and stock bin.
Artwork coordinates: native grid = artwork + (0,-1) (industrial_layouts.Q).
"""
import math
import random
from mathutils import Vector
from frontier_architecture import Geometry,WOOD,PLANK,IRON,ROOF,SAND,BRASS
from industrial_kit import (lean_gauge as gauge,band,prism,open_box,lean_rock as rock)
from reference_materials import CRUSHER_STEEL
from industrial_facades import side_window,window_y,CYAN,RUBBER

# Hoist law: the bucket rises HOIST_TRAVEL out of the stone collar, tips
# into the receiver beside the headframe and returns.
HOIST_TRAVEL=2.10
BELT_A=Vector((7.30,4.50,1.70))
BELT_B=Vector((7.30,3.40,1.47))
BELT_R=.105
BELT_SLATS=16
RECEIVER=(6.00,4.20,2.40)
# The shallow stone tray stands on the plinth's front strip under the screen.
BIN=(7.25,1.60,1.0)
PROCESS={
    'scope':'Visual process choreography; no item creation or dependency belt entities',
    'route':['lift bucket','side tipping receiver','gravity chute',
             'short powered slat conveyor','vibrating screen','discharge chute','stone bin'],
    'receiver':list(RECEIVER),
    'beltStart':list(BELT_A),'beltEnd':list(BELT_B),
    'collectionBin':list(BIN),
    'cycleSeconds':16,'maximumBucketTipDegrees':40,
    'enclosedSections':['front operator cabin','left tool room','rear winding house (open toward the headframe)'],
    'interiors':'Closed opaque facades; no visible interiors or character props',
    'doorwayIdleAnchors':[
        {'section':'front operator cabin','position':[1.50,1.06,0],'facing':[0,-1,0]}],
    'doorwayStatus':'The ground cabin door is the only door; its native slot is exported',
    'artDirection':'Worn timber and teal metal on a stone plinth, restrained cyan instrumentation'
}


def lift_state(t):
    def smooth(v):return .5-.5*math.cos(math.pi*v)
    h=HOIST_TRAVEL
    if t<.36:lift=h*smooth(t/.36)
    elif t<.56:lift=h
    elif t<.91:lift=h*(1-smooth((t-.56)/.35))
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
        for fraction in (.15,.50,.85):
            p=a+(b-a)*fraction
            g.beam(p-side+Vector((0,0,height+.02)),p+side+Vector((0,0,height+.02)),.055,mat=IRON)


def receiver(g):
    """Plank-lined receiving hopper between the headframe's east posts,
    under the tipping bucket's lip, on two stone-seated legs."""
    x,y,top=RECEIVER
    w,d=.60,1.00
    for row in range(2):
        z=top-.10-row*.18
        for yy in (y-d/2,y+d/2):g.box((x,yy,z),(w,.07,.17),PLANK)
        for xx in (x-w/2,x+w/2):g.box((xx,y,z),(.07,d-.07,.17),PLANK)
    for xx in (x-w/2,x+w/2):g.box((xx,y,top),(.11,d+.11,.09),WOOD)
    # Tapered iron throat into the gravity chute.
    v=[(x+dx*w/2,y+dy*d/2,top-.36) for dx,dy in ((-1,-1),(1,-1),(1,1),(-1,1))]
    v+=[(x+.20+dx*.18,y+dy*.22,top-.60) for dx,dy in ((-1,-1),(1,-1),(1,1),(-1,1))]
    g.add(v,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],IRON)
    for yy in (y-.36,y+.36):
        g.box((x+.12,yy,(1.0+top-.36)/2),(.12,.12,top-.36-1.0),WOOD)


def material_flow(g,parts):
    receiver(g)
    # Covered gravity chute from the receiver throat to the belt head.
    chute(g,(6.20,4.20,1.80),(7.10,4.45,1.78),.56,.24,True)
    g.box((7.10,4.45,1.68),(.60,.36,.10),IRON)
    # Belt side rails, supported bearings, two drums and separately animated cleats.
    for x in (6.79,7.81):
        g.beam((x,BELT_A.y,BELT_A.z),(x,BELT_B.y,BELT_B.z),.10,.16,IRON)
        for p in (BELT_A,BELT_B):
            g.box((x,p.y,(1+p.z)/2),(.09,.12,p.z-1),WOOD)
    for i,p in enumerate((BELT_A,BELT_B)):
        roller=Geometry(f'Quarry.BeltRoller{i}',p);prism(roller,p,BELT_R,.94,RUBBER,'X',10)
        for dx in (-.51,.51):prism(roller,p+Vector((dx,0,0)),.13,.065,IRON,'X',8)
        parts.append((roller,'X',-8))
    for i in range(BELT_SLATS):
        cleat=Geometry(f'Quarry.BeltSlat{i:02d}')
        cleat.box((0,0,0),(.88,.085,.045),WOOD)
        parts.append((cleat,'BELT_SLAT',i/BELT_SLATS))
    # Screen feed and discharge connect directly into the stone bin.
    chute(g,(7.30,3.30,1.50),(7.30,3.14,1.42),.80,.12)
    # Discharge from the screen's foot into the stone tray.
    chute(g,(7.30,2.42,1.24),(7.25,2.10,1.21),1.00,.10)
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
    from quarry_isometric_geometry import HOIST_X,HOIST_Y,BUCKET_BASE,BUCKET_H
    for frame in range(1,frame_end+1):
        t=(frame-1)/480
        if kind=='BELT_SLAT':
            p,d=belt_pose((t*4+phase)%1)
            obj.location=(-p.x,-p.y,p.z);obj.rotation_mode='XYZ'
            obj.rotation_euler.x=math.atan2(-d.z,d.y)
            obj.keyframe_insert(data_path='location',frame=frame);obj.keyframe_insert(data_path='rotation_euler',frame=frame)
        else:
            if kind=='POUR_STONE':
                # From the tipped bucket's lip into the receiver.
                start=.43+phase*.009;u=(t-start)/.075;visible=0<=u<1
                p=Vector((HOIST_X+.62,HOIST_Y+(phase-2.5)*.085,BUCKET_BASE+HOIST_TRAVEL+BUCKET_H+.05))
                if visible:p+=Vector((u*.30,0,-.10*u-.20*u*u))
            elif kind=='BELT_STONE':
                u=(t-.47-phase*.007)/.105;visible=0<=u<1
                p=BELT_A+Vector(((phase%3-1)*.21,0,.20))
                if visible:p+=(BELT_B-BELT_A)*u
            elif kind=='SCREEN_STONE':
                u=(t-.57-phase*.009)/.13;visible=0<=u<1
                p=Vector((7.30+(phase%3-1)*.25,3.28,1.55))
                if visible:p+=Vector((0,-1.20*u,-.33*u))
            else:raise ValueError('Unknown process animation: '+kind)
            obj.location=(-p.x,-p.y,p.z);obj.scale=(1,1,1) if visible else (0,0,0)
            obj.keyframe_insert(data_path='location',frame=frame);obj.keyframe_insert(data_path='scale',frame=frame)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:key.interpolation='LINEAR'
