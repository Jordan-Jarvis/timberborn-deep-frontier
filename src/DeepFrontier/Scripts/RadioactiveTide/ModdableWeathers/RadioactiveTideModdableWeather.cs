#if !UNITY_EDITOR
using System;
using System.Linq;
using Bindito.Core;
using DeepFrontier.Scripts.RadioactiveTide;
using ModdableWeathers.Historical;
using ModdableWeathers.Weathers;
using ModdableWeathers.Weathers.Settings;
using Timberborn.Common;
using Timberborn.HazardousWeatherSystem;

namespace DeepFrontier.RadioactiveTideModdableWeathers {
  // The radioactive tide as a Moddable Weathers hazardous weather
  // (IModdableHazardousWeather), with the same rules as the vanilla path
  // (RadioactiveTideService.Choose, RadioactiveTideWeather):
  // - only when enabled, from the earliest cycle on, never in a cycle right
  //   after a tide (RadioactiveTideTuning.CooldownCycles) nor twice in one
  //   cycle;
  // - with probability ChancePercent per hazardous stage, replacing the
  //   other hazardous weathers' roll;
  // - lasting MinDurationDays..MaxDurationDays whole days, uniform, with no
  //   early-game handicap.
  //
  // Chance. Moddable Weathers picks a stage's weather by weight: each
  // enabled hazardous weather returns a weight from GetChance and one is
  // drawn in proportion (Cycles/WeatherGenerator.DecideWeather). For the
  // tide to win with probability p it returns w = others * p / (1 - p),
  // where others is the summed weight of the other enabled hazardous
  // weathers for the same stage. w is rounded to a whole weight and is at
  // least 1, so the drawn probability is w / (w + others): with Moddable
  // Weathers' default drought + badtide weights (100 together) the error is
  // under half a percentage point. At 100 % the tide takes the whole roll
  // except a 1 in (2^31 - 1) remainder. When no other hazardous weather can
  // occur in the stage the tide is the only candidate and is chosen whenever
  // it is eligible (otherwise the stage would get Moddable Weathers' "No
  // Hazardous Weather").
  //
  // State. Nothing of its own is saved: the chosen stages and durations are
  // Moddable Weathers' WeatherHistoryRegistry, the settings its
  // ModdableWeatherSettingsService, and Active is restored by
  // WeatherCycleService calling Start when a save loads inside a tide.
  public sealed class RadioactiveTideModdableWeather : ModdableWeatherBase, IModdableHazardousWeather,
      IModdableWeatherWithSettings<RadioactiveTideModdableWeatherSettings> {
    private readonly ModdableWeatherSpecService _specs;
    private readonly ModdableWeatherSettingsService _settingsService;
    private readonly IContainer _container;
    private readonly IRandomNumberGenerator _random;
    // Resolved on first use: the registry is constructed from every
    // IModdableWeather, this one included, so it cannot be a constructor
    // argument here.
    private ModdableWeatherRegistry _registry;
    private int _forcedCycle;

    public RadioactiveTideModdableWeather(ModdableWeatherSpecService specs, ModdableWeatherSettingsService settingsService,
        IContainer container, IRandomNumberGenerator random) : base(specs) {
      _specs = specs; _settingsService = settingsService; _container = container; _random = random;
    }

    public override string Id => RadioactiveTideTuning.WeatherId;
    public override bool Enabled => Settings.Enabled;
    public RadioactiveTideModdableWeatherSettings Settings { get; private set; }

    public override void Load() {
      if (!_specs.SpecsById.ContainsKey(Id))
        throw new InvalidOperationException($"Radioactive tide: Moddable Weathers has no ModdableWeatherSpec '{Id}' (Deep Frontier ModdableWeatherSpecs/{Id}.blueprint.json is missing)");
      base.Load();
      ReloadSettings();
    }

    public void ReloadSettings() {
      Settings = _settingsService.GetSettings<RadioactiveTideModdableWeatherSettings>();
    }

    public override int GetChance(WeatherCycleStageDecision stageDecision, WeatherCycleDecision cycleDecision, WeatherHistoryService history) {
      if (stageDecision.IsBenign)
        throw new InvalidOperationException($"Radioactive tide: Moddable Weathers asked a hazardous weather for a benign stage (cycle {cycleDecision.Cycle}, stage {stageDecision.StageIndex})");
      int cycle = cycleDecision.Cycle;
      if (cycle == _forcedCycle) return int.MaxValue - checked((int)OtherHazardousWeight(stageDecision, cycleDecision, history));
      Settings.Validate();
      if (cycle < Settings.StartCycle) return 0;
      if (TideBefore(stageDecision, cycleDecision, history)) return 0;
      long others = OtherHazardousWeight(stageDecision, cycleDecision, history);
      int percent = Settings.ChancePercent;
      if (percent == 100) return int.MaxValue - checked((int)others);
      if (others == 0) return 1;
      long weight = Math.Max(1L, (long)Math.Round(others * percent / (double)(100 - percent)));
      if (others + weight > int.MaxValue)
        throw new InvalidOperationException($"Radioactive tide: the hazardous weather weights ({others} + {weight}) exceed Moddable Weathers' integer roll");
      return (int)weight;
    }

    public override int GetDuration(WeatherCycleStageDecision stageDecision, WeatherCycleDecision cycleDecision, WeatherHistoryService history) {
      Settings.Validate();
      return _random.Range(Settings.MinDurationDays, Settings.MaxDurationDays + 1);
    }

    // Dev mode (RadioactiveTideModdableDevModule): the next generation of
    // `cycle` makes its first hazardous stage a tide, ignoring the earliest
    // cycle, the chance and the cooldown. 0 clears it.
    internal void ForceForCycle(int cycle) {
      if (cycle != 0 && !Settings.Enabled)
        throw new InvalidOperationException($"Radioactive tides are disabled in {RadioactiveTideModdableWeatherSettings.WhereToFix}");
      _forcedCycle = cycle;
    }

    private bool TideBefore(WeatherCycleStageDecision stageDecision, WeatherCycleDecision cycleDecision, WeatherHistoryService history) {
      if (cycleDecision.Stages.Any(s => s.StageIndex < stageDecision.StageIndex && s.Weather == this)) return true;
      for (int back = 1; back <= RadioactiveTideTuning.CooldownCycles; back++) {
        int earlier = cycleDecision.Cycle - back;
        if (earlier < 1) break;
        if (history.GetWeatherCycle(earlier).Stages.Any(s => s.Weather.Id == Id)) return true;
      }
      return false;
    }

    // The summed weight of the other enabled hazardous weathers for this
    // stage, as WeatherGenerator.DecideWeather adds them.
    private long OtherHazardousWeight(WeatherCycleStageDecision stageDecision, WeatherCycleDecision cycleDecision, WeatherHistoryService history) {
      _registry ??= _container.GetInstance<ModdableWeatherRegistry>();
      long sum = 0;
      foreach (IModdableWeather weather in _registry.HazardousWeathers) {
        if (ReferenceEquals(weather, this) || !weather.Enabled) continue;
        int chance = weather.GetChance(stageDecision, cycleDecision, history);
        if (chance < 0) throw new InvalidOperationException($"Radioactive tide: hazardous weather {weather.Id} returned a negative weight {chance}");
        sum += chance;
      }
      if (sum >= int.MaxValue)
        throw new InvalidOperationException($"Radioactive tide: the other hazardous weather weights ({sum}) fill Moddable Weathers' integer roll");
      return sum;
    }
  }
}
#endif
