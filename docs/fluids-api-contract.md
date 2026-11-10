# Moddable Fluids 0.1 contract

Implemented 2026-11-09 as item 3 of the [Moddable Fluids plan](fluids-api-plan.md), with item 4's persistent identities. The contract is experimental: its major version is 0, so any minor release may change it. It has passed the .NET 8 harness and the installed-Mono probes, including a Mono process without the API. In game, the registry, both consumer routes and the provider scene lifecycle passed the worker fixture on 2026-11-09, under the pre-rename names. Behaviour policies and tide registration are not part of 0.1. Source types (0.1.1), the world service (0.1.2), and legacy import and column rules (0.1.3) were added in patch releases; shared rendering is a runtime service with no API surface yet. Where the plan calls a definition field a behaviour or appearance, that is only data until the matching capability exists.

## Rename from FluidsApi

On 2026-11-09 the user named the foundation **Moddable Fluids**. Nothing was released under the working name. The rename has no aliases and no compatibility shims: old names are simply not recognised.

| Working name (before 2026-11-09) | Moddable Fluids |
| --- | --- |
| Mod ID and manifest `FluidsApi` | `ModdableFluids` |
| Assemblies `FluidsApi`, `FluidsApi.TransportPrototype`, `.GamePrototype`, `.RuntimePrototype` | `ModdableFluids`, `ModdableFluids.TransportPrototype`, `.GamePrototype`, `.RuntimePrototype` |
| Namespaces `FluidsApi`, `FluidsApi.*.Prototype` | `ModdableFluids`, `ModdableFluids.*.Prototype` |
| Entry and host types `FluidsApiEntry`, `FluidsApiHost` | `ModdableFluidsEntry`, `ModdableFluidsHost` |
| Capabilities `FluidsApi.<Name>` | `ModdableFluids.<Name>` |
| Harmony owner `FluidsApi.Prototype.NativeTransport` | `ModdableFluids.Prototype.NativeTransport` |
| Flags `-fluidsApiWorkerAcceptance`, `-fluidsApiReport` | `-moddableFluidsWorkerAcceptance`, `-moddableFluidsReport` |
| Fixture mods `FluidsApiSyntheticReflection`, `FluidsApiSyntheticCompiled` (and their fluid IDs) | `ModdableFluidsSyntheticReflection`, `ModdableFluidsSyntheticCompiled` |
| Source `src/FluidsApi`; `tools/build_fluids_api.ps1`, `verify_fluids_api_package.ps1`, `unity/FluidsApiBatchBuild.cs` | `src/ModdableFluids`; `tools/build_moddable_fluids.ps1`, `verify_moddable_fluids_package.ps1`, `unity/ModdableFluidsBatchBuild.cs` |
| Worker fixture map and settlement `Fluids API Worker Fixture/Acceptance` | `Moddable Fluids Worker Fixture/Acceptance`; regenerate it with `tools/create_fluid_acceptance_map.py` |

Unchanged:

- the documentation file names `docs/fluids-api-*.md`, so existing links keep working;
- the evidence folder `outputs/fluids-api-prototype`;
- the generic tool names (`test_fluid_transport.ps1`, `run_fluid_native_mono.py`, `start_fluid_worker_acceptance.ps1`);
- the API version 0.1.0 and the save schema 1.

No save holds fluid state yet, so there is nothing to migrate.

The pre-rename development package must be removed from an installation. Its old assembly name means the duplicate-copy check would not catch it, and its old flag means it would never activate. `tools/build_moddable_fluids.ps1 -RemoveLegacyPackage` checks the manifest of each pre-rename package, then deletes `Mods/FluidsApi`, the two old fixture folders, their staged copies in the authoring project and their enablement keys. The build refuses to run while any of them remains. The launcher refuses to start while `Mods/FluidsApi` exists.

## Assemblies

| Assembly | Contents | References |
| --- | --- | --- |
| `ModdableFluids` | IDs, definitions, registry and handles, providers, scene lifecycle, discovery entry, save schema | `netstandard` only, so its types enumerate safely in any installation |
| `ModdableFluids.TransportPrototype` | Transport, native adapter, world persistence (`FluidWorldPersistence`) | `ModdableFluids` |
| `ModdableFluids.GamePrototype` | Native scheduler hooks and their startup contract | Harmony, `Timberborn.Multithreading` |
| `ModdableFluids.RuntimePrototype` | Flag-gated scene owner and worker fixture | Game assemblies |

The three prototype assemblies keep their experimental `*.Prototype` namespaces. From 0.1.4 the package attaches to a game scene when another mod registered a fluid besides water and badwater; with none it binds nothing and native water stays untouched (see [Ordinary play](#ordinary-play-and-exception-saves-014)).

## Identity

- **ID format.** A fluid ID is the owning mod's manifest ID, a dot, and a local name: `DeepFrontier.RadioactiveWater`, `eMka.ModSettings.Coffee`.
  - Mod IDs are dot-separated segments of letters, digits, `_` and `-`.
  - Local names start with an ASCII letter, then use letters, digits or `_`.
  - The last dot separates the two parts.
- **No normalization.** IDs are case-sensitive and kept exactly as written. They are never trimmed or aliased; invalid text is rejected.
- **Built-ins.** The game's fluids are `Timberborn.Water` (slot 0) and `Timberborn.Badwater` (slot 1). No mod may use the `Timberborn` owner.
- **Ownership.** A provider can register only inside its own `OwnerModId` namespace. Two registrations of one ID are an error that names both providers. A matching display name never merges two fluids.
- **Handles.** Handles are built-ins first, then ordinal ID order. They depend on the registry's content, not on registration order. A handle from a registry with different content is rejected, and handles are never saved.
- **Fingerprint.** `FluidRegistry.Fingerprint` is the SHA-256 of every ID, owner and native role, in handle order.

## Registration and load order

Register providers from an `IModStarter.StartMod`. The runtime freezes the registry once, when the first game scene is configured. After that, registering throws an error that points back to `StartMod`.

The freeze runs each provider's `Register` in ordinal `ProviderId` order, then validates everything together. Every problem is reported in one `FluidRegistryException` that names the provider, the mod and the fluid. A failed freeze leaves the host faulted with that report.

Load order cannot break registration. Timberborn loads every enabled mod's assemblies before any `StartMod` runs (`ModCodeStarter`), and the process-wide host is created on first use. Consumers should still list `ModdableFluids` in `RequiredMods` (compiled route) or `OptionalMods` (reflection route), so the native sorter places the API first by default. A player can move mods by hand-set priority; registration does not depend on the API loading first.

## Compiled providers

```csharp
public sealed class CoffeeProvider : IFluidProvider, IFluidSceneProvider, IFluidStateProvider {
  public string ProviderId => "MoreFluids.Drinks";
  public string OwnerModId => "MoreFluids";
  public string MinimumApiVersion => "0.1.0";
  public IReadOnlyCollection<string> RequiredCapabilities { get; } = new[] { "ModdableFluids.Registry.Definitions" };
  public void Register(FluidRegistration r) {
    r.AddFluid("Coffee", "MoreFluids.Coffee.DisplayName", .3f, .2f, .1f, .9f);
    r.AddMetadata("Coffee", "MoreFluids.Caffeine", "2");
  }
  public void Activate(FluidScene scene) { /* scene.Registry.GetHandle("MoreFluids.Coffee") */ }
  public void Unload(FluidScene scene) { }
  public int StateSchemaVersion => 1;
  public string SaveState(FluidScene scene) => "";
  public void LoadState(FluidScene scene, bool hasState, int schemaVersion, string state) { }
}
// IModStarter.StartMod: ModdableFluidsEntry.RegisterProvider(new CoffeeProvider());
```

Optional behaviour uses separate interfaces (`IFluidSceneProvider`, `IFluidStateProvider`). Later stages will add new optional interfaces rather than change `IFluidProvider`.

## Reflection providers

A consumer with no compiled reference:

1. Finds exactly one loaded assembly named `ModdableFluids` in `AppDomain.CurrentDomain.GetAssemblies()`. If there is none, the API is absent. If there are several, it stops with an error.
2. Gets the type `ModdableFluids.ModdableFluidsEntry`.
3. Reads the static `ApiVersion` (string) and `Capabilities` (`IReadOnlyList<string>`).
4. Calls `RegisterReflectedProvider(object)` with a plain object.

The API binds the object's members by name and exact signature:

| Member | Required | Signature |
| --- | --- | --- |
| `ProviderId`, `OwnerModId`, `MinimumApiVersion` | yes | `string` properties |
| `RequiredCapabilities` | yes | `string[]` property (empty for none) |
| `Register` | yes | `void Register(object registration)` |
| `Activate` and `Unload` | together or neither | `void Activate(object scene)`, `void Unload(object scene)` |
| `StateSchemaVersion`, `SaveState`, `LoadState` | all three or none | `int` property, `string SaveState(object scene)`, `void LoadState(object scene, bool hasState, int schemaVersion, string state)` |

The context objects use primitive methods only: `AddFluid(string localName, string displayNameLocKey, float r, float g, float b, float a)`, `AddMetadata(string localName, string key, string value)` and the `Serial` property. Binding rejects:

- a partial group;
- an overloaded member;
- a wrong return or parameter type;
- an object that already implements `IFluidProvider`.

A reflected provider then goes through the same validation and lifecycle as a compiled one. [SyntheticReflectionFluids.cs](../src/ModdableFluids/Examples/SyntheticReflection/SyntheticReflectionFluids.cs) is the working example.

## Versions and capabilities

`MinimumApiVersion` must be exactly `major.minor.patch`. While the major version is 0, a provider is accepted when its major and minor match the runtime's and its patch is no newer. Each capability a provider requires must be listed by the runtime, which lists only what is implemented:

| Capability | Meaning |
| --- | --- |
| `ModdableFluids.Registry.Definitions` | Register fluids with colour and namespaced metadata |
| `ModdableFluids.Registry.Providers` | Compiled provider registration and validation |
| `ModdableFluids.Discovery.Reflection` | The reflection route above |
| `ModdableFluids.Scene.Lifecycle` | Per-scene activation and unload |
| `ModdableFluids.Persistence.ComponentIdentity` | Saves identify fluids by ID |
| `ModdableFluids.Persistence.ProviderState` | Versioned provider-owned save data |
| `ModdableFluids.Sources.Types` | Register source types; the seven native kinds are built in (0.1.1) |
| `ModdableFluids.World.Sampling` | Read columns of the last completed tick (0.1.2) |
| `ModdableFluids.World.Additions` | Add a named fluid at a cell (0.1.2) |
| `ModdableFluids.World.SourceComposition` | One owner at a time overrides what tide-overridable sources emit (0.1.2) |
| `ModdableFluids.World.Import` | Import another save format once (0.1.3) |
| `ModdableFluids.World.Rules` | Provider rules after every completed tick (0.1.3) |
| `ModdableFluids.World.Losses` | Per-tick losses by place, reason and fluid, read by rules (0.1.4) |
| `ModdableFluids.World.Extraction` | Remove one fluid at a cell, with a per-request result (0.1.4) |
| `ModdableFluids.Policies.WaterIntakes` | Per-fluid water-intake refusal and drawn-as-water transformation (0.1.4) |
| `ModdableFluids.Policies.Irrigation` | Per-fluid soil-moisture effect (0.1.4) |
| `ModdableFluids.Rendering.TerrainOverlays` | Per-cell ground tints drawn by the native soil-contamination look on per-scene terrain material copies ([below](#terrain-overlays-moddablefluidsrenderingterrainoverlays)) |

The current runtime is 0.1.3. Each patch release only added capabilities; a provider built for 0.1.1 loads on 0.1.3.

`ModdableFluidsEntry.DescribeRuntime()` returns a plain-text report for logs and support requests. It lists the version, capabilities, phase, any fault, the registry fingerprint and fluids, and each provider with its route, minimum version and optional interfaces.

`ModdableFluidsEntry.Host` refuses to start when more than one `ModdableFluids` assembly is loaded. This was verified under the game's Mono: a second byte-load of the same DLL produces a second assembly, which is what a local copy plus a Workshop copy would do.

## Scene lifecycle and provider state

The host runs these stages in order:

1. **`ActivateScene`.** Calls `Activate` in provider order. If one provider fails, those already activated are unloaded in reverse order and the error names the failing provider.
2. **`LoadProviderStates`.** Runs once per scene and calls `LoadState` on every stateful provider. `hasState` is false for a new game or a save without data for that provider.
3. **`UnloadScene`.** Unloads every provider in reverse order, even when one throws, and then reports all failures.

The following stop loading with a `FluidSaveException` that names the provider and mod:

- saved state for a provider that is not loaded;
- saved state for a provider that no longer stores state;
- saved state from a newer schema;
- a provider that moved to another mod.

An older schema is passed to the provider, which migrates it explicitly. The compiled example migrates schema 1 to 2.

## World save schema

`FluidSaveDocument` contains only ints and strings, so it maps directly onto native `ListKey<int>` and `ListKey<string>` entries.

| Field group | Contents |
| --- | --- |
| Header | `SchemaVersion` (1), `ApiVersion`, `RegistryFingerprint` (informational) |
| Fluid table | `FluidIds`, `FluidOwners`: only fluids that have volume somewhere in the save |
| Columns | `ColumnX`, `ColumnY` (unpadded map cell), `ColumnFloor`, `ColumnCeiling`, `ColumnCapacity` |
| Components | `EntryColumn`, `EntryFluid`, `EntryVolume`: positive volumes only |
| Providers | `ProviderIds`, `ProviderOwners`, `ProviderSchemas`, `ProviderData` |

Quantities are stored as the exact IEEE-754 bits of the double, as 16 uppercase hex digits, so .NET and Mono round trips are bit-identical. The constructor validates the whole document and reports every problem.

Rules:

- **Capture.** Capture only at a completed-tick barrier, when the session phase is `Ready`.
- **Missing fluids.** A saved fluid that is not registered stops loading and names its mod. Unknown fluid is never turned into water.
- **Unused fluids.** A save with no volume of a fluid does not require that fluid's mod.
- **Added fluids.** A fluid registered after the save starts empty. The other fluids keep their volumes by ID, even though their handles move.
- **Unchanged geometry.** A column whose cell, interval and capacity are unchanged is copied bit for bit.
- **Changed geometry.** Other columns are projected with the shared geometry rules, and geometry and pressure losses are reported explicitly.
- **Native mismatch.** When native water disagrees with the restored state, the session faults and the load stops with the cell named.

The game-side envelope (`ModdableFluids.World`) is built and round-trips through the game's own persistence under Mono; see [World save in game](fluids-native-adapter.md#world-save-in-game). Envelope 2 adds `ImportPending`: a native-only save written before the first fluid substep of a world whose importers have not run, so the next load imports again. Envelope 3 (0.1.4) adds `LastCompletedTickSnapshot` (see [exception saves](#ordinary-play-and-exception-saves-014)). Envelopes 1 and 2 are still read, as written. Not yet done: the in-game save/reload run.

## Source types (0.1.1)

A source type describes one kind of water source placed from a blueprint: its template, tile count, default strength, whether it follows drought, whether badtide contaminates it, whether a tide may override what it emits, an optional periodic schedule, and the share of each extra fluid it emits. `FluidRegistration.AddSourceType`, `SetSourceEmission` and `SetSourceSchedule` register one; every behaviour is stated, nothing is inherited from a native kind. The seven native kinds (water and badwater sources, both seeps, the aquifer, the badtide drain and the dev source) are registered by Moddable Fluids with their native behaviour, including the seep depth limit, the aquifer's drill and the drain's badtide-only activity. `FluidRegistry.SourceTypes`, `TryGetSourceType` and `TryGetSourceTypeByTemplate` read them. In game the template must carry a native `WaterSourceSpec` with the same tile count and strength. Emission shares are of the source's non-bad volume and may total at most one; the rest stays fresh water.

## World service (0.1.2)

`IFluidWorld`, reached through `FluidScene.World` from 0.1.3, is the scene's fluid state for other mods:

- `TrySample(x, y, z)` returns the open column containing height z at a cell; `SampleCell(x, y)` returns every open column of the cell, lowest first (0.1.3). Samples come from the state published at the last completed tick, so any game thread may read them and never sees half a tick. `HasState` is false until the scene's first native water substep (0.1.3).
- `QueueAddition(x, y, z, fluid, volume)` is a main-thread request, like the native water service. It becomes a native clean-water change that the change stage resolves to the named fluid by cell and volume, oldest first. Badwater additions use the native contaminated-water change.
  - **Column lookup (from 0.1.4).** The column is found at the change stage, against that tick's native layout, so the last published tick need not have it: geometry may have changed this tick, or no fluid tick may have run yet. Until 0.1.3 such a request threw.
  - **Closed cell.** A cell with no open column at that stage drops the addition, as the native game drops the change. The drop is reported as `DroppedAddition`.
  - **Outside the map.** A cell outside the map throws at once.
- `SetSourceComposition(owner, shares)` makes tide-overridable source types emit the given extra fluids; `null` clears it. A second owner fails instead of winning by load order.

## Legacy import and column rules (0.1.3)

Two optional provider interfaces, for compiled providers:

- **`IFluidWorldImporter`.** When a save has no `ModdableFluids.World` entry (or one marked `ImportPending`), Moddable Fluids asks every importer once, in the first native substep on a worker thread, with the native columns (`FluidNativeColumn`: cell, interval, capacity, physical volume, native contamination). An importer returns a `FluidSaveDocument` built from data it read in its own Load, or null. The document is validated and restored like a saved one; two importers returning documents stop loading and name both.
- **`IFluidColumnRules`.** After every completed native water tick, before the tick is published, each provider's rules run in provider order on the worker thread with an `IFluidColumnEditor`. The editor reads columns and can only convert volume between two non-badwater fluids within one column, so native depth and contamination never change. It is valid only during the call. An exception fails the tick and names the provider.

## Losses, extraction and native policies (0.1.4, in development)

Built 2026-11-09. All four capabilities below are implemented and listed: `ModdableFluids.World.Losses`, `.World.Extraction`, `.Policies.WaterIntakes` and `.Policies.Irrigation`. The runtime still reports 0.1.3 until the lead sets the release version.

**Verified.** The .NET harness covers the pure parts: the loss ledger and its report, the extraction queue and its resolution, policy registration on both routes, the guard's decision, the moisture shadow, and the exception-save snapshot. The installed-Mono probe checks every native contract below against the installed assemblies. It also runs the moisture prefix on the actual native `StartTask`.

**Still needs a game.** The guard on real pumps, the moisture effect on real crops, extraction from real buildings, and ordinary-play attachment.

### Loss reports (`ModdableFluids.World.Losses`)

`IFluidColumnEditor.Losses` lists what left the world during the completed tick, on the native worker thread, while column rules run. Copy what you keep; the list is valid only during the call. Each `FluidLoss` has a kind, a place, a requester for extractions, and a volume per fluid. Entries are summed over the tick, unique per kind, place and requester, and ordered by kind, then y, x, z and requester.

| Kind | Place (`X`, `Y`, `Z`; `Column`) |
| --- | --- |
| `Evaporation`, `Discharge` (off the map edge), `Pressure` (above a column's pressure capacity) | the column's cell and floor; its editor slot |
| `NativeRemoval` (native queued removals: pumps, intakes, mechanical pumps, other mods) | the requested cell; the slot that held it |
| `SourceWithdrawal` (a native source with negative strength) | the source cell; its slot |
| `Extraction` (an `IFluidExtraction` request; `RequesterId` set) | the requested cell; its slot |
| `Geometry` (water deleted by a solid, a shrunk or a removed column) | the old column's cell and floor; `Column` is -1 |
| `DroppedAddition` (an addition queued to a cell with no open column; the native game drops it, so it never entered) | the requested cell; `Column` is -1 |

A tick's losses run from the geometry reconciliation at its start to its change stage. A blocked source loses only its own emission (`Pressure`); geometry merges report pressure on the new column. Conversions made by column rules are not losses. Losses projected while restoring a save are not part of any tick.

### Extraction (`ModdableFluids.World.Extraction`)

`FluidScene.Extraction.RequestExtraction(requesterId, x, y, z, fluid, volume, minimumShare, resolved)` removes up to `volume` of one fluid, and nothing else, from the open column containing (x, y, z). It is a main-thread request, like a native water change. Requests made before a native water tick is scheduled are resolved in that tick's change stage, after the native queued changes, in request order.

- **No column.** A request whose cell has no open column then removes nothing (`NoColumn`).
- **Too dilute.** A request whose fluid share is below `minimumShare` at that moment removes nothing (`BelowMinimumShare`).
- **Result.** Otherwise `ExtractedVolume` is what actually left: at most the request, and at most what the column held.
- **Delivery.** The callback runs once on the main thread, after that parallel tick finished and before any save is written. A building can therefore keep the result in its own save data. Requests still queued at a save removed nothing and are not saved.
- **Unload.** A scene unload drops unresolved requests without calling them back.

`requesterId` is an ID in the requester's namespace (`MoreFluids.FluidExtractor`) and appears on the tick's `Extraction` losses. A building that draws through extraction while it has a native `WaterInput` for its pipe marks itself with a component implementing `IFluidCustomIntake`, so the water-intake guard leaves it alone.

`IFluidCustomIntake` also covers an intake that keeps the native pump path on purpose. Deep Frontier's sludge intake pumps through its native `WaterInput`, so the fresh water it draws is used up as natively. Its column rules credit the radioactive volume from the tick's `NativeRemoval` losses at its cell. This is supported. Losses are summed per cell, so two intakes that share one cell share one entry, as natively they share one `RemovedWater` result.

### Water-intake policy (`ModdableFluids.Policies.WaterIntakes`)

`FluidRegistration.SetWaterIntakePolicy(localName, refuseAtShare, drawnAsWater, refusedStatusLocKey, refusedAlertLocKey)`:

- **Refusal.** Native water intakes are entities with a native `WaterInput` and no `IFluidCustomIntake` component. Moddable Fluids' one guard blocks them through the native `BlockableObject`, with the fluid's status, while their column's share of the fluid is at or above `refuseAtShare` (in (0, 1]). The share is read at the last completed tick.
- **Drawn as water.** Below the refusal share, the part of a native clean-water removal that is this fluid becomes native clean water: Water goods at a pump, water at a mechanical pump's outlet. `drawnAsWater` names that transformation (for example `MoreFluids.CoffeeDrunkAsWater`). It is an ID in the provider's namespace, and no two fluids may share one. The drawn volume appears in the tick's `NativeRemoval` losses.
- **Examples.** Coffee is refused at 0.5 and drawn as `MoreFluids.CoffeeDrunkAsWater`; saltwater is refused at 0.1. Deep Frontier's radioactive water is refused at 0.005.
- **Scope.** Like Deep Frontier's guard, it blocks every native intake, badwater pumps and mechanical pumps included. It has one status per refusing fluid and no hysteresis. Before a scene's first completed fluid tick it decides nothing.

### Irrigation policy (`ModdableFluids.Policies.Irrigation`)

`SetIrrigatesLikeWater(localName)` or `SetBlocksMoisture(localName, blocksAtShare)`. Moddable Fluids owns the native soil-moisture input. The moisture tasks see a column's contamination as `b + sum(share * M / blocksAtShare)` over the fluids that block. Here `b` is the badwater share and `M` is the native `SoilMoistureSimulatorSpec.MaximumWaterContamination` (0.53 in 1.1.2.8), where badwater gives no moisture.

- **Saltwater.** Blocking at 0.1 gives no moisture from a 10% saltwater column.
- **Badwater-like.** Blocking at `M` behaves exactly like badwater.
- **Above 1.** Native moisture readers treat values at or above 1 as no moisture.

### Placed source types (0.1.4)

Every placed native water source is classified once, when its entity wakes, by its blueprint's template name and native specs (`NativeSourceClassifier`):

- **Matching.** A blueprint without a registered source type, or one that no longer matches its type (tiles, default strength, badtide controller, and for native kinds contamination, depth limit, drill, weathers, direction), stops loading with both named.
- **Emission.** Each source emits its own type's fluids. An active tide composition replaces them only for tide-overridable types.
- **Schedule.** A type's schedule (a geyser) is applied as a native `IWaterStrengthModifier` on the source.
- **Drought.** A type that does not follow droughts removes the source's native drought modifier, as the Badwater Pressurizer's `UnderlyingWaterSource.DisableDroughtInfluence` does.
- **Badtide.** Badtide behaviour stays the blueprint's own native controller; the classification checks that it agrees with the type.

### Visibility curve (shared rendering)

`SetVisibilityCurve(localName, fromShare, visibilityAtFromShare)` declares how visible a fluid is in the shared water renderer (`FluidVisibility`):

- **The curve.** The fluid is hidden below `fromShare` (in (0, 1)) and shows at `visibilityAtFromShare` (in (0, 1]) there. Visibility then rises with the logarithm of the share, reaching 1 in a pure column.
- **Without a curve,** the visibility is the share.
- **Deep Frontier.** Its radioactive water is `(0.005, 0.12)`. This reproduces `RadioactiveWaterSurface.Encode`, `0.12 + 0.88 * log10(r / 0.005) / -log10(0.005)`, to 1e-12 in the harness.
- **Blending.** Each fluid's weight is its colour alpha times its visibility. Each fluid's tint covers what the others leave: strength = 1 - product(1 - weight). The colour is the weight-weighted mean.
- **Native curve.** The GPU half encodes the strength through the inverse of the native contamination curve, as before.

Not covered: Deep Frontier's two base and two detail colours. A fluid has one colour.

### Both policies are required in game

Every extra fluid needs both policies before Moddable Fluids attaches to a game scene. `FluidRegistry.UndeclaredPolicies()` lists what is missing, and the scene stops loading with that list, naming each fluid, provider and mod. Registration, freeze and the harness do not require them, so providers built for 0.1.3 still register. `DescribeRuntime()` prints each fluid's policies.

## Terrain overlays (`ModdableFluids.Rendering.TerrainOverlays`)

Built 2026-11-09, at the user's decision 8a, so that no mod has to change the game's terrain materials. It has passed the .NET harness and the installed-Mono probe; nothing of it has run in game, and its shader has not been built by Unity yet. The capability is listed; the API version stays 0.1.4 until the lead sets the release version.

**Registering.** Call `ModdableFluidsEntry.Host.RegisterTerrainOverlay(id, ownerModId, color, curve)` from `IModStarter.StartMod` and keep the returned `FluidTerrainOverlay`. Registration closes with the provider registrations, when the registry freezes before the first game scene. Afterwards `Host.TerrainOverlays` lists the overlays in ordinal ID order, and that order is each overlay's `Index`.

- **ID.** `<OwnerModId>.<LocalName>`, inside the owner's namespace. The `Timberborn` owner is reserved, and a second registration of one ID is refused.
- **Curve.** `FluidTerrainOverlayCurve(visibleFrom, full, levelAtZero)` maps a value to a level the way the game maps soil contamination (`SoilContaminationService.GetMapSoilContamination`):
  - nothing below `visibleFrom`, which is in (0, `full`];
  - from there, the straight line from `levelAtZero` (in [0, 1)) at 0 to 1 at `full`;
  - 1 above `full`.

  The level is stored as the native `PixelData` stores it, `byte(255 * level)`, truncated. `Encode(value)` returns that byte. Values must be finite and at least 0.
- **Colour.** `FluidTerrainOverlayColor(red, green, blue)` gives the factors the native soil-contamination texture (the veins the game draws on contaminated soil) is multiplied by. It is a material colour, as `Material.SetColor` takes the native Contamination Color: in the game's gamma colour space the shader multiplies by the values as they are. A linear project would linearise them as SetColor does. Channels may exceed 1, because the veins are dark; each is finite and in [0, 64], the headroom of the half-float colour map.

**Writing.** `overlay.Set(x, y, z, value)` sets the value at the ground surface of terrain cell (x, y) drawn at floor z. `GetLevel(x, y, z)` reads the stored level.

- **Thread and scene.** Only on the main thread, and only while a game scene's surface is attached (`IsAttached`). The surface attaches when Moddable Fluids' terrain renderer loads, before any `PostLoad`, and detaches at unload. Each scene starts with every cell at 0.
- **Size.** `Width`, `Height` and `Depth` are the native `TerrainService.Size`. A cell outside it is refused.
- **Cost.** A value whose level did not change changes nothing.

**What is drawn.** Several overlays on one cell draw the highest level, in the level-weighted mean of their colours. Levels follow the native soil-contamination update rule. A change shows during the next tick, interpolated from old to new by the native tick progress, and settles at the tick after. A loaded scene's values, written before its first tick, show at once. A colour changes at the tick, not interpolated. A cell fading out keeps its colour until its level settles at 0.

**Rendering.** Moddable Fluids makes per-scene copies of the game's terrain materials on its own shader variant and assigns them only to the scene's terrain tiles, as it does for water. The game's materials are never changed. See [Shared rendering](fluids-native-adapter.md#shared-rendering).

**What is not covered.**

- Only terrain tiles get the overlay. Any other renderer drawn with a native terrain material keeps the native look. In 1.1.2.8 the terrain block models (`Environment/Land`, read from the game data) use only Cliff and CliffEdge; Grass, SlopeCliff and SlopeCliffEdge are drawn by other models.
- There is no reflection route: the overlay types are compiled API.

## Ordinary play and exception saves (0.1.4)

- **Attaching.** The `Game` configurator freezes the registry. When a mod registered at least one extra fluid, it binds the scene owner, shared rendering, the water-intake guard, the moisture input and placed-source classification. With none it binds none of these. The worker fixture stays behind `-moddableFluidsWorkerAcceptance`.
  - **Terrain overlays.** When a mod registered at least one terrain overlay, the configurator checks the terrain renderer's native contract and binds it, whether or not a fluid was registered. With none, the native terrain stays untouched.
- **Refusing.** Before anything changes, the scene stops loading with one message per problem:
  - a fluid without both policies;
  - a changed native contract (intake guard, moisture input, placed sources, scheduler, exception-save flag);
  - another mod's Harmony patch on a native method Moddable Fluids replaces or skips. The shipped Deep Frontier's `DeepFrontier.RadiationLockstep` and `DeepFrontier.RadiationSoil` are refused this way, by owner and method.
- **Exception saves.** The native exception saver (`GameSceneExceptionStateSaver`, marked by `TickOnlyArrayService._forceAllowAccess`) can arrive while a fluid tick runs.
  - **Writing.** Moddable Fluids writes the last published completed tick, rules included, marked `LastCompletedTickSnapshot` in envelope 3. This mirrors Deep Frontier's `RadiationSimulation.Save`. Normal saves still require a completed tick and fail otherwise.
  - **Loading.** Such a save keeps each column's native physical volume and badwater share, because those arrays were saved mid-tick. The non-bad volume takes the snapshot's non-bad composition, or fresh water where the snapshot had none. Every adjusted column and the change per fluid go to the log.

## Optional integrations

| Route | When the API is absent |
| --- | --- |
| Reflection only, `OptionalMods: ModdableFluids` | Works and reports absence; verified under .NET 8 and the installed Mono |
| Compiled reference, `RequiredMods: ModdableFluids` | The package's provider types cannot load. `GetTypes()` fails, and the game's `ModCodeStarter` does not catch that (verified under both runtimes). Ship such a package only as a hard dependent. |
| Moddable Timberborn `.optional` bridge | Loaded only when the named mod is enabled (Deep Frontier's existing mechanism); for consumers that already depend on Moddable Timberborn |

## Development fixtures

The two fixture packages under `src/ModdableFluids/Examples` register only with `-moddableFluidsWorkerAcceptance`:

- `ModdableFluidsSyntheticReflection` registers `Juice` by reflection, with state and scenes.
- `ModdableFluidsSyntheticCompiled` registers `Tracer` through the compiled interfaces, with a state migration.

Timberborn enables a newly installed mod by default. The official build therefore moves every package out of `Mods` into `outputs/fluids-api-prototype/packages`: both fixtures and the Moddable Fluids package itself. `tools/start_fluid_worker_acceptance.ps1` installs them only for a run, then removes them and any preference keys created for them.
