"""Double Lodge rail geometry and original atlas UVs, on authored deck spans."""
import json
from pathlib import Path
from mathutils import Vector
KIT=json.loads(Path(__file__).with_name('housing-railing.json').read_text())
HOUSING_RAIL=31

def post(g,p,z):
    part=KIT['parts']['post']
    # Original post centre and floor; retain the native beveled, irregular top.
    vertices=[(p.x+x-1,p.y+depth-.05,z+height-1) for x,height,depth in part['vertices']]
    g.native_piece(vertices,part['faces'],part['uv'],HOUSING_RAIL)

def panel(g,a,b,z):
    part=KIT['parts']['handrail'];a,b=Vector(a),Vector(b)
    delta=b-a;length=delta.length
    if length<=0:raise ValueError('Housing handrail needs a positive authored span')
    tangent=delta/length;normal=Vector((-tangent.y,tangent.x))
    lo,hi=part['bounds'][0]
    # Only the long axis takes the authored span. Cross-section, height and UVs
    # remain the source rail; cuts at cell boundaries are the exporter's job.
    vertices=[]
    for x,height,depth in part['vertices']:
        p=a+tangent*((x-lo)/(hi-lo)*length)+normal*(depth-.04390627145767212)
        vertices.append((p.x,p.y,z+height-1))
    g.native_piece(vertices,part['faces'],part['uv'],HOUSING_RAIL)
