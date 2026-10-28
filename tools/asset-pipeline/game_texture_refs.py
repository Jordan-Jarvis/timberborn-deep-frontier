"""Game textures used by the .blend scenes: list them, or point the scenes at GameTextures.

blender --background --factory-startup --python tools/asset-pipeline/game_texture_refs.py -- scan <list> <manifest.json>
blender --background --factory-startup --python tools/asset-pipeline/game_texture_refs.py -- repoint <list>

Game textures are images named "<path id>-<texture>.<ext>", taken from Timberborn's
resources.assets. They live in src/DeepFrontier/Art/GameTextures/ (not tracked;
tools/asset-pipeline/extract_game_textures.py recreates it from the installed game).

scan     writes the sorted file names every listed scene uses to the manifest.
repoint  sets every game-texture image whose file is missing to GameTextures/<name>
         (which must exist) and saves the scene compressed; geometry, objects,
         materials and node links must be unchanged.
"""
import bpy, hashlib, json, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GAME = os.path.join(ROOT, 'src', 'DeepFrontier', 'Art', 'GameTextures')
GAME_NAME = re.compile(r'^\d+-.+\.(png|jpg|jpeg|tga|exr)$', re.I)


def game_file(img):
    name = os.path.basename(bpy.path.abspath(img.filepath)) if img.filepath else ''
    return name if img.source == 'FILE' and GAME_NAME.match(name) else None


def structure():
    h = hashlib.sha256()
    for m in sorted((m for m in bpy.data.meshes if m.users), key=lambda m: m.name):
        co = [0.0] * (len(m.vertices) * 3); m.vertices.foreach_get('co', co)
        h.update(m.name.encode()); h.update(repr([round(c, 6) for c in co]).encode())
        h.update(repr([(p.loop_start, p.loop_total, p.material_index) for p in m.polygons]).encode())
    for o in sorted((o for o in bpy.data.objects if o.users), key=lambda o: o.name):
        h.update(o.name.encode()); h.update(repr([round(v, 6) for row in o.matrix_world for v in row]).encode())
        h.update(repr([s.material.name if s.material else None for s in o.material_slots]).encode())
    for mat in sorted((m for m in bpy.data.materials if m.users), key=lambda m: m.name):
        h.update(mat.name.encode())
        if mat.node_tree:
            for n in sorted(mat.node_tree.nodes, key=lambda n: n.name):
                h.update(f'{n.name}|{n.bl_idname}|{n.image.name if getattr(n, "image", None) else ""}'.encode())
            for l in mat.node_tree.links:
                h.update(f'{l.from_node.name}.{l.from_socket.identifier}>{l.to_node.name}.{l.to_socket.identifier}'.encode())
    return h.hexdigest()


def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    mode, files = args[0], [l.strip() for l in open(args[1], encoding='utf-8') if l.strip()]
    needed = set()
    for path in files:
        bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
        names = {n for n in (game_file(i) for i in bpy.data.images if i.users) if n}
        needed |= names
        if mode == 'repoint':
            before, changed = structure(), 0
            for img in bpy.data.images:
                name = game_file(img)
                if not name or os.path.isfile(bpy.path.abspath(img.filepath)):
                    continue
                target = os.path.join(GAME, name)
                if not os.path.isfile(target):
                    raise RuntimeError(f'{name} is not in GameTextures; run extract_game_textures.py first ({path})')
                img.filepath = bpy.path.relpath(target)
                changed += 1
            if changed:
                if structure() != before:
                    raise RuntimeError(f'Scene changed while repointing: {path}')
                bpy.context.preferences.filepaths.save_version = 0
                bpy.ops.wm.save_mainfile(filepath=path, compress=True, relative_remap=True)
            print(f'REPOINTED {os.path.basename(path)} {changed}', flush=True)
    if mode == 'scan':
        json.dump(sorted(needed), open(args[2], 'w', encoding='utf-8'), indent=1)
        print(f'SCAN {len(needed)} game textures', flush=True)


if __name__ == '__main__':
    main()
