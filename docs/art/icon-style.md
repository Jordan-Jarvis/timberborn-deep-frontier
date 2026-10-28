# UI icon style (vanilla Timberborn 1.1)

Deep Frontier goods, building-tool and map-object icons must read as part of the vanilla
icon set. The numbers below were measured on 2026-10-21 from the installed game's own
sprites (Timberborn 1.1.2.8, `Timberborn_Data/resources.assets`), not from screenshots.

## Evidence and tools

- `tools/asset-pipeline/export_vanilla_icon_references.py` exports every vanilla `Sprite`
  (full authored canvas) to `outputs/vanilla-icons/<Name>.png` plus `index.json`
  (canvas, sprite rect, tight rect). Local review reference only; never shipped.
- `tools/measure_icon_style.py <png>...` prints canvas, alpha bounds, padding, ink colour,
  luminance and shadow fraction per icon (run with `PYTHONPATH=tools/asset-pipeline/unitypy`).
- `tools/native_icon_style.mjs` is the single renderer that applies these conventions.
- `tools/review_native_icons.mjs <folder>` audits every shipped icon against the contract
  and writes 1x/2x contact sheets beside vanilla references.

## Measured conventions

| | Goods (`Sprites/Goods/*Icon`) | Building tools / map objects |
|---|---|---|
| Canvas | 80 x 80 RGBA (54 of 56 vanilla) | 112 x 112 RGBA (276 of 278; two 116 x 100 outliers) |
| Artwork extent (largest side / canvas) | 72-93 % (16 sampled) | 68-96 % (16 sampled) |
| Alpha padding incl. shadow | 2-20 px (typically 6-13) | 2-22 px (typically 6-16) |
| Ink | flat rgb(202,172,107) `#caac6b`, no gradient | flat rgb(187,161,108) `#bba16c` |
| Line width (2 x ink area / edge, fills included) | 3.5-5.6 px (median 4.3) | 2.7-3.9 px (median 3.1) |
| Shadow | black, offset 0 / +3 px (straight down), blur sigma ~0.5, opacity ~0.95: a hard under-line | black, offset 0 / +3 px, blur sigma ~2.5-3, opacity ~0.95 of the blurred line: a soft halo, heavier below |
| Light direction | from directly above (shadow straight down, no lateral offset) | same |
| Fills | selective solid fills in the ink colour (bolt, drops, dots, trefoils) | same, sparingly |
| Drawing | monochrome outline, rounded caps, slightly hand-inked | hand-inked, wobbly line ends, mostly front elevation of the real building, often with a ground line |
| Background | fully transparent; no frame, panel or colour | same |
| Sidecar (official examples) | `{"generateMipmap":true,"mipmapCount":-1,"ignoreMipmapLimits":true,"textureFormat":"RGB32"}` (OverwritesExample BadwaterIcon) | `{"isSprite":true}` (ShantySpeaker icon) |

Shadow parameters were fitted by least squares on Gear, Plank, Paper, Log (goods) and
Smelter, LargeWarehouse, Refinery, Forester, OilPress, GravityBattery (buildings).

## Authoring contract (Art/Icons/<Id>.svg)

- `viewBox="0 0 256 256"`, no root width/height, single ink colour (any value; the renderer
  uses only coverage), no text, raster images, gradients, filters, styles or opacity.
- Goods: stroke 11 (details >= 8) -> 3.4-4.8 px measured at 80. Buildings/map objects:
  stroke 6 (details >= 4) -> 2.7-3.6 px measured at 112. Round caps and joins.
- Keep the artwork within the extent band above and >= 16 viewBox units clear at the
  bottom for the shadow; the renderer throws otherwise.
- Building icons trace the approved model: late-game buildings follow
  `outputs/lategame-studies/<Id>-front*.png`; the grocery follows the timber market hall
  study `outputs/grocery-market-study/GroceryMarket-front-right.png`.
- Keep icons distinct from vanilla goods: no plain drop (Water), barrel-with-bolt (Biofuel),
  flask (Extract), oil can (Grease), gear (Gear) or iso ingot (MetalBlock) on their own.

The renderer adds the hand-inked wobble (deterministic displacement, seeded by icon name),
the vanilla ink, canvas and shadow, and writes the sidecar for the icon kind.

## Generators

| Generator | Icons | Output |
|---|---|---|
| `tools/create_frontier_expansion_icons.mjs` | 44 expansion goods, DeepOre, DeepAlloy, 17 late-game buildings, DeepDrill/DeepMine/DeepProcessor, DeepOreSource/DeepOreVein | `src/DeepFrontier/Data` |
| `tools/create_restaurant_icons.mjs` | civic/aquaculture goods and buildings (incl. GroceryStore market hall) | `src/DeepFrontier/Data` |
| `tools/create_construction_icons.mjs` | 7 construction buildings, 5 mineral goods, 4 map sources | `src/DeepFrontier/Data` |
| `tools/create_structural_icons.mjs` | 15 structural platforms | `outputs/structural-integration`, promoted by `tools/promote_style_exports.ps1` |
| `tools/create_research_icons.mjs`, `tools/create_hydro_icon.mjs` | MaterialsLaboratory, ReinforcedHydroTurbine | `outputs/research-integration`, `outputs/hydro-integration` |

`tools/asset-pipeline/build_deep_frontier_assets.ps1` runs the expansion, civic and
construction generators; `tools/stage_deep_frontier.ps1` / `tools/build_deep_frontier.ps1`
(official Mod Builder) package `src/DeepFrontier/Data` unchanged.
