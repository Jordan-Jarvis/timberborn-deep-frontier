"""Brick-faced solid blocks (2026-10-30 bricks pass; flat tile 2026-10-31).

Bricks are the mod's painted running-bond tile, DFIndustrial06
(reference_materials.BRICK_TILE, paint_brick_tile.py), on flat faces. Custom
tiles are world-projected (frontier_architecture.Geometry.build), so the 8
courses per height layer line up across every face of a building. The first
pass modelled each brick as a Plaster_Orange box; that read as orange plaster
at game distance and cost thousands of triangles.

A block is a core in its own material, set back by BRICK_DEPTH on the brick
faces, with one brick slab on each brick face, so the block's extents do not
change and its top stays the core material. Front and back slabs run corner to
corner; the side slabs fit between them. The slabs only touch the core (their
backs face it), so no two faces overlap. Used through an explicit box function
so each geometry module keeps its own coordinate convention:

    brick_block(box, x0, x1, y0, y1, z0, z1, core, brick, faces=...)
    box(center, size, material)
"""

BRICK_DEPTH = .02    # brick slab in front of the core
BRICK = 'brick'      # sentinel material: a caller lays this block as brick
FACES = ('front', 'back', 'left', 'right')


def brick_block(box, x0, x1, y0, y1, z0, z1, core, brick, faces=FACES):
    if x1 <= x0 or y1 <= y0 or z1 <= z0:
        raise ValueError(f'Degenerate brick block {x0, x1, y0, y1, z0, z1}')
    unknown = set(faces) - set(FACES)
    if unknown or not faces:
        raise ValueError(f'Brick block faces must be a non-empty subset of {FACES}: {faces}')
    d = BRICK_DEPTH
    ca, cb = x0 + (d if 'left' in faces else 0), x1 - (d if 'right' in faces else 0)
    da, db = y0 + (d if 'front' in faces else 0), y1 - (d if 'back' in faces else 0)
    if cb <= ca or db <= da:
        raise ValueError(f'Brick block thinner than its brick faces {x0, x1, y0, y1}')

    def solid(lo, hi, material):
        box(tuple((lo[i] + hi[i]) / 2 for i in range(3)), tuple(hi[i] - lo[i] for i in range(3)), material)

    solid((ca, da, z0), (cb, db, z1), core)
    if 'front' in faces:
        solid((x0, y0, z0), (x1, da, z1), brick)
    if 'back' in faces:
        solid((x0, db, z0), (x1, y1, z1), brick)
    if 'left' in faces:
        solid((x0, da, z0), (ca, db, z1), brick)
    if 'right' in faces:
        solid((cb, da, z0), (x1, db, z1), brick)
