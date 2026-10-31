"""Summarize exact current source audits; reject stale or missing reports."""
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MODELS=('StoneCrusher','CementKiln','MineralQuarry','ConcreteMixer','ReinforcedHydroTurbine',
        'MaterialsLaboratory','Hospital','Restaurant','GroceryStore','FisheryWorks','FishHatchery',
        'SandstonePit','LimestonePit','SandstoneMasonryBlock','BrickMasonryBlock',
        'ConcreteBlock','ConcreteOverhang8x1','ConcreteScaffold3x3','ReinforcedDamBlock','ConcreteOverflowDam',
        'ConcreteScaffold3x3H1','ConcreteScaffold3x3H2','ConcreteScaffold4x4H1','ConcreteScaffold4x4H2',
        'ConcreteScaffold4x4H3','ConcreteScaffold5x5H1','ConcreteScaffold5x5H2','ConcreteScaffold5x5H3')
folder=ROOT/'outputs/zfight'
detector_hash=hashlib.sha256((Path(__file__).with_name('zfight_audit.py')).read_bytes()).hexdigest()
rows=[]
for model in MODELS:
    report=json.loads((folder/f'{model}-frame1.json').read_text(encoding='utf-8'))
    assert report['model']==model and report['frame']==1
    assert report['detectorSha256']==detector_hash,'Stale detector: '+model
    assert report['sourceSha256']==hashlib.sha256((ROOT/report['sourceScene']).read_bytes()).hexdigest(),'Stale source: '+model
    rows.append({key:report[key] for key in ('model','sourceScene','sourceSha256','triangles','visibleConflicts','occludedConflicts')})
result={'scope':'Current source scenes, evaluated at frame one. Geometric candidates only; not GPU/native gameplay verification.',
        'models':len(rows),'visibleConflicts':sum(row['visibleConflicts'] for row in rows),
        'detectorSha256':detector_hash,'reports':rows}
(folder/'index.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
lines=['# Current building surface audits','',result['scope'],'',
       '| Model | Evaluated triangles | Visible overlap candidates | Occluded pairs |',
       '| --- | ---: | ---: | ---: |']
for row in rows:lines.append(f'| [{row["model"]}]({row["model"]}-frame1.md) | {row["triangles"]:,} | {row["visibleConflicts"]} | {row["occludedConflicts"]} |')
lines+=['','All listed source and detector hashes were checked when generating this index. Pair counts are not distinct defects.',
        'The strict export gate reruns the detector. Animation poses, neighboring objects and native shaders require separate checks.']
(folder/'index.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({key:value for key,value in result.items() if key!='reports'}))
