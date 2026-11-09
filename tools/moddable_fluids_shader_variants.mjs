// Moddable Fluids variants of the two native Timberborn 1.1.2.8 water shader graphs: the shared
// renderer for every registered fluid colour. They replace Deep Frontier's radioactive-water
// variants after migration; unlike that swap, they are assigned to per-scene material copies on the
// scene's own water tiles, so the game's materials are never modified (native-safety audit C2).
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
export const VARIANTS = [
  {name: 'FluidWaterURP_Opaque', native: 'PhysicalWaterURP_Opaque', multiCompile: ['_CALCULATE_OUTFLOWS']},
  {name: 'FluidWaterURP_Transparent', native: 'PhysicalWaterURP_Transparent', multiCompile: ['_CALCULATE_OUTFLOWS']},
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

export async function buildVariants() {
  const guid = await subgraphGuid('WaterContamination');
  const library = new Graph(await readFile(resolve(NATIVE_SHADER_DIR, 'PhysicalWaterURP_Opaque.shadergraph'), 'utf8'), 'moddable-fluids-library');
  const result = [];
  for (const variant of VARIANTS) {
    const graph = new Graph(await readFile(resolve(NATIVE_SHADER_DIR, `${variant.native}.shadergraph`), 'utf8'), `moddable-fluids:${variant.name}`, library);
    if (graph.data.m_Path !== 'Shader Graphs') throw new Error(`${variant.native}: native graph path changed (${graph.data.m_Path})`);
    graph.data.m_Path = SHADER_PATH;
    graph.convertToMultiCompile(variant.multiCompile);
    patchWater(graph, guid, variant);
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
