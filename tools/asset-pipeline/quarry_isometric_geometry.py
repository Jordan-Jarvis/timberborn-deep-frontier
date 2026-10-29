"""Permanent quarry from the two ISOMETRIC illustrations on mining sheet 01.

Original geometry, no characters, plan-view tracing or concept tile counts.
The authored access landings and ladder clearances are explicit at the source.
Native grid occupancy, navigation and dependency integration remain separate.
"""
import math
import random
from frontier_architecture import *
from industrial_geometry import steel_bolt,bracket,timber_column,beam_joint,sheet_roof,access_stair
from reference_details import cage_lamp,cask,round_pipe
from industrial_kit import (open_beam,lean_wheel as wheel,lean_gauge as gauge,bracket as nutted_bracket)
from industrial_kit import (steel_bolt,lean_bracket as bracket,lean_timber_column as timber_column,lean_beam_joint as beam_joint,lean_sheet_roof as sheet_roof,lean_cage_lamp as cage_lamp,lean_cask as cask,round_pipe,lean_bin as bin,band,prism,bolt,square_nut,open_box,lean_rock as rock,lean_rock_heap as rock_heap,lean_wall as wall,skin_board)
from reference_materials import (CRUSHER_STEEL,KILN_STONE,KILN_STONE_LIGHT,KILN_SOOT,
                                KILN_RUST,KILN_WOOD_SPLIT,KILN_WOOD_WEAR,KILN_DUST,WATER)
from walkway_geometry import RailAssembly
from quarry_process_details import material_flow,enclosed_rooms,side_window,lift_state
from industrial_door_components import recipe as door_recipe
from industrial_levels import QUARRY_ENTRANCE

HOIST_TRAVEL=3.60
BUCKET_BASE=1.55
BUCKET_TOP=BUCKET_BASE+1.30
ROPE_TOP=7.96
HOIST_X,HOIST_Y=5.10,4.18
# Ground cabin: door centred on grid x=1.5, facade 0.18 behind artwork y=1.
CABIN_X,CABIN_FRONT=1.50,1.18

# These are physical source coordinates, not inferred block occupations.
# The quarry has no walkable decks, galleries or balconies: the process floor
# is a solid stone plinth (layer 1 top) and the headframe is served by a
# maintenance ladder mast with one narrow, rail-free top landing.
ACCESS={
    'plinthTop':1.0,
    'ladderCellCenter':[2.5,7.5],
    'ladderClearOpening':[2.12,7.12,2.88,7.88],
    'ladderFlights':[[1,3],[3,5],[5,7]],
    'serviceLanding':7.0,
    'walkableDecks':'None; maintenance ladder only',
    'bodyCheckRadius':0.20,
    'hoistExclusion':[4.25,3.40,5.95,5.00],
    'ladderNodes':['Quarry.AccessLadder01','Quarry.AccessLadder02','Quarry.AccessLadder03'],
    'status':'Authored clearance and motion contract; not native navigation or gameplay verification'
}


def platform(g,x0,y0,x1,y1,top):
    deck(g,x0,y0,x1,y1,top-.07)


def plinth(g,x0,y0,x1,y1,top):
    '''Solid stone process plinth (not a deck); its bottom is just below ground.'''
    g.box(((x0+x1)/2,(y0+y1)/2,(top-.02)/2),(x1-x0,y1-y0,top+.02),KILN_STONE)


def footing(g,x,y,width=.55):
    # 12k cap (2026-10-29): no anchor nuts; the bottom faces lie on the ground.
    open_box(g,(x,y,.16),(width,width,.30),KILN_STONE,('-z',))
    open_box(g,(x,y,.335),(width+.035,width+.035,.065),IRON,('-z',))


def heavy_beam(g,a,b,w=.34,plates=True):
    # Fish plates without their nuts (12k cap); plates=False for the ring ties.
    g.beam(a,b,w,w,WOOD)
    for t in ((.12,.88) if plates else ()):
        p=tuple(a[i]+(b[i]-a[i])*t for i in range(3))
        if abs(b[0]-a[0])>=max(abs(b[1]-a[1]),abs(b[2]-a[2])):
            g.box((p[0],p[1]-.19,p[2]),(.49,.045,.37),IRON)
        else:
            g.box((p[0]-.19,p[1],p[2]),(.045,.49,.36),IRON)


def shaft_collar(g):
    # Actual open volume above ground; do not fake a walkable floor over the shaft.
    x0,x1,y0,y1=3.24,6.74,3.16,6.62
    g.box((5.0,4.89,.065),(3.34,3.28,.10),KILN_SOOT)
    # Stone lining in long blocks (12k cap; was 7 and 6 per course).
    for z in (.26,.56,.86):
        # Their outer faces lie on the plinth's inner faces.
        for i in range(5):
            x=x0+(i+.5)*(x1-x0)/5
            for y in (y0,y1):open_box(g,(x,y,z),(.69,.28,.28),KILN_STONE if i%3 else KILN_STONE_LIGHT,('-z','-y' if y==y0 else '+y'))
        for i in range(4):
            y=y0+.25+(i+.5)*(y1-y0-.5)/4
            for x in (x0,x1):open_box(g,(x,y,z),(.28,.73,.28),KILN_STONE,('-z','-x' if x==x0 else '+x'))
    for y in (y0,y1):g.box((4.99,y,1.04),(3.80,.38,.16),WOOD)
    for x in (x0,x1):g.box((x,4.89,1.04),(.38,3.08,.16),WOOD)
    # Paired timber guide rails descend visibly into the lined collar.
    for x in (4.32,5.88):
        g.box((x,4.95,3.94),(.105,.14,7.72),WOOD)
        for z in (.63,2.70,4.77,6.84):
            g.box((x,4.95,z),(.18,.18,.14),IRON)


def foundation(g):
    # Solid stone plinth (top at layer 1) in the same stepped, cut-away
    # footprint as the art, with no rails. Outer faces are on tile edges
    # (artwork y = grid y - 1); inner faces meet the stone shaft collar.
    plinth(g,0,2.0,3.10,8.0,1.0)
    plinth(g,2.30,1.0,3.10,2.0,1.0)
    plinth(g,3.10,1.0,6.88,3.02,1.0)
    plinth(g,6.88,1.0,11.0,8.0,1.0)
    plinth(g,3.10,6.76,6.88,8.0,1.0)
    # (The stone step in front of the sorting yard, artwork y 0..1, was a
    # forecourt with nothing on it; removed with its footprint row, 2026-10-22.)
    shaft_collar(g)


def headframe(g):
    # Four heavy inclined legs, intermediate ties, gussets and rear X bracing.
    feet=[(2.95,2.60),(7.05,2.60),(2.95,6.75),(7.05,6.75)]
    heads=[(3.65,3.60),(6.35,3.60),(3.65,6.20),(6.35,6.20)]
    for (x,y),(xx,yy) in zip(feet,heads):
        footing(g,x,y,.65)
        heavy_beam(g,(x,y,.38),(xx,yy,7.18),.37)
        # End plates already reinforce the lower leg at z=1.196. The first
        # intermediate collar belongs above that plate and its fasteners.
        for z in (3.15,6.88):
            t=(z-.38)/6.80;px=x+(xx-x)*t;py=y+(yy-y)*t
            bracket(g,px,py,z,.39)
        if (x,y)==(2.95,2.60):
            # The front-left leg keeps its low collar with nuts: a head
            # blocks and covers roof cell (3,1,0) in the registered
            # connection faces (outputs/connection-faces).
            t=(1.65-.38)/6.80
            nutted_bracket(g,x+(xx-x)*t,y+(yy-y)*t,1.65,.39)
    for z in (3.10,5.10,7.10):
        t=(z-.38)/6.80
        pts=[(x+(xx-x)*t,y+(yy-y)*t,z) for (x,y),(xx,yy) in zip(feet,heads)]
        for a,b in ((0,1),(2,3),(0,2),(1,3)):heavy_beam(g,pts[a],pts[b],.24,plates=False)
    # The front hoist bay stays open from collar to pulley.
    for x in (3.35,6.65):
        heavy_beam(g,(x,3.05,3.23),(x,6.45,5.02),.20)
        heavy_beam(g,(x+.22,6.45,3.23),(x+.22,3.05,5.02),.20)
    heavy_beam(g,(3.28,6.51,1.15),(6.50,6.25,4.92),.21)
    heavy_beam(g,(6.72,6.51,1.15),(3.50,6.25,4.92),.21)
    for y in (3.58,6.20):
        heavy_beam(g,(3.40,y,7.18),(6.60,y,7.18),.34)
    for x in (3.67,6.33):
        heavy_beam(g,(x,3.38,7.15),(x,6.48,7.15),.32)
    # Bearing gantry above the open bucket path.
    for x in (4.48,5.72):
        heavy_beam(g,(x,4.18,7.20),(x,4.18,8.10),.21)
    heavy_beam(g,(4.25,4.18,8.14),(5.95,4.18,8.14),.28)


def ladder_mesh(g,x,y,bottom,top,handhold=.44):
    # Two continuous stiles, bolted round rungs, anti-slip tread sleeves and
    # handholds above each exit. Designed for a reserved vertical access bay.
    # 12k cap: each rung is one six-sided timber rod (no iron core, brass end
    # caps or clamp nuts), the old tread sleeve's section: its edge covers
    # roof cell (2,6,0) in the registered connection faces.
    for xx in (x-.29,x+.29):
        g.box((xx,y,(bottom+top+handhold)/2),(.09,.10,top-bottom+handhold),WOOD)
        for z in (bottom+.10,top-.10):
            g.box((xx,y+.08,z),(.16,.24,.10),IRON)
    count=round((top-bottom)/.20)
    if abs(count*.20-(top-bottom))>1e-6:raise ValueError('Ladder rise must be an exact multiple of rung spacing')
    for i in range(count):
        z=bottom+.16+i*.20
        prism(g,(x,y-.025,z),.034,.65,WOOD,'X',6,(False,False),phase=0)


def access_tower(g,parts):
    # The maintenance ladder mast is beside the headframe, never inside its
    # moving bucket. Galleries and balconies are removed; one narrow,
    # rail-free hatch frame at the top serves the head gear.
    # The rear posts, collars and landing end on the plinth's rear face
    # (artwork y 8, the footprint edge since 2026-10-22). The posts stand
    # beside the ladder opening (x 2.12..2.88), so its clearance is unchanged.
    for x in (1.98,3.12):
        for y,base in ((6.88,6.88),(7.88,7.80)):
            footing(g,x,base,.36);timber_column(g,x,y,.36,7.12,.17)
    top=ACCESS['serviceLanding']
    platform(g,1.90,6.80,3.35,7.12,top)
    platform(g,1.90,7.88,3.35,7.995,top)
    platform(g,1.90,7.12,2.12,7.88,top)
    platform(g,2.88,7.12,3.35,7.88,top)
    for level in (3.0,5.0,7.0):
        # Ring frames tie the mast posts at each flight joint.
        for yy in (6.85,7.88):g.box((2.62,yy,level-.35),(1.60,.13,.22),WOOD)
    for i,(bottom,top) in enumerate(ACCESS['ladderFlights']):
        node=Geometry(ACCESS['ladderNodes'][i]);ladder_mesh(node,2.5,7.68,bottom,top,handhold=.44 if top==7 else 0)
        parts.append((node,'STATIC',0))


def room(g,x0,y0,x1,y1,top,seed,door_side):
    from opaque_shell_geometry import lean_roof_curb
    for x in (x0,x1):
        for y in (y0,y1):
            # Front door bays have a header above the one-tile wall insert,
            # not a full post running through that entrance.
            over_door=y==y0 and x==(x0 if door_side=='left' else x1)
            timber_column(g,x,y,2.0 if over_door else 1.0,top,.22,top_collar_only=True)
            if (x,y)==(1.92,4.30):
                # Its foot collar keeps its nuts: their heads keep cell
                # (1,3,1)'s Right face out of the registered connection faces.
                nutted_bracket(g,x,y,1.0+.115,.22)
    wall(g,x0,y1,x1,top-.08,1.04)
    # Opaque side cladding behind the native window assemblies. The old
    # full-width window band was wider than those assemblies and leaked sky.
    for x in (x0,x1):
        count=math.ceil((y1-y0)/.17)
        for i in range(count):
            y=y0+(i+.5)*(y1-y0)/count
            # Inner faces kept: the connection-face registration samples them.
            skin_board(g,(x,y,(top-.12+1.04)/2),(.07,(y1-y0)/count,top-.12-1.04),'Y',i,count,PLANK,None)
        side_window(g,x+(-.035 if x==x0 else .035),(y0+y1)/2,2.15,1,'left' if x==x0 else 'right')
        for z in (1.15,top-.15):g.box((x,(y0+y1)/2,z),(.13,y1-y0-.04,.12),WOOD)
        for yy in (y0+.12,y1-.43):
            g.beam((x-.05,yy,1.12),(x-.05,yy+.21,1.54),.070,mat=WOOD)
    heavy_beam(g,(x0,y0,top-.10),(x1,y0,top-.10),.16)
    lean_roof_curb(g,x0,y0,x1,y1,top-.12,top-.12,y0-.23,y1+.20,top+.12,top+.49,.0225)
    sheet_roof(g,x0-.18,y0-.23,x1+.18,y1+.20,top+.12,top+.49,seed)


def workshops(g):
    room(g,.35,4.30,1.92,6.56,3.25,710,'left')
    room(g,7.44,5.10,9.25,7.52,3.10,711,'right')
    for x in (.52,1.74):cage_lamp(g,x,4.31,2.87)
    # Exterior regulator cabinet; enclosed room interiors are not modeled.
    g.box((7.65,5.27,2.15),(.29,.18,.50),IRON)
    for z in (2.03,2.27):
        prism(g,(7.65,5.16,z),.082,.03,BRASS,'Y',8,(True,False))
        prism(g,(7.65,5.14,z),.064,.012,KILN_WOOD_WEAR,'Y',8,(True,False))
        g.beam((7.65,5.13,z),(7.68,5.13,z+.041),.009,mat=IRON)
    cage_lamp(g,9.20,5.06,2.72)
    # Lower operator cabin in front of the plinth. Its door is centred on grid
    # tile column 1 with the face 0.14 behind the grid y=2 edge (artwork y=1).
    cx,front=CABIN_X,CABIN_FRONT
    x0,x1=cx-.595,cx+.595
    for x in (x0-.02,x1+.03):timber_column(g,x,front+.07,QUARRY_ENTRANCE,1.34,.16)
    for j in range(8):
        a=x0+j*1.19/8;b=x0+(j+1)*1.19/8
        facade_panel(g,'Y',2.055,a,b,QUARRY_ENTRANCE,1.35,True,PLANK)
    for lo,hi in ((cx-.54,cx-.50),(cx+.50,cx+.54)):
        facade_panel(g,'Y',front,lo,hi,QUARRY_ENTRANCE,1.26,False,PLANK)
    wall(g,cx-.50,front,cx+.50,1.26,QUARRY_ENTRANCE+1.0)
    g.include_component(door_recipe('MineralQuarry','Door.GroundDoor'))
    # The ground cabin has opaque side walls, rather than a door between
    # four posts with unobstructed views straight through the workshop.
    def cabin_top(y):return 1.30+(1.57-1.30)*(y-(front-.07))/(2.12-(front-.07))-.0225
    for x,positive in ((x0,False),(x1,True)):
        g.add([(x,front,QUARRY_ENTRANCE),(x,2.055,QUARRY_ENTRANCE),
               (x,2.055,cabin_top(2.055)),(x,front,cabin_top(front))],
              [(0,1,2,3) if positive else (3,2,1,0)],PLANK)
    facade_panel(g,'Y',front,x0,x1,1.26,cabin_top(front),False,PLANK)
    facade_panel(g,'Y',2.055,x0,x1,1.35,cabin_top(2.055),True,PLANK)
    # Same pitch as before, raised 4 cm to keep a header above the door wall.
    sheet_roof(g,x0-.14,front-.07,x1+.13,2.12,1.30,1.57,712)
    cage_lamp(g,x1-.03,front+.02,.94)
    g.box((cx,1.075,QUARRY_ENTRANCE-.045),(.75,.15,.15),WOOD)


def wheel(g,p,r,axis,segments=16):
    # 12k cap: one 16-sided rim (12 on the small sheave and drive; the inner
    # brass ring went), six spokes.
    band(g,p,r,.09,.16,IRON,axis,segments)
    prism(g,p,.13,.26,IRON,axis,8)
    for i in range(6):
        a=i*math.tau/6
        q=(p[0],p[1]+math.cos(a)*(r-.04),p[2]+math.sin(a)*(r-.04)) if axis=='X' else (p[0]+math.cos(a)*(r-.04),p[1],p[2]+math.sin(a)*(r-.04))
        s=(p[0],p[1]+math.cos(a)*.12,p[2]+math.sin(a)*.12) if axis=='X' else (p[0]+math.cos(a)*.12,p[1],p[2]+math.sin(a)*.12)
        open_beam(g,s,q,.082,.065,IRON,end=False)


def machinery(g,parts):
    # Main hoisting drum with many actual helical rope windings.
    p=(4.99,5.62,7.54);m=Geometry('Quarry.HoistDrum',p)
    prism(m,p,.43,1.64,IRON,'X',16)
    for x in (4.12,5.86):prism(m,(x,5.62,7.54),.57,.11,IRON,'X',16)
    # Each rope turn is its outer surface; between turns the core shows as the
    # groove. (12k cap: 10 broad 8-sided turns; were 42.)
    for i in range(10):
        x=4.2335+i*.155;prism(m,(x,5.62,7.54),.467,.125,WOOD,'X',8,(False,False))
    # Six-sided stubs: the wheel hub is an 8-sided prism of the same radius.
    for x in (3.91,6.07):prism(m,(x,5.62,7.54),.13,.43,CRUSHER_STEEL,'X',6)
    wheel(m,(3.79,5.62,7.54),.54,'X')
    parts.append((m,'HOIST_DRUM',1.0))
    for x in (3.99,6.01):
        g.box((x,5.62,7.26),(.38,.67,.19),WOOD)
        prism(g,(x,5.62,7.54),.18,.23,IRON,'X',8)
        band(g,(x-.14,5.62,7.54),.18,.035,.045,BRASS,'X',8,inner=True)
    # Sheave guides the moving lift cable down the open shaft.
    p=(HOIST_X,4.49,ROPE_TOP);m=Geometry('Quarry.HeadSheave',p)
    wheel(m,p,.31,'X',12);parts.append((m,'HOIST_SHEAVE',1.0))
    round_pipe(g,[(HOIST_X,5.15,7.54),(HOIST_X,4.72,8.16)],.019)
    p=(HOIST_X,HOIST_Y,BUCKET_BASE);carrier=Geometry('Quarry.LiftCarriage',p)
    # A rear yoke keeps guides and cable separate from the tipping container.
    for xx in (4.32,5.88):
        carrier.box((xx,4.95,BUCKET_BASE+.52),(.21,.24,.14),IRON)
        carrier.beam((xx,4.95,BUCKET_BASE+.20),(xx,4.95,BUCKET_TOP),.075,mat=IRON)
    carrier.beam((4.32,4.95,BUCKET_TOP),(5.88,4.95,BUCKET_TOP),.075,mat=IRON)
    # Butts against the cross beam's face rather than overlapping its top.
    carrier.beam((HOIST_X,4.9125,BUCKET_TOP),(HOIST_X,HOIST_Y,BUCKET_TOP),.075,mat=IRON)
    band(carrier,(HOIST_X,HOIST_Y,BUCKET_TOP),.075,.020,.045,IRON,'Y',8,inner=True)
    # Bucket hinge and trunnions attach to the rear yoke. They do not rotate the cable.
    hinge=(HOIST_X+.59,HOIST_Y,BUCKET_BASE+.76)
    for yy in (HOIST_Y-.61,HOIST_Y+.61):
        prism(carrier,(hinge[0],yy,hinge[2]),.07,.13,BRASS,'Y',8)
    carrier.beam((5.88,4.95,BUCKET_BASE+.70),(hinge[0],4.79,hinge[2]),.065,mat=IRON)
    parts.append((carrier,'HOIST_LIFT',1.0))
    bucket=Geometry('Quarry.TippingBucket',hinge);bin(bucket,p,(1.18,1.12,.76),None)
    parts.append((bucket,'HOIST_TIP',1.0))
    load=Geometry('Quarry.BucketLoad',hinge);rng=random.Random(848)
    for i in range(6):
        rock(load,(HOIST_X+rng.uniform(-.40,.40),HOIST_Y+rng.uniform(-.36,.36),BUCKET_BASE+.60),(.23,.20,.18),SAND,84800+i)
    parts.append((load,'HOIST_LOAD',1.0))
    rope=Geometry('Quarry.LiftCable',(HOIST_X,HOIST_Y,ROPE_TOP))
    prism(rope,(HOIST_X,HOIST_Y,(ROPE_TOP+BUCKET_TOP)/2),.022,ROPE_TOP-BUCKET_TOP,WOOD,'Z',6)
    parts.append((rope,'HOIST_CABLE',1.0))
    # Low-level power train beneath the sorting deck and the covered engine.
    for name,p,r,axis,turns in (
        ('Quarry.InputFlywheel',(9.70,3.60,1.64),.62,'X',4),
        ('Quarry.SortingDrive',(7.52,3.60,1.64),.27,'X',-6),
        ('Quarry.EngineFlywheel',(9.45,6.30,2.00),.53,'X',4)):
        m=Geometry(name,p);wheel(m,p,r,axis,16 if r>.4 else 12);parts.append((m,axis,turns))
    prism(g,(8.54,3.60,1.64),.105,2.65,IRON,'X',8)
    for x in (7.53,9.34):
        g.box((x,3.60,1.25),(.38,.55,.35),WOOD)
        prism(g,(x,3.60,1.64),.18,.26,IRON,'X',8)


def sorting(g,parts):
    bin(g,(8.00,1.91,1.00),(2.42,1.48,.46),SAND,738)
    # Deep slatted sorting tray, angled toward the separate finished-stone bin.
    for i in range(11):
        x=6.83+i*.2114;g.beam((x,3.80,1.83),(x,2.68,1.35),.12,.055,WOOD)
    for x in (6.72,9.06):
        g.beam((x,3.85,1.86),(x,2.66,1.37),.11,.21,IRON)
    # Six separator fingers (12k cap; were eleven) fit inside the two outer tray beams.
    for i in range(6):
        x=6.92+i*.36;g.box((x,3.30,1.78),(.10,.04,.24),IRON)
    # Suspended sieve frame has a restrained, physically connected shake.
    p=(7.90,3.20,1.61);m=Geometry('Quarry.SortingSieve',p)
    for x in (6.88,8.92):m.beam((x,3.73,1.92),(x,2.79,1.52),.06,.07,IRON)
    # Sparser screen bars (12k cap: 12, were 18 at 5.4 cm).
    for i in range(12):
        y=2.80+i*.0818;z=1.52+(y-2.80)*.40/.94
        m.beam((6.89,y,z),(8.91,y,z),.023,mat=IRON)
    parts.append((m,'SIEVE',.020))
    for x in (6.89,8.92):
        for y,z in ((2.81,1.56),(3.71,1.94)):
            prism(g,(x,y,z-.11),.046,.19,IRON,'Z',6)


def water_and_supplies(g):
    # Closed pump circuit and valved fill port; no decorative infinite discharge.
    from native_building_assets import water_barrel
    water_barrel(g,'QuarryWaterBarrel',(.94,2.80,1.03),.62)
    round_pipe(g,[(.94,2.80,1.1),(.94,2.57,1.1),(.12,2.57,1.1),(.12,2.57,.58)],.095)
    for x in (.18,.65):
        prism(g,(x,2.57,1.10),.15,.055,IRON,'X',8)
    band(g,(.38,2.57,1.45),.15,.027,.04,IRON,'Z',8,inner=True)
    for i in range(4):
        a=i*math.pi/2;g.beam((.38,2.57,1.45),(.38+math.cos(a)*.13,2.57+math.sin(a)*.13,1.45),.025,mat=BRASS)
    prism(g,(.38,2.57,1.29),.025,.31,IRON,'Z',6)
    # Covered supply bins on the plinth beside the ladder mast. (2026-10-22:
    # the bin hanging over the rear plinth edge, and the spare sheave and
    # timber stack left buried in the plinth, were removed.)
    for x,y,w,d in ((.95,7.12,.63,.55),(1.65,7.13,.55,.55)):
        bin(g,(x,y,1.03),(w,d,.48),None)
        for i in range(4):g.box((x,y-d*.35+i*d*.23,1.555),(w,.11,.055),PLANK)
    for x in (3.07,6.93):
        cage_lamp(g,x,2.46,2.68)
        g.box((x,2.48,2.17),(.25,.09,.28),IRON)
    cage_lamp(g,3.13,7.88,6.55)


def quarry(g,parts):
    # No walkways or balconies: the rail assembly stays empty. (The 7 mm roof
    # scratches, 8 mm dust flecks and 1.2 cm polished rung strips of the old
    # wear() were sub-pixel at game zoom; removed 2026-10-29.)
    rails=RailAssembly('WalkwayRail')
    foundation(g);headframe(g);access_tower(g,parts)
    workshops(g);machinery(g,parts);sorting(g,parts);water_and_supplies(g)
    material_flow(g,parts);enclosed_rooms(g)
    return rails


def animate_hoist(obj,kind,frame_end):
    """One kinematic law drives bucket, taut rope, winding drum and sheave."""
    if frame_end!=481:raise ValueError('Quarry hoist uses an explicit 16-second cycle')
    from mathutils import Quaternion
    base=obj.location.copy();length=ROPE_TOP-BUCKET_TOP
    for frame in range(1,frame_end+1):
        t=(frame-1)/(frame_end-1)
        lift,tip=lift_state(t)
        if kind=='HOIST_LIFT':
            obj.location=base+Vector((0,0,lift));obj.keyframe_insert(data_path='location',frame=frame)
        elif kind=='HOIST_CABLE':
            obj.scale.z=(length-lift)/length;obj.keyframe_insert(data_path='scale',frame=frame)
        elif kind in ('HOIST_DRUM','HOIST_SHEAVE'):
            radius={'HOIST_DRUM':.467,'HOIST_SHEAVE':.31}[kind]
            obj.rotation_mode='QUATERNION';obj.rotation_quaternion=Quaternion((-1,0,0),lift/radius)
            obj.keyframe_insert(data_path='rotation_quaternion',frame=frame)
        elif kind in ('HOIST_TIP','HOIST_LOAD'):
            obj.location=base+Vector((0,0,lift));obj.keyframe_insert(data_path='location',frame=frame)
            obj.rotation_mode='QUATERNION';obj.rotation_quaternion=Quaternion((0,-1,0),tip)
            obj.keyframe_insert(data_path='rotation_quaternion',frame=frame)
            if kind=='HOIST_LOAD':
                if t<.43 or t>=.95:amount=1
                elif t<.49:amount=1-(t-.43)/.06
                else:amount=0
                obj.scale=(amount,amount,amount);obj.keyframe_insert(data_path='scale',frame=frame)
        elif kind=='SIEVE':
            obj.location=base+Vector((.020*math.sin(math.tau*t*32),0,0))
            obj.keyframe_insert(data_path='location',frame=frame)
        else:raise ValueError('Unsupported quarry movement: '+kind)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:key.interpolation='LINEAR'
