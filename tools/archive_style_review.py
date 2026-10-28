"""Save authored renders and an honest inventory of detailed art vs prototypes."""
import hashlib,json,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
models=['StoneCrusher','CementKiln','MineralQuarry','ConcreteMixer','ReinforcedHydroTurbine','MaterialsLaboratory',
        'Hospital','Restaurant','GroceryStore','FisheryWorks','FishHatchery','SandstonePit','LimestonePit',
        'SandstoneMasonryBlock','LimestoneMasonryBlock','ConcreteBlock','ReinforcedDamBlock','ConcreteOverflowDam','ConcreteOverhang8x1','ConcreteScaffold3x3']
out=root/'docs/art/reviews/2026-10-20-native-style';out.mkdir(parents=True,exist_ok=True)
report=[]
for name in models:
    image=root/f'outputs/reference-studies/{name}-front.png'
    blend=root/f'src/DeepFrontier/Art/Source/{name}-ReferenceStudy.blend'
    if not image.is_file() or not blend.is_file():raise FileNotFoundError(name)
    shutil.copyfile(image,out/image.name)
    report.append({'model':name,'render':image.name,'source':str(blend.relative_to(root)),
                   'sourceSha256':hashlib.sha256(blend.read_bytes()).hexdigest()})
shutil.copyfile(root/'outputs/reference-studies/NativeHousing-rail-reference.png',out/'DoubleLodge-native-rail-source.png')
targets=set(models)-{'MineralQuarry'}|{'SandstoneQuarry','LimestoneQuarry'}
buildings=[]
for p in sorted((root/'src/DeepFrontier/Data/Buildings').rglob('*.blueprint.json')):
    ident=p.parent.name
    blueprint=json.loads(p.read_text())
    if ident=='GathererFlag':
        if set(blueprint)!={'ShoreFishingSpec'}:raise ValueError('Gatherer flag is no longer a behavior-only patch')
        stage='Original vanilla gatherer flag; behavior-only patch, no custom building art'
    else:stage='Detailed source restyled; native validation tracked in STATUS' if ident in targets else 'Older prototype; full concept-art replacement still required'
    buildings.append({'id':ident,'path':str(p.relative_to(root)),
        'artStage':stage})
(out/'review.json').write_text(json.dumps({'scope':'Authored source renders; in-game screenshots recorded separately',
    'dependency':'Redic.NewStyles >= 0.1','railSource':'DoubleLodge.Folktails.Model',
    'renders':report,'buildingAudit':buildings},indent=2)+'\n')
lines=['# Native material and housing-rail review','',
       'Iron Teeth materials follow REDIC New Building Styles. Deck rails reuse the original Folktails Double Lodge posts and handrails, including UVs. These are Blender renders; native validation is recorded in STATUS.',
       '',f'{len(targets)} detailed building variants use the shared style pass. The remaining catalog entries below are older prototypes and are not presented as finished concept-quality buildings.','',
       '| Building | Isometric render |','| --- | --- |']
lines += [f'| {r["model"]} | [View]({r["render"]}) |' for r in report]
lines += ['','The Gatherer Flag retains original vanilla artwork; its mod file only adds shore fishing.','',
          '## Remaining prototype geometry','']+[f'- {b["id"]}' for b in buildings if b['artStage'].startswith('Older prototype')]
(out/'README.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'detailedBuildingVariants':len(targets),'sourceRenders':len(report),'catalogBuildings':len(buildings),'folder':str(out)}))
