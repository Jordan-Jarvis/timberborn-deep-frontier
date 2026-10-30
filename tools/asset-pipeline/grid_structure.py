"""Author visible platform parts and their exact picking boxes from one grid contract.

Bounds are explicitly authored in native grid XYZ, with exclusive upper edges.
This creates geometry at those dimensions; it never fits or rounds an old mesh.
"""
import math
from frontier_architecture import WOOD,PLANK,IRON,facade_panel
from reference_materials import CIVIC_CONCRETE,CIVIC_ORANGE_PANEL,CIVIC_FORGED_PANEL


def grid_bounds(bounds):
    if len(bounds)!=6 or any(type(v) is not int for v in bounds):
        raise ValueError('Structural bounds require six explicit integer grid coordinates')
    if any(bounds[i]>=bounds[i+3] for i in range(3)):
        raise ValueError('Structural bounds must have positive width, depth and height')


FASCIA_SIDES=('front','back','left','right')


def platform(g,ident,bounds,origin,supports,floor_material=PLANK,*,slab_material=None,
             support_style='timber',fascia=(),fascia_material=WOOD,beam_material=WOOD,beam_depth=.12,board_relief=.004):
    """Slab carried by explicitly authored short posts, not a per-tile forest.

    Defaults reproduce the original timber module exactly. Opt-in options:
    `slab_material` gives the 106 mm structural layer its own material (a cast
    slab under timber boards); `support_style='pier'` stands each authored
    post on a cast footing (ground) or bearing plate (deck) with a cap collar
    and knee braces into the edge beams it carries; `fascia` lists exposed
    edges as (side, start, end) native spans and closes them with a board
    flush to the tile boundary below the slab. `board_relief` is the board
    thickness above the structural layer. The original 4 mm sits exactly on
    the strict 0.004 overlap tolerance between board tops and the slab seen
    through board joints, so reworked decks use 10 mm. The total slab stays
    110 mm. Picking volumes for posts keep their original envelope, so
    placement data is independent of the trim.
    """
    grid_bounds(bounds)
    if any(p['id']==ident for p in g.structural_parts):
        raise ValueError('Duplicate authored structural module '+ident)
    if support_style not in ('timber','pier'):raise ValueError('Unknown deck support style '+str(support_style))
    if not .08<=beam_depth<=.24:raise ValueError('Edge beam depth must stay within the slab layer band')
    if not .004<=board_relief<=.02:raise ValueError('Deck board relief must stay between 4 and 20 mm')
    x0,y0,z0,x1,y1,z1=bounds
    ox,oy,oz=origin
    boxes=[]
    def box(center,size,material):
        g.box((center[0]-ox,center[1]-oy,center[2]-oz),size,material)
        boxes.append({'center':list(center),'size':list(size)})
    def art(center,size,material):
        # Decorative trim only; never a picking volume.
        g.box((center[0]-ox,center[1]-oy,center[2]-oz),size,material)
    slab_material=floor_material if slab_material is None else slab_material
    # The standard 120 mm beam keeps its exact original centre expression.
    beam_z=z1-.17 if beam_depth==.12 else z1-.11-beam_depth/2
    # Individual boards occupy the exact declared slab, without edge overhang.
    n=math.ceil((y1-y0)/.20)
    width=(y1-y0)/n
    # Deeper relief: a joint-free nosing closes both board ends, so the 6 mm
    # board joints do not open as notches in the side faces of the deck.
    nosing=.02 if board_relief>.004 else 0
    for row in range(n):
        # The slight joint is inside the slab's footprint.
        cy=y0+(row+.5)*width
        g.box(((x0+x1)/2-ox,cy-oy,z1-board_relief/2-oz),(x1-x0-2*nosing,width-.006,board_relief),floor_material)
    if nosing:
        # Joint beds: one upward quad 4 mm below the board tops in each 6 mm
        # joint, overlapping 2 mm under both neighbouring boards. Joints read
        # as dark lines but are only 4 mm deep, and no bed face lies under a
        # board top, so the strict overlap check sees no coplanar pair.
        for k in range(n+1):
            jy=y0+k*width
            a=max(y0,jy-.005);b=min(y1,jy+.005)
            g.add([(x0+nosing-ox,a-oy,z1-.004-oz),(x1-nosing-ox,a-oy,z1-.004-oz),
                   (x1-nosing-ox,b-oy,z1-.004-oz),(x0+nosing-ox,b-oy,z1-.004-oz)],[(0,1,2,3)],floor_material)
        # Hard-edged like the structural plate: a bevel would chamfer the
        # outer face back from the tile boundary and reopen the side.
        for a,b in ((x0,x0+nosing),(x1-nosing,x1)):
            nose=[(x-ox,y-oy,z-oz) for z in (z1-board_relief,z1) for y in (y0,y1) for x in (a,b)]
            for face in ((0,2,3,1),(4,5,7,6),(0,1,5,4),(1,3,7,5),(3,2,6,7),(2,0,4,6)):
                g.add([nose[i] for i in face],[(0,1,2,3)],floor_material)
    # The solid structural layer and shallow top boards occupy disjoint height
    # bands. Backing spans the complete slab; an inset backing left pinholes
    # at every board joint along the deck's outer edge.
    slab=[(x-ox,y-oy,z-oz) for z in (z1-.11,z1-board_relief) for y in (y0,y1) for x in (x0,x1)]
    # Each structural plate face owns its hard boundary edges. Applying the
    # decorative beam bevel here rounded both sides of adjoining tile slabs
    # away from their common edge and reopened a through-crack.
    for face in ((0,2,3,1),(4,5,7,6),(0,1,5,4),(1,3,7,5),(3,2,6,7),(2,0,4,6)):
        g.add([slab[i] for i in face],[(0,1,2,3)],slab_material)
    boxes.append({'center':[(x0+x1)/2,(y0+y1)/2,z1-.055],
                  'size':[x1-x0,y1-y0,.11]})
    # Continuous edge beams and a few joists span bays. No repeated little
    # frames around every path tile, and no automatic ground-reaching posts.
    for yy in (y0+.14,y1-.14):box(((x0+x1)/2,yy,beam_z),(x1-x0-.12,.16,beam_depth),beam_material)
    for xx in (x0+.14,x1-.14):box((xx,(y0+y1)/2,beam_z),(.16,y1-y0-.44,beam_depth),beam_material)
    for xx in range(x0+2,x1,2):box((xx,(y0+y1)/2,beam_z),(.14,y1-y0-.44,beam_depth),beam_material)
    beam_bottom=z1-.11-beam_depth
    for cell,corner,bottom in supports:
        if len(cell)!=2 or len(corner)!=2 or any(v not in (-1,1) for v in corner):raise ValueError('Explicit post tile and corner required')
        if not (x0<=cell[0]<x1 and y0<=cell[1]<y1 and z0<=bottom<z1 and z1-bottom<=2):raise ValueError('Post outside module or more than two levels tall: '+ident)
        x,y=(cell[i]+.5+.41*corner[i] for i in range(2))
        if support_style=='timber':
            box((x,y,(bottom+z1-.23)/2),(.16,.16,z1-bottom-.23),WOOD)
            # Small collars stay inside the same reserved native corner.
            for z in (bottom+.05,z1-.28):
                box((x,y,z),(.18,.18,.07),IRON)
            continue
        if beam_depth!=.12:raise ValueError('Pier supports carry the standard 120 mm edge beams')
        top=z1-.23
        boxes.append({'center':[x,y,(bottom+top)/2],'size':[.16,.16,top-bottom]})
        for z in (bottom+.05,z1-.28):boxes.append({'center':[x,y,z],'size':[.18,.18,.07]})
        if bottom==0:
            # Cast pier: the only solid that owns the ground under the post.
            art((x,y,.20),(.17,.17,.40),CIVIC_CONCRETE)
            art((x,y,.42),(.18,.18,.04),IRON)
            shaft=.41
        else:
            # Bearing plate on the deck below; its underside rests on the boards.
            art((x,y,bottom+.025),(.18,.18,.05),IRON)
            shaft=bottom+.04
        art((x,y,(shaft+top)/2),(.16,.16,top-shaft),WOOD)
        art((x,y,z1-.28),(.18,.18,.07),IRON)
        # Knee braces into each edge beam that actually passes the post. They
        # stay within the outer 0.18 strip of the post's own cell, high under
        # the slab, and run toward the cell centre.
        lines={0:[v for v in (y0+.14,y1-.14) if abs(v-y)<.1],1:[v for v in (x0+.14,x1-.14) if abs(v-x)<.1]}
        # A one-layer ground post (2026-10-30) is short enough that z1-.62
        # falls inside its cast pier; the brace then starts just above the
        # pier's bearing plate. Taller posts keep their original brace.
        brace_low=max(z1-.62,shaft+.06)
        for axis,found in lines.items():
            for line in found:
                a=[x,y,brace_low];b=[x,y,beam_bottom-.005]
                a[1-axis]=b[1-axis]=line
                b[axis]=(x if axis==0 else y)-corner[axis]*.34
                g.beam(tuple(v-o for v,o in zip(a,origin)),tuple(v-o for v,o in zip(b,origin)),.07,.07,WOOD)
    # Exposed deck edges: a fascia flush with the tile boundary, below the
    # slab and clear of the post collars. Side boards stop at perpendicular
    # front/back boards so no two end faces share a plane.
    spans={side:[] for side in FASCIA_SIDES}
    for side,a,b in fascia:
        if side not in FASCIA_SIDES or not a<b:raise ValueError('Fascia needs a side and a positive native span: '+ident)
        lo,hi=(x0,x1) if side in ('front','back') else (y0,y1)
        if not lo<=a<b<=hi:raise ValueError('Fascia span outside its platform: '+ident)
        spans[side].append((a,b))
    t=.05;fz=(z1-.235,z1-.112)
    for side,items in spans.items():
        for a,b in items:
            if side in ('front','back'):
                y=y0+t/2 if side=='front' else y1-t/2
                art(((a+b)/2,y,sum(fz)/2),(b-a,t,fz[1]-fz[0]),fascia_material)
            else:
                x=x0+t/2 if side=='left' else x1-t/2
                if any(lo<=x<=hi for lo,hi in spans['front']) and a==y0:a+=t
                if any(lo<=x<=hi for lo,hi in spans['back']) and b==y1:b-=t
                art((x,(a+b)/2,sum(fz)/2),(t,b-a,fz[1]-fz[0]),fascia_material)
    g.structural_parts.append({'id':ident,'kind':'platform','bounds':list(bounds),
        'floorHeight':z1,'supports':supports,'pickingBoxes':boxes,
        'occupation':'Top, Corners slab; Corners only at authored posts; BlockObject stack support'})


def gallery(g,rails,ident,bounds,origin,edges,supports,*,grid_rails=False,**platform_options):
    platform(g,ident,bounds,origin,supports,**platform_options)
    x0,y0,z0,x1,y1,z1=bounds
    ox,oy,oz=origin
    # The entire native post remains inside its structural footprint.
    a=x0+.10-ox;b=x1-.10-ox;c=y0+.10-oy;d=y1-.10-oy
    ends={'front':((a,c),(b,c)),'back':((a,d),(b,d)),
          'left':((a,c),(a,d)),'right':((b,c),(b,d))}
    for edge in edges:
        if grid_rails:rails.run_grid(ident+edge,*ends[edge],z1-oz,origin)
        else:rails.run(ident+edge,*ends[edge],z1-oz)


def room(g,ident,bounds,origin,front_door=None,*,exterior,joined_ends=None,joined_post_inset=0.0,wall_style='banded'):
    """Opaque exterior shell; shared partitions and room interiors are not drawn.

    `wall_style='storey'` (opt-in, 2026-10-30 compaction) is the infill for a
    one-layer storey: one plaster band between the base beam and the head
    fascia (a concrete plinth and plank sill on the ground storey) instead of
    the five courses of the two-layer default, which crowd a one-layer wall.
    """
    grid_bounds(bounds)
    if wall_style not in ('banded','storey'):raise ValueError('Unknown room wall style '+str(wall_style))
    if wall_style=='storey' and bounds[5]-bounds[2]!=1:raise ValueError('Storey walls are for one-layer rooms: '+ident)
    if any(p['id']==ident for p in g.structural_parts):raise ValueError('Duplicate room '+ident)
    x0,y0,z0,x1,y1,z1=bounds
    ox,oy,oz=origin
    if set(exterior)!={'front','back','left','right'}:raise ValueError('Declare every exterior wall span')
    if joined_ends is None:joined_ends={}
    if any(side not in exterior or any(end not in ('start','end') for end in ends) for side,ends in joined_ends.items()):
        raise ValueError('Joined room ends require explicit exterior side and start/end names')
    def box(center,size,material):
        g.box((center[0]-ox,center[1]-oy,center[2]-oz),size,material)
    def face_runs(a,b,door):
        if door is None:return [(a,b)]
        # Subtract the authored opening from this wall interval. A single-cell
        # doorway can consume the entire infill; never emit a negative box.
        left,right=door[0]-door[1]/2,door[0]+door[1]/2
        return [(lo,hi) for lo,hi in ((a,min(b,left)),(max(a,right),b)) if hi>lo]
    # The infill and exposed wood occupy disjoint height bands. Structural
    # timber projects to the tile face; panels sit 4 cm behind that face.
    # Never put a full wood face at the same depth as a plaster face.
    bands=((z0+.20,z0+.45,CIVIC_CONCRETE if z0==0 else CIVIC_ORANGE_PANEL),
           (z0+.45,z0+.53,PLANK),(z0+.53,z1-.36,CIVIC_ORANGE_PANEL),
           (z1-.36,z1-.33,PLANK),(z1-.33,z1-.28,CIVIC_FORGED_PANEL))
    if wall_style=='storey':
        bands=(((z0+.20,z0+.36,CIVIC_CONCRETE),(z0+.36,z0+.40,PLANK),(z0+.40,z1-.28,CIVIC_ORANGE_PANEL))
               if z0==0 else ((z0+.20,z1-.28,CIVIC_ORANGE_PANEL),))
    for side,axis,plane,sign,start,end,door in (
            ('front','Y',y0,1,x0,x1,front_door),('back','Y',y1,-1,x0,x1,None),
            ('left','X',x0,1,y0,y1,None),('right','X',x1,-1,y0,y1,None)):
        for a,b in exterior[side]:
            if not start<=a<b<=end:raise ValueError('Exterior wall span outside room: '+ident+'/'+side)
            # Front/back frames own the room corners; side beams butt into them.
            # A shared room junction has no perpendicular wall/post. Do not
            # reserve an imaginary corner there: that cut a 20 cm vertical
            # opening in both halves of the Restaurant/Kitchen junction.
            corner_a=axis=='Y' or any(lo<=plane<=hi for lo,hi in exterior['front'])
            corner_b=axis=='Y' or any(lo<=plane<=hi for lo,hi in exterior['back'])
            if axis=='X' and front_door is not None and abs(plane-front_door[0])<=front_door[1]/2:
                # A full-cell door removes the lower front corner post. The
                # side wall must continue to the doorway's return instead of
                # leaving the post's former 20 cm bay open below the lintel.
                corner_a=False
            frame_a=a+.214 if axis=='X' and a==start and corner_a else a
            frame_b=b-.214 if axis=='X' and b==end and corner_b else b
            panel_a=a+.20 if a==start and corner_a else a
            panel_b=b-.20 if b==end and corner_b else b
            def panel(lo,hi,low,high,material):
                facade_panel(g,axis,plane+sign*.04-(oy if axis=='Y' else ox),
                    lo-(ox if axis=='Y' else oy),hi-(ox if axis=='Y' else oy),low-oz,high-oz,sign<0,material)
            def member(lo,hi,z,height,material,width=.20):
                # The steel collar reaches the cell face; timber is recessed
                # behind it by its real plate thickness, never coplanar.
                inset=.014 if material==WOOD else 0
                center=((lo+hi)/2,plane+sign*(width/2+inset),z) if axis=='Y' else (plane+sign*(width/2+inset),(lo+hi)/2,z)
                size=(hi-lo,width,height) if axis=='Y' else (width,hi-lo,height)
                box(center,size,material)
            for low,high,material in bands:
                for lo,hi in face_runs(panel_a,panel_b,door if low<z0+1 else None):panel(lo,hi,low,high,material)
                if door is not None and low<z0+1<high:
                    lo=max(panel_a,door[0]-door[1]/2);hi=min(panel_b,door[0]+door[1]/2)
                    if hi>lo:panel(lo,hi,z0+1,high,material)
            # Full-height exterior fascia closes the old inter-storey gap. It
            # does not require a hidden floor/ceiling slab inside the room.
            for lo,hi in face_runs(frame_a,frame_b,door):member(lo,hi,z0+.10,.20,WOOD)
            # This fascia is a surface, not a full-depth beam. It spans the
            # whole authored wall, including the corner strips. Its recessed
            # depth is shared with the perpendicular fascia; shortening its
            # span as well left an exposed sliver above full-width doorways.
            fascia_a=a
            fascia_b=b
            facade_panel(g,axis,plane+sign*.014-(oy if axis=='Y' else ox),
                fascia_a-(ox if axis=='Y' else oy),fascia_b-(ox if axis=='Y' else oy),z1-.28-oz,z1-oz,sign<0,WOOD)
            columns=[v+.5 for v in range(start,end) if a<=v+.5<=b]
            if axis=='Y':
                columns += [v for v in (start+.10,end-.10) if a<=v<=b]
            for v in columns:
                bottom=z0+.20
                if door is not None and abs(v-door[0])<door[1]/2+.13:
                    if v not in (start+.10,end-.10):continue
                    # A one-cell stairhead's doorway takes its entire lower
                    # facade. Its corner posts still close the upper facade;
                    # dropping the whole posts left open strips beside it.
                    bottom=z0+1
                top=z1-.28
                if top<=bottom:continue
                # Opt-in: at a joined room end the corner post stops short of the
                # junction, so its end face is not coplanar with the collar's.
                post_lo=v-.10+(joined_post_inset if v==start+.10 and 'start' in joined_ends.get(side,()) else 0)
                post_hi=v+.10-(joined_post_inset if v==end-.10 and 'end' in joined_ends.get(side,()) else 0)
                member(post_lo,post_hi,(bottom+top)/2,top-bottom,WOOD)
                collar_lo=start if v==start+.10 and 'start' in joined_ends.get(side,()) else v-.13
                collar_hi=end if v==end-.10 and 'end' in joined_ends.get(side,()) else v+.13
                for z in (bottom+.08,z1-.28):member(collar_lo,collar_hi,z,.11,IRON,.28)
    # The shell's inside (behind the panels, which sit 4 cm in from the tile
    # faces, between the base beam and the head fascia) is a hidden volume
    # for the enclosed-face cull: the back halves of posts and collars.
    # Every removal it proposes is ray-verified at build, so an open side
    # or a roof gap keeps its faces; the doorway recess stays visible.
    exposed=[]
    if front_door is not None:
        exposed.append(((front_door[0]-front_door[1]/2-.2-ox,y0-.1-oy,z0-.01-oz),
                        (front_door[0]+front_door[1]/2+.2-ox,y0+.9-oy,z0+1.3-oz)))
    g.declare_hidden_volume((x0+.04-ox,y0+.04-oy,z0+.20-oz),(x1-.04-ox,y1-.04-oy,z1-.28-oz),exposed)
    g.structural_parts.append({'id':ident,'kind':'room','bounds':list(bounds),
        'pickingBoxes':[{'center':[(x0+x1)/2,(y0+y1)/2,(z0+z1)/2],
                         'size':[x1-x0,y1-y0,z1-z0]}]})
