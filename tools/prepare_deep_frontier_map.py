"""Prepare Deep Frontier variants of existing Timberborn maps.

A variant is described by tools/map_variants/<id>.json: the source map, the
output name/description, the height (Map Transformer MapHeight), explicit
map-object placements (any template of the mod's MapEditor Common collection:
veins, ore sources, outcrops, seams, Human Record Caches, the hard variant's
spring) and a checked site for every building of the Iron Teeth building
collection that needs one (site_rule). The script copies the source map,
resizes its height as Map Transformer does, appends the placements, writes the
.timber and validates the result statically against the source terrain, water
and entities, the mod's collections and the full-loop requirements
(loop_coverage; docs/maps.md "Full game loop"). Nothing here normalizes or
repairs inputs: an invalid placement, an unknown template or a changed source
map is an error.

Commands (run from any directory):
  analyze  <source> [--png PATH]   terrain/water/site survey of a source map
  suggest  <source> [--png PATH]   candidate vein/source/reactor/pad sites
  plan     <variant.json> --out P  propose the placements and sites a variant
                                   still lacks for the full loop (for review)
  build    <variant.json>...       write the variant(s) and validate them
  validate <variant.json>...       validate already written variant(s)

<source> is either builtin:<Name> (a built-in map, read from the game's
resources.assets by its MapMetadata.<Name>.Name key) or a .timber path.

Format facts used here (Timberborn 1.1.2.8, decompiled):
- MapSize saves only Size; without a "MapHeight" {X: terrain, Y: total} key
  the height comes from the global MapSizeSpec (23 terrain / 33 total layers).
  Map Transformer 11.0.0, a required mod, reads the key (docs/map-height.md);
  the variants carry {46, 66}.
- TerrainMap.Voxels and WaterMapNew.WaterColumns are packed z-major:
  index = level * (X * Y) + y * X + x.
- WaterColumn entries are "0" or "depth:contamination:overflow:floor:old".
- BlockObject blocks: index = (z * Size.y + y) * Size.x + x; positioned
  cell = Orientation(Flip(local)) + Coordinates; Cw90 maps (x, y)->(y, -x).
- On load, every BlockObject must pass BlockValidator and the
  IBlockObjectValidators (occupied z < total height, matter below,
  ContinuousTerrainConstraint) or it is deleted.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import mmap
import struct
import sys
import uuid
import zipfile
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import dev_environment as dev
GAME = dev.game_root()
RESOURCES_ASSETS = GAME / 'Timberborn_Data/resources.assets'
BLUEPRINTS_ZIP = GAME / 'Timberborn_Data/StreamingAssets/Modding/Blueprints.zip'
MOD_DATA = ROOT / 'src/DeepFrontier/Data'
MAP_EDITOR_COLLECTION = MOD_DATA / 'TemplateCollections/TemplateCollection.MapEditor.Common.blueprint.json'
MOD_MANIFEST = ROOT / 'src/DeepFrontier/manifest.json'
DEPENDENCY_MANIFESTS = ROOT / 'tools/installed_dependency_manifests_1_1.json'
ENTRY_ORDER = ['map_metadata.json', 'map_thumbnail.jpg', 'version.txt', 'world.json']

# Every building of the mod's Iron Teeth building collection is classified by
# its blueprint (site_rule); sizes, entrances and top occupied layers are read
# from the blueprints, not repeated here.
BUILDING_COLLECTION = MOD_DATA / 'TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json'
NARRATIVE_SETTINGS = MOD_DATA / 'Configurations/DeepFrontierNarrative.blueprint.json'
LOOP_REQUIREMENTS = ROOT / 'tools/map_loop_requirements.json'
GATHERER_FLAG_PATCH = MOD_DATA / 'Buildings/Food/GathererFlag/GathererFlag.IronTeeth.blueprint.json'
ORIENTATIONS = ['Cw0', 'Cw90', 'Cw180', 'Cw270']
# NavigationDistance.ResourceBuildings (Timberborn.Navigation.dll, 1.1.2.8) = 20:
# BuildingTerrainRange of a yield-removing building (the Sandstone/Limestone
# Pit's InRangeYielders) holds the terrain nodes within this distance of its
# access. The check below counts 4-neighbour steps over same-level dry ground,
# which is never shorter than the native path.
RESOURCE_BUILDING_RANGE = 20
# ContaminationBlockableBuilding.MaximumWaterContamination (Timberborn.WaterContaminationBuildings.dll,
# 1.1.2.8) = 0.05: a building whose WaterDepthWorkCells sample exceeds it (plus a 0.005 band) is blocked.
MAX_WORK_CELL_CONTAMINATION = 0.05
# Human Record Cache (docs/story.md): tools/narrative_content.mjs clones the
# vanilla MediumRelic blueprint (CACHE.template) and keeps its BlockObjectSpec.
RECORD_CACHE_TEMPLATE = 'HumanRecordCache'
RECORD_CACHE_CLONED_FROM = 'MediumRelic'
VANILLA_RESOURCES = ROOT / 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources'


class MapError(Exception):
    pass


def fail(message):
    raise MapError(message)


# ---------------------------------------------------------------- sources

def read_zip_bytes(data):
    archive = zipfile.ZipFile(io.BytesIO(data))
    names = archive.namelist()
    if sorted(names) != sorted(ENTRY_ORDER):
        fail(f'Unexpected .timber entries {names}; expected {ENTRY_ORDER}')
    return {name: archive.read(name) for name in names}


def builtin_map_bytes(name):
    """Return the zip bytes of a built-in map stored as BinaryData in resources.assets."""
    key = f'MapMetadata.{name}.Name'
    matches = []
    with open(RESOURCES_ASSETS, 'rb') as handle:
        view = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
        position = view.find(b'PK\x05\x06')
        while position != -1:
            _, _, _, _, cd_size, cd_offset, comment = struct.unpack('<HHHHIIH', view[position + 4:position + 22])
            start = position - cd_size - cd_offset
            if start >= 4 and view[start:start + 4] == b'PK\x03\x04':
                length = struct.unpack('<i', view[start - 4:start])[0]
                data = bytes(view[start:position + 22 + comment])
                if length != len(data):
                    fail(f'BinaryData length {length} does not match zip size {len(data)} at {start}')
                try:
                    metadata = json.loads(zipfile.ZipFile(io.BytesIO(data)).read('map_metadata.json'))
                except (KeyError, zipfile.BadZipFile):
                    metadata = None
                if metadata and metadata.get('MapNameLocKey') == key:
                    matches.append(data)
            position = view.find(b'PK\x05\x06', position + 1)
    if len(matches) != 1:
        fail(f'Expected one built-in map with {key} in {RESOURCES_ASSETS}, found {len(matches)}')
    return matches[0]


def load_source(source):
    if source.startswith('builtin:'):
        data = builtin_map_bytes(source.split(':', 1)[1])
    else:
        path = Path(source)
        if not path.is_file():
            fail(f'Source map {path} does not exist')
        data = path.read_bytes()
    return data, read_zip_bytes(data)


# Map Transformer 11.0.0 (Workshop 3798650616, Id MapTransformer). Its
# MapSizePatches postfix on MapSize.Load replaces the global MapSizeSpec with
# MaxGameTerrainHeight = X - 1, MaxHeightAboveTerrain = Y - X when the MapSize
# singleton carries MapHeight {X: terrain layers, Y: total layers}; its Save
# postfix writes the key on every save made while it is enabled.
MAP_TRANSFORMER_MAX_TOTAL = 254   # WaterColumn.Floor/Ceiling are bytes; ceiling = total + 1


def resize_height(entries, terrain_layers, total_height):
    """Reproduce Map Transformer's "Resize Map Height" (MapOp.ResizeHeight) on a packed map.

    MapIndexCopy.CopyTerrainVoxels keeps every voxel at its z (layers above the
    old terrain height stay empty, and the new top layer is never filled), and
    the water, moisture, contamination and evaporation components copy column
    slot k to slot k, so a ResizeHeight that keeps all terrain only appends empty
    voxel layers and adds the MapHeight key. Everything else stays byte-identical.
    """
    raw = entries['world.json']
    world = json.loads(raw)
    map_size = world['Singletons']['MapSize']
    if set(map_size) != {'Size'}:
        fail(f'resize_height expects a source without MapHeight, found {sorted(map_size)}')
    sx, sy = map_size['Size']['X'], map_size['Size']['Y']
    cells = sx * sy
    voxels = world['Singletons']['TerrainMap']['Voxels']['Array']
    stored = (voxels.count(' ') + 1) // cells
    if (voxels.count(' ') + 1) != stored * cells:
        fail('Voxel count is not a whole number of layers')
    if not stored <= terrain_layers <= total_height <= MAP_TRANSFORMER_MAX_TOTAL:
        fail(f'Need {stored} <= terrain {terrain_layers} <= total {total_height} <= {MAP_TRANSFORMER_MAX_TOTAL}')
    size_bytes = json.dumps({'MapSize': map_size}, separators=(',', ':')).encode()[1:-2] + b'}'
    if raw.count(size_bytes) != 1:
        fail(f'MapSize singleton {size_bytes!r} not found exactly once')
    height_bytes = size_bytes[:-1] + b',"MapHeight":{"X":%d,"Y":%d}}' % (terrain_layers, total_height)
    marker = b'"TerrainMap":{"Voxels":{"Array":"'
    if raw.count(marker) != 1:
        fail('TerrainMap.Voxels not found exactly once')
    end = raw.index(b'"', raw.index(marker) + len(marker))
    padding = b' 0' * ((terrain_layers - stored) * cells)
    resized = raw[:end] + padding + raw[end:]
    resized = resized.replace(size_bytes, height_bytes, 1)
    out = dict(entries)
    out['world.json'] = resized
    return out


# ------------------------------------------------------------- blueprints

def water_per_strength_hour():
    # Native water-source strength is water per simulated second: a strength-1
    # source adds TickIntervalInSeconds * ConfiguredDayLengthInTicks / 24 water
    # per game hour (tools/radiation_content.mjs waterPerStrengthHour).
    tick = read_json(VANILLA_RESOURCES / 'Configurations/TickTime.blueprint.json')['TickTimeSpec']['TickIntervalInSeconds']
    ticks = read_json(VANILLA_RESOURCES / 'Configurations/DayNightCycle.blueprint.json')['DayNightCycleSpec']['ConfiguredDayLengthInTicks']
    if not (tick > 0 and ticks > 0):
        fail('Vanilla TickTimeSpec / DayNightCycleSpec values are missing')
    return tick * ticks / 24


def read_json(path_or_bytes):
    raw = path_or_bytes if isinstance(path_or_bytes, bytes) else Path(path_or_bytes).read_bytes()
    return json.loads(raw.decode('utf-8-sig'))


class TemplateCatalog:
    """TemplateName -> blueprint, from the game's Blueprints.zip and the mod Data."""

    def __init__(self):
        self.blueprints = {}
        self.origin = {}
        with zipfile.ZipFile(BLUEPRINTS_ZIP) as archive:
            for name in archive.namelist():
                if name.endswith('.blueprint.json'):
                    self._add(read_json(archive.read(name)), 'vanilla:' + name)
        for path in MOD_DATA.rglob('*.blueprint.json'):
            self._add(read_json(path), 'mod:' + path.relative_to(MOD_DATA).as_posix())
        self.map_editor_common = self._map_editor_collection()
        self.building_collection = self._building_collection()

    def _add(self, blueprint, origin):
        name = blueprint.get('TemplateSpec', {}).get('TemplateName')
        if not name:
            return
        if name in self.blueprints and origin.startswith('vanilla:'):
            fail(f'Duplicate vanilla template {name}: {self.origin[name]} and {origin}')
        if name in self.blueprints:
            fail(f'Mod template {name} ({origin}) collides with {self.origin[name]}')
        self.blueprints[name] = blueprint
        self.origin[name] = origin

    @staticmethod
    def _map_editor_collection():
        spec = read_json(MAP_EDITOR_COLLECTION)['TemplateCollectionSpec']
        if spec['CollectionId'] != 'Common':
            fail(f'{MAP_EDITOR_COLLECTION} is not the Common collection')
        result = {}
        for entry in spec['Blueprints#append']:
            path = MOD_DATA / (entry + '.json')
            if not path.is_file():
                fail(f'MapEditor collection entry {entry} has no blueprint file {path}')
            result[read_json(path)['TemplateSpec']['TemplateName']] = entry
        return result

    @staticmethod
    def _building_collection():
        """TemplateName -> collection entry of the mod's Iron Teeth building collection."""
        spec = read_json(BUILDING_COLLECTION)['TemplateCollectionSpec']
        if spec['CollectionId'] != 'Buildings.IronTeeth':
            fail(f'{BUILDING_COLLECTION} is not the Buildings.IronTeeth collection')
        result = {}
        for entry in spec['Blueprints#append']:
            path = MOD_DATA / (entry + '.json')
            if not path.is_file():
                fail(f'Building collection entry {entry} has no blueprint file {path}')
            result[read_json(path)['TemplateSpec']['TemplateName']] = entry
        return result

    def get(self, name):
        if name not in self.blueprints:
            fail(f'Template {name} is not defined by the game or the mod')
        return self.blueprints[name]

    def is_natural_resource(self, name):
        return self.origin[name].startswith('vanilla:NaturalResources/')


class Blocks:
    """BlockObjectSpec blocks with the game's positioning rules."""

    def __init__(self, spec):
        self.size = (spec['Size']['X'], spec['Size']['Y'], spec['Size']['Z'])
        self.base_z = spec['BaseZ']
        self.flippable = spec['Flippable']
        self.blocks = spec['Blocks']
        self.entrance = spec['Entrance']
        sx, sy, sz = self.size
        if len(self.blocks) != sx * sy * sz:
            fail(f'Block count {len(self.blocks)} does not match size {self.size}')
        self._cache = {}

    def _local(self, orientation, flipped):
        """Positioned blocks at the origin; positions translate with Coordinates."""
        key = (orientation, flipped)
        if key not in self._cache:
            blocks = list(self.positioned((0, 0, 0), orientation, flipped))
            self._cache[key] = (frozenset((x, y) for x, y, _, _ in blocks),
                                [(x, y, z, b) for x, y, z, b in blocks if occupied(b)])
        return self._cache[key]

    def columns(self, coordinates, orientation='Cw0', flipped=False):
        """(x, y) of every block, occupied or not."""
        cx, cy = coordinates[0], coordinates[1]
        return {(x + cx, y + cy) for x, y in self._local(orientation, flipped)[0]}

    def occupied_cells(self, coordinates, orientation='Cw0', flipped=False):
        """(x, y, z) of every occupied block."""
        cx, cy, cz = coordinates
        return [(x + cx, y + cy, z + cz) for x, y, z, _ in self._local(orientation, flipped)[1]]

    def occupied_blocks(self, coordinates, orientation='Cw0', flipped=False):
        cx, cy, cz = coordinates
        return [(x + cx, y + cy, z + cz, b) for x, y, z, b in self._local(orientation, flipped)[1]]

    def block(self, x, y, z):
        sx, sy, _ = self.size
        return self.blocks[(z * sy + y) * sx + x]

    def transform(self, local, coordinates, orientation, flipped):
        x, y = local
        if flipped:
            x = self.size[0] - x - 1
        if orientation == 'Cw0':
            rx, ry = x, y
        elif orientation == 'Cw90':
            rx, ry = y, -x
        elif orientation == 'Cw180':
            rx, ry = -x, -y
        elif orientation == 'Cw270':
            rx, ry = -y, x
        else:
            fail(f'Unknown orientation {orientation}')
        return rx + coordinates[0], ry + coordinates[1]

    def positioned(self, coordinates, orientation='Cw0', flipped=False):
        """Yield (x, y, z, block) for every local block; z includes Coordinates.z - BaseZ."""
        if flipped and not self.flippable:
            fail('Flipped placement of a non-flippable object')
        sx, sy, sz = self.size
        base = coordinates[2] - self.base_z
        for z in range(sz):
            for y in range(sy):
                for x in range(sx):
                    wx, wy = self.transform((x, y), coordinates, orientation, flipped)
                    yield wx, wy, base + z, self.block(x, y, z)

    def entrance_cell(self, coordinates, orientation='Cw0', flipped=False):
        if not self.entrance['HasEntrance']:
            return None
        c = self.entrance['Coordinates']
        wx, wy = self.transform((c['X'], c['Y']), coordinates, orientation, flipped)
        return wx, wy, coordinates[2] - self.base_z + c['Z']

    def top_occupied_layer(self):
        if 'top' in self._cache:
            return self._cache['top']
        sx, sy, sz = self.size
        top = -1
        for z in range(sz):
            for y in range(sy):
                for x in range(sx):
                    if self.block(x, y, z)['Occupations'] != 'None':
                        top = z
        self._cache['top'] = top
        return top


def occupied(block):
    return block['Occupations'] != 'None'


# --------------------------------------------------------------- map model

def map_size_spec():
    with zipfile.ZipFile(BLUEPRINTS_ZIP) as archive:
        spec = read_json(archive.read('Configurations/MapSize.blueprint.json'))['MapSizeSpec']
    return spec


class MapModel:
    def __init__(self, entries, catalog):
        self.entries = entries
        self.catalog = catalog
        self.world = json.loads(entries['world.json'])
        self.metadata = json.loads(entries['map_metadata.json'])
        self.version = entries['version.txt'].decode('utf-8').strip()
        singletons = self.world['Singletons']
        size = singletons['MapSize']['Size']
        self.sx, self.sy = size['X'], size['Y']
        spec = map_size_spec()
        if 'MapHeight' in singletons['MapSize']:
            height = singletons['MapSize']['MapHeight']
            self.terrain_layers, self.total_height = height['X'], height['Y']
            self.height_source = 'MapHeight key (Map Transformer 11.0.0, a required mod)'
            if (self.terrain_layers, self.total_height) != (spec['MaxGameTerrainHeight'] + 1,
                                                             spec['MaxGameTerrainHeight'] + 1 + spec['MaxHeightAboveTerrain']):
                self.height_source += ' - NON-VANILLA: requires Map Transformer at play time'
        else:
            self.terrain_layers = spec['MaxGameTerrainHeight'] + 1
            self.total_height = self.terrain_layers + spec['MaxHeightAboveTerrain']
            self.height_source = 'vanilla MapSizeSpec (Configurations/MapSize.blueprint.json)'
        self._terrain()
        self._water()
        self._entities()

    def _terrain(self):
        values = self.world['Singletons']['TerrainMap']['Voxels']['Array'].split(' ')
        cells = self.sx * self.sy
        if len(values) % cells:
            fail(f'Voxel count {len(values)} is not a multiple of {cells}')
        layers = len(values) // cells
        if layers > self.terrain_layers:
            fail(f'Map stores {layers} terrain layers but the effective terrain height is {self.terrain_layers}')
        solid = np.array(values, dtype=np.uint8).reshape(layers, self.sy, self.sx).astype(bool)
        self.solid = solid
        self.layers = layers
        any_solid = solid.any(axis=0)
        top = layers - np.argmax(solid[::-1], axis=0)
        self.height = np.where(any_solid, top, 0).astype(np.int32)
        self.contiguous = solid.sum(axis=0) == self.height

    def _water(self):
        water = self.world['Singletons']['WaterMapNew']
        levels = water['Levels']
        values = water['WaterColumns']['Array'].split(' ')
        cells = self.sx * self.sy
        if len(values) != levels * cells:
            fail(f'Water column count {len(values)} != {levels} * {cells}')
        depth = np.zeros((levels, self.sy, self.sx), dtype=np.float32)
        floor = np.full((levels, self.sy, self.sx), -1, dtype=np.int32)
        contamination = np.zeros((levels, self.sy, self.sx), dtype=np.float32)
        for index, value in enumerate(values):
            if value == '0':
                continue
            parts = value.split(':')
            level, rest = divmod(index, cells)
            y, x = divmod(rest, self.sx)
            depth[level, y, x] = float(parts[0])
            contamination[level, y, x] = float(parts[1])
            floor[level, y, x] = int(parts[3]) if len(parts) >= 4 else 0
        self.water_depth_levels, self.water_floor_levels = depth, floor
        surface_depth = np.zeros((self.sy, self.sx), dtype=np.float32)
        surface_contamination = np.zeros((self.sy, self.sx), dtype=np.float32)
        any_depth = np.zeros((self.sy, self.sx), dtype=np.float32)
        for level in range(levels):
            top = floor[level] == self.height
            surface_depth = np.where(top, depth[level], surface_depth)
            surface_contamination = np.where(top, contamination[level], surface_contamination)
            any_depth = np.maximum(any_depth, depth[level])
        self.water_depth = surface_depth
        self.water_contamination = surface_contamination
        self.water_any = any_depth
        self.water_surface = self.height + surface_depth

    def water_at(self, x, y, z):
        """Water depth of the column whose floor is at or below z and whose surface is above z."""
        for level in range(self.water_depth_levels.shape[0]):
            floor = self.water_floor_levels[level, y, x]
            depth = self.water_depth_levels[level, y, x]
            if floor >= 0 and depth > 0 and floor <= z < floor + depth:
                return float(depth)
        return 0.0

    def _entities(self):
        self.objects = []
        self.cells = {}
        self.bottom_cells = {}
        self.start = None
        for index, entity in enumerate(self.world['Entities']):
            components = entity['Components']
            if 'BlockObject' not in components:
                continue
            block_object = components['BlockObject']
            c = block_object['Coordinates']
            coordinates = (c['X'], c['Y'], c['Z'])
            orientation = block_object.get('Orientation', 'Cw0')
            flipped = bool(block_object.get('Flipped', False))
            template = entity['Template']
            blueprint = self.catalog.get(template)
            blocks = Blocks(blueprint['BlockObjectSpec'])
            natural = self.catalog.is_natural_resource(template)
            record = {'index': index, 'template': template, 'coordinates': coordinates,
                      'orientation': orientation, 'flipped': flipped and blocks.flippable,
                      'natural': natural, 'id': entity['Id']}
            self.objects.append(record)
            for x, y, z, block in blocks.positioned(coordinates, orientation, record['flipped']):
                if occupied(block) or block['Underground']:
                    self.cells.setdefault((x, y, z), []).append(record)
                if block['OccupyAllBelow']:
                    for bz in range(z - 1, -1, -1):
                        self.bottom_cells.setdefault((x, y, bz), []).append(record)
            if template == 'StartingLocation':
                if self.start is not None:
                    fail('More than one StartingLocation')
                self.start = coordinates
                self.start_cells = footprint(blocks, coordinates, orientation, record['flipped'])
        if self.start is None:
            fail('Map has no StartingLocation')
        self.hard_mask = np.zeros((self.sy, self.sx), dtype=bool)
        self.natural_mask = np.zeros((self.sy, self.sx), dtype=bool)
        for (x, y, z), records in self.cells.items():
            if not (0 <= x < self.sx and 0 <= y < self.sy):
                continue
            for record in records:
                if record['natural']:
                    self.natural_mask[y, x] = True
                else:
                    self.hard_mask[y, x] = True
        for (x, y, z), records in self.bottom_cells.items():
            if 0 <= x < self.sx and 0 <= y < self.sy:
                self.hard_mask[y, x] = True

    # ---- derived grids
    def dry(self):
        return (self.water_any == 0)

    def distance_from(self, sources, passable=None):
        """4-neighbour BFS distance from sources, optionally limited to passable cells."""
        distance = np.full((self.sy, self.sx), -1, dtype=np.int32)
        queue = deque()
        for x, y in sources:
            distance[y, x] = 0
            queue.append((x, y))
        while queue:
            x, y = queue.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if not (0 <= nx < self.sx and 0 <= ny < self.sy) or distance[ny, nx] >= 0:
                    continue
                if passable is not None and not passable[ny, nx]:
                    continue
                distance[ny, nx] = distance[y, x] + 1
                queue.append((nx, ny))
        return distance

    def walk_distance(self):
        """Route length from the starting location (see route())."""
        return self.route()[0]

    def route(self, bridge_cost=12):
        """Cheapest route from the starting location over cells without hard objects.

        Dry cells cost 1; a water cell costs bridge_cost, standing for a bridge,
        dam or levee the player must build. Height steps are free (stairs and
        ramps). Returns (route length in cells, water cells crossed); both are
        -1 where no route exists."""
        if not hasattr(self, '_route'):
            import heapq
            passable = ~self.hard_mask
            wet = self.water_any > 0
            cost = np.full((self.sy, self.sx), np.iinfo(np.int32).max, dtype=np.int64)
            length = np.full((self.sy, self.sx), -1, dtype=np.int32)
            bridges = np.full((self.sy, self.sx), -1, dtype=np.int32)
            heap = []
            for x, y in ring(self.start_cells, 1):
                if 0 <= x < self.sx and 0 <= y < self.sy and passable[y, x] and not wet[y, x]:
                    cost[y, x] = 0
                    length[y, x] = 0
                    bridges[y, x] = 0
                    heap.append((0, x, y))
            if not heap:
                fail('No dry free cell next to the StartingLocation')
            heapq.heapify(heap)
            while heap:
                c, x, y = heapq.heappop(heap)
                if c > cost[y, x]:
                    continue
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if not (0 <= nx < self.sx and 0 <= ny < self.sy) or not passable[ny, nx]:
                        continue
                    step = bridge_cost if wet[ny, nx] else 1
                    if c + step < cost[ny, nx]:
                        cost[ny, nx] = c + step
                        length[ny, nx] = length[y, x] + 1
                        bridges[ny, nx] = bridges[y, x] + (1 if wet[ny, nx] else 0)
                        heapq.heappush(heap, (c + step, nx, ny))
            self._route = (length, bridges)
        return self._route

    def water_distance(self, badwater=False):
        """Distance to the nearest wet surface cell; clean is contamination < 0.5.

        Built-in maps store shallow initial water (median depth about 0.3), so
        any wet cell marks the river or lake bed."""
        key = ('_wd', badwater)
        if key not in self.__dict__:
            wet = self.water_depth > 0
            if badwater:
                mask = wet & (self.water_contamination >= 0.5)
            else:
                mask = wet & (self.water_contamination < 0.5)
            ys, xs = np.nonzero(mask)
            self.__dict__[key] = self.distance_from(list(zip(xs.tolist(), ys.tolist())))
        return self.__dict__[key]


# ------------------------------------------------------- placement checks

def check_object(model, blocks, coordinates, orientation, flipped, others, template_spec=None):
    """Return a list of problems for placing blocks at coordinates in model."""
    problems = []
    continuous = template_spec is not None and 'ContinuousTerrainConstraintSpec' in template_spec
    for x, y, z, block in blocks.positioned(coordinates, orientation, flipped):
        if not (0 <= x < model.sx and 0 <= y < model.sy):
            if occupied(block):
                problems.append(f'block ({x},{y},{z}) outside the map')
            continue
        if occupied(block):
            if z >= model.total_height:
                problems.append(f'block ({x},{y},{z}) above total height {model.total_height}')
            if 0 <= z < model.layers and model.solid[z, y, x]:
                problems.append(f'block ({x},{y},{z}) inside terrain')
            if z < 0:
                problems.append(f'block ({x},{y},{z}) below the map')
            depth = model.water_at(x, y, z)
            if depth > 0:
                problems.append(f'block ({x},{y},{z}) is in water (depth {depth:.2f})')
            for record in model.cells.get((x, y, z), []) + model.bottom_cells.get((x, y, z), []):
                problems.append(f'block ({x},{y},{z}) overlaps {record["template"]} at {record["coordinates"]}')
            for other in others.get((x, y, z), []):
                problems.append(f'block ({x},{y},{z}) overlaps placed {other}')
        matter = block['MatterBelow']
        if matter in ('Ground', 'GroundOrStackable'):
            below = z - 1
            if not (0 <= below < model.layers and model.solid[below, y, x]):
                problems.append(f'block ({x},{y},{z}) needs ground below ({matter})')
        if block['OccupyAllBelow']:
            for bz in range(z - 1, -1, -1):
                for record in model.cells.get((x, y, bz), []):
                    problems.append(f'bottom block ({x},{y},{bz}) overlaps {record["template"]} at {record["coordinates"]}')
                for other in others.get((x, y, bz), []):
                    problems.append(f'bottom block ({x},{y},{bz}) overlaps placed {other}')
        if continuous and matter == 'Ground' and 0 <= x < model.sx and 0 <= y < model.sy:
            if not model.contiguous[y, x] or model.height[y, x] != z:
                problems.append(f'block ({x},{y},{z}) is not on the first terrain column (ContinuousTerrainConstraint)')
    return problems


def footprint(blocks, coordinates, orientation='Cw0', flipped=False):
    return {(x, y) for x, y, _ in blocks.occupied_cells(coordinates, orientation, flipped)}


def site_problems(model, cells, level, placed_columns):
    """Problems for a building footprint resting on terrain level `level`."""
    problems = []
    trees = 0
    for x, y in sorted(cells):
        if not (0 <= x < model.sx and 0 <= y < model.sy):
            problems.append(f'({x},{y}) outside the map')
            continue
        if model.height[y, x] != level:
            problems.append(f'({x},{y}) terrain {model.height[y, x]} != {level}')
        elif not model.contiguous[y, x]:
            problems.append(f'({x},{y}) has an overhang/gap')
        if model.water_any[y, x] > 0:
            problems.append(f'({x},{y}) has water')
        if model.hard_mask[y, x]:
            problems.append(f'({x},{y}) has a non-removable map object')
        if (x, y) in placed_columns:
            problems.append(f'({x},{y}) is occupied by a Deep Frontier placement')
        if model.natural_mask[y, x]:
            trees += 1
    return problems, trees


def ring(cells, width):
    xs = [x for x, _ in cells]
    ys = [y for _, y in cells]
    result = set()
    for x in range(min(xs) - width, max(xs) + width + 1):
        for y in range(min(ys) - width, max(ys) + width + 1):
            if (x, y) not in cells:
                result.add((x, y))
    return result


def side_strips(cells, width):
    """Margin strips of the footprint bounding box per side (corners excluded): N is +y, E is +x."""
    xs = [x for x, _ in cells]
    ys = [y for _, y in cells]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    return {
        'N': {(x, y) for x in range(x0, x1 + 1) for y in range(y1 + 1, y1 + width + 1)},
        'S': {(x, y) for x in range(x0, x1 + 1) for y in range(y0 - width, y0)},
        'E': {(x, y) for x in range(x1 + 1, x1 + width + 1) for y in range(y0, y1 + 1)},
        'W': {(x, y) for x in range(x0 - width, x0) for y in range(y0, y1 + 1)},
    }


def route_to(model, cells):
    """(route length, water cells bridged) to the best dry cell next to cells; (None, None) if none."""
    length, bridges = model.route()
    best = None
    for x, y in ring(set(cells), 1):
        if 0 <= x < model.sx and 0 <= y < model.sy and length[y, x] >= 0 and model.water_any[y, x] == 0:
            key = (int(bridges[y, x]), int(length[y, x]))
            if best is None or key < best:
                best = key
    return (None, None) if best is None else (best[1], best[0])


# --------------------------------------------------------------- previews

def render_preview(model, path, marks=(), legend=()):
    """Overview render, north up. A mark is (label, cells, colour) or (label, cells, colour, filled);
    legend lines (text, colour) are listed in a panel on the right."""
    from PIL import Image, ImageDraw
    scale = 4 if max(model.sx, model.sy) <= 256 else 3
    panel = 420 if legend else 0
    image = Image.new('RGB', (model.sx * scale + panel, max(model.sy * scale, 14 * len(legend) + 20)), (24, 24, 24))
    pixels = image.load()
    hmax = max(int(model.height.max()), 1)
    for y in range(model.sy):
        for x in range(model.sx):
            h = int(model.height[y, x])
            shade = 60 + int(170 * h / hmax)
            colour = (shade, shade, int(shade * 0.85))
            if model.water_depth[y, x] > 0:
                c = model.water_contamination[y, x]
                colour = (int(90 + 120 * c), int(80 + 40 * (1 - c)), int(200 * (1 - c) + 40)) if c >= 0.5 else (40, 90, 210)
            elif model.hard_mask[y, x]:
                colour = (200, 60, 60)
            elif model.natural_mask[y, x]:
                colour = (40, 120 + min(h * 4, 60), 40)
            for dy in range(scale):
                for dx in range(scale):
                    # map y grows north; draw north up
                    pixels[x * scale + dx, (model.sy - 1 - y) * scale + dy] = colour
    draw = ImageDraw.Draw(image)
    sx, sy, _ = model.start
    draw.rectangle([sx * scale - 6, (model.sy - 1 - sy) * scale - 6, sx * scale + 6, (model.sy - 1 - sy) * scale + 6], outline=(255, 255, 255), width=2)
    for mark in marks:
        label, cells, colour = mark[:3]
        filled = len(mark) > 3 and mark[3]
        xs = [x for x, _ in cells]
        ys = [y for _, y in cells]
        x0, x1 = min(xs) * scale, (max(xs) + 1) * scale - 1
        y0, y1 = (model.sy - 1 - max(ys)) * scale, (model.sy - min(ys)) * scale - 1
        if filled:
            draw.rectangle([x0, y0, x1, y1], fill=colour, outline=(0, 0, 0))
        else:
            draw.rectangle([x0, y0, x1, y1], outline=colour, width=2)
        if label:
            draw.text((x0 + 2, y0 + 2) if not filled else (x1 + 2, y0 - 2), label, fill=colour)
    for index, (text, colour) in enumerate(legend):
        draw.text((model.sx * scale + 10, 10 + 14 * index), text, fill=colour)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


PLACEMENT_COLOURS = {'DeepOreVein': (255, 190, 0), 'DeepOreSource': (255, 255, 0), 'RadioactiveSpringSource': (170, 255, 0),
                     'SandstoneOutcrop': (235, 150, 80), 'LimestoneOutcrop': (235, 235, 205), 'SandstoneSeam': (235, 150, 80),
                     'LimestoneSeam': (235, 235, 205), 'HumanRecordCache': (255, 255, 255)}
STAGE_COLOURS = {'construction': (235, 170, 110), 'deepIndustry': (255, 130, 0), 'power': (255, 70, 255),
                 'narrative': (150, 200, 255), 'nuclear': (170, 255, 0), 'rocket': (0, 255, 255), 'space': (255, 255, 255)}


def preview_marks(variant, catalog, report):
    """Marks and legend for every placement and site of a variant (site codes S1.., placement codes P1..)."""
    marks, legend = [], [(f'{variant["output"]["name"]}', (255, 255, 255)), ('white square: starting location', (255, 255, 255)), ('', (0, 0, 0))]
    stages = {}
    for stage in report['loopCoverage']['stages']:
        for item in stage['items']:
            stages[item['item'].split(' site (')[0]] = stage['id']
    for index, p in enumerate(variant['placements'], 1):
        blocks = Blocks(catalog.get(p['template'])['BlockObjectSpec'])
        colour = PLACEMENT_COLOURS[p['template']]
        cells = footprint(blocks, (p['x'], p['y'], p['z']), p.get('orientation', 'Cw0'))
        small = len(cells) <= 6
        marks.append((f'P{index}', cells, colour, small))
        legend.append((f'P{index} {p["template"]}: {p["label"]}'[:62], colour))
    legend.append(('', (0, 0, 0)))
    for index, (site, info) in enumerate(zip(variant['sites'], report['sites']), 1):
        stage = stages.get(site['template'], 'space')
        colour = STAGE_COLOURS[stage] if not info['problems'] else (255, 0, 0)
        if info['rule'] == 'hydro':
            cells = {(site['x'] + dx, site['y'] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
            marks.append((f'S{index}', cells, colour, True))
        else:
            blocks = building_blocks(catalog, site['template'])
            cells = {(x, y) for x, y, z, _ in blocks.positioned((site['x'], site['y'], site['z']), site['orientation'])}
            marks.append((f'S{index}', cells, colour))
        legend.append((f'S{index} {site["template"].split(".")[0]}: {site["label"]}'[:62], colour))
    legend.append(('', (0, 0, 0)))
    legend += [(f'{name}: {stage}', STAGE_COLOURS[stage]) for stage, name in
               [(s, t) for s, t in LOOP_STAGES if s in STAGE_COLOURS]]
    return marks, legend


# ----------------------------------------------------------------- survey

def rect_cells(x, y, width, height):
    return {(cx, cy) for cx in range(x, x + width) for cy in range(y, y + height)}


def survey(model):
    heights = model.height
    values, counts = np.unique(heights, return_counts=True)
    water_cells = int((model.water_depth > 0).sum())
    bad_cells = int(((model.water_depth > 0) & (model.water_contamination >= 0.5)).sum())
    sources = {}
    for record in model.objects:
        if record['template'] in ('WaterSource', 'BadwaterSource', 'WaterSeep', 'BadwaterSeep', 'Aquifer', 'BadtideDrain'):
            entity = model.world['Entities'][record['index']]
            strength = entity['Components'].get('WaterSource', {}).get('SpecifiedStrength')
            sources.setdefault(record['template'], []).append((record['coordinates'], strength))
    return {
        'size': [model.sx, model.sy], 'gameVersion': model.world['GameVersion'], 'version': model.version,
        'terrainLayersStored': model.layers, 'terrainLayers': model.terrain_layers,
        'totalHeight': model.total_height, 'heightSource': model.height_source,
        'heights': {int(v): int(c) for v, c in zip(values, counts)},
        'waterCells': water_cells, 'badwaterCells': bad_cells,
        'start': model.start, 'waterSources': sources,
        'entities': len(model.world['Entities']),
    }


# --------------------------------------------------------------- variants

def load_variant(path):
    path = Path(path)
    variant = read_json(path)
    required = ['id', 'source', 'sourceSha256', 'output', 'hardVariant', 'description', 'placements', 'sites']
    missing = [key for key in required if key not in variant]
    if missing:
        fail(f'{path}: missing keys {missing}')
    return variant


def dump_variant(variant):
    """Variant JSON in the repository layout: one placement or site per line."""
    lines = ['{']
    keys = list(variant)
    for index, key in enumerate(keys):
        comma = ',' if index < len(keys) - 1 else ''
        value = variant[key]
        if key in ('placements', 'sites'):
            lines.append(f'  {json.dumps(key)}: [')
            for i, entry in enumerate(value):
                lines.append('    ' + json.dumps(entry, ensure_ascii=False) + (',' if i < len(value) - 1 else ''))
            lines.append('  ]' + comma)
        else:
            lines.append(f'  {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)}{comma}')
    lines.append('}')
    return '\n'.join(lines) + '\n'


def building_blocks(catalog, template):
    """Blocks of a building template (a TemplateName of the Iron Teeth building collection)."""
    if template not in catalog.building_collection:
        fail(f'{template} is not in {BUILDING_COLLECTION}')
    return Blocks(catalog.get(template)['BlockObjectSpec'])


def new_entity(placement, catalog, variant_id, index):
    template = placement['template']
    if template not in catalog.map_editor_common:
        fail(f'{template} is not in the mod MapEditor Common collection')
    entity_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f'deep-frontier-map/{variant_id}/{index}/{template}'))
    block_object = {'Coordinates': {'X': placement['x'], 'Y': placement['y'], 'Z': placement['z']}}
    orientation = placement.get('orientation', 'Cw0')
    if orientation != 'Cw0':
        block_object['Orientation'] = orientation
    components = {'BlockObject': block_object}
    blueprint = catalog.get(template)
    if 'StockpileSpec' in blueprint:
        good, amount = placement['good'], placement['amount']
        components['FixedStockpile'] = {'FixedGoodId': good}
        components['SingleGoodAllower'] = {'AllowedGood': good}
        components['Inventory:Stockpile'] = {'Storage': {'Goods': [{'Good': good, 'Amount': amount}]}}
    elif 'RadioactiveWaterSourceSpec' in blueprint:
        # A native water source whose water is radioactive. Native
        # WaterSource.Save writes, and WaterSource.Load requires, both
        # SpecifiedStrength and CurrentStrength (build 124 crashed on load
        # with only the first); the vanilla map sources store them equal.
        strength = placement['radioactivePerHour'] / water_per_strength_hour()
        components['WaterSource'] = {'SpecifiedStrength': strength, 'CurrentStrength': strength}
    elif 'MineralDepositSpec' in blueprint:
        # The native Yielder saves under "Yielder:<YielderComponentName>"; the
        # official map editor wrote {"Yield": {"Good", "Amount"}} for these
        # outcrops in Deep Frontier - Concrete Test. The amount is the
        # blueprint's full yield.
        yielder = blueprint['MineralDepositSpec']['Yielder']
        components[f'Yielder:{yielder["YielderComponentName"]}'] = {
            'Yield': {'Good': yielder['Yield']['Id'], 'Amount': yielder['Yield']['Amount']}}
    extra = set(placement) - {'template', 'x', 'y', 'z', 'orientation', 'label', 'good', 'amount', 'radioactivePerHour'}
    missing = {'template', 'x', 'y', 'z', 'label'} - set(placement)
    if extra or missing:
        fail(f'Placement {placement} has unknown keys {sorted(extra)} / missing keys {sorted(missing)}')
    return {'Id': entity_id, 'Template': template, 'Components': components}


def good_spec(good_id):
    for path in (MOD_DATA / 'Goods').rglob('*.json'):
        spec = read_json(path).get('GoodSpec')
        if spec and spec.get('Id') == good_id:
            return spec
    fail(f'Good {good_id} is not defined in {MOD_DATA / "Goods"}')


def deep_drill_inputs(catalog):
    """Goods the DeepDrill's recipes consume; a DeepOreSource must hold one of them."""
    drill = catalog.get('DeepDrill.IronTeeth')
    recipe_ids = set(drill['ManufactorySpec']['ProductionRecipeIds'])
    inputs = set()
    for path in (MOD_DATA / 'Recipes').rglob('*.json'):
        spec = read_json(path).get('RecipeSpec')
        if spec and spec['Id'] in recipe_ids:
            recipe_ids.discard(spec['Id'])
            inputs |= {ingredient['Id'] for ingredient in spec['Ingredients']}
    if recipe_ids:
        fail(f'DeepDrill recipes {sorted(recipe_ids)} are not defined in {MOD_DATA / "Recipes"}')
    return inputs


def record_cache_blocks(catalog):
    """BlockObjectSpec of the Human Record Cache (identical to its MediumRelic source)."""
    spec = catalog.get(RECORD_CACHE_CLONED_FROM)['BlockObjectSpec']
    if catalog.get(RECORD_CACHE_TEMPLATE)['BlockObjectSpec'] != spec:
        fail(f'{RECORD_CACHE_TEMPLATE} no longer has the {RECORD_CACHE_CLONED_FROM} BlockObjectSpec; update this tool')
    return Blocks(spec)


def required_mod_names():
    """Display names of the mod manifest's RequiredMods, from the installed dependency capture."""
    manifest = read_json(MOD_MANIFEST)
    names = {package['id']: package['name'] for package in read_json(DEPENDENCY_MANIFESTS)['packages']}
    result = []
    for mod in manifest['RequiredMods']:
        if mod['Id'] not in names:
            fail(f'Required mod {mod["Id"]} has no installed name in {DEPENDENCY_MANIFESTS}')
        result.append(names[mod['Id']].split(' [')[0])
    return manifest, result


def compose_description(variant):
    manifest, names = required_mod_names()
    return (f'{variant["description"]} Requires {manifest["Name"]} {manifest["Version"]} '
            f'(Iron Teeth, Timberborn {manifest["MinimumGameVersion"]}) and its required mods: {", ".join(names)}.')


ENTITIES_TAIL = b']}'


def entity_array_head(raw):
    """Source world.json bytes up to (not including) the closing ']}' of the trailing Entities array."""
    world = json.loads(raw)
    if list(world)[-1] != 'Entities' or not world['Entities'] or not raw.endswith(ENTITIES_TAIL):
        fail('world.json must end with a non-empty "Entities" array')
    return raw[:-len(ENTITIES_TAIL)]


def apply_variant(variant, source_entries, catalog):
    """Append the placements to the source Entities array without re-serializing the source.

    The source bytes stay identical up to the end of the existing Entities; the
    new entities are appended. Nothing is removed: a placement that overlaps
    any existing object (including trees) is a validation error."""
    head = entity_array_head(source_entries['world.json'])
    addition = b''.join(b',' + json.dumps(new_entity(placement, catalog, variant['id'], index),
                                           separators=(',', ':'), ensure_ascii=False).encode('utf-8')
                        for index, placement in enumerate(variant['placements']))
    metadata = json.loads(source_entries['map_metadata.json'])
    metadata['MapNameLocKey'] = ''
    metadata['MapDescriptionLocKey'] = ''
    metadata['MapDescription'] = compose_description(variant)
    metadata['IsRecommended'] = False
    metadata['IsUnconventional'] = False
    metadata['IsDev'] = False
    entries = dict(source_entries)
    entries['world.json'] = head + addition + ENTITIES_TAIL
    entries['map_metadata.json'] = json.dumps(metadata, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return entries


def write_timber(entries, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in ENTRY_ORDER:
            archive.writestr(name, entries[name])
    path.write_bytes(buffer.getvalue())


def output_path(variant):
    output = variant['output']
    return Path(output['directory']) / (output['name'] + '.timber')


# ------------------------------------------------------------ loop coverage
#
# docs/maps.md "Full game loop": what each stage of the Deep Frontier loop
# needs from a map, read from the generated blueprints (placement specs,
# recipes, building costs, narrative settings) plus the authored policy
# minimums in tools/map_loop_requirements.json.

SPECIAL_SITE_RULES = (('UnderstructureConstraintSpec', 'understructure'), ('MapEdgeSiteSpec', 'mapEdge'),
                      ('WaterDepthWorkCellsSpec', 'waterDepth'), ('WaterInputSpec', 'waterInput'),
                      ('MineralPitSpec', 'pit'), ('HydroTurbineSpec', 'hydro'))
SITE_KEYS = {
    'flat': {'template', 'label', 'x', 'y', 'z', 'orientation', 'margin', 'openSides'},
    'understructure': {'template', 'label', 'x', 'y', 'z', 'orientation', 'margin', 'openSides', 'understructure'},
    'pit': {'template', 'label', 'x', 'y', 'z', 'orientation', 'margin', 'openSides'},
    'mapEdge': {'template', 'label', 'x', 'y', 'z', 'orientation', 'margin', 'openSides'},
    'waterDepth': {'template', 'label', 'x', 'y', 'z', 'orientation'},
    'waterInput': {'template', 'label', 'x', 'y', 'z', 'orientation'},
    'hydro': {'template', 'label', 'x', 'y', 'z'},
}
OPTIONAL_SITE_KEYS = {'maxWaterDistance', 'alternative', 'dynamite'}
LOOP_STAGES = [
    ('start', 'Start-game resources'),
    ('construction', 'Construction materials'),
    ('deepIndustry', 'Metal and deep industry'),
    ('power', 'Power'),
    ('narrative', 'Science and narrative'),
    ('nuclear', 'Nuclear and radiation'),
    ('rocket', 'Rocket program'),
    ('space', 'Space for late-game footprints'),
]


def load_loop_requirements():
    raw = read_json(LOOP_REQUIREMENTS)
    if raw.get('schema') != 1:
        fail(f'{LOOP_REQUIREMENTS}: schema must be 1')
    return {key: value['value'] for key, value in raw.items() if isinstance(value, dict) and 'value' in value}


def site_rule(catalog, template, large):
    """The map provision a building of the collection needs, from its blueprint (None: places anywhere)."""
    blueprint = catalog.get(template)
    for spec, rule in SPECIAL_SITE_RULES:
        if spec in blueprint:
            return rule
    if catalog.building_collection[template].startswith('Buildings/Platforms/'):
        return None
    size = blueprint['BlockObjectSpec']['Size']
    if 'WorkshopPoweredGeneratorSpec' in blueprint or 'GoodPoweredGeneratorSpec' in blueprint or max(size['X'], size['Y']) >= large:
        return 'flat'
    return None


def required_site_templates(catalog, requirements):
    return {template: rule for template in catalog.building_collection
            if (rule := site_rule(catalog, template, requirements['largeFootprint'])) is not None}


def approach_cell(blocks, coordinates, orientation):
    """Door approach: the entrance cell, or the first cell in front of it (local -y) outside the footprint."""
    entrance = blocks.entrance
    if not entrance['HasEntrance']:
        return None
    c = entrance['Coordinates']
    sx, sy, _ = blocks.size
    x, y = c['X'], c['Y']
    while 0 <= x < sx and 0 <= y < sy:
        y -= 1
    wx, wy = blocks.transform((x, y), coordinates, orientation, False)
    return wx, wy, coordinates[2] - blocks.base_z + c['Z']


def building_block_problems(model, blocks, coordinates, orientation, placed, blasted=None, stands_in_water=False):
    """Native block rules for a building that is not a flat footprint (waterside): trees are counted, not refused.
    `blasted` maps a column to the terrain level it has after the player's Dynamite (vanilla
    DynamiteSpec removes Depth layers per charge). Native BlockValidator has no water rule; an
    occupied block in water is refused here unless `stands_in_water` (a building whose working
    cells must be submerged and that has no FloodableBuildingSpec, i.e. the Fish Hatchery's
    deck slabs and pens)."""
    problems, trees = [], set()
    blasted = blasted or {}
    for x, y, z, block in blocks.positioned(coordinates, orientation):
        if not (0 <= x < model.sx and 0 <= y < model.sy):
            if occupied(block):
                problems.append(f'block ({x},{y},{z}) outside the map')
            continue
        if occupied(block):
            if not 0 <= z < model.total_height:
                problems.append(f'block ({x},{y},{z}) outside the height {model.total_height}')
            if 0 <= z < model.layers and model.solid[z, y, x] and not ((x, y) in blasted and z >= blasted[(x, y)]):
                problems.append(f'block ({x},{y},{z}) inside terrain')
            depth = model.water_at(x, y, z)
            if depth > 0 and not stands_in_water:
                problems.append(f'block ({x},{y},{z}) is in water (depth {depth:.2f})')
            for record in model.cells.get((x, y, z), []) + model.bottom_cells.get((x, y, z), []):
                if record['natural']:
                    trees.add((x, y))
                else:
                    problems.append(f'block ({x},{y},{z}) overlaps {record["template"]} at {record["coordinates"]}')
            for other in placed.get((x, y, z), []):
                problems.append(f'block ({x},{y},{z}) overlaps placed {other}')
        matter = block['MatterBelow']
        below_solid = 0 <= z - 1 < model.layers and model.solid[z - 1, y, x]
        if (x, y) in blasted and z - 1 >= blasted[(x, y)]:
            below_solid = False
        if matter in ('Ground', 'GroundOrStackable') and not below_solid:
            problems.append(f'block ({x},{y},{z}) needs ground below ({matter})')
        if matter == 'Air' and below_solid:
            problems.append(f'block ({x},{y},{z}) needs open air below')
    return problems, len(trees)


def water_source_cells(model, catalog, badwater=None):
    """(x, y, strength, contamination) of every native water source (WaterSourceSpec) of the map."""
    result = []
    for record in model.objects:
        blueprint = catalog.get(record['template'])
        if 'WaterSourceSpec' not in blueprint:
            continue
        entity = model.world['Entities'][record['index']]
        strength = entity['Components']['WaterSource']['SpecifiedStrength']
        contamination = blueprint.get('WaterSourceContaminationSpec', {}).get('DefaultContamination', 0)
        if badwater is not None and (contamination >= 0.5) != badwater:
            continue
        blocks = Blocks(blueprint['BlockObjectSpec'])
        for c in blueprint['WaterSourceSpec']['Coordinates']:
            x, y = blocks.transform((c['X'], c['Y']), record['coordinates'], record['orientation'], record['flipped'])
            result.append((x, y, strength, contamination))
    return result


def wet_components(model):
    """Label of the 4-connected surface-wet component of every cell (-1 when dry)."""
    if hasattr(model, '_wet_labels'):
        return model._wet_labels
    wet = model.water_depth > 0
    labels = np.full((model.sy, model.sx), -1, dtype=np.int32)
    current = 0
    for y0, x0 in zip(*np.nonzero(wet)):
        if labels[y0, x0] >= 0:
            continue
        queue = deque([(int(x0), int(y0))])
        labels[y0, x0] = current
        while queue:
            x, y = queue.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < model.sx and 0 <= ny < model.sy and wet[ny, nx] and labels[ny, nx] < 0:
                    labels[ny, nx] = current
                    queue.append((nx, ny))
        current += 1
    model._wet_labels = labels
    return labels


def source_strength_by_component(model, catalog):
    """Water-source strength feeding each wet component (a source feeds the components it touches)."""
    labels = wet_components(model)
    strength = {}
    for x, y, value, _ in water_source_cells(model, catalog):
        touched = {int(labels[ny, nx]) for nx, ny in ((x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                   if 0 <= nx < model.sx and 0 <= ny < model.sy and labels[ny, nx] >= 0}
        for label in touched:
            strength[label] = strength.get(label, 0) + value
    return strength


def check_flat_site(model, blocks, site, placed_columns, exclude=frozenset()):
    """Flat, dry, free footprint (trees allowed), top layer inside the map and the listed open margins."""
    coordinates = (site['x'], site['y'], site['z'])
    orientation = site['orientation']
    columns = {k: v for k, v in placed_columns.items() if k not in exclude}
    all_cells = blocks.columns(coordinates, orientation)
    problems, trees = site_problems(model, all_cells, site['z'], columns)
    top = site['z'] - blocks.base_z + blocks.top_occupied_layer()
    if top >= model.total_height:
        problems.append(f'top occupied layer z={top} >= total height {model.total_height}')
    margin = site['margin']
    margin_problems, _ = site_problems(model, ring(all_cells, margin), site['z'], placed_columns)
    side_problems = {side: len(site_problems(model, strip, site['z'], placed_columns)[0])
                     for side, strip in side_strips(all_cells, margin).items()}
    for side in site['openSides']:
        if side_problems[side]:
            problems.append(f'open side {side} has {side_problems[side]} margin cells that are not flat/free')
    info = {'footprint': [min(x for x, _ in all_cells), min(y for _, y in all_cells),
                          max(x for x, _ in all_cells), max(y for _, y in all_cells)],
            'topOccupiedZ': top, 'treesToClear': trees, 'margin': margin,
            'marginCellsNotFlat': len(margin_problems), 'openSides': site['openSides'], 'sideProblems': side_problems}
    return problems, info, all_cells


def check_door(model, blocks, site, placed_columns):
    coordinates = (site['x'], site['y'], site['z'])
    approach = approach_cell(blocks, coordinates, site['orientation'])
    if approach is None:
        return [], None
    problems = []
    ax, ay, az = approach
    door_problems, _ = site_problems(model, {(ax, ay)}, az, placed_columns)
    if door_problems:
        problems.append(f'door approach {approach} is blocked: {door_problems}')
    length, _ = model.route()
    if not (0 <= ax < model.sx and 0 <= ay < model.sy) or length[ay, ax] < 0:
        problems.append(f'door approach {approach} has no route from the start')
    return problems, list(approach)


def understructure_core(blocks, coordinates, orientation):
    """UnderstructureFinder.FindStrict: foundation blocks whose occupation is exactly Top and/or Corners."""
    core, other = set(), set()
    for x, y, z, b in blocks.occupied_blocks(coordinates, orientation):
        if z != coordinates[2] - blocks.base_z:
            continue
        if b['MatterBelow'] in ('Ground', 'GroundOrStackable', 'Stackable') \
                and b['Occupations'] in ('Top', 'Corners', 'Top, Corners', 'Corners, Top'):
            core.add((x, y))
        elif occupied(b):
            other.add((x, y))
    return core, other


def pit_reach(model, blocks, site, deposits, blocked):
    """Deposits whose cell is within RESOURCE_BUILDING_RANGE 4-neighbour steps of the pit's door
    over same-level, dry, free ground outside every claimed footprint."""
    approach = approach_cell(blocks, (site['x'], site['y'], site['z']), site['orientation'])
    if approach is None:
        return []
    ax, ay, level = approach
    distance = {(ax, ay): 0}
    queue = deque([(ax, ay)])
    while queue:
        x, y = queue.popleft()
        if distance[(x, y)] >= RESOURCE_BUILDING_RANGE:
            continue
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) in distance or not (0 <= nx < model.sx and 0 <= ny < model.sy) or (nx, ny) in blocked:
                continue
            if model.height[ny, nx] != level or not model.contiguous[ny, nx] or model.water_any[ny, nx] > 0 \
                    or model.hard_mask[ny, nx]:
                continue
            distance[(nx, ny)] = distance[(x, y)] + 1
            queue.append((nx, ny))
    reached = []
    for record in deposits:
        x, y, z = record['coordinates']
        if z != level:
            continue
        steps = [distance[(nx, ny)] + 1 for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                 if (nx, ny) in distance]
        if steps and min(steps) <= RESOURCE_BUILDING_RANGE:
            reached.append((record, min(steps)))
    return reached


def hydro_head(model, x, y, window):
    """Natural bed drop (layers) over the wet cells within `window` steps of (x, y) along the water."""
    wet = model.water_depth > 0
    seen = {(x, y): 0}
    queue = deque([(x, y)])
    while queue:
        cx, cy = queue.popleft()
        if seen[(cx, cy)] >= window:
            continue
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < model.sx and 0 <= ny < model.sy and wet[ny, nx] and (nx, ny) not in seen:
                seen[(nx, ny)] = seen[(cx, cy)] + 1
                queue.append((nx, ny))
    beds = [int(model.height[cy, cx]) for cx, cy in seen]
    return max(beds) - min(beds), len(seen)


def check_site(model, catalog, site, records, placed, placed_columns, requirements, rule):
    """(problems, info, claimed cells) for one site."""
    template = site['template']
    blueprint = catalog.get(template)
    blocks = building_blocks(catalog, template)
    coordinates = (site['x'], site['y'], site['z'])
    info = {'template': template, 'rule': rule, 'label': site['label'], 'at': list(coordinates),
            'orientation': site.get('orientation'), 'alternative': bool(site.get('alternative'))}
    problems = []
    cells = set()
    if rule in ('flat', 'understructure', 'pit', 'mapEdge'):
        exclude = frozenset()
        under = None
        if rule == 'understructure':
            names = blueprint['UnderstructureConstraintSpec']['UnderstructureTemplateNames']
            match = [r for r in records if r['template'] in names and list(r['coordinates']) == list(site['understructure'])]
            if len(match) != 1:
                problems.append(f'understructure {site["understructure"]} is not one placed {names}')
            else:
                under = match[0]
                exclude = frozenset(under['cells'])
        p, extra, cells = check_flat_site(model, blocks, site, placed_columns, exclude)
        problems += p
        info.update(extra)
        if under is not None:
            core, other = understructure_core(blocks, coordinates, site['orientation'])
            if not core or not core <= under['cells']:
                problems.append(f'ground core ({len(core)} cells) is not entirely on the {under["template"]}')
            if other & under['cells']:
                problems.append(f'{len(other & under["cells"])} other occupied foundation cells stand on the {under["template"]}')
            if under['coordinates'][2] != site['z']:
                problems.append(f'{under["template"]} level {under["coordinates"][2]} differs from the site level')
            info.update(understructure=under['template'], understructureAt=list(under['coordinates']),
                        coreCellsOnUnderstructure=len(core & under['cells']))
        if rule == 'mapEdge':
            edge = [(x, y) for x, y, z in blocks.occupied_cells(coordinates, site['orientation'])
                    if x in (0, model.sx - 1) or y in (0, model.sy - 1)]
            info['edgeCells'] = len(edge)
            if not edge:
                problems.append('no occupied block on the map edge (MapEdgeSiteSpec)')
        if 'maxWaterDistance' in site or 'ReactorMeltdownSpec' in blueprint:
            if 'maxWaterDistance' not in site:
                fail(f'site {site["label"]}: a reactor site needs maxWaterDistance')
            water = model.water_distance()
            border = [(x, y) for x, y in ring(cells, 1) if 0 <= x < model.sx and 0 <= y < model.sy]
            wd = [int(water[y, x]) for x, y in border if water[y, x] >= 0]
            info['waterDistance'] = min(wd) if wd else None
            if info['waterDistance'] is None or info['waterDistance'] > site['maxWaterDistance']:
                problems.append(f'water distance {info["waterDistance"]} exceeds {site["maxWaterDistance"]}')
        p, info['door'] = check_door(model, blocks, site, placed_columns)
        problems += p
        info['freeboard'] = freeboard(model, cells, site['z'])
    elif rule in ('waterDepth', 'waterInput'):
        # "dynamite": [[x, y, layers], ...] cells of the footprint the player blasts first with the
        # vanilla Dynamite (DynamiteSpec.Depth 1-3 layers per charge, 600-1,200 science).
        blasted = {}
        columns = blocks.columns(coordinates, site['orientation'])
        for x, y, layers in site.get('dynamite', []):
            if (x, y) not in columns:
                problems.append(f'dynamite cell ({x},{y}) is outside the footprint')
            elif not 1 <= layers <= int(model.height[y, x]):
                problems.append(f'dynamite cell ({x},{y}) cannot remove {layers} layers')
            else:
                blasted[(x, y)] = int(model.height[y, x]) - layers
        info['dynamite'] = site.get('dynamite', [])
        stands_in_water = rule == 'waterDepth' and 'FloodableBuildingSpec' not in blueprint
        p, trees = building_block_problems(model, blocks, coordinates, site['orientation'], placed, blasted,
                                           stands_in_water)
        problems += p
        cells = blocks.columns(coordinates, site['orientation'])
        problems += [f'({x},{y}) is a Deep Frontier placement column' for x, y in sorted(cells) if (x, y) in placed_columns]
        info['treesToClear'] = trees
        base = site['z'] - blocks.base_z
        if rule == 'waterDepth':
            # The in-game reading (WatersideSurvey.ReadWorkCell / Classify,
            # src/DeepFrontier/Scripts/Waterside): the open native water column that
            # contains the working cell. Shallow when its surface stands less than
            # MinDepth above the cell's own floor (submersion = surface - cell z), Deep
            # when the column holds more than MaxDepth. Only WorkCells[0] supplies the
            # native ContaminationBlockableBuilding sample (its column), blocked above 0.05.
            spec = blueprint['WaterDepthWorkCellsSpec']
            readings = []
            for index, c in enumerate(spec['WorkCells']):
                wx, wy = blocks.transform((c['X'], c['Y']), coordinates, site['orientation'], False)
                wz = base + c['Z']
                inside = 0 <= wx < model.sx and 0 <= wy < model.sy
                depth = float(model.water_depth[wy, wx]) if inside else 0.0
                floor = blasted.get((wx, wy), int(model.height[wy, wx])) if inside else None
                contamination = float(model.water_contamination[wy, wx]) if inside else 1.0
                submersion = floor + depth - wz if floor is not None else None
                readings.append({'cell': [wx, wy, wz], 'floor': floor, 'depth': round(depth, 3),
                                 'submersion': None if submersion is None else round(submersion, 3),
                                 'contamination': round(contamination, 3)})
                if floor is None or floor > wz:
                    problems.append(f'work cell ({wx},{wy},{wz}) is not in an open water column (floor {floor})')
                    continue
                if submersion < spec['MinDepth']:
                    problems.append(f'work cell ({wx},{wy},{wz}) water surface {floor + depth:.2f} is {submersion:.2f} '
                                    f'above the cell floor, below MinDepth {spec["MinDepth"]} (needs water)')
                elif depth > spec['MaxDepth']:
                    problems.append(f'work cell ({wx},{wy}) column holds {depth:.2f} m of water > MaxDepth {spec["MaxDepth"]}')
                if index == 0 and contamination > MAX_WORK_CELL_CONTAMINATION:
                    problems.append(f'work cell ({wx},{wy}) water contamination {contamination:.2f} > {MAX_WORK_CELL_CONTAMINATION} (blocked)')
            info['workCells'] = readings
            supports = blueprint.get('AdaptiveSupportsSpec')
            if supports:
                # AdaptiveSupportsPlacementValidator / WatersideSurvey.ProbeSupport: every pile column
                # lies inside the map and reaches terrain within MaxDepth cells below its top cell
                # (the bottom of the map is solid).
                piles = []
                for c in supports['Columns']:
                    px, py = blocks.transform((c['X'], c['Y']), coordinates, site['orientation'], False)
                    top = base + c['Z']
                    if not (0 <= px < model.sx and 0 <= py < model.sy):
                        problems.append(f'support column ({px},{py}) is outside the map')
                        continue
                    bed = blasted.get((px, py))
                    if bed is not None:
                        segments = top - (bed - 1)
                    else:
                        segments = next((top - z for z in range(min(top, model.layers - 1), -1, -1)
                                         if model.solid[z, py, px]), top + 1)
                    piles.append({'column': [px, py, top], 'segments': segments})
                    if segments > supports['MaxDepth']:
                        problems.append(f'support column ({px},{py}) needs {segments} segments > MaxDepth {supports["MaxDepth"]}')
                info['supports'] = piles
        else:
            c = blueprint['WaterInputSpec']['WaterInputCoordinates']
            max_depth = blueprint['WaterInputPipeSpec']['MaxDepth']
            ix, iy = blocks.transform((c['X'], c['Y']), coordinates, site['orientation'], False)
            iz = base + c['Z']
            if not (0 <= ix < model.sx and 0 <= iy < model.sy):
                problems.append(f'intake ({ix},{iy}) outside the map')
            elif (ix, iy) in blasted:
                # The player blasts the intake column down to the bed of the
                # neighbouring water, which then flows into it.
                floor = blasted[(ix, iy)]
                beds = [int(model.height[ny, nx]) for nx, ny in ((ix + 1, iy), (ix - 1, iy), (ix, iy + 1), (ix, iy - 1))
                        if 0 <= nx < model.sx and 0 <= ny < model.sy and model.water_depth[ny, nx] > 0]
                info['intake'] = {'cell': [ix, iy, iz], 'floor': floor, 'blasted': True,
                                  'neighbourBeds': beds, 'maxDepth': max_depth}
                if not beds or floor > max(beds):
                    problems.append(f'blasted intake floor {floor} at ({ix},{iy}) does not reach a neighbouring water bed {beds}')
                if floor > iz or iz - floor >= max_depth:
                    problems.append(f'blasted intake floor {floor} is not within {max_depth} layers below z={iz}')
            else:
                floor = int(model.height[iy, ix])
                info['intake'] = {'cell': [ix, iy, iz], 'floor': floor, 'water': round(float(model.water_depth[iy, ix]), 3),
                                  'maxDepth': max_depth}
                if floor > iz or iz - floor >= max_depth:
                    problems.append(f'intake column ({ix},{iy}) floor {floor} is not within {max_depth} layers below z={iz}')
                if model.water_depth[iy, ix] <= 0:
                    problems.append(f'intake column ({ix},{iy}) holds no water')
        p, info['door'] = check_door(model, blocks, site, placed_columns)
        problems += p
    elif rule == 'hydro':
        x, y, z = coordinates
        labels = wet_components(model)
        strength = source_strength_by_component(model, catalog)
        if not (0 <= x < model.sx and 0 <= y < model.sy) or labels[y, x] < 0:
            problems.append('dam site is not a wet river cell')
        else:
            if int(model.height[y, x]) != z:
                problems.append(f'river bed at ({x},{y}) is {int(model.height[y, x])}, not {z}')
            head, reach = hydro_head(model, x, y, requirements['hydroWindow'])
            info.update(naturalHead=head, reachCells=reach, sourceStrength=strength.get(int(labels[y, x]), 0),
                        contamination=round(float(model.water_contamination[y, x]), 3))
            if head < requirements['minHydroHead']:
                problems.append(f'natural head {head} < {requirements["minHydroHead"]}')
            if not strength.get(int(labels[y, x])):
                problems.append('the river reach is fed by no water source')
        cells = {(x, y)}
    if rule != 'hydro':
        # Site z is the surface level the building stands on; the native Placement z is its layer 0
        # (surface - BaseZ), as tools/all_buildings_sites.json records for the in-game placements.
        info['nativePlacement'] = [site['x'], site['y'], site['z'] - blocks.base_z]
    info['routeFromStart'], info['bridgeCells'] = route_to(model, cells)
    if info['routeFromStart'] is None:
        problems.append('no route from the start')
    return problems, info, cells


def check_sites(model, catalog, variant, records, placed, placed_columns, requirements):
    """Validate every listed site against its building's placement rule. Returns (reports, claimed, errors)."""
    errors, reports = [], []
    required = required_site_templates(catalog, requirements)
    claimed = {}
    for site in variant['sites']:
        template = site.get('template')
        if template not in required:
            fail(f'{variant["id"]} site {site.get("label")}: {template} is not a building of '
                 f'{BUILDING_COLLECTION.name} that needs a site')
        rule = required[template]
        keys = set(site)
        missing = SITE_KEYS[rule] - keys
        unknown = keys - SITE_KEYS[rule] - OPTIONAL_SITE_KEYS
        if missing or unknown:
            fail(f'{variant["id"]} site {site["label"]} ({rule}): missing {sorted(missing)}, unknown {sorted(unknown)}')
        problems, info, cells = check_site(model, catalog, site, records, placed, placed_columns, requirements, rule)
        info['problems'] = problems
        info['_cells'] = cells
        reports.append(info)
    # Primary sites (not "alternative", not dam sites) must not overlap each
    # other, and no primary footprint may cover another site's door approach.
    for info in reports:
        if info['alternative'] or info['rule'] == 'hydro':
            continue
        label = f'{info["template"]} {info["label"]}'
        for cell in sorted(info['_cells']):
            if cell in claimed:
                info['problems'].append(f'overlaps {claimed[cell]} at {cell}')
                break
        for cell in info['_cells']:
            claimed.setdefault(cell, label)
    for info in reports:
        if info.get('door') and not info['alternative']:
            owner = claimed.get(tuple(info['door'][:2]))
            if owner and owner != f'{info["template"]} {info["label"]}':
                info['problems'].append(f'door approach {info["door"]} is inside {owner}')
    # A listed open side stays open: no other primary footprint inside its margin strip.
    for site, info in zip(variant['sites'], reports):
        if info['rule'] in ('hydro', 'waterDepth', 'waterInput'):
            continue
        own = f'{info["template"]} {info["label"]}'
        strips = side_strips(info['_cells'], site['margin'])
        for side in site['openSides']:
            owners = sorted({claimed[c] for c in strips[side] if c in claimed and claimed[c] != own})
            if owners:
                info['problems'].append(f'open side {side} margin is inside {", ".join(owners)}')
    # Pits: deposits in range, around every other claimed footprint.
    for site, info in zip(variant['sites'], reports):
        if info['rule'] != 'pit':
            continue
        blueprint = catalog.get(site['template'])
        group = blueprint['YieldRemovingBuildingSpec']['ResourceGroup']
        deposits = [r for r in records if 'MineralDepositSpec' in r['blueprint']
                    and r['blueprint']['MineralDepositSpec']['Yielder']['ResourceGroup'] == group]
        own = f'{info["template"]} {info["label"]}'
        blocked = {cell for cell, owner in claimed.items() if owner != own} | set(info['_cells'])
        blocked |= set(placed_columns)
        reached = pit_reach(model, building_blocks(catalog, site['template']), site, deposits, blocked)
        info['good'] = blueprint['MineralPitSpec']['GoodId']
        info['depositsInRange'] = [{'label': r['placement']['label'], 'steps': steps,
                                    'yield': r['blueprint']['MineralDepositSpec']['Yielder']['Yield']['Amount']}
                                   for r, steps in reached]
        info['yieldInRange'] = sum(d['yield'] for d in info['depositsInRange'])
        if not reached:
            info['problems'].append(f'no {group} deposit within {RESOURCE_BUILDING_RANGE} steps of the door')
    for info in reports:
        errors += [f'site {info["label"]} ({info["template"]}): {p}' for p in info['problems']]
    return reports, claimed, errors


def tree_counts(model, catalog, near):
    """(trees, resin trees) whose cell is in `near`."""
    trees = resin = 0
    for record in model.objects:
        if not record['natural']:
            continue
        x, y, _ = record['coordinates']
        if not (0 <= x < model.sx and 0 <= y < model.sy) or not near[y, x]:
            continue
        blueprint = catalog.get(record['template'])
        if 'TreeComponentSpec' not in blueprint:
            continue
        trees += 1
        if blueprint.get('GatherableSpec', {}).get('Yielder', {}).get('Yield', {}).get('Id') == 'PineResin':
            resin += 1
    return trees, resin


def shore_banks(model, spec):
    """Bank cells that satisfy ShoreFishing.Suitable on the saved water: the bank is dry and free; the
    neighbouring cell one layer down holds clean water at least MinimumDepth deep whose surface is
    within MaximumReachDown below the bank and at most 0.1 above it."""
    banks = set()
    depth, contamination, height = model.water_depth, model.water_contamination, model.height
    wet_y, wet_x = np.nonzero((depth >= spec['MinimumDepth']) & (contamination <= spec['MaximumContamination']))
    for wy, wx in zip(wet_y.tolist(), wet_x.tolist()):
        surface = float(height[wy, wx] + depth[wy, wx])
        for x, y in ((wx + 1, wy), (wx - 1, wy), (wx, wy + 1), (wx, wy - 1)):
            if not (0 <= x < model.sx and 0 <= y < model.sy):
                continue
            if model.water_any[y, x] > 0 or model.hard_mask[y, x] or not model.contiguous[y, x]:
                continue
            bank = int(height[y, x])
            if height[wy, wx] <= bank - 1 and bank - spec['MaximumReachDown'] <= surface <= bank + 0.10:
                banks.add((x, y))
    return banks


def start_resources(model, catalog, requirements):
    """Start-game resources measured on the source map (saved terrain, water and entities)."""
    length, bridges = model.route()
    near = (length >= 0) & (length <= requirements['startRoute']) & (bridges == 0)
    clean_wet = (model.water_depth > 0) & (model.water_contamination < 0.5)
    bad_wet = (model.water_depth > 0) & (model.water_contamination >= 0.5)
    clean_distance = model.water_distance()
    trees, resin = tree_counts(model, catalog, near)
    fields = near & model.dry() & ~model.hard_mask & ~model.natural_mask & model.contiguous \
        & (clean_distance >= 0) & (clean_distance <= requirements['fieldWaterReach'])
    spec = read_json(GATHERER_FLAG_PATCH)['ShoreFishingSpec']
    banks = shore_banks(model, spec)
    shore_near = [b for b in banks if 0 <= length[b[1], b[0]] <= requirements['shoreRoute']]
    shore_reachable = sorted((int(bridges[y, x]), int(length[y, x])) for x, y in banks if length[y, x] >= 0)
    labels = wet_components(model)
    strength = source_strength_by_component(model, catalog)

    def nearest(mask):
        best = None
        for y, x in zip(*np.nonzero(mask)):
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < model.sx and 0 <= ny < model.sy and model.water_any[ny, nx] == 0 and length[ny, nx] >= 0:
                    key = (int(bridges[ny, nx]), int(length[ny, nx]))
                    best = key if best is None or key < best else best
        return None if best is None else {'route': best[1], 'bridgeCells': best[0]}

    fed = [label for label, value in strength.items() if value > 0]
    fed_clean = clean_wet & np.isin(labels, fed)
    underground, ruin_scrap = [], 0
    for record in model.objects:
        blueprint = catalog.get(record['template'])
        if 'RuinSpec' in blueprint:
            ruin_scrap += blueprint['RuinSpec']['Yielder']['Yield']['Amount']
        if record['template'] == 'UndergroundRuins':
            cells = footprint(Blocks(blueprint['BlockObjectSpec']), record['coordinates'], record['orientation'])
            route, bridge_cells = route_to(model, cells)
            underground.append({'at': list(record['coordinates']), 'routeFromStart': route, 'bridgeCells': bridge_cells})
    return {
        'start': list(model.start),
        'cleanSourceStrength': round(sum(s[2] for s in water_source_cells(model, catalog, badwater=False)), 3),
        'badwaterSourceStrength': round(sum(s[2] for s in water_source_cells(model, catalog, badwater=True)), 3),
        'sourceFedCleanCells': int(fed_clean.sum()),
        'cleanWaterNearest': nearest(fed_clean),
        'badwaterNearest': nearest(bad_wet),
        'treesNearStart': trees, 'pinesNearStart': resin,
        'fieldCellsNearStart': int(fields.sum()),
        'shoreBanks': len(banks), 'shoreBanksNearStart': len(shore_near), 'shoreBanksReachable': len(shore_reachable),
        'shoreNearest': {'route': shore_reachable[0][1], 'bridgeCells': shore_reachable[0][0]} if shore_reachable else None,
        'ruinScrap': ruin_scrap, 'undergroundRuins': underground,
    }


class ProgramModel:
    """Raw materials of goods and buildings, expanded along tools/map_loop_requirements.json recipeChoices."""

    def __init__(self, catalog, requirements):
        self.catalog = catalog
        self.raw = set(requirements['rawGoods'])
        self.choice = requirements['recipeChoices']
        self.recipes = {}
        with zipfile.ZipFile(BLUEPRINTS_ZIP) as archive:
            for name in archive.namelist():
                if name.startswith('Recipes/') and name.endswith('.json'):
                    spec = read_json(archive.read(name)).get('RecipeSpec')
                    if spec:
                        self.recipes[spec['Id']] = spec
        for path in (MOD_DATA / 'Recipes').rglob('*.json'):
            spec = read_json(path).get('RecipeSpec')
            if spec:
                self.recipes[spec['Id']] = spec
        for good, recipe in self.choice.items():
            if recipe not in self.recipes:
                fail(f'{LOOP_REQUIREMENTS}: recipeChoices {good} -> {recipe} is not a recipe')

    def expand(self, goods, totals=None, depth=0):
        totals = {} if totals is None else totals
        if depth > 40:
            fail(f'Recipe expansion of {goods} does not terminate')
        for good, amount in goods:
            if good in self.raw:
                totals[good] = totals.get(good, 0) + amount
                continue
            if good not in self.choice:
                fail(f'{LOOP_REQUIREMENTS}: {good} is neither in rawGoods nor in recipeChoices')
            recipe = self.recipes[self.choice[good]]
            made = sum(p['Amount'] for p in recipe['Products'] if p['Id'] == good)
            if not made:
                fail(f'recipe {recipe["Id"]} does not produce {good}')
            cycles = amount / made
            self.expand([(i['Id'], i['Amount'] * cycles) for i in recipe['Ingredients']], totals, depth + 1)
            if recipe.get('Fuel'):
                self.expand([(recipe['Fuel'], cycles / max(recipe['CyclesFuelLasts'], 1))], totals, depth + 1)
        return totals

    def building_cost(self, templates):
        goods = []
        for template in templates:
            goods += [(c['Id'], c['Amount']) for c in self.catalog.get(template)['BuildingSpec']['BuildingCost']]
        return self.expand(goods)

    def missions(self):
        pads = [t for t in self.catalog.building_collection if 'RocketLaunchPadSpec' in self.catalog.get(t)]
        if len(pads) != 1:
            fail(f'Expected one building with RocketLaunchPadSpec, found {pads}')
        return [(m['Id'], self.recipes[m['RecipeId']]) for m in self.catalog.get(pads[0])['RocketLaunchPadSpec']['Missions']]

    def products(self, template):
        return {p['Id'] for rid in self.catalog.get(template).get('ManufactorySpec', {}).get('ProductionRecipeIds', [])
                for p in self.recipes[rid]['Products']}


def rounded(totals):
    return {k: int(round(v)) for k, v in sorted(totals.items()) if round(v)}


def narrative_cache_count():
    settings = read_json(NARRATIVE_SETTINGS)['NarrativeSettingsSpec']
    amounts = [r['Amount'] for entry in settings['Stages'] + settings['Discoveries'] for r in entry['Requirements']
               if r['Kind'] == 'CachesSurveyed']
    return max(amounts) if amounts else 0


def cache_coverage(catalog, records, sites, reports):
    """Each Human Record Cache needs a checked site of a building that runs the survey recipe (the
    Archive Excavation) with an occupied cell within SurveyRadius tiles (Chebyshev) and layers."""
    spec = catalog.get(RECORD_CACHE_TEMPLATE)['HumanRecordCacheSpec']
    radius = spec['SurveyRadius']
    surveyors = []
    for site, info in zip(sites, reports):
        blueprint = catalog.get(site['template'])
        if spec['SurveyRecipeId'] in blueprint.get('ManufactorySpec', {}).get('ProductionRecipeIds', []) and not info['problems']:
            blocks = building_blocks(catalog, site['template'])
            surveyors.append((site['label'], blocks.occupied_cells((site['x'], site['y'], site['z']), site['orientation'])))
    result = []
    for record in records:
        if record['template'] != RECORD_CACHE_TEMPLATE:
            continue
        cells = record['blocks'].occupied_cells(record['coordinates'], record['orientation'])
        covered = []
        for label, others in surveyors:
            d = min((max(abs(ox - cx), abs(oy - cy)) for ox, oy, oz in others for cx, cy, cz in cells
                     if abs(oz - cz) <= radius), default=None)
            if d is not None and d <= radius:
                covered.append({'site': label, 'distance': d})
        result.append({'label': record['placement']['label'], 'at': list(record['coordinates']),
                       'surveyedFrom': covered, 'ok': record['ok'] and bool(covered)})
    return result, radius


def site_stage(program, catalog, template):
    """Loop stage a building's site belongs to, from its blueprint and recipe products."""
    blueprint = catalog.get(template)
    products = program.products(template)
    if any(s in blueprint for s in ('WorkshopPoweredGeneratorSpec', 'GoodPoweredGeneratorSpec', 'HydroTurbineSpec')):
        return 'power'
    if 'UnderstructureConstraintSpec' in blueprint or 'MineralPitSpec' in blueprint:
        return 'deepIndustry' if 'DeepOre' in products else 'construction'
    if any(s in blueprint for s in ('RocketLaunchPadSpec', 'RocketMissionControlSpec', 'CryogenicTankSpec')) \
            or products & {'LiquidHydrogen', 'HydrogenGas', 'RocketAirframe', 'PureWater'}:
        return 'rocket'
    if any(s in blueprint for s in ('MapEdgeSiteSpec', 'WaterInputSpec', 'WasteLeakSpec', 'ReactorMeltdownSpec')) \
            or products & {'Yellowcake', 'EnrichedFuel', 'RecoveredMinerals'}:
        return 'nuclear'
    if catalog.get(RECORD_CACHE_TEMPLATE)['HumanRecordCacheSpec']['SurveyRecipeId'] in \
            blueprint.get('ManufactorySpec', {}).get('ProductionRecipeIds', []):
        return 'narrative'
    if products & {'DeepOre', 'DeepAlloy', 'HighGradeSteel', 'Alloy', 'MachineCore', 'Coal', 'CrudeOil'}:
        return 'deepIndustry'
    return 'space'


def loop_coverage(model, catalog, variant, records, site_reports, requirements):
    """Per-stage map provisions of the full game loop. Returns (report, errors)."""
    items = []

    def need(stage, item, ok, detail):
        items.append({'stage': stage, 'item': item, 'ok': bool(ok), 'detail': detail})

    program = ProgramModel(catalog, requirements)
    required = required_site_templates(catalog, requirements)
    good_sites = {}
    for info in site_reports:
        if not info['problems'] and not info['alternative']:
            good_sites.setdefault(info['template'], []).append(info)
    resources = start_resources(model, catalog, requirements)
    templates = [t for t in catalog.building_collection if not catalog.building_collection[t].startswith('Buildings/Platforms/')
                 and 'BuildingSpec' in catalog.get(t)]
    construction = program.building_cost(templates)

    # 1. Start-game resources
    need('start', 'clean water', resources['cleanWaterNearest'] is not None and resources['cleanSourceStrength'] > 0,
         f'clean source strength {resources["cleanSourceStrength"]}; nearest source-fed clean water {resources["cleanWaterNearest"]}')
    need('start', 'badwater (Extract, Explosives, Chemical)',
         resources['badwaterNearest'] is not None and resources['badwaterSourceStrength'] > 0,
         f'badwater source strength {resources["badwaterSourceStrength"]}; nearest badwater {resources["badwaterNearest"]}')
    need('start', 'trees near the start', resources['treesNearStart'] >= requirements['minTreesNearStart'],
         f'{resources["treesNearStart"]} trees within route {requirements["startRoute"]} (min {requirements["minTreesNearStart"]})')
    need('start', 'pines (resin) near the start', resources['pinesNearStart'] >= requirements['minPinesNearStart'],
         f'{resources["pinesNearStart"]} pines (min {requirements["minPinesNearStart"]})')
    need('start', 'irrigated farmland near the start', resources['fieldCellsNearStart'] >= requirements['minFieldCellsNearStart'],
         f'{resources["fieldCellsNearStart"]} cells within {requirements["fieldWaterReach"]} of clean water '
         f'(min {requirements["minFieldCellsNearStart"]})')
    need('start', 'shore fishing banks (first FreshFish)', resources['shoreBanksReachable'] >= requirements['minShoreBanks'],
         f'{resources["shoreBanksReachable"]} reachable banks (min {requirements["minShoreBanks"]}), {resources["shoreBanksNearStart"]} '
         f'within route {requirements["shoreRoute"]}; nearest {resources["shoreNearest"]}')

    # 2. Construction materials: pit deposits cover every building up to the permanent quarry
    for template, rule in sorted(required.items()):
        if rule != 'pit':
            continue
        good = catalog.get(template)['MineralPitSpec']['GoodId']
        permanent = [t for t in templates if good in program.products(t)]
        science = max((catalog.get(t)['BuildingSpec']['ScienceCost'] for t in permanent), default=None)
        before = [t for t in templates if science is not None and catalog.get(t)['BuildingSpec']['ScienceCost'] <= science]
        threshold = int(round(program.building_cost(before).get(good, 0)))
        in_range = sum(info.get('yieldInRange', 0) for info in good_sites.get(template, []))
        need('construction', f'{good} deposits in range of a {template} site', in_range > 0 and in_range >= threshold,
             f'{in_range} {good} in range; buildings up to the permanent {", ".join(permanent)} ({science} science) need {threshold}')

    # 3. Metal and deep industry
    sources = [r for r in records if r['template'] == 'DeepOreSource' and r['ok']]
    finite = sum(r['placement']['amount'] for r in sources)
    need('deepIndustry', 'finite deep ore covers one of each building', finite >= construction.get('DeepOre', 0),
         f'{finite} DeepOre in {len(sources)} sources; one of each collection building needs {int(round(construction.get("DeepOre", 0)))}')
    drill_sites = good_sites.get('DeepDrill.IronTeeth', [])
    near_source = [info for info in drill_sites if any(
        abs(r['coordinates'][0] - info['at'][0]) + abs(r['coordinates'][1] - info['at'][1]) <= 25 for r in sources)]
    need('deepIndustry', 'Deep Drill sites beside Deep Ore Sources', len(near_source) >= requirements['minDrillSites'],
         f'{len(near_source)} checked drill sites within 25 cells of a source (min {requirements["minDrillSites"]})')
    reachable_ruins = [u for u in resources['undergroundRuins'] if u['routeFromStart'] is not None]
    need('deepIndustry', 'renewable scrap (Underground Ruins for the Efficient Mine)',
         len(reachable_ruins) >= requirements['minUndergroundRuinsReachable'],
         f'{len(reachable_ruins)} reachable Underground Ruins; ruins hold {resources["ruinScrap"]} scrap, one of each building '
         f'needs {int(round(construction.get("ScrapMetal", 0)))}')

    # Every building that needs a site has a checked one (understructures: the policy minimum).
    for template, rule in sorted(required.items()):
        count = len(good_sites.get(template, []))
        minimum = 1
        if rule == 'understructure' and 'DeepOreVein' in catalog.get(template)['UnderstructureConstraintSpec']['UnderstructureTemplateNames']:
            minimum = requirements['minVeinsWithMineSite']
        need(site_stage(program, catalog, template), f'{template} site ({rule})', count >= minimum,
             f'{count} checked sites (min {minimum})')

    # Narrative: a surveyable cache for every CachesSurveyed discovery
    caches, radius = cache_coverage(catalog, records, variant['sites'], site_reports)
    wanted = narrative_cache_count()
    good_caches = [c for c in caches if c['ok']]
    need('narrative', 'Human Record Caches in survey range of an Archive Excavation site', len(good_caches) >= wanted,
         f'{len(good_caches)} of {len(caches)} caches surveyable (radius {radius}); the journal counts up to {wanted}')

    # Nuclear: the hard variant's spring
    if variant['hardVariant']:
        springs = [r for r in records if 'RadioactiveWaterSourceSpec' in r['blueprint']]
        need('nuclear', 'Radioactive Spring (hard variant)', springs and all(r['ok'] for r in springs), f'{len(springs)} springs')

    # Rocket program: raw materials of every mission (reported) and clean water
    missions = {mid: rounded(program.expand([(i['Id'], i['Amount']) for i in recipe['Ingredients']]))
                for mid, recipe in program.missions()}
    total = {}
    for values in missions.values():
        for k, v in values.items():
            total[k] = total.get(k, 0) + v
    need('rocket', 'source-fed clean water for treatment, electrolysis and liquefaction', resources['sourceFedCleanCells'] > 0,
         f'{resources["sourceFedCleanCells"]} source-fed clean water cells; the missions need {total.get("Water", 0)} Water')

    errors = [f'loop coverage [{i["stage"]}] {i["item"]}: {i["detail"]}' for i in items if not i['ok']]
    stages = [{'id': sid, 'title': title, 'ok': all(i['ok'] for i in items if i['stage'] == sid),
               'items': [i for i in items if i['stage'] == sid]} for sid, title in LOOP_STAGES]
    report = {'stages': stages, 'startResources': resources, 'caches': caches,
              'program': {'missions': missions, 'allMissions': total, 'oneOfEachBuilding': rounded(construction),
                          'finiteDeepOre': finite}}
    return report, errors


def validate_variant(variant, catalog, source_entries, output_entries):
    """Static validation of a written variant. Returns (report, errors)."""
    errors = []
    report = {'variant': variant['id'], 'output': str(output_path(variant))}
    source = MapModel(source_entries, catalog)
    out_world = json.loads(output_entries['world.json'])
    out_meta = json.loads(output_entries['map_metadata.json'])
    src_world = source.world
    # versions and unchanged singletons
    if output_entries['version.txt'] != source_entries['version.txt']:
        errors.append('version.txt differs from the source map')
    if out_world['GameVersion'] != src_world['GameVersion']:
        errors.append(f'GameVersion {out_world["GameVersion"]} != source {src_world["GameVersion"]}')
    report['version'] = {'version.txt': source.version, 'GameVersion': src_world['GameVersion']}
    for key, value in src_world['Singletons'].items():
        if out_world['Singletons'].get(key) != value:
            errors.append(f'Singleton {key} differs from the source map')
    if set(out_world['Singletons']) != set(src_world['Singletons']):
        errors.append('Singleton set differs from the source map')
    # Every water source must carry exactly the fields native WaterSource.Load
    # reads (as the source map's own sources do); a missing one aborts loading.
    native_fields = {'SpecifiedStrength', 'CurrentStrength'}
    for entity in out_world['Entities']:
        fields = entity.get('Components', {}).get('WaterSource')
        if fields is not None and set(fields) != native_fields:
            errors.append(f'{entity["Template"]} {entity["Id"]}: WaterSource saves {sorted(fields)}, native needs {sorted(native_fields)}')
    if output_entries['map_thumbnail.jpg'] != source_entries['map_thumbnail.jpg']:
        errors.append('Thumbnail differs from the source map')
    # metadata
    expected_meta = {'Width': source.sx, 'Height': source.sy, 'MapNameLocKey': '', 'MapDescriptionLocKey': '',
                     'MapDescription': compose_description(variant), 'IsRecommended': False,
                     'IsUnconventional': False, 'IsDev': False}
    if out_meta != expected_meta:
        errors.append(f'map_metadata.json {out_meta} != {expected_meta}')
    if not variant['output']['name'].startswith('Deep Frontier - '):
        errors.append('Output name must start with "Deep Frontier - "')
    manifest, names = required_mod_names()
    for name in [manifest['Name']] + names:
        if name not in out_meta.get('MapDescription', ''):
            errors.append(f'Description does not mention required mod {name}')
    report['description'] = out_meta.get('MapDescription')
    # entity accounting
    out_ids = [e['Id'] for e in out_world['Entities']]
    if len(set(out_ids)) != len(out_ids):
        errors.append('Duplicate entity ids in the output')
    source_by_id = {e['Id']: e for e in src_world['Entities']}
    removed_ids = set(source_by_id) - set(out_ids)
    added = [e for e in out_world['Entities'] if e['Id'] not in source_by_id]
    for entity in out_world['Entities']:
        if entity['Id'] in source_by_id and entity != source_by_id[entity['Id']]:
            errors.append(f'Source entity {entity["Id"]} was modified')
    if removed_ids:
        errors.append(f'{len(removed_ids)} source entities are missing from the output')
    head = entity_array_head(source_entries['world.json'])
    if not output_entries['world.json'].startswith(head):
        errors.append('Output world.json does not keep the source bytes up to the end of the source entities')
    report['sourceBytesPreserved'] = output_entries['world.json'].startswith(head)
    if len(added) != len(variant['placements']):
        errors.append(f'{len(added)} added entities for {len(variant["placements"])} placements')
    # placements against the source terrain, water and entities
    placed = {}
    placed_columns = {}
    placement_reports = []
    records = []
    for entity, placement in zip(added, variant['placements']):
        template = entity['Template']
        problems = []
        if template != placement['template']:
            problems.append(f'entity template {template} != placement {placement["template"]}')
        if template not in catalog.map_editor_common:
            problems.append(f'{template} is not in TemplateCollection.MapEditor.Common')
        blueprint = catalog.get(template)
        blocks = Blocks(blueprint['BlockObjectSpec'])
        c = entity['Components']['BlockObject']['Coordinates']
        coordinates = (c['X'], c['Y'], c['Z'])
        orientation = entity['Components']['BlockObject'].get('Orientation', 'Cw0')
        problems += check_object(source, blocks, coordinates, orientation, False, placed, blueprint)
        label = f'{template}@{coordinates}'
        for x, y, z, block in blocks.positioned(coordinates, orientation):
            if occupied(block):
                placed.setdefault((x, y, z), []).append(label)
                placed_columns[(x, y)] = label
            if block['OccupyAllBelow']:
                for bz in range(z - 1, -1, -1):
                    placed.setdefault((x, y, bz), []).append(label)
        info = {'template': template, 'label': placement['label'], 'at': list(coordinates),
                'orientation': orientation}
        if 'StockpileSpec' in blueprint:
            spec = blueprint['StockpileSpec']
            good = good_spec(placement['good'])
            if good['GoodType'] != spec['WhitelistedGoodType']:
                problems.append(f'good {good["Id"]} type {good["GoodType"]} != {spec["WhitelistedGoodType"]}')
            if not 0 < placement['amount'] <= spec['MaxCapacity']:
                problems.append(f'amount {placement["amount"]} outside 1..{spec["MaxCapacity"]}')
            if template == 'DeepOreSource' and placement['good'] not in deep_drill_inputs(catalog):
                problems.append(f'good {placement["good"]} is not consumed by a DeepDrill recipe {sorted(deep_drill_inputs(catalog))}')
            entrance = blocks.entrance_cell(coordinates, orientation)
            ex, ey, ez = entrance
            if not (0 <= ex < source.sx and 0 <= ey < source.sy) or source.height[ey, ex] != ez \
                    or source.water_any[ey, ex] > 0 or source.hard_mask[ey, ex] or (ex, ey) in placed_columns:
                problems.append(f'stockpile entrance {entrance} is not dry free ground at its level')
            info.update(good=placement['good'], amount=placement['amount'], entrance=list(entrance))
        if 'RadioactiveWaterSourceSpec' in blueprint:
            if not variant['hardVariant']:
                problems.append('RadioactiveSpringSource placed in a variant not marked hardVariant')
            if not placement['radioactivePerHour'] > 0:
                problems.append(f'radioactivePerHour {placement["radioactivePerHour"]} must be positive')
            info['radioactivePerHour'] = placement['radioactivePerHour']
            info['nativeStrength'] = placement['radioactivePerHour'] / water_per_strength_hour()
            # The hard variant's spring must seep into a river: a wet cell within
            # two cells whose bed is not above the spring.
            x, y, z = coordinates
            wet = [(abs(wx - x) + abs(wy - y), int(source.height[wy, wx]))
                   for wx in range(x - 2, x + 3) for wy in range(y - 2, y + 3)
                   if 0 <= wx < source.sx and 0 <= wy < source.sy and source.water_depth[wy, wx] > 0]
            downhill = [d for d, bed in wet if bed <= z]
            info['nearestRiverCell'] = min(downhill) if downhill else None
            if not downhill:
                problems.append('spring is not next to a river cell at or below its level')
        if 'MineralDepositSpec' in blueprint:
            yielder = blueprint['MineralDepositSpec']['Yielder']
            info.update(good=yielder['Yield']['Id'], amount=yielder['Yield']['Amount'], resourceGroup=yielder['ResourceGroup'])
        cells = footprint(blocks, coordinates, orientation)
        info['routeFromStart'], info['bridgeCells'] = route_to(source, cells)
        if 'RadioactiveWaterSourceSpec' not in blueprint and info['routeFromStart'] is None:
            problems.append('no route from the starting location')
        if 'RadioactiveWaterSourceSpec' not in blueprint:
            info['freeboard'] = freeboard(source, cells, coordinates[2])
        info['problems'] = problems
        errors += [f'{label}: {p}' for p in problems]
        placement_reports.append(info)
        records.append({'placement': placement, 'template': template, 'blueprint': blueprint, 'blocks': blocks,
                        'coordinates': coordinates, 'orientation': orientation, 'cells': cells, 'ok': not problems})
    report['placements'] = placement_reports
    if variant['hardVariant'] and not any(p['template'] == 'RadioactiveSpringSource' for p in variant['placements']):
        errors.append('hardVariant without a RadioactiveSpringSource')
    if not variant['hardVariant'] and any(p['template'] == 'RadioactiveSpringSource' for p in variant['placements']):
        errors.append('default variant contains a RadioactiveSpringSource')
    # Sites of every building that needs one, then the full-loop coverage.
    requirements = load_loop_requirements()
    site_reports, claimed, site_errors = check_sites(source, catalog, variant, records, placed, placed_columns, requirements)
    errors += site_errors
    coverage, coverage_errors = loop_coverage(source, catalog, variant, records, site_reports, requirements)
    errors += coverage_errors
    report['sites'] = [{k: v for k, v in info.items() if k != '_cells'} for info in site_reports]
    report['loopCoverage'] = coverage
    expected_height = {'X': variant['height']['terrainLayers'], 'Y': variant['height']['totalHeight']}
    if out_world['Singletons']['MapSize'].get('MapHeight') != expected_height:
        errors.append(f'MapHeight {out_world["Singletons"]["MapSize"].get("MapHeight")} != {expected_height}')
    if source.layers != source.terrain_layers:
        errors.append(f'{source.layers} stored terrain layers != MapHeight terrain {source.terrain_layers}')
    report['zBudget'] = {'terrainLayers': source.terrain_layers, 'totalHeight': source.total_height,
                         'source': source.height_source, 'maxTerrainHeight': int(source.height.max())}
    report['errors'] = errors
    return report, errors


def build(variant_paths, catalog, out_dir=None, write=True):
    results = []
    for variant_path in variant_paths:
        variant = load_variant(variant_path)
        data, source_entries = load_source(variant['source'])
        digest = hashlib.sha256(data).hexdigest()
        if digest != variant['sourceSha256']:
            fail(f'{variant["id"]}: source sha256 {digest} != recorded {variant["sourceSha256"]}')
        height = variant['height']
        source_entries = resize_height(source_entries, height['terrainLayers'], height['totalHeight'])
        destination = output_path(variant) if out_dir is None else Path(out_dir) / output_path(variant).name
        if write:
            write_timber(apply_variant(variant, source_entries, catalog), destination)
        if not destination.is_file():
            fail(f'{destination} does not exist; run build first')
        written = read_zip_bytes(destination.read_bytes())
        report, errors = validate_variant(variant, catalog, source_entries, written)
        report['output'] = str(destination)
        report['sourceSha256'] = digest
        report['outputSha256'] = hashlib.sha256(destination.read_bytes()).hexdigest()
        evidence = ROOT / 'outputs/maps' / f'{variant["id"]}-validation.json'
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(json.dumps(report, indent=1, default=list), encoding='utf-8')
        model = MapModel(written, catalog)
        marks, legend = preview_marks(variant, catalog, report)
        render_preview(model, ROOT / 'outputs/maps' / f'{variant["id"]}-preview.png', marks, legend)
        status = 'OK' if not errors else f'{len(errors)} ERRORS'
        print(f'{variant["id"]}: {status} -> {destination}')
        for error in errors[:40]:
            print('  ', error)
        results.append((variant, report, errors))
    return results


# ---------------------------------------------------------------- suggest

def core_cells(blocks):
    """Local (x, y) of the ground-core blocks that must sit over an understructure."""
    sx, sy, _ = blocks.size
    return [(x, y) for y in range(sy) for x in range(sx)
            if blocks.block(x, y, 0)['MatterBelow'] == 'Ground' and blocks.block(x, y, 0)['Occupations'] == 'Top']


def mine_coordinates(blocks, vein_xy, level, orientation):
    """Coordinates that put the DeepMine ground core exactly over a 5x5 vein at vein_xy."""
    points = [blocks.transform(c, (0, 0), orientation, False) for c in core_cells(blocks)]
    return vein_xy[0] - min(p[0] for p in points), vein_xy[1] - min(p[1] for p in points), level


def freeboard(model, cells, level, radius=4):
    """Level minus the highest wet river/lake surface within radius (None if no water nearby)."""
    beds = []
    for x, y in ring(cells, radius) | set(cells):
        if 0 <= x < model.sx and 0 <= y < model.sy and model.water_any[y, x] > 0:
            beds.append(float(model.height[y, x] + model.water_depth[y, x]))
    return None if not beds else round(level - max(beds), 2)


def building_site_ok(model, blocks, coordinates, orientation, margin, blocked_columns=frozenset()):
    """(ok, info) for a building resting on terrain at coordinates[2]."""
    level = coordinates[2]
    cells = {(x, y) for x, y, z, b in blocks.positioned(coordinates, orientation)}
    problems, trees = site_problems(model, cells, level, blocked_columns)
    if problems:
        return False, None
    margin_cells = ring(cells, margin) if margin else set()
    margin_problems, _ = site_problems(model, margin_cells, level, blocked_columns)
    entrance = blocks.entrance_cell(coordinates, orientation)
    if entrance is not None:
        ex, ey, _ = entrance
        entrance_problems, _ = site_problems(model, {(ex, ey)}, level, blocked_columns)
        if entrance_problems:
            return False, None
    water = model.water_distance()
    border = [(x, y) for x, y in ring(cells, 1) if 0 <= x < model.sx and 0 <= y < model.sy]
    route, bridge_cells = route_to(model, cells)
    wd = [int(water[y, x]) for x, y in border if water[y, x] >= 0]
    sx, sy, _ = model.start
    cx = sum(x for x, _ in cells) / len(cells)
    cy = sum(y for _, y in cells) / len(cells)
    return True, {'trees': trees, 'marginProblems': len(margin_problems), 'walk': route, 'bridges': bridge_cells,
                  'water': min(wd) if wd else None, 'straight': round(((cx - sx) ** 2 + (cy - sy) ** 2) ** 0.5),
                  'freeboard': freeboard(model, cells, level), 'cells': cells}


def _window(arr, w, h, op):
    from numpy.lib.stride_tricks import sliding_window_view
    a = getattr(sliding_window_view(arr, w, axis=1), op)(axis=2)
    return getattr(sliding_window_view(a, h, axis=0), op)(axis=2)


def rect_candidates(model, w, h, max_level, margin):
    """Vectorised scan: (x, y, level, margin_bad, water, walk, trees) for flat w x h rectangles."""
    big = 10 ** 6
    base = model.dry() & ~model.hard_mask & model.contiguous
    water = np.where(model.water_distance() >= 0, model.water_distance(), big)
    walk = np.where(model.walk_distance() >= 0, model.walk_distance(), big)
    water_min = _window(np.pad(water, 1, constant_values=big), w + 2, h + 2, 'min')
    walk_min = _window(np.pad(walk, 1, constant_values=big), w + 2, h + 2, 'min')
    trees = _window(model.natural_mask.astype(np.int32), w, h, 'sum')
    result = []
    for level in sorted(set(model.height.flatten().tolist())):
        if not 0 < level <= max_level:
            continue
        good = (base & (model.height == level)).astype(np.int32)
        inner = _window(good, w, h, 'sum')
        outer = _window(np.pad(good, margin), w + 2 * margin, h + 2 * margin, 'sum')
        ys, xs = np.nonzero(inner == w * h)
        for y, x in zip(ys.tolist(), xs.tolist()):
            result.append((x, y, level, int((w + 2 * margin) * (h + 2 * margin) - outer[y, x]),
                           int(water_min[y, x]), int(walk_min[y, x]), int(trees[y, x])))
    return result


def spread(items, key_xy, distance, count):
    picked = []
    for item in items:
        x, y = key_xy(item)
        if all(abs(x - px) > distance or abs(y - py) > distance for px, py in (key_xy(p) for p in picked)):
            picked.append(item)
        if len(picked) >= count:
            break
    return picked


def suggest(model, catalog, png=None, limit=10):
    cache = {}
    names = ('NuclearReactor', 'LaunchPad', 'DeepMine', 'DeepDrill')
    blocks = {name: building_blocks(catalog, name + '.IronTeeth') for name in names}
    limits = {name: model.total_height - 1 - blocks[name].top_occupied_layer() for name in names}
    print('max base level per building:', limits)
    sx, sy, _ = model.start
    candidates = {}
    for name, margin in (('NuclearReactor', 2), ('LaunchPad', 2), ('DeepDrill', 1)):
        b = blocks[name]
        found = []
        for orientation in ORIENTATIONS:
            w, h = (b.size[0], b.size[1]) if orientation in ('Cw0', 'Cw180') else (b.size[1], b.size[0])
            local = {(cx, cy) for cx, cy, cz, _ in b.positioned((0, 0, 0), orientation)}
            ox, oy = min(p[0] for p in local), min(p[1] for p in local)
            for x, y, level, margin_bad, water, walk, trees in rect_candidates(model, w, h, limits[name], margin):
                if walk >= 10 ** 6:
                    continue
                found.append(((x - ox, y - oy, level), orientation, margin_bad, water, walk, trees, (x, y)))
        found.sort(key=lambda r: (r[2] > 12, r[3], r[2], r[5]))
        picked = []
        for cand in spread(found, lambda r: r[6], 16, 4 * limit):
            ok, info = building_site_ok(model, b, cand[0], cand[1], margin)
            if ok:
                picked.append((cand[0], cand[1], info))
            if len(picked) >= limit:
                break
        candidates[name] = picked
        print(f'{name}: {len(found)} flat placements (margin {margin})')
        for coordinates, orientation, info in picked:
            print(f'   at {coordinates} {orientation} water {info["water"]} margin-bad {info["marginProblems"]} '
                  f'trees {info["trees"]} walk {info["walk"]} straight {info["straight"]} freeboard {info["freeboard"]}')
    # Veins: a tree-free flat 5x5 whose DeepMine footprint (any orientation) is flat at the same level.
    mine = blocks['DeepMine']
    mine_rects = {}
    for orientation in ORIENTATIONS:
        w, h = (mine.size[0], mine.size[1]) if orientation in ('Cw0', 'Cw180') else (mine.size[1], mine.size[0])
        local = {(cx, cy) for cx, cy, cz, _ in mine.positioned((0, 0, 0), orientation)}
        ox, oy = min(p[0] for p in local), min(p[1] for p in local)
        mc = mine_coordinates(mine, (0, 0), 0, orientation)
        # rect origin = mine coordinates + (ox, oy) = vein + mc + (ox, oy)
        shift = (mc[0] + ox, mc[1] + oy)
        mine_rects[orientation] = (shift, {(x, y, level): (margin_bad, water, walk, trees)
                                           for x, y, level, margin_bad, water, walk, trees in
                                           rect_candidates(model, w, h, limits['DeepMine'], 1)})
    veins = []
    for x, y, level, _, water, walk, trees in rect_candidates(model, 5, 5, limits['DeepMine'], 0):
        if trees:
            continue
        straight = ((x + 2 - sx) ** 2 + (y + 2 - sy) ** 2) ** 0.5
        if straight < 35:
            continue
        for orientation in ORIENTATIONS:
            shift, rects = mine_rects[orientation]
            key = (x + shift[0], y + shift[1], level)
            if key in rects:
                margin_bad, mwater, mwalk, mtrees = rects[key]
                if mwalk >= 10 ** 6:
                    continue
                veins.append(((x, y, level), orientation, margin_bad, mwater, mwalk, mtrees, round(straight)))
                break
    veins.sort(key=lambda r: (r[0][2], r[2], r[5]))
    picked = []
    for cand in spread(veins, lambda r: r[0][:2], 14, 6 * limit):
        coordinates = mine_coordinates(mine, cand[0][:2], cand[0][2], cand[1])
        ok, info = building_site_ok(model, mine, coordinates, cand[1], 1)
        if ok:
            picked.append((cand[0], coordinates, cand[1], info))
        if len(picked) >= 3 * limit:
            break
    print(f'DeepOreVein: {len(veins)} vein origins with a flat DeepMine footprint')
    for vein, coordinates, orientation, info in picked:
        print(f'   vein {vein} mine {coordinates} {orientation} walk {info["walk"]} straight {info["straight"]} '
              f'water {info["water"]} freeboard {info["freeboard"]} trees {info["trees"]} margin-bad {info["marginProblems"]}')
    candidates['veins'] = picked
    if png:
        marks = []
        for name, colour in (('NuclearReactor', (255, 0, 255)), ('LaunchPad', (0, 255, 255)), ('DeepDrill', (255, 255, 255))):
            for coordinates, orientation, info in candidates[name][:6]:
                marks.append((f'{name[:5]}{coordinates[2]}', info['cells'], colour))
        for vein, coordinates, orientation, info in picked:
            marks.append((f'v{vein[2]}', rect_cells(vein[0], vein[1], 5, 5), (255, 160, 0)))
        render_preview(model, Path(png), marks)
    return candidates


# ------------------------------------------------------------------ plan
#
# `plan` proposes the placements and sites a variant still lacks for the full
# loop (pits with outcrops, quarries with seams, caches with Archive
# Excavation sites, waterside, map-edge and dam sites, then a flat site for
# every remaining building) and writes the extended variant JSON for review.
# The proposal is ordinary variant data: `build` validates it like any
# hand-written entry.

COMPASS = ['east', 'north-east', 'north', 'north-west', 'west', 'south-west', 'south', 'south-east']


def describe(model, cells):
    import math
    sx, sy, _ = model.start
    cx = sum(x for x, _ in cells) / len(cells)
    cy = sum(y for _, y in cells) / len(cells)
    distance = math.hypot(cx - sx, cy - sy)
    if distance < 8:
        return 'by the start'
    angle = math.degrees(math.atan2(cy - sy, cx - sx)) % 360
    return f'{round(distance)} cells {COMPASS[int((angle + 22.5) // 45) % 8]} of the start'


def display_name(template):
    import re
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', template.split('.')[0]).replace('Iron Teeth', '').strip()


class Planner:
    def __init__(self, variant, catalog, model, requirements):
        self.variant = variant
        self.catalog = catalog
        self.model = model
        self.requirements = requirements
        self.placed, self.placed_columns = {}, {}
        self.records = []
        for placement in variant['placements']:
            self._place(placement)
        self.claimed, self.doors, self.reserved = {}, set(), set()
        self.required = required_site_templates(catalog, requirements)
        for site in variant['sites']:
            self._claim(site)
        self.rect_cache = {}
        self.length, self.bridges = model.route()
        self.added_placements, self.added_sites = [], []

    # ---- bookkeeping
    def _place(self, placement):
        blueprint = self.catalog.get(placement['template'])
        blocks = Blocks(blueprint['BlockObjectSpec'])
        coordinates = (placement['x'], placement['y'], placement['z'])
        orientation = placement.get('orientation', 'Cw0')
        label = placement['label']
        for x, y, z, block in blocks.positioned(coordinates, orientation):
            if occupied(block):
                self.placed.setdefault((x, y, z), []).append(label)
                self.placed_columns[(x, y)] = label
            if block['OccupyAllBelow']:
                for bz in range(z - 1, -1, -1):
                    self.placed.setdefault((x, y, bz), []).append(label)
        self.records.append({'placement': placement, 'template': placement['template'], 'blueprint': blueprint,
                             'blocks': blocks, 'coordinates': coordinates, 'orientation': orientation,
                             'cells': footprint(blocks, coordinates, orientation), 'ok': True})

    def placement_ok(self, placement):
        blueprint = self.catalog.get(placement['template'])
        blocks = Blocks(blueprint['BlockObjectSpec'])
        coordinates = (placement['x'], placement['y'], placement['z'])
        orientation = placement.get('orientation', 'Cw0')
        cells = footprint(blocks, coordinates, orientation)
        if cells & (set(self.claimed) | self.doors | self.reserved):
            return False
        return not check_object(self.model, blocks, coordinates, orientation, False, self.placed, blueprint)

    def add_placement(self, placement):
        self.variant['placements'].append(placement)
        self.added_placements.append(placement)
        self._place(placement)

    def add_site(self, site):
        self.variant['sites'].append(site)
        self.added_sites.append(site)
        self._claim(site)

    def _claim(self, site):
        """Footprint, door and listed open margins of a site stay clear of every later proposal
        (alternative sites included: they must keep working)."""
        if self.required[site['template']] == 'hydro':
            return
        blocks = building_blocks(self.catalog, site['template'])
        coordinates = (site['x'], site['y'], site['z'])
        cells = blocks.columns(coordinates, site.get('orientation', 'Cw0'))
        for cell in cells:
            self.claimed.setdefault(cell, site['label'])
        door = approach_cell(blocks, coordinates, site.get('orientation', 'Cw0'))
        if door:
            self.doors.add(door[:2])
        strips = side_strips(cells, site.get('margin', 1))
        for side in site.get('openSides', []):
            self.reserved |= strips[side]

    def site_check(self, site):
        rule = self.required[site['template']]
        problems, info, cells = check_site(self.model, self.catalog, site, self.records, self.placed,
                                           self.placed_columns, self.requirements, rule)
        if rule != 'hydro':
            if cells & set(self.claimed):
                problems.append('overlaps a claimed site')
            if info.get('door') and (tuple(info['door'][:2]) in self.claimed):
                problems.append('door inside a claimed site')
            if cells & self.doors:
                problems.append('covers another site door')
        return problems, info, cells

    def open_sides(self, cells, level, margin):
        return [side for side, strip in side_strips(cells, margin).items()
                if not site_problems(self.model, strip, level, self.placed_columns)[0]
                and not (strip & set(self.claimed))]

    # ---- candidate generators
    def rects(self, w, h, max_level, margin):
        key = (w, h, max_level, margin)
        if key not in self.rect_cache:
            self.rect_cache[key] = rect_candidates(self.model, w, h, max_level, margin)
        return self.rect_cache[key]

    def flat_candidates(self, template, margin=1, all_sides=True, keep_out=14, max_route=10 ** 6):
        """(coordinates, orientation, cells) of flat footprints, best route first."""
        blocks = building_blocks(self.catalog, template)
        max_level = self.model.total_height - 1 - (blocks.top_occupied_layer() - blocks.base_z)
        sx, sy, _ = self.model.start
        found = []
        for orientation in ORIENTATIONS:
            local = {(cx, cy) for cx, cy, cz, _ in blocks.positioned((0, 0, 0), orientation)}
            ox, oy = min(p[0] for p in local), min(p[1] for p in local)
            w = max(p[0] for p in local) - ox + 1
            h = max(p[1] for p in local) - oy + 1
            for x, y, level, margin_bad, water, walk, trees in self.rects(w, h, max_level, margin):
                if walk >= min(max_route, 10 ** 6) or (all_sides and margin_bad):
                    continue
                if max(abs(x + w / 2 - sx), abs(y + h / 2 - sy)) < keep_out + max(w, h) / 2:
                    continue
                bridges = int(self.bridges[max(0, min(self.model.sy - 1, y)), max(0, min(self.model.sx - 1, x))])
                found.append(((bridges > 0, walk, trees), (x - ox, y - oy, level), orientation))
        found.sort(key=lambda r: r[0])
        return [(coordinates, orientation) for _, coordinates, orientation in found]

    def flat_site(self, template, label=None, margin=1, extra=None, accept=None, limit=4000, keep_out=14, all_sides=True,
                  max_route=10 ** 6):
        rule = self.required[template]
        blocks = building_blocks(self.catalog, template)
        blocked = set(self.claimed) | self.doors | self.reserved | set(self.placed_columns)
        for coordinates, orientation in self.flat_candidates(template, margin, all_sides, keep_out, max_route)[:limit]:
            site = {'template': template, 'label': '', 'x': coordinates[0], 'y': coordinates[1], 'z': coordinates[2],
                    'orientation': orientation, 'margin': margin, 'openSides': []}
            if rule == 'understructure':
                site['understructure'] = [0, 0, 0]
            if extra:
                site.update(extra(site) or {})
                if site.get('_skip'):
                    continue
            cells = blocks.columns(coordinates, orientation)
            if cells & blocked:
                continue
            site['openSides'] = self.open_sides(cells, coordinates[2], margin)
            if all_sides and len(site['openSides']) < 4:
                continue
            problems, info, cells = self.site_check(site)
            if problems or (accept and not accept(site, info)):
                continue
            site['label'] = label or f'{display_name(template)}, {describe(self.model, cells)}'
            return site, info
        return None, None

    # ---- stages
    def plan_pits(self, outcrops_per_pit=3):
        for template, rule in sorted(self.required.items()):
            if rule != 'pit' or any(s['template'] == template for s in self.variant['sites']):
                continue
            blueprint = self.catalog.get(template)
            group = blueprint['YieldRemovingBuildingSpec']['ResourceGroup']
            deposit = [t for t in self.catalog.map_editor_common if 'MineralDepositSpec' in self.catalog.get(t)
                       and self.catalog.get(t)['MineralDepositSpec']['Yielder']['ResourceGroup'] == group]
            if len(deposit) != 1:
                fail(f'Expected one map object of resource group {group}, found {deposit}')
            chosen = {}

            def with_outcrops(site):
                blocks = building_blocks(self.catalog, template)
                coordinates = (site['x'], site['y'], site['z'])
                door = approach_cell(blocks, coordinates, site['orientation'])
                cells = {(x, y) for x, y, z, b in blocks.positioned(coordinates, site['orientation'])}
                blocked = set(self.claimed) | self.doors | self.reserved | set(self.placed_columns) | cells | ring(cells, 1)
                distance = {door[:2]: 0}
                queue = deque([door[:2]])
                while queue:
                    x, y = queue.popleft()
                    if distance[(x, y)] >= 14:
                        continue
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if (nx, ny) in distance or (nx, ny) in blocked or not (0 <= nx < self.model.sx and 0 <= ny < self.model.sy):
                            continue
                        if self.model.height[ny, nx] != door[2] or self.model.water_any[ny, nx] > 0 \
                                or self.model.hard_mask[ny, nx] or not self.model.contiguous[ny, nx]:
                            continue
                        distance[(nx, ny)] = distance[(x, y)] + 1
                        queue.append((nx, ny))
                picks = []
                for (x, y), d in sorted(distance.items(), key=lambda kv: (kv[1], kv[0])):
                    if d < 3 or self.model.natural_mask[y, x]:
                        continue
                    if any(abs(x - px) <= 2 and abs(y - py) <= 2 for px, py in picks):
                        continue
                    placement = {'template': deposit[0], 'label': '', 'x': x, 'y': y, 'z': door[2]}
                    if self.placement_ok(placement):
                        picks.append((x, y))
                    if len(picks) == outcrops_per_pit:
                        break
                if len(picks) < outcrops_per_pit:
                    return {'_skip': True}
                chosen['picks'], chosen['level'] = picks, door[2]
                return {}

            site, info = self.flat_site(template, extra=with_outcrops, keep_out=10)
            if site is None:
                fail(f'{self.variant["id"]}: no {template} site with {outcrops_per_pit} free outcrop cells in range')
            site.pop('_skip', None)
            name = display_name(deposit[0])
            for index, (x, y) in enumerate(chosen['picks'], 1):
                self.add_placement({'template': deposit[0], 'label': f'{name} {index} ({site["label"]})',
                                    'x': x, 'y': y, 'z': chosen['level']})
            self.add_site(site)

    def plan_understructures(self):
        """A seam and a quarry site for every understructure building without a site (veins already exist)."""
        for template, rule in sorted(self.required.items()):
            if rule != 'understructure' or any(s['template'] == template for s in self.variant['sites']):
                continue
            names = self.catalog.get(template)['UnderstructureConstraintSpec']['UnderstructureTemplateNames']
            if len(names) != 1:
                fail(f'{template}: expected one understructure template, found {names}')
            under = names[0]
            blocks = building_blocks(self.catalog, template)
            ublocks = Blocks(self.catalog.get(under)['BlockObjectSpec'])
            done = False
            for coordinates, orientation in self.flat_candidates(template, 1, True, 20)[:6000]:
                core, _ = understructure_core(blocks, coordinates, orientation)
                ux, uy, z = min(x for x, _ in core), min(y for _, y in core), coordinates[2]
                if not core <= footprint(ublocks, (ux, uy, z)):
                    continue
                cells = blocks.columns(coordinates, orientation)
                if cells & (set(self.claimed) | self.doors | self.reserved | set(self.placed_columns)):
                    continue
                placement = {'template': under, 'label': f'__pending {under}', 'x': ux, 'y': uy, 'z': z, 'orientation': 'Cw0'}
                if not self.placement_ok(placement):
                    continue
                self._place(placement)
                site = {'template': template, 'label': '', 'x': coordinates[0], 'y': coordinates[1], 'z': z,
                        'orientation': orientation, 'margin': 1, 'openSides': self.open_sides(cells, z, 1),
                        'understructure': [ux, uy, z]}
                problems = ['sides'] if len(site['openSides']) < 4 else self.site_check(site)[0]
                self._unplace(placement)
                if problems:
                    continue
                site['label'] = f'{display_name(template)}, {describe(self.model, cells)}'
                placement['label'] = f'{display_name(under)} ({site["label"]})'
                self.add_placement(placement)
                self.add_site(site)
                done = True
                break
            if not done:
                fail(f'{self.variant["id"]}: no {template} site over a new {under}')

    def _unplace(self, placement):
        label = placement['label']
        self.placed = {k: [v for v in vs if v != label] for k, vs in self.placed.items()}
        self.placed = {k: v for k, v in self.placed.items() if v}
        self.placed_columns = {k: v for k, v in self.placed_columns.items() if v != label}
        self.records = [r for r in self.records if r['placement'] is not placement]

    def plan_caches(self):
        wanted = narrative_cache_count()
        surveyor = [t for t in self.required if self.catalog.get(RECORD_CACHE_TEMPLATE)['HumanRecordCacheSpec']['SurveyRecipeId']
                    in self.catalog.get(t).get('ManufactorySpec', {}).get('ProductionRecipeIds', [])]
        if len(surveyor) != 1:
            fail(f'Expected one survey building, found {surveyor}')
        surveyor = surveyor[0]
        radius = self.catalog.get(RECORD_CACHE_TEMPLATE)['HumanRecordCacheSpec']['SurveyRadius']
        sblocks = building_blocks(self.catalog, surveyor)
        cblocks = record_cache_blocks(self.catalog)

        def covers(site, cache_cells):
            cells = np.array(sblocks.occupied_cells((site['x'], site['y'], site['z']), site['orientation']))
            other = np.array(cache_cells)
            d = np.maximum(np.abs(cells[:, None, 0] - other[None, :, 0]), np.abs(cells[:, None, 1] - other[None, :, 1]))
            d = np.where(np.abs(cells[:, None, 2] - other[None, :, 2]) <= radius, d, 99)
            return int(d.min()) <= radius

        def cache_cells(placement):
            return cblocks.occupied_cells((placement['x'], placement['y'], placement['z']), placement.get('orientation', 'Cw0'))

        def surveyed(placement):
            return any(s['template'] == surveyor and covers(s, cache_cells(placement)) for s in self.variant['sites'])

        # 1. an excavation site for every existing cache
        for record in list(self.records):
            if record['template'] != RECORD_CACHE_TEMPLATE or surveyed(record['placement']):
                continue
            cells = cache_cells(record['placement'])
            site, info = self._near_site(surveyor, cells, covers)
            if site is None:
                # No room for an excavation beside this cache: drop it here and
                # let step 2 place a surveyable cache elsewhere.
                print(f'   dropped cache {record["placement"]["label"]}: no {surveyor} site within {radius}')
                self.variant['placements'].remove(record['placement'])
                self._unplace(record['placement'])
                continue
            site['label'] = f'Archive Excavation for {record["placement"]["label"].split(" (")[0]}'
            self.add_site(site)
        # 2. more caches beside ruin clusters until the narrative count is met
        count = sum(1 for r in self.records if r['template'] == RECORD_CACHE_TEMPLATE)
        ruins = [r for r in self.model.objects if 'RuinSpec' in self.catalog.get(r['template'])]
        existing = [r['coordinates'] for r in self.records if r['template'] == RECORD_CACHE_TEMPLATE]
        clusters, routed = [], []
        for r in ruins:
            route, bridge_cells = route_to(self.model, {r['coordinates'][:2]})
            if route is not None:
                routed.append(((bridge_cells > 0, route), r['coordinates']))
        for _, (x, y, z) in sorted(routed):
            if any(abs(x - ex) < 30 and abs(y - ey) < 30 for ex, ey, _ in existing + clusters):
                continue
            clusters.append((x, y, z))
        for cx, cy, cz in clusters:
            if count >= wanted:
                break
            placed = self._cache_near(cx, cy, cblocks, surveyor, covers, cache_cells)
            if placed:
                count += 1
                existing.append((cx, cy, cz))
        if count < wanted:
            fail(f'{self.variant["id"]}: only {count} of {wanted} caches could be placed')

    def _near_site(self, surveyor, cells, covers):
        xs = [x for x, _, _ in cells]
        ys = [y for _, y, _ in cells]
        blocks = building_blocks(self.catalog, surveyor)
        options = []
        for orientation in ORIENTATIONS:
            local = {(cx, cy) for cx, cy, cz, _ in blocks.positioned((0, 0, 0), orientation)}
            ox, oy = min(p[0] for p in local), min(p[1] for p in local)
            w = max(p[0] for p in local) - ox + 1
            h = max(p[1] for p in local) - oy + 1
            for x0 in range(min(xs) - 4 - w, max(xs) + 6):
                for y0 in range(min(ys) - 4 - h, max(ys) + 6):
                    if not (0 <= x0 and 0 <= y0 and x0 + w <= self.model.sx and y0 + h <= self.model.sy):
                        continue
                    level = int(self.model.height[y0, x0])
                    options.append(((x0 - ox, y0 - oy, level), orientation))
        blocked = set(self.claimed) | self.doors | self.reserved | set(self.placed_columns)
        for coordinates, orientation in options:
            footprint_cells = blocks.columns(coordinates, orientation)
            if footprint_cells & blocked:
                continue
            if any(self.model.height[y, x] != coordinates[2] for x, y in footprint_cells
                   if 0 <= x < self.model.sx and 0 <= y < self.model.sy):
                continue
            site = {'template': surveyor, 'label': '', 'x': coordinates[0], 'y': coordinates[1], 'z': coordinates[2],
                    'orientation': orientation, 'margin': 1, 'openSides': []}
            if not covers(site, cells):
                continue
            site['openSides'] = self.open_sides(footprint_cells, coordinates[2], 1)
            problems, info, _ = self.site_check(site)
            if not problems:
                return site, info
        return None, None

    def _cache_near(self, cx, cy, cblocks, surveyor, covers, cache_cells):
        """Place a cache on free tree-free ground near (cx, cy) with an excavation site in range."""
        spots = []
        for x in range(cx - 12, cx + 13):
            for y in range(cy - 12, cy + 13):
                if not (0 <= x < self.model.sx - 3 and 0 <= y < self.model.sy - 2):
                    continue
                level = int(self.model.height[y, x])
                placement = {'template': RECORD_CACHE_TEMPLATE, 'label': '', 'x': x, 'y': y, 'z': level, 'orientation': 'Cw0'}
                cells = footprint(cblocks, (x, y, level))
                if any(self.model.natural_mask[py, px] for px, py in cells if 0 <= px < self.model.sx and 0 <= py < self.model.sy):
                    continue
                if self.length[y, x] < 0:
                    continue
                spots.append((abs(x - cx) + abs(y - cy), placement))
        spots.sort(key=lambda s: s[0])
        for _, placement in spots[:60]:
            if not self.placement_ok(placement):
                continue
            cells = cache_cells(placement)
            # temporarily place, find a site, keep both or roll back
            placement['label'] = f'Ruins {describe(self.model, {(c[0], c[1]) for c in cells})}'
            self._place(placement)
            site, info = self._near_site(surveyor, cells, covers)
            if site is None:
                self._unplace(placement)
                continue
            self._unplace(placement)
            self.add_placement(placement)
            site['label'] = f'Archive Excavation for {placement["label"]}'
            self.add_site(site)
            return True
        return False

    def plan_special(self, rule):
        for template, r in sorted(self.required.items()):
            if r != rule or any(s['template'] == template for s in self.variant['sites']):
                continue
            site = None
            if rule == 'mapEdge':
                site, info = self.flat_site(template, keep_out=0, all_sides=False, limit=10 ** 6,
                                            accept=lambda s, i: i.get('edgeCells', 0) > 0)
            elif rule in ('waterDepth', 'waterInput'):
                site, info = self._waterside(template, rule)
            elif rule == 'hydro':
                site, info = self._dam_site(template)
            if site is None:
                fail(f'{self.variant["id"]}: no {rule} site for {template}')
            self.add_site(site)

    def _waterside(self, template, rule):
        blueprint = self.catalog.get(template)
        blocks = building_blocks(self.catalog, template)
        if rule == 'waterDepth':
            spec = blueprint['WaterDepthWorkCellsSpec']
            anchors = [(c['X'], c['Y']) for c in spec['WorkCells']]
            work_z = [c['Z'] - blocks.base_z for c in spec['WorkCells']]
            # Only WorkCells[0] is the native contamination sample (check_site).
            wet = (self.model.water_depth > 0) & (self.model.water_contamination <= MAX_WORK_CELL_CONTAMINATION)
        else:
            c = blueprint['WaterInputSpec']['WaterInputCoordinates']
            anchors = [(c['X'], c['Y'])]
            wet = self.model.water_depth > 0
        ground = [(x, y, z) for x, y, z, b in blocks.positioned((0, 0, 0), 'Cw0')
                  if occupied(b) and b['MatterBelow'] in ('Ground', 'GroundOrStackable')]
        options = []
        model = self.model
        for wy, wx in zip(*np.nonzero(wet)):
            wx, wy = int(wx), int(wy)
            for orientation in ORIENTATIONS:
                ax, ay = blocks.transform(anchors[0], (0, 0), orientation, False)
                cx, cy = wx - ax, wy - ay
                cells = [blocks.transform((lx, ly), (cx, cy), orientation, False) for lx, ly, _ in ground]
                if not all(0 <= x < model.sx and 0 <= y < model.sy for x, y in cells):
                    continue
                level = int(model.height[cells[0][1], cells[0][0]])
                if any(model.height[y, x] != level or model.water_any[y, x] > 0 for x, y in cells):
                    continue
                work = [blocks.transform(a, (cx, cy), orientation, False) for a in anchors]
                if not all(0 <= x < model.sx and 0 <= y < model.sy for x, y in work):
                    continue
                if rule == 'waterDepth':
                    # Surface-based, as check_site: each working cell (world z = site z + local z
                    # - BaseZ) is in an open column whose surface stands MinDepth above it.
                    if not wet[work[0][1], work[0][0]] or not all(
                            model.water_depth[y, x] > 0 and model.height[y, x] <= level - ground[0][2] + dz
                            and model.water_surface[y, x] - (level - ground[0][2] + dz) >= spec['MinDepth']
                            for (x, y), dz in zip(work, work_z)):
                        continue
                elif not all(wet[y, x] and model.height[y, x] < level for x, y in work):
                    continue
                gx, gy = cells[0]
                if self.length[gy, gx] < 0:
                    continue
                # the Ground blocks stand on the terrain: world z of their local z is the terrain level
                z = level - ground[0][2]
                options.append(((int(self.bridges[gy, gx]) > 0, int(self.length[gy, gx])), (cx, cy, z), orientation))
        if rule == 'waterInput' and not options:
            options = self._blast_options(blocks, anchors[0], ground)
        natural = self._first_site(template, blocks, options)
        if natural[0] is not None or rule != 'waterDepth':
            return natural
        # No natural site: blast the bank cells under the deck (at most 3 layers each).
        blasted = []
        for key, coordinates, orientation in options:
            cuts = {}
            for x, y, z in blocks.occupied_cells(coordinates, orientation):
                if 0 <= x < model.sx and 0 <= y < model.sy and model.height[y, x] > z:
                    cuts[(x, y)] = max(cuts.get((x, y), 0), int(model.height[y, x]) - z)
            if not cuts or max(cuts.values()) > 3:
                continue
            blasted.append(((len(cuts), sum(cuts.values())) + key, coordinates, orientation,
                            [[x, y, layers] for (x, y), layers in sorted(cuts.items())]))
        return self._first_site(template, blocks, blasted)

    def _first_site(self, template, blocks, options):
        options = sorted(options, key=lambda o: o[0])
        for option in options[:20000]:
            _, coordinates, orientation = option[:3]
            site = {'template': template, 'label': '', 'x': coordinates[0], 'y': coordinates[1], 'z': coordinates[2],
                    'orientation': orientation}
            if len(option) > 3:
                site['dynamite'] = option[3]
            cells = blocks.columns(coordinates, orientation)
            if cells & (set(self.claimed) | self.doors | self.reserved | set(self.placed_columns)):
                continue
            problems, info, cells = self.site_check(site)
            if not problems:
                site['label'] = f'{display_name(template)}, {describe(self.model, cells)}'
                return site, info
        return None, None

    def _blast_options(self, blocks, anchor, ground):
        """Water-input placements on a straight bank: every footprint cell is dry ground at one level and
        the intake cell borders water; the player blasts the intake column (vanilla Dynamite)."""
        model = self.model
        wet = model.water_depth > 0
        options = []
        for wy, wx in zip(*np.nonzero(wet)):
            wx, wy = int(wx), int(wy)
            for ix, iy in ((wx + 1, wy), (wx - 1, wy), (wx, wy + 1), (wx, wy - 1)):
                if not (0 <= ix < model.sx and 0 <= iy < model.sy) or model.water_any[iy, ix] > 0:
                    continue
                level = int(model.height[iy, ix])
                depth = level - int(model.height[wy, wx])
                if not 1 <= depth <= 3:
                    continue
                for orientation in ORIENTATIONS:
                    ax, ay = blocks.transform(anchor, (0, 0), orientation, False)
                    cx, cy = ix - ax, iy - ay
                    cells = [blocks.transform((lx, ly), (cx, cy), orientation, False) for lx, ly, _ in ground]
                    if not all(0 <= x < model.sx and 0 <= y < model.sy and model.height[y, x] == level
                               and model.water_any[y, x] == 0 for x, y in cells):
                        continue
                    if self.length[iy, ix] < 0:
                        continue
                    options.append(((depth, int(self.bridges[iy, ix]) > 0, int(self.length[iy, ix])),
                                    (cx, cy, level - ground[0][2]), orientation, [[ix, iy, depth]]))
        return options

    def _dam_site(self, template):
        labels = wet_components(self.model)
        strength = source_strength_by_component(self.model, self.catalog)
        wet = self.model.water_depth > 0
        best = None
        for y, x in zip(*np.nonzero(wet)):
            x, y = int(x), int(y)
            if not strength.get(int(labels[y, x])):
                continue
            drop = any(0 <= nx < self.model.sx and 0 <= ny < self.model.sy and wet[ny, nx]
                       and self.model.height[ny, nx] != self.model.height[y, x]
                       for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
            if not drop:
                continue
            route, bridge_cells = route_to(self.model, {(x, y)})
            if route is None:
                continue
            head, _ = hydro_head(self.model, x, y, self.requirements['hydroWindow'])
            clean = self.model.water_contamination[y, x] < 0.5
            # The turbine's two lanes pass at most 3 m3/s (docs/hydroelectric-construction.md); a native
            # source strength is water per second, so flow up to 3 ranks before natural drop.
            flow = min(strength[int(labels[y, x])], 3.0)
            key = (not clean, -flow, -head, bridge_cells > 0, route)
            if best is None or key < best[0]:
                best = (key, x, y)
        if best is None:
            return None, None
        _, x, y = best
        site = {'template': template, 'label': '', 'x': x, 'y': y, 'z': int(self.model.height[y, x])}
        problems, info, cells = self.site_check(site)
        if problems:
            return None, None
        site['label'] = f'Dam site with {info["naturalHead"]} layers of natural drop, {describe(self.model, cells)}'
        return site, info

    def plan_flat(self):
        missing = [t for t, r in self.required.items() if r == 'flat'
                   and not any(s['template'] == t for s in self.variant['sites'])]
        def area(t):
            size = self.catalog.get(t)['BlockObjectSpec']['Size']
            return size['X'] * size['Y']
        for template in sorted(missing, key=lambda t: -area(t)):
            site, info = self.flat_site(template, max_route=100)
            if site is None:
                site, info = self.flat_site(template, all_sides=False, keep_out=6, max_route=100)
            if site is None:
                site, info = self.flat_site(template, all_sides=False, keep_out=6)
            if site is None:
                fail(f'{self.variant["id"]}: no flat site for {template}')
            self.add_site(site)


def plan(variant_path, catalog, out):
    variant = load_variant(variant_path)
    data, entries = load_source(variant['source'])
    entries = resize_height(entries, variant['height']['terrainLayers'], variant['height']['totalHeight'])
    model = MapModel(entries, catalog)
    requirements = load_loop_requirements()
    planner = Planner(variant, catalog, model, requirements)
    planner.plan_pits()
    planner.plan_understructures()
    planner.plan_caches()
    for rule in ('waterDepth', 'waterInput', 'mapEdge', 'hydro'):
        planner.plan_special(rule)
    planner.plan_flat()
    Path(out).write_text(dump_variant(variant), encoding='utf-8')
    print(f'{variant["id"]}: +{len(planner.added_placements)} placements, +{len(planner.added_sites)} sites -> {out}')
    for p in planner.added_placements:
        print('   placement', p['template'], p['label'], (p['x'], p['y'], p['z']))
    for s in planner.added_sites:
        print('   site', s['template'], s['label'], (s['x'], s['y'], s['z']), s.get('orientation'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('analyze', 'suggest'):
        p = sub.add_parser(name)
        p.add_argument('source')
        p.add_argument('--png')
    p = sub.add_parser('build')
    p.add_argument('variants', nargs='+')
    p.add_argument('--out-dir')
    p = sub.add_parser('validate')
    p.add_argument('variants', nargs='+')
    p.add_argument('--out-dir')
    p = sub.add_parser('plan')
    p.add_argument('variant')
    p.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    catalog = TemplateCatalog()
    try:
        if args.command in ('analyze', 'suggest'):
            data, entries = load_source(args.source)
            model = MapModel(entries, catalog)
            info = survey(model)
            info['sha256'] = hashlib.sha256(data).hexdigest()
            print(json.dumps(info, indent=1, default=list))
            if args.command == 'suggest':
                suggest(model, catalog, args.png)
            elif args.png:
                render_preview(model, Path(args.png))
            return 0
        if args.command == 'plan':
            plan(args.variant, catalog, args.out)
            return 0
        results = build(args.variants, catalog, args.out_dir, write=args.command == 'build')
        return 1 if any(errors for _, _, errors in results) else 0
    except MapError as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
