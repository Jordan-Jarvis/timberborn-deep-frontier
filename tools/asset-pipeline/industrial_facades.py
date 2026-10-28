"""Reusable closed Timberborn-style facades: arched portals, no interiors."""
import math
from frontier_architecture import Geometry,WOOD,PLANK,IRON,BRASS
from reference_materials import KILN_SOOT,GLASS
from industrial_geometry import steel_bolt

# Exterior entrances have a one-tile outer envelope, including the arch and
# infill above it. The narrower clear opening leaves room for structural wood.
DOOR_OUTER_WIDTH=1.0
DOOR_OUTER_HEIGHT=1.0
DOOR_OPENING_WIDTH=.79
DOOR_ARCH_HEIGHT=.88


def building_portal(g,x,y,bottom,*,threshold=False,facade='recessed',panel_depth=None):
    """A complete one-tile wall insert around the actual native Barrack door."""
    from architectural_windows import KIT,WINDOW
    from frontier_architecture import facade_panel
    from reference_materials import CIVIC_ORANGE_PANEL
    if facade not in ('recessed','grid','framed'):
        raise ValueError('Unknown doorway facade contract: '+facade)
    if facade=='framed':
        if panel_depth is None or not -.2<panel_depth<.2:
            raise ValueError('Framed doorway requires its explicit authored wall depth')
    else:
        if panel_depth is not None:raise ValueError('Only framed facades accept an authored wall depth')
        panel_depth=.04 if facade=='grid' else .12
    native_bottom=-.000023614316887687892
    for name,material in (('doorJamb',WOOD),('doorLintel',WOOD),('doorRecess',WINDOW)):
        part=KIT['parts'][name]
        vertices=[(x+px-1.5,y+pz,bottom+py-native_bottom) for px,py,pz in part['vertices']]
        g.native_piece(vertices,part['faces'],part['uv'],material)
    # Continuous wall around all four corners. The native opaque recess closes
    # the opening, so the doorway requires no hidden furnished interior.
    opening=.6029270887374878/2;head=.6832980513572693-native_bottom
    # Grid rooms place their plaster at 0.04 behind the cell face. Their
    # door insert joins that exact plane, without duplicate perimeter caps
    # on the adjacent wooden baseboard ends. Older free-standing facades
    # have an actual deeper recess, which needs its four cavity faces.
    for lo,hi,low,high in ((-.5,-opening,0,1),(opening,.5,0,1),(-opening,opening,head,1)):
        facade_panel(g,'Y',y+panel_depth,x+lo,x+hi,bottom+low,bottom+high,False,CIVIC_ORANGE_PANEL)
    # These are the INSIDE faces of a recess, visible from the doorway cavity.
    # Outward box winding shows in Blender's two-sided preview but is culled
    # by the native one-sided material, reopening the angled perimeter slots.
    if facade=='recessed':
        for xx,positive in ((x-.5,True),(x+.5,False)):
            facade_panel(g,'X',xx,y,y+.12,bottom,bottom+1,positive,CIVIC_ORANGE_PANEL)
        for zz,face in ((bottom,(0,1,2,3)),(bottom+1,(3,2,1,0))):
            g.add([(x-.5,y,zz),(x+.5,y,zz),(x+.5,y+.12,zz),(x-.5,y+.12,zz)],
                  [face],CIVIC_ORANGE_PANEL)
    if threshold:g.box((x,y-.055,bottom+.015),(.79,.24,.03),WOOD)


def arched_portal(g,x,y,bottom,width,height,threshold_top=.03,threshold=True):
    """Dark recessed entrance, segmented timber arch and clear doorstep.

    This creates artwork only. The native idle/access slot must be authored at
    (x,y-.08,bottom) during grid integration; never add a character to the mesh.
    """
    radius=width/2;spring=bottom+height-radius
    outline=[(x-radius,y+.105,bottom),(x+radius,y+.105,bottom)]
    outline.extend((x+math.cos(a)*radius,y+.105,spring+math.sin(a)*radius)
                   for a in [i*math.pi/16 for i in range(17)])
    g.add(outline,[tuple(range(len(outline)))],KILN_SOOT)
    for xx in (x-radius-.04,x+radius+.04):
        jamb_bottom=bottom+threshold_top if threshold else bottom
        g.box((xx,y,(jamb_bottom+spring)/2),(.095,.16,spring-jamb_bottom),WOOD)
        for z in (bottom+.09,spring-.06):steel_bolt(g,(xx,y-.09,z),'Y',.017)
    for i in range(12):
        a=i*math.pi/12;b=(i+1)*math.pi/12
        vertices=[(x+math.cos(angle)*r,yy,spring+math.sin(angle)*r)
                  for yy in (y-.08,y+.08) for r in (radius,radius+.105) for angle in (a,b)]
        g.add(vertices,[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)],WOOD)
        angle=(a+b)/2;steel_bolt(g,(x+math.cos(angle)*(radius+.052),y-.095,spring+math.sin(angle)*(radius+.052)),'Y',.015)
        # Fill rectangular facade corners above the opening so the arch is
        # cut into a wall, rather than floating in an otherwise open shed.
        g.add([(x+math.cos(a)*radius,y+.025,spring+math.sin(a)*radius),
               (x+math.cos(b)*radius,y+.025,spring+math.sin(b)*radius),
               (x+math.cos(b)*radius,y+.025,bottom+height+.12),
               (x+math.cos(a)*radius,y+.025,bottom+height+.12)],[(0,1,2,3)],PLANK)
    if threshold:g.box((x,y-.055,bottom+threshold_top-.015),(width+.18,.38,.03),WOOD)


def building_portal_side(g,x,y,bottom,*,facade='recessed',panel_depth=None):
    portal=Geometry('Side portal source');building_portal(portal,0,0,bottom,facade=facade,panel_depth=panel_depth)
    vertices=[(x-v[1],y-v[0],v[2]) for v in portal.vertices]
    for face,material,uv,source in zip(portal.faces,portal.materials,portal.face_uvs,portal.face_sources,strict=True):
        g.add([vertices[i] for i in reversed(face)],[tuple(range(len(face)))],material)
        g.face_uvs[-1]=list(reversed(uv)) if uv is not None else None
        g.face_sources[-1]=source


CYAN=25
RUBBER=26

def extra_materials():
    import bpy
    result=[]
    for name,color,rough,metal,emission in (
        ('Frontier cyan instrument',(.025,.48,.48),.35,.18,1.3),
        ('Frontier dark belt rubber',(.026,.034,.029),.88,.08,0)):
        material=bpy.data.materials.new(name);material.use_nodes=True
        bs=material.node_tree.nodes['Principled BSDF']
        bs.inputs['Base Color'].default_value=(*color,1)
        bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
        bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=emission
        result.append(material)
    return result


def window_y(g,x,y,z,scale=1,face='front'):
    from architectural_windows import window
    window(g,x,y,z,scale,face)


def side_window(g,x,y,z,scale=1,face='right'):
    from architectural_windows import window
    window(g,x,y,z,scale,face)


def gauge(g,x,y,z,r=.09,rim_material=BRASS):
    g.cylinder((x,y,z),r,.045,rim_material,'Y',24)
    g.cylinder((x,y-.03,z),r*.79,.016,GLASS,'Y',24)
    g.beam((x,y-.046,z),(x+r*.48,y-.046,z+r*.42),.009,mat=CYAN)
    for a in range(7):
        angle=a*math.pi/5-.3
        g.beam((x+math.cos(angle)*r*.57,y-.047,z+math.sin(angle)*r*.57),
               (x+math.cos(angle)*r*.68,y-.047,z+math.sin(angle)*r*.68),.006,mat=IRON)

