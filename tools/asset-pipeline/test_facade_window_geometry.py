"""Keep the selected District Center window geometry and UVs intact."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from frontier_architecture import Geometry
from architectural_windows import window,KIT,MOUNT_DEPTH
materials=[bpy.data.materials.new(str(i)) for i in range(32)]
collection=bpy.context.scene.collection
for style,count in {'grand':46,'lancet':40,'diamond':26,'factory':16}.items():
    parts=[KIT['parts'][name] for name in KIT['windowAssemblies'][style]['parts']]
    assert sum(len(p['faces']) for p in parts)==count
    for face in ('front','back','left','right'):
        g=Geometry(style+' window '+face);window(g,0,0,0,1.25,face,style)
        assert len(g.faces)>count,'Window needs its physical mounting reveal'
        source_uvs=[[[p['uv'][i] for i in f] for f in p['faces']] for p in parts]
        assert g.face_uvs[:count]==[face_uv for group in source_uvs for face_uv in group]
        assert all(uv is None for uv in g.face_uvs[count:]),'Reveal must use its own timber UV mapping'
        assert g.window_mounts[0]['mountDepth']==MOUNT_DEPTH
        axis=1 if face in ('front','back') else 0
        assert all(abs(point[axis])<1e-8 for edge in g.window_mounts[0]['rearEdges'] for point in edge),'Reveal must reach the declared wall plane'
        if style=='factory':
            # Geometry stores Blender coordinates with game X/Y negated.
            outward=Vector({'front':(0,1,0),'back':(0,-1,0),'left':(1,0,0),'right':(-1,0,0)}[face])
            for tri in g.faces[:count]:
                a,b,c=(Vector(g.vertices[i]) for i in tri)
                assert (b-a).cross(c-a).dot(outward)>0,'Factory pane faces into the wall'
        obj=g.build(collection,materials,.012,'civic-native')
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
        assert len(evaluated.polygons)==len(g.faces),'Native frame or hard reveal was bevelled again'
        obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
print('PASS: four window styles in four orientations retain exact source triangles and UVs; physical40mm reveal reaches the declared wall plane')
