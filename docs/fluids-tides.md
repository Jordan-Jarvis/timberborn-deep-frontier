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
6. On a hit, one eligible tide is chosen by weight. With a single eligible tide there is no further draw. Otherwise one `Range(0, total weight)` draw is walked over the eligible tides in ordinal ID order.

Load order never matters: tides are always taken in ordinal ID order. With one installed tide the draws, including the random calls, are exactly those of Deep Frontier's `RadioactiveTideService.Choose`.

Per save:

- **Budget.** The chance per eligible cycle that the cycle becomes a tide. The default is the largest chance among the installed tides for the game's mode.
- **Weight.** Each tide's share of the budget. The default is the tide's own chance.
- **Per tide:** on or off, cycles without the tide, and duration.

When only some tides are eligible (one tide's cycles without have passed and another's have not), the eligible tides share the whole budget. Long-run shares do not depend on this, because every tide is eligible by then.

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
| `SetTideSourceStrength(tide, multiplier)` | While in progress, tide-overridable sources run at this multiple of their native strength, in (0, 1]. Optional; the default is 1. |
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
- **Strength.** `FluidTideStrengthModifier` uses the native mechanism: an `IWaterStrengthModifier` on every `WaterSource`, attached by a `TemplateModule` decorator the same way the game attaches `DroughtWaterStrengthModifier`. `WaterSource` multiplies it into `CurrentStrength` every tick. While a tide is in progress, a tide-overridable source returns the tide's multiplier, for example 0.5 for coffee; otherwise it returns 1.
- **Source types.** A source's type is found by its template name (`TemplateSpec`). A placed source whose template has no registered source type stops loading, naming the template.
- **Badwater sources.** Every native source type is tide-overridable, including badwater sources, so the coffee tide also halves them. Their badwater stays badwater.
- **Timing.** The composition and strength change in the tick the tide starts and ends. There is no ramp.

### Saving

| Key | Contents |
| --- | --- |
| Singleton `ModdableFluids.Tides` | `CurrentCycleTide` (tide ID or empty), `LastTideCycle`, `LastTideId`, `LastTideDuration` |
| Singleton `ModdableFluids.TideSettings` | `BudgetPercent`, and parallel lists `TideIds`, `Enabled`, `Weights`, `CyclesWithoutTide`, `MinDurationDays`, `MaxDurationDays` |
| Native `HazardousWeatherHistory` | each tide under its native weather ID, which gives it its own occurrence count |

`PostLoad` checks the restored tide against the native service: the same tide, cycle and duration.

A game's settings come from, in order:

1. **The save's own copy.**
   - A tide registered after the save was made is off in that save.
   - A saved tide that no installed mod registers stops loading, naming it.
2. **A new game's mode.**
   - The custom mode's tide rows, as a `FluidTideGameModeSpec` on its blueprint.
   - Any other mode derives its values from its own weather. A mode's own spec that leaves out a tide also derives that tide.
3. **A save made without tide settings.** Every tide is off. The mode such a save started from is not stored.

A save without Moddable Fluids tide state whose native history already contains a registered tide's weather ID was played under another tide system, such as Deep Frontier's own. Its loading is refused: importing that state is not implemented.

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

### Moddable Weathers

Not implemented. Moddable Weathers replaces the native hazardous weather system and transpiles the targets above into throws. With its assembly loaded and any tide registered, the configurator stops the scene with a message naming the tides. The check compares assembly names only and references no Moddable Weathers type.

The intended adapter is a Moddable Timberborn `.optional` assembly, like Deep Frontier's. It would convert all registered tides to Moddable Weathers weights once, so that each stage's tide total is the budget, split by weight, with the global cooldown. That gives the same C′ shares.

### Development

`FluidTideDevModule` adds one development method per tide: "Moddable Fluids: <tide> next cycle". It forces the next cycle's hazardous weather to that tide, ignoring cycles without, the budget and the cooldown. The force is not saved.

## Evidence

- **.NET harness** (`HarnessExtensions.Tides.cs`, in `tools/test_fluid_transport.ps1`). It covers:
  - registration, freeze validation and the reflection route;
  - per-mode values, including Deep Frontier's Chill-mode parity and the vanilla anchors against the blueprints;
  - the selection draws;
  - the exact long-run shares above.
- **Compile check** (`tools/compile-check/fluid-tides`). Runtime and Tides compiled together as `ModdableFluids.RuntimePrototype`, against the shipped (not publicized) game assemblies.
- **Mono probe** (`tools/compile-check/fluid-tides/probe`, run by `run_tides_mono.py`). It runs in the installed game's Mono, in a separate process, with the shipped Harmony, and covers:
  - the startup contract and install/uninstall per scene;
  - refusal of a second service and of a foreign patch;
  - the real `HazardousWeatherRandomizer` through the selection postfix: draws, cooldown, weighted pick and budget miss;
  - the real `HazardousWeatherService.Load` restoring a tide;
  - the UI helper prefixes, including a caller compiled after patching;
  - the new-game patch;
  - new-game, custom-mode, partial-spec and no-settings resolution;
  - the fog check.

## Not done yet

- **In-game runs.** Nothing here has run in the game.
- **Weather Station.** There is no mode per registered tide; the native station signals only drought and badtide.
- **Moddable Weathers adapter.** Refused visibly; see above.
- **Importing another tide system's state.** Deep Frontier's `DeepFrontier.RadioactiveTide` and `DeepFrontier.RadioactiveTideSettings` cannot be imported yet, so such a save is refused.
- **Source composition by type.** The world service's source resolver composes every source as the native water source type. A tide's composition therefore also reaches source types that are not tide-overridable, while the strength modifier already classifies each source by its template.
