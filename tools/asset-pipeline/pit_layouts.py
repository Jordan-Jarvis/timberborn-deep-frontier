"""Explicit registration after the isometric pit art review; no mesh scaling."""
import json
from pathlib import Path

LAYOUTS={
    # 2026-10-22: footprints end at the walls. The sandstone pit keeps its
    # front row for the working hoist and the sorting grate (process yard);
    # its back row (yard floor only) is gone. The limestone pit loses the
    # front yard, the side shelter column and the back row: its door's
    # entrance is the open cell in front of the footprint edge.
    'SandstonePit':{
        # One storey since the 2026-10-30 compaction: 5x4x3 (was 5x4x4).
        'origin':[.57,0,0],'size':[5,4,3],'baseZ':0,
        'entrance':[1,-1,0],'idle':[[.93,.98,0]],
        # Native path cell between the entrance and the door, under the
        # yard floor (Floor occupation).
        'approachFloor':[1,0,0],
        'nodes':[],'edges':[],'ports':[],'deckMode':'None',
        # Occupied height per column, Y rows from the front: the flat roof
        # below layer 2, the hoist jib in layer 2.
        'columnHeights':[
            [2,2,2,2,3],
            [2,2,2,2,3],
            [2,2,2,2,3],
            [2,2,2,2,3],
        ],
    },
    'LimestonePit':{
        # One storey since the 2026-10-30 compaction: 5x3x3 (was 5x3x4).
        'origin':[.57,-1,0],'size':[5,3,3],'baseZ':0,
        'entrance':[1,-1,0],'idle':[[.93,.98,0]],
        'approachFloor':None,
        'nodes':[],'edges':[],'ports':[],'deckMode':'None',
        # Column (4,0) holds nothing: a free cell for the player's own path
        # or decoration (no occupation, no matter rule, no collider).
        'columnHeights':[
            [2,2,2,2,0],
            [2,2,2,2,3],
            [2,2,2,2,3],
        ],
    },
}

if __name__=='__main__':
    target=Path(__file__).resolve().parents[1]/'pit-layouts.json'
    target.write_text(json.dumps(LAYOUTS,indent=2)+'\n')
    print(target)
