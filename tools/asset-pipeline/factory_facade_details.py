"""Closed rooms and exterior services for the accepted crusher/kiln silhouettes.

Authored positions are in artwork units. Native entrance slots and grid access
are a separate export step. These details add no heat or maintenance mechanic.
"""
from frontier_architecture import WOOD,PLANK,IRON,BRASS,ROOF,wall
from industrial_geometry import steel_bolt
from industrial_facades import window_y,side_window,gauge,CYAN
from reference_details import round_pipe
from industrial_kit import steel_bolt,round_pipe,band,prism,bolt,square_nut,open_box,gauge
from reference_materials import KILN_SOOT
from industrial_levels import (CRUSHER_DECK,KILN_DECK,KILN_MACHINE_DATUM,MountedMachinery,
                               FACTORY_PORCH_ROOF)


def strapped_vessel(g,x,y,z,r,height):
    prism(g,(x,y,z),r,height,IRON,'Z',12)
    for zz in (z-height*.39,z+height*.39):
        band(g,(x,y,zz),r+.024,.03,.06,BRASS,'Z',12)
        g.box((x,y+r+.05,zz),(r*2.3,.10,.08),WOOD)
    prism(g,(x,y,z+height/2+.035),r*.44,.07,BRASS,'Z',8,(False,False))  # ends inside vessel and cap
    prism(g,(x,y,z+height/2+.085),r*.61,.035,IRON,'Z',8)


def instrument_strip(g,x,y,z,width):
    g.box((x,y,z),(width,.07,.14),IRON)
    g.box((x,y-.041,z),(width*.78,.015,.035),CYAN)
    for dx in (-width*.44,width*.44):square_nut(g,(x+dx,y-.049,z),'Y',.014,-1)


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
        g.box((east-.0375,y,(.26+CRUSHER_DECK-.22)/2),(.075,(y1-y0)/count,CRUSHER_DECK-.48),PLANK)
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


def kiln_facades(g):
    machinery=MountedMachinery(g,KILN_MACHINE_DATUM,KILN_DECK)
    # Under-deck operator room continues back from the existing front porch.
    # Solid panes hide the room; the roofed rotary machinery stays visible.
    # One tile wide (grid x 4..5): plank outer faces on the tile edges.
    for x in (3.0375,3.9625):
        for j in range(19):
            y=.32+j*.159
            g.box((x,y,(.20+KILN_DECK-.19)/2),(.075,.159,KILN_DECK-.39),PLANK)
        left=x<3.5
        for y in (.75,2.75):side_window(g,x+(-.0375 if left else .0375),y,KILN_DECK-.58,0.75,'left' if left else 'right')
        for y in (.25,1.75,3.28):
            g.box((x,y,(.155+KILN_DECK-.145)/2),(.11,.12,KILN_DECK-.30),WOOD)
            for z in (.29,KILN_DECK-.29):square_nut(g,(x+(-.068 if left else .068),y,z),'X',.016,-1 if left else 1)
    g.box((3.5,1.75,KILN_DECK-.16),(.925,3.10,.07),WOOD)
    window_y(g,3.5,3.335,KILN_DECK-.57,0.8,'back')
    # The porch is the room's width; one header closes the front above it.
    wall(g,3.075,.28,3.925,KILN_DECK-.18,FACTORY_PORCH_ROOF+.08)
    # Air/control lines stay on the rear machine frame, inside the gallery's
    # walking line; their ends visibly connect to the damper and feed gate.
    round_pipe(machinery,[(.42,1.52,2.47),(.42,3.42,2.47),(.42,3.42,2.88),
                  (5.87,3.42,2.88),(5.87,2.70,2.88),(5.87,2.70,3.28)],.045)
    for x in (1.60,2.75,4.02,5.30):
        band(machinery,(x,3.42,2.88),.076,.025,.055,BRASS,'X',8)
        machinery.box((x,3.34,2.88),(.07,.18,.15),IRON)
    for y in (1.48,3.30):strapped_vessel(g,4.12,y,.65,.11,.60)
    round_pipe(g,[(4.12,1.48,.99),(4.12,1.48,1.10),(4.12,3.30,1.10),(4.12,3.30,.99)],.027)
    round_pipe(g,[(4.12,3.30,.99),(4.12,3.42,.99),(4.12,3.42,KILN_DECK+2.88-KILN_MACHINE_DATUM)],.023)
    # The original mechanical gauges get a small status strip, not neon trim.
    instrument_strip(machinery,4.89,1.33,1.86,.24)
    # A short sealed outlet neck connects the process chamber to its front tray.
    machinery.box((6.16,.95,.84),(.58,.16,.16),KILN_SOOT)
    for x in (5.84,6.48):machinery.box((x,.85,.84),(.06,.25,.21),IRON)
