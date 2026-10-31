# Steel platforms, overhangs, bridges and dynamic legs

Target: Timberborn 1.1.2.8, Iron Teeth. Research of 2026-10-29 (decompiled 1.1.2.8 DLLs with `tools/dotnet/ilspycmd.exe`), updated to what was built.

User request, 2026-10-29: "bigger platforms with dynamic legs (since our 3x3 platform requires all feet are at the same height, we want to allow reinforced steel ones to have 4 different leg heights if the user wants to place of the legs be higher or lower, and also able to connect to and sit on top of non flat topped buildings (going through/into the building) allowing for easier building on top of existing infrastructure."

Labels: **[S]** source evidence (decompiled code or blueprint JSON); **[R]** runtime fact recorded in `tools/STATUS.md`; **[H]** hypothesis, not verified in game.

| Slice | What | State |
|---|---|---|
| 1 | Steel cantilevers 10/12/15, truss bridges 8/10/12/15, columns H1–H6, decks 3×3/5×5 (native data only) | Built 2026-10-29; not run in game |
| 2 | **C2, assisted placement ("dynamic legs")**: one click places a deck and a column stack per corner, each as long as its bed needs | Built 2026-10-31; compiled and statically checked; not run in game |
| 3 | **D1, roof hardpoints ("legs into buildings")** | See section 5 |

---

## 1. Native platforms, supports and placement (1.1.2.8) [S]

### 1.1 Block model (`Timberborn.BlockSystem`)

- `BlockObjectSpec`: `Size`, a flat `Blocks` array indexed `(z*Size.y+y)*Size.x+x`, `BaseZ`, `Overridable`, `Flippable`, `Entrance`. Each `BlockSpec` has `MatterBelow` (Ground, GroundOrStackable, Air, Any, Stackable), `Occupations` (None, Floor, Bottom, Top, Corners, Path, Middle; All = -1), `Stackable` (None, BlockObject, UnfinishedGround), `OccupyAllBelow`, `Underground`.
- A **foundation** block is one whose `MatterBelow.IsSolidMatter()` (Ground, GroundOrStackable, Stackable).
- `BlockValidator.BlocksValid` checks every block: fits in the map, no conflict with a non-overridable object's occupation flags, no Top block under a block that needs Air below, `OccupyAllBelow`, terrain, underground rules, then `MatterBelowValidator`. Only occupied blocks meet terrain or objects.
- `MatterBelowValidator.Validate` looks only at the cell below: Ground needs terrain there; GroundOrStackable also accepts `StackableBlockService.IsStackableBlockAt` (unfinished stackables count); Stackable needs a stackable block; Air needs no terrain and no Top object below; Any always passes.
- There is no "anything solid below" option and no OR across blocks: every foundation must pass alone.
- `BlockObject.IsValid()` = `BlocksValid` and every `IBlockObjectValidator`. `BlockObject.IsAlmostValid()` = `BlocksAlmostValid` only: at least one solid-matter block passes everything except its own matter below. Validators are not consulted.
- `AddToService()` throws on an invalid object; `AddToServiceAfterLoad()` deletes an invalid loaded object. So every Deep Frontier placement validator runs on previews only.

### 1.2 Support, deletion and load

- Stack deletion (`TerrainAndBlockObjectsToDeleteFinder`): removing a stackable block or terrain deletes every object with a foundation above it; losing any foundation deletes the whole object.
- `BlockObjectAtopDeletionBlocker` stops deleting an object while something stands on one of its stackable blocks.
- Load: `BlockObjectBatchLoader` orders objects by `CoordinatesAtBaseZ.z`, then by the highest occupation on that layer; `TerrainPhysicsPostLoader` then keeps only objects reachable from the map floor through terrain or stackable blocks. A deck of only `Any` blocks over a non-stackable roof is deleted on load.
- `GroundedConstructionSite` waits for supports to be finished; an object can be queued on top of an unfinished stackable one.

### 1.3 Placement tools

- `BlockObjectTool.Place` asks `PreviewPlacer.GetBuildableCoordinates` (an iterator: previews are validated, removed from the preview services, then each placement is yielded), calls the tool's `IBlockObjectPlacer.Place` for each, then `IUndoRegistry.CommitStack()`.
- The placer is `BlockObjectPlacerService.GetMatchingPlacer(spec)` = `_blockObjectPlacers.SingleOrDefault(p => p.CanHandle(spec)) ?? DefaultBlockObjectPlacer`, chosen once when the tool is created. `BuildingPlacer.CanHandle` claims every template with a `BuildingSpec`; a second claimant makes `SingleOrDefault` throw.
- **The game scene has no undo:** `GameSceneConfigurator` binds `IUndoRegistry` to `DummyUndoRegistry` (`UndoAllowed` false, `CommitStack` does nothing). Undo exists only in the map editor.
- `PreviewPlacer.ShowSinglePreview`: a valid preview is shown buildable; an invalid one is shown red with the validators' message only if `IsAlmostValid()`; otherwise it is hidden. `IPreviewValidator` components only add a yellow warning; they never block placement.
- Picking (`BlockObjectPreviewPicker.CenteredPreviewCoordinates`): the ray stops on a terrain or stackable top face; the footprint is centred on the cursor (odd sizes: the centre cell is the cursor cell) and z = 0 of the object is the cell above the picked face, minus `BaseZ`.
- `BlockObject.UpdateTransform` mirrors a flipped object by scaling the entity -1 in X.
- `ToolDescription.Builder.AddUpdatableSection` sections are updated every frame while the tool panel is shown (`DescriptionPanelController.UpdateSingleton`).

### 1.4 Native auto-extending supports: none

No native component sizes legs at placement time. The closest: `WaterInputPipe` (visual segments to a bed, no blocks), `OccupyAllBelow` (reserves cells to the map floor, not a support) and `DrivewayModelsSpec`. Deep Frontier's `AdaptiveSupports` (fish hatchery posts) copies the WaterInputPipe pattern.

### 1.5 Vanilla references

| Template | Size | Blocks | Cost / science |
|---|---|---|---|
| Platform | 1,1,1 | GroundOrStackable, Top+Corners, Stackable | 6 Plank / 100 |
| TriplePlatform | 1,1,3 | Corners, Corners, Top+Corners | 10 Plank / 200 |
| MetalPlatform3x3 / 5x5 | 3,3,1 / 5,5,1 | one centre foundation, the rest Any/Top, all stackable | 30 / 90 MetalBlock |
| Overhang2x1–6x1 | 1,N,1 | first cell GroundOrStackable, the rest Any/Top, SideLine | 6x1: 36 Log, 36 Plank, 12 MetalBlock |
| SuspensionBridge1x1–6x1 | 1,N+1,1 | near end GroundOrStackable, span Air, path edges | 6x1: 24 Log, 24 Plank |

### 1.6 Why the old platforms needed level feet, and why roofs were closed

- A blueprint is one rigid grid. The concrete scaffolds have their four foundations at z = 0, so all four need a bed at the same layer.
- A building's top is a bed only where it is stackable. Deep Frontier makes flat roofs stackable (`tools/roof_deck_content.mjs`); pitched or curved roofs were neither stackable nor pickable.

### 1.7 Navigation over stackable blocks

`NavMeshObjectUpdater.AddEdgesAddedByStackable` (with `GenerateFloorsOnStackable`) lays floor edges from the cell above each stackable block to its four neighbours. `CanAddBlockingEdge` never adds a blocking edge equal to one of the object's own added edges, so an object's `BlockedEdges` cannot remove its own stackable floors.

---

## 2. Deep Frontier before this work

- Structural catalog `tools/structural_content.json` -> `tools/structural_building_content.mjs` (kinds block, dam, overhang, scaffold, sidedeck, and since slice 1 bridge, column, deck), models from `tools/asset-pipeline/structural_geometry.py` and `steel_structure_geometry.py`.
- Concrete side platforms (`Scripts/AnchoredDecks`): a native foundation in an unusual place plus a narrow preview-only validator, the precedent for slice 2.
- Roof decks: flat, open roof cells are stackable (`roof_decks.json`).
- Harmony and placement code touching validation: `StackableTopBlockExemption` (buildings under stackable tops keep working), `StackableBaseLoadOrder`, `AdaptiveSupports`, `AnchoredDeckValidator`, `PreviewNavMesh/*`.

---

## 3. Options considered

**(a) Overhangs** and **(b) bridges**: native data, built in slice 1.

**(c) Large platforms with legs of different heights**

| Route | Verdict |
|---|---|
| C1 native pieces: columns H1–H6 + corner-supported decks, placed in two steps | Built in slice 1. Fully native. |
| **C2 assisted placement** through the native `IBlockObjectPlacer` extension point | **Built in slice 2.** |
| C3 per-instance procedural blocks | Rejected: native code reads `BlockObjectSpec` blocks everywhere; save-corruption risk. |
| One blueprint per leg-length tuple | Rejected: Lmax⁴ templates. |
| Visual-only legs under an all-Any deck | Rejected: deleted on load, no deletion cascade. |

**(d) Platforms on non-flat building tops**

| Route | Verdict |
|---|---|
| **D1 roof hardpoints**: the top cells of non-flat roofs become stackable beds for steel supports only | Slice 3. |
| D2 leg sleeves: clear `Corners` down chosen building columns so columns pass through to the ground | Not built (section 5). |
| D3 Harmony on `MatterBelowValidator`, the load flood and the deletion finder | Rejected: three core patches that must agree or saves lose objects. |

---

## 4. Slice 2 as built: steel decks on legs

### 4.1 What the player gets

Eight tools in Paths → Steel structures: **Steel deck 3×3 / 5×5 on legs (1, 2, 3 or 4 high)**. The deck appears that many layers above the spot under the cursor. Under each corner the preview draws the steel columns that will be built, each reaching down to the first support: the ground (also under water), a platform, a column, a flat roof, or (slice 3) a roof hardpoint. Legs can all differ. One click places the deck and every column; the columns are built first. If a leg cannot reach a support within 12 layers below the deck, or runs into a building, the preview turns red with the reason. The tool panel shows the deck's cost and, live, the columns this spot needs and their extra cost. The manual pieces (columns, decks) stay available.

### 4.2 Data (`tools/structural_building_content.mjs`, `legDeckBlueprints`)

- Catalog: `structural_content.json` `legDecks` = `{maxDepth: 12, columns: [SteelColumnH1..H6], tools: [{id, deck, clearance, name, description}]}`; `legDeckContract` checks ids (`SteelLegDeck<n>x<n>H<1-4>`), the deck kind and the column heights.
- Tool blueprint = a clone of the generated deck blueprint with:
  - size [n, n, clearance+1]; the deck layer at z = clearance is the deck's blocks with its four corner foundations relaxed to Any; **one foot block** at the footprint centre, z = 0: `GroundOrStackable`, no occupation; every other cell empty. The foot is the cell picking puts on the pointed surface, so it is natively valid wherever the tool can be shown, and `IsAlmostValid` keeps an unbuildable preview visible with its message (an all-Any tool would simply vanish when a leg fails: 1.3);
  - the deck's cost and science (separate native unlock per tool, like the concrete platform heights);
  - models: `#Finished` owns no mesh; its children are `#Deck` (the deck's model raised `clearance` layers by `TransformSpec`, with the deck's colliders) and `#SteelColumnH1..H6` (each column's own finished model); `#Unfinished` is the deck's construction model, raised;
  - `SteelDeckToolSpec {DeckTemplate, DeckZ, Columns, ColumnNodes, MaxDepth}`.
- Icons from `create_steel_structure_icon_svgs.mjs` (`legDeck`: three legs of unequal length, collars per clearance layer), rasterized like the other structural icons.

### 4.3 Code (`src/DeepFrontier/Scripts/SteelStructures/`)

- `SteelLegPlanner` (singleton): for each deck foundation (the real deck's solid-matter blocks; no separate leg list) it tries L = 0 (the deck block's own `MatterBelowValidator.Validate`) and then L = 1..MaxDepth with the native `BlockValidator.BlocksValid` on exactly the column blocks that will be built (a stacked column's upper foundation is relaxed to Any: it stands on the cap below). The shortest valid L wins. A cell no column block can hold (off the map, terrain, a non-overridable object's Corners) stops the probe early, because native validation would reject every longer leg for that same cell. Legs longer than 6 stack columns: full H6 columns with the remainder as the bottom column (every split into the same number of columns costs the same). One plan per frame and placement is shared by the validator, the drawing and the tool panel. Every tool template is checked at load (`IPostLoadableSingleton`): sizes, the relaxed deck layer, the foot, the column contract.
- `SteelDeckLegValidator` (`IBlockObjectValidator`, previews of tools only): "A leg runs into a building or another object before it reaches a support" or "A leg finds no support within 12 layers below the deck".
- `SteelDeckLegs` (decorator of `SteelDeckToolSpec`): clones the column nodes to draw the planned columns; a failing leg shows plain one-layer segments down to where its probe stopped. Clones keep their parent's axes and are centred on their cell, so rotation and the native -1 X flip scale draw them on the right cell. Rebuilt only when the layout changes.
- `SteelDeckPlacer` (`IBlockObjectPlacer`, multibound): `CanHandle` = has `SteelDeckToolSpec`. `Place` plans again against the world without previews, then creates every column bottom-up and the deck last, each through the native `BuildingPlacer.Place` (unfinished, or finished with the native PlaceFinished key). `Describe` is the native `BuildingPlacer.Describe` plus a live section. `BuildingPlacer` comes from the container on first use (it is in the same multibinding, so a constructor dependency would be circular).
- **The only Harmony patch: `SteelDeckPlacerClaim`**, a postfix on `BuildingPlacer.CanHandle` that returns false for templates with `SteelDeckToolSpec`, so `GetMatchingPlacer` finds exactly one placer. Checked at mod start (throws on a changed game): `CanHandle(BlockObjectSpec) : bool` only calls `HasSpec<BuildingSpec>`, and `GetMatchingPlacer` still uses `SingleOrDefault`. `CanHandle` is 7 bytes of IL but is only ever reached through the `IBlockObjectPlacer` interface, which Mono never inlines.
- After the click everything is native: columns and deck are ordinary buildings with native support, construction order, deletion cascade and load validation. The tool itself is never an entity and is never saved. Removing the mod patch would leave valid entities.

### 4.4 Changes from the original design

| Design | Built | Why |
|---|---|---|
| Tool deck with leg corners Any | Plus a foot block at the centre of z = 0 | Without one solid-matter block `IsAlmostValid` is false and an unbuildable preview is hidden, so "no support" could not be shown. |
| Visual legs from `AdaptiveSupports` with a tightened probe | Clones of the real column models, placed from the planner's result | The preview draws exactly the columns that are built; no second probe rule to keep in step. |
| `LegCells` in the spec | Legs = the deck's foundations | One source of truth. |
| `Describe` delegates to BuildingPlacer and adds column costs | Native panel plus a live section with this spot's columns and their summed cost | Column count depends on the spot. |
| "Undo removes all of it" | The game has no undo (1.3) | In the map editor the native `CommitStack` after `Place` would group everything; in game, deleting is the only removal. Deleting the deck leaves the columns (native). |
| Clearance family H1–H4 | As designed | Native picking has no height control. |
| 7×7 deck | Not built | It would need a new model, icons and an 8-leg deck (mid-edge foundations), plus four more tool buttons; the 5×5 on legs covers the request, and content sprawl is to be avoided. The planner already handles any number of foundations, so a 7×7 is data plus a model later. |

### 4.5 Checks

- `tools/validate_steel_leg_decks.mjs` (validate_all `steel_leg_decks`): catalog vs blueprints, the full tool block contract, deck corners, column contract, models and colliders, cost and science, loc rows, icons, sounds, tool group, and the C# wiring (bindings, placer claim, the single Harmony patch and its checks). A broken tool fails explicitly.
- Runs the generators through `building_sounds.json`, `automation_content.json` (role none, MetalPlatform precedent), `building_asset_catalog.json` (art stage `tool`, checked by `audit_building_assets.py`) and `material_cost_context.json`; `audit_progression.mjs` treats the tools like the structures they place.
- `AllBuildingsAcceptance` skips the tools (never entities).

### 4.6 In game, still to test

See section 6.

---

## 5. Slice 3: roof hardpoints

Planned: a generator step beside `roof_deck_content.mjs` makes the top cell of every non-flat roof column a native stackable bed for steel supports only, with a validator that keeps every other object off it and a column sleeve that enters the roof.

---

## 6. In-game test list

Not yet run. Acceptance runs need someone to click the launch dialogs.

1. **Toolbar and panel.** Paths → Steel structures shows the eight "on legs" tools with distinct icons. Unlock one (native science prompt). The panel shows the deck cost; hovering a spot adds "Legs at this spot: N steel columns, M layers in all" with the summed column cost; hovering a spot where the deck rests directly shows "no columns are needed".
2. **Flat ground.** 3×3 H2 on flat ground: preview shows four 2-high columns; click; four SteelColumnH2 sites and one SteelDeck3x3 site appear; builders build the columns first, then the deck.
3. **Slope / terraces.** On a hillside, legs of different lengths in the preview match the columns built (count and heights, one by one).
4. **Over water.** Legs standing in a pond reach the riverbed.
5. **On a platform / existing column / flat roof deck.** A leg ends on it; where a corner sits directly on a support, no column is placed there.
6. **Long legs.** A 5×5 H4 over a deep valley: a leg of 7–12 layers is two stacked columns (shorter one at the bottom); 13+ layers: red preview "no support within 12 layers".
7. **Blocked leg.** A leg landing on a non-flat building roof (before slice 3) or crossing a building: red preview "runs into a building".
8. **Rotation and flip.** Rotate and flip the tool: the columns are drawn and built under the deck corners in every orientation.
9. **Deletion.** Delete one column under a finished deck: blocked while the deck stands (native). Delete the deck: columns remain.
10. **Save/reload.** Save with decks and columns finished and unfinished; reload; nothing is deleted.
11. **Preview cost.** `tools/start_preview_cost.ps1` with a leg deck tool hovering a slope: frame time comparable to the plain deck.
12. **Unreachable warnings.** Note whether the tool preview shows native reachability warnings; the built columns and deck must become reachable as usual.
