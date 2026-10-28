"""Adaptive waterside pile templates: one plain segment and one foot per model.

Runtime contract (src/DeepFrontier/Scripts/Waterside/AdaptiveSupports.cs): the
finished model holds exactly one `#SupportSegment` and one `#SupportFoot`
node. Each is one cell tall with its origin at the bottom centre of a cell;
clones are positioned at GridToWorldCentered(cell) and stacked from each
authored column top down to the bed, the foot lowest. Segments therefore abut
exactly at whole-cell boundaries and never overlap one another.

`shift` lowers the whole post inside its cell. The Hatchery's columns start
in the layer directly below its bank-height deck: a -0.10 shift ends the top
segment 10 mm inside the 110 mm deck slab instead of poking through the
boards. The Fishery's columns start below its z=0 basin floors, so its posts
end flush against the basin bottoms (opposite-facing contact, no overlap).

Templates are emitted by export_industrial_models.py, placed at a buried
anchor below a land cell. AdaptiveSupports deactivates them in the finished
model; in the copied construction-stage model they stay underground.
"""
import json
from pathlib import Path
from frontier_architecture import Geometry,WOOD,IRON
from reference_materials import CIVIC_CONCRETE
from industrial_geometry import bracket

ROOT=Path(__file__).resolve().parents[2]
SEGMENT_NODE='#SupportSegment'
FOOT_NODE='#SupportFoot'
# Width matches each building's own timber columns; shift is explained above.
STYLES={
    'hatchery':{'width':.16,'shift':-.10,'pier':.30,'pierTop':.16},
    'fishery':{'width':.17,'shift':0.,'pier':.32,'pierTop':.18},
}
FOOT_EMBED=.22   # The foot runs this far below the bed top, into the ground.


def sites():
    return json.loads((ROOT/'tools/waterside_sites.json').read_text(encoding='utf-8'))


def _channels(g,w,bottom,top):
    # Steel channels on two faces, as civic timber_column; 20 mm short of each
    # end so stacked segments read as separate one-layer pile sections. Their
    # width keeps every face >= 10 mm from the collar plates (strict audit).
    for side in (-1,1):
        g.box((side*w*.44,0,(bottom+top)/2),(.035,w+.02,top-bottom-.04),IRON)


def segment(style):
    s=STYLES[style];w=s['width'];bottom=s['shift'];top=1+s['shift']
    g=Geometry(SEGMENT_NODE)
    g.box((0,0,(bottom+top)/2),(w,w,top-bottom),WOOD)
    _channels(g,w,bottom,top)
    bracket(g,0,0,bottom+.5,w)
    return g


def foot(style):
    s=STYLES[style];w=s['width'];top=1+s['shift'];low=-FOOT_EMBED
    g=Geometry(FOOT_NODE)
    # Core bottom stays 20 mm inside the pier so their bottom faces never coincide.
    g.box((0,0,(low+.02+top)/2),(w,w,top-low-.02),WOOD)
    g.box((0,0,(low+s['pierTop'])/2),(s['pier'],s['pier'],s['pierTop']-low),CIVIC_CONCRETE)
    # Bearing plate straddles the pier top: no coincident pier/plate faces.
    g.box((0,0,s['pierTop']+.02),(s['pier']+.02,s['pier']+.02,.06),IRON)
    _channels(g,w,s['pierTop']+.06,top)
    bracket(g,0,0,(s['pierTop']+.06+top)/2,w)
    return g


def templates(model):
    """(node name, Geometry, anchor cell) for one model; unknown models fail."""
    site=sites()[model]
    style=site['templates']['style']
    return [(SEGMENT_NODE,segment(style),site['templates']['anchor']),
            (FOOT_NODE,foot(style),site['templates']['anchor'])]


def models():
    return [k for k,v in sites().items() if isinstance(v,dict) and 'supports' in v]
