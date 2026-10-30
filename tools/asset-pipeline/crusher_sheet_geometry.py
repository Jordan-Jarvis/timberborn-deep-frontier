"""Stone crusher authored against 02-concrete-production-concept-v1.png.

Coordinates describe the artwork, not a game tile envelope. This module does
not read blueprints or scale the model to a footprint.
"""
import math
import random
from frontier_architecture import *
from reference_materials import CRUSHER_STEEL
from reference_details import cage_lamp, cask


from industrial_geometry import steel_bolt,bracket,timber_column,beam_joint,handrail,sheet_roof,access_stair
from industrial_kit import (open_beam,lean_wheel as wheel,lean_gauge as gauge)
from industrial_kit import (steel_bolt,lean_bracket as bracket,lean_timber_column as timber_column,lean_beam_joint as beam_joint,lean_sheet_roof as sheet_roof,lean_cage_lamp as cage_lamp,lean_cask as cask,lean_bin as bin,band,prism,bolt,square_nut,open_box,lean_rock as rock,lean_rock_heap as rock_heap,lean_wall as wall,skin_board)
from walkway_geometry import RailAssembly
from crusher_workshop_details import workshop_details,worn_surfaces,ROLL_ROOF,ROLL_ROOF_POST,HOPPER_ROOF
from industrial_door_components import recipe as door_recipe
from factory_facade_details import crusher_facades
from opaque_shell_geometry import lean_roof_curb
from factory_registration import RigidPlacement,flagstone_slab
from industrial_levels import (CRUSHER_DECK as DECK_Z,CRUSHER_MACHINE_DATUM,
                               FACTORY_ENTRANCE as ENTRY_Z,FACTORY_PORCH_ROOF as PORCH_Z)


def pillow_block(g,x,y,z):
    # Split bearing housing, saddle and projecting keyed shaft. (12k cap: no
    # base nuts or inner brass ring; 10/8 sides.)
    g.box((x,y,z-.19),(.35,.32,.10),IRON)
    g.box((x,y,z-.075),(.26,.26,.16),IRON)
    prism(g,(x,y,z),.143,.24,IRON,'Y',10)
    band(g,(x,y-.132,z),.134,.025,.033,CRUSHER_STEEL,'Y',10)
    prism(g,(x,y-.19,z),.071,.10,CRUSHER_STEEL,'Y',8)
    g.box((x,y-.19,z+.069),(.035,.09,.022),IRON)
    # Its ends are inside the bearing cylinder and the oil cup above it.
    prism(g,(x,y,z+.157),.022,.047,BRASS,'Z',6,(False,False))

def toothed_roller(g,p,phase):
    x,y,z=p;r=.315;length=1.77
    prism(g,p,r,length,IRON,'Y',16)
    # Shaft ends stop 5 mm inside the bearing housings' faces.
    prism(g,p,.075,length+.64,CRUSHER_STEEL,'Y',6)
    # Separate wear segments carry broad rectangular teeth. Bronze collars
    # divide the segments as in the sheet's machinery close-up. (12k cap:
    # eight teeth per segment straight on the roll, no segment bands.)
    for row in range(7):
        yy=y-.76+row*.252
        for i in range(8):
            a=(i+phase+(row%2)*.5)*2*math.pi/8
            radial=Vector((math.cos(a),0,math.sin(a)));tangent=Vector((-math.sin(a),0,math.cos(a)))
            center=Vector((x,yy,z));verts=[]
            for rr,ww in ((r-.007,.112),(r+.095,.090)):
                for dy in (-.073,.073):
                    for side in (-1,1):verts.append(center+radial*rr+tangent*ww*side/2+Vector((0,dy,0)))
            g.add(verts,[(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)],CRUSHER_STEEL)
    for yy in (y-.91,y-.24,y+.91):
        band(g,(x,yy,z),r+.028,.04,.065,BRASS,'Y',16)
    for yy in (y-.96,y+.96):
        prism(g,(x,yy,z),.249,.065,IRON,'Y',12)
        band(g,(x,yy,z),.265,.022,.08,CRUSHER_STEEL,'Y',12)

def flywheel(g,p):
    # 12k cap: one 16-sided rim (the side lips, inner ring and rim nuts went).
    x,y,z=p;r=.665
    band(g,p,r,.105,.21,IRON,'Y',16,inner=True)
    prism(g,p,.14,.29,IRON,'Y',10)
    for i in range(6):
        a=i*math.pi/3
        for j in range(3):
            r0=.11+j*.15;r1=r0+.16;a0=a+j*.045;a1=a+(j+1)*.045
            g.beam((x+math.cos(a0)*r0,y,z+math.sin(a0)*r0),
                   (x+math.cos(a1)*r1,y,z+math.sin(a1)*r1),.135-j*.018,.12,IRON)
    prism(g,(x,y-.22,z),.095,.25,CRUSHER_STEEL,'Y',8)
    band(g,(x,y-.29,z),.115,.025,.045,BRASS,'Y',8)

def hopper(g):
    x0,x1,y0,y1=.13,1.64,1.93,3.58
    bx0,bx1,by0,by1=.37,1.45,2.14,3.40;bottom,top=2.62,3.18
    g.add([(bx0,by0,bottom),(bx1,by0,bottom),(bx1,by1,bottom),(bx0,by1,bottom),
           (x0,y0,top),(x1,y0,top),(x1,y1,top),(x0,y1,top)],
          [(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],IRON)
    for row in range(3):
        t=(row+.5)/3;z=bottom+(top-bottom)*t
        a=bx0+(x0-bx0)*t;b=bx1+(x1-bx1)*t;c=by0+(y0-by0)*t;d=by1+(y1-by1)*t
        for y in (c,d):g.box(((a+b)/2,y,z),(b-a+.07,.075,.172),PLANK)
        for x in (a,b):g.box((x,(c+d)/2,z),(.075,d-c-.075,.172),PLANK)
    for x in (x0,x1):g.box((x,(y0+y1)/2,top),(.14,y1-y0+.13,.12),WOOD)
    for y in (y0,y1):g.box(((x0+x1)/2,y,top),(x1-x0-.14,.14,.12),WOOD)
    for x,y in ((x0,y0),(x1,y0),(x0,y1),(x1,y1)):
        bracket(g,x,y,top-.11,.15)
        open_box(g,(x,y,top+.065),(.20,.20,.022),IRON,('-z',))
    g.box((.88,2.73,2.96),(1.17,1.31,.12),LIME)
    # 12k cap: a load of nine large stones (was twenty).
    rng=random.Random(830)
    for j in range(3):
        for i in range(3):
            x=.47+i*.40+rng.uniform(-.04,.04);y=2.26+j*.42+rng.uniform(-.05,.05);s=rng.uniform(.34,.46)
            rock(g,(x,y,3.05+rng.uniform(-.02,.10)),(s,s*.82,s*.84),LIME,i+j*5+700)
    g.add([(1.48,2.16,2.69),(1.48,3.24,2.69),(2.35,3.24,2.47),(2.35,2.16,2.47)],
          [(0,1,2,3),(3,2,1,0)],IRON)
    for yy in (2.15,3.25):g.beam((1.48,yy,2.75),(2.35,yy,2.53),.045,.13,IRON)
    for y in (2.10,3.40):
        g.beam((.25,y,2.57),(1.49,y,2.57),.14,mat=WOOD)
        g.beam((.25,y,1.72),(.95,y,2.58),.115,mat=WOOD)

# Native grid frame: the layout origin is (0,0,0), so the numbers below are
# grid XY. The reviewed machinery, hopper, roofs and fittings were authored in
# the earlier artwork frame and are placed rigidly by LEGACY (no scaling).
LEGACY=(1.30,1.71,0)
# The porch and door assembly keep their reviewed shape; +0.09 X centres the
# native door on tile column 2 (x=2.5). Its face stays 0.10 behind y=2.
PORCH=(LEGACY[0]+.09,LEGACY[1],0)
# Lower room, outer frame faces on tile edges: west x=1 and east x=5 face the
# open bays under the side walkways, rear y=6 faces the bay under the rear
# walkway. Plank infill sits 0.05 behind the frame face.
ROOM_W,ROOM_E,ROOM_FRONT,ROOM_REAR=1.0,5.0,2.97,6.0
MID_COLUMN=3.04


def room(g):
    """Enclosed lower workshop under the walking deck, in grid coordinates."""
    xs=(ROOM_W+.12,MID_COLUMN,ROOM_E-.12)
    ys=(ROOM_FRONT,ROOM_REAR-.12)
    for x in xs:
        for y in ys:timber_column(g,x,y,.09,DECK_Z-.05,.20)
    beam_joint(g,(xs[0],ys[1],DECK_Z-.25),(xs[2],ys[1],DECK_Z-.25),.21,.21)
    beam_joint(g,(xs[0],ROOM_FRONT,DECK_Z-.30),(2.71,ROOM_FRONT,DECK_Z-.30),.18,.18)
    # The upper lintel sits .012 proud of the post line so its end plate
    # clears the middle post's collar fasteners.
    beam_joint(g,(2.71,ROOM_FRONT-.012,DECK_Z-.25),(xs[2],ROOM_FRONT-.012,DECK_Z-.25),.21,.21)
    for x in xs:
        # Upper side beams sit .01 lower so their end plates clear the ceiling boards.
        for z in (.24,DECK_Z-.26):beam_joint(g,(x,ys[0],z),(x,ys[1],z),.17,.18)
    # West plank skin (face x=1.05) and its two exterior braces on the frame face.
    count=16;y0,y1=ys[0]+.10,ys[1]-.10
    for j in range(count):
        y=y0+(j+.5)*(y1-y0)/count
        skin_board(g,(ROOM_W+.0875,y,(.255+DECK_Z-.235)/2),(.075,(y1-y0)/count,DECK_Z-.49),'Y',j,count,PLANK,'+x')
    for a,b in (((ROOM_W+.045,3.09,.34),(ROOM_W+.045,4.35,DECK_Z-.30)),((ROOM_W+.045,4.50,DECK_Z-.30),(ROOM_W+.045,5.76,.34))):
        g.beam(a,b,.09,mat=WOOD)
    # Rear plank wall, outer face y=5.96; trim on the inside.
    wall(g,xs[0]+.08,ROOM_REAR-.075,xs[2]-.08,DECK_Z-.19,.23)
    # Front-left wall beside the porch (front face y=2.825).
    wall(g,xs[0]+.03,2.86,MID_COLUMN-.14,DECK_Z-.19,.22)
    # East exterior knee braces on the frame face (x=5).
    for yy in (4.15,4.89):g.beam((ROOM_E-.05,yy,.30),(ROOM_E-.05,yy+.40,DECK_Z-.30),.10,mat=WOOD)
    # Wall couplings: flanges stand 0.02-0.03 proud of the plank skin.
    for x in (ROOM_W+.10,ROOM_E-.10):
        prism(g,(x,4.58,.45),.13,.16,IRON,'X',8)
        band(g,(x,4.58,.45),.16,.035,.06,BRASS,'X',8)
    # The closed workshop: its walls, ceiling boards, the porch insert and the
    # dark output aperture seal it (ray-verified at build, enclosed_cull.py).
    g.declare_hidden_volume((ROOM_W+.12,3.02,.10),(ROOM_E-.11,ROOM_REAR-.105,DECK_Z-.18))


def porch(g):
    """Reviewed porch in its artwork frame; placed by PORCH."""
    # Native-style recessed arched portal. No furnished interior or mesh beaver.
    # Entrance floor 0, canopy underside 1, walking deck 2. Roof pitch and
    # joinery thickness remain detailed artwork inside the layer-1 roof band.
    for z in (.70,.85,1.00):g.box((.71,1.08,z),(.46,.04,.095),IRON)
    for x,positive in ((.525,False),(1.695,True)):
        facade_panel(g,'X',x,.38,1.14,ENTRY_Z,ENTRY_Z+1.08,positive,PLANK)
    for a,b in ((.525,.61),(1.61,1.695)):
        facade_panel(g,'Y',.39,a,b,ENTRY_Z,ENTRY_Z+1.08,False,PLANK)
    facade_panel(g,'Y',.51,.61,1.61,ENTRY_Z+1,ENTRY_Z+1.08,False,PLANK)
    # Since the machine floor is layer 1 (2026-10-30) the canopy's back edge
    # and right shoe stop short of the front roller bearings.
    lean_roof_curb(g,.525,.39,1.695,1.00,ENTRY_Z+1.08,ENTRY_Z+1.08,.32,1.02,PORCH_Z+.135,PORCH_Z+.385,.0225)
    for x in (.48,1.74):timber_column(g,x,.41,ENTRY_Z,PORCH_Z+.10,.14)
    sheet_roof(g,.38,.32,1.80,1.02,PORCH_Z+.135,PORCH_Z+.385,9)
    # The portal owns its doorstep; this apron meets its front edge.
    cage_lamp(g,1.60,.32,PORCH_Z-.18)


def housing_roof(g):
    """Concrete cap of the lower workshop, the floor the crushing machinery
    stands on (layer 2 top). It is not a walkway: no lanes, rails or posts.
    Outer edges are the room's tile edges (x=1, x=5, y=6); the crusher pit
    stays open around the rolls and the flywheel slot."""
    # Stone masonry, not concrete: the crusher unlocks before concrete exists
    # (user 2026-10-30).
    flagstone_slab(g,1,2.86,1.43,6,DECK_Z)
    flagstone_slab(g,1.43,5.14,5,6,DECK_Z)
    flagstone_slab(g,1.43,2.56,2.62,2.91,DECK_Z)
    flagstone_slab(g,2.62,2.65,5,3.20,DECK_Z)
    flagstone_slab(g,4.57,3.20,5,5.14,DECK_Z)


def discharge(g):
    # Explicit tray corners keep the broad bed across the material flow.
    a=Vector((2.38,1.85,DECK_Z+.19));b=Vector((2.80,.70,.86));half=.37
    left=Vector((half,0,0));up=Vector((0,0,.15));thick=Vector((0,0,.035))
    g.add([a-left,a+left,b+left,b-left,a-left-thick,a+left-thick,b+left-thick,b-left-thick],
          [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],IRON)
    for sign in (-1,1):
        g.add([a+left*sign,b+left*sign,b+left*sign+up,a+left*sign+up],[(0,1,2,3),(3,2,1,0)],CRUSHER_STEEL)
    # The chute-fed output bin stands in the porch line, its front 5 cm
    # behind the y=2 tile edge (no footprint row in front of the facade, 2026-10-22).
    bin(g,(2.80,.69,.12),(1.46,.70,.63),None)
    g.box((2.80,.69,.64),(1.29,.51,.09),LIME)
    rng=random.Random(103)
    for j in range(2):
        for i in range(4):
            s=rng.uniform(.24,.34)
            rock(g,(2.27+i*.35+rng.uniform(-.025,.025),.52+j*.32+rng.uniform(-.035,.035),.74+rng.uniform(-.02,.06)),(s,s*.85,s*.8),LIME,2100+i+j*8)
    for xx in (2.13,3.47):
        for yy in (.40,.97):bracket(g,xx,yy,.25,.12)
    for x in (2.05,3.52):g.beam((x,.91,.23),(x,1.26,DECK_Z-.11),.14,mat=WOOD)

def crusher(g,parts):
    static=g;art=RigidPlacement(g,LEGACY)
    machinery=RigidPlacement(g,(LEGACY[0],LEGACY[1],DECK_Z-CRUSHER_MACHINE_DATUM))
    # No walkways or balconies: the assembly stays empty (no rail manifest runs).
    rails=RailAssembly("WalkwayRail")
    room(g)
    g.include_component(door_recipe('StoneCrusher','Door.GroundDoor'))
    porch(RigidPlacement(g,PORCH))
    housing_roof(g)
    g=machinery
    for x in (1.96,2.79):
        g.box((x,2.25,1.56),(.23,2.25,.19),WOOD)
        for y in (1.17,3.30):
            g.box((x,y,1.76),(.34,.30,.25),WOOD)
            bracket(g,x,y,1.70,.30);pillow_block(g,x,y,2.00)
    for i,x in enumerate((1.96,2.79)):
        p=(x,2.25,2.00);m,node=machinery.moving_part('ReferenceCrusherRoller'+str(i+1),p)
        toothed_roller(m,p,i*.5);parts.append((node,'Y',1 if i==0 else -1))
    p=(.61,1.43,2.03);m,node=machinery.moving_part('ReferenceCrusherFlywheel',p)
    flywheel(m,p);parts.append((node,'Y',1))
    g.box((.61,.98,1.73),(.79,.31,.16),WOOD)
    for x in (.27,.94):
        g.box((x,.98,1.545),(.13,.13,.21),WOOD)
        bracket(g,x,.98,1.545,.13)
    pillow_block(g,.61,.99,2.03)
    # Driven chain loops are behind the front wheel and bearing pedestal.
    for x in (.61,1.96):
        p=(x,1.56,2.02);m,node=machinery.moving_part('ReferenceCrusherDriveSprocket'+str(x),p)
        prism(m,p,.205,.075,IRON,'Y',12)
        for i in range(12):
            a=i*2*math.pi/12
            open_beam(m,(x+math.cos(a)*.19,1.56,2.02+math.sin(a)*.19),(x+math.cos(a)*.228,1.56,2.02+math.sin(a)*.228),.043,.07,IRON)
        parts.append((node,'Y',1))
    # Chain runs: twelve links each (was 24 half-size links).
    for z in (1.81,2.23):
        for i in range(12):
            x=.6675+i*.11;open_box(g,(x,1.56,z),(.102,.078,.028),IRON,('-z',))
    for x in (.15,1.63):
        for y in (1.94,3.60):timber_column(g,x,y,1.48,3.19,.18)
    hopper(g)
    # Separate short roofs leave most roller teeth visible. The right-hand
    # posts and eave stay inside x=5, clear of the right walking lane.
    for x in (1.72,ROLL_ROOF_POST):
        # Level roof: both posts end under its eave beams.
        for y in (2.97,3.72):timber_column(g,x,y,1.49,ROLL_ROOF[4]-.135,.19)
        g.beam((x-.06,2.97,2.63),(x-.06,3.34,3.08),.105,mat=WOOD)
        g.beam((x+.06,3.72,2.65),(x+.06,3.27,3.08),.105,mat=WOOD)
    beam_joint(g,(1.72,2.97,3.02),(ROLL_ROOF_POST,2.97,3.02),.18,.18)
    sheet_roof(g,*ROLL_ROOF,44)
    sheet_roof(g,*HOPPER_ROOF,45)
    discharge(art)
    cask(art,(2.19,3.40,.18),.23,.54)
    for i in range(5):art.box((2.90,3.29,.25+i*.075),(.54,.47,.065),PLANK)
    for x in (.33,1.40):
        g.box((x,3.74,2.17),(.075,.06,.55),IRON)
    workshop_details(g,art,static)
    crusher_facades(static)
    worn_surfaces(g,art)
    return rails
