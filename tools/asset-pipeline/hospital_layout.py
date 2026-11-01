"""Explicit hospital doors, player-owned decks and enclosed internal links.

Front and back balconies only (2026-10-21); the side decks are gone. Every
balcony has its own door into the enclosed interior network.

2026-10-30 (user): the two ward wings are removed; only the central pavilion
remains (4x9). Its rear decks, roof garden and their doors are unchanged in
shape; the ward corridors and ward doors went with the wings.

2026-10-31 roof pass: no deck rails; the decks are open platforms.

2026-11-01 second shrink pass: 4x4x4. Ground door, an interior corridor to
the stairhead on the back-right corner (3,3) and its door onto the layer-2
roof garden; no rear decks.
"""
from industrial_layouts import layout,grid_lane,edge
from hospital_structure import ORIGIN,SIZE,ROOMS,PLATFORMS,SUPPORTS,DOORS,RESERVATIONS

HOSPITAL=layout(ORIGIN,SIZE,[2,0,0],[],deck_mode='PlayerPlacedPaths')
d=HOSPITAL
d['structure']={'platforms':PLATFORMS,'supports':SUPPORTS,'rooms':ROOMS,'reservations':RESERVATIONS,'doors':DOORS}
# Enclosed interior network: ground door, the ground corridor to the
# stairhead column (3,3) and its stair core to the roof door. The ground door
# is on the footprint edge, its doorstep outside.
grid_lane(d,[(2,y,0) for y in range(4)]+[(3,3,0)])
grid_lane(d,[(3,3,z) for z in range(3)])
# Suggested roads on the player-owned roof garden (layer 2); they never
# become building-owned paths. The stairhead door opens onto (3,2,2).
grid_lane(d,[(3,3,2),(3,2,2)])
grid_lane(d,[(x,2,2) for x in range(4)])
grid_lane(d,[(x,3,2) for x in range(3)])
for x in range(3):edge(d,(x,2,2),(x,3,2))
# 2026-10-31 roof pass: no rails, so no rail openings ('ports').
interior={(2,y,0) for y in range(4)}|{(3,3,z) for z in range(3)}
d['interiorCells']=[list(c) for c in sorted(interior)]
d['doorLinks']=[{'Interior':[2,0,0],'Exterior':[2,-1,0]},
                {'Interior':[3,3,2],'Exterior':[3,2,2]}]
d['suggestedPathCells']=[n['cell'] for n in d['nodes'] if n['cell'] not in d['interiorCells']]
# The roof garden's clear area: the cells beside the stairhead and its door
# step (the front-roof eave timber reaches 0.1 over row 2, as before).
d['buildableCells']=[[x,y,2] for x in range(3) for y in (2,3)]
d['staffSlots']=[]
d['doorNodes']=[link['Interior'] for link in d['doorLinks']]
d['patientCapacity']=30
d['localAccess']=[2.5,0,0]
# Staff attend this interior ward point (native XYZ with Y up), in the
# ground ward (cell (2,3,0)); the same cell since the wings were removed.
d['wardWorkPosition']=[2.5,0,3.5]
