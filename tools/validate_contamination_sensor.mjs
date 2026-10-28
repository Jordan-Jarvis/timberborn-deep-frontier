// Static checks for the Contamination Sensor substance choice
// (src/DeepFrontier/Scripts/Sensors, tools/contamination_sensor_content.mjs).
//
//   node tools/validate_contamination_sensor.mjs [dataRoot]
//
// 1. Native contract: the native sensor, its panel fragment and its UI module
//    still decompile (project ilspycmd, project Timberborn plugin assemblies)
//    with the members the extension relies on (tools/automation_content.json
//    nativeTransmitterExtensions.ContaminationSensorSpec.nativeEvidence).
// 2. Extension: decorator registration, Badwater default and absent-key load,
//    own save key, the measurement substitution, the editor-guarded postfix
//    applied after Verify(), radiation read only through IRadiationService.
// 3. Content: the generated localization rows match the source keys, and no
//    generated blueprint patches the native sensor (icon and model unchanged).
// Runtime behaviour is verified in game, not here.
import {execFileSync} from 'node:child_process';
import {readFile, readdir} from 'node:fs/promises';
import {resolve, relative, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {LOCALIZATION_FILE, READING_PLACEHOLDERS, localizationRows, readSensorSource} from './contamination_sensor_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = process.argv[2] ? resolve(process.argv[2]) : resolve(root, 'src', 'DeepFrontier', 'Data');
const scripts = resolve(root, 'src', 'DeepFrontier', 'Scripts');
const sensors = resolve(scripts, 'Sensors');
const pluginsRoot = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Plugins', 'Timberborn');
const ilspy = resolve(root, 'tools', 'dotnet', 'ilspycmd.exe');
const errors = [];
const read = (path) => readFile(path, 'utf8');

async function files(dir, suffix) {
  const result = [];
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) result.push(...await files(path, suffix));
    else if (entry.name.endsWith(suffix)) result.push(path);
  }
  return result;
}

// 1. Native contract.
const config = JSON.parse(await read(resolve(root, 'tools', 'automation_content.json')));
const extension = config.nativeTransmitterExtensions?.ContaminationSensorSpec;
if (!extension) errors.push('tools/automation_content.json: nativeTransmitterExtensions.ContaminationSensorSpec is missing');
if (!config.nativeContract?.transmitterSpecs?.includes('ContaminationSensorSpec')) errors.push('ContaminationSensorSpec is no longer a native transmitter spec in tools/automation_content.json');
for (const {dll, type, contains} of extension?.nativeEvidence ?? []) {
  let source;
  try {
    source = execFileSync(ilspy, [resolve(pluginsRoot, dll), '-r', pluginsRoot, '-t', type], {encoding: 'utf8', maxBuffer: 64 << 20});
  } catch (error) {
    errors.push(`${dll} ${type}: decompilation failed (${error.message.split('\n')[0]})`);
    continue;
  }
  for (const text of contains) if (!source.includes(text)) errors.push(`${dll} ${type}: no "${text}"; the native contamination sensor changed`);
}
for (const {file, contains} of extension?.evidence ?? []) {
  let text;
  try { text = await read(resolve(root, file)); } catch { errors.push(`evidence file ${file} is missing`); continue; }
  if (!text.includes(contains)) errors.push(`${file} no longer contains "${contains}"`);
}

// 2. Extension source.
const sensor = await readSensorSource();
const substance = sensor.text;
const patches = await read(resolve(sensors, 'ContaminationSensorPatches.cs'));
const panel = await read(resolve(sensors, 'ContaminationSensorPanel.cs'));
const require = (text, needle, message) => { if (!text.includes(needle)) errors.push(message); };

if (sensor.substances[0] !== 'Badwater') errors.push(`SensedSubstance must start with Badwater (the default), found ${sensor.substances.join(', ')}`);
for (const name of ['Badwater', 'Radiation', 'Any']) if (!sensor.substances.includes(name)) errors.push(`SensedSubstance lacks ${name}`);
const key = /ComponentKey Key = new\("([^"]+)"\)/.exec(substance)?.[1];
if (!key?.startsWith('DeepFrontier.')) errors.push(`the substance save key must be a DeepFrontier.* component key, found ${key}`);
if (['ContaminationSensor', 'WaterContaminationSensor'].includes(key)) errors.push(`the substance save key ${key} collides with a native sensor key`);
require(substance, 'if (!entityLoader.TryGetComponent(Key, out var loader)) return;', 'Load must keep Badwater when the save has no substance component');
require(substance, 'RequireDefined(substance);', 'Load and SetSubstance must reject unknown substances');
if (!/\[Context\("Game"\)\]\s*public sealed class ContaminationSensorConfigurator\b/.test(substance))
  errors.push('ContaminationSensorConfigurator must be [Context("Game")] like native AutomationBuildingsConfigurator');
require(substance, 'Bind<ContaminationSensorSubstance>().AsTransient();', 'the decorator must be bound transient');
require(substance, 'MeasuredBadwaterShare + MeasuredRadioactiveShare', 'Any must sum the badwater and radioactive shares');
require(substance, '_radiation.Sample(cell).WaterRadiation', 'Radiation must read the radioactive share through IRadiationService.Sample');
require(substance, '_radiation.SavedStatePending', 'the measurement must use the saved share until the saved radiation is applied');
for (const path of await files(sensors, '.cs')) {
  const text = await read(path);
  if (/\bRadiationSimulation\b|\bRadiationLockstep\b|\bRadiationRenderer\b/.test(text.replace(/\/\/.*$/gm, '')))
    errors.push(`${relative(root, path)}: read radiation only through IRadiationService`);
  if (/\b(Prefix|Transpiler|Finalizer)\s*\(/.test(text)) errors.push(`${relative(root, path)}: only a postfix on the native measurement is allowed`);
}
const radiationApi = await read(resolve(scripts, 'Radiation', 'IRadiationService.cs'));
require(radiationApi, 'bool SavedStatePending { get; }', 'IRadiationService must declare SavedStatePending');

const lines = patches.split(/\r?\n/).filter((line) => line.trim());
if (lines[0].trim() !== '#if !UNITY_EDITOR' || lines.at(-1).trim() !== '#endif') errors.push('ContaminationSensorPatches.cs must be wrapped in #if !UNITY_EDITOR');
require(patches, 'Method("GetContamination", typeof(float), BindingFlags.Instance | BindingFlags.NonPublic,', 'the patch must target the private ContaminationSensor.GetContamination(int) : float');
require(patches, 'private static MethodBase TargetMethod() => ContaminationSensorNative.Measurement();', 'the patch target must be the verified measurement method');
const start = /public void StartMod\([^)]*\) \{([\s\S]*?)\r?\n    \}/.exec(patches)?.[1] ?? '';
const verifyAt = start.indexOf('ContaminationSensorNative.Verify();');
const patchAt = start.indexOf('.Patch();');
if (verifyAt < 0 || patchAt < 0 || verifyAt > patchAt) errors.push('StartMod must call ContaminationSensorNative.Verify() before applying the patch');
if (!/\[HarmonyPatch\]\s*internal static class ContaminationSensorMeasurementPatch/.test(patches)) errors.push('ContaminationSensorMeasurementPatch must be a [HarmonyPatch] class');

if (panel.split(/\r?\n/)[0].trim() !== '#if !UNITY_EDITOR') errors.push('ContaminationSensorPanel.cs uses TimberUi and must be wrapped in #if !UNITY_EDITOR');
require(panel, 'this.BindFragment<ContaminationSensorSubstancePanel>();', 'the substance panel must be bound as an entity panel fragment');
require(panel, '_dropdownProviders.CreateLocalized(', 'the substance dropdown must use the native localized EnumDropdownProvider');
require(panel, 'ContaminationSensorLoc.SubstancePrefix', 'the substance dropdown must use ContaminationSensorLoc.SubstancePrefix');
require(panel, 'component.Sensor.SampledContamination.HasValue', 'the readout must follow the native sampled value (none when dry)');

// 3. Generated content.
const csv = await read(resolve(dataRoot, LOCALIZATION_FILE));
const table = new Map();
for (const line of csv.split(/\r?\n/).slice(1)) {
  if (!line) continue;
  const match = /^([^,]+),("(?:[^"]|"")*"|[^,]*),/.exec(line);
  if (!match) continue;
  const value = match[2].startsWith('"') ? match[2].slice(1, -1).replaceAll('""', '"') : match[2];
  table.set(match[1], [...(table.get(match[1]) ?? []), value]);
}
for (const [id, text] of localizationRows(sensor)) {
  const found = table.get(id) ?? [];
  if (found.length !== 1) errors.push(`${LOCALIZATION_FILE}: ${id} is defined ${found.length} times`);
  else if (found[0] !== text) errors.push(`${LOCALIZATION_FILE}: ${id} is "${found[0]}", expected "${text}"`);
}
for (const [name, count] of Object.entries(READING_PLACEHOLDERS)) {
  const text = table.get(sensor.loc[name])?.[0] ?? '';
  for (let i = 0; i < count; i++) if (!text.includes(`{${i}}`)) errors.push(`${sensor.loc[name]} lacks {${i}}`);
  if (text.includes(`{${count}}`)) errors.push(`${sensor.loc[name]} has more than ${count} placeholders`);
}
for (const path of await files(dataRoot, '.json')) {
  const id = relative(dataRoot, path).split(sep).join('/');
  if (/ContaminationSensor/.test(id) || (id.endsWith('.blueprint.json') && (await read(path)).includes('ContaminationSensorSpec')))
    errors.push(`${id}: the native Contamination Sensor blueprint, icon and model must stay unpatched`);
}

if (errors.length) {
  console.error(`Contamination sensor validation failed:\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
console.log(`Contamination sensor validation passed: substances ${sensor.substances.join(', ')}, ` +
  `${localizationRows(sensor).length} localization rows, ${extension.nativeEvidence.length} native evidence types, decorator ${extension.decorator}.`);
