"""Explicit registration of the Materials Laboratory's existing architecture."""
import json
from pathlib import Path
from industrial_layouts import layout,lane,grid_lane,edge,port

# Idle slots stand 8 cm in front of each door casing (ground casing on y=0).
# 2026-10-30 compaction: one layer per storey; the terrace and the records
# office door are at layer 1 (were 2), 10x8x9 -> 10x8x5.
# 2026-10-30 (user: every flat roof tile placeable like a platform): the
# terrace is a player-placed-path deck (PlatformDeckSpec, as the Restaurant,
# Hospital and Hatchery decks), no longer a built-in walkway; its nodes are
# suggested path cells, the records office door the one deck door link.
LAB=layout([0,0,0],[10,8,5],[1,0,0],[[1.35,-.08,0],[1.65,-.08,0],[1.35,2.92,1],[1.65,2.92,1]],deck_mode='PlayerPlacedPaths')
lane(LAB,[(1,0,0),(1,1,0),(1,2,0),(1,3,0)],
     [(1.5,.5,0),(1.5,1.5,0),(1.5,2.5,0),(1.5,3.5,0)])
lane(LAB,[(1,3,z) for z in range(2)],[(1.5,3.5,z) for z in range(2)])
for y in range(3):grid_lane(LAB,[(x,y,1) for x in range(3)])
for x in range(3):grid_lane(LAB,[(x,y,1) for y in range(3)])
edge(LAB,(1,3,1),(1,2,1))
for x in range(3):port(LAB,f'Front{x}',(x,0,1),(x,-1,1),f'TerraceFront{x}')
for y in range(3):port(LAB,f'Left{y}',(0,y,1),(-1,y,1),f'TerraceLeft{y}')
port(LAB,'Right0',(2,0,1),(3,0,1),'TerraceRight0')
# The door cell is interior too since the terrace sits one layer up, right
# over it (2026-10-30): its solid cast cell carries the terrace slab.
LAB['interiorCells']=[[1,y,0] for y in range(0,4)]+[[1,3,1]]
LAB['buildableCells']=[[x,y,1] for y in range(2) for x in range(3)]
LAB['doorNodes']=[[1,0,0],[1,2,1]]
LAB['doorLinks']=[{'Interior':[1,3,1],'Exterior':[1,2,1]}]
LAB['suggestedPathCells']=[n['cell'] for n in LAB['nodes'] if n['cell'] not in LAB['interiorCells']]
LAYOUTS={'MaterialsLaboratory':LAB}

if __name__=='__main__':
    for a,b in LAB['edges']:
        if sum(abs(a[i]-b[i]) for i in range(3))!=1:raise ValueError('Research route must use unit edges')
    path=Path(__file__).resolve().parents[1]/'research-layouts.json'
    path.write_text(json.dumps(LAYOUTS,indent=2)+'\n')
    print(path)
