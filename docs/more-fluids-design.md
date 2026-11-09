# More Fluids: first-release design

The user approved these numbers on 2026-11-09, chose shared-budget tide selection (policy C′), approved the geyser, and asked for a player-buildable Healing Spring. Everything here is grounded in vanilla Timberborn 1.1.2.8 data (Blueprints.zip, Localizations.zip) and the Moddable Fluids [0.1 contract](fluids-api-contract.md). Design is not proof: nothing here has been verified in game.

## Shared rules

- **IDs and colours.** IDs are `MoreFluids.Coffee`, `MoreFluids.Saltwater` and `MoreFluids.HealingWater`, registered by one compiled provider, `MoreFluids.Liquids`. Colours below are linear RGBA. Alpha is how strongly a pure column covers the native water look in the shared renderer.
- **Volume per good.** Converting between world fluid and goods uses the native rate of **0.2 world volume per good**, the same as `Timberborn.WaterWorkshops.WaterGoodToWaterAmountConverter.WaterAmountConversion` and Deep Frontier's sludge.
- **Mixing.** Fluids mix by volume, as in contract 0.1. A fluid is never drinkable or irrigating merely because the engine treats its volume as non-bad water; each rule below is explicit.
- **Effects.** Each fluid's effects are independent. Healing water does not remove radioactive volume, and Deep Frontier's radiation does not cancel healing. Physical conversion happens only through declared transformations.
- **Vanilla first, no sprawl.** Effects reuse vanilla goods and needs: `Coffee`, `Water`, `Antidote`, `Injury`, `BadwaterContamination`. The pack adds three buildings and two map objects, and no new goods.
- **Factions.** Folktails and Iron Teeth. Deep Frontier is Iron Teeth only; More Fluids is not. In vanilla, `Coffee` is an Iron Teeth good and `Antidote` a Folktails good (`GoodCollection.IronTeeth` and `.Folktails`), while `Injury` and `BadwaterContamination` are common needs. So each faction's Fluid Extractor has the recipe its faction can use; everything else is the same for both.
- **Tides.** Policy C′: registered tides share one hazard budget and split it by their weights, with a global cooldown (no tide in the cycle after any tide). Each tide's weight is a per-save row on the new-game screen. Moddable Fluids' tide registration owns the selection; see `docs/fluids-tides.md` for the rule and the long-run shares.

## Coffee (`MoreFluids.Coffee`)

| Question | Decision |
| --- | --- |
| Exposure or consumption | Consumption only. Swimming in coffee has no effect, so beavers gain from it only through the vanilla `Coffee` good: 0.4 points of the Coffee need, which decays 0.05 a day and gives +3 wellbeing for Iron Teeth. |
| Recovery | The Iron Teeth **Fluid Extractor**: 1 `Coffee` good per 0.33 hours (the vanilla `Water` recipe rate), drawing 0.2 coffee volume per good. That is 3 coffee an hour without beans or logs. The Coffee Brewery makes 4 an hour from 1 bean, 1 water and log fuel. |
| Dilution | The extractor removes only the coffee component, and works only while coffee is at least 10% of the column. Below that it shows "Too dilute". |
| Water pumps | Coffee counts as potable. Water intakes accept a column while coffee is under 50% of it, and the coffee they draw becomes `Water` goods through the declared transformation `MoreFluids.CoffeeDrunkAsWater`. From 50% coffee, water intakes stop. |
| Irrigation | Coffee moistens soil like water. |
| Colour | Vanilla coffee barrel colour (0.161, 0.110, 0.090) at alpha 0.85. |
| **Coffee tide** | Water sources run at ×0.5 strength and everything they emit (the non-bad part) is coffee. Near the sources the river passes 50% coffee, so water pumps stop there: a drought with a harvestable upside. |
| Tide rows (Easy / Normal / Hard) | Chance 10 / 15 / 20%, the tide's default weight. Cycles without the tide 12 / 8 / 6. Duration 2–4 / 3–5 / 4–7 days. |

## Saltwater (`MoreFluids.Saltwater`)

| Question | Decision |
| --- | --- |
| Model | A volumetric component in contract 0.1: saltwater is a fluid, and mixing it with fresh water dilutes it. Evaporation removes the mixture in proportion, so it does not concentrate salt. Concentrating brine needs the later dissolved-salt model and a new contract. |
| Drinking | Not potable. Water intakes refuse a column with 10% or more saltwater (a brackish limit). Deep Frontier's radioactive guard refuses at 0.5%. |
| Irrigation | Saltwater does not moisten soil. A column with 10% or more saltwater blocks growth on the soil it would irrigate, like badwater. |
| Desalination | The **Desalinator**: each `Water` good costs 0.3 saltwater volume (about 67% recovery). The remaining 0.1 is brine and leaves the world: all 0.3 appears in the tick's extraction losses under the requester `MoreFluids.Desalinator`. |
| Colour | (0.15, 0.45, 0.55) at alpha 0.35: a subtle teal over the native water. |
| **Salt tide** | Sources keep their strength, and everything they emit (the non-bad part) is saltwater. The river turns salty: water pumps and irrigation fail until the salt flushes downstream or is desalinated. |
| Tide rows (Easy / Normal / Hard) | Chance 10 / 15 / 20%, the tide's default weight. Cycles without the tide 10 / 7 / 5. Duration 2–4 / 4–8 / 10–20 days (vanilla badtide is 1–3 / 4–8 / 15–30). |

## Healing water (`MoreFluids.HealingWater`)

| Question | Decision |
| --- | --- |
| Conditions | Exposure: a beaver standing outside buildings in a column with at least 20% healing water recovers `Injury` and `BadwaterContamination` at +0.25 a day each. Vanilla Injury recovers by itself at +0.1 a day; one `Antidote` gives +0.125 to BadwaterContamination. Bots have neither need. |
| Mixed hazards | Healing water never removes another fluid. In a column that is also radioactive, Deep Frontier's irradiation and the healing apply independently, each from its own share. |
| Recovery | The Folktails **Fluid Extractor**: 0.4 healing volume per vanilla `Antidote`, 2 Antidote every 2 hours, the vanilla Antidote recipe's output without its paper, dandelions and berries. (The proposal said both "1 every 2 hours" and "the vanilla recipe's output, 2 per 2 hours"; the build follows the second.) |
| Drinking and irrigation | Potable, with the same rule as coffee: drawn healing water becomes `Water` goods below 50% (`MoreFluids.HealingDrunkAsWater`). It irrigates like water. |
| Colour | (0.55, 0.95, 0.75) at alpha 0.5. Contract 0.1 does not support emissive glow. |
| Sources | No tide: a hazard slot should not hold a blessing. The **Healing Spring** map object (strength 0.4) for map makers, and the player-built **Healing Spring** below (strength 0.2 at full power). |

## Geyser

A map object for map makers: a native water source of strength 2.0 that erupts for 3 hours of every 18 at three times its strength (half-hour ramps up and down) and is dormant in between, so its mean strength is 0.83. Each geyser's phase comes from its saved entity ID, so geysers do not erupt together. It ignores droughts and badtides: a bursty, drought-proof supply of fresh water.

## Objects

All five templates are prefixed `MoreFluids` so they cannot collide with vanilla or other mods. Paths follow Deep Frontier's layout under `src/MoreFluids/Data`; resource paths in blueprints omit the extension. Block layouts list `X, Y, Z` with Z up, as in `BlockObjectSpec`.

### Fluid Extractor

| Field | Value |
| --- | --- |
| Templates | `MoreFluidsFluidExtractor.Folktails`, `MoreFluidsFluidExtractor.IronTeeth` |
| Footprint | The vanilla Deep Badwater Pump (Iron Teeth) and Badwater Pump (Folktails) blocks exactly: size 2 × 3 × 3, `BaseZ` 1, entrance (1, −1, 1), the Deep Water Pump's footprint and intake with a fully occupied top layer. Ground blocks at z = 1 for y = 0–1; the intake overhang (0, 2, 1) sits over water (`MatterBelow` Air). |
| Water input | (0, 2, −1); pipe `MaxDepth` 6, like the Deep Water Pump. Pipe segments reuse vanilla prefabs: `Buildings/Water/BadwaterPump/BadwaterPumpPipeSegment.Folktails` and `Buildings/Water/DeepBadwaterPump/DeepBadwaterPumpPipeSegment.IronTeeth`. |
| Factions and recipe | Iron Teeth: `MoreFluidsCoffee`, 1 `Coffee` per 0.33 h from 0.2 coffee volume. Folktails: `MoreFluidsAntidote`, 2 `Antidote` per 2 h from 0.8 healing volume. |
| Status | "Too dilute" while the recipe's fluid is under 10% of the intake column; production stops. |
| Cost | Log 20, Gear 15, Metal Block 10 (the Badwater Pump's goods, a little more for the separator). |
| Science | 400 |
| Workers | 1 beaver (bots allowed), like the vanilla pumps |
| Power | None |
| Toolbar | `Water`, order 13 (after the Badwater Pump) |

### Desalinator

| Field | Value |
| --- | --- |
| Templates | `MoreFluidsDesalinator.Folktails`, `MoreFluidsDesalinator.IronTeeth` |
| Footprint | The vanilla Large Water Pump layout: size 3 × 4 × 4, `BaseZ` 1, entrance (1, −1, 1). Ground blocks at z = 1 for y = 0–2; the intake overhang (1, 3, 1) sits over water. |
| Water input | (1, 3, −1); pipe `MaxDepth` 6, like the Deep Water Pump. Pipe segments: `Buildings/Water/LargeWaterPump/LargeWaterPumpPipeSegment.Folktails` and `Buildings/Water/DeepWaterPump/DeepWaterPumpPipeSegment.IronTeeth`. |
| Factions and recipe | Both: `MoreFluidsDesalinatedWater`, 1 `Water` per 0.33 h from 0.3 saltwater volume (0.2 into the good, 0.1 as brine). |
| Status | "No saltwater" while the intake column holds none. |
| Cost | Plank 40, Gear 20, Metal Block 20 (below the Centrifuge's 60 / 40 / 30: one worker, a third of its power) |
| Science | 600 |
| Workers | 1 beaver (bots allowed) |
| Power | 60 hp input, connecting at the middle of either side wall of the working floor: (0, 1, 1) on the left, (2, 1, 1) on the right |
| Toolbar | `Water`, order 61 (after the Centrifuge) |

### Healing Spring (building)

| Field | Value |
| --- | --- |
| Templates | `MoreFluidsHealingWell.Folktails`, `MoreFluidsHealingWell.IronTeeth` (one blueprint per faction, each with its faction's model) |
| Footprint | 1 × 1 × 2, `BaseZ` 0, no entrance. Both blocks fully occupied; the bottom one needs terrain (`MatterBelow` Ground), like vanilla water sources. |
| Water source | 1 tile at (0, 0), `DefaultStrength` 0.2, emits only healing water. Strength × the building's power efficiency; 0 while under construction or paused. Follows droughts (the native drought modifier) and keeps flowing, clean, through badtides. Source types `MoreFluids.HealingWellFolktails` and `MoreFluids.HealingWellIronTeeth`, one per template (a source type names one template). |
| Placement | Anywhere on terrain, not on platforms. It cannot go on an existing water source tile, because the native source already occupies it. |
| Cost | Plank 40, Gear 30, Metal Block 20 (a little above the Aquifer Drill's 40 / 25 / 15) |
| Science | 1,000 |
| Workers | None |
| Power | 100 hp input; power connects on all four sides of either block |
| Toolbar | `Water`, order 101 (after the Aquifer Drill) |
| Description | "Draws healing water from deep below. Beavers wading in water that is at least 20% healing recover from injuries and contamination. Stops in droughts." (The native tooltip lists cost, science and power.) |

Placement reasons: a healing pool belongs beside the colony's paths, and map sources are often far away. The native water source inside a building is exactly how Deep Frontier's Radioactive Spring and vanilla `DevWaterSource` work, and Moddable Fluids gives it its own source type with no new API. Converting an existing map source would destroy that source's drinking water and need a per-source composition override that the API does not have. The power gate follows the vanilla Aquifer Drill (`UndergroundWaterSourceDrill`: strength × `MechanicalNode.PowerEfficiency`). Its output does not replace drinking water: pure healing water is above the 50% pump limit.

### Healing Spring (map object)

| Field | Value |
| --- | --- |
| Template | `MoreFluidsHealingSpring`, map editor only (`TemplateCollection.MapEditor.Common`) |
| Footprint | 1 × 1 × 1, `MatterBelow` Ground, fully occupied, like the vanilla Water Source |
| Water source | 1 tile, `DefaultStrength` 0.4, emits only healing water, follows droughts, not contaminated by badtides. Source type `MoreFluids.HealingSpring`. |
| Factions, cost, science, workers, power | Any faction; none (map object) |
| Toolbar | `MapEditorWater`, order 520 (after Deep Frontier's Radioactive Spring at 510) |

### Geyser (map object)

| Field | Value |
| --- | --- |
| Template | `MoreFluidsGeyser`, map editor only |
| Footprint | 1 × 1 × 1, `MatterBelow` Ground, fully occupied |
| Water source | 1 tile, `DefaultStrength` 2.0, fresh water, schedule above; ignores droughts and badtides. Source type `MoreFluids.Geyser`. |
| Factions, cost, science, workers, power | Any faction; none (map object) |
| Toolbar | `MapEditorWater`, order 530 |

## Art

The art agent owns every model, icon and art source at these paths and nothing else. Each icon gets a `.png.meta.json` of `{"isSprite":true}`, as in Deep Frontier. Models must fit the footprints above; colliders in the blueprints follow the vanilla templates and are adjusted to the delivered models.

| Object | Resource paths (under `src/MoreFluids/Data/`, add `.timbermesh` or `.png`) |
| --- | --- |
| Fluid Extractor | `Buildings/Water/MoreFluidsFluidExtractor/MoreFluidsFluidExtractor.<Faction>.Model`, `…<Faction>.ConstructionStage0.Model` for Folktails and IronTeeth; icon `…/MoreFluidsFluidExtractorIcon` |
| Desalinator | `Buildings/Water/MoreFluidsDesalinator/MoreFluidsDesalinator.<Faction>.Model`, `…<Faction>.ConstructionStage0.Model` for both; icon `…/MoreFluidsDesalinatorIcon` |
| Healing Spring (building) | `Buildings/Water/MoreFluidsHealingWell/MoreFluidsHealingWell.<Faction>.Model`, `…<Faction>.ConstructionStage0.Model` for both; icon `…/MoreFluidsHealingWellIcon` |
| Healing Spring (map object) | `MapEditor/Objects/MoreFluidsHealingSpring/MoreFluidsHealingSpring.Model`; icon `…/MoreFluidsHealingSpringIcon` |
| Geyser | `MapEditor/Objects/MoreFluidsGeyser/MoreFluidsGeyser.Model`; icon `…/MoreFluidsGeyserIcon` |
| Coffee tide, Salt tide | `Sprites/Weather/MoreFluidsCoffeeTideIcon` (46 × 46), `…Progress` (316 × 52) and `…Notification` (1514 × 348), and the same three for `MoreFluidsSaltTide`, at the sizes of Deep Frontier's radioactive tide sprites |

Art sources (Blender scenes, references, renders) go under `src/MoreFluids/Art/`. One icon per building serves both factions, as vanilla does (`CentrifugeIcon`). Direction (user, 2026-11-09): vanilla style, wood and stone like the base game, matching each faction's own look, so the pack works without Deep Frontier; not Deep Frontier's metal and concrete. The Fluid Extractor is a pump with a small separator vessel and a glass sight gauge. The Desalinator is a pump feeding shallow evaporation pans under a condenser hood, with white salt crust and a brine spout. The buildable Healing Spring is a carved-stone wellhead with a small pump head in the faction's style and mint-green mineral staining (the fluid colour). The map Healing Spring is a natural mossy rock vent with mint crusts, at the scale of Deep Frontier's Radioactive Spring. The Geyser is a grey-white sinter cone with ochre bands around a vent.

## Tides

Both tides use Moddable Fluids' tide registration: per difficulty a chance (the tide's default weight, and the save's default budget when it is the largest installed chance), cycles without the tide and duration; presentation (name, notifications, weather-panel text, sprites, the native drought alarm for coffee and badtide alarm for salt) and the source composition and strength while active. Each tide's weather ID (`MoreFluidsCoffeeTideWeather`, `MoreFluidsSaltTideWeather`) has a fog colour in every day stage (`Data/Configurations/Sun.blueprint.json`), which the native sun needs.

Long-run shares on Normal under policy C′, from [fluids-tides.md](fluids-tides.md) (computed by `tools/model_tide_selection.py`, all weathers eligible):

| Installed | Budget | Drought | Badtide | Radioactive | Coffee | Salt |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Vanilla | – | 59.7% | 40.3% | – | – | – |
| Deep Frontier | 25% | 48.1% | 31.9% | 20.0% | – | – |
| More Fluids | 15% | 52.2% | 34.8% | – | 6.5% | 6.5% |
| Deep Frontier + More Fluids | 25% | 48.1% | 31.9% | 9.1% | 5.5% | 5.5% |

Installing More Fluids never raises the total hazard: its tides share the budget.

## Moddable Fluids capabilities

More Fluids requires `Policies.Irrigation`, `Policies.WaterIntakes`, `Registry.Definitions`, `Scene.Lifecycle`, `Sources.Types`, `Tides.Registration`, `World.Extraction` and `World.Sampling`, so Moddable Fluids rejects it, naming the missing ones, until each is listed. It uses:

1. **Intake policies and selective extraction.** Water-pump thresholds through `SetWaterIntakePolicy`; the Fluid Extractor and Desalinator draw only their fluid through `FluidScene.Extraction` and mark themselves `IFluidCustomIntake`.
2. **Irrigation policies.** `SetIrrigatesLikeWater` for coffee and healing water, `SetBlocksMoisture(0.1)` for saltwater.
3. **Tide registration.** Both tides; Moddable Fluids owns selection, the new-game rows and the weather adapter.
4. **Sampling.** Healing exposure reads each beaver's column, much as `RadiationExposure` does in Deep Frontier.
5. **Custom source types in play.** Emission, schedule and drought-following for the Healing Spring, Healing Well and Geyser templates. The Geyser ignores droughts, so the native `DroughtWaterStrengthModifier` that the game adds to every `WaterSource` must be turned off for it, as the native `WaterSourceDischarger` does under a Badwater Pressurizer.
