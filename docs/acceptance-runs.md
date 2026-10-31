# Unattended in-game acceptance runs

The marked acceptance launchers (`tools/start_*.ps1`) start Timberborn with `-deepFrontierLoadAcceptance` and one harness flag. The mod's main-menu `IndustrialAcceptanceLoader` then loads the fixture save through the native `GameSceneLoader`, and the harness runs in the game scene. This page records what used to need clicking, what now handles it, and the procedure.

## What blocked the runs (Timberborn 1.1.2.8, 2026-10-21)

**1. The "Mods" screen. This was the only blocker seen.** Whenever mods are installed, scene 0 shows the Mods list with an OK button. Source: `Timberborn.ModManagerSceneUI.ModManagerScenePanel.Awake`. It loads the enabled mods and the main menu only after OK, Enter, or the `skipModManager` command-line key. No mod code is loaded at this point, so Deep Frontier cannot dismiss the screen. The mod's DLLs load in `LoadModsAndStartGame`.
- Evidence: the build-121 run log `outputs/lategame-main121.log` ends with one "Successfully connected to the Steam client." line, then the window-close shutdown.
  - That first line comes from the Mods screen's own `SteamManager`.
  - A completed run logs a second connect line, then `Modded: true, official` and the mod list.
- A probe launch of build 121 the old way (`Steam.exe -applaunch 1062090 …`, 2026-10-21 23:41) reproduced that log tail exactly, after the version line. Its screenshot showed the Mods screen and no other window.
- Steam showed no prompt and no window of its own during that launch.

**2. In-game startup panels lock the game speed.** `PanelStack.Push` posts `PanelShownEvent(lockSpeed: true)`, and `Timberborn.UILayoutSystem.OverlayPanelSpeedLocker` then calls `SpeedManager.ChangeAndLockSpeed(0)`. While the lock holds, `SpeedManager.ChangeSpeed` does nothing, so a harness's speed changes are silently ignored.
- The only known startup panel is Moddable Weathers' Weather Settings dialog. It opens on `ShowPrimaryUIEvent`, which `GameInitializer` posts on the first game frame after a save loads, when the save lacks the singleton `WeatherSettingsDialogShower.DialogShowed`.
- A scan of every save in `ExperimentalSaves/Industrial Acceptance` found that only `Industrial acceptance - initial`, `Industrial acceptance - verified` and `Industrial Acceptance (1)` lack the flag. These are the walkway flows.
- The reservoir, mixer, hospital, restaurant, hydro, structures and later saves all have it. The late-game, rocket, mixer and hospital runs therefore never hit it.

**3. Main-menu panels do not block.** Examples are the experimental `WelcomeScreenBox`, the intro and analytics consent. The loader calls `GameSceneLoader.StartSaveGame` at main-menu frame 30 whatever panel is open. The validating load path (`ValidatingGameLoader`, which shows the mods-compatibility dialog and Load Game Mod Validator's patch) is only used by the Load Game UI, never by the loader.

**4. The crash screen ("Uh oh… a bug").** Timberborn shows it after the first uncaught exception and stops the scene. The run is over at that point. Nothing can dismiss it into a working game.
- A probe of build 121 with `-skipModManager` (2026-10-21 23:43) loaded the mods and ran the loader. It then crashed while loading the game scene: `InvalidOperationException: Launch Pad model must contain exactly one 'LaunchPad.Rocket' node; found 2`.
  - The exception came from `RocketLaunchVisual.Awake`, during `BottomBarPanel` tool-preview creation.
  - `#Unfinished/ConstructionStage0` is a byte-identical copy of the finished Launch Pad mesh.
- Because the crash happens during tool-preview creation, **every build-121 game-scene load crashes**, whichever save is loaded.
- `RocketLaunchVisual.cs` was corrected in source at 23:57, after this probe: the lookup is now limited to the finished model, and `validate_rocket_program.mjs` checks this. Build 121 does not contain the fix.

## What now handles them

- `tools/launch_timberborn.ps1` handles every launcher.
  - It starts `Timberborn.exe` directly with `SteamAppId`/`SteamGameId=1062090` set and always adds `-skipModManager`.
  - `SteamManager.RestartAppIfNecessary` then connects to the running Steam client instead of relaunching.
  - Steam must already be running. If it is not, the launch fails.
  - It removes a previous log of the same name before starting. Unity truncates the log anyway.
  - It needs no rebuild. It was verified on build 121: the mods loaded, there was no Mods screen, Steam connected, and the loader ran.
- `src/DeepFrontier/Scripts/AcceptanceStartupPanels.cs` is bound only with `-deepFrontierLoadAcceptance`. **It takes effect only from the next build.**
  - Game scene, frames 1–59 (every harness first sets up at frame 60): it dismisses each stacked panel exactly as the native Escape key does (`IPanelController.OnUICancelled`). It logs `[DeepFrontier Acceptance] Dismissed startup panel …` with the panel type and its text.
  - A panel that does not close throws.
  - Later panels are only logged (`Panel shown … after the startup window; left for the harness`). The rocket run closes its own dialogs.
  - Main menu: open panels are only logged.
  - Normal play binds nothing.
- `tools/watch_acceptance_log.ps1` waits for one of these outcomes: `done` (the harness's saved/complete line), `failed`, `crash`, `stuck` (no `Modded:` line within 180 s), `exited` or `timeout`.
  - It then closes the game with a window close and exits 0 only for `done`.
  - The late-game, rocket, mixer and hospital launchers take `-Watch`.
  - For other launchers, run the watcher yourself with that harness's completion regex.

## Procedure for the next run

1. Build and install with the official pipeline, which needs a build that includes the corrected `RocketLaunchVisual.cs`. Build 121 crashes on every game load. Verify the package as usual.
2. Start Steam and leave it running. Close Timberborn.
3. Run the launcher with `-Watch`. For example:
   - `pwsh tools/start_lategame_acceptance.ps1 -Build N -Watch`
   - then `python tools/capture_lategame_acceptance.py --build N`
   - Reload: `pwsh tools/start_lategame_acceptance.ps1 -Build N -Reload -Watch`, then the capture with `--reload`.
   - Rocket: `pwsh tools/start_lategame_rocket.ps1 -Build N -Watch`. Add `-Checkpoint preparing|flight|refurbishing` for the reloads.
4. Read the watcher's `outcome:` and `detail:` lines and any `panel:` lines. On `done`, the game is closed 10 s after the save line. On any other outcome, the log is in `outputs/` and the game has been closed.
5. If the outcome is `stuck`, look at the screen: something new is blocking before the mods load. Record what it is here.

The Windows API screenshot helper used for the probes (`System.Drawing` `CopyFromScreen` plus `EnumWindows`) is not part of the tools. The watcher's log outcomes are the run evidence.

## Several game scenes in one process

`pwsh tools/start_scene_cycle.ps1 -Label N` (harness `src/DeepFrontier/Scripts/SceneCycleAcceptance.cs`) loads a copy of the newest Memory Test autosave, returns to the main menu with native `MainMenuSceneLoader.OpenMainMenu`, starts an Iron Teeth new game on `builtin:Canyon`, returns again, and repeats (`-Cycles`, default 2: four games). Every main menu compares the native water and terrain materials with the first menu's record (shader, keywords, every native property value); every game requires the radiation variants on them. The run ends with `[DeepFrontier SceneCycle] COMPLETE`. The launcher backs up the Memory Test folder, restores any file the run removed with its original time, reports any file it added, and removes its save copy.

Keep the Timberborn window focused for the whole run. Timberborn advances no frames while unfocused, so a game scene stops before its frame-60 check and a scene load can stall. In the build-223 run the 4th load sat idle for 15 minutes until the window was focused again, and the user closed it then. Closing the game during a game-scene load logs a native `NullReferenceException` in `SingletonLifecycleService.UnloadSingletons` (the scene is destroyed before `LoadAll`), plus a failed exception save in `FactionService.Save`. Neither comes from the mod.
