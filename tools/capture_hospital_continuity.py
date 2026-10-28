"""Archive a completed native hospital reload against its explicit main save."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--build', type=int, required=True)
parser.add_argument('--baseline-build', type=int, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
log_path = root / f'outputs/hospital-reload{args.build}.log'
log = log_path.read_text(encoding='utf-8')
assert '[DeepFrontier Hospital Reload] FAILED' not in log
assert 'ALL RELOAD, NEIGHBORHOOD, SUPPLY AND PARTIAL-STAFF CHECKS PASSED AND SAVED' in log
baseline = json.loads((root / f'outputs/hospital-verification{args.baseline_build}.json').read_text(encoding='utf-8'))
source = Path('C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance/Hospital continuity - verified.timber')
assert source.stat().st_mtime >= log_path.stat().st_ctime, 'Native save predates this reload run'
with zipfile.ZipFile(source) as archive:
    world = json.loads(archive.read('world.json'))
assert any(e['Components']['NamedEntity']['EntityName'] == 'Deep Frontier Acceptance Fixture'
           for e in world['Entities'] if 'NamedEntity' in e['Components'])
for expected in baseline['entities']:
    found = [e for e in world['Entities'] if e['Id'] == expected['id']]
    assert len(found) == 1, ('Missing saved entity', expected)
    actual = found[0]
    x, y, z = expected['position']
    assert actual['Template'] == expected['template'], expected
    assert actual['Components']['BlockObject']['Coordinates'] == {'X': x, 'Y': y, 'Z': z}, expected
hospitals = [e for e in world['Entities'] if e['Template'] == 'Hospital.IronTeeth']
assert len(hospitals) == 1
assert hospitals[0]['Components']['PausableBuilding']['Paused']
target = root / f'outputs/hospital-continuity-build{args.build}.timber'
shutil.copyfile(source, target)
report = {
    'build': args.build,
    'baselineBuild': args.baseline_build,
    'archive': str(target.relative_to(root)),
    'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'verifiedPlacements': len(baseline['entities']),
    'entities': baseline['entities'],
    'scope': 'Native reload, care, neighborhood, supply and partial-staff checks; exact saved placement identities and coordinates preserved. One authored orientation.'
}
(root / f'outputs/hospital-continuity-verification{args.build}.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: value for key, value in report.items() if key != 'entities'}, indent=2))
