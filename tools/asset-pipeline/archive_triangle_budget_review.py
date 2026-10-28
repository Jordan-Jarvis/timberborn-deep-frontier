"""Archive the triangle-budget / no-forced-decoration review of the civic,
hydro, research and waterside scenes.

Copies each model's before | after | difference sheet from
outputs/review-sheets into docs/art/reviews/2026-10-22-triangle-budget/ and
writes review.json with the reviewed scene's SHA256 next to each image's, in
the shape of the earlier exterior-repair review (validate_civic_exports.py
checks that the Restaurant scene is the reviewed one). Re-run it after the
sheets are rendered from the saved scenes; it never renders or saves a scene.

Run: python archive_triangle_budget_review.py
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHEETS = ROOT / 'outputs/review-sheets'
FOLDER = ROOT / 'docs/art/reviews/2026-10-22-triangle-budget'
MODELS = {
    'FisheryWorks': ('FisheryWorks', 'triangle-budget-civic-FisheryWorks.png'),
    'FishHatchery': ('FishHatchery', 'triangle-budget-civic-FishHatchery.png'),
    'Restaurant': ('Restaurant', 'triangle-budget-civic-Restaurant.png'),
    'Hospital': ('Hospital', 'triangle-budget-civic-Hospital.png'),
    'GroceryStore': ('GroceryMarket', 'triangle-budget-grocery.png'),
    'MaterialsLaboratory': ('MaterialsLaboratory', 'triangle-budget-research.png'),
    'ReinforcedHydroTurbine': ('ReinforcedHydroTurbine', 'triangle-budget-hydro.png'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    FOLDER.mkdir(parents=True, exist_ok=True)
    renders = []
    for model, (study, sheet) in MODELS.items():
        source = Path('src/DeepFrontier/Art/Source') / f'{study}-ReferenceStudy.blend'
        image = SHEETS / sheet
        if not image.is_file():
            raise SystemExit(f'{model}: missing review sheet {image}')
        shutil.copyfile(image, FOLDER / sheet)
        renders.append({'model': model, 'source': str(source), 'sourceSha256': sha(ROOT / source),
                        'images': [sheet], 'imageSha256': {sheet: sha(FOLDER / sheet)}})
    extra = [p.name for p in (SHEETS / 'no-forced-decor-civic.png',) if p.is_file()]
    for name in extra:
        shutil.copyfile(SHEETS / name, FOLDER / name)
    (FOLDER / 'review.json').write_text(json.dumps({
        'scope': 'Before | after | difference sheets (render_budget_views.py, compose_budget_sheet.py) of the shell '
                 'build (no bevel, lean fasteners, enclosed-face cull) and the removal of forced decoration and '
                 'aprons beyond the walls (2026-10-22). Blender renders, not game screenshots.',
        'renders': renders, 'extraImages': extra}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'archived': len(renders), 'folder': str(FOLDER)}))


if __name__ == '__main__':
    main()
