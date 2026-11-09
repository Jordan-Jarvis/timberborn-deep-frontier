# Moddable Fluids tides

Tide registration for Moddable Fluids, started 2026-11-09. A tide is a hazardous weather registered by a content mod. While it is the cycle's weather and in progress, every tide-overridable water source emits the tide's fluids, and may run at reduced strength. Moddable Fluids owns the one native weather adapter for all registered tides. Content mods register tides; they do not patch the native weather.

Status: the registration API, the validation at registry freeze and the selection rule are implemented and covered by the .NET harness. The game-side adapter is described below with its own status. Nothing here has been run in game.

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
