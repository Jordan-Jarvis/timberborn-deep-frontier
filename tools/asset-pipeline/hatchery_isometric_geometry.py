"""Open nursery companion to Fishery.png's isometric waterfront architecture.

This is a new art study, not an exact reproduction of a separate hatchery sheet.
The pen openings use the game's actual world water after integration. No plan
view, printed footprint, existing prototype size or baked stairs is a reference.
"""
import math
from frontier_architecture import Geometry,WOOD,PLANK,IRON,ROOF,BRASS,deck
from industrial_budget import bin
from reference_materials import CLOTH,CIVIC_CONCRETE,CIVIC_FORGED_PANEL
from civic_isometric_geometry import framed_room,gabled_roof,roof_bearing,component_doorway,glazing,beam_joint,timber_column,wall_lamp,deck_lamp,hanging_board,hanging_board_storey,fishing_net
from industrial_budget import bracket
from civic_isometric_geometry import steel_bolt
from industrial_facades import gauge
from industrial_budget import round_pipe
from native_building_assets import barrel,water_barrel
from walkway_geometry import RailAssembly


def nursery_pen(g,x0,y0,x1,y1):
    """Submerged mesh basket, open to world water, with lifting and feed rails."""
    # Individual fine bars remain visible beneath the real river surface.
    for x in (x0,x1):
        for y in (y0,y1):
            g.box((x,y,-.38),(.12,.12,.86),IRON)
            bracket(g,x,y,.03,.17)
        for z in (-.78,-.42,-.08):g.beam((x,y0,z),(x,y1,z),.045,mat=IRON)
        for i in range(math.ceil((y1-y0)/.17)+1):
            yy=y0+i*(y1-y0)/math.ceil((y1-y0)/.17)
            g.beam((x,yy,-.78),(x,yy,.02),.014,mat=IRON)
    for y in (y0,y1):
        for z in (-.78,-.42,-.08):g.beam((x0,y,z),(x1,y,z),.045,mat=IRON)
        for i in range(10):
            x=x0+(x1-x0)*i/9
            g.beam((x,y,-.78),(x,y,.02),.014,mat=IRON)
    for x in (x0-.05,x1+.05):beam_joint(g,(x,y0-.02,.06),(x,y1+.02,.06),.12,.10)
    for y in (y0-.08,y1+.08):beam_joint(g,(x0-.08,y,.06),(x1+.08,y,.06),.12,.10)
    for y in (y0+.15,y1-.15):
        for x in (x0+.13,x1-.13):g.ring((x,y,.12),.055,.014,.026,IRON,'X',12)
    # Feed hopper and a small perforated distribution chute along one side.
    cy=(y0+y1)/2
    bin(g,(x0+.20,cy,.18),(.29,.40,.31),None)
    g.box((x0+.20,cy,.51),(.36,.47,.05),ROOF)
    round_pipe(g,[(x0+.20,cy,.18),(x0+.20,y0+.22,.18)],.035)
    for i in range(6):g.cylinder((x0+.20,y0+.25+i*.15,.15),.028,.07,BRASS,'Z',8)


def canopy_flat_roof(g,x0,y0,x1,y1,z):
    """Flat pump-canopy roof (2026-10-30): edge beams on the four posts, a
    timber slab and timber decking set in from its edges (no concrete: the
    hatchery unlocks before concrete exists, user 2026-10-30)."""
    for y in (y0+.22,y1-.19):beam_joint(g,(x0+.10,y,z+.07),(x1-.10,y,z+.07),.16,.14)
    g.box(((x0+x1)/2,(y0+y1)/2,z+.20),(x1-x0,y1-y0,.12),WOOD)
    g.box(((x0+x1)/2,(y0+y1)/2,z+.27),(x1-x0-.30,y1-y0-.30,.02),PLANK)


def hatchery(g,parts):
    from hatchery_components import include,rails as platform_rails
    from hatchery_structure import DOORS,source
    rails=platform_rails()
    for name in ('Deck.MainFrontApron','Deck.MainApron','Headhouse.Shell',
                 'Door.Door0','Headhouse.DoorLamps','Headhouse.Roof','Headhouse.Windows'):
        include(g,name)
    g.doorways.append({'id':'Door0','position':list(source(DOORS['Door0']['position'])),
                      'outward':[0,-1],'width':1.,'internalConnection':'BuildingInterior'})
    # One-layer headhouse (2026-10-30): the shorter sign hangs under the
    # flat roof's front edge.
    hanging_board_storey(g,parts,'FisheryWorks',.37,.20,.42,.64,'FishHatchery.NurserySign')
    # Central aisle between the pens at one whole game layer. 2026-10-26
    # (user): the perimeter dock loop around the pens is gone (compact early
    # building). The two pen openings are not covered by a modelled floor.
    # Dock piles are runtime AdaptiveSupports clones, not fixed scene posts.
    include(g,'Deck.CentreDock')
    # 2x2 pens since the 2026-11-01 shrink (were 2x3), right behind the headhouse.
    nursery_pen(g,.22,2.58,1.70,4.02)
    nursery_pen(g,2.80,2.58,4.25,4.02)
    # Workshop canopy is lower and narrower than the headhouse roof. Its
    # sealed filter machinery and small tank are native-material equipment.
    # 2026-10-30: one layer tall under a flat roof; the filter drum sits low
    # on its cast base.
    include(g,'Deck.CanopyFrontApron');include(g,'Deck.CanopyBaseApron')
    # 2x2 canopy beside the headhouse since the 2026-11-01 shrink (native x
    # 3..5, y 1..3; was 3x2 with its rear posts out over the pen row): posts
    # and roof inside its own cells, machinery 1.5 west of where it stood.
    for x in (3.05,4.55):
        for y in (.76,2.06):timber_column(g,x,y,0,.80,.15,collars=False,foot=WOOD)
    canopy_flat_roof(g,2.85,.54,4.75,2.20,.80)
    g.box((3.85,1.42,.13),(1.05,.72,.26),WOOD)   # timber sleeper bed under the pump
    g.box((3.85,1.42,.29),(1.13,.80,.06),IRON)
    g.cylinder((3.85,1.42,.56),.24,.76,CIVIC_FORGED_PANEL,'X',24)
    for x in (3.49,4.21):g.ring((x,1.42,.56),.26,.025,.045,IRON,'X',24)
    g.cylinder((3.43,1.42,.56),.15,.05,BRASS,'X',16)
    for i in range(8):
        a=i*math.pi/4
        g.cylinder((3.39,1.42+math.sin(a)*.19,.56+math.cos(a)*.19),.026,.04,IRON,'X',8)
    round_pipe(g,[(3.85,1.74,.56),(3.85,1.88,.56),(2.95,1.88,.56),(2.95,1.88,.30)],.055)
    # Feed main to the Timber Pipes port on the canopy's east face (4,2,1).
    round_pipe(g,[(4.42,1.42,.40),(4.70,1.42,.40),(4.70,1.92,.40)],.055)
    gauge(g,3.90,1.02,.14,.09)
    # The header tank is the WorkshopReservoir water stock, so it stays.
    water_barrel(g,'HatcheryHeaderTank',(4.30,.10,0),.49)
    for x in (3.45,4.25):wall_lamp(g,x,2.10,.50,'back')
    # 2026-10-22 (user): no forced decoration beyond the walls. The two
    # barrels and the sacks on the bank row, the net drying frames on the
    # docks and the dock lamps are gone. The bank row itself stays: it is the
    # native land anchor (waterside_sites.json landCells) and the doorstep.
    from hatchery_selection import parts as picking_parts
    g.structural_parts.extend(picking_parts())
    # Native world-water-only preview rectangles are authored by the study
    # renderer; they are excluded from the eventual Timbermesh payload.
    return rails
