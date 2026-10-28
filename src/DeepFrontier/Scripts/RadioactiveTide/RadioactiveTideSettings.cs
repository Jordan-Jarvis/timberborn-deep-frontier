#if !UNITY_EDITOR
using Bindito.Core;
using ModSettings.Common;
using ModSettings.Core;
using Timberborn.Modding;
using Timberborn.SettingsSystem;

namespace DeepFrontier.Scripts.RadioactiveTide {
  // Player options for the radioactive tide, shown by eMka.ModSettings
  // (required by the manifest) under Deep Frontier in the main-menu mod
  // settings. The native new-game/difficulty settings cannot carry them:
  // GameModeSpec is a fixed record (Timberborn 1.1.2.8) and its panel lists
  // only native fields.
  //
  // Values are global for this player (ModSettings stores them in
  // modSettings.json, keys "ModSetting.DeepFrontier.RadioactiveTideSettings.<property>")
  // and are read live at every cycle's weather selection. They are
  // changeable in the main menu only (the ModSettings default), so they
  // cannot change half-way through a tide, and RadioactiveTideService checks
  // them when a game loads. An unset option is the ModSettings default
  // listed in RadioactiveTideTuning.
  internal sealed class RadioactiveTideSettings : ModSettingsOwner, IRadioactiveTideSettings {
    public RadioactiveTideSettings(ISettings settings, ModSettingsOwnerRegistry modSettingsOwnerRegistry, ModRepository modRepository)
      : base(settings, modSettingsOwnerRegistry, modRepository) {
    }

    protected override string ModId => "DeepFrontier";
    public override string HeaderLocKey => RadioactiveTideLoc.SettingsHeader;

    public ModSetting<bool> TideEnabled { get; } = new ModSetting<bool>(RadioactiveTideTuning.DefaultEnabled,
      Describe(RadioactiveTideLoc.SettingEnabled, RadioactiveTideLoc.SettingEnabledTooltip));
    public RangeIntModSetting TideMinCycle { get; } = new RangeIntModSetting(RadioactiveTideTuning.DefaultMinCycle,
      RadioactiveTideTuning.MinCycleLowest, RadioactiveTideTuning.MinCycleHighest,
      Describe(RadioactiveTideLoc.SettingMinCycle, RadioactiveTideLoc.SettingMinCycleTooltip));
    public RangeIntModSetting TideChancePercent { get; } = new RangeIntModSetting(RadioactiveTideTuning.DefaultChancePercent,
      RadioactiveTideTuning.ChancePercentLowest, RadioactiveTideTuning.ChancePercentHighest,
      Describe(RadioactiveTideLoc.SettingChance, RadioactiveTideLoc.SettingChanceTooltip));
    public RangeIntModSetting TideMinDurationDays { get; } = new RangeIntModSetting(RadioactiveTideTuning.DefaultMinDurationDays,
      RadioactiveTideTuning.DurationLowest, RadioactiveTideTuning.DurationHighest,
      Describe(RadioactiveTideLoc.SettingMinDuration, RadioactiveTideLoc.SettingMinDurationTooltip));
    public RangeIntModSetting TideMaxDurationDays { get; } = new RangeIntModSetting(RadioactiveTideTuning.DefaultMaxDurationDays,
      RadioactiveTideTuning.DurationLowest, RadioactiveTideTuning.DurationHighest,
      Describe(RadioactiveTideLoc.SettingMaxDuration, RadioactiveTideLoc.SettingMaxDurationTooltip));

    public bool IsLoaded { get; private set; }
    public bool Enabled => TideEnabled.Value;
    public int MinCycle => TideMinCycle.Value;
    public int ChancePercent => TideChancePercent.Value;
    public int MinDurationDays => TideMinDurationDays.Value;
    public int MaxDurationDays => TideMaxDurationDays.Value;

    protected override void OnAfterLoad() => IsLoaded = true;

    private static ModSettingDescriptor Describe(string nameLocKey, string tooltipLocKey) =>
      ModSettingDescriptor.CreateLocalized(nameLocKey).SetLocalizedTooltip(tooltipLocKey);
  }

  // Bound wherever ModSettings shows or reads options: the main menu (to edit
  // them) and the game (to read them).
  [Context("MainMenu")]
  [Context("Game")]
  public sealed class RadioactiveTideSettingsConfigurator : Configurator {
    protected override void Configure() {
      Bind<RadioactiveTideSettings>().AsSingleton();
      Bind<IRadioactiveTideSettings>().ToExisting<RadioactiveTideSettings>();
    }
  }
}
#endif
