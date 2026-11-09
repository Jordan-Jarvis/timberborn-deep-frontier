using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using HarmonyLib;
using ModdableFluids.Tides.Prototype;
using Timberborn.BlueprintSystem;
using Timberborn.Common;
using Timberborn.GameSceneLoading;
using Timberborn.HazardousWeatherSystem;
using Timberborn.HazardousWeatherSystemUI;
using Timberborn.MainMenuPanels;
using Timberborn.MapStateSystem;
using Timberborn.NewGameConfigurationSystem;
using Timberborn.Persistence;
using Timberborn.SceneLoading;
using Timberborn.SerializationSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace ModdableFluids.Tides.Acceptance {
  /// <summary>
  /// The tide adapter against the installed native weather types, in the game's Mono: the startup contract, per-scene
  /// install and uninstall, foreign-owner refusal, the real HazardousWeatherRandomizer through the selection postfix,
  /// the restore postfix on the real HazardousWeatherService.Load, the UI helper prefixes, the new-game patch, the
  /// settings of a new game, and the fog check. No engine call: the probe never logs through UnityEngine.
  /// </summary>
  public static class TidesMonoProbe {
    private const BindingFlags Any = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;
    private static readonly List<string> Calls = new List<string>();
    private static readonly Queue<object> Script = new Queue<object>();

    public static string Run(string managed) {
      int checks = 0;
      void Check(bool condition, string name) { checks++; if (!condition) throw new InvalidOperationException("Tide probe: " + name); }
      void Throws(Action action, string expected, string name) {
        try { action(); }
        catch (Exception e) {
          var cause = e is TargetInvocationException t && t.InnerException != null ? t.InnerException : e;
          Check(cause is InvalidOperationException && cause.Message.Contains(expected), name + " (got " + cause.GetType().Name + ": " + cause.Message + ")");
          return;
        }
        Check(false, name + " did not throw");
      }
      object Internal(Type type, string name, object target, params object[] arguments) {
        try { return type.GetMethod(name, Any).Invoke(target, arguments); }
        catch (TargetInvocationException e) when (e.InnerException != null) { System.Runtime.ExceptionServices.ExceptionDispatchInfo.Capture(e.InnerException).Throw(); throw; }
      }
      var runtime = typeof(FluidTideService).Assembly;
      Type Native() => runtime.GetType("ModdableFluids.Tides.Prototype.FluidTideNative", true);
      Type Content() => runtime.GetType("ModdableFluids.Tides.Prototype.FluidTideContent", true);
      FluidTideService CurrentService() => (FluidTideService)typeof(FluidTideService).GetProperty("Current", Any).GetValue(null);
      string[] Owners(MethodBase method) => Harmony.GetPatchInfo(method)?.Owners.Distinct().ToArray() ?? new string[0];

      var host = ModdableFluidsEntry.Host;
      host.RegisterProvider(new Provider("DeepFrontier.Radiation", "DeepFrontier", "RadioactiveWater", "RadioactiveTide", "RadioactiveTideWeather", 1.0,
        new[] { (15, 24, 2, 4), (25, 14, 3, 6), (35, 9, 5, 10) }));
      host.RegisterProvider(new Provider("MoreFluids.Liquids", "MoreFluids", "Coffee", "CoffeeTide", "MoreFluids.CoffeeTide", .5,
        new[] { (10, 12, 2, 4), (15, 8, 3, 5), (20, 6, 4, 7) }));
      host.RegisterProvider(new Importer());
      host.Freeze();
      var tides = host.Tides;
      Check(tides.Count == 2, "two tides registered");

      // The game's own objects, with fakes only where the engine or a loaded save would supply them.
      var random = new ScriptedRandom();
      var mapMode = MapEditorMode.NonMapEditorInstance();
      var drought = new DroughtWeather(null, random, mapMode, null);
      var badtide = new BadtideWeather(null, random, mapMode, null, null);
      var history = new HazardousWeatherHistory(null, null, null);
      var randomizer = new HazardousWeatherRandomizer(drought, badtide, history, random);
      var weatherService = new HazardousWeatherService(null, new EmptyLoader(), mapMode, drought, badtide, randomizer, history);
      var normal = new Blueprint("GameMode.Normal", new ComponentSpec[] { Mode(13, 17, 5, 9, 4, 8, .4f) }, ImmutableArray<Blueprint>.Empty).GetSpec<GameModeSpec>();
      var scene = new SceneLoader(GameSceneParameters.CreateNewGameParameters(new NewGameConfiguration("Folktails", default(Timberborn.MapRepositorySystem.MapFileReference), normal, "Probe")));

      // A new game's settings: derived from its mode's weather.
      var settings = FluidTideSettingsStore.Resolve(tides, new EmptyLoader(), scene, out string source, out var notes);
      Check(settings.BudgetPercent == 25 && settings.Get("DeepFrontier.RadioactiveTide").Weight == 25 && settings.Get("MoreFluids.CoffeeTide").Weight == 15
        && settings.Get("DeepFrontier.RadioactiveTide").CyclesWithoutTide == 14 && source.Contains("GameMode.Normal") && notes.Count == 2, "new Normal game settings: " + settings + " from " + source);
      var custom = (GameModeSpec)Internal(typeof(FluidTideNewGameSettings), "WithTides", null,
        new Blueprint(null, new ComponentSpec[] { Mode(10, 10, 3, 3, 3, 3, .5f) }, ImmutableArray<Blueprint>.Empty).GetSpec<GameModeSpec>(),
        Internal(typeof(FluidTideGameModeSpec), "From", null, new FluidTideSaveSettings(40, new[] {
          new FluidTideSettings("DeepFrontier.RadioactiveTide", true, 3, 5, 2, 2), new FluidTideSettings("MoreFluids.CoffeeTide", false, 0, 0, 0, 0) })));
      var own = FluidTideSettingsStore.Resolve(tides, new EmptyLoader(), new SceneLoader(GameSceneParameters.CreateNewGameParameters(new NewGameConfiguration("Folktails", default(Timberborn.MapRepositorySystem.MapFileReference), custom, "Probe"))), out source, out _);
      Check(own.BudgetPercent == 40 && own.Get("DeepFrontier.RadioactiveTide").Weight == 3 && !own.Get("MoreFluids.CoffeeTide").Enabled && source.Contains("its own"), "custom mode keeps its tide rows: " + own);
      var partialMode = (GameModeSpec)Internal(typeof(FluidTideNewGameSettings), "WithTides", null,
        new Blueprint(null, new ComponentSpec[] { Mode(10, 10, 3, 3, 3, 3, .5f) }, ImmutableArray<Blueprint>.Empty).GetSpec<GameModeSpec>(),
        new FluidTideGameModeSpec { BudgetPercent = 30, TideIds = ImmutableArray.Create("DeepFrontier.RadioactiveTide"), Enabled = ImmutableArray.Create(true),
          Weights = ImmutableArray.Create(7), CyclesWithoutTide = ImmutableArray.Create(5), MinDurationDays = ImmutableArray.Create(1), MaxDurationDays = ImmutableArray.Create(2) });
      var partial = FluidTideSettingsStore.Resolve(tides, new EmptyLoader(), new SceneLoader(GameSceneParameters.CreateNewGameParameters(new NewGameConfiguration("Folktails", default(Timberborn.MapRepositorySystem.MapFileReference), partialMode, "Probe"))), out _, out _);
      var derivedCoffee = FluidTideModes.Derive(tides.Get("MoreFluids.CoffeeTide"), new FluidTideModeWeather(10, 10, 3, 3, 3, 3, 50), out _, out _);
      Check(partial.BudgetPercent == 30 && partial.Get("DeepFrontier.RadioactiveTide").Weight == 7 && partial.Get("MoreFluids.CoffeeTide").Enabled
        && partial.Get("MoreFluids.CoffeeTide").Weight == derivedCoffee.Weight, "a mode's own spec without a tide derives that tide from the mode's weather: " + partial);
      var saved = FluidTideSettingsStore.Resolve(tides, new EmptyLoader(), new SceneLoader(null), out source, out _);
      Check(saved.Tides.All(t => !t.Enabled) && source == FluidTideSettingsStore.NoSettingsSource, "a save without tide settings has every tide off");

      // Scene 1: the service verifies the contract and installs its patches on construction.
      var service = NewService(weatherService, history, random, scene, settings);
      var targets = (MethodInfo[])Internal(Native(), "VerifyGame", null);
      Check(targets.Length == 12 && targets.All(t => Owners(t).SequenceEqual(new[] { FluidTideService.OwnerId })), "every native target patched by ModdableFluids.Tides only");
      Throws(() => NewService(weatherService, history, random, scene, settings), "already active", "a second service refuses while the first is active");

      // The real randomizer: native draw first (badtide chance 0 here), then one budget draw, then one weighted draw.
      Draws(random, false);
      Check(randomizer.GetRandomWeatherForCycle(1) == drought && Calls.Count == 1, "cycle 1 is never a tide");
      Draws(random, false, true, 10);
      var weather = randomizer.GetRandomWeatherForCycle(15);
      Check(weather is FluidTideWeather w && w.Definition.Id == "DeepFrontier.RadioactiveTide" && weather.Id == "RadioactiveTideWeather", "cycle 15 becomes the radioactive tide: " + weather?.Id);
      Check(Calls.SequenceEqual(new[] { "P(0)", "P(" + (25 / 100f).ToString("R") + ")", "R(0,40)" }), "draws: " + string.Join(" ", Calls));
      Draws(random, 4);
      Check(weather.GetDurationAtCycle(1) == 4 && Calls.SequenceEqual(new[] { "R(3,7)" }), "duration uniform over 3-6 days");
      Draws(random, false);
      Check(randomizer.GetRandomWeatherForCycle(16) == drought && Calls.Count == 1, "cooldown: cycle 16 keeps the native weather with no tide draw");
      Draws(random, false, true, 30);
      Check(randomizer.GetRandomWeatherForCycle(17) is FluidTideWeather c && c.Definition.Id == "MoreFluids.CoffeeTide", "cycle 17: weighted roll 30 picks coffee");
      Draws(random, false, false);
      Check(randomizer.GetRandomWeatherForCycle(19) == drought && Calls.Count == 2, "budget miss keeps the native weather");

      // Restore: native Load maps a saved tide to badtide (here: leaves what it has); the postfix puts the saved tide back.
      Draws(random, false, true, 5);
      var tide = randomizer.GetRandomWeatherForCycle(21);
      Internal(Native(), "SetCurrentWeather", null, weatherService, drought);
      weatherService.Load();
      Check(weatherService.CurrentCycleHazardousWeather == tide && service.IsCurrentCycleTide, "HazardousWeatherService.Load postfix restores the cycle's tide");

      // UI helper: the skipping prefix and the getters answer for the tide.
      var helper = new HazardousWeatherUIHelper(weatherService, null, null, null);
      Internal(typeof(HazardousWeatherUIHelper), "UpdateCurrentUISpecification", helper);
      string Get(string property) => (string)typeof(HazardousWeatherUIHelper).GetProperty(property).GetValue(helper);
      Check(Get("NameLocKey") == "DeepFrontier.Weather.RadioactiveTide" && Get("ApproachingLocKey") == "DeepFrontier.Weather.RadioactiveTideApproaching"
        && Get("IconClass") == "moddable-fluids-tide-date" && Get("NotificationBackgroundClass") == "moddable-fluids-tide-notification", "UI helper answers with the tide's texts and markers");
      // A caller compiled after the patch (as the game's panels are, in the Game scene) sees the patched getter.
      Check(DirectName(helper) == "DeepFrontier.Weather.RadioactiveTide", "a caller JIT-compiled after patching reads the patched getter");

      // Fog content check through the internal SunSpec.
      Internal(Content(), "RequireFog", null, new Specs(Sun(new[] { "DroughtWeather", "BadtideWeather", "RadioactiveTideWeather", "MoreFluids.CoffeeTide" }, night: null)), tides);
      Throws(() => Internal(Content(), "RequireFog", null, new Specs(Sun(new[] { "DroughtWeather", "BadtideWeather", "RadioactiveTideWeather", "MoreFluids.CoffeeTide" },
        night: new[] { "DroughtWeather", "BadtideWeather", "RadioactiveTideWeather" })), tides), "MoreFluids.CoffeeTide (MoreFluids.CoffeeTide) in NightColors", "missing night fog is named");

      // Scene unload removes every patch; the native randomizer is untouched afterwards.
      service.Unload();
      Check(CurrentService() == null && targets.All(t => Owners(t).Length == 0) && !service.PatchesInstalled, "unload removes every patch and the current service");
      Draws(random, false);
      Check(randomizer.GetRandomWeatherForCycle(30) == drought && Calls.Count == 1, "after unload the randomizer is native");

      // A foreign patch on a replaced target is refused, naming its owner, and nothing of ours stays installed.
      var foreign = new Harmony("Probe.ForeignTide");
      foreign.Patch((MethodInfo)Internal(Native(), "Randomizer", null), postfix: new HarmonyMethod(typeof(TidesMonoProbe), nameof(ForeignPostfix)));
      Throws(() => NewService(weatherService, history, random, scene, settings), "Probe.ForeignTide", "a foreign patch on the randomizer is refused");
      Check(CurrentService() == null && targets.All(t => !Owners(t).Contains(FluidTideService.OwnerId)), "a refused install leaves nothing behind");
      foreign.UnpatchAll("Probe.ForeignTide");

      // Scene 2 installs again cleanly.
      var second = NewService(weatherService, history, random, scene, settings);
      Check(targets.All(t => Owners(t).SequenceEqual(new[] { FluidTideService.OwnerId })), "the next scene installs again");
      second.Unload();
      Check(targets.All(t => Owners(t).Length == 0), "and removes again");

      // A loaded save without Moddable Fluids tide state: the importer is asked once, its state is restored by the native
      // Load postfix, and the next save writes Moddable Fluids' own singletons, so the import never repeats.
      var loaded = new SceneLoader(null);
      var legacy = new MemorySave();
      new ObjectSaver(legacy.Objects["Probe.LegacyTide"] = new SerializedObject()).Set(Importer.CycleKey, 21);
      Importer.Calls = 0;
      var importing = NewService(weatherService, history, random, loaded, settings, legacy);
      Internal(Native(), "SetCurrentWeather", null, weatherService, badtide);   // native Load maps IsDrought=false to badtide
      weatherService.Load();
      Check(Importer.Calls == 1 && importing.ImportedBy == "Probe.Importer" && weatherService.CurrentCycleHazardousWeather is FluidTideWeather imported
        && imported.Definition.Id == "DeepFrontier.RadioactiveTide" && importing.LastTideCycle == 21 && importing.LastTideDuration == 4, "the importer's tide is restored on load");
      Check(importing.Settings.BudgetPercent == 30 && importing.Settings.Get("DeepFrontier.RadioactiveTide").Weight == 30 && !importing.Settings.Get("MoreFluids.CoffeeTide").Enabled
        && Importer.Calls == 1, "imported settings, the unlisted tide off, asked once: " + importing.Settings);
      var written = new MemorySave();
      importing.Save(written);
      Check(written.Objects.ContainsKey("ModdableFluids.Tides") && written.Objects.ContainsKey("ModdableFluids.TideSettings"), "the next save writes both own singletons");
      importing.Unload();
      var reloaded = written.RoundTrip();
      reloaded.Objects.Add("Probe.LegacyTide", legacy.Objects["Probe.LegacyTide"]);   // even with the legacy key still present
      Internal(Native(), "SetCurrentWeather", null, weatherService, badtide);
      var again = NewService(weatherService, history, random, loaded, settings, reloaded);
      weatherService.Load();
      Check(Importer.Calls == 1 && again.ImportedBy == null && weatherService.CurrentCycleHazardousWeather is FluidTideWeather restored && restored.Definition.Id == "DeepFrontier.RadioactiveTide"
        && again.LastTideCycle == 21 && again.Settings.BudgetPercent == 30 && again.SettingsSource == FluidTideSettingsStore.SavedSource, "after a save the import is not repeated");
      again.Unload();
      var nothing = NewService(weatherService, history, random, loaded, settings, new MemorySave());
      Check(nothing.Settings.Tides.All(t => !t.Enabled) && Importer.Calls == 2 && nothing.ImportedBy == null, "a loaded save the importer has nothing for: every tide off");
      nothing.Unload();
      var half = new MemorySave();
      half.Objects.Add("ModdableFluids.Tides", written.Objects["ModdableFluids.Tides"]);
      var broken = NewService(weatherService, history, random, loaded, settings, half);
      Throws(() => _ = broken.Settings, "every save writes both", "a save with only one of the two tide singletons is refused");
      broken.Unload();
      Check(targets.All(t => Owners(t).Length == 0), "the import scenes leave no patch behind");

      // Main menu: the new-game patch installs with its contract check and uninstalls on unload.
      var newGame = new FluidTideNewGameSettings(null, null, null, null, null);
      var customTarget = (MethodInfo)Internal(Native(), "CustomTryGetValidatedGameMode", null);
      Check(Owners(customTarget).SequenceEqual(new[] { FluidTideNewGameSettings.OwnerId }), "new-game patch installed");
      Throws(() => new FluidTideNewGameSettings(null, null, null, null, null), "already active", "a second new-game screen refuses");
      newGame.Unload();
      Check(Owners(customTarget).Length == 0, "new-game patch removed on unload");
      Check(typeof(NewGameModePanel).Assembly.GetName().Name == "Timberborn.MainMenuPanels", "native main menu assembly");
      return "PASS " + checks + " tide checks in Mono " + Environment.Version + " against " + managed;
    }

    // The service logs its settings only in Load, which the probe never calls: no engine call in this process.
    private static FluidTideService NewService(HazardousWeatherService weatherService, HazardousWeatherHistory history, IRandomNumberGenerator random, ISceneLoader scene,
        FluidTideSaveSettings settings, ISingletonLoader singletons = null) {
      var service = new FluidTideService(singletons ?? new EmptyLoader(), scene, null, weatherService, history, null, null, random, null, null, null, null);
      if (singletons == null && service.Settings.ToString() != settings.ToString()) throw new InvalidOperationException("Tide probe: the new game's settings changed: " + service.Settings);
      return service;
    }

    /// <summary>A compiled importer reading its own legacy singleton from the save's native singleton loader.</summary>
    private sealed class Importer : IFluidProvider, IFluidTideImporter {
      internal static int Calls;
      internal static readonly SingletonKey LegacyKey = new SingletonKey("Probe.LegacyTide");
      internal static readonly PropertyKey<int> CycleKey = new PropertyKey<int>("Cycle");
      public string ProviderId => "Probe.Importer";
      public string OwnerModId => "Probe";
      public string MinimumApiVersion => "0.1.3";
      public IReadOnlyCollection<string> RequiredCapabilities => new[] { FluidTideRules.ImportCapability };
      public void Register(FluidRegistration registration) { }
      public FluidTideImport ImportTides(FluidTideImportContext context) {
        Calls++;
        if (!((ISingletonLoader)context.NativeSingletonLoader).TryGetSingleton(LegacyKey, out var legacy)) return null;
        int cycle = legacy.Get(CycleKey);
        return new FluidTideImport("DeepFrontier.RadioactiveTide", cycle, "DeepFrontier.RadioactiveTide", 4, 30,
          new[] { new FluidTideSettings("DeepFrontier.RadioactiveTide", true, 30, 5, 3, 6) });
      }
    }

    /// <summary>Singletons kept as the game keeps them: SerializedObjects behind the native ObjectSaver and ObjectLoader.</summary>
    private sealed class MemorySave : ISingletonLoader, ISingletonSaver {
      internal readonly Dictionary<string, SerializedObject> Objects = new Dictionary<string, SerializedObject>(StringComparer.Ordinal);
      public IObjectLoader GetSingleton(SingletonKey key) => throw new NotSupportedException();
      public bool TryGetSingleton(SingletonKey key, out IObjectLoader objectLoader) {
        objectLoader = Objects.TryGetValue(key.Name, out var data) ? new ObjectLoader(data) : null;
        return objectLoader != null;
      }
      IObjectSaver ISingletonSaver.GetSingleton(SingletonKey key) {
        if (!Objects.TryGetValue(key.Name, out var data)) Objects.Add(key.Name, data = new SerializedObject());
        return new ObjectSaver(data);
      }
      // Through the game's JSON writer and reader, as a save file is.
      internal MemorySave RoundTrip() {
        var json = new SerializedObjectReaderWriter(new JsonMerger());
        var copy = new MemorySave();
        foreach (var pair in Objects) copy.Objects.Add(pair.Key, json.ReadJson(json.WriteJson(pair.Value)));
        return copy;
      }
    }

    private static void ForeignPostfix() { }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static string DirectName(HazardousWeatherUIHelper helper) => helper.NameLocKey;

    private static void Draws(ScriptedRandom random, params object[] script) {
      Calls.Clear(); Script.Clear();
      foreach (var item in script) Script.Enqueue(item);
    }

    private static GameModeSpec Mode(int tMin, int tMax, int dMin, int dMax, int bMin, int bMax, float chance) => new GameModeSpec {
      TemperateWeatherDuration = new MinMaxSpec<int> { Min = tMin, Max = tMax }, DroughtDuration = new MinMaxSpec<int> { Min = dMin, Max = dMax },
      BadtideDuration = new MinMaxSpec<int> { Min = bMin, Max = bMax }, ChanceForBadtide = chance,
    };

    // An internal SunSpec whose four day stages list these fog weather IDs (night may differ).
    private static object Sun(string[] ids, string[] night) {
      var assembly = Assembly.Load("Timberborn.SkySystem");
      Type T(string name) => assembly.GetType("Timberborn.SkySystem." + name, true);
      object New(Type type) => Activator.CreateInstance(type, true);
      void Set(object target, string property, object value) => target.GetType().GetProperty(property, Any).SetValue(target, value);
      object Colors(string[] fogIds) {
        var fogType = T("HazardousWeatherFogSettingsSpec");
        var array = Array.CreateInstance(fogType, fogIds.Length);
        for (int i = 0; i < fogIds.Length; i++) { var fog = New(fogType); Set(fog, "HazardousWeatherId", fogIds[i]); array.SetValue(fog, i); }
        var create = typeof(ImmutableArray).GetMethods().Single(m => m.Name == "Create" && m.IsGenericMethodDefinition && m.GetParameters().Length == 1 && m.GetParameters()[0].ParameterType.IsArray);
        var colors = New(T("DayStageColorsSpec"));
        Set(colors, "HazardousWeatherFogs", create.MakeGenericMethod(fogType).Invoke(null, new object[] { array }));
        return colors;
      }
      var sun = New(T("SunSpec"));
      Set(sun, "SunriseColors", Colors(ids)); Set(sun, "DayColors", Colors(ids)); Set(sun, "SunsetColors", Colors(ids)); Set(sun, "NightColors", Colors(night ?? ids));
      return sun;
    }

    private sealed class Specs : ISpecService {
      private readonly object _sun;
      public Specs(object sun) { _sun = sun; }
      public Blueprint GetBlueprint(string blueprintPath) => throw new NotSupportedException();
      public T GetSingleSpec<T>() where T : ComponentSpec => (T)_sun;
      public IEnumerable<T> GetSpecs<T>() where T : ComponentSpec => throw new NotSupportedException();
    }

    private sealed class Provider : IFluidProvider {
      private readonly string _fluid, _tide, _weather;
      private readonly double _strength;
      private readonly (int, int, int, int)[] _modes;
      public string ProviderId { get; }
      public string OwnerModId { get; }
      public string MinimumApiVersion => "0.1.3";
      public IReadOnlyCollection<string> RequiredCapabilities => new[] { FluidTideRules.RegistrationCapability };
      public Provider(string id, string owner, string fluid, string tide, string weather, double strength, (int, int, int, int)[] modes) {
        ProviderId = id; OwnerModId = owner; _fluid = fluid; _tide = tide; _weather = weather; _strength = strength; _modes = modes;
      }
      public void Register(FluidRegistration r) {
        r.AddFluid(_fluid, OwnerModId + "." + _fluid, .5f, .5f, .5f, 1f);
        string p = OwnerModId + ".Weather." + _tide;
        r.AddTide(_tide, _weather, p, p + "Description");
        for (int i = 0; i < 3; i++) r.SetTideMode(_tide, FluidTideRules.Modes[i], _modes[i].Item1, _modes[i].Item2, _modes[i].Item3, _modes[i].Item4);
        r.SetTideSourceEmission(_tide, OwnerModId + "." + _fluid, 1.0);
        if (_strength != 1) r.SetTideSourceStrength(_tide, _strength);
        r.SetTideTexts(_tide, p + "Approaching", p + "InProgress", p + "Started", p + "Ended", p + "ApproachingDescription", p + "StartedDescription");
        r.SetTideArt(_tide, "i", "p", "n");
        r.SetTideStartSound(_tide, "Badtide");
      }
    }

    private sealed class ScriptedRandom : IRandomNumberGenerator {
      public bool CheckProbability(float normalizedProbability) { Calls.Add("P(" + normalizedProbability.ToString("R") + ")"); return (bool)Script.Dequeue(); }
      public int Range(int inclusiveMin, int exclusiveMax) { Calls.Add("R(" + inclusiveMin + "," + exclusiveMax + ")"); return (int)Script.Dequeue(); }
      public float Range(float inclusiveMin, float inclusiveMax) => throw new NotSupportedException();
      public Vector2 InsideUnitCircle() => throw new NotSupportedException();
      public T GetListElement<T>(IReadOnlyList<T> list) => throw new NotSupportedException();
      public bool TryGetListElement<T>(IReadOnlyList<T> list, out T randomElement) => throw new NotSupportedException();
      public T GetListElementOrDefault<T>(IReadOnlyList<T> list) => throw new NotSupportedException();
      public T GetEnumerableElement<T>(IEnumerable<T> source) => throw new NotSupportedException();
      public bool TryGetEnumerableElement<T>(IEnumerable<T> source, out T randomElement) => throw new NotSupportedException();
    }

    private sealed class EmptyLoader : ISingletonLoader {
      public Timberborn.Persistence.IObjectLoader GetSingleton(SingletonKey key) => throw new NotSupportedException();
      public bool TryGetSingleton(SingletonKey key, out Timberborn.Persistence.IObjectLoader objectLoader) { objectLoader = null; return false; }
    }

    private sealed class SceneLoader : ISceneLoader {
      private readonly ISceneParameters _parameters;
      public SceneLoader(ISceneParameters parameters) { _parameters = parameters; }
      public long LastLoadTimeMs => 0;
      public void LoadScene(ISceneParameters sceneParameters, string tip) => throw new NotSupportedException();
      public void LoadSceneInstantly(ISceneParameters sceneParameters, string tip) => throw new NotSupportedException();
      public void LoadSceneInstantly(ISceneParameters sceneParameters) => throw new NotSupportedException();
      public bool HasAnySceneParameters() => _parameters != null;
      public bool TryGetSceneParameters<T>(out T sceneParameters) where T : ISceneParameters {
        if (_parameters is T match) { sceneParameters = match; return true; }
        sceneParameters = default; return false;
      }
      public T GetSceneParameters<T>() where T : ISceneParameters => throw new NotSupportedException();
    }
  }
}
