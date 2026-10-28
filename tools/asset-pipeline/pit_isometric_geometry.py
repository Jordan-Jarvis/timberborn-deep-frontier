"""Small mineral yards from the mining sheet's two isometric pit drawings.

No top view or printed tile dimensions are used. Game registration follows the
finished geometry. The enclosed store room has one ground-level arch.
"""
import math
import random

from frontier_architecture import Geometry, WOOD, PLANK, IRON, SAND, LIME, BRASS, deck, facade_panel
from industrial_geometry import timber_column, beam_joint, bracket, steel_bolt, sheet_roof
from industrial_facades import window_y, side_window
from industrial_door_components import recipe as door_recipe
from pit_apron_components import recipe as apron_recipe
# (No native props: the pits' loose barrels were removed, 2026-10-22.)
from reference_details import cage_lamp
from industrial_kit import open_beam, wheel, gauge
from industrial_kit import (timber_column, beam_joint, bracket, steel_bolt, sheet_roof, cage_lamp, band, prism,
                               bolt, square_nut, open_box, rock, rock_heap)
from reference_materials import CIVIC_CONCRETE, CIVIC_FORGED_PANEL
from walkway_geometry import RailAssembly
from opaque_shell_geometry import lean_roof_curb

HOIST_TOP=3.67
CABLE_BOTTOM=2.43

def stone_bin(g, p, size, stone, seed):
    x,y,z=p;w,d,h=size
    g.box((x,y,z+.055),(w-.09,d-.09,.11),PLANK)
    for row in range(4):
        zz=z+(row+.5)*h/4
        for yy in (y-d/2,y+d/2):
            g.box((x,yy,zz),(w+.08,.09,h/4-.012),PLANK)
        for xx in (x-w/2,x+w/2):
            g.box((xx,y,zz),(.09,d-.09,h/4-.012),PLANK)
    for xx in (x-w/2,x+w/2):
        for yy in (y-d/2,y+d/2):
            timber_column(g,xx,yy,z+.11,z+h+.08,.13)
    rng=random.Random(seed)
    g.box((x,y,z+h*.60),(w-.10,d-.10,.14),stone)
    for row in range(4):
        for col in range(5):
            xx=x+(col-2)*w*.17+rng.uniform(-.04,.04)
            yy=y+(row-1.5)*d*.22+rng.uniform(-.035,.035)
            s=rng.uniform(.20,.32)
            rock(g,(xx,yy,z+h*.78+rng.uniform(0,.12)),(s,s*.85,s*.8),stone,seed+row*5+col)


def enclosure(g, *, limestone):
    # A closed room behind the public ground arch, alongside the working bay.
    front=1.12
    for x in (.30,1.55):
        for y in (front,3.70):
            timber_column(g,x,y,.05,2.13 if y==front else 2.73,.22)
        outer=x+(-.0375 if x==.30 else .0375)
        for j in range(17):
            a=1.07+j*(3.74-1.07)/17;b=1.07+(j+1)*(3.74-1.07)/17
            za=2.13+(a-1.07)*(.59/(3.74-1.07));zb=2.13+(b-1.07)*(.59/(3.74-1.07))
            # Exterior boards meet the authored sloped curb edge exactly;
            # former flat-topped boxes overlapped its surface on every plank.
            g.add([(outer,a,0),(outer,b,0),(outer,b,zb),(outer,a,za)],
                  [(3,2,1,0) if x==.30 else (0,1,2,3)],PLANK)
    for j in range(9):
        a=.2625+j*1.325/9;b=.2625+(j+1)*1.325/9
        facade_panel(g,'Y',3.74,a,b,0,2.72,True,PLANK)
    # Door shoulders, solid head wall and narrow framed clerestory.
    for x in (.33,1.53):
        g.box((x,front,.50),(.20,.10,1.00),PLANK)
    facade_panel(g,'Y',1.07,.2625,1.5875,1,2.13,False,PLANK)
    g.include_component(door_recipe('LimestonePit' if limestone else 'SandstonePit','Door.PitStoreDoor'))
    g.doorways.append({"name":"PitStoreDoor","position":[.93,front-.14,0]})
    window_y(g,.93,front-.05,1.96,0.5)
    for y in (2.05,3.05):
        side_window(g,.2625,y,1.65,1,'left')
    window_y(g,.93,3.74,1.88,1,'back')
    for x in (.30,1.55):
        g.box((x,2.42,.30),(.12,2.70,.48),CIVIC_FORGED_PANEL)
    lean_roof_curb(g,.2625,1.07,1.5875,3.74,2.13,2.72,1.00,3.86,2.25,2.93,.0225)
    sheet_roof(g,.16,.88,1.72,1.67,1.56,1.82,1302)
    cage_lamp(g,1.42,front-.18,1.55)
    # (2026-10-22: the limestone pit's side shelter and workbench stood
    # outside the wall line; removed with their footprint tiles.)


def hoist(g,parts,stone,*,limestone):
    x=3.70;back=3.60;end=2.35 if limestone else .95;top=HOIST_TOP
    g.box((x,back,.17),(.60,.62,.34),CIVIC_CONCRETE)
    timber_column(g,x,back,.34,top-.15,.28)
    beam_joint(g,(x,back+.35,top),(x,end-.18,top),.28,.30)
    g.beam((x,back,2.10),(x,2.0,top-.12),.15,mat=WOOD)
    g.beam((x,back,2.55),(x,back+.40,top),.12,mat=IRON)
    for yy in (end,back):
        for xx in (x-.18,x+.18):
            g.box((xx,yy,top),(.055,.33,.40),IRON)
        band(g,(x,yy,top),.17,.044,.11,IRON,'X',12,inner=True)
    # Winding spool, crank, ratchet and continuous cable over both sheaves.
    pivot=(3.13,3.47,1.40)
    spool=Geometry('Pit.Winch',pivot)
    prism(spool,pivot,.16,.65,WOOD,'X',12)
    for xx in (2.80,3.46):
        prism(spool,(xx,3.47,1.40),.29,.07,IRON,'X',12)
    # Each cable turn is its outer surface; between turns the drum shows as the groove.
    for i in range(15):
        prism(spool,(2.84+i*.04,3.47,1.40),.18,.028,IRON,'X',12,(False,False))
    wheel(spool,(2.69,3.47,1.40),.34,'X')
    spool.beam((2.60,3.47,1.40),(2.60,3.47,1.71),.055,mat=IRON)
    prism(spool,(2.48,3.47,1.71),.045,.26,WOOD,'X',6)
    parts.append((spool,'PIT_DRUM',1))
    for xx,bottom in ((2.75,0),(3.49,.34)):
        timber_column(g,xx,3.47,bottom,1.40,.16)
        g.box((xx,3.47,1.4),(.15,.34,.35),IRON)
    g.beam((3.13,3.47,1.56),(x,back,top+.15),.028,mat=IRON)
    g.beam((x,back,top+.15),(x,end,top+.15),.028,mat=IRON)
    # Moving basket and its four sling chains; cable grows from a fixed top.
    basket=Geometry('Pit.HoistedBasket',(x,end,1.25))
    stone_bin(basket,(x,end,1.25),(.66,.61,.55),stone,1400)
    for dx in (-.30,.30):
        for dy in (-.27,.27):
            basket.beam((x+dx,end+dy,1.82),(x,end,2.35),.022,mat=IRON)
    band(basket,(x,end,2.39),.08,.025,.055,IRON,'X',8,inner=True)
    parts.append((basket,'PIT_BASKET',1))
    rope=Geometry('Pit.HoistCable',(x,end,top-.10))
    prism(rope,(x,end,(top-.10+CABLE_BOTTOM)/2),.025,top-.10-CABLE_BOTTOM,IRON,'Z',6)
    parts.append((rope,'PIT_CABLE',1))
    # Pegboard and tools on the rear structure.
    g.box((4.00,back+.08,1.37),(.42,.09,1.20),PLANK)
    for xx in (3.88,4.08):
        g.beam((xx,back,.88),(xx,back,1.96),.038,mat=WOOD)
        g.beam((xx-.15,back,1.82),(xx+.15,back,1.92),.075,.045,IRON)


def mineral_pit(g,parts,*,limestone):
    stone=LIME if limestone else SAND
    # Native paths remain at layer zero. The physical timber wearing surface
    # tops out at 20mm, above the native terrain mesh's measured 10mm peaks,
    # without raising the doorway or buried joists.
    g.include_component(apron_recipe('LimestonePit' if limestone else 'SandstonePit'))
    enclosure(g,limestone=limestone)
    for x in (2.88,):
        for y in (1.12,3.70):
            timber_column(g,x,y,.03,2.17 if y<2 else 2.79,.22)
    for y,z in ((1.12,2.17),(3.70,2.79)):
        beam_joint(g,(.30,y,z),(2.88,y,z),.23,.25)
    for x in (.30,2.88):
        beam_joint(g,(x,1.12,2.17),(x,3.70,2.79),.18,.24)
        g.beam((x,3.68,1.33),(x,2.76,2.48),.12,mat=WOOD)
    sheet_roof(g,.13,1.00,3.05,3.86,2.25,2.93,1501 if limestone else 1502)
    stone_bin(g,(2.22,2.42,.08),(1.05,1.62,1.02),stone,1510)
    hoist(g,parts,stone,limestone=limestone)
    # (2026-10-22: the limestone hand cart, both pits' loose barrels and the
    # rear plank stack were loose props outside the wall line; removed.)
    if not limestone:
        for x in (1.78,2.94):
            for y in (.20,1.22):
                timber_column(g,x,y,0,.91,.17)
        for y in (.20,1.22):
            beam_joint(g,(1.78,y,.91),(2.94,y,.91),.16,.17)
        for x in (1.78,2.94):
            beam_joint(g,(x,.28,.91),(x,1.14,.91),.16,.17)
        for i in range(11):
            g.box((1.74+i*.109,.71,.93),(.025,.95,.035),IRON)
        for j in range(9):
            g.box((2.29,.27+j*.109,.95),(1.16,.025,.025),IRON)
        g.box((2.29,.71,.20),(1.05,.79,.08),PLANK)
        for y in (.25,1.17):
            g.box((2.29,y,.31),(1.18,.065,.22),PLANK)
        for x in (1.73,2.85):
            g.box((x,.71,.31),(.065,.855,.22),PLANK)
        for i in range(16):
            rock(g,(1.84+(i%4)*.28,.36+(i//4)*.23,.32),
                 (.23,.20,.12),stone,1600+i)
        for i in range(3):
            rock(g,(1.90+i*.27,.95,1.03),(.21,.18,.16),stone,1640+i)
    return RailAssembly('PitRails')


def sandstone_pit(g,parts):
    return mineral_pit(g,parts,limestone=False)


def limestone_pit(g,parts):
    return mineral_pit(g,parts,limestone=True)


def animate_pit(obj,kind,frame_end):
    # Closed lift/lower cycle. Blender Z is height; native export preserves it.
    if frame_end!=121:
        raise ValueError('Pit hoist requires its authored 121-frame loop')
    base=obj.location.copy()
    for frame in range(1,122,5):
        lift=.35*(1-math.cos((frame-1)*2*math.pi/120))/2
        if kind=='PIT_DRUM':
            obj.rotation_euler.x=lift/.18
            obj.keyframe_insert(data_path='rotation_euler',frame=frame)
        elif kind=='PIT_BASKET':
            obj.location.z=base.z+lift
            obj.keyframe_insert(data_path='location',frame=frame)
        elif kind=='PIT_CABLE':
            obj.scale.z=1-lift/(HOIST_TOP-.10-CABLE_BOTTOM)
            obj.keyframe_insert(data_path='scale',frame=frame)
        else:
            raise ValueError('Unknown pit motion '+kind)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation='LINEAR'
