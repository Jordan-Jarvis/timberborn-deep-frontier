# Transport adapter boundary

The foundation packages declared in Deep Frontier's manifest are required. Use their installed 1.1 contracts and the official game inventories/mechanical system. Missing required dependencies must fail explicitly. A reference-model conveyor inside a machine can be animated artwork; this does not create an item-transfer network.

## Verified contracts

| Foundation | Installed package | Contract observed | Deep Frontier use |
|---|---:|---|---|
| Timber Pipes | 3801726769, `version-1.1`, 11.4.0 | `BuildingPipeTargetPortsSpec.Ports` for a receiving building; `BuildingPipeSpec`/`TransportPipeSpec` for pipe entities | Explicit water, oil, badwater and waste connections to native inventories |
| Conveyor Belts v2 | 3815376360, `version-1.1`, 11.4.0 | `BuildingBeltTarget` on BuildingSpec, native `Inventories`, `InventoryConnection`, `BeltGoodService` | Test withdrawals from enabled output inventories and accepted deliveries to input inventories; mechanical transputs alone are not item ports |
| Powered Tubeway | 3543155128, `version-1.1` | `TransputProviderSpec` plus `MechanicalNodeSpec` | Power transmission through supported Tubeways; do not infer goods transport from power specs |
| Power Lines | 3766893705, `version-1.1` | Mechanical network connector blueprints | Existing `MechanicalNodeSpec` values are the power contract |
| Pump to Tank | 3681283725, `Version-1.1` | Tank transfer content | Use it for water/badwater logistics; Deep Frontier does not reimplement tank transfer |

The installed pipe package decorates ordinary BuildingSpec entities with BuildingPipeTarget. DefaultBuildingConnectionProvider uses explicit BuildingPipeTargetPortsSpec when authored. DefaultBuildingPipeConnection transfers registered Liquid goods into accepting native inventories and withdraws unreserved takeable stock; construction inventories are excluded. Existing Water recipe inputs already provide the machine side. Native aquaculture acceptance 76 verified real tank-to-factory transfer through authored faces; a second water inventory is unnecessary.

## Current slice

`DeepDrill.IronTeeth` declares two mechanical transputs and consumes 1,000 hp. `DeepProcessor.IronTeeth` declares eight mechanical transputs and consumes 500 hp. Those are power connections. The earlier claim that they were verified item endpoints was incorrect.

Installed Conveyor Belts v2 11.4.0 decorates BuildingSpec with `BuildingBeltTarget`. It supplies an `InventoryConnection` when the approached entity has native `Inventories`, is not itself hosting a belt, and the approach meets its lane conditions. `BeltGoodService.TryTake` withdraws one non-liquid good from unreserved stock in an enabled output inventory; `TryGive` requires an enabled input inventory accepting that good with unreserved capacity. Ignored inventory rules also apply. Evidence: `outputs/conveyor-api-11.4.0/ConveyorBelt.cs`. Mixer build 81 verified physical Aggregate/Cement delivery and Concrete withdrawal with full buffers and saved queues; other factory layouts and rotations remain separate coverage.

The generic belt withdrawal checks IsOutput rather than PublicOutput. A grocery's takeable food is therefore visible to generic belts even though ordinary factory haulers cannot export it. `GroceryBeltIntake` uses the public IBeltConnectionProvider priority contract to return an input-only ISimLink/ISimTarget, with no ISimSource. Accepted food enters the grocery's existing native inventory and respects its real reservations and per-good capacity. Native build 73 passed physical incoming/outgoing lanes, wrong-good rejection, the 100-per-food shelf limit, complete power interruption and resumed delivery, exact stock conservation and prevention of outbound withdrawal. Its saved queue holds ten real Corn Rations, with seven more at the donor and 100 on the shop shelf.

Fresh-process reload 75 passed exact saved belt goods/positions, resumed delivery of all seventeen donor/queued items, native consumption accounting and protection against outbound withdrawal. The final saved corn stock is 74: initial total 117 minus the explicit 30-unit test withdrawal minus thirteen actual shopper meals. Both belt lanes and donor/receiver warehouses are empty. Preserved native save: `outputs/grocery-belt-continuity-build75.timber`, SHA256 `fc51807bc76dd708818b0f653c4ed5b0ec4ee7b724f883adb28ba3e59519c603`. Run 74 had incorrectly waited for a full shelf despite finite supply and concurrent eating; 75 opens space for the entire saved supply and verifies its exact arrival.

The recipes currently consume `Water` as an ordinary inventory good. That is the authored recipe contract, not a missing-pipe substitution or proof that the slice is playable. Verify inventory delivery, production and actual hp behavior in game.

Aquaculture intake faces are authored in `tools/aquaculture_pipe_ports.json`: Fishery rear tank cell (5,9,0), facing Up; Hatchery pump canopy cell (6,2,1) since the 7×7 compact footprint (2026-10-26; (7,2,1) before), facing Right. Both are OpenIn and use the dependency's BuildingPipeTargetPortsSpec. Hatchery coordinates include its BaseZ=1. They are occupied machinery cells away from doors and walking rails. Their native Water recipe inventory remains authoritative. Canonical generation changed exactly these two building blueprints.

Native build 76 passed physical tank/pump/pipe/valve delivery to both buildings, wrong-face and Badwater rejection, the 90/60-unit recipe limits, valve interruption/reopening and water conservation. Visible reservoirs matched real inventory stock, and paused production did not circulate. The saved lines each retain 290 Water-equivalent units across factory, tank and pipes; each of the six pipe cells holds 1 m³. Native save: `outputs/aquaculture-pipes-build76.timber`, SHA256 `d6ed16c1159f84f191193191cb0a36fdd99edcfe7ae2396a0c3173d79d56b64b`.

Fresh-process continuation 76 also passed exact inventories, signed tank fractions, every saved pipe volume/good and valve settings. Native workers completed two Fishery batches and one Hatchery batch using pipe-fed stock; real recipe consumption was three/two Water, with visible flow and advancing Fishery wheel. The first Fishery batch resumed prepaid progress, so the second batch was required to prove a new Water debit. Final buffers refilled to 90/60 and total water reconciled to 267/268 after the explicit fixture withdrawals and actual recipe consumption. Native continuity save: `outputs/aquaculture-pipe-continuity-build76.timber`, SHA256 `b9f7be74f9ff2faa5c0c0c875be5a1d4403db327cb165f725039ee34e50e678f`. This verifies these authored orientations; broader factory belts, FishOil transport and rotation coverage remain separate work.

## Adapter sequence

The reference mixer passed native build 81 main and fresh-process transport tests. Its water inlet is local (7,5,0), facing Right, OpenIn. Two ordinary conveyor lanes approach the rear frame with Aggregate/Cement and another withdraws Concrete. Actual transfer respected the native 12/4/8 ingredient limits, rejected wrong goods/faces, stopped at lost belt power or a closed valve, and supplied two newly debited production batches per run. Every new Concrete unit reached the output warehouse: 20 at the first checkpoint, 28 after reload. Native inventories and all six belt queues/positions, three pipe volumes, valve state and tank fraction restored exactly.

Preserved evidence: `outputs/factory-transport-build81.timber` (SHA256 `eccb0556458ebda8ca07420b081bcb10936311fba02e07aa4542a6e7410e849c`) and `outputs/factory-transport-continuity-build81.timber` (SHA256 `b91f12951c44eb6e1c31116eb17ce0a7f815a5bd6e1df5a5f1a278a611986a86`). The reload's disposable workers were initially starving; the native developer Boost on one assigned worker allowed production to proceed. This verifies transfer/consumption, not economic throughput. Subsequent fixture code prepares only Hunger/Thirst/Sleep once before assignment.

Power Lines 11.1.1 provides `PowerLineComponent` on every native MechanicalNode and public `PowerLineConnectionService.Connect/DisconnectConnection`. The source authors the mixer's cable attachment on its existing rear-right deck beam at local grid (7.84,5.84,1.80). Connection counts and ranges retain the dependency's settings. Native main 82 passed one isolated 350 hp cable supply, graph separation/reconnection, actual 250 + 12 + 50 = 312 hp demand and two transport-fed production batches with conservation. Self/duplicate connections were rejected. The native save retains exactly the mixer/remote-source endpoint pair. Fresh-process 83 restored it and every transport queue, repeated interruption/reconnection and delivered two more batches. The fixture explicitly withdrew eight previously received Concrete after checking saved stock, leaving room in the 30-unit receiver; final stock is 28. Continuity archive: `outputs/factory-power-lines-continuity-build83.timber`, SHA256 `1a5af810d379ca817cf58662a432547f5b88913886fe95507166bdcc941e0bb7`. PowerLines.dll and its authoring dependency ModSettings.Common.dll remain external to the mod package.

1. Test Conveyor Belts v2 against native inventories, beginning with grocery intake and factory input/output. Choose hauling or conveyor-only access explicitly per building; do not substitute hauling when a required transport contract fails.
2. Author explicit Timber Pipes faces on the already working native Water consumers, then test against a real tank and extraction/transport pipe network.
3. Check power, capacity, wrong goods, interruption and save/reload with actual goods retained on the networks.
4. Add Power Lines presets for the 1,000 hp drill and 500 hp processor, then verify demand/output accounting in a save.
5. Add custom vein targeting and runtime depletion after the data-only `DeepOreSource` stockpile path is accepted in-game.

The quarry's bucket, tipping receiver, internal slat conveyor and screen are visual process parts. External belts must exchange actual goods through the dependency's inventory contract. Keep those two responsibilities distinct, and fail visibly when required integration data is invalid.

## Reactor coolant by pipe (2026-10-21)

User decision: the Nuclear Reactor is pipe-fed. Coolant is the existing `ReactorCoolantWater` Liquid good, made by the Water Treatment Plant and consumed by the reactor's `NuclearWaste` recipe (6 per cycle). `tools/coolant_pipe_ports.json` is the source for both ports, which `create_frontier_expansion_content.mjs` applies:

- Nuclear Reactor: local (0,1,0), `Left`, `OpenIn`. The pipe delivers into the native manufactory inventory.
- Water Treatment Plant: local (2,1,0), `Right`, `OpenOut`. The pipe withdraws takeable coolant.

These sit on the current 3×3×3 placeholder footprints. The 20×15 reactor study (`tools/asset-pipeline/lategame_NuclearReactor.py`) records its intended inlet as `PIPE_INLET`, a flanged socket at the front-left intake sluice. The port moves there when that model's footprint is integrated. Its canals, basins and water race are visual native-water surfaces; they do not draw on world water.

Verification so far: regeneration changed only the two blueprints and the reactor description, and `validate_vertical_slice_content.mjs` passes. Native delivery, the OpenOut withdrawal from the treatment plant, wrong-good rejection and save/reload have not been run in game.

## Cryogenic tank farm by pipe (2026-10-22)

The Cryogenic Tank Farm is the integration's LargeTank-derived Liquid Stockpile: 2,000 capacity and 6,500 hp (power rule, docs/progression.md). The player selects Liquid Hydrogen or Liquid Oxygen with the native stockpile selection. `tools/cryogenic_content.mjs` adds `CryogenicTankSpec` and the pipe sockets; the runtime is in `src/DeepFrontier/Scripts/Cryogenics/`.

**Source-confirmed contracts** (installed Timber Pipes 11.4.0, DLL hash equal to the audit record; game 1.1.2.8):
- **Every liquid stockpile is an in-network tank.** `TankPipe` (`[AddTemplateModule2(typeof(Stockpile))]`) makes a Liquid stockpile a `BuildingPipe` plus `PipeTank`. `BuildingPipe.ResolveSpec` prefers an explicit `BuildingPipeSpec` with ports; otherwise it opens every exposed face.
- **`BuildingPipeTargetPortsSpec` is ignored here.** `DefaultBuildingConnectionProvider` returns null when `isAlreadyPipe`, so the farm's sockets are authored as `BuildingPipeSpec.Ports`.
- **One port can fill and draw.** `PipePortState` is a flag set (`Closed` 0, `OpenOut` 1, `OpenIn` 2, `Open` 3), and edge flow uses each port's `CanOutflow`/`CanInflow`. Separate In and Out ports for one cell and face are rejected ("Duplicate port definition").
- **Hydrogen and oxygen networks stay separate.** Graphs flood-fill transport pipes only. A tank between two networks keeps them as two graphs; each lists the tank in its flow.
- **A mixed network fails visibly.** `PipeFluidSimulator.Simulate` contaminates any graph whose fluid conflicts with a connected tank (`TankConflictsWithPipe`: the stored good differs, or the tank does not take the fluid). That graph stops moving fluid and shows Timber Pipes' "Contaminated pipes" status and alert until flushed. A Closed port still connects, so it would still contaminate.
- **The gap: an empty farm refuses a foreign fluid silently.** It takes every liquid (`Inventory.Takes`), but the native selection gives it no capacity. The tank's own "Wrong fuel network" status covers this case and any contaminated connected graph.

**Socket decision.** The study's sockets are cell (9,0,0) for LH2 and (10,0,0) for LOX, both facing Down. Both are `Open`. Port states are static per template, while the farm's good is a runtime selection, so neither socket can be closed for "the other good". A wrong network on either socket fails visibly as described above. Closing one socket statically would need one template per good.

**Power gating.** Native `StockpileInventoryInitializer` gives the inventory one `IGoodDisallower`, the `SingleGoodAllower`. For templates with `CryogenicTankSpec`, a Harmony prefix on `InventoryInitializer.Initialize` substitutes `CryogenicIntakeGate`. The gate keeps the native selection, refuses goods outside `Goods`, and while unpowered allows only the stock on hand. `UnreservedCapacity` is then 0, which blocks haulers, `PipeTank` filling and valves. No stock becomes unwanted, and withdrawal continues. The `AddGoodDisallower` setter is not patched because it is 7 bytes of IL and Mono may inline it.

"Powered" means `MechanicalBuilding.ActiveAndPowered`, so pause and automation Off also close intake. After `BufferHours` (12) the tank vents `VentPerHourOnPowerLoss` (4 units/h) of unreserved stock: 96 per day, 4.8% of a full farm per day, about four liquefaction plant-hours per outage hour.

**Source-derived, unverified:** while closed, the pipe solver treats the tank as full (capacity equals stock). It may push stock into connected pipes up to the tank's top layer, and Timber Pipes' tank panel shows it as full.

**Verification:** compile and scratch generation only. In-game acceptance is pending. Run it in a marked fixture after `TANK_FARM.status` is `ready`, with every generator on the tank's graph enumerated so that switching power off really cuts it:

1. **Setup.** The log contains "Cryogenic intake gate patch applied". The farm's `BuildingPipe.Ports` start with the two transformed study sockets, followed by the generated flat-face ports (all `Open`; see the next section), and capacity is 2,000.
2. **Selection.** Selecting Water gives `UnreservedCapacity` 0 and the "Stores only one of" status. Selecting Liquid Hydrogen gives capacity 2,000 minus stock.
3. **Powered intake.** Liquid hydrogen from a pipe network on socket (9,0,0), and from haulers, raises the stock.
4. **Power loss.** Within one tick, `Accepting` is false and capacity is 0, and no stock arrives for two hours. The native No Power status and the holding status show, with no Unwanted Stock status. A valve can still draw to the Launch Pad.
5. **Buffer.** The stock does not change for 12 hours, apart from withdrawals.
6. **Venting.** Each following hour removes 4 units (from negative `InventoryStockChanged` events), with the "Venting cryogenic fuel" priority status and alert. Exactly one notification is posted per outage.
7. **Restore.** When power returns, intake reopens and the clock resets. A later outage notifies again.
8. **Pause and automation Off.** Each repeats steps 4–6.
9. **Save and reload.** Saved mid-vent, a fresh-process reload restores `UnpoweredHours`, `VentRemainder` and `VentedThisOutage` exactly, posts no second notification, and keeps venting at 4 units per hour.
10. **Separate networks.**
   - A stocked hydrogen farm with an oxygen network on socket (10,0,0): that graph is `Contaminated` (cause Liquid Hydrogen and Liquid Oxygen) and moves nothing. The hydrogen graph keeps working, and the farm shows "Wrong fuel network".
   - An empty hydrogen farm with an oxygen network: no Liquid Oxygen enters, and "Wrong fuel network" shows.
11. **Conservation while closed.** Tank stock plus five times the pipe volumes stays constant, apart from venting and withdrawals.

## Shafts and pipes on every flat exterior face (2026-10-23)

User rules:
- "The Bathhouse and basically any and all buildings need to accept power and pipes on any flat surface of the building."
- "The reactor has curved edges on it; we don't want to be able to connect to the curved edges, just the flat ones."
- "We don't connect to roof tiles unless it is platformable roof."
- "From the bottom counts as flat."

`tools/connection_content.mjs` applies these to every generated Deep Frontier building after all blueprints exist (called from `create_vertical_slice_content.mjs`). `tools/asset-pipeline/measure_connection_faces.py` writes the face records in `outputs/connection-faces/` from the exported finished models.

**Source-confirmed contracts** (game 1.1.2.8, `outputs/navigation-api-1.1.2.8/Timberborn.MechanicalSystem.decompiled.cs`; Timber Pipes 11.4.0, `outputs/modding-api-audit-1.1/TimberPipes.cs`):
- **Power.** `TransputProviderSpec.Transputs` lists `{Coordinates, Directions, ReverseRotation}`. `MechanicalNode.InitializeTransputs` makes one `Transput` per direction, and `TransputMap` stores them per world cell. `MechanicalGraphManager.AddNode` asks `TransputMap.GetFacingTransput` for each one. `Transput.Faces` joins two transputs whose targets are each other's cells and whose directions are opposite. `Up`/`Down` are grid Y and `Top`/`Bottom` are vertical.
  - A vanilla `PowerShaft` (Left/Right/Up/Down + Bottom, `MatterBelow GroundOrStackable`) meets a horizontal or Top face. A shaft on a roof therefore needs a stackable roof block (vanilla BotPartFactory: Top transputs on `Stackable BlockObject` roof blocks).
  - A `VerticalPowerShaft` (+ Top) meets a Bottom face from below.
- **Pipes.** `BuildingPipeTargetPortsSpec.Ports` lists `{Coordinates, Directions, State}`: the building cell and the outward face a pipe meets. `Directions3D` covers all six faces, including Bottom.
  - `DefaultBuildingConnectionProvider` transforms the list once. `BuildingPipeTargetIo.FaceAllowed` scans it linearly when a pipe end looks for a building.
  - Without the spec every face is accepted (`anyFace`). Many ports are supported.
  - **Targets.** `BuildingPipeTarget` is added to every BuildingSpec entity. A building exchanges the Liquid goods its enabled inventories register: InputGoods (Givable) when a pipe gives, OutputGoods or takeable stock when it takes (`ValvePipeIo.LiquidIdsForConnection`). A GoodConsumingBuilding supply inventory (the Bathhouse's Water) qualifies; no Manufactory or Stockpile is needed.
  - **Only valves reach buildings.** `ExtractionPipe.FindInletTarget`/`FindOutletTarget` -> `ValvePipeService.FindConnection`. The valves are `HorizontalPipeValve` (local Down OpenIn from the network, Up OpenOut into the building) and `ElbowPipeValve` (Down/Right). Plain transport pipes join only pipes and tanks (`PipeRegistry.portOwners`).
  - No valve is vertical, so building target ports are horizontal faces only. A new valve's Inlet is off (`ExtractionPipe.InletEnabled`).
  - Build 146: the user ran plain HorizontalPipes onto the Bathhouse ports and nothing flowed. A valve with its outlet toward the building, Inlet on, is the supported connection. Every piped building's description now says so (`connection_content.mjs` `PIPE_PHRASES`).
  - A Liquid stockpile uses `BuildingPipeSpec.Ports` instead (see the tank farm above).

**Face rule.** A face is a connection face when all of these hold:
1. **It is flat.** Measured on the exported model, 8 x 8 rays per face, with the covering surface being the nearest front-facing static surface, window glazing included, within 0.35 behind the cell plane (or 0.02 proud of it):
   - **No curve or slope, even partly.** Every covering normal lies within 5 degrees of the face axis and 1 degree of the covering mean. Domes, cylinders, tanks, rounded edges, vaults, pitched roofs, faceted curves and bevels anywhere on the face disqualify it.
   - **One wall plane** (depths within 0.05) covers at least 60% of the face. Parallel relief elsewhere, such as trim or a plinth step, is allowed. The plane may be the glazing or the wall it is set in, so windows proud of or recessed from a flat wall do not break it.
   - **Glass is a surface** (2026-10-26, the Greenhouse): flat glazing (`WindowsAtlas`, `DFIndustrial09`) qualifies like a wall, and curved glass fails the curve test. Lamp glass (`DFIndustrial08`, faceted wall lanterns standing off the wall) never makes a wall curved.
   - **No animated part in front.**
   - Back faces never cover a face. Rails, liquids and native props never count as walls.
   - The plane band is 0.05 rather than the requested 0.02 because timber frames stand 0.03-0.04 proud of their infill on the walls with in-game-tested sockets.
2. **Its cell is occupied.**
3. **Its neighbour is exterior.** The neighbour lies outside the Size, or is an open cell that a flood fill reaches from outside. Open means the game's block validator would accept the shaft there: the cell's occupation shares no flag with the vanilla PowerShaft's (Bottom, Path, Middle), such as None, a deck's Top/Corners, or a porch's Floor (the Fish Hatchery's front walk). Under a Bottom face the VerticalPowerShaft's flags must fit instead.
4. **Its neighbour is not an access cell.** Access cells are the Entrance, every door's path cell, walkway openings, unoccupied navmesh edge ends, and native water/sludge in- and outlets. The radiation export's MAP_EDGE side is skipped.
5. **Roof (Top) faces only on platformable roofs.** The block must already be Stackable when the connection step runs: roof terraces and decks of the families, and every flat, clear roof cell of `tools/roof_decks.json` (generated by `tools/roof_deck_content.mjs`, a design step that runs just before the connection step). The connection step never changes a block.

Undersides: every occupied ground-layer cell standing on ground or a platform also gets a Bottom shaft face (the vanilla convention), except on buildings with BaseZ > 0, whose lowest layer stands below their placement level (the Fish Hatchery's pens in the water). Measured-flat undersides over open cells carry Bottom shaft faces. Pipe target ports are horizontal only; the tank farm's tank ports keep all six faces because transport pipes meet a tank directly.

**Ports.** A building gets ports when its recipes, consumed goods, pantry or restaurant stock include a Liquid good. The state follows what it does with them: `OpenIn` when it only takes them, `OpenOut` when it only gives them, `Open` when it does both (and on a tank). Authored sockets stay first and unchanged: the study sockets, reactor/treatment coolant, the aquaculture intakes and the mixer inlet.

**Native cost (source-derived, not profiled in game).**
- **Power.** One of each powered template has 5,475 transputs, down from 6,655; the largest is the reactor at 373.
  - Building placement: `AddNode` and `TransputMap` work is linear in the transput count.
  - Connector stubs: `MechanicalConnectorActivator` instantiates one connector GameObject per horizontal or Top transput on buildings with `MechanicalConnectorTargetSpec`. That is 2,453 for one of each, down from 3,644; the most on one building is 250 (RocketAssemblyHangar).
  - Shaft placement: each `TransputAdded` anywhere scans every subscribed building's connectable list.
  - Power ticks: they run per graph node, not per transput, so tick cost does not change.
- **Pipes.** One of each liquid template has 1,968 horizontal port faces, up from 11; the largest is the Hospital at 168.
  - Building initialisation: the list is transformed once.
  - Connection lookup: `FaceAllowed` scans at most 168 entries. That runs when a valve or pipe end looks for a building; attached connections are cached (`ExtractionPipe.CachedTarget`). A valve that faces a building on a face without a port rescans each tick.
  - Tank farm: `CryogenicTank` checks `IsConnected` on each of its ports per tick.

**Verification:** scratch generation and validators only (`validate_connection_faces.mjs`, `validate_connection_exports.py`, which includes curved test cases on the reactor, the tank farm's LOX tank and the oil plant's vault). `LategameAcceptance` places a PowerShaft on a Top face where a platformable roof exists, and tests one generated ground-level pipe port per building. Not run in game.
