
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

    // Cycle 1 is chosen by GameCycleService.Load on a new game before the
    // mod settings load; the minimum-cycle setting cannot go below this.
    public const int EarliestCycle = 2;

    // Player options (eMka.ModSettings): defaults and slider ranges.
    public const bool DefaultEnabled = true;
    public const int DefaultMinCycle = 15;
    public const int MinCycleLowest = EarliestCycle;
    public const int MinCycleHighest = 100;
    public const int DefaultChancePercent = 25;
    public const int ChancePercentLowest = 1;
    public const int ChancePercentHighest = 100;
    public const int DefaultMinDurationDays = 3;
    public const int DefaultMaxDurationDays = 6;
    public const int DurationLowest = 1;
    public const int DurationHighest = 30;

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
    public const string SettingsHeader = "DeepFrontier.RadioactiveTide.Settings.Header";
    public const string SettingEnabled = "DeepFrontier.RadioactiveTide.Settings.Enabled";
    public const string SettingEnabledTooltip = "DeepFrontier.RadioactiveTide.Settings.Enabled.Tooltip";
    public const string SettingMinCycle = "DeepFrontier.RadioactiveTide.Settings.MinCycle";
    public const string SettingMinCycleTooltip = "DeepFrontier.RadioactiveTide.Settings.MinCycle.Tooltip";
    public const string SettingChance = "DeepFrontier.RadioactiveTide.Settings.Chance";
    public const string SettingChanceTooltip = "DeepFrontier.RadioactiveTide.Settings.Chance.Tooltip";
    public const string SettingMinDuration = "DeepFrontier.RadioactiveTide.Settings.MinDuration";
    public const string SettingMinDurationTooltip = "DeepFrontier.RadioactiveTide.Settings.MinDuration.Tooltip";
    public const string SettingMaxDuration = "DeepFrontier.RadioactiveTide.Settings.MaxDuration";
    public const string SettingMaxDurationTooltip = "DeepFrontier.RadioactiveTide.Settings.MaxDuration.Tooltip";
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

  // Player options, read live. Implemented with eMka.ModSettings
  // (RadioactiveTideSettings); kept as an interface so the core compiles in
  // the Unity editor, where the ModSettings assemblies are excluded.
  public interface IRadioactiveTideSettings {
    bool IsLoaded { get; }
    bool Enabled { get; }
    int MinCycle { get; }
    int ChancePercent { get; }
    int MinDurationDays { get; }
    int MaxDurationDays { get; }
  }
}
