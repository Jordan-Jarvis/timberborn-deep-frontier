using System;
using Timberborn.GameSceneLoading;
using Timberborn.Persistence;
using Timberborn.SceneLoading;
using Timberborn.SettingsSystem;
using Timberborn.WorldPersistence;
using ModdableFluids;

namespace ModdableFluids.Tides.Prototype {
  /// <summary>
  /// A Game scene's tide state and settings as the save holds them, shared by both bindings (native
  /// <see cref="FluidTideService"/>, and the Moddable Weathers adapter). Read once, at first use (the weather may ask during
  /// the scene's Load); every save writes both singletons:
  /// <list type="bullet">
  /// <item><c>ModdableFluids.Tides</c>: CurrentCycleTide (tide ID or empty), LastTideCycle, LastTideId, LastTideDuration;</item>
  /// <item><c>ModdableFluids.TideSettings</c> (<see cref="FluidTideSettingsStore"/>).</item>
  /// </list>
  /// They come from, in order:
  /// <list type="number">
  /// <item>both of Moddable Fluids' own singletons; a save with only one of them is refused;</item>
  /// <item>a loaded save with neither: every IFluidTideImporter is asked once (ModdableFluidsHost.ImportTides); the next
  /// save writes the own singletons, so the import never repeats;</item>
  /// <item>otherwise no tide state, and the settings of a new game's mode, or the save's mode defaults (FluidTideSettingsStore).</item>
  /// </list>
  /// </summary>
  public sealed class FluidTideSaveData {
    public static readonly SingletonKey StateKey = new SingletonKey("ModdableFluids.Tides");
    private static readonly PropertyKey<string> CurrentKey = new PropertyKey<string>("CurrentCycleTide");
    private static readonly PropertyKey<int> LastCycleKey = new PropertyKey<int>("LastTideCycle");
    private static readonly PropertyKey<string> LastIdKey = new PropertyKey<string>("LastTideId");
    private static readonly PropertyKey<int> LastDurationKey = new PropertyKey<int>("LastTideDuration");

    private readonly FluidTideRegistry _tides;
    private readonly ISingletonLoader _singletons;
    private readonly ISceneLoader _sceneLoader;
    private readonly ISettings _nativeSettings;
    private FluidTideSaveSettings _settings;
    private bool _loaded, _hadState, _newGame;
    private string _currentCycleTide, _lastTideId, _settingsSource, _importedBy, _loadMessage;
    private int _lastTideCycle, _lastTideDuration;

    public FluidTideSaveData(FluidTideRegistry tides, ISingletonLoader singletons, ISceneLoader sceneLoader, ISettings nativeSettings) {
      _tides = tides ?? throw new ArgumentNullException(nameof(tides));
      _singletons = singletons; _sceneLoader = sceneLoader; _nativeSettings = nativeSettings;
    }

    public FluidTideSaveSettings Settings { get { EnsureLoaded(); return _settings; } }
    /// <summary>The cycle's tide as the state records it (forecast or in progress), or null.</summary>
    public string CurrentCycleTide { get { EnsureLoaded(); return _currentCycleTide; } }
    /// <summary>The cycle of the save's last tide (any tide), 0 for none.</summary>
    public int LastTideCycle { get { EnsureLoaded(); return _lastTideCycle; } }
    public string LastTideId { get { EnsureLoaded(); return _lastTideId; } }
    public int LastTideDuration { get { EnsureLoaded(); return _lastTideDuration; } }
    /// <summary>Whether the state came from the save itself or an importer (rather than from no state at all).</summary>
    public bool HadState { get { EnsureLoaded(); return _hadState; } }
    public bool NewGame { get { EnsureLoaded(); return _newGame; } }
    public string SettingsSource { get { EnsureLoaded(); return _settingsSource; } }
    /// <summary>The provider whose <see cref="IFluidTideImporter"/> supplied this save's tide state, or null.</summary>
    public string ImportedBy { get { EnsureLoaded(); return _importedBy; } }
    /// <summary>What was read, for the scene's log.</summary>
    public string LoadMessage { get { EnsureLoaded(); return _loadMessage; } }

    /// <summary>The cycle's weather was chosen: <paramref name="tideId"/> (or no tide). Its duration follows with <see cref="RecordDuration"/>.</summary>
    public void RecordSelection(int cycle, string tideId) {
      EnsureLoaded();
      _currentCycleTide = tideId;
      if (tideId == null) return;
      if (!_tides.TryGet(tideId, out _)) throw new ArgumentException("Tide " + tideId + " is not registered");
      _lastTideCycle = cycle; _lastTideId = tideId; _lastTideDuration = 0;
    }

    public void RecordDuration(int days) {
      EnsureLoaded();
      if (_lastTideId == null || _lastTideDuration != 0) throw new InvalidOperationException("Moddable Fluids tides: a tide duration arrived without a tide selection waiting for it");
      _lastTideDuration = days;
    }

    /// <summary>Replaces the state after checking it as a saved state is checked (the Moddable Weathers binding derives it from its history).</summary>
    public void SetState(string current, int lastCycle, string lastId, int lastDuration, string what) {
      EnsureLoaded();
      Apply(current, lastCycle, lastId, lastDuration, what);
    }

    public void Save(ISingletonSaver singletonSaver) {
      EnsureLoaded();
      var data = singletonSaver.GetSingleton(StateKey);
      data.Set(CurrentKey, _currentCycleTide ?? "");
      data.Set(LastCycleKey, _lastTideCycle);
      data.Set(LastIdKey, _lastTideId ?? "");
      data.Set(LastDurationKey, _lastTideDuration);
      FluidTideSettingsStore.Write(singletonSaver, _settings);
    }

    public string DescribeState() =>
      "current " + (_currentCycleTide ?? "none") + ", last " + (_lastTideId == null ? "none" : _lastTideId + " in cycle " + _lastTideCycle + " for " + _lastTideDuration + " days");

    private void EnsureLoaded() {
      if (_loaded) return;
      _loaded = true;
      bool hasState = _singletons.TryGetSingleton(StateKey, out var data);
      bool hasSettings = _singletons.TryGetSingleton(FluidTideSettingsStore.Key, out _);
      if (hasState != hasSettings)
        throw new InvalidOperationException("Moddable Fluids tides: this save has " + (hasState ? StateKey.Name + " but not " + FluidTideSettingsStore.Key.Name : FluidTideSettingsStore.Key.Name + " but not " + StateKey.Name)
          + "; every save writes both");
      _newGame = _sceneLoader.TryGetSceneParameters<GameSceneParameters>(out var parameters) && parameters.NewGame;
      if (hasState) {
        _hadState = true;
        string current = data.Get(CurrentKey), lastId = data.Get(LastIdKey);
        Apply(current.Length == 0 ? null : current, data.Get(LastCycleKey), lastId.Length == 0 ? null : lastId, data.Get(LastDurationKey), "saved");
      } else if (!_newGame) {
        var import = ModdableFluidsEntry.Host.ImportTides(new FluidTideImportContext(_tides, _singletons, _nativeSettings), out string importer);
        if (import != null) {
          _hadState = true;
          _importedBy = importer;
          Apply(import.CurrentCycleTideId, import.LastTideCycle, import.LastTideId, import.LastTideDuration, "imported");
          _settings = import.Settings;
          _settingsSource = "this save's earlier tide state, imported by " + importer;
          _loadMessage = "[ModdableFluids] Tide state and settings imported by " + importer + ": " + import;
          return;
        }
      }
      _settings = FluidTideSettingsStore.Resolve(_tides, _singletons, _sceneLoader, out string source, out var notes);
      _settingsSource = source;
      _loadMessage = "[ModdableFluids] Tide settings from " + source + ": " + _settings + (notes.Count > 0 ? "\n  " + string.Join("\n  ", notes) : "");
    }

    private void Apply(string current, int lastCycle, string lastId, int lastDuration, string what) {
      if (lastCycle < 0 || lastDuration < 0 || (lastCycle == 0) != (lastId == null) || (lastCycle == 0 && (lastDuration != 0 || current != null))
          || (lastCycle > 0 && lastCycle < FluidTideRules.EarliestCycle) || (current != null && current != lastId))
        throw new InvalidOperationException("Moddable Fluids tides: the " + what + " tide state is invalid (current " + current + ", last " + lastId + " in cycle " + lastCycle + " for " + lastDuration + " days)");
      if (current != null && !_tides.TryGet(current, out _))
        throw new InvalidOperationException("Moddable Fluids tides: this save is in a " + current + ", which no installed mod registers. Enable the mod that adds it.");
      _currentCycleTide = current; _lastTideCycle = lastCycle; _lastTideId = lastId; _lastTideDuration = lastDuration;
    }
  }
}
