"""Concrete mixer, compact 4x3 workshop (2026-10-30 compaction pass).

Steam Workshop feedback: the buildings exceeded Timberborn's scale. The user
kept the textures and asked for less scaffolding and size. The 7x5x7 mixer
with its tall timber feed tower, stilted header-tank tower and pier-borne
drum becomes a 4x3x3 workshop with the same parts and materials:

- the closed operator room (grid x 0..1, all three rows) with its door,
  canopy and clerestory, its concrete roof carrying the aggregate and cement
  hoppers, which feed the drum through two short chutes,
- the mixing drum (same profile, 0.62 scale) on four rollers seated on low
  concrete piers, its flywheel on a concrete drive pedestal in front,
- the discharge chute and wet tray in the front-right cell,
- the native header tank on a concrete pedestal in the rear-right cell.

Native grid XY (layout origin 0); outer walls and pedestals sit on the tile
lines x 0..4, y 0..3. No walkways, decks or balconies.
"""
import math
import random

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS, facade_panel
from industrial_facades import side_window, window_y
from industrial_door_components import recipe as door_recipe
from industrial_kit import (open_beam,lean_wheel as wheel,lean_gauge as gauge,bracket as nutted_bracket)
from industrial_kit import (lean_timber_column as timber_column,lean_bracket as bracket,lean_sheet_roof as sheet_roof,lean_machinery_shell as machinery_shell,round_pipe,lean_cage_lamp as cage_lamp,lean_bin as bin,band,prism,open_box,lean_rock as rock)
from reference_materials import (
    CRUSHER_STEEL, KILN_CEMENT, KILN_DUST,
    CIVIC_CONCRETE, CIVIC_FORGED_PANEL,
)
from native_building_assets import water_barrel
from walkway_geometry import RailAssembly
from factory_registration import machine_slab

DECK = 2
# Native grid XY (layout origin 0). The operator door is centred on tile
# column 1 with its face 0.12 behind the y=0 edge; the native entrance is the
# path cell in front of it, (1,-1,0), and the door cell is the doorstep.
DOOR_X, DOOR_FACE, WALL_FRONT = 1.50, .12, .16
# Operator room: west wall 0.10 inside the x=0 edge (corner piers stand in it
# as pilasters), east wall on the x=2 line, rear wall on the y=3 edge. The
# low entry vestibule (y .16..1) carries the canopy; the clerestory face is
# on y=1.
ROOM_W, ROOM_E, ROOM_FRONT, ROOM_REAR = .10, 2.0, 1.0, 3.0
ROOF_TOP = 1.96
# Drum: the original profile and fittings at this scale about its centre.
DRUM = (2.85, 1.45, 1.35)
DRUM_SCALE = .62
ACCESS = {
    "groundDoor": [DOOR_X, DOOR_FACE, 0],
    "decks": "None: the machine is not walked on at upper levels",
}


def pier(g, x, y, top, collar=bracket, column=timber_column):
    g.box((x, y, .15), (.40, .40, .30), CIVIC_CONCRETE)
    column(g, x, y, .29, top, .24)
    for z in (1.15,):
        if z < top - .3:
            collar(g, x, y, z, .24)


def hopper(g, x, y, bottom, width, length, material, seed, *, powder=False):
    """Open plank-lined bin standing on the room's concrete roof, with its
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
            for col in range(5):
                xx=x-width*.38+col*width*.19+rng.uniform(-.04,.04)
                yy=y-length*.22+row*length*.44+rng.uniform(-.04,.04)
                size=rng.uniform(.26,.36)
                rock(g,(xx,yy,bottom+.66+rng.uniform(-.02,.06)),
                     (size,size*.82,size*.64),material,seed+row*6+col)


def operator_room(g):
    # Door at ground, canopy top at layer one, concrete roof at layer two.
    w,e,front,rear=ROOM_W,ROOM_E,ROOM_FRONT,ROOM_REAR
    for x in (w+.10,e-.10):
        pier(g,x,front,DECK-.08)
        pier(g,x,rear-.22,DECK-.08)
    count=13
    for x,positive in ((w,False),(e,True)):
        for j in range(count):
            a=front+j*(rear-front)/count;b=front+(j+1)*(rear-front)/count
            facade_panel(g,'X',x,a,b,0,1.86,positive,PLANK)
    for x in (w+.04,e-.04):g.box((x,(front+.015+rear-.015)/2,.28),(.10,rear-front-.03,.35),CIVIC_CONCRETE)
    count=12
    for j in range(count):
        a=w+j*(e-w)/count;b=w+(j+1)*(e-w)/count
        facade_panel(g,'Y',rear,a,b,0,1.86,True,PLANK)
    # Entry vestibule: plank front wall west of the door, the native door on
    # tile column 1 (its east jamb on the room's east wall). The plank wall's
    # front face is WALL_FRONT.
    a,b=w+.005,DOOR_X-.5
    for i in range(5):
        x=a+(i+.5)*(b-a)/5
        g.box((x,WALL_FRONT+.04,.5425),((b-a)/5,.08,1.075),PLANK)
    g.include_component(door_recipe('ConcreteMixer','Door.MixerOperatorDoor'))
    g.doorways.append({"name":"MixerOperatorDoor","position":[DOOR_X,DOOR_FACE,0]})
    # The vestibule, clerestory and roof slab close one room.
    facade_panel(g,'Y',front,w,e,1.08,1.86,False,PLANK)
    for x,positive in ((w,False),(e,True)):
        facade_panel(g,'X',x,WALL_FRONT,front,0,1.08,positive,PLANK)
    machine_slab(g,w,front,e,rear,ROOF_TOP,.10)
    # Canopy over the vestibule, carried by one front post and the east wall.
    # Its corner collars close the registered front connection faces.
    sheet_roof(g,.36,.11,2.06,front,.94,1.12,910,corner_collars=True)
    timber_column(g,.48,.20,.03,.93,.16)
    for x in (.40,.95):
        window_y(g,x,front,1.30,.6)
    g.box((1.62,front-.06,1.48),(.30,.12,.40),CIVIC_FORGED_PANEL)
    gauge(g,1.62,front-.14,1.50,.095)
    cage_lamp(g,1.27,front+.045,1.66)
    # Side windows only: a casing on the rear wall would stand outside the
    # y=3 edge.
    for y in (1.55,2.45):side_window(g,w,y,1.0,.9,'left')
    # Control cabinet on the east wall, facing the drum.
    g.box((e+.05,2.45,1.05),(.10,.40,.50),CIVIC_FORGED_PANEL)
    for z in (.92,1.18):
        prism(g,(e+.115,2.45,z),.06,.03,BRASS,'X',8,(False,True))
    # Aggregate and cement hoppers on the roof, chutes to the drum.
    hopper(g,1.05,1.55,ROOF_TOP,1.60,.82,CIVIC_CONCRETE,930)
    hopper(g,1.05,2.48,ROOF_TOP,1.50,.72,KILN_CEMENT,970,powder=True)
    chute(g,(1.90,1.50,2.55),(2.55,1.30,2.05),.30)
    chute(g,(1.83,2.48,2.45),(2.62,2.05,1.88),.28)


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
    prism(m,at(0,-1.28,0),.19*s,.32*s,IRON,'Y',10)
    band(m,at(0,-1.30,0),.36*s,.08*s,.13*s,BRASS,'Y',12,inner=True)
    parts.append((m,'Y',1))
    # Rollers under each tyre on low concrete piers clear of the tyre.
    for dy in (-.50,.61):
        y=cy+dy*s
        for side in (-1,1):
            x=cx+side*.55
            g.box((x,y,.3865),(.20,.40,.773),CIVIC_CONCRETE)
            prism(g,(x,y,.933),.13,.17,CRUSHER_STEEL,'Y',8)
            prism(g,(x,y,.933),.04,.38,IRON,'Y',6)
            for yy in (y-.135,y+.135):
                open_box(g,(x,yy,.853),(.18,.09,.16),IRON,('-z',))
    # Flywheel on a concrete drive pedestal in front of the drum mouth.
    drive=Geometry('Mixer.Drive',(cx,.40,cz))
    wheel(drive,(cx,.40,cz),.34,'Y')
    prism(drive,(cx,.45,cz),.07,.45,IRON,'Y',10)
    parts.append((drive,'Y',2))
    # One concrete base under the drive and the wet trough (front row).
    g.box((3.03,.50,.20),(1.86,.84,.40),CIVIC_CONCRETE)
    g.box((cx,.59,.76),(.40,.18,.72),CIVIC_CONCRETE)
    open_box(g,(cx,.59,1.20),(.26,.16,.16),IRON,('-z',))


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
    # Native header tank on a concrete pedestal (rear-right cell), drop line
    # into the drum's rear journal and a riser to the ground inlet.
    g.box((3.55,2.65,.65),(.90,.70,1.30),CIVIC_CONCRETE)
    open_box(g,(3.55,2.65,1.285),(.86,.66,.06),IRON,('-z',))
    water_barrel(g,'MixerHeaderTank',(3.55,2.65,1.315),.62)
    round_pipe(g,[(3.27,2.62,1.62),(2.85,2.62,1.62),(2.85,2.62,1.35),(2.85,2.25,1.35)],.06)
    band(g,(2.85,2.62,1.47),.10,.03,.08,BRASS,'Z',8)
    wheel(g,(3.05,2.50,1.62),.12,'Y')
    round_pipe(g,[(3.80,2.30,1.36),(3.80,2.24,1.36),(3.80,2.24,.40),(3.92,2.24,.40)],.06)
    band(g,(3.80,2.24,.70),.10,.03,.08,BRASS,'Z',8)
    gauge(g,3.35,2.27,.95,.10)
    cage_lamp(g,3.55,2.30,1.08)


def tray(g):
    # Sloped discharge from the drum's side into the wet trough set in the
    # concrete drive base (no loose bin on an open cell, 2026-10-30).
    chute(g,(3.30,.95,1.28),(3.58,.55,.62),.40)
    for y in (.16,.84):g.box((3.58,y,.46),(.74,.07,.12),PLANK)
    for x in (3.24,3.92):g.box((x,.50,.46),(.07,.61,.12),PLANK)
    open_box(g,(3.58,.50,.42),(.61,.61,.04),KILN_CEMENT,('-z',))
    for i in range(4):
        rock(g,(3.43+(i%2)*.30,.36+(i//2)*.28,.455),(.16,.13,.04),KILN_DUST,1000+i)


def mixer(g, parts):
    # No gallery or balconies: the assembly stays empty (no rail runs).
    rails=RailAssembly('MixerRails')
    operator_room(g)
    drum(g,parts)
    tank(g)
    tray(g)
    return rails
