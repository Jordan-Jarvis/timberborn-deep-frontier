"""Original Materials Laboratory from its two isometric concept views.

Stepped sawtooth testing halls, enclosed records wing, cast foundations,
instrument tower and a working screw press. Artwork sets the envelope; no
top-view or printed footprint is consulted. The public terrace is layer one.

2026-10-30 compaction (user: "currently we have two layers between floors,
we should reduce it to one"; flat roofs): the cast bases are one layer, the
public terrace is layer one, the records office is one layer under a flat
cast roof, and the sawtooth testing hall, instrument tower and press are
lower. The sawtooth sheds stay: they are the laboratory's silhouette.
10x8x9 -> 10x8x5.

Second shrink pass (2026-11-01, user: "shrink the buildings down even
more"): 10x8x5 -> 5x4x3. The sawtooth testing hall on a 3x3 cast base, a
one-tile entrance annex in front of it with the ground door (same door
cell) and the terrace on its roof, the press and the instrument tower on
their 2x2 plinths in the right column. The records office and its terrace
door went; the tower is lower.
"""
import math
import random

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
from reference_materials import CIVIC_CONCRETE, CIVIC_FORGED_PANEL, GLASS, KILN_SOOT
from industrial_budget import bin as budget_bin, band
from civic_isometric_geometry import collar, gauge, handwheel
from industrial_facades import building_portal, window_y, side_window
from architectural_windows import window
from native_window_atlas import atlas_window, glass_curtain
from industrial_budget import round_pipe, cage_lamp
from civic_isometric_geometry import framed_room, gabled_roof, roof_bearing, timber_column
from native_building_assets import barrel, plant
from walkway_geometry import RailAssembly
from lategame_kit import emitter

# Triangle budget, 20k grand cap (2026-10-29): no fastener heads (the civic
# shell family's rule, civic_isometric_geometry.collar), no sub-pixel soot
# streaks or tower rivets, roof sheets about 40 cm wide (was 25-28), 8-side
# pipe flanges, lean valve wheels and gauges, 12-24 sides on round parts.


def concrete_course(g,x0,y0,x1,y1,top,door=None,cap=True,*,left_wall=True,left_straps=True,front_from=None,back_from=None,strap_rows=None):
    """Closed cast shell with narrow recessed joints and steel corner straps.

    front_from/back_from start the front/back wall at another x (a plinth
    abutting a neighbour's wall: cover its corner, never share its footprint).
    strap_rows limits the corner straps to those wall lines (y0 and/or y1),
    where the other corner meets a neighbouring course's own strap.
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
    # One strap per corner on a one-layer course (2026-10-30); the two of a
    # two-layer course would overlap there.
    straps=((.45,.46),(top-.4,.46)) if top>=1.5 else ((top/2,min(.46,top-.30)),)
    for x in ((x0,x1) if left_straps else (x1,)):
        for y in ((y0,y1) if strap_rows is None else strap_rows):
            for z,h in straps:
                g.box((x,y,z),(.24,.24,h),IRON)


def girder(g,a,b,width=.22,*,plate_stations=(.12,.88)):
    g.beam(a,b,width,.18,WOOD)
    for t in plate_stations:
        p=tuple(a[i]+(b[i]-a[i])*t for i in range(3))
        if abs(b[1]-a[1])>abs(b[0]-a[0]):
            g.box((p[0]-width/2-.018,p[1],p[2]),(.035,.36,.30),IRON)
        else:
            front_half_depth=.09 if b[0]==a[0] else width/2
            g.box((p[0],p[1]-front_half_depth-.018,p[2]),(.36,.035,.30),IRON)


def shed_roof(g,x0,x1,y0,y1,left,right,seed):
    """Diagonal blue roof with visible rolled seams, straps and worn edges."""
    def z(x):return left+(right-left)*(x-x0)/(x1-x0)
    count=math.ceil((y1-y0)/.40)
    rng=random.Random(seed)
    for i in range(count):
        ya=y0+i*(y1-y0)/count;yb=y0+(i+1)*(y1-y0)/count
        g.add([(x0,ya,z(x0)),(x1,ya,z(x1)),(x1,yb,z(x1)),(x0,yb,z(x0)),
               (x0,ya,z(x0)-.065),(x1,ya,z(x1)-.065),(x1,yb,z(x1)-.065),(x0,yb,z(x0)-.065)],
              [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],ROOF)
        g.beam((x0,ya,z(x0)+.025),(x1,ya,z(x1)+.025),.025,mat=IRON)
        # Triangle budget: no 12 mm brass wear streaks (two per sheet could
        # overlap coplanar once the bevel modifier is gone).
    for y in (y0,y1):girder(g,(x0,y,z(x0)-.07),(x1,y,z(x1)-.07),.16)
    for x in (x0,x1):
        girder(g,(x,y0+.005,z(x)-.04),(x,y1-.005,z(x)-.04),.16)
    # The back strap stands 20 cm in, clear of the pier collars at the step.
    for y in (y0+.16,(y0+y1)/2,y1-.20):
        g.beam((x0,y,z(x0)+.05),(x1,y,z(x1)+.05),.055,.045,IRON)


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
    del seed  # it placed the soot streaks, removed for the triangle budget
    for i in range(n):
        a=x0+i*(x1-x0)/n;b=x0+(i+1)*(x1-x0)/n
        g.add([(a,y-.055,bottom),(b,y-.055,bottom),(b,y-.055,z(b)),(a,y-.055,z(a)),
               (a,y+.055,bottom),(b,y+.055,bottom),(b,y+.055,z(b)),(a,y+.055,z(a))],
              [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],PLANK)
    # The base rail butts between the corner stiles; its end caps do not
    # occupy the same plane as the plank end caps.
    # On the low step facade (2026-11-01) the base rail's plates would meet
    # the top rail's: it has none (it sits behind the front shed roof).
    girder(g,(x0+.11,y-.12,bottom+.04),(x1-.11,y-.12,bottom+.04),plate_stations=(.12,.88) if bottom<=1 else ())
    girder(g,(x0,y-.12,left-.08),(x1,y-.12,right-.08))
    for i in range(5):
        x=x0+(x1-x0)*i/4
        # Lower facades (2026-10-30): the upper plate stays clear of the
        # roof's edge girder, and a short stile has none.
        girder(g,(x,y-.12,bottom),(x,y-.12,z(x)),plate_stations=(.12,.70) if z(x)-bottom>=.8 else ())
        if i==4:continue
        cx=x+(x1-x0)/8;head=z(cx)-.32
        if tall_windows:
            # Testing-hall bays: full-height steel curtain glazing with big
            # native panes, so specimens can be inspected in daylight.
            low=bottom+.35
            glass_curtain(g,cx,y-.055,low,head,(x1-x0)/4-.30,'front',cols=2,rows=max(1,round((head-low)/.85)))
        else:
            # North-light ribbon on the sawtooth step, sized to the lower
            # step facade (2026-10-30).
            width=min(.84,3*(z(cx)-bottom-.22))
            atlas_window(g,cx,y-.055,bottom+.10+width/6,width,'front','ribbon')
    for a,b in ((x0,x0+(x1-x0)/4),(x1-(x1-x0)/4,x1)):
        # A low step facade (2026-10-30) has no room for the diagonal brace.
        if z(b)-.16-(bottom+.24)>=.40:girder(g,(a,y-.27,bottom+.24),(b,y-.27,z(b)-.16),.15)


def stack(g,x,y,bottom,height,*,emits):
    """Banded flue with a flared cowl. `emits` is the vanilla effect at its
    mouth (a lategame_kit.EMITTER_KINDS entry) or None; every caller decides.
    The emitter adds no geometry."""
    g.cylinder((x,y,bottom+height/2),.12,height,IRON,'Z',12)
    for z in (bottom+.1,bottom+.45,bottom+height-.14):
        g.ring((x,y,z),.17,.045,.075,IRON,'Z',12)
    g.cylinder((x,y,bottom+height+.02),.24,.13,IRON,'Z',12,.15)
    g.cylinder((x,y,bottom+height-.12),.14,.04,KILN_SOOT,'Z',12)
    if emits is not None:
        # Mouth: the cowl's top face (radius 0.15).
        emitter(g,emits,x,y,bottom+height+.085,.15)


def flanged_pipe(g,points,r=.065,segments=8):
    # 8-side flanges (was 16) except where a flange stands on a measured
    # connection face (measure_connection_faces.py).
    round_pipe(g,points,r)
    for a,b in zip(points,points[1:]):
        axis='XYZ'[next(i for i in range(3) if a[i]!=b[i])]
        for f in (.13,.86):
            p=tuple(a[i]+(b[i]-a[i])*f for i in range(3))
            g.ring(p,r*1.5,.03,.065,BRASS,axis,segments)


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
    rng=random.Random(seed);count=math.ceil((x1-x0)/.40)
    for i in range(count):
        x=x0+(i+.5)*(x1-x0)/count
        g.beam((x,y0,z0),(x,y1,z1),(x1-x0)/count,.045,ROOF)
    for x in (x0,x1):g.beam((x,y0,z0-.035),(x,y1,z1-.035),.13,.14,WOOD)
    for y,z in ((y0,z0),(y1,z1)):
        g.beam((x0,y,z-.055),(x1,y,z-.055),.15,.16,WOOD)
        for x in (x0,x1):
            # .17 collar (was .16): its nut heads stood 0.45 mm off the
            # side beam's face, inside the strict overlap tolerance.
            collar(g,x,y,z-.07,.17)
            g.box((x,y,z+.050),(.23,.23,.025),IRON)
    for t in (.35,.72):
        y=y0+(y1-y0)*t;z=z0+(z1-z0)*t+.03
        g.beam((x0,y,z),(x1,y,z),.06,.018,IRON)
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
# Second shrink pass (2026-11-01, 10x8x5 -> 5x4x3): the testing hall stands
# on a 3x3 cast base (x 0..3, y 1..4) behind a one-tile entrance annex
# (x 0..3, y 0..1, the ground door and the terrace on its roof); the press
# and the instrument tower keep their 2x2 plinths in the right column (press
# in front, y 0..2; tower behind, y 2..4). The timber upper hall stands back
# from its base so its frame, braces and roof trim stay inside the occupied
# cells (within a 12 cm edge sliver at the sides, 32/38 cm front and rear).
HALL_BASE=(0.0,1.0,3.0,4.0)            # x0,y0,x1,y1 outer faces
HALL_X0,HALL_X1=.18,2.85               # upper side board planes
HALL_FRONT,HALL_STEP,HALL_REAR=1.32,2.47,3.62
ROOF_X0,ROOF_X1=.04,2.98
STEP_BOTTOM=2.05                       # sawtooth step facade sill (was 2.43)
TOWER_SCALE=.36                        # instrument tower heights (was .62)


# Lower and shorter sheds (2026-11-01, were 3.10..2.35 and 3.60..2.85 over
# 4.86): the whole hall stays under three layers.
def front_roof_z(x):
    return 2.42+(1.97-2.42)*(x+.02)/2.94


def rear_roof_z(x):
    return 2.90+(2.45-2.90)*(x+.02)/2.94


def service_fittings(g):
    """Power Lines bracket and the Timber Pipes inlet (2026-11-01: the open
    service bay between the press and the tower went with the 10x8 plan).

    The insulator bracket stands on the hall's right upper wall over the
    press plinth's back half (PowerLineSpec point at the top insulator); the
    water inlet socket is on the tower plinth's rear face. Timber Pipes
    accepts any face; the socket marks the spot.
    """
    upper=HALL_X1+.055        # outer face of the upper hall boards
    g.box((upper+.03,1.85,1.75),(.06,.30,.30),IRON)
    g.beam((upper+.05,1.85,1.75),(upper+.30,1.85,1.75),.07,mat=IRON)
    for dz in (0,.09,.18):g.cylinder((upper+.30,1.85,1.80+dz),.045,.06,BRASS,'Z',8)
    g.cylinder((upper+.30,1.85,2.06),.02,.06,IRON,'Z',6)
    face,wx=4.0,4.6
    round_pipe(g,[(wx,face-.15,.2),(wx,face+.06,.2)],.08)
    g.ring((wx,face+.03,.2),.13,.05,.05,BRASS,'Y',16)
    g.wheel((wx,face+.035,.42),.11,'Y',IRON,BRASS)
    g.beam((wx,face+.035,.28),(wx,face+.035,.36),.03,mat=IRON)


def instrument_tower(g,x,y,*,base):
    """Instrument tower on its cast plinth, which abuts the hall: no left
    wall or straps, and its own cap starts where the hall's cap ends.

    Second shrink pass (2026-11-01): heights over the plinth top scaled
    TOWER_SCALE (was .62) so the tower stays under three layers; the barrel,
    bands, ribs, cap and fittings keep their plan proportions. The down pipe
    on the plinth's front face went (that face now abuts the press plinth).
    """
    def f(z):return 1+(z-2)*TOWER_SCALE
    bx0,by0,bx1,by1=base
    concrete_course(g,bx0,by0,bx1,by1,1,cap=False,left_wall=False,left_straps=False,
                    front_from=bx0+.075,back_from=bx0+.075,strap_rows=(by1,))
    cap_x0,cap_x1=bx0+.075,bx1+.075
    g.box(((cap_x0+cap_x1)/2,(by0+by1)/2,.92),(cap_x1-cap_x0,by1-by0+.15,.16),CIVIC_CONCRETE)
    g.cylinder((x,y,f(4.165)),.61,4.33*TOWER_SCALE,IRON,'Z',24)
    for z in (2.20,3.15,4.40,5.55,6.20):
        band(g,(x,y,f(z)),.65,.06,.11,BRASS,'Z',24)
    for i in range(12):
        a=i*math.tau/12
        g.beam((x+math.cos(a)*.612,y+math.sin(a)*.612,f(2.36)),
               (x+math.cos(a)*.612,y+math.sin(a)*.612,f(6.10)),.016,mat=BRASS)
    g.cylinder((x,y,f(6.66)),.91,.32,ROOF,'Z',16,.09)
    g.ring((x,y,f(6.36)),.92,.055,.07,IRON,'Z',16)
    for i in range(12):
        a=i*math.tau/12
        g.beam((x+math.cos(a)*.90,y+math.sin(a)*.90,f(6.39)),(x+math.cos(a)*.09,y+math.sin(a)*.09,f(6.97)),.024,mat=IRON)
    g.cylinder((x,y,f(7.02)),.085,.12,IRON,'Z',8,.035)
    for z,r in ((3.02,.15),(4.93,.17)):
        gauge(g,x+.32,y-.65,f(z),r)
    for offset in (-.72,.72):
        flanged_pipe(g,[(x+offset,y-.20,.60),(x+offset,y-.20,f(5.65)),(x+offset*.5,y-.20,f(5.65))],.055)
        for z in (2.65,4.9):g.box((x+offset,y-.2,f(z)),(.17,.18,.06),IRON)
        handwheel(g,(x+offset,y-.37,f(2.85)),.13,'Y',IRON,BRASS)
    # Header pipe onto the hall's right eave, just above the rear roof edge,
    # over the rear shed only.
    zh=rear_roof_z(ROOF_X1)+.13
    flanged_pipe(g,[(x-.60,y,zh),(x-1.05,y,zh),(x-1.05,y-.5,zh)],.11)


def testing_press(g,parts,x,y,*,base,flywheel_x,flywheel_y):
    # Heights over the plinth scaled .62 (h), the ram's stroke .14 (animate_press).
    def h(z):return .80+(z-1.55)*.62
    bx0,by0,bx1,by1=base
    # The front wall covers the annex's corner; the back wall starts at the
    # hall's face.
    concrete_course(g,bx0,by0,bx1,by1,.80,cap=False,left_wall=False,left_straps=False,
                    back_from=bx0+.075)
    # Own cap from the hall's x=3 face outward: never inside its wall.
    g.box(((bx0+.075+bx1+.075)/2,(by0+by1)/2,.80-.08),(bx1-bx0,by1-by0+.15,.16),CIVIC_CONCRETE)
    for xx in (x-.78,x+.78):
        girder(g,(xx,y-.1,h(1.6)),(xx,y-.1,h(4.56)),.24)
        g.box((xx,y,h(1.62)),(.48,.51,.14),IRON)
    # Two top plates sit between the upright fasteners, not through them.
    girder(g,(x-.85,y-.1,h(4.56)),(x+.85,y-.1,h(4.56)),.30,plate_stations=(.30,.70))
    g.box((x,y,h(2.03)),(1.20,.70,.20),IRON)
    g.box((x,y,h(2.31)),(.53,.5,.24),CIVIC_CONCRETE)
    for z in (2.05,4.43):
        g.cylinder((x,y,h(z)),.19,.14,IRON,'Z',12)
    screw=Geometry('MaterialsLaboratory.PressScrew',(x,y,h(3.68)))
    screw.cylinder((x,y,h(3.68)),.10,.87,IRON,'Z',12)
    # The same 14-turn thread in 8 segments per turn, its pitch scaled with
    # the press.
    for i in range(112):
        a=i*math.tau/8;b=(i+1)*math.tau/8
        screw.beam((x+math.cos(a)*.14,y+math.sin(a)*.14,h(3.0+i*.011875)),
                   (x+math.cos(b)*.14,y+math.sin(b)*.14,h(3.0+(i+1)*.011875)),.040,mat=BRASS)
    parts.append((screw,'Z',1))
    ram=Geometry('MaterialsLaboratory.TestRam',(x,y,h(2.98)))
    ram.box((x,y,h(2.98)),(1.12,.72,.18),IRON)
    ram.box((x,y,h(2.98)-.13),(.64,.54,.08),CIVIC_CONCRETE)
    parts.append((ram,'LAB_PRESS',1))
    gauge(g,x-.94,y-.18,h(3.22),.12)
    flanged_pipe(g,[(x-.95,y+.25,h(1.8)),(x-.95,y+.25,h(3.8)),(x-.2,y+.25,h(3.8))],.05)
    # The flywheel turns inside the testing hall, behind its front glazing,
    # on the hall floor (the base cap, top z=1); its rim clears the cap.
    # Radius .50 (was .73) so it stays under the lower front shed roof.
    fx,fy=flywheel_x,flywheel_y
    fz=1.0+.50-.04
    fly=Geometry('MaterialsLaboratory.Flywheel',(fx,fy,fz))
    fly.wheel((fx,fy,fz),.46,'Y',IRON,BRASS)
    fly.ring((fx,fy,fz),.50,.065,.19,IRON,'Y',24)
    parts.append((fly,'Y',-1))
    g.cylinder((fx,fy+.13,fz),.10,.57,IRON,'Y',12)
    for xx in (fx-.20,fx+.20):g.box((xx,fy+.18,(1.0+fz)/2),(.15,.30,fz-1.0),IRON)


def laboratory(g,parts):
    rails=RailAssembly('MaterialsLaboratory.Rail',cap_material=IRON)
    # Cast entrance annex (x 0..3, y 0..1), the terrace on its roof; no
    # integral stairs. Outer faces: x=0, y=0.015 (behind the door casing on
    # the y=0 edge), x=2.975 and y=1.
    concrete_course(g,.075,.09,2.90,.925,1,(1.5,1.0,1.0),cap=False,strap_rows=(.09,))
    # The cast opening and terrace slab already form the reveal and sill, so
    # the portal omits its own cavity faces (no duplicate surfaces). The
    # casing face lies on the y=0 tile edge, centred on tile x=1.
    building_portal(g,1.5,0.0,0,facade='grid')
    g.doorways.append({'id':'GroundDoor','position':[1.5,0.0,0],'outward':[0,-1],'width':1.0,'internalConnection':'BuildingInterior'})
    for x in (.52,2.48):atlas_window(g,x,.015,.48,.44,'front','grid9')
    atlas_window(g,0.0,.52,.52,.56,'left','band4')
    # Door lamps beside the entrance, arms on the wall face.
    for x in (1.09,1.91):cage_lamp(g,x,-.035,.62)
    # Terrace: the annex roof, on whole cell boundaries, open to its tile
    # edges (no rails, 2026-10-31) and clear of decor; a platformable roof
    # deck in front of the testing hall's glazing.
    g.box((1.4975,.5,.905),(2.995,1.0,.13),CIVIC_CONCRETE)
    for i in range(14):g.box((.11+i*2.78/13,.50,.985),(.185,.85,.03),PLANK)
    # (The records office, its terrace door and flat cast roof went in the
    # second shrink pass, 2026-11-01.)
    # Main hall: cast base on the x=0..3, y=1..4 tile edges; enclosed
    # sawtooth upper hall set back on its plinth.
    bx0,by0,bx1,by1=HALL_BASE
    concrete_course(g,bx0+.075,by0+.075,bx1-.075,by1-.075,1)
    right_front=front_roof_z(HALL_X1)-.042
    right_rear=rear_roof_z(HALL_X1)-.052
    left_front=front_roof_z(HALL_X0)-.032
    left_rear=rear_roof_z(HALL_X0)-.032
    slope_facade(g,HALL_X0,HALL_X1,HALL_FRONT,1,left_front,right_front,220,True)
    slope_facade(g,HALL_X0,HALL_X1,HALL_STEP,STEP_BOTTOM,left_rear,right_rear,221,False)
    slope_facade(g,HALL_X0,HALL_X1,HALL_REAR,1,left_rear,right_rear,222,True,1)
    # One bay per sawtooth section on each side (2026-11-01; two per section
    # before): the only side pier is the shared one at the step.
    centres=((HALL_FRONT+HALL_STEP)/2,(HALL_STEP+HALL_REAR)/2)
    for x,height_front,height_back in ((HALL_X0,left_front,left_rear),(HALL_X1,right_front,right_rear)):
        right=x>(HALL_X0+HALL_X1)/2
        for (ya,yb,h),yy in zip(((HALL_FRONT,HALL_STEP,height_front),(HALL_STEP,HALL_REAR,height_back)),centres):
            count=math.ceil((yb-ya)/.17)
            for i in range(count):g.box((x,ya+(i+.5)*(yb-ya)/count,(1+h)/2),(.11,(yb-ya)/count,h-1),PLANK)
            # The shared sawtooth pier stops just under the step facade.
            if ya==HALL_STEP:steel_column(g,x,ya,1,STEP_BOTTOM-.015,.22)
            girder(g,(x,ya,1.05),(x,yb,1.05),.20,plate_stations=(.2,.8))  # plates clear of the other section
            # Side eave beams butt against the front/rear frame thickness.
            girder(g,(x,ya+.22,h-.08),(x,yb-.22,h-.08),.20)
            if right:
                # Press side: a large single pane looking onto the press.
                atlas_window(g,x+.055,yy,1.45,.40,'right','single')
            else:
                # Service side: a three-pane vertical, and a porthole under
                # the eave where the wall is tall enough.
                atlas_window(g,x-.055,yy,1.55,.24,'left','triple')
                if h-.28-.13>=1.84:
                    atlas_window(g,x-.055,yy,h-.28,.26,'left','porthole',reveal=IRON)
        if not right:
            # Pipe risers between the windows and the step pier.
            for yy in (HALL_FRONT+.25,HALL_STEP+.25,HALL_REAR-.25):
                flanged_pipe(g,[(x-.18,yy,1.35),(x-.18,yy,2.10),(x-.18,yy+.2,2.10)],.045)
    # Sheet joints keep clear of the step facade planes and fasteners.
    shed_roof(g,ROOF_X0,ROOF_X1,HALL_FRONT-.27,HALL_STEP+.266,front_roof_z(ROOF_X0),front_roof_z(ROOF_X1),351)
    shed_roof(g,ROOF_X0,ROOF_X1,HALL_STEP-.22,HALL_REAR+.25,rear_roof_z(ROOF_X0),rear_roof_z(ROOF_X1),352)
    # The press (front) and the instrument tower (rear) on their 2x2 plinths
    # in the right column (x 3..5), abutting the hall's base.
    instrument_tower(g,4.0,3.0,base=(2.925,2.075,4.925,3.925))
    testing_press(g,parts,4.0,1.18,base=(2.925,.075,4.925,1.925),flywheel_x=1.95,flywheel_y=1.75)
    # Ground-side shaft socket on the hall base's left face (transput (0,2,0)
    # Left), 1 cm proud of the cast wall.
    g.cylinder((.14,2.5,.62),.18,.30,IRON,'X',12)
    cage_lamp(g,HALL_X1+.06,HALL_REAR-.25,1.80)
    service_fittings(g)
    return rails


def animate_press(obj,frame_end):
    if frame_end!=121:raise ValueError('Laboratory press requires a 121-frame loop')
    base=obj.location.z
    for frame,offset in ((1,0),(31,-.14),(46,-.14),(76,0),(121,0)):
        obj.location.z=base+offset;obj.keyframe_insert(data_path='location',frame=frame)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:key.interpolation='LINEAR'
