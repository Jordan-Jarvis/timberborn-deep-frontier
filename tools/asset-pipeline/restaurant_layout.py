"""Player-built deck roads; only the enclosed interior is part of the building graph."""
from industrial_layouts import layout,grid_lane,edge,decorative_port
from restaurant_structure import ORIGIN,SIZE,PLATFORMS,SUPPORTS,ROOMS,RESERVATIONS,DOORS

R=layout(ORIGIN,SIZE,[1,1,0],[],deck_mode='PlayerPlacedPaths')
R['structure']={'platforms':PLATFORMS,'supports':SUPPORTS,'rooms':ROOMS,'reservations':RESERVATIONS,'doors':DOORS}
# 2026-10-22: the footprint lost its empty first row and column (native -1 in
# x and y). The ground doorstep (1,0,0) is open ground under the dining
# balcony; opening IDs keep their original numbers.
# 2026-10-30 compaction: one layer per storey (dining balconies at 1 and 2,
# flat roof at 3). The interior stair column rises at (4,3) through the three
# halls into the roof stairhead; the gabled roof no longer encloses a route.
grid_lane(R,[(1,0,0),(1,1,0),(2,1,0),(2,2,0),(3,2,0),(4,2,0),(4,3,0)])
grid_lane(R,[(4,3,z) for z in range(4)])
for z,prefix in ((1,'Dining'),(2,'UpperDining')):
    grid_lane(R,[(x,1,z) for x in range(0,6)])
    grid_lane(R,[(5,y,z) for y in range(1,7)])
    grid_lane(R,[(x,5,z) for x in range(1,6)])
    grid_lane(R,[(x,6,z) for x in range(1,7)])
    for x in range(1,6):edge(R,(x,5,z),(x,6,z))
    grid_lane(R,[(4,3,z),(4,2,z),(3,2,z)])
    edge(R,(3,2,z),(3,1,z))
    if z==2:
        grid_lane(R,[(6,y,z) for y in range(1,7)])
        for y in range(1,7):
            edge(R,(5,y,z),(6,y,z))
grid_lane(R,[(4,3,3),(5,3,3),(6,3,3)])
for y in (2,3,4):grid_lane(R,[(x,y,3) for x in (6,7,8)])
for x in (6,7,8):
    edge(R,(x,2,3),(x,3,3))
    edge(R,(x,3,3),(x,4,3))
# Every physical boundary segment can open. These bindings neither create nor
# restrict roads, and remain independent of the optional suggested path layout.
for z,prefix in ((1,'Dining'),(2,'UpperDining')):
    for x in range(1,7):decorative_port(R,f'{prefix}Front{x}',(x-1,0,z),(x-1,-1,z),prefix+'Frontfront')
    decorative_port(R,prefix+'Left1',(0,0,z),(-1,0,z),prefix+'Frontleft')
    decorative_port(R,prefix+'Left',(0,1,z),(-1,1,z),prefix+'Frontleft')
    for x in range(2,8):decorative_port(R,f'{prefix}Rear{x}',(x-1,6,z),(x-1,7,z),prefix+'Rearback')
    decorative_port(R,prefix+'RearLeft6',(1,5,z),(0,5,z),prefix+'Rearleft')
    decorative_port(R,prefix+'RearLeft7',(1,6,z),(0,6,z),prefix+'Rearleft')
    for y in range(2,8):decorative_port(R,f'{prefix}Right{y}',(6,y-1,z),(7,y-1,z),prefix+'Sideright')
decorative_port(R,'DiningSideFront',(6,1,1),(6,0,1),'StairAccess')
for x in range(6,10):
    decorative_port(R,f'RoofFront{x}',(x-1,2,3),(x-1,1,3),'RoofTerraceFront')
    decorative_port(R,f'RoofRear{x}',(x-1,4,3),(x-1,5,3),'RoofTerraceRear')
for y in range(3,6):
    decorative_port(R,f'RoofLeft{y}',(5,y-1,3),(4,y-1,3),'RoofTerraceLeft')
    decorative_port(R,f'RoofRight{y}',(8,y-1,3),(9,y-1,3),'RoofTerraceRight')
R['interiorCells']=[[1,1,0],[2,1,0],[2,2,0],[3,2,0],[4,2,0],*[[4,3,z] for z in range(4)],
                    [4,2,1],[3,2,1],[4,2,2],[3,2,2],[5,3,3]]
R['doorLinks']=[{'Interior':[1,1,0],'Exterior':[1,0,0]},
                {'Interior':[3,2,1],'Exterior':[3,1,1]},
                {'Interior':[3,2,2],'Exterior':[3,1,2]},
                {'Interior':[5,3,3],'Exterior':[6,3,3]}]
R['suggestedPathCells']=[n['cell'] for n in R['nodes'] if n['cell'] not in R['interiorCells']]
R['buildableCells']=[[x,y,3] for x in (6,7,8) for y in (2,3,4)]
# The two ground staff markers stood at the removed outdoor counters; they are
# inside the ground hall now, off the freed ground.
R['staffSlots']=[[3,2.45,0],[4.3,2.45,0],[5.3,5.35,1],[5.3,5.35,2]]
R['doorNodes']=[d['Interior'] for d in R['doorLinks']]
