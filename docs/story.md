# Deep Frontier story bible

Status 2026-10-21: the content and runtime are authored and compile-checked. Scratch-copy generation and the static validator pass. Nothing here has been built, launched or played; `tools/STATUS.md` holds runtime verification.

The canonical text is in `tools/narrative_content.mjs`, which writes every string to `enUS.csv`. This document explains the design. Where the two differ, the module is right and this document needs updating. The three rocket success texts in `tools/rocket_program_content.mjs` are part of the canon, and the chapters below build on them.

## Tone

Timberborn's tone applies. The story is hopeful, with dry humour and no gore. The humans did not die on screen. They left, tidily, and forgot one very important switch. The beavers are not victims of a curse. They are the first ones to read the manual. Jokes come from human bureaucracy and signage, and from beaver pragmatism. Characters are never mocked.

## The mystery

**What the beavers know at the start:** badwater is green, sour and dangerous, and badtides come and go. The old stories call it a sickness of the land.

**What actually happened (revealed in order):**

1. **The Deepworks.** The valley's humans ran great wells and drills. They pulled ancient deep water and ore up from under the valley for their factories. The pipes are stamped VWA, for the Valley Water Authority.
2. **The Holding.** Factory residue went upriver into the Holding, a chain of sealed basins. A treatment works ran day and night to keep it clean. Projected containment life: "indefinite, subject to maintenance". The maintenance was postponed to next quarter, more than once.
3. **The departure.** The rains failed, then the wells, then the harvests. The humans decided to leave "for now" and follow the rain north. Nobody wrote down when "now" would end. The crew of the orbital Watch station also went "home, wherever that turns out to be". They left the telescope on.
4. **The switch.** The last shift set the treatment works to automatic and put the Holding's flush valves on a schedule "until further notice". No further notice ever came. The filters ran out and the treatment works stopped. The flush schedule kept cycling.
5. **The provenance.** Every badwater spring sits on an old pipe line that leads back to the Holding. The badtides arrive on the flush schedule. Badwater is not a disease. It is runoff from a forgotten tank that nobody switched off.
6. **What the beavers choose.** The colony's own water treatment plants already do, at beaver size, what the humans' works did. The Holding can be kept, as long as someone stays to keep it. The last rocket carries the colony's answer: a signal, an archive, or a map home.

## Chapters

The chapters complete strictly in order. Each completion grants its science, posts a notification and opens a native story dialog. Each chapter also gets a journal entry. Goods counters are cumulative from the start of the game, so a colony that is already ahead completes a chapter as soon as it becomes current. Several chapters can complete in one tick. Their dialogs then queue in order.

| # | Id | Title | Trigger (all must hold) | Reveals | Science |
|---:|---|---|---|---|---:|
| 1 | `NotNatural` | Something in the Water | First finished Public Health Lab, Water Treatment Plant, Deep Drill **or** Chemical Works (story line varies by which) | Badwater behaves like a recipe, so somebody made it | 500 |
| 2 | `UnderTheValley` | Under the Valley | 20 DeepAlloy produced (Deep Processor) | VWA pipe tunnels run upriver ("NOT FOR DRINKING", with increasing underlining) | 1,000 |
| 3 | `WhatTheWaterCarries` | What the Water Carries | 80 PureWater **and** 10 Chemical produced | Badwater is industrial runoff, still leaking from upriver | 1,500 |
| 4 | `OpenTheRuins` | Open the Ruins | 6 RecoveredArtifact produced (Archive Excavation) | Holding Station 3 artifacts: hard hat, mug, sign; sealed data drives | 2,000 |
| 5 | `TheArchiveWakes` | The Archive Wakes | 10 ArchiveData produced (cache surveys count) | The Deepworks, the Holding, and the postponed maintenance | 3,000 |
| 6 | `TheLastShift` | The Last Shift | 30 ArchiveData produced in total **and** a finished Mission Control | Why the humans left; the switch set to "until further notice"; an orbital frequency still answers | 5,000 |
| 7 | `EyesAbove` | Eyes Above | Orbital Observatory mission succeeded | Orbital images plus Authority maps: every spring and every badtide traces back to the Holding | 0 (mission gives 100,000) |
| 8 | `WhatTheStationKept` | What the Station Kept | Recovery Probe mission succeeded | The station crew's last log; the treatment design matches the colony's plants; the Holding can be kept | 0 (mission gives 250,000) |
| 9 | `TheMessage` | What the Beacon Says | Ending chosen (journal, or the choice dialog that opens when chapter 8 completes) | The colony's decision | 0 |
| 10 | `TheBeacon` | The Long-Range Beacon | Long-Range Beacon mission succeeded | The badwater has a source, a reason and a caretaker, followed by the chosen epilogue | 0 |

Rocket missions show their own success dialog (from the Launch Pad) first. The journal's chapter dialog waits until no panel or dialog is open. Chapters 7, 8 and 10 therefore read as the archive's interpretation of what the mission found.

**Evidence budget.** The three missions consume about 48 ArchiveData through guidance computers, telemetry and payloads. The 30 ArchiveData for chapter 6 is therefore not extra grinding. Every rocket route makes it anyway.

## How the four player stories reach the ending

Every route to a launch must already build a Deep Drill and Deep Processor (DeepAlloy for T4 construction and for Alloy). It also needs a Water Treatment Plant (PureWater for electrolysis), Chemical Works (Polymer), an Archive Excavation (ArchiveData for guidance computers, artifacts for payloads) and Mission Control. Every chapter trigger uses only those mandatory steps, or an "any of" list. No trigger checks nuclear power. The reactor and vault feed only the optional discovery `HoldingOurOwn`.

| Story | Chapter 1 trigger it usually hits | Order it tends to meet chapters 2–3 | Notes |
|---|---|---|---|
| Civic builder | Public Health Lab ("the chemists came back with a very long list") | Chapter 3 later, once treatment is built for rocket fuel | Hospital discovery `ClinicLog` early; renewable launch grid |
| Automation engineer | Chemical Works or Deep Drill | Chapters 2 and 3 back to back | Likely nuclear: `HoldingOurOwn` and `CleanHands` discoveries |
| Underground prospector | Deep Drill ("a pipe far too big for beavers") | Chapter 2 immediately | Explores ruins early; Archive Excavation and record caches |
| Badwater remediator | Water Treatment Plant ("the exact same wrong colour, every single time") | Chapter 3 is often already satisfied when it becomes current | `CleanerThanTheRiver` discovery; mixed renewable grid |

## Endings

The choice is made once, in chapter 9. It changes the closing story, not the rocket. The native wonder completion (started by the beacon's success in `RocketLaunchPad`) is the same for all three endings.

| Id | Title | Choice | Epilogue flavour |
|---|---|---|---|
| `Signal` | We Are Here | A standing call: where the Holding is, how to keep it, and an invitation to anyone listening | A drawing of a beaver waving, repeated every few hours. Nobody has answered *yet*, and a light stays on at the pad. |
| `Archive` | The Whole Record | Everything, human and beaver, safe in orbit | Every ledger, including the boring ones, filed under MAINTENANCE: DO NOT POSTPONE |
| `Settlement` | The Map Home | Clean-water maps, treatment designs and safe routes for future settlers | It doesn't ask anyone to come. Someday travellers follow it over the ridge to a valley already waiting. |

If the beacon flies before the colony has chosen, a notification and the choice dialog appear. The final chapter completes as soon as a choice is made.

## Optional discoveries

Discoveries never gate the chapters, and the colony can find them in any order.

| Id | Trigger | Science |
|---|---|---:|
| `ClinicLog` | First finished Hospital | 250 |
| `CleanerThanTheRiver` | 500 PureWater produced | 250 |
| `HoldingOurOwn` | First finished Radioactive Waste Vault (nuclear route) | 250 |
| `CleanHands` | One DecontaminateWater cycle (radiation remediation) | 250 |
| `CacheRoster`, `CacheDrawing`, `CacheWeather`, `CacheMemo`, `CachePostcard` | 1–5 Human Record Caches surveyed | 0 (each cache gives 6 ArchiveData) |

## Human Record Cache (map evidence)

The cache is a map-editor object (`MapEditor/Objects/HumanRecordCache`, MapEditorObjects tool order 1450). It is cloned from the vanilla Medium Relic and keeps that relic's model, colliders, icon and native demolition. Demolition still gives 800 science but loses the records.

A finished workshop that runs the `ArchiveData` recipe, meaning an Archive Excavation, can survey a cache. The workshop needs an occupied cell within 7 tiles horizontally and 7 layers vertically. While its workers work, the survey advances. After 24 working hours the cache hands 6 ArchiveData to that workshop's output inventory as unreserved space allows. The survey counts toward ArchiveData chapters and unlocks the next cache record. Map authors should place caches near ruins, so a colony that excavates there finds them naturally. Caches are optional, so maps without them still complete the story.

## Runtime contract (summary)

- `NarrativeObjectiveService` (Game singleton) reads the single `NarrativeSettingsSpec` (`Configurations/DeepFrontierNarrative`) and validates it explicitly. It tracks:
  - native `EnteredFinishedStateEvent`, plus a PostLoad scan of finished buildings, for "ever finished" latches;
  - `NarrativeProductionReporter`, decorated on every native `Manufactory`, which reports each finished cycle;
  - `RocketProgramService.IsCompleted`;
  - cache surveys;
  - the ending choice.
- Only Iron Teeth settlements run the story (`FactionId`).
- The service saves under `DeepFrontier.Narrative`: completed chapters (which must be a prefix of the authored order), discoveries, finished-template latches, goods and recipe counters, the ending choice and the number of caches surveyed. Inconsistent saved data throws.
- The journal (`NarrativeJournal.cs`, TimberUi, player build only) has three parts:
  - a top-left panel (order 4) showing chapter n/10 and the next unmet objective;
  - the journal window, with the current objective, progress, hint, ending choice, chronicle and discoveries;
  - native story dialogs, queued until no panel is open.

## Follow-ups

- **Art:** an original Human Record Cache model and icon (currently the vanilla Medium Relic, a placeholder). A journal icon for a native-style top-right square button would replace the text panel.
- **UI polish:** test the top-left panel's width and position against the notification panel in game. Consider a hotkey for the journal and a short "new entry" highlight.
- **Map:** place 3–5 caches near ruins on the purpose-built Deep Frontier map.
- **Content:** the Archive Excavation integration must keep running the `ArchiveData` and `RecoveredArtifact` recipes. The validator fails if no generated or planned building runs them.
