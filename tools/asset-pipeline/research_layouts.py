"""Explicit registration of the Materials Laboratory's existing architecture."""
import json
from pathlib import Path
from industrial_layouts import layout,lane

# Idle slots stand 8 cm in front of the ground door casing (y=0).
# 2026-10-30 compaction: one layer per storey (10x8x9 -> 10x8x5).
# Second shrink pass (2026-11-01, 10x8x5 -> 5x4x3): the testing hall on a
# 3x3 base behind a one-tile entrance annex, the press and the instrument
# tower in the right column. The records office and its terrace door went:
# the terrace on the annex roof (cells x 0..2, y 0, layer 1) is an ordinary
# platformable roof deck (roof_deck_content.mjs), reached by player stairs or
# a neighbouring roof, with no deck door link; all four idle slots wait at
# the ground door. Same origin and ground door cell (1,0,0).
LAB=layout([0,0,0],[5,4,3],[1,0,0],[[1.2,-.08,0],[1.4,-.08,0],[1.6,-.08,0],[1.8,-.08,0]],deck_mode='PlayerPlacedPaths')
lane(LAB,[(1,0,0),(1,1,0)],[(1.5,.5,0),(1.5,1.5,0)])
# No terrace rails (2026-10-31 roof pass), so no rail openings ('ports').
LAB['interiorCells']=[[1,0,0],[1,1,0]]
LAB['buildableCells']=[[x,0,1] for x in range(3)]
LAB['doorNodes']=[[1,0,0]]
LAB['doorLinks']=[]
LAB['suggestedPathCells']=[n['cell'] for n in LAB['nodes'] if n['cell'] not in LAB['interiorCells']]
LAYOUTS={'MaterialsLaboratory':LAB}

if __name__=='__main__':
    for a,b in LAB['edges']:
        if sum(abs(a[i]-b[i]) for i in range(3))!=1:raise ValueError('Research route must use unit edges')
    path=Path(__file__).resolve().parents[1]/'research-layouts.json'
    path.write_text(json.dumps(LAYOUTS,indent=2)+'\n')
    print(path)
