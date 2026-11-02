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
    # The hatchery takes the coal plant's dry, flat site, far from any water (a shift of a few cells
    # along the shore keeps the 5x5 pens in water).
    s = site(v, 'FishHatchery.IronTeeth')
    other = site(v, 'CoalPowerPlant.IronTeeth')
    s.update(x=other['x'], y=other['y'], z=other['z'])
    drop_sites(v, 'CoalPowerPlant.IronTeeth')


def quarry_wrong_seam(v):
    site(v, 'SandstoneQuarry.IronTeeth')['understructure'] = site(v, 'LimestoneQuarry.IronTeeth')['understructure']


def overlap(v):
    a, b = site(v, 'SteelMill.IronTeeth'), site(v, 'DeepProcessor.IronTeeth')
    b.update(x=a['x'] + 2, y=a['y'] + 2, z=a['z'], orientation=a['orientation'])


def footprint_corner(s):
    cells = m.building_blocks(catalog, s['template']).columns((s['x'], s['y'], s['z']), s['orientation'])
    return min(x for x, _ in cells), min(y for _, y in cells)


def open_margin(v):
    # The coal plant's top row (blueprint depth, Cw0) lands in the row just south of the steel mill:
    # its open S margin.
    mill = site(v, 'SteelMill.IronTeeth')
    plant = site(v, 'CoalPowerPlant.IronTeeth')
    depth = catalog.get(plant['template'])['BlockObjectSpec']['Size']['Y']
    x, y = footprint_corner(mill)
    plant.update(x=x, y=y - depth, z=mill['z'], orientation='Cw0')


def dynamite_outside(v):
    # Plains' sites list no Dynamite any more; a charge listed outside a site's footprint must
    # still fail.
    s = site(v, 'RadioactiveSludgeRecoveryPump.IronTeeth')
    s['dynamite'] = [[s['x'] - 10, s['y'] - 10, 1]]


def poor_sources(v):
    for p in v['placements']:
        if p['template'] == 'DeepOreSource':
            p['amount'] = 100   # 300 in all; the buildings up to the Deep Mine need about 1,400


def dry_dam(v):
    s = site(v, 'ReinforcedHydroTurbine.IronTeeth')
    s['x'] += 8


def pit_far(v):
    # The pit takes the corner of the Electrolysis Plant's footprint (flat, far from the outcrops).
    pit = site(v, 'SandstonePit.IronTeeth')
    other = site(v, 'ElectrolysisPlant.IronTeeth')
    x, y = footprint_corner(other)
    pit.update(x=x, y=y, z=other['z'], orientation='Cw0')
    drop_sites(v, 'ElectrolysisPlant.IronTeeth')


def platforms_miscounted(v):
    # A flat site on level ground declares platform blocks it does not need.
    site(v, 'SteelMill.IronTeeth')['platformBlocks'] = 5


def raised_below_terrain(v):
    # A raised site may stand above its terrain, never inside it.
    s = site(v, 'SteelMill.IronTeeth')
    s['z'] -= 1
    s['platformBlocks'] = 1


def platforms_under_quarry(v):
    # Understructure buildings stand on their real ground deposit: no platform key.
    site(v, 'LimestoneQuarry.IronTeeth')['platformBlocks'] = 3


def vanilla_object_placed(v):
    # The setup adds Deep Frontier's own map objects only, never base-game content (user 2026-11-01).
    s = site(v, 'SteelMill.IronTeeth')
    v['placements'].append({'template': 'UndergroundRuins', 'label': 'ruins', 'x': s['x'], 'y': s['y'] - 6, 'z': s['z']})


def player_work_for_met_item(v):
    # Plains has shore fishing banks: declaring them player work is stale data.
    v['playerWork'] = [{'item': 'shore fishing banks (first FreshFish)', 'reason': 'dam a river'}]


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
    ('platform blocks miscounted', platforms_miscounted, 'platform blocks 0 != declared 5'),
    ('raised site below its terrain', raised_below_terrain, 'is above the raised level'),
    ('platforms under a quarry', platforms_under_quarry, 'MapError'),
    ('vanilla map object placed', vanilla_object_placed, 'MapError'),
    ('player work declared for a met item', player_work_for_met_item, "player-work item 'shore fishing banks (first FreshFish)' is met"),
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
