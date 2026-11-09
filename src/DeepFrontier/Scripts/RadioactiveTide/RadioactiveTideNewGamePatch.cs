#if !UNITY_EDITOR
using HarmonyLib;
using Timberborn.ModManagerScene;
using Timberborn.NewGameConfigurationSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.RadioactiveTide {
  // Why Harmony (Timberborn 1.1.2.8, decompiled Timberborn.MainMenuPanels and
  // Timberborn.NewGameConfigurationSystem): the presets need none, their
  // radioactive tide settings follow from their own weather
  // (RadioactiveTideGameModes.For). The custom mode is built inside the
  // native CustomNewGameModeController.TryGetValidatedGameMode as a new
  // GameModeSpec whose blueprint holds only itself, and NewGameModePanel
  // passes it straight to GameSceneLoader.StartNewGame; GameModeSpec is a
  // fixed record and nothing in that path is bound through an interface or
  // raises an event. The same method decides whether the native Start button
  // is enabled. This postfix is the one place both happen:
  // - it returns false while the radioactive tide rows are invalid, so the
  //   native Start button stays disabled (as for the native fields);
  // - it returns a copy of the custom GameModeSpec whose blueprint also holds
  //   the custom RadioactiveTideGameModeSpec, so a custom game carries its
  //   tide settings into the Game scene exactly as a preset does.
  // Nothing else of the native mode changes, and nothing is saved here.
  //
  // Applied with or without Moddable Weathers (both read the new game's mode).
  // RadioactiveTideNewGameNative.Verify() checks every native member this
  // relies on first and throws if a game update changed one.
  internal sealed class RadioactiveTideNewGameModStarter : IModStarter {
    private const string HarmonyId = "DeepFrontier.RadioactiveTideNewGame";

    public void StartMod(IModEnvironment modEnvironment) {
      NativePatches.Install(HarmonyId, RadioactiveTideNewGameNative.Verify, harmony => harmony.Patch(RadioactiveTideNewGameNative.CustomTryGetValidatedGameMode(),
        postfix: new HarmonyMethod(typeof(RadioactiveTideNewGamePatch), nameof(RadioactiveTideNewGamePatch.Postfix))));
      Debug.Log("[DeepFrontier] Radioactive tide new-game settings applied (CustomNewGameModeController.TryGetValidatedGameMode postfix).");
    }
  }

  internal static class RadioactiveTideNewGamePatch {
    internal static void Postfix(ref bool __result, ref GameModeSpec gameMode) {
      // Validated (and marked) even when a native field is invalid, as native
      // ValidateGameMode marks every invalid field at once.
      bool tideValid = RadioactiveTideNewGameSettings.RequireCurrent().TryGetValidated(out var tide);
      if (!__result) return;
      if (!tideValid) {
        __result = false;
        gameMode = null;
        return;
      }
      gameMode = RadioactiveTideGameModes.WithTide(gameMode, tide);
    }
  }
}
#endif
