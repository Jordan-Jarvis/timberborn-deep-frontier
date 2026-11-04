# Mineral source authoring

Updated 2026-11-04. Implementation is authoritative; verification results are in `tools/STATUS.md`.

## Visible outcrops

`DeepOreSource` (display name **Deep Ore Outcrop**), `SandstoneOutcrop` and `LimestoneOutcrop` use `MineralDepositSpec` and the native `Yielder`. They are map objects, not inventories or district buildings.

- A Scavenger Flag collects **Raw Deep Ore** from an accessible ore outcrop within its work range. Sandstone and limestone use their respective pits. Workers carry the extracted goods to their workplace; native hauling then supplies consumers.
- New ore outcrops hold up to 10,000 raw ore. Stone outcrops start with 600 of their mineral. The map editor amount field uses native undo. Built-in map variants explicitly author raw ore amounts in `tools/map_variants/*.json` with `good: RawDeepOre`.
- Empty outcrops remain on the map. Each recovers **20 units after five days**; recovery stops while stock remains. The native time trigger's progress persists across saving. It does not run in the map editor.
- The source panel shows remaining stock and its recovery countdown. It needs accessible ground for a worker, not a road attached to an entrance.

## Deep Drill

Each two-minute recipe cycle takes **1 Raw Deep Ore + 3 Water -> 1 Deep Ore**. It draws **1,000 hp** and uses **0.1 Metal Block + 0.1 Treated Plank per full-crew operating hour**. These are operating supplies in the same native inventory, not crafted drill-bit items. Missing-supply statuses name the actual goods.

The drill consumes physical stock delivered by workers/haulers or compatible transport. There is no invisible district ore pool and no requirement to build the drill over an outcrop. Raw ore also has a second useful route: the Stone Crusher turns **3 Raw Deep Ore -> 8 Dirt** for brick production.

## Permanent extraction and exhaustion recovery

- A Deep Mine must stand on `DeepOreVein`. It produces **4 Deep Ore from 12 Water** per two-minute cycle, with **7,700 hp** demand and its existing metal-block/brick operating supplies.
- Its construction no longer consumes Deep Iron (`DeepAlloy`) or Steel (`HighGradeSteel`), so those goods cannot block access to their own permanent source.
- Sandstone and Limestone Quarries must stand on their matching permanent seams. Their construction uses Planks, Treated Planks, Metal Blocks and Gears, not stone-derived materials or deep metals. This also permits recovery in older saves whose stone outcrops were already removed.
- The slow outcrop yield is a recovery route, not a replacement for quarries/mines. A permanent seam/vein must still exist on the map; the mod does not invent one when a player deletes it.

## New games and existing settlements

All 19 supported built-in maps place raw-ore/stone outcrops and permanent veins/seams during new-game setup. Workshop/custom maps keep their authored contents: missing deposits produce a one-time warning listing the absent types, and players place them manually. Existing settlements get the same check after loading; no deposits are silently added. Empty recovering outcrops count as present. The notice is saved per settlement so it does not repeat on each reload.

In a running settlement, enable native developer mode and open the map-object category (mountain/tree icon). It contains Deep Ore Outcrop, Sandstone Outcrop, Limestone Outcrop, Deep Ore Vein, Sandstone Seam and Limestone Seam. Place them on suitable clear ground; permanent seams/veins need space for their matching mine. All six use `DevModeTool: true` and the common map-editor template collection. `validate_map_setup.mjs` checks those registrations; build 274's native UI placement of an ore outcrop yielded its full 10,000 raw-ore stock.

## Author a map

1. Place accessible outcrops in the native map editor; leave room for workers to reach them and for a flag/pit within range.
2. Set their starting amounts. Use `RawDeepOre` for ore placements in the built-in variant files.
3. Place permanent stone seams and deep-ore veins with usable mine sites.
4. Run the map checks. They validate placement, routes, source budgets, permanent sites and a deliberately low recharge rate. The initial stock budget excludes future recovery.

## Existing saves

Template names remain unchanged. Native mineral yield amounts load normally. Old `DeepFrontier.DeepOreDeposit` amounts/timers and older `Inventory:Stockpile` ore amounts migrate explicitly to the raw-ore outcrop. Empty old stockpiles mean zero remaining ore and begin recovery. Deleted outcrops cannot be restored from missing save entities; bootstrap quarry costs address that older-save case.

Existing processed Deep Ore in warehouses remains processed ore. The drill retains its recipe id and native production progress. See `MineralDeposit.cs` for the two supported legacy source formats and `OreHaulingAcceptance.cs` for the opt-in native hauling/recovery test.
