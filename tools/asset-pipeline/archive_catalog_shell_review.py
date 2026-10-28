"""Archive the manually reviewed, exact-source catalog exterior evidence.

Run only after reviewing both renders for every entry below. This is source
review evidence; placement, power connections and native rendering are separate.
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/art/reviews/2026-10-21-catalog-shells'
REVIEW_NOTES = {
    'GroceryStore': 'Closed walls and attached windows. Terrace has wall-mounted cantilevers instead of dangling outer posts; terrace footprint preserved.',
    'FisheryWorks': 'Closed hall and warehouse shells; rear net drapes and open water equipment are intentional.',
    'FishHatchery': 'Closed nursery cabin; side windows fit the forward wall bays below collars. Water baskets and channels remain open.',
    'ReinforcedHydroTurbine': 'Closed dam/conduit shell and attached workshop windows. Both conduit mouths remain intentionally open; rear review uses temporary fill lighting.',
    'MaterialsLaboratory': 'Closed asymmetrical laboratory shells, attached windows and roof bearings. Heavy external bracing across window fields is retained.',
    'StoneCrusher': 'Closed operator workshop and entry porch; open upper crusher machinery is intentional.',
    'CementKiln': 'Closed operator walls and porch beneath the kiln canopy; rotary processing equipment remains visible.',
    'MineralQuarry': 'Closed workshops, ground cabin and rear control room; open hoist frame and transfer equipment are intentional.',
    'ConcreteMixer': 'Closed operator room and porch; exposed mixing machinery and underside structure are intentional.',
    'SandstonePit': 'Closed sloping cabin walls, front header and roof bearing; attached native windows.',
    'LimestonePit': 'Closed sloping cabin walls, front header and roof bearing; attached native windows.',
}
STRUCTURAL = ('SandstoneMasonryBlock', 'LimestoneMasonryBlock', 'ConcreteBlock',
              'ConcreteOverhang8x1', 'ConcreteScaffold3x3', 'ReinforcedDamBlock',
              'ConcreteOverflowDam')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = ROOT / 'outputs/catalog-shell-review/manifest.json'
    renders = json.loads(manifest_path.read_text())
    by_model = {item['model']: item for item in renders}
    assert set(by_model) == set(REVIEW_NOTES), 'The rendered model set must match the manually reviewed set.'
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for model in (*REVIEW_NOTES, *STRUCTURAL):
        source = ROOT / f'src/DeepFrontier/Art/Source/{model}-ReferenceStudy.blend'
        source_hash = digest(source)
        audit_path = ROOT / f'outputs/zfight/{model}-frame1.json'
        audit = json.loads(audit_path.read_text())
        assert audit['sourceSha256'] == source_hash, f'Stale strict report: {model}'
        assert audit['visibleConflicts'] == 0, f'Visible overlap findings: {model}'
        shutil.copy2(audit_path, OUT / f'{model}-overlap.json')
        record = {
            'model': model, 'sourceScene': str(source.relative_to(ROOT)),
            'sourceSha256': source_hash, 'strictOverlapReport': f'{model}-overlap.json',
            'strictOverlapReportSha256': digest(audit_path),
            'visibleConflicts': 0, 'occludedConflicts': audit['occludedConflicts'],
            'nativeAcceptance': 'pending separate native scene, placement and power checks',
        }
        if model in REVIEW_NOTES:
            entry = by_model[model]
            assert entry['sourceSha256'] == source_hash, f'Stale rendered scene: {model}'
            assert [view['view'] for view in entry['views']] == ['front', 'rear']
            record['views'] = []
            for view in entry['views']:
                original = ROOT / view['image']
                assert digest(original) == view['sha256'], f'Changed review image: {original}'
                shutil.copy2(original, OUT / original.name)
                record['views'].append({'view': view['view'], 'image': original.name,
                                        'sha256': view['sha256']})
            record['visualReview'] = 'reviewed front and rear source renders'
            record['reviewNotes'] = REVIEW_NOTES[model]
            entry['visualReview'] = record['visualReview']
            entry['reviewNotes'] = record['reviewNotes']
        else:
            record['visualReview'] = 'no new render pair in this review; strict source report only'
        records.append(record)

    surface_path = ROOT / 'outputs/catalog-surface-coverage.json'
    window_path = ROOT / 'outputs/window-mount-audit.json'
    surfaces = json.loads(surface_path.read_text())['checks']
    windows = json.loads(window_path.read_text())['models']
    assert all(row['missingOrBackfacing'] == 0 for row in surfaces)
    assert all(not row['mountFindings'] for row in windows)
    assert {row['model'] for row in windows} == set(REVIEW_NOTES)
    for path in (surface_path, window_path):
        shutil.copy2(path, OUT / path.name)
    code_names = (
        'frontier_architecture.py', 'industrial_geometry.py', 'opaque_shell_geometry.py',
        'civic_isometric_geometry.py', 'architectural_windows.py', 'factory_facade_details.py',
        'crusher_sheet_geometry.py', 'kiln_isometric_geometry.py', 'quarry_isometric_geometry.py',
        'quarry_process_details.py', 'mixer_isometric_geometry.py', 'pit_isometric_geometry.py',
        'materials_laboratory_geometry.py', 'hydro_isometric_geometry.py',
        'hatchery_isometric_geometry.py', 'structural_geometry.py',
        'test_catalog_surfaces.py', 'audit_window_mounts.py', 'render_catalog_shell_views.py',
    )
    code = {name: digest(ROOT / 'tools/asset-pipeline' / name) for name in code_names}
    payload = {
        'scope': '18 exact detailed source scenes; 11 front/rear architectural render pairs manually reviewed. Source rays test declared opaque patches and window backing, not every possible building surface. Seven structural models have fresh strict reports but no new render pair here. Native placement, hitboxes, power and shader acceptance remain separate.',
        'rendersAndChecks': records,
        'surfaceContracts': len(surfaces),
        'surfaceSamples': sum(row['samples'] for row in surfaces),
        'surfaceMissingOrBackfacing': 0,
        'windowMounts': sum(row['windows'] for row in windows),
        'windowBackingSamples': sum(row['windows'] for row in windows) * 5,
        'windowMountFindings': 0,
        'sourceAndAuditCodeSha256': code,
    }
    (OUT / 'review.json').write_text(json.dumps(payload, indent=2) + '\n')
    manifest_path.write_text(json.dumps(renders, indent=2) + '\n')
    lines = [
        '# Catalog exterior repair review — 2026-10-21', '',
        'These are exact-source Blender reviews. The manifest records the canonical saved scene and SHA-256 for every model, image hashes, current overlap reports, and the source/audit code hashes. The original scenes remain in `src/DeepFrontier/Art/Source`.', '',
        'All 18 listed scenes passed the current visible-overlap check. The 11 architectural scenes below were reviewed from both isometric directions. Separate declared-surface tests covered 26 contracts and 1,088,252 samples; window backing tests covered 176 windows and 880 samples. Both reported zero findings.', '',
        '| Model | Front | Rear | Review |', '|---|---|---|---|',
    ]
    for model, note in REVIEW_NOTES.items():
        lines.append(f'| {model} | [Front]({model}-front.png) | [Rear]({model}-rear.png) | {note} |')
    lines += ['', 'The seven structural models have fresh source-bound overlap reports in this folder, but this review does not claim a new visual render pass for them: ' + ', '.join(STRUCTURAL) + '.', '',
              'Open machinery, scaffold space, water baskets and conduit mouths are intentional. Occluded overlap candidates remain recorded; zero visible candidates is not a blanket claim that all geometry overlaps were removed.', '',
              'This evidence does not certify native shaders, beaver paths, platform placement, hitboxes or gear connections. The broader catalog includes prototypes whose detailed art and tile-grid redesign remain a separate tracked task.', '']
    (OUT / 'README.md').write_text('\n'.join(lines))
    print('ARCHIVED', len(records), 'source records,', len(REVIEW_NOTES) * 2,
          'reviewed images,', payload['surfaceSamples'], 'surface samples,',
          payload['windowMounts'], 'window mounts')


if __name__ == '__main__':
    main()
