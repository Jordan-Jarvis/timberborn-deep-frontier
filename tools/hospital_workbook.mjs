import {readFile} from 'node:fs/promises';
const root=new URL('../',import.meta.url);
const read=async p=>JSON.parse(await readFile(new URL(p,root),'utf8'));
const name=id=>id.replace(/([a-z])([A-Z])/g,'$1 $2');
const amounts=goods=>goods.map(g=>`${g.Amount} ${name(g.Id)}`).join('; ');
const b=await read('src/DeepFrontier/Data/Buildings/Wellbeing/Hospital/Hospital.IronTeeth.blueprint.json');
const p=(await read('tools/frontier_progression.json')).hospital;
const size=b.BlockObjectSpec.Size;
const layout=(await read('tools/civic-layouts.json')).Hospital;
const source='tools/frontier_progression.json; src/DeepFrontier/Data/Buildings/Wellbeing/Hospital; src/DeepFrontier/Scripts/Hospital.cs';
const inputs=p.suppliesPerHour.map(g=>`${g.GoodPerHour} ${name(g.GoodId)}`).join('; ');
export const hospitalBuildingUpdates=new Map([['B011',{
  'Infobox':'Native treatment attraction and workplace','Width':size.X,'Length':size.Y,'Footprint':`${size.X}x${size.Y}`,
  'Footprint tiles':size.X*size.Y,'Height':size.Z,'Workers':b.WorkplaceSpec.MaxWorkers,
  'Power demand (hp)':b.MechanicalNodeSpec.PowerInput,'Power output (hp)':b.MechanicalNodeSpec.PowerOutput,'Power role':'Consumer',
  'Science unlock':b.BuildingSpec.ScienceCost,'Bot unlock':'Beaver staff only','Build materials':amounts(b.BuildingSpec.BuildingCost),
  'Flags':`${p.patientCapacity} patients; staff use no patient slots; player-placed paths; ${layout.nodes.length} authored access cells; ${b.PlatformDeckSpec.Openings.length} decorative rail openings; native F mirroring`,
  'Recipe names':'None; native per-hour supply consumption','Source':source,'Data status':p.requirementStatus,
  'Role':'Treat injuries, chipped teeth and badwater contamination; staffed neighborhood care',
  'Stackable':'Clear 4x3 roof construction area','Stacking rule':'Clear 4x3 roof area at layer 6; player-placed paths; native support/collision; no layer cap',
  'Conveyor-only solids':'No','Pipe ports':'Water inventory; pipe transfer unverified','Power mode':'Grid',
  'Unlock prerequisites':`${p.scienceUnlock} science; concrete, treated planks, metal, gears; medicine, water and extract deliveries`,
  'Inputs':`${inputs} per operating hour; ${p.supplyBufferHours}-hour buffer`,
  'Outputs':'Native condition recovery; Public Healthcare neighborhood wellbeing','Waste / side effect':'None',
  'Placement':'Two ward wings and a central pavilion; four one-tile doors connect through enclosed interiors to player-built paths at 0/2/4/6',
  'Player cue':'Care panel shows patient occupancy, attending staff and care availability','Status':p.requirementStatus,
  'Notes':`Full staff and power target 1.8x Medical Bed injury recovery during treatment. Native treatment replaces passive healing on those ticks. ${p.areaRadius}-cell native area radius; +${p.areaWellbeingPoints} wellbeing cap. ${p.supplyPolicy} ${p.balanceStatus}`
}]]);
// Medical Food was retired on 2026-10-30 (bricks pass, tools/content_policy.json migratedGoods: saves map it to Canned Fish).
export const hospitalItemUpdates=new Map([['I012',{
  'Source / recipe':'Retired','Consumed by':'None','Source':'tools/content_policy.json migratedGoods',
  'Data status':'Retired 2026-10-30; saved stock loads as Canned Fish','Primary uses':'None',
  'Notes':'Removed: a plain Hunger 0.3 food with no medical effect. The Hospital uses Medicine.'
}],['I011',{'Primary uses':'Hospital operating supply; Technical School reactor course','Consumed by':'Hospital; Technical School',
  'Notes':'Hospital consumes 2 per operating hour with water and extract; reactor studies use it as a course supply.'}]]);
export const hospitalProgressionUpdates=new Map([['G005',{
  'Player goal':'Provide large-scale hospital care','Required buildings':'Hospital; medicine production and water supply',
  'Science range':p.scienceUnlock,
  'Required items':amounts(b.BuildingSpec.BuildingCost),
  'Infrastructure gate':`${b.MechanicalNodeSpec.PowerInput} hp; ${p.workers} staff; ${inputs} per operating hour`,
  'Suggested trigger':'Injured, chipped-tooth or contaminated workers need more care capacity',
  'Why now':'Thirty patient places and faster full-staff injury recovery support a larger industrial colony',
  'Player-facing cue':'Hospital care panel and native health needs; neighborhood benefit requires operating supplies',
  'Status':p.requirementStatus,'Data status':p.balanceStatus
}]]);
export const hospitalTransport=['T018','Iron Teeth','Hospital supplies and access','Native hauling; player-placed deck paths',
  'Medicine; Water; Extract',null,b.MechanicalNodeSpec.PowerInput,'Ground entrance; native power shaft; six attending staff',
  'Four doors at 0/2/4/6; galleries at 2/4; clear 4x3 roof area at 6',`${p.areaRadius}-cell native area effect`,
  'Sustain ward care and nearby wellbeing',`${p.supplyBufferHours}-hour input buffer; actual attending staff`,
  'Pipes and belts require runtime checks','Native Enterable, Attraction, GoodConsumingBuilding and RangedEffectBuilding',
  'Native support and collision; no artificial layer cap',source,p.requirementStatus];
export const hospitalSource=['Hospital reference and native care',source,'Exact building data, native treatment math and operating supplies',
  '2026-10-21','Two-wing exterior revision; player-built deck paths; separate patient/staff capacity; exact native condition effects; initial economy balance.',
  'DeepFrontier',p.requirementStatus,'Dimensions; costs; hp; science; staff; treatment; supply buffer; multi-level access'];
