"""Roof-deck parts for compacted late-game buildings (2026-10-30 compaction pass).

`lategame_kit.parapet` caps its ring with one solid plate over the whole roof
(a lid), so the roof under it is neither open to the sky nor platformable
(measure_connection_faces.py records every roof cell as covered and blocked).
`parapet_ring` is a parapet that is only a ring: four walls and four cap
strips, so the roof inside stays a usable roof deck (tools/roof_decks.json).
The walls stay within the 0.15 occupancy inset of the edge cells, and within
0.31 of the cell edges, so they neither claim the cells above the roof nor
block them as a roof deck.
"""
from frontier_architecture import IRON
from lategame_kit import CONCRETE
from lategame_civic_parts import blk


def parapet_ring(g, x0, y0, x1, y1, z, *, height=.26, t=.13, cap=.02, mat=CONCRETE, open_sides=()):
    """Parapet walls (thickness t) standing on a roof at z, outer faces on the
    given rectangle, with an IRON cap strip `cap` proud on each side.
    `open_sides` ('front', 'back', 'left', 'right') leaves a side without
    wall (where the roof abuts a taller block). Corners never overlap."""
    if not (x1 - x0 > 2 * t and y1 - y0 > 2 * t and height > 0):
        raise ValueError(f'Degenerate parapet {x0, y0, x1, y1}')
    zt = z + height
    front, back = 'front' not in open_sides, 'back' not in open_sides
    left, right = 'left' not in open_sides, 'right' not in open_sides
    # Front and back walls run the full width; side walls fit between them.
    ya = y0 + t if front else y0
    yb = y1 - t if back else y1
    if front:
        blk(g, x0, y0, z, x1, y0 + t, zt, mat)
        blk(g, x0 - (cap if left else 0), y0 - cap, zt, x1 + (cap if right else 0), y0 + t + cap, zt + .04, IRON)
    if back:
        blk(g, x0, y1 - t, z, x1, y1, zt, mat)
        blk(g, x0 - (cap if left else 0), y1 - t - cap, zt, x1 + (cap if right else 0), y1 + cap, zt + .04, IRON)
    ca = ya + (cap if front else 0)
    cb = yb - (cap if back else 0)
    if left:
        blk(g, x0, ya, z, x0 + t, yb, zt, mat)
        blk(g, x0 - cap, ca, zt, x0 + t + cap, cb, zt + .04, IRON)
    if right:
        blk(g, x1 - t, ya, z, x1, yb, zt, mat)
        blk(g, x1 - t - cap, ca, zt, x1 + cap, cb, zt + .04, IRON)
