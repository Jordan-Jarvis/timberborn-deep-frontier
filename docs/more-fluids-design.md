# More Fluids: first-release design proposal

Proposed 2026-11-09 after the user put coffee, saltwater and healing water all in the first release. All the numbers here are proposals awaiting the user's approval. They are grounded in vanilla Timberborn 1.1.2.8 data (sources below) and in the Moddable Fluids [0.1 contract](fluids-api-contract.md). No More Fluids code exists yet. This design also fixes which API capabilities have to come first.

## Shared rules

- **IDs and colours.** IDs are `MoreFluids.Coffee`, `MoreFluids.Saltwater` and `MoreFluids.HealingWater`, registered by one compiled provider, `MoreFluids.Liquids`. Colours below are linear RGBA. Alpha is how strongly a pure column covers the native water look in the shared renderer.
- **Volume per good.** Converting between world fluid and goods uses the native rate of **0.2 world volume per good**, the same as `Timberborn.WaterWorkshops.WaterGoodToWaterAmountConverter.WaterAmountConversion` and Deep Frontier's sludge.
- **Mixing.** Fluids mix by volume, as in contract 0.1. A fluid is never drinkable or irrigating merely because the engine treats its volume as non-bad water; each rule below is explicit.
- **Effects.** Each fluid's effects are independent. Healing water does not remove radioactive volume, and Deep Frontier's radiation does not cancel healing. Physical conversion happens only through declared transformations.
- **Vanilla first, no sprawl.** Effects reuse vanilla goods and needs wherever possible: `Coffee`, `Water`, `Antidote`, `Injury`, `BadwaterContamination`. The pack adds two buildings and one map object, and no new goods.
- **Tides.** Each tide's chance is defined explicitly in its data and as a per-save row on the new-game screen. Selection follows the decided policy D: independent rolls, then a weighted pick when several succeed, with a one-cycle cooldown per tide.

## Coffee (`MoreFluids.Coffee`)

| Question from the plan | Proposal |
| --- | --- |
| Exposure or consumption | Consumption only. Swimming in coffee has no effect, so beavers gain from it only through the vanilla `Coffee` good: 0.4 points of the Coffee need, which decays 0.05 a day and gives +3 wellbeing for Iron Teeth. |
| Recovery | The **Fluid Extractor** (below) with a coffee recipe: 1 `Coffee` good per 0.33 hours (the vanilla `Water` pump recipe rate), drawing 0.2 coffee volume per good. That is 3 coffee an hour without beans or logs. The Coffee Brewery makes 4 an hour from 1 bean, 1 water and log fuel. |
| Dilution | The extractor removes only the coffee component, and works only while coffee is at least 10% of the column. Below that it shows "Too dilute". |
| Water pumps | Coffee counts as potable. Water intakes accept a column while coffee is under 50% of it, and the coffee they draw becomes `Water` goods through the declared transformation `MoreFluids.CoffeeDrunkAsWater`. From 50% coffee, water intakes stop. |
| Irrigation | Coffee moistens soil like water. |
| Colour | Vanilla coffee barrel colour (0.161, 0.110, 0.090) at alpha 0.85. |
| **Coffee tide** | Water sources run at ×0.5 strength and everything they emit (the non-bad part) is coffee. Near the sources the river passes 50% coffee, so water pumps stop there: a drought with a harvestable upside. |
| Tide rows (Easy / Normal / Hard) | Chance 10 / 15 / 20%. Cycles without the tide 12 / 8 / 6. Duration 2–4 / 3–5 / 4–7 days. Cooldown 1 cycle. |

## Saltwater (`MoreFluids.Saltwater`)

| Question from the plan | Proposal |
| --- | --- |
| Model | A volumetric component in contract 0.1: saltwater is a fluid, and mixing it with fresh water dilutes it. Evaporation removes the mixture in proportion, so it does not concentrate salt. Concentrating brine needs the later dissolved-salt model and a new contract. |
| Drinking | Not potable. Water intakes refuse a column with 10% or more saltwater (a brackish limit). Deep Frontier's radioactive guard refuses at 0.5%. |
| Irrigation | Saltwater does not moisten soil. A column with 10% or more saltwater blocks growth on the soil it would irrigate, like badwater. This needs the API's irrigation adapter, which follows Deep Frontier's moisture-input hook pattern. |
| Desalination | The **Desalinator**, one new building: 1 worker, 60 hp. Each `Water` good costs 0.3 saltwater volume (about 67% recovery). The remaining 0.1 leaves through the declared transformation `MoreFluids.DesalinationBrine`. |
| Colour | (0.15, 0.45, 0.55) at alpha 0.35: a subtle teal over the native water. |
| **Salt tide** | Sources keep their strength, and everything they emit (the non-bad part) is saltwater. The river turns salty: water pumps and irrigation fail until the salt flushes downstream or is desalinated. |
| Tide rows (Easy / Normal / Hard) | Chance 10 / 15 / 20%. Cycles without the tide 10 / 7 / 5. Duration 2–4 / 4–8 / 10–20 days (vanilla badtide is 1–3 / 4–8 / 15–30). Cooldown 1 cycle. |

## Healing water (`MoreFluids.HealingWater`)

| Question from the plan | Proposal |
| --- | --- |
| Conditions | Exposure: a beaver standing in a column with at least 20% healing water recovers `Injury` and `BadwaterContamination` at +0.25 a day each. Vanilla Injury recovers by itself at +0.1 a day; one `Antidote` gives +0.125 to BadwaterContamination. |
| Mixed hazards | Healing water never removes another fluid. In a column that is also radioactive, Deep Frontier's irradiation and the healing apply independently, each from its own share. |
| Recovery | The Fluid Extractor with a healing recipe: 1 vanilla `Antidote` per 0.4 healing volume, 1 every 2 hours. That equals the vanilla Antidote recipe's output (2 per 2 hours) without its paper, dandelions and berries. |
| Drinking and irrigation | Potable, with the same rule as coffee: drawn healing water becomes `Water` goods below 50% (`MoreFluids.HealingDrunkAsWater`). It irrigates like water. |
| Colour | (0.55, 0.95, 0.75) at alpha 0.5. Contract 0.1 does not support emissive glow. |
| Source | No tide: a hazard slot should not hold a blessing. The **Healing Spring** is a map object for map makers: a spring of 0.4 strength that emits only healing water. A player-buildable spring is left for later. |

## Buildings and content count

| Content | Purpose | Notes |
| --- | --- | --- |
| Fluid Extractor | Intake with one recipe per registered extractable fluid: coffee to `Coffee`, healing water to `Antidote` | One building rather than one per fluid. Its pipe and depth follow the Deep Water Pump. |
| Desalinator | Saltwater to `Water` | The only salt-specific building. |
| Healing Spring (map object) | Healing source | Map editor only. |
| Coffee tide, Salt tide | Per-save chance rows | Registered through Moddable Fluids tide registration (still to be built). |

## Long-run tide shares under policy D (Normal)

Computed with [model_tide_selection.py](../tools/model_tide_selection.py), using the native badtide streak rule and one-cycle cooldowns:

| Installed | Drought | Badtide | Radioactive | Coffee | Salt |
| --- | ---: | ---: | ---: | ---: | ---: |
| Vanilla | 59.7% | 40.3% | – | – | – |
| Deep Frontier | 48.1% | 31.9% | 20.0% | – | – |
| More Fluids | 45.3% | 30.1% | – | 12.3% | 12.3% |
| Deep Frontier + More Fluids | 35.8% | 23.8% | 18.5% | 11.0% | 11.0% |

Each player sets every tide's chance per save.

## API capabilities this needs, in build order

1. **Intake conversion and refusal policies.** The Fluid Extractor, the Desalinator and the water-pump refusal thresholds. Each conversion is a declared transformation in the ledgers.
2. **Tide registration.** The policy-D selection, per-tide new-game rows, presentation and source emission override, plus the Moddable Weathers adapter.
3. **Shared rendering on the GPU.** The CPU half is built; see the [native adapter document](fluids-native-adapter.md#shared-rendering).
4. **Exposure context.** Healing water reads each beaver's column, much as `RadiationExposure` does in Deep Frontier.
5. **Irrigation policy.** Saltwater blocks growth through the same native moisture-input hook that Deep Frontier patches today.

## Decisions requested

- The numbers above, especially the water-pump thresholds (coffee and healing water 50%, saltwater 10%), the Coffee tide's ×0.5 strength, and the Desalinator's 67% recovery.
- Whether coffee and healing water drawn by water pumps should become water (proposed), or block the pump at a lower share.
- Whether healing water should also get a player-buildable spring in the first release.
