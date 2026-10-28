// Contamination Sensor substance choice (runtime: src/DeepFrontier/Scripts/Sensors).
//
// Called by tools/create_vertical_slice_content.mjs after the canonical
// Localizations/enUS.csv exists:
//
//   await (await import('./contamination_sensor_content.mjs')).applyContaminationSensor();
//
// or standalone: node tools/contamination_sensor_content.mjs [dataRoot]
// (dataRoot defaults to src/DeepFrontier/Data; use a scratch mirror to test).
//
// What it writes: localization rows only (the panel's dropdown label, one row
// per SensedSubstance member and the two readouts), appended to the canonical
// enUS.csv, which must not already define any of them. The native sensor
// blueprint, icon and model are not patched: the behaviour is a TemplateModule
// decorator on the native ContaminationSensor component.
//
// The keys are read from ContaminationSensorSubstance.cs (ContaminationSensorLoc
// and the SensedSubstance enum); every mismatch throws.
import {readFile, writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
export const SENSOR_SOURCE = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'Sensors', 'ContaminationSensorSubstance.cs');
export const LOCALIZATION_FILE = 'Localizations/enUS.csv';

export const SUBSTANCE_TEXT = {
  Badwater: 'Badwater',
  Radiation: 'Radiation',
  Any: 'Any contamination',
};
export const LABEL_TEXT = 'Measures';
// {0}, {1}: percent of the water, formatted by the panel.
export const READING_TEXT = {
  RadiationReading: 'Radiation: {0}%',
  AnyReading: 'Badwater: {0}%, radiation: {1}%',
};
export const READING_PLACEHOLDERS = {RadiationReading: 1, AnyReading: 2};

const fail = (message) => { throw new Error(`Contamination sensor content: ${message}`); };

// ContaminationSensorLoc constants and SensedSubstance members, in source order.
export async function readSensorSource(path = SENSOR_SOURCE) {
  const text = await readFile(path, 'utf8');
  const enumBody = /public enum SensedSubstance \{([^}]*)\}/.exec(text)?.[1] ?? fail(`no SensedSubstance enum in ${path}`);
  const substances = enumBody.split(',').map((part) => part.replace(/\/\/.*$/gm, '').trim()).filter(Boolean);
  if (substances.some((name) => !/^[A-Za-z]+$/.test(name))) fail(`SensedSubstance members must be plain names without values: ${substances.join(', ')}`);
  const locBody = /(?:internal|public) static class ContaminationSensorLoc \{([\s\S]*?)\n  \}/.exec(text)?.[1] ?? fail(`no ContaminationSensorLoc in ${path}`);
  const loc = Object.fromEntries([...locBody.matchAll(/public const string (\w+) = "([^"]+)";/g)].map(([, name, value]) => [name, value]));
  for (const name of ['Substance', 'SubstancePrefix', ...Object.keys(READING_TEXT)]) if (!loc[name]) fail(`ContaminationSensorLoc.${name} is missing`);
  if (loc.SubstancePrefix !== `${loc.Substance}.`) fail(`SubstancePrefix ${loc.SubstancePrefix} must be ${loc.Substance}.`);
  return {text, substances, loc};
}

export function localizationRows({substances, loc}) {
  const missing = substances.filter((name) => !SUBSTANCE_TEXT[name]);
  const extra = Object.keys(SUBSTANCE_TEXT).filter((name) => !substances.includes(name));
  if (missing.length || extra.length) fail(`substance texts differ from SensedSubstance (missing ${missing.join(', ') || 'none'}; extra ${extra.join(', ') || 'none'})`);
  return [
    [loc.Substance, LABEL_TEXT],
    ...substances.map((name) => [`${loc.SubstancePrefix}${name}`, SUBSTANCE_TEXT[name]]),
    ...Object.entries(READING_TEXT).map(([name, value]) => [loc[name], value]),
  ];
}

function csvCell(value) {
  if (typeof value !== 'string') fail('localization cells must be strings');
  return /[",\n\r]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
}

export async function applyContaminationSensor(dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')) {
  const rows = localizationRows(await readSensorSource());
  const path = resolve(dataRoot, LOCALIZATION_FILE);
  const text = await readFile(path, 'utf8').catch(() => fail(`localization target is missing: ${path}`));
  if (!text.endsWith('\n')) fail(`${path} must end with a newline`);
  const ids = new Set(text.split(/\r?\n/).map((line) => line.split(',')[0]));
  for (const [id] of rows) if (ids.has(id)) fail(`${path} already defines ${id}`);
  await writeFile(path, `${text}${rows.map(([id, value]) => [id, value, 'Deep Frontier'].map(csvCell).join(',')).join('\n')}\n`, 'utf8');
  console.log(`Contamination sensor content: ${rows.length} localization rows.`);
  return {rows: rows.length};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await applyContaminationSensor(process.argv[2] ? resolve(process.argv[2]) : undefined);
}
