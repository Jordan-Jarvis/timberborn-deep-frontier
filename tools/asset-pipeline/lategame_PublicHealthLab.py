"""PublicHealthLab: civic water and sanitation laboratory (3 workers, 100 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the water-testing forecourt (basin, fountain, sampling hoist, dosing
tanks), planting and post lamp.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "public health lab needs to shrink a decent amount", "one layer
per floor", "make the roof flat on more of our buildings"): 8x6x12 -> 6x4x5,
inside the old footprint with the same origin, door and native entrance.
Removed: the two-layer podium, the second plaster storey, the mansard with its
dormers, the octagonal observation lantern and its rails, the eight-layer
ventilation tower with its floor bands, ladder, top rails and duct bridge,
the header tank on its stand and the fume-cupboard flue. The lab is now two
one-layer storeys under a flat roof deck; the ventilation tower is a short
rooftop shaft.

HERO: a square concrete ventilation shaft, steel-banded and louvred, rising
from the roof deck and crowned by a ring of turning ventilator cowls.
ROOF: flat concrete roof with a low parapet, exactly on layer 2 (a roof deck).

Plan (6 x 4 tiles; front y = 0; one layer per storey):
  - ground storey (layer 0): cast-concrete walls with factory windows and the
    native door centred on x = 4.5, face on the y = 0 tile edge;
  - upper storey (layer 1): pale plaster laboratory in a grey timber frame
    with a lancet window in every bay;
  - roof slab top exactly layer 2 with a parapet ring on the edges; the vent
    shaft stands on the single roof cell (1, 2), every other roof cell is
    clear (no flue or emitter: a steam emitter would bar the cells round it
    from the roof deck).

Animated (unchanged names and kinds): four tower cowls and the main cowl
(SPIN_Z), anemometer on a spindle above the main cowl (SPIN_Z).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN
import lategame_civic_parts as P
from lategame_civic_parts import blk, animate  # noqa: F401
import native_building_assets as N
from lategame_roofdeck_parts import parapet_ring

IDENT = 'PublicHealthLab'
FOOTPRINT = (6, 4)
HEIGHT = 5
HERO = ('Square concrete ventilation shaft, steel-banded and louvred, rising from the flat roof deck and crowned '
        'by a ring of turning ventilator cowls.')
FRAME_END = 121

W, D = FOOTPRINT
STOREY = 1.0                    # one layer per storey
ROOF_TOP = 2.0                  # roof deck, exactly layer 2
SLAB = .16
DOOR_X = 4.5
# Vent shaft centred on roof cell (1, 2): its cap overhang stays inside the
# 0.15 occupancy inset, so it claims only that cell above the roof.
TOWER = (.97, 1.97, 2.03, 3.03)
TTOP = 3.55


def ground_storey(g):
    P.podium(g, 0, 0, W, D, STOREY, skip=[(DOOR_X - .5, DOOR_X + .5)])
    P.door(g, DOOR_X, 0, 0, 'Door0')
    K.lamp(g, DOOR_X - .64, 0, .5, face='front')
    K.lamp(g, DOOR_X + .64, 0, .5, face='front')
    for x in (.5, 1.5, 2.5, 3.5, 5.5):
        P.native_window(g, x, 0, .47, .55, 'front', 'factory')
    for x in (.5, 1.5, 2.5, 3.5, 4.5, 5.5):
        P.native_window(g, x, D, .47, .55, 'back', 'factory')
    for y in (.5, 1.5, 2.5, 3.5):
        P.native_window(g, 0, y, .47, .55, 'left', 'factory')
        P.native_window(g, W, y, .47, .55, 'right', 'factory')


def upper_storey(g):
    x0, y0, x1, y1 = .1, .1, W - .1, D - .1
    z0, z1 = STOREY, ROOF_TOP - SLAB
    xs = [x0 + (x1 - x0) * (i + .5) / W for i in range(W)]
    ys = [y0 + (y1 - y0) * (i + .5) / D for i in range(D)]
    P.framed_block(g, x0, y0, x1, y1, z0, z1, infill=CONCRETE, frame=GREYWOOD, pitch=1.0 - .2 / W,
                   corner=.16, post=.1,
                   windows={'front': [(x, 1.41, .72, 'lancet') for x in xs],
                            'back': [(x, 1.41, .72, 'lancet') for x in xs],
                            'left': [(y, 1.41, .72, 'lancet') for y in ys],
                            'right': [(y, 1.41, .72, 'lancet') for y in ys]})
    K.flat_roof(g, x0, y0, x1, y1, z1, thickness=SLAB, overhang=.1)
    parapet_ring(g, -.03, -.03, W + .03, D + .03, ROOF_TOP)


def vent_tower(g, parts):
    x0, y0, x1, y1 = TOWER
    P.framed_block(g, x0, y0, x1, y1, ROOF_TOP, TTOP, infill=CONCRETE, frame=IRON, pitch=5.0, corner=.18,
                   floors=(2.55,), sink=.04)
    # Louvre panels below the cap on all four faces.
    for k in range(4):
        z = 2.85 + k * .16
        blk(g, x0 + .17, y0 - .07, z, x1 - .17, y0, z + .09, FORGED)
        blk(g, x0 + .17, y1, z, x1 - .17, y1 + .07, z + .09, FORGED)
        blk(g, x0 - .07, y0 + .17, z, x0, y1 - .17, z + .09, FORGED)
        blk(g, x1, y0 + .17, z, x1 + .07, y1 - .17, z + .09, FORGED)
    P.native_window(g, (x0 + x1) / 2, y0, 2.3, .45, 'front', 'lancet')
    # Cap and cowls (the cap overhang stays within the shaft's own cell).
    blk(g, x0 - .08, y0 - .08, TTOP - .02, x1 + .08, y1 + .08, TTOP + .1, CONCRETE)
    blk(g, x0 - .1, y0 - .1, TTOP + .1, x1 + .1, y1 + .1, TTOP + .15, IRON)
    top = TTOP + .15
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    corners = [(x0 + .25, y0 + .25), (x1 - .25, y0 + .25), (x1 - .25, y1 - .25), (x0 + .25, y1 - .25)]
    for i, (x, y) in enumerate(corners):
        g.cylinder((x, y, top + .08), .12, .16, IRON, 'Z', 12)
        c = P.cowl(f'TowerCowl{i}', x, y, top + .16, r=.15, h=.36, facing=i * math.pi / 2)
        parts.append((c, 'SPIN_Z', .5 if i % 2 else -.5))
    g.cylinder((cx, cy, top + .2), .17, .4, FORGED, 'Z', 14)
    g.ring((cx, cy, top + .32), .2, .045, .05, BRASS, 'Z', 14)
    big = P.cowl('TowerCowlMain', cx, cy, top + .4, r=.24, h=.5, facing=0)
    parts.append((big, 'SPIN_Z', .25))
    # Anemometer on a spindle above the main cowl's cap (same vertical axis).
    az = top + .4 + .5 * .55 + .24 * .85 + .025 + .06
    an = Geometry('Anemometer', (cx, cy, az))
    an.cylinder((cx, cy, az - .04), .025, .08, IRON, 'Z', 8)
    an.cylinder((cx, cy, az + .02), .045, .06, BRASS, 'Z', 8)
    for i in range(3):
        a = i * 2 * math.pi / 3
        tip = (cx + math.cos(a) * .24, cy + math.sin(a) * .24, az + .03)
        an.beam((cx, cy, az + .03), tip, .022, mat=IRON)
        K.revolve(an, (tip[0], tip[1], tip[2] - .05), [(.001, 0), (.065, .035), (.065, .085), (.001, .1)], BRASS,
                  segments=8)
    parts.append((an, 'SPIN_Z', 2))


def build(g, parts):
    ground_storey(g)
    upper_storey(g)
    vent_tower(g, parts)
