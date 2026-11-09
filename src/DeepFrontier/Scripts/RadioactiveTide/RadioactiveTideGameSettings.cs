using System;
using Timberborn.GameSceneLoading;
using Timberborn.Persistence;
using Timberborn.SceneLoading;
using Timberborn.SettingsSystem;
using Timberborn.SingletonSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.RadioactiveTide {
  // One game's radioactive tide settings, fixed values with where they came from.
  public sealed class RadioactiveTideValues : IRadioactiveTideSettings {
    public RadioactiveTideValues(bool enabled, int cyclesWithoutTide, int chancePercent, int minDurationDays, int maxDurationDays, string source) {
      Enabled = enabled; CyclesWithoutTide = cyclesWithoutTide; ChancePercent = chancePercent;
      MinDurationDays = minDurationDays; MaxDurationDays = maxDurationDays;
      Source = source ?? throw new ArgumentNullException(nameof(source));
    }

    public bool Enabled { get; }
    public int CyclesWithoutTide { get; }
    public int ChancePercent { get; }
    public int MinDurationDays { get; }
    public int MaxDurationDays { get; }
    // Where the values come from, for messages and the load log.
    public string Source { get; }

    public static RadioactiveTideValues FromSpec(RadioactiveTideGameModeSpec spec, string source) {
      if (spec == null) throw new ArgumentNullException(nameof(spec));
      if (spec.Duration == null) throw new InvalidOperationException($"Radioactive tide settings of {source} have no Duration");
      return new RadioactiveTideValues(spec.Enabled, spec.CyclesWithoutTide, spec.ChancePercent, spec.Duration.Min, spec.Duration.Max, source);
    }

    public override string ToString() => Enabled
      ? $"on, from cycle {CyclesWithoutTide + 1}, {ChancePercent}% per cycle, {MinDurationDays}-{MaxDurationDays} days ({Source})"
      : $"off ({Source})";
  }

  public static class RadioactiveTideSettingsCheck {
    // Settings of a game. Only enabled settings are used, so only they must
    // be in range (the native custom mode does not check a switched-off
    // badtide either).
    public static void Validate(IRadioactiveTideSettings settings, string source) {
      if (settings == null) throw new InvalidOperationException("Radioactive tide settings are not bound");
      if (!settings.Enabled) return;
      ValidateValues(settings.CyclesWithoutTide, settings.ChancePercent, settings.MinDurationDays, settings.MaxDurationDays, source);
    }

    public static void ValidateValues(int cyclesWithoutTide, int chancePercent, int minDurationDays, int maxDurationDays, string source) {
      Require(cyclesWithoutTide, RadioactiveTideTuning.CyclesWithoutTideLowest, RadioactiveTideTuning.CyclesWithoutTideHighest, "cycles without radioactive tide", source);
      ValidateChanceAndDuration(chancePercent, minDurationDays, maxDurationDays, source);
    }

    // Shared with Moddable Weathers' per-save settings, which keep the
    // earliest cycle instead of the cycles without a tide.
    public static void ValidateChanceAndDuration(int chancePercent, int minDurationDays, int maxDurationDays, string source) {
      Require(chancePercent, RadioactiveTideTuning.ChancePercentLowest, RadioactiveTideTuning.ChancePercentHighest, "radioactive tide chance (%)", source);
      Require(minDurationDays, RadioactiveTideTuning.DurationLowest, RadioactiveTideTuning.DurationHighest, "shortest radioactive tide (days)", source);
      Require(maxDurationDays, RadioactiveTideTuning.DurationLowest, RadioactiveTideTuning.DurationHighest, "longest radioactive tide (days)", source);
      if (minDurationDays > maxDurationDays)
        throw new InvalidOperationException($"Radioactive tide settings of {source}: the shortest tide ({minDurationDays} days) is longer than the longest tide ({maxDurationDays} days).");
    }

    public static void Require(int value, int lowest, int highest, string name, string source) {
      if (value < lowest || value > highest)
        throw new InvalidOperationException($"Radioactive tide setting '{name}' of {source} is {value}; allowed {lowest}..{highest}.");
    }
  }

  // Where a game's radioactive tide settings come from, in this order:
  // 1. the game's own saved copy (singleton DeepFrontier.RadioactiveTideSettings,
  //    written by RadioactiveTideGameSettings when the game runs without
  //    Moddable Weathers);
  // 2. a new game: the settings of the new game's mode
  //    (GameSceneParameters.NewGameConfiguration.GameMode), as native
  //    BadtideWeather.Load reads its values from that GameModeSpec: its own
  //    RadioactiveTideGameModeSpec (the custom mode), else the settings its
  //    weather gives (RadioactiveTideGameModes.Derive; Easy, Normal, Hard and
  //    any mode a mod adds), named in the source with how they were derived;
  // 3. a save from before per-game settings: the values the player had in the
  //    former Deep Frontier mod settings, so such a save keeps the tides it had
  //    (keys the player never changed read as the old defaults, the Normal
  //    mode's values).
  // Moddable Weathers seeds its per-save tide settings from the same order
  // (RadioactiveTideModdableWeatherSettings.InitializeNewValuesTo).
  public static class RadioactiveTideStartingValues {
    public static readonly SingletonKey SavedKey = new SingletonKey("DeepFrontier.RadioactiveTideSettings");
    private static readonly PropertyKey<bool> EnabledKey = new PropertyKey<bool>("Enabled");
    private static readonly PropertyKey<int> CyclesWithoutTideKey = new PropertyKey<int>("CyclesWithoutTide");
    private static readonly PropertyKey<int> ChancePercentKey = new PropertyKey<int>("ChancePercent");
    private static readonly PropertyKey<int> MinDurationKey = new PropertyKey<int>("MinDurationDays");
    private static readonly PropertyKey<int> MaxDurationKey = new PropertyKey<int>("MaxDurationDays");

    public const string SavedSource = "this save";
    public const string NewGameSource = "the new game's mode";
    public const string LegacySource = "the former Deep Frontier mod settings (a save from before per-game radioactive tide settings)";

    public static RadioactiveTideValues Resolve(ISingletonLoader singletonLoader, ISceneLoader sceneLoader, ISettings settings) {
      if (singletonLoader == null) throw new ArgumentNullException(nameof(singletonLoader));
      return TryReadSaved(singletonLoader, out var values) ? values : ForUnsavedGame(sceneLoader, settings);
    }

    // A loaded save, never a new game (steps 1 and 3): the Moddable Fluids build's tide importer reads it.
    public static RadioactiveTideValues ForLoadedSave(ISingletonLoader singletonLoader, ISettings settings) {
      if (singletonLoader == null) throw new ArgumentNullException(nameof(singletonLoader));
      if (settings == null) throw new ArgumentNullException(nameof(settings));
      if (TryReadSaved(singletonLoader, out var values)) return values;
      values = Legacy(settings);
      RadioactiveTideSettingsCheck.Validate(values, values.Source);
      return values;
    }

    private static bool TryReadSaved(ISingletonLoader singletonLoader, out RadioactiveTideValues values) {
      values = null;
      if (!singletonLoader.TryGetSingleton(SavedKey, out var saved)) return false;
      if (!saved.Has(EnabledKey) || !saved.Has(CyclesWithoutTideKey) || !saved.Has(ChancePercentKey) || !saved.Has(MinDurationKey) || !saved.Has(MaxDurationKey))
        throw new InvalidOperationException($"Saved radioactive tide settings ({SavedKey.Name}) are incomplete");
      values = new RadioactiveTideValues(saved.Get(EnabledKey), saved.Get(CyclesWithoutTideKey), saved.Get(ChancePercentKey),
        saved.Get(MinDurationKey), saved.Get(MaxDurationKey), SavedSource);
      RadioactiveTideSettingsCheck.Validate(values, values.Source);
      return true;
    }

    public static RadioactiveTideValues ForUnsavedGame(ISceneLoader sceneLoader, ISettings settings) {
      if (sceneLoader == null) throw new ArgumentNullException(nameof(sceneLoader));
      if (settings == null) throw new ArgumentNullException(nameof(settings));
      RadioactiveTideValues values;
      if (sceneLoader.TryGetSceneParameters<GameSceneParameters>(out var parameters) && parameters.NewGame) {
        var gameMode = parameters.NewGameConfiguration.GameMode;
        var spec = RadioactiveTideGameModes.For(gameMode, NewGameSource, out var derivation);
        values = RadioactiveTideValues.FromSpec(spec, derivation == null ? NewGameSource
          : $"{NewGameSource} {RadioactiveTideGameModes.Name(gameMode)}, derived from its weather: {derivation}");
      } else {
        values = Legacy(settings);
      }
      RadioactiveTideSettingsCheck.Validate(values, values.Source);
      return values;
    }

    private static RadioactiveTideValues Legacy(ISettings settings) => new RadioactiveTideValues(
      settings.Has(RadioactiveTideTuning.LegacyEnabledKey) ? settings.GetBool(RadioactiveTideTuning.LegacyEnabledKey) : RadioactiveTideTuning.LegacyEnabled,
      LegacyInt(settings, RadioactiveTideTuning.LegacyMinCycleKey, RadioactiveTideTuning.LegacyMinCycle) - 1,
      LegacyInt(settings, RadioactiveTideTuning.LegacyChancePercentKey, RadioactiveTideTuning.LegacyChancePercent),
      LegacyInt(settings, RadioactiveTideTuning.LegacyMinDurationKey, RadioactiveTideTuning.LegacyMinDurationDays),
      LegacyInt(settings, RadioactiveTideTuning.LegacyMaxDurationKey, RadioactiveTideTuning.LegacyMaxDurationDays),
      LegacySource);

    public static void Write(ISingletonSaver singletonSaver, IRadioactiveTideSettings values) {
      var data = singletonSaver.GetSingleton(SavedKey);
      data.Set(EnabledKey, values.Enabled);
      data.Set(CyclesWithoutTideKey, values.CyclesWithoutTide);
      data.Set(ChancePercentKey, values.ChancePercent);
      data.Set(MinDurationKey, values.MinDurationDays);
      data.Set(MaxDurationKey, values.MaxDurationDays);
    }

    private static int LegacyInt(ISettings settings, string key, int oldDefault) =>
      settings.Has(key) ? settings.GetInt(key, oldDefault) : oldDefault;
  }

  // The radioactive tide settings of the running game without Moddable
  // Weathers, saved with the game like native BadtideWeather's values. They
  // cannot change during a game (the native weather settings cannot either).
  // Read lazily: the native weather may ask during the Game scene's Load.
  public sealed class RadioactiveTideGameSettings : IRadioactiveTideSettings, ILoadableSingleton, ISaveableSingleton {
    private readonly ISingletonLoader _singletonLoader;
    private readonly ISceneLoader _sceneLoader;
    private readonly ISettings _settings;
    private RadioactiveTideValues _values;

    public RadioactiveTideGameSettings(ISingletonLoader singletonLoader, ISceneLoader sceneLoader, ISettings settings) {
      _singletonLoader = singletonLoader; _sceneLoader = sceneLoader; _settings = settings;
    }

    private RadioactiveTideValues Values => _values ??= Logged(RadioactiveTideStartingValues.Resolve(_singletonLoader, _sceneLoader, _settings));

    public bool Enabled => Values.Enabled;
    public int CyclesWithoutTide => Values.CyclesWithoutTide;
    public int ChancePercent => Values.ChancePercent;
    public int MinDurationDays => Values.MinDurationDays;
    public int MaxDurationDays => Values.MaxDurationDays;
    public string Source => Values.Source;

    public void Load() => _ = Values;

    public void Save(ISingletonSaver singletonSaver) => RadioactiveTideStartingValues.Write(singletonSaver, Values);

    private static RadioactiveTideValues Logged(RadioactiveTideValues values) {
      Debug.Log($"[DeepFrontier] Radioactive tide settings: {values}.");
      return values;
    }
  }
}
