"""Create the explicit small disposable map for real-worker acceptance."""
import json
import zipfile
from pathlib import Path
import dev_environment as dev


def main():
    maps = Path(dev.get('timberbornDocuments')) / 'Maps'
    source = maps / 'Deep Frontier - All Buildings Test.timber'
    target = maps / 'Moddable Fluids Worker Fixture.timber'
    with zipfile.ZipFile(source) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    world = json.loads(entries['world.json'])
    specs = json.loads((dev.ROOT / 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/Configurations/MapSize.blueprint.json').read_text())['MapSizeSpec']
    terrain_layers = specs['MaxGameTerrainHeight'] + 1
    total_layers = terrain_layers + specs['MaxHeightAboveTerrain']
    cells = 32 * 32
    state = world['Singletons']
    state['MapSize'] = {'Size': {'X': 32, 'Y': 32}, 'MapHeight': {'X': terrain_layers, 'Y': total_layers}}
    state['TerrainMap']['Voxels']['Array'] = ' '.join(['1'] * (3*cells) + ['0'] * ((terrain_layers-3)*cells))
    for singleton, size_key, fields, value in [
        ('WaterMapNew', 'Levels', ['WaterColumns', 'ColumnOutflows'], '0'),
        ('WaterEvaporationMap', 'Levels', ['EvaporationModifiers'], '1'),
        ('SoilMoistureSimulator', 'Size', ['MoistureLevels'], '0'),
        ('SoilContaminationSimulator', 'Size', ['ContaminationCandidates', 'ContaminationLevels'], '0')
    ]:
        state[singleton][size_key] = 1
        for field in fields:
            state[singleton][field]['Array'] = ' '.join([value] * cells)
    starts = [entity for entity in world['Entities'] if entity['Template'] == 'StartingLocation']
    if len(starts) != 1:
        raise ValueError('The fixture source must have exactly one native StartingLocation')
    starts[0]['Components']['BlockObject']['Coordinates'] = {'X': 16, 'Y': 16, 'Z': 3}
    world['Entities'] = starts
    metadata = json.loads(entries['map_metadata.json'])
    metadata.update(Width=32, Height=32, MapNameLocKey='', MapDescriptionLocKey='',
                    MapDescription='Disposable Moddable Fluids real-worker fixture, flat and dry at height 3.', IsRecommended=False, IsDev=False)
    entries['world.json'] = json.dumps(world, separators=(',', ':')).encode()
    entries['map_metadata.json'] = json.dumps(metadata, separators=(',', ':')).encode()
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    print(f'Created {target}: 32x32; native terrain/total height {terrain_layers}/{total_layers}; one starting location')


if __name__ == '__main__':
    main()
