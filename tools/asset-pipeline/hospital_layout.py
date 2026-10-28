"""Explicit hospital doors, player-owned decks and enclosed internal links.

Front and back balconies only (2026-10-21); the side decks are gone. Every
balcony has its own door into the enclosed interior network.
"""
from industrial_layouts import layout,grid_lane,edge,decorative_port
from hospital_structure import ORIGIN,ROOMS,PLATFORMS,SUPPORTS,DOORS,RESERVATIONS

HOSPITAL=layout(ORIGIN,[12,9,9],[6,0,0],[],deck_mode='PlayerPlacedPaths')
d=HOSPITAL
d['structure']={'platforms':PLATFORMS,'supports':SUPPORTS,'rooms':ROOMS,'reservations':RESERVATIONS,'doors':DOORS}
# Enclosed interior network: ground door, central stair core and one
# corridor per balcony door. The footprint ends at the pavilion front wall
# (2026-10-22): the ground door is on the edge, its doorstep outside.
grid_lane(d,[(6,y,0) for y in range(5)])
grid_lane(d,[(6,4,z) for z in range(7)])
grid_lane(d,[(x,4,2) for x in range(2,10)])
grid_lane(d,[(2,y,2) for y in range(0,5)])
grid_lane(d,[(9,y,2) for y in range(0,5)])
grid_lane(d,[(6,y,2) for y in range(4,9)])
grid_lane(d,[(6,y,4) for y in range(4,9)])
grid_lane(d,[(6,y,6) for y in range(4,8)])
# Suggested roads on the player-owned balconies; they never become
# building-owned paths.
grid_lane(d,[(x,0,2) for x in range(4)])
grid_lane(d,[(x,0,2) for x in range(8,12)])
grid_lane(d,[(x,8,2) for x in range(12)])
grid_lane(d,[(x,8,4) for x in range(3,9)])
for y in (5,6,7):grid_lane(d,[(x,y,6) for x in range(4,8)])
for x in range(4,8):
    for y in (5,6):edge(d,(x,y,6),(x,y+1,6))
# Every physical balcony boundary segment can open.
for x in range(4):decorative_port(d,f'WestFront{x}',(x,0,2),(x,-1,2),'WestFrontOuter')
decorative_port(d,'WestFrontLeft',(0,0,2),(-1,0,2),'WestFrontLeft')
for x in range(8,12):decorative_port(d,f'EastFront{x}',(x,0,2),(x,-1,2),'EastFrontOuter')
decorative_port(d,'EastFrontRight',(11,0,2),(12,0,2),'EastFrontRight')
for x in range(12):decorative_port(d,f'Rear{x}',(x,8,2),(x,9,2),'RearOuter')
decorative_port(d,'RearLeft',(0,8,2),(-1,8,2),'RearLeft')
decorative_port(d,'RearRight',(11,8,2),(12,8,2),'RearRight')
for x in range(3,9):decorative_port(d,f'UpperRear{x}',(x,8,4),(x,9,4),'UpperRearOuter')
decorative_port(d,'UpperRearWest',(3,8,4),(2,8,4),'UpperRearLeft')
decorative_port(d,'UpperRearEast',(8,8,4),(9,8,4),'UpperRearRight')
for y in range(5,8):
    decorative_port(d,f'RoofLeft{y}',(4,y,6),(3,y,6),'RoofGardenLeft')
    decorative_port(d,f'RoofRight{y}',(7,y,6),(8,y,6),'RoofGardenRight')
for x in range(4,8):decorative_port(d,f'RoofRear{x}',(x,7,6),(x,8,6),'RoofGardenRear')
interior={(6,y,0) for y in range(0,5)}|{(6,4,z) for z in range(7)}
interior|={(x,4,2) for x in range(2,10)}|{(2,y,2) for y in range(1,5)}|{(9,y,2) for y in range(1,5)}
interior|={(6,y,2) for y in range(4,8)}|{(6,y,4) for y in range(4,8)}
d['interiorCells']=[list(c) for c in sorted(interior)]
d['doorLinks']=[{'Interior':[6,0,0],'Exterior':[6,-1,0]},
                {'Interior':[2,1,2],'Exterior':[2,0,2]},
                {'Interior':[9,1,2],'Exterior':[9,0,2]},
                {'Interior':[6,7,2],'Exterior':[6,8,2]},
                {'Interior':[6,7,4],'Exterior':[6,8,4]},
                {'Interior':[6,4,6],'Exterior':[6,5,6]}]
d['suggestedPathCells']=[n['cell'] for n in d['nodes'] if n['cell'] not in d['interiorCells']]
d['buildableCells']=[[x,y,6] for x in range(4,8) for y in range(5,8)]
d['staffSlots']=[]
d['doorNodes']=[link['Interior'] for link in d['doorLinks']]
d['patientCapacity']=30
d['localAccess']=[6.5,0,0]
