// Static checks for the buildings that react to water contamination or to the
// weather, extended for radiation and the Radioactive Tide (the Contamination
// Sensor itself is tools/validate_contamination_sensor.mjs):
//   Weather Station     Radioactive Tide as a fourth mode (src/DeepFrontier/Scripts/WeatherStations)
//   Stream Gauge        radiation readout (Scripts/Sensors/StreamGaugeRadiationPanel.cs)
//   Sluice is Back!     "Measures" choice for the sluice's contamination automation, in the
//                       optional assembly DeepFrontier.SluiceIsBack (Scripts/SluiceIsBack)
//
//   node tools/validate_contamination_consumers.mjs [dataRoot]
//
// 1. Native contract: the Weather Station, its panel fragment and the Stream
//    Gauge still decompile (project ilspycmd, project Timberborn plugin
//    assemblies) with the members the extensions rely on
//    (tools/automation_content.json nativeTransmitterExtensions.WeatherStationSpec
//    and the evidence below); the installed Sluice is Back! is 11.0.0 with the
//    members the bridge patches.
// 2. Extensions: decorators, own save keys with the native behaviour as the
//    absent-key default, editor guards, Verify() before the patches, the
//    tide recognised by RadioactiveTideTuning.WeatherId, radiation read only
//    through IRadiationService, the sluice bridge only postfixing and never
//    referenced by the main assembly.
// 3. Packaging: the bridge is built as an optional assembly and installed as
//    Scripts/DeepFrontier.SluiceIsBack.dll.SluiceIsBack.optional.
// 4. Content: the panels' localization keys exist once in the generated
//    enUS.csv (they are the Contamination Sensor's and the tide's rows; no
//    new rows), and no generated blueprint patches the three buildings.
// Runtime behaviour is verified in game (all-buildings acceptance probes).
import {execFileSync} from 'node:child_process';
import {readFile, readdir, access} from 'node:fs/promises';
import {resolve, relative, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {devEnvironment} from './dev_environment.mjs';
import {LOCALIZATION_FILE, readSensorSource} from './contamination_sensor_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = process.argv[2] ? resolve(process.argv[2]) : resolve(root, 'src', 'DeepFrontier', 'Data');
const scripts = resolve(root, 'src', 'DeepFrontier', 'Scripts');
const stations = resolve(scripts, 'WeatherStations');
const bridge = resolve(scripts, 'SluiceIsBack');
const pluginsRoot = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Plugins', 'Timberborn');
const workshop = (await devEnvironment(root, ['workshopContent'])).workshopContent;
const sluiceMod = `${workshop}/3677643870/version-1.1`;
const ilspy = resolve(root, 'tools', 'dotnet', 'ilspycmd.exe');
const errors = [];
const read = (path) => readFile(path, 'utf8');
const exists = (path) => access(path).then(() => true, () => false);
const require = (text, needle, message) => { if (!text.includes(needle)) errors.push(message); };
const code = (text) => text.replace(/\/\/.*$/gm, '');
// Code without comments and string literals (type names in strings are reflection, not references).
const symbols = (text) => code(text).replace(/"(?:[^"\\]|\\.)*"/g, '""');
const guarded = (text) => text.trimStart().startsWith('#if !UNITY_EDITOR') && text.trimEnd().endsWith('#endif');

async function files(dir, suffix) {
  const result = [];
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) result.push(...await files(path, suffix));
    else if (entry.name.endsWith(suffix)) result.push(path);
  }
  return result;
}

function decompile(dll, type, references) {
  try {
    return execFileSync(ilspy, [dll, ...references.flatMap((r) => ['-r', r]), '-t', type], {encoding: 'utf8', maxBuffer: 64 << 20});
  } catch (error) {
    errors.push(`${relative(root, dll)} ${type}: decompilation failed (${error.message.split('\n')[0]})`);
    return '';
  }
}
function evidence(dll, type, contains, references, what) {
  const source = decompile(dll, type, references);
  if (!source) return;
  for (const text of contains) if (!source.includes(text)) errors.push(`${type}: no "${text}"; ${what} changed`);
}

// 1. Native contract.
const config = JSON.parse(await read(resolve(root, 'tools', 'automation_content.json')));
const station = config.nativeTransmitterExtensions?.WeatherStationSpec;
if (!station) errors.push('tools/automation_content.json: nativeTransmitterExtensions.WeatherStationSpec is missing');
if (!config.nativeContract?.transmitterSpecs?.includes('WeatherStationSpec')) errors.push('WeatherStationSpec is no longer a native transmitter spec in tools/automation_content.json');
for (const {dll, type, contains} of station?.nativeEvidence ?? []) evidence(resolve(pluginsRoot, dll), type, contains, [pluginsRoot], 'the native Weather Station');
for (const {file, contains} of station?.evidence ?? []) {
  let text;
  try { text = await read(resolve(root, file)); } catch { errors.push(`evidence file ${file} is missing`); continue; }
  if (!text.includes(contains)) errors.push(`${file} no longer contains "${contains}"`);
}
// The Stream Gauge is a display: no transmitter, a badwater-only readout from its first occupied block.
const gauge = decompile(resolve(pluginsRoot, 'Timberborn.WaterBuildings.dll'), 'Timberborn.WaterBuildings.StreamGauge', [pluginsRoot]);
if (gauge) {
  for (const text of ['ContaminationLevel = _threadSafeWaterMap.ColumnContamination(_coordinates);', '_coordinates = _blockObject.PositionedBlocks.GetOccupiedCoordinates().First();',
    'float num = _threadSafeWaterMap.WaterHeightOrFloor(_coordinates);', 'SetValues();', 'ResetValues();'])
    if (!gauge.includes(text)) errors.push(`StreamGauge: no "${text}"; the native Stream Gauge changed`);
  if (/ISamplingTransmitter|ITransmitter|Automator/.test(gauge)) errors.push('StreamGauge became an automation transmitter: it needs a "Measures" choice like the Contamination Sensor, not only a readout');
}
evidence(resolve(pluginsRoot, 'Timberborn.WaterBuildingsUI.dll'), 'Timberborn.WaterBuildingsUI.StreamGaugeFragment',
  ['_loc.T(_contaminationLevelPhrase, _streamGauge.ContaminationLevel);', 'if ((bool)_streamGauge && _streamGauge.Enabled)'], [pluginsRoot], 'the native Stream Gauge panel');
// Installed Sluice is Back!.
const sluiceManifestText = await read(`${sluiceMod}/manifest.json`).catch(() => null);
if (!sluiceManifestText) errors.push(`Sluice is Back! is not installed at ${sluiceMod}; the bridge cannot be checked`);
else {
  const manifest = JSON.parse(sluiceManifestText.replace(/^\uFEFF/, ''));
  if (manifest.Id !== 'SluiceIsBack' || manifest.Version !== '11.0.0') errors.push(`installed Sluice is Back! is ${manifest.Id} ${manifest.Version}; the bridge was verified against SluiceIsBack 11.0.0`);
  const refs = [pluginsRoot, `${workshop}/3430626620/version-1.1`];
  evidence(`${sluiceMod}/SluiceIsBack.dll`, 'SluiceIsBack.Components.Sluice', [
    'private float GetContamination()',
    'return (float)Math.Round(_threadSafeWaterMap.ColumnContamination(_sourceCoordinates), 2);',
    'return GetContamination() > _sluiceState.OnAboveLimit;',
    'return GetContamination() < _sluiceState.OnBelowLimit;',
    '_sourceCoordinates = _blockObject.TransformCoordinates(new Vector3Int(0, -1, 0));',
    '_sluiceState.SetStateAndSynchronize(source._sluiceState, MinHeight - MaxHeight);',
  ], refs, 'Sluice is Back!\'s sluice');
  evidence(`${sluiceMod}/SluiceIsBack.dll`, 'SluiceIsBack.Components.SluiceState', [
    'public void SetState(SluiceState neighbor, int minLimit)', 'public void SetStateAndSynchronize(SluiceState neighbor, int minLimit)',
    'new ComponentKey("SluiceState")',
  ], refs, 'Sluice is Back!\'s sluice state');
  evidence(`${sluiceMod}/SluiceIsBack.dll`, 'SluiceIsBack.Components.SluiceSynchronizer',
    ['sluice.SetState(currentState, component.MinHeight - component.MaxHeight);'], refs, 'Sluice is Back!\'s synchronizer');
}

// 2. Extensions.
const sensor = await readSensorSource();
if (sensor.substances[0] !== 'Badwater') errors.push('SensedSubstance must start with Badwater, the default of the sensor and the sluice');
if (!/public static class ContaminationSensorLoc \{/.test(sensor.text)) errors.push('ContaminationSensorLoc must be public: the Stream Gauge readout and the sluice bridge use its keys');

// Weather Station.
const tide = await read(resolve(stations, 'WeatherStationRadioactiveTide.cs'));
const stationPatches = await read(resolve(stations, 'WeatherStationPatches.cs'));
const stationKey = /ComponentKey Key = new\("([^"]+)"\)/.exec(tide)?.[1];
if (!stationKey?.startsWith('DeepFrontier.')) errors.push(`the Weather Station save key must be a DeepFrontier.* key, found ${stationKey}`);
require(tide, 'if (!entityLoader.TryGetComponent(Key, out var loader)) return;', 'a Weather Station saved without the tide choice must load as the native station');
require(tide, 'currentCycleHazardousWeather.Id == RadioactiveTideTuning.WeatherId', 'the tide must be recognised by RadioactiveTideTuning.WeatherId (both the vanilla and the Moddable Weathers tide use it)');
require(tide, '_station.Sample();', 'changing the tide mode must re-sample at once, as native SetMode updates the output');
if (!/\[Context\("Game"\)\]\s*public sealed class WeatherStationRadioactiveTideConfigurator\b/.test(tide)) errors.push('WeatherStationRadioactiveTideConfigurator must be [Context("Game")]');
require(tide, 'Bind<WeatherStationRadioactiveTide>().AsTransient();', 'the Weather Station decorator must be bound transient');
if (/ModdableWeathersLoaded|return;\s*\}\s*Bind</.test(code(tide))) errors.push('the Weather Station decorator must be bound on both tide paths (vanilla and Moddable Weathers)');
if (!guarded(stationPatches)) errors.push('WeatherStationPatches.cs must be wrapped in #if !UNITY_EDITOR');
const stationStart = /public void StartMod\([^)]*\) \{([\s\S]*?)\r?\n    \}/.exec(stationPatches)?.[1] ?? '';
if (!(stationStart.indexOf('WeatherStationNative.Verify();') >= 0 && stationStart.indexOf('WeatherStationNative.Verify();') < stationStart.indexOf('.Patch();')))
  errors.push('WeatherStationModStarter must call WeatherStationNative.Verify() before patching');
for (const patch of ['WeatherStationSamplePatch', 'WeatherStationOutputPatch', 'WeatherStationFragmentInitializePatch', 'WeatherStationFragmentUpdatePatch'])
  if (!stationStart.includes(`CreateClassProcessor(typeof(${patch})).Patch();`) || !new RegExp(`\\[HarmonyPatch\\]\\s*internal static class ${patch}\\b`).test(stationPatches))
    errors.push(`${patch} must be a [HarmonyPatch] class applied at mod start`);
require(stationPatches, 'if (!tide.SignalsRadioactiveTide) return true;', 'the output prefix must leave the native modes to the native switch');
require(stationPatches, 'private static void Prefix(WeatherStation __instance, HazardousWeatherService ____hazardousWeatherService)', 'the sample prefix must read the station\'s own HazardousWeatherService and never skip');
require(stationPatches, 'CreateLocalizable(new[] { RadioactiveTideLoc.Name }, container)', 'the fourth mode button must be a native radio button labelled RadioactiveTideLoc.Name');
require(stationPatches, 'NativeIl.LoadsString(initialize, ModeContainerName)', 'Verify() must check the native mode container name');
for (const path of await files(stations, '.cs'))
  if (/\bModdableWeathers\.|\busing\s+ModdableWeathers\b/.test(code(await read(path)))) errors.push(`${relative(root, path)}: the Weather Station must not reference Moddable Weathers types`);

// Stream Gauge readout.
const gaugePanel = await read(resolve(scripts, 'Sensors', 'StreamGaugeRadiationPanel.cs'));
if (!guarded(gaugePanel)) errors.push('StreamGaugeRadiationPanel.cs uses TimberUi and must be wrapped in #if !UNITY_EDITOR');
require(gaugePanel, 'this.BindFragment<StreamGaugeRadiationPanel>();', 'the Stream Gauge readout must be bound as an entity panel fragment');
require(gaugePanel, 'ContaminationSensorLoc.RadiationReading', 'the Stream Gauge readout must use the sensor\'s "Radiation: {0}%" row');
require(gaugePanel, 'PositionedBlocks.GetOccupiedCoordinates().First()', 'the Stream Gauge readout must sample the native gauge cell');
require(gaugePanel, '_radiation.Sample(cell).WaterRadiation', 'the Stream Gauge readout must read radiation through IRadiationService.Sample');

// Sluice is Back! bridge.
const bridgeFiles = await files(bridge, '.cs').catch(() => { errors.push(`missing ${relative(root, bridge)}`); return []; });
const bridgeText = new Map();
for (const path of bridgeFiles) {
  const text = await read(path);
  bridgeText.set(relative(bridge, path), text);
  if (!guarded(text)) errors.push(`${relative(root, path)} must be wrapped in #if !UNITY_EDITOR`);
  if (/\b(Prefix|Transpiler|Finalizer)\s*\(/.test(text)) errors.push(`${relative(root, path)}: the sluice bridge may only postfix the mod's measurement and state copy`);
  if (/\bRadiationSimulation\b|\bRadiationLockstep\b/.test(code(text))) errors.push(`${relative(root, path)}: read radiation only through IRadiationService`);
}
const bridgeSource = await read(resolve(scripts, 'Sensors', 'SluiceIsBackBridge.cs'));
const constant = (name) => new RegExp(`public const string ${name} = "([^"]+)";`).exec(bridgeSource)?.[1];
const asmdefText = await read(resolve(bridge, `${constant('BridgeAssembly')}.asmdef`)).catch(() => null);
if (!asmdefText) errors.push(`Scripts/SluiceIsBack has no ${constant('BridgeAssembly')}.asmdef`);
else {
  const asmdef = JSON.parse(asmdefText);
  if (asmdef.name !== constant('BridgeAssembly')) errors.push(`the bridge asmdef is named ${asmdef.name}, expected ${constant('BridgeAssembly')}`);
  if (JSON.stringify(asmdef.references) !== JSON.stringify(['DeepFrontier'])) errors.push('the bridge asmdef must reference only the DeepFrontier assembly');
}
if (constant('ModId') !== 'SluiceIsBack' || constant('ModAssembly') !== 'SluiceIsBack') errors.push('SluiceIsBackBridge.ModId and ModAssembly must be SluiceIsBack (the installed manifest Id and SluiceIsBack.dll)');
const substance = bridgeText.get('SluiceContaminationSubstance.cs') ?? '';
const sluicePatches = bridgeText.get('SluiceContaminationPatches.cs') ?? '';
const sluicePanel = bridgeText.get('SluiceContaminationPanel.cs') ?? '';
const sluiceKey = /ComponentKey Key = new\("([^"]+)"\)/.exec(substance)?.[1];
if (!sluiceKey?.startsWith('DeepFrontier.') || ['Sluice', 'SluiceState'].includes(sluiceKey)) errors.push(`the sluice save key must be a DeepFrontier.* key distinct from the mod's, found ${sluiceKey}`);
require(substance, 'if (!entityLoader.TryGetComponent(Key, out var loader)) return;', 'a sluice saved without the choice must load as the native badwater sluice');
require(substance, 'if (Substance == SensedSubstance.Badwater) return nativeBadwater;', 'Badwater must return the mod\'s own value unchanged');
require(substance, 'Math.Round(Share(Read(sourceCell)), 2)', 'the sluice measurement must round as Sluice.GetContamination does (Math.Round(share, 2))');
require(substance, 'sample.BadwaterShare + sample.WaterRadiation', 'Any must sum the badwater and radioactive shares');
require(substance, 'builder.AddDecorator<Sluice, SluiceContaminationSubstance>();', 'the sluice decorator must decorate the mod\'s Sluice');
if (!/\[Context\("Game"\)\]\s*public sealed class SluiceContaminationConfigurator\b/.test(substance)) errors.push('SluiceContaminationConfigurator must be [Context("Game")]');
const sluiceStart = /public void StartMod\([^)]*\) \{([\s\S]*?)\r?\n    \}/.exec(sluicePatches)?.[1] ?? '';
if (!(sluiceStart.indexOf('SluiceIsBackNative.Verify();') >= 0 && sluiceStart.indexOf('SluiceIsBackNative.Verify();') < sluiceStart.indexOf('.Patch();')))
  errors.push('SluiceContaminationModStarter must call SluiceIsBackNative.Verify() before patching');
for (const patch of ['SluiceMeasurementPatch', 'SluiceStateSynchronizationPatch'])
  if (!sluiceStart.includes(`CreateClassProcessor(typeof(${patch})).Patch();`)) errors.push(`${patch} must be applied at mod start`);
require(sluicePatches, 'Method(typeof(Sluice), "GetContamination", typeof(float))', 'the measurement patch must target the private Sluice.GetContamination() : float');
require(sluicePanel, 'this.BindFragment<SluiceContaminationPanel>();', 'the sluice choice must be bound as an entity panel fragment');
require(sluicePanel, '_dropdownProviders.CreateLocalized(', 'the sluice dropdown must use the native localized EnumDropdownProvider');
require(sluicePanel, 'ContaminationSensorLoc.SubstancePrefix', 'the sluice dropdown must use the sensor\'s substance rows');
for (const path of (await files(scripts, '.cs')).filter((p) => !p.startsWith(bridge + sep)))
  if (/\bSluiceIsBack\.[A-Za-z_]|\busing\s+SluiceIsBack\b/.test(symbols(await read(path))))
    errors.push(`${relative(root, path)} references Sluice is Back! in the main assembly; such code belongs in Scripts/SluiceIsBack (Assembly.GetTypes() must succeed without the mod)`);
const manifest = JSON.parse((await read(resolve(root, 'src', 'DeepFrontier', 'manifest.json'))).replace(/^\uFEFF/, ''));
if (manifest.RequiredMods.some((m) => m.Id === 'SluiceIsBack')) errors.push('the manifest must not require Sluice is Back! (optional dependency)');

// In-game acceptance: the all-buildings run ends with the sluice and weather station probes.
const probes = await read(resolve(scripts, 'AllBuildingsHazardProbes.cs')).catch(() => '');
const acceptance = await read(resolve(scripts, 'AllBuildingsAcceptance.cs'));
if (!guarded(probes)) errors.push('AllBuildingsHazardProbes.cs is missing or not wrapped in #if !UNITY_EDITOR');
require(acceptance, 'if(StartProbes()){_batchNumber--;return;}', 'the all-buildings run must start the hazard probes after its last batch');
require(acceptance, 'case ProbePhase: ProbeTick(); break;', 'the all-buildings run must drive the hazard probes');
for (const needle of ['"sluice: measures "', 'SensedSubstance.Radiation,true,.05f,false', 'SensedSubstance.Badwater,true,.05f,true', 'SensedSubstance.Badwater,false,.05f,false',
  'TideCommand="Deep Frontier: radioactive tide next cycle"', 'JumpCommand="Jump to next season"', '"weather station: signals while the radioactive tide is active"',
  '"weather station: advance warning (early activation) before the tide"', '"weather station: the forced cycle holds the tide"'])
  require(probes, needle, `AllBuildingsHazardProbes.cs no longer contains ${needle}`);
if (/\busing\s+SluiceIsBack\b|\bSluiceIsBack\.Components\.[A-Z]\w*\s*[<(]/.test(code(probes))) errors.push('AllBuildingsHazardProbes.cs must reach Sluice is Back! types by name only');

// 3. Packaging.
const optional = `${constant('BridgeAssembly')}.dll.${constant('ModId')}.optional`;
const batch = await read(resolve(root, 'tools', 'unity', 'DeepFrontierBatchBuild.cs'));
// The build packages every DeepFrontier.<ModId> asmdef as <name>.dll.<ModId>.optional (ac37d5c),
// so the bridge must be named DeepFrontier.<ModId> for that rule to give `optional`.
if (constant('BridgeAssembly') !== `DeepFrontier.${constant('ModId')}`) errors.push(`SluiceIsBackBridge.BridgeAssembly must be DeepFrontier.${constant('ModId')} so the build packages it as ${optional}`);
require(batch, 'OptionalPrefix = "DeepFrontier."', `the build must package the bridge as ${optional}`);
require(batch, 'PackageOptionalAssembly(mod.Name, name + ".dll", name + ".dll." + name.Substring(OptionalPrefix.Length) + ".optional");', `the build must package the bridge as ${optional}`);
const stage = await read(resolve(root, 'tools', 'stage_deep_frontier.ps1'));
require(stage, '3677643870\\version-1.1\\SluiceIsBack.dll', 'the stage script must import SluiceIsBack.dll for the bridge compile');
require(stage, "unity\\SluiceIsBack.dll.meta", 'the stage script must import SluiceIsBack.dll.meta');
if (!await exists(resolve(root, 'tools', 'unity', 'SluiceIsBack.dll.meta'))) errors.push('tools/unity/SluiceIsBack.dll.meta is missing');
require(await read(resolve(root, 'tools', 'build_deep_frontier.ps1')), "  '-disable-assembly-updater',", 'the build must pass -disable-assembly-updater without names (no assembly, SluiceIsBack.dll included, is updated)');
const verify = await read(resolve(root, 'tools', 'verify_deep_frontier_package.ps1'));
require(verify, `Scripts\\${optional}`, `the package verification must compare Scripts\\${optional}`);
require(await read(resolve(root, 'tools', 'validate_editor_guards.mjs')), "'SluiceIsBack'", 'tools/validate_editor_guards.mjs must treat SluiceIsBack as a dependency mod');

// 4. Content.
const csv = await read(resolve(dataRoot, LOCALIZATION_FILE));
const counts = new Map();
for (const line of csv.split(/\r?\n/).slice(1)) {
  const id = line.split(',')[0];
  if (id) counts.set(id, (counts.get(id) ?? 0) + 1);
}
const tideName = /public const string Name = "([^"]+)";/.exec(await read(resolve(scripts, 'RadioactiveTide', 'RadioactiveTideTuning.cs')))?.[1];
for (const id of [tideName, sensor.loc.Substance, sensor.loc.RadiationReading, sensor.loc.AnyReading, ...sensor.substances.map((s) => `${sensor.loc.SubstancePrefix}${s}`)])
  if (counts.get(id) !== 1) errors.push(`${LOCALIZATION_FILE}: ${id} is defined ${counts.get(id) ?? 0} times, expected once`);
for (const path of await files(dataRoot, '.json')) {
  const id = relative(dataRoot, path).split(sep).join('/');
  if (!id.endsWith('.blueprint.json')) continue;
  const text = await read(path);
  for (const spec of ['WeatherStationSpec', 'StreamGaugeSpec', 'LVSluiceSpec'])
    if (text.includes(`"${spec}"`)) errors.push(`${id}: ${spec} buildings must stay unpatched (the extensions are decorators and panels)`);
}

if (errors.length) {
  console.error(`Contamination consumer validation failed:\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
console.log(`Contamination consumer validation passed: Weather Station tide mode (${station.nativeEvidence.length} native evidence types), Stream Gauge radiation readout, ` +
  `Sluice is Back! 11.0.0 bridge (${bridgeFiles.length} files, packaged as ${optional}).`);
