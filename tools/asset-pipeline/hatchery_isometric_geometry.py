"""Open nursery companion to Fishery.png's isometric waterfront architecture.

This is a new art study, not an exact reproduction of a separate hatchery sheet.
The pen openings use the game's actual world water after integration. No plan
view, printed footprint, existing prototype size or baked stairs is a reference.
"""
import math
from frontier_architecture import Geometry,WOOD,PLANK,IRON,ROOF,BRASS,deck
from industrial_budget import bin
from reference_materials import CLOTH,CIVIC_CONCRETE,CIVIC_FORGED_PANEL
from civic_isometric_geometry import framed_room,gabled_roof,roof_bearing,component_doorway,glazing,beam_joint,timber_column,wall_lamp,deck_lamp,hanging_board,fishing_net
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


def hatchery(g,parts):
    from hatchery_components import include,rails as platform_rails
    from hatchery_structure import DOORS,source
    rails=platform_rails()
    for name in ('Deck.MainFrontApron','Deck.MainApron','Headhouse.Shell',
                 'Door.Door0','Headhouse.DoorLamps','Headhouse.RoofBearing',
                 'Headhouse.Roof','Headhouse.Windows','Headhouse.RoofVent'):
        include(g,name)
    g.doorways.append({'id':'Door0','position':list(source(DOORS['Door0']['position'])),
                      'outward':[0,-1],'width':1.,'internalConnection':'BuildingInterior'})
    hanging_board(g,parts,'FisheryWorks',.37,.20,1.10,.64)
    parts[-1][0].name='FishHatchery.NurserySign'
    # Central aisle between the pens at one whole game layer. 2026-10-26
    # (user): the perimeter dock loop around the pens is gone (compact early
    # building). The two pen openings are not covered by a modelled floor.
    # Dock piles are runtime AdaptiveSupports clones, not fixed scene posts.
    include(g,'Deck.CentreDock')
    nursery_pen(g,.22,3.58,1.70,6.02)
    nursery_pen(g,2.80,3.58,4.25,6.02)
    # Workshop canopy is lower and narrower than the headhouse roof. Its
    # sealed filter machinery and small tank are native-material equipment.
    include(g,'Deck.CanopyFrontApron');include(g,'Deck.CanopyBaseApron')
    for x in (4.55,6.15):
        for y in (.76,2.62):timber_column(g,x,y,0,1.72,.15)
    gabled_roof(g,4.35,.54,6.34,2.81,1.85,2.43,941)
    g.box((5.35,1.50,.41),(1.05,.72,.82),CIVIC_CONCRETE)
    g.box((5.35,1.50,.86),(1.13,.80,.08),IRON)
    g.cylinder((5.35,1.50,1.08),.26,.76,CIVIC_FORGED_PANEL,'X',24)
    for x in (4.99,5.71):g.ring((x,1.50,1.08),.28,.025,.045,IRON,'X',24)
    g.cylinder((4.93,1.50,1.08),.16,.05,BRASS,'X',16)
    for i in range(8):
        a=i*math.pi/4
        g.cylinder((4.89,1.50+math.sin(a)*.20,1.08+math.cos(a)*.20),.026,.04,IRON,'X',8)
    round_pipe(g,[(5.35,1.92,1.06),(5.35,2.35,1.06),(4.30,2.35,1.06),(4.30,2.35,.30)],.055)
    round_pipe(g,[(5.92,1.50,.40),(6.02,1.50,.40),(6.02,2.83,.40)],.055)
    gauge(g,5.40,.99,.60,.11)
    # The header tank is the WorkshopReservoir water stock, so it stays.
    water_barrel(g,'HatcheryHeaderTank',(5.33,.10,0),.49)
    for x in (4.65,5.30,5.95):wall_lamp(g,x,2.66,1.45,'back')
    # 2026-10-22 (user): no forced decoration beyond the walls. The two
    # barrels and the sacks on the bank row, the net drying frames on the
    # docks and the dock lamps are gone. The bank row itself stays: it is the
    # native land anchor (waterside_sites.json landCells) and the doorstep.
    from hatchery_selection import parts as picking_parts
    g.structural_parts.extend(picking_parts())
    # Native world-water-only preview rectangles are authored by the study
    # renderer; they are excluded from the eventual Timbermesh payload.
    return rails
