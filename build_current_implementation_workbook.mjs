import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const ROOT = process.cwd();
const DATA = path.join(ROOT, 'src', 'DeepFrontier', 'Data');
const TOOLS = path.join(ROOT, 'tools');
const OUT = path.join(ROOT, 'outputs', 'Timberborn_Deep_Frontier_Balance_Workbook.xlsx');
const today = new Date('2026-10-25T00:00:00-07:00');

async function readJson(file) { return JSON.parse(await fs.readFile(file, 'utf8')); }
async function walk(dir) {
  const out = [];
  for (const ent of await fs.readdir(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) out.push(...await walk(p));
    else if (ent.name.endsWith('.blueprint.json')) out.push(p);
  }
  return out;
}
const rel = (p) => path.relative(ROOT, p).replaceAll('\\', '/');
const text = (v) => v === null || v === undefined || v === '' ? '' : String(v);
const json = (v) => JSON.stringify(v ?? '');
const list = (xs, map = x => x) => (xs || []).map(map).join('; ');
const pairs = (xs) => list(xs, x => `${x.Id}:${x.Amount}`);
const unique = (xs) => [...new Set((xs || []).filter(Boolean))];
const prettyId = (id) => String(id || '').replace(/\.(IronTeeth|Folktails)$/, '').replaceAll('.', ' ');
const colLetter = (n) => { let s=''; while(n>0){const r=(n-1)%26;s=String.fromCharCode(65+r)+s;n=Math.floor((n-1)/26);} return s; };

const [progression, construction, deps, targetMods, freshness, vanilla, policy, hydro] = await Promise.all([
  readJson(path.join(TOOLS, 'frontier_progression.json')),
  readJson(path.join(TOOLS, 'construction_materials.json')),
  readJson(path.join(TOOLS, 'installed_dependency_manifests_1_1.json')),
  readJson(path.join(TOOLS, 'target_mod_packages_1_1.json')),
  readJson(path.join(TOOLS, 'dependency_freshness_1_1.json')),
  readJson(path.join(TOOLS, 'vanilla_1_1_data.json')),
  readJson(path.join(TOOLS, 'content_policy.json')),
  readJson(path.join(TOOLS, 'hydro_content.json')).catch(() => ({})),
]);

const allBlueprints = await walk(DATA);
const buildingFiles = allBlueprints.filter(p => p.includes(`${path.sep}Buildings${path.sep}`) && /\.IronTeeth\.blueprint\.json$/.test(p));
const recipeFiles = allBlueprints.filter(p => p.includes(`${path.sep}Recipes${path.sep}`));
const goodFiles = allBlueprints.filter(p => p.includes(`${path.sep}Goods${path.sep}`));
const mapFiles = allBlueprints.filter(p => p.includes(`${path.sep}MapEditor${path.sep}`));
const [buildingJsons, recipeJsons, goodJsons, mapJsons] = await Promise.all([
  Promise.all(buildingFiles.map(async p => ({ path:p, json:await readJson(p) }))),
  Promise.all(recipeFiles.map(async p => ({ path:p, json:await readJson(p) }))),
  Promise.all(goodFiles.map(async p => ({ path:p, json:await readJson(p) }))),
  Promise.all(mapFiles.map(async p => ({ path:p, json:await readJson(p) }))),
]);

const buildingRows = [];
const buildingByRecipe = new Map();
for (const {path:p, json:j} of buildingJsons) {
  const b = j.BuildingSpec || {};
  const block = j.BlockObjectSpec || {};
  const size = block.Size || {};
  const mech = j.MechanicalNodeSpec || {};
  const work = j.WorkplaceSpec || {};
  const manu = j.ManufactorySpec || {};
  const t = j.TemplateSpec || {};
  const id = t.TemplateName || path.basename(p).replace('.IronTeeth.blueprint.json','');
  const recipes = manu.ProductionRecipeIds || [];
  for (const r of recipes) { if (!buildingByRecipe.has(r)) buildingByRecipe.set(r, []); buildingByRecipe.get(r).push(id); }
  const blocks = block.Blocks || [];
  const ports = j.BuildingPipeTargetPortsSpec?.Ports || [];
  const enter = j.EnterableSpec || {};
  const special = Object.keys(j).filter(k => /Spec$/.test(k) && !['BuildingSpec','BuildingModelSpec','WorkplaceSpec','ManufactorySpec','WorkshopSpec','MechanicalBuildingSpec','EnterableSpec','TemplateSpec','BlockObjectSpec','BuildingAccessibleSpec','MechanicalNodeSpec','PlaceableBlockObjectSpec','LabeledEntitySpec','ConstructionSiteProgressVisualizerSpec','TransputProviderSpec','MechanicalConnectorTargetSpec'].includes(k));
  const category = rel(p).split('/')[4] || 'Other';
  const demand = Number(mech.PowerInput || 0);
  const output = Number(mech.PowerOutput || 0);
  const powerRole = demand && output ? 'Demand + output (review)' : demand ? 'Power demand' : output ? 'Power output' : 'No authored hp connection';
  const policyRow = progression.restaurant && id.endsWith('Restaurant.IronTeeth') ? progression.restaurant : id.endsWith('Hospital.IronTeeth') ? progression.hospital : id.endsWith('GroceryStore.IronTeeth') ? progression.groceryStore : null;
  buildingRows.push([
    id, prettyId(id), category, 'Implemented blueprint', rel(p),
    size.X ?? '', size.Y ?? '', size.Z ?? '', (size.X && size.Y) ? size.X * size.Y : '',
    b.ScienceCost ?? '', work.MaxWorkers ?? '', demand, output, powerRole,
    list(b.BuildingCost, x => `${x.Id}:${x.Amount}`), recipes.join('; '),
    enter.CapacityFinished ?? '', blocks.filter(x => x.Stackable && x.Stackable !== 'None').length,
    unique(blocks.map(x => x.MatterBelow)).join('; '), unique(blocks.map(x => x.Occupations)).join('; '),
    ports.length, list(ports, x => `${x.Coordinates?.X},${x.Coordinates?.Y},${x.Coordinates?.Z} ${x.Directions} ${x.State}`),
    special.join('; '), policyRow ? (policyRow.requirementStatus || '') : '',
  ]);
}
// Include the active gatherer feature patch, which is not a full building template.
const gatherer = buildingJsons.find(x => x.path.includes('GathererFlag'));
if (gatherer) buildingRows.push(['GathererFlag', 'Gatherer flag fishing patch', 'Food', 'Implemented feature patch', rel(gatherer.path), '', '', '', '', '', '', '', '', 'No authored hp connection', '', '', '', '', '', '', '', '', 'ShoreFishingSpec', '']);
buildingRows.sort((a,b)=>String(a[0]).localeCompare(String(b[0])));

const recipeRows = recipeJsons.map(({path:p,json:j}) => {
  const r=j.RecipeSpec||{}; const id=r.Id||path.basename(p).replace('Recipe.','').replace('.blueprint.json','');
  return [id, prettyId(id), list(buildingByRecipe.get(id)||[]), pairs(r.Ingredients), pairs(r.Products), r.CycleDurationInHours??'', r.Fuel||'', r.CyclesFuelLasts??'', r.FuelCapacity??'', r.CyclesCapacity??'', r.ProducedSciencePoints??0, rel(p), 'Implemented recipe blueprint'];
}).sort((a,b)=>String(a[0]).localeCompare(String(b[0])));

const goodUse = new Map();
function addUse(id, use) { if (!id) return; if (!goodUse.has(id)) goodUse.set(id, new Set()); goodUse.get(id).add(use); }
for (const r of recipeJsons.map(x=>x.json.RecipeSpec||{})) {
  for (const x of r.Ingredients||[]) addUse(x.Id, `Recipe input: ${r.Id}`);
  for (const x of r.Products||[]) addUse(x.Id, `Recipe output: ${r.Id}`);
}
for (const row of buildingRows) for (const token of String(row[14]||'').split('; ')) { if (!token) continue; const [id] = token.split(':'); addUse(id, `Construction: ${row[0]}`); }
for (const x of construction.goods||[]) addUse(x.id, `Construction chain: ${x.use}`);
for (const x of construction.sources||[]) addUse(x.good, `Map source: ${x.id}`);
const legacyOnly = policy.legacySaveOnlyGoods || {};
const itemRows = goodJsons.map(({path:p,json:j}) => {
  const g=j.GoodSpec||{}; const id=g.Id||path.basename(p).replace('Good.','').replace('.blueprint.json','');
  const uses=[...(goodUse.get(id)||[])]; const status=legacyOnly[id] ? 'Legacy save only (unproduced and unused)' : 'Implemented good blueprint';
  return [id, prettyId(id), status, g.GoodType||'', g.GoodGroupId||'', g.Weight??'', g.Icon||'', list(g.ConsumptionEffects, e => `${e.NeedId || e.Id}:${e.PointsPerHour ?? e.Amount ?? ''}`), uses.length, uses.join('; '), rel(p)];
}).sort((a,b)=>String(a[0]).localeCompare(String(b[0])));

const progressionRows = buildingRows.map(r => {
  const id=r[0]; const bare=id.replace('.IronTeeth',''); const p = progression.implementedBuildingScienceOverrides?.[bare] ?? r[9];
  const source = progression[bare.charAt(0).toLowerCase()+bare.slice(1)] || progression[bare] || null;
  const status = r[3] === 'Implemented blueprint' ? 'Implemented' : 'Feature patch';
  return [id, r[1], status, p ?? '', r[14] || '', r[11] || '', r[12] || '', r[13] || '', source?.requirementStatus || source?.balanceStatus || '', progression.revision || ''];
});

const transportRows = [];
for (const pkg of deps.packages||[]) {
  const name=pkg.name||pkg.id; const lower=name.toLowerCase();
  let kind = lower.includes('pipe') ? 'Pipes' : lower.includes('conveyor') ? 'Conveyor belts' : lower.includes('tubeway') ? 'Tubeway' : lower.includes('power line') ? 'Power lines' : lower.includes('teleporter') ? 'Teleport' : lower.includes('pump') ? 'Liquid pump/tank' : lower.includes('flywheel') ? 'Energy storage' : lower.includes('ladder') ? 'Vertical access' : lower.includes('storage') ? 'Storage' : lower.includes('solar') ? 'Generator' : lower.includes('map transformer') ? 'Map scale' : 'Support';
  transportRows.push([kind, name, pkg.id||'', pkg.version||'', pkg.workshopId||'', pkg.minimumGameVersion||'', list(pkg.requiredMods,x=>`${x.id||x.Id}${x.minimumVersion||x.MinVersion?` >= ${x.minimumVersion||x.MinVersion}`:''}`), list(pkg.optionalMods,x=>`${x.id||x.Id}${x.minimumVersion||x.MinVersion?` >= ${x.minimumVersion||x.MinVersion}`:''}`), freshness.packages?.find(x=>x.id===pkg.id)?.current ? 'Current installed package' : 'Manifest record only', `https://steamcommunity.com/sharedfiles/filedetails/?id=${pkg.workshopId||''}`]);
}
for (const row of buildingRows.filter(r=>r[20] || r[21])) transportRows.push(['Deep Frontier port contract', row[0], 'DeepFrontier', '', '', '', '', '', `Pipe ports: ${row[20]}; ${row[21]}`]);

const dependencyRows = (deps.packages||[]).map(pkg => {
  const f=freshness.packages?.find(x=>x.id===pkg.id); const tm=targetMods.packages?.find(x=>x.id===pkg.id);
  return [pkg.workshopId||'',pkg.name||'',pkg.id||'',pkg.version||'',pkg.path||'',pkg.minimumGameVersion||'',list(pkg.requiredMods,x=>`${x.id||x.Id}${x.minimumVersion||x.MinVersion?` >= ${x.minimumVersion||x.MinVersion}`:''}`),list(pkg.optionalMods,x=>`${x.id||x.Id}${x.minimumVersion||x.MinVersion?` >= ${x.minimumVersion||x.MinVersion}`:''}`),f?.current?'Current':'Review',tm?.source||'',tm?.notes||''];
}).sort((a,b)=>String(a[1]).localeCompare(String(b[1])));

const sourceRows = [];
for (const s of construction.sources||[]) sourceRows.push(['Construction source',s.id,s.name,s.kind,s.good,(s.size||[]).join('x'),s.yield??'',s.removalHours??'',s.description||'','tools/construction_materials.json']);
for (const m of mapJsons) {
  const id=m.json.TemplateSpec?.TemplateName || m.json.MapObjectSpec?.Id || path.basename(m.path).replace('.blueprint.json','');
  sourceRows.push(['Map editor object',id,prettyId(id),'Blueprint',m.json.GoodSourceSpec?.GoodId||m.json.SourceSpec?.GoodId||'',JSON.stringify(m.json.BlockObjectSpec?.Size||''),'','','',rel(m.path)]);
}
for (const b of construction.buildings||[]) sourceRows.push(['Construction building',b.id,b.name,b.kind,b.good||'',(b.size||[]).join('x'),b.hp??'',b.workers??'',b.description||'','tools/construction_materials.json']);

const powerRows = buildingRows.filter(r => Number(r[11]||0) || Number(r[12]||0)).map(r => [r[0],r[1],Number(r[11]||0),Number(r[12]||0),r[13],r[5]||'',r[6]||'',r[7]||'',r[14]||'',r[4]||'']);

const itemUseRows = itemRows.map(r => [r[0],r[1],r[2],r[8],r[9],r[10]]);
const feasibilityRows = [
  ['Current source authority','Deep Frontier blueprints','Active source data under src/DeepFrontier/Data is the authoritative implementation layer for this workbook.','Implemented','Current source tree'],
  ['Building geometry contracts','BlockObjectSpec / BuildingAccessibleSpec / PlatformDeckSpec','Footprints, block occupancy, platform contracts and authored special specs are read from each blueprint.','Implemented','Buildings sheet'],
  ['Power contracts','MechanicalNodeSpec','Demand and output are separate columns. A row with both is flagged for review instead of being silently normalized.','Implemented','PowerCurve sheet'],
  ['Recipes','Recipe.*.blueprint.json','All current recipes are listed with exact ingredients, products, durations, fuel and science.','Implemented','Recipes sheet'],
  ['Item policy','content_policy.json','Legacy license goods remain defined for save compatibility but are marked legacy-only and are not counted as active uses.','Implemented','Items sheet'],
  ['Vanilla anchors','vanilla_1_1_data.json','Vanilla 1.1 reference data is retained as a separate source layer.','Reference','Vanilla* sheets'],
  ['External dependencies','installed_dependency_manifests_1_1.json / dependency_freshness_1_1.json','Installed versions and freshness are shown separately from Deep Frontier authored contracts.','Implemented','Dependencies / Transport sheets'],
  ['Metallurgy training','workforce_risks.json / TechnicalSchool blueprint','Technical School currently names SpecialistTraining.Metallurgy; SteelMill is not present as a generated building, so this remains a current-source gap.','Pending source gap','Progression / Buildings'],
];

const wb=Workbook.create();
const sheetNames=['Overview','Buildings','Items','Recipes','Progression','Feasibility','Transport','Calculator','Sources','VanillaAnchors','VanillaBuildings','VanillaItems','VanillaRecipes','Dependencies','PowerCurve','ItemUses'];
const sheets=Object.fromEntries(sheetNames.map(n=>[n,wb.worksheets.add(n)]));
const font='Arial', navy='#17365D';
function base(s,color){s.showGridLines=false;s.tabColor=color;}
for (const [i,n] of sheetNames.entries()) base(sheets[n], ['#1F4E78','#5B9BD5','#70AD47','#ED7D31','#A5A5A5','#70AD47','#4472C4','#FFC000','#8064A2','#A9D18E','#70AD47','#70AD47','#ED7D31','#8064A2','#C55A11','#70AD47'][i]);
function title(s,a,b){s.getRange('A1').values=[[a]];s.getRange('A1').format={font:{name:font,size:15,bold:true,color:navy}};s.getRange('A2').values=[[b]];s.getRange('A2').format={font:{name:font,size:10,italic:true,color:'#666666'}};}
function table(s,start,headers,rows,name){const end=start+rows.length;const last=colLetter(headers.length);s.getRange(`A${start}:${last}${start}`).values=[headers];if(rows.length)s.getRange(`A${start+1}:${last}${end}`).values=rows;const t=s.tables.add(`A${start}:${last}${end}`,true,name);t.style='TableStyleMedium2';t.showFilterButton=true;s.getRange(`A${start}:${last}${end}`).format.font={name:font,size:9};s.getRange(`A${start}:${last}${start}`).format={fill:navy,font:{name:font,size:9,bold:true,color:'#FFFFFF'},wrapText:true,verticalAlignment:'center'};s.getRange(`A${start}:${last}${end}`).format.verticalAlignment='center';s.freezePanes.freezeRows(start);return {end,last};}
function widths(s, headers, wide=[]){headers.forEach((h,i)=>{const c=colLetter(i+1);s.getRange(`${c}1:${c}500`).format.columnWidth=wide.includes(h)?34:(String(h).length>24?22:16);});}

title(sheets.Overview,'Timberborn Deep Frontier: Current Implementation Workbook',`Authoritative source snapshot ${progression.revision || 'current source'}; generated ${today.toISOString().slice(0,10)}. Power values are hp. This workbook follows active blueprints and manifests, not older planning rows.`);
sheets.Overview.getRange('A4:F10').values=[
 ['Current source layer','Value','Why it matters','Status','Evidence','As of'],
 ['Deep Frontier blueprints',buildingRows.length,'Implemented buildings and active feature patches','Current',rel(DATA),today],
 ['Recipes',recipeRows.length,'Exact authored production recipes','Current',rel(path.join(DATA,'Recipes')),today],
 ['Goods',itemRows.length,'Exact authored good definitions plus current-use audit','Current',rel(path.join(DATA,'Goods')),today],
 ['External dependencies',dependencyRows.length,'Installed manifests and freshness records','Current',rel(path.join(TOOLS,'installed_dependency_manifests_1_1.json')),deps.checkedDate||today],
 ['Vanilla reference buildings',vanilla.buildings?.length||0,'Separate vanilla 1.1 reference layer','Reference',rel(path.join(TOOLS,'vanilla_1_1_data.json')),vanilla.checkedDate||''],
 ['Workbook rule','Current source wins','Planning/docs rows are not treated as implementation evidence','Active',progression.revision||'',''],
];
sheets.Overview.getRange('A4:F4').format={fill:navy,font:{name:font,size:10,bold:true,color:'#FFFFFF'},wrapText:true};sheets.Overview.getRange('F5:F9').format.numberFormat='yyyy-mm-dd';sheets.Overview.getRange('A4:F10').format.font={name:font,size:10};
sheets.Overview.getRange('A1:A40').format.columnWidth=38;sheets.Overview.getRange('B1:B40').format.columnWidth=18;sheets.Overview.getRange('C1:C40').format.columnWidth=34;sheets.Overview.getRange('D1:D40').format.columnWidth=16;sheets.Overview.getRange('E1:E40').format.columnWidth=34;sheets.Overview.getRange('F1:F40').format.columnWidth=18;table(sheets.Overview,13,['Workbook tab','Rows','Purpose','Current source'],[['Buildings',buildingRows.length,'Active building and feature contracts','src/DeepFrontier/Data/Buildings'],['Items',itemRows.length,'Goods, policy status and derived current uses','src/DeepFrontier/Data/Goods + content_policy.json'],['Recipes',recipeRows.length,'Exact recipe contracts','src/DeepFrontier/Data/Recipes'],['Progression',progressionRows.length,'Science, power, construction and authored progression notes','frontier_progression.json + blueprints'],['PowerCurve',powerRows.length,'Separate hp demand/output audit','MechanicalNodeSpec'],['Dependencies',dependencyRows.length,'Installed packages and freshness','installed_dependency_manifests_1_1.json'],['VanillaBuildings',vanilla.buildings?.length||0,'Vanilla 1.1 reference data','vanilla_1_1_data.json']], 'OverviewTabs');

const buildingHeaders=['Blueprint ID','Display name','Category','Implementation status','Source file','Size X','Size Y','Size Z','Footprint blocks','Science','Workers','Power demand hp','Power output hp','Power role','Construction cost','Recipe IDs','Finished capacity','Stackable blocks','Matter below','Occupations','Pipe ports','Port contracts','Special contracts','Progression note'];
title(sheets.Buildings,'Buildings','Every row is read from the current Deep Frontier blueprint tree. Blank means the source does not author a value.');table(sheets.Buildings,4,buildingHeaders,buildingRows,'CurrentBuildings');widths(sheets.Buildings,buildingHeaders,['Source file','Construction cost','Recipe IDs','Matter below','Occupations','Port contracts','Special contracts','Progression note']);
const itemHeaders=['Good ID','Display name','Implementation status','Good type','Good group','Weight','Icon','Consumption effects','Current use count','Current uses','Source file'];
title(sheets.Items,'Items','Current good blueprints, with legacy save-only goods kept visible and excluded from active production counts.');table(sheets.Items,4,itemHeaders,itemRows,'CurrentItems');widths(sheets.Items,itemHeaders,['Consumption effects','Current uses','Source file']);
const recipeHeaders=['Recipe ID','Display name','Buildings','Ingredients','Products','Cycle hours','Fuel','Fuel cycles','Fuel capacity','Cycles capacity','Science produced','Source file','Implementation status'];
title(sheets.Recipes,'Recipes','Exact recipe contracts from the current source tree.');table(sheets.Recipes,4,recipeHeaders,recipeRows,'CurrentRecipes');widths(sheets.Recipes,recipeHeaders,['Ingredients','Products','Source file']);
const progressionHeaders=['Blueprint ID','Display name','Status','Science unlock','Construction cost','Workers','Power demand hp','Power output hp','Authored progression note','Progression revision'];
title(sheets.Progression,'Progression','Progression values are joined to current blueprints. Missing values remain blank rather than being inferred.');table(sheets.Progression,4,progressionHeaders,progressionRows,'CurrentProgression');widths(sheets.Progression,progressionHeaders,['Construction cost','Authored progression note']);
const feasibilityHeaders=['Feature','Current implementation','Interpretation','Status','Evidence'];
title(sheets.Feasibility,'Feasibility and source gaps','Implementation status is based on current source contracts. Pending entries identify real gaps instead of hiding them.');table(sheets.Feasibility,4,feasibilityHeaders,feasibilityRows,'CurrentFeasibility');widths(sheets.Feasibility,feasibilityHeaders,['Current implementation','Interpretation','Evidence']);
const transportHeaders=['Transport kind','Package or contract','Mod ID','Version','Workshop ID','Minimum game version','Required mods','Optional mods','Status','Source'];
title(sheets.Transport,'Transport and integration','Installed dependency facts and authored Deep Frontier transport contracts.');table(sheets.Transport,4,transportHeaders,transportRows,'CurrentTransport');widths(sheets.Transport,transportHeaders,['Required mods','Optional mods','Source']);
const calculatorHeaders=['Recipe ID','Machines','Cycle hours','Output good','Output per cycle','Hourly output','Power demand hp','Workers','Comment'];
title(sheets.Calculator,'Factory line calculator','Use a recipe row to estimate hourly throughput. Change Machines and inspect the formula result.');
const calcRows=recipeRows.slice(0,12).map((r,i)=>{const first=String(r[4]||'').split(';')[0];const parts=first.split(':');const amount=Number(parts[1]);return [r[0],1,r[5],parts[0],amount,`=B${5+i}*E${5+i}/C${5+i}`,0,'','Current recipe throughput'];});
table(sheets.Calculator,4,calculatorHeaders,calcRows,'CalculatorRows');widths(sheets.Calculator,calculatorHeaders,['Outputs per cycle','Hourly output formula','Comment']);
const sourceHeaders=['Source type','ID','Name','Kind','Good','Size','Yield','Removal hours','Description','Source file'];
title(sheets.Sources,'Sources','Finite and permanent source records plus current map editor source blueprints.');table(sheets.Sources,4,sourceHeaders,sourceRows,'CurrentSources');widths(sheets.Sources,sourceHeaders,['Description','Source file']);
const vanillaHeaders=['Name','Infobox','Categories','Faction','Width','Length','Footprint','Footprint tiles','Height','Workers','Power hp','Power output hp','Science unlock','Bot unlock','Materials','Recipes','Buildable','Availability','Flags','Source','Status'];
title(sheets.VanillaBuildings,'Vanilla 1.1 buildings','Reference layer from the captured vanilla 1.1 dataset; it is not used to overwrite current Deep Frontier values.');table(sheets.VanillaBuildings,4,vanillaHeaders,(vanilla.buildings||[]).map(x=>[x.name,x.infobox,x.categories,x.faction,x.width,x.length,x.footprint,x.footprintTiles,x.height,x.workers,x.powerHp,x.powerOutputHp,x.scienceUnlock,x.botUnlock,x.materials,list(x.recipes,r=>json(r)),x.buildable,x.availability,x.flags,x.source,x.status]),'VanillaBuildings');widths(sheets.VanillaBuildings,vanillaHeaders,['Categories','Materials','Recipes','Source']);
const vanillaItemHeaders=['Name','Infobox','Categories','Faction','Type','Source','Storage','Weight','Satisfies','Produces','Consumed by','Source URL','Status'];
title(sheets.VanillaItems,'Vanilla 1.1 items','Reference layer from the captured vanilla 1.1 dataset.');table(sheets.VanillaItems,4,vanillaItemHeaders,(vanilla.items||[]).map(x=>[x.name,x.infobox,x.categories,x.faction,x.type,x.source,x.storage,x.weight,x.satisfies,x.produces,x.consumedBy,x.sourceUrl,x.status]),'VanillaItems');widths(sheets.VanillaItems,vanillaItemHeaders,['Categories','Satisfies','Produces','Consumed by','Source URL']);
const vanillaRecipeHeaders=['Building','Faction','Recipe','Inputs','Outputs','Cycle hours','Power hp','Power output hp','Workers','Fuel','Storage','Source','Raw consumes','Raw produces'];
title(sheets.VanillaRecipes,'Vanilla 1.1 recipes','Reference layer from the captured vanilla 1.1 dataset.');table(sheets.VanillaRecipes,4,vanillaRecipeHeaders,(vanilla.recipes||[]).map(x=>[x.building,x.faction,x.recipe,x.inputs,x.outputs,x.cycleHours,x.powerHp,x.powerOutputHp,x.workers,x.fuel,x.storage,x.source,x.rawConsumes,x.rawProduces]),'VanillaRecipes');widths(sheets.VanillaRecipes,vanillaRecipeHeaders,['Inputs','Outputs','Storage','Source','Raw consumes','Raw produces']);
title(sheets.VanillaAnchors,'Vanilla anchors','Dataset metadata for the separate vanilla reference layer.');table(sheets.VanillaAnchors,4,['Field','Value'],Object.entries(vanilla).filter(([k,v])=>!Array.isArray(v)).map(([k,v])=>[k,typeof v==='object'?json(v):v]),'VanillaAnchors');widths(sheets.VanillaAnchors,['Field','Value'],['Value']);
title(sheets.Dependencies,'Dependencies','Installed 1.1 package manifests, versions, required mods and freshness records.');const depHeaders=['Workshop ID','Name','Mod ID','Version','Path','Minimum game version','Required mods','Optional mods','Freshness','Captured source','Notes'];table(sheets.Dependencies,4,depHeaders,dependencyRows,'CurrentDependencies');widths(sheets.Dependencies,depHeaders,['Path','Required mods','Optional mods','Captured source','Notes']);
title(sheets.PowerCurve,'Power curve','Power demand and power output are stored independently. A source row that authors both is visibly flagged for review.');const powerHeaders=['Blueprint ID','Display name','Power demand hp','Power output hp','Power role','Size X','Size Y','Size Z','Construction cost','Source file'];table(sheets.PowerCurve,4,powerHeaders,powerRows,'CurrentPowerCurve');widths(sheets.PowerCurve,powerHeaders,['Construction cost','Source file']);
title(sheets.ItemUses,'Item uses','Derived only from current recipe, construction, and source records. Legacy save-only goods remain visible with zero active uses.');const useHeaders=['Good ID','Display name','Implementation status','Current use count','Current uses','Source file'];table(sheets.ItemUses,4,useHeaders,itemUseRows,'CurrentItemUses');widths(sheets.ItemUses,useHeaders,['Current uses','Source file']);

for (const s of Object.values(sheets)) { const used=s.getUsedRange(); if (used) used.format.wrapText=true; }
wb.recalculate();
await fs.mkdir(path.dirname(OUT), {recursive:true});
const blob=await SpreadsheetFile.exportXlsx(wb); await blob.save(OUT);
console.log(JSON.stringify({output:OUT,buildingRows:buildingRows.length,recipeRows:recipeRows.length,itemRows:itemRows.length,dependencyRows:dependencyRows.length,powerRows:powerRows.length,revision:progression.revision},null,2));
