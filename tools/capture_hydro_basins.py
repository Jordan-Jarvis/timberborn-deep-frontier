"""Archive the completed native two-turbine test and verify its saved entities."""
import argparse
import hashlib
import json
import math
import shutil
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--build', type=int, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
log = (root / f'outputs/hydro-basins{args.build}.log').read_text(encoding='utf-8')
assert '[DeepFrontier Hydro Basins] ALL CHECKS PASSED AND SAVED' in log
assert '[DeepFrontier Hydro Basins] FAILED:' not in log
assert not any(line.startswith(('- No Build Restriction (', '- All Buildings Transfer Power ('))
               for line in log.splitlines())
measurements = json.loads((root / 'outputs/hydro-basins-measurements.json').read_text(encoding='utf-8'))
assert len(measurements['windows']) == 2
for window in measurements['windows']:
    assert abs(window['volumeError']) < .5
    assert abs(window['transferError']) < 2
    assert abs(window['contaminationError']) < 1
    assert window['integratedGateVolume'] > 30
    assert window['peakFlows'][0] > .7 and window['peakFlows'][1] > 1.4
    phase_samples = [s for s in measurements['samples'] if s['phase'] == window['phase']]
    for index in range(2):
        assert max(s['turbines'][index]['nativeHp'] for s in phase_samples) > 100
        assert any(s['turbines'][index]['nativeHp'] == math.ceil(s['turbines'][index]['hp'])
                   and s['turbines'][index]['hp'] > 100 for s in phase_samples)
for sample in measurements['samples']:
    assert len(sample['turbines']) == 2
    for turbine in sample['turbines']:
        assert turbine['flow'] <= turbine['limit'] + .001
        assert abs(turbine['flow'] - sum(turbine['channels'])) < .001
        assert 0 <= turbine['nativeHp'] <= 9600
        assert math.isfinite(turbine['hp'])
reverse = [s for s in measurements['samples'] if s['phase'] == 8]
dry = [s for s in measurements['samples'] if s['phase'] == 10]
assert reverse and dry
assert all(t['hp'] == 0 and t['nativeHp'] == 0 for s in reverse + dry for t in s['turbines'])
assert all(t['downstream'] > t['upstream'] + 1 for t in reverse[-1]['turbines'])
assert all(t['state'] == 'Dry intake' for t in dry[-1]['turbines'])
source = Path('C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance/Hydro basins - verified.timber')
with zipfile.ZipFile(source) as z:
    world = json.loads(z.read('world.json'))
entities = {e['Id']: e for e in world['Entities']}
records = json.loads((root / 'outputs/hydro-basins-entities.json').read_text(encoding='utf-8'))
for record in records:
    entity = entities[record['Id']]
    assert entity['Template'] == record['Template']
    assert entity['Components']['BlockObject']['Coordinates'] == {
        axis.upper(): record['Coordinates'][axis] for axis in ('x', 'y', 'z')}
turbines = sorted((e for e in entities.values() if e['Template'] == 'ReinforcedHydroTurbine.IronTeeth'),
                  key=lambda e: e['Components']['BlockObject']['Coordinates']['X'])
assert len(turbines) == 2
for turbine, limit in zip(turbines, [.75, 1.5]):
    control = turbine['Components']['DeepFrontier.HydroTurbine']
    assert control['DischargeLimit'] == limit and control['ManuallyClosed']
archive = root / f'outputs/hydro-basins-build{args.build}.timber'
shutil.copyfile(source, archive)
shutil.copyfile(root / 'outputs/hydro-basins-measurements.json', root / f'outputs/hydro-basins-measurements{args.build}.json')
report = {'status': 'native-basin-fixture-passed', 'build': args.build, 'entities': len(records),
          'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'archive': str(archive),
          'peakNativeHp': [max(s['turbines'][i]['nativeHp'] for s in measurements['samples']) for i in range(2)],
          'reverseHeadSamples': len(reverse), 'droughtSamples': len(dry),
          'windows': measurements['windows'], 'checks': measurements['checks'],
          'scope': measurements['scope']}
(root / f'outputs/hydro-basins-verification{args.build}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'windows'}, indent=2))
