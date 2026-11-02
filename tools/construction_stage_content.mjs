// Construction sites of every Deep Frontier building (tools/construction_stages.json,
// docs/asset-pipeline.md "Construction stages").
//
// Native contract (Timberborn 1.1.2.8, decompiled ConstructionSiteProgressVisualizer and
// BuildingModel): the direct children of BuildingModelSpec.UnfinishedModelName are the
// stages, child 0 the construction base shown until the site gets its first material
// (ConstructionSite.WasStarted), then the last stage whose ProgressThreshold the build
// progress has reached; ProgressThresholds.Length must equal the child count minus one.
// Every vanilla Iron Teeth workshop nests a vanilla ConstructionBase<X>x<Y> blueprint and
// has one ConstructionStage0 model (a dark timber or BaseMetal frame on a Dirt patch) with
// ProgressThresholds [0.0]. Deep Frontier buildings used to ship a byte copy of the
// finished model as their only stage, so a site looked finished from the moment it was
// placed.
//
// Ownership: the building generators drop any #Unfinished they cloned from a vanilla
// template (unbindConstructionSite), and this pass, run once at the end of canonical
// generation (create_vertical_slice_content.mjs) or standalone on a Data root
//   node tools/construction_stage_content.mjs [dataRoot]
// binds, for every generated building, the vanilla base and the generated stage that
// tools/asset-pipeline/build_construction_stages.py recorded in the manifest, and copies
// the stage mesh into Data. A building without a manifest entry, or whose blocks changed
// since its stage was generated, fails here: rebuild its stage first. Authored stages
// (the Fisher Flag) are checked, preview-only tool templates (steel leg decks) are left
// as their generator wrote them. tools/asset-pipeline/validate_construction_exports.py checks the result.
import {readFile, writeFile, copyFile, mkdir, access} from 'node:fs/promises';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {join, resolve, dirname, basename} from 'node:path';
import {fileURLToPath} from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const CONFIG = JSON.parse(readFileSync(join(repo, 'tools/construction_stages.json'), 'utf8'));
const UNFINISHED = '#Unfinished';

function fail(message) { throw new Error(`construction_stage_content: ${message}`); }

// For the building generators: the construction site is bound here, not by them.
export function unbindConstructionSite(value) {
  if (value.BuildingModelSpec?.UnfinishedModelName !== UNFINISHED) fail('unexpected UnfinishedModelName');
  delete value.Children[UNFINISHED];
  delete value.ConstructionSiteProgressVisualizerSpec;
}

// Same string as construction_stage_massing.blocks_sha (Python json.dumps, compact separators).
export function blocksSha(spec) {
  const payload = [[spec.Size.X, spec.Size.Y, spec.Size.Z], spec.BaseZ ?? 0, spec.Blocks.map((b) => [b.Occupations, b.MatterBelow])];
  return createHash('sha256').update(JSON.stringify(payload)).digest('hex');
}

export function kindOf(id) {
  if (Object.hasOwn(CONFIG.authored, id)) return 'authored';
  if (Object.keys(CONFIG.previewOnly).some((prefix) => id.startsWith(prefix))) return 'previewOnly';
  return 'generated';
}

async function exists(path) {
  try { await access(path); return true; } catch { return false; }
}

// Deep Frontier building templates: TemplateCollection.Buildings.IronTeeth entries with a
// BuildingModelSpec whose finished model is in this Data tree (construction_stage_massing.buildings).
export async function constructionSiteBuildings(dataRoot) {
  const collection = JSON.parse((await readFile(join(dataRoot, 'TemplateCollections', 'TemplateCollection.Buildings.IronTeeth.blueprint.json'), 'utf8')).replace(/^﻿/, ''));
  const paths = collection.TemplateCollectionSpec?.['Blueprints#append'];
  if (!Array.isArray(paths) || !paths.length) fail('TemplateCollection.Buildings.IronTeeth lists no blueprints');
  const result = [];
  for (const path of paths) {
    const file = join(dataRoot, `${path}.json`);
    const value = JSON.parse((await readFile(file, 'utf8')).replace(/^﻿/, ''));
    if (!value.BuildingModelSpec) continue;
    const id = basename(path).replace('.IronTeeth.blueprint', '');
    const finished = value.Children?.[value.BuildingModelSpec.FinishedModelName]?.TimbermeshSpec?.Model;
    if (!finished) {
      if (kindOf(id) !== 'previewOnly') fail(`${id}: the finished model has no TimbermeshSpec`);
    } else if (!await exists(join(dataRoot, `${finished}.timbermesh`))) continue;   // vanilla model, vanilla stage
    result.push({id, file, value, finished, kind: kindOf(id)});
  }
  return result;
}

export function baseChild(base) {
  const [x, y, z] = base.offset;
  const child = {BlueprintPath: base.blueprint};
  if (x || y || z) {
    child.Modification = {TransformSpec: {Position: {X: x, Y: z, Z: y}, Rotation: {X: 0, Y: 0, Z: 0}, Scale: {X: 1, Y: 1, Z: 1}}};
  }
  return [`${base.name}#nested`, child];
}

export function constructionSite(entry) {
  const [name, base] = baseChild(entry.base);
  return {
    thresholds: [...CONFIG.progressThresholds],
    unfinished: {Children: {
      [name]: base,
      ConstructionStage0: {TimbermeshSpec: {Model: entry.stage},
        CollidersSpec: {BoxColliders: entry.colliders, SphereColliders: [], CapsuleColliders: []}},
    }},
  };
}

function checkAuthored(id, value) {
  const children = value.Children?.[UNFINISHED]?.Children ?? {};
  const names = Object.keys(children);
  const finished = value.Children[value.BuildingModelSpec.FinishedModelName].TimbermeshSpec.Model;
  if (names.length !== 2 || !names[0].startsWith('ConstructionBase') || names[1] !== 'ConstructionStage0')
    fail(`${id}: an authored construction site needs a ConstructionBase and ConstructionStage0, found ${names}`);
  if (children.ConstructionStage0.TimbermeshSpec?.Model === finished) fail(`${id}: the authored stage is the finished model`);
  if (JSON.stringify(value.ConstructionSiteProgressVisualizerSpec?.ProgressThresholds) !== JSON.stringify(CONFIG.progressThresholds))
    fail(`${id}: an authored construction site needs ProgressThresholds ${JSON.stringify(CONFIG.progressThresholds)}`);
}

export async function applyConstructionStages({dataRoot = join(repo, 'src/DeepFrontier/Data'),
  exportRoot = join(repo, CONFIG.exportRoot), manifestPath = join(repo, CONFIG.manifest)} = {}) {
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  const buildings = await constructionSiteBuildings(dataRoot);
  const generated = new Set(buildings.filter((b) => b.kind === 'generated').map((b) => b.id));
  const stale = Object.keys(manifest.stages).filter((id) => !generated.has(id));
  if (stale.length) fail(`the manifest has stages for ${stale.join(', ')}, which are not generated Deep Frontier buildings; rebuild with build_construction_stages.py -- --models all`);
  const rows = [];
  for (const {id, file, value, finished, kind} of buildings) {
    if (kind === 'previewOnly') continue;
    if (kind === 'authored') { checkAuthored(id, value); continue; }
    if (value.Children[UNFINISHED] || value.ConstructionSiteProgressVisualizerSpec)
      fail(`${id}: its generator still writes #Unfinished or ConstructionSiteProgressVisualizerSpec; call unbindConstructionSite instead`);
    const entry = manifest.stages[id];
    if (!entry) fail(`${id}: no generated construction stage; run tools/asset-pipeline/build_construction_stages.py -- --models ${id}`);
    if (entry.finished !== finished) fail(`${id}: the stage was generated for ${entry.finished}, the blueprint shows ${finished}`);
    if (entry.blocksSha !== blocksSha(value.BlockObjectSpec))
      fail(`${id}: its blocks changed since its construction stage was generated; run tools/asset-pipeline/build_construction_stages.py -- --models ${id}`);
    const source = join(exportRoot, 'Data', `${entry.stage}.timbermesh`);
    const bytes = await readFile(source);
    if (createHash('sha256').update(bytes).digest('hex') !== entry.exportSha256) fail(`${id}: ${source} differs from the manifest`);
    const target = join(dataRoot, `${entry.stage}.timbermesh`);
    await mkdir(dirname(target), {recursive: true});
    await copyFile(source, target);
    const site = constructionSite(entry);
    value.ConstructionSiteProgressVisualizerSpec = {ProgressThresholds: site.thresholds};
    value.Children[UNFINISHED] = site.unfinished;
    await writeFile(file, JSON.stringify(value, null, 2) + '\n');
    rows.push({id, base: entry.base.name, frame: entry.frame, triangles: entry.triangles});
  }
  console.log(`Construction stages: ${rows.length} generated sites bound, ` +
    `${buildings.filter((b) => b.kind === 'authored').length} authored, ${buildings.filter((b) => b.kind === 'previewOnly').length} preview-only.`);
  return rows;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await applyConstructionStages(process.argv[2] ? {dataRoot: resolve(process.argv[2])} : {});
}
