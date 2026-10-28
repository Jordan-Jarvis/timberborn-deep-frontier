"""Capture the explicitly requested seating correction, separate from prior art approval."""
import hashlib
import json
import shutil
from pathlib import Path

root=Path(__file__).resolve().parents[2]
folder=root/'docs/art/reviews/2026-10-19-restaurant-seating'
folder.mkdir(parents=True,exist_ok=True)
scene='src/DeepFrontier/Art/Source/Restaurant-ReferenceStudy.blend'
previous=json.loads((root/'docs/art/reviews/2026-10-19-civic/review-manifest.json').read_text())
base=next(m for m in previous['models'] if m['model']=='Restaurant')
for view in ('front','front-right'):
    shutil.copyfile(root/f'outputs/reference-studies/Restaurant-{view}.png',folder/f'Restaurant-{view}.png')
manifest={'status':'Source seating correction; in-game seated character verification required',
          'scene':scene,'sceneSha256':hashlib.sha256((root/scene).read_bytes()).hexdigest(),
          'previousReview':'docs/art/reviews/2026-10-19-civic/review-manifest.json',
          'previousSceneSha256':base['sceneSha256'],
          'changes':['Seat markers at chair surfaces','Front chairs face across the balcony','More table clearance','Tabletop lowered to 0.58 above deck','Animated sign outside the front deck with extended brackets'],
          'preserved':['Building envelope','Doors','Roof terraces','Native materials','Native plants','Gallery route centerlines']}
(folder/'review-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('Recorded source seating revision; no claim of runtime acceptance.')
