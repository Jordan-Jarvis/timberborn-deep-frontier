// Narrative layer: the human-history mystery, staged objectives, evidence and
// the story beats that lead into the rocket missions and the ending.
//
// Called once, last, from tools/create_frontier_expansion_content.mjs after the
// rocket program (the Launch Pad missions, goods and recipes exist):
//   await (await import('./narrative_content.mjs')).applyNarrative();
//
// Runtime: src/DeepFrontier/Scripts/Narrative/ (NarrativeObjectiveService,
// NarrativeProductionReporter, HumanRecordCache, NarrativeJournal). Story bible:
// docs/story.md. Every story string lives in the enUS rows authored here.
//
// Writes:
// - Configurations/DeepFrontierNarrative.blueprint.json (NarrativeSettingsSpec)
// - MapEditor/Objects/HumanRecordCache (map object cloned from the vanilla
//   MediumRelic: its blocks, demolition and underground part; its own vault
//   model and icon from tools/map_objects.json) and its entry in the Common
//   map-editor collection
// - enUS.csv rows
// It reads every trigger target from the generated data and fails explicitly
// when a template, good, recipe or mission is missing. No spec is added to a
// player building, so tools/automation_content.json needs no customSpecs entry.
import {readFile, writeFile, mkdir, access, readdir} from 'node:fs/promises';
import {dirname, relative, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {MISSIONS as ROCKET_MISSIONS, LAUNCH_PAD} from './rocket_program_content.mjs';
import {mapObjectModel, mapObjectCollider, checkMapObjectBlueprint} from './map_object_content.mjs';

const defaultRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));
const vanillaRelative = ['vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources'];

export const NARRATIVE_FILES = {
  settings: 'Configurations/DeepFrontierNarrative.blueprint.json',
  cache: 'MapEditor/Objects/HumanRecordCache/HumanRecordCache.blueprint',
  mapCollection: 'TemplateCollections/TemplateCollection.MapEditor.Common.blueprint.json',
  buildingCollection: 'TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json',
  goodCollection: 'GoodCollections/GoodCollection.IronTeeth.blueprint.json',
  localization: 'Localizations/enUS.csv',
};
export const FACTION_ID = 'IronTeeth';
export const ENDING_MISSION = 'LongRangeBeacon';
export const REQUIREMENT_KINDS = ['BuildingFinished', 'GoodProduced', 'RecipeCompleted', 'MissionCompleted', 'EndingChosen', 'CachesSurveyed'];
export const ENDING_TEXT = ['', 'Choice', 'Epilogue'];

// Human Record Cache: a map-editor object cloned from the vanilla MediumRelic.
// A finished workshop that runs SurveyRecipeId with any occupied cell within
// SurveyRadius cells (horizontal, and within SurveyRadius layers) surveys it
// while its workers work. After SurveyHours of working time the cache hands
// RewardAmount RewardGoodId to that workshop's output inventory, as its
// storage allows, and the next cache record joins the journal.
export const CACHE = {
  template: 'MediumRelic',
  templateName: 'HumanRecordCache',
  icon: 'MapEditor/Objects/HumanRecordCache/HumanRecordCacheIcon',
  toolGroup: 'MapEditorObjects',
  toolOrder: 1450,
  // Radius 7 (was 4) since the 2026-10-30 compaction trimmed the Archive Excavation from 10x9 to 7x6 inside
  // its old footprint (at most 3 tiles per axis): every cache the old excavation reached stays in range.
  spec: {SurveyRecipeId: 'ArchiveData', SurveyRadius: 7, SurveyHours: 24, RewardGoodId: 'ArchiveData', RewardAmount: 6},
};

const T = (name) => `${name}.IronTeeth`;

// ---- Main chapters (strictly in order) ----
export const STAGES = [
  {id: 'NotNatural', science: 500,
    title: 'Something in the Water',
    objective: 'Study the badwater: finish a Public Health Lab, a Water Treatment Plant, a Deep Drill or a Chemical Works.',
    hint: 'Public Health Lab (Wellbeing, 1,000 science), Deep Drill (Metal, 1,000), Water Treatment Plant (Water, 1,800) or Chemical Works (Metal, 4,000). Any one will do.',
    story: [
      'Every beaver knows badwater: green, sour, and best admired from a distance. The old stories call it a sickness of the land.',
      'The colony is no longer sure the old stories are right. Badwater behaves the same everywhere, in every spring and every badtide, as if it were made to a recipe. Somebody, it seems, wrote that recipe down.',
    ],
    requirements: [{kind: 'BuildingFinished', amount: 1, label: 'Investigation building finished',
      targets: [T('PublicHealthLab'), T('WaterTreatmentPlant'), T('DeepDrill'), T('ChemicalWorks')],
      variants: {
        [T('PublicHealthLab')]: "The health lab's first badwater samples were meant to help the sick. The chemists came back with puzzled faces and a very long list of things that should not be in a river.",
        [T('WaterTreatmentPlant')]: "The treatment plant's first filter cakes came out of the press the wrong colour. The exact same wrong colour, every single time.",
        [T('DeepDrill')]: 'The drill crew brought up a core with something round and hollow inside it: a pipe, far older than the colony and far too big for beavers.',
        [T('ChemicalWorks')]: 'The chemists who turn badwater into feedstock noticed that it splits the same way, batch after batch, like a recipe someone followed carefully.',
      }}]},
  {id: 'UnderTheValley', science: 1000,
    title: 'Under the Valley',
    objective: 'Reach the deep sector: refine 20 deep alloy at a Deep Processor.',
    hint: 'The Deep Drill brings up deep ore from a deep ore source; the Deep Processor turns ore and water into deep alloy, coal, crude oil and uranium ore.',
    story: [
      'The deep sector is not empty. Below the old riverbed run tunnels lined with enormous pipes, all of them stamped with the same three letters, VWA, and all of them heading upriver.',
      'Painted on one pipe, with increasing underlining: NOT FOR DRINKING. Someone long ago took that very seriously.',
    ],
    requirements: [{kind: 'GoodProduced', amount: 20, label: 'Deep alloy refined', targets: ['DeepAlloy']}]},
  {id: 'WhatTheWaterCarries', science: 1500,
    title: 'What the Water Carries',
    objective: 'Trace what the water carries: purify 80 pure water and make 10 chemical from badwater.',
    hint: 'Water Treatment Plants make pure water from water and filter media. Chemical Works make chemical from badwater and extract.',
    story: [
      'Side by side, the filter residue and the chemical feedstock tell the same story. Badwater is a mixture: fine grit from deep rock, a stubborn green dye and a dozen compounds nothing in nature bothers to make.',
      'It is not a disease. It is runoff. Somewhere upriver, something is still leaking what the old deep pipes once carried, and the colony is going to find out what.',
    ],
    requirements: [
      {kind: 'GoodProduced', amount: 80, label: 'Pure water purified', targets: ['PureWater']},
      {kind: 'GoodProduced', amount: 10, label: 'Chemical made from badwater', targets: ['Chemical']},
    ]},
  {id: 'OpenTheRuins', science: 2000,
    title: 'Open the Ruins',
    objective: 'Open the human ruins: recover 6 artifacts at an Archive Excavation.',
    hint: 'The Archive Excavation (Science menu, 9,000 science) opens human ruins with explosives and treated planks. Any Human Record Cache on the map can be surveyed by a nearby excavation for extra archive data.',
    story: [
      'The first finds are small and baffling: a hard hat big enough to bathe a kit in, a mug reading WORLD\'S OKAYEST ENGINEER, and a sign that says HOLDING STATION 3 - AUTHORIZED PERSONNEL ONLY.',
      'Underneath, in smaller letters: UNAUTHORIZED PERSONNEL ALSO ONLY. The humans, it turns out, had a sense of humour. They also had sealed data drives, which the excavation crews are now carefully drying out.',
    ],
    requirements: [{kind: 'GoodProduced', amount: 6, label: 'Artifacts recovered', targets: ['RecoveredArtifact']}]},
  {id: 'TheArchiveWakes', science: 3000,
    title: 'The Archive Wakes',
    objective: 'Wake the archive: restore 10 archive data.',
    hint: 'Archive data comes from 2 recovered artifacts, grease and a metal part at the Archive Excavation.',
    story: [
      'The first restored drive belongs to the Valley Water Authority. Its records describe the Deepworks, the humans\' great wells and drills, which pulled ancient water and ore up from under this valley for their factories.',
      'What the factories could not use went upriver into the Holding: a chain of sealed basins kept clean by a treatment works that ran day and night. Projected containment life: indefinite, subject to maintenance.',
      'A memo is attached. Re: containment maintenance. Postponed to next quarter. Previous note: postponed to next quarter.',
    ],
    requirements: [{kind: 'GoodProduced', amount: 10, label: 'Archive data restored', targets: ['ArchiveData']}]},
  {id: 'TheLastShift', science: 5000,
    title: 'The Last Shift',
    objective: "Read the last shift's records: restore 30 archive data in total and finish a Mission Control.",
    hint: 'Mission Control unlocks at 30,000 science. Guidance computers and telemetry also need archive data, so keep the drives coming.',
    story: [
      'The newest drives are the saddest and the tidiest. The rains failed, then the wells, then the harvests. The humans decided to leave the valley for now and follow the rain north. Nobody wrote down when now would end.',
      'The last shift did its best. It set the treatment works to automatic, put the Holding\'s flush valves on a schedule to run until further notice, and switched off the lights. No further notice was ever given.',
      'Mission Control has found one more thing: an old orbital frequency. Something up there is still answering.',
    ],
    requirements: [
      {kind: 'GoodProduced', amount: 30, label: 'Archive data restored', targets: ['ArchiveData']},
      {kind: 'BuildingFinished', amount: 1, label: 'Mission Control finished', targets: [T('MissionControl')]},
    ]},
  {id: 'EyesAbove', science: 0,
    title: 'Eyes Above',
    objective: 'Launch the Orbital Observatory from a Launch Pad.',
    hint: 'A launch needs airframes, propulsion, guidance computers, telemetry and liquid hydrogen and oxygen. A staffed Mission Control lowers the risk. Nuclear power helps but is not required.',
    story: [
      'Laid over the Authority\'s maps, the orbital images settle the question. Every badwater spring in the valley sits on the line of an old pipe, and every pipe leads back to the Holding.',
      'The badtides line up too: they arrive on the same schedule the last shift set for the flush valves. The humans never turned the Holding off. There was simply nobody left to give further notice.',
    ],
    requirements: [{kind: 'MissionCompleted', amount: 1, label: 'Orbital Observatory mission', targets: ['OrbitalObservatory']}]},
  {id: 'WhatTheStationKept', science: 0,
    title: 'What the Station Kept',
    objective: 'Launch the Recovery Probe.',
    hint: 'The Recovery Probe carries mission payloads: guidance computers packed with recovered artifacts.',
    story: [
      'The station\'s data core holds the treatment works\' full design and a final log from its crew: Turned the lights off. Left the telescope on. Someone should keep looking. Heading home, wherever that turns out to be.',
      'The design looks familiar. The colony\'s own water treatment plants already do, in beaver size, what the humans\' works did before the filters ran out. The Holding still leaks, but it can be kept, as long as someone stays to keep it.',
      'Only one launch remains, and the colony must decide what that last rocket will say.',
    ],
    requirements: [{kind: 'MissionCompleted', amount: 1, label: 'Recovery Probe mission', targets: ['RecoveryProbe']}]},
  {id: 'TheMessage', science: 0, endingText: 'Choice',
    title: 'What the Beacon Says',
    objective: 'Decide what the Long-Range Beacon will carry. Choose in this journal.',
    hint: 'The choice changes the ending\'s story, not the rocket or its launch.',
    story: [
      'After three evenings of debate, two votes and one very long speech about punctuation, the colony agreed on what the beacon will carry.',
    ],
    requirements: [{kind: 'EndingChosen', amount: 1, label: 'Beacon message chosen', targets: ['Signal', 'Archive', 'Settlement']}]},
  {id: 'TheBeacon', science: 0, endingText: 'Epilogue',
    title: 'The Long-Range Beacon',
    objective: 'Launch the Long-Range Beacon.',
    hint: 'The beacon is the final launch. Its success completes the colony\'s story.',
    story: [
      'The Long-Range Beacon is aloft. Far upriver the Holding still seeps, but the colony\'s treatment works now do what the last shift could not: they keep running, and somebody changes the filters.',
      'The badwater has a source, a reason and, at last, a caretaker.',
    ],
    requirements: [{kind: 'MissionCompleted', amount: 1, label: 'Long-Range Beacon mission', targets: [ENDING_MISSION]}]},
];

// ---- Optional discoveries (any order, never gate the chapters) ----
export const DISCOVERIES = [
  {id: 'ClinicLog', science: 250,
    title: "The Doctors' Ledger",
    objective: 'Finish a Hospital.',
    story: ['The hospital keeps a ledger of every badwater patient. After a season, the doctors notice the bad days arrive in a rhythm, like a schedule nobody remembers setting.'],
    requirements: [{kind: 'BuildingFinished', amount: 1, label: 'Hospital finished', targets: [T('Hospital')]}]},
  {id: 'CleanerThanTheRiver', science: 250,
    title: 'Cleaner Than the River',
    objective: 'Purify 500 pure water.',
    story: ['Five hundred barrels of water cleaner than the river has been in living memory. The treatment crews have started tasting it competitively.'],
    requirements: [{kind: 'GoodProduced', amount: 500, label: 'Pure water purified', targets: ['PureWater']}]},
  {id: 'HoldingOurOwn', science: 250,
    title: 'Holding Our Own',
    objective: 'Finish a Radioactive Waste Vault.',
    story: ['The colony now keeps a holding of its own. Unlike the humans\' Holding, this one has a label, a ledger and a beaver whose whole job is reading both.'],
    requirements: [{kind: 'BuildingFinished', amount: 1, label: 'Radioactive Waste Vault finished', targets: [T('RadioactiveWasteVault')]}]},
  {id: 'CleanHands', science: 250,
    title: 'Clean Hands',
    objective: 'Decontaminate water once at a Radioactive Waste Refinery.',
    story: ['The first barrel of contaminated water made drinkable again. It is a small barrel, and the colony is very proud of it.'],
    requirements: [{kind: 'RecipeCompleted', amount: 1, label: 'Water decontaminated', targets: ['DecontaminateWater']}]},
  ...[
    ['CacheRoster', 'Record Cache: Shift Roster', 'A shift roster from Holding Station 3. The names have faded, but one column, headed BROUGHT SNACKS, is ticked every single day by the same person.'],
    ['CacheDrawing', "Record Cache: A Child's Drawing", 'A drawing of the river, a sun, a very tall house and a small round animal with a flat tail. The label underneath says FRIEND.'],
    ['CacheWeather', 'Record Cache: Weather Log', 'Day 41: no rain. Day 42: no rain. Day 43: no rain, but someone has drawn a cloud in the margin to cheer everyone up.'],
    ['CacheMemo', 'Record Cache: Memo 14-C', 'Filters for the treatment works are back-ordered. Please do not drink from the river until further notice. Please do not ask when further notice is.'],
    ['CachePostcard', 'Record Cache: Postcard', 'Arrived north. It rains here. Miss the valley terribly. I think somebody left the pumps on. - M.'],
  ].map(([id, title, text], index) => ({id, science: 0, title,
    objective: `Survey ${index + 1} Human Record ${index ? 'Caches' : 'Cache'} from an Archive Excavation.`,
    story: [text],
    requirements: [{kind: 'CachesSurveyed', amount: index + 1, label: 'Record caches surveyed', targets: []}]})),
];

// ---- The colony's choice for the final launch ----
export const ENDINGS = [
  {id: 'Signal', title: 'We Are Here',
    description: 'Transmit a standing call: where the Holding is, how to keep it, and an open invitation to anyone still listening.',
    epilogue: [
      'Every few hours the beacon repeats one message in every format the archive could find: a map, a list of numbers and a drawing of a beaver waving.',
      "Nobody has answered yet. The colony has decided that 'yet' is the important word, and keeps a light on at the launch pad, just in case.",
    ]},
  {id: 'Archive', title: 'The Whole Record',
    description: "Preserve everything: the humans' records, the colony's own ledgers and the story of the badwater, safe in orbit for whoever comes next.",
    epilogue: [
      'The beacon carries every drive the excavations restored and every ledger the colony ever kept, including the boring ones, because the boring ones turned out to matter most.',
      "If anyone ever wonders how a valley went dry and came back, the answer is up there, filed under MAINTENANCE: DO NOT POSTPONE.",
    ]},
  {id: 'Settlement', title: 'The Map Home',
    description: 'Guide future settlers: clean-water maps, treatment designs and the safe routes the colony learned, so others can build where the land has healed.',
    epilogue: [
      'The beacon does not ask anyone to come. It simply explains, very clearly, where the water is clean, how to keep it that way and which roots are the tastiest.',
      'Somewhere, someday, a small band of travellers will follow it over the ridge and find a valley already waiting for them.',
    ]},
];

// ---- Interface text used by the C# runtime ----
export const UI_ROWS = [
  ['Narrative.Notification.Chapter', 'Frontier Journal: {0}'],
  ['Narrative.Notification.Discovery', 'Discovery: {0}'],
  ['Narrative.Notification.Choose', 'The beacon is ready to carry a message: choose it in the Frontier Journal.'],
  ['Narrative.Dialog.Chapter', 'Frontier Journal - chapter {0} of {1}'],
  ['Narrative.Dialog.Discovery', 'Frontier Journal - discovery'],
  ['Narrative.Dialog.Reward', 'Reward: {0} science'],
  ['Narrative.Dialog.Decision', 'The beacon will carry: {0}'],
  ['Narrative.Journal.Title', 'Frontier Journal'],
  ['Narrative.Journal.Widget', 'Frontier Journal ({0}/{1})'],
  ['Narrative.Journal.WidgetComplete', 'Frontier Journal: complete'],
  ['Narrative.Journal.Open', 'Open journal'],
  ['Narrative.Journal.Current', 'Chapter {0} of {1}: {2}'],
  ['Narrative.Journal.AllComplete', "Every chapter is complete. The colony's story is told."],
  ['Narrative.Journal.Progress', '{0}: {1} / {2}'],
  ['Narrative.Journal.ProgressDone', '{0}: done'],
  ['Narrative.Journal.Hint', 'Hint: {0}'],
  ['Narrative.Journal.ChooseIntro', 'Choose what the Long-Range Beacon will carry. The choice is final.'],
  ['Narrative.Journal.ChooseButton', 'Choose: {0}'],
  ['Narrative.Journal.Chosen', 'The beacon will carry: {0}'],
  ['Narrative.Journal.Chronicle', 'Chronicle'],
  ['Narrative.Journal.NoChronicle', 'No chapters completed yet.'],
  ['Narrative.Journal.Discoveries', 'Discoveries: {0} of {1}'],
  ['Narrative.Journal.DiscoveryPending', 'Undiscovered: {0}'],
  ['Narrative.Journal.ChapterEntry', '{0}. {1}'],
  ['Narrative.Choice.Title', 'What the Beacon Says'],
  ['Narrative.Choice.Later', 'Decide later'],
  ['Narrative.Cache.Title', 'Human Record Cache'],
  ['Narrative.Cache.Surveyed', 'Surveyed: its records are in the Frontier Journal.'],
  ['Narrative.Cache.NoSurveyor', 'Needs a finished Archive Excavation within {0} tiles to survey it.'],
  ['Narrative.Cache.Idle', 'Archive Excavation in range, but no one is working there.'],
  ['Narrative.Cache.Surveying', 'Surveying: {0}%'],
  ['Narrative.Cache.WaitingForStorage', 'Survey complete: handing over records as the excavation has storage space ({0} of {1}).'],
  ['Narrative.Cache.Reward', 'Survey reward: {0} {1} and a journal record. Demolishing it before the survey loses its records.'],
  ['Building.HumanRecordCache.DisplayName', 'Human Record Cache'],
  ['Building.HumanRecordCache.Description', 'A sealed human records box. A working Archive Excavation within four tiles surveys it for archive data and a Frontier Journal record. It can also be demolished like a relic, losing its records.'],
  ['Building.HumanRecordCache.FlavorDescription', 'Labelled, in three languages: DO NOT OPEN. Open carefully.'],
];

const stageKey = (kind, id, suffix) => `Narrative.${kind}.${id}.${suffix}`;
const shortTemplate = (template) => template.replace(/\.IronTeeth$/, '');

function entrySpec(entry, kind) {
  return {
    Id: entry.id,
    TitleLocKey: stageKey(kind, entry.id, 'Title'),
    ObjectiveLocKey: stageKey(kind, entry.id, 'Objective'),
    HintLocKey: entry.hint ? stageKey(kind, entry.id, 'Hint') : '',
    StoryLocKeys: entry.story.map((_, i) => stageKey(kind, entry.id, `Story.${i + 1}`)),
    ScienceReward: entry.science,
    EndingText: entry.endingText ?? '',
    Requirements: entry.requirements.map((r, i) => ({
      Kind: r.kind, Targets: r.targets, Amount: r.amount,
      LabelLocKey: stageKey(kind, entry.id, `Requirement.${i + 1}`),
      VariantLocKeys: r.variants ? r.targets.map((t) => stageKey(kind, entry.id, `Variant.${shortTemplate(t)}`)) : [],
    })),
  };
}

export function narrativeSpec() {
  return {
    FactionId: FACTION_ID,
    EndingMissionId: ENDING_MISSION,
    Stages: STAGES.map((s) => entrySpec(s, 'Stage')),
    Discoveries: DISCOVERIES.map((d) => entrySpec(d, 'Discovery')),
    Endings: ENDINGS.map((e) => ({
      Id: e.id, TitleLocKey: `Narrative.Ending.${e.id}.Title`, DescriptionLocKey: `Narrative.Ending.${e.id}.Description`,
      EpilogueLocKeys: e.epilogue.map((_, i) => `Narrative.Ending.${e.id}.Epilogue.${i + 1}`),
    })),
  };
}

export function localizationRows() {
  const rows = [];
  const entryRows = (entry, kind) => {
    rows.push([stageKey(kind, entry.id, 'Title'), entry.title]);
    rows.push([stageKey(kind, entry.id, 'Objective'), entry.objective]);
    if (entry.hint) rows.push([stageKey(kind, entry.id, 'Hint'), entry.hint]);
    entry.story.forEach((text, i) => rows.push([stageKey(kind, entry.id, `Story.${i + 1}`), text]));
    entry.requirements.forEach((r, i) => {
      rows.push([stageKey(kind, entry.id, `Requirement.${i + 1}`), r.label]);
      if (r.variants) for (const t of r.targets) rows.push([stageKey(kind, entry.id, `Variant.${shortTemplate(t)}`), r.variants[t]]);
    });
  };
  STAGES.forEach((s) => entryRows(s, 'Stage'));
  DISCOVERIES.forEach((d) => entryRows(d, 'Discovery'));
  for (const e of ENDINGS) {
    rows.push([`Narrative.Ending.${e.id}.Title`, e.title]);
    rows.push([`Narrative.Ending.${e.id}.Description`, e.description]);
    e.epilogue.forEach((text, i) => rows.push([`Narrative.Ending.${e.id}.Epilogue.${i + 1}`, text]));
  }
  rows.push(...UI_ROWS);
  return rows;
}

// Authoring checks that need no generated data (also run by the validator).
export function checkAuthoredContent() {
  const errors = [];
  const ids = [...STAGES, ...DISCOVERIES].map((e) => e.id);
  if (new Set(ids).size !== ids.length) errors.push('duplicate stage or discovery id');
  const endingIds = ENDINGS.map((e) => e.id);
  if (new Set(endingIds).size !== endingIds.length || !endingIds.length) errors.push('endings must be unique and non-empty');
  for (const [kind, list] of [['stage', STAGES], ['discovery', DISCOVERIES]]) {
    for (const entry of list) {
      const where = `${kind} ${entry.id}`;
      if (!entry.title || !entry.objective || !entry.story?.length || entry.story.some((t) => !t)) errors.push(`${where}: title, objective and story are required`);
      if (kind === 'stage' && !entry.hint) errors.push(`${where}: chapters carry a hint`);
      if (!Number.isInteger(entry.science) || entry.science < 0) errors.push(`${where}: science reward`);
      if (!ENDING_TEXT.includes(entry.endingText ?? '')) errors.push(`${where}: unknown endingText ${entry.endingText}`);
      if (kind === 'discovery' && entry.endingText) errors.push(`${where}: discoveries carry no ending text`);
      if (!entry.requirements?.length) errors.push(`${where}: needs at least one requirement`);
      for (const r of entry.requirements ?? []) {
        if (!REQUIREMENT_KINDS.includes(r.kind)) errors.push(`${where}: unknown requirement kind ${r.kind}`);
        if (!Number.isInteger(r.amount) || r.amount < 1) errors.push(`${where}: requirement amount must be a positive integer`);
        if (['BuildingFinished', 'MissionCompleted', 'EndingChosen'].includes(r.kind) && r.amount !== 1) errors.push(`${where}: ${r.kind} amount must be 1`);
        if (r.kind === 'CachesSurveyed' ? r.targets.length !== 0 : r.targets.length === 0) errors.push(`${where}: ${r.kind} targets`);
        if (r.kind === 'MissionCompleted' && r.targets.length !== 1) errors.push(`${where}: one mission per requirement`);
        if (r.kind === 'EndingChosen' && (kind !== 'stage' || JSON.stringify(r.targets) !== JSON.stringify(endingIds))) errors.push(`${where}: EndingChosen lists every ending, on a chapter only`);
        if (r.variants && (r.kind !== 'BuildingFinished' || r.targets.some((t) => !r.variants[t]) || Object.keys(r.variants).length !== r.targets.length))
          errors.push(`${where}: variants are one text per BuildingFinished target`);
        if (!r.label) errors.push(`${where}: requirement label`);
      }
    }
  }
  const choice = STAGES.filter((s) => s.endingText === 'Choice');
  const epilogue = STAGES.filter((s) => s.endingText === 'Epilogue');
  if (choice.length !== 1 || !choice[0].requirements.some((r) => r.kind === 'EndingChosen')) errors.push('exactly one Choice chapter, with the EndingChosen requirement');
  if (STAGES.filter((s) => s.requirements.some((r) => r.kind === 'EndingChosen')).length !== 1) errors.push('only the Choice chapter asks for the ending');
  if (epilogue.length !== 1 || epilogue[0] !== STAGES.at(-1)) errors.push('the last chapter, and only it, carries the epilogue');
  if (!STAGES.at(-1).requirements.some((r) => r.kind === 'MissionCompleted' && r.targets[0] === ENDING_MISSION)) errors.push(`the last chapter requires ${ENDING_MISSION}`);
  if (STAGES.indexOf(choice[0]) >= STAGES.length - 1) errors.push('the choice comes before the final launch');
  const rows = localizationRows();
  const keys = rows.map(([k]) => k);
  if (new Set(keys).size !== keys.length) errors.push('duplicate localization key');
  for (const [key, text] of rows) if (typeof text !== 'string' || !text || /[\r\n]/.test(text)) errors.push(`${key}: single-line text required`);
  return errors;
}

const csvCell = (text) => {
  if (typeof text !== 'string') throw new TypeError('Localization cells must be authored strings.');
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
const csvRow = (id, text) => [id, text, 'Deep Frontier narrative'].map(csvCell).join(',');

// Every id the spec references, grouped by kind.
export function referencedTargets() {
  const all = [...STAGES, ...DISCOVERIES].flatMap((e) => e.requirements);
  const of = (kind) => [...new Set(all.filter((r) => r.kind === kind).flatMap((r) => r.targets))];
  return {templates: of('BuildingFinished'), goods: of('GoodProduced'), recipes: of('RecipeCompleted'), missions: of('MissionCompleted')};
}

async function blueprintFiles(dir) {
  const result = [];
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) result.push(...await blueprintFiles(path));
    else if (entry.name.endsWith('.blueprint.json')) result.push(path);
  }
  return result;
}

// Checks against generated data, shared by the generator and the validator.
export async function checkTargets(dataRoot) {
  const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^\uFEFF/, ''));
  const exists = (path) => access(path).then(() => true, () => false);
  const errors = [];
  const {templates, goods, recipes, missions} = referencedTargets();
  const collection = (await readJson(resolve(dataRoot, NARRATIVE_FILES.buildingCollection))).TemplateCollectionSpec['Blueprints#append'];
  const byTemplate = new Map();
  for (const path of await blueprintFiles(resolve(dataRoot, 'Buildings'))) {
    const value = await readJson(path);
    const name = value.TemplateSpec?.TemplateName;
    if (name) byTemplate.set(name, relative(dataRoot, path).split(sep).join('/').replace(/\.json$/, ''));
  }
  for (const t of templates) {
    if (!byTemplate.has(t)) errors.push(`template ${t} is not generated`);
    else if (!collection.includes(byTemplate.get(t))) errors.push(`template ${t} (${byTemplate.get(t)}) is not in the Iron Teeth building collection`);
  }
  const goodCollection = (await readJson(resolve(dataRoot, NARRATIVE_FILES.goodCollection))).GoodCollectionSpec['Goods#append'];
  for (const g of goods) {
    const own = await exists(resolve(dataRoot, 'Goods', `Good.${g}.blueprint.json`));
    if (!own || !goodCollection.includes(g)) errors.push(`good ${g} is not an authored Iron Teeth good`);
  }
  const recipeIds = new Set();
  for (const file of await readdir(resolve(dataRoot, 'Recipes'))) {
    if (file.endsWith('.blueprint.json')) recipeIds.add((await readJson(resolve(dataRoot, 'Recipes', file))).RecipeSpec.Id);
  }
  for (const r of recipes) if (!recipeIds.has(r)) errors.push(`recipe ${r} is not generated`);
  // Production triggers must name goods some generated recipe produces.
  const produced = new Set();
  for (const file of await readdir(resolve(dataRoot, 'Recipes'))) {
    if (file.endsWith('.blueprint.json')) for (const p of (await readJson(resolve(dataRoot, 'Recipes', file))).RecipeSpec.Products) produced.add(p.Id);
  }
  for (const g of goods) if (!produced.has(g)) errors.push(`good ${g} is produced by no generated recipe, so GoodProduced can never count it`);
  if (!recipeIds.has(CACHE.spec.SurveyRecipeId)) errors.push(`cache survey recipe ${CACHE.spec.SurveyRecipeId} is not generated`);
  const surveyRecipe = [...(await readdir(resolve(dataRoot, 'Recipes')))].includes(`Recipe.${CACHE.spec.SurveyRecipeId}.blueprint.json`)
    ? (await readJson(resolve(dataRoot, 'Recipes', `Recipe.${CACHE.spec.SurveyRecipeId}.blueprint.json`))).RecipeSpec : null;
  if (surveyRecipe && !surveyRecipe.Products.some((p) => p.Id === CACHE.spec.RewardGoodId))
    errors.push(`cache reward ${CACHE.spec.RewardGoodId} must be a product of ${CACHE.spec.SurveyRecipeId}, so the surveying workshop's output accepts it`);
  const padPath = resolve(dataRoot, `${LAUNCH_PAD}.json`);
  if (!await exists(padPath)) errors.push('Launch Pad blueprint is missing');
  else {
    const padMissions = (await readJson(padPath)).RocketLaunchPadSpec?.Missions ?? [];
    for (const m of missions) if (!padMissions.some((p) => p.Id === m)) errors.push(`mission ${m} is not a Launch Pad mission`);
    const final = padMissions.find((p) => p.CompletesStory);
    if (final?.Id !== ENDING_MISSION) errors.push(`the story-completing Launch Pad mission is ${final?.Id}, not ${ENDING_MISSION}`);
  }
  for (const m of missions) if (!ROCKET_MISSIONS.some((r) => r.Id === m)) errors.push(`mission ${m} is not in rocket_program_content.mjs`);
  return errors;
}

export function cacheBlueprint(template) {
  const value = JSON.parse(JSON.stringify(template));
  for (const key of ['TemplateSpec', 'PlaceableBlockObjectSpec', 'LabeledEntitySpec', 'BlockObjectSpec'])
    if (!value[key]) throw new Error(`Narrative: vanilla ${CACHE.template} lacks ${key}`);
  if (value.HumanRecordCacheSpec) throw new Error(`Narrative: vanilla ${CACHE.template} already has HumanRecordCacheSpec`);
  value.TemplateSpec = {...value.TemplateSpec, TemplateName: CACHE.templateName, BackwardCompatibleTemplateNames: []};
  value.PlaceableBlockObjectSpec = {...value.PlaceableBlockObjectSpec, ToolGroupId: CACHE.toolGroup, ToolOrder: CACHE.toolOrder};
  value.LabeledEntitySpec = {...value.LabeledEntitySpec,
    DisplayNameLocKey: 'Building.HumanRecordCache.DisplayName', DescriptionLocKey: 'Building.HumanRecordCache.Description',
    FlavorDescriptionLocKey: 'Building.HumanRecordCache.FlavorDescription', Icon: CACHE.icon};
  value.HumanRecordCacheSpec = {...CACHE.spec};
  // Its own old-world vault model (build_map_objects.py) with a collider over
  // it; the native relic underground part (#Underground) stays.
  if (!value.Children?.['#Model']?.TimbermeshSpec || !value.Children['#Underground'])
    throw new Error(`Narrative: vanilla ${CACHE.template} no longer has #Model and #Underground children`);
  value.Children = {...value.Children,
    '#Model': {TimbermeshSpec: {Model: mapObjectModel(CACHE.templateName)}, CollidersSpec: mapObjectCollider(CACHE.templateName)}};
  checkMapObjectBlueprint(CACHE.templateName, value, '#Model');
  return value;
}

export async function applyNarrative({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^\uFEFF/, ''));
  const writeJson = async (path, value) => { await mkdir(dirname(path), {recursive: true}); await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8'); };
  const fail = (message) => { throw new Error(`Narrative content: ${message}`); };

  const authored = checkAuthoredContent();
  if (authored.length) fail(`authored content is invalid:\n  ${authored.join('\n  ')}`);
  const targets = await checkTargets(dataRoot);
  if (targets.length) fail(`trigger targets are missing:\n  ${targets.join('\n  ')}`);

  // Story configuration (singleton spec).
  await writeJson(resolve(dataRoot, NARRATIVE_FILES.settings), {NarrativeSettingsSpec: narrativeSpec()});

  // Human Record Cache map object.
  const vanilla = resolve(root, ...vanillaRelative);
  const template = await readJson(resolve(vanilla, 'MapEditor', 'Objects', CACHE.template, `${CACHE.template}.blueprint.json`));
  await writeJson(resolve(dataRoot, `${NARRATIVE_FILES.cache}.json`), cacheBlueprint(template));
  const mapCollectionPath = resolve(dataRoot, NARRATIVE_FILES.mapCollection);
  const mapCollection = await readJson(mapCollectionPath);
  const mapList = mapCollection.TemplateCollectionSpec?.['Blueprints#append'];
  if (!Array.isArray(mapList)) fail(`${NARRATIVE_FILES.mapCollection} has no Blueprints#append list`);
  if (mapList.includes(NARRATIVE_FILES.cache)) fail(`${NARRATIVE_FILES.cache} is already collected; the map collection is rewritten fresh by the base generator`);
  for (const path of await blueprintFiles(resolve(dataRoot, 'MapEditor'))) {
    const other = await readJson(path);
    if (!path.includes('HumanRecordCache') && other.PlaceableBlockObjectSpec?.ToolGroupId === CACHE.toolGroup && other.PlaceableBlockObjectSpec.ToolOrder === CACHE.toolOrder)
      fail(`${path} already uses ${CACHE.toolGroup}#${CACHE.toolOrder}`);
  }
  mapList.push(NARRATIVE_FILES.cache);
  await writeJson(mapCollectionPath, mapCollection);

  // Localization: every story string.
  const localizationPath = resolve(dataRoot, NARRATIVE_FILES.localization);
  const text = await readFile(localizationPath, 'utf8');
  if (!text.endsWith('\n')) fail('enUS.csv must end with a newline');
  const ids = new Set(text.split(/\r?\n/).map((line) => line.split(',')[0]));
  const rows = localizationRows();
  for (const [id] of rows) if (ids.has(id)) fail(`enUS.csv already defines ${id}`);
  await writeFile(localizationPath, text + rows.map(([id, value]) => csvRow(id, value)).join('\n') + '\n', 'utf8');
  return {stages: STAGES.length, discoveries: DISCOVERIES.length, endings: ENDINGS.length, rows: rows.length};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const dataRoot = process.argv[2] ? resolve(process.argv[2]) : undefined;
  console.log(JSON.stringify(await applyNarrative(dataRoot ? {dataRoot} : {})));
}
