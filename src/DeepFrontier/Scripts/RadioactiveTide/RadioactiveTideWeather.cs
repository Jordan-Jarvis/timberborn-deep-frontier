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
    // over the game's whole-day range. Tides are only chosen while enabled.
    public int GetDurationAtCycle(int cycle) {
      if (!_settings.Enabled) throw new InvalidOperationException("Radioactive tide: a duration was drawn while radioactive tides are off in this game");
      RadioactiveTideSettingsCheck.Validate(_settings, "this game");
      return _random.Range(_settings.MinDurationDays, _settings.MaxDurationDays + 1);
    }

    public override string ToString() => Id;
  }
}
