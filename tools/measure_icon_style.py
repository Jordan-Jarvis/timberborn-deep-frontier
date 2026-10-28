"""Measure UI icon conventions for docs/art/icon-style.md.

Usage (vendored Pillow):
  PYTHONPATH=tools/asset-pipeline/unitypy python tools/measure_icon_style.py [--shadow] <png> ...

Per icon: canvas, alpha bounds (alpha > 24), padding, artwork extent, dominant
light ink colours and median ink luminance, and line width (2 x area / edge).
--shadow also least-squares fits the drop shadow (offset, blur sigma, opacity)
as a blurred, shifted copy of the ink coverage. Reference sprites come from
tools/asset-pipeline/export_vanilla_icon_references.py (outputs/vanilla-icons).
"""
import itertools, json, os, statistics, sys
from collections import Counter
from PIL import Image, ImageChops, ImageFilter


def coverage(im):
    """Split RGBA into ink coverage and dark (shadow) coverage, both 0-255."""
    ink, dark = Image.new('L', im.size), Image.new('L', im.size)
    ip, dp, px = ink.load(), dark.load(), im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            f = min(1.0, (0.299 * r + 0.587 * g + 0.114 * b) / 165)
            ip[x, y], dp[x, y] = int(a * f), int(a * (1 - f))
    return ink, dark


def measure(path, fit_shadow):
    im = Image.open(path).convert('RGBA')
    w, h = im.size
    px = im.load()
    colours, lum = Counter(), []
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            l = 0.299 * r + 0.587 * g + 0.114 * b
            if a >= 200 and l > 90:
                colours[(r // 8 * 8, g // 8 * 8, b // 8 * 8)] += 1
                lum.append(l)
    bbox = im.getchannel('A').point(lambda v: 255 if v > 24 else 0).getbbox()
    ink, dark = coverage(im)
    solid = {(x, y) for y in range(h) for x in range(w) if ink.getpixel((x, y)) > 127}
    edge = sum(1 for x, y in solid if any(n not in solid for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))))
    row = {
        'icon': os.path.basename(path), 'size': [w, h], 'bbox': bbox,
        'pad_lrtb': [bbox[0], w - bbox[2], bbox[1], h - bbox[3]] if bbox else None,
        'extent': round(max(bbox[2] - bbox[0], bbox[3] - bbox[1]) / max(w, h), 3) if bbox else 0,
        'ink_colours': ['#%02x%02x%02x' % c for c, _ in colours.most_common(3)],
        'ink_lum_median': round(statistics.median(lum), 1) if lum else None,
        'line_px': round(2 * len(solid) / edge, 2) if edge else None,
    }
    if fit_shadow:
        target, base = list(dark.getdata()), list(ink.getdata())
        best = None
        for dx, dy, sigma, opacity in itertools.product(range(-1, 4), range(0, 6), [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4], [0.3, 0.5, 0.8, 0.95]):
            shade = list(ImageChops.offset(ink, dx, dy).filter(ImageFilter.GaussianBlur(sigma)).getdata())
            err = sum((opacity * s * (1 - i / 255) - t) ** 2 for s, i, t in zip(shade, base, target))
            if best is None or err < best[0]:
                best = (err, dx, dy, sigma, opacity)
        row['shadow'] = {'dx': best[1], 'dy': best[2], 'sigma': best[3], 'opacity': best[4]}
    return row


if __name__ == '__main__':
    args = sys.argv[1:]
    fit = '--shadow' in args
    for path in (a for a in args if a != '--shadow'):
        print(json.dumps(measure(path, fit)))
