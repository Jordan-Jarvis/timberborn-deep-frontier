"""Capture exact installed Ladder 1.1 package facts; no download or mutation."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=Path('C:/Program Files (x86)/Steam/steamapps/workshop/content/1062090/3286476486/version-1.1')
manifest_path=PACKAGE/'manifest.json'
blueprint_path=PACKAGE/'Buildings/Paths/Ladder/Ladder.IronTeeth.blueprint.json'
dll_path=PACKAGE/'Scripts/Ladder.dll'
manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
blueprint=json.loads(blueprint_path.read_text(encoding='utf-8'))
if manifest['Id']!='Tobbert.Ladder' or manifest['Version']!='1.0.0.4':
    raise ValueError('Ladder package changed; inspect its API before updating the capture')
for spec in ('MechanicalNodeSpec','WorkplaceSpec','ManufactorySpec'):
    if spec in blueprint:raise ValueError('Ladder now has a production/power spec: '+spec)
record={
    'checkedDate':'2026-10-19','targetGameVersion':'1.1.2.8',
    'workshopId':'3286476486','packagePath':str(PACKAGE),
    'id':manifest['Id'],'version':manifest['Version'],
    'minimumGameVersion':manifest['MinimumGameVersion'],'requiredMods':manifest['RequiredMods'],
    'deepFrontierRole':'Candidate vertical access dependency; already installed; no mandatory manifest entry yet',
    'sourceFiles':{str(p.relative_to(PACKAGE)):hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (manifest_path,blueprint_path,dll_path)},
    'ironTeeth':{
        'templateName':blueprint['TemplateSpec']['TemplateName'],
        'size':blueprint['BlockObjectSpec']['Size'],
        'blocks':blueprint['BlockObjectSpec']['Blocks'],
        'cost':blueprint['BuildingSpec']['BuildingCost'],
        'science':blueprint['BuildingSpec']['ScienceCost'],
        'workers':0,'powerDemandHp':0,'powerOutputHp':0,'recipes':[],
        'mainPathCoordinates':blueprint['PathSpec']['MainPathCoordinates'],
        'navigation':blueprint['BlockObjectNavMeshSettingsSpec']},
    'evidence':{
        'loadedPackage':'outputs/timberborn_construction_world_13.log:59',
        'apiInspection':'outputs/ladder-api-1.0.0.4/Ladder.decompiled.cs',
        'runtimeTraversal':'Not tested on the reviewed quarry',
        'redistribution':'External Workshop dependency; no third-party assets or code bundled into Deep Frontier'}
}
destination=ROOT/'tools/ladder_dependency_1_1.json'
destination.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(destination)
