// Moddable Fluids variants of the two native Timberborn 1.1.2.8 water shader graphs (the shared
// renderer for every registered fluid colour) and of the native terrain graph (the shared terrain
// overlay). They replace Deep Frontier's radioactive-water and irradiated-soil variants after
// migration; unlike that swap, they are assigned to per-scene material copies on the scene's own
// water tiles and terrain tiles, so the game's materials are never modified (native-safety audit C2).
//
// The native WaterContamination subgraph samples one R8 texture array pair (_OldContaminations /
// _NewContaminations, layer = column ordinal, pixel x + y * width), interpolates by _TickProgress,
// blends linked neighbours and returns a visual weight. Each variant adds four instances of that
// same subgraph, fed from Moddable Fluids arrays for the red, green, blue and strength channels of
// the resolved appearance (src/ModdableFluids/Rendering), so tick interpolation and neighbour
// blending are exactly the native ones. FluidWaterRendering encodes every channel through the inverse
// of the native visibility curve, so each instance's Contamination output is the linear channel.
// The colour (Vector3 of the three channels) is lerped over the native, already contaminated albedo
// by the strength channel; normals, smoothness, emission, foam and transparency stay native. A
// global multi_compile keyword gates the addition, so with no extra fluid the variant compiles to
// the native code.
//
// Terrain: the native SoilContaminationVisualization subgraph samples the RG16 _ContaminationMap
// (R old, G new; layer = terrain z, pixel x + y * width) through SoilContaminationMapSampler, raises
// the tick-interpolated level to the native nonlinearity, adds the native noise and blending, and
// multiplies the native soil-contamination texture by a colour; TerrainURP lerps that over the albedo.
// FluidTerrainURP adds a second instance of the subgraph, fed from Moddable Fluids' overlay level map
// (same layout and update rule, FluidTerrainRendering) instead of _ContaminationMap. Its colour input
// is per cell: another SoilContaminationMapSampler (copied from the native subgraph) reads the overlay
// colour map, an RGBAHalf array of sum(level * colour) and sum(level) per cell, so the blended colour
// sum over the blended level sum is the level-weighted mean colour, also where cells of different
// overlays or empty cells meet. The result is lerped over the native, already contaminated albedo
// behind its own global keyword; everything else stays native.
//
//   node tools/moddable_fluids_shader_variants.mjs           # writes the variants
//   node tools/moddable_fluids_shader_variants.mjs --check   # fails if they are stale
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {resolve, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {Graph, NATIVE_SHADER_DIR, subgraphGuid, nativeContamination, duplicateContamination} from './native_shader_variants.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
export const VARIANT_DIR = resolve(root, 'src', 'ModdableFluids', 'AssetBundles', 'Resources', 'Shaders', 'ModdableFluids');
export const SHADER_PATH = 'ModdableFluids';
// Names shared with src/ModdableFluids/Runtime/FluidWaterRendering.cs.
export const APPEARANCE = {
  keyword: '_MODDABLE_FLUIDS_APPEARANCE',
  channels: ['Red', 'Green', 'Blue', 'Strength'].map(name => ({name, old: `_MFOldTint${name}`, new: `_MFNewTint${name}`})),
};
// Names shared with src/ModdableFluids/Runtime/FluidTerrainRendering.cs.
export const TERRAIN_OVERLAY = {
  keyword: '_MODDABLE_FLUIDS_TERRAIN_OVERLAY',
  levels: '_MFTerrainOverlayMap',
  colors: '_MFTerrainOverlayColors',
  // Floor of the blended level sum the colour sum is divided by. Below it the colour fades to black
  // instead of dividing by zero, which happens only where the blended level (the lerp weight) is near
  // zero too.
  minimumLevelSum: 0.0001,
};
// The native terrain materials enable these (RadiationShading.TerrainCompiledKeywords lists the same
// for Deep Frontier's variant): Grass [_USELAYERTOOL], Cliff [all three], CliffEdge [_SAMPLE_SPLATMAP
// _USELAYERTOOL], SlopeCliff [_SAMPLE_SPLATMAP _USE_TRIPLANAR_SPLATMAP], SlopeCliffEdge [_SAMPLE_SPLATMAP].
export const VARIANTS = [
  {name: 'FluidWaterURP_Opaque', native: 'PhysicalWaterURP_Opaque', kind: 'water', multiCompile: ['_CALCULATE_OUTFLOWS']},
  {name: 'FluidWaterURP_Transparent', native: 'PhysicalWaterURP_Transparent', kind: 'water', multiCompile: ['_CALCULATE_OUTFLOWS']},
  {name: 'FluidTerrainURP', native: 'TerrainURP', kind: 'terrain', multiCompile: ['_USE_TRIPLANAR_SPLATMAP', '_SAMPLE_SPLATMAP', '_USELAYERTOOL']},
];

function patchWater(graph, guid, variant) {
  const {native, lerp} = nativeContamination(graph, guid, variant.name);
  const category = graph.addCategory('Moddable Fluids appearance');
  const keyword = graph.addGlobalKeyword(APPEARANCE.keyword, category);
  const p = native.m_DrawState.m_Position;
  const mapTemplate = graph.propertyByReference('_NewContaminations');
  let row = 0;
  const node = property => graph.propertyNode(property, `node:${property.m_DefaultReferenceName}`, p.x - 420, p.y + 1300 + 60 * row++);
  const channel = {};
  for (const [index, c] of APPEARANCE.channels.entries()) {
    const copy = duplicateContamination(graph, native, `appearance:${c.name}`, {
      OldContaminations: [node(graph.addProperty(mapTemplate, c.old, category)), 0],
      NewContaminations: [node(graph.addProperty(mapTemplate, c.new, category)), 0],
    });
    copy.m_Name = `${native.m_Name} (Moddable Fluids ${c.name})`;
    copy.m_DrawState.m_Position.y += 260 * index;
    channel[c.name] = [copy, graph.slot(copy, 'Contamination', 1)];
  }
  const color = graph.utility('Vector3Node', 'vector3:tint', lerp, 0, 1300);
  for (const [axis, name] of [['X', 'Red'], ['Y', 'Green'], ['Z', 'Blue']]) graph.connect(...channel[name], color, graph.slot(color, axis, 0));
  const tinted = graph.utility('LerpNode', 'lerp:tint', lerp, 0, 1450);
  graph.connect(lerp, graph.slot(lerp, 'Out', 1), tinted, graph.slot(tinted, 'A', 0));
  graph.connect(color, graph.slot(color, 'Out', 1), tinted, graph.slot(tinted, 'B', 0));
  graph.connect(...channel.Strength, tinted, graph.slot(tinted, 'T', 0));
  graph.gate(keyword, lerp, graph.slot(lerp, 'Out', 1), tinted, graph.slot(tinted, 'Out', 1), 'gate:tint');
}

// The edge into a native node's input slot: [source node, source slot].
function nativeInput(graph, node, name) {
  const slot = graph.slot(node, name, 0);
  const edges = graph.edgesInto(node).filter(e => e.m_InputSlot.m_SlotId === slot);
  if (edges.length !== 1) throw new Error(`${node.m_Name}: expected native input "${name}" to be connected once, found ${edges.length}`);
  return [graph.get(edges[0].m_OutputSlot.m_Node.m_Id), edges[0].m_OutputSlot.m_SlotId];
}

function patchTerrain(graph, guids, soilGraph, variant) {
  const {native, lerp, color, contamination} = nativeContamination(graph, guids.soil, variant.name);
  for (const slot of [color, contamination])
    if (graph.edgesFrom(native, slot).length !== 1) throw new Error(`${variant.name}: native soil contamination output ${slot} has other consumers`);
  const category = graph.addCategory('Moddable Fluids terrain overlay');
  const keyword = graph.addGlobalKeyword(TERRAIN_OVERLAY.keyword, category);
  const p = native.m_DrawState.m_Position;
  // Global texture arrays, declared like the native _ContaminationMap (no material property).
  const mapTemplate = graph.propertyByReference('_ContaminationMap');
  const levels = graph.propertyNode(graph.addProperty(mapTemplate, TERRAIN_OVERLAY.levels, category), `node:${TERRAIN_OVERLAY.levels}`, p.x - 420, p.y + 1300);
  const colors = graph.propertyNode(graph.addProperty(mapTemplate, TERRAIN_OVERLAY.colors, category), `node:${TERRAIN_OVERLAY.colors}`, p.x - 420, p.y + 1360);
  // The native subgraph's own map sampler, on the colour map, addressed exactly as the native soil map.
  const samplers = soilGraph.subGraphNodes(guids.sampler);
  if (samplers.length !== 1) throw new Error(`SoilContaminationVisualization: expected one native SoilContaminationMapSampler, found ${samplers.length}`);
  const sampler = graph.cloneNode(samplers[0], 'overlay:color-sampler', 0, 0, 'SoilContaminationMapSampler (Moddable Fluids overlay colours)', soilGraph);
  Object.assign(sampler.m_DrawState.m_Position, {x: p.x - 420, y: p.y + 1500});
  for (const [into, from] of [['Terrain Coordinates', 'Terrain Coordinates'], ['Terrain Material Map Scale', 'Terrain Material Map Scale'], ['Blending Margin', 'ContaminationBlendingMargin']])
    graph.connect(...nativeInput(graph, native, from), sampler, graph.slot(sampler, into, 0));
  graph.connect(colors, graph.slots(colors)[0].m_Id, sampler, graph.slot(sampler, 'Terrain Material Map', 0));
  // Colour = blended sum(level * colour) / max(blended sum(level), floor).
  const sum = graph.utility('Vector3Node', 'vector3:overlay-color-sum', sampler, 300, 0);
  for (const [axis, channel] of [['X', 'R'], ['Y', 'G'], ['Z', 'B']]) graph.connect(sampler, graph.slot(sampler, channel, 1), sum, graph.slot(sum, axis, 0));
  const floor = graph.utility('MaximumNode', 'max:overlay-level-sum', sampler, 300, 150);
  graph.connect(sampler, graph.slot(sampler, 'A', 1), floor, graph.slot(floor, 'A', 0));
  const minimum = graph.slots(floor).find(s => s.m_Id === graph.slot(floor, 'B', 0));
  const m = TERRAIN_OVERLAY.minimumLevelSum;
  for (const field of ['m_Value', 'm_DefaultValue']) minimum[field] = {x: m, y: m, z: m, w: m};
  const mean = graph.utility('DivideNode', 'divide:overlay-color', sampler, 520, 0);
  graph.connect(sum, graph.slot(sum, 'Out', 1), mean, graph.slot(mean, 'A', 0));
  graph.connect(floor, graph.slot(floor, 'Out', 1), mean, graph.slot(mean, 'B', 0));
  const overlay = duplicateContamination(graph, native, 'overlay', {
    ContaminationMap: [levels, graph.slots(levels)[0].m_Id],
    'Contamination Color': [mean, graph.slot(mean, 'Out', 1)],
  });
  overlay.m_Name = `${native.m_Name} (Moddable Fluids overlay)`;
  const mixed = graph.utility('LerpNode', 'lerp:overlay', lerp, 0, 1300);
  graph.connect(lerp, graph.slot(lerp, 'Out', 1), mixed, graph.slot(mixed, 'A', 0));
  graph.connect(overlay, graph.slot(overlay, 'Color', 1), mixed, graph.slot(mixed, 'B', 0));
  graph.connect(overlay, graph.slot(overlay, 'Contamination', 1), mixed, graph.slot(mixed, 'T', 0));
  graph.gate(keyword, lerp, graph.slot(lerp, 'Out', 1), mixed, graph.slot(mixed, 'Out', 1), 'gate:overlay');
}

export async function buildVariants() {
  const guids = {water: await subgraphGuid('WaterContamination'), soil: await subgraphGuid('SoilContaminationVisualization'),
    sampler: await subgraphGuid('SoilContaminationMapSampler')};
  const library = new Graph(await readFile(resolve(NATIVE_SHADER_DIR, 'PhysicalWaterURP_Opaque.shadergraph'), 'utf8'), 'moddable-fluids-library');
  const soilGraph = new Graph(await readFile(resolve(NATIVE_SHADER_DIR, 'SoilContaminationVisualization.shadersubgraph'), 'utf8'), 'moddable-fluids-soil-library');
  const result = [];
  for (const variant of VARIANTS) {
    const graph = new Graph(await readFile(resolve(NATIVE_SHADER_DIR, `${variant.native}.shadergraph`), 'utf8'), `moddable-fluids:${variant.name}`, library);
    if (graph.data.m_Path !== 'Shader Graphs') throw new Error(`${variant.native}: native graph path changed (${graph.data.m_Path})`);
    graph.data.m_Path = SHADER_PATH;
    graph.convertToMultiCompile(variant.multiCompile);
    if (variant.kind === 'water') patchWater(graph, guids.water, variant);
    else patchTerrain(graph, guids, soilGraph, variant);
    result.push({variant, path: resolve(VARIANT_DIR, `${variant.name}.shadergraph`), text: graph.serialize()});
  }
  return result;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const check = process.argv.includes('--check');
  const stale = [];
  for (const {path, text} of await buildVariants()) {
    if (check) {
      if (await readFile(path, 'utf8').catch(() => null) !== text) stale.push(path);
    } else {
      await mkdir(dirname(path), {recursive: true});
      await writeFile(path, text);
      console.log(`wrote ${path}`);
    }
  }
  if (stale.length) { console.error(`Stale Moddable Fluids shader variants (run node tools/moddable_fluids_shader_variants.mjs):\n${stale.join('\n')}`); process.exit(1); }
  if (check) console.log('Moddable Fluids shader variants are current.');
}
