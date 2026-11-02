#if !UNITY_EDITOR
using System.ComponentModel;
using DeepFrontier.Scripts.RadioactiveTide;
using ModdableWeathers.Weathers.Settings;
using Timberborn.NewGameConfigurationSystem;
using Timberborn.WorldPersistence;
using Timberborn.SceneLoading;
using Timberborn.SettingsSystem;
using UnityEngine;

namespace DeepFrontier.RadioactiveTideModdableWeathers {
  // Per-save radioactive tide settings under Moddable Weathers. Moddable
  // Weathers lists every public read/write property with a [Description]
  // in its Weather Settings dialog (label: the description key; text under
  // it: key + "Desc"), saves them as JSON in its ModdableWeatherSettingsService
  // singleton under this type's full name, and treats the bool "Enabled"
  // as the weather's enable toggle (ModdableWeathers Common/Settings/
  // IBaseWeatherSettings.cs, UI/Settings/SettingElement.cs).
  //
  // With Moddable Weathers these are the game's only radioactive tide
  // settings (the vanilla RadioactiveTideGameSettings is not bound), edited
  // in Moddable Weathers' Weather Settings dialog. StartCycle is the earliest
  // cycle (the new-game screen's "cycles without radioactive tide" + 1);
  // ChancePercent is the probability that a hazardous stage becomes a tide,
  // not a Moddable Weathers weight (RadioactiveTideModdableWeather.GetChance
  // converts it).
  //
  // Seeding: Moddable Weathers calls InitializeNewValuesTo once per save, the
  // first time the save loads with this weather (a new game, or a save
  // without these settings), with the first game mode CanSupport accepts of
  // PersistentGameModeService's ReconstructedMode (the new game's mode),
  // BestMatchedMode and Default. The values come from
  // RadioactiveTideStartingValues, the same order the vanilla path uses: the
  // save's vanilla tide settings (a save played without Moddable Weathers),
  // else the new game's mode (its RadioactiveTideGameModeSpec from the
  // new-game screen), else the former Deep Frontier mod settings (a save from
  // before per-game settings). Moddable Weathers' default-settings file and
  // profile import can overwrite them later, like any of its weather settings.
  public sealed class RadioactiveTideModdableWeatherSettings : IModdableWeatherSettings {
    private readonly ISingletonLoader _singletonLoader;
    private readonly ISceneLoader _sceneLoader;
    private readonly ISettings _settings;

    public RadioactiveTideModdableWeatherSettings(ISingletonLoader singletonLoader, ISceneLoader sceneLoader, ISettings settings) {
      _singletonLoader = singletonLoader; _sceneLoader = sceneLoader; _settings = settings;
    }

    [Description(RadioactiveTideLoc.SettingEnabled)]
    public bool Enabled { get; set; }

    [Description(RadioactiveTideLoc.SettingMinCycle)]
    public int StartCycle { get; set; }

    [Description(RadioactiveTideLoc.SettingChance)]
    public int ChancePercent { get; set; }

    [Description(RadioactiveTideLoc.SettingMinDuration)]
    public int MinDurationDays { get; set; }

    [Description(RadioactiveTideLoc.SettingMaxDuration)]
    public int MaxDurationDays { get; set; }

    public bool FirstLoad { get; set; }

    // The values do not come from the offered game mode (see above), so the
    // first candidate is taken.
    public bool CanSupport(GameModeSpec gameMode) => true;

    public void InitializeNewValuesTo(GameModeSpec gameMode) {
      var values = RadioactiveTideStartingValues.Resolve(_singletonLoader, _sceneLoader, _settings);
      Enabled = values.Enabled;
      StartCycle = values.CyclesWithoutTide + 1;
      ChancePercent = values.ChancePercent;
      MinDurationDays = values.MinDurationDays;
      MaxDurationDays = values.MaxDurationDays;
      Debug.Log($"[DeepFrontier] Moddable Weathers radioactive tide settings seeded: {values}.");
    }

    public const string WhereToFix = "Moddable Weathers' Weather Settings (Radioactive tide)";

    public void Validate() {
      RadioactiveTideSettingsCheck.Require(StartCycle, RadioactiveTideTuning.CyclesWithoutTideLowest + 1, RadioactiveTideTuning.CyclesWithoutTideHighest + 1,
        "earliest cycle", WhereToFix);
      RadioactiveTideSettingsCheck.ValidateChanceAndDuration(ChancePercent, MinDurationDays, MaxDurationDays, WhereToFix);
    }
  }
}
#endif
