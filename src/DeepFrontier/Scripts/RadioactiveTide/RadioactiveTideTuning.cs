using System.Collections.Immutable;

namespace DeepFrontier.Scripts.RadioactiveTide {
  // Radioactive Tide: an optional third hazardous weather (after drought and
  // badtide). During it every native water source keeps flowing clean water
  // but also releases radioactive sludge into the radiation system in
  // proportion to its current strength. See docs/radiation.md, section
  // "Radioactive tide", for the design numbers and the native evidence.
  //
  // Authored tuning lives in code (like RadiationTuning) so every value is
  // visible and checked; tools/validate_radioactive_tide_content.mjs reads
  // these constants from this file to cross-check the content module.
  public static class RadioactiveTideTuning {
    // Hazardous weather id. Native code keys sky fog (SunSpec
    // HazardousWeatherFogs), HazardousWeatherWaterSourceSpec lists and the
    // saved HazardousWeatherHistory by this id.
    public const string WeatherId = "RadioactiveTideWeather";

    // Radioactive share of the non-bad water every native source adds during a
    // tide (IRadiationService.SetSourceRadioactiveShare). 100%, as a native
    // badtide makes source water fully bad: clean sources pour pure radioactive
    // water, and a badwater source's bad share stays bad while the rest is
    // radioactive (bad + radioactive never exceeds 1). A strength-1 source pours
    // IRadiationService.WaterPerStrengthHour water (19.2 units per game hour:
    // strength per simulated second, 0.6 s ticks, 768 ticks per day), so a clean
    // one releases 19.2 radioactive units (96 sludge goods) per game hour.
    public const float SourceRadioactiveShare = 1f;

    // A radioactive tide never follows another one directly: at least this
    // many cycles must lie between two tides.
    public const int CooldownCycles = 1;

    // Cycle 1 is chosen by GameCycleService.Load on a new game, before the
    // rest of the game has loaded; a tide can come from cycle 2 at the earliest.
    public const int EarliestCycle = 2;

    // Per-game settings (derived from each game mode's weather, GameModeCurve
    // below, and edited on the native new-game screen; saved per game). Allowed ranges,
    // as the custom-mode fields clamp them. Tides can happen in cycles after
    // CyclesWithoutTide, like the native "Cycles without badtide"; the
    // lowest value is EarliestCycle - 1 (checked by the content validator).
    public const int CyclesWithoutTideLowest = 1;
    public const int CyclesWithoutTideHighest = 99;
    public const int ChancePercentLowest = 1;
    public const int ChancePercentHighest = 100;
    public const int DurationLowest = 1;
    public const int DurationHighest = 30;

    // Every game mode's radioactive tide settings follow from its own weather
    // (RadioactiveTideGameModes.Derive; docs/radiation.md "Settings per game"),
    // unless its blueprint carries a RadioactiveTideGameModeSpec (the custom
    // mode; a mod may give its own mode one). The rule is this curve, through
    // the native Easy, Normal and Hard modes: each point is that mode's
    // Timberborn 1.1.2.8 weather (NewGameModes/GameMode.*.blueprint.json:
    // TemperateWeatherDuration, DroughtDuration, BadtideDuration in days,
    // ChanceForBadtide in whole percent) and the radioactive tide it gets.
    // A mode is placed on the curve by the share of a cycle its hazardous
    // weather takes (RadioactiveTideModeWeather.HazardShare: Easy 12.9%,
    // Normal 30.6%, Hard 77.6%); between two points every value is linear in
    // that share, beyond Easy or Hard the end segment continues, so a gentler
    // mode than Easy gets later, rarer, shorter tides. Normal keeps the 0.8.3
    // defaults (Legacy* below). tools/validate_radioactive_tide_content.mjs
    // checks each point's weather against the vanilla blueprints, the order,
    // and that the curve stays inside the ranges above for every share in
    // (0, 1], so the rule needs no clamping.
    public static readonly ImmutableArray<RadioactiveTideCurvePoint> GameModeCurve = ImmutableArray.Create(
      //                           mode      temperate  drought  badtide  badtide %   cycles without  chance %  duration
      new RadioactiveTideCurvePoint("Easy",   16, 19,     2, 4,    1, 3,    40,         24,             15,       2, 4),
      new RadioactiveTideCurvePoint("Normal", 13, 17,     5, 9,    4, 8,    40,         14,             25,       3, 6),
      new RadioactiveTideCurvePoint("Hard",    5, 8,     15, 30,  15, 30,   40,          9,             35,       5, 10));

    // Saves from before per-game settings (0.8.3 and older) take the values the
    // player had set in the former Deep Frontier mod settings (eMka.ModSettings
    // stored them in the native ISettings under these keys); a key the player
    // never changed reads as the old default below. The Normal game mode has
    // exactly these defaults (tools/validate_radioactive_tide_content.mjs).
    // Keys: "ModSetting.<ModId>.<owner type>.<property>" (ModSettings.Core
    // 1.1.1.0 ModSettingsOwner.InitializePropertyModSetting) of the removed
    // RadioactiveTideSettings owner.
    public const string LegacyEnabledKey = "ModSetting.DeepFrontier.RadioactiveTideSettings.TideEnabled";
    public const string LegacyMinCycleKey = "ModSetting.DeepFrontier.RadioactiveTideSettings.TideMinCycle";
    public const string LegacyChancePercentKey = "ModSetting.DeepFrontier.RadioactiveTideSettings.TideChancePercent";
    public const string LegacyMinDurationKey = "ModSetting.DeepFrontier.RadioactiveTideSettings.TideMinDurationDays";
    public const string LegacyMaxDurationKey = "ModSetting.DeepFrontier.RadioactiveTideSettings.TideMaxDurationDays";
    public const bool LegacyEnabled = true;
    public const int LegacyMinCycle = 15;
    public const int LegacyChancePercent = 25;
    public const int LegacyMinDurationDays = 3;
    public const int LegacyMaxDurationDays = 6;

    // UI. The CSS class names are deliberately unstyled: native panels add
    // them, and RadioactiveTideUi recognises them and applies inline styles.
    public const string IconSpritePath = "Sprites/Weather/RadioactiveTideIcon";
    // The tide's own weather-panel and banner art: the native badtide wave
    // art recoloured to the radiation yellow-green by
    // tools/radioactive_tide_content.mjs, so the tide never reads as badtide.
    public const string ProgressSpritePath = "Sprites/Weather/RadioactiveTideProgress";
    public const string NotificationSpritePath = "Sprites/Weather/RadioactiveTideNotification";
    public const string DatePanelClass = "deep-frontier-date-panel--radioactive-tide";
    public const string WeatherPanelClass = "deep-frontier-weather-panel--radioactive-tide";
    public const string NotificationClass = "deep-frontier-weather-notification--radioactive-tide";

    // Moddable Weathers 11.0.0 (optional). With it loaded the vanilla path
    // above is off and the tide is a Moddable Weathers hazardous weather,
    // registered by the optional assembly Scripts/RadioactiveTide/ModdableWeathers
    // (packaged as DeepFrontier.ModdableWeathers.dll.ModdableWeathers.optional
    // and loaded by ModdableTimberborn's OptionalModsLoader only when the
    // ModdableWeathers mod is enabled). tools/radioactive_tide_content.mjs
    // writes its ModdableWeatherSpec blueprint from these values. Moddable
    // Weathers' panels draw the spec sprites: the tide's own progress and
    // banner art, the native stripes and the badtide start sound (the same
    // paths as its own BadtideWeather spec).
    public const string ModdableWeathersAssembly = "ModdableWeathers";
    public const string ModdableWeathersBridgeAssembly = "DeepFrontier.ModdableWeathers";
    public const int ModdableWeatherOrder = 35;
    public const string ModdableProgressSpritePath = ProgressSpritePath;
    public const string ModdableBlinkSpritePath = "UI/Images/Backgrounds/bg-striped-4";
    public const string ModdableNotificationSpritePath = NotificationSpritePath;
    public const string ModdableStartSound = "UI.Weather.BadtideStarted";
  }

  public static class RadioactiveTideLoc {
    public const string Name = "DeepFrontier.Weather.RadioactiveTide";
    public const string Approaching = "DeepFrontier.Weather.Notification.RadioactiveTideApproaching";
    public const string InProgress = "DeepFrontier.Weather.Notification.RadioactiveTideInProgress";
    public const string Started = "DeepFrontier.Weather.RadioactiveTideStartedNotification";
    public const string Ended = "DeepFrontier.Weather.RadioactiveTideEndedNotification";
    public const string ApproachingDescription = "DeepFrontier.Weather.RadioactiveTideApproachingDescription";
    public const string StartedDescription = "DeepFrontier.Weather.RadioactiveTideStartedDescription";
    // The native new-game screen's custom mode (RadioactiveTideNewGameSettings):
    // the toggle reuses SettingEnabled; the rows follow the native badtide rows
    // ("Cycles without badtide", "Badtide chance", "Badtide duration").
    public const string NewGameCyclesWithout = "DeepFrontier.NewGame.CyclesWithoutRadioactiveTide";
    public const string NewGameChance = "DeepFrontier.NewGame.RadioactiveTideChance";
    public const string NewGameDuration = "DeepFrontier.NewGame.RadioactiveTideDuration";
    // Moddable Weathers' Weather Settings dialog labels for the per-save
    // values (RadioactiveTideModdableWeatherSettings).
    public const string SettingEnabled = "DeepFrontier.RadioactiveTide.Settings.Enabled";
    public const string SettingMinCycle = "DeepFrontier.RadioactiveTide.Settings.MinCycle";
    public const string SettingChance = "DeepFrontier.RadioactiveTide.Settings.Chance";
    public const string SettingMinDuration = "DeepFrontier.RadioactiveTide.Settings.MinDuration";
    public const string SettingMaxDuration = "DeepFrontier.RadioactiveTide.Settings.MaxDuration";
    // Moddable Weathers: the weather description in its Weather Settings
    // dialog (ModdableWeatherSpec.DescLoc), and the per-save setting
    // descriptions it looks up as <setting label key> + "Desc"
    // (ModdableWeathers.UI.Settings.SettingElement.AddTwoColumns).
    public const string ModdableDescription = "DeepFrontier.Weather.RadioactiveTideDescription";
    public const string SettingEnabledModdableDesc = "DeepFrontier.RadioactiveTide.Settings.EnabledDesc";
    public const string SettingMinCycleModdableDesc = "DeepFrontier.RadioactiveTide.Settings.MinCycleDesc";
    public const string SettingChanceModdableDesc = "DeepFrontier.RadioactiveTide.Settings.ChanceDesc";
    public const string SettingMinDurationModdableDesc = "DeepFrontier.RadioactiveTide.Settings.MinDurationDesc";
    public const string SettingMaxDurationModdableDesc = "DeepFrontier.RadioactiveTide.Settings.MaxDurationDesc";
  }

  // A game's radioactive tide settings. Without Moddable Weathers they are
  // RadioactiveTideGameSettings (saved per game, started from the new game's
  // mode, RadioactiveTideGameModes.For); with it, the per-save values of
  // RadioactiveTideModdableWeatherSettings play this part.
  public interface IRadioactiveTideSettings {
    bool Enabled { get; }
    // Tides can happen from cycle CyclesWithoutTide + 1.
    int CyclesWithoutTide { get; }
    int ChancePercent { get; }
    int MinDurationDays { get; }
    int MaxDurationDays { get; }
  }
}
