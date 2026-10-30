import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {solidPowerFaces} from './power_faces.mjs';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
import {industrialColliders} from './industrial_occupancy.mjs';
import {applyNativeBuildingAssembly} from './native_building_content.mjs';
import {applyVanillaSmoke,sceneSmokeRegistration} from './vanilla_smoke.mjs';
import {scaledCost,scaledPower} from './lategame_costs.mjs';
const root=new URL('../',import.meta.url);
const read=async path=>JSON.parse(await readFile(new URL(path,root),'utf8'));
const xyz=([X,Y,Z])=>({X,Y,Z});

export async function researchContent() {
  const catalog=await read('tools/research_content.json');
  const goods=new Set();
  for(const name of ['Common','IronTeeth']) {
    const collection=await read(`vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/GoodCollections/GoodCollection.${name}.blueprint.json`);
    for(const id of collection.GoodCollectionSpec.Goods)goods.add(id);
  }
  const ownGoods=await read('src/DeepFrontier/Data/GoodCollections/GoodCollection.IronTeeth.blueprint.json');
  for(const id of ownGoods.GoodCollectionSpec['Goods#append'])goods.add(id);
  const layouts=await read('tools/research-layouts.json');
  const recipes=[];
  for(const r of catalog.recipes) {
    for(const [id] of r.ingredients)if(!goods.has(id))throw new Error('Research ingredient is not registered for Iron Teeth: '+id);
    const v=await read('vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/Recipes/Recipe.SciencePointsNumbercruncher.blueprint.json');
    Object.assign(v.RecipeSpec,{Id:r.id,DisplayLocKey:`Recipe.${r.id}.DisplayName`,
      CycleDurationInHours:r.hours,Ingredients:r.ingredients.map(([Id,Amount])=>({Id,Amount})),
      Products:[],ProducedSciencePoints:r.science,CyclesCapacity:r.cyclesCapacity});
    recipes.push({path:`Recipes/Recipe.${r.id}.blueprint.json`,blueprint:v,
      rows:[[`Recipe.${r.id}.DisplayName`,r.name]]});
  }
  const buildings=[];
  for(const b of catalog.buildings) {
    const d=layouts[b.id];
    if(JSON.stringify(d.size)!==JSON.stringify(b.size)||d.origin.some(n=>n!==0)||d.baseZ!==0)
      throw new Error('Laboratory artwork/grid contract differs');
    for(const id of b.recipes) {
      const recipe=catalog.recipes.find(r=>r.id===id);
      if(!recipe||recipe.science/recipe.hours!==b.sciencePerWorkingHour)
        throw new Error('Laboratory recipe/nameplate rate differs');
    }
    const v=await read('vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/Buildings/Metal/Smelter/Smelter.IronTeeth.blueprint.json');
    for(const key of ['TemplateAttachmentsSpec','WorkshopParticleControllerSpec','WindParticleControllerSpec',
      'WorkshopRandomNeedApplierSpec']) {
      if(!Object.hasOwn(v,key))throw new Error('Native laboratory donor contract changed: '+key);
      delete v[key];
    }
    const [w,h,layers]=d.size,index=([x,y,z])=>(z*h+y)*w+x;
    const blocks=Array.from({length:w*h*layers},()=>({MatterBelow:'Any',Occupations:'None',
      Stackable:'None',OccupyAllBelow:false,Underground:false}));
    const region=(a,c,occupation)=>{
      for(let z=a[2];z<=c[2];z++)for(let y=a[1];y<=c[1];y++)for(let x=a[0];x<=c[0];x++) {
        if(x<0||x>=w||y<0||y>=h||z<0||z>=layers)throw new Error('Laboratory region outside envelope');
        Object.assign(blocks[index([x,y,z])],{Occupations:occupation,MatterBelow:z===0?'GroundOrStackable':'Any'});
      }
    };
    // Occupancy follows the registered shell (materials_laboratory_geometry.py):
    // cast bases on tile edges, upper storeys set back on them.
    // 2026-10-30 compaction: one-layer cast bases, terrace and records office
    // at layer 1 under a flat roof, lower sawtooth sheds, tower and press.
    region([0,0,0],[2,6,0],'All'); // Cast records wing and terrace foundation.
    region([0,3,1],[2,6,1],'All'); // Enclosed records room under its flat roof.
    region([3,1,0],[7,7,1],'All'); // Closed testing hall on its cast base (x 3..8, y 1..8).
    // Sloping roof occupancy follows each sawtooth: the front roof over rows
    // 1..3, the step facade and rear roof over rows 4..7.
    for(let x=3;x<=7;x++) {
      region([x,1,2],[x,3,[3,2,2,2,2][x-3]],'All');
      region([x,4,2],[x,7,[3,3,3,3,2][x-3]],'All');
    }
    region([8,1,0],[9,2,2],'All'); // Test press on its 2x2 plinth.
    region([8,5,0],[9,6,4],'All'); // Instrument tower on its 2x2 plinth.
    // No forced decoration beyond the walls (2026-10-22): the outdoor shelves,
    // planters, barrel and crate are gone; their cells are open ground.
    const interior=new Set(d.interiorCells.map(c=>c.join(',')));
    for(const n of d.nodes) {
      if(interior.has(n.cell.join(',')))continue;
      blocks[index(n.cell)].Occupations='Floor, Bottom, Path';
      if(n.cell[2]>0) {
        const support=blocks[index([n.cell[0],n.cell[1],n.cell[2]-1])];
        if(support.Occupations!=='All')throw new Error('Laboratory terrace has no solid support');
        support.Stackable='BlockObject';
      }
    }
    const model=`Buildings/Science/${b.id}/${b.id}.IronTeeth`;
    v.TemplateSpec={TemplateName:b.id+'.IronTeeth',BackwardCompatibleTemplateNames:[],RequiredFeatureToggle:'',DisablingFeatureToggle:''};
    Object.assign(v.BuildingSpec,{BuildingCost:scaledCost(b.cost.map(([Id,Amount])=>({Id,Amount})),b.scienceUnlock),ScienceCost:b.scienceUnlock});
    Object.assign(v.BuildingModelSpec,{FinishedUncoveredModelName:'',UndergroundModelName:'',UndergroundModelDepth:0});
    v.WorkplaceSpec={MaxWorkers:b.workers,DefaultWorkers:b.workers,DefaultWorkerType:'Beaver',
      DisallowOtherWorkerTypes:false,WorkerTypeUnlockCosts:[{WorkerType:'Bot',ScienceCost:2000}]};
    v.ManufactorySpec={ProductionRecipeIds:b.recipes};
    v.MechanicalNodeSpec={PowerInput:scaledPower(b.id,b.powerDemandHp,b.scienceUnlock),PowerOutput:0,IsShaft:false};
    v.MechanicalNodeAnimatorSpec={MinSpeedMultiplier:0};
    // Native Entrance on the path cell in front of the ground door (vanilla
    // convention, as in the donor Smelter); its doorstep is the door cell, so
    // an adjacent player path draws its connection stub to the doorway.
    const doorOutside=[d.entrance[0],d.entrance[1]-1,d.entrance[2]];
    v.BlockObjectSpec={Size:xyz(d.size),Blocks:blocks,Entrance:{HasEntrance:true,Coordinates:xyz(doorOutside)},BaseZ:0,Overridable:false,Flippable:true};
    // Access point on the ground door's casing face (tile edge y=0).
    v.BuildingAccessibleSpec={LocalAccess:xyz([1.5,0,0]),ForceOneFinalAccess:false};
    v.BlockObjectNavMeshSettingsSpec={NoAutoWalls:false,GenerateFloorsOnStackable:false,
      EdgeGroups:[...d.edges.map(([a,c])=>({Cost:1,Group:{UseGroup:a[2]!==c[2],GroupName:a[2]!==c[2]?'DeepFrontierInterior':''},IsPath:true,
        AddedEdges:[{Start:xyz(a),End:xyz(c),IsTwoWay:true}]})),
        {Cost:1,Group:{UseGroup:false,GroupName:''},IsPath:true,AddedEdges:d.ports.map(p=>({Start:xyz(p.inside),End:xyz(p.outside),IsTwoWay:false}))},
        {Cost:1,Group:{UseGroup:false,GroupName:''},IsPath:true,AddedEdges:[{Start:xyz(d.entrance),End:xyz(doorOutside),IsTwoWay:true}]}],
      UnblockedCoordinates:[],BlockedEdges:[]};
    v.BuildingWalkwaySpec=await read(`outputs/research-integration/${b.id}-walkway.json`);
    // Shafts only where an authored wall closes the face (measured from the
    // saved study); the three tested service sockets stay first.
    const walls=(await read(`outputs/research-integration/${b.id}-wall-faces.json`)).walls;
    v.TransputProviderSpec={IgnoreRotation:false,Transputs:solidPowerFaces(blocks,d.size,{exclude:[d.entrance,doorOutside],walls,keep:[
      {Coordinates:xyz([7,4,0]),Directions:'Right, Bottom',ReverseRotation:false},
      {Coordinates:xyz([0,4,0]),Directions:'Left, Bottom',ReverseRotation:false},
      {Coordinates:xyz([4,7,0]),Directions:'Up, Bottom',ReverseRotation:false}]})};
    // Second point: the insulator bracket over the right-side service bay.
    // Timber Pipes 11.4.0: with no BuildingPipeTargetPortsSpec the default
    // connection provider accepts any face, provided the building holds a
    // liquid good. Recipe Water supplies that; no port is authored, so a pipe
    // may meet any side (the tower's bay socket marks the intended spot).
    // Heights follow the one-layer bases and the lower insulator bracket (2026-10-30).
    v.PowerLineSpec={ConnectionLocations:[xyz([.18,6.65,.84]),xyz([8.205,3.5,2.06])]};
    v.TransformSlotInitializerSpec={Slots:[{SlotKeyword:'Entrance',Animation:'ForcedIdle',Inanimate:false,RandomizeYRotation:false,WaterSlot:false}]};
    v.PlaceableBlockObjectSpec={ToolGroupId:'Science',ToolOrder:100,ToolShape:'Square',Layout:'Single',
      CustomPivot:{HasCustomPivot:false,Coordinates:xyz([0,0,0])},CanBeAttachedToTerrainSide:false,DevModeTool:false};
    v.LabeledEntitySpec={DisplayNameLocKey:`Building.${b.id}.DisplayName`,DescriptionLocKey:`Building.${b.id}.Description`,
      FlavorDescriptionLocKey:`Building.${b.id}.FlavorDescription`,Icon:`Buildings/Science/${b.id}/Icon`};
    v.ConstructionSiteProgressVisualizerSpec={ProgressThresholds:[]};
    const colliders=industrialColliders(blocks,d.size,0);
    v.Children={'#Finished':{TimbermeshSpec:{Model:model+'.Model'},CollidersSpec:colliders},
      '#Unfinished':{Children:{ConstructionStage0:{TimbermeshSpec:{Model:model+'.ConstructionStage0.Model'},CollidersSpec:colliders}}}};
    // Vanilla smoke from the scene's registered emitters (the donor Smelter's own
    // effects were removed above): none since the roof flues went (no roof vents,
    // user 2026-10-30), so the lab no longer pollutes.
    applyVanillaSmoke(v,await sceneSmokeRegistration('research-integration',b.id,d),b.id);
    await applyNativeBuildingAssembly(v,b.id,d.origin,{goodId:'Water',flowNodes:[],wheelNodes:[]});
    buildings.push({id:b.id,path:model+'.blueprint.json',blueprint:v,rows:[
      [`Building.${b.id}.DisplayName`,b.name],[`Building.${b.id}.Description`,b.description],
      [`Building.${b.id}.FlavorDescription`,'Break a few samples. Build a better future.']]});
  }
  return {buildings,recipes};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const {buildings,recipes}=await researchContent();
  for(const entry of [...buildings,...recipes]) {
    const path=fileURLToPath(new URL('outputs/research-integration/Data/'+entry.path,root));
    await mkdir(dirname(path),{recursive:true});
    await writeFile(path,JSON.stringify(entry.blueprint,null,2)+'\n');
  }
  console.log('Research candidate authored; active package unchanged.');
}
