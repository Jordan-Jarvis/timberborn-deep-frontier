"""Cement kiln from Cement Kiln 3D Reference Sheet.png.

Only Front Left, Front Right and Back Left isometric illustrations are sources.
The roof covers the rotary kiln. Build coherent access around the covered hall,
raised feed bins, lower fuel bays, porch and masonry firebox. No characters,
plan views, orthographic elevations, exploded diagrams or tile labels are used.
"""
import math
import random
from frontier_architecture import *
from industrial_geometry import timber_column,bracket,beam_joint,handrail,sheet_roof,steel_bolt,access_stair
from reference_details import cage_lamp,cask,round_pipe
from industrial_kit import (open_beam,lean_wheel as wheel,lean_gauge as gauge)
from industrial_kit import (lean_timber_column as timber_column,lean_bracket as bracket,lean_beam_joint as beam_joint,lean_sheet_roof as sheet_roof,steel_bolt,lean_cage_lamp as cage_lamp,lean_cask as cask,round_pipe,lean_bin as bin,band,prism,bolt,square_nut,open_box,lean_rock as rock,lean_rock_heap as rock_heap,lean_wall as wall,skin_board)
from walkway_geometry import RailAssembly
from industrial_door_components import recipe as door_recipe
from factory_facade_details import kiln_facades
from opaque_shell_geometry import lean_roof_curb
from factory_registration import machine_slab
from industrial_levels import (KILN_DECK as DECK_Z,KILN_MACHINE_DATUM,MountedMachinery,
                               FACTORY_ENTRANCE as ENTRY_Z,FACTORY_PORCH_ROOF as PORCH_Z)
from reference_materials import (CRUSHER_STEEL,KILN_STONE,KILN_STONE_LIGHT,KILN_SOOT,
                                KILN_EMBER,KILN_FLAME,KILN_CEMENT,KILN_SHELL,
                                KILN_RUST,KILN_WOOD_SPLIT,KILN_WOOD_WEAR,KILN_DUST)


def kiln_barrel(g,p):
    x,y,z=p
    # 12k cap (2026-10-29): 16-sided shell, plates and hoops; one hoop band
    # per tyre side; no rivet rows (sub-pixel heads); 24-tooth drive ring.
    # The core shows only through the plate joints and at the ends.
    prism(g,p,.492,4.70,IRON,'X',16)
    # Discrete curved plates, dark joints and broad wearing tyres.
    # Each plate is its outer skin: its 16 mm edges sit under the hoops or
    # over the core, and its inner face is inside the core.
    for course in range(10):
        xa=x-2.35+course*.47;xb=xa+.457
        radius=(.497,.516,.523,.523,.523,.523,.523,.523,.516,.497)[course]
        for sector in range(16):
            a0=(sector+.025)*math.tau/16;a1=(sector+.975)*math.tau/16
            vertices=[(xx,y+math.cos(a)*rr,z+math.sin(a)*rr)
                      for xx in (xa,xb) for rr in (radius-.016,radius) for a in (a0,a1)]
            g.add(vertices,[(2,3,7,6)],KILN_SHELL)
    for xx in (1.31,3.48,5.13):
        band(g,(xx,y,z),.59,.082,.17,IRON,'X',16)
    for xx in (.91,5.64):
        prism(g,(xx,y,z),.45,.065,IRON,'X',16)
    # Bolted inspection covers travel with the shell.
    for xx in (2.68,4.80):
        verts=[(a,y+math.cos(b)*.548,z+math.sin(b)*.548)
               for a in (xx-.16,xx+.16) for b in (math.pi-.22,math.pi+.22)]
        g.add(verts,[(0,1,3,2),(2,3,1,0)],IRON)
    prism(g,(.79,y,z),.14,.32,IRON,'X',8)
    band(g,(.70,y,z),.183,.04,.12,BRASS,'X',8)
    # A toothed drive ring near the feed end, integral with the rotating shell.
    band(g,(1.06,y,z),.56,.07,.085,IRON,'X',24)
    for i in range(24):
        a=i*math.tau/24
        open_beam(g,(1.06,y+math.cos(a)*.55,z+math.sin(a)*.55),
                  (1.06,y+math.cos(a)*.605,z+math.sin(a)*.605),.072,.055,IRON)

def axle_bearing(g,x,y,z):
    g.box((x,y,z-.11),(.30,.34,.10),IRON)
    prism(g,(x,y,z),.13,.27,IRON,'X',6)

def mechanics(g,parts):
    p=(3.27,2.14,2.04);m,node=g.moving_part('ReferenceKilnBarrel',p)
    kiln_barrel(m,p);parts.append((node,'X',1))
    # Carrier rollers sit on saddles that transfer the load to cross-members.
    for j,x in enumerate((1.31,3.48,5.13)):
        g.box((x,2.14,1.25),(.28,1.69,.21),WOOD)
        # .62 lateral / .51 vertical offset keeps rollers tangent to the tyres.
        for k,y in enumerate((1.52,2.76)):
            g.box((x,y,1.42),(.46,.38,.20),WOOD)
            for xx in (x-.20,x+.20):axle_bearing(g,xx,y,1.53)
            p=(x,y,1.53);m,node=g.moving_part(f'ReferenceKilnSupport{j+1}{k+1}',p)
            prism(m,p,.19,.34,IRON,'X',10)
            # Visible keyed wheel face makes its rotation legible.
            for i in range(3):
                a=i*math.tau/3;square_nut(m,(x-.19,y+math.cos(a)*.12,1.53+math.sin(a)*.12),'X',.015,-1)
            parts.append((node,'X',-3))
        # Screw adjuster and locking nut on the forward support saddle.
        prism(g,(x,1.43,1.40),.034,.38,IRON,'Y',6)
        g.cylinder((x,1.26,1.40),.062,.055,IRON,'Y',6)
    # Exposed small reduction gear, drive shaft and flywheel in the left bay.
    p=(1.06,1.46,1.62);m,node=g.moving_part('ReferenceKilnPinion',p)
    prism(m,p,.164,.12,IRON,'X',12)
    for i in range(12):
        a=i*math.tau/12
        open_beam(m,(p[0],p[1]+math.cos(a)*.15,p[2]+math.sin(a)*.15),
                  (p[0],p[1]+math.cos(a)*.199,p[2]+math.sin(a)*.199),.068,.051,IRON)
    prism(m,(.70,1.46,1.62),.065,.80,CRUSHER_STEEL,'X',6)
    parts.append((node,'X',-3))
    g.box((.55,1.46,1.34),(.71,.49,.15),WOOD)
    for xx in (.29,.83):axle_bearing(g,xx,1.46,1.62)
    p=(.24,1.46,1.62);m,node=g.moving_part('ReferenceKilnDriveWheel',p)
    band(m,p,.32,.07,.095,IRON,'X',16,inner=True)
    prism(m,p,.095,.18,IRON,'X',8)
    for i in range(6):
        a=i*math.pi/3;m.beam(p,(.24,1.46+math.cos(a)*.28,1.62+math.sin(a)*.28),.057,mat=IRON)
    parts.append((node,'X',-3))

def feed_bin(g,y,bottom,seed):
    x0,x1=.14,1.53;y0,y1=y-.49,y+.49;top=bottom+.47
    for row in range(3):
        t=(row+.5)/3;z=bottom+.47*t;a=x0+.12*(1-t);b=x1-.12*(1-t)
        # The two lower courses' inner faces lie under the stone fill.
        under=row<2
        for yy in (y0+.08*(1-t),y1-.08*(1-t)):
            open_box(g,((a+b)/2,yy,z),(b-a+.06,.075,.145),PLANK,(('+y' if yy<y else '-y'),) if under else ())
        for xx in (a,b):
            open_box(g,(xx,y,z),(.075,.905-.16*(1-t),.145),PLANK,(('+x' if xx<.835 else '-x'),) if under else ())
    g.box((.835,y,bottom+.30),(1.08,.76,.13),LIME)
    rng=random.Random(seed)
    for i in range(3):
        s=rng.uniform(.34,.44)
        rock(g,(rng.uniform(.34,1.30),rng.uniform(y-.32,y+.32),bottom+.39+rng.uniform(-.035,.07)),(s,s*.80,s*.76),LIME,seed+i)
    for yy in (y0,y1):g.box((.835,yy,top),(1.26,.14,.12),WOOD)
    for xx in (x0,x1):g.box((xx,y,top),(.13,1.06,.12),WOOD)
    for xx in (x0,x1):
        for yy in (y0,y1):
            open_box(g,(xx,yy,top+.063),(.19,.19,.02),IRON,('-z',))

def feed_tower(g,ground):
    for x in (.20,1.55):
        for y,top in ((1.28,3.14),(3.33,3.45)):timber_column(ground,x,y,.12,top+DECK_Z-KILN_MACHINE_DATUM,.19,top_collar_only=True)
        for z in (1.25,2.72):beam_joint(g,(x,1.28,z),(x,3.33,z),.18,.18)
        g.beam((x,1.35,1.45),(x,2.33,2.68),.105,mat=WOOD)
        g.beam((x,3.30,1.45),(x,2.42,2.68),.105,mat=WOOD)
    for y in (1.28,3.33):beam_joint(g,(.29,y,2.72),(1.46,y,2.72),.18,.14)
    feed_bin(g,1.79,2.68,701);feed_bin(g,2.84,2.94,771)
    # Gravity feed terminates at the left end of the drum under the sorting bay.
    g.add([(.45,1.52,2.70),(1.31,1.52,2.70),(1.31,2.12,2.70),(.45,2.12,2.70),
           (.67,1.98,2.13),(.88,1.98,2.13),(.88,2.30,2.13),(.67,2.30,2.13)],
          [(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],IRON)
    # The rear bin has its own enclosed inclined feed into the same inlet.
    a=Vector((.78,2.84,2.94));b=Vector((.78,2.20,2.33))
    side=Vector((.25,0,0));up=Vector((0,0,.22))
    g.add([a-side,a+side,b+side,b-side,a-side+up,a+side+up,b+side+up,b-side+up],
          [(0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5)],IRON)
    for t in (.15,.50,.85):
        p=a+(b-a)*t+up
        g.beam(p-side,p+side,.035,.025,BRASS)

def fuel_logs(g):
    rng=random.Random(17)
    # 12k cap: fifteen logs in three rows (was 21 slightly thinner logs).
    for row in range(3):
        for i in range(6-row):
            x=.42+i*.29+row*.145;z=.25+row*.225;r=rng.uniform(.115,.135)
            prism(g,(x,1.80,z),r,1.16,WOOD,'Y',6,(False,True))
            prism(g,(x,1.206,z),r*.88,.025,PLANK,'Y',6,(True,False))
    for x in (.22,2.17):
        g.box((x,1.25,.49),(.11,.11,.76),WOOD)
        g.box((x,1.25,.19),(.16,.16,.12),IRON)
    # The sill's top stays 1 cm under the post feet's caps (no shared plane).
    g.box((1.18,1.25,.175),(1.79,.12,.13),WOOD)

# Kiln artwork X/Y = native grid X/Y minus the layout origin (1,2): grid x=k
# is artwork x=k-1, grid y=k is artwork y=k-2. Outer deck edges, rails,
# walkway posts and the control room walls are on those tile lines.
# The control room and porch are exactly one tile wide (grid x 4..5) with the
# native door centred on it; the door face is 0.14 behind the y=1 tile edge.
ROOM_X0,ROOM_X1=3.0,4.0
ROOM_FRONT=.2405
DOOR_X,DOOR_Y=3.50,-.86


def porch(g):
    # Entrance floor 0, canopy underside 1, walking deck 2. The pitched
    # canopy projects outside the layer-2 route and is not a walking surface.
    for x in (DOOR_X-.65,DOOR_X+.65):timber_column(g,x,DOOR_Y+.01,ENTRY_Z,PORCH_Z+.10,.15)
    g.include_component(door_recipe('CementKiln','Door.GroundDoor'))
    for x in (DOOR_X-.555,DOOR_X+.555):g.box((x,DOOR_Y+.05,ENTRY_Z+.58),(.11,.08,1.00),PLANK)
    # Eave and corner shoes stay inside the y=1 tile edge (artwork y=-1).
    # The eave beam's underside stays 5 mm above the door insert's top cap.
    sheet_roof(g,DOOR_X-.77,DOOR_Y-.03,DOOR_X+.77,.28,PORCH_Z+.14,PORCH_Z+.38,235)
    for x in (ROOM_X0,ROOM_X1):
        g.beam((x,DOOR_Y+.01,PORCH_Z+.10),(x,.26,PORCH_Z+.10),.12,mat=WOOD)
    # Side walls meet the door insert edges and stop at the room's front plank.
    for x,positive in ((ROOM_X0,False),(ROOM_X1,True)):
        facade_panel(g,'X',x,DOOR_Y-.03,ROOM_FRONT,ENTRY_Z,ENTRY_Z+1.08,positive,PLANK)
    facade_panel(g,'Y',DOOR_Y+.12,ROOM_X0,ROOM_X1,ENTRY_Z+1,ENTRY_Z+1.08,False,PLANK)
    lean_roof_curb(g,ROOM_X0,DOOR_Y,ROOM_X1,.28,ENTRY_Z+1.08,ENTRY_Z+1.08,DOOR_Y-.03,.28,PORCH_Z+.14,PORCH_Z+.38,.0225)
    cage_lamp(g,DOOR_X+.46,-.78,PORCH_Z-.18)

def structure(g,rails,machinery):
    ground=g
    # No walkways or balconies: the drum, saddles and feed bins stand on the
    # timber hall frame and the masonry firebox. The control room gets a
    # concrete cap (grid x 4..5) instead of the former walkway above it.
    machine_slab(g,ROOM_X0+.01,ROOM_FRONT,ROOM_X1-.01,3.30,DECK_Z-.04,.16)
    for x in (.20,5.65):
        g.beam((x,2.16,.21),(x,3.25,DECK_Z-.20),.12,mat=WOOD)
    for x in (1.58,3.15,4.60,5.65):
        for y,top in ((1.30,3.00),(3.25,3.42)):timber_column(g,x,y,.09,top+DECK_Z-KILN_MACHINE_DATUM,.20,top_collar_only=True)
    g=machinery
    for x in (1.58,3.15,4.60,5.65):
        beam_joint(g,(x,1.41,1.18),(x,3.14,1.18),.19,.21)
        g.beam((x,1.30,2.55),(x,1.73,3.09),.11,mat=WOOD)
        g.beam((x,3.25,2.98),(x,2.85,3.32),.11,mat=WOOD)
    for y in (1.30,3.25):
        beam_joint(g,(.20,y,1.18),(5.65,y,1.18),.22,.23)
        beam_joint(g,(1.58,y,2.97 if y<2 else 3.39),(5.65,y,2.97 if y<2 else 3.39),.20,.20)
    wall(ground,ROOM_X0+.0375,3.30,ROOM_X1-.0375,DECK_Z-.20,.20)
    for x in (1.65,3.15,4.65):g.beam((x,3.30,1.42),(x+.8,3.30,2.97),.11,mat=WOOD)
    # The large continuous canopy covers the whole main rotary barrel.
    sheet_roof(g,1.44,1.15,5.80,3.40,3.06,3.50,521)
    # Low roof monitor, with open black interior and timber-framed metal louvres.
    g.box((3.08,2.38,3.46),(.76,.53,.28),KILN_SOOT)
    for x in (2.70,3.46):
        for y in (2.12,2.64):g.box((x,y,3.46),(.09,.09,.36),WOOD)
    for z in (3.35,3.44,3.53):
        g.box((3.08,2.075,z),(.67,.035,.035),IRON)
        g.box((3.08,2.685,z),(.67,.035,.035),IRON)
    sheet_roof(g,2.63,2.04,3.53,2.72,3.65,3.77,522)

def masonry(g,p,size,index):
    # Small authored differences keep masonry from reading as a perfect tile grid.
    rng=random.Random(round(p[0]*1000+p[1]*390+p[2]*167))
    size=tuple(v-rng.uniform(.001,.012) for v in size)
    # Its underside lies on the course below (12k cap).
    open_box(g,p,size,KILN_STONE_LIGHT if index%7==0 else KILN_STONE,('-z',))

def arch(g,cx,y,cz,inner,outer):
    for i in range(11):
        a0=i*math.pi/11+.012;a1=(i+1)*math.pi/11-.012
        verts=[(cx+math.cos(a)*r,yy,cz+math.sin(a)*r)
               for yy in (y-.07,y+.11) for r in (inner,outer) for a in (a0,a1)]
        g.add(verts,[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)],KILN_STONE_LIGHT if i%3==0 else KILN_STONE)

def flame(g,p,h,seed):
    rng=random.Random(seed);x,y,z=p;n=7;verts=[]
    for zz,r,dx in ((0,.095,0),(.22*h,.12,.025),(.58*h,.073,-.018),(h,.003,.045)):
        for i in range(n):
            a=i*math.tau/n;verts.append((x+math.cos(a)*r+dx,y+math.sin(a)*r*.65,z+zz))
    faces=[tuple(reversed(range(n))),tuple(range(3*n,4*n))]
    for j in range(3):
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    g.add(verts,faces,KILN_FLAME)

def firebox(g,parts):
    # A real recessed arched opening; no glowing rectangle in front of masonry.
    cx=6.16;y=.94
    g.box((cx,1.72,.96),(1.00,.09,1.52),KILN_SOOT)
    g.box((cx,1.30,.28),(1.12,.80,.14),KILN_SOOT)
    for row in range(8):
        z=.23+row*.23
        for xx in (5.61,6.71):masonry(g,(xx,y,z),(.235,.29,.214),row)
        # Side walls: two long stretchers per course (12k cap; were four).
        for xx in (5.58,6.74):
            for j in range(2):masonry(g,(xx,1.265+j*.46,z),(.22,.446,.214),row+j)
    for row,z in enumerate((1.60,1.83)):
        for i in range(4):masonry(g,(5.74+i*.28,y,z),(.265,.29,.215),row+i)
    arch(g,cx,y-.03,1.03,.34,.51)
    for xx in (5.73,6.59):
        for row in range(4):masonry(g,(xx,y-.005,.34+row*.21),(.17,.29,.198),row+1)
    # Crown: two rows of long slabs (12k cap; was a 4 x 4 grid).
    for j in range(2):
        for i in range(4):masonry(g,(5.65+i*.325,1.115+j*.62,2.02),(.311,.604,.15),i+j*4)
    for i in range(3):
        rock(g,(5.90+i*.26,1.20+(i%2)*.12,.39),(.26,.21,.15),KILN_EMBER,1100+i)
    for i,(x,yy,h) in enumerate(((5.93,1.18,.34),(6.16,1.22,.47),(6.36,1.17,.31))):
        p=(x,yy,.43);m,node=g.moving_part('ReferenceKilnFire'+str(i+1),p)
        flame(m,p,h,1200+i);parts.append((node,'FLAME',i))
    # Iron grate, hinge pins and retaining bands sit ahead of the ember bed.
    for x in (5.86,6.01,6.16,6.31,6.46):g.box((x,.81,.59),(.026,.04,.48),IRON)
    for z in (.37,.77):g.box((6.16,.805,z),(.69,.055,.05),IRON)
    for x in (5.59,6.72):
        g.box((x,.762,.99),(.09,.035,1.58),IRON)
    # Heavy iron register above the arch, with an inset hatch.
    g.box((cx,.755,1.77),(.87,.075,.30),IRON)
    g.box((cx,.707,1.77),(.45,.028,.18),KILN_SHELL)
    # Higher rear combustion chamber, visibly stepping up toward the chimney.
    for row in range(7):
        z=1.46+row*.22
        for i in range(3):masonry(g,(5.732+i*.362,2.97,z),(.352,.23,.205),row+i)
        # Five blocks per course on the right side: their joints keep cell
        # (6,3,2)'s face below the connection-face cover (registration).
        for j in range(5):masonry(g,(6.75,2.00+j*.21,z),(.23,.198,.205),row+j)
    g.box((6.16,2.70,2.10),(.93,.06,1.19),KILN_SOOT)
    for i in range(4):
        rock(g,(5.95+(i%2)*.32,2.52+(i//2)*.20,2.035),(.21,.17,.09),KILN_EMBER,1400+i)
    for x in (5.85,6.00,6.15,6.30,6.45):g.box((x,2.09,2.30),(.025,.04,.37),IRON)
    for z in (2.09,2.51):g.box((6.15,2.09,z),(.69,.04,.05),IRON)
    for x in (5.64,6.67):
        for row in range(6):masonry(g,(x,2.10,1.58+row*.22),(.24,.35,.205),row)
    for i in range(4):masonry(g,(5.68+i*.275,2.43,2.99),(.26,1.15,.16),i)

def chimney(g):
    # Tapered, individually seamed steel stack with an open dark interior.
    x,y=6.22,2.70;bottom,top=3.03,4.62
    for row in range(6):
        z0=bottom+row*(top-bottom)/6;z1=bottom+(row+1)*(top-bottom)/6
        r0=.255-row*.011;r1=r0-.011
        verts=[(x+dx*r,y+dy*r,z) for z,r in ((z0,r0),(z1,r1)) for dx,dy in ((-1,-1),(1,-1),(1,1),(-1,1))]
        g.add(verts,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],IRON)
        # Seam bands on alternate courses (12k cap). The lowest course keeps
        # its two seam nuts on the -y face: their heads keep the registered
        # connection faces of cell (6,3,3) (outputs/connection-faces).
        if row%2:continue
        for dy in (-1,1):
            g.box((x,y+dy*r0,z0+.018),(r0*2,.024,.028),IRON)
            if row==0 and dy<0:
                for dx in (-.60,.60):square_nut(g,(x+dx*r0,y+dy*(r0+.02),z0+.09),'Y',.015,dy)
        for dx in (-1,1):
            g.box((x+dx*r0,y,z0+.018),(.024,r0*2,.028),IRON)
    for dx in (-.27,.27):g.box((x+dx,y,top-.02),(.075,.61,.24),IRON)
    # The side bars end on the end bars' inner faces (no overlapping tops).
    for dy in (-.27,.27):g.box((x,y+dy,top-.02),(.465,.075,.24),IRON)
    g.box((x,y,top-.28),(.36,.36,.025),KILN_SOOT)
    for dx in (-.31,.31):g.box((x+dx,y,bottom+.02),(.09,.68,.10),IRON)
    for dy in (-.31,.31):g.box((x,y+dy,bottom+.02),(.53,.09,.10),IRON)
    # Kiln firing smoke at the top of the collar; the flue's top course is
    # 0.189 in half-width. Recorded in the machinery frame (no geometry).
    g.emitter('smoke',x,y,top+.10,.19)

def output(g):
    bin(g,(6.16,.25,.12),(1.38,.94,.58),None)
    g.box((6.16,.25,.60),(1.19,.74,.13),KILN_CEMENT)
    rng=random.Random(554);verts=[];nx,ny=7,5
    for j in range(ny):
        for i in range(nx):
            x=5.58+i*1.16/(nx-1);y=-.10+j*.70/(ny-1)
            z=.66+.12*math.exp(-((x-6.17)/.44)**2-((y-.30)/.34)**2)+rng.uniform(-.008,.008)
            verts.append((x,y,z))
    g.add(verts,[(j*nx+i,j*nx+i+1,(j+1)*nx+i+1,(j+1)*nx+i) for j in range(ny-1) for i in range(nx-1)],KILN_CEMENT)
    a=Vector((6.16,.93,DECK_Z-KILN_MACHINE_DATUM+.79));b=Vector((6.16,.60,.72))
    g.beam(a,b,.60,.035,IRON)
    for x in (5.84,6.48):g.beam((x,.93,DECK_Z-KILN_MACHINE_DATUM+.85),(x,.60,.78),.035,.11,IRON)
    for x in (5.51,6.81):
        for y in (-.16,.65):bracket(g,x,y,.26,.11)

def details(g,rails,ground):
    machinery=g
    # Riveted gear guard, two small gauges and lever linkages at the operator rail.
    g.box((4.89,1.42,1.92),(.63,.10,.39),IRON)
    for x in (4.76,5.04):
        prism(g,(x,1.355,1.97),.086,.06,BRASS,'Y',8,(True,False))
        prism(g,(x,1.317,1.97),.067,.015,LIME,'Y',8,(True,False))
        g.beam((x,1.286,1.97),(x-.035,1.286,2.009),.008,mat=IRON)
    for x in (4.75,5.03):
        prism(g,(x,1.36,1.76),.038,.07,BRASS,'Y',6)
        g.beam((x,1.34,1.76),(x,1.20,1.86),.025,mat=IRON)
        prism(g,(x,1.20,1.86),.038,.09,WOOD,'X',6)
    round_pipe(g,[(4.87,1.50,1.77),(4.87,1.66,1.77),(5.43,1.66,1.77),(5.43,1.80,1.77)],.025)
    # A distinct coal/ash work bay under the extended section, with hinged box.
    g=ground
    bin(g,(4.94,1.69,.12),(.96,.73,.49),None)
    for i in range(5):g.box((4.55+i*.195,1.69,.64),(.185,.77,.05),PLANK)
    for x in (4.62,5.26):
        g.box((x,1.69,.675),(.07,.79,.025),IRON)
        prism(g,(x,2.06,.65),.04,.09,IRON,'X',6,phase=math.pi/6)
    for x in (5.44,5.57):
        g.beam((x,1.93,.22),(x,1.83,.98),.025,mat=WOOD)
        g.box((x,1.93,.22),(.11,.075,.15),IRON)
    # Hand-operated chimney damper (the furnace-side walk is removed).
    g=machinery
    prism(g,(5.88,2.70,3.65),.045,.44,IRON,'X',6)
    band(g,(5.70,2.70,3.65),.18,.035,.05,IRON,'X',8,inner=True)
    for i in range(4):
        a=i*math.pi/2;g.beam((5.70,2.70,3.65),(5.70,2.70+math.cos(a)*.155,3.65+math.sin(a)*.155),.025,mat=IRON)
    g.beam((5.90,2.70,3.65),(5.90,2.70,3.30),.035,mat=IRON)
    g.box((5.90,2.70,3.23),(.10,.12,.16),IRON)
    # Staggered flat roof repairs, with nails and folded seams instead of clutter.
    for x,y,z in ((2.30,2.83,3.417),(4.83,2.44,3.341)):
        g.box((x,y,z),(.31,.22,.016),IRON)
    # Warm caged lights hang from real brackets on the hall frame.
    for x,y,z in ((1.58,1.24,2.58),(5.65,1.24,2.56),(1.58,3.56,2.72),(5.65,3.56,2.81)):
        if y>3.5:g.beam((x,3.25,z+.20),(x,3.61,z+.20),.035,mat=IRON)
        cage_lamp(g,x,y,z)
    # Hanging tool rack and clearly recognizable storage props; no characters.
    g=ground
    for x in (2.49,2.65):
        g.beam((x,3.19,.20),(x,3.15,.89),.027,mat=WOOD)
        g.box((x,3.20,.25),(.12,.055,.20),IRON)
    cask(g,(.71,2.70,.12),.21,.55)
    bin(g,(5.23,3.08,.12),(.56,.62,.43),None)
    g.beam((4.97,2.75,.18),(5.49,2.75,.50),.065,mat=WOOD)
    g.box((5.23,3.08,.58),(.60,.65,.07),PLANK)

def worn_surfaces(g,ground):
    """Wear follows exposed joints, traffic, soot and handling, not random clutter."""
    # (The 75 paint chips 1-3 cm wide along the roof joints, timber checks
    # 3-7 mm wide, soot drips and rust streaks were sub-pixel at game zoom;
    # the native atlases paint their own grain and wear.)
    # A repaired roof sheet has a lapped edge and folded seams.
    x0,x1,y0,y1=3.92,4.45,2.11,2.76
    points=[(x,y,3.06+(y-1.15)*.44/2.25+.045) for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1))]
    g.add(points,[(0,1,2,3)],KILN_SHELL)
    for a,b in ((points[0],points[3]),(points[1],points[2])):g.beam(a,b,.025,.018,KILN_RUST)

def workshop_details(g,ground):
    machinery=g
    # Oiling cups, retaining straps and a small feed-gate linkage at the hopper.
    for x in (1.31,3.48,5.13):
        prism(g,(x+.27,1.41,1.64),.042,.09,BRASS,'Z',6)
        prism(g,(x+.27,1.41,1.699),.052,.024,IRON,'Z',6)
        round_pipe(g,[(x+.27,1.41,1.60),(x+.27,1.52,1.60)],.016)
    g.box((.43,1.52,2.47),(.35,.055,.21),IRON)
    prism(g,(.42,1.43,2.48),.048,.18,IRON,'Y',6)
    band(g,(.42,1.32,2.48),.16,.027,.04,IRON,'Y',8,inner=True)
    for a in (0,math.pi/2,math.pi,math.pi*1.5):
        g.beam((.42,1.32,2.48),(.42+math.cos(a)*.145,1.32,2.48+math.sin(a)*.145),.025,mat=IRON)
    # (2026-10-22: the side workshop bench, the rear cask and spare tyre and
    # the ash bucket under the porch wing stood outside the hall's frame
    # line and were removed with their footprint tiles; players place props.)

def kiln(g,parts):
    machinery=MountedMachinery(g,KILN_MACHINE_DATUM,DECK_Z)
    rails=RailAssembly('WalkwayRail')
    structure(g,rails,machinery);feed_tower(machinery,g);mechanics(machinery,parts);fuel_logs(g)
    porch(g);firebox(machinery,parts);chimney(machinery);output(g);details(machinery,rails,g)
    # Masonry supports the raised process chamber down to the ground datum.
    for row in range(4):
        # Five long stretchers per course (12k cap; were ten): the ground
        # course under the whole firebox and rear chamber.
        for x in (5.61,6.71):
            for j in range(5):masonry(g,(x,1.07+j*.44,.20+row*.20),(.235,.434,.19),row+j)
        for x in (5.86,6.16,6.46):masonry(g,(x,2.98,.20+row*.20),(.29,.23,.19),row)
    g.box((6.16,1.98,.87),(1.34,2.18,.12),KILN_STONE)
    worn_surfaces(machinery,g);workshop_details(machinery,g)
    kiln_facades(g)
    # The cask in the closed control room stays: its staves keep cell
    # (3,3,0)'s Right face out of the registered connection faces. (The plank
    # stack beside it went with the 12k cap.)
    cask(g,(3.76,2.99,.14),.23,.56)
    # Ground-level mechanical coupling. (The tool rack behind the rear frame
    # line was removed, 2026-10-22.)
    timber_column(g,.25,2.55,.12,1.19,.17)
    prism(g,(.10,2.55,.57),.14,.16,IRON,'X',8)
    band(g,(.035,2.55,.57),.16,.03,.04,BRASS,'X',8,inner=True)
    return rails
