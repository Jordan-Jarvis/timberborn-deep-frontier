import fs from 'node:fs/promises';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';
import {aquacultureBuildingUpdates,aquacultureBuildingAdds,aquacultureItemUpdates,aquacultureItemAdds,juvenileRecipeRow,aquacultureRecipeAdds,aquacultureOverview,aquacultureProgression,aquacultureTransport,aquacultureSource,updateAquacultureRows} from './tools/aquaculture_workbook.mjs';
import {hospitalBuildingUpdates,hospitalItemUpdates,medicalFoodRecipe,hospitalProgressionUpdates,hospitalTransport,hospitalSource} from './tools/hospital_workbook.mjs';
import {groceryBuildingUpdates,groceryItemUpdates,grocerySupplyRecipes,groceryProgression,groceryTransport,grocerySource} from './tools/grocery_workbook.mjs';
import {structuralWorkbookRows,structuralSource,hydroSource,hydroBuildingRow} from './tools/structural_workbook.mjs';
import {updateResearchBuilding,researchRecipe,researchSource,styleDependency,styleSource} from './tools/research_workbook.mjs';

const root = 'C:/Users/Jordan/Documents/TimberbornModding';
const outputDir = `${root}/outputs`;
await fs.mkdir(outputDir, { recursive: true });
const vanillaData = JSON.parse(await fs.readFile(`${root}/tools/vanilla_1_1_data.json`, 'utf8'));
const targetModData = JSON.parse(await fs.readFile(`${root}/tools/target_mod_packages_1_1.json`, 'utf8'));
const installedManifestData = JSON.parse(await fs.readFile(`${root}/tools/installed_dependency_manifests_1_1.json`, 'utf8'));
const civicPlan = JSON.parse(await fs.readFile(`${root}/tools/frontier_progression.json`, 'utf8'));
const hydroCatalog = JSON.parse(await fs.readFile(`${root}/tools/hydro_content.json`, 'utf8'));
const restaurantBlueprint = JSON.parse(await fs.readFile(`${root}/src/DeepFrontier/Data/Buildings/Food/Restaurant/Restaurant.IronTeeth.blueprint.json`, 'utf8'));
const restaurantSource = 'src/DeepFrontier/Data/Buildings/Food/Restaurant; tools/frontier_progression.json';
const restaurantStatus = civicPlan.restaurant.requirementStatus;
const cakeGood=JSON.parse(await fs.readFile(`${root}/src/DeepFrontier/Data/Goods/Good.SweetBerryCake.blueprint.json`,'utf8')).GoodSpec;
const restaurantRecipes=[];
for(const id of civicPlan.restaurant.kitchenRecipes) {
  const directory=id==='SweetBerryCake'?'src/DeepFrontier/Data':'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources';
  restaurantRecipes.push(JSON.parse(await fs.readFile(`${root}/${directory}/Recipes/Recipe.${id}.blueprint.json`,'utf8')).RecipeSpec);
}
const itemUseAudit = JSON.parse(await fs.readFile(`${root}/outputs/item-use-audit.json`, 'utf8'));
const dependencyFreshness = JSON.parse(await fs.readFile(`${root}/tools/dependency_freshness_1_1.json`, 'utf8'));
const construction = JSON.parse(await fs.readFile(`${root}/tools/construction_materials.json`, 'utf8'));
const constructionSource = 'tools/construction_materials.json; src/DeepFrontier/Data';
const constructionStatus = 'Factories/quarries 15/17; mixer 79; belts/pipes 81; Power Lines 82/83; detailed pits 86 passed harvesting, native ground/roof rules, animation and reload/depletion. Wider transport/layout checks pending.';
const constructionBlueprints = new Map();
for(const building of construction.buildings) {
  constructionBlueprints.set(building.id,JSON.parse(await fs.readFile(
    `${root}/src/DeepFrontier/Data/Buildings/Metal/${building.id}/${building.id}.IronTeeth.blueprint.json`,'utf8')));
}
const constructionBuildingStatus = new Map([
  ['SandstonePit','5×5×4 reference mesh; native 86 passed ground-only placement, rejected roof paths/platforms, no power node, harvesting/hoist/pause and exact reload/depletion. Test yield 24; authored yield 600.'],
  ['LimestonePit','6×5×4 reference mesh; native 86 passed ground-only placement, rejected roof paths/platforms, no power node, harvesting/hoist/pause and exact reload/depletion. Test yield 24; authored yield 600.'],
  ['StoneCrusher','Native production, shaft power, stairs, deck platforms and reload passed 15/17'],
  ['CementKiln','Native production, shaft power, stairs, deck platforms and reload passed 15/17'],
  ['SandstoneQuarry','Native extraction, access and reload passed 15/17; water stock/reload passed 23'],
  ['LimestoneQuarry','Native extraction, access and reload passed 15/17; water stock/reload passed 23'],
  ['ConcreteMixer','Reference/access/production/reload 79; belts/pipes 81; Power Lines main82/reload83 passed actual 312 hp circuit, interruption and conserved production'],
]);
const goodName = id => id.replace(/([a-z])([A-Z])/g, '$1 $2');
const amountsText = amounts => amounts.map(([id, quantity]) => `${quantity} ${goodName(id)}`).join('; ');
const constructionRecipe = new Map(construction.recipes.map(r => [r.id, r]));

const wb = Workbook.create();
const overview = wb.worksheets.add('Overview');
const buildings = wb.worksheets.add('Buildings');
const items = wb.worksheets.add('Items');
const recipes = wb.worksheets.add('Recipes');
const progression = wb.worksheets.add('Progression');
const feasibility = wb.worksheets.add('Feasibility');
const transport = wb.worksheets.add('Transport');
const calculator = wb.worksheets.add('Calculator');
const sources = wb.worksheets.add('Sources');
const vanilla = wb.worksheets.add('VanillaAnchors');
const vanillaBuildings = wb.worksheets.add('VanillaBuildings');
const vanillaItems = wb.worksheets.add('VanillaItems');
const vanillaRecipes = wb.worksheets.add('VanillaRecipes');
const dependencies = wb.worksheets.add('Dependencies');
const powerCurve = wb.worksheets.add('PowerCurve');
const itemUses = wb.worksheets.add('ItemUses');

const font = 'Arial';
const navy = '#17365D';
const blue = '#D9EAF7';
const gold = '#FFF2CC';
const green = '#E2F0D9';
const gray = '#F2F2F2';

const powerRole = (demand, output) => {
  const d = Number(demand) || 0;
  const o = Number(output) || 0;
  if (d > 0 && o > 0) return 'Review: demand + output';
  if (d > 0) return 'Consumer';
  if (o > 0) return 'Generator';
  return 'Passive / transport';
};

function baseSheet(sheet, tabColor) {
  sheet.showGridLines = false;
  sheet.tabColor = tabColor;
}

function title(sheet, text, subtitle) {
  sheet.getRange('A1').values = [[text]];
  sheet.getRange('A1').format = { font: { name: font, size: 15, bold: true, color: navy } };
  if (subtitle) {
    sheet.getRange('A2').values = [[subtitle]];
    sheet.getRange('A2').format = { font: { name: font, size: 10, italic: true, color: '#666666' } };
  }
}

function writeTable(sheet, startRow, headers, rows, tableName, tabColor) {
  const endRow = startRow + rows.length;
  const endCol = headers.length;
  const colLetter = (n) => {
    let s = '';
    while (n > 0) { const r = (n - 1) % 26; s = String.fromCharCode(65 + r) + s; n = Math.floor((n - 1) / 26); }
    return s;
  };
  const range = `A${startRow}:${colLetter(endCol)}${endRow}`;
  sheet.getRange(`A${startRow}:${colLetter(endCol)}${startRow}`).values = [headers];
  if (rows.length) sheet.getRange(`A${startRow + 1}:${colLetter(endCol)}${endRow}`).values = rows;
  const table = sheet.tables.add(range, true, tableName);
  table.style = 'TableStyleMedium2';
  table.showFilterButton = true;
  sheet.getRange(`A${startRow}:${colLetter(endCol)}${endRow}`).format.font = { name: font, size: 9 };
  sheet.getRange(`A${startRow}:${colLetter(endCol)}${startRow}`).format = {
    fill: navy,
    font: { name: font, size: 9, bold: true, color: '#FFFFFF' },
    wrapText: true,
    verticalAlignment: 'center',
  };
  sheet.getRange(`A${startRow}:${colLetter(endCol)}${endRow}`).format.verticalAlignment = 'center';
  sheet.freezePanes.freezeRows(startRow);
  sheet.tabColor = tabColor;
  return { endRow, endCol, colLetter };
}

baseSheet(overview, '#1F4E78');
baseSheet(buildings, '#5B9BD5');
baseSheet(items, '#70AD47');
baseSheet(recipes, '#ED7D31');
baseSheet(progression, '#A5A5A5');
baseSheet(feasibility, '#70AD47');
baseSheet(transport, '#4472C4');
baseSheet(calculator, '#FFC000');
baseSheet(sources, '#8064A2');
baseSheet(vanilla, '#A9D18E');
baseSheet(vanillaBuildings, '#70AD47');
baseSheet(vanillaItems, '#70AD47');
baseSheet(vanillaRecipes, '#ED7D31');
baseSheet(dependencies, '#8064A2');
baseSheet(powerCurve, '#C55A11');

title(overview, 'Timberborn Deep Frontier: Balance Workbook', 'Planning workbook for Timberborn 1.1.2.8. Vanilla 1.1 data is separated from the proposed mod layer. Power values use hp.');
overview.getRange('A4:F10').values = [
  ['Balance goals', 'Rule', 'Why it matters', 'Editable?', 'Owner', 'Status'],
  ['Natural progression', 'Every major unlock answers a visible colony need and points to the next project.', 'Players should know what to build next without reading an external guide.', 'Yes', 'Design', 'Planning'],
  ['Science pacing', 'Science unlocks capability; materials and infrastructure prove readiness.', 'Prevents a player from rushing a powerful building with science alone.', 'Yes', 'Design', 'Planning'],
  ['Factory scale', 'Large factories require belts, power, workers, storage, and waste handling.', 'Creates logistics challenges without heat or maintenance simulation.', 'Yes', 'Systems', 'Planning'],
  ['Surface first', 'Agriculture, food, healthcare, retail, and recreation mature before deep drilling.', 'Keeps the expansion recognizable as Timberborn.', 'Yes', 'Content', 'Planning'],
  ['Required foundations', 'Use the declared 1.1 foundation mods and validate their APIs.', 'Missing requirements must be explicit; no hidden fallback behavior.', 'Yes', 'Engineering', 'Integration testing'],
  ['Readability', 'Inputs, outputs, power, size, stacking, and gates appear in one row per object.', 'Makes implementation and balancing reviewable.', 'Yes', 'All', 'Planning'],
];
overview.getRange('A4:F4').format = { fill: navy, font: { name: font, size: 10, bold: true, color: '#FFFFFF' }, wrapText: true };
overview.getRange('A4:F10').format.font = { name: font, size: 10 };
overview.getRange('A4:F10').format.borders = { preset: 'outside', style: 'thin', color: '#D9D9D9' };
overview.getRange('A12:E18').values = [
  ['Progression stage', 'Primary question', 'New colony capability', 'Typical player cue', 'Target scale'],
  ['1. Survival', 'Can we reliably feed and water the colony?', 'Food variety, storage, irrigation, basic services', 'A new need appears in the Well-Being panel.', '10–30 beavers'],
  ['2. Productive settlement', 'Can we turn farm output into better food and goods?', 'Mills, bakeries, fertilizer, markets, clinics', 'A bottleneck appears in production statistics.', '30–80 beavers'],
  ['3. Industrial city', 'Can we build dedicated districts?', 'Conveyor factories, substations, hospitals, restaurants', 'A new factory output is visible in the recipe chain.', '80–180 beavers'],
  ['4. Wonder transition', 'Can the colony support a new industrial era?', 'Advanced materials, automation, large logistics', 'A completed wonder unlocks a capability branch.', '180–350 beavers'],
  ['5. Frontier', 'Can we safely expand production and resources?', 'Deep drilling, rare materials, map expansion', 'Survey data reveals a new sector or resource.', '350+ beavers'],
  ['6. Mystery', 'What caused badwater and what happened to humanity?', 'Human facilities, launch program, endgame choices', 'Recovered evidence creates the next objective.', 'Endgame'],
];
overview.getRange('A12:E12').format = { fill: navy, font: { name: font, size: 10, bold: true, color: '#FFFFFF' }, wrapText: true };
overview.getRange('A12:E18').format.font = { name: font, size: 10 };
overview.getRange('A12:E18').format.borders = { preset: 'outside', style: 'thin', color: '#D9D9D9' };
overview.getRange('G4:J12').values = [
  ['Workbook tab', 'Purpose', 'Primary inputs', 'Review question'],
  ['Buildings', 'One row per building or machine.', 'Size, power, workers, gates, ports.', 'Is this building worth its footprint and unlock cost?'],
  ['Items', 'Resources, goods, waste, and special materials.', 'Tier, source, uses, storage, hazard.', 'Does this item have a clear role?'],
  ['Recipes', 'Production chain and throughput targets.', 'Inputs, outputs, cycles, power.', 'Where is the bottleneck?'],
  ['Progression', 'What players do next and why.', 'Science, materials, triggers, cues.', 'Can a player discover the next step?'],
  ['Transport', 'Belts, pipes, lifts, and teleports.', 'Capacity, power, range, requirements.', 'Does logistics remain meaningful?'],
  ['Calculator', 'Quick balance checks for a proposed machine.', 'Count, cycle, output, power, workers.', 'What does one factory line actually require?'],
  ['Dependencies', 'Verified mod package facts and integration assumptions.', 'Version, requirements, costs, recipes, compatibility.', 'Can this dependency be detected and used safely?'],
  ['Feasibility', 'Feature-level engine review.', 'Map authoring, specs, adapters, limits.', 'Does this fit the first playable slice?'],
];
overview.getRange('G4:J4').format = { fill: navy, font: { name: font, size: 10, bold: true, color: '#FFFFFF' }, wrapText: true };
overview.getRange('G4:J12').format.font = { name: font, size: 10 };
overview.getRange('G4:J12').format.borders = { preset: 'outside', style: 'thin', color: '#D9D9D9' };
overview.getRange('G13:J28').values = [
  ['Data layer', 'Rows', 'Source / status', 'How to use'],
  ['VanillaBuildings', vanillaData.buildings.length, 'Official wiki Category:Constructions tree', 'Authoritative vanilla 1.1 reference; filter Buildable / Availability.'],
  ['VanillaItems', vanillaData.items.length, 'Official wiki Category:Goods tree', 'Authoritative vanilla goods, ingredients, plants, and crops.'],
  ['VanillaRecipes', vanillaData.recipes.length, 'Parsed from vanilla building infoboxes', 'Exact inputs, outputs, cycle hours, fuel, power, and workers.'],
  ['TargetModPackages', targetModData.buildings.length, 'Installed Northforge / Expanded Storage blueprints', 'Exact Iron Teeth dimensions, costs, hp, science, storage, and stacking data.'],
  ['InstalledDependencyManifests', installedManifestData.packages.length, 'Local Steam Workshop manifest scan', 'Exact 1.1 package IDs, versions, minimum game versions, and declared requirements.'],
  ['Buildings / Items / Recipes', 'Draft', 'Iron Teeth mod layer draft', 'Proposed Deep Frontier content layered above vanilla-aligned columns.'],
  ['Vanilla-aligned fields', 'Applied', 'Buildings / Items / Recipes / Progression / Transport', 'Use the same names and units as the vanilla reference where the concept exists.'],
  ['VanillaAnchors', 9, 'Hand-curated spot checks', 'Quick power and progression anchors for design review.'],
  ['Power demand (hp)', 'Consumed', 'Powered building or recipe load', 'Continuous mechanical power drawn while operating; zero for generators and passive buildings.'],
  ['Power output (hp)', 'Produced', 'Generator or power source', 'Maximum mechanical power supplied to the network; zero for consumers and passive buildings.'],
  ['Power role', 'Explicit', 'Buildings / Recipes / Vanilla reference', 'Consumer, Generator, Passive / transport, or Review when both fields are nonzero.'],
  ['Power accounting', 'Do not add duplicate views', 'Buildings + Recipes', 'Recipe power demand mirrors the machine load for reference; count the building load once in colony totals.'],
  ['Underground model', 'Planned', 'Pre-authored lower sectors + shafts', 'Use authored map volume and vertical logistics first; defer runtime terrain expansion until a supported API exists.'],
  ['Map authoring', 'Map Transformer', 'Copied source map + extra Z layers', 'Transform once, hand-author lower sectors, reload/save the generated map, and publish the required map/mod dependencies.'],
  ['PowerCurve', 'Fuel-tier output targets', 'Wood, coal, oil, gas, nuclear', 'Use the nonlinear hp curve and playtest bands when sizing consumers and generator obligations.'],
];
overview.getRange('G12:J12').format = { fill: navy, font: { name: font, size: 10, bold: true, color: '#FFFFFF' }, wrapText: true };
overview.getRange('G13:J28').format.font = { name: font, size: 10 };
overview.getRange('G13:J28').format.borders = { preset: 'outside', style: 'thin', color: '#D9D9D9' };
overview.getRange('A1:J28').format.wrapText = true;
overview.getRange('A1:J28').format.verticalAlignment = 'center';
overview.getRange('A1:J28').format.autofitRows();
overview.getRange('A:A').format.columnWidth = 23;
overview.getRange('B:B').format.columnWidth = 32;
overview.getRange('C:C').format.columnWidth = 34;
overview.getRange('D:D').format.columnWidth = 18;
overview.getRange('E:E').format.columnWidth = 16;
overview.getRange('F:F').format.columnWidth = 14;
overview.getRange('G:G').format.columnWidth = 20;
overview.getRange('H:H').format.columnWidth = 32;
overview.getRange('I:I').format.columnWidth = 30;
overview.getRange('J:J').format.columnWidth = 34;
overview.getRange('A30:F33').values = [
  ['Concrete progression','First supply','Processing','Permanent supply','Demand (hp)','Verification'],
  ['Surface industry','Sandstone and limestone pits','Crusher; cement kiln; concrete mixer','Use first 120 concrete for both quarries',750,'Authored; runtime pending'],
  ['Permanent industry','Matching deep seams; water','Same three processing buildings','1500 hp per quarry',3750,'No finite-only mineral dependency'],
  ['Map requirement','Place both outcrop types','Place both permanent seam types','Existing worlds need authored sources','n.a.','Sources are registered map-editor entities'],
];
overview.getRange('A30:F30').format = {fill:navy,font:{name:font,size:10,bold:true,color:'#FFFFFF'},wrapText:true};
overview.getRange('A31:F33').format.font = {name:font,size:10};
overview.getRange('A30:F33').format.wrapText = true;
overview.getRange('A30:F33').format.autofitRows();
overview.getRange('A35:F41').values = [
  ['Latest requirements','Restaurant','Hospital','Grocery','Science','Item policy'],
  ['2026-10-19','400 hp; native cooking; worker-served meals, cake, optional coffee and water for thirsty diners','30 patients; 1.8x Medical Bed injury recovery','Several foods and an area wellbeing effect',civicPlan.implementedBuildingScienceOverrides.NuclearReactor,'2+ uses; target 3–5. Food and rocket exceptions.'],
  ['Status',restaurantStatus,civicPlan.hospital.requirementStatus,civicPlan.groceryStore.requirementStatus,'Reactor unlock authored; advanced research pending','ItemUses checks implemented destinations only'],
  ['Construction','Concrete blocks and overhangs','Steel bridge trusses','Aluminum scaffolds','Native support rules','No arbitrary vertical layer cap'],
  ['Oil and equipment','Oil to polymer resin','Resin to plastic','Plastic to hazmat suits','Reusable equipment','Other resin/plastic uses required'],
  ['Radiation','Shielded liquid pipes','Radiation-blocking storage','Nuclear waste blocks demolition','Cooling remains necessary','Implementation pending'],
  ['Warehouse','Multiple selected goods','Per-good stock limits','Shared capacity','Hauling and belts','Shielded variant planned'],
];
overview.getRange('A35:F35').format={fill:navy,font:{name:font,size:10,bold:true,color:'#FFFFFF'},wrapText:true};
overview.getRange('A36:F41').format.font={name:font,size:10};
overview.getRange('A35:F41').format.wrapText=true;
overview.getRange('A43:F45').values=aquacultureOverview;
overview.getRange('A43:F43').format={fill:navy,font:{name:font,size:10,bold:true,color:'#FFFFFF'},wrapText:true};
overview.getRange('A44:F45').format.font={name:font,size:10};
overview.getRange('A44:F45').format.verticalAlignment='top';
overview.getRange('A43:F45').format.wrapText=true;
overview.getRange('A43:F45').format.autofitRows();
overview.getRange('A35:F41').format.autofitRows();
overview.getRange('E36').setNumberFormat('#,##0');
overview.getRange('A47:F49').values=[
  ['Reinforced infrastructure','Solid blocks','Overflow dams','Open construction','Turbine','Advanced foundations'],
  ['2026-10-20','Concrete levee and metal-reinforced dam block','Native 0.65-layer sill','8-tile overhang; 3×3 four-layer scaffold',
   'Controlled dam-base outlet; m³/s and hp','Concrete added to advanced factory, research and launch costs'],
  ['Status','Native main 90 / reload 91 passed','Native retention and vanilla spill parity passed 90 / reload 91','Native stairs, stacked platforms, open bays and walking passed 90 / reload 91',
   hydroCatalog.status,'Starter concrete chain remains buildable without concrete']
];
overview.getRange('A47:F47').format={fill:navy,font:{name:font,size:10,bold:true,color:'#FFFFFF'},wrapText:true};
overview.getRange('A48:F49').format.font={name:font,size:10};
overview.getRange('A47:F49').format.wrapText=true;
overview.getRange('A47:F49').format.autofitRows();

title(powerCurve, 'Deep Frontier generator scaling', 'Draft mod targets. The exact vanilla reference remains on VanillaAnchors; this curve uses the 500 hp early wood baseline and makes each fuel tier materially different.');
const powerCurveHeaders = ['Power ID','Generator tier','Fuel / operating input','Target output (hp)','Playtest band (hp)','Footprint','Workers','Science unlock','Continuous inputs','Failure / hazard','Why this tier exists'];
const powerCurveRows = [
  ['P001','Foundation wood generator','Wood; water',500,'400–600','3x3',0,400,'Wood and water per hour','Stops when fuel or water is missing','Reliable first non-worker generator; establishes the 500 hp baseline.'],
  ['P002','Coal steam generator','Coal; water',2500,'2,000–3,000','4x4',1,1500,'Coal and water per hour','Stops cleanly; soot or badwater outlet','Industrial city power without requiring uranium.'],
  ['P003','Oil turbine','Crude oil; water',10000,'8,000–12,000','4x5',2,5000,'Crude oil and water per hour','Contaminated water and fuel starvation','Makes oil valuable before the nuclear branch.'],
  ['P004','Optional gas turbine','Methane or refined gas; water',25000,'20,000–30,000','5x5',4,9000,'Gas and water per hour','Fume alarm, contaminated outlet, fuel starvation','Optional late power branch; the core route does not require gas.'],
  ['P005','Nuclear reactor','Enriched fuel; reactor coolant water',75000,'50,000–100,000','4x4',6,civicPlan.implementedBuildingScienceOverrides.NuclearReactor,'1 fuel unit and 180 coolant-water units per hour','Coolant warning, emergency shutdown, bounded meltdown if the buffer empties','Compact power for aluminum, advanced research, cryogenics and launch preparation.'],
];
const powerCurveTable = writeTable(powerCurve, 4, powerCurveHeaders, powerCurveRows, 'PowerCurveTable', '#C55A11');
powerCurve.getRange(`A4:K${powerCurveTable.endRow}`).format.wrapText = true;
powerCurve.getRange(`A4:K${powerCurveTable.endRow}`).format.autofitRows();
powerCurve.getRange('A:A').format.columnWidth = 12;
powerCurve.getRange('B:B').format.columnWidth = 24;
powerCurve.getRange('C:C').format.columnWidth = 30;
powerCurve.getRange('D:E').format.columnWidth = 18;
powerCurve.getRange('F:H').format.columnWidth = 14;
powerCurve.getRange('I:K').format.columnWidth = 42;

const buildingHeaders = ['Building ID','Building / Machine','Infobox','Categories','Faction','Buildable?','Availability','Width','Length','Footprint','Footprint tiles','Height','Workers','Power demand (hp)','Power output (hp)','Power role','Science unlock','Bot unlock','Build materials','Flags','Recipe names','Source','Data status','Stage','Role','Stackable','Stacking rule','Conveyor-only solids','Pipe ports','Power mode','Unlock prerequisites','Inputs','Outputs','Waste / side effect','Placement','Player cue','Status','Notes'];
const buildingRows = [
['B001','Agriculture','Compost Yard','1. Survival','Both','Turns organic waste into compost',2,2,1,4,'Yes','No','No','None',0,1,20,'Logs; water','Farmhouse; basic crops','Organic waste; water','Compost','None','Surface; near farms','Soil fertility is falling','Prototype','Early resilience building'],
['B002','Agriculture','Fertilizer Works','2. Productive settlement','Both','Makes crop fertilizer',3,3,2,9,'No','Yes','Yes','Grid',80,2,180,'Planks; gears; metal blocks','Compost Yard; science institute','Compost; water; algae or minerals','Fertilizer','Wastewater','Surface; farm district','Crop yields can be improved','Planning','First major farm factory'],
['B003','Agriculture','Greenhouse','2. Productive settlement','Both','Extends crop reliability',3,4,2,12,'Yes','No','Yes','Grid',35,1,120,'Planks; glass; gears','Fertilizer Works; water storage','Water; seeds; fertilizer','Protected crops','None','Surface; near water','Drought preparation is needed','Planning','High reliability, lower raw yield'],
['B004','Food','Bakery','2. Productive settlement','Both','Produces advanced food',3,3,2,9,'No','Yes','No','Grid',45,2,150,'Planks; gears; metal blocks','Mill; crop variety','Flour; water; sweetener','Bread; pastries','None','Surface; town district','Nutrition variety is low','Planning','Feeds well-being and retail'],
['B005','Food','Fish Pond','2. Productive settlement','Both','Produces fish',4,4,1,16,'No','No','Yes','None',0,1,100,'Logs; planks','Water storage; science institute','Water; juvenile fish; feed','Fresh fish','Low output if water is contaminated','Surface; reservoir edge','A new food source is available','Prototype','Uses water space'],
['B006','Food','Fish Hatchery','3. Industrial city','Both','Breeds juvenile fish',3,3,2,9,'No','Yes','Yes','Grid',55,2,220,'Planks; gears; metal blocks','Fish Pond; Feed Mill','Adult fish; feed; water','Juvenile fish','None','Surface; aquaculture district','Fish demand exceeds pond output','Planning','Keeps aquaculture scalable'],
['B007','Food','Food Factory','3. Industrial city','Iron Teeth','High-volume rations',4,4,3,16,'No','Yes','Yes','Grid',120,2,500,'Planks; gears; metal blocks','Bakery; oil press; wonder','Crops; oils; logs','Rations; emergency food','Wastewater','Surface; factory district','Population growth needs reliable food','Planning','Uses existing faction direction'],
['B008','Civic','Market Hall','2. Productive settlement','Both','Distributes food variety',3,3,2,9,'Yes','Yes','No','Grid',20,3,120,'Planks; gears','Bakery; storage','Packaged food; fish; drinks','Local service','None','Surface; central town','Food is available but far away','Planning','Improves access, not total food'],
['B009','Civic','Grocery Store','3. Industrial city','Iron Teeth','Multi-food retail and neighborhood wellbeing',3,4,2,12,'Yes','No','No','Grid',25,3,240,'Planks; gears; metal blocks','Food production; delivery logistics','Canned fish; canned foods; algae rations; corn rations; other staples','Native food effects; area wellbeing','None','Surface; residential district','Several food needs can be supplied in one place','Planning','Accepted grand artwork supersedes these provisional dimensions; no food/service-token production; stocked area effect pending'],
['B010','Civic','Clinic','2. Productive settlement','Both','Routine healthcare',3,3,2,9,'Yes','No','Yes','Grid',15,2,160,'Planks; gears; paper','Science institute; water storage','Medicine; clean water','Healthcare','None','Surface; town district','Sick days are slowing production','Planning','Basic public health'],
['B011','Civic','Hospital','3. Industrial city','Iron Teeth','30-patient treatment and area wellbeing',5,5,3,25,'Yes','No','Yes','Grid',90,6,600,'Planks; gears; metal blocks; concrete','Medicine production; water supply','Treatment supplies to be balanced','Injury recovery at 1.8x Medical Bed rate; chipped-teeth and badwater treatment; area wellbeing','None authored','Surface; civic district','Injured and contaminated workers need care','Planning','30 shared patient slots; 80% faster is 1.8x rate. Accepted artwork supersedes provisional dimensions. Native treatment pending.'],
['B012','Civic','Restaurant','3. Industrial city','Iron Teeth','Worker-served multi-food meals and dining wellbeing',10,8,9,80,'Yes','No','No','Grid',civicPlan.restaurant.powerDemandHp,4,800,'Planks; gears; metal blocks','Fish and berry supply; other food production','Fresh fish; berries; fermented mushrooms and eggplant rations; drinking water','Actual native food benefits; dining wellbeing','None authored','Surface; commercial district','Guests sit before workers serve them',restaurantStatus,'14 seats; door layers 0/2/4/6. Registration 10x8x9 is not solid occupancy. No DiningService item.'],
['B013','Civic','Neighborhood Park','1. Survival','Both','Basic recreation and beauty',3,3,1,9,'Yes','No','No','None',0,1,40,'Logs; shrubs; decorations','Campfire or equivalent','Trees; flowers; decorations','Aesthetics; recreation','None','Surface; between housing','Housing density is increasing','Prototype','Low-tech well-being'],
['B014','Civic','Public Pool','3. Industrial city','Both','Water-based recreation',4,5,1,20,'No','No','Yes','Grid',40,2,260,'Planks; treated water; gears','Water treatment; clinic','Clean water; power','Recreation; hygiene','Wastewater','Surface; civic district','Water is plentiful enough for comfort','Planning','Consumes treated water'],
['B015','Civic','School','3. Industrial city','Both','Improves workforce capability',4,4,2,16,'Yes','No','No','Grid',20,3,300,'Planks; paper; books','Paper mill; library','Books; paper; food','Education service','None','Surface; town district','Production chains need skilled workers','Planning','Unlocks advanced jobs'],
['B016','Power','Substation','3. Industrial city','Both','Distributes high power',2,2,2,4,'Yes','No','No','Grid',0,1,120,'Planks; gears; metal blocks','Power plant; power lines','Power network','Power access','None','Surface; near factories','Power demand is outgrowing shafts','Prototype','No generation'],
['B017','Power','Flywheel Bank','3. Industrial city','Both','Stores mechanical or electric power',3,3,3,9,'No','No','No','Grid',5,1,240,'Gears; metal blocks; treated wood','Substation; advanced science','Power input','Stored power','None','Surface; power district','Factories need stable power','Planning','Integrates with Flywheels'],
['B018','Logistics','Vertical Belt Lift','3. Industrial city','Both','Moves solids between levels',2,2,4,4,'Yes','Yes','No','Grid',150,0,220,'Planks; gears; metal blocks','Conveyor Belts v2; substation','Solid items','Vertical transfer','None','Surface; shaft edge','Surface and lower district are disconnected','Prototype','Integrates with belts; target load 150 hp'],
['B019','Logistics','Freight Elevator','4. Wonder transition','Both','Large vertical transfer',4,4,8,16,'No','Yes','Yes','Grid',500,2,700,'Metal blocks; gears; treated wood','Vertical Belt Lift; wonder','Solid items; fluids','High-capacity transfer','None','Surface; central logistics','Belt lifts are the bottleneck','Planning','Major infrastructure project; target load 500 hp'],
['B020','Factory','Arc Furnace Complex','3. Industrial city','Both','Conveyor-only alloy production',6,8,4,48,'No','Yes','Yes','Grid',2500,8,900,'Metal blocks; gears; treated wood; glass','Substation; conveyor network; steel recipe','Iron ore; coal; flux; power','High-grade steel; alloys','Slag','Surface; industrial district','Basic steel output is limiting expansion','Planning','Landmark factory; target load 2,500 hp'],
['B021','Factory','Polymer and Chemical Works','4. Wonder transition','Both','Conveyor-only chemical production',6,8,4,48,'No','Yes','Yes','Grid',3500,8,1200,'Metal blocks; gears; treated glass','Oil chain; water treatment; wonder','Crude oil; sulfur; water; power','Polymers; lubricants; resins','Contaminated wastewater','Surface; isolated industrial district','Advanced materials are required','Planning','Target load 3,500 hp; fuel and water remain limiting'],
['B022','Factory','Precision Machine Works','4. Wonder transition','Both','Produces machine cores and robotics parts',5,6,4,30,'No','Yes','No','Grid',2200,6,1100,'Alloys; gears; metal blocks; treated glass','Arc Furnace; school; automation','Alloys; polymers; gears; science','Machine cores; robotics parts','Scrap','Surface; industrial district','Automation research is ready','Planning','Feeds late automation; target load 2,200 hp'],
['B023','Environment','Water Treatment Plant','2. Productive settlement','Both','Cleans water and wastewater',4,5,3,20,'No','Yes','Yes','Grid',500,4,420,'Planks; gears; metal blocks','Clinic or fertilizer works; water storage','Dirty water; wastewater; filter media','Clean water; recovered solids','Concentrated waste','Surface; near reservoirs','Water quality is becoming a constraint','Planning','Supports aquaculture and civic life; target load 500 hp'],
['B024','Environment','Badwater Treatment Works','4. Wonder transition','Both','Converts badwater into safer outputs',5,6,3,30,'No','Yes','Yes','Grid',1500,5,1000,'Metal blocks; gears; glass; science','Water Treatment Plant; wonder','Badwater; chemicals; power','Treated water; industrial salts','Concentrated waste','Surface; isolated district','Badwater is limiting expansion','Planning','Narrative and utility bridge; target load 1,500 hp'],
['B025','Underground','Survey Station','4. Wonder transition','Both','Reveals underground sectors',3,3,2,9,'Yes','No','No','Grid',150,2,500,'Planks; gears; paper','Exploration wonder; statistics','Power; survey maps','Survey data','None','Surface; high ground','A new sector is visible on the map','Planning','Starts frontier branch; target load 150 hp'],
['B026','Underground','Deep Drill','5. Frontier','Both','Extracts deep resources',4,4,5,16,'No','Yes','Yes','Grid',1000,3,800,'Alloys; machine cores; gears','Survey Station; Freight Elevator','Power; drill heads; water','Deep ore; crude oil; optional gas','Spoil or dirty water','Surface or underground shaft','A survey reveals a resource vein','Planning','Requires full logistics chain; gas branch is optional; target load 1,000 hp'],
['B027','Underground','Underground Settlement','5. Frontier','Both','Provides habitable lower district',6,6,3,36,'No','Yes','Yes','Grid',300,8,900,'Alloys; treated glass; concrete','Deep Drill; hospital; lift','Water; food; power','Housing and services','Wastewater','Underground; connected shaft','Surface land is becoming scarce','Planning','Uses existing civic systems; target load 300 hp'],
['B028','Narrative','Human Archive','6. Mystery','Both','Reveals history and badwater source',4,4,3,16,'No','No','No','Grid',250,2,1500,'Paper; machine cores; glass','Survey Station; frontier milestones','Survey data; recovered artifacts','Evidence; science','None','Surface or underground facility','A recovered signal points to the past','Planning','Endgame objective; target load 250 hp'],
['B029','Optional Hazard','Gas Detector','5. Frontier','Both','Detects gas and fume pockets and controls shutoffs',1,1,1,1,'Yes','No','No','Grid',20,0,1000,'Planks; gears; metal blocks','Survey Station; Deep Drill','Power','Gas readings; alarm signal','None','Surface or lower-sector pocket edge','A fume reading rises','Planning','Optional late gas branch; area sensor; target load 20 hp'],
['B030','Optional Hazard','Fume Scrubber','5. Frontier','Both','Clears gas and fume pockets',3,3,3,9,'No','Yes','Yes','Grid',750,2,1200,'Planks; gears; metal blocks; filter media','Gas Detector; Water Treatment Plant','Toxic fumes; water; filter media','Clean air; recovered chemicals','Concentrated waste','Low-area pocket edge','Gas pocket exceeds a safe threshold','Planning','Optional late gas branch; uses fluid-engine goods and explicit pocket inventories; target load 750 hp'],
['B031','Power','Nuclear Reactor','5. Frontier','Iron Teeth','Produces compact, reliable industrial power',4,4,5,16,'No','Yes','Yes','Produces',0,6,civicPlan.implementedBuildingScienceOverrides.NuclearReactor,'Alloys; high-grade steel; machine cores; treated glass','Advanced research; fuel processing; trained healthy workers','Enriched fuel; reactor coolant water','75000 hp','Radioactive waste; contaminated water; meltdown risk if coolant is exhausted','Isolated power district','Aluminum and science districts need compact power','Planning','1,000,000 science authored. 75,000 hp target; constant coolant. Worker wellbeing must not disable cooling or safe shutdown.'],
['B032','Factory','Uranium Processing Plant','5. Frontier','Both','Refines uranium into reactor fuel',5,6,4,30,'No','Yes','Yes','Grid',5000,6,12000,'Alloys; machine cores; metal blocks; treated glass','Deep Drill; Nuclear Reactor research','Uranium ore; chemicals; power','Yellowcake; enriched fuel','Radon; concentrated waste','Isolated industrial district','A reactor fuel chain is now available','Planning','Requires sealed storage and hazard control; target load 5,000 hp'],
['B033','Factory','Electrolysis Plant','6. Launch program','Both','Splits purified water into gases',4,5,4,20,'No','Yes','Yes','Grid',6000,5,9000,'Alloys; gears; treated glass; machine cores','Water Treatment Plant; advanced power','Pure water; power','Hydrogen gas; oxygen gas','Wastewater','Surface or industrial district','Rocket fuel production begins','Planning','Separate output ports for each gas; target load 6,000 hp'],
['B034','Factory','Cryogenic Liquefaction Plant','6. Launch program','Both','Liquefies hydrogen and oxygen for launch fuel',5,6,4,30,'No','Yes','Yes','Grid',10000,6,11000,'Alloys; machine cores; treated glass; polymers','Electrolysis Plant; nuclear or large renewable grid','Hydrogen gas; oxygen gas; cryocoolant; power','Liquid hydrogen; liquid oxygen','Boiloff gas; contaminated coolant','Isolated cryogenic district','Gas supply is ready for launch preparation','Planning','Target load 10,000 hp; use bounded storage loss; no global heat system'],
['B035','Storage','Cryogenic Tank','6. Launch program','Both','Stores liquid hydrogen or oxygen',3,3,3,9,'No','No','Yes','Grid',1000,0,7000,'Treated glass; alloys; polymers; metal blocks','Cryogenic Liquefaction Plant; Power Lines','Liquid hydrogen or liquid oxygen; power','Launch fuel inventory','Vented gas if unpowered too long','Cryogenic fuel district','Fuel must remain launch-ready','Planning','Target load 1,000 hp per active tank; separate tanks by good type'],
['B036','Factory','Rocket Assembly Hangar','6. Launch program','Both','Assembles rocket components',8,12,8,96,'No','Yes','Yes','Grid',12000,10,15000,'High-grade steel; alloys; machine cores; treated glass; polymers','Precision Machine Works; Cryogenic Tank; Mission Control','Rocket components; launch fuel; workers','Armed rocket','Scrap; rejected components','Launch complex','Every component has arrived','Planning','Target load 12,000 hp; conveyor-fed solids and pipe-fed fuel'],
['B037','Wonder','Launch Pad','6. Launch program','Both','Launches an assembled rocket',8,8,4,64,'No','No','Yes','Grid',25000,2,18000,'High-grade steel; alloys; treated glass; concrete; machine cores','Rocket Assembly Hangar; Mission Control','Armed rocket; liquid hydrogen; liquid oxygen; power','Mission result','Exhaust and spent stage','Clearance zone','The colony is ready to launch','Planning','Short 25,000 hp high-demand launch sequence'],
['B038','Narrative','Mission Control','6. Launch program','Both','Schedules missions and interprets signals',4,4,3,16,'No','Yes','No','Grid',1500,4,12000,'Machine cores; electronics; treated glass; paper','Human Archive; Rocket Assembly Hangar','Archive data; evidence; power','Mission plan; recovered telemetry','None','Surface or launch district','A recovered record identifies the next mission','Planning','Supports three mission tiers; target load 1,500 hp'],
['B039','Environment','Radioactive Waste Vault','5. Frontier','Both','Stores and isolates radioactive waste',4,4,3,16,'No','No','Yes','None',0,2,10000,'Concrete; treated glass; metal blocks; polymers','Nuclear Reactor; Water Treatment Plant','Radioactive waste','Safe waste storage','Radiation if capacity is exceeded','Isolated lower sector or surface district','Waste storage is nearly full','Planning','Bounded radiation area; no maintenance loop'],
['B040','Education','Technical School','4. Wonder transition','Both','Educates individual advanced-machine workers',4,4,3,16,'Yes','Yes','No','Grid',300,4,1800,'Planks; paper; gears; treated glass','School; Precision Machine Works','Books; paper; food; power','Persistent industrial and specialist qualifications','None','Surface; town district','Advanced machinery needs trained staff','Planning','Persistent individual education; safe-boundary wellbeing eligibility. No inventory license product. Proposed 300 hp.'],
['B041','Environment','Radioactive Waste Refinery','5. Frontier','Both','Refines radioactive waste into badwater and recovered minerals',5,6,4,30,'No','Yes','Yes','Grid',8000,6,16000,'Alloys; machine cores; treated glass; concrete; polymers','Nuclear Reactor; Radioactive Waste Vault; Badwater Treatment Works','Radioactive waste; chemicals; water','Badwater; recovered minerals','Radon; residual radioactive sludge','Isolated hazardous district','Waste storage is full and cannot be deleted','Planning','Persistent-waste route; storage containing radioactive waste is demolition-locked; target load 8,000 hp'],
['B042','Underground','Deep Mine','5. Frontier','Iron Teeth','Permanently extracts Deep Ore from a placed Deep Ore Vein',5,5,4,25,'No','Yes','Yes','Grid',4000,6,6000,'Logs; planks; gears; metal blocks; Deep Alloy','Survey Station; Deep Ore Vein; Technical School','Water','Deep Ore','None','On a Deep Ore Vein understructure','The finite source is running low','Planning','Permanent source branch; 4 Deep Ore per 2 min; 12 Water per cycle; 4,000 hp; no artificial layer cap'],
];
const modInfobox = (category) => category === 'Civic' ? 'Well-Being' : ['Power', 'Storage', 'Wonder'].includes(category) ? 'Structure' : category === 'Narrative' ? 'Monument' : 'Workplace';
const formatCostObject = (costs) => Object.entries(costs ?? {}).map(([id, amount]) => `${id.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/^./, (c) => c.toUpperCase())}: ${amount}`).join('; ');
const alignedBuildingRows = buildingRows.map((r) => {
  const [id, category, name, stage, faction, role, width, length, height, tiles, stackable, conveyorOnly, pipePorts, powerMode, powerDemand, workers, science, materials, prerequisites, inputs, outputs, waste, placement, cue, status, notes] = r;
  const stackingRule = stackable === 'Yes' ? 'Yes; no artificial layer cap; use compatible support and vanilla block rules' : 'No';
  const powerOutput = powerMode === 'Produces' ? Number(String(outputs).match(/[0-9]+(?:\.[0-9]+)?/)?.[0] ?? 0) : 0;
  const row=[id, name, modInfobox(category), `${category}; Deep Frontier`, 'Iron Teeth', 'Yes', 'Build menu', width, length, `${width}x${length}`, tiles, height, workers, powerDemand, powerOutput, powerRole(powerDemand, powerOutput), science, '', materials, `stackable=${stackable}; conveyor-only=${conveyorOnly}; pipe-ports=${pipePorts}; power-mode=${powerMode}`, '', 'Deep Frontier design draft', 'Mod draft; vanilla-aligned columns', stage, role, stackable, stackingRule, conveyorOnly, pipePorts, powerMode, prerequisites, inputs, outputs, waste, placement, cue, status, notes];
  if(name==='Restaurant') {
    const b=restaurantBlueprint;
    const fields={'Infobox':'Workshop and dining hall','Workers':b.WorkplaceSpec.MaxWorkers,'Power demand (hp)':b.MechanicalNodeSpec.PowerInput,
      'Power output (hp)':b.MechanicalNodeSpec.PowerOutput,'Science unlock':b.BuildingSpec.ScienceCost,
      'Build materials':amountsText(b.BuildingSpec.BuildingCost.map(g=>[g.Id,g.Amount])),
      'Recipe names':b.ManufactorySpec.ProductionRecipeIds.join('; '),'Source':restaurantSource,'Data status':restaurantStatus,
      'Flags':'Sparse occupancy; 14 seats; 4 workers; native Sitting; shared kitchen inventory',
      'Stackable':'Clear terrace cells','Stacking rule':'Four clear roof terrace cells at layer 6; native support rules; no layer cap',
      'Inputs':'Main meal: fish, berries, fermented mushrooms, eggplant rations. Optional: fermented cassava/soybean, cake, coffee. Water for thirsty diners stays stocked; other kitchen ingredients depend on recipe.',
      'Outputs':'Seated food effects and dining wellbeing; fermented foods and cake stay in restaurant',
      'Status':restaurantStatus,'Notes':'400 hp total, not additional per recipe. Doors at 0/2/4/6. Cake cooked and eaten only at tables. Shaft power, platform placement, seated fit and service reload tested; exterior stairs/rail seams need dedicated civic checks.'};
    for(const [header,value] of Object.entries(fields)) {const i=buildingHeaders.indexOf(header);if(i<0)throw Error('Unknown building column: '+header);row[i]=value;}
  }
  return row;
});
const packageBuildingRows = targetModData.buildings.map((b, i) => {
  const stackable = (b.flags.stackableValues ?? []).includes('BlockObject') ? 'Yes' : 'No';
  const flags = `stackable=${b.flags.stackableValues.join(',')}; occupations=${b.flags.occupations.join(',')}; entrance=${b.flags.hasEntrance}; flippable=${b.flags.flippable}; good-type=${b.flags.whitelistedGoodType}; capacity=${b.flags.maxCapacity}; tool-group=${b.flags.toolGroup}; package=${b.manifestId} ${b.packageVersion}`;
  return [`DP${String(i + 1).padStart(3, '0')}`, b.building, b.infobox, b.categories, 'Iron Teeth', b.buildable, b.availability, b.width, b.length, b.footprint, b.footprintTiles, b.height, b.workers, b.powerDemandHp, b.powerOutputHp, powerRole(b.powerDemandHp, b.powerOutputHp), b.scienceUnlock, b.botUnlock, formatCostObject(b.materials), flags, '', b.sourceUrl, b.dataStatus, 'Dependency foundation', b.outputs, stackable, b.flags.stackingRule, 'No', 'No', b.powerOutputHp > 0 ? 'Produces' : 'None', `${b.packageName} package ${b.packageVersion}`, b.inputs, b.outputs, 'None', b.flags.placement, 'Use the installed package profile', 'Verified package data', `Workshop ${b.packageId}; blueprint ${b.blueprintPath}`];
});
const constructionBuildingRows = construction.buildings.map(b => {
  const blueprint=constructionBlueprints.get(b.id);
  const {X:w,Y:d,Z:h}=blueprint.BlockObjectSpec.Size;
  const blocks=blueprint.BlockObjectSpec.Blocks;
  const support=blocks.filter(block=>block.Stackable==='BlockObject').length;
  const empty=blocks.filter(block=>block.Occupations==='None').length;
  const status=constructionBuildingStatus.get(b.id);
  if(!status)throw Error('Missing construction verification status: '+b.id);
  const route=blueprint.BuildingWalkwaySpec;
  const flags=`${support} support cells; ${empty} empty cells; `+(route
    ?`${route.Waypoints.length} route cells; ${route.Openings.length} adaptive rail openings`
    :'no built-in walkways');
  const stackRule=support?'Platforms on supported clear deck cells; native collision; no layer cap':'No authored support cells; native collision';
  const r = b.recipes.map(id => constructionRecipe.get(id));
  const inputs = r.map(recipe => amountsText(recipe.inputs)).join(' / ');
  const outputs = b.kind === 'pit' ? goodName(b.good) : r.map(recipe => amountsText(recipe.outputs)).join(' / ');
  const pipe=blueprint.BuildingPipeTargetPortsSpec
    ?blueprint.BuildingPipeTargetPortsSpec.Ports.map(p=>`(${p.Coordinates.X},${p.Coordinates.Y},${p.Coordinates.Z}) ${p.Directions} ${p.State}; native transfer/reload passed 81`).join('; ')
    :r.some(recipe=>recipe.inputs.some(([id])=>id==='Water'))
      ?'Recipe Water inventory; industrial pipe port not yet verified':'None';
  return [b.id,b.name,b.kind==='pit'?'Workplace':'Manufactory','Construction materials; Deep Frontier','Iron Teeth','Yes','Build menu',
    w,d,`${w}x${d}`,w*d,h,b.workers,b.hp,0,b.hp>0?'Consumer':'Passive / transport',b.science,b.botScience,amountsText(b.cost),
    flags,b.recipes.join('; '),constructionSource,status,'3. Industrial city',b.description,
    support?'Clear supported deck cells':'No',stackRule,'No',pipe,b.hp>0?'Consumes':'None',
    b.source ? b.source : 'Prior mineral processing buildings',inputs,outputs,'None',
    b.kind==='quarry'?'Matching 5x5 seam':b.kind==='pit'?'Ground; outcrops in walking range':'Ground or stackable support',
    b.description,status,b.kind==='quarry'?'Permanent source; 60 concrete construction gate':'No concrete required to build the first line'];
});
const constructionSourceRows = construction.sources.map(s => {
  const [w,d,h]=s.size;
  return [s.id,s.name,'Map object','Mineral source; Deep Frontier','Iron Teeth','No','Map editor',w,d,`${w}x${d}`,w*d,h,0,0,0,'Passive / transport',0,'n.a.','None',
    `Source=${s.kind}`,'',constructionSource,constructionStatus,'3. Industrial city',s.description,'No','Native geological understructure; no artificial layer cap','No','No','None',
    'Map author places before play','None',s.kind==='finite'?`${s.yield} ${goodName(s.good)}`:`Permanent ${goodName(s.good)}`,'None','Authored terrain',s.description,'Prototype',
    s.kind==='finite'?`Native Yielder; ${s.removalHours} game hours per unit; yield persists`:'Required understructure for the corresponding quarry'];
});
const plannedFacilities = [
  ...civicPlan.proposedScienceStations.map(b=>({id:b.id,name:goodName(b.id),category:'Science',hp:b.powerDemandHp,workers:b.workers,role:`Proposed ${b.sciencePerWorkingHour.toLocaleString('en-US')} science per working hour`,inputs:'Useful existing industrial materials; recipes pending',outputs:'Science',notes:'Research rate is a balance target. No license goods.'})),
  {id:'DeepBauxiteMine',name:'Deep Bauxite Mine',category:'Minerals',hp:6000,workers:null,role:'Permanent bauxite supply after finite starter deposits',inputs:'Water; proposed operating supplies',outputs:'Bauxite',notes:'Requires an authored permanent deposit and bootstrap route.'},
  {id:'AluminaRefinery',name:'Alumina Refinery',category:'Factory',hp:8000,workers:null,role:'Refine bauxite into several-use industrial material',inputs:'Bauxite; water; recipes pending',outputs:'Alumina; Badwater',notes:'No new one-use sludge good.'},
  {id:'AluminumSmelter',name:'Aluminum Smelter',category:'Factory',hp:40000,workers:null,role:'Power-intensive aluminum electrolysis',inputs:'Alumina; recipes pending',outputs:'Aluminum',notes:'Supplies structures, electrical equipment, research and rocket frames.'},
  {id:'AdvancedWarehouse',name:'Advanced Warehouse',category:'Storage',hp:0,workers:0,role:'Store multiple selected solid goods in one shared inventory',inputs:'Player-selected goods via haulers and belts',outputs:'The same stored goods',notes:'Per-good stock limits; total shared capacity. Reject invalid settings. Costs/capacity/dimensions pending.'},
  {id:'ShieldedWarehouse',name:'Shielded Warehouse',category:'Storage',hp:0,workers:0,role:'Multi-good storage with radiation shielding',inputs:'Ordinary and radioactive solids via haulers and belts',outputs:'The same stored goods',notes:'Concrete/metal/plastic materials proposed. Waste blocks demolition until emptied. Shielding behavior pending.'},
];
const plannedFacilityRows=plannedFacilities.map((b,i)=>[`B${String(43+i).padStart(3,'0')}`,b.name,b.category==='Storage'?'Structure':'Workplace',`${b.category}; Deep Frontier`,'Iron Teeth','Planned','Not authored',null,null,'Unassigned',null,null,b.workers,b.hp,0,powerRole(b.hp,0),null,'','Not balanced','Not authored','','tools/frontier_progression.json','Design only; not implemented','4–5. Industrial expansion',b.role,'Pending geometry','Native support; no arbitrary layer cap','No','Pending inventory type',b.hp?'Grid':'None','Materials and research gates pending',b.inputs,b.outputs,'Pending recipe','Fit approved isometric art','Next factory capability','Planning',`${b.id}. ${b.notes}`]);
const allBuildingRows = [...alignedBuildingRows, ...constructionBuildingRows, ...constructionSourceRows, ...packageBuildingRows, ...plannedFacilityRows];
updateAquacultureRows(allBuildingRows,buildingHeaders,aquacultureBuildingUpdates);
updateAquacultureRows(allBuildingRows,buildingHeaders,hospitalBuildingUpdates);
updateAquacultureRows(allBuildingRows,buildingHeaders,groceryBuildingUpdates);
allBuildingRows.push(...aquacultureBuildingAdds);
allBuildingRows.push(...structuralWorkbookRows(buildingHeaders));
allBuildingRows.push(hydroBuildingRow);
updateResearchBuilding(allBuildingRows,buildingHeaders);
// These exact cost fields belong to the authored prototypes; other planning
// columns retain their explicit draft status until their replacement is built.
const costCatalog=JSON.parse(await fs.readFile(`${root}/tools/building_construction_costs.json`,'utf8'));
const costRowIds={B002:'FertilizerWorks',B003:'Greenhouse',B006:'FishHatchery',B012:'Restaurant',
  B021:'ChemicalWorks',B022:'PrecisionMachineWorks',B023:'WaterTreatmentPlant',B031:'NuclearReactor',
  B032:'UraniumProcessingPlant',B033:'ElectrolysisPlant',B034:'CryogenicLiquefactionPlant',
  B036:'RocketAssemblyHangar',B037:'LaunchPad',B038:'MissionControl',B040:'TechnicalSchool',
  B041:'RadioactiveWasteRefinery'};
for(const [rowId,id] of Object.entries(costRowIds)) {
  const row=allBuildingRows.find(r=>r[0]===rowId);
  if(!row||!Object.hasOwn(costCatalog.buildings,id))throw new Error('Missing construction cost workbook target: '+id);
  row[buildingHeaders.indexOf('Build materials')]=amountsText(costCatalog.buildings[id]);
  row[buildingHeaders.indexOf('Source')]+='; tools/building_construction_costs.json (exact authored cost)';
}
for(const [rowId,id] of [['B026','DeepDrill'],['B042','DeepMine']]) {
  const blueprint=JSON.parse(await fs.readFile(`${root}/src/DeepFrontier/Data/Buildings/Metal/${id}/${id}.IronTeeth.blueprint.json`,'utf8'));
  const row=allBuildingRows.find(r=>r[0]===rowId);
  if(!row)throw new Error('Missing deep extraction workbook row: '+id);
  row[buildingHeaders.indexOf('Build materials')]=amountsText(blueprint.BuildingSpec.BuildingCost.map(g=>[g.Id,g.Amount]));
}
for (const row of allBuildingRows) {
  if(row.length!==buildingHeaders.length) throw new Error(`Wrong building column count for ${row[0]}`);
}
const buildingTable = writeTable(buildings, 1, buildingHeaders, allBuildingRows, 'BuildingsTable', '#5B9BD5');
const buildingEnd = buildingTable.endRow;
const buildingEndCol = buildingTable.colLetter(buildingTable.endCol);
buildings.getRange(`A1:${buildingEndCol}${buildingEnd}`).format.wrapText = true;
buildings.getRange(`A1:${buildingEndCol}${buildingEnd}`).format.autofitRows();
buildings.getRange('A:A').format.columnWidth = 12;
buildings.getRange('B:B').format.columnWidth = 26;
buildings.getRange('C:E').format.columnWidth = 18;
buildings.getRange('F:G').format.columnWidth = 14;
buildings.getRange('H:R').format.columnWidth = 13;
buildings.getRange('S:U').format.columnWidth = 30;
buildings.getRange('V:W').format.columnWidth = 52;
buildings.getRange('X:AL').format.columnWidth = 26;
const hospitalWorkbookRow=allBuildingRows.findIndex(r=>r[0]==='B011')+2;
buildings.getRange(`A${hospitalWorkbookRow}:AL${hospitalWorkbookRow}`).format.verticalAlignment='top';
buildings.getRange(`A${hospitalWorkbookRow}:AL${hospitalWorkbookRow}`).format.autofitRows();
buildings.getRange(`AK2:AK${buildingEnd}`).conditionalFormats.add('containsText', { text: 'Prototype', format: { fill: gold } });
buildings.getRange(`AK2:AK${buildingEnd}`).conditionalFormats.add('containsText', { text: 'Planning', format: { fill: blue } });

const itemHeaders = ['Item ID','Item','Infobox','Categories','Faction','Type','Source / recipe','Storage','Weight','Satisfies / effects','Produces','Consumed by','Source','Data status','Tier','Primary uses','Perishable','Hazard','Unit','Science value','Notes'];
const itemRows = [
['I001','Basic resource','Compost','1','Compost Yard','Fertilizer; soil restoration','Warehouse','No','None','Solid',0,'Early agriculture input'],
['I002','Agriculture','Fertilizer','2','Fertilizer Works','Greenhouses; crop fields','Warehouse','No','Chemical waste risk','Solid',2,'Improves yield, not mandatory'],
['I003','Agriculture','Seed Treatment','3','Soil Lab','Greenhouses; advanced crops','Warehouse','No','None','Solid',3,'Improves reliability'],
['I004','Food','Fresh Fish','2','Fish Pond','Food; restaurants; grocery stores','Warehouse','Yes','Contaminated-water risk','Solid',1,'New protein variety'],
['I005','Food','Smoked Fish','2','Fishery Works','Food; grocery stores','Warehouse','No','None','Solid',2,'Long shelf life'],
['I006','Food','Canned Fish','3','Fishery Works','Restaurants; hospitals; emergency food','Warehouse','No','None','Solid',4,'Consumer good'],
['I007','Food','Fish Oil','3','Fishery Works','Medicine; advanced food; lubricant','Tank','No','None','Liquid',5,'Cross-chain ingredient'],
['I008','Food','Bread','2','Bakery','Food; restaurants; grocery stores','Warehouse','Yes','None','Solid',2,'Food variety'],
['I009','Food','Emergency Ration','3','Food Factory','Hospitals; drought stockpile','Warehouse','No','None','Solid',5,'High-density food'],
['I010','Consumer','Packaged Food','3','Food factories','Grocery stores; restaurants','Warehouse','No','None','Solid',3,'Retail input'],
['I011','Healthcare','Medicine','3','Public Health Lab','Clinics; hospitals','Warehouse','No','None','Solid',6,'Reduces sick days'],
['I012','Healthcare','Medical Food','4','Food Synthesis Plant','Hospitals; specialist care','Warehouse','No','None','Solid',8,'High-tier service input'],
['I013','Industrial','Flux','2','Crusher / quarry','Arc Furnace','Warehouse','No','Dust','Solid',2,'Factory input'],
['I014','Industrial','High-grade Steel','3','Arc Furnace Complex','Freight elevators; factories','Warehouse','No','None','Solid',8,'Unlocks heavy structures'],
['I015','Industrial','Alloy','4','Arc Furnace Complex','Machine Works; deep drill','Warehouse','No','None','Solid',12,'Advanced material'],
['I016','Industrial','Polymer (legacy draft)','4','Chemical Works','Superseded by Polymer Resin and Plastic','Warehouse','No','Chemical','Solid',10,'Legacy authored good; replacement requires explicit source and save migration. No aliases.'],
['I017','Industrial','Lubricant','4','Chemical Works','Machines; transport','Tank','No','Chemical','Liquid',8,'Useful without maintenance system'],
['I018','Industrial','Machine Core','4','Precision Machine Works','Automation; deep drill; archives','Warehouse','No','None','Solid',15,'Capability unlock'],
['I019','Power','Power Module','4','Megawatt Storage Works','Flywheel bank; substations','Warehouse','No','None','Solid',10,'Power infrastructure'],
['I020','Environment','Filter Media','2','Water Treatment Plant','Water treatment','Warehouse','No','None','Solid',2,'Keeps water chain operating'],
['I021','Environment','Concentrated Waste','4','Treatment works','Future disposal or vitrification','Warehouse','No','Hazard','Solid',0,'Must have a safe outlet'],
['I022','Underground','Deep Ore','5','Deep Drill','Alloy; chemical chains','Warehouse','No','Cave-in context','Solid',12,'Frontier resource'],
['I023','Underground','Crude Oil','5','Pumpjack / deep drill','Chemical Works; fuel','Tank','No','Flammable','Liquid',12,'Surface factory input'],
['I024','Underground','Gas','5','Gas well / Deep Drill','Chemical Works; power','Tank; Fume Basin','No','Flammable','Fluid (gas proxy)',10,'Optional late hazard branch; use named gas goods when a recipe needs a specific hazard'],
['I025','Narrative','Recovered Artifact','6','Human Archive','Evidence; science','Warehouse','No','None','Solid',20,'Story item'],
['I026','Underground','Methane','5','Deep Drill / gas well','Chemical Works; fuel; power','Tank; Fume Basin','No','Flammable / explosive','Fluid (gas proxy)',12,'Optional late gas branch; pipeable in sealed networks; accumulates in low-area pockets'],
['I027','Underground','Sulfur Gas','5','Sulfur well / acid plant','Acid; chemical processing','Tank; Fume Basin','No','Corrosive','Fluid (gas proxy)',12,'Optional late gas branch; low-area pocket hazard; scrubber input'],
['I028','Environment','Toxic Fumes','5','Chemical Works / refinery','Scrubbing; industrial salts','Fume Basin; Tank','No','Toxic','Fluid (gas proxy)',10,'Optional late gas branch; produced by selected machines; detector and scrubber control'],
['I029','Underground','Radon','6','Uranium mine / deep strata','Isotope processing; medical systems','Sealed Tank; Fume Basin','No','Radiation','Fluid (gas proxy)',20,'Optional late gas branch; area exposure is handled separately from storage'],
['I030','Underground','Uranium Ore','5','Deep Drill','Uranium processing; nuclear fuel','Warehouse','No','Radiation','Solid',18,'Finite authored source; requires hazard control'],
['I031','Nuclear','Yellowcake','5','Uranium Processing Plant','Enriched fuel','Warehouse','No','Radiation','Solid',22,'Intermediate fuel material'],
['I032','Nuclear','Enriched Fuel','5','Uranium Processing Plant','Nuclear Reactor','Warehouse','No','Radiation','Solid',30,'High-value reactor input'],
['I033','Nuclear','Pure Water','6','Water Treatment Plant','Electrolysis; cryogenic systems','Tank','No','None','Liquid',6,'Separate from ordinary water for launch fuel'],
['I034','Launch','Hydrogen Gas','6','Electrolysis Plant','Cryogenic Liquefaction Plant','Tank; Fume Basin','No','Flammable / explosive','Fluid (gas proxy)',16,'Keep in isolated network'],
['I035','Launch','Oxygen Gas','6','Electrolysis Plant','Cryogenic Liquefaction Plant','Tank','No','Oxidizer','Fluid (gas proxy)',16,'Keep separate from hydrogen'],
['I036','Launch','Liquid Hydrogen','6','Cryogenic Liquefaction Plant','Cryogenic Tank; Launch Pad','Cryogenic Tank','No','Cryogenic / flammable','Liquid',24,'Launch fuel; storage requires power'],
['I037','Launch','Liquid Oxygen','6','Cryogenic Liquefaction Plant','Cryogenic Tank; Launch Pad','Cryogenic Tank','No','Cryogenic / oxidizer','Liquid',24,'Launch fuel; storage requires power'],
['I038','Launch','Cryocoolant','6','Chemical Works','Cryogenic Liquefaction Plant','Tank','No','Chemical','Liquid',18,'Supports liquefaction without adding global heat simulation'],
['I039','Nuclear','Radioactive Waste','5','Nuclear Reactor','Radioactive Waste Vault; reprocessing','Sealed Storage','No','Radiation','Solid',0,'Capacity and isolation are the hazard gate'],
['I040','Launch','Rocket Airframe','6','Rocket Assembly Hangar','Launch Complex','Warehouse','No','None','Solid',40,'Large structural component'],
['I041','Launch','Propulsion Package','6','Rocket Assembly Hangar','Launch Complex','Warehouse','No','None','Solid',50,'Engine and turbopump package'],
['I042','Launch','Guidance Computer','6','Mission Control','Launch Complex; mission payload','Warehouse','No','None','Solid',60,'Requires archive data and precision parts'],
['I043','Launch','Mission Payload','6','Mission Control','Launch Pad','Warehouse','No','None','Solid',50,'Mission-specific payload'],
['I044','Narrative','Recovered Telemetry','6','Launch Pad','Human Archive; final mission','Warehouse','No','None','Solid',30,'Launch result and story evidence'],
['I045','Education','Industrial License (legacy token)','4','Technical School','Replace with persistent worker education','Warehouse','No','None','Solid',8,'Legacy authored token; not the new education design. Explicit removal/migration pending.'],
['I046','Education','Specialist License (legacy token)','5','Technical School','Replace with persistent worker education','Warehouse','No','None','Solid',16,'Legacy authored token; education and individual wellbeing gate difficult jobs. Safety systems stay active.'],
['I047','Education','Flight License (legacy token)','6','Mission Control','Replace with persistent worker education','Warehouse','No','None','Solid',24,'Legacy authored token; replacement is a worker qualification, not an inventory item.'],
['I048','Industrial','Electronics','5','Precision Machine Works','Mission Control; Guidance Computer','Warehouse','No','None','Solid',18,'High-value avionics input'],
['I049','Nuclear','Reactor Coolant Water','5','Water Treatment Plant','Nuclear Reactor safety loop','Tank','No','None','Liquid',4,'Constant reactor input; a depleted coolant buffer creates meltdown risk'],
['I050','Environment','Badwater','5','Radioactive Waste Refinery; Badwater Treatment Works','Treatment; industrial recovery; narrative evidence','Tank','No','Contaminated','Liquid',12,'Radioactive waste can be converted into this persistent liquid; it still needs storage or treatment'],
['I051','Nuclear','Recovered Minerals','5','Radioactive Waste Refinery','Industrial recovery; chemical processing','Warehouse','No','Residual radiation','Solid',20,'Useful output from refining waste; does not erase the badwater obligation'],
['I052','Underground','Deep Ore Vein','5','Map Editor placement','Deep Mine understructure; permanent Deep Ore','Map Editor','No','None','Marker',0,'Authored permanent resource node; placed in terrain and never stored as inventory'],
['I053','Industrial','Polymer Resin','4','Chemical Works','Plastic; composite structures; protective coatings; filter media','Warehouse','No','Chemical','Solid',0,'Proposed oil-derived material. Recipe and implementation pending; uses are planned, not audited as implemented.'],
['I054','Industrial','Plastic','4','Polymer processing','Hazmat suits; pipe liners; food packaging; electronics insulation; medical equipment','Warehouse','No','None','Solid',0,'Proposed refined resin. Exact ingredients and rates pending.'],
['I055','Equipment','Hazmat Suit','5','Protective Equipment Workshop','Reactor work; waste handling; contamination treatment; emergency cleanup','Warehouse','No','None','Reusable equipment',0,'Proposed plastic/polymer equipment. No durability or maintenance loop. Does not replace cooling.'],
['I056','Mineral','Bauxite','4','Finite surface deposit; permanent deep mine','Alumina; specialist cement','Pile','No','None','Solid',0,'Proposed; both starter and renewable supply required.'],
['I057','Industrial','Alumina','4','Alumina Refinery','Aluminum; abrasives; industrial filter media','Warehouse','No','None','Solid',0,'Proposed; refinery produces badwater. No one-use sludge good.'],
['I058','Industrial','Aluminum','5','Aluminum Smelter','Electrical equipment; alloys; advanced research; bridges and scaffolds; rocket airframes','Warehouse','No','None','Solid',0,'Proposed 40,000 hp electrolysis. Multiple useful destinations required before release.'],
['I059','Food','Sweet Berry Cake','3','Restaurant kitchen','Seated dessert; unique food wellbeing','Restaurant only','No','None','RestaurantDish',0,'2 berries + 2 corn + 1 water yield 4 cakes in 2 base working hours. Cooked and eaten only at restaurant tables. Food single-use exception applies.'],
];
const alignedItemRows = itemRows.map((r) => {
  const [id, category, item, tier, sourceRecipe, primaryUses, storage, perishable, hazard, unit, scienceValue, notes] = r;
  if(id==='I059')return [id,item,'Good',category,'Iron Teeth',cakeGood.GoodType,sourceRecipe,storage,cakeGood.Weight,
    cakeGood.ConsumptionEffects.map(e=>`${e.NeedId}: +${e.Points}`).join('; '),'','Restaurant table service',
    'src/DeepFrontier/Data/Goods/Good.SweetBerryCake.blueprint.json',restaurantStatus,tier,primaryUses,perishable,hazard,unit,scienceValue,notes];
  return [id, item, 'Good', category, 'Iron Teeth', unit, sourceRecipe, storage, 1, '', '', '', 'Deep Frontier design draft', 'Mod draft; vanilla-aligned columns', tier, primaryUses, perishable, hazard, unit, scienceValue, notes];
});
for (const g of construction.goods) {
  const producers = construction.buildings.filter(b=>b.good===g.id).map(b=>b.name).join('; ');
  const consumers = construction.buildings.filter(b=>b.cost.some(([id])=>id===g.id) || b.recipes.some(id=>constructionRecipe.get(id).inputs.some(([good])=>good===g.id))).map(b=>b.name);
  if(g.id==='Concrete') consumers.push('Radioactive Waste Vault');
  alignedItemRows.push([g.id,g.name,'Good','Construction materials','Iron Teeth','Box',producers,'Warehouse',g.weight,'None','',consumers.join('; '),
    constructionSource,constructionStatus,'3',g.use,'No','None','Solid',0,'Finite pits bootstrap permanent quarries; standard inventory and carrying']);
}
updateAquacultureRows(alignedItemRows,itemHeaders,aquacultureItemUpdates);
updateAquacultureRows(alignedItemRows,itemHeaders,hospitalItemUpdates);
updateAquacultureRows(alignedItemRows,itemHeaders,groceryItemUpdates);
alignedItemRows.push(...aquacultureItemAdds);
const itemTable = writeTable(items, 1, itemHeaders, alignedItemRows, 'ItemsTable', '#70AD47');
const itemEnd = itemTable.endRow;
const itemEndCol = itemTable.colLetter(itemTable.endCol);
items.getRange(`A1:${itemEndCol}${itemEnd}`).format.wrapText = true;
items.getRange(`A1:${itemEndCol}${itemEnd}`).format.autofitRows();
items.getRange('A:A').format.columnWidth = 12;
items.getRange('B:B').format.columnWidth = 24;
items.getRange('C:E').format.columnWidth = 18;
items.getRange('F:F').format.columnWidth = 13;
items.getRange('G:H').format.columnWidth = 28;
items.getRange('I:I').format.columnWidth = 10;
items.getRange('J:L').format.columnWidth = 28;
items.getRange('M:N').format.columnWidth = 42;
items.getRange('O:U').format.columnWidth = 22;

baseSheet(itemUses, '#C55A11');
title(itemUses, 'Implemented item uses', 'Counts authored consumers only. Food and final rocket parts may have one use. Planned destinations do not count.');
const useHeaders = ['Good ID','Distinct uses','Required uses','Exception','Result','Authored destinations','Evidence'];
const useRows = itemUseAudit.items.map(i => [i.id,i.distinctUses,i.minimum,i.foodException?'Direct food':i.rocketException?'Final rocket part':'None',i.status,i.uses.map(u=>u.destination).join('\n'),i.uses.map(u=>u.evidence).join('\n')]);
const useTable=writeTable(itemUses,4,useHeaders,useRows,'ItemUsesTable','#C55A11');
itemUses.getRange('A:A').format.columnWidth=26;
itemUses.getRange('B:C').format.columnWidth=13;
itemUses.getRange('D:E').format.columnWidth=25;
itemUses.getRange('F:F').format.columnWidth=65;
itemUses.getRange('G:G').format.columnWidth=78;
itemUses.getRange(`A4:G${useTable.endRow}`).format.wrapText=true;
itemUses.getRange(`A4:G${useTable.endRow}`).format.autofitRows();
itemUses.getRange(`E5:E${useTable.endRow}`).conditionalFormats.add('containsText',{text:'NEEDS',format:{fill:'#FCE4D6'}});

const recipeHeaders = ['Recipe ID','Building','Faction','Recipe','Inputs','Outputs','Cycle hours','Power demand (hp)','Power output (hp)','Power role','Workers','Fuel','Storage / buffers','Source','Raw inputs','Raw outputs','Output qty','Cycle min','Input materials','Input qty','Byproducts','Stage','Balance intent','Data status'];
const recipeRows = [
['R001','Compost Yard','Compost',2,1,'Organic waste; water','4; 1',0,1,'None','1. Survival','Makes waste useful without requiring science grind'],
['R002','Fertilizer Works','Fertilizer',3,1,'Compost; water; algae','2; 1; 1',80,2,'Wastewater','2. Productive settlement','Improves farms but competes for water'],
['R003','Fish Pond','Fresh Fish',2,2,'Juvenile fish; feed','1; 1',0,1,'None','2. Productive settlement','Simple water-based food branch'],
['R004','Fish Hatchery','Juvenile Fish',4,2,'Adult fish; feed; water','1; 2; 1',55,2,'None','3. Industrial city','Supports aquaculture scale'],
['R005','Fishery Works','Smoked Fish',2,1,'Fresh fish; wood','3; 1',40,2,'None','2. Productive settlement','Preserves food for droughts'],
['R006','Fishery Works','Canned Fish',2,1.5,'Fresh fish; metal; oil','3; 1; 1',65,3,'Packaging scrap','3. Industrial city','Feeds retail and hospitals'],
['R007','Bakery','Bread',4,1,'Flour; water; sweetener','2; 1; 1',45,2,'None','2. Productive settlement','First advanced food factory'],
['R008','Food Factory','Emergency Ration',5,0.5,'Corn; logs','1; 0.1',120,2,'Wastewater','3. Industrial city','High throughput, strong power demand'],
['R009','Water Treatment Plant','Clean Water',8,1,'Dirty water; filter media','10; 1',110,4,'Concentrated waste','2. Productive settlement','Makes civic services sustainable'],
['R010','Arc Furnace Complex','High-grade Steel',4,1,'Iron ore; coal; flux','4; 2; 1',2500,8,'Slag','3. Industrial city','Conveyor-only landmark factory; target load 2,500 hp'],
['R011','Arc Furnace Complex','Alloy',2,1.5,'High-grade steel; copper; power','2; 1; 1',2500,8,'Slag','4. Wonder transition','Unlocks heavy industry; target load 2,500 hp'],
['R012','Polymer and Chemical Works','Polymer',3,1,'Crude oil; sulfur; water','3; 1; 2',3500,8,'Contaminated wastewater','4. Wonder transition','Valuable materials with waste cost; target load 3,500 hp'],
['R013','Polymer and Chemical Works','Lubricant',2,1,'Crude oil; fish oil; water','2; 1; 1',3500,6,'Contaminated wastewater','4. Wonder transition','Useful transport and factory input; target load 3,500 hp'],
['R014','Precision Machine Works','Machine Core',1,2,'Alloy; polymer; gears; science','2; 1; 2; 4',2200,6,'Scrap','4. Wonder transition','Capability item rather than bulk good; target load 2,200 hp'],
['R015','Food Synthesis Plant','Medical Food',2,1,'Canned fish; bread; medicine','1; 1; 1',90,6,'Clinical waste','3. Industrial city','Legacy food draft pending redesign. Hospital treats 30 patients through native condition recovery; it does not manufacture food.'],
['R016','Restaurant','Served meal effects (not an item)',1,15,'Fresh fish; berries; fermented mushrooms; eggplant rations','1; 1; 1; 1',civicPlan.restaurant.powerDemandHp,4,'None','3. Industrial city','Worker serves a seated guest after 15 minutes. One of each main food, plus available optional cake, coffee and fermented cassava/soybean. One Water if the diner can use its native +0.33 Thirst effect. Each good applies its own effects.'],
['R017','Badwater Treatment Works','Treated Water',6,1,'Badwater; chemicals; power','10; 1; 1',1500,5,'Concentrated waste','4. Wonder transition','Makes pollution a production decision; target load 1,500 hp'],
['R018','Deep Drill','Deep Ore',2,2,'Deep ore source; water','1; 3',1000,3,'None','5. Frontier','Consumes one unit from a finite authored source stockpile; target load 1,000 hp'],
['R019','Fume Scrubber','Recovered Chemicals',2,1,'Toxic fumes; water; filter media','5; 2; 1',750,2,'Concentrated waste','5. Frontier','Optional later hazard module; converts local fume-pocket inventory into recoverable chemicals; target load 750 hp'],
['R020','Uranium Processing Plant','Yellowcake',2,2,'Uranium ore; chemicals; water','3; 2; 2',5000,6,'Radon; concentrated waste','5. Frontier','Starts the nuclear fuel chain; target load 5,000 hp'],
['R021','Uranium Processing Plant','Enriched Fuel',1,3,'Yellowcake; machine cores; power','2; 1; 1',5000,6,'Radioactive waste','5. Frontier','Converts rare ore into a compact power input; target load 5,000 hp'],
['R022','Water Treatment Plant','Pure Water',8,1,'Water; filter media; power','10; 1; 1',150,4,'Concentrated waste','6. Launch program','Required before electrolysis'],
['R023','Electrolysis Plant','Hydrogen Gas; Oxygen Gas',3,2,'Pure water; power','8; 1',6000,5,'Wastewater','6. Launch program','Splits water into two isolated gas networks; target load 6,000 hp'],
['R024','Cryogenic Liquefaction Plant','Liquid Hydrogen; Liquid Oxygen',2,4,'Hydrogen gas; oxygen gas; cryocoolant; power','4; 32; 2; 1',10000,6,'Boiloff gas; contaminated coolant','6. Launch program','Consumes energy and materials to make launch-ready fuel; target load 10,000 hp'],
['R025','Cryogenic Tank','Launch fuel inventory',1,1,'Liquid hydrogen or liquid oxygen; power','1; 1',1000,0,'Vented gas if unpowered','6. Launch program','Powered storage keeps fuel launch-ready; target load 1,000 hp'],
['R026','Rocket Assembly Hangar','Rocket Airframe',1,6,'High-grade steel; alloy; treated glass; polymer; machine cores','12; 8; 4; 4; 2',12000,10,'Scrap','6. Launch program','Builds the structural stage; target load 12,000 hp'],
['R027','Rocket Assembly Hangar','Propulsion Package',1,8,'Alloy; machine cores; polymer; high-grade steel','10; 4; 6; 6',12000,10,'Scrap','6. Launch program','Builds engines and turbopumps; target load 12,000 hp'],
['R028','Mission Control','Guidance Computer',1,4,'Electronics; machine cores; archive data; power','4; 2; 1; 1',1500,4,'None','6. Launch program','Converts evidence into a flight system; target load 1,500 hp'],
['R029','Mission Control','Mission Payload',1,6,'Guidance computer; recovered artifacts; treated glass; power','1; 2; 2; 1',1500,4,'None','6. Launch program','Mission-specific payload; target load 1,500 hp'],
['R030','Rocket Assembly Hangar','Armed Rocket',1,12,'Rocket airframe; propulsion package; guidance computer; mission payload; liquid hydrogen; liquid oxygen','1; 1; 1; 1; 24; 192',12000,10,'Spent stage','6. Launch program','Final assembly consumes complete parts and cryogenic fuel; target load 12,000 hp'],
['R031','Launch Pad','Orbital Observatory',1,6,'Armed rocket; mission control; liquid hydrogen; liquid oxygen; power','1; 1; 12; 96; 1',25000,2,'Exhaust','6. Launch program','First launch reveals orbital records; target load 25,000 hp'],
['R032','Launch Pad','Recovery Probe',1,8,'Armed rocket; mission control; liquid hydrogen; liquid oxygen; power','1; 1; 12; 96; 1',25000,2,'Exhaust','6. Launch program','Second launch retrieves a rare data package; target load 25,000 hp'],
['R033','Launch Pad','Long-Range Beacon or Ark',1,12,'Armed rocket; mission control; liquid hydrogen; liquid oxygen; power; archive data','1; 1; 12; 96; 1; 4',25000,2,'Exhaust','6. Launch program','Final mission completes the chosen ending; target load 25,000 hp'],
['R034','Technical School','Industrial License',1,8,'Books; paper; food; power','2; 2; 1; 1',180,4,'None','4. Wonder transition','One-time commissioning license for heavy industrial buildings'],
['R035','Technical School','Specialist License',1,12,'Industrial license; machine cores; books; power','1; 1; 2; 1',240,4,'None','5. Frontier','Enables specialist capacity for drilling, nuclear, and cryogenic work'],
['R036','Mission Control','Flight License',1,12,'Specialist license; electronics; recovered artifacts; power','1; 2; 1; 1',300,4,'None','6. Launch program','One-time launch workforce license'],
['R037','Nuclear Reactor','Mechanical Power',75000,60,'Enriched fuel; reactor coolant water','1; 180',0,6,'Radioactive waste; contaminated water; meltdown risk if coolant buffer empties','5. Frontier','Nominal 75,000 hp generator; playtest range 50,000–100,000 hp; coolant is a continuous operating input'],
['R038','Radioactive Waste Refinery','Badwater; Recovered Minerals','8; 1',60,'Radioactive waste; chemicals; water','1; 2; 4',8000,6,'Radon; residual radioactive sludge','5. Frontier','Persistent waste route: produces badwater and a useful mineral fraction; storage lock prevents deletion'],
['R039','Deep Mine','Deep Ore',4,2,'Water','12',4000,6,'None','5. Frontier','Permanent mine branch: requires a Deep Ore Vein understructure and trades a heavy 4,000 hp load for an indefinite source'],
];
const alignedRecipeRows = recipeRows.map((r) => {
  const [id, building, output, outputQty, cycleMin, inputMaterials, inputQty, powerDemand, workers, byproducts, stage, balanceIntent] = r;
  const names = String(inputMaterials).split(';').map((v) => v.trim()).filter(Boolean);
  const quantities = String(inputQty).split(';').map((v) => v.trim());
  const inputs = names.map((name, i) => `${quantities[i] ?? ''} ${name}`.trim()).join('; ');
  const isPowerOutput = String(output).toLowerCase().includes('mechanical power');
  const powerOutput = isPowerOutput ? Number(String(outputQty).match(/[0-9]+(?:\.[0-9]+)?/)?.[0] ?? 0) : 0;
  const recipeDemand = isPowerOutput ? 0 : powerDemand;
  return [id, building, 'Iron Teeth', output, inputs, `${outputQty} ${output}`, Number(cycleMin) / 60, recipeDemand, powerOutput, powerRole(recipeDemand, powerOutput), workers, '', '', building==='Restaurant'?restaurantSource:'Deep Frontier design draft', inputMaterials, output, outputQty, cycleMin, inputMaterials, inputQty, byproducts, stage, balanceIntent, building==='Restaurant'?restaurantStatus:'Mod draft; vanilla-aligned columns'];
});
for(const r of restaurantRecipes) {
  alignedRecipeRows.push([r.Id,'Restaurant','Iron Teeth',goodName(r.Id),amountsText(r.Ingredients.map(g=>[g.Id,g.Amount])),amountsText(r.Products.map(g=>[g.Id,g.Amount])),r.CycleDurationInHours,civicPlan.restaurant.powerDemandHp,0,'Consumer',civicPlan.restaurant.workers,
    'None','32 per stocked good',restaurantSource,JSON.stringify(r.Ingredients),JSON.stringify(r.Products),r.Products[0].Amount,r.CycleDurationInHours*60,r.Ingredients.map(g=>goodName(g.Id)).join('; '),r.Ingredients.map(g=>g.Amount).join('; '),'None','3. Industrial city',
    r.Id==='SweetBerryCake'?'Exclusive table dessert; +2 food wellbeing when satisfied. No exported cake.':'Exact native fermenter recipe; prepared food available for seated service.',restaurantStatus]);
}
for(const r of construction.recipes) {
  const b=construction.buildings.find(b=>b.recipes.includes(r.id));
  if(!b) throw new Error(`No construction producer for ${r.id}`);
  alignedRecipeRows.push([r.id,b.name,'Iron Teeth',r.name,amountsText(r.inputs),amountsText(r.outputs),r.hours,b.hp,0,'Consumer',b.workers,
    r.fuel ? `${r.fuel}: 1 per ${r.fuelCycles} cycle; capacity ${r.fuelCapacity}` : 'None','4 cycles',constructionSource,
    JSON.stringify(r.inputs),JSON.stringify(r.outputs),r.outputs[0][1],r.hours*60,r.inputs.map(([id])=>goodName(id)).join('; '),r.inputs.map(([,q])=>q).join('; '),'None',
    '3. Industrial city','First concrete before nuclear; permanent quarries after starter concrete',constructionBuildingStatus.get(b.id)]);
}
const hatcheryRecipeIndex=alignedRecipeRows.findIndex(r=>r[0]==='R004');
if(hatcheryRecipeIndex<0)throw Error('Missing draft hatchery recipe to replace');
alignedRecipeRows[hatcheryRecipeIndex]=juvenileRecipeRow;
for(const id of ['R003','R005','R006']) {
  const row=alignedRecipeRows.find(r=>r[0]===id);if(!row)throw Error('Missing aquaculture draft '+id);
  row[recipeHeaders.indexOf('Data status')]='Design only; not an active recipe on this building';
}
alignedRecipeRows.push(...aquacultureRecipeAdds);
const medicalRecipeIndex=alignedRecipeRows.findIndex(r=>r[0]==='R015');
if(medicalRecipeIndex<0)throw Error('Missing medical food draft to replace');
alignedRecipeRows[medicalRecipeIndex]=medicalFoodRecipe;
const cannedFishRecipeIndex=alignedRecipeRows.findIndex(r=>r[0]==='R006');
if(cannedFishRecipeIndex<0)throw Error('Missing canned fish draft to replace');
alignedRecipeRows[cannedFishRecipeIndex]=grocerySupplyRecipes[0];
alignedRecipeRows.push(grocerySupplyRecipes[1]);
alignedRecipeRows.push(researchRecipe);
const recipeTable = writeTable(recipes, 1, recipeHeaders, alignedRecipeRows, 'RecipesTable', '#ED7D31');
const recipeEnd = recipeTable.endRow;
const recipeEndCol = recipeTable.colLetter(recipeTable.endCol);
recipes.getRange(`A1:${recipeEndCol}${recipeEnd}`).format.wrapText = true;
recipes.getRange(`A1:${recipeEndCol}${recipeEnd}`).format.autofitRows();
recipes.getRange('A:A').format.columnWidth = 12;
recipes.getRange('B:B').format.columnWidth = 28;
recipes.getRange('C:C').format.columnWidth = 16;
recipes.getRange('D:D').format.columnWidth = 24;
recipes.getRange('E:F').format.columnWidth = 34;
recipes.getRange('G:K').format.columnWidth = 15;
recipes.getRange('L:M').format.columnWidth = 25;
recipes.getRange('N:P').format.columnWidth = 42;
recipes.getRange('Q:X').format.columnWidth = 24;

const progressionHeaders = ['Gate ID','Faction','Stage','Player goal','Science range','Required buildings','Required items','Infrastructure gate','Suggested trigger','Unlocks','Why now','Player-facing cue','Target colony size','Vanilla comparison','Status','Data status'];
const progressionRows = [
['G001','1. Survival','Keep the colony fed through the first drought','0–100','Farmhouse; water storage','Basic crops; compost','Reliable water and food storage','First drought survived','Compost Yard; Park; basic food variety','Turns survival waste into resilience','A farm panel shows depleted soil','10–30','Planning'],
['G002','2. Productive settlement','Make food variety and farming reliable','100–300','Compost Yard; Mill; Clinic','Fertilizer; flour; medicine','Basic power and water treatment','Nutrition need remains unmet for 3 days','Fertilizer Works; Bakery; Fish Pond; Market Hall','Creates a clear response to well-being needs','A new nutrition need points to a recipe','30–80','Planning'],
['G003','2. Productive settlement','Build a comfortable town','250–500','Bakery; Market Hall; Clinic; Park','Bread; fresh fish; decorations','Local delivery routes','Housing reaches a density threshold','Grocery Store; Restaurant preview; School preview','Makes civic growth visible before industry','A town milestone unlocks services','50–100','Planning'],
['G004','3. Industrial city','Create a dedicated production district','500–900','Substation; conveyors; storage','Metal blocks; gears; fertilizer','Power network and belt routes','A production bottleneck is detected','Food Factory; Arc Furnace Complex; Hospital','Factory scale follows surface needs','Statistics identify a shortage','80–180','Planning'],
['G005','3. Industrial city','Support a modern city','800–1400','Hospital; Grocery Store; Food Factory','Medicine; canned fish; packaged food','Stable power and delivery network','Population exceeds 100 and sick days rise','School; Public Pool; advanced retail','Services solve visible workforce problems','A civic service report requests capacity','100–220','Planning'],
['G006','4. Wonder transition','Complete a wonder and choose a capability branch','1400–2200','Wonder; substations; factories','Alloys; machine parts; advanced food','Large factory district','Wonder completion','Agricultural, Industrial, Social, Environmental, or Exploration branch','Wonders start the next era','Wonder completion reveals five paths','180–350','Planning'],
['G007','5. Frontier','Survey and connect a new resource sector','2200–3500','Survey Station; Freight Elevator','Machine Core; High-grade Steel','Vertical transport and surface logistics','Survey milestone completed','Deep Drill; Underground Settlement; frontier resources','Underground growth is earned by surface capacity','Survey map reveals a new objective','350+','Planning'],
['G008','6. Mystery','Trace badwater and humanity’s disappearance','3500+','Human Archive; treatment works','Recovered Artifacts; treated water','Frontier logistics and civic stability','Archive evidence chain completed','Endgame choices and world-state changes','Narrative follows industrial capability','A recovered signal names the next site','Endgame','Planning'],
['G009','6. Launch program','Build and launch a rocket mission','12000–18000','Nuclear Reactor or large renewable grid; Rocket Assembly Hangar; Mission Control','Alloys; polymers; machine cores; liquid hydrogen; liquid oxygen; archive data','Cryogenic fuel chain and launch power','Human Archive evidence identifies an orbital record','Orbital Observatory; Recovery Probe; Long-Range Beacon or Ark','The final wonder consumes the complete industrial system','Mission control displays the next launch objective','500+','Planning'],
['G010','5. Frontier','Train and support specialist workers','Advanced research rebalance pending','School; Technical School; Restaurant; Grocery Store; Hospital','Actual foods; medicine; training supplies','Persistent individual education plus wellbeing at safe work boundaries','First advanced factory is commissioned','Qualified advanced machine operators','Basic recovery services and reactor safety cannot be locked out','Machine panel shows required and current education/wellbeing','180–350','Planning'],
['G011','5. Frontier','Contain, refine, and route radioactive waste','8000–15000','Nuclear Reactor; Radioactive Waste Vault; Radioactive Waste Refinery','Radioactive waste; chemicals; water; badwater storage','Sealed storage and a non-deletion waste route','First reactor produces radioactive waste','Badwater conversion; recovered minerals; bounded radiation cleanup','Waste remains a permanent logistics obligation instead of an inventory exploit','A storage panel warns that demolition is locked until waste is removed','350+','Planning'],
['G012','5. Frontier','Replace finite starter stockpiles with a permanent mine','6000–9000','Deep Mine; Survey Station; Technical School','Deep Alloy; Water; qualified workers','A placed Deep Ore Vein, 4,000 hp supply, and water logistics','Deep Ore source falls below the reserve threshold','Deep Mine; permanent Deep Ore throughput; larger automation districts','The player has a clear next step when the finite source starts to run out','The source panel recommends surveying a permanent vein','350+','Planning'],
];
const alignedProgressionRows = progressionRows.map((r) => [r[0], 'Iron Teeth', r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], 'Uses vanilla science/material/well-being gates; no arbitrary layer cap', r[12], 'Mod planning draft']);
alignedProgressionRows.push(
  ['G013','Iron Teeth','3. Industrial city','Make the first concrete','300–1000','Sandstone Pit; Limestone Pit; Stone Crusher; Cement Kiln; Concrete Mixer','Sandstone; limestone; dirt; logs; water','Authored surface deposits; 750 hp processing line','Advanced foundations require concrete','Concrete; permanent quarries','All startup buildings use vanilla materials','Pit descriptions point to crusher/kiln/mixer','80–180','Vanilla scrap-to-mine progression','Processing tested; finite gathering coverage pending',constructionStatus],
  ['G014','Iron Teeth','3. Industrial city','Secure permanent construction minerals','4000','Sandstone Quarry; Limestone Quarry','120 concrete; planks; gears; metal blocks; water','Both deep seams; 1500 hp per quarry','Surface reserves are running low','Indefinite sandstone and limestone','Keep finite deposits useful without a resource dead end','Quarry menu identifies its required seam','80–180','Native mine understructure placement','Native extraction and reload tested',constructionStatus]
);
alignedProgressionRows.push(
  ['G015','Iron Teeth','5. Frontier','Fund nuclear research',1000000,'Materials Laboratory; Applied Research Institute; Advanced Science Center','Aluminum; electronics; actual service foods','8,000 science per working hour per proposed advanced center; 12,000 hp each','Research throughput becomes the bottleneck','Nuclear Reactor','1,000,000 science takes 7.8125 days at 16 hours/day with one center','Show research rate and remaining working days','Endgame','Native science unlock; industrial research rates proposed','Reactor science authored; laboratories pending','tools/frontier_progression.json'],
  ['G016','Iron Teeth','4. Wonder transition','Build a reusable aluminum industry','Not balanced','Bauxite Mine; Alumina Refinery; Aluminum Smelter','Bauxite; alumina; water','6,000 / 8,000 / 40,000 hp proposed demands; badwater outlet','Heavy steel structures and electronics need a new material','Aluminum; lightweight bridges; scaffolds; research; rocket frames','Every intermediate has at least two planned consumers','Finite bauxite points to a permanent mine','Industrial city','Scrap-to-permanent-mine pattern','Design only','No recipes or source entities implemented'],
  ['G017','Iron Teeth','4. Wonder transition','Turn oil into general materials','Not balanced','Chemical Works; Polymer Processing; Equipment Workshop','Crude oil; polymer resin; plastic','Oil supply; power; badwater storage','PPE and advanced infrastructure require refined materials','Reusable hazmat suits; pipe liners; packaging; insulation','Resin and plastic have several useful destinations','Show the complete oil-to-equipment recipe chain','Industrial city','Native recipes and inventories; equipment behavior pending','Design only','Legacy Polymer replacement requires explicit migration'],
  ['G018','Iron Teeth','4. Wonder transition','Build taller transport and factory districts','Not balanced','Reinforced blocks; improved overhangs; bridges; scaffolds','Concrete; high-grade steel; aluminum; resin composites','Native support and clear occupation volumes','Factory space or transport routes constrain growth','Clear spans and stackable logistics structures','Additional material uses change useful building capabilities','Preview supports and occupied cells before construction','Industrial city','Native support rules; no arbitrary layer cap','Design only','Exact spans and dimensions require geometry and placement validation'],
  ['G019','Iron Teeth','5. Frontier','Centralize stock and shield dangerous materials','Not balanced','Advanced Warehouse; Shielded Warehouse; shielded liquid pipes','Plastic liners; concrete; metal; hazmat suits','Shared capacity; selected goods; explicit per-item limits; haulers and belts','Several separate stores make logistics cumbersome','Multiple stored goods; protected waste handling','Shielding blocks stored radiation; waste still requires refinement','Show total capacity, per-good limits and non-empty waste demolition lock','Industrial city','Native multi-good inventory API; storage UI/hauling integration pending','Design only','Dimensions, capacity and construction recipes not yet authored']
);
alignedProgressionRows.push(['G020','Iron Teeth','3. Industrial city','Open the restaurant',restaurantBlueprint.BuildingSpec.ScienceCost,
  'Restaurant; native food production and fish supply',amountsText(restaurantBlueprint.BuildingSpec.BuildingCost.map(g=>[g.Id,g.Amount])),
  '400 hp; four staff; path access; four main menu foods; water for thirsty diners',
  'Stable food variety and power make table service useful','Dining wellbeing; native food benefits; unique table-only berry cake',
  'Existing foods gain a shared service destination; workers divide cooking and table service',
  'Dining panel shows missing food, drinks, staffing and seated/waiting guests','Industrial city',
  'Native science/material unlock and fermenter recipes',restaurantStatus,'Exact blueprint gates; unseeded hatchery-to-fishery supply chain still needs acceptance']);
alignedProgressionRows.push(['HydroInfrastructure','Iron Teeth','4. Wonder transition','Build reinforced dams and regulate their discharge',
  `Blocks 600–2200; overhang/scaffold 5000–6000; turbine ${hydroCatalog.science.toLocaleString('en-US')}`,'Concrete levees; reinforced dam blocks; overflow dams; controlled turbine',
  'Concrete; metal; aggregate; cement','Starter concrete chain; a suitable reservoir and outlet',
  'Factory power demand and water storage grow together','Stackable infrastructure; renewable hp varies with actual flow and head',
  'Concrete has multiple construction uses; native water passes downstream; dependency pump-loop energy remains unresolved',
  'Display actual flow, requested m³/s limit, head and hp','Industrial city',
  'Native support/obstacles, water limits and automation',hydroCatalog.status,
  hydroCatalog.balanceStatus]);
alignedProgressionRows.push(aquacultureProgression);
alignedProgressionRows.push(groceryProgression);
updateAquacultureRows(alignedProgressionRows,progressionHeaders,hospitalProgressionUpdates);
alignedProgressionRows.push(['MaterialsResearch','Iron Teeth','4. Wonder transition','Scale science with industrial samples',12000,
 'Materials Laboratory; gear and concrete production','4 Gear; 2 Concrete; 1 MetalBlock per batch',
 '600 hp and four workers; 10x9x9 building with supported layer-2 terrace','Basic science cannot fund the next industrial branch quickly enough',
 '800 science per two working hours','Reusable construction materials also support research',
 'Keep gears, concrete and metal supplied before adding more laboratories','Industrial settlement',
 'Native science recipe; no research-token good','Authored; corrected production test pending','tools/research_content.json']);
const progressionTable = writeTable(progression, 1, progressionHeaders, alignedProgressionRows, 'ProgressionTable', '#A5A5A5');
const progressionEnd = progressionTable.endRow;
const progressionEndCol = progressionTable.colLetter(progressionTable.endCol);
progression.getRange(`A1:${progressionEndCol}${progressionEnd}`).format.wrapText = true;
progression.getRange(`A1:${progressionEndCol}${progressionEnd}`).format.autofitRows();
progression.getRange('A:A').format.columnWidth = 11;
progression.getRange('B:B').format.columnWidth = 16;
progression.getRange('C:C').format.columnWidth = 23;
progression.getRange('D:D').format.columnWidth = 32;
progression.getRange('E:E').format.columnWidth = 14;
progression.getRange('F:H').format.columnWidth = 28;
progression.getRange('I:L').format.columnWidth = 32;
progression.getRange('M:P').format.columnWidth = 24;

const feasibilityHeaders = ['Feature ID','Area','Feasibility','V1 implementation','Engine boundary','Dependencies','First slice','Status'];
const feasibilityRows = [
  ['F001','Map authoring','High','Duplicate a vanilla .timber map, add bottom dirt and extra Z layers with Map Transformer, then hand-author lower sectors.','Transform once and reload the generated save; custom Terrain Height keeps the map tied to the height mod.','Map Transformer; Moddable Timberborn','One 8-layer lower sector and one shaft','Recommended'],
  ['F002','Runtime map expansion','Low','Unlock authored lower sectors with Survey Stations.','Do not resize or generate terrain during normal play; keep runtime transformation as research.','None beyond core mod','Survey milestone reveals an existing room','Defer'],
  ['F003','Underground rooms','Medium-high','Use ordinary buildings, paths, platforms, airlocks and risers inside authored chambers.','No generic cave generator or dig-anywhere model in v1.','Map Transformer; visible-layer QoL optional','One room with lift, pipe riser and power riser','Recommended'],
  ['F004','Underground settlement','Medium-high','Place standard housing, workplaces, food and district services in a lower sector.','Playtest pathing, lighting, district range and service reach; no special citizen simulation.','Powered Tubeway optional; transport stack','Ten-beaver outpost','Recommended'],
  ['F005','Custom goods and recipes','High','Add standard specs, blueprints and recipes with explicit inputs, outputs, gates and storage.','Novel UI and entity behavior require code; every good needs a visible use.','Official modding tools; Moddable Timberborn','Deep ore to alloy','Recommended'],
  ['F006','Surface agriculture and food','High','Use ordinary workplaces and recipes for compost, fertilizer, greenhouse, bakery and packaged food.','Keep each tier to a short chain so surface progression stays readable.','Core game; Expanded Storage optional','Compost to fertilizer to bread','Recommended'],
  ['F007','Civic services','High','Use Well-Being buildings with visitors, workers, storage and service recipes.','New needs or status effects are a separate code feature; start with existing needs and supply chains.','Core game','Clinic, grocery, restaurant','Recommended'],
  ['F008','Fish farming','Medium-high','Use a water-dependent workplace plus Fish goods and hatchery recipes.','Start with inventory-based production; delay individual fish entities and migration.','Core water system; pipes optional','Pond to fresh fish','Recommended'],
  ['F009','Conveyor-only factories','High','Expose fixed solid ports and build around belt lifts, splitters and high power demand.','Detect the belt package and keep hauling fallback for non-required lines.','Conveyor Belts v2','One belt-fed alloy line','Recommended'],
  ['F010','Pipes and Pump to Tank','High','Use pipe ports, tanks and the existing Pump to Tank transfer behavior.','Test custom fluid types; if rejected, retain tank and pocket inventories with the same recipes.','Timber Pipes; Pump to Tank; Expanded Storage','Water or oil tank loop','Recommended'],
  ['F011','Solar, lines and flywheels','High','Register consumers and generators against the existing mechanical network.','Extract exact package profiles; do not create a second power system.','Northforge Solar; Power Lines; Flywheels','Solar plus flywheel plus substation','Recommended'],
  ['F012','Coal, oil and ore veins','Medium','Use pre-authored resource nodes or claims that feed extractor recipes and finite storage.','Runtime terrain-cell scanning and natural vein depletion need code; explicit nodes come first.','Map authoring; Expanded Storage','One authored oil or ore node','Prototype'],
  ['F013','Deep drilling','Medium-high','Clone Mine/Aquifer Drill-style workplace with power, workers, drill heads and a selected source node.','Do not promise arbitrary drilling into any terrain block in v1.','Conveyors; Timber Pipes; power stack','One drill at one vein','Recommended'],
  ['F014','Gas and fume pockets','Optional later','Use named custom goods plus per-pocket inventories and detector/scrubber buildings after the core factory loop is stable.','Avoid full diffusion, buoyancy, pressure and world-fluid simulation; keep this branch optional if custom fluids are rejected.','Timber Pipes; Pump to Tank; Expanded Storage','One low pocket and scrubber','Deferred'],
  ['F015','Hazards and contamination','Optional later','Use bounded area alarms, machine shutoff, contaminated inputs and recovery recipes.','Start with reactor radiation or badwater isolation; defer lethal gas exposure and a global hazard solver.','Gas Detector; Fume Scrubber','Detector disables a machine','Deferred'],
  ['F016','Oil, polymers and nuclear chain','Medium-high','Use linear recipe chains with power demand, waste goods and unlock gates.','Represent radiation as an area state and byproduct; no heat or maintenance simulation.','Timber Pipes; conveyors; storage','Refinery plus one waste outlet','Planning'],
  ['F017','Badwater source mystery','High content / Medium systems','Use Archive buildings, map objects, science milestones and staged objectives.','If a novel quest API is unavailable, use staged unlocks and evidence items.','Core progression; authored map','Human Archive chain','Planning'],
  ['F018','No heat or maintenance','High','Make power, inputs, storage, workers, hazards and waste the operating constraints.','Avoid hidden universal upkeep and repair loops.','Core game','All machines use clear stop/throttle states','Design rule'],
  ['F019','Rocket program','Medium-high','Use explicit rocket component recipes, cryogenic gas goods, powered tanks, launch work orders, and staged mission rewards.','Do not simulate orbital physics or require nuclear power; use renewable power plus storage as a slower, larger-footprint fallback.','Conveyors; Timber Pipes; Power Lines; nuclear optional','Orbital Observatory launch','Planning'],
  ['F020','Specialist workforce','Medium-high','Use schools, one-time commissioning licenses, and a colony-level specialist capacity pool for advanced machines.','Do not hard-lock individual beavers to jobs in v1; defer worker identity patches until supported APIs are proven.','School; Technical School; core progression','Technical School commissions one reactor','Planning'],
  ['F021','Radioactive waste custody','Medium-high','Make radioactive waste a persistent good that can be moved only through sealed storage or a Radioactive Waste Refinery that converts it into badwater and recovered minerals.','Do not allow manual deletion or demolition of storage containing waste; if a save is corrupted, migrate the good to a locked emergency vault.','Nuclear branch; Timber Pipes; Pump to Tank; Expanded Storage','Reactor output to locked vault to badwater refinery','Planning'],
];
const feasibilityTable = writeTable(feasibility, 1, feasibilityHeaders, feasibilityRows, 'FeasibilityTable', '#70AD47');
feasibility.getRange(`A1:H${feasibilityTable.endRow}`).format.wrapText = true;
feasibility.getRange(`A1:H${feasibilityTable.endRow}`).format.autofitRows();
feasibility.getRange('A:A').format.columnWidth = 12;
feasibility.getRange('B:B').format.columnWidth = 24;
feasibility.getRange('C:C').format.columnWidth = 18;
feasibility.getRange('D:E').format.columnWidth = 48;
feasibility.getRange('F:F').format.columnWidth = 34;
feasibility.getRange('G:G').format.columnWidth = 34;
feasibility.getRange('H:H').format.columnWidth = 16;
feasibility.getRange(`C2:C${feasibilityTable.endRow}`).conditionalFormats.add('containsText', { text: 'Low', format: { fill: gold } });
feasibility.getRange(`C2:C${feasibilityTable.endRow}`).conditionalFormats.add('containsText', { text: 'Medium', format: { fill: '#FFF2CC' } });

const transportHeaders = ['System ID','Faction','System','Mode','Material class','Base capacity / min','Power demand (hp)','Requires','Stackable / vertical','Range','Best use','Primary bottleneck','Dependency adapter','Vanilla baseline','Stacking / layering rule','Source','Data status'];
const transportRows = [
['T001','Beaver hauling','Manual','Solid',12,0,'Paths; workers','No / Limited','Local','Early buildings','Worker time','Core'],
['T002','Cart route','Manual vehicle','Solid',30,0,'Paths; hauling post','No / Limited','Local','Farm and market supply','Worker time','Core'],
['T003','Conveyor Belts v2','Belt','Solid',120,20,'Power; belt network','Yes / Yes','District','Factories; vertical lifts','Belt throughput','Conveyor Belts v2'],
['T004','Timber Pipes','Pipe','Liquid',80,10,'Pipe network','Yes / Yes','District','Water, oil, chemicals','Pressure / flow','Timber Pipes'],
['T005','Powered Tubeway','Tube','Solid package',90,35,'Power; stations','Yes / Yes','Regional','High-value packages','Station throughput','Powered Tubeway'],
['T006','Vertical Belt Lift','Belt lift','Solid',100,35,'Conveyor Belts v2; substation','Yes / Yes','Vertical','Underground-to-surface','Lift capacity','Conveyor Belts v2'],
['T007','Freight Elevator','Lift','Solid / fluid',240,100,'Machine cores; substation','No / Yes','Vertical','Megafactories and shafts','Loading bays','Core plus optional belt adapter'],
['T008','Wormhole Station','Teleport','Solid package',180,80,'Stations; power','No / Yes','Regional','Rare or high-value goods','Station capacity','Wormhole/Ring mod'],
['T009','Ring Teleporter','Teleport','Solid package',300,140,'Stations; advanced power','No / Yes','Regional','Late-game bulk transfer','Power demand','Wormhole/Ring mod'],
['T010','Power Lines','Power','Electricity',0,0,'Substations; generators','Yes / Yes','District','Factory power distribution','Grid capacity','Power Lines'],
['T011','Flywheel Bank','Storage','Power',0,5,'Power network','No / Yes','District','Power buffering','Storage capacity','Flywheels'],
['T012','Pump to Tank','Pump','Liquid',100,25,'Water source; tank','Yes / Yes','Local','Water transfer','Pump capacity','Pump to Tank'],
];
const alignedTransportRows = transportRows.map((r) => [r[0], 'Iron Teeth', r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], r[1] === 'Beaver hauling' || r[1] === 'Cart route' ? 'Vanilla transport baseline' : 'Optional dependency or Deep Frontier transport', String(r[7]).includes('Yes') ? 'No artificial layer cap; obey piece blueprint support' : 'Per-piece blueprint rule', r[11] === 'Core' ? 'Timberborn vanilla' : `Dependency: ${r[11]}`, 'Iron Teeth transport planning']);
alignedTransportRows.push(['T013','Iron Teeth','Concrete supply chain','Native hauling; mixer belts/pipes/cable verified','Aggregate/Cement in; Concrete out; Water inlet',null,null,'Water (7,5,0) Right OpenIn; cable grid (7.84,5.84,1.80); Sp1 belt 2 hp/piece; pump 50 hp','Native supports','Native range; per-piece rules; tested 250 hp mixer + six belts + pump = 312 hp','First concrete and quarry investment','Mixer 12 Aggregate / 4 Cement / 8 Water buffers','Belts/Pipes main/reload81; Power Lines main82/reload83','Cable/valve stops; wrong goods/faces rejected; exact saved queues, cable endpoints and conservation','No arbitrary layer cap',constructionSource,constructionStatus]);
alignedTransportRows.push(['T014','Iron Teeth','Advanced multi-good warehouse','Shared inventory','Selected solid goods',null,0,'Advanced materials; exact costs pending','Pending model supports','Hauling routes and attached belts','Buffer several factory inputs/outputs in one building','Shared capacity and per-item stock limits','Native Inventory; Conveyor Belts; TimberUi','Inventory already supports multiple goods; stockpile UI requires extension','No arbitrary layer cap; author clear supports','tools/frontier_progression.json','Design only; runtime integration pending']);
alignedTransportRows.push(['T015','Iron Teeth','Shielded storage and pipes','Protected inventory / pipe','Radioactive solids / liquids separately',null,null,'Shielding materials; reusable hazmat equipment','Pending piece geometry','Native hauling/belt and pipe networks','Move and store radioactive goods without emitting stored radiation','Finite throughput; coolant remains independent; waste cannot be deleted','Conveyor Belts for solids; Timber Pipes for liquids','No claim that dependency pieces provide radiation protection','Native support/occupation rules','tools/frontier_progression.json','Design only; radiation and transport tests pending']);
alignedTransportRows.push(['T016','Iron Teeth','Restaurant supply','Native input inventory','Foods, water and selected cooking ingredients',null,civicPlan.restaurant.powerDemandHp,'Staff; complete main menu; shaft power','Authored doors at 0/2/4/6','District hauling','Deliver raw ingredients and meals to one kitchen','Kitchen production and table service share four staff','Belts and pipes require dedicated runtime checks','Public input; no output or counter eating','Four clear rooftop support cells; native support rules',restaurantSource,restaurantStatus]);
alignedTransportRows.push(['DamDischarge','Iron Teeth','Dam-base turbine outlet','Native world-water flow',
  'Water and contamination; not inventory Water',null,0,'Player-set maximum m³/s; actual flow limited by reservoir/head',
  'Sealed dam with a clear downstream outlet','Same native water simulation',
  'Release water and generate hp from measured through-flow and head','Closed/dry/blocked/reverse/equalized conditions stop generation',
  'Native IWaterService and automation; native shaft graph and authored Power Lines anchor','Pump/turbine energy and water conservation require runtime checks',
  'Native support and sealing rules','docs/hydroelectric-construction.md',hydroCatalog.status]);
alignedTransportRows.push(aquacultureTransport);
alignedTransportRows.push(hospitalTransport);
alignedTransportRows.push(groceryTransport);
const transportTable = writeTable(transport, 1, transportHeaders, alignedTransportRows, 'TransportTable', '#4472C4');
const transportEnd = transportTable.endRow;
const transportEndCol = transportTable.colLetter(transportTable.endCol);
transport.getRange(`A1:${transportEndCol}${transportEnd}`).format.wrapText = true;
transport.getRange(`A1:${transportEndCol}${transportEnd}`).format.autofitRows();
transport.getRange('A:A').format.columnWidth = 12;
transport.getRange('B:B').format.columnWidth = 16;
transport.getRange('C:C').format.columnWidth = 24;
transport.getRange('D:E').format.columnWidth = 16;
transport.getRange('F:G').format.columnWidth = 15;
transport.getRange('H:M').format.columnWidth = 28;
transport.getRange('N:Q').format.columnWidth = 30;

const dependencyHeaders = ['Dependency ID','Mod / library','Target 1.1 status','Compatibility / package','Purpose','Verified buildings / mechanics','Verified costs / unlocks / recipes','Required dependencies','Integration rules','Source','Confidence','Next check'];
const dependencyRows = [
  ['D001','Pump to Tank','Installed 1.1 package; Version 1.0.9','Workshop 3681283725; Version-1.1 manifest; minimum game version 1.1.2.4','Direct tank-to-tank fluid logistics','Mechanical pump scans vertically for a compatible tank; supports tank → pump → tank; strict Water/Badwater filter matching; valid pairs bypass world spill; primed pump draws its full rated hp while transfer is blocked','No new production recipe; patches existing pump/tank behavior. Exact hp/capacity still require blueprint extraction.','Harmony >= 2.4.1','Use the existing mod through a detected adapter; do not reimplement it. Missing required Pump to Tank must be reported explicitly.','https://steamcommunity.com/workshop/filedetails/?id=3681283725','High','Capture the local blueprint hp and capacity before balancing.'],
  ['D002','Flywheels','Installed 1.1 package; Version 4.1.1.15','Workshop 3322428023; Version-1.1 manifest; minimum game version 1.1.2.4','Power storage and smoothing','Flywheels store surplus network power and discharge into deficits; stored power decays when the network has no surplus; Junctions redirect power but do not store it','Blueprint dimensions, costs, capacity, and decay values still require extraction.','None declared in the 1.1 manifest','Detect flywheel network types and use them as the power buffer; never assume capacity until the package profile is captured.','https://steamcommunity.com/sharedfiles/filedetails/?id=3322428023','High mechanics / Medium exact profile','Extract the Version-1.1 building profile.'],
  ['D003','Wormhole and Ring Teleporter Stations','Installed 1.1 package; Version 0.4.0','Workshop 3813842276; root manifest; minimum game version 1.1.0.0','Long-distance beaver and package transport','Wormhole Station links stations in one district and enables instant beaver travel; Ring Station pairs with a Remote Ring within 30 tiles; both consume Extract per crossing and have internal stores','Wormhole Station: 1x1, 20 Planks + 20 Metal Blocks + 50 Extract, unlock 5000 science; Ring Station: 1x1, 20 Planks + 20 Metal Blocks + 25 Extract, unlock 5000 science; one Extract per ten crossings; Remote Ring is free','None declared in the manifest','Use stations for rare/high-value goods and emergency workforce routing; keep bulk throughput on belts and pipes.','https://steamcommunity.com/sharedfiles/filedetails/?id=3813842276','High','Capture the installed blueprint profile before balancing.'],
  ['D004','Timber Pipes','Installed 1.1 package; Version 11.4.0','Workshop 3801726769; version-1.1 manifest; minimum game version 1.1.1','Liquid transport for water, badwater, oil, and chemicals','Horizontal pipes share tiles with Paths; platforms can be built over them; vertical pieces need Double Platform; headlift matters; unconnected outlets do not spill; Outfall Pipe is the liquid outlet; networks contaminate when multiple liquid types enter','One-way Valve: 1 Log + 1 Gear, unlock 50; One-way Elbow: 1 Log + 1 Gear, unlock 100; Pipe Pump: 8 Planks + 8 Gears, unlock 200; Riser: 1 Plank, unlock 20; Riser Pipe Pump: 12 Planks + 8 Gears, unlock 150; Outfall Pipe: 12 Logs + 1 Gear, unlock 350; default capacity about 1 m³ / 5 goods','Moddable Timberborn; Moddable Tool Groups; eMka.ModSettings; ExtendedOptionalModSupport optional','Use pipe ports for liquid factories; keep each liquid network isolated and test custom gas goods before treating them as native fluids.','https://steamcommunity.com/sharedfiles/filedetails/?id=3801726769','High','Pin the local package and test custom fluid compatibility.'],
  ['D005','Northforge - Solar Panel','Installed package 1.0.2; MinimumGameVersion 1.1.0.0','northforge.solarpanel; optional northforge.core >= 0.1.0','Renewable power generation','Iron Teeth 1x1x1 solar panel; produces up to 100 hp; side and rear gear connections; no worker; Stackable=None','6 Logs + 8 Planks + 4 Gears + 2 Scrap Metal + 2 Extract; unlock 250 science; no recipe; power output up to 100 hp','Northforge.Core optional','Use its exact manifest ID and native power output. Report a missing required dependency explicitly.','https://steamcommunity.com/sharedfiles/filedetails/?id=3801036916','High','Keep package pinned; re-check only after mod update.'],
  ['D006','Expanded Storage','Installed package 1.0.1; MinimumGameVersion 1.1.0.0','MauricioBedoya.ExpandedStorage; Iron Teeth variants','Bulk buffering for factory inputs and outputs','Grand Warehouse 12,000 boxes (3x3x4); Grand Tank 12,000 liquids (3x3x4); Grand Underground Pile 12,000 pileables (3x3x2); Storage/Tank Modules 1,750 (3x3x3); Pile Module 520 (3x3x3); modules use BlockObject stacking','Grand Warehouse: 220 Logs + 300 Planks + 60 Gears, 2500 science; Grand Tank: 300 Planks + 220 Gears + 110 Metal Blocks, 3000 science; Grand Underground Pile: 100 Logs + 200 Planks + 100 Gears, 3500 science; Storage Module: 55 Logs + 75 Planks + 15 Gears, 750 science; Tank Module: 75 Planks + 55 Gears + 30 Metal Blocks, 1050 science; Pile Module: 50 Logs + 35 Planks, 650 science; no recipes','None','Use the exact storage capacities and good-type filters when present; modules may stack through the blueprint block rule.','https://steamcommunity.com/sharedfiles/filedetails/?id=3795292508','High','Keep package pinned; re-check only after mod update.'],
  ['D007','Conveyor Belts v2','Installed 1.1 package; Version 11.4.0','Workshop 3815376360; version-1.1 manifest; minimum game version 1.1.1','Solid-item logistics and factory automation','Four belt speed tiers; later tiers reach up to 100 items/hour; Riser Up doubles power and Riser Down halves it; Merger, Splitter, Smart Splitter, Lift In/Out; speed-4 Impermeable Belt blocks water; belts share tiles with buildings, Pipes, and Platforms; under-powered networks stop','Exact per-piece costs and science unlocks still require blueprint extraction; old saves require belt networks to be rebuilt; no production recipes assumed','Moddable Timberborn; Moddable Tool Groups; eMka.ModSettings; ModdedFactionsBuildingSupport optional','Require the declared belt dependency. Buildings explicitly designed for both hauling and belts share the same inventory.','https://steamcommunity.com/sharedfiles/filedetails/?id=3815376360','High mechanics / Medium exact costs','Extract per-tier cost and power values.'],
  ['D008','Powered Tubeway','Installed 1.1 package; Version 11.0.0','Workshop 3543155128; version-1.1 manifest; minimum game version 1.1.1','Powered package transport','Patches normal and vertical Tubeways so they transmit power; later notes mention Tubeway Bridges and faction variants','No separate production recipe or additional cost is verified; this is a behavior patch to existing Tubeway pieces.','None declared in the 1.1 manifest','Treat Tubeway power transmission as an optional network capability; do not require it for core recipes.','https://steamcommunity.com/sharedfiles/filedetails/?id=3543155128','High mechanics / Medium exact behavior','Verify supported Tubeway variants in game.'],
  ['D009','Power Lines','Installed 1.1 package; Version 11.1.1','Workshop 3766893705; version-1.1 manifest; minimum game version 1.1.1','Long-distance power distribution','Native MechanicalNode graph through PowerLineSpec.ConnectionLocations and public connection service; mixer cable main82/reload83 passed','Mixer attachment grid (7.84,5.84,1.80); test circuit 350 hp supply / 312 hp actual demand; pylon/beam catalog extraction pending','TimberUi; Harmony; ModSettings.Common authoring reference','Exact endpoint persistence, cut/reconnect, self/duplicate rejection and conserved production verified; dependency DLLs remain external.','https://steamcommunity.com/sharedfiles/filedetails/?id=3766893705','High tested mixer contract / Medium exact catalog','Other structures and Gravity Battery edge cases remain to test.'],
  ['D010','Moddable Timberborn','Required shared framework for several target mods','Current 1.1 framework package','Shared modding API and data hooks','Provides the pipeline used by Timber Pipes and Conveyor Belts v2 to add content safely','No player-facing recipes; framework dependency only.','None beyond the game and current framework version','Check the loaded mod ID and version before enabling adapters.','https://mod.io/g/timberborn','High','Pin the installed framework version in the mod manifest.'],
  ['D011','Moddable Tool Groups','Required shared UI/content framework','Current 1.1 framework package','Adds/extends building and item groups','Used by Timber Pipes and Conveyor Belts v2 for their toolbar groups','No player-facing recipes; framework dependency only.','None beyond the game and current framework version','Do not create duplicate toolbar groups when this framework is present.','https://mod.io/g/timberborn','High','Pin the installed framework version in the mod manifest.'],
  ['D012','Mod Settings','Required shared settings framework','Current 1.1 framework package','Exposes mod configuration','Used by Timber Pipes and Conveyor Belts v2 for animation, arrows, flow, and related settings','No player-facing recipes; framework dependency only.','None beyond the game and current framework version','Use the required framework API; missing dependencies must fail visibly. ModSettings.Common is also required to compile the Power Lines reference.','https://mod.io/g/timberborn','High','Pin the installed framework version in the mod manifest.'],
  ['D013','Harmony','Required >= 2.4.1','src/DeepFrontier/manifest.json','Targeted native inventory initialization','Restaurant input-only kitchen/menu inventory and exact Moddable Recipes ownership exception','No player-facing recipes; runtime dependency only.','Harmony','Required by the current restaurant implementation. No post-mutation repair or substitute inventory.','src/DeepFrontier/Scripts/RestaurantKitchenInventory.cs','Source and official build 40 runtime','Verify recipe changes and reload preserve table-only dishes.'],
  ['D014','Map Transformer','Installed 1.1 authoring tool; Version 11.0.0','Workshop 3798650616; version-1.1 manifest; minimum game version 1.1.1','One-time copied-map height and terrain authoring','Resizes map height, adds bottom dirt, preserves water while transforming, and writes a transformed save. New Z layers are empty until terrain is authored.','No player-facing recipes; map authoring operations only.','Harmony; ModdableTimberborn','Use on a duplicated source map before play; keep backups, reload/save the transformed output, and publish the custom terrain-height requirement with the map.','https://steamcommunity.com/sharedfiles/filedetails/?id=3798650616','High','Create and validate the Deep Frontier source map.'],
  ['D015','Moddable Recipes','Required 11.0.0','Workshop 3639961044; exact installed 1.1 DLL','Recipe selection and persistent inventory compatibility','InitInventoryForRecipe rebuilds allowed goods on SetRecipe and Load; Restaurant retains ownership of its multi-food input inventory','Native fermenter recipes plus authored table-only cake','Moddable Timberborn; Harmony','Restaurant-only prefix at the mutation entry point; other manufactories retain dependency behavior','outputs/civic-native-api/ModdableRecipes.ManufactoryPatches.cs','SetRecipe and fresh-process reload verified','Builds 40/41: no public/worker output; saved service resumed without duplicate meals.'],
  ['D016','TimberUi','Required 11.0.1','src/DeepFrontier/manifest.json; exact installed DLL','Native-style entity panel fragments','RestaurantPanel displays seats, waiting diners, actual foods, optional coffee and conditional water stock','No recipes','See exact installed manifest capture','BindFragment and BaseEntityPanelFragment; keep dependency DLL in its own package','tools/modding_api_audit_1_1.json','Native dining panel inspected in game','Source: src/DeepFrontier/Scripts/RestaurantPanel.cs'],
];
dependencyRows.push(styleDependency);
const dependencyTable = writeTable(dependencies, 1, dependencyHeaders, dependencyRows, 'DependenciesTable', '#8064A2');
dependencies.getRange(`A1:L${dependencyTable.endRow}`).format.wrapText = true;
dependencies.getRange(`A1:L${dependencyTable.endRow}`).format.autofitRows();
dependencies.getRange('A:A').format.columnWidth = 12;
dependencies.getRange('B:B').format.columnWidth = 25;
dependencies.getRange('C:D').format.columnWidth = 22;
dependencies.getRange('E:E').format.columnWidth = 24;
dependencies.getRange('F:I').format.columnWidth = 42;
dependencies.getRange('J:J').format.columnWidth = 52;
dependencies.getRange('K:L').format.columnWidth = 22;
dependencies.getRange(`K2:K${dependencyTable.endRow}`).conditionalFormats.add('containsText', { text: 'Low', format: { fill: gold } });

title(calculator, 'Factory Line Calculator', 'Change the yellow cells to test a proposed building or production line. The model intentionally uses simple throughput and power checks.');
calculator.getRange('A4:B13').values = [
  ['Input','Value'],
  ['Machine count',1],
  ['Output per cycle',1],
  ['Cycle minutes',1],
  ['Power per machine (hp)',100],
  ['Workers per machine',2],
  ['Buffer target minutes',2],
  ['Belt capacity per minute',120],
  ['Power available (hp)',500],
  ['Workers available',10],
];
calculator.getRange('D4:E13').values = [
  ['Calculated result','Value'],
  ['Output per hour',null],
  ['Total power demand',null],
  ['Total workers',null],
  ['Target buffer units',null],
  ['Belt utilization',null],
  ['Power utilization',null],
  ['Worker utilization',null],
  ['Primary constraint',null],
  ['Readiness',null],
];
calculator.getRange('E5:E13').formulas = [
  ['=B5*B6*60/B7'],
  ['=B5*B8'],
  ['=B5*B9'],
  ['=E5*B10'],
  ['=E5/B11'],
  ['=E6/B12'],
  ['=E7/B13'],
  ['=IF(E9>1,"Belt capacity",IF(E10>1,"Power grid",IF(E11>1,"Workers","None")))'],
  ['=IF(E12="None","Ready","Needs capacity")'],
];
calculator.getRange('A4:B4').format = { fill: navy, font: { name: font, size: 10, bold: true, color: '#FFFFFF' } };
calculator.getRange('D4:E4').format = { fill: navy, font: { name: font, size: 10, bold: true, color: '#FFFFFF' } };
calculator.getRange('A4:E13').format.font = { name: font, size: 10 };
calculator.getRange('B5:B13').format = { fill: gold, font: { name: font, size: 10, bold: true } };
calculator.getRange('A4:B13').format.borders = { preset: 'outside', style: 'thin', color: '#D9D9D9' };
calculator.getRange('D4:E13').format.borders = { preset: 'outside', style: 'thin', color: '#D9D9D9' };
calculator.getRange('E9:E11').format.numberFormat = '0.0%';
calculator.getRange('A16:C20').values = [
  ['Balancing rule','Starting target','Use'],
  ['Science unlock','1,000,000 reactor','Advanced laboratories raise research throughput; materials and workforce still matter.'],
  ['Material gate','1–3 new materials','Require a short visible chain before a major building.'],
  ['Power gate','1–3 substations for landmarks','Power should create district planning.'],
  ['Footprint gate','Fit approved art','Use the isometric model and voxel clearance to determine dimensions; no imposed tile maximum.'],
];
calculator.getRange('A16:C16').format = { fill: navy, font: { name: font, size: 10, bold: true, color: '#FFFFFF' } };
calculator.getRange('A16:C20').format.font = { name: font, size: 10 };
calculator.getRange('A16:C20').format.wrapText = true;
calculator.getRange('A:A').format.columnWidth = 26;
calculator.getRange('B:B').format.columnWidth = 16;
calculator.getRange('C:C').format.columnWidth = 42;
calculator.getRange('D:D').format.columnWidth = 26;
calculator.getRange('E:E').format.columnWidth = 18;

title(sources, 'Sources and reference notes', 'Use these references to keep the workbook aligned with the current game and modding environment.');
const sourceHeaders = ['Source','URL','Use in workbook','Checked date','Notes','Package ID','Data status','Verified fields'];
const sourceRows = [
['Timberborn Official Wiki','https://timberborn.wiki.gg/','Current game categories, Update 1.1 context, food, crops, well-being, buildings, and power','2026-10-17','Power is rotary mechanical torque measured in hp. Under-supplied powered buildings operate more slowly.','','Reference','Game context'],
['Vanilla building data extract','https://timberborn.wiki.gg/wiki/Category%3AConstructions','VanillaBuildings and VanillaRecipes sheets','2026-10-17',`Fetched the official Category:Constructions tree and parsed ${vanillaData.buildings.length} recognized buildable/map infobox pages and ${vanillaData.recipes.length} recipe or power-output rows. Local install is Timberborn 1.1.2.8.`,'','Extracted','Dimensions; costs; science; hp; workers; recipes'],
['Vanilla item data extract','https://timberborn.wiki.gg/wiki/Category%3AGoods','VanillaItems sheet','2026-10-17',`Fetched the official Category:Goods tree and parsed ${vanillaData.items.length} Good, Plant, and Crop pages.`,'','Extracted','Goods; plants; crops; categories'],
['Official Timberborn modding tools','https://github.com/mechanistry/timberborn-modding','Unity project structure, templates, DLL and asset import workflow','2026-10-17','Local checkout pins Unity 6000.5.11f1.','','Reference','Project structure; templates'],
['ModdableTimberborn API overview','https://github.com/datvm/TimberbornMods/blob/master/ModdableTimberborn/Docs/README.MD','Runtime capabilities and integration boundary','2026-10-17','Documented subsystems include spec/template modifiers, building settings, entity tracking, game stats, areas, extra hauler targets, and mechanical-system changes; no supported terrain-expansion subsystem is listed.','','API reference','Runtime systems; mechanical API; areas'],
['ModdableTimberborn map stats','https://github.com/datvm/TimberbornMods/blob/master/ModdableTimberborn/Docs/GameStats.MD','Underground feasibility and map-dimension assumptions','2026-10-17','MapSizeTerrainZ and MapSizeTotalZ are exposed as readable map stats; use authored lower sectors for the first implementation.','','API reference','Map dimensions; terrain height; total height'],
['Timberborn map editor visible layers','https://timberborn.wiki.gg/wiki/Map_Editor/Top_right_controls','Player-facing underground visibility reference','2026-10-17','The map editor can hide upper terrain layers to reveal underground areas; this supports authored lower sectors but does not establish runtime terrain expansion.','','Game reference','Visible layers; underground view'],
['Map Transformer','https://steamcommunity.com/sharedfiles/filedetails/?id=3798650616','One-time copied-map authoring and height expansion','2026-10-18','Update 1.1 mod; can resize map height, add bottom dirt, preserve water, and write a transformed save. Use it before play, keep backups, and publish the custom-terrain-height dependency with the map.','3798650616','Authoring tool; 1.1 listing','Height transform; bottom dirt; map copy/resize'],
['Conveyor Belts v2','https://steamcommunity.com/sharedfiles/filedetails/?id=3815376360','Installed solid-item logistics dependency','2026-10-18','Local Version-1.1 manifest confirms Version 11.4.0, minimum game version 1.1.1, and the shared framework requirements. Exact per-piece blueprint costs and hp remain a balancing input to extract.','3815376360','Installed 1.1 manifest','Version; minimum game; declared requirements; mechanics'],
['Timber Pipes','https://steamcommunity.com/sharedfiles/filedetails/?id=3801726769','Installed liquid logistics dependency','2026-10-18','Local Version-1.1 manifest confirms Version 11.4.0, minimum game version 1.1.1, and the shared framework requirements. Use the current Steam package rather than the legacy Pipes listing.','3801726769','Installed 1.1 manifest','Version; minimum game; declared requirements; public costs'],
['Powered Tubeway','https://steamcommunity.com/sharedfiles/filedetails/?id=3543155128','Installed powered transport dependency','2026-10-18','Local Version-1.1 manifest confirms Version 11.0.0, minimum game version 1.1.1, and no declared package dependencies. Treat it as a behavior patch to Tubeway pieces.','3543155128','Installed 1.1 manifest','Version; minimum game; declared requirements; behavior'],
['Pump to Tank','https://steamcommunity.com/workshop/filedetails/?id=3681283725','Installed foundation tank-to-tank fluid transfer','2026-10-18','Local Version-1.1 manifest confirms Version 1.0.9, Version-1.1, minimum game version 1.1.2.4, and Harmony >= 2.4.1. Deep Frontier will detect and use its transfer behavior instead of recreating it; exact blueprint hp/capacity remain pending.','3681283725','Installed 1.1 manifest','Version; minimum game; Harmony; tank transfer'],
['Wormhole and Ring Teleporter Stations','https://steamcommunity.com/sharedfiles/filedetails/?id=3813842276','Optional beaver and high-value transport','2026-10-17','Public 1.1 description provides station costs and Extract-per-crossing behavior; confirm package availability.','3813842276','Public mechanics reference','Costs; science; Extract crossings'],
['Power Lines','https://steamcommunity.com/sharedfiles/filedetails/?id=3766893705','Installed long-distance power distribution','2026-10-18','Local Version-1.1 manifest confirms Version 11.1.1, minimum game version 1.1.1, and TimberUi plus Harmony requirements. Exact pylon/beam profiles remain package-specific.','3766893705','Installed 1.1 manifest','Version; minimum game; declared requirements; pylon/beam mechanics'],
['Flywheels','https://steamcommunity.com/sharedfiles/filedetails/?id=3322428023','Installed power storage and smoothing','2026-10-18','Local Version-1.1 manifest confirms Version 4.1.1.15, minimum game version 1.1.2.4, and no declared package dependencies. Exact capacity/cost must be extracted from the package.','3322428023','Installed 1.1 manifest','Version; minimum game; declared requirements; storage behavior'],
['Timber Pipes detail reference','https://catalogue.smods.ru/archives/496562','Pipe costs, unlocks, headlift, and placement notes','2026-10-17','Use alongside the current package; the catalogue page is a secondary reference.','','Secondary reference','Pipe pieces; costs; headlift'],
['Timber Pipes announcement','https://www.reddit.com/r/Timberborn/comments/1wgbrpl/new_mod_timber_pipes/','Current pipe pieces and 1.1 changes','2026-10-17','Community announcement used to cross-check One-way Valve, Riser, Pump, and Outfall Pipe values.','','Community reference','Pipe changes; 1.1 notes'],
['Northforge - Solar Panel','https://steamcommunity.com/sharedfiles/filedetails/?id=3801036916','Exact installed Iron Teeth package profile','2026-10-17','Solar Panel 1.0.2; optional Northforge.Core >= 0.1.0; no recipe.','3801036916','Installed package','1x1x1; 6 Logs; 8 Planks; 4 Gears; 2 Scrap Metal; 2 Extract; 250 science; 100 hp; Stackable=None'],
['Expanded Storage','https://steamcommunity.com/sharedfiles/filedetails/?id=3795292508','Exact installed Iron Teeth package profiles','2026-10-17','Expanded Storage 1.0.1; six storage buildings; no recipes; modules use BlockObject stacking.','3795292508','Installed package','Grand Warehouse/Tank/Pile 12000; Modules 1750/1750/520; dimensions; exact costs; science unlocks'],
['Deep Frontier vertical slice','src/DeepFrontier/Data','Exact mod-layer blueprints, recipes, progression, and custom asset outputs','2026-10-18','Validated finite and permanent Deep Ore branches. Deep Mine is 5x5x4, six workers, 4,000 hp demand, 12 Water -> 4 Deep Ore per 2 minutes, and requires a DeepOreVein understructure; no artificial layer cap.','DeepFrontier','Generated and validated','Blueprint dimensions; costs; science; workers; hp; recipes; understructure; Timbermesh; icons'],
];
sourceRows.push(['Concrete construction chain','tools/construction_materials.json; outputs/factory-transport-reload81.log; outputs/factory-power-lines-run82.log; outputs/factory-power-lines-reload83.log; outputs/mineral-pits-run86.log; outputs/mineral-pits-reload86.log','Exact authored mineral buildings, goods, recipes, sources and progression','2026-10-20','Five goods, seven buildings, four sources. Mixer belts/pipes81 and cable82/83 verified; reload83 withdrew eight old Concrete before two conserved batches to respect the 30-unit receiver. Pits86 passed native ground/roof rules and exact reload/depletion with No Build Restriction and All Buildings Transfer Power disabled. Test deposits explicitly shortened to 24; authored deposits remain 600. Seeded functional evidence, not economic throughput.','DeepFrontier',constructionStatus,'Dimensions; costs; workers; hp; science; recipe fuel; finite yield; permanent source constraints']);
sourceRows.push(
 ['Current civic and factory requirements','tools/frontier_progression.json','User decisions and proposed balance','2026-10-19','Restaurant actual meals; hospital 30 and 1.8x recovery; grocery assortment; aluminum; oil-derived resin/plastic; reusable PPE; advanced structures and multi-good warehouses.','DeepFrontier','Design except authored reactor science','Nuclear unlock 1,000,000; distinguish proposals from runtime behavior'],
 ['Item-use audit','outputs/item-use-audit.json','Implemented consumers against user item policy','2026-10-19',`${itemUseAudit.total} new goods; ${itemUseAudit.failures} unresolved. Food and final rocket parts may have one use. Storage and disposal do not count.`,'DeepFrontier','Static authored graph; not runtime proof','Distinct consumer destinations; active recipe assignments; evidence paths'],
 ['Steam dependency freshness','tools/dependency_freshness_1_1.json','Installed packages versus official Valve published details','2026-10-19',`${dependencyFreshness.packages.length} packages checked; all current: ${dependencyFreshness.allCurrent}. Checked ${dependencyFreshness.checkedAt}.`,'1062090','Installed timestamps and byte sizes match','Version; update timestamp; package bytes; manifest hash']
);
sourceRows.push(['Restaurant kitchen and service',restaurantSource,'Exact blueprint, native fermenter recipes and authored cake recipe','2026-10-19','400 hp; four workers; fourteen seats; 2 berries + 2 corn + 1 water produce 4 table-only cakes in 2 base working hours. Optional coffee; one water for thirsty diners.','DeepFrontier',restaurantStatus,'Dimensions; cost; science; power; recipes; inventory permissions; seating']);
sourceRows.push(aquacultureSource);
sourceRows.push(hospitalSource);
sourceRows.push(grocerySource);
sourceRows.push(structuralSource,hydroSource);
sourceRows.push(researchSource,styleSource);
const sourceTable = writeTable(sources, 4, sourceHeaders, sourceRows, 'SourcesTable', '#8064A2');
sources.getRange(`A4:H${sourceTable.endRow}`).format.wrapText = true;
sources.getRange(`A4:H${sourceTable.endRow}`).format.autofitRows();
sources.getRange('A:A').format.columnWidth = 26;
sources.getRange('B:B').format.columnWidth = 52;
sources.getRange('C:C').format.columnWidth = 38;
sources.getRange('D:D').format.columnWidth = 14;
sources.getRange('E:E').format.columnWidth = 36;
sources.getRange('F:F').format.columnWidth = 16;
sources.getRange('G:G').format.columnWidth = 24;
sources.getRange('H:H').format.columnWidth = 52;

title(vanilla, 'Vanilla 1.1 balance anchors', 'Reference values from the current game. Use these to keep draft mod numbers in a believable range.');
const vanillaHeaders = ['Anchor ID','Vanilla building','Category','Dimensions','Height','Power role / hp','Workers','Science unlock','Known construction materials','Why it matters','Source'];
const vanillaRows = [
['V001','Power Wheel','Power','3x1',2,'50 output',1,0,'20 Logs','Early baseline generator','https://timberborn.wiki.gg/wiki/Power_Wheel'],
['V002','Large Power Wheel','Power','3x3',1,'300 output',4,0,'50 Logs','Industrial worker-powered baseline','https://timberborn.wiki.gg/wiki/Large_Power_Wheel'],
['V003','Steam Engine','Power','3x3',3,'400 output',0,400,'20 Logs; 25 Gears; 40 Metal Parts','Midgame fuel-powered baseline; consumes 0.1 Logs + 0.3 Water per 1h','https://timberborn.wiki.gg/wiki/Steam_Engine'],
['V004','Food Factory','Food','3x3',3,'120 demand',1,300,'40 Planks; 15 Gears; 10 Metal Blocks','Existing high-throughput food reference','https://timberborn.wiki.gg/wiki/Food_Factory'],
['V005','Gear Workshop','Industrial','3x2',3,'120 demand',1,100,'15 Logs; 25 Planks','Powered production reference; 1 Plank -> 1 Gear per 3h','https://timberborn.wiki.gg/wiki/Gear_Workshop'],
['V006','Smelter','Metal','2x4','2 (3 at pipe)','200 demand',1,300,'50 Planks; 20 Gears; 30 Scrap Metal','Heavy processing reference; 2 Scrap Metal + 0.2 Logs -> 1 Metal Block per 2h','https://timberborn.wiki.gg/wiki/Smelter'],
['V007','Bot Assembler','Science','3x3',1,'250 demand',2,750,'100 Planks; 50 Gears; 50 Metal Blocks','Automation reference; bot unlock 10000','https://timberborn.wiki.gg/wiki/Bot_Assembler'],
['V008','Numbercruncher','Science','4x4 minus corners',3,'500 demand',0,1500,'30 Planks; 100 Gears; 50 Metal Parts','Late science/power reference; produces 10 Science Points per 1h','https://timberborn.wiki.gg/wiki/Numbercruncher'],
['V009','Power Meter','Automation','1x1',2,'0 demand',0,600,'10 Gears; 6 Metal Blocks','Existing automation gate and load-shedding tool','https://timberborn.wiki.gg/wiki/Power_Meter'],
];
writeTable(vanilla, 4, vanillaHeaders, vanillaRows, 'VanillaAnchorsTable', '#A9D18E');
vanilla.getRange('A4:K13').format.wrapText = true;
vanilla.getRange('A4:K13').format.autofitRows();
vanilla.getRange('A:A').format.columnWidth = 12;
vanilla.getRange('B:B').format.columnWidth = 24;
vanilla.getRange('C:C').format.columnWidth = 14;
vanilla.getRange('D:E').format.columnWidth = 12;
vanilla.getRange('F:H').format.columnWidth = 18;
vanilla.getRange('I:J').format.columnWidth = 34;
vanilla.getRange('K:K').format.columnWidth = 52;

const vanillaBuildingHeaders = [
  'Vanilla ID','Building','Infobox','Categories','Faction','Buildable?','Availability','Width','Length','Footprint','Footprint tiles','Height',
  'Workers','Power demand (hp)','Power output (hp)','Power role','Science unlock','Bot unlock','Build materials','Flags','Recipe names','Source','Data status'
];
const vanillaBuildingRows = vanillaData.buildings.map((b, i) => [
  `VB${String(i + 1).padStart(3, '0')}`, b.name, b.infobox, b.categories, b.faction, b.buildable ? 'Yes' : 'No', b.availability,
  b.width, b.length, b.footprint, b.footprintTiles, b.height, b.workers, b.powerHp, b.powerOutputHp, powerRole(b.powerHp, b.powerOutputHp), b.scienceUnlock, b.botUnlock,
  b.materials, b.flags, b.recipes.map((r) => r.name).join('; '), b.source, b.status,
]);
const vanillaBuildingTable = writeTable(vanillaBuildings, 1, vanillaBuildingHeaders, vanillaBuildingRows, 'VanillaBuildingsTable', '#70AD47');
vanillaBuildings.getRange(`A1:W${vanillaBuildingTable.endRow}`).format.wrapText = true;
vanillaBuildings.getRange(`A1:W${vanillaBuildingTable.endRow}`).format.autofitRows();
vanillaBuildings.getRange('A:A').format.columnWidth = 12;
vanillaBuildings.getRange('B:B').format.columnWidth = 25;
vanillaBuildings.getRange('C:C').format.columnWidth = 14;
vanillaBuildings.getRange('D:D').format.columnWidth = 42;
vanillaBuildings.getRange('E:G').format.columnWidth = 18;
vanillaBuildings.getRange('H:O').format.columnWidth = 14;
vanillaBuildings.getRange('P:R').format.columnWidth = 14;
vanillaBuildings.getRange('S:U').format.columnWidth = 30;
vanillaBuildings.getRange('V:W').format.columnWidth = 52;
vanillaBuildings.getRange(`F2:F${vanillaBuildingTable.endRow}`).conditionalFormats.add('containsText', { text: 'No', format: { fill: gray } });
vanillaBuildings.getRange(`W2:W${vanillaBuildingTable.endRow}`).conditionalFormats.add('containsText', { text: 'missing', format: { fill: gold } });

const vanillaItemHeaders = [
  'Vanilla ID','Item','Infobox','Categories','Faction','Type','Source / recipe','Storage','Weight','Satisfies / effects','Produces','Consumed by','Source','Data status'
];
const vanillaItemRows = vanillaData.items.map((item, i) => [
  `VI${String(i + 1).padStart(3, '0')}`, item.name, item.infobox, item.categories, item.faction, item.type, item.source, item.storage,
  item.weight, item.satisfies, item.produces, item.consumedBy, item.sourceUrl, item.status,
]);
const vanillaItemTable = writeTable(vanillaItems, 1, vanillaItemHeaders, vanillaItemRows, 'VanillaItemsTable', '#70AD47');
vanillaItems.getRange(`A1:N${vanillaItemTable.endRow}`).format.wrapText = true;
vanillaItems.getRange(`A1:N${vanillaItemTable.endRow}`).format.autofitRows();
vanillaItems.getRange('A:A').format.columnWidth = 12;
vanillaItems.getRange('B:B').format.columnWidth = 24;
vanillaItems.getRange('C:C').format.columnWidth = 12;
vanillaItems.getRange('D:D').format.columnWidth = 30;
vanillaItems.getRange('E:H').format.columnWidth = 24;
vanillaItems.getRange('I:I').format.columnWidth = 10;
vanillaItems.getRange('J:L').format.columnWidth = 30;
vanillaItems.getRange('M:M').format.columnWidth = 52;
vanillaItems.getRange('N:N').format.columnWidth = 22;

const vanillaRecipeHeaders = [
  'Vanilla Recipe ID','Building','Faction','Recipe','Inputs','Outputs','Cycle hours','Power demand (hp)','Power output (hp)','Power role','Workers','Fuel','Storage / buffers','Source','Raw inputs','Raw outputs'
];
const vanillaRecipeRows = vanillaData.recipes.map((recipe, i) => [
  `VR${String(i + 1).padStart(3, '0')}`, recipe.building, recipe.faction, recipe.recipe, recipe.inputs, recipe.outputs, recipe.cycleHours,
  recipe.powerHp, recipe.powerOutputHp, powerRole(recipe.powerHp, recipe.powerOutputHp), recipe.workers, recipe.fuel, recipe.storage, recipe.source, recipe.rawConsumes, recipe.rawProduces,
]);
const vanillaRecipeTable = writeTable(vanillaRecipes, 1, vanillaRecipeHeaders, vanillaRecipeRows, 'VanillaRecipesTable', '#ED7D31');
vanillaRecipes.getRange(`A1:P${vanillaRecipeTable.endRow}`).format.wrapText = true;
vanillaRecipes.getRange(`A1:P${vanillaRecipeTable.endRow}`).format.autofitRows();
vanillaRecipes.getRange('A:A').format.columnWidth = 16;
vanillaRecipes.getRange('B:B').format.columnWidth = 25;
vanillaRecipes.getRange('C:C').format.columnWidth = 20;
vanillaRecipes.getRange('D:D').format.columnWidth = 24;
vanillaRecipes.getRange('E:F').format.columnWidth = 34;
vanillaRecipes.getRange('G:K').format.columnWidth = 15;
vanillaRecipes.getRange('L:M').format.columnWidth = 30;
vanillaRecipes.getRange('N:N').format.columnWidth = 52;
vanillaRecipes.getRange('O:P').format.columnWidth = 34;

// Fit only the newly added records after established column widths are set.
buildings.getRange(`A${alignedBuildingRows.length+2}:AL${alignedBuildingRows.length+constructionBuildingRows.length+constructionSourceRows.length+1}`).format.autofitRows();
items.getRange(`A${itemRows.length+2}:U${itemEnd}`).format.autofitRows();
recipes.getRange(`A${recipeRows.length+2}:X${recipeEnd}`).format.autofitRows();
progression.getRange(`A${progressionRows.length+2}:P${progressionEnd}`).format.autofitRows();
transport.getRange(`A${transportEnd}:Q${transportEnd}`).format.autofitRows();
sources.getRange(`A${sourceTable.endRow}:H${sourceTable.endRow}`).format.autofitRows();
const constructionStartRow=alignedBuildingRows.length+2;
const crusherRow=constructionStartRow+construction.buildings.findIndex(b=>b.id==='StoneCrusher');
const mixerRow=constructionStartRow+construction.buildings.findIndex(b=>b.id==='ConcreteMixer');
overview.getRange('E31').formulas=[[`=SUM(Buildings!N${crusherRow}:N${mixerRow})`]];
overview.getRange('E32').formulas=[[`=SUM(Buildings!N${constructionStartRow}:N${mixerRow})`]];
// Verify a real driver change, then restore before the final recalculation/export.
const mixerDemand=buildings.getRange(`N${mixerRow}`);
const originalMixerDemand=mixerDemand.values[0][0];
const originalSurfaceDemand=construction.buildings.filter(b=>['crusher','kiln','mixer'].includes(b.kind)).reduce((sum,b)=>sum+b.hp,0);
const originalTotalDemand=construction.buildings.reduce((sum,b)=>sum+b.hp,0);
mixerDemand.values=[[originalMixerDemand+100]];
if(overview.getRange('E31').values[0][0]!==originalSurfaceDemand+100 || overview.getRange('E32').values[0][0]!==originalTotalDemand+100) throw new Error('Concrete-line hp formulas failed driver-change check');
mixerDemand.values=[[originalMixerDemand]];
// Fit affected rows after final column widths; preserve unrelated source views.
buildings.getRange(`A${buildingEnd-plannedFacilities.length+1}:AL${buildingEnd}`).format.autofitRows();
buildings.getRange(`M${buildingEnd-plannedFacilities.length+1}:O${buildingEnd}`).format.numberFormat='#,##0';
buildings.getRange('Q32').format.numberFormat='#,##0';
buildings.getRange(`Q${buildingEnd-7}:Q${buildingEnd}`).format.numberFormat='#,##0';
items.getRange('A54:U60').format.autofitRows();
buildings.getRange('A13:AL13').format.autofitRows();
const groceryRow=allBuildingRows.findIndex(r=>r[0]==='B009')+2;
buildings.getRange(`A${groceryRow}:AL${groceryRow}`).format.verticalAlignment='top';
buildings.getRange(`A${groceryRow}:AL${groceryRow}`).format.autofitRows();
recipes.getRange('A16:X17').format.autofitRows();
recipes.getRange('G16:G17').format.numberFormat='0.0000';
progression.getRange('E16').format.numberFormat='#,##0';
calculator.getRange('A16:C20').format.autofitRows();
sources.getRange(`A${sourceTable.endRow-2}:H${sourceTable.endRow}`).format.autofitRows();
transport.getRange(`A${transportEnd-2}:Q${transportEnd}`).format.autofitRows();
powerCurve.getRange('D5:D9').format.numberFormat='#,##0';
powerCurve.getRange('H5:H9').format.numberFormat='#,##0';
wb.recalculate();

const checks = [
 ['Overview','A35:F41',7,6], ['Buildings',`A${buildingEnd-7}:Q${buildingEnd}`,8,17],
 ['Buildings','M32:Q32',1,5], ['Items','A54:U59',6,21],
 ['Recipes','B16:K17',2,10], ['Progression','A16:H20',5,8],
 ['PowerCurve','A4:K9',6,11], ['ItemUses','A4:F10',7,6],
 ['Calculator','A16:C20',5,3], ['Sources',`A${sourceTable.endRow-2}:H${sourceTable.endRow}`,3,8],
];
for(const [sheetName,range,tableMaxRows,tableMaxCols] of checks) {
 const inspection=await wb.inspect({kind:'table',range:`${sheetName}!${range}`,include:'values,formulas',tableMaxRows,tableMaxCols,maxChars:4500});
 console.log(inspection.ndjson);
}
const errors = await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'final formula error scan'});
console.log(errors.ndjson);
const changedPreviews = [
 ['Buildings','H62:U62'],
 ['Dependencies','A18:E18'],
 ['Recipes',`A${recipeEnd}:K${recipeEnd}`],
 ['Overview','A47:F49'],
 ['Buildings',`H${buildingEnd-7}:U${buildingEnd}`],
 ['Buildings',`V${buildingEnd}:AL${buildingEnd}`],
 ['Sources',`A${sourceTable.endRow-1}:H${sourceTable.endRow}`],
 ['Transport',`C${alignedTransportRows.findIndex(r=>r[0]==='DamDischarge')+2}:Q${alignedTransportRows.findIndex(r=>r[0]==='DamDischarge')+2}`],
 ['Progression',`C${alignedProgressionRows.findIndex(r=>r[0]==='HydroInfrastructure')+2}:P${alignedProgressionRows.findIndex(r=>r[0]==='HydroInfrastructure')+2}`],
 ['Buildings','M32:U35'],
 ['Buildings','M13:U13'],
];
for (const [index,[name,range]] of changedPreviews.entries()) {
 const preview=await wb.render({sheetName:name,range,scale:1,format:'png'});
 await fs.writeFile(`${outputDir}/hydro_workbook_${index}_${name}.png`,new Uint8Array(await preview.arrayBuffer()));
}

const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(`${outputDir}/Timberborn_Deep_Frontier_Balance_Workbook.xlsx`);
console.log(`Saved ${outputDir}/Timberborn_Deep_Frontier_Balance_Workbook.xlsx`);
