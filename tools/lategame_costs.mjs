// Construction cost rule for the full-size late-game buildings.
//
// The rule and each building's tier live in tools/building_construction_costs.json
// (lategameRule, lategameTier); the size comes from the study registration the
// blueprint is generated from (outputs/lategame-studies/<Id>-registration.json):
//   groundCells = occupied cells on layer 0 (the foundation slab)
//   builtCells  = every occupied cell (the built mass)
// Foundation: Concrete = groundCells x tier.concretePerGroundCell.
// Superstructure: each good = builtCells / 100 x tier.per100BuiltCells[good].
// Every amount rounds to the nearest multiple of 5 (minimum 5).
// Gate: lategameGates[id] adds explicit goods that prove the previous stage
// (DeepMine's DeepAlloy from the finite drill phase); a gate good must not
// also come from the rule.
// The tier is fixed by the building's science unlock (tier.scienceMax bands);
// tools/audit_progression.mjs checks the band against the generated blueprint.
//
// CLI:
//   node tools/lategame_costs.mjs           print the rule's costs
//   node tools/lategame_costs.mjs --check   fail when a catalog row differs
//   node tools/lategame_costs.mjs --write   rewrite the catalog rows the rule owns
import {readFile, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';

const root = new URL('../', import.meta.url);
const read = async (path) => JSON.parse(await readFile(new URL(path, root), 'utf8'));
const catalogPath = new URL('tools/building_construction_costs.json', root);

export const catalog = JSON.parse(await readFile(catalogPath, 'utf8'));
export const rule = catalog.lategameRule;
export const LATEGAME_IDS = (await read('tools/lategame_batches.json')).integrated;

const tierNames = Object.keys(rule?.tiers ?? {});
if (!tierNames.length) throw new Error('building_construction_costs.json: lategameRule.tiers is missing');
for (const [i, name] of tierNames.entries()) {
  const tier = rule.tiers[name];
  const previous = i ? rule.tiers[tierNames[i - 1]].scienceMax : -1;
  const last = i === tierNames.length - 1;
  if (last ? tier.scienceMax !== null : !(Number.isInteger(tier.scienceMax) && tier.scienceMax > previous)) {
    throw new Error(`lategameRule tier ${name}: scienceMax must rise through the tiers and be null on the last`);
  }
  if (!(tier.concretePerGroundCell >= 0)) throw new Error(`lategameRule tier ${name}: concretePerGroundCell missing`);
  for (const [good, rate] of Object.entries(tier.per100BuiltCells ?? {})) {
    if (good === 'Concrete' || !(rate > 0)) throw new Error(`lategameRule tier ${name}: invalid superstructure rate ${good}=${rate}`);
  }
}
for (const id of Object.keys(catalog.lategameGates ?? {})) {
  if (!LATEGAME_IDS.includes(id)) throw new Error(`lategameGates: ${id} is not an integrated late-game building`);
}
// Planned buildings (frontier_progression.json) declare their tier ahead of
// integration; the rule prices them once their registration exists.
export const PLANNED = (await read('tools/frontier_progression.json')).plannedBuildings;
export function tierForScience(science) {
  return tierNames.find((name) => rule.tiers[name].scienceMax === null || science <= rule.tiers[name].scienceMax);
}
for (const planned of PLANNED) {
  if (catalog.lategameTier[planned.id] !== planned.costTier) throw new Error(`${planned.id}: lategameTier must equal the planned costTier ${planned.costTier}`);
  if (tierForScience(planned.scienceUnlock) !== planned.costTier) throw new Error(`${planned.id}: science ${planned.scienceUnlock} lies outside tier ${planned.costTier}`);
}
const expectedTierIds = new Set([...LATEGAME_IDS, ...PLANNED.map((p) => p.id)]);
const ids = Object.keys(catalog.lategameTier ?? {});
if (ids.sort().join() !== [...expectedTierIds].sort().join()) {
  throw new Error('building_construction_costs.json: lategameTier must list exactly the integrated and planned late-game buildings');
}

const round5 = (value) => Math.max(5, Math.round(value / 5) * 5);

export async function lategameSize(id) {
  const registration = await read(`outputs/lategame-studies/${id}-registration.json`);
  if (registration.ident !== id) throw new Error(`Registration identity mismatch: ${id}`);
  return {builtCells: registration.occupied.length, groundCells: registration.occupied.filter((c) => c[2] === 0).length,
    footprint: registration.footprint, height: registration.height};
}

// [[good, amount], ...] in the catalog's row format.
export async function lategameCost(id) {
  const tierName = catalog.lategameTier[id];
  const tier = rule.tiers[tierName];
  if (!tier) throw new Error(`${id}: unknown late-game tier ${tierName}`);
  const {builtCells, groundCells} = await lategameSize(id);
  const rows = Object.entries(tier.per100BuiltCells).map(([good, rate]) => [good, round5(builtCells / 100 * rate)]);
  if (tier.concretePerGroundCell > 0) rows.push(['Concrete', round5(groundCells * tier.concretePerGroundCell)]);
  for (const [good, amount] of catalog.lategameGates[id] ?? []) {
    if (rows.some(([g]) => g === good) || !Number.isInteger(amount) || amount <= 0) throw new Error(`${id}: invalid gate ${good}=${amount}`);
    rows.push([good, amount]);
  }
  return rows;
}

// The catalog keeps one line per building and per tier.
function formatCatalog(value) {
  const known = ['status', 'lategameRule', 'lategameTier', 'lategameGates', 'buildings'];
  const extra = Object.keys(value).filter((key) => !known.includes(key));
  if (extra.length) throw new Error('Unexpected catalog keys: ' + extra.join(', '));
  const indent = (text, pad) => text.split('\n').map((line, i) => (i ? pad : '') + line).join('\n');
  const map = (object) => '{\n' + Object.entries(object).map(([k, v]) => `    ${JSON.stringify(k)}: ${JSON.stringify(v)}`).join(',\n') + '\n  }';
  const {tiers, ...ruleText} = value.lategameRule;
  const ruleBody = JSON.stringify(ruleText, null, 2).slice(0, -2) + ',\n  "tiers": ' + map(tiers) + '\n}';
  return '{\n' + [
    `  "status": ${JSON.stringify(value.status)}`,
    `  "lategameRule": ${indent(ruleBody, '  ')}`,
    `  "lategameTier": ${map(value.lategameTier)}`,
    `  "lategameGates": ${map(value.lategameGates)}`,
    `  "buildings": ${map(value.buildings)}`,
  ].join(',\n') + '\n}\n';
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const mode = process.argv[2] ?? '';
  if (!['', '--check', '--write'].includes(mode)) throw new Error('Usage: node tools/lategame_costs.mjs [--check|--write]');
  // Rows the rule owns: integrated buildings whose generator reads this catalog.
  // An integrated planned building reads its row from this catalog too.
  const owned = LATEGAME_IDS.filter((id) => Object.hasOwn(catalog.buildings, id) || PLANNED.some((p) => p.id === id));
  const mismatches = [];
  for (const id of LATEGAME_IDS) {
    const size = await lategameSize(id);
    const cost = await lategameCost(id);
    const current = catalog.buildings[id];
    const same = current && JSON.stringify(current) === JSON.stringify(cost);
    console.log(`${id.padEnd(28)} ${catalog.lategameTier[id]} ${String(size.builtCells).padStart(5)} built ${String(size.groundCells).padStart(4)} ground  ${cost.map(([g, a]) => `${a} ${g}`).join(', ')}${current ? (same ? '' : '  (catalog differs)') : '  (cost authored outside this catalog)'}`);
    if (owned.includes(id) && !same) mismatches.push(id);
    if (mode === '--write' && owned.includes(id)) catalog.buildings[id] = cost;
  }
  for (const p of PLANNED.filter((p) => !LATEGAME_IDS.includes(p.id))) console.log(`${p.id.padEnd(28)} ${p.costTier} planned; priced by the rule once its registration is integrated`);
  if (mode === '--write') {
    await writeFile(catalogPath, formatCatalog(catalog), 'utf8');
    console.log(`Wrote ${owned.length} rule-owned rows.`);
  } else if (mode === '--check' && mismatches.length) {
    throw new Error('Catalog rows differ from the late-game cost rule: ' + mismatches.join(', '));
  }
}
