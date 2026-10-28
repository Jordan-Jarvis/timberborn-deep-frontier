// Static validator for Deep Frontier cryogenic storage (data + C# + the
// native/Timber Pipes contracts the behaviour relies on).
//
//   node tools/validate_cryogenic_content.mjs [--root <repo>] [--data <dataRoot>] [--report <json>]
//     [--status awaiting-template|ready] [--automation <automation_content.json>]
//
// --data defaults to src/DeepFrontier/Data; point it at a scratch copy that
// tools/cryogenic_content.mjs was applied to. --status and --automation check
// a scratch copy against another TANK_FARM.status / automation declaration
// (defaults: the module's status and tools/automation_content.json). Static
// evidence only: intake gating, venting, statuses and pipe behaviour are
// verified in game.
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {access, readdir, readFile, writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {CRYOGENIC_LOCALIZATION, IGNORED_ON_TANKS, LOCALIZATION_FILE, MODULE_SPECS, SPEC_KEYS, TANK_FARM, checkBlueprintSockets,
  checkGoods, checkRegistrationSockets, cryogenicLocalization, cryogenicTankSpec, findTemplate, readStudySockets, socketPorts,
  validateTankFarmConfig} from './cryogenic_content.mjs';

const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : null; };
const root = opt('--root') ? resolve(opt('--root')) : resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = opt('--data') ? resolve(opt('--data')) : resolve(root, 'src', 'DeepFrontier', 'Data');
const reportPath = opt('--report');
const config = {...TANK_FARM, status: opt('--status') ?? TANK_FARM.status};
const automationPath = opt('--automation') ? resolve(opt('--automation')) : resolve(root, 'tools', 'automation_content.json');
const GAME_MANAGED = 'C:/Program Files (x86)/Steam/steamapps/common/Timberborn/Timberborn_Data/Managed';
const GAME_DATA = 'C:/Program Files (x86)/Steam/steamapps/common/Timberborn/Timberborn_Data';
const PIPES_PACKAGE = 'C:/Program Files (x86)/Steam/steamapps/workshop/content/1062090/3801726769/version-1.1';
const ilspy = resolve(root, 'tools', 'dotnet', 'ilspycmd.exe');
const errors = [];
const check = (ok, message) => { if (!ok) errors.push(message); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^\uFEFF/, ''));
const exists = (path) => access(path).then(() => true, () => false);
const guard = async (what, fn) => { try { return await fn(); } catch (error) { errors.push(`${what}: ${error.message}`); return null; } };

// --- module configuration and study sockets --------------------------------
await guard('TANK_FARM', () => validateTankFarmConfig(config));
const sockets = await guard('study sockets', () => readStudySockets(root, config));
if (sockets) await guard('registration sockets', () => checkRegistrationSockets(root, sockets, config));
const rocket = await import(new URL('./rocket_program_content.mjs', import.meta.url));
check(same([...config.goods].sort(), [...rocket.LIQUID_FUELS].sort()), `TANK_FARM.goods [${config.goods}] must be the launch fuels [${rocket.LIQUID_FUELS}]`);

// --- C# contract -----------------------------------------------------------
const scriptsDir = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'Cryogenics');
const sources = Object.fromEntries(await Promise.all((await readdir(scriptsDir)).filter((f) => f.endsWith('.cs'))
  .map(async (f) => [f, await readFile(resolve(scriptsDir, f), 'utf8')])));
const all = Object.values(sources).join('\n');
const spec = all.match(/record CryogenicTankSpec : ComponentSpec \{([\s\S]*?)\n  \}/);
const props = spec ? [...spec[1].matchAll(/\[Serialize\] public \S+ (\w+) \{ get; init; \}/g)].map((m) => m[1]) : [];
check(same(props, SPEC_KEYS), `C#: CryogenicTankSpec serializes [${props}], expected [${SPEC_KEYS}]`);
check(same(Object.keys(cryogenicTankSpec(config)), SPEC_KEYS), 'module: cryogenicTankSpec() keys differ from SPEC_KEYS');
const configurator = sources['CryogenicsConfigurator.cs'] ?? '';
for (const line of ['[Context("Game")]', 'Bind<CryogenicTank>().AsTransient()', 'AddDecorator<CryogenicTankSpec, CryogenicTank>()'])
  check(configurator.includes(line), `C#: CryogenicsConfigurator lacks ${line}`);
const patches = sources['CryogenicsPatches.cs'] ?? '';
for (const line of ['#if !UNITY_EDITOR', '[HarmonyPatch(typeof(InventoryInitializer), nameof(InventoryInitializer.Initialize))]',
  'Prefix(ref IGoodDisallower ____goodDisallower)', 'allower.GetComponent<CryogenicTankSpec>()', 'CryogenicIntakeGate.Install(allower, spec)',
  ': IModStarter', 'CreateClassProcessor(typeof(CryogenicIntakeGatePatch)).Patch()'])
  check(patches.includes(line), `C#: CryogenicsPatches lacks ${line}`);
const tank = sources['CryogenicTank.cs'] ?? '';
for (const line of ['bool powered = _power.ActiveAndPowered;', '_gate.SetAccepting(powered);', 'inventory.TakeExisting(new GoodAmount(good, amount));',
  '_notifications.Post(', 'CryogenicIntakeGate.For(_allower)', 'IPersistentEntity', 'UnpoweredHoursKey', 'VentRemainderKey', 'VentedThisOutageKey',
  '_pipes.TryGetConnectedBuilding(port, out var neighbour)', 'graph.Contaminated', 'GetComponent<BuildingPipeSpec>()'])
  check(tank.includes(line), `C#: CryogenicTank lacks ${line}`);
const gate = sources['CryogenicIntakeGate.cs'] ?? '';
for (const line of ['IInitializableGoodDisallower', 'return Accepting ? allowed : _inventory.AmountInStock(goodId);', 'if (allowed == 0 || !_goods.Contains(goodId)) return 0;'])
  check(gate.includes(line), `C#: CryogenicIntakeGate lacks ${line}`);

// Localization keys and placeholder counts against the _loc.T calls.
const locConsts = Object.fromEntries([...tank.matchAll(/public const string (\w+) = "(DeepFrontier\.Cryogenics\.[\w.]+)";/g)].map((m) => [m[1], m[2]]));
const locText = new Map(CRYOGENIC_LOCALIZATION);
check(same(Object.values(locConsts).sort(), [...locText.keys()].sort()), `localization: CryogenicLoc keys [${Object.values(locConsts)}] differ from CRYOGENIC_LOCALIZATION`);
const placeholders = (text) => { const n = [...text.matchAll(/\{(\d+)\}/g)].map((m) => Number(m[1])); return n.length ? Math.max(...n) + 1 : 0; };
let locCalls = 0;
for (let i = all.indexOf('_loc.T(CryogenicLoc.'); i >= 0; i = all.indexOf('_loc.T(CryogenicLoc.', i + 1)) {
  let depth = 0, j = i + 6, start = j + 1, parts = [], inString = false;
  for (; j < all.length; j++) {
    const ch = all[j];
    if (ch === '"' && all[j - 1] !== '\\') inString = !inString;
    if (inString) continue;
    if (ch === '(') depth++;
    else if (ch === ')') { depth--; if (depth === 0) { parts.push(all.slice(start, j)); break; } }
    else if (ch === ',' && depth === 1) { parts.push(all.slice(start, j)); start = j + 1; }
  }
  const name = parts[0].trim().replace('CryogenicLoc.', '');
  const key = locConsts[name];
  locCalls++;
  if (!key) { errors.push(`localization: _loc.T(CryogenicLoc.${name}) has no constant`); continue; }
  check(placeholders(locText.get(key) ?? '') === parts.length - 1, `localization: ${key} has ${placeholders(locText.get(key) ?? '')} placeholders, _loc.T passes ${parts.length - 1}`);
}
check(locCalls >= Object.keys(locConsts).length, `localization: only ${locCalls} _loc.T calls for ${Object.keys(locConsts).length} keys`);

// Status icons: native names in the installed resource container; Timber
// Pipes' own icon in its installed package.
const sprites = Object.fromEntries([...tank.matchAll(/public const string (\w+) = "(\w+)";/g)]
  .filter((m) => !m[2].startsWith('DeepFrontier')).map((m) => [m[1], m[2]]));
const container = (await readFile(resolve(GAME_DATA, 'globalgamemanagers'))).toString('latin1').toLowerCase();
for (const [name, sprite] of Object.entries(sprites)) {
  const native = container.includes(`sprites/statusicons/${sprite.toLowerCase()}`);
  const pipes = await exists(resolve(PIPES_PACKAGE, 'Sprites', 'StatusIcons', `${sprite}.png`));
  check(native || pipes, `status icon CryogenicSprites.${name} = ${sprite} is neither a native nor a Timber Pipes status icon`);
}

// --- native and Timber Pipes contracts (installed assemblies) -------------
const decompile = (dll, refs, type) => {
  try { return execFileSync(ilspy, [dll, '-r', refs, '-t', type], {encoding: 'utf8', maxBuffer: 64 << 20}); }
  catch (error) { errors.push(`${type}: decompilation failed (${error.message.split('\n')[0]})`); return ''; }
};
const audit = await readJson(resolve(root, 'tools', 'modding_api_audit_1_1.json'));
const pipesAudit = JSON.stringify(audit).match(/"path":"TimberPipes\.dll","sha256":"([0-9A-F]+)"/);
const pipesDll = resolve(PIPES_PACKAGE, 'TimberPipes.dll');
const pipesHash = createHash('sha256').update(await readFile(pipesDll)).digest('hex').toUpperCase();
check(pipesAudit && pipesAudit[1] === pipesHash, `Timber Pipes: installed DLL ${pipesHash} differs from the audited 11.4.0 hash ${pipesAudit?.[1]}; re-inspect the contract`);
const pipeRefs = 'C:/Users/Jordan/Documents/Timberborn/ModsBuild/TimberbornModExamples_Data/Managed';
const contracts = [
  [pipesDll, pipeRefs, 'TimberPipes.Components.TankPipe', ['[AddTemplateModule2(typeof(Stockpile))]', 'component.WhitelistedGoodType == "Liquid"', 'PipePortState.Open)']],
  [pipesDll, pipeRefs, 'TimberPipes.Components.BuildingPipe', ['TryGetComponent<BuildingPipeSpec>(out var component) && component.Ports.Length > 0', 'Duplicate port definition']],
  [pipesDll, pipeRefs, 'TimberPipes.Components.DefaultBuildingConnectionProvider', ['isAlreadyPipe = (bool)building.GetEnabledComponent<BuildingPipe>() || (bool)building.GetEnabledComponent<PipeTank>();', 'if (isAlreadyPipe)']],
  [pipesDll, pipeRefs, 'TimberPipes.Services.PipeFluidSimulator', ['if (pipeTank.ConflictsWith(text))', 'graph.Contaminate(new PipeContaminationCause(pipeTank.FluidGoodId, text));']],
  [pipesDll, pipeRefs, 'TimberPipes.Components.PipeTank', ['num += item.UnreservedCapacity(goodId);', 'PipeTankIo.GiveCount(num, item.UnreservedCapacity(goodId))']],
  [pipesDll, pipeRefs, 'TimberPipes.Models.PipeFlowSolver', ['return tankStoredGoodId != pipeGoodId;', 'return !tankTakesPipeGood;']],
  [pipesDll, pipeRefs, 'TimberPipes.Specs.PipePortState', ['Closed,', 'OpenOut,', 'OpenIn,', 'Open\n']],
  [pipesDll, pipeRefs, 'TimberPipes.Services.PipeRegistry', ['public bool TryGetConnectedBuilding(PipePort port, [NotNullWhen(true)] out BuildingPipe? other)']],
  [resolve(GAME_MANAGED, 'Timberborn.Stockpiles.dll'), GAME_MANAGED, 'Timberborn.Stockpiles.StockpileInventoryInitializer', ['inventoryInitializer.AddGoodDisallower(component2);', 'inventoryInitializer.Initialize();']],
  [resolve(GAME_MANAGED, 'Timberborn.InventorySystem.dll'), GAME_MANAGED, 'Timberborn.InventorySystem.InventoryInitializer', ['private IGoodDisallower _goodDisallower;', 'public void Initialize()', 'IGoodDisallower goodDisallower = _goodDisallower ?? new NullGoodDisallower();']],
  [resolve(GAME_MANAGED, 'Timberborn.InventorySystem.dll'), GAME_MANAGED, 'Timberborn.InventorySystem.Inventory', ['int val = GoodCapacity(goodId) - _reservedCapacity.Amount(goodId);', 'return Math.Min(_goodDisallower.AllowedAmount(goodId), _allowedGoods.GetAmount(goodId));']],
  [resolve(GAME_MANAGED, 'Timberborn.MechanicalSystem.dll'), GAME_MANAGED, 'Timberborn.MechanicalSystem.MechanicalNode', ['public bool Active => _blockableObject.IsUnblocked;']],
  [resolve(GAME_MANAGED, 'Timberborn.MechanicalSystem.dll'), GAME_MANAGED, 'Timberborn.MechanicalSystem.MechanicalBuilding', ['public bool ActiveAndPowered => _mechanicalNode.ActiveAndPowered;']],
  [resolve(GAME_MANAGED, 'Timberborn.Localization.dll'), GAME_MANAGED, 'Timberborn.Localization.LocalizationLoader', ["int num = assetName.IndexOf('_');"]],
];
for (const [dll, refs, type, needles] of contracts) {
  const source = decompile(dll, refs, type).replace(/\r\n/g, '\n');
  for (const needle of needles) check(source.includes(needle), `${type}: no "${needle}"; the contract this module relies on changed`);
}

// --- generated data --------------------------------------------------------
const locPath = resolve(dataRoot, LOCALIZATION_FILE);
check(await exists(locPath) && (await readFile(locPath, 'utf8')) === cryogenicLocalization(), `${LOCALIZATION_FILE}: missing or not the module's output; run applyCryogenics`);
const automation = await readJson(automationPath);
const declared = MODULE_SPECS.filter((key) => Object.hasOwn(automation.customSpecs, key));
const expansion = await readFile(resolve(root, 'tools', 'create_frontier_expansion_content.mjs'), 'utf8');
const wiring = "await (await import('./cryogenic_content.mjs')).applyCryogenics();";
const wiringAt = expansion.indexOf(wiring), lastBuildingWrite = expansion.lastIndexOf('buildingBlueprints.push(');
check(wiringAt >= 0 && wiringAt > lastBuildingWrite, `create_frontier_expansion_content.mjs must call ${wiring} after every building blueprint is written`);
const templatePath = await guard('template lookup', () => findTemplate(dataRoot, config));
let template = null;
if (config.status === 'awaiting-template') {
  check(!templatePath, `${config.template}.IronTeeth exists (${templatePath}) while TANK_FARM.status is awaiting-template`);
  check(!declared.length, `automation customSpecs declares [${declared}] before the template exists; the automation audit rejects unused declarations`);
} else {
  check(templatePath, `TANK_FARM.status is ready but ${config.template}.IronTeeth is not generated in ${dataRoot}`);
  await guard('goods', () => checkGoods(dataRoot, config));
  if (templatePath) {
    template = await readJson(templatePath);
    const id = config.template;
    check(same(template.CryogenicTankSpec, cryogenicTankSpec(config)), `${id}: CryogenicTankSpec ${JSON.stringify(template.CryogenicTankSpec)} != module ${JSON.stringify(cryogenicTankSpec(config))}`);
    if (sockets) {
      // The study sockets lead; connection_content.mjs appends every other
      // flat exterior face as an Open port (validate_connection_faces.mjs).
      const ports = template.BuildingPipeSpec?.Ports ?? [];
      check(same(ports.slice(0, sockets.length), socketPorts(sockets, config)) && ports.every((p) => p.State === config.socketState),
        `${id}: BuildingPipeSpec must start with the study sockets and keep every port ${config.socketState}`);
      await guard(id, () => checkBlueprintSockets(template, sockets, id));
    }
    for (const key of IGNORED_ON_TANKS) check(!template[key], `${id}: ${key} is ignored on a Liquid stockpile tank; remove it`);
    check(template.StockpileSpec?.WhitelistedGoodType === 'Liquid', `${id}: StockpileSpec must whitelist Liquid`);
    check(template.MechanicalBuildingSpec && template.MechanicalNodeSpec?.PowerInput > 0 && template.MechanicalNodeSpec.PowerOutput === 0, `${id}: must be a powered consumer`);
    const role = Object.entries(automation.templates).find(([key]) => key.endsWith(`/${id}.IronTeeth.blueprint`));
    check(role && role[1].role === 'pausable' && role[1].sources?.includes('MechanicalBuildingSpec'), `${id}: automation_content.json templates must declare it pausable via MechanicalBuildingSpec`);
  }
  check(same(declared, MODULE_SPECS), `automation customSpecs must declare [${MODULE_SPECS}], has [${declared}]`);
  const tankSpec = automation.customSpecs.CryogenicTankSpec;
  if (tankSpec) {
    check(tankSpec.kind === 'operational' && tankSpec.evidence?.some((e) => e.contains === 'bool powered = _power.ActiveAndPowered;'),
      'customSpecs.CryogenicTankSpec must be operational with the ActiveAndPowered evidence');
  }
  if (automation.customSpecs.BuildingPipeSpec) check(automation.customSpecs.BuildingPipeSpec.kind === 'dependency', 'customSpecs.BuildingPipeSpec must be kind dependency');
}

// --- design numbers ----------------------------------------------------------
const capacity = template?.StockpileSpec?.MaxCapacity ?? 2000;
const vent = config.ventPerHourOnPowerLoss, buffer = config.bufferHours;
const liquefaction = expansion.match(/\['Liquefaction', [^\]]*?, ([\d.]+), \[[^\]]*\], \[\{ Id: 'LiquidHydrogen', Amount: (\d+) \}/);
const perPlantHour = liquefaction ? Number(liquefaction[2]) / Number(liquefaction[1]) : null;
const launchLoads = rocket.MISSIONS.map((m) => [m.Id, m.ingredients.find(([g]) => g === 'LiquidHydrogen')[1]]);
const design = {
  status: config.status, template: templatePath, capacity, powerHp: template?.MechanicalNodeSpec?.PowerInput ?? null,
  bufferHours: buffer, ventPerHourOnPowerLoss: vent, ventPerDay: vent * 24, fullTankVentDaysAfterBuffer: +(capacity / vent / 24).toFixed(2),
  fractionOfFullTankPerDay: +(vent * 24 / capacity).toFixed(3), liquefactionPerPlantHour: perPlantHour,
  plantHoursLostPerOutageHour: perPlantHour ? vent / perPlantHour : null, launchHydrogenLoads: Object.fromEntries(launchLoads),
  sockets: sockets?.map((s) => ({good: s.good, cell: s.cell, direction: s.direction, state: config.socketState})),
};
if (reportPath) await writeFile(reportPath, `${JSON.stringify({errors, design}, null, 2)}\n`, 'utf8');
if (errors.length) {
  console.error(`Cryogenic content validation failed:\n  ${errors.join('\n  ')}`);
  process.exitCode = 1;
} else {
  console.log(`Cryogenic content valid (${design.status}). Buffer ${buffer} h, then ${vent}/h (${design.ventPerDay}/day, `
    + `${(design.fractionOfFullTankPerDay * 100).toFixed(1)}% of a ${capacity} tank per day; full tank gone ${design.fullTankVentDaysAfterBuffer} days after the buffer). `
    + `Sockets: ${design.sockets.map((s) => `${s.good} ${s.cell} ${s.direction} ${s.state}`).join(', ')}.`);
}
