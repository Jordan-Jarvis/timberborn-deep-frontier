"""Cement kiln and concrete mixer composed from the approved production sheet."""
import math
from frontier_architecture import *
from reference_crusher import column,shoe,trimmed_beam,roof
from reference_details import cask,round_pipe,machinery_shell,cage_lamp
from reference_materials import GLOW

def kiln(g,parts):
    deck(g,.10,.10,5.22,4.25,.20)
    # Long covered hall with a masonry furnace attached to the right-hand end.
    for x in (.30,2.28,4.16):
        for y in (1.29,4.00):column(g,x,y,.25,3.19 if y<2 else 3.73)
        trimmed_beam(g,(x,1.29,1.13),(x,4.00,1.13),.20)
    for y in (1.29,4.00):trimmed_beam(g,(.30,y,1.13),(4.16,y,1.13),.24)
    # Side sorting platform, storage and diagonal framing break up the large bay.
    deck(g,.34,1.34,1.17,3.85,1.08)
    rail(g,(.39,1.47),(.39,3.77),1.16)
    g.beam((.30,1.40,.34),(.30,3.76,1.10),.13,mat=WOOD)
    g.beam((.30,3.76,1.26),(.30,2.31,2.91),.13,mat=WOOD)
    cask(g,(.72,3.51,.25),.29,.65)
    for i in range(4):g.box((.70,2.55,.42+i*.12),(.58,.67,.10),PLANK)
    wall(g,.36,3.96,4.08,3.62,.28)
    for x in (.30,4.16):g.beam((x,1.35,2.57),(x,1.93,3.24),.14,mat=WOOD)
    # Steel barrel panels, raised flanges and paired support rollers.
    p=(2.24,2.15,2.08);m=Geometry('ReferenceKilnBarrel',p)
    machinery_shell(m,p,[(-1.60,.50),(-1.42,.62),(-1.05,.64),(-.48,.64),(.25,.64),(.96,.64),(1.39,.58),(1.61,.40)],'X',32)
    for x in (.98,3.30):m.ring((x,2.15,2.08),.69,.065,.18,BRASS,'X',32)
    parts.append((m,'X',.3))
    for x in (.98,3.30):
        for y in (1.70,2.60):
            g.cylinder((x,y,1.61),.19,.31,IRON,'X',16)
            g.box((x,y,1.38),(.43,.38,.19),WOOD)
        g.box((x,2.15,1.19),(.28,1.65,.19),WOOD)
    # Fuel bay: cut log ends, split timber and an exposed drive wheel.
    for row in range(3):
        for i in range(5-row):
            x=.50+i*.21+row*.07;z=.35+row*.18
            g.cylinder((x,.91,z),.10,.61,WOOD,'Y',12)
            g.cylinder((x,.597,z),.080,.015,PLANK,'Y',12)
            g.ring((x,.584,z),.053,.008,.008,WOOD,'Y',12)
    p=(.52,1.18,1.73);m=Geometry('ReferenceKilnDrive',p);m.wheel(p,.34,'Y');parts.append((m,'Y',.9))
    g.box((.52,1.18,1.35),(.61,.36,.18),WOOD)
    # High rear feed bins emerge from the canopy.
    for x in (.79,1.85):bin(g,(x,3.48,2.81),(.98,1.02,.52),LIME,int(x*100))
    roof(g,.19,1.18,4.31,3.08,3.28,3.69,19)
    roof(g,2.39,3.08,4.31,4.14,3.69,3.77,20)
    # Short louvred monitor sitting on the hall roof.
    for x in (1.94,2.70):g.box((x,2.12,3.67),(.10,.58,.40),WOOD)
    for i in range(4):g.box((2.32,1.82,3.53+i*.08),(.76,.035,.045),IRON)
    roof(g,1.87,1.77,2.77,2.49,3.87,3.97,21)
    # Individual masonry blocks, soot-black fire mouth and iron fire-door bars.
    g.box((4.46,1.96,1.24),(1.11,1.33,1.95),GREY)
    for row in range(7):
        for i in range(4):
            x=4.00+(i+.5)*.24;z=.38+row*.25
            g.box((x,1.275,z),(.228,.11,.231),LIME if (i+row)%4==0 else GREY)
        for i in range(5):g.box((5.04,1.39+i*.24,.38+row*.25),(.10,.225,.231),GREY)
    g.box((4.50,1.20,.99),(.57,.08,.79),IRON)
    g.box((4.50,1.15,.99),(.42,.025,.61),GLOW)
    for x in (4.34,4.45,4.56,4.67):g.box((x,1.12,.99),(.035,.04,.66),IRON)
    for z in (.67,1.30):g.box((4.50,1.10,z),(.53,.06,.065),IRON)
    # Tapered plated chimney with an actual recessed open top.
    for row in range(7):
        z=2.25+row*.25;width=.48-row*.020
        g.box((4.69,2.63,z),(width,width,.25),IRON)
        for dx in (-width*.32,width*.32):g.rivet((4.69+dx,2.63-width/2-.012,z),'Y',.019)
        g.box((4.69,2.63,z+.12),(width+.03,width+.03,.035),GREY)
    for x in (4.49,4.89):g.box((x,2.63,4.02),(.06,.46,.20),IRON)
    for y in (2.43,2.83):g.box((4.69,y,4.02),(.36,.06,.20),IRON)
    # Separate foreground operator entrance and powdered cement collection.
    wall(g,1.62,.72,2.67,1.35,.26);door(g,2.16,.66,.27)
    roof(g,1.53,.23,2.77,1.14,1.20,1.49,22);cage_lamp(g,2.71,.58,1.02)
    bin(g,(4.41,.60,.23),(1.29,.87,.52),None)
    for i in range(19):g.rock((4.00+(i%5)*.18,.36+(i//5)*.14,.72),(.30,.25,.10),LIME,i+810)
    g.beam((4.48,1.19,.78),(4.41,.82,.75),.59,.045,IRON)
    for row in range(7):
        for i in range(5):g.box((3.87,1.40+i*.24,.38+row*.25),(.10,.225,.231),GREY)
    rail(g,(3.86,3.94),(5.06,3.94),.27)

def mixer(g,parts):
    deck(g,.10,.10,4.91,4.15,.20)
    # Tall left ingredients bay, central suspended drum, independent right water tower.
    for x in (.29,2.18):
        for y in (1.39,3.91):column(g,x,y,.25,3.18 if y<2 else 3.73)
        for z in (1.24,2.72):trimmed_beam(g,(x,1.39,z),(x,3.91,z),.20)
        g.beam((x,1.40,1.37),(x,2.34,2.66),.14,mat=WOOD)
    for y in (1.39,3.91):trimmed_beam(g,(.29,y,1.24),(2.18,y,1.24),.22)
    wall(g,.36,3.88,2.12,3.55,.28)
    roof(g,.18,2.66,2.33,4.05,3.43,3.78,31)
    # Ingredient bins are forward of the roof, fully visible like the reference.
    for x,y,z,stone in ((1.18,1.98,2.34,GREY),(2.15,2.90,2.78,LIME)):
        bin(g,(x,y,z),(1.25,1.02,.55),stone,int(x*150))
        for xx in (x-.49,x+.49):
            g.beam((xx,y-.42,1.29),(xx,y-.42,z),.13,mat=WOOD)
    deck(g,.35,1.48,2.10,2.64,1.19)
    rail(g,(.42,1.59),(.42,2.60),1.28)
    ladder(g,.74,1.16,.27,1.03,.31)
    # Deep faceted mixer body with tapered ends, rings and longitudinal raised seams.
    p=(2.86,2.14,1.90);m=Geometry('ReferenceMixingDrum',p)
    profile=[(-1.04,.24),(-.89,.36),(-.67,.65),(-.36,.81),(.56,.81),(.86,.61),(1.05,.29)]
    machinery_shell(m,p,profile,'Y',24)
    for t,r in ((-.84,.40),(-.36,.83),(.56,.83)):
        m.ring((2.86,2.14+t,1.90),r,.04,.10,BRASS if t<-.5 else IRON,'Y',24)
    for i in range(12):
        a=i*math.pi/6
        m.beam((2.86+math.cos(a)*.815,1.78,1.90+math.sin(a)*.815),
               (2.86+math.cos(a)*.815,2.70,1.90+math.sin(a)*.815),.025,mat=IRON)
    parts.append((m,'Y',.45))
    for x in (2.14,3.61):
        for y in (1.35,3.00):column(g,x,y,.24,1.44,.24)
        g.beam((x,1.35,.51),(x,2.92,1.42),.15,mat=WOOD)
        g.box((x,2.16,1.39),(.23,1.92,.19),WOOD)
    for y in (1.37,2.95):g.box((2.86,y,1.28),(1.85,.25,.20),WOOD)
    # Front shaft and small driving flywheel mounted on a projecting timber shelf.
    p=(2.86,.97,1.90);m=Geometry('ReferenceMixerDrive',p);m.wheel(p,.28,'Y');parts.append((m,'Y',.9))
    g.cylinder((2.86,1.10,1.90),.10,.42,IRON,'Y',20)
    g.box((2.86,1.01,1.54),(.73,.38,.19),WOOD)
    for x in (2.57,3.15):g.beam((x,1.40,.94),(x,.99,1.54),.12,mat=WOOD)
    # Water cask and its own bolted support tower; circular pipework wraps the cask.
    for x in (4.02,4.65):
        for y in (2.94,3.58):column(g,x,y,.24,2.90,.20)
        g.beam((x,2.94,1.83),(x,3.58,2.77),.11,mat=WOOD)
    deck(g,3.88,2.80,4.79,3.73,2.81)
    cask(g,(4.34,3.26,2.89),.46,1.15)
    round_pipe(g,[(4.34,2.86,3.94),(4.34,2.68,3.94),(4.34,2.59,3.84),(4.34,2.59,2.62),
                  (4.18,2.59,2.47),(3.43,2.59,2.47),(3.43,2.59,2.34)],.065)
    for z in (2.80,3.54):g.ring((4.34,2.59,z),.085,.026,.065,BRASS,'Z',16)
    # Ingredients throat and right-hand discharge tray connect to the drum.
    g.beam((2.10,3.05,2.83),(2.86,2.98,2.45),.65,.045,IRON)
    g.beam((3.18,1.48,1.49),(3.83,.79,.81),.68,.055,IRON)
    for x in (2.84,3.52):g.beam((x,1.48,1.56),(x+.65,.79,.88),.04,.16,IRON)
    bin(g,(3.93,.56,.23),(1.45,.82,.47),None)
    for i in range(6):g.box((3.47+(i%3)*.30,.40+(i//3)*.28,.64),(.27,.25,.19),GREY)
    # Foreground operator bay and ladder, as shown below the feed frame.
    wall(g,.43,.70,1.89,1.29,.25);door(g,1.19,.64,.26)
    roof(g,.38,.25,1.94,1.17,1.20,1.45,33);cage_lamp(g,1.88,.57,1.00)
    ladder(g,2.00,.80,.27,1.18,.31)
    rail(g,(4.69,1.18),(4.69,2.72),1.32)
    deck(g,4.30,1.12,4.83,2.78,1.25)
    for x in (.45,1.00):cask(g,(x,3.52,.25),.22,.51)
