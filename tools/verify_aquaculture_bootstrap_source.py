"""Read-only proof that the exact native bootstrap fixture has no fish stock."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT.parent / 'Timberborn/ExperimentalSaves/Industrial Acceptance/Reservoir acceptance - verified.timber'
with zipfile.ZipFile(source) as archive:
    world = json.loads(archive.read('world.json'))

goods = ('FreshFish', 'JuvenileFish')
assert 'Deep Frontier Acceptance Fixture' in json.dumps(world)
assert not any(e['Template'] in ('FisheryWorks.IronTeeth', 'FishHatchery.IronTeeth') for e in world['Entities'])

# Import settings mention every registered good; history samples must be zero.
# Neither component contains physical stock, carried goods or production state.
histories = []
def check_history(component):
    rows = component['GoodSamplingRegistry']['GoodSampleHistory']
    for row in rows:
        if row['Good'] in goods:
            for field in ('Stock', 'Capacity', 'Production', 'Consumption'):
                assert all(value == 0 for value in row[field]), row
            histories.append(row)

for entity in world['Entities']:
    for key, component in entity['Components'].items():
        if key == 'DistrictDistributionSetting':
            continue
        if key == 'DistrictGoodSamplingRegistry':
            check_history(component)
            continue
        assert not any(good in json.dumps(component) for good in goods), (entity['Template'], key)
for key, component in world['Singletons'].items():
    if key == 'GlobalGoodSamplingRegistry':
        check_history(component)
        continue
    assert not any(good in json.dumps(component) for good in goods), key

report = {
    'source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'gameVersion': world['GameVersion'], 'physicalFishStockOrProductionPresent': False,
    'zeroHistorySamplesChecked': len(histories),
    'scope': 'Exact native bootstrap source has no fish/juvenile stock, carrying, breeding or production. Native import settings are configuration, not goods.'
}
(ROOT / 'outputs/aquaculture-bootstrap-source.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
