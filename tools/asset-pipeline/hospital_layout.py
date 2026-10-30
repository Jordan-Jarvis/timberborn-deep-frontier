"""Explicit hospital doors, player-owned decks and enclosed internal links.

Front and back balconies only (2026-10-21); the side decks are gone. Every
balcony has its own door into the enclosed interior network.

2026-10-30 (user): the two ward wings are removed; only the central pavilion
remains (4x9). Its rear decks, roof garden and their doors are unchanged in
shape; the ward corridors and ward doors went with the wings. Rail opening
IDs keep their original numbers (Rear4..Rear7, UpperRear4..UpperRear7).
"""
from industrial_layouts import layout,grid_lane,edge,decorative_port
from hospital_structure import ORIGIN,SIZE,ROOMS,PLATFORMS,SUPPORTS,DOORS,RESERVATIONS

HOSPITAL=layout(ORIGIN,SIZE,[2,0,0],[],deck_mode='PlayerPlacedPaths')
d=HOSPITAL
d['structure']={'platforms':PLATFORMS,'supports':SUPPORTS,'rooms':ROOMS,'reservations':RESERVATIONS,'doors':DOORS}
# Enclosed interior network: ground door, central stair core and the rear
# corridors to each deck door. The ground door is on the footprint edge, its
# doorstep outside.
grid_lane(d,[(2,y,0) for y in range(5)])
grid_lane(d,[(2,4,z) for z in range(7)])
grid_lane(d,[(2,y,2) for y in range(4,9)])
grid_lane(d,[(2,y,4) for y in range(4,9)])
grid_lane(d,[(2,y,6) for y in range(4,8)])
# Suggested roads on the player-owned balconies; they never become
# building-owned paths.
grid_lane(d,[(x,8,2) for x in range(4)])
grid_lane(d,[(x,8,4) for x in range(4)])
for y in (5,6,7):grid_lane(d,[(x,y,6) for x in range(4)])
for x in range(4):
    for y in (5,6):edge(d,(x,y,6),(x,y+1,6))
# Every physical balcony boundary segment can open.
for x in range(4,8):decorative_port(d,f'Rear{x}',(x-4,8,2),(x-4,9,2),'RearOuter')
decorative_port(d,'RearLeft',(0,8,2),(-1,8,2),'RearLeft')
decorative_port(d,'RearRight',(3,8,2),(4,8,2),'RearRight')
for x in range(4,8):decorative_port(d,f'UpperRear{x}',(x-4,8,4),(x-4,9,4),'UpperRearOuter')
decorative_port(d,'UpperRearWest',(0,8,4),(-1,8,4),'UpperRearLeft')
decorative_port(d,'UpperRearEast',(3,8,4),(4,8,4),'UpperRearRight')
for y in range(5,8):
    decorative_port(d,f'RoofLeft{y}',(0,y,6),(-1,y,6),'RoofGardenLeft')
    decorative_port(d,f'RoofRight{y}',(3,y,6),(4,y,6),'RoofGardenRight')
for x in range(4,8):decorative_port(d,f'RoofRear{x}',(x-4,7,6),(x-4,8,6),'RoofGardenRear')
interior={(2,y,0) for y in range(0,5)}|{(2,4,z) for z in range(7)}
interior|={(2,y,2) for y in range(4,8)}|{(2,y,4) for y in range(4,8)}
d['interiorCells']=[list(c) for c in sorted(interior)]
d['doorLinks']=[{'Interior':[2,0,0],'Exterior':[2,-1,0]},
                {'Interior':[2,7,2],'Exterior':[2,8,2]},
                {'Interior':[2,7,4],'Exterior':[2,8,4]},
                {'Interior':[2,4,6],'Exterior':[2,5,6]}]
d['suggestedPathCells']=[n['cell'] for n in d['nodes'] if n['cell'] not in d['interiorCells']]
d['buildableCells']=[[x,y,6] for x in range(4) for y in range(5,8)]
d['staffSlots']=[]
d['doorNodes']=[link['Interior'] for link in d['doorLinks']]
d['patientCapacity']=30
d['localAccess']=[2.5,0,0]
# Staff attend this interior ward point (native XYZ with Y up), in the
# pavilion's ground hall (cell (2,3,0)); it was (6.5,0,3.5) before the
# wings were removed, the same pavilion cell.
d['wardWorkPosition']=[2.5,0,3.5]
