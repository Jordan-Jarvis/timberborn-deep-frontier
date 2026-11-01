"""Stone crusher, 3x3 workshop (2026-11-01 second shrink pass).

A YouTuber's first look called several Deep Frontier buildings "massive";
the user: "we need to shrink the buildings down even more". The 4x4x3
crusher (2026-10-30 compaction) becomes a 3x3x3 workshop with the same
machinery, materials and animations:

- one closed timber-framed plank workshop on the ground (all nine cells),
  its door on tile column 1 in the front wall,
- its flagstone roof is the machine floor (layer 1): the two toothed
  crushing rolls on bearing pedestals, the flywheel and its pillow block in
  the front-left corner, chained to the first roll by two sprockets, and the
  feed hopper standing over the rolls on two timber end frames, its funnel
  over the nip; the crushed stone drops through a grate into the workshop,
- the floor's two open cells (the west column's middle and rear) are an open
  platform.
The external porch, the chute-fed output bin and the two short machine roofs
are gone (no clutter on open cells).

Authored in native grid XY; the layout origin is (-1,-2,0), so the artwork
frame is grid + (1,2) (GRID below). No walkways, decks or balconies.
"""
import math
import random
from frontier_architecture import *
from reference_materials import CRUSHER_STEEL,KILN_SOOT,KILN_STONE
from industrial_kit import (open_beam,lean_wheel as wheel,lean_gauge as gauge)
from industrial_kit import (steel_bolt,lean_bracket as bracket,lean_timber_column as timber_column,lean_beam_joint as beam_joint,lean_cage_lamp as cage_lamp,band,prism,bolt,square_nut,open_box,lean_rock as rock,skin_board)
from industrial_facades import side_window,window_y
from walkway_geometry import RailAssembly
from industrial_door_components import recipe as door_recipe
from factory_registration import RigidPlacement,flagstone_slab
from industrial_levels import CRUSHER_DECK as DECK_Z

# Artwork frame = native grid + GRID (layout origin (-1,-2,0)).
GRID=(1,2,0)
# Workshop: walls on the x=0, x=3 and y=3 tile lines (plank skins 0.04
# inside), the front wall's face WALL_FRONT behind the y=0 edge; the native
# door is centred on tile column 1, its casing .04 ahead of that wall.
WALL_FRONT=.14
ROOM_X0,ROOM_X1,ROOM_REAR=0.0,3.0,3.0
# Machine floor: flagstone slab, top on layer 1.
SLAB=.20
# Rolls (axis Y) side by side, centred on the floor's east two columns.
ROLLS=(1.72,2.55)
ROLL_Y,ROLL_Z=1.80,DECK_Z+.50
PILLOWS=(.76,2.84)
# Flywheel in the front-left corner; both sprockets on the front line.
WHEEL=(.62,.62,DECK_Z+.50)
WHEEL_R=.48
SPROCKET_Y=.45
# Hopper: rim over the rolls, funnel over the nip (x 2.135).
HOPPER=(1.32,.64,2.93,2.86)
HOPPER_BOTTOM,HOPPER_TOP=2.00,2.60
FRAME_Y=(.58,2.92)
FRAME_X=(1.30,2.92)


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
    # Shaft ends stop inside the bearing housings' faces.
    prism(g,p,.075,length+.30,CRUSHER_STEEL,'Y',6)
    # Separate wear segments carry broad rectangular teeth (eight per
    # segment), bronze collars divide them.
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


def flywheel(g,p,r):
    # The reviewed six-spoke wheel at radius r (it was .665).
    x,y,z=p;k=r/.665
    band(g,p,r,.105*k,.21,IRON,'Y',16,inner=True)
    prism(g,p,.14*k,.29,IRON,'Y',10)
    for i in range(6):
        a=i*math.pi/3
        for j in range(3):
            r0=(.11+j*.15)*k;r1=r0+.16*k;a0=a+j*.045;a1=a+(j+1)*.045
            g.beam((x+math.cos(a0)*r0,y,z+math.sin(a0)*r0),
                   (x+math.cos(a1)*r1,y,z+math.sin(a1)*r1),(.135-j*.018)*k,.12,IRON)


def sprocket(g,x,y,z):
    prism(g,(x,y,z),.205,.075,IRON,'Y',12)
    for i in range(12):
        a=i*2*math.pi/12
        open_beam(g,(x+math.cos(a)*.19,y,z+math.sin(a)*.19),(x+math.cos(a)*.228,y,z+math.sin(a)*.228),.043,.07,IRON)


def room(g,art):
    """The closed workshop under the machine floor. Windows and the sealed
    volume are authored on the artwork target `art` (grid + GRID)."""
    def A(x,y):return x+GRID[0],y+GRID[1]
    top=DECK_Z-SLAB
    # Timber frame: corner and middle posts on the outer faces.
    for x in (ROOM_X0+.10,1.50,ROOM_X1-.10):
        timber_column(g,x,ROOM_REAR-.10,.0,top,.18)
    for x in (ROOM_X0+.10,ROOM_X1-.10):
        for y in (WALL_FRONT+.10,1.55):timber_column(g,x,y,.0,top,.18)
    # Plank skins: west and east (outer faces .0375 inside the x=0 / x=3
    # edges), rear (.0375 inside y=3).
    count=12;y0,y1=WALL_FRONT+.20,ROOM_REAR-.20
    for x,inner in ((ROOM_X0+.075,'+x'),(ROOM_X1-.075,'-x')):
        for j in range(count):
            y=y0+(j+.5)*(y1-y0)/count
            skin_board(g,(x,y,(.06+top)/2),(.075,(y1-y0)/count,top-.06),'Y',j,count,PLANK,inner)
    count=12;x0,x1=ROOM_X0+.20,ROOM_X1-.20
    for j in range(count):
        x=x0+(j+.5)*(x1-x0)/count
        skin_board(g,(x,ROOM_REAR-.075,(.06+top)/2),((x1-x0)/count,.075,top-.06),'X',j,count,PLANK,'-y')
    # Front wall: boards either side of the door (face WALL_FRONT), up to the
    # floor's underside; the native door insert fills tile column 1.
    for a,b in ((ROOM_X0+.20,1.0),(2.0,ROOM_X1-.20)):
        n=4
        for i in range(n):
            x=a+(i+.5)*(b-a)/n
            skin_board(g,(x,WALL_FRONT+.0375,(.06+top)/2),((b-a)/n,.075,top-.06),'X',i,n,PLANK,'+y')
    # Stone sill under the skins, 2 cm proud of them.
    for x,face in ((ROOM_X0+.03,'+x'),(ROOM_X1-.03,'-x')):
        open_box(g,(x,(WALL_FRONT+ROOM_REAR)/2,.03),(.06,ROOM_REAR-WALL_FRONT-.40,.06),KILN_STONE,('-z',face))
    open_box(g,(1.5,ROOM_REAR-.03,.03),(2.60,.06,.06),KILN_STONE,('-z','-y'))
    # Small panes in the one-layer walls.
    side_window(art,*A(ROOM_X0+.0375,1.05),.40,.42,'left')
    side_window(art,*A(ROOM_X1-.0375,2.20),.40,.42,'right')
    window_y(art,*A(.75,ROOM_REAR-.0375),.40,.42,'back')
    window_y(art,*A(2.30,ROOM_REAR-.0375),.40,.42,'back')
    # Instruments and a lamp beside the door.
    g.box((.55,WALL_FRONT-.04,.55),(.30,.08,.30),IRON)
    gauge(g,.55,WALL_FRONT-.096,.59,.078)
    cage_lamp(g,2.12,WALL_FRONT-.02,.78)
    # The closed workshop: its walls, the floor slab and the door insert seal it.
    art.declare_hidden_volume((*A(ROOM_X0+.12,WALL_FRONT+.08),.06),(*A(ROOM_X1-.12,ROOM_REAR-.12),top-.02))


def machine_floor(g):
    # Flagstone roof of the workshop: the floor the machinery stands on and,
    # in the west column's middle and rear cells, an open platform. Stone
    # masonry, not concrete: the crusher unlocks before concrete exists.
    # In the door column the slab starts 1 cm behind the casing's plane.
    flagstone_slab(g,ROOM_X0,WALL_FRONT,1.0,ROOM_REAR,DECK_Z,SLAB,seed=1)
    flagstone_slab(g,1.0,WALL_FRONT+.01,2.0,ROOM_REAR,DECK_Z,SLAB,seed=2)
    flagstone_slab(g,2.0,WALL_FRONT,ROOM_X1,ROOM_REAR,DECK_Z,SLAB,seed=3)
    # Grate over the drop under the rolls' nip.
    mid=(ROLLS[0]+ROLLS[1])/2
    g.box((mid,ROLL_Y,DECK_Z+.004),(.30,1.40,.008),KILN_SOOT)
    for i in range(7):
        g.box((mid,ROLL_Y-.60+i*.20,DECK_Z+.015),(.36,.04,.03),IRON)


def machinery(g,parts,place):
    m=place
    # Bearing pedestals and pillow blocks at both ends of each roll.
    for x in ROLLS:
        for y in PILLOWS:
            g.box((x,y,DECK_Z+.13),(.34,.30,.26),WOOD)
            pillow_block(g,x,y,ROLL_Z)
            # Replaceable cheek plate, jacking screw and oil cup.
            g.box((x,y-.18 if y<ROLL_Y else y+.18,ROLL_Z-.20),(.28,.025,.22),CRUSHER_STEEL)
            prism(g,(x+.17,y,ROLL_Z-.16),.024,.32,IRON,'Z',6)
            prism(g,(x+.17,y,ROLL_Z+.04),.052,.045,BRASS,'Z',6)
    for i,x in enumerate(ROLLS):
        p=(x,ROLL_Y,ROLL_Z);r,node=m.moving_part('ReferenceCrusherRoller'+str(i+1),p)
        toothed_roller(r,p,i*.5);parts.append((node,'Y',1 if i==0 else -1))
    # Flywheel, its shaft into the pillow block behind it on a timber
    # pedestal, and the drive sprocket in front of it.
    wx,wy,wz=WHEEL
    p=WHEEL;r,node=m.moving_part('ReferenceCrusherFlywheel',p)
    flywheel(r,p,WHEEL_R)
    prism(r,(wx,(SPROCKET_Y+.90)/2,wz),.07,.90-SPROCKET_Y+.10,CRUSHER_STEEL,'Y',8)
    parts.append((node,'Y',1))
    g.box((wx,.90,DECK_Z+.13),(.42,.36,.26),WOOD)
    pillow_block(g,wx,.90,wz)
    # Sprockets keep their reviewed node names (they were placed by x).
    for x,name in ((wx,'ReferenceCrusherDriveSprocket0.61'),(ROLLS[0],'ReferenceCrusherDriveSprocket1.96')):
        p=(x,SPROCKET_Y,ROLL_Z);r,node=m.moving_part(name,p)
        sprocket(r,x,SPROCKET_Y,ROLL_Z)
        parts.append((node,'Y',1))
    # Chain runs between the sprockets, top and bottom.
    n=10;a,b=wx+.07,ROLLS[0]-.07
    for z in (ROLL_Z-.21,ROLL_Z+.21):
        for i in range(n):
            open_box(g,(a+(i+.5)*(b-a)/n,SPROCKET_Y,z),((b-a)/n-.008,.078,.028),IRON,('-z',))


def hopper(g):
    """Feed hopper on two timber end frames over the rolls; its funnel ends
    over the nip, its load of limestone shows above the rim."""
    x0,y0,x1,y1=HOPPER
    mid=(ROLLS[0]+ROLLS[1])/2
    bx0,bx1,by0,by1=mid-.16,mid+.16,y0+.30,y1-.30
    bottom,top=HOPPER_BOTTOM,HOPPER_TOP
    # End frames: two posts and a cross beam at each end.
    for y in FRAME_Y:
        for x in FRAME_X:timber_column(g,x,y,DECK_Z,bottom-.07,.14)
        g.box(((FRAME_X[0]+FRAME_X[1])/2,y,bottom-.035),(FRAME_X[1]-FRAME_X[0]+.14,.14,.07),WOOD)
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
    g.box(((x0+x1)/2,(y0+y1)/2,top-.22),(x1-x0-.20,y1-y0-.20,.12),LIME)
    rng=random.Random(830)
    for j in range(4):
        for i in range(3):
            x=x0+.30+i*.50+rng.uniform(-.04,.04);y=y0+.28+j*.53+rng.uniform(-.05,.05);s=rng.uniform(.32,.42)
            rock(g,(x,y,top-.12+rng.uniform(-.02,.06)),(s,s*.82,s*.80),LIME,i+j*5+700)
    # Feed gate on the hopper's west side: handwheel, screw and guides.
    for y in (y0+.40,y1-.40):g.box((x0-.06,y,top-.25),(.055,.08,.36),IRON)
    g.box((x0-.05,(y0+y1)/2,top-.27),(.045,y1-y0-.70,.16),CRUSHER_STEEL)
    prism(g,(x0-.14,(y0+y1)/2,top-.27),.027,.20,IRON,'X',6)
    band(g,(x0-.25,(y0+y1)/2,top-.27),.127,.024,.035,IRON,'X',8,inner=True)


def crusher(g,parts):
    rails=RailAssembly("WalkwayRail")
    grid=RigidPlacement(g,GRID)
    g.include_component(door_recipe('StoneCrusher','Door.GroundDoor'))
    room(grid,g)
    machine_floor(grid)
    machinery(grid,parts,grid)
    hopper(grid)
    return rails
