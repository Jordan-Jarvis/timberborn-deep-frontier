"""Running-bond brick faces on a solid block (2026-10-30, bricks pass).

Brick coursing is geometry: the native atlases have no brick tile, so bricks
are boxes in the brick-red plaster (Plaster_Orange.IronTeeth) over a mortar
core set back by the brick depth, inside the block's extents. Front and back
courses run corner to corner; the side courses stop short of them, so no two
bricks share a face at a corner. Used through an explicit box function so
each geometry module keeps its own coordinate convention:

    brick_block(box, x0, x1, y0, y1, z0, z1, mortar, brick, faces=...)
    box(center, size, material)

The same dimensions as lategame_mining_parts' brick plinths (BRICK_*).
"""

BRICK_LENGTH = .42   # nominal stretcher; each run is divided evenly
BRICK_COURSE = .125  # nominal course height
BRICK_JOINT = .012
BRICK_DEPTH = .02    # brick face in front of the mortar core
BRICK_EMBED = .006   # brick backs sit inside the core
BRICK = 'brick'      # sentinel material: a caller lays this block as brick


def brick_runs(a, b, offset):
    """Brick extents along a run: whole bricks, or half bricks at both ends (offset course)."""
    count = max(1, round((b - a) / BRICK_LENGTH))
    w = (b - a) / count
    if offset and count > 1:
        cuts = [a] + [a + w * (i + .5) for i in range(count)] + [b]
    else:
        cuts = [a + w * i for i in range(count + 1)]
    return [(u, v) for u, v in zip(cuts, cuts[1:]) if v - u > BRICK_JOINT * 2]


def brick_block(box, x0, x1, y0, y1, z0, z1, mortar, brick, faces=('front', 'back', 'left', 'right')):
    if x1 <= x0 or y1 <= y0 or z1 <= z0:
        raise ValueError(f'Degenerate brick block {x0, x1, y0, y1, z0, z1}')
    d, e, j = BRICK_DEPTH, BRICK_EMBED, BRICK_JOINT
    ca, cb = x0 + (d if 'left' in faces else 0), x1 - (d if 'right' in faces else 0)
    da, db = y0 + (d if 'front' in faces else 0), y1 - (d if 'back' in faces else 0)
    box(((ca + cb) / 2, (da + db) / 2, (z0 + z1) / 2), (cb - ca, db - da, z1 - z0), mortar)
    n = max(1, round((z1 - z0) / BRICK_COURSE))
    pitch = (z1 - z0) / n
    side = (da + e + j if 'front' in faces else da, db - e - j if 'back' in faces else db)
    runs = {'front': (x0, x1), 'back': (x0, x1), 'left': side, 'right': side}
    for row in range(n):
        za, zb = z0 + row * pitch + j / 2, z0 + (row + 1) * pitch - j / 2
        for face in faces:
            for u, v in brick_runs(*runs[face], row % 2):
                u, v = u + j / 2, v - j / 2
                if face == 'front':
                    lo, hi = (u, y0, za), (v, da + e, zb)
                elif face == 'back':
                    lo, hi = (u, db - e, za), (v, y1, zb)
                elif face == 'left':
                    lo, hi = (x0, u, za), (ca + e, v, zb)
                else:
                    lo, hi = (cb - e, u, za), (x1, v, zb)
                box(tuple((lo[i] + hi[i]) / 2 for i in range(3)), tuple(hi[i] - lo[i] for i in range(3)), brick)
