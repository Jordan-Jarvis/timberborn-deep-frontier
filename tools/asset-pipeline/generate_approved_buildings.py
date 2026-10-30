"""Build remaining reactor/cryo prototypes; reviewed replacements and the map objects have separate owners."""
import argparse
import json
import math
import random
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
import gpu_render_lock
from frontier_architecture import *
from concept_materials import create_concept_materials
from concept_crusher import crusher as concept_crusher
PLUGIN=ROOT/'tools/asset-pipeline/timbermesh-plugin'
sys.path[:0]=[str(PLUGIN),str(PLUGIN/'timbermesh_blender_plugin')]
from timbermesh_blender_plugin import timbermesh_exporter
SOURCE=ROOT/'src/DeepFrontier'; DATA=SOURCE/'Data'; OUT=ROOT/'outputs/approved-building-renders'
CATALOG=json.loads((ROOT/'tools/construction_materials.json').read_text())

def roller(g,p,r,length,teeth=True,axis='X'):
    g.cylinder(p,r,length,IRON,axis,24)
    for offset in (-length*.43,length*.43):
        point=list(p);point[0 if axis=='X' else 1]+=offset
        g.ring(point,r+.028,.035,.07,BRASS,axis)
    if teeth:
        for row in range(5):
            for i in range(12):
                a=(i+row*.5)*math.pi/6
                g.box((p[0]-length*.40+row*length*.20,p[1]+math.cos(a)*(r+.015),p[2]+math.sin(a)*(r+.015)),(.09,.075,.075),GREY)
    else:
        for i in range(12):
            a=i*math.pi/6
            for offset in (-length*.32,length*.32):
                point=(p[0]+math.cos(a)*r,p[1]+offset,p[2]+math.sin(a)*r)
                g.box(point,(.035,.045,.035),BRASS)

def crusher(g,parts):
    deck(g,.06,.06,2.94,2.94)
    # Rear feed hopper and a low, separate roof leave the moving rollers visible.
    shed(g,.15,1.80,2.85,2.86,1.64,1.92)
    for x in (.45,2.55):
        post(g,x,.80,1.30);g.beam((x,.80,1.2),(x,2.5,1.2),.16,mat=WOOD)
        g.beam((x,.8,.45),(x,1.55,1.2),.10,mat=WOOD)
    for y in (1.15,1.72):
        center=(1.50,y,1.15);m=Geometry('CrusherRoller',center)
        roller(m,center,.24,1.62);parts.append((m,'X',1 if y<1.5 else -1))
    for y in (1.15,1.72):
        g.cylinder((.56,y,1.15),.10,.23,IRON,'X')
        g.cylinder((2.44,y,1.15),.10,.23,IRON,'X')
    m=Geometry('CrusherFlywheel',(.30,1.15,1.15));m.wheel((.30,1.15,1.15),.39);parts.append((m,'X',1))
    bin(g,(1.5,2.28,1.17),(1.68,.73,.40),SAND,11)
    bin(g,(2.10,.45,.20),(1.14,.60,.39),GREY,21)
    g.beam((1.6,1.03,.90),(2.1,.65,.58),.68,.055,IRON)
    # Clear access is at X=1.5 on the front tile edge.
    door(g,1.18,.33,.20)
    roof(g,.72,.18,1.62,.63,.96,1.08)
    for x in (.10,2.90):
        g.cylinder((x,1.5,.50),.12,.12,IRON,'X');g.ring((x,1.5,.50),.15,.025,.06,BRASS,'X')

def kiln(g,parts):
    deck(g,.06,.06,2.94,3.94)
    shed(g,.17,.78,2.54,3.82,2.25,2.63)
    for y in (1.28,2.78):
        g.box((1.48,y,.68),(1.80,.24,.93),WOOD)
        g.plate((1.48,y-.13,1.02),(.65,.04,.26))
    center=(1.48,2.03,1.40);m=Geometry('RotaryKiln',center)
    roller(m,center,.53,2.55,False,'Y')
    for y in (1.0,1.62,2.40,3.05):m.ring((1.48,y,1.40),.56,.035,.10,IRON,'Y')
    parts.append((m,'Y',.35))
    for y in (1.12,2.94):g.ring((1.48,y,1.40),.60,.05,.09,BRASS,'Y')
    for xx in (1.02,1.94):
        for yy in (1.12,2.94):g.cylinder((xx,yy,1.06),.13,.18,IRON,'Y')
    bin(g,(1.38,3.38,1.72),(1.22,.70,.44),LIME,31)
    g.box((2.50,1.05,.95),(.60,.72,1.40),GREY)
    for row in range(6):
        for i in range(3):g.box((2.27+i*.19, .676,.31+row*.22),(.18,.035,.20),LIME)
    chimney(g,2.55,1.12,1.64,1.19)
    g.box((2.50,.647,.91),(.34,.035,.40),IRON)
    g.box((2.50,.621,.89),(.23,.012,.25),SAND)
    for x in (2.43,2.50,2.57):g.box((x,.605,.89),(.018,.025,.25),IRON)
    for i in range(8):
        g.cylinder((.50+(i%2)*.20,1.10+(i//4)*.52,.30+((i//2)%2)*.17),.085,.44,WOOD,'Y',10)
        g.cylinder((.50+(i%2)*.20,.871+(i//4)*.52,.30+((i//2)%2)*.17),.067,.008,PLANK,'Y',10)
    bin(g,(2.17,.34,.18),(1.10,.52,.30),LIME,41)
    door(g,1.5,.40,.18);roof(g,1.03,.18,1.97,.70,1.02,1.15)
    m=Geometry('KilnDrive',(.35,2.2,.83));m.wheel((.35,2.2,.83),.32);parts.append((m,'X',1))

def mixer(g,parts):
    deck(g,.06,.06,2.94,2.94)
    shed(g,.12,1.25,2.09,2.87,2.55,2.84)
    for x in (.44,2.42):
        post(g,x,.80,1.83)
        g.beam((x,.8,.6),(x,1.72,1.58),.14,mat=WOOD)
        g.beam((x,.8,1.58),(x,2.5,1.58),.15,mat=WOOD)
    center=(1.48,1.38,1.43);m=Geometry('MixingDrum',center)
    m.cylinder((1.48,1.38,1.43),.57,1.13,IRON,'Y',24)
    m.cylinder((1.48,.69,1.43),.30,.27,IRON,'Y',24,r2=.55)
    m.ring((1.48,.55,1.43),.32,.055,.08,BRASS,'Y')
    for y in (.94,1.55,1.87):m.ring((1.48,y,1.43),.61,.035,.08,BRASS,'Y')
    for i in range(12):
        a=i*math.pi/6
        m.beam((1.48+math.cos(a)*.58,.91,1.43+math.sin(a)*.58),(1.48+math.cos(a)*.58,1.92,1.43+math.sin(a)*.58),.035,mat=IRON)
    parts.append((m,'Y',.55))
    bin(g,(.77,2.27,1.67),(1.08,.87,.43),GREY,51)
    bin(g,(1.61,2.27,2.12),(.56,.68,.32),LIME,52)
    barrel(g,(2.50,2.32,1.96),.30,.73)
    for x in (2.25,2.74):post(g,x,2.34,1.96)
    pipe(g,[(2.50,2.05,2.34),(2.50,1.62,2.34),(1.9,1.62,2.34),(1.9,1.62,1.84)],.055)
    bin(g,(2.16,.41,.20),(1.08,.56,.30),GREY,53)
    g.beam((1.48,.60,1.21),(2.16,.49,.55),.60,.055,IRON)
    door(g,.88,.36,.18);roof(g,.44,.16,1.30,.66,1.06,1.21)
    m=Geometry('MixerDriveWheel',(.29,1.40,1.35));m.wheel((.29,1.40,1.35),.35);parts.append((m,'X',1))

def pit(g,parts,stone):
    deck(g,.06,.06,1.94,1.94)
    shed(g,.14,.64,1.35,1.86,1.52,1.84)
    bin(g,(.58,.45,.20),(.85,.56,.37),stone,61)
    bin(g,(.67,1.27,.27),(.77,.66,.45),stone,62)
    post(g,1.75,1.63,1.77)
    g.beam((1.72,1.67,1.69),(1.72,.82,1.69),.12,mat=WOOD)
    g.beam((1.72,1.62,1.26),(1.72,1.05,1.69),.07,mat=IRON)
    g.beam((1.72,.86,1.62),(1.72,.86,.97),.021,mat=IRON)
    bin(g,(1.67,.87,.55),(.38,.38,.32),stone,63)
    center=(1.67,1.54,1.31);m=Geometry('PitWinch',center)
    m.wheel(center,.18);m.cylinder((1.52,1.54,1.31),.085,.30,WOOD,'X')
    parts.append((m,'X',.3))
    g.box((1.34,1.83,.69),(.30,.06,.85),WOOD)
    for z in (.50,.72,.94):g.beam((1.26,1.78,z),(1.43,1.78,z),.03,mat=IRON)
    # A narrow inspection grate adds readable sorting machinery.
    for i in range(5):g.box((.29+i*.13,.48,.66),(.025,.47,.025),IRON)

def quarry(g,parts,stone):
    # Four walkways frame the shaft; no fake 5x5 mountain under the building.
    deck(g,.06,.06,4.94,1.70);deck(g,.06,3.40,4.94,4.94)
    deck(g,.06,1.70,1.73,3.40);deck(g,3.38,1.70,4.94,3.40)
    g.box((2.55,2.55,.10),(1.65,1.65,.14),IRON)
    for x in (1.72,3.38):g.box((x,2.55,.25),(.15,1.85,.20),GREY)
    for y in (1.68,3.42):g.box((2.55,y,.25),(1.80,.15,.20),GREY)
    for x in (1.65,3.45):
        for y in (1.9,3.25):
            g.beam((x,y,.25),(2.02 if x<2 else 3.08,y,3.50),.22,.24,WOOD)
            g.plate((x,y-.11,.52),(.28,.08,.37))
        g.beam((x,1.9,.50),(x,3.25,2.25),.12,mat=WOOD)
    for y in (1.9,3.25):
        g.beam((1.84,y,3.48),(3.26,y,3.48),.25,mat=WOOD)
        g.beam((1.65,y,1.95),(3.45,y,1.95),.16,mat=WOOD)
    center=(2.55,2.6,3.48);m=Geometry('QuarryWindingDrum',center)
    m.cylinder(center,.30,.98,WOOD,'X',24)
    for x in (2.04,3.06):m.ring((x,2.6,3.48),.37,.055,.08,IRON,'X')
    for i in range(14):m.ring((2.10+i*.068,2.6,3.48),.31,.012,.025,BRASS,'X')
    parts.append((m,'X',.30))
    g.beam((2.55,2.35,.75),(2.55,2.35,3.45),.025,mat=IRON)
    bin(g,(2.55,2.35,.55),(.61,.57,.46),stone,77)
    deck(g,1.7,3.46,3.55,4.23,2.05);rail(g,(1.75,4.18),(3.5,4.18),2.12)
    ladder(g,3.85,3.7,.23,1.9,.34)
    shed(g,.20,2.18,1.48,4.66,1.88,2.30)
    door(g,.84,2.14,.18);window(g,.84,2.09,1.30,.44,.36)
    for y in (.54,1.36):bin(g,(4.12,y,.21),(1.18,.68,.53),stone,int(y*100))
    bin(g,(.88,.70,.21),(1.23,.92,.51),stone,79)
    for a,b in [((.12,1.5),(.12,4.80)),((.12,4.8),(4.84,4.8)),((4.84,1.9),(4.84,4.8))]:rail(g,a,b,.20)
    barrel(g,(4.25,4.11,.22),.35,.85,True)
    pipe(g,[(4.25,4.11,1.02),(3.80,4.11,1.02),(3.80,3.0,.57)],.075)
    m=Geometry('QuarryDrive',(.43,1.75,.86));m.wheel((.43,1.75,.86),.40);parts.append((m,'X',.7))
    for y in (1.2,1.45):g.box((2.55,y,.20),(1.05,.22,.10),PLANK)

def civic(g,parts,kind):
    deck(g,.06,.06,2.94,2.94)
    # Real walls, corner framing and separate story floor beams.
    wall(g,.22,2.77,2.78,2.33)
    for x in (.24,2.76):
        for i in range(17):g.box((x,.46+i*.137,1.25),(.07,.128,2.16),PLANK)
        for y in (.43,1.59,2.75):post(g,x,y,2.42)
        for z in (.25,1.29,2.35):g.box((x,1.59,z),(.16,2.43,.14),WOOD)
    wall(g,.28,.45,2.72,2.34,.20)
    for z in (1.29,2.34):g.box((1.50,.40,z),(2.62,.16,.13),WOOD)
    for x in (.28,1.5,2.72):post(g,x,.40,2.42)
    door(g,1.50,.35)
    for x in (.72,2.28):
        window(g,x,.36,.77,.56,.55)
        window(g,x,.36,1.85,.55,.58)
    window(g,1.50,.36,1.85,.47,.58)
    if kind=='Hospital':
        roof(g,.13,.25,2.87,2.87,2.40,2.92)
        for x in (.64,2.36):
            bin(g,(x,.23,.31),(.50,.24,.20),None)
            for i in range(5):g.rock((x-.16+i*.08,.23,.58),(.10,.10,.14),ROOF,80+i)
        barrel(g,(2.44,2.36,2.03),.30,.65)
    elif kind=='Restaurant':
        roof(g,.13,.25,2.87,2.87,2.39,2.75)
        chimney(g,2.53,2.53,2.39,.47)
        g.box((1.5,1.68,2.71),(1.2,.85,.22),WOOD)
        roof(g,.86,1.22,2.14,2.13,2.80,2.94)
        for x in (.65,2.35):
            g.box((x,.22,.51),(.60,.31,.10),WOOD)
            for i in range(3):g.cylinder((x-.18+i*.18,.22,.59),.065,.035,LIME,segments=12)
    elif kind=='GroceryStore':
        roof(g,.13,.37,2.87,2.87,2.39,2.78)
        # Receiving stock and a large street-facing timber awning.
        roof(g,.22,.11,2.78,.95,1.15,1.34)
        for x in (.30,2.70):post(g,x,.18,1.18)
        for x in (.65,2.35):
            bin(g,(x,.25,.20),(.55,.32,.31),SAND,int(x*100))
            g.box((x,.51,.83),(.60,.32,.06),WOOD)
        barrel(g,(2.55,2.48,.2),.22,.58)
    elif kind=='FisheryWorks':
        roof(g,.13,.38,2.87,2.87,2.39,2.91)
        chimney(g,2.51,2.48,2.24,.46)
        for x in (.60,2.43):barrel(g,(x,.42,.20),.28,.43,True)
        pipe(g,[(2.77,1.15,1.30),(2.77,.45,1.30),(2.43,.45,.65)],.055)
        g.box((1.5,.20,1.05),(.85,.25,.10),WOOD)
        for x in (1.23,1.48,1.73):g.rock((x,.20,1.13),(.19,.07,.06),LIME,int(x*100))
    else:raise ValueError(kind)
    # Pivoted hanging sign: purposeful, subtle animation on civic buildings.
    center=(1.5,.19,1.50);m=Geometry(kind+'HangingSign',center)
    sign_geometry(m,(1.50,.19,1.30),kind)
    g.beam((1.17,.43,1.55),(1.17,.13,1.55),.045,mat=IRON)
    g.beam((1.83,.43,1.55),(1.83,.13,1.55),.045,mat=IRON)
    parts.append((m,'SWAY',.04))

def prototype_post(g,x,y,top,bottom=.18):
    """Timber seated inside a separate steel shoe, with no shared bottom face."""
    g.box((x,y,(bottom+.13+top)/2),(.14,.14,top-bottom-.13),WOOD)
    g.plate((x,y-.025,bottom+.08),(.18,.17,.16))
    g.plate((x,y-.025,top-.105),(.18,.17,.11))


def prototype_shed(g,x0,y0,x1,y1,eave,ridge):
    """Joined canopy members, with end caps extending beyond roof planks.

    Headers sit on the post ends. Each side has one diagonal so short sheds
    cannot cross two braces in the same plane. Roof end trim overlaps the
    sheets in real depth, rather than sharing their exposed end faces.
    """
    for x in (x0+.08,x1-.08):
        for y in (y0+.10,y1-.10):prototype_post(g,x,y,eave-.25)
    for y in (y0+.10,y1-.10):
        g.beam((x0+.08,y,eave-.18),(x1-.08,y,eave-.18),.14,mat=WOOD)
    for x in (x0+.08,x1-.08):
        g.beam((x,y0+.1,eave-.60),(x,y1-.1,eave-.25),.09,mat=WOOD)
    # Back infill butts against the timber posts; its horizontal trim ends
    # before the wider steel shoes instead of sharing their upper face.
    lo,hi=x0+.15,x1-.15;bottom=.22;top=eave-.2
    count=math.ceil((hi-lo)/.15);width=(hi-lo)/count
    for i in range(count):
        g.box((lo+(i+.5)*width,y1-.10,(top+bottom)/2),(width,.07,top-bottom),PLANK)
    for z in (bottom+.07,top-.07):
        g.box(((x0+x1)/2,y1-.135,z),(x1-x0-.38,.12,.10),WOOD)
    mid=(x0+x1)/2;length=y1-y0;count=math.ceil(length/.26)
    for i in range(count):
        y=y0+(i+.5)*length/count
        for x in (x0,x1):g.beam((x,y,eave),(mid,y,ridge),length/count,.055,ROOF)
    for y in (y0+.015,y1-.015):
        for x in (x0,x1):
            g.beam((x,y,eave-.055),(mid,y,ridge-.055),.10,.09,WOOD)
            for t in (.07,.48,.90):g.rivet((x+(mid-x)*t,y-.055,eave+(ridge-eave)*t),r=.022)
    # The solid longitudinal cap ends wrap past both plank end planes.
    g.beam((mid,y0-.06,ridge),(mid,y1+.06,ridge),.10,.11,IRON)
    for x in (x0,x1):g.beam((x,y0-.06,eave),(x,y1+.06,eave),.11,.12,WOOD)


def industrial_tanks(g,parts,kind,size):
    w,d,h=size;deck(g,.06,.06,w-.06,d-.06)
    if kind=='NuclearReactor':
        cx,cy=w*.57,d*.56;r=min(w,d)*.255
        g.cylinder((cx,cy,1.18),r,1.93,IRON,'Z',32)
        g.cylinder((cx,cy,2.30),r,.40,ROOF,'Z',32,r2=r*.68)
        g.cylinder((cx,cy,2.55),r*.68,.18,IRON,'Z',24,r2=.20)
        for z in (.34,.75,1.82,2.10):g.ring((cx,cy,z),r+.055,.06,.10,BRASS)
        for i in range(16):
            a=i*math.pi/8
            for z in (.75,1.82):g.box((cx+math.cos(a)*(r+.06),cy+math.sin(a)*(r+.06),z),(.035,.035,.035),LIME)
        prototype_shed(g,.18,.25,1.16,d-.30,1.25,1.55)
        for x in (.26,w-.28):
            pipe(g,[(x,.50,.50),(x,d*.53,.50),(cx-r if x<1 else cx+r,d*.53,1.2)],.12)
        ladder(g,w-.42,d-.7,.20,2.1,.25)
    else:
        for cx in (w*.32,w*.67):
            cy=d*.62;r=.43
            g.cylinder((cx,cy,1.26),r,1.85,LIME,'Z',24)
            g.cylinder((cx,cy,2.25),r,.18,IRON,'Z',24,r2=.24)
            for z in (.42,1.33,2.10):g.ring((cx,cy,z),r+.035,.035,.07,IRON)
            for x in (cx-.28,cx+.28):prototype_post(g,x,cy,.55)
            pipe(g,[(cx,cy,2.40),(cx,cy-.6,2.40),(cx,cy-.6,.54)],.07)
        prototype_shed(g,.16,.18,w-.16,.97,1.15,1.40)
        for i in range(8):g.box((w*.5,.32+i*.07,.69),(.55,.035,.30),IRON)
    center=(.48,.35,.68);m=Geometry(kind+'PumpWheel',center)
    g.cylinder((.48,.57,.68),.07,.27,IRON,'Y')
    m.wheel(center,.22,'Y');parts.append((m,'Y',.8))

def validate_collection(c,size):
    low=np.full(3,np.inf);high=np.full(3,-np.inf);faces=0;cache={}
    bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
    for obj in c.objects:
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
        coordinates=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',coordinates)
        cache[obj.name]=coordinates.reshape((-1,3));mesh.calc_loop_triangles();faces+=len(mesh.loop_triangles)
        evaluated.to_mesh_clear()
    for frame in range(1,62):
        bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
        for obj in c.objects:
            if frame>1 and obj.animation_data is None:continue
            evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            matrix=np.array(evaluated.matrix_world)
            points=cache[obj.name]@matrix[:3,:3].T+matrix[:3,3]
            points=points*np.array([-1,-1,1])
            low=np.minimum(low,points.min(axis=0));high=np.maximum(high,points.max(axis=0))
    for i in range(3):
        if low[i]<-.0001 or high[i]>size[i]+.0001:
            raise ValueError(f'{c.name}: animated geometry exceeds declared {size}; bounds={low}, {high}')
    return dict(name=c.name,size=size,boundsMin=low.tolist(),boundsMax=high.tolist(),triangles=faces,objects=len(c.objects),animationFramesChecked=61)

def main():
    args=argparse.ArgumentParser();args.add_argument('--render',default='NuclearReactor');args.add_argument('--resolution',type=int,default=1200)
    args.add_argument('--save-only',action='store_true',help='Author source only; perform checks before official export')
    cli=args.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):bpy.data.collections.remove(c)
    scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=61;scene.render.fps=30
    materials=create_materials();concept_materials=create_concept_materials();models={};reports=[];exports=[]
    # This historical generator owns only unreplaced prototypes. Reviewed
    # buildings are exported from their individual ReferenceStudy sources.
    definitions=[]
    extra={'NuclearReactor':'Power','CryogenicLiquefactionPlant':'Metal'}
    for ident,group in extra.items():
        folder=f'Buildings/{group}/{ident}'
        blueprint=json.loads((DATA/f'{folder}/{ident}.IronTeeth.blueprint.json').read_text())
        s=blueprint['BlockObjectSpec']['Size']
        definitions.append(dict(id=ident,kind='civic' if ident in ('Hospital','Restaurant','GroceryStore','FisheryWorks') else 'tanks',size=[s['X'],s['Y'],s['Z']],folder=folder))
    for b in definitions:
        ident,kind,size=b['id'],b['kind'],b['size'];c=bpy.data.collections.new(ident+'.IronTeeth.Model');scene.collection.children.link(c)
        g=Geometry(ident+'Architecture');parts=[]
        if kind=='crusher':concept_crusher(g,parts)
        elif kind=='kiln':kiln(g,parts)
        elif kind=='mixer':mixer(g,parts)
        elif kind=='pit':pit(g,parts,SAND if b['good']=='Sandstone' else LIME)
        elif kind=='quarry':quarry(g,parts,SAND if b['good']=='Sandstone' else LIME)
        elif kind=='civic':civic(g,parts,ident)
        elif kind=='tanks':industrial_tanks(g,parts,ident,size)
        else:raise ValueError(kind)
        model_materials=concept_materials if kind=='crusher' else materials
        g.build(c,model_materials,uv_profile='prototype-native')
        for geo,axis,speed in parts:
            obj=geo.build(c,model_materials,.004,uv_profile='prototype-native')
            if axis=='SWAY':sway(obj,speed)
            else:spin(obj,axis,speed)
        report=validate_collection(c,size);reports.append(report)
        print('BOUNDS PASS',json.dumps(report),flush=True)
        models[ident]=(c,size);exports.append((c,DATA/b['folder']/(c.name+'.timbermesh')))
        uc=bpy.data.collections.new(ident+'.IronTeeth.ConstructionStage0.Model');scene.collection.children.link(uc)
        ug=Geometry(ident+'Construction');w,d,h=size;deck(ug,.06,.06,w-.06,d-.06)
        for x in (.25,w-.25):
            for y in (.25,d-.25):prototype_post(ug,x,y,h*.55)
            ug.beam((x,.25,.3),(x,d-.25,h*.52),.08,mat=WOOD)
        for i in range(7):ug.box((w*.5,.45+i*.12,.34),(w*.50,.10,.12),PLANK)
        ug.build(uc,model_materials,uv_profile='prototype-native');validate_collection(uc,size)
        exports.append((uc,DATA/b['folder']/(uc.name+'.timbermesh')))
    # Map objects (deposits, seams, the ore vein and source) are owned by
    # build_map_objects.py and tools/map_objects.json; this generator no longer
    # writes MapEditor models.
    scene.frame_set(1)
    if cli.save_only:
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/'geometry-validation.json').write_text(json.dumps(reports,indent=2))
        blend=SOURCE/'Art/Source/ApprovedBuildings.blend'
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        print('PROTOTYPE SOURCE SAVED; EXPORT AND RENDER NOT RUN',flush=True)
        return
    settings=timbermesh_exporter.ExportSettings(bpy.context,False,True,False)
    for c,path in exports:
        path.parent.mkdir(parents=True,exist_ok=True);timbermesh_exporter.Exporter.export_collection(c,str(path),settings)
        print('EXPORTED',path.relative_to(ROOT),flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'geometry-validation.json').write_text(json.dumps(reports,indent=2))
    rig=bpy.data.collections.new('StudioRig');scene.collection.children.link(rig)
    scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
    preferences=bpy.context.preferences.addons['cycles'].preferences
    preferences.compute_device_type='OPTIX';preferences.get_devices()
    devices=[device for device in preferences.devices if device.type=='OPTIX' and device.name=='NVIDIA GeForce RTX 2060']
    if len(devices)!=1:raise RuntimeError('Required local OptiX render device NVIDIA GeForce RTX 2060 is unavailable')
    for device in preferences.devices:device.use=device in devices
    scene.cycles.device='GPU'
    # Denoise on the GPU too: OIDN on the CPU used ~85 of the ~95 CPU-seconds of a 1200 px render.
    if not preferences.has_oidn_gpu_devices():raise RuntimeError('RTX 2060 OIDN GPU denoising unavailable')
    scene.cycles.denoising_use_gpu=True
    scene.render.resolution_x=cli.resolution;scene.render.resolution_y=cli.resolution;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.world.color=(.35,.35,.35);scene.view_settings.view_transform='AgX'
    def move_to_rig(o):
        for c in list(o.users_collection):c.objects.unlink(o)
        rig.objects.link(o)
    bpy.ops.object.camera_add();cam=bpy.context.object;move_to_rig(cam);scene.camera=cam;cam.data.type='ORTHO'
    for pos,energy,scale in [((2,4,7),650,5),((-5,1,5),400,5),((-1,-5,7),850,4)]:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;move_to_rig(o)
        o.data.energy=energy;o.data.shape='DISK';o.data.size=scale
        o.rotation_euler=(Vector((-1.5,-1.5,1))-o.location).to_track_quat('-Z','Y').to_euler()
    ground=bpy.data.materials.new('StudioGround');ground.diffuse_color=(.20,.22,.22,1);ground.use_nodes=True
    ground.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.20,.22,.22,1)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.035));plane=bpy.context.object;move_to_rig(plane);plane.data.materials.append(ground)
    # Preserve a usable Blender source scene with studio rig and all named assets.
    for ident in cli.render.split(','):
        c,size=models[ident]
        for candidate in scene.collection.children:candidate.hide_render=candidate not in (c,rig)
        w,d,h=size;target=Vector((-w/2,-d/2,h*.43));cam.location=target+Vector((6,8,5.5))
        cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=max(w,d,h)*1.52
        scene.render.filepath=str(OUT/(ident+'-studio.png'));gpu_render_lock.render(write_still=True)
        print('RENDERED',ident,flush=True)
    for c in scene.collection.children:c.hide_render=c.name=='StudioRig';c.hide_viewport=c.name=='StudioRig'
    blend=SOURCE/'Art/Source/ApprovedBuildings.blend';blend.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print('APPROVED ARCHITECTURE GENERATION COMPLETE',len(exports),'exports',flush=True)

if __name__=='__main__':main()
