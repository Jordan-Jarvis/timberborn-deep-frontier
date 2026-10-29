"""Archive a triangle-budget review of the civic, hydro, research and
waterside scenes.

Copies each model's before | after | difference sheet from
outputs/review-sheets into docs/art/reviews/<review folder>/ and writes
review.json with the reviewed scene's SHA256 next to each image's, in the
shape of the earlier exterior-repair review (validate_civic_exports.py checks
that the Restaurant scene is the reviewed one of the latest review). Re-run it
after the sheets are rendered from the saved scenes; it never renders or
saves a scene.

Run: python archive_triangle_budget_review.py --review 2026-10-29
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHEETS = ROOT / 'outputs/review-sheets'
REVIEWS = {
    # Shell build (no bevel, lean fasteners, enclosed-face cull) and the
    # removal of forced decoration beyond the walls.
    '2026-10-22': {
        'folder': '2026-10-22-triangle-budget',
        'models': {
            'FisheryWorks': ('FisheryWorks', 'triangle-budget-civic-FisheryWorks.png'),
            'FishHatchery': ('FishHatchery', 'triangle-budget-civic-FishHatchery.png'),
            'Restaurant': ('Restaurant', 'triangle-budget-civic-Restaurant.png'),
            'Hospital': ('Hospital', 'triangle-budget-civic-Hospital.png'),
            'GroceryStore': ('GroceryMarket', 'triangle-budget-grocery.png'),
            'MaterialsLaboratory': ('MaterialsLaboratory', 'triangle-budget-research.png'),
            'ReinforcedHydroTurbine': ('ReinforcedHydroTurbine', 'triangle-budget-hydro.png'),
        },
        'extra': ('no-forced-decor-civic.png',),
        'scope': 'Before | after | difference sheets (render_budget_views.py, compose_budget_sheet.py) of the shell '
                 'build (no bevel, lean fasteners, enclosed-face cull) and the removal of forced decoration and '
                 'aprons beyond the walls (2026-10-22). Blender renders, not game screenshots.',
    },
    # 20k grand cap: no fastener heads, plain collars, undersides culled,
    # fewer sides, sheets, boards and stock-item triangles. FishHatchery's
    # scene is unchanged and stays in the 2026-10-22 review.
    '2026-10-29': {
        'folder': '2026-10-29-triangle-budget-20k',
        'models': {
            'FisheryWorks': ('FisheryWorks', 'triangle-budget-20k-FisheryWorks.png'),
            'Restaurant': ('Restaurant', 'triangle-budget-20k-Restaurant.png'),
            'Hospital': ('Hospital', 'triangle-budget-20k-Hospital.png'),
            'GroceryStore': ('GroceryMarket', 'triangle-budget-20k-GroceryStore.png'),
            'MaterialsLaboratory': ('MaterialsLaboratory', 'triangle-budget-20k-MaterialsLaboratory.png'),
            'ReinforcedHydroTurbine': ('ReinforcedHydroTurbine', 'triangle-budget-20k-ReinforcedHydroTurbine.png'),
        },
        'extra': (),
        'scope': 'Before | after | difference sheets (render_budget_views.py, compose_budget_sheet.py) of the 20k '
                 'grand-cap pass (2026-10-29): no fastener heads, plain collars, undersides no orbit camera faces '
                 'culled (Geometry.cull_below), fewer sides, roof sheets, boards and stock-item triangles. Blender '
                 'renders, not game screenshots.',
    },
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', required=True, choices=sorted(REVIEWS))
    review = REVIEWS[parser.parse_args().review]
    folder = ROOT / 'docs/art/reviews' / review['folder']
    folder.mkdir(parents=True, exist_ok=True)
    renders = []
    for model, (study, sheet) in review['models'].items():
        source = Path('src/DeepFrontier/Art/Source') / f'{study}-ReferenceStudy.blend'
        image = SHEETS / sheet
        if not image.is_file():
            raise SystemExit(f'{model}: missing review sheet {image}')
        shutil.copyfile(image, folder / sheet)
        renders.append({'model': model, 'source': str(source), 'sourceSha256': sha(ROOT / source),
                        'images': [sheet], 'imageSha256': {sheet: sha(folder / sheet)}})
    for name in review['extra']:
        if not (SHEETS / name).is_file():
            raise SystemExit(f'missing extra review image {SHEETS / name}')
        shutil.copyfile(SHEETS / name, folder / name)
    (folder / 'review.json').write_text(json.dumps({
        'scope': review['scope'], 'renders': renders, 'extraImages': list(review['extra'])}, indent=2) + '\n',
        encoding='utf-8')
    print(json.dumps({'archived': len(renders), 'folder': str(folder)}))


if __name__ == '__main__':
    main()
