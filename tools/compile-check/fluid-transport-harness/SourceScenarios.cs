using System.IO.Compression;
using System.Text.Json;
using ModdableFluids;
using ModdableFluids.Sources.Prototype;
using ModdableFluids.Transport.Prototype;
using static RegistryScenarios;

/// <summary>Source types: the game's native kinds, custom kinds such as a geyser, schedules and emission.</summary>
internal static class SourceScenarios {
  internal sealed class SourceProvider : PlainProvider {
    private readonly Action<FluidRegistration> _sources;
    public SourceProvider(string id, string owner, List<string> log, Action<FluidRegistration> sources, params Fluid[] fluids) : base(id, owner, log, fluids) {
      _sources = sources; RequiredCapabilities = new[] { "ModdableFluids.Registry.Definitions", "ModdableFluids.Sources.Types" };
      Extra = registration => _sources(registration);
    }
  }

  /// <summary>A reflected provider registering a source type through the primitive-only methods.</summary>
  public sealed class ReflectedSpring {
    public string ProviderId => "ExampleCreator.Springs"; public string OwnerModId => "ExampleCreator"; public string MinimumApiVersion => "0.1.1";
    public string[] RequiredCapabilities => new[] { "ModdableFluids.Sources.Types" };
    public void Register(object registration) {
      registration.GetType().GetMethod("AddSourceType")!.Invoke(registration, new object[] { "LemonSpring", "ExampleCreator.LemonSpring", "ExampleLemonSpring", 1, 1f, true, false, true });
    }
  }

  internal static void Run(Action<bool, string> check, Action<string, Action> scenario, string managed, Dictionary<string, object> observations) {
    void Rejects<T>(Action action, string name, string? mention = null) where T : Exception {
      Exception? caught = null;
      try { action(); } catch (Exception e) { caught = e; }
      check(caught is T, name + $": expected {typeof(T).Name}, got {caught?.GetType().Name ?? "no exception"} {caught?.Message}");
      if (mention != null && caught != null) check(caught.Message.Contains(mention, StringComparison.Ordinal), name + ": message lacks '" + mention + "': " + caught.Message);
    }
    var log = new List<string>();
    var healing = new Fluid("HealingWater", "MoreFluids.HealingWater", .55f, .95f, .75f, .5f);
    var coffee = new Fluid("Coffee", "MoreFluids.Coffee", .161f, .11f, .09f, .85f);
    void Geyser(FluidRegistration r) {
      r.AddSourceType("Geyser", "MoreFluids.Geyser", "MoreFluidsGeyser", 1, 2f, false, false, false);
      r.SetSourceSchedule("Geyser", 18, 3, .5, 3, 0);
      r.AddSourceType("HealingGeyser", "MoreFluids.HealingGeyser", "MoreFluidsHealingGeyser", 1, 2f, false, false, false);
      r.SetSourceSchedule("HealingGeyser", 18, 3, .5, 3, 0);
      r.SetSourceEmission("HealingGeyser", "MoreFluids.HealingWater", 1);
    }
    FluidRegistry Registry(params object[] providers) {
      var host = new ModdableFluidsHost();
      foreach (var p in providers) { if (p is IFluidProvider c) host.RegisterProvider(c); else host.RegisterReflectedProvider(p); }
      return host.Freeze();
    }

    scenario("source types: the game's native kinds, custom kinds and validation", () => {
      var registry = Registry(new SourceProvider("MoreFluids.Liquids", "MoreFluids", log, Geyser, healing, coffee), new ReflectedSpring());
      string[] natives = { NativeFluidSourceTypes.WaterSource, NativeFluidSourceTypes.BadwaterSource, NativeFluidSourceTypes.WaterSeep, NativeFluidSourceTypes.BadwaterSeep,
        NativeFluidSourceTypes.Aquifer, NativeFluidSourceTypes.BadtideDrain, NativeFluidSourceTypes.DevWaterSource };
      check(registry.SourceTypes.Select(t => t.Id).SequenceEqual(natives.Concat(new[] { "ExampleCreator.LemonSpring", "MoreFluids.Geyser", "MoreFluids.HealingGeyser" })),
        "Source type order: " + string.Join(", ", registry.SourceTypes.Select(t => t.Id)));
      check(registry.SourceTypes.Take(7).All(t => t.IsNative && t.FollowsDrought && t.OwnerModId == "Timberborn" && t.EmittedFluids.Count == 0), "Native kinds");
      check(registry.TryGetSourceTypeByTemplate("MoreFluidsHealingGeyser", out var healingGeyser) && healingGeyser.EmittedFluids["MoreFluids.HealingWater"] == 1
        && !healingGeyser.FollowsDrought && healingGeyser.Schedule!.ActiveMultiplier == 3, "Custom geyser definition");
      check(registry.TryGetSourceType("ExampleCreator.LemonSpring", out var lemon) && lemon.TideOverridable && lemon.Template == "ExampleLemonSpring", "Reflected source type");
      var reversed = Registry(new ReflectedSpring(), new SourceProvider("MoreFluids.Liquids", "MoreFluids", log, Geyser, healing, coffee));
      check(reversed.SourceTypes.Select(t => t.Id).SequenceEqual(registry.SourceTypes.Select(t => t.Id)), "Registration order changed the source types");

      void Fails(Action<FluidRegistration> sources, string mention, params Fluid[] fluids) {
        var host = new ModdableFluidsHost();
        host.RegisterProvider(new SourceProvider("Bad.Sources", "Bad", log, sources, fluids));
        FluidRegistryException? report = null;
        try { host.Freeze(); } catch (FluidRegistryException e) { report = e; }
        check(report != null && report.Message.Contains(mention, StringComparison.Ordinal), "Invalid source type accepted or unreported (" + mention + "): " + report?.Message);
      }
      Fails(r => { r.AddSourceType("Ghost", "Bad.Ghost", "BadGhost", 1, 1f, true, true, true); r.SetSourceEmission("Ghost", "Bad.Missing", .5); }, "not a registered extra fluid");
      Fails(r => { r.AddSourceType("Over", "Bad.Over", "BadOver", 1, 1f, true, true, true); r.SetSourceEmission("Over", "Bad.A", .7); r.SetSourceEmission("Over", "Bad.B", .4); },
        "above 1", new Fluid("A", "Bad.A"), new Fluid("B", "Bad.B"));
      Fails(r => { r.AddSourceType("Burst", "Bad.Burst", "BadBurst", 1, 3f, false, false, false); r.SetSourceSchedule("Burst", 10, 2, .5, 3, 0); }, "above the native limit of 8 per tile");
      Fails(r => r.AddSourceType("Clash", "Bad.Clash", "WaterSource", 1, 1f, true, true, true), "both claim blueprint WaterSource");
      Fails(r => { r.AddSourceType("Ramp", "Bad.Ramp", "BadRamp", 1, 1f, true, true, true); r.SetSourceSchedule("Ramp", 10, 2, 1.5, 2, 0); }, "Both ramps must fit");
      Fails(r => r.AddSourceType("Huge", "Bad.Huge", "BadHuge", 1, 9f, true, true, true), "the native limit");
      Fails(r => r.SetSourceEmission("Nothing", "Bad.A", .5), "has not registered source type", new Fluid("A", "Bad.A"));
      Fails(r => { r.AddSourceType("Twice", "Bad.Twice", "BadTwice", 1, 1f, true, true, true); r.AddSourceType("Twice", "Bad.Twice", "BadTwice2", 1, 1f, true, true, true); }, "twice");
      var noCapability = new ModdableFluidsHost();
      noCapability.RegisterProvider(new PlainProvider("Bad.Old", "Bad", log) { RequiredCapabilities = new[] { "ModdableFluids.Sources.Types", "ModdableFluids.Sources.Runtime" } });
      Rejects<FluidRegistryException>(() => noCapability.Freeze(), "Unimplemented source runtime capability", "ModdableFluids.Sources.Runtime");
      observations["sourceTypes"] = registry.SourceTypes.Select(t => t.ToString()).ToArray();
    });

    scenario("geyser schedules erupt periodically with ramps, an exact mean and a stable per-entity phase", () => {
      var schedule = new FluidSourceSchedule(18, 3, .5, 3, 0);
      void Near(double actual, double expected, string name) => check(Math.Abs(actual - expected) < 1e-12, name + $": {actual:R} vs {expected:R}");
      Near(schedule.MultiplierAt(0, 0), 0, "Eruption start"); Near(schedule.MultiplierAt(.25, 0), 1.5, "Rising");
      Near(schedule.MultiplierAt(.5, 0), 3, "Peak"); Near(schedule.MultiplierAt(2, 0), 3, "Plateau"); Near(schedule.MultiplierAt(2.75, 0), 1.5, "Falling");
      Near(schedule.MultiplierAt(3, 0), 0, "Dormant"); Near(schedule.MultiplierAt(17.9, 0), 0, "Late dormant");
      Near(schedule.MultiplierAt(18.25, 0), 1.5, "Next period"); Near(schedule.MultiplierAt(-17.75, 0), 1.5, "Negative time");
      Near(schedule.MultiplierAt(10, 8.5), 3, "Phase shift");
      double integral = 0; const int steps = 180000;
      for (int i = 0; i < steps; i++) integral += schedule.MultiplierAt((i + .5) * 18.0 / steps, 0);
      check(Math.Abs(integral / steps - schedule.MeanMultiplier) < 1e-6, "Mean multiplier");
      Near(schedule.MeanMultiplier, 3 * 2.5 / 18, "Mean of a 3-hour, half-hour-ramp eruption every 18 hours");
      var a = Guid.Parse("8f0c2f9e-2b31-4c0e-9a51-7a0d6c1f2e33"); var b = Guid.Parse("10a1b2c3-d4e5-4f60-8172-839405a6b7c8");
      check(schedule.PhaseFor(a) == schedule.PhaseFor(a) && schedule.PhaseFor(a) != schedule.PhaseFor(b), "Phase is stable per entity and differs between entities");
      check(schedule.PhaseFor(a) >= 0 && schedule.PhaseFor(a) < 18, "Phase within one period");
      Rejects<ArgumentOutOfRangeException>(() => new FluidSourceSchedule(0, 1, 0, 1, 0), "Zero period");
      Rejects<ArgumentOutOfRangeException>(() => new FluidSourceSchedule(10, 11, 0, 1, 0), "Eruption longer than its period");
      Rejects<ArgumentOutOfRangeException>(() => new FluidSourceSchedule(10, 2, 0, double.NaN, 0), "NaN multiplier");
      Rejects<ArgumentOutOfRangeException>(() => schedule.MultiplierAt(double.PositiveInfinity, 0), "Infinite time");
      observations["geyserMeanMultiplier"] = schedule.MeanMultiplier;
    });

    scenario("source emission composes native contamination, registered fluids and tide overrides", () => {
      var registry = Registry(new SourceProvider("MoreFluids.Liquids", "MoreFluids", log, Geyser, healing, coffee), new ReflectedSpring());
      registry.TryGetSourceType(NativeFluidSourceTypes.WaterSource, out var water);
      registry.TryGetSourceType("MoreFluids.HealingGeyser", out var geyser);
      registry.TryGetSourceType("ExampleCreator.LemonSpring", out var lemon);
      int h = registry.GetHandle("MoreFluids.HealingWater").Index, c = registry.GetHandle("MoreFluids.Coffee").Index;
      void Conserves(FluidVolumes mixture, double volume, string name) => check(Math.Abs(mixture.TotalVolume - volume) <= 4 * mixture.ComponentCount * 2.2204460492503131e-16 * volume, name + " conservation");
      var clean = FluidSourceEmission.Compose(registry, water!, 2, 0, null);
      check(clean.GetVolume(FluidRegistry.WaterIndex) == 2 && clean.TotalVolume == 2, "Native clean source");
      var badtide = FluidSourceEmission.Compose(registry, water!, 2, .6, null);
      check(Math.Abs(badtide.GetVolume(FluidRegistry.BadwaterIndex) - 1.2) < 1e-15 && Math.Abs(badtide.GetVolume(FluidRegistry.WaterIndex) - .8) < 1e-15, "Badtide ramp share");
      var tide = new Dictionary<string, double> { ["MoreFluids.Coffee"] = 1 };
      var coffeeTide = FluidSourceEmission.Compose(registry, water!, 2, .25, tide);
      check(coffeeTide.GetVolume(c) == 1.5 && coffeeTide.GetVolume(FluidRegistry.WaterIndex) == 0 && coffeeTide.GetVolume(FluidRegistry.BadwaterIndex) == .5, "Tide override on a native source");
      var healingEruption = FluidSourceEmission.Compose(registry, geyser!, 3, 0, tide);
      check(healingEruption.GetVolume(h) == 3 && healingEruption.GetVolume(c) == 0, "A non-overridable geyser ignores the tide");
      var lemonTide = FluidSourceEmission.Compose(registry, lemon!, 1, 0, new Dictionary<string, double> { ["MoreFluids.Coffee"] = .3, ["MoreFluids.HealingWater"] = .2 });
      Conserves(lemonTide, 1, "Mixed tide"); check(lemonTide.GetVolume(c) == .3 && lemonTide.GetVolume(h) == .2, "Mixed tide shares");
      var random = new Random(3301);
      for (int i = 0; i < 2000; i++) {
        double volume = Math.Exp(random.NextDouble() * 20 - 12), bad = random.NextDouble(), s1 = random.NextDouble() * .6, s2 = random.NextDouble() * .4;
        Conserves(FluidSourceEmission.Compose(registry, lemon!, volume, bad, new Dictionary<string, double> { ["MoreFluids.Coffee"] = s1, ["MoreFluids.HealingWater"] = s2 }), volume, "Generated emission");
      }
      Rejects<ArgumentException>(() => FluidSourceEmission.Compose(registry, lemon!, 1, 0, new Dictionary<string, double> { ["MoreFluids.Coffee"] = .7, ["MoreFluids.HealingWater"] = .4 }), "Tide shares above one");
      Rejects<ArgumentException>(() => FluidSourceEmission.Compose(registry, lemon!, 1, 0, new Dictionary<string, double> { ["Timberborn.Badwater"] = .5 }), "Tide naming a built-in fluid");
      Rejects<ArgumentOutOfRangeException>(() => FluidSourceEmission.Compose(registry, water!, -1, 0, null), "Negative emission");
      Rejects<ArgumentOutOfRangeException>(() => FluidSourceEmission.Compose(registry, water!, 1, 1.5, null), "Contamination above one");
      check(FluidSourceEmission.StrengthMultiplier(water!, 5, Guid.NewGuid()) == 1, "Native sources have no schedule");
    });

    scenario("the native source kinds match every source blueprint the installed game ships", () => {
      string zipPath = Path.GetFullPath(Path.Combine(managed, "..", "StreamingAssets", "Modding", "Blueprints.zip"));
      using var zip = ZipFile.OpenRead(zipPath);
      var registry = new ModdableFluidsHost().Freeze();
      var seen = new List<string>(); var operators = new SortedSet<string>(StringComparer.Ordinal);
      foreach (var entry in zip.Entries.Where(e => e.FullName.EndsWith(".json", StringComparison.Ordinal))) {
        using var reader = new StreamReader(entry.Open());
        var root = JsonDocument.Parse(reader.ReadToEnd()).RootElement;
        if (root.ValueKind != JsonValueKind.Object) continue;
        foreach (string op in new[] { "UndergroundWaterSourceDrillSpec", "WaterSourceRegulatorSpec", "WaterSourceDischargerSpec", "WaterSourceDisablerSpec" })
          if (root.TryGetProperty(op, out _)) operators.Add(op + ": " + Path.GetFileNameWithoutExtension(Path.GetFileNameWithoutExtension(entry.Name)));
        if (!root.TryGetProperty("WaterSourceSpec", out var spec)) continue;
        string template = root.GetProperty("TemplateSpec").GetProperty("TemplateName").GetString()!;
        double? depth = root.TryGetProperty("WaterDepthStrengthModifierSpec", out var d) ? d.GetProperty("DepthLimit").GetDouble() : null;
        var weathers = root.TryGetProperty("HazardousWeatherWaterSourceSpec", out var w) ? w.GetProperty("ActiveInHazardousWeather").EnumerateArray().Select(x => x.GetString()!).ToArray() : Array.Empty<string>();
        var signature = new NativeSourceSignature(template, spec.GetProperty("Coordinates").GetArrayLength(), spec.GetProperty("DefaultStrength").GetSingle(),
          root.GetProperty("WaterSourceContaminationSpec").GetProperty("DefaultContamination").GetSingle(), root.TryGetProperty("BadtideWaterSourceContaminationControllerSpec", out _),
          depth, root.TryGetProperty("UndergroundWaterSourceSpec", out _), weathers, root.TryGetProperty("DirectionalWaterSourceSpec", out _));
        check(NativeSourceClassifier.TryClassify(registry, signature, out var type, out string reason), "Unclassified native source blueprint " + entry.FullName + ": " + reason);
        check(type!.IsNative, "Native blueprint classified as a custom type");
        seen.Add(type.Id);
      }
      check(seen.OrderBy(s => s, StringComparer.Ordinal).SequenceEqual(registry.SourceTypes.Where(t => t.IsNative).Select(t => t.Id).OrderBy(s => s, StringComparer.Ordinal)),
        "Native source table and installed blueprints differ: " + string.Join(", ", seen));
      var changed = new NativeSourceSignature("WaterSeep", 4, 1f, 0f, true, .9, false, Array.Empty<string>(), false);
      Rejects<InvalidOperationException>(() => NativeSourceClassifier.TryClassify(registry, changed, out _, out _), "A changed native seep", "depth limit 0.9");
      check(!NativeSourceClassifier.TryClassify(registry, new NativeSourceSignature("SomeModSpring", 1, 1f, 0f, false, null, false, Array.Empty<string>(), false), out _, out var why)
        && why.Contains("SomeModSpring"), "An unregistered blueprint is reported, not guessed");
      observations["nativeSourceBlueprints"] = seen.ToArray();
      observations["nativeSourceOperators"] = operators.ToArray();
    });
  }
}
