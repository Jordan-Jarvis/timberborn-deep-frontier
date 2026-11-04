// Radioactive tide settings of game modes, run against the shipped game DLLs
// (how to run: RadioactiveTideModesHarness.csproj). Every game mode, vanilla or
// added by another mod, must get valid tide settings: a mode without a
// RadioactiveTideGameModeSpec takes the ones its weather gives
// (RadioactiveTideGameModes.Derive), a mode with one keeps it.
using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;
using DeepFrontier.Scripts.RadioactiveTide;
using Timberborn.BlueprintSystem;
using Timberborn.GameSceneLoading;
using Timberborn.MapRepositorySystem;
using Timberborn.NewGameConfigurationSystem;
using Timberborn.Persistence;
using Timberborn.SceneLoading;
using Timberborn.SerializationSystem;
using Timberborn.SettingsSystem;
using Timberborn.WorldPersistence;

internal static class Program {
  private static int _failures;
  private static int _cases;

  // Like zxuiji's Chill Mode (Workshop 3642660958) and the coordinator's
  // repro mod: 350-day temperate seasons, 15-day droughts and badtides at
  // 50% from cycle 0, no handicap cycles.
  private const string ChillJson = @"{
    ""GameModeSpec"": {
      ""Order"": 5, ""IsDefault"": false,
      ""DisplayNameLocKey"": ""NewGameConfigurationPanel.Chill"", ""DescriptionLocKey"": ""NewGameConfigurationPanel.ChillModeDescription"",
      ""StartingAdults"": 10, ""AdultAgeProgress"": { ""Min"": 0.1, ""Max"": 0.7 },
      ""StartingChildren"": 10, ""ChildAgeProgress"": { ""Min"": 0.1, ""Max"": 0.8 },
      ""FoodConsumption"": 0.1, ""WaterConsumption"": 0.1, ""StartingFood"": 999, ""StartingWater"": 999,
      ""TemperateWeatherDuration"": { ""Min"": 350, ""Max"": 350 },
      ""DroughtDuration"": { ""Min"": 15, ""Max"": 15 },
      ""DroughtDurationHandicapMultiplier"": 1.0, ""DroughtDurationHandicapCycles"": 0,
      ""CyclesBeforeRandomizingBadtide"": 0, ""ChanceForBadtide"": 0.5,
      ""BadtideDuration"": { ""Min"": 15, ""Max"": 15 },
      ""BadtideDurationHandicapMultiplier"": 1.0, ""BadtideDurationHandicapCycles"": 0,
      ""InjuryChance"": 0.1, ""DemolishableRecoveryRate"": 0.75
    }
  }";

  private static int Main() {
    string root = RepoRoot();
    string managed = GameManaged(root);
    AssemblyLoadContext.Default.Resolving += (context, name) => {
      string path = Path.Combine(managed, name.Name + ".dll");
      return File.Exists(path) ? context.LoadFromAssemblyPath(path) : null;
    };
    Run(root);
    Console.WriteLine($"{_cases - _failures}/{_cases} cases passed");
    return _failures == 0 ? 0 : 1;
  }

  private static void Run(string root) {
    string vanillaDir = Path.Combine(root, "vendor", "timberborn-modding", "Assets", "Tools", "ImportedAssets", "Editor", "Resources", "NewGameModes");
    var vanilla = new Dictionary<string, GameModeSpec>();
    foreach (string mode in new[] { "Easy", "Normal", "Hard" })
      vanilla[mode] = Preset($"GameMode.{mode}", File.ReadAllText(Path.Combine(vanillaDir, $"GameMode.{mode}.blueprint.json")).TrimStart('﻿'));
    var chill = Preset("GameMode.Chill", ChillJson);

    // 1. The vanilla modes get exactly their curve points (the 0.8.5 presets).
    var expected = new Dictionary<string, (int cycles, int chance, int min, int max)> {
      ["Easy"] = (24, 15, 2, 4), ["Normal"] = (14, 25, 3, 6), ["Hard"] = (9, 35, 5, 10) };
    foreach (var (mode, (cycles, chance, min, max)) in expected) {
      var tide = RadioactiveTideGameModes.For(vanilla[mode], $"game mode {mode}", out var derivation);
      Case($"{mode}: derived {Show(tide)} = on, {cycles} cycles without, {chance}%, {min}-{max} days",
        derivation != null && tide.Enabled && tide.CyclesWithoutTide == cycles && tide.ChancePercent == chance && tide.Duration.Min == min && tide.Duration.Max == max);
      var point = RadioactiveTideTuning.GameModeCurve.Single(p => p.Mode == mode);
      var weather = RadioactiveTideModeWeather.Of(vanilla[mode], mode);
      Case($"{mode}: curve point weather is the vanilla weather ({weather})", weather.ToString() == point.Weather.ToString()
        && weather.HazardShare == point.Weather.HazardShare);
      Console.WriteLine($"    {mode}: {derivation}");
    }
    Case("Normal keeps the 0.8.3 defaults", Matches(RadioactiveTideGameModes.For(vanilla["Normal"], "Normal", out _),
      RadioactiveTideTuning.LegacyEnabled, RadioactiveTideTuning.LegacyMinCycle - 1, RadioactiveTideTuning.LegacyChancePercent,
      RadioactiveTideTuning.LegacyMinDurationDays, RadioactiveTideTuning.LegacyMaxDurationDays));

    // 2. A mode another mod adds, without a RadioactiveTideGameModeSpec.
    var chillTide = RadioactiveTideGameModes.For(chill, "game mode Chill", out var chillDerivation);
    Console.WriteLine($"    Chill: {Show(chillTide)}; {chillDerivation}");
    var easyTide = RadioactiveTideGameModes.For(vanilla["Easy"], "Easy", out _);
    Case("Chill: derived, on and valid", chillDerivation != null && chillTide.Enabled && Valid(chillTide));
    Case("Chill: gentler than Easy (later, rarer, no longer)", chillTide.CyclesWithoutTide > easyTide.CyclesWithoutTide
      && chillTide.ChancePercent < easyTide.ChancePercent && chillTide.Duration.Max <= easyTide.Duration.Max && chillTide.Duration.Min <= easyTide.Duration.Min);
    Case("Chill: on, 29 cycles without (from cycle 30), 10%, 1-3 days", Matches(chillTide, true, 29, 10, 1, 3));
    Case("Chill: tides no longer than its 15-day hazardous seasons", chillTide.Duration.Max <= 15);

    // 3. A Chill new game: settings, their source, and the save round trip.
    var settings = new FakeSettings();
    var newGame = new FakeSceneLoader(GameSceneParameters.CreateNewGameParameters(new NewGameConfiguration("IronTeeth", default(MapFileReference), chill, "")));
    var empty = new FakeSingletons();
    var values = RadioactiveTideStartingValues.Resolve(empty, newGame, settings);
    Console.WriteLine($"    Chill new game: {values}");
    Case("Chill new game: the derived values, source names the mode and the derivation",
      values.Enabled && values.CyclesWithoutTide == 29 && values.ChancePercent == 10 && values.MinDurationDays == 1 && values.MaxDurationDays == 3
      && values.Source.StartsWith(RadioactiveTideStartingValues.NewGameSource + " GameMode.Chill, derived from its weather: ", StringComparison.Ordinal));
    var saved = new FakeSingletons();
    RadioactiveTideStartingValues.Write(saved, values);
    var reloaded = RadioactiveTideStartingValues.Resolve(saved, new FakeSceneLoader(GameSceneParameters.CreateGameSaveParameters(null)), settings);
    Case($"Chill save reloads its own values, without needing the mode ({reloaded})", reloaded.Source == RadioactiveTideStartingValues.SavedSource
      && reloaded.Enabled == values.Enabled && reloaded.CyclesWithoutTide == values.CyclesWithoutTide && reloaded.ChancePercent == values.ChancePercent
      && reloaded.MinDurationDays == values.MinDurationDays && reloaded.MaxDurationDays == values.MaxDurationDays);
    var oldSave = RadioactiveTideStartingValues.Resolve(empty, new FakeSceneLoader(GameSceneParameters.CreateGameSaveParameters(null)), settings);
    Case($"a save from before per-game settings keeps the former defaults ({oldSave})", oldSave.Source == RadioactiveTideStartingValues.LegacySource
      && oldSave.Enabled && oldSave.CyclesWithoutTide == 14 && oldSave.ChancePercent == 25 && oldSave.MinDurationDays == 3 && oldSave.MaxDurationDays == 6);
    var hardGame = RadioactiveTideStartingValues.Resolve(empty, new FakeSceneLoader(GameSceneParameters.CreateNewGameParameters(
      new NewGameConfiguration("IronTeeth", default(MapFileReference), vanilla["Hard"], ""))), settings);
    Case($"a Hard new game ({hardGame})", hardGame.CyclesWithoutTide == 9 && hardGame.ChancePercent == 35 && hardGame.MinDurationDays == 5 && hardGame.MaxDurationDays == 10);

    // 4. A mode's own RadioactiveTideGameModeSpec wins; the custom mode keeps its rows' values.
    var own = RadioactiveTideGameModes.Create(false, 40, 5, 1, 2);
    var chillWithOwn = new Blueprint("GameMode.Chill", new ComponentSpec[] { chill, own }, ImmutableArray<Blueprint>.Empty).GetSpec<GameModeSpec>();
    var ownTide = RadioactiveTideGameModes.For(chillWithOwn, "Chill with its own settings", out var ownDerivation);
    Case("a mode's own RadioactiveTideGameModeSpec is used as it is", ownDerivation == null && Matches(ownTide, false, 40, 5, 1, 2));
    var custom = new GameModeSpec { TemperateWeatherDuration = Days(13, 17), DroughtDuration = Days(5, 9), BadtideDuration = Days(4, 8), ChanceForBadtide = 0.4f };
    var customWithTide = RadioactiveTideGameModes.WithTide(custom, RadioactiveTideGameModes.Create(true, 1, 100, 1, 1));
    var customTide = RadioactiveTideGameModes.For(customWithTide, "the custom mode", out var customDerivation);
    Case("the custom mode keeps its rows' values", customDerivation == null && Matches(customTide, true, 1, 100, 1, 1));
    Case("a custom mode left without values derives them like a preset",
      RadioactiveTideGameModes.For(custom, "custom", out var d) is var c && d != null && Matches(c, true, 14, 25, 3, 6));

    // 5. Weather without hazards, or with very short ones.
    var calm = Mode(temperate: (20, 25), drought: (0, 0), badtide: (0, 0), chance: 0f);
    var calmTide = RadioactiveTideGameModes.For(calm, "calm", out var calmDerivation);
    Case($"no hazardous weather: tides off ({calmDerivation})", !calmTide.Enabled && Valid(calmTide, checkDisabled: true));
    Case("native custom mode with drought and badtide switched off: tides off",
      !RadioactiveTideGameModes.For(Mode((13, 17), (0, 0), (0, 0), 0f, cyclesBefore: 0), "off", out _).Enabled);
    Case("native custom mode with only badtides (chance forced to 100%, drought 0-0): on, capped by the badtide",
      RadioactiveTideGameModes.For(Mode((13, 17), (0, 0), (4, 8), 1f), "badtide only", out _) is var b && b.Enabled && b.Duration.Max <= 8 && Valid(b));
    var droughtOnly = RadioactiveTideGameModes.For(Mode((13, 17), (5, 9), (40, 60), 0f), "drought only", out var droughtOnlyDerivation);
    Case($"drought only: its unused 40-60 day badtide setting is ignored ({Show(droughtOnly)})", droughtOnly.Enabled && droughtOnly.Duration.Max <= 9);
    var brief = RadioactiveTideGameModes.For(Mode((5, 5), (1, 1), (1, 1), 0.4f), "one-day hazards", out var briefDerivation);
    Console.WriteLine($"    one-day hazards: {Show(brief)}; {briefDerivation}");
    Case("one-day hazards: tides last one day", brief.Enabled && brief.Duration.Min == 1 && brief.Duration.Max == 1);
    var endless = RadioactiveTideGameModes.For(Mode((0, 0), (30, 60), (30, 60), 0.4f), "no temperate weather", out var endlessDerivation);
    Console.WriteLine($"    no temperate weather: {Show(endless)}; {endlessDerivation}");
    Case("no temperate weather (share 1): valid", endless.Enabled && Valid(endless));
    var yearLong = RadioactiveTideGameModes.For(Mode((100000, 100000), (1, 1), (1, 1), 0.5f), "100,000-day temperate", out _);
    Case($"share near 0: valid, gentler than Chill ({Show(yearLong)})", yearLong.Enabled && Valid(yearLong) && yearLong.CyclesWithoutTide >= chillTide.CyclesWithoutTide);

    // 6. Every mode on a grid of native values gets valid settings, never
    // longer than its longest hazardous season, and harsher with more hazard.
    int[] temperates = { 0, 1, 3, 5, 8, 13, 17, 30, 60, 120, 350, 999 };
    int[] lengths = { 0, 1, 2, 3, 4, 5, 8, 9, 15, 30, 60, 99 };
    float[] chances = { 0f, 0.01f, 0.1f, 0.25f, 0.4f, 0.5f, 0.75f, 0.99f, 1f };
    int grid = 0, invalid = 0, longer = 0, offWithHazard = 0;
    var byShare = new List<(double share, RadioactiveTideGameModeSpec tide, int longest)>();
    foreach (int t in temperates) foreach (int dMin in lengths) foreach (int dMax in lengths) foreach (int bMin in lengths) foreach (int bMax in lengths) foreach (float p in chances) {
      if (dMin > dMax || bMin > bMax || (dMax - dMin) % 3 != 0 || (bMax - bMin) % 2 != 0) continue;
      var mode = Mode((t, t + t / 4), (dMin, dMax), (bMin, bMax), p);
      var weather = RadioactiveTideModeWeather.Of(mode, "grid");
      var tide = RadioactiveTideGameModes.For(mode, "grid", out _);
      grid++;
      if (!Valid(tide, checkDisabled: true)) invalid++;
      if (tide.Enabled && tide.Duration.Max > weather.LongestHazardDays) longer++;
      if (tide.Enabled != (weather.LongestHazardDays >= 1)) offWithHazard++;
      if (tide.Enabled) byShare.Add((weather.HazardShare, tide, weather.LongestHazardDays));
    }
    Case($"grid of {grid} modes: every one valid", invalid == 0);
    Case("grid: no tide longer than the mode's longest hazardous season", longer == 0);
    Case("grid: tides on exactly when the mode has hazardous weather", offWithHazard == 0);
    var ordered = byShare.OrderBy(x => x.share).ToList();
    int unordered = 0;
    for (int i = 1; i < ordered.Count; i++) {
      var (a, b2) = (ordered[i - 1].tide, ordered[i].tide);
      if (b2.CyclesWithoutTide > a.CyclesWithoutTide || b2.ChancePercent < a.ChancePercent) unordered++;
    }
    Case("grid: more hazard never brings tides later or more rarely", unordered == 0);

    // 7. Invalid modes fail, naming the mode.
    Throws("a mode without BadtideDuration", () => RadioactiveTideGameModes.For(Mode((13, 17), (5, 9), (4, 8), 0.4f) with { BadtideDuration = null }, "game mode Broken", out _), "game mode Broken");
    Throws("a shortest badtide longer than the longest", () => RadioactiveTideGameModes.For(Mode((13, 17), (5, 9), (8, 4), 0.4f), "game mode Broken", out _), "BadtideDuration is 8-4");
    Throws("a negative drought", () => RadioactiveTideGameModes.For(Mode((13, 17), (-1, 9), (4, 8), 0.4f), "game mode Broken", out _), "DroughtDuration");
    Throws("a badtide chance above 1", () => RadioactiveTideGameModes.For(Mode((13, 17), (5, 9), (4, 8), 1.5f), "game mode Broken", out _), "ChanceForBadtide");
    Throws("a mode whose blueprint was dropped", () => RadioactiveTideGameModes.For(chill with { Blueprint = null }, "the new game's mode", out _), "has no blueprint");
    Throws("an own spec without Duration", () => RadioactiveTideGameModes.For(new Blueprint("GameMode.X", new ComponentSpec[] { chill,
      new RadioactiveTideGameModeSpec { Enabled = true, CyclesWithoutTide = 5, ChancePercent = 5 } }, ImmutableArray<Blueprint>.Empty).GetSpec<GameModeSpec>(), "game mode X", out _), "has no Duration");
  }

  private static GameModeSpec Mode((int min, int max) temperate, (int min, int max) drought, (int min, int max) badtide, float chance, int cyclesBefore = 4) =>
    new Blueprint("GameMode.Test", new ComponentSpec[] { new GameModeSpec {
      DisplayNameLocKey = "Test", TemperateWeatherDuration = Days(temperate.min, temperate.max), DroughtDuration = Days(drought.min, drought.max),
      BadtideDuration = Days(badtide.min, badtide.max), ChanceForBadtide = chance, CyclesBeforeRandomizingBadtide = cyclesBefore } },
      ImmutableArray<Blueprint>.Empty).GetSpec<GameModeSpec>();

  private static MinMaxSpec<int> Days(int min, int max) => new MinMaxSpec<int> { Min = min, Max = max };

  // A preset as the game loads it: the blueprint file's GameModeSpec in a blueprint named after the file.
  private static GameModeSpec Preset(string name, string json) {
    using var document = JsonDocument.Parse(json);
    var spec = (GameModeSpec)FromJson(typeof(GameModeSpec), document.RootElement.GetProperty("GameModeSpec"));
    return new Blueprint(name, new ComponentSpec[] { spec }, ImmutableArray<Blueprint>.Empty).GetSpec<GameModeSpec>();
  }

  private static object FromJson(Type type, JsonElement element) {
    if (type == typeof(int)) return element.GetInt32();
    if (type == typeof(float)) return element.GetSingle();
    if (type == typeof(bool)) return element.GetBoolean();
    if (type == typeof(string)) return element.GetString();
    object value = Activator.CreateInstance(type);
    foreach (var property in element.EnumerateObject()) {
      var info = type.GetProperty(property.Name, BindingFlags.Public | BindingFlags.Instance)
        ?? throw new InvalidOperationException($"{type.Name} has no {property.Name}");
      info.SetValue(value, FromJson(info.PropertyType, property.Value));
    }
    return value;
  }

  private static bool Valid(RadioactiveTideGameModeSpec tide, bool checkDisabled = false) {
    if (tide.Duration == null || tide.Duration.Min > tide.Duration.Max) return false;
    if (!tide.Enabled && !checkDisabled) return true;
    try {
      RadioactiveTideSettingsCheck.ValidateValues(tide.CyclesWithoutTide, tide.ChancePercent, tide.Duration.Min, tide.Duration.Max, "harness");
      return true;
    } catch (InvalidOperationException) { return false; }
  }

  private static bool Matches(RadioactiveTideGameModeSpec tide, bool enabled, int cycles, int chance, int min, int max) =>
    tide.Enabled == enabled && tide.CyclesWithoutTide == cycles && tide.ChancePercent == chance && tide.Duration.Min == min && tide.Duration.Max == max;

  private static string Show(RadioactiveTideGameModeSpec t) =>
    $"{(t.Enabled ? "on" : "off")}, {t.CyclesWithoutTide} cycles without, {t.ChancePercent}%, {t.Duration.Min}-{t.Duration.Max} days";

  private static void Case(string name, bool passed) {
    _cases++;
    if (!passed) _failures++;
    Console.WriteLine($"{(passed ? "PASS" : "FAIL")} {name}");
  }

  private static void Throws(string name, Action action, string messagePart) {
    try {
      action();
      Case($"{name} fails", false);
    } catch (InvalidOperationException e) {
      Case($"{name} fails: {e.Message}", e.Message.Contains(messagePart));
    }
  }

  private static string RepoRoot() {
    for (var dir = new DirectoryInfo(Directory.GetCurrentDirectory()); dir != null; dir = dir.Parent)
      if (File.Exists(Path.Combine(dir.FullName, "tools", "dev-environment.json"))) return dir.FullName;
    throw new InvalidOperationException("Run from inside the repository (or a scratch mirror): tools/dev-environment.json not found; run python tools/setup_dev.py");
  }

  private static string GameManaged(string root) {
    using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(root, "tools", "dev-environment.json")));
    string managed = document.RootElement.GetProperty("gameManaged").GetString();
    if (!Directory.Exists(managed)) throw new InvalidOperationException($"gameManaged {managed} does not exist");
    return managed;
  }

  private sealed class FakeSceneLoader : ISceneLoader {
    private readonly ISceneParameters _parameters;
    public FakeSceneLoader(ISceneParameters parameters) { _parameters = parameters; }
    public long LastLoadTimeMs => 0;
    public void LoadScene(ISceneParameters sceneParameters, string tip) => throw new NotSupportedException();
    public void LoadSceneInstantly(ISceneParameters sceneParameters, string tip) => throw new NotSupportedException();
    public void LoadSceneInstantly(ISceneParameters sceneParameters) => throw new NotSupportedException();
    public bool HasAnySceneParameters() => _parameters != null;
    public bool TryGetSceneParameters<T>(out T sceneParameters) where T : ISceneParameters {
      if (_parameters is T typed) { sceneParameters = typed; return true; }
      sceneParameters = default;
      return false;
    }
    public T GetSceneParameters<T>() where T : ISceneParameters =>
      TryGetSceneParameters<T>(out var parameters) ? parameters : throw new InvalidOperationException("no scene parameters");
  }

  // A save's singletons, written and read through the native ObjectSaver/ObjectLoader.
  private sealed class FakeSingletons : ISingletonLoader, ISingletonSaver {
    private readonly Dictionary<string, SerializedObject> _singletons = new Dictionary<string, SerializedObject>();
    public IObjectLoader GetSingleton(SingletonKey key) => new ObjectLoader(_singletons[key.Name]);
    public bool TryGetSingleton(SingletonKey key, out IObjectLoader objectLoader) {
      objectLoader = _singletons.TryGetValue(key.Name, out var saved) ? new ObjectLoader(saved) : null;
      return objectLoader != null;
    }
    IObjectSaver ISingletonSaver.GetSingleton(SingletonKey key) {
      if (!_singletons.TryGetValue(key.Name, out var saved)) _singletons[key.Name] = saved = new SerializedObject();
      return new ObjectSaver(saved);
    }
  }

  // The player's settings store with nothing in it (no former mod settings).
  private sealed class FakeSettings : ISettings {
    public int GetInt(string key, int defaultValue) => defaultValue;
    public int GetSafeInt(string key, int defaultValue) => defaultValue;
    public void SetInt(string key, int value) => throw new NotSupportedException();
    public bool GetBool(string key, bool defaultValue = false) => defaultValue;
    public bool GetSafeBool(string key, bool defaultValue = false) => defaultValue;
    public void SetBool(string key, bool value) => throw new NotSupportedException();
    public float GetFloat(string key, float defaultValue) => defaultValue;
    public float GetSafeFloat(string key, float defaultValue) => defaultValue;
    public void SetFloat(string key, float value) => throw new NotSupportedException();
    public string GetString(string key, string defaultValue) => defaultValue;
    public string GetSafeString(string key, string defaultValue) => defaultValue;
    public void SetString(string key, string value) => throw new NotSupportedException();
    public bool Has(string key) => false;
    public void Clear(string key) => throw new NotSupportedException();
    public void ValidateInt(string key, ImmutableArray<int> validValues, int defaultValue) => throw new NotSupportedException();
    public void ValidateString(string key, ImmutableArray<string> validValues, string defaultValue) => throw new NotSupportedException();
  }
}
