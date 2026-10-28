"""Explicit exterior roof-bearing panels for closed industrial rooms.

This authors only the missing perimeter between declared wall and roof edges.
It does not fill open work bays, add invisible interior skins, or infer bounds.
"""
from frontier_architecture import facade_panel, PLANK


def lean_roof_curb(g,x0,y0,x1,y1,wall_front,wall_back,roof_y0,roof_y1,roof_z0,roof_z1,thickness):
    if not (x1>x0 and y1>y0 and roof_y1>roof_y0 and thickness>0):
        raise ValueError('Declare positive roof-bearing dimensions')
    def underside(y):
        return roof_z0+(roof_z1-roof_z0)*(y-roof_y0)/(roof_y1-roof_y0)-thickness
    z0,z1=underside(y0),underside(y1)
    if z0<=wall_front or z1<=wall_back:
        raise ValueError('A roof curb requires a genuine positive perimeter gap')
    facade_panel(g,'Y',y0,x0,x1,wall_front,z0,False,PLANK)
    facade_panel(g,'Y',y1,x0,x1,wall_back,z1,True,PLANK)
    for x,positive in ((x0,False),(x1,True)):
        vertices=[(x,y0,wall_front),(x,y1,wall_back),(x,y1,z1),(x,y0,z0)]
        g.add(vertices,[(0,1,2,3) if positive else (3,2,1,0)],PLANK)
