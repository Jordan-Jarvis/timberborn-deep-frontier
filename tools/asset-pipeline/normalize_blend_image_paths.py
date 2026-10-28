"""Point every image of the .blend scenes at its canonical file, by relative path.

blender --background --factory-startup --python tools/asset-pipeline/normalize_blend_image_paths.py -- <list file>

- Game textures ("<path id>-<texture>.<ext>") use src/DeepFrontier/Art/GameTextures/<name>
  (not tracked; extract_game_textures.py recreates it from the installed game).
- The flat DFArt*.png preview textures use src/DeepFrontier/Art/Textures/Packed/<name>:
  the asset bundle folder holds only the DFArt*.BaseColor materials, and a second
  file of the same name there collides in the bundle.
- Every other image keeps its file, which must be inside the repository.

A target file that exists with different bytes than the image's current file is an
error, as is an image outside the repository. Geometry, objects, materials and
node links must be unchanged; changed scenes are saved compressed, relative.
"""
import bpy, hashlib, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GAME = os.path.join(ROOT, 'src', 'DeepFrontier', 'Art', 'GameTextures')
PACKED = os.path.join(ROOT, 'src', 'DeepFrontier', 'Art', 'Textures', 'Packed')
GAME_NAME = re.compile(r'^\d+-.+\.(png|jpg|jpeg|tga|exr)$', re.I)
FLAT_DFART = re.compile(r'^DFArt[A-Za-z]+\.png$')
sys.path.insert(0, os.path.dirname(__file__))
from game_texture_refs import structure  # noqa: E402  (geometry/material fingerprint)


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def canonical(current):
    name = os.path.basename(current)
    if GAME_NAME.match(name):
        return os.path.join(GAME, name)
    if FLAT_DFART.match(name):
        return os.path.join(PACKED, name)
    if os.path.normcase(os.path.abspath(current)).startswith(os.path.normcase(ROOT) + os.sep):
        return current
    raise RuntimeError(f'Image outside the repository: {current}')


args = sys.argv[sys.argv.index('--') + 1:]
for path in [l.strip() for l in open(args[0], encoding='utf-8') if l.strip()]:
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    before, changed = structure(), 0
    for img in bpy.data.images:
        if img.source != 'FILE' or not img.filepath or img.packed_file:
            continue
        current = os.path.abspath(bpy.path.abspath(img.filepath))
        target = canonical(current)
        if not os.path.isfile(target):
            raise RuntimeError(f'{os.path.basename(path)}: {img.name} has no file at {target}')
        if os.path.isfile(current) and os.path.normcase(current) != os.path.normcase(target) and sha(current) != sha(target):
            raise RuntimeError(f'{os.path.basename(path)}: {current} and {target} differ')
        relative = bpy.path.relpath(target)
        if img.filepath != relative:
            img.filepath = relative
            changed += 1
    if changed:
        if structure() != before:
            raise RuntimeError(f'Scene changed while repointing: {path}')
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_mainfile(filepath=path, compress=True, relative_remap=True)
    print(f'NORMALIZED {os.path.basename(path)} {changed}', flush=True)
print('NORMALIZE COMPLETE', flush=True)
