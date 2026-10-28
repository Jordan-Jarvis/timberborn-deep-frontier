"""Create a marked disposable copy of the existing native concrete test save."""
import json, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SAVES=Path('C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves')
source=SAVES/'Concrete Acceptance/Concrete chain recovery.timber'
destination=SAVES/'Industrial Acceptance/Industrial acceptance - initial.timber'
destination.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(source) as archive:
    contents={name:archive.read(name) for name in archive.namelist()}
world=json.loads(contents['world.json'])
# These two objects were placed with No Build Restriction in the original test
# save and are rejected by native loading. Remove them only in this fixture.
obsolete={('Path',(133,135,5)),('LimestonePit.IronTeeth',(136,139,5))}
removed=[];kept=[]
for entity in world['Entities']:
    components=entity['Components']
    key=None
    if 'BlockObject' in components:
        c=components['BlockObject']['Coordinates']
        key=(entity['Template'],(c['X'],c['Y'],c['Z']))
    if key in obsolete:removed.append(key)
    else:kept.append(entity)
assert set(removed)==obsolete,(removed,obsolete)
world['Entities']=kept
centers=[e for e in world['Entities'] if e['Template']=='DistrictCenter.IronTeeth']
assert len(centers)==1
centers[0]['Components']['NamedEntity']['EntityName']='Deep Frontier Acceptance Fixture'
world['Singletons']['CameraService']['CameraState']={
    'Target':{'X':166.0,'Y':3.0,'Z':150.0},'ZoomLevel':.60,
    'HorizontalAngle':215.0,'VerticalAngle':50.0}
contents['world.json']=json.dumps(world,separators=(',',':')).encode()
metadata=json.loads(contents['save_metadata.json'])
print('Fixture retains native metadata for',len(metadata['Mods']),'mods; removed exactly',len(removed),'obsolete test objects')
with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
    for name,data in contents.items():archive.writestr(name,data)
print(destination)
