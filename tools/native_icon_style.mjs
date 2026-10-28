// Shared renderer for Deep Frontier UI icons in the vanilla Timberborn 1.1 style.
//
// Authored icon SVGs (src/DeepFrontier/Art/Icons/<Id>.svg) are single-ink line
// drawings on a 256×256 viewBox. This module is the one place that turns such a
// drawing into a game icon: it rasterizes the drawing's coverage onto the vanilla
// canvas, paints it with the vanilla ink and adds the vanilla drop shadow. The
// measured vanilla conventions are documented in docs/art/icon-style.md and come
// from the game's own sprites (tools/asset-pipeline/export_vanilla_icon_references.py).
//
// Inputs that break the contract (wrong viewBox, more than one ink, raster or
// text content, artwork outside the vanilla padding range) throw.
import {mkdir, writeFile} from 'node:fs/promises';
import {dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import sharp from 'sharp';

// Vanilla conventions measured from resources.assets (Timberborn 1.1.2.8).
// Authoring strokes on the 256 viewBox: goods 11 (details >= 8) -> ~4 px lines at 80;
// buildings/map objects 6 (details >= 4) -> ~3 px at 112. hand.scale is in viewBox units.
export const ICON_KINDS = {
  // Sprites/Goods/*Icon: 80×80, flat ink rgb(202,172,107), hard black shadow 3px down.
  good: {canvas: 80, ink: [202, 172, 107], shadow: {dy: 3, sigma: 0.5, opacity: 0.95},
         hand: {frequency: 0.025, scale: 4}, extent: [0.70, 0.95],
         meta: {generateMipmap: true, mipmapCount: -1, ignoreMipmapLimits: true, textureFormat: 'RGB32'}},
  // Building / map-object tool icons: 112×112, ink rgb(187,161,108), soft shadow 3px down.
  building: {canvas: 112, ink: [187, 161, 108], shadow: {dy: 3, sigma: 2.6, opacity: 0.95},
             hand: {frequency: 0.02, scale: 7}, extent: [0.68, 0.97], meta: {isSprite: true}},
};
ICON_KINDS.mapObject = ICON_KINDS.building;

const SUPERSAMPLE = 4;
const VIEWBOX = '0 0 256 256';

function checkSvg(svg, name) {
  const root = svg.match(/<svg\b[^>]*>/);
  if (!root) throw new Error(`${name}: no <svg> root`);
  const viewBox = root[0].match(/viewBox="([^"]+)"/);
  if (!viewBox || viewBox[1] !== VIEWBOX) throw new Error(`${name}: icon SVGs use viewBox="${VIEWBOX}"`);
  if (/\swidth=|\sheight=/.test(root[0])) throw new Error(`${name}: root width/height are set by the renderer`);
  if (/<(image|text|linearGradient|radialGradient|filter|style)\b/.test(svg))
    throw new Error(`${name}: icon SVGs are plain single-ink vector line art`);
  const colours = new Set();
  for (const [, value] of svg.matchAll(/(?:fill|stroke|color)\s*[=:]\s*"?\s*([^";\s>]+)/g))
    if (value !== 'none') colours.add(value.toLowerCase());
  if (colours.size !== 1) throw new Error(`${name}: expected exactly one ink colour, found ${[...colours].join(', ') || 'none'}`);
  if (/opacity\s*[=:]/.test(svg)) throw new Error(`${name}: ink opacity is set by the renderer`);
  return root[0];
}

// Vanilla icons are hand-inked: lines wander slightly and are never ruler-straight.
// The renderer applies that wobble as a small, deterministic displacement of the
// authored geometry (seeded by icon name) so every icon gets the same hand.
function seedFor(name) {
  let h = 2166136261;
  for (const c of name) h = Math.imul(h ^ c.charCodeAt(0), 16777619) >>> 0;
  return h % 997;
}
function inked(svg, root, name, hand) {
  if (!hand) return svg;
  const body = svg.slice(svg.indexOf(root) + root.length, svg.lastIndexOf('</svg>'));
  return `${root}<defs><filter id="nativeHand" x="-4%" y="-4%" width="108%" height="108%">`
    + `<feTurbulence type="fractalNoise" baseFrequency="${hand.frequency}" numOctaves="2" seed="${seedFor(name)}"/>`
    + `<feDisplacementMap in="SourceGraphic" scale="${hand.scale}" xChannelSelector="R" yChannelSelector="G"/>`
    + `</filter></defs><g filter="url(#nativeHand)">${body}</g></svg>`;
}

async function coverage(svg, name, canvas, hand) {
  const root = checkSvg(svg, name);
  const size = canvas * SUPERSAMPLE;
  const sized = inked(svg, root, name, hand).replace(root, root.replace('<svg', `<svg width="${size}" height="${size}"`));
  const alpha = await sharp(Buffer.from(sized)).ensureAlpha().extractChannel(3)
    .resize(canvas, canvas, {kernel: 'lanczos3'}).raw().toBuffer();
  if (alpha.length !== canvas * canvas) throw new Error(`${name}: unexpected coverage size`);
  return alpha;
}

async function blur(mask, canvas, sigma) {
  const out = await sharp(mask, {raw: {width: canvas, height: canvas, channels: 1}}).blur(sigma).extractChannel(0).raw().toBuffer();
  if (out.length !== canvas * canvas) throw new Error('shadow blur changed the channel layout');
  return out;
}

function bounds(alpha, canvas, threshold = 24) {
  let x0 = canvas, y0 = canvas, x1 = -1, y1 = -1;
  for (let y = 0; y < canvas; y++) for (let x = 0; x < canvas; x++)
    if (alpha[y * canvas + x] > threshold) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
  return x1 < 0 ? null : [x0, y0, x1 + 1, y1 + 1];
}

// Mean line width in canvas pixels: 2 × covered area / boundary length.
export function strokeWidth(alpha, canvas) {
  let area = 0, edge = 0;
  const on = (x, y) => x >= 0 && y >= 0 && x < canvas && y < canvas && alpha[y * canvas + x] > 127;
  for (let y = 0; y < canvas; y++) for (let x = 0; x < canvas; x++) {
    if (!on(x, y)) continue;
    area++;
    if (!on(x + 1, y) || !on(x - 1, y) || !on(x, y + 1) || !on(x, y - 1)) edge++;
  }
  return edge ? 2 * area / edge : 0;
}

/** Render an authored icon SVG to a vanilla-style RGBA PNG buffer. */
export async function renderNativeIcon(svgSource, kind, name = 'icon', override = {}) {
  if (!ICON_KINDS[kind]) throw new Error(`${name}: unknown icon kind ${kind}`);
  const style = {...ICON_KINDS[kind], ...override};
  const svg = String(svgSource);
  const {canvas, ink, shadow} = style;
  const cover = await coverage(svg, name, canvas, style.hand);
  const box = bounds(cover, canvas);
  if (!box) throw new Error(`${name}: empty icon`);
  const extent = Math.max(box[2] - box[0], box[3] - box[1]) / canvas;
  if (extent < style.extent[0] || extent > style.extent[1])
    throw new Error(`${name}: artwork spans ${(extent * 100).toFixed(0)}% of the canvas; vanilla ${kind} icons span ${style.extent.map(v => v * 100).join('-')}%`);
  if (box[0] < 2 || box[1] < 2 || canvas - box[2] < 2 || canvas - box[3] < 2 + shadow.dy)
    throw new Error(`${name}: artwork bounds ${box} leave no room for the vanilla shadow`);

  const shifted = Buffer.alloc(canvas * canvas);
  for (let y = shadow.dy; y < canvas; y++) cover.copy(shifted, y * canvas, (y - shadow.dy) * canvas, (y - shadow.dy + 1) * canvas);
  const shade = await blur(shifted, canvas, shadow.sigma);
  const rgba = Buffer.alloc(canvas * canvas * 4);
  for (let i = 0; i < canvas * canvas; i++) {
    const a = cover[i] / 255, s = shadow.opacity * shade[i] / 255 * (1 - a), out = a + s;
    rgba[i * 4] = ink[0] * a / (out || 1);
    rgba[i * 4 + 1] = ink[1] * a / (out || 1);
    rgba[i * 4 + 2] = ink[2] * a / (out || 1);
    rgba[i * 4 + 3] = Math.round(out * 255);
  }
  const png = await sharp(rgba, {raw: {width: canvas, height: canvas, channels: 4}}).png().toBuffer();
  return {png, canvas, bounds: box, extent, stroke: strokeWidth(cover, canvas)};
}

/** Render and write <output> plus its official-builder <output>.meta.json sidecar. */
export async function writeNativeIcon(svgSource, kind, output, name) {
  const result = await renderNativeIcon(svgSource, kind, name);
  const path = output instanceof URL ? fileURLToPath(output) : output;
  await mkdir(dirname(path), {recursive: true});
  await writeFile(path, result.png);
  await writeFile(`${path}.meta.json`, JSON.stringify(ICON_KINDS[kind].meta) + '\n');
  return result;
}

const SHEET_BG = '#34302b';
/**
 * Review sheet: each icon at game size (1×) and 2×, on the dark vanilla panel
 * colour, after a row of vanilla references of the same kind.
 * entries: [{label, png: Buffer, flag?}] (flag marks an off-contract icon in red),
 * references: [{label, path}]. Oversized canvases are shown scaled to 112 px.
 */
export async function writeReviewSheet(entries, references, output, columns = 6) {
  const cell = 380, rowHeight = 270;
  const all = [...references.map(r => ({...r, reference: true})), ...entries];
  const layers = [];
  for (const [index, entry] of all.entries()) {
    const x = (index % columns) * cell, y = Math.floor(index / columns) * rowHeight;
    let png = entry.png ?? await sharp(entry.path).png().toBuffer();
    let meta = await sharp(png).metadata();
    if (Math.max(meta.width, meta.height) > 112) {  // off-contract canvas: show it at UI size
      png = await sharp(png).resize(112, 112, {fit: 'inside'}).png().toBuffer();
      meta = await sharp(png).metadata();
    }
    layers.push({input: await sharp(png).resize(meta.width * 2, meta.height * 2, {kernel: 'nearest'}).png().toBuffer(), left: x + 8, top: y + 8});
    layers.push({input: png, left: x + 8 + meta.width * 2 + 10, top: y + 8});
    const label = entry.label.replace(/&/g, '&amp;').replace(/</g, '&lt;');
    const colour = entry.reference ? '#9fd0ff' : entry.flag ? '#ff7a6a' : '#f0e6d0';
    layers.push({input: Buffer.from(`<svg width="${cell}" height="30"><text x="8" y="20" fill="${colour}" font-family="Arial" font-size="15">${entry.reference ? 'vanilla · ' : ''}${label}${entry.flag ? ' · ' + entry.flag : ''}</text></svg>`), left: x, top: y + 236});
  }
  const rows = Math.ceil(all.length / columns);
  const path = output instanceof URL ? fileURLToPath(output) : output;
  await sharp({create: {width: columns * cell, height: rows * rowHeight, channels: 4, background: SHEET_BG}})
    .composite(layers).png().toFile(path);
}
