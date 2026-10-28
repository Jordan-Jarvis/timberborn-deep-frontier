// Static validator for the radiation content (tools/radiation_content.mjs) and
// its C# contract (src/DeepFrontier/Scripts/Radiation).
//
// Usage: node tools/validate_radiation_content.mjs [dataRoot] [--strict-chain] [--scripts=<dir>]
//   dataRoot defaults to src/DeepFrontier/Data.
//   --scripts checks another Radiation C# folder (default src/DeepFrontier/Scripts/Radiation).
//   --strict-chain also fails while no reactor/refinery recipe produces
//   RadioactiveSludge (that wiring belongs to the progression generator).
// Exits 1 on any failure. Static evidence only: nothing here proves runtime
// behaviour; see the in-game acceptance assertions in the radiation report.
import {readFile, access, readdir} from 'node:fs/promises';
import {resolve, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {RADIATION_BUILDINGS, RADIATION_RECIPES, RADIATION_SPRINGS, SPRING_SPEC, SPRING_RADIOACTIVE_PER_HOUR, RECOVERY_MAX_WATER_PER_CYCLE,
  SLUDGE, CONTAMINATED_WATER, NEED, ZOMBIE_MOVEMENT_DELTA, ZOMBIE_NAME, readTuning, hospitalTreatmentRate, waterPerStrengthHour} from './radiation_content.mjs';
import {buildVariants, WATER, SOIL, SHADER_PATH} from './native_shader_variants.mjs';
import {studyPipePort} from './lategame_building_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const vanillaRoot = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');
const args = process.argv.slice(2);
const scripts = resolve(args.find(a => a.startsWith('--scripts='))?.slice('--scripts='.length) ?? resolve(root, 'src', 'DeepFrontier', 'Scripts', 'Radiation'));
const strictChain = args.includes('--strict-chain');
const dataRoot = resolve(args.find(a => !a.startsWith('--')) ?? resolve(root, 'src', 'DeepFrontier', 'Data'));

const failures = [];
const notes = [];
const fail = message => failures.push(message);
const check = (condition, message) => { if (!condition) fail(message); return condition; };

async function exists(path) { try { await access(path); return true; } catch { return false; } }
async function readJson(path) {
  if (!await exists(path)) { fail(`missing ${path}`); return null; }
  return JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
}
async function walk(dir, out = []) {
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) await walk(path, out);
    else if (entry.name.endsWith('.blueprint.json')) out.push(path);
  }
  return out;
}

const tuning = await readTuning();
const csharp = {};
for (const file of await readdir(scripts)) if (file.endsWith('.cs')) csharp[file] = await readFile(join(scripts, file), 'utf8');
const allCs = Object.values(csharp).join('\n');
const constant = name => allCs.match(new RegExp(`const string ${name} = "([^"]+)"`))?.[1];

// --- ids shared by C# and data
check(constant('SludgeGoodId') === SLUDGE, `RadiationTuning.SludgeGoodId must be ${SLUDGE}`);
check(constant('ContaminatedWaterGoodId') === CONTAMINATED_WATER, `RadiationTuning.ContaminatedWaterGoodId must be ${CONTAMINATED_WATER}`);
check(constant('NeedId') === NEED, `RadiationTuning.NeedId must be ${NEED}`);
check(constant('WaterGoodId') === 'Water', 'RadiationTuning.WaterGoodId must be Water');

// --- goods
const goodCollection = await readJson(resolve(dataRoot, 'GoodCollections', 'GoodCollection.IronTeeth.blueprint.json'));
const goodIds = goodCollection?.GoodCollectionSpec?.['Goods#append'] ?? [];
for (const id of [SLUDGE, CONTAMINATED_WATER]) {
  const good = (await readJson(resolve(dataRoot, 'Goods', `Good.${id}.blueprint.json`)))?.GoodSpec;
  if (!good) continue;
  check(good.Id === id, `${id}: GoodSpec.Id mismatch`);
  check(good.GoodType === 'Liquid', `${id}: must be a Liquid good (Timber Pipes and liquid tanks discover GoodType Liquid)`);
  check(!['Water', 'Badwater'].includes(good.GoodGroupId), `${id}: must not join the single-resource Water/Badwater groups (TopBarPanel.CreateCounter uses Single())`);
  check(Array.isArray(good.ConsumptionEffects) && good.ConsumptionEffects.length === 0, `${id}: must have no consumption effects (undrinkable)`);
  check(good.Icon === `Sprites/Goods/${id}Icon`, `${id}: icon path`);
  check(await exists(resolve(dataRoot, 'Sprites', 'Goods', `${id}Icon.png`)), `${id}: icon PNG missing`);
  check(await exists(resolve(dataRoot, 'Sprites', 'Goods', `${id}Icon.png.meta.json`)), `${id}: icon meta missing`);
  check(goodIds.filter(g => g === id).length === 1, `${id}: must appear once in the Iron Teeth good collection`);
}
const goodExists = async id => await exists(resolve(dataRoot, 'Goods', `Good.${id}.blueprint.json`))
  || await exists(resolve(vanillaRoot, 'Goods', `Good.${id}.blueprint.json`));

// --- need
const need = await readJson(resolve(dataRoot, 'Needs', `Need.Beaver.${NEED}.blueprint.json`));
if (need) {
  const spec = need.NeedSpec;
  check(spec.Id === NEED && spec.CharacterType === 'Beaver', 'Irradiation need id/character');
  check(spec.MinimumValue === -1 && spec.MaximumValue === 0 && spec.StartingValue === 0, 'Irradiation need must run -1..0 starting at 0');
  check(spec.DailyDelta === 0, 'Irradiation need must not recover passively (DailyDelta 0)');
  check(spec.UnfavorableWellbeing < -10, 'Irradiation must be worse for wellbeing than badwater contamination (-10)');
  check(!!need.CriticalNeedSpec, 'Irradiation needs CriticalNeedSpec (ContaminationNeedEnabler resets non-critical needs)');
  check(!!need.NeedPreventingWorkSpec, 'Irradiation should prevent work');
  check(!need.LethalNeedSpec, 'Irradiation must not carry LethalNeedSpec: exposure sets the need to minimum at once; death comes from the untreated-sickness clock');
  notes.push(`placeholder status sprite on the need: ${need.CriticalNeedSpec?.SpriteName}`);
}
const needCollection = await readJson(resolve(dataRoot, 'NeedCollections', 'NeedCollection.IronTeeth.blueprint.json'));
check((needCollection?.NeedCollectionSpec?.['Needs#append'] ?? []).filter(n => n === NEED).length === 1, 'Irradiation must appear once in the Iron Teeth need collection');

// --- hospital
const hospital = await readJson(resolve(dataRoot, 'Buildings', 'Wellbeing', 'Hospital', 'Hospital.IronTeeth.blueprint.json'));
if (hospital) {
  const effects = hospital.AttractionSpec?.Effects ?? [];
  const effect = effects.filter(e => e.NeedId === NEED);
  if (check(effect.length === 1, 'Hospital must have exactly one Irradiation effect')) {
    const {pointsPerHour, duty} = await hospitalTreatmentRate(tuning);
    check(Math.abs(effect[0].PointsPerHour - pointsPerHour) < 1e-9, `Hospital Irradiation rate ${effect[0].PointsPerHour} != ${pointsPerHour}`);
    check(effect[0].SatisfyToMaxValue === true, 'Hospital Irradiation effect must SatisfyToMaxValue (admitted until cured)');
    notes.push(`hospital Irradiation ${pointsPerHour.toFixed(6)} points/h = 1/(${tuning.treatmentDays} days * 24 * duty ${duty})`);
  }
  // Native MaxValueNeedsAreActive releases a patient once every SatisfyToMaxValue
  // need is at its maximum: all-or-none, or one healthy condition ends another's stay.
  check(effects.length > 0 && effects.every(e => e.SatisfyToMaxValue === true), 'Every Hospital effect must SatisfyToMaxValue (all-or-none: admitted until cured)');
  const meals = hospital.HospitalPantrySpec;
  check(meals?.WaterGoodId === 'Water' && meals.FoodCapacityPerGood > 0 && meals.WaterCapacity > 0 && meals.LowStockUnits > 0, 'Hospital must stock patient meals (HospitalPantrySpec): admitted patients cannot leave to eat');
  const progressionMeals = (await readJson(resolve(root, 'tools', 'frontier_progression.json')))?.hospital?.patientMeals;
  check(progressionMeals?.zombieNeedMultiplier === Number((csharp['IRadiationService.cs'] ?? '').match(/ZombieNeedDecayMultiplier = ([0-9.]+)f/)?.[1]), 'hospital.patientMeals.zombieNeedMultiplier must equal RadiationTuning.ZombieNeedDecayMultiplier (pantry water sized for zombies)');
}

// --- recipes
for (const recipe of RADIATION_RECIPES) {
  const spec = (await readJson(resolve(dataRoot, 'Recipes', `Recipe.${recipe.id}.blueprint.json`)))?.RecipeSpec;
  if (!spec) continue;
  check(spec.Id === recipe.id && spec.CycleDurationInHours === recipe.hours, `${recipe.id}: id/duration`);
  for (const item of [...spec.Ingredients, ...spec.Products]) check(await goodExists(item.Id), `${recipe.id}: unknown good ${item.Id}`);
}

// --- buildings
const templates = (await readJson(resolve(dataRoot, 'TemplateCollections', 'TemplateCollection.Buildings.IronTeeth.blueprint.json')))
  ?.TemplateCollectionSpec?.['Blueprints#append'] ?? [];
const waterOrders = new Map();
for (const base of [resolve(vanillaRoot, 'Buildings'), resolve(dataRoot, 'Buildings')]) {
  for (const file of await walk(base)) {
    if (base.startsWith(vanillaRoot) && !file.includes('.IronTeeth.')) continue;
    const value = JSON.parse((await readFile(file, 'utf8')).replace(/^﻿/, ''));
    const placeable = value.PlaceableBlockObjectSpec;
    if (!placeable) continue;
    // Tool orders must be unique within a group (the native Water group, or the Deep
    // Frontier sub-group tools/tool_groups.json moves a building into).
    const key = `${placeable.ToolGroupId}:${placeable.ToolOrder}`;
    const list = waterOrders.get(key) ?? [];
    list.push(file);
    waterOrders.set(key, list);
  }
}
const blueprintKeys = [];
const specFields = (record) => {
  if (new RegExp(`record ${record} : ComponentSpec \\{ \\}`).test(allCs)) return [];
  const match = allCs.match(new RegExp(`record ${record} : ComponentSpec \\{([\\s\\S]*?)\\n  \\}`));
  if (!match) return null;
  return [...match[1].matchAll(/\[Serialize\] public \w+ (\w+) \{/g)].map(m => m[1]);
};
for (const building of RADIATION_BUILDINGS) {
  const relative = `Buildings/Water/${building.id}/${building.id}.IronTeeth.blueprint`;
  const value = await readJson(resolve(dataRoot, `${relative}.json`));
  if (!value) continue;
  check(templates.filter(t => t === relative).length === 1, `${building.id}: must appear once in the building template collection`);
  check(value.TemplateSpec?.TemplateName === `${building.id}.IronTeeth`, `${building.id}: TemplateName`);
  check(JSON.stringify(value.ManufactorySpec?.ProductionRecipeIds) === JSON.stringify(building.recipes), `${building.id}: recipes`);
  for (const id of building.recipes) check(await exists(resolve(dataRoot, 'Recipes', `Recipe.${id}.blueprint.json`)), `${building.id}: recipe ${id} missing`);
  for (const cost of value.BuildingSpec.BuildingCost) check(await goodExists(cost.Id), `${building.id}: unknown cost good ${cost.Id}`);
  for (const forbidden of ['WaterOutputSpec', 'ManufactoryWaterProducerSpec', 'ManufactoryWaterContaminationProducerSpec',
    'ManufactoryWaterConsumerSpec', 'ManufactoryWaterContaminationConsumerSpec'])
    check(!value[forbidden], `${building.id}: must not keep native water component ${forbidden}`);
  const placeable = value.PlaceableBlockObjectSpec;
  const orders = waterOrders.get(`${placeable.ToolGroupId}:${placeable.ToolOrder}`) ?? [];
  check(orders.length === 1, `${building.id}: ${placeable.ToolGroupId} tool order ${placeable.ToolOrder} collides: ${orders.join(', ')}`);
  const size = value.BlockObjectSpec.Size;
  if (building.kind === 'export') {
    check(value.MapEdgeSiteSpec && Object.keys(value.MapEdgeSiteSpec).length === 0, `${building.id}: needs MapEdgeSiteSpec {}`);
    check(specFields('MapEdgeSiteSpec')?.length === 0, 'C#: MapEdgeSiteSpec must be an empty record');
  }
  if (building.kind === 'outfall') {
    const spec = value.RadioactiveSludgeOutfallSpec;
    if (check(!!spec, `${building.id}: needs RadioactiveSludgeOutfallSpec`)) {
      check(JSON.stringify(Object.keys(spec).sort()) === JSON.stringify((specFields('RadioactiveSludgeOutfallSpec') ?? []).sort()), `${building.id}: outfall spec fields differ from C#`);
      const c = spec.OutputCoordinates;
      check(c.X >= 0 && c.Y >= 0 && c.Z >= 0 && c.X < size.X && c.Y < size.Y && c.Z < size.Z, `${building.id}: outlet outside the footprint`);
      const release = RADIATION_RECIPES.find(r => r.id === 'ReleaseRadioactiveSludge');
      check(Math.abs(spec.RadioactiveVolumePerCycle - release.ingredients[0][1] * tuning.volumePerGood) < 1e-9, `${building.id}: released radioactive volume must equal consumed goods * ${tuning.volumePerGood}`);
    }
  }
  if (building.kind === 'recovery') {
    const spec = value.RadioactiveSludgeIntakeSpec;
    if (check(!!spec, `${building.id}: needs RadioactiveSludgeIntakeSpec`)) {
      check(JSON.stringify(Object.keys(spec)) === JSON.stringify(specFields('RadioactiveSludgeIntakeSpec')), `${building.id}: intake spec fields differ from C#`);
      const recover = RADIATION_RECIPES.find(r => r.id === 'RecoverRadioactiveSludge');
      check(Math.abs(spec.RadioactiveVolumePerCycle - recover.products[0][1] * tuning.volumePerGood) < 1e-9, `${building.id}: removed radioactive volume must equal produced goods * ${tuning.volumePerGood}`);
      check(spec.MaxWaterPerCycle === RECOVERY_MAX_WATER_PER_CYCLE && spec.MaxWaterPerCycle >= spec.RadioactiveVolumePerCycle, `${building.id}: MaxWaterPerCycle`);
    }
    check(!!value.WaterInputSpec && !!value.WaterInputPipeSpec, `${building.id}: needs the native intake pipe (WaterInputSpec + WaterInputPipeSpec)`);
  }
  check(value.Children?.['#Finished']?.TimbermeshSpec?.Model === `Buildings/Water/${building.id}/${building.id}.IronTeeth.Model`, `${building.id}: must use its late-game study model`);
  check(value.BlockObjectSpec.Blocks.every(b => b.MatterBelow !== 'Air') || building.kind === 'recovery', `${building.id}: no overhang block (MatterBelow Air) outside the recovery pump intake`);
  // The study socket stays first; connection_content.mjs adds the other flat
  // exterior faces (validate_connection_faces.mjs checks those).
  check(JSON.stringify(value.BuildingPipeTargetPortsSpec?.Ports?.[0]) === JSON.stringify(await studyPipePort(building.id, building.pipe)),
    `${building.id}: its study's Timber Pipes socket must be the first port`);
  notes.push(`${building.id}: model ${JSON.stringify(value.Children?.['#Finished']?.TimbermeshSpec?.Model)} and icon ${value.LabeledEntitySpec.Icon}`);
}

// --- Radioactive Spring (dev tool + map editor object)
const mapEditorTemplates = (await readJson(resolve(dataRoot, 'TemplateCollections', 'TemplateCollection.MapEditor.Common.blueprint.json')))
  ?.TemplateCollectionSpec?.['Blueprints#append'] ?? [];
for (const spring of RADIATION_SPRINGS) {
  const value = await readJson(resolve(dataRoot, `${spring.path}.json`));
  if (!value) continue;
  const list = spring.collection === 'buildings' ? templates : mapEditorTemplates;
  check(list.filter(t => t === spring.path).length === 1, `${spring.id}: must appear once in its ${spring.collection} template collection`);
  check(value.TemplateSpec.TemplateName === spring.id, `${spring.id}: TemplateName`);
  check(!value.BuildingSpec, `${spring.id}: must be a source object without BuildingSpec`);
  // One fluid: the spring is a native water source whose water is radioactive.
  check(Math.abs((value.WaterSourceSpec?.DefaultStrength ?? NaN) - SPRING_RADIOACTIVE_PER_HOUR / await waterPerStrengthHour()) < 1e-9, `${spring.id}: native WaterSourceSpec strength must give ${SPRING_RADIOACTIVE_PER_HOUR} radioactive water per hour`);
  check(value.WaterSourceContaminationSpec?.DefaultContamination === 0, `${spring.id}: native WaterSourceContaminationSpec must stay at 0 (b + r <= 1)`);
  check(!value.BadtideWaterSourceContaminationControllerSpec, `${spring.id}: a badtide must not turn the spring's water bad`);
  check(!value.RadioactiveSpringSpec, `${spring.id}: the sludge-era RadioactiveSpringSpec is gone`);
  check(value.PlaceableBlockObjectSpec.DevModeTool === true && value.PlaceableBlockObjectSpec.ToolGroupId === spring.toolGroup, `${spring.id}: dev-mode tool in ${spring.toolGroup}`);
  check(JSON.stringify(value.RadioactiveWaterSourceSpec) === JSON.stringify(SPRING_SPEC), `${spring.id}: RadioactiveWaterSourceSpec`);
  check(JSON.stringify(Object.keys(value.RadioactiveWaterSourceSpec ?? {})) === JSON.stringify(specFields('RadioactiveWaterSourceSpec')), `${spring.id}: spring spec fields differ from C#`);
  check(value.BlockObjectSpec.Flippable === true, `${spring.id}: must stay flippable`);
  check(await exists(resolve(dataRoot, `${spring.icon}.png`)), `${spring.id}: icon missing`);
  for (const key of ['DisplayName', 'Description']) blueprintKeys.push(`Building.${spring.id}.${key}`);
}
check(allCs.includes('[Context("MapEditor")]') && allCs.includes('AddDecorator<RadioactiveWaterSourceSpec, RadioactiveSpringVisual>'), 'Radioactive Spring visual must be bound in Game and MapEditor');
check((csharp['RadiationConfigurator.cs'] ?? '').includes('AddDecorator<RadioactiveWaterSourceSpec, RadioactiveWaterSource>'), 'RadioactiveWaterSource (Game) decorator missing');
check(allCs.includes('AddDecorator<PlantableSpec, IrradiatedPlantWarning>'), 'planting warning decorator missing');

// --- C# runtime contract (one fluid: fresh + bad + radioactive native water).
// Static guards only; outputs/radiation-onefluid/harness runs the shipped
// native water tasks against RadiationMixing.
const methodBody = (file, signature) => {
  const text = csharp[file] ?? '';
  const start = text.indexOf(signature);
  if (start < 0) return null;
  const open = text.indexOf('{', start);
  if (open < 0) return null;
  for (let i = open, depth = 0; i < text.length; i++) {
    if (text[i] === '{') depth++;
    else if (text[i] === '}' && --depth === 0) return text.slice(open + 1, i);
  }
  return null;
};
const simulation = csharp['RadiationSimulation.cs'] ?? '';
const lockstep = csharp['RadiationLockstep.cs'] ?? '';
const service = csharp['IRadiationService.cs'] ?? '';
// Internal/private native access is valid at runtime only because the assembly requests
// SkipVerification (unsafe code); Mono 6.13 otherwise throws Method/FieldAccessException
// (outputs/radiation-mono-access-probe).
const asmdefPath = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'DeepFrontier.asmdef');
const asmdef = await exists(asmdefPath) ? JSON.parse((await readFile(asmdefPath, 'utf8')).replace(/^﻿/, '')) : null;
check(asmdef?.allowUnsafeCode === true, 'DeepFrontier.asmdef must keep "allowUnsafeCode": true (SkipVerification lets Scripts/Radiation use internal water types at runtime)');
// No second fluid.
check(!/\b(AddSludge|RemoveSludge|QueueSludgeRemoval|AddWaterRadiation|ISludgeRemovalReceiver)\b/.test(allCs), 'sludge-era API is back (one fluid: AddRadioactiveWater)');
check(!/OutflowsUpdateTask|WaterParametersUpdateTask|IParallelTickableSingleton|_sludge/.test(simulation), 'RadiationSimulation must not run a second fluid simulation');
check(/void AddRadioactiveWater\(Vector3Int cell, float radioactiveVolume\);/.test(service), 'IRadiationService must expose AddRadioactiveWater');
check((methodBody('RadiationSimulation.cs', 'public void AddRadioactiveWater(') ?? '').includes('_waterService.AddCleanWater('), 'AddRadioactiveWater must use the native water add path');
// Lockstep hooks and chain order (native order: kernels, then sources).
for (const target of ['WaterSimulationTaskStarter), nameof(WaterSimulationTaskStarter.ScheduleSimulationSteps)', 'UpdateWaterSourcesTask), nameof(UpdateWaterSourcesTask.Run)',
  'UpdateWaterChangesTask), nameof(UpdateWaterChangesTask.Run)', 'WaterChangeService), nameof(WaterChangeService.Tick)'])
  check(lockstep.includes(`[HarmonyPatch(typeof(${target})]`), `lockstep patch missing: ${target}`);
check(/BindingFlags\.Instance \| BindingFlags\.Public \| BindingFlags\.NonPublic/.test(lockstep) && !/BindingFlags\.Instance \| BindingFlags\.Public\)/.test(lockstep), 'lockstep reflection must include NonPublic (shipped fields are private)');
const chain = methodBody('RadiationSimulation.cs', 'internal ParallelizerHandle ScheduleLockstepSubstep(') ?? '';
check(/in copy, after\)\s*\.ContinueWith\(in restore\)\s*\.ContinueWith\(in clear\)/.test(chain) && /in harvest\)\s*\.ContinueWith\(in mix\);/.test(chain),
  'lockstep chain must restore pre-source columns before the kernels and mix source water after the harvest');
// The share invariant is checked, never silently clamped.
check(/public const float ShareTolerance = /.test(service), 'RadiationTuning.ShareTolerance missing');
for (const [file, signature] of [['RadiationSimulation.cs', 'internal void HarvestRow('], ['RadiationSimulation.cs', 'internal void MixSourceCells('],
  ['RadiationSimulation.cs', 'internal void MixWaterChanges('], ['RadiationSimulation.cs', 'private void RunInteraction(']])
  check((methodBody(file, signature) ?? '').includes('RadiationMixing.RequireShares('), `${signature} must check b + r <= 1`);
check((methodBody('RadiationSimulation.cs', 'internal void CopyRow(') ?? '').includes('RadiationMixing.EvaporatedVolume('), 'evaporated radioactive volume must go into the soil');
// Saves.
check(/private const int SaveVersion = 3;/.test(simulation) && /private const int SludgeSaveVersion = 2;/.test(simulation), 'radiation SaveVersion 3 with explicit version-2 conversion');
check(/state\.Version == SludgeSaveVersion/.test(methodBody('RadiationSimulation.cs', 'private void ApplyLoaded(') ?? ''), 'version-2 sludge must be converted on load');
const saveBody = methodBody('RadiationSimulation.cs', 'public void Save(ISingletonSaver singletonSaver)') ?? '';
const writeCurrent = methodBody('RadiationSimulation.cs', 'private void WriteCurrent(ISingletonSaver singletonSaver)') ?? '';
check(writeCurrent.indexOf('SyncGeometry(') >= 0 && writeCurrent.indexOf('SyncGeometry(') < writeCurrent.indexOf('saver.Set(CellsKey'), 'a normal save must mirror post-forced-finish geometry before writing cells');
// Native exception save (GameSceneExceptionStateSaver: TickOnlyArrayService.ForceAllowAccess, then
// GameSaver.SaveWithoutFinishingTick) can arrive mid-tick: it writes the last completed tick and never throws;
// normal saves (GameSaver finishes the tick first) keep the strict guard.
{
  const iException = saveBody.indexOf('if (exceptionSave && (midTick || _inTick)) { WriteSnapshot(singletonSaver); return; }');
  const iStrict = saveBody.indexOf('if (midTick)\n        throw new InvalidOperationException("Radiation can only be saved between parallel ticks');
  check(/bool exceptionSave = _tickOnlyArrays\._forceAllowAccess;/.test(saveBody) && iException >= 0 && iStrict > iException
    && /try \{ WriteCurrent\(singletonSaver\); \} catch \(Exception e\) \{[\s\S]*?WriteSnapshot\(singletonSaver\);/.test(saveBody),
    'Save: the exception saver gets the snapshot mid-tick (or the snapshot if the current state fails); normal mid-tick saves still throw');
  check(!/throw /.test(methodBody('RadiationSimulation.cs', 'private void WriteSnapshot(ISingletonSaver singletonSaver)') ?? 'throw ')
    && /saver\.Set\(SnapshotKey, true\);/.test(methodBody('RadiationSimulation.cs', 'private void WriteSnapshot(ISingletonSaver singletonSaver)') ?? ''),
    'WriteSnapshot must never throw and must mark the save as a last-completed-tick snapshot');
  const tickBody2 = methodBody('RadiationSimulation.cs', 'public void Tick()') ?? '';
  check(/^\s*_inTick = true;/.test(tickBody2) && /if \(envelope\.Empty\) \{ TakeSnapshot\(\); return; \}/.test(tickBody2) && /TakeSnapshot\(\);\s*$/.test(tickBody2)
    && /_inTick = false;/.test(methodBody('RadiationSimulation.cs', 'private void TakeSnapshot()') ?? ''), 'every completed Tick must end with TakeSnapshot (which clears _inTick)');
  check(/TakeSnapshot\(\);/.test(methodBody('RadiationSimulation.cs', 'public void UpdateSingleton()') ?? ''), 'an applied save is the snapshot until the first tick');
  check(/Snapshot = loader\.Has\(SnapshotKey\) && loader\.Get\(SnapshotKey\)/.test(simulation)
    && /if \(state\.Snapshot\) \{ droppedCells\+\+; continue; \}/.test(methodBody('RadiationSimulation.cs', 'private void ApplyLoaded(') ?? '')
    && /if \(state\.Snapshot && bad \+ _radiation\[idx\] > 1f\)/.test(methodBody('RadiationSimulation.cs', 'private void ApplyLoaded(') ?? ''),
    'loading a snapshot exception save drops cells whose geometry changed and caps r at 1 - b; other saves stay strict');
  check(/GetField\("_forceAllowAccess"/.test(methodBody('RadiationSimulation.cs', 'public void Load()') ?? ''), 'the native exception-save marker must be verified at load, not mid-crash');
}
const loadBody = methodBody('RadiationSimulation.cs', 'public void Load()') ?? '';
check(/_nextSourceId = _loaded\.NextSourceId/.test(loadBody) && /_sources\.AddRange\(_loaded\.Sources\)/.test(loadBody), 'Load must restore sources and NextSourceId immediately');
check(/ApplyLoaded\(/.test(methodBody('RadiationSimulation.cs', 'public void UpdateSingleton()') ?? ''), 'loaded radiation must be applied before the first tick (UpdateSingleton)');
check(/class RadiationRenderer\b[^{]*IUpdatableSingleton/.test(csharp['RadiationRenderer.cs'] ?? '') && /HasTicked/.test(methodBody('RadiationRenderer.cs', 'public void UpdateSingleton()') ?? ''), 'renderer must draw loaded state before the first tick');
// Geometry: soil moves once. Plants: irradiated ground kills at once (2026-10-22).
const reconcile = methodBody('RadiationSimulation.cs', 'private void Reconcile(') ?? '';
check(!/FindOldContaining\(oldCount, floor\)/.test(reconcile) && /_oldSoilMoved\[/.test(reconcile), 'Reconcile must move each old soil surface to at most one new column');
{
  const radConfig = csharp['RadiationConfigurator.cs'] ?? '';
  const plants = csharp['IrradiatedPlantWarning.cs'] ?? '';
  check(/AddDecorator<NaturalResourceSpec, IrradiatedGroundDeath>/.test(radConfig) && /MultiBind<ISpawnValidator>\(\)\.To<IrradiatedGroundSpawnValidator>\(\)/.test(radConfig)
    && !/RadiationFloraDose/.test(radConfig) && !/class RadiationFloraDose\b/.test(allCs), 'plants: IrradiatedGroundDeath on NaturalResourceSpec and the spawn validator replace the per-plant flora dose');
  check(/public const float IrradiatedGroundThreshold = 0\.05f;/.test(service) && !/FloraThreshold|FloraLethalDose/.test(allCs),
    'one irradiated-ground threshold (0.05) for the tint and plant death; no flora dose tuning');
  check(/private const float MinRenderedSoil = RadiationTuning\.IrradiatedGroundThreshold;/.test(csharp['RadiationShading.cs'] ?? ''), 'the ground tint must start at IrradiatedGroundThreshold (what you see is what kills)');
  const kill = methodBody('RadiationSimulation.cs', 'private void KillOnIrradiatedGround(') ?? '';
  check(/RowRange\.Union\(_soilRows, _irradiatedRows\)/.test(kill) && /SoilAt\(idx\) >= RadiationTuning\.IrradiatedGroundThreshold/.test(kill)
    && /GetBottomObjectComponentAt<LivingNaturalResource>/.test(kill) && /plant\.Die\(\);/.test(kill), 'KillOnIrradiatedGround must kill through native LivingNaturalResource.Die on tracked rows only');
  const tickBody = methodBody('RadiationSimulation.cs', 'public void Tick()') ?? '';
  check(tickBody.indexOf('Rescan(') >= 0 && tickBody.indexOf('KillOnIrradiatedGround();') > tickBody.indexOf('Rescan('), 'plants must be checked every tick after Rescan');
  check(/_irradiatedGround\[j \* _vs \+ i\] = false;/.test(methodBody('RadiationSimulation.cs', 'private void Reconcile(') ?? ''), 'a geometry change must recheck its slots');
  check(!/LivingNaturalResource|FloraDose|Expose\(/.test(methodBody('RadiationSimulation.cs', 'private void HourlySoilPass(') ?? ''), 'the hourly soil pass no longer doses plants');
  check(/class IrradiatedGroundDeath\b[^{]*IPostInitializableEntity[^{]*IPersistentEntity/.test(plants) && /_simulation\.IsIrradiatedGround\(_block\.Coordinates\)\) _living\.Die\(\);/.test(plants)
    && /new ComponentKey\("DeepFrontier\.RadiationFloraDose"\)/.test(plants) && /public void Save\(IEntitySaver entitySaver\) \{ \}/.test(plants),
    'new plants on irradiated ground die in PostInitializeEntity; legacy flora-dose data is read and discarded; nothing is saved');
  check(/if \(_loaded != null\) return false;/.test(methodBody('RadiationSimulation.cs', 'internal bool IsIrradiatedGround(') ?? ''), 'before a save is applied the first tick, not plant initialization, decides');
}
// Soil (RadiationSoil.cs): radioactive water never irrigates, irradiates the
// ground in the native soil-contamination pattern, and washes out of
// submerged ground conservatively. outputs/radiation-soil-harness runs the
// shipped soil kernels and the exchange.
const soilCs = csharp['RadiationSoil.cs'] ?? '';
if (check(soilCs.length > 0, 'RadiationSoil.cs missing')) {
  const soilClass = soilCs.match(/public sealed class RadiationSoil\s*:([^{]*)\{/)?.[1] ?? '';
  for (const iface of ['ILoadableSingleton', 'IPostLoadableSingleton', 'ITickableSingleton', 'IParallelTickableSingleton', 'IUnloadableSingleton'])
    check(soilClass.includes(iface), `RadiationSoil must implement ${iface}`);
  check(!/ISaveableSingleton|PropertyKey<|ListKey<|SingletonKey/.test(soilCs), 'RadiationSoil must not add save data (its level arrays are rebuilt from the water)');
  check(/Bind<RadiationSoil>\(\)\.AsSingleton\(\);/.test(csharp['RadiationConfigurator.cs'] ?? ''), 'RadiationConfigurator must bind RadiationSoil');
  // Moisture: Harmony prefix replaces the moisture tasks' water columns with b + r, editor-excluded.
  const patchStart = soilCs.indexOf('#if !UNITY_EDITOR\n  // Harmony');
  const patchEnd = soilCs.indexOf('#endif', patchStart);
  const patches = patchStart >= 0 && patchEnd > patchStart ? soilCs.slice(patchStart, patchEnd) : '';
  check(/\[HarmonyPatch\(typeof\(SoilMoistureSimulationTaskStarter\), nameof\(SoilMoistureSimulationTaskStarter\.StartTask\)\)\]/.test(patches)
    && /Prefix\(ref ReadOnlyArray<ReadOnlyWaterColumn> waterColumns\)/.test(patches), 'moisture prefix on SoilMoistureSimulationTaskStarter.StartTask(ref waterColumns) missing or outside #if !UNITY_EDITOR');
  check(!/HarmonyPatch|new Harmony\(/.test(soilCs.slice(0, Math.max(0, patchStart)) + soilCs.slice(patchEnd)), 'RadiationSoil Harmony code must stay inside #if !UNITY_EDITOR');
  check(/parameter\.ParameterType == typeof\(ReadOnlyArray<ReadOnlyWaterColumn>\)\.MakeByRefType\(\)/.test(patches) && /Verify\(\);\s*new Harmony\(HarmonyId\)/.test(patches),
    'moisture patch target must be verified before patching');
  const moisture = methodBody('RadiationSoil.cs', 'private void BuildMoistureShadow(') ?? '';
  check(/RadiationMixing\.RequireShares\(column\.Contamination, r,/.test(moisture) && /column\.Contamination \+= r;/.test(moisture) && /native\.CopyTo\(_moistureWater\)/.test(moisture),
    'moisture shadow must be the thread-safe columns with Contamination = b + r (checked <= 1)');
  check(/waterColumns\.AsSpan != _waterMap\.WaterColumns\.AsSpan/.test(methodBody('RadiationSoil.cs', 'internal void SubstituteMoistureColumns(') ?? ''),
    'moisture substitution must only replace the thread-safe water map');
  // Field: shipped native kernels with native per-tick parameters, on a shadow whose (c - min) x scaler = T(r).
  const schedule = methodBody('RadiationSoil.cs', 'public void StartParallelTick()') ?? '';
  check(/new ContaminationCandidatesCountingTask\(/.test(schedule) && /new ContaminationsUpdateTask\(/.test(schedule)
    && /in prepare\)\s*\.ContinueWith\(rows\.Lo, rows\.Hi \+ 1, 1, in candidates\)\s*\.ContinueWith\(rows\.Lo, rows\.Hi \+ 1, 5, in update\);/.test(schedule),
    'soil field must run the native candidate then update kernels in native order');
  const postLoad = methodBody('RadiationSoil.cs', 'public void PostLoad()') ?? '';
  for (const field of ['_regularSpreadCost', '_diagonalSpreadCost', '_contaminationDecayRate', '_contaminationSpreadingRate', '_minimumWaterContamination',
    '_contaminationScaler', '_verticalCostModifier', '_contaminationThreshold', '_contaminationPositiveEqualizationRate', '_contaminationNegativeEqualizationRate'])
    check(postLoad.includes(`s.${field}`), `soil field must take ${field} from the native SoilContaminationSimulationTaskStarter`);
  check(/RadiationSoilNative\.Verify\(\);/.test(postLoad), 'RadiationSoil.PostLoad must verify the native members first');
  check(/minimumWaterContamination \+ Mathf\.Min\(1f, r \* RadiationTuning\.WaterToSoilFactor\) \/ contaminationScaler/.test(soilCs),
    'kernel contamination must map r to the existing soil target min(1, WaterToSoilFactor x r)');
  const shadow = methodBody('RadiationSoil.cs', 'private void BuildSoilShadow(') ?? '';
  check(/column\.Contamination = 0f;/.test(shadow), 'soil field shadow must not see badwater (Contamination 0 where r = 0)');
  const nativeSoil = (await readJson(resolve(vanillaRoot, 'Configurations', 'SoilContaminationSimulator.blueprint.json')))?.SoilContaminationSimulatorSpec;
  const rangeMargin = Number(service.match(/public const int RangeMargin = (\d+);/)?.[1]);
  const syncMargin = Number(service.match(/public const int GeometrySyncMargin = (\d+);/)?.[1]);
  check(/internal const int FieldRowMargin = RadiationTuning\.GeometrySyncMargin;/.test(soilCs) && rangeMargin + syncMargin >= (nativeSoil?.MaxRangeFromSource ?? Infinity) + 1,
    `field rows (RangeMargin ${rangeMargin} + FieldRowMargin ${syncMargin}) must cover the native reach MaxRangeFromSource ${nativeSoil?.MaxRangeFromSource} + 1`);
  const nativeMoisture = (await readJson(resolve(vanillaRoot, 'Configurations', 'SoilMoistureSimulator.blueprint.json')))?.SoilMoistureSimulatorSpec;
  if (nativeSoil && nativeMoisture) {
    const reach = T => { let d = 0; while (T - d / nativeSoil.MaxRangeFromSource >= nativeSoil.ContaminationThreshold) d++; return d; };
    notes.push(`soil field (native rules): T = min(1, 4r) at the bank, -1/${nativeSoil.MaxRangeFromSource} per tile, -${nativeSoil.VerticalSpreadCostMultiplier}/${nativeSoil.MaxRangeFromSource} per level uphill; reach r>=0.25: ${reach(1)} tiles, r=0.1: ${reach(0.4)}, tide r=0.01: ${reach(0.04)}; nothing below DetectionLimit 0.005`);
    notes.push(`moisture (native rules on b + r): full range below ${nativeMoisture.MinimumWaterContamination}, none from ${nativeMoisture.MaximumWaterContamination}`);
  }
  // Exchange: rinse under clean water at the native recovery rate; conserved
  // exchange under radioactive water; dry ground only decays.
  const exchange = methodBody('RadiationSoil.cs', 'internal void Exchange(') ?? '';
  check(/ share = r - delta \* VolumePerSoil \/ depth;/.test(exchange) && /soil\[idx\] = s \+ delta;/.test(exchange) && /radiation\[idx\] = share;/.test(exchange)
    && /RadiationMixing\.RequireShares\(bad, share, "the soil washout"\)/.test(exchange), 'soil exchange must conserve radioactive volume and keep b + r <= 1');
  check(/if \(!\(column\.WaterDepth > 0f\)\) continue;/.test(exchange) && /if \(RadiationTuning\.Detected\(r\) == 0f\) \{[\s\S]*?delta = Rinse\(s, r, bad, depth, wash, out share\);/.test(exchange),
    'any wet column (no depth threshold) rinses when its share reads 0; dry ground is untouched');
  check(!/_levels\[/.test(exchange), 'the native-pattern level must not be written into the persistent soil (it is the bank layer)');
  check(/simulation\.VisibleRows/.test(exchange), 'washout must reach soil rows without radioactive water');
  check(/_washoutPerHour = _negativeRate \/ _dayNightCycle\.FixedDeltaTimeInHours;/.test(soilCs) && /wash = _washoutPerHour \* hours;/.test(exchange) && !/SoilWashoutPerHour/.test(soilCs),
    'washout must be the native negative equalization rate per tick, converted to game hours');
  check(/internal const float VolumePerSoil = 1f \/ RadiationTuning\.SoilPerDepositedVolume;/.test(soilCs), 'VolumePerSoil = 1 / SoilPerDepositedVolume (the evaporation deposit rule)');
  const rinse = methodBody('RadiationSoil.cs', 'internal static float Rinse(') ?? '';
  check(/internal const float RinseShareCap = 0\.5f \* RadiationTuning\.DetectionLimit;/.test(soilCs) && /float washed = Mathf\.Min\(s, maxWash\);/.test(rinse)
    && /Mathf\.Min\(RinseShareCap - r, 1f - b - r\)/.test(rinse), 'rinsing removes min(soil, native rate) and leaves rinse water below the detection limit and b + r <= 1');
  // Banks: the native level is a transient layer read as max(soil, bank).
  check(/internal float SoilAt\(int idx\) => Mathf\.Max\(_soil\[idx\], _soilExchange\.BankAt\(idx\)\);/.test(simulation)
    && /CellIsUnderwater\(cell\), SoilAt\(idx\)\)/.test(simulation) && /SoilAt\(idx\) >= RadiationTuning\.IrradiatedGroundThreshold/.test(methodBody('RadiationSimulation.cs', 'private void KillOnIrradiatedGround(') ?? '')
    && /_soilExchange\.BankAt\(idx\) > 0f\) soilValues\.Include\(y\)/.test(methodBody('RadiationSimulation.cs', 'private void Rescan(') ?? ''),
    'Sample, plant death and the soil rows must see max(soil, bank)');
  check(/_bankRows\)/.test(methodBody('RadiationSoil.cs', 'internal void Prepare(') ?? ''), 'the kernels must keep running on rows whose banks are still clearing');
  // Irradiated-ground tint: decreases reach the GPU and cells return to native.
  if (csharp['RadiationShading.cs']) {
    const soilUpdate = (csharp['RadiationShading.cs'].match(/class IrradiatedSoilSurface[\s\S]*$/)?.[0] ?? '');
    const update = soilUpdate.slice(soilUpdate.indexOf('internal void Update(RadiationSimulation simulation)'));
    check(/Encode\(simulation\.SoilAt\(idx\)\)/.test(update), 'the soil tint must draw max(soil, bank) (RadiationSimulation.SoilAt)');
    check(/RowRange\.Union\(simulation\.VisibleRows, _rowsWithData\)/.test(update) && /if \(!any && !_hasData\[p\]\) continue;/.test(update)
      && /else if \(g != target\) \{ nr = g; ng = target; \}/.test(update) && /else if \(r != g\) nr = g;/.test(update)
      && /_dirty\[z\] = true;/.test(update) && /_hasData\[p\] = cellData;/.test(update) && /_rowsWithData = withData;/.test(update)
      && update.indexOf('_rowsWithData = withData;') < update.indexOf('RadiationShading.UploadLayer('),
      'soil tint: rows keep updating while a cell holds data, a drop moves G to R then settles R = G, every change marks its layer dirty and is uploaded in the same update');
    check(/_soil\.Pending/.test(csharp['RadiationRenderer.cs'] ?? ''), 'the renderer must keep settling while soil pixels are non-zero, even when the simulation state is unchanged');
  }
  const sww = methodBody('RadiationSoil.cs', 'internal static float SoilWaterExchange(') ?? '';
  check(/\(r \* F - s\) \/ \(1f \+ F \* a\)/.test(sww) && /\(s - r \* F\) \/ \(1f \+ F \* a\)/.test(sww) && /\(1f - b - r\) \/ a/.test(sww), 'exchange must stop at the equilibrium and the b + r <= 1 headroom');
  // RadiationSimulation hands the late tick over: decay, exchange, rescan, then shadows.
  const tick = methodBody('RadiationSimulation.cs', 'public void Tick()') ?? '';
  const order = ['RunInteraction(', '_soilExchange.Exchange(', 'Rescan(', '_soilExchange.Prepare('].map(s => tick.indexOf(s));
  check(order.every(i => i >= 0) && order.every((v, k) => k === 0 || v > order[k - 1]), 'RadiationSimulation.Tick must run RunInteraction, Exchange, Rescan, Prepare in that order');
  check(!/SoilRiseFromWaterPerHour|_soil\[/.test(methodBody('RadiationSimulation.cs', 'private void RunInteraction(') ?? ''), 'RunInteraction must leave the soil to RadiationSoil.Exchange (one rise per tick)');
}

// Native surfaces (RadiationShading.cs, RadiationRenderer.cs,
// tools/native_shader_variants.mjs): radioactive water and irradiated ground
// are drawn by the native water and terrain materials through bundled variants
// of their native shader graphs. No overlay meshes.
{
  const renderer = csharp['RadiationRenderer.cs'] ?? '';
  const shading = csharp['RadiationShading.cs'] ?? '';
  const materials = csharp['RadiationMaterials.cs'] ?? '';
  for (const [file, text] of Object.entries(csharp))
    check(!/new Mesh\b|MeshFilter|AddComponent<MeshRenderer>|SetTriangles\(|Sprites\/Default/.test(text), `${file}: radiation must not draw overlay meshes (the native surfaces draw it)`);
  check(!/WaterTint\b|_waterTint|WaterTintShader|public Material Soil\b/.test(materials), 'RadiationMaterials must not create the overlay water tint or ground material');
  // Variants: current, under AssetBundles/Resources, named as the C# expects.
  const variants = await buildVariants().catch(error => { fail(`shader variants: ${error.message}`); return []; });
  check(variants.length === 3, 'expected the opaque water, transparent water and terrain variants');
  const resources = resolve(root, 'src', 'DeepFrontier', 'AssetBundles', 'Resources');
  for (const {variant, path, text} of variants) {
    check(await readFile(path, 'utf8').catch(() => null) === text, `${variant.name}.shadergraph is missing or stale (run node tools/native_shader_variants.mjs)`);
    check(path.startsWith(resources + '\\') || path.startsWith(resources + '/'), `${variant.name} must sit under AssetBundles/Resources (bundled by the Mod Builder)`);
    check(shading.includes(`"Shaders/${SHADER_PATH}/${variant.name}"`) && shading.includes(`"${SHADER_PATH}/${variant.name}"`), `RadiationShading must load Shaders/${SHADER_PATH}/${variant.name} and expect shader ${SHADER_PATH}/${variant.name}`);
    check(shading.includes(`"Shader Graphs/${variant.native}"`), `RadiationShading must require the native shader Shader Graphs/${variant.native}`);
    const list = shading.match(new RegExp(`${variant.kind === 'water' ? 'Water' : 'Terrain'}CompiledKeywords = \\{([^}]*)\\}`))?.[1] ?? '';
    check(JSON.stringify([...list.matchAll(/"([^"]+)"/g)].map(m => m[1])) === JSON.stringify(variant.multiCompile), `${variant.name}: RadiationShading compiled keywords must equal the generator's multi_compile list`);
  }
  for (const name of [WATER.keyword, WATER.oldMap, WATER.newMap, ...Object.values(WATER.colors), SOIL.keyword, SOIL.map, SOIL.color])
    check(shading.includes(`"${name}"`), `RadiationShading must use the variant name ${name}`);
  // The official Mod Builder bundles every AssetBundles file except .unity, .cs and .meta; staging copies AssetBundles.
  const builder = await readFile(resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'Editor', 'Scripts', 'ModBuilding', 'AssetBundleBuilder.cs'), 'utf8').catch(() => '');
  check(/InvalidAssetBundleExtensions = \{ "\.unity", "\.cs", "\.meta" \}/.test(builder), 'AssetBundleBuilder.InvalidAssetBundleExtensions changed: check that .shadergraph files are still bundled');
  const stage = await readFile(resolve(root, 'tools', 'stage_deep_frontier.ps1'), 'utf8').catch(() => '');
  check(/foreach \(\$entry in @\('manifest\.json', 'Data', 'Scripts', 'Editor', 'AssetBundles'\)\)/.test(stage), 'stage_deep_frontier.ps1 must stage AssetBundles');
  // Native terrain materials: MaterialCollection.Common, by repository name.
  const common = (await readJson(resolve(vanillaRoot, 'MaterialCollections', 'MaterialCollection.Common.blueprint.json')))?.MaterialCollectionSpec?.Materials ?? [];
  const terrain = [...(shading.match(/TerrainMaterials = \{([^}]*)\}/)?.[1] ?? '').matchAll(/"([^"]+)"/g)].map(m => m[1]);
  check(terrain.length === 5, 'RadiationShading.TerrainMaterials must list the five native TerrainURP materials');
  for (const name of terrain) check(common.filter(path => path.split('/').pop() === name).length === 1, `${name} must be one native MaterialCollection.Common material`);
  const waterMesh = (await readJson(resolve(vanillaRoot, 'Configurations', 'WaterMesh.blueprint.json')))?.WaterMeshSpec;
  check(waterMesh?.OpaqueMaterial === 'Environment/Water/Materials/PhysicalWater_Opaque' && waterMesh?.TransparentMaterial === 'Environment/Water/Materials/PhysicalWater_Transparent',
    'native WaterMeshSpec materials changed');
  // Verify coverage: every native member the variants mirror or the renderer reads, checked before any shader swap.
  const verify = methodBody('RadiationShading.cs', 'internal static void Verify()') ?? '';
  for (const member of ['nameof(WaterMeshSpec.OpaqueMaterial)', 'nameof(WaterMeshSpec.TransparentMaterial)', 'typeof(AssetRef<Material>)',
    'RequireField(typeof(WaterRenderer), "_contaminations", typeof(DataTextureArray<byte>))',
    'RequireField(typeof(UpdateWaterTexturesTask), "_contaminations", typeof(DataTextureArray<byte>))',
    'RequireField(typeof(UpdateWaterTexturesTask), "_waterColumns", typeof(ReadOnlyArray<ReadOnlyWaterColumn>))',
    'WaterTextureNames.OldContaminations == "_OldContaminations"', 'WaterTextureNames.NewContaminations == "_NewContaminations"',
    'RequireField(typeof(TerrainMaterialMap), "_contaminationMapTexture", typeof(Texture2DArray))',
    'RequireField(typeof(TerrainMaterialMap), "_contaminations", typeof(PixelData[][]))', 'nameof(TerrainMaterialMap.SetSoilContamination)',
    'Marshal.SizeOf(typeof(PixelData)) == 2', 'throw new InvalidOperationException('])
    check(verify.includes(member), `RadiationShading.Verify must check ${member}`);
  check(/public void Load\(\) => RadiationShading\.Verify\(\);/.test(renderer) && /class RadiationRenderer\b[^{]*IPostLoadableSingleton/.test(renderer),
    'RadiationRenderer must verify on Load and swap shaders in PostLoad');
  const unload = methodBody('RadiationRenderer.cs', 'public void Unload()') ?? '';
  check(/_water\?\.Unload\(\);/.test(unload) && /_soil\?\.Unload\(\);/.test(unload), 'RadiationRenderer.Unload must restore the native shaders');
  for (const surface of ['RadioactiveWaterSurface', 'IrradiatedSoilSurface']) {
    const body = shading.slice(shading.indexOf(`internal sealed class ${surface}`));
    check(/internal void Unload\(\) \{\s*RadiationShading\.SetKeyword\([^)]*, false\);\s*foreach \(var swap in _swaps\) swap\.Restore\(\);/.test(body), `${surface}.Unload must clear its keyword and restore the native shaders`);
    check(/if \(!_dirty\[[jz]\]\) continue;/.test(body) && /RadiationShading\.UploadLayer\(/.test(body), `${surface} must upload only changed layers`);
  }
  const swap = shading.slice(shading.indexOf('internal sealed class ShaderSwap'), shading.indexOf('internal static void UploadLayer('));
  for (const [pattern, what] of [[/_native\.name != nativeShader/, 'the native shader name'], [/variant\.FindPropertyIndex\(name\)/, 'every native property on the variant'],
    [/GetPropertyType\(index\) != _native\.GetPropertyType\(i\)/, 'native property types'], [/material\.enabledKeywords/, 'the native material keywords'],
    [/Array\.IndexOf\(compiledKeywords, _keywords\[i\]\) < 0/, 'that enabled keywords are compiled for every combination'], [/variant\.isSupported/, 'GPU support']])
    check(pattern.test(swap), `ShaderSwap must check ${what}`);
  check(/Graphics\.CopyTexture\(buffer, 0, 0, array, layer, 0\)/.test(shading), 'layers upload through the native buffer + Graphics.CopyTexture path');
  check(/simulation\.VisibleRows, _rowsWithData/.test(shading), 'surfaces must update the radiation rows plus rows still settling');
  check(/Refresh\(settle: false\)/.test(methodBody('RadiationRenderer.cs', 'public void UpdateSingleton()') ?? ''), 'before the first tick the renderer must draw only new simulation states');
  check(/weight = visibility \* radiation \/ \(contamination \+ radiation\)/.test(shading), 'radioactive water must mix with badwater by share');
}

// The one threshold (2026-10-22: "if it is below 0.5 percent then it is gone").
check(/public const float DetectionLimit = 0\.005f;/.test(service) && /public static float Detected\(float share\) => share >= DetectionLimit \? share : 0f;/.test(service),
  'RadiationTuning.DetectionLimit must be 0.005f with Detected() reading smaller shares as 0');
{
  const sensorsDir = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'Sensors');
  const tideDir = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'RadioactiveTide');
  const others = {};
  for (const dir of [sensorsDir, tideDir]) if (await exists(dir))
    for (const file of await readdir(dir)) if (file.endsWith('.cs')) others[`${dir}/${file}`] = await readFile(join(dir, file), 'utf8');
  const stray = [];
  for (const [file, text] of [...Object.entries(csharp), ...Object.entries(others)])
    text.split(/\r?\n/).forEach((line, n) => {
      // MinSoilRadiation is a soil level (0..1), not a water share.
      if (/\b(1e-4f?|5e-5f?|0\.0001f?|0\.00005f?)\b/.test(line) && !/public const float MinSoilRadiation = 1e-4f;/.test(line)) stray.push(`${file}:${n + 1}`);
    });
  check(stray.length === 0, `stray water-share thresholds (use RadiationTuning.DetectionLimit): ${stray.join(', ')}`);
  check(!/DetectionClearLimit/.test(allCs + Object.values(others).join('\n')), 'no second (resume) threshold: pumps resume once the share reads 0');
}
check(/SetBlocked\(radiation >= RadiationTuning\.DetectionLimit\);/.test(methodBody('RadiationIntakeGuard.cs', 'private void Evaluate()') ?? ''), 'pumps must refuse at DetectionLimit and resume below it (no hysteresis)');
check(/RadiationTuning\.Detected\(_radiation\[idx\]\)/.test(methodBody('RadiationSimulation.cs', 'internal float ColumnRadiation(') ?? '')
  && /RadiationTuning\.Detected\(_radiation\[idx\]\)/.test(methodBody('RadiationSimulation.cs', 'public RadiationSample Sample(') ?? ''),
  'Sample and ColumnRadiation must report shares below DetectionLimit as 0');
check(/radiation < RadiationTuning\.DetectionLimit && !\(radiation > _radPrevious\[idx\]\)\) radiation = 0f;/.test(methodBody('RadiationSimulation.cs', 'private void Rescan(') ?? ''),
  'Rescan must remove a final share below DetectionLimit once it stops growing');
check((methodBody('RadiationSimulation.cs', 'private void ApplyLoaded(') ?? '').split('RadiationTuning.Detected(').length >= 3, 'loaded shares below DetectionLimit must be zeroed (versions 2 and 3)');
check(/RadiationTuning\.Detected\(radiation\[idx\]\)/.test(methodBody('RadiationSoil.cs', 'private void BuildMoistureShadow(') ?? '')
  && /RadiationTuning\.Detected\(radiation\[idx\]\)/.test(methodBody('RadiationSoil.cs', 'private void BuildSoilShadow(') ?? '')
  && /RadiationTuning\.Detected\(r\) \* F/.test(methodBody('RadiationSoil.cs', 'internal static float SoilWaterExchange(') ?? ''),
  'moisture, the bank field and the soil target must ignore shares below DetectionLimit');
if (csharp['RadiationShading.cs']) check(/RadiationTuning\.DetectionLimit/.test(csharp['RadiationShading.cs']), 'water tint visibility must start at RadiationTuning.DetectionLimit');

// Buildings and beavers.
const buildings = csharp['RadiationBuildings.cs'] ?? '';
check(/_intake\.DemandCleanWaterAmount\(/.test(buildings) && /class RadioactiveSludgeIntake\b[^{]*IPersistentEntity[^{]*IDeletableEntity/.test(buildings), 'recovery pump must pump through the native WaterInput and keep a saved buffer');
check(/_radiation\.AddRadioactiveWater\(Outlet,/.test(buildings), 'outfall must release radioactive water');
check(/public const float ExposurePerWaterRadiationPerHour = 60f;/.test(service), 'wading in r = 1 water must dose 60/h, as sludge did');
const processBody = methodBody('RadiationStorage.cs', 'private void Process(Stockpile stockpile)') ?? '';
const conversionBlock = processBody.indexOf('if (holdsWater && (');
const conversionEnd = conversionBlock < 0 ? -1 : (() => {
  const open = processBody.indexOf('{', conversionBlock);
  for (let i = open, depth = 0; i < processBody.length; i++) {
    if (processBody[i] === '{') depth++;
    else if (processBody[i] === '}' && --depth === 0) return i;
  }
  return -1;
})();
check(conversionEnd > 0 && processBody.indexOf('allower.Allow(') > conversionEnd, 'tank allower switch must run on every pass, outside the conversion branch');
const exposure = csharp['RadiationExposure.cs'] ?? '';
check(/class RadiationExposure\b[^{]*IChildhoodInfluenced/.test(exposure) && /_untreatedHours = childExposure\._untreatedHours/.test(exposure) && /_dose = childExposure\._dose/.test(exposure), 'RadiationExposure must carry dose and untreated time from kit to adult');

// --- C# decorators and localization
const configurator = csharp['RadiationConfigurator.cs'] ?? '';
for (const decorator of ['AddDecorator<WaterInput, RadiationIntakeGuard>', 'AddDecorator<BeaverSpec, RadiationExposure>',
  'AddDecorator<Stockpile, IrradiatedStorageStatus>', 'AddDecorator<RadioactiveSludgeOutfallSpec, RadioactiveSludgeOutfall>',
  'AddDecorator<RadioactiveSludgeIntakeSpec, RadioactiveSludgeIntake>', 'MultiBind<IBlockObjectValidator>().ToExisting<MapEdgeSiteValidator>'])
  check(configurator.includes(decorator), `RadiationConfigurator is missing ${decorator}`);
check(/\[Context\("Game"\)\]/.test(configurator), 'RadiationConfigurator must be a [Context("Game")] configurator');
const csv = (await exists(resolve(dataRoot, 'Localizations', 'enUS.csv'))) ? await readFile(resolve(dataRoot, 'Localizations', 'enUS.csv'), 'utf8') : '';
const locIds = new Set(csv.split(/\r?\n/).map(line => line.split(',')[0]));
const locBlock = allCs.match(/class RadiationLoc \{([\s\S]*?)\n  \}/)?.[1] ?? '';
const locKeys = [...locBlock.matchAll(/= "([^"]+)"/g)].map(m => m[1]);
check(locKeys.length >= 7, 'RadiationLoc keys not found');
blueprintKeys.push(`Need.${NEED}.DisplayName`, `Status.Need.${NEED}`, `Status.Need.${NEED}.Short`,
  ...[SLUDGE, CONTAMINATED_WATER].flatMap(id => [`Good.${id}.DisplayName`, `Good.${id}.PluralDisplayName`]),
  ...RADIATION_BUILDINGS.flatMap(b => ['DisplayName', 'Description', 'FlavorDescription'].map(k => `Building.${b.id}.${k}`)));
for (const key of [...locKeys, ...blueprintKeys]) check(locIds.has(key), `enUS.csv is missing ${key}`);
const sprites = allCs.match(/class RadiationSprites \{([\s\S]*?)\n  \}/)?.[1] ?? '';
notes.push(`placeholder building status sprites: ${[...new Set([...sprites.matchAll(/= "([^"]+)"/g)].map(m => m[1]))].join(', ')}`);

// --- Radioactive zombie (the irradiated beaver; C#: RadioactiveZombie.cs, RadioactiveZombieTint.cs)
const csvText = id => {
  for (const line of csv.split(/\r?\n/)) {
    if (!line.startsWith(`${id},`)) continue;
    const rest = line.slice(id.length + 1);
    if (!rest.startsWith('"')) return rest.split(',')[0];
    let text = '';
    for (let i = 1; i < rest.length; i++) {
      if (rest[i] === '"' && rest[i + 1] === '"') { text += '"'; i++; } else if (rest[i] === '"') return text; else text += rest[i];
    }
  }
  return undefined;
};
const zombie = csharp['RadioactiveZombie.cs'] ?? '';
const zombieTint = csharp['RadioactiveZombieTint.cs'] ?? '';
const zombieNeedSpec = async id => (await exists(resolve(dataRoot, 'Needs', `Need.Beaver.${id}.blueprint.json`)))
  ? await readJson(resolve(dataRoot, 'Needs', `Need.Beaver.${id}.blueprint.json`))
  : await readJson(resolve(vanillaRoot, 'Needs', `Need.Beaver.${id}.blueprint.json`));
// Speed: strictly slower than a native badwater-contaminated beaver. The
// MovementSpeed bonus is 1 + sum of deltas, clamped to the bonus type's range
// (native BonusManager), so compare across every shared bonus.
const vanillaContamination = await readJson(resolve(vanillaRoot, 'Needs', 'Need.Beaver.BadwaterContamination.blueprint.json'));
const movementType = (await readJson(resolve(vanillaRoot, 'BonusTypes', 'BonusType.MovementSpeed.blueprint.json')))?.BonusTypeSpec;
const contaminatedDelta = vanillaContamination?.PunitiveNeedSpec?.Penalties?.find(p => p.Id === 'MovementSpeed')?.MultiplierDelta;
const zombieDelta = need?.PunitiveNeedSpec?.Penalties?.find(p => p.Id === 'MovementSpeed')?.MultiplierDelta;
check(need?.PunitiveNeedSpec?.Penalties?.length === 1 && zombieDelta === ZOMBIE_MOVEMENT_DELTA, `Irradiation need must carry exactly MovementSpeed ${ZOMBIE_MOVEMENT_DELTA}`);
if (check(typeof contaminatedDelta === 'number' && movementType, 'vanilla BadwaterContamination MovementSpeed penalty / MovementSpeed bonus type not found')) {
  const speed = (delta, shared) => Math.min(movementType.MaximumValue, Math.max(movementType.MinimumValue, 1 + shared + delta));
  check(speed(zombieDelta, 0) < speed(contaminatedDelta, 0), `zombie speed x${speed(zombieDelta, 0)} must be below contaminated x${speed(contaminatedDelta, 0)}`);
  const faster = [];
  for (let step = -20; step <= 20; step++) {
    const shared = step / 20, z = speed(zombieDelta, shared), c = speed(contaminatedDelta, shared);
    if (!(z < c || (z === movementType.MinimumValue && c === movementType.MinimumValue))) faster.push(shared.toFixed(2));
  }
  check(faster.length === 0, `zombie not slower than a contaminated beaver at shared MovementSpeed bonus ${faster.join(', ')}`);
  notes.push(`movement: contaminated x${speed(contaminatedDelta, 0).toFixed(2)} (vanilla ${contaminatedDelta}), zombie x${speed(zombieDelta, 0).toFixed(2)} (${zombieDelta}, native floor ${movementType.MinimumValue})`);
}
check(need?.NeedSpec?.DisplayNameLocKey === `Need.${NEED}.DisplayName` && csvText(`Need.${NEED}.DisplayName`) === ZOMBIE_NAME, `Irradiation need must display as "${ZOMBIE_NAME}"`);
check(csvText(`Status.Need.${NEED}.Short`) === ZOMBIE_NAME, `Irradiation status short text must be "${ZOMBIE_NAME}"`);
check(need?.CriticalNeedSpec?.CriticalNeedType === 'Alert', 'the zombie status must be a native critical-need alert');
// Twice the hunger and thirst: a native ContinuousEffect of 2 x DailyDelta per
// tick, which replaces the native decay of that update (Need.Update skips decay
// after Need.Apply), divided by Effectiveness (Need.Apply multiplies by it).
check(/public const float ZombieNeedDecayMultiplier = 2f;/.test(service), 'RadiationTuning.ZombieNeedDecayMultiplier must be 2f');
check(constant('HungerNeedId') === 'Hunger' && constant('ThirstNeedId') === 'Thirst', 'zombie need ids must be Hunger and Thirst');
check(zombie.includes('new ContinuousEffect(needId, RadiationTuning.ZombieNeedDecayMultiplier * spec.DailyDelta / 24f / spec.Effectiveness)'), 'zombie decay must be ZombieNeedDecayMultiplier x DailyDelta / Effectiveness as a native ContinuousEffect');
check(/_needs\.ApplyEffect\(_hungerDecay, hours\);/.test(zombie) && /_needs\.ApplyEffect\(_thirstDecay, hours\);/.test(zombie), 'zombie must apply the Hunger and Thirst decay every tick');
check(/float hours = _dayNightCycle\.FixedDeltaTimeInHours;/.test(methodBody('RadioactiveZombie.cs', 'public override void Tick()') ?? ''), 'zombie decay must use the native fixed tick length (the one NeedManager decays with)');
for (const id of ['Hunger', 'Thirst']) {
  const spec = (await zombieNeedSpec(id))?.NeedSpec;
  if (!check(spec && spec.DailyDelta < 0 && spec.Effectiveness > 0 && spec.Wastable === false, `${id}: native need must decay with positive Effectiveness`)) continue;
  const days = (spec.StartingValue - spec.MinimumValue) / -spec.DailyDelta;
  notes.push(`${id}: full to lethal minimum in ${days.toFixed(2)} days natively, ${(days / 2).toFixed(2)} days as a zombie`);
}
// The extra decay cannot see native need suspension (Need.DisableUpdate has no
// public getter), so no building may suspend Hunger or Thirst.
for (const base of [resolve(vanillaRoot, 'Buildings'), resolve(dataRoot, 'Buildings')]) {
  for (const file of await walk(base)) {
    const text = await readFile(file, 'utf8');
    if (!text.includes('EntererNeedSuspendingBuildingSpec')) continue;
    const ids = JSON.parse(text.replace(/^﻿/, '')).EntererNeedSuspendingBuildingSpec?.NeedSuspender?.SuspendableNeedIds ?? [];
    check(!ids.includes('Hunger') && !ids.includes('Thirst'), `${file}: suspends Hunger/Thirst, which the zombie's doubled decay would ignore`);
  }
}
// Look: native animator parameter and the radiation tint yellow.
for (const id of ['BeaverAdult', 'BeaverChild']) {
  const controller = (await readJson(resolve(vanillaRoot, 'Characters', 'Beaver', `${id}.blueprint.json`)))?.TimbermeshAnimatorControllerSpec;
  check(controller?.BoolParameters?.includes('Contaminated'), `${id}: native animator lost the Contaminated parameter`);
  check(controller?.AnimatorStates?.some(s => s.SpeedModifier === 'WalkingSpeed' && s.Conditions.some(c => c.ParameterName === 'Contaminated' && c.MustBeTrue)
    && s.Conditions.some(c => c.ParameterName === 'Walking' && c.MustBeTrue)), `${id}: no native infected walking state scaled by WalkingSpeed`);
}
check(/internal const string ContaminatedAnimatorParameter = "Contaminated";/.test(zombie), 'zombie must drive the native Contaminated animator parameter');
check(/_tint\.SetTint\(RadiationMaterials\.WaterTintColor\)/.test(zombie), 'zombie tint must be the native CharacterTint in the radiation tint yellow');
// Walk: the native contaminated inputs. Native RunningStateUpdater forces
// RunningProhibited for a contaminated beaver; the infected walking state needs
// it, and the plain Running state (no Contaminated condition) wins without it.
const syncBody = methodBody('RadioactiveZombie.cs', 'private void Sync()') ?? '';
check(/GetComponent<WalkingEnforcer>\(\)/.test(zombie) && /\.GetWalkingEnforcerToggle\(\)/.test(zombie)
  && /_walkingToggle\.EnableForcedWalking\(\);/.test(syncBody) && /_walkingToggle\.DisableForcedWalking\(\);/.test(syncBody),
  'zombie must prohibit running through a native WalkingEnforcerToggle, applied and removed with the zombie state');
for (const id of ['BeaverAdult', 'BeaverChild']) {
  const states = (await readJson(resolve(vanillaRoot, 'Characters', 'Beaver', `${id}.blueprint.json`)))?.TimbermeshAnimatorControllerSpec?.AnimatorStates ?? [];
  const has = (s, name, value) => s.Conditions.some(c => c.ParameterName === name && c.MustBeTrue === value);
  check(states.some(s => has(s, 'Walking', true) && has(s, 'RunningProhibited', true) && has(s, 'Contaminated', true)),
    `${id}: native infected walk no longer requires Walking + RunningProhibited + Contaminated`);
  check(states.some(s => has(s, 'Walking', true) && has(s, 'RunningProhibited', false) && !s.Conditions.some(c => c.ParameterName === 'Contaminated')),
    `${id}: expected the native Running state without a Contaminated condition (why running must be prohibited)`);
}
// Hospital stay: zombies stay admitted for the whole course and are fed there.
const pantrySource = await readFile(resolve(root, 'src', 'DeepFrontier', 'Scripts', 'HospitalPantry.cs'), 'utf8').catch(() => '');
check(/appraiser\.AppraiseEffects\(_effects\[id\]\)/.test(pantrySource) && /Inventory\.TakeConsumed\(new GoodAmount\(best, 1\)\)/.test(pantrySource) && /new GoodConsumedEvent\(best\)/.test(pantrySource),
  'Hospital pantry must feed patients the natively appraised good with its native effects (Scripts/HospitalPantry.cs)');
// Build 146: zombies stopped going because admission waited on a pantry that never enabled.
const hospitalSource = await readFile(resolve(root, 'src', 'DeepFrontier', 'Scripts', 'Hospital.cs'), 'utf8').catch(() => '');
check(/class HospitalPantry\b[^{]*IFinishedStateListener/.test(pantrySource), 'HospitalPantry must declare IFinishedStateListener (it enables on the finished state)');
check(/public bool CanUse => IsOperating && CrewAssigned>0 && _pantry\.Enabled && !_pantry\.MealsShort;/.test(hospitalSource) && !/CanUse[^;]*CanFeed/.test(hospitalSource),
  'Hospital admission must not wait for patient meals: only a starving patient with an empty stock closes the ward');
check(/_needs\.NeedChangedActiveState \+=/.test(zombie) && /_needs\.NeedIsActive\(RadiationTuning\.NeedId\)/.test(methodBody('RadioactiveZombie.cs', 'private void Sync()') ?? ''),
  'zombie state must follow the native Irradiation need (saved, loaded and inherited by NeedManager)');
check(/_animator\.SetBool\(ContaminatedAnimatorParameter, _contaminable\.IsContaminated\)/.test(zombie) && /#if !UNITY_EDITOR\s+RadioactiveZombieTint\.RestoreNative\(this\);\s+#endif/.test(zombie),
  'cure must hand the animator and tint back to native contamination and CitizenTint');
check(zombieTint.trimStart().startsWith('#if !UNITY_EDITOR') && zombieTint.trimEnd().endsWith('#endif'), 'RadioactiveZombieTint.cs (Harmony) must be editor-excluded');
check(/\[HarmonyPatch\(typeof\(CitizenTint\), nameof\(CitizenTint\.UpdateTint\)\)\]/.test(zombieTint) && /static void Postfix\(/.test(zombieTint) && /class RadioactiveZombieModStarter : IModStarter/.test(zombieTint),
  'CitizenTint.UpdateTint postfix must be applied at mod start');
check(configurator.includes('AddDecorator<BeaverSpec, RadioactiveZombie>') && !/AddDecorator<Bot\w*, Radio/.test(configurator), 'RadioactiveZombie must be decorated on BeaverSpec only (bots are unaffected)');
// Death: the unchanged 8-day untreated clock, made visible.
check(/public const float LethalUntreatedHours = 8f \* 24f;/.test(service) && /public const float CareGraceHours = 12f;/.test(service), 'untreated radiation sickness must stay fatal after 8 days, after a 12-hour grace');
check(/public float UntreatedHoursLeft => RadiationTuning\.LethalUntreatedHours - _untreatedHours;/.test(exposure), 'RadiationExposure.UntreatedHoursLeft must count from UntreatedHours');
check(!/Hunger|Thirst/.test(methodBody('RadiationExposure.cs', 'private void UpdateSickness(') ?? 'Hunger'), 'the sickness clock must not depend on hunger or thirst');
check(/_exposure\.UntreatedHoursLeft/.test(methodBody('RadioactiveZombie.cs', 'public IEnumerable<EntityDescription> DescribeEntity()') ?? ''), 'zombie panel line must show RadiationExposure.UntreatedHoursLeft');
check(/public const float ZombieDyingAlertHours = 2f \* 24f;/.test(service) && /hoursLeft < RadiationTuning\.ZombieDyingAlertHours/.test(zombie), 'zombie alert must show under 2 days of untreated time');
check(/IEntityBadge/.test(zombie) && /_entityPanel\.ReloadDescription\(_entity\)/.test(zombie), 'zombie badge and live panel line missing');
check(/_loc\.T\(RadiationLoc\.DeathMessage, GetComponent<Character>\(\)\.FirstName\)/.test(exposure) && /^\{0\}.*zombie/.test(csvText('DeepFrontier.Radiation.DeathMessage') ?? ''), 'death message must name the beaver as a radioactive zombie');
for (const key of ['DeepFrontier.Radiation.Zombie.Countdown', 'DeepFrontier.Radiation.Zombie.CountdownPaused', 'DeepFrontier.Radiation.Zombie.Subtitle'])
  check((csvText(key) ?? '').includes('{0}'), `${key} must take its {0} argument`);

// --- production chain (owned by the progression generator)
const producers = [];
for (const file of await walk(resolve(dataRoot, 'Recipes'))) {
  const spec = JSON.parse((await readFile(file, 'utf8')).replace(/^﻿/, '')).RecipeSpec;
  if (spec?.Products?.some(p => p.Id === SLUDGE) && spec.Id !== 'RecoverRadioactiveSludge') producers.push(spec.Id);
}
if (producers.length === 0) {
  const message = 'no reactor/refinery recipe produces RadioactiveSludge yet (progression generator wiring pending)';
  if (strictChain) fail(message); else notes.push(`PENDING: ${message}`);
} else notes.push(`RadioactiveSludge producers: ${producers.join(', ')}`);

for (const note of notes) console.log(`note: ${note}`);
if (failures.length) {
  for (const failure of failures) console.error(`FAIL: ${failure}`);
  console.error(`Radiation content validation failed (${failures.length}) for ${dataRoot}`);
  process.exit(1);
}
console.log(`Radiation content validation passed for ${dataRoot}`);
