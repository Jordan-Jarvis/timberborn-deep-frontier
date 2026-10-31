"""Player-built deck roads; only the enclosed interior is part of the building graph."""
from industrial_layouts import layout,grid_lane,edge
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
# 2026-10-31 roof pass (user: no railings on the roofs; "like an actual
# platform where roads can connect"): the balconies and roof are open decks
# with no rails, so there are no rail openings ('ports').
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
