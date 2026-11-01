"""Concrete mixer, 3x2 workshop (2026-11-01 second shrink pass).

A YouTuber's first look called several Deep Frontier buildings "massive";
the user: "we need to shrink the buildings down even more". The 4x3x3 mixer
(2026-10-30 compaction) becomes a 3x2x3 workshop with the same parts and
materials:

- the closed operator room (grid x 0..2, both rows) with its door on tile
  column 1, its steel plate roof carrying the aggregate and cement hoppers
  (rear row) and the native header tank (front left), which feed the drum
  by two short chutes and a drop line; the roof's front-right cell is an
  open platform,
- the mixing drum (same profile, 0.46 scale) on four rollers on low brick
  piers in the east column, its flywheel on a brick drive pedestal behind
  it,
- the discharge chute and the wet trough on a brick base in the front-right
  cell; the water riser and inlet on the room's west wall.

Native grid XY (layout origin 0); outer walls and pedestals sit on the tile
lines x 0..3, y 0..2. No walkways, decks or balconies.
"""
import math
import random

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS, facade_panel
from industrial_facades import side_window, window_y
from industrial_door_components import recipe as door_recipe
from industrial_kit import (open_beam,lean_wheel as wheel,lean_gauge as gauge,bracket as nutted_bracket)
from industrial_kit import (lean_timber_column as timber_column,lean_bracket as bracket,lean_sheet_roof as sheet_roof,lean_machinery_shell as machinery_shell,round_pipe,lean_cage_lamp as cage_lamp,lean_bin as bin,band,prism,open_box,lean_rock as rock)
from reference_materials import (
    CRUSHER_STEEL, KILN_CEMENT, KILN_DUST, KILN_STONE, KILN_STONE_LIGHT,
    CIVIC_FORGED_PANEL,
)
# No concrete surfaces: the mixer unlocks before concrete exists (user,
# 2026-10-30). Footings, piers and pedestals are brick;
# the roof the hoppers stand on is riveted steel plate.
from native_building_assets import water_barrel
from walkway_geometry import RailAssembly
# Brick footings, piers and pedestals (2026-10-30, bricks pass; were coursed
# grey kiln masonry): bricks exist from 600 science, before the mixer.
from factory_registration import machine_slab, brick_box

# Native grid XY (layout origin 0). The operator door is centred on tile
# column 1 with its face 0.12 behind the y=0 edge; the native entrance is the
# path cell in front of it, (1,-1,0), and the door cell is the doorstep.
DOOR_X, DOOR_FACE, WALL_FRONT = 1.50, .12, .16
# Operator room: west wall 0.10 inside the x=0 edge (corner piers stand in it
# as pilasters), east wall on the x=2 line, rear wall on the y=2 edge, front
# wall WALL_FRONT behind the y=0 edge. One storey: walls to WALL_TOP, the
# steel plate roof's top on layer 2.
ROOM_W, ROOM_E, ROOM_FRONT, ROOM_REAR = .10, 2.0, WALL_FRONT, 2.0
WALL_TOP = 1.90
ROOF_TOP = 2.0
# Drum: the original profile and fittings at this scale about its centre,
# axis Y in the east column (grid x 2..3); its mouth faces the front.
DRUM = (2.50, 1.17, .92)
DRUM_SCALE = .46
ACCESS = {
    "groundDoor": [DOOR_X, DOOR_FACE, 0],
    "decks": "None: the machine is not walked on at upper levels",
}


def pier(g, x, y, top, collar=bracket, column=timber_column):
    brick_box(g,(x, y, .15),(.36, .36, .30))
    column(g, x, y, .29, top, .24)
    for z in (1.15,):
        if z < top - .3:
            collar(g, x, y, z, .24)


def hopper(g, x, y, bottom, width, length, material, seed, *, powder=False):
    """Open plank-lined bin standing on the room's steel plate roof, with its
    individually piled input."""
    top = bottom + .82
    for row in range(4):
        z = bottom + .10 + row * .20
        for yy in (y-length/2, y+length/2):
            g.box((x, yy, z), (width, .085, .185), PLANK)
        for xx in (x-width/2, x+width/2):
            g.box((xx, y, z), (.085, length-.085, .185), PLANK)
    for xx in (x-width/2, x+width/2):
        g.box((xx, y, top), (.15, length+.15, .12), WOOD)
        for yy in (y-length/2, y+length/2):
            nutted_bracket(g, xx, yy, top-.15, .18)
    for yy in (y-length/2, y+length/2):
        g.box((x, yy, top), (width-.15, .15, .12), WOOD)
        for xx in (x-width*.30, x+width*.30):
            g.box((xx, yy-.05 if yy < y else yy+.05, bottom+.40), (.06, .035, .67), IRON)
    g.box((x, y, bottom+.53), (width-.13,length-.13,.15), material)
    rng = random.Random(seed)
    if powder:
        vertices=[]
        for row in range(4):
            for col in range(5):
                u=col/4*2-1;v=row/3*2-1
                vertices.append((x+u*(width-.15)/2,y+v*(length-.15)/2,
                                 bottom+.60+.22*(1-u*u)*(1-v*v)+rng.uniform(-.015,.015)))
        g.add(vertices,[(r*5+c,r*5+c+1,(r+1)*5+c+1,(r+1)*5+c)
                        for r in range(3) for c in range(4)],material)
    else:
        for row in range(2):
            for col in range(3):
                xx=x-width*.30+col*width*.30+rng.uniform(-.03,.03)
                yy=y-length*.22+row*length*.44+rng.uniform(-.03,.03)
                size=rng.uniform(.24,.32)
                rock(g,(xx,yy,bottom+.66+rng.uniform(-.02,.06)),
                     (size,size*.82,size*.64),material,seed+row*6+col)


def operator_room(g):
    # One storey: door at ground, the steel plate roof's top on layer two.
    w,e,front,rear=ROOM_W,ROOM_E,ROOM_FRONT,ROOM_REAR
    top=WALL_TOP-.04
    # Rear corner piers; the front corners are the front wall's own boards.
    for x in (w+.10,e-.10):
        pier(g,x,rear-.22,top)
    count=10
    for x,positive in ((w,False),(e,True)):
        for j in range(count):
            a=front+j*(rear-front)/count;b=front+(j+1)*(rear-front)/count
            facade_panel(g,'X',x,a,b,0,WALL_TOP,positive,PLANK)
    # Brick plinth on all four walls (a band 1 cm proud of the boards).
    for x,face in ((w+.04,'left'),(e-.04,'right')):
        # Ends short of the rear plinth (which runs across both corners).
        brick_box(g,(x,(front+.015+rear-.11)/2,.575),(.10,rear-.11-front-.015,.95),faces=(face,),cap=.12)
    brick_box(g,((w+.015+e-.015)/2,rear-.055,.575),(e-w-.03,.10,.95),faces=('back',),cap=.12)
    brick_box(g,((w+.015+DOOR_X-.515)/2,WALL_FRONT+.04,.575),(DOOR_X-.515-w-.015,.10,.95),faces=('front',),cap=.12)
    count=12
    for j in range(count):
        a=w+j*(e-w)/count;b=w+(j+1)*(e-w)/count
        facade_panel(g,'Y',rear-.015,a,b,0,WALL_TOP,True,PLANK)
    # Front wall: plank boards west of the door, the native door on tile
    # column 1 (its east jamb on the room's east wall), the head wall above
    # it. The plank wall's front face is WALL_FRONT.
    a,b=w+.005,DOOR_X-.5
    for i in range(5):
        x=a+(i+.5)*(b-a)/5
        g.box((x,WALL_FRONT+.04,WALL_TOP/2),((b-a)/5,.08,WALL_TOP),PLANK)
    g.include_component(door_recipe('ConcreteMixer','Door.MixerOperatorDoor'))
    g.doorways.append({"name":"MixerOperatorDoor","position":[DOOR_X,DOOR_FACE,0]})
    facade_panel(g,'Y',WALL_FRONT,DOOR_X-.5,e,1.08,WALL_TOP,False,PLANK)
    # Riveted steel plate roof (the hoppers' platform), an iron band under
    # its edge on the wall heads.
    # A timber slab (its underside and edge fascia) under one riveted plate.
    cx,cy=(w+e)/2,(front+rear)/2
    open_box(g,(cx,cy,ROOF_TOP-.0575),(e-w,rear-front,.085),PLANK,('+z',))
    open_box(g,(cx,cy,ROOF_TOP-.0075),(e-w,rear-front,.015),CIVIC_FORGED_PANEL,('-z',))
    # (The rear wall stands 1.5 cm inside the y=2 edge, so the band stays
    # inside the footprint.)
    for y in (front-.0075,rear-.0075):
        g.box(((w+e)/2,y,WALL_TOP-.045),(e-w,.015,.07),IRON)
    for x in (w-.0075,e+.0075):
        g.box((x,(front+rear)/2,WALL_TOP-.045),(.015,rear-front,.07),IRON)
    window_y(g,.55,WALL_FRONT,1.42,.55)
    gauge(g,1.15,WALL_FRONT-.03,1.50,.085)
    cage_lamp(g,1.12,WALL_FRONT-.02,1.12)
    # Side window only: a casing on the rear wall would stand outside the
    # y=2 edge.
    side_window(g,w,1.30,1.42,.6,'left')
    # Control cabinet on the east wall, facing the drum.
    g.box((e+.05,1.80,.95),(.10,.30,.45),CIVIC_FORGED_PANEL)
    for z in (.84,1.06):
        prism(g,(e+.115,1.80,z),.05,.03,BRASS,'X',8,(False,True))
    # Aggregate and cement hoppers side by side on the roof's rear row; the
    # aggregate chute runs along the row line past the cement hopper.
    hopper(g,.53,1.44,ROOF_TOP,.80,.84,KILN_STONE_LIGHT,930)
    hopper(g,1.55,1.55,ROOF_TOP,.70,.62,KILN_CEMENT,970,powder=True)
    # Two runs: level over the roof, then down past its edge (the lower run
    # is narrower, so the flanges never share a plane at the joint).
    chute(g,(.93,1.04,2.55),(2.08,1.04,2.10),.22)
    chute(g,(2.08,1.04,2.10),(2.34,1.04,1.48),.20)
    chute(g,(1.90,1.55,2.44),(2.36,1.40,1.48),.22)


def drum(g, parts):
    s=DRUM_SCALE;cx,cy,cz=DRUM
    def at(dx,dy,dz):return (cx+dx*s,cy+dy*s,cz+dz*s)
    m=Geometry('Mixer.Drum',DRUM)
    machinery_shell(m,DRUM,[(t*s,r*s) for t,r in ((-1.23,.27),(-1.05,.46),(-.78,.79),
                         (-.52,1.03),(.63,1.03),(.98,.73),(1.23,.29))],'Y',16)
    for dy in (-.50,.61):
        band(m,at(0,dy,0),1.065*s,.055*s,.14*s,CRUSHER_STEEL,'Y',16)
    for i in range(8):
        a=i*math.pi/4
        dx=math.cos(a)*1.043;dz=math.sin(a)*1.043
        m.beam(at(dx,-.50,dz),at(dx,.61,dz),.033*s,.022*s,IRON)
    # Drive journal and ring at the rear end (the mouth faces the trough).
    prism(m,at(0,1.28,0),.19*s,.32*s,IRON,'Y',10)
    band(m,at(0,1.30,0),.36*s,.08*s,.13*s,BRASS,'Y',12,inner=True)
    parts.append((m,'Y',1))
    # Rollers under each tyre, 35 degrees off the bottom, on low brick piers
    # clear of the room's east wall.
    reach=1.065*s+.11
    for dy in (-.50,.61):
        y=cy+dy*s
        for side in (-1,1):
            x=cx+side*reach*math.sin(math.radians(35));z=cz-reach*math.cos(math.radians(35))
            brick_box(g,(x,y,(z-.11)/2),(.16,.30,z-.11))
            prism(g,(x,y,z),.11,.15,CRUSHER_STEEL,'Y',8)
            prism(g,(x,y,z),.035,.32,IRON,'Y',6)
            for yy in (y-.12,y+.12):
                open_box(g,(x,yy,z-.07),(.15,.08,.12),IRON,('-z',))
    # Flywheel behind the drum's rear journal, which rests on a brick drive
    # pedestal and an iron bearing block.
    wy=1.92
    drive=Geometry('Mixer.Drive',(cx,wy,cz))
    wheel(drive,(cx,wy,cz),.30,'Y')
    prism(drive,(cx,wy-.04,cz),.06,.12,IRON,'Y',10)
    parts.append((drive,'Y',2))
    brick_box(g,(cx,1.80,.295),(.30,.12,.59))
    open_box(g,(cx,1.80,.705),(.20,.10,.23),IRON,('-z',))


def chute(g, start, end, width):
    g.beam(start,end,width,.065,IRON)
    # Side flanges are perpendicular to the flow, including sideways chutes.
    length=math.hypot(end[0]-start[0],end[1]-start[1])
    nx,ny=-(end[1]-start[1])/length,(end[0]-start[0])/length
    for side in (-1,1):
        dx,dy=nx*side*width/2,ny*side*width/2
        g.beam((start[0]+dx,start[1]+dy,start[2]+.10),
               (end[0]+dx,end[1]+dy,end[2]+.10),.055,.21,IRON)


def tank(g):
    # Native header tank on the roof's front-left cell on an iron bearing
    # plate, the riser climbing the west wall from the ground inlet (cell
    # (0,1,0), face Left); the feed runs inside the room and leaves its east
    # wall into the drum's rear journal.
    brick_box(g,(.55,.58,ROOF_TOP+.12),(.62,.62,.24))
    open_box(g,(.55,.58,ROOF_TOP+.265),(.56,.56,.05),IRON,('-z',))
    water_barrel(g,'MixerHeaderTank',(.55,.58,ROOF_TOP+.29),.46)
    round_pipe(g,[(2.0,1.95,1.45),(2.50,1.95,1.45),(2.50,1.95,1.20)],.045)
    band(g,(2.24,1.95,1.45),.08,.03,.07,BRASS,'X',8)
    round_pipe(g,[(.05,1.50,.40),(.05,1.50,2.20),(.05,.70,2.20),(.24,.70,2.20)],.05)
    band(g,(.05,1.50,1.00),.09,.03,.08,BRASS,'Z',8)
    wheel(g,(.05,1.50,.62),.10,'X')


def tray(g):
    # The drum's mouth pours down a chute into the wet trough set in a brick
    # base in the front-right cell (no loose bin on an open cell).
    brick_box(g,(2.50,.32,.225),(.88,.56,.45))
    chute(g,(2.50,.64,.86),(2.50,.44,.64),.30)
    for y in (.08,.56):g.box((2.50,y,.53),(.80,.06,.16),PLANK)
    for x in (2.13,2.87):g.box((x,.32,.53),(.06,.42,.16),PLANK)
    open_box(g,(2.50,.32,.49),(.68,.42,.04),KILN_CEMENT,('-z',))
    for i in range(4):
        rock(g,(2.32+(i%2)*.34,.22+(i//2)*.20,.525),(.15,.12,.04),KILN_DUST,1000+i)


def mixer(g, parts):
    # No gallery or balconies: the assembly stays empty (no rail runs).
    rails=RailAssembly('MixerRails')
    operator_room(g)
    drum(g,parts)
    tank(g)
    tray(g)
    return rails
