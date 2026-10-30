"""Cement kiln, compact 5x3 workshop (2026-10-30 compaction pass).

Steam Workshop feedback: the buildings exceeded Timberborn's scale. The user
kept the textures and asked for less scaffolding and size. The 7x5x6 kiln
with its open trestle deck, raised feed tower and walk-height drum hall
becomes a 5x3x4 ground-level workshop with the same parts, in the same
materials and atlas regions:

- a closed plank feed house with an open limestone bin on top (grid x 0),
- the rotary drum, its tyres, carrier rollers and drive pinion, on low stone
  plinths under a lean-to roof whose rear wall is closed (grid x 1..3),
- the masonry firebox with its arched fire, grate and chimney (grid x 4),
- the one-tile porch and door (grid x 3, unchanged native door contract),
- fuel logs, a coal bin and the cement output bin in the front row.

Artwork X/Y = native grid X/Y minus the layout origin (0,1): artwork x is
grid x, artwork y is grid y - 1. The footprint is artwork x 0..5, y -1..2.
Outer masses sit on those tile lines. No walkways, decks or balconies.
"""
import math
import random
from frontier_architecture import *
from industrial_kit import (open_beam,lean_wheel as wheel)
from industrial_kit import (lean_timber_column as timber_column,lean_bracket as bracket,lean_beam_joint as beam_joint,lean_sheet_roof as sheet_roof,steel_bolt,lean_cage_lamp as cage_lamp,lean_cask as cask,round_pipe,lean_bin as bin,band,prism,bolt,square_nut,open_box,lean_rock as rock,lean_rock_heap as rock_heap,lean_wall as wall,skin_board,lean_gauge as gauge)
from walkway_geometry import RailAssembly
from industrial_door_components import recipe as door_recipe
from industrial_facades import window_y,side_window
from opaque_shell_geometry import lean_roof_curb
from industrial_levels import (MountedMachinery,FACTORY_ENTRANCE as ENTRY_Z,FACTORY_PORCH_ROOF as PORCH_Z)
from reference_materials import (CRUSHER_STEEL,KILN_STONE,KILN_STONE_LIGHT,KILN_SOOT,
                                KILN_EMBER,KILN_FLAME,KILN_CEMENT,KILN_SHELL,KILN_RUST)

# Drum axis (artwork). Its feed end is inside the feed house (x<1), its
# firing end inside the firebox's west wall (x>4); x 1..4 is in view.
DRUM_X0,DRUM_X1=.90,4.10
DRUM_Y,DRUM_Z=1.00,1.15
TYRES=(2.05,3.55)
RING_X=1.30
# The porch and door: one tile wide (grid x 3..4), the native door centred on
# it with its face 0.14 behind the front tile edge (artwork y=-1).
ROOM_X0,ROOM_X1=3.0,4.0
ROOM_BACK=.28
DOOR_X,DOOR_Y=3.50,-.86
# Hall roof (lean-to, low at the front): its eave beams and corner shoes stay
# inside the y=0 and y=2 lines.
HALL_X0,HALL_X1=1.0,4.0
HALL_Y0,HALL_Y1=.07,1.88
HALL_Z0,HALL_Z1=2.30,2.60
# Feed house (grid x 0, rows 1..2): corner posts on the tile lines, plank
# skin 0.04 inside them, open limestone bin at the top.
HOUSE_TOP=2.70
# Firebox masonry (grid x 4, rows 1..2) and chimney.
FIRE_X0,FIRE_X1=4.0,5.0
FIRE_CX=4.5
CROWN_TOP=1.985
STACK_X,STACK_Y,STACK_TOP=4.5,1.45,3.85


def kiln_barrel(g,p):
    # Eight .40 courses of curved plates on a 16-sided core, two wearing
    # tyres and a 24-tooth drive ring, all one rotating part.
    x,y,z=p
    length=DRUM_X1-DRUM_X0;courses=8;pitch=length/courses
    prism(g,p,.492,length,IRON,'X',16)
    for course in range(courses):
        xa=DRUM_X0+course*pitch;xb=xa+pitch-.013
        radius=(.497,.516,.523,.523,.523,.523,.516,.497)[course]
        for sector in range(16):
            a0=(sector+.025)*math.tau/16;a1=(sector+.975)*math.tau/16
            vertices=[(xx,y+math.cos(a)*rr,z+math.sin(a)*rr)
                      for xx in (xa,xb) for rr in (radius-.016,radius) for a in (a0,a1)]
            g.add(vertices,[(2,3,7,6)],KILN_SHELL)
    for xx in TYRES:
        band(g,(xx,y,z),.59,.082,.17,IRON,'X',16)
    # A bolted inspection cover travels with the shell.
    xx=2.80
    verts=[(a,y+math.cos(b)*.548,z+math.sin(b)*.548)
           for a in (xx-.16,xx+.16) for b in (math.pi-.22,math.pi+.22)]
    g.add(verts,[(0,1,3,2),(2,3,1,0)],IRON)
    band(g,(RING_X,y,z),.56,.07,.085,IRON,'X',24)
    for i in range(24):
        a=i*math.tau/24
        open_beam(g,(RING_X,y+math.cos(a)*.55,z+math.sin(a)*.55),
                  (RING_X,y+math.cos(a)*.605,z+math.sin(a)*.605),.072,.055,IRON)


def bearing(g,x,y,z):
    g.box((x,y,z-.11),(.16,.30,.10),IRON)
    # The journal stands 1 cm proud of both block faces.
    prism(g,(x,y,z),.11,.18,IRON,'X',6)


def mechanics(g,parts):
    p=(2.50,DRUM_Y,DRUM_Z);m,node=g.moving_part('ReferenceKilnBarrel',p)
    kiln_barrel(m,p);parts.append((node,'X',1))
    # Carrier rollers on stone plinths, tangent to the tyres (.62 lateral,
    # .51 below the axis).
    for j,x in enumerate(TYRES):
        masonry(g,(x,DRUM_Y,.18),(.50,1.62,.36),j)
        for k,dy in enumerate((-.62,.62)):
            y=DRUM_Y+dy;zr=DRUM_Z-.51
            g.box((x,y,.42),(.46,.38,.12),WOOD)
            for xx in (x-.20,x+.20):bearing(g,xx,y,zr)
            q=(x,y,zr);m,node=g.moving_part(f'ReferenceKilnSupport{j+1}{k+1}',q)
            prism(m,q,.19,.22,IRON,'X',10)
            # Visible keyed wheel face makes its rotation legible.
            for i in range(3):
                a=i*math.tau/3;square_nut(m,(x-.13,y+math.cos(a)*.12,zr+math.sin(a)*.12),'X',.015,-1)
            parts.append((node,'X',-3))
        # Screw adjuster on the forward saddle.
        prism(g,(x,DRUM_Y-.95,.42),.034,.18,IRON,'Y',6)
        g.cylinder((x,DRUM_Y-1.05,.42),.062,.055,IRON,'Y',6)
    # Drive: pinion on the ring gear, a short shaft on one stone-seated
    # bearing and the flywheel, in front of the drum between ring and tyre.
    py,pz=DRUM_Y-.68,DRUM_Z-.42
    p=(RING_X,py,pz);m,node=g.moving_part('ReferenceKilnPinion',p)
    prism(m,p,.164,.12,IRON,'X',12)
    for i in range(12):
        a=i*math.tau/12
        open_beam(m,(p[0],p[1]+math.cos(a)*.15,p[2]+math.sin(a)*.15),
                  (p[0],p[1]+math.cos(a)*.199,p[2]+math.sin(a)*.199),.068,.051,IRON)
    prism(m,(1.525,py,pz),.065,.45,CRUSHER_STEEL,'X',6)
    parts.append((node,'X',-3))
    masonry(g,(1.50,py,.29),(.20,.34,.58),3)
    bearing(g,1.50,py,pz)
    p=(1.75,py,pz);m,node=g.moving_part('ReferenceKilnDriveWheel',p)
    band(m,p,.32,.07,.095,IRON,'X',16,inner=True)
    prism(m,p,.095,.18,IRON,'X',8)
    for i in range(6):
        a=i*math.pi/3;m.beam(p,(1.75,py+math.cos(a)*.28,pz+math.sin(a)*.28),.057,mat=IRON)
    parts.append((node,'X',-3))


def masonry(g,p,size,index):
    # Small authored differences keep masonry from reading as a perfect tile grid.
    rng=random.Random(round(p[0]*1000+p[1]*390+p[2]*167))
    size=tuple(v-rng.uniform(.001,.012) for v in size)
    # Its underside lies on the course below.
    open_box(g,p,size,KILN_STONE_LIGHT if index%7==0 else KILN_STONE,('-z',))


def arch(g,cx,y,cz,inner,outer):
    for i in range(11):
        a0=i*math.pi/11+.012;a1=(i+1)*math.pi/11-.012
        verts=[(cx+math.cos(a)*r,yy,cz+math.sin(a)*r)
               for yy in (y-.07,y+.11) for r in (inner,outer) for a in (a0,a1)]
        g.add(verts,[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)],KILN_STONE_LIGHT if i%3==0 else KILN_STONE)


def flame(g,p,h,seed):
    rng=random.Random(seed);x,y,z=p;n=7;verts=[]
    for zz,r,dx in ((0,.095,0),(.22*h,.12,.025),(.58*h,.073,-.018),(h,.003,.045)):
        for i in range(n):
            a=i*math.tau/n;verts.append((x+math.cos(a)*r+dx,y+math.sin(a)*r*.65,z+zz))
    faces=[tuple(reversed(range(n))),tuple(range(3*n,4*n))]
    for j in range(3):
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    g.add(verts,faces,KILN_FLAME)


def firebox(g,parts):
    """Masonry box on the tile lines x 4..5, y 0..2: arched fire opening in
    the front face, the drum's firing end entering the west wall, the stack
    on the crown."""
    cx=FIRE_CX
    for row in range(8):
        z=.115+row*.23
        # Front pillars either side of the arch.
        for xx in (4.10,4.90):masonry(g,(xx,.145,z),(.20,.29,.214),row)
        # Side walls: three stretchers per course.
        for xx in (4.11,4.89):
            for j in range(4):masonry(g,(xx,.50375+j*.4275,z),(.22,.4275,.214),row+j)
        # Rear wall between the side walls.
        for i in range(2):masonry(g,(4.36+i*.28,1.885,z),(.28,.23,.214),row+i)
    # Courses over the arch, between the pillars.
    for row,z in enumerate((1.475,1.705)):
        for i in range(3):masonry(g,(4.30+i*.20,.145,z),(.20,.29,.215),row+i)
    arch(g,cx,.115,.90,.30,.44)
    # Soot at the back of the fire chamber.
    g.box((cx,.80,.74),(.56,.09,1.40),KILN_SOOT)
    # Raised fire bed over the ash pit.
    g.box((cx,.55,.33),(.56,.42,.14),KILN_SOOT)
    # Crown: two rows of long slabs.
    for j in range(2):
        for i in range(3):masonry(g,(4.167+i*.333,.5+j*1.0,1.91),(.323,.99,.15),i+j*3)
    for i in range(3):
        rock(g,(4.30+i*.20,.40+(i%2)*.10,.47),(.22,.18,.13),KILN_EMBER,1100+i)
    for i,(x,yy,h) in enumerate(((4.33,.40,.32),(4.50,.46,.44),(4.67,.40,.30))):
        p=(x,yy,.50);m,node=g.moving_part('ReferenceKilnFire'+str(i+1),p)
        flame(m,p,h,1200+i);parts.append((node,'FLAME',i))
    # Ash-pit grate and retaining bands below the fire bed; the jamb irons
    # and the register above the arch sit proud of the stone face.
    for x in (4.26,4.38,4.50,4.62,4.74):g.box((x,-.01,.22),(.026,.04,.34),IRON)
    for z in (.10,.36):g.box((cx,-.02,z),(.58,.05,.05),IRON)
    for x in (4.04,4.96):
        g.box((x,-.0175,.80),(.08,.035,1.40),IRON)
    g.box((cx,-.0375,1.47),(.70,.075,.24),IRON)
    g.box((cx,-.085,1.47),(.36,.028,.14),KILN_SHELL)
    # Gauges on the firebox's west face, read from the porch side.
    for y in (.45,.75):
        prism(g,(3.97,y,1.60),.07,.06,BRASS,'X',8,(True,False))
        prism(g,(3.937,y,1.60),.055,.015,LIME,'X',8,(True,False))


def chimney(g):
    # Tapered, individually seamed steel stack with an open dark interior.
    x,y=STACK_X,STACK_Y;bottom,top=CROWN_TOP,STACK_TOP
    for row in range(6):
        z0=bottom+row*(top-bottom)/6;z1=bottom+(row+1)*(top-bottom)/6
        r0=.235-row*.010;r1=r0-.010
        verts=[(x+dx*r,y+dy*r,z) for z,r in ((z0,r0),(z1,r1)) for dx,dy in ((-1,-1),(1,-1),(1,1),(-1,1))]
        g.add(verts,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],IRON)
        if row%2:continue
        for dy in (-1,1):
            g.box((x,y+dy*r0,z0+.018),(r0*2,.024,.028),IRON)
        for dx in (-1,1):
            g.box((x+dx*r0,y,z0+.018),(.024,r0*2,.028),IRON)
    for dx in (-.25,.25):g.box((x+dx,y,top-.02),(.07,.57,.22),IRON)
    # The side bars end on the end bars' inner faces (no overlapping tops).
    for dy in (-.25,.25):g.box((x,y+dy,top-.02),(.43,.07,.22),IRON)
    g.box((x,y,top-.26),(.33,.33,.025),KILN_SOOT)
    for dx in (-.29,.29):g.box((x+dx,y,bottom+.05),(.08,.64,.10),IRON)
    for dy in (-.29,.29):g.box((x,y+dy,bottom+.05),(.50,.08,.10),IRON)
    # Kiln firing smoke at the top of the collar (top-.02+.22/2; no geometry).
    g.emitter('smoke',x,y,top+.09,.175)
    # Hand-operated damper on the stack's west side.
    prism(g,(x-.30,y,2.95),.045,.22,IRON,'X',6)
    band(g,(x-.44,y,2.95),.14,.03,.045,IRON,'X',8,inner=True)
    for i in range(4):
        a=i*math.pi/2;g.beam((x-.44,y,2.95),(x-.44,y+math.cos(a)*.12,2.95+math.sin(a)*.12),.022,mat=IRON)


def output(g):
    # Cement output bin in the front row before the arch.
    x,y=4.63,-.52
    bin(g,(x,y,.02),(.64,.78,.50),None)
    open_box(g,(x,y,.47),(.52,.66,.05),KILN_CEMENT,('-z',))
    rng=random.Random(554);verts=[];nx,ny=5,5
    for j in range(ny):
        for i in range(nx):
            xx=x-.25+i*.50/(nx-1);yy=y-.32+j*.64/(ny-1)
            zz=.495+.08*math.exp(-((xx-x)/.20)**2-((yy-y)/.24)**2)+rng.uniform(-.006,.006)
            verts.append((xx,yy,zz))
    g.add(verts,[(j*nx+i,j*nx+i+1,(j+1)*nx+i+1,(j+1)*nx+i) for j in range(ny-1) for i in range(nx-1)],KILN_CEMENT)


def feed_house(g):
    """Closed plank house on the tile lines x 0..1, y 0..2 with corner posts,
    a stone sill and an open limestone bin at the top."""
    h=HOUSE_TOP
    # Plain posts: collar plates would stand proud of the tile lines.
    for x in (.08,.92):
        for y in (.08,1.92):g.box((x,y,h/2),(.16,.16,h),WOOD)
    # Stone sill under the skin, 0.02 proud of it.
    for x,(inner) in ((.03,'+x'),(.97,'-x')):
        open_box(g,(x,1.0,.125),(.06,1.68,.25),KILN_STONE,('-z',inner))
    for y,inner in ((.03,'+y'),(1.97,'-y')):
        open_box(g,(.5,y,.125),(.68,.06,.25),KILN_STONE,('-z',inner))
    top=h-.14
    count=11
    for x,inner in ((.0775,'+x'),(.9225,'-x')):
        for j in range(count):
            y=.16+(j+.5)*1.68/count
            skin_board(g,(x,y,(.25+top)/2),(.075,1.68/count,top-.25),'Y',j,count,PLANK,inner)
    count=5
    for y,inner in ((.0775,'+y'),(1.9225,'-y')):
        for j in range(count):
            x=.16+(j+.5)*.68/count
            skin_board(g,(x,y,(.25+top)/2),(.68/count,.075,top-.25),'X',j,count,PLANK,inner)
    # Top frame between the posts, and the limestone load showing above it.
    for x in (.10,.90):g.box((x,1.0,top+.07),(.12,1.68,.14),WOOD)
    for y in (.10,1.90):g.box((.5,y,top+.07),(.68,.12,.14),WOOD)
    open_box(g,(.5,1.0,top+.04),(.68,1.68,.06),LIME,('-z',))
    rng=random.Random(701)
    for i in range(6):
        s=rng.uniform(.26,.34)
        rock(g,(rng.uniform(.30,.70),.32+i*.27+rng.uniform(-.04,.04),top+.09+rng.uniform(0,.05)),(s,s*.82,s*.70),LIME,701+i)
    # A window on the front face (a west-face casing would stand outside the
    # x=0 edge); the drum's feed end enters the east face, with a feed-gate
    # linkage beside it.
    window_y(g,.5,.04,1.30,.7)
    g.box((.985,.36,1.55),(.03,.30,.20),IRON)
    prism(g,(1.06,.36,1.55),.045,.15,IRON,'X',6)
    band(g,(1.14,.36,1.55),.14,.027,.04,IRON,'X',8,inner=True)
    for a in (0,math.pi/2,math.pi,math.pi*1.5):
        g.beam((1.14,.36,1.55),(1.14,.36+math.cos(a)*.125,1.55+math.sin(a)*.125),.022,mat=IRON)


def hall(g):
    """Lean-to roof over the drum between feed house and firebox, carried by
    their walls and one front post; closed plank rear wall."""
    sheet_roof(g,HALL_X0,HALL_Y0,HALL_X1,HALL_Y1,HALL_Z0,HALL_Z1,521)
    eave_bottom=HALL_Z0-.055-.08
    timber_column(g,2.55,.10,0,eave_bottom,.19,top_collar_only=True)
    for x in (2.95,2.15):g.beam((2.55,.10,eave_bottom-.55),(x,.10,eave_bottom+.05),.10,mat=WOOD)
    rear_bottom=HALL_Z1-.055-.08
    # The rear wall stands 0.10 inside the y=2 edge so its windows' casings
    # stay inside the footprint.
    open_box(g,(2.51,1.85,.11),(3.02,.14,.22),KILN_STONE,('-z',))
    wall(g,1.0,1.865,4.02,rear_bottom+.02,.22)
    window_y(g,2.0,1.90,1.05,.75,'back')
    window_y(g,3.10,1.90,1.05,.75,'back')
    # A repaired roof sheet with lapped edge and folded seams.
    x0,x1,y0,y1=3.10,3.62,.70,1.30
    slope=(HALL_Z1-HALL_Z0)/(HALL_Y1-HALL_Y0)
    points=[(x,y,HALL_Z0+(y-HALL_Y0)*slope+.045) for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1))]
    g.add(points,[(0,1,2,3)],KILN_SHELL)
    for a,b in ((points[0],points[3]),(points[1],points[2])):g.beam(a,b,.025,.018,KILN_RUST)
    # Caged lights under the eave.
    cage_lamp(g,2.55,-.01,1.62)


def porch(g):
    # Entrance floor 0, canopy underside 1. The pitched canopy is not a
    # walking surface. The porch closes behind on y=ROOM_BACK (the drum hall).
    for x in (DOOR_X-.65,DOOR_X+.65):timber_column(g,x,DOOR_Y+.01,ENTRY_Z,PORCH_Z+.10,.15)
    g.include_component(door_recipe('CementKiln','Door.GroundDoor'))
    for x in (DOOR_X-.555,DOOR_X+.555):g.box((x,DOOR_Y+.05,ENTRY_Z+.58),(.11,.08,1.00),PLANK)
    # Eave and corner shoes stay inside the front tile edge (artwork y=-1).
    # The eave beam's underside stays 5 mm above the door insert's top cap.
    sheet_roof(g,DOOR_X-.77,DOOR_Y-.03,DOOR_X+.77,ROOM_BACK,PORCH_Z+.14,PORCH_Z+.38,235)
    for x in (ROOM_X0,ROOM_X1):
        g.beam((x,DOOR_Y+.01,PORCH_Z+.10),(x,ROOM_BACK-.02,PORCH_Z+.10),.12,mat=WOOD)
    # Side walls meet the door insert edges and the porch's back wall.
    for x,positive in ((ROOM_X0,False),(ROOM_X1,True)):
        facade_panel(g,'X',x,DOOR_Y-.03,ROOM_BACK,ENTRY_Z,ENTRY_Z+1.08,positive,PLANK)
    facade_panel(g,'Y',ROOM_BACK,ROOM_X0,ROOM_X1,ENTRY_Z,ENTRY_Z+1.08,True,PLANK)
    facade_panel(g,'Y',DOOR_Y+.12,ROOM_X0,ROOM_X1,ENTRY_Z+1,ENTRY_Z+1.08,False,PLANK)
    lean_roof_curb(g,ROOM_X0,DOOR_Y,ROOM_X1,ROOM_BACK,ENTRY_Z+1.08,ENTRY_Z+1.08,DOOR_Y-.03,ROOM_BACK,PORCH_Z+.14,PORCH_Z+.38,.0225)
    cage_lamp(g,DOOR_X+.46,-.78,PORCH_Z-.18)


def fuel_logs(g):
    rng=random.Random(17)
    # Log stack before the feed house: twelve logs in three rows, end grain
    # to the front.
    for row in range(3):
        for i in range(5-row):
            x=.36+i*.29+row*.145;z=.13+row*.225;r=rng.uniform(.115,.135)
            prism(g,(x,-.52,z),r,.76,WOOD,'Y',6,(False,True))
            prism(g,(x,-.9125,z),r*.88,.025,PLANK,'Y',6,(True,False))
    for x in (.14,1.78):
        for y in (-.86,-.18):
            g.box((x,y,.38),(.11,.11,.76),WOOD)
    # Coal bin beside the logs.
    bin(g,(2.25,-.52,.02),(.62,.72,.44),KILN_SOOT,1300)


def kiln(g,parts):
    machinery=MountedMachinery(g,0,0)
    rails=RailAssembly('WalkwayRail')
    feed_house(g);hall(g);mechanics(machinery,parts)
    firebox(machinery,parts);chimney(machinery);output(g);porch(g);fuel_logs(g)
    return rails
