"""Site test map for the all-buildings acceptance (tools/start_all_buildings.ps1, sites batch).

Twelve buildings cannot be placed on the flat pad of 'Deep Frontier - All Buildings Test': they need
an understructure (Deep Mine, both quarries), water (Fish Hatchery, Double Shower, Swimming Pool, Deep
Water Pump, Radioactive Sludge Recovery Pump, Reinforced Hydro Turbine) or a terrain step with an
anchor (the three Concrete Side Platforms). This writes
'<Maps>/Deep Frontier - All Buildings Sites Test.timber': the flat test map (create_flat_test_map.py)
plus the terrain and map-authored objects listed in tools/all_buildings_sites.json:

  understructures  DeepOreVein, SandstoneSeam, LimestoneSeam entities (MapEditor Common collection)
  pits             cells dug down to 'floor' (pond, two enclosed radioactive pools, the step)
  walls            a terrain ring raised to 'height' (the sealed hydro reach)

The map holds no water: the acceptance fills it through the native water services with known
volumes, so the radiation and flow accounting starts from exact amounts. Everything stays inside
'zone', away from the pad and the corridor the harness levels next to the district centre.

Before writing, every building, anchor and understructure placement of the contract is checked
against the planned terrain with the native placement rules this map is responsible for
(prepare_deep_frontier_map.check_object, plus MatterBelow Air/Stackable, the UnderstructureFinder
core rule, water-input pipe depth, water work cells and separate pits). After writing, the file is
read back with prepare_deep_frontier_map.MapModel and its terrain and entities compared with the plan.

    python tools/create_all_buildings_sites_map.py [--check]   (--check validates without writing)
"""
import argparse
import copy
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_flat_test_map as flat  # noqa: E402
import prepare_deep_frontier_map as maps  # noqa: E402

CONTRACT = Path(__file__).resolve().parent / 'all_buildings_sites.json'
# The harness levels a 100x84 pad and its corridor to the district centre, from 3 cells around the
# centre's footprint (StartingLocation y - 2 for the Iron Teeth centre at Cw180). The zone must end
# before that corridor (AllBuildingsAcceptance.ChoosePad also refuses pads overlapping the zone).
START_CLEARANCE = 5


def rect_cells(rect):
    x, y, w, h = rect
    return {(i, j) for i in range(x, x + w) for j in range(y, y + h)}


def ring_cells(rect):
    x, y, w, h = rect
    return {(i, j) for (i, j) in rect_cells(rect) if i in (x, x + w - 1) or j in (y, y + h - 1)}


class Plan:
    """Planned terrain heights (no overhangs) and placements."""

    def __init__(self, contract, sx, sy, layers):
        self.c = contract
        self.sx, self.sy, self.layers = sx, sy, layers
        ground = contract['ground']
        self.height = np.full((sy, sx), ground, dtype=np.int32)
        self.pit_of = {}
        for pit in contract['pits']:
            for rect in pit['rects']:
                for (x, y) in rect_cells(rect):
                    if (x, y) in self.pit_of:
                        raise maps.MapError(f'pit {pit["id"]} overlaps pit {self.pit_of[(x, y)]} at {(x, y)}')
                    self.pit_of[(x, y)] = pit['id']
                    self.height[y, x] = pit['floor']
        self.wall_cells = set()
        for wall in contract['walls']:
            for (x, y) in ring_cells(wall['ring']):
                if (x, y) in self.pit_of:
                    raise maps.MapError(f'wall {wall["id"]} crosses pit {self.pit_of[(x, y)]} at {(x, y)}')
                self.wall_cells.add((x, y))
                self.height[y, x] = wall['height']
        if self.height.max() > layers:
            raise maps.MapError(f'terrain height {self.height.max()} exceeds the {layers} stored layers')

    def solid(self, x, y, z):
        return 0 <= z < self.height[y, x]


class PlanModel:
    """The minimum of MapModel that check_object reads, over the planned terrain."""

    def __init__(self, plan, total_height):
        self.sx, self.sy = plan.sx, plan.sy
        self.layers = plan.layers
        self.total_height = total_height
        z = np.arange(plan.layers).reshape(plan.layers, 1, 1)
        self.solid = z < plan.height[np.newaxis, :, :]
        self.height = plan.height
        self.contiguous = np.ones((plan.sy, plan.sx), dtype=bool)
        self.cells, self.bottom_cells = {}, {}

    def water_at(self, x, y, z):
        return 0.0


def blueprint_for(catalog, template):
    return catalog.get(template)


def validate(contract, catalog, plan, model, start):
    errors = []
    ground = contract['ground']
    zone = rect_cells(contract['zone'])
    zx, zy, zw, zh = contract['zone']
    sx0, sy0 = start[0], start[1]
    if zy + zh > sy0 - START_CLEARANCE:
        errors.append(f'zone reaches y {zy + zh - 1}, into the corridor the harness levels around the district centre (start y {sy0})')
    for cells, what in ((set(plan.pit_of), 'pit'), (plan.wall_cells, 'wall')):
        outside = [c for c in cells if c not in zone]
        if outside:
            errors.append(f'{what} cells outside the zone, e.g. {outside[0]}')
    # Pits hold separate water: no two pits may touch (4-neighbourhood).
    for (x, y), pit in plan.pit_of.items():
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            other = plan.pit_of.get((x + dx, y + dy))
            if other and other != pit:
                errors.append(f'pits {pit} and {other} touch at {(x, y)}')
    others = {}

    def occupy(name, blocks, coordinates, orientation):
        for x, y, z, block in blocks.positioned(coordinates, orientation):
            if maps.occupied(block):
                others.setdefault((x, y, z), []).append(name)

    # Understructures first: they are map objects that the buildings stand over.
    under = {}
    for u in contract['understructures']:
        bp = blueprint_for(catalog, u['template'])
        if u['template'] not in catalog.map_editor_common:
            errors.append(f'{u["template"]} is not in the mod MapEditor Common collection')
        blocks = maps.Blocks(bp['BlockObjectSpec'])
        coords = (u['x'], u['y'], u['z'])
        for p in maps.check_object(model, blocks, coords, 'Cw0', False, others, bp):
            errors.append(f'{u["template"]}: {p}')
        under[u['template']] = (coords, maps.footprint(blocks, coords))
        model.cells.update({(x, y, z): model.cells.get((x, y, z), []) + [{'template': u['template'], 'coordinates': coords}]
                            for x, y, z, b in blocks.positioned(coords) if maps.occupied(b)})
    stackable_tops = {}
    for a in contract['anchors'] + [contract['negativeAnchor']]:
        bp = blueprint_for(catalog, a['template'])
        blocks = maps.Blocks(bp['BlockObjectSpec'])
        coords = (a['x'], a['y'], a['z'] + blocks.base_z)
        for p in maps.check_object(model, blocks, coords, 'Cw0', False, others, bp):
            errors.append(f'anchor {a["template"]} at {(a["x"], a["y"], a["z"])}: {p}')
        occupy(a['template'], blocks, coords, 'Cw0')
        for x, y, z, b in blocks.positioned(coords):
            if b['Stackable'] != 'None':
                stackable_tops[(x, y, z)] = a['template']
    pits = {p['id']: p for p in contract['pits']}
    for b in contract['buildings']:
        template, orientation = b['template'], b['orientation']
        bp = blueprint_for(catalog, template)
        spec = bp['BlockObjectSpec']
        blocks = maps.Blocks(spec)
        coords = (b['x'], b['y'], b['z'] + blocks.base_z)   # map/Blocks convention: z at BaseZ
        name = template
        if 'AnchoredDeckSpec' not in bp and b['z'] + blocks.base_z != ground:
            errors.append(f'{name}: BaseZ layer {b["z"] + blocks.base_z} is not the bank height {ground}')
        problems = maps.check_object(model, blocks, coords, orientation, False, others, bp)
        if 'understructure' in b:
            # UnderstructureFinder.FindStrict (as validate_variant checks DeepMine sites): every block
            # whose occupation is exactly Top/Corners with solid MatterBelow stands on the understructure,
            # and no other occupied block of that layer shares its cells.
            u_coords, u_cells = under[b['understructure']]
            core = set()
            for x, y, z, block in blocks.positioned(coords, orientation):
                if block['MatterBelow'] in ('Ground', 'GroundOrStackable', 'Stackable') and \
                        block['Occupations'] in ('Top', 'Corners', 'Top, Corners', 'Corners, Top'):
                    core.add((x, y))
                elif z == u_coords[2] and maps.occupied(block) and (x, y) in u_cells:
                    errors.append(f'{name}: block ({x},{y}) {block["Occupations"]} conflicts with the {b["understructure"]}')
            if not core or not core <= u_cells:
                errors.append(f'{name}: ground core ({len(core)} cells) is not entirely on the {b["understructure"]}')
            if u_coords[2] != b['z']:
                errors.append(f'{name}: level differs from the {b["understructure"]} level')
            # check_object reports the core's 'overlap' with the understructure, which is the intended stacking.
            problems = [p for p in problems if f'overlaps {b["understructure"]}' not in p]
        errors += [f'{name}: {p}' for p in problems]
        for x, y, z, block in blocks.positioned(coords, orientation):
            matter = block['MatterBelow']
            if matter == 'Air' and plan.solid(x, y, z - 1):
                errors.append(f'{name}: block ({x},{y},{z}) needs open space below (Air) but terrain is there')
            if matter == 'Stackable' and (x, y, z - 1) not in stackable_tops:
                errors.append(f'{name}: block ({x},{y},{z}) needs a stackable top below and none is planned')
        if 'AnchoredDeckSpec' in bp:
            a = bp['AnchoredDeckSpec']['Anchor']
            ax, ay = blocks.transform((a['X'], a['Y']), coords, orientation, False)
            anchor = (ax, ay, b['z'] + a['Z'])
            planned = stackable_tops.get(anchor)
            if planned is None or 'AnchoredDeckAnchorSpec' not in blueprint_for(catalog, planned):
                errors.append(f'{name}: anchor cell {anchor} is not the stackable top of an AnchoredDeckAnchorSpec structure ({planned})')
            # The deck must overhang the step: open cells below every slab.
            for x, y, z, block in blocks.positioned(coords, orientation):
                if block['Stackable'] == 'BlockObject' and plan.solid(x, y, z - 1):
                    errors.append(f'{name}: slab ({x},{y},{z}) rests on terrain, not over the step')
        if 'WaterInputSpec' in bp:
            # Native WaterInputPipeCoordinates: start = transformed input + (0,0,BaseZ+1), then down to the
            # first terrain cell within MaxDepth; Depth = start - stop must be positive and the stop cell wet.
            w = bp['WaterInputSpec']['WaterInputCoordinates']
            wx, wy = blocks.transform((w['X'], w['Y']), coords, orientation, False)
            start_z = b['z'] + w['Z'] + blocks.base_z + 1
            max_depth = bp.get('WaterInputPipeSpec', {}).get('MaxDepth', 1)
            stop = start_z - max_depth
            for z in range(start_z - 1, start_z - max_depth - 1, -1):
                if plan.solid(wx, wy, z):
                    stop = z + 1
                    break
            pit = plan.pit_of.get((wx, wy))
            if start_z - stop <= 0:
                errors.append(f'{name}: water input pipe at ({wx},{wy}) is obstructed (depth 0)')
            elif pit is None or not (pits[pit].get('clean', 0) + pits[pit].get('radioactive', 0)) > 0 or plan.height[wy, wx] != stop:
                errors.append(f'{name}: water input pipe at ({wx},{wy}) stops at z {stop}, not on a filled pit floor')
            elif pit != b.get('pit'):
                errors.append(f'{name}: water input draws from {pit}, contract says {b.get("pit")}')
        if 'WaterDepthWorkCellsSpec' in bp:
            for cell in bp['WaterDepthWorkCellsSpec']['WorkCells']:
                wx, wy = blocks.transform((cell['X'], cell['Y']), coords, orientation, False)
                if plan.pit_of.get((wx, wy)) != b.get('pit'):
                    errors.append(f'{name}: water work cell ({wx},{wy}) is not in pit {b.get("pit")}')
        if 'TickableWaterBuildingSpec' in bp:
            cell = bp['TickableWaterBuildingSpec']['WaterCoordinates']
            wx, wy = blocks.transform((cell['X'], cell['Y']), coords, orientation, False)
            if plan.pit_of.get((wx, wy)) != b.get('pit'):
                errors.append(f'{name}: water cell ({wx},{wy}) is not in pit {b.get("pit")}')
        if b.get('control'):
            def shape(pit_id):
                cells = [c for c, v in plan.pit_of.items() if v == pit_id]
                x0, y0 = min(c[0] for c in cells), min(c[1] for c in cells)
                return sorted((x - x0, y - y0) for (x, y) in cells)
            if shape(b['pit']) != shape(b['control']) or pits[b['pit']]['floor'] != pits[b['control']]['floor'] or                     (pits[b['pit']]['clean'], pits[b['pit']]['radioactive']) != (pits[b['control']]['clean'], pits[b['control']]['radioactive']):
                errors.append(f'{name}: control pool {b["control"]} is not identical to {b["pit"]}')
        if 'basin' in b:
            hydro = contract['hydro']
            bx, by, bw, bh = hydro['basin']
            inner = rect_cells((bx + 1, by + 1, bw - 2, bh - 2))
            if not maps.footprint(blocks, coords, orientation) <= inner:
                errors.append(f'{name}: turbine footprint leaves the basin interior')
            if not (by < hydro['divider'] < by + bh - 1):
                errors.append(f'{name}: divider row outside the basin')
        entrance = blocks.entrance_cell(coords, orientation)
        if entrance:
            own = {(x, y, z) for x, y, z, block in blocks.positioned(coords, orientation) if maps.occupied(block)}
            ex, ey, ez = entrance
            if entrance not in own and (not plan.solid(ex, ey, ez - 1) or plan.solid(ex, ey, ez) or entrance in others):
                errors.append(f'{name}: entrance {entrance} is not a free cell on ground')
        occupy(name, blocks, coords, orientation)
        for x, y, z, block in blocks.positioned(coords, orientation):
            if maps.occupied(block) and (x, y) not in zone:
                errors.append(f'{name}: block ({x},{y},{z}) outside the zone')
                break
    return errors


def apply(contract, catalog, world, sx, sy, layers, plan):
    singletons = world['Singletons']
    cells = sx * sy
    voxels = singletons['TerrainMap']['Voxels']['Array'].split(' ')
    for (x, y) in set(plan.pit_of) | plan.wall_cells:
        h = int(plan.height[y, x])
        for z in range(layers):
            voxels[z * cells + y * sx + x] = '1' if z < h else '0'
    singletons['TerrainMap']['Voxels']['Array'] = ' '.join(voxels)
    for index, u in enumerate(contract['understructures']):
        placement = {'template': u['template'], 'x': u['x'], 'y': u['y'], 'z': u['z'], 'label': u['label']}
        world['Entities'].append(maps.new_entity(placement, catalog, 'all-buildings-sites', index))


def read_back(path, catalog, plan, contract):
    entries = maps.read_zip_bytes(path.read_bytes())
    model = maps.MapModel(entries, catalog)
    errors = []
    if not np.array_equal(model.height, plan.height):
        diff = np.argwhere(model.height != plan.height)
        errors.append(f'written terrain differs from the plan at {len(diff)} cells, e.g. (x,y)={tuple(diff[0][::-1])}')
    if not model.contiguous.all():
        errors.append('written terrain has overhangs')
    if model.water_any.any():
        errors.append('written map holds water')
    found = sorted((o['template'], o['coordinates']) for o in model.objects if o['template'] != 'StartingLocation')
    wanted = sorted((u['template'], (u['x'], u['y'], u['z'])) for u in contract['understructures'])
    if found != wanted:
        errors.append(f'written entities {found} != planned {wanted}')
    return model, errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true', help='validate the contract without writing the map')
    args = parser.parse_args(argv)
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    catalog = maps.TemplateCatalog()
    entries, world, metadata, (sx, sy, layers) = flat.flat_map()
    total_height = world['Singletons']['MapSize']['MapHeight']['Y']
    start = world['Entities'][0]['Components']['BlockObject']['Coordinates']
    plan = Plan(contract, sx, sy, layers)
    errors = validate(contract, catalog, plan, PlanModel(plan, total_height), (start['X'], start['Y'], start['Z']))
    if errors:
        print('Site contract problems:')
        for e in errors:
            print('  ' + e)
        raise SystemExit(1)
    print(f'Contract valid: {len(contract["buildings"])} buildings, {len(contract["anchors"]) + 1} anchors, '
          f'{len(contract["understructures"])} understructures, {len(contract["pits"])} pits, {len(contract["walls"])} wall rings')
    if args.check:
        return
    apply(contract, catalog, world, sx, sy, layers, plan)
    metadata['MapDescription'] = ('TEST MAP for the Deep Frontier all-buildings acceptance only (tools/start_all_buildings.ps1). '
                                  'Flat and dry at height 3 with the sites of tools/all_buildings_sites.json: a Deep Ore Vein, '
                                  'Sandstone and Limestone Seams, a pond, two enclosed pools, a terrain step and a walled river reach. '
                                  'Written by tools/create_all_buildings_sites_map.py.')
    target = flat.MAPS / (contract['map'] + '.timber')
    flat.store(entries, world, metadata, target)
    model, errors = read_back(target, catalog, plan, contract)
    if errors:
        print('Written map differs from the plan:')
        for e in errors:
            print('  ' + e)
        raise SystemExit(1)
    with zipfile.ZipFile(target) as archive:
        names = archive.namelist()
    print(f'Wrote {target} ({names}); read back with MapModel: terrain and {len(model.objects) - 1} understructures match the plan')
    marks = [('pad (b160)', maps.rect_cells(76, 132, 100, 84), (255, 255, 255))]
    for b in contract['buildings']:
        blocks = maps.Blocks(catalog.get(b['template'])['BlockObjectSpec'])
        marks.append((b['template'].split('.')[0][:10], maps.footprint(blocks, (b['x'], b['y'], b['z'] + blocks.base_z), b['orientation']), (255, 160, 0)))
    png = Path(__file__).resolve().parent.parent / 'outputs' / 'all-buildings-sites-map.png'
    maps.render_preview(model, png, marks)
    print(f'Preview {png}')


if __name__ == '__main__':
    main()
