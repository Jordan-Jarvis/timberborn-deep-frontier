"""Record only complete exact-source exterior review renders and checks."""
import hashlib,json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
folder=ROOT/'docs/art/reviews/2026-10-21-exterior-repair'
source=ROOT/'src/DeepFrontier/Art/Source/Restaurant-ReferenceStudy.blend'
digest=hashlib.sha256(source.read_bytes()).hexdigest()
views=('front','front-right','rear','back-left','terrace-door','wall-junction')
logs=[(ROOT/'outputs'/name).read_text() for name in ('restaurant-shell-render.log','restaurant-shell-details.log')]
for log in logs:assert re.findall(r'SOURCE SCENE HASH PRESERVED ([a-f0-9]{64})',log)==[digest]
assert all('SAVED SCENE RENDERED Restaurant '+view in logs[0] for view in views[:4])
assert all('SAVED SCENE DETAIL RENDERED '+view in logs[1] for view in views[4:])
shell=json.loads((ROOT/'outputs/restaurant-shell-after.json').read_text())
surface=json.loads((ROOT/'outputs/zfight/Restaurant-frame1.json').read_text())
assert shell['sourceSha256']==digest and shell['failureCount']==0
assert surface['sourceSha256']==digest and surface['visibleConflicts']==0
names=[f'Restaurant-{view}.png' for view in views]
record={'model':'Restaurant','source':str(source.relative_to(ROOT)),
        'sourceSha256':digest,'images':names,
        'imageSha256':{name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in names}}
(folder/'review.json').write_text(json.dumps({'scope':'Blender source review only; native build/runtime verification is separate',
    'renders':[record],'shellProbeCount':shell['samples'],'uncoveredSamples':0,'visibleOverlapCandidates':0},indent=2)+'\n')
print('ARCHIVED RESTAURANT SHELL REVIEW',digest,shell['samples'],'samples, 6 images')
