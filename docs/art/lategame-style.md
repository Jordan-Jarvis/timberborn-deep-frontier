# Late-game building style (Deep Frontier)

User direction, 2026-10-21. These are **late-game buildings**: large, grand and tall, with proper animations for each building type. They must still sit naturally beside vanilla Iron Teeth buildings. Use the native art language and add late-game materials: concrete, riveted steel, forged metal sheet, glazing and instrument lighting. Do not shrink or flatten a design to make it fit in.

This guide covers the twenty buildings that are still prototypes, plus later passes on the detailed catalog. Authoring helpers are in `tools/asset-pipeline/lategame_kit.py`. Studies render through `tools/asset-pipeline/render_lategame_studies.py`. Each building lives in its own `tools/asset-pipeline/lategame_<Ident>.py`.

## What reads as Timberborn

- **Big, simple masses with a few bold details.** A building has to read at normal game zoom. One or two strong shapes plus a clear roof matter more than hundreds of small parts.
- **Chunky native materials.** Dark Iron Teeth timber with oversized grain, teal `RoofPlanks` roofs, orange plaster infill, dark painted metal, and the native multi-pane windows and Barrack doors.
- **Visible structure.** Timber or steel frames, braces and banded tanks. Machinery is shown, not hidden in a box.
- **Warm, worn and handmade.** Industrial, but never sleek sci-fi. Panels are bolted, tanks are banded, chimneys are soot-capped.

## Textures: reuse the game's

User direction, 2026-10-21: surfaces reuse shipped Timberborn textures. Any new texture has to match them. `render_lategame_studies.py` rejects any material outside `lategame_kit.NATIVE_SLOTS`:

| Slot | Shipped material | Use |
| --- | --- | --- |
| `WOOD` 0 | BaseWood_DarkBrown.IronTeeth | Timber frames, doors, trim |
| `PLANK` 1 | IrregularPlanks_DarkBrown.IronTeeth | Timber cladding, gable infill |
| `IRON` 2 | BaseMetal.IronTeeth | Structural steel, machinery, tanks |
| `ROOF` 3 | RoofPlanks.IronTeeth | Teal roofs and vaults |
| `BRASS` 7 | Details.IronTeeth (metal strip) | Flanges, fittings, rivet heads |
| `CONCRETE` 27 | Plaster_White.IronTeeth | Cast concrete plinths, walls, slabs |
| `ORANGE` 28 | Plaster_Orange.IronTeeth | Native orange infill |
| `FORGED` 29 | IrregularPlanks_MetalForged.IronTeeth | Riveted sheet cladding |
| `WINDOW` 30 | WindowsAtlas.IronTeeth | Native window and door pieces only |
| `FOLK_WOOD` 31 | BaseWood_Brown.Folktails | Native Double Lodge rails |
| `PAINTED` 32 | PaintedMetal.IronTeeth | Painted machinery, tank bands, panels |
| `GREYWOOD` 33 | BaseWood_Grey.IronTeeth | Weathered grey timber |
| `GREYPLANK` 34 | IrregularPlanks_Grey.IronTeeth | Grey cladding |

Slots 32–34 are a late-game addition to the 32-slot palette. The harness authors their bounded atlas islands. Export integration must map them to these exact native names. `GLOW` (8) and `CYAN` (25) are allowed only as tiny emissive accents (lamp bulbs, indicator lights), under 4% of faces. No custom smoke or glass meshes: the game supplies particle effects, and windows come from the native atlas.

## What makes it late game

- **Concrete base.** Every building stands on a continuous cast-concrete plinth or lower storey (`CONCRETE`, Plaster_White.IronTeeth), with a proud coping band. No thin timber legs reach the ground.
- **Steel upper works.** Steel portal frames, lattice towers, gantries, riveted panels (`FORGED`), bare structural steel (`IRON`) and painted machinery (`PAINTED`).
- **Material ratio, roughly:** 35–45% concrete and stone, 25–35% metal, 15–25% timber, 10–15% roof. Timber stays as framing, doors, window surrounds and the odd shed, so the native family resemblance holds.
- **Technology tier shows in the details.** Pipes with flanges and valve wheels, gauges, cyan instrument lights (`CYAN`), stacks and vents, insulated tanks, cable trays.

## Silhouette and identity

Every building gets one **hero element** that no other building shares, plus a distinct roof shape. Neighbouring buildings in the same chain must not share a massing. Before modelling, write the hero element and the roof type at the top of the building module.

| Rule | Requirement |
| --- | --- |
| Height | Late-game buildings are tall. Main mass 4–7 layers; the hero element usually 8–14. |
| Footprint | Art first. Declare `FOOTPRINT = (X, Y)` in whole tiles. Geometry must stay inside `0..X`, `0..Y`. |
| Roofline | Vary it: gable, sawtooth, barrel vault, monitor roof, flat roof with parapet, domes. Don't repeat the civic gable cluster. |
| Decks | Only where they have a job: a worker catwalk around machinery, a loading dock, or a roof work platform. Industrial catwalks are steel grating with steel rails, held by brackets off the structure or by concrete piers, never by long timber stilts. No generic wraparound decks. |
| Brackets | Metal plates only at real structural joints. At most one plate cluster per beam end. Never a ring of plates around every roof edge. |

## Hard geometry rules (z-fighting and watertightness)

- No two parallel surfaces may overlap within **12 mm** (`lategame_kit.LAYER_GAP`) unless one is fully buried inside a solid. Trim, panels and bands sit at least **20 mm** proud (`TRIM_PROUD`) of their host.
- When boxes overlap, their top faces must not share a height. Raise one by at least `LAYER_GAP` or bury it.
- The same applies to **bottom faces on the ground**: only one solid may own the ground plane at any spot. Start inner solids `GROUND_SINK` (30 mm) up inside their footing, as `plinth`, `concrete_pier`, `lattice_tower` and `portal_frame` do. The audit treats downward faces as visible.
- Pipe flanges, rails and posts on neighbouring runs need clearance: keep parallel pipes at least the sum of their flange radii apart.
- Panels are a recessed infill behind a proud frame, or a proud plate on a solid core. Never two broad faces in the same plane.
- Closed rooms are watertight from every isometric angle. No see-through seams at corners, eaves or roof joints. Roofs overhang their walls, and gable ends close to the roof.
- Face winding is outward (back faces are culled in game). Kit primitives guarantee this; hand-written `g.add` faces must be counter-clockwise seen from outside.
- No visible interiors. Doors use the native one-tile `building_portal`; windows use the native `architectural_windows` assemblies seated on a real wall plane.

## Grid and access

- One Blender unit is one tile horizontally and one height layer vertically.
- Main door on a whole-cell boundary at layer 0, centred on a tile (`x = n + 0.5`). Record it in `g.doorways`.
- Work floors, catwalks and roof platforms sit at integer layers.
- Leave player stairs to the player. Do not author integral stair flights to the ground, except ladders and short internal stairs on steel structures.

## Animation

Each building has at least **two meaningful animated parts** that show its function. A 121-frame loop at 30 fps must close cleanly. Use the harness kinds: `SPIN_X/Y/Z` (turns per loop), `PISTON_X/Y/Z` (amplitude), `SWAY_X/Y` (angle), `FLAME` (phase), `PULSE` (scale amplitude), `SLIDE_X/Y/Z` (out-and-back travel), `STATIC`. Examples: fans, flywheels, pumps, cranes, drill strings, conveyors, stirrers, beacon shutters, smoke and fire flicker.

## Review

Render with `render_lategame_studies.py --models <Ident> --views front,front-right,rear`. Then run the strict surface audit with a game-distance tolerance:

```powershell
tools/asset-pipeline/blender-4.5.3/blender.exe -b --python-exit-code 1 --python tools/asset-pipeline/zfight_audit.py -- --models <Ident> --epsilon 0.004 --render --fail-on-visible
```

A passing audit is necessary but not sufficient. Look at the renders: silhouette, identity, proportion against a one-tile door, closed shell, and whether it would look at home beside vanilla Iron Teeth buildings.

## Windows with intent

The user rejected copying one window type across every facade. Pick glazing by the room behind it, and vary it between rooms.

`tools/asset-pipeline/native_window_atlas.py` cuts whole cells from the shipped `WindowsAtlas.IronTeeth` (frames painted in, native night glow included): `grid9`, `single`, `triple`, `band4`, `ribbon`, `cross`, `slit`/`slit2` and `porthole`. `atlas_window()` keeps each cell's aspect and seats the pane 56 mm off the wall skin on a real reveal. `glass_curtain()` builds large glazing from the plain native glass tile behind a proud steel or timber mullion grid. These cells are registered in `native_uv_contract.py`, so the civic UV check accepts them.

The Materials Laboratory and Restaurant were reworked on 2026-10-21:
- **Lab, cast base:** nine-pane grids, with high archive bands on the side.
- **Lab, records office:** lancets, framed crosses, and one grand feature window.
- **Lab, testing hall:** full-height curtain glazing, north-light ribbons, eaves portholes, and singles and triples between the piers.
- **Restaurant:** a timber-mullioned dining picture window and grand side windows on the dining floor; front lancets, side crosses and rear triples on the upper floor; kitchen-side grids.
