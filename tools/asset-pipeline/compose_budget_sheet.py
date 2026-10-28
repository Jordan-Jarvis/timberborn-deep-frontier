"""Before | after | difference review sheet from render_budget_views.py output.

The difference column shows the absolute per-pixel change (x4) in grey, with
pixels whose change exceeds THRESHOLD (out of 255, max over RGB) in red, and
reports their share per view, so visibly changed regions are flagged rather
than averaged away.

Run: python compose_budget_sheet.py --study FisheryWorks --dir RENDERS
        --out outputs/review-sheets/triangle-budget-civic-FisheryWorks.png
        --title "..." [--report JSON]
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

THRESHOLD = 24
VIEWS = ('normal-front', 'normal-rear', 'close-front', 'close-rear')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', required=True)
    parser.add_argument('--dir', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--title', required=True)
    parser.add_argument('--report')
    parser.add_argument('--tile', type=int, default=640)
    cli = parser.parse_args()
    folder = Path(cli.dir)
    tile = cli.tile
    font = ImageFont.load_default(size=22)
    small = ImageFont.load_default(size=18)
    head = 70
    label = 34
    sheet = Image.new('RGB', (tile * 3, head + len(VIEWS) * (tile + label)), (24, 24, 26))
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 10), cli.title, fill=(235, 235, 235), font=font)
    draw.text((12, 40), f'columns: before | after | difference (x4 grey; red = change > {THRESHOLD}/255)', fill=(180, 180, 180), font=small)
    report = {}
    for row, view in enumerate(VIEWS):
        before = Image.open(folder / f'{cli.study}-{view}-before.png').convert('RGB')
        after = Image.open(folder / f'{cli.study}-{view}-after.png').convert('RGB')
        a = np.asarray(before).astype(np.int16)
        b = np.asarray(after).astype(np.int16)
        delta = np.abs(a - b).max(axis=2)
        changed = delta > THRESHOLD
        diff = np.clip(np.abs(a - b) * 4, 0, 255).astype(np.uint8)
        diff[changed] = (230, 40, 40)
        share = float(changed.mean())
        report[view] = {'changedShare': round(share, 5), 'meanAbsDelta': round(float(np.abs(a - b).mean()), 3)}
        y = head + row * (tile + label)
        for col, image in enumerate((before, after, Image.fromarray(diff))):
            sheet.paste(image.resize((tile, tile), Image.LANCZOS), (col * tile, y + label))
        draw.text((12, y + 6), f'{view}: {share * 100:.2f}% of pixels changed > {THRESHOLD}', fill=(220, 220, 220), font=small)
    out = Path(cli.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    if cli.report:
        Path(cli.report).write_text(json.dumps({'study': cli.study, 'threshold': THRESHOLD, 'views': report}, indent=1) + '\n')
    print(json.dumps({'sheet': str(out), **report}))


if __name__ == '__main__':
    main()
