"""Original Materials Laboratory from its two isometric concept views.

Stepped sawtooth testing halls, enclosed records wing, cast foundations,
instrument tower and a working screw press. Artwork sets the envelope; no
top-view or printed footprint is consulted. The public terrace is layer two.
"""
import math
import random

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
from reference_materials import CIVIC_CONCRETE, CIVIC_FORGED_PANEL, GLASS, KILN_SOOT
from industrial_budget import bracket, bin as budget_bin
from civic_isometric_geometry import steel_bolt
from industrial_facades import building_portal, window_y, side_window, gauge
from architectural_windows import window
from native_window_atlas import atlas_window, glass_curtain
from industrial_budget import round_pipe, cage_lamp
from civic_isometric_geometry import framed_room, gabled_roof, roof_bearing, timber_column
from native_building_assets import barrel, plant
from walkway_geometry import RailAssembly
from lategame_kit import emitter


def concrete_course(g,x0,y0,x1,y1,top,door=None,cap=True,*,left_wall=True,left_straps=True,front_from=None,back_from=None):
    """Closed cast shell with narrow recessed joints and steel corner straps.

    front_from/back_from start the front/back wall at another x (a plinth
    abutting a neighbour's wall: cover its corner, never share its footprint).
    """
    wall_top=top-.16
    for row in range(math.ceil(wall_top/.47)):
        bottom=row*.47;h=min(.47,wall_top-bottom)
        for y in (y0,y1):
            start=(front_from if y==y0 else back_from)
            start=x0 if start is None else start
            count=math.ceil((x1-start)/.66)
            for i in range(count):
                a=start+i*(x1-start)/count;b=start+(i+1)*(x1-start)/count
                # Door opening is authored in the wall, not hidden by a black card.
                ranges=[(a,b)]
                if y==y0 and door is not None and bottom<door[2]:
                    left,right=door[0]-door[1]/2,door[0]+door[1]/2
                    ranges=[(a,min(b,left)),(max(a,right),b)]
                for lo,hi in ranges:
                    if hi>lo:g.box(((lo+hi)/2,y,bottom+h/2),(hi-lo,.15,h),CIVIC_CONCRETE)
                if y==y0 and door is not None and bottom<door[2]<bottom+h:
                    lo=max(a,door[0]-door[1]/2);hi=min(b,door[0]+door[1]/2)
                    if hi>lo:g.box(((lo+hi)/2,y,(door[2]+bottom+h)/2),(hi-lo,.15,bottom+h-door[2]),CIVIC_CONCRETE)
        for x in ((x0,x1) if left_wall else (x1,)):
            count=math.ceil((y1-y0-.15)/.66)
            for i in range(count):
                g.box((x,y0+.075+(i+.5)*(y1-y0-.15)/count,bottom+h/2),(.15,(y1-y0-.15)/count,h),CIVIC_CONCRETE)
    # The cap is flush with the outer wall faces, so a cast shell on tile
    # edges ends exactly on them.
    if cap:g.box(((x0+x1)/2,(y0+y1)/2,top-.08),(x1-x0+.15,y1-y0+.15,.16),CIVIC_CONCRETE)
    for x in ((x0,x1) if left_straps else (x1,)):
        for y in (y0,y1):
            for z in (.45,top-.4):
                g.box((x,y,z),(.24,.24,.46),IRON)
                for dz in (-.14,.14):steel_bolt(g,(x,y-.14,z+dz),r=.027)


def girder(g,a,b,width=.22,*,plate_stations=(.12,.88)):
    g.beam(a,b,width,.18,WOOD)
    for t in plate_stations:
        p=tuple(a[i]+(b[i]-a[i])*t for i in range(3))
        if abs(b[1]-a[1])>abs(b[0]-a[0]):
            g.box((p[0]-width/2-.018,p[1],p[2]),(.035,.36,.30),IRON)
            for dy in (-.11,.11):
                for dz in (-.08,.08):steel_bolt(g,(p[0]-width/2-.045,p[1]+dy,p[2]+dz),'X',.025)
        else:
            front_half_depth=.09 if b[0]==a[0] else width/2
            g.box((p[0],p[1]-front_half_depth-.018,p[2]),(.36,.035,.30),IRON)
            for dx in (-.11,.11):
                for dz in (-.08,.08):steel_bolt(g,(p[0]+dx,p[1]-front_half_depth-.045,p[2]+dz),r=.025)


def shed_roof(g,x0,x1,y0,y1,left,right,seed):
    """Diagonal blue roof with visible rolled seams, straps and worn edges."""
    def z(x):return left+(right-left)*(x-x0)/(x1-x0)
    count=math.ceil((y1-y0)/.25)
    rng=random.Random(seed)
    for i in range(count):
        ya=y0+i*(y1-y0)/count;yb=y0+(i+1)*(y1-y0)/count
        g.add([(x0,ya,z(x0)),(x1,ya,z(x1)),(x1,yb,z(x1)),(x0,yb,z(x0)),
               (x0,ya,z(x0)-.065),(x1,ya,z(x1)-.065),(x1,yb,z(x1)-.065),(x0,yb,z(x0)-.065)],
              [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],ROOF)
        g.beam((x0,ya,z(x0)+.025),(x1,ya,z(x1)+.025),.025,mat=IRON)
        for x in (x0+.07,x1-.07):steel_bolt(g,(x,(ya+yb)/2,z(x)+.04),'Z',.018)
        # Triangle budget: no 12 mm brass wear streaks (two per sheet could
        # overlap coplanar once the bevel modifier is gone).
    for y in (y0,y1):girder(g,(x0,y,z(x0)-.07),(x1,y,z(x1)-.07),.16)
    for x in (x0,x1):
        girder(g,(x,y0+.005,z(x)-.04),(x,y1-.005,z(x)-.04),.16)
    # The back strap stands 20 cm in, clear of the pier collars at the step.
    for y in (y0+.16,(y0+y1)/2,y1-.20):
        g.beam((x0,y,z(x0)+.05),(x1,y,z(x1)+.05),.055,.045,IRON)
        for x in (x0+.12,(x0+x1)/2,x1-.12):steel_bolt(g,(x,y,z(x)+.08),'Z',.023)


def slope_facade(g,x0,x1,y,bottom,left,right,seed,tall_windows,outward=-1):
    """Individual vertical boards closed up to a sloping roof edge."""
    if outward==1:
        rear=Geometry('Rear facade source')
        slope_facade(rear,x0,x1,0,bottom,left,right,seed,tall_windows,-1)
        vertices=[(-vx,y+vy,vz) for vx,vy,vz in rear.vertices]
        for face,material,uv,source in zip(rear.faces,rear.materials,rear.face_uvs,rear.face_sources,strict=True):
            g.add([vertices[i] for i in reversed(face)],[tuple(range(len(face)))],material)
            g.face_uvs[-1]=list(reversed(uv)) if uv is not None else None
            g.face_sources[-1]=source
        return
    if outward!=-1:raise ValueError('Facade must face forward or back')
    def z(x):return left+(right-left)*(x-x0)/(x1-x0)
    n=math.ceil((x1-x0)/.17)
    rng=random.Random(seed)
    for i in range(n):
        a=x0+i*(x1-x0)/n;b=x0+(i+1)*(x1-x0)/n
        g.add([(a,y-.055,bottom),(b,y-.055,bottom),(b,y-.055,z(b)),(a,y-.055,z(a)),
               (a,y+.055,bottom),(b,y+.055,bottom),(b,y+.055,z(b)),(a,y+.055,z(a))],
              [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],PLANK)
        for _ in range(2):
            zz=rng.uniform(bottom+.12,z(a)-.18)
            g.box(((a+b)/2,y-.115,zz),(.009,.008,.12),KILN_SOOT)
    # The base rail butts between the corner stiles; its end caps do not
    # occupy the same plane as the plank end caps.
    girder(g,(x0+.11,y-.12,bottom+.04),(x1-.11,y-.12,bottom+.04))
    girder(g,(x0,y-.12,left-.08),(x1,y-.12,right-.08))
    for i in range(5):
        x=x0+(x1-x0)*i/4
        girder(g,(x,y-.12,bottom),(x,y-.12,z(x)))
        if i==4:continue
        cx=x+(x1-x0)/8;head=z(cx)-.32
        if tall_windows:
            # Testing-hall bays: full-height steel curtain glazing with big
            # native panes, so specimens can be inspected in daylight.
            low=bottom+.65
            glass_curtain(g,cx,y-.055,low,head,(x1-x0)/4-.30,'front',cols=2,rows=max(2,round((head-low)/.85)))
        else:
            # North-light ribbon on the sawtooth step.
            atlas_window(g,cx,y-.055,head-.2,.84,'front','ribbon')
            g.box((cx,y-.09,bottom+.33),((x1-x0)/4-.24,.06,.27),CIVIC_FORGED_PANEL)
    for a,b in ((x0,x0+(x1-x0)/4),(x1-(x1-x0)/4,x1)):
        girder(g,(a,y-.27,bottom+.24),(b,y-.27,z(b)-.16),.15)


def stack(g,x,y,bottom,height,*,emits):
    """Banded flue with a flared cowl. `emits` is the vanilla effect at its
    mouth (a lategame_kit.EMITTER_KINDS entry) or None; every caller decides.
    The emitter adds no geometry."""
    g.cylinder((x,y,bottom+height/2),.12,height,IRON,'Z',16)
    for z in (bottom+.1,bottom+.45,bottom+height-.14):
        g.ring((x,y,z),.17,.045,.075,IRON)
        for dx in (-.10,.10):steel_bolt(g,(x+dx,y-.14,z),r=.015)
    g.cylinder((x,y,bottom+height+.02),.24,.13,IRON,'Z',16,.15)
    g.cylinder((x,y,bottom+height-.12),.14,.04,KILN_SOOT)
    if emits is not None:
        # Mouth: the cowl's top face (radius 0.15).
        emitter(g,emits,x,y,bottom+height+.085,.15)


def flanged_pipe(g,points,r=.065):
    round_pipe(g,points,r)
    for a,b in zip(points,points[1:]):
        axis='XYZ'[next(i for i in range(3) if a[i]!=b[i])]
        for f in (.13,.86):
            p=tuple(a[i]+(b[i]-a[i])*f for i in range(3))
            g.ring(p,r*1.5,.03,.065,BRASS,axis,16)


# Laboratory copies of the shared bin/crate/planter/sheet-roof props. Same
# dimensions, UV materials and plants; only the fasteners that sat within
# 1-4 mm of a neighbouring face (strict z-fight audit, epsilon 0.004) stand
# 6-9 mm proud instead. The shared helpers are left unchanged.
def lab_bin(g,p,size):
    # Triangle budget: the shell-only bin (one square rivet per post face).
    budget_bin(g,p,size,None,proud_rivets=True)


def lab_crate(g,x,y,z,w=.55,h=.5):
    lab_bin(g,(x,y,z),(w,w*.85,h))
    for i in range(4):g.box((x-w*.375+i*w*.25,y,z+h+.035),(w*.24,w*.85,.05),PLANK)
    for yy in (y-w*.28,y+w*.28):g.box((x,yy,z+h+.085),(w+.04,.06,.05),WOOD)
    g.beam((x-w*.39,y-w*.44,z+.08),(x+w*.39,y-w*.44,z+h-.07),.055,.025,WOOD)


def lab_planter(g,x,y,z,width,seed,species='DandelionMature'):
    lab_bin(g,(x,y,z),(width,.32,.27))
    count=math.floor((width-.10)/.24)
    if count<1:raise ValueError('Planter is too narrow for an authored native plant')
    g.box((x,y,z+.23),(width-.06,.26,.035),KILN_SOOT)
    for i in range(count):
        along=(i-(count-1)/2)*.24
        plant(g,species,(x+along,y,z+.245),.29,((seed+i)%4)*90)


def lab_awning(g,x0,y0,x1,y1,z0,z1,seed=41):
    rng=random.Random(seed);count=math.ceil((x1-x0)/.28)
    for i in range(count):
        x=x0+(i+.5)*(x1-x0)/count
        g.beam((x,y0,z0),(x,y1,z1),(x1-x0)/count,.045,ROOF)
        for t in (.08,.92):steel_bolt(g,(x,y0+(y1-y0)*t,z0+(z1-z0)*t+.035),'Z',.015)
    for x in (x0,x1):g.beam((x,y0,z0-.035),(x,y1,z1-.035),.13,.14,WOOD)
    for y,z in ((y0,z0),(y1,z1)):
        g.beam((x0,y,z-.055),(x1,y,z-.055),.15,.16,WOOD)
        for x in (x0,x1):
            # .17 collar (was .16): its nut heads stood 0.45 mm off the
            # side beam's face, inside the strict overlap tolerance.
            bracket(g,x,y,z-.07,.17)
            g.box((x,y,z+.050),(.23,.23,.025),IRON)
            steel_bolt(g,(x,y,z+.071),'Z',.024)
    for t in (.35,.72):
        y=y0+(y1-y0)*t;z=z0+(z1-z0)*t+.03
        g.beam((x0,y,z),(x1,y,z),.06,.018,IRON)
        for x in (x0+.08,x1-.08):steel_bolt(g,(x,y,z+.015),'Z',.016)
    # Triangle budget: no 6x4 mm scratch slivers (sub-pixel at game zoom).


def steel_column(g,x,y,bottom,top,w):
    timber_column(g,x,y,bottom,top,w,steel_channels=False)
    core_bottom=.53 if bottom==0 else bottom
    for side in (-1,1):
        g.box((x+side*w*.44,y,(core_bottom+top)/2),(.035,w+.065,top-core_bottom-.04),IRON)


def specimen_shelf(g,x,y,width=2.8,*,awning_back=None):
    for xx in (x-width/2,x,x+width/2):steel_column(g,xx,y,0,1.75,.14)
    # The middle board sits 2 cm under the column collars (was 2.5 mm).
    for z in (.12,.70,1.30):
        g.box((x,y-.16,z),(width+.10,.50,.075),PLANK)
        for i in range(6):
            # Three items per half, clear of the three columns.
            a,b=(x-width/2+.26,x-.26) if i<3 else (x+.26,x+width/2-.26)
            cx=a+(b-a)*(i%3)/2
            if (i+round(z*10))%2:
                g.box((cx,y-.15,z+.17),(.25,.25,.27),CIVIC_CONCRETE)
                g.cylinder((cx,y-.285,z+.18),.035,.015,IRON,'Y',10)
            else:
                lab_crate(g,cx,y-.15,z+.04,.32,.25)
                g.box((cx,y-.327,z+.15),(.11,.018,.07),CIVIC_CONCRETE)
    # The awning is carried back to the hall's cast base when it stands in
    # front of one, so it reads as a lean-to rather than a floating canopy.
    # The high edge stays just under layer 2 (shelf cells are layers 0-1);
    # the 0.29 rise keeps the sheet bolts 6 mm under the back beam.
    lab_awning(g,x-width/2-.15,y-.65,x+width/2+.15,y+.35 if awning_back is None else awning_back,1.64,1.93)
    for xx in (x-width/2+.15,x,x+width/2-.15):cage_lamp(g,xx,y-.57,1.44)


# Native-grid registration of the shell (art XY = grid XY, origin 0).
# Cast bases have their outer faces on tile edges; the timber upper hall
# stands back from its base so its frame, braces and roof trim stay inside
# the occupied cells (within a 12 cm edge sliver).
HALL_BASE=(3.0,1.0,8.0,8.0)            # x0,y0,x1,y1 outer faces
HALL_X0,HALL_X1=3.18,7.85              # upper side board planes
HALL_FRONT,HALL_STEP,HALL_REAR=1.32,4.30,7.30
ROOF_X0,ROOF_X1=3.04,7.98


def front_roof_z(x):
    return 6.62+(4.75-6.62)*(x-2.98)/4.86


def rear_roof_z(x):
    return 7.58+(5.71-7.58)*(x-2.98)/4.86


def service_bay(g):
    """Player service bay between the press and the instrument tower.

    Grid cells (8..9, 3..4, 0..) stay unoccupied for player-built shafts,
    conveyors and Power Lines. The hall wall facing it carries the native
    shaft socket (transput (7,4,0) Right), a conveyor intake hatch on cell
    (7,3,0) and a Power Lines insulator bracket; nothing is built inside it.
    Every fitting stays within 12 cm of the x=8 tile edge.
    """
    wall=HALL_BASE[2]         # outer face of the hall's cast base: tile edge x=8
    upper=HALL_X1+.055        # outer face of the upper hall boards
    # Conveyor intake: steel-framed hatch with a dark recess and a short lip
    # at belt height, centred on cell (7,3,0)'s right face.
    g.box((wall+.025,3.5,.47),(.05,.78,.74),IRON)
    g.box((wall+.056,3.5,.47),(.012,.6,.56),KILN_SOOT)
    # Rails stand 15 mm proud of the stiles; stile ends sit inside the rails.
    for z in (.12,.84):g.box((wall+.065,3.5,z),(.08,.86,.06),CIVIC_FORGED_PANEL)
    for yy in (3.08,3.92):g.box((wall+.06,yy,.48),(.07,.06,.74),CIVIC_FORGED_PANEL)
    g.box((wall+.06,3.5,.17),(.12,.62,.035),IRON)
    for yy in (3.16,3.84):steel_bolt(g,(wall+.104,yy,.84),'X',.02)
    # Power Lines connection: bracket arm with three insulators on the upper
    # hall wall (PowerLineSpec point at the top insulator).
    g.box((upper+.03,3.5,2.35),(.06,.30,.30),IRON)
    g.beam((upper+.05,3.5,2.35),(upper+.30,3.5,2.35),.07,mat=IRON)
    for dz in (0,.09,.18):g.cylinder((upper+.30,3.5,2.40+dz),.045,.06,BRASS,'Z',10)
    g.cylinder((upper+.30,3.5,2.66),.02,.06,IRON,'Z',8)
    # Water inlet socket on the tower plinth's bay face (the y=5 tile edge),
    # at ground-pipe height. Timber Pipes accepts any face; this marks the spot.
    face,wx=5.0,9.6
    round_pipe(g,[(wx,face+.15,.2),(wx,face-.06,.2)],.08)
    g.ring((wx,face-.03,.2),.13,.05,.05,BRASS,'Y',16)
    g.wheel((wx,face-.035,.42),.11,'Y',IRON,BRASS)
    g.beam((wx,face-.035,.28),(wx,face-.035,.36),.03,mat=IRON)


def instrument_tower(g,x,y,*,base=None):
    """Instrument tower on its cast plinth.

    `base` gives explicit wall centrelines (x0,y0,x1,y1) for a plinth that
    abuts the hall: no left wall or straps, and its own cap starts where the
    hall's cap ends (the hall's x=8 face) so the two tops never overlap.
    """
    if base is None:
        concrete_course(g,x-.78,y-.78,x+.78,y+.78,2,left_straps=False)
        front_face=y-.955
    else:
        bx0,by0,bx1,by1=base
        concrete_course(g,bx0,by0,bx1,by1,2,cap=False,left_wall=False,left_straps=False,
                        front_from=bx0+.075,back_from=bx0+.075)
        cap_x0,cap_x1=bx0+.075,bx1+.075
        g.box(((cap_x0+cap_x1)/2,(by0+by1)/2,1.92),(cap_x1-cap_x0,by1-by0+.15,.16),CIVIC_CONCRETE)
        front_face=by0-.075
    # The barrel stands on the plinth cap (top z=2), not 7.5 cm above it.
    g.cylinder((x,y,4.16),.61,4.33,IRON,'Z',32)
    for z in (2.20,3.15,4.40,5.55,6.27):
        g.ring((x,y,z),.65,.06,.11,BRASS,'Z',32)
        for i in range(16):
            a=i*math.tau/16
            g.cylinder((x+math.cos(a)*.657,y+math.sin(a)*.657,z),.029,.10,IRON,'Z',6)
    for i in range(12):
        a=i*math.tau/12
        g.beam((x+math.cos(a)*.612,y+math.sin(a)*.612,2.28),
               (x+math.cos(a)*.612,y+math.sin(a)*.612,6.22),.016,mat=BRASS)
    g.cylinder((x,y,6.66),.91,.62,ROOF,'Z',24,.09)
    g.ring((x,y,6.36),.92,.055,.07,IRON,'Z',24)
    for i in range(12):
        a=i*math.tau/12
        g.beam((x+math.cos(a)*.90,y+math.sin(a)*.90,6.39),(x+math.cos(a)*.09,y+math.sin(a)*.09,6.97),.024,mat=IRON)
    g.cylinder((x,y,7.02),.085,.16,IRON,'Z',12,.035)
    for z,r in ((3.02,.19),(4.93,.23),(5.66,.17)):
        gauge(g,x+.32,y-.65,z,r)
    for offset in (-.72,.72):
        flanged_pipe(g,[(x+offset,y-.20,1.0),(x+offset,y-.20,5.65),(x+offset*.5,y-.20,5.65)],.055)
        for z in (1.2,2.65,4.9):g.box((x+offset,y-.2,z),(.17,.18,.06),IRON)
        g.wheel((x+offset,y-.37,2.85),.13,'Y',IRON,BRASS)
    # Header pipe runs onto the hall's right eave, clear of its girder.
    flanged_pipe(g,[(x-.60,y,5.88),(x-1.05,y,5.88),(x-1.05,y-1,5.88)],.11)
    front=front_face+.02   # half set into the plinth face: flanges stay within 11 cm
    # Down the plinth's bay face in the x=9 column, high enough to pass over
    # the water inlet socket.
    flanged_pipe(g,[(x+.2,y-.60,2.3),(x+.2,front,2.3),(x+.2,front,.75),(x+.95,front,.75)],.085)


def testing_press(g,parts,x,y,*,base=None,flywheel_x=None):
    bx0,by0,bx1,by1=(x-.72,y-.65,x+1,y+.75) if base is None else base
    # With an explicit base the front wall covers the hall's corner and the
    # back wall starts at the hall's face.
    concrete_course(g,bx0,by0,bx1,by1,1.55,cap=base is None,left_wall=False,left_straps=False,
                    back_from=None if base is None else bx0+.075)
    if base is not None:
        # Own cap from the hall's x=8 face outward: never inside its wall.
        g.box(((bx0+.075+bx1+.075)/2,(by0+by1)/2,1.55-.08),(bx1-bx0,by1-by0+.15,.16),CIVIC_CONCRETE)
    for xx in (x-.78,x+.78):
        girder(g,(xx,y-.1,1.6),(xx,y-.1,4.56),.24)
        g.box((xx,y,1.62),(.48,.51,.14),IRON)
        for dx in (-.16,.16):steel_bolt(g,(xx+dx,y-.2,1.74),'Z',.03)
    # Two top plates sit between the upright fasteners, not through them.
    girder(g,(x-.85,y-.1,4.56),(x+.85,y-.1,4.56),.30,plate_stations=(.30,.70))
    g.box((x,y,2.03),(1.20,.70,.28),IRON)
    g.box((x,y,2.35),(.53,.5,.38),CIVIC_CONCRETE)
    for z in (2.05,4.43):
        g.cylinder((x,y,z),.19,.19,IRON)
        for xx in (x-.35,x+.35):steel_bolt(g,(xx,y-.38,z),r=.032)
    screw=Geometry('MaterialsLaboratory.PressScrew',(x,y,3.68))
    screw.cylinder((x,y,3.68),.10,1.40,IRON,'Z',20)
    for i in range(140):
        a=i*math.tau/10;b=(i+1)*math.tau/10
        screw.beam((x+math.cos(a)*.14,y+math.sin(a)*.14,3.0+i*.0095),
                   (x+math.cos(b)*.14,y+math.sin(b)*.14,3.0+(i+1)*.0095),.040,mat=BRASS)
    parts.append((screw,'Z',1))
    ram=Geometry('MaterialsLaboratory.TestRam',(x,y,2.98))
    ram.box((x,y,2.98),(1.12,.72,.29),IRON)
    ram.box((x,y,2.77),(.64,.54,.12),CIVIC_CONCRETE)
    for dx in (-.39,.39):
        for dz in (-.08,.08):steel_bolt(ram,(x+dx,y-.38,2.98+dz),r=.03)
    parts.append((ram,'LAB_PRESS',1))
    gauge(g,x-.94,y-.18,3.22,.14)
    flanged_pipe(g,[(x-.95,y+.25,1.8),(x-.95,y+.25,3.8),(x-.2,y+.25,3.8)],.05)
    fx=x-1.40 if flywheel_x is None else flywheel_x
    fly=Geometry('MaterialsLaboratory.Flywheel',(fx,y+.30,2.69))
    fly.wheel((fx,y+.30,2.69),.69,'Y',IRON,BRASS)
    fly.ring((fx,y+.30,2.69),.73,.09,.19,IRON,'Y',40)
    parts.append((fly,'Y',-1))
    g.cylinder((fx,y+.43,2.69),.10,.57,IRON,'Y',16)
    for xx in (fx-.25,fx+.25):g.box((xx,y+.48,2.23),(.15,.30,.60),IRON)


def laboratory(g,parts):
    rails=RailAssembly('MaterialsLaboratory.Rail',cap_material=IRON)
    # Cast lower records wing and broad front terrace; no integral stairs.
    # Outer faces: x=0, y=0.015 (behind the door casing on the y=0 edge),
    # x=2.975 and y=7.
    concrete_course(g,.075,.09,2.90,6.925,2,(1.5,1.0,1.0),cap=False)
    # The cast opening and terrace slab already form the reveal and sill, so
    # the portal omits its own cavity faces (no duplicate surfaces). The
    # casing face lies on the y=0 tile edge, centred on tile x=1.
    building_portal(g,1.5,0.0,0,facade='grid')
    g.doorways.append({'id':'GroundDoor','position':[1.5,0.0,0],'outward':[0,-1],'width':1.0,'internalConnection':'BuildingInterior'})
    # Cast records base: sturdy nine-pane grids front, high archive bands side.
    for x in (.52,2.48):atlas_window(g,x,.015,1.0,.72,'front','grid9')
    for y in (1.45,3.6,5.8):atlas_window(g,0.0,y,1.38,.96,'left','band4')
    # Door lamps over the entrance path cell, arms on the wall face.
    for x in (1.09,1.91):cage_lamp(g,x,-.035,1.49)
    # Floor edges sit on whole cell boundaries, and the nine middle cells stay clear.
    g.box((1.4975,1.5,1.905),(2.995,3,.13),CIVIC_CONCRETE)
    g.box((1.4875,5.0,1.92),(2.975,4.0,.16),CIVIC_CONCRETE)
    for i in range(14):g.box((.11+i*2.78/13,1.50,1.985),(.185,2.85,.03),PLANK)
    # Terrace rails: native posts (0.14 x 0.16) set in by half a post so their
    # outer faces lie on the terrace edges; one run per cell, with the inner
    # posts on cell edges so an open cell never leaves a stub.
    ix,iy=.071,.081
    for x in range(3):
        rails.run(f'TerraceFront{x}',(x+ix if x==0 else x,iy),(x+1-ix if x==2 else x+1,iy),2)
    for y in range(3):
        rails.run(f'TerraceLeft{y}',(ix,y+iy if y==0 else y),(ix,y+1),2)
    rails.run('TerraceRight0',(3-ix,iy),(3-ix,1),2)
    # Short return to the hall's front frame across the plinth ledge.
    rails.run('TerraceRightReturn',(3-ix,1),(3-ix,HALL_FRONT-.05),2)
    framed_room(g,.27,3.10,2.73,6.55,2,4.20,3,(1.5,1.0,1.0))
    building_portal(g,1.5,3.00,2,facade='grid')
    g.doorways.append({'id':'TerraceDoor','position':[1.5,3.00,2],'outward':[0,-1],'width':1.0,'internalConnection':'BuildingInterior'})
    roof_bearing(g,.27,3.10,2.73,6.55,4.20,4.24)
    gabled_roof(g,.05,2.85,2.94,6.80,4.24,5.16,121)
    # Records office: tall lancets either side of the terrace door, framed
    # crosses along the side, one grand window as the gable's feature.
    # Centred in framed_room's bays: front posts .27/1.09/1.91/2.73 (door
    # between), side posts 3.10/4.25/5.40/6.55.
    for x in (.68,2.32):window(g,x,3.04,3.03,.95,'front','lancet')
    for y in (3.675,4.825,5.975):atlas_window(g,.21,y,3.10,.7,'left','cross')
    # Gable feature window on the gable cladding. At scale 1.15 its inner
    # frame plane clears the eave beam face by 4.6 mm (1.1 left it 4 mm).
    window_y(g,1.5,2.805,4.45,1.15)
    for x in (.57,2.50):cage_lamp(g,x,2.84,3.65)
    # The roof terrace stays clear, usable space: no planters or decor on its
    # walkable cells (user rule, 2026-10-21); only wall-mounted lamps above.
    # Main hall: cast base on the x=3..8, y=1..8 tile edges; enclosed
    # sawtooth upper hall set back on its plinth.
    bx0,by0,bx1,by1=HALL_BASE
    concrete_course(g,bx0+.075,by0+.075,bx1-.075,by1-.075,2)
    right_front=front_roof_z(HALL_X1)-.042
    right_rear=rear_roof_z(HALL_X1)-.052
    slope_facade(g,HALL_X0,HALL_X1,HALL_FRONT,2,6.50,right_front,220,True)
    slope_facade(g,HALL_X0,HALL_X1,HALL_STEP,4.83,7.45,right_rear,221,False)
    slope_facade(g,HALL_X0,HALL_X1,HALL_REAR,2,7.45,right_rear,222,True,1)
    # Side bays are halves of each sawtooth section (equal 1.5 m bays); every
    # window is centred between its piers.
    front_stile,rear_stile=HALL_FRONT-.12,HALL_REAR+.12
    # The rear pier sits 1 cm aft of the bay midpoint so its faces clear the
    # side-board joints (5.967); windows stay centred in the resulting bays.
    front_pier,rear_pier=(front_stile+HALL_STEP)/2,(HALL_STEP+rear_stile)/2+.01
    bays=[(front_stile,front_pier),(front_pier,HALL_STEP),(HALL_STEP,rear_pier),(rear_pier,rear_stile)]
    centres=[(a+b)/2 for a,b in bays]
    for x,height_front,height_back in ((HALL_X0,6.5,7.45),(HALL_X1,right_front,right_rear)):
        for ya,yb,h in ((HALL_FRONT,HALL_STEP,height_front),(HALL_STEP,HALL_REAR,height_back)):
            count=math.ceil((yb-ya)/.17)
            for i in range(count):g.box((x,ya+(i+.5)*(yb-ya)/count,(2+h)/2),(.11,(yb-ya)/count,h-2),PLANK)
            # The shared sawtooth pier is authored once, to the taller roof.
            # Pier tops stop 15 mm under the boards; girders are 2 cm
            # narrower than the piers so no side faces coincide.
            steel_column(g,x,front_pier if ya==HALL_FRONT else rear_pier,2,h-.015,.22)
            if ya==HALL_STEP:steel_column(g,x,ya,2,4.815,.22)  # just under the step facade, clear of roof bolts
            girder(g,(x,ya,2.05),(x,yb,2.05),.20)
            # Side eave beams butt against the front/rear frame thickness.
            girder(g,(x,ya+.22,h-.08),(x,yb-.22,h-.08),.20)
            for yy in (centres[:2] if ya==HALL_FRONT else centres[2:]):
                # Upper frames fit between the lower window row and the
                # eave girder plates, with the native aspect ratio retained.
                atlas_window(g,x+(.055 if x>5 else -.055),yy,h-.62,.52,'right' if x>5 else 'left','porthole',reveal=IRON)
        if x>5:
            # Press side: large single panes looking onto the testing press,
            # one centred in each bay.
            for yy in centres:atlas_window(g,x+.055,yy,3.15,.74,'right','single')
            girder(g,(x+.06,HALL_FRONT+.13,2.2),(x+.06,HALL_STEP-.15,4.6),.15)
        else:
            # Service side: three-pane verticals centred in the bays, with the
            # pipe risers between the windows and the piers.
            for yy in centres:
                atlas_window(g,x-.055,yy,4.6,.42,'left','triple')
            for yy in (front_stile+.34,HALL_STEP+.34,rear_stile-.39):
                flanged_pipe(g,[(x-.18,yy,2.7),(x-.18,yy,5.2),(x-.18,yy+.2,5.2)],.045)
    # Sheet joints keep clear of the step facade planes and fasteners.
    shed_roof(g,ROOF_X0,ROOF_X1,HALL_FRONT-.27,HALL_STEP+.266,front_roof_z(ROOF_X0),front_roof_z(ROOF_X1),351)
    shed_roof(g,ROOF_X0,ROOF_X1,HALL_STEP-.22,HALL_REAR+.25,rear_roof_z(ROOF_X0),rear_roof_z(ROOF_X1),352)
    # Furnace and kiln-test flues: combustion smoke while the lab works.
    stack(g,4.15,6.8,7.12,.78,emits='smoke')
    stack(g,7.30,2.80,4.95,.85,emits='smoke')
    # Timber and metal joints remain deliberately legible at normal game zoom.
    # Interior joints only; the corners carry the cast shell's own straps.
    for i in range(1,4):
        x=bx0+.075+(bx1-bx0-.15)*i/4
        for z in (.35,1.65):
            g.box((x,by0-.025,z),(.15,.06,.38),IRON)
            for dz in (-.10,.10):steel_bolt(g,(x,by0-.065,z+dz),r=.023)
    # 2026-10-22 (user): no forced decoration beyond the walls. The outdoor
    # specimen shelves before and behind the hall, the rear planters, the
    # barrel and the crate are gone; the footprint ends at the hall's rear
    # cast base (10x9 -> 10x8) and the freed front cells are open ground.
    instrument_tower(g,9.0,6.0,base=(7.925,5.075,9.925,6.925))
    testing_press(g,parts,9.0,2.18,base=(7.925,1.075,9.925,2.925),flywheel_x=7.02)
    # Ground-side shaft socket and a bank of valved services, in relief on
    # the x=8 face of the cast base (transput (7,4,0) Right).
    g.cylinder((bx1-.15,4.58,.72),.18,.40,IRON,'X',20)
    g.ring((bx1+.04,4.58,.72),.27,.07,.07,IRON,'X',20)
    for y in (4.05,4.40):
        flanged_pipe(g,[(bx1+.05,y,.40),(bx1+.05,y,3.95),(HALL_X1+.05,y,3.95)],.045)
        g.wheel((bx1+.02,y-.17,1.25),.12,'X',IRON,BRASS)
    for x,y,z in ((8.58,3.0,4.12),(HALL_X1+.06,6.9,3.8),(3.45,HALL_FRONT-.105,4.2),(1.5,6.75,3.8)):
        cage_lamp(g,x,y,z)
    service_bay(g)
    return rails


def animate_press(obj,frame_end):
    if frame_end!=121:raise ValueError('Laboratory press requires a 121-frame loop')
    base=obj.location.z
    for frame,offset in ((1,0),(31,-.22),(46,-.22),(76,0),(121,0)):
        obj.location.z=base+offset;obj.keyframe_insert(data_path='location',frame=frame)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:key.interpolation='LINEAR'
