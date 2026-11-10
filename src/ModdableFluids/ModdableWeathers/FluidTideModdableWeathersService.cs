using System;
using System.Collections.Immutable;
using System.Linq;
using Bindito.Core;
using ModdableFluids;
using ModdableFluids.Runtime.Prototype;
using ModdableFluids.Tides.Prototype;
using ModdableWeathers.Cycles;
using ModdableWeathers.Historical;
using ModdableWeathers.Weathers;
using Timberborn.Common;
using Timberborn.GameCycleSystem;
using Timberborn.HazardousWeatherSystem;
using Timberborn.SceneLoading;
using Timberborn.SettingsSystem;
using Timberborn.SingletonSystem;
using Timberborn.TickSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace ModdableFluids.Tides.ModdableWeathersAdapter {
  /// <summary>
  /// The Game scene's tide owner under Moddable Weathers (the second binding of <see cref="IFluidTideScene"/>; the native
  /// one is FluidTideService). No native weather method is patched: Moddable Weathers draws, saves, shows and starts the
  /// weathers, and this service supplies the tides' side of it.
  /// <list type="bullet">
  /// <item><b>Selection.</b> Once per hazardous stage, the first tide weather asked weighs every tide: it sums the other
  /// enabled hazardous weathers' GetChance for the stage (O), finds the last tide in Moddable Weathers' history, and
  /// applies FluidTideSelection.StageWeights (C′ as integer weights; at most one tide per cycle; the one-cycle global
  /// cooldown).</item>
  /// <item><b>Source effect.</b> While a tide weather is Active (Moddable Weathers starts and ends it with its stage, and
  /// starts it again when a save loads inside it), this service owns the world's source composition and the strength
  /// modifier applies the tide's multiplier.</item>
  /// <item><b>Weather Station.</b> Moddable Weathers' HazardousWeatherService returns the cycle's current or next hazardous
  /// stage's weather; the station samples it by weather ID. The station patches are installed per scene
  /// (FluidTideStationPatches) and removed on unload.</item>
  /// <item><b>Saving.</b> The settings and state singletons of the native binding (FluidTideSaveData). Moddable Weathers'
  /// history is the state of record; each save writes the native binding's state derived from it, so the save loads
  /// without Moddable Weathers too, and a loaded state must agree with the history.</item>
  /// </list>
  /// </summary>
  public sealed class FluidTideModdableWeathersService : IFluidTideScene, ILoadableSingleton, IPostLoadableSingleton, ISaveableSingleton, ITickableSingleton, IUnloadableSingleton {
    private readonly IRandomNumberGenerator _random;
    private readonly ModdableFluidsSceneOwner _sceneOwner;
    private readonly IContainer _container;
    private readonly FluidTideSaveData _data;
    private readonly FluidTideStationPatches _station = new FluidTideStationPatches();
    private readonly FluidTideModdableWeather[] _weathers;
    // Resolved on first use, never constructor arguments: under Moddable Weathers each of these is constructed from the
    // registry (HazardousWeatherService -> WeatherCycleService -> WeatherHistoryService -> ModdableWeatherRegistry;
    // GameCycleService -> its ICycleDuration CycleDurationService -> WeatherGenerator -> ModdableWeatherRegistry), the
    // registry from every IModdableWeather, and the tide weathers from this service: a dependency cycle.
    private ModdableWeatherRegistry _registry;
    private WeatherHistoryRegistry _history;
    private HazardousWeatherService _hazardousWeatherService;
    private GameCycleService _gameCycleService;
    // One stage's weights, computed when its first tide weather is asked.
    private WeatherCycleStageDecision _stage;
    private int[] _weights;
    private bool _weighing;
    private IModdableWeather _asking;
    private string _forcedTide;
    private int _forcedCycle;
    private FluidTideDefinition _composing;

    public FluidTideRegistry Tides { get; }

    public FluidTideModdableWeathersService(ISingletonLoader singletons, ISceneLoader sceneLoader, ISettings nativeSettings, IRandomNumberGenerator random,
        ModdableFluidsSceneOwner sceneOwner, IContainer container) {
      _random = random; _sceneOwner = sceneOwner; _container = container;
      var host = ModdableFluidsEntry.Host;
      host.Freeze();
      Tides = host.Tides;
      if (Tides.Count == 0) throw new InvalidOperationException("Moddable Fluids tides: the Moddable Weathers adapter was bound without registered tides");
      _weathers = new FluidTideModdableWeather[Tides.Count];
      _data = new FluidTideSaveData(Tides, singletons, sceneLoader, nativeSettings);
      FluidTideScenes.Attach(this);
      try { _station.Install(); }
      catch { FluidTideScenes.Detach(this); throw; }
    }

    public FluidTideSaveSettings Settings => _data.Settings;
    public FluidTideSaveData Data => _data;
    public bool StationPatchesInstalled => _station.Installed;
    public FluidTideModdableWeather WeatherOf(string tideId) => _weathers.FirstOrDefault(w => w?.Tide.Id == tideId) ?? throw new ArgumentException("Tide " + tideId + " has no Moddable Weathers weather");

    /// <summary>The cycle's tide: Moddable Weathers' current or next hazardous stage in this cycle, recognised by its weather ID.</summary>
    public FluidTideDefinition CurrentCycleTide {
      get {
        var weather = HazardousWeather().CurrentCycleHazardousWeather;
        return weather != null && Tides.TryGetByWeather(weather.Id, out var tide) ? tide : null;
      }
    }

    /// <summary>The tide whose weather is Active (its stage is in progress), or null. Read by every water source every tick.</summary>
    public FluidTideDefinition EmittingTide {
      get {
        FluidTideDefinition active = null;
        for (int i = 0; i < _weathers.Length; i++) {
          if (!_weathers[i].Active) continue;
          if (active != null) throw new InvalidOperationException("Moddable Fluids tides: Moddable Weathers has two tides active at once (" + active.Id + ", " + _weathers[i].Tide.Id + ")");
          active = _weathers[i].Tide;
        }
        return active;
      }
    }

    // Each tide weather attaches itself while the container constructs it (class i takes the i-th tide).
    internal FluidTideDefinition Attach(FluidTideModdableWeather weather) {
      if (weather.Index < 0 || weather.Index >= Tides.Count)
        throw new InvalidOperationException("Moddable Fluids tides: tide weather class " + weather.GetType().Name + " was bound for " + Tides.Count + " registered tides");
      if (_weathers[weather.Index] != null) throw new InvalidOperationException("Moddable Fluids tides: tide weather " + weather.Index + " was constructed twice");
      _weathers[weather.Index] = weather;
      return Tides.Tides[weather.Index];
    }

    public void Load() {
      RequireWeathers();
      Debug.Log(_data.LoadMessage + "\n  [ModdableFluids] Tides run as Moddable Weathers weathers: " + string.Join(", ", _weathers.Select(w => w.Tide.Id + " = " + w.Id)));
    }

    /// <summary>Every registered tide has its weather (the configurator bound one class per tide).</summary>
    internal void RequireWeathers() {
      var missing = Enumerable.Range(0, Tides.Count).Where(i => _weathers[i] == null).Select(i => Tides.Tides[i].Id).ToArray();
      if (missing.Length > 0) throw new InvalidOperationException("Moddable Fluids tides: no Moddable Weathers weather was bound for " + string.Join(", ", missing));
    }

    public void PostLoad() {
      Registry();
      foreach (var weather in _weathers)
        if (!_registry.WeathersById.TryGetValue(weather.Id, out var registered) || !ReferenceEquals(registered, weather))
          throw new InvalidOperationException("Moddable Fluids tides: Moddable Weathers' registry does not list tide weather " + weather.Id + " as the adapter's weather");
      int cycle = Cycles().Cycle;
      var derived = Derive(cycle);
      if (_data.HadState) {
        // A state saved by either binding (or imported) is the history Moddable Weathers holds (its own, or the one it
        // converted from the native history of a save played without it); a disagreement is another tide system's work.
        if (derived.Current != _data.CurrentCycleTide || derived.LastCycle != _data.LastTideCycle || derived.LastId != _data.LastTideId || derived.LastDuration != _data.LastTideDuration)
          throw new InvalidOperationException("Moddable Fluids tides: this save's " + (_data.ImportedBy != null ? "imported (" + _data.ImportedBy + ")" : "saved") + " tide state (" + _data.DescribeState()
            + ") disagrees with Moddable Weathers' weather history (" + Describe(derived) + ")");
      } else if (!_data.NewGame && derived.LastId != null) {
        // As the native binding: a loaded save without tide state whose history already holds a registered tide was
        // played under another tide system.
        throw new InvalidOperationException("Moddable Fluids tides: Moddable Weathers' weather history of this save holds " + derived.LastId + " (cycle " + derived.LastCycle
          + "), but the save has no Moddable Fluids tide state and no installed tide importer (IFluidTideImporter) read it: it was played with another tide system.");
      }
      DryRun(cycle + 1);
    }

    public void Save(ISingletonSaver singletonSaver) {
      var derived = Derive(Cycles().Cycle);
      _data.SetState(derived.Current, derived.LastCycle, derived.LastId, derived.LastDuration, "Moddable Weathers history's");
      _data.Save(singletonSaver);
    }

    public void Tick() {
      var tide = EmittingTide;
      if (tide == _composing) return;
      var world = _sceneOwner.World ?? throw new InvalidOperationException("Moddable Fluids tides: the scene has no world service to apply the tide's source emission");
      world.SetSourceComposition(FluidTideService.OwnerId, tide?.SourceEmission);
      _composing = tide;
    }

    public void Unload() {
      try { _station.Uninstall(); }
      finally { FluidTideScenes.Detach(this); }
    }

    /// <summary>
    /// A tide weather's integer weight for one hazardous stage. The first tide asked for a stage weighs them all; the
    /// others read the result. A weather that asks for a tide's weight while the tides weigh it would recurse forever and
    /// is refused, naming it.
    /// </summary>
    internal int WeightOf(FluidTideModdableWeather weather, WeatherCycleStageDecision stage, WeatherCycleDecision cycle) {
      if (stage == null || cycle == null) throw new ArgumentNullException(stage == null ? nameof(stage) : nameof(cycle));
      if (_weighing)
        throw new InvalidOperationException("Moddable Fluids tides cannot run beside Moddable Weathers' hazardous weather " + _asking?.Id + ": asked for its weight, it asks for the tides' "
          + "weights in turn (it weighs itself against the other hazardous weathers, as the tides do), so neither can be weighed. A tide of its own must register through Moddable Fluids instead.");
      if (stage.IsBenign) throw new InvalidOperationException("Moddable Fluids tides: Moddable Weathers asked a tide for a benign stage (cycle " + cycle.Cycle + ", stage " + stage.StageIndex + ")");
      if (!ReferenceEquals(stage, _stage)) {
        _weights = Weigh(stage, cycle);
        _stage = stage;
      }
      return _weights[IndexInSettings(weather.Tide.Id)];
    }

    internal int DrawDuration(FluidTideDefinition tide) {
      var settings = Settings.Get(tide.Id);
      if (!settings.Enabled) throw new InvalidOperationException("Moddable Fluids tides: a duration was drawn for " + tide.Id + ", which is off in this game");
      return _random.Range(settings.MinDurationDays, settings.MaxDurationDays + 1);
    }

    /// <summary>
    /// Development: regenerates the next cycle with the tide in its first hazardous stage, as Moddable Weathers regenerates
    /// future cycles after its Weather Settings dialog (clear the future entries, generate, refresh the references).
    /// </summary>
    public void ForceNextCycle(string tideId) {
      if (!Settings.Get(tideId).Enabled) throw new InvalidOperationException("Tide " + tideId + " is off in this game's settings (chosen when the game was started)");
      int cycle = Cycles().Cycle;
      var generator = _container.GetInstance<WeatherGenerator>();
      var historyService = _container.GetInstance<WeatherHistoryService>();
      _forcedTide = tideId; _forcedCycle = cycle + 1;
      try {
        History().ClearFutureEntries(cycle);
        generator.EnsureWeatherGenerated(cycle);
      } finally { _forcedTide = null; _forcedCycle = 0; }
      historyService.UpdateReferences(cycle, true);
      var weather = WeatherOf(tideId);
      if (!historyService.GetWeatherCycle(cycle + 1).Stages.Any(s => ReferenceEquals(s.Weather, weather)))
        throw new InvalidOperationException("Moddable Fluids tides: cycle " + (cycle + 1) + " was regenerated without a hazardous stage for " + tideId + " (Moddable Weathers' cycle stages have none)");
    }

    private int[] Weigh(WeatherCycleStageDecision stage, WeatherCycleDecision cycle) {
      bool earlier = false;
      foreach (var other in cycle.Stages)
        if (other.StageIndex < stage.StageIndex && other.Weather is FluidTideModdableWeather) earlier = true;
      int last = earlier ? cycle.Cycle : LastTideBefore(cycle.Cycle);
      string forced = !earlier && _forcedTide != null && _forcedCycle == cycle.Cycle ? _forcedTide : null;
      return FluidTideSelection.StageWeights(cycle.Cycle, last, Settings, forced, OtherWeight(stage, cycle));
    }

    // The summed weight of the other enabled hazardous weathers for this stage, as WeatherGenerator.DecideWeather adds them.
    private long OtherWeight(WeatherCycleStageDecision stage, WeatherCycleDecision cycle) {
      var historyService = _container.GetInstance<WeatherHistoryService>();
      long sum = 0;
      _weighing = true;
      try {
        foreach (IModdableWeather weather in Registry().HazardousWeathers) {
          if (weather is FluidTideModdableWeather || !weather.Enabled) continue;
          _asking = weather;
          int chance = weather.GetChance(stage, cycle, historyService);
          if (chance < 0) throw new InvalidOperationException("Moddable Fluids tides: Moddable Weathers' hazardous weather " + weather.Id + " returned a negative weight " + chance);
          sum += chance;
        }
      } finally { _weighing = false; _asking = null; }
      if (sum >= int.MaxValue) throw new InvalidOperationException("Moddable Fluids tides: the other hazardous weathers' weights (" + sum + ") fill Moddable Weathers' integer roll");
      return sum;
    }

    // The latest earlier cycle with a tide stage in Moddable Weathers' history, 0 for none.
    private int LastTideBefore(int cycle) {
      var history = History();
      for (int c = Math.Min(cycle - 1, history.CycleCount); c >= 1; c--)
        if (TideStage(history[c]) != null) return c;
      return 0;
    }

    // The last tide stage of a saved cycle, by its raw weather ID.
    private WeatherCycleStage TideStage(WeatherCycle cycle) {
      WeatherCycleStage found = null;
      foreach (var stage in cycle.Stages)
        if (!stage.IsBenign && Tides.TryGetByWeather(stage.WeatherId, out _)) found = stage;
      return found;
    }

    private readonly struct DerivedState {
      internal readonly string Current, LastId;
      internal readonly int LastCycle, LastDuration;
      internal DerivedState(string current, int lastCycle, string lastId, int lastDuration) { Current = current; LastCycle = lastCycle; LastId = lastId; LastDuration = lastDuration; }
    }

    /// <summary>
    /// The native binding's tide state as Moddable Weathers' history gives it at <paramref name="cycle"/>: the last tide is
    /// the latest tide stage in this or an earlier cycle (the native binding chooses a cycle's weather when the cycle
    /// starts), with its days; the cycle's tide is the current or next hazardous stage's, as the native
    /// HazardousWeatherService would report it.
    /// </summary>
    private DerivedState Derive(int cycle) {
      var history = History();
      for (int c = Math.Min(cycle, history.CycleCount); c >= 1; c--) {
        var stage = TideStage(history[c]);
        if (stage == null) continue;
        Tides.TryGetByWeather(stage.WeatherId, out var tide);
        return new DerivedState(CurrentCycleTide?.Id, c, tide.Id, stage.Days);
      }
      return new DerivedState(CurrentCycleTide?.Id, 0, null, 0);
    }

    private static string Describe(DerivedState state) =>
      "current " + (state.Current ?? "none") + ", last " + (state.LastId == null ? "none" : state.LastId + " in cycle " + state.LastCycle + " for " + state.LastDuration + " days");

    /// <summary>
    /// Weighs one hazardous stage of the next cycle once while the game loads, as WeatherGenerator.DecideWeather would (no
    /// draw is made and nothing is stored), so a weather that recurses into the tides, a negative weight or weights beyond
    /// Moddable Weathers' integer roll stop the load instead of the first cycle generated in play.
    /// </summary>
    private void DryRun(int cycle) {
      var stage = new WeatherCycleStageDecision { Cycle = cycle, StageIndex = 0, IsBenign = false, DaysMultiplier = 100 };
      var decision = new WeatherCycleDecision { Cycle = cycle, Stages = ImmutableArray.Create(stage) };
      var historyService = _container.GetInstance<WeatherHistoryService>();
      long total = 0;
      foreach (IModdableWeather weather in Registry().HazardousWeathers)
        if (weather.Enabled) total += weather.GetChance(stage, decision, historyService);
      if (total > int.MaxValue) throw new InvalidOperationException("Moddable Fluids tides: the hazardous weathers' weights for cycle " + cycle + " total " + total + ", beyond Moddable Weathers' integer roll");
      _stage = null; _weights = null;
    }

    private int IndexInSettings(string tideId) {
      var tides = Settings.Tides;
      for (int i = 0; i < tides.Count; i++) if (tides[i].TideId == tideId) return i;
      throw new InvalidOperationException("Moddable Fluids tides: this game's tide settings have no entry for " + tideId);
    }

    private ModdableWeatherRegistry Registry() => _registry ??= _container.GetInstance<ModdableWeatherRegistry>();
    private HazardousWeatherService HazardousWeather() => _hazardousWeatherService ??= _container.GetInstance<HazardousWeatherService>();
    private GameCycleService Cycles() => _gameCycleService ??= _container.GetInstance<GameCycleService>();
    private WeatherHistoryRegistry History() => _history ??= _container.GetInstance<WeatherHistoryRegistry>();
  }
}
