"""Roof-deck parts for late-game buildings.

Flat roofs are plain open platforms edge to edge: no parapet, curb, cap strip
or rail at the edge (user, 2026-10-31: "lets remove the railings and cement
railing/mini walls on the roofs of our buildings. I want it to be like an
actual platform where roads can connect. buildings can be built on edges of
two buildings butting up to each other"). Every flat roof cell, edge rows
included, is then a platformable roof deck (tools/roof_decks.json) with a
free cell above, so paths join across abutting roofs and a building can
straddle two of them. Never lid a roof (`lategame_kit.parapet` is gone).
"""
from frontier_architecture import IRON
from lategame_kit import CONCRETE
from lategame_civic_parts import blk


# Flat-roof finishes (BRIEF "ROOF VARIETY", user 2026-10-30: timber decks, metal
# and steel sheet, concrete only some of the time). Existing native materials only.
from frontier_architecture import PLANK
from lategame_kit import FORGED, PAINTED, GREYPLANK
FINISHES = {'timber': PLANK, 'greytimber': GREYPLANK, 'forged': FORGED, 'painted': PAINTED, 'steel': IRON,
            'concrete': CONCRETE}


STRIP = {'timber': .25, 'greytimber': .25, 'forged': .5, 'painted': .5, 'steel': 1.0}


def deck_slab(g, x0, y0, x1, y1, top, finish, *, thickness=.16, base=CONCRETE):
    """Flat roof slab whose top is exactly `top` (a whole layer, so it can be a
    roof deck), in one of FINISHES. Plank and sheet finishes are laid as
    separate boards or sheets (STRIP wide, running along the longer side) on a
    slab of `base` material, so each board takes its own native texture
    island instead of one stretched over the whole roof."""
    if finish not in FINISHES:
        raise ValueError(f'Unknown roof finish {finish!r}; one of {sorted(FINISHES)}')
    if finish == 'concrete':
        blk(g, x0, y0, top - thickness, x1, y1, top, CONCRETE)
        return
    skin = .03
    blk(g, x0, y0, top - thickness, x1, y1, top - skin, base)
    along_x = (x1 - x0) >= (y1 - y0)
    a0, a1 = (y0, y1) if along_x else (x0, x1)
    n = max(1, round((a1 - a0) / STRIP[finish]))
    for i in range(n):
        u0, u1 = a0 + (a1 - a0) * i / n, a0 + (a1 - a0) * (i + 1) / n
        if along_x:
            blk(g, x0, u0, top - skin, x1, u1, top, FINISHES[finish])
        else:
            blk(g, u0, y0, top - skin, u1, y1, top, FINISHES[finish])
