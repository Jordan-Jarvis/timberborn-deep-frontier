"""Four individually composed civic buildings from the approved surface sheet."""
import math
import random
from frontier_architecture import *
from frontier_architecture import roof as pitched_panels
from reference_crusher import column,shoe,trimmed_beam,roof as lean_roof
from reference_details import cask,cage_lamp,steps,round_pipe
from reference_materials import GLOW,GLASS,LEAF,WATER,CLOTH

def glazing(g,x,y,z,w,h,axis='Y',back=True):
    def box(u,v,zz,size,mat):
        p=(x+u,y+v,z+zz) if axis=='Y' else (x+v,y+u,z+zz)
        s=size if axis=='Y' else (size[1],size[0],size[2]);g.box(p,s,mat)
    if back:box(0,0,0,(w+.08,.07,h+.08),IRON)
    box(0,-.046,0,(w-.06,.015,h-.06),GLASS)
    for u in (-w/2,w/2):box(u,-.08,0,(.065,.12,h+.14),WOOD)
    for zz in (-h/2,h/2):box(0,-.08,zz,(w+.13,.12,.065),WOOD)
    for u in (-w*.17,w*.17):box(u,-.09,0,(.032,.09,h),WOOD)
    box(0,-.10,0,(w,.08,.035),WOOD)
    box(0,-.13,-h/2-.06,(w+.21,.23,.065),PLANK)

def side_wall(g,x,y0,y1,z0,z1):
    count=math.ceil((y1-y0)/.17)
    for i in range(count):g.box((x,y0+(i+.5)*(y1-y0)/count,(z0+z1)/2),(.08,(y1-y0)/count-.009,z1-z0),PLANK)

def room(g,x0,y0,x1,y1,levels,open_upper=False):
    deck(g,x0-.11,y0-.10,x1+.11,y1+.10,levels[0]-.05)
    for a,b in zip(levels,levels[1:]):
        wall(g,x0+.08,y1,x1-.08,b-.10,a+.08)
        side_wall(g,x1,y0,y1,a+.08,b-.10)
        if not open_upper or a==levels[0]:
            wall(g,x0+.08,y0,x1-.08,b-.10,a+.08)
            side_wall(g,x0,y0,y1,a+.08,b-.10)
        for y in (y0,y1):trimmed_beam(g,(x0,y,b),(x1,y,b),.19)
        for x in (x0,x1):trimmed_beam(g,(x,y0,b),(x,y1,b),.19)
    for x in (x0,x1):
        for y in (y0,y1):column(g,x,y,levels[0],levels[-1],.22)
    for z in levels[1:-1]:deck(g,x0+.04,y0+.04,x1-.04,y1-.04,z)
    for x in (x0+(x1-x0)/3,x0+2*(x1-x0)/3):column(g,x,y0,levels[0],levels[-1],.16)
    for y in (y0+(y1-y0)/3,y0+2*(y1-y0)/3):column(g,x0,y,levels[0],levels[-1],.16)

def gable(g,x0,y0,x1,y1,eave,ridge):
    pitched_panels(g,x0,y0,x1,y1,eave,ridge)
    middle=(x0+x1)/2
    for y in (y0+.06,y1-.06):
        count=math.ceil((x1-x0)/.16)
        for i in range(count):
            x=x0+(i+.5)*(x1-x0)/count
            top=eave+(ridge-eave)*(1-abs(x-middle)/((x1-x0)/2))
            g.box((x,y,(eave+top)/2),((x1-x0)/count-.01,.075,top-eave+.01),PLANK)
        trimmed_beam(g,(x0,y,eave),(x1,y,eave),.15)
        for x in (x0,x1):
            g.beam((x,y,eave),(middle,y,ridge),.14,.14,WOOD)
            shoe(g,x,y-.02,eave-.10,.20)
    for y in (y0+.12,y1-.12):g.box((middle,y,ridge),(.24,.24,.14),IRON)

def flowers(g,x,y,z,w=.70):
    bin(g,(x,y,z),(w,.29,.22),None)
    for i in range(9):
        xx=x-w*.4+i*w*.1
        g.rock((xx,y,z+.27),(.14,.19,.15),LEAF,900+i)
        for j in range(3):
            a=j*math.pi*2/3;g.rock((xx+math.cos(a)*.035,y+math.sin(a)*.035,z+.36),(.055,.055,.035),LIME,980+i*3+j)

def hanging_sign(g,parts,x,y,z,kind):
    for xx in (x-.27,x+.27):g.beam((xx,y+.24,z+.40),(xx,y-.04,z+.40),.07,mat=WOOD)
    g.beam((x-.37,y,z+.40),(x+.37,y,z+.40),.09,mat=WOOD)
    for xx in (x-.23,x+.23):
        for i in range(3):g.ring((xx,y,z+.29-i*.06),.04,.010,.015,IRON,'Y',10)
    m=Geometry(kind+'HangingSign',(x,y,z+.31))
    m.box((x,y,z-.05),(.74,.085,.65),WOOD)
    m.box((x,y-.052,z-.05),(.65,.025,.55),PLANK)
    q=y-.075
    if kind=='Hospital':
        m.box((x,q,z-.08),(.22,.018,.26),LIME)
        m.box((x,q,z+.09),(.105,.018,.11),LIME)
        m.box((x,q,z+.16),(.16,.018,.045),LIME)
        m.rock((x+.07,q-.01,z-.05),(.15,.025,.09),LEAF,10)
    elif kind=='Restaurant':
        for a,b in [((x-.22,q,z+.03),(x-.13,q,z-.16)),((x-.13,q,z-.16),(x+.13,q,z-.16)),((x+.13,q,z-.16),(x+.22,q,z+.03))]:m.beam(a,b,.035,mat=LIME)
        m.beam((x-.22,q,z+.03),(x+.22,q,z+.03),.032,mat=LIME)
        for xx in (x-.13,x,x+.13):
            m.beam((xx,q,z+.09),(xx-.035,q,z+.16),.021,mat=LIME)
            m.beam((xx-.035,q,z+.16),(xx+.025,q,z+.22),.021,mat=LIME)
    elif kind=='GroceryStore':
        m.box((x,q,z-.11),(.41,.02,.15),LIME)
        m.ring((x,q,z+.01),.20,.025,.018,LIME,'Y',16)
        for xx in (x-.13,x,x+.13):m.rock((xx,q,z+.07),(.14,.03,.15),LIME,20)
    elif kind=='FisheryWorks':
        m.rock((x-.04,q,z),(.43,.035,.19),LIME,10)
        m.add([(x+.11,q-.01,z),(x+.29,q-.01,z+.13),(x+.29,q-.01,z-.13)],[(0,1,2)],LIME)
        m.cylinder((x-.18,q-.025,z+.025),.022,.015,IRON,'Y',8)
    else:raise ValueError(kind)
    parts.append((m,'SWAY',.035))

def hospital(g,parts):
    room(g,.45,1.00,4.75,4.25,[.25,1.75,3.28])
    # Main gable, front cross-gable, dormer and distinct entrance wing.
    gable(g,.25,.84,4.94,4.43,3.37,4.67)
    room(g,.48,.60,2.43,1.47,[.25,1.75,3.27])
    gable(g,.32,.42,2.57,1.88,3.36,4.13)
    glazing(g,1.45,.44,3.64,.51,.55)
    # Dormer on the long left roof slope.
    side_wall(g,.82,2.28,3.03,3.70,4.09)
    wall(g,.81,2.28,1.60,4.08,3.66);glazing(g,1.21,2.23,3.87,.45,.40)
    gable(g,.72,2.14,1.69,3.12,4.10,4.39)
    # Rectangular windows with shutters across both occupied storeys.
    for x in (3.12,4.10):
        for z in (.97,2.51):glazing(g,x,.94,z,.54,.76)
    for y in (1.89,3.06):
        for z in (.97,2.51):glazing(g,.39,y,z,.55,.76,'X')
    glazing(g,1.45,.54,2.51,.56,.76)
    for x in (3.12,4.10):flowers(g,x,.72,1.86,.73)
    # Deep sheltered porch with stairs, plants, lanterns and medicine sign.
    for x in (.91,1.99):column(g,x,.15,.20,1.46,.20)
    door(g,1.45,.50,.28)
    gable(g,.79,.04,2.12,.87,1.49,1.83)
    steps(g,1.45,-.14,1.05,.26,.30)
    cage_lamp(g,.84,.42,1.21);cage_lamp(g,2.12,.42,1.21)
    hanging_sign(g,parts,1.45,.12,2.37,'Hospital')
    for x in (.52,2.42,3.28,4.14):flowers(g,x,.51,.27,.60)
    # Rooftop water/medical supply cask, rear rack and service barrels.
    deck(g,3.84,3.27,4.81,4.23,3.20)
    cask(g,(4.28,3.76,3.29),.42,.80)
    for y in (2.96,3.65):cask(g,(4.99,y,.24),.24,.58)

def dining_table(g,x,y,z):
    g.box((x,y,z),(.65,.53,.065),PLANK)
    for xx in (x-.25,x+.25):
        for yy in (y-.19,y+.19):g.box((xx,yy,z-.23),(.055,.055,.46),WOOD)
    for xx in (x-.17,x+.17):
        g.cylinder((xx,y,z+.045),.10,.018,LIME,'Z',20)
        g.cylinder((xx,y+.12,z+.09),.035,.10,PLANK,'Z',12)
    for yy in (y-.47,y+.47):
        g.box((x,yy,z-.14),(.33,.28,.055),WOOD)
        g.box((x,yy+(1 if yy>y else -1)*.10,z+.05),(.33,.055,.35),WOOD)

def restaurant(g,parts):
    room(g,.38,.95,4.38,3.96,[.25,1.75,3.20],True)
    for x in (1.06,2.38,3.68):glazing(g,x,.91,2.49,1.12,1.06,back=False)
    for y in (1.50,2.43,3.39):glazing(g,.34,y,2.49,.81,1.06,'X',False)
    for x in (1.10,2.40,3.65):
        for y in (1.62,3.10):dining_table(g,x,y,2.35)
    # Broad roof, glazed clerestory and the attached kitchen chimney.
    gable(g,.21,.78,4.54,4.11,3.29,4.01)
    room(g,1.43,1.91,3.24,2.92,[3.64,4.14])
    for x in (1.90,2.77):glazing(g,x,1.86,3.90,.65,.31)
    lean_roof(g,1.34,1.76,3.33,3.03,4.17,4.30,40)
    chimney(g,4.10,3.54,3.42,1.15)
    # Ground-floor entry and serving counter with bowls and preparation trays.
    door(g,1.61,.88,.27)
    for x in (1.09,2.13):column(g,x,.24,.22,1.43,.19)
    gable(g,.96,.13,2.26,1.03,1.48,1.79)
    cage_lamp(g,1.03,.68,1.24)
    glazing(g,3.25,.89,1.03,.75,.78)
    hanging_sign(g,parts,.68,.45,1.69,'Restaurant')
    g.box((3.41,.40,.72),(1.40,.60,.88),WOOD)
    g.box((3.41,.37,1.18),(1.52,.69,.09),PLANK)
    lean_roof(g,2.60,.18,4.21,.97,1.58,1.95,41)
    for x in (2.93,3.30,3.69,4.00):
        g.ring((x,.31,1.25),.12,.025,.07,LIME,'Z',20)
        g.cylinder((x,.31,1.23),.093,.018,SAND,'Z',20)
    for i in range(5):g.rock((3.35,.62,1.29),(.16,.12,.08),SAND,300+i)
    cask(g,(4.61,3.09,.24),.30,.76)
    bin(g,(4.63,1.58,.24),(.59,.65,.48),LEAF,110)
    # Small masonry cooking bay under the chimney.
    g.box((4.62,3.44,1.08),(.60,.74,1.51),GREY)
    g.box((4.62,3.05,1.02),(.41,.04,.51),GLOW)
    for xx in (4.46,4.57,4.68,4.79):g.box((xx,3.02,1.02),(.025,.025,.51),IRON)

def grocery(g,parts):
    room(g,.39,1.01,4.37,3.95,[.25,2.14])
    # Open shop frontage: side alcoves and a central recessed entry.
    g.box((2.37,.93,1.10),(3.53,.04,1.52),IRON)
    for x in (1.05,3.64):glazing(g,x,.89,1.18,1.12,1.21,back=False)
    door(g,2.37,.88,.27)
    gable(g,.19,.77,4.58,4.13,2.25,3.25)
    room(g,1.01,1.91,3.75,3.13,[2.93,3.40])
    for x in (1.47,2.38,3.28):glazing(g,x,1.86,3.16,.68,.25)
    lean_roof(g,.91,1.77,3.86,3.25,3.44,3.55,50)
    chimney(g,3.46,3.17,3.21,.64)
    # Striped fabric awning, shaped as a sloping then curved sheet.
    for i in range(12):
        a=.43+i*1.55/12;b=a+1.55/12-.003
        ys=[.97,.67,.34,.19];zs=[1.96,1.88,1.68,1.60]
        verts=[(x,y,z) for y,z in zip(ys,zs) for x in (a,b)]
        g.add(verts,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(3)],CLOTH if i%2 else PLANK)
    for x in (.41,2.0):g.beam((x,.97,1.98),(x,.19,1.60),.05,mat=WOOD)
    hanging_sign(g,parts,.77,.24,1.22,'GroceryStore')
    # Produce, sacks, jars and stock bins are modeled separately, not a painted facade.
    for x in (1.10,3.60):
        bin(g,(x,.44,.25),(1.19,.68,.50),None)
        for i in range(18):g.rock((x-.46+(i%6)*.18,.23+(i//6)*.18,.84),(.16,.15,.14),SAND if i%3 else LEAF,700+i)
    g.box((4.32,.59,.71),(.63,.69,.92),WOOD)
    for i in range(4):g.rock((4.31,.57,1.23+i*.15),(.57,.43,.19),CLOTH,840+i)
    for y in (2.25,3.34):cask(g,(4.65,y,.24),.25,.65)
    for i in range(5):
        x=2.99+i*.23;g.cylinder((x,.64,1.03),.08,.26,PLANK,'Z',12);g.cylinder((x,.64,1.18),.08,.025,IRON,'Z',12)
    cage_lamp(g,2.04,.77,1.59)
    side_wall(g,.32,1.07,3.86,.28,1.97)
    for y in (1.73,2.86):glazing(g,.27,y,1.10,.65,.74,'X')

def fish(g,p,length=.40):
    x,y,z=p;g.rock(p,(length,length*.30,length*.18),LIME,44)
    g.add([(x+length*.28,y,z),(x+length*.65,y-length*.16,z),(x+length*.65,y+length*.16,z)],[(0,1,2)],GREY)
    g.cylinder((x-length*.30,y-.02,z+length*.07),.016,.012,IRON,'Z',8)

def fishery(g,parts):
    deck(g,.18,.72,4.57,4.01,.20)
    for x in (.39,2.17,4.36):
        for y in (1.24,3.79):column(g,x,y,.24,2.89,.23)
        trimmed_beam(g,(x,1.24,1.12),(x,3.79,1.12),.23)
    wall(g,.48,3.76,4.28,2.81,.28)
    side_wall(g,.43,1.34,3.70,.28,2.74)
    deck(g,.41,1.23,4.36,3.79,1.10)
    gable(g,.20,1.01,4.55,3.98,2.98,4.04)
    # Raised roof ventilator and small chimney break the broad roof plane.
    room(g,1.83,2.47,2.69,3.20,[3.91,4.43])
    for i in range(4):g.box((2.26,2.40,4.04+i*.075),(.71,.06,.035),IRON)
    gable(g,1.72,2.34,2.81,3.29,4.47,4.68)
    chimney(g,.83,1.75,2.82,.90)
    # Open working deck with tables, basins, knives and hanging fish.
    for x in (1.20,2.80):
        g.box((x,1.98,1.65),(1.15,.66,.11),PLANK)
        for xx in (x-.46,x+.46):g.box((xx,1.98,1.38),(.08,.49,.54),WOOD)
        for i in range(3):fish(g,(x-.31+i*.30,1.92,1.75),.28)
    for i in range(5):
        x=1.48+i*.38;g.beam((x,2.80,2.82),(x,2.80,2.35),.014,mat=IRON)
        g.rock((x,2.80,2.18),(.12,.08,.37),LIME,40+i)
    for x in (1.48,2.66,3.83):cage_lamp(g,x,2.70,2.67)
    # Door on the lower left, sign, work rail, and stairs at the outer side.
    wall(g,.49,1.04,1.76,1.09,.26);door(g,1.09,.98,.27)
    hanging_sign(g,parts,.64,.95,1.92,'FisheryWorks')
    rail(g,(2.00,1.21),(4.26,1.21),1.17)
    steps(g,4.33,.90,.54,1.10,1.52)
    # Wide water tanks on the lower front apron, trays and visible outfall at right.
    for x in (2.67,3.98):cask(g,(x,.57,.24),.54,.52,True)
    bin(g,(1.74,.48,.24),(.76,.66,.41),None)
    for i in range(4):fish(g,(1.58+i*.10,.46,.70),.25)
    round_pipe(g,[(4.36,3.50,2.12),(4.68,3.50,2.12),(4.76,3.38,1.93),(4.76,2.82,1.93)],.12)
    water=[(4.64,2.83,1.90),(4.90,2.83,1.90),(4.67,2.59,1.54),(4.95,2.59,1.54),
           (4.69,2.44,.72),(4.98,2.44,.72),(4.70,2.33,.28),(5.12,2.33,.28)]
    g.add(water,[(0,1,3,2),(2,3,5,4),(4,5,7,6)],WATER)
    g.box((4.91,2.25,.23),(.75,.88,.035),WATER)
    for z in (1.60,1.15,.65):g.rock((4.84,2.53,z),(.18,.06,.21),LIME,int(z*100))
