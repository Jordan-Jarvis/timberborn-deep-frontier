"""Small mineral yards from the mining sheet's two isometric pit drawings.

No top view or printed tile dimensions are used. Game registration follows the
finished geometry. The enclosed store room has one ground-level arch.

Compaction pass (2026-10-30): one storey under one flat roof below layer 2.
Second shrink pass (2026-11-01, user: "we need to shrink the buildings down
even more"): both pits are 3x3x3 (5x4 and 5x3 before). Same plan on both:
the one-tile store room with its door on grid tile column 1, the bay with the
stone bin in column 0, both under one flat roof, and the jib hoist in column
2 (post and winch at the back, its basket hanging over the yard floor in
front on the sandstone pit, over the open ground of the middle row on the
limestone pit). The sandstone pit's door stays set back behind its yard row
(sorting grate and approach floor under the roof); the limestone pit's
front-right cell is free ground. Authored in native grid XY through PitFrame:
artwork = grid - registration origin (pit_layouts.py).
"""
import math
import random

from frontier_architecture import Geometry, WOOD, PLANK, IRON, SAND, LIME, BRASS, deck, facade_panel
from industrial_facades import window_y, side_window
from industrial_door_components import recipe as door_recipe
from pit_apron_components import recipe as apron_recipe
# (No native props: the pits' loose barrels were removed, 2026-10-22.)
from industrial_kit import open_beam, wheel, gauge
from industrial_kit import (timber_column, beam_joint, bracket, steel_bolt, sheet_roof, cage_lamp, band, prism,
                               bolt, square_nut, open_box, rock, rock_heap)
from reference_materials import CIVIC_FORGED_PANEL
from industrial_kit import lean_plate_roof
from walkway_geometry import RailAssembly
from factory_registration import RigidPlacement

HOIST_TOP=2.62
CABLE_BOTTOM=1.73
# One-storey frame: posts and beams at BEAM_Z, walls to WALL_TOP, the flat
# roof sheets at ROOF_Z (their shoes stay under layer 2).
BEAM_Z=1.78
WALL_TOP=1.70
ROOF_Z=1.92

# Plan in native grid XY (both pits).
SHED_X=(.87,2.12)      # store room posts (column 1); door centred on x 1.5
SHED_REAR=2.88
ROOF_X=(.03,2.24)
ROOF_Y=(.03,2.97)
FRAME_X=(.12,2.12)     # roof frame posts: the west line and the shed's east line
FRAME_Y=(.12,2.88)
HOIST_X,HOIST_BACK=2.64,2.62
WINCH_Y,WINCH_Z=2.10,1.10


class PitFrame:
    """Grid -> artwork for one pit: artwork = grid - origin (pit_layouts.py)."""
    def __init__(self,limestone):
        from pit_layouts import LAYOUTS
        ox,oy,_=LAYOUTS['LimestonePit' if limestone else 'SandstonePit']['origin']
        self.offset=(-ox,-oy,0)
    def __call__(self,x,y):return x+self.offset[0],y+self.offset[1]


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


def enclosure(g, art, A, *, limestone):
    # A closed room behind the public ground arch, beside the bay. Its front
    # is the shed's front post line: grid y 1.12 on the sandstone pit (behind
    # its yard row), .12 on the limestone pit.
    front=.12 if limestone else 1.12
    x0,x1=SHED_X
    for x in (x0,x1):
        for y in (front,SHED_REAR):
            timber_column(g,x,y,.05,BEAM_Z,.22)
        outer=x+(-.0375 if x==x0 else .0375)
        n=max(6,round((SHED_REAR-front)*6))
        a0,a1=front-.05,SHED_REAR+.04
        for j in range(n):
            a=a0+j*(a1-a0)/n;b=a0+(j+1)*(a1-a0)/n
            facade_panel(g,'X',outer,a,b,0,WALL_TOP,x!=x0,PLANK)
    for j in range(9):
        a=x0-.0375+j*1.325/9;b=x0-.0375+(j+1)*1.325/9
        facade_panel(g,'Y',SHED_REAR+.04,a,b,0,WALL_TOP,True,PLANK)
    # Door shoulders and a solid head wall to the roof beam.
    for x in (x0+.03,x1-.02):
        g.box((x,front,.50),(.20,.10,1.00),PLANK)
    facade_panel(g,'Y',front-.05,x0-.0375,x1+.0375,1,WALL_TOP,False,PLANK)
    ident='LimestonePit' if limestone else 'SandstonePit'
    art.include_component(door_recipe(ident,'Door.PitStoreDoor'))
    art.doorways.append({"name":"PitStoreDoor","position":[*A(1.5,front-.14),0]})
    side_window(art,*A(x0-.0375,(front+SHED_REAR)/2+.10),.95,.85,'left')
    window_y(art,*A(1.5,SHED_REAR+.04),.95,.85,'back')
    for x in (x0,x1):
        g.box((x,(front+SHED_REAR)/2,.30),(.12,SHED_REAR-front-.40,.48),CIVIC_FORGED_PANEL)
    cage_lamp(g,x1-.13,front-.18,1.30)


def sorting_grate(g,p,size,stone):
    """Sandstone sorting grate on its timber frame and plank tray (yard row)."""
    x,y=p;w,d=size
    for xx in (x-w/2,x+w/2):
        for yy in (y-d/2,y+d/2):
            timber_column(g,xx,yy,0,.91,.15)
    for yy in (y-d/2,y+d/2):
        beam_joint(g,(x-w/2,yy,.91),(x+w/2,yy,.91),.15,.16)
    for xx in (x-w/2,x+w/2):
        beam_joint(g,(xx,y-d/2+.08,.91),(xx,y+d/2-.08,.91),.15,.16)
    n=7
    for i in range(n):
        g.box((x-w/2+.06+i*(w-.12)/(n-1),y,.93),(.025,d-.12,.035),IRON)
    for j in range(6):
        g.box((x,y-d/2+.08+j*(d-.16)/5,.95),(w-.10,.025,.025),IRON)
    g.box((x,y,.20),(w-.10,d-.12,.08),PLANK)
    for yy in (y-d/2+.05,y+d/2-.05):
        g.box((x,yy,.31),(w,.065,.22),PLANK)
    for xx in (x-w/2+.04,x+w/2-.04):
        g.box((xx,y,.31),(.065,d-.10,.22),PLANK)
    for i in range(9):
        rock(g,(x-w/2+.16+(i%3)*(w-.32)/2,y-d/2+.16+(i//3)*(d-.32)/2,.32),
             (.21,.18,.11),stone,1600+i)
    for i in range(3):
        rock(g,(x-.20+i*.20,y+.10,1.03),(.19,.16,.15),stone,1640+i)


def hoist(g,parts,stone,*,limestone):
    x=HOIST_X;back=HOIST_BACK;end=1.40 if limestone else .55;top=HOIST_TOP
    # Timber sill under the hoist post: a pit shows only wood and metal (it
    # cannot cost the stone its own chain produces; user 2026-10-30).
    g.box((x,back,.17),(.56,.56,.34),WOOD)
    timber_column(g,x,back,.34,top-.15,.28)
    beam_joint(g,(x,back+.30,top),(x,end-.18,top),.28,.30)
    # The jib brace meets the jib clear of the basket's lifted slings.
    g.beam((x,back,1.50),(x,max(end+.45,1.75),top-.12),.15,mat=WOOD)
    g.beam((x,back,1.70),(x,back+.30,top),.12,mat=IRON)
    for yy in (end,back):
        for xx in (x-.18,x+.18):
            g.box((xx,yy,top),(.055,.33,.40),IRON)
        band(g,(x,yy,top),.17,.044,.11,IRON,'X',12,inner=True)
    # Winding spool in front of the post, crank on its east side, and the
    # continuous cable over both sheaves.
    pivot=(2.52,WINCH_Y,WINCH_Z)
    spool,node=g.moving_part('Pit.Winch',pivot)
    prism(spool,pivot,.16,.45,WOOD,'X',12)
    for xx in (2.30,2.74):
        prism(spool,(xx,WINCH_Y,WINCH_Z),.29,.06,IRON,'X',12)
    # Each cable turn is its outer surface; between turns the drum shows as the groove.
    for i in range(9):
        prism(spool,(2.36+i*.04,WINCH_Y,WINCH_Z),.18,.028,IRON,'X',12,(False,False))
    # The handwheel outside the east bearing (no crank: it would pass the
    # x=3 edge).
    wheel(spool,(2.92,WINCH_Y,WINCH_Z),.24,'X')
    parts.append((node,'PIT_DRUM',1))
    for xx in (2.215,2.83):
        timber_column(g,xx,WINCH_Y,0,WINCH_Z-.16,.11)
        g.box((xx,WINCH_Y,WINCH_Z-.08),(.10,.30,.16),IRON)
    g.beam((2.52,WINCH_Y,WINCH_Z+.16),(x,back,top+.15),.028,mat=IRON)
    g.beam((x,back,top+.15),(x,end,top+.15),.028,mat=IRON)
    # Moving basket and its four sling chains; cable grows from a fixed top.
    p=(x,end,.55)
    basket,node=g.moving_part('Pit.HoistedBasket',p)
    # Clear of the roof's east frame post (x 2.12 +.11).
    stone_bin(basket,p,(.54,.54,.55),stone,1400)
    for dx in (-.24,.24):
        for dy in (-.23,.23):
            basket.beam((x+dx,end+dy,1.12),(x,end,1.65),.022,mat=IRON)
    band(basket,(x,end,1.69),.08,.025,.055,IRON,'X',8,inner=True)
    parts.append((node,'PIT_BASKET',1))
    p=(x,end,top-.10)
    rope,node=g.moving_part('Pit.HoistCable',p)
    prism(rope,(x,end,(top-.10+CABLE_BOTTOM)/2),.025,top-.10-CABLE_BOTTOM,IRON,'Z',6)
    parts.append((node,'PIT_CABLE',1))


def mineral_pit(g,parts,*,limestone):
    stone=LIME if limestone else SAND
    A=PitFrame(limestone)
    P=RigidPlacement(g,A.offset)
    # Native paths remain at layer zero. The physical timber wearing surface
    # tops out at 20mm, above the native terrain mesh's measured 10mm peaks,
    # without raising the doorway or buried joists.
    g.include_component(apron_recipe('LimestonePit' if limestone else 'SandstonePit'))
    enclosure(P,g,A,limestone=limestone)
    # Roof frame: the west posts and the shed's east posts carry the beams
    # (where the shed has a post on that line, it carries the beam).
    shed_front=.12 if limestone else 1.12
    for x in FRAME_X:
        for y in FRAME_Y:
            if x==SHED_X[1] and y in (SHED_REAR,shed_front):continue
            timber_column(P,x,y,.03,BEAM_Z,.22)
    for y in FRAME_Y:
        beam_joint(P,(FRAME_X[0],y,BEAM_Z),(FRAME_X[1],y,BEAM_Z),.23,.25)
    for x in FRAME_X:
        beam_joint(P,(x,FRAME_Y[0],BEAM_Z),(x,FRAME_Y[1],BEAM_Z),.18,.24)
    P.beam((FRAME_X[0],FRAME_Y[1]-.02,.95),(FRAME_X[0],FRAME_Y[1]-.65,1.70),.12,mat=WOOD)
    # One flat roof over the store and the bay: native roof sheets on the
    # sandstone pit, riveted steel plate on the limestone pit (roof variety,
    # user 2026-10-30).
    if limestone:
        lean_plate_roof(P,ROOF_X[0],ROOF_Y[0],ROOF_X[1],ROOF_Y[1],ROOF_Z,CIVIC_FORGED_PANEL)
    else:
        sheet_roof(P,ROOF_X[0],ROOF_Y[0],ROOF_X[1],ROOF_Y[1],ROOF_Z,ROOF_Z,1502)
    # The bay's stone bin (column 0) and the sandstone yard's sorting grate.
    stone_bin(P,(.42,1.98,.08),(.58,1.42,1.02),stone,1510)
    if not limestone:
        sorting_grate(P,(.50,.64),(.56,.62),stone)
    hoist(P,parts,stone,limestone=limestone)
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
