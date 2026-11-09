using System.Text.Json;
using ModdableFluids;

/// <summary>
/// Moddable Fluids tides (docs/fluids-tides.md): registration and freeze validation, per-mode values, the C′ selection
/// rule and its exact long-run shares against tools/model_tide_selection.py.
/// </summary>
internal static partial class HarnessExtensions {
  static partial void RunTides(Action<bool, string> check, Action<string, Action> scenario, string managed, string specification, Dictionary<string, object> observations) {
    TideScenarios.Run(check, scenario, specification, observations);
  }
}

internal static class TideScenarios {
  internal const string Radioactive = "DeepFrontier.RadioactiveTide", Coffee = "MoreFluids.CoffeeTide", Salt = "MoreFluids.SaltTide";

  /// <summary>A tide as Deep Frontier and More Fluids are expected to register it (numbers from their documents).</summary>
  internal sealed record TideSpec(string Owner, string Local, string Weather, string Fluid, double Strength, string Sound, (int Chance, int Without, int Min, int Max)[] Modes);

  internal static readonly TideSpec RadioactiveSpec = new("DeepFrontier", "RadioactiveTide", "RadioactiveTideWeather", "DeepFrontier.RadioactiveWater", 1, "Badtide",
    new[] { (15, 24, 2, 4), (25, 14, 3, 6), (35, 9, 5, 10) });
  internal static readonly TideSpec CoffeeSpec = new("MoreFluids", "CoffeeTide", "MoreFluids.CoffeeTide", "MoreFluids.Coffee", .5, "Drought",
    new[] { (10, 12, 2, 4), (15, 8, 3, 5), (20, 6, 4, 7) });
  internal static readonly TideSpec SaltSpec = new("MoreFluids", "SaltTide", "MoreFluids.SaltTide", "MoreFluids.Saltwater", 1, "Badtide",
    new[] { (10, 10, 2, 4), (15, 7, 4, 8), (20, 5, 10, 20) });

  internal sealed class TideProvider : IFluidProvider {
    private readonly TideSpec[] _tides;
    private readonly string[] _fluids;
    public string ProviderId { get; }
    public string OwnerModId { get; }
    public string MinimumApiVersion => "0.1.3";
    public IReadOnlyCollection<string> RequiredCapabilities { get; init; } = new[] { FluidTideRules.RegistrationCapability };
    public Action<FluidRegistration>? Extra { get; init; }
    public bool Throw { get; init; }
    public TideProvider(string id, string owner, string[] fluids, params TideSpec[] tides) { ProviderId = id; OwnerModId = owner; _fluids = fluids; _tides = tides; }
    public void Register(FluidRegistration r) {
      foreach (var fluid in _fluids) r.AddFluid(fluid, OwnerModId + "." + fluid + ".DisplayName", .5f, .5f, .5f, 1f);
      foreach (var t in _tides) Add(r, t);
      Extra?.Invoke(r);
      if (Throw) throw new InvalidOperationException("provider failed after registering its tides");
    }
  }

  internal static void Add(FluidRegistration r, TideSpec t, bool texts = true, bool art = true, bool sound = true, bool emission = true, int modes = 3) {
    r.AddTide(t.Local, t.Weather, t.Owner + ".Weather." + t.Local, t.Owner + ".Weather." + t.Local + "Description");
    for (int i = 0; i < modes; i++) r.SetTideMode(t.Local, FluidTideRules.Modes[i], t.Modes[i].Chance, t.Modes[i].Without, t.Modes[i].Min, t.Modes[i].Max);
    if (emission) r.SetTideSourceEmission(t.Local, t.Fluid, 1.0);
    if (t.Strength != 1) r.SetTideSourceStrength(t.Local, t.Strength);
    string p = t.Owner + ".Weather." + t.Local;
    if (texts) r.SetTideTexts(t.Local, p + "Approaching", p + "InProgress", p + "Started", p + "Ended", p + "ApproachingDescription", p + "StartedDescription");
    if (art) r.SetTideArt(t.Local, "Sprites/Weather/" + t.Local + "Icon", "Sprites/Weather/" + t.Local + "Progress", "Sprites/Weather/" + t.Local + "Notification");
    if (sound) r.SetTideStartSound(t.Local, t.Sound);
  }

  internal static IFluidProvider DeepFrontier() => new TideProvider("DeepFrontier.Radiation", "DeepFrontier", new[] { "RadioactiveWater" }, RadioactiveSpec);
  internal static IFluidProvider MoreFluids() => new TideProvider("MoreFluids.Liquids", "MoreFluids", new[] { "Coffee", "Saltwater" }, CoffeeSpec, SaltSpec);

  internal static FluidTideRegistry Freeze(params IFluidProvider[] providers) {
    var host = new ModdableFluidsHost();
    foreach (var provider in providers) host.RegisterProvider(provider);
    host.Freeze();
    return host.Tides;
  }

  internal static FluidRegistryException Rejected(params IFluidProvider[] providers) {
    var host = new ModdableFluidsHost();
    foreach (var provider in providers) host.RegisterProvider(provider);
    try { host.Freeze(); } catch (FluidRegistryException e) { return e; }
    throw new InvalidOperationException("The registry accepted invalid tides");
  }

  /// <summary>Scripted draws: the CheckProbability results and Range values to return, and a log of every call.</summary>
  internal sealed class ScriptedRandom : IFluidTideRandom {
    private readonly Queue<object> _script;
    public List<string> Calls { get; } = new();
    public ScriptedRandom(params object[] script) { _script = new Queue<object>(script); }
    public bool CheckProbability(float p) { Calls.Add("P(" + p.ToString("R") + ")"); return (bool)_script.Dequeue(); }
    public int Range(int min, int max) { Calls.Add("R(" + min + "," + max + ")"); int v = (int)_script.Dequeue(); return v; }
    public bool Done => _script.Count == 0;
  }

  /// <summary>
  /// Enumerates every branch of one selection exactly: CheckProbability(p) branches true/false with p and 1 − p
  /// (p read as its decimal percent, as the model does), Range branches uniformly.
  /// </summary>
  internal static Dictionary<string, double> Distribution(Func<IFluidTideRandom, string?> select) {
    var result = new Dictionary<string, double>(StringComparer.Ordinal);
    var path = new List<int>();
    while (true) {
      var random = new BranchRandom(path);
      string outcome = select(random) ?? "native";
      result[outcome] = result.GetValueOrDefault(outcome) + random.Probability;
      // Odometer: advance the deepest decision that has another option.
      var options = random.Options;
      int depth = options.Count - 1;
      path = random.Taken.ToList();
      while (depth >= 0 && path[depth] + 1 >= options[depth]) depth--;
      if (depth < 0) return result;
      path = path.Take(depth + 1).ToList();
      path[depth]++;
    }
  }

  private sealed class BranchRandom : IFluidTideRandom {
    private readonly List<int> _plan;
    public List<int> Taken { get; } = new();
    public List<int> Options { get; } = new();
    public double Probability { get; private set; } = 1;
    public BranchRandom(List<int> plan) { _plan = plan; }
    private int Next(int options) {
      int choice = Taken.Count < _plan.Count ? _plan[Taken.Count] : 0;
      Taken.Add(choice); Options.Add(options);
      return choice;
    }
    public bool CheckProbability(float p) {
      double exact = Math.Round(p, 6);
      if (Math.Abs(p - 1f) < 1e-6f) { Next(1); return true; }
      bool hit = Next(2) == 0;
      Probability *= hit ? exact : 1 - exact;
      return hit;
    }
    public int Range(int min, int max) {
      int choice = Next(max - min);
      Probability /= max - min;
      return min + choice;
    }
  }

  /// <summary>Native HazardousWeatherRandomizer badtide chance (1.1.2.8), in exact decimals as the model computes it.</summary>
  private static double NativeBadtideChance(double baseChance, string last, int streak) {
    if (streak <= 0) return baseChance;
    bool badtide = last == FluidTideRules.NativeBadtideWeatherId;
    double value = badtide ? baseChance : 1 - baseChance;
    double power = Math.Pow(value, streak + 1);
    if (power < 0.025) value = 0;
    else if (power < 0.05) value *= 0.5;
    return badtide ? value : 1 - value;
  }

  /// <summary>
  /// Long-run shares of a save's settings: the native streak rule plus <see cref="FluidTideSelection.Select"/> (every
  /// tide past its cycles without), solved as the same Markov chain as tools/model_tide_selection.py.
  /// </summary>
  internal static Dictionary<string, double> LongRun(double baseBadtide, FluidTideSaveSettings? settings) {
    const int Cap = 12, Cycle = 1000;
    var tides = settings?.Tides.Select(t => t.TideId).ToList() ?? new List<string>();
    var ids = new List<string> { FluidTideRules.NativeBadtideWeatherId, FluidTideRules.NativeDroughtWeatherId };
    ids.AddRange(tides);
    var states = ids.SelectMany(w => Enumerable.Range(1, Cap).Select(s => (w, s))).ToList();
    var index = states.Select((st, i) => (st, i)).ToDictionary(p => p.st, p => p.i);
    // The selection depends only on whether the previous cycle was a tide (global cooldown).
    var afterTide = settings == null ? new() : Distribution(r => FluidTideSelection.Select(Cycle, Cycle - 1, settings, null, r));
    var otherwise = settings == null ? new() : Distribution(r => FluidTideSelection.Select(Cycle, 0, settings, null, r));
    var distribution = Enumerable.Repeat(1.0 / states.Count, states.Count).ToArray();
    for (int iteration = 0; ; iteration++) {
      if (iteration == 20000) throw new InvalidOperationException("The tide chain did not converge");
      var next = new double[states.Count];
      for (int i = 0; i < states.Count; i++) {
        var (last, streak) = states[i];
        double p = distribution[i];
        if (p == 0) continue;
        var tide = tides.Contains(last) ? afterTide : otherwise;
        double native = tide.GetValueOrDefault("native", settings == null ? 1 : 0);
        double beta = NativeBadtideChance(baseBadtide, last, streak);
        var outcomes = tide.Where(o => o.Key != "native").ToDictionary(o => o.Key, o => o.Value);
        outcomes[FluidTideRules.NativeBadtideWeatherId] = native * beta;
        outcomes[FluidTideRules.NativeDroughtWeatherId] = native * (1 - beta);
        foreach (var (weather, q) in outcomes) next[index[(weather, weather == last ? Math.Min(streak + 1, Cap) : 1)]] += p * q;
      }
      double delta = next.Zip(distribution, (a, b) => Math.Abs(a - b)).Max();
      distribution = next;
      if (delta < 1e-15) break;
    }
    var shares = ids.ToDictionary(w => w, _ => 0.0);
    for (int i = 0; i < states.Count; i++) shares[states[i].w] += distribution[i];
    return shares;
  }

  internal static void Run(Action<bool, string> check, Action<string, Action> scenario, string specification, Dictionary<string, object> observations) {
    void Close(double actual, double expected, string message, double tolerance = 1e-9) =>
      check(Math.Abs(actual - expected) <= tolerance, message + $": actual {actual:R}, expected {expected:R}");
    void Rejects(Action action, string name) {
      bool rejected = false;
      try { action(); } catch (Exception e) when (e is ArgumentException || e is InvalidOperationException) { rejected = true; }
      check(rejected, "Invalid tide input accepted: " + name);
    }

    scenario("tides: registration, freeze order and lookup", () => {
      check(ModdableFluidsHost.Capabilities.Contains(FluidTideRules.RegistrationCapability), "Tide capability listed");
      var tides = Freeze(MoreFluids(), DeepFrontier());
      var reversed = Freeze(DeepFrontier(), MoreFluids());
      check(tides.Tides.Select(t => t.Id).SequenceEqual(new[] { Radioactive, Coffee, Salt }), "Tides in ordinal ID order");
      check(reversed.Tides.Select(t => t.Id).SequenceEqual(tides.Tides.Select(t => t.Id)), "Registration order does not matter");
      var coffee = tides.Get(Coffee);
      check(coffee.OwnerModId == "MoreFluids" && coffee.ProviderId == "MoreFluids.Liquids" && coffee.NativeWeatherId == "MoreFluids.CoffeeTide", "Coffee tide identity");
      check(coffee.SourceStrengthMultiplier == .5 && coffee.SourceEmission.Single().Key == "MoreFluids.Coffee" && coffee.SourceEmission.Single().Value == 1, "Coffee tide source effect");
      check(tides.Get(Radioactive).SourceStrengthMultiplier == 1, "Strength unchanged by default");
      // Decision 2b: the multiplier applies to clean tide-overridable sources only.
      var registry = new ModdableFluidsHost();
      registry.RegisterProvider(MoreFluids());
      var sourceTypes = registry.Freeze();
      double Strength(string type) { check(sourceTypes.TryGetSourceType(type, out var t), "Source type " + type); return registry.Tides.Get(Coffee).StrengthMultiplierFor(t!); }
      foreach (var clean in new[] { NativeFluidSourceTypes.WaterSource, NativeFluidSourceTypes.WaterSeep, NativeFluidSourceTypes.Aquifer, NativeFluidSourceTypes.DevWaterSource })
        check(Strength(clean) == .5, "Coffee tide halves " + clean);
      foreach (var bad in new[] { NativeFluidSourceTypes.BadwaterSource, NativeFluidSourceTypes.BadwaterSeep, NativeFluidSourceTypes.BadtideDrain })
        check(Strength(bad) == 1, "Coffee tide keeps the strength of " + bad);
      var normal = coffee.GetMode(FluidTideRules.Normal);
      check(normal.ChancePercent == 15 && normal.CyclesWithoutTide == 8 && normal.MinDurationDays == 3 && normal.MaxDurationDays == 5, "Coffee Normal values");
      check(coffee.Presentation.StartSound == "Drought" && coffee.Presentation.ApproachingDescriptionLocKey == "MoreFluids.Weather.CoffeeTideApproachingDescription", "Coffee presentation");
      check(tides.TryGetByWeather("RadioactiveTideWeather", out var byWeather) && byWeather.Id == Radioactive, "Lookup by native weather ID");
      check(!tides.TryGetByWeather(FluidTideRules.NativeBadtideWeatherId, out _), "A native weather is no tide");
      check(Freeze(new RegistryScenarios.PlainProvider("Plain.Fluids", "Plain", new List<string>(), new RegistryScenarios.Fluid("Juice", "Plain.Juice"))).Count == 0, "No tides registered");
      Rejects(() => new ModdableFluidsHost().Tides.ToString(), "tides before freeze");
    });

    scenario("tides: freeze reports every problem, registration rejects bad values", () => {
      var problems = Rejected(
        new TideProvider("Broken.Tides", "Broken", new[] { "Mud" }, RadioactiveSpec with { Owner = "Broken", Local = "NoParts", Weather = "Broken.NoParts", Fluid = "Broken.Mud" }) {
          Extra = r => {
            r.AddTide("Unknown", "Broken.Unknown", "a", "b");
            Add(r, RadioactiveSpec with { Owner = "Broken", Local = "UnknownFluid", Weather = "Broken.UnknownFluid", Fluid = "Elsewhere.Mud" });
            r.AddTide("Steep", "Broken.Steep", "a", "b");
            r.SetTideMode("Steep", "Easy", 1, 24, 2, 4); r.SetTideMode("Steep", "Normal", 50, 14, 3, 6); r.SetTideMode("Steep", "Hard", 100, 9, 5, 10);
            r.SetTideSourceEmission("Steep", "Broken.Mud", .6);
          }
        },
        new TideProvider("Copycat.Tides", "Copycat", new[] { "RadioactiveWater" }, RadioactiveSpec with { Owner = "Copycat" }),
        DeepFrontier(),
        new TideProvider("Failing.Tides", "Failing", new string[0], CoffeeSpec with { Owner = "Failing", Weather = "Failing.Coffee", Fluid = "MoreFluids.Coffee" }) { Throw = true }).Problems;
      string all = string.Join("\n", problems);
      check(problems.Any(p => p.Contains("Broken.Unknown") && p.Contains("Easy, Normal, Hard")), "Missing modes named: " + all);
      check(problems.Any(p => p.Contains("Broken.Unknown") && p.Contains("SetTideTexts")), "Missing texts named");
      check(problems.Any(p => p.Contains("Broken.Unknown") && p.Contains("SetTideArt")), "Missing art named");
      check(problems.Any(p => p.Contains("Broken.Unknown") && p.Contains("SetTideStartSound")), "Missing sound named");
      check(problems.Any(p => p.Contains("Broken.Unknown") && p.Contains("SetTideSourceEmission")), "Missing emission named");
      check(problems.Any(p => p.Contains("Broken.UnknownFluid") && p.Contains("Elsewhere.Mud")), "Unknown emitted fluid named");
      check(problems.Any(p => p.Contains("Broken.Steep") && p.Contains("chance curve")), "Out-of-range curve named");
      check(problems.Any(p => p.Contains("Copycat.RadioactiveTide") && p.Contains("RadioactiveTideWeather")), "Shared native weather ID named");
      check(problems.Any(p => p.Contains("Failing.Tides") && p.Contains("failed during Register")) && !problems.Any(p => p.Contains("Failing.CoffeeTide")),
        "A failed provider contributes no tides");
      var log = new List<string>();
      void Bad(Action<FluidRegistration> register, string name) {
        var host = new ModdableFluidsHost();
        bool thrown = false;
        host.RegisterProvider(new RegistryScenarios.PlainProvider("Bad.Tides", "Bad", log, new RegistryScenarios.Fluid("Mud", "Bad.Mud")) {
          RequiredCapabilities = new[] { FluidTideRules.RegistrationCapability },
          Extra = r => { try { register(r); } catch (ArgumentException) { thrown = true; } }
        });
        try { host.Freeze(); } catch (FluidRegistryException) { }
        check(thrown, "Invalid tide registration accepted: " + name);
      }
      Bad(r => r.AddTide("Drought", FluidTideRules.NativeDroughtWeatherId, "a", "b"), "native drought ID");
      Bad(r => r.AddTide("Tide", "", "a", "b"), "empty weather ID");
      Bad(r => r.AddTide("Bad.Tide", "Bad.Tide", "a", "b"), "dotted local name");
      Bad(r => r.AddTide("Tide", "Bad.Tide", "", "b"), "missing display name");
      Bad(r => { r.AddTide("Tide", "Bad.Tide", "a", "b"); r.AddTide("Other", "Bad.Tide", "a", "b"); }, "duplicate weather ID");
      Bad(r => { r.AddTide("Tide", "Bad.Tide", "a", "b"); r.SetTideMode("Tide", "Chill", 10, 5, 1, 2); }, "unknown mode");
      Bad(r => { r.AddTide("Tide", "Bad.Tide", "a", "b"); r.SetTideMode("Tide", "Easy", 0, 5, 1, 2); }, "zero chance");
      Bad(r => { r.AddTide("Tide", "Bad.Tide", "a", "b"); r.SetTideMode("Tide", "Easy", 10, 5, 3, 2); }, "inverted duration");
      Bad(r => { r.AddTide("Tide", "Bad.Tide", "a", "b"); r.SetTideMode("Tide", "Easy", 10, 5, 1, 2); r.SetTideMode("Tide", "Easy", 10, 5, 1, 2); }, "mode twice");
      Bad(r => { r.AddTide("Tide", "Bad.Tide", "a", "b"); r.SetTideSourceStrength("Tide", 1.5); }, "strength above 1");
      Bad(r => { r.AddTide("Tide", "Bad.Tide", "a", "b"); r.SetTideSourceStrength("Tide", 0); }, "zero strength");
      Bad(r => { r.AddTide("Tide", "Bad.Tide", "a", "b"); r.SetTideSourceEmission("Tide", "Bad.Mud", 1.2); }, "share above 1");
      Bad(r => { r.AddTide("Tide", "Bad.Tide", "a", "b"); r.SetTideStartSound("Tide", "Thunder"); }, "unknown sound");
      Bad(r => r.SetTideMode("Missing", "Easy", 10, 5, 1, 2), "unregistered tide");
      var kept = new RegistryScenarios.PlainProvider("Late.Tides", "Late", log) { RequiredCapabilities = new[] { FluidTideRules.RegistrationCapability } };
      var after = new ModdableFluidsHost();
      after.RegisterProvider(kept);
      after.Freeze();
      Rejects(() => kept.Kept!.AddTide("Tide", "Late.Tide", "a", "b"), "tide registration after Register returned");
    });

    scenario("tides: reflected provider registers a tide with primitives only", () => {
      var host = new ModdableFluidsHost();
      host.RegisterReflectedProvider(new ReflectedTides());
      host.Freeze();
      var tide = host.Tides.Get("ExampleCreator.JuiceTide");
      check(tide.SourceEmission["ExampleCreator.Juice"] == .75 && tide.GetMode(FluidTideRules.Hard).ChancePercent == 30, "Reflected tide registered");
    });

    scenario("tides: per-mode values, derivation and Deep Frontier parity", () => {
      // The anchors are the vanilla blueprints.
      string resources = Path.GetDirectoryName(Path.GetDirectoryName(specification))!;
      foreach (var (mode, anchor) in new[] { ("Easy", FluidTideModeWeather.VanillaEasy), ("Normal", FluidTideModeWeather.VanillaNormal), ("Hard", FluidTideModeWeather.VanillaHard) }) {
        using var json = JsonDocument.Parse(File.ReadAllText(Path.Combine(resources, "NewGameModes", "GameMode." + mode + ".blueprint.json")));
        var spec = json.RootElement.GetProperty("GameModeSpec");
        int Min(string name) => spec.GetProperty(name).GetProperty("Min").GetInt32();
        int Max(string name) => spec.GetProperty(name).GetProperty("Max").GetInt32();
        var weather = new FluidTideModeWeather(Min("TemperateWeatherDuration"), Max("TemperateWeatherDuration"), Min("DroughtDuration"), Max("DroughtDuration"),
          Min("BadtideDuration"), Max("BadtideDuration"), (int)Math.Round(spec.GetProperty("ChanceForBadtide").GetSingle() * 100f));
        check(FluidTideModes.VanillaMode(weather) == mode && weather.ToString() == anchor.ToString(), "Vanilla " + mode + " anchor matches its blueprint: " + weather);
      }
      var tides = Freeze(DeepFrontier(), MoreFluids());
      foreach (var tide in tides.Tides)
        for (int i = 0; i < 3; i++) {
          var weather = new[] { FluidTideModeWeather.VanillaEasy, FluidTideModeWeather.VanillaNormal, FluidTideModeWeather.VanillaHard }[i];
          var derived = FluidTideModes.Derive(tide, weather, out int chance, out _);
          var point = tide.GetMode(FluidTideRules.Modes[i]);
          check(derived.Enabled && chance == point.ChancePercent && derived.Weight == point.ChancePercent && derived.CyclesWithoutTide == point.CyclesWithoutTide
            && derived.MinDurationDays == point.MinDurationDays && derived.MaxDurationDays == point.MaxDurationDays, tide.Id + " " + FluidTideRules.Modes[i] + " gets its own point");
        }
      // Deep Frontier's own harness (tools/compile-check/radioactive-tide-modes): Chill is on, 29 cycles without, 10%, 1-3 days.
      var chill = FluidTideModes.Derive(tides.Get(Radioactive), new FluidTideModeWeather(350, 350, 15, 15, 15, 15, 50), out int chillChance, out string chillWhy);
      check(chill.Enabled && chill.CyclesWithoutTide == 29 && chillChance == 10 && chill.MinDurationDays == 1 && chill.MaxDurationDays == 3, "Deep Frontier parity, Chill: " + chill + " " + chillWhy);
      var calm = FluidTideModes.Derive(tides.Get(Coffee), new FluidTideModeWeather(20, 25, 0, 0, 0, 0, 0), out _, out _);
      check(!calm.Enabled, "No hazardous weather: tide off");
      var brief = FluidTideModes.Derive(tides.Get(Salt), new FluidTideModeWeather(5, 5, 1, 1, 1, 1, 40), out _, out string briefWhy);
      check(brief.Enabled && brief.MinDurationDays == 1 && brief.MaxDurationDays == 1 && briefWhy.Contains("capped"), "Capped at the longest hazardous season");
      var defaults = FluidTideModes.Defaults(tides, FluidTideModeWeather.VanillaNormal, out var why);
      check(defaults!.BudgetPercent == 25 && defaults.Get(Radioactive).Weight == 25 && defaults.Get(Coffee).Weight == 15 && defaults.Get(Salt).Weight == 15 && why.Count == 3,
        "Normal defaults: budget is the largest chance, weights the chances");
      check(FluidTideModes.Defaults(Freeze(MoreFluids()), FluidTideModeWeather.VanillaHard, out _)!.BudgetPercent == 20, "More Fluids alone, Hard: budget 20%");
      check(FluidTideModes.Defaults(Freeze(), FluidTideModeWeather.VanillaHard, out _) == null, "No tides: no settings");
      // Every share in a dense grid stays in range for the three expected tides (registration checked the ends).
      foreach (var tide in tides.Tides)
        for (int t = 0; t <= 400; t += 7) for (int d = 0; d <= 60; d += 3) {
          var s = FluidTideModes.Derive(tide, new FluidTideModeWeather(t, t + t / 4, d, d + d / 3, d / 2, d, 40), out int c, out _);
          check(c >= 1 && c <= 100 && (!s.Enabled || (s.MaxDurationDays <= Math.Max(d, d + d / 3))), tide.Id + " grid " + t + "/" + d + ": " + s);
        }
    });

    scenario("tides: C′ selection rule, draws and order", () => {
      FluidTideSettings T(string id, int weight, int without = 1, bool enabled = true) => new(id, enabled, weight, without, 1, 3);
      var df = new FluidTideSaveSettings(25, new[] { T(Radioactive, 25, 14) });
      // One tide: Deep Frontier's exact calls (RadioactiveTideService.Choose): one CheckProbability(25 / 100f), nothing else.
      var random = new ScriptedRandom(true);
      check(FluidTideSelection.Select(15, 0, df, null, random) == Radioactive && random.Calls.SequenceEqual(new[] { "P(" + (25 / 100f).ToString("R") + ")" }) && random.Done, "Single tide draws as Deep Frontier");
      random = new ScriptedRandom(false);
      check(FluidTideSelection.Select(15, 0, df, null, random) == null, "Budget miss keeps the native weather");
      random = new ScriptedRandom();
      check(FluidTideSelection.Select(14, 0, df, null, random) == null && random.Calls.Count == 0, "Cycles without: no draw");
      check(FluidTideSelection.Select(1, 0, df, Radioactive, random) == null && random.Calls.Count == 0, "Cycle 1 never, even forced");
      check(FluidTideSelection.Select(16, 15, df, null, random) == null && random.Calls.Count == 0, "Cooldown: no draw after a tide");
      check(FluidTideSelection.Select(17, 15, df, null, new ScriptedRandom(true)) == Radioactive, "Cooldown is one cycle");
      check(FluidTideSelection.Select(3, 2, df, Radioactive, random) == Radioactive && random.Calls.Count == 0, "Forced tide ignores cooldown and cycles without");
      Rejects(() => FluidTideSelection.Select(3, 0, new FluidTideSaveSettings(25, new[] { T(Radioactive, 25, enabled: false) }), Radioactive, random), "forcing a disabled tide");
      Rejects(() => FluidTideSelection.Select(3, 0, df, Coffee, random), "forcing an unknown tide");
      Rejects(() => FluidTideSelection.Select(3, 3, df, null, random), "last tide in the same cycle");
      // Three tides: one budget draw, then one weighted draw over the eligible tides in ordinal order.
      var all = new FluidTideSaveSettings(25, new[] { T(Salt, 15, 7), T(Radioactive, 25, 14), T(Coffee, 15, 8) });
      var shuffled = new FluidTideSaveSettings(25, new[] { T(Coffee, 15, 8), T(Salt, 15, 7), T(Radioactive, 25, 14) });
      foreach (var (roll, expected) in new[] { (0, Radioactive), (24, Radioactive), (25, Coffee), (39, Coffee), (40, Salt), (54, Salt) }) {
        random = new ScriptedRandom(true, roll);
        check(FluidTideSelection.Select(20, 0, all, null, random) == expected && random.Calls.SequenceEqual(new[] { "P(" + (25 / 100f).ToString("R") + ")", "R(0,55)" }), "Weighted roll " + roll);
        check(FluidTideSelection.Select(20, 0, shuffled, null, new ScriptedRandom(true, roll)) == expected, "Order of the settings does not matter, roll " + roll);
      }
      // Early cycles (decision 1b): the weighted draw is over every enabled tide; a pick not eligible yet keeps the native weather.
      foreach (var (roll, expected) in new[] { (0, (string?)null), (24, null), (25, Coffee), (39, Coffee), (40, Salt), (54, Salt) }) {
        random = new ScriptedRandom(true, roll);
        check(FluidTideSelection.Select(9, 0, all, null, random) == expected && random.Calls.Last() == "R(0,55)", "Cycle 9 (coffee and salt eligible), roll " + roll);
      }
      foreach (var (roll, expected) in new[] { (24, (string?)null), (25, null), (39, null), (40, Salt) }) {
        random = new ScriptedRandom(true, roll);
        check(FluidTideSelection.Select(8, 0, all, null, random) == expected && random.Calls.Count == 2, "Cycle 8 (only salt eligible), roll " + roll);
      }
      var early = Distribution(r => FluidTideSelection.Select(8, 0, all, null, r));
      Close(early[Salt], .25 * 15 / 55, "Cycle 8: salt keeps only its own slice"); Close(early["native"], 1 - .25 * 15 / 55, "Cycle 8: the rest stays native");
      var nine = Distribution(r => FluidTideSelection.Select(9, 0, all, null, r));
      Close(nine[Coffee] + nine[Salt], .25 * 30 / 55, "Cycle 9: coffee and salt keep their slices");
      random = new ScriptedRandom();
      check(FluidTideSelection.Select(7, 0, all, null, random) == null && random.Calls.Count == 0, "No tide eligible: no draw");
      var dfAndOff = new FluidTideSaveSettings(25, new[] { T(Radioactive, 25, 14), T(Coffee, 15, 8, enabled: false) });
      random = new ScriptedRandom(true);
      check(FluidTideSelection.Select(15, 0, dfAndOff, null, random) == Radioactive && random.Calls.Count == 1, "A switched-off tide takes no slice: one enabled tide, Deep Frontier's draws");
      check(FluidTideSelection.Select(21, 20, all, null, new ScriptedRandom()) == null, "Global cooldown blocks every tide");
      var exact = Distribution(r => FluidTideSelection.Select(30, 0, all, null, r));
      Close(exact[Radioactive], .25 * 25 / 55, "Radioactive share of an eligible cycle"); Close(exact[Coffee], .25 * 15 / 55, "Coffee share"); Close(exact["native"], .75, "Native share");
      Rejects(() => new FluidTideSaveSettings(0, new FluidTideSettings[0]), "zero budget");
      Rejects(() => new FluidTideSaveSettings(25, new[] { T(Coffee, 1), T(Coffee, 2) }), "duplicate tide settings");
      Rejects(() => T(Coffee, 0), "zero weight");
      check(new FluidTideSettings(Coffee, false, 0, 0, 0, 0).ToString().EndsWith("off"), "A switched-off tide needs no values");
    });

    scenario("tides: legacy tide-state import (IFluidTideImporter)", () => {
      check(ModdableFluidsHost.Capabilities.Contains(FluidTideRules.ImportCapability), "Tide import capability listed");
      FluidTideSettings Radio(int weight = 25) => new(Radioactive, true, weight, 14, 3, 6);
      FluidTideImport InTide() => new(Radioactive, 20, Radioactive, 4, 25, new[] { Radio() });
      (ModdableFluidsHost Host, FluidTideImportContext Context) Setup(params Func<FluidTideImportContext, FluidTideImport?>[] importers) {
        var host = new ModdableFluidsHost();
        host.RegisterProvider(DeepFrontier()); host.RegisterProvider(MoreFluids());
        for (int i = 0; i < importers.Length; i++) host.RegisterProvider(new TideImporter("Importer" + i + ".Tides", "Importer" + i, importers[i]));
        host.Freeze();
        return (host, new FluidTideImportContext(host.Tides, new object(), new object()));
      }
      // Accepted: unlisted tides are off; the context reaches the importer unchanged.
      FluidTideImportContext? seen = null;
      var (accepting, context) = Setup(c => { seen = c; return InTide(); });
      var import = accepting.ImportTides(context, out string? importer);
      check(importer == "Importer0.Tides" && ReferenceEquals(seen, context) && import.CurrentCycleTideId == Radioactive && import.LastTideCycle == 20 && import.LastTideDuration == 4,
        "Import accepted from its provider: " + import);
      check(import.Settings.BudgetPercent == 25 && import.Settings.Tides.Select(t => t.TideId).SequenceEqual(new[] { Radioactive, Coffee, Salt })
        && import.Settings.Get(Radioactive).Weight == 25 && !import.Settings.Get(Coffee).Enabled && !import.Settings.Get(Salt).Enabled, "Unlisted tides are off in an imported save");
      var none = Setup(_ => null);
      check(none.Host.ImportTides(none.Context, out importer) == null && importer == null, "An importer with nothing for the save returns null");
      var without = Setup();
      check(without.Host.ImportTides(without.Context, out _) == null, "No importer: nothing imported");
      var nullThenState = Setup(_ => null, _ => new FluidTideImport(null, 0, null, 0, 30, new[] { Radio(30) }));
      check(nullThenState.Host.ImportTides(nullThenState.Context, out importer)?.Settings.BudgetPercent == 30 && importer == "Importer1.Tides", "One importer of two returns state");
      // Validation, every failure naming the importer.
      void Refused(Func<FluidTideImportContext, FluidTideImport?> importer, string expected, string name) {
        var (host, ctx) = Setup(importer);
        try { host.ImportTides(ctx, out _); }
        catch (InvalidOperationException e) { check(e.Message.Contains(expected) && e.Message.Contains("Importer0"), name + ": " + e.Message); return; }
        check(false, "Invalid import accepted: " + name);
      }
      Refused(_ => new FluidTideImport(null, 0, null, 0, 25, new[] { new FluidTideSettings("Other.Tide", true, 5, 3, 1, 2) }), "Other.Tide", "settings for an unregistered tide");
      Refused(_ => new FluidTideImport("Other.Tide", 9, "Other.Tide", 3, 25, new[] { Radio() }), "Other.Tide", "an unregistered current tide");
      Refused(_ => new FluidTideImport(Radioactive, 20, Coffee, 4, 25, new[] { Radio() }), "is not the last tide", "current tide differs from the last tide");
      Refused(_ => new FluidTideImport(null, 1, Radioactive, 4, 25, new[] { Radio() }), "impossible", "a last tide in cycle 1");
      Refused(_ => new FluidTideImport(null, 20, Radioactive, 0, 25, new[] { Radio() }), "impossible", "a last tide without a duration");
      Refused(_ => new FluidTideImport(null, 0, Radioactive, 0, 25, new[] { Radio() }), "cycle 0", "a tide ID without a cycle");
      Refused(_ => new FluidTideImport(null, 0, null, 0, 0, new[] { Radio() }), "budget", "a zero budget");
      Refused(_ => new FluidTideImport(null, 0, null, 0, 25, new[] { Radio(0) }), "weight", "a zero weight");
      Refused(_ => new FluidTideImport(null, 0, null, 0, 25, new[] { new FluidTideSettings(Radioactive, true, 25, 14, 6, 3) }), "longer", "an inverted duration");
      Refused(_ => new FluidTideImport(null, 0, null, 0, 25, new[] { Radio(), Radio() }), "two settings", "a tide listed twice");
      Refused(_ => throw new InvalidOperationException("legacy key unreadable"), "legacy key unreadable", "an importer that throws");
      // Two importers returning state stop loading, naming both.
      var (both, bothContext) = Setup(_ => InTide(), _ => InTide());
      bool named = false;
      try { both.ImportTides(bothContext, out _); } catch (FluidSaveException e) { named = e.Message.Contains("Importer0.Tides") && e.Message.Contains("Importer1.Tides"); }
      check(named, "Two importers returning state are refused, naming both");
      Rejects(() => new ModdableFluidsHost().ImportTides(bothContext, out _), "import before the registry froze");
      Rejects(() => accepting.ImportTides(bothContext, out _), "a context of another registry");
      // Weather Station modes of another tide system (IFluidTideStationImporter).
      check(ModdableFluidsHost.Capabilities.Contains(FluidTideRules.WeatherStationCapability), "Weather Station capability listed");
      (ModdableFluidsHost Host, object Entity) Stations(params Func<object, string?>[] importers) {
        var host = new ModdableFluidsHost();
        host.RegisterProvider(DeepFrontier()); host.RegisterProvider(MoreFluids());
        for (int i = 0; i < importers.Length; i++) host.RegisterProvider(new StationImporter("Station" + i + ".Tides", "Station" + i, importers[i]));
        host.Freeze();
        return (host, new object());
      }
      object? entitySeen = null;
      var (stationHost, entity) = Stations(e => { entitySeen = e; return Radioactive; });
      check(stationHost.ImportStationTide(entity, out string? stationImporter) == Radioactive && stationImporter == "Station0.Tides" && ReferenceEquals(entitySeen, entity), "A station's tide imported");
      var quiet = Stations(_ => null, _ => null);
      check(quiet.Host.ImportStationTide(quiet.Entity, out stationImporter) == null && stationImporter == null, "No station importer answers: the native mode");
      void StationRefused(string expected, string name, params Func<object, string?>[] importers) {
        var (host, e) = Stations(importers);
        try { host.ImportStationTide(e, out _); }
        catch (InvalidOperationException ex) { check(ex.Message.Contains(expected), name + ": " + ex.Message); return; }
        check(false, "Invalid station import accepted: " + name);
      }
      StationRefused("Other.Tide", "a station signalling an unregistered tide", _ => "Other.Tide");
      StationRefused("Station1.Tides", "two station importers answering", _ => Coffee, _ => Salt);
      StationRefused("Station0.Tides", "a throwing station importer", _ => throw new InvalidOperationException("unreadable"));
      Rejects(() => new ModdableFluidsHost().ImportStationTide(new object(), out _), "station import before the registry froze");
      // Not repeated after a save: the tide service asks only when the save has neither of its own singletons, and every
      // save writes both. The Mono probe (tools/compile-check/fluid-tides) runs that round trip through the game's persistence.
    });

    scenario("tides: C′ long-run shares match tools/model_tide_selection.py", () => {
      // Exact values printed by tools/model_tide_selection.py (implemented C′ rows).
      var expected = new Dictionary<(string, string), Dictionary<string, double>> {
        [("Easy", "")] = new() { ["BadtideWeather"] = 0.4032274405391503, ["DroughtWeather"] = 0.5967725594608501 },
        [("Easy", "DF")] = new() { ["BadtideWeather"] = 0.3478739087133482, ["DroughtWeather"] = 0.5216913086779567, [Radioactive] = 0.13043478260869576 },
        [("Easy", "MF")] = new() { ["BadtideWeather"] = 0.3644122732182974, ["DroughtWeather"] = 0.5446786358726159, [Coffee] = 0.04545454545454568, [Salt] = 0.04545454545454568 },
        [("Easy", "DF+MF")] = new() { ["BadtideWeather"] = 0.3478739087133486, ["DroughtWeather"] = 0.5216913086779572, [Radioactive] = 0.05590062111801252, [Coffee] = 0.037267080745341685, [Salt] = 0.037267080745341685 },
        [("Normal", "")] = new() { ["BadtideWeather"] = 0.4032274405391503, ["DroughtWeather"] = 0.5967725594608501 },
        [("Normal", "DF")] = new() { ["BadtideWeather"] = 0.3192828887655399, ["DroughtWeather"] = 0.48071711123446054, [Radioactive] = 0.2000000000000001 },
        [("Normal", "MF")] = new() { ["BadtideWeather"] = 0.3478739087133485, ["DroughtWeather"] = 0.5216913086779572, [Coffee] = 0.06521739130434792, [Salt] = 0.06521739130434792 },
        [("Normal", "DF+MF")] = new() { ["BadtideWeather"] = 0.3192828887655396, ["DroughtWeather"] = 0.4807171112344599, [Radioactive] = 0.09090909090909087, [Coffee] = 0.05454545454545453, [Salt] = 0.05454545454545453 },
        [("Hard", "")] = new() { ["BadtideWeather"] = 0.4032274405391503, ["DroughtWeather"] = 0.5967725594608501 },
        [("Hard", "DF")] = new() { ["BadtideWeather"] = 0.29541518996031696, ["DroughtWeather"] = 0.4453255507804237, [Radioactive] = 0.25925925925925924 },
        [("Hard", "MF")] = new() { ["BadtideWeather"] = 0.3329012244751022, ["DroughtWeather"] = 0.5004321088582305, [Coffee] = 0.08333333333333327, [Salt] = 0.08333333333333327 },
        [("Hard", "DF+MF")] = new() { ["BadtideWeather"] = 0.2954151899603168, ["DroughtWeather"] = 0.4453255507804236, [Radioactive] = 0.12098765432098758, [Coffee] = 0.06913580246913577, [Salt] = 0.06913580246913577 },
      };
      var installs = new Dictionary<string, Func<FluidTideRegistry>> {
        [""] = () => Freeze(), ["DF"] = () => Freeze(DeepFrontier()), ["MF"] = () => Freeze(MoreFluids()), ["DF+MF"] = () => Freeze(MoreFluids(), DeepFrontier()),
      };
      var weathers = new Dictionary<string, FluidTideModeWeather> {
        ["Easy"] = FluidTideModeWeather.VanillaEasy, ["Normal"] = FluidTideModeWeather.VanillaNormal, ["Hard"] = FluidTideModeWeather.VanillaHard,
      };
      var table = new List<object>();
      foreach (var ((mode, install), shares) in expected) {
        var settings = FluidTideModes.Defaults(installs[install](), weathers[mode], out _);
        var actual = LongRun(.4, settings);
        check(actual.Keys.OrderBy(k => k, StringComparer.Ordinal).SequenceEqual(shares.Keys.OrderBy(k => k, StringComparer.Ordinal)), mode + " " + install + " weathers");
        foreach (var (weather, share) in shares) Close(actual[weather], share, mode + " " + (install == "" ? "vanilla" : install) + " " + weather);
        table.Add(new { mode, installed = install == "" ? "vanilla" : install, budget = settings?.BudgetPercent ?? 0, shares = actual });
      }
      observations["tideLongRunShares"] = table;
    });
  }

  /// <summary>A compiled provider that only imports Weather Station tide modes.</summary>
  internal sealed class StationImporter : IFluidProvider, IFluidTideStationImporter {
    private readonly Func<object, string?> _import;
    public string ProviderId { get; }
    public string OwnerModId { get; }
    public string MinimumApiVersion => "0.1.3";
    public IReadOnlyCollection<string> RequiredCapabilities => new[] { FluidTideRules.WeatherStationCapability };
    public StationImporter(string id, string owner, Func<object, string?> import) { ProviderId = id; OwnerModId = owner; _import = import; }
    public void Register(FluidRegistration registration) { }
    public string ImportStationTide(FluidTideRegistry tides, object nativeEntityLoader) => _import(nativeEntityLoader)!;
  }

  /// <summary>A compiled provider that only imports tide state.</summary>
  internal sealed class TideImporter : IFluidProvider, IFluidTideImporter {
    private readonly Func<FluidTideImportContext, FluidTideImport?> _import;
    public string ProviderId { get; }
    public string OwnerModId { get; }
    public string MinimumApiVersion => "0.1.3";
    public IReadOnlyCollection<string> RequiredCapabilities => new[] { FluidTideRules.ImportCapability };
    public TideImporter(string id, string owner, Func<FluidTideImportContext, FluidTideImport?> import) { ProviderId = id; OwnerModId = owner; _import = import; }
    public void Register(FluidRegistration registration) { }
    public FluidTideImport ImportTides(FluidTideImportContext context) => _import(context)!;
  }

  /// <summary>A reflected provider: the registration context is reached by method name, with primitives only.</summary>
  public sealed class ReflectedTides {
    public string ProviderId => "ExampleCreator.Tides";
    public string OwnerModId => "ExampleCreator";
    public string MinimumApiVersion => "0.1.3";
    public string[] RequiredCapabilities => new[] { "ModdableFluids.Discovery.Reflection", "ModdableFluids.Tides.Registration" };
    public void Register(object registration) {
      void Call(string name, params object[] arguments) => registration.GetType().GetMethod(name)!.Invoke(registration, arguments);
      Call("AddFluid", "Juice", "ExampleCreator.Juice", .9f, .5f, .1f, .8f);
      Call("AddTide", "JuiceTide", "ExampleCreator.JuiceTide", "ExampleCreator.JuiceTide", "ExampleCreator.JuiceTideDescription");
      Call("SetTideMode", "JuiceTide", "Easy", 10, 10, 2, 3);
      Call("SetTideMode", "JuiceTide", "Normal", 20, 8, 3, 4);
      Call("SetTideMode", "JuiceTide", "Hard", 30, 6, 4, 5);
      Call("SetTideSourceEmission", "JuiceTide", "ExampleCreator.Juice", .75);
      Call("SetTideTexts", "JuiceTide", "a", "b", "c", "d", "e", "f");
      Call("SetTideArt", "JuiceTide", "i", "p", "n");
      Call("SetTideStartSound", "JuiceTide", "Badtide");
    }
  }
}
