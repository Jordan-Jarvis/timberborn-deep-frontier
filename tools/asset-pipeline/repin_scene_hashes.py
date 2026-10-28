"""Replace recorded scene hashes after scenes were re-saved without content changes.

python tools/asset-pipeline/repin_scene_hashes.py <folder with the previous .blend files>

Registrations and review captures pin each source scene's SHA-256 (for example
"sourceSha256") so that an export is known to come from the reviewed scene.
unpack_blend_textures.py re-saves scenes compressed with their images
unpacked, which changes the file hash but not the scene (it verifies an
unchanged fingerprint before saving). This maps each tracked scene's previous
hash (from the given copy of the previous files, same relative paths) to its
current hash and replaces exactly those 64-character values in every tracked
text file. Scenes whose bytes are unchanged are skipped; a scene missing from
the previous folder is an error.
"""
import hashlib, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
previous = Path(sys.argv[1])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


tracked = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True).stdout.decode().split('\0')
mapping = {}
for rel in (t for t in tracked if t.endswith('.blend')):
    old_file = previous / rel
    if not old_file.is_file():
        raise SystemExit(f'No previous copy of {rel} in {previous}')
    old, new = sha(old_file), sha(ROOT / rel)
    if old != new:
        mapping[old] = new
print(f'{len(mapping)} scenes changed bytes')
changed = 0
for rel in tracked:
    path = ROOT / rel
    if not rel or path.suffix.lower() not in {'.json', '.py', '.mjs', '.js', '.md', '.csv', '.ps1', '.txt'} or not path.is_file():
        continue
    # Bytes, not text: the hashes are ASCII, and a few text files are not UTF-8.
    text = path.read_bytes()
    updated = text
    for old, new in mapping.items():
        if old.encode() in updated:
            updated = updated.replace(old.encode(), new.encode())
    if updated != text:
        path.write_bytes(updated)
        changed += 1
        print('repinned', rel)
print(f'{changed} files repinned')
