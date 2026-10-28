"""Registration follows the existing isometric turbine; artwork is not scaled."""
import json
from pathlib import Path
from industrial_layouts import layout,grid_lane,lane,port

TURBINE=layout([0,0,0],[8,10,7],[6,5,2],[],deck_mode='BuiltInWalkways')
grid_lane(TURBINE,[(x,4,2) for x in range(4,8)])
grid_lane(TURBINE,[(7,y,2) for y in range(4,10)])
grid_lane(TURBINE,[(x,9,2) for x in range(4,8)])
lane(TURBINE,[(6,4,2),(6,5,2)],[(6.5,4.5,2),(6.5,5.5,2)])
for x in range(4,8):
    port(TURBINE,f'Front{x}',(x,4,2),(x,3,2),f'Front{x-1}')
    port(TURBINE,f'Rear{x}',(x,9,2),(x,10,2),f'Rear{x-1}')
for y in range(4,10):
    port(TURBINE,f'Right{y}',(7,y,2),(8,y,2),f'Right{y-4}')
LAYOUTS={'ReinforcedHydroTurbine':TURBINE}

if __name__=='__main__':
    target=Path(__file__).resolve().parents[1]/'hydro-layouts.json'
    target.write_text(json.dumps(LAYOUTS,indent=2)+'\n')
    print(target)
