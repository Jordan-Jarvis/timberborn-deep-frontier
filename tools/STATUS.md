# Current development status



Updated 2026-10-25. Target: Timberborn 1.1.2.8, Iron Teeth; Unity 6000.5.11f1.

## Compaction: Cryogenic Liquefaction Plant 12x11x16 -> 8x6x9 (Claude Code session, 2026-10-30, built by an agent; scene, export and blueprint promoted; validated in mirror `lgi` on HEAD + this change; not built or run in game)

- **Art** (`lategame_CryogenicLiquefactionPlant.py`, saved scene unpacked): the cold box tower (tiles 5-8 x 2-5, cap at layer 6.5) in insulated concrete courses with a caged ladder up its back, vent stack with steam, vent rotor and beacon on its cap; the banded distillation column (to layer 7.5) in front of it, tied to it, its transfer line over onto the cap; the two Horton spheres on steel legs behind the compressor house; the two-storey compressor house (concrete ground storey with the door, steel-framed forged upper storey, one layer each) whose flat roof carries one fin bank with three cooler fans; the open engine bed on its west flank with both flywheels and both compressor pistons under a rocker frame. Removed: the cooler deck on six piers, the pipe rack on its bents, the tanker loading bay with its gantry, wagon and swinging loading arm (its `LoadingArm` animation goes with it), the product tank, the cold box's two platforms, the sphere-top walkway and the sawtooth roof. The other 9 animated parts keep their names.
- **Checks on the art:** triangles 18,702 -> 7,792 (ceiling re-recorded); strict z-fight audit 0 visible at frames 1/31/61/91; grid audit: one reported edge (the cold box plinth stands 0.1 inside its tile line so its foot clears the house's), no floor misses, nothing floating.
- **Data:** footprint inside the old one with the same origin; the door stays on tile column 3 and moved from the house front at y 1 to the front edge: Entrance (3,0,0) -> (3,-1,0), the cell in front of the old door, which is also where the map sites' door approach already was. Solid cells 533 -> 187; steam at the cold-box vent (5.77, 2.72, 7.92). Still a sited building (8 = `largeFootprint`). Cost held by `lategame_cost_basis.json`; power, crew and recipes unchanged.
- **Old saves:** a placed plant keeps its origin and frees the tiles it no longer uses; its entrance moves one tile forward onto the tile in front of the old door (flipped: same column). Shafts and pipes on removed walls disconnect.
- **Review:** `outputs/compaction/CryogenicLiquefactionPlant-before-after.png`.
- **Checks (mirror):** canonical generation on HEAD + this change reaches a fixed point; `validate_all -Only` 23 checks: all pass except `map-setup-terrain` on `smallMap.maxArea` alone (re-derived after the pass).
- **In game:** not seen yet.

## Compaction: Archive Excavation 10x9x11 -> 7x6x6, cache survey radius 4 -> 7 (Claude Code session, 2026-10-30, built by an agent; scenes, exports and blueprints promoted; validated in mirror `minesdrill` on HEAD + this change; not built or run in game)

- **Archive Excavation** (`lategame_ArchiveExcavation.py`): a one-storey flat-roofed archive hall with the door (same door, doorstep (2,1) and entrance (2,0)), a 4-layer flat-roofed archive stack tower with its stove flue, and a flat-roofed catalogue wing. All roofs have `parapet_ring` (no lid), so they stay usable decks. The pit (tiles 4..7 x 1..6) holds the half-buried cogwheel, the broken column and the string grid under a 5-layer tripod derrick (sheave, bucket, rope, beacon), with the winch drum and flywheel on the thick back retaining wall; the two sieves and the spoil belt are under a flat shed roof at the front right. Removed: the gable roofs, the reading lantern, the catalogue lean-to, the 8-layer tower roof, the sorting table and the tall derrick's extra height. All 9 animated parts keep their names. Triangles 15,602 -> 8,166. Strict z-fight audit 0 visible. The pit's inner retaining-wall faces are the only grid-audit edge misses.
- **Data:** footprint inside the old one with the same origin, door and entrance. Connection faces, roof decks, one smoke/smog source (the stove flue) and `lategame_freed_cells.json` (7x6x6, keeping its two open tiles in front of the hall; the door lamps went so they stay open) regenerated. Cost held by `lategame_cost_basis.json`; power, crew and recipes unchanged.
- **Cache survey radius 4 -> 7** (`narrative_content.mjs` `CACHE.spec.SurveyRadius`; coordinator's decision): with radius 4 the smaller excavation left Human Record Caches out of range on 16 built-in maps (for example Canyon 0/5, Beaverome 2/5). The new footprint lies inside the old one, trimmed by at most 3 tiles per axis, so radius 7 keeps every cache the old excavation reached in range, on the maps and in existing saves. The Archive description now takes the radius from the spec; `docs/maps.md` and `docs/story.md` follow. With it, every map's cache coverage passes again.
- **Maps:** the excavation is now under `largeFootprint` (8), so `prepare_deep_frontier_map.py` adds it to `FLAT_SITE_TEMPLATES` (caches are surveyed from its sites). `map-setup-terrain` otherwise fails only on `smallMap.maxArea` and on the Electrolysis Plant's door approach (another building's compaction).
- **Old saves:** a placed excavation keeps position and entrance and frees the tiles it no longer uses at any rotation; a flipped one's entrance moves 3 tiles (local x 7 -> 4). Caches near it stay surveyable (radius 7). Shafts and pipes on removed walls disconnect.
- **Review:** `outputs/compaction/ArchiveExcavation-before-after.png`, `ArchiveExcavation-compaction-close.png`, `ArchiveExcavation-footprint-height.png`.
- **Checks (mirror):** canonical generation to a fixed point; 18 of 19 building checks pass, with `map-setup-terrain` failing as above.
- **In game:** not seen yet.

## Compaction: Fish Hatchery, Fishery Works, Materials Laboratory; no-clutter fixes on Restaurant, Hospital and Grocery (Claude Code session, 2026-10-30, civic agent; generated and validated in mirror `civic`, promoted into Data; not built or run in game)

- **Fish Hatchery 7x7x5 -> 7x7x3** (already 7x7 since 2026-10-26): the headhouse is one layer (native z 1..2) under a flat cast roof with timber decking; the pump canopy is one layer under a flat roof, its filter drum lower on a shorter cast base. Gabled roofs, roof bearing and roof vent are gone (components `Headhouse.RoofBearing` and `Headhouse.RoofVent` removed from `hatchery_components.BUILDERS`). Shorter sign (`hanging_board_storey`). Footprint, origin, BaseZ, door, pens, decks, rails and pipe port unchanged. Metadata written with `refresh_hatchery_metadata.py` (redesign path). Triangles 18,950 -> 7,632.
- **Fishery Works 11x8x7 -> 11x8x4**: one layer per storey (processing floor 0-1; galleries, upper-hall door and warehouse roof terrace at layer 1, were 2). The long gabled roof stays as the works' silhouette, lower; the entrance gable, crane, wheel header, cascade and nets follow. The lean-to awnings under the galleries, the wall service ducts and the roof cowl are gone. The two rear water tanks (the Timber Pipes inlet) stand under the rear gallery now (no-clutter rule): `aquaculture_pipe_ports.json` (4,7,0) -> (4,6,0), still facing Up (+Y). Occupancy regions in `fishery_building_content.mjs`; doors at layers 0/1/1 (`building_components.DOOR_LAYOUTS`).
- **Materials Laboratory 10x8x9 -> 10x8x5**: one-layer cast bases, terrace and records-office door at layer 1, the records office under a flat cast roof (gable roof gone), the sawtooth sheds lower (their silhouette kept), the instrument tower and press scaled to the lower plinths (press stroke .22 -> .14). Power-line points (.18,6.65,.84) and (8.205,3.5,2.06). Occupancy regions in `research_building_content.mjs`.
- **No-clutter re-check of the committed three** (user rule, BRIEF.md): the Restaurant's sign gantry stands on the front parapet's edge strip and its two roof stacks became one on the roof stairhead's cap, so every main-roof cell outside the stairhead is buildable (reservations 3 -> 1); the Hospital's steam flue rises through the transverse roof's rear slope instead of taking a roof-garden cell; the Grocery's overflow crate, basket and sack on the open cell in front of the stall wing are gone and the basket sign hangs inside the wing.
- **Shared code (append-only):** `civic_isometric_geometry`: `framed_room(wall_style='storey')`, `terrace_access_house(storey=True)`, `balcony_storey`, `component_doorway_storey`, `hanging_board_storey`; defaults unchanged.
- **Saves:** Hatchery, Fishery and Laboratory keep footprint, origin and entrance; paths, stairs and platforms on their old decks and terraces float and need re-placing; a pipe to the Fishery's tank inlet must reconnect one tile in.
- **Checks:** strict z-fight 0 visible, hidden-geometry 0 culled faces exposed, sources-civic (FishHatchery, FisheryWorks, Hospital, Restaurant), restaurant shell 55,834 probes 0 uncovered, triangle budget; mirror canonical generation and `validate_all -SkipBlender` (see the commit).
- **Open:** in-game checks; the C# acceptance fixtures (Fishery, Aquaculture, Hospital, Grocery, Restaurant) still use pre-compaction coordinates.

## Compaction: Electrolysis Plant 12x9x12 -> 8x5x6 (Claude Code session, 2026-10-30, built by an agent; scene, export and blueprint promoted; validated in mirror `lgi` on HEAD + this change; not built or run in game)

- **Art** (`lategame_ElectrolysisPlant.py`, saved scene unpacked): the hydrogen holder (two lifts) and the oxygen holder (one bell) in concrete water tanks, each in a round guide frame of columns on piers with two girt rings; the two-storey cell hall front-left (concrete ground storey with the door, steel-framed orange upper storey, one layer each) under a flat roof with a flat-capped glazed lantern and the hydrogen vents; two transformers (radiator fans facing the back) on a pad behind the hall, their bus bars running into a bushing panel on its back wall; the one-tile water intake channel with its pump and flywheel between the pad and the holders, open to the back edge. Removed: the bus-bar gantry's portal frames, the open cell gallery with its cells, the scrubber drums, the guide frames' diagonal bracing and third girt, and the monitor roof's pitched slopes. The 7 animated parts keep their names; slides 1.2/2.4/1.6 -> 0.5/1.0/0.8.
- **Checks on the art:** triangles 18,978 -> 10,454 (ceiling re-recorded); strict z-fight audit 0 visible at frames 1/31/61/91; grid audit: no edge misses (the round holder tanks are reported as round masses), the lantern cap is not a floor, transformer fins and radiators are wall-mounted.
- **Data:** footprint inside the old one with the same origin; the door moved from the yard to the front edge: Entrance (6,3,0) -> (1,-1,0), `LocalAccess` (6.5, 0, 4.15) -> (1.5, 0, 0). Solid cells 559 -> 110; shaft faces 127 -> 58, pipe ports 30 -> 13; platformable roof cells 1 -> 8 (the hall roof around the lantern). Still a sited building (8 = `largeFootprint`); its map sites stay valid for the smaller footprint. Cost held by `lategame_cost_basis.json`; power, 5 workers and recipes unchanged.
- **Old saves:** a placed plant keeps its origin and frees the tiles it no longer uses, but its entrance moves from local (6,3) inside the old yard to (1,-1) in front of the new hall (flipped: (5,3) -> (6,-1)); reconnect its path. Shafts and pipes on removed walls disconnect.
- **Review:** `outputs/compaction/ElectrolysisPlant-before-after.png`.
- **Checks (mirror):** canonical generation on HEAD + this change reaches a fixed point; `validate_all -Only` 23 checks: all pass except `map-setup-terrain` on `smallMap.maxArea` (re-derived after the pass).
- **In game:** not seen yet.

## Compaction: Steel Mill 12x10x15 -> 8x6x8 (Claude Code session, 2026-10-30, built by an agent; scenes, exports and blueprints promoted; validated in mirror `minesdrill` on HEAD + this change; not built or run in game)

- **Steel Mill** (`lategame_SteelMill.py`): a steel-framed control pulpit with the door (flat roof, beacon on the parapet corner); behind it the melt shop, now flat-roofed (ring parapet), with the electrode penthouse (electrodes PISTON_Z) and a fume duct to a 7.6-high flue in the teeming bay's corner. The rolling line (reheat furnace, three stands with six rolls, hot bar) sits under a flat open canopy at layer 2. The teeming ladle, pour stream, tap glow and mould car are under a flat-roofed bay at layer 3. Removed: the open crane bay (runway columns, braces, girders) and the travelling `SteelMill.LadleCrane` (13 animated parts, was 14), the bunkers, the cooling bed, the melt shop's gable roof and monitor lantern, the rolling line's gable canopy and the reheat stovepipe (it would have blocked the canopy roof). Triangles 17,760 -> 9,152. Strict z-fight audit 0 visible at frames 1/31/61/91/111. Grid audit: 0 floor misses; the 6 edge misses are machinery on the yard slab (reheat furnace, ladle stands).
- **Data:** footprint inside the old one with the same origin and entrance. Connection faces, roof decks, one smoke/smog source (the flue) and `lategame_freed_cells.json` (8x6x8, no inside cells) regenerated. Cost held by `lategame_cost_basis.json`; power, crew and recipes unchanged.
- **Maps:** the Steel Mill is still 8 wide, so it stays a flat-site building by size; `map-setup-terrain` fails only on `smallMap.maxArea` (re-derived after the pass).
- **Old saves:** a placed mill keeps position and entrance and frees the tiles it no longer uses at any rotation; a flipped one's entrance moves 4 tiles (local x 10 -> 6). Shafts and pipes on removed walls disconnect.
- **Review:** `outputs/compaction/SteelMill-before-after.png`, `SteelMill-compaction-close.png`, `SteelMill-footprint-height.png`.
- **Checks (mirror):** canonical generation to a fixed point; the building checks pass except `map-setup-terrain` (maxArea) and the Archive Excavation's pending cache coverage (not in this commit).
- **In game:** not seen yet.

## Compaction: Precision Machine Works 11x9x14 -> 9x5x7 (Claude Code session, 2026-10-30, built by an agent; scene, export and blueprint promoted; validated in mirror `lgi` on HEAD + this change; not built or run in game)

- **Art** (`lategame_PrecisionMachineWorks.py`, saved scene unpacked): the machine shop on tiles 0-6 x 0-5, a concrete ground storey with the open belt bay (line shaft, belts and three lathes under the coping) and a steel-framed forged upper storey, one layer each, under the north-light sawtooth (three teal plank teeth with glazed north faces; kept as the building's defining silhouette, the only sawtooth among the late-game works); the two-storey gate office (tiles 6-9 x 0-2) with the door and a flat roof whose front row is open, the riveted air receiver on concrete saddles on its back row; the crane yard behind it: concrete paving, the travelling crane on a solid runway wall (tile column 8) and a bracket beam on the shop wall, the roll lathe under it, the steam hammer on its pad and the six-layer square brick chimney with iron bands on its firebox in the corner. Removed: the yard's six steel columns and knee braces, the receiver's braced frame, the forge lean-to and the 13-layer chimney. The 7 animated parts keep their names; the crane travel is 1.0 (was 3.9).
- **Checks on the art:** triangles 11,206 -> 7,504 (ceiling re-recorded); strict z-fight audit 0 visible at frames 1/31/61/91; grid audit: one reported edge (the runway wall starts 0.15 behind the office to clear its roof curb), no floor misses, nothing floating.
- **Data:** footprint inside the old one, same origin, door and Entrance (8,-1,0); door face on the tile edge (`LocalAccess` z 0.15 -> 0). Solid cells 297 -> 131; shaft faces 195 -> 102, pipe ports 91 -> 56; smoke at the new chimney mouth (8.5, 4.5, 6.64); platformable roof cells 36 -> 3 (the office's front row; the sawtooth is pitched). `lategame_freed_cells.json`: the three 2026-10-22 yard cells are gone (two now outside the 9x5 footprint, one under the runway wall); footprintAfter 9x5x7. Still a sited building (9 >= `largeFootprint`); its map sites stay valid for the smaller footprint. Cost held by `lategame_cost_basis.json`; power, 6 workers and recipes unchanged.
- **Old saves:** a placed works keeps its origin and entrance and frees the tiles it no longer uses. A flipped one's entrance moves 2 tiles (local x 2 -> 0). Shafts and pipes on removed walls disconnect.
- **Review:** `outputs/compaction/PrecisionMachineWorks-before-after.png`.
- **Checks (mirror):** canonical generation on HEAD + this change reaches a fixed point (a second run leaves Data and `roof_decks.json` unchanged); `validate_all -Only` 23 checks as for the Chemical Works plus `cryogenic_content`: all pass except `map-setup-terrain` on `smallMap.maxArea` (re-derived after the pass).
- **In game:** not seen yet.

## Compaction follow-up: no clutter on buildable space, Deep Drill and Deep Mine (Claude Code session, 2026-10-30, built by an agent; scenes, exports and blueprints promoted; validated in mirror `minesdrill` on HEAD + this change; not built or run in game)

- **User rule:** "we don't want clutter everywhere taking buildable space"; props must not claim otherwise-open footprint or roof cells.
- **Deep Drill (7x6x8):** the drill-pipe joints on the pump-house roof and the two mud tanks (with their ladder, gauge and pipes) are gone. The engine room now runs to y 6 (tiles 3..7 x 0..6), so the two stacks stand on its deck and the radiator fan sits on its right wall (SPIN_X again). The back-left tiles (0..2, 5) are open ground. Triangles 10,588 -> 9,532 (ceiling re-recorded). Strict z-fight audit 0 visible at frames 1/31/61/95/121.
- **Deep Mine (7x6x7):** the front ore track and ore tub (`OreTub` removed, 8 animated parts again), the bin's front chute, the bath-house hot-water tank and the winding-engine exhaust stack are gone. The front strip (tiles 3..6 x 0) is open ground, and one smoke source remains (the bath-house chimney). Triangles 9,436 -> 8,139 (ceiling re-recorded). Strict z-fight audit 0 visible at frames 1/26/51/61/91/111.
- **Data:** roof decks, connection faces and smoke/smog regenerated for both; cost, power, crew, entrance and the mine's vein core unchanged.
- **Checks (mirror):** canonical generation to a fixed point; the building checks pass except `map-setup-terrain` (`smallMap.maxArea`, re-derived after the pass).

## Compaction: Chemical Works 10x9x14 -> 5x5x8 (Claude Code session, 2026-10-30, built by an agent; scene, export and blueprint promoted; validated in mirror `lgi` on HEAD + this change; not built or run in game)

- **Art** (`lategame_ChemicalWorks.py`, new own helper `compact_industry_parts.py`: one-layer storey blocks with a flat roof whose top is a whole layer and a curb under 0.15; not named `lategame_*_parts.py`, so other studies' source hashes stay put; saved scene unpacked): a solid two-storey reactor hall (concrete ground storey with the door, steel-framed forged upper storey, one layer each, floor band on every layer) under a flat concrete roof that carries the fin-fan cooler, the three turbine ventilators on the cooler housing and a short flare stack with its flame at the back corner; three agitated reactors in a row on a concrete apron along the hall's right wall; the 7-layer riveted column (insulated middle, one ring platform on layer 5, ladder) behind them, its vapour line dropping to the cooler. Removed: the lattice flare tower and knock-out drum, the pipe-rack catwalk on its bents, the cooler's piers, the spherical product tank, two of the three column platforms and both gabled roofs. Same textures, slots and UV authoring; the 9 animated parts keep their names.
- **Checks on the art:** triangles 19,004 -> 8,768 (ceiling re-recorded); strict z-fight audit 0 visible at frames 1/31/61/91; grid audit 0 edge and floor misses (the instrument board is wall-mounted).
- **Data:** footprint inside the old one, same origin, door and Entrance (1,-1,0); door face on the tile edge (`LocalAccess` z 0.15 -> 0). Solid cells 416 -> 89; shaft faces 137 -> 52, pipe ports 60 -> 21; one smoke emitter (the flare); 6 platformable roof cells (the front two rows of the hall roof). Cost held by `lategame_cost_basis.json`; power, 8 workers and recipes unchanged.
- **Maps:** 5x5 is under `largeFootprint` (8), so the Chemical Works no longer needs a site: its site lines (17 variants) and unmet items (Beaverome, Cliffside, Diorama) are removed from `tools/map_variants`, with the matching `docs/maps.md` rows and the generated "No room for" lines. `map-setup-terrain` fails only on `smallMap.maxArea` (re-derived by the coordinator after the pass).
- **Old saves:** a placed Chemical Works keeps its origin and entrance and frees the tiles it no longer uses. A flipped one's entrance moves 5 tiles (local x 8 -> 3). Shafts and pipes on removed walls disconnect.
- **Review:** `outputs/compaction/ChemicalWorks-before-after.png`.
- **Checks (mirror):** canonical generation; `validate_all -Only` 22 checks (exports-lategame/connection/preview_budget, model-bindings, entrances, connection faces, roof decks, smog, slice content, freed cells, sounds, status icons, power rule, automation, tool groups, workforce risks, narrative, map setup, progression, building assets): 21 pass, `map-setup-terrain` on maxArea only.
- **In game:** not seen yet.

## Compaction follow-up: no clutter on buildable space, kiln, mixer and quarries (Claude Code session, 2026-10-30, built by an agent; scenes, exports and blueprints promoted; validated in mirror `ind-head` and the real repo; not built or run in game)

- **User rule (BRIEF.md "No clutter on buildable space"):** "we can have details, but clutter that leaves most of a tile open but makes it un buildable is not great."
- **Cement Kiln:** the log stack, coal bin and cement output bin (front row) and the porch posts are gone; the porch canopy rests on the porch's side walls (DOOR_X +-0.62). The front row's ground cells (0,0), (1,0), (2,0) and (4,0) are open (`industrial_occupancy.mjs`; `IndustrialAcceptance` lists them as freed cells); the firebox crown's cell above stays open, though the roof-deck plan excludes it for the smoke emitter above. The door's shoulder strips (part of its frame, 0.11 wide) still reach into cells 2 and 4.
- **Concrete Mixer:** the wet tray is now a trough on one concrete base under the drive pedestal (solid mass), not a loose bin.
- **Quarries:** the native water tank stands inside the winding house (the ground cell it took is plinth now: the plinth's front strip runs the full width either side of the cabin); the front-strip supply bins, spoil heap and the plinth-top supply pipe are gone; the stone bin is a shallow tray on the plinth under the screen. The open plinth top and the winding-house roof are now platformable roof decks (`roof_decks.json`).
- **Not changed:** the pits keep their yard row: the apron floor, the sandstone pit's sorting grate and the hoist basket are their working yard (the door's approach floor is in that row, so the row cannot be trimmed without moving the entrance). The crusher's porch and chute-fed output bin are its door and process.
- **Checks:** strict z-fight 0 visible on all three; kiln and quarry motion checks; `exports-industrial`, `sources-mixer`, `model-bindings`, `building_entrances`, `construction_materials`, `freed_cells`, `status_icon_anchors`, `audit-building-assets` pass (`roof_decks` and `smog_content` fail only on other agents' buildings); recipes, costs and workers unchanged; scripts compile.

## Compaction: Deep Ore Processor 11x10x14 -> 7x6x8 (Claude Code session, 2026-10-30, built by an agent; scene, export and blueprint promoted; validated in mirror `minesdrill` on HEAD + this change; not built or run in game)

- **Art** (`lategame_DeepProcessor.py`, saved scene unpacked): a riveted blast furnace on a one-layer concrete hearth podium (tiles 3..7 x 2..5) with banded bosh and stack, bustle main and tuyeres, a top platform at layer 6 on shell brackets, the rotating charging distributor, uptakes into a downcomer to the dust catcher and a bleeder. A plated vertical skip hoist on tile (6, 5) charges it over a short chute. Two domed hot-blast stoves with their chimney and the hot-blast main stand behind the flat-roofed brick blower house (the door, a wall blower fan). In front, a flat-roofed open casting bay holds the runner, the tilting ladle, the pour stream and the pig moulds. Removed: the column-and-brace frame round the furnace, the 60-degree lattice skip bridge and its bents, the third stove and its catwalk, the gabled casting bay and blower house, and the bunker strip. No clutter on buildable space: the flat roofs are clear and the ground beside the hoist is open.
- **Animation:** the same 5 parts (`ChargingDistributor`, `SkipCar` now rising in the hoist, `Ladle`, `PourStream`, `GableFan` now on the blower house's left wall, SPIN_X).
- **Checks on the art:** triangles 15,098 -> 6,826 (ceiling re-recorded); strict z-fight audit 0 visible at frames 1/31/51/61/91/111; grid audit 0 edge and floor misses.
- **Data:** footprint inside the old one with the same origin, door tile and Entrance (1,-1,0); door face on the tile edge (`LocalAccess` z 0.18 -> 0). Shaft transputs 107 -> 67, pipe ports 41 -> 26 (still water for its recipes); one smoke/smog source at the stove chimney (1.5, 5.62). Roof decks: the blower-house and casting-bay roofs and the podium edges are platformable. Cost held by `lategame_cost_basis.json`; power, workers and recipes unchanged. `lategame_freed_cells.json`: the 2026-10-22 inside cells now lie outside the 7x6 footprint.
- **Maps:** the processor is now under `largeFootprint` (8), so `prepare_deep_frontier_map.py` lists it with the drill in `FLAT_SITE_TEMPLATES` (the deep-industry stage needs it: the only building that turns DeepOre into products). `map-setup-terrain` still fails only on `smallMap.maxArea`, re-derived after the pass.
- **Old saves:** a placed processor keeps its position and entrance and frees the tiles it no longer uses at any rotation; a flipped one's entrance moves 4 tiles (local x 9 -> 5). Shafts and pipes on removed walls disconnect.
- **Review:** `outputs/compaction/DeepProcessor-before-after.png`, `DeepProcessor-compaction-close.png`, `DeepProcessor-footprint-height.png`.
- **Checks (mirror):** canonical generation to a fixed point; 21 `validate_all -Only` checks pass except `map-setup-terrain` (maxArea, as above); triangle budget passes.
- **In game:** not seen yet.

## Compaction: civic and wellbeing late-game buildings (Claude Code session, 2026-10-30, built by an agent; each building committed when promoted; validated in mirror `civicwell` on HEAD + that building; not built or run in game)

- **Shared:** `lategame_kit.parapet` (and `flat_roof(..., parapet_height=)`) caps its ring with one IRON plate over the whole roof, so `measure_connection_faces.py` records the roof below as covered and blocked and it never becomes a roof deck. The compacted buildings use `parapet_ring` from the new `lategame_roofdeck_parts.py` instead (walls and cap strips only, inside the 0.15 occupancy inset). The kit helper is unchanged. Costs are held by `lategame_cost_basis.json`.
- **Public Health Lab 8x6x12 -> 6x4x5** (`lategame_PublicHealthLab.py`; user: "public health lab needs to shrink a decent amount"):
  - **Art:** two one-layer storeys: concrete ground floor with factory windows and the door, pale plaster lab floor in a grey timber frame with a lancet in every bay. Flat roof deck on layer 2 with a parapet ring. The ventilation tower (HERO) is now a short louvred shaft on one roof cell, crowned by the same four cowls and the main cowl; the anemometer sits on a spindle above the main cowl. Every other roof cell is clear (the fume flue and its steam emitter were dropped: an emitter bars the cells round it from the roof deck; BRIEF "no clutter on buildable space"). Removed: the two-layer podium, the second plaster storey, the mansard and dormers, the observation lantern with its rails, the eight-layer tower with floor bands, ladder, top rails and duct bridge, and the header tank. Same textures, material slots and UV authoring; the 6 animated parts keep their names and kinds.
  - **Checks on the art:** triangles 7,854 -> 4,116 (ceiling re-recorded); strict z-fight 0 visible (frames 1/31/61/91); hidden-geometry audit 0 culled faces exposed; grid audit 0 misses.
  - **Data:** same origin, door tile and Entrance (4,-1,0). Occupied cells 293 -> 51, box colliders 21 -> 2, shaft faces 117 -> 86, pipe ports 52 -> 31, roof deck 23 platformable cells (every roof cell but the shaft's; was 9). No smoke or steam emitter. Cost, power 100 and 3 workers unchanged. `lategame_freed_cells.json` footprintAfter 6x4x5.
  - **Maps:** at 6x4 it is under `largeFootprint` (8), so it no longer needs a map site: its site rows leave all 20 `tools/map_variants`, Diorama's unmet item and the Diorama "No room for" text drop it, and `docs/maps.md` loses its rows.
  - **Old saves:** a placed lab keeps its origin and entrance at any rotation and frees the tiles it no longer uses. A flipped lab's entrance moves 2 tiles (the flip mirrors across the width, 8 -> 6). Shafts and pipes on removed walls disconnect.
  - **Review:** `outputs/compaction/PublicHealthLab-before-after.png`.
- **Technical School 11x5x14 -> 8x4x7** (`lategame_TechnicalSchool.py`):
  - **Art:** the clock tower stays the silhouette (allowed: it is the building's defining feature) at half its height: door storey, a shaft to layer 3, the four-faced clock stage, a lancet belfry and the teal pyramid spire with the weathervane. Central block x 3..8: rusticated concrete ground storey and orange plaster upper storey, one layer each, under a flat roof deck on layer 2 with a parapet ring. The left lecture wing became a one-layer engine house with a flat roof deck on layer 1; the demonstration beam engine (flywheel, rocking beam, governor, boiler) stands on a low bed in front of it. Removed: the right lecture wing, both hipped roofs with ventilator cupolas, the roof skylight, the two roof chimneys and the yard guard rail; the boiler stack shows no plume (its steam emitter barred the engine-house roof cells). Same textures, material slots and UV authoring; the 10 animated parts keep their names and kinds.
  - **Checks on the art:** triangles 9,024 -> 6,842 (ceiling re-recorded); strict z-fight 0 visible (frames 1/31/61/91); hidden-geometry audit 0 culled faces exposed; grid audit: no floor or ground misses; the edge notes are the tower base on x 4.75/6.25 (as before) and the engine bed.
  - **Data:** same origin, door tile and Entrance (5,-1,0). Occupied cells 283 -> 81, box colliders 17 -> 11, shaft faces 144 -> 72, roof deck 18 platformable cells (was none), no smoke or steam emitter. Cost, power 1,800 and the 12 study seats unchanged. `lategame_freed_cells.json` footprintAfter 8x4x7; its 2026-10-22 inside cell (1,0) now holds the engine.
  - **Maps:** at 8 wide it still needs a flat site; the variant sites stay (the smaller footprint lies inside each old site with the same origin).
  - **Old saves:** a placed school keeps its origin and entrance at any rotation and frees the tiles it no longer uses. A flipped school's entrance moves 3 tiles (width 11 -> 8). Shafts on removed walls disconnect.
  - **Review:** `outputs/compaction/TechnicalSchool-before-after.png`.
- **Town Plaza 9x9x6 -> 7x8x4** (`lategame_TownPlaza.py`):
  - **Art:** the same square with the native Fountain of Joy (3 x 3), its terracotta ring and the visitors' 15 places round it, and the native Iron Teeth beaver statue. The bandstand stands on a 3 x 2 podium one layer high, with columns one layer tall under a smaller bell roof (kept as its defining silhouette). The right and back paving strips are gone. No clutter on buildable paving: the four flagpoles stand on the bandstand podium's corners instead of the corner paving, and the statue plinth fits one tile (1,1), so every paved cell outside the fountain is free. Same textures and materials; the weathervane and four flags keep their names and kinds.
  - **Checks on the art:** triangles 5,718 -> 4,994 (ceiling re-recorded); strict z-fight 0 visible (frames 1/31/61/91); hidden-geometry audit 0 culled faces exposed; grid audit 0 misses.
  - **Data:** same origin, door tile, Entrance (4,5,0) and 15 visitor slots (capacity unchanged). Occupied cells 71 -> 34, box colliders 12 -> 6. Cost unchanged. `lategame_freed_cells.json` footprintAfter 7x8x4; of its 2026-10-22 inside cells only (0,7) is still inside, now free paving.
  - **Maps:** 8 deep, so it keeps its flat map sites.
  - **Old saves:** a placed plaza keeps its origin, entrance and visitor places at any rotation and frees the tiles it no longer uses. A flipped plaza moves 2 tiles across its width (9 -> 7), entrance and visitor places with it.
  - **Review:** `outputs/compaction/TownPlaza-before-after.png`.
- **Greenhouse 9x5x9 -> 9x3x5** (`lategame_Greenhouse.py`):
  - **Art:** the glazed palm pavilion (HERO) on a low podium with the door, walls up to layer 2 and a flatter two-tier faceted glass dome, lantern and weathervane; the two glazed wings are one storey (eaves at 0.95, no floor band) under their glazed ridge roofs. The glazed ridge roofs and dome stay as the glasshouse's defining silhouette. The boiler house moved from behind the pavilion to the strip behind the right wing (one layer, flat roof, the smoke stack 4.2 high instead of 8.3), with the coal bunker beside it and the circulating pump and flywheel on its roof; the strip behind the left wing holds only the heating main on the wing wall, so its cells stay free (no clutter on buildable space). Same textures and materials; the 8 animated parts keep their names and kinds.
  - **Checks on the art:** triangles 9,628 -> 7,478 (ceiling re-recorded); strict z-fight 0 visible (frames 1/31/61/91); hidden-geometry audit 0 culled faces exposed; grid audit: no floor or ground misses (one edge note: the boiler-house wall set 0.13 back from the pavilion's corner post).
  - **Data:** same origin, width, door tile and Entrance (4,-1,0). Occupied cells 148 -> 69, shaft faces 87 -> 46, pipe ports 40 -> 19, box colliders 8 -> 6; the smoke and smog source moves to the new stack mouth (7.45, 2.5, 4.3). No roof deck (glass roofs; the boiler-house roof sits beside the smoke). Cost, power 35 and the worker unchanged. `lategame_freed_cells.json` footprintAfter 9x3x5.
  - **Maps:** 9 wide, so it keeps its flat map sites.
  - **Old saves:** a placed greenhouse keeps its origin, entrance and width at any rotation, flipped too, and frees the back tiles it no longer uses. Shafts and pipes on removed walls disconnect.
  - **Review:** `outputs/compaction/Greenhouse-before-after.png`.
- **Bathhouse 9x7x11 -> 7x5x5** (`lategame_Bathhouse.py`):
  - **Art:** the cross-vaulted bath hall (HERO: four teal plank barrel quarters in groins, iron-banded arches over semicircular thermal windows, the louvred steam lantern) is kept as the defining silhouette on a 3 x 3 hall: a rusticated one-layer concrete storey with the door, a short orange plaster band and the vault (crown 2.45 instead of 6). The changing wing and the boiler room are one layer high with flat roofs and low parapets (no lean-to or plank gable); the plunge pool is in front, the flywheel and laundry drum stand along the boiler-room wall and the front row stays bare ground (no clutter on buildable space); the steam stack is 4.4 high instead of 10.5. Same textures and materials; the flywheel, laundry drum and safety-valve lever keep their names and kinds.
  - **Checks on the art:** triangles 9,722 -> 7,704 (ceiling re-recorded); strict z-fight 0 visible (frames 1/31/61/91); hidden-geometry audit 0 culled faces exposed; grid audit 0 misses.
  - **Data:** same origin, door tile and Entrance (3,1,0). 12 visitor seats as before (6 in the pool, 6 in the hall). The study's Water inlet moved to the boiler room's back recess, cell (6,4,0) Up (was (7,6,0)). Occupied cells 213 -> 59, box colliders 22 -> 11, shaft faces 162 -> 55, pipe ports 81 -> 17, roof deck 8 platformable cells (changing-wing and boiler roofs). Cost, power and water unchanged. `lategame_freed_cells.json` footprintAfter 7x5x5; its 2026-10-22 inside cells (0,0) and (0,1) are now the pool.
  - **Maps:** at 7x5 it is under `largeFootprint` (8), so it no longer needs a map site: its site rows leave the variants, Diorama's unmet item and "No room for" text drop it, and `docs/maps.md` loses its rows.
  - **Old saves:** a placed bathhouse keeps its origin and entrance at any rotation and frees the tiles it no longer uses. A flipped one's entrance moves 2 tiles (width 9 -> 7). A pipe on the old inlet must be reconnected at the new one; shafts on removed walls disconnect.
  - **Review:** `outputs/compaction/Bathhouse-before-after.png`.
## Compaction: Stone Crusher one-layer workshop, 4x4x5 -> 4x4x3 (Claude Code session, 2026-10-30, built by an agent; scene, export and blueprint promoted; validated in mirror `ind-head` (HEAD + this change) and the real repo; not built or run in game)

- **User:** one layer per storey, flat roofs. The crusher was already 4x4; its workshop was two layers tall under a machine deck at layer 2.
- **Changed:** `CRUSHER_DECK` 2 -> 1 (`industrial_levels.py`): the closed workshop is one layer, the concrete machine floor is at layer 1, and the reviewed machinery (rolls, flywheel, sprockets, chains, hopper, roofs) moves down 1.0 rigidly. The roll and hopper roofs are flat native roof sheets (`crusher_workshop_details.py`), the hopper roof 0.11 above the roll roof. Hard-coded heights that assumed the old deck now follow it: west and east wall braces, couplings, the east cable trunk, the louvre vents. The windows in the one-layer walls are smaller (scale 0.45), and the clerestory pane over the porch went. The porch canopy's back edge and right shoe stop short of the front roll bearings. Height 5 -> 3 (art top 2.92).
- **Kept:** footprint, origin, door, entrance (1,-1,0), materials and atlas slots, animated parts (2 rolls, flywheel, 2 sprockets), recipe, cost and workers (checked against HEAD).
- **Data:** layout size, `industrial_occupancy.mjs` cells (layer 0 workshop and porch, layer 1 machine floor, layer 2 hopper and roofs), catalog size, LEVELS envelope 3; wall faces, connection faces, the `roof_decks.json` row (one platformable cell on the flat hopper roof) and the triangle ceiling (8,817 -> 8,769) remeasured; `IndustrialAcceptance` expects 4x4x3.
- **Cleanup:** `factory_clearance.py` removed (walkway routes for decks that no longer exist; nothing imported it). `test_catalog_surfaces.py` imports work again and its crusher, quarry and pit cases follow the compact geometry; the whole test passes.
- **Old saves:** footprint, origin and entrance unchanged; the top two layers are freed.
- **Checks:** strict z-fight 0 visible; `exports-industrial`, `model-bindings`, `building_entrances`, `construction_materials`, `freed_cells`, `status_icon_anchors`, `audit-building-assets` pass (the `roof_decks` failures are other agents' buildings). Scripts compile.
- **Review:** `outputs/compaction/StoneCrusher-before-after.png`.

## Compaction: Restaurant, Hospital and Grocery Store (Claude Code session, 2026-10-30, civic agent; generated and validated in mirror `civic`, promoted into Data; not built or run in game)

- **Restaurant 9x7x9 -> 9x7x5** (user: "needs to be shortened but footprint needs to stay the same"; one layer per storey). Footprint, origin and ground door unchanged.
  - Storeys: ground hall, kitchen and vestibule 0-1, middle hall and first dining balcony at 1, upper hall and second balcony at 2, flat roof at 3 (`restaurant_structure.py`, `SIZE`, `HEADROOM` .72 under the deck beams one layer up).
  - Flat roof: the main roof is a `MainRoof` platform (cast slab, timber decking, low parapet) level with the roof terrace bays; the gabled roof, dormers and lantern are gone. The roof stairhead is one layer with a flat cast cap. The carved sign (`#Restaurant.CarvedSign`, 61 frames) swings from a steel gantry on the front edge of the roof; two kitchen chimneys keep their smoke.
  - Kept: all 7 tables and 14 seats, both dining balconies with their rails, planters and lamps; the 3x3 roof terrace stays clear. The oven is rebuilt below the one-layer kitchen's fascia.
  - Interior route: a stair column at (4,3) through the three halls into the stairhead; doors at layers 0/1/2/3. Service cells and staff slots moved to layers 1/2 (`civic_building_content.mjs`). 59 rail openings unchanged.
  - Triangles 19,846 -> 14,622 (ceiling recorded).
- **Hospital 12x9x9 -> 4x9x9** (user: "keep it as it is, but remove the right and left wings, just keeping the center").
  - The central pavilion keeps its roof, storeys, materials, banners and doors exactly; both ward wings, their front balconies, the rear balcony ends, the ward roofs and the West/East ward doors are gone. The rear decks, roof garden and their doors (ground, rear deck, rear ward, roof garden) were already in the pavilion. The pavilion's lower side walls carry the upper storey's lancets now.
  - One steam flue moved onto the roof garden's front-left cell (outside the clear 4x3 area), so the hospital keeps its steam; the two ward flues went with the wings.
  - `ORIGIN` x -4 (artwork keeps its source coordinates); ward work point (6.5,0,3.5) -> (2.5,0,3.5), the same pavilion cell, now from `hospital_layout.wardWorkPosition`.
  - Map variants: each Hospital site moved +4 tiles along its local x, so the pavilion stays where it stood (oasis' door approach had moved onto lower terrain).
  - Triangles 18,222 -> 10,899.
- **Grocery Store 9x6x8 -> 9x6x5**: one layer per storey (shop floor 0-1, market room 1-2, balcony at layer 1, stair bay for one native stair). The gable roof with its lit monitor stays: it is the market's defining silhouette and keeps it clearly different from the flat-roofed Restaurant. Eaves .30 -> .20 so the front and back rows at layer 1 stay free; arcade, stall-wing pents, awning, hoist and stocked displays lowered; the hoist door above the dock and the upper-window flower boxes are gone. Triangles 19,620 -> 18,662.
- **Shared code (append-only; other buildings unchanged):** `grid_structure.room(wall_style='storey')` opt-in one-layer infill; `grid_structure.platform` pier knee braces start above the pier only when `z1-.62` falls inside it (never true for the existing two-layer posts); `civic_validation` takes an explicit per-model `headroom` (1.09 for the two-layer buildings); `civic_isometric_geometry.hanging_board_storey` (new). `validate_building_entrances.mjs` and `civic_building_content.nativeEntrance` accept an Entrance cell whose building block holds only Top/Corners: a vanilla Path ('Path') shares such a cell, as under a vanilla Platform or Overhang (the Restaurant doorstep is under its layer-1 balcony).
- **Saves:** Restaurant and Grocery keep footprint, origin and ground entrance; their upper decks and doors are one/two layers lower, so player paths, stairs and platforms built on the old balconies or terrace float and need re-placing. A placed Hospital's origin is now the pavilion's corner, so an old hospital, flipped or not, shows the pavilion 4 tiles to the left of where it stood (on its old west wing tiles); re-place it and reconnect its shafts and pipes.
- **Checks:** strict z-fight 0 visible, hidden-geometry 0 culled faces exposed (all three), `test_restaurant_shell.py` 55,834 probes 0 uncovered, sources-civic, triangle budget; mirror `civic` (HEAD + this work): canonical generation and `validate_all -SkipBlender` pass for these buildings (exports-civic/hospital/grocery, restaurant grid/content, building entrances, vertical slice, roof decks, connection faces). Other agents' in-progress buildings failed audit-progression (power plant costs) and two beaverome loop sites (ChemicalWorks, PublicHealthLab) in that mirror.
- **Review:** `outputs/compaction/<Building>-before-after.png`, archived in `docs/art/reviews/2026-10-30-compaction-civic/`.
- **Open:** in-game placement, walking and service; the C# acceptance fixtures (Restaurant, Hospital, Grocery) still use the old coordinates.

## Compaction: Sandstone and Limestone Pit, one storey (5x4x4 -> 5x4x3, 5x3x4 -> 5x3x3) (Claude Code session, 2026-10-30, built by an agent; scenes, exports and blueprints promoted; validated in mirror `ind-head` (HEAD + this change) and the real repo; not built or run in game)

- **User:** one layer per storey, flat roofs, "the mines need to have a lot of tlc". The pits were already vanilla-scale (5x4 and 5x3, like the vanilla 5x5x3 mine), so their footprints, door, apron and entrance stay; the storey goes.
- **Changed** (`pit_isometric_geometry.py`): the store room and working bay now stand under one flat roof of native roof sheets at 1.92 (posts and beams at 1.78, walls to 1.70); the sloped roof that reached 2.93, the store room's clerestory and the door canopy went. The jib hoist is 1.05 lower (top 2.62); the basket, slings and cable foot are 0.70 lower together, so the cable still meets the basket eye and the lift stays 0.35. The jib brace meets the jib clear of the lifted basket. Height 4 -> 3 layers (only the hoist column uses layer 2).
- **Roof deck:** the flat roof is now a platformable roof deck under the existing system (`roof_deck_content.mjs`): 8 cells on each pit (`roof_decks.json` rows); `validate_pit_exports.py` now requires the stackable blocks to equal those cells (it used to require none, for the sloped roof) and reads the sizes from `pit-layouts.json`.
- **Kept:** footprints, origins, entrance (1,-1,0), the door and its approach floor, materials and atlas slots, the three animated parts (`Pit.Winch`, `Pit.HoistedBasket`, `Pit.HoistCable`), recipes, costs and workers (checked against HEAD).
- **Data:** `pit_layouts.py` sizes and column heights (2 under the roof, 3 under the hoist), catalog sizes, connection faces, triangle ceilings (SandstonePit 10,896 -> 10,154, LimestonePit 8,944 -> 8,202). `MineralPitAcceptance` expects 5x4x3 and 5x3x3.
- **Old saves:** footprint, origin and entrance unchanged; the top layer of each pit is freed.
- **Checks:** strict z-fight 0 visible on both; `sources-pits` (door clearance, UVs, hoist loop with no basket intersections), `exports-pit`, `model-bindings`, `building_entrances`, `construction_materials`, `freed_cells`, `status_icon_anchors`, `audit-building-assets` pass; the pit rows of `roof_decks` pass (its other failures are the in-progress Hospital). Scripts compile.
- **Review:** `outputs/compaction/SandstonePit-before-after.png`, `LimestonePit-before-after.png`.

## Compaction: Limestone and Sandstone Quarry 11x7x9 -> 8x6x5 (Claude Code session, 2026-10-30, built by an agent; scene, export and blueprints promoted; validated in mirror `ind-head` (HEAD + this change) and the real repo; not built or run in game)

- **User:** smaller buildings, less scaffolding; "the mines need to have a lot of tlc". Shared model `MineralQuarry` (`quarry_isometric_geometry.py`, `quarry_process_details.py`, rewritten).
- **New quarry:** one stone plinth (top at layer 1) over the seam with the lined shaft collar; a four-post timber headframe boarded on its west and rear faces and in an upper band on the front (east side open for the tipping bucket), the head sheave on carriers on its head frame; the winding drum in an open-fronted, flat-roofed winding house behind it, the rope running drum -> sheave -> bucket; receiver, gravity chute, 16-slat belt, vibrating screen and a ground stone bin on the east side; the front cabin with the native door, a flat-roofed tool room on the west, supply bins and a spoil heap on the front strip, the native water tank in front. Flat roofs use the native roof sheets laid level.
- **Removed:** the side ladder mast and its landing, the lattice headframe with its X bracing and bearing gantry, both upper workshops and the control room with their three decorative doors (`LeftWorkshopDoor`, `RightWorkshopDoor`, `ControlRoomDoor` and the `quarry_bay_return` helper; their door-mounting test rows went too), the pipe racks and roof vessels.
- **Kept:** origin, entrance (1,-1,0), the ground cabin door and idle slot, and the 25 seam foundation cells (grid x 3..7, y 1..5, `Top` over `Ground`), so a saved quarry stays over its seam; materials and atlas slots; every animated part name (hoist drum, sheave, carriage, tipping bucket, load, cable, three flywheels, sieve, belt rollers, belt slats (16, were 22), pour/belt/screen stones); recipes, costs, science, power and workers (checked against HEAD).
- **Hoist law:** travel 2.10 (was 3.60), sheave at 4.45; `quarry_validation.py` checks attachment over all 481 frames, minimum rope 0.80 and that the raised yoke stays under the sheave (the ladder-bay rays went with the ladder).
- **Data:** layout size, `industrial_occupancy.mjs` cells, catalog sizes, LEVELS envelope 5; wall faces, connection faces, the two quarry `roof_decks.json` rows and triangle ceilings (11,784 -> 6,967) remeasured; `IndustrialAcceptance` expects 8x6x5 with no open ground cell inside.
- **Old saves:** same origin, entrance and seam cells, so an unflipped quarry stays valid; the freed former cells (x 8..10, y 6) become empty ground. Flipped placements mirror inside the new width (entrance x 9 -> 6; not verified in game).
- **Maps:** `map-setup-terrain` reports no quarry site error (the seam offset is unchanged). The Beaverome unmet notes in `tools/map_variants` still give the old 11x7 footprint as the reason no quarry site fits; a smaller footprint may now fit there (not re-searched; map data belongs to the map pass).
- **Checks:** strict z-fight 0 visible; motion check; `exports-industrial`, `model-bindings`, `construction_materials`, `freed_cells`, `building_entrances`, `status_icon_anchors`, `exports-preview_budget`, `audit-building-assets` pass; the other failures in that run are other agents' in-progress buildings (Restaurant, Chemical Works, Deep Mine, Public Health Lab, Hospital sites). Scripts compile.
- **Review:** `outputs/compaction/MineralQuarry-before-after.png`, `MineralQuarry-after-views.png`, `MineralQuarry-footprint-height.png`.
- **Not verified in game:** placement over a seam, construction look, hoist and process playback, old-save loading.

## Compaction: late-game power, nuclear and rocketry buildings (Claude Code session, 2026-10-30, built by an agent; promoted building by building; validated in mirror `compactlg`; not built or run in game)

- **Scope:** Nuclear Reactor, Uranium Processing Plant, Radioactive Waste Refinery and Vault, Mission Control, Rocket Assembly Hangar, Launch Pad, Coal and Oil Power Plants, the six small radiation/bot buildings and the Reinforced Hydro Turbine (one agent). Each building is committed as soon as it is promoted. Shared rules: `outputs/compaction/BRIEF.md`. The cost of every compacted late-game building is held by `tools/lategame_cost_basis.json` (46d9ee9).
- **Process per building:** the old scene is copied to `outputs/compaction/before/`; the generator is rewritten and the scene saved unpacked; matched before/after cameras go to `outputs/compaction/<Id>-before-after.png`; strict z-fight audit at frames 1/31/61/91; `lategame_grid_audit`; official export. Canonical generation, connection faces and roof decks run in mirror `compactlg`, which is HEAD plus this work only (other agents' uncommitted files and scenes reset to HEAD). Only these buildings' files and their keys in `roof_decks.json` and `triangle-budget.json` are promoted.
- **Coal Power Plant** 5x5x10 -> 4x4x6 (`lategame_CoalPowerPlant.py`). Boiler house on tiles 0..3 x 0..4: concrete ground storey (layer 0) and one steel-clad storey (layer 1) under a flat concrete roof with an open parapet (top at layer 3), with the riveted coal bunker standing on it. The plank gable is gone. Engine deck (layer 1) and chimney base on tile column 3; the chimney rises to 5.9 (it was 9.9). Flywheel and piston rod keep their names. Triangles 3,758 -> 2,572.
  - **Data:** same origin, door and Entrance (1,-1,0) / LocalAccess. Shaft faces 87 -> 55, pipe ports 62 -> 36, colliders 10 -> 4, 3 roof-deck cells. Smoke and smog follow the stack, now at (3.52, 3.02, 5.9). Cost (125 Plank, 75 Gear, 75 MetalBlock, 30 TreatedPlank, 100 Concrete) and output (25,000) unchanged.
- **Oil Power Plant** 6x6x9 -> 5x4x6 (`lategame_OilPowerPlant.py`). Turbine hall on tiles 0..5 x 0..2: concrete ground storey and one steel-clad storey under a flat roof (top at layer 3). Its two fin-fan coolers now spin in cowls on that roof; the barrel vault and the four-column cooler frame over the tanks are gone. Tank bund with two day tanks and the transfer pump on tiles 0..3 x 2..4. Boiler tower on tiles 3..5 x 2..4 to layer 4, with its two stacks to 5.84. The three animated parts keep their names. `validate_connection_exports.py` CURVED_CASES: the vault faces are replaced by the arched door portal. Triangles 7,160 -> 4,240.
  - **Data:** same origin, door and Entrance (1,-1,0). Shaft faces 125 -> 73, pipe ports 88 -> 50, colliders 4 -> 6, 3 roof-deck cells. Smoke at (3.55 / 4.45, 3.1, 5.84). Cost and output (90,000) unchanged.
- **Old saves (both plants):** a placed plant keeps its origin and entrance. The cells it no longer uses become empty ground. A flipped plant's entrance moves one tile (local x 3 -> 2 for Coal, 4 -> 3 for Oil). Shafts and pipes on removed walls disconnect and need reconnecting.
- **Checks (mirror, Coal and Oil):** canonical generation; `validate_all -Only` exports-connection, exports-lategame, exports-preview_budget, model-bindings, building_entrances, connection_faces, freed_cells, lategame_freed_cells, map_setup, power_rule, roof_decks, smog_content, status_icon_anchors, vertical_slice_content, audit-progression and audit-building-assets pass. Strict z-fight audit: 0 visible. `map-setup-terrain` fails only on `smallMap.maxArea` (re-derived once the pass is done, as on HEAD).
- **Uranium Processing Plant** 12x11x14 -> 8x7x8 (`lategame_UraniumProcessingPlant.py`).
  - **Building:** a one-storey concrete podium with the door, and on its deck an open row of five spinning centrifuges under a solid flat canopy. The cascade hall behind them is lit by a flat-roofed glazed clerestory monitor; roof parapets are open `parapet_ring`s.
  - **Around it:** a 2x2 thickener with its rake, the fuel vault, two acid tanks on a concrete bund, and the scrubber house with its column, fan and a stack to 7.8.
  - **Removed:** the lattice gantry girder, the layer-4 catwalk and its ladder, the two hidden inner centrifuge rows, the stack's work ring, the 13-layer stack and the monitor gable. Under the no-clutter rule, the open drum dock and its jib hoist also went, so `HoistCable` and `HoistHook` are dropped and tiles 6..8 x 2..4 are free.
  - **Triangles:** 19,684 -> 8,874.
  - **Data:** same origin, door and Entrance (3,-1,0). Shaft faces 246 -> 139, pipe ports 113 -> 61, colliders 56 -> 24, roof-deck cells 16 -> 26. Steam emitter at the new stack (7.2, 6.15, 7.8). Cost, 53,000 hp and 6 workers unchanged.
  - **Old saves:** keeps its origin and entrance. A flipped plant's entrance moves 4 tiles (local x 8 -> 4).
  - **Checks:** same building-level set as Coal/Oil, plus workforce_risks and building_sounds; all pass apart from `map-setup-terrain` (maxArea only). Strict z-fight audit: 0 visible.
- **In game:** not seen yet.
- **Radioactive Waste Vault** 9x10x12 -> 8x7x6 (`lategame_RadioactiveWasteVault.py`; the old `GRID_ORIGIN` (4,2) corner is the same grid origin, now authored directly).
  - **Building:** two one-layer battered berm courses (there were three), a lower ribbed dome on a short buttressed drum with its turning lantern, two vent towers with turning cowls (ending 4.4/4.9, was 8.6/9.6), the cask port in the left berm face, and a flat-roofed gatehouse with an open parapet ring (the plank gable is gone). The dome stays as the defining silhouette.
  - **Triangles:** 6,086 -> 4,466.
  - **Data:** same origin, door tile and Entrance (4,-1,0). Colliders 21 -> 13, roof-deck cells 1 -> 5. No power or pipes. `lategame_freed_cells.json`: footprintAfter 8x7x6, outsideCells 100; the two recorded inside cells stay free. Cost unchanged.
  - **Old saves:** keeps its origin and entrance. A flipped vault's entrance moves 1 tile (local x 4 -> 3).
  - **Checks:** building-level set plus radiation_content and meltdown_content pass; `lategame_freed_cells` passes with the record. Strict z-fight audit: 0 visible.
- **Reinforced Hydro Turbine** 8x10x7 -> 8x10x6 (`hydro_isometric_geometry.py`, `hydro_layout.py`, `hydro_content.json`, `hydro_building_content.mjs`).
  - **Unchanged (gameplay):** the conduit, the dam cap (support surface on layer 6), the gates, the intakes and outlets, the solid and closed-gate water cells, and the layer-2 service terrace with its built-in walkways, rails and ports.
  - **Workshop:** one storey from the terrace to a flat concrete roof whose top is layer 4. It replaces a three-layer room under a plank gable with a dormer, so nothing rises above the dam cap.
  - **Blocks:** the workshop region is now layers 2..3; the eave, gable and dormer regions are gone.
  - **Scene:** rebuilt by `render_reference_studies.py --models ReinforcedHydroTurbine`; wall faces re-measured.
  - **Checks:** exported through `export_checked_models.ps1` (strict audit 0 visible at frames 1/31/61/91). `audit_hidden_geometry` and `validate_hydro_source` pass.
  - **Triangles:** 12,459 -> 10,292.
  - **Data:** Size Z 7 -> 6. Colliders and solid cells 227 -> 187, shaft faces 161 -> 169 (the flat roof's walls), roof-deck cells 21 -> 29. Power (40,000 hp), cost and walkway nodes unchanged.
  - **Old saves:** same footprint, origin and terrace. Anything placed on the old roof slopes does not exist.
  - **Validation:** in the mirror, the building-level set plus exports-hydro passes (map-setup-terrain maxArea only).

## Compaction: Deep Mine 10x11x16 -> 7x6x7 (Claude Code session, 2026-10-30, built by an agent; scene, export and blueprint promoted; validated in mirror `minesdrill` on HEAD b2d8fb6 + this change; not built or run in game)

- **Art** (`lategame_DeepMine.py`, saved scene unpacked; user: "the mines need to have a lot of tlc"): a compact plated steel headframe (head deck at layer 5) on a low one-layer concrete shaft house over the vein. Corrugated sides and back, open front showing both skips on their timber guides, two box-girder backstays, two 1.2-tile sheave wheels on the head deck. The winding drum and flywheel stand in the open on the shaft-house deck, their ropes running up to the sheaves. Ore flow: the skips tip into a chute through the headframe's side, into a boarded ore bin; its front chute fills an ore tub that runs out along a short front track. Brick lamp house with the door and a flat parapet roof; one-layer bath-house annex with chimney and hot-water tank. Removed: the 13-layer open lattice headframe (bracing, gussets, lattice backstays, gantry, caged ladder), the drum shed, the two-storey monitor-roofed engine house, the ore bin on stilts with its tipple deck and head-house, and the gabled bath house. Same textures, material slots and UV authoring.
- **Animation:** the 8 animated parts keep their names (sheaves, skips, ropes, drum, flywheel); skip travel 2.6 (was 7.6). New ninth part `OreTub` (SLIDE_X 1.5).
- **Checks on the art:** triangles 18,508 -> 9,436 (ceiling re-recorded); strict z-fight audit 0 visible at frames 1/26/51/61/91/111; grid audit 0 edge and floor misses, nothing floating; back-face-culled renders show no holes.
- **Data:** footprint inside the old one with the same origin, door tile, Entrance (1,-1,0) and understructure core (tiles x 2-6, y 1-5, `DeepOreVein`): all 25 core cells are building cells (Top), so the vein still has one alignment and map placements (`understructure` = mine + (2,1)) stay valid. Door face on the tile edge (`LocalAccess` z 0.18 -> 0). Shaft transputs 133 -> 85, pipe ports 77 -> 41; smoke and smog at the engine exhaust (4.5, 5.55) and the bath-house chimney (0.55, 5.45); status icon 7.7. Roof decks: 18 platformable cells (lamp-house roof, bath-house roof, the deck, one head-deck cell). Cost held by `lategame_cost_basis.json`; power, 6 workers, recipe, drill bits and shaft lining unchanged. `lategame_freed_cells.json`: the 2026-10-22 inside cells now lie outside the 7x6 footprint (footprintAfter 7x6x7, no inside cells).
- **Old saves:** a placed mine keeps its position and vein and frees the tiles it no longer uses, at any rotation. Flipped mines are the exception: a flip mirrors the footprint across its width, so a flipped mine's entrance moves 3 tiles (local x 8 -> 5) and its vein core moves from local x 3-7 to 0-4, off the vein it was placed on. Re-place a flipped Deep Mine (no map variant places one flipped). Shafts and pipes on removed walls disconnect.
- **Maps:** `map-setup-terrain` still fails only on `smallMap.maxArea` (derived now 10,328), re-derived after the pass. Diorama's unmet Deep Mine reason was measured with the 10x11 mine; a 7x6 mine may now fit (left to the map owner).
- **Review:** `outputs/compaction/DeepMine-before-after.png`, `DeepMine-compaction-close.png`, `DeepMine-footprint-height.png`.
- **Checks (mirror):** canonical generation to a fixed point; the same 19 `validate_all -Only` checks as the drill: 18 pass, `map-setup-terrain` as above; triangle budget passes.
- **In game:** not seen yet.

## Compaction: Deep Drill 11x9x16 -> 7x6x8 (Claude Code session, 2026-10-30, built by an agent; scene, export and blueprint promoted; validated in mirror `minesdrill` on HEAD 46d9ee9 + this change; not built or run in game)

- **Art** (`lategame_DeepDrill.py`, saved scene unpacked): a boarded, tapered tower (crown at layer 7) on a solid concrete engine room whose roof is the drill floor (layer 2), open at the front so the hoist shows; brick pump house with the door, doghouse and pipe joints on its flat roof; mud pump, two mud tanks, two stacks and the radiator fan behind. Removed: the open lattice derrick (diagonals, V-door brace, monkey board, racked pipe), the pier and I-beam substructure with its cellar stack, the pipe ramp and catwalk, the pipe rack and the separate power house. Same textures, material slots and UV authoring. The 9 animated parts keep their names; the hoist stroke is 0.95 (was 2.6) and the radiator fan turns about Y on the back wall.
- **Checks on the art:** triangles 19,264 -> 10,588 (ceiling re-recorded); strict z-fight audit 0 visible at frames 1/31/61/95/121; grid audit 0 edge and floor misses; back-face-culled renders show no holes.
- **Data:** footprint inside the old one with the same origin, door tile and Entrance (1,-1,0). The door face moved onto the tile edge (`LocalAccess` z 0.18 -> 0). Shaft transputs 121 -> 57, pipe ports 41 -> 25, box colliders 51 -> 20; smoke and smog sources at the two new stacks (3.6/4.6, 5.5, 4.9); status icon 8.7; roof decks: 2 drill-floor cells. Cost held at its old value by `lategame_cost_basis.json` (Plank 445, Gear 175, MetalBlock 140, Concrete 180); power 1,000, 3 workers and the drill-bit upkeep unchanged.
- **Maps:** the drill is now under `largeFootprint` (8), so `prepare_deep_frontier_map.py` names it explicitly (`DEEP_DRILL`): the deep-industry stage counts its sites (`minDrillSites`). `map-setup-terrain` fails only on `smallMap.maxArea` 11176 != derived 10796, to be re-derived once the compaction pass is done. The unmet texts of Beaverome, Meander and Waterfalls still cite 11x9 drill footprints; a 7x6 drill may now fit there (left to the map owner).
- **Old saves:** a placed drill keeps its position and frees the tiles it no longer uses, at any rotation. A flipped drill keeps its footprint but its entrance moves 4 tiles (local x 9 -> 5). Shafts and pipes on removed walls disconnect and need reconnecting.
- **Review:** `outputs/compaction/DeepDrill-before-after.png` (matched cameras) and `DeepDrill-footprint-height.png`.
- **Checks (mirror):** canonical generation; `validate_all -Only` exports-lategame, exports-preview_budget, model-bindings, building_entrances, connection_faces, freed_cells, lategame_freed_cells, roof_decks, smog_content, status_icon_anchors, vertical_slice_content, power_rule, bot_upkeep, map_setup, audit-progression, audit-building-assets, tool_groups, workforce_risks pass; triangle budget passes.
- **In game:** not seen yet.

## Compaction: Cement Kiln 7x5x6 -> 5x3x4 and Concrete Mixer 7x5x7 -> 4x3x3 (Claude Code session, 2026-10-30, built by an agent; scenes, exports and blueprints promoted; validated in mirror `cmp-industrial` and the real repo; not built or run in game)

- **User (Steam Workshop feedback):** the buildings exceed Timberborn's scale; "the textures are fine.... it is the scaffolding and size". The user approved these two candidates ("looking much better") before promotion.
- **Cement Kiln** (`kiln_isometric_geometry.py`, rewritten): closed plank feed house with an open limestone bin (grid x 0); the drum (3.2 tiles of it in view, was 4.7) on two roller stations seated on stone blocks, under a lean-to roof with a closed back wall (x 1..3); the stone firebox with arched fire, ash grate and chimney (x 4); the unchanged one-tile porch and door (x 3); logs, coal bin and cement output bin in the front row. Removed: the open timber trestle and raised drum deck, the raised feed tower, the long operator room, the third roller station. Triangles 11,930 -> 6,183.
- **Concrete Mixer** (`mixer_isometric_geometry.py`, rewritten): the closed operator room (grid x 0..1, all rows) with door, canopy and clerestory, its concrete roof carrying the aggregate and cement hoppers, which feed the drum by two short chutes; the drum (same profile at 0.62 scale) on four rollers on low concrete piers, its flywheel on a concrete drive pedestal; the wet tray front right; the native header tank on a concrete pedestal rear right. Removed: the timber feed tower and its roofs, the stilted tank tower and deck, every timber leg under the drum, hoppers and tray. Triangles 9,865 -> 5,088 (+359 native tank preview).
- **Kept:** origin, entrance (kiln (3,-1,0), mixer (1,-1,0)), door anchors and native door recipes, idle slots, materials, atlas slots and UV authoring, moving-part names (kiln: barrel, 4 rollers (were 6), pinion, drive wheel, 3 flames; mixer: drum, drive), recipes, costs, science, power and workers (checked against HEAD blueprints).
- **Registration:** `industrial_layouts.py` sizes, `industrial_occupancy.mjs` cells, `construction_materials.json` sizes, LEVELS kiln envelope 4. Mixer pipe inlet (3,2,0) Right (pedestal east face, was (6,4,0)) and power-line point (3.9, 2.9, 1.32) (was (6.9, 4.9, 3.8)); kiln smoke re-registered at the new stack (4.5, 2.45, 3.94). Wall faces, connection faces and the kiln/mixer `roof_decks.json` rows remeasured; triangle ceilings recorded.
- **Old saves:** unflipped placements load with the smaller footprint at the same origin; the entrance cell is unchanged and the freed cells (kiln: the two right columns and two back rows; mixer: three right columns, two back rows) become empty ground. Flipped placements mirror inside the new width, so their entrance moves (kiln x 3 -> 1, mixer x 5 -> 2; not verified in game). A pipe connected at the mixer's old inlet (6,4,0) and a power line attached at the old insulator detach and must be reconnected.
- **Checks:** strict z-fight audit 0 visible on both; kiln motion check (10 parts loop) and `sources-mixer`; `exports-industrial`, `model-bindings`, `construction_materials`, `freed_cells`, `building_entrances`, `status_icon_anchors`, `exports-preview_budget`, `promote-clearance`, `audit-building-assets` pass. The remaining failures in that run (`exports-connection`, `connection_faces`, `roof_decks`, `smog_content`, `vertical_slice_content`) are the in-progress Deep Drill and Coal Power Plant work of other agents. Scripts compile.
- **Tests and fixtures:** `test_catalog_surfaces.py` kiln and mixer patches follow the new walls (the file still fails to import the old crusher `workshop`, a separate stale import fixed with the crusher pass). `IndustrialAcceptance` and `MixerAcceptance` expect the new sizes and freed cells. `FactoryTransportAcceptance` still encodes the 7x5x7 mixer (lanes on its west wall rows 1..3) and fails explicitly until its lanes are re-laid; not run.
- **Review:** `outputs/compaction/CementKiln-before-after.png`, `ConcreteMixer-before-after.png`, `*-after-views.png`, `footprint-height-comparison.png` (untracked outputs).
- **Not verified in game:** placement, construction look, animation playback, smoke, pipe and power-line connections, flipped placements, old-save loading.

## Cleanups: rerunnable Reactor Bots generator, data-sized acceptance power, drill-bit descriptions (Claude Code session, 2026-10-30, built by an agent; validated in mirror `cleanups` and the real repo; not built or run in game)

- **User:** three follow-ups from the Power, Drill bits and Reactor Bots entries.
- **Reactor Bots generator reruns** (`tools/super_bot_content.mjs`): it now follows the radiation and Deep Well pattern.
  - Its own files are rewritten each run: settings, the 5 needs, part goods and recipes, light colour, charging bay and icons.
  - The files it extends are rewritten fresh by their producers each canonical run: collections, manufactories, upkeep goods and `enUS.csv`. They must not already hold its ids, and a vanilla good, recipe, need or colour with one of its ids still fails.
  - Two full canonical runs in the mirror leave every Data file byte-identical. A standalone rerun on generated data still stops ("already runs", "already lists", "already has ConsumptionEffects") without writing anything.
  - `validate_all` does not generate. `validate_super_bots` checks the outputs against the generator's functions.
- **Acceptance power** (`AcceptancePower` in `AllBuildingsAcceptance.cs`):
  - Correction to the Power entry: a fresh DevPowerGenerator gives 5,000 hp, not 10,000. Native `AdjustableStrengthPowerGenerator.InitializeEntity` sets strength 0.5, and the strength is not saved, so a loaded one runs at 1 (decompiled 1.1.2.8). Every consumer above 5,000 hp was underpowered in the bulk runs.
  - Each consumer's test generator now has an output multiplier of `ceil(PowerInput / PowerOutput)`, read from the consumer's and the generator's `MechanicalNodeSpec`. `MechanicalNode` does not clamp the multiplier.
  - **AllBuildings:** applied in `AttachPower`.
  - **Lategame:** applied in `PlacePower`, and again on reload in `BindSaved`.
  - **Rocket run:** `AddLaunchPower` raises the layout run's generator by whole rated outputs to the pad load plus the existing 2,000 hp margin. Before, it placed extra generators at 0.5. `SetSupply(false)` sets one generator to the whole outputs just below the launch load (27,000: 20,000). The `10000` literals and unused injected fields are gone.
  - `HospitalAcceptance` is unchanged: two stacked generators, set to 1.
  - Compile check passes. Acceptance was not run in game.
- **Drill-bit descriptions:**
  - `workplaceUpkeep.roles` gained `description` ("high-grade steel drill bits", "concrete shaft lining").
  - `bot_upkeep_content.mjs` `upkeepDescription` appends one sentence to each upkeep building's description row, the way the connection step appends its pipe phrase. Deep Drill: "Wears out 0.1 high-grade steel drill bits per hour at full crew and stops without them." Deep Mine: "... 0.1 high-grade steel drill bits and 0.1 concrete shaft lining ...".
  - `validate_bot_upkeep` checks that the sentence is there exactly once.
  - The two regenerated rows reached `enUS.csv` in ef3fd53, which staged the whole file while this work was in progress. This commit adds the generator that produces them.
- **Checks:**
  - mirror `cleanups`: two canonical runs, byte-identical; `validate_all -SkipBlender` 55 pass + 1 report-only (`no-game-assets` outside git).
  - real repo: `validate_all -SkipBlender` 56 pass + 1 report-only; compile.

## Maps: Beaverome warning, fuller Deep Ore Sources, rebuilt map files (Claude Code session, 2026-10-30, built by an agent; validated in mirror `mapfix` and the real repo; not built or run in game)

- **User:** Beaverome gets the EXTREMELY difficult warning (deep ore is required and it has none), with a data-driven rule rather than a map list. Finite Deep Ore Sources should cover one of each building with margin. Rebuild the four map files and fix the stale map test.
- **Warning rule** (`tools/map_setup.json` `smallMap`): a map gets the warning when its area is below `maxArea` (11,176) **or** its variant lists no primary site of `deepMineSite` (`DeepMine.IronTeeth`, the only permanent deep ore). `prepare_deep_frontier_map.py builtin` checks that it is the only building over a Deep Ore Vein.
  - Warned maps: Beaverome (no Deep Mine), Cliffside (area) and Diorama (area and no Deep Mine).
  - `BuiltinMapSpec.Small` is replaced by `SmallArea` + `NoDeepMineSite`, and the C# `Small` is now computed from them.
  - Dialog: the title is "Deep Frontier is EXTREMELY difficult on {0}". The small-map lines (size, room, height) show only on small maps; a new `SmallNoDeepMine` line shows on maps without a Deep Mine.
- **Finite deep ore:**
  - `DeepOreSource` `StockpileSpec.MaxCapacity` is 10,000 (was 4,000; set in `create_vertical_slice_content.mjs`).
  - Map source amounts: two-source maps 17,000 (8,500 + 8,500; Lakes and Terraces 7,000 + 10,000); three-source maps 18,000 (x3).
  - The `acceptedGaps` entry is retired (`acceptedGaps` is now empty). The check now counts only sources with a checked drill site within 25 cells and requires their DeepOre to cover one of each building, as the ProgramModel computes it (15,608 now), plus `finiteDeepOreMargin` 5% = 16,389.
  - Beaverome declares it `unmet` (no Deep Drill site fits, so it has no sources), with a new `unmetText` line.
- **Map files:** `build` rewrote the four files in `Documents/Timberborn/Maps` (0.6.0.0 description; Plains and Plains Hard 18,000, Lakes and Terraces 17,000). 0 errors; hashes in `docs/maps.md`.
- **Test:** `test_prepare_deep_frontier_map.py`: the stale `no_dynamite` case (Plains lists no Dynamite) is replaced by "a Dynamite cell outside the footprint". 17/17 caught; "finite deep ore too small" now fails as a real requirement.
- **Docs:** `docs/maps.md` (rule, dialogs, per-map table, quantities table refreshed to the current costs), CHANGELOG, Workshop description and 0.6.0 change notes.
- **Checks:** `builtin` passes on all 19 maps, compile check passes, real repo `validate_all -SkipBlender` 56 pass + 1 report-only.
- **In game:** not run. Still to see: the Beaverome dialog, a 10,000 source in the map editor, and a Deep Drill on a 8,500 source.

## Built-in maps: new-game resource setup, 66-layer height, small-map warning (Claude Code session, 2026-10-29, built by an agent; validated in mirror `maphook` and the real repo; not built or run in game)

- **User:** add the Deep Frontier resources to the official maps automatically, for all built-in maps (Diorama the hardest), and warn that small maps are EXTREMELY difficult.
- **Detection:** `GameSceneParameters.NewGame` with `NewGameConfiguration.MapFileReference.Resource` and `.Name`, the same test native `MapNameService.Load` uses. A saved `DeepFrontierMapSetup` singleton makes it run once per settlement. Old saves and map files, including the shipped variants, are untouched.
- **Placement:** the map editor's path. A `PreviewFactory` preview must pass `BlockObject.IsValid()`, then `BlockObjectPlacerService.GetMatchingPlacer(spec).Place(...)`; Deep Ore Sources are placed finished. Stockpiles are filled as `FixedStockpileInventorySetter` does. A rejected placement is logged and listed in a dialog, never moved or skipped.
- **Height:** {23 terrain, 66 total}. A postfix on `GameSceneSerializedWorldSupplier.Load` keeps the new game's world; a prefix on `MapSize.Load` writes `MapHeight` for Map Transformer to apply and keep. The global `MapSizeSpec` is not touched; the stored terrain layers are read unchanged. Files: `Scripts/MapSetup/BuiltinMapHeight.cs`, `BuiltinMapSetup.cs`, `MapSetupSpecs.cs`.
- **Data:**
  - One spec per map in `tools/map_variants/*.json`; 16 are new runtime-only specs with declared unmet requirements.
  - `tools/map_setup.json` sets the small-map threshold: 11,176 tiles, twice Plains' late-game site footprint. Small maps: Diorama, Cliffside.
  - `tools/map_setup_content.mjs` writes `Configurations/DeepFrontierMapSetup.blueprint.json` and the dialog texts.
  - `tools/validate_map_setup.mjs` checks the data, and `prepare_deep_frontier_map.py builtin` (`map-setup-terrain` in `validate_all`) validates every spec against its unmodified built-in map.
  - Built-in Plains uses `plains.json`; Plains Hard stays map-file only.
- **Gaps per map:** documented in `docs/maps.md` ("Built-in maps: new-game setup"). 11 maps have no reactor site; Beaverome has no deep ore; Diorama has no Deep Mine site.
- **Accepted gap: finite deep ore.** Since the cost pass, one of each building needs about 15,600 DeepOre, but the maps carry 4,000–6,000 in sources. The loop still closes through the Deep Mines. Decision pending (more or fuller sources, or a bootstrap rule).
- **Tool fixes:**
  - dry badwater sources count (Nomads, Oasis);
  - tunnel sources feed their river (Hollows);
  - `plan` keeps going past an unplaceable building;
  - `map_loop_requirements.json` gained ReinforcedBotFrame, BotChassis and ReactorPowerCell.
- **Checks:** real repo `validate_all -SkipBlender` 56 pass + 1 report-only; compile.
- **Open:**
  - Rebuild the four shipped map files with `build` before publishing; they still carry the 0.5.0.0 description.
  - `test_prepare_deep_frontier_map.py`'s `no_dynamite` case is stale, so the cases after it don't run.
  - Closed 2026-10-30 (Cleanups entry): `super_bot_content.mjs` rewrites its own outputs on a rerun.
- **In game:**
  - **Plains new game:** the log shows MapHeight {23, 66} and "19 placed, 0 failed"; the slicer reaches 65.
  - **Reload:** no re-placement, and the height is kept.
  - **Dialogs:** Diorama shows the small-map warning once; Canyon shows the short notice.
  - **Untouched:** the Deep Frontier Lakes map file and old saves.

## Power: science-scaled consumer floor and stronger power plants (Claude Code session, 2026-10-29, built by an agent; validated in mirror `power`; not built or run in game)

- **User:** endgame buildings should need lots of power ("smog scrubber only taking 200? more like 2000"); Coal 25k, Oil 90k, Hydro 40k, Nuclear 1M.
- **Rule:** every consumer at >= 2,000 science draws `max(base, 5.65 x science^0.75)` hp (k = 2000 / 2500^0.75; rounded to 100 below 10,000, to 1,000 above). Constants and exemptions (DeepWell: slider-driven; ReactorChargingBay: user-set 5,000) are in `building_construction_costs.json` `lategameRule.power`. `scaledPower(id, base, science)` sits next to `scaledCost` in `tools/lategame_costs.mjs`; every generator calls it where it writes `PowerInput`. `tools/validate_power_rule.mjs` fails on a consumer below its floor, or a stale or extra exemption. It cannot confirm the exact authored base of the four buildings above the floor (ChemicalWorks, DeepMine, Electrolysis, CryoLiquefaction), whose bases are generator literals.
- **Generators:** Coal 25,000, Oil 90,000 (fuel unchanged), Reactor 1,000,000 (still x (1 - heat)). Hydro: authored as `ratedHp` 40,000; the generator derives 833.33 hp per m3/s per layer of head (cap 3 m3/s x 16 layers, unchanged; was 200).
- **Descriptions** that state hp now take the generated value.
- **Acceptance code:**
  - `LategameAcceptance` reads the launch load from data.
  - `HospitalAcceptance` stacks two 10,000 hp test generators.
  - `HydroAcceptance` scales its band.
  - `HydroTurbine` compares rated to authored output within float precision.
- **Checks:** mirror `power`: `validate_all -SkipBlender` 54 pass, 1 report-only, 2 failures from other work (`map-setup-terrain`: unfinished map work; `no-game-assets`: outside git); compile.
- **Open:**
  - **Bulk acceptance runs:** closed 2026-10-30 (Cleanups entry). Each consumer's test generator is now sized from its `PowerInput`. The generators actually gave 5,000 hp each (native half strength), not 10,000.
  - **Not updated:** the old balance workbook (`Timberborn_Deep_Frontier_Balance_Workbook.xlsx`, already stale) and `capture_hydro*.py` (they check the recorded 9,600 hp runs).

## Drill bits for the Deep Drill and Deep Mine (Claude Code session, 2026-10-29, built by an agent; validated in mirror `drillbits` and the real repo; not built or run in game)

- **User:** concrete and steel need ongoing industrial uses (follow-up to the reactor casks and maintenance entry).
- **Rates:** Deep Drill 0.1 HighGradeSteel per full-crew hour (DrillBits); Deep Mine 0.1 HighGradeSteel + 0.1 Concrete (ShaftLining). Stock 15 of each. Use scales with actual recipe progress, so a partial crew or low power uses less and an idle building none.
- **Mechanism:** `FrontierWorkplaceUpkeepSpec` (from `tools/workforce_risks.json` `workplaceUpkeep`, written by `bot_upkeep_content.mjs`) and the `WorkplaceUpkeep` component (`Scripts/Workforce/WorkplaceUpkeep.cs`).
  - The goods join the native Manufactory inventory through the existing bot-maintenance prefix and Moddable Recipes postfix (the stock class is renamed `ManufactoryExtraStock`), so each building keeps one enabled inventory. No new Harmony patches.
  - Use follows `Manufactory.ProductionProgressed`. One unit is taken when the one in use wears through; the part left is saved.
  - A native `IManufactoryLimiter` sets efficiency 0 with nothing in use and none in stock, and caps progress to the unit in use. One status per missing good ("Waiting for drill bits", "Waiting for shaft lining"). The panel has an Upkeep section.
- **Item uses:** HighGradeSteel 33 → 35, Concrete 72 → 73.
- **Checks:** mirror `drillbits`: `validate_all -SkipBlender` 52 pass + 1 report-only (`no-game-assets` outside git); real repo: bot upkeep, single inventory, enable guard, slice content, compile.
- **In game:** deliveries up to 15 with and without bots; the stop, status and resume; timed use at full and partial crew; the panel; the part unit across save/load; older saves; bot oils still stocked after Moddable Recipes rebuilds the inventory. Closed 2026-10-30 (Cleanups entry): the building descriptions now state the upkeep, generated from `workplaceUpkeep`.

## Reactor Bots: in-place bot upgrade and Reactor Charging Bay (Claude Code session, 2026-10-29, built by an agent; integrated and validated in mirror `integ`; not built or run in game)

- **User:** super bots as an upgrade of the ordinary bot (same name, still a bot, big buffs, a different skin). They need steel, fuel rods and coolant, plus their own 5,000 hp charging stations. Design: `scratchpad/super-bots-design.md`.
- **Mechanism:** a saved `ReactorBot` component on every bot (Ordinary / Queued / Reactor); no second template, since the native bot factory takes one BotSpec. The panel's "Retrofit" button switches on two hidden needs, so the bot fetches 1 ReinforcedBotFrame and 1 ReactorPowerCell from storage, the way bots take Grease, then upgrades.
- **Buffs:**
  - **Carry ×5:** the native carry bonus.
  - **Speed ×4:** a small patch; the native bonus caps at ×2.
  - **Wear ÷10:** a patch, so the bot lives 700 days.
  - **Charge:** its own `ReactorCharge` need at a quarter of Energy's rate, with Energy off on Reactor Bots and the new needs off on ordinary bots, so each kind of bot uses only its own station.
  - **Skin:** amber illumination and a gunmetal tint, except on colour-named bots.
- **Upkeep per day:** coolant 1 ReactorCoolantWater or 0.5 Cryocoolant (critical); plating 0.2 HighGradeSteel or 0.1 Alloy (without it, wear ×5). The bay burns about 0.2 EnrichedFuel per charging hour.
- **Parts:**
  - ReinforcedBotFrame at the Precision Machine Works: 8 HGS, 4 Alloy, 1 MachineCore, 1 BotChassis, 8 h.
  - ReactorPowerCell at the Uranium Processing Plant: 1 EnrichedFuel, 2 PowerModule, 2 Electronics, 2 Cryocoolant, 6 h.
- **ReactorChargingBay:** 3×2×3, two cradles, 5,000 hp, no workers, 250,000 science, Science tool group. T5 cost plus a gate of 2 ReinforcedBotFrame and 2 ReactorPowerCell. Model is 2,772 triangles.
- **Files:**
  - `tools/super_bots.json`, `super_bot_content.mjs`, `validate_super_bots.mjs`, `Scripts/SuperBots/*`, `lategame_ReactorChargingBay.py`.
  - Shared-file entries: batches, costs, generation hook after bot upkeep, automation, sounds, exporter slots, triangle budget, roof decks, asset catalog, and the restaurant validator's need list.
- **Saves:** ordinary bots gain five switched-off needs. Without the mod, Reactor Bots load as ordinary bots.
- **Checks:** mirror `integ`: promote, generation, `validate_all -SkipBlender` 52 pass + 1 report-only (`no-game-assets` outside git), compile.
- **In game:**
  - the retrofit errand, and whether the need switches survive save/load;
  - ×4 movement on stairs and in water, and the leg cadence (animation speed is per template, so legs run 4× fast);
  - wear;
  - only Reactor Bots charging at the bay, two at once, and the bay stopping without fuel;
  - coolant and plating pick-ups;
  - the skin.

## Deep Well and steel structures (Claude Code session, 2026-10-29, built by two agents; integrated and validated in mirror `integ`; not built or run in game)

- **Deep Well (user request: the map runs dry; boost sources, seeps flow, drought-proof, optional tide shut-off).** Files: `tools/deep_well_content.{json,mjs}`, `validate_deep_well_content.mjs`, `Scripts/DeepWell/DeepWell.cs` and `DeepWellPanel.cs`, `lategame_DeepWell.py`; design `scratchpad/deep-well-design.md`.
  - **Footprint:** 1×2×5, a cantilever with no vanilla patch. The anchor cell stands on ground, seep or badwater-source cells; the drill cell hangs (`Any`) over the source.
  - **Why the cantilever:** a 1×1 clean source is not stackable and fills its cell, so nothing can stand on it.
  - **Placement:** a custom validator through the official extension point runs on previews only and gives three reasons.
  - **Boost:** 1 + (boost − 1) × power efficiency, within the native cap of 8 per source cell. Power is 1,667 hp per boost step, 10,000 at 6×.
  - **While running:** a seep loses its `WaterDepthStrengthModifier` limit, and the source keeps flowing through drought (vanilla and Moddable Weathers).
  - **Tide checkbox:** blocks the source completely.
  - **Drill bits:** 0.05 HighGradeSteel per hour per boost step, stock 15, hauler-delivered with no workplace.
  - **Waterproof**, with the native no-flood access setting.
  - **Cost:** T4 at 30,000 science, plus a gate (MetalBlock 200, Gear 150, HighGradeSteel 60, MachineCore 10, DeepAlloy 15, Concrete 40).
  - **Model:** 2,912 triangles.
  - **Not done:** it does not wake a map source that hasn't started flowing yet.
- **Steel structures (first slice of `scratchpad/platforms-design.md`).** 15 pieces in a new "Steel structures" sub-group under Paths:
  - `SteelCantilever10x1/12x1/15x1` (1, 2 and 3 anchors; every overhang now declares `anchors`);
  - `SteelBridge8x1/10x1/12x1/15x1` (vanilla suspension-bridge pattern; gaps of exactly that length);
  - `SteelColumnH1`–`H6` (stackable caps);
  - `SteelDeck3x3/5x5` (corner support only).

  Models are 340–2,724 triangles; scenes are unpacked. Base costs were halved once the ×2..×8 tier factor landed, e.g. 15-tile cantilever 360 HighGradeSteel + 486 Concrete, 5×5 deck 450 + 420.
- **Checks:** mirror `integ` with the super-bot work excluded:
  - promote (12 checks), canonical generation, workbooks;
  - `validate_all -SkipBlender` 51 pass + 1 report-only (`no-game-assets` cannot run outside git; it runs at commit);
  - compile.
- **In game:**
  - **Deep Well:** placement messages on and off a source, save/reload, the boost readout, seeps in deep water, drought, the tide checkbox, steel deliveries (also in deep water) and the slider's power draw.
  - **Steel pieces:** rotations, flips, deletion when support is removed, beavers crossing 15-tile bridges, decks on uneven columns, and drag-preview cost.

## Hauling radioactive goods can irradiate beavers (Claude Code session, 2026-10-29; generated and validated in mirror `costs`; not built or run in game)

- **User request:** a small chance that a beaver hauling radioactive materials is irradiated and needs the hospital.
- **Rates:** `RadiationExposure` rolls each tick, while the beaver carries a good (native `GoodCarrier`) and is not already irradiated, with `1 - exp(-rate * hours)` on the native `IRandomNumberGenerator`. Rates come from `RadiationTuning.HaulingIrradiationRate`: RadioactiveWaste and RadioactiveSludge 2% per carrying hour, ContaminatedWater 0.5%.
- **On a hit:** the dose is set to 1, so the usual irradiation, hospital course and sickness clock follow. A notification names the beaver and the good (`DeepFrontier.Radiation.Notification.HaulingIrradiated`). Bots carry no `RadiationExposure` and are immune.
- **Checks:** mirror (other agents' files at HEAD): generation, `validate_all -SkipBlender` 50 pass + 1 report-only (`no-game-assets` outside git), compile. **In game:** the notification and rate feel.

## Reactor consumes steel and concrete: casks and maintenance repairs (Claude Code session, 2026-10-29; generated and validated in mirror `costs`; not built or run in game)

- **User:** building materials need ongoing industrial uses. Chosen: reactor casks, drill bits, maintenance stops.
- **Casks:** `NuclearWaste` now takes 6 ReactorCoolantWater + 1 HighGradeSteel + 2 Concrete per 2 h cycle.
- **Maintenance:** `ReactorMeltdownSpec.MaintenanceGoods` (`ImmutableArray<GoodAmountSpec>`) = 20 HighGradeSteel + 40 Concrete, consumed from the reactor inventory when a 24-hour stop completes. Without them the stop waits, and a "waiting for repair materials" status shows. `ReactorCore` requires each maintenance good to be an ingredient of every reactor recipe with room for its amount; the panel lists the materials.
- **Drill bits:** the Deep Well's High-Grade Steel bits are in that agent's work. The Deep Drill and Deep Mine run 2-minute cycles, so integer recipe ingredients cannot express a small per-hour bit use; they need an upkeep inventory like BotMaintenance. Not done.
- **Checks:** mirror `costs` (other agents' files at HEAD): generation, `validate_meltdown_content`, `validate_all -SkipBlender` 50 pass + 1 report-only (`no-game-assets` cannot run outside git), compile.

## Heavy construction costs: x2 to x8 by science tier (Claude Code session, 2026-10-29; generated and validated in mirror `costs`; not built or run in game)

- **User:** the whole building set was far too cheap next to the vanilla wonders (Earth Repopulator 5,500 goods; the reactor was 1,620). Chosen: "Heavy x2 to x8".
- **Rule:** each `lategameRule.tiers` entry in `building_construction_costs.json` has a `costFactor`:

  | Tier | Science unlock | Factor |
  |---|---|---|
  | T1 | ≤600 | 2 |
  | T2 | ≤3,000 | 3 |
  | T3 | ≤8,000 | 4 |
  | T4 | ≤30,000 | 6 |
  | T5 | above | 8 |

  `lategame_costs.mjs` applies it to the late-game foundation and superstructure; gates (the reactor's 20 EnrichedFuel and 100 extra HighGradeSteel) are added unscaled. Every other authored cost goes through the new `scaledCost(cost, science)` at its write site:
  - `create_frontier_expansion_content.mjs` authoredCost (catalog rows for FishHatchery, FisheryWorks, Restaurant; Hospital; GroceryStore);
  - the hospital, grocery, hydro, research and structural generators;
  - construction materials.
- **Results (goods):** NuclearReactor 1,620 -> 12,085; LaunchPad 605 -> 4,855; UraniumProcessingPlant 530 -> 4,250; RadioactiveWasteRefinery 475 -> 3,775; Hospital 310 -> 1,860; DeepDrill 315 -> 940; ConcreteBlock 5 -> 15.
- **Checks:** mirror `costs` (the steel agent's in-progress files reset to HEAD there): generation, `validate_all -SkipBlender` 50 pass + 1 report-only (`no-game-assets` cannot run outside git). Generated Data copied into the repository. Not built.

## Simpler radioactive waste chain (Claude Code session, 2026-10-29; generated and statically checked; not built or run in game)

- **User:** the waste chain was too complex to manage; casks should be mixed with water into the tide's radioactive fluid and shipped off the map. Approved plan:
  - **Export dissolves casks:** the Radioactive Waste Export gains `ExportRadioactiveWaste` (2 RadioactiveWaste + 8 Water per hour, no product; `radiation_content.mjs`), so one building disposes of casks, radioactive water and contaminated water.
  - **Refinery without Chemical:** `WasteRefining` and `ContaminatedWaterRefining` no longer take Chemical. `Vitrification` is removed (recipe, refinery list, stale Data file; a saved refinery on it loads with no recipe, native `Manufactory.Load`).
  - **Rename:** `RadioactiveSludge` keeps its id and is shown as "Radioactive Water"; the Outfall and Recovery Pump are renamed "Radioactive Water Outfall" and "Radioactive Water Recovery Pump"; meltdown and leak texts follow. Fuel Reprocessing is unchanged.
- **Minerals retired, badwater filtering (user, same day):**
  - **Minerals:** waste refining no longer yields RecoveredMinerals and `SludgeMineralRecovery` is removed. The good is legacy save-only (`content_policy.json`).
  - **Reactor gate:** 20 EnrichedFuel + 100 extra HighGradeSteel. `lategame_costs.mjs` now lets a gate add to a rule good.
  - **Badwater:** the refinery gains `BadwaterFiltering` (10 Badwater + 1 FilterMedia → 8 Water, 2 h). Filter Media was the least-used candidate input.
- **Item-use audit:** a recipe with no product, science or launch counts as "Disposal". RadioactiveSludge is a single-use exception. 0 of 55 goods flagged (releaseReady).
- **Checks:** generation, `validate_all -SkipBlender` 51 pass + 1 report-only. Docs: `docs/progression.md` waste rows, CHANGELOG, Workshop change notes and description.

## Reactor heat rework: power falls with heat, symmetric cooling, full waste heats the core (Claude Code session, 2026-10-29; generated, compiled and statically checked; not built or run in game)

- **User direction:** output should fall as the core heats; it should cool as slowly as it heated, so a reactor short of water more than half the time (even with water 45% of the time) eventually melts down; full radioactive waste or sludge should heat it like missing coolant for as long as it stays full.
- **Runtime (`Meltdown/ReactorCore.cs`):** an uncooled core (coolant dry while running or holding heat, or waste full: no unreserved room for one more cycle of a recipe product) heats `HeatPerFaultPerHour` 2.5%/h whether running, idle or SCRAMmed; otherwise it cools `CoolingPerHour` 2.5%/h (pause: cold shutdown at the same rate). Crew and maintenance faults heat only below `FaultHeatLimit` 85%. Automatic SCRAM and auto-restart are removed (an automatic SCRAM stopped coolant use, refilled the stock and rescued a reactor at 45% supply); manual SCRAM and restart at 40% remain. Saved automatic SCRAMs load as running; old `AutoRestart`/`LastRunDay` keys are ignored.
- **Output:** new `IGeneratorOutputFactor` in `WorkshopPoweredGenerator.cs`; the reactor returns `1 - heat` (0 under SCRAM), multiplied into the native output multiplier. Coolant use per cycle is unchanged, so a hot reactor does not need less water.
- **Spec:** `RunningCoolingPerHour`, `ShutdownCoolingPerHour`, `DecayHeatHours`, `DecayHeatPerHour`, `ScramHeat` replaced by `CoolingPerHour` and `FaultHeatLimit` (`meltdown_content.mjs`, `MeltdownSpecs.cs`); `validate_meltdown_content.mjs` asserts cooling equals heating and that the generator applies the factor.
- **UI:** new waste-full priority status, notification and cause; panel shows output (% and hp), waste and sludge stock against capacity, the uncooled causes, time to meltdown, to the 85% limit or to cold. Tooltip, rules and `docs/meltdown.md` rewritten.
- **Checks:** generation, `validate_meltdown_content`, `validate_priority_statuses`, `validate_all -SkipBlender` 51 pass + 1 report-only, compile. Not built (the game was running). **In game:** output falling with heat, waste-full heating, notifications, an old save with a SCRAMmed reactor.

## Triangle targets halved: 43 building models lighter, 906k -> 632k finished triangles (Claude Code session, 2026-10-29; build 213 installed and verified, 659 hashes; not yet looked at in game)

- **Targets:** grand 40,000 -> 20,000, workshop 20,000 -> 12,000 (user approval; `validate_triangle_budget.py` TARGETS). Ceilings re-recorded for all 76 models; none is above its target and no model went up.
- **Late-game (32 models, shared `lategame_kit.py`):** NuclearReactor 36,338 -> 19,536, UraniumProcessingPlant 36,042 -> 19,684, ChemicalWorks 30,492 -> 19,004, ElectrolysisPlant 27,446 -> 18,978, WaterTreatmentPlant 26,060 -> 18,502, LaunchPad 25,232 -> 18,269; every other late-game model also lighter. 12-sided default in multiples of 4, solid flange discs, four-sided bolt heads, sparser grating and rungs, single-bar ladder hoops; the uranium acid tanks and scrubber ladders lost their cages. Bevels now only on edges at least 1.0 long between faces at least 0.25 deep (`render_lategame_studies.py`).
- **Industrial (`industrial_kit.py` `lean_*`, `LEAN_MODELS`):** CementKiln 34,620 -> 11,930, Sandstone/LimestoneQuarry 29,953 -> 11,784, ConcreteMixer 24,478 -> 9,857, StoneCrusher 23,706 -> 8,817. Fewer stones in bins and hoppers, fewer rope turns, no lamp undersides.
- **Shell-built:** FisheryWorks 37,467 -> 18,129, Restaurant 25,934 -> 19,846 (all seating kept), Hospital 24,176 -> 18,222, MaterialsLaboratory 31,695 -> 18,938, GroceryStore 30,101 -> 19,620, ReinforcedHydroTurbine 22,029 -> 12,459. No fastener heads, plain collars, wider roof sheets, half-triangle stock items. Review archive `docs/art/reviews/2026-10-29-triangle-budget-20k/`.
- **Registrations:** occupied cells, doors, wall faces, smoke emitters, animated nodes, slots and static-merge nodes are unchanged for every model. Connection faces: none lost anywhere (removed details that had made faces non-flat or covered roof cells were restored where a face or roof cell would have changed: industrial nuts and wall courses, reactor lead bands and gallery, Fertilizer silo hoops, uranium tank bands, DeepProcessor tanks). The smaller late-game bevels make some surfaces flat, so 17 late-game models offer new shaft and pipe faces (reactor 120, 1-10 elsewhere) under the 2026-10-23 every-flat-surface rule; `roof_decks.json` gains platformable cells only (Greenhouse +1, MissionControl +3, NuclearReactor +2, SteelMill +2).
- **Checks:** strict z-fight audits, hidden-geometry audit, door culling, motion and registration comparisons per family in scratch mirrors; canonical generation, `validate_all -SkipBlender` 51 pass + 1 report-only, compile checks, build 213 verified.
- **Pipeline note:** the late-game regeneration saved its 32 scenes with the game textures packed (68 MB each); they were unpacked with `unpack_blend_textures.py` + `normalize_blend_image_paths.py` before commit (22 MB in all). Run both after any late-game scene regeneration.
- **To see in game:** the 43 lighter models up close; whether load memory and frame time drop on the user's big save (`start_frame_profile.ps1`).

## Performance on the user's big save: power-network split patch, frame profiler, measurements (Claude Code session, 2026-10-29; build 212 installed and verified, 659 hashes)

- **User report:** loads of 200+ s, low frame rate, and a freeze while placing buildings on a large map (87 mods, including All Buildings Transfer Power, which makes every building a power shaft).
- **Native O(n^2) found and patched:** `MechanicalGraphReorganizer.VisitConnectedNodes` (1.1.2.8) runs `Transputs.Select(ConnectedNode).Intersect(_oldGraphNodes)` for every node of a network being split, and LINQ Intersect copies the whole unvisited set each time. Every node leaving a network (delete, pause, block, flood, automation Off) split it in time quadratic in its size. `Scripts/Performance/PowerGraphReorganizer.cs` replaces it with the equivalent direct set lookups (type IL digest pinned; throws at mod start on a changed game). Loaded in build 212 ("Power network split patch applied"); the split itself is not yet timed in game.
- **Tools:** `Scripts/Performance/FrameProfileProbe.cs` + `tools/start_frame_profile.ps1` (load a Memory Test save copy, speed 3, 20 s warm-up, 60 s of frames; native `-metrics` per-system tick report; frames csv). The native benchmark cannot be used: ModManagerScenePanel ignores every mod when `-benchmarkLength` is given.
- **Measured (copy of the user's Day 30-7 autosave, build 211/212):**
  - Placement previews (`start_preview_cost.ps1`, ms per frame, native -> shipped caches): Reactor 1,303 -> 13.7 still, 32.5 moving, hitch up to 478 when the mouse rests (deferred native preview navmesh, 224 ms); Steel Mill 217 -> 4.5 / 23 / 98; vanilla Smelter 6.9 -> 1.3.
  - Frames at speed 3 (`start_frame_profile.ps1`): 41 fps without the two unfocused-window frames, median 20.8 ms, p95 41.7, regular ~49 ms frames. Metered ticks are 3.65 s of the 60 s (under 10% of frame time); Deep Frontier systems about a third of that (RadiationSimulation 16.7%, RadiationRenderer 9.8%, HydroTurbineSimulation 2.8%, RadiationExposure 1.3%, smog about 1%). The rest of the frame is rendering and unmetered per-frame work.
  - Memory: 12.5-13.1 GB private, about 9 GB working set, on a 16 GB laptop (i7-8750H, RTX 2060 6 GB, rendering on the NVIDIA GPU).
- **Test-run hazard handled:** the Memory Test folder was backed up first; the two autosaves the probes rotated out were restored with their timestamps and the probe files removed.

## Waste storage cannot be deleted while it holds waste (Claude Code session, 2026-10-29; compiled and statically checked; not run in game)

- User request: deleting a warehouse or tank full of radioactive waste, sludge or contaminated water threw the byproducts away. `HazardousStorageDeletionBlocker` (Scripts/Radiation/RadiationStorage.cs), decorated on every native Stockpile, is a native IBlockObjectDeletionBlocker (FixedStockpileDeletionBlocker pattern): while the enabled inventory holds RadioactiveWaste, RadioactiveSludge or ContaminatedWater, BlockObject.CanDelete is false (panel delete button off, reason "DeepFrontier.Radiation.DeletionBlocker.HazardousStock") and the deconstruction tool skips it. Emptying it (native Empty storage, or selecting another good) lifts the block. Production buildings are not blocked (their inputs cannot be emptied). ContaminatedWater was already selectable in tank pickers (user confirmed). In-game check pending.

## Steeper late-game science, 800,000 hp reactor, per-profession school supplies, stronger smog scrubber (Claude Code session, 2026-10-29; generated, compiled and statically checked; not built or run in game)

- **Science curve (user request):** above the 12,000 Materials Laboratory the unlocks climb to the reactor: Mission Control 30,000, Rocket Assembly Hangar 50,000, Launch Pad 80,000, Uranium Processing Plant / Waste Vault / sludge export, outfall and recovery pump 200,000, Waste Refinery 500,000, reactor 1,000,000. The laboratory, its build chain and the producers of its recipe inputs are unchanged; the Hospital stays at 25,000 (needed before radioactive tides). Tier T4 widened to 30,000 so Mission Control keeps its cost. Table in docs/progression.md (Science curve).
- **Reactor:** 750,000 -> 800,000 hp (MechanicalNodeSpec.PowerOutput, description, validate_vertical_slice_content).
- **Technical School supplies (user: "just gears and rations is too easy"):** each profession now uses the goods of its retired staffed course, per hour while anyone studies it: Metallurgy 1.5 Metal Block, 0.75 Deep Alloy, 0.75 Corn Ration; Reactor 0.4 Electronics, 0.2 Yellowcake, 0.4 Medicine; Flight 0.5 Electronics, 0.25 Recovered Telemetry, 0.5 Packaged Food (the course's goods per graduate at six of twelve seats). The template's GoodConsumingBuildingSpec lists every profession's goods; SpecialistSchool gives its native GoodConsumingBuilding a copy with only the taught profession's goods (private `_goodConsumingBuildingSpec` and `_suppliesLeft`, resolved at load) and is the inventory's IGoodDisallower, added by the new SchoolSupplyInventory prefix on GoodConsumingBuildingInventoryInitializer.Initialize, so haulers bring only the taught profession's goods. In-game check pending: deliveries switch with the Teach buttons, students are turned away without supplies, save/reload keeps the partial supply.
- **Smog Scrubber (user request):** radius 7 -> 20 tiles, removal 75% -> 100%, ScrubberMaxReduction 0.9 -> 1, so the air within 20 tiles of a running scrubber is clean.
- validate_all: 51 pass + 1 report-only; the four compile-check projects build. Not built: the game was running.

## Dependency-only test profile; toolbar sub-groups; build 208 (Claude Code session, 2026-10-28)

- **Dependencies (user request: run with only the manifest's mods):** the game's mod switches are Unity PlayerPrefs `ModEnabled.<DisplaySource>.<OriginName>.<Id>` (native ModPlayerPrefsHelper; a missing key means enabled; value names end in Unity's `_h<djb2-xor>` hash). Set Deep Frontier + its 17 RequiredMods on and the other 67 installed mods off (registry backup kept). Static closure: every required mod's own RequiredMods are in our list. In game (build 207, Memory Test save): loaded in 78 s, every Deep Frontier patch applied; the only errors were 201 skipped buildings of disabled mods (TubewayLevee 178, Bob's/More Platforms side platforms 23, a Bob Storage warehouse).
- **Log noise found (open):** the six retired goods kept for old saves (Gas, Methane, Radon, SulfurGas, ToxicFumes, DiningService) have no localization; `ModdableWeatherSpecs/RadioactiveTideWeather.blueprint.json` logs "No type found for key ModdableWeatherSpec" when the optional Moddable Weathers is off. Others' noise: Expanded Storage's enUS.csv columns, Redic.NewStyles names.
- **Toolbar sub-groups (user: group our buildings better):** `tools/tool_groups.json` + `tool_group_content.mjs` (end of generation) + `validate_tool_groups.mjs`: nine Moddable Tool Groups sub-groups (BlockObjectToolGroupSpec + ParentToolGroupSpec, icon from a member building) inside Metal (deep mining, quarries and cement, heavy industry, nuclear fuel, rocketry incl. Mission Control), Paths (concrete scaffolds, concrete side platforms), Water (radioactive waste) and Wellbeing (civic services); 41 buildings moved. `validate_radiation_content.mjs` checks tool-order uniqueness per group.
- **Build 208** (school rework + sub-groups): Official Mod Builder in 142 s, verify 659 hashes match. In-game check of the groups and the school pending.

## Technical School: free-time study for every beaver, several professions each (generated, compiled and statically checked; not built or run in game) (Claude Code session, 2026-10-28)

- **User:** beavers should enrol and learn by themselves, every beaver should try to become educated, and a beaver can learn every profession (e.g. with three schools). Chosen with the user: free-time study, goods per study hour, one profession per school picked by the player.
- **No staff:** staff would work the shift during which the students are at work, so a staffed class would rarely meet its students. The school is a native goods-consuming attraction (vanilla Detailer pattern): `GoodConsumingBuildingSpec` (supplies Gear 0.1/h and CornRation 0.2/h, the same for every profession, since the native spec has one supply list) + `GoodConsumingAttractionSpec` + `AttractionSpec`. The producer drops the cloned Inventor workshop specs (`SCHOOL_WORKSHOP_SPECS`); training recipes are gone.
- **Study needs:** `StudyMetallurgy`, `StudyNuclear`, `StudyFlight` (from vanilla Need.Beaver.Books, SocialLife group, 0.5 points/h, -1/day, +1 wellbeing), appended to the Iron Teeth need collection. The school's AttractionSpec lists all three; `SpecialistSchool` keeps only the taught one in native `Attraction.Effects` (reflection; it re-registers with the district's `DistrictNeedBehaviorService`), so the native AI sends only beavers whose study need for that profession is low. `SpecialistStudyNeeds` keeps every held profession's need full, so a beaver never visits a school teaching what it knows.
- **Learning:** each hour inside a usable school (supplies, power, not paused) adds a study hour; 16 h Metallurgy, 24 h Flight, 32 h Nuclear make a graduate. `SpecialistTrait` holds a list of disciplines and per-discipline study hours (legacy single `Discipline` saves load into the list; old course hours are dropped). Specialist workplaces accept any beaver holding their discipline.
- **Panel:** "Teach <profession>" buttons, students inside, adults in the district still to learn it, colony specialists; the beaver panel lists held professions and study progress. Status "Choose a profession" until one is picked.
- **Saves:** a school saved as a staffed workshop loads with empty supplies (`PowerPlantSaveMigration` covers `TechnicalSchool.IronTeeth`); its workers' references to the removed workplace are dropped natively (as for the coal and oil plants in build 193).
- **Build:** `build_deep_frontier.ps1` now passes `-disable-assembly-updater` without names. On a fresh project, Unity's single-threaded API updater spent over 30 minutes on the 518 game assemblies; with it disabled, a fresh clone built and installed in 16 minutes and verified (650 hashes match).
- **Verified:** content generation, validate_all 50 pass + 1 report-only, all 4 compile checks, editor guards, 4 maps. **Not verified:** the in-game AI (whether beavers visit, how fast they graduate, beavers shown inside), supply use and the save migration on a real save.

## Fresh-clone setup verified; Workshop required items; user screenshots (Claude Code session, 2026-10-28)

- **Fresh clone** (`git clone` of the commit into `%USERPROFILE%\dfs\freshclone`, then `python tools/setup_dev.py`): setup, content generation (Data identical to the commit), all 51 checks (50 pass + 1 report-only) and the Blender scenes (116 scenes, 3,188 images, none missing or outside the clone) pass. Fixed on the way:
  - setup found npm only on PATH (now beside the chosen node first);
  - Unity's first open of the modding project fails its script compile until the game assemblies are imported; setup now checks the resolved Mono.Cecil package instead of the exit code, then runs the bootstrap (whose Mono.Cecil path was fixed to this machine's package hash);
  - setup installs ILSpy's ilspycmd 9.1.0.7988 into `tools/dotnet` (API validators);
  - setup extracts the native preview models (`read_native_civic_models.py`, `extract_native_models.py --registered`) and the extraction scripts create their output folders;
  - three vanilla blueprints (`Good.MetalPart`, `RuinColumnH1`, `UndergroundRuins`) start with a UTF-8 BOM as the game ships them (the old vendor copies had lost it); their readers now decode it;
  - `validate_cryogenic_content.mjs` reads the ModsBuild folder from the dev environment;
  - Windows PowerShell scripts need `-ExecutionPolicy Bypass` (README).
- **Fresh-clone Unity build:** the first build of a new project spends a long time in Unity's single-threaded API updater over the 518 imported game assemblies (see the next entry for the result).
- **Workshop required items:** `tools/workshop_dependencies.py` maps manifest `RequiredMods` to Workshop items through the subscribed copies (17/17) and, with `--apply`, adds them to the uploaded item with ISteamUGC::AddDependency through the game's Steam library. Steam API init and interface lookup verified; AddDependency not yet run (the mod is not uploaded).
- **Screenshots:** `workshop/screenshots` now holds the user's 11 named in-game screenshots (JPEG); the README shows them.

## Public-repository preparation: dev-environment setup and game-asset guard, build 206 (Claude Code session, 2026-10-28)

- **Setup:** `python tools/setup_dev.py` (Windows, macOS, Linux) finds Timberborn in the Steam libraries (or `--game`), writes `tools/dev-environment.json` and `tools/compile-check/Directory.Build.props` (both untracked), installs UnityPy and sharp, clones the official modding project at cc50d47 and bootstraps it (Windows), extracts the local-only game references, and installs the pre-commit guard.
- **No machine paths in the build and check scripts:** generators, validators, build, stage, verify, launch and the compile checks read the dev environment. The acceptance and capture scripts still hold machine paths (noted in the README).
- **Game assets out of git:** `tools/check_no_game_assets.py` (validate_all check `no-game-assets`, pre-commit). The Blender scenes reference the extracted game textures by relative path (`Art/GameTextures`, list in `Art/GameTextures.json`); `normalize_blend_image_paths.py` made every image path relative and canonical (3,150 images; the flat DFArt*.png previews now use `Art/Textures/Packed`). Pinned scene hashes repinned by `repin_scene_hashes.py`.
- **Build 205 had failed** (bundle name collision between `DFArt*.mat` and stray `DFArt*.png` in the bundle folder); verify passed only because the old install remained. Removed the stray PNGs.
- **Verified:** regenerated Data identical to the commit; validate_all 50 pass + 1 report-only; 4 map variants OK; compile checks pass; build 206 "Official Mod Builder completed successfully", verify: 650 hashes match the installed package. Not run in game this pass.

## Flipped FishHatchery/FisheryWorks/Greenhouse: entrance and power reports on build 176 (generated and validated in mirror `flipentrance`; not promoted, built or run in game) (Claude Code session, 2026-10-26)

- **User (b176, save `ExperimentalSaves/leg/2026-10-26 15h11m, Day 20-4`):** the FishHatchery and FisheryWorks entrances still don't work; Greenhouse and hatchery headhouse walls don't take power. All three are flipped there.
- **Entrances: the save, not the buildings.**
  - Native entrances in the save: FisheryWorks (131,169,3) and FishHatchery (138,162,3). Both carry the user's Path.
  - That path is one 19-cell cluster (x131-138, y162-169). Its nearest other path is 17 cells away, at y=145, across the crop fields. The district centre is at (131,138).
  - Native `UnconnectedBuildingStatus` shows whenever `DistrictBuilding.InstantDistrict` is null. That needs the access on the district road, so both buildings show "not connected" whatever their blueprint.
  - Flip does not affect entrances. `PositionedEntrance`, the doorstep, the navmesh edges and the entrance flags all go through the flip-aware `Blocks.Transform`. Source facts; the in-game check is open.
- **Hatchery height: no fault.** `BlockObject.Save` writes `Coordinates + BaseZ`, so the save's z=3 is origin z=2 with layer 1 on the bank (z=3). The user's paths and solar panels are consistent only with that height.
- **Power, root cause 1 (source):** FishHatchery and Greenhouse (from the unpowered HydroponicGarden), and DeepDrill and DeepMine (EfficientMine), had no `MechanicalConnectorTargetSpec`.
  - A shaft joined their graph, but no gear socket was ever drawn on the wall.
  - All 24 vanilla Iron Teeth consumers with transputs have the spec.
  - In the save, the flipped Greenhouse is powered by 3 solar panels on its back-wall transputs (production progressed), so the graph join works when flipped.
  - Fixed in `create_frontier_expansion_content.mjs` (`makeBuilding`, power added to an unpowered template) and `create_vertical_slice_content.mjs` (DeepDrill, DeepMine).
- **Power, root cause 2 (source):** 20 transputs pointed into the building's own cells, where nothing can carry a shaft or valve: the block below is a non-stackable part a Platform cannot share. The same faces had pipe ports.
  - FisheryWorks had 8 of them (beside and behind its walkway), Hospital 11 and Restaurant 1.
  - Fixed by `connection_content.mjs` rule 2a (`supportedInside`): going down, platforms must reach a stackable building block or the ground.
  - FishHatchery and Greenhouse were unaffected.
- **Checks added:**
  - `validate_connection_faces.mjs`: consumers need `MechanicalConnectorTargetSpec` (vanilla evidence re-read: 24/24), and every face into an own cell must be supportable.
  - Against the current src it reports the 4 missing sockets and the 20 unsupported faces.
  - `AllBuildingsAcceptance` adds "power socket shown".
  - New `Scripts/FlipPlacementProbe.cs` (`tools/start_flip_probe.ps1`): the three buildings × 4 rotations × flip, the hatchery on a carved, watered bank. It checks:
    - the native cursor pick with Paths and a SolarPanel nearby;
    - the native preview;
    - entrance Path, path connection toward the door, district, no Unconnected status, access;
    - every horizontal and Top face: platforms, native PowerShaft preview, graph join, socket;
    - a beaver walk.
  - New read-only `Scripts/SaveInspectionProbe.cs` (`start_memory_load.ps1 -SaveInspect`) for a save copy.
- **Mirror results:**
  - Generation changes only these 7 blueprints: the connector spec on 4, faces removed on FisheryWorks, Hospital and Restaurant.
  - Scripts compile with 0 errors (`outputs/contamination-consumers-compile`).
  - `validate_all -SkipBlender`: 49 pass, 1 report-only.
- **Side effect:** one validator run in the real repo rewrote `outputs/connection-faces-report.json`. Same data, plus the new `vanillaConsumersWithSocket` field.
- **Build 177 runs (fixes promoted; ran without dialog clicks):**
  - **SaveInspect** on `Memory Test/leg Day 20-4 copy` (`outputs/save-inspect-leg_Day_20-4_copy.json`). Peak memory 11.1 GB; no exceptions in the log.
  - All three buildings: entrance Path present, `pathConnectsTowardDoor=True`, not blocked, access on the entrance.
  - FishHatchery and FisheryWorks: no district and the "isn't connected to any district center by paths" status. That is the isolated road.
  - Power: the hatchery is joined to 2 SolarPanels on its back wall, FisheryWorks to 3 on its east wall, the Greenhouse to 3 on its back wall. Sockets are shown at all eight joins (the new `MechanicalConnectorTargetSpec`).
  - The hatchery's saved origin z=2 is confirmed. It is blocked (`unblocked=False`), likely its pen-depth or contamination rule; not investigated.
  - `AreConnectedRoadInstant` toward the district centre's entrance cell is False even for the connected Greenhouse, so that field means nothing; trust `instantDistrict`.
  - **Flip probe `b177`:** FishHatchery Cw0 unflipped passed every check:
    - cursor pick at the bank level with Paths and SolarPanels nearby;
    - native preview and placement;
    - entrance Path connected toward the door, district, no Unconnected status, access;
    - 24/24 faces take a shaft (11 on platforms), join the graph and show the socket.
  - Then the probe aborted on its own bug: it employed a worker at a workplace the district had already staffed natively. Fixed in source: it now follows the native assignee. It compiles, but a rebuild is needed to rerun. Peak memory 9.25 GB.
  - Not run yet: the other 23 cases, and every beaver walk.

## Radioactive tide has its own weather-panel and banner art (build 176; generated and validated, not yet seen in game) (Claude Code session, 2026-10-26)

- User: the tide banner should not look like badtide colours. With Moddable Weathers (installed) the spec pointed at the native badtide sprites, and the vanilla path tinted the native wet art.
- `tools/radioactive_tide_content.mjs` now writes `Sprites/Weather/RadioactiveTideProgress.png` and `RadioactiveTideNotification.png`. They are the native badtide wave art (`outputs/vanilla-icons`) recoloured, which keeps the tide's wave look: saturated warm pixels go orange to lime and red to deep green, while the gold frame and the white mist are untouched. Review sheet: `outputs/radioactive-tide-icons/radioactive-tide-banner.png`.
- `RadioactiveTideTuning.ProgressSpritePath` and `NotificationSpritePath` are used by `RadioactiveTideUi` (untinted; `HazardTint` removed) and by the Moddable Weathers spec. The stripes and the start sound stay the badtide ones.
- `validate_radioactive_tide_content.mjs`: checks native size, sidecar, a byte-identical re-render, and that both paths use the tide's own art.
- All-buildings b175: 74/79, with 5 test-harness failures, fixed in source (see the b175 entry). The map-loop test has not been re-run since b174.

## Radiation and the Radioactive Tide in the buildings that react to contamination or weather: Weather Station tide mode, Sluice is Back! "Measures" choice, Stream Gauge readout; compiled, verified against the shipped DLLs in the game's Mono, validated in mirror `contamination`, not built or tested in game (Claude Code session, 2026-10-26)

- **Inventory (1.1.2.8 decompiled; installed mods from `outputs/timberborn_build174.log`).**
  - Read contamination: Contamination Sensor (extended earlier), Sluice is Back! 11.0.0 sluice (auto close above/below x%), Stream Gauge (display only, no automation output), `ContaminationBlockableBuilding` on every `IWaterNeedingBuilding` (Swimming Pool, Fish Hatchery: blocked above 5.5% badwater), `WaterInput` buildings (pumps, showers, badwater pumps; blocked by `RadiationIntakeGuard`), Compact Water Turbine (badwater only tints its water visual), Pump to Tank and Bobingabout AutomatedManufactory (badwater share of a `WaterInput`, behind the intake guard), Mechanical Filter Pump (turns a pump's badwater output into clean water; the intake guard stops the pump on radiation first).
  - Read the weather: Weather Station (Temperate/Drought/Badtide automation), `HazardousWeatherWaterSource` (map sources listing weather ids), underground water drills and Bobingabout's aquifer increaser (drought/badtide only; the tide keeps sources flowing by design), Weather Scientific Projects (any hazardous stage).
  - Not contamination or weather readers: Floodgates (signal-driven only), Depth and Flow Sensors, Timber Pipes (pipe "contamination" is fluid mixing), Configurable Pumps (badwater conversion rate), Water Extention and Water Extention PowerEdition (data only, no DLL).
  - Moddable Weathers 11.0.0 does not patch the Weather Station; its `GameDroughtWeather`/`GameBadtideWeather` are not the native classes the station tests with `is`, so with Moddable Weathers the native Drought and Badtide modes never signal (source-confirmed; not changed).
- **Weather Station (`Scripts/WeatherStations`).** A fourth native radio button "Radioactive tide" in the native panel. The decorator `WeatherStationRadioactiveTide` holds and saves the choice (`DeepFrontier.WeatherStationRadioactiveTide`; absent key = native station); the native `Mode` keeps the previous native choice. Prefix on `Sample()` samples `CurrentCycleHazardousWeather.Id == RadioactiveTideWeather` from the station's own service; prefix on `UpdateOutputState()` sets `tide && native WithinActivationTimeHazardous` and skips the native switch only in tide mode (one `SetState` per update). Clicking a native mode button turns tide mode off. Works on the vanilla tide and on the Moddable Weathers tide (same id on the cycle's `IHazardousWeather`); the native early activation gives the advance warning.
- **Sluice is Back! (`Scripts/SluiceIsBack`, optional assembly `DeepFrontier.SluiceIsBack`).** "Measures: Badwater / Radiation / Any contamination" (the sensor's `SensedSubstance`, keys and texts). Postfix on the mod's private `Sluice.GetContamination()` (Math.Round(share, 2) like the mod); postfix on `SluiceState.SetState(neighbor, minLimit)` copies the choice to synchronized neighbours, new neighbours and copy-settings. Default Badwater (saved `DeepFrontier.SluiceContaminationSubstance`). Packaging like the Moddable Weathers bridge: staged `SluiceIsBack.dll` (+ `tools/unity/SluiceIsBack.dll.meta`), `-disable-assembly-updater`, `DeepFrontierBatchBuild.PackageOptionalAssembly` -> `Scripts/DeepFrontier.SluiceIsBack.dll.SluiceIsBack.optional`, checked by `verify_deep_frontier_package.ps1`; `SluiceIsBackBridgeConfigurator` throws when the mod is loaded without the bridge.
- **Stream Gauge (`Scripts/Sensors/StreamGaugeRadiationPanel.cs`).** "Radiation: x%" for the gauge cell under the native readout. No choice: the gauge compares nothing.
- **Not changed (decision needed):** Swimming Pool and Fish Hatchery stay open in radioactive water (native `ContaminationBlockableBuilding` reads badwater only); Weather Station Drought/Badtide under Moddable Weathers.
- **Shared code:** `Scripts/NativeIl.cs` (IL size, callees, string literals for start-up verification); `ContaminationSensorLoc` is now public (`tools/contamination_sensor_content.mjs` reads either visibility). No new localization rows (the sensor's rows and `DeepFrontier.Weather.RadioactiveTide` are reused); generation output in the mirror has the same `enUS.csv` as `src`.
- **Checks done:**
  - The Scripts tree, the Moddable Weathers bridge and the Sluice bridge compile (`outputs/contamination-consumers-compile`); the Sluice bridge also compiles against the shipped non-publicized game DLLs (public API only; its asmdef has no SkipVerification).
  - `outputs/contamination-consumers-harness` (game Mono 6.13, shipped 1.1.2.8 DLLs, installed Sluice is Back! 11.0.0, Harmony 2.4.1): `WeatherStationNative.Verify()` and `SluiceIsBackNative.Verify()` pass, all six Harmony patch classes apply, negative IL checks behave (`harness-result.txt`).
  - New `tools/validate_contamination_consumers.mjs` (`contamination_consumers`): native evidence (also `automation_content.json` `nativeTransmitterExtensions.WeatherStationSpec`), installed Sluice is Back! 11.0.0 members, extension rules, packaging, localization keys, the acceptance hooks. Three deliberate mutations were each caught.
  - Mirror `contamination`: canonical generation passes; `validate_all -SkipBlender`: 50 checks, 48 passed, 1 report-only, 1 failed: `exports-connection` (OilPowerPlant recorded curvedFaces differ from a fresh measurement), an export-geometry check this change does not touch.
- **All-buildings acceptance (`Scripts/AllBuildingsHazardProbes.cs`, hooks in `AllBuildingsAcceptance.cs`; compiled, not run).** After the last batch, on the emptied pad:
  - Sluice in a 1x4 pool sealed by `ReinforcedDamBlock`s with 0.4 clean + 0.4 radioactive water (r about 0.5), auto mode with the depth rule off: Badwater/close above 5% open; Radiation and Any/close above 5% closed; Radiation/close below r+0.1 closed and below r-0.1 open; Badwater/close below 5% closed. SKIP without Sluice is Back!.
  - Four Weather Stations (tide; tide + 72 h early activation; native Badtide; native Temperate). Dev "Deep Frontier: radioactive tide next cycle", then native dev "Jump to next season" (and native `SetTimeToNextDay` into the early window). Every stop is compared with the native weather state; explicit checks: the forced cycle holds the tide, advance warning, "signals while the radioactive tide is active", stops after the tide.
- **Not verified in game:** everything above at runtime (panel layout and the fourth radio button, outputs, saves, the optional DLL load, synchronization).

## All-buildings run b175 (build 175, 2026-10-26): 74/79 PASS, 5 failed checks, all in the test harness; harness fixed in source, not built

- 79 subjects: the 77 buildings plus the hazard probes' Sluice and WeatherStation, which both pass. Memory peak 10.57 GB. No uncaught exceptions; game closed.
- **Entrance fix verified in game:** FisheryWorks (entrance (152,133,3)) and FishHatchery ((121,79,3)) are reached by a plain path. District, access and the beaver going inside all pass. Greenhouse and Hatchery take shafts on their new faces.
- **Failures, all harness-side:**
  - "A beaver reached the building through its entrance" failed on Hospital, Restaurant and GroceryStore. Their workers work at stations, not inside the Enterable. The check now also accepts the worker coming within 1.5 of the access on the entrance.
  - "No inputs: LackOfResources" failed again on both quarries. The check now looks a second time after another native worker event (0.1 h later), and reports the native `ManufactoryInputChecker._inputUnavailable` and `HasAllIngredients` if it still fails.

## FisheryWorks and FishHatchery entrances take a player's ordinary path: sources fixed and generated in mirror `entrance`, not promoted, built or tested in game (Claude Code session, 2026-10-26)

- **User reports (build 174):**
  - "The FisheryWorks entryway doesn't connect correctly."
  - "The fish hatchery also looks like it is connected, but I get the icon saying the door is not connected."
- **Saves:** no save contains either building. The newest, `ExperimentalSaves/leg` (Day 19), has neither. The only saves with a FisheryWorks are the acceptance fixtures from 2026-10-19/20. So the cause comes from the blueprints and native code.
- **Cause:** both generators wrote the native `Entrance` on the door cell itself, the building's own block: FisheryWorks (3,0,0) with Floor, Bottom, Path; FishHatchery (1,0,1), a floor-only bank cell.
  - Native 1.1.2.8 `BuildingAccessible.CalculateAccessAtEntrance` puts the access at the centre of `PositionedEntrance.Coordinates`.
  - `PositionedEntrance.DoorstepCoordinates` = Entrance minus the unrotated Down offset, so the doorstep is the cell north of the Entrance.
  - 138 of 139 vanilla buildings put the Entrance at y=-1, on the path cell in front of the door. The exception is the Folktails Carousel.
  - FisheryWorks: a player's path in front of the door joined only through a generated deck edge, and `DynamicPathModel` draws a path's connection stub only toward an entrance flag on that path cell. The path therefore looked unconnected, which is what `civic_building_content.mjs` already fixed for the Restaurant.
  - FishHatchery: the access was off the road network, since the door cell has no Path occupation or link to the outside. It showed "not connected" unless a path was laid on its own door cell, which the fixtures did.
- **Fix:**
  - New `tools/native_entrance.mjs`: native Entrance = the cell in front of the layout's door cell (door occupied, Entrance cell open).
  - `fishery_building_content.mjs`: Entrance (3,-1,0). The door-to-Entrance deck edge and the shaft exclusions now use the door and Entrance cells.
  - `hatchery_building_content.mjs`: Entrance (1,-1,1) at bank height, plus an IsPath door-to-Entrance link. Water rules, adaptive posts, the cursor pivot (1.5,0.5) and `StackableBaseLoadOrder` are unchanged.
  - `validate_hatchery_exports.py` expects (1,-1,1).
  - Mirror generation changes only these Entrances and the hatchery edge. Mirror `validate_all -SkipBlender`: 47 passed, 0 failed.
- **Check:** new `tools/validate_building_entrances.mjs` (`building_entrances`). Every entrance must be at the base level and open (outside the footprint, or an unoccupied porch connected to the outside), with an occupied doorstep; exceptions need a documented native access.
  - Mirror: all 45 entrances pass (11 in open porches: GroceryStore, Restaurant, CryogenicLiquefactionPlant, ElectrolysisPlant, LaunchPad, RadioactiveWasteRefinery, ArchiveExcavation, MissionControl, WaterTreatmentPlant, Bathhouse, TownPlaza).
  - Current src: fails on exactly FisheryWorks and FishHatchery, until the generated data is promoted.
- **Tests:**
  - All-buildings harness: the special deck-entrance branch is removed. "Entrance takes a plain player Path" passes only for an ordinary Path on the native Entrance and fails on a building's own block. New "a beaver reached the building through its entrance" check.
  - FisheryAcceptance: FisheryWorks expects Entrance (3,-1,0) with the existing ordinary paths. The hatchery gets one path on its Entrance (188,155); the door cell is no longer paved (removed from `HatcheryPathCells`); it asserts district and access through that path alone.
  - Scripts compile, excluding the other agent's in-progress `SluiceIsBack` folder, which needs its own dependency.

## Fish Hatchery compact (8x8 → 7x7) with the cursor anchor on its door: scene regenerated and exported to outputs, not promoted, built or tested in game (Claude Code session, 2026-10-26)

- **Cursor (user bug: the preview dropped onto the riverbed).**
  - Native mechanism (decompiled 1.1.2.8 `BlockObjectPreviewPicker.CenteredPreviewCoordinates` / `ComposeCoordinates`): the cursor ray takes the first terrain or stackable top face it meets (water is not a face). The origin is (hovered cell − `PlaceableBlockObjectSpec.CustomPivot`, or `Size/2` without one), and z is that face's height − `BaseZ`.
  - The hatchery had no pivot, so the cursor sat over the water under the deck and the preview took the riverbed height.
  - Vanilla water buildings anchor on a bank cell. The SwimmingPool has pivot (1.5, 0.5) with BaseZ 1, and Large Water Wheel, the pumps and the Lido are the same.
  - The hatchery now uses CustomPivot = door cell + 0.5 = (1.5, 0.5), set in `tools/hatchery_building_content.mjs`.
  - Native pivots are rotated but never flipped. A flipped hatchery therefore has the door's mirror (5,0), still a bank cell, under the cursor. `validate_hatchery_exports.py` replays the native pick: 4 rotations × 2 flips × 9 cursor positions.
  - No other building needed a change. FisheryWorks' centre cell is on its hall foundation, and its centre column is flip-invariant. The sludge recovery pump and the outfall pivots already sit on ground cells. The hydro turbine's pivot is over its channel by design, because its base is the bed.
- **Compact footprint (user: "remove the extra docks around the edges").**
  - Removed: LeftDock (x0, y4–7), RearDock (y7), RightDock (x6–7, y4–7) and the walkway column beside the headhouse. Grid x moved −1 with SOURCE_ORIGIN, so every kept part keeps its source position.
  - Kept: the headhouse, door and bank row; the canopy, intake and header tank; both pens with their 4 work cells; the front walkway; the centre dock; player paths.
  - Now: 4 deck piles (was 9), 6 adaptive bank posts, ground only under the door, 3 rail openings (was 20), 14 suggested path cells (was 35).
  - The intake moved from (7,2,1) to (6,2,1).
  - Triangles 20,238 → 18,950 (ceiling recorded), vertices 42,605 → 39,452.
  - Strict z-fight audit: 0 visible. Hidden-geometry audit: 0 culled faces exposed, hidden share 23.0%. Door culling: 0 failures. sources-civic passes.
  - New `refresh_hatchery_metadata.py` writes the component, rail and native metadata for a redesign; `carry_hatchery_metadata.py` only carries unchanged metadata.
  - Review: `outputs/review-sheets/hatchery-compact.png`. Evidence: `outputs/hatchery-compact/`.
- **Sites (map script validate OK on all four, in mirror `hatchery`):**
  - Plains and Plains-hard: 145,147,3 Cw0, route 19.
  - Lakes: 102,150,3 Cw0, route 16.
  - Terraces: 121,195,6 Cw90, natural with no Dynamite. Its pen 0, the native contamination sample, is at 0.00; the far pens are at a mixing edge, 0.11–0.25. A listed alternative at 128,193,6 Cw270 uses two one-layer charges and keeps all four pens clean.
  - All-buildings contract: valid.
- **Fixtures updated:** FisheryAcceptance (paths, pond 187..193 × 157..162, power, platform stack, rail openings, walk targets, access 188.5), AquacultureContinuity, AquaculturePipeAcceptance and its capture script (intake line one cell west).
  - The deck no longer reaches the bank row. The fixture joins the bank row on the west along x=186, a cell column outside the surveyed pond; this is untested.
  - AllBuildingsSites adds "site: cursor on the door cell picks the bank height": a native picker ray onto the door cell must pick the contract placement, and that native preview must be valid.
- **Checks:** scripts compile with 0 errors. All 47 non-Blender `validate_all` checks pass in the mirror, plus sources-civic.
- **Open:** promotion and canonical generation in the real Data; the in-game cursor, placement and fixture runs. Existing hatchery saves need re-placement, because the registration changed.

## Map objects and ore goods rebuilt in native style: promoted and installed in build 169 (verified); pile visuals load-tested in game, the rest not yet seen in game (Claude Code session, 2026-10-25)

- **Build 167 crash and fix (builds 168 and 169 installed; build 169 verified, 647 hashes; game closed).**
  - Symptom: every game load failed with `InvalidOperationException: Failed to load asset at StockpileGoodModels/DeepFrontier/1DeepOre` in `GoodPileVariantsService.BuildIntermediateMeshes` (`outputs/map-loop-b167-plains.log`).
  - Cause: `GoodVisualizationSpec.PrimaryMesh`/`SecondaryMesh` are `AssetRef<Mesh>`, which load through `AssetBundle.LoadAsset<Mesh>`. The official importer (`Timberborn.TimbermeshTools.Editor` `TimbermeshScriptedImporter`, decompiled in `outputs/timbermesh-editor-api`) adds Mesh sub-assets only when its `_createMeshAsset` option is set. By default it stores just the BinaryData GameObject.
    - The build 167 bundle held only a GameObject at each pile path.
    - Bob Storage's bundle holds a GameObject and a `Mesh` (`#18BoxColumn`) at `stockpilegoodmodels/18boxcolumn.timbermesh`.
  - Fix: Deep Frontier > Create Materials (run by the batch build) now calls `DeepFrontierMaterials.ImportPileMeshes`.
    - It sets `_createMeshAsset` on every `.timbermesh` under `AssetBundles/Resources/StockpileGoodModels`, through the importer's own serialized option, and reimports.
    - It then requires one readable single-submesh Mesh per file.
    - `DeepFrontierBatchBuild` re-checks the import result and fails the build otherwise, because exceptions inside a menu item do not fail `ExecuteMenuItem`.
    - The importer logs "Material BeaverCarryingModels not found": the authoring project has no such editor material, so the prefab renderer gets no material. The pile draws with the GoodVisualization material.
  - Static check: new `tools/asset-pipeline/validate_goodmesh_exports.py` (`exports-goodmesh` in validate_all). Every non-vanilla GoodVisualization mesh must have one bundled source under the configured folder.
  - Package check: `verify_deep_frontier_package.ps1` now runs the same check with `--bundle` on the installed bundle and requires a Mesh at each path. Against build 167 it reports the 4 GameObject-only paths; against builds 168 and 169 it passes.
  - Load tests, `tools/start_memory_load.ps1`, new Plains game, 13 GB sampler:
    - b168: loads, 180 s of game time, no exception, peak 10.46 GB.
    - b169 with the new `-PileProbe`: same, peak 10.47 GB.
    - The probe (`Scripts/PileVisualizationProbe.cs`, flag `-deepFrontierPileProbe`) placed two finished SmallIndustrialPile.IronTeeth with 20 DeepOre and 20 DeepAlloy. PASS for both: the GoodVisualization meshes have 920 = 5 x 184 vertices (five levels of `4DeepOres`) and 400 = 5 x 80 (`4DeepAlloys`).
    - Screenshots: `outputs/pile-probe-DeepOre.png`, `outputs/pile-probe-DeepAlloy.png`, `outputs/review-sheets/pile-probe-b169-close.png`.

- **Contract:** `tools/map_objects.json` (footprint, height band, triangle ceiling per model; pile-good meshes). Template ids, footprints and placement rules are unchanged.
- **Audit (before, `outputs/review-sheets/map-objects-before.png`):**
  - The vein and both seams were one mesh: 88 jittered blobs, 12,774 triangles each (5x the largest vanilla map object). Only the colour differed: BaseMetal (a striped plate tile), white plaster, orange plaster.
  - The outcrops were three plaster blobs (712 triangles). The ore source was four metal-plate boulders.
  - The vein had no collider: its UndergroundRuins collider was dropped with the children, so it could not be selected in the map editor. The seams had a full-layer collider over a 0.4 model.
  - Radioactive Spring (map and dev tool): the vanilla water-source rock with every material replaced by flat emissive yellow-green.
  - Human Record Cache: the vanilla MediumRelic model and icon.
  - DeepOre piled as vanilla ScrapMetal (rusted bars) and DeepAlloy as vanilla MetalBlock. CrudeOil and RadioactiveSludge showed golden CanolaOil in tanks.
- **New models** (one saved scene per model, `src/DeepFrontier/Art/Source/<Id>-ReferenceStudy.blend`, built by `tools/asset-pipeline/build_map_objects.py` from `map_objects_geometry.py`, exported to `outputs/mapobjects-integration`):
  - Native materials only: WaterSource/UndergroundRuinsCliff rock, BaseMetal ore, BeaverCarryingModels goods atlas, Plaster sandstone/limestone, Ruins slabs, UnstableCore bronze. Each face has a UV island inside its atlas tile; no glowing UnstableCore regions.
  - Triangles:

    | Model | Before | After |
    |---|---:|---:|
    | DeepOreVein | 12,774 | 1,265 |
    | SandstoneSeam / LimestoneSeam | 12,774 / 12,774 | 582 / 369 |
    | SandstoneOutcrop / LimestoneOutcrop | 712 / 712 | 145 / 76 |
    | DeepOreSource | 712 | 495 |
    | RadioactiveSpringSource (also the dev tool) | 305 (vanilla) | 289 |
    | HumanRecordCache | 1,072 (vanilla) | 440 |
    | DeepOre pile item / level | 16 / 64 (vanilla scrap) | 16 / 62 |
    | DeepAlloy pile item / level | 10 / 40 (vanilla block) | 10 / 40 |

  - Vein: fractured bedrock plates on a dark bedrock floor, a diagonal fissure of ore crystals and nuggets; at most 0.3 high under the Deep Mine floor.
  - Seams: sandstone is stepped terraces of orange blocks with dark partings; limestone is a pale clint pavement with dark grikes.
  - Spring: a rock ring around a pool and sinter crusts. Only the `RadioactiveGlow` node is tinted: `RadioactiveSpringVisual` now matches renderers by that name and throws if none exists.
  - Cache: a half-buried concrete vault with a bronze hatch, lintel, vent, rebar and record canisters. It keeps the native MediumRelic blocks and underground part; new icon `Art/Icons/HumanRecordCache.svg`.
- **Goods:**
  - Carried models cannot be custom: `VisibleContainer` is an enum of beaver-rig children (`GoodCarrierModel`, `CarriedItem`). DeepOre stays Scrap and DeepAlloy MetalBlock; dropped `GoodStackModel` stacks show only Log, Barrel, Box and Bag, as for vanilla scrap and blocks.
  - Pile models: `GoodVisualization.DeepOre`/`.DeepAlloy` are cloned from vanilla ScrapMetal/MetalBlock (same offsets, 4 per level, goods-atlas material). Their meshes ship as `.timbermesh` in `AssetBundles/Resources/StockpileGoodModels/DeepFrontier/`, the route Bob Storage 1.1 uses for `StockpileGoodModels/18BoxColumn` (an `AssetRef<Mesh>`).
  - Partial blueprints append the two visualizations to SmallIndustrialPile/LargeIndustrialPile.IronTeeth, ReservePile and Expanded Storage's PileModule.IronTeeth. They are registered as vanilla patches in `automation_content.json`; a new `baseRoot` field points at the installed dependency.
  - Tank liquids: CrudeOil uses `Materials/Goods/Coffee`, RadioactiveSludge `Materials/Goods/BioFuel`.
- **Colliders** now fit the models (box up to `maxHeight`). The vein gained one; the seams dropped from 1.0 to 0.32 high; the ore source rose from 0.49 to 1.3.
- **Generators:**
  - `tools/map_object_content.mjs` holds the contract helpers and pile visualizations. It is used by `create_vertical_slice_content.mjs` (vein, source, goods), `create_construction_material_content.mjs` (seams, outcrops), `radiation_content.mjs` (spring model, sludge liquid), `narrative_content.mjs` (cache model, collider, icon) and `create_frontier_expansion_content.mjs` (crude oil liquid).
  - `generate_approved_buildings.py` and `generate_construction_material_assets.py` no longer write MapEditor models.
  - `create_frontier_expansion_icons.mjs` renders the cache icon. `tools/render_map_object_icons.mjs` renders only the map-object icons, into any Data root, and leaves the docs sheets alone.
- **Checks:**
  - Strict z-fight: 0 visible and 0 occluded on all 12 scenes.
  - Hidden geometry (`--terrain-z 0`): 0 culled faces exposed. Hidden shares are 0-18%, mostly buried prism bases and crystal roots.
  - `validate_triangle_budget.py`: 12 new rows, classes `mapobject` (target 2,500) and `pilegood` (target 64).
  - New `validate_mapobjects_exports.py` (`exports-mapobjects`).
  - Mirror `mapobjects`, with the candidates copied in as promotion would: canonical generation, map-object icons and `validate_all -SkipBlender` (45 pass, item uses report only).
  - `prepare_deep_frontier_map.py validate` on all four variants: OK.
  - Scripts compile with 0 errors.
- **Promotion:** promoted into real `src/DeepFrontier` for build 167. For later re-exports: `pwsh tools/promote_map_objects.ps1`, then canonical generation, then `node tools/create_frontier_expansion_icons.mjs`.
- **Must be checked in game:**
  - DeepOre and DeepAlloy in the large pile, ReservePile and Expanded Storage PileModule. The small industrial pile passed in b169.
  - The spring glow tints only the pool.
  - All objects sit on the terrain and are selectable.
  - The Coffee and BioFuel tank surfaces look right.
  - The Deep Mine and quarries still place over the vein and seams.
- **Review sheets:** `outputs/review-sheets/map-objects-before.png` and `map-objects-after.png` (before | after close | after, matched cameras, icons). Renders are by `render_map_object_views.py` and `compose_map_objects_sheet.py`, from native textures cached by `export_map_object_references.py` in `outputs/map-objects/native`.

## Item-use gate completed and official package rebuilt (2026-10-25)

- `tools/create_frontier_expansion_content.mjs` now consumes one `Cryocoolant` in `ReactorCoolantWater`, giving the cryogenic chain a second productive destination.
- `tools/research_content.json` now sends one `LiquidHydrogen` and one `LiquidOxygen` into `GeochemicalAssay`; the materials lab therefore has a real cold-fuel research sink in addition to rocket missions.
- The refinery now exposes `SludgeMineralRecovery`, consuming `RadioactiveSludge` for `RecoveredMinerals` and `ConcentratedWaste`; sludge remains available for vitrification and controlled export.
- Canonical generation completed in the working tree. Scratch mirror `implementation-debug` passed `tools/validate_all.ps1 -SkipBlender`: 44 hard checks passed, 0 failed; the report-only item-use audit checked 55 goods with 0 failures and `releaseReady=True`.
- `tools/build_deep_frontier.ps1` completed the official Unity Mod Builder successfully. Log: `outputs/unity_official_build.log`.
- The balance workbook was rebuilt from current source: `outputs/Timberborn_Deep_Frontier_Balance_Workbook.xlsx` (70 buildings/features, 77 recipes, 55 goods, 18 dependencies, 38 power rows). Runtime acceptance and save/reload testing are still separate from this static/package result.

## Map variants support the full loop: statically validated, written to the Maps folder, and proven in game on build 169 (Claude Code session, 2026-10-24/25)

- **In-game proof, build 169 (2026-10-25)**, `tools/start_map_loop_test.ps1 -Label b169`, one new game per map, 13 GB sampler (peak 10.35 GB), game closed afterwards. Results: `outputs/map-loop-b169-<id>.json`.

  | Map | Checks | Failed |
  |---|---:|---:|
  | Plains | 88 | 0 |
  | Plains Hard | 89 | 0 |
  | Lakes | 85 | 0 |
  | Terraces | 86 | 0 |

  - Every check passed on every map:
    - the map file matches its evidence hash;
    - every placement survived loading, with full stock and yield, and the caches are unsurveyed;
    - the native preview accepted every site;
    - the hatchery work cells are in clean water;
    - the pump intake columns hold water;
    - the dam sites are wet;
    - both pits on each map see all three of their outcrops in their native `InRangeYielders`.
  - Terraces ran with its seven blasted cells.
  - Build 167 crashed at game load: `StockpileGoodModels/DeepFrontier/1DeepOre` failed to load as a good-visualization mesh. The coordinator fixed it in 169.
  - Launcher fix: `-Variants a,b,c` passed through `pwsh -File` arrives as one string and is now split.
- **Build 174 rerun (2026-10-26)**, `-Label b174`, peak 10.29 GB, game closed afterwards.
  - Plains 88/0, Plains Hard 89/0, Lakes 85/0, Terraces 88/1.
  - The Terraces failure is the test's own strictness. Its hatchery check required contamination ≤ 0.05 on all four work cells. The game only samples `WorkCells[0]` (`WaterDepthWorkCells` → `ContaminationBlockableBuilding`), and so does the static validator.
  - On the primary hatchery, the sample cell read 0.00; the other two pens read 0.05 and 0.16. The backup site read 0.00 on all four.
  - `MapLoopAcceptance.cs` now checks depth on every cell and contamination on the sample cell only. It compiles; it is not built and not rerun.

- **Requirement matrix:** `docs/maps.md` "Full game loop". It is derived from the generated blueprints, recipes, building costs and narrative settings; the policy minimums are in `tools/map_loop_requirements.json`.
  - `site_rule` classifies every building of the Iron Teeth collection. Special placement specs get special sites: understructure, map edge, waterside depth, water intake, pit with deposits, dam. Generators and buildings with a side of 8 or more get a flat site.
  - Native constants (decompiled): pit range `NavigationDistance.ResourceBuildings` = 20; hatchery contamination limit `ContaminationBlockableBuilding` 0.05.
- **Audit before:** on all four maps,
  - no sandstone/limestone outcrops (pits had nothing to dig, so concrete was unreachable) and no seams (quarries impossible);
  - no Human Record Caches placed (5 discoveries unreachable);
  - 36 building types without a checked site; no map-edge export, hatchery, sludge-pump or dam site.
  - Plains: no shore-fishing bank within route 80 (the start river is 0.32 deep, under the 0.5 minimum).
  - Deep ore: the finite sources (6,000 / 4,000 / 4,000) cover one of each building (2,450 DeepOre) but not three launches on top (5,451 more). The permanent Deep Mines carry the program; each map has three veins with sites.
- **Fix (variant JSON only; the script edits no terrain):** per map,
  - three outcrops of each stone beside their pit sites;
  - a seam of each stone under a quarry site;
  - five caches, each with its own Archive Excavation site;
  - 40 new sites (48 / 48 / 47 in total).
  - Plains Hard equals Plains plus its spring.
  - Three sites list player Dynamite: the sludge pump intake on Plains and Lakes (one cell), and the Terraces hatchery deck (seven cells). Terraces has no clean reach where the deck clears the bank.
- **Tooling:** `tools/prepare_deep_frontier_map.py`
  - sites are a generic list keyed by building template;
  - `check_sites` and `loop_coverage` fail any stage without its provision;
  - the `plan` command proposes what a variant lacks;
  - outcrop entities save `Yielder:Mineral`;
  - previews mark and list every placement and site.
  - `tools/test_prepare_deep_frontier_map.py`: 17 injected faults, all caught.
- **Validation:** `build` on all four maps reports 0 errors, every loop stage OK. The maps were written to `Documents/Timberborn/Maps` after the dry run passed; the .NET ZipFile open check passes. Evidence: `outputs/maps/<id>-validation.json` and `-preview.png`.
- **In-game proof (not run):** `tools/start_map_loop_test.ps1` with `Scripts/MapLoopAcceptance.cs` (`-deepFrontierMapLoop`, new game, never saves). It checks the map hash against the evidence, every placement after load, a native preview of every site (trees removed, Dynamite cells blasted first), dam-site water, and each pit's native `InRangeYielders`.
  - Compile-only check against the game DLLs, in a scratch copy of `outputs/all-buildings-compile`: passed.
  - `validate_editor_guards`, `validate_component_lifecycle` and `validate_priority_statuses`: passed.
  - It needs a mod build that contains the script, and the user present for the startup dialogs.
- **Building findings for their owners:**
  - The Radioactive Sludge Recovery Pump needs a one-cell water notch: Air below its intake, Ground below both neighbours. Natural shores almost never have one.
  - The Fish Hatchery needs clean water at least six cells wide off a straight bank.

## All-buildings regression audit and functional test: static diff and patch audit done, driver compiled, not built or run in game (Claude Code session, 2026-10-23)

- **Static diff.** The old blueprints and models were recovered byte-exact from the `%USERPROFILE%\dfs` mirrors by the sha256 in `outputs/restaurant-package-verification<N>.json`: builds 125, 139 and 140, 304/304 files each. They were compared with the build 146 install and the current src (build 147).
  - 140 -> 147: connection faces (transputs and pipe ports); reactor PowerOutput 75000 -> 750000 (intended); Stackable roof decks on LaunchPad, MissionControl, PrecisionMachineWorks and ArchiveExcavation; Bathhouse FixedSlotManager plus 12 `#Slot#Spot` nodes; TownPlaza props and occupancy.
  - No Inventory, Workplace, Enterable, Attraction, GoodConsuming, recipe or power-input spec changed since 125.
  - Every entrance is reachable from outside its footprint and its door cell is occupied. Every `#` node a spec references exists in the models.
- **Patch audit:** every Harmony patch and native-type decorator leaves non-target buildings on the native path. Evidence for each is in the session report.
- **Status priority fix (source):** HospitalPantry "out", SpecialistWorkplace "no specialists" and RadiationIntakeGuard "pump blocked" are now normal statuses.
  - Why: native `StatusSubject.ActiveStatuses` lists only the priority statuses while any is active, so these hid the native NoPower, no-workers and lack-of-resources statuses.
  - Priority stays only on the hazards: reactor overheat, scram and coolant dry; cryogenic venting and wrong network; waste leak.
  - New check `tools/validate_priority_statuses.mjs` (`priority_statuses` in validate_all) fails on any other priority status.
- **All-buildings test (compiled, editor-guard checked, not run):** `Scripts/AllBuildingsAcceptance.cs` (`-deepFrontierAllBuildings`, new game through the acceptance loader) and `tools/start_all_buildings.ps1 -Label <label>`.
  - Placement: every TemplateCollection building, the patched vanilla templates and vanilla references, in batches on a dry levelled pad by the district centre.
  - Checks: placement; entrance; unpowered NoPower in the panel and as a floating icon; status icon height; missing-input LackOfResources; exactly one enabled inventory accepting its goods; enterable; slot nodes; worker; production; power demand or supply; Timber Pipes chain tank -> pump -> pipe -> valve (Inlet on) at a generated side-face port with liquid arriving; each attraction visited (the others blocked, matching needs lowered).
  - Results go to `outputs/all-buildings-<label>.json`. Water, map-edge and seam buildings report SITE on the dry pad.
- **Status icon anchor (source plus mirror `regression` generation; not built):**
  - The native icon floats 0.7 above the tallest mesh (`BuildingStatusIconOffsetter`). Measured on the exported models, it sits 3-14 layers above the main body on about 25 buildings (LaunchPad 14.4, Cryo plant 10.7, Technical School 8.7, Bathhouse 5.2).
  - `tools/status_icon_content.mjs` (the last generation step before the automation audit) writes `StatusIconAnchorSpec {Height}` on all 64 Deep Frontier building templates. Height = max(main roof, top of the occupied cells within 1 of the footprint centre, so the icon never sinks into a central tower) + 0.7. The main roof is the highest layer holding at least 30% of the widest layer's occupied cells. 28 of the 64 are lowered.
  - `Scripts/StatusIconAnchor.cs` postfixes the private `GetFinishedTopBound`/`GetUnfinishedTopBound` and caps the result at Coordinates.z + Height, only for entities with the spec; it never raises. Native members, the calls, the 0.7 offset and the Mono inline limit are verified at mod start. Vanilla stays native.
  - Check: `tools/validate_status_icon_anchors.mjs`. `automation_content.json` declares the spec passive. The all-buildings test asserts the icon is at or below the anchor.
- **In-game all-buildings runs (builds 148-155, `outputs/all-buildings-b1xx.json`):**
  - Map: no Deep Frontier map has a dry 48x40 pad near its start. `tools/create_flat_test_map.py` writes `Documents/Timberborn/Maps/Deep Frontier - All Buildings Test.timber` (flat, dry, height 3, start at the centre), the launcher's default.
  - Harness fixes:
    - `Workplace.DecreaseDesiredWorkers` stops at 1, so idling is a native pause; `LategameAcceptance.Idle` has the same infinite loop.
    - Frontier Journal dialogs are dismissed with native Escape.
    - BaseZ anchoring; native stairs to raised entrances; deck entrances.
    - Pipe liquid chosen from recipe ingredients, not maintenance oils.
    - LimitedAmount for goods checks; beaver needs refreshed every 3 h; work phases count working hours only.
  - **Passed (b152-b155):**
    - Bathhouse and Hospital: tank -> pump -> pipe -> valve (Inlet on) at a generated side port delivers Water. Supplied but unpowered, they show native NoPower in the panel and as an icon. The Bathhouse is appealing and visited.
    - Pipe liquid arrives on all 30 piped buildings that fit a line.
    - TownPlaza, ObservationDeck, MudBath and Campfire are visited.
    - Status icons sit at their anchors.
  - **Root cause of "no no-power icon":** Moddable Timberborn 11.1.3 (required) postfixes the MechanicalGraph Powered getter to report a graph with zero demand as powered. A consumer without inputs or workers draws nothing, so the native NoPower never shows; the vanilla Smelter and MudBath behave the same.
    - Fix: `Scripts/PowerConnectionStatus.cs` adds "Not connected to a power source", a normal status with alert and the native NoPower icon, on all 34 Deep Frontier consumers while their graph has no generator or battery. The spec and localization come from `status_icon_content.mjs`; the check is `validate_status_icon_anchors.mjs`.
  - **Moddable Recipes 11.0.0 workaround: `Scripts/InventoryEnableGuard.cs` (2026-10-24, approved; report upstream).** All-buildings run b161 crashed the game with a NullReferenceException in `DistrictInventoryPicker.InventoryIsTaking`.
    - What happened: batch 1's DeepProcessor (single-recipe, accepts DeepOre) had been deleted. Its inventory was still registered with the district, because the double Enable below registers it twice and deletion unregisters it once. Batch 2's DeepDrill worker emptied DeepOre (`EmptyOutputWorkplaceBehavior`) and the native picker reached the destroyed inventory. The same crash can happen in normal play.
    - The fix is a Harmony prefix on native `Inventory.Enable` that skips the call only when the inventory is already enabled. Native `Inventory.Initialize` ends disabled, so the first Enable runs unchanged. Disable is not patched. The native signatures are checked at mod start (inside `#if !UNITY_EDITOR`), and the prefix is applied from `DeepFrontierModStarter`.
    - Static check: `tools/validate_inventory_enable_guard.mjs` (`inventory_enable_guard`).
    - Test: the all-buildings harness asserts "enabled inventory listed once" on every building, which was INFO before. After each batch is deleted, it looks up every good the deleted buildings' inventories accepted or held through the native `DistrictInventoryPicker` (the worker's emptying path). It requires that no destroyed or deleted inventory remains in the district registry ("deleted: no district inventory left behind"). The next batch's workers then empty outputs through the same path.
    - For the upstream report: in `ModdableRecipes.Patches.ManufactoryPatches.InitInventoryForRecipe`, `inventory.Disable(); ... inventory.Enable();` should restore the previous enabled state instead of always enabling.
    - **Complete fix (approved):** `ModdableRecipesEnabledState` (same file) patches MR's `InitInventoryForRecipe` for every manufactory.
      - A `Priority.First` prefix records `inventory.Enabled`. A `Priority.Last` postfix disables the inventory again (native Disable) only when MR enabled one it had found disabled. MR therefore never leaves a construction-site inventory enabled or registered, which a site deleted unfinished never unregistered.
      - Order with our other hooks on that method: the prefix runs before `RestaurantKitchenRecipeCompatibility` (which skips MR for the restaurant; state unchanged, postfix no-op). The postfix runs after `BotMaintenanceRecipeCompatibility` (which keeps the state it finds).
      - MR's signature and both hooks' shapes are checked at mod start. The Enable guard stays as defence in depth. Both are covered by `validate_inventory_enable_guard.mjs`.
      - Construction-site repro in the harness, before batch 1: a vanilla Smelter is placed as an unfinished native site and a recipe is selected. The test asserts the inventory stays disabled and unregistered. The site is then deleted, and the test asserts that every good it accepted resolves through the native picker with no district inventory left behind.
  - **Grocery crash fix (b163):** the run crashed again with the same `InventoryIsTaking` NullReferenceException, this time from `EmptyInventoriesLaborBehavior`.
    - Cause: `GroceryStore`'s inventory is a public input, but the entity had no `IInventoryValidator`. Native public-input buildings get one from the `Emptiable` decorator.
    - Effect: any worker emptying a food the Grocery takes (the nearest reachable taker) stopped the game. The deletion probe caught it first (food goods failed after batch 1, with batch 2's Grocery present).
    - Fix: `GroceryStoreConfigurator` adds the native `Emptiable` decorator, as the Restaurant does. AutoEmptiable is not added.
    - New harness check on every building: "public inventory meets the native picker contract" (IInventoryValidator and BlockableObject present).
  - **b164 (build 164): complete, 77 subjects, 73 PASS, 4 FAIL, 9 failed checks, no SITE; memory peak 10.2 GB.**
    - All 12 site buildings placed on their sites. Results: DeepMine 30 cycles, quarries 4 each, Hatchery 3 cycles with 26 deck paths ranked after it and still standing, Deep Water Pump 41 cycles. The decks' preview was accepted on the anchor and rejected on a plain platform, and they were built on. The turbine reached 4800 hp at 1.5 flow and 16.8 head. The shower and pool were visited.
    - Construction-site repro passed, every deletion probe passed, and the Enable guard skipped 0 calls (the MR restore removed every duplicate).
    - Fixed after b164:
      - **Radiation (gameplay):** `RadiationSimulation.AddRadioactiveWater` into a world with no radiation yet was never tracked. Its row was outside the scan envelope, so 20.8 radioactive volume added to two dry pools read 0. The same would hit a waste leak, an outfall or a continuous source on a clean map. The add's row now joins the pending rows (geometry synced before the mix), and the rows mixed by the parallel tick join the next envelope (`_mixedRows`).
      - **Harness:** the Hatchery's entrance cell is a native floor that needs a player Path, as the hatchery fixture builds it ("district connection none"). The SwimmingPool slot count ignored its patrolling water slots. The Sandstone Quarry was already filled with Water by haulers before the pipe line, so arrival could not be measured; the harness now makes room first.
  - **b165 (build 165): 75 PASS, 2 FAIL.** The radiation fix worked: 10.32 radioactive volume per pool, 5 sludge recovered. Both failures were test arithmetic:
    - The world radiation balance subtracted the control drift once, but the world holds both pools. It is now split: the pumped pool falls by recovered + drift, the world by recovered + 2 x drift. The tolerance is 0.03 + 5% of recovered + 5% of drift, plus the radiation outside both pools at the baseline.
    - The DoubleShower's "appealing" check required a free slot while visitors held both. It now requires the shower to be open.
  - **b166 (build 166, installed and verified, 636 hashes; game closed): `outputs/all-buildings-b166.json`, 77 subjects, 77 PASS, 0 failed checks, 0 SITE.** Memory peak 10.17 GB of the 13 GB ceiling.
    - Sludge: 5 goods (1.000 recovered) in 8.2 h. Pumped pool 10.323 -> 7.942: recovered + control drift 1.332, difference 0.049 (tolerance 0.147). World 20.771 -> 16.932, difference 0.174 (tolerance 0.339).
    - Turbine: 4800 hp at 1.5 flow, 16.8 head; 76 delivered to the lower reach.
    - The MR restore ran 52 times and the Enable guard skipped 0 calls.
    - One "worker kept" INFO: the reactor's worker had a critical industrial injury at 39.5 h, was restored and employed again.
  - **Build 169 (map-object/ore models, sludge pump edge intake, hatchery door-only bank foundation, regenerated maps).**
    - The sites contract still validates against the new blueprints, so the map is unchanged. The new hatchery bank posts and the sludge edge intake passed the native preview in game.
    - b169: 74 PASS. All three failures were "no inputs: LackOfResources" on the mine and quarries, a test-timing issue:
      - Native `ManufactoryInputAvailabilityChecker` re-checks only on the building's inventory, worker or district events.
      - The district's Water ran out after the workers were assigned, so the status stayed stale.
      - Fix: the harness re-assigns each wave manufactory's worker 0.05 h before the snapshot (a native worker event). It classifies the result with the native predicate: SKIP when the building holds every ingredient and its fuel.
    - b170 (build 170): 77/77. b171 (build 171, fuel refinement): 76/77; the 0.2 h re-check window was too wide.
  - **b172 (build 172, installed and verified, 647 hashes; game closed; final confirmation): `outputs/all-buildings-b172.json`, 77/77 PASS, 0 failed checks, 0 SITE.** Memory peak 10.50 GB.
    - Sludge: 5 goods (1.012 recovered); pool difference 0.051 (tolerance 0.147); world difference 0.051 (tolerance 0.213).
    - Turbine: 4800 hp at 1.5 flow and 16.8 head.
    - MR restore ran 52 times; the Enable guard skipped 0 calls.
    - Two industrial injuries were handled (WaterTreatmentPlant, RadioactiveWasteRefinery).
  - **Build 173 (restaurant auto-cooking, 7x7 hatchery with the door-cell pivot, roof decks on 46 buildings).** The sites contract validates unchanged.
    - b173: 70 PASS. All 7 failures were test-side:
      - The new cursor check built a Unity world-space ray. The native picker takes grid-space rays (`CameraService.ScreenPointToRayInGridSpace`, `GridTraversal.TraverseRay`), so the check now casts straight down in grid space.
      - The roof-deck probe on the side platforms found the slabs already built on by "building on the deck". That now runs after the probe.
      - The roof-deck probe on the turbine sampled cells under the divider dam. Cells held by objects other than the building are now left out and reported as INFO; on pad buildings these were goods stacks recovered from the previous batch.
      - LackOfResources has a native 3 h show delay, which the 0.05 h worker re-assignment restarted. An active status still inside the delay now counts.
  - **b174 (build 174, test-only changes; installed and verified, 647 hashes; game closed): `outputs/all-buildings-b174.json`, 77/77 PASS, 0 failed checks, 0 SITE.** Memory peak 10.54 GB.
    - 44 roof-deck passes; the hatchery cursor check picked the contract placement (bank height).
    - Sludge: pool difference 0.054 (tolerance 0.147).
    - Turbine: 4800 hp.
  - **Dependency bug (the cause of the workaround above):** Moddable Recipes 11.0.0's SetRecipe prefix (Disable/Enable before the native finished-state Enable) lists every single-recipe manufactory twice in `Inventories.EnabledInventories` and registers it twice with the district (`InventoryRegistered` fires twice). As a result the goods-balance production and consumption counts double, and Timber Pipes reports double stock and limit. Affected: vanilla Smelter, Reactor, Cryo, DeepDrill, Electrolysis, PublicHealthLab, both power plants, Crusher, Kiln, Mixer, Outfall. A save and reload clears it.
  - **Generator start deadlock (fixed, verified in build 160):** the Smelter-clone generators keep MechanicalBuildingSpec, which is needed for the Power batch-control tab. Native `ProduceExecutor.Launch` refuses while `MechanicalBuilding.ActiveAndPowered` is false, so a plant whose graph has demand and no other supply never starts (the Oil plant with a charging station). `WorkshopPoweredGenerator` now offers a 1 hp pilot output while the plant is staffed and the recipe is ready. The Oil plant reached 20,000 hp, Coal 5,000 and the reactor 750,000.
  - **More harness fixes (builds 157-160):**
    - Each batch is emptied (workplaces paused, buildings blocked, wait until nobody is inside) before deletion. A beaver inside a deleted building never decided again, which caused the flaky "worker wanders" failures.
    - Production is observed from the supplied-unpowered phase onward.
    - The generator supply check requires the full output.
  - **Build 160 (installed, verified 636 hashes): `outputs/all-buildings-b160.json`, 77 subjects, 0 failed checks, 65 PASS, 12 SITE** (DeepMine, FishHatchery, both quarries, the 3 side platforms, the sludge recovery pump, the hydro turbine's supply, DoubleShower, SwimmingPool, DeepWaterPump: they need water, a seam, an understructure or a terrain step). Memory peak 10.07 GB of the 13 GB ceiling.
    - Build 159 still had wandering-worker failures on ChemicalWorks, Greenhouse and the vanilla BotAssembler, which passed in 160. Treat a single production failure as possibly flaky; rerun before concluding.
  - **Sites for the 12 SITE buildings (2026-10-24; written and checked offline, not built or run in game):**
    - Contract `tools/all_buildings_sites.json`: one zone (x 56-196, y 40-119) south of the district centre, clear of the pad and its corridor. It holds a Deep Ore Vein, a Sandstone Seam and a Limestone Seam (map entities); a pond dug one layer (Hatchery, Double Shower, Swimming Pool, Deep Water Pump on its bank); two identical enclosed pools (the sludge pump's, and a control); a two-layer step under the three side-platform decks; and a walled river reach (the `HydroBasinAcceptance` geometry with one turbine). Each building's placement is listed.
    - Map `Documents/Timberborn/Maps/Deep Frontier - All Buildings Sites Test.timber`, written by `tools/create_all_buildings_sites_map.py`: the flat test map (`create_flat_test_map.py`, now with a `flat_map()` function, output unchanged) plus that terrain and those entities, with no water. Before writing, every placement is checked against the planned terrain:
      - `check_object`, MatterBelow Air and Stackable;
      - the UnderstructureFinder core rule;
      - water-input pipe depth onto a filled pit floor;
      - hatchery work cells and pool cell in the pond;
      - anchors carrying `AnchoredDeckAnchorSpec`, and slabs overhanging the step;
      - separate pits, and an identical control pool.
      Eight deliberate mistakes were each caught. The written file is read back with `MapModel` (terrain equals the plan, 3 entities, no water). Preview: `outputs/all-buildings-sites-map.png`. `start_all_buildings.ps1` now defaults to this map. On a map without the sites, the twelve buildings run on the pad and report SITE as before.
    - Driver `Scripts/AllBuildingsSites.cs` (partial `AllBuildingsAcceptance`) runs one sites batch after the pad batches. It fills the water through `IWaterService`/`IRadiationService` (pond 0.8 clean, topped up below 0.65; pools 0.4 clean + 0.4 radioactive per cell; upper reach to height 20). It then builds the dam-block anchors and the divider dam, takes a native preview of every site (`PreviewFactory` + `BlockObjectValidationService`), places the buildings, and runs the generic checks plus:
      - production cycles on the vein and seams (mine, both quarries), the hatchery and the vanilla pump;
      - hatchery nursery cells wet; player paths on its deck (`FisheryAcceptance.HatcheryPathCells`); the native loader ranks them after the hatchery; still standing at the end;
      - decks: preview valid on the dam-block anchor, rejected with the anchor message when cleated onto a plain `Platform.IronTeeth`; a platform and paths built on every slab;
      - sludge pump: intake column radioactive; sludge produced; world water radiation falls by recovered volume (0.2 x cycles + progress + intake buffer, via the new read-only `RadioactiveSludgeIntake.BufferedVolume`), net of the control pool's drift, within 0.02 + 5%;
      - turbine: reach filled with the gate closed; gate opened when the services start; peak flow, turbine and node output, graph supply, and water delivered to the lower reach;
      - shower and pool: intake or pool cell in water; visits (the generic attraction check).
    - Offline checks: the Scripts tree compiles (`outputs/all-buildings-compile`), and validate_all passes for editor_guards, component_lifecycle, priority_statuses, status_icon_anchors, automation_content, radiation_content, deep_frontier_manifest, single_inventory and vertical_slice_content.

## Shafts and pipes on every flat exterior face: generated and validated in mirror `connections`, not promoted, built or tested in game (Claude Code session, 2026-10-23)

- **User rules:**
  - "The Bathhouse and basically any and all buildings need to accept power and pipes on any flat surface of the building."
  - "The reactor has curved edges on it; we don't want to be able to connect to the curved edges, just the flat ones."
  - "We don't connect to roof tiles unless it is platformable roof."
  - "From the bottom counts as flat."
- **Build 146 "the bathhouse is not accepting the pipes" (2026-10-23).** The Bathhouse is a valid Timber Pipes target.
  - Its native GoodConsumingBuilding inventory registers Water as Givable, so Water is in its InputGoods (`GoodConsumingBuildingInventoryInitializer`, `StorableGood.CreateAsGivable`).
  - `BuildingPipeTarget` decorates every BuildingSpec entity. `ValvePipeIo.LiquidIdsForConnection` reads InputGoods when a pipe gives.
  - The user's autosave (`Memory Test`, 11h13m, read-only) shows the cause: three plain `HorizontalPipe` pieces at (133,149), (134,149) and (135,147). They sit on Bathhouse ports (7,6,0) Up (the study inlet), (8,6,0) Up and (8,5,0) Right, fed from a GrandTank, and there is no valve.
  - In Timber Pipes 11.4.0 transport pipes connect only to other pipes and tanks (`PipeRegistry.portOwners`). Only an extraction valve reaches a building (`ExtractionPipe.FindInletTarget` -> `ValvePipeService.FindConnection` -> `BuildingPipeTarget.TryConnecting`): `HorizontalPipeValve` (local Down OpenIn from the network, Up OpenOut into the building) or `ElbowPipeValve`. A new valve's Inlet is off (`ExtractionPipe.InletEnabled` defaults false).
  - **The supported way:** put a valve on a port face with its outlet toward the building and switch Inlet on.
  - **Player hint (generated):** `connection_content.mjs` appends one shared phrase to the description of every piped building (`PIPE_PHRASES`): 32 buildings.
    - In: "Liquids enter through a pipe valve placed against a flat wall, outlet facing the building, with its Inlet switched on."
    - Out (OpenOut/Open): "Liquids leave through a pipe valve placed against a flat wall, inlet facing the building, with its Outlet switched on."
    - Tank farm: "Pipes connect directly to its flat walls, without a valve."
    - `validate_connection_faces.mjs` checks every piped description ends with its phrase and no other building has one. `validate_meltdown_content.mjs` accepts the phrase after the reactor's risk text.
    - Ten descriptions are still generator placeholders ("Deep Frontier ... production building"; a full stop is added before the phrase): FertilizerWorks, FoodPackagingWorks, PublicHealthLab, Greenhouse, ChemicalWorks, PrecisionMachineWorks, WaterTreatmentPlant, UraniumProcessingPlant, ElectrolysisPlant, CryogenicLiquefactionPlant.
    - Older socket wording ("piped in at the boiler-room socket", "two front sockets", "front socket") remains in the Bathhouse, tank farm and radiation descriptions.
  - **Data fix:** no valve is vertical, so building target ports are now horizontal faces only. 1,968 port faces, down from 3,389; the roof and underside pipe ports are gone. Tank farm ports stay six-sided, because transport pipes meet its tank directly.
  - Hospital is the other piped building without a Manufactory or Stockpile; its pantry inventory registers Water and Extract as Givable, so it is valid too.
  - **New static check** in `validate_connection_faces.mjs`: every building with target ports is a non-pipe BuildingSpec entity, every port is horizontal, and each OpenIn/OpenOut port and each liquid the plan uses is backed by the inventory goods Timber Pipes reads (`connection_content.mjs` `pipeTargetGoods`, mirroring the Manufactory, Restaurant kitchen, GoodConsumingBuilding, Hospital pantry, Grocery and bot-maintenance initializers). A negative test (a Bottom port, an OpenOut port on the Bathhouse) failed as intended.
- **Records:** `tools/asset-pipeline/measure_connection_faces.py` (plain Python, no Blender) measures each building's owning export (`validate_triangle_budget.OWNERS`) over its blueprint Size/BaseZ. It writes `outputs/connection-faces/<Template>.json` with the export SHA-256: 64 models, 9,694 flat faces. Each record also lists the faces the superseded depth-band rule accepted that sit on curves or slopes. Rerun it with `--data <generated Data>` whenever an export changes; generation refuses a stale record.
- **Flat rule** (all six faces):
  - No curve or slope, even partly: every covering surface within 0.35 of the cell plane has its normal within 5 degrees of the face axis and 1 degree of the covering mean.
  - One wall plane (depth band 0.05) covers at least 60% of the face.
  - Back faces never cover a face (they are culled in game).
  - No animated part in front. Glass is a surface (2026-10-26): flat window glazing qualifies, and a wall's plane may be its glazing or the wall the windows sit in. Lamp glass of wall lanterns never makes a wall curved.
  - **Rule pass after build 174** ("The fish hatchery also has walls which should accept power but don't"; "The Greenhouse has a lot of wall space which should allow power connections").
    - Glass exclusion dropped (it had rejected the hatchery headhouse windows and most of the Greenhouse).
    - Exterior cells are those a vanilla shaft fits in, per its occupation flags, so the hatchery porch (Floor) holds a shaft against the headhouse front.
    - Buildings with BaseZ > 0 get no ground-layer Bottom faces below their placement level.
    - The all-buildings power check now uses each building's own level (Coordinates.z + BaseZ), so the hatchery's bank-level walls are tested.
    - Shaft faces 5,653 -> 6,074 and wall faces 2,466 -> 2,923; pipe ports 1,971 -> 2,303. No face was lost anywhere except the hatchery's 36 unreachable below-bank Bottom faces.
    - Greenhouse walls 14 -> 47; hatchery walls 10 -> 16 (bank level: left side, back wall, two front faces beside the door).
    - The 45 curved test faces stay excluded.
    - Sheets: `outputs/review-sheets/hatchery-connection-faces-before.png`, `-after.png`, `greenhouse-connection-faces-after.png`.
  - Deviations from the requested numbers, decided on the measurements:
    - **Plane band 0.05, not 0.02.** Timber frames stand 0.03-0.04 proud of their infill on the Fishery, Hospital and crusher walls that hold the in-game-tested sockets. At 0.02 those sockets disappear.
    - **Parallel relief allowed on the rest of the face.** Requiring the whole covered area within 0.02 left the crusher with no face at all.
- **Exterior rule:** occupied cell; the neighbour is outside the Size or an open cell reached by a flood fill from outside. Faces toward the Entrance, door path cells, walkway openings, navmesh ends and water/sludge flow cells are skipped, as is the export's MAP_EDGE side.
- **Roofs:** a Top face only where the block is already Stackable in the families' blueprint (platformable terraces and decks). The step never changes blocks: `applyPlan` throws if it would, and the validator rejects any `Stackable` assignment in `connection_content.mjs`.
  - **Platformable flat roofs on every building (user, 2026-10-26: "A lot of buildings like the mines and whatnot have flat areas on their roofs, but don't allow placement of anything on top").** This is a design step, `tools/roof_deck_content.mjs`, run just before the connection step. It replaces the late-game-only `lategame_roof_decks.json`/`roofDeck`.
    - **Which roofs.** A roof cell qualifies when:
      - its Top face is flat on the export (one plane, no curve or slope, at a cell boundary);
      - the cell above is free, exterior and not an access cell;
      - nothing of the building stands in the middle of the cell above (0.31 in from each edge, so railings and trim on the edge do not count), probed along all three axes (`measure_connection_faces.py` `roof.blocked`);
      - no animated part, glass, smoke/steam emitter (`TemplateAttachmentsSpec`) or native prop is above.
    - **Generated list.** `tools/roof_decks.json` is written by `node tools/roof_deck_content.mjs --write <generated Data>`, never by hand. It holds the platformable cells, every excluded flat roof with its reason, and `freedAbove`.
    - **Freed cells.** `freedAbove` lists late-game registered cells over a flat roof that hold nothing. The registration marks a cell occupied whenever any part's bounding box reaches 0.15 into it, so railing loops and rooftop frames claimed empty terrace cells. A cell is freed only when its middle is empty, it sees the sky, and it is no door, emitter or prop cell. `lategame_building_content.mjs` leaves those 59 cells unoccupied (colliders follow). Footprints, models and triangle counts are unchanged.
    - **Walkability, the native approach.** All 33 vanilla Iron Teeth blueprints with a stackable block set `GenerateFloorsOnStackable` (platforms, overhangs, warehouses, barracks, rowhouses, BotPartFactory, HydroponicGarden). `AddEdgesAddedByStackable` then lays floor edges over each stackable block, so beavers can walk onto the roof from a stair, path or platform and build there. The step turns it on for every template with a stackable block: 23 changed, adding a floors-only navmesh spec (no edges) where none existed.
    - **Result.** 705 platformable roof cells on 46 templates, 364 of them newly stackable (structural pieces were already platformable). Roof shaft faces follow (the connection rule). No roof pipe ports, because valves are horizontal.
      - The four confirmed decks now have: LaunchPad 72 (was 66), MissionControl 65 (43), PrecisionMachineWorks 36 (36), ArchiveExcavation 3 (2).
      - Per-building table: `outputs/roof-decks-report.json`. Review sheets: `outputs/review-sheets/roof-decks-mines.png` and `roof-decks-industry.png`.
    - **Mines.** DeepMine gains its headframe deck (3 cells; 3 more sit under the animated winding gear). DeepDrill gains 4 front-terrace cells.
    - **Still not platformable** (the building's own registered blocks stand above): DeepDrill's derrick platform and the cells round its pump hut, DeepProcessor's raised decks, and DeepMine's hopper deck. All are covered by structure or have machinery in the middle of the cell.
    - **Validators.** New `validate_roof_decks.mjs` checks that:
      - the list is current;
      - every listed cell is stackable with a free cell above;
      - every flat roof open to the sky is platformable or excluded with a reason;
      - every stackable template has floors on.
      - The industrial, grocery and construction-material checks now accept a floors-only navmesh spec.
    - **Fixture.** `AllBuildingsAcceptance` adds "roof deck takes a Path, a 1x1 decoration and a Platform": the native BlockValidator, on up to three listed roof cells per building. Compiled, not run.
    - **Status icons.** Anchors are unchanged (they derive from the blocks, and `validate_status_icon_anchors` passes). The icon still sits 0.7 above the main roof, as on vanilla stackable roofs (Barrack, Warehouse, BotPartFactory), so things built on a roof can stand above it.
    - **Open.** In game: placement on the roofs and beavers reaching them by stairs. Every building with a stackable block now has walkable floors over it, including the research lab's terraces and the Fishery's and grocery's decks.
- **Undersides:**
  - Every occupied ground-layer cell that stands on ground or a platform gets a Bottom shaft face, met by a VerticalPowerShaft from below.
  - Measured-flat undersides over an open exterior cell get Bottom shaft faces and pipe ports. That covers overhangs (15 shaft faces, on DeepDrill, LaunchPad, PrecisionMachineWorks and FishHatchery) and flat ground floors (pipe ports only).
- **Generation:** `tools/connection_content.mjs` runs from `create_vertical_slice_content.mjs` after bot upkeep.
  - 38 powered templates get `TransputProviderSpec`: authored sockets first with their surviving directions, then generated faces.
  - 32 liquid templates get `BuildingPipeTargetPortsSpec` (the tank farm extends its `BuildingPipeSpec`). State is OpenIn, OpenOut or Open. Authored sockets (study, coolant, aquaculture, mixer, radiation, cryogenic) stay first and unchanged.
- **Counts (one of each):**
  - Shaft faces 6,655 -> 5,475: walls 2,463, roof 273, ground Bottom 2,724, overhang Bottom 15. Connectable (horizontal + Top) 2,736; largest is RocketAssemblyHangar at 250.
  - Pipe port faces 11 -> 1,968, horizontal only (valves are horizontal); largest is the Hospital at 168, then the reactor and CryogenicLiquefactionPlant at 113.
  - Roof faces (shaft / pipe):

    | Building | Shaft |
    |---|---|
    | LaunchPad | 66 |
    | Restaurant | 52 |
    | MissionControl | 43 |
    | Hospital | 36 |
    | PrecisionMachineWorks | 36 |
    | FishHatchery | 28 |
    | ReinforcedHydroTurbine | 8 |
    | ArchiveExcavation | 2 |
    | GroceryStore | 2 |

    No roof pipe ports: no Timber Pipes valve faces up or down.
  - Per building: `outputs/connection-faces-report.json`.
- **Reactor:** of its 512 original transputs, 42 sat on curved surfaces (3 or more distinct off-axis facet directions: the domed containment, round tanks and the rounded front edge) and 50 on slopes or bevels. Both groups are excluded now. 373 shaft faces remain (112 wall, 261 ground Bottom) plus 293 pipe faces. Review sheet: `outputs/review-sheets/reactor-connection-faces.png`.
- **Curved test cases** in `validate_connection_exports.py`, each covered by a curve or slope and never a connection face:
  - the reactor's rounded hall edge and corner pier;
  - the tank farm's round LOX tank (wall on three sides plus dome) and a hydrogen bullet;
  - the oil plant's barrel vault.
- **No pipes (no Liquid good):**
  - Powered: GroceryStore, CementKiln, StoneCrusher, SteelMill, RocketAssemblyHangar, MissionControl, TechnicalSchool, SmogScrubber, ReinforcedHydroTurbine.
  - Unpowered and dry: RadioactiveWasteVault, ObservationDeck, TownPlaza, both pits, all 18 structural pieces (no structural piece has a MechanicalNodeSpec).
- **Validators:** new `validate_connection_faces.mjs` and `asset-pipeline/validate_connection_exports.py` (re-measure, per-face planarity re-check, curved cases). Updated: radiation, cryogenic, construction materials, restaurant grid (power at z 0/2/4/5).
  - `validate_all -SkipBlender` in mirror `connections`: 41 pass, item-uses report only.
  - Earlier negative test (door face, non-stackable roof, crusher pipe) failed as intended.
- **Fixtures (compiled, 0 errors, not run):**
  - `LategameAcceptance`: "roof shaft connects" (skips buildings without a platformable roof); one generated ground-level pipe port per building beside the authored socket.
  - `FactoryTransportAcceptance`: reads the intake as `Ports[0]`.
  - The tested sockets of the crusher, kiln, mixer and quarries (`Transputs[0]`), research, hydro, Fishery and Hospital all remain.
  - The mixer's rear tank-tower face (6,4,0) Up is gone (diagonal braces, a slope). The fixtures agent rerouted `FactoryTransportAcceptance` to the (0,3,0) Up face.
- **Open:**
  - Promotion and build.
  - In-game checks of a roof shaft on a terrace, the generated pipe ports, and Bottom shafts from below.
  - `aquaculture_workbook.mjs` / `verify_aquaculture_workbook.py` list every port and need a rerun after promotion.

## Coal and Oil Power Plants: studies, exports and generators added; generated and validated in mirror `powerplants`, not promoted, built or tested in game (Claude Code session, 2026-10-22)

- **Design** (`frontier_progression.json` `powerPlants`; sizing table in `docs/progression.md` "Power plants"): Coal Power Plant 5,000 hp, 5×5×10, 3 workers, science 4,500 (T3), burns 1 Coal + 1 Water per working hour (`CoalFiring`); Oil Power Plant 20,000 hp, 6×6×9, 4 workers, science 11,000 (T4, +4 MachineCore gate), burns 2 CrudeOil + 2 Water (`OilFiring`). One coal plant runs a steel mill line (4,570 hp), three a mid-game district (12,520 hp); one oil plant runs the cryogenic fuel line (17,500 hp), three the whole launch program (56,000 hp).
- **Generator path:** the reactor's (Smelter manufactory + `WorkshopPoweredGeneratorSpec`); fuel is the recipe's native `Fuel` good (`RECIPE_FUELS` in `create_frontier_expansion_content.mjs`), water its only ingredient, no products. Output only while a worker works; bots allowed (open crews, Dangerous, bot wear 3x).
- **Fuel chains:** Coal and CrudeOil from the existing Deep Ore Processor (`DeepCoal`, `DeepOil`); no producer added. No refinery or refined fuel exists, so oil burns crude.
- **Art:** `lategame_CoalPowerPlant.py` (steel-clad boiler house on a concrete storey, coal bunker through the gable, riveted chimney to 9.9, open horizontal engine with flywheel SPIN_X and piston rod PISTON_Y) and `lategame_OilPowerPlant.py` (barrel-vaulted turbine hall, boiler tower with two stacks to 8.8, day tanks, fin-fan cooler fans SPIN_Z, pump coupling SPIN_X). Footprints end at the walls; door face .18 behind the front edge; shafts on wall faces only (63 / 71). Exported triangles 4,812 / 8,316 (ceilings recorded, class workshop 20k).
- **Integration:** `lategame_batches.json`, cost rows (`lategame_costs.mjs --write`), smog (coal one 12-tile disc 0.55, oil two 8-tile discs 0.3), sounds (Engine + PrintingPress / PaperMill, workshop driver), workforce, automation (pausable), asset catalog, exporter declared models, triangle budget, icons (`src/DeepFrontier/Art/Icons/*PowerPlant.svg`), localization, `validate_vertical_slice_content.mjs` power contracts. `audit_item_uses.mjs` now labels generator fuel as "Fuel: power generation" (EnrichedFuel's label changed too).
- **Checks passed:** strict z-fight 0 visible (frames 1/31/61/91), hidden geometry 0 culled faces exposed, grid audit 0 misses, canonical generation and full `validate_all -SkipBlender` in mirror `powerplants` (37 pass, item-uses report only; Coal 4 uses, CrudeOil 3), `validate_triangle_budget.py` 64 models.
- **Review:** `outputs/review-sheets/power-plants.png` (normal and closest zoom, grey review-only puffs at the registered smoke mouths).
- **Open:** canonical generation and icon rendering into the real Data, build, in-game check of output/fuel burn, smoke scale and placement. The icon run in the mirror rewrote `docs/art/reviews/2026-10-21-icons/expansion-*.png` through the docs/art junction (now include the two new icons).

## Moving-preview lag (Reactor): build 145 installed, measured in game (Claude Code session, 2026-10-23)

- **Cause (source + probe):** native `PositionedBlocks.TryGetBlock`/`HasBlockAt`/`HasStackableBlockAt` scan every block of an object; `BlockObjectAccessGenerator.IsAccessBlockedBySelf` calls it for every column and level it tests, so each placement change regenerated builder accesses in ~1 s for the 6,600-block Reactor. Each placement change also rebuilt and re-applied the preview navmesh object (~230 ms).
- **Fix:** `Scripts/PreviewNavMesh/PositionedBlocksIndex.cs` (per-instance coordinate -> first-index map on the immutable block array; exactly the native first match; objects under 64 blocks and any instance with duplicate coordinates keep the native scan) and movement deferral in `PreviewNavMeshCache.cs` (a held preview keeps its applied navmesh list until it rests 0.2 s at one placement; placement never reads the preview navmesh; PreviewPlacer and PositionedBlocks IL-verified).
- **Result (ms per frame, native -> shipped):** quiet (new game, Plains) Reactor moving 1,092 -> 18.8, still 1,094 -> 6.0, one swap of 242 ms when the mouse rests; busy ("asdf copy", 66 layers, colony running) Reactor moving 1,204 -> 22.2, still 1,155 -> 7.6, rest swap 263 ms. Launch Pad, Hangar, Steel Mill moving 6-25 ms (were 108-298). No exception or guard; memory peak 11.1 GB of 13. Game closed.
- **Remaining:** the rest swap is the native cost of applying ~32,000 wall edges for the Reactor (fewer occupied blocks would be a design change). The asdf colony was not very busy (28 world changes in 4.7 s during the Reactor run).

## Preview navmesh + construction-access caches (placement lag): build 144 installed, measured in game (Claude Code session, 2026-10-22)

- **Causes (measured, `PreviewCostAcceptance`, build 143):** per frame while a building tool is active, native code (a) re-applies the preview's navmesh object (Reactor 226 ms) and (b) regenerates construction-site accesses in `ConstructionSiteAccessible.OnPreviewSelect` -> `BlockObjectAccessGenerator.GenerateAccesses` (Reactor 1,045 ms). Highlighting 0.05 ms, block validation 1.6 ms, preview blocks 1 ms.
- **Fix:** `Scripts/PreviewNavMesh/PreviewNavMeshCache.cs` (navmesh list cached per placement; unmoved per-frame remove/add cancelled for single, blocks+navmesh-only previews; checked add/remove balance) and `PreviewAccessCache.cs` (accesses reused until the placement changes or terrain height/field/cutout, a regular navmesh update, a block set/unset or any finished/unfinished state change occurs). Both Harmony, `#if !UNITY_EDITOR`; IL of every relied-on native method and type (incl. iterators) is hash-checked at mod start.
- **Result (build 144, new game on "Deep Frontier - Plains", ms per frame, native -> shipped):** Nuclear Reactor 1,228 -> 6.3; Launch Pad 289 -> 1.7; Rocket Assembly Hangar 118 -> 1.3; Steel Mill 242 -> 1.4; Coal Power Plant 30 -> 0.8; Oil Power Plant 35 -> 0.8; vanilla Smelter 5.5 -> 0.2, EarthRepopulator 47 -> 0.7, DistrictCenter 6.6 -> 6.8 (district previews keep the native navmesh path). 53 buildings measured, 5 found no site on that map. No exception or guard in the log; private memory peak 11.2 GB (13 GB sampler ceiling). Game left closed.
- **Not tested by hand:** placing, cancelling and moving previews in normal play; reachability warnings after world changes while a preview is held still.

## Acceptance fixtures updated for the 2026-10-22 footprints: compiled, not run in game (Claude Code session, 2026-10-22)

- **Source of coordinates:** blueprints regenerated in mirror `fixtures` (identical to the promoted src Data at 18:04). Shifted buildings keep their former world cells: origin = former origin minus the local shift (Hospital (160,162), Restaurant (160,161), Fishery (159,162), crushers (149,145)/(155,145)/(150,155) Cw90, kiln (164,144), quarries (176,145)/(176,158)). Mixer, MaterialsLaboratory, Grocery and both pits keep their origins.
- **Changed drivers:** Hospital, Restaurant, Fishery (+Hatchery probe), AquaculturePipe (Fishery intake (4,7,0) → world (163,169)), Grocery/GroceryBelt/GroceryContinuity (rewritten for the Grocery Market: door walk, stair bay, balcony paths; the gallery walkway checks were stale since the market replaced it), Industrial, FactoryTransport (west belt lanes on the mixer's wall faces, pipe line at the first pipe port (6,4,0), shaft line from the (0,3,0) Up face via (159,164) and row y 165 to the pump at (168,165) since the braced tank tower lost its shaft face in the connection-face pass, cable anchor (6.9,4.9,3.8)), Mixer, Research, MineralPit, Lategame (freed cells from `tools/lategame_freed_cells.json`).
- **Freed-cell checks:** `Scripts/FreedCellProbe.cs` asks the native BlockValidator whether a Path and a 1x1 decoration (Shrub, or Brazier under an overhang) fit on each freed cell, before the driver builds beside it.
- **Checks passed:** incremental compile of the Scripts tree (0 errors), `validate_editor_guards.mjs`.
- **Open:** every launcher must be re-run after the next build, starting from the industrial chain (the shared base save "Reservoir acceptance - verified" holds the old industrial origins). The FactoryTransport lane/shaft topology and the Grocery stair route are derived from blueprint faces and the market registration, not yet seen in game.

## Industrial footprints end at the walls, no forced decor: meshes exported to src Data, blueprints not yet canonically generated, not built or tested in game (Claude Code session, 2026-10-22)

- **User rule:** no apron, paving, yard or loose prop on ground tiles beyond the front, side or back walls; each door's entrance is the open cell in front of the footprint edge. Functional parts stay, built with the lean kit.
- **Footprints (before → after; triangles before → after):**
  - StoneCrusher 6×7 → 4×4 (24,486 → 23,706)
  - CementKiln 9×9 → 7×5 (36,978 → 34,620)
  - ConcreteMixer 8×6 → 7×5 (24,736 → 24,478)
  - Sandstone/LimestoneQuarry 11×10 → 11×7 (31,952 → 29,953)
  - SandstonePit 5×5 → 5×4 (11,054 → 10,896)
  - LimestonePit 6×5 → 5×3 (13,633 → 8,944)

  Heights are unchanged. Ceilings were lowered in `triangle-budget.json`.
- **Removed:**
  - crusher: jack and stacked crates by the porch;
  - kiln: side workshop bench, rear cask, spare tyre with cradle, ash bucket/shovel/poker, rear tool rack;
  - mixer: stacked finished blocks;
  - quarry: forecourt stone step (artwork y 0..1), the supply bin overhanging the plinth's rear edge, and a spare sheave and timber stack that were buried in the plinth;
  - pits: both native barrels and the rear plank stack (pit `NativeBuildingPropsSpec` is now empty);
  - limestone pit: hand cart, side shelter and workbench.
- **Moved inside the wall line:**
  - crusher output bin: 0.70 deep, behind the y=2 edge; still chute-fed;
  - mixer: header tank and deck (−0.2 X), tray piers, cement hopper and its rear legs (−0.29 Y) and feed-tower roof eave;
  - quarry: rear mast posts, landing and collars, and the control room (−0.15 Y), so its rear windows end on the plinth edge. The ControlRoomDoor anchor moved to (3.37, 7.34, 1).
- **Kept (functional):**
  - crusher output bin (process);
  - mixer header tank (`WorkshopReservoirSpec` water display, on its own tower inside the footprint);
  - quarry water barrel and pump circuit (`WorkshopReservoirSpec`, on the building's own plinth inside the footprint);
  - sandstone pit front row: working hoist basket and sorting grate (process yard), with its native path cell (1,0,0).
- **Registration:**
  - `industrial_layouts.py` origins: crusher (−1,−2), kiln (0,1), quarry (0,−1). Entrances (1,−1,0)/(3,−1,0)/(1,−1,0).
  - `pit_layouts.py`: limestone origin (.57,−1), `approachFloor`.
  - `industrial_occupancy.mjs`; quarry seam rows 1..5 in `industrial_building_content.mjs`.
  - `pit_building_content.mjs` (`pitBlocks`, `approachFloor`, height-0 columns are free ground).
  - `construction_materials.json` sizes.
  - `pit_apron_components.BOUNDS`; legacy deck kept as `LEGACY_BOUNDS`.
- **Free ground:** new `tools/validate_freed_cells.mjs` writes `outputs/freed-cells.json`. It lists every freed cell (all outside the new footprints) and the open ground cells left inside the bounds, all ground-layer None, MatterBelow Any, no collider: kiln (0..1,0..1),(2,1),(4,1),(2,3); mixer (3,0),(4,0) [the former block stacks],(3,1),(4,1),(4,2),(6,2),(5,3),(0,4); limestone pit (4,0). Each is an in-game acceptance point: place a Path and a 1×1 decoration there.
- **Checks passed:**
  - strict z-fight at 0 visible (multi-frame); hidden-geometry audit 0 culled faces exposed;
  - wall faces re-measured and kiln smoke re-registered; motion checks for crusher, kiln and quarry;
  - sources-mixer and sources-pits (`validate_pit_sources.py`: an edge door's approach is native ground, so no authored floor in front);
  - `test_pit_aprons.py` (now against the current recipe), `test_industrial_door_mounting.py`;
  - exported door culling, all 9 industrial doors: 0 failures.
  - In mirror `industrial`, canonical generation passes, as do exports-industrial, exports-pit (updated for the new pit contracts), exports-preview_budget, model-bindings, freed_cells, construction_materials, audit-building-assets and content validators.
  - `validate_triangle_budget.py` passes for all 62 models.
- **Open:**
  - Real `src/DeepFrontier/Data` holds the new meshes (new origins) with the old blueprints until canonical generation is promoted.
  - Acceptance fixtures still name the old cells: `IndustrialAcceptance.cs` walk targets (2,1,0)/(4,0,0)/(1,1,0) and the deck/shaft test cells, `FactoryTransportAcceptance.cs` port (7,5,0), `MineralPitAcceptance.cs`.
  - `test_industrial_door_components.py` passes for all industrial doors but fails on ReinforcedHydroTurbine: its saved door (scene rebuilt 16:55 by the hydro family) lacks 4 native faces of its recipe.
  - Not built, not checked in game.

## Triangle budget and no forced decoration, civic/waterside/research/hydro/grocery: scenes rebuilt, exported to outputs, not promoted, built or tested in game (Claude Code session, 2026-10-22)

- **Scope:** FisheryWorks, MaterialsLaboratory, ReinforcedHydroTurbine, FishHatchery, Restaurant, Hospital, GroceryStore.
- **Result (exported finished model, triangles / vertices):** FisheryWorks 774,461 → 37,467 / 1,675,492 → 79,084; MaterialsLaboratory 473,246 → 31,695 / 1,021,797 → 64,760; ReinforcedHydroTurbine 267,678 → 22,029 / 577,232 → 46,045; FishHatchery 218,225 → 20,238 / 472,455 → 42,605; Restaurant 164,002 → 25,934 / 354,035 → 54,890; Hospital 142,640 → 24,176 / 306,967 → 51,526; GroceryStore 63,205 → 30,101 / 137,492 → 63,908. Total 2,103,457 → 191,640 triangles. Tables: `outputs/triangle-budget/before-exports.json`, `after-exports.json`. Ceilings are recorded in `tools/asset-pipeline/triangle-budget.json`.
- **Hidden share (orbit-ray audit, before → after):** Fishery 67.5% → 31.3%, MatLab 66.6% → 30.1%, Hydro 64.8% → 32.9%, Hatchery 50.2% → 23.4%, Restaurant 56.0% → 40.4%, Hospital 53.5% → 40.9%, Grocery 41.9% → 37.3%. The remaining hidden share is mostly back sides of thin parts and faces seen only from below. 0 culled faces exposed. Audits: `outputs/triangle-budget/hidden-before/`, `hidden-after/`.
- **How (shell build):** no bevel modifier, the lean fastener kit from `industrial_budget.py`, and an opt-in enclosed-face cull. The cull is `enclosed_cull.py` plus `Geometry._cull_enclosed` in `frontier_architecture.py`, set per model by `SHELL_MODELS`. It removes faces covered exactly by convex primitives. Faces inside declared room volumes and small faces are only proposals, kept or removed by ray verification. Moving parts get the exact cull only. Door components and every `building_portal` face are never culled (they still occlude): the first pass had culled 4 hidden native faces from each door component and some inline portal faces (MaterialsLaboratory), which failed `test_industrial_door_components.py` for the hydro door; Hydro, Restaurant, Hospital, MaterialsLaboratory and Hatchery were regenerated, and all door objects now equal their recipes (37 faces). Sub-pixel scratches were removed. Coplanar overlaps that the bevel had masked were fixed at source.
- **Footprints (decoration and aprons beyond the walls removed):** Hospital 12x11 → 12x9 (canopy trimmed to a vanilla-sized overhang); MaterialsLaboratory 10x9 → 10x8; Restaurant 10x8 → 9x7 (balconies kept); FisheryWorks 12x10 → 11x8; GroceryStore 9x7 → 9x6 (water tank and dock goods removed). FishHatchery 8x8 and ReinforcedHydroTurbine are unchanged. Kept as functional: restaurant dining balconies, fishery basins/wheel/cascade/water tanks/crane, hatchery docks/pens/header tank, grocery stocked stalls and hoist. Freed cells are checked against the native Path and Shrub.IronTeeth placement rules: `validate_freed_cells.py` → `outputs/triangle-budget/freed-cells.json`.
- **Registrations:** smoke, civic wall faces and Hatchery migration metadata were re-registered after the scene saves (`carry_hatchery_metadata.py`).
- **Checks passed:**
  - strict z-fight audit: 0 visible on all seven;
  - exports-fishery, hatchery, grocery and civic;
  - restaurant grid;
  - `validate_triangle_budget.py` (62 models);
  - map validate: plains-hard, plains and terraces;
  - `test_industrial_door_components.py` (7 scenes, 10 doors) and `check_exported_door_culling.py --game-blend` for Hydro, Hatchery, Restaurant, Hospital and Fishery, 0 failures (`building_components.EXPORT_OFFSETS` for FisheryWorks updated to its new layout origin);
  - full canonical generation in mirror `tribudget-civic` and `validate_all -SkipBlender` there: all pass except the report-only item-uses audit (exports-civic re-checked after the review archive was refreshed from the regenerated scenes).
- **Open:**
  - Promotion into Data and canonical generation (blueprints, layouts, footprints) are pending.
  - C# acceptance fixtures need updating for the new sizes and entrances: Hospital, Restaurant, Fishery, Grocery and Hatchery.
  - Construction stages are still byte copies of the finished model.
  - Not built, not checked in game.
- **Review:**
  - `outputs/review-sheets/triangle-budget-civic-<Model>.png`, `triangle-budget-research.png`, `-hydro.png`, `-grocery.png` and `no-forced-decor-civic.png`: before | after | difference at normal and close zoom.
  - Archived in `docs/art/reviews/2026-10-22-triangle-budget/`.

## Triangle budget, industrial family: scenes regenerated and exported into src Data, not built or tested in game (Claude Code session, 2026-10-22)

- **Result (exported finished model, triangles / vertices):** CementKiln 476,610 → 36,978 / 1,027,992 → 75,771; ConcreteMixer 457,856 → 24,736 / 989,431 → 51,899; StoneCrusher 343,168 → 24,486 / 737,707 → 50,828; Sandstone/LimestoneQuarry 431,362 → 31,952 / 928,249 → 67,001; SandstonePit 204,144 → 11,054 / 440,437 → 23,966; LimestonePit 259,898 → 13,633 / 561,165 → 29,163. Construction stages are the same file. Ceilings recorded in `tools/asset-pipeline/triangle-budget.json`.
- **How:** `industrial_budget.py` (shared kit, same signatures as the industrial_geometry/reference_details helpers) and `industrial_kit.py` (the industrial family's fastener style). No bevel modifier (`industrial_budget.BEVEL`, used by `render_reference_studies.py` and `rebuild_components.py`); opt-in enclosed-face cull on; fasteners are one head with only the outward cap, two per collar plate, square heads set diagonally; 4–12 sides on small round parts, 24–32 on drums/tyres; sub-pixel scratches/checks removed; fewer, rounder rocks; buried parts removed (bearing base bolts, pit sheave-plate bolts, crusher middle/rear collar bolts). All six scenes regenerated from the generators (regeneration of the unchanged generators had matched the saved scenes object by object, except pit-architecture UV strips).
- **Kept:** all animated nodes and tracks (quarry 53, kiln 12, crusher 5, pits 3, mixer 2), `#Slot` nodes, doors, glass slots, `static_mesh_merge.py`. Smoke registration unchanged; wall faces: crusher/kiln identical, mixer +2 and quarry ±6 faces, all between two `All`-occupied cells (not exposed).
- **Checks passed:** strict z-fight audit 0 visible (kiln frames 1/61/121/181, quarry 1/120/220/350, others 1/31/61); `audit_hidden_geometry.py` 0 culled faces exposed; sources-mixer, sources-pits, motion `--check-only` for crusher/kiln/quarry (`quarry_validation.py` now skips the native barrel's empty root, which failed before this pass too); exports-industrial, exports-pit, exports-preview_budget, model-bindings; `validate_triangle_budget.py` passes for these seven; `test_pit_aprons.py` (updated: no bevel). Review: `outputs/review-sheets/triangle-budget-industrial.png` and `-<Model>.png`.
- **Doors:** `test_industrial_door_components.py` had been stale since the 2026-10-21 grid pass (last pass 10-21 13:37; already noted in `docs/art/grid-alignment.md`). It compared each current recipe with its legacy-anchor recipe at absolute coordinates, but every door anchor had moved (the pit doors again today, .08 in Y). It also searched the architecture for legacy door faces, which the component migration had moved into `<Model>.Door.<Id>` objects, and it did not know the quarry outer-bay cheek panels. Measured: all ten current recipes equal their legacy native inserts (34 faces, UVs, materials) under exactly the anchor translation. Every saved door object equals its current recipe face for face, with exact native UVs and 0 faces culled. The test now checks those three things. `industrial_facades.py` was last changed 2026-10-21 13:34, before that pass, and is unrelated. Passes for 7 scenes and 10 doors.
- **Door checks:** `check_exported_door_culling.py --game-blend <Model>-Game.blend` now reads merged exports: each door's evaluated triangles are found in the StaticMerged nodes, and every triangle must be present. All ten doors pass, 0 failures (crusher, kiln, mixer and pits 3,600 isolated + 720 seam probes each; quarry 14,400 + 2,880; hydro 3,600 + 720). Also passing: `test_industrial_door_mounting.py`, the pit 50-sample door approach, and an approach strip (135 headroom rays per door) that is identical before and after.
- **Open:** not built, not checked in game.

## Radioactive Sludge Recovery Pump: cantilevered intake for natural straight banks; exported to outputs, not promoted or built (Claude Code session, 2026-10-24)

- **Change:** the back-row piers and brackets under the intake deck are gone. Four joists and a buried edge beam cantilever the grating from the house wall, so on footprint row 2 only the intake cell (1,2,0) is a block, and it overhangs the water like the vanilla DeepBadwaterPump. Occupancy row 2 is `+#+`. Generated blocks for row 2: Any/None, Air/All, Any/None. WaterInputCoordinates is (1,2,-1). Before, the piers made the neighbouring back-row cells need ground, so the pump fit only a one-cell water notch, which needed dynamite.
- **Unchanged:** INTAKE, PIPE_OUTLET, the radiation specs, the footprint rule, and the 0.15 inset registration.
- **Map sites (no dynamite):** taken from the `prepare_deep_frontier_map.py plan` proposals. plains and plains-hard are at (128,154,3) Cw270, lakes at (105,146,3) Cw0, terraces at (88,172,10) Cw0. In the mirror, `validate` reports the pump sites OK on all four maps; the only errors there are FishHatchery water depth, from the hatchery change. `create_all_buildings_sites_map.py --check` is still valid.
- **Checks:** strict z-fight 0; culled faces 0 exposed; export; connection faces re-measured; mirror `validate_all -SkipBlender` 44 pass, 1 report-only. Triangle ceiling is 3,476 triangles / 6,552 vertices. Sheet: `outputs/review-sheets/sludge-pump-intake.png`.
- **Open:** not built, not placed in game.

## Bathhouse bathers and pool steam; Town Plaza fountain and native statue: exported to outputs, not promoted or built (Claude Code session, 2026-10-22)

- **Bathhouse:** 12 native visitor slots (`#Slot#Spot0-11`, TransformSlotInitializer `Sitting`, WaterSlot false, FixedSlotManager): 6 seats in the outdoor plunge pool (filled first; native SlotManager takes the first unassigned slot in hierarchy order), 6 inside the closed hall (native FixedSlotManager requires a slot per visitor, so none can stay slotless). Evidence: vanilla MudBath.IronTeeth (Seat/Sitting, WaterSlot false); WaterSlot would snap to the world water map (TransformSlot.MoveSlotToWaterLevel), and the pool water is the model's own surface. Two SteamEngineSmoke emitters over the water join the existing EnterableParticleControllerSpec (steam while bathers are present). `frontier_progression.json` slotAnimation `Sitting`; exporter `bathhouse_slots`.
- **Town Plaza (v3, after the hand-modelled fountain was rejected):** the shipped Folktails `FountainOfJoy` model as a native prop (scale 0.6 on a 3x3 concrete plinth that keeps the fountain tiles occupied) with its own FountainWater surfaces, plus the vanilla `FountainOfJoyWater` effect (spray and bucket pour from the model's own bucket) at its vanilla attachment point, scaled with the model (`fountainSpray` emitter kind in lategame_kit / vanilla_smoke.mjs, non-polluting in smog_content.json; EnterableParticleController). Its Folktails materials are registered for Iron Teeth in `MaterialCollection.DeepFrontierLategame` (lategame_building_content.mjs). The custom engineer statue is replaced by the shipped `BeaverStatue.IronTeeth` native prop (scale 1.4). Model 6,002 triangles + 2,526 native props (ceiling 9,520 before). Sheet: `outputs/review-sheets/town-plaza-fountain-v3.png`.
- **Checks:** strict z-fight 0, culled 0 exposed, export, full `validate_all -SkipBlender` in the mirror (37 pass, 1 report-only), triangle ceilings recorded. Sheets: `outputs/review-sheets/bathhouse-bathers-steam.png`, `town-plaza-fountain-statue.png`. Not seen in game: bather depth, steam scale, statue facing.

## Late-game: no forced decoration, footprints end at the walls; exported to outputs, not promoted or built (Claude Code session, 2026-10-22)

- **Removed** (per building in each module's docstring): all native plant props, planters, loose barrels/drums/casks/crates/stock and post lamps; yards, aprons, porches and forecourts outside the walls. Kept as functional: cooling basins/race/intake (reactor), launch pad deck, loading bay (cryo), drum dock and jib (uranium), crane yard machinery (precision works), crane runway and pond pump (refinery), sieving shed (archive), plunge-pool court (bathhouse), plaza paving with fountain/bandstand/statue/flags, observation deck overhang, bund (tank farm), track and gate (waste export), water structures.
- **Footprints:** FertilizerWorks 9x8→9x6, FoodPackagingWorks 10x8→10x7, PublicHealthLab 8x8→8x6, Greenhouse 9x7→9x5 (door now in the pavilion podium face), TechnicalSchool 11x6→11x5, RocketAssemblyHangar 12x12→8x9, RadioactiveWasteVault 13x12→9x10, DeepMine 12x11→10x11 (understructure core unchanged). Mechanism: module `GRID_ORIGIN` (render_lategame_studies.apply_grid_origin) and `lategame_kit.shifted`.
- **Freed cells:** `tools/lategame_freed_cells.json` (record_freed_cells.py); `tools/validate_lategame_freed_cells.mjs` checks inside cells are Occupations None / MatterBelow Any / no collider and writes the in-game acceptance points to `outputs/lategame-freed-cells.json`.
- **Data:** late-game cost rows rewritten by `lategame_costs.mjs --write` (PublicHealthLab, TechnicalSchool, RocketAssemblyHangar, SteelMill, ArchiveExcavation changed); triangle ceilings lowered (no model went up).
- **Checks passed:** strict z-fight 0 visible (30), culled faces 0 exposed, exports-lategame, model-bindings, preview_budget, freed cells, radiation/smog/workforce content, full `validate_all -SkipBlender` in mirror `tribudget-late` except exports-pit/exports-research (other families). Generation there needed a scratch-only bypass of the stale MineralQuarry wall-face record (industrial, in progress). Map variants validate OK.
- **Sheets:** `outputs/review-sheets/no-forced-decor-lategame.png`, `-2`, `-3`.

## Triangle budget, late-game and structural: scenes rebuilt and exported to outputs, not promoted or built (Claude Code session, 2026-10-22)

- **Result:** 48 models (30 late-game, 18 structural) from 1,972,374 to 569,517 finished triangles (vertices 4,232,816 to 1,088,709). Reactor 154,344 → 36,346, Uranium plant 135,180 → 37,316; every model is under its target (grand ≥90 tiles 40k, ordinary 20k, small/structural 8k). Table: `outputs/triangle-budget/lategame-before.json`, `lategame-after.json`; ceilings recorded in `tools/asset-pipeline/triangle-budget.json`.
- **How (by construction):** `render_lategame_studies.budget_shading` keeps the 1.2 cm bevel only on edges ≥0.5 long between faces ≥0.1 deep and not between curved facets, and smooth-shades by angle (37°); enclosed-face cull on (`CULL_ENCLOSED`). Kit: 16-side defaults, hoop/host check in `band()`, `stud()` (20-triangle bolt head) replacing rivets, light valve wheel, own 8/12-side `pipe_run`, sparser grating. Modules: literal side counts ≥20 roughly halved, reactor/uranium detail trims. Structural: `fastener()` replaces `steel_bolt`; structural models build with no bevel and the cull (`render_reference_studies.py` shell set).
- **Kept:** registrations byte-identical to before (occupied, doors, wall faces, emitters; hashes only), animated parts and names, pipe sockets, glass, static merge.
- **Checks passed:** strict z-fight 0 visible on all 48 (source overlaps the old bevel had masked were fixed at source), `audit_hidden_geometry` 0 exposed culled faces (16,436 checked), sources-structural, exports-lategame/structural/preview_budget and model-bindings in mirror `tribudget-late` after canonical generation, full `validate_all -SkipBlender` there (35 pass, 1 report-only).
- **Review sheets:** `outputs/review-sheets/triangle-budget-lategame.png`, `-2`, `-3`, `-4`. Visible change is texture-strip variation (native atlas strips are picked by face index) and slightly rounder smooth-shaded cylinders.
- **Open:** construction stages are still byte copies of the finished model (doubles memory); promotion into Data, build and in-game check pending.

## Load-time memory: cause found, mesh release verified through full loads, build 139 installed (Claude Code session, 2026-10-22)

- **Cause (decompiled Timberborn.PrefabOptimization, traced in game):** `BottomBarPanel.Load` builds one tool preview per placeable blueprint during the game-scene load. Each blueprint goes once through `PrefabOptimizationChain.ProcessPrefab`: Timbermesh import, AutoAtlasing (`Object.Instantiate(sharedMesh)`), VertexColor (`Object.Instantiate`), MergeMeshesByMaterial (`MeshBuilder.Build`). No step destroys the mesh it replaces, so every renderer leaves 3 orphaned full copies until the next scene change. Every Deep Frontier `ConstructionStage0.Model.timbermesh` (62 files) is byte-identical to its finished model, so each building is imported twice. It is not the save, the radiation code or the 66-layer height: a new game, the asdf copy and a 33-layer save spike at the same point.
- **Fix:** `Scripts/PrefabMeshRelease.cs` (Harmony, verifies the native chain and 5 optimizers). It destroys meshes replaced during a run that the finished prefab no longer uses, never meshes of the input prefab or an earlier prefab (throws instead). Byte-identical models in one prefab share the finished meshes, matched by import node index (throws on any mismatch). It runs a full GC after each run that released at least 100k vertices, and between steps of models of at least 200k vertices. Measured to the 259th preview (FishHatchery): preview cost 3.2 GB -> 1.7 GB; FishHatchery Unity allocation +211 -> +31 MB; 8,619 meshes (13.8 M vertices) released, 1,209 shared.
- **Full loads at a 13 GB ceiling** (GiB private; each loaded run also ran 180 s of game time; `outputs/memory-load-<label>.csv/.log`). No release or sharing guard tripped on any blueprint:
  - Deep Frontier disabled, other mods unchanged: asdf copy (66 layers) peak 9.31, steady 9.1; 33-layer save peak 8.34, steady 8.2.
  - Build 138 (old models + release): asdf copy peak 11.88, steady 11.75, working set up to 7.7. The new game loaded, then the test harness threw (`AcceptanceLoadingIssues` read `LoadedSave` in a new game; fixed in 139).
  - Build 139 (industrial meshes after the art cuts + release): asdf copy peak 11.28, steady 11.0; new game on the 66 map peak 10.92, steady 10.6.
  - Build 139 with the release switched off (`-deepFrontierKeepPrefabMeshes`, test only): both runs passed 13 GB during the load and were stopped. The build-132 user session without the release sat at 20.75 GB private.
  - Build 140 (all art cuts promoted, 1.79 M finished triangles, was 6.68 M; + release): asdf copy peak 10.09, steady 9.99, working set 7.0, load 84 s (139: 163 s); new game peak 9.79, steady 9.63. No guard tripped. Without the release (test switch): asdf copy peak 11.87, steady 11.68, so the release still saves about 1.8 GiB.
- **Remaining Deep Frontier cost (140):** about 0.8 GiB above the Deep Frontier-disabled baseline (9.31 on the asdf copy).
- **Remaining Deep Frontier cost (139):** about 2 GB above the Deep Frontier-disabled baseline. The late-game, structural and civic art cuts are not promoted yet. The duplicate `ConstructionStage0` models are written by the exporters.
- **Test tools:** `tools/start_memory_load.ps1` (sampler + `-deepFrontierLoadAcceptance` with `-deepFrontierLoadSave <path>` or `-deepFrontierNewGame user:|builtin:<map>`, `-deepFrontierSaveAs`, `-Trace` for `-deepFrontierMemoryTrace`, `-KeepPrefabMeshes`, `-CeilingGB`); `Scripts/MemoryLoadProbe.cs`, `Scripts/MemoryTrace.cs`. Test save copies live in `ExperimentalSaves/Memory Test`. Logs: `outputs/memory-load-*.log/.csv`.

## Pit door approach and Hatchery gallery routes: source fixed, pit meshes re-exported, not promoted or built (Claude Code session, 2026-10-22)

- **Pits:** the native Barrack door insert (component `Door.PitStoreDoor`) was anchored at Y=1.06, so its opaque recess (Y 1.105–1.136) and lintel stood inside a 0.15 body at the idle point Y=.98. `industrial_door_components.py` now anchors it at Y=1.14 (0.14 behind the y=1 tile edge, inside the column/shoulder reveal). Only that component was rebuilt in both ReferenceStudy scenes; idle, LocalAccess and the door cell did not change. The pit meshes in `src/DeepFrontier/Data/Buildings/Metal/{Sandstone,Limestone}Pit` were re-exported. Strict overlap audit: 0 visible. Review sheet: `outputs/review-sheets/pit-door-approach-before-after.png`.
- **Hatchery:** the raised bank aprons (wearing top Z1.020, which clears the measured terrain at Z1.010) cannot meet the deck-gallery tolerance. `hatchery_structure.ACCESS` routes now cover only the water-side decks and reject bank cells explicitly. The scene and mesh did not change.
- **Checks passed:** sources-pits, sources-civic, exports-pit/hatchery/civic/fishery/preview_budget, model-bindings. `check_exported_door_culling.py` cannot read merged exports: it needs separate `.Architecture`/`.Door.*` nodes, which `static_mesh_merge.py` now joins.

## Placement-preview lag: exports and scripts staged, not promoted or tested in game (Claude Code session, 2026-10-22)

- **Cause (source evidence):** native `PreviewPlacer.ShowPreviews` runs every frame while a building tool is active. Each frame it removes and re-adds the preview to the preview services (all blocks; the preview navmesh object is rebuilt and applied twice), validates every block two or three times, re-highlights every renderer and material slot twice, and calls every `IModelUpdater`/`IPreviewSelectionListener`. Placed buildings do this once. Deep Frontier buildings are 20-100x vanilla in occupied blocks (SteelMill 538, NuclearReactor 2,543; vanilla Smelter 24) and were up to 13x in renderers (FisheryWorks 333; largest vanilla 26).
- **Exports:** `tools/asset-pipeline/static_mesh_merge.py` joins static parts (glass kept in its own nodes; rails grouped by opening). Called by `export_industrial_models.py` and `export_lategame_models.py`. Re-exported to outputs/*-integration: Restaurant, FisheryWorks, FishHatchery, Hospital, ReinforcedHydroTurbine, MaterialsLaboratory, GroceryStore. `compare_merged_exports.py` shows the same triangles per material; renderers per model 162->47 (Fishery), 128->53 (Restaurant), 98->39 (Hospital), 83->34 (hydro), 61->27 (Hatchery), 43->26 (Grocery), 42->21 (MatLab). Metal-family exports (quarries, kiln, crusher, mixer) not re-run: that exporter writes them straight into src Data.
- **Scripts:** per-frame allocations and node rewrites removed from BuildingWalkway, PlatformDeck, AdaptiveSupports (+validator), WaterSitePreviewMarkers, WaterDepthPreviewValidator, MapEdgeSite, HydroTurbine validator. New probe `PreviewCostAcceptance.cs` (`tools/start_preview_cost.ps1 -Label <x>`).
- **Checks:** new `validate_preview_budget_exports.py` (ceiling 5x/4x vanilla max renderers/slots) and `validate_preview_components.mjs`. Scratch mirror `previews`: canonical generation + research/hydro promotion, every export validator, model bindings, all `validate_*.mjs` and the asset audit pass; Scripts compile 0 errors.
- **Open:** the block-driven native navmesh/validation cost is not changed (needs a design or Harmony decision). Nothing measured in game.

## Radioactive water and soil: source only, not built or tested in game (Claude Code session, 2026-10-22)

`src/DeepFrontier/Scripts/Radiation/RadiationSoil.cs` changes how radioactive water treats soil; `docs/radiation.md` has the details.
- **Moisture:** radioactive water no longer irrigates. A Harmony prefix makes the native moisture tasks see contamination b + r.
- **Irradiated banks:** the native soil-contamination kernels on a shadow put irradiated ground around radioactive water, up to 7 tiles.
- **Rinsing:** clean water at any depth clears stored soil radiation at the native recovery rate of contaminated soil (0.006 per tick, 0.192 per game hour): fully irradiated ground loses its tint after 5.0 h and reaches 0 after 5.2 h. Banks are a transient native-pattern layer read as max(soil, bank); they clear the same way once the water is clean. Under radioactive water the exchange is conserved.
- **Plants:** irradiated ground (stored soil or bank at 0.05 or more, where the tint starts) kills plants at once through native `LivingNaturalResource.Die`.
  - It acts the tick the ground turns irradiated, and when a plant is planted or spawns there.
  - Natural spreading skips irradiated ground (spawn validator).
  - `RadiationFloraDose` is retired. Its saved dose is read and discarded.
  - Canonical generation in the mirror is currently blocked by an unrelated error (FisheryWorks smoke emitters registered on a different scene). The validators pass read-only against the real Data, which still holds the old warning text until the next generation.
- **Saves:** no new save data.
- **Exception saves (build 145 crash):** the native exception saver (marked by `TickOnlyArrayService._forceAllowAccess`, writing without finishing the tick) now gets the last completed tick's snapshot and never throws.
  - Normal mid-tick saves still throw.
  - Snapshot saves load leniently: cells whose geometry changed are dropped, r is capped at 1 − b, and both are logged.
  - Not verified in game.

**Verified:**
- the whole Scripts tree compiles with 0 errors;
- the shipped kernels and the exchange ran in the game's Mono 6.13 (`outputs/radiation-soil-harness/harness-result.txt`);
- generation and all 17 node validators pass in the `soil` scratch mirror.

**Not verified:** anything in game, including whether the Harmony `ref` on the `in` parameter applies.

**0.5% radiation cutoff (same session, source only).**
- `RadiationTuning.DetectionLimit` is 0.005 and is the only water-share threshold.
- `Rescan` removes a final share below it once that share stops growing.
- Every reader treats a share below it as 0 (`Detected`). Pumps have no second resume threshold.
- The Radioactive Tide adds 1% of the source water (`SourceRadioactiveShare`), on both the vanilla and the Moddable Weathers paths.
- Compiles with 0 errors.
- In the mirror, `validate_all -SkipBlender` gives 31 passed, 1 report-only and 2 failed: `exports-hydro` and `exports-research`, both rail geometry assertions unrelated to this change.

## Contamination Sensor detects radiation: source written, compiled and statically validated, not built or tested in game (Claude Code session, 2026-10-22)

The native Contamination Sensor now has a per-sensor **Measures** choice in its panel: **Badwater** (native, the default), **Radiation** (the radioactive share of the measured column) or **Any contamination** (badwater + radioactive share). Each is rounded to the native 1% precision and compared with the native threshold and mode, and drives the native automation output.

- **Code:** `Scripts/Sensors/`. `ContaminationSensorSubstance` is a TemplateModule decorator on native `ContaminationSensor`, saved under `DeepFrontier.ContaminationSensorSubstance`; a save without that key loads as Badwater. `ContaminationSensorPatches.cs` is one postfix on the private `GetContamination(floor)`, applied after `Verify()`. `ContaminationSensorPanel.cs` adds a native Dropdown and the "Radiation: x%" readout. Radiation is read through `IRadiationService` only; its new `SavedStatePending` lets a sensor use its saved radioactive share at `AutomationRunner.PostLoad`, before the saved radiation is applied.
- **Content:** `tools/contamination_sensor_content.mjs` adds 6 localization rows, wired after `radiation_content.mjs`. The sensor blueprint, icon and model are not patched. The native evidence is in `tools/automation_content.json` `nativeTransmitterExtensions`, and `tools/validate_contamination_sensor.mjs` checks it.
- **Checks:**
  - The whole Scripts tree compiles with 0 errors (`outputs/contamination-sensor-compile`).
  - `Verify()` passes against the shipped 1.1.2.8 DLLs in a reflection harness, and a negative test fails as intended.
  - Generation and the validators pass in the `sensor` scratch mirror.
- **Not verified in game:**
  - existing sensors still reading badwater;
  - Radiation and Any triggering and sending the native signal;
  - the panel layout;
  - save/reload;
  - linked buildings responding.

## Builds 122–124 (Claude Code session, 2026-10-22)

- **122:** the seven late-game buildings and three wellbeing attractions integrated. It crashed at mod loading: with Moddable Weathers enabled, re-patching `HazardousWeatherUIHelper` re-ran its throwing transpiler.
- **123:** one-fluid radiation swapped into `src` (the two-layer set is backed up in the session scratchpad as `radiation-two-layer-build122`). The hard map's spring writes native `WaterSource` strength. The vanilla tide patches are skipped when Moddable Weathers is loaded. Staging now removes files deleted from src, but keeps the assets that the Create Materials step authors. Create Materials re-imports textures and rewrites materials only when they changed. New `validate_editor_guards.mjs` (dependency-mod code must sit inside `#if !UNITY_EDITOR`; the dotnet check cannot see this).
- **124:** radioactive zombies (`Radiation/RadioactiveZombie*.cs`): MovementSpeed -0.8 (vanilla contaminated -0.7; game floor ×0.25), 2× Hunger and Thirst, no work, yellow tint, infected walk, and an 8-day untreated countdown with an alert under 2 days. The Moddable Weathers tide bridge is in `Scripts/RadioactiveTide/ModdableWeathers` (its own asmdef). `DeepFrontierBatchBuild.PackageOptionalAssembly` installs it as `Scripts/DeepFrontier.ModdableWeathers.dll.ModdableWeathers.optional`, which Moddable Timberborn loads only when Moddable Weathers is enabled. With Moddable Weathers loaded and the bridge missing, the tide configurator now throws.
- **Verified:** 124 installs (623 hashes match, no plain bridge DLL). Startup with the user's mod list logs "Loaded 2 optional DLL(s)" and no exceptions.
- **Not verified in game:** zombies, the Moddable Weathers tide (settings dialog, emission, save/reload), one-fluid radiation, and all new buildings.
- **Agent testing:** use `tools/scratch_mirror.ps1` (AGENTS.md), never a copied repo.
- **Docs:** `docs/radiation.md` still says -50% for irradiated movement, and it has no zombie or Moddable Weathers section.

## One-fluid radiation staged for build 123, not in src (Claude Code session, 2026-10-22)

Per the user's design decision, radiation becomes one mixed fluid: each native water column is fresh + bad + radioactive. The separate sludge fluid, its simulation and its mesh are deleted.

The new file set is in `outputs/radiation-onefluid/`; `src` still holds the two-layer version for build 122. The staged set covers:
- `Radiation/`;
- the Meltdown and RadioactiveTide call sites;
- content, validator and tide content (`tools/`);
- `docs/radiation.md`;
- the invariant harness (`harness/`).

**Checks:**
- The whole Scripts tree with the staged files swapped in compiles with 0 errors (`outputs/radiation-onefluid-compile`).
- Against the shipped DLLs, the only errors are the expected CS0122 errors.
- The harness runs the shipped native water tasks in the game's Mono and passes. It also found that the native contamination kernels themselves can push b + r over 1, in thin films and in diffusion.
- Staged content applied to a scratch data copy passes the staged validator.

**Saves:** radiation save version 3, with explicit conversion of version 2 (build 122) and rejection of version 1.

**Not verified:** anything in game.

## Build 122 integration of ten late-game studies: source and exports done, not generated into real Data or tested in game (Claude Code session, 2026-10-22)

Seven studies (SteelMill, ArchiveExcavation, CryogenicTankFarm, SmogScrubber and the three radiation buildings) and three wellbeing attractions (Bathhouse, TownPlaza, ObservationDeck) are now real buildings, all listed in `tools/lategame_batches.json` and generated through `lategame_building_content.mjs` (registration blocks, entrance, wall-only shafts, colliders, own construction stage, native props, animation, vanilla smoke).

**Buildings** (cost from the late-game rule; tier in brackets):
- **Steel Mill** (Smelter template, Metal 40): Flux, HighGradeSteel, Alloy; 6 metallurgist specialists, beaver-only, Extreme danger; 2,500 hp; 4,500 science [T3]. Two smoke flues pollute (r10, 0.45). Fixes the review finding that nothing made HighGradeSteel/Alloy.
- **Archive Excavation** (BotPartFactory template, Science 46, free placement): RecoveredArtifact, ArchiveData; 4 open workers, Dangerous, bot wear 4; 400 hp; 9,000 [T4]. Stove chimney pollutes (r4, 0.3).
- **Cryogenic Tank Farm** (LargeTank, Storage 90): Liquid stockpile 2,000; 1,000 hp; 12,000 [T4]; `cryogenic_content.mjs` is `ready` (CryogenicTankSpec + Open sockets (9,0,0)/(10,0,0) Down); boil-off steam while occupied.
- **Smog Scrubber** (Aquifer Drill without aquifer, Wellbeing 160): 200 hp, no workers, 2,500 [T2]; SmogScrubberSpec r7 / 75%; towerSteam through the native MechanicalNodeParticlesController (plays while powered; new case in `vanilla_smoke.mjs`).
- **Radiation buildings** (`radiation_content.mjs`, vanilla Discharge/DeepBadwaterPump behaviour on the study meshes, cost now rule T5 at 120,000): Export pipe socket (5,0,0) Down OpenIn, its MAP_EDGE `Up` side must be fully built (checked); Outfall socket (0,0,0) Down OpenIn, release cell SLUDGE_OUTPUT (3,2,0); Recovery Pump socket (2,0,0) Down OpenOut, intake (1,2,0) is the only MatterBelow Air block, WaterInputCoordinates (1,2,-1). The Export's inherited Discharge overhang is gone. Catalog rows are detailed.
- **Bathhouse** (MudBath template, Wellbeing 155): needs MudBath 0.6 + Massager 0.6 + WetFur 1.0 per hour (vanilla wellbeing +3/+1/+1), 12 bathers hidden inside (Hospital pattern), 300 hp, 1 Water/h through native GoodConsuming (pipe socket (7,6,0) Up OpenIn), 6,000 [T3].
- **Town Plaza** (ExercisePlaza template, Wellbeing 105): DancePit 0.6 + Campfire 0.6 (+2/+1), 15 exported `#Slot#Spot` paving slots round the fountain ('Jumping'), 5,000 [T3], not automatable.
- **Observation Deck** (ExercisePlaza template, Wellbeing 115): ExercisePlaza 0.6 + RooftopTerrace 0.6 (+3/+1), 20 exported slots on the layer-12 deck rim ('Sitting'), 32 deck cells stackable for player paths, 9,500 [T4], not automatable.

**Data:** `frontier_progression.json` (planned entries marked integrated, `lategameWellbeing`, scrubber science), `building_construction_costs.json` (tiers, rule rows), `workforce_risks.json` (no pending templates), `building_sounds.json` (no planned entries), `smog_content.json` (scrubber ready, two polluters), `automation_content.json` (7 templates, CryogenicTankSpec, BuildingPipeSpec, SmogScrubberSpec, AmbientAnimationSpec; RadioactiveSludgeIntakeSpec evidence follows the queued removal), catalog, 10 icon SVGs. DeepOre/DeepAlloy goods now use their own icons.

**Exports:** `export_lategame_models.py` (declared model paths for new blueprints, visitor slot empties + `<Id>-visitor-slots.json`) exported all ten into `outputs/lategame-integration`. New `validate_lategame_exports.py` checks active meshes = export, animated nodes, slot keywords and visitor counts.

**Checks (scratch copy `scratchpad/r`, fresh mirror of real Data):** canonical generation passes; validate_all -SkipBlender passes every check except four that hit MAX_PATH in the scratch location (exports-lategame, exports-structural, model-bindings, audit-building-assets); all four pass when run through a `\\?\` path. Progression audit 0 failures; item uses 4 (RecoveredArtifact fixed). Scripts tree compiles (0 errors).

**Before promote/build 122:** run canonical generation into real Data, then `node tools/create_frontier_expansion_icons.mjs` (the seven new tool icons; the radiation icons are written by generation). Not verified in game: placement, slots on the deck and plaza, bath water by pipe, recovery-pump intake over water, map-edge placement, scrubber plume, construction look.

## Radiation review defects fixed in source, not built or tested in game (Claude Code session, 2026-10-22)

The confirmed radiation findings in `outputs/review-2026-10-21/radiation-{core,gameplay}.json` are fixed in `Scripts/Radiation` (the lockstep NonPublic reflection fix was already in place):
- Recovery Pump crash: removals are queued (`QueueSludgeRemoval`) and applied in the late tick; the pump turns a saved buffer of removed sludge into progress, so world sludge is conserved exactly.
- Save corruption: Save first mirrors geometry changed by the forced tick finish and applies queued releases; sources, `NextSourceId` and `HourAccumulator` load in `Load`.
- Dilution: Harmony prefixes on `UpdateWaterSourcesTask.Run` and `UpdateWaterChangesTask.Run` let source and water-change water dilute radiation the way it dilutes native contamination.
- Column splits no longer copy soil radiation upward. Flora dose is per plant (`RadiationFloraDose`); save version 2.
- Water tanks switch to ContaminatedWater on any pass. Loaded state is applied and drawn while paused. Kits pass dose and the sickness clock to the adult.
- Export overhang: left to the building-integration agent.
- Internal water types at runtime: Mono 6.13 enforces member access unless the assembly requests SkipVerification. Deep Frontier has it through `DeepFrontier.asmdef` `allowUnsafeCode`; runtime-probed in the game's Mono (`outputs/radiation-mono-access-probe`).

Checks: the Scripts tree compiles with 0 errors. The shipped-DLL build of Radiation reports only the expected CS0122 internal-type errors. `validate_radiation_content.mjs` passes. It has 24 new regression checks: 23 fail on the pre-fix sources, and the 24th guards `allowUnsafeCode`. Nothing is verified in game.

## Deep Frontier map variants: written and statically validated, not loaded in game (Claude Code session, 2026-10-22)

Four maps are in `C:\Users\Jordan\Documents\Timberborn\Maps\`:
- `Deep Frontier - Plains`;
- `Deep Frontier - Plains (Hard, Radioactive Spring)`;
- `Deep Frontier - Lakes`;
- `Deep Frontier - Terraces`.

They are generated from the built-in maps, which `tools/prepare_deep_frontier_map.py` reads from `resources.assets` and checks against a recorded SHA-256. The placements and sites are in `tools/map_variants/*.json`. Details, coordinates and the in-game checklist are in `docs/maps.md`; evidence is in `outputs/maps/`.

**Per map:**
- 3 DeepOreVein placements (Deep Mine sites) and 2–3 DeepOreSource placements (1,500–2,500 DeepOre each);
- checked Deep Drill and Deep Mine sites;
- checked reactor and launch-pad sites;
- three Human Record Cache candidate spots. `HumanRecordCache` is defined in `docs/story.md` and `tools/narrative_content.mjs`, but it is not yet in the generated MapEditor collection, so no cache is placed.
- Only the hard variant has a Radioactive Spring (0.2/h, at a river head).

**Z budget (source-confirmed):**
- Vanilla map height is global, not per map: 23 terrain layers and 33 in total.
- A `MapHeight` key is honoured only by Map Transformer, which is not a Deep Frontier dependency. Heights were therefore left unchanged.
- Sites respect each building's highest occupied layer: reactor base ≤ 14, pad ≤ 15, Deep Mine/Drill ≤ 17.

**Static validation:**
- All four pass with 0 errors.
- A scratch harness ran 15 negative tests; each injected fault was caught.

**Not verified:** anything in game. This covers:
- loading without "Can't validate loaded BlockObject" issues;
- the DeepOreSource stock;
- Deep Mine placement on the veins;
- reactor and pad placement near the height cap;
- flooding at low-freeboard sites;
- the spring's and the radioactive tide's sludge paths;
- save/reload.

## Building sounds: source integrated, not yet generated into real data or heard in game (Claude Code session, 2026-10-22)

Every Deep Frontier building template now has a deliberate native selection sound and loop: 55 BuildingSpec templates, plus the dev and map-editor Radioactive Spring. Before this, the generated blueprints inherited whatever sounds their vanilla template had. Source contract, the full inventory of shipped clips and the choice table are in `docs/sounds.md`; each choice's reason is in `tools/building_sounds.json`.

**Contract (decompiled 1.1.2.8, source-confirmed):**
- Selection plays `UI.Buildings.Selected.<name>`; loops play `Environment.Buildings.Loop.<name>`.
- A loop plays only while a native driver toggles it: workshop working, `PowerGeneratorSoundsSpec`, an attraction or dwelling being occupied, a ranged-effect building being powered, or an aquifer drill. Nothing plays a loop all the time.
- Clip names are exact. An unknown name throws when it plays.
- The game ships 100 selection, 15 loop and 14 basic-selection clips, read from resources.assets and cross-checked against globalgamemanagers.

**Data:**
- `tools/building_sounds_content.mjs` runs in `create_vertical_slice_content.mjs` after smog and before the automation audit. It cannot run at the end of the expansion generator, because the construction-material and radiation templates are written later.
- It writes only the sound fields. It fails if:
  - a template has no entry, a listed template is missing, or a planned building appears;
  - a name is not in the registry;
  - a loop has anything other than exactly its one declared driver;
  - `PowerGeneratorSoundsSpec` sits on a workshop generator.
- The reactor uses the Steam Engine pair (Engine, PrintingPress), driven by its workshop. The turbine keeps Gristmill.
- Hospital and Grocery have no loop: their drivers do not track occupancy or staffing.
- The 18 platforms keep the native platform/levee `Default`.

**Checks (scratch copy of the repository):**
- Full canonical generation passes with the hook.
- Applying the module to a baseline generation changed only `SelectionSoundName`, `LoopingSoundName` and `BasicSelectionSoundSpec.SoundName`, in 30 files, and a second run changed nothing. The hooked chain reproduced that output exactly.
- All 15 `tools/validate_*.mjs` pass, including `validate_building_sounds.mjs --game`.
- `validate_model_bindings.py` passes, 70 templates, when the concurrent narrative map object `HumanRecordCache` is parked. Its vanilla `MapEditor/Objects/MediumRelic` model is not covered by that validator's Buildings-only vanilla-model list.

**Blocking canonical generation (not sounds):** the workforce check that every course has an accepting template now fails on Metallurgy. Only the pending SteelMill accepts it. The scratch run bypassed that check in its copy only.

**Not verified:** everything at runtime, including:
- in-game playback;
- subjective fit, judged by listening;
- the loop start and stop behaviour of the newly looping buildings.

## Second uses and bot upkeep — source changed, not yet generated into real data (Claude Code session, 2026-10-22)

The design and the reasoning for each use are in `docs/progression.md` (Second uses).

**Item-use audit:** failures drop from 20 to 5: Cryocoolant, LiquidHydrogen, LiquidOxygen, RecoveredArtifact and RadioactiveSludge. Those are left to the cryogenic and narrative agents or to a user decision. `docs/item-use-audit.md` comes from a scratch generation of the current sources.

**What changed**
- New recipes:
  - Water Treatment Plant: activated carbon filters.
  - Chemical Works: chemical from brine.
  - Greenhouse: aquaponics. Its unlock moves from 500 to 600 science.
  - Precision Machine Works: three bot-part recipes.
  - Uranium Processing Plant: spent fuel reprocessing.
  - Waste Refinery: waste refining with contaminated water, and sludge vitrification.
  - Materials Laboratory: geochemical assays.
- Changed recipes: Electronics +Flux, PowerModule +Coal, Yellowcake +OxygenGas, EnrichedFuel +HydrogenGas.
- Construction gates: Greenhouse 30 Compost; Nuclear Reactor 20 EnrichedFuel and 10 RecoveredMinerals.
- Bots:
  - The IndustrialBot recipe is added to the vanilla Bot Assembler through a same-path `ProductionRecipeIds#append` patch, in `tools/bot_upkeep_content.mjs`.
  - `FrontierBotMaintenanceSpec` goes on the 16 open bot-wear workplaces.
  - C#: `Scripts/Workforce/BotMaintenance.cs` (component, dedicated inventory, own configurator) and `BotUpkeepPanels.cs`. `BotWear.cs` now holds the saved dose.
- Both audits read vanilla patches. `audit_progression.mjs` fails on recipe display-key collisions within one building.

**Checks (scratch copy):**
- Full canonical generation passes, with one scratch-only stub: the workforce agent's new course check fails while the Steel Mill is pending.
- `audit_progression.mjs`: 0 failures. There is one new warning: the IndustrialBot is visible at the assembler's 750 science, while PowerModule arrives at 5,000.
- These pass: `lategame_costs.mjs --check`, every `tools/validate_*.mjs` (including the new `validate_bot_upkeep.mjs`), and the real Scripts tree compile.

**Not verified in game:** everything. Specific risks:
- the second native inventory on manufactories: hauling, UI and save;
- the assembler recipe dropdown with the vanilla recipe's empty icon;
- whether the `#append` patch merges into the vanilla Bot Assembler.

## Cryogenic fuel storage behaviour — source only, waiting for the tank-farm template (Claude Code session)

Design and Timber Pipes evidence are in `docs/transport-adapters.md` ("Cryogenic tank farm by pipe").

**What exists:**
- C# in `src/DeepFrontier/Scripts/Cryogenics/`: `CryogenicTankSpec`, the `CryogenicIntakeGate` stockpile disallower, its Harmony prefix on `InventoryInitializer.Initialize`, and `CryogenicTank`.
- Behaviour: intake is open only while `MechanicalBuilding.ActiveAndPowered` is true; pause and automation Off count as power loss. After 12 h without power the tank vents 4 units/h. It shows statuses, posts a notification on the first vent of an outage, saves the outage clock, and reports a wrong or contaminated pipe network.
- Data: `tools/cryogenic_content.mjs`, wired at the end of the expansion generator, with `tools/validate_cryogenic_content.mjs`. Both pipe sockets from the study are `Open` `BuildingPipeSpec` ports.

**Verified:**
- The whole Scripts tree compiles (0 errors at 00:15).
- In a scratch repository mirror, canonical generation ran the cryogenic step in the awaiting state. It then stopped at the pre-existing workforce SteelMill course, not at this step.
- Scratch-copy runs passed: the ready state on a synthetic LargeTank-derived template, seven negative cases, and the validator in both states.

**Pending:**
- The integration's `CryogenicTankFarm.IronTeeth` blueprint has not landed. When it does: set `TANK_FARM.status` to `ready`, declare `CryogenicTankSpec` (operational) and `BuildingPipeSpec` (dependency) in automation `customSpecs`, then regenerate.
- No build, install or in-game test yet.

## Reactor meltdown and waste leaks: source integrated, not built or tested in game (Claude Code session)

Design, numbers, native evidence, acceptance assertions and open questions are in `docs/meltdown.md`.

**What exists:**
- **Nuclear Reactor core heat** (`Scripts/Meltdown/ReactorCore.cs`). The core heats while running with coolant dry, fewer than 4 operators working, or maintenance overdue (a 24 h stop every 360 running hours). It warns at 60%, trips an automatic SCRAM at 85% (an `IManufactoryLimiter`, so crew and coolant deliveries stay) and restarts at or below 40%.
  - Decay heat without coolant keeps heating it for 72 h after it stops.
  - Pause or automation Off is a safe cold shutdown.
  - The panel has SCRAM and Restart buttons and an auto-restart toggle.
- **Meltdown at 100%** (`MeltdownService.cs`):
  - native `EntityService.Delete` destroys the reactor;
  - characters inside or within 2 tiles die, and beavers within 16 tiles are irradiated;
  - 60 sludge units, plus 0.5/h for 10 days;
  - soil and water radiation within 12 tiles;
  - a notification and a dialog.
- **Waste leaks** (`WasteLeak.cs`):
  - A full vault breaches 4 casks every 24 h.
  - The refinery leaks 6 sludge every 24 h when its sludge output is full; pausing it seals the tanks.
  - Warnings start at 90% and 75% respectively.
  - Each leak releases 1.2 sludge units and +0.16 soil radiation within 3 tiles.
- **Data:**
  - `tools/meltdown_content.mjs` runs at the end of `create_frontier_expansion_content.mjs` and writes the `ReactorMeltdownSpec`/`WasteLeakSpec` specs, the risk text in the three building descriptions and every row in `enUS.csv`.
  - `tools/automation_content.json` declares both specs.

**Checks (2026-10-22, scratch copy of the repository):**
- The whole Scripts tree compiles with no new warnings.
- Full canonical generation passes, including the automation audit. One scratch-only stub was needed for the unrelated SteelMill workforce check, which is pending in the real tree.
- `validate_meltdown_content.mjs` passes, and also fails as it should on a tampered spec and on a missing row.
- These pass: automation, vertical slice, workforce, rocket, smog, restaurant (content and grid), construction materials, manifest, radiation `--strict-chain`, cryogenic, building sounds, the progression audit (0 failures) and the item-use audit.

**Not verified:** everything at runtime. The real data is not regenerated, so standalone `validate_automation_content.mjs` and `validate_meltdown_content.mjs` against the current real data fail until the next canonical generation.


## Radioactive tide weather: source integrated, not built or tested in game (Claude Code session)

Design, numbers, native evidence and open questions are in `docs/radiation.md`, section "Radioactive tide".

**What exists:**
- **A third hazardous weather (`RadioactiveTideWeather`).** Water sources keep flowing clean water. Every native water source also releases radioactive sludge: 0.1 units per game hour per unit of current strength, through `IRadiationService.AddSludge`.
- **Options (eMka.ModSettings, main menu).** The tide is on by default. Defaults: earliest cycle 15, 25% chance per cycle, 3–6 days. It never comes two cycles in a row.
- **Native UI.** The top-bar icon, the forecast bar, the approaching, started and ended banners with one-line explanations, the badtide alarm and a yellow-green sky fog.
- **Saving.** The tide's state is saved, and a saved tide is restored after the native load.
- **Harmony.** Five patches, verified at mod start:
  - weather selection;
  - restore after load;
  - three UI-helper patches.
- **Dev mode.** A method forces a tide next cycle.

**Code and data:**
- C#: `src/DeepFrontier/Scripts/RadioactiveTide/`.
- Data: `tools/radioactive_tide_content.mjs`, imported last by `create_frontier_expansion_content.mjs`. It writes 18 enUS rows, the `Configurations/Sun.blueprint.json` fog overlay and `Sprites/Weather/RadioactiveTideIcon.png`.

**Checks (2026-10-22, scratch copy of the repository):**
- **Compile passes:**
  - the whole Scripts tree, through `outputs/radioactive-tide-compile`;
  - the tide sources against the shipped, non-publicized 1.1.2.8 assemblies, ModSettings 1.1.1.0 and Harmony, through `outputs/radioactive-tide-compile-real`. This shows the tide uses public APIs only, apart from its verified reflection and patches.
- **Generation.** Canonical generation ran the tide module. It then stopped in `workforce_risk_content.mjs` on the pending SteelMill Metallurgy course, which is unrelated to the tide.
- **Validators.** These pass on the scratch output:
  - `validate_radioactive_tide_content.mjs --native outputs/weather-api-1.1.2.8`;
  - manifest, vertical slice, radiation, smog, building sounds, meltdown, cryogenic, narrative, rocket, restaurant, restaurant grid and construction materials.
- **Still failing:** workforce and automation, because the workforce stage did not run.
- The real `src/DeepFrontier/Data` was not regenerated.

**Not verified:** everything at runtime. That includes:
- the patches and the restored weather;
- that the `Sun.blueprint.json` nested `#append` merge applies;
- the inline UI styles and the ModSettings panel;
- sludge emission and balance;
- save and reload.

## Narrative layer: source integrated, not built or tested in game (Claude Code session)

The story bible, the chapter table and the endings are in `docs/story.md`. The canonical text and data are in `tools/narrative_content.mjs`, imported last by `create_frontier_expansion_content.mjs`.

**What exists:**
- **Ten ordered chapters.** They run from "Something in the Water" to "The Long-Range Beacon" and are triggered by:
  - buildings first finished;
  - cumulative native production of DeepAlloy, PureWater, Chemical, RecoveredArtifact and ArchiveData;
  - rocket mission successes;
  - the ending choice.
- **Rewards and endings.** Chapters give science. There are nine optional discoveries and three endings (Signal, Archive, Settlement).
- **C# in `src/DeepFrontier/Scripts/Narrative/`:**
  - `NarrativeObjectiveService`: listens for EnteredFinishedStateEvent, plus a PostLoad scan of already finished buildings. It saves under `DeepFrontier.Narrative`.
  - `NarrativeProductionReporter`: decorated on every native Manufactory.
  - `HumanRecordCache`: a map object.
  - `NarrativeJournal`, guarded by `!UNITY_EDITOR`, with three parts:
    - the top-left journal panel;
    - the journal window;
    - the native story dialogs, queued until no panel is open.
- **Human Record Cache map object.** It is a clone of the vanilla Medium Relic, at MapEditorObjects tool order 1450, using the placeholder model and icon. An Archive Excavation within 4 tiles surveys it for 24 working hours. The cache then gives 6 ArchiveData and a journal record.
- **Automation.** No spec is added to any player building, so `automation_content.json` is unchanged.

**Checks (00:05, 2026-10-22, scratch copy):**
- The whole Scripts tree compiles in a throwaway project.
- The canonical generation ran through expansion, the narrative step, construction materials and radiation. It then stopped in `workforce_risk_content.mjs` on the pending SteelMill Metallurgy course, which is not part of the narrative.
- These pass on the scratch data: `validate_narrative_content.mjs`, rocket, radiation, vertical slice, manifest and construction materials.
- The automation audit reported only the four customSpecs whose producers run after the failed workforce step.

**Not verified:** all runtime behaviour. That includes trigger firing, dialog order after a rocket's own dialog, the journal panel's layout, cache surveys, the TimberUi DialogBoxElement rendering, and save/reload.

## Radiation — source integrated, not yet built or tested in game (Claude Code session)

Design, API and the in-game acceptance list are in `docs/radiation.md`.

**What exists (C#: `src/DeepFrontier/Scripts/Radiation/`):**
- **Radioactive sludge is a third world fluid.** The native 1.1.2.8 shallow-water kernels run on mod-owned columns that mirror the native geometry, so terrain, dams and levees shape it like water. It drains off open map edges. Its surface is drawn in glowing yellow-green.
- **Dissolved radiation rides the water.** The native contamination kernels run on a copy of the water columns. The water surface gets a log-scaled yellow-green tint that blends with badwater.
- **Soil radiation** kills plants. Planting is still allowed; crops show a warning in the planting tooltip and their panel, plus a status icon.
- **Pumps refuse** to run with any radiation at their intake ("Radiation detected"). Badwater filtering is unchanged.
- **Stored Water converts** to undrinkable ContaminatedWater.
- **Irradiated beavers** need 10 days of hospital care. Untreated, they die 8 days after a 12-hour grace period.
- **Buildings:**
  - Radioactive Waste Export: must touch the map edge.
  - Sludge Outfall and Sludge Recovery Pump.
  - All three are placeholders that reuse vanilla models and icons, at 120,000 science.
- **Radioactive Spring:**
  - an in-game dev-mode tool and a map-editor object;
  - strength in sludge per hour, set with the native water-source field;
  - saved with the map and the game.
- **API:** `IRadiationService` for meltdown and spill systems.

**Data:**
- `tools/radiation_content.mjs` runs in canonical generation after the tool overrides and before workforce and automation.
- Reactor `NuclearWaste` also yields 1 sludge. `WasteRefining` yields 6 sludge in place of 12 Badwater. New refinery recipe `DecontaminateWater`: 10 ContaminatedWater + 1 Chemical → 8 Water + 1 sludge.
- Solid RadioactiveWaste stays as spent-fuel casks.

**Checks (18:50, scratch copy of the repository):**
- Compile passes.
- Full canonical generation passes.
- These pass: radiation `--strict-chain`, automation, vertical slice, workforce, rocket, smog, restaurant grid, manifest, model bindings (5 vanilla placeholder models, now explicitly allowed), and the progression audit (0 failures).

**Still failing:**
- `validate_restaurant_content.mjs`: its exact need list must add `Irradiation`.
- `audit_item_uses.mjs`: crashes on a collected template without a `BuildingSpec`, which the dev spring is, as vanilla DevWaterSource is.
- `validate_construction_materials.mjs`: ConcreteMixer port 6,4 against an expected 7,5. This comes from the concurrent industrial layout change, not radiation.

**Blocking canonical generation (not radiation):** at 18:37 `Hospital-ReferenceStudy.blend` changed without a fresh `civic_wall_faces.py` measurement. The scratch run used its `.blend1`, which matches the record.

**Not verified:** everything at runtime. That includes:
- kernel stability;
- whether the runtime material and the `Sprites/Default` shader load;
- the 10-day course, which assumes the measured 0.5 hospital repeat-visit duty and must be measured in game;
- save/reload;
- performance.

## Ground/plank clearance, selected doors and Hatchery decks — build119 installed

The user's ground/plank concern was confirmed in both mineral pits: their wearing surfaces were exactly at terrain height. A read-only audit covered 19 canonical detailed scenes /20 shipping templates and 5,778,448 evaluated triangles; Hatchery was checked separately. The other 17 scenes had no exposed horizontal wood tops in the ±0.025 ground band. Installed native terrain has horizontal tops up to +0.010. The two pits now have independent `Apron` components at +0.020, preserving buried joists, doors and all unselected objects. Their 424 assembled maximum-height-terrain probes and fresh strict overlaps pass. See `outputs/terrain-contact/REPORT.md` and `docs/art/z-fighting-checks.md` for scope and native-render limitations.

Hatchery now has seventeen selective components, aligned enclosed headhouse walls and door, 32 player-path cells, 28 stackable dock cells, 16 power-socket cells and 120 physical picking volumes. Native housing rails are authored on exact cell edges with twenty selective openings. The two bank aprons have +0.016 backing/+0.020 plank tops above their native floor; 462 assembled terrain probes pass. Both pens, retained machinery, water behavior bindings, recipes, 55hp demand, two workers, 600science and 8×8×5/BaseZ1 registration are preserved. Source/UV/shell/window checks pass. The official export passed 4,320 one-sided doorway coverage probes and its data validator; source SHA256 `339ff5e714b351092f7431dbd69edf971199e7b9f8c5b15b63b7feb4090fa44e`, model `24135f27694a6d6c45dfaeec07465cc213891bbd9e2ed46b997a1896934a57ae`.

Native DirtPath meshes would be hidden by raised planks. The four clear Hatchery bank cells and each pit's existing doorway cell now use the native ImpermeableFloor contract: `Floor` occupation without `Path`, plus `PathModelTypeEnforcerSpec: Roof`. Door, native floor and worker idle heights did not move. Both updated pit exports passed 4,320 one-sided doorway probes each and their export validator. The native path-height capture and blueprint promotion records are in `outputs/hatchery-platform-candidate/` and `outputs/terrain-contact/`.

The selected door component repairs for Fishery Works, Grocery, Crusher, Kiln, Mixer, Quarry, both pits and Hydro have also been exported. Their strict overlap and actual exported doorway checks pass; the final Quarry includes explicit L-shaped bay returns and its original reflected side door. The corresponding industrial, hydro, civic, hospital, grocery, fishery and hatchery export validators pass. All54 current model bindings and content/manifest checks pass. Fishery Works and Grocery retain their existing built-in outdoor routes; this stage does not claim their full platform migration.

Official build119 succeeded and installed all480 matching authored data/manifest/DLL hashes at 14:41 on2026-10-21 (`outputs/restaurant-package-verification119.json`). It includes the selectively promoted Hatchery blueprint/meshes, pit floor changes, current portal exports and the six vanilla shaft visibility overrides. Build logs are `outputs/components119-official-build.log` and `outputs/components119-unity.log`. Canonical Hatchery generation is no longer blocked on missing structure metadata; it is complete. Keep unrelated late-game candidate activation separate from this package's evidence. New native placement, paths, rails, power, appearance and reload tests remain pending because Computer Use was stopped with the physical Escape key. No further game control or restart was attempted; the already running game has not reloaded these assets. Saved-scene Hatchery front/rear previews are archived in `docs/art/reviews/2026-10-21-component-authoring/`.

## Hospital selected doors — installed by build116; later component work below

Hospital's four portals now use the same explicit component authoring workflow as Restaurant. Only `Door.GroundDoor`, `Door.WestWardDoor`, `Door.RearWardDoor` and `Door.RoofTerraceDoor` were rebuilt, with flush grid-room joints and no duplicate cavity caps. The one-time migration preserved 259 other objects and 34,470 retained architecture faces in 9.449 seconds. An independent read-only audit confirmed the exact legacy face ownership and canonical anchors (`outputs/hospital-portals-legacy-provenance.json`). The full hospital generator was not run; its two-wing layout, native props, paths, hitboxes, care settings and gameplay definitions were not changed.

The checked official export passed strict overlaps and 17,280 one-sided exported coverage probes. `validate_hospital_exports.py` passed with 279 nodes, 323,265 native-UV vertices, 79 routes and sixty rail openings. Source SHA256: `71e72c516cd3b87de22dbc7c84f8fc10daf4a9e6a20df3ac986f272aaaa24a6b`; model SHA256: `3b7f997f527cf4c68400998867b9e84db515f0c5d53a58e1bfaca2f0554a6023`. Only the two official Hospital meshes were promoted to source Data after verifying their previous contents matched installed115 (`outputs/hospital-component-promotion.json`). The independent build116 subsequently installed this export and verified all 474 hashes. Evidence: `hospital-components-initialize.log`, `hospital-components-export.log`, `hospital-component-export-culling.json`, `hospital-component-validation.log` and `restaurant-package-verification116.json` in outputs.

The installed Restaurant build115 mesh was independently checked: SHA256 `267662728466e37c8bad563934f671da4dd6b7e1be846d0ae4067e2bf6cd8eff`, 14,400 isolated-door and 2,880 oblique wall/corner coverage probes, zero failures (`outputs/restaurant-installed115-door-culling.json`). All 474 installed115 hashes matched before the Hospital candidate promotion. The user subsequently reported the doors appear fixed and explicitly authorized game control to move to other buildings. During the next work session, Computer Use was stopped by the physical Escape key; no further game control was attempted. New native appearance and entrance-cell traversal are not independently certified by these export checks.

A saved-scene Hospital doorway preview is in `docs/art/reviews/2026-10-21-component-authoring/Hospital-GroundDoor-context.png`; it generated no geometry and verified the source hash remained unchanged. The remaining-component read-only inventory identifies twenty portals in eleven models (`outputs/component-inventory/`). Ten scene hashes matched at report time; Materials Laboratory was externally edited and its current entry is marked unverified. No other catalog components were migrated by that audit.

## Runtime review of the new code — 37 confirmed defects (Claude Code session)

An adversarial review (9 subsystem reviewers, 2 skeptics per finding, 91 agents) confirmed 37 defects; the per-subsystem findings with evidence are in `outputs/review-2026-10-21/*.json`. The one that would have broken every game load in build 122 is fixed: `RadiationLockstep.Verify` reflected with `BindingFlags.Public`, but the shipped `Timberborn.WaterSystem.dll` keeps those fields private (only the ModsBuild compile references are publicized); it now includes NonPublic and the Scripts tree compiles. The others are assigned: rocket (3), restaurant (3), grocery clerk position (1), workforce (3), side-platform flip (1), acceptance harness (7). Not yet assigned, because their agents were stopped: radiation core/gameplay (13 remaining: the Recovery Pump's RemoveSludge crash, two save-corruption cases, dilution, column split, flora dose, tank conversion, export overhang, kit growth, load visibility), smog (3), hatchery BaseZ load order (save corruption), water hysteresis and off-map supports. **Build 122 must wait for those.** The seven-building integration was also stopped before exporting anything.

Waterside review findings fixed 2026-10-22 (source, compile and scratch-copy generation only; not built or run in game):
- **Hatchery deck load order (save corruption).** Native `BlockObjectBatchLoader` sorts by `CoordinatesAtBaseZ.z`, then by the highest occupation on the BaseZ layer. Deck paths, shafts and platforms share the Hatchery's layer and loaded before it (headhouse 'All' = rank 6), so they were deleted on every load. No data-only fix exists: the picker places origin = cursor - BaseZ while the loader sorts at origin + BaseZ, and a rank below Path would need a Floor/None-only bank layer that still ties with ImpermeableFloor. New Harmony postfix `Scripts/Waterside/StackableBaseLoadOrder.cs` on `GetHighestOccupation` returns -1 for objects with stackable cells below BaseZ and every foundation at or below BaseZ, so they are added first in their layer (Hatchery and the side platforms). Registration, art and FisheryWorks (BaseZ 0, unaffected) are unchanged. The generator and `validate_hatchery_exports.py` now require that foundation condition. The hatchery acceptance asserts the native order for all 27 deck objects; continuity reload asserts all 29 fixture paths and the (193,161) platform stack survive. Saves made before this fix have already lost their deck objects; re-run the hatchery acceptance before continuity.
- **Water hysteresis.** `WatersideSurvey.Next` gives Shallow priority in every state. A dry pen over a pit deeper than MaxDepth now stays Shallow instead of alternating Shallow/Deep every tick. A scratch exhaustive check of 54,639 reading/state pairs found every state settles after at most one transition.
- **Off-map support preview.** `AdaptiveSupportsPlacementValidator` reports `DeepFrontier.Waterside.SupportOutsideMap` ("A support post would stand outside the map.") before judging depth. The row is in `WATERSIDE_ROWS`, which canonical generation appends to enUS.csv.
- Scripts tree compiles with 0 errors. Scratch generation was run with the Metallurgy workforce check disabled in the copy only. It changed no hatchery/fishery registration, and hatchery, fishery and model-binding validators pass.

Hatchery natural map sites, 2026-10-24 (source, scratch-mirror generation and static map validation only; not built or run in game):
- **The map script accepted dry hatcheries.** `prepare_deep_frontier_map.py` refused hatchery blocks in water, which forces the pens dry. It also compared MinDepth with the column depth instead of the surface above the pen cell. The earlier Plains, Lakes and Terraces sites had pen submersion −0.69, −0.40 and −1.79, so in game they would have stayed blocked for water. The script now follows `WatersideSurvey`: open column, surface ≥ cell floor + MinDepth, depth ≤ MaxDepth, and contamination from WorkCells[0] only, as native. A building with WaterDepthWorkCells and no FloodableBuildingSpec may stand in water. Every adaptive pile must reach the bed within MaxDepth. The planner prefilter uses the same reading.
- **What makes natural sites rare.** The pens hang one layer below the bank, so the surface must stand within 0.8 of the bank top. Natural rivers on these maps sit 1.3–1.7 below their banks. On shore-aligned, deck-clear positions this rule alone keeps 4 of 30 clean Plains positions and 6 of 78 on Lakes. The straight eight-cell bank is the second filter. On Terraces every physically fitting position is badwater-mixed (about 0.44).
- **Change.** Only the door cell (2,0,1) needs ground now. The seven other bank-row cells may step down over a lower shore or water, each carried by an adaptive bank post (`waterside_sites.json` `bankColumns`/`groundCells`). The posts reuse the pile templates and show nothing on a level bank. The nine deck piles, the four pen work cells, the surface rule and the 0.05 limit are unchanged. Generator, `validate_hatchery_exports.py`, the preview markers (no foot tile at depth 0) and the hatchery acceptance (one foundation cell, 16 probes, bank posts at depth 0 on the straight fixture bank) are updated.
- **Sites.** Plains and Plains-hard: 151,144,3 Cw0, natural, route 22, 4 bank posts. Lakes: 99,151,3 Cw0, natural, route 17, 5 bank posts. Terraces still needs Dynamite: 120,197,6 Cw90, seven one-layer charges, all four pens wet (0.51 above the cell floor), route 68. All four variants validate OK in the mirror, the all-buildings contract passes, and all non-Blender `validate_all` checks pass. Untested in game: an overhanging bank row and its posts.
- **Not changed (needs a decision).** Letting the pens reach one layer lower would roughly triple the clean sites on Plains and Lakes, but the cages would hang above the water without new adaptive pen art. Accepting mixed water would be a balance change. Native ContaminationBlockableBuilding decorates every IWaterNeedingBuilding with a fixed 0.05 block, so the current limit is the native behaviour.

## Build 121 installed — 556/556 files verified (Claude Code session)

**Build 121 is unplayable:** every game load crashes with "Launch Pad model must contain exactly one 'LaunchPad.Rocket' node; found 2" (the construction-stage mesh is a byte copy of the finished one, and RocketLaunchVisual searched the whole entity). Fixed in source (finished-model search only); needs the next build. The startup blocker was Timberborn's Mods screen, bypassed by `-skipModManager` in `tools/launch_timberborn.ps1`, which every acceptance launcher now uses.

**Acceptance runs: what blocked them is now handled; build 121 still crashes on every game load (2026-10-22).** The blocker was Timberborn's own "Mods" screen (`ModManagerScenePanel`, OK button). It appears before any mod code loads. A probe launch of build 121 with the old Steam `-applaunch` command reproduced the end of `outputs/lategame-main121.log` exactly; its screenshot showed only the Mods screen and no Steam prompt. All `tools/start_*.ps1` launchers now start through `tools/launch_timberborn.ps1`: Timberborn.exe directly, `SteamAppId` set, and the native `-skipModManager`. This needs no rebuild and was verified on build 121: mods loaded, Steam connected, and the loader ran. The late-game, rocket, mixer and hospital launchers take `-Watch` (`tools/watch_acceptance_log.ps1`). It closes the game after the harness's saved line, a FAILED line, a crash or a stall, and exits non-zero unless the harness completed. `AcceptanceStartupPanels.cs` (compiled, not built; acceptance flag only) dismisses in-game startup panels with native Escape before harness frame 60. Such panels lock game speed; the known one is Moddable Weathers' dialog, which appears only on the `Industrial acceptance - initial/verified` saves. **Build 121 crashes on every game-scene load:** `RocketLaunchVisual.Awake` found two `LaunchPad.Rocket` nodes, because ConstructionStage0 is a copy of the finished mesh. This has since been fixed in source; the next build is needed. Procedure and evidence: `docs/acceptance-runs.md`. No build 121 behaviour is verified in game.

The official build initially failed on two compile errors in the deck-free IndustrialAcceptance.cs and MixerAcceptance.cs: Directions3D was used as a string. Both now use `Directions.ToString()`. `verify_deep_frontier_package.ps1 -Build 121` passes: 556/556. The game was launched for the user's review. Nothing in it has been verified in game yet.

Promote passed end to end. All export, content, automation, workforce, rocket, smog, radiation and progression validators pass, and so does the asset audit: 56 buildings, of which 52 are detailed and 4 are radiation placeholders on vanilla stand-in models.

**Buildings**
- All 20 late-game buildings, on the grid with wall-only shafts, plus vanilla smoke and steam.
- The Grocery Market with stock displays.
- The Restaurant with waiters and table dishes (new art; top terrace clear) and the Hospital (new art).
- The deck-free industrial machines: crusher, kiln, mixer and both quarries, with no walkway specs (deckMode None) and the mixer pipe port at (6,4) Right.
- The grid-aligned hydro turbine and Materials Laboratory (clear roof terrace).
- Fishery and Hatchery adaptive supports.
- Concrete platform variants and side platforms on dam blocks.

**Systems:** the rocket program, smog, workforce risks, radiation with the dev and map-editor Radioactive Spring, and automation roles.

**Validators updated for new content:**
- Restaurant: the needs list gains the rocket legacy needs and Irradiation.
- Hospital: Irradiation treatment.
- Construction materials and item uses: dev tools without a BuildingSpec.
- Promote: structural counts 36/18.
- Asset audit: new `placeholder` art stage.

**Pending:** in-game acceptance (`tools/start_lategame_acceptance.ps1` and `tools/start_lategame_rocket.ps1`), plus IndustrialAcceptance and MixerAcceptance for the deck-free machines. Build 122: the radiation-in-water lockstep (staged in outputs/radiation-lockstep) and integration of the seven new studies (SteelMill, ArchiveExcavation, CryogenicTankFarm, SmogScrubber, and the three radiation buildings).

## Progression pass — source changed, not yet generated into real data (Claude Code session)

Rules, the chain table and planned-building specs are in `docs/progression.md`. Checked with `tools/audit_progression.mjs`: no failures in a scratch-copy generation.

**Goods and recipes**
- Gases scrapped: Gas, Methane, SulfurGas, ToxicFumes, Radon. HydrogenGas and OxygenGas stay. DiningService is dropped.
- Polymer and Yellowcake now use Chemical. Chemical is made at ChemicalWorks from Badwater + Extract.
- PowerModule is made at PrecisionMachineWorks.
- DeepCoal, DeepOil and DeepUranium run at DeepProcessor. Compost runs at FertilizerWorks with no Dirt (Log + Algae + Water).
- Cement is 3 Limestone + 1 Aggregate, with no Dirt, so concrete becomes available at 1,000 science.

**Buildings**
- The Greenhouse grows Eggplant, Kohlrabi and Coffee with Fertilizer.
- Reactor waste: 1 per cycle. The refinery takes 4 waste per 8 h, so one refinery serves one reactor.

**Science and unlock order**
- Hydro turbine: 8,000. Uranium plant and Vault: 100,000. Waste refinery: 120,000.
- Raised so nothing unlocks before its materials: masonry 900, and DeepDrill, Restaurant and PublicHealthLab 1,000.

**Costs and menus**
- Late-game construction costs follow the documented size rule (`tools/building_construction_costs.json`, `tools/lategame_costs.mjs`).
- Menu collisions are fixed: reactor Power 250, MissionControl Science 110.

**Planned** (data only in `frontier_progression.json` plannedBuildings; art in progress): SteelMill, ArchiveExcavation (free placement), CryogenicTankFarm.

**Workbook:** needs a rebuild by Codex. The rows to change are listed in `docs/progression.md`.

## Concurrency rule: never restore src/DeepFrontier/Data wholesale (Claude Code session)

Several agents tested generation by snapshotting src/DeepFrontier/Data, generating, then restoring the whole folder. Concurrent restores reverted other sessions' generations. At 16:43 the active data fell back to the build 120 state, losing the 16:37 run with late-game batches 2–3.

**Rule:**
- Test generation in a scratch copy of the repository.
- Only the coordinating session runs canonical generation into the real data, and it restores only the files it can attribute to a failed run.

## Smoke/steam review notes for the in-progress `vanilla_smoke.mjs` (Claude Code session → Codex)

The Claude Code session reviewed the concurrent smoke work, which records `kit.stack()` mouths and STEAM_VENTS and adds `applyVanillaSmoke`. It made no edits to it. Decompiled evidence is in the session scratchpad `particles/`. Findings:

**1. Not wired, and the reactor study is stale.** `vanilla_smoke.mjs` is not imported yet. The reactor's STEAM_VENTS edit changed its artHash, so it needs a `--save-only` rebuild before its registration can refresh.

**2. Hand-built chimneys are missed.** Only `kit.stack()` mouths are recorded. Positions are artwork (x, y, z), so the blueprint Position is {X: x, Y: z, Z: y}:
- PrecisionMachineWorks brick chimney: (0.45, 8.15, 12.87).
- TechnicalSchool roof chimneys: (3.8, 4.775, 5.8) and (7.2, 4.775, 5.8).
- PublicHealthLab fume flue: (0.875, 7.075, 6.95). Steam fits better here.
- ChemicalWorks flare tip: (9.475, 8.475, 12.47).

**3. Every kit stack becomes black smelter smoke.** Suggested instead:
- Steam for the Cryogenic vent, Uranium scrubber, Waste Refinery, PublicHealthLab and FertilizerWorks drier-hood stacks.
- No smoke on the reactor's two ventilation stacks.

**4. Plume scale.** Cooling-tower mouths are about 1.98 in radius but get SteamEngineSmoke at Scale 1. Scale by mouth radius, or use GeothermalEngineSmoke for the towers.

**5. Mouth height.** Kit stack mouths sit about 1 cm under the soot cap; use bottom + height + 0.10.

**6. Grocery chimney.** Position {X: 7.0, Y: 7.22, Z: 4.75} under #Finished. GroceryStore is not a workshop, so use EnterableParticleControllerSpec or BlockableObjectParticleControllerSpec.

**7. Factory chimneys (artwork coordinates).**
- Restaurant: (5.55, 5.50, 8.51) and (2.30, 3.85, 8.51).
- Hospital: (2.5, 8.5, 6.65) and (10.5, 8.5, 6.65).
- Kiln: (6.22, 2.70, 4.62).
- Materials lab: (4.15, 6.80, 7.99) and (7.30, 2.80, 5.89).
- Fishery: (5.72, 6.65, 6.13).

**8. Construction-model duplicates.** ConstructionStage0 is a copy of the finished mesh, so named emitter empties would be duplicated. #Finished plus Position avoids that.

## Build numbering note (Claude Code session)

Two concurrent sessions each produced a "build119": Codex's at 14:41 (480 files), and the Claude Code session's at about 15:05 (520 files, late-game pilot and platforms). Both wrote `outputs/restaurant-package-verification119.json`, so the later Claude Code verification overwrote Codex's record. Build 120 (Claude Code, 520 files) followed.

**Next build: 121.** Canonical generation ran at 16:37, apparently from Codex's finished hatchery/pit work. Active data now contains:
- late-game batches 2–3 and the redesigned PrecisionMachineWorks/MissionControl meshes
- the side-platform blueprints; their meshes still need `promote_style_exports.ps1`
- AmbientAnimationSpec on the vault, and WorkshopAnimationController on every late-game workshop
- the in-progress factory alignment generators (crusher, kiln, mixer, hydro, lab)

Hold build 121 until those two alignment agents report done.

## Build 120 installed (Claude Code session)

Built from the last validated data, data-before15: the Grocery Market hall, the grid-aligned NuclearReactor and FertilizerWorks, wall-only shafts on late-game and grocery buildings, and the native-style icons. The game was closed first at the user's request. `verify_deep_frontier_package.ps1 -Build 120` (pwsh 7): 520/520 match. Batches 2–3 and the side platforms are not included, because generation was blocked. None of 120 is verified in game yet.

## Late-game batches 2–3 staged; all 20 studies grid-aligned (Claude Code session)

The grid pass on all 20 late-game studies is done (`tools/asset-pipeline/lategame_grid_audit.py` → `outputs/lategame-grid-audit.json`). Masses, plinths, aprons, basins and decks sit on tile edges. Every study has 0 visible z-fight conflicts, except the 84 pairs inside the shipped CompactWaterWheel meshes on the reactor; doors are unchanged. Deliberate off-grid exceptions are listed in the agent report and in module comments.

**Staged** (`tools/lategame_batches.json`, 17 ids): the reactor, FertilizerWorks, and 15 more. The 15 are FoodPackagingWorks, PublicHealthLab, Greenhouse, ChemicalWorks, PrecisionMachineWorks, WaterTreatmentPlant, TechnicalSchool, UraniumProcessingPlant, RadioactiveWasteRefinery, ElectrolysisPlant, CryogenicLiquefactionPlant, RocketAssemblyHangar, MissionControl, LaunchPad and RadioactiveWasteVault.
- **Exports and catalog:** all exported, and catalog ownership moved.
- **Vault:** it takes the late-game path; worker-slot specs apply only to buildings with a WorkplaceSpec.
- **WaterTreatmentPlant coolant outlet:** cell (11,1,0), facing Right.
- **Dry run of the blueprint transform:** passes for all 17, and every entrance connects to open ground.

**Not generated yet:** canonical generation is blocked by the hydro/lab alignment agent's missing `ReinforcedHydroTurbine-wall-faces.json`.

**Batch 4** (DeepDrill, DeepMine, DeepProcessor; understructure and underground) is in progress. PrecisionMachineWorks and MissionControl are being redesigned away from the shared clock-tower silhouette, so their exports will be refreshed.

## Shafts only on authored walls; native-style icons (Claude Code session, in progress)

**Shafts.** `render_lategame_studies.registration()` now emits `wallFaces`: horizontal faces of occupied cells toward open space where authored parts within 0.12 of the plane cover ≥60% of the face (4×4 samples). `wallTransputs()` (lategame_building_content.mjs, also used by the grocery) keeps only those faces plus ground-layer Bottom faces. Result: reactor 1,747 → 192 side faces, grocery 261 → 54. The factory audit (`outputs/alignment-audit/report.json`) found most generated faces ended in air.
- **Generation is blocked:** canonical generation stops explicitly until FertilizerWorks' study is rebuilt with the new field. Its art is mid-way through the late-game grid-alignment pass. Data is restored to the last good state (data-before12 snapshot).

**Icons.** All goods icons and most building/map icons now follow the measured vanilla style (`docs/art/icon-style.md`, renderer `tools/native_icon_style.mjs`, contact sheets in `docs/art/reviews/2026-10-21-icons/`). The 15 platform icons need promote. The MaterialsLaboratory and ReinforcedHydroTurbine icons are rendered in their integration folders, but no copy step exists yet.

## Grocery Market hall — generated and validated, not built yet (Claude Code session)

The approved Grocery Market study (`grocery_market_geometry.py`, scene `src/DeepFrontier/Art/Source/GroceryMarket-ReferenceStudy.blend`) replaces the gallery Grocery Store. It is grid-aligned: hall frame x 1–8 and y 2–6, balcony x 6–9 and y 1–2 with its deck top at layer 2, and post lines and footings on tile edges from z 0. Strict audit at frames 1/31/61/91: 0 visible conflicts.
- **Registration:** `register_grocery_market.py` writes `outputs/lategame-studies/GroceryMarket-registration.json` with the late-game rules (9×7×8; main door face 0.12 behind y = 2). It fails if the door walk (x 4–5, y 0–2) or the stair bay (x 8–9, y 2–4) is occupied.
- **Export:** `export_lategame_models.py --models GroceryStore` handles the 32-slot palette.
- **Blueprint:** `grocery_building_content.mjs` uses registration occupancy, merged colliders, shafts on solid walls and the native Entrance at (4,1,0). The balcony deck cells at layer 2 take player paths (layer-1 support is Stackable BlockObject), and the stair bay is left for native stairs. Shop behaviour is unchanged: stock, clerk (one tile inside the door), neighbourhood need, 2 workers, 100 hp. The old gallery walkway and navigation data are removed.
- **Validators:** `validate_grocery_exports.py` now checks the market contract. `validate_vertical_slice_content.mjs` reads its size from the registration. The catalog owner moved to the market pipeline.
- **Checks:** all promote validators, model bindings and the catalog audit pass.
- **Pending:** build 120 (the game was running with 119), then in-game shoppers, balcony paths and stairs.

## Build 119 — late-game pilot, platform variants, dam block top (Claude Code session)

Canonical generation and promotion ran. The FishHatchery, SandstonePit and LimestonePit blueprints were restored to Codex's last-written versions after each run, because the concurrent hatchery/pit generator refactor is unfinished. Official build 119 succeeded; `verify_deep_frontier_package.ps1 -Build 119` (pwsh 7): 520/520 hashes match the installed package. Contents:
- **NuclearReactor (20×15×22) and FertilizerWorks (9×8×13)** come from their late-game studies; see the pilot section below. Construction thresholds are none (single stage).
- **Eight ConcreteScaffold variants:** 3×3 H1/H2, 4×4 H1–H3 and 5×5 H1–H3, with meshes, icons and localization.
- **ReinforcedDamBlock:** support top exactly 1.0 (was 0.99). Posts stop 1 cm lower and the steel bands sit 7.5 mm proud and overlap at the corners. Strict audit: 0 visible, 0 occluded.
- **Validators:**
  - `validate_structural_sources.py` passes all 15 structures; scaffold seams carry an explicit 0.004 authored crown allowance.
  - `validate_model_bindings.py` resolves dependency (Redic.NewStyles) props from the installed file recorded in each native assembly.
  - `validate_vertical_slice_content.mjs` reads integrated late-game footprints from their registrations.
- **Compiled but inert:** the waterside C# components (`Scripts/Waterside`) compile into the DLL, but no blueprint uses them yet. The global placement validator returns valid for objects without `AdaptiveSupports`.
- **Not yet verified in game:** reactor and Fertilizer Works placement, entrances, shafts, colliders, CompactWaterWheel props, construction look, the reactor pipe inlet, and the platform variants stacking and being walked under.

## Late-game integration pilot — built in 119 (Claude Code session)

`tools/lategame_batches.json` lists studies that replace their 3×3 prototypes: pilot NuclearReactor (20×15×22) and FertilizerWorks (9×8×13). Pipeline:
- `render_lategame_studies.py` writes `outputs/lategame-studies/<Ident>-registration.json` from the authored parts: occupied cells (parts reaching 0.15 into a cell), and per door the doorstep, native Entrance path cell and face offset. Wall-mounted parts ≤0.3 proud of a door face leave its path cell free. `--registration-only` rewrites registrations without a scene while `artHash` matches the saved study.
- `export_lategame_models.py` (official Timbermesh exporter) writes `outputs/lategame-integration/Data/...` plus entrance slots; native props are referenced, not embedded.
- `lategame_building_content.mjs` is called from `create_frontier_expansion_content.mjs` for listed ids. It writes the occupancy blocks (ground cells GroundOrStackable), Entrance and LocalAccess, shafts on every solid wall, merged box colliders and the study's own construction stage. It also calls `applyNativeBuildingAssembly`, then copies the meshes into active data. Invalid doors fail explicitly.
- Prototype exporters skip integrated ids; catalog ownership for the pilot moved to the late-game pipeline.
- Reactor coolant inlet: cell (0,0,0) facing Down. The WaterTreatmentPlant port stays on its 3×3 prototype until that study is integrated.

Dry run over all 20 registrations: 14 pass. ChemicalWorks, ElectrolysisPlant, PrecisionMachineWorks, RadioactiveWasteRefinery, RadioactiveWasteVault and UraniumProcessingPlant need door faces moved to a tile edge (in progress). DeepDrill/DeepMine also need understructure handling. Not yet run: canonical generation (blocked by the concurrent hatchery work), validation, build and in-game checks. In-game checks still owed: CompactWaterWheel props animating, the construction stage look, and pipe connection at the reactor inlet.

## Vanilla shafts restored — build118 installed (Claude Code session)

Power Lines 11.1.1 (required dependency) overrides vanilla `PowerShaft`, `VerticalPowerShaft` and `ImpermeablePowerShaft` with `"PlaceableBlockObjectSpec": {"DevModeTool": true}`, hiding them outside dev mode. The new `tools/vanilla_tool_overrides.mjs`, imported at the end of `create_vertical_slice_content.mjs`, writes same-path partial blueprints setting `DevModeTool: false` for IronTeeth and Folktails. Deep Frontier loads after Power Lines, so its value wins. The MoreGroups workshop mod separately moves all shafts into a "Shafts" sub-button under Power.

Canonical generation was blocked when this was built: `hatchery_building_content.mjs` needs the not-yet-produced `outputs/reference-studies/FishHatchery-structure.json`. The override script was therefore run alone. Official build118 succeeded. Verification shows 470/474: four quarry meshes were rewritten in `src` at 14:14 by the concurrent door work, after staging. The installed package carries the previous quarry meshes.

## Shafts on every solid wall and pipe-fed lab water — build117 installed (Claude Code session)

User direction: gears should connect to essentially any solid wall. The new `tools/power_faces.mjs` `solidPowerFaces()` gives every `All` cell a transput on each horizontal face whose neighbour is open (outside the footprint or `None`), plus `Bottom` on the ground layer. Faces toward the entrance and doorstep cells are excluded, and existing authored sockets are kept first, in order. It is applied in the research, fishery, hydro and industrial generators. Restaurant and Hospital already used `roomPowerFaces`. Not applied:
- Deep Drill and Deep Mine (understructure mine template)
- the 3×3 prototypes, which use it when their late-game models are integrated
- Grocery (redesign pending)

Shaft cells: Lab 3→252, Fishery 2→155, Hatchery 2→53, Hydro 3→146, Kiln 16→86, Crusher 17→59, Mixer 16→96, each Quarry 23→158.

Timber Pipes 11.4.0 `DefaultBuildingConnectionProvider` sets `anyFace=true` when no `BuildingPipeTargetPortsSpec` exists. It connects only if the building holds a liquid good (`outputs/modding-api-audit-1.1/TimberPipes.cs`). So `MaterialsResearch` now takes 1 Water, and the lab has no port restriction. A flanged socket on the instrument tower's bay face marks the intended spot. `validate_research_exports.py` and `verify_research_workbook.py` expect the new recipe. **The balance workbook still needs regenerating** with the `@oai/artifact-tool` runtime (not available to Claude Code).

All export, binding and content validators pass. Official build117 installed. Verification shows 472/474 files matching: the two CementKiln meshes were rewritten in `src` at 13:45:46 by the concurrent door work, after this build. They are not part of build117.

Not yet run in game: shaft connections on the new faces and pipe delivery.

## Materials Laboratory service bay — build116 installed (Claude Code session)

User request after the build115 in-game look:
- The front specimen-shelf awning now carries back to the hall's cast base (`awning_back=1.62`) instead of floating.
- The stray planter between the press and the instrument tower is removed. Grid cells (8..9, 3..4, 0) stay unoccupied as a player service bay. The hall wall facing it carries the native shaft socket (transput (7,4,0) Right), a framed conveyor intake hatch on cell (7,3,0) and a Power Lines insulator. `PowerLineSpec` gains its second location (7.975, 3.5, 2.66).
- The records-office windows are centred in their `framed_room` bays: side crosses at y 3.675/4.825/5.975, front lancets at x 0.68/2.32.
- No pipe port was added, because the lab's recipe (Gear, Concrete, MetalBlock) has no liquid input.

Checked export showed zero visible conflicts at 0.0005, and no new 4 mm conflicts from the bay or windows. Promotion validators passed. Official build116 matches all 474 hashes. Belt and Power Lines attachment at the bay has not been tested in game.

## Window intent, door path entrances and pipe-fed coolant — build115 installed (Claude Code session)

User-requested export while the door-component refactor was in progress; build115 therefore contains the door/portal source state at about 12:50.

- **Windows.** `native_window_atlas.py` adds whole shipped `WindowsAtlas.IronTeeth` cells and steel/timber `glass_curtain` glazing. Materials Laboratory goes from 36 identical District Center windows to eight purposeful types. Restaurant: dining picture window, side crosses, rear triples and kitchen grids; the 0.25-scale diamond row is removed. Atlas cell UVs are registered in `native_uv_contract.py`. Both lab portals use `facade='grid'` because the cast opening and terrace slab already supply the reveal; the new inward cavity faces otherwise duplicated them (32 official-tolerance conflicts).
- **Entrances.** The native `Entrance` is now the path cell in front of the ground door (vanilla convention), so adjacent player paths can draw their connection stub: Restaurant (2,1,0), Hospital (7,1,0), Materials Laboratory (1,-1,0). See `docs/art/grid-alignment.md`.
- **Coolant.** Reactor `OpenIn` and Water Treatment Plant `OpenOut` Timber Pipes ports from `tools/coolant_pipe_ports.json` (see `docs/transport-adapters.md`).
- **Checks passed.**
  - Checked export, zero visible conflicts at 0.0005 for both models.
  - Restaurant shell: 118,893 probes, zero uncovered. Review re-archived in `docs/art/reviews/2026-10-21-exterior-repair/`; previous images were kept outside the repo.
  - Native window mounts zero findings, and an equivalent backing check of all 71 atlas windows/panes zero findings.
  - `promote_style_exports.ps1` with all validators and 48 model bindings.
  - Official build115, all 474 hashes match (`outputs/restaurant-package-verification115.json`).
- **Not run in game.** Path stub appearance, worker access at the new entrance cells, pipe delivery/withdrawal and save/reload.

## Selected Blender components and doorway joint — source/export verified, native update pending

The user requested selective asset rebuilds instead of whole-building/catalog regeneration. The restaurant's four portal assemblies are now separate named Blender objects with independent recipes. `tools/rebuild_building_components.ps1` requires exact model/component IDs and verifies every unselected object before saving. The one-time source migration retained all 62,857 architecture faces with the same stored geometry, UVs, materials, provenance and bevel weights. A single-door test rebuilt 41 faces in 4.259 seconds while preserving 250 other objects. The later grid-joint correction reduced each door to 37 faces and changed only the four selected portal objects; 247 other objects remained identical. No whole-building generator or rendering was invoked by these edits. The rest of the static architecture is not yet divided into independent recipes; extract its selected component before future edits instead of regenerating the catalog. See `docs/asset-pipeline.md`.

The screenshot's recessed entrance treatment exposed a source winding defect: the cavity return faces pointed away from the doorway interior. The shared recessed-portal source now faces them correctly, checked by the source entrance contract. For the restaurant's grid rooms, the correct joint is a flush plaster insert at the room's authored 0.04-depth plane. That removes the recess gap and duplicate lower-trim caps; it does not add a two-sided shader, depth bias or runtime repair. The official export is staged in `outputs/civic-integration/Data/Buildings/Food/Restaurant`. Strict overlap audit: zero sampled visible candidates. Evaluated source shell: 118,893 coverage probes, zero failures. Actual export: 14,400 isolated-door coverage probes and 2,880 oblique wall/corner probes, zero failures. Export SHA256: `b184c707cee6ba4c3077620d37a1fa6cb553eb16a521be3c710920e4361b22b3`. Evidence: `component-restaurant-export.log`, `restaurant-component-shell.json`, `restaurant-component-export-culling.json`, `component-authoring-contract.log` in outputs.

The exported coverage checker explicitly reverses the official exporter's Unity triangle ordering when decoding into Blender's BVH. The earlier `door-culling-installed114.json` result used the wrong ordering and is not valid export evidence. The isolated source winding diagnosis is separately verified. At this earlier checkpoint build114 was the last installed/native-tested version; build115 installation and its actual exported-mesh check are recorded above, with native appearance still pending. The verified earlier source SHA256 is `9a35ed028c37606a9625e6b77013bc0f9854f913d79248a00c88483b2920dbe1`, archived at `outputs/component-rebuilds/Restaurant-doors-verified-20261021.blend`. An independent process subsequently changed the canonical source at 12:48; its changes were preserved, and the earlier audit is not claimed for that later whole scene. The targeted rebuild tool now also refuses to overwrite a source file changed by another process while open. The interrupted broad source job saved Hospital, StoneCrusher and CementKiln before the user stopped that approach; those newer sources were not exported/installed at that checkpoint. Prior build114 evidence below belongs to its archived revision.

## Exterior closure, distinct hospital and native mirroring — build114 installed and native tests passed

The reported restaurant gaps were literal missing roof-sheet/gable surfaces, small-roof curbs, joined-room corner strips and a vestibule roof cell. These are repaired in the producing geometry. Its evaluated shell passes 118,893 coverage probes; 43 native windows pass 1,240 backing probes using explicit wall anchors and physical timber reveals. The exact wall-junction close-up supplied by the user has been rerendered from the repaired source. All six matching views and source hashes are in `docs/art/reviews/2026-10-21-exterior-repair/`. A clean overlap report alone cannot detect holes or floating windows.

The hospital now has two substantial ward wings with separate long roofs around a transverse central pavilion. Registration is 14×11×9, with four one-tile doors at levels 0/2/4/6, sixty decorative rail openings, fifteen short supports and a clear 4×3 roof garden. Its source shell, roof, window-contact, walking-clearance and overlap checks passed, followed by official export. Four matching views are in `docs/art/reviews/2026-10-21-hospital-wings/`. The workbook's twelve affected Hospital cells were updated, preserving all sixteen sheets and eleven formula results. Native care, placement and fresh-process reload passed in build114 as recorded below. This enlarged footprint is not a migration of existing older hospital placements.

Every producing generator now explicitly sets native `BlockObjectSpec.Flippable` to true; the canonical audit confirms all 41 templates. Native build114 passed all 328 preview placements and 76,800 point probes: four rotations and both flip states for every template, including native entrance coordinates (`outputs/mirroring114.log`). Native `BlockObject` mirrors its model transform, cell coordinates and entrance and persists `Flipped`. The restaurant's native F button was also visibly confirmed in the actual placement UI (`docs/art/reviews/2026-10-21-exterior-repair-runtime/restaurant-native-F-option.png`). These results do not verify keyboard input or every custom path, power, seating or saved-placement scenario.

All twenty detailed scenes have fresh matching-source strict overlap reports with zero sampled visible conflicts at frame one. The other architectural sources pass 26 opaque-surface contracts / 1,088,252 rays and 176 native-window backing checks / 880 rays. The Grocery's dangling roof-terrace posts were replaced with short connected cantilevers, preserving its footprint and checked clearance. Twenty-two front/rear architectural views across eleven models are in `docs/art/reviews/2026-10-21-catalog-shells/`; seven structural scenes have fresh strict source reports without new paired renders.

The twenty older prototypes also passed their separate strict overlap, closed-component and 50,160-corner native-UV checks. Reactor/cryo join defects were fixed in their producing generator. Their report is `docs/art/reviews/2026-10-21-prototype-surface-audit/`; these remain prototype architecture, not completed detailed art or grid migration.

Canonical content, ten detailed export validators, all 48 model bindings, restaurant grid/recipe/content checks and the all-building ownership/mirroring audit passed. Official build114 installed successfully; all 474 authored data/manifest/DLL hashes match (`outputs/restaurant-package-verification114.json`). Native test results are recorded separately below.

Native hospital114 main run passed placement, full 600 hp shaft supply, native stairs, roof platform stacks, four door connections and selective decorative rail visibility. It reserved exactly thirty patient places, treated real injury/teeth/contamination cases with six separate staff, consumed real supplies, stopped/resumed care with power and staff availability, and walked a beaver to eight authored destinations. The sampled full-staff/control injury ratio was 1.747 against the 1.8 target within the fixture's discrete-cadence tolerance. Capture verified all 87 native placement identities/coordinates in `outputs/hospital-verified-build114.timber` (SHA256 `9a119b8cca7f8c7460e704a0298a512a32c371af472752acf9e3937281533b02`). Matching in-game views are in `docs/art/reviews/2026-10-21-hospital-wings-runtime/`. The old baseline's obsolete pit placements were removed by the native loader; this disposable fixture result does not establish user-save migration.

Fresh-process hospital114 reload passed exact identity, pause state, stocks, fractional supplies and patient needs. A real observer gained neighborhood wellbeing in range, lost it outside range, stopped receiving it when medicine and its fractional buffer were exhausted, and regained it after replenishment. Three staff produced the expected reduced treatment rate, measured 0.009666424 injury points/hour. All 87 original native placement identities/coordinates survived in `outputs/hospital-continuity-build114.timber` (SHA256 `99a495f4a5b7e75e37196e939ff62e2c935e95273464e8ffa165813c8eb56cad`); see `outputs/hospital-continuity-verification114.json`. These main/reload results cover the authored unmirrored test orientation, not every rotated neighboring-building arrangement.

Native restaurant114 main run passed shafts at three heights, four door connections, both directions across native stairs, under-deck paths/shafts/tubeways, platform stacks, solid-room rejection and selective rail opening on both sides through path creation, deletion and recreation. Five actual walking destinations passed. Workers served seated diners real foods, four freshly baked cakes, coffee and water with thirst and stock accounting. The final archive contains all 90 recorded placement identities/coordinates, including 69 native paths and a native Rooftop Terrace on the unchanged white deck. Archive: `outputs/restaurant-grid-run114.timber`, SHA256 `78a0bcdb1038441f25a85093f02b59c163852c96132e1bd2b394766fc6092f8f`.

Fresh-process restaurant114 reload completed saved service without duplicate receipts, passed Pause/Resume, power loss/restoration and off-duty/on-duty transitions, and preserved all 90 placement identities/positions. Capture: `outputs/restaurant-grid-reload114.json`; archive SHA256 `6e4789ee5937df8bc193f1fb2c6b90b741ef93dd0988365d3f223220f5a56aef`. Matching game screenshots are in `docs/art/reviews/2026-10-21-exterior-repair-runtime/`. Main/reload checks cover the authored unmirrored orientation; wider neighboring-building arrangements remain separate.

`tools/building_asset_catalog.json` explicitly records ownership for all 41 active templates: 21 templates use twenty detailed scenes; twenty retain older prototype scenes. `tools/audit_building_assets.py` rejects missing owners and records source/export hashes, while `--require-mirroring` checks every generated blueprint. Closed prototype component meshes do not imply detailed visual, grid or native-style acceptance.

Historical build113 installed 474 matching authored artifacts and passed live restaurant placement, rail, power, five walking targets and dining/cake/coffee/water checks. Its final save archive check failed because the Rooftop Terrace was absent at the expected recorded coordinate. Do not treat that save as verified or reuse it as a reload baseline. User stopped Computer Use; no further input was sent in that turn. Its source previews are in `docs/art/reviews/2026-10-20-restaurant-roof/`; they predate the current missing-surface repairs.

## Window variety — build112 installed

The user requested variety after the larger-window review. Build112 explicitly composes four original New Styles assemblies: District Center grand pointed windows, Flat tall narrow windows, Flat diamond accents and Foodplant factory grids. Uniform scales preserve each assembly's proportions. Restaurant main dining windows remain large; its upper floor uses tall narrow windows, the ground service frontage uses grids, and dormers use diamond accents. Hospital, Grocery and Fishery have different floor/function arrangements. Eight exact-source renders are archived in `docs/art/reviews/2026-10-20-window-variety/`, alongside the original source comparison. These are Blender previews.

All five civic scenes passed strict overlap checks and official exports. The first check caught a Grocery clerestory post intersecting the new narrow window; its source framing now uses corner posts clear of the continuous window row. All twenty source reports again have zero sampled visible candidates. Four styles in four orientations retain original triangles/UVs; factory panes face outward. Civic export checks and all 48 model bindings passed. All **212 gameplay C# scripts and blueprint definitions are byte-identical** before/after this art revision (`outputs/window-variety-runtime-diff.json`). Official build112 installed all **474 matching artifacts** (`outputs/restaurant-package-verification112.json`).

Fresh-process native112 loaded the verified build111 main save and passed saved-service completion without duplicate receipts, Pause/Resume, power loss/restoration and staff off-duty/on-duty transitions. Capture explicitly uses baseline build111 and preserves all **81 entity identities/positions**. Archive: `outputs/restaurant-grid-reload112.timber`, SHA256 `2358e1f7eb0649771156435e4c0df35d6d553459528033b2b1c175a754d9aece`. The daylight paused in-game view is `docs/art/reviews/2026-10-20-window-variety/Restaurant-native112.png`. Other civic buildings' matching Blender previews remain source appearance evidence; build111 below contains the preceding full placement/walking run with identical gameplay definitions.

The small Barrack diamond windows were rejected for two-block-high storeys. The shared window source now reuses the larger pointed, multi-pane assembly from the required REDIC New Building Styles 0.1 District Center, including its original crown, sill, panes and atlas UVs. Restaurant main-storey windows are approximately 0.86 wide by 1.18 high; doors remain separate complete 1-by-1 inserts. Eight fresh civic isometric renders and exact source hashes are archived in `docs/art/reviews/2026-10-20-exterior-facades/`. These are Blender previews, not installed-game captures or user approval.

All **twenty** current detailed source scenes now have **zero sampled visible overlap candidates at frame one**, including all eighteen originally flagged scenes. Exact current source and detector hashes pass `tools/asset-pipeline/summarize_surface_audits.py`; see `outputs/zfight/index.json`. Corrections are in producing geometry: disjoint wall skins, exposed facade spans, roof-bearing curbs, joined frame ends, plate setbacks, fitted crate lids, nonoverlapping footings and machinery fasteners. No exported-geometry cleanup, UV clamping, depth bias or fallback was added. Occluded joints and unsampled animation poses still require separate interpretation; this is not a proof of GPU behavior.

The restaurant's invisible room partitions/furnishings were removed at source while exterior seating and native internal navigation remain. Its doorway uses the original Large Barrack frame/recess inside a closed one-tile insert; coverage tests include oblique perimeter seams. Shared imported native pieces preserve their UVs and finished edges rather than receiving another bevel. Other buildings have not yet all migrated to the restaurant's whole-cell structure or exterior-only room declarations.

The current source also contains forty-nine restaurant decorative rail openings, covering all physical boundary cells independently of suggested road routes. Outdoor navigation blockers were removed from `PlatformDeck`; native player paths own outdoor connectivity. Both side seams now have create/delete/recreate fixture assertions. All twenty strict checked official exports succeeded. Canonical content regenerated; ten export checks, five saved civic source checks, restaurant content/grid tests and all 48 template model bindings passed. The old hydro candidate blueprint initially referenced retired rail nodes; regenerating that candidate from the same canonical generator fixed the stale test input. The shipping blueprint was already current.

Official build111 succeeded and all **474** authored data/manifest/DLL hashes match the installed package (`outputs/restaurant-package-verification111.json`). Native111 passed player path/platform/stair/under-deck placement, enclosed-room rejection, 400 hp operation and actual shaft graphs at three levels. Both side rail sections passed path creation/deletion/recreation while the adjacent unsupported section stayed visible. All five actual beaver walking targets passed. Native cooking produced four cakes; workers served seated diners real foods, optional coffee and water, with matched stock/meal accounting. The test continued serving without coffee and checked thirsty versus hydrated diners. Capture preserved **81 entity identities/positions**, including 61 native Path entities, in `outputs/restaurant-grid-run111.timber`, SHA256 `3517a92187be98e03af9e6050b026bfb696e212b6bea918e267dd8d03c25ab68`. In-game appearance is archived as `Restaurant-native111.png` in the facade review. Fresh-process reload/interruption verification passed as detailed below. Wider rotations, neighboring restaurant combinations, animated surface checks and broader building grid migrations remain separate.

Fresh-process native111 reload also passed: previously served guests left without duplicate receipts, saved service finished, and Pause/Resume, power loss/restoration and staff off-duty/on-duty transitions released guests and stopped/resumed serving correctly. All 81 saved entity identities/positions matched the main run. Archive: `outputs/restaurant-grid-reload111.timber`, SHA256 `2306fe67e316af998c71be52fb95e72185f32f45e6b7e50d2b64c5ba4464b94f`.

The first run109 exposed an obsolete fixture assertion: a native platform's ordinary floor stays connected with no neighboring Path, while decorative rails stay visible. The corrected test declares expected floor connectivity separately for the supported seams and adjacent unsupported panel, then checks actual Path presence and rail visibility. Build110 was an intermediate fixture; build111 is the completed native main/reload pass. The decorative rail adapter was unchanged between these tests. The old reservoir test save also contained obsolete Sandstone/Limestone Pit placements which the native loader removed as invalid; this was a disposable fixture, not a user settlement migration test.

## Surface overlap detector — 2026-10-20

`tools/check_building_surfaces.ps1` audits evaluated Blender triangles for same-facing near-coplanar overlap, material/UV disagreement and sampled exterior visibility. It writes exact face/material/polygon records and optional red diagnostic images. All nine synthetic positive/negative cases passed. The historical baseline found candidates in eighteen of twenty scenes; it is preserved in `outputs/zfight-baseline-2026-10-20/`. The current index records the repaired sources described above. Pair counts are not distinct visual-defect counts, and the earlier narrow plaster-wall test did not cover the frame, trim and deck defects found by this general detector.

`tools/export_checked_models.ps1` runs a fresh strict audit before invoking the existing official Timbermesh exporter. Its tested failure path rejected Restaurant and left the game scene and official Timbermesh SHA256 hashes unchanged (`outputs/zfight/checked-export-test.json`). A strict SandstoneMasonryBlock frame-two audit passed; an unrendered report correctly omits any image link. The official exporter itself is unchanged. Existing exports and packages are not retroactively certified. Workflow and geometric/GPU limitations: `docs/art/z-fighting-checks.md`.

## Grid alignment and player-built deck paths

The user's latest decision is that decks behave like native platforms: players place their own paths. The restaurant is the first migration. Whole-cell structural modules now produce visible platforms, closed room boundaries and exact picking boxes together. Its four door thresholds are grid-aligned; exposed room faces accept shafts on multiple levels. Fixed dining/garden furniture reserves its occupied cells. `PlatformDeck` only gates rails from actual finished Path/Stairs edges on both sides. Outdoor roads belong to player Path entities; indoor links remain native building navigation. No filler-plank joins, coordinate normalization or fallback lookup is used.

Build 107 passed actual player path placement, stacked native platforms, vanilla stairs, under-deck path/shaft/tubeway placement, solid-room rejection and shaft graph connection on three levels. Its fixture then stopped because it searched railing names across both finished and unfinished trees; the component itself already scopes the finished tree correctly. The fixture is corrected. The user rejected the dense support grid and coincident plaster/wood surfaces seen in 107.

Build 108 has sixteen explicit short posts, no outer roof terrace ground legs and 110 exact picking boxes (previously 636). Native occupation now reserves post cells only. Broad plaster and wood wall faces are separated at source. The narrow mesh audit checks 5,742 facade/frame rectangles with zero coplanar broad plaster/wood overlaps; source aisle, terrace, seat/rail, official export and blueprint checks pass. The later general detector finds remaining joints and trim conflicts. Official build 108 installed 474 matching authored files. Native `ALL PLATFORM DECK CHECKS PASSED` covers actual player paths, stacked native platforms, under-deck path/shaft/tubeway, room rejection, power graphs at three levels, selective rail creation/deletion and bidirectional door/stair graph links. Actual walking, restaurant service and fresh reload remain pending while the simulation is paused. Other buildings retain their prior walkway implementation until migrated and tested; do not report all buildings fixed. See `docs/art/grid-alignment.md`.

## Native style pass, housing rails and Materials Laboratory

User selected REDIC New Building Styles (Workshop 3723883597) for all new building surfaces/details and specifically selected double-height housing railings. The complete package is subscribed/downloaded; manifest requires exact ID `Redic.NewStyles`, minimum `0.1`. It uses original native material atlases rather than shipping replacement texture images. See `docs/art/iron-teeth-style.md`. Build 107 installed the dependency declaration; native startup confirmed New Building Styles loaded. All 474 authored package hashes matched.

Materials Laboratory source is 12,000 science, 600 hp demand, four workers and 800 science per two-hour batch. Official build 106 passed native placement, shaft, stairs, deck platform and rail checks, but production failed because Paper is absent from the Iron Teeth goods collection. The canonical recipe is corrected to four Gear, two Concrete and one MetalBlock; generator now rejects ingredients missing from the actual faction collection. Regeneration and native production/reload testing remain pending. Do not call build 106 production-ready.

## Shared-reservoir hydraulic acceptance — native build 105 passed

Added an explicitly launched two-turbine fixture with sealed upper/lower basins, independent 0.75/1.5 m³/s controls, full-column water and contamination accounting, native evaporation integration, reverse-head and dry-intake checks. It creates only a separate marked test area in the disposable acceptance settlement. Approved turbine art, physics and rating are unchanged. Build 104 rejected a missing `Timberborn.BlueprintSystem` import in the new fixture; corrected at source. Official build 105 succeeded and all 468 authored package hashes match. `tools/start_hydro_basins.ps1` launches the test; `tools/capture_hydro_basins.py` requires its completed native save and measured assertions.

Native run 105 passed both independent limits with **2,400 and 4,800 actual native hp**. Clean and 50%-contaminated two-hour windows each integrated 85.725 m³ of gate flow. Over about 3,205 m³ of stored water, the water-accounting residual after native evaporation integration was −0.113 m³; upper-reservoir loss versus integrated gate flow differed by 0.675 m³ (within the declared 2 m³ tick-sampling allowance). Downstream contaminated concentration was 50.047%; contamination-volume residual was −0.016 m³. These are bounded measurements, not mathematically exact conservation claims. All 32 reverse-head samples and 17 dry-intake samples had zero custom and native hp on both turbines.

Capture verified all **496 created entity identities/positions** and saved distinct discharge limits/manual closure. Native archive: `outputs/hydro-basins-build105.timber`, SHA256 `c8a5d0795f5ae7b3c9081fd88ef141653035974adad6af45d5b49a9b52d802e5`. Report: `outputs/hydro-basins-verification105.json`; measurements: `outputs/hydro-basins-measurements105.json`; log: `outputs/hydro-basins105.log`. In-game contaminated-flow screenshot: `docs/art/reviews/2026-10-20-hydro/Turbine-basins105-badwater.jpg`. The game is paused with both gates closed and a refilled clean upper basin. This test adds shared-reservoir, badwater, reverse-head and drought coverage; pump-loop energy balance, further lifecycle/rotation combinations and fresh-process reload of this two-unit save remain separate.

## Turbine sound and faster blades — build 103 passed native audio, motion and reload checks

User requested a turbine sound and faster blades. The canonical hydro catalog now selects the native Wind Turbine's `Gristmill` mechanical loop and a required animation multiplier of 4. The generator preserves native `PowerGeneratorSoundsSpec`; the existing native controller starts/stops the spatial building loop from actual mechanical activity. `HydroTurbine.RefreshAnimation` applies the multiplier to both existing runner/shaft tracks, preserving measured-flow dependence, simulation speed and zero-output stopping. No geometry, costs, discharge, head or hp tuning changed.

Candidate export validation passed. An exact blueprint comparison allowed only `BuildingSpec.LoopingSoundName` and the added `HydroTurbineSpec.AnimationSpeedMultiplier`; both were promoted from the generator. Official build 103 succeeded, and all **468 authored data/manifest/DLL hashes** match the installed package (`outputs/restaurant-package-verification103.json`). Build 103 adds measurement instrumentation to the explicit acceptance fixture; gameplay is unchanged from 102. After the user authorized using the latest save, a fresh game process restored all **709 fixture identities/positions**, saved 0.75 discharge/manual closure and native lever wiring.

Native reload 103 measured **4.00× animation playback** from public `IAnimator.Time` advancement against integrated reference speed at both 0.75 and 3 m³/s. Actual native output was **2,400 and 9,600 hp** respectively. The building's spatial `Environment.Buildings.Loop.Gristmill` source played through the `Building` mixer and produced nonzero waveform RMS at both rates. Building Pause and manual closure disabled the animator and faded source volume to zero. Native fade leaves `AudioSource.isPlaying` true; zero volume is the verified silence condition. Resume and all five actual beaver walking destinations passed. This verifies source playback programmatically; subjective sound quality was not assessed by listening.

Capture passed: `outputs/hydro-continuity103.json`; samples: `outputs/hydro-reload-measurements103.json`; log: `outputs/hydro-reload103.log`. Native archive `outputs/hydro-continuity-build103.timber`, SHA256 `f35da5416a326645d6a4779dba5e193194ea405a5f9163da80bf730bafbb5498`. The maintained Timberborn skill records the native three-second fade and actual animation/audio verification procedure. Extended hydraulic and pump-loop balance coverage remains separate.

## Reinforced hydro turbine — two-cell main 100 and fresh-process reload 101 passed

Latest user revision is installed: maximum combined discharge **3 m³/s**, **9,000 hp at 15 layers of head**, capped at **9,600 hp at 16 layers**. The new 8×10×7 model has two adjacent native water lanes, a four-tile casing/cap and the preserved powerhouse translated one tile sideways. The casing ends at the actual six-tile physical water-wall boundary. Each lane receives half the player's discharge limit; its actual incoming gate crossing and head contribute to native shaft output. No decorative water or substituted flow measurements are used.

Native main 100 passed both wet lanes, measured 0.25/1/3 m³/s limits, maximum **9,600 native hp**, manual closure, automation, native Pause/Resume, a sustained settled blocked-outlet stop, shafts, stairs, deck/cap stacks, selective rails and all five actual walking destinations. Capture verified **709 identities/positions**, saved 0.75 limit/manual closure and native lever wiring. Archive `outputs/hydro-verified-build100.timber`, SHA256 `731de768a2a56c0b1ce5195fe03842995eb024bd538af6e2f435053f1107dda0`. Samples at 0.25/1/3 m³/s produced 800/3,200/9,600 actual native hp with sufficient head.

Official build 101 installed all **468 matching artifacts**, including the final casing-length refinement. Fresh-process reload restored all 709 fixture identities, saved controls and wiring, then passed measured 0.75 m³/s / 2,400 native hp operation, rotor motion, native Pause/Resume and five actual walking destinations. Completed continuity archive `outputs/hydro-continuity-build101.timber`, SHA256 `32e25adaaa9908673e2e5a6423a492d1979dcdcba128c9429189b317158431c6`. The subsequent UI review set 3 m³/s and opened the outlet: **3.000 m³/s, 15.19 layers of head and 9,113 native hp**, with water spanning both mouth cells. The game was left paused on this review view. Screenshots: `docs/art/reviews/2026-10-20-hydro/Turbine-native-reload101-power.jpg` and `Turbine-native-reload101-outlet.jpg`.

Source checks passed 164 route samples, 32 cap-support samples and both 121-frame loops. Export checks passed all 24 horizontal water planes, 104 full obstacles, 21 support cells and 14 adaptive openings. The regenerated workbook records the same dimensions, total flow limit, maximum output and current verification status. Extended hydraulic tests and actual dependency pump-loop balance remain pending: the requested 200 hp/(m³/s·layer) coefficient exceeds Timber Pipes' idealized pump-energy bound. No dependency costs were changed. Historical 97 results below refer to the earlier one-cell geometry.

Workbook verification passed structural/hydro catalog parity, concrete construction requirements and restaurant data. All four vanilla sheets retain their values, formulas, formatting and tables. Formula-error inspection found no errors; affected workbook previews were reviewed. The structural checker now explicitly reads canonical JSON as UTF-8 rather than the Windows default encoding. The maintained Timberborn skill passed validation.

Historical run 99 reached 9,600 actual native shaft hp with both wet lanes but failed the blocked-outlet test. An outside probe lay inside the new plug and reported zero water level instead of pressure behind it. Failed measurements are preserved in `outputs/hydro-measurements99-failed.json`. Build 100 corrected the authored tail-pressure probes to the final clear conduit cells and passed a stable settled zero-flow/zero-power interval after pressurization. Run 99 is not a passed full acceptance run.

Hydro update: corrected native valve probe 92 passed 0 / 0.25 / 1 / 0 m³/s phases with settled discharge maxima 0 / 0.249844179 / 0.999844134 / 0. The new original turbine has a downstream powerhouse, explicit 7×10×7 registration, a layer-two service terrace and layer-six cap. Saved Blender route/support/UV/animation checks and official export passed. Official builds through 97 installed all 468 matching package files, including the native-water-service controller and automation/persistence panel. Main and fresh-process reload 97 passed the single-unit fixture; extended hydraulic and pump-loop tests remain pending.

Native turbine run 94 stopped during its fourth dry rotation because the trial anchor put part of the rotated footprint outside the existing cleared pad. Run 95 corrected those trial anchors and passed all four dry rotations, native shaft connection, selective rails, vanilla stairs, deck/cap platform stacks, dry zero output and closed-reservoir retention. Actual generation and rotor motion occurred, but the quarter-flow phase failed: its measured outgoing peak was 0.3636943 m³/s against a requested 0.25 limit. No verified turbine save was written.

Native source inspection established that SetInflowLimit caps the edge entering the aperture's column. The downstream edge previously sampled can emit stored pressurized water in pulses. Build 96 measures the actual incoming gate crossing instead, without replacing observed flow with the requested value or clamping it to that setting. Its first launch was interrupted during loading; the incomplete log is preserved as `outputs/hydro-run96-interrupted.log`. The resumed result follows. Native partial appearance is preserved in `docs/art/reviews/2026-10-20-hydro/Turbine-native-integration95.jpg`.

Resumed main 96 passed 0.25/1/3 m³/s gate limits, finite drawdown, actual runner motion and native shaft generation, manual closure, lever Off/On, blocked-outlet cessation and five actual walking targets. Capture verified all 211 entity identities/positions, saved 0.75 discharge/manual closure and the exact native lever connection. Archive: `outputs/hydro-verified-build96.timber`, SHA256 `867330dc59930629fe7e85bd902ced79616543eedd92e5a983abd0c5dee443d4`. All 47 model bindings passed. Native panel screenshot: `Turbine-native-main96-panel.jpg` in the hydro review directory.

Fresh-process reload 96 restored all identities, controls and wiring, then failed its shaft-output assertion. The fixture paused every existing PausableBuilding during setup, including the loaded turbine; the native MechanicalNode correctly suppressed power while the custom gate continued flowing. Build 97 narrows fixture pausing to workplaces and defines ordinary turbine Pause as gate closure, zero output and stopped animation through native PausedChanged. Resume retains its limit/manual/automation settings. Main and reload now explicitly exercise Pause/Resume and record native node/graph hp alongside measured generator hp.

Official build 97 installed all 468 matching package files. Main 97 passed the full previous sequence plus native Pause/Resume, and its captured samples match the native integer shaft output. All 211 saved records, controls, wiring and five walking targets passed capture. Archive: `outputs/hydro-verified-build97.timber`, SHA256 `fbff5ffb50745f9a90d6a60edbb9b14f175285a8e3fff9872cdc9323c48554ea`. Daylight native screenshot: `Turbine-native-main97.jpg` in the hydro review directory.

Fresh-process reload 97 passed exact restoration of all 211 identities/positions and saved controls/wiring, renewed measured 0.75 m³/s operation, native shaft supply, actual rotor motion, Pause/Resume and all five walking destinations. Completed continuity archive: `outputs/hydro-continuity-build97.timber`, SHA256 `618257769fb8850f77c5929794b8f59c2d348756c2b4bb2748dc770ba050bf56`. Both captures check actual native hp against the measured calculation, closure and exact automation IDs. Native screenshot: `Turbine-native-reload97.jpg`. This verifies a seeded single-unit fixture, not multiple turbines, badwater conservation, reverse head or pump-loop efficiency.

Build 98 introduced the turbine panel layout: label above the slider, native numeric input, and the existing native power row. These panel changes are included in build 101 and passed its final UI review; current catalog/workbook status is recorded above.

## Reinforced structures and advanced concrete foundations — main 90 / reload 91 passed

Seven original passive models are authored: sandstone/limestone masonry, concrete levee, reinforced dam block, concrete overflow dam, eight-tile reinforced overhang and a 3×3 four-layer scaffold. Saved Blender geometry passed 550 support samples, 66 open-passage samples, native UV and bound checks; official exports and all 46 template model bindings passed. See `docs/art/reviews/2026-10-20-structures`.

Official build 87 installed all 463 matching package files. Native placement passed all seven templates in four rotations, unsupported floating rejection, a twelve-layer masonry tower, stairs and platform stacks, and shafts/tubeways in open bays. The sealed basin retained actual water. The subsequent one-cell overflow test drained completely and failed; no verified structural save was written. Build 88 expands the test to matched 3×3 reservoirs with a native Dam control so spill behavior can be compared directly. Walking and reload remain unverified.

Build 88's two reservoirs drew down to exactly the same 0.04744648 depth, including the native Dam control. Thus the test's assumed 0.5–0.69 final-depth band did not match native transient behavior. Build 89 added actual crest registration and a separate below-crest replenishment check; its diagnostic incorrectly indexed the water array without the native border margin. Build 90 uses `MapIndexService.CoordinatesToIndex3D`. These fixture revisions do not change the shipped spillway or water simulation.

Native main 90 passed all seven templates in four rotations, unsupported placement rejection, native stairs/platform stacking, clear under-deck transport, full-wall retention, native 0.65 crest registration and six actual beaver destinations. The concrete and vanilla control pools both retained 0.3938513 after below-crest replenishment. Archive: `outputs/structures-verified-build90.timber`, SHA256 `80c5269828b12ef01d5cd7c827e4ebf84007872b12e5cd067159c0f30bf22ce6`; screenshot: `docs/art/reviews/2026-10-20-structures/Structures-native-build90.jpg`.

Reload 90 rejected the fixture's pre-save water expectation. The native artifact contains 0.3897473 depth; the earlier thread-safe snapshot recorded 0.389858961, before the remaining queued physics and save completed. The capture tool now produces the water checkpoint from the actual completed native save, using the inspected packed-column schema. Reload compares against that exact artifact checkpoint. This corrects the test's source of truth without changing water behavior or rewriting saves.

Fresh-process reload 91 passed exact restoration of 136 identities/positions and both saved water levels, then all six actual walking destinations. Its completed native save retained equal 0.3843088 depths in the concrete and native control pools. Archive: `outputs/structures-continuity-build91.timber`, SHA256 `eaeed8ba2cf8550759adb188ebc2e399f4cc99c8694463b42ede1f5b7183a0a3`; capture validation passed. Native appearance was inspected and preserved as `Structures-native-reload91.jpg` in the structural review directory. This establishes native support, water and traversal continuity in the seeded fixture; construction costs remain an initial balance.

Advanced foundation costs now require concrete in the canonical catalog/generators; starter pits, crusher, kiln and mixer remain buildable before concrete exists. The workbook includes exact authored costs and structural rows, while the new dam-base turbine remains in development. Its native valve probe, control implementation and installed Compact Water Turbine inspection are in `docs/hydroelectric-construction.md`. The workbook generator includes the provisional turbine catalog; regeneration and acceptance updates remain pending.

### Concrete platform size/height variants — authored and export-checked; native untested (2026-10-21)

Eight new templates extend the accepted `ConcreteScaffold3x3` (unchanged template, now displayed as "Concrete platform 3×3 (3 high)"): `ConcreteScaffold{3x3,4x4,5x5}H{1,2,3}` except the original 3×3 H3. Size is [n, n, H+1]; the deck is the top layer at exactly z = H+1. `structural_geometry.scaffold_for(n, legs)` produces all nine models; `scaffold_for(3,3)` reproduces the saved 3×3 source vertex-for-vertex. 4×4 and 5×5 decks add steel joists under every interior cell seam, inside the deck layer. Occupation: corner cells `Corners` below the deck (`GroundOrStackable` at z=0), `All` on the deck; other deck cells `Top`; everything else `None`; deck layer `Stackable: BlockObject`.

Cost formula, enforced by `structural_building_content.mjs` and the workbook verifier: k = n² + H; cost k × (3 Concrete, 2 Metal Block, 1 Gear); science 500k. Every deck cell and every leg layer carries the same 3:2:1 bill, and k = 12 reproduces the original 36/24/12 and 6,000 science.

Evidence: zero visible overlap candidates in all eight fresh strict audits (8 occluded pairs each, identical to the original 3×3), official Timbermesh export, `validate_structural_exports.py` (15 buildings) and the structural candidate blueprint generator. Reviewed renders: `outputs/reference-studies/ConcreteScaffold*H*-front*.png`. `validate_structural_sources.py` fails before reaching the variants: the existing `ConcreteScaffold3x3` scene's 0.004 raised deck-seam crown exceeds its 0.001 module-bound tolerance (the variants share that seam), and `ReinforcedDamBlock` fails its flush-support check. A scratch run of the scaffold scenes with only the bound tolerance at 0.005 passed every support, clear-passage and UV check. Pending: canonical generation, promotion of meshes and icons, build, workbook rebuild and native placement/stacking/traversal tests (the acceptance fixtures `StructuralAcceptance.cs`/`MirroringAcceptance.cs` do not list the variants).

Hydro probe 90 placed the native valve and concrete reservoir, then its diagnostic read failed because `INonThreadSafeWaterService.UpdateOutflowsData` requires singleton Tick. Build 91 moved sampling into ITickableSingleton and completed the diagnostic capture, but every recorded open-phase flow was zero. Source inspection identified the fixture's reversed valve: Cw0 admits +Y inflow, toward this reservoir, whereas its outlet is -Y. Build 92 rotates only that test valve to Cw180 and requires measurable increasing discharge in its two open phases and cessation when closed. Preserved 91 measurements: `outputs/hydro-control-probe91.json`. These are not turbine generation evidence.

The turbine Blender study is rendered and checked: 164 route/headroom samples, 24 cap supports, bounded native UVs and both 121-frame shaft/runner loops passed. The closed downstream workshop opens onto the layer-two terrace. Review renders and source hash are in `docs/art/reviews/2026-10-20-hydro`. Registration, official export and installation are complete; full native operational acceptance remains pending.

## Concrete mixer reference replacement — build 79 passed main and fresh-process reload

The right-hand isometric mixer in `02-concrete-production-concept-v1.png` now has a detailed Blender replacement: two feed bins, plated rotating drum, native header tank/barrels, enclosed operator room, layer-2 service gallery and separate adaptive rails. Canonical source is `ConcreteMixer-ReferenceStudy.blend`; registration follows the model at 8×6×7. Source checks passed 198 floor/headroom samples, native UV mapping and two 121-frame animation loops. Exports have 153 nodes and 23 rail openings. Review: `docs/art/reviews/2026-10-20-mixer`.

Official build 77 installed with 428 matching package hashes. Native run 77 passed shaft connection, 250 hp nameplate demand, stairs, deck platform stacking, under-deck paths/shafts/tubeways, enclosed-room collision, selective rails, five actual walking destinations, and header water at 0/4/8/0. Production remained blocked because the fixture's road stopped before the recessed local (1,0,0) entrance. Build 78 adds that missing native Path to the fixture and a corresponding connection assertion. The model and production rules are unchanged. Build 78 also includes the new ivory outline mixer icon.

Native run 78 additionally passed actual drum motion, power interruption/resumption, two input-accounted batches, water exhaustion, replenishment and a third batch (twelve Concrete). Saving failed when the fixture tried to add two checkpoint batches after ordinary haulers had delivered extra cement from the other factories. Build 79 isolates those other Aggregate/Cement output inventories using native Disable/Enable for this explicitly seeded test, restoring them before saving. Ordinary gameplay behavior is unchanged.

Corrected native run 79 passed placement, five walking destinations, selective rails, shaft power, platform stacks, under-deck construction, visible header levels, animated production, power interruption and three input-accounted batches producing twelve Concrete. The native save is `outputs/mixer-verified-build79.timber`, SHA256 `709ad9aa68ace8440f7d17abd2daa444d17a59f39b73b99713e0b2c3f20bb1f2`.

Fresh-process reload 79 restored exact identity, stock, progress, supports, rails and reservoir level, then completed another water-consuming batch with actual drum motion and all five walking destinations. The native continuity save is `outputs/mixer-continuity-build79.timber`, SHA256 `2fff4e5944fea2d13da3df152deb60782749aa4e3d8a2741b92af0293c2a13ec`. Both archives passed `tools/capture_mixer_save.py`. Native model and inventory screenshots were inspected and preserved in the mixer review directory.

The workbook now reads actual blueprint support and empty-cell counts instead of marking the entire construction chain non-stackable. Export 80 records the completed 79 tests and the pending mixer pipe face. Exact construction-row comparisons, vanilla-sheet preservation and zero formula errors passed; mixer and deck/pipe previews were inspected.

Sixteen construction icon exports now use authored ivory SVGs: seven buildings, five goods and four map sources. The 128px/32px sheet was inspected; build 79 includes them. Historical prototype exporters no longer own the reviewed industrial/civic/hatchery models or these construction icons. Current model ownership is recorded in `docs/asset-pipeline.md`.

Official build 80 installed with all 428 authored package hashes matching. Its first compile rejected LINQ Any on the native ReadOnlyHashSet; the fixture now calls that collection's supported Contains method. The source authors an intake-only Timber Pipes face at local (7,5,0)/Right, under the rear gallery. Native run 80 placed all six belts, three warehouses and tank/pump/pipe/valve successfully, then stopped on an incorrect fixture assertion requiring ISimSource on every belt segment. The dependency uses downstream BeltLink objects between belts; only inventory-facing inputs supply ISimSource.

Build 81 corrects that assertion and advances native simulation before inspecting BeltRegistry's links. It also distinguishes a BeltLink's target identity from its capacity-dependent CanAccept result, so full saved lanes remain valid. The first 81 build was intentionally interrupted before completion to include that last correction. Its completed official build matched all 428 package hashes.

Native main 81 passed six real belts delivering Aggregate/Cement and withdrawing Concrete, Water intake through the tank/pump/pipe/valve, native 12/4/8 buffer limits, wrong-good/face rejection, power and valve interruption, exact conservation and two newly debited batches. Output stock reached 20 Concrete. Preserved save: `outputs/factory-transport-build81.timber`, SHA256 `eccb0556458ebda8ca07420b081bcb10936311fba02e07aa4542a6e7410e849c`.

Fresh-process 81 restored every factory/warehouse identity and stock, all six exact belt queues/positions, three pipe volumes/goods, valve state and tank fraction. The disposable settlement's assigned workers were starving/dehydrated, so native developer Boost was applied to one worker. Two more real batches reached the warehouse (28 Concrete), with exact input debits and conservation. This is transport evidence, not economic throughput. The driver now seeds only Hunger/Thirst/Sleep once at assignment. Preserved save: `outputs/factory-transport-continuity-build81.timber`, SHA256 `b91f12951c44eb6e1c31116eb17ce0a7f815a5bd6e1df5a5f1a278a611986a86`. Both archives passed the capture tool. Native nighttime transport view: `docs/art/reviews/2026-10-20-mixer/ConcreteMixer-native-transport-build81.jpg`.

Power Lines build 82 adds an explicit attachment on the existing rear-right mixer frame, grid (7.84,5.84,1.80), using the dependency's public connection service and native mechanical graph. Its first compile exposed a missing Timberborn.Effects import in test-needs preparation. The next build exposed PowerLines.dll's transitive ModSettings.Common.dll reference in Unity's linker. Both were corrected at source; the official build installed all 428 matching package hashes. PowerLines and ModSettings.Common remain external dependencies and are excluded from the shipping package.

Native main 82 passed a single isolated 350 hp cable supply powering the mixer, six belts and pump at their actual combined 312 hp demand. Self/duplicate connections were rejected; disconnecting the cable split the graph and stopped the factory, belts and pump; reconnecting restored two real batches with exact ingredient/Water accounting. The warehouse reached 28 Concrete. Saved endpoint IDs match the native connection singleton. Preserved save: `outputs/factory-power-lines-build82.timber`, SHA256 `2876993fa98b78130f311ec722c1e125e57a7fbeee28ec412bf7a7e410612510`. Screenshot: `docs/art/reviews/2026-10-20-mixer/ConcreteMixer-native-power-lines-build82.jpg`.

Reload 82 restored the exact cable pair, stocks, progress, queues and pipe volumes, passed cable interruption and 350/312 hp, then completed two batches. Its output delivery correctly stopped at the receiving Small Warehouse's 30-unit capacity; the fixture had incorrectly expected 36. That unsaved test was stopped. Build 83 changes only test preparation: after exact reload verification, explicitly withdraw a previous eight-Concrete lot and debit its conservation baseline; assert capacity for the next eight before starting production. No warehouse capacity, transport or production gameplay rule is changed.

Official build 83 installed all 428 matching package hashes. Its fresh process loaded the main 82 save and passed exact endpoint/stock/queue/pipe continuity, the declared eight-Concrete withdrawal, cable interruption/reconnection, actual 350/312 hp and two further input-accounted batches. All eight new Concrete arrived; the warehouse finished at 28 (28 saved − 8 withdrawn + 8 produced). The native save passed capture: `outputs/factory-power-lines-continuity-build83.timber`, SHA256 `1a5af810d379ca817cf58662a432547f5b88913886fe95507166bdcc941e0bb7`. Evidence is `outputs/factory-power-lines-reload83.log`. This remains a seeded transport fixture, not an economic throughput test.

## Isometric pit replacement — isolated native main/reload 86 passed

Sandstone and limestone now have separate detailed source studies based only on the mining sheet's front/rear isometric illustrations. The first render was revised for lower proportions and a consistent cable material. Both use native Iron Teeth wood/roof/metal and closed native barrel props. Sandstone has a sorting grate/catch tray; limestone has a cart and workbench canopy. Review renders and exact source checks: `docs/art/reviews/2026-10-20-pits`.

Each model passed 50 door-clearance samples and all 121 hoist frames, with a continuous cable attachment and zero basket/static mesh intersections. Registration follows the art at 5×5×4 and 6×5×4 without scaling. Official Timbermesh export passed seven-node/three-track/121-frame checks, exact native material UV bounds, ground-door occupations and the original external barrel reference. All 39 model bindings passed.

Official build 84 installed all 428 matching package hashes. Native placement, mineral-specific selection, both workers' deliveries and actual basket movement passed. The pause fixture sampled a position before the next controller tick and failed its stationary assertion; no verified save was written. Build 85 waits for the controller to disable before taking that snapshot, and checks saved pause before fixture mutation on reload.

Official build 85 installed all 428 matching package hashes. Native main 85 passed new-model placement, correct/wrong mineral selection, actual worker harvesting and delivery, actual basket movement, stationary paused baskets and exact source/output conservation. Each explicitly shortened 24-unit test outcrop saved 22 remaining, with two stone in its pit. Preserved native save: `outputs/mineral-pits-verified-build85.timber`, SHA256 `94a9a00df6600482efbe29daacd1dec7be32ed1791c5c6d96ac6aa0f91778bd5`; screenshot `docs/art/reviews/2026-10-20-pits/Pits-native-build85.jpg`. Normal map outcrops remain 600 units.

Fresh-process reload 85 restored exact pit/source identities, partial yields, stock and pause state. Native workers delivered the remaining 22 units of each mineral; both finite source entities disappeared at exhaustion and each pit finished with 24 units. Actual hoist animation and conservation passed. Preserved native save: `outputs/mineral-pits-continuity-build85.timber`, SHA256 `b276cd358aa7722680e0497ce3e75113002f9c353c9255e2c1d8bd838fa45182`. Both archives passed `capture_mineral_pits.py`.

The 85 profile still loaded No Build Restriction and All Buildings Transfer Power. The pit panel consequently labelled its roof Solid and exposed power connections despite the authored non-supporting, unpowered rules. These results establish harvesting and continuity under that profile, not the native support baseline. Both optional overrides were disabled through the game's mod menu; `outputs/modifier-isolation86.log` confirms their absence from the loaded list. Build 86 adds runtime checks for unchanged Ground foundations/None stacking, rejection of floating pits and roof paths/platforms, and absence of MechanicalNode. It also limits each test pit to one desired worker; the authored maximum remains two. Results follow.

Official build 86 installed 428 exact package hashes. Main and fresh-process reload both passed effective Ground/None support rules, rejection of floating pits and every occupied column's roof paths/platforms, and absence of MechanicalNode. Both global overrides are absent from the loaded mod lists. Main then passed harvesting, actual hoist movement/pause and the 2-stock/22-reserve checkpoint. Reload restored identities, inventories, yields and pause, delivered the remaining 22 units each and removed both exhausted sources. Captures with `--native-rules` passed. Main archive SHA256: `56185c5c8c1373c5df74b8e9473f6bff77a3003a210ec96dd75f8390ffa5c287`; continuity SHA256: `ad9ebd70ecd5161df3f5256b36ad983ccefb70016bf73bea81c1ac44310ba9c0`. Files: `outputs/mineral-pits-verified-build86.timber`, `outputs/mineral-pits-continuity-build86.timber`. The panel now shows Ground-only without Solid or power controls; review capture is `Pits-native-isolated-build86.jpg`.

The enlarged footprints are not backward compatible with the two cramped prototype locations in the old disposable reservoir save. Native load validation removed those old pits; the fixture then placed the new models successfully in a clear area. The source save is preserved. Rebuild prototype pits with sufficient room; no silent relocation or footprint scaling is implemented.

## Aquaculture pipes — build 76 main and fresh-process production passed

Official build 76 installed with all 428 authored package hashes matching. Timber Pipes 11.4.0 is an external authoring/runtime dependency, never bundled into Deep Frontier. Explicit intake-only faces are authored on FisheryWorks at (5,9,0)/Up and FishHatchery at (7,2,1)/Right. The reviewed building meshes are unchanged.

Native main run 76 passed real Medium Tank → 50 hp horizontal pump → transport pipe → valve → factory delivery, rejection of Badwater and unlisted faces, 90/60 Water buffer limits, valve interruption/reopening, actual reservoir levels and water conservation. Native source save: `outputs/aquaculture-pipes-build76.timber`, SHA256 `d6ed16c1159f84f191193191cb0a36fdd99edcfe7ae2396a0c3173d79d56b64b`.

Fresh-process reload 76 restored exact factory/tank identities and stocks, signed fractional tank volumes, all six saved pipe volumes/goods and both valve settings. After another interruption/refill, native workers completed two Fishery batches and one Hatchery batch, consuming three/two pipe-fed Water. Both flow effects ran and the Fishery wheel advanced. Final buffers refilled to 90/60; total water reconciles to 267/268 after explicit fixture withdrawals and actual production debits. Native continuity save: `outputs/aquaculture-pipe-continuity-build76.timber`, SHA256 `b9f7be74f9ff2faa5c0c0c875be5a1d4403db327cb165f725039ee34e50e678f`. Evidence: `outputs/aquaculture-pipes-reload76.log`, `outputs/aquaculture-pipe-continuity76.json`. Wider rotations, factory belts and FishOil transport remain separate work.

The balance workbook was regenerated with exact aquaculture pipe faces, per-piece power requirements and grocery belt 73/75 evidence. Transport network demand is left unspecified because it depends on the player's chosen pieces; factories remain 55/80 hp and each horizontal pipe pump demands 50 hp. Formula scan found no errors; changed transport previews were visually inspected.



## Reference hatchery integration — build 57 native acceptance passed

The canonical hatchery is `src/DeepFrontier/Art/Source/FishHatchery-ReferenceStudy.blend` (SHA256 `b98f3265fd3cb368ce4ce3c9b94763de12ed67115566a473f2d30b244fcd8fe4`). Its official export retains the low workroom, pump canopy, open pens, native tank/barrels and sign animation. Its 8×8×5 registration includes BaseZ=1, 31 route cells, 20 adaptive rail openings and one clear construction tile. Export SHA256 is `b1861cbd2bf96c890f2d7e315b09a7b94ff6ddd750ee1643c9897673b448b515`. All 426 authored data/manifest/DLL hashes matched the official build 57 installation. Source mesh, UV, rail and animation checks passed.

`outputs/fishery-hatchery57.log` passed bank placement, native shaft power, the exact submerged water probe/model pivot, selective rails, header Water at 0/30/60, dry and badwater blocking, two working employees, juvenile production and actual walking through seven dock/door destinations. A native Double Platform + Platform + Path stack fits the clear dock. Native inspection confirms the 0.004-unit front apron offset removes terrain flicker. The successful paused save is preserved as `outputs/hatchery-verified-build57.timber`; screenshots are in `docs/art/reviews/2026-10-19-hatchery`.

Fresh-process continuity restored the saved stock, recipe, water and paused state, then bred another batch. Fishery production, cascade and wheel stopped at zero power, resumed after power returned, stopped after real ingredient exhaustion and resumed after replenishment. Evidence: `outputs/fishery-continuity57.log`, `outputs/aquaculture-continuity-build57.timber`.

The separate zero-stock test passed from a save with no fish or juveniles: a real shore catch was delivered, the hatchery bred juveniles, workers hauled them natively and the Fishery produced fish. Only vanilla feed/water and fixture power were supplied. Evidence: `outputs/fishery-bootstrap57.log`, `outputs/aquaculture-bootstrap-source.json`, `outputs/aquaculture-bootstrap-build57.timber`. Overnight work breaks are expected; economy balance remains a playtest task. JuvenileFish still needs a second useful downstream consumer before release.

Build 56 exposed the hatchery final-access height error: BuildingAccessibleSpec.LocalAccess is grid-relative, while idle model slots are model-relative. Build 57 sets its access Y=1, asserts the world entrance, and retains the walker before Pause unassigns workers. The reviewed artwork is not shifted to compensate.

Hospital official build 63 installed with all 427 authored package files matching. The preserved reference model has a sparse 12×9×9 registration, 69 route cells, 50 adaptive rail openings and clear roof construction cells. Initial care settings are 30 patients, six separate staff, 600 hp and 25,000 science.

Run 63 passed native placement, shaft power, stairs, roof platform stacking, thirty patient reservations, selective railing openings, actual entry and recovery for injury/chipped teeth/contamination, separate staff attendance, supply consumption, power/work-hour interruptions, and eight actual walking destinations across the ground door, galleries and rooftop. Native GameSaver wrote the successful fixture, preserved as `outputs/hospital-verified-build63.timber` (SHA256 `0655ccab3bcf8d1ac9a9d654a45ea43e266802e35654a62f99269ed45adbe908`). Evidence: `outputs/hospital-run63.log`.

Official build 66 installed with 428 exact package hashes. Its fresh-process hospital continuation passed exact identity, paused state, all three supply stocks, fractional supply duration and saved health needs. A real observer gained 0.09375001 PublicHealthcare inside the radius, then lost points outside. Exhausting medicine and its fractional buffer stopped both treatment and neighborhood care; replenishment restored them. Three attending staff produced measured injury recovery 0.009666424/hour. Evidence: `outputs/hospital-reload66.log`; preserved native save `outputs/hospital-continuity-build66.timber` SHA256 `f3b451f58beb468075be6cccf9fd760e75f9b025a36c970854227bfff96e46b2`. The native hospital panel was visually inspected after the test, including separate patient/staff counts and paused care status. Economic balance remains untested.

Grocery Store approved source geometry is registered at 11×9×9, with 64 route cells, 38 rail openings, connected doors at 0/2/4/6 and a clear roof construction cell. Build 68 passed native placement, shaft power, vanilla stairs, stacked roof platforms, selective rails, six-food hauling, unpowered shopping and actual food effects, stocked neighborhood gain, power/pause/assortment gates, native restocking, and all eight walking destinations. Its native inventory holds 100 of each of six foods; two clerks, 100 hp demand/zero output and 6000 science are initial balance values. Preserved save: `outputs/grocery-verified-build68.timber`, SHA256 `f7c2cbd78f42c1737108f3b3ac68fdd6cd806ee785269a2a6e9e29226871e7ed`.

Fresh-process grocery continuation 68 restored exact stock, identity, paused state, permissions and resident needs. Staffed neighborhood service resumed, a real resident gained wellbeing need points, and another shopper ate the saved food while clerks were off duty. Preserved save: `outputs/grocery-continuity-build68.timber`, SHA256 `a20543dc2317d67662c3417a51ee54fa5577515b057311aa43aebc29d1aee5ac`. Evidence: `outputs/grocery-run68.log`, `outputs/grocery-reload68.log`. Native build 69 corrects the panel's invisible food rows; visual inspection confirmed all six native food rows, counts/limits, empty shelves and service explanation. Its continuation passed again, preserved as `outputs/grocery-continuity-build69.timber`. Panel capture: `docs/art/reviews/2026-10-20-grocery-runtime/grocery-stock-panel-build69.jpg`.

The grocery intake-only belt adapter uses Conveyor Belts' public connection provider. Source inspection found the generic belt target ignores PublicOutput when taking goods; the explicit grocery connection exposes a sink but no source. Official build 72 succeeded with 428 exact package hashes after adding the installed ConveyorBelt/Algorithm and transitive ModdableTimberborn/ModSettings.Core authoring references. Dependency DLLs remain outside the shipping mod. Native run 72 placed both physical lanes, rejected non-food inputs, delivered corn to exactly 100, conserved all 127 units and prevented outbound withdrawal. Its power-cut assertion failed because the belt network remained powered after disabling the newly placed generator; build 73 inspects and switches every native test generator on the actual connected graphs. Build 73 then passed full interruption/restoration and saved 100 Corn Rations on the shelf, seven at the donor and ten on the belts (117 total). Preserved native save: outputs/grocery-belts-build73.timber, SHA256 9776d830bac07920f0ac63a90156453ac80ae8c4a9bb245b3b8f2214ef4b0a62. Reload 74 restored every saved good and position; native stock events identified thirteen shopper-consumed rations while all seventeen donor/queued units arrived. Its full-shelf completion condition was invalid with finite supply and concurrent eating. Build 75 opens thirty spaces and requires the entire saved supply to arrive with exact consumption accounting. Fresh-process reload 75 PASSED AND SAVED: all seventeen donor/queued units arrived, thirteen were natively consumed, and final corn stock is 74 after the explicit thirty-unit withdrawal (117 = 74 + 13 + 30). Incoming/outgoing lanes and donor/receiver are empty. Preserved native save: outputs/grocery-belt-continuity-build75.timber, SHA256 fc51807bc76dd708818b0f653c4ed5b0ec4ee7b724f883adb28ba3e59519c603. Official build 75 has 428 matching package hashes and also contains the new explicit Fishery/Hatchery pipe faces; their physical acceptance is underway.

Six old civic/food placeholder icons are replaced at source with ivory SVGs: GroceryStore, Hospital, CannedFish, PackagedFood, Medicine and MedicalFood. Their transparent 256px exports and 32px review were inspected. Native build 73 visibly confirms the grocery basket, canned fish and packaged-food icons (grocery-ivory-panel-build73.jpg); hospital/medicine icons still need separate native panel inspection. The placeholder generator no longer owns these or the already approved restaurant/aquaculture icons.

Run 59 found a duplicate IStatusHider (Workplace already provides it); the producer now omits StatusHidingEnterableSpec. Runs 60–62 corrected the healing comparison: native Need.Update skips passive healing on treatment ticks, while repeated visits alternate treatment and completion/passive ticks. A settled Medical Bed measured 0.009583455/hour. Hospital authors 0.0303333333 on treatment ticks for a 0.01725/hour steady target (1.8×); the short run 63 sample measured 0.01672733/hour (1.745439×), within the declared 0.08 ratio tolerance. This is measured cadence evidence, not a claim that the raw blueprint effect is the total recovery rate.

The workbook now uses exact hospital and grocery building data, supplies/food stock, progression, transport and native verification status. MedicalFood, CannedFish and PackagedFood are assigned to Food Packaging Works with their actual recipes; the grocery has no production recipe. Hospital/grocery/aquaculture/restaurant checks pass with zero formula errors. The four vanilla sheets retain their values, formulas, cell formats and tables. Changed building and recipe previews were visually inspected. Transport rates remain unavailable where only storage capacity is known.

## Waterfront Fishery revision â€” build 54 continuity and bootstrap passed



The user requested the individual Fishery.png isometric reference after rejecting the civic-like Fishery silhouette. The replacement has offset floor outlines, one lower warehouse, a broad low roof, working decks at layer 2, nets, fish preparation details, native wheel/water and three connected doorways. Official build 51 installed the 12Ã—10Ã—7 replacement; all 426 authored data/manifest/DLL hashes match. The source review is `docs/art/reviews/2026-10-19-fishery-waterfront`.

Fresh native run 51 passed placement, shaft supply, a terrace platform stack, six water surfaces at 0/45/90 stock, real wheel playback during production and stopping on workplace pause. The Fishery produced two batches and the gatherer delivered a real shoreline catch. Native GameSaver preserved the active next catch and half-full reservoirs; the copy is `outputs/fishery-waterfront-verified-build51.timber`. See `outputs/fishery-run51.log` and `fishery-native-build51.jpg` in the art review.

Fresh-process reload 51 passed saved catches and water surfaces, contamination/drain/refill, job/pause cancellation, the redesigned native stairs and deck platforms, selective rails (`FishFront8`, `FishRoofLeft6` open; adjacent `FishRoofLeft5` closed), actual beaver movement through both upper doors and ground return, and quarry reservoir regression. Hatchery clean/dry/contaminated/refilled production passed again. Native GameSaver wrote `outputs/fishery-waterfront-regression-build51.timber`.

Official build 54 installed successfully; all 426 authored data/manifest/DLL hashes match. Its fresh-process continuation restored hatchery stock/recipe and clean-water gating, resumed juvenile production, stopped Fishery production/cascade/native-wheel playback at zero shaft power, completed the interrupted batch after power returned, stopped after real inputs ran out and produced again after replenishment. Native GameSaver wrote the successful fixture, preserved as `outputs/aquaculture-continuity-build54.timber`; evidence is `outputs/fishery-continuity54.log`. The test resumed work after the normal overnight break. No ordinary production behavior or reviewed Fishery geometry changed.

Builds 52/53 exposed test setup mistakes: the aggregate blocker includes Pause, and native workplace assignment requires an unblocked workplace. Build 54 resumes before checking/assigning. Its separate zero-fish-stock bootstrap PASSED: the gatherer caught/delivered fish, the hatchery bred juveniles, and native workers hauled juveniles to the Fishery and completed fresh-fish production. The exact starting save has no fish/juvenile stock, carrying or production (`outputs/aquaculture-bootstrap-source.json`). Only vanilla feed/water and fixture shaft power were supplied. `outputs/fishery-bootstrap54.log` records the run; native GameSaver wrote `Aquaculture bootstrap - verified`, preserved as `outputs/aquaculture-bootstrap-build54.timber`. This establishes reachable starting inputs and actual hauling; longer-term economy balance remains a playtest task.

Before build 55, the replacement small hatchery was a separate Blender candidate, archived at `docs/art/reviews/2026-10-19-hatchery`. It follows the Fishery isometric waterfront details with a low enclosed workroom, pump canopy, two open nursery pens, native barrels/tank, metal/concrete trim and a clear entrance apron. Its source SHA256 is `ca4538e830e816b9fe87d4ce315de4b900daace0325b6b193ba9a8eea0099051`. An explicit 8Ã—8Ã—5/BaseZ=1 candidate has 31 connected route cells, 20 rail openings and 32 mesh-clear route segments. One full construction tile fits the checked side dock; the sign's 61-frame loop closes and stays clear of the entrance lane. That candidate has since become the active source; the current integration and remaining checks are recorded above.



Official build 50 succeeded; 426 authored data/manifest/DLL hashes matched. `outputs/fishery-reload50.log` passed saved catch delivery, contamination/drain/refill, job/pause interruption, actual model-facing direction, native stairs, adaptive rails, real beaver traversal through the old Fishery doors, deck platforms and quarry water regression. The hatchery passed native bank placement and shaft supply, water below its rear nursery, dry and contaminated blocking, clean refill and actual juvenile production. Native GameSaver wrote the successful fixture, preserved as `outputs/fishery-regression-build50.timber`. This is a seeded production test; unseeded bootstrap and dedicated hatchery reload remain pending. Its small prototype artwork also still needs replacement.



Build 49 exposed a fixture-only path crossing an earlier industrial structure. Build 50 uses the surveyed empty east pond bank. Build 48's walker assertion compared a cell corner target with a cell-centre arrival; 49 corrected the command to use the same authored fractional coordinate as the arrival check and passed actual traversal. These were test corrections, not production workarounds.



The workbook includes the new Fishery dimensions, 34 route cells, 19 openings, three doors at levels 0/2, exact fishery/hatchery/flag costs and recipes, and native hatchery water requirements. Four vanilla sheets retain values, formulas, formats and tables; restaurant checks pass; zero formula errors. Native verification status follows `tools/aquaculture.json`. Ivory aquaculture icons and clearer descriptions shipped in builds 49/50; the native fishing panel was visually verified in build 47.



## Earlier fishery and gatherer shore fishing â€” builds 44/45



Fresh-process reload 45 restored six half-full factory surfaces, the fishing selection and an active catch. That catch completed and was delivered. Contamination interrupted the next catch with no fish; draining prevented fishing; clean refilling resumed it. Switching to plant gathering and pausing cancelled active catches without fish. All shoreline regression phases completed and native GameSaver wrote `Fishery regression - verified` (`outputs/fishery-reload45.log`, preserved `outputs/fishery-regression-build45.timber`). UI inspection found a dark unstyled toggle, and the saved visible-model rotation exposed use of the wrong facing target. Builds 46/47 correct these and extend the fixture with native civic access checks; build 46 was packaged but not launched. Build 47 is being built/tested. Workbook fishery/gatherer rows and unseeded aquaculture bootstrap remain to update/test.



Build 44 is installed through the official Mod Builder; 426 authored data/manifest/DLL hashes match the final player build and installed package. It integrates the accepted Fishery Works scene at 13Ã—8Ã—9 with sparse occupation, 65 route cells, 25 rail ports and two clear roof construction cells. Native placement, a real shaft supplying 80 hp demand, Double Platform + Platform + Path on the terrace, and six water surfaces at 0/45/90 stock passed. The original native wheel advances during actual workshop production and stops with the cascade when paused. Native production completed two batches (six FreshFish). Evidence: `outputs/fishery-run44.log`, `outputs/restaurant-package-verification44.json`, `outputs/civic-integration/fishery-static-checks.json`.



The existing Iron Teeth Gatherer Flag now offers a fishing job, initially off. The authored rate is one FreshFish per four base working hours plus travel/delivery, using native worker speed. A real reachable clean shoreline passed; dry ground was rejected. One catch was carried back and deposited through native carrying. GameSaver wrote `Industrial Acceptance/Fishery acceptance - verified.timber` with one fish at the flag, an active second catch, six fish and 45 Water at the paused fishery. A preserved copy is `outputs/fishery-verified-build44.timber`. Source balance and renewable bootstrap are in `tools/aquaculture.json`. Full civic stairs/rail-route checks remain in progress.



## Restaurant water and furniture â€” official build 41



Build 41 is installed through the official Mod Builder; all 425 authored data/manifest/DLL hashes match (`outputs/restaurant-package-verification41.json`). It adds conditional native Water service, permanently allows Water intake regardless of recipe, lowers the tables by 0.10 tile and moves the animated sign outside the deck. All 61 source frames retain a 0.50 tile sign/deck gap. In-game tests passed one Water with exactly +0.33 native Thirst for the thirsty diner and zero Water for the hydrated diner. Native cooking produced four cakes, staff served cake/coffee, and meals continued without coffee. The saved fixture contains four visits, one served guest, one active worker service, and actual cake/coffee need values (`outputs/restaurant-save-verification41.json`). The outer build wrapper incorrectly tested PowerShell's stale LASTEXITCODE; the official builder itself succeeded, its log confirms completion, and independent package hashes pass.



Fresh-process reload 41 passed the no-output inventory contract, restored the saved service and released previously served guests without duplicate receipts. Pause, zero power and zero working hours each released guests and produced no meal debit; restored operation completed new service. All phases finished and native GameSaver wrote `Industrial Acceptance/Restaurant regression - verified.timber` (`outputs/restaurant-reload41.log`). The fixture is paused with nine guests. In-game close-ups show adults and a child seated with clear faces/table edges and chairs inside the rails; the banner hangs outside the deck. Captures are in `docs/art/reviews/2026-10-19-restaurant-seating`. This establishes the observed poses, not exhaustive animation or every civic rotation/stair/rail-seam case.



The workbook has been regenerated from the restaurant blueprint and exact recipes: 400 hp demand / zero output, 800 science, 4 staff, costs, four kitchen recipes, table-only cake and conditional Water. Relevant Overview/Buildings/Items/Recipes/Progression/Transport/Sources/Dependencies records are updated, including a specific restaurant progression row and the required Moddable Recipes/TimberUi dependencies. The four vanilla sheets retain every value/formula, cell format and table definition; no formula errors were found (`outputs/restaurant-workbook-verification.json`). Other proposals remain labeled pending.



Build 40 first verified the 400 hp native kitchen, cooking four Sweet Berry Cakes from 2 Berries + 2 Corn + 1 Water in 2 base working hours, optional coffee, real menu receipts and continued service without coffee (`outputs/restaurant-run40.log`). Read-only inspection of its native save found SweetBerryCake and Coffee needs on actual diners, plus a served guest and an active worker service executor. Run 39 had exposed Moddable Recipes changing inventory permissions on SetRecipe; the restaurant-specific entry exception in build 40 passed the no-public/no-worker-output assertion. Reload acceptance is now established by build 41 above. The prior save is preserved as `outputs/restaurant-verified-build40.timber`.



The furniture revision retains fourteen native Sitting anchors at chair surfaces, front chairs facing across the balcony and the increased chair/table spacing. Table center height is now 0.58 above each deck. Source gallery/roof clearance and official-export quaternion/position/chair-to-rail checks pass. The review is `docs/art/reviews/2026-10-19-restaurant-seating`; this intentionally revises the earlier approved scene. Build 38 caught a test-only API error (`ReadOnlyHashSet` is not LINQ-enumerable); the harness uses native Inventory.IsOutput.



Build 37's reload test passed no duplicate service, pause, zero power and zero working hours, including guest release. The final resumed-work phase timed out after eight game hours; it did not finish the full regression or write its final save. The fixture now allows a full day for the restored work schedule and returning hungry guests. It also separates native recipe ingredient consumption from meal receipts and checks table-only stock, cake production and optional coffee. Wider item audit: 59 goods, 38 release failures; native recipes are now included in its source catalog.



## Earlier restaurant integration â€” official build 35 runtime evidence



The grand restaurant now has an active 10Ã—8Ã—9 blueprint with sparse occupancy, 14 native sitting slots, 4 separate staff, connected authored doors at levels 0/2/4/6, 21 adaptive rails, four clear terrace cells, shaft sockets and 30 hp demand / zero output. `Restaurant.cs` implements worker-served real food, native inventory/hauling, per-diner food effects, a Dining need, and persistence for visits and active service. `RestaurantPanel.cs` uses TimberUi for stock and service status. No DiningService recipe remains active on this building. The obsolete token good remains a release-audit failure until it is removed from the old catalog.



Build 35 completed through the official Mod Builder; 420 data/manifest/DLL hashes match the installed package (`outputs/restaurant-package-verification35.json`, `outputs/restaurant-unity-build35.log`). Its marked acceptance settlement passed native shaft power (5,000 hp test supply, 30 hp demand, zero output), Double Platform + Platform + Path placement on the roof terrace, empty/partial menu rejection and native decorative plant assembly. Eight guests occupied native sitting slots; staff reached upper-deck service positions and committed four real meals, each with exactly one consumed-stock event for each of the four foods. Native GameSaver wrote `Industrial Acceptance/Restaurant acceptance - verified.timber` with eight active visits, two served guests and one active service executor. Read-only save inspection found Dining=1 and native Fermented Mushroom/Eggplant Ration effects on served guests.



Fresh-process reload 35 restored the eight guests including both served flags and continued service. Twenty-eight additional meals were served with matching consumed-stock events until the finite test supply ran out; ordinary haulers independently replenished berries. No restaurant exception was logged. This establishes native persistence and continued operation, while the stricter per-diner duplicate-receipt and interruption assertions are being added. The TimberUi dining panel was inspected in game: occupancy, waiting guests, menu quantities and native power demand are correct (`docs/art/reviews/2026-10-19-restaurant-runtime/restaurant-dining-panel.png`). Exact sitting height, all door exits, restaurant-specific vanilla stairs, rail seams, rotations and interrupted service still require dedicated checks. The colored prototype UI icon remains unfinished.



Earlier failures were corrected at their sources: build 27 looked for the animator on the sign mesh instead of the imported root; build 31 omitted the native EntityMaterials decorator required by assembled plants; run 33 attempted to seed food after native haulers had reserved incoming capacity. Build 35 seeds the disposable fixture before reservations and measures consumption events rather than net inventory. TimberUi registers fragments through its BindFragment extension. Builds 28/29 stalled on dependency import and 30 failed at the linker; the exact installed library plus Unity's documented per-assembly updater exclusion resolved authoring in 31. The dependency remains in its own package.



The item-use audit now counts authored restaurant menu consumers, separately from direct eating. It still reports 58 new goods and 38 release failures; proposed uses and successful compilation do not make the wider expansion complete. The workbook still needs the final restaurant integration values once runtime acceptance passes.



## Earlier progression revision and official build 24



The latest user requirements are recorded in `tools/frontier_progression.json` and [the civic/industry revision](../docs/civic-progression-revision.md): worker-served actual restaurant meals; a 30-patient hospital with 1.8Ã— Medical Bed injury recovery and teeth/contamination care; stocked grocery wellbeing; individual education/wellbeing proposals; industrial science and aluminum; oil-derived resin/plastic and reusable hazmat equipment; advanced structural pieces; multi-good warehouses with per-item limits and shielded variants. These mechanics are plans pending implementation. The required 1,000,000-science reactor unlock is wired into the producing generator.



Official build 24 completed and installed that science change plus current TimberUi/Pipes/Belts dependency minimums. All 415 authored data files, the manifest and the official player DLL match the installed package (`outputs/progression-package-verification24.json`, `outputs/progression-unity-build24.log`). The DLL is unchanged from build 23. The running game has not loaded build 24; the latest actual gameplay evidence remains build 23 below. The grand restaurant is staged separately and was not shipped against its old prototype blueprint.



The workbook now includes these proposals across Overview, Buildings, Items, Recipes, Progression, Transport and Sources, plus a new ItemUses audit sheet. It recalculated without detected formula errors; four vanilla sheets retained their values, formulas, cell formats and table definitions (`outputs/civic-workbook-verification.json`). The strict item audit checks 58 authored new goods and currently rejects release for 38 incomplete/obsolete goods. Directly edible foods and final rocket components may have one use; proposed destinations do not satisfy the audit. This audit does not establish resource bootstrap or gameplay balance.



Restaurant export validation passed: fourteen diner slots, four staff markers, one 61-frame sign animation, native Iron Teeth material bindings, 21 adaptive rail openings and a connected 58-cell authored graph through levels 0/2/4/6. Accepted scene hash is unchanged. Evidence: `outputs/civic-integration/static-checks.json`. Runtime occupancy, district routing, seating height, native prop assembly and worker-served meals remain the next work. The current native FixedSlotManager does not distinguish staff from guests; preserve guest capacity by implementing staff work routes separately. Multi-good storage can use native Inventory plus a dedicated IGoodDisallower; do not attach SingleGoodAllower.



## API and Steam Workshop audit



Freshness checked all 21 installed foundation/supporting packages against Valve published-file timestamps and sizes; all were current, with Steam reporting no pending update/download. `tools/check_workshop_dependencies.py` writes `tools/dependency_freshness_1_1.json` and the raw response. No package reinstall was necessary. Required manifest versions now explicitly match TimberUi 11.0.1 and Pipes/Conveyor Belts 11.4.0; the manifest validator checks both IDs and minimum versions. This establishes revision freshness, not universal compatibility.



The installed APIs and current Workshop listings were checked before civic runtime integration. [The audit](../docs/modding-api-audit.md) records 13 exact installed package/DLL captures, source-confirmed contracts and feature decisions. Moddable Recipes 11.0.0 and Scientific Projects 11.0.0 are already installed and are the preferred candidates for recipe/certification progression. Moddable Timberborn's visitor/work events, TimberUi panels, existing transport interfaces, TimberCommons building helpers and Bobingabout automated-manufactory components were inspected. Author source/examples are pinned in `vendor/datvm-timberborn-mods`.



Hooman Stairs 2.0.2 and source were downloaded for inspection, not installed/enabled. It connects separate stacked entities; the current version has no general multi-door API for one building. Native explicit edges are the first approach for civic interior routes; actual district access and traversal remain unverified. CustomTools is a Workshop candidate. Deprecated TimberAPI/Moddable Prefab are excluded. No shipping dependency or enabled-mod change was made during this audit. Captures: `tools/modding_api_audit_1_1.json`, `tools/hooman_stairs_dependency_1_1.json`.



## Next buildings: four civic reference studies



The user accepted the latest industrial result and supplied individual Fishery, Restaurant, Grocery Store and Hospital sheets. These supersede the combined surface-colony sheet for those models. `civic_isometric_geometry.py` now authors four distinct detailed buildings from their isometric views, with enclosed facades, outward-facing opaque windows, real arched entrance cutouts, stock/furniture/service details, animation parts and separate gallery rails. Printed tile counts and top-down views remain excluded. Mixer and surface-pit art remain queued after this batch.



The current art review is `docs/art/reviews/2026-10-19-civic/README.md`. The grander revision has three main storeys, galleries at 2 and 4, multiple roof pavilions and clear construction terraces at 6 with enclosed access doors. Door positions at 0/2/4/6 belong to one required internal network; the restaurant records fourteen sitting positions. The 30-slot civic palette uses exact native Iron Teeth wood, blue roofing, steel panels and concrete-colored plaster. Chunky wood grain is retained. Rejected blob foliage is replaced by original native leaf/stem meshes, flowers and potted shrubs. The user accepted the plants and requested functionality work. Still/motion regeneration and video decoding are complete; 75 review artifacts plus source-scene/reference hashes are archived in `review-manifest.json`. Current motion reports include geometry/clearance checks; obsolete standalone geometry reports were excluded. No further plant redesign was made.



These are Blender studies and have not replaced installed civic assets or their blueprint dimensions. Native door routing, support/occupation, power where required, adaptive rails, restaurant visits and other services/production still require integration and save/reload tests. No integral stairs or beaver meshes were added. See `docs/civic-building-integration.md` for the source-confirmed native attraction and access contracts.



## Native quarry water: official build 23 verified



Build 23 compiled, packaged and installed through the official Mod Builder (`outputs/native-water-build23.log`). The native Small Tank mesh/material replaces the quarry's visual water barrel; its surface reads the real quarry Manufactory Water inventory, capacity 16. Both quarries passed 0/8/16/0/8 transitions, exact heights and visibility in `outputs/native-water-run23.log`, then saved the verified fixture. A new process reloaded the save and passed both half-full surfaces at 8/16 and local Y 1.63946, plus the existing industrial reload rail/route checks (`outputs/native-water-reload23.log`). All 415 authored data files and the official player DLL match the installed package (`outputs/native-water-package-verification23.json`).



Build 21 exposed an empty-water visibility conflict: native building visibility re-enabled the surface renderer. Build 22 owns the water child's active state and leaves renderer visibility to the native model. The first reload test then allowed a quarry to consume water before the assertion; build 23 pauses the two test workplaces before saving and asserts that their paused state persisted. This changes the fixture, not production behavior. Automatic state screenshots obscured by another mod's Weather Settings dialog are excluded from visual evidence. The fresh reload was inspected and saved as `docs/art/reviews/2026-10-19-native-water/quarry-water-reloaded-build23.jpg`. The disposable acceptance settlement is left paused. Fishery basins/flow/wheel runtime binding remains pending.



## Industrial integration: builds 15 and 17 runtime verified



Build 17 established the industrial reload result below; the current installed package is build 23 described above. Build 17 changed only the test's explicit saved-path lifecycle expectation from build 15. Its thirteen selected installed files (the DLL plus each industrial blueprint, model and construction model) matched their official build/authored sources: `outputs/industrial-integration/run17-build-hashes.json`.



Run 15 (`outputs/industrial-game-run15.log`) passed:



- Four real generator â†’ vanilla shaft â†’ factory graphs, with 5,000 hp test supply and efficiency 1. Mechanical sockets are authored on occupied side/rear frames, plus crusher front connections.

- All seven native stair upper exits, six factory ground-to-deck routes before and after path restoration, and 35 rail/graph assertions. Shared decks, rotation, wrong-facing stairs, unfinished paths and individual panel removal/restoration are covered.

- Five native deck stacks, each Double Platform + two Platforms + a top Path, including the rotated crusher and quarry's layer-7 gallery. Support exists under clear horizontal route cells, not machinery or ladder hatches; no arbitrary layer cap is imposed.

- Twelve under-deck Path/Power Shaft/Tubeway placements and three solid-room path rejections through native placement/object validators.

- Eight actual beaver movement targets: crusher approach/deck, shared crusher decks, kiln approach/rear gallery, quarry approach/top ladder gallery/engine-room doorway approach. Native control and pathfinding moved the beaver without teleporting. The test's exact direct animation clip is `BeaverAdult_idle`; native idle doorway slots correctly retain the separate `ForcedIdle` parameter.

- All four workshops produced Aggregate, Cement, Sandstone and Limestone. Only recipe inputs and developer power were supplied. The limestone workplace was raised to highest priority via its ordinary UI after native workforce reassignment left it vacant.

- Native GameSaver wrote `Industrial Acceptance/Industrial acceptance - verified.timber` after production and traversal passed. Run 17 reloaded it in a fresh process and passed all 17 connection/rail assertions and all six native ground-to-deck routes (`outputs/industrial-game-run17-reload.log`). All six factories remained registered with valid native requirements.



Run 16 exposed a stale fixture expectation: native builders completed the deliberately unfinished path during production, so its rail correctly opened on reload. Build 17 explicitly requires completion before saving and asserts that completed path and open rail in the reload phase. No gameplay or mesh change was needed for that correction.



The texture correction is verified in game. Run 13's repeating world-coordinate UVs sampled unrelated parts of native atlases. `frontier_architecture.py` now authors bounded face islands with lengthwise grain; no post-export UV wrapping/clamping or material substitution was added. Validation covers 600,485 native-material vertices. Actual materials are `BaseWood_DarkBrown.IronTeeth`, `IrregularPlanks_DarkBrown.IronTeeth` and `PaintedMetal.IronTeeth`. Before/after and close-up screenshots are documented in `docs/art/reviews/2026-10-19-native-material-fix/README.md`.



Integral stairs are removed and native stair bays are clear. Quarry gallery ladders and every existing doorway retain their layout. Source footprints remain crusher 6Ã—7Ã—5, kiln 9Ã—9Ã—6 and both quarries 11Ã—10Ã—9. `industrial_layouts.py` owns routes/ports/door coordinates; `industrial_occupancy.mjs` owns occupied cells and clear space; `BuildingWalkway` adapts individual rail nodes through native graph listeners. The source's 5/12/53 animation-track exports and geometric clearances remain checked. Actual quarry hoist movement is visible in successive game observations; this is not an exhaustive check of every exported track.



These tests establish the listed layouts and native production, not every rotation, terrain condition, long-term colony logistics or progression balance. Extra disconnected/unpowered crusher instances are deliberate rotation/shared-deck test objects. Original user saves remain preserved; the acceptance harness operates only with explicit flags and its marked disposable settlement.



## Earlier package correction



Graphical world creation failed on a missing recipe icon. Inspection of the official `AssetsCopier.CopyFiles` showed the root error: our installer retained the authoring `Data` directory inside the installed package. The official builder copies its contents to the package root. Earlier icon substitutions and metadata changes did not fix that error.



The custom installer and custom bundle packager have been removed. `tools/build_deep_frontier.ps1` stages authoring files and calls the official Mod Builder through `tools/unity/DeepFrontierBatchBuild.cs`. This small entry point selects DeepFrontier, compatibility 1.1, Code and Windows AssetBundle; all compilation, packaging and installation remain in the official implementation. `tools/open_deep_frontier_builder.ps1` opens its interactive window. The output is `Documents/Timberborn/Mods/DeepFrontier/version-1.1`.



The old custom package was moved from `Mods/Deep Frontier/version-1.1` to `outputs/legacy-dev-package-2026-10-18`, preventing duplicate manifest IDs. Official builds succeeded with exit code 0 and `[DeepFrontier] Official Mod Builder completed successfully` in `outputs/unity_official_build.log`. The latest construction build's 413 installed data files matched authored sources, and `Scripts/DeepFrontier.dll` matched the official player build (`outputs/construction-package-verification.json`).



The old icon failure was resolved. The following `Concrete` construction-good failure was resolved by authoring the complete material chain described below. The next graphical Iron Teeth/Plains run reached preview creation and failed because FishHatchery retained HydroponicGarden's crop-stage model references (`outputs/timberborn_construction_world.log`). Those inherited visualizers, slots and particle attachments were removed in the producing expansion generator. Run 2 identified the paired worker-visibility component's dependency on those slots; both are now removed together. Run 3 identified the pit's inherited construction thresholds, which did not match its single authored unfinished stage; the construction generator now explicitly sets an empty threshold array. The model-binding validator checks all 38 templates, including those two additional contracts. Later runtime outcomes are recorded below; these static checks did not establish visual or production acceptance.



## Current art review



Current revision: [quarry review](../docs/art/reviews/2026-10-19-quarry/README.md) and [crusher/kiln facade and height review](../docs/art/reviews/2026-10-19-factory-detail-pass/README.md). The quarry has a continuous animated bucket â†’ receiver â†’ enclosed chute â†’ slat conveyor â†’ vibrating screen â†’ bin route, with worn timber/teal construction, ladders/galleries, enclosed workshops, opaque windows, native-style dark arches and exterior instrumentation. Internal belts are visual machinery, not additional inventory producers. Crusher and kiln retain their accepted machinery and roof silhouettes while adding enclosed lower workshops and service details.



Functional levels are authored explicitly in `industrial_levels.py`; see [height layout](../docs/art/height-layout.md). Crusher/kiln use doorway 0, porch-roof band 1, and actual walking surface 2, with railings above it. The quarry ground doorway is 0 and existing deck entrances are 1; galleries remain 3, 5 and 7. Latest user correction limits the quarry edit to height alignment: preserve all existing doors and the existing layout. No rear entrance was removed. The ground doorway retains its size and X/Y coordinates. Do not reinterpret a conversational door count as an instruction to change geometry layout.



The model manifests and Blender checks are saved beside the review images. These studies are not exported or installed. Native occupancy, horizontal grid routes, stairs/ladder traversal, Entrance/ForcedIdle slots, material export, belt inventory exchange and adaptive-rail bindings still require integration and a fresh game test. Earlier dated art reviews below remain historical records of accepted appearances; source scenes now contain the later facade and height revisions. Older mixer and civic drafts still need their own geometry pass.



The latest quarry height-only comparison passed across 284 model objects with zero horizontal vertex changes, unchanged topology/material assignments and unchanged transforms at source frames 1, 220 and 481. Its report is `outputs/reference-studies/MineralQuarry-height-only-check.json`. This verifies preservation of the model layout, not native navigation.



Final review regeneration and checks completed: crusher 5 moving parts / 56 rail nodes, kiln 12 / 87, quarry 53 / 227. The saved scenes passed geometry/material/UV, movement/loop and authored floor checks; quarry cable/hatch/gallery checks cover all 481 source frames. MP4 decoding verified 640Ã—640 previews of 2, 8 and 16 seconds respectively. Four quarry stills and five stills per factory are saved at 1800Ã—1800 with current reports, height manifests and file hashes in the review folders. `outputs/final-art-review-summary.json` records the copied set. The modding skill was updated and its structure validation passed. No game package or workbook footprint was changed during this art pass.



### Earlier accepted art passes



Latest pass: the user approved the kiln and requested the same worn, detailed treatment for the crusher. The crusher now has the same material palette/weathering, wider side/rear decks, a substantial stair, separate perimeter rail nodes, feed-gate handwheel, bearing oilers and adjusters, machine controls, workshop supplies, lanterns, roof repair and localized wear. Its exposed rollers, flywheel clearance slot and short rear covers remain. Current files are under `docs/art/reviews/2026-10-19-crusher-workshop/`; the earlier review directory is archival. The user subsequently accepted this worn crusher and requested the quarry. This is a Blender review, not a game screenshot. All five animated nodes passed sampled movement/loop checks; UV/material presence and 56 separate rail nodes across five runs passed. The source contains 90,180 vertices and 60,930 polygons; the MP4 is a two-second 640px preview.



The shared joinery was extracted to `industrial_geometry.py`; `check_kiln_joinery_refactor.py` compared all 100 kiln nodes against the approved scene and found zero vertex differences. The approved kiln source scene was not overwritten. The shaft inspection confirmed native connection-driven model variants; the shared rail component uses native instant-navigation notifications, completed neighboring paths or matching factory ports, and two-way graph checks. The official build succeeded and installed the new DLL (`outputs/walkway_official_build_wrapper.log`). No reviewed mesh was exported and Timberborn was not restarted in this pass.



2026-10-19: the user accepted the crusher's rebuilt Blender appearance as good enough and directed work to the kiln. The crusher still uses `docs/art/concepts/02-concrete-production-concept-v1.png`; its active geometry is `tools/asset-pipeline/crusher_sheet_geometry.py` and scene is `src/DeepFrontier/Art/Source/StoneCrusher-ReferenceStudy.blend`. Character-like entrance props have since been removed from both crusher and kiln at the user's request. Current review uses angled renders only; historical top views are archival. Tile dimensions remain undecided. No game assets were exported, installed or tested during this art pass.



The kiln now uses the user-supplied `docs/art/concepts/Cement Kiln 3D Reference Sheet.png`, specifically **Front Left, Front Right and Back Left**. The exact source image is also preserved in `src/DeepFrontier/Art/Concepts/` (matching SHA-256). Its source is `tools/asset-pipeline/kiln_isometric_geometry.py`. The longer covered hall contains ten barrel shell sections, three riding tyres with six support rollers, a reduction gear/flywheel, two elevated feed bins, a masonry firebox and riveted tapered chimney. It has two substantial stairs, capped rails, underfloor braces, lanterns and an iron furnace register. Later user feedback widened all perimeter walks and stairs, moved the porch canopy outside the walking route, recessed the controls and added worn timber, oxidation, roof repairs, stair scuffs, oilers, a feed-gate handwheel, tools and a spare tyre. Four current 1800px Blender review views were inspected and saved under `docs/art/reviews/2026-10-19-kiln/`. The full roof still covers the barrel. The user has now explicitly approved this kiln appearance. It is not yet integrated into the game.



The user requires pathable building decks/stairs and adaptive railings as a reusable feature. `tools/asset-pipeline/walkway_geometry.py` now creates 87 separate rail/post nodes across the kiln's nine outer runs, recorded in its rail manifest. `docs/building-walkways.md` captures verified native housing navigation, connection APIs and integration requirements. Double/Triple Lodge use native internal navigation edges; the 1Ã—1Ã—1 restriction found in DynamicPathModel applies only to that visual component. `src/DeepFrontier/Scripts/BuildingWalkway.cs` now implements the shared railing adapter and passed the official build. No building blueprint activates it yet. Native route/grid bindings, staircase movement and in-game openings remain unfinished and unverified. No custom pathfinding or Harmony patch was added.



The kiln's saved Blender scene passed animation-node, sampled movement, loop closure, UV/material and rail-manifest checks. Its twelve moving parts use an eight-second source loop (241 endpoints at 30 fps); the 640px MP4 preview samples it at 7.5 fps. `docs/art/reviews/2026-10-19-kiln/CementKiln-motion-check.json` records the checks. These checks do not establish in-game animation, navigation or material appearance.



The earlier crusher's three angled stills and its two-second MP4 were regenerated after removing the character-like props. Its five moving parts also passed the saved-scene checks. Blender decoded the kiln preview as 640Ã—640/60 frames/7.5 fps and the crusher preview as 640Ã—640/30 frames/15 fps. Current review videos and reports are saved in their respective dated review directories.



The user rejected both initial crusher Blender drafts for failing to match the approved concept, before accepting the later rebuild. Ignore all tile counts, including printed concept labels; model ALL reference buildings in Blender first and size the game footprint afterward. On 2026-10-19 the user further prohibited using top-down concept views for every future model. `docs/art/approved-designs.md` records this precedence. `render_reference_studies.py` produces standalone art studies without exporting or installing them. No claim of current in-game appearance follows from these renders.



The v2 official build completed successfully (`outputs/crusher_v2_official_build_wrapper.log`, `outputs/unity_official_build.log`). Timberborn was NOT restarted to load that package before computer control stopped, so the displayed running game still showed earlier assets. This is not runtime verification of the new mesh or materials. The next game check requires a fresh process and confirmation of the installed asset version.



The user rejected the existing meshes on 2026-10-18: they do not visually fit their footprints, lack sufficient architectural and mechanical detail, and do not read as recognizable buildings. Existing export checks establish file structure only; they are not visual acceptance. The current models and colored icons are not approved final art. Concept review now precedes mesh replacement. Use the official BerryJam example's JamStove and BerryJam icons as the accepted UI direction: single-colour pale ivory/gold linework and selective solid fills on transparency. The prompt set is `src/DeepFrontier/Art/Concepts/concept-prompts-v1.json`.



## Latest settlement test



Run 13 loaded the unchanged recovery save with the corrected DLL. The sandstone pit assigned two workers and its inventory increased from zero to 21 sandstone through actual native gathering, without the run-11 crash. The output inventory panel now displays the good and its 40-unit capacity. The test was paused after this observation; limestone extraction, processing into aggregate/cement/concrete, power behaviour and save/reload after gathering remain unverified. `outputs/timberborn_construction_world_13.log` records the load. All Buildings Transfer Power and No Build Restriction were disabled through the official Mods menu for native power/support acceptance; the required foundation mods remain enabled. Native loading validation removed the accidentally stacked upper limestone pit and roof path as invalid locations, leaving the lower construction site. Run 12 was a startup-only attempt and never loaded a settlement.



Run 11 successfully created **Concrete Acceptance**, Iron Teeth, on **Deep Frontier - Concrete Test** (`outputs/timberborn_construction_world_11.log`). The four geological sources appeared. Sandstone and limestone pits could be unlocked, placed and completed with native developer controls. Connecting the missing district-centre entrance tile cleared the sandstone pit's road warning, and two workers were assigned. Actual production was not verified: the first scavenger decision crashed because our custom pit spec lacked the `YieldStatus` decorator registered for vanilla scavengers by `RuinsUIConfigurator`. `MineralConfigurator.cs` now registers it and the native output-inventory fragment enabler. The official rebuild passed; run 13 verified sandstone gathering as recorded above.



The same run exposed shared mineral resource groups causing both pit tooltips to list both goods. The producing generator now gives each mineral its own group and extends the native removal strategy with both. Static construction and model-binding checks passed. No Build Restriction can override authored support rules through its AlwaysSolid setting; run 13 isolated that optional override. The game-generated error save was preserved unchanged as `ExperimentalSaves/Concrete Acceptance/Concrete chain recovery.timber` for retesting. No concrete, aggregate or cement was created by developer controls.



## Concrete construction chain



Development mod configuration: Moddable Weathers 11.0.0 crashes Plains map-editor loading in `ModdableHazardousWeatherService.MHazardousWeatherDuration` (run 4). It and Weather Scientific Projects 11.0.0 are disabled for testing; the latter requires the former and must be disabled explicitly. No Dev Mod is disabled to permit native developer test controls. Deep Frontier was moved below Timber Pipes in the official Mods list; its dependency-order warning disappeared. These changes do not remove installed packages.



Run 6 exposed Iron Teeth material references unavailable in the map editor's Common collection. The authoring generator now registers the four exact source-mesh materials in Common. Run 7 passed material import, then exposed Game-only navigation decorators registered in MapEditor. The shared mineral configurator and Game-only workplace/navigation configurator are now separate. Run 8 loaded Plains in the official map editor successfully. All four geological objects were placed and saved as `Documents/Timberborn/Maps/Deep Frontier - Concrete Test.timber`, with a project copy in `outputs/`. Reading its native `world.json` confirmed both outcrops persist 600 units and both seams retain their coordinates. This establishes editor placement and serialization, not settlement production.



- Canonical catalog: `tools/construction_materials.json`; generated by `tools/create_construction_material_content.mjs` through the normal generation entrypoint.

- Five goods: sandstone, limestone, aggregate, cement, concrete. Seven buildings: two gathering pits, two permanent quarries, crusher, kiln, mixer. Four source entities: two finite outcrops (600 units each) and two permanent seams.

- The starter line uses vanilla construction goods and 750 hp. The first 120 concrete can build both permanent quarries, adding 3,000 hp. The kiln uses native log fuel and vanilla Dirt; no heat subsystem.

- Native `Yielder` supplies quantity/reservation/persistence, native scavenger behaviors handle gathering, and native mine understructure constraints handle quarry placement. Only the mineral selector and deposit lifecycle need small custom decorators; no Harmony patch.

- All construction-cost goods and recipe inputs/outputs belong to the active Common + Iron Teeth collection. Older Folktails-only recipe inputs were replaced at the source generator with Iron Teeth goods.

- Static reachability includes building costs, finite bootstrap, permanent continuation, and a missing-cement-producer mutation. It does not prove actual production or placement.

- New original UV-mapped machinery, source meshes, construction stages and rendered UI icons are exported. Existing deep-ore markers also received model/understructure corrections after the model-binding audit found retained vanilla model roots.

- Workbook Buildings, Items, Recipes, Progression, Transport, Sources and Overview include exact authored construction values. Its older planning rows remain design drafts and need broader synchronization. Export/recalculation and the power-summary input-change check passed; changed ranges were visually inspected.

- Required before playtesting: an authored map containing both outcrops and both seams; successful gathering, processing, placement, animation, source depletion and save/reload checks.



## Existing content and evidence



- Generated data currently includes 58 goods, 47 recipes, 32 building definitions, and six map-editor objects.

- Original Blender geometry and Timbermesh exports exist. The export validator found 32 finished models with 61-frame Default animation clips at 30 FPS. In-game appearance and playback still require verification. Older pre-construction meshes still need axis/footprint review.

- Static content and asset validators cover selected fields and files. They do not establish working gameplay.

- Earlier Unity imports and a headless run succeeded, but later graphical world creation failed. The previous description of a load-safe/playable shell was premature.

- The dependency manifest captures the required foundation mods and supporting libraries. Declaring a dependency does not implement its transport integration.

- Custom material authoring remains in `DeepFrontierMaterials.cs`. It requires its texture and shader explicitly. Bundle compilation and installation belong to the official builder.



## Outstanding implementation



The mineral gathering decorators are implemented. Nuclear coolant failure and meltdown, persistent waste custody and demolition guards, training/commissioning, transport adapters, civic services, and launch sequencing are not complete.



Settlement run 9 rejected NuclearReactor because `Manufactory` and `GoodConsumingBuilding` both implement `IGoodProcessor`; native `GoodProcessorRegistrar` requires one. The reactor now uses a complete native Smelter-style workshop/manufactory with one recipe processor. `WorkshopPoweredGenerator` connects productive workshop activity to the native mechanical output (75,000 hp; zero input). Its current batch recipe consumes 6 coolant per 2 working hours, fuel lasting 10 cycles, and produces 4 waste per cycle. This resolves the component conflict at authoring time but is not the final continuous-coolant reactor safety system. The earlier validator incorrectly equated component presence with continuous coolant safety and persistent waste custody; it now explicitly checks only authored production contracts. The official rebuild passed; subsequent settlement runs 10â€“13 are recorded below.



Production reachability needs an audit: the fish/juvenile-fish cycle needs a starting source, Iron Teeth recipes must not rely on Folktails-only goods, and all designed resources need reachable producers. The workbook and implementation plan describe intended behavior rather than verified runtime behavior.



Run 10 passed all building-preview creation, then failed in `TopBarPanel.CreateCounter`: PureWater and ReactorCoolantWater shared the native single-resource Water category. The generator now places those industrial liquids in Ingredients. DiningService also used an undefined Wellbeing goods group and now belongs to Ingredients. Active-faction goods-group and singleton-cardinality validation passed after these corrections. Run 11 subsequently loaded the settlement successfully, then exposed the gathering issue described above.



The next acceptance checks are official package output, Iron Teeth world creation, menus and placement, production and hp behavior, animations, and save/reload. Full playtest readiness requires implementing and verifying the outstanding mechanics.



## Maintained guidance



Static validation: `pwsh tools/validate_all.ps1` runs, in order, the promotion clearance checks, every `validate_*_exports.py`, the saved-scene source checks (Blender; `-SkipBlender` omits them), `validate_model_bindings.py`, every `tools/validate_*.mjs`, `audit_progression.mjs`, `audit_item_uses.mjs` (report only, prints the count) and `audit_building_assets.py --require-mirroring`. It prints a PASS/FAIL table with each failure's first error line, keeps full logs in `outputs/validate-all/`, and exits 1 on any failure. Use `-List` for ids and `-Only <ids>` for a subset; `promote_style_exports.ps1` calls it with its unchanged check list. In-game acceptance runs: `docs/acceptance-runs.md`.

The discoverable skill is `C:/Users/Jordan/.codex/skills/timberborn-modding/SKILL.md`. It records official-tool workflows, source-confirmed contracts, project constraints, and the requirement to update discoveries during the same session. Skill structure validation passed.



Use `docs/implementation-plan.md`, `docs/feature-feasibility.md`, and the workbook for design requirements. No normalization or fallback logic; correct source contracts and report errors explicitly. Gas/scrubbers are low priority; heat and maintenance systems are excluded.

## Build 180 — buildable tops no longer stop workers (2026-10-26)

User report: the Fish Hatchery never got workers and showed no status. `SaveInspectionProbe` (now also listing `BlockableObject` blockers and water work cells) on `leg Day 20-11 copy`: the hatchery was blocked twice by native `BlockObjectBelowBlocker`, from two finished solar panels standing on its stackable deck. A blocked `Workplace` is never understaffed, so no beaver is assigned and no status shows; `AutoEmptiable` had also marked it for emptying. Water depth (0.65 m in all four cells) and the district were fine. 28 Deep Frontier workplaces have stackable blocks, so all were exposed.

Fix: `Scripts/StackableTopBlockExemption.cs`, a Harmony prefix on `BlockObjectBelowBlocker.FillBlockableObjectsBelow` that skips an object below wherever its own block at that cell is stackable; anything else below is blocked as before. Build 180 verified (652 hashes). The re-inspection shows the hatchery unblocked, with no blockers and the native "No available workers in district." status, and no exceptions. Launched for the user (log `outputs/timberborn_build180.log`).

## Build 181 — Greenhouse yields 8x (2026-10-27)

At the user's request every Greenhouse product is 8x, with ingredients and the 8 h cycle unchanged (`create_frontier_expansion_content.mjs`): Eggplant 6→48, Kohlrabi 14→112, CoffeeBean 3→24, and Aquaponics 10 Kohlrabi + 2 FreshFish → 80 + 16. `docs/progression.md` is updated. Output storage follows the native rule (product × CyclesCapacity 30). validate_all: 49 pass and 1 report-only; editor guards pass. Build 181 verified (652 hashes) and launched for the user.

## Builds 182–188 — Restaurant panel, partial meals, Fine dining, kitchen batches, late shift (2026-10-27)

- **Panel** (`Scripts/RestaurantPanel.cs`): built from native elements only. It has native `InformationalRowsFactory` rows for the full meal, the extras and the kitchen ingredients, plus one native `ProductionProgressFragment` layout per kitchen recipe (filled by `ManufactoryDescriber`) with that recipe's real progress. It sits in the middle section at order 20, in place of the native `ManufactoryInventoryFragment`. That fragment and `ProductionProgressFragment` are hidden for the Restaurant (`RestaurantNativeFragmentHider`).
- **Partial meals**: `HasMeal` means any main food is in unreserved stock. Each order takes every main food and extra in stock. Only a full meal (one of each `Foods`) applies `RestaurantDining`, now displayed as "Fine dining" (`DeepFrontier.Need.FineDining`). A partial meal gives just its foods' own effects.
- **Kitchen batches** (`RestaurantKitchenChooser`): haulers also deliver the kitchen's dishes, so a batch's products could stop fitting mid-batch and stall the kitchen (save: FermentedCassava at 47% with its stock at 32/32). Such a batch is now set aside with its progress and consumed ingredients, saved as `DeepFrontierRestaurantKitchen`. It resumes when its products fit.
- **Cooks**: half the assigned staff (rounded down) work the kitchen while it can produce and serve otherwise. Before this, a full dining room kept all 4 serving and nothing cooked.
- **Late shift** (`Scripts/RestaurantLateShift.cs`): Restaurant staff `WorkerWorkingHours` run past the colony's end by half the off-work time (16 h working hours: until hour 20).
- **Visit needs**: `VisitEffects` advertise each served good's own needs (fermented foods, cake, coffee, thirst) at their points per 0.25 h of service.
- **Verified** on build 188 with the `leg latest copy` save (`-SaveInspect` service log). Staff were on duty until 20.0, off overnight and back at about 0.4. 15 partial meals were served with EggplantRation at 0. FermentedSoybean, SweetBerryCake and FermentedMushroom batches ran to completion in turn, and FermentedCassava stayed set aside at 0.47. There were no exceptions. validate_all: 49 pass and 1 report-only.
- **Not verified**: a full meal granting Fine dining (the save has no eggplant rations); interaction with the Second Shift mod's two-shift toggle.

## Builds 189–190 — recovered-goods crash fixed; cook switching confirmed (2026-10-27)

- **Crash** (user game, build 188, 13:02): a builder hauling a `RecoveredGoodStack` asked every inventory's `UnreservedCapacity`. `RestaurantKitchenStock.AllowedAmount` used `Single` over the authored stock and threw for goods the Restaurant doesn't keep. It now returns 0 for unstocked goods, per the native `IGoodDisallower` contract. The other disallowers (cryogenic intake, bot maintenance) already return 0 for unknown goods.
- **Probe**: `-deepFrontierRunSeconds N` (`start_memory_load.ps1 -RunSeconds`). With `-SaveInspect` the service log runs at speed 3 and records cooks (`ProduceExecutor` running), waiters (order stage) and waiting guests.
- **Verified** on build 190 with `Memory Test\crash test copy` (the user's 13:01 autosave), 1000 game seconds, no exceptions. With an empty dining room and the kitchen ready there were 4 cooks (60 samples). With 8–11 guests waiting: 2 cooks and 2 waiters. Mixed states had 3 cooks and 1 waiter, or 2 and 1. Process peak was 12.4 GB at speed 3; not investigated.
- The user's session since 10:46 was in the Memory Test settlement: the game's Continue loaded the probe's `leg latest copy`.

## Coal and Oil Power Plants are workerless native Steam Engine generators; DeepOil doubled: generated and validated in the real Data, not built or tested in game (Claude Code session, 2026-10-27)

- **Generator** (`frontier_progression.json` `powerPlants`, `makePowerPlant` in `create_frontier_expansion_content.mjs`): both plants clone the vanilla Iron Teeth Steam Engine (`GoodConsumingBuildingSpec`, `GoodPoweredGeneratorSpec`, `MechanicalBuildingSpec`, `PowerGeneratorSoundsSpec`, `GoodPoweredGeneratorAnimatorSpec`, `MechanicalNodeIlluminatorSpec`) with their study model, footprint, cost, science, output, pipe ports and shaft faces. No workplace, manufactory or workshop specs. Coal: 1 Coal + 1 Water per hour, 5,000 hp; oil: 2 CrudeOil + 2 Water per hour, 20,000 hp; `FullInventoryWorkHours` 50 (vanilla). Native `GoodPoweredGenerator` (decompiled 1.1.2.8) pauses consumption while the graph does not require power and sets output 1/0 from `IsConsuming`, so fuel burns only under demand, day and night. The staffed-workshop branch and the `CoalFiring`/`OilFiring` recipes (definitions, `RECIPE_FUELS`, `RECIPE_NAMES`, localization, generated recipe blueprints, `validate_vertical_slice_content.mjs` ids) are removed.
- **Coupled systems:** smoke runs on the Steam Engine's `PowerGeneratorParticleController` (`vanilla_smoke.mjs` picks it for any `GoodPoweredGeneratorSpec`; ilspycmd: plays while `ActiveAndPowered && OutputMultiplier > 0`); `GoodPoweredGeneratorAnimator` replaces the workshop animation controller (`lategame_building_content.mjs`); smog Activity `Generator` (new in `smog_building_content.mjs` and `Scripts/Smog/SmogEmitter.cs`, same condition as the particles); sounds `loopDriver` `powerGenerator`; workforce risks and bot upkeep entries removed (no workers); automation sources `MechanicalBuildingSpec` + `GoodConsumingBuildingSpec` (`GoodConsumingBuilding : IFinishedPausable`); map site rules treat `GoodPoweredGeneratorSpec` as a power generator (`prepare_deep_frontier_map.py`, unchanged result for both plants); `validate_model_bindings.py` requires a generator for power-generator particles; `LategameAcceptance` records a skip for the plants' workshop-animation wave (generation is checked by `AllBuildingsAcceptance` power supply, which already handles workerless `GoodConsumingBuilding` targets).
- **DeepOil:** 1 DeepOre + 3 Water -> 6 CrudeOil per 2 h (was 3). One processor on oil (3 per working hour) supplies 1.5 oil plants at full load during its working hours.
- **Checks passed:** `promote_style_exports.ps1`, `aquaculture_workbook.mjs`, `validate_all.ps1 -SkipBlender` 49 pass + item-uses report only, `validate_editor_guards.mjs`, incremental compile of all scripts (0 errors). Item uses: Coal 4 (Operation: CoalPowerPlant), CrudeOil 3 (Operation: OilPowerPlant).
- **Open:** build and in-game check of generation under demand only, burn rates, night operation, smoke and smog stopping when demand ends, automation pause, and pipe/hauler supply of fuel and water.

## Builds 193–202 — workerless power plants, Deep Oil x2, cake tooltip crash, building passages replace Hooman Stairs (2026-10-27)

- **Tooltip crash (build 191)**: Sweet Berry Cake's custom `GoodType` `RestaurantDish` had no stockpile, so the native top-bar `GoodStockpilesTooltipFactory.AddIcons` threw `KeyNotFoundException` on hover. Cake is now a native `Box` good. It stays table-only because the Restaurant inventory is givable only and blocks counter eating. The probe builds every good's tooltip; all 92 build.
- **Power plants**: Coal (5,000 hp; 1 Coal + 1 Water per hour) and Oil (20,000 hp; 2 Crude Oil + 2 Water per hour) are native Steam Engine generators (`GoodConsumingBuilding` + `GoodPoweredGenerator`), with no workers. They burn only while the network needs power, day and night. `CoalFiring`/`OilFiring` were removed. The smog emitter gained a `Generator` activity. Details are in the earlier entry written by the conversion helper.
- **Save migration** (`Scripts/PowerPlantSaveMigration.cs`): native `GoodConsumingBuilding.Load` throws when its component is missing, so a plant saved as a workshop crashed the load (user save, build 193). For those two templates only, it now starts with empty supplies; any other missing component still throws.
- **DeepOil** makes 6 Crude Oil (was 3) from 1 Deep Ore + 3 Water per 2 h.
- **Building passages** (`Scripts/BuildingPassages.cs`) replace the Hooman Stairs mod.
  - Touching finished buildings in one district get a passage, stacked or side by side; eligible buildings are homes, workplaces, storage and attractions, excluding district centres and crossings.
  - A passage is a breadth-first, 6-direction unit path through both buildings' cells, doorstep to doorstep, plus each building's entrance↔doorstep step. Its steps are native nav edges in group `DeepFrontierPassages` at costs 0.6/0.8.
  - Patches: `NavMeshSource.Block/UnblockEdge` skip that group, `DistrictObstacleService.IsSetObstacle` exempts its nodes, and `Accessible.SetAccesses` routes a linked building to its doorstep. The doorstep flow fields are cached, and native access returns when a building's last passage goes.
  - Costs: at cost 1, `NavMeshSourceNode.IsConnectedTo` (cheapest unblocked edge wins) let native non-road edges tie and win. That made 54 of 86 doorsteps road-unreachable in build 201; at 0.6/0.8 all are reachable.
  - Incompatible with Hooman Stairs: while its assembly is loaded, passages are not bound, and the main menu shows a dialog naming the conflict. The `Calloatti.HoomanStairs` enabled flag was set to 0 in the user's Timberborn settings, at their request.
  - The optional Hooman Stairs bridge assembly from builds 193–198 was removed, including its wiring and installed file.
- **Verified** on build 202 with the user's 14:40 save copy: 97 passages (44 stacked) and 86 linked buildings. All 97 are walkable both ways with the native road path search. All 86 doorsteps are reachable from the district centre, with 0 lost and 0 gained (every building in this save already has road access). There were no exceptions. The Oil plant filled to 100/100 and burned on demand; the Coal plant had no coal delivered. With Hooman Stairs on (b201 reference), its 26 top buildings: 24 kept, 0 lost.
- **Not verified**: removing a building (passage cleanup); a building whose only access is a passage; the main-menu incompatibility dialog on screen.
- **Test-run hazard**: probe runs load copies in the "Memory Test" settlement, the one the user plays in, and their autosaves rotated out the user's autosaves. The user's 14:40 autosave was restored from the byte-identical test copy.

## Build 204 — repository and Workshop preparation (2026-10-27)

- **Workspace cleanup** (user approved deleting):
  - Root `.tmp_*` scripts, the 112 Blender `.blend1` auto-backups (6.4 GB), and the Blender download zip.
  - From `vendor/`: the Unity installer, Ghidra and its zip, the old Mod Manager source, and the datvm and Hooman Stairs reference copies.
  - All of `outputs/` except the 13 folders the content generators read. These were found by regenerating against an empty `outputs/` and restoring only what each failure named, until `promote_style_exports.ps1`, `aquaculture_workbook.mjs`, `validate_all.ps1` (49 pass, 1 report-only) and the map validator all passed.
- **Compile checks** moved from `outputs/contamination-consumers-compile` to `tools/compile-check` (`DeepFrontierCompileCheck.csproj` plus the Moddable Weathers and Sluice is Back! projects); all four build.
- **Repository files**:
  - New README, LICENSE (MIT code, art all rights reserved), `.gitignore` (vendor, local tool installs, untracked outputs) and `.gitattributes` (`*.blend` in Git LFS).
  - `src/DeepFrontier/README.md` updated; the manifest description rewritten for the in-game uploader.
- **Workshop**: `workshop/description.bbcode`, `workshop/thumbnail.png` (640×640) and `workshop/screenshots/` (8 images), all from `Scripts/ShowcaseCapture.cs` (`start_memory_load.ps1 -Showcase`: UI hidden, camera aimed at each listed building) on the user's 19:09 save copy. The thumbnail is also copied into `Documents\Timberborn\Mods\DeepFrontier`.
- **Verified**: build 204 matches all 650 files.
- **Public-repo preparation** (2026-10-28):
  - No longer tracked, kept on disk: `outputs/vanilla-icons` (game icons), `outputs/native-civic-assets` (meshes, materials and reference scenes extracted from the game and from New Styles), `outputs/workforce-api-1.1.2.8` (decompiled excerpts), `docs/art/references/new-building-styles` (another mod's Workshop previews) and `tools/target_mod_packages_1_1.json` (other mods' blueprints).
  - The README explains how to recreate the game references locally.
  - History was recreated without them, under the GitHub no-reply e-mail.

## Blender scenes slimmed; Git LFS dropped (2026-10-28)

- **Size**: the 116 tracked `.blend` scenes were 6.29 GB, uncompressed, and about 95% packed images, nearly all game textures. That included the 4096² water normal map (18.7 MB) packed into 100 scenes, and Iron Teeth plaster and wood textures, often packed twice.
- **Cleanup** (`tools/asset-pipeline/unpack_blend_textures.py`):
  - Game textures (`<path id>-<name>.png`) went to the untracked `src/DeepFrontier/Art/GameTextures/`.
  - Deep Frontier textures point at their identical tracked files (asset-bundle materials, `Art/Textures/Reference`), or were written to `Art/Textures/Packed/`.
  - Duplicate copies were merged, unused data purged, and the scenes saved with Blender's compression.
  - Each save requires an unchanged fingerprint of geometry, transforms, material slots, node links and image bytes.
- **Result**: the scenes are now 62 MB, about 1% of their old size.
- **Game texture references**: `tools/asset-pipeline/game_texture_refs.py` lists every game texture the scenes use into `src/DeepFrontier/Art/GameTextures.json` (58), and points scenes whose external game textures had been deleted from `outputs/map-objects` at GameTextures (12 scenes). `tools/asset-pipeline/extract_game_textures.py` recreates the folder from the installed game by path id; a mismatched texture name fails.
- **Verified**:
  - All 116 scenes open with no packed images and every texture file present.
  - Re-exporting the Bathhouse from the original and the cleaned scene gives identical model content (`tools/asset-pipeline/compare_timbermesh.py`).
  - The official exporter is not byte-stable: two exports of one unchanged scene differ by float noise up to 0.001 in one vertex attribute.
- **Repository**: `.blend` files are back in normal git, and the repository uses no LFS storage. The originals are backed up in `Documents\TimberbornModding-blend-backup`.
