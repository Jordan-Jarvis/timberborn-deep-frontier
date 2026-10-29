"""Validate staged civic exports without claiming runtime navigation or service."""
import collections
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2
from native_uv_contract import valid_native_uv

def read_json(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))

def require(condition, detail):
    if not condition:
        raise ValueError(detail)

ident = 'Restaurant'
staging = ROOT / 'outputs/civic-integration'
folder = staging / 'Data/Buildings/Food/Restaurant'
model_path = folder / 'Restaurant.IronTeeth.Model.timbermesh'
payload = model_path.read_bytes()
model = model_pb2.Model()
model.ParseFromString(zlib.decompress(payload))
names = collections.Counter(n.name for n in model.nodes)
require(all(v == 1 for v in names.values()), 'Duplicate exported node names')
visitor = read_json('outputs/reference-studies/Restaurant-visitor-manifest.json')
expected_seats = {'#Slot#' + s['id'] for s in visitor['visitorSeats']}
require(len(expected_seats) == 14, 'Restaurant must have fourteen authored diner seats')
require({n for n in names if n.startswith('#Slot#Seat')} == expected_seats, 'Diner slot mismatch')
require({n for n in names if n.startswith('#Slot#Staff')} == {f'#Slot#Staff{i}' for i in range(4)}, 'Staff slot mismatch')
native = {'BaseWood_DarkBrown.IronTeeth', 'IrregularPlanks_DarkBrown.IronTeeth',
          'RoofPlanks.IronTeeth', 'BaseMetal.IronTeeth', 'Details.IronTeeth',
          'Plaster_White.IronTeeth', 'Plaster_Orange.IronTeeth',
          'IrregularPlanks_MetalForged.IronTeeth', 'WindowsAtlas.IronTeeth',
          'BaseWood_Brown.Folktails'}
materials = {m.material for n in model.nodes for m in n.meshes}
require(native <= materials, 'Missing native civic palette materials')
require(not ({f'DFIndustrial{i:02d}' for i in (0, 1, 2, 3, 7, 27, 28, 29)} & materials), 'Native palette replaced by custom material')
uv_count = 0
for node in model.nodes:
    meshes = [m for m in node.meshes if m.material in native]
    if not meshes:
        continue
    uv = next(p for p in node.vertexProperties if p.name == 'uv0')
    coords = list(struct.iter_unpack('<ff', uv.data))
    for mesh in meshes:
        for index in set(mesh.indices):
            # Authored UVs use inset atlas islands. Reused finished pieces
            # retain exact source UV pairs, including native boundary values.
            require(valid_native_uv(mesh.material,coords[index]),
                    f'UV is neither inset nor an exact source pair: {node.name}/{mesh.material}/{index}')
            uv_count += 1
tracks = [(n.name, a) for n in model.nodes for a in n.nodeAnimations]
require(len(tracks) == 1 and tracks[0][0] == '#Restaurant.CarvedSign', 'Unexpected animation bindings')
require(len(tracks[0][1].frames) == 61, 'Restaurant sign must retain its 61 frame clip')
require(payload == (folder / 'Restaurant.IronTeeth.ConstructionStage0.Model.timbermesh').read_bytes(), 'Construction-stage binding changed')

layout = read_json('tools/civic-layouts.json')[ident]
walkway = read_json('outputs/civic-integration/Restaurant-platform-deck.json')
cells = {tuple(n['cell']) for n in layout['nodes']}
require(len(cells) == len(layout['nodes']), 'Duplicate native graph cells')
graph = {c: set() for c in cells}
for a, b in layout['edges']:
    a, b = tuple(a), tuple(b)
    require(a in cells and b in cells, f'Edge without nodes: {a}/{b}')
    require(sum(abs(a[i] - b[i]) for i in range(3)) == 1, f'Non-unit edge: {a}/{b}')
    graph[a].add(b)
    graph[b].add(a)
visited = set()
queue = [tuple(layout['entrance'])]
while queue:
    current = queue.pop()
    if current in visited:
        continue
    visited.add(current)
    queue.extend(graph[current] - visited)
require(visited == cells, f'Disconnected authored route cells: {cells - visited}')
require(all(tuple(p) in visited for p in layout['doorNodes'] + layout['buildableCells']), 'Disconnected door or terrace support cell')
require(len(walkway['Openings']) == len(layout['ports']) == 59, 'Expected all fifty-nine physical deck-edge openings')
require(len({p['Id'] for p in walkway['Openings']}) == 59, 'Duplicate opening IDs')
require(len(walkway['Doors'])==4 and all(not p['ShownNodes'] for p in walkway['Openings']), 'Whole-tile decks must not need connection-only filler planks')
for opening in walkway['Openings']:
    for name in opening['HiddenNodes'] + opening['ShownNodes']:
        require(names[name] == 1, f'Missing adaptive railing node: {name}')

# The 2026-10-29 triangle-budget review (20k grand cap) supersedes the
# 2026-10-22 one, which superseded the 2026-10-21 exterior-repair capture
# (archive_triangle_budget_review.py --review 2026-10-29).
review = next(r for r in read_json('docs/art/reviews/2026-10-29-triangle-budget-20k/review.json')['renders'] if r['model'] == ident)
require(hashlib.sha256((ROOT / review['source']).read_bytes()).hexdigest() == review['sourceSha256'], 'Source scene changed after native style review capture')
seat_clearances=[]
rails=read_json('outputs/reference-studies/Restaurant-rail-manifest.json')
post=read_json('tools/asset-pipeline/housing-railing.json')['parts']['post']
post_half_width=[max(abs(v[0]-1) for v in post['vertices']),max(abs(v[2]-.05) for v in post['vertices'])]
for seat in visitor['visitorSeats']:
    x,y,z=seat['position']
    require(abs(z-seat['seatSurfaceHeight'])<1e-6, 'Sitting marker is not at the chair seat: '+seat['id'])
    exported=next(n for n in model.nodes if n.name=='#Slot#'+seat['id'])
    require(all(abs(a-b)<1e-5 for a,b in zip((exported.position.x,exported.position.y,exported.position.z),(x,z,y))), 'Seat translation changed during official export')
    # Unity local +Z is the native sitting direction. Check the actual exported
    # quaternion as well as source-facing metadata.
    q=exported.rotation
    forward=(2*(q.x*q.z+q.w*q.y),1-2*(q.x*q.x+q.y*q.y))
    require(all(abs(a-b)<1e-5 for a,b in zip(forward,seat['facing'])), 'Exported diner faces away from its table: '+seat['id'])
    low,high=seat['chairBounds'];minimum=float('inf')
    for run in rails['runs']:
        for panel in run['panels']:
            a,b=panel['start'],panel['end']
            if abs(a[2]-seat['deckHeight'])>1e-5:continue
            # All authored runs are axis-aligned. Include their post half-width.
            pmin=[min(a[i],b[i])-post_half_width[i] for i in (0,1)]
            pmax=[max(a[i],b[i])+post_half_width[i] for i in (0,1)]
            dx=max(pmin[0]-high[0],low[0]-pmax[0],0)
            dy=max(pmin[1]-high[1],low[1]-pmax[1],0)
            gap=(dx*dx+dy*dy)**.5;minimum=min(minimum,gap)
            require(gap>.025, 'Chair intersects a railing or post: '+seat['id'])
    seat_clearances.append({'seat':seat['id'],'railClearance':minimum,'anchorHeight':z,'facing':list(forward)})
assembly = read_json('outputs/reference-studies/Restaurant-native-assembly.json')
require(all(not any(p['name'] in name for name in names) for p in assembly['props']), 'Preview native props included in exported payload')
report = {
    'scope': 'Staged mesh and authored graph only. Runtime occupancy, district access, native props, seating height and staffed meal service remain unverified.',
    'model': ident, 'sha256': hashlib.sha256(payload).hexdigest(), 'nodes': len(model.nodes),
    'dinerSlots': 14, 'staffMarkers': 4, 'nativeUvVerticesChecked': uv_count,
    'animationTracks': 1, 'frames': 61, 'openings': 59, 'connectedSuggestedRouteCells': len(cells),
    'doorLevels': sorted({c[2] for c in layout['doorNodes']}),
    'nativePropsForRuntimeAssembly': len(assembly['props']), 'reviewSceneMatches': True,
    'seatingGeometry':seat_clearances
}
(staging / 'static-checks.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report))
