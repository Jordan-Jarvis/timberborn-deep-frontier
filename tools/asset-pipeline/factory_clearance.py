"""Inspect the saved factory meshes along their intended service circuits.

Source-unit mesh clearance only. Native grid navigation still needs integration
and actual beaver movement tests. A clear rendered deck is not a path graph.
"""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from industrial_levels import CRUSHER_DECK,KILN_DECK

ROUTES={
    # Crusher points are native grid XY (origin 0): lane centres.
    'StoneCrusher':{'height':CRUSHER_DECK,'points':[(5.50,2.50),(5.50,6.50),(.50,6.50),(.50,3.50)]},
    'CementKiln':{'height':KILN_DECK,'points':[(-.45,.80),(5.20,.80)],
                 'otherRoutes':[[(-.45,.80),(-.45,3.80),(7.40,3.80),(7.40,1.10)]]},
}


def validate_factory_walks(ident,model,scene):
    scene.frame_set(1)
    vertices=[];faces=[]
    for obj in model.objects:
        if obj.animation_data and obj.animation_data.action:continue
        start=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(start+i for i in p.vertices) for p in obj.data.polygons)
    tree=BVHTree.FromPolygons(vertices,faces)
    definition=ROUTES[ident];z=definition['height']
    routes=[definition['points']]
    if ident=='CementKiln':routes.extend(definition['otherRoutes'])
    samples=[]
    for route in routes:
        for a,b in zip(route,route[1:]):
            a,b=Vector(a),Vector(b)
            count=math.ceil((b-a).length/.15)
            for i in range(count+1):
                x,y=a+(b-a)*(i/count)
                contacts=0
                for dx in (-.035,0,.035):
                    hit=tree.ray_cast(Vector((-x-dx,-y,z+.08)),Vector((0,0,-1)),.12)
                    if hit[0] is not None and abs(hit[0].z-z)<.005:contacts+=1
                if contacts<2:raise ValueError(f'{ident}: missing walkway floor at {x},{y},{z}')
                for dx,dy in ((0,0),(.20,0),(-.20,0),(0,.20),(0,-.20)):
                    hit=tree.ray_cast(Vector((-x-dx,-y-dy,z+.01)),Vector((0,0,1)),1.09)
                    if hit[0] is not None:raise ValueError(f'{ident}: walkway obstruction at {tuple(hit[0])}')
                samples.append([x,y,z])
    return {'scope':'Saved mesh check; no native navigation or stair traversal verification',
            'sourceUnitHeadroom':1.10,'sourceUnitBodyRadius':.20,'floorAndClearanceSamples':samples}
