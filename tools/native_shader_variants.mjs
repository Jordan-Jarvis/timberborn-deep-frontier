// Deep Frontier variants of three native Timberborn 1.1.2.8 shader graphs, so
// radioactive water and irradiated ground are drawn by the native surfaces
// themselves instead of overlay meshes.
//
// Native mechanism (decompiled Timberborn.WaterSystemRendering and
// Timberborn.TerrainSystemRendering 1.1.2.8, graphs from the official modding
// tools in vendor/.../ImportedAssets/Editor/Resources/Shaders):
// - water: UpdateWaterTexturesTask writes byte(255 * WaterColumn.Contamination)
//   into DataTextureArray<byte> (R8, layer = column index, pixel x + y * width),
//   WaterColumnPostprocessor publishes it as the global texture arrays
//   _OldContaminations/_NewContaminations, and the WaterContamination subgraph
//   samples them (old/new lerped by _TickProgress, blended with linked
//   neighbours) and colours the surface: Lerp(clean albedo, contamination
//   colour, contamination), plus emission, metallic, smoothness and normal.
// - soil: TerrainMaterialMap keeps an RG16 Texture2DArray (R old, G new,
//   layer = terrain z, pixel x + y * width) as the global _ContaminationMap,
//   and the SoilContaminationVisualization subgraph blends the soil
//   contamination texture into the terrain albedo with one Lerp.
// The native texture has no spare channel, so each variant is the native graph
// with a second instance of the graph's own native contamination subgraph fed
// from Deep Frontier's texture arrays (same layout and update scheme) and its
// own colours, lerped over the native result. Everything else (reflections,
// transparency, foam, flow, waterfalls, level visibility, terrain layers) is
// the unchanged native graph. A global multi_compile keyword gates the extra
// subgraph, so with no radiation the variant compiles to the native code.
// Shader-feature keywords that the native materials enable become
// multi_compile: the bundle has no material that would keep those variants.
//
// Output: src/DeepFrontier/AssetBundles/Resources/Shaders/DeepFrontier/*.shadergraph
// (bundled by the official Mod Builder). Untouched native objects are written
// back byte for byte; only the graph object, the converted keywords and the new
// objects are serialised.
//
//   node tools/native_shader_variants.mjs           # writes the variants
//   node tools/native_shader_variants.mjs --check   # fails if they are stale
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
export const NATIVE_SHADER_DIR = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources', 'Shaders');
export const VARIANT_DIR = resolve(root, 'src', 'DeepFrontier', 'AssetBundles', 'Resources', 'Shaders', 'DeepFrontier');
export const SHADER_PATH = 'DeepFrontier';

// Names shared with src/DeepFrontier/Scripts/Radiation/RadiationShading.cs.
export const WATER = {
  keyword: '_DEEP_FRONTIER_RADIOACTIVE_WATER',
  oldMap: '_DFOldRadioactivity',
  newMap: '_DFNewRadioactivity',
  colors: {
    'Base Contamination Color A': '_DFRadioactiveBaseColorA',
    'Base Contamination Color B': '_DFRadioactiveBaseColorB',
    'Detail Contamination Color A': '_DFRadioactiveDetailColorA',
    'Detail Contamination Color B': '_DFRadioactiveDetailColorB',
  },
};
export const SOIL = {
  keyword: '_DEEP_FRONTIER_IRRADIATED_SOIL',
  map: '_DFIrradiatedSoilMap',
  color: '_DFIrradiatedSoilColor',
};

// Native materials (resources.assets 1.1.2.8) and the keywords they enable:
// PhysicalWater_Opaque/_Transparent [_CALCULATE_OUTFLOWS]; Grass
// [_USELAYERTOOL], Cliff [_SAMPLE_SPLATMAP _USELAYERTOOL _USE_TRIPLANAR_SPLATMAP],
// CliffEdge [_SAMPLE_SPLATMAP _USELAYERTOOL], SlopeCliff [_SAMPLE_SPLATMAP
// _USE_TRIPLANAR_SPLATMAP], SlopeCliffEdge [_SAMPLE_SPLATMAP].
export const VARIANTS = [
  {name: 'RadioactiveWaterURP_Opaque', native: 'PhysicalWaterURP_Opaque', kind: 'water', multiCompile: ['_CALCULATE_OUTFLOWS']},
  {name: 'RadioactiveWaterURP_Transparent', native: 'PhysicalWaterURP_Transparent', kind: 'water', multiCompile: ['_CALCULATE_OUTFLOWS']},
  {name: 'IrradiatedTerrainURP', native: 'TerrainURP', kind: 'soil', multiCompile: ['_USE_TRIPLANAR_SPLATMAP', '_SAMPLE_SPLATMAP', '_USELAYERTOOL']},
];

// Graph defaults only; RadiationShading sets the colours on the materials.
const WATER_DEFAULTS = {
  '_DFRadioactiveBaseColorA': {r: 0.50, g: 0.56, b: 0.04, a: 0},
  '_DFRadioactiveBaseColorB': {r: 0.86, g: 0.92, b: 0.08, a: 0},
  '_DFRadioactiveDetailColorA': {r: 0.55, g: 0.68, b: 0.12, a: 0},
  '_DFRadioactiveDetailColorB': {r: 0.62, g: 0.72, b: 0.16, a: 0},
};
const SOIL_DEFAULT = {r: 2.0, g: 4.7, b: 2.3, a: 1};

// ------------------------------------------------------------ serialisation

// Top-level objects of a Unity multi-JSON graph, as exact source text.
function splitObjects(text) {
  const chunks = [];
  let depth = 0, inString = false, escaped = false, start = -1;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (c === '\\') escaped = true;
      else if (c === '"') inString = false;
      continue;
    }
    if (c === '"') inString = true;
    else if (c === '{') { if (depth++ === 0) start = i; }
    else if (c === '}') {
      if (--depth === 0) chunks.push(text.slice(start, i + 1));
      if (depth < 0) throw new Error('unbalanced braces');
    } else if (depth === 0 && !/\s/.test(c)) throw new Error(`text outside objects at ${i}`);
  }
  if (depth !== 0 || inString) throw new Error('truncated graph');
  return chunks;
}

// Re-serialised objects must not hold integers beyond double precision.
function requireSafeNumbers(text, what) {
  let inString = false, escaped = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inString) {
      if (escaped) escaped = false; else if (c === '\\') escaped = true; else if (c === '"') inString = false;
      continue;
    }
    if (c === '"') { inString = true; continue; }
    if (/[-0-9]/.test(c)) {
      const token = /^-?\d+(\.\d+)?([eE][+-]?\d+)?/.exec(text.slice(i))[0];
      const value = Number(token);
      if (!Number.isFinite(value) || (/^-?\d+$/.test(token) && !Number.isSafeInteger(value)))
        throw new Error(`${what}: number ${token} cannot be re-serialised exactly`);
      i += token.length - 1;
    }
  }
}

class Graph {
  // library: a native graph that lends utility-node templates (Add, Maximum,
  // Keyword) this graph does not contain.
  constructor(text, seed, library = null) {
    this.seed = seed;
    this.library = library;
    this.chunks = splitObjects(text.replace(/^﻿/, '')).map(source => ({source, object: JSON.parse(source), dirty: false}));
    this.byId = new Map();
    for (const chunk of this.chunks) {
      const id = chunk.object.m_ObjectId;
      if (!id || this.byId.has(id)) throw new Error(`missing or duplicate object id ${id}`);
      this.byId.set(id, chunk);
    }
    this.data = this.chunks[0].object;
    if (this.data.m_Type !== 'UnityEditor.ShaderGraph.GraphData') throw new Error('first object is not GraphData');
    this.touch(this.data);
    this.newNodes = new Set();
  }
  get(id) { const chunk = this.byId.get(id); if (!chunk) throw new Error(`unknown object ${id}`); return chunk.object; }
  touch(object) {
    const chunk = this.byId.get(object.m_ObjectId);
    if (!chunk.dirty) { requireSafeNumbers(chunk.source, object.m_ObjectId); chunk.dirty = true; }
  }
  id(key) { return createHash('sha256').update(`${this.seed}:${key}`).digest('hex').slice(0, 32); }
  guid(key) { const h = this.id(`guid:${key}`); return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20, 32)}`; }
  add(object) {
    if (this.byId.has(object.m_ObjectId)) throw new Error(`duplicate object id ${object.m_ObjectId}`);
    const chunk = {source: null, object, dirty: true};
    this.chunks.push(chunk);
    this.byId.set(object.m_ObjectId, chunk);
    return object;
  }
  copy(object, key, owner = this) {
    requireSafeNumbers(owner.byId.get(object.m_ObjectId).source, object.m_ObjectId);
    return {...structuredClone(object), m_ObjectId: this.id(key)};
  }
  nodes() { return this.data.m_Nodes.map(ref => this.get(ref.m_Id)); }
  type(object) { return object.m_Type.split('.').pop(); }
  slots(node) { return node.m_Slots.map(ref => this.get(ref.m_Id)); }
  slot(node, name, direction) {
    const matches = this.slots(node).filter(s => s.m_DisplayName === name && s.m_SlotType === direction);
    if (matches.length !== 1) throw new Error(`${node.m_Name}: expected one ${direction ? 'output' : 'input'} slot "${name}", found ${matches.length}`);
    return matches[0].m_Id;
  }
  edgesFrom(node, slotId) { return this.data.m_Edges.filter(e => e.m_OutputSlot.m_Node.m_Id === node.m_ObjectId && e.m_OutputSlot.m_SlotId === slotId); }
  edgesInto(node) { return this.data.m_Edges.filter(e => e.m_InputSlot.m_Node.m_Id === node.m_ObjectId); }
  connect(from, fromSlot, to, toSlot) {
    if (this.data.m_Edges.some(e => e.m_InputSlot.m_Node.m_Id === to.m_ObjectId && e.m_InputSlot.m_SlotId === toSlot))
      throw new Error(`${to.m_Name}: input ${toSlot} already connected`);
    this.data.m_Edges.push({m_OutputSlot: {m_Node: {m_Id: from.m_ObjectId}, m_SlotId: fromSlot}, m_InputSlot: {m_Node: {m_Id: to.m_ObjectId}, m_SlotId: toSlot}});
  }
  // A node and its slots, copied with new ids and moved by (dx, dy).
  cloneNode(template, key, dx, dy, name = template.m_Name, owner = this) {
    const node = this.copy(template, key, owner);
    node.m_Name = name;
    node.m_Group = {m_Id: ''};
    const position = node.m_DrawState.m_Position;
    position.x += dx; position.y += dy;
    node.m_Slots = owner.slots(template).map(slot => ({m_Id: this.add(this.copy(slot, `${key}:slot:${slot.m_Id}`, owner)).m_ObjectId}));
    this.add(node);
    this.data.m_Nodes.push({m_Id: node.m_ObjectId});
    this.newNodes.add(node.m_ObjectId);
    return node;
  }
  // The first native node of a type, from this graph or the library, as a
  // template for utility nodes; returns [template, owner graph].
  template(type, filter = () => true) {
    for (const owner of [this, this.library]) {
      const node = owner?.nodes().find(n => owner.type(n) === type && !this.newNodes.has(n.m_ObjectId) && filter(n, owner));
      if (node) return [node, owner];
    }
    throw new Error(`no native ${type} to copy`);
  }
  utility(type, key, anchor, dx, dy) {
    const [template, owner] = this.template(type);
    const node = this.cloneNode(template, key, 0, 0, template.m_Name, owner);
    node.m_DrawState.m_Position.x = anchor.m_DrawState.m_Position.x + dx;
    node.m_DrawState.m_Position.y = anchor.m_DrawState.m_Position.y + dy;
    return node;
  }
  property(id) {
    const ref = [...this.data.m_Properties, ...this.data.m_Keywords].find(p => p.m_Id === id);
    if (!ref) throw new Error(`${id} is not a graph property`);
    return this.get(id);
  }
  propertyByReference(reference) {
    const matches = this.data.m_Properties.map(p => this.get(p.m_Id)).filter(p => (p.m_OverrideReferenceName || p.m_DefaultReferenceName) === reference);
    if (matches.length !== 1) throw new Error(`expected one native property ${reference}, found ${matches.length}`);
    return matches[0];
  }
  // A new property copied from a native one; display name = reference without "_".
  addProperty(template, reference, category, value) {
    const name = reference.slice(1);
    const property = this.copy(template, `property:${reference}`);
    Object.assign(property, {
      m_Guid: {m_GuidSerialized: this.guid(reference)}, m_Name: name, m_DefaultRefNameVersion: 1,
      m_RefNameGeneratedByDisplayName: name, m_DefaultReferenceName: reference, m_OverrideReferenceName: '',
      promotedFromAssetID: '', promotedFromCategoryName: '', promotedOrdering: -1,
    });
    if (value !== undefined) property.m_Value = value;
    this.add(property);
    this.data.m_Properties.push({m_Id: property.m_ObjectId});
    category.m_ChildObjectList.push({m_Id: property.m_ObjectId});
    return property;
  }
  addGlobalKeyword(reference, category) {
    const template = this.get(this.data.m_Keywords[0].m_Id);
    const name = reference.slice(1).split('_').map(w => w[0] + w.slice(1).toLowerCase()).join('');
    const keyword = this.copy(template, `keyword:${reference}`);
    Object.assign(keyword, {
      m_Guid: {m_GuidSerialized: this.guid(reference)}, m_Name: name, m_DefaultRefNameVersion: 1, m_RefNameGeneratedByDisplayName: name,
      m_DefaultReferenceName: `_${name.toUpperCase()}`, m_OverrideReferenceName: reference, m_GeneratePropertyBlock: false,
      m_KeywordType: 0, m_KeywordDefinition: 1, m_KeywordScope: 1, m_KeywordStages: 63, m_Entries: [], m_Value: 0, m_IsEditable: true,
      promotedFromAssetID: '', promotedFromCategoryName: '', promotedOrdering: -1,
    });
    this.add(keyword);
    this.data.m_Keywords.push({m_Id: keyword.m_ObjectId});
    category.m_ChildObjectList.push({m_Id: keyword.m_ObjectId});
    return keyword;
  }
  // A property node for a new property, copied from a native node of the same property type.
  propertyNode(property, key, x, y) {
    const template = this.nodes().find(n => this.type(n) === 'PropertyNode' && this.get(n.m_Property.m_Id).m_Type === property.m_Type);
    if (!template) throw new Error(`no native PropertyNode for ${property.m_Type}`);
    const node = this.cloneNode(template, key, 0, 0);
    node.m_DrawState.m_Position.x = x; node.m_DrawState.m_Position.y = y;
    node.m_Property = {m_Id: property.m_ObjectId};
    const [slot] = this.slots(node);
    slot.m_DisplayName = property.m_Name;
    return node;
  }
  keywordNode(keyword, key, x, y) {
    const [template, owner] = this.template('KeywordNode', (n, g) => g.get(n.m_Keyword.m_Id).m_KeywordType === 0);
    const node = this.cloneNode(template, key, 0, 0, keyword.m_Name, owner);
    node.m_DrawState.m_Position.x = x; node.m_DrawState.m_Position.y = y;
    node.m_Keyword = {m_Id: keyword.m_ObjectId};
    return node;
  }
  addCategory(name) {
    const category = this.add({m_SGVersion: 0, m_Type: 'UnityEditor.ShaderGraph.CategoryData', m_ObjectId: this.id(`category:${name}`), m_Name: name, m_ChildObjectList: []});
    this.data.m_CategoryData.push({m_Id: category.m_ObjectId});
    return category;
  }
  subGraphNodes(guid) {
    return this.nodes().filter(n => this.type(n) === 'SubGraphNode' && JSON.parse(n.m_SerializedSubGraph).subGraph.guid === guid);
  }
  // Route every native consumer of (source, slot) through a keyword node:
  // On = the radiation result, Off = the native result.
  gate(keyword, source, sourceSlot, on, onSlot, key, exclude = []) {
    const consumers = this.edgesFrom(source, sourceSlot).filter(e => !this.newNodes.has(e.m_InputSlot.m_Node.m_Id) && !exclude.includes(e.m_InputSlot.m_Node.m_Id));
    if (!consumers.length) throw new Error(`${source.m_Name}.${sourceSlot} has no native consumer to gate`);
    const p = source.m_DrawState.m_Position;
    const node = this.keywordNode(keyword, key, p.x + p.width + 60, p.y + 1500 + 140 * this.newNodes.size % 1400);
    const [out, onIn, offIn] = ['Out', 'On', 'Off'].map((n, i) => this.slot(node, n, i === 0 ? 1 : 0));
    for (const edge of consumers) edge.m_OutputSlot = {m_Node: {m_Id: node.m_ObjectId}, m_SlotId: out};
    this.connect(on, onSlot, node, onIn);
    this.connect(source, sourceSlot, node, offIn);
    return node;
  }
  convertToMultiCompile(references) {
    for (const reference of references) {
      const matches = this.data.m_Keywords.map(k => this.get(k.m_Id)).filter(k => (k.m_OverrideReferenceName || k.m_DefaultReferenceName) === reference);
      if (matches.length !== 1) throw new Error(`expected one native keyword ${reference}, found ${matches.length}`);
      const [keyword] = matches;
      if (keyword.m_KeywordType !== 0 || keyword.m_KeywordDefinition !== 0) throw new Error(`${reference} is no longer a shader_feature boolean`);
      this.touch(keyword);
      keyword.m_KeywordDefinition = 1;
    }
  }
  validate() {
    const ids = new Set();
    for (const {object} of this.chunks) { if (ids.has(object.m_ObjectId)) throw new Error(`duplicate ${object.m_ObjectId}`); ids.add(object.m_ObjectId); }
    const inputs = new Set();
    for (const edge of this.data.m_Edges) {
      const from = this.get(edge.m_OutputSlot.m_Node.m_Id), to = this.get(edge.m_InputSlot.m_Node.m_Id);
      const out = this.slots(from).find(s => s.m_Id === edge.m_OutputSlot.m_SlotId);
      const into = this.slots(to).find(s => s.m_Id === edge.m_InputSlot.m_SlotId);
      if (!out || out.m_SlotType !== 1) throw new Error(`edge from a missing output ${from.m_Name}.${edge.m_OutputSlot.m_SlotId}`);
      if (!into || into.m_SlotType !== 0) throw new Error(`edge into a missing input ${to.m_Name}.${edge.m_InputSlot.m_SlotId}`);
      const key = `${to.m_ObjectId}:${into.m_Id}`;
      if (inputs.has(key)) throw new Error(`two edges into ${to.m_Name}.${into.m_DisplayName}`);
      inputs.add(key);
    }
    const categorised = new Set(this.data.m_CategoryData.flatMap(c => this.get(c.m_Id).m_ChildObjectList.map(x => x.m_Id)));
    for (const ref of [...this.data.m_Properties, ...this.data.m_Keywords]) {
      this.get(ref.m_Id);
      if (!categorised.has(ref.m_Id)) throw new Error(`${this.get(ref.m_Id).m_Name} is in no blackboard category`);
    }
    const references = [...this.data.m_Properties, ...this.data.m_Keywords].map(r => { const p = this.get(r.m_Id); return p.m_OverrideReferenceName || p.m_DefaultReferenceName; });
    if (new Set(references).size !== references.length) throw new Error('duplicate property or keyword reference names');
    for (const node of this.nodes()) {
      this.slots(node);
      if (node.m_Property) this.property(node.m_Property.m_Id);
      if (node.m_Keyword) this.property(node.m_Keyword.m_Id);
    }
  }
  serialize() {
    this.validate();
    return this.chunks.map(c => c.dirty ? JSON.stringify(c.object, null, 4) : c.source).join('\n\n') + '\n\n';
  }
}

async function subgraphGuid(name) {
  const meta = await readFile(resolve(NATIVE_SHADER_DIR, `${name}.shadersubgraph.meta`), 'utf8');
  const guid = /^guid: ([0-9a-f]{32})$/m.exec(meta)?.[1];
  if (!guid) throw new Error(`${name}.shadersubgraph.meta has no guid`);
  return guid;
}

// The native contamination subgraph node and the Lerp that applies its colour.
function nativeContamination(graph, guid, what) {
  const matches = graph.subGraphNodes(guid);
  if (matches.length !== 1) throw new Error(`${what}: expected one native contamination subgraph, found ${matches.length}`);
  const [native] = matches;
  const color = graph.slot(native, 'Color', 1), contamination = graph.slot(native, 'Contamination', 1);
  const lerps = graph.nodes().filter(n => graph.type(n) === 'LerpNode'
    && graph.edgesInto(n).some(e => e.m_OutputSlot.m_Node.m_Id === native.m_ObjectId && e.m_OutputSlot.m_SlotId === color && e.m_InputSlot.m_SlotId === graph.slot(n, 'B', 0))
    && graph.edgesInto(n).some(e => e.m_OutputSlot.m_Node.m_Id === native.m_ObjectId && e.m_OutputSlot.m_SlotId === contamination && e.m_InputSlot.m_SlotId === graph.slot(n, 'T', 0)));
  if (lerps.length !== 1) throw new Error(`${what}: expected one native Lerp(albedo, contamination colour, contamination), found ${lerps.length}`);
  return {native, lerp: lerps[0], color, contamination};
}

// Copies `native` with every native input edge, except `replace`: input name
// -> [node, output slot].
function duplicateContamination(graph, native, key, replace) {
  const copy = graph.cloneNode(native, key, 0, 1300, `${native.m_Name} (Deep Frontier)`);
  const used = new Set();
  for (const edge of graph.edgesInto(native)) {
    const name = graph.slots(native).find(s => s.m_Id === edge.m_InputSlot.m_SlotId).m_DisplayName;
    if (replace[name]) { used.add(name); continue; }
    graph.connect(graph.get(edge.m_OutputSlot.m_Node.m_Id), edge.m_OutputSlot.m_SlotId, copy, edge.m_InputSlot.m_SlotId);
  }
  for (const [name, [node, slot]] of Object.entries(replace)) {
    if (!used.has(name)) throw new Error(`${native.m_Name}: native input "${name}" is no longer connected`);
    graph.connect(node, slot, copy, graph.slot(copy, name, 0));
  }
  return copy;
}

function patchWater(graph, guid, variant) {
  const {native, lerp, color, contamination} = nativeContamination(graph, guid, variant.name);
  const out = name => graph.slot(native, name, 1);
  const category = graph.addCategory('Deep Frontier radiation');
  const keyword = graph.addGlobalKeyword(WATER.keyword, category);
  const p = native.m_DrawState.m_Position;
  const mapTemplate = graph.propertyByReference('_NewContaminations');
  const replace = {};
  let row = 0;
  const node = property => graph.propertyNode(property, `node:${property.m_DefaultReferenceName}`, p.x - 420, p.y + 1300 + 60 * row++);
  replace.OldContaminations = [node(graph.addProperty(mapTemplate, WATER.oldMap, category)), 0];
  replace.NewContaminations = [node(graph.addProperty(mapTemplate, WATER.newMap, category)), 0];
  for (const [nativeName, reference] of Object.entries(WATER.colors)) {
    const template = graph.propertyByReference(`_${nativeName.replaceAll(' ', '_')}`);
    replace[nativeName] = [node(graph.addProperty(template, reference, category, WATER_DEFAULTS[reference])), 0];
  }
  // Chained surface: the radioactive pass starts from the native contaminated surface.
  for (const name of ['Normal', 'Metallic', 'Smoothness']) replace[name] = [native, out(name)];
  const radioactive = duplicateContamination(graph, native, 'radioactive', replace);
  const rOut = name => graph.slot(radioactive, name, 1);

  const mixed = graph.utility('LerpNode', 'lerp:radioactive', lerp, 0, 1300);
  graph.connect(lerp, graph.slot(lerp, 'Out', 1), mixed, graph.slot(mixed, 'A', 0));
  graph.connect(radioactive, rOut('Color'), mixed, graph.slot(mixed, 'B', 0));
  graph.connect(radioactive, rOut('Contamination'), mixed, graph.slot(mixed, 'T', 0));
  const emission = graph.utility('AddNode', 'add:emission', lerp, 0, 1450);
  graph.connect(native, out('Emission'), emission, graph.slot(emission, 'A', 0));
  graph.connect(radioactive, rOut('Emission'), emission, graph.slot(emission, 'B', 0));
  const strongest = graph.utility('MaximumNode', 'max:contamination', lerp, 0, 1600);
  graph.connect(native, contamination, strongest, graph.slot(strongest, 'A', 0));
  graph.connect(radioactive, rOut('Contamination'), strongest, graph.slot(strongest, 'B', 0));

  graph.gate(keyword, lerp, graph.slot(lerp, 'Out', 1), mixed, graph.slot(mixed, 'Out', 1), 'gate:color');
  graph.gate(keyword, native, out('Emission'), emission, graph.slot(emission, 'Out', 1), 'gate:emission');
  for (const name of ['Metallic', 'Smoothness', 'Normal']) graph.gate(keyword, native, out(name), radioactive, rOut(name), `gate:${name}`);
  // Reflections and level visibility see the stronger of the two contaminations.
  graph.gate(keyword, native, contamination, strongest, graph.slot(strongest, 'Out', 1), 'gate:contamination', [lerp.m_ObjectId]);
  if (graph.edgesFrom(native, color).length !== 1) throw new Error(`${variant.name}: native contamination colour has other consumers`);
}

function patchSoil(graph, guid, variant) {
  const {native, lerp, color, contamination} = nativeContamination(graph, guid, variant.name);
  for (const slot of [color, contamination])
    if (graph.edgesFrom(native, slot).length !== 1) throw new Error(`${variant.name}: native soil contamination output ${slot} has other consumers`);
  const category = graph.addCategory('Deep Frontier radiation');
  const keyword = graph.addGlobalKeyword(SOIL.keyword, category);
  const p = native.m_DrawState.m_Position;
  const map = graph.addProperty(graph.propertyByReference('_ContaminationMap'), SOIL.map, category);
  const tint = graph.addProperty(graph.propertyByReference('_Contamination_Color'), SOIL.color, category, SOIL_DEFAULT);
  const irradiated = duplicateContamination(graph, native, 'irradiated', {
    ContaminationMap: [graph.propertyNode(map, 'node:map', p.x - 420, p.y + 1300), 0],
    'Contamination Color': [graph.propertyNode(tint, 'node:color', p.x - 420, p.y + 1360), 0],
  });
  const mixed = graph.utility('LerpNode', 'lerp:irradiated', lerp, 0, 1300);
  graph.connect(lerp, graph.slot(lerp, 'Out', 1), mixed, graph.slot(mixed, 'A', 0));
  graph.connect(irradiated, graph.slot(irradiated, 'Color', 1), mixed, graph.slot(mixed, 'B', 0));
  graph.connect(irradiated, graph.slot(irradiated, 'Contamination', 1), mixed, graph.slot(mixed, 'T', 0));
  graph.gate(keyword, lerp, graph.slot(lerp, 'Out', 1), mixed, graph.slot(mixed, 'Out', 1), 'gate:color');
}

export async function buildVariants() {
  const guids = {water: await subgraphGuid('WaterContamination'), soil: await subgraphGuid('SoilContaminationVisualization')};
  const library = new Graph(await readFile(resolve(NATIVE_SHADER_DIR, 'PhysicalWaterURP_Opaque.shadergraph'), 'utf8'), 'library');
  const result = [];
  for (const variant of VARIANTS) {
    const graph = new Graph(await readFile(resolve(NATIVE_SHADER_DIR, `${variant.native}.shadergraph`), 'utf8'), variant.name, library);
    if (graph.data.m_Path !== 'Shader Graphs') throw new Error(`${variant.native}: native graph path changed (${graph.data.m_Path})`);
    graph.data.m_Path = SHADER_PATH;
    graph.convertToMultiCompile(variant.multiCompile);
    if (variant.kind === 'water') patchWater(graph, guids.water, variant);
    else patchSoil(graph, guids.soil, variant);
    result.push({variant, path: resolve(VARIANT_DIR, `${variant.name}.shadergraph`), text: graph.serialize()});
  }
  return result;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const check = process.argv.includes('--check');
  const stale = [];
  for (const {path, text} of await buildVariants()) {
    if (check) {
      const current = await readFile(path, 'utf8').catch(() => null);
      if (current !== text) stale.push(path);
    } else {
      await mkdir(dirname(path), {recursive: true});
      await writeFile(path, text);
      console.log(`wrote ${path}`);
    }
  }
  if (stale.length) { console.error(`Stale shader variants (run node tools/native_shader_variants.mjs):\n${stale.join('\n')}`); process.exit(1); }
  if (check) console.log('Shader variants are current.');
}
