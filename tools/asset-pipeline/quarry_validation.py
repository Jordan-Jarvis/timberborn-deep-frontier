"""Physical checks against the actual saved quarry scene, not native gameplay.

Check all source animation frames for cable/bucket attachment and that the
bucket stays under the sheave. The compact quarry (2026-10-30) has no ladder
mast or walkable galleries. These checks do not substitute for occupancy,
navmesh, placement or beaver tests in game.
"""
from mathutils import Vector
from quarry_isometric_geometry import ACCESS,BUCKET_TOP,BUCKET_BASE,ROPE_TOP,SHEAVE_R
from quarry_process_details import HOIST_TRAVEL

MIN_ROPE=.80


def validate_quarry(model,scene):
    if scene.frame_end!=481:raise ValueError('Quarry timeline must be 481 frames')
    bucket=model.objects['Quarry.LiftCarriage'];rope=model.objects['Quarry.LiftCable']
    local_bottom=Vector((0,0,BUCKET_TOP-ROPE_TOP));local_top=Vector((0,0,0))
    errors=[];lifts=[];rope_lengths=[]
    import bpy
    for frame in range(1,482):
        scene.frame_set(frame)
        # Blender evaluates frame changes before object matrices are read.
        bpy.context.view_layer.update()
        attachment=bucket.matrix_world@Vector((0,0,BUCKET_TOP-BUCKET_BASE))
        cable_bottom=rope.matrix_world@local_bottom;cable_top=rope.matrix_world@local_top
        errors.append((attachment-cable_bottom).length)
        lifts.append(bucket.location.z-BUCKET_BASE);rope_lengths.append((cable_top-cable_bottom).length)
        if abs(cable_top.z-ROPE_TOP)>1e-5:raise ValueError('Cable top moves away from sheave')
        if max(errors)>1e-5:raise ValueError('Cable detaches from moving bucket')
    if abs(max(lifts)-HOIST_TRAVEL)>1e-5 or min(rope_lengths)<MIN_ROPE:
        raise ValueError('Bucket travel or hoist head clearance is wrong')
    if BUCKET_TOP+HOIST_TRAVEL>=ROPE_TOP-SHEAVE_R:
        raise ValueError('Raised yoke reaches the head sheave')
    scene.frame_set(1)
    return {'scope':'Authored mesh/animation only; native route verification pending',
            'framesChecked':481,'maximumCableAttachmentError':max(errors),
            'bucketTravel':max(lifts)-min(lifts),'minimumCableLength':min(rope_lengths),
            'walkableDecks':ACCESS['walkableDecks']}
