"""Explicit routes for the approved Grocery Store isometric artwork.

Keep the saved source architecture at its authored scale. This registration
becomes active only with the corresponding occupancy, inventory and service.
"""
from industrial_layouts import layout, lane, node, edge, port

# A zero Y origin keeps the front-gallery points inside their authored row.
# It also keeps rail cuts away from the source's 3.699999809 post.
GROCERY = layout([.4, 0, 0], [11, 9, 9], [2, 0, 0], [],deck_mode='BuiltInWalkways')
d = GROCERY
lane(d, [(2, y, 0) for y in range(4)],
     [(1.6, .35, 0), (1.6, 1.1, 0), (1.6, 2.10, 0), (1.6, 3.2, 0)])
lane(d, [(2, 3, 0), (3, 3, 0), (4, 3, 0)],
     [(1.6, 3.2, 0), (2.9, 3.2, 0), (4.1, 3.2, 0)])
lane(d, [(4, 3, z) for z in range(7)], [(4.1, 3.2, z) for z in range(7)])
interior = {(2, 3, 0), (3, 3, 0)} | {(4, 3, z) for z in range(7)}
for z, front, side, rear, door_x in (
    (2, 'ShopFront', 'ShopSide', 'ShopRear', 4.08),
    (4, 'UpperShopFront', 'UpperShopSide', 'UpperShopRear', 4.1),
):
    lane(d, [(x, 2, z) for x in range(1, 8)],
         [(x, 2.35, z) for x in (1.3, 2.1, 3.1, door_x, 5.1, 6.1, 7.0)])
    lane(d, [(7, y, z) for y in range(2, 7)],
         [(7.0, y, z) for y in (2.35, 3.2, 4.2, 5.2, 6.5)])
    lane(d, [(x, 6, z) for x in range(2, 8)],
         [(x, 6.5, z) for x in (2.0, 3.1, 4.1, 5.1, 6.1, 7.0)])
    edge(d, (4, 2, z), (4, 3, z))
    for x in range(1, 7):
        point = next(n['point'] for n in d['nodes'] if n['cell'] == [x, 2, z])
        node(d, (x, 1, z), (point[0], 1.95, z))
        edge(d, (x, 1, z), (x, 2, z))
        port(d, f'Gallery{z}Front{x}', (x, 1, z), (x, 0, z), front+'front')
    port(d, f'Gallery{z}Left', (1, 2, z), (0, 2, z), front+'left')
    port(d, f'Gallery{z}Stairs', (7, 2, z), (7, 1, z), side+'front')
    for y in range(2, 7):
        port(d, f'Gallery{z}Right{y}', (7, y, z), (8, y, z), side+'right')
    for x in range(2, 7):
        port(d, f'Gallery{z}Rear{x}', (x, 6, z), (x, 7, z), rear+'back')

lane(d, [(4, 3, 6), (5, 3, 6), (6, 3, 6), (6, 4, 6), (7, 4, 6), (8, 4, 6), (9, 4, 6)],
     [(4.1, 3.2, 6), (5.1, 3.2, 6), (6.1, 3.2, 6), (6.1, 4.7, 6),
      (6.78, 4.7, 6), (8.1, 4.7, 6), (9.1, 4.7, 6)])
interior.update([(5, 3, 6), (6, 3, 6), (6, 4, 6), (7, 4, 6)])
lane(d, [(8, 3, 6), (8, 4, 6), (8, 5, 6)],
     [(8.1, 3.6, 6), (8.1, 4.7, 6), (8.1, 5.3, 6)])
port(d, 'RoofFront', (8, 3, 6), (8, 2, 6), 'RoofTerraceFront')
port(d, 'RoofRight', (9, 4, 6), (10, 4, 6), 'RoofTerraceRight')
d['interiorCells'] = [list(c) for c in sorted(interior)]
d['buildableCells'] = [[8, 4, 6]]
d['staffSlots'] = []
d['doorNodes'] = [[2, 2, 0], [4, 3, 2], [4, 3, 4], [7, 4, 6]]
d['localAccess'] = [2.0, 0, 1.90]

if __name__ == '__main__':
    import json
    from industrial_layouts import ROOT
    cells = {tuple(n['cell']) for n in d['nodes']}
    graph = {c: set() for c in cells}
    for a, b in d['edges']:
        a, b = tuple(a), tuple(b)
        if a not in cells or b not in cells or sum(abs(a[i]-b[i]) for i in range(3)) != 1:
            raise ValueError('Invalid Grocery Store route edge')
        graph[a].add(b)
        graph[b].add(a)
    seen = set()
    pending = [tuple(d['entrance'])]
    while pending:
        c = pending.pop()
        if c in seen:
            continue
        seen.add(c)
        pending.extend(graph[c]-seen)
    if seen != cells:
        raise ValueError('Disconnected Grocery Store routes')
    for cell in cells:
        if not all(0 <= v < limit for v, limit in zip(cell, d['size'])):
            raise ValueError('Grocery Store route outside registration')
    for n in d['nodes']:
        for axis in (0, 1):
            p = n['point'][axis] + d['origin'][axis]
            if not n['cell'][axis] <= p < n['cell'][axis]+1:
                raise ValueError(f"Grocery waypoint lies outside its authored cell: {n}")
    (ROOT/'outputs/civic-integration/GroceryStore-registration-candidate.json').write_text(
        json.dumps({'status': 'Source registration candidate; native integration pending', 'layout': d}, indent=2)+'\n',
        encoding='utf-8')
    print('Grocery Store registration:', len(cells), 'cells,', len(d['ports']), 'openings, four doors')
