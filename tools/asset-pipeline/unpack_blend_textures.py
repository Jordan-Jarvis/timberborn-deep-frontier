"""Unpack the images packed into Deep Frontier's .blend scenes and save them compressed.

blender --background --factory-startup --python tools/asset-pipeline/unpack_blend_textures.py -- <list file>

The list file names one .blend per line. For every packed image:

- Game textures (names "<path id>-<texture>.png", taken from Timberborn's
  resources.assets) go to src/DeepFrontier/Art/GameTextures/, which is not tracked:
  they belong to Mechanistry. tools/asset-pipeline/extract_game_textures.py
  recreates the folder from the installed game.
- Deep Frontier textures point at their tracked file when one with the same name
  and identical bytes exists (the asset bundle materials or Art/Textures/Reference);
  otherwise they are written to src/DeepFrontier/Art/Textures/Packed/.

Duplicate copies of one image (Blender's ".001" names, identical bytes) are
merged into one datablock, data without users is purged (Blender would not save it), and the scene is saved with
Blender's compression and no .blend1 backup. Before saving, a fingerprint of the
scene (mesh geometry, object transforms and material slots, material node links
and the image each texture node uses, by bytes) must equal the fingerprint taken
after loading; otherwise the file is left unsaved and the run fails.
"""
import bpy, hashlib, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GAME = os.path.join(ROOT, 'src', 'DeepFrontier', 'Art', 'GameTextures')
PACKED = os.path.join(ROOT, 'src', 'DeepFrontier', 'Art', 'Textures', 'Packed')
TRACKED = [os.path.join(ROOT, 'src', 'DeepFrontier', 'AssetBundles', 'Resources', 'Materials', 'DeepFrontierArt'),
           os.path.join(ROOT, 'src', 'DeepFrontier', 'Art', 'Textures', 'Reference')]
GAME_NAME = re.compile(r'^\d+-.+\.(png|jpg|jpeg|tga|exr)$', re.I)


def base_name(name):
    return re.sub(r'\.\d{3}$', '', name)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def image_bytes(img):
    """The bytes an image shows: packed data, or the file it points at."""
    if img.packed_file:
        return bytes(img.packed_file.data)
    path = bpy.path.abspath(img.filepath) if img.filepath else ''
    if path and os.path.isfile(path):
        return open(path, 'rb').read()
    return b''


def fingerprint():
    # Datablocks without users are left out: Blender never saves them, and the
    # orphan purge below removes them.
    h = hashlib.sha256()
    for m in sorted((m for m in bpy.data.meshes if m.users), key=lambda m: m.name):
        h.update(m.name.encode())
        co = [0.0] * (len(m.vertices) * 3); m.vertices.foreach_get('co', co)
        h.update(repr([round(c, 6) for c in co]).encode())
        idx = [0] * len(m.loops); m.loops.foreach_get('vertex_index', idx)
        h.update(repr(idx).encode())
        h.update(repr([(p.loop_start, p.loop_total, p.material_index) for p in m.polygons]).encode())
        h.update(repr([uv.name for uv in m.uv_layers]).encode())
    for o in sorted((o for o in bpy.data.objects if o.users), key=lambda o: o.name):
        h.update(o.name.encode()); h.update(repr([round(v, 6) for row in o.matrix_world for v in row]).encode())
        h.update(repr([s.material.name if s.material else None for s in o.material_slots]).encode())
        h.update((o.data.name if o.data else '').encode())
    image_hash = {img.name: sha(image_bytes(img)) for img in bpy.data.images if img.source == 'FILE'}
    for mat in sorted((m for m in bpy.data.materials if m.users), key=lambda m: m.name):
        h.update(mat.name.encode())
        if mat.node_tree:
            for n in sorted(mat.node_tree.nodes, key=lambda n: n.name):
                h.update(f'{n.name}|{n.bl_idname}'.encode())
                if n.bl_idname == 'ShaderNodeTexImage' and n.image:
                    h.update(image_hash.get(n.image.name, n.image.name).encode())
            for l in mat.node_tree.links:
                h.update(f'{l.from_node.name}.{l.from_socket.identifier}>{l.to_node.name}.{l.to_socket.identifier}'.encode())
    return h.hexdigest()


def target_for(base, data):
    if GAME_NAME.match(base):
        return os.path.join(GAME, base)
    for folder in TRACKED:
        path = os.path.join(folder, base)
        if os.path.isfile(path) and sha(open(path, 'rb').read()) == sha(data):
            return path
    return os.path.join(PACKED, base)


def process(path):
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    before = fingerprint()
    canonical = {}
    for img in list(bpy.data.images):
        if not img.packed_file:
            continue
        data = bytes(img.packed_file.data)
        base = base_name(img.name)
        key = (base, sha(data))
        if key in canonical:
            img.user_remap(canonical[key])
            bpy.data.images.remove(img)
            continue
        canonical[key] = img
        target = target_for(base, data)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if not os.path.isfile(target):
            with open(target, 'wb') as f:
                f.write(data)
        elif sha(open(target, 'rb').read()) != sha(data):
            raise RuntimeError(f'{target} exists with different bytes than {img.name} in {path}')
        img.filepath = bpy.path.relpath(target)
        img.unpack(method='USE_ORIGINAL')
        if img.packed_file:
            raise RuntimeError(f'{img.name} is still packed in {path}')
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    after = fingerprint()
    if after != before:
        raise RuntimeError(f'Scene changed while unpacking: {path}')
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_mainfile(filepath=path, compress=True, relative_remap=True)
    print(f'UNPACKED {path} images={len(canonical)}', flush=True)


args = sys.argv[sys.argv.index('--') + 1:]
files = [l.strip() for l in open(args[0], encoding='utf-8') if l.strip()]
for path in files:
    process(path)
print('UNPACK COMPLETE', len(files), flush=True)
