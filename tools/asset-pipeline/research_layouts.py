"""Explicit registration of the Materials Laboratory's existing architecture."""
import json
from pathlib import Path
from industrial_layouts import layout,lane,grid_lane,edge,port

# Idle slots stand 8 cm in front of each door casing (ground casing on y=0).
LAB=layout([0,0,0],[10,8,9],[1,0,0],[[1.35,-.08,0],[1.65,-.08,0],[1.35,2.92,2],[1.65,2.92,2]],deck_mode='BuiltInWalkways')
lane(LAB,[(1,0,0),(1,1,0),(1,2,0),(1,3,0)],
     [(1.5,.5,0),(1.5,1.5,0),(1.5,2.5,0),(1.5,3.5,0)])
lane(LAB,[(1,3,z) for z in range(3)],[(1.5,3.5,z) for z in range(3)])
for y in range(3):grid_lane(LAB,[(x,y,2) for x in range(3)])
for x in range(3):grid_lane(LAB,[(x,y,2) for y in range(3)])
edge(LAB,(1,3,2),(1,2,2))
for x in range(3):port(LAB,f'Front{x}',(x,0,2),(x,-1,2),f'TerraceFront{x}')
for y in range(3):port(LAB,f'Left{y}',(0,y,2),(-1,y,2),f'TerraceLeft{y}')
port(LAB,'Right0',(2,0,2),(3,0,2),'TerraceRight0')
LAB['interiorCells']=[[1,y,0] for y in range(1,4)]+[[1,3,1],[1,3,2]]
LAB['buildableCells']=[[x,y,2] for y in range(2) for x in range(3)]
LAB['doorNodes']=[[1,0,0],[1,2,2]]
LAYOUTS={'MaterialsLaboratory':LAB}

if __name__=='__main__':
    for a,b in LAB['edges']:
        if sum(abs(a[i]-b[i]) for i in range(3))!=1:raise ValueError('Research route must use unit edges')
    path=Path(__file__).resolve().parents[1]/'research-layouts.json'
    path.write_text(json.dumps(LAYOUTS,indent=2)+'\n')
    print(path)
