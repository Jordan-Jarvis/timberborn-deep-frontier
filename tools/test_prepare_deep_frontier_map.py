"""Negative tests for the full-loop coverage and site checks of tools/prepare_deep_frontier_map.py.

Each case injects one fault into tools/map_variants/plains.json, builds it into a temporary folder
(maps, evidence and previews never touch Documents/Timberborn/Maps or outputs/maps) and expects a
specific error. Run from the repository root with the codex runtime Python:
  python tools/test_prepare_deep_frontier_map.py [scratch-dir]
"""
import contextlib
import copy
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, 'tools')
import prepare_deep_frontier_map as m

import tempfile
SP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix='df-map-tests-'))
m.ROOT = SP / 'negroot'          # evidence and previews go to the scratchpad
base = json.loads(Path('tools/map_variants/plains.json').read_text(encoding='utf-8'))
catalog = m.TemplateCatalog()


def site(v, template, n=0):
    return [s for s in v['sites'] if s['template'] == template][n]


def drop_placements(v, template):
    v['placements'] = [p for p in v['placements'] if p['template'] != template]


def drop_sites(v, template):
    v['sites'] = [s for s in v['sites'] if s['template'] != template]


def move(entry, dx=0, dy=0):
    entry['x'] += dx
    entry['y'] += dy


def edge_inward(v):
    s = site(v, 'RadioactiveWasteExport.IronTeeth')
    s['y'] += 3


def cache_without_site(v):
    label = [s for s in v['sites'] if s['template'] == 'ArchiveExcavation.IronTeeth'][0]['label']
    v['sites'] = [s for s in v['sites'] if s['label'] != label]


def hatchery_off_water(v):
    s = site(v, 'FishHatchery.IronTeeth')
    s['x'] += 6


def quarry_wrong_seam(v):
    site(v, 'SandstoneQuarry.IronTeeth')['understructure'] = site(v, 'LimestoneQuarry.IronTeeth')['understructure']


def overlap(v):
    a, b = site(v, 'SteelMill.IronTeeth'), site(v, 'DeepProcessor.IronTeeth')
    b.update(x=a['x'] + 2, y=a['y'] + 2, z=a['z'], orientation=a['orientation'])


def open_margin(v):
    # The vault's top row (blueprint depth, Cw0) lands in the row just south of the pad: its open S margin.
    pad = site(v, 'LaunchPad.IronTeeth')
    vault = site(v, 'RadioactiveWasteVault.IronTeeth')
    depth = catalog.get(vault['template'])['BlockObjectSpec']['Size']['Y']
    vault.update(x=pad['x'], y=pad['y'] - depth, z=pad['z'], orientation='Cw0')


def dynamite_outside(v):
    # Plains' sites list no Dynamite any more; a charge listed outside a site's footprint must
    # still fail.
    s = site(v, 'RadioactiveSludgeRecoveryPump.IronTeeth')
    s['dynamite'] = [[s['x'] - 10, s['y'] - 10, 1]]


def poor_sources(v):
    for p in v['placements']:
        if p['template'] == 'DeepOreSource':
            p['amount'] = 500


def dry_dam(v):
    s = site(v, 'ReinforcedHydroTurbine.IronTeeth')
    s['x'] += 8


def pit_far(v):
    pit = site(v, 'SandstonePit.IronTeeth')
    other = site(v, 'Restaurant.IronTeeth')
    pit.update(x=other['x'], y=other['y'], z=other['z'])
    drop_sites(v, 'Restaurant.IronTeeth')


def one_vein(v):
    veins = [p for p in v['placements'] if p['template'] == 'DeepOreVein'][1:]
    v['placements'] = [p for p in v['placements'] if p not in veins]
    keep = [s for s in v['sites'] if s['template'] != 'DeepMine.IronTeeth' or s.get('understructure') == [156, 102, 4]]
    v['sites'] = keep


def bad_template(v):
    v['sites'].append(dict(site(v, 'SteelMill.IronTeeth'), template='StoneCrusher.IronTeeth', label='crusher'))


def outcrop_in_water(v):
    p = [p for p in v['placements'] if p['template'] == 'SandstoneOutcrop'][0]
    hatch = site(v, 'FishHatchery.IronTeeth')
    p.update(x=hatch['x'] - 2, y=hatch['y'], z=hatch['z'])


def caches_four(v):
    cache = [p for p in v['placements'] if p['template'] == 'HumanRecordCache'][-1]
    v['placements'].remove(cache)


CASES = [
    ('no sandstone outcrops', lambda v: drop_placements(v, 'SandstoneOutcrop'), 'Sandstone deposits in range'),
    ('pit far from outcrops', pit_far, 'deposit within 20 steps'),
    ('no limestone seam', lambda v: drop_placements(v, 'LimestoneSeam'), 'understructure'),
    ('quarry on the wrong seam', quarry_wrong_seam, 'is not one placed'),
    ('export off the map edge', edge_inward, 'no occupied block on the map edge'),
    ('cache without an excavation site', cache_without_site, 'caches surveyable'),
    ('only four caches', caches_four, 'Human Record Caches in survey range'),
    ('hatchery off the water', hatchery_off_water, 'work cell'),
    ('overlapping sites', overlap, 'overlaps'),
    ('footprint in an open margin', open_margin, 'margin is inside'),
    ('dynamite outside the footprint', dynamite_outside, 'is outside the footprint'),
    ('finite deep ore too small', poor_sources, 'finite deep ore covers one of each building'),
    ('dam site on dry land', dry_dam, 'dam site is not a wet river cell'),
    ('one vein only', one_vein, 'DeepMine.IronTeeth site (understructure): 1 checked sites (min 2)'),
    ('no steel mill site', lambda v: drop_sites(v, 'SteelMill.IronTeeth'), 'SteelMill.IronTeeth site (flat): 0 checked sites'),
    ('outcrop over water', outcrop_in_water, 'SandstoneOutcrop@'),
    ('site of a building that needs none', bad_template, 'MapError'),
]

failures = 0
for name, mutate, expected in CASES:
    v = copy.deepcopy(base)
    v['id'] = 'neg-' + name.replace(' ', '-')
    mutate(v)
    path = SP / 'neg' / f'{v["id"]}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(v), encoding='utf-8')
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            results = m.build([path], catalog, out_dir=SP / 'neg', write=True)
        errors = results[0][2]
        hit = [e for e in errors if expected in e]
        status = 'caught' if hit else 'MISSED'
        detail = hit[0] if hit else (errors[:3] if errors else 'no errors')
    except m.MapError as error:
        status = 'caught' if expected == 'MapError' else 'MISSED'
        detail = f'MapError: {error}'
    failures += status != 'caught'
    print(f'{status:7} {name}: {str(detail)[:170]}')
print(f'{len(CASES) - failures}/{len(CASES)} faults caught')
sys.exit(1 if failures else 0)
