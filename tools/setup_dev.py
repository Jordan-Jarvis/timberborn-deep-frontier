"""Set up a Deep Frontier development checkout on Windows, macOS or Linux.

    python tools/setup_dev.py                       # find Timberborn in the Steam libraries
    python tools/setup_dev.py --game "D:/Games/Timberborn"   # or point at the install
    python tools/setup_dev.py --skip-extract        # paths and packages only

Steps:
1. Find the Timberborn install. Default Steam libraries are searched (and every
   library listed in Steam's libraryfolders.vdf); --game accepts the install
   folder, the data folder holding resources.assets, or Timberborn.app on macOS.
2. Record this machine's paths in tools/dev-environment.json (not tracked): the
   game, its Managed assemblies, the Workshop mods folder, the Timberborn
   documents folder, and Node, Python, PowerShell 7 and Blender.
   tools/compile-check/Directory.Build.props (not tracked) gets the same paths
   for the C# compile checks.
3. Install the tool packages: UnityPy into tools/asset-pipeline/unitypy and
   Node's sharp (package.json).
4. Clone Mechanistry's official modding project into vendor/timberborn-modding
   at the commit the build was verified with (Windows builds only).
5. Extract the local-only game references from your install into their
   git-ignored folders (game textures for the Blender scenes, vanilla icons,
   native material previews). They belong to Mechanistry and are never committed.
6. Install the pre-commit guard (tools/check_no_game_assets.py), which refuses
   commits that would add game assets.

Building and installing the mod itself (tools/build_deep_frontier.ps1, Unity's
official Mod Builder) is Windows-only; extraction, content generation and the
static checks work on every platform.
"""
import argparse, json, os, platform, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'tools' / 'dev-environment.json'
PROPS = ROOT / 'tools' / 'compile-check' / 'Directory.Build.props'
UNITYPY = ROOT / 'tools' / 'asset-pipeline' / 'unitypy'
UNITYPY_VERSION = '1.25.4'
MODDING_REPO = 'https://github.com/mechanistry/timberborn-modding.git'
MODDING_COMMIT = 'cc50d47'
UNITY_VERSION = '6000.5.11f1'  # matches the official modding project
APP_ID = '1062090'
SYSTEM = platform.system()  # 'Windows', 'Darwin', 'Linux'


def steam_roots():
    home = Path.home()
    roots = []
    if SYSTEM == 'Windows':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as key:
                roots.append(Path(winreg.QueryValueEx(key, 'SteamPath')[0]))
        except OSError:
            pass
        roots += [Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Steam',
                  Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Steam']
    elif SYSTEM == 'Darwin':
        roots.append(home / 'Library' / 'Application Support' / 'Steam')
    else:
        roots += [home / '.steam' / 'steam', home / '.local' / 'share' / 'Steam',
                  home / '.var' / 'app' / 'com.valvesoftware.Steam' / '.local' / 'share' / 'Steam']
    return [r for r in roots if r.is_dir()]


def steam_libraries():
    libraries = []
    for root in steam_roots():
        libraries.append(root)
        vdf = root / 'steamapps' / 'libraryfolders.vdf'
        if vdf.is_file():
            for path in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text(encoding='utf-8', errors='ignore')):
                libraries.append(Path(path.replace('\\\\', '\\')))
    unique = []
    for lib in libraries:
        if lib.is_dir() and lib.resolve() not in [u.resolve() for u in unique]:
            unique.append(lib)
    return unique


def resolve_game(path):
    """(install folder, data folder) for an install folder, a data folder or a macOS .app."""
    path = Path(path).expanduser()
    candidates = [(path.parent, path), (path, path / 'Timberborn_Data'),
                  (path, path / 'Timberborn.app' / 'Contents' / 'Resources' / 'Data'),
                  (path.parent, path / 'Contents' / 'Resources' / 'Data')]
    for install, data in candidates:
        if (data / 'resources.assets').is_file() and (data / 'Managed').is_dir():
            if data.name == 'Data' and data.parent.name == 'Resources':  # inside Timberborn.app
                install = data.parents[2].parent
            return install, data
    return None


def find_game(explicit):
    if explicit:
        found = resolve_game(explicit)
        if not found:
            raise SystemExit(f'No Timberborn install at {explicit}: expected resources.assets and Managed/ in it, '
                             'in its Timberborn_Data folder, or in Timberborn.app/Contents/Resources/Data.')
        return found
    for library in steam_libraries():
        found = resolve_game(library / 'steamapps' / 'common' / 'Timberborn')
        if found:
            return found
    raise SystemExit('Timberborn was not found in the Steam libraries. Run again with '
                     '--game <the Timberborn install folder>.')


def workshop_for(install):
    steamapps = install.parent.parent  # <library>/steamapps/common/Timberborn
    content = steamapps / 'workshop' / 'content' / APP_ID
    if content.is_dir():
        return content
    for library in steam_libraries():
        content = library / 'steamapps' / 'workshop' / 'content' / APP_ID
        if content.is_dir():
            return content
    return None


def documents_folder():
    if SYSTEM == 'Windows':
        import ctypes
        buf = ctypes.create_unicode_buffer(260)
        ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)  # CSIDL_PERSONAL: Documents
        return Path(buf.value) / 'Timberborn'
    return Path.home() / 'Documents' / 'Timberborn'


def find_tool(explicit, names, local=()):
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise SystemExit(f'Not a file: {explicit}')
        return str(path)
    for candidate in local:
        if candidate.is_file():
            return str(candidate)
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def run(command, **kwargs):
    print('  $ ' + ' '.join(str(c) for c in command), flush=True)
    subprocess.run([str(c) for c in command], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--game', help='Timberborn install folder, data folder, or Timberborn.app')
    parser.add_argument('--workshop', help='steamapps/workshop/content/1062090 (found next to the game by default)')
    parser.add_argument('--blender', help='Blender 4.5 executable (default: tools/asset-pipeline/blender-4.5.3, then PATH)')
    parser.add_argument('--node', help='Node.js executable (default: PATH)')
    parser.add_argument('--pwsh', help='PowerShell 7 executable (default: PATH)')
    parser.add_argument('--unity', help=f'Unity {UNITY_VERSION} editor executable (default: the Unity Hub install)')
    parser.add_argument('--skip-packages', action='store_true', help='do not install UnityPy or npm packages')
    parser.add_argument('--skip-unity-project', action='store_true', help='do not clone the official modding project')
    parser.add_argument('--skip-extract', action='store_true', help='do not extract game references')
    args = parser.parse_args()

    print('1. Timberborn')
    install, data = find_game(args.game)
    workshop = Path(args.workshop) if args.workshop else workshop_for(install)
    print(f'   install   {install}\n   data      {data}\n   workshop  {workshop or "not found (subscribe to the required mods)"}')

    print('2. Tools')
    exe = '.exe' if SYSTEM == 'Windows' else ''
    local_blender = ROOT / 'tools' / 'asset-pipeline' / 'blender-4.5.3' / f'blender{exe}'
    hub_unity = {'Windows': Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Unity' / 'Hub' / 'Editor' / UNITY_VERSION / 'Editor' / 'Unity.exe',
                 'Darwin': Path('/Applications/Unity/Hub/Editor') / UNITY_VERSION / 'Unity.app' / 'Contents' / 'MacOS' / 'Unity',
                 'Linux': Path.home() / 'Unity' / 'Hub' / 'Editor' / UNITY_VERSION / 'Editor' / 'Unity'}[SYSTEM]
    config = {
        'gameRoot': str(install), 'gameData': str(data), 'gameManaged': str(data / 'Managed'),
        'workshopContent': str(workshop) if workshop else '',
        'timberbornDocuments': str(documents_folder()),
        'python': sys.executable,
        'node': find_tool(args.node, ['node']),
        'pwsh': find_tool(args.pwsh, ['pwsh']),
        'blender': find_tool(args.blender, ['blender'], [local_blender]),
        'unity': find_tool(args.unity, [], [hub_unity]),
    }
    for key in ('python', 'node', 'pwsh', 'blender', 'unity'):
        print(f'   {key:9} {config[key] or "not found"}')
    CONFIG.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    managed_build = Path(config['timberbornDocuments']) / 'ModsBuild' / 'TimberbornModExamples_Data' / 'Managed'
    PROPS.write_text(f"""<Project>
  <!-- Written by tools/setup_dev.py for this machine; not tracked. -->
  <PropertyGroup>
    <TimberbornManaged>{config['gameManaged']}</TimberbornManaged>
    <ModsBuildManaged>{managed_build}</ModsBuildManaged>
    <Workshop>{config['workshopContent']}</Workshop>
  </PropertyGroup>
</Project>
""", encoding='utf-8')
    print(f'   wrote {CONFIG.relative_to(ROOT)} and {PROPS.relative_to(ROOT)}')

    print('3. Packages')
    if args.skip_packages:
        print('   skipped')
    else:
        if not any(UNITYPY.glob(f'unitypy-{UNITYPY_VERSION}.dist-info')):
            run([sys.executable, '-m', 'pip', 'install', '--target', UNITYPY, f'UnityPy=={UNITYPY_VERSION}'])
        else:
            print(f'   UnityPy {UNITYPY_VERSION} present')
        if (ROOT / 'node_modules' / 'sharp').exists():
            print('   sharp present')
        elif config['node']:
            npm = shutil.which('npm')
            if not npm:
                raise SystemExit('npm not found: install Node.js (with npm) and run setup again.')
            run([npm, 'install', '--no-audit', '--no-fund'], cwd=ROOT)
        else:
            print('   Node.js not found: install it for the content generators, then run setup again.')

    print('4. Official modding project')
    vendor = ROOT / 'vendor' / 'timberborn-modding'
    if args.skip_unity_project:
        print('   skipped')
    elif vendor.is_dir():
        print(f'   present at {vendor.relative_to(ROOT)}')
    elif SYSTEM != 'Windows':
        print('   skipped: the Unity mod build runs on Windows')
    else:
        run(['git', 'clone', MODDING_REPO, vendor])
        run(['git', '-C', vendor, 'checkout', MODDING_COMMIT])
    if not args.skip_unity_project and SYSTEM == 'Windows' and vendor.is_dir():
        if not config['unity']:
            print(f'   Unity {UNITY_VERSION} not found: install it with Unity Hub (or pass --unity), then run setup again.')
        else:
            if not (vendor / 'Library' / 'PackageCache').is_dir():
                # First open: Unity resolves the project's packages (Mono.Cecil for the bootstrap).
                run([config['unity'], '-batchmode', '-nographics', '-quit', '-projectPath', vendor,
                     '-logFile', ROOT / 'outputs' / 'unity_first_import.log'])
            if not any((vendor / 'Assets' / 'Plugins' / 'Timberborn').glob('Timberborn.*.dll')):
                # The official importer's step: the game's assemblies and modding archives, publicized.
                run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                     ROOT / 'tools' / 'bootstrap_unity_timberborn_assets.ps1'])
            else:
                print('   game assemblies imported (re-run tools/bootstrap_unity_timberborn_assets.ps1 after a game update)')

    print('5. Game references (local only)')
    if args.skip_extract:
        print('   skipped')
    else:
        for script in ('extract_game_textures.py', 'export_vanilla_icon_references.py',
                       'export_native_civic_materials.py', 'export_native_civic_inspection.py'):
            run([sys.executable, ROOT / 'tools' / 'asset-pipeline' / script], cwd=ROOT)

    print('6. Pre-commit guard')
    hooks = ROOT / '.git' / 'hooks'
    if hooks.is_dir():
        hook = hooks / 'pre-commit'
        hook.write_text(f'#!/bin/sh\nexec "{Path(sys.executable).as_posix()}" tools/check_no_game_assets.py --staged\n',
                        encoding='utf-8', newline='\n')
        hook.chmod(0o755)
        print(f'   installed {hook.relative_to(ROOT)}')
    else:
        print('   no .git folder: clone the repository with git to install the guard')
    print('Done.')


if __name__ == '__main__':
    main()
