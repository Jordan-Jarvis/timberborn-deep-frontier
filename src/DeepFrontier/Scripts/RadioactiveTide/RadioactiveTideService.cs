using System;
using DeepFrontier.Scripts.Radiation;
using Timberborn.Common;
using Timberborn.EntitySystem;
using Timberborn.GameCycleSystem;
using Timberborn.HazardousWeatherSystem;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSourceSystem;
using Timberborn.WeatherSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.RadioactiveTide {
  // Chooses radioactive tides, keeps their saved state and makes the water of
  // every native water source partly radioactive while one is in progress.
  //
  // Selection (RadioactiveTidePatches postfix on the native
  // HazardousWeatherRandomizer.GetRandomWeatherForCycle): from the player's
  // earliest cycle onward, with the player's chance per cycle, the cycle's
  // hazardous weather becomes a radioactive tide instead of the native
  // drought/badtide choice, never in two consecutive cycles
  // (RadioactiveTideTuning.CooldownCycles).
  //
  // Emission: while WeatherService.IsHazardousWeather and the cycle's weather
  // is the tide, IRadiationService.SetSourceRadioactiveShare makes
  // SourceRadioactiveShare (100%) of the non-bad water
  // every native source adds radioactive (native UpdateWaterSourcesTask adds
  // the water; RadiationSimulation mixes the share in). CurrentStrength already
  // includes the native modifiers, so a source that stops flowing also stops
  // releasing radioactivity. The share returns to 0 when the cycle ends.
  //
  // Saved (singleton DeepFrontier.RadioactiveTide): whether the current
  // cycle's weather is the tide, the last tide's cycle and duration, and the
  // sludge emitted by that tide. Native HazardousWeatherService saves only
  // IsDrought, so RestoreAfterNativeLoad (postfix on its Load) puts the tide
  // back before anything else reads the weather.
  public sealed class RadioactiveTideService : ILoadableSingleton, IPostLoadableSingleton, ISaveableSingleton,
      ITickableSingleton, IUnloadableSingleton {
    private static readonly SingletonKey Key = new SingletonKey("DeepFrontier.RadioactiveTide");
    private static readonly PropertyKey<bool> CurrentCycleIsTideKey = new PropertyKey<bool>("CurrentCycleIsTide");
    private static readonly PropertyKey<int> LastTideCycleKey = new PropertyKey<int>("LastTideCycle");
    private static readonly PropertyKey<int> LastTideDurationKey = new PropertyKey<int>("LastTideDuration");
    private static readonly PropertyKey<float> EmittedKey = new PropertyKey<float>("SludgeEmittedThisTide");

    // The Game scene's service, for the Harmony patches. Every
    // ILoadableSingleton is constructed before the first Load runs
    // (SingletonLifecycleService.LoadAll), so it is set before native
    // HazardousWeatherService.Load and cleared on scene unload.
    internal static RadioactiveTideService Current { get; private set; }

    private readonly ISingletonLoader _singletonLoader;
    private readonly EventBus _eventBus;
    private readonly HazardousWeatherService _hazardousWeatherService;
    private readonly WeatherService _weatherService;
    private readonly GameCycleService _gameCycleService;
    private readonly EntityComponentRegistry _registry;
    private readonly IRadiationService _radiation;
    private readonly IDayNightCycle _dayNightCycle;
    private readonly IRandomNumberGenerator _random;
    private readonly IRadioactiveTideSettings _settings;
    private readonly RadioactiveTideWeather _weather;

    private bool _loaded;
    private bool _currentCycleIsTide;
    private bool _forceNextCycle;

    public RadioactiveTideService(ISingletonLoader singletonLoader, EventBus eventBus, HazardousWeatherService hazardousWeatherService,
        WeatherService weatherService, GameCycleService gameCycleService, EntityComponentRegistry registry, IRadiationService radiation,
        IDayNightCycle dayNightCycle, IRandomNumberGenerator random, IRadioactiveTideSettings settings, RadioactiveTideWeather weather) {
      _singletonLoader = singletonLoader; _eventBus = eventBus; _hazardousWeatherService = hazardousWeatherService;
      _weatherService = weatherService; _gameCycleService = gameCycleService; _registry = registry; _radiation = radiation;
      _dayNightCycle = dayNightCycle; _random = random; _settings = settings; _weather = weather;
      if (Current != null) throw new InvalidOperationException("A radioactive tide service is already active; the previous Game scene was not unloaded");
      Current = this;
    }

    internal static RadioactiveTideService RequireCurrent() =>
      Current ?? throw new InvalidOperationException("Radioactive tide: the native weather was used outside a loaded Game scene");

    public RadioactiveTideWeather Weather => _weather;
    public bool IsTide(IHazardousWeather weather) => weather == _weather;
    // Native truth: the cycle's hazardous weather (forecast or in progress).
    public bool IsCurrentCycleTide => _hazardousWeatherService.CurrentCycleHazardousWeather == _weather;
    public bool IsEmitting => _weatherService.IsHazardousWeather && IsCurrentCycleTide;
    public int LastTideCycle { get; private set; }
    public int LastTideDuration { get; private set; }
    public float SludgeEmittedThisTide { get; private set; }
    public float RemainingDays => IsEmitting ? _weatherService.CycleLengthInDays + 1 - _gameCycleService.PartialCycleDay : 0f;
    public bool ForceNextCycle => _forceNextCycle;

    public float CurrentEmissionPerHour {
      get {
        if (!IsEmitting) return 0f;
        float total = 0f;
        foreach (var source in _registry.GetEnabled<WaterSource>())
          if (source.CurrentStrength > 0f) total += RadioactiveTideTuning.SourceRadioactiveShare * _radiation.WaterPerStrengthHour * source.CurrentStrength;
        return total;
      }
    }

    public void Load() {
      EnsureLoaded();
      _eventBus.Register(this);
    }

    public void PostLoad() {
      if (!_settings.IsLoaded) throw new InvalidOperationException("Radioactive tide settings did not load with the Game scene");
      if (_currentCycleIsTide) {
        if (!IsCurrentCycleTide)
          throw new InvalidOperationException("Saved radioactive tide was not restored into HazardousWeatherService");
        if (LastTideCycle != _gameCycleService.Cycle)
          throw new InvalidOperationException($"Saved radioactive tide belongs to cycle {LastTideCycle}, but the game is in cycle {_gameCycleService.Cycle}");
        if (LastTideDuration != _hazardousWeatherService.HazardousWeatherDuration)
          throw new InvalidOperationException($"Saved radioactive tide lasts {LastTideDuration} days, but the native hazardous weather lasts {_hazardousWeatherService.HazardousWeatherDuration}");
        RadioactiveTideSettingsCheck.Validate(_settings);
      } else {
        if (IsCurrentCycleTide) throw new InvalidOperationException("HazardousWeatherService holds a radioactive tide the save does not record");
        if (_settings.Enabled) RadioactiveTideSettingsCheck.Validate(_settings);
      }
    }

    public void Save(ISingletonSaver singletonSaver) {
      var data = singletonSaver.GetSingleton(Key);
      data.Set(CurrentCycleIsTideKey, _currentCycleIsTide);
      data.Set(LastTideCycleKey, LastTideCycle);
      data.Set(LastTideDurationKey, LastTideDuration);
      data.Set(EmittedKey, SludgeEmittedThisTide);
    }

    public void Unload() {
      if (Current == this) Current = null;
    }

    // Postfix of native HazardousWeatherService.Load (Game scene only).
    internal void RestoreAfterNativeLoad(HazardousWeatherService native) {
      if (native != _hazardousWeatherService) throw new InvalidOperationException("Radioactive tide: a foreign HazardousWeatherService was loaded");
      EnsureLoaded();
      if (_currentCycleIsTide) RadioactiveTideNative.SetCurrentWeather(native, _weather);
    }

    // Postfix of native HazardousWeatherRandomizer.GetRandomWeatherForCycle,
    // called once per cycle from HazardousWeatherService.SetForCycle.
    internal IHazardousWeather SelectForCycle(int cycle, IHazardousWeather native) {
      if (native == null) throw new InvalidOperationException($"Native weather randomizer chose no weather for cycle {cycle}");
      var selected = Choose(cycle, native);
      _currentCycleIsTide = selected == _weather;
      if (_currentCycleIsTide) {
        LastTideCycle = cycle;
        LastTideDuration = 0;   // set by OnHazardousWeatherSelected
        SludgeEmittedThisTide = 0f;
      }
      return selected;
    }

    private IHazardousWeather Choose(int cycle, IHazardousWeather native) {
      // Cycle 1 is chosen during GameCycleService.Load, possibly before the
      // settings load; the earliest-cycle setting cannot be below 2.
      if (cycle < RadioactiveTideTuning.EarliestCycle) return native;
      if (!_settings.IsLoaded) throw new InvalidOperationException("Radioactive tide settings are not loaded");
      if (!_settings.Enabled) return native;
      RadioactiveTideSettingsCheck.Validate(_settings);
      if (_forceNextCycle) { _forceNextCycle = false; return _weather; }
      if (cycle < _settings.MinCycle) return native;
      if (LastTideCycle > 0 && cycle - LastTideCycle <= RadioactiveTideTuning.CooldownCycles) return native;
      return _random.CheckProbability(_settings.ChancePercent / 100f) ? _weather : native;
    }

    [OnEvent]
    public void OnHazardousWeatherSelected(HazardousWeatherSelectedEvent selectedEvent) {
      bool tide = selectedEvent.SelectedWeather == _weather;
      if (tide != _currentCycleIsTide)
        throw new InvalidOperationException($"Radioactive tide: native selected {selectedEvent.SelectedWeather?.Id}, but the tide selection recorded {(_currentCycleIsTide ? "a tide" : "no tide")}");
      if (!tide) return;
      if (selectedEvent.Duration < RadioactiveTideTuning.DurationLowest)
        throw new InvalidOperationException($"Radioactive tide drew an invalid duration of {selectedEvent.Duration} days");
      LastTideDuration = selectedEvent.Duration;
    }

    public void Tick() {
      bool emitting = IsEmitting;
      _radiation.SetSourceRadioactiveShare(emitting ? RadioactiveTideTuning.SourceRadioactiveShare : 0f);
      if (emitting) SludgeEmittedThisTide += CurrentEmissionPerHour * _dayNightCycle.FixedDeltaTimeInHours;
    }

    // Dev mode: the next cycle's hazardous weather is a radioactive tide,
    // ignoring the earliest cycle, the chance and the cooldown. Not saved.
    public void ForceTideNextCycle() {
      if (!_settings.Enabled) throw new InvalidOperationException("Radioactive tides are disabled in the Deep Frontier mod settings");
      _forceNextCycle = true;
    }

    private void EnsureLoaded() {
      if (_loaded) return;
      _loaded = true;
      if (!_singletonLoader.TryGetSingleton(Key, out var data)) return;
      _currentCycleIsTide = data.Get(CurrentCycleIsTideKey);
      LastTideCycle = data.Get(LastTideCycleKey);
      LastTideDuration = data.Get(LastTideDurationKey);
      SludgeEmittedThisTide = data.Get(EmittedKey);
      if (LastTideCycle < 0 || LastTideDuration < 0 || !(SludgeEmittedThisTide >= 0f) || float.IsInfinity(SludgeEmittedThisTide))
        throw new InvalidOperationException($"Saved radioactive tide state is invalid (cycle {LastTideCycle}, duration {LastTideDuration}, emitted {SludgeEmittedThisTide})");
      if (LastTideCycle == 0 && (LastTideDuration != 0 || _currentCycleIsTide))
        throw new InvalidOperationException("Saved radioactive tide state has a tide without a cycle");
      if (LastTideCycle > 0 && (LastTideCycle < RadioactiveTideTuning.EarliestCycle || LastTideDuration < RadioactiveTideTuning.DurationLowest))
        throw new InvalidOperationException($"Saved radioactive tide in cycle {LastTideCycle} lasting {LastTideDuration} days is impossible");
    }
  }
}
