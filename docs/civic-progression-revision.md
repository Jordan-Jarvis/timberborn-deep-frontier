# Civic services and advanced industry — 2026-10-19

This records the user's latest requirements and supersedes the older factory/service-token descriptions in the workbook and early blueprints. `tools/frontier_progression.json` holds the requirements and clearly marked balancing proposals. Restaurant kitchen/service, aquaculture, hospital treatment and grocery shopping/neighborhood service have passed their native acceptance and fresh-process continuity checks. Physical transport integration and economic balance are being tested separately; exact evidence is recorded in `tools/STATUS.md`. The reactor science override is authored, while the wider reactor, worker eligibility, aluminum and advanced research work remains unfinished.

## Restaurant

Keep the accepted grand model, fourteen seats around seven tables, four doors at layers 0/2/4/6, native materials/plants, and separate player-built stairs. The current export registration is 10×8×9; this encloses the artwork without scaling it. Occupancy must follow rooms and slabs, not fill that whole envelope. Registration and route drafts are integration artifacts until native placement, movement and clearance tests pass.

A beaver reserves a seat, arrives and sits. An actual restaurant worker serves a meal. That completed service deducts several real foods from one native inventory, applies their native food effects, and grants a separate dining wellbeing benefit once. Fish and berries are required menu ingredients; the initial proposed additional courses are fermented mushrooms and eggplant rations. The grocery complements that assortment with canned foods, algae/corn rations and other staples. There is no restaurant-ration or DiningService product.

The restaurant demands 400 hp and offers the native fermenter recipes. Its unique Sweet Berry Cake uses berries, corn and water; cake is cooked and eaten only at restaurant tables. Workers include coffee when available. They serve one Water to a thirsty diner who can use its full native 0.33-point effect; already hydrated diners consume none. Water remains stocked even when the selected cooking recipe needs none. Drinks and cooking share the actual native input inventory.

Use the native `Enterable`, `AttractionNeedBehavior`, `FixedSlotManager`, `TransformSlot`/`Sitting`, `Inventory`, `NeedManager.ApplyEffect(InstantEffect.FromSpec(...))` and food-consumption event contracts where they fit. Native attraction effects must not grant hunger or dining points while a guest is merely waiting. Native `GoodConsumingAttraction` consumes building supplies by time while anyone is inside; that is not the requested per-meal contract and must not be used as the meal deduction mechanism.

Serving needs a small explicit job component: reserve a diner, walk a worker to the authored service approach, complete service, debit the complete menu atomically and apply the good effects once. The worker and guest are separate roles. Do not let workers occupy diner seats or let visitors consume staff capacity. Cancellation releases reservations; leaving or saving must never issue a free duplicate meal. Use the native walking/job and inventory systems rather than adding a parallel pathfinder, inventory or generic ration good. A worker assignment alone is not proof of attendance or service.

Tests: unstaffed, staff walking, seated and waiting, served once, partly missing menu, paused, diner leaves, worker interrupted, inventory reserved by hauling, all fourteen seats, save/reload during service, hauling/belt delivery, and distinct food-need changes. Verify actual visible serving motion before claiming it works.

## Aquaculture and shore fishing

The user added low-yield fishing at the existing gatherer flag on 2026-10-19. This provides initial fresh fish from real world water; it does not require a finite fish deposit or a pre-existing aquaculture inventory. The first authored balance is one FreshFish per four base working hours plus walking and carrying, using the flag's existing one worker and output inventory. Fishing is an explicit job selection so plant gathering remains available. Reachable banks, at least 0.5 water depth, no more than 1% contamination and a surface within 1.25 layers below the bank are the initial constraints. Builds 44/45 verified catch delivery, saved-catch continuation and water/job interruptions. Broader balance remains for playtesting.

The fish hatchery then uses FreshFish + Algae + Water to breed JuvenileFish; Fishery Works grows these with Algae + Water into more FreshFish and separately renders FishOil. The flag closes the bootstrap cycle without inventing starter stock. Permanent aquaculture still depends on renewable feed, water, workers and power. JuvenileFish remains a non-edible ingredient and still needs a second useful downstream use before release; direct-food exemptions do not cover it.

The latest user requirement places part of the hatchery over real world water, similar to a native swimming pool. Its front bank is supported and its rear nursery uses native water-height and badwater blocking. Delivered Water remains a separate breeding ingredient. Build 57 installed the reference-derived open-pen nursery at 8×8×5/BaseZ=1 and passed dry/refill/pollution, actual production and walking, tank levels, shafts, rails and dock platform stacking. A fresh reload resumed breeding, and a separate zero-fish-stock run completed real shore catches, hatchery breeding, native juvenile hauling and Fishery production. JuvenileFish's second useful downstream use and broader economy balance remain unfinished.

The waterfront Fishery Works revision follows the individual Fishery.png isometric reference with changed floor and roof proportions. Build 51 installs its 12×10×7 sparse registration, 34 authored route cells, three doors at levels 0/2, 19 individually adaptive rail openings and two clear working-roof platform cells. It demands 80 hp and generates zero; the visible wheel circulates water instead of producing free power. Four rectangular basins and two native small tanks display one shared native workshop Water inventory (90-unit capacity from the current 30-cycle fish recipe allowance). Run/reload 51 passed native placement, shaft power, roof platform stacks, production, water levels, wheel pause, stairs, real door traversal and selective rail openings. No architecture was scaled to old prototype dimensions. See `tools/STATUS.md` for current evidence.

## Hospital

The hospital houses **30 patients** and targets injury treatment **80% faster than the vanilla Medical Bed**. The authored interpretation is a **1.8× total healing rate**, which takes about **55.6% of the bed's treatment time** under equal treatment conditions. Native treatment replaces passive recovery on its active ticks. Chipped teeth and badwater contamination receive their own native treatment effects. The first integration uses six staff, 600 hp, 25,000 science, medicine/water/extract supplies and a ten-cell neighborhood effect worth up to +2 wellbeing. Native builds 63/66 passed patient care, staff/supply/power gates, neighborhood effects, access and saved continuity. The short native comparison measured 1.745439× bed recovery; it passed the fixture's ±0.08 tolerance around the 1.8× target, and is not evidence of an exact measured 1.8× rate. Economic balance remains a playtest task. See the [integration contract](civic-building-integration.md) for exact rates and construction costs.

Thirty is the shared patient capacity, not thirty patients per condition. Recovery does not create immunity to ongoing contamination. Do not substitute ordinary hunger or generic wellbeing changes for actual injury/teeth/contamination recovery. Inspect each native treatment blueprint and condition API before implementation. Patient slots can be in enclosed wards; the native model should not expose the interior.

## Grocery store

One stocked store offers several foods, including canned fish, general canned food and staples such as algae and corn rations. Use one native inventory and ordinary food consumption effects; hauling and belts deliver to that same inventory. The current `PackagedFood` placeholder is not automatically a canning recipe: decide its ingredients/container and identity explicitly before calling it canned food.

A stocked neighborhood receives an area wellbeing benefit through native `RangedEffectBuilding`/`ContinuousEffectBuilding`. The store's effect must be its own need, shared by copies of the store so overlapping stores cannot stack it without limit. The hospital uses a different need. Stocking requirements, range and replenishment rates are still proposals. Neither building produces a service-token item.

## Wellbeing, education and science

User direction: advanced machines should require a capable, well-supported population. Proposed implementation checks each worker's wellbeing and education at safe work boundaries. Show both the required and current values in the building's status; allow a qualified replacement. Education persists if wellbeing later falls. Exact thresholds are not enabled or balanced yet.

Keep food/water, hauling, care, basic power, entry-level research and training accessible so the colony can recover. A reactor must not immediately lose its cooling/safe-shutdown staff because a worker's wellbeing dipped; operating eligibility and mandatory safety operation are distinct. Do not introduce maintenance or general heat mechanics.

The **Nuclear Reactor costs 1,000,000 science** in the producing catalog. Proposed industrial research uses native `RecipeSpec.ProducedSciencePoints`, consuming useful existing materials with high hp/workforce demand. Scientific Projects can express persistent certification/prerequisites; research must not mint single-use license goods.

| Proposed facility | Science per working hour | hp demand | Workers | Status |
|---|---:|---:|---:|---|
| Materials Laboratory | 400 | 600 | 4 | Balance proposal |
| Applied Research Institute | 2,000 | 3,000 | 6 | Balance proposal |
| Advanced Science Center | 8,000 | 12,000 | 8 | Balance proposal |

At 16 productive hours/day, one proposed Advanced Science Center generates 128,000 science/day. One million science therefore takes about 7.81 operating days, or 3.91 with two centers, before shortages or other spending. Two centers already require 24,000 hp. These are arithmetic design targets, not measured gameplay rates; unlock costs, input recipes and worker eligibility must be tested together. Build the research ladder before presenting the million-point unlock as balanced progression.

## Aluminum and the nuclear power budget

Plan a finite early bauxite deposit and a harder permanent bauxite mine, followed by an alumina refinery and aluminum electrolysis. Draft power demands are 6,000 / 8,000 / 40,000 hp. A 40,000 hp smelter, two 12,000 hp science centers, 6,000 hp electrolysis and 10,000 hp cryogenics together demand **80,000 hp**, before mining, refining and transport. This gives the existing 75,000 hp reactor target meaningful industrial loads; it does not make nuclear a mandatory story key.

Keep the material graph connected: bauxite feeds alumina and specialist cement; alumina feeds aluminum, machining abrasives and filter media; aluminum feeds electrical equipment, alloys, advanced buildings, logistics and rocket airframes. These are planned destinations, excluded from the implemented-use count. Prefer existing Badwater for refinery effluent instead of inventing a one-use sludge item. Exact chemistry-inspired recipes remain gameplay abstractions to be balanced, not a heat simulation.

## Item rule and rocket exception

Every new ordinary industrial item requires **at least two distinct useful downstream uses**, preferably **three to five**. **Directly edible foods may have eating as their single use. Rocket-specific components and final-goal launch payloads may also have one use.** General hydrogen/oxygen, aluminum, electronics, fuels and research inputs do not become exempt merely because rockets also use them. Ingredient oils, juvenile fish and fertilizers are not directly edible food exceptions.

Two alternate recipes for the same output are one destination. Storage, hauling, disposal and cycling a good into itself are not additional useful destinations. A rocket part with no implemented launch consumer still fails. Credentials become persistent unlocks, not inventory products. Existing placeholders require an explicit development-save migration before removal.

Run `tools/audit_item_uses.mjs` to regenerate [the current audit](item-use-audit.md), or pass `--release-check` to fail a release with missing uses. The audit reads active Iron Teeth recipe assignments and authored construction/consumption. It does not count proposed services and does not establish resource bootstrap, infinite extraction, balance or in-game functionality. Fix the source graph, not the report.

## Advanced construction

New materials also build useful structural blocks, stronger overhangs, longer bridges and modular scaffolds. Concrete serves blocks, reinforced overhangs, bridge piers and machine foundations. High-grade steel serves long trusses, heavy cantilevers and scaffold frames. Aluminum serves light bridge decks, modular scaffolding and elevated logistics frames alongside electrical and rocket uses. Sandstone masonry, limestone flux, aggregate ballast and cement foundations give early processing materials more than one useful destination too.

Author these as building costs directly unless an intermediate manufactured part has its own multiple uses. Do not invent a one-use bridge-kit good. Use the installed native block occupation/stackability and overhang/support rules; determine real spans and clearances through placement tests before publishing values. Keep space for paths, gears and tubeways under tall structures, and preserve native-compatible vertical stacking without an arbitrary layer cap. Planned construction uses do not count toward the implemented item-use audit yet.

## Oil, polymers and radiation protection

User direction: oil makes **polymer resin and plastic**, used to craft **hazmat suits and other items**. Replace the vague generic Polymer draft with distinct `PolymerResin` and `Plastic` goods at the producing source. Planned paths are crude oil to resin, resin to plastic, and plastic plus other general materials to protective equipment. Oil also feeds lubricants and generation; resin also feeds composites, coatings and filter media; plastic also feeds pipe liners, packaging, electrical insulation and medical equipment. Recipes and quantities are not implemented yet. Keep the old development ID explicit until a deliberate save migration is authored; do not silently rename or substitute inventory goods.

Reusable hazmat suits serve reactor work, waste handling, contamination treatment and cleanup. Specify equipping/return behavior and actual exposure protection; a visual outfit alone is not protection. No durability, repair or routine maintenance mechanic is introduced.

Add purpose-built shielded pipe pieces for explicitly radioactive **liquids** using Timber Pipes' actual port/connection API. Solid radioactive waste remains in the solid inventory/conveyor system. Ordinary Badwater is not automatically a radioactive fluid. Shielded warehouses and appropriate tanks block the stored contents' radiation while intact, with the existing non-deletion/demolition-lock requirement retained until waste is transferred or refined. These are new behaviors to implement and test, not properties already provided by Timber Pipes or Expanded Storage. Shielding and suits never replace a reactor's constant coolant supply and safe shutdown requirements.

## Advanced warehouses

User direction: advanced warehouses can store **multiple types of goods**. Expose selected goods and per-item stock limits with one shared capacity. Native haulers and Conveyor Belts must access the same inventory, so one warehouse can supply several factory inputs or buffer several outputs. Reject invalid capacity settings explicitly instead of adjusting limits behind the player's back. Capacity, costs and model dimensions remain unbalanced.

Include a shielded variant for radioactive goods. It retains the multi-item inventory and blocks radiation from stored contents. Any remaining nuclear waste prevents demolition, even when most of the warehouse contains ordinary goods. Expanded Storage supplies foundation/reference profiles; its existing buildings must not be described as already providing these new controls or shielding behavior.

### Native implementation and controls

The installed 1.1.2.8 `Timberborn.InventorySystem` already exposes `InventoryInitializer.AddAllowedGoods`, `HasPublicInput`, `HasPublicOutput`, a shared `Inventory.Capacity`, and an `IGoodDisallower.AllowedAmount(goodId)` extension. `Inventory.UnreservedCapacity` accounts for both the good's allowance and the inventory's total stock plus incoming reservations. The stockpile's `SingleGoodAllower` deliberately prevents a second type while other goods remain; do not attach it to the advanced warehouse. Evidence: `outputs/civic-native-api/inventory/Timberborn.InventorySystem.decompiled.cs`.

Use one native inventory with a dedicated multi-good limit component, persistent player selections and a TimberUi panel. Register public input/output through the native initializer so hauling and belts see the same quantities and reservations. Limits are per-good maxima, not reserved shelves: their sum may exceed shared capacity, while the shared inventory still prevents overfilling. Label both values clearly. Reject negative limits, unknown/non-solid goods and settings that conflict with current stock or committed incoming deliveries. Do not silently resize, redistribute or delete stock.

Provide an explicit drain action for a selected good: stop new intake, keep its existing stock available for collection, and show the remaining amount. Finish removing that selection only when stock and reservations are empty. Nuclear waste remains protected throughout draining, transfer, building pause, copying settings and save/reload. Capacity reductions and copied settings must use the same validation as direct edits.

Acceptance cases: two food types; mixed construction materials; full shared capacity while one good remains below its limit; a full per-good limit with free total capacity; simultaneous belt and hauler deliveries; incoming reservations during a limit edit; drain to another warehouse; unknown goods rejected; restart with mixed stock; mixed ordinary/radioactive stock preventing demolition; radiation shielding restored after reload. Confirm both belt intake and extraction against the installed 11.4.0 API before claiming compatibility. These controls are specified, not implemented.
