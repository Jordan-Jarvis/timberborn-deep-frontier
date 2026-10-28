"""Shared workshop joinery and stairs; authored dimensions are explicit."""
import math
import random
from frontier_architecture import *
from reference_materials import CRUSHER_STEEL


def steel_bolt(g,p,axis='Y',r=.022):
    g.cylinder(p,r*1.5,.014,IRON,axis,12)
    g.cylinder(p,r,.031,CRUSHER_STEEL,axis,6)

def bracket(g,x,y,z,w=.22):
    """Folded corner plate, with four fasteners on both visible faces."""
    for dx in (-1,1):
        xx=x+dx*(w/2+.012)
        g.box((xx,y,z),(.028,w+.052,.23),IRON)
        for dy in (-w*.30,w*.30):
            for dz in (-.068,.068):steel_bolt(g,(xx+dx*.018,y+dy,z+dz),'X',.018)
    for dy in (-1,1):
        yy=y+dy*(w/2+.012)
        g.box((x,yy,z),(w-.004,.028,.23),IRON)
        for dx in (-w*.30,w*.30):
            for dz in (-.068,.068):steel_bolt(g,(x+dx,yy+dy*.018,z+dz),'Y',.018)

def timber_column(g,x,y,bottom,top,w=.19):
    g.box((x,y,(bottom+top)/2),(w,w,top-bottom),WOOD)
    collar_levels=((bottom+top)/2,) if top-bottom<.46 else (bottom+.115,top-.115)
    for level in collar_levels:bracket(g,x,y,level,w)

def beam_joint(g,a,b,w=.18,depth=.18):
    g.beam(a,b,w,depth,WOOD)
    # End plates sit within the beam span, clear of the adjoining corner plate.
    span=math.dist(a,b)
    # Short tenons need no plate; short lintels have one central plate.
    plate_stations=() if span<.30 else ((.5,) if span<.60 else (.12,.88))
    for t in plate_stations:
        p=tuple(a[i]+(b[i]-a[i])*t for i in range(3))
        if abs(b[0]-a[0])>=abs(b[1]-a[1]):
            g.box((p[0],p[1]-.12,p[2]),(.27,.035,depth+.06),IRON)
            for dx in (-.075,.075):steel_bolt(g,(p[0]+dx,p[1]-.15,p[2]))
        else:
            g.box((p[0]-.12,p[1],p[2]),(.035,.27,depth+.06),IRON)
            for dy in (-.075,.075):steel_bolt(g,(p[0]-.15,p[1]+dy,p[2]),'X')

def handrail(g,a,b,z):
    a,b=Vector(a),Vector(b);count=math.ceil((b-a).length/.65)
    for i in range(count+1):
        p=a+(b-a)*i/count
        g.box((p.x,p.y,z+.19),(.075,.075,.45),WOOD)
        g.box((p.x,p.y,z-.035),(.12,.12,.11),IRON)
        steel_bolt(g,(p.x,p.y-.045,z+.34),r=.016)
    for height,width in ((.12,.065),(.38,.085)):
        g.beam((a.x,a.y,z+height),(b.x,b.y,z+height),width,mat=WOOD)

def sheet_roof(g,x0,y0,x1,y1,z0,z1,seed):
    """Broad weathered panels, timber edging, flat iron straps, corner shoes."""
    rng=random.Random(seed);count=math.ceil((x1-x0)/.28)
    for i in range(count):
        x=x0+(i+.5)*(x1-x0)/count
        g.beam((x,y0,z0),(x,y1,z1),(x1-x0)/count,.045,ROOF)
        for t in (.08,.92):steel_bolt(g,(x,y0+(y1-y0)*t,z0+(z1-z0)*t+.035),'Z',.015)
    for x in (x0,x1):g.beam((x,y0,z0-.035),(x,y1,z1-.035),.13,.14,WOOD)
    for y,z in ((y0,z0),(y1,z1)):
        g.beam((x0,y,z-.055),(x1,y,z-.055),.15,.16,WOOD)
        for x in (x0,x1):
            bracket(g,x,y,z-.07,.16)
            g.box((x,y,z+.050),(.22,.22,.025),IRON)
            steel_bolt(g,(x,y,z+.071),'Z',.024)
    for t in (.35,.72):
        y=y0+(y1-y0)*t;z=z0+(z1-z0)*t+.03
        g.beam((x0,y,z),(x1,y,z),.06,.018,IRON)
        for x in (x0+.08,x1-.08):steel_bolt(g,(x,y,z+.015),'Z',.016)
    for i in range(20):
        x=rng.uniform(x0+.05,x1-.05);t=rng.uniform(.08,.88);length=rng.uniform(.025,.12)
        y=y0+(y1-y0)*t;z=z0+(z1-z0)*t+.026
        g.beam((x,y,z),(x,y+length,z+length*(z1-z0)/(y1-y0)),.006,.004,WOOD)

def access_stair(g,x,lower_y,upper_y,*,z,top,width=.85):
    """Open treads, two diagonal stringers, vertical balusters and sloped rails."""
    if z!=int(z) or top!=int(top) or top<=z:
        raise ValueError('Stair endpoints must use increasing whole grid layers')
    run=upper_y-lower_y;rise=top-z
    if abs(abs(run)-rise)>1e-6:raise ValueError('Native stair flights need one horizontal cell per layer')
    count=8*int(rise)
    for i in range(count):
        t=(i+1)/count;yy=lower_y+run*(i+.5)/count;zz=z+rise*t
        g.box((x,yy,zz-.04),(width,abs(run)/count+.035,.08),PLANK)
        for dx in (-width*.39,width*.39):steel_bolt(g,(x+dx,yy,zz+.007),'Z',.015)
    for sign in (-1,1):
        xx=x+sign*(width/2+.025)
        g.beam((xx,lower_y,z-.025),(xx,upper_y,top-.095),.115,.15,WOOD)
        g.box((xx,lower_y,z+.08),(.21,.24,.16),IRON)
        for dy in (-.065,.065):steel_bolt(g,(xx+sign*.12,lower_y+dy,z+.10),'X',.024)
        for t in (0,.33,.67,1):
            yy=lower_y+run*t;zz=z+rise*t
            g.box((xx,yy,zz+.23),(.075,.075,.56),WOOD)
            g.box((xx,yy,zz+.505),(.11,.11,.035),IRON)
            steel_bolt(g,(xx+sign*.047,yy,zz-.02),'X',.022)
        for offset,w in ((.19,.052),(.47,.083)):
            g.beam((xx,lower_y,z+offset),(xx,upper_y,top+offset),w,mat=WOOD)

