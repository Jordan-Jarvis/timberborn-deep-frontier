"""Join unreferenced static meshes before the official Timbermesh export.

Why: the official exporter (ExportSettings merge_meshes=False, as every Deep
Frontier exporter calls it) writes one node per Blender object, and Timberborn
1.1.2.8 StaticMeshBuilder gives every node with vertices its own MeshRenderer,
one material slot per used material. While a building is a placement preview,
native PreviewPlacer.ShowPreviews runs every frame and, through
PreviewShower/Highlighter.UnhighlightAllPrimary + HighlightPrimary, calls
HighlightableObject.UpdateColorAndHighlight twice: MaterialColorer walks every
MeshRenderer (GetComponentsInChildren(includeInactive: true), so the inactive
construction-stage copy too) and every material slot, and
HighlightRenderingService rewrites every renderer's renderingLayerMask.
Vanilla Iron Teeth buildings carry 1-26 renderers; the civic exports carried
up to 333. Joining static parts keeps the triangles, materials, UVs and
normals and only removes renderer and slot overhead.

What stays a node of its own (never joined):
- '#' roots: animated parts, '#Slot#' empties, support templates. The
  official exporter already makes them independent nodes.
- Every object whose name a runtime spec, generator, Script or export
  validator can reference (referenced_names): grocery stock stages,
  reservoir flow nodes, rocket nodes, seats... Their whole subtrees stay
  too, because toggling or moving them must keep moving their children.
- Walkway rails and joins: opening_groups/join_groups join the parts that
  every opening toggles together into one node per group
  (WalkwayGroup.<ident>.<n>), and remap_openings points the walkway/deck
  spec at those nodes.
- Objects flagged 'liquid_surface' (preview water planes, native Water).
- Window and lamp glass (LIGHTING_MATERIALS): faces of those materials are
  joined into one node per material, never into the opaque node, so native
  night lighting (MaterialLightingRenderers / SetShaderUserValue, which acts
  per MeshRenderer) can address them separately.

Everything else that is static (no action on itself or an ancestor) joins
into STATIC_NODE (opaque materials) plus one STATIC_NODE.<material> node per
lighting material, all direct children of the grid-origin root with an
identity local transform. Evaluated corner normals are frozen as custom
normals first, so splitting faces by material cannot re-average smooth
normals across a material boundary.

Invalid inputs fail: more than one UV layer, differing UV layer names, colour
attributes (the joined mesh would zero-fill them), negative-scale objects,
or names that already exist.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

STATIC_NODE = 'StaticMerged'

# Glass/light materials kept out of the opaque node. WindowsAtlas.IronTeeth is
# the only palette material whose shipped Material carries a _LightingMap
# (installed 1.1.2.8 resources.assets; the others are BadwaterSource,
# UnstableCore and WindowsAtlas.Folktails). DFIndustrial08 (ReferenceWarmLight,
# lamp glass) and DFIndustrial09 (ReferenceWindow, window glass) are the custom
# glass tiles of the 27-slot catalog
# (src/DeepFrontier/AssetBundles/Resources/Materials/DeepFrontierIndustrial/material-catalog.json).
LIGHTING_MATERIALS = frozenset({'WindowsAtlas.IronTeeth', 'DFIndustrial08', 'DFIndustrial09'})

# Node names built in code rather than written as literals: GroceryStockDisplay.cs
# (Prefix "GroceryStock.") and validate_grocery_exports.py.
PRESERVED_PREFIXES = ('GroceryStock.',)

_LITERAL = re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'')


def _json_strings(value, found):
    if isinstance(value, str):
        found.add(value)
    elif isinstance(value, dict):
        for k, v in value.items():
            found.add(k)
            _json_strings(v, found)
    elif isinstance(value, list):
        for v in value:
            _json_strings(v, found)


def referenced_names(extra=()):
    """Every string a blueprint, integration record, generator, Script or
    export validator holds. Over-preserving only keeps a node separate."""
    found = set(extra)
    # Runtime names reach the game through blueprints (Data, and the
    # integration records generators promote into Data) or through code.
    # Export inputs such as rail manifests are not references.
    json_roots = [ROOT / 'src/DeepFrontier/Data', *sorted((ROOT / 'outputs').glob('*-integration'))]
    for folder in json_roots:
        for path in folder.rglob('*.json'):
            # This module's own provenance lists the joined parts, and the
            # walkway/deck specs are rewritten by the exporter from the
            # openings it passes in (stale ones from an older deck mode
            # would only hold parts no opening toggles any more).
            if path.name.endswith(('-static-merge.json', '-walkway.json', '-platform-deck.json')):
                continue
            _json_strings(json.loads(path.read_text(encoding='utf-8-sig')), found)
    code = [*(ROOT / 'tools').glob('*.mjs'), *(ROOT / 'src/DeepFrontier/Scripts').rglob('*.cs'),
            *(ROOT / 'tools/asset-pipeline').glob('validate_*_exports.py')]
    for path in code:
        for a, b in _LITERAL.findall(path.read_text(encoding='utf-8-sig')):
            found.add(a or b)
    return found


def _animated(obj):
    while obj is not None:
        if obj.animation_data and obj.animation_data.action:
            return True
        obj = obj.parent
    return False


def _held(obj, root, keep):
    """True when obj or an ancestor below the root must stay its own node."""
    while obj is not None and obj != root:
        if obj.name.startswith('#') or obj.name in keep or obj.name.startswith(PRESERVED_PREFIXES) \
                or 'liquid_surface' in obj or 'native_resource' in obj:
            return True
        obj = obj.parent
    return False


def _subtree(obj):
    yield obj
    for child in obj.children:
        yield from _subtree(child)


def _candidates(collection, root, keep):
    members = set(collection.all_objects)
    joinable = []
    for obj in collection.all_objects:
        if obj == root or _held(obj, root, keep) or _animated(obj):
            continue
        # Only whole static subtrees join: a parent whose child must stay
        # would leave the child behind without its transform owner.
        subtree = list(_subtree(obj))
        if any(o not in members or _held(o, root, keep) or _animated(o)
               or o.type not in ('MESH', 'EMPTY') for o in subtree):
            continue
        if obj.type == 'MESH' and len(obj.data.polygons):
            joinable.append(obj)
    return joinable


def _check(obj, mesh):
    if len(mesh.uv_layers) != 1:
        raise ValueError(f'{obj.name}: static join needs exactly one UV layer, found {len(mesh.uv_layers)}')
    if len(mesh.color_attributes):
        raise ValueError(f'{obj.name}: colour attributes would be zero-filled by the join')
    if obj.matrix_world.determinant() <= 0:
        raise ValueError(f'{obj.name}: negative-scale object cannot be joined without flipping its faces')
    if any(slot.material is None for slot in obj.material_slots):
        raise ValueError(f'{obj.name}: empty material slot')


def _triangles(mesh):
    """Triangles per material name, as the exporter's loop triangles count them."""
    mesh.calc_loop_triangles()
    counts = {}
    for triangle in mesh.loop_triangles:
        name = mesh.materials[triangle.material_index].name
        counts[name] = counts.get(name, 0) + 1
    return counts


def _split(mesh, name, groups):
    """One mesh per material group; groups maps key -> set of material indices."""
    import bmesh
    import bpy
    parts = {}
    for key, indices in groups.items():
        part = mesh.copy()
        part.name = f'{name}.{key or "Opaque"}'
        bm = bmesh.new()
        bm.from_mesh(part)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index not in indices], context='FACES')
        bm.to_mesh(part)
        bm.free()
        if len(part.polygons):
            parts[key] = part
        else:
            bpy.data.meshes.remove(part)
    bpy.data.meshes.remove(mesh)
    return parts


def _join(collection, root, objects, base):
    """Join objects into base (opaque materials) and base.<material> per
    lighting material, each a direct child of root with identity local
    transform. Removes the sources; returns the node records."""
    import bpy
    from mathutils import Matrix
    for name in [base] + [f'{base}.{m}' for m in LIGHTING_MATERIALS]:
        if name in bpy.data.objects:
            raise ValueError(f'Merged node name already used: {name}')
    depsgraph = bpy.context.evaluated_depsgraph_get()
    # The exporter's own mesh source (node_builder/blender_utils.create_mesh):
    # the evaluated object, modifiers applied.
    evaluated = {obj: bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph)) for obj in objects}
    for obj, mesh in evaluated.items():
        _check(obj, mesh)
    uv_names = {mesh.uv_layers[0].name for mesh in evaluated.values()}
    if len(uv_names) != 1:
        raise ValueError(f'{base}: joined parts need one UV layer name, found {sorted(uv_names)}')
    pieces = {}
    expected = {}
    for obj, mesh in evaluated.items():
        # Mesh.materials.clear() resets every face to slot 0; assign in place.
        for index, slot in enumerate(obj.material_slots):
            if index < len(mesh.materials):
                mesh.materials[index] = slot.material
            else:
                mesh.materials.append(slot.material)
        if len(mesh.materials) != len(obj.material_slots):
            raise ValueError(f'{obj.name}: evaluated mesh has {len(mesh.materials)} slots, object {len(obj.material_slots)}')
        for key, count in _triangles(mesh).items():
            node = base if key not in LIGHTING_MATERIALS else f'{base}.{key}'
            expected.setdefault(node, {}).setdefault(key, 0)
            expected[node][key] += count
        mesh.normals_split_custom_set([tuple(n.vector) for n in mesh.corner_normals])
        groups = {}
        for index, material in enumerate(mesh.materials):
            key = material.name if material.name in LIGHTING_MATERIALS else None
            groups.setdefault(key, set()).add(index)
        for key, part in _split(mesh, obj.name, groups).items():
            temp = bpy.data.objects.new(part.name, part)
            collection.objects.link(temp)
            temp.matrix_world = obj.matrix_world.copy()
            pieces.setdefault(key, []).append(temp)
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    nodes = []
    for key in sorted(pieces, key=lambda k: (k is not None, k or '')):
        name = base if key is None else f'{base}.{key}'
        target = bpy.data.objects.new(name, bpy.data.meshes.new(name))
        collection.objects.link(target)
        target.parent = root
        target.matrix_parent_inverse = Matrix.Identity(4)
        target.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()
        temps = [t.name for t in pieces[key]]
        selection = [target] + pieces[key]
        with bpy.context.temp_override(active_object=target, object=target,
                                       selected_objects=selection, selected_editable_objects=selection):
            result = bpy.ops.object.join()
        if result != {'FINISHED'} or any(t in bpy.data.objects for t in temps):
            raise RuntimeError(f'Join of {name} did not finish: {result}')
        actual = _triangles(target.data)
        if actual != expected[name]:
            raise RuntimeError(f'{name}: joined triangles per material {actual} differ from the parts {expected[name]}')
        nodes.append({'node': name, 'parts': len(temps), 'triangles': sum(actual.values()), 'materials': actual})
    return nodes


def join_groups(collection, root, groups):
    """Join each named group of static objects ({node name: [object names]},
    two or more each) into one node per group (plus a node per lighting
    material it holds). Returns {group name: [exported node names]}."""
    import bpy
    result = {}
    for name, members in sorted(groups.items()):
        if len(members) < 2:
            raise ValueError(f'{name}: a joined group needs at least two parts')
        objects = [bpy.data.objects[m] for m in members]
        for obj in objects:
            if obj.type != 'MESH' or obj.children or _animated(obj) or obj.name.startswith('#'):
                raise ValueError(f'{name}: {obj.name} is not a static leaf mesh')
        result[name] = [n['node'] for n in _join(collection, root, objects, name)]
    return result


def merge_static_meshes(collection, root, keep):
    """Join the static, unreferenced meshes of collection (children of root).
    Returns a provenance record. Call after every rename, slot and '#' prefix
    is final, immediately before Exporter.export_collection. Fewer than two
    joinable objects leave the scene as it is: nothing would be saved."""
    joinable = _candidates(collection, root, keep)
    names = sorted(o.name for o in joinable)
    if len(joinable) < 2:
        return {'joinedObjects': 0, 'objects': [], 'nodes': []}
    return {'joinedObjects': len(names), 'objects': names, 'nodes': _join(collection, root, joinable, STATIC_NODE)}


def opening_groups(openings, prefix):
    """Rail and join parts that every opening hides or shows together.
    BuildingWalkway/PlatformDeck set each named node from the openings that
    list it, so parts listed by exactly the same (opening, list) pairs always
    share one state and can be one node. Returns ({group: [parts]} for groups
    of two or more, {part: group})."""
    signatures = {}
    for opening in openings:
        for kind in ('HiddenNodes', 'ShownNodes'):
            for name in opening[kind]:
                signatures.setdefault(name, set()).add((opening['Id'], kind))
    together = {}
    for name, signature in signatures.items():
        together.setdefault(frozenset(signature), []).append(name)
    groups, remap = {}, {}
    for i, members in enumerate(sorted(sorted(m) for m in together.values() if len(m) > 1)):
        group = f'{prefix}.{i:03d}'
        groups[group] = members
        remap.update({m: group for m in members})
    return groups, remap


def remap_openings(openings, remap, joined):
    """Point each opening at the joined nodes instead of their parts."""
    for opening in openings:
        for kind in ('HiddenNodes', 'ShownNodes'):
            opening[kind] = sorted({node for name in opening[kind]
                                    for node in (joined[remap[name]] if name in remap else [name])})
