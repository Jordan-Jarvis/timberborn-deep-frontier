import {readFile,writeFile,copyFile} from 'node:fs/promises';
import {structureBlocks,authoredColliders,roomPowerFaces} from './grid_structure.mjs';
import {applyNativeBuildingAssembly} from './native_building_content.mjs';
import {wallRoomPowerFaces} from './civic_wall_faces.mjs';
import {applyVanillaSmoke,sceneSmokeRegistration} from './vanilla_smoke.mjs';
import {scaledCost,scaledPower} from './lategame_costs.mjs';
const root=new URL('../',import.meta.url);
const data=new URL('src/DeepFrontier/Data/',root);
const vanilla=new URL('vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/',root);
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const xyz=([X,Y,Z])=>({X,Y,Z});
const layout=(await read(new URL('tools/civic-layouts.json',root))).Hospital;
const care=(await read(new URL('tools/frontier_progression.json',root))).hospital;
// Generated draw: the authored demand under the power rule (lategame_costs.mjs scaledPower).
const careHp=scaledPower('Hospital',care.powerDemandHp,care.scienceUnlock);

// Vanilla convention (138 of 139 shipped buildings): the native Entrance is
// the path cell in front of the door, and its doorstep is the door cell.
// Timberborn's DynamicPathModel only draws a path's connection stub toward an
// entrance flag on that path cell, so an Entrance on the door cell itself
// leaves the path visually unconnected. Use the ground door's exterior cell.
function nativeEntrance(layout,blocks,index){
  const door=layout.doorLinks.find(d=>d.Interior.join()===layout.entrance.join());
  if(!door)throw new Error('No door link leaves the layout entrance '+layout.entrance);
  const [a,b]=[door.Interior,door.Exterior];
  if(a[2]!==b[2]||Math.abs(a[0]-b[0])+Math.abs(a[1]-b[1])!==1)throw new Error('Entrance door link is not one horizontal step: '+a+' -> '+b);
  const [w,d,h]=layout.size;
  const inside=b[0]>=0&&b[1]>=0&&b[2]>=0&&b[0]<w&&b[1]<d&&b[2]<h;
  if(inside&&blocks[index(b)].Occupations!=='None')throw new Error('Entrance path cell is occupied: '+b);
  return b;
}

export async function applyHospital(value) {
  // A care attraction has one native supply processor. It is not a factory.
  for(const key of ['ManufactorySpec','WorkshopSpec','SimpleManufactoryBehaviorsSpec',
    'WorkshopAnimationControllerSpec','WorkplaceIlluminatorSpec','WorkplaceSlotManagerSpec',
    'WorkshopWorkerHiderSpec'])delete value[key];
  const [w,d,h]=layout.size,index=([x,y,z])=>(z*d+y)*w+x;
  const blocks=structureBlocks(layout.structure,layout.size);
  const interior=new Set(layout.interiorCells.map(c=>c.join(',')));
  for(const n of layout.nodes) {
    if(interior.has(n.cell.join(',')))continue;
    const [x,y,z]=n.cell;
    if(blocks[index(n.cell)].Occupations==='All')throw new Error('Hospital suggested road intersects a room: '+n.cell);
    if(z>0) {
      const support=blocks[index([x,y,z-1])];
      if(support.Occupations==='None')throw new Error('Hospital road has no authored floor: '+n.cell);
      support.Stackable='BlockObject';
    }
  }
  for(const [x,y,z] of layout.buildableCells) {
    if(blocks[index([x,y,z])].Occupations!=='None')throw new Error('Hospital roof garden is obstructed: '+[x,y,z]);
    blocks[index([x,y,z-1])].Stackable='BlockObject';
  }
  value.BlockObjectSpec={Size:xyz(layout.size),Blocks:blocks,Entrance:{HasEntrance:true,Coordinates:xyz(nativeEntrance(layout,blocks,index))},BaseZ:0,Overridable:false,Flippable:true};
  value.BuildingAccessibleSpec={LocalAccess:xyz(layout.localAccess),ForceOneFinalAccess:false};
  value.EnterableSpec={OperatingState:'Finished',LimitedCapacityFinished:true,CapacityFinished:care.patientCapacity,LimitedCapacityUnfinished:false,CapacityUnfinished:0};
  // Native Enterer hides indoor patients. Staff walk to the ward work point
  // without entering this patient-capacity pool.
  value.WorkplaceSpec={MaxWorkers:care.workers,DefaultWorkers:care.workers,DefaultWorkerType:'Beaver',DisallowOtherWorkerTypes:true,WorkerTypeUnlockCosts:[]};
  Object.assign(value.BuildingSpec,{ScienceCost:care.scienceUnlock,BuildingCost:scaledCost(care.buildingCost,care.scienceUnlock),SelectionSoundName:'MedicalBed',LoopingSoundName:''});
  value.MechanicalNodeSpec={PowerInput:careHp,PowerOutput:0,IsShaft:false};
  value.ConstructionSiteProgressVisualizerSpec={ProgressThresholds:[]};
  const colliders=authoredColliders(await read(new URL('outputs/reference-studies/Hospital-structure.json',root)),layout.structure,layout.baseZ);
  value.Children['#Finished'].CollidersSpec=colliders;
  value.Children['#Unfinished']={Children:{ConstructionStage0:{
    TimbermeshSpec:{Model:'Buildings/Wellbeing/Hospital/Hospital.IronTeeth.ConstructionStage0.Model'},
    CollidersSpec:colliders}}};
  const edges=layout.edges.filter(([a,b])=>interior.has(a.join(','))&&interior.has(b.join(','))).map(([a,b])=>({
    Cost:1,Group:{UseGroup:a[2]!==b[2],GroupName:a[2]!==b[2]?'DeepFrontierInterior':''},IsPath:true,
    AddedEdges:[{Start:xyz(a),End:xyz(b),IsTwoWay:true}]}));
  edges.push({Cost:1,Group:{UseGroup:false,GroupName:''},IsPath:true,
    AddedEdges:layout.doorLinks.map(link=>({Start:xyz(link.Interior),End:xyz(link.Exterior),IsTwoWay:true}))});
  value.BlockObjectNavMeshSettingsSpec={NoAutoWalls:false,GenerateFloorsOnStackable:true,EdgeGroups:edges,UnblockedCoordinates:[],BlockedEdges:[]};
  delete value.BuildingWalkwaySpec;
  value.PlatformDeckSpec=await read(new URL('outputs/civic-integration/Hospital-platform-deck.json',root));
  value.TransputProviderSpec={IgnoreRotation:false,Transputs:await wallRoomPowerFaces('Hospital',layout.structure,layout.size)};
  const bed=await read(new URL('Buildings/Wellbeing/MedicalBed/MedicalBed.IronTeeth.blueprint.json',vanilla));
  const teeth=await read(new URL('Buildings/Wellbeing/TeethGrindstone/TeethGrindstone.IronTeeth.blueprint.json',vanilla));
  const pod=await read(new URL('Buildings/Wellbeing/DecontaminationPod/DecontaminationPod.IronTeeth.blueprint.json',vanilla));
  const injury=await read(new URL('Needs/Need.Beaver.Injury.blueprint.json',vanilla));
  const effect=(b,id)=>{
    const matches=b.AttractionSpec.Effects.filter(e=>e.NeedId===id);
    if(matches.length!==1)throw new Error('Expected one native treatment effect: '+id);
    return matches[0];
  };
  // The native repeat-visit cadence alternates an effect tick with a completion
  // tick. Need.Update uses passive recovery only on the latter. Match the
  // measured steady Medical Bed rate under that same native cadence.
  const duty=care.nativeTreatmentEvidence.observedRepeatVisitTreatmentFraction;
  const passive=injury.NeedSpec.DailyDelta/24;
  const bedRate=duty*effect(bed,'Injury').PointsPerHour+(1-duty)*passive;
  const healing=(care.injuryRecoveryRateMultiplier*bedRate-(1-duty)*passive)/duty;
  // Admitted until cured. Native AttractionNeedBehavior.MaxValueNeedsAreActive
  // releases a patient only once every SatisfyToMaxValue need is at its
  // maximum, and otherwise returns to the stay (ReturnWhenFinished), so all
  // effects carry it (radiation_content.mjs adds Irradiation the same way):
  // one cured condition never ends another's treatment. The stay keeps the
  // native cadence (0.05 h effect, then a completion tick), so the measured
  // half-treatment duty above still holds.
  value.AttractionSpec={Effects:[
    {NeedId:'Injury',PointsPerHour:healing,SatisfyToMaxValue:true},
    {...effect(teeth,'ChippedTeeth'),SatisfyToMaxValue:true},
    {...effect(pod,'BadwaterContamination'),SatisfyToMaxValue:true}
  ]};
  // Patient meals (Scripts/HospitalPantry.cs): admitted patients cannot leave
  // to eat. Foods are chosen at runtime from the faction's goods; water covers
  // every bed for waterDays at the zombie's doubled native Thirst.
  const meals=care.patientMeals;
  const thirst=(await read(new URL('Needs/Need.Beaver.Thirst.blueprint.json',vanilla))).NeedSpec;
  const water=(await read(new URL(`Goods/Good.${meals.waterGood}.blueprint.json`,vanilla))).GoodSpec;
  const quench=water.ConsumptionEffects.filter(e=>e.NeedId==='Thirst');
  if(quench.length!==1||!(quench[0].Points>0)||!(thirst.DailyDelta<0))throw new Error('Hospital water needs one Thirst effect and a decaying native Thirst');
  value.HospitalPantrySpec={FoodCapacityPerGood:meals.foodUnitsPerGood,WaterGoodId:meals.waterGood,
    WaterCapacity:Math.ceil(care.patientCapacity*meals.zombieNeedMultiplier*-thirst.DailyDelta*meals.waterDays/quench[0].Points),
    LowStockUnits:meals.lowStockUnits};
  value.GoodConsumingBuildingSpec={ConsumedGoods:care.suppliesPerHour,FullInventoryWorkHours:care.supplyBufferHours};
  value.PoweredGoodConsumingBuildingSpec={};
  value.EntererNeedSuspendingBuildingSpec=bed.EntererNeedSuspendingBuildingSpec;
  // Workplace already implements native IStatusHider. Enterer requests one
  // implementation, so an attraction's additional hider would be ambiguous.
  delete value.StatusHidingEnterableSpec;
  value.EnterableIlluminatorSpec={};
  value.RangedEffectBuildingSpec={EffectRadius:care.areaRadius};
  value.HospitalSpec={WardWorkPosition:xyz([6.5,0,3.5]),RequiredStaff:care.workers,
    NeighborhoodEffect:{NeedId:'PublicHealthcare',PointsPerHour:care.areaPointsPerHour,SatisfyToMaxValue:false}};
  // Ward flue steam while patients are inside (EnterableParticleController:
  // the hospital is not a workshop). Steam does not pollute.
  applyVanillaSmoke(value,await sceneSmokeRegistration('civic-integration','Hospital',layout),'Hospital');
  await applyNativeBuildingAssembly(value,'Hospital',layout.origin,{goodId:'Water',flowNodes:[],wheelNodes:[]});
  const folder=new URL('Buildings/Wellbeing/Hospital/',data);
  for(const suffix of ['Model','ConstructionStage0.Model'])
    await copyFile(new URL(`outputs/civic-integration/Data/Buildings/Wellbeing/Hospital/Hospital.IronTeeth.${suffix}.timbermesh`,root),
      new URL(`Hospital.IronTeeth.${suffix}.timbermesh`,folder));
}

// Hospital description and the panel/status rows used by Scripts/Hospital*.cs;
// create_frontier_expansion_content.mjs writes them with the other rows.
export const HOSPITAL_DESCRIPTION=`Houses 30 patients, who stay admitted until cured and are fed and watered from its own stock. An assigned crew of six and ${careHp.toLocaleString('en-US')} hp treat injury 80% faster than a medical bed, plus chipped teeth, badwater contamination and 10-day radiation decontamination, day and night. Uses medicine, water and extract while treating or attended. Attending, supplied staff grant neighborhood care up to +2 wellbeing within ten cells.`;
export const HOSPITAL_LOCALIZATION=[
  ['DeepFrontier.Hospital.Panel.Title','Hospital'],
  ['DeepFrontier.Hospital.Panel.Patients','Patients admitted: {0} / {1} beds'],
  ['DeepFrontier.Hospital.Panel.Crew','Ward crew: {0} / {1} ({2} attending the ward)'],
  ['DeepFrontier.Hospital.Panel.Meals','Patient meals: {0} food, {1} water ({2})'],
  ['DeepFrontier.Hospital.Panel.Fed','Patients fed: {0} / {1}'],
  ['DeepFrontier.Hospital.Panel.UnderConstruction','Under construction'],
  ['DeepFrontier.Hospital.Panel.Paused','Paused'],
  ['DeepFrontier.Hospital.Panel.NoPower','Care stopped: check power and building warnings'],
  ['DeepFrontier.Hospital.Panel.NoCrew','Closed: no ward crew assigned'],
  ['DeepFrontier.Hospital.Panel.NoMeals','Closed: a patient is starving or dehydrated and the food or water stock is empty'],
  ['DeepFrontier.Hospital.Panel.NoSupplies','Waiting for medicine, water and extract'],
  ['DeepFrontier.Hospital.Panel.Treating','Patients stay until cured of injury, chipped teeth, badwater contamination and radiation. Treatment: {0}% (crew strength)'],
  ['DeepFrontier.Hospital.Panel.AreaActive','Neighborhood care active (+2 wellbeing)'],
  ['DeepFrontier.Hospital.Panel.AreaInactive','Neighborhood care inactive'],
  ['DeepFrontier.Hospital.Status.MealsLow','Patient food or water is running low.'],
  ['DeepFrontier.Hospital.Status.MealsLow.Short','Low patient meals'],
  ['DeepFrontier.Hospital.Status.MealsOut','No food or water for patients: hungry or thirsty patients will be sent out to eat.'],
  ['DeepFrontier.Hospital.Status.MealsOut.Short','No patient meals'],
];

export async function authorHospitalNeed() {
  const need=await read(new URL('Needs/Need.Beaver.RooftopTerrace.blueprint.json',vanilla));
  Object.assign(need.NeedSpec,{Id:'PublicHealthcare',BackwardCompatibleIds:[],Order:36,DailyDelta:-.5,
    DisplayNameLocKey:'Need.PublicHealthcare.DisplayName',FavorableWellbeing:care.areaWellbeingPoints});
  await writeFile(new URL('Needs/Need.Beaver.PublicHealthcare.blueprint.json',data),JSON.stringify(need,null,2)+'\n');
  const path=new URL('NeedCollections/NeedCollection.IronTeeth.blueprint.json',data),collection=await read(path);
  if(collection.NeedCollectionSpec['Needs#append'].includes('PublicHealthcare'))throw new Error('PublicHealthcare is already authored');
  collection.NeedCollectionSpec['Needs#append'].push('PublicHealthcare');
  await writeFile(path,JSON.stringify(collection,null,2)+'\n');
}
