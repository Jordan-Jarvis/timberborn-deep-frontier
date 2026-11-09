// Steel decks on legs (docs/platforms-design.md slice 2; tools/structural_building_content.mjs
// legDeckBlueprints; src/DeepFrontier/Scripts/SteelStructures).
//
//   node tools/validate_steel_leg_decks.mjs [dataRoot]
//
// Checks, against the generated Data root:
// - every catalog tool (structural_content.json legDecks.tools) has exactly one blueprint, and
//   no other Deep Frontier blueprint carries SteelDeckToolSpec;
// - the tool contract the C# planner relies on (SteelLegPlanner.Build repeats it at game load):
//   size [n, n, DeckZ+1]; the deck layer equals the deck's blocks with only its foundations
//   relaxed to Any; one foot block (GroundOrStackable, no occupation) at the centre of z = 0;
//   every other cell empty; BaseZ 0; Single layout; flippable;
// - the deck is an ordinary one-layer building whose foundations are its corners, and the
//   columns are the 1..N layer steel columns (GroundOrStackable foot, stackable cap);
// - the tool shows the deck's cost and science, and its models are the deck's (raised DeckZ
//   layers) and one node per column with that column's own model;
// - name, description, icon, sound, tool group and the placement messages exist;
// - the C# wiring: the planner, validator, placer and leg drawing are bound, the placer claims
//   SteelDeckToolSpec through the native IBlockObjectPlacer multibinding, and the one Harmony
//   patch (BuildingPlacer.CanHandle postfix) is applied from a mod starter with its checks.
import {readFile, readdir, access} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {legDeckBlocks, legDeckContract, STEEL_LEG_ROWS} from './structural_building_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = process.argv[2] ? resolve(process.argv[2]) : join(root, 'src/DeepFrontier/Data');
const failures = [];
const fail = (m) => failures.push(m);
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const exists = (path) => access(path).then(() => true, () => false);
const catalog = await readJson(join(root, 'tools/structural_content.json'));
const tools = catalog.legDecks?.tools;
if (!Array.isArray(tools) || !tools.length) throw new Error('structural_content.json has no legDecks.tools');
const blueprint = (id) => readJson(join(dataRoot, `Buildings/Platforms/${id}/${id}.IronTeeth.blueprint.json`));
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const solid = (b) => ['Ground', 'GroundOrStackable', 'Stackable'].includes(b.MatterBelow);

// No stray tool specs.
async function* blueprints(dir) {
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* blueprints(path);
    else if (entry.name.endsWith('.blueprint.json')) yield path;
  }
}
const withSpec = [];
for await (const path of blueprints(join(dataRoot, 'Buildings'))) {
  const value = await readJson(path);
  if (value.SteelDeckToolSpec) withSpec.push(value.TemplateSpec.TemplateName);
}
const expectedNames = tools.map((t) => `${t.id}.IronTeeth`).sort();
if (!same(withSpec.sort(), expectedNames)) fail(`SteelDeckToolSpec templates ${withSpec.join(', ')} differ from the catalog tools ${expectedNames.join(', ')}`);

const csv = await readFile(join(dataRoot, 'Localizations/enUS.csv'), 'utf8');
const locKeys = new Set(csv.split('\n').map((line) => line.split(',')[0]));
const groups = await readJson(join(root, 'tools/tool_groups.json'));
const sounds = (await readJson(join(root, 'tools/building_sounds.json'))).buildings;
for (const [key] of STEEL_LEG_ROWS) if (!locKeys.has(key)) fail(`missing placement message ${key}`);

for (const tool of tools) {
  let contract;
  try { contract = legDeckContract(tool); } catch (error) { fail(error.message); continue; }
  const {n, deck, columns, clearance, maxDepth} = contract;
  const v = await blueprint(tool.id);
  const d = await blueprint(deck.id);
  const spec = v.SteelDeckToolSpec;
  if (!same(spec, {DeckTemplate: `${deck.id}.IronTeeth`, DeckZ: clearance, Columns: columns.map((c) => `${c.id}.IronTeeth`),
    ColumnNodes: columns.map((c) => `#${c.id}`), MaxDepth: maxDepth})) fail(`${tool.id}: SteelDeckToolSpec differs from the catalog`);
  const b = v.BlockObjectSpec, db = d.BlockObjectSpec;
  if (!same(b.Size, {X: n, Y: n, Z: clearance + 1}) || b.BaseZ !== 0 || b.Flippable !== true || b.Overridable !== false || b.Entrance.HasEntrance)
    fail(`${tool.id}: tool size/base/flip contract broken`);
  if (!same(b.Blocks, legDeckBlocks(tool))) fail(`${tool.id}: tool blocks differ from legDeckBlocks`);
  if (!same(db.Size, {X: n, Y: n, Z: 1}) || db.BaseZ !== 0) fail(`${deck.id}: the deck must be one layer at BaseZ 0`);
  // Deck layer = deck blocks with foundations relaxed; the foot; nothing else.
  const layer = n * n;
  db.Blocks.forEach((block, i) => {
    const t = b.Blocks[clearance * layer + i];
    if (!same(t, solid(block) ? {...block, MatterBelow: 'Any'} : block)) fail(`${tool.id}: deck layer block ${i} is not the deck's (foundations relaxed)`);
  });
  const corners = db.Blocks.map((block, i) => solid(block) ? [i % n, Math.floor(i / n)] : null).filter(Boolean);
  if (!same(corners, [[0, 0], [n - 1, 0], [0, n - 1], [n - 1, n - 1]])) fail(`${deck.id}: foundations ${JSON.stringify(corners)} are not its four corners`);
  const below = b.Blocks.slice(0, clearance * layer);
  const centre = (n - 1) / 2 * n + (n - 1) / 2;
  below.forEach((block, i) => {
    const foot = i === centre;
    if (!same(block, {MatterBelow: foot ? 'GroundOrStackable' : 'Any', Occupations: 'None', Stackable: 'None', OccupyAllBelow: false, Underground: false}))
      fail(`${tool.id}: block ${i} under the deck must be ${foot ? 'the foot' : 'empty'}`);
  });
  if (v.PlaceableBlockObjectSpec.Layout !== 'Single' || v.PlaceableBlockObjectSpec.CustomPivot.HasCustomPivot)
    fail(`${tool.id}: the tool must use the Single layout with the native centred pivot (the foot sits under the cursor)`);
  if (!same(v.BuildingSpec.BuildingCost, d.BuildingSpec.BuildingCost) || v.BuildingSpec.ScienceCost !== d.BuildingSpec.ScienceCost)
    fail(`${tool.id}: cost/science must be the deck's`);
  // Columns.
  for (const [k, c] of columns.entries()) {
    const cv = await blueprint(c.id);
    const cb = cv.BlockObjectSpec;
    if (!same(cb.Size, {X: 1, Y: 1, Z: k + 1}) || cb.BaseZ !== 0) fail(`${c.id}: must be 1x1x${k + 1}`);
    cb.Blocks.forEach((block, z) => {
      if (block.MatterBelow !== (z === 0 ? 'GroundOrStackable' : 'Any') || (z === k) !== (block.Stackable === 'BlockObject'))
        fail(`${c.id}: block ${z} breaks the stackable column contract`);
    });
    const node = v.Children['#Finished']?.Children?.[`#${c.id}`];
    if (!node || !same(node.TimbermeshSpec, cv.Children['#Finished'].TimbermeshSpec) || node.TransformSpec)
      fail(`${tool.id}: model node #${c.id} must carry ${c.id}'s finished model untransformed`);
  }
  if (maxDepth > 2 * columns.length) fail(`legDecks.maxDepth ${maxDepth} needs more than two stacked columns`);
  // Models: the deck raised by the clearance.
  const up = {Position: {X: 0, Y: clearance, Z: 0}, Rotation: {X: 0, Y: 0, Z: 0}, Scale: {X: 1, Y: 1, Z: 1}};
  const deckNode = v.Children['#Finished']?.Children?.['#Deck'];
  if (!deckNode || !same(deckNode.TimbermeshSpec, d.Children['#Finished'].TimbermeshSpec) || !same(deckNode.TransformSpec, up) ||
      !same(deckNode.CollidersSpec, d.Children['#Finished'].CollidersSpec))
    fail(`${tool.id}: #Deck must be ${deck.id}'s finished model raised ${clearance} layers`);
  if (v.Children['#Finished'].TimbermeshSpec) fail(`${tool.id}: #Finished must own no model (connection and roof steps skip the tool)`);
  const stage = v.Children['#Unfinished']?.Children?.ConstructionStage0;
  if (!stage || !same(stage.TimbermeshSpec, d.Children['#Unfinished'].Children.ConstructionStage0.TimbermeshSpec) || !same(stage.TransformSpec, up))
    fail(`${tool.id}: the unfinished model must be ${deck.id}'s, raised`);
  const nodes = Object.keys(v.Children['#Finished'].Children ?? {}).sort();
  if (!same(nodes, ['#Deck', ...columns.map((c) => `#${c.id}`)].sort())) fail(`${tool.id}: unexpected model nodes ${nodes.join(', ')}`);
  // UI.
  for (const key of ['DisplayName', 'Description', 'FlavorDescription'])
    if (!locKeys.has(`Building.${tool.id}.${key}`)) fail(`${tool.id}: missing ${key}`);
  if (v.LabeledEntitySpec.Icon !== `Buildings/Platforms/${tool.id}/Icon` || !(await exists(join(dataRoot, `Buildings/Platforms/${tool.id}/Icon.png`))))
    fail(`${tool.id}: icon missing`);
  if (!groups.groups.DeepFrontierSteelStructures.templates.includes(tool.id)) fail(`${tool.id}: not in the Steel structures tool group`);
  if (!sounds[tool.id]) fail(`${tool.id}: no building_sounds.json entry`);
  if (v.MechanicalNodeSpec || v.WorkplaceSpec || v.WaterObstacleSpec) fail(`${tool.id}: a placement tool must stay passive`);
}

// C# wiring.
const dir = join(root, 'src/DeepFrontier/Scripts/SteelStructures');
const cs = await readFile(join(dir, 'SteelLegDecks.cs'), 'utf8');
const claim = await readFile(join(dir, 'SteelDeckPlacerClaim.cs'), 'utf8');
const need = (text, what, file) => { if (!text.includes(what)) fail(`${file}: missing ${what}`); };
for (const what of ['Bind<SteelLegPlanner>().AsSingleton()', 'MultiBind<IBlockObjectValidator>().ToExisting<SteelDeckLegValidator>()',
  'MultiBind<IBlockObjectPlacer>().To<SteelDeckPlacer>().AsSingleton()', 'b.AddDecorator<SteelDeckToolSpec,SteelDeckLegs>()',
  'b.AddDecorator<SteelDeckLegs,EntityMaterials>()', 'public bool CanHandle(BlockObjectSpec template)=>template.HasSpec<SteelDeckToolSpec>();',
  'if(!blockObject.IsPreview||!blockObject.HasComponent<SteelDeckToolSpec>())return true;', '[Context("Game")]',
  'internal record SteelDeckToolSpec : ComponentSpec'])
  need(cs, what, 'SteelLegDecks.cs');
for (const field of ['DeckTemplate', 'DeckZ', 'Columns', 'ColumnNodes', 'MaxDepth'])
  if (!new RegExp(`\\[Serialize\\] public [\\w<>]+ ${field} \\{ get; init; \\}`).test(cs)) fail(`SteelLegDecks.cs: SteelDeckToolSpec.${field} is not serialized`);
for (const [, key] of cs.matchAll(/public const string \w+="([^"]+)";/g)) if (!locKeys.has(key)) fail(`SteelLegLoc key ${key} has no enUS row`);
for (const what of ['internal sealed class SteelStructuresModStarter : IModStarter', 'SteelDeckPlacerClaim.Apply();',
  'AccessTools.Method(typeof(BuildingPlacer),nameof(BuildingPlacer.CanHandle),new[] {typeof(BlockObjectSpec)})',
  'postfix:new HarmonyMethod(typeof(SteelDeckPlacerClaim),nameof(CanHandlePostfix))',
  'if(__result&&__0.HasSpec<SteelDeckToolSpec>())__result=false;', 'nameof(BlockObjectPlacerService.GetMatchingPlacer)', '#if !UNITY_EDITOR'])
  need(claim, what, 'SteelDeckPlacerClaim.cs');
const patches = [...(cs + claim).matchAll(/NativePatches\.Install\(/g)].length + [...(cs + claim).matchAll(/new Harmony\(/g)].length;
if (patches !== 1) fail(`steel structures install ${patches} Harmony patches; the design allows exactly one (BuildingPlacer.CanHandle, through NativePatches)`);

if (failures.length) {
  console.log(failures.map((f) => 'FAIL ' + f).join('\n'));
  console.error(`Steel leg deck validation failed (${failures.length})`);
  process.exit(1);
}
console.log(`Steel leg decks: ${tools.length} placement tools (${[...new Set(tools.map((t) => t.deck))].join(', ')}, clearances `
  + `${[...new Set(tools.map((t) => t.clearance))].join('/')}), legs to ${catalog.legDecks.maxDepth} layers from `
  + `${catalog.legDecks.columns.length} column heights; placer, validator and the one BuildingPlacer.CanHandle postfix wired.`);
