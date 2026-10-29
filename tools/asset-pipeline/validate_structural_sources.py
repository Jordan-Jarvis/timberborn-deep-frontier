"""Check actual saved structural meshes, support surfaces and open passages."""
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from structural_layouts import SIZES, SIDE_PLATFORMS
from native_uv_contract import valid_native_uv

SCAFFOLD_SEAM_CROWN = .004
from structural_geometry import SIDE_SEAM_CROWN
from steel_structure_grid import CANTILEVERS, BRIDGES, cantilever_ident
from steel_structure_geometry import BRIDGE_DECK_TOP, BRIDGE_UNDERSIDE, CLEAR_BELOW_DECK
STEEL_ANCHORS = {cantilever_ident(n): a for n, a in CANTILEVERS.items()}

results = []
for ident, (w, h, height) in SIZES.items():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'src/DeepFrontier/Art/Source'/(ident+'-ReferenceStudy.blend')))
    meshes = [o for o in bpy.data.collections[ident+'.ReferenceStudy'].objects if o.type == 'MESH']
    vertices, faces = [], []
    uv_corners = 0
    for obj in meshes:
        assert obj.animation_data is None, (ident, 'Passive structure must be static')
        offset = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in face.vertices) for face in obj.data.polygons)
        assert len(obj.material_slots) == 32 and obj.data.uv_layers, ident
        for face in obj.data.polygons:
            if face.material_index not in (0, 1, 2, 3, 7, 27, 28, 29):
                continue
            for index in face.loop_indices:
                assert valid_native_uv(obj.material_slots[face.material_index].material.name,obj.data.uv_layers.active.data[index].uv), ident
                uv_corners += 1
    tree = BVHTree.FromPolygons(vertices, faces)
    # Scaffold decks carry embedded metal seams whose shallow raised crown
    # stands exactly 0.004 above the deck top (structural_geometry.py); it is
    # authored relief, not a support surface (the flush-support rays below
    # still require the deck top itself at the module height).
    side = ident in SIDE_PLATFORMS
    crown = SCAFFOLD_SEAM_CROWN if ident.startswith('ConcreteScaffold') else 0
    if side:
        # Concrete side platform: n x n deck on art layer 0..1 beside the
        # anchor cell (a, n); the cleat shoes rest on the anchor top at 1.0.
        # Deck seam crowns stand SIDE_SEAM_CROWN proud (structural_geometry.py).
        n = h-1
        crown = SIDE_SEAM_CROWN
        assert w == (n if n % 2 else n+1) and height == 2, ident
        a = n//2
        anchor = [v for v in vertices if -v.y > n+.001]
        assert anchor and all(-a-1-.001 <= v.x <= -a+.001 for v in anchor), (ident, 'Geometry outside the anchor column')
        assert min(v.z for v in anchor) > 1-.001, (ident, 'Geometry inside the anchor block')
        hit = tree.ray_cast(Vector((-a-.17, -n-.085, 1.5)), Vector((0, 0, -1)), 1)[0]
        assert hit is not None and abs(hit.z-1.07) < .001, (ident, 'Cleat shoe missing')
        under = tree.ray_cast(Vector((-a-.17, -n-.085, 1.034)), Vector((0, 0, -1)), 1)[0]
        assert under is not None and abs(under.z-1) < .001, (ident, 'Cleat shoe does not bear on the anchor top')
    # Steel bridges hang their floor system into the open cell below the span
    # (like the vanilla suspension bridge); everything else stays in its grid.
    bridge = ident in BRIDGES
    floor = BRIDGE_UNDERSIDE if bridge else 0
    assert vertices and all(-w-.001 <= v.x <= .001 and -h-.001 <= v.y <= .001
                            and floor-.001 <= v.z <= height+crown+.001 for v in vertices), (ident, 'Mesh leaves its module')
    if bridge:
        assert min(v.z for v in vertices) < floor+.001, (ident, 'Bridge floor system depth changed')
    support_samples = 0
    deck_top = BRIDGE_DECK_TOP if bridge else 1 if side else height
    # Stackable tops (and the bridge's walking deck, which is not stackable)
    # are flush at their exact height; on the bridge only the strip between
    # the trusses is sampled.
    for x in range(n if side else w):
        for y in range(n if side else h):
            for dx in ((.22, .35, .50, .65, .78) if bridge else (.10, .30, .50, .70, .90)):
                for dy in (.10, .30, .50, .70, .90):
                    hit = tree.ray_cast(Vector((-x-dx, -y-dy, deck_top+.1)), Vector((0,0,-1)), .2)[0]
                    assert hit is not None and abs(hit.z-deck_top) < max(crown, SCAFFOLD_SEAM_CROWN)+.001, (ident, x, y, 'Missing flush support')
                    support_samples += 1
    passage_samples = 0
    # (x, y, z0, clearance): upward rays from z0 must stay clear for `clearance`.
    rays = []
    if ident in STEEL_ANCHORS:
        # Open strip under every cantilever tile (not the anchors), below the
        # floor beams: the trusses stand at the side edges.
        rays = [(x, y+.5+dy, .01, CLEAR_BELOW_DECK-.01) for y in range(STEEL_ANCHORS[ident], h)
                for x in (.34, .5, .66) for dy in (-.3, 0, .3)]
    elif bridge:
        # Walking headroom between the trusses over the whole bridge.
        rays = [(x, y+dy, BRIDGE_DECK_TOP+.002, .95-BRIDGE_DECK_TOP) for y in range(h)
                for x in (.22, .35, .5, .65, .78) for dy in (.15, .5, .85)]
    elif ident.startswith('SteelColumnH'):
        # Every layer of the trestle is open through its middle below the ties.
        rays = [(.5+dx, .5+dy, k+.01, CLEAR_BELOW_DECK-.01) for k in range(height)
                for dx in (-.15, 0, .15) for dy in (-.15, 0, .15)]
    elif ident.startswith('SteelDeck'):
        # Open below every non-corner tile, under the girders and joists.
        rays = [(x+.5+dx, y+.5+dy, .01, CLEAR_BELOW_DECK-.01) for x in range(w) for y in range(h)
                if not ((x in (0, w-1)) and (y in (0, h-1))) for dx in (-.2, 0, .2) for dy in (-.2, 0, .2)]
    for x, y, z0, clearance in rays:
        hit = tree.ray_cast(Vector((-x, -y, z0)), Vector((0, 0, 1)), clearance)[0]
        assert hit is None, (ident, 'Obstruction in declared open passage', (x, y, z0), hit)
        passage_samples += 1
    if ident == 'ConcreteOverhang8x1':
        # Middle strip below the overhang, excluding its supported anchor.
        samples = [(x, y+.5, .78) for y in range(1, 8) for x in (.34, .5, .66)]
    elif ident.startswith('ConcreteScaffold'):
        # Every non-corner cell is clear for the full leg height, deliberately
        # outside the corner posts/braces; girders and joists stay above it.
        assert w == h and w in (3, 4, 5) and height-1 in (1, 2, 3), ident
        samples = [(x+.5+dx, y+.5+dy, height-1+.05) for x in range(w) for y in range(h)
                   if 0 < x < w-1 or 0 < y < h-1 for dx in (-.2, 0, .2) for dy in (-.2, 0, .2)]
    elif side:
        # Clear below 0.55 under every deck cell except the anchor-wall cell,
        # where the knee braces descend to the wall plate.
        samples = [(x+.5+dx, y+.5+dy, .55) for x in range(n) for y in range(n)
                   if (x, y) != (a, n-1) for dx in (-.2, 0, .2) for dy in (-.2, 0, .2)]
    else:
        samples = []
    for x, y, clearance in samples:
        hit = tree.ray_cast(Vector((-x,-y,.01)), Vector((0,0,1)), clearance-.01)[0]
        assert hit is None, (ident, 'Obstruction in declared open passage', hit)
        passage_samples += 1
    results.append(dict(model=ident, vertices=len(vertices), supportSamples=support_samples,
                        clearPassageSamples=passage_samples, nativeAtlasUvCorners=uv_corners))
report = dict(scope='Saved Blender geometry; native placement and traversal require separate tests', models=results)
target = ROOT/'outputs/structural-integration/source-checks.json'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
