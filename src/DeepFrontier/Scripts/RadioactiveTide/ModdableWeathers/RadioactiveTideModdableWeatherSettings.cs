#if !UNITY_EDITOR
using System;
using System.ComponentModel;
using DeepFrontier.Scripts.RadioactiveTide;
using ModdableWeathers.Weathers.Settings;
using Timberborn.NewGameConfigurationSystem;

namespace DeepFrontier.RadioactiveTideModdableWeathers {
  // Per-save radioactive tide settings under Moddable Weathers. Moddable
  // Weathers lists every public read/write property with a [Description]
  // in its Weather Settings dialog (label: the description key; text under
  // it: key + "Desc"), saves them as JSON in its ModdableWeatherSettingsService
  // singleton under this type's full name, and treats the bool "Enabled"
  // as the weather's enable toggle (ModdableWeathers Common/Settings/
  // IBaseWeatherSettings.cs, UI/Settings/SettingElement.cs).
  //
  // The same five values as the Deep Frontier mod settings, with the same
  // ranges and the same meaning: ChancePercent is the probability that a
  // hazardous stage becomes a tide, not a Moddable Weathers weight
  // (RadioactiveTideModdableWeather.GetChance converts it).
  //
  // Sync with the Deep Frontier mod settings (eMka.ModSettings, global):
  // Moddable Weathers calls InitializeNewValuesTo once per save, the first
  // time the save loads with this weather (new game, or an older save
  // without these settings). The values are then copied from the Deep
  // Frontier mod settings. Afterwards the save keeps its own values, edited
  // only in Moddable Weathers' Weather Settings dialog; later changes to the
  // Deep Frontier mod settings apply to saves seeded after the change.
  // Moddable Weathers' default-settings file and profile import can also
  // overwrite them, like any Moddable Weathers weather setting.
  public sealed class RadioactiveTideModdableWeatherSettings : IModdableWeatherSettings {
    private readonly IRadioactiveTideSettings _modSettings;

    public RadioactiveTideModdableWeatherSettings(IRadioactiveTideSettings modSettings) {
      _modSettings = modSettings;
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

    public bool CanSupport(GameModeSpec gameMode) => true;

    public void InitializeNewValuesTo(GameModeSpec gameMode) {
      if (!_modSettings.IsLoaded)
        throw new InvalidOperationException("Radioactive tide: Moddable Weathers initialised the tide settings before eMka.ModSettings loaded the Deep Frontier settings");
      RadioactiveTideSettingsCheck.Validate(_modSettings);
      Enabled = _modSettings.Enabled;
      StartCycle = _modSettings.MinCycle;
      ChancePercent = _modSettings.ChancePercent;
      MinDurationDays = _modSettings.MinDurationDays;
      MaxDurationDays = _modSettings.MaxDurationDays;
    }

    public const string WhereToFix = "Moddable Weathers' Weather Settings (Radioactive tide)";

    public void Validate() =>
      RadioactiveTideSettingsCheck.ValidateValues(StartCycle, ChancePercent, MinDurationDays, MaxDurationDays, WhereToFix);
  }
}
#endif
