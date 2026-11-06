# Bigger small maps ("skyblock" padding)

Status 2026-10-29: feasibility study plus a scratch prototype. Nothing in `src/`, the real Data, `tools/map_variants` or `Documents/Timberborn/Maps` has changed, and nothing has been built or loaded in the game. Evidence comes from the Timberborn 1.1.2.8 DLLs and Map Transformer 11.0.0 (`3798650616/version-1.1/MapTransformer.dll`), decompiled with `tools/dotnet/ilspycmd.exe`.

## The idea

Small maps (Diorama is 50 × 50) have no room for the late-game footprints: the 20 × 15 reactor, the 12 × 12 launch pad, the Deep Mine and Deep Drill (10 × 11, 11 × 9). The user asked whether a map can be made bigger in X/Y, with the original terrain kept as an island and the added area left as empty air down to the bottom, like a Minecraft skyblock that players build outward from.

## Verdict

**Partly feasible.** The map can be made bigger, and the added area can have no terrain at all. But Timberborn has no real void: a column with no terrain is a **solid, flat bedrock floor at z = 0**. You can walk on it, build on it, and water collects on it. Nothing falls through and nothing drains out of the bottom.

The result is not a floating island. It is the original island standing on a wide, flat lowland at level 0. For the user's goal (room for big buildings) this works better than a void would: every large building can go straight onto the floor without supports.

**Recommendation:** ship padded maps as pre-made `.timber` files. Build them with a new `pad` operation in `tools/prepare_deep_frontier_map.py`, which reproduces Map Transformer's *Resize Map* (Empty fill) on the packed file. Leave the edges where rivers leave the map unpadded, so the river mouths stay on the map edge. The Diorama prototype (128 × 128, island at x 39–88 along the south edge) passes the full static validation, including the complete game-loop check, with 37 of 46 building sites on the new floor.

## 1. Columns without terrain

**Verdict: supported by the game, and they behave as bedrock ground at z = 0.**

- **Terrain data.**
  - `TerrainMap.IsTerrainVoxel(coords)` returns `true` for `z < 0` inside the map, so the cell under level 0 always counts as terrain.
  - `TerrainService.Underground` and `OnGround` read it, so `OnGround((x, y, 0))` is true for an empty column.
  - `ColumnTerrainMap.LoadColumns` creates a `TerrainColumn(0, 0)` for an empty column (floor 0, ceiling 0).
  - `ColumnTerrainMap.RemoveTerrain` keeps that column when its last voxel at z = 0 is removed (`column.Ceiling = 0`).
  - `MapIndexService` (stride X + 2, margin 1) is size-agnostic.
- **The game already makes and ships such columns.**
  - The Dirt Excavator (`Terraforming.Drill.TryDrillTerrain`) digs its 5 × 5 footprint down to level 0 inclusive (`while DrillingLevel >= 0`).
  - The built-in maps already contain columns with no voxels at all: Plains 367, Lakes 1,781, Terraces 873. Many of them are dry. Diorama has none.
- **Placement.**
  - `MatterBelowValidator.AtGroundLevel` and `UndergroundTerrainValidator` both test `Underground(z − 1)`, which is true at z = 0. So `Ground` and `GroundOrStackable` buildings are valid on the floor.
  - `MatterBelow: Air` blocks are invalid there (`AboveGround` is false). Nothing can count as "hanging over the void" at level 0.
- **Terrain physics.** `TerrainPhysicsPostLoader.GetInitialCandidates` floods from every (x, y, 0), and the floor counts as support. Objects on the floor are kept on load.
- **Navigation.** `TerrainNavMeshUpdater.AddTerrainToNavMesh` adds walkable nodes wherever `OnGround` is true, which includes z = 0 on empty columns.
  - Beavers need a ramp or stairs to get from the island down to the floor, as with any height step.
- **Rendering.**
  - `TerrainMeshManager.UpdateCodeForCoords` builds the surface shape from `Underground(below)` and `Underground(self)`. An empty column therefore draws a flat terrain top at world height 0.
  - Cells outside the map are not terrain, so the island keeps its cliff faces down to the floor.
  - Nothing is drawn below z = 0. Exactly how the outer border of the floor looks needs an in-game check.
- **Camera.** `CameraService.ClampTarget` clamps the target to the terrain size ± `MapMargin` 50, so it follows the larger map. It does not look at the terrain.
- **Assumptions about ground at z = 0.** In the game, nothing assumes there is a voxel at z = 0. The gap is in Deep Frontier's own map tool:
  - `check_object` and `building_block_problems` required a voxel below a ground block;
  - `rect_candidates` skipped level 0.

  The prototype corrects all three to the game's rule; see "Changes to the map script".

**A true void would need patches to the core.** It would take Harmony patches to:

- `TerrainMap.IsTerrainVoxel`;
- `TerrainService.Underground` and `OnGround`;
- `MatterBelowValidator`;
- `TerrainPhysicsPostLoader`, which floods from z = 0;
- the navmesh and the terrain mesh;
- `WaterSimulator`, whose water columns always start at floor 0.

You would also need a new water sink. That goes against "official methods first", and it is not recommended.

## 2. Water

**Verdict: water collects on the floor. The map edge is the only drain, and it is a perfect one. There is no placeable drain in the game.**

- **The map edge is a sink at any height.**
  - `WaterSimulator.CreateColumns` gives every margin column (outside the map) `WaterColumn(0, maxColumnHeight)`.
  - The simulation tasks (`OutflowsUpdateTask.Run`, `WaterParametersUpdateTask.Run` and the contamination tasks) loop only over the in-map cells (`for i < _xMapSize`, index `i + 1 + (y + 1) * stride`).
  - So margin columns never gain depth. Any water that flows into them (`GetOutflow` against a target of floor 0 and depth 0) disappears.
- **Water on the floor.**
  - A floor column is a water column with floor 0. Water that falls off the island lands on it and spreads like water on any flat ground.
  - `GetOutflow` subtracts `WaterSpillThreshold` (0.1, `WaterSimulator.blueprint.json`) when the target is empty and on the same floor. So a spreading sheet only moves forward while it is deeper than 0.1.
  - Where the floor reaches the map edge, the water drains away. A leftover film under 0.1 stays until it evaporates.
- **Evaporation does not drain anything.**
  - The rate is per column: `NormalEvaporationSpeed` 0.0001, or `FastEvaporationSpeed` 0.001 below 0.02 depth. It is multiplied by `WaterEvaporationMap` modifiers (soil saturation, about 1).
  - Large areas evaporate no faster per column.
- **No drain object.**
  - The only official ways to remove water are the map edge, pumps and other water inputs (`IWaterRemovalService`), and evaporation.
  - `BadtideDrain` is a badwater *source* that switches on in badtides.
  - `WaterMapBoundary` only blocks the edge cells next to a water source that sits on the map edge.
- **Design consequence: keep the river mouths on the map edge.**
  - In Diorama the only wet edge cells are on the south edge (x 10–12, water floor 1).
  - The prototype pads west, north and east only, with an offset of (39, 0). The river still leaves the map exactly as before, and in normal play the island's water never reaches the floor.
  - Floods or badtide overflow that spill off the old west, north or east edges fall onto the floor. They spread toward the new edge and drain there, leaving thin puddles. Contaminated water contaminates the soil it touches, as it would anywhere.

## 3. Building outward

**Verdict: players build directly on the floor. Reclaiming land upward from z = 0 is possible but limited by dirt, and it is not needed.**

- **Terrain Block** (`TerrainBlock.IronTeeth`: 4 Dirt, 1,000 science).
  - It has `MatterBelow: Any`, `Stackable: UnfinishedGround`, `CanBeAttachedToTerrainSide`, a `GroundRaiserSpec` and a `TerrainPhysicsBlockObjectValidatorSpec`.
  - When finished, `GroundRaisingService.OnEntityDeleted` turns it into a terrain voxel.
  - `TerrainPhysicsValidator.TerrainHasSupport` accepts it if terrain or a finished stackable block (`IsFinishedStackableBlockAt`) is directly below. Otherwise it must be within `MaxSupportDistance` = 3 horizontal steps of a supported voxel.
  - So a Terrain Block can go:
    - on the floor at z = 0, and stacked from there;
    - on platforms;
    - on the stackable tops of the mod's steel columns and decks;
    - up to 3 cells sideways off any supported terrain, such as the island's cliffs.
- **Platforms and the mod's structures** (`tools/structural_content.json`). All of these need `GroundOrStackable`, `Ground` or a stackable surface below, so they can stand on the floor:
  - vanilla Platform (6 Planks), Double and Triple Platforms, Metal Platforms 3×3 and 5×5;
  - steel columns H1–H6 (5–30 High-Grade Steel + 9–24 Concrete);
  - steel decks 3×3 and 5×5 (27/75 High-Grade Steel + 38/70 Concrete);
  - steel cantilevers (10–15 tiles, anchored);
  - concrete scaffolds.

  The mod's decks and cantilevers are useful for bridging from the island's top to buildings on the floor, or for stacking above the floor. They are not needed to hold anything up.
- **Dirt Excavator** (2,000 science; 100 Gear + 100 Treated Plank + 50 Metal Block; 200 hp; 4 workers).
  - Its `Dirt` recipe makes 4 Dirt per 6-hour cycle. Each finished cycle removes exactly one terrain voxel from its 5 × 5 footprint (`Drill.OnProductionFinished`).
  - Dirt is therefore conserved: one voxel dug gives one Terrain Block.
  - On the bare floor an excavator finds nothing to dig.
- **Cost of reclaiming land.**
  - Diorama holds 12,576 terrain voxels in total. The 13,884 floor cells of the 128 × 128 prototype would need more than the whole island to raise them even one layer.
  - Building land upward is practical for ramps, terraces and small foundations, not for whole districts. The floor is already buildable, so large buildings go straight onto it.
- **Getting down.** The island's south edge is 1–2 layers above the floor; elsewhere the cliffs are up to 16 layers high. Stairs, ramps or the mod's ladders connect the two levels.

## 4. Making the enlarged map

**Verdict: (a) pre-made variant files. Map Transformer already has the operation; the script mirrors it.**

**Map Transformer** already has the operation, *Resize Map* (`MapOp.ResizeXy`). It offers `EnlargeFill.Empty`, `CopyEdge` and `Mirror`, with a pivot: the offset is `AnchorOffset = pivot · new / old − pivot`. Its components handle the parts of the map like this:

- `TerrainMapTransformComponent` copies the voxels (`MapIndexCopy.CopyTerrainVoxels`) and leaves unmapped columns empty under Empty fill.
- `WaterTransformComponent` rebuilds the water columns, copies depth and contamination by matching floor, and creates a **new, empty** `ColumnOutflows` array.
- `SoilMoistureTransformComponent`, `SoilContaminationTransformComponent` and `WaterEvaporationTransformComponent` copy values by column slot (`CopyColumnFloats`).
- `PlantingTransformComponent` re-lays out the planting map.
- `BlockObjectTransformComponent` moves every BlockObject (`UpdateValues`).

**(a) Pre-made files with the new `pad` operation (recommended).**

- `pad_xy` reproduces the same result directly on the packed `world.json`:
  - every packed per-column array is re-laid out (index = slot · X · Y + y · X + x) for terrain, water depths, moisture, soil contamination and evaporation;
  - added cells get the values the game writes for an empty column: water `0`, moisture `0`, contamination `0`, evaporation `1`;
  - saved water flows are reset to `0`, as Map Transformer does. They store unpacked `Index3D` targets in the old stride (`ColumnOutflowsPackedListSerializer`), so they would point at the wrong cells after the resize;
  - BlockObject coordinates and the thumbnail camera move by the offset;
  - `MapSize.Size` and `map_metadata.json` Width/Height follow the new size.
- It refuses to run when:
  - it meets a singleton it does not know;
  - an entity component other than `BlockObject` saves coordinates;
  - the new size is above `MapSizeSpec.MaxMapSize`;
  - the operation would crop the map.
- `check_pad` independently verifies the result against the unpadded map.
- Native cross-check: open Diorama in the map editor and run Transform Map → Resize Map 128 × 128, pivot (25, 0), fill Empty. 25 · 128 / 50 − 25 = 39 gives offset (39, 0). Then compare `ResizedMap.timber`.

**(b) Enlarging at new-game load time (not recommended).** Map Transformer cannot do it: its button runs only from the options menu in a game or the map editor, it writes a new save, and it asks for a reload. Doing it ourselves at load time would mean:

- a Harmony patch on `MapSize.Load` to change Size;
- re-laying out every per-column array before `TerrainMap.Load`. `MapIndexService.Unpack3D` reads with the new size, so the old data would throw `IndexOutOfRangeException`;
- moving every entity before it is created.

That re-implements Map Transformer inside the loader. It would collide with the map hook agent's new-game setup and with Map Transformer's own `MapSize` patch, and it could not be validated statically.

**Pivot choice.** Pad away from the edges where water leaves the map (section 2). Choose the size per map. 128 × 128 makes Diorama larger than the hook agent's small-map limit of 11,176 cells (`tools/map_setup.json`).

## 5. Size limits and performance

- **Size limit.**
  - `MapSizeSpec.MaxMapSize` = 256 is read only by the new-map UI (`Timberborn.MapRepositorySystemUI`). `MapSize.Load` and Map Transformer's dialog do not enforce it, and the engine arrays are sized from the map.
  - `pad_xy` still caps at 256, the largest size the game ships and tests (Plains, Lakes, Terraces).
  - Height is limited separately: total height ≤ 254 (`WaterColumn` floors are bytes, `docs/map-height.md`).
- **Cost.** An empty floor costs about the same per cell as any map of that size, minus trees and entities.
  - Water, moisture and contamination tick every in-map column. `OutflowsUpdateTask.UpdateOutflows` returns early for dry columns, but `WaterParametersUpdateTask` still visits each one.
  - The padded Diorama costs less than a quarter of Plains.

| At 66 total layers | Diorama 50² | Padded 128² | Plains 256² |
|---|---:|---:|---:|
| Columns simulated (water, soil) | 2,500 | 16,384 | 65,536 |
| Navigation nodes (X+2)(Y+2)(Z+2) | 0.18 M | 1.15 M | 4.53 M |
| Navigation memory (~135 B/node, `docs/map-height.md`) | ~25 MB | ~155 MB | ~611 MB |
| `BlockService` (≈80 B/cell) | ~13 MB | ~87 MB | ~346 MB |
| Prototype file | — | 151 KB (`world.json` 2.1 MB) | — |

These are estimates from the constructors. Measure them in game: private bytes, load time and FPS against vanilla Diorama.

## Prototype

Built and validated in the scratch mirror `%USERPROFILE%\dfs\skyblock`. Nothing was written to `Documents/Timberborn/Maps`.

- **Variant.** `tools/map_variants/diorama-skyblock.json` in the mirror; a copy is in `outputs/skyblock/diorama-skyblock.json`. It contains:
  - `"height": {46, 66}`, `"mapSize": {128, 128}`;
  - `"pad": {"size": {"X": 128, "Y": 128}, "offset": {"X": 39, "Y": 0}}`;
  - 19 placements and 46 sites.
  - The output directory points at the mirror. Change it to `Documents/Timberborn/Maps` only when shipping.
- **How it was filled.** The planner proposed most placements and sites (the run used a scratch driver with a higher candidate limit; see the notes below). Some were authored by hand:
  - four Human Record Caches on the floor (Diorama's ruins give only one cache cluster);
  - the reactor at (60, 52, 0) and the launch pad at (45, 52, 0), on the floor below the north lake cliff;
  - four Deep Ore Sources (16,000 Deep Ore);
  - a second Deep Drill and a second Deep Mine.
- **Output.** `%USERPROFILE%\dfs\skyblock\outputs\skyblock\Deep Frontier - Diorama Skyblock.timber`, sha256 `4cd162a5…26e2`, 150,720 bytes.
- **Validation.** `build` reports **OK with 0 errors**:
  - all eight loop-coverage stages are met;
  - no declared unmet items and no accepted gaps;
  - `check_pad` passes: the island is byte-identical at its offset, the added columns are empty, flows are reset, and all 638 source entities have moved by exactly (39, 0).
  - Evidence: `outputs/skyblock/diorama-skyblock-validation.json` and `outputs/skyblock/diorama-skyblock-preview.png`.
- **Regression.** The four shipped variants (Plains, Plains Hard, Lakes, Terraces) were built with the script before and after the change. Their `.timber` entries and validation reports are identical: 0 errors.
- **Built-in check.** The hook agent's `builtin` command skips the padded variant (`is_runtime_variant` change below).

### Changes to the map script (for merging)

`tools/prepare_deep_frontier_map.py` in the working tree is being rewritten by the map hook agent, so the change ships as an anchor-based applier, not an edit:

```
python outputs/skyblock/apply_skyblock.py tools/prepare_deep_frontier_map.py outputs/skyblock/pad_xy_block.py
```

`outputs/skyblock/skyblock-pad.patch` shows the same diff against the snapshot it was tested on. The changes:

1. **New, additive.** `PAD_PACKED`, `PAD_RESET`, `PAD_UNCHANGED`, `pad_xy`, `check_pad` and `prepare_source`, inserted before the blueprints section.
2. **`load_variant`.** Accepts an optional `"pad"` key, and only on written variants (`output` not null).
3. **`build`.** Runs `prepare_source` (height, then pad), adds `check_pad` errors, and records `report['pad']`.
4. **`plan`.** Plans on `prepare_source(...)` for written variants.
5. **Native ground below z = 0.** This is a correction, not an addition. It cannot change maps whose sites avoid empty columns; the regression shows no change.
   - `check_object`: `below < 0 or solid[below]`.
   - `building_block_problems`: the same rule.
   - `rect_candidates`: allows level 0.
6. **`is_runtime_variant`.** Adds `and 'pad' not in variant`, so the built-in new-game setup never applies a padded variant's coordinates to the unpadded built-in map.

**Notes for the map hook agent.**

- Its future `tools/map_setup_content.mjs` must skip padded variants in the same way as `is_runtime_variant`.
- `mapSize` in a padded variant is the padded size, because validation runs on the padded source.
- The `builtin` message for skipped variants ("hard variant or not a built-in source") does not mention padding.

**Planner limit.** `Planner.flat_site`'s default `limit=4000` is too small for a large empty floor: tens of thousands of level-0 candidates sort first, and the nearest ones are already claimed. The prototype raised the limit from a scratch driver; the repository code is unchanged. Raise or parameterise it when padded maps become real.

## In-game test steps (attended; not run)

The user is playing, and acceptance runs need the startup dialogs clicked. Test runs in Memory Test rotate the user's autosaves; restore and backdate them afterwards.

1. **Load.** Copy `Deep Frontier - Diorama Skyblock.timber` from the mirror into `Documents/Timberborn/Maps`. Start a new Iron Teeth game on it with Map Transformer enabled.
   - The log shows no loading issues: no terrain cut-off, nothing "not supported by terrain physics", no deleted objects.
   - The layer slicer reaches 66.
2. **Look.**
   - The floor renders as flat ground at level 0 out to the 128 × 128 border, and the island cliffs render down to it.
   - Check the floor's outer border, the terrain colour at altitude 0, and the camera reach (map margin 50).
3. **Navigation.** Build stairs or a ramp from the island's south edge (1–2 layers up) to the floor. Beavers walk onto the floor and across it to the far border.
4. **Building on the floor.**
   - Place a ground building, a Platform, a steel column with a deck on it, and the reactor and launch pad at their listed sites. All are accepted.
   - Place a building with `MatterBelow: Air`; it is refused.
5. **Terrain Blocks.**
   - Place one on the floor and stack a second on it.
   - Place one on a finished Platform and one on a steel deck.
   - Place them 1, 2 and 3 cells out from an island cliff. The 4th is refused.
6. **Dirt Excavator.** One on the floor produces nothing. One on the island digs down to level 0, leaving floor.
7. **Water.**
   - The south river still leaves at the map edge.
   - Pour water onto the floor with the dev water tool. It spreads, reaches the border and drains; a thin film stays and evaporates.
   - Repeat with badwater and watch the soil contamination.
   - Run one wet/dry cycle and one badtide, and check whether anything spills off the old west, north or east edges.
8. **Farming.** Plant crops and trees on the floor at z = 0, next to irrigation. Soil moisture on empty columns has not been checked in the source.
9. **Save and reload.** Save, reload and save again.
   - `MapSize` stays 128 × 128 with `MapHeight {46, 66}`.
   - Water, floor buildings and Terrain Blocks survive.
10. **Performance.** Record FPS, private bytes and load time against vanilla Diorama at the same height.
11. **Native cross-check.** In the map editor, run Map Transformer → Resize Map 128 × 128, pivot (25, 0), Empty, on Diorama (also Resize Height to 46/66). Diff the voxels, water and entity positions of `ResizedMap.timber` against the script output.

## Open decisions for the user

1. **Floor or plateau.** The floor at level 0 is what the game can do natively. For a look closer to a skyblock, the map could first get Map Transformer's *Add Bottom Dirt* (N layers under the island, every entity shifted up by N) and then be padded. That gives a tall plateau above a deep floor. It needs the not-yet-built `AddHeight` operation (`docs/map-height.md`).
2. **Alternative: a raised plain at z = 1.** Padding with one dirt layer instead of nothing makes the floor diggable. The Dirt Excavator would get a large dirt reserve, which affects balance. It also loses the "empty" look, and Map Transformer cannot produce it with Empty fill.
3. **Which maps and sizes.** Diorama 128 × 128 is the prototype. Cliffside is the other small map. Up to 256 × 256 is possible.
4. **Shipping.** Ship padded maps as new `Deep Frontier - <Map> Skyblock` files next to the built-in new-game setup, which still covers the unpadded built-in maps.
