"""Check hospital catalogue data against the authored game package."""
import json
from pathlib import Path
from openpyxl import load_workbook

root=Path(__file__).resolve().parents[1]
book=load_workbook(root/'outputs/Timberborn_Deep_Frontier_Balance_Workbook.xlsx',data_only=False)
def read(p):return json.loads((root/p).read_text(encoding='utf-8'))
def one(sheet,key,value):
    rows=book[sheet].iter_rows(values_only=True)
    headers=next(rows)
    matches=[dict(zip(headers,r)) for r in rows if r[headers.index(key)]==value]
    assert len(matches)==1,(sheet,key,value)
    return matches[0]
b=read('src/DeepFrontier/Data/Buildings/Wellbeing/Hospital/Hospital.IronTeeth.blueprint.json')
p=read('tools/frontier_progression.json')['hospital']
row=one('Buildings','Building ID','B011')
for key,value in {
    'Width':b['BlockObjectSpec']['Size']['X'],'Length':b['BlockObjectSpec']['Size']['Y'],
    'Height':b['BlockObjectSpec']['Size']['Z'],'Workers':b['WorkplaceSpec']['MaxWorkers'],
    'Power demand (hp)':b['MechanicalNodeSpec']['PowerInput'],
    'Power output (hp)':b['MechanicalNodeSpec']['PowerOutput'],
    'Science unlock':b['BuildingSpec']['ScienceCost'],'Status':p['requirementStatus']
}.items():assert row[key]==value,(key,row[key],value)
assert row['Recipe names']=='None; native per-hour supply consumption'
assert not [row for row in book['Recipes'].iter_rows(values_only=True) if row and row[0]=='R015'],'Retired Medical Food recipe still listed'
assert one('Items','Item ID','I012')['Primary uses']=='None'
assert one('Progression','Gate ID','G005')['Status']==p['requirementStatus']
assert one('Transport','System ID','T018')['Power demand (hp)']==p['powerDemandHp']
assert book['Overview']['C37'].value==p['requirementStatus']
errors=[(s.title,c.coordinate,c.value) for s in book for cells in s for c in cells if c.data_type=='e']
assert not errors,errors
report={'hospital':'Exact package dimensions, hp, science, workers and status',
        'medicalFood':'Retired 2026-10-30: no recipe row, item marked unused',
        'progressionTransportOverview':'Current hospital source values','formulaErrors':errors}
(root/'outputs/hospital-workbook-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
