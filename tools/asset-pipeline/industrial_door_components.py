"""Explicit industrial portal assets in authored source coordinates.

These recipes generate only the requested door. Recess depth, native UVs and
the quarry's reflected side assembly remain part of the existing architecture.
MineralQuarry is the shared source for SandstoneQuarry and LimestoneQuarry.
"""
from frontier_architecture import Geometry, facade_panel, PLANK
from industrial_facades import building_portal, building_portal_side
from reference_materials import CIVIC_ORANGE_PANEL


DOORS = {
    'StoneCrusher': {
        # Native grid XY (crusher layout origin 0,0): centred on tile column 2,
        # face 0.10 behind the y=2 edge. Surface-only shoulders are on the face,
        # inset header 0.12 behind it. Explicit returns join the pitched
        # canopy/eave; a generic horizontal top cap duplicates its underside.
        'GroundDoor': {'position': (2.50, 2.10, 0), 'outward': (0, -1), 'transform': 'front',
            'facade': 'framed', 'panelDepth': .12, 'returnOwnership': 'complete'},
    },
    'CementKiln': {
        # Artwork = native grid - (1,2): centred on tile column 4 (grid x 4.5),
        # face 0.14 behind the grid y=1 edge. The header .12 behind the face
        # retains the recess. Shoulder-box ends occupy .01..09 behind the face
        # / Z=.08..1, so only the exposed strips are ours.
        'GroundDoor': {'position': (3.50, -.86, 0), 'outward': (0, -1), 'transform': 'front',
            'facade': 'framed', 'panelDepth': .12, 'returnOwnership': 'kiln-shoulder-strips'},
    },
    'ConcreteMixer': {
        # Native grid XY: centred on tile column 1, wall front .16 behind the
        # y=0 edge. The native casing is mounted .04 ahead of that wall
        # (face .12), matching the proven grid-door joint; infill meets it.
        'MixerOperatorDoor': {'position': (1.50, .12, 0), 'outward': (0, -1), 'transform': 'front',
            'facade': 'framed', 'panelDepth': .04, 'wallPlaneY': .16, 'returnOwnership': 'wall'},
    },
    'MineralQuarry': {
        # Each casing mounts .04 ahead of its actual facade. Ground cabin:
        # artwork = grid - (0,1); centred on grid tile column 1, face 0.14
        # behind the grid y=2 edge; shoulders meet the header at Y=1.18.
        'GroundDoor': {'position': (1.50, 1.14, 0), 'outward': (0, -1), 'transform': 'front',
            'facade': 'framed', 'panelDepth': .04, 'wallPlaneY': 1.18, 'returnOwnership': 'wall'},
        # (The two upper workshop doors and the control-room door went with
        # the compact 8x6x5 quarry, 2026-10-30.)
    },
    'SandstonePit': {
        # Centred on grid tile column 1 (x .93 + origin .57), casing face 0.14
        # behind the y=1 tile edge, inside the front column/shoulder reveal
        # (shoulders Y=1.07..1.17, header wall Y=1.07 above Z=1). The worker
        # idle point stays at Y=.98 (blueprint LocalAccess), so a 0.15 body
        # there clears the casing; at Y=1.06 the native opaque recess
        # (Y=anchor+.045..076) and lintel stood inside that body.
        'PitStoreDoor': {'position': (.93, 1.14, 0), 'outward': (0, -1), 'transform': 'front',
            'facade': 'framed', 'panelDepth': .01, 'returnOwnership': 'wall'},
    },
    'LimestonePit': {
        'PitStoreDoor': {'position': (.93, 1.14, 0), 'outward': (0, -1), 'transform': 'front',
            'facade': 'framed', 'panelDepth': .01, 'returnOwnership': 'wall'},
    },
    'ReinforcedHydroTurbine': {
        # Native grid: centred on tile x=6.5, casing face on the y=6 edge.
        'HydroWorkshopDoor': {'position': (5.5+1.0, 2.0+4.0, 2), 'outward': (0, -1),
            'transform': 'powerhouse-placement', 'localPosition': (5.5, 2.0, 2), 'translation': (1.0, 4.0, 0),
            # Room front=2.10-.06=2.04. Casing sits .04 ahead of its infill.
            # Its right edge is the workshop corner (side cladding on x=7).
            'facade': 'framed', 'panelDepth': .04, 'wallPlaneY': 2.04+4.0, 'returnOwnership': 'wall',
            'seamCorners': ['right'], 'seamCornerAcross': {'right': .30}},
    },
}
MODELS = frozenset(DOORS)

# The crusher, kiln and mixer ground doors are also registered in native grid
# XY by industrial_layouts.py (the content generator checks that contract).
# Both declarations must describe the same door.
def _check_registered_doors():
    from industrial_layouts import LAYOUTS
    for model, ident in (('StoneCrusher','GroundDoor'),('CementKiln','GroundDoor'),('ConcreteMixer','MixerOperatorDoor'),('MineralQuarry','GroundDoor')):
        door=LAYOUTS[model]['door'];origin=LAYOUTS[model]['origin']
        grid=[a+o for a,o in zip(DOORS[model][ident]['position'],origin,strict=True)]
        if any(abs(a-b)>1e-9 for a,b in zip(grid,door['position'],strict=True)) or list(DOORS[model][ident]['outward'])!=door['outward']:
            raise ValueError(f'{model} door anchor differs from its grid registration: {grid} vs {door}')
_check_registered_doors()
UV_PROFILES = {model: 'civic-native' for model in MODELS}
HYDRO_WORKSHOP_DOOR = {'position': (5.5, 2.0, 2), 'outward': (0, -1), 'transform': 'front',
    'facade': 'framed', 'panelDepth': .04, 'wallPlaneY': 2.04, 'returnOwnership': 'wall'}

# Immutable placement contract of the original 41-face recessed inserts.
# Migration must still find those exact old assemblies after an active door's
# facade anchor changes. Worker idle points are a separate source contract.
LEGACY_POSITIONS = {
    ('StoneCrusher','GroundDoor'): (1.11,.39,0),
    ('CementKiln','GroundDoor'): (3.45,-.79,0),
    ('ConcreteMixer','MixerOperatorDoor'): (1.65,.50,0),
    ('MineralQuarry','GroundDoor'): (1.37,1.35,0),
    ('SandstonePit','PitStoreDoor'): (.93,1.12-.06,0),
    ('LimestonePit','PitStoreDoor'): (.93,1.12-.06,0),
    ('ReinforcedHydroTurbine','HydroWorkshopDoor'): (5.35+1.0,2.24+4.0,2),
}
HYDRO_LEGACY_LOCAL_POSITION = (5.35,2.24,2)


def crusher_return_surfaces(g,position):
    """A pitched porch soffit joined inside its existing structural eave.

The front eave spans .145 ahead of the face to .005 behind it, Z=1..1.16; it
owns the low visible front edge. The ceiling starts inside that timber at
Z=1.01 and follows the authored canopy pitch (.25 rise / .84 run) to the rear
header .12 behind the face. Side returns meet this actual ceiling, rather
than leaving triangular gaps. The native door and its one-tile front infill
are unchanged; all positions follow the door anchor.
    """
    px,py,_=position
    front=1.01
    rear=front+.12*(.25/.84)
    x0,x1,y0,y1=px-.5,px+.5,py,py+.12
    for x,face in ((x0,(0,1,2,3)),(x1,(3,2,1,0))):
        g.add([(x,y0,0),(x,y1,0),(x,y1,rear),(x,y0,front)],
              [face],CIVIC_ORANGE_PANEL)
    g.add([(x0,y0,0),(x1,y0,0),(x1,y1,0),(x0,y1,0)],
          [(0,1,2,3)],CIVIC_ORANGE_PANEL)
    g.add([(x0,y0,front),(x1,y0,front),(x1,y1,rear),(x0,y1,rear)],
          [(3,2,1,0)],CIVIC_ORANGE_PANEL)


def kiln_return_strips(g,position):
    """Only exposed returns around the porch shoulder-box ends.

The boxes occupy X = door -.61..-.50 / +.50..+.61, Y = face +.01..+.09 and
Z=.08..1.08. Those end faces already own the middle of the reveals. The
source insert owns the adjoining narrow strips and caps. All positions
follow the door anchor.
    """
    px,py,_=position
    for x,positive in ((px-.5,True),(px+.5,False)):
        for y0,y1,z0,z1 in ((py,py+.01,0,1),(py+.09,py+.12,0,1),(py+.01,py+.09,0,.08)):
            facade_panel(g,'X',x,y0,y1,z0,z1,positive,CIVIC_ORANGE_PANEL)
    for z,face in ((0,(0,1,2,3)),(1,(3,2,1,0))):
        g.add([(px-.5,py,z),(px+.5,py,z),(px+.5,py+.12,z),(px-.5,py+.12,z)],
              [face],CIVIC_ORANGE_PANEL)


def _door(model, ident, definition, *, legacy=False):
    g = Geometry(f'{model}.Door.{ident}')
    position=LEGACY_POSITIONS[(model,ident)] if legacy else definition['position']
    facade='recessed' if legacy else definition['facade']
    options={'facade':facade}
    if facade=='framed':options['panel_depth']=definition['panelDepth']
    transform = definition['transform']
    if transform == 'front':
        if definition['outward'] != (0, -1):
            raise ValueError('Front portal must face source -Y')
        building_portal(g, *position, **options)
    elif transform == 'reflected-left':
        if definition['outward'] != (-1, 0):
            raise ValueError('Reflected quarry portal must face source -X')
        # This exact source helper reverses each face AND its original UV
        # corner order after swapping X/Y. A quarter-turn is not equivalent.
        building_portal_side(g, *position, **options)
    elif transform == 'powerhouse-placement':
        if definition['outward'] != (0, -1):
            raise ValueError('Powerhouse portal must face source -Y')
        local=HYDRO_LEGACY_LOCAL_POSITION if legacy else definition['localPosition']
        offset=definition['translation']
        if tuple(a+b for a,b in zip(local,offset,strict=True))!=position:
            raise ValueError('Powerhouse door position differs from authored rigid placement')
        # Match the existing subassembly operation order. Native mesh points
        # enter Blender's float storage locally, before the rigid placement.
        building_portal(g,*local,**options)
        dx,dy,dz=offset
        g.vertices=[(x-dx,y-dy,z+dz) for x,y,z in g.vertices]
    else:
        raise ValueError('Unknown authored industrial door transform: '+transform)
    if not legacy:
        if model=='StoneCrusher':crusher_return_surfaces(g,position)
        elif definition['returnOwnership']=='kiln-shoulder-strips':kiln_return_strips(g,position)
    return g


def recipes(model):
    return {f'Door.{ident}': (lambda ident=ident, definition=definition:
            _door(model, ident, definition)) for ident, definition in DOORS[model].items()}


def recipe(model, component):
    return recipes(model)[component]()


def legacy_door(model, component):
    """Exact saved insert topology/placement for lossless one-time separation.

The producing helper has corrected inward-facing cavity returns. Their vertex
sets, face count and materials still match the old saved insert; the selective
rebuild replaces that component with the corrected winding.
    """
    if component not in recipes(model):raise ValueError('Unknown industrial legacy door: '+model+'/'+component)
    ident=component.removeprefix('Door.')
    return _door(model,ident,DOORS[model][ident],legacy=True)


def hydro_workshop_door():
    """The local asset before the existing downstream powerhouse placement."""
    return _door('ReinforcedHydroTurbine', 'HydroWorkshopDoor', HYDRO_WORKSHOP_DOOR)
