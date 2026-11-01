"""Registration follows the existing isometric turbine; artwork is not scaled."""
import json
from pathlib import Path
from industrial_layouts import layout,grid_lane,lane

# 2026-10-30 (user: every flat roof tile placeable like a platform): the
# U-shaped terrace lane on the workshop foundation is a player-placed-path
# deck (PlatformDeckSpec), no longer a built-in walkway. The turbine has no
# workers and no enclosed door, so the deck has no door links; players lay
# ordinary paths across it (and onto neighbouring turbines) as on any roof.
# 2026-11-01 second shrink (8x10x6 -> 4x6x6): the foundation terrace beside the
# conduit is gone; the deck is the powerhouse's flat roof over the downstream
# conduit (tiles 0..4 x 4..6, top layer 5), beside the layer-6 dam cap.
TURBINE=layout([0,0,0],[4,6,6],[0,4,5],[],deck_mode='PlayerPlacedPaths')
grid_lane(TURBINE,[(x,4,5) for x in range(4)])
grid_lane(TURBINE,[(x,5,5) for x in range(4)])
grid_lane(TURBINE,[(0,4,5),(0,5,5)])
grid_lane(TURBINE,[(3,4,5),(3,5,5)])
# 2026-10-31 roof pass: the terrace has no rails, so no rail openings ('ports').
TURBINE['interiorCells']=[]
TURBINE['doorLinks']=[]
TURBINE['suggestedPathCells']=[n['cell'] for n in TURBINE['nodes']]
LAYOUTS={'ReinforcedHydroTurbine':TURBINE}

if __name__=='__main__':
    target=Path(__file__).resolve().parents[1]/'hydro-layouts.json'
    target.write_text(json.dumps(LAYOUTS,indent=2)+'\n')
    print(target)
