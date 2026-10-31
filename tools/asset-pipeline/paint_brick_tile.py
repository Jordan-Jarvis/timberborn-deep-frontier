"""Paint the Deep Frontier brick tile, DFIndustrial06 (2026-10-31, bricks pass).

blender --background --factory-startup --python tools/asset-pipeline/paint_brick_tile.py

Writes src/DeepFrontier/AssetBundles/Resources/Materials/DeepFrontierIndustrial/
DFIndustrial06.BaseColor.png. The slot was the retired aggregate tile, which no
exported model used. Original procedural artwork from a fixed seed; nothing is
read from the game.

Scale. Custom industrial tiles are world-projected at one texture per tile
(frontier_architecture.Geometry.build: u, v = the two in-plane coordinates), so
the 512 px tile is one tile wide and one height layer tall: 512 px per tile,
the density of every other DFIndustrial tile. A Timberborn tile is about a
beaver and a half tall, so it carries 8 courses (4 per half tile) of 3
stretchers: bricks about 2.7 times as long as their course, as real bricks,
and big enough to read at the game's camera distance. The courses run along
u (image x), so they stay horizontal on every wall, and the tile repeats on
both axes (512 = 8 x 64; the offset rows repeat every 3 bricks).

Style. Flat hand-painted colour in the native manner: each brick its own red
or brown from a small palette, a soft lighter top edge and darker lower edge,
broad horizontal brush streaks and a few chips, set in grey lime mortar joints
wide enough (9 px) to survive the mipmaps at game zoom. Weathered brown-red
and terracotta, at the native textures' saturation and value (see PALETTE).
"""
from pathlib import Path
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'src/DeepFrontier/AssetBundles/Resources/Materials/DeepFrontierIndustrial/DFIndustrial06.BaseColor.png'
SIZE = 512
COURSES = 8
BRICKS = 3            # stretchers per course
JOINT = 9             # mortar joint width, px
SEED = 20261031
# sRGB weathered brown-reds and terracotta (2026-10-31, second pass: the
# first palette read as bright red beside the native textures). Measured in
# a lit swatch render beside the shipped Iron Teeth materials (mean HSV:
# Plaster_Orange S .68 V .60, Plaster_White S .10 V .66, dark planks
# S .13 V .25, BaseMetal V .47), the tile now sits at about S .34 V .46:
# darker than the plasters, lighter than the timber.
PALETTE = np.array([
    (103, 56, 44), (92, 50, 40), (111, 64, 49), (85, 49, 40), (99, 59, 45),
    (82, 52, 42), (106, 68, 52), (94, 47, 38), (77, 47, 38), (115, 73, 56),
], float)
MORTAR = np.array((132, 128, 118), float)   # weathered grey lime, not stark white


def wrap_noise(rng, cells_x, cells_y):
    """Seamless value noise on the tile: bilinear on a wrapping lattice."""
    lattice = rng.random((cells_y, cells_x))
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(float)
    fx, fy = x / SIZE * cells_x, y / SIZE * cells_y
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - x0, fy - y0
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    x1, y1 = (x0 + 1) % cells_x, (y0 + 1) % cells_y
    x0, y0 = x0 % cells_x, y0 % cells_y
    a = lattice[y0, x0] * (1 - tx) + lattice[y0, x1] * tx
    b = lattice[y1, x0] * (1 - tx) + lattice[y1, x1] * tx
    return a * (1 - ty) + b * ty


def paint():
    rng = np.random.default_rng(SEED)
    course = SIZE / COURSES
    length = SIZE / BRICKS
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(float) + .5
    row = np.floor(y / course).astype(int)
    shift = np.where(row % 2 == 1, length / 2, 0.0)
    u = (x + shift) % SIZE
    col = np.floor(u / length).astype(int)
    # Distance to the nearest joint centre line, in px, for a soft joint edge.
    dy = np.minimum(y - row * course, (row + 1) * course - y)
    du = np.minimum(u - col * length, (col + 1) * length - u)
    edge = np.minimum(dy, du)
    brick = np.clip((edge - JOINT / 2 + .75) / 1.5, 0, 1)     # 1 inside a brick
    # One colour per brick (row, col), varied a little in value.
    ids = rng.integers(0, len(PALETTE), (COURSES, BRICKS))
    value = rng.uniform(.92, 1.06, (COURSES, BRICKS))
    colour = PALETTE[ids[row, col]] * value[row, col][..., None]
    # Painted relief: lighter top edge, darker lower edge (v grows upward in
    # Blender, so the image's last rows are the top of the wall).
    t = (y - row * course - JOINT / 2) / (course - JOINT)     # 0 bottom .. 1 top
    relief = 1 + .10 * np.clip((t - .78) / .22, 0, 1) - .12 * np.clip((.2 - t) / .2, 0, 1)
    colour *= relief[..., None]
    # Broad horizontal brush streaks and soft mottling, seamless.
    streak = wrap_noise(rng, 8, 64) - .5
    mottle = wrap_noise(rng, 16, 16) - .5
    colour *= (1 + .10 * streak + .12 * mottle)[..., None]
    # A few chips: small darker notches on brick corners.
    for _ in range(14):
        r, c = rng.integers(0, COURSES), rng.integers(0, BRICKS)
        cx = (c * length + rng.choice((JOINT, length - JOINT)) - (length / 2 if r % 2 else 0)) % SIZE
        cy = r * course + rng.choice((JOINT, course - JOINT))
        d = np.hypot(np.minimum(abs(x - cx), SIZE - abs(x - cx)), y - cy)
        colour *= (1 - .22 * np.clip(1 - d / rng.uniform(4, 8), 0, 1))[..., None]
    mortar = MORTAR * (1 + .08 * (wrap_noise(rng, 32, 32) - .5))[..., None]
    # The joint is a little shaded where it meets the brick above it.
    mortar *= (1 - .10 * np.clip(1 - dy / (JOINT / 2), 0, 1) * (y - row * course > course / 2))[..., None]
    rgb = colour * brick[..., None] + mortar * (1 - brick[..., None])
    return np.clip(rgb, 0, 255) / 255


def main():
    rgb = paint()
    image = bpy.data.images.new('DFIndustrial06', SIZE, SIZE, alpha=False)
    image.colorspace_settings.name = 'sRGB'
    pixels = np.ones((SIZE, SIZE, 4))
    pixels[..., :3] = rgb
    image.pixels.foreach_set(pixels.ravel().astype(np.float32))
    image.filepath_raw = str(OUT)
    image.file_format = 'PNG'
    image.save()
    print('BRICK TILE', OUT, flush=True)


if __name__ == '__main__':
    main()
