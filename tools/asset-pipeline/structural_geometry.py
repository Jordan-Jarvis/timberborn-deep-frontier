"""Original modular construction art using the established Iron Teeth palette.

These are new structural designs, not reconstructions from a reference plan.
All support planes are authored at exact whole layers. Open bays deliberately
exclude mid-height decorative bracing that would obstruct transport.
"""
from frontier_architecture import IRON, SAND, LIME
from reference_materials import CIVIC_CONCRETE
from walkway_geometry import RailAssembly

# Triangle budget: no bevel modifier on these models (render_reference_studies
# builds them like the shell models); the native atlases paint edge wear.


def fastener(g,p,axis='Y',r=.022):
    """Bolt head for the triangle budget: one six-sided prism, half buried in
    its host (industrial_geometry.steel_bolt's 12-sided head plus shank is 64
    triangles; at game zoom a bolt head is a pixel or two). The buried cap is
    removed by the enclosed-face cull."""
    g.cylinder(p,r*1.4,.028,IRON,axis,6)


def masonry(g, stone):
    # Recessed mortar core, alternating dressed stone courses and a flush cap.
    g.box((.5,.5,.495),(.98,.98,.99),CIVIC_CONCRETE)
    for row in range(4):
        z=.015+(row+.5)*.24
        widths=(.33,.66) if row%2 else (.66,.33)
        for side in range(4):
            start=.006
            for width in widths:
                along=start+width/2
                if side<2:
                    g.box((along,.024 if side==0 else .976,z),(width-.015,.048,.224),stone)
                else:
                    g.box((.024 if side==2 else .976,along,z),(.048,width-.015,.224),stone)
                start+=width
    g.box((.5,.5,.98),(.992,.992,.04),stone)
    return RailAssembly('StructureRails')


def sandstone_masonry(g,parts):
    return masonry(g,SAND)


def limestone_masonry(g,parts):
    return masonry(g,LIME)


def concrete_block(g,parts):
    # Cast panels with shallow form seams, steel ties and an exact support top.
    g.box((.5,.5,.5),(.99,.99,1),CIVIC_CONCRETE)
    for z in (.24,.49,.74):
        for y in (.002,.998):g.box((.5,y,z),(.98,.004,.008),IRON)
        for x in (.002,.998):g.box((x,.5,z),(.004,.98,.008),IRON)
    for z in (.16,.84):
        for u in (.18,.82):
            for y in (.003,.997):g.cylinder((u,y,z),.025,.006,IRON,'Y',6)
            for x in (.003,.997):g.cylinder((x,u,z),.025,.006,IRON,'X',6)
    return RailAssembly('StructureRails')


def reinforced_dam_block(g,parts):
    # Recess the cast infill so the external cage is actually visible. Its top
    # is the exact support top at 1.0 (whole layer); the corner posts stop
    # 1 cm lower so the two tops never share a plane where they overlap.
    g.box((.5,.5,.505),(.88,.88,.99),CIVIC_CONCRETE)
    for x in (.06,.94):
        for y in (.06,.94):
            g.box((x,y,.495),(.10,.10,.99),IRON)
    # Bands stand 7.5 mm proud of the corner posts they cross. At the corners
    # the two directions overlap; the side bands are 1 cm shallower so each
    # end is buried inside the crossing band instead of sharing its faces.
    for z in (.08,.50,.92):
        for y in (.02,.98):
            g.box((.5,y,z),(.955,.035,.075),IRON)
            for x in (.12,.50,.88):fastener(g,(x,y,z),'Y',.018)
        for x in (.02,.98):
            g.box((x,.5,z),(.035,.955,.065),IRON)
            for y in (.12,.50,.88):fastener(g,(x,y,z),'X',.018)
    return RailAssembly('StructureRails')


def concrete_overflow_dam(g,parts):
    # The visible sill matches the native partial obstacle at 0.65 layers.
    g.box((.5,.5,.325),(.99,.99,.65),CIVIC_CONCRETE)
    for x in (.08,.92):
        for y in (.08,.92):
            g.box((x,y,.775),(.15,.15,.25),IRON)
            fastener(g,(x,y,.975),'Z',.018)
    g.box((.5,.5,.95),(.99,.99,.10),CIVIC_CONCRETE)
    for x in (.04,.96):g.box((x,.5,.89),(.06,.97,.025),IRON)   # rail ends buried in the corner posts
    for z in (.12,.48):
        for y in (.008,.992):g.box((.5,y,z),(.96,.012,.025),IRON)
    return RailAssembly('StructureRails')


def girder_y(g,x,y0,y1,z,height=.30,width=.13):
    # The web meets the flanges, instead of sharing their top/bottom faces.
    g.box((x,(y0+y1)/2,z),(.045,y1-y0-.09,height-.10),IRON)
    for zz in (z-height/2+.025,z+height/2-.025):
        g.box((x,(y0+y1)/2,zz),(width,y1-y0,.05),IRON)
    for y in (y0+.06,y1-.06):
        g.box((x,y,z),(width,.045,height-.10),IRON)
        for dz in (-height*.27,height*.27):
            fastener(g,(x-width/2-.012,y,z+dz),'X',.018)
            fastener(g,(x+width/2+.012,y,z+dz),'X',.018)


def concrete_overhang(g,parts):
    # Prestressed-looking deck over paired steel girders; no fictional stress sim.
    for y in range(8):
        g.box((.5,y+.5,.94),(.99,.986,.12),CIVIC_CONCRETE)
        for x in (.13,.87):
            girder_y(g,x,y+.015,y+.985,.68,.40,.20)
            g.box((x,y+.5,.87),(.23,.23,.035),IRON)
        g.box((.5,y+.5,.85),(.76,.10,.06),IRON)
        for x in (.06,.94):
            for yy in (y+.18,y+.82):
                fastener(g,(x,yy,.91),'Z',.025)
    # The supported anchor end has substantial base feet and diagonal gussets.
    for x in (.14,.86):
        g.box((x,.5,.19),(.26,.96,.38),CIVIC_CONCRETE)
        g.box((x,.5,.40),(.27,.97,.045),IRON)   # bearing plate ends stand clear of the foot ends
        g.beam((x,.12,.40),(x,.91,.73),.13,.10,IRON)
    return RailAssembly('StructureRails')


def joist_y(g,x,y0,y1,top):
    # Secondary deck joist hung between the cross girders. Its top flange
    # bears on the slab soffit; end plates meet the girder faces exactly.
    for y,direction in ((y0,1),(y1,-1)):
        g.box((x,y+direction*.02,top-.10),(.17,.04,.17),IRON)
        for dx in (-.05,.05):
            fastener(g,(x+dx,y+direction*.047,top-.10),'Y',.016)
    a,b=y0+.04,y1-.04
    g.box((x,(a+b)/2,top-.10),(.035,b-a,.12),IRON)
    for z in (top-.02,top-.18):
        g.box((x,(a+b)/2,z),(.12,b-a,.04),IRON)


SCAFFOLD_SPANS=(3,4,5)
SIDE_SEAM_CROWN=.005
SCAFFOLD_LEGS=(1,2,3)


def scaffold_for(n,legs):
    """Square deck of n-by-n cells on four corner columns `legs` layers high.

    The deck surface is the whole layer legs+1. Everything below the deck
    stays inside the four corner cells, leaving the central cross clear.
    """
    if n not in SCAFFOLD_SPANS or legs not in SCAFFOLD_LEGS:
        raise ValueError(f'Unsupported concrete platform {n}x{n} with {legs}-layer legs')
    top=legs+1
    far=n-.18
    def build(g,parts):
        # Four perimeter columns leave the center and cross-lanes open.
        for x in (.18,far):
            for y in (.18,far):
                g.box((x,y,.15),(.34,.34,.30),CIVIC_CONCRETE)
                g.box((x,y,.32),(.35,.35,.04),IRON)
                g.box((x,y,(.34+top-.30)/2),(.20,.20,top-.64),CIVIC_CONCRETE)
                for xx in (x-.12,x+.12):g.box((xx,y,(.34+top-.30)/2),(.035,.23,top-.64),IRON)
                # Base collar, one per intermediate layer joint, and the head.
                for z in (.43,*(k+.48 for k in range(1,legs)),top-.48):
                    g.box((x,y,z),(.29,.29,.08),IRON)
                    for dx in (-.10,.10):
                        fastener(g,(x+dx,y-.16,z),'Y',.022)
                        fastener(g,(x+dx,y+.16,z),'Y',.022)
                for dx in (-.12,.12):
                    for dy in (-.12,.12):fastener(g,(x+dx,y+dy,.355),'Z',.022)
        # High knee braces stay above the logistics opening, in the deck layer.
        for x in (.18,far):
            girder_y(g,x,.04,n-.04,top-.27,.30,.26)
            for y,direction in ((.18,1),(far,-1)):
                g.beam((x,y,top-.83),(x,y+direction*.49,top-.30),.12,.10,IRON)
        for y in (.18,far):
            g.box((n/2,y,top-.27),(n-.62,.25,.30),IRON)
            for x,direction in ((.18,1),(far,-1)):
                g.beam((x,y,top-.83),(x+direction*.49,y,top-.30),.12,.10,IRON)
        # Wider spans carry secondary joists under every interior cell seam,
        # wholly inside the deck layer and clear of the bay below.
        if n>3:
            for x in range(1,n):joist_y(g,x,.305,n-.305,top-.12)
        for x in range(n):
            for y in range(n):
                g.box((x+.5,y+.5,top-.06),(.988,.988,.12),CIVIC_CONCRETE)
                for u in range(5):
                    # Embedded metal seam with a visible shallow raised crown.
                    g.box((x+.10+u*.20,y+.5,top),(.012,.82,.008),IRON)
        return RailAssembly('StructureRails')
    return build


def anchored_deck_for(n):
    """Legless n-by-n concrete deck hung beside a reinforced dam block.

    Art space: deck cells x 0..n, y 0..n on layer z 0..1, top exactly 1.0,
    so it is level with the anchor's top. The anchor block itself (x a..a+1,
    y n..n+1, z 0..1; a = n//2, the centre column of the odd-width native
    grid, so it is flip-invariant) is not part of this model and stays empty;
    only the two cleat shoes rest on its top. The export origin moves the art
    one layer down for native BaseZ 1 (structural_layouts.py).
    """
    if n not in SCAFFOLD_SPANS:
        raise ValueError(f'Unsupported concrete side platform {n}x{n}')
    a=n//2
    top=1
    far=n-.18
    def build(g,parts):
        # The platform deck frame without legs: perimeter girders and edge
        # beams in the deck layer, plus secondary joists on wider spans.
        for x in (.18,far):
            girder_y(g,x,.04,n-.04,top-.27,.30,.26)
        for y in (.18,far):
            g.box((n/2,y,top-.27),(n-.62,.25,.30),IRON)
        if n>3:
            for x in range(1,n):joist_y(g,x,.305,n-.305,top-.12)
        for x in range(n):
            for y in range(n):
                g.box((x+.5,y+.5,top-.06),(.988,.988,.12),CIVIC_CONCRETE)
                for u in range(5):
                    # Embedded metal seam, crown 5 mm proud. The platform
                    # decks' 4 mm crown sits exactly at the 0.004 audit
                    # epsilon, which float32 rounding fails at layer 1.
                    g.box((x+.10+u*.20,y+.5,top+SIDE_SEAM_CROWN-.004),(.012,.82,.008),IRON)
        # Bolted wall plate against the anchor face, below the slab and
        # 5 mm short of the cell boundary (the anchor's bands stand 2.5 mm in).
        g.box((a+.5,n-.02,.52),(.86,.03,.70),IRON)
        for x in (a+.12,a+.5,a+.88):
            for z in (.28,.50):fastener(g,(x,n-.035,z),'Y',.02)
        # Cross beam one cell out, clear of the joists, carrying two knee
        # braces that rise from the plate foot.
        g.box((a+.5,n-1,top-.23),(.76,.14,.22),IRON)
        for x in (a+.25,a+.75):
            g.beam((x,n-.035,.26),(x,n-1,top-.34),.10,.08,IRON)
        # Cleat shoes bearing on the anchor top at its deck-side corners.
        for x in (a+.12,a+.88):
            g.box((x,n+.085,top+.035),(.16,.15,.07),IRON)
            fastener(g,(x,n+.085,top+.07),'Z',.02)
        return RailAssembly('StructureRails')
    return build


def anchored_deck_ident(n):
    return f'ConcreteSidePlatform{n}x{n}'


def scaffold_ident(n,legs):
    # The original 3x3 with three-layer legs keeps its saved template name.
    return 'ConcreteScaffold3x3' if (n,legs)==(3,3) else f'ConcreteScaffold{n}x{n}H{legs}'


MODELS={
    'SandstoneMasonryBlock':sandstone_masonry,
    'LimestoneMasonryBlock':limestone_masonry,
    'ConcreteBlock':concrete_block,
    'ConcreteOverhang8x1':concrete_overhang,
    'ReinforcedDamBlock':reinforced_dam_block,
    'ConcreteOverflowDam':concrete_overflow_dam,
}
MODELS.update({scaffold_ident(n,legs):scaffold_for(n,legs) for n in SCAFFOLD_SPANS for legs in SCAFFOLD_LEGS})
MODELS.update({anchored_deck_ident(n):anchored_deck_for(n) for n in SCAFFOLD_SPANS})
