"""Explicit waterfront Fishery registration, measured from its isometric model."""
from industrial_layouts import layout,node,edge,lane,grid_lane,port

# 2026-10-22 (user): no forced decoration beyond the walls. The two front
# rows (fish tables, bins, the front basin) and the empty right column left
# the footprint (12x10 -> 11x8): native y is 2 less, ORIGIN y -2; artwork
# and idle points (source coordinates) are unchanged. The ground door's
# approach is now the open tile outside the footprint.
# 2026-10-30 compaction: one layer per storey. The galleries, the upper hall
# door and the warehouse roof terrace are at layer 1 (were 2); the long roof
# stays, lower: 11x8x7 -> 11x8x4. Rail opening IDs keep their numbers.
F=layout([1.25,-1.30,0],[11,8,4],[3,0,0],[[2.0,1.55,0],[3.90,3.12,1],[1.22,5.55,1]],deck_mode='BuiltInWalkways')
F['idleFacing']=[[0,-1],[0,-1],[-1,0]]
lane(F,[(3,0,0),(3,1,0),(4,1,0),(5,1,0),(5,2,0),(5,3,0)],
     [(2,1.55,0),(2,2.8,0),(3,2.8,0),(3.9,2.8,0),(3.9,3.8,0),(3.9,4.8,0)])
lane(F,[(5,3,z) for z in range(2)],[(3.9,4.8,z) for z in range(2)])
lane(F,[(5,3,1),(5,2,1),(5,1,1)],[(3.9,4.8,1),(3.9,3.5,1),(3.9,2.8,1)])
grid_lane(F,[(x,1,1) for x in range(6,9)])
edge(F,(5,1,1),(6,1,1))
grid_lane(F,[(8,y,1) for y in range(1,7)])
grid_lane(F,[(x,6,1) for x in range(2,9)])
# The warehouse roof has its own real doorway into the upper processing hall.
lane(F,[(5,3,1),(4,3,1),(3,3,1),(3,4,1),(2,4,1),(1,4,1)],
     [(3.9,4.8,1),(2.9,4.8,1),(1.9,4.8,1),(1.9,5.55,1),(1.22,5.55,1),(.25,5.8,1)])
grid_lane(F,[(0,4,1),(0,3,1),(1,3,1),(1,4,1)])
edge(F,(0,4,1),(1,4,1))
for x in (5,6,7):port(F,f'FishFront{x}',(x,1,1),(x,0,1),'FishFrontfront')
port(F,'FishFront8',(8,1,1),(8,0,1),'FishRightfront')
for y in range(3,9):port(F,f'FishRight{y}',(8,y-2,1),(9,y-2,1),'FishRightright')
for x in range(2,9):port(F,f'FishRear{x}',(x,6,1),(x,7,1),'FishBack')
for y in (5,6):port(F,f'FishRoofLeft{y}',(0,y-2,1),(-1,y-2,1),'RoofTerraceLeft')
F['interiorCells']=[[3,1,0],[4,1,0],[5,1,0],[5,2,0],[5,3,0],[5,3,1],
                    [5,2,1],[4,3,1],[3,3,1],[3,4,1]]
F['buildableCells']=[[1,3,1],[1,4,1]]
F['staffSlots']=[]
F['doorNodes']=[[3,0,0],[5,2,1],[2,4,1]]
