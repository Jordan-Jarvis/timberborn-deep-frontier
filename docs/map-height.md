# Double map height through Map Transformer

Status 2026-10-22: plan plus scratch prototype. Nothing in `src/`, the real Data or `Documents/Timberborn/Maps` has changed, and nothing has been built or loaded in the game. Evidence comes from the Timberborn 1.1.2.8 DLLs and Map Transformer 11.0.0 (`3798650616/version-1.1/MapTransformer.dll`), both decompiled with `tools/dotnet/ilspycmd.exe`.

## Decision

The user chose Map Transformer (Id `MapTransformer`) as a required mod. With it, height is stored per map:

- Deep Frontier ships its four prepared maps at **46 terrain layers / 66 total**, double the vanilla 23 / 33.
- Every other world keeps the height recorded in its own file.
- Deep Frontier does **not** override `Configurations/MapSize.blueprint.json` (reasons under "Why not change the global spec").

## How Map Transformer sets height (decompiled 11.0.0)

- **Load and save.** `MapSizePatches` adds a Harmony postfix to two methods:
  - `MapSize.Load`: if the `MapSize` singleton has `MapHeight {X, Y}`, it clones `MapSizeSpec` with `MaxGameTerrainHeight = MaxMapEditorTerrainHeight = X − 1` and `MaxHeightAboveTerrain = Y − X`, then calls `Initialize` again. Without the key, the global spec (23 / 33) is used.
  - `MapSize.Save`: it writes `MapHeight` on every save made while the mod is enabled.
  - A tall map therefore raises the in-game terrain cap (`GroundRaiser`'s `TopTerrainLevelValidationConstraint` limit) and the map editor brush cap (16 → 45). It also sets the slicing range (`LevelVisibilityService`) and the block-object top limit (`z < Y`).
- **Where the transform runs.** "Transform Map" is a button in the options menu. `MConfigs` uses `ConfigurationContext` 12, which is Game | MapEditor, so the button works in a game or in the map editor, not at new-game start. The work is done by `MapTransformService.PerformAsync`:
  1. It edits the live session: terrain, column terrain, water, evaporation, moisture, contamination, planting, `BlockObject.UpdateValues` and character positions.
  2. It writes a save named `MapResized` (game) or `Maps/ResizedMap.timber` (editor).
  3. It offers to load that file. Its own warning says the old session "will likely crash" if you keep playing.
- **Operations.**
  - *Resize Map Height* (`MapOp.ResizeHeight`) pads **above**. `MapIndexCopy.CopyTerrainVoxels` keeps every voxel at the same z, leaves new layers empty, and never fills the new top layer (`k < newZ − 1`). Water and soil data are copied slot for slot, matched by floor.
  - *Add Bottom Dirt* (`MapOp.AddHeight`) inserts N solid layers **below** at z = 0. It shifts everything up by N and can add N to terrain and total.
- **Limits.** The dialog only enforces a minimum of 1. The real ceiling is `WaterColumn.Floor`/`Ceiling` as bytes (ceiling = total + 1), so total height must be ≤ 254. 46 / 66 is supported.
- **Other patches.**
  - `HidableModels.ModelsAt/Add/Remove` prefixes grow the per-level list after a live resize.
  - `Ticker.FinishFullTick` is skipped while a transform runs.
  - Map Transformer itself requires Harmony and ModdableTimberborn, which are already Deep Frontier dependencies.

## Why not change the global spec

A Deep Frontier `MapSize.blueprint.json` merge would apply to every world that has no `MapHeight` key, including all built-in maps. `TerrainMap.Load` → `MapIndexService.Unpack3D` loops `k < TerrainSize.z` over the packed z-major array. A stored 23-layer map would be read past its end, an `IndexOutOfRangeException`. `TerrainMap.GetTerrainData` only handles the opposite case: it truncates taller data with the loading issue `LoadingIssue.TerrainCutOffIssue`, and copies only `MaxGameTerrainHeight` layers. With Map Transformer installed, saves carrying `MapHeight {23,33}` would still load, but new games on built-in maps would fail. Per-map height avoids this.

## What Deep Frontier needs

1. **Manifest.** Add this to `src/DeepFrontier/manifest.json` `RequiredMods`:

   ```json
   { "Id": "MapTransformer", "MinimumVersion": "11.0.0" }
   ```

   - `tools/installed_dependency_manifests_1_1.json` already records it (workshop 3798650616, `version-1.1`, game ≥ 1.1.1).
   - `tools/validate_deep_frontier_manifest.mjs` passes with it (prototype: 17 required, status ok).
   - Add Map Transformer to the Steam Workshop "required items" when publishing.
2. **Load order.** Nothing extra. Deep Frontier does not patch `MapSize` and does not override the spec, and RequiredMods already loads Map Transformer first.
3. **Prepared maps at 46 / 66.**
   - The script reproduces Map Transformer's *Resize Map Height* on the packed file. Because the transform keeps terrain at its z and copies water and soil slot for slot, the exact result is:
     - the source `world.json` with `" 0"` appended for 23 × 256 × 256 voxels in `TerrainMap.Voxels`;
     - `"MapHeight":{"X":46,"Y":66}` added after `Size`.
   - The water, moisture, contamination and evaporation arrays are column-slot indexed (`WaterSimulator.PostLoad` copies by slot `i`; the stored floor is not read back), so they stay byte-identical, as do all entities.
   - The native cross-check is to open one prepared map in the map editor, run Transform Map → Resize Map Height 46 / 66, and compare the written `ResizedMap.timber`.
4. **Bottom layers (optional second step).**
   - For deeper lower sectors, the same script can reproduce *Add Bottom Dirt*: fill N bottom layers (not the top one), shift the voxels up, and add N to every `BlockObject.Coordinates.Z`.
   - In the three shipped maps, that is the only coordinate-bearing entity field (15,421 occurrences); `MapThumbnailCameraMover` holds a camera pose.
   - Water and soil slots stay valid because the inserted dirt joins the bottom of each column.
   - Bottom insertion moves every site and must be re-surveyed. It is not in the prototype.

## Code and docs that assume 33 layers

| Place | Change |
|---|---|
| `tools/prepare_deep_frontier_map.py` docstring (lines 22–33), `MapModel` height text | Map Transformer is required; drop "NON-VANILLA" |
| `prepare_deep_frontier_map.py` `build` / `validate_variant` | Apply `resize_height` from the variant's `height`; check `MapHeight` and that the stored layers equal the terrain layers (prototype) |
| Site `top >= total_height` check, `suggest` limits | Already parametric. At 66, the highest base is reactor 47, launch pad 48, Deep Mine/Drill 50 (was 14 / 15 / 17) |
| `tools/map_variants/*.json` | Add `"height": {"terrainLayers": 46, "totalHeight": 66}`. Sites may move to higher terraces (open decision) |
| `docs/maps.md` lines 39–41 (Z budget, base-level table, "z = 32 exactly"), test step 6, follow-up near line 259, SHA table | Rewrite for 66 |
| `tools/STATUS.md` lines 91–92 | Height is per map through the required Map Transformer |
| `docs/dependency-matrix.md:18`, `docs/dependency-reference.md:20,44`, `docs/implementation-plan.md:17,79`, `docs/feature-feasibility.md`, `docs/roadmap.md:11`, `docs/underground-strategy.md` | Map Transformer moves from authoring-only to required at runtime |
| `src/DeepFrontier/Scripts/HydroAcceptance.cs:166,168`, `HydroBasinAcceptance.cs:134` | Test scaffolds hard-code `z < 23`. They are harmless on 33-layer test saves; parameterise them only if they are reused on tall saves |

Runtime C# reads `MapSize` and `MapIndexService` dynamically and needs no change: `ShoreFishing`, `MeltdownService`, `WasteLeak`, `RadiationBuildings`, and `RadiationSimulation` (whose arrays are sized by `WaterSimulator.MaxColumnCount`). The late-game generators (`lategame_building_content.mjs`) have no map-height cap.

## Compatibility

- **Existing saves.** The 40 most recent saves scanned in `ExperimentalSaves/Industrial Acceptance` and `Concrete Acceptance` (none failed the check), `Concrete Test` and the `Poocano` saves already store `MapHeight {23,33}`, because Map Transformer was already enabled (it is in build 124's mod list). They load unchanged at 33.
  - Saves without the key, and the current 33-layer Deep Frontier maps, also stay at 33.
  - Requiring the mod changes no existing world.
- **Making an existing save taller.** Use Map Transformer in game: Resize Map Height to 46 / 66, then load `MapResized`. Nothing moves, so this is safe for Deep Frontier.
  - **Do not use Add Bottom Dirt on Deep Frontier saves.** It moves only BlockObjects and characters. Deep Frontier's `RadiationSimulation` saves absolute cells (`Cells`, `SourceCells`), and other mods' saved coordinates have not been audited.
- **Removing Map Transformer.** Tall worlds degrade to vanilla height: terrain is truncated with a loading issue, and objects at z ≥ 33 are deleted. RequiredMods prevents this while Deep Frontier is enabled.
- **Mods** (build 124 list, log lines ~44–128):
  - **More Tunnels 1.5** (`ImprovedTunnel` unsets terrain at its own cell, `BottomTerrainLevelValidationConstraint`) and **More Tunnels - Ladder** are height-agnostic. With padding above, tunnels gain no depth; that needs bottom layers.
  - **Bob Platforms Extended 1.1.2.1** is data only; vanilla validators let it stack to z = 65.
  - **Extended Builder Reach**, **TimberCommons**, **More Platforms**, **Moddable Weathers** (rain) and **ModdableTimberborn** (areas, game stats) read `MapSize.TotalSize` live, so they work at 66.
  - No installed mod ships a `MapSize` blueprint or patches `MapSize` except Map Transformer.
  - FreeCam, Building Mover, Replatform and No Build Restriction do not reference map size.

## Performance (256 × 256, 33 → 66 total)

Allocations that scale with height, from the decompiled constructors (64-bit references; estimates to be measured):

| Structure | Size rule | 33 | 66 |
|---|---|---:|---:|
| `BlockService` `Array3D<WorldBlock>` (8 refs + 3 ints ≈ 80 B) | 256²·Z | 173 MB | 346 MB |
| Navigation: `NodeIdService` nodes, 258²·(Z+2) = 2.33 M → 4.53 M; about 135 B per node across 6 `NavMeshSource`, 3 terrain and 3 road graph arrays, an id table and bool maps | per node | ~314 MB | ~611 MB |
| `TubeMap` `Array3D<Tube>`, `TransputMap` `List<>[,,]` | 8 B·256²·Z each | 2 × 17 MB | 2 × 35 MB |
| `FlowLimiterService` (3 × 4 B) | 258²·(Z+2) | 28 MB | 54 MB |
| Terrain voxels, terrain physics, water horizontal obstacles, mesh shape codes | about 1 B per cell | ~8 MB | ~15 MB |
| `TerrainMaterialMap` 3 RG16 `Texture2DArray` (GPU) plus CPU copies | 256²·Zt | ~17 MB | ~35 MB |

That is roughly **+0.55 GB RAM** on a 256² map. Other costs:

- **Simulation.** Water simulation, water rendering (`DataTextureArray` depth = column count) and soil moisture/contamination scale with column **slots**, not height. They cost more only if players build more stacked overhangs.
- **Rendering.** Terrain tiles (16×16×8) grow from 768 to 1,536 objects; tiles above the terrain stay empty. Per-tick CPU scales with content, not empty air.
- **Load and garbage collection.** Expect a few hundred ms more at load (the `Array3D` and navigation initialisers visit every cell). Expect longer full GC marks, because about twice as many reference-array slots are scanned.
- **Save size.** The uncompressed `world.json` voxel string grows from 6.4 MB to 9.5 MB on Plains; it compresses well.
- **Camera.** The target clamps to terrain z + 50 margin (`CameraService.ClampTarget`). Default maximum distance is 32·1.3⁶ ≈ 154, so all 66 layers are visible. `ShadowDistanceUpdater.MaxDistance = 150` is fixed.

## Open decisions for the user

1. **Pad above only, or also add bottom layers?** Above only (prototype) keeps every site and the surface where they are and adds 33 layers of build space. Bottom layers (N ≤ 23) give deeper underground sectors but move every site and need a re-survey.
2. **Move reactor and launch-pad sites to higher terraces** now that bases up to 47–50 are legal? Or keep the current checked sites?
3. **Terrain colouring.** `TerrainMaterialMapSpec.AltitudeCeiling` is 22 globally. Players can now raise terrain to 44. Should the colour gradient be left as is, or should Deep Frontier override it (this changes the look of every map)?
4. **Replace or add maps.** Replace the four 33-layer maps in `Documents/Timberborn/Maps`, or ship the 66 versions under new names?

## Implementation steps

1. Apply `outputs/map-height/map-height-prototype.patch`:
   - `resize_height()` and its use in `build`/`validate_variant`;
   - the manifest entry;
   - the `height` block in the four variants.
2. Update the docs and STATUS rows listed above.
3. Run `python tools/prepare_deep_frontier_map.py build tools/map_variants/*.json` (real output folder), then `validate`. Record the new SHA prefixes in `docs/maps.md`.
4. Build with the official Mod Builder and verify the package (`tools/verify_deep_frontier_package.ps1`).
5. Run the acceptance plan.

The prototype mirror (`%USERPROFILE%\dfs\map-height`) built all four variants at 46 / 66 with 0 validation errors. Evidence is in `outputs/map-height/*-66-validation.json`. Only `MapSize` and `TerrainMap` differ from the shipped maps; all entities are equal.

## Acceptance plan

These need an attended run (startup dialogs).

1. With Map Transformer enabled, start a new game on each 66 map. The log shows no truncation issue, and the layer-slicing tool reaches 66.
2. Place a NuclearReactor or LaunchPad high enough that its top occupies z = 65; placement is accepted. A block at z = 66 is rejected (top constraint).
3. Raise terrain with a `GroundRaiser` above 22. Check the rendering and the colour at altitude (decision 3).
4. Load one `Industrial Acceptance` save. It is still 33 high, and its saved state is intact.
5. Save, reload and save again on a 66 map. `MapHeight {46,66}` persists, water depth and contamination match, and the radiation spring state survives.
6. Open one prepared map in the map editor and run Transform Map → Resize Map Height 46 / 66 on its 33 source. Diff `ResizedMap.timber`'s `MapHeight`, voxels, water and entities against the script output.
7. Load the same save at 33 and 66 and record private bytes and load time.
