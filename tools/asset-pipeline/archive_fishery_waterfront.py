"""Archive the reviewed waterfront source and its exact evidence, not approval."""
import json,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'outputs/reference-studies'
dest=ROOT/'docs/art/reviews/2026-10-19-fishery-waterfront'
scene=ROOT/'src/DeepFrontier/Art/Source/FisheryWorks-ReferenceStudy.blend'
concept=ROOT/'docs/art/concepts/Fishery.png'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names=[f'FisheryWorks-{v}.png' for v in ('front','front-right','rear')]
names += [f'FisheryWorks-{v}.json' for v in ('study','access-manifest','height-manifest','native-assembly','rail-manifest','terrace-manifest','visitor-manifest','clearance-check','geometry-check')]
dest.mkdir(parents=True,exist_ok=True)
for name in names:shutil.copy2(source/name,dest/name)
route=ROOT/'outputs/fishery-reference-redesign/game-route-clearance.json'
if json.loads(route.read_text())['failures']:raise ValueError('Unresolved game-route clearance failures')
shutil.copy2(route,dest/route.name)
manifest={'scope':'Source review and clearance evidence; native integration verification is separate. User approval is not implied.',
 'scene':scene.relative_to(ROOT).as_posix(),'sceneSha256':sha(scene),
 'concept':concept.relative_to(ROOT).as_posix(),'conceptSha256':sha(concept),
 'referenceViews':'Only the isometric reference views. Printed tile counts and top views excluded.',
 'registration':[12,10,7],'doorLevels':[0,2],
 'files':[{'path':n,'sha256':sha(dest/n)} for n in names+[route.name]]}
(dest/'review-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
(dest/'README.md').write_text('''# Waterfront Fishery source review

Rebuilt from the individual [Fishery isometric reference](../../concepts/Fishery.png) after the user requested different floor and roof proportions from the Hospital/Restaurant. The top views and printed footprint counts were excluded.

The two-storey processing hall has a broad low roof, an offset entrance, a single-storey warehouse with a working roof deck, net frames, fish preparation stations, pipes, a hoist and the original native Iron Teeth wheel, tanks and materials. Three doors connect through the intended interior at ground/layer 2. Deck construction and separately placed vanilla stairs are part of the game contract.

![Front-left Blender review](FisheryWorks-front.png)

![Wheel-side Blender review](FisheryWorks-front-right.png)

![Rear Blender review](FisheryWorks-rear.png)

The manifest pins the source scene, reference and evidence. Source clearance and loop checks establish authoring consistency only. See [native verification](native-verification.md) and `tools/STATUS.md` for the separately verified installed build and gameplay results.
''',encoding='utf-8')
print('Archived waterfront Fishery scene evidence:',len(manifest['files']),'files')
