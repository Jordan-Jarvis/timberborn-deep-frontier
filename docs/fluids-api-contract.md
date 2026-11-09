# Fluids API 0.1 contract

Implemented 2026-11-09 as item 3 of the [Fluids API plan](fluids-api-plan.md), with item 4's persistent identities. The contract is experimental: its major version is 0, so any minor release may change it. It has passed the .NET 8 harness and the installed-Mono probes, including a Mono process without the API. It has not run in a game yet. Behaviour policies, public sampling, shared rendering and tide registration are not part of 0.1. Where the plan calls a definition field a behaviour or appearance, that is only data until the matching capability exists.

## Assemblies

| Assembly | Contents | References |
| --- | --- | --- |
| `FluidsApi` | IDs, definitions, registry and handles, providers, scene lifecycle, discovery entry, save schema | `netstandard` only, so its types enumerate safely in any installation |
| `FluidsApi.TransportPrototype` | Transport, native adapter, world persistence (`FluidWorldPersistence`) | `FluidsApi` |
| `FluidsApi.GamePrototype` | Native scheduler hooks and their startup contract | Harmony, `Timberborn.Multithreading` |
| `FluidsApi.RuntimePrototype` | Flag-gated scene owner and worker fixture | Game assemblies |

The three prototype assemblies keep their experimental `*.Prototype` namespaces. The package activates nothing unless the game is started with `-fluidsApiWorkerAcceptance`.

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

Register providers from an `IModStarter.StartMod`. The flag-gated runtime freezes the registry once, before the first game world. After that, registering throws an error that points back to `StartMod`.

The freeze runs each provider's `Register` in ordinal `ProviderId` order, then validates everything together. Every problem is reported in one `FluidRegistryException` that names the provider, the mod and the fluid. A failed freeze leaves the host faulted with that report.

Load order cannot break registration. Timberborn loads every enabled mod's assemblies before any `StartMod` runs (`ModCodeStarter`), and the process-wide host is created on first use. Consumers should still list `FluidsApi` in `RequiredMods` (compiled route) or `OptionalMods` (reflection route), so the native sorter places the API first by default. A player can move mods by hand-set priority; registration does not depend on the API loading first.

## Compiled providers

```csharp
public sealed class CoffeeProvider : IFluidProvider, IFluidSceneProvider, IFluidStateProvider {
  public string ProviderId => "MoreFluids.Drinks";
  public string OwnerModId => "MoreFluids";
  public string MinimumApiVersion => "0.1.0";
  public IReadOnlyCollection<string> RequiredCapabilities { get; } = new[] { "FluidsApi.Registry.Definitions" };
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
// IModStarter.StartMod: FluidsApiEntry.RegisterProvider(new CoffeeProvider());
```

Optional behaviour uses separate interfaces (`IFluidSceneProvider`, `IFluidStateProvider`). Later stages will add new optional interfaces rather than change `IFluidProvider`.

## Reflection providers

A consumer with no compiled reference:

1. Finds exactly one loaded assembly named `FluidsApi` in `AppDomain.CurrentDomain.GetAssemblies()`. If there is none, the API is absent. If there are several, it stops with an error.
2. Gets the type `FluidsApi.FluidsApiEntry`.
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

A reflected provider then goes through the same validation and lifecycle as a compiled one. [SyntheticReflectionFluids.cs](../src/FluidsApi/Examples/SyntheticReflection/SyntheticReflectionFluids.cs) is the working example.

## Versions and capabilities

`MinimumApiVersion` must be exactly `major.minor.patch`. While the major version is 0, a provider is accepted when its major and minor match the runtime's and its patch is no newer. Each capability a provider requires must be listed by the runtime, which lists only what is implemented:

| Capability | Meaning |
| --- | --- |
| `FluidsApi.Registry.Definitions` | Register fluids with colour and namespaced metadata |
| `FluidsApi.Registry.Providers` | Compiled provider registration and validation |
| `FluidsApi.Discovery.Reflection` | The reflection route above |
| `FluidsApi.Scene.Lifecycle` | Per-scene activation and unload |
| `FluidsApi.Persistence.ComponentIdentity` | Saves identify fluids by ID |
| `FluidsApi.Persistence.ProviderState` | Versioned provider-owned save data |

`FluidsApiEntry.DescribeRuntime()` returns a plain-text report for logs and support requests. It lists the version, capabilities, phase, any fault, the registry fingerprint and fluids, and each provider with its route, minimum version and optional interfaces.

`FluidsApiEntry.Host` refuses to start when more than one `FluidsApi` assembly is loaded. This was verified under the game's Mono: a second byte-load of the same DLL produces a second assembly, which is what a local copy plus a Workshop copy would do.

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

Not built yet: the game-side saver/loader singleton, the Deep Frontier importer, and in-game save/reload acceptance.

## Optional integrations

| Route | When the API is absent |
| --- | --- |
| Reflection only, `OptionalMods: FluidsApi` | Works and reports absence; verified under .NET 8 and the installed Mono |
| Compiled reference, `RequiredMods: FluidsApi` | The package's provider types cannot load. `GetTypes()` fails, and the game's `ModCodeStarter` does not catch that (verified under both runtimes). Ship such a package only as a hard dependent. |
| Moddable Timberborn `.optional` bridge | Loaded only when the named mod is enabled (Deep Frontier's existing mechanism); for consumers that already depend on Moddable Timberborn |

## Development fixtures

The two fixture packages under `src/FluidsApi/Examples` register only with `-fluidsApiWorkerAcceptance`:

- `FluidsApiSyntheticReflection` registers `Juice` by reflection, with state and scenes.
- `FluidsApiSyntheticCompiled` registers `Tracer` through the compiled interfaces, with a state migration.

Timberborn enables a newly installed mod by default. The official build therefore moves both packages out of `Mods` into `outputs/fluids-api-prototype/fixture-packages`. `tools/start_fluid_worker_acceptance.ps1` installs them only for a run, then removes them and any preference keys created for them.
