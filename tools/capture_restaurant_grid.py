"""Archive completed native platform/restaurant tests with saved entity evidence."""
import argparse,hashlib,json,re,shutil,zipfile
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--build',type=int,required=True)
parser.add_argument('--reload',action='store_true')
parser.add_argument('--baseline-build',type=int,help='Required for reload: exact build that created the main verified save')
args=parser.parse_args()
if args.reload and args.baseline_build is None:parser.error('--reload requires an explicit --baseline-build')
if not args.reload and args.baseline_build is not None:parser.error('--baseline-build applies only to reload captures')
root=Path(__file__).resolve().parents[1]
mode='reload' if args.reload else 'run'
log_path=root/f'outputs/restaurant-{mode}{args.build}.log'
log=log_path.read_text(encoding='utf-8')
baseline=args.baseline_build if args.reload else args.build
main=(root/f'outputs/restaurant-run{baseline}.log').read_text(encoding='utf-8')
assert '[DeepFrontier Restaurant] FAILED' not in log
assert '[DeepFrontier Restaurant] FAILED' not in main
for marker in ('ALL PLATFORM DECK CHECKS PASSED','PASS both directions across two native stairs',
               'PASS native kitchen baked four cakes','SAVED dining fixture'):
    assert marker in main,marker
assert main.count('PASS actual beaver reached ')==5
if args.reload:
    assert 'RELOAD AND INTERRUPTION CHECKS COMPLETE; native save written' in log
save_name='Restaurant regression - verified' if args.reload else 'Restaurant acceptance - verified'
source=Path('C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance')/(save_name+'.timber')
assert source.stat().st_mtime>=log_path.stat().st_ctime,'Saved file predates the current run'
with zipfile.ZipFile(source) as archive:world=json.loads(archive.read('world.json'))
assert any(e['Components']['NamedEntity']['EntityName']=='Deep Frontier Acceptance Fixture'
           for e in world['Entities'] if 'NamedEntity' in e['Components'])
placements=set((name,int(x),int(y),int(z)) for name,x,y,z in re.findall(
    r'\[DeepFrontier Restaurant\] PLACED (.+) \((-?\d+), (-?\d+), (-?\d+)\)',main))
records=[]
for name,x,y,z in sorted(placements):
    matches=[e for e in world['Entities'] if e['Template']==name and
             e['Components']['BlockObject']['Coordinates']=={'X':x,'Y':y,'Z':z}]
    assert len(matches)==1,(name,x,y,z,len(matches))
    records.append({'template':name,'position':[x,y,z],'id':matches[0]['Id']})
if args.reload:
    previous=json.loads((root/f'outputs/restaurant-grid-run{baseline}.json').read_text(encoding='utf-8'))
    assert records==previous['entities'],'Reload changed saved entity identities or positions'
restaurants=[e for e in world['Entities'] if e['Template']=='Restaurant.IronTeeth']
assert len(restaurants)==1
target=root/f'outputs/restaurant-grid-{mode}{args.build}.timber'
shutil.copyfile(source,target)
report={'build':args.build,'baselineBuild':baseline,'reload':args.reload,'archive':str(target.relative_to(root)),
        'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'entities':records,
        'verifiedPlacements':len(records),'actualWalkingTargets':5,
        'nativePathEntities':sum(r['template']=='Path' for r in records),
        'restaurant':restaurants[0],
        'limitations':'One authored orientation and adjacent external native path; wider rotations and neighboring restaurant combinations remain separate.'}
(root/f'outputs/restaurant-grid-{mode}{args.build}.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('entities','restaurant')},indent=2))
