"""Compact storey blocks for the 2026-10-30 late-game industry compaction.

Owned by the ChemicalWorks / PrecisionMachineWorks / ElectrolysisPlant /
CryogenicLiquefactionPlant / CryogenicTankFarm / WaterTreatmentPlant /
FertilizerWorks / FoodPackagingWorks studies.

Deliberately not named lategame_*_parts.py: render_lategame_studies.source_hash
globs that pattern, so a new file there would change every study's hash (the
civic_wellbeing_parts.py precedent). `--skip-unchanged` therefore does not see
edits to this file; rebuild the owning studies explicitly after changing it.

The user's direction (Steam Workshop feedback, 2026-10-30): smaller buildings,
far less open scaffolding, one layer per floor ("currently we have two layers
between floors, we should reduce it to one") and flat roofs on more buildings.
So a storey block here is a concrete ground storey exactly one layer high
(the native one-tile door fills it), timber- or steel-framed upper storeys of
one layer each with a floor band on every whole layer, and a flat concrete
roof whose top is exactly on the next whole layer, edged by a low curb that
stays under 0.15 above it (so the registration does not claim the cells
above it, and the roof-deck step can make it platformable).

Roof finishes vary by building (user, 2026-10-30: "we need variety, not
just a bunch of boring concrete"): flat roofs take roof_mat/curb_mat
(corrugated PAINTED metal, IRON or FORGED steel plate, PLANK timber, and
CONCRETE only sometimes); pitched and sawtooth roofs are authored by the
buildings themselves in the native roof planks. No roof vents.

Native material slots only (lategame_kit.NATIVE_SLOTS); same-facing parallel
surfaces are kept at least LAYER_GAP apart or buried in a solid.
"""
from frontier_architecture import WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED
import lategame_civic_parts as C
from lategame_civic_parts import blk

CURB = .12         # roof curb height above the roof top (registration needs < .15)
CURB_W = .12       # roof curb width
ROOF_T = .12       # roof slab thickness under its top
EAVE = .06         # slab overhang beyond the storey core


def flat_roof(g, x0, y0, x1, y1, top, *, overhang=EAVE, curb=True, mat=CONCRETE, curb_mat=CONCRETE):
    """Flat slab whose top face lies exactly at `top` (a whole layer), with a
    low curb ring flush with the slab edge. Returns `top`."""
    xa, ya, xb, yb = x0 - overhang, y0 - overhang, x1 + overhang, y1 + overhang
    blk(g, xa, ya, top - ROOF_T, xb, yb, top, mat)
    if curb:
        w = CURB_W
        blk(g, xa, ya, top, xb, ya + w, top + CURB, curb_mat)
        blk(g, xa, yb - w, top, xb, yb, top + CURB, curb_mat)
        blk(g, xa, ya + w, top, xa + w, yb - w, top + CURB, curb_mat)
        blk(g, xb - w, ya + w, top, xb, yb - w, top + CURB, curb_mat)
    return top


def storey_block(g, x0, y0, x1, y1, layers, *, infill=ORANGE, frame=WOOD, door=None, door_id='Door0',
                 ground_windows=None, windows=None, roof=True, curb=True, pitch=1.0, ground_skip=(),
                 faces=('front', 'back', 'left', 'right'), roof_mat=CONCRETE, curb_mat=CONCRETE):
    """Concrete ground storey (0..1) plus `layers - 1` framed storeys of one
    layer each, floor bands on every whole layer, and a flat roof whose top is
    the whole layer `layers`.

    `door` is the x centre of a native one-tile portal in the front (y0) face.
    `ground_windows` maps a face to (u, scale, style) native windows centred
    in the ground storey; `windows` maps a face to (u, z, scale, style) on the
    framed storeys (z absolute). Returns the roof top.
    """
    if layers < 1 or layers != int(layers):
        raise ValueError('A storey block has a whole number of one-layer storeys')
    skip = list(ground_skip)
    if door is not None:
        skip.append((door - .5, door + .5))
    C.podium(g, x0, y0, x1, y1, 1.0, skip=skip)
    if door is not None:
        C.door(g, door, y0, 0, door_id)
    for face, items in (ground_windows or {}).items():
        plane = {'front': y0, 'back': y1, 'left': x0, 'right': x1}[face]
        for u, scale, style in items:
            if face in ('front', 'back'):
                C.native_window(g, u, plane, .52, scale, face, style)
            else:
                C.native_window(g, plane, u, .52, scale, face, style)
    top = 1.0
    if layers > 1:
        top = float(layers)
        z1 = top - .03 if roof else top
        C.framed_block(g, x0 + .05, y0 + .05, x1 - .05, y1 - .05, 1.0, z1, infill=infill, frame=frame,
                       pitch=pitch, faces=faces, floors=tuple(float(z) for z in range(2, layers)),
                       windows=windows)
    if roof:
        if layers > 1:
            # Over the framed core (inset .05) and past its proud frame (.055).
            flat_roof(g, x0 + .05, y0 + .05, x1 - .05, y1 - .05, top, overhang=EAVE + .05,
                      curb=curb, mat=roof_mat, curb_mat=curb_mat)
        elif curb:
            # The podium coping is the roof: add the curb on its edge.
            xa, ya, xb, yb = x0 - .05, y0 - .05, x1 + .05, y1 + .05
            w = CURB_W
            blk(g, xa, ya, top, xb, ya + w, top + CURB, CONCRETE)
            blk(g, xa, yb - w, top, xb, yb, top + CURB, CONCRETE)
            blk(g, xa, ya + w, top, xa + w, yb - w, top + CURB, CONCRETE)
            blk(g, xb - w, ya + w, top, xb, yb - w, top + CURB, CONCRETE)
    return top


def roof_vent(g, x, y, top, *, h=.34, r=.16):
    """Short steel vent stub on a flat roof (static part of a turbine vent)."""
    g.cylinder((x, y, top + h / 2), r * .7, h, IRON, 'Z', 12)
    g.cylinder((x, y, top + h - .015), r, .03, BRASS, 'Z', 12)
    return top + h
