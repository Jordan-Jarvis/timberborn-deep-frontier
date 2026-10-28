"""Recreate src/DeepFrontier/Art/GameTextures/ from your own Timberborn install.

python tools/asset-pipeline/extract_game_textures.py

The Blender scenes reference game textures (wood, plaster, metal, water and so on)
that belong to Mechanistry, so they are not in this repository. Each file is
named "<path id>-<texture name>.png" after its Texture2D in the game's
resources.assets; src/DeepFrontier/Art/GameTextures.json lists every one the
scenes use (written by game_texture_refs.py scan). This reads them with the
vendored UnityPy and writes the missing ones. A path id whose texture name no
longer matches (a game update) is an error, never a substitution.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'asset-pipeline' / 'unitypy'))
import UnityPy

GAME = Path('C:/Program Files (x86)/Steam/steamapps/common/Timberborn/Timberborn_Data/resources.assets')
OUT = ROOT / 'src' / 'DeepFrontier' / 'Art' / 'GameTextures'
names = json.loads((ROOT / 'src' / 'DeepFrontier' / 'Art' / 'GameTextures.json').read_text(encoding='utf-8'))
missing = [n for n in names if not (OUT / n).is_file()]
if not missing:
    print(f'All {len(names)} game textures are present in {OUT}')
    sys.exit(0)
if not GAME.is_file():
    raise SystemExit(f'Timberborn resources.assets not found at {GAME}')
env = UnityPy.load(str(GAME))
objects = {o.path_id: o for o in env.objects}
OUT.mkdir(parents=True, exist_ok=True)
for name in missing:
    m = re.match(r'^(\d+)-(.+)\.png$', name)
    if not m:
        raise SystemExit(f'Unexpected game texture name {name}')
    obj = objects.get(int(m.group(1)))
    if obj is None or obj.type.name != 'Texture2D':
        raise SystemExit(f'{name}: path id {m.group(1)} is not a Texture2D in this game version')
    tex = obj.parse_as_object()
    if tex.m_Name != m.group(2):
        raise SystemExit(f'{name}: path id {m.group(1)} is now "{tex.m_Name}" (game update); re-export the scenes')
    tex.image.save(OUT / name)
    print(f'extracted {name}')
print(f'{len(missing)} extracted, {len(names) - len(missing)} already present')
