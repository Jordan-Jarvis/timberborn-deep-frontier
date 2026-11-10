using System;
using System.Collections.Frozen;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.ComponentModel;
using System.Linq;
using System.Reflection;
using DeepFrontier.ModdableFluidsMigration;
using ModdableWeathers.Common.Settings;
using ModdableWeathers.Cycles;
using ModdableWeathers.Historical;
using ModdableWeathers.WeatherModifiers;
using ModdableWeathers.Weathers;
using ModdableWeathers.Weathers.GameBuiltIns;
using ModdableWeathers.Weathers.Settings;
using Timberborn.Common;
using Timberborn.GameCycleSystem;
using Timberborn.HazardousWeatherSystem;
using Timberborn.NewGameConfigurationSystem;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.WorldPersistence;

namespace ModdableFluids.Tides.ModdableWeathersAdapter.Acceptance {
  /// <summary>
  /// Deep Frontier's import of a save played under its shipped build with Moddable Weathers, where its optional bridge
  /// registered the radioactive tide as the Moddable Weathers weather RadioactiveTideWeather (RadioactiveTideModdableWeathersSave,
  /// from the Deep Frontier groundwork). The save is written by the real Moddable Weathers 11.0.0 WeatherHistoryRegistry and
  /// ModdableWeatherSettingsService and the native GameCycleService, through the game's JSON writer and reader. Deep
  /// Frontier must read the history as Moddable Weathers reads it back, take the cycle's tide from the stage the real
  /// WeatherCycleService finds (its current or next hazardous stage), and the adapter's load check must accept the import.
  /// </summary>
  public static partial class ModdableWeathersMonoProbe {
    /// <summary>What the Deep Frontier stand-in's IFluidTideImporter answers; null answers nothing (the other sections).</summary>
    private static Func<FluidTideImportContext, FluidTideImport> DeepFrontierImport;

    /// <summary>The Deep Frontier stand-in: its tide registration, and Deep Frontier's tide importer while a section sets one.</summary>
    private sealed class DeepFrontierProvider : IFluidProvider, IFluidTideImporter {
      private readonly Provider _tides;
      public DeepFrontierProvider(Provider tides) { _tides = tides; }
      public string ProviderId => _tides.ProviderId;
      public string OwnerModId => _tides.OwnerModId;
      public string MinimumApiVersion => _tides.MinimumApiVersion;
      public IReadOnlyCollection<string> RequiredCapabilities => _tides.RequiredCapabilities.Append(FluidTideRules.ImportCapability).ToArray();
      public void Register(FluidRegistration registration) => _tides.Register(registration);
      public FluidTideImport ImportTides(FluidTideImportContext context) => DeepFrontierImport?.Invoke(context);
    }

    // As the flagged mod starter reads the save (ModdableFluidsRadiationGame.cs, DeepFrontierFluidsModStarter.ImportTide).
    private static FluidTideImport ImportBridgeSave(FluidTideImportContext context, string weather) {
      var loader = (ISingletonLoader)context.NativeSingletonLoader;
      var bridge = RadioactiveTideModdableWeathersSave.Read(weather, loader.TryGetSingleton(new SingletonKey("DeepFrontier.RadioactiveTide"), out _)
          || loader.TryGetSingleton(new SingletonKey("DeepFrontier.RadioactiveTideSettings"), out _),
        loader.TryGetSingleton(new SingletonKey(RadioactiveTideModdableWeathersSave.SettingsSingleton), out var settings)
          ? settings.Get(new PropertyKey<string>(RadioactiveTideModdableWeathersSave.SettingsProperty)) : null,
        loader.TryGetSingleton(new SingletonKey(RadioactiveTideModdableWeathersSave.HistorySingleton), out var history)
          ? history.Get(new ListKey<string>(RadioactiveTideModdableWeathersSave.HistoryList)) : null,
        loader.TryGetSingleton(new SingletonKey("GameCycleService"), out var cycle)
          ? (cycle.Get(new PropertyKey<int>("Cycle")), cycle.Get(new PropertyKey<int>("CycleDay"))) : ((int, int)?)null)
        ?? throw new InvalidOperationException("Deep Frontier read no bridge save");
      return RadioactiveTideImport.Map(bridge.State, bridge.Enabled, bridge.CyclesWithoutTide, bridge.ChancePercent, bridge.MinDurationDays, bridge.MaxDurationDays);
    }

    private static void DeepFrontierBridgeSaves(Action<bool, string> check, Action<Action, string, string> throws, ModdableWeatherSpecService specs, IRandomNumberGenerator random,
        Container container, GameCycleService cycles, Action<IHazardousWeather> setCurrent) {
      void SetDay(int cycle, int day) {
        typeof(GameCycleService).GetProperty("Cycle").GetSetMethod(true).Invoke(cycles, new object[] { cycle });
        typeof(GameCycleService).GetProperty("CycleDay").GetSetMethod(true).Invoke(cycles, new object[] { day });
      }
      // The history the bridge leaves (the harness uses the same layout): tides in cycle 7 (stage 1), 13 (between benign
      // stages), 15 (after a drought stage) and 18 (after a skipped stage: indices 0, 2, 3); generated up to cycle 19.
      WeatherCycleStage Benign(int index, int days) => new WeatherCycleStage(index, true, "TemperateWeather", ImmutableArray<string>.Empty, days);
      WeatherCycleStage Hazard(int index, string weather, int days) =>
        new WeatherCycleStage(index, false, weather, weather == RadioactiveWeather ? ImmutableArray<string>.Empty : ImmutableArray.Create(weather == "DroughtWeather" ? "Drought" : "Badtide"), days);
      var written = new WeatherHistoryRegistry(new EmptyLoader(), null, null);
      written.WeatherCycleAdded += (cycle, current) => { };
      for (int c = 1; c <= 19; c++) written.AddWeatherCycles(new WeatherCycle(c, c switch {
        7 => ImmutableArray.Create(Benign(0, 12), Hazard(1, RadioactiveWeather, 5)),
        13 => ImmutableArray.Create(Benign(0, 10), Hazard(1, RadioactiveWeather, 6), Benign(2, 3)),
        15 => ImmutableArray.Create(Benign(0, 9), Hazard(1, "DroughtWeather", 3), Benign(2, 2), Hazard(3, RadioactiveWeather, 4)),
        18 => ImmutableArray.Create(Benign(0, 5), Benign(2, 4), Hazard(3, RadioactiveWeather, 3)),
        _ => ImmutableArray.Create(Benign(0, 12), Hazard(1, c % 3 == 0 ? "BadtideWeather" : "DroughtWeather", 4)),
      }), c);
      // The bridge's settings (Normal: from cycle 15, 25%, 3-6 days) beside Moddable Weathers' drought settings.
      var settingsService = new ModdableWeatherSettingsService(null, new EmptyLoader(), null);
      var bridgeSettings = new DeepFrontier.RadioactiveTideModdableWeathers.RadioactiveTideModdableWeatherSettings { Enabled = true, StartCycle = 15, ChancePercent = 25, MinDurationDays = 3, MaxDurationDays = 6 };
      typeof(BaseWeatherSettingsService<IModdableWeatherSettings>).GetField("settingsByType", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(settingsService,
        new Dictionary<Type, IModdableWeatherSettings> { [bridgeSettings.GetType()] = bridgeSettings,
          [typeof(GameDroughtWeatherSettings)] = new GameDroughtWeatherSettings { Enabled = true, StartCycle = 0, Chance = 60 } }.ToFrozenDictionary());

      MemorySave Saved(int cycle, int day) {
        var save = new MemorySave();
        written.Save(save);
        settingsService.Save(save);
        SetDay(cycle, day);
        cycles.Save(save);
        return save.RoundTrip();
      }
      var first = Saved(9, 14);
      check(first.Objects.ContainsKey(RadioactiveTideModdableWeathersSave.HistorySingleton) && first.Objects.ContainsKey(RadioactiveTideModdableWeathersSave.SettingsSingleton),
        "Deep Frontier reads the singletons Moddable Weathers writes: " + string.Join(", ", first.Objects.Keys));
      // Deep Frontier parses the history as Moddable Weathers itself reads it back from the save.
      first.TryGetSingleton(new SingletonKey(RadioactiveTideModdableWeathersSave.HistorySingleton), out var historyData);
      var parsed = RadioactiveTideModdableWeathersSave.ReadHistory(historyData.Get(new ListKey<string>(RadioactiveTideModdableWeathersSave.HistoryList)), RadioactiveWeather);
      var reread = new WeatherHistoryRegistry(first, null, null);
      reread.Load();
      check(reread.CycleCount == 19 && parsed.Count == 20 && Enumerable.Range(0, 20).All(c => reread[c].Cycle == c && reread[c].Stages.Length == parsed[c].Count
          && reread[c].Stages.Select((s, k) => s.Index == parsed[c][k].Index && s.IsBenign == parsed[c][k].IsBenign && s.WeatherId == parsed[c][k].WeatherId && s.Days == parsed[c][k].Days).All(same => same)),
        "Deep Frontier's parse of every cycle and stage is Moddable Weathers' own reading of the save");

      var modifiers = new ModdableWeatherModifierRegistry(new IModdableWeatherModifier[0]);
      modifiers.Load();
      DeepFrontierImport = context => ImportBridgeSave(context, RadioactiveWeather);
      try {
        var cases = new (int Cycle, int Day, bool Current, int Last, int Days)[] {
          (6, 5, false, 0, 0), (7, 3, true, 7, 5), (7, 13, true, 7, 5), (7, 40, true, 7, 5), (9, 14, false, 7, 5), (13, 11, true, 13, 6), (13, 18, false, 13, 6),
          (15, 5, false, 15, 4), (15, 11, false, 15, 4), (15, 13, true, 15, 4), (15, 16, true, 15, 4), (17, 2, false, 15, 4), (18, 3, true, 18, 3), (18, 7, false, 18, 3) };
        foreach (var (cycle, day, current, last, days) in cases) {
          string at = "cycle " + cycle + " day " + day;
          var save = Saved(cycle, day);
          var history = new WeatherHistoryRegistry(save, null, null);
          history.Load();
          container.Add(history);
          var scene = Scene(save, new SceneLoader(null), random, container, specs);
          try {
            // The real WeatherCycleService on this save: the stage it finds is what Moddable Weathers' hazardous weather
            // service reports (its replacing CurrentCycleHazardousWeather), which the probe's native service stands in for.
            var registry = container.Get<ModdableWeatherRegistry>();
            var historyService = new WeatherHistoryService(history, registry, modifiers);
            var generator = new WeatherGenerator(history, historyService, registry, null, null);
            var cycleService = new WeatherCycleService(new EventBus(), historyService, cycles, generator, null, new CycleDurationService(history, generator));
            cycleService.Load();
            var truth = cycleService.GetCurrentOrNextHazardousWeatherInThisCycle()?.Weather;
            cycleService.CurrentWeather.End();
            setCurrent(truth as IHazardousWeather);
            check((truth?.Id == RadioactiveWeather) == current, at + ": Moddable Weathers' current or next hazardous stage is " + (truth?.Id ?? "none"));
            scene.PostLoad();
            check(scene.Data.ImportedBy == "DeepFrontier.Radiation" && scene.Data.CurrentCycleTide == (current ? Radioactive : null) && scene.Data.LastTideCycle == last
              && scene.Data.LastTideId == (last == 0 ? null : Radioactive) && scene.Data.LastTideDuration == days && scene.Settings.Get(Radioactive).Weight == 25
              && scene.Settings.Get(Radioactive).CyclesWithoutTide == 14 && !scene.Settings.Get(Coffee).Enabled,
              at + ": Deep Frontier's import (" + scene.Data.DescribeState() + "; " + scene.Settings + ") is accepted by the adapter's history check");
          } finally { scene.Unload(); }
        }
        // A save holding Deep Frontier's own tide keys beside the bridge's settings is refused, naming Deep Frontier.
        var both = Saved(9, 14);
        both.Objects["DeepFrontier.RadioactiveTideSettings"] = new Timberborn.SerializationSystem.SerializedObject();
        var refused = Scene(both, new SceneLoader(null), random, container, specs);
        try { throws(() => _ = refused.Data.HadState, "holds both", "a save with both tide systems' keys is refused"); }
        finally { refused.Unload(); }
      } finally { DeepFrontierImport = null; }
    }
  }
}

namespace DeepFrontier.RadioactiveTideModdableWeathers {
  /// <summary>
  /// The bridge's settings type as Moddable Weathers serializes it: the same full name and [Description] properties (the
  /// fluid harness checks both against src/DeepFrontier/Scripts/RadioactiveTide/ModdableWeathers). The bridge assembly
  /// itself needs the shipped Deep Frontier assembly, which this probe does not load.
  /// </summary>
  public sealed class RadioactiveTideModdableWeatherSettings : IModdableWeatherSettings {
    [Description("DeepFrontier.RadioactiveTide.Settings.Enabled")]
    public bool Enabled { get; set; }

    [Description("DeepFrontier.RadioactiveTide.Settings.MinCycle")]
    public int StartCycle { get; set; }

    [Description("DeepFrontier.RadioactiveTide.Settings.Chance")]
    public int ChancePercent { get; set; }

    [Description("DeepFrontier.RadioactiveTide.Settings.MinDuration")]
    public int MinDurationDays { get; set; }

    [Description("DeepFrontier.RadioactiveTide.Settings.MaxDuration")]
    public int MaxDurationDays { get; set; }

    public bool FirstLoad { get; set; }

    public bool CanSupport(GameModeSpec gameMode) => true;

    public void InitializeNewValuesTo(GameModeSpec gameMode) => throw new NotSupportedException("The probe's bridge settings are set directly");
  }
}
