// Static check of the Modular Warehouse: a core that haulers use and Warehouse
// Modules attached beside it or stacked on it (src/DeepFrontier/Scripts/ModularStorage).
//
//   node tools/validate_modular_warehouse.mjs [dataRoot]
//
// Catalog (tools/frontier_progression.json modularWarehouse): whole positive
// slots and capacities of Box goods, early-game science (cost tier T1), the
// module no denser than the vanilla Large Warehouse, the core first in the menu.
// Generated blueprints: the specs equal the catalog; no native single-good
// stockpile left from the LargeWarehouse template; unpowered and worker-free;
// the core keeps the warehouse door, the module has none; the module stands on
// ground or a stackable block and both tops take a stacked module (Stackable).
// Runtime: one native inventory (unlimited, the slots limit each good) with the
// core as its good disallower and native Emptiable as its inventory validator,
// the native decorators a stockpile gets, slot modes in the native
// StockpilePriorityToggle order, the network search over native block occupancy
// across the six faces after loading and after finished-state changes, closing
// slots on fewer modules, persistence through the native SerializedGood
// serializer, native events subscribed in InitializeEntity, no Harmony and no
// dependency mod.
// Native contract (Timberborn 1.1.2.8, decompiled from the plugin assemblies).
import {readFile, readdir, access} from 'node:fs/promises';
import {resolve, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = resolve(process.argv[2] ?? join(root, 'src', 'DeepFrontier', 'Data'));
const vanilla = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');
const scripts = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'ModularStorage');
const errors = [];
const fail = (message) => errors.push(message);
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const exists = (path) => access(path).then(() => true, () => false);
const compact = (text) => text.replace(/\s+/g, '');
const has = (text, needle) => compact(text).includes(compact(needle));

// --- Catalog.
const {core, module} = (await readJson(resolve(root, 'tools', 'frontier_progression.json'))).modularWarehouse;
const largeWarehouse = await readJson(resolve(vanilla, 'Buildings', 'Storage', 'LargeWarehouse', 'LargeWarehouse.IronTeeth.blueprint.json'));
const large = largeWarehouse.StockpileSpec;
const largeCells = Object.values(largeWarehouse.BlockObjectSpec.Size).reduce((a, b) => a * b, 1);
const tiers = (await readJson(resolve(root, 'tools', 'building_construction_costs.json'))).lategameRule.tiers;
if (!Number.isInteger(core.maxSlots) || core.maxSlots < 2) fail('catalog: core.maxSlots must be a whole number of at least 2');
for (const [name, entry] of [['core', core], ['module', module]]) {
  if (!Number.isInteger(entry.capacity) || entry.capacity < 1) fail(`catalog: ${name}.capacity must be a whole positive number`);
  if (entry.costTier !== 'T1' || entry.scienceUnlock > tiers.T1.scienceMax) fail(`catalog: the ${name} is an early-game building (T1, at most ${tiers.T1.scienceMax} science)`);
  if (entry.toolGroup !== 'Storage') fail(`catalog: the ${name} belongs in the Storage menu`);
}
if (core.goodType !== large.WhitelistedGoodType) fail(`catalog: core.goodType must be ${large.WhitelistedGoodType}, as the vanilla warehouses`);
if (module.scienceUnlock < core.scienceUnlock) fail('catalog: the module unlocks with or after its core (menu order: core first)');

// --- Generated data.
const blueprint = async (entry) => {
  const path = resolve(dataRoot, 'Buildings', 'Storage', entry.id, `${entry.id}.IronTeeth.blueprint.json`);
  if (!await exists(path)) { fail(`${entry.id}: blueprint not generated`); return null; }
  return readJson(path);
};
const collection = await readJson(resolve(dataRoot, 'TemplateCollections', 'TemplateCollection.Buildings.IronTeeth.blueprint.json'));
const csv = (await readFile(resolve(dataRoot, 'Localizations', 'enUS.csv'), 'utf8')).split(/\r?\n/);
const blocksAt = (bp, z) => {
  const {X, Y} = bp.BlockObjectSpec.Size;
  return bp.BlockObjectSpec.Blocks.slice(z * X * Y, (z + 1) * X * Y);
};
for (const entry of [core, module]) {
  const bp = await blueprint(entry);
  if (!bp) continue;
  const id = entry.id;
  for (const key of ['StockpileSpec', 'StockpileGoodColumnVisualizerSpec', 'StockpilePlaneVisualizerSpec', 'StockpileGoodPileVisualizerSpec', 'FixedStockpileSpec'])
    if (bp[key]) fail(`${id}: ${key} would add a native single-good stockpile`);
  for (const key of ['MechanicalNodeSpec', 'MechanicalBuildingSpec', 'WorkplaceSpec']) if (bp[key]) fail(`${id}: an early warehouse needs no ${key}`);
  if (bp.BuildingSpec.ScienceCost !== entry.scienceUnlock) fail(`${id}: science ${bp.BuildingSpec.ScienceCost} is not the catalog's ${entry.scienceUnlock}`);
  if (bp.PlaceableBlockObjectSpec.ToolGroupId !== 'Storage') fail(`${id}: tool group ${bp.PlaceableBlockObjectSpec.ToolGroupId} is not Storage`);
  const {Z} = bp.BlockObjectSpec.Size;
  const top = blocksAt(bp, Z - 1).filter((b) => b.Occupations !== 'None');
  if (!top.length || top.some((b) => b.Stackable !== 'BlockObject')) fail(`${id}: every top block must be Stackable BlockObject so modules stack on it`);
  if (!await exists(resolve(dataRoot, `${bp.LabeledEntitySpec.Icon}.png`))) fail(`${id}: icon ${bp.LabeledEntitySpec.Icon}.png is missing`);
  if (!collection.TemplateCollectionSpec['Blueprints#append'].includes(`Buildings/Storage/${id}/${id}.IronTeeth.blueprint`)) fail(`${id}: not in the Iron Teeth template collection`);
  for (const key of ['DisplayName', 'Description', 'FlavorDescription'])
    if (!csv.some((line) => line.startsWith(`Building.${id}.${key},`))) fail(`${id}: Building.${id}.${key} row missing`);
  if (id === core.id) {
    const spec = bp.ModularWarehouseSpec;
    if (!spec || spec.MaxSlots !== core.maxSlots || spec.CoreCapacity !== core.capacity || spec.GoodType !== core.goodType)
      fail(`${id}: ModularWarehouseSpec ${JSON.stringify(spec)} differs from the catalog core`);
    if (!bp.BlockObjectSpec.Entrance?.HasEntrance || !bp.EnterableSpec || !bp.BuildingAccessibleSpec) fail(`${id}: the core keeps the warehouse's native door`);
  } else {
    const spec = bp.WarehouseModuleSpec;
    if (!spec || spec.Capacity !== module.capacity) fail(`${id}: WarehouseModuleSpec ${JSON.stringify(spec)} differs from the catalog module`);
    if (bp.BlockObjectSpec.Entrance?.HasEntrance || bp.EnterableSpec || bp.BuildingAccessibleSpec) fail(`${id}: a module has no door, access or enterable spec`);
    if (blocksAt(bp, 0).some((b) => b.Occupations !== 'None' && b.MatterBelow !== 'GroundOrStackable')) fail(`${id}: its ground blocks stand on ground or a stackable block (stacking)`);
    const cells = bp.BlockObjectSpec.Blocks.filter((b) => b.Occupations !== 'None').length;
    if (module.capacity / cells > large.MaxCapacity / largeCells + 1e-9) fail(`${id}: ${module.capacity} in ${cells} cells is denser than the vanilla Large Warehouse (${large.MaxCapacity} in ${largeCells})`);
  }
}
for (const key of ['DeepFrontier.ModularWarehouse.Network', 'DeepFrontier.ModularWarehouse.ModuleUnattached'])
  if (!csv.some((line) => line.startsWith(`${key},`))) fail(`localization ${key} missing`);

// --- Runtime.
const sources = {};
for (const entry of await readdir(scripts)) if (entry.endsWith('.cs')) sources[entry] = (await readFile(resolve(scripts, entry), 'utf8')).replace(/\/\/.*$/gm, '');
const all = Object.values(sources).join('\n');
const warehouse = sources['ModularWarehouse.cs'] ?? '';
const network = sources['WarehouseModule.cs'] ?? '';
const hauling = sources['ModularWarehouseHauling.cs'] ?? '';
const configurator = sources['ModularWarehouseConfigurator.cs'] ?? '';
const panel = (sources['ModularWarehousePanel.cs'] ?? '') + (sources['WarehouseGoodSelectionBox.cs'] ?? '');
if (/HarmonyLib|\[HarmonyPatch|\bHarmony\b/.test(all)) fail('runtime: the warehouse uses no Harmony');
if (/\b(TimberPipes|ConveyorBelt|PowerLines|TimberUi|ModdableRecipes|ModdableTimberborn|ModSettings)\./.test(all)) fail('runtime: no dependency mod (the editor build compiles it without them)');
if (/IInventoryValidator|MechanicalBuilding|ActiveAndPowered/.test(warehouse + hauling)) fail('runtime: the core is unpowered; native Emptiable is its inventory validator');
if (!/class ModularWarehouse\s*:[^{]*\bIGoodDisallower\b/.test(warehouse)) fail('runtime: ModularWarehouse must be the inventory\'s IGoodDisallower');
for (const iface of ['IPersistentEntity', 'IInitializableEntity', 'IFinishedStateListener', 'IDuplicable<ModularWarehouse>'])
  if (!new RegExp(`class ModularWarehouse\\s*:[^{]*\\b${iface.replace(/[<>]/g, '\\$&')}`).test(warehouse)) fail(`runtime: ModularWarehouse must implement ${iface}`);
const enumMatch = warehouse.match(/enum WarehouseSlotMode\s*\{([^}]*)\}/);
if (!enumMatch || compact(enumMatch[1]) !== 'Accept,Obtain,Supply,Empty') fail('runtime: slot modes must be Accept, Obtain, Supply, Empty (native StockpilePriorityToggle order)');
const allowed = warehouse.match(/public int AllowedAmount\(string goodId\)\s*\{([\s\S]*?)\n    \}/);
if (!allowed || !has(allowed[1], 'if (slot.Mode == WarehouseSlotMode.Empty) return 0;') || !has(allowed[1], 'Math.Max(0, SlotCapacity(i) - slot.Leftovers.Sum(Inventory.AmountInStock))') || !has(allowed[1], 'return 0;'))
  fail('runtime: AllowedAmount gives 0 to Empty slots and unselected goods and the slot share less its leftovers to a selected good');
if (!has(warehouse, 'public int ActiveSlots => Math.Min(_slots.Length, 1 + Modules);') || !has(warehouse, 'return NetworkCapacity / active + (slot < NetworkCapacity % active ? 1 : 0);'))
  fail('runtime: open slots = 1 + modules (capped) and the capacity is shared equally');
const setNetwork = warehouse.match(/public void SetNetwork\(int modules, int capacity\)\s*\{([\s\S]*?)\n    \}/);
if (!setNetwork || !has(setNetwork[1], 'for (int i = ActiveSlots; i < _slots.Length; i++)') || !has(setNetwork[1], 'slot.Good = null;') || !has(setNetwork[1], 'InvokeDisallowedGoodsChanged(good)'))
  fail('runtime: SetNetwork closes the slots past the open count and tells the inventory every affected good');
const awake = warehouse.match(/public void Awake\(\)\s*\{([\s\S]*?)\n    \}/);
if (!awake || /\+=/.test(awake[1])) fail('runtime: ModularWarehouse subscribes to no event in Awake (load replays it)');
const init = warehouse.match(/public void InitializeEntity\(\)\s*\{([\s\S]*?)\n    \}/);
if (!init || !has(init[1], 'Inventory.InventoryStockChanged += OnInventoryStockChanged;')) fail('runtime: the stock subscription belongs in InitializeEntity');
if (!has(warehouse, 'new PropertyKey<SerializedGood>("Good" + i)') || !has(warehouse, 'loader.GetObsoletable(GoodKey(i), _goodSerializer, out var good)'))
  fail('runtime: slot goods persist through the native SerializedGood serializer (retired goods load as obsolete)');
if (!has(warehouse, 'saver.Set(ModulesKey, Modules);') || !has(warehouse, 'Modules = loader.Get(ModulesKey);')) fail('runtime: the core saves the network it last saw, so a load starts from it');
if (!/throw new InvalidOperationException\(\$"ModularWarehouse save has an unknown slot mode/.test(warehouse)) fail('runtime: an unknown saved slot mode fails explicitly');
for (const needle of ['_inventories.CreateWithUnlimitedCapacity(decorator, InventoryComponentName);', 'init.AddAllowedGoodType(spec.GoodType);', 'init.HasPublicOutput();',
  'init.HasPublicInput();', 'init.AddGoodDisallower(subject);', 'init.Initialize();', '_needs.AddNeedBehavior(decorator);'])
  if (!has(warehouse, needle)) fail(`runtime: the inventory initializer must call ${needle}`);
if (!/IDedicatedDecoratorInitializer<\s*ModularWarehouse\s*,\s*Inventory\s*>/.test(warehouse)) fail('runtime: the inventory comes from a dedicated decorator initializer');
for (const needle of ['class ModularWarehouseNetwork : IPostLoadableSingleton, ITickableSingleton', '_blocks.GetObjectsAt(next)',
  'new Vector3Int(0, 0, 1), new Vector3Int(0, 0, -1)', 'if (_loaded && _dirty) Update();', '_cores.OrderBy(c => c.GetComponent<EntityComponent>().EntityId)',
  'core.SetNetwork(attached.Count, core.GetComponent<ModularWarehouseSpec>().CoreCapacity + attached.Sum(m => m.Capacity));'])
  if (!has(network, needle)) fail(`runtime: the network search must keep ${needle}`);
if (!has(network, 'private const string UnattachedSprite = "UnconnectedBuilding";')) fail('runtime: an unattached module shows the native UnconnectedBuilding status icon');
for (const decorator of ['ModularWarehouseSpec, ModularWarehouse', 'ModularWarehouse, Emptiable', 'ModularWarehouse, EmptyInventoriesWorkplaceBehavior',
  'ModularWarehouse, RemoveUnwantedStockWorkplaceBehavior', 'ModularWarehouse, InventoryNeedBehavior',
  'ModularWarehouse, ModularWarehouseObtainBehavior', 'ModularWarehouse, ModularWarehouseObtainHaulProvider',
  'ModularWarehouse, ModularWarehouseSupplyBehavior', 'ModularWarehouse, ModularWarehouseSupplyHaulProvider', 'WarehouseModuleSpec, WarehouseModule'])
  if (!has(configurator, `builder.AddDecorator<${decorator}>();`)) fail(`runtime: missing decorator <${decorator}>`);
if (!has(configurator, 'Bind<ModularWarehouseNetwork>().AsSingleton();') || !has(configurator, '[Context("Game")]')) fail('runtime: the network is a Game singleton');
for (const needle of ['if (source == own) return false;', 'obtainer.IsObtaining', 'warehouse.HasSlot(good, WarehouseSlotMode.Obtain)'])
  if (!has(hauling, needle)) fail(`runtime: Obtain must not take from itself, an obtaining stockpile or an obtaining slot (${needle})`);
for (const needle of ['if (target == own) return false;', 'supplier.IsSupplying', 'warehouse.HasSlot(good, WarehouseSlotMode.Supply)'])
  if (!has(hauling, needle)) fail(`runtime: Supply must not give to itself, a supplying stockpile or a supplying slot (${needle})`);
if ((hauling.match(/if \(!_warehouse\.Operating\) return/g) ?? []).length !== 4) fail('runtime: Obtain and Supply behaviors and providers stop while the core is blocked');
for (const view of ['Game/EntityPanel/StockpileInventoryFragment', 'Game/StockpileGoodSelectionBox', 'Game/EntityPanel/GoodSelectionBoxRow', 'Game/EntityPanel/StockpileInventoryFragmentItem'])
  if (!panel.includes(`"${view}"`)) fail(`panel: loads the native view ${view}`);
if (!panel.includes('$"StockpilePriority.{mode}"') || !panel.includes('$"stockpile-priority-toggle__icon--{icon}"')) fail('panel: the toggle uses the native StockpilePriority texts and icons');
const fragmentInit = panel.match(/public VisualElement InitializeFragment\(\)\s*\{([\s\S]*?)\n    \}/);
if (!fragmentInit || /_views\.Create|GetComponent|_loc\.T/.test(fragmentInit[1])) fail('panel: InitializeFragment builds nothing that depends on another singleton or an entity');
if (!(await readFile(resolve(root, 'tools', 'validate_single_inventory.mjs'), 'utf8')).includes("ModularWarehouse: 'ModularWarehouseSpec'"))
  fail('validate_single_inventory.mjs must declare the core inventory');

// --- Native contract (Timberborn 1.1.2.8), decompiled from the plugin assemblies.
const plugins = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Plugins', 'Timberborn');
const decompile = (dll, type) => {
  try {
    return execFileSync(resolve(root, 'tools', 'dotnet', 'ilspycmd.exe'), [resolve(plugins, dll), '-r', plugins, '-t', type], {encoding: 'utf8', maxBuffer: 64 << 20});
  } catch (error) {
    fail(`native: ${dll} ${type}: decompilation failed (${error.message.split('\n')[0]})`);
    return '';
  }
};
for (const [dll, type, patterns, what] of [
  ['Timberborn.InventorySystem.dll', 'Timberborn.InventorySystem.Inventory',
    [/return Math\.Min\(_goodDisallower\.AllowedAmount\(goodId\), _allowedGoods\.GetAmount\(goodId\)\);/, /num \+= Math\.Max\(0, good\.Amount - LimitedAmount\(good\.GoodId\)\);/,
      /_goodDisallower\.DisallowedGoodsChanged \+= OnDisallowedGoodsChanged;/],
    'each good is limited by min(disallower, allowed amount), stock above it is unwanted, and a disallower change rechecks it'],
  ['Timberborn.InventorySystem.dll', 'Timberborn.InventorySystem.InventoryInitializerFactory', [/return Create\(inventory, int\.MaxValue, componentName\);/],
    'an unlimited inventory has int.MaxValue capacity'],
  ['Timberborn.SimpleOutputBuildings.dll', 'Timberborn.SimpleOutputBuildings.SimpleOutputInventoryInitializer', [/CreateWithUnlimitedCapacity\(decorator, InventoryComponentName\)/],
    'native buildings use unlimited inventories limited elsewhere'],
  ['Timberborn.InventorySystem.dll', 'Timberborn.InventorySystem.DistrictInventoryPicker', [/inventory\.GetComponent<IInventoryValidator>\(\)\.ValidInventory/],
    'deliveries read the inventory\'s IInventoryValidator'],
  ['Timberborn.Emptying.dll', 'Timberborn.Emptying.Emptiable', [/class Emptiable : [^{]*IInventoryValidator/], 'Emptiable is the native IInventoryValidator'],
  ['Timberborn.Emptying.dll', 'Timberborn.Emptying.EmptyingConfigurator',
    [/AddDecorator<Emptiable, HaulCandidate>\(\)/, /AddDecorator<Emptiable, UnwantedStockHaulBehaviorProvider>\(\)/, /AddDecorator<Emptiable, EmptiableHaulBehaviorProvider>\(\)/],
    'Emptiable brings HaulCandidate and the emptying haul providers'],
  ['Timberborn.Stockpiles.dll', 'Timberborn.Stockpiles.StockpileInventoryInitializer',
    [/AddAllowedGoodType\(component\.WhitelistedGoodType\)/, /HasPublicOutput\(\)/, /HasPublicInput\(\)/, /AddGoodDisallower\(component2\)/],
    'a warehouse inventory takes every good of its type with public input and output and its allower as disallower'],
  ['Timberborn.StockpilePrioritySystem.dll', 'Timberborn.StockpilePrioritySystem.ObtainGoodWorkplaceBehavior', [/TryCarryFromAnyInventory\(allowedGood, _inventory, CanObtainFrom\)/, /return !component\.IsObtaining;/],
    'Obtain carries from any inventory that is not obtaining'],
  ['Timberborn.StockpilePrioritySystem.dll', 'Timberborn.StockpilePrioritySystem.SupplyGoodWorkplaceBehavior', [/TryCarryToAnyInventory\(allowedGood, _inventory, CanGiveTo\)/, /return !component\.IsSupplying;/],
    'Supply carries to any inventory that is not supplying'],
  ['Timberborn.Emptying.dll', 'Timberborn.Emptying.RemoveUnwantedStockLaborBehavior', [/InventoriesWithUnwantedStock/],
    'laborers carry out any registered inventory\'s unwanted stock'],
  ['Timberborn.Carrying.dll', 'Timberborn.Carrying.CarryRootBehavior', [/if \(capacityReservation\.Inventory\.HasUnreservedCapacity\(capacityReservation\.GoodAmount\)\)/],
    'a delivery checks capacity again on arrival (a slot that shrinks mid-delivery is safe)'],
  ['Timberborn.BlockSystem.dll', 'Timberborn.BlockSystem.BlockService', [/return _blocks\.GetCopyAtOrDefault\(coordinates\)\.BlockObjects;/],
    'GetObjectsAt is safe outside the map'],
  ['Timberborn.RecoverableGoodSystem.dll', 'Timberborn.RecoverableGoodSystem.RecoverableGoodProvider', [/AddGoodsFromInventory\(recoverableGoodRegistry, inventory\)/],
    'deleting the core recovers its stored goods'],
  ['Timberborn.StockpilePriorityUISystem.dll', 'Timberborn.StockpilePriorityUISystem.StockpilePriorityToggle',
    [/stockpile-priority-toggle__icon--accept/, /StockpilePriority\.Obtain/, /_sliderToggleFactory\.Create\(parent, sliderToggleItem, sliderToggleItem3, sliderToggleItem4, sliderToggleItem2\)/],
    'the priority toggle is Accept, Obtain, Supply, Empty with the stockpile-priority-toggle icons'],
]) {
  const source = decompile(dll, type);
  if (source && !patterns.every((p) => p.test(source))) fail(`native: ${type}: no longer true that ${what}`);
}

if (errors.length) {
  for (const error of errors) console.error(`FAIL: ${error}`);
  console.error(`Modular Warehouse validation failed (${errors.length})`);
  process.exit(1);
}
console.log(`Modular Warehouse validation passed: core ${core.capacity} with up to ${core.maxSlots} slots, modules of ${module.capacity}; runtime and native contract checked.`);
