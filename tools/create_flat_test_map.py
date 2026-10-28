"""Flat, dry test map for the all-buildings acceptance (tools/start_all_buildings.ps1).

None of the Deep Frontier maps has a dry pad of even 48x40 within reach of its starting
location (measured 2026-10-24 with prepare_deep_frontier_map.MapModel), so the harness needs its
own map. This writes '<Maps>/Deep Frontier - All Buildings Test.timber' from the Deep Frontier
Plains map file: the same size and MapHeight, terrain solid to height GROUND everywhere, no water,
moisture, soil contamination or evaporation modifiers, and only the StartingLocation, moved to the
map centre. Every other singleton and the map format stay as the source wrote them.

    python tools/create_flat_test_map.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_deep_frontier_map as maps  # noqa: E402

MAPS = Path.home() / 'Documents' / 'Timberborn' / 'Maps'
SOURCE = MAPS / 'Deep Frontier - Plains.timber'
TARGET = MAPS / 'Deep Frontier - All Buildings Test.timber'
GROUND = 3


def zeros(spec, field, value='0'):
    count = len(spec[field]['Array'].split(' '))
    spec[field]['Array'] = ' '.join([value] * count)


def flat_map():
    """The flat, dry map entries (not written): (entries, world, metadata, (sx, sy, layers))."""
    entries = maps.read_zip_bytes(SOURCE.read_bytes())
    world = json.loads(entries['world.json'])
    singletons = world['Singletons']
    sx, sy = singletons['MapSize']['Size']['X'], singletons['MapSize']['Size']['Y']
    voxels = singletons['TerrainMap']['Voxels']['Array'].split(' ')
    cells = sx * sy
    if len(voxels) % cells:
        raise SystemExit(f'Voxel count {len(voxels)} is not a multiple of {cells}')
    layers = len(voxels) // cells
    if layers <= GROUND:
        raise SystemExit(f'Map stores only {layers} terrain layers')
    singletons['TerrainMap']['Voxels']['Array'] = ' '.join(['1'] * (GROUND * cells) + ['0'] * ((layers - GROUND) * cells))
    zeros(singletons['WaterMapNew'], 'WaterColumns')
    zeros(singletons['WaterMapNew'], 'ColumnOutflows')
    zeros(singletons['SoilMoistureSimulator'], 'MoistureLevels')
    zeros(singletons['SoilContaminationSimulator'], 'ContaminationCandidates')
    zeros(singletons['SoilContaminationSimulator'], 'ContaminationLevels')
    zeros(singletons['WaterEvaporationMap'], 'EvaporationModifiers', '1')
    starts = [e for e in world['Entities'] if e['Template'] == 'StartingLocation']
    if len(starts) != 1:
        raise SystemExit(f'Expected one StartingLocation, found {len(starts)}')
    start = starts[0]
    start['Components']['BlockObject']['Coordinates'] = {'X': sx // 2, 'Y': sy // 2, 'Z': GROUND}
    world['Entities'] = [start]
    metadata = json.loads(entries['map_metadata.json'])
    metadata['IsRecommended'] = False
    metadata['IsDev'] = False
    return entries, world, metadata, (sx, sy, layers)


def store(entries, world, metadata, target):
    entries['world.json'] = json.dumps(world, separators=(',', ':')).encode('utf-8')
    entries['map_metadata.json'] = json.dumps(metadata, separators=(',', ':')).encode('utf-8')
    maps.write_timber(entries, target)


def main():
    entries, world, metadata, (sx, sy, layers) = flat_map()
    metadata['MapDescription'] = ('Deep Frontier all-buildings acceptance map: flat and dry at height 3, no water or '
                                  'natural resources. Written by tools/create_flat_test_map.py from the Deep Frontier '
                                  'Plains map; for tools/start_all_buildings.ps1 only.')
    store(entries, world, metadata, TARGET)
    print(f'Wrote {TARGET}: {sx}x{sy}, {layers} terrain layers stored, solid to {GROUND}, start at ({sx // 2},{sy // 2},{GROUND})')


if __name__ == '__main__':
    main()
