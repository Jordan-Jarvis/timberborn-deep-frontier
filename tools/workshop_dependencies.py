"""Set Deep Frontier's Steam Workshop "Required items" from manifest.json.

    python tools/workshop_dependencies.py            # show the plan, change nothing
    python tools/workshop_dependencies.py --apply    # add the missing required items on Steam

Timberborn's in-game uploader does not send RequiredMods to Steam, so subscribers
are not offered the required mods. This adds each one as a Workshop dependency of
the Deep Frontier item (ISteamUGC::AddDependency), which makes Steam list them under
Required items and offer to subscribe to them.

- Required mods: src/DeepFrontier/manifest.json RequiredMods. Each mod Id maps to
  the Workshop item whose manifest.json has that Id, among your subscribed items
  (the workshopContent folder in tools/dev-environment.json). Subscribe to every
  required mod first; a missing or ambiguous Id is an error.
- The Deep Frontier item: ItemId in Documents/Timberborn/Mods/DeepFrontier/
  workshop_data.json, which the game writes on the first upload, or --item.
- --apply talks to the running Steam client through the game's own Steam API
  library, as the signed-in user, who must own the item.
"""
import argparse, ctypes, glob, json, os, platform, sys, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import dev_environment  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
APP_ID = '1062090'
ADD_DEPENDENCY_RESULT = 3412  # AddUGCDependencyResult_t::k_iCallback (ISteamUGC callbacks 3400 + 12)
EResultOK = 1


def manifest(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def required_items(workshop):
    wanted = [m['Id'] for m in manifest(ROOT / 'src' / 'DeepFrontier' / 'manifest.json')['RequiredMods']]
    found, unreadable = {}, []
    for path in glob.glob(os.path.join(workshop, '*', '**', 'manifest.json'), recursive=True):
        item = Path(path).relative_to(workshop).parts[0]
        try:
            mod = manifest(path).get('Id')
        except json.JSONDecodeError:
            unreadable.append(path)  # other authors' manifests the game's lenient reader accepts
            continue
        found.setdefault(mod, set()).add(item)
    items, problems = [], []
    for mod in wanted:
        ids = sorted(found.get(mod, ()))
        if len(ids) != 1:
            problems.append(f'{mod}: {"not subscribed" if not ids else "several items " + ", ".join(ids)}')
        else:
            items.append((mod, int(ids[0])))
    if problems:
        raise SystemExit('Cannot map every required mod to a Workshop item:\n  ' + '\n  '.join(problems)
                         + ''.join(f'\n  (not strict JSON, not read: {p})' for p in unreadable))
    return items


def parent_item(args, dev):
    if args.item:
        return args.item
    data = Path(dev['timberbornDocuments']) / 'Mods' / 'DeepFrontier' / 'workshop_data.json'
    if not data.is_file():
        raise SystemExit(f'{data} is missing: upload Deep Frontier from the game once, or pass --item <id>.')
    content = json.loads(data.read_text(encoding='utf-8-sig'))
    if 'ItemId' not in content:
        raise SystemExit(f'{data} has no ItemId: {content}; pass --item <id>.')
    return int(content['ItemId'])


def steam_library(game_root):
    names = {'Windows': 'steam_api64.dll', 'Darwin': 'libsteam_api.dylib', 'Linux': 'libsteam_api.so'}[platform.system()]
    hits = sorted(glob.glob(os.path.join(game_root, '**', names), recursive=True))
    if not hits:
        raise SystemExit(f'{names} not found under {game_root}')
    return hits[0]


class AddDependencyResult(ctypes.Structure):
    # Steam packs callback structs to 8 bytes on Windows and 4 elsewhere.
    _pack_ = 8 if platform.system() == 'Windows' else 4
    _fields_ = [('result', ctypes.c_int32), ('parent', ctypes.c_uint64), ('child', ctypes.c_uint64)]


def add_dependencies(game_root, parent, items):
    os.environ['SteamAppId'] = APP_ID
    os.environ['SteamGameId'] = APP_ID
    api = ctypes.CDLL(steam_library(game_root))
    error = ctypes.create_string_buffer(1024)
    api.SteamAPI_InitFlat.argtypes = [ctypes.c_char_p]
    if api.SteamAPI_InitFlat(error) != 0:
        raise SystemExit(f'Steam API init failed: {error.value.decode(errors="replace")} (is Steam running and signed in?)')
    try:
        api.SteamAPI_SteamUGC_v021.restype = ctypes.c_void_p
        api.SteamAPI_SteamUtils_v010.restype = ctypes.c_void_p
        ugc, utils = api.SteamAPI_SteamUGC_v021(), api.SteamAPI_SteamUtils_v010()
        api.SteamAPI_ISteamUGC_AddDependency.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint64]
        api.SteamAPI_ISteamUGC_AddDependency.restype = ctypes.c_uint64
        api.SteamAPI_ISteamUtils_IsAPICallCompleted.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.POINTER(ctypes.c_bool)]
        api.SteamAPI_ISteamUtils_IsAPICallCompleted.restype = ctypes.c_bool
        api.SteamAPI_ISteamUtils_GetAPICallResult.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int,
                                                             ctypes.c_int, ctypes.POINTER(ctypes.c_bool)]
        api.SteamAPI_ISteamUtils_GetAPICallResult.restype = ctypes.c_bool
        failures = 0
        for mod, child in items:
            call = api.SteamAPI_ISteamUGC_AddDependency(ugc, parent, child)
            failed = ctypes.c_bool()
            deadline = time.time() + 30
            while not api.SteamAPI_ISteamUtils_IsAPICallCompleted(utils, call, ctypes.byref(failed)):
                if time.time() > deadline:
                    raise SystemExit(f'{mod}: Steam did not answer within 30 s')
                api.SteamAPI_RunCallbacks()
                time.sleep(0.1)
            result = AddDependencyResult()
            ok = api.SteamAPI_ISteamUtils_GetAPICallResult(utils, call, ctypes.byref(result), ctypes.sizeof(result),
                                                           ADD_DEPENDENCY_RESULT, ctypes.byref(failed))
            if not ok or failed.value or result.result != EResultOK:
                failures += 1
                print(f'  FAILED {mod} ({child}): EResult {result.result}')
            else:
                print(f'  added  {mod} ({child})')
        if failures:
            raise SystemExit(f'{failures} required item(s) were not added.')
    finally:
        api.SteamAPI_Shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--apply', action='store_true', help='add the dependencies on Steam (default: only show them)')
    parser.add_argument('--item', type=int, help='Deep Frontier Workshop item id (default: from workshop_data.json)')
    args = parser.parse_args()
    dev = {key: dev_environment.get(key) for key in ('gameRoot', 'workshopContent', 'timberbornDocuments')}
    items = required_items(dev['workshopContent'])
    parent = parent_item(args, dev) if args.apply or args.item else None
    print(f'Deep Frontier item: {parent or "(not uploaded yet)"}; {len(items)} required items:')
    for mod, child in items:
        print(f'  {mod:32} https://steamcommunity.com/sharedfiles/filedetails/?id={child}')
    if not args.apply:
        print('Dry run: pass --apply to add them on Steam.')
        return
    add_dependencies(dev['gameRoot'], parent, items)
    print(f'Done: https://steamcommunity.com/sharedfiles/filedetails/?id={parent} lists them under Required items.')


if __name__ == '__main__':
    main()
