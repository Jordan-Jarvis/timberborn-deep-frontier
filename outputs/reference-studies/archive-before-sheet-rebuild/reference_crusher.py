"""Standalone reference-matched crusher. Art dimensions are not tile counts.

The concrete concept sheet is authoritative. This study deliberately does not
read building blueprints, resize geometry, export a package, or change gameplay.
"""
import math
import random
from frontier_architecture import *
from concept_crusher import plank_roof, crusher_drum, bearing, lamp

def shoe(g,x,y,z,w=.24):
    # Folded iron shoes cover the timber ends; individual faces and bolts remain legible.
    g.box((x,y,z),(w+.055,w+.055,.035),IRON)
    for xx in (x-w/2-.014,x+w/2+.014):
        g.box((xx,y,z+.11),(.028,w+.025,.24),IRON)
        for yy in (y-w*.28,y+w*.28):g.rivet((xx,yy,z+.14),'X',.022)
    for yy in (y-w/2-.014,y+w/2+.014):
        g.box((x,yy,z+.11),(w+.025,.028,.24),IRON)
        for xx in (x-w*.28,x+w*.28):g.rivet((xx,yy-.018,z+.14),'Y',.022)

def column(g,x,y,bottom,top,w=.23):
    g.box((x,y,(bottom+top)/2),(w,w,top-bottom),WOOD)
    shoe(g,x,y,bottom,w)
    shoe(g,x,y,top-.23,w)

def trimmed_beam(g,a,b,w=.19):
    g.beam(a,b,w,mat=WOOD)
    # Joinery faces are separate plates rather than huge metal cubes.
    for p in (a,b):
        g.plate((p[0],p[1]-.102,p[2]),(.25,.035,.25))

def roof(g,x0,y0,x1,y1,z0,z1,seed):
    plank_roof(g,x0,y0,x1,y1,z0,z1)
    rng=random.Random(seed)
    # Thin raised seams, repair strips and exposed paint chips, aligned to panels.
    count=math.ceil((x1-x0)/.19)
    for i in range(count+1):
        x=x0+i*(x1-x0)/count
        g.beam((x,y0+.04,z0+.03),(x,y1-.04,z1+.03),.014,.014,IRON)
    for i in range(19):
        x=rng.uniform(x0+.08,x1-.08);t=rng.uniform(.07,.90)
        y=y0+(y1-y0)*t;z=z0+(z1-z0)*t+.032
        length=rng.uniform(.035,.14)
        g.beam((x,y,z),(x,y+length,z+length*(z1-z0)/(y1-y0)),.012,.004,WOOD)

def feed_hopper(g):
    x0,x1,y0,y1=.39,2.11,1.84,3.53
    bx0,bx1,by0,by1=.58,1.96,2.05,3.35
    bottom,top=2.48,3.18
    corners=[(bx0,by0,bottom),(bx1,by0,bottom),(bx1,by1,bottom),(bx0,by1,bottom),
             (x0,y0,top),(x1,y0,top),(x1,y1,top),(x0,y1,top)]
    g.add(corners,[(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],IRON)
    for row in range(4):
        t=(row+.5)/4;z=bottom+(top-bottom)*t
        a=bx0+(x0-bx0)*t;b=bx1+(x1-bx1)*t;c=by0+(y0-by0)*t;d=by1+(y1-by1)*t
        for y in (c,d):g.box(((a+b)/2,y,z),(b-a+.07,.085,.165),PLANK)
        for x in (a,b):g.box((x,(c+d)/2,z),(.085,d-c,.165),PLANK)
    for x in (x0,x1):g.box((x,(y0+y1)/2,top),(.145,y1-y0+.14,.14),WOOD)
    for y in (y0,y1):g.box(((x0+x1)/2,y,top),(x1-x0,.145,.14),WOOD)
    for x,y in ((x0,y0),(x1,y0),(x0,y1),(x1,y1)):
        shoe(g,x,y,top-.24,.16)
    # A dark filled bed prevents floating stones, topped with several sizes of angular ore.
    g.box((1.25,2.68,2.96),(1.42,1.37,.12),SAND)
    rng=random.Random(830)
    for i in range(47):
        x=rng.uniform(.59,1.92);y=rng.uniform(2.03,3.34);s=rng.uniform(.16,.34)
        g.rock((x,y,3.02+rng.uniform(.00,.12)),(s,s*.84,s*.80),LIME,i+700)
    # A broad downward transfer throat exits the hopper's right wall.
    g.beam((1.90,2.65,2.58),(2.63,2.65,2.27),1.05,.045,IRON)
    for y in (2.12,3.18):g.beam((1.90,y,2.64),(2.63,y,2.33),.04,.16,IRON)

def flywheel(g,p):
    x,y,z=p;r=.66
    g.ring(p,r,.105,.18,IRON,'Y',48)
    g.ring((x,y-.10,z),r-.025,.025,.025,BRASS,'Y',48)
    g.cylinder(p,.16,.31,IRON,'Y',24)
    for i in range(8):
        a=i*math.pi/4
        # Curved, tapered cast spokes meet the substantial outer rim.
        for j in range(3):
            r0=.12+j*.16;r1=r0+.175
            a0=a+j*.055;a1=a+(j+1)*.055
            g.beam((x+math.cos(a0)*r0,y,z+math.sin(a0)*r0),
                   (x+math.cos(a1)*r1,y,z+math.sin(a1)*r1),.095,.105,IRON)
    for i in range(12):
        a=i*math.pi/6;g.rivet((x+math.cos(a)*.605,y-.11,z+math.sin(a)*.605),'Y',.025)
    g.cylinder((x,y-.24,z),.115,.30,BRASS,'Y',12)
    g.cylinder((x,y-.40,z),.085,.035,IRON,'Y',12)

def side_rack(g):
    for z in (.52,.79,1.07):g.box((.47,2.92,z),(.08,1.13,.08),WOOD)
    for y in (2.55,2.83,3.12):
        g.beam((.40,y,.36),(.40,y,1.35),.032,mat=WOOD)
        g.box((.40,y,1.29),(.10,.16,.045),IRON)
    # Visible tool and sorting supplies at the lower rear bay.
    bin(g,(.88,3.15,.25),(.65,.55,.37),None)
    for i in range(5):g.box((.87,3.05+i*.055,.64),(.53,.045,.055),PLANK)

def crusher(g,parts):
    # Compact and broad like the illustration: lower workshop, central machinery,
    # overlapping hopper and short rear shelters. No empty upper storey.
    deck(g,.20,.08,4.67,3.80,.20)
    for x in (.34,2.08,4.48):
        for y in (1.33,3.63):column(g,x,y,.24,1.54)
    for x in (.34,2.08,4.48):
        for z in (.40,1.47):trimmed_beam(g,(x,.94,z),(x,3.63,z),.19)
    for y in (1.33,3.63):trimmed_beam(g,(.34,y,1.47),(4.48,y,1.47),.23)
    # Lower room and individual side boarding with readable, thick sill joints.
    wall(g,.46,3.59,4.37,1.39,.26)
    for i in range(12):g.box((.38,1.05+i*.21,.86),(.08,.20,1.14),PLANK)
    wall(g,.46,.75,2.08,1.38,.26)
    g.beam((.31,1.45,.44),(.31,3.46,1.34),.13,mat=WOOD)
    g.beam((4.49,1.45,.44),(4.49,3.46,1.34),.13,mat=WOOD)
    # Operator porch as a distinct foreground projection, with a deep door recess.
    for x in (1.12,1.91):column(g,x,.51,.23,1.31,.16)
    door(g,1.51,.56,.26)
    roof(g,1.00,.22,2.03,1.07,1.17,1.46,9)
    lamp(g,1.99,.48,1.11)
    g.box((1.52,.21,.24),(.83,.25,.11),PLANK)
    # Lower room viewable below the flywheel; separate wood louvres at front left.
    for i in range(4):g.box((.72,.89,.55+i*.16),(.55,.06,.11),PLANK)
    # Main machine support: bearings are connected to heavy longitudinal rails.
    for x in (2.55,3.38):
        g.box((x,2.15,1.63),(.30,2.20,.22),WOOD)
        for y in (1.10,3.19):
            bearing(g,x,y,1.99)
            shoe(g,x,y,1.48,.28)
    for i,x in enumerate((2.55,3.38)):
        p=(x,2.15,1.99);m=Geometry('ReferenceCrusherRoller'+str(i+1),p)
        crusher_drum(m,p,.335,1.85,i*.5);parts.append((m,'Y',1 if i==0 else -1))
    # Left flywheel prominently overlaps the exposed roller ends.
    p=(1.09,1.18,1.99);m=Geometry('ReferenceCrusherFlywheel',p)
    flywheel(m,p);parts.append((m,'Y',1))
    g.box((1.09,.94,1.66),(.89,.33,.18),WOOD)
    for x in (.73,1.45):column(g,x,.94,.24,1.71,.18)
    bearing(g,1.09,.91,1.99)
    # Shaft / gearbox drive bridge between the flywheel and the twin rollers.
    g.box((1.99,1.27,1.98),(.46,.35,.34),IRON)
    for x in (1.09,2.55):g.cylinder((x,1.39,1.99),.225,.08,IRON,'Y',24)
    for z in (1.78,2.20):g.beam((1.09,1.39,z),(2.55,1.39,z),.04,mat=IRON)
    for x in (1.83,2.14):g.rivet((x,1.08,1.99),'Y',.025)
    # Tall hopper columns and closely fitted roof structure.
    for x in (.40,2.10):
        for y in (1.85,3.54):column(g,x,y,1.50,3.21,.22)
        g.beam((x,1.86,1.63),(x,2.49,2.51),.14,mat=WOOD)
    for y in (1.85,3.54):trimmed_beam(g,(.40,y,2.49),(2.10,y,2.49),.20)
    feed_hopper(g)
    for x in (2.19,4.48):
        for y,z in ((2.20,3.08),(3.65,3.43)):column(g,x,y,1.47,z,.23)
        g.beam((x,2.20,2.63),(x,2.73,3.12),.14,mat=WOOD)
    trimmed_beam(g,(2.19,2.20,3.08),(4.48,2.20,3.08),.20)
    roof(g,2.10,2.08,4.60,3.80,3.16,3.54,44)
    roof(g,.32,3.07,2.21,3.80,3.31,3.55,45)
    # Full right service walkway and timber guardrail, nested around the discharge.
    deck(g,3.91,1.10,4.63,3.57,1.45)
    rail(g,(4.51,1.20),(4.51,3.53),1.55)
    rail(g,(3.99,3.54),(4.51,3.54),1.55)
    ladder(g,2.12,.67,.28,1.22,.30)
    # A coherent discharge tray passes beneath the crushing gap into the output bin.
    g.beam((2.98,1.54,1.66),(3.38,.86,.91),.78,.055,IRON)
    for x in (2.59,3.37):g.beam((x,1.54,1.74),(x+.40,.86,.99),.045,.17,IRON)
    bin(g,(3.58,.56,.23),(1.70,.84,.63),None)
    g.box((3.58,.56,.70),(1.48,.63,.10),GREY)
    rng=random.Random(102)
    for i in range(49):
        s=rng.uniform(.085,.17)
        g.rock((rng.uniform(2.90,4.25),rng.uniform(.29,.84),rng.uniform(.74,.88)),(s,s*.83,s*.72),LIME,2000+i)
    for x in (2.80,4.36):shoe(g,x,.20,.24,.15)
    side_rack(g)
    # Ground-level power housings and visible brackets are located on the side bays.
    for x in (.30,4.57):
        g.cylinder((x,2.10,.55),.15,.14,IRON,'X',20)
        g.ring((x,2.10,.55),.18,.035,.055,BRASS,'X',24)
    for y in (1.62,3.35):g.plate((.26,y,1.49),(.06,.34,.32),'X')
