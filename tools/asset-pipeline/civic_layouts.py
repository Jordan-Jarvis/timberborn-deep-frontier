"""Explicit registration of accepted civic artwork; no automatic fitting."""
import json
from pathlib import Path
from industrial_layouts import layout, node, edge, lane, grid_lane, port
from restaurant_layout import R

ROOT = Path(__file__).resolve().parents[2]
# The waterfront model has its own authored floors and envelope.
from fishery_layout import F
from hatchery_layout import H
from hospital_layout import HOSPITAL
from grocery_layout import GROCERY
LAYOUTS = {'Restaurant': R, 'FisheryWorks': F, 'FishHatchery': H, 'Hospital': HOSPITAL, 'GroceryStore': GROCERY}

if __name__ == '__main__':
    for ident, d in LAYOUTS.items():
        cells = [n['cell'] for n in d['nodes']]
        for a,b in d['edges']:
            if a not in cells or b not in cells:raise ValueError((ident,a,b))
            if sum(abs(a[i]-b[i]) for i in range(3)) != 1:raise ValueError('Non-unit civic edge')
    (ROOT/'tools/civic-layouts.json').write_text(json.dumps(LAYOUTS,indent=2)+'\n')
    for ident,d in LAYOUTS.items():print('Authored',ident,'registration:',d['size'],'door levels:', sorted({c[2] for c in d['doorNodes']} ))
