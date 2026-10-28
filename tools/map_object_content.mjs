// Map-object models and pile-good visualizations (tools/map_objects.json).
//
// The Blender study build (tools/asset-pipeline/build_map_objects.py) exports
// the models; this module gives the blueprint generators their bindings:
//   mapObjectModel(id)     the TimbermeshSpec resource of a map object
//   mapObjectCollider(id)  a box collider over the footprint up to the model's
//                          authored maxHeight (the old ones were either missing,
//                          as on the vein, or a full layer tall over a 0.3 seam)
//   applyPileGoodVisualizations()  the DeepOre and DeepAlloy pile models:
//     - GoodVisualization blueprints cloned from the vanilla ScrapMetal /
//       MetalBlock ones (same offsets, levels and goods-atlas material), with
//       Deep Frontier meshes shipped in the asset bundle;
//     - same-path partial blueprints that append the two visualizations to
//       every Iron Teeth pile that visualizes pileable goods (vanilla piles,
//       the map-editor ReservePile and Expanded Storage's PileModule), so a
//       pile shows ore and alloy instead of nothing.
// Every input is checked; nothing falls back.
import {readFile, writeFile, mkdir, access} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const defaultRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));
export const CONTRACT = JSON.parse(await readFile(resolve(defaultRoot, 'tools', 'map_objects.json'), 'utf8'));
const vanillaRelative = ['vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources'];
const EXPANDED_STORAGE = 'C:/Program Files (x86)/Steam/steamapps/workshop/content/1062090/3795292508';

const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^\uFEFF/, ''));
const writeJson = async (path, value) => { await mkdir(dirname(path), {recursive: true}); await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8'); };
const exists = async (path) => access(path).then(() => true, () => false);

function spec(id) {
  const value = CONTRACT.models[id];
  if (!value) throw new Error(`map_objects.json has no model ${id}`);
  return value;
}

export function mapObjectModel(id) {
  return spec(id).resource;
}

export function mapObjectCollider(id) {
  const {size: [w, d], maxHeight} = spec(id);
  if (!(maxHeight > 0)) throw new Error(`${id}: maxHeight must be positive`);
  const h = Math.round(maxHeight * 1000) / 1000;
  // Unity axes: X across, Y up, Z back.
  return {BoxColliders: [{Center: {X: w / 2, Y: h / 2, Z: d / 2}, Size: {X: w, Y: h, Z: d}}], SphereColliders: [], CapsuleColliders: []};
}

// Checks a generated blueprint against the contract: footprint and model binding.
export function checkMapObjectBlueprint(id, value, child) {
  const {size: [w, d, z]} = spec(id);
  const size = value.BlockObjectSpec?.Size;
  if (!size || size.X !== w || size.Y !== d || size.Z !== z)
    throw new Error(`${id}: blueprint footprint ${JSON.stringify(size)} differs from map_objects.json ${w}x${d}x${z}`);
  const model = value.Children?.[child]?.TimbermeshSpec?.Model;
  if (model !== mapObjectModel(id)) throw new Error(`${id}: ${child} binds ${model}, not ${mapObjectModel(id)}`);
}

// Pile templates (Iron Teeth) that visualize pileable goods, by same-path
// partial blueprint. Base files must exist with exactly the vanilla pile list.
const VANILLA_PILE_LIST = ['Log', 'Plank', 'TreatedPlank', 'ScrapMetal', 'MetalBlock'];
const PILES = [
  {source: 'vanilla', path: 'Buildings/Storage/SmallIndustrialPile/SmallIndustrialPile.IronTeeth.blueprint.json'},
  {source: 'vanilla', path: 'Buildings/Storage/LargeIndustrialPile/LargeIndustrialPile.IronTeeth.blueprint.json'},
  {source: 'vanilla', path: 'MapEditor/Objects/ReservePile/ReservePile.blueprint.json'},
  {source: 'MauricioBedoya.ExpandedStorage', path: 'Buildings/Storage/PileModule/PileModule.IronTeeth.blueprint.json'},
];
const PILE_GOODS = [
  {good: 'DeepOre', template: 'ScrapMetal'},
  {good: 'DeepAlloy', template: 'MetalBlock'},
];
export const PILE_PATCHES = PILES.map((p) => p.path);
export const GOOD_VISUALIZATION_FILES = PILE_GOODS.map(({good}) => `GoodVisualization/GoodVisualization.${good}.blueprint.json`);

export async function applyPileGoodVisualizations({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const vanilla = resolve(root, ...vanillaRelative);
  const ids = [];
  for (const {good, template} of PILE_GOODS) {
    const contract = CONTRACT.goods[good];
    if (!contract) throw new Error(`map_objects.json has no pile good ${good}`);
    const base = await readJson(resolve(vanilla, 'GoodVisualization', `GoodVisualization.${template}.blueprint.json`));
    const v = base.GoodVisualizationSpec;
    if (v.Id !== template || v.Variant !== '' || v.LimitingAmount !== contract.items || v.Offset.X !== contract.itemSpacing || v.Offset.Z !== contract.levelHeight)
      throw new Error(`vanilla GoodVisualization.${template} no longer matches the ${good} pile contract (${JSON.stringify(v)})`);
    await writeJson(resolve(dataRoot, `GoodVisualization/GoodVisualization.${good}.blueprint.json`), {
      GoodVisualizationSpec: {...v, Id: contract.visualization, PrimaryMesh: contract.primary, SecondaryMesh: contract.secondary},
    });
    const goodPath = resolve(dataRoot, 'Goods', `Good.${good}.blueprint.json`);
    const goodValue = await readJson(goodPath);
    if (goodValue.GoodSpec.GoodType !== 'Pileable' || goodValue.GoodSpec.StockpileVisualization !== template)
      throw new Error(`${good}: expected a Pileable good cloned with the ${template} visualization, found ${goodValue.GoodSpec.GoodType}/${goodValue.GoodSpec.StockpileVisualization}`);
    goodValue.GoodSpec.StockpileVisualization = contract.visualization;
    await writeJson(goodPath, goodValue);
    ids.push(contract.visualization);
  }
  for (const pile of PILES) {
    const base = pile.source === 'vanilla' ? resolve(vanilla, pile.path) : resolve(EXPANDED_STORAGE, pile.path);
    if (!await exists(base)) throw new Error(`pile template base missing: ${pile.source} ${pile.path}`);
    const list = (await readJson(base)).StockpileGoodPileVisualizerSpec?.GoodPileVisualizations;
    if (JSON.stringify(list) !== JSON.stringify(VANILLA_PILE_LIST))
      throw new Error(`${pile.path}: pile visualizations ${JSON.stringify(list)} are not the vanilla list; review the patch`);
    const target = resolve(dataRoot, pile.path);
    if (await exists(target)) {
      const keys = Object.keys(await readJson(target));
      if (keys.length !== 1 || keys[0] !== 'StockpileGoodPileVisualizerSpec')
        throw new Error(`${pile.path} holds other Deep Frontier content (${keys}); merge the pile patch there`);
    }
    await writeJson(target, {StockpileGoodPileVisualizerSpec: {'GoodPileVisualizations#append': ids}});
  }
  return {visualizations: ids, piles: PILE_PATCHES};
}
