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
        'origin':[.57,0,0],'size':[5,4,4],'baseZ':0,
        'entrance':[1,-1,0],'idle':[[.93,.98,0]],
        # Native path cell between the entrance and the door, under the
        # yard floor (Floor occupation).
        'approachFloor':[1,0,0],
        'nodes':[],'edges':[],'ports':[],'deckMode':'None',
        # Occupied height per column, Y rows from the front. The front doorway
        # remains clear; only the hoist needs the fourth layer.
        'columnHeights':[
            [2,2,2,2,4],
            [3,3,3,3,4],
            [3,3,3,3,4],
            [3,3,3,3,4],
        ],
    },
    'LimestonePit':{
        'origin':[.57,-1,0],'size':[5,3,4],'baseZ':0,
        'entrance':[1,-1,0],'idle':[[.93,.98,0]],
        'approachFloor':None,
        'nodes':[],'edges':[],'ports':[],'deckMode':'None',
        # Column (4,0) holds nothing: a free cell for the player's own path
        # or decoration (no occupation, no matter rule, no collider).
        'columnHeights':[
            [3,3,3,3,0],
            [3,3,3,3,4],
            [3,3,3,3,4],
        ],
    },
}

if __name__=='__main__':
    target=Path(__file__).resolve().parents[1]/'pit-layouts.json'
    target.write_text(json.dumps(LAYOUTS,indent=2)+'\n')
    print(target)
