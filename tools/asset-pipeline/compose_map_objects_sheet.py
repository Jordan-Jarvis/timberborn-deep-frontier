"""Compose the map-object review sheets from render_map_object_views.py output.

  python compose_map_objects_sheet.py before   -> outputs/review-sheets/map-objects-before.png
  python compose_map_objects_sheet.py after    -> outputs/review-sheets/map-objects-after.png

The before sheet shows each item as it is in the active Data (close and
normal view, icon, triangles, materials) with the audit finding. The after
sheet puts before and after side by side (same cameras) with both icons and
the new triangle count. Text comes from AUDIT below; numbers from the render
stats.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/map-objects'
SHEETS = ROOT / 'outputs/review-sheets'
DATA = ROOT / 'src/DeepFrontier/Data'
ICON_AFTER = Path.home() / 'dfs/mapobjects/src/DeepFrontier/Data'

ITEMS = [
    ('DeepOreVein', 'Deep Ore Vein (5x5x1)', 'MapEditor/Objects/DeepOreVein/DeepOreVeinIcon.png',
     'Was: 88 identical pebble blobs of one BaseMetal plate tile (wood-stripe atlas sheet), 12,774 tris, no collider (unselectable). Same mesh as both seams.',
     'Now: fractured dark bedrock pavement on a dark bedrock floor, a diagonal fissure with bursts of metallic ore crystals and rusted ore; low (0.3) under the mine floor; collider added.'),
    ('DeepOreSource', 'Deep Ore Source (2x2x2)', 'MapEditor/Objects/DeepOreSource/DeepOreSourceIcon.png',
     'Was: four plate-textured metal balloons; collider 0.49 under a 1.1 model.',
     'Now: rock mound split by metallic ore clusters, spilled ore at the worked front, access lane clear; collider fits 1.3.'),
    ('SandstoneSeam', 'Sandstone Seam (5x5x1)', 'MapEditor/Objects/SandstoneSeam/SandstoneSeamIcon.png',
     'Was: the vein mesh in orange plaster: a carpet of round blobs, 12,774 tris, full-layer collider.',
     'Now: warm stepped bedding terraces (Voronoi blocks), dark partings, weathered blocks; distinct from limestone by relief and colour.'),
    ('LimestoneSeam', 'Limestone Seam (5x5x1)', 'MapEditor/Objects/LimestoneSeam/LimestoneSeamIcon.png',
     'Was: the same blob carpet in white plaster; sandstone and limestone differed only in colour.',
     'Now: pale limestone pavement of clints and dark grikes, gently domed, two toppled blocks.'),
    ('SandstoneOutcrop', 'Sandstone Outcrop (1x1)', 'MapEditor/Objects/SandstoneOutcrop/SandstoneOutcropIcon.png',
     'Was: three orange plaster blobs (712 tris).',
     'Now: stacked tilted sandstone beds with a dark parting (145 tris).'),
    ('LimestoneOutcrop', 'Limestone Outcrop (1x1)', 'MapEditor/Objects/LimestoneOutcrop/LimestoneOutcropIcon.png',
     'Was: three white plaster blobs (712 tris).',
     'Now: a small jointed limestone tor of pale blocks (76 tris).'),
    ('RadioactiveSpringSource', 'Radioactive Spring (map + dev tool)', 'MapEditor/Objects/RadioactiveSpringSource/RadioactiveSpringSourceIcon.png',
     'Was: the vanilla water-source rock pile with every material replaced by flat emissive yellow-green: a neon blob.',
     'Now: a natural vent: native rock ring, glowing pool and sinter crusts (only the RadioactiveGlow node is tinted).'),
    ('HumanRecordCache', 'Human Record Cache (3x2x1)', 'MapEditor/Objects/HumanRecordCache/HumanRecordCacheIcon.png',
     'Was: the vanilla MediumRelic model and icon (a scrap heap), placeholder.',
     'Now: a half-buried old-world concrete vault with a bronze hatch, lintel, vent, rebar and record canisters; own icon.'),
    ('DeepOrePile', 'Deep Ore in piles', 'Sprites/Goods/DeepOreIcon.png',
     'Was: the vanilla ScrapMetal pile (rusted bars): ore read as scrap.',
     'Now: own pile model of rough ore nuggets (goods atlas, 64 tris per level = vanilla scrap).'),
    ('DeepAlloyPile', 'Deep Alloy in piles', 'Sprites/Goods/DeepAlloyIcon.png',
     'Was: the vanilla MetalBlock pile: identical to Metal Blocks.',
     'Now: own trapezoid ingots (goods atlas, 40 tris per level = vanilla blocks).'),
    ('CrudeOilTank', 'Crude Oil in tanks', 'Sprites/Goods/CrudeOilIcon.png',
     'Was: golden CanolaOil liquid material.',
     'Now: the native near-black Coffee liquid material.'),
    ('RadioactiveSludgeTank', 'Radioactive Sludge in tanks', 'Sprites/Goods/RadioactiveSludgeIcon.png',
     'Was: golden CanolaOil liquid material.',
     'Now: the native yellow-green Biofuel liquid material.'),
]

BG, PANEL, INK, DIM = (36, 38, 42), (48, 51, 56), (232, 228, 214), (170, 166, 152)


def font(size, bold=False):
    name = 'segoeuib.ttf' if bold else 'segoeui.ttf'
    return ImageFont.truetype(str(Path('C:/Windows/Fonts') / name), size)


def wrap(draw, text, width, f):
    words, lines, line = text.split(), [], ''
    for word in words:
        trial = (line + ' ' + word).strip()
        if draw.textlength(trial, font=f) > width and line:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def stats(label):
    path = OUT / label / f'{label}-stats.json'
    return json.loads(path.read_text()) if path.is_file() else {}


def tris(entry):
    return sum(f.get('triangles', 0) for f in entry.get('files', []))


def materials(entry):
    names = {}
    for f in entry.get('files', []):
        for k, v in f.get('materials', {}).items():
            names[k] = names.get(k, 0) + v
    return ', '.join(sorted(names)) or '-'


def paste_icon(sheet, path, x, y, size=72):
    if path.is_file():
        icon = Image.open(path).convert('RGBA')
        icon.thumbnail((size, size))
        sheet.alpha_composite(icon, (x, y))


def main(mode):
    tile = 300
    before, after = stats('before'), stats('after')
    title_f, head_f, body_f = font(30, True), font(19, True), font(15)
    if mode == 'before':
        cols = [('close', 'before'), ('', 'before')]
        width = 2 * tile + 560
    else:
        cols = [('close', 'before'), ('close', 'after'), ('', 'after')]
        width = 3 * tile + 520
    row_h = tile + 12
    sheet = Image.new('RGBA', (width, 70 + row_h * len(ITEMS)), BG)
    d = ImageDraw.Draw(sheet)
    d.text((16, 16), 'Deep Frontier map objects and goods - ' + ('BEFORE (active Data)' if mode == 'before' else 'BEFORE | AFTER (close) | AFTER'),
           font=title_f, fill=INK)
    for row, (ident, title, icon, was, now) in enumerate(ITEMS):
        y = 64 + row * row_h
        d.rectangle([8, y, width - 8, y + tile + 4], fill=PANEL)
        for c, (view, label) in enumerate(cols):
            image = OUT / label / f'{ident}{"-close" if view else ""}-{label}.png'
            if image.is_file():
                sheet.paste(Image.open(image).convert('RGB').resize((tile - 8, tile - 8)), (12 + c * tile, y + 6))
        x = 16 + len(cols) * tile
        d.text((x, y + 8), title, font=head_f, fill=INK)
        b, a = before.get(ident, {}), after.get(ident, {})
        lines = [f'Triangles: {tris(b)}' + (f'  ->  {tris(a)}' if mode == 'after' and a else ''),
                 'Materials: ' + (materials(a) if mode == 'after' and a else materials(b))]
        yy = y + 38
        for line in lines:
            for part in wrap(d, line, width - x - 110, body_f):
                d.text((x, yy), part, font=body_f, fill=DIM)
                yy += 20
        yy += 6
        for part in wrap(d, was if mode == 'before' else now, width - x - 120, body_f):
            d.text((x, yy), part, font=body_f, fill=INK)
            yy += 20
        before_icon = DATA / icon
        if not before_icon.is_file() and ident == 'HumanRecordCache':
            before_icon = ROOT / 'outputs/vanilla-icons/MediumRelicIcon.png'   # the vanilla placeholder it used
        paste_icon(sheet, before_icon, width - 100, y + 36)
        if mode == 'after':
            after_icon = ICON_AFTER / icon
            paste_icon(sheet, after_icon if after_icon.is_file() else DATA / icon, width - 100, y + 120)
            d.text((width - 100, y + 18), 'icons', font=body_f, fill=DIM)
    SHEETS.mkdir(parents=True, exist_ok=True)
    out = SHEETS / f'map-objects-{mode}.png'
    sheet.convert('RGB').save(out)
    print(out)


if __name__ == '__main__':
    main(sys.argv[1])
