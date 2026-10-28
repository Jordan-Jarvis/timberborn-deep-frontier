using System;
using Timberborn.Common;
using Timberborn.HazardousWeatherSystem;

namespace DeepFrontier.Scripts.RadioactiveTide {
  // The third hazardous weather. Native HazardousWeatherService stores it as
  // CurrentCycleHazardousWeather and posts the native selected/started/ended
  // events with it; native systems that test `is DroughtWeather` or
  // `is BadtideWeather` treat it as neither, so sources keep their clean flow.
  public sealed class RadioactiveTideWeather : IHazardousWeather {
    private readonly IRandomNumberGenerator _random;
    private readonly IRadioactiveTideSettings _settings;

    public RadioactiveTideWeather(IRandomNumberGenerator random, IRadioactiveTideSettings settings) {
      _random = random; _settings = settings;
    }

    public string Id => RadioactiveTideTuning.WeatherId;

    // Native passes the count of earlier occurrences + 1, not the cycle.
    // Radioactive tides have no early-game handicap; the duration is uniform
    // over the player's whole-day range.
    public int GetDurationAtCycle(int cycle) {
      RadioactiveTideSettingsCheck.Validate(_settings);
      return _random.Range(_settings.MinDurationDays, _settings.MaxDurationDays + 1);
    }

    public override string ToString() => Id;
  }

  // Public for the optional Moddable Weathers assembly
  // (Scripts/RadioactiveTide/ModdableWeathers), which checks its per-save copy of
  // the same five values against the same ranges.
  public static class RadioactiveTideSettingsCheck {
    public const string MainMenuSettings = "the main menu mod settings";

    public static void Validate(IRadioactiveTideSettings settings) {
      if (settings == null) throw new InvalidOperationException("Radioactive tide settings are not bound");
      if (!settings.IsLoaded) throw new InvalidOperationException("Radioactive tide settings were read before eMka.ModSettings loaded them");
      ValidateValues(settings.MinCycle, settings.ChancePercent, settings.MinDurationDays, settings.MaxDurationDays, MainMenuSettings);
    }

    // fixWhere names the place the player edits these values.
    public static void ValidateValues(int minCycle, int chancePercent, int minDurationDays, int maxDurationDays, string fixWhere) {
      Require(minCycle, RadioactiveTideTuning.MinCycleLowest, RadioactiveTideTuning.MinCycleHighest, "earliest cycle", fixWhere);
      Require(chancePercent, RadioactiveTideTuning.ChancePercentLowest, RadioactiveTideTuning.ChancePercentHighest, "chance per cycle", fixWhere);
      Require(minDurationDays, RadioactiveTideTuning.DurationLowest, RadioactiveTideTuning.DurationHighest, "shortest tide", fixWhere);
      Require(maxDurationDays, RadioactiveTideTuning.DurationLowest, RadioactiveTideTuning.DurationHighest, "longest tide", fixWhere);
      if (minDurationDays > maxDurationDays)
        throw new InvalidOperationException($"Radioactive tide settings: the shortest tide ({minDurationDays} days) is longer than the longest tide ({maxDurationDays} days). Fix it in {fixWhere}.");
    }

    private static void Require(int value, int lowest, int highest, string name, string fixWhere) {
      if (value < lowest || value > highest)
        throw new InvalidOperationException($"Radioactive tide setting '{name}' is {value}; allowed {lowest}..{highest}. Fix it in {fixWhere}.");
    }
  }
}
