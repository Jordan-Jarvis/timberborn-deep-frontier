using ModdableFluids;
using MoreFluids;

/// <summary>More Fluids on the public API: registration, approved numbers, policies, source types, tides and intake math.</summary>
internal static class MoreFluidsScenarios {
  /// <summary>The real provider's Register stage with only the capabilities this API lists, so its content is checked before every capability ships.</summary>
  private sealed class ListedCapabilitiesProvider : IFluidProvider {
    private readonly MoreFluidsLiquids _inner = new();
    public string ProviderId => _inner.ProviderId;
    public string OwnerModId => _inner.OwnerModId;
    public string MinimumApiVersion => _inner.MinimumApiVersion;
    public IReadOnlyCollection<string> RequiredCapabilities => _inner.RequiredCapabilities.Where(c => ModdableFluidsEntry.Capabilities.Contains(c)).ToArray();
    public void Register(FluidRegistration registration) => _inner.Register(registration);
  }

  internal static (FluidRegistry Registry, FluidTideRegistry Tides) Freeze() {
    var host = new ModdableFluidsHost();
    host.RegisterProvider(new ListedCapabilitiesProvider());
    return (host.Freeze(), host.Tides);
  }

  internal static void Run(Action<bool, string> check, Action<string, Action> scenario, Dictionary<string, object> observations) {
    scenario("More Fluids requires exactly the capabilities it uses, and Moddable Fluids rejects it until each one is listed", () => {
      string[] expected = { "ModdableFluids.Policies.Irrigation", "ModdableFluids.Policies.WaterIntakes", "ModdableFluids.Registry.Definitions", "ModdableFluids.Scene.Lifecycle",
        "ModdableFluids.Sources.Types", "ModdableFluids.Tides.Registration", "ModdableFluids.World.Extraction", "ModdableFluids.World.Sampling" };
      var provider = new MoreFluidsLiquids();
      check(provider.RequiredCapabilities.OrderBy(c => c, StringComparer.Ordinal).SequenceEqual(expected), "More Fluids capabilities: " + string.Join(", ", provider.RequiredCapabilities));
      check(provider.MinimumApiVersion == "0.1.3", "More Fluids keeps MinimumApiVersion 0.1.3 until the release is set");
      var missing = expected.Where(c => !ModdableFluidsEntry.Capabilities.Contains(c)).ToArray();
      var host = new ModdableFluidsHost();
      host.RegisterProvider(provider);
      if (missing.Length == 0) {
        var registry = host.Freeze();
        check(registry.UndeclaredPolicies().Count == 0, "More Fluids declares every policy: " + string.Join("; ", registry.UndeclaredPolicies()));
      } else {
        try { host.Freeze(); check(false, "Moddable Fluids accepted More Fluids without " + string.Join(", ", missing)); }
        catch (FluidRegistryException e) {
          check(missing.All(c => e.Message.Contains(c, StringComparison.Ordinal)), "The rejection names every missing capability: " + e.Message);
        }
      }
      observations["moreFluidsAwaitedCapabilities"] = missing;
    });

    scenario("More Fluids registers its approved fluids, numbers and policies", () => {
      var (registry, _) = Freeze();
      string[] fluids = { MoreFluidsLiquids.Coffee, MoreFluidsLiquids.HealingWater, MoreFluidsLiquids.Saltwater };
      check(registry.Definitions.Skip(2).Select(d => d.Id).SequenceEqual(fluids), "More Fluids definitions: " + string.Join(", ", registry.Definitions.Select(d => d.Id)));
      check(registry.UndeclaredPolicies().Count == 0, "Every More Fluids fluid has both policies: " + string.Join("; ", registry.UndeclaredPolicies()));
      foreach (var id in fluids) {
        var d = registry.Definitions.Single(f => f.Id == id);
        check(!d.Metadata.Keys.Any(k => k.EndsWith(".Provisional", StringComparison.Ordinal)), id + " still carries provisional metadata");
        check(d.DisplayNameLocKey == id + ".DisplayName", id + " display name key");
      }
      void Intake(string id, double refuse, string transformation) {
        var p = registry.Definitions.Single(f => f.Id == id).WaterIntake;
        check(p != null && p.RefuseAtShare == refuse && p.DrawnAsWater == transformation, id + " water intakes: " + p);
      }
      Intake(MoreFluidsLiquids.Coffee, .5, "MoreFluids.CoffeeDrunkAsWater");
      Intake(MoreFluidsLiquids.HealingWater, .5, "MoreFluids.HealingDrunkAsWater");
      Intake(MoreFluidsLiquids.Saltwater, .1, "MoreFluids.BrackishDrunkAsWater");
      var coffee = registry.Definitions.Single(f => f.Id == MoreFluidsLiquids.Coffee);
      var salt = registry.Definitions.Single(f => f.Id == MoreFluidsLiquids.Saltwater);
      var healing = registry.Definitions.Single(f => f.Id == MoreFluidsLiquids.HealingWater);
      check(coffee.Irrigation!.Effect == FluidMoistureEffect.IrrigatesLikeWater && healing.Irrigation!.Effect == FluidMoistureEffect.IrrigatesLikeWater, "Coffee and healing water irrigate like water");
      check(salt.Irrigation!.Effect == FluidMoistureEffect.BlocksLikeBadwater && salt.Irrigation.BlocksAtShare == .1, "Saltwater blocks growth at 10%: " + salt.Irrigation);
      check(coffee.Color.Equals(new FluidColor(.161f, .110f, .090f, .85f)) && salt.Color.Equals(new FluidColor(.15f, .45f, .55f, .35f))
        && healing.Color.Equals(new FluidColor(.55f, .95f, .75f, .5f)), "Approved colours");
      check(MoreFluidsLiquids.Number(coffee, MoreFluidsLiquids.VolumePerGoodKey) == .2 && MoreFluidsLiquids.Number(coffee, MoreFluidsLiquids.ExtractorMinimumShareKey) == .1, "Coffee extraction numbers");
      check(MoreFluidsLiquids.Number(salt, MoreFluidsLiquids.DesalinationVolumePerWaterKey) == .3 && MoreFluidsLiquids.Number(salt, MoreFluidsLiquids.VolumePerGoodKey) == .2, "Desalination numbers");
      check(MoreFluidsLiquids.Number(healing, MoreFluidsLiquids.VolumePerGoodKey) == .4 && MoreFluidsLiquids.Number(healing, MoreFluidsLiquids.ExposureMinimumShareKey) == .2
        && MoreFluidsLiquids.Number(healing, MoreFluidsLiquids.InjuryRecoveryPerDayKey) == .25 && MoreFluidsLiquids.Number(healing, MoreFluidsLiquids.BadwaterContaminationRecoveryPerDayKey) == .25,
        "Healing water numbers");
      bool threw = false;
      try { MoreFluidsLiquids.Number(salt, MoreFluidsLiquids.ExposureMinimumShareKey); } catch (KeyNotFoundException) { threw = true; }
      check(threw, "A missing More Fluids number throws instead of defaulting");
    });

    scenario("More Fluids source types: geyser, map Healing Spring and the per-faction buildable Healing Spring", () => {
      var (registry, _) = Freeze();
      check(registry.TryGetSourceType("MoreFluids.Geyser", out var geyser) && geyser.Template == "MoreFluidsGeyser" && geyser.DefaultStrength == 2f && geyser.TileCount == 1
        && !geyser.FollowsDrought && !geyser.BadtideContamination && !geyser.TideOverridable && geyser.EmittedFluids.Count == 0, "Geyser: " + geyser);
      var s = geyser!.Schedule!;
      check(s.PeriodHours == 18 && s.ActiveHours == 3 && s.RampHours == .5 && s.ActiveMultiplier == 3 && s.DormantMultiplier == 0, "Geyser schedule");
      check(Math.Abs(s.MeanMultiplier * geyser.DefaultStrength - 5.0 / 6) < 1e-12, "Geyser mean strength 0.83: " + s.MeanMultiplier * geyser.DefaultStrength);
      check(s.MultiplierAt(1.5, 0) == 3 && s.MultiplierAt(.25, 0) == 1.5 && s.MultiplierAt(10, 0) == 0, "Geyser erupts at 3x, ramps, then sleeps");
      check(registry.TryGetSourceType("MoreFluids.HealingSpring", out var spring) && spring.Template == "MoreFluidsHealingSpring" && spring.DefaultStrength == .4f
        && spring.FollowsDrought && !spring.BadtideContamination && !spring.TideOverridable && spring.EmittedFluids.Count == 1 && spring.EmittedFluids[MoreFluidsLiquids.HealingWater] == 1,
        "Map Healing Spring: " + spring);
      foreach (string faction in new[] { "Folktails", "IronTeeth" }) {
        check(registry.TryGetSourceType("MoreFluids.HealingWell" + faction, out var well) && well.Template == "MoreFluidsHealingWell." + faction && well.DefaultStrength == .2f
          && well.FollowsDrought && !well.BadtideContamination && !well.TideOverridable && well.EmittedFluids.Count == 1 && well.EmittedFluids[MoreFluidsLiquids.HealingWater] == 1
          && well.Schedule == null, "Buildable Healing Spring (" + faction + "): " + well);
      }
      check(MoreFluidsLiquids.HealingWellTemplates.SequenceEqual(new[] { "MoreFluidsHealingWell.Folktails", "MoreFluidsHealingWell.IronTeeth" }), "Healing well templates");
      observations["moreFluidsSourceTypes"] = registry.SourceTypes.Where(t => !t.IsNative).Select(t => t.ToString()).ToArray();
    });

    scenario("More Fluids registers the Coffee and Salt tides with the approved rows and presentation", () => {
      var (registry, tides) = Freeze();
      check(tides.Tides.Select(t => t.Id).SequenceEqual(new[] { "MoreFluids.CoffeeTide", "MoreFluids.SaltTide" }), "More Fluids tides: " + string.Join(", ", tides.Tides));
      void Rows(string id, string weather, string sound, double strength, string fluid, params (int chance, int without, int min, int max)[] rows) {
        var tide = tides.Get(id);
        check(tide.NativeWeatherId == weather && tide.SourceStrengthMultiplier == strength && tide.SourceEmission.Count == 1 && tide.SourceEmission[fluid] == 1, id + " weather and emission");
        for (int i = 0; i < 3; i++) {
          var m = tide.GetMode(FluidTideRules.Modes[i]);
          check(m.ChancePercent == rows[i].chance && m.CyclesWithoutTide == rows[i].without && m.MinDurationDays == rows[i].min && m.MaxDurationDays == rows[i].max,
            id + " " + FluidTideRules.Modes[i] + ": " + m);
        }
        string name = id.Substring("MoreFluids.".Length), loc = "MoreFluids.Weather." + name, note = "MoreFluids.Weather.Notification." + name, sprite = "Sprites/Weather/MoreFluids" + name;
        var p = tide.Presentation;
        check(tide.DisplayNameLocKey == loc && tide.DescriptionLocKey == loc + "Description" && p.ApproachingLocKey == note + "Approaching" && p.InProgressLocKey == note + "InProgress"
          && p.StartedLocKey == loc + "StartedNotification" && p.EndedLocKey == loc + "EndedNotification" && p.ApproachingDescriptionLocKey == loc + "ApproachingDescription"
          && p.StartedDescriptionLocKey == loc + "StartedDescription", id + " texts");
        check(p.IconSprite == sprite + "Icon" && p.ProgressSprite == sprite + "Progress" && p.NotificationSprite == sprite + "Notification" && p.StartSound == sound, id + " art and sound");
      }
      Rows("MoreFluids.CoffeeTide", "MoreFluidsCoffeeTideWeather", "Drought", .5, MoreFluidsLiquids.Coffee, (10, 12, 2, 4), (15, 8, 3, 5), (20, 6, 4, 7));
      Rows("MoreFluids.SaltTide", "MoreFluidsSaltTideWeather", "Badtide", 1, MoreFluidsLiquids.Saltwater, (10, 10, 2, 4), (15, 7, 4, 8), (20, 5, 10, 20));
      // Each preset gets exactly its own row, so the save defaults match the approved numbers (budget = the largest chance).
      foreach (var (weather, budget, without, min, max) in new[] { (FluidTideModeWeather.VanillaEasy, 10, (12, 10), (2, 2), (4, 4)),
          (FluidTideModeWeather.VanillaNormal, 15, (8, 7), (3, 4), (5, 8)), (FluidTideModeWeather.VanillaHard, 20, (6, 5), (4, 10), (7, 20)) }) {
        var defaults = FluidTideModes.Defaults(tides, weather, out _);
        var c = defaults.Get("MoreFluids.CoffeeTide"); var s = defaults.Get("MoreFluids.SaltTide");
        check(defaults.BudgetPercent == budget && c.Enabled && s.Enabled && c.Weight == budget && s.Weight == budget && c.CyclesWithoutTide == without.Item1
          && s.CyclesWithoutTide == without.Item2 && c.MinDurationDays == min.Item1 && s.MinDurationDays == min.Item2 && c.MaxDurationDays == max.Item1 && s.MaxDurationDays == max.Item2,
          FluidTideModes.VanillaMode(weather) + " save defaults: " + defaults);
        if (weather == FluidTideModeWeather.VanillaNormal) observations["moreFluidsNormalTideDefaults"] = defaults.ToString();
      }
    });

    scenario("Fluid Extractor and Desalinator conversion math comes from the registry", () => {
      var (registry, _) = Freeze();
      var coffee = FluidIntakeRecipe.Extraction(registry, "Coffee", 1);
      check(coffee.FluidId == MoreFluidsLiquids.Coffee && coffee.VolumePerCycle == .2 && coffee.ProductVolumePerCycle == .2 && coffee.MinimumShare == .1, "Coffee: 0.2 volume per Coffee, 10% minimum");
      // 1 Coffee per 0.33 h (the vanilla Water recipe rate) is 3 an hour from 0.6 coffee volume an hour.
      check(Math.Abs(coffee.VolumePerCycle / .33 - .2 / .33) < 1e-12, "Coffee extraction rate");
      var antidote = FluidIntakeRecipe.Extraction(registry, "Antidote", 2);
      check(antidote.FluidId == MoreFluidsLiquids.HealingWater && Math.Abs(antidote.VolumePerCycle - .8) < 1e-12 && antidote.MinimumShare == .1, "Antidote: 2 per cycle from 0.8 healing volume");
      var water = FluidIntakeRecipe.Desalination(registry, "Water", 1);
      check(water.FluidId == MoreFluidsLiquids.Saltwater && water.VolumePerCycle == .3 && water.ProductVolumePerCycle == .2 && water.MinimumShare == 0, "Desalination: 0.3 saltwater per Water");
      check(Math.Abs(water.ProductVolumePerCycle / water.VolumePerCycle - 2.0 / 3) < 1e-12 && Math.Abs(water.VolumePerCycle - water.ProductVolumePerCycle - .1) < 1e-12, "67% recovery, 0.1 brine");
      check(!coffee.Accepts(.0999) && coffee.Accepts(.1) && coffee.Accepts(1), "Too dilute below 10% coffee");
      check(!water.Accepts(0) && water.Accepts(1e-9), "The Desalinator needs any saltwater");
      foreach (var (good, desalination) in new[] { ("Water", false), ("Log", false), ("Coffee", true) }) {
        bool threw = false;
        try { if (desalination) FluidIntakeRecipe.Desalination(registry, good, 1); else FluidIntakeRecipe.Extraction(registry, good, 1); }
        catch (InvalidOperationException) { threw = true; }
        check(threw, (desalination ? "Desalinating " : "Extracting ") + good + " is a content error");
      }
    });

    scenario("Intake buffer: three ticks of need, one request in flight, production only from what was drawn", () => {
      var buffer = new FluidIntakeBuffer();
      check(buffer.Demand(.01) == .03 && buffer.Pending, "First demand requests three ticks' need");
      check(buffer.Demand(.01) == 0, "No second request while one is in flight");
      check(buffer.MaxProgress(.2) == 0, "Nothing drawn, no progress");
      buffer.Resolve(.03);
      check(!buffer.Pending && Math.Abs(buffer.MaxProgress(.2) - .15) < 1e-12, "Resolved volume allows its progress");
      check(buffer.Demand(.01) == 0, "Three ticks stored: no request");
      buffer.Consume(.025);
      check(buffer.Demand(.01) == .03, "Below three ticks: request again");
      buffer.Resolve(0);
      check(Math.Abs(buffer.Stored - .005) < 1e-12, "A refused extraction adds nothing");
      bool threw = false;
      try { buffer.Consume(.01); } catch (InvalidOperationException) { threw = true; }
      check(threw, "Production cannot use more than was drawn");
      threw = false;
      try { buffer.Resolve(.01); } catch (InvalidOperationException) { threw = true; }
      check(threw, "A resolution without a request is an error");
      buffer.Demand(.01);
      buffer.Load(.5);
      check(buffer.Stored == .5 && !buffer.Pending, "Loading restores the store and drops the unsaved request");
    });

    scenario("More Fluids references only the public API, the game and Unity: no Harmony, no Deep Frontier", () => {
      var references = typeof(MoreFluidsLiquids).Assembly.GetReferencedAssemblies().Select(a => a.Name!).OrderBy(n => n, StringComparer.Ordinal).ToArray();
      check(references.All(n => n == "ModdableFluids" || n == "netstandard" || n == "Bindito.Core" || n == "System.Collections.Immutable" || n.StartsWith("Timberborn.", StringComparison.Ordinal)
        || n.StartsWith("UnityEngine", StringComparison.Ordinal)), "More Fluids references: " + string.Join(", ", references));
      check(!references.Any(n => n.Contains("Harmony", StringComparison.OrdinalIgnoreCase) || n.StartsWith("DeepFrontier", StringComparison.Ordinal)
        || n.StartsWith("ModdableFluids.", StringComparison.Ordinal)), "More Fluids uses no Harmony, Deep Frontier or Moddable Fluids internals");
      observations["moreFluidsReferences"] = references;
    });
  }
}
