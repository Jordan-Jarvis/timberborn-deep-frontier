"""Check the explicit Grocery Store routes against its approved saved mesh."""
import json
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from grocery_layout import GROCERY as d
from civic_isometric_geometry import CIVIC_ACCESS, CIVIC_TERRACES
from civic_validation import validate_civic_walks

source = ROOT/'src/DeepFrontier/Art/Source/GroceryStore-ReferenceStudy.blend'
if Path(bpy.data.filepath) != source:
    raise ValueError('Open the canonical Grocery Store study')
points = {tuple(n['cell']): n['point'] for n in d['nodes']}
interior = {tuple(c) for c in d['interiorCells']}
reports = {}
for z in (2, 4, 6):
    routes = []
    for a, b in d['edges']:
        a, b = tuple(a), tuple(b)
        if a[2] == z and b[2] == z and a not in interior and b not in interior:
            routes.append([points[a][:2], points[b][:2]])
    if not routes:
        raise ValueError('No public Grocery Store routes on layer '+str(z))
    CIVIC_ACCESS['GroceryStore']['routes'] = routes
    CIVIC_ACCESS['GroceryStore']['balconyLayers'] = [z]
    reports[str(z)] = validate_civic_walks('GroceryStore', bpy.data.collections['GroceryStore.ReferenceStudy'], bpy.context.scene)
x0, y0, x1, y1 = CIVIC_TERRACES['GroceryStore']['clearArea']
for x, y, z in d['buildableCells']:
    lo_x, lo_y = x-d['origin'][0], y-d['origin'][1]
    if not (x0 <= lo_x and y0 <= lo_y and lo_x+1 <= x1 and lo_y+1 <= y1 and z == 6):
        raise ValueError('Grocery platform support extends beyond the clear terrace')
report = {'status': 'Source clearance only; native integration pending', 'publicLayers': reports,
          'routeCells': len(d['nodes']), 'railOpenings': len(d['ports']), 'buildableCells': d['buildableCells']}
(ROOT/'outputs/civic-integration/GroceryStore-candidate-clearance.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print('Grocery Store public routes and full terrace cells passed')
