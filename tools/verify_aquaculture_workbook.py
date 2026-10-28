"""Read-only checks that aquaculture workbook rows match authored game data."""
import json
from pathlib import Path
from openpyxl import load_workbook

root=Path(__file__).resolve().parents[1]
book=load_workbook(root/'outputs/Timberborn_Deep_Frontier_Balance_Workbook.xlsx',data_only=False)
def read(path):return json.loads((root/path).read_text(encoding='utf-8'))
def rows(sheet):
    data=book[sheet].iter_rows(values_only=True)
    header=next(data)
    return [dict(zip(header,row)) for row in data]
def one(sheet,column,value):
    matches=[r for r in rows(sheet) if r[column]==value]
    assert len(matches)==1,(sheet,value,len(matches))
    return matches[0]
report={}
for id,label in [('FishHatchery','Fish Hatchery'),('FisheryWorks','Fishery Works')]:
    b=read(f'src/DeepFrontier/Data/Buildings/Food/{id}/{id}.IronTeeth.blueprint.json')
    row=one('Buildings','Building / Machine',label)
    expected={'Width':b['BlockObjectSpec']['Size']['X'],'Length':b['BlockObjectSpec']['Size']['Y'],'Height':b['BlockObjectSpec']['Size']['Z'],
      'Power demand (hp)':b['MechanicalNodeSpec']['PowerInput'],'Power output (hp)':b['MechanicalNodeSpec']['PowerOutput'],
      'Workers':b['WorkplaceSpec']['MaxWorkers'],'Science unlock':b['BuildingSpec']['ScienceCost']}
    for key,value in expected.items():assert row[key]==value,(id,key,row[key],value)
    port_text='; '.join(f"({p['Coordinates']['X']},{p['Coordinates']['Y']},{p['Coordinates']['Z']}) {p['Directions']} {p['State']}"
                       for p in b['BuildingPipeTargetPortsSpec']['Ports'])
    assert row['Pipe ports']==port_text,(id,row['Pipe ports'],port_text)
    report[id]=expected
for recipeId,rowId in [('JuvenileFish','R004'),('FreshFish','FreshFish'),('FishOil','FishOil')]:
    recipe=read(f'src/DeepFrontier/Data/Recipes/Recipe.{recipeId}.blueprint.json')['RecipeSpec']
    row=one('Recipes','Recipe ID',rowId)
    assert row['Cycle hours']==recipe['CycleDurationInHours']
    assert json.loads(row['Raw inputs'])==recipe['Ingredients']
    assert json.loads(row['Raw outputs'])==recipe['Products']
    assert row['Power output (hp)']==0
    report[recipeId+'Recipe']='Exact inputs, outputs and native cycle hours'
catch=one('Recipes','Recipe ID','ShoreCatch')
assert catch['Cycle hours']==read('tools/aquaculture.json')['shoreFishing']['CatchHours']
assert catch['Power demand (hp)']==0
assert one('Items','Item','Fresh Fish')['Perishable']=='No'
assert one('Items','Item','Juvenile Fish')['Weight']==8
assert one('Items','Item','Fish Oil')['Type']=='Liquid'
assert 'real clean water below' in one('Buildings','Building / Machine','Fish Hatchery')['Placement'].lower()
transport=one('Transport','System ID','T017')
assert transport['Power demand (hp)'] is None
assert '50 hp' in transport['Requires']
assert transport['Data status']==read('tools/aquaculture.json')['transportStatus']
assert not [(s.title,c.coordinate,c.value) for s in book for row in s for c in row if c.data_type=='e']
report['formulaErrors']=[]
(root/'outputs/aquaculture-workbook-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
