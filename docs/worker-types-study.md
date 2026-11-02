# Third worker-type option for Reactor Bots: feasibility study

**User request (2026-11-02):** "I want to see what it would take to make there be an extra toggle for nuclear bots vs normal beavers vs regular bots. Right now it has regular and bot, I want a third option, furthest to the right, which specifies nuclear bots."

This began as a study. The user chose Option 1 and answered its decision points, and it is now implemented: see "What was built" first; the study below it is kept as written. Evidence comes from Timberborn 1.1.2.8, decompiled with the project's `tools/dotnet/ilspycmd.exe` from the installed `Timberborn_Data/Managed` assemblies, and from the Deep Frontier sources at the commit that adds this file.

- **[S]** marks a source-confirmed fact, with the type and member it comes from.
- **[H]** marks a hypothesis that has not been checked in code or in game.

## What was built (2026-11-02)

**The user's answers to the decision points:**
1. "No, reactor bot only works at reactor bot workplaces." The three modes are exclusive: Beaver workplaces take beavers, Bot workplaces take ordinary bots only, Reactor Bot workplaces take Reactor Bots only.
2. "Yes. 3x the cost of the normal bot unlock." The Reactor Bot option is its own science unlock per workplace.
3. "We should also allow reactor bots at ANY building in the game." This includes beaver-only and specialist-only workplaces.
4. "Yes": the District Center's default worker type has the third option.

**Runtime** (`src/DeepFrontier/Scripts/SuperBots/`: `ReactorBotWorkplace.cs`, `ReactorBotStaffing.cs`, `ReactorBotWorkplaceUnlocks.cs`, `ReactorBotWorkplaceLight.cs`, `ReactorBotWorkplacePatches.cs`)

- **The mode.** `ReactorBotWorkplace` is decorated on every `WorkplaceWorkerType` and holds a saved flag (`DeepFrontier.ReactorBotWorkplace`).
  - **Turning it on** sets the native worker type to Bot, so these stay native: the `AssignWorker` type check, the statistics, the bot outfits, the empty bot slot icons and the saved type. Then every worker is released.
    - Where bots are natively allowed and unlocked, it uses native `SetWorkerType`.
    - Elsewhere (beaver-only workplaces, or bots still locked) it performs the same steps without the native checks (`NativeWorkerTypeAccess`, private members resolved by reflection): release the workers, set the type, raise `WorkerTypeChanged`, mark the type as chosen.
  - **Turning it off** releases the Reactor Bots. A Bot type the workplace may not natively have goes back to its default type.
  - **Ending the mode.** Any native change of the type away from Bot ends the mode: the Beaver button, copied settings, other mods.
  - **Copy settings.** Native copy settings (`IDuplicable`) carries the mode where the target has it unlocked.
- **Staffing.** `ReactorBotStaffing` is the `SpecialistStaffing` pattern. Each tick it does three things:
  - it releases Reactor Bots from any workplace not set to Reactor Bots;
  - it releases anyone else from Reactor Bot workplaces;
  - it fills each Reactor Bot workplace, highest priority first, with Reactor Bots of its district: unemployed ones first, then ones from a lower-priority Reactor Bot workplace.
  - Desired workers, priority, overstaffing release, work refusal, district checks and saves stay native.
- **Specialists.**
  - **Which rule wins.** The Reactor Bot mode wins over the specialist requirement: `SpecialistStaffing` skips a specialist workplace while it is set to Reactor Bots and clears its "no specialists" statuses. Switching it back to Beaver restores the specialist rule.
  - **Why.** The user asked for Reactor Bots at any building. The specialist requirement is the rule for beaver crews (specialists are beavers with a trained discipline). The unlock price is the gate: Nuclear Reactor 3,003,000 science, Launch Pad 603,000, Steel Mill 33,000.
  - **Panel.** The specialist panel says the Reactor Bots work there instead of the trained discipline.
- **Unlock.** `ReactorBotWorkplaceUnlocks` saves the unlocked templates in its own singleton.
  - **Cost.** 3 x the template's native Bot unlock cost. Without one (beaver-only, specialist-only, and the bot-free District Center, flags, Deep Water Pump and Industrial Lumber Mill), 3 x (`BuildingSpec.ScienceCost` + 1,000), the bot unlock Deep Frontier gives its own buildings (science + 1,000). The cost is therefore never free; with no `BuildingSpec` the science is 0.
  - **Why apart from the native service.** Native `WorkplaceUnlockingService` resolves each saved worker type through `WorkerTypeService` on load, so a third type saved there would stop the save loading without the mod [S].
  - **Flow.** It is that of native `WorkplaceUnlockingDialogService`: the InstantUnlock key, the native dialog box with a confirmation, the native "not enough Science Points" box, and the native `Game/ScienceCostTooltip` locked tooltip. The texts say "Reactor Bots".
- **District default.** `ReactorBotDistrictDefault` on `DistrictDefaultWorkerType` holds a saved flag; the native default is set to Bot with it. A new workplace takes the Reactor Bot mode where it is unlocked; elsewhere it gets the native result for a Bot default.
- **Light.** `ReactorBotWorkplaceLight` turns a Reactor Bot workplace neon green (priority 30) whenever it is set to Reactor Bots. The lights still go on and off natively, while a worker (here a Reactor Bot) works. The rule became simpler: with exclusive modes, only Reactor Bots work at such a workplace.
- **Harmony** (`ReactorBotWorkplacePatches.cs`, editor-guarded). Every target and member is verified at mod start; a changed game throws there. Each patch:
  1. `WorkerTypeToggle.Initialize` postfix: rebuilds the toggle's `SliderToggle` with Beaver, Bot (inactive while set to Reactor Bots) and Reactor Bot. This covers the entity panel and the batch control window, both from `WorkerTypeToggleFactory`. The third icon is the bot icon tinted with the window colour. `SliderToggleFactory` takes any number of items, and the native Gate toggle already uses three [S].
  2. `DistrictCenterFragment.InitializeFragment` postfix: the same for the district default.
  3. `UnemployedWorkers.UpdateUnemployedState` prefix: keeps Reactor Bots out of the native pool the district assigner hires from, so Bot workplaces get ordinary bots only.
  4. `PriorityOrderedWorkplaces.GetHighestPriorityUnderstaffedWorkplace` and `GetLowestPriorityStaffedWorkplace` postfixes: when native picks a Reactor Bot workplace, they pick the next one that is not, so native neither hires into it nor takes its crew.
  5. `WorkplaceWorkerType.SetWorkerTypeToDistrict` prefix and postfix: applies the district's Reactor Bot default once, when native applies the district default (`_wasSet`).
- **Startup check.** All of this was run in the game's own Mono 6.13 against the shipped 1.1.2.8 DLLs (a scratch host, as earlier harnesses): verification passes, the six methods patch, and the patched workplace order runs.

**What the player sees in the shared native systems**

- **Top bar.** Reactor Bot workplaces count as bot jobs and vacancies (native type Bot), and idle Reactor Bots count as unemployed bots.
- **Bot wear and maintenance.** Both follow the workplace (`IndustrialRisk.BotWearMultiplier`, `BotMaintenance` doses), so Reactor Bots wear as bots do there. Beaver-only and specialist buildings declare no bot wear (1x), and their panel now says so.
- **Workplace upkeep** (drill bits) does not depend on who works.
- **Reactor Bot needs** (charge, coolant, plating) are fetched by the bot's own need behaviour and do not depend on the workplace.
- **Hauling and building.** These are workplaces too (District Center builders, Builders' Hut, Hauling Post), so they can be set to Reactor Bots.
- **Retrofits.** A bot queued for a retrofit is still ordinary and keeps its bot job. Once upgraded, it leaves that job for a Reactor Bot workplace.

**Saves**

- The native type is saved as Bot and the mode under Deep Frontier's own key.
- Without Deep Frontier, the workplace loads as a Bot workplace where bots are natively allowed and unlocked, otherwise as its default type (native `WorkplaceWorkerType.Load`) [S]. The Reactor Bot unlocks and the district flag are then ignored.
- An older save keeps its workplaces as they were. Its Reactor Bots leave Bot workplaces and wait for Reactor Bot workplaces.

**Checks:** `tools/validate_reactor_bot_workplaces.mjs` checks the data, the runtime and the native contract, decompiled from the project's plugin assemblies.

**Open:**
- [H] A third button in the batch control row and in Second Shift's replacement panel is not yet seen in game.
- [H] Reactor Bots on a power wheel may lack a fitting animation, because native disallows bots there.
- The Reactor Bot panel and Bot Assembler texts do not yet mention that Reactor Bots need Reactor Bot workplaces; they belong to the Reactor Bot catalog (`tools/super_bot_content.mjs`).

## Summary

- **The game has no data-only way to add the button.** A new worker type can be registered with data alone (a `WorkerTypeSpec` blueprint). But the two-button toggle is hard-coded C#, and every worker reads its type from its character template.
- **A Reactor Bot is a state of the ordinary bot, not a separate character template**, so the game cannot tell it apart from an ordinary bot when it assigns workers.
- **Recommended: Option 1.** The third button is a Deep Frontier setting, "Reactor Bots only". A workplace with it on keeps the native worker type Bot, and Deep Frontier staffs it, the way specialist-only workplaces are already staffed.
  - What it needs: about four small Harmony patches. One adds the button to the native toggle. The other three reuse the existing specialist pattern that keeps the game's own staffing away from these workplaces.
  - Saves: unaffected. Removing the mod turns these back into ordinary bot workplaces.
  - Effort: about 2-3 days with in-game checks. Risk: medium.

## How the native toggle works

### Worker types are strings, registered by data
- **[S] Registration.** `Timberborn.WorkerTypes.WorkerTypeService.Load` reads every `WorkerTypeSpec` blueprint into a dictionary, under its `Id` and its `BackwardCompatibleIds`.
- **[S] Vanilla types.** Vanilla ships two, `WorkerTypes/WorkerType.Beaver` and `WorkerType.Bot`. Each has `IgnoresWorkingHours` (true only for Bot), `DisplayNameLocKey` and `WorkerOnlyTextLocKey`.
- **[S] A new type needs only data.** Adding a `WorkerType.ReactorBot` blueprint registers a third type. No code is needed for that.
- **[S] Lookups throw on an unknown id.** `GetWorkerTypeSpec(id)` uses the dictionary indexer, so an unknown id throws `KeyNotFoundException`.

### Each worker's type is fixed by its character template
- **[S] Where the type comes from.** `Worker.WorkerType => _workerSpec.WorkerType`, where `WorkerSpec` is a component spec on the character blueprint. `Characters/Beaver/BeaverAdult` has `"Beaver"`; `Bot.IronTeeth` and `Bot.Folktails` have `"Bot"`.
- **[S] No per-bot override.** No setter exists, and nothing else feeds the value.
- **[S] Reactor Bots are ordinary bots.** A Reactor Bot is the vanilla `Bot.IronTeeth` entity with `DeepFrontier.Scripts.SuperBots.ReactorBot` decorated on `BotSpec`; its `State` (`Ordinary`/`Queued`/`Reactor`) is saved per bot. Its `Worker.WorkerType` is therefore always `"Bot"`.
- **[H] One bot cannot get its own type without patching.** That would take a Harmony patch on the `Worker.WorkerType` getter.

### Each workplace has one worker type, saved with it
- **[S] `WorkplaceSpec` fields.** `MaxWorkers`, `DefaultWorkers`, `DefaultWorkerType` (default `"Beaver"`), `DisallowOtherWorkerTypes`, and `WorkerTypeUnlockCosts` (a list of `{WorkerType, ScienceCost}`).
- **[S] Validation.** `Workplace.ValidateWorkplaceSpec` rejects `DisallowOtherWorkerTypes` together with unlock costs.
- **[S] `WorkplaceWorkerType` holds the current type.** It starts from `DefaultWorkerType` and is set to the district's default when the building finishes, unless the player chose already (`WasSet`).
- **[S] Changing the type.** `SetWorkerType(type)` checks `IsWorkerTypeAllowed` (with `DisallowOtherWorkerTypes`, only the default type) and `IsWorkerTypeUnlocked`. It then unassigns every worker and raises `WorkerTypeChanged`.
- **[S] Saving and loading.** The component saves `WorkplaceWorkerType.WorkerType` and `WasSet`. `Load` maps the saved string through `WorkerTypeService.GetWorkerType`, so a missing spec throws on load.
- **[S] Unlocking.** `WorkplaceUnlockingService` collects every workplace template's `WorkerTypeUnlockCosts`. `Unlocked(template, type)` is true when that pair has no cost or was unlocked; unlocked pairs are saved (`UnlockedWorkerTypes`). A type with no cost entry is free everywhere.
- **[S] Vanilla data.** All 70 vanilla workplaces default to Beaver. Only the Inventors and power wheels are `DisallowOtherWorkerTypes`. Bot unlock costs run from 250 to 10,000 science.
- **[S] Deep Frontier data.** All 37 Deep Frontier workplaces default to Beaver. Seven are beaver-only, among them the specialist workplaces, which `SpecialistWorkplace.Awake` requires to be beaver-only with no bot unlock. 29 have bot unlock costs.

### The panel toggle is two hard-coded buttons
- **[S] Two buttons in `WorkerTypeToggle.Initialize`** (`Timberborn.WorkSystemUI`). It builds a Beaver item (`worker-type-toggle__icon--beaver`) and a Bot item (`--bot`) with `SliderToggleItem.CreateBlockable` and passes both to `SliderToggleFactory.Create`/`CreateBindable`.
- **[S] Where the toggle appears.** The class is built with `new` by `WorkerTypeToggleFactory` (not bound per instance). It is used by:
  - `WorkplaceFragment` (the entity panel, `WorkerTypeToggleWrapper`, hotkey `ToggleWorkerType`);
  - `WorkplaceWorkerTypeBatchControlRowItemFactory` (the batch control window).
- **[S] The slider itself takes any number of buttons.** `SliderToggleFactory.Create(parent, params SliderToggleItem[] items)`. The hotkey moves to `(i + 1) % Count` (`SliderToggle.GetNextIndex`). Button states are `None`, `Active`, `Locked` and `Unclickable`.
- **[S] Icons.** Icons are USS classes in `UI/Views/Game/GameMiscStyle.uss` (`background-image: resource('UI/Images/Game/ico-bot')`). `SliderToggleItem` can also carry a `Sprite`, but only through the non-blockable `Create` overloads, so not with a `Locked` state.
- **[S] Button states and actions.**
  - State: Beaver is active while `IsBeaverWorkerType(type)`. Bot is active while `IsBotWorkerType(type)`, and shows as Locked until the Bot pair is unlocked.
  - Click: Bot either sets the type or opens `WorkplaceUnlockingDialogService.TryToUnlockWorkerType`.
  - `WorkerTypeHelper` hard-codes `"Beaver"` and `"Bot"`.
- **[S] Visibility.** The toggle is hidden until `BotPopulation.BotCreated`.
- **[S] District centre.** `DistrictCenterFragment` has its own two-button toggle for `DistrictDefaultWorkerType`, which is saved as a bare string and not checked on load.

### Workers are assigned per worker type, per district
- **[S] One assigner per type and district.** `DistrictWorkplaceAssigner` (internal, decorated on `DistrictCenter`) keeps one `WorkplaceAssigner` per worker-type string. A finished workplace goes in under its current `WorkplaceWorkerType.WorkerType` and moves on `WorkerTypeChanged`. A worker goes in under `Worker.WorkerType` when it joins the district (`CitizenAssigned`) and is removed by the same key (`CitizenUnassigned`), which throws if the key is missing.
- **[S] How an assigner fills workplaces.** Each tick, every `WorkplaceAssigner` fills its highest-priority understaffed workplace from its unemployed workers. With none unemployed, it moves workers from its lowest-priority staffed workplace to a higher-priority one.
- **[S] The type must match.** `Workplace.AssignWorker` throws when `WorkplaceWorkerType.WorkerType != worker.WorkerType`. `Worker.AssignToWorkplaceAfterLoad` re-employs a saved worker only if the types still match; otherwise it logs "couldn't get employed at their old workplace".

### Other systems that read the worker type
- **[S] `WorkerWorkingHours.Awake`** reads `IgnoresWorkingHours` from the worker's type once.
- **[S] `WorkerOutfitService`** looks up outfits by (outfit id, `worker.WorkerType`). Iron Teeth ships 6 bot outfits: Builder, Farmer, Forester, Gatherer, Pilot and Scavenger.
- **[S] Statistics.**
  - `WorkplaceWorkerCounter` reports employment under the workplace's type.
  - `WorkRefuserRegistry` groups refusers by `Worker.WorkerType`.
  - `PopulationDataCollector` (the top-bar population panel) asks only for `"Beaver"` and `"Bot"`.
- **[S] `PopulationCounter`** (automation) has a "count bots" switch rather than a type string.
- **[S] `WorkerTypeIlluminator` and `WorkerView`** test `IsBotWorkerType(workplace type)`, for the blue light and the empty bot slot icon.
- **[S] Deep Frontier.**
  - `BotWear` is decorated on `BotSpec`, and its wear follows `Worker.Workplace`'s `IndustrialRisk`.
  - `BotMaintenance` doses the bots employed there.
  - `ReactorBotWorkplaceLight` (this commit) turns a workplace green while an assigned Reactor Bot works.
  - None of these read the worker-type string.

### Other mods that touch worker types (installed Workshop items)
- **[S] Moddable Timberborn** (a Deep Frontier dependency) has `WorkplaceWorkerTypeSettings` and `DistrictDefaultWorkerTypeSettings`. They copy the type string and apply it through `SetWorkerType`, gated by `IsWorkerTypeAllowed`/`IsWorkerTypeUnlocked`.
- **[S] Second Shift (eMka)** references `WorkerTypeToggle` and `WorkerTypeToggleFactory`; its description says it "replaces the entire panel" of the workplace.
- **[S] TImprove 4 UI** references `WorkerTypeHelper` and `WorkplaceWorkerType`.
- **[H] Second Shift would show the new button.** If it builds its toggle through `WorkerTypeToggleFactory`, a patch on `WorkerTypeToggle.Initialize` would give its panel the third button too.

### Deep Frontier already staffs some workplaces itself
- **[S] Specialist-only workplaces bypass the game's staffing.** Their staff come from `SpecialistStaffing` (a tickable singleton in `Scripts/Workforce/SpecialistWorkplace.cs`), which fills each one's native `Workplace` by priority:
  - unemployed qualified beavers first, then those employed at ordinary workplaces;
  - it releases anyone unqualified.
- **[S] The game's assigner never sees them.** Two Harmony prefixes in `WorkforcePatches.cs` skip `DistrictWorkplaceAssigner.OnFinishedBuildingRegistered/Unregistered` for them. The native controls (desired workers, priority, work refusal, unreachable release, saves) stay native.
- **This is the closest existing model for a Reactor-Bot-only workplace.**

## Options

### Option 1 (recommended): "Reactor Bots only" as a Deep Frontier setting on bot workplaces

**What the player gets.** The slider reads Beaver | Bot | Reactor Bot. Bot still means any bot, ordinary or Reactor, as today. Reactor Bot means only Reactor Bots.

**Implementation**

- **Setting.**
  - `ReactorBotOnlyWorkplace`, decorated on `WorkplaceWorkerType`, holds a saved bool under its own key (absent means off) and implements `IDuplicable`, so the game's copy settings carry it.
  - It is only allowed where the Bot type is allowed and unlocked. The native `SetEnabledState` logic makes it unclickable on beaver-only (specialist) workplaces.
  - Turning it on sets the native type to Bot first (through the native unlock dialog when Bot is still locked). Choosing Beaver or Bot turns it off.
- **Staffing.**
  - `ReactorBotStaffing`, a copy of the `SpecialistStaffing` pattern, accepts a worker when `GetComponent<ReactorBot>().IsReactor`.
  - It takes unemployed Reactor Bots first, then Reactor Bots from ordinary Bot workplaces (the game refills those from ordinary bots), and releases ordinary bots.
  - It needs a list of Reactor Bots per district: a small registry fed by `ReactorBot` and `Citizen.AssignedDistrict`.
- **Keeping the game's assigner away.**
  - Extend the two existing registration prefixes to skip workplaces with the setting on.
  - Because the setting changes during play, toggling it calls the native handlers through `AccessTools` (already used by `NativeWorkplaceAssigner`): `DistrictWorkplaceAssigner.OnFinishedBuildingUnregistered` when it turns on, and `OnFinishedBuildingRegistered` when it turns off, on the workplace's district centre.
- **Button.**
  - A Harmony postfix on `WorkerTypeToggle.Initialize` rebuilds `_sliderToggle` with three items: the native Beaver item; a Bot item whose state is Active only while the setting is off; and a Reactor Bot item. This way the entity panel, the batch control window and [H] Second Shift all show it.
  - The icon is set as a sprite on the third button's `Icon` image after creation. A blockable item cannot carry a sprite, and the mod has no stylesheet of its own.
  - Tooltips: "Reactor Bots" or the bot unlock cost.
  - Self-check at startup like `SteelDeckPlacerClaim`: the private fields and methods the postfix uses must exist, or the mod start fails.
- **Lights.** `ReactorBotWorkplaceLight` already shows green whenever such a workplace is working, because every worker there is a Reactor Bot. The native blue stays for ordinary bot workplaces.

**What it changes and breaks**

- **[S] Saves.** None of them change: the workplace keeps saving `"Bot"`, and the flag is a Deep Frontier key the loader ignores when absent. Removing the mod turns these back into ordinary bot workplaces.
- **[S] Statistics.** Bot employment numbers stay complete, because the workplace type is still Bot.
- **[S] Bot wear, maintenance, outfits and working hours** are unchanged; they do not read the type string.
- **Risks.**
  - The UI patch reaches into private members of a non-injected class. A game update can rename them, which the startup self-check turns into a visible failure.
  - [H] A third button may not fit the batch control row; it has to be checked in game.
  - Moddable Timberborn's building settings copy only the native type, so pasting onto another building does not carry the flag. [H] This is minor.
  - [H] Second Shift's replacement panel is untested.

**Effort:** about 2-3 days with the acceptance fixture and in-game checks. **Risk:** medium.

**No-Harmony variant of the button.** A "Reactor Bots only" checkbox in a Deep Frontier panel section, using the native or TimberUi controls the mod already uses for its workforce panels, removes the UI patch. It does not give the "third option, furthest to the right" the user asked for; the staffing work is the same.

### Option 2: a native third workplace type ("ReactorBot") in data, with a patch for employing Reactor Bots

**Implementation**

- **Data.** A `WorkerType.ReactorBot` blueprint (ignores working hours, Deep Frontier loc keys). `SetWorkerType("ReactorBot")` then works natively [S]. The game's assigner moves the workplace into a "ReactorBot" `WorkplaceAssigner` that has no workers, so it never hires there or takes its crew [S]. No assigner patch is needed.
- **Employing Reactor Bots.** Every Reactor Bot's `Worker.WorkerType` is still `"Bot"`, so `Workplace.AssignWorker` throws [S]. Deep Frontier would need:
  - a Harmony prefix or transpiler on `AssignWorker` that accepts a Reactor Bot into a "ReactorBot" workplace. The method raises `WorkerAssigned` and `RelationsChanged`, which outside code cannot raise without reflection on the event fields;
  - a patch on `Worker.AssignToWorkplaceAfterLoad`, or every Reactor Bot crew is dropped on each load with a warning (the staffing then re-hires it) [S].
- **Button.** The same toggle patch as Option 1, but the third item calls native `SetWorkerType("ReactorBot")`. The native Beaver and Bot items already show as inactive for that type [S].
- **Unlock.** The "ReactorBot" type has no cost entries, so it would be free everywhere [S]. It needs a custom rule ("Bot unlocked"), or cost entries patched into every workplace blueprint, vanilla included (70 plus 29).

**What it changes and breaks**

- **[S] Saves.**
  - The workplace saves `"ReactorBot"`. Without the spec (mod removed, or the id renamed without `BackwardCompatibleIds`), `WorkplaceWorkerType.Load` throws `KeyNotFoundException`, and even vanilla buildings (a Lumber Mill set to Reactor Bot) stop the save loading.
  - The same applies to a saved `WorkplaceUnlockingService` entry.
- **[S] Missing bot behaviour.** No native blue light, the beaver empty-slot icon (`WorkerView` tests `IsBotWorkerType`), and these workplaces drop out of the top bar's bot vacancies (`PopulationDataCollector` reads only Beaver and Bot).
- **[S] Unchanged.** Outfits, wear and working hours, because the workers stay "Bot".

**Effort:** about 3-4 days. **Risk:** high. The `AssignWorker` patch sits on every assignment in the game, and saves lose removal safety.

### Option 3: Reactor Bots as a real worker type (their `Worker.WorkerType` becomes "ReactorBot")

**Implementation**

- **The worker type.** A Harmony postfix on the `Worker.WorkerType` getter returning `"ReactorBot"` while `IsReactor`. A separate character template is ruled out:
  - the user's 2026-10-29 direction is the same bot, the same template and a saved flag;
  - [S] an entity's template is fixed: saves store the template name and `WorldEntitiesLoader` instantiates by it;
  - [H] converting would mean deleting the bot and spawning a new one, losing its identity.
- **At the moment of upgrade**, the bot must:
  - leave its Bot workplace (`AssignWorker`'s check);
  - move from the district's "Bot" assigner to the "ReactorBot" one. `DistrictWorkplaceAssigner` keys workers when they join the district and removes them by the current key, so a stale entry either throws or is later hired into a Bot workplace and throws there [S];
  - move between the `WorkRefuserRegistry` groups [S].
- **Data.** A WorkerType blueprint, plus 6 duplicated Iron Teeth bot outfits for "ReactorBot" (or Reactor Bots lose their profession outfits, [S] `WorkerOutfitService`).
- **Button.** The same toggle patch.

**What it changes and breaks**

- **Gameplay.** Bot workplaces no longer take Reactor Bots at all ("Bot" would mean ordinary bots only). Reactor Bots then sit idle unless the player sets workplaces to Reactor Bot. That is a large change to how Reactor Bots play today.
- **[S] Statistics.** Reactor Bots disappear from the bot workforce numbers.
- **[S] Saves.** The same removal risk as Option 2 for workplaces saved as "ReactorBot". [H] Worker types are not saved per worker, so bots follow their saved state on load.

**Effort:** 5 or more days. **Risk:** high: the getter feeds assignment, statistics, outfits and working hours.

## Recommendation

**Option 1.** It is the only option with these four properties:
- it keeps Reactor Bots useful in every bot workplace, as today;
- it keeps saves loadable without the mod;
- it keeps the native statistics complete;
- it reuses a staffing pattern this mod already ships and has tested.

**Decision points for the user before implementation**

1. **Should "Bot" keep accepting Reactor Bots?** Recommended: yes.
   - Making "Bot" ordinary-only would mean Deep Frontier staffs every bot workplace, not only Reactor-Bot ones.
2. **Should the Reactor Bot button need anything beyond the workplace's Bot unlock?** For example, an extra science cost, or the first Reactor Bot or Reactor Charging Bay existing.
3. **Should the district centre's default worker type get the third option too?** It is a separate native toggle (`DistrictCenterFragment`) and would be one more patch.
