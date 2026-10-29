"""Crusher workshop fittings and localized wear, outside the walking circuit."""
import math
import random
from frontier_architecture import *
from industrial_geometry import steel_bolt,bracket
from reference_details import cage_lamp,cask,round_pipe
from industrial_kit import (open_beam,lean_wheel as wheel,lean_gauge as gauge)
from industrial_kit import (steel_bolt,lean_bracket as bracket,lean_cage_lamp as cage_lamp,lean_cask as cask,round_pipe,band,prism,bolt,square_nut,open_box,lean_rock as rock)
from reference_materials import CRUSHER_STEEL,KILN_RUST,KILN_WOOD_SPLIT,KILN_WOOD_WEAR,KILN_DUST,KILN_SOOT
from industrial_levels import CRUSHER_DECK as DECK_Z

# Roller canopy in the reviewed machinery frame. Its right posts and eave end
# inside grid x=5 (legacy x 3.70), clear of the right walking lane.
ROLL_ROOF_POST=3.50
ROLL_ROOF=(1.65,2.87,3.56,3.84,3.13,3.36)
# Hopper roof. It stands .02 above the roller roof's rear edge so its corner
# brackets and straps clear that roof's edge beam and corner shoe.
HOPPER_ROOF=(.07,3.40,1.68,3.86,3.30,3.43)


def workshop_details(g,ground,static):
    # Replaceable cheek plates and jacking screws beside both crushing rolls.
    for x in (1.96,2.79):
        for y in (1.17,3.30):
            g.box((x,y-.18,1.80),(.28,.025,.22),CRUSHER_STEEL)
            prism(g,(x,y+.17,1.84),.024,.32,IRON,'Z',6)
            prism(g,(x,y+.17,2.04),.052,.045,BRASS,'Z',6)
            # Small brass oil cups with transparent amber inset.
            prism(g,(x,y,2.21),.049,.063,BRASS,'Z',6)
            prism(g,(x,y,2.255),.030,.055,BRASS,'Z',6,(False,False))  # ends inside the cups
            prism(g,(x,y,2.29),.046,.016,IRON,'Z',6)
    # Feed gate: handwheel, screw, guide channels and cross brace. (12k cap:
    # no plate nuts, screw threads or chute rivets.)
    for y in (2.16,3.27):
        g.box((1.52,y,2.53),(.055,.08,.40),IRON)
    g.box((1.53,2.72,2.51),(.045,1.06,.18),CRUSHER_STEEL)
    prism(g,(1.43,1.84,2.66),.027,.48,IRON,'Y',6)
    band(g,(1.43,1.60,2.66),.127,.024,.035,IRON,'Y',8,inner=True)
    for i in range(4):
        a=i*math.pi/2;g.beam((1.43,1.60,2.66),(1.43+math.cos(a)*.118,1.60,2.66+math.sin(a)*.118),.025,mat=BRASS)
    # Wear strips under material flow.
    for dx in (-.28,.28):ground.beam((2.38+dx,1.85,DECK_Z+.20),(2.80+dx,.70,.87),.044,.012,CRUSHER_STEEL)
    # Recessed controls stay on the machine side of the wider right-hand walk.
    for dx,size,mat in ((-.15,(.11,.44,.31),WOOD),(-.08,(.025,.40,.26),IRON)):
        g.box((3.66+dx,2.35,2.12),size,mat)
    for yy in (2.24,2.44):
        prism(g,(3.61,yy,2.17),.056,.025,BRASS,'X',8)
        prism(g,(3.63,yy,2.17),.043,.012,KILN_WOOD_WEAR,'X',8)
        g.beam((3.64,yy,2.17),(3.64,yy+.025,2.195),.008,mat=IRON)
    g.beam((3.62,2.35,2.06),(3.65,2.35,1.94),.023,mat=IRON)
    prism(g,(3.65,2.35,1.93),.039,.055,WOOD,'Y',6)
    # Warm lights, lower store bays and a proper workshop bench below the deck.
    cage_lamp(g,ROLL_ROOF_POST,2.83,2.70);cage_lamp(g,.14,3.60,2.58)
    g=ground
    g.box((2.83,3.48,.72),(1.20,.46,.09),PLANK)
    for x in (2.34,3.32):
        for y in (3.31,3.65):g.box((x,y,.40),(.09,.09,.59),WOOD)
    g.box((2.83,3.48,.24),(1.13,.36,.07),WOOD)
    for x in (2.42,2.64,2.86):
        g.box((x,3.49,.84),(.12,.19,.15),IRON)
    g.box((3.16,3.47,.81),(.13,.17,.12),IRON)
    prism(g,(3.16,3.30,.82),.024,.22,CRUSHER_STEEL,'Y',6)
    g.beam((3.09,3.20,.82),(3.23,3.20,.82),.025,mat=IRON)
    # Louvre vents sit flush in the west plank skin (face x=1.05), grid
    # coordinates. (The jack and stacked supply crates that stood outside the
    # wall line beside the porch were removed, 2026-10-22: the player places
    # their own props.)
    g=static
    for y in (3.86,4.92):
        g.box((1.045,y,.88),(.020,.42,.36),IRON)
        for z in (.75,.83,.91,.99):g.box((1.03,y,z),(.04,.36,.045),WOOD)


def worn_surfaces(g,ground):
    # (The 6 mm timber checks on the posts, the 9 mm roof seam chips, the
    # 6 mm dust flecks and the chain drips were sub-pixel at game zoom; the
    # native atlases paint grain and wear.)
    # The player supplies native stairs. Their removed authored flight must
    # not leave floating tread-wear strips in the open stair bay.
    # One lapped repair panel on the roller roof.
    g.beam((2.84,3.14,3.222),(2.84,3.52,3.312),.29,.018,IRON)
    # Grease stays on bearing saddles, not on the walkway.
    for x in (1.96,2.79):
        for y in (1.17,3.30):g.box((x,y,1.638),(.22,.21,.004),KILN_SOOT)
