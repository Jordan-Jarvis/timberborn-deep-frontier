"""Construction details used by reference studies, at consistent visual scale."""
import math
from mathutils import Vector
from frontier_architecture import *
from reference_materials import GLOW,WATER

def cask(g,p,r=.43,h=1.0,water=False):
    x,y,z=p;n=20
    # Separate tapered staves form a closed barrel with narrow joints.
    levels=[(0,r*.88),(.13*h,r*.96),(.50*h,r),(h*.87,r*.96),(h,r*.88)]
    for i in range(n):
        a0=(i+.025)*2*math.pi/n;a1=(i+.975)*2*math.pi/n
        v=[]
        for zz,rr in levels:
            v.extend([(x+math.cos(a0)*rr,y+math.sin(a0)*rr,z+zz),(x+math.cos(a1)*rr,y+math.sin(a1)*rr,z+zz)])
        g.add(v,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(len(levels)-1)],PLANK)
    for zz,rr in ((.12*h,r*.96),(.50*h,r),(.88*h,r*.96)):
        g.ring((x,y,z+zz),rr+.015,.032,.075,IRON,'Z',n)
        for i in range(10):
            a=i*math.pi/5;g.cylinder((x+math.cos(a)*(rr+.025),y+math.sin(a)*(rr+.025),z+zz),.017,.035,BRASS,'Z',6)
    if water:g.cylinder((x,y,z+h-.07),r*.85,.025,WATER,'Z',32)
    else:
        g.cylinder((x,y,z+h-.014),r*.88,.035,PLANK,'Z',n)
        for offset in (-.55,-.18,.18,.55):
            length=2*math.sqrt((r*.86)**2-(offset*r)**2)
            g.box((x+offset*r,y,z+h+.008),(.009,length,.008),WOOD)
        g.ring((x,y,z+h),r*.89,.025,.045,IRON,'Z',n)

def round_pipe(g,points,r=.055):
    # Cylindrical tubing and faceted rounded elbows, with flange bolts at each joint.
    for a,b in zip(points,points[1:]):
        a,b=Vector(a),Vector(b);d=b-a;rotation=d.to_track_quat('Z','Y');n=12
        verts=[p+rotation@Vector((math.cos(i*2*math.pi/n)*r,math.sin(i*2*math.pi/n)*r,0)) for p in (a,b) for i in range(n)]
        g.add(verts,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],IRON)
    for p in points[1:-1]:g.rock(p,(r*2.22,r*2.22,r*2.22),IRON,12)

def machinery_shell(g,p,profile,axis='Y',segments=24,fastener_material=BRASS):
    x,y,z=p
    def point(a,b,c):return (x+c,y+a,z+b) if axis=='X' else (x+a,y+c,z+b)
    verts=[point(math.cos(i*math.pi*2/segments)*r,math.sin(i*math.pi*2/segments)*r,t) for t,r in profile for i in range(segments)]
    faces=[tuple(reversed(range(segments))),tuple(range((len(profile)-1)*segments,len(profile)*segments))]
    for level in range(len(profile)-1):
        for i in range(segments):faces.append((level*segments+i,level*segments+(i+1)%segments,(level+1)*segments+(i+1)%segments,(level+1)*segments+i))
    if axis=='Y':faces=[tuple(reversed(f)) for f in faces]
    g.add(verts,faces,IRON)
    for t,r in profile[1:-1]:
        pp=point(0,0,t);g.ring(pp,r+.018,.035,.075,IRON,axis,segments)
        for i in range(12):
            a=i*math.pi/6
            q=point(math.cos(a)*(r+.024),math.sin(a)*(r+.024),t)
            g.cylinder(q,.021,.035,fastener_material,axis,6)

def steps(g,x,y,width,height,depth):
    count=math.ceil(height/.15)
    for i in range(count):g.box((x,y+depth*(i+.5)/count,(i+1)*height/count/2),(width,depth/count+.01,(i+1)*height/count),PLANK)
    for xx in (x-width/2,x+width/2):g.beam((xx,y+.05,.1),(xx,y+depth,height),.10,mat=WOOD)

def cage_lamp(g,x,y,z):
    g.beam((x,y+.05,z+.16),(x,y-.13,z+.16),.035,mat=IRON)
    g.cylinder((x,y-.13,z),.06,.19,GLOW,'Z',8)
    for zz in (z-.12,z+.12):g.cylinder((x,y-.13,zz),.085,.025,IRON,'Z',8)
    for dx,dy in ((-.052,-.052),(-.052,.052),(.052,-.052),(.052,.052)):
        g.beam((x+dx,y-.13+dy,z-.12),(x+dx,y-.13+dy,z+.12),.012,mat=IRON)
