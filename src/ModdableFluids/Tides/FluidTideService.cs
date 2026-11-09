using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using Timberborn.AutomationBuildings;
using Timberborn.BlueprintSystem;
using Timberborn.Common;
using Timberborn.GameCycleSystem;
using Timberborn.GameSound;
using Timberborn.HazardousWeatherSystem;
using Timberborn.Persistence;
using Timberborn.GameSceneLoading;
using Timberborn.SceneLoading;
using Timberborn.SettingsSystem;
using Timberborn.SingletonSystem;
using Timberborn.TickSystem;
using Timberborn.WeatherSystem;
using Timberborn.WorldPersistence;
using ModdableFluids;
using ModdableFluids.Runtime.Prototype;
using UnityEngine;

namespace ModdableFluids.Tides.Prototype {
  /// <summary>
  /// One registered tide as a native hazardous weather. HazardousWeatherService stores it as the cycle's weather, posts
  /// the native selected, started and ended events with it and keeps it in the native history under
  /// <see cref="Id"/>. Native systems that test for DroughtWeather or BadtideWeather treat it as neither, so sources keep
  /// their flow apart from the tide's own strength modifier.
  /// </summary>
  public sealed class FluidTideWeather : IHazardousWeather {
    private readonly FluidTideService _service;
    public FluidTideDefinition Definition { get; }
    internal FluidTideWeather(FluidTideService service, FluidTideDefinition definition) { _service = service; Definition = definition; }
    public string Id => Definition.NativeWeatherId;
    /// <summary>Native passes the count of earlier occurrences + 1. Tides have no early-game handicap: uniform whole days.</summary>
    public int GetDurationAtCycle(int cycle) => _service.DrawDuration(Definition);
    public override string ToString() => Id;
  }

  /// <summary>
  /// The Game scene's tide owner: the save's settings and tide state, the native weather patches for this scene, and the
  /// source effect of the tide in progress.
  /// <list type="bullet">
  /// <item><b>Selection.</b> A postfix on HazardousWeatherRandomizer.GetRandomWeatherForCycle (called once per cycle from
  /// HazardousWeatherService.SetForCycle) applies <see cref="FluidTideSelection.Select"/> after the native draw.</item>
  /// <item><b>Restore.</b> Native Save writes only IsDrought; a postfix on HazardousWeatherService.Load puts a saved tide
  /// back before anything reads the weather.</item>
  /// <item><b>Presentation.</b> The native UI helper and start-sound player know only drought and badtide; while a tide is
  /// the cycle's weather the patches answer with the tide's texts, marker classes and alarm (FluidTideUi draws its art).</item>
  /// <item><b>Source effect.</b> While the tide is in progress this service owns the world's source composition
  /// (owner <c>ModdableFluids.Tides</c>), and FluidTideStrengthModifier scales tide-overridable sources natively.</item>
  /// </list>
  /// The patches are installed when the service is constructed (every singleton is constructed before the first Load,
  /// so before native HazardousWeatherService.Load and the first SetForCycle) and removed on unload. With no registered
  /// tide nothing is bound (FluidTidesConfigurator). Saved under <c>ModdableFluids.Tides</c> (state) and <c>ModdableFluids.TideSettings</c>.
  /// </summary>
  public sealed class FluidTideService : ILoadableSingleton, IPostLoadableSingleton, ISaveableSingleton, ITickableSingleton, IUnloadableSingleton {
    public const string OwnerId = "ModdableFluids.Tides";
    private static readonly SingletonKey StateKey = new SingletonKey("ModdableFluids.Tides");
    private static readonly PropertyKey<string> CurrentKey = new PropertyKey<string>("CurrentCycleTide");
    private static readonly PropertyKey<int> LastCycleKey = new PropertyKey<int>("LastTideCycle");
    private static readonly PropertyKey<string> LastIdKey = new PropertyKey<string>("LastTideId");
    private static readonly PropertyKey<int> LastDurationKey = new PropertyKey<int>("LastTideDuration");
    // Marker classes the native panels add where they would add the badtide ones; unstyled, FluidTideUi recognises them.
    internal const string DatePanelClass = "moddable-fluids-tide-date", WeatherPanelClass = "moddable-fluids-tide-weather", NotificationClass = "moddable-fluids-tide-notification";

    internal static FluidTideService Current { get; private set; }

    private readonly ISingletonLoader _singletons;
    private readonly ISceneLoader _sceneLoader;
    private readonly EventBus _eventBus;
    private readonly HazardousWeatherService _hazardousWeatherService;
    private readonly HazardousWeatherHistory _history;
    private readonly WeatherService _weatherService;
    private readonly GameCycleService _gameCycleService;
    private readonly IRandomNumberGenerator _random;
    private readonly GameUISoundController _sound;
    private readonly ISpecService _specs;
    private readonly ModdableFluidsSceneOwner _sceneOwner;
    private readonly FluidTidePatchSet _patches = new FluidTidePatchSet(OwnerId);
    private readonly Dictionary<string, FluidTideWeather> _weathers = new Dictionary<string, FluidTideWeather>(StringComparer.Ordinal);
    private readonly ISettings _nativeSettings;
    private FluidTideSaveSettings _settings;
    private bool _loaded, _hadState;
    private string _loadMessage;
    private string _currentCycleTide, _forcedTide;
    private FluidTideDefinition _composing;

    public FluidTideRegistry Tides { get; }
    public int LastTideCycle { get; private set; }
    public string LastTideId { get; private set; }
    public int LastTideDuration { get; private set; }
    public string SettingsSource { get; private set; }
    /// <summary>The provider whose <see cref="IFluidTideImporter"/> supplied this save's tide state, or null.</summary>
    public string ImportedBy { get; private set; }

    public FluidTideService(ISingletonLoader singletons, ISceneLoader sceneLoader, EventBus eventBus, HazardousWeatherService hazardousWeatherService,
        HazardousWeatherHistory history, WeatherService weatherService, GameCycleService gameCycleService, IRandomNumberGenerator random,
        GameUISoundController sound, ISpecService specs, ISettings nativeSettings, ModdableFluidsSceneOwner sceneOwner) {
      _nativeSettings = nativeSettings;
      _singletons = singletons; _sceneLoader = sceneLoader; _eventBus = eventBus; _hazardousWeatherService = hazardousWeatherService; _history = history;
      _weatherService = weatherService; _gameCycleService = gameCycleService; _random = random; _sound = sound; _specs = specs; _sceneOwner = sceneOwner;
      if (Current != null) throw new InvalidOperationException("Moddable Fluids tides: a tide service is already active; the previous Game scene was not unloaded");
      var host = ModdableFluidsEntry.Host;
      host.Freeze();
      Tides = host.Tides;
      foreach (var tide in Tides.Tides) _weathers.Add(tide.Id, new FluidTideWeather(this, tide));
      if (Tides.Count == 0) throw new InvalidOperationException("Moddable Fluids tides: the tide service was bound without registered tides");
      Current = this;
      try {
        var targets = FluidTideNative.VerifyGame();
        _patches.Install(targets, FluidTidePatches.Apply);
      } catch {
        Current = null;
        throw;
      }
    }

    internal static FluidTideService RequireCurrent() =>
      Current ?? throw new InvalidOperationException("Moddable Fluids tides: the native weather was used outside a Game scene with a tide service");

    /// <summary>The game's tide settings, read on first use: the native weather may ask during the Game scene's Load.</summary>
    public FluidTideSaveSettings Settings { get { EnsureLoaded(); return _settings; } }
    public bool PatchesInstalled => _patches.Installed;
    /// <summary>The cycle's tide (forecast or in progress), from the native service's current weather.</summary>
    public FluidTideDefinition CurrentCycleTide => (_hazardousWeatherService.CurrentCycleHazardousWeather as FluidTideWeather)?.Definition;
    public bool IsCurrentCycleTide => CurrentCycleTide != null;
    public bool IsEmitting => _weatherService.IsHazardousWeather && IsCurrentCycleTide;
    public FluidTideWeather WeatherOf(string tideId) => _weathers.TryGetValue(tideId, out var weather) ? weather : throw new ArgumentException("Tide " + tideId + " is not registered");

    /// <summary>The native strength multiplier of a source of this type: the tide's rule while it is in progress (FluidTideDefinition.StrengthMultiplierFor), else 1.</summary>
    public float StrengthMultiplier(FluidSourceTypeDefinition type) {
      if (type == null) throw new ArgumentNullException(nameof(type));
      var tide = IsEmitting ? CurrentCycleTide : null;
      return tide != null ? (float)tide.StrengthMultiplierFor(type) : 1f;
    }

    public void Load() {
      EnsureLoaded();
      Debug.Log(_loadMessage);
      _eventBus.Register(this);
    }

    public void PostLoad() {
      FluidTideContent.RequireFog(_specs, Tides);
      var current = _hazardousWeatherService.CurrentCycleHazardousWeather;
      if (_currentCycleTide != null) {
        if (!(current is FluidTideWeather weather) || weather.Definition.Id != _currentCycleTide)
          throw new InvalidOperationException("Moddable Fluids tides: the saved tide " + _currentCycleTide + " was not restored into HazardousWeatherService");
        if (LastTideCycle != _gameCycleService.Cycle)
          throw new InvalidOperationException("Moddable Fluids tides: the saved tide belongs to cycle " + LastTideCycle + ", but the game is in cycle " + _gameCycleService.Cycle);
        if (LastTideDuration != _hazardousWeatherService.HazardousWeatherDuration)
          throw new InvalidOperationException("Moddable Fluids tides: the saved tide lasts " + LastTideDuration + " days, but the native hazardous weather lasts " + _hazardousWeatherService.HazardousWeatherDuration);
      } else if (current is FluidTideWeather) {
        throw new InvalidOperationException("Moddable Fluids tides: HazardousWeatherService holds a tide this save does not record");
      }
      if (!_hadState) {
        // A save without Moddable Fluids tide state whose native history already holds a registered tide's weather was
        // played under another tide system (for example Deep Frontier's own radioactive tide). Its tide state cannot be
        // read here; refuse instead of guessing the cooldown and the cycle's weather.
        var seen = Tides.Tides.Where(t => _history.GetCyclesCount(t.NativeWeatherId) > 0).Select(t => t.Id + " (" + t.NativeWeatherId + ")").ToArray();
        if (seen.Length > 0)
          throw new InvalidOperationException("Moddable Fluids tides: this save's weather history holds " + string.Join(", ", seen)
            + ", but the save has no Moddable Fluids tide state and no installed tide importer (IFluidTideImporter) read it: it was played with another tide system.");
      }
    }

    public void Save(ISingletonSaver singletonSaver) {
      var data = singletonSaver.GetSingleton(StateKey);
      data.Set(CurrentKey, _currentCycleTide ?? "");
      data.Set(LastCycleKey, LastTideCycle);
      data.Set(LastIdKey, LastTideId ?? "");
      data.Set(LastDurationKey, LastTideDuration);
      FluidTideSettingsStore.Write(singletonSaver, Settings);
    }

    public void Tick() {
      // While the tide is in progress this service owns the world's source composition; it clears it when the tide ends.
      var tide = IsEmitting ? CurrentCycleTide : null;
      if (tide == _composing) return;
      var world = _sceneOwner.World ?? throw new InvalidOperationException("Moddable Fluids tides: the scene has no world service to apply the tide's source emission");
      world.SetSourceComposition(OwnerId, tide?.SourceEmission);
      _composing = tide;
    }

    public void Unload() {
      try { _patches.Uninstall(); }
      finally { if (Current == this) Current = null; }
    }

    // Postfix of HazardousWeatherService.Load (Game scene).
    internal void RestoreAfterNativeLoad(HazardousWeatherService native) {
      if (native != _hazardousWeatherService) throw new InvalidOperationException("Moddable Fluids tides: a foreign HazardousWeatherService was loaded");
      EnsureLoaded();
      if (_currentCycleTide != null) FluidTideNative.SetCurrentWeather(native, WeatherOf(_currentCycleTide));
    }

    // Postfix of HazardousWeatherRandomizer.GetRandomWeatherForCycle, after the native drought/badtide draw.
    internal IHazardousWeather SelectForCycle(int cycle, IHazardousWeather native) {
      if (native == null) throw new InvalidOperationException("Moddable Fluids tides: the native weather randomizer chose no weather for cycle " + cycle);
      EnsureLoaded();
      string forced = cycle >= FluidTideRules.EarliestCycle ? _forcedTide : null;
      string selected = FluidTideSelection.Select(cycle, LastTideCycle, Settings, forced, new NativeRandom(_random));
      if (forced != null) _forcedTide = null;
      _currentCycleTide = selected;
      if (selected == null) return native;
      LastTideCycle = cycle; LastTideId = selected; LastTideDuration = 0;   // the duration arrives with the native selected event
      return WeatherOf(selected);
    }

    internal int DrawDuration(FluidTideDefinition tide) {
      var settings = Settings.Get(tide.Id);
      if (!settings.Enabled) throw new InvalidOperationException("Moddable Fluids tides: a duration was drawn for " + tide.Id + ", which is off in this game");
      return _random.Range(settings.MinDurationDays, settings.MaxDurationDays + 1);
    }

    [OnEvent]
    public void OnHazardousWeatherSelected(HazardousWeatherSelectedEvent selectedEvent) {
      string selected = (selectedEvent.SelectedWeather as FluidTideWeather)?.Definition.Id;
      if (selected != _currentCycleTide)
        throw new InvalidOperationException("Moddable Fluids tides: native selected " + selectedEvent.SelectedWeather?.Id + ", but the tide selection recorded " + (_currentCycleTide ?? "no tide"));
      if (selected == null) return;
      if (selectedEvent.Duration < FluidTideRules.DurationLowest) throw new InvalidOperationException("Moddable Fluids tides: " + selected + " drew an invalid duration of " + selectedEvent.Duration + " days");
      LastTideDuration = selectedEvent.Duration;
    }

    /// <summary>Development: the next cycle's hazardous weather is this tide, ignoring cycles without, the budget and the cooldown. Not saved.</summary>
    public void ForceNextCycle(string tideId) {
      if (!Settings.Get(tideId).Enabled) throw new InvalidOperationException("Tide " + tideId + " is off in this game's settings (chosen when the game was started)");
      _forcedTide = tideId;
    }

    internal bool TryPlayStartSound(IHazardousWeather weather) {
      if (!(weather is FluidTideWeather tide)) return false;
      if (tide.Definition.Presentation.StartSound == FluidTideRules.BadtideSound) _sound.PlayBadtideStartedSound();
      else _sound.PlayDroughtStartedSound();
      return true;
    }

    internal string UiValue(string getterName) {
      var tide = CurrentCycleTide ?? throw new InvalidOperationException("Moddable Fluids tides: the weather UI asked for a tide value outside a tide");
      var p = tide.Presentation;
      switch (getterName) {
        case "get_NameLocKey": return tide.DisplayNameLocKey;
        case "get_ApproachingLocKey": return p.ApproachingLocKey;
        case "get_InProgressLocKey": return p.InProgressLocKey;
        case "get_StartedNotificationLocKey": return p.StartedLocKey;
        case "get_EndedNotificationLocKey": return p.EndedLocKey;
        case "get_InProgressClass": return WeatherPanelClass;
        case "get_IconClass": return DatePanelClass;
        case "get_NotificationBackgroundClass": return NotificationClass;
        default: throw new ArgumentException("Moddable Fluids tides have no value for HazardousWeatherUIHelper." + getterName);
      }
    }

    /// <summary>
    /// Reads the save's tide state and settings once, at first use (the native weather may ask during the scene's Load):
    /// <list type="number">
    /// <item>both of Moddable Fluids' own singletons, written together by every save;</item>
    /// <item>a loaded save with neither: every IFluidTideImporter is asked once (ModdableFluidsHost.ImportTides); the next
    /// save writes the own singletons, so the import never repeats;</item>
    /// <item>otherwise no tide state, and the settings of a new game's mode, or every tide off (FluidTideSettingsStore).</item>
    /// </list>
    /// </summary>
    private void EnsureLoaded() {
      if (_loaded) return;
      _loaded = true;
      bool hasState = _singletons.TryGetSingleton(StateKey, out var data);
      bool hasSettings = _singletons.TryGetSingleton(FluidTideSettingsStore.Key, out _);
      if (hasState != hasSettings)
        throw new InvalidOperationException("Moddable Fluids tides: this save has " + (hasState ? StateKey.Name + " but not " + FluidTideSettingsStore.Key.Name : FluidTideSettingsStore.Key.Name + " but not " + StateKey.Name)
          + "; every save writes both");
      bool newGame = _sceneLoader.TryGetSceneParameters<GameSceneParameters>(out var parameters) && parameters.NewGame;
      if (hasState) {
        _hadState = true;
        string current = data.Get(CurrentKey), lastId = data.Get(LastIdKey);
        SetState(current.Length == 0 ? null : current, data.Get(LastCycleKey), lastId.Length == 0 ? null : lastId, data.Get(LastDurationKey), "saved");
      } else if (!newGame) {
        var import = ModdableFluidsEntry.Host.ImportTides(new FluidTideImportContext(Tides, _singletons, _nativeSettings), out string importer);
        if (import != null) {
          _hadState = true;
          ImportedBy = importer;
          SetState(import.CurrentCycleTideId, import.LastTideCycle, import.LastTideId, import.LastTideDuration, "imported");
          _settings = import.Settings;
          SettingsSource = "this save's earlier tide state, imported by " + importer;
          _loadMessage = "[ModdableFluids] Tide state and settings imported by " + importer + ": " + import;
          return;
        }
      }
      _settings = FluidTideSettingsStore.Resolve(Tides, _singletons, _sceneLoader, out string source, out var notes);
      SettingsSource = source;
      _loadMessage = "[ModdableFluids] Tide settings from " + source + ": " + _settings + (notes.Count > 0 ? "\n  " + string.Join("\n  ", notes) : "");
    }

    private void SetState(string current, int lastCycle, string lastId, int lastDuration, string what) {
      _currentCycleTide = current; LastTideCycle = lastCycle; LastTideId = lastId; LastTideDuration = lastDuration;
      if (LastTideCycle < 0 || LastTideDuration < 0 || (LastTideCycle == 0) != (LastTideId == null) || (LastTideCycle == 0 && (LastTideDuration != 0 || _currentCycleTide != null))
          || (LastTideCycle > 0 && LastTideCycle < FluidTideRules.EarliestCycle) || (_currentCycleTide != null && _currentCycleTide != LastTideId))
        throw new InvalidOperationException("Moddable Fluids tides: the " + what + " tide state is invalid (current " + current + ", last " + lastId + " in cycle " + LastTideCycle + " for " + LastTideDuration + " days)");
      if (_currentCycleTide != null && !Tides.TryGet(_currentCycleTide, out _))
        throw new InvalidOperationException("Moddable Fluids tides: this save is in a " + _currentCycleTide + ", which no installed mod registers. Enable the mod that adds it.");
    }

    private sealed class NativeRandom : IFluidTideRandom {
      private readonly IRandomNumberGenerator _random;
      internal NativeRandom(IRandomNumberGenerator random) { _random = random; }
      public bool CheckProbability(float normalizedProbability) => _random.CheckProbability(normalizedProbability);
      public int Range(int inclusiveMin, int exclusiveMax) => _random.Range(inclusiveMin, exclusiveMax);
    }
  }

  /// <summary>The scene's Harmony patches; each dispatches to the current tide service and is inert outside a tide.</summary>
  internal static class FluidTidePatches {
    internal static void Apply(Harmony harmony) {
      harmony.Patch(FluidTideNative.Randomizer(), postfix: new HarmonyMethod(typeof(FluidTidePatches), nameof(SelectionPostfix)));
      harmony.Patch(FluidTideNative.ServiceLoad(), postfix: new HarmonyMethod(typeof(FluidTidePatches), nameof(RestorePostfix)));
      harmony.Patch(FluidTideNative.UiSpecification(), prefix: new HarmonyMethod(typeof(FluidTidePatches), nameof(UiSpecificationPrefix)));
      foreach (var getter in FluidTideNative.UiGetters()) harmony.Patch(getter, prefix: new HarmonyMethod(typeof(FluidTidePatches), nameof(UiTextPrefix)));
      harmony.Patch(FluidTideNative.StartSound(), prefix: new HarmonyMethod(typeof(FluidTidePatches), nameof(StartSoundPrefix)));
      harmony.Patch(FluidTideNative.StationSample(), prefix: new HarmonyMethod(typeof(FluidTidePatches), nameof(StationSamplePrefix)));
      harmony.Patch(FluidTideNative.StationUpdateOutput(), prefix: new HarmonyMethod(typeof(FluidTidePatches), nameof(StationOutputPrefix)));
      harmony.Patch(FluidTideNative.FragmentInitialize(), postfix: new HarmonyMethod(typeof(FluidTidePatches), nameof(FragmentInitializePostfix)));
      harmony.Patch(FluidTideNative.FragmentUpdate(), postfix: new HarmonyMethod(typeof(FluidTidePatches), nameof(FragmentUpdatePostfix)));
    }

    // Weather Station: sample the cycle's tide just before the native sample; while a tide mode is on, set the output
    // instead of the native mode switch (one SetState per update, as native). The panel gets one radio button per tide.
    private static void StationSamplePrefix(WeatherStation __instance) =>
      FluidTideWeatherStation.Of(__instance).Sample(FluidTideService.RequireCurrent().CurrentCycleTide?.Id);
    private static bool StationOutputPrefix(WeatherStation __instance) {
      var station = FluidTideWeatherStation.Of(__instance);
      if (station.SignalledTide == null) return true;
      station.SetOutput(FluidTideNative.WithinActivationTimeHazardous(__instance));
      return false;
    }
    private static void FragmentInitializePostfix(object __instance) => FluidTideStationPanel.Initialize(__instance, FluidTideService.RequireCurrent().Tides);
    private static void FragmentUpdatePostfix(object __instance) => FluidTideStationPanel.Update(__instance);

    private static void SelectionPostfix(int cycle, ref IHazardousWeather __result) => __result = FluidTideService.RequireCurrent().SelectForCycle(cycle, __result);
    private static void RestorePostfix(HazardousWeatherService __instance) => FluidTideService.RequireCurrent().RestoreAfterNativeLoad(__instance);
    // The native helper throws for an unknown weather; while a tide is the cycle's weather the getters below answer instead.
    private static bool UiSpecificationPrefix() => !FluidTideService.RequireCurrent().IsCurrentCycleTide;
    private static bool UiTextPrefix(MethodBase __originalMethod, ref string __result) {
      var service = FluidTideService.RequireCurrent();
      if (!service.IsCurrentCycleTide) return true;
      __result = service.UiValue(__originalMethod.Name);
      return false;
    }
    private static bool StartSoundPrefix(HazardousWeatherStartedEvent hazardousWeatherStartedEvent) =>
      !FluidTideService.RequireCurrent().TryPlayStartSound(hazardousWeatherStartedEvent.HazardousWeather);
  }

  /// <summary>Content checks: every tide's native weather has fog in every day stage, or the native Sun throws mid-game.</summary>
  internal static class FluidTideContent {
    private static readonly string[] Stages = { "SunriseColors", "DayColors", "SunsetColors", "NightColors" };

    internal static void RequireFog(ISpecService specs, FluidTideRegistry tides) {
      var sunSpec = Type.GetType("Timberborn.SkySystem.SunSpec, Timberborn.SkySystem") ?? throw FluidTideNative.Changed("Timberborn.SkySystem.SunSpec");
      var get = typeof(ISpecService).GetMethod(nameof(ISpecService.GetSingleSpec)) ?? throw FluidTideNative.Changed("ISpecService.GetSingleSpec<T>()");
      object sun = get.MakeGenericMethod(sunSpec).Invoke(specs, null);
      var missing = new List<string>();
      foreach (string stage in Stages) {
        object colors = sunSpec.GetProperty(stage)?.GetValue(sun) ?? throw FluidTideNative.Changed("SunSpec." + stage);
        var fogs = colors.GetType().GetProperty("HazardousWeatherFogs")?.GetValue(colors) as IEnumerable ?? throw FluidTideNative.Changed("DayStageColorsSpec.HazardousWeatherFogs");
        var ids = new HashSet<string>(StringComparer.Ordinal);
        foreach (object fog in fogs) ids.Add((string)(fog.GetType().GetProperty("HazardousWeatherId")?.GetValue(fog) ?? throw FluidTideNative.Changed("HazardousWeatherFogSettingsSpec.HazardousWeatherId")));
        foreach (var tide in tides.Tides) if (!ids.Contains(tide.NativeWeatherId)) missing.Add(tide.Id + " (" + tide.NativeWeatherId + ") in " + stage);
      }
      if (missing.Count > 0)
        throw new InvalidOperationException("Moddable Fluids tides: these tides have no sky fog, so the native Sun would fail when they start: " + string.Join(", ", missing)
          + ". The mod that registers a tide adds a HazardousWeatherFogs entry for its weather ID to every day stage of Configurations/Sun.");
    }
  }
}
