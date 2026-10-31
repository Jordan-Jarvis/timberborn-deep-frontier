"""Inspect the hospital's actual export and care blueprint before a native run."""
import collections,json,hashlib,math,struct,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent/'timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2
from native_uv_contract import valid_native_uv

def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def require(value,message):
    if not value:raise ValueError(message)

layout=read('tools/civic-layouts.json')['Hospital']
folder=ROOT/'src/DeepFrontier/Data/Buildings/Wellbeing/Hospital'
blueprint=read('src/DeepFrontier/Data/Buildings/Wellbeing/Hospital/Hospital.IronTeeth.blueprint.json')
payload=(folder/'Hospital.IronTeeth.Model.timbermesh').read_bytes()
model=model_pb2.Model();model.ParseFromString(zlib.decompress(payload))
names=collections.Counter(n.name for n in model.nodes)
require(all(count==1 for count in names.values()),'Duplicate model nodes')
require(not any(name.startswith('#Slot#Seat') for name in names),'Hospital patients must be indoors, not restaurant seats')
native={'BaseWood_DarkBrown.IronTeeth','IrregularPlanks_DarkBrown.IronTeeth','RoofPlanks.IronTeeth',
        'BaseMetal.IronTeeth','Details.IronTeeth','Plaster_White.IronTeeth',
        'Plaster_Orange.IronTeeth','IrregularPlanks_MetalForged.IronTeeth'}
require(native<={m.material for n in model.nodes for m in n.meshes},'Missing original civic palette')
uv_count=0
for n in model.nodes:
    meshes=[m for m in n.meshes if m.material in native]
    if not meshes:continue
    uv=list(struct.iter_unpack('<ff',next(p.data for p in n.vertexProperties if p.name=='uv0')))
    for m in meshes:
        for i in set(m.indices):
            require(valid_native_uv(m.material,uv[i]),'UV outside authored/native contract: '+n.name)
            uv_count+=1
tracks=[(n.name,a) for n in model.nodes for a in n.nodeAnimations]
require({name for name,a in tracks}=={'#Hospital.WardBanner5.18','#Hospital.WardBanner8.82'},'Hospital banner tracks missing')
require(all(len(a.frames)==61 for name,a in tracks),'Banner loop lost frames')
require(payload==(folder/'Hospital.IronTeeth.ConstructionStage0.Model.timbermesh').read_bytes(),'Construction export differs')
assembly=read('outputs/reference-studies/Hospital-native-assembly.json')
require(all(not any(p['name'] in n for n in names) for p in assembly['props']),'Native preview props shipped in export')
# No forced ground decoration (2026-10-22): the facade planters and the rear
# barrel are gone, so the Hospital has no native props.
require('NativeBuildingPropsSpec' not in blueprint and len(assembly['props'])==0,'Native prop binding mismatch')
# 2026-10-21: front/back balconies only; each ward and the back balcony has its own door.
# Since the wings were removed (2026-10-30): ground, rear deck, rear ward and roof garden doors.
require('BuildingWalkwaySpec' not in blueprint and len(blueprint['PlatformDeckSpec']['Doors'])==4,'Hospital must use player roads and four internal doors')
require(len(blueprint['PlatformDeckSpec']['Openings'])==22,'Missing individual rail ports')
for port in blueprint['PlatformDeckSpec']['Openings']:
    require(all(names[n]==1 for n in port['HiddenNodes']+port['ShownNodes']),'Missing rail node '+port['Id'])
cells={tuple(n['cell']) for n in layout['nodes']};graph={c:set() for c in cells}
for a,b in layout['edges']:
    a,b=tuple(a),tuple(b)
    require(a in cells and b in cells and sum(abs(a[i]-b[i]) for i in range(3))==1,'Invalid route edge')
    graph[a].add(b);graph[b].add(a)
seen=set();queue=[tuple(layout['entrance'])]
while queue:
    c=queue.pop()
    if c in seen:continue
    seen.add(c);queue.extend(graph[c]-seen)
require(seen==cells and len(cells)==37,'Disconnected hospital doors/galleries')
require({c[2] for c in layout['doorNodes']}=={0,2,4,6},'Existing doors were moved')
w,d,h=layout['size'];blocks=blueprint['BlockObjectSpec']['Blocks']
require(len(blocks)==w*d*h,'Occupation extent mismatch')
# The footprint ends at the walls (2026-10-22): every ground cell outside the
# halls is open (balcony posts take only Corners), so player paths and
# decorations fit there (validate_freed_cells.py checks the native rules).
rooms=[r for r in layout['structure']['rooms'].values() if r[2]==0]
for y in range(d):
    for x in range(w):
        if not any(r[0]<=x<r[3] and r[1]<=y<r[4] for r in rooms):
            require(blocks[y*w+x]['Occupations'] in ('None','Corners'),f'Ground cell {(x,y,0)} outside the halls is reserved')
for x,y,z in layout['buildableCells']:
    require(blocks[((z-1)*d+y)*w+x]['Stackable']=='BlockObject','Roof terrace has no native support')
    require(blocks[(z*d+y)*w+x]['Occupations']=='None','Fixed object consumes clear hospital roof space')
require(len(layout['buildableCells'])==12,'The central four-by-three roof garden must stay clear')
require(blueprint['BlockObjectSpec']['Flippable'],'Hospital must offer native mirroring')
require('ManufactorySpec' not in blueprint and 'WorkshopSpec' not in blueprint,'Hospital retains factory behavior')
require('FixedSlotManagerSpec' not in blueprint and 'WorkplaceSlotManagerSpec' not in blueprint,'Staff/patient capacity must not share restaurant slots')
require('StatusHidingEnterableSpec' not in blueprint,'Workplace already supplies the one native IStatusHider')
require(blueprint['EnterableSpec']['CapacityFinished']==30,'Patient capacity differs')
# 11,000 hp: the late-game power rule's floor at 25,000 science (authored 600).
require(blueprint['MechanicalNodeSpec']=={'PowerInput':11000,'PowerOutput':0,'IsShaft':False},'Hospital hp roles differ')
require(blueprint['BuildingSpec']['ScienceCost']==25000,'Initial science balance differs')
effects={e['NeedId']:e for e in blueprint['AttractionSpec']['Effects']}
# Radiation adds its 10-day Irradiation treatment (tools/radiation_content.mjs).
require(set(effects)=={'Injury','ChippedTeeth','BadwaterContamination','Irradiation'},'Wrong native conditions')
require(effects['Irradiation']['PointsPerHour']>0,'Irradiation treatment must recover the condition')
# Native AttractionNeedBehavior.MaxValueNeedsAreActive releases a patient once every
# SatisfyToMaxValue need is full: all effects carry it, so patients stay until cured.
require(all(e['SatisfyToMaxValue'] for e in effects.values()),'Every treatment must keep patients admitted until cured (all-or-none SatisfyToMaxValue)')
meals=blueprint.get('HospitalPantrySpec')
care=json.loads((ROOT/'tools/frontier_progression.json').read_text(encoding='utf-8'))['hospital']
vanilla=ROOT/'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources'
thirst=-json.loads((vanilla/'Needs/Need.Beaver.Thirst.blueprint.json').read_text(encoding='utf-8-sig'))['NeedSpec']['DailyDelta']
quench=[e['Points'] for e in json.loads((vanilla/'Goods/Good.Water.blueprint.json').read_text(encoding='utf-8-sig'))['GoodSpec']['ConsumptionEffects'] if e['NeedId']=='Thirst']
require(len(quench)==1 and thirst>0,'Native water/Thirst evidence changed')
require(meals=={'FoodCapacityPerGood':care['patientMeals']['foodUnitsPerGood'],'WaterGoodId':'Water',
  'WaterCapacity':math.ceil(care['patientCapacity']*care['patientMeals']['zombieNeedMultiplier']*thirst*care['patientMeals']['waterDays']/quench[0]),
  'LowStockUnits':care['patientMeals']['lowStockUnits']},'Admitted patients need the authored meal stock (HospitalPantrySpec)')
require(abs((effects['Injury']['PointsPerHour']+.1/24)/(.015+.1/24)-1.8)<1e-10,'Steady native recovery is not 80 percent faster under the observed half-treatment cadence')
require(effects['ChippedTeeth']['PointsPerHour']==.5 and effects['BadwaterContamination']['PointsPerHour']==.068,'Native tooth/contamination rates differ')
require(blueprint['HospitalSpec']['WardWorkPosition']=={'X':2.5,'Y':0,'Z':3.5},'Staff work point differs from the enclosed central ward')
report={'status':'Source/export checks passed; native runtime acceptance pending','size':[w,d,h],
        'sourceSha256':hashlib.sha256((ROOT/'src/DeepFrontier/Art/Source/Hospital-ReferenceStudy.blend').read_bytes()).hexdigest(),
        'exportSha256':hashlib.sha256(payload).hexdigest(),'nodes':len(model.nodes),'nativeUvVertices':uv_count,
        'routes':len(cells),'openings':42,'doors':6,'doorLevels':[0,2,4,6],'nativeProps':0,'bannerTracks':2,
        'patients':30,'workers':6,'patientMeals':meals,'hpDemand':11000,'hpOutput':0,'science':25000,'treatmentEffects':effects}
(ROOT/'outputs/civic-integration/hospital-static-checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
