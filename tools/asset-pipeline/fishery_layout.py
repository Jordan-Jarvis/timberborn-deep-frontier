"""Explicit waterfront Fishery registration, measured from its isometric model."""
from industrial_layouts import layout,node,edge,lane,grid_lane

# Second shrink pass (2026-11-01, user: "shrink the buildings down even more"):
# 11x8x4 -> 6x5x3, art in native grid coordinates (fishery_works_geometry.py,
# origin [0,0,0]; until now the art had its own source frame, origin
# [1.25,-1.30,0]). Same origin and ground door cell (3,0,0), so the native
# Entrance stays the path cell (3,-1,0). The galleries, the warehouse roof
# terrace and its door house are gone: the lower hall's flat roof is the one
# player-path deck (PlatformDeckSpec), and the upper hall door is its door
# link. Three worker idle slots (three workers): two at the ground door, one
# at the upper hall door.
F=layout([0,0,0],[6,5,3],[3,0,0],[[3.5,.09,0],[3.5,1.94,1],[3.5,.09,0]],deck_mode='PlayerPlacedPaths')
F['idleFacing']=[[0,-1],[0,-1],[0,-1]]
# Interior route: the ground door, the hall and the stair up to the upper hall door.
lane(F,[(3,0,0),(3,1,0),(3,2,0),(3,2,1)],[(3.5,.5,0),(3.5,1.5,0),(3.5,2.5,0),(3.5,2.5,1)])
# Deck cells on the lower hall's roof (layer 1): the front two rows and the
# right column beside the upper hall.
grid_lane(F,[(x,1,1) for x in range(2,6)])
grid_lane(F,[(x,0,1) for x in range(2,6)])
edge(F,(2,0,1),(2,1,1))
grid_lane(F,[(5,1,1),(5,2,1),(5,3,1)])
edge(F,(3,2,1),(3,1,1))
F['interiorCells']=[[3,0,0],[3,1,0],[3,2,0],[3,2,1]]
F['buildableCells']=[]
F['staffSlots']=[]
F['doorNodes']=[[3,0,0],[3,2,1]]
# Deck door link: the upper hall door (doorstep (3,2,1)) opens on the deck at (3,1,1).
F['doorLinks']=[{'Interior':[3,2,1],'Exterior':[3,1,1]}]
F['suggestedPathCells']=[n['cell'] for n in F['nodes'] if n['cell'] not in F['interiorCells']]
