"""Preserve only a completed native laboratory acceptance save."""
import argparse,hashlib,json,shutil,zipfile
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--build',type=int,required=True);parser.add_argument('--reload',action='store_true')
args=parser.parse_args();root=Path(__file__).resolve().parents[1]
kind='reload' if args.reload else 'run'
log=(root/f'outputs/research-{kind}{args.build}.log').read_text(encoding='utf-8')
success='ALL RELOAD CHECKS PASSED AND SAVED' if args.reload else 'ALL MAIN CHECKS PASSED AND SAVED'
assert success in log and '[DeepFrontier Research] FAILED:' not in log
save_name='Research continuity - verified' if args.reload else 'Research acceptance - verified'
source=Path('C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance')/(save_name+'.timber')
with zipfile.ZipFile(source) as archive:world=json.loads(archive.read('world.json'))
assert any(e['Components']['NamedEntity']['EntityName']=='Deep Frontier Acceptance Fixture'
    for e in world['Entities'] if 'NamedEntity' in e['Components'])
labs=[e for e in world['Entities'] if e['Template']=='MaterialsLaboratory.IronTeeth'];assert len(labs)==1
lab=labs[0];record=json.loads((root/'outputs/research-reload-expectations.json').read_text())
assert lab['Id']==record['EntityId']
assert lab['Components']['PausableBuilding']['Paused'] is True
assert lab['Components']['BlockObject']['Coordinates']=={'X':159,'Y':160,'Z':3}
stock=lab['Components']['Inventory:Manufactory']['Storage']['Goods']
for good,amount in record['Stock'].items():
    assert sum(g['Amount'] for g in stock if g['Good']==good)==(0 if args.reload else amount),good
assert world['Singletons']['ScienceService']['SciencePoints']==record['Science']+(800 if args.reload else 0)
stem='research-continuity' if args.reload else 'research-verified'
target=root/f'outputs/{stem}-build{args.build}.timber';shutil.copyfile(source,target)
report={'build':args.build,'reload':args.reload,'archive':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
    'science':world['Singletons']['ScienceService']['SciencePoints'],'laboratory':lab}
(root/f'outputs/{stem}{args.build}.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='laboratory'},indent=2))
