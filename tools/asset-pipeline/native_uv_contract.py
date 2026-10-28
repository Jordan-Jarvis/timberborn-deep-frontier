"""Validate authored inset islands and exact reused native UV pairs."""
import json,math
from pathlib import Path

HERE=Path(__file__).parent
facades=json.loads((HERE/'housing-facade.json').read_text(encoding='utf-8'))['parts']
rails=json.loads((HERE/'housing-railing.json').read_text(encoding='utf-8'))
SOURCE_UV={'BaseWood_DarkBrown.IronTeeth':set(),'WindowsAtlas.IronTeeth':set(),rails['material']:set()}
for part in facades.values():
    SOURCE_UV[part['material']].update(tuple(uv) for uv in part['uv'])
for part in rails['parts'].values():SOURCE_UV[rails['material']].update(tuple(uv) for uv in part['uv'])

def valid_native_uv(material,uv):
    if len(uv)!=2 or not all(math.isfinite(v) for v in uv):return False
    if all(.001<=v<=.999 for v in uv):return True
    return material in SOURCE_UV and tuple(uv) in SOURCE_UV[material]

# Whole shipped WindowsAtlas.IronTeeth cells placed by native_window_atlas.py
# (exact inset cell corners, float32-rounded).
from native_window_atlas import cell_uvs as _atlas_cell_uvs
SOURCE_UV['WindowsAtlas.IronTeeth'].update(_atlas_cell_uvs())
