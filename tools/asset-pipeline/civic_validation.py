"""Check authored civic galleries before binding their native grid routes."""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from civic_isometric_geometry import CIVIC_ACCESS,CIVIC_TERRACES
from native_uv_contract import SOURCE_UV


# Deck boards stand 10 mm proud of their structural layer (grid_structure
# board_relief); 4 mm sat on the strict overlap tolerance. Walking floors are
# accepted within that authored relief.
FLOOR_TOLERANCE=.012


def validate_civic_walks(ident,model,scene):
    scene.frame_set(1);scene.view_layers[0].update()
    vertices=[];faces=[];owners=[]
    for obj in model.objects:
        if obj.type=='EMPTY':continue
        start=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(start+i for i in p.vertices) for p in obj.data.polygons)
        owners.extend([obj.name]*len(obj.data.polygons))
    tree=BVHTree.FromPolygons(vertices,faces)
    definition=CIVIC_ACCESS[ident];samples=[];failures=[]
    for z,route in ((z,r) for z in definition['balconyLayers'] for r in definition['routes']):
        for a,b in zip(route,route[1:]):
            a,b=Vector(a),Vector(b);count=math.ceil((b-a).length/.12)
            for i in range(count+1):
                x,y=a+(b-a)*(i/count);contacts=0
                for dx in (-.035,0,.035):
                    hit=tree.ray_cast(Vector((-x-dx,-y,z+.08)),Vector((0,0,-1)),.12)
                    # A probe may fall into a 6 mm board joint and meet the
                    # structural layer under the 10 mm board relief.
                    if hit[0] is not None and abs(hit[0].z-z)<FLOOR_TOLERANCE:contacts+=1
                if contacts<2:failures.append(f'missing floor at {x:.3f},{y:.3f},{z}')
                for dx,dy in ((0,0),(.20,0),(-.20,0),(0,.20),(0,-.20)):
                    hit=tree.ray_cast(Vector((-x-dx,-y-dy,z+.01)),Vector((0,0,1)),1.09)
                    if hit[0] is not None:
                        failures.append(f'obstruction at {-hit[0].x:.3f},{-hit[0].y:.3f},{hit[0].z:.3f} in {owners[hit[2]]}')
                samples.append([x,y,z])
    terrace=CIVIC_TERRACES[ident];x0,y0,x1,y1=terrace['clearArea'];z=terrace['layer']
    terrace_samples=[]
    for i in range(9):
        for j in range(9):
            x=x0+(x1-x0)*i/8;y=y0+(y1-y0)*j/8
            hit=tree.ray_cast(Vector((-x,-y,z+.06)),Vector((0,0,-1)),.10)
            if hit[0] is None or abs(hit[0].z-z)>FLOOR_TOLERANCE:failures.append(f'roof terrace floor at {x},{y},{z}')
            hit=tree.ray_cast(Vector((-x,-y,z+.015)),Vector((0,0,1)),2.0)
            if hit[0] is not None:failures.append(f'roof terrace obstruction at {x},{y},{z}, height {hit[0].z:.3f} in {owners[hit[2]]}')
            terrace_samples.append([x,y,z])
    if failures:raise ValueError(ident+' gallery check: '+str(len(failures))+' failures; '+'; '.join(failures[:18]))
    checked=0
    for obj in model.objects:
        if obj.type=='EMPTY':continue
        if 'native_resource' in obj or 'liquid_surface' in obj:
            if not obj.data.uv_layers:raise ValueError('Native prop is missing original UVs: '+obj.name)
            continue
        if len(obj.material_slots)!=32:raise ValueError('Civic material palette changed: '+obj.name)
        uv=obj.data.uv_layers.active.data
        for polygon in obj.data.polygons:
            if polygon.material_index in (0,1,2,3,7,27,28,29,30):
                for loop in polygon.loop_indices:
                    # Imported native UVs include exact authored coordinates
                    # outside [0,1] (Barrack jamb: -0.000079099). Only generated
                    # atlas islands use our inset boundary contract.
                    source_uv=obj.data.attributes['df_source_uv'].data[polygon.index].value
                    material=obj.material_slots[polygon.material_index].material.name
                    valid=(material in SOURCE_UV and tuple(uv[loop].uv) in SOURCE_UV[material]) if source_uv else all(.001<=v<=.999 for v in uv[loop].uv)
                    if not valid:
                        raise ValueError('Native atlas island is out of bounds: '+obj.name)
                    checked+=1
    sign_clearance=None
    if ident=='Restaurant':
        # The carved sign hangs from the front gable (2026-10-21). Its whole
        # swing must stay inside the reserved roof cells (native y >= 2,
        # 6 <= z <= 7; source y = native y - .15) and keep the upper gallery's
        # walking headroom (deck 4 + 1.10) clear by at least .15.
        sign=next(o for o in model.objects if o.name=='Restaurant.CarvedSign')
        low=float('inf');high=float('-inf');nearest_y=float('inf')
        for frame in range(1,scene.frame_end+1):
            scene.frame_set(frame);scene.view_layers[0].update()
            points=[sign.matrix_world@v.co for v in sign.data.vertices]
            low=min(low,min(p.z for p in points));high=max(high,max(p.z for p in points))
            nearest_y=min(nearest_y,min(-p.y for p in points))
        sign_clearance=low-(4+1.10)
        if sign_clearance<.15:raise ValueError('Restaurant sign swing enters the upper gallery headroom')
        if low<6-.001 or high>7+.001 or nearest_y<1.85-.001:
            raise ValueError(f'Restaurant sign swing leaves its reserved gable cells: z {low:.3f}..{high:.3f}, source y >= {nearest_y:.3f}')
        scene.frame_set(1);scene.view_layers[0].update()
    return {'scope':'Authored mesh only; native grid paths, stair and platform placement are not verified',
            'animatedSignDeckClearance':sign_clearance,
            'sourceUnitHeadroom':1.10,'sourceUnitBodyRadius':.20,
            'floorAndClearanceSamples':samples,'terraceClearAreaSamples':terrace_samples,'nativeAtlasUvCornersChecked':checked}
