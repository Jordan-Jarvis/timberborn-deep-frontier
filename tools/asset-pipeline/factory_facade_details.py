"""Closed rooms and exterior services for the accepted crusher/kiln silhouettes.

Authored positions are in artwork units. Native entrance slots and grid access
are a separate export step. These details add no heat or maintenance mechanic.
"""
from frontier_architecture import WOOD,PLANK,IRON,BRASS,ROOF,wall
from industrial_geometry import steel_bolt
from industrial_facades import window_y,side_window,gauge,CYAN
from reference_details import round_pipe
from industrial_kit import (steel_bolt,round_pipe,band,prism,bolt,square_nut,open_box,lean_gauge as gauge,lean_wall as wall,skin_board)
from reference_materials import KILN_SOOT
from industrial_levels import (CRUSHER_DECK,KILN_DECK,KILN_MACHINE_DATUM,MountedMachinery,
                               FACTORY_PORCH_ROOF)


def strapped_vessel(g,x,y,z,r,height):
    prism(g,(x,y,z),r,height,IRON,'Z',8)
    for zz in (z-height*.39,z+height*.39):
        g.box((x,y+r+.05,zz),(r*2.3,.10,.08),WOOD)
    prism(g,(x,y,z+height/2+.035),r*.44,.07,BRASS,'Z',8,(False,False))  # ends inside vessel and cap
    prism(g,(x,y,z+height/2+.085),r*.61,.035,IRON,'Z',8)


def instrument_strip(g,x,y,z,width):
    g.box((x,y,z),(width,.07,.14),IRON)
    g.box((x,y-.041,z),(width*.78,.015,.035),CYAN)


def crusher_facades(g):
    """Closed lower workshop in native grid XY (crusher layout origin 0,0).

    Frame faces: west x=1, east x=5, rear y=6 (see crusher_sheet_geometry).
    Plank skins are 0.04-0.05 behind the frame. The dark output aperture is
    occupied by the chute; beavers use the arched porch beside it.
    """
    east,rear=4.96,5.96
    count=16;y0,y1=3.07,5.78
    for j in range(count):
        y=y0+(j+.5)*(y1-y0)/count
        skin_board(g,(east-.0375,y,(.26+CRUSHER_DECK-.22)/2),(.075,(y1-y0)/count,CRUSHER_DECK-.48),'Y',j,count,PLANK,'-x')
    g.box((3.96,2.98,(.25+CRUSHER_DECK-.21)/2),(1.48,.04,CRUSHER_DECK-.46),KILN_SOOT)
    g.box((3.96,2.98,.29),(1.48,.07,.12),IRON)
    for x in (3.18,4.74):g.box((x,2.95,(.27+CRUSHER_DECK-.19)/2),(.08,.12,CRUSHER_DECK-.46),WOOD)
    for y in (3.94,4.91):side_window(g,east,y,CRUSHER_DECK-.66,0.8)
    for x in (2.08,3.96):window_y(g,x,rear,CRUSHER_DECK-.65,0.8,'back')
    window_y(g,1.57,2.825,CRUSHER_DECK-.53,0.6)
    # The room is sealed at the top rather than open through the roll deck.
    g.box((3.005,4.39,CRUSHER_DECK-.155),(3.75,2.98,.055),WOOD)
    # Narrow rear cable trunk feeds the existing upstairs controller.
    round_pipe(g,[(4.98,5.29,1.20),(4.98,5.29,CRUSHER_DECK+1.18),(4.98,4.14,CRUSHER_DECK+1.18),(4.98,4.14,CRUSHER_DECK+.79)],.016)
    for z in (CRUSHER_DECK+.15,CRUSHER_DECK+.60,CRUSHER_DECK+1.05):g.box((4.96,5.29,z),(.075,.08,.035),BRASS)
    g.box((1.57,2.785,.54),(.30,.08,.30),IRON)
    gauge(g,1.57,2.729,.58,.078)
    instrument_strip(g,1.57,2.725,.78,.24)
