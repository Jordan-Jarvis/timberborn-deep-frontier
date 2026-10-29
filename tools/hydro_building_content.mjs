import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {solidPowerFaces} from './power_faces.mjs';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
import {industrialColliders} from './industrial_occupancy.mjs';
import {scaledCost} from './lategame_costs.mjs';

const root=new URL('../',import.meta.url);
const read=async path=>JSON.parse(await readFile(new URL(path,root),'utf8'));
const xyz=([X,Y,Z])=>({X,Y,Z});
export async function hydroBlueprint() {
  const b=await read('tools/hydro_content.json');
  const d=(await read('tools/hydro-layouts.json'))[b.id];
  if(JSON.stringify(d.size)!==JSON.stringify(b.size)||d.origin.some(n=>n!==0)||d.baseZ!==0)
    throw new Error('Turbine model/grid contract differs');
  const v=await read('vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/Buildings/Power/LargeWaterWheel/LargeWaterWheel.IronTeeth.blueprint.json');
  for(const key of ['WaterPoweredGeneratorSpec','WaterObjectSpec','FloodableBuildingSpec',
    'BlockableFloodableObjectSpec','WaterWheelSpec']) {
    if(!Object.hasOwn(v,key))throw new Error('Native turbine donor contract changed: '+key);
    delete v[key];
  }
  const [w,h,layers]=b.size;
  const index=([x,y,z])=>(z*h+y)*w+x;
  const blocks=Array.from({length:w*h*layers},()=>({
    MatterBelow:'Any',Occupations:'None',Stackable:'None',OccupyAllBelow:false,Underground:false}));
  const region=(a,c,occupation)=> {
    for(let z=a[2];z<=c[2];z++)for(let y=a[1];y<=c[1];y++)for(let x=a[0];x<=c[0];x++)
      blocks[index([x,y,z])].Occupations=occupation;
  };
  region([0,0,0],[3,5,2],'All'); // Conduit casing and rotating machinery.
  region([0,2,3],[3,3,5],'All'); // Concrete dam cap.
  region([1,1,2],[2,1,5],'All'); // Existing gate lead screw and handwheel.
  region([4,4,0],[7,9,1],'All'); // Downstream workshop foundation.
  region([4,6,2],[6,8,5],'All'); // Enclosed workshop and its roof.
  region([5,6,6],[5,6,6],'All'); // Tall dormer crest.
  // The workshop roof's eave ring: sheets end on the tile edges, its beams,
  // corner brackets and gable cladding stand 15-22 cm beyond them.
  region([3,6,4],[3,8,4],'All'); // Left eave over the conduit side.
  region([4,5,4],[6,5,5],'All'); // Front eave and gable over the terrace lane.
  region([4,5,6],[6,6,6],'All'); // Dormer roof and its front gable.
  region([4,9,4],[6,9,4],'All'); // Rear eave over the rear lane.
  region([5,9,5],[5,9,5],'All'); // Rear gable apex.
  region([7,6,4],[7,8,4],'All'); // Right eave over the side lane.
  region([4,5,2],[5,5,3],'All'); // Generator housing and coupling.
  region([4,4,3],[5,4,3],'All'); // Generator casing above the front lane.
  for(let y=0;y<h;y++)for(let x=0;x<w;x++)
    if(x!==1&&x!==2&&blocks[index([x,y,0])].Occupations!=='None')
      blocks[index([x,y,0])].MatterBelow='GroundOrStackable';
  for(const n of d.nodes) {
    const [x,y,z]=n.cell;
    blocks[index(n.cell)].Occupations='Floor, Bottom, Path';
    if(blocks[index([x,y,z-1])].Occupations!=='All')
      throw new Error('Turbine route has no solid foundation');
    blocks[index([x,y,z-1])].Stackable='BlockObject';
  }
  for(let x=0;x<4;x++)for(const y of [2,3])
    blocks[index([x,y,5])].Stackable='BlockObject';
  const solid=[];
  for(const x of [0,3])for(let y=0;y<6;y++)for(let z=0;z<2;z++)solid.push([x,y,z]);
  for(let x=0;x<4;x++)for(const y of [2,3])for(let z=2;z<6;z++)solid.push([x,y,z]);
  for(let x=4;x<8;x++)for(let y=4;y<10;y++)for(let z=0;z<2;z++)solid.push([x,y,z]);
  const planes=[];
  for(const x of [1,2])for(let y=0;y<6;y++)for(const z of [0,2])planes.push(xyz([x,y,z]));
  const model=`Buildings/Power/${b.id}/${b.id}.IronTeeth`;
  v.TemplateSpec={TemplateName:b.id+'.IronTeeth',BackwardCompatibleTemplateNames:[],
    RequiredFeatureToggle:'',DisablingFeatureToggle:''};
  v.BuildingSpec.BuildingCost=scaledCost(b.cost.map(([Id,Amount])=>({Id,Amount})),b.science);
  v.BuildingSpec.ScienceCost=b.science;
  v.BuildingSpec.SelectionSoundName='WaterWheel';
  // Same mechanical loop as the native Wind Turbine; PowerGeneratorSoundsSpec
  // starts and stops it through the native mechanical node and building mixer.
  v.BuildingSpec.LoopingSoundName=b.loopingSound;
  v.BuildingModelSpec.FinishedUncoveredModelName='';
  v.BlockObjectSpec={Size:xyz(b.size),Blocks:blocks,
    Entrance:{HasEntrance:false,Coordinates:xyz(d.entrance)},BaseZ:0,Overridable:false,Flippable:true};
  v.BlockObjectNavMeshSettingsSpec={NoAutoWalls:false,GenerateFloorsOnStackable:true,
    EdgeGroups:[
      ...d.edges.map(([a,c])=>({Cost:1,Group:{UseGroup:false,GroupName:''},IsPath:true,
        AddedEdges:[{Start:xyz(a),End:xyz(c),IsTwoWay:true}]})),
      {Cost:1,Group:{UseGroup:false,GroupName:''},IsPath:true,
        AddedEdges:d.ports.map(p=>({Start:xyz(p.inside),End:xyz(p.outside),IsTwoWay:false}))}
    ],UnblockedCoordinates:[],BlockedEdges:[]};
  v.BuildingWalkwaySpec=await read('outputs/hydro-integration/ReinforcedHydroTurbine-walkway.json');
  v.HydroTurbineSpec={
    Intakes:[[1,-1,0],[2,-1,0]].map(xyz),Outlets:[[1,5,0],[2,5,0]].map(xyz),
    Gates:[[1,3,0],[2,3,0]].map(xyz),
    SolidWaterCells:solid.map(xyz),ClosedGateCells:[[1,3,0],[1,3,1],[2,3,0],[2,3,1]].map(xyz),
    MaxDischarge:b.maxDischarge,DefaultDischarge:b.defaultDischarge,
    HpPerFlowAndHead:b.hpPerFlowAndHead,MaxGeneratingHead:b.maxGeneratingHead,
    AnimationSpeedMultiplier:b.animationSpeedMultiplier,
  };
  v.FinishableHorizontalWaterObstacleSpec={Obstacles:planes};
  v.MechanicalNodeSpec={PowerOutput:b.maxDischarge*b.maxGeneratingHead*b.hpPerFlowAndHead,
    PowerInput:0,IsShaft:false};
  v.MechanicalNodeDescriptionSpec={AlternativePowerUnitLocKey:''};
  // Shafts only where an authored wall closes the face (measured from the
  // saved study); the tested sockets stay first.
  const walls=(await read('outputs/hydro-integration/ReinforcedHydroTurbine-wall-faces.json')).walls;
  {const E=v.BlockObjectSpec.Entrance?.Coordinates,ex=E?[[E.X,E.Y,E.Z],[E.X,E.Y-1,E.Z]]:[];
  v.TransputProviderSpec={Transputs:solidPowerFaces(blocks,d.size,{exclude:ex,walls,keep:[
    {Coordinates:xyz([7,7,0]),Directions:'Right, Bottom',ReverseRotation:false},
    {Coordinates:xyz([6,9,0]),Directions:'Up, Bottom',ReverseRotation:false},
    {Coordinates:xyz([6,4,0]),Directions:'Down, Bottom',ReverseRotation:false}
  ]})};}
  v.PowerLineSpec={ConnectionLocations:[xyz([7.97,9.97,1.90])]};
  v.PlaceableBlockObjectSpec={ToolGroupId:'Power',ToolOrder:240,ToolShape:'Square',Layout:'Single',
    CustomPivot:{HasCustomPivot:true,Coordinates:xyz([2,3.5,0])},
    CanBeAttachedToTerrainSide:false,DevModeTool:false};
  v.LabeledEntitySpec={DisplayNameLocKey:`Building.${b.id}.DisplayName`,
    DescriptionLocKey:`Building.${b.id}.Description`,FlavorDescriptionLocKey:`Building.${b.id}.FlavorDescription`,
    Icon:`Buildings/Power/${b.id}/Icon`};
  v.ConstructionSiteProgressVisualizerSpec={ProgressThresholds:[]};
  const colliders=industrialColliders(blocks,b.size,0);
  v.Children={'#Finished':{TimbermeshSpec:{Model:model+'.Model'},CollidersSpec:colliders},
    '#Unfinished':{Children:{ConstructionStage0:{
      TimbermeshSpec:{Model:model+'.ConstructionStage0.Model'},CollidersSpec:colliders}}}};
  return {id:b.id,path:model+'.blueprint.json',blueprint:v,rows:[
    [`Building.${b.id}.DisplayName`,b.name],
    [`Building.${b.id}.Description`,b.description],
    [`Building.${b.id}.FlavorDescription`,'A river, given a useful job.'],
  ]};
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const entry=await hydroBlueprint();
  const target=fileURLToPath(new URL('outputs/hydro-integration/Data/'+entry.path,root));
  await mkdir(dirname(target),{recursive:true});
  await writeFile(target,JSON.stringify(entry.blueprint,null,2)+'\n');
  console.log('Hydro candidate blueprint generated; active data unchanged.');
}
