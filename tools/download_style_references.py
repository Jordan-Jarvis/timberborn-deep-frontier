"""Preserve the user-selected Workshop's public preview art for visual review."""
import json, hashlib, urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
root=Path(__file__).resolve().parents[1]
out=root/'docs/art/references/new-building-styles'
urls=json.loads((out/'image-urls.json').read_text(encoding='utf-8-sig'))
def download(pair):
    i,url=pair
    display_url=url+'?imw=637&imh=358&ima=fit&impolicy=Letterbox&imcolor=%23000000&letterbox=true'
    data=urllib.request.urlopen(display_url,timeout=60).read()
    path=out/f'preview-{i:02}.jpg'
    path.write_bytes(data)
    return {'file':path.name,'source':display_url,'sha256':hashlib.sha256(data).hexdigest()}
with ThreadPoolExecutor(max_workers=4) as pool:
    rows=list(pool.map(download,enumerate(urls)))
(out/'provenance.json').write_text(json.dumps({'workshop':'https://steamcommunity.com/sharedfiles/filedetails/?id=3723883597','title':'New Building Styles [ModContest1]','author':'REDIC','purpose':'User-selected visual reference only; these images are not shipped mod assets.','previews':rows},indent=2),encoding='utf-8')
print(json.dumps({'downloaded':len(rows),'directory':str(out)}))
