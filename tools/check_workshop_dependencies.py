"""Compare the exact installed Workshop revisions with Valve's current metadata."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STEAM = Path('C:/Program Files (x86)/Steam/steamapps/workshop')
ENDPOINT = 'https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/'


def parse_vdf(text):
    tokens = re.findall(r'"([^"\r\n]*)"|([{}])', text)
    values = [a if not b else b for a, b in tokens]
    index = 0

    def object_value(nested):
        nonlocal index
        result = {}
        while index < len(values):
            key = values[index]
            index += 1
            if key == '}':
                if not nested:
                    raise ValueError('Unexpected closing VDF brace')
                return result
            if key == '{' or key in result or index == len(values):
                raise ValueError(f'Invalid VDF key: {key}')
            value = values[index]
            index += 1
            result[key] = object_value(True) if value == '{' else value
        if nested:
            raise ValueError('Unclosed VDF object')
        return result

    return object_value(False)


catalog = json.loads((ROOT / 'tools/installed_dependency_manifests_1_1.json').read_text(encoding='utf-8-sig'))
apis = json.loads((ROOT / 'tools/modding_api_audit_1_1.json').read_text(encoding='utf-8-sig'))
packages = {}
for item in catalog['packages']:
    directory = STEAM / 'content/1062090' / item['workshopId']
    if item['path'] != 'root':
        directory /= item['path']
    packages[item['workshopId']] = directory
for item in apis['packages']:
    directory = Path(item['packageDirectory'])
    if item['workshopId'] in packages and packages[item['workshopId']] != directory:
        raise ValueError(f"Conflicting directories for {item['workshopId']}")
    packages[item['workshopId']] = directory

body = {'itemcount': len(packages)}
for index, identifier in enumerate(packages):
    body[f'publishedfileids[{index}]'] = identifier
request = urllib.request.Request(ENDPOINT, data=urllib.parse.urlencode(body).encode('ascii'))
with urllib.request.urlopen(request, timeout=60) as response:
    remote = json.load(response)
if remote['response']['result'] != 1 or remote['response']['resultcount'] != len(packages):
    raise ValueError('Incomplete Steam response')
(ROOT / 'outputs/steam-workshop-current-details.json').write_text(json.dumps(remote, indent=2), encoding='utf-8')
details = {item['publishedfileid']: item for item in remote['response']['publishedfiledetails']}
acf_path = STEAM / 'appworkshop_1062090.acf'
acf_bytes = acf_path.read_bytes()
acf = parse_vdf(acf_bytes.decode('utf-8'))['AppWorkshop']
results = []
for identifier, directory in packages.items():
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8-sig'))
    server = details[identifier]
    if server['result'] != 1 or server['consumer_app_id'] != 1062090:
        raise ValueError(f'Invalid Workshop response for {identifier}')
    local = acf['WorkshopItemsInstalled'][identifier]
    results.append({
        'workshopId': identifier,
        'workshopUrl': f'https://steamcommunity.com/sharedfiles/filedetails/?id={identifier}',
        'name': manifest['Name'], 'id': manifest['Id'], 'version': manifest['Version'],
        'packageDirectory': str(directory),
        'installedManifest': local['manifest'],
        'installedUpdated': int(local['timeupdated']), 'currentUpdated': server['time_updated'],
        'installedBytes': int(local['size']), 'currentBytes': int(server['file_size']),
        'current': int(local['timeupdated']) == server['time_updated'] and int(local['size']) == int(server['file_size']),
        'manifestSha256': hashlib.sha256((directory / 'manifest.json').read_bytes()).hexdigest(),
    })
report = {
    'checkedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source': ENDPOINT, 'localSteamState': str(acf_path),
    'localSteamStateSha256': hashlib.sha256(acf_bytes).hexdigest(),
    'scope': 'Installed required dependencies and inspected supporting APIs. Matching Steam timestamps and sizes establish revision freshness, not runtime compatibility.',
    'steamNeedsUpdate': acf['NeedsUpdate'], 'steamNeedsDownload': acf['NeedsDownload'],
    'allCurrent': all(item['current'] for item in results), 'packages': results,
}
(ROOT / 'tools/dependency_freshness_1_1.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
for item in results:
    print(f"{'CURRENT' if item['current'] else 'DIFFERS'} {item['name']} {item['version']}")
if not report['allCurrent']:
    raise SystemExit('Workshop revisions differ. Update through Steam before building.')
print(f'All {len(results)} installed packages match current Steam revisions.')
