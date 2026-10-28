import {readFile} from 'node:fs/promises';
const catalog=JSON.parse(await readFile(new URL('./research_content.json',import.meta.url),'utf8'));
const b=catalog.buildings[0],r=catalog.recipes[0];
const amounts=rows=>rows.map(([id,n])=>`${n} ${id}`).join('; ');
const source='tools/research_content.json; tools/research_building_content.mjs';
export function updateResearchBuilding(rows,headers){
  const row=rows.find(row=>row[0]==='B043');
  if(!row||row[1]!==b.name)throw Error('Missing stable Materials Laboratory row');
  const fields={
    'Building ID':'B043','Building / Machine':b.name,'Infobox':'Workplace','Categories':'Science; Deep Frontier',
    'Faction':'Iron Teeth','Buildable?':'Yes','Availability':'Authored build menu',
    'Width':b.size[0],'Length':b.size[1],'Footprint':`${b.size[0]}x${b.size[1]}`,'Footprint tiles':b.size[0]*b.size[1],'Height':b.size[2],
    'Workers':b.workers,'Power demand (hp)':b.powerDemandHp,'Power output (hp)':0,'Power role':'Consumer',
    'Science unlock':b.scienceUnlock,'Bot unlock':'n.a.','Build materials':amounts(b.cost),
    'Flags':'Sparse occupancy; 9 terrace support cells; 7 adaptive rail openings','Recipe names':r.name,
    'Source':source,'Data status':catalog.status,'Stage':'4. Wonder transition','Role':b.description,
    'Stackable':'Yes, clear layer-2 terrace','Stacking rule':'Native support; no artificial layer cap',
    'Conveyor-only solids':'No','Pipe ports':'None; dry research process','Power mode':'Grid',
    'Unlock prerequisites':'Concrete, gear and metal production; 12,000 science',
    'Inputs':amounts(r.ingredients),'Outputs':`${r.science} science per ${r.hours} working hours`,
    'Waste / side effect':'Samples consumed','Placement':'Supported ground; sparse open deck volumes',
    'Player cue':'Build reliable concrete and gear supply before scaling research','Status':catalog.status,
    'Notes':'No new research-item good. Native blueprint and original animated art; production/reload evidence tracked in STATUS.'
  };
  for(const [i,h] of headers.entries()){
    if(!Object.hasOwn(fields,h))throw Error('Missing research field: '+h);
    row[i]=fields[h];
  }
}
export const researchRecipe=[r.id,b.name,'Iron Teeth',r.name,amounts(r.ingredients),`${r.science} Science`,r.hours,b.powerDemandHp,0,'Consumer',b.workers,
  'None',`${r.cyclesCapacity} batches: ${amounts(r.ingredients.map(([id,n])=>[id,n*r.cyclesCapacity]))}`,source,
  JSON.stringify(r.ingredients),'SciencePoints; not a stockpile good',r.science,r.hours*60,amounts(r.ingredients),r.ingredients.reduce((sum,[,n])=>sum+n,0),
  'None','4. Wonder transition','400 science per working hour at full productivity',catalog.status];
export const researchSource=['Materials Laboratory',source,'Canonical native science recipe and authored geometry','2026-10-20',
  '12,000 science unlock; 600 hp demand; zero hp output; four workers; Gear, Concrete and MetalBlock samples. Paper is not an Iron Teeth ingredient.',
  'DeepFrontier',catalog.status,'Dimensions; science; hp; workers; costs; sample recipe; native navigation'];
export const styleDependency=['D017','New Building Styles [ModContest1]','Downloaded; required Redic.NewStyles >= 0.1',
  'Workshop 3723883597; root manifest; minimum game 1.0.0.0','Iron Teeth architectural style reference and added building styles',
  'Orange plaster, dark native timber, teal roof planks and detailed native window atlases',
  'No replacement texture pack; exact package uses shipped material resources','None declared',
  'Required source dependency. Deep Frontier deck rails reuse the native Folktails Double Lodge handrail and post geometry with original UVs.',
  'https://steamcommunity.com/sharedfiles/filedetails/?id=3723883597','Exact downloaded manifest and inspected material collection',
  'Official package and in-game visual verification tracked in STATUS'];
export const styleSource=['New Building Styles and native housing rails','https://steamcommunity.com/sharedfiles/filedetails/?id=3723883597',
  'Downloaded package and native 1.1.2.8 model/material data','2026-10-20',
  'Redic.NewStyles 0.1 required. No custom replacement texture images. Rail source: DoubleLodge.Folktails.Model, upstairs entrance.',
  '3723883597','Source inspected; style render/export pass in progress','Dependency version; native material paths; rail geometry and UVs'];
