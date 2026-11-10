using System;
using System.Collections.Frozen;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using System.Reflection;
using Bindito.Core;
using HarmonyLib;
using ModdableFluids.Tides.Prototype;
using ModdableWeathers.Historical;
using ModdableWeathers.Weathers;
using ModdableWeathers.Weathers.GameBuiltIns;
using Timberborn.AutomationBuildings;
using Timberborn.BlueprintSystem;
using Timberborn.Common;
using Timberborn.GameCycleSystem;
using Timberborn.GameSceneLoading;
using Timberborn.HazardousWeatherSystem;
using Timberborn.MapStateSystem;
using Timberborn.NewGameConfigurationSystem;
using Timberborn.Persistence;
using Timberborn.SceneLoading;
using Timberborn.SerializationSystem;
using Timberborn.TimeSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace ModdableFluids.Tides.ModdableWeathersAdapter.Acceptance {
  /// <summary>
  /// The Moddable Weathers adapter against the installed Moddable Weathers 11.0.0 (with Moddable Timberborn and TimberUi
  /// from the Workshop) and the installed game, in the game's Mono: the contract check, the real ModdableWeatherBase
  /// lifecycle of the tide weathers, Moddable Weathers' real registry and history, the stage weights as
  /// WeatherGenerator.DecideWeather asks them (cooldown, one tide per cycle, a recursing weather and an overflowing roll
  /// refused), durations, the source effect following Active, the Weather Station by weather ID, saving the native
  /// binding's state from Moddable Weathers' history and refusing a disagreeing one, and per-scene install and uninstall
  /// of the station patches. WeatherGenerator itself draws with UnityEngine.Random (an engine call), so its loop is
  /// mirrored here, not run. No engine call: nothing here logs through UnityEngine.
  /// </summary>
  public static class ModdableWeathersMonoProbe {
    private const BindingFlags Any = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;
    private const string Radioactive = "DeepFrontier.RadioactiveTide", Coffee = "MoreFluids.CoffeeTide", Salt = "MoreFluids.SaltTide";
    private const string RadioactiveWeather = "RadioactiveTideWeather", CoffeeWeather = "MoreFluidsCoffeeTideWeather", SaltWeather = "MoreFluidsSaltTideWeather";

    public static string Run(string managed) {
      int checks = 0;
      void Check(bool condition, string name) { checks++; if (!condition) throw new InvalidOperationException("Moddable Weathers probe: " + name); }
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
      void SetProperty(Type type, string name, object target, object value) => type.GetProperty(name, Any).GetSetMethod(true).Invoke(target, new[] { value });
      string[] Owners(MethodBase method) => Harmony.GetPatchInfo(method)?.Owners.Distinct().ToArray() ?? new string[0];

      // The main assemblies never reference Moddable Weathers; the adapter does.
      var workshop = new[] { "ModdableWeathers", "ModdableTimberborn", "TimberUi" };
      foreach (var main in new[] { typeof(ModdableFluidsEntry).Assembly, typeof(FluidTideService).Assembly, Assembly.Load("ModdableFluids.TransportPrototype"), Assembly.Load("ModdableFluids.GamePrototype") })
        Check(!main.GetReferencedAssemblies().Any(r => workshop.Contains(r.Name)), main.GetName().Name + " references no Workshop assembly");
      Check(typeof(FluidTideModdableWeather).Assembly.GetReferencedAssemblies().Any(r => r.Name == "ModdableWeathers"), "the adapter references Moddable Weathers");

      // The contract, against the installed Moddable Weathers.
      var mw = FluidTideModdableWeathersContract.Verify();
      Check(mw.GetName().Name == "ModdableWeathers" && FluidTideModdableWeathersContract.InstalledVersion(mw).StartsWith("11.0.0 at "), "contract verified against " + FluidTideModdableWeathersContract.InstalledVersion(mw));
      var configuratorChecks = typeof(FluidTideService).Assembly.GetType("ModdableFluids.Tides.Prototype.FluidTideModdableWeathers", true);
      Check((bool)configuratorChecks.GetProperty("Loaded", Any).GetValue(null), "the main configurator sees Moddable Weathers loaded");
      Internal(configuratorChecks, "RequireAdapter", null, (object)null);

      // Three tides as Deep Frontier and More Fluids register them (Normal: 25/14, 15/8, 15/7).
      var host = ModdableFluidsEntry.Host;
      host.RegisterProvider(new Provider("DeepFrontier.Radiation", "DeepFrontier", "RadioactiveWater", "RadioactiveTide", RadioactiveWeather, new[] { (15, 24, 2, 4), (25, 14, 3, 6), (35, 9, 5, 10) }));
      host.RegisterProvider(new Provider("MoreFluids.Liquids", "MoreFluids", "Coffee", "CoffeeTide", CoffeeWeather, new[] { (10, 12, 2, 4), (15, 8, 3, 5), (20, 6, 4, 7) }, "Saltwater", "SaltTide", SaltWeather,
        new[] { (10, 10, 2, 4), (15, 7, 4, 8), (20, 5, 10, 20) }));
      host.Freeze();
      var tides = host.Tides;
      Check(tides.Tides.Select(t => t.Id).SequenceEqual(new[] { Radioactive, Coffee, Salt }), "three tides in ordinal order");

      // Moddable Weathers' spec service, with the specs the content mods ship (ModdableWeatherSpecs/<weather ID>).
      ModdableWeatherSpec Spec(string id, int order, string display) => new ModdableWeatherSpec { Id = id, Order = order, DisplayLoc = display };
      var allSpecs = new[] { Spec("TemperateWeather", 10, "Weather.Temperate"), Spec("DroughtWeather", 20, "Weather.Drought"), Spec("BadtideWeather", 30, "Weather.Badtide"),
        Spec("EmptyBenignWeather", -1, "x"), Spec("EmptyHazardousWeather", -1, "x"), Spec("Probe.Other", 25, "Probe.Other"),
        Spec(RadioactiveWeather, 35, "DeepFrontier.Weather.RadioactiveTide"), Spec(CoffeeWeather, 36, "MoreFluids.Weather.CoffeeTide"), Spec(SaltWeather, 37, "MoreFluids.Weather.SaltTide") };
      var specs = new ModdableWeatherSpecService(null, null);
      SetProperty(typeof(ModdableWeatherSpecService), "SpecsById", specs, allSpecs.ToFrozenDictionary(s => s.Id));

      // The native services the adapter reads: the hazardous weather service (Moddable Weathers replaces its getter in game;
      // here its native private setter stands in), the cycle, the random generator, a new Normal game.
      var random = new ScriptedRandom();
      var mapMode = MapEditorMode.NonMapEditorInstance();
      var drought = new DroughtWeather(null, random, mapMode, null);
      var badtide = new BadtideWeather(null, random, mapMode, null, null);
      var nativeHistory = new HazardousWeatherHistory(null, null, null);
      var hazardous = new HazardousWeatherService(null, new EmptyLoader(), mapMode, drought, badtide, new HazardousWeatherRandomizer(drought, badtide, nativeHistory, random), nativeHistory);
      void SetCurrent(IHazardousWeather weather) => SetProperty(typeof(HazardousWeatherService), "CurrentCycleHazardousWeather", hazardous, weather);
      var cycles = new GameCycleService(null, new EmptyLoader(), null, mapMode, new ICycleDuration[0]);
      void SetCycle(int cycle) => SetProperty(typeof(GameCycleService), "Cycle", cycles, cycle);
      var normal = new Blueprint("GameMode.Normal", new ComponentSpec[] { new GameModeSpec {
        TemperateWeatherDuration = new MinMaxSpec<int> { Min = 13, Max = 17 }, DroughtDuration = new MinMaxSpec<int> { Min = 5, Max = 9 },
        BadtideDuration = new MinMaxSpec<int> { Min = 4, Max = 8 }, ChanceForBadtide = .4f } }, ImmutableArray<Blueprint>.Empty).GetSpec<GameModeSpec>();
      var newGame = new SceneLoader(GameSceneParameters.CreateNewGameParameters(new NewGameConfiguration("Folktails", default(Timberborn.MapRepositorySystem.MapFileReference), normal, "Probe")));
      var container = Services(new Container(), hazardous, cycles);
      // Under Moddable Weathers the hazardous weather service and the cycle service are constructed from its registry, and
      // the registry from the tide weathers, which are constructed from the adapter: the adapter resolves them lazily.
      var forbidden = new[] { typeof(HazardousWeatherService), typeof(GameCycleService) };
      Check(typeof(FluidTideModdableWeathersService).GetConstructors().Single().GetParameters().All(a => !forbidden.Contains(a.ParameterType) && a.ParameterType.Assembly != mw),
        "the adapter's constructor takes nothing that Moddable Weathers constructs from its registry");

      // ---- Scene 1: a new game.
      var service = new FluidTideModdableWeathersService(new EmptyLoader(), newGame, null, random, null, container);
      var stationTargets = (MethodInfo[])Internal(typeof(FluidTideService).Assembly.GetType("ModdableFluids.Tides.Prototype.FluidTideNative", true), "VerifyStationGame", null);
      Check(stationTargets.Length == 4 && stationTargets.All(t => Owners(t).SequenceEqual(new[] { FluidTideService.OwnerId })) && service.StationPatchesInstalled,
        "the four Weather Station targets patched by ModdableFluids.Tides only");
      var nativeTargets = new MethodBase[] { typeof(HazardousWeatherRandomizer).GetMethod("GetRandomWeatherForCycle"), typeof(HazardousWeatherService).GetMethod("Load") };
      Check(nativeTargets.All(t => !Owners(t).Contains(FluidTideService.OwnerId)), "no native weather method is patched");
      Check(FluidTideScenes.Current == service, "the adapter is the scene's tide owner");
      Throws(() => new FluidTideModdableWeathersService(new EmptyLoader(), newGame, null, random, null, container), "already active", "a second owner is refused while the first is active");
      Check(service.Settings.BudgetPercent == 25 && service.Settings.Get(Coffee).Weight == 15 && service.Data.NewGame, "a new Normal game's tide settings: " + service.Settings);

      // The tide weathers: one class per tide, each taking its tide by position.
      var tide0 = new FluidTideWeather0(specs, service);
      var tide1 = new FluidTideWeather1(specs, service);
      Throws(() => Internal(typeof(FluidTideModdableWeathersService), "RequireWeathers", service), Salt, "a tide without its weather is named");
      var tide2 = new FluidTideWeather2(specs, service);
      Throws(() => new FluidTideWeather3(specs, service), "was bound for 3 registered tides", "a class beyond the registered tides is refused");
      Internal(typeof(FluidTideModdableWeathersService), "RequireWeathers", service);
      Check(tide0.Tide.Id == Radioactive && tide1.Id == CoffeeWeather && ((IHazardousWeather)tide2).Id == SaltWeather && tide2 is IModdableHazardousWeather, "weather IDs are the tides' native weather IDs");
      foreach (var weather in new FluidTideModdableWeather[] { tide0, tide1, tide2 }) weather.Load();
      Check(tide1.Spec.Id == CoffeeWeather && tide1.Enabled && !tide1.Active, "Moddable Weathers' base Load reads each tide's spec");

      // Moddable Weathers' own weathers, registry and history.
      var temperate = new GameTemperateWeather(specs, null);
      var mwDrought = new GameDroughtWeather(specs, null);
      var mwBadtide = new GameBadtideWeather(specs, null);
      SetProperty(typeof(ModdableWeatherBase), "Spec", temperate, allSpecs[0]); SetProperty(typeof(ModdableWeatherBase), "Spec", mwDrought, allSpecs[1]); SetProperty(typeof(ModdableWeatherBase), "Spec", mwBadtide, allSpecs[2]);
      SetProperty(mwDrought.GetType().BaseType, "Settings", mwDrought, new GameDroughtWeatherSettings { Enabled = true, StartCycle = 0, Chance = 60 });
      SetProperty(mwBadtide.GetType().BaseType, "Settings", mwBadtide, new GameBadtideWeatherSettings { Enabled = true, StartCycle = 0, Chance = 40 });
      var other = new ProbeWeather(specs);
      SetProperty(typeof(ModdableWeatherBase), "Spec", other, allSpecs[5]);
      var emptyBenign = new EmptyBenignWeather(specs);
      var emptyHazardous = new EmptyHazardousWeather(specs);
      var registry = new ModdableWeatherRegistry(new IModdableWeather[] { temperate, tide2, mwDrought, tide0, mwBadtide, other, tide1 }, emptyBenign, emptyHazardous, temperate, mwDrought, mwBadtide);
      registry.Load();
      Check(registry.HazardousWeathers.Select(w => ((IModdableWeather)w).Id).SequenceEqual(new[] { "DroughtWeather", "Probe.Other", "BadtideWeather", RadioactiveWeather, CoffeeWeather, SaltWeather }),
        "the registry lists the tides among the hazardous weathers by spec order");
      var history = new WeatherHistoryRegistry(new EmptyLoader(), null, null);
      history.WeatherCycleAdded += (cycle, current) => { };
      var historyService = new WeatherHistoryService(history, registry, null);
      container.Add(registry); container.Add(history); container.Add(historyService);
      WeatherCycle Cycle(int cycle, string hazardousWeather, int days) => new WeatherCycle(cycle, ImmutableArray.Create(
        new WeatherCycleStage(0, true, "TemperateWeather", ImmutableArray<string>.Empty, 12), new WeatherCycleStage(1, false, hazardousWeather, ImmutableArray<string>.Empty, days)));
      for (int c = 1; c <= 14; c++) history.AddWeatherCycles(Cycle(c, c == 6 ? CoffeeWeather : "DroughtWeather", 5), c);

      // WeatherGenerator.DecideWeather's loop: every enabled hazardous weather's GetChance for one stage, in registry order.
      int[] Decide(WeatherCycleStageDecision stage, WeatherCycleDecision decision) =>
        registry.HazardousWeathers.Select(w => w.Enabled ? w.GetChance(stage, decision, historyService) : 0).ToArray();
      (WeatherCycleStageDecision, WeatherCycleDecision) Stage(int cycle, params IModdableWeather[] earlier) {
        var stages = earlier.Select((w, i) => new WeatherCycleStageDecision { Cycle = cycle, StageIndex = i, IsBenign = false, Weather = w, DaysMultiplier = 100 }).ToList();
        var stage = new WeatherCycleStageDecision { Cycle = cycle, StageIndex = stages.Count, IsBenign = false, DaysMultiplier = 100 };
        stages.Add(stage);
        return (stage, new WeatherCycleDecision { Cycle = cycle, Stages = stages.ToImmutableArray() });
      }
      string W(int[] weights) => "[" + string.Join(", ", weights) + "]";

      // Cycle 15 (every tide eligible): drought 60, other 0, badtide 40, and the tides' integer split of K = 33.
      ProbeWeather.Calls = 0;
      var (s15, d15) = Stage(15);
      var weights = Decide(s15, d15);
      Check(weights.SequenceEqual(new[] { 60, 0, 40, 15, 9, 9 }), "cycle 15 weights " + W(weights));
      Check(weights.Skip(3).SequenceEqual(FluidTideSelection.StageWeights(15, 6, service.Settings, null, 100)), "the tides' weights are StageWeights of the other weathers' sum");
      Check(ProbeWeather.Calls == 2, "the other weathers are weighed once by Moddable Weathers and once for all tides together: " + ProbeWeather.Calls);
      Check(Decide(s15, d15).SequenceEqual(weights) && ProbeWeather.Calls == 3, "a stage asked again reuses the tides' weights");
      var (s9, d9) = Stage(9);
      Check(Decide(s9, d9).SequenceEqual(new[] { 60, 0, 40, 0, 8, 8 }), "cycle 9: coffee and salt only");
      var (s7, d7) = Stage(7);
      Check(Decide(s7, d7).SequenceEqual(new[] { 60, 0, 40, 0, 0, 0 }), "cycle 7: no tide is eligible after coffee in cycle 6 (cooldown) and before its cycles without");
      history.AddWeatherCycles(Cycle(15, SaltWeather, 6), 15);
      var (s16, d16) = Stage(16);
      Check(Decide(s16, d16).SequenceEqual(new[] { 60, 0, 40, 0, 0, 0 }), "cycle 16: the global cooldown after the salt tide in cycle 15");
      var (later, sameCycle) = Stage(17, tide1);
      Check(Decide(later, sameCycle).SequenceEqual(new[] { 60, 0, 40, 0, 0, 0 }), "a second hazardous stage of a cycle with a tide gets none");
      var (s17, d17) = Stage(17, mwDrought);
      Check(Decide(s17, d17).SequenceEqual(new[] { 60, 0, 40, 15, 9, 9 }), "a second hazardous stage after a drought stage is weighed as the first");
      Throws(() => tide0.GetChance(new WeatherCycleStageDecision { Cycle = 17, StageIndex = 0, IsBenign = true }, d17, historyService), "benign stage", "a benign stage is refused");
      ProbeWeather.Weight = 7;
      var (s18, d18) = Stage(18);
      Check(Decide(s18, d18).SequenceEqual(new[] { 60, 7, 40, 16, 10, 10 }), "another hazardous weather's weight enters O (107 -> K 36)");
      ProbeWeather.Weight = int.MaxValue - 200;
      var (s19, d19) = Stage(19);
      Throws(() => Decide(s19, d19), "exceed Moddable Weathers' integer roll", "weights beyond Moddable Weathers' integer roll are refused");
      ProbeWeather.Weight = 0;
      ProbeWeather.Recurse = tide0;
      var (s20, d20) = Stage(20);
      Throws(() => Decide(s20, d20), "beside Moddable Weathers' hazardous weather Probe.Other", "a weather that weighs itself against the tides is refused, named");
      ProbeWeather.Recurse = null;

      // Durations: uniform whole days over the save's settings (coffee 3-5 on Normal).
      Draws(random, 4);
      Check(tide1.GetDuration(s15, d15, historyService) == 4 && Calls.SequenceEqual(new[] { "R(3,6)" }), "coffee lasts 3-5 days: " + string.Join(" ", Calls));

      // Source effect follows Active; the station's cycle tide follows the hazardous weather service by weather ID.
      Check(service.EmittingTide == null, "no tide in progress");
      tide1.Start(default(DetailedWeatherStageReference), false);
      Check(service.EmittingTide?.Id == Coffee, "an Active coffee weather emits coffee");
      tide2.Start(default(DetailedWeatherStageReference), true);
      Throws(() => _ = service.EmittingTide, "two tides active", "two active tides are refused");
      tide2.End(); tide1.End();
      Check(service.EmittingTide == null && !tide1.Active, "End stops the emission");
      SetCurrent(tide2);
      Check(service.CurrentCycleTide?.Id == Salt, "the cycle's hazardous weather is recognised as the salt tide by its weather ID");
      SetCurrent(drought);
      Check(service.CurrentCycleTide == null, "a drought is no tide");
      var station = new FluidTideWeatherStation(service);
      var stationEntity = new MemoryEntity();
      new ObjectSaver(stationEntity.Objects["ModdableFluids.WeatherStationTide"] = new SerializedObject()).Set(new PropertyKey<string>("Tide"), Salt);
      station.Load(stationEntity);
      SetCurrent(tide2);
      Internal(typeof(FluidTideWeatherStation), "Sample", station, service.CurrentCycleTide?.Id);
      Check(station.SignalledTide == Salt && (bool)Internal(typeof(FluidTideWeatherStation), "Output", station, true), "a station in salt mode signals during the salt tide");
      SetCurrent(tide1);
      Internal(typeof(FluidTideWeatherStation), "Sample", station, service.CurrentCycleTide?.Id);
      Check(!(bool)Internal(typeof(FluidTideWeatherStation), "Output", station, true), "and not during coffee");

      // Saving: the native binding's state, derived from Moddable Weathers' history (cycle 15: salt for 6 days, in progress).
      SetCycle(15); SetCurrent(tide2);
      var save = Weather(new MemorySave());
      service.Save(save);
      Check(service.Data.CurrentCycleTide == Salt && service.Data.LastTideCycle == 15 && service.Data.LastTideId == Salt && service.Data.LastTideDuration == 6,
        "the saved state is the history's: " + service.Data.DescribeState());
      Check(save.Objects.ContainsKey("ModdableFluids.Tides") && save.Objects.ContainsKey("ModdableFluids.TideSettings"), "both tide singletons are written");
      service.Unload();
      Check(stationTargets.All(t => Owners(t).Length == 0) && FluidTideScenes.Current == null && !service.StationPatchesInstalled, "unload removes the station patches and the owner");

      // ---- Scene 2: the save loads; its state agrees with the history, and the load-time dry run weighs cycle 16.
      var loaded = new SceneLoader(null);
      var reloaded = Scene(save.RoundTrip(), loaded, random, container, specs);
      Check(reloaded.Data.HadState && reloaded.Data.LastTideId == Salt && reloaded.Settings.BudgetPercent == 25 && reloaded.Data.SettingsSource == FluidTideSettingsStore.SavedSource, "the save's state and settings load");
      reloaded.PostLoad();
      Check(stationTargets.All(t => Owners(t).SequenceEqual(new[] { FluidTideService.OwnerId })), "the next scene installs the station patches again");
      reloaded.Unload();

      // A state written by the native binding, played on under Moddable Weathers (its history converted from the native one).
      var native = Weather(new MemorySave());
      var nativeData = new FluidTideSaveData(tides, new EmptyLoader(), newGame, null);
      nativeData.RecordSelection(15, Salt); nativeData.RecordDuration(6);
      nativeData.Save(native);
      var fromNative = Scene(native.RoundTrip(), loaded, random, container, specs);
      fromNative.PostLoad();
      fromNative.Unload();
      // A state that disagrees with the history is another tide system's work.
      var wrong = new FluidTideSaveData(tides, new EmptyLoader(), newGame, null);
      wrong.RecordSelection(15, Salt); wrong.RecordDuration(5);
      var wrongSave = Weather(new MemorySave());
      wrong.Save(wrongSave);
      var disagreeing = Scene(wrongSave.RoundTrip(), loaded, random, container, specs);
      Throws(() => disagreeing.PostLoad(), "disagrees with Moddable Weathers' weather history", "a state that disagrees with the history is refused");
      disagreeing.Unload();
      // A loaded save without tide state whose history holds a tide was played with another tide system.
      var foreign = Scene(Weather(new MemorySave()), loaded, random, container, specs);
      Throws(() => foreign.PostLoad(), "played with another tide system", "a history with tides but no tide state is refused");
      foreign.Unload();
      Check(stationTargets.All(t => Owners(t).Length == 0) && FluidTideScenes.Current == null, "every scene left nothing behind");

      // The specs a tide needs: a missing one and a mismatched name are named.
      SetProperty(typeof(ModdableWeatherSpecService), "SpecsById", specs, allSpecs.Where(s => s.Id != SaltWeather).ToFrozenDictionary(s => s.Id));
      var check = new FluidTideModdableWeathersService(new EmptyLoader(), newGame, null, random, null, Services(new Container(), hazardous, cycles));
      new FluidTideWeather0(specs, check); new FluidTideWeather1(specs, check);
      Throws(() => new FluidTideWeather2(specs, check).Load(), "ModdableWeatherSpecs/" + SaltWeather + ".blueprint.json", "a tide without its Moddable Weathers spec is named");
      check.Unload();
      SetProperty(typeof(ModdableWeatherSpecService), "SpecsById", specs, allSpecs.Select(s => s.Id == SaltWeather ? Spec(SaltWeather, 37, "Other.Name") : s).ToFrozenDictionary(s => s.Id));
      check = new FluidTideModdableWeathersService(new EmptyLoader(), newGame, null, random, null, Services(new Container(), hazardous, cycles));
      new FluidTideWeather0(specs, check); new FluidTideWeather1(specs, check);
      Throws(() => new FluidTideWeather2(specs, check).Load(), "Other.Name", "a spec naming another weather is refused");
      check.Unload();
      return "PASS " + checks + " Moddable Weathers adapter checks in Mono " + Environment.Version + " against " + managed + " and Moddable Weathers " + FluidTideModdableWeathersContract.InstalledVersion(mw);
    }

    private static Container Services(Container container, HazardousWeatherService hazardous, GameCycleService cycles) {
      container.Add(hazardous); container.Add(cycles);
      return container;
    }

    private static FluidTideModdableWeathersService Scene(MemorySave save, ISceneLoader scene, IRandomNumberGenerator random, Container container, ModdableWeatherSpecService specs) {
      var service = new FluidTideModdableWeathersService(save, scene, null, random, null, container);
      var weathers = new FluidTideModdableWeather[] { new FluidTideWeather0(specs, service), new FluidTideWeather1(specs, service), new FluidTideWeather2(specs, service) };
      // The container's registry keeps the first scene's weathers; this scene's replace them by ID.
      var registry = container.Get<ModdableWeatherRegistry>();
      var listed = registry.Weathers.Select(w => weathers.FirstOrDefault(t => t.Id == w.Id) ?? w).ToArray();
      foreach (var weather in weathers) weather.Load();
      var fresh = new ModdableWeatherRegistry(listed, registry.EmptyBenignWeather, registry.EmptyHazardousWeather, registry.GameTemperateWeather, registry.GameDroughtWeather, registry.GameBadtideWeather);
      fresh.Load();
      container.Add(fresh);
      var history = container.Get<WeatherHistoryRegistry>();
      container.Add(new WeatherHistoryService(history, fresh, null));
      return service;
    }

    // The native weather singletons every save keeps (vanilla Normal), for a loaded save's tide defaults.
    private static MemorySave Weather(MemorySave save) {
      var t = new ObjectSaver(save.Objects["TemperateWeatherDurationService"] = new SerializedObject());
      t.Set(new PropertyKey<int>("MinTemperateWeatherDuration"), 13); t.Set(new PropertyKey<int>("MaxTemperateWeatherDuration"), 17);
      var d = new ObjectSaver(save.Objects["DroughtWeather"] = new SerializedObject());
      d.Set(new PropertyKey<int>("MinDroughtDuration"), 5); d.Set(new PropertyKey<int>("MaxDroughtDuration"), 9);
      var b = new ObjectSaver(save.Objects["BadtideWeather"] = new SerializedObject());
      b.Set(new PropertyKey<int>("MinBadtideWeatherDuration"), 4); b.Set(new PropertyKey<int>("MaxBadtideWeatherDuration"), 8);
      b.Set(new PropertyKey<float>("ChanceBadtideWeather"), .4f);
      return save;
    }

    /// <summary>Another mod's hazardous weather: a fixed weight, counting its weighings; it can weigh itself against a tide.</summary>
    private sealed class ProbeWeather : ModdableWeatherBase, IModdableHazardousWeather {
      internal static int Calls, Weight;
      internal static IModdableWeather Recurse;
      public ProbeWeather(ModdableWeatherSpecService specs) : base(specs) { }
      public override string Id => "Probe.Other";
      public override int GetChance(WeatherCycleStageDecision stageDecision, WeatherCycleDecision cycleDecision, WeatherHistoryService history) {
        Calls++;
        return Recurse != null ? Weight + Recurse.GetChance(stageDecision, cycleDecision, history) : Weight;
      }
      public override int GetDuration(WeatherCycleStageDecision stageDecision, WeatherCycleDecision cycleDecision, WeatherHistoryService history) => 1;
      public override string ToString() => Id;
    }

    /// <summary>The container the adapter resolves Moddable Weathers' services from, after they are constructed.</summary>
    private sealed class Container : IContainer {
      private readonly Dictionary<Type, object> _instances = new Dictionary<Type, object>();
      internal void Add(object instance) => _instances[instance.GetType()] = instance;
      internal T Get<T>() => (T)_instances[typeof(T)];
      public T GetInstance<T>() => _instances.TryGetValue(typeof(T), out var instance) ? (T)instance : throw new InvalidOperationException("Probe container has no " + typeof(T).Name);
      public IEnumerable<T> GetInstances<T>() => throw new NotSupportedException();
      public object GetInstance(Type type) => throw new NotSupportedException();
      public IEnumerable<object> GetInstances(Type type) => throw new NotSupportedException();
      public IEnumerable<object> GetBoundInstances() => throw new NotSupportedException();
      public void Inject(object instance) => throw new NotSupportedException();
      public IContainer CreateChildContainer(IEnumerable<IConfigurator> configurators) => throw new NotSupportedException();
      public IContainer CreateChildContainer(params IConfigurator[] configurators) => throw new NotSupportedException();
    }

    private static readonly List<string> Calls = new List<string>();
    private static readonly Queue<object> Script = new Queue<object>();

    private static void Draws(ScriptedRandom random, params object[] script) {
      Calls.Clear(); Script.Clear();
      foreach (var item in script) Script.Enqueue(item);
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

    /// <summary>A provider registering one or two tides with their fluids, as Deep Frontier and More Fluids do.</summary>
    private sealed class Provider : IFluidProvider {
      private readonly (string Fluid, string Tide, string Weather, (int, int, int, int)[] Modes)[] _tides;
      public string ProviderId { get; }
      public string OwnerModId { get; }
      public string MinimumApiVersion => "0.1.3";
      public IReadOnlyCollection<string> RequiredCapabilities => new[] { FluidTideRules.RegistrationCapability };
      public Provider(string id, string owner, string fluid, string tide, string weather, (int, int, int, int)[] modes, string fluid2 = null, string tide2 = null, string weather2 = null,
          (int, int, int, int)[] modes2 = null) {
        ProviderId = id; OwnerModId = owner;
        _tides = fluid2 == null ? new[] { (fluid, tide, weather, modes) } : new[] { (fluid, tide, weather, modes), (fluid2, tide2, weather2, modes2) };
      }
      public void Register(FluidRegistration r) {
        foreach (var (fluid, tide, weather, modes) in _tides) {
          r.AddFluid(fluid, OwnerModId + "." + fluid, .5f, .5f, .5f, 1f);
          string p = OwnerModId + ".Weather." + tide;
          r.AddTide(tide, weather, p, p + "Description");
          for (int i = 0; i < 3; i++) r.SetTideMode(tide, FluidTideRules.Modes[i], modes[i].Item1, modes[i].Item2, modes[i].Item3, modes[i].Item4);
          r.SetTideSourceEmission(tide, OwnerModId + "." + fluid, 1.0);
          r.SetTideTexts(tide, p + "Approaching", p + "InProgress", p + "Started", p + "Ended", p + "ApproachingDescription", p + "StartedDescription");
          r.SetTideArt(tide, "i", "p", "n");
          r.SetTideStartSound(tide, "Badtide");
        }
      }
    }

    private sealed class EmptyLoader : ISingletonLoader {
      public IObjectLoader GetSingleton(SingletonKey key) => throw new NotSupportedException();
      public bool TryGetSingleton(SingletonKey key, out IObjectLoader objectLoader) { objectLoader = null; return false; }
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

    /// <summary>One entity's components kept as the game keeps them.</summary>
    private sealed class MemoryEntity : IEntityLoader {
      internal readonly Dictionary<string, SerializedObject> Objects = new Dictionary<string, SerializedObject>(StringComparer.Ordinal);
      public IObjectLoader GetComponent(ComponentKey key) => throw new NotSupportedException();
      public IObjectLoader GetComponent(ComponentKey key, string suffix) => throw new NotSupportedException();
      public bool HasComponent(ComponentKey key) => Objects.ContainsKey(key.Name);
      public bool HasComponent(ComponentKey key, string suffix) => throw new NotSupportedException();
      public bool TryGetComponent(ComponentKey key, out IObjectLoader objectLoader) {
        objectLoader = Objects.TryGetValue(key.Name, out var data) ? new ObjectLoader(data) : null;
        return objectLoader != null;
      }
      public bool TryGetComponent(ComponentKey key, string suffix, out IObjectLoader objectLoader) => throw new NotSupportedException();
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
