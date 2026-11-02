using System;
using System.Collections.Immutable;
using Timberborn.BlueprintSystem;
using Timberborn.NewGameConfigurationSystem;

namespace DeepFrontier.Scripts.RadioactiveTide {
  // The radioactive tide settings of a game mode, the counterpart of the
  // native badtide fields of GameModeSpec (Timberborn 1.1.2.8:
  // CyclesBeforeRandomizingBadtide, ChanceForBadtide, BadtideDuration).
  //
  // Native game modes are blueprints (NewGameModes/GameMode.{Easy,Normal,Hard})
  // with one GameModeSpec. GameModeSpec is a fixed record, so the tide values
  // are a second component of the same blueprint: tools/radioactive_tide_content.mjs
  // writes Data/NewGameModes/GameMode.*.blueprint.json, which the native
  // BlueprintFileBundleLoader merges into the vanilla file at the same path.
  // A preset's GameModeSpec reaches the tide through ComponentSpec.GetSpec.
  // The custom mode is a GameModeSpec built by CustomNewGameModeController
  // without a blueprint of its own; RadioactiveTideNewGamePatch gives it one
  // that also holds the custom tide values (WithTide).
  //
  // The new game's GameModeSpec travels in GameSceneParameters into the Game
  // scene, where RadioactiveTideStartingValues reads this spec once and the
  // game then saves its own copy, as native BadtideWeather does.
  public record RadioactiveTideGameModeSpec : ComponentSpec {
    [Serialize]
    public bool Enabled { get; init; }

    // Tides can happen in cycles after this one.
    [Serialize]
    public int CyclesWithoutTide { get; init; }

    // Chance per cycle that the cycle's hazardous season is a tide.
    [Serialize]
    public int ChancePercent { get; init; }

    // Whole days, uniform between Min and Max.
    [Serialize]
    public MinMaxSpec<int> Duration { get; init; }
  }

  public static class RadioactiveTideGameModes {
    // The tide settings of a game mode; a mode without them is an error
    // (every native game-mode blueprint carries them, and the custom mode is
    // given them before the game starts).
    public static RadioactiveTideGameModeSpec Require(GameModeSpec gameMode, string what) {
      if (gameMode == null) throw new ArgumentNullException(nameof(gameMode));
      if (gameMode.Blueprint == null)
        throw new InvalidOperationException($"Radioactive tide: {what} has no blueprint, so its radioactive tide settings cannot be read");
      return gameMode.GetSpec<RadioactiveTideGameModeSpec>()
        ?? throw new InvalidOperationException($"Radioactive tide: {what} has no RadioactiveTideGameModeSpec "
          + $"({gameMode.DisplayNameLocKey ?? "custom"}{(gameMode.Blueprint.Name != null ? $", blueprint {gameMode.Blueprint.Name}" : "")}). "
          + "Every game mode needs radioactive tide settings (Deep Frontier Data/NewGameModes).");
    }

    // A copy of the custom mode whose blueprint also holds the tide settings
    // (native Blueprint(name, specs, children) copies each spec with
    // Blueprint = the new blueprint).
    public static GameModeSpec WithTide(GameModeSpec customMode, RadioactiveTideGameModeSpec tide) {
      if (customMode == null) throw new ArgumentNullException(nameof(customMode));
      if (tide == null) throw new ArgumentNullException(nameof(tide));
      if (customMode.Blueprint == null || customMode.Blueprint.Specs.Length != 1)
        throw new InvalidOperationException("Radioactive tide: the native custom game mode is no longer a lone GameModeSpec");
      var blueprint = new Blueprint(customMode.Blueprint.Name, new ComponentSpec[] { customMode, tide }, ImmutableArray<Blueprint>.Empty);
      var copy = blueprint.GetSpec<GameModeSpec>();
      if (copy == null || copy.GetSpec<RadioactiveTideGameModeSpec>() == null)
        throw new InvalidOperationException("Radioactive tide: the custom game mode copy lost its radioactive tide settings");
      return copy;
    }

    public static RadioactiveTideGameModeSpec Create(bool enabled, int cyclesWithoutTide, int chancePercent, int minDurationDays, int maxDurationDays) =>
      new RadioactiveTideGameModeSpec {
        Enabled = enabled,
        CyclesWithoutTide = cyclesWithoutTide,
        ChancePercent = chancePercent,
        Duration = new MinMaxSpec<int> { Min = minDurationDays, Max = maxDurationDays },
      };
  }
}
