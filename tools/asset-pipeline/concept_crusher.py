"""Stone crusher, directly composed from approved concrete concept sheet.

3 x 3 x 4, front entrance at x=.5. The two shafts run front-to-back, as
shown in the sheet's plan, rather than across the generic first draft.
"""
import math
import random
from frontier_architecture import *

def structural_post(g,x,y,top):
    g.box((x,y,(top+.25)/2),(.22,.23,top-.25),WOOD)
    for z in (.39,1.48,top-.12):
        g.box((x,y,z),(.265,.275,.21),IRON)
        for dx in (-.073,.073):g.rivet((x+dx,y-.145,z),r=.026)
        g.rivet((x-.145,y,z),'X',.026)

def plank_roof(g,x0,y0,x1,y1,z0,z1):
    # Low-pitch roof panels slope towards the front; shallow ribs and patch plates.
    count=math.ceil((x1-x0)/.19)
    for i in range(count):
        x=x0+(i+.5)*(x1-x0)/count
        g.beam((x,y0,z0),(x,y1,z1),(x1-x0)/count-.012,.052,ROOF)
        for t in (.10,.90):g.rivet((x,y0+(y1-y0)*t,z0+(z1-z0)*t+.034),'Z',.015)
    for x in (x0,x1):g.beam((x,y0,z0-.055),(x,y1,z1-.055),.11,.12,WOOD)
    for y,z in ((y0,z0),(y1,z1)):
        g.beam((x0,y,z-.05),(x1,y,z-.05),.14,.14,WOOD)
        for x in (x0+.07,x1-.07):g.box((x,y,z-.025),(.20,.18,.15),IRON);g.rivet((x,y-.101,z-.025),r=.025)

def hopper(g):
    # Sloped funnel walls, open mouth, separate structural rim and individual boards.
    x0,x1,y0,y1=.20,1.35,1.38,2.80
    bx0,bx1,by0,by1=.45,1.18,1.66,2.50
    bottom,top=2.75,3.48
    g.add([(bx0,by0,bottom),(bx1,by0,bottom),(bx1,by1,bottom),(bx0,by1,bottom),
           (x0,y0,top),(x1,y0,top),(x1,y1,top),(x0,y1,top)],
          [(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],IRON)
    for row in range(4):
        t=(row+.5)/4;xx0=bx0+(x0-bx0)*t;xx1=bx1+(x1-bx1)*t
        yy0=by0+(y0-by0)*t;yy1=by1+(y1-by1)*t;z=bottom+(top-bottom)*t
        for y in (yy0,yy1):g.box(((xx0+xx1)/2,y,z),(xx1-xx0+.07,.075,.17),PLANK)
        for x in (xx0,xx1):g.box((x,(yy0+yy1)/2,z),(.075,yy1-yy0,.17),PLANK)
    for x,y in ((x0,y0),(x1,y0),(x0,y1),(x1,y1)):
        g.box((x,y,top-.10),(.16,.16,.32),IRON)
        for z in (top-.20,top):g.rivet((x,y-.09,z),r=.026)
    for y in (y0,y1):g.box(((x0+x1)/2,y,top), (x1-x0+.16,.16,.13),WOOD)
    for x in (x0,x1):g.box((x,(y0+y1)/2,top),(.13,y1-y0,.13),WOOD)
    rng=random.Random(482)
    for i in range(34):
        x=rng.uniform(x0+.15,x1-.15);y=rng.uniform(y0+.15,y1-.15)
        s=rng.uniform(.15,.27)
        g.rock((x,y,3.32+rng.uniform(0,.12)),(s,s*.86,s*.80),SAND,i)
    # Short feed throat slopes from the hopper to the roller nip.
    for y in (1.67,2.49):g.beam((1.16,y,2.81),(1.77,y,2.38),.04,.13,IRON)
    g.beam((1.17,2.08,2.72),(1.77,2.08,2.29),.78,.045,IRON)

def crusher_drum(g,p,r,length,phase):
    x,y,z=p
    g.cylinder(p,r,length,IRON,'Y',32)
    for row in range(7):
        yy=y-length*.43+row*length*.86/6
        g.ring((x,yy,z),r+.015,.035,.075,IRON,'Y',24)
        for i in range(12):
            a=(i+phase+row*.5)*2*math.pi/12
            a0=(x+math.cos(a)*(r-.015),yy,z+math.sin(a)*(r-.015))
            a1=(x+math.cos(a)*(r+.084),yy,z+math.sin(a)*(r+.084))
            g.beam(a0,a1,.095,.105,GREY)
    for yy in (y-length/2-.025,y+length/2+.025):
        g.cylinder((x,yy,z),r*.83,.055,IRON,'Y',24)
        g.ring((x,yy-.031,z),r*.69,.035,.025,BRASS,'Y')
        for i in range(8):
            a=i*math.pi/4;g.rivet((x+math.cos(a)*r*.62,yy-.055,z+math.sin(a)*r*.62),'Y',.020)
    g.cylinder(p,.085,length+.35,IRON,'Y',16)

def bearing(g,x,y,z):
    g.box((x,y,z-.18),(.37,.26,.13),IRON)
    g.cylinder((x,y,z),.155,.22,BRASS,'Y',16)
    g.ring((x,y-.12,z),.17,.035,.04,IRON,'Y',16)
    for dx in (-.14,.14):g.rivet((x+dx,y,z-.10),'Z',.026)

def lamp(g,x,y,z):
    g.beam((x,y+.05,z+.12),(x,y-.12,z+.12),.03,mat=IRON)
    g.cylinder((x,y-.12,z-.05),.055,.17,SAND,'Z',8)
    for zz in (z-.15,z+.05):g.cylinder((x,y-.12,zz),.075,.025,IRON,'Z',8)
    for dx,dy in ((-.047,-.047),(-.047,.047),(.047,-.047),(.047,.047)):
        g.beam((x+dx,y-.12+dy,z-.15),(x+dx,y-.12+dy,z+.05),.012,mat=IRON)

def crusher(g,parts):
    deck(g,.065,.065,2.935,2.935)
    for x in (.17,2.81):
        for y in (1.04,2.80):structural_post(g,x,y,3.53 if y>2 else 1.72)
    for x in (.17,1.20,2.81):
        for z in (.38,1.48):g.beam((x,1.02,z),(x,2.80,z),.18,.20,WOOD)
    for y in (1.04,2.80):
        for z in (.40,1.48):g.beam((.17,y,z),(2.81,y,z),.20,.20,WOOD)
    structural_post(g,.20,1.40,3.50)
    g.beam((.20,1.40,2.71),(1.35,1.40,2.71),.18,.18,WOOD)
    g.beam((.20,2.80,2.71),(1.35,2.80,2.71),.18,.18,WOOD)
    # Lower enclosed operator/workshop bay, open roller floor above.
    wall(g,.18,2.77,2.80,1.39,.28)
    for x in (.18,1.12):
        for i in range(12):g.box((x,.56+i*.18,.83),(.075,.17,1.10),PLANK)
    wall(g,.16,.45,1.14,1.39,.27)
    door(g,.53,.395,.26)
    plank_roof(g,.09,.19,1.15,.91,1.18,1.43)
    lamp(g,.98,.34,1.03)
    for x in (.19,2.80):
        g.beam((x,1.12,.48),(x,2.58,1.40),.12,mat=WOOD)
        g.beam((x,1.44,1.58),(x,2.75,3.28),.11,mat=WOOD)
    # Roller floor and bearing crossmembers. No wall hides the machine.
    deck(g,1.15,.80,2.89,1.08,1.51)
    deck(g,1.15,2.55,2.89,2.78,1.51)
    for y in (1.01,2.58):g.box((1.99,y,1.77),(1.71,.23,.24),WOOD)
    for i,x in enumerate((1.55,2.25)):
        p=(x,1.82,2.14);m=Geometry('CrusherRoller'+str(i+1),p)
        crusher_drum(m,p,.263,1.45,i*.5);parts.append((m,'Y',1 if i==0 else -1))
        for y in (.98,2.66):bearing(g,x,y,2.14)
    # Large front-left flywheel, compact reduction gear and visible shaft bearings.
    p=(.63,1.05,2.15);m=Geometry('CrusherFlywheel',p)
    m.wheel(p,.51,'Y');m.ring(p,.515,.07,.13,IRON,'Y',32)
    for i in range(12):
        a=i*math.pi/6;m.rivet((p[0]+math.cos(a)*.45,p[1]-.08,p[2]+math.sin(a)*.45),'Y',.022)
    m.cylinder((.63,.92,2.15),.13,.24,BRASS,'Y',16)
    parts.append((m,'Y',1))
    bearing(g,.63,.81,2.15)
    g.beam((.26,.81,1.51),(.26,.81,1.97),.16,mat=WOOD)
    g.beam((1.0,.81,1.51),(1.0,.81,1.97),.16,mat=WOOD)
    g.box((.63,.81,1.84),(.90,.24,.15),WOOD)
    # Driven shaft between wheel and left roller, enclosed chain at its rear.
    for x in (.63,1.55):
        g.cylinder((x,1.11,2.14),.18,.09,IRON,'Y',20)
    for z in (1.97,2.31):g.beam((.63,1.11,z),(1.55,1.11,z),.045,mat=IRON)
    hopper(g)
    # Separate small rear-right shelter and hopper's rear rain cap.
    for x in (1.43,2.80):structural_post(g,x,2.77,3.67)
    g.beam((1.43,1.90,3.34),(1.43,2.77,3.61),.14,mat=WOOD)
    g.beam((2.80,1.90,3.34),(2.80,2.77,3.61),.14,mat=WOOD)
    for x in (1.43,2.80):g.beam((x,2.77,2.83),(x,2.15,3.43),.10,mat=WOOD)
    plank_roof(g,1.37,1.80,2.88,2.88,3.45,3.77)
    plank_roof(g,.17,2.48,1.40,2.88,3.69,3.88)
    # Walkway, knee rail, ladder and dense bolted framing around the mechanism.
    deck(g,2.67,1.16,2.92,2.71,1.51)
    rail(g,(2.87,1.16),(2.87,2.69),1.60)
    ladder(g,1.12,.60,.28,1.25,.28)
    # Aggregate discharge chute: sloped tray with side walls, terminating over bin.
    g.beam((1.95,1.28,1.78),(2.24,.62,.91),.63,.055,IRON)
    for x in (1.63,2.27):g.beam((x,1.28,1.84),(x+.29,.62,.97),.04,.17,IRON)
    bin(g,(2.17,.45,.24),(1.25,.64,.55),GREY,335)
    for x in (1.59,2.75):
        g.plate((x,.135,.49),(.13,.07,.55))
    # Two explicit native power connection housings at ground-level side faces.
    for x in (.12,2.88):
        g.cylinder((x,1.50,.52),.15,.14,IRON,'X',16)
        g.ring((x,1.50,.52),.17,.035,.08,BRASS,'X',16)
    # Small maintenance access details are visual architecture, no upkeep mechanic.
    for i in range(3):g.box((1.34,2.77,.58+i*.18),(.29,.08,.14),IRON)
