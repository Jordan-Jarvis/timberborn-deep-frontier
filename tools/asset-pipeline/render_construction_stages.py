"""Review renders of the construction stages (plain Python; renders through Blender).

  python render_construction_stages.py specs [--out DIR]
      writes <out>/after-spec.json (each generated stage) and <out>/before-spec.json
      (each finished model: what a construction site showed while its stage was a
      copy of it) for render_map_object_views.py, from the construction manifest;
  blender -b --factory-startup --python-exit-code 1 --python render_map_object_views.py --
      --spec <out>/after-spec.json --out <out>/renders --label after [--close] [--only A,B]
      (and the same for before); paths must be absolute;
  python render_construction_stages.py sheets [--out DIR] [--pairs A,B,...]
      composes <out>/construction-stages-after.png (every stage), and with --pairs
      <out>/construction-stages-before-after.png (finished model | stage per row).

Each model is placed at its BaseZ so the block grid stands on the review ground.
Default --out: outputs/construction-stages.
"""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / 'tools/construction_stages.json').read_text(encoding='utf-8'))


def specs(out):
    manifest = json.loads((ROOT / CONFIG['manifest']).read_text(encoding='utf-8'))['stages']
    export = ROOT / CONFIG['exportRoot']
    after, before = [], []
    for ident, entry in manifest.items():
        offset = [0, 0, entry['baseZ']]
        after.append({'id': ident, 'size': entry['size'], 'files': [{'path': str(export / entry['export']), 'offset': offset}]})
        before.append({'id': ident, 'size': entry['size'],
                       'files': [{'path': str(ROOT / 'src/DeepFrontier/Data' / f"{entry['finished']}.timbermesh"), 'offset': offset}]})
    out.mkdir(parents=True, exist_ok=True)
    (out / 'after-spec.json').write_text(json.dumps({'entries': after}, indent=1) + '\n', encoding='utf-8')
    (out / 'before-spec.json').write_text(json.dumps({'entries': before}, indent=1) + '\n', encoding='utf-8')
    print(f'{len(after)} entries -> {out}')


def sheets(out, pairs):
    from PIL import Image, ImageDraw
    renders = out / 'renders'
    manifest = json.loads((ROOT / CONFIG['manifest']).read_text(encoding='utf-8'))['stages']
    tile, label = 300, 20
    ids = sorted(manifest)
    cols = 9
    rows = math.ceil(len(ids) / cols)
    sheet = Image.new('RGB', (cols * tile, rows * (tile + label)), 'white')
    draw = ImageDraw.Draw(sheet)
    for i, ident in enumerate(ids):
        x, y = (i % cols) * tile, (i // cols) * (tile + label)
        sheet.paste(Image.open(renders / f'{ident}-after.png').convert('RGB').resize((tile, tile)), (x, y + label))
        draw.text((x + 4, y + 4), f"{ident} ({manifest[ident]['frame']}, {manifest[ident]['triangles']} tris)", fill=(0, 0, 0))
    sheet.save(out / 'construction-stages-after.png')
    print('wrote', out / 'construction-stages-after.png')
    if pairs:
        tile = 360
        cols = 4   # two pairs per row
        rows = math.ceil(len(pairs) / 2)
        sheet = Image.new('RGB', (cols * tile, rows * (tile + label) + label), 'white')
        draw = ImageDraw.Draw(sheet)
        draw.text((4, 4), 'Left: under construction before (the finished model). Right: the generated construction stage.', fill=(0, 0, 0))
        for i, ident in enumerate(pairs):
            x, y = (i % 2) * 2 * tile, (i // 2) * (tile + label) + label
            for j, kind in enumerate(('before', 'after')):
                sheet.paste(Image.open(renders / f'{ident}-{kind}.png').convert('RGB').resize((tile, tile)), (x + j * tile, y + label))
            draw.text((x + 4, y + 4), f'{ident}: before | after', fill=(0, 0, 0))
        sheet.save(out / 'construction-stages-before-after.png')
        print('wrote', out / 'construction-stages-before-after.png')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('specs', 'sheets'))
    parser.add_argument('--out', default=str(ROOT / 'outputs/construction-stages'))
    parser.add_argument('--pairs', default='')
    cli = parser.parse_args()
    out = Path(cli.out)
    if cli.mode == 'specs':
        specs(out)
    else:
        sheets(out, [p for p in cli.pairs.split(',') if p])


if __name__ == '__main__':
    main()
