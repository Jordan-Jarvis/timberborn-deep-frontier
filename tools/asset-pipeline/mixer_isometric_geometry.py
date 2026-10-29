"""Concrete mixer from the production sheet's right-hand isometric view.

The feed tower, exposed drum and independent tank determine the architecture.
Whole-height decks are authored here; registration must follow this artwork.
No reference top view or printed footprint is used.
"""
import math
import random

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS, deck, facade_panel
from industrial_geometry import timber_column, beam_joint, bracket, steel_bolt, sheet_roof
from industrial_facades import side_window, window_y, gauge
from industrial_door_components import recipe as door_recipe
from reference_details import machinery_shell, round_pipe, cage_lamp
from industrial_kit import (open_beam,lean_wheel as wheel,lean_gauge as gauge,bracket as nutted_bracket,timber_column as nutted_column)
from industrial_kit import (lean_timber_column as timber_column,lean_beam_joint as beam_joint,lean_bracket as bracket,steel_bolt,lean_sheet_roof as sheet_roof,lean_machinery_shell as machinery_shell,round_pipe,lean_cage_lamp as cage_lamp,band,prism,bolt,square_nut,open_box,lean_rock as rock)
from reference_materials import (
    CRUSHER_STEEL, KILN_CEMENT, KILN_DUST, KILN_SOOT,
    CIVIC_CONCRETE, CIVIC_FORGED_PANEL,
)
from native_building_assets import barrel, water_barrel
from walkway_geometry import RailAssembly
from factory_registration import machine_slab

DECK = 2
# Native grid XY (layout origin 0). The operator door is centred on tile
# column 1 with its face 0.12 behind the y=0 edge; the native entrance is the
# path cell in front of it, (1,-1,0), and the door cell is the doorstep.
DOOR_X, DOOR_FACE, WALL_FRONT = 1.50, .12, .16
ROOM_W, ROOM_E, ROOM_REAR = .10, 2.8275, 4.0
ACCESS = {
    "groundDoor": [DOOR_X, DOOR_FACE, 0],
    "decks": "None: the machine is not walked on at upper levels",
}


def pier(g, x, y, top, collar=bracket, column=timber_column):
    g.box((x, y, .15), (.40, .40, .30), CIVIC_CONCRETE)
    column(g, x, y, .29, top, .24)
    for z in (1.15, 2.15, 3.15, 4.15):
        if z < top - .3:
            collar(g, x, y, z, .24)


def hopper(g, x, y, bottom, width, length, material, seed, *, powder=False):
    """Open plank-lined bin, tapered steel throat and individually piled input."""
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
            # The full collar, nuts included: its heads count towards the
            # tower's registered wall faces (industrial_wall_faces.py).
            nutted_bracket(g, xx, yy, top-.15, .18)
    for yy in (y-length/2, y+length/2):
        g.box((x, yy, top), (width-.15, .15, .12), WOOD)
        for xx in (x-width*.30, x+width*.30):
            g.box((xx, yy-.05, bottom+.40), (.06, .035, .67), IRON)
    verts = [(x+dx*width/2, y+dy*length/2, bottom)
             for dx,dy in ((-1,-1),(1,-1),(1,1),(-1,1))]
    verts += [(x+dx*.25, y+dy*.24, bottom-.50)
              for dx,dy in ((-1,-1),(1,-1),(1,1),(-1,1))]
    g.add(verts, [(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)], IRON)
    g.box((x, y, bottom+.53), (width-.13,length-.13,.15), material)
    rng = random.Random(seed)
    if powder:
        vertices=[]
        for row in range(4):
            for col in range(5):
                u=col/4*2-1;v=row/3*2-1
                vertices.append((x+u*(width-.15)/2,y+v*(length-.15)/2,
                                 bottom+.60+.28*(1-u*u)*(1-v*v)+rng.uniform(-.015,.015)))
        g.add(vertices,[(r*5+c,r*5+c+1,(r+1)*5+c+1,(r+1)*5+c)
                        for r in range(3) for c in range(4)],material)
    else:
        # 12k cap: twelve large stones (was thirty).
        for row in range(3):
            for col in range(4):
                xx=x-width*.33+col*width*.22+rng.uniform(-.055,.055)
                yy=y-length*.30+row*length*.30+rng.uniform(-.05,.05)
                size=rng.uniform(.30,.44)
                rock(g,(xx,yy,bottom+.66+rng.uniform(-.025,.12)),
                     (size,size*.82,size*.64),material,seed+row*6+col)
    # Screw-operated slide gate and inspection plate below the throat.
    g.box((x,y-.29,bottom-.35),(.65,.08,.24),IRON)
    prism(g,(x,y-.43,bottom-.35),.035,.30,BRASS,'Y',6)
    wheel(g,(x,y-.60,bottom-.35),.16,'Y')


def operator_room(g):
    # Door at ground, canopy top at layer one, accessible gallery at layer two.
    # The enclosed room fills grid cells x 0..2, y 0..3: its west wall face is
    # 0.10 inside the x=0 tile edge (the corner piers stand in it as pilasters)
    # and its rear wall face is on the y=4 edge, facing the bays under the
    # left walk and the feed tower.
    w,e,rear=ROOM_W,ROOM_E,ROOM_REAR
    for x in (w+.10,2.80):
        pier(g,x,1.15,DECK-.08)
        pier(g,x,rear-.22,DECK-.08)
    for x,positive in ((w,False),(e,True)):
        for j in range(18):
            a=1.15+j*(rear-1.15)/18;b=1.15+(j+1)*(rear-1.15)/18
            facade_panel(g,'X',x,a,b,0,1.86,positive,PLANK)
    for x in (w+.04,2.79):g.box((x,(1.165+rear-.015)/2,.28),(.10,rear-1.18,.35),CIVIC_CONCRETE)
    for j in range(17):
        a=w+j*(e-w)/17;b=w+(j+1)*(e-w)/17
        facade_panel(g,'Y',rear,a,b,0,1.86,True,PLANK)
    # Entry sits in the front of the fully enclosed vestibule; no modelled
    # interior. The plank wall's front face is WALL_FRONT.
    for a,b in ((w+.005,DOOR_X-.5),(DOOR_X+.5,2.84)):
        for i in range(5):
            x=a+(i+.5)*(b-a)/5
            g.box((x,WALL_FRONT+.04,.5425),((b-a)/5,.08,1.075),PLANK)
    g.include_component(door_recipe('ConcreteMixer','Door.MixerOperatorDoor'))
    g.doorways.append({"name":"MixerOperatorDoor","position":[DOOR_X,DOOR_FACE,0]})
    # The porch, upper clerestory and machine-floor roof are one closed room.
    # The former clerestory windows had no wall and the feed tower looked
    # straight through the operator room's missing ceiling.
    facade_panel(g,'Y',1.15,w,e,1.08,1.86,False,PLANK)
    for x,positive in ((w,False),(e,True)):
        facade_panel(g,'X',x,WALL_FRONT,1.17,0,1.08,positive,PLANK)
    # Concrete roof slab over the closed room (formerly under the gallery).
    machine_slab(g,w,1.15,e,rear,1.96,.10)
    # Canopy eave and corner shoes stay inside the tile edges. The front
    # walk's corner piers carry it; lamps hang on the clerestory.
    # Its corner collars close the registered front connection faces.
    sheet_roof(g,.36,.11,2.93,1.15,.94,1.15,910,corner_collars=True)
    for x in (.48,2.80):timber_column(g,x,.20,.03,.93,.16)
    for x in (.55,1.23):cage_lamp(g,x,1.195,1.62)
    # High clerestory panes sit above the entry canopy.
    for x in (.82,1.64,2.46):
        window_y(g,x,1.15,1.55,0.7)
    for y in (2.07,3.39):
        side_window(g,w,y,1.16,0.9,'left')
    window_y(g,(w+e)/2,rear,1.15,1,'back')
    round_pipe(g,[(2.91,1.20,.28),(2.91,1.20,1.66),
                  (2.91,3.74,1.66),(3.20,3.74,1.66)],.052)
    g.box((2.05,1.09,1.48),(.36,.12,.43),CIVIC_FORGED_PANEL)
    gauge(g,2.05,1.01,1.50,.105)


def drum(g, parts):
    p=(4.40,3.30,3.19)
    m=Geometry('Mixer.Drum',p)
    # 12k cap: 16-sided shell; eight wear bars on its ridges (no hex heads).
    machinery_shell(m,p,[(-1.23,.27),(-1.05,.46),(-.78,.79),
                         (-.52,1.03),(.63,1.03),(.98,.73),(1.23,.29)],'Y',16)
    for yy in (2.80,3.90):
        band(m,(4.40,yy,3.19),1.065,.055,.14,CRUSHER_STEEL,'Y',16)
    for i in range(8):
        a=i*math.pi/4
        xx=4.40+math.cos(a)*1.043
        zz=3.19+math.sin(a)*1.043
        m.beam((xx,2.80,zz),(xx,3.91,zz),.033,.022,IRON)
    prism(m,(4.40,2.02,3.19),.19,.32,IRON,'Y',10)
    band(m,(4.40,2.00,3.19),.36,.08,.13,BRASS,'Y',12,inner=True)
    parts.append((m,'Y',1))
    for x in (3.48,5.57):
        for y in (2.35,4.26):
            pier(g,x,y,2.52)
        beam_joint(g,(x,2.30,2.50),(x,4.35,2.50),.22,.24)
        g.beam((x,2.35,1.02),(x,4.20,2.45),.18,mat=WOOD)
    for yy in (2.79,3.91):
        beam_joint(g,(3.17,yy,2.30),(5.64,yy,2.30),.25,.25)
        for xx in (3.66,5.14):
            g.box((xx,yy,2.37),(.43,.35,.22),IRON)
            prism(g,(xx,yy,2.57),.21,.28,CRUSHER_STEEL,'Y',8)
    # Independent keyed power shaft, flywheel, motor and lower crank.
    drive=Geometry('Mixer.Drive',(4.40,1.77,3.19))
    wheel(drive,(4.40,1.77,3.19),.51,'Y')
    prism(drive,(4.40,1.77,3.19),.105,.54,IRON,'Y',10)
    parts.append((drive,'Y',2))
    g.box((4.40,1.89,2.57),(1.18,.65,.18),WOOD)
    for x in (3.97,4.83):
        g.beam((x,2.40,2.01),(x,1.86,2.57),.14,mat=WOOD)
        g.box((x,1.89,2.73),(.18,.40,.19),IRON)
    g.box((3.38,3.44,1.16),(.55,1.15,.65),CIVIC_FORGED_PANEL)
    for y in (3.03,3.15,3.27,3.39,3.51,3.63,3.75,3.87):
        g.box((3.08,y,1.15),(.04,.034,.43),IRON)
    prism(g,(3.38,2.74,1.16),.19,.30,IRON,'Y',8)
    band(g,(3.38,2.55,1.16),.20,.04,.07,CRUSHER_STEEL,'Y',8,inner=True)


def chute(g, start, end, width):
    g.beam(start,end,width,.065,IRON)
    # Side flanges are perpendicular to the flow, including sideways chutes.
    length=math.hypot(end[0]-start[0],end[1]-start[1])
    nx,ny=-(end[1]-start[1])/length,(end[0]-start[0])/length
    for side in (-1,1):
        dx,dy=nx*side*width/2,ny*side*width/2
        g.beam((start[0]+dx,start[1]+dy,start[2]+.09),
               (end[0]+dx,end[1]+dy,end[2]+.09),.055,.21,IRON)


def mixer(g, parts):
    # No gallery or balconies: the drum, feed tower, hoppers and header tank
    # stand on their own concrete piers and timber frames. The assembly stays
    # empty (no rail manifest runs).
    rails=RailAssembly('MixerRails')
    operator_room(g)
    # Feed tower: open equipment bays with a low roof behind the loaded bins.
    # Its rear piers stand inside grid row 4, clear of the bay under the rear
    # walk; the roof keeps its rear overhang above that walk.
    for x in (1.23,2.97):
        for y in (2.15,4.80):
            # The front-right pier keeps its collar nuts: their heads complete
            # the registered wall face of cell (2,2,4) (industrial_wall_faces.py).
            pier(g,x,y,5.10 if y<3 else 5.70,nutted_bracket if (x,y)==(2.97,2.15) else bracket)
        beam_joint(g,(x,2.15,3.17),(x,4.80,3.17),.20,.22)
        g.beam((x,2.20,2.25),(x,4.70,4.70),.18,mat=WOOD)
    for y,z in ((2.15,5.10),(4.80,5.70)):
        beam_joint(g,(1.23,y,z),(2.97,y,z),.22,.24)
    # Footprint ends at y=5 and x=7 (2026-10-22): the feed-tower roof, the
    # cement hopper and the header-tank tower stay inside those tile edges.
    sheet_roof(g,1.03,3.95,3.20,4.98,5.47,5.81,919)
    sheet_roof(g,1.03,3.18,1.92,3.69,5.10,5.32,920)
    hopper(g,2.03,3.12,4.01,1.65,1.55,CIVIC_CONCRETE,930)
    hopper(g,3.87,4.37,4.30,1.55,1.25,KILN_CEMENT,970,powder=True)
    # Cement hopper legs, under the hopper's front and rear thirds.
    for x in (4.02,4.57):
        for y in (4.18,4.60):
            # The rear right leg keeps its post-collar nuts: their heads keep
            # cell (4,4,4)'s Right face out of the registered connection faces.
            pier(g,x,y,4.26,column=nutted_column if (x,y)==(4.57,4.60) else timber_column)
    chute(g,(2.10,3.24,3.53),(3.38,3.24,3.25),.49)
    chute(g,(3.90,4.37,3.81),(4.40,4.20,3.54),.52)
    drum(g,parts)
    # Independent native tank and flanged drop line, as in the reference.
    # Tower piers stand inside grid column 6, clear of the right walk.
    for x in (6.18,6.80):
        for y in (3.80,4.80):
            pier(g,x,y,4.20)
        g.beam((x,3.83,2.25),(x,4.77,3.97),.15,mat=WOOD)
    # The header tank (the mixer's water reservoir display) and its deck end
    # on the x=7 tile edge.
    deck(g,6.0,3.62,7.0,5.0,4.17)
    water_barrel(g,'MixerHeaderTank',(6.49,4.33,4.25),1.02)
    round_pipe(g,[(6.02,4.10,4.86),(5.84,4.10,4.86),
                  (5.78,4.10,4.70),(5.78,4.10,3.85),
                  (5.60,4.10,3.67),(5.03,4.10,3.67)],.075)
    for z in (4.02,4.58):
        band(g,(5.78,4.10,z),.11,.035,.09,BRASS,'Z',8)
    gauge(g,5.80,3.98,4.16,.13)
    wheel(g,(5.78,3.85,4.48),.18,'Y')
    # The riser drops inside the tank tower (row 4), clear of the rear lane.
    round_pipe(g,[(6.49,4.83,4.45),(6.49,4.91,4.45),
                  (6.49,4.91,.40)],.078)
    band(g,(6.49,4.91,.40),.145,.040,.10,IRON,'Z',8)
    # Sloped discharge and a removable wet tray (the stacked finished blocks
    # were loose props and were removed, 2026-10-22).
    chute(g,(5.25,2.73,2.70),(6.15,.69,.88),.74)
    for x in (5.59,6.78):
        for y in (.22,1.34):
            pier(g,x,y,.81)
    g.box((6.20,.79,.69),(1.40,1.30,.15),IRON)
    for y in (.17,1.42):
        g.box((6.20,y,.89),(1.27,.13,.35),PLANK)
    for x in (5.50,6.90):
        g.box((x,.79,.89),(.13,1.30,.35),PLANK)
    g.box((6.20,.79,.86),(1.20,1.09,.14),KILN_CEMENT)
    for i in range(4):
        rock(g,(5.82+(i%2)*.70,.42+(i//2)*.62,.96),(.26,.21,.05),KILN_DUST,1000+i)
    for x,y,z in ((1.22,2.11,3.08),(2.98,2.11,4.79)):
        cage_lamp(g,x,y,z)
    # Low-level utilities and control cabinet add detail without occupying walks.
    round_pipe(g,[(3.00,3.55,.40),(4.60,3.55,.40),(4.60,3.55,1.44),
                  (5.86,3.55,1.44),(5.86,4.93,1.44)],.055)
    g.box((6.02,3.63,2.48),(.44,.20,.57),CIVIC_FORGED_PANEL)
    gauge(g,6.02,3.50,2.55,.105)
    for x in (5.89,6.02,6.15):
        prism(g,(x,3.50,2.29),.027,.04,BRASS,'Y',6,(True,False))
    return rails
