"""Player-built deck roads; only the enclosed interior is part of the building graph."""
from industrial_layouts import layout,grid_lane,edge
from restaurant_structure import ORIGIN,SIZE,PLATFORMS,SUPPORTS,ROOMS,RESERVATIONS,DOORS

R=layout(ORIGIN,SIZE,[1,1,0],[],deck_mode='PlayerPlacedPaths')
R['structure']={'platforms':PLATFORMS,'supports':SUPPORTS,'rooms':ROOMS,'reservations':RESERVATIONS,'doors':DOORS}
# 2026-10-22: the footprint lost its empty first row and column (native -1 in
# x and y). The ground doorstep (1,0,0) is open ground under the dining
# balcony.
# 2026-11-01 second shrink (9x7x5 -> 6x5x3): the interior stair column rises
# at (3,3) through the ground hall and the dining room into the roof
# stairhead, whose door opens onto the roof over the side balcony (4,3,2).
# Each deck has a lane: the front row y 1 (tables on row y 0) and the side
# column x 4 (the side table on x 5, y 2..3).
grid_lane(R,[(1,0,0),(1,1,0),(2,1,0),(2,2,0),(3,2,0),(3,3,0)])
grid_lane(R,[(3,3,z) for z in range(3)])
for z in (1,2):
    grid_lane(R,[(x,1,z) for x in range(0,6)])
    grid_lane(R,[(4,y,z) for y in range(1,5)])
grid_lane(R,[(3,3,1),(3,2,1),(2,2,1)])
edge(R,(2,2,1),(2,1,1))
edge(R,(3,3,2),(4,3,2))
# Open roof cells beside the lanes (the main roof's front row and the side
# roof's back corner), reachable as player decks.
grid_lane(R,[(x,2,2) for x in (1,2,3)])
for x in (1,2,3):edge(R,(x,2,2),(x,1,2))
edge(R,(3,2,2),(4,2,2))
grid_lane(R,[(4,4,2),(5,4,2)])
# 2026-10-31 roof pass (user: no railings on the roofs; "like an actual
# platform where roads can connect"): the balconies and roof are open decks
# with no rails, so there are no rail openings ('ports').
R['interiorCells']=[[1,1,0],[2,1,0],[2,2,0],[3,2,0],[3,3,0],[3,3,1],[3,2,1],[2,2,1],[3,3,2]]
R['doorLinks']=[{'Interior':[1,1,0],'Exterior':[1,0,0]},
                {'Interior':[2,2,1],'Exterior':[2,1,1]},
                {'Interior':[3,3,2],'Exterior':[4,3,2]}]
R['suggestedPathCells']=[n['cell'] for n in R['nodes'] if n['cell'] not in R['interiorCells']]
R['buildableCells']=[[1,2,2],[2,2,2],[3,2,2],[5,4,2]]
# Staff work in the ground hall, the kitchen and the dining room.
R['staffSlots']=[[2.3,2.45,0],[4.6,2.45,0],[1.6,4.45,1],[2.6,4.45,1]]
R['doorNodes']=[d['Interior'] for d in R['doorLinks']]
