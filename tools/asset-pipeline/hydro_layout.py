"""Registration follows the existing isometric turbine; artwork is not scaled."""
import json
from pathlib import Path
from industrial_layouts import layout,grid_lane,lane,port

# 2026-10-30 (user: every flat roof tile placeable like a platform): the
# U-shaped terrace lane on the workshop foundation is a player-placed-path
# deck (PlatformDeckSpec), no longer a built-in walkway. The turbine has no
# workers and no enclosed door, so the deck has no door links; players lay
# ordinary paths across it (and onto neighbouring turbines) as on any roof.
TURBINE=layout([0,0,0],[8,10,6],[6,5,2],[],deck_mode='PlayerPlacedPaths')
grid_lane(TURBINE,[(x,4,2) for x in range(4,8)])
grid_lane(TURBINE,[(7,y,2) for y in range(4,10)])
grid_lane(TURBINE,[(x,9,2) for x in range(4,8)])
lane(TURBINE,[(6,4,2),(6,5,2)],[(6.5,4.5,2),(6.5,5.5,2)])
for x in range(4,8):
    port(TURBINE,f'Front{x}',(x,4,2),(x,3,2),f'Front{x-1}')
    port(TURBINE,f'Rear{x}',(x,9,2),(x,10,2),f'Rear{x-1}')
for y in range(4,10):
    port(TURBINE,f'Right{y}',(7,y,2),(8,y,2),f'Right{y-4}')
TURBINE['interiorCells']=[]
TURBINE['doorLinks']=[]
TURBINE['suggestedPathCells']=[n['cell'] for n in TURBINE['nodes']]
LAYOUTS={'ReinforcedHydroTurbine':TURBINE}

if __name__=='__main__':
    target=Path(__file__).resolve().parents[1]/'hydro-layouts.json'
    target.write_text(json.dumps(LAYOUTS,indent=2)+'\n')
    print(target)
