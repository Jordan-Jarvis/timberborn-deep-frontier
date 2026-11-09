"""Compose a labelled contact sheet from More Fluids review renders.

  python more_fluids_sheet.py OUT.png --columns 4 --cell 420 LABEL=PATH [LABEL=PATH ...]

Each image is scaled into a square cell with its label underneath, on the
dark vanilla panel colour. Review output only (outputs/more-fluids-art).
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BACKGROUND = (52, 48, 43)
INK = (240, 230, 208)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output')
    parser.add_argument('items', nargs='+', help='LABEL=PATH')
    parser.add_argument('--columns', type=int, default=4)
    parser.add_argument('--cell', type=int, default=420)
    parser.add_argument('--title')
    cli = parser.parse_args()
    items = [item.split('=', 1) for item in cli.items]
    for label_path in items:
        if len(label_path) != 2 or not Path(label_path[1]).is_file():
            raise SystemExit(f'Bad item {label_path}: expected LABEL=existing image path')
    cell, label_h = cli.cell, 30
    title_h = 40 if cli.title else 0
    rows = (len(items) + cli.columns - 1) // cli.columns
    sheet = Image.new('RGB', (cli.columns * cell, title_h + rows * (cell + label_h)), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype('arial.ttf', 17)
        title_font = ImageFont.truetype('arialbd.ttf', 22)
    except OSError:
        font = title_font = ImageFont.load_default()
    if cli.title:
        draw.text((12, 8), cli.title, fill=INK, font=title_font)
    for index, (label, path) in enumerate(items):
        image = Image.open(path).convert('RGBA')
        image.thumbnail((cell - 8, cell - 8))
        x = (index % cli.columns) * cell + (cell - image.width) // 2
        y = title_h + (index // cli.columns) * (cell + label_h) + (cell - image.height) // 2
        sheet.paste(image, (x, y), image)
        draw.text(((index % cli.columns) * cell + 8, title_h + (index // cli.columns) * (cell + label_h) + cell + 2),
                  label, fill=INK, font=font)
    Path(cli.output).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(cli.output)
    print('sheet', cli.output, sheet.size)


if __name__ == '__main__':
    main()
