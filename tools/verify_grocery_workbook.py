"""Read-only comparison of grocery workbook records and the authored package."""
import json
from pathlib import Path
from openpyxl import load_workbook

root=Path(__file__).resolve().parents[1]
book=load_workbook(root/'outputs/Timberborn_Deep_Frontier_Balance_Workbook.xlsx',data_only=False)
b=json.loads((root/'src/DeepFrontier/Data/Buildings/Food/GroceryStore/GroceryStore.IronTeeth.blueprint.json').read_text())
p=json.loads((root/'tools/frontier_progression.json').read_text())['groceryStore']
def one(sheet,key,value):
    rows=book[sheet].iter_rows(values_only=True)
    headers=next(rows)
    matches=[dict(zip(headers,r)) for r in rows if r[headers.index(key)]==value]
    assert len(matches)==1,(sheet,key,value)
    return matches[0]
row=one('Buildings','Building ID','B009')
for key,value in {
    'Width':b['BlockObjectSpec']['Size']['X'],'Length':b['BlockObjectSpec']['Size']['Y'],
    'Height':b['BlockObjectSpec']['Size']['Z'],'Workers':b['WorkplaceSpec']['MaxWorkers'],
    'Power demand (hp)':b['MechanicalNodeSpec']['PowerInput'],'Power output (hp)':b['MechanicalNodeSpec']['PowerOutput'],
    'Science unlock':b['BuildingSpec']['ScienceCost'],'Status':p['requirementStatus']
}.items():assert row[key]==value,(key,row[key],value)
assert row['Recipe names']=='None; stocks and serves existing foods'
assert 'restaurant' not in one('Items','Item ID','I010')['Consumed by'].lower()
assert one('Progression','Gate ID','G022')['Science range']==p['scienceUnlock']
assert one('Transport','System ID','T019')['Power demand (hp)']==p['powerDemandHp']
assert one('Transport','System ID','T019')['Base capacity / min'] is None
assert one('Transport','System ID','T019')['Dependency adapter']=='Belt intake, capacity, power and saved queue passed 73/75'
for id,row_id in [('CannedFish','R006')]:
    r=json.loads((root/f'src/DeepFrontier/Data/Recipes/Recipe.{id}.blueprint.json').read_text())['RecipeSpec']
    entry=one('Recipes','Recipe ID',row_id)
    assert entry['Building']=='Food Packaging Works'
    assert entry['Cycle hours']==r['CycleDurationInHours']
    assert json.loads(entry['Raw inputs'])==r['Ingredients']
    assert json.loads(entry['Raw outputs'])==r['Products']
assert book['Overview']['D37'].value==p['requirementStatus']
assert not [(s.title,c.coordinate,c.value) for s in book for cells in s for c in cells if c.data_type=='e']
report={'grocery':'Exact package dimensions, hp, science, workers, stock and status',
        'progressionTransportOverview':'Source values match','formulaErrors':[]}
(root/'outputs/grocery-workbook-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
