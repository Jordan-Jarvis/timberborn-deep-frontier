# Moddable Fluids tides

Tide registration for Moddable Fluids, started 2026-11-09. A tide is a hazardous weather registered by a content mod. While it is the cycle's weather and in progress, every tide-overridable water source emits the tide's fluids, and may run at reduced strength. Moddable Fluids owns the one native weather adapter for all registered tides, and with Moddable Weathers one Moddable Weathers weather per tide. Content mods register tides; they do not patch the native weather.

Status:

- **Implemented and tested outside the game.** The registration API, the validation at registry freeze and the selection rule are covered by the .NET harness. The game-side adapter (`src/ModdableFluids/Tides`) compiles against the shipped game assemblies, and its native parts pass a probe in the game's own Mono (see [Evidence](#evidence)).
- **Moddable Weathers adapter implemented and tested outside the game** (decision 9a, 2026-11-09): the optional assembly `ModdableFluids.ModdableWeathers` passes a probe in the game's Mono against the installed Moddable Weathers 11.0.0 (see [Moddable Weathers](#moddable-weathers)).
- **Not yet run in game.** It binds where the scene owner does (every game in which a mod registers a fluid, and the worker fixture), and only when a tide is registered. The new-game rows follow the same rule in the main menu.

## Selection policy C′

User decision, 2026-11-09: tides split one shared hazard budget. Installing more tide mods therefore does not make a game harder, and a vanilla-only or Deep-Frontier-only game stays exactly as before. Each tide has a weight within the budget, shown on the new-game screen. The rule is `FluidTideSelection.Select`, a pure function in the `ModdableFluids` assembly.

The native drought or badtide draw runs first, unchanged. The rule then decides whether that cycle's hazardous weather becomes a tide:

1. Cycle 1 keeps the native weather; tides start from cycle 2 (`FluidTideRules.EarliestCycle`).
2. A tide forced from the development menu is chosen. It must be enabled in the save.
3. **Global cooldown.** The cycle right after any tide keeps the native weather (`CooldownCycles` = 1).
4. The eligible tides are the save's enabled tides whose cycles without tide have passed. If there are none, the native weather stays.
5. One draw with the cycle's tide chance p (below). When every enabled tide is eligible, p is the budget and the draw is `CheckProbability(budget / 100)`. A miss keeps the native weather.
6. On a hit, one eligible tide is picked by weight. With a single eligible tide there is no further draw. Otherwise one `Range(0, total eligible weight)` draw is walked over the eligible tides in ordinal ID order.

Load order never matters: tides are always taken in ordinal ID order. With one installed tide the draws, including the random calls, are exactly those of Deep Frontier's `RadioactiveTideService.Choose`.

Per save:

- **Budget.** The chance per eligible cycle that the cycle becomes a tide. The default is the largest chance among the installed tides for the game's mode.
- **Weight.** Each tide's share of the budget. The default is the tide's own chance.
- **Per tide:** on or off, cycles without the tide, and duration.

**Early cycles** (user decisions 1b and 1c, 2026-11-09). With B the budget, W and m the total and largest weight of the enabled tides, and We and me those of the eligible tides, the cycle's tide chance is

p = B × min(We ÷ W, me ÷ m), split by weight over the eligible tides.

- **1b.** Each eligible tide gets at most its own slice of the budget, B × w ÷ W. A tide that cannot occur yet leaves its slice to the native weather.
- **1c.** The cycle gets at most B × me ÷ m. With the default weights (the chances) and budget (the largest chance), that is the largest chance among the eligible tides. So no cycle is harder than the hardest eligible tide alone, for any set of chances.
- **Raised budget.** A budget the player raised above the largest chance scales the cap with it.
- **Long run.** Every tide is eligible, p is the budget exactly, and the shares are unchanged. The model asserts the long-run shares, and that chances 50, 10 and 10 with only the two 10% tides eligible give 10%.

On Normal, a cycle right after a non-tide cycle becomes a tide with this chance (cycles without: radioactive 14, coffee 8, salt 7):

| Cycle | Deep Frontier | More Fluids | Deep Frontier + More Fluids |
| ---: | ---: | ---: | ---: |
| 8 (salt only) | 0% | 7.5% | 6.8% |
| 9–14 (coffee and salt) | 0% | 15.0% | 13.6% |
| 15 on (all) | 25.0% | 15.0% | 25.0% |

For these installs the 1c cap (15%) does not bind. It does bind for chances 50, 10 and 10 with only the two 10% tides eligible: the cycle gets 10%, not 50 × 20 ÷ 70 = 14.3%.

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
- For Moddable Weathers, a `ModdableWeatherSpecs/<native weather ID>.blueprint.json` ([Moddable Weathers](#content-each-tide-mod-supplies-under-moddable-weathers)).

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

The scene's tide owner is an `IFluidTideScene`, bound once per scene:

- **Without Moddable Weathers:** `FluidTideService`, the native binding described below.
- **With Moddable Weathers:** the adapter in the optional assembly `ModdableFluids.ModdableWeathers` (see [Moddable Weathers](#moddable-weathers)). `FluidTidesConfigurator` then binds neither `FluidTideService` nor `FluidTideUi`, and stops the scene, naming the tides and the missing file, if the adapter assembly is not loaded.

Both bindings share the save data (`FluidTideSaveData`), the strength modifier, the Weather Station decorator with its patches, and the development module. The static Harmony patches reach the owner through `FluidTideScenes.Current`, set by its constructor and cleared on unload; a second owner is refused.

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

**Foreign patches.** Any other Harmony owner on a target is refused before anything is installed, naming each owner. One example is Deep Frontier's shipped radioactive tide (`DeepFrontier.RadioactiveTide`). A tide of Deep Frontier's must then come from its Moddable Fluids build (`DEEP_FRONTIER_MODDABLE_FLUIDS`), which registers through this API. Moddable Weathers' transpilers no longer meet this check: with Moddable Weathers loaded the native binding is not bound.

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
   - A tide registered after the save was made is added on at its defaults for the save's mode (decision 3b; rule below).
   - A saved tide that no installed mod registers stops loading, naming it.
2. **An importer.** A loaded save (not a new game) with neither singleton asks every `IFluidTideImporter` once (see [Importing another tide system's state](#importing-another-tide-systems-state)).
3. **A new game's mode.**
   - The custom mode's tide rows, as a `FluidTideGameModeSpec` on its blueprint.
   - Any other mode derives its values from its own weather. A mode's own spec that leaves out a tide also derives that tide.
4. **A loaded save without tide settings that no importer reads.** Every tide gets its defaults for the save's mode, as a new game of that mode would (decision 3b).

**The save's mode** (decision 3b). A save does not store the mode it started from, but it stores that mode's weather. `FluidTideSettingsStore.SavedModeWeather` reads it from the native singletons every 1.1.2.8 save writes:

- `TemperateWeatherDurationService`: `Min`/`MaxTemperateWeatherDuration`;
- `DroughtWeather`: `Min`/`MaxDroughtDuration`;
- `BadtideWeather`: `Min`/`MaxBadtideWeatherDuration`, `ChanceBadtideWeather`.

These are the values the native Customize screen would show. The per-mode rule then applies to them. A save missing them is refused.

**Adding tides to a saved game** (`FluidTideModes.AddMissing`, decision 3b):

- Each tide the save does not list starts at its defaults for the save's mode: on when the mode has hazardous weather, with weight equal to its chance.
- The budget becomes the larger of the save's budget and the largest chance among the added tides that are on.
- Tides the save lists keep their settings, and each added tide is logged.

The save therefore never gets a budget above both its own and the added content's own default. With 1b, no cycle's tide chance exceeds that budget. For example, More Fluids added to a Normal Deep Frontier save keeps the budget at 25%, and the long-run shares are those of a new game with both. An importer's result is unchanged: tides the import does not list stay off.

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

Implemented 2026-11-09 (decision 9a) for Moddable Weathers 11.0.0. Not yet run in game; the [in-game checks](#in-game-checks-under-moddable-weathers) are listed below. With Moddable Weathers loaded, Moddable Weathers draws, saves, shows and starts every tide as one of its hazardous weathers; Moddable Fluids supplies their weights, durations and source effect. No native weather method is patched.

**Packaging.** The optional assembly `ModdableFluids.ModdableWeathers` (`src/ModdableFluids/ModdableWeathers`, asmdef `src/ModdableFluids/Authoring/ModdableFluids.ModdableWeathers.asmdef`):

- It ships as `Scripts/ModdableFluids.ModdableWeathers.dll.ModdableWeathers.optional`. Moddable Timberborn's `OptionalModsLoader`, which Moddable Weathers requires, loads it only while Moddable Weathers is enabled, and the game's `ModCodeStarter` never sees it.
- `tools/build_moddable_fluids.ps1` stages it like the other assemblies, with the installed Workshop `ModdableWeathers.dll`, `ModdableTimberborn.dll` and `TimberUi.dll` as precompiled references, as Deep Frontier's staging does.
- `ModdableFluidsBatchBuild.PackageOptionalAssembly` renames the builder's DLL, as Deep Frontier's batch build does.
- `tools/verify_moddable_fluids_package.ps1` requires the `.optional` file and no plain DLL. It requires that no other package assembly references Moddable Weathers, Moddable Timberborn or TimberUi, and it runs the adapter's Mono probe against the official copies.
- The main assemblies check for Moddable Weathers by assembly name only. With Moddable Weathers loaded and the adapter missing, `FluidTidesConfigurator` stops the scene, naming the tides and the file.

**Binding.** `FluidTideModdableWeathersConfigurator` (Game context) binds under the native binding's condition (`FluidTidesConfigurator.Binds`):

- It first runs the startup contract (below).
- It binds `FluidTideModdableWeathersService` as the scene's `IFluidTideScene`. Its constructor takes nothing Moddable Weathers builds from its registry. Under Moddable Weathers, `HazardousWeatherService` and `GameCycleService` (through its `CycleDurationService`) are built from the registry, the registry from the tide weathers, and the weathers from the service. So the service resolves them, and the registry and history, from the container on first use.
- It binds one weather per tide with Moddable Weathers' own `BindWeather<T>`. Moddable Weathers binds by type, so the weathers are a fixed set of classes, `FluidTideWeather0` … `FluidTideWeather7`. Class i takes the i-th tide in ordinal ID order.
- More than eight tides stop the scene, naming them.

**The weathers.** Each is a `ModdableWeatherBase` and `IModdableHazardousWeather`:

- **ID.** Its `Id` is the tide's native weather ID, so Moddable Weathers' history, the Weather Station and a converted native save all name it the same way.
- **Spec.** Its `Load` requires the `ModdableWeatherSpec` with that ID, naming the missing `ModdableWeatherSpecs/<ID>.blueprint.json` and its provider. The spec's `DisplayLoc` must be the tide's name key.
- **On/off.** `Enabled` is the save's on/off for the tide. Moddable Weathers neither weighs nor offers a disabled weather.
- **Duration.** `GetDuration` draws whole days, uniform over the save's shortest to longest tide, as the native binding does. Moddable Weathers then applies its stage length multiplier.
- **Settings.** They stay in `ModdableFluids.TideSettings`, from the new-game screen's tide rows, which work unchanged under Moddable Weathers. Moddable Weathers' Weather Settings dialog lists the tides with "no settings".

**Selection.** Moddable Weathers draws each hazardous stage of a cycle in proportion to the integer `GetChance` of its enabled hazardous weathers (`WeatherGenerator.DecideWeather`). The first tide asked for a stage weighs all tides at once; the others read the result:

1. **O.** The summed `GetChance` of the stage's other enabled hazardous weathers, as `DecideWeather` adds them.
2. **The last tide.** An earlier stage of this cycle with a tide, else the latest cycle with a tide stage in Moddable Weathers' history (`WeatherHistoryRegistry`, by raw weather ID).
3. **The weights.** `FluidTideSelection.StageWeights`, the C′ rule as integers (next section). Eligibility is `Select`'s: cycle 2 on, the one-cycle global cooldown, on/off and cycles without. At most one tide per cycle: a later hazardous stage of a cycle with a tide gets none.
4. **Recursion.** A weather asked for its weight that asks the tides for theirs in turn is refused, naming it. Deep Frontier's own unflagged radioactive tide weather is one: it weighs itself against the others, as the tides do.
5. **Load-time dry run.** At `PostLoad` the adapter weighs one hazardous stage of the next cycle without drawing, so a recursing weather, a negative weight or weights beyond the integer roll stop the load, not the first cycle generated in play.

The development method ("Moddable Fluids: <tide> next cycle") regenerates the next cycle with the tide in its first hazardous stage, as Moddable Weathers regenerates future cycles after its settings dialog. It fails when the regenerated cycle has no hazardous stage.

**Source effect.** While a tide weather is `Active` (Moddable Weathers starts and ends it with its stage, and starts it again when a save loads inside it), the service owns the source composition and the strength modifier applies the tide's multiplier, as in the native binding. Two active tides are refused.

**Presentation.** Moddable Weathers draws the panels, banner, sky fog and start sound from the tide's `ModdableWeatherSpec` and `ModdableWeatherSkySpec`, with its own generic texts ("<name> approaching" and so on). The tide's own notification texts and `FluidTideUi` are not used; the native `SunSpec` fog entries are not read. Moddable Weathers' weather modifiers (drought, badtide and the rest) apply to a tide only if the player associates them in its dialog.

**Weather Station.** Moddable Weathers leaves the station native. Its replacing `HazardousWeatherService` returns the cycle's current or next hazardous stage's weather, which the station samples; the decorator recognises a tide by its weather ID. The four station patches are installed per scene (`FluidTideStationPatches`) and removed on unload, after the same startup contract as the native binding's.

**Saving.**

- **Same keys.** Both singletons of the native binding, through the same `FluidTideSaveData`; imports and a saved station's tide work as there.
- **History of record.** Moddable Weathers' history is the state of record. Each save writes the native binding's state derived from it:
  - the last tide is the latest tide stage in this or an earlier cycle, with its days;
  - the cycle's tide is the current or next hazardous stage's.
- **Without Moddable Weathers.** A save made under Moddable Weathers therefore loads with the native binding too, if Moddable Weathers' own saved weather allows it.
- **Saved state must agree.** A loaded state, saved by either binding or imported, must equal the one derived from the history, or loading stops with both. This is how a save played without Moddable Weathers is checked after Moddable Weathers converts its native history.
- **Another tide system.** A loaded save without tide state whose history holds a registered tide stops loading, as in the native binding.

**What differs from the native binding:**

- **Cycles.** Moddable Weathers generates each cycle one cycle ahead and may give a cycle several hazardous stages. Each stage is weighed; a cycle has at most one tide.
- **Long-run shares.** Moddable Weathers has no native badtide streak rule, and its drought and badtide weights are its own settings, so the long-run table above (native weather) does not apply.
- **Integer weights.** The stage's chances are approximate (next section).
- **Converted saves.** A save converted mid-tide from the native weather gets Moddable Weathers' drought modifier on its current hazardous stage. Moddable Weathers' history conversion attaches it to every converted stage.
- **Texts.** The tide's own notification texts are not shown (Presentation above).

#### Integer weights

`FluidTideSelection.StageWeights(cycle, lastTideCycle, settings, forced, O)`, in the API assembly. With p = Pn ÷ Pd the cycle's tide chance from `Select` (B × min(We ÷ W, me ÷ m)) and n eligible tides:

- **The total.** The tides together get K, the integer nearest to X = O × p ÷ (1 − p) (halves up), and at least n. So K ÷ (O + K) ≈ p.
- **The split.** K is split by weight with the largest-remainder method, ties to the earlier tide in ordinal order. A tide whose share rounds to 0 gets one unit from the largest share, so every eligible tide can occur.
- **O = 0.** No other hazardous weather can occur in the stage: the weights are the tides' own, so a tide is certain and picked as `Select` picks it. (Integer weights cannot express "no hazardous weather" with probability 1 − p.)
- **p = 1** (budget 100%, every tide eligible). K = 2³¹ − 1 − O; the other weathers keep O ÷ (2³¹ − 1).
- **Forced tide.** It gets 2³¹ − 1 − O, the others 0.
- **Overflow.** O + K never exceeds the int Moddable Weathers sums into; larger weights stop the game, naming them.

Worst-case error, with Q = K ÷ (O + K) the stage's tide chance and qᵢ = K × wᵢ ÷ We a tide's exact share of K:

- **The stage's tide chance.** When X ≥ n − ½ (the other weathers weigh at least about (n − ½)(1 − p) ÷ p), |K − X| ≤ ½. Then |Q − p| ≤ (1 − p)² ÷ (2O − (1 − p)), about (1 − p)² ÷ 2O. Below that the tides get n units, so for example one tide against O = 1 occurs in half the stages.
- **Each tide.** Its chance kᵢ ÷ (O + K) is off its exact one, p × wᵢ ÷ We, by at most |kᵢ − qᵢ| ÷ (O + K) + (wᵢ ÷ We) × |Q − p|. |kᵢ − qᵢ| is under 1, or under 1 + z when z tides' exact shares are below one unit (they take a unit each from the largest).
- **The shipped tides.** Deep Frontier and More Fluids on Easy, Normal and Hard, in every eligibility phase, with Moddable Weathers' default weights (drought 60 alone before badtides start, drought 60 + badtide 40 after). The stage's tide chance is within 0.59 percentage points, each tide within 1.02 points. The worst total is Normal, Deep Frontier + More Fluids, cycles 9–14, drought alone: K = 9 gives 13.0% for 13.6%. The worst tide is the same stage: salt gets 4 of 9 units, 5.8% for 6.8%; coffee gets 5, 7.2%.
- **Evidence.** The harness checks the bound on 109,440 cases, eligibility parity with `Select` (340 cases) and the shipped table. Its observations list every row (`moddableWeathersStageWeights`).

#### Startup contract

`FluidTideModdableWeathersContract.Verify`, before anything is bound. Every member is looked up by name, so a renamed type cannot fail the JIT first. Every change is reported at once, naming the installed version (read from Moddable Weathers' manifest) and the version the adapter was written for (11.0.0). It checks:

- **Weathers.** `IModdableWeather`'s members; `IModdableHazardousWeather : IModdableWeather, IHazardousWeather`; `ModdableWeatherBase`'s constructor and its abstract members (exactly `Id`, `GetChance`, `GetDuration`); a virtual `Load` reading `SpecsById`; a virtual `Enabled`; `Start` and `End` setting `Active`.
- **Specs.** `ModdableWeatherSpecService.SpecsById`, and the spec's `Id` and `DisplayLoc`.
- **Selection.** The registry's multi-bound constructor, `HazardousWeathers` and `WeathersById`, and its `Load` ordering with `OrderBy` on `Spec`. `WeatherGenerator.DecideWeather` weighing the enabled weathers by `GetChance`. `EnsureWeatherGenerated`. The stage and cycle decision properties.
- **History.** `WeatherHistoryRegistry`'s indexer, `CycleCount` and `ClearFutureEntries`; `WeatherCycle` and `WeatherCycleStage`; `WeatherHistoryService.GetWeatherCycle` and `UpdateReferences`.
- **Lifecycle and service.** `WeatherCycleService.TransitionWeather` starting and ending the weathers. `[ReplaceSingleton] ModdableHazardousWeatherService : HazardousWeatherService` with its replacing `CurrentCycleHazardousWeather`.
- **Binding.** `BindWeather<T>(Configurator) where T : class, IModdableWeather`.

A Moddable Weathers update that removes a type the adapter's weathers derive from fails earlier, when the game enumerates the adapter's types; the game's log then names the assembly.

#### Content each tide mod supplies under Moddable Weathers

A `ModdableWeatherSpecs/<native weather ID>.blueprint.json` with a `ModdableWeatherSpec` (and a `ModdableWeatherSkySpec`), in the shape of Moddable Weathers' own. Without Moddable Weathers the game logs its two unknown keys and never reads it.

| Mod | File | Order | Sound |
| --- | --- | ---: | --- |
| Deep Frontier | `ModdableWeatherSpecs/RadioactiveTideWeather` (already shipped) | 35 | badtide |
| More Fluids | `ModdableWeatherSpecs/MoreFluidsCoffeeTideWeather` | 36 | drought |
| More Fluids | `ModdableWeatherSpecs/MoreFluidsSaltTideWeather` | 37 | badtide |

The harness checks each against its tide's registration: ID, name and description keys, the three sprites and the start sound. It also checks that the blink background is one Moddable Weathers' own weathers use, that the order is free, and that More Fluids' sky equals its `SunSpec` fog. Deep Frontier's spec matches its flagged registration.

#### In-game checks under Moddable Weathers

Nothing here has run in game. In order:

1. **Moddable Weathers + Moddable Fluids + More Fluids.**
   - The log shows the optional DLL loaded by `[ModdableTimberborn.OptionalMods]`, then "Tides run as Moddable Weathers weathers".
   - A new Normal game: the tide rows on the new-game screen; Moddable Weathers' Weather Settings lists Coffee tide and Salt tide with no settings.
   - Dev "Moddable Fluids: MoreFluids.CoffeeTide next cycle", then jump to the hazardous stage: the coffee icon, progress bar, banner, fog and drought alarm; sources at half strength emitting coffee; both stop when the stage ends.
   - A Weather Station in coffee mode signals during the coffee tide only.
   - Save inside the tide and reload: the tide is still active and emitting.
   - Let a few cycles run: tides appear only from their cycles without, never two cycles in a row.
   - Disable Moddable Weathers and load that save: the native binding takes over without refusal.
2. **The same with flagged Deep Frontier** (`tools/build_deep_frontier_moddable_fluids.ps1`, which leaves out Deep Frontier's own Moddable Weathers bridge).
   - All three tides are listed.
   - The radioactive tide from its dev method shows Deep Frontier's spec.
   - A save from unflagged Deep Frontier played without Moddable Weathers loads (imported).
   - Unflagged Deep Frontier with its own bridge plus More Fluids must stop the load, naming `RadioactiveTideWeather`.

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
- **Compile check** (`tools/compile-check/fluid-tides`). Runtime and Tides compiled together as `ModdableFluids.RuntimePrototype`, against the shipped (not publicized) game assemblies. `tools/compile-check/fluid-moddable-weathers` compiles the optional adapter against it, the shipped game assemblies and the installed Workshop Moddable Weathers 11.0.0, Moddable Timberborn and TimberUi.
- **Harness, Moddable Weathers** (`HarnessExtensions.Tides.cs`): `StageWeights` (the shipped weights, edges, refusals, the bound on 109,440 cases, eligibility parity with `Select`, the shipped error table) and every shipped `ModdableWeatherSpec` against its tide. `HarnessExtensions.MoreFluids.cs` checks More Fluids' two specs against Moddable Weathers' own spec types.
- **Mono probe, Moddable Weathers** (`tools/compile-check/fluid-moddable-weathers/probe`, run by `run_moddable_weathers_mono.py` in `tools/test_fluid_transport.ps1`). It runs in the installed game's Mono with the installed Moddable Weathers, Moddable Timberborn and TimberUi (51 checks):
  - the contract against Moddable Weathers 11.0.0, no main assembly referencing a Workshop mod, and no constructor dependency that would form a cycle through Moddable Weathers' registry;
  - the tide weathers on Moddable Weathers' real `ModdableWeatherBase`, registry and history, beside its real drought and badtide weathers;
  - the stage weights as `DecideWeather` asks them: cooldown, one tide per cycle, a second hazardous stage, the per-stage cache, a recursing weather and an overflowing roll refused;
  - durations, the source effect following `Active`, and the Weather Station by weather ID;
  - saving the derived state, reloading it, a native-binding state accepted, a disagreeing state and another tide system's history refused;
  - a missing or misnamed spec named, and the station patches installed and removed per scene.
  - `WeatherGenerator` itself draws with `UnityEngine.Random`, an engine call, so the probe mirrors its loop rather than running it. `tools/verify_moddable_fluids_package.ps1` reruns the probe against the official package's DLLs.
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
- **Moddable Weathers in game.** The adapter is not yet run in game; see [its in-game checks](#in-game-checks-under-moddable-weathers).
- **Source composition by type.** The world service's source resolver composes every source as the native water source type. A tide's composition therefore also reaches source types that are not tide-overridable, while the strength modifier already classifies each source by its template.
