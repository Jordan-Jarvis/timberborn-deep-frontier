"""Confirm shared-helper extraction did not alter the approved kiln geometry."""
from pathlib import Path
import json
import sys
import bpy
from mathutils import Vector

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from frontier_architecture import Geometry
from kiln_isometric_geometry import kiln

g=Geometry('CementKiln.Architecture');parts=[];rails=kiln(g,parts)
sources=[g]+rails.meshes+[p[0] for p in parts]
scene=bpy.data.collections['CementKiln.ReferenceStudy']
if set(o.name for o in scene.objects)!=set(g.name for g in sources):
    raise ValueError('Approved kiln node set changed during helper extraction')
worst=0
for geo in sources:
    mesh=scene.objects[geo.name].data
    if len(mesh.vertices)!=len(geo.vertices) or len(mesh.polygons)!=len(geo.faces):
        raise ValueError('Approved kiln topology changed: '+geo.name)
    for vertex,expected in zip(mesh.vertices,geo.vertices):
        worst=max(worst,(vertex.co-Vector(expected)).length)
    for polygon,face,material in zip(mesh.polygons,geo.faces,geo.materials):
        if tuple(polygon.vertices)!=tuple(face) or polygon.material_index!=material:
            raise ValueError('Approved kiln face/material changed: '+geo.name)
if worst>1e-6:raise ValueError('Approved kiln vertex positions changed')
report={'result':'passed','nodes':len(sources),'maximumVertexDifference':worst,
        'scope':'Regenerated authoring geometry versus approved saved Blender scene; no game claims'}
(root/'outputs/kiln-shared-joinery-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
