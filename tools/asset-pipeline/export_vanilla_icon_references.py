"""Export vanilla 1.1 UI sprites as local icon-review references (never shipped).

Reads the installed game's resources.assets with the vendored UnityPy and writes
each Sprite's full source texture (the authored canvas, not UnityPy's tight
crop) to outputs/vanilla-icons/<Name>.png
(duplicate UI glyph names get __<path id>),
plus index.json with each sprite's texture size and rect. The goods/building
paths these sprites are addressed by are in outputs/native-civic-assets/resource-paths.json.
"""
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dev_environment as dev
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/unitypy'))
import UnityPy

GAME = dev.game_data()
OUT = ROOT / 'outputs/vanilla-icons'
OUT.mkdir(parents=True, exist_ok=True)

env = UnityPy.load(str(GAME / 'resources.assets'))
index = {}
for obj in env.objects:
    if obj.type.name != 'Sprite':
        continue
    sprite = obj.read()
    name = sprite.m_Name
    if name in index:  # a few UI glyphs exist twice; keep both, suffixed by path id
        name = name + '__' + str(obj.path_id)
    rect, tight = sprite.m_Rect, sprite.m_RD.textureRect
    texture = sprite.m_RD.texture.read()
    if (texture.m_Width, texture.m_Height) == (int(rect.width), int(rect.height)):
        image = texture.image  # one sprite per texture: keep the authored canvas and padding
    else:
        image = sprite.image  # atlas member: only the sprite's own pixels are meaningful
    image.save(OUT / (name + '.png'))
    index[name] = {'path_id': obj.path_id, 'size': list(image.size),
                   'rect': [rect.x, rect.y, rect.width, rect.height],
                   'tight_rect': [round(tight.x, 2), round(tight.y, 2), round(tight.width, 2), round(tight.height, 2)]}
if not index:
    raise SystemExit('No Sprite objects found in resources.assets')
(OUT / 'index.json').write_text(json.dumps(index, indent=1, sort_keys=True))
print('Exported', len(index), 'vanilla sprites to', OUT)
