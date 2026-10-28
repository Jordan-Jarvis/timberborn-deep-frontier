import fs from 'node:fs/promises';

const root = 'C:/Users/Jordan/Documents/TimberbornModding';
const outPath = `${root}/tools/vanilla_1_1_data.json`;
const apiBase = 'https://timberborn.wiki.gg/api.php';
const userAgent = 'TimberbornDeepFrontierResearch/1.0 (local workbook build)';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function api(params) {
  const url = `${apiBase}?${new URLSearchParams({ ...params, format: 'json' })}`;
  const response = await fetch(url, { headers: { 'User-Agent': userAgent } });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText} for ${url}`);
  return response.json();
}

async function categoryMembers(category) {
  const data = await api({ action: 'query', list: 'categorymembers', cmtitle: category, cmlimit: 'max', cmnamespace: '0|14' });
  return (data.query?.categorymembers ?? []).map((x) => ({ title: x.title, ns: x.ns }));
}

async function collectCategoryTree(rootCategory) {
  const queue = [rootCategory];
  const seenCategories = new Set();
  const pageToCategories = new Map();
  while (queue.length) {
    const category = queue.shift();
    if (seenCategories.has(category)) continue;
    seenCategories.add(category);
    const members = await categoryMembers(category);
    for (const member of members) {
      if (member.ns === 14) queue.push(member.title);
      else if (member.ns === 0) {
        if (!pageToCategories.has(member.title)) pageToCategories.set(member.title, new Set());
        pageToCategories.get(member.title).add(category.replace(/^Category:/, ''));
      }
    }
    await sleep(40);
  }
  return { pages: [...pageToCategories.keys()].sort(), pageToCategories, categories: [...seenCategories].sort() };
}

async function fetchWikitextBatch(titles) {
  const result = new Map();
  for (let i = 0; i < titles.length; i += 40) {
    const batch = titles.slice(i, i + 40);
    const data = await api({ action: 'query', prop: 'revisions', rvprop: 'content', rvslots: 'main', titles: batch.join('|') });
    for (const page of Object.values(data.query?.pages ?? {})) {
      const text = page.revisions?.[0]?.slots?.main?.['*'] ?? '';
      result.set(page.title, text);
    }
    await sleep(80);
  }
  return result;
}

function balancedTemplate(text, templateNames) {
  const namePattern = templateNames.map((x) => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
  const start = new RegExp(`\\{\\{\\s*(?:${namePattern})\\b`, 'i').exec(text);
  if (!start) return null;
  let depth = 0;
  for (let i = start.index; i < text.length - 1; i++) {
    if (text[i] === '{' && text[i + 1] === '{') { depth++; i++; continue; }
    if (text[i] === '}' && text[i + 1] === '}') {
      depth--; i++;
      if (depth === 0) return text.slice(start.index, i + 1);
    }
  }
  return null;
}

function templateName(template) {
  return template?.match(/^\{\{\s*([^|}\n]+)/)?.[1]?.trim() ?? '';
}

function templateFields(template) {
  const fields = {};
  if (!template) return fields;
  for (const rawLine of template.split('\n')) {
    const line = rawLine.trim();
    if (!line.startsWith('|')) continue;
    const equals = line.indexOf('=');
    if (equals < 0) continue;
    const key = line.slice(1, equals).trim().toLowerCase();
    const value = line.slice(equals + 1).trim();
    if (key) fields[key] = value;
  }
  return fields;
}

function cleanMarkup(value = '') {
  return value
    .replace(/<br\s*\/?\s*>/gi, '; ')
    .replace(/<!--.*?-->/gs, '')
    .replace(/\{\{r\|([^|}]+)\|([^|}]+)(?:\|[^}]*)?\}\}/gi, '$1 $2')
    .replace(/\{\{icon\|([^|}]+)(?:\|[^}]*)?\}\}/gi, '$1')
    .replace(/\{\{hp(?:\|[^}]*)?\}\}/gi, 'hp')
    .replace(/\bhp[\s)]*\}\}+/gi, 'hp')
    .replace(/\[\[([^]|]+)\|([^]]+)\]\]/g, '$2')
    .replace(/\[\[([^]]+)\]\]/g, '$1')
    .replace(/\{\{[^{}]*\}\}/g, '')
    .replace(/'''?/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function numberOrRaw(value) {
  const cleaned = cleanMarkup(value);
  const match = cleaned.match(/-?\d+(?:\.\d+)?/);
  if (!match) return cleaned || '';
  return Number(match[0]);
}

function parseFootprint(raw) {
  const cleaned = cleanMarkup(raw);
  const match = cleaned.match(/(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)/i);
  return { raw: cleaned, width: match ? Number(match[1]) : '', length: match ? Number(match[2]) : '', tiles: match ? Number(match[1]) * Number(match[2]) : '' };
}

function parseQuantityIcons(raw = '') {
  const result = [];
  const re = /(?:(\d+(?:\.\d+)?)\s*)?\{\{\s*icon\s*\|\s*([^|}]+)(?:\|[^}]*)?\}\}/gi;
  let match;
  while ((match = re.exec(raw))) {
    result.push(`${match[1] ? match[1] : 1} ${cleanMarkup(match[2])}`);
  }
  return result.join('; ');
}

function parseRecipeFields(fields, buildingKind = '') {
  const numbers = new Set();
  for (const key of Object.keys(fields)) {
    const match = key.match(/^(?:recipe|consumes|produces|hours|storage)(\d+)$/);
    if (match) numbers.add(Number(match[1]));
  }
  const hasBareRecipe = fields.consumes || fields.produces || fields.hours;
  if (hasBareRecipe) numbers.add(0);
  const recipes = [];
  for (const n of [...numbers].sort((a, b) => a - b)) {
    const suffix = n === 0 ? '' : n;
    const hasRecipeData = fields[`recipe${suffix}`] || fields[`consumes${suffix}`] || fields[`produces${suffix}`] || fields[`hours${suffix}`];
    if (!hasRecipeData) continue;
    const rawProduces = fields[`produces${suffix}`] ?? '';
    const rawConsumes = fields[`consumes${suffix}`] ?? '';
    const cleanedProduces = cleanMarkup(rawProduces).replace(/\}\}+/g, '').trim();
    const cleanedConsumes = cleanMarkup(rawConsumes).replace(/\}\}+/g, '').trim();
    const name = fields[`recipe${suffix}`]
      ? cleanMarkup(fields[`recipe${suffix}`])
      : (/(?:power|Power)/.test(buildingKind) || /^\s*\d+(?:\.\d+)?\s*(?:\{\{hp\}\}|hp)?\s*$/i.test(rawProduces)
        ? 'Power output'
        : 'Default');
    const fuel = fields.fuel ?? fields.Fuel ?? '';
    const outputs = parseQuantityIcons(rawProduces) || (name === 'Power output' && cleanedProduces ? `${cleanedProduces} hp` : cleanedProduces);
    recipes.push({
      name,
      inputs: parseQuantityIcons(rawConsumes) || cleanedConsumes,
      outputs,
      cycleHours: cleanMarkup(fields[`hours${suffix}`] ?? ''),
      storage: cleanMarkup(fields[`storage${suffix}`] ?? ''),
      fuel: cleanMarkup(fuel),
      rawConsumes: cleanedConsumes,
      rawProduces: cleanedProduces,
    });
  }
  return recipes;
}

const materialKeys = new Set([
  'algae', 'antidotes', 'badwater', 'biofuel', 'books', 'bot chassis', 'bot heads', 'bot limbs', 'canola oil',
  'canola seeds', 'cassava', 'catalyst', 'cattail flour', 'cattail roots', 'chestnuts', 'coffee beans', 'corn',
  'dandelions', 'dirt', 'eggplants', 'explosives', 'extract', 'fireworks', 'gears', 'grease', 'logs', 'maple syrup',
  'metal blocks', 'metal parts', 'mushrooms', 'paper', 'pine resin', 'planks', 'potatoes', 'punch cards',
  'scrap metal', 'soybeans', 'spadderdock', 'treated planks', 'water', 'wheat', 'wheat flour', 'wheat flour',
]);

function buildMaterials(fields) {
  const costs = [];
  for (const [key, value] of Object.entries(fields)) {
    if (!materialKeys.has(key)) continue;
    const clean = cleanMarkup(value);
    if (clean) costs.push(`${key.replace(/\b\w/g, (c) => c.toUpperCase())}: ${clean}`);
  }
  return costs.join('; ');
}

function pageKind(text) {
  for (const name of ['Workplace', 'Structure', 'Housing', 'Decoration', 'Well-Being', 'Storage', 'Monument', 'Good', 'Plant', 'Crop']) {
    if (balancedTemplate(text, [name])) return name;
  }
  return '';
}

function parseBuilding(title, text, categories) {
  const kind = pageKind(text);
  if (!['Workplace', 'Structure', 'Housing', 'Decoration', 'Well-Being', 'Storage', 'Monument'].includes(kind)) return null;
  const fields = templateFields(balancedTemplate(text, [kind]));
  const footprint = parseFootprint(fields.footprint ?? '');
  const recipes = parseRecipeFields(fields, fields['tool group'] ?? '');
  const rawPowerOutput = fields.produces ?? fields.produces1 ?? '';
  const powerOutputMatch = cleanMarkup(rawPowerOutput).replace(/\}\}+/g, '').trim().match(/^(\d+(?:\.\d+)?)(?:\s*hp)?$/i);
  const recipePowerOutputMatch = recipes.find((recipe) => recipe.name === 'Power output')?.outputs?.match(/(\d+(?:\.\d+)?)\s*hp/i);
  const categoryList = [...(categories.get(title) ?? [])].filter((x) => !x.includes('Goods')).sort();
  return {
    name: title,
    infobox: kind,
    categories: categoryList.join('; '),
    faction: cleanMarkup(fields.faction ?? '') || 'Common / all factions',
    width: footprint.width,
    length: footprint.length,
    footprint: footprint.raw,
    footprintTiles: footprint.tiles,
    height: cleanMarkup(fields.height ?? ''),
    workers: numberOrRaw(fields.workers ?? ''),
    powerHp: numberOrRaw(fields.power ?? ''),
    powerOutputHp: powerOutputMatch ? Number(powerOutputMatch[1]) : (recipePowerOutputMatch ? Number(recipePowerOutputMatch[1]) : ''),
    scienceUnlock: numberOrRaw(fields.unlock ?? ''),
    botUnlock: numberOrRaw(fields.unlockbot ?? ''),
    materials: buildMaterials(fields),
    recipes,
    buildable: fields.unlock !== undefined && (buildMaterials(fields) !== '' || fields.unlock === '0'),
    availability: fields.unlock === '-1' ? 'Map/preplaced object' : (fields.unlockbot === '0' ? 'Pre-unlocked' : 'Build menu'),
    flags: [
      fields['transmit-power'] ? `transmit-power=${cleanMarkup(fields['transmit-power'])}` : '',
      fields['water-dependent'] ? `water-dependent=${cleanMarkup(fields['water-dependent'])}` : '',
      fields.solid ? `solid=${cleanMarkup(fields.solid)}` : '',
      fields['ground-only'] ? `ground-only=${cleanMarkup(fields['ground-only'])}` : '',
      fields.capacity ? `capacity=${cleanMarkup(fields.capacity)}` : '',
      fields.fuel ? `fuel=${cleanMarkup(fields.fuel)}` : '',
    ].filter(Boolean).join('; '),
    source: `https://timberborn.wiki.gg/wiki/${encodeURIComponent(title.replaceAll(' ', '_'))}`,
    rawTemplate: cleanMarkup(balancedTemplate(text, [kind]) ?? ''),
    status: ['footprint', 'height', 'unlock'].every((key) => fields[key] !== undefined) ? 'Wiki infobox complete' : 'Wiki infobox has missing field',
  };
}

function parseItem(title, text, categories) {
  const kind = pageKind(text);
  if (!['Good', 'Plant', 'Crop'].includes(kind)) return null;
  const fields = templateFields(balancedTemplate(text, [kind]));
  const categoryList = [...(categories.get(title) ?? [])].sort();
  return {
    name: title,
    infobox: kind,
    categories: categoryList.join('; '),
    faction: cleanMarkup(fields.faction ?? '') || 'Common / all factions',
    type: cleanMarkup(fields.type ?? ''),
    source: cleanMarkup(fields.source ?? ''),
    storage: cleanMarkup(fields.storage ?? ''),
    weight: numberOrRaw(fields.weight ?? ''),
    satisfies: cleanMarkup(fields.satisfies ?? ''),
    produces: cleanMarkup(fields.produces ?? ''),
    consumedBy: cleanMarkup(fields['consumed by'] ?? ''),
    sourceUrl: `https://timberborn.wiki.gg/wiki/${encodeURIComponent(title.replaceAll(' ', '_'))}`,
    status: kind === 'Good' ? 'Wiki good infobox' : 'Wiki plant/crop infobox',
    rawTemplate: cleanMarkup(balancedTemplate(text, [kind]) ?? ''),
  };
}

const buildingTree = await collectCategoryTree('Category:Constructions');
const itemTree = await collectCategoryTree('Category:Goods');
const buildingTexts = await fetchWikitextBatch(buildingTree.pages);
const itemTexts = await fetchWikitextBatch(itemTree.pages);

const buildings = [];
for (const title of buildingTree.pages) {
  const parsed = parseBuilding(title, buildingTexts.get(title) ?? '', buildingTree.pageToCategories);
  if (parsed) buildings.push(parsed);
}
const items = [];
for (const title of itemTree.pages) {
  const parsed = parseItem(title, itemTexts.get(title) ?? '', itemTree.pageToCategories);
  if (parsed) items.push(parsed);
}

const recipes = [];
for (const building of buildings) {
  for (const recipe of building.recipes) {
    recipes.push({
      building: building.name,
      faction: building.faction,
      recipe: recipe.name,
      inputs: recipe.inputs,
      outputs: recipe.outputs,
      cycleHours: recipe.cycleHours,
      powerHp: building.powerHp,
      powerOutputHp: building.powerOutputHp,
      workers: building.workers,
      fuel: recipe.fuel,
      storage: recipe.storage,
      source: building.source,
      rawConsumes: recipe.rawConsumes,
      rawProduces: recipe.rawProduces,
    });
  }
}

const payload = {
  schemaVersion: 1,
  gameVersion: 'Timberborn 1.1.x (local install 1.1.2.8)',
  source: 'https://timberborn.wiki.gg/',
  checkedDate: '2026-10-17',
  buildingCategoryCount: buildingTree.categories.length,
  itemCategoryCount: itemTree.categories.length,
  buildingPageCount: buildingTree.pages.length,
  itemPageCount: itemTree.pages.length,
  buildings: buildings.sort((a, b) => a.name.localeCompare(b.name)),
  items: items.sort((a, b) => a.name.localeCompare(b.name)),
  recipes,
  notes: [
    'Building and item scope is derived from the official wiki Category:Constructions and Category:Goods trees.',
    'Infobox values are preserved as raw strings where the game uses a conditional or faction-specific value.',
    'The wiki is the canonical public reference; local asset/assembly inspection remains a secondary verification step.',
    'Pages that are redirects, navigation pages, obsolete stubs, or category indexes are excluded when they have no recognized data infobox.',
  ],
};
await fs.writeFile(outPath, JSON.stringify(payload, null, 2), 'utf8');
console.log(JSON.stringify({ outPath, buildings: buildings.length, items: items.length, recipes: recipes.length, buildingPages: buildingTree.pages.length, itemPages: itemTree.pages.length }, null, 2));

