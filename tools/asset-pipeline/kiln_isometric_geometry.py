"""Cement kiln, 3x3 workshop (2026-11-01 second shrink pass).

A YouTuber's first look called several Deep Frontier buildings "massive";
the user: "we need to shrink the buildings down even more". The 5x3x4 kiln
(2026-10-30 compaction) becomes a 3x3x3 workshop with the same parts, in the
same materials and atlas regions:

- the closed plank feed house with its open limestone bin (grid x 0, rows
  1..2), its one-tile porch and door in front of it (grid x 0, row 0),
- the rotary drum, its ring gear, two tyres and four carrier rollers on one
  low stone plinth under a lean-to roof whose rear wall is closed (grid x 1),
  the drive pinion and flywheel on a shaft out of the feed house,
- the masonry firebox with its arched fire, grate and chimney (grid x 2).
The front row's other two cells (x 1..2, row 0) are open buildable ground:
the stoking yard in front of the fire and the view onto the drive.

Artwork X/Y = native grid X/Y minus the layout origin (0,1): artwork x is
grid x, artwork y is grid y - 1. The footprint is artwork x 0..3, y -1..2.
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
DRUM_X0,DRUM_X1=.90,2.10
DRUM_Y,DRUM_Z=1.00,1.15
TYRES=(1.48,1.82)
RING_X=1.10
# Drive flywheel on the pinion shaft, between the ring gear and the plinth.
WHEEL_X=1.235
# The porch and door: one tile wide (grid x 0..1, row 0), the native door
# centred on it with its face 0.14 behind the front tile edge (artwork
# y=-1). The porch's back is the feed house's front (artwork y=0).
ROOM_X0,ROOM_X1=0.0,1.0
ROOM_BACK=.0
DOOR_X,DOOR_Y=.50,-.86
# Hall roof (lean-to, low at the front): its eave beams and corner shoes stay
# inside the y=0 and y=2 lines.
HALL_X0,HALL_X1=1.0,2.0
HALL_Y0,HALL_Y1=.07,1.88
HALL_Z0,HALL_Z1=2.00,2.25
# Feed house (grid x 0, rows 1..2): corner posts on the tile lines, plank
# skin 0.04 inside them, open limestone bin at the top.
HOUSE_TOP=2.40
# Firebox masonry (grid x 4, rows 1..2) and chimney.
FIRE_X0,FIRE_X1=2.0,3.0
FIRE_CX=2.5
CROWN_TOP=1.985
# The stack's collar (top +.09) stays under layer 3.
STACK_X,STACK_Y,STACK_TOP=2.5,1.45,2.90


def kiln_barrel(g,p):
    # Eight .40 courses of curved plates on a 16-sided core, two wearing
    # tyres and a 24-tooth drive ring, all one rotating part.
    x,y,z=p
    length=DRUM_X1-DRUM_X0;courses=3;pitch=length/courses
    prism(g,p,.492,length,IRON,'X',16)
    for course in range(courses):
        xa=DRUM_X0+course*pitch;xb=xa+pitch-.013
        radius=(.516,.523,.516)[course]
        for sector in range(16):
            a0=(sector+.025)*math.tau/16;a1=(sector+.975)*math.tau/16
            vertices=[(xx,y+math.cos(a)*rr,z+math.sin(a)*rr)
                      for xx in (xa,xb) for rr in (radius-.016,radius) for a in (a0,a1)]
            g.add(vertices,[(2,3,7,6)],KILN_SHELL)
    for xx in TYRES:
        band(g,(xx,y,z),.59,.082,.17,IRON,'X',16)
    # A bolted inspection cover travels with the shell.
    # Between the ring gear and the first tyre.
    xx=1.28
    verts=[(a,y+math.cos(b)*.548,z+math.sin(b)*.548)
           for a in (xx-.10,xx+.10) for b in (math.pi-.22,math.pi+.22)]
    g.add(verts,[(0,1,3,2),(2,3,1,0)],IRON)
    band(g,(RING_X,y,z),.56,.07,.085,IRON,'X',24)
    for i in range(24):
        a=i*math.tau/24
        open_beam(g,(RING_X,y+math.cos(a)*.55,z+math.sin(a)*.55),
                  (RING_X,y+math.cos(a)*.605,z+math.sin(a)*.605),.072,.055,IRON)


def bearing(g,x,y,z,w=.16):
    g.box((x,y,z-.11),(w,.30,.10),IRON)
    # The journal stands 1 cm proud of both block faces.
    prism(g,(x,y,z),.11,w+.02,IRON,'X',6)


def mechanics(g,parts):
    p=((DRUM_X0+DRUM_X1)/2,DRUM_Y,DRUM_Z);m,node=g.moving_part('ReferenceKilnBarrel',p)
    kiln_barrel(m,p);parts.append((node,'X',1))
    # Carrier rollers on one stone plinth, tangent to the tyres (.62
    # lateral, .51 below the axis).
    masonry(g,((TYRES[0]+TYRES[1])/2,DRUM_Y,.18),(TYRES[1]-TYRES[0]+.30,1.62,.36),0)
    for j,x in enumerate(TYRES):
        for k,dy in enumerate((-.62,.62)):
            y=DRUM_Y+dy;zr=DRUM_Z-.51
            g.box((x,y,.42),(.28,.38,.12),WOOD)
            for xx in (x-.13,x+.13):bearing(g,xx,y,zr,.06)
            q=(x,y,zr);m,node=g.moving_part(f'ReferenceKilnSupport{j+1}{k+1}',q)
            prism(m,q,.19,.20,IRON,'X',10)
            # Visible keyed wheel face makes its rotation legible.
            for i in range(3):
                a=i*math.tau/3;square_nut(m,(x-.12,y+math.cos(a)*.12,zr+math.sin(a)*.12),'X',.015,-1)
            parts.append((node,'X',-3))
        # Screw adjuster on the forward saddle.
        prism(g,(x,DRUM_Y-.88,.42),.034,.14,IRON,'Y',6)
        g.cylinder((x,DRUM_Y-.97,.42),.062,.055,IRON,'Y',6)
    # Drive: pinion on the ring gear and the flywheel on one shaft that
    # comes out of the feed house's east wall, in front of the drum.
    py,pz=DRUM_Y-.68,DRUM_Z-.42
    p=(RING_X,py,pz);m,node=g.moving_part('ReferenceKilnPinion',p)
    prism(m,p,.164,.12,IRON,'X',12)
    for i in range(12):
        a=i*math.tau/12
        open_beam(m,(p[0],p[1]+math.cos(a)*.15,p[2]+math.sin(a)*.15),
                  (p[0],p[1]+math.cos(a)*.199,p[2]+math.sin(a)*.199),.068,.051,IRON)
    prism(m,(1.10,py,pz),.065,.34,CRUSHER_STEEL,'X',6)
    parts.append((node,'X',-3))
    p=(WHEEL_X,py,pz);m,node=g.moving_part('ReferenceKilnDriveWheel',p)
    band(m,p,.32,.07,.095,IRON,'X',16,inner=True)
    prism(m,p,.095,.10,IRON,'X',8)
    for i in range(6):
        a=i*math.pi/3;m.beam(p,(WHEEL_X,py+math.cos(a)*.28,pz+math.sin(a)*.28),.057,mat=IRON)
    parts.append((node,'X',-3))


def masonry(g,p,size,index,skip=('-z',)):
    # Small authored differences keep masonry from reading as a perfect tile grid.
    rng=random.Random(round(p[0]*1000+p[1]*390+p[2]*167))
    size=tuple(v-rng.uniform(.001,.012) for v in size)
    # Its underside lies on the course below; skip also names the faces that
    # lie against a neighbouring stone, the crown or the closed fire chamber.
    open_box(g,p,size,KILN_STONE_LIGHT if index%7==0 else KILN_STONE,skip)


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
    """Masonry box on the tile lines x 2..3, y 0..2: arched fire opening in
    the front face, the drum's firing end entering the west wall, the stack
    on the crown."""
    cx=FIRE_CX
    # Only the stone faces that can be seen are built (3x3 kiln, 2026-11-01):
    # the courses' tops lie under the next course or the crown, the rear
    # wall's inner face is behind the soot, and stones meet their neighbours
    # end to end. The side walls' inner faces line the fire chamber seen
    # through the arch. (The measured material mix and so the
    # cost counts what is built.)
    for row in range(8):
        z=.115+row*.23
        # Front pillars either side of the arch: their backs meet the side walls.
        for xx in (2.10,2.90):masonry(g,(xx,.145,z),(.20,.29,.214),row,('-z','+z','+y'))
        # Side walls: four stretchers per course.
        for xx in (2.11,2.89):
            for j in range(4):
                # The first stone meets the pillar, the last ends on the rear face.
                ends=('-y',)+(('+y',) if j<3 else ())
                masonry(g,(xx,.50375+j*.4275,z),(.22,.4275,.214),row+j,('-z','+z')+ends)
        # Rear wall between the side walls.
        for i in range(2):masonry(g,(2.36+i*.28,1.885,z),(.28,.23,.214),row+i,('-z','+z','-y','-x','+x'))
    # Courses over the arch, between the pillars.
    for row,z in enumerate((1.475,1.705)):
        for i in range(3):masonry(g,(2.30+i*.20,.145,z),(.20,.29,.215),row+i,('-z','+z','+y','-x','+x'))
    arch(g,cx,.115,.90,.30,.44)
    # Soot at the back of the fire chamber.
    g.box((cx,.80,.74),(.56,.09,1.40),KILN_SOOT)
    # Raised fire bed over the ash pit.
    g.box((cx,.55,.33),(.56,.42,.14),KILN_SOOT)
    # Crown: two rows of long slabs.
    for j in range(2):
        for i in range(3):masonry(g,(2.167+i*.333,.5+j*1.0,1.91),(.323,.99,.15),i+j*3)
    for i in range(3):
        rock(g,(2.30+i*.20,.40+(i%2)*.10,.47),(.22,.18,.13),KILN_EMBER,1100+i)
    for i,(x,yy,h) in enumerate(((2.33,.40,.32),(2.50,.46,.44),(2.67,.40,.30))):
        p=(x,yy,.50);m,node=g.moving_part('ReferenceKilnFire'+str(i+1),p)
        flame(m,p,h,1200+i);parts.append((node,'FLAME',i))
    # Ash-pit grate and retaining bands below the fire bed; the jamb irons
    # and the register above the arch sit proud of the stone face.
    for x in (2.26,2.38,2.50,2.62,2.74):g.box((x,-.01,.22),(.026,.04,.34),IRON)
    for z in (.10,.36):g.box((cx,-.02,z),(.58,.05,.05),IRON)
    for x in (2.04,2.96):
        g.box((x,-.0175,.80),(.08,.035,1.40),IRON)
    g.box((cx,-.0375,1.47),(.70,.075,.24),IRON)
    g.box((cx,-.085,1.47),(.36,.028,.14),KILN_SHELL)
    # Gauges on the firebox's west face, read from the porch side.
    for y in (.45,.75):
        prism(g,(1.97,y,1.60),.07,.06,BRASS,'X',8,(True,False))
        prism(g,(1.937,y,1.60),.055,.015,LIME,'X',8,(True,False))


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
    prism(g,(x-.30,y,2.50),.045,.22,IRON,'X',6)
    band(g,(x-.44,y,2.50),.14,.03,.045,IRON,'X',8,inner=True)
    for i in range(4):
        a=i*math.pi/2;g.beam((x-.44,y,2.50),(x-.44,y+math.cos(a)*.12,2.50+math.sin(a)*.12),.022,mat=IRON)


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
    # A window on the front face above the porch roof (a west-face casing
    # would stand outside the x=0 edge); the drum's feed end and the drive
    # shaft enter the east face, with a feed-gate linkage beside them.
    window_y(g,.5,.04,1.78,.55)
    g.box((.985,1.72,.62),(.03,.30,.20),IRON)
    prism(g,(1.06,1.72,.62),.045,.15,IRON,'X',6)
    band(g,(1.14,1.72,.62),.14,.027,.04,IRON,'X',8,inner=True)
    for a in (0,math.pi/2,math.pi,math.pi*1.5):
        g.beam((1.14,1.72,.62),(1.14,1.72+math.cos(a)*.125,.62+math.sin(a)*.125),.022,mat=IRON)


def hall(g):
    """Lean-to roof over the drum between feed house and firebox, carried by
    their walls; closed plank rear wall."""
    sheet_roof(g,HALL_X0,HALL_Y0,HALL_X1,HALL_Y1,HALL_Z0,HALL_Z1,521)
    rear_bottom=HALL_Z1-.055-.08
    # The rear wall stands 0.10 inside the y=2 edge so its window's casing
    # stays inside the footprint.
    open_box(g,(1.51,1.85,.11),(1.02,.14,.22),KILN_STONE,('-z',))
    wall(g,1.0,1.865,2.02,rear_bottom+.02,.22)
    window_y(g,1.5,1.90,1.05,.75,'back')
    # A repaired roof sheet with lapped edge and folded seams.
    x0,x1,y0,y1=1.30,1.70,.70,1.30
    slope=(HALL_Z1-HALL_Z0)/(HALL_Y1-HALL_Y0)
    points=[(x,y,HALL_Z0+(y-HALL_Y0)*slope+.045) for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1))]
    g.add(points,[(0,1,2,3)],KILN_SHELL)
    for a,b in ((points[0],points[3]),(points[1],points[2])):g.beam(a,b,.025,.018,KILN_RUST)


def porch(g):
    # Entrance floor 0, canopy underside 1. The pitched canopy is not a
    # walking surface. The porch fills its tile (grid x 0, row 0); its back
    # is the feed house's front wall. The door casing spans the tile, so
    # the reveals are closed by inward panels just inside the side-wall
    # planes (shoulder boxes would stand outside the x=0 edge).
    g.include_component(door_recipe('CementKiln','Door.GroundDoor'))
    for x,positive in ((DOOR_X-.496,True),(DOOR_X+.496,False)):
        facade_panel(g,'X',x,DOOR_Y+.01,DOOR_Y+.09,ENTRY_Z+.08,ENTRY_Z+1.0,positive,PLANK)
    # Eave and corner shoes stay inside the front tile edge (artwork y=-1).
    # The eave beam's underside stays 5 mm above the door insert's top cap.
    sheet_roof(g,ROOM_X0+.06,DOOR_Y-.03,ROOM_X1-.06,ROOM_BACK,PORCH_Z+.14,PORCH_Z+.38,235)
    # Canopy beams 1.5 cm inside the side-wall planes.
    for x in (ROOM_X0+.065,ROOM_X1-.065):
        g.beam((x,DOOR_Y+.01,PORCH_Z+.10),(x,ROOM_BACK-.02,PORCH_Z+.10),.10,mat=WOOD)
    # Side walls meet the door insert edges and the feed house.
    for x,positive in ((ROOM_X0,False),(ROOM_X1,True)):
        facade_panel(g,'X',x,DOOR_Y-.03,ROOM_BACK,ENTRY_Z,ENTRY_Z+1.08,positive,PLANK)
    facade_panel(g,'Y',DOOR_Y+.12,ROOM_X0,ROOM_X1,ENTRY_Z+1,ENTRY_Z+1.08,False,PLANK)
    lean_roof_curb(g,ROOM_X0,DOOR_Y,ROOM_X1,ROOM_BACK,ENTRY_Z+1.08,ENTRY_Z+1.08,DOOR_Y-.03,ROOM_BACK,PORCH_Z+.14,PORCH_Z+.38,.0225)
    cage_lamp(g,DOOR_X+.40,-.78,PORCH_Z-.18)


def kiln(g,parts):
    machinery=MountedMachinery(g,0,0)
    rails=RailAssembly('WalkwayRail')
    feed_house(g);hall(g);mechanics(machinery,parts)
    firebox(machinery,parts);chimney(machinery);porch(g)
    return rails
