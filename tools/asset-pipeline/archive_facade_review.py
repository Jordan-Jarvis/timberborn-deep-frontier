"""Archive only completed renders whose logged source hash still matches."""
import hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
folder=ROOT/'docs/art/reviews/2026-10-20-window-variety'
folder.mkdir(parents=True,exist_ok=True)
records=[]
logs={model:f'{model}-window-variety-review.log' for model in ('Restaurant','Hospital','GroceryStore','FisheryWorks')}
for model,log_name in logs.items():
    log=(ROOT/'outputs'/log_name).read_text(encoding='utf-8')
    source=ROOT/f'src/DeepFrontier/Art/Source/{model}-ReferenceStudy.blend'
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    assert re.findall(r'SOURCE SCENE HASH PRESERVED ([a-f0-9]{64})',log)==[digest],model+' source/render mismatch'
    images=[];image_hashes={}
    for view in ('front','front-right'):
        assert f'SAVED SCENE RENDERED {model} {view}\n' in log
        name=f'{model}-{view}.png';image=ROOT/'outputs/reference-studies'/name
        shutil.copyfile(image,folder/name);images.append(name)
        image_hashes[name]=hashlib.sha256(image.read_bytes()).hexdigest()
    records.append({'model':model,'source':str(source.relative_to(ROOT)),
                    'sourceSha256':digest,'images':images,'imageSha256':image_hashes})
for reference in ('NewStylesDistrict-facade-reference.png','Window-source-comparison.png'):
    shutil.copyfile(ROOT/'outputs/reference-studies'/reference,folder/reference)
review={'scope':'Blender source review only; not installed or runtime verified','renders':records,
        'windowSource':'Redic.NewStyles 0.1 District Center, Flat and Foodplant; four original window assemblies with exact UVs',
        'doorSource':'Native Large Barrack inside closed 1x1 insert'}
(folder/'review.json').write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8')
print('Archived eight matching civic isometric renders and the original window source comparisons.')
