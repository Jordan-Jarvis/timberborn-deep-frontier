"""Physical checks against the actual saved quarry scene, not native gameplay.

Check all source animation frames for cable/bucket attachment. Ray tests inspect
authored mesh clearance at the ladder hatch of the maintenance ladder mast (the quarry has no walkable galleries).
They do not substitute for occupancy, navmesh, placement or beaver tests in game.
"""
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from quarry_isometric_geometry import ACCESS,BUCKET_TOP,BUCKET_BASE,ROPE_TOP,HOIST_TRAVEL


def validate_quarry(model,scene):
    if scene.frame_end!=481:raise ValueError('Quarry timeline must be 481 frames')
    bucket=model.objects['Quarry.LiftCarriage'];rope=model.objects['Quarry.LiftCable']
    local_bottom=Vector((0,0,BUCKET_TOP-ROPE_TOP));local_top=Vector((0,0,0))
    errors=[];lifts=[];rope_lengths=[]
    for frame in range(1,482):
        scene.frame_set(frame)
        # Blender evaluates frame changes before object matrices are read.
        import bpy
        bpy.context.view_layer.update()
        attachment=bucket.matrix_world@Vector((0,0,BUCKET_TOP-BUCKET_BASE))
        cable_bottom=rope.matrix_world@local_bottom;cable_top=rope.matrix_world@local_top
        errors.append((attachment-cable_bottom).length)
        lifts.append(bucket.location.z-BUCKET_BASE);rope_lengths.append((cable_top-cable_bottom).length)
        if abs(cable_top.z-ROPE_TOP)>1e-5:raise ValueError('Cable top moves away from sheave')
        if max(errors)>1e-5:raise ValueError('Cable detaches from moving bucket')
    if abs(max(lifts)-HOIST_TRAVEL)>1e-5 or min(rope_lengths)<1.5:
        raise ValueError('Bucket travel or hoist head clearance is wrong')
    scene.frame_set(1)
    # Combine authored static meshes, including rails and ladders. No camera,
    # studio floor, animated parts or bounding-box substitutes enter this test.
    vertices=[];faces=[]
    for obj in model.objects:
        if obj.animation_data and obj.animation_data.action:continue
        # The native water barrel's root is an empty (no mesh of its own).
        if obj.type!='MESH':continue
        start=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(start+i for i in p.vertices) for p in obj.data.polygons)
    tree=BVHTree.FromPolygons(vertices,faces)
    def ray(x,y,z,direction,length):
        return tree.ray_cast(Vector((-x,-y,z)),Vector(direction),length)
    # A body-width cylinder in front of the rungs must pass up the mast to
    # the open hatch of the top service landing. There are no galleries.
    for dx,dy in ((0,0),(.18,0),(-.18,0),(0,.18),(0,-.18)):
        hit=ray(2.5+dx,7.35+dy,1.02,(0,0,1),6.18)
        if hit[0] is not None:raise ValueError('Ladder bay is obstructed at '+str(tuple(hit[0])))
    for name in ACCESS['ladderNodes']:
        if name not in model.objects:raise ValueError('Missing ladder mesh: '+name)
    return {'scope':'Authored mesh/animation only; native route verification pending',
            'framesChecked':481,'maximumCableAttachmentError':max(errors),
            'bucketTravel':max(lifts)-min(lifts),'minimumCableLength':min(rope_lengths),
            'ladderHatchClearanceRays':5,'walkableDecks':ACCESS['walkableDecks'],
            'ladderNodes':ACCESS['ladderNodes']}
