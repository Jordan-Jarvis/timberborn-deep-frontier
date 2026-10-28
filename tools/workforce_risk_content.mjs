// Workforce risks: industrial injuries, bot wear, beaver-only and
// specialist-only crews (tools/workforce_risks.json).
//
// Run once at the end of canonical generation, after every building
// blueprint, recipe and the localization table exist, and before the
// automation audit (which must see the specs added here):
//   await (await import('./workforce_risk_content.mjs')).applyWorkforceRisks();
//
// What it writes (runtime in src/DeepFrontier/Scripts/Workforce/):
// - FrontierWorkforceRiskSpec on every template with a danger tier. It
//   replaces the native WorkshopRandomNeedApplierSpec those templates cloned
//   from vanilla, so each building has exactly one injury mechanism.
// - Beaver-only crews: WorkplaceSpec DisallowOtherWorkerTypes, Beaver
//   default, no bot unlock (native Workplace.ValidateWorkplaceSpec rejects a
//   disallowing workplace that still lists unlock costs).
// - FrontierSpecialistWorkplaceSpec on specialist crews.
// - The training programmes: one native product-less recipe each (vanilla
//   Recipe.Bot.IronTeeth pattern) and FrontierSpecialistSchoolSpec on the
//   school. The school's ProductionRecipeIds come from trainingRecipeIds(),
//   which create_frontier_expansion_content.mjs uses; checked here.
// - Configurations/DeepFrontierWorkforce.blueprint.json (settings and
//   disciplines) and the Workforce localization rows.
// It fails, without writing anything, when a listed template is missing, a
// pending template has appeared, a template already carries a workforce spec,
// or any collected template keeps native injuries without a declaration.
import {readFile, writeFile, access, mkdir} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const defaultRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));
export const CONFIG = 'tools/workforce_risks.json';
export const SETTINGS_BLUEPRINT = 'Configurations/DeepFrontierWorkforce.blueprint.json';
export const COLLECTION = 'TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json';
export const WORKFORCE_SPECS = ['FrontierWorkforceRiskSpec', 'FrontierSpecialistWorkplaceSpec', 'FrontierSpecialistSchoolSpec'];
export const NATIVE_INJURY_SPEC = 'WorkshopRandomNeedApplierSpec';
const PROBABILITIES = ['Low', 'Medium', 'High'];
const WORKERS = ['open', 'beavers', 'specialists'];
const VANILLA = ['vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources'];

const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const writeJson = async (path, value) => {
  await mkdir(dirname(path), {recursive: true});
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
};
const exists = (path) => access(path).then(() => true, () => false);
const csvCell = (value) => {
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
const csvRow = (id, text) => [id, text, 'Deep Frontier workforce risks'].map(csvCell).join(',');

export const disciplineKey = (id) => `DeepFrontier.Workforce.Discipline.${id}`;
export const disciplinePluralKey = (id) => `DeepFrontier.Workforce.Discipline.${id}.Plural`;
export const dangerKey = (tier) => `DeepFrontier.Workforce.Danger.${tier}`;

// Fixed texts used by the runtime (WorkforcePanels.cs and components).
export const TEXTS = {
  'DeepFrontier.Workforce.Panel.Title': 'Workforce risks',
  'DeepFrontier.Workforce.Panel.InjuryRisk': 'Injury risk: {0}. About {1}% per worker-hour while working; strained/exhausted workers face {2} times that.',
  'DeepFrontier.Workforce.Panel.InjuriesDisabled': 'Injury risk: {0}. Injuries are switched off in this game\'s settings.',
  'DeepFrontier.Workforce.Panel.InjurySeverity': 'An accident takes {0} days to heal without a hospital; {1}% of accidents are fatal.',
  'DeepFrontier.Workforce.Panel.Crew': 'Crew at the last check: {0} fit, {1} strained (low wellbeing or tired), {2} exhausted.',
  'DeepFrontier.Workforce.Panel.Record': 'Accidents here: {0} injured, {1} killed.',
  'DeepFrontier.Workforce.Panel.BotWear': 'Bots wear out {0}× faster while working here.',
  'DeepFrontier.Workforce.Panel.BotsNotAllowed': 'Bots are not allowed here.',
  'DeepFrontier.Workforce.Status.Exhausted': 'Exhausted workers: injury risk ×{0}',
  'DeepFrontier.Workforce.Specialists.Title': 'Specialist crew',
  'DeepFrontier.Workforce.Specialists.Required': 'Only trained {0} can work here.',
  'DeepFrontier.Workforce.Specialists.Staffing': 'Posts filled: {0}. Unassigned {2} in this district: {1}.',
  'DeepFrontier.Workforce.Specialists.Train': 'Train {0} at the Technical School. A specialist\'s skill dies with them.',
  'DeepFrontier.Workforce.Status.NoSpecialists': 'No {0}: this building cannot run. Train them at the Technical School.',
  'DeepFrontier.Workforce.Status.NoSpecialists.Short': 'No {0}',
  'DeepFrontier.Workforce.Status.FewSpecialists': 'Not enough {0}. Train more at the Technical School.',
  'DeepFrontier.Workforce.School.Title': 'Specialist training',
  'DeepFrontier.Workforce.School.Program': 'Course: {0}. Each finished course graduates the trainee with the most training hours.',
  'DeepFrontier.Workforce.School.NoProgram': 'Choose a training course.',
  'DeepFrontier.Workforce.School.NextGraduate': 'Next graduate: {0} ({1} h of training).',
  'DeepFrontier.Workforce.School.NoTrainee': 'No trainee enrolled. Specialists working here teach but never retrain.',
  'DeepFrontier.Workforce.School.Pending': 'Finished courses waiting for a trainee: {0}.',
  'DeepFrontier.Workforce.School.Roster': 'Colony specialists: {0}.',
  'DeepFrontier.Workforce.Status.NoTrainee': 'A course finished but no trainee is enrolled. Assign beavers who are not specialists.',
  'DeepFrontier.Workforce.Status.NoTrainee.Short': 'No trainee',
  'DeepFrontier.Workforce.Trait.Specialist': 'Specialist: {0}',
  'DeepFrontier.Workforce.Trait.Training': 'Technical School training: {0} h',
  'DeepFrontier.Workforce.Notification.Graduated': '{0} graduated as a {1}.',
  'DeepFrontier.Workforce.Notification.SkillLost': 'Skill lost: {0}, a {1}, has died. {2} left.',
  'DeepFrontier.Workforce.FatalAccident': '{0} was killed in an industrial accident at the {1}.',
  'DeepFrontier.Workforce.Bot.Wearing': 'Wearing out {0}× faster at the {1}.',
  'DeepFrontier.Workforce.Bot.Assigned': 'Assigned to the {1}: wears out {0}× faster inside.',
};

export async function loadWorkforceConfig(root = defaultRoot) {
  return readJson(resolve(root, CONFIG));
}

// Shape and value checks shared with tools/validate_workforce_risks.mjs.
export function checkWorkforceConfig(config) {
  const errors = [];
  const s = config.settings ?? {};
  const fraction = (v) => typeof v === 'number' && v > 0 && v < 1;
  if (typeof s.probabilityGroupId !== 'string' || !s.probabilityGroupId) errors.push('settings.probabilityGroupId is required');
  if (!PROBABILITIES.every((p) => fraction(s.nativeChances?.[p]))) errors.push('settings.nativeChances needs Low/Medium/High in (0, 1)');
  else if (!(s.nativeChances.Low < s.nativeChances.Medium && s.nativeChances.Medium < s.nativeChances.High)) errors.push('settings.nativeChances must rise Low < Medium < High');
  for (const key of ['injuryNeedId', 'fatigueNeedId']) if (typeof s[key] !== 'string' || !s[key]) errors.push(`settings.${key} is required`);
  if (!(typeof s.strainedBelowFatiguePoints === 'number' && s.strainedBelowFatiguePoints > 0)) errors.push('settings.strainedBelowFatiguePoints must be positive (tired band above the critical state)');
  if (!Number.isInteger(s.strainedBelowWellbeing) || !Number.isInteger(s.exhaustedBelowWellbeing) || s.exhaustedBelowWellbeing >= s.strainedBelowWellbeing)
    errors.push('settings: integer wellbeing thresholds with exhaustedBelowWellbeing < strainedBelowWellbeing');
  if (!Number.isInteger(s.strainedRolls) || !Number.isInteger(s.exhaustedRolls) || s.strainedRolls < 2 || s.exhaustedRolls <= s.strainedRolls)
    errors.push('settings: rolls must rise 1 (fit) < strainedRolls < exhaustedRolls');

  const tiers = config.dangerTiers ?? {};
  if (!Object.keys(tiers).length) errors.push('dangerTiers is empty');
  for (const [id, t] of Object.entries(tiers)) {
    if (!/^[A-Z][A-Za-z]+$/.test(id)) errors.push(`dangerTiers.${id}: id must be a PascalCase word (used in localization keys)`);
    if (!PROBABILITIES.includes(t.probability)) errors.push(`dangerTiers.${id}.probability must be Low, Medium or High`);
    if (!(typeof t.rollIntervalHours === 'number' && t.rollIntervalHours > 0 && t.rollIntervalHours <= 24)) errors.push(`dangerTiers.${id}.rollIntervalHours must be in (0, 24]`);
    // The native Injury need spans [-1, 0].
    if (!(typeof t.injuryPoints === 'number' && t.injuryPoints < 0 && t.injuryPoints >= -1)) errors.push(`dangerTiers.${id}.injuryPoints must be in [-1, 0)`);
    if (!(typeof t.fatalAccidentChance === 'number' && t.fatalAccidentChance >= 0 && t.fatalAccidentChance < 1)) errors.push(`dangerTiers.${id}.fatalAccidentChance must be in [0, 1)`);
  }

  const disciplines = config.disciplines ?? {};
  if (!Object.keys(disciplines).length) errors.push('disciplines is empty');
  for (const [id, d] of Object.entries(disciplines)) {
    if (!/^[A-Z][A-Za-z]+$/.test(id)) errors.push(`disciplines.${id}: id must be a PascalCase word`);
    if (!d.displayName || !d.pluralDisplayName) errors.push(`disciplines.${id} needs displayName and pluralDisplayName`);
  }

  const entries = [...Object.entries(config.templates ?? {}).map(([id, e]) => [id, e, false]),
    ...Object.entries(config.pendingTemplates ?? {}).map(([id, e]) => [id, e, true])];
  const usedDisciplines = new Set();
  for (const [id, e, pending] of entries) {
    const where = `${pending ? 'pendingTemplates' : 'templates'}.${id}`;
    if (!/^Buildings\/.+\.IronTeeth\.blueprint$/.test(id)) errors.push(`${where}: expected a Buildings/... .IronTeeth.blueprint id`);
    if (!Object.hasOwn(e, 'danger')) errors.push(`${where}: danger is required (a tier id or null)`);
    else if (e.danger !== null && !Object.hasOwn(tiers, e.danger)) errors.push(`${where}: unknown danger tier ${e.danger}`);
    if (!WORKERS.includes(e.workers)) errors.push(`${where}: workers must be ${WORKERS.join(', ')}`);
    if (!e.reason) errors.push(`${where}: reason is required`);
    if (e.workers === 'specialists') {
      if (!Object.hasOwn(disciplines, e.discipline)) errors.push(`${where}: unknown discipline ${e.discipline}`);
      else usedDisciplines.add(e.discipline);
    } else if (Object.hasOwn(e, 'discipline')) errors.push(`${where}: only specialist crews have a discipline`);
    if (e.workers === 'open' && e.danger) {
      if (!(typeof e.botWear === 'number' && e.botWear > 1)) errors.push(`${where}: an open workplace with a danger tier needs botWear > 1`);
    } else if (Object.hasOwn(e, 'botWear')) errors.push(`${where}: botWear only applies to open workplaces with a danger tier`);
    if (e.workers === 'open' && !e.danger) errors.push(`${where}: an open workplace without a danger tier changes nothing; remove it`);
  }

  const school = config.school ?? {};
  const schoolEntry = config.templates?.[school.template];
  if (!schoolEntry) errors.push(`school.template ${school.template} is not a declared template`);
  else if (schoolEntry.workers !== 'beavers' || schoolEntry.danger !== null) errors.push('school.template must be a beaver-only workplace without danger');
  const programs = school.programs ?? [];
  if (!programs.length) errors.push('school.programs is empty');
  const recipes = new Set();
  const taught = new Set();
  for (const p of programs) {
    if (!/^SpecialistTraining\.[A-Z][A-Za-z]+$/.test(p.recipe ?? '')) errors.push(`school program ${p.recipe}: recipe id must be SpecialistTraining.<Name>`);
    if (recipes.has(p.recipe)) errors.push(`school program ${p.recipe} is listed twice`);
    recipes.add(p.recipe);
    if (!Object.hasOwn(disciplines, p.discipline)) errors.push(`school program ${p.recipe}: unknown discipline ${p.discipline}`);
    if (!p.displayName) errors.push(`school program ${p.recipe}: displayName is required`);
    if (!(typeof p.hours === 'number' && p.hours > 0)) errors.push(`school program ${p.recipe}: hours must be positive worker-hours`);
    if (!(Number.isInteger(p.cyclesCapacity) && p.cyclesCapacity >= 1)) errors.push(`school program ${p.recipe}: cyclesCapacity must be a positive integer`);
    if (!/^Sprites\/Goods\/\w+Icon$/.test(p.icon ?? '')) errors.push(`school program ${p.recipe}: icon must be a Sprites/Goods/<Name>Icon sprite`);
    if (!Array.isArray(p.ingredients) || !p.ingredients.length
        || p.ingredients.some((i) => !Array.isArray(i) || typeof i[0] !== 'string' || !Number.isInteger(i[1]) || i[1] <= 0)
        || new Set(p.ingredients.map((i) => i[0])).size !== p.ingredients.length)
      errors.push(`school program ${p.recipe}: ingredients must be distinct [good, positive integer] pairs`);
    taught.add(p.discipline);
  }
  for (const id of Object.keys(disciplines)) {
    if (!usedDisciplines.has(id)) errors.push(`discipline ${id} is required by no specialist workplace`);
    if (!taught.has(id)) errors.push(`discipline ${id} is taught by no school programme`);
  }
  return errors;
}

export function settingsBlueprint(config) {
  const s = config.settings;
  return {
    FrontierWorkforceSettingsSpec: {
      ProbabilityGroupId: s.probabilityGroupId,
      NativeLowChance: s.nativeChances.Low,
      NativeMediumChance: s.nativeChances.Medium,
      NativeHighChance: s.nativeChances.High,
      InjuryNeedId: s.injuryNeedId,
      FatigueNeedId: s.fatigueNeedId,
      StrainedBelowFatiguePoints: s.strainedBelowFatiguePoints,
      StrainedBelowWellbeing: s.strainedBelowWellbeing,
      ExhaustedBelowWellbeing: s.exhaustedBelowWellbeing,
      StrainedRolls: s.strainedRolls,
      ExhaustedRolls: s.exhaustedRolls,
      Disciplines: Object.keys(config.disciplines).map((id) => ({
        Id: id, DisplayNameLocKey: disciplineKey(id), PluralDisplayNameLocKey: disciplinePluralKey(id),
      })),
    },
  };
}

export function riskSpec(config, entry) {
  const t = config.dangerTiers[entry.danger];
  return {
    DangerTier: entry.danger,
    Probability: t.probability,
    RollIntervalHours: t.rollIntervalHours,
    InjuryPoints: t.injuryPoints,
    FatalAccidentChance: t.fatalAccidentChance,
    BotWearMultiplier: entry.workers === 'open' ? entry.botWear : 1,
  };
}

export const trainingRecipeIds = (config) => config.school.programs.map((p) => p.recipe);

// Product-less training recipe from the vanilla Bot Assembler recipe.
export function trainingRecipe(template, program) {
  return {
    ...template,
    RecipeSpec: {
      ...template.RecipeSpec,
      Id: program.recipe,
      BackwardCompatibleIds: [],
      DisplayLocKey: `Recipe.${program.recipe}.DisplayName`,
      CycleDurationInHours: program.hours,
      Ingredients: program.ingredients.map(([Id, Amount]) => ({Id, Amount})),
      Products: [],
      ProducedSciencePoints: 0,
      Fuel: '',
      CyclesFuelLasts: 0,
      FuelCapacity: 0,
      CyclesCapacity: program.cyclesCapacity,
      Icon: program.icon,
    },
  };
}

export function schoolSpec(config) {
  return {Programs: config.school.programs.map((p) => ({RecipeId: p.recipe, Discipline: p.discipline}))};
}

export function localizationRows(config) {
  const rows = [];
  for (const [id, d] of Object.entries(config.disciplines)) {
    rows.push([disciplineKey(id), d.displayName], [disciplinePluralKey(id), d.pluralDisplayName]);
  }
  for (const tier of Object.keys(config.dangerTiers)) rows.push([dangerKey(tier), tier]);
  for (const p of config.school.programs) rows.push([`Recipe.${p.recipe}.DisplayName`, p.displayName]);
  rows.push(...Object.entries(TEXTS));
  return rows;
}

// Computes every change without writing; errors is empty when it may apply.
export async function planWorkforceRisks({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const config = await loadWorkforceConfig(root);
  const configErrors = checkWorkforceConfig(config);
  if (configErrors.length) throw new Error(`Workforce risks: ${CONFIG} is invalid:\n  ${configErrors.join('\n  ')}`);

  const collection = (await readJson(resolve(dataRoot, COLLECTION))).TemplateCollectionSpec?.['Blueprints#append'];
  if (!Array.isArray(collection)) throw new Error(`Workforce risks: ${COLLECTION} has no Blueprints#append list`);
  const collected = new Set(collection);

  // Load and change everything in memory first; write only if all checks pass.
  const changed = new Map();
  const errors = [];
  for (const id of Object.keys(config.pendingTemplates)) {
    if (collected.has(id) || await exists(resolve(dataRoot, `${id}.json`)))
      errors.push(`${id} is now generated; move it from pendingTemplates to templates in ${CONFIG}`);
  }
  for (const [id, entry] of Object.entries(config.templates)) {
    const path = resolve(dataRoot, `${id}.json`);
    if (!collected.has(id)) { errors.push(`${id} is not in the Buildings.IronTeeth template collection`); continue; }
    if (!await exists(path)) { errors.push(`${id} is declared but its blueprint was not generated (${path})`); continue; }
    const blueprint = await readJson(path);
    const present = WORKFORCE_SPECS.filter((key) => blueprint[key]);
    if (present.length) { errors.push(`${id} already has ${present.join(', ')}; regenerate it from its producer`); continue; }
    const workplace = blueprint.WorkplaceSpec;
    if (!workplace) { errors.push(`${id} has no WorkplaceSpec`); continue; }

    if (entry.workers === 'open') {
      const bot = (workplace.WorkerTypeUnlockCosts ?? []).some((cost) => cost.WorkerType === 'Bot');
      if (workplace.DisallowOtherWorkerTypes || !bot) errors.push(`${id} is declared open with bot wear but bots cannot work there`);
    } else {
      blueprint.WorkplaceSpec = {...workplace, DefaultWorkerType: 'Beaver', DisallowOtherWorkerTypes: true, WorkerTypeUnlockCosts: []};
    }
    if (entry.workers === 'specialists') blueprint.FrontierSpecialistWorkplaceSpec = {Discipline: entry.discipline};
    if (entry.danger) {
      if (!blueprint.WorkshopSpec) { errors.push(`${id} has a danger tier but no WorkshopSpec (injuries roll while the workshop works)`); continue; }
      delete blueprint[NATIVE_INJURY_SPEC];
      blueprint.FrontierWorkforceRiskSpec = riskSpec(config, entry);
    }
    changed.set(id, {path, blueprint});
  }

  // Every course must graduate into a generated workplace: a discipline whose
  // only workplace is still pending would leave graduates idle in the school.
  for (const program of config.school.programs) {
    const accepting = Object.entries(config.templates).filter(([, e]) => e.workers === 'specialists' && e.discipline === program.discipline).map(([id]) => id);
    if (!accepting.length) {
      const pending = Object.entries(config.pendingTemplates).filter(([, e]) => e.discipline === program.discipline).map(([id]) => id);
      errors.push(`course ${program.recipe} trains ${program.discipline} but no generated template accepts that discipline`
        + (pending.length ? ` (only pending: ${pending.join(', ')}; move it to templates when it is generated)` : ''));
    }
  }

  // School programmes: product-less native recipes written here.
  const recipeFiles = [];
  const school = changed.get(config.school.template);
  if (school) {
    const listed = school.blueprint.ManufactorySpec?.ProductionRecipeIds;
    const programs = trainingRecipeIds(config);
    if (!Array.isArray(listed)) errors.push(`${config.school.template} has no ManufactorySpec.ProductionRecipeIds`);
    else if (listed.length !== programs.length || !programs.every((r) => listed.includes(r)))
      errors.push(`${config.school.template} recipes are [${listed.join(', ')}]; its producer must list exactly trainingRecipeIds() [${programs.join(', ')}]`);
    const template = await readJson(resolve(root, ...VANILLA, 'Recipes', 'Recipe.Bot.IronTeeth.blueprint.json'));
    if (template.RecipeSpec.Products.length) errors.push('vanilla Recipe.Bot.IronTeeth is no longer product-less');
    for (const program of config.school.programs) {
      for (const [good] of program.ingredients) {
        if (!await exists(resolve(root, ...VANILLA, 'Goods', `Good.${good}.blueprint.json`)) && !await exists(resolve(dataRoot, 'Goods', `Good.${good}.blueprint.json`)))
          errors.push(`training recipe ${program.recipe}: ingredient ${good} is not a vanilla or generated good`);
      }
      if (!await exists(resolve(dataRoot, `${program.icon}.png`))) errors.push(`training recipe ${program.recipe}: icon ${program.icon}.png is not generated`);
      recipeFiles.push({path: resolve(dataRoot, 'Recipes', `Recipe.${program.recipe}.blueprint.json`), blueprint: trainingRecipe(template, program)});
    }
    school.blueprint.FrontierSpecialistSchoolSpec = schoolSpec(config);
  }

  // Every native injury on a Deep Frontier building must be declared here.
  for (const id of collection) {
    if (changed.has(id)) continue;
    const path = resolve(dataRoot, `${id}.json`);
    if (!await exists(path)) continue; // the automation audit reports ungenerated collection entries
    if ((await readJson(path))[NATIVE_INJURY_SPEC]) errors.push(`${id} keeps native ${NATIVE_INJURY_SPEC}; declare its danger tier in ${CONFIG}`);
  }

  const localizationPath = resolve(dataRoot, 'Localizations', 'enUS.csv');
  const lines = (await readFile(localizationPath, 'utf8')).split('\n');
  if (lines.at(-1) !== '') errors.push('enUS.csv must end with a newline');
  const ids = new Set(lines.map((line) => line.split(',')[0]));
  const rows = localizationRows(config);
  for (const [id] of rows) if (ids.has(id)) errors.push(`localization ${id} already exists`);
  return {config, changed, recipeFiles, errors, lines, rows, localizationPath};
}

export async function applyWorkforceRisks({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const {config, changed, recipeFiles, errors, lines, rows, localizationPath} = await planWorkforceRisks({root, dataRoot});
  if (errors.length) throw new Error(`Workforce risks: generation stopped:\n  ${errors.join('\n  ')}`);

  for (const {path, blueprint} of [...changed.values(), ...recipeFiles]) await writeJson(path, blueprint);
  await writeJson(resolve(dataRoot, SETTINGS_BLUEPRINT), settingsBlueprint(config));
  lines.pop();
  for (const [id, text] of rows) lines.push(csvRow(id, text));
  await writeFile(localizationPath, `${lines.join('\n')}\n`, 'utf8');

  const count = (predicate) => Object.values(config.templates).filter(predicate).length;
  const summary = {
    risk: count((e) => e.danger), beaverOnly: count((e) => e.workers !== 'open'),
    specialist: count((e) => e.workers === 'specialists'), pending: Object.keys(config.pendingTemplates).length,
  };
  console.log(`Workforce risks: ${summary.risk} hazardous workplaces, ${summary.beaverOnly} beaver-only crews (${summary.specialist} specialist), ${summary.pending} pending templates.`);
  return summary;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const dataRoot = process.argv[2] ? resolve(process.argv[2]) : undefined;
  console.log(JSON.stringify(await applyWorkforceRisks(dataRoot ? {dataRoot} : {})));
}
