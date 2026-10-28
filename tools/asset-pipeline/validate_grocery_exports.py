"""Validate the actual grocery payload and native inventory declaration."""
import collections
import hashlib
import json
import sys
import zlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent/'timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2

def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))
def require(condition, message):
    if not condition:
        raise ValueError(message)

# The Grocery Market hall (grocery_market_geometry.py): registration from the
# authored parts (register_grocery_market.py), export by export_lategame_models.py.
reg = read('outputs/lategame-studies/GroceryMarket-registration.json')
require(reg['ident'] == 'GroceryStore' and reg['study'] == 'GroceryMarket', 'Grocery registration identity changed')
folder = ROOT/'src/DeepFrontier/Data/Buildings/Food/GroceryStore'
blueprint = json.loads((folder/'GroceryStore.IronTeeth.blueprint.json').read_text(encoding='utf-8'))
payload = (folder/'GroceryStore.IronTeeth.Model.timbermesh').read_bytes()
require(payload == (ROOT/'outputs/lategame-integration/Data/Buildings/Food/GroceryStore/GroceryStore.IronTeeth.Model.timbermesh').read_bytes(),
        'Active grocery mesh is not the reviewed market export')
model = model_pb2.Model()
model.ParseFromString(zlib.decompress(payload))
names = collections.Counter(n.name for n in model.nodes)
require(all(v == 1 for v in names.values()), 'Duplicate grocery model nodes')
# Fill-stage nodes switched by GroceryStockDisplay.cs: all 18 exactly once,
# static, with geometry, and no stock node for an undeclared food or stage.
stock_foods = read('tools/frontier_progression.json')['groceryStore']['stock']
stock_nodes = [f'GroceryStock.{f}.{n}' for f in stock_foods for n in (1, 2, 3)]
require(len(stock_nodes) == 18, 'The grocery must declare six foods with three stages each')
require(all(names[n] == 1 for n in stock_nodes), 'Grocery stock stage nodes missing or duplicated: '+str([n for n in stock_nodes if names[n] != 1]))
require(not {n for n in names if n.startswith('GroceryStock.')} - set(stock_nodes), 'Undeclared grocery stock nodes')
stock_meshes = {n.name: n for n in model.nodes if n.name in stock_nodes}
require(all(any(len(m.indices) for m in node.meshes) for node in stock_meshes.values()), 'Empty grocery stock stage node')
require(not any(node.nodeAnimations for node in stock_meshes.values()), 'Grocery stock stage nodes must be static')
require(blueprint.get('GroceryStockDisplaySpec') == {'Stages': 3}, 'Grocery stock display spec differs')
native = {'BaseWood_DarkBrown.IronTeeth', 'RoofPlanks.IronTeeth', 'BaseMetal.IronTeeth', 'Details.IronTeeth',
          'Plaster_White.IronTeeth', 'IrregularPlanks_MetalForged.IronTeeth', 'WindowsAtlas.IronTeeth'}
require(native <= {m.material for n in model.nodes for m in n.meshes}, 'Missing native palette')
tracks = [(n.name, a) for n in model.nodes for a in n.nodeAnimations]
animated = {'#GroceryMarket.BasketSign', '#GroceryMarket.HoistPulley', '#GroceryMarket.HoistRope', '#GroceryMarket.HoistLoad'}
require({n for n, a in tracks} == animated, 'Market animations differ: '+str(sorted({n for n, a in tracks})))
require(all(len(a.frames) == reg['frameEnd'] for n, a in tracks), 'Market animation lost frames')
require(payload == (folder/'GroceryStore.IronTeeth.ConstructionStage0.Model.timbermesh').read_bytes(), 'Construction export differs')
require(sum(n.name.startswith('#Slot#Entrance') for n in model.nodes) == 1, 'Missing the main-door worker slot')
assembly = read('outputs/reference-studies/GroceryMarket-native-assembly.json')
require(not assembly['liquids'], 'The water-tower barrel must not pretend to be a water inventory')
require(all(p['name'] not in names for p in assembly['props']), 'Native preview props shipped in payload')
require(len(blueprint.get('NativeBuildingPropsSpec', {}).get('Props', [])) == len(assembly['props']), 'Native prop binding mismatch')
# A navmesh spec may only switch on native floors over platformable roofs (roof_deck_content.mjs).
nav = blueprint.get('BlockObjectNavMeshSettingsSpec')
require('BuildingWalkwaySpec' not in blueprint and (nav is None or not (nav['EdgeGroups'] or nav['UnblockedCoordinates'] or nav['BlockedEdges'])),
        'Old gallery walkway data remains')
w, d = reg['footprint']
h = reg['height']
spec = blueprint['BlockObjectSpec']
require([spec['Size'][k] for k in 'XYZ'] == [w, d, h], 'Footprint differs from the registration')
blocks = spec['Blocks']
require(len(blocks) == w*d*h, 'Occupation extent mismatch')
index = lambda x, y, z: (z*d+y)*w+x
door = next(x for x in reg['doors'] if x['id'] == 'MainDoor')
require([spec['Entrance']['Coordinates'][k] for k in 'XYZ'] == door['entrance'], 'Entrance is not the path cell before the main door')
require(blocks[index(*door['doorstep'])]['Occupations'] == 'All', 'Main doorstep is not a building cell')
x0, y0, x1, y1 = (int(v) for v in reg['access']['groundWalk']['mainDoorApproach'])
require(all(blocks[index(x, y, z)]['Occupations'] == 'None' for x in range(x0, x1) for y in range(y0, y1) for z in (0, 1)),
        'Main door walk is blocked')
# The clerk must stand where the native path network reaches: the centre of
# a free ground cell on the entrance route (the Entrance cell or a free cell
# beside it), never inside the solid hall. Unity local XYZ = grid (x, z, y).
clerk = blueprint['GroceryStoreSpec']['ClerkWorkPosition']
clerk_cell = [int(clerk['X'] // 1), int(clerk['Z'] // 1), int(round(clerk['Y']))]
require(clerk['Y'] == 0 and clerk['X'] % 1 == .5 and clerk['Z'] % 1 == .5, 'Clerk position is not a ground cell centre: '+str(clerk))
require(0 <= clerk_cell[0] < w and 0 <= clerk_cell[1] < d, 'Clerk cell outside the footprint: '+str(clerk_cell))
require(blocks[index(*clerk_cell)]['Occupations'] == 'None', 'Clerk cell is not free: '+str(clerk_cell))
require(sum(abs(a - b) for a, b in zip(clerk_cell, door['entrance'])) <= 1, 'Clerk cell is not on the entrance route: '+str(clerk_cell))
bx0, by0, bx1, by1 = reg['access']['stairBay']['bounds']
require(all(blocks[index(x, y, z)]['Occupations'] == 'None' for x in range(bx0, bx1) for y in range(by0, by1) for z in (0, 1)),
        'Stair bay is blocked')
balcony = reg['access']['balcony']
cx0, cy0, cx1, cy1 = (int(v) for v in balcony['bounds'])
deck = [(x, y) for x in range(cx0, cx1) for y in range(cy0, cy1)]
for x, y in deck:
    require(blocks[index(x, y, balcony['layer'])]['Occupations'] == 'None', 'Balcony path cell is occupied')
    require(blocks[index(x, y, balcony['layer']-1)]['Stackable'] == 'BlockObject', 'Balcony lacks native path support')
require(not {'ManufactorySpec', 'WorkshopSpec', 'AttractionSpec', 'StatusHidingEnterableSpec'} & blueprint.keys(), 'Grocery retains factory/attraction behaviors')
shop = read('tools/frontier_progression.json')['groceryStore']
require(blueprint['GroceryStoreSpec']['Foods'] == shop['stock'], 'Assortment differs from canonical data')
require(blueprint['GroceryStoreSpec']['CapacityPerFood'] == 100 and len(shop['stock']) == 6, 'Shelf capacities differ')
require(blueprint['MechanicalNodeSpec'] == {'PowerInput': 100, 'PowerOutput': 0, 'IsShaft': False}, 'Grocery hp roles differ')
require(blueprint['BuildingSpec']['ScienceCost'] == 6000, 'Initial science balance differs')
require(blueprint['WorkplaceSpec']['MaxWorkers'] == 2, 'Clerk capacity differs')
require(blueprint['GroceryStoreSpec']['MinimumStockedFoodTypes'] == 3, 'Stocked-service threshold differs')
report = {'status': 'Source/export checks passed; native shoppers, balcony paths and service pending',
          'sourceSha256': hashlib.sha256((ROOT/'src/DeepFrontier/Art/Source/GroceryMarket-ReferenceStudy.blend').read_bytes()).hexdigest(),
          'exportSha256': hashlib.sha256(payload).hexdigest(), 'size': [w, d, h],
          'nodes': len(model.nodes), 'animatedTracks': sorted(animated), 'nativeProps': len(assembly['props']),
          'entrance': door['entrance'], 'balconyPathCells': deck, 'workers': 2, 'hpDemand': 100, 'hpOutput': 0,
          'science': 6000, 'foods': shop['stock'], 'capacityPerFood': 100,
          'clerkCell': clerk_cell, 'stockStageNodes': stock_nodes, 'stockDisplay': blueprint['GroceryStockDisplaySpec']}
(ROOT/'outputs/civic-integration/grocery-static-checks.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report, indent=2))
