"""Permanent quarry, compact 8x6x5 (2026-10-30 compaction pass).

Steam Workshop feedback: the buildings exceeded Timberborn's scale. The user
kept the textures and asked for less scaffolding and size; the mines get
extra care. The 11x7x9 quarry with its tall lattice headframe, side ladder
mast and two upper workshops becomes a solid stone plinth with:

- a lined shaft collar over the seam and a four-post timber headframe with
  the head sheave on its top frame (no lattice, no ladder mast),
- the winding drum in an open-fronted, flat-roofed winding house behind it,
  the rope running from the drum up to the sheave and down to the bucket,
- the tipping bucket, receiver, gravity chute, slat belt, screen and stone
  bin on the plinth's east side,
- the front operator cabin with the native door, a flat-roofed tool room and
  supplies on the plinth's west side, the native water tank in front.

The origin, entrance and the 5x5 seam foundation cells (grid x 3..7,
y 1..5) are those of the old registration, so a saved quarry stays over its
seam. Artwork coordinates: native grid = artwork + (0,-1); the footprint is
artwork x 0..8, y 1..7. No walkable decks, galleries or ladders.
"""
import math
import random
from mathutils import Vector
from frontier_architecture import *
from industrial_kit import (open_beam,lean_gauge as gauge)
from industrial_kit import (lean_timber_column as timber_column,lean_sheet_roof as sheet_roof,lean_cage_lamp as cage_lamp,round_pipe,lean_bin as bin,band,prism,square_nut,open_box,lean_rock as rock,lean_rock_heap as rock_heap,lean_wall as wall,skin_board)
from reference_materials import (CRUSHER_STEEL,KILN_STONE,KILN_STONE_LIGHT,KILN_SOOT,CIVIC_FORGED_PANEL)
from walkway_geometry import RailAssembly
from quarry_process_details import material_flow,side_window,window_y,lift_state,HOIST_TRAVEL,BIN
from industrial_door_components import recipe as door_recipe
from industrial_levels import QUARRY_ENTRANCE

PLINTH_TOP=1.0
HOIST_X,HOIST_Y=5.10,4.18
BUCKET_BASE=.25
BUCKET_H=.62
# Rope attachment (top of the carriage yoke) above the bucket floor.
BUCKET_TOP=BUCKET_BASE+1.0
ROPE_TOP=4.45
SHEAVE_R=.31
DRUM=(HOIST_X,5.85,1.62)
DRUM_R=.467
# Shaft collar opening in the plinth, and the headframe post centres.
COLLAR=(4.40,3.50,5.80,4.90)
POSTS_X=(4.22,5.98)
POSTS_Y=(3.33,5.07)
HEAD_Z=4.12
GUIDES_X=(4.62,5.58)
GUIDE_Y=4.80
# Ground cabin: door centred on grid x=1.5, facade 0.18 behind artwork y=1.
CABIN_X,CABIN_FRONT=1.50,1.18

ACCESS={
    'plinthTop':PLINTH_TOP,
    'walkableDecks':'None; the quarry is not climbed (no ladder mast since 2026-10-30)',
    'groundDoor':[CABIN_X,1.14,QUARRY_ENTRANCE],
    'hoistExclusion':[COLLAR[0],COLLAR[1],COLLAR[2],COLLAR[3]],
    'status':'Authored clearance and motion contract; not native navigation or gameplay verification'
}


def platform(g,x0,y0,x1,y1,top):
    deck(g,x0,y0,x1,y1,top-.07)


def plinth(g,x0,y0,x1,y1,top):
    '''Solid stone process plinth (not a deck); its bottom is just below ground.'''
    g.box(((x0+x1)/2,(y0+y1)/2,(top-.02)/2),(x1-x0,y1-y0,top+.02),KILN_STONE)


def heavy_beam(g,a,b,w=.26,plates=True):
    g.beam(a,b,w,w,WOOD)
    for t in ((.12,.88) if plates else ()):
        p=tuple(a[i]+(b[i]-a[i])*t for i in range(3))
        if abs(b[0]-a[0])>=max(abs(b[1]-a[1]),abs(b[2]-a[2])):
            g.box((p[0],p[1]-w/2-.02,p[2]),(w+.12,.04,w+.03),IRON)
        elif abs(b[1]-a[1])>=abs(b[2]-a[2]):
            g.box((p[0]-w/2-.02,p[1],p[2]),(.04,w+.12,w+.03),IRON)


def flat_roof(g,x0,y0,x1,y1,top,seed):
    """Flat roof of the native roof sheets (the sheet roof laid level): its
    edge beams are the fascia, its corner shoes stay inside the walls' lines."""
    sheet_roof(g,x0+.11,y0+.11,x1-.11,y1-.11,top,top,seed)


def foundation(g):
    # One stone plinth, top at layer 1, around the collar opening; the cabin
    # stands in front of it on the ground. Outer faces are on tile edges.
    cx0,cy0,cx1,cy1=COLLAR
    plinth(g,0,2.06,cx0,7.0,PLINTH_TOP)
    plinth(g,cx1,2.06,8.0,7.0,PLINTH_TOP)
    plinth(g,cx0,2.06,cx1,cy0,PLINTH_TOP)
    plinth(g,cx0,cy1,cx1,7.0,PLINTH_TOP)
    # Front strip either side of the cabin (the stone tray stands on it).
    plinth(g,0,1.0,.905,2.06,PLINTH_TOP)
    plinth(g,2.10,1.0,8.0,2.06,PLINTH_TOP)
    # The lined collar: stone blocks against the plinth's inner faces, the
    # dark shaft floor and a timber collar frame on the plinth top.
    g.box(((cx0+cx1)/2,(cy0+cy1)/2,.065),(cx1-cx0,cy1-cy0,.10),KILN_SOOT)
    for k,z in enumerate((.26,.56,.86)):
        for i in range(3):
            x=cx0+(i+.5)*(cx1-cx0)/3
            for y,skip in ((cy0+.075,'-y'),(cy1-.075,'+y')):
                open_box(g,(x,y,z),((cx1-cx0)/3-.01,.15,.28),KILN_STONE_LIGHT if (i+k)%3==0 else KILN_STONE,('-z',skip))
        for j in range(2):
            y=cy0+.15+(j+.5)*(cy1-cy0-.30)/2
            for x,skip in ((cx0+.075,'-x'),(cx1-.075,'+x')):
                open_box(g,(x,y,z),(.15,(cy1-cy0-.30)/2-.01,.28),KILN_STONE,('-z',skip))
    # Frame beams 0.26 wide: their inner faces stand 2 cm behind the lining's.
    for y in (cy0,cy1):g.box(((cx0+cx1)/2,y,1.04),(cx1-cx0+.26,.26,.16),WOOD)
    for x in (cx0,cx1):g.box((x,(cy0+cy1)/2,1.04),(.26,cy1-cy0-.26,.16),WOOD)


def headframe(g):
    """Four timber posts round the collar, a head frame carrying the sheave,
    mid ties on the closed sides and short knee braces; the east side stays
    open for the tipping bucket."""
    top=HEAD_Z+.08
    for x in POSTS_X:
        for y in POSTS_Y:
            open_box(g,(x,y,PLINTH_TOP+.03),(.40,.40,.06),IRON,('-z',))
            heavy_beam(g,(x,y,PLINTH_TOP),(x,y,top),.26,plates=False)
            for z in (2.10,3.70):g.box((x,y,z),(.31,.31,.12),IRON)
    # The head beams run 3 cm past the posts' outer faces.
    for y in POSTS_Y:heavy_beam(g,(POSTS_X[0]-.16,y,HEAD_Z),(POSTS_X[1]+.16,y,HEAD_Z),.24,plates=False)
    for x in POSTS_X:heavy_beam(g,(x,POSTS_Y[0]+.12,HEAD_Z),(x,POSTS_Y[1]-.12,HEAD_Z),.24,plates=False)
    # Mid ties: front, rear and west at 2.6; east low at 1.9, under the receiver.
    for y in POSTS_Y:heavy_beam(g,(POSTS_X[0]+.13,y,2.60),(POSTS_X[1]-.13,y,2.60),.18,plates=False)
    heavy_beam(g,(POSTS_X[0],POSTS_Y[0]+.13,2.60),(POSTS_X[0],POSTS_Y[1]-.13,2.60),.18,plates=False)
    heavy_beam(g,(POSTS_X[1],POSTS_Y[0]+.13,1.90),(POSTS_X[1],POSTS_Y[1]-.13,1.90),.18,plates=False)
    # Knee braces under the head frame on the west and rear faces.
    for y,sign in ((POSTS_Y[0],1),(POSTS_Y[1],-1)):
        g.beam((POSTS_X[0],y+sign*.10,3.55),(POSTS_X[0],y+sign*.55,HEAD_Z-.10),.11,mat=WOOD)
    for x,sign in ((POSTS_X[0],1),(POSTS_X[1],-1)):
        g.beam((x+sign*.10,POSTS_Y[1],3.55),(x+sign*.55,POSTS_Y[1],HEAD_Z-.10),.11,mat=WOOD)
    # Sheave carriers on the head frame, with the sheave bearings.
    for x in (4.85,5.35):
        g.box((x,(POSTS_Y[0]+POSTS_Y[1])/2,HEAD_Z+.19),(.14,POSTS_Y[1]-POSTS_Y[0]+.12,.14),WOOD)
        g.box((x,4.49,ROPE_TOP-.05),(.18,.26,.16),IRON)
    prism(g,(5.10,4.49,ROPE_TOP),.06,.54,CRUSHER_STEEL,'X',8)
    # Timber guides for the carriage, from the shaft floor to the head.
    for x in GUIDES_X:
        g.box((x,GUIDE_Y,(.15+HEAD_Z-.12)/2),(.105,.14,HEAD_Z-.12-.15),WOOD)
        for z in (1.70,2.90):g.box((x,GUIDE_Y,z),(.17,.20,.10),IRON)
    # Iron straps from the guides back to the rear mid tie.
    for x in GUIDES_X:
        g.box((x,4.93,2.60),(.10,.12,.10),IRON)
    for x,y in ((POSTS_X[0],POSTS_Y[0]-.13),(POSTS_X[1],POSTS_Y[0]-.13)):
        cage_lamp(g,x,y,2.35)
    # Boarded shaft house: the west and rear faces closed to the rope slot,
    # an upper band on the front; the east face stays open for the tipping
    # bucket and the front below the band shows the collar.
    def boards(axis,line,a,b,z0,z1):
        count=max(2,round((b-a)/.17))
        for j in range(count):
            c=a+(j+.5)*(b-a)/count
            p=(line,c,(z0+z1)/2) if axis=='Y' else (c,line,(z0+z1)/2)
            size=(.07,(b-a)/count,z1-z0) if axis=='Y' else ((b-a)/count,.07,z1-z0)
            skin_board(g,p,size,axis,j,count,PLANK,None)
    boards('Y',POSTS_X[0],POSTS_Y[0]+.13,POSTS_Y[1]-.13,PLINTH_TOP+.12,HEAD_Z-.12)
    boards('X',POSTS_Y[1],POSTS_X[0]+.13,POSTS_X[1]-.13,PLINTH_TOP+.12,3.40)
    boards('X',POSTS_Y[0],POSTS_X[0]+.13,POSTS_X[1]-.13,2.72,HEAD_Z-.12)


def wheel(g,p,r,axis,segments=16):
    band(g,p,r,.09,.16,IRON,axis,segments)
    prism(g,p,.13,.26,IRON,axis,8)
    for i in range(6):
        a=i*math.tau/6
        q=(p[0],p[1]+math.cos(a)*(r-.04),p[2]+math.sin(a)*(r-.04)) if axis=='X' else (p[0]+math.cos(a)*(r-.04),p[1],p[2]+math.sin(a)*(r-.04))
        s=(p[0],p[1]+math.cos(a)*.12,p[2]+math.sin(a)*.12) if axis=='X' else (p[0]+math.cos(a)*.12,p[1],p[2]+math.sin(a)*.12)
        open_beam(g,s,q,.082,.065,IRON,end=False)


def winding_house(g):
    """Flat-roofed winding house on the plinth's rear (artwork x 3..7,
    y 5.6..7): closed sides and back, open toward the headframe so the rope
    leaves the drum under the roof's front edge."""
    x0,x1,y0,y1=3.0,7.0,5.60,7.0
    top=2.85
    for x in (x0+.08,x1-.08):
        for y in (y0+.08,y1-.08):g.box((x,y,(PLINTH_TOP+top-.12)/2),(.16,.16,top-.12-PLINTH_TOP),WOOD)
    # Open front: the walls keep their inner faces.
    count=8
    for x in (x0+.0775,x1-.0775):
        for j in range(count):
            y=y0+.16+(j+.5)*(y1-y0-.32)/count
            skin_board(g,(x,y,(PLINTH_TOP+top-.12)/2),(.075,(y1-y0-.32)/count,top-.12-PLINTH_TOP),'Y',j,count,PLANK,None)
    # The back wall stands 0.10 inside the y=7 edge so its window casings
    # stay inside the footprint.
    wall(g,x0+.16,y1-.135,x1-.16,top-.12,PLINTH_TOP)
    window_y(g,4.20,y1-.10,1.95,.8,'back')
    window_y(g,5.80,y1-.10,1.95,.8,'back')
    side_window(g,x1-.04,6.30,1.95,.8,'right')
    g.box(((x0+x1)/2,y0+.08,top-.20),(x1-x0-.32,.16,.16),WOOD)
    flat_roof(g,x0,y0,x1,y1,top,731)
    cage_lamp(g,3.60,y0+.0,2.45)
    # The engine: housing and flywheel on the east side of the drum.
    g.box((6.20,6.62,1.35),(.44,.44,.70),CIVIC_FORGED_PANEL)
    for z in (1.20,1.45):prism(g,(6.20,6.385,z),.05,.03,BRASS,'Y',8,(True,False))


def machinery(g,parts):
    # Winding drum with helical rope turns, stone-seated bearings.
    cx,cy,cz=DRUM
    p=DRUM;m=Geometry('Quarry.HoistDrum',p)
    prism(m,p,.43,1.64,IRON,'X',16)
    for dx in (-.87,.87):prism(m,(cx+dx,cy,cz),.57,.11,IRON,'X',16)
    for i in range(10):
        x=cx-.7565+i*.155;prism(m,(x,cy,cz),DRUM_R,.125,WOOD,'X',8,(False,False))
    for dx in (-1.08,1.08):prism(m,(cx+dx,cy,cz),.13,.43,CRUSHER_STEEL,'X',6)
    wheel(m,(cx-1.20,cy,cz),.54,'X')
    parts.append((m,'HOIST_DRUM',1.0))
    for dx in (-1.01,1.01):
        x=cx+dx
        open_box(g,(x,cy,(PLINTH_TOP+1.245)/2),(.34,.58,1.245-PLINTH_TOP),KILN_STONE,('-z',))
        g.box((x,cy,1.34),(.38,.67,.19),WOOD)
        prism(g,(x,cy,cz),.18,.23,IRON,'X',8)
    # Head sheave over the shaft.
    p=(HOIST_X,4.49,ROPE_TOP);m=Geometry('Quarry.HeadSheave',p)
    wheel(m,p,SHEAVE_R,'X',12);parts.append((m,'HOIST_SHEAVE',1.0))
    # Static rope run from the drum's top to the sheave's rear.
    round_pipe(g,[(HOIST_X,cy-.10,cz+DRUM_R-.01),(HOIST_X,4.49+SHEAVE_R-.01,ROPE_TOP+.03)],.019)
    # Carriage: yoke on the guides, bucket hinged on its east side.
    p=(HOIST_X,HOIST_Y,BUCKET_BASE);carrier=Geometry('Quarry.LiftCarriage',p)
    yoke_y=4.68
    for xx in GUIDES_X:
        carrier.box((xx,GUIDE_Y,BUCKET_BASE+.52),(.21,.24,.14),IRON)
        carrier.beam((xx,yoke_y,BUCKET_BASE+.20),(xx,yoke_y,BUCKET_TOP),.075,mat=IRON)
    carrier.beam((GUIDES_X[0],yoke_y,BUCKET_TOP),(GUIDES_X[1],yoke_y,BUCKET_TOP),.065,mat=IRON)
    carrier.beam((HOIST_X,yoke_y-.0375,BUCKET_TOP),(HOIST_X,HOIST_Y,BUCKET_TOP),.075,mat=IRON)
    band(carrier,(HOIST_X,HOIST_Y,BUCKET_TOP),.075,.020,.045,IRON,'Y',8,inner=True)
    hinge=(HOIST_X+.46,HOIST_Y,BUCKET_BASE+.58)
    for yy in (HOIST_Y-.47,HOIST_Y+.47):
        prism(carrier,(hinge[0],yy,hinge[2]),.06,.10,BRASS,'Y',8)
    carrier.beam((GUIDES_X[1],yoke_y,BUCKET_BASE+.50),(hinge[0],HOIST_Y+.52,hinge[2]),.055,mat=IRON)
    parts.append((carrier,'HOIST_LIFT',1.0))
    bucket=Geometry('Quarry.TippingBucket',hinge);bin(bucket,p,(.92,.86,BUCKET_H),None)
    parts.append((bucket,'HOIST_TIP',1.0))
    load=Geometry('Quarry.BucketLoad',hinge);rng=random.Random(848)
    for i in range(5):
        rock(load,(HOIST_X+rng.uniform(-.30,.30),HOIST_Y+rng.uniform(-.28,.28),BUCKET_BASE+BUCKET_H-.12),(.20,.17,.15),SAND,84800+i)
    parts.append((load,'HOIST_LOAD',1.0))
    rope=Geometry('Quarry.LiftCable',(HOIST_X,HOIST_Y,ROPE_TOP))
    prism(rope,(HOIST_X,HOIST_Y,(ROPE_TOP+BUCKET_TOP)/2),.022,ROPE_TOP-BUCKET_TOP,WOOD,'Z',6)
    parts.append((rope,'HOIST_CABLE',1.0))
    # Drive train: belt and screen drives at the east edge, engine flywheel
    # in the winding house.
    for name,p,r,turns in (
        ('Quarry.InputFlywheel',(7.86,4.05,1.70),.40,4),
        ('Quarry.SortingDrive',(7.86,2.95,1.40),.22,-6),
        ('Quarry.EngineFlywheel',(6.55,6.10,1.68),.42,4)):
        m=Geometry(name,p);wheel(m,p,r,'X',16 if r>.3 else 12);parts.append((m,'X',turns))
    for y,z in ((4.05,1.70),(2.95,1.40)):
        open_box(g,(7.86,y,(PLINTH_TOP+z-.18)/2),(.20,.30,z-.18-PLINTH_TOP),WOOD,('-z',))
        prism(g,(7.86,y,z),.15,.24,IRON,'X',8)


def sorting(g,parts):
    x,y,z=BIN
    bin(g,(x,y,z+.02),(1.30,.90,.18),SAND,738)
    # Suspended vibrating screen between the belt foot and the discharge.
    p=(7.30,2.80,1.35);m=Geometry('Quarry.SortingSieve',p)
    for xx in (6.88,7.72):m.beam((xx,3.20,1.45),(xx,2.45,1.25),.06,.07,IRON)
    for i in range(9):
        yy=2.48+i*.085;zz=1.25+(yy-2.45)*.20/.75
        m.beam((6.89,yy,zz),(7.71,yy,zz),.023,mat=IRON)
    parts.append((m,'SIEVE',.020))
    for xx in (6.88,7.72):
        for yy,zz in ((2.47,1.25),(3.18,1.45)):
            prism(g,(xx,yy,(PLINTH_TOP+zz-.04)/2),.04,zz-.04-PLINTH_TOP,IRON,'Z',6)


def cabin(g):
    # Ground operator cabin in front of the plinth. Its door is centred on grid
    # tile column 1 with the face 0.14 behind the grid y=0 edge (artwork y=1).
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
    def cabin_top(y):return 1.30+(1.57-1.30)*(y-(front-.07))/(2.12-(front-.07))-.0225
    for x,positive in ((x0,False),(x1,True)):
        g.add([(x,front,QUARRY_ENTRANCE),(x,2.055,QUARRY_ENTRANCE),
               (x,2.055,cabin_top(2.055)),(x,front,cabin_top(front))],
              [(0,1,2,3) if positive else (3,2,1,0)],PLANK)
    facade_panel(g,'Y',front,x0,x1,1.26,cabin_top(front),False,PLANK)
    facade_panel(g,'Y',2.055,x0,x1,1.35,cabin_top(2.055),True,PLANK)
    sheet_roof(g,x0-.14,front-.07,x1+.13,2.12,1.30,1.57,712)
    cage_lamp(g,x1-.03,front+.02,.94)
    g.box((cx,1.075,QUARRY_ENTRANCE-.045),(.75,.15,.15),WOOD)


def tool_room(g):
    """Flat-roofed tool room on the plinth's west side (artwork x 0..2,
    y 2.3..5), one layer high: corner posts on the tile lines, plank skin
    0.04 inside them."""
    x0,x1,y0,y1=0.0,2.0,2.30,7.0
    top=2.10
    for x in (x0+.08,x1-.08):
        for y in (y0+.08,y1-.08):g.box((x,y,(PLINTH_TOP+top-.12)/2),(.16,.16,top-.12-PLINTH_TOP),WOOD)
    count=20
    for x,inner in ((x0+.0775,'+x'),(x1-.0775,'-x')):
        for j in range(count):
            y=y0+.16+(j+.5)*(y1-y0-.32)/count
            skin_board(g,(x,y,(PLINTH_TOP+top-.12)/2),(.075,(y1-y0-.32)/count,top-.12-PLINTH_TOP),'Y',j,count,PLANK,inner)
    for y,inner in ((y0+.0775,'+y'),(y1-.0775,'-y')):
        count=8
        for j in range(count):
            x=x0+.16+(j+.5)*(x1-x0-.32)/count
            skin_board(g,(x,y,(PLINTH_TOP+top-.12)/2),((x1-x0-.32)/count,.075,top-.12-PLINTH_TOP),'X',j,count,PLANK,inner)
    # Two sheet runs (a single 4.5-long run stretches the native sheet
    # strips); the rear run steps up 4 cm, its eave 2 cm behind the front's.
    sheet_roof(g,x0+.11,y0+.11,x1-.11,4.64,top,top,732)
    sheet_roof(g,x0+.13,4.66,x1-.13,y1-.11,top+.04,top+.04,733)
    # Front and east windows only: a west or rear casing would stand outside
    # the footprint edge.
    for x in (.62,1.38):window_y(g,x,y0+.04,1.40,.70)
    for y in (3.60,5.70):side_window(g,x1-.04,y,1.40,.80,'right')
    cage_lamp(g,1.65,y0+.04,1.85)


def supplies(g):
    # The native water tank stands inside the winding house (no props on
    # open plinth or ground cells, 2026-10-30); its line runs along the
    # house's west wall to the drum's bearing.
    from native_building_assets import water_barrel
    water_barrel(g,'QuarryWaterBarrel',(3.45,6.55,PLINTH_TOP),.55)
    round_pipe(g,[(3.45,6.26,1.30),(3.45,6.05,1.30),(3.80,6.05,1.30)],.05)
    band(g,(3.45,6.16,1.30),.08,.025,.06,BRASS,'Y',8)


def quarry(g,parts):
    # No walkways or balconies: the rail assembly stays empty.
    rails=RailAssembly('WalkwayRail')
    foundation(g);headframe(g);winding_house(g);machinery(g,parts)
    sorting(g,parts);material_flow(g,parts);cabin(g);tool_room(g);supplies(g)
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
            radius={'HOIST_DRUM':DRUM_R,'HOIST_SHEAVE':SHEAVE_R}[kind]
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
