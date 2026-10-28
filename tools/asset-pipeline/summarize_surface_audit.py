"""Index explicitly requested surface reports; reject stale scene evidence."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'outputs/zfight'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', required=True)
    parser.add_argument('--frames', default='1')
    parser.add_argument('--rendered', action='store_true')
    args = parser.parse_args()
    records = []
    for model in args.models.split(','):
        for frame in map(int, args.frames.split(',')):
            stem = f'{model}-frame{frame}'
            path = FOLDER / f'{stem}.json'
            report = json.loads(path.read_text(encoding='utf-8'))
            if report['model'] != model or report['frame'] != frame:
                raise ValueError(f'Report identity mismatch: {path}')
            if digest(ROOT / report['sourceScene']) != report['sourceSha256']:
                raise ValueError(f'Scene changed after audit: {model}')
            record = {key: report[key] for key in (
                'model', 'frame', 'sourceScene', 'sourceSha256', 'detectorSha256',
                'visibleConflicts', 'occludedConflicts', 'identicalMaterialAndUvPairs',
                'epsilon', 'minimumOverlapArea', 'parallelAngleDegrees', 'triangles')}
            record['reportSha256'] = digest(path)
            record['markdownSha256'] = digest(FOLDER / f'{stem}.md')
            if args.rendered:
                record['imageSha256'] = digest(FOLDER / f'{stem}.png')
            records.append(record)
    lines = ['# Detailed building surface audit', '',
             'Geometric candidates at the listed poses. Counts are overlapping triangle pairs, '
             'not distinct visible defects. Red images mark sampled potentially visible regions. '
             'These reports do not certify in-game rendering.', '',
             '| Model | Frame | Potentially visible pairs | Occluded pairs | Report |',
             '| --- | ---: | ---: | ---: | --- |']
    for record in records:
        model = record['model']; frame = record['frame']
        lines.append(f'| {model} | {frame} | {record["visibleConflicts"]:,} | '
                     f'{record["occludedConflicts"]:,} | [Review]({model}-frame{frame}.md) |')
    lines += ['', 'Scene hashes were checked against the current saved sources when this index was generated. '
              '`index.json` records source, detector and report hashes. A later source change invalidates the corresponding evidence.', '',
              'Commands, tolerances, verified synthetic cases and limitations: '
              '[surface-check documentation](../../docs/art/z-fighting-checks.md).', '']
    (FOLDER / 'index.md').write_text('\n'.join(lines), encoding='utf-8')
    (FOLDER / 'index.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'reports': len(records),
                      'modelsWithVisibleCandidates': sum(r['visibleConflicts'] > 0 for r in records),
                      'index': str(FOLDER / 'index.md')}))


if __name__ == '__main__':
    main()
