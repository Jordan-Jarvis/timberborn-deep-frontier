# Deep Frontier asset pipeline

## Map objects and pile goods (2026-10-25)

`tools/map_objects.json` lists the map-object models and the stockpile pile meshes: footprint, height band and triangle ceiling for each. `tools/asset-pipeline/build_map_objects.py -- --models all` builds them from `map_objects_geometry.py`, checks them against that file, saves `src/DeepFrontier/Art/Source/<Id>-ReferenceStudy.blend` and exports to `outputs/mapobjects-integration`.

- Map objects go to `Data/MapEditor/...`. Pile meshes go to `AssetBundles/Resources/StockpileGoodModels/DeepFrontier`: a `GoodVisualizationSpec` mesh is an `AssetRef<Mesh>`, so it ships in the asset bundle, not in Data.
- Use only native materials registered for the editor (vanilla `MaterialCollection.Common` plus `DeepFrontierMapResources`). Give every face a UV island inside its atlas tile (`TILES`). Pile meshes use only `BeaverCarryingModels`, sit untransformed at the origin and hang one level below it, like vanilla `1ScrapMetal`.
- Promote with `pwsh tools/promote_map_objects.ps1`. The blueprint bindings and colliders come from `tools/map_object_content.mjs` during canonical generation.
- Checks:
  - `zfight_audit.py --models <Id>,...`;
  - `audit_hidden_geometry.py --terrain-z 0`;
  - `validate_mapobjects_exports.py`;
  - `validate_triangle_budget.py` (`mapobject` and `pilegood` rows).
- Review renders use `render_map_object_views.py --spec ... --close` with `compose_map_objects_sheet.py`. The native textures they preview are cached by `export_map_object_references.py`.

## Triangle budget: shell builds (2026-10-22)

Every placeable blueprint's models are built into a preview at load, and the prefab optimizer keeps several copies of each mesh, so triangles and vertices cost memory per building type. `tools/asset-pipeline/validate_triangle_budget.py` measures every exported model (finished, construction stage, native props, vertices, slots) and holds each to the ceiling recorded in `tools/asset-pipeline/triangle-budget.json`. Set a ceiling only after a reviewed reduction (`--record <ids>`). `--measure out.json` writes a measurement without checking. The targets in that file come from the measured vanilla buildings (largest finished model 20,440, HydroponicGarden): grand 40k, workshop 20k, small 8k. They are reported, not enforced.

These scenes are built as shells: the civic family (FisheryWorks, FishHatchery, Restaurant, Hospital), ReinforcedHydroTurbine, MaterialsLaboratory and the Grocery Market (`enclosed_cull.SHELL_MODELS`, `render_grocery_market_study.py`).
- No bevel modifier. The native atlases paint edge highlights, as vanilla meshes do.
- The fastener and container kit is `industrial_budget.py`; the civic `steel_bolt` is one diamond-turned square nut.
- `Geometry.cull_enclosed` (`frontier_architecture.py`, `enclosed_cull.py`) removes, at build, every face whose front lies inside a closed convex primitive of the same part. The coverage is exact, in the face's plane.
- Declared sealed rooms (`Geometry.declare_hidden_volume`: `civic_isometric_geometry.framed_room`, `grid_structure.room`) only propose removals.
- With `cull_small_hidden`, faces smaller than 5x5 cm are also proposed.
- Every proposal is kept unless rays from it towards 80 orbit-camera directions stay blocked with all proposals gone. Removed polygons are recorded in `outputs/triangle-budget/culled/`.
- Moving parts get only the exact cull, which does not depend on rotation.
- Wood UV strips use the uncut face index, so kept faces keep their grain.

Removing the bevel can make faces coplanar that the chamfers used to separate, so run the strict audit (`zfight_audit.py --fail-on-visible`) after regenerating.

`audit_hidden_geometry.py -- --models X [--blend-dir D]` measures the triangles no orbit camera sees, per object and per producing source line. It also re-checks every removed face against the saved scene and fails if one is exposed (`culledFacesExposed`). Run it after any scene save or component rebuild of a shell model. The FishHatchery scene carries migration metadata that generation does not write; after regenerating it, run `carry_hatchery_metadata.py` (checks the native props and rails are unchanged, then refreshes the manifests). For an intentional redesign that changes rooms, decks or rails (the 2026-10-26 compact 7x7 footprint), run `refresh_hatchery_metadata.py -- --scene <new blend> --native-assembly <new native-assembly.json> --output <dir>` instead: it writes that metadata from the same recipes without editing any mesh, then refreshes the manifests. Before/after review: `render_budget_views.py` (matched orthographic cameras, 45 degree pitch, whole building and 4.5-tile closest zoom) and `compose_budget_sheet.py` (before | after | difference sheet with changed-pixel share).

## Selected component authoring (2026-10-21)

Edit independently named assets in the existing saved Blender scene. Do not regenerate a whole building or catalog for a doorway, window, roof section or prop change. Full scene creation is for a new scene or an intentional whole-building redesign; `render_reference_studies.py` now requires an explicit `--models` argument. For reviewing unchanged models, use the saved-scene render scripts.

Restaurant, Hospital, Fishery Works, Grocery Store, Crusher, Kiln, Mixer, Quarry, both pits and Hydro Turbine now have independent portal recipes. Restaurant has `Door.GroundDoor`, `Door.MiddleDoor`, `Door.UpperDoor`, and `Door.RoofTerraceDoor`; Hospital has `Door.GroundDoor`, `Door.WestWardDoor`, `Door.RearWardDoor`, and `Door.RoofTerraceDoor`. Each object name is prefixed by its building name. `building_components.recipes(model)` lists the exact IDs. Hatchery's separate platform migration adds seventeen room, roof, window, deck, lamp, support and doorway components; its promotion status is recorded in `tools/STATUS.md`. Rails, native props and animated machinery already have independent objects. Remaining static architecture still needs explicit component recipes as it is edited; it has not all been split. Do not silently substitute a whole-building generation when a component is not registered.

From the repository root, rebuilding only the upper restaurant door is:

```powershell
.\tools\rebuild_building_components.ps1 -Model Restaurant -Components Door.UpperDoor
```

Pass comma-separated component IDs only when each needs changing. `building_components.py` defines their independently callable source recipes. `Geometry.include_component` records their face ownership, and the normal source builder keeps them as separate Blender mesh objects. `rebuild_components.py` opens the saved scene, replaces just those objects, checks geometry/UV/material/transform/animation fingerprints of every unselected object, then saves. Unknown components or changed unselected objects fail explicitly. It does not invoke a building generator, render, bake textures, regenerate icons, or alter gameplay data.

Legacy scenes need an explicit one-time `-Initialize` migration before their first selected edit. The portal migration identifies only known `building_portal` source faces, verifies canonical placement/topology, and splits them losslessly with stored UVs, materials and bevel weights preserved. It rejects missing/ambiguous ownership. The eleven portal scenes listed above have already been migrated; do not run initialization again. Hatchery uses the dedicated `migrate_hatchery_platform.py` contract, not door-only initialization. Its selected objects own `df_structural_parts` and `df_window_mounts`; `hatchery_manifests.write_manifests` validates native-prop fingerprints and refreshes matching layout, picking, rail and window metadata after a selected edit. New component families need an authored recipe and explicit migration, not mesh repair heuristics.

Preview only a saved asset without regenerating it:

```powershell
$preview = Join-Path (Get-Location).Path 'outputs/Restaurant-UpperDoor.png'
.\tools\asset-pipeline\blender-4.5.3\blender.exe -b --python-exit-code 1 --python tools/asset-pipeline/render_components.py -- --model Restaurant --components Door.UpperDoor --output $preview
```

Use `--context` for a close-up including surrounding saved geometry and `--view front-left|front-right|rear-left|rear-right` for the useful isometric side. Neither preview mode saves scene changes. Then `tools/export_checked_models.ps1 -Models Restaurant` audits and serializes only the selected building through the official exporter. Export still writes a complete Timbermesh because that is the game asset format; it does not regenerate the building's geometry. Installation and native verification remain separate.

Evidence: `outputs/component-single-door-restaurant.log` recorded a single 41-face door rebuild in 4.259 seconds, with 250 unselected objects unchanged. After correcting the grid-door joint, each door has 37 faces; the four-door update preserved all other 247 objects and the 62,857-face architecture. `outputs/component-authoring-contract.log` checks the root source path on one actual door and a small wall without generating a building. The official restaurant export passed strict overlaps and 17,280 exported one-sided coverage probes; see `tools/STATUS.md` for installation status.

Hospital's four-door migration took 9.449 seconds, preserving 259 other objects and 34,470 retained architecture faces. It passed strict overlaps and 17,280 exported coverage probes. Its canonical source and two source Data meshes are updated; native installation/testing is tracked separately in `tools/STATUS.md`. To check the actual exported triangles, use `check_exported_door_culling.py -- --building Hospital --model <absolute timbermesh path> --report <absolute JSON path>` through Blender with `--python-exit-code 1`. The `--building` argument is required; the checker never guesses a layout from a filename. Exports whose doors `static_mesh_merge.py` joined into `StaticMerged` need `--game-blend <absolute path to <Model>-Game.blend>`. That is the scene the exporter saved before the join. The checker finds every door triangle among the merged triangles and fails if any is missing.

The [portal inventory](../outputs/component-inventory/README.md) preserves the pre-migration baseline, including source anchors, orientations, face provenance and native-UV profiles. It is historical evidence, not the current migration count. Materials Laboratory is independently edited and is outside this component migration. Declare each model's actual facade mode and UV profile. Industrial idle-worker points are not door mesh anchors, and the Quarry side portal has an explicitly reflected legacy transform. Numeric face ranges are revision evidence, not permanent ownership IDs.

A sealed doorway is not enough: its infill must also sit behind the native casing. `industrial_door_components.py` owns explicit wall planes and mounts. Mixer, Hydro and all four Quarry portals use a 0.04-deep joint; the original anchors remain separately declared for lossless legacy migration. `test_industrial_door_mounting.py` checks native shape/UV preservation and sampled casing visibility. `check_exported_door_culling.py` checks actual exported triangles and adjacent wall joints. Neither check replaces a saved-context render or the native game check.

Both mineral pits also have an independent `Apron` recipe in `pit_apron_components.py`. Their one-time `migrate_pit_apron.py` split retained all other faces and native UVs; do not repeat it on migrated scenes. Rebuild a pit apron through the same selected-component command with `-Components Apron`. `test_pit_aprons.py` checks physical clearance above native terrain, exact retained joists, bevels and atlas regions. Ground clearance must include the actual native terrain and path surfaces; see [the ground-contact contract](art/z-fighting-checks.md#ground-and-plank-contact-2026-10-21).

Hatchery's grid-aligned rails use `RailAssembly.run_cells`: integer endpoints, grid axis, owning cell and source origin are authored together. The exporter verifies the complete contract and emits that one-cell segment directly. It does not re-split its endpoints from float32 mesh coordinates. This avoids microscopic boundary fragments without rounding, dropping segments or adding an export repair. Existing art-span rails retain their separately authored legacy contract.

## Surface overlap validation (2026-10-20)

Use `tools/check_building_surfaces.ps1` for measured z-fighting candidates and red diagnostic renders, and `tools/export_checked_models.ps1` for a fresh strict check before official Timbermesh export. See [the detection workflow and limits](art/z-fighting-checks.md). The audit does not repair geometry; remaining overlaps must be corrected in their source helpers. Existing exported models are not certified by the addition of this tool.

## Current native style contract (2026-10-20)

The 20 detailed source models now share an explicit 32-slot palette. This supersedes the historical 27/30-slot counts below. Slots 30 and 31 are `WindowsAtlas.IronTeeth` and `BaseWood_Brown.Folktails`; roofs use `RoofPlanks.IronTeeth` and orange infill uses `Plaster_Orange.IronTeeth`. Native atlases are reused, not baked into replacement textures. Windows require explicit outward facade directions and bounded pane UV islands.

Adaptive deck rails use the actual Folktails Double Lodge balcony pieces and original UVs. Both source generation and cell-split export call `housing_railing.py`; keep the original opening-node contracts. Register the Folktails wood material in the Iron Teeth collection. See [the style reference](art/iron-teeth-style.md) and [current review](art/reviews/2026-10-20-native-style/README.md). Twenty older prototype building models still need their full concept-quality replacement; the coverage manifest lists them explicitly. Source/export validation and native gameplay evidence remain separate.

## Visual redesign gate — 2026-10-18

2026-10-19: the crusher rebuild was visually accepted. From this point onward, author every building from **only its isometric concept illustration**. Do not use top-down views or printed tile counts. Use angled 3D renders and detail views for review. Existing top-down files are historical artifacts, not references for future models.

Buildings with walkways must follow [building-walkways.md](building-walkways.md). Reuse `walkway_geometry.RailAssembly` to keep perimeter panels and posts separately addressable. The kiln writes its node manifest beside the study. Author native navigation like the shipped housing examples; the 1×1×1 restriction on DynamicPathModel is a visual-component constraint, not a building navigation restriction. All intended decks/stairs require real walking tests after grid integration.

The original prototype meshes and coloured UI icons were rejected in visual review. Replacements and their native verification are tracked in `tools/STATUS.md`. The user explicitly prioritizes the approved reference images over ALL tile counts, including labels printed on the sheets. Build the references as standalone Blender models first. Match silhouettes, relative masses, machinery, architecture, materials and detail. Only after the models look right should the game footprints be derived and all placement data updated together. Do not stretch or shrink a model to preserve an old blueprint size.

For initial scene creation, the art-only command is `blender.exe --background --factory-startup --python-exit-code 1 --python tools/asset-pipeline/render_reference_studies.py -- --models StoneCrusher --resolution 1600` (choose the exact new scene). Reference studies save editable Blender scenes and angled renders. Use selected component edits for existing scenes as described above. They do not export Timbermesh or install game assets. The second crusher draft's tall frame was rejected; do not copy that shape to other machinery. References are preserved under `docs/art/concepts/` and explained in `docs/art/approved-designs.md`.

For the 2026-10-19 crusher rebuild use `--models StoneCrusher --views front,rear,detail`; its active geometry is `crusher_sheet_geometry.py`, matching the explicitly selected concrete production sheet. For the kiln use `--models CementKiln --views front,front-right,back-left,detail`; its source is `kiln_isometric_geometry.py`. Only Front Left, Front Right and Back Left from `Cement Kiln 3D Reference Sheet.png` guide that model. Keep the roof covering the barrel and omit beavers from both models. The source sheet is saved unchanged in both concept directories.

Render motion from a saved scene with `blender.exe --background src/DeepFrontier/Art/Source/CementKiln-ReferenceStudy.blend --python-exit-code 1 --python tools/asset-pipeline/render_reference_motion.py -- --model CementKiln` (substitute StoneCrusher in both positions for the crusher). The script checks the exact animation node set, sampled movement, loop closure, UVs and material presence. The kiln scene has an eight-second 30 fps loop; the crusher has a two-second loop. Preview sampling is reduced for quick review and does not alter the saved source. Its output verifies Blender motion only.

The user approved the visual language of the official `BerryJam/Buildings/Food/JamStove/JamStoveIcon.png` and `BerryJam/Sprites/Goods/BerryJamIcon.png` examples inspected from the installed game's ModTemplates directory. Use single-colour pale ivory/gold outlines, selected solid fills and transparent negative space for building and goods UI icons. Coloured 3D thumbnails are not the approved icon direction. Validate legibility at the actual UI size; do not use a concept sheet itself as a sprite atlas.

Concept prompts and review images live in `src/DeepFrontier/Art/Concepts/`. They are design references, not exported meshes, collision proofs, or final icons. The root generators remain the source for later approved replacements.

## Existing tooling

Deep Frontier buildings are authored as new Blender geometry and exported to Timbermesh. Native reusable props, including barrels, tanks, water wheels and plants, are included in source previews and referenced from the game's original resources at runtime. Preview copies are excluded from mod payloads. The repository includes pinned portable Blender 4.5.3 and the Timbermesh plugin under `tools/asset-pipeline`.

The remaining prototype catalog uses this command from the repository root:

```powershell
.\tools\asset-pipeline\build_deep_frontier_assets.ps1
```

The command runs these stages:

1. `generate_deep_frontier_assets.py` builds the low-poly scene, collections, UV-ready material slots, icon PNGs, and authored texture source PNGs.
2. `export_deep_frontier_assets.py` calls the official Timbermesh exporter in Blender background mode and writes the `.timbermesh` files into the mod's `Data` tree.
3. `generate_approved_buildings.py` owns the remaining reactor and cryogenic prototypes; the geological map objects moved to `build_map_objects.py` (2026-10-25). Its historical name does not imply visual approval. It no longer writes pit, crusher, kiln, mixer, quarry or civic models. `pit_isometric_geometry.py` owns the detailed sandstone/limestone reference studies; `pit_layouts.py` registers them at 5×5×4 and 6×5×4, without resizing. The older `generate_construction_material_assets.py` also excludes the reviewed industrial models, and its colored construction icons have been retired.
4. `validate_deep_frontier_assets.mjs` checks that every source scene, texture, icon, and model export exists and is non-empty.
5. `validate_deep_frontier_animations.py` decompresses the exported Timbermesh protobufs and checks animation tracks on every finished model. This checks export structure; in-game playback remains a separate acceptance check.
6. `validate_model_bindings.py` checks visual model-name and attachment references against authored Timbermesh node names. It catches retained vanilla crop stages and missing model roots before world creation.

Reviewed models use their individual `Art/Source/*-ReferenceStudy.blend` files and `export_industrial_models.py --models <explicit names>`. The exporter reads authored registration and rail bindings; it does not resize the artwork. Civic exports first go to `outputs/civic-integration/Data` for promotion together with their matching blueprint changes. The generic exporter no longer writes the hatchery prototype over its reviewed waterfront model. Preserve model ownership when adding another replacement.

`tools/create_restaurant_icons.mjs` owns the civic/aquaculture SVG icons. `tools/create_construction_icons.mjs` owns seven construction building icons, five mineral goods and four source icons. All use the approved ivory outline language. The construction review shows 128px and 32px versions in `docs/art/reviews/2026-10-20-mixer/construction-ivory-icons.png`. Run the matching icon generator after editing its SVG sources.

For authored Unity materials, run `tools/asset-pipeline/prepare_deep_frontier_materials.py`, stage the source with `tools/stage_deep_frontier.ps1`, and use **Deep Frontier > Create Materials** in Unity. This authors the three material assets; the official **Timberborn > Show Mod Builder** packages them with the rest of the mod. Enable Code and Windows AssetBundle and set compatibility to `1.1`. The live meshes currently use known Iron Teeth material names; custom material lookup still needs in-game verification.

The scene is intentionally collection-driven. Building blueprints reference the collection exports by these resource paths:

- `Buildings/Metal/DeepDrill/DeepDrill.IronTeeth.Model`
- `Buildings/Metal/DeepMine/DeepMine.IronTeeth.Model`
- `Buildings/Metal/DeepProcessor/DeepProcessor.IronTeeth.Model`
- `MapEditor/Objects/DeepOreVein/DeepOreVein.Model`

The expansion layer uses the same collection pattern for its 22 authored food, wellbeing, school, chemical, water, uranium, waste, cryogenic, rocket, mission, reactor, and vault buildings. Finished machine collections carry the animation clip; construction-stage collections stay static so the build view remains readable.

`validate_model_bindings.py` checks exported node references, worker-hider/slot-manager pairing, the native construction threshold count, and material availability by context. Map objects require Common materials even when the eventual game faction is Iron Teeth. `MaterialCollection.DeepFrontierMapResources` explicitly registers the four materials used by geological markers for the editor. A single unfinished child uses an empty construction-threshold array; each additional stage requires one threshold.

Construction and underground variants are separate collections. `Art/Textures/` contains the authored texture source. The official Mod Builder compiles and installs the package; the custom file-copy installer and custom bundle packager have been removed.

For a fast iteration loop, use `-SkipGeneration` when only the exporter changed, `-SkipExport` when only source files need checking, or `-SkipValidation` when debugging Blender output. The exported files are generated artifacts; the `.blend`, generator script, texture source, and blueprint references are the editable source of truth.

## Shared workshop details and current crusher revision

### Native industrial material mapping

The crusher, kiln and quarry now reference native Iron Teeth wood, planks and painted metal in palette slots 0, 1 and 3. These materials address a shared atlas: repeating world-coordinate UVs can sample unrelated signs, windows and emission. `Geometry.build` authors padded face islands on selected board strips, with grain following the face's longest edge. This occurs while creating the source mesh; no exported UV wrapping/clamping or runtime material replacement is used. `validate_industrial_exports.py` checks every exported vertex indexed by these native materials, including bevel geometry. Material-name availability alone cannot validate appearance.

`inspect_native_materials.py` reads the official `TimberbornExampleModels.blend` and records its material nodes, UV ranges and packed texture references under `outputs/native-material-inspection/`. These example textures are authoring evidence; the installed industrial meshes resolve the game's Iron Teeth materials directly. The Blender palette preview is not an exact runtime shader preview. Save and inspect actual game screenshots before accepting a material change.

`industrial_geometry.py` supplies unchanged joint plates, bolts, roof panels and access stairs to both crusher and kiln; it removes the previous dependency of shared rail geometry on the crusher module. `crusher_workshop_details.py` adds recessed controls, gate screw, oilers, bench/supplies and localized wear. Both industrial palettes now use the kiln's worn timber/teal/iron treatment. The crusher retains open rollers, its flywheel clearance slot and short roof; new side/rear walks and stairs supply visual clearance. These are authored Blender dimensions, not a gameplay footprint.

The accepted prior crusher's four angled 1800px renders, source metadata, rail manifest and motion check are saved in `docs/art/reviews/2026-10-19-crusher-workshop/`. Both buildings now emit separate rail manifests. `check_kiln_joinery_refactor.py`, run against the then-approved kiln scene, verified 100 matching nodes and zero vertex differences after the shared-helper extraction. This historical comparison precedes the later facade and height changes.

`BuildingWalkway.cs` is compiled with the official builder; it is not yet attached to these art studies through blueprints. Do not describe the new walk decks as game-tested, or use the old installed meshes as screenshots of this revision. Final tile alignment, collision, native navigation, material export and a restarted game test still follow.

## Closed facades and quarry process studies — 2026-10-19

Use opaque amber panes and dark recessed arched entrances, with no modeled visible interiors. `reference_materials.py` supplies this window contract at its source (alpha 1, transmission 0). `industrial_facades.py` shares arched portals, panes, gauges and the restrained cyan instrument material. `factory_facade_details.py` adds enclosed lower rooms and exterior services to the accepted crusher and kiln. Keep the kiln roof and existing machinery silhouettes. These additions are artwork, with no heat or maintenance system.

`quarry_isometric_geometry.py` authors the headframe and access structure; `quarry_process_details.py` supplies enclosed workshops and the animated bucket → receiver → gravity chute → slat belt → vibrating screen → bin sequence. Internal belts and moving rocks are visual geometry, not dependency entities or additional inventory producers. The source access and process manifests use artwork coordinates. Native entrance transforms, occupied grid cells, ladder edges and adaptive-rail ports must be authored during export integration.

Use `--save-only` for source-scene generation without stills. Use `render_reference_motion.py -- --model <Name> --check-only` to inspect the saved scene before rendering a preview. The quarry checks all 481 source frames, cable attachments, ladder hatch clearance, gallery floors/headroom and the stair-to-ladder deck route. `factory_clearance.py` checks the crusher/kiln service circuits against saved static mesh triangles. These are mesh checks, not native pathfinding tests. `inspect_reference_video.py` decodes final MP4 previews, verifies dimensions/frame count/fps, and saves actual decoded frames for visual inspection.

Render commands must include `--python-exit-code 1`: Blender's default exit status can be zero after a Python exception. Require the successful report and output files as well. Frame checks iterate frames once across all animated nodes; a node-by-node full-timeline traversal is unnecessarily expensive. The explicit local render target is the RTX 2060 through OptiX; missing hardware fails visibly. No device substitution is introduced.

The quarry adds a `process` close-up; crusher/kiln add a lower-angle `facade` close-up so doors and windows under the decks can be reviewed. Neither is a top view. The broad review images retain the selected isometric-reference policy. Save final reviewed renders and reports in the dated documentation folders; keep old review sets unchanged.

## Functional height layers

Read [height-layout.md](art/height-layout.md) before authoring structural floors. `industrial_levels.py` declares the crusher and kiln decks at layer 2 and quarry decks at 1, 3, 5 and 7. One Blender Z unit equals one native height layer. Supports and stairs are authored around those constants; `MountedMachinery` places intact detailed assemblies and their animation pivots on the declared deck. It never infers dimensions from bounds or rounds them during export.

`access_stair` requires explicit integer bottom/top layers and one horizontal cell of run per layer of rise. Decorative treads, pitched roofs, frames and fittings retain fractional dimensions. A decorative roof is not automatically a stackable surface. The renderer writes a height manifest and rejects geometry above the declared vertical envelope; motion validation also checks rail floor levels against the manifest. These checks do not replace horizontal grid alignment or native route integration.

Current review destinations: [quarry](art/reviews/2026-10-19-quarry/README.md) and [crusher/kiln facade and height pass](art/reviews/2026-10-19-factory-detail-pass/README.md). Saved source scenes remain in `src/DeepFrontier/Art/Source/`. Earlier dated review folders retain the accepted prior appearances.

## Four civic studies from individual sheets

`civic_isometric_geometry.py` replaces the old `reference_civic` building functions in `render_reference_studies.py`. References are exactly `Fishery.png`, `Resturaunt.png`, `Grocery Store.png` and `Hospital.png`; use their isometric illustrations only. Closed rooms, explicit facade directions, modeled entrance cutouts, layered roofs, service details and separate rails are authored at source. Civic models now have an explicit 30-slot palette and `civic-native` UV profile; the industrial 27-slot contract is unchanged. Native export/grid binding for these four studies is not implemented yet.

Render with `--models Hospital,Restaurant,GroceryStore,FisheryWorks --views front,front-right,rear --resolution 1600`. Include Blender's `--python-exit-code 1`. Source generation now invokes `civic_validation.py`: gallery-floor and body/headroom rays are checked against the mesh, along with native atlas bounds and exact material-slot count. `CIVIC_ACCESS` holds explicit source routes and future stair bays. A source gallery pass does not prove grid-center alignment or native pathfinding.

`render_reference_motion.py` and `inspect_reference_video.py` accept the four civic identifiers. Exact node identity, sampled movement, loop closure, rail nodes and whole-layer floors are checked before motion previews. Review files live in [the civic review directory](art/reviews/2026-10-19-civic/README.md). Do not run the older all-building generators over these source scenes or advertise their old installed meshes as this revision.

After the four still/motion jobs and video decoding finish, run `tools/asset-pipeline/archive_civic_review.py` with the bundled Python. It checks doorway layers and motion/video agreement, copies the explicit current review set, verifies copy hashes and records source-scene/concept hashes. The 2026-10-19 archive contains 75 artifacts. It excludes obsolete standalone geometry reports because current motion reports already include the geometry/clearance evidence. This archive step does not build or install game content.

### Exact native props, plant silhouettes and material previews

`export_native_civic_inspection.py`, `read_native_civic_models.py` and `export_native_civic_materials.py` inspect exact installed resource IDs and decode the official BinaryData/Timbermesh payload. Cache local review inputs in `outputs/native-civic-assets`; do not ship those original resources. `native_building_assets.py` records original resource references plus authored placement, then builds Blender preview instances.

The inverse import reverses native triangle winding, converts Unity coordinates once, preserves original normals/UV channels and imports original vertex colors. Color properties are decoded from sRGB for Blender sockets. Materials with metallic maps use the original red channel and alpha smoothness with its scale. Packed Unity normals use R times A for X and G for Y. The civic base-metal slot deliberately maps faces to the plain upper-left atlas plate. Wood grain density remains deliberately chunky.

Plants require actual leaf/stem meshes with alpha-cut edges and vertex colors. Green rock clusters are rejected. Current planters use native dandelions, sunflowers, coffee/blueberry foliage and Iron Teeth potted shrubs. Dandelion flower heads occupy UV channel 3 (`uv2`), while their UV0 sits on transparent texels; the explicit flowering preview combines the original detail layer with the base leaves. Matching that maturity state in the native shader remains civic integration work. Cycles needs 32 transparent bounces for overlapping leaf cards: its default eight produced black patches. This changes preview ray tracing, not the mesh or game shader. `render_native_plant_review.py` provides the original-plant comparison before building-wide review.

Native props are excluded from custom industrial mesh export. Original animations and materials remain native at runtime. Plant shader wind, final game appearance, multi-level doors, terrace construction and restaurant visits require their own runtime evidence; see [civic integration](civic-building-integration.md).
