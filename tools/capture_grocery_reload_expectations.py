"""Preserve successful native grocery save and exact read-only reload expectations."""
import argparse,hashlib,json,shutil,zipfile
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--build',required=True,type=int)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
source=Path('C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance/Grocery acceptance - verified.timber')
log=(root/f'outputs/grocery-run{args.build}.log').read_text(encoding='utf-8')
assert 'ALL STOCK, SHOPPING, SERVICE AND ACCESS CHECKS PASSED AND SAVED' in log
with zipfile.ZipFile(source) as archive:world=json.loads(archive.read('world.json'))
assert any(e['Components']['NamedEntity']['EntityName']=='Deep Frontier Acceptance Fixture'
           for e in world['Entities'] if 'NamedEntity' in e['Components'])
shops=[e for e in world['Entities'] if e['Template']=='GroceryStore.IronTeeth']
assert len(shops)==1
shop=shops[0];components=shop['Components']
assert components['PausableBuilding']['Paused']
foods=json.loads((root/'tools/frontier_progression.json').read_text())['groceryStore']['stock']
saved={g['Good']:g['Amount'] for g in components['Inventory:GroceryStore']['Storage']['Goods']}
assert set(saved)<=set(foods)
stocks=[{'Name':id,'Amount':amount} for id,amount in saved.items()]
patients=[]
for entity in world['Entities']:
    if entity['Template']!='BeaverAdult':continue
    needs=[n for n in entity['Components']['NeedManager']['Needs'] if n['Name']=='NeighborhoodGroceries']
    if needs:patients.append({'EntityId':entity['Id'],'Needs':needs})
assert patients
record={'EntityId':shop['Id'],'Stocks':stocks,'Residents':patients}
(root/'outputs/grocery-reload-expectations.json').write_text(json.dumps(record,indent=2)+'\n')
preserved=root/f'outputs/grocery-verified-build{args.build}.timber'
shutil.copyfile(source,preserved)
evidence={'build':args.build,'nativeSave':str(source),'preserved':str(preserved),
          'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'stocks':stocks,'savedResidents':len(patients)}
(root/'outputs/grocery-reload-source.json').write_text(json.dumps(evidence,indent=2)+'\n')
print(json.dumps(evidence,indent=2))
