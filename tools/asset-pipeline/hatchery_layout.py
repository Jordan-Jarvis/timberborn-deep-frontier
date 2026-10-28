"""Bank-height nursery, native player paths and one enclosed workshop door."""
from industrial_layouts import layout,node,edge
from hatchery_structure import ORIGIN,BASE_Z,SIZE,ROOMS,PLATFORMS,SUPPORTS,DOORS,RESERVATIONS,DOOR_LINKS,SHAFT_PORTS,source,deck_cells

H=layout(ORIGIN,SIZE,[1,0,1],[list(source((1.35,1,1))),list(source((1.65,1,1)))],deck_mode='PlayerPlacedPaths')
H['baseZ']=BASE_Z
H['idleFacing']=[[0,-1],[0,-1]]
H['structure']={'platforms':PLATFORMS,'supports':SUPPORTS,'rooms':ROOMS,'reservations':RESERVATIONS,'doors':DOORS}
H['interiorCells']=[[1,1,1]]
H['doorLinks']=DOOR_LINKS
H['doorNodes']=[[1,1,1]]
H['localAccess']=[1.5,1,1]
H['shaftPorts']=SHAFT_PORTS
H['waterCell']=[1,5,0]
H['staffSlots']=[]
H['suggestedPathCells']=[list(c) for c in deck_cells()]
H['buildableCells']=[list(c) for c in deck_cells() if c[1]!=0]
for cell in [*deck_cells(),(1,1,1)]:node(H,cell,source((cell[0]+.5,cell[1]+.5,cell[2])))
cells={tuple(n['cell']) for n in H['nodes']}
for x,y,z in sorted(cells):
    for b in ((x+1,y,z),(x,y+1,z)):
        if b in cells:edge(H,(x,y,z),b)
# One railing opening per remaining rail cell (hatchery_structure.RAIL_RUNS).
for name,inside,outside,run in [
    ('NurseryLeft3',(0,3,1),(-1,3,1),'NurseryLeft'),
    ('NurseryBack2',(2,6,1),(2,7,1),'NurseryBack'),
    ('NurseryRight5',(5,3,1),(5,4,1),'NurseryRight')]:
    H['ports'].append({'id':name,'inside':list(inside),'outside':list(outside),'run':run,
                       'approach':list(source((inside[0]+.5,inside[1]+.5,inside[2])))})
