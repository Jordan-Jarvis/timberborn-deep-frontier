"""Reinforced turbine study from the two original isometric concept views.

The concrete conduit, high dam cap and side workshop determine the form.
This file does not register a game footprint or claim working water controls.
Its open conduit contains no decorative water: runtime water must be native.

Compacted 2026-10-30 (outputs/compaction/BRIEF.md): 8x10x7 -> 8x10x6. The
conduit, the dam cap (support surface at layer 6), the gates, the water cells
and the service terrace with its built-in walkways are gameplay and stay
exactly as they were. The workshop on the terrace is one storey (layer 2 to
3.84) under its plank gable roof (roof-variety pass: a real pitched roof, no
dormer, no roof vent), so nothing rises above the dam cap.

Shrunk again 2026-11-01 (user: "we need to shrink the buildings down even
more"): 8x10x6 -> 4x6x6. The conduit, the dam cap (support surface at layer
6), the gates, intakes, outlets and every water cell are unchanged. The
downstream foundation, its terrace and the gabled workshop beside the
conduit (tiles 4..8 x 4..10) are gone: a cast headwall now closes the
casing's crown over the downstream lanes, and on it, behind the cap, an
enclosed generator house and an open generator bay share a flat concrete
roof whose top is layer 5 (the player-path deck). The generator turns to run
downstream; the dam continuation beside the cap stays outside the footprint
for the player's own dam blocks, as before. The workshop door went with the
workshop (the turbine has no workers or entrance).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON
from reference_materials import CIVIC_CONCRETE, CIVIC_FORGED_PANEL
from industrial_facades import window_y, side_window
from industrial_door_components import hydro_workshop_door
from industrial_budget import round_pipe, cage_lamp, machinery_shell, band
from civic_isometric_geometry import framed_room, gabled_roof, roof_bearing, dormer, gauge, handwheel, steel_bolt
from walkway_geometry import RailAssembly

# Triangle budget, 20k grand cap (2026-10-29): no fastener heads (the civic
# shell family's rule, civic_isometric_geometry.collar), half as many
# generator fins and lead-screw threads, and 12-24 sides on the large round
# parts.


def arch_band(g, y, width, outer, inner, material, *, center=2.0, spring=1.0, foot=.36, segments=24):
    """Open semicircular conduit crown with straight feet at either side."""
    for i in range(segments):
        a, b = i*math.pi/segments, (i+1)*math.pi/segments
        verts = [(center+math.cos(t)*r, yy, spring+math.sin(t)*r)
                 for yy in (y-width/2, y+width/2)
                 for r in (inner, outer) for t in (a,b)]
        g.add(verts, [(0,2,3,1),(4,5,7,6),(0,1,5,4),
                      (2,6,7,3),(0,4,6,2),(1,3,7,5)], material)
    for direction in (-1,1):
        x = center+direction*(inner+outer)/2
        g.box((x,y,(spring+foot)/2), (outer-inner,width,spring-foot), material)


def flange(g,y,outer=2.04,inner=1.00,width=.13):
    # 26 segments: its joints never share a radial plane with the casing's 24.
    arch_band(g,y,width,outer,inner,IRON,foot=.42,segments=26)
    # Only the two springing bolts of each face stay (of nineteen): they stand
    # in the cell faces over the conduit feet (native 0,3,1 and 3,3,1
    # Bottom), which the connection-face measurement keeps unconnectable.
    for i in (0,18):
        angle=i*math.pi/18
        x=2.0+math.cos(angle)*(outer-.14)
        z=1+math.sin(angle)*(outer-.14)
        for yy in (y-width/2-.012,y+width/2+.012):
            steel_bolt(g,(x,yy,z),'Y',.032)


def cast_conduit(g):
    # A continuous open arch, with shallow casting joints at each segment.
    for i in range(10):
        arch_band(g,.30+i*.60,.60,1.92,1.02,CIVIC_CONCRETE)
    # The outlet flange's bolts stay inside the casing's y<6 cells.
    for y in (.12,1.72,3.87,5.90):
        flange(g,y)
    for x in (.50,3.50):
        g.box((x,3.0,.18),(1.0,6.0,.36),CIVIC_CONCRETE)
        for y in (.35,1.55,4.05,5.75):
            g.box((x,y,.36),(.21,.44,.055),IRON)
    # Long crown straps attach the casing sections to the tall dam pier.
    for angle in (.23,math.pi/2,math.pi-.23):
        x=2.0+math.cos(angle)*1.95
        z=1+math.sin(angle)*1.95
        for a,b in ((.14,1.92),(4.05,5.93)):
            g.beam((x,a,z),(x,b,z),.12,.05,IRON)
    # Intake grate leaves the outlet open; both ends remain visually legible.
    for i in range(11):
        x=1.04+i*.192
        top=1+math.sqrt(1.00**2-(x-2.0)**2)
        g.box((x,.075,top/2),(.043,.065,top-.04),IRON)
    for z in (.60,1.08):
        g.box((2.0,.015,z),(1.92,.08,.065),IRON)
    g.box((2.0,-.018,.82),(.31,.06,.37),IRON)


def dam_cap(g):
    # The workshop sits alongside this substantial square cap. The conduit
    # crown stays open below it; no solid box is hidden across the passage.
    # Cast faces lie on the y=2 and y=4 tile edges; the open conduit cells
    # either side (y=1 and y=4 rows above the casing) stay clear.
    g.box((2.0,3.0,4.12),(3.98,2.0,3.52),CIVIC_CONCRETE)
    for x in (.48,3.52):
        g.box((x,3.0,1.683),(.94,2.0,1.354),CIVIC_CONCRETE)  # 6 mm above the spring plane
    for z in (2.65,3.5,4.35,5.2):
        for y in (1.992,4.008):
            g.box((2.0,y,z),(3.85,.008,.012),IRON)
        for x in (.008,3.992):
            g.box((x,3.0,z),(.008,2.0,.012),IRON)
    for x in (.13,3.87):
        for y in (2.065,3.935):
            g.box((x,y,4.17),(.16,.17,3.62),IRON)
            for z in (2.58,3.48,4.44,5.64):
                g.box((x,y,z),(.28,.25,.46),IRON)
    # Cast support surface is exactly layer six. Bolts remain below its top.
    for x in range(4):
        for y in (2,3):
            g.box((x+.5,y+.5,5.94),(.988,.988,.12),CIVIC_CONCRETE)
    for x in (.12,3.88):
        for y in (2.155,3.845):
            g.box((x,y,5.85),(.34,.34,.23),IRON)
    # Gate lead screw and handwheel on the upstream face.
    g.cylinder((2.0,1.80,4.05),.075,2.55,IRON,'Z',16)
    for z in (3.03,4.18,5.25):
        g.box((2.0,1.83,z),(.42,.25,.19),IRON)
    # Thread collars every 15 cm (was 7.5), 8 sides, without the inner face
    # (on the screw): 13 where there were 25.
    for i in range(13):
        band(g,(2.0,1.8,3.02+i*.15),.092,.018,.028,IRON,'Z',8)
    handwheel(g,(2.0,1.63,5.08),.38,'Y',IRON,IRON)
    g.box((2.0,1.83,2.74),(.51,.37,.43),IRON)
    gauge(g,2.0,1.61,2.75,.14,rim_material=IRON)
    # (The back pressure lines and inspection panels on the y=4 face went in the
    # 2026-11-01 shrink: the powerhouse now stands against that face.)


def generator(g,parts):
    # In the open generator bay at the right of the powerhouse, its axis running
    # downstream. The exposed shaft/coupler carries the motion; housing and
    # bearings stay still.
    p=(GEN_X,4.72,3.62)
    machinery_shell(g,p,[(-.58,.34),(-.47,.46),(.33,.46),(.5,.3)],'Y',24,fastener_material=IRON)
    for y in (4.4,5.0):
        g.box((GEN_X,y,3.13),(.78,.3,.26),CIVIC_CONCRETE)
        g.box((GEN_X,y,3.29),(.82,.34,.06),IRON)
    # Five cooling fins, 24 sides like the shell, without the inner face.
    for i in range(5):
        band(g,(GEN_X,4.4+i*.13,3.62),.48,.03,.025,IRON,'Y',24)
    for x in (GEN_X-.36,GEN_X+.36):
        round_pipe(g,[(x,4.3,3.4),(x,4.3,4.05),(x,4.95,4.05)],.04)
    rotor=Geometry('Hydro.GeneratorCoupling',(GEN_X,5.5,3.62))
    rotor.cylinder((GEN_X,5.47,3.62),.11,.5,IRON,'Y',12)
    for y in (5.33,5.63):
        rotor.cylinder((GEN_X,y,3.62),.23,.08,IRON,'Y',16)
    parts.append((rotor,'Y',1))
    g.box((GEN_X,5.8,3.31),(.5,.12,.62),IRON)
    g.ring((GEN_X,5.8,3.62),.2,.1,.13,IRON,'Y',16)


def runner(parts):
    # A visible turbine rotor inside the downstream mouth, mechanically linked
    # by its own authored loop. Runtime will drive both from measured operation.
    runner=Geometry('Hydro.TurbineRunner',(2.0,4.92,1.05))
    runner.cylinder((2.0,4.92,1.05),.19,.28,IRON,'Y',12)
    runner.ring((2.0,4.92,1.05),.85,.055,.10,IRON,'Y',24)
    for i in range(8):
        a=i*math.pi/4
        verts=[]
        for y in (4.79,5.03):
            for radius,t in ((.18,a),(.78,a+.24),(.78,a+.47),(.18,a+.2)):
                verts.append((2.0+math.cos(t)*radius,y,1.05+math.sin(t)*radius))
        runner.add(verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),
                          (1,2,6,5),(2,3,7,6),(3,0,4,7)],IRON)
    parts.append((runner,'Y',1))


# Powerhouse (2026-11-01 second shrink): on a concrete headwall over the
# downstream conduit (tiles 0..4 x 4..6), behind the dam cap's y=4 face. An
# enclosed generator house on the left, the open generator bay on the right,
# both under one flat concrete roof whose top is layer 5: the player-path deck.
PH_Y0,PH_Y1=4.0,5.98     # the casing's last arch band stands 2 cm proud at y=6
HEAD_TOP=3.0             # headwall top and powerhouse floor (layer 3)
PH_TOP=4.84              # roof slab bottom; its top is layer 5
WS_X0,WS_X1=.06,2.5      # enclosed generator house
GEN_X=3.25               # generator axis in the open bay (x 2.5..4)


def headwall(g):
    # Solid cast headwall closing the casing's crown over the downstream lanes;
    # the lanes and the arch below it stay open (inner crown 2.02).
    g.box((2.0,(PH_Y0+PH_Y1)/2,(2.05+HEAD_TOP)/2),(4.0,PH_Y1-PH_Y0,HEAD_TOP-2.05),CIVIC_CONCRETE)
    for x in (.25,3.75):   # spandrel walls over the arch shoulders
        g.box((x,(PH_Y0+PH_Y1)/2,(.36+2.05)/2),(.5,PH_Y1-PH_Y0,2.05-.36),CIVIC_CONCRETE)
    for z in (2.3,2.75):
        g.box((2.0,PH_Y1+.004,z),(3.85,.008,.012),IRON)


def powerhouse(g):
    framed_room(g,WS_X0,PH_Y0+.06,WS_X1,PH_Y1-.06,HEAD_TOP,PH_TOP,2,infill=CIVIC_FORGED_PANEL)
    rear=PH_Y1-.02
    for x in (WS_X0+(WS_X1-WS_X0)*.25,WS_X0+(WS_X1-WS_X0)*.75):
        window_y(g,x,rear,3.95,.75,'back')
    side_window(g,WS_X0-.02,5.0,3.95,.75,'left')
    # Generator bay: two corner posts carry the roof; the bay stays open on its
    # right and downstream sides so the generator and coupling read.
    for y in (PH_Y0+.1,PH_Y1-.1):
        g.box((3.9,y,(HEAD_TOP+PH_TOP)/2),(.16,.16,PH_TOP-HEAD_TOP),IRON)
    g.box((3.9,(PH_Y0+PH_Y1)/2,PH_TOP-.08),(.14,PH_Y1-PH_Y0-.36,.12),IRON)
    cage_lamp(g,WS_X1+.09,5.0,4.2)
    # Flat concrete roof, open edge to edge: the turbine's player-path deck.
    g.box((2.0,(PH_Y0+PH_Y1)/2,PH_TOP+.08),(4.0,PH_Y1-PH_Y0,.16),CIVIC_CONCRETE)
    for z in (PH_TOP+.03,):
        g.box((2.0,PH_Y1+.004,z),(3.9,.008,.012),IRON)


def hydro(g,parts):
    rails=RailAssembly('HydroRails',cap_material=IRON)
    cast_conduit(g);dam_cap(g)
    runner(parts)
    headwall(g)
    generator(g,parts);powerhouse(g)
    # No terrace rails or roof props: paths run off the roof deck onto a
    # neighbouring turbine or platform at any edge.
    return rails
