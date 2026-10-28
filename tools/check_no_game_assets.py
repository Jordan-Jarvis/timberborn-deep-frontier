"""Refuse to commit Timberborn's own assets or other authors' files.

    python tools/check_no_game_assets.py            # every tracked file
    python tools/check_no_game_assets.py --staged   # files staged for commit (the pre-commit hook)

Deep Frontier's repository holds only its own work. Game textures, icons,
meshes, decompiled code, game or mod binaries and saved maps stay in the
git-ignored local folders that tools/setup_dev.py fills from your own install.
A path matching any rule below fails the check and names the rule.
"""
import re, subprocess, sys

RULES = [
    (r'(^|/)GameTextures/', 'game textures (src/DeepFrontier/Art/GameTextures, recreated by setup)'),
    (r'^outputs/(vanilla-icons|native-civic-assets|workforce-api[^/]*|map-objects)/', 'references extracted from the game'),
    # resources.assets path ids are 3+ digits (our own numbered art, "01-...", is 2)
    (r'(^|/)\d{3,}-[^/]+\.(png|jpe?g|tga|exr|dds)$', 'a game texture (name starts with its resources.assets path id)'),
    (r'\.decompiled\.cs$|(^|/)decompiled/', 'decompiled code'),
    (r'\.(dll|exe|pdb|so|dylib)$', 'a binary (game, mod or tool)'),
    (r'(^|/)resources\.assets$|\.assets$|\.resS$|\.resource$', 'Unity game data'),
    (r'\.timber$', 'a Timberborn save or map (derived from the game\'s maps)'),
    (r'(^|/)vendor/', 'vendored third-party projects'),
    (r'^docs/art/references/new-building-styles/', 'another mod\'s Workshop images'),
    (r'^tools/target_mod_packages_[^/]*\.json$', 'other mods\' blueprints'),
]


def files(staged):
    if staged:
        command = ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z']
    else:
        command = ['git', 'ls-files', '-z']
    out = subprocess.run(command, capture_output=True, check=True).stdout.decode('utf-8')
    return [f for f in out.split('\0') if f]


def main():
    staged = '--staged' in sys.argv[1:]
    problems = []
    for path in files(staged):
        for pattern, reason in RULES:
            if re.search(pattern, path, re.I):
                problems.append(f'  {path}: {reason}')
                break
    if problems:
        print('Refusing to commit game assets or other authors\' files:' if staged else 'Tracked files that must not be in the repository:')
        print('\n'.join(problems[:50]))
        if len(problems) > 50:
            print(f'  ... and {len(problems) - 50} more')
        print('Keep them in the git-ignored local folders (see README, "Local-only game references").')
        sys.exit(1)
    print(f'No game assets in {"the staged files" if staged else "the tracked files"}.')


if __name__ == '__main__':
    main()
