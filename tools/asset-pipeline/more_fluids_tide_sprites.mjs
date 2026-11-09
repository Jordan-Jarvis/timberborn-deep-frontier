// More Fluids tide sprites: the coffee tide and the salt tide, at the sizes of
// the vanilla weather sprites and Deep Frontier's radioactive tide
// (tools/radioactive_tide_content.mjs):
//   Sprites/Weather/MoreFluids<Tide>TideIcon.png          46 x 46, top-bar weather icon
//   Sprites/Weather/MoreFluids<Tide>TideProgress.png      316 x 52, weather-panel bar
//   Sprites/Weather/MoreFluids<Tide>TideNotification.png  1514 x 348, notification banner
// each with its {"isSprite":true} sidecar, under src/MoreFluids/Data.
//
// Icons are single-ink line art (src/MoreFluids/Art/Icons/MoreFluids<Tide>Tide.svg)
// rendered by tools/native_icon_style.mjs on the vanilla 46 px weather canvas.
// Bars and banners recolour the native badtide wave art (local reference cache
// outputs/vanilla-icons from tools/asset-pipeline/export_vanilla_icon_references.py):
// only the saturated warm wave and background pixels move; the gold frame and
// the mist keep their native colours, so each tide reads as a tide but never
// as badtide. Review sheet: outputs/more-fluids-art/tides/tides-review.png.
//
// Run: node tools/asset-pipeline/more_fluids_tide_sprites.mjs
import {access, mkdir, readFile, writeFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import sharp from 'sharp';
import {ICON_KINDS, renderNativeIcon, writeReviewSheet} from '../native_icon_style.mjs';

const root = resolve(fileURLToPath(new URL('../../', import.meta.url)));
const data = resolve(root, 'src', 'MoreFluids', 'Data');
const review = resolve(root, 'outputs', 'more-fluids-art', 'tides');
const vanilla = name => resolve(root, 'outputs', 'vanilla-icons', name);
const META = JSON.stringify(ICON_KINDS.building.meta) + '\n';

// Hue window of the badtide art that moves (degrees; deep red .. orange) and
// the target per tide: t = 0 at deep red (background, shadows), 1 at orange
// (wave faces). Each channel is lerped from its *0 to its *1 value.
const WARM = {minSaturation: 0.55, hueLow: -15, hueHigh: 40};
export const TIDES = {
  Coffee: {
    // Coffee and crema: dark roast background, caramel wave faces.
    ink: [214, 170, 118],
    recolour: {hue0: 16, hue1: 28, sat0: 0.66, sat1: 0.62, val0: 0.34, val1: 0.72},
  },
  Salt: {
    // Saltwater teal (More Fluids colour 0.15, 0.45, 0.55) with pale brine crests.
    ink: [176, 226, 228],
    recolour: {hue0: 192, hue1: 182, sat0: 0.72, sat1: 0.2, val0: 0.62, val1: 1.18},
  },
};
const ICON_STYLE = ink => ({canvas: 46, ink, shadow: {dy: 1, sigma: 0.9, opacity: 0.9},
                            hand: {frequency: 0.03, scale: 3}, extent: [0.70, 0.90]});

function fail(message) { throw new Error(message); }

function rgbToHsv(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), d = max - Math.min(r, g, b);
  let h = 0;
  if (d) h = 60 * (max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4);
  return [h < 0 ? h + 360 : h, max ? d / max : 0, max];
}

function hsvToRgb(h, s, v) {
  h = ((h % 360) + 360) % 360;
  const c = v * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = v - c;
  const [r, g, b] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
  return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)];
}

async function recolour(source, k) {
  await access(source).catch(() => fail(`native badtide art missing: ${source} (run tools/asset-pipeline/export_vanilla_icon_references.py)`));
  const {data: px, info} = await sharp(source).ensureAlpha().raw().toBuffer({resolveWithObject: true});
  for (let i = 0; i < px.length; i += 4) {
    let [h, s, v] = rgbToHsv(px[i], px[i + 1], px[i + 2]);
    if (h > 360 + WARM.hueLow) h -= 360;
    if (s < WARM.minSaturation || h < WARM.hueLow || h > WARM.hueHigh) continue;
    const t = (h - WARM.hueLow) / (WARM.hueHigh - WARM.hueLow);
    const lerp = (a, b) => a + (b - a) * t;
    [px[i], px[i + 1], px[i + 2]] = hsvToRgb(lerp(k.hue0, k.hue1), Math.min(1, s * lerp(k.sat0, k.sat1)),
                                            Math.min(1, v * lerp(k.val0, k.val1)));
  }
  return sharp(px, {raw: info}).png().toBuffer();
}

async function write(path, png) {
  await mkdir(dirname(path), {recursive: true});
  await writeFile(path, png);
  await writeFile(`${path}.meta.json`, META);
}

await mkdir(review, {recursive: true});
const icons = [];
const bannerLayers = [];
let top = 0;
for (const [tide, spec] of Object.entries(TIDES)) {
  const id = `MoreFluids${tide}Tide`;
  const svg = await readFile(resolve(root, 'src', 'MoreFluids', 'Art', 'Icons', `${id}.svg`), 'utf8');
  const icon = await renderNativeIcon(svg, 'building', id, ICON_STYLE(spec.ink));
  if (icon.canvas !== 46) fail(`${id}: icon canvas ${icon.canvas}`);
  await write(resolve(data, 'Sprites', 'Weather', `${id}Icon.png`), icon.png);
  icons.push({label: `${tide}Tide ${icon.stroke.toFixed(1)}px`, png: icon.png});
  for (const [kind, source] of [['Progress', 'weather-progress-badtide.png'], ['Notification', 'weather-notification-badtide.png']]) {
    const png = await recolour(vanilla(source), spec.recolour);
    const meta = await sharp(png).metadata();
    const expected = kind === 'Progress' ? [316, 52] : [1514, 348];
    if (meta.width !== expected[0] || meta.height !== expected[1]) fail(`${id}${kind}: ${meta.width}x${meta.height}, expected ${expected.join('x')}`);
    await write(resolve(data, 'Sprites', 'Weather', `${id}${kind}.png`), png);
    const scaled = kind === 'Notification' ? await sharp(png).resize(757, 174).png().toBuffer() : png;
    bannerLayers.push({input: scaled, left: 0, top});
    top += kind === 'Notification' ? 174 : 52;
    console.log(`${id}${kind}: ${meta.width}x${meta.height}`);
  }
  console.log(`${id}Icon: 46x46, ${(icon.extent * 100).toFixed(0)}% extent`);
}
const references = ['ico-weather-temperate', 'ico-weather-drought', 'ico-weather-badtide'].map(name => ({label: name, path: vanilla(`${name}.png`)}));
for (const r of references) await access(r.path);
await writeReviewSheet(icons, references, resolve(review, 'tides-icons.png'), 5);
const vanillaBanner = await sharp(vanilla('weather-notification-badtide.png')).resize(757, 174).png().toBuffer();
await sharp({create: {width: 757, height: top + 174, channels: 4, background: {r: 40, g: 34, b: 28, alpha: 1}}})
  .composite([{input: vanillaBanner, left: 0, top: 0}, ...bannerLayers.map(l => ({...l, top: l.top + 174}))])
  .png().toFile(resolve(review, 'tides-banners.png'));
console.log('review: outputs/more-fluids-art/tides/tides-icons.png, tides-banners.png');
