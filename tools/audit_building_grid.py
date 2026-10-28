"""Measure current authored door/grid and mechanical-face coverage. Never snap geometry."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
layouts={}
for name in ('industrial','civic','pit','hydro','research','structural'):
    layouts.update(json.loads((root/f'tools/{name}-layouts.json').read_text()))
reports=[]
for path in sorted((root/'src/DeepFrontier/Data/Buildings').rglob('*.blueprint.json')):
    b=json.loads(path.read_text())
    if 'TemplateSpec' not in b:
        continue
    ident=path.parent.name
    source='MineralQuarry' if ident in ('SandstoneQuarry','LimestoneQuarry') else ident
    entry={'building':ident,'size':b['BlockObjectSpec']['Size'],'source':source,
           'colliderCount':sum(len(n.get('CollidersSpec',{}).get('BoxColliders',[])) for n in b.get('Children',{}).values())}
    if source in layouts:
        d=layouts[source]
        entry['origin']=d['origin']
        visitor=root/f'outputs/reference-studies/{source}-visitor-manifest.json'
        access=root/f'outputs/reference-studies/{source}-access-manifest.json'
        if visitor.is_file():
            doors=json.loads(visitor.read_text())['doors']
        elif access.is_file() and 'doors' in json.loads(access.read_text()):
            doors=json.loads(access.read_text())['doors']
        else:
            doors=[]
        entry['doors']=[]
        for door in doors:
            if not {'id','position','outward'} <= set(door):
                entry['doors'].append({'authoringError':'Door manifest lacks explicit id/position/outward contract','raw':door})
                continue
            p=[a+b for a,b in zip(door['position'],d['origin'])]
            normal=door['outward']
            axis=0 if normal[0] else 1
            tangent=1-axis
            # Distance diagnostics only: no inferred replacement coordinates.
            centered=abs((p[tangent] % 1)-.5)
            edge=min(p[axis]%1,1-p[axis]%1)
            entry['doors'].append({'id':door['id'],'gridPosition':p,'outward':normal,
                'tileCenterOffset':centered,'faceBoundaryOffset':edge})
    sockets=b.get('TransputProviderSpec',{}).get('Transputs',[])
    entry['mechanicalSockets']=sockets
    entry['powerLayers']=sorted({s['Coordinates']['Z'] for s in sockets})
    entry['powered']=bool(b.get('MechanicalNodeSpec',{}).get('PowerInput',0) or b.get('MechanicalNodeSpec',{}).get('PowerOutput',0))
    reports.append(entry)
report={'scope':'Pre-correction authoring audit. Offset measurements are diagnostics, not replacement coordinates or native placement evidence.',
        'buildings':reports}
(root/'outputs/building-grid-audit-before.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([{'building':r['building'],'doors':r.get('doors',[]),'powerLayers':r['powerLayers']} for r in reports if r.get('doors')],indent=2))
