using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using Timberborn.BlueprintSystem;
using Timberborn.GameSceneLoading;
using Timberborn.NewGameConfigurationSystem;
using Timberborn.Persistence;
using Timberborn.SceneLoading;
using Timberborn.WorldPersistence;

namespace ModdableFluids.Tides.Prototype {
  /// <summary>
  /// A game mode's own tide settings, the counterpart of the native weather fields of GameModeSpec: the custom mode
  /// carries it after the new-game screen's tide rows (FluidTideNewGameSettings), and a mod may give its own preset
  /// one (a file at the preset's blueprint path holding {"FluidTideGameModeSpec": {...}}). Parallel lists, one entry per
  /// tide. A registered tide the spec does not list gets the values the mode's weather gives (FluidTideModes), so a tide
  /// mod installed later never breaks a mode; a listed tide that no mod registers is an error naming it.
  /// </summary>
  public record FluidTideGameModeSpec : ComponentSpec {
    [Serialize] public int BudgetPercent { get; init; }
    [Serialize] public ImmutableArray<string> TideIds { get; init; }
    [Serialize] public ImmutableArray<bool> Enabled { get; init; }
    [Serialize] public ImmutableArray<int> Weights { get; init; }
    [Serialize] public ImmutableArray<int> CyclesWithoutTide { get; init; }
    [Serialize] public ImmutableArray<int> MinDurationDays { get; init; }
    [Serialize] public ImmutableArray<int> MaxDurationDays { get; init; }

    internal static FluidTideGameModeSpec From(FluidTideSaveSettings settings) => new FluidTideGameModeSpec {
      BudgetPercent = settings.BudgetPercent,
      TideIds = settings.Tides.Select(t => t.TideId).ToImmutableArray(),
      Enabled = settings.Tides.Select(t => t.Enabled).ToImmutableArray(),
      Weights = settings.Tides.Select(t => t.Weight).ToImmutableArray(),
      CyclesWithoutTide = settings.Tides.Select(t => t.CyclesWithoutTide).ToImmutableArray(),
      MinDurationDays = settings.Tides.Select(t => t.MinDurationDays).ToImmutableArray(),
      MaxDurationDays = settings.Tides.Select(t => t.MaxDurationDays).ToImmutableArray(),
    };

    internal FluidTideSaveSettings ToSettings(FluidTideRegistry tides, FluidTideModeWeather weather, string what) {
      int count = TideIds.IsDefault ? -1 : TideIds.Length;
      if (count < 0 || Enabled.IsDefault || Weights.IsDefault || CyclesWithoutTide.IsDefault || MinDurationDays.IsDefault || MaxDurationDays.IsDefault
          || Enabled.Length != count || Weights.Length != count || CyclesWithoutTide.Length != count || MinDurationDays.Length != count || MaxDurationDays.Length != count)
        throw new InvalidOperationException("Moddable Fluids tides: the FluidTideGameModeSpec of " + what + " needs equally long TideIds, Enabled, Weights, CyclesWithoutTide, MinDurationDays and MaxDurationDays");
      return FluidTideSettingsStore.Build(tides, BudgetPercent, Enumerable.Range(0, count).Select(i =>
        (TideIds[i], Enabled[i], Weights[i], CyclesWithoutTide[i], MinDurationDays[i], MaxDurationDays[i])), what,
        tide => FluidTideModes.Derive(tide, weather, out _, out _));
    }
  }

  /// <summary>
  /// Where a game's tide settings come from, in this order:
  /// <list type="number">
  /// <item>the save's own copy (singleton <c>ModdableFluids.TideSettings</c>); a tide registered after the save was made is off
  /// in it, and a saved tide that is no longer registered stops loading, naming it;</item>
  /// <item>a new game: the new game's mode (GameSceneParameters.NewGameConfiguration.GameMode), as native BadtideWeather reads
  /// it: its own FluidTideGameModeSpec (the custom mode), else the values its weather gives (FluidTideModes);</item>
  /// <item>a save made before this save had tide settings: every tide off, with the default budget of the vanilla Normal mode.
  /// The game mode such a save started from is not stored, so nothing better can be derived without guessing.</item>
  /// </list>
  /// Before the last two, FluidTideService asks every IFluidTideImporter for a loaded save without Moddable Fluids tide state.
  /// The settings never change during a game, as the native weather settings do not.
  /// </summary>
  public static class FluidTideSettingsStore {
    public static readonly SingletonKey Key = new SingletonKey("ModdableFluids.TideSettings");
    private static readonly PropertyKey<int> BudgetKey = new PropertyKey<int>("BudgetPercent");
    private static readonly ListKey<string> IdsKey = new ListKey<string>("TideIds");
    private static readonly ListKey<bool> EnabledKey = new ListKey<bool>("Enabled");
    private static readonly ListKey<int> WeightsKey = new ListKey<int>("Weights");
    private static readonly ListKey<int> WithoutKey = new ListKey<int>("CyclesWithoutTide");
    private static readonly ListKey<int> MinKey = new ListKey<int>("MinDurationDays");
    private static readonly ListKey<int> MaxKey = new ListKey<int>("MaxDurationDays");

    public const string SavedSource = "this save", NewGameSource = "the new game's mode", NoSettingsSource = "a save without tide settings (every tide off)";

    public static FluidTideSaveSettings Resolve(FluidTideRegistry tides, ISingletonLoader singletons, ISceneLoader sceneLoader, out string source, out IReadOnlyList<string> notes) {
      var list = new List<string>();
      notes = list;
      if (singletons.TryGetSingleton(Key, out var saved)) {
        source = SavedSource;
        if (!saved.Has(BudgetKey) || !saved.Has(IdsKey) || !saved.Has(EnabledKey) || !saved.Has(WeightsKey) || !saved.Has(WithoutKey) || !saved.Has(MinKey) || !saved.Has(MaxKey))
          throw new InvalidOperationException("Moddable Fluids tides: the saved tide settings (" + Key.Name + ") are incomplete");
        var ids = saved.Get(IdsKey); var enabled = saved.Get(EnabledKey); var weights = saved.Get(WeightsKey);
        var without = saved.Get(WithoutKey); var min = saved.Get(MinKey); var max = saved.Get(MaxKey);
        int n = ids.Count;
        if (enabled.Count != n || weights.Count != n || without.Count != n || min.Count != n || max.Count != n)
          throw new InvalidOperationException("Moddable Fluids tides: the saved tide settings (" + Key.Name + ") have lists of different lengths");
        var settings = Build(tides, saved.Get(BudgetKey), Enumerable.Range(0, n).Select(i => (ids[i], enabled[i], weights[i], without[i], min[i], max[i])), SavedSource,
          tide => new FluidTideSettings(tide.Id, false, 0, 0, 0, 0));
        foreach (var tide in tides.Tides.Where(t => !ids.Contains(t.Id)))
          list.Add(tide.Id + " was installed after this save was made, so it is off in this save (its settings were chosen when the game started)");
        return settings;
      }
      if (sceneLoader.TryGetSceneParameters<GameSceneParameters>(out var parameters) && parameters.NewGame) {
        var mode = parameters.NewGameConfiguration.GameMode ?? throw new InvalidOperationException("Moddable Fluids tides: the new game has no game mode");
        if (mode.Blueprint == null) throw new InvalidOperationException("Moddable Fluids tides: the new game's mode has no blueprint, so its tide settings cannot be read");
        var own = mode.GetSpec<FluidTideGameModeSpec>();
        var weather = Weather(mode, NewGameSource);
        if (own != null) { source = NewGameSource + " (its own tide settings)"; return own.ToSettings(tides, weather, NewGameSource); }
        var defaults = FluidTideModes.Defaults(tides, weather, out var derivations);
        source = NewGameSource + " " + (mode.Blueprint.Name ?? "custom") + ", derived from its weather";
        list.AddRange(derivations);
        return defaults;
      }
      source = NoSettingsSource;
      var normal = FluidTideModes.Defaults(tides, FluidTideModeWeather.VanillaNormal, out _);
      return new FluidTideSaveSettings(normal.BudgetPercent, normal.Tides.Select(t => new FluidTideSettings(t.TideId, false, t.Weight, t.CyclesWithoutTide, t.MinDurationDays, t.MaxDurationDays)));
    }

    public static void Write(ISingletonSaver singletons, FluidTideSaveSettings settings) {
      var data = singletons.GetSingleton(Key);
      data.Set(BudgetKey, settings.BudgetPercent);
      data.Set(IdsKey, settings.Tides.Select(t => t.TideId).ToList());
      data.Set(EnabledKey, settings.Tides.Select(t => t.Enabled).ToList());
      data.Set(WeightsKey, settings.Tides.Select(t => t.Weight).ToList());
      data.Set(WithoutKey, settings.Tides.Select(t => t.CyclesWithoutTide).ToList());
      data.Set(MinKey, settings.Tides.Select(t => t.MinDurationDays).ToList());
      data.Set(MaxKey, settings.Tides.Select(t => t.MaxDurationDays).ToList());
    }

    /// <summary>
    /// A game mode's weather as the tide rule reads it. The badtide chance in whole percent is the native Customize
    /// screen's (Mathf.RoundToInt(chance * 100), ties to even); values the native screen would refuse are an error.
    /// </summary>
    public static FluidTideModeWeather Weather(GameModeSpec mode, string what) {
      static (int, int) Days(MinMaxSpec<int> days, string field, string what) =>
        days == null ? throw new InvalidOperationException("Moddable Fluids tides: " + what + " has no " + field) : (days.Min, days.Max);
      var (tMin, tMax) = Days(mode.TemperateWeatherDuration, "TemperateWeatherDuration", what);
      var (dMin, dMax) = Days(mode.DroughtDuration, "DroughtDuration", what);
      var (bMin, bMax) = Days(mode.BadtideDuration, "BadtideDuration", what);
      float chance = mode.ChanceForBadtide;
      if (!(chance >= 0f && chance <= 1f)) throw new InvalidOperationException("Moddable Fluids tides: " + what + " has a badtide chance outside 0..1");
      try { return new FluidTideModeWeather(tMin, tMax, dMin, dMax, bMin, bMax, (int)Math.Round(chance * 100f)); }
      catch (ArgumentException e) { throw new InvalidOperationException("Moddable Fluids tides: " + what + " has invalid weather settings, so its tide settings cannot be derived: " + e.Message, e); }
    }

    internal static FluidTideSaveSettings Build(FluidTideRegistry tides, int budget, IEnumerable<(string Id, bool Enabled, int Weight, int Without, int Min, int Max)> entries,
        string what, Func<FluidTideDefinition, FluidTideSettings> unlisted) {
      var settings = new List<FluidTideSettings>();
      var unknown = new List<string>();
      foreach (var e in entries) {
        if (!tides.TryGet(e.Id, out _)) { unknown.Add(e.Id); continue; }
        try { settings.Add(new FluidTideSettings(e.Id, e.Enabled, e.Weight, e.Without, e.Min, e.Max)); }
        catch (ArgumentException ex) { throw new InvalidOperationException("Moddable Fluids tides: the tide settings of " + what + " are invalid: " + ex.Message, ex); }
      }
      if (unknown.Count > 0)
        throw new InvalidOperationException("Moddable Fluids tides: " + what + " has settings for tide(s) " + string.Join(", ", unknown)
          + ", which no installed mod registers. Enable the mod that adds them; a save keeps the tides it started with.");
      var missing = tides.Tides.Where(t => settings.All(s => s.TideId != t.Id)).ToArray();
      try { return new FluidTideSaveSettings(budget, settings.Concat(missing.Select(unlisted))); }
      catch (ArgumentException ex) { throw new InvalidOperationException("Moddable Fluids tides: the tide settings of " + what + " are invalid: " + ex.Message, ex); }
    }
  }
}
