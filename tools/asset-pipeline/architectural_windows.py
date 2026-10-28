"""Large District Center windows from required New Styles, original atlas UVs."""
import json
from pathlib import Path
from frontier_architecture import WOOD
KIT=json.loads(Path(__file__).with_name('housing-facade.json').read_text())
WINDOW=30
MOUNT_DEPTH=.04
PANES={'grand':'grandWindowPanes','lancet':'lancetPanes','diamond':'diamondPanes','factory':'factoryGrid'}

def window(g,x,y,z,scale=1,face='front',style='grand'):
    """Seat an original assembly on a real 40 mm timber reveal.

    The x/y anchor is the explicitly authored opaque wall skin, not an
    arbitrary decorative offset. Native mesh proportions and UVs are retained.
    The physical reveal clears projecting timber posts and joins the pane
    boundary back to that exact wall plane.
    """
    if scale<=0:raise ValueError('Native window scale must be positive')
    nx,ny={'front':(0,-1),'back':(0,1),'left':(-1,0),'right':(1,0)}[face]
    tx,ty=-ny,nx
    assembly=KIT['windowAssemblies'][style]
    origin=assembly['origin'];tangent=assembly['tangent'];outward=assembly['outward']
    first_face=len(g.faces)
    def placed(p,back=False):
        delta=tuple(p[i]-origin[i] for i in range(3))
        u=sum(a*b for a,b in zip(delta,tangent))*scale
        depth=0 if back else MOUNT_DEPTH+sum(a*b for a,b in zip(delta,outward))*scale
        return (x+u*tx+depth*nx,y+u*ty+depth*ny,z+delta[1]*scale)
    for name in assembly['parts']:
        part=KIT['parts'][name];vertices=[]
        material={'BaseWood_DarkBrown.IronTeeth':WOOD,'WindowsAtlas.IronTeeth':WINDOW}[part['material']]
        for point in part['vertices']:vertices.append(placed(point))
        g.native_piece(vertices,part['faces'],part['uv'],material)
    # Extrude the exact native pane perimeter. Coincident source edge keys
    # identify internal triangle edges; no vertex is rounded or moved.
    pane=KIT['parts'][PANES[style]];edges={}
    for face_indices in pane['faces']:
        for ia,ib in zip(face_indices,face_indices[1:]+face_indices[:1]):
            a=tuple(pane['vertices'][ia]);b=tuple(pane['vertices'][ib]);key=tuple(sorted((a,b)))
            edges.setdefault(key,[]).append((a,b))
    boundary=[]
    for key,uses in edges.items():
        if len(uses)==2:continue
        if len(uses)!=1:raise ValueError('Native pane has a nonmanifold edge: '+PANES[style])
        a,b=uses[0]
        rear_a,rear_b=placed(a,True),placed(b,True)
        front_a,front_b=placed(a),placed(b)
        g.add([rear_a,rear_b,front_b,front_a],[(0,1,2,3)],WOOD)
        boundary.append([rear_a,rear_b])
    if not boundary:raise ValueError('Native pane has no mounting perimeter: '+PANES[style])
    g.window_mounts.append({'style':style,'face':face,'anchor':[x,y,z],'scale':scale,
        'outward':[nx,ny,0],'mountDepth':MOUNT_DEPTH,'faceRange':[first_face,len(g.faces)],
        'rearEdges':boundary})
