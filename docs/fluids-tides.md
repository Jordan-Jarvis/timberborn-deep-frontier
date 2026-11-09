# Moddable Fluids tides

Tide registration for Moddable Fluids, started 2026-11-09. A tide is a hazardous weather registered by a content mod. While it is the cycle's weather and in progress, every tide-overridable water source emits the tide's fluids, and may run at reduced strength. Moddable Fluids owns the one native weather adapter for all registered tides. Content mods register tides; they do not patch the native weather.

Status:

- **Implemented and tested outside the game.** The registration API, the validation at registry freeze and the selection rule are covered by the .NET harness. The game-side adapter (`src/ModdableFluids/Tides`) compiles against the shipped game assemblies, and its native parts pass a probe in the game's own Mono (see [Evidence](#evidence)).
- **Not yet run in game.** It binds where the scene owner does (every game in which a mod registers a fluid, and the worker fixture), and only when a tide is registered. The new-game rows follow the same rule in the main menu.

## Selection policy C′

User decision, 2026-11-09: tides split one shared hazard budget. Installing more tide mods therefore does not make a game harder, and a vanilla-only or Deep-Frontier-only game stays exactly as before. Each tide has a weight within the budget, shown on the new-game screen. The rule is `FluidTideSelection.Select`, a pure function in the `ModdableFluids` assembly.

The native drought or badtide draw runs first, unchanged. The rule then decides whether that cycle's hazardous weather becomes a tide:

1. Cycle 1 keeps the native weather; tides start from cycle 2 (`FluidTideRules.EarliestCycle`).
2. A tide forced from the development menu is chosen. It must be enabled in the save.
3. **Global cooldown.** The cycle right after any tide keeps the native weather (`CooldownCycles` = 1).
4. The eligible tides are the save's enabled tides whose cycles without tide have passed. If there are none, the native weather stays.
5. One draw against the save's budget: `CheckProbability(budget / 100)`. A miss keeps the native weather.
6. On a hit, one of the save's **enabled** tides is picked by weight. With a single enabled tide there is no further draw. Otherwise one `Range(0, total enabled weight)` draw is walked over the enabled tides in ordinal ID order. A pick that is not eligible yet keeps the native weather.

Load order never matters: tides are always taken in ordinal ID order. With one installed tide the draws, including the random calls, are exactly those of Deep Frontier's `RadioactiveTideService.Choose`.

Per save:

- **Budget.** The chance per eligible cycle that the cycle becomes a tide. The default is the largest chance among the installed tides for the game's mode.
- **Weight.** Each tide's share of the budget. The default is the tide's own chance.
- **Per tide:** on or off, cycles without the tide, and duration.

**Early cycles** (user decision 1b, 2026-11-09). Each eligible tide gets only its own slice of the budget: budget × its weight ÷ the total weight of every enabled tide. A tide whose cycles without have not passed leaves its slice to the native weather, so the eligible tides do not share the whole budget. The cycle's tide chance never exceeds the budget. Long-run shares are unchanged, because every tide is eligible by then. The model asserts that both forms agree in the long run.

On Normal, a cycle right after a non-tide cycle becomes a tide with this chance (cycles without: radioactive 14, coffee 8, salt 7):

| Cycle | Deep Frontier | More Fluids | Deep Frontier + More Fluids |
| ---: | ---: | ---: | ---: |
| 8 (salt only) | 0% | 7.5% | 6.8% |
| 9–14 (coffee and salt) | 0% | 15.0% | 13.6% |
| 15 on (all) | 25.0% | 15.0% | 25.0% |

For these installs no cycle is harder than with the harder mod alone. In general the bound is the budget, and each tide's chance per eligible cycle is its fixed slice. An install where a high-chance tide is not yet eligible can still give the eligible low-chance tides more than they would get alone. For example, chances 50, 10 and 10 with only the two 10% tides eligible give 50 × 20 ÷ 70 = 14.3%.

### Long-run shares

Computed by [model_tide_selection.py](../tools/model_tide_selection.py), an exact Markov model of the native badtide streak rule plus this selection rule. Its output is `outputs/fluids-api-prototype/tide-policy-model.json`. The harness recomputes the same shares from the C# `Select` function and checks them to 1e-9. All shares assume every weather is eligible.

Each install uses its tides' own chances: Deep Frontier radioactive 15/25/35% on Easy/Normal/Hard, More Fluids coffee and salt 10/15/20% each. The budget is the largest of those chances, and the weights are the chances.

| Mode | Installed | Budget | Drought | Badtide | Radioactive | Coffee | Salt |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| any | Vanilla only | – | 59.7% | 40.3% | – | – | – |
| Easy | Deep Frontier | 15% | 52.2% | 34.8% | 13.0% | – | – |
| Easy | More Fluids | 10% | 54.5% | 36.4% | – | 4.5% | 4.5% |
| Easy | Deep Frontier + More Fluids | 15% | 52.2% | 34.8% | 5.6% | 3.7% | 3.7% |
| Normal | Deep Frontier | 25% | 48.1% | 31.9% | 20.0% | – | – |
| Normal | More Fluids | 15% | 52.2% | 34.8% | – | 6.5% | 6.5% |
| Normal | Deep Frontier + More Fluids | 25% | 48.1% | 31.9% | 9.1% | 5.5% | 5.5% |
| Hard | Deep Frontier | 35% | 44.5% | 29.5% | 25.9% | – | – |
| Hard | More Fluids | 20% | 50.0% | 33.3% | – | 8.3% | 8.3% |
| Hard | Deep Frontier + More Fluids | 35% | 44.5% | 29.5% | 12.1% | 6.9% | 6.9% |

- **One tide reproduces Deep Frontier.** The Deep Frontier rows equal the current Deep Frontier rule (13.0, 20.0 and 25.9%); the model asserts this.
- **More tides, same hazard.** Deep Frontier + More Fluids keeps Deep Frontier's total hazard exactly. The installed tides divide it.

The model treats the probabilities as exact decimals; the game draws them as floats (0.15f), which moves shares by about 1e-8.

## Registration API

Capability `ModdableFluids.Tides.Registration`. A provider calls these on its `FluidRegistration` during `Register`. All parameters are primitives, so reflected providers can call them too.

| Method | Meaning |
| --- | --- |
| `AddTide(localName, nativeWeatherId, displayNameLocKey, descriptionLocKey)` | Tide `OwnerModId.localName`. `nativeWeatherId` is the `IHazardousWeather.Id` the game stores in its weather history and looks up in fog and source lists. |
| `SetTideMode(tide, mode, chancePercent, cyclesWithoutTide, minDays, maxDays)` | Values for `Easy`, `Normal` and `Hard`; all three are required. |
| `SetTideSourceEmission(tide, fluidId, share)` | While in progress, this share of every tide-overridable source's non-bad volume is the registered extra fluid. At least one is required, and the shares total at most 1. |
| `SetTideSourceStrength(tide, multiplier)` | While in progress, clean tide-overridable sources (default badwater share 0) run at this multiple of their native strength, in (0, 1]. Optional; the default is 1. |
| `SetTideTexts(tide, approaching, inProgress, started, ended, approachingDescription, startedDescription)` | Loc keys for the native weather panels and banner. |
| `SetTideArt(tide, iconSprite, progressSprite, notificationSprite)` | Sprite asset paths for the date panel, weather panel and banner. |
| `SetTideStartSound(tide, "Badtide" or "Drought")` | The native alarm. |

Ranges: chance 1–100%, weight 1–100, budget 1–100%, cycles without 1–99, duration 1–30 days.

The freeze reports every problem in one `FluidRegistryException`:

- a missing part;
- a fluid that is not a registered extra fluid, or shares above 1;
- two tides with one ID or one native weather ID, or a tide using a native weather ID;
- a mode curve that leaves the allowed ranges (see below).

A provider whose `Register` throws contributes no tides.

After the freeze, `ModdableFluidsEntry.Host.Tides` (a `FluidTideRegistry`) lists the tides in ordinal ID order. `TryGetByWeather` finds a tide by its native weather ID.

### Content each tide mod supplies

- Fog entries for its native weather ID in every day stage of `SunSpec`. The native `Sun.GetFogSettings` throws without them.
- The loc keys and sprites it names.

### Example (More Fluids coffee tide)

```csharp
r.AddTide("CoffeeTide", "MoreFluids.CoffeeTide", "MoreFluids.Weather.CoffeeTide", "MoreFluids.Weather.CoffeeTideDescription");
r.SetTideMode("CoffeeTide", "Easy", 10, 12, 2, 4);
r.SetTideMode("CoffeeTide", "Normal", 15, 8, 3, 5);
r.SetTideMode("CoffeeTide", "Hard", 20, 6, 4, 7);
r.SetTideSourceEmission("CoffeeTide", "MoreFluids.Coffee", 1.0);
r.SetTideSourceStrength("CoffeeTide", 0.5);
r.SetTideTexts("CoffeeTide", ...);  r.SetTideArt("CoffeeTide", ...);  r.SetTideStartSound("CoffeeTide", "Drought");
```

## Values for other game modes

A tide defines values for the vanilla Easy, Normal and Hard presets only. Every other mode derives them from its own weather (`FluidTideModes.Derive`). This is Deep Frontier's rule (docs/radiation.md, "Settings per game"), applied to any tide:

- **No hazards, no tide.** A mode whose longest hazardous season is under a day has the tide off.
- **Curve.** Chance, cycles without and the shortest and longest tide are read off the tide's three points at the mode's hazard share. Values are linear between the two surrounding points, the end segment continues beyond Easy or Hard, and each is rounded to a whole number (halves away from zero).
- **Cap.** The tide never lasts longer than the mode's longest hazardous season.

The anchors are the vanilla 1.1.2.8 presets (`FluidTideModeWeather.VanillaEasy`/`Normal`/`Hard`); the harness checks them against the blueprints. Registration requires each tide's curve to stay in range for every hazard share in [0, 1], so the rule never clamps.

A save's defaults: each tide's weight is its derived chance, and the budget is the largest derived chance among the installed tides.

## Game adapter

`src/ModdableFluids/Tides`, compiled into the Runtime assembly. `FluidTidesConfigurator` binds it under the scene owner's condition, and only when at least one tide is registered. A tide always emits a registered extra fluid, so the scene owner is then bound too. With no tide, nothing is bound and no native method is patched.

### Native hooks

Hazardous weather is closed in Timberborn 1.1.2.8:

- `HazardousWeatherRandomizer` and `HazardousWeatherService` know only drought and badtide.
- The service saves only `IsDrought`.
- `HazardousWeatherUIHelper` throws "No UI for weather" for any other weather.
- The internal `HazardousWeatherSoundPlayer` throws for any other weather.

One adapter covers every tide, generalizing Deep Frontier's radioactive tide patches. Each registered tide is a `FluidTideWeather` (`IHazardousWeather`, `Id` = its native weather ID). Harmony owner `ModdableFluids.Tides`:

| Target | Kind | Purpose |
| --- | --- | --- |
| `HazardousWeatherRandomizer.GetRandomWeatherForCycle(int)` | postfix | `FluidTideSelection.Select` after the native draw |
| `HazardousWeatherService.Load()` | postfix | puts a saved tide back through the private `CurrentCycleHazardousWeather` setter |
| `HazardousWeatherUIHelper.UpdateCurrentUISpecification()` | skipping prefix while a tide is current | avoids the native throw |
| eight `HazardousWeatherUIHelper` string getters | prefixes while a tide is current | the tide's loc keys and three marker classes |
| `HazardousWeatherSoundPlayer.OnHazardousWeatherStarted` | prefix for a tide | the tide's native alarm (badtide or drought) |
| `WeatherStation.Sample()` | prefix | samples the cycle's tide just before the native sample |
| `WeatherStation.UpdateOutputState()` (private) | skipping prefix while a tide mode is on | the tide mode's output |
| `WeatherStationFragment.InitializeFragment()` and `UpdateFragment()` (internal type) | postfixes | one radio button per tide, exactly one button selected |

`FluidTideUi` turns the marker classes into inline styles with the current tide's sprites, and adds the tide's description line to the banner. This is Deep Frontier's `RadioactiveTideUi`, made generic.

**Lifetime.** The patches are installed when `FluidTideService` is constructed and removed when it unloads. Every Game-scene singleton is constructed before the first `Load`, so the patches are in place before native `HazardousWeatherService.Load` and the first `SetForCycle`. A second install while patches from an earlier scene remain is refused.

**Startup contract.** `FluidTideNative.VerifyGame` runs before installing and stops the scene, naming any member that changed. It checks:

- every target's signature;
- the private setter and `PanelStack._root`;
- that `SetForCycle` calls the randomizer and `GetDurationAtCycle`;
- the sound controller's two start sounds;
- that each prefixed or postfixed method is longer than Mono's inline limit.

The eight getters are small enough to inline. They rely on Harmony disabling inlining when it patches, and the game's panels are compiled after the patch. The Mono probe reads a getter from a caller compiled after patching.

**Foreign patches.** Any other Harmony owner on a target is refused before anything is installed, naming each owner. Two examples are Deep Frontier's shipped radioactive tide (`DeepFrontier.RadioactiveTide`) and Moddable Weathers' transpilers. A tide of Deep Frontier's must then come from its Moddable Fluids build (`DEEP_FRONTIER_MODDABLE_FLUIDS`), which registers through this API.

**Content check.** At `PostLoad`, every tide's native weather ID must have fog in all four day stages of `SunSpec`. Otherwise the native `Sun.GetFogSettings` would throw when the tide starts.

### Source effect

- **Composition.** While a tide is in progress (`WeatherService.IsHazardousWeather` and the cycle's weather is the tide), `FluidTideService` owns the world's source composition: it calls `IFluidWorld.SetSourceComposition("ModdableFluids.Tides", tide.SourceEmission)`, and clears it when the tide ends. Content mods must not set a composition themselves; the single-owner rule would refuse them.
- **Strength.** `FluidTideStrengthModifier` uses the native mechanism: an `IWaterStrengthModifier` on every `WaterSource`, attached by a `TemplateModule` decorator the same way the game attaches `DroughtWaterStrengthModifier`. `WaterSource` multiplies it into `CurrentStrength` every tick. While a tide is in progress, it returns `FluidTideDefinition.StrengthMultiplierFor(type)`, for example 0.5 for coffee; otherwise it returns 1.
- **Which sources the strength applies to** (user decision 2b, 2026-11-09). A source type gets the tide's multiplier when it is tide-overridable and clean: its default badwater share is 0. That covers the native water source, water seep, aquifer and dev source, and every registered custom type. Badwater-emitting kinds (badwater source, badwater seep, badtide drain) keep their strength. The harness checks every native kind.
- **Source types.** A source's type is found by its template name (`TemplateSpec`). A placed source whose template has no registered source type stops loading, naming the template.
- **Badwater sources.** Every native source type is tide-overridable, but a tide's composition only shares out non-bad volume, so a badwater source's emission stays badwater. Its strength is unchanged (rule above).
- **Timing.** The composition and strength change in the tick the tide starts and ends. There is no ramp.

### Saving

| Key | Contents |
| --- | --- |
| Singleton `ModdableFluids.Tides` | `CurrentCycleTide` (tide ID or empty), `LastTideCycle`, `LastTideId`, `LastTideDuration` |
| Singleton `ModdableFluids.TideSettings` | `BudgetPercent`, and parallel lists `TideIds`, `Enabled`, `Weights`, `CyclesWithoutTide`, `MinDurationDays`, `MaxDurationDays` |
| Native `HazardousWeatherHistory` | each tide under its native weather ID, which gives it its own occurrence count |

`PostLoad` checks the restored tide against the native service: the same tide, cycle and duration.

Every save writes both singletons; a save with only one of them is refused. The state and settings are read once, at first use, because the native weather may ask during the scene's Load. They come from, in order:

1. **The save's own copy.**
   - A tide registered after the save was made is off in that save.
   - A saved tide that no installed mod registers stops loading, naming it.
2. **An importer.** A loaded save (not a new game) with neither singleton asks every `IFluidTideImporter` once (see [Importing another tide system's state](#importing-another-tide-systems-state)).
3. **A new game's mode.**
   - The custom mode's tide rows, as a `FluidTideGameModeSpec` on its blueprint.
   - Any other mode derives its values from its own weather. A mode's own spec that leaves out a tide also derives that tide.
4. **A loaded save without tide settings that no importer reads.** Every tide is off. The mode such a save started from is not stored.

A save without tide state whose native history already contains a registered tide's weather ID, and that no importer read, was played under another tide system. Its loading is refused.

### Importing another tide system's state

Capability `ModdableFluids.Tides.Import`. A compiled provider can also implement `IFluidTideImporter`:

```csharp
public interface IFluidTideImporter {
  FluidTideImport ImportTides(FluidTideImportContext context);
}
```

**When it is asked.** The tide service calls `ModdableFluidsHost.ImportTides` once per scene, before it resolves settings or restores the cycle's weather. That happens only for a loaded save (not a new game) that has neither `ModdableFluids.Tides` nor `ModdableFluids.TideSettings`. The host asks every importer in provider order.

**What it is given.** `FluidTideImportContext` holds:

- `Tides`, the frozen tide registry;
- `NativeSingletonLoader`, the save's `Timberborn.WorldPersistence.ISingletonLoader`, from which the importer reads its own singletons;
- `NativeSettings`, the game's `Timberborn.SettingsSystem.ISettings`, where older mod settings were stored.

Both native services are passed as `object`, so the API assembly stays free of game types.

**What it returns.** Null when the save holds nothing for this importer. Otherwise a `FluidTideImport(currentCycleTideId, lastTideCycle, lastTideId, lastTideDuration, budgetPercent, tides)`, where `tides` is a list of `FluidTideSettings`.

**Validation.** The constructor validates the state as a saved state is validated:

- no last tide means cycle 0, no ID and no duration;
- a last tide is in cycle 2 or later and lasted at least a day;
- the current cycle's tide, if any, is the last tide.

`FluidTideSaveSettings` and `FluidTideSettings` check the budget, weights, cycles without, durations and duplicates. Then:

- **Importer failures.** An importer that throws, including on these checks, stops loading with its provider named.
- **Unknown tides.** A current, last or listed tide that no installed mod registers stops loading with a `FluidSaveException` naming the importer.
- **Two importers.** If two importers return state, loading stops naming both.
- **Unlisted tides.** Registered tides the import does not list are off in the save.

**Afterwards.** The import replaces steps 3 and 4 above. The native Load postfix restores the imported current tide, and `PostLoad` checks it against the native cycle and duration. `FluidTideService.ImportedBy` names the importer. The next save writes Moddable Fluids' own singletons, so a save is imported at most once.

**Deep Frontier's mapping** is implemented by Deep Frontier, not here:

| Deep Frontier key | Import field |
| --- | --- |
| `DeepFrontier.RadioactiveTide`: `CurrentCycleIsTide`, `LastTideCycle`, `LastTideDuration` | current and last tide `DeepFrontier.RadioactiveTide` |
| `DeepFrontier.RadioactiveTideSettings`: `Enabled`, `CyclesWithoutTide`, `ChancePercent`, `MinDurationDays`, `MaxDurationDays` | settings, with budget = weight = `ChancePercent` |
| Saves from 0.8.3 and older | the former mod-setting keys, through `NativeSettings` |

### New-game screen

`FluidTideNewGameSettings` generalizes Deep Frontier's radioactive tide rows. After the native badtide rows it adds:

- **Tide chance (shared by all tides)**: the budget;
- for each tide in ordinal order: its toggle, then *Cycles without …*, *… share of the tide chance* (its weight) and *… duration*.

How the rows work:

- They are native rows moved from fresh copies of the native panel view, renamed and relabelled.
- They clamp on focus-out with the native `TextFields.InitializeIntegerField`.
- Invalid values get the native invalid class and keep Start disabled.
- Customize fills the rows from the selected preset.

A postfix on `CustomNewGameModeController.TryGetValidatedGameMode` attaches the values as a `FluidTideGameModeSpec`. Its Harmony owner is `ModdableFluids.TidesNewGame`. It is installed when the main menu builds the screen and removed when the main menu unloads. `VerifyNewGame` first checks the native call path from the panel to `GameSceneLoader.StartNewGame`.

The row labels are Moddable Fluids keys in `src/ModdableFluids/Tides/Localizations/enUS.csv`.

### Weather Station

Capability `ModdableFluids.Tides.WeatherStations`. This is Deep Frontier's radioactive-tide mode, made generic for every registered tide.

**Why it needs patches.** The native `WeatherStationMode` is a closed enum `{Temperate, Drought, Badtide}`. The station saves it, and `UpdateOutputState` throws for any other value. `Sample` tests the cycle's weather only with `is DroughtWeather` and `is BadtideWeather`. So a tide cannot be an enum value.

**The decorator.** `FluidTideWeatherStation` is added to every `WeatherStation` by a `TemplateModule` decorator. It holds the chosen tide and saves it by tide ID: component `ModdableFluids.WeatherStationTide`, property `Tide`, empty for the native mode.

**While a tide mode is on:**

- the native `Mode` keeps the player's previous native choice, so removing the tide system leaves a working station;
- the output is (the cycle's weather is that tide) and the native private `WithinActivationTimeHazardous`, as for the native Drought and Badtide modes, early activation included;
- there is one `Automator.SetState` per update, as native.

**The panel.** The internal `WeatherStationFragment` gets one native radio toggle, with a button per registered tide in ordinal order, made with the public `RadioToggleFactory.CreateLocalizable` in the native `ModeRadioToggleContainer`. Exactly one button is selected. Clicking a native mode button returns the station to its native mode.

**Startup contract.** `FluidTideNative.VerifyGame` checks:

- the enum's exact values, and that `UpdateOutputState` is private;
- that `Sample` reads `CurrentCycleHazardousWeather` and calls `UpdateOutputState`;
- that `UpdateOutputState` calls `Automator.SetState(bool)` and `WithinActivationTimeHazardous`;
- the fragment's container name, its `CreateLocalizable<WeatherStationMode>` call, `RadioToggle.Update(int)` and the four private fields;
- the inline limits.

The patches install and uninstall with the other tide patches, and foreign owners are refused the same way. Deep Frontier's shipped `DeepFrontier.WeatherStation` patches are therefore refused, so its flagged build must drop them.

**Loading.**

- A station saved with an unregistered tide stops loading, naming it.
- A station saved without the component asks every `IFluidTideStationImporter` once: `string ImportStationTide(FluidTideRegistry tides, object nativeEntityLoader)`, given the station's `IEntityLoader`, through `ModdableFluidsHost.ImportStationTide`.
- An unregistered answer, a throwing importer or two answering importers stop loading.
- The next save writes the station's own component.
- Deep Frontier's mapping: component `DeepFrontier.WeatherStationRadioactiveTide`, property `SignalsRadioactiveTide` true, becomes `DeepFrontier.RadioactiveTide`.

### Moddable Weathers

Not implemented. With Moddable Weathers loaded and any tide registered, the configurator stops the scene with a message naming the tides. The check compares assembly names only and references no Moddable Weathers type. Moddable Weathers replaces the native hazardous weather system and transpiles the native targets above into throws.

**Design of an adapter** (Moddable Weathers 11.0.0, from Deep Frontier's `DeepFrontier.ModdableWeathers` bridge):

- **Packaging.** An assembly `ModdableFluids.ModdableWeathers`, compiled against Moddable Weathers, shipped as `Scripts/ModdableFluids.ModdableWeathers.dll.ModdableWeathers.optional`. Moddable Timberborn's `OptionalModsLoader`, which Moddable Weathers requires, loads it only when Moddable Weathers is enabled. `ModCodeStarter` never enumerates it. The Moddable Fluids build stages it like Deep Frontier's build stages its bridges (a build-script change for the lead).
- **One weather object per tide.** It would be an `IModdableHazardousWeather` (via `ModdableWeatherBase`) whose `Id` is the tide's native weather ID, multi-bound once per registered tide. `BindWeather<T, TSettings>` binds by type, and tides are only known at run time, so the adapter needs a binding by instance, or one generated type per tide. That has to be confirmed against Moddable Weathers' registry first.
- **Settings.** The save's settings stay in `ModdableFluids.TideSettings`, not in Moddable Weathers' per-type settings. Its Weather Settings dialog lists a type's attributed properties, and cannot show one row per registered tide.
- **Selection, C′.** Moddable Weathers draws each hazardous stage by integer weights.
  - Once per stage, the adapter sums the other enabled hazardous weathers' weights `O`, asking only non-tide weathers. It caches `O` for the stage, so the tides never call each other.
  - Each eligible tide then gets `O × B / (1 − B) × wᵢ / W`, rounded to an integer of at least 1, where `B` is the budget, `wᵢ` the tide's weight and `W` the eligible tides' total weight.
  - A tide gets weight 0 in the cycle after any tide (read from Moddable Weathers' `WeatherHistoryService`), before its cycles without, and after a tide earlier in the same cycle.
  - With `O = 0`, only tides can occur and the tide total is the whole stage.
- **Duration.** `GetDuration` draws uniformly from the save's settings, as the native adapter does.
- **Source effect.** While a tide's stage is active (its `Start` and `End`), the service owns the source composition, and the strength modifier uses that stage instead of the native weather.
- **Presentation.** Moddable Weathers draws its panels and sound from a `ModdableWeatherSpecs/<weather ID>.blueprint.json` per tide, which each content mod would ship. The native UI, sound, selection and restore patches are not installed under Moddable Weathers.
- **Weather Station.** Moddable Weathers does not patch the station. Its `HazardousWeatherService` returns the current or next hazardous stage's weather, so the station decorator works unchanged.

**Risks.** Each of these is why the refusal stays for now:

- **Weights.** Integer weights make the shares approximate. Deep Frontier measured under half a percentage point with the default weights.
- **Interference.** Another mod's weather that computes its weight from others' can still recurse into ours.
- **Bindings.** Per-tide binding may need generated types.
- **Coupling.** The adapter couples to Moddable Weathers' unversioned public API (`ModdableWeatherBase`, `WeatherCycleStageDecision`, `WeatherHistoryService`). It needs its own startup contract checks.
- **No probe yet.** None of this can be checked without a Mono probe against the installed Moddable Weathers 11.0.0.

### Development

`FluidTideDevModule` adds one development method per tide: "Moddable Fluids: <tide> next cycle". It forces the next cycle's hazardous weather to that tide, ignoring cycles without, the budget and the cooldown. The force is not saved.

## Evidence

- **.NET harness** (`HarnessExtensions.Tides.cs`, in `tools/test_fluid_transport.ps1`). It covers:
  - registration, freeze validation and the reflection route;
  - per-mode values, including Deep Frontier's Chill-mode parity and the vanilla anchors against the blueprints;
  - the selection draws;
  - the exact long-run shares above;
  - imports: an accepted import with unlisted tides off, null imports, every validation failure with the importer named, and two importers refused by name;
  - Weather Station imports: an accepted answer, no answer, an unregistered tide, two answers and a throwing importer.
- **Compile check** (`tools/compile-check/fluid-tides`). Runtime and Tides compiled together as `ModdableFluids.RuntimePrototype`, against the shipped (not publicized) game assemblies.
- **Mono probe** (`tools/compile-check/fluid-tides/probe`, run by `run_tides_mono.py`). It runs in the installed game's Mono, in a separate process, with the shipped Harmony, and covers:
  - the startup contract and install/uninstall per scene;
  - refusal of a second service and of a foreign patch;
  - the real `HazardousWeatherRandomizer` through the selection postfix: draws, cooldown, weighted pick and budget miss;
  - the real `HazardousWeatherService.Load` restoring a tide;
  - the UI helper prefixes, including a caller compiled after patching;
  - the new-game patch;
  - new-game, custom-mode, partial-spec and no-settings resolution;
  - the fog check;
  - the Weather Station contract (16 patched targets in all), the private activation time read on a real `WeatherStation`, the panel's private fields, and the station decorator's output rule;
  - the station's tide saved by ID through the game's persistence, an unregistered saved tide refused, and another tide system's station mode imported once;
  - a legacy import read from the save's own singleton loader and restored by the native Load, then saved through the game's `ObjectSaver` and JSON writer and reloaded without asking the importer again;
  - refusal of a save with only one of the two tide singletons.

## Not done yet

- **In-game runs.** Nothing here has run in the game.
- **Moddable Weathers adapter.** Refused visibly; a design is above.
- **Source composition by type.** The world service's source resolver composes every source as the native water source type. A tide's composition therefore also reaches source types that are not tide-overridable, while the strength modifier already classifies each source by its template.
