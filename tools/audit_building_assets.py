"""Exact catalog coverage and mirror readiness; missing evidence is never a pass."""
import argparse, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--require-mirroring',action='store_true')
args=parser.parse_args()
catalog=json.loads((ROOT/'tools/building_asset_catalog.json').read_text(encoding='utf-8'))
assert catalog['schema']==1
rows=catalog['buildings']
assert len({r['template'] for r in rows})==len(rows),'Duplicate catalog templates'
actual={}
for path in (ROOT/'src/DeepFrontier/Data/Buildings').rglob('*.blueprint.json'):
    b=json.loads(path.read_text(encoding='utf-8'))
    if 'TemplateSpec' in b:actual[b['TemplateSpec']['TemplateName']]=path
assert set(actual)=={r['template'] for r in rows},'Active building catalog changed; register its explicit asset owner'
VANILLA=ROOT/'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources'
vanilla_models=set()
for vp in VANILLA.rglob('*.blueprint.json'):
    t=vp.read_text(encoding='utf-8',errors='ignore')
    if '"Model"' in t:
        import re
        vanilla_models.update(re.findall(r'"Model"\s*:\s*"([^"]+)"',t))
reports=[]
for row in rows:
    for key in ('sourceScene','geometry','generator','exporter','blueprint'):
        assert (ROOT/row[key]).is_file(),(row['building'],key,row[key])
    path=ROOT/row['blueprint'];b=json.loads(path.read_text(encoding='utf-8'))
    assert actual[row['template']]==path
    mirror=b['BlockObjectSpec']['Flippable']
    if args.require_mirroring:assert mirror is True,'Native F mirroring disabled: '+row['building']
    if row['artStage']=='placeholder':
        # Integrated logic with a vanilla stand-in model until its own art is
        # exported: the model must be one a vanilla blueprint names (or none,
        # for dev tools without a finished model).
        mesh=b.get('Children',{}).get('#Finished',{}).get('TimbermeshSpec',{}).get('Model')
        if mesh is not None:
            assert mesh in vanilla_models,(row['building'],'placeholder model is not a vanilla resource',mesh)
        reports.append({**row,'placeholderModel':mesh,'flippable':mirror,'size':b['BlockObjectSpec']['Size'],
            'verification':'Placeholder art: vanilla stand-in model; own art pending'})
        continue
    mesh=b['Children']['#Finished']['TimbermeshSpec']['Model']
    payload=ROOT/'src/DeepFrontier/Data'/(mesh+'.timbermesh')
    assert payload.is_file(),payload
    reports.append({**row,'sourceSha256':hashlib.sha256((ROOT/row['sourceScene']).read_bytes()).hexdigest(),
        'export':payload.relative_to(ROOT).as_posix(),'exportSha256':hashlib.sha256(payload.read_bytes()).hexdigest(),
        'flippable':mirror,'size':b['BlockObjectSpec']['Size'],
        'verification':'Prototype component closure is not whole-building visual/grid acceptance' if row['artStage']=='prototype'
                       else 'Source coverage, overlap, exported geometry and native interaction need separate evidence'})
report={'scope':'Exact ownership and authored mirror flags. This does not certify visual appearance or native mirrored operation.',
    'buildingCount':len(reports),'detailedTemplates':sum(r['artStage']=='detailed' for r in reports),
    'prototypeTemplates':sum(r['artStage']=='prototype' for r in reports),
    'placeholderTemplates':sum(r['artStage']=='placeholder' for r in reports),
    'flippableTemplates':sum(r['flippable'] for r in reports),'buildings':reports}
(ROOT/'outputs/building-asset-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='buildings'}))
