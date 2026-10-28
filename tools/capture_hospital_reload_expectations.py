"""Extract read-only expectations from the successful native hospital save."""
import argparse,hashlib,json,re,shutil,zipfile
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--build',required=True,type=int)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
source=Path('C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance/Hospital acceptance - verified.timber')
log_path=root/f'outputs/hospital-run{args.build}.log'
log=log_path.read_text(encoding='utf-8')
assert '[DeepFrontier Hospital] FAILED' not in log
assert 'ALL CARE, STAFF, POWER, CAPACITY AND ACCESS CHECKS PASSED AND SAVED' in log
assert source.stat().st_mtime>=log_path.stat().st_ctime,'Saved file predates the current hospital run'
with zipfile.ZipFile(source) as archive:world=json.loads(archive.read('world.json'))
assert any(e['Components']['NamedEntity']['EntityName']=='Deep Frontier Acceptance Fixture'
           for e in world['Entities'] if 'NamedEntity' in e['Components'])
placements=set((name,int(x),int(y),int(z)) for name,x,y,z in re.findall(
    r'\[DeepFrontier Hospital\] PLACED (.+) \((-?\d+), (-?\d+), (-?\d+)\)',log))
assert placements,'No native hospital placement records'
placed_entities=[]
for name,x,y,z in sorted(placements):
    matches=[e for e in world['Entities'] if e['Template']==name and
             e['Components']['BlockObject']['Coordinates']=={'X':x,'Y':y,'Z':z}]
    assert len(matches)==1,(name,x,y,z,len(matches))
    placed_entities.append({'template':name,'position':[x,y,z],'id':matches[0]['Id']})
hospitals=[e for e in world['Entities'] if e['Template']=='Hospital.IronTeeth']
assert len(hospitals)==1
hospital=hospitals[0];components=hospital['Components']
assert components['PausableBuilding']['Paused']
stocks={g['Good']:g['Amount'] for g in components['Inventory:GoodConsumingBuilding']['Storage']['Goods']}
assert set(stocks)=={'Medicine','Water','Extract'}
blueprint=json.loads((root/'src/DeepFrontier/Data/Buildings/Wellbeing/Hospital/Hospital.IronTeeth.blueprint.json').read_text(encoding='utf-8'))
rates=blueprint['GoodConsumingBuildingSpec']['ConsumedGoods']
fractions=components['GoodConsumingBuilding']['SuppliesLeft']
assert len(rates)==len(fractions)==3
hours=min((stocks[g['GoodId']]+fraction)/g['GoodPerHour'] for g,fraction in zip(rates,fractions))
patients=[]
for entity in world['Entities']:
    if entity['Template']!='BeaverAdult':continue
    needs=[n for n in entity['Components']['NeedManager']['Needs']
           if n['Name'] in {'Injury','ChippedTeeth','BadwaterContamination','PublicHealthcare'}]
    if needs:patients.append({'EntityId':entity['Id'],'Needs':needs})
assert len(patients)>=3
record={'EntityId':hospital['Id'],**stocks,'SupplyHours':hours,'Patients':patients}
(root/'outputs/hospital-reload-expectations.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
preserved=root/f'outputs/hospital-verified-build{args.build}.timber'
shutil.copyfile(source,preserved)
evidence={'build':args.build,'nativeSave':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
          'preserved':str(preserved),'stocks':stocks,'fractionalSupplies':fractions,'hours':hours,
          'savedAdultsWithHealthOrNeighborhoodPoints':len(patients),
          'verifiedPlacements':len(placed_entities),'entities':placed_entities}
(root/'outputs/hospital-reload-source.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
(root/f'outputs/hospital-verification{args.build}.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in evidence.items() if k!='entities'},indent=2))
