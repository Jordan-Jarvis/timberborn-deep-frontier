"""Reinforced turbine study from the two original isometric concept views.

The concrete conduit, high dam cap and side workshop determine the form.
This file does not register a game footprint or claim working water controls.
Its open conduit contains no decorative water: runtime water must be native.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON
from reference_materials import CIVIC_CONCRETE, CIVIC_FORGED_PANEL
from civic_isometric_geometry import steel_bolt
from industrial_facades import window_y, side_window, gauge
from industrial_door_components import hydro_workshop_door
from industrial_budget import round_pipe, cage_lamp, machinery_shell
from civic_isometric_geometry import framed_room, gabled_roof, roof_bearing, dormer
from walkway_geometry import RailAssembly


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
    for i in range(19):
        angle=i*math.pi/18
        x=2.0+math.cos(angle)*(outer-.14)
        z=1+math.sin(angle)*(outer-.14)
        for yy in (y-width/2-.012,y+width/2+.012):
            steel_bolt(g,(x,yy,z),'Y',.032)
    for x in (.16,3.84):
        for z in (.18,.56,.90):
            steel_bolt(g,(x,y-width/2-.015,z),'Y',.031)


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
            steel_bolt(g,(x,y,.40),'Z',.032)
    # Long crown straps attach the casing sections to the tall dam pier.
    for angle in (.23,math.pi/2,math.pi-.23):
        x=2.0+math.cos(angle)*1.95
        z=1+math.sin(angle)*1.95
        for a,b in ((.14,1.92),(4.05,5.93)):
            g.beam((x,a,z),(x,b,z),.12,.05,IRON)
            for y in (a+.13,b-.13):steel_bolt(g,(x,y,z+.035),'Z',.025)
    # Intake grate leaves the outlet open; both ends remain visually legible.
    for i in range(11):
        x=1.04+i*.192
        top=1+math.sqrt(1.00**2-(x-2.0)**2)
        g.box((x,.075,top/2),(.043,.065,top-.04),IRON)
    for z in (.60,1.08):
        g.box((2.0,.015,z),(1.92,.08,.065),IRON)
    g.box((2.0,-.018,.82),(.31,.06,.37),IRON)
    for x in (1.89,2.11):
        for z in (.71,.93):steel_bolt(g,(x,-.06,z),'Y',.023)


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
                for dz in (-.14,.14):
                    steel_bolt(g,(x,y-.145,z+dz),'Y',.028)
                    steel_bolt(g,(x-.155,y,z+dz),'X',.028)
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
        for x in (1.85,2.15):steel_bolt(g,(x,1.68,z),'Y',.025)
    for i in range(25):
        g.ring((2.0,1.8,3.02+i*.075),.092,.018,.028,IRON,'Z',12)
    g.wheel((2.0,1.63,5.08),.38,'Y',IRON,accent=IRON)
    g.box((2.0,1.83,2.74),(.51,.37,.43),IRON)
    gauge(g,2.0,1.61,2.75,.14,rim_material=IRON)
    # Back pressure lines and removable inspection panels.
    for x in (.55,3.45):
        round_pipe(g,[(x,4.065,2.5),(x,4.065,4.85),
                      (x,4.065,5.25),(2.0,4.065,5.25)],.055)
        for z in (2.9,4.35):
            g.box((x,4.05,z),(.22,.14,.11),IRON)


def generator(g,parts):
    # Exposed shaft/coupler carries the motion; housing and bearings stay still.
    p=(3.82,1.36,2.78)
    machinery_shell(g,p,[(-.76,.44),(-.61,.59),(.43,.59),(.64,.39)],'X',32,fastener_material=IRON)
    for x in (3.13,4.27):
        g.box((x,1.36,2.17),(.40,.95,.32),CIVIC_CONCRETE)
        g.box((x,1.36,2.35),(.44,.99,.07),IRON)
        for y in (.99,1.73):steel_bolt(g,(x,y,2.41),'Z',.033)
    for i in range(14):
        x=3.3+i*.064
        g.ring((x,1.36,2.78),.615,.032,.027,IRON,'X',32)
    for y in (.91,1.81):
        round_pipe(g,[(3.31,y,2.59),(3.31,y,3.30),(4.10,y,3.30)],.047)
    rotor=Geometry('Hydro.GeneratorCoupling',(4.7,1.36,2.78))
    rotor.cylinder((4.60,1.36,2.78),.14,.72,IRON,'X',20)
    for x in (4.43,4.83):
        rotor.cylinder((x,1.36,2.78),.29,.10,IRON,'X',24)
        for i in range(8):
            a=i*math.pi/4
            steel_bolt(rotor,(x+.065,1.36+math.cos(a)*.22,
                              2.78+math.sin(a)*.22),'X',.024)
    parts.append((rotor,'X',1))
    g.box((4.91,1.36,2.35),(.15,.63,.65),IRON)
    g.ring((4.91,1.36,2.78),.25,.12,.12,IRON,'X',24)
def runner(parts):
    # A visible turbine rotor inside the downstream mouth, mechanically linked
    # by its own authored loop. Runtime will drive both from measured operation.
    runner=Geometry('Hydro.TurbineRunner',(2.0,4.92,1.05))
    runner.cylinder((2.0,4.92,1.05),.19,.28,IRON,'Y',24)
    runner.ring((2.0,4.92,1.05),.85,.055,.10,IRON,'Y',32)
    for i in range(8):
        a=i*math.pi/4
        verts=[]
        for y in (4.79,5.03):
            for radius,t in ((.18,a),(.78,a+.24),(.78,a+.47),(.18,a+.2)):
                verts.append((2.0+math.cos(t)*radius,y,1.05+math.sin(t)*radius))
        runner.add(verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),
                          (1,2,6,5),(2,3,7,6),(3,0,4,7)],IRON)
    parts.append((runner,'Y',1))


# Workshop frame in powerhouse-local coordinates (+1, +4 to the native grid).
# Post outer faces sit on the x=4, y=6 and y=9 tile edges with the cladding
# 6 cm inside them. On the right the cladding itself lies on the x=7 edge, so
# the door insert (tile x=6.5, filling 6..7) closes flush against the side
# wall; those posts stand 4 cm proud. Bays are thirds of the frame, and every
# window is centred in its bay between posts.
WS_X0,WS_Y0,WS_X1,WS_Y1=3.10,2.10,5.94,4.90
WS_DOOR_X=5.5          # native tile x=6.5, face on the y=6 edge
WS_BAYS=3


def _bay_centres(a,b):
    return [a+(b-a)*(i+.5)/WS_BAYS for i in range(WS_BAYS)]


def workshop(g):
    front,side=_bay_centres(WS_X0,WS_X1),_bay_centres(WS_Y0,WS_Y1)
    front_wall,right_wall,rear_wall=WS_Y0-.06,WS_X1+.06,WS_Y1+.06
    framed_room(g,WS_X0,WS_Y0,WS_X1,WS_Y1,2,4.82,WS_BAYS,
                front_door=(WS_DOOR_X,1.0,1.0),infill=CIVIC_FORGED_PANEL)
    g.include_component(hydro_workshop_door())
    g.doorways.append({'name':'HydroWorkshopDoor','position':[WS_DOOR_X,WS_Y0-.10,2]})
    window_y(g,front[0],front_wall,3.82,1)
    window_y(g,WS_DOOR_X,front_wall,4.15,0.75)
    for y in (side[0],side[2]):
        side_window(g,right_wall,y,3.84,1)
    for x in (front[0],front[2]):
        window_y(g,x,rear_wall,3.85,1,'back')
    roof_bearing(g,WS_X0,WS_Y0,WS_X1,WS_Y1,4.82,4.84)
    # The eave outline lies on the workshop's tile edges (x=4..7, y=6..9):
    # 4 cm past the left/front/rear cladding, flush on the right.
    # 1 cm past the edges so its end beams never share the frame's beam faces.
    gabled_roof(g,WS_X0-.11,WS_Y0-.11,WS_X1+.06,WS_Y1+.11,4.84,5.80,228)
    # Dormer window, plates and fasteners stand 1-4 cm proud of the gable
    # cladding (y 1.945), never on its plane.
    dormer(g,(WS_X0+WS_X1)/2,WS_Y0-.025,5.40,1.13)  # eave beam clear of the ridge bracket
    # Weather hood / ventilation stack, not a combustion chimney.
    g.box((5.61,4.45,5.48),(.24,.26,.75),IRON)
    g.box((5.61,4.45,5.89),(.35,.37,.10),IRON)
    for z in (5.63,5.72):
        g.box((5.61,4.305,z),(.27,.025,.035),IRON)
    # Door lamps: arms meet the cladding, lamps stay over the door path cell.
    cage_lamp(g,WS_DOOR_X-.64,front_wall-.05,3.07)
    cage_lamp(g,WS_DOOR_X+.38,front_wall-.05,3.07)
    # Flush control cabinet under the first rear window, clear of the lane.
    g.box((front[0],rear_wall-.015,2.71),(.57,.09,1.10),CIVIC_FORGED_PANEL)
    for x in (front[0]-.23,front[0]+.23):
        for z in (2.24,3.18):steel_bolt(g,(x,rear_wall+.045,z),'Y',.023)
    # Cooling grille centred in the middle bay of the right wall.
    g.box((right_wall+.005,side[1],2.86),(.10,.90,.80),IRON)
    for i in range(8):
        g.box((right_wall+.055,side[1],2.55+i*.085),(.035,.77,.035),IRON)
    # Instrument loop and gauges framing the front window.
    cx=front[0]
    round_pipe(g,[(cx-.30,front_wall-.15,3.36),(cx-.30,front_wall-.15,4.40),
                  (cx+.86,front_wall-.15,4.40),(cx+.86,front_wall-.15,3.32)],.047)
    for x in (cx-.16,cx+.16):
        gauge(g,x,front_wall-.21,4.17,.115,rim_material=IRON)
    g.box((front[1],front_wall-.145,2.55),(.36,.29,.50),IRON)
    gauge(g,front[1],front_wall-.31,2.60,.12,rim_material=IRON)


def append_powerhouse(architecture,powerhouse,*,sideways,downstream):
    """Place the authored subassembly and retain its named component ownership."""
    existing={part['name'] for part in architecture.components}
    if existing.intersection(part['name'] for part in powerhouse.components):
        raise ValueError('Duplicate powerhouse component ownership')
    base=len(architecture.vertices)
    first_face=len(architecture.faces)
    architecture.vertices.extend((x-sideways,y-downstream,z) for x,y,z in powerhouse.vertices)
    architecture.faces.extend(tuple(base+i for i in f) for f in powerhouse.faces)
    architecture.materials.extend(powerhouse.materials)
    architecture.face_uvs.extend(powerhouse.face_uvs)
    architecture.face_sources.extend(powerhouse.face_sources)
    for part in powerhouse.components:
        architecture.components.append({'name':part['name'],
            'faceRange':[first_face+i for i in part['faceRange']]})
    for door in powerhouse.doorways:
        x,y,z=door['position']
        architecture.doorways.append({**door,'position':[x+sideways,y+downstream,z]})


def hydro(g,parts):
    rails=RailAssembly('HydroRails',cap_material=IRON)
    cast_conduit(g);dam_cap(g)
    runner(parts)
    # The powerhouse is an explicit downstream subassembly. Its front is
    # behind the dam's y=2..4 seal, leaving the wall continuation buildable.
    # This is an authored rigid placement, never fitting or rescaling the mesh.
    architecture=g
    g=Geometry('Hydro.Powerhouse')
    powerhouse_parts=[]
    # Solid workshop foundation, with a layer-two walkable service terrace.
    for x in range(3,7):
        for y in range(6):
            g.box((x+.5,y+.5,1),(.989,.989,2),CIVIC_CONCRETE)
    for y,out in ((.0015,-1),(5.9985,1)):
        for z in (.5,1.0,1.5):
            g.box((5,y,z),(3.97,.012,.012),IRON)
        for x in (3.25,4.5,5.5,6.75):
            for z in (.28,1.72):g.cylinder((x,y+out*.0055,z),.035,.015,IRON,'Y',12)
    # Deck edge angles only along open deck edges; the workshop wall stands
    # on the x=4 edge between y=6 and y=9.
    for y0,y1 in ((.03,WS_Y0-.10),(WS_Y1+.10,5.97)):
        g.box((3.03,(y0+y1)/2,2.015),(.06,y1-y0,.05),IRON)
    g.box((6.97,3,2.015),(.06,5.94,.05),IRON)
    for y in (.03,5.97):
        g.box((5,y,2.015),(3.88,.06,.05),IRON)
    generator(g,powerhouse_parts);workshop(g)
    # Keep a full clear strip outside the door and around the back/right wall.
    # These are separate rail nodes so integration can reuse adaptive openings.
    ix,iy=.071,.081
    for x in range(3,7):
        a=x+ix if x==3 else x;b=x+1-ix if x==6 else x+1
        rails.run(f'Front{x}',(a,iy),(b,iy),2)
        rails.run(f'Rear{x}',(a,6-iy),(b,6-iy),2)
    for y in range(6):
        a=y+iy if y==0 else y;b=y+1-iy if y==5 else y+1
        rails.run(f'Right{y}',(7-ix,a),(7-ix,b),2)
    # Conduit-side rails only beside the two open lane cells; the generator
    # and the workshop wall close the rest of that edge.
    rails.run('ConduitSide0',(3+ix,iy),(3+ix,.85),2)  # ends at the generator pedestal
    rails.run('ConduitSide5',(3+ix,5),(3+ix,6-iy),2)
    # Flush service hatch does not obstruct the terrace or imply a second door:
    # 4.5 mm proud, so the walking surface stays on the whole layer.
    g.box((5.68,.58,2.00225),(.64,.64,.0045),IRON)
    for x in (5.44,5.92):
        for y in (.34,.82):steel_bolt(g,(x,y,2.0115),'Z',.021)
    downstream=4.0
    sideways=1.0
    append_powerhouse(architecture,g,sideways=sideways,downstream=downstream)
    for part,axis,speed in powerhouse_parts:
        part.origin.x+=sideways
        part.origin.y+=downstream
        parts.append((part,axis,speed))
    for rail in rails.meshes:
        rail.vertices=[(x-sideways,y-downstream,z) for x,y,z in rail.vertices]
    for run in rails.runs:
        for panel in run['panels']:
            panel['start'][0]+=sideways
            panel['end'][0]+=sideways
            panel['start'][1]+=downstream
            panel['end'][1]+=downstream
    return rails
