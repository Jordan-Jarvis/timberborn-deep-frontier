using System;
using System.Collections.Generic;
using System.Globalization;
using ModdableFluids;
using Timberborn.ModManagerScene;
using UnityEngine;

namespace MoreFluids {
  /// <summary>Registers More Fluids with Moddable Fluids at mod start (any mod order; see the API contract).</summary>
  public sealed class MoreFluidsStarter : IModStarter {
    /// <summary>The registered provider; game components reach the active fluid scene through it.</summary>
    internal static MoreFluidsLiquids Provider { get; private set; }

    public void StartMod(IModEnvironment modEnvironment) {
      if (Provider != null) throw new InvalidOperationException("More Fluids registered its fluids twice");
      Provider = new MoreFluidsLiquids();
      ModdableFluidsEntry.RegisterProvider(Provider);
      Debug.Log("[MoreFluids] registered " + MoreFluidsLiquids.Id + " with Moddable Fluids " + ModdableFluidsEntry.ApiVersion);
    }
  }

  /// <summary>
  /// Coffee, saltwater and healing water, their water-intake and irrigation policies, the Coffee and Salt tides and the
  /// More Fluids source types, as approved on 2026-11-09 (docs/more-fluids-design.md). The numbers that More Fluids' own
  /// components read (extraction, desalination, exposure) are namespaced fluid metadata, so they live here once.
  /// </summary>
  public sealed class MoreFluidsLiquids : IFluidProvider, IFluidSceneProvider {
    public const string Owner = "MoreFluids";
    public const string Id = Owner + ".Liquids";
    public const string Coffee = Owner + ".Coffee";
    public const string Saltwater = Owner + ".Saltwater";
    public const string HealingWater = Owner + ".HealingWater";
    /// <summary>Metadata keys (each prefixed with <see cref="Owner"/> and a dot).</summary>
    public const string GoodKey = Owner + ".Good", VolumePerGoodKey = Owner + ".VolumePerGood", ExtractorMinimumShareKey = Owner + ".ExtractorMinimumShare",
      DesalinationVolumePerWaterKey = Owner + ".DesalinationVolumePerWater", ExposureMinimumShareKey = Owner + ".ExposureMinimumShare",
      InjuryRecoveryPerDayKey = Owner + ".InjuryRecoveryPerDay", BadwaterContaminationRecoveryPerDayKey = Owner + ".BadwaterContaminationRecoveryPerDay";
    /// <summary>The buildable Healing Spring's blueprint per faction; each is its own source type.</summary>
    public static readonly string[] HealingWellTemplates = { "MoreFluidsHealingWell.Folktails", "MoreFluidsHealingWell.IronTeeth" };

    public string ProviderId => Id;
    public string OwnerModId => Owner;
    public string MinimumApiVersion => "0.1.4";
    public IReadOnlyCollection<string> RequiredCapabilities { get; } = new[] {
      "ModdableFluids.Policies.Irrigation", "ModdableFluids.Policies.WaterIntakes", "ModdableFluids.Registry.Definitions", "ModdableFluids.Scene.Lifecycle",
      "ModdableFluids.Sources.Types", "ModdableFluids.Tides.Registration", "ModdableFluids.World.Extraction", "ModdableFluids.World.Sampling" };

    /// <summary>The active fluid scene, between Activate and Unload; null outside a game scene.</summary>
    public FluidScene Scene { get; private set; }

    public void Register(FluidRegistration registration) {
      // Coffee: vanilla coffee barrel colour; native rate of 0.2 world volume per good.
      registration.AddFluid("Coffee", Owner + ".Coffee.DisplayName", .161f, .110f, .090f, .85f);
      Metadata(registration, "Coffee", (GoodKey, "Coffee"), (VolumePerGoodKey, "0.2"), (ExtractorMinimumShareKey, "0.1"));
      registration.SetWaterIntakePolicy("Coffee", .5, Owner + ".CoffeeDrunkAsWater", Owner + ".Status.TooMuchCoffee", Owner + ".Alert.TooMuchCoffee");
      registration.SetIrrigatesLikeWater("Coffee");

      // Saltwater: brackish limit 10% for intakes and soil; 0.3 saltwater per desalinated Water good (0.2 into the good, 0.1 brine).
      registration.AddFluid("Saltwater", Owner + ".Saltwater.DisplayName", .15f, .45f, .55f, .35f);
      Metadata(registration, "Saltwater", (GoodKey, "Water"), (VolumePerGoodKey, "0.2"), (DesalinationVolumePerWaterKey, "0.3"));
      registration.SetWaterIntakePolicy("Saltwater", .1, Owner + ".BrackishDrunkAsWater", Owner + ".Status.TooSalty", Owner + ".Alert.TooSalty");
      registration.SetBlocksMoisture("Saltwater", .1);

      // Healing water: Antidote at 0.4 volume each; exposure at 20% heals Injury and BadwaterContamination 0.25 a day each.
      registration.AddFluid("HealingWater", Owner + ".HealingWater.DisplayName", .55f, .95f, .75f, .5f);
      Metadata(registration, "HealingWater", (GoodKey, "Antidote"), (VolumePerGoodKey, "0.4"), (ExtractorMinimumShareKey, "0.1"),
        (ExposureMinimumShareKey, "0.2"), (InjuryRecoveryPerDayKey, "0.25"), (BadwaterContaminationRecoveryPerDayKey, "0.25"));
      registration.SetWaterIntakePolicy("HealingWater", .5, Owner + ".HealingDrunkAsWater", Owner + ".Status.TooMuchHealingWater", Owner + ".Alert.TooMuchHealingWater");
      registration.SetIrrigatesLikeWater("HealingWater");

      // Geyser (map object): strength 2, erupts 3 of every 18 hours at three times that with half-hour ramps, dormant
      // between; ignores droughts and badtides.
      registration.AddSourceType("Geyser", "Building.MoreFluidsGeyser.DisplayName", "MoreFluidsGeyser", 1, 2f, false, false, false);
      registration.SetSourceSchedule("Geyser", 18, 3, .5, 3, 0);
      // Healing Spring (map object): 0.4, only healing water, follows droughts, clean in badtides.
      registration.AddSourceType("HealingSpring", "Building.MoreFluidsHealingSpring.DisplayName", "MoreFluidsHealingSpring", 1, .4f, true, false, false);
      registration.SetSourceEmission("HealingSpring", HealingWater, 1);
      // Healing Spring (building), one blueprint per faction: 0.2 at full power, otherwise as the map object.
      foreach (string template in HealingWellTemplates) {
        string local = "HealingWell" + template.Substring(template.IndexOf('.') + 1);
        registration.AddSourceType(local, "Building.MoreFluidsHealingWell.DisplayName", template, 1, .2f, true, false, false);
        registration.SetSourceEmission(local, HealingWater, 1);
      }

      // Coffee tide: half-strength sources emitting coffee, a drought with an upside.
      Tide(registration, "Coffee", Coffee, "Drought", new[] { (10, 12, 2, 4), (15, 8, 3, 5), (20, 6, 4, 7) });
      registration.SetTideSourceStrength("CoffeeTide", .5);
      // Salt tide: full-strength sources emitting saltwater.
      Tide(registration, "Salt", Saltwater, "Badtide", new[] { (10, 10, 2, 4), (15, 7, 4, 8), (20, 5, 10, 20) });
    }

    private static readonly string[] Modes = { "Easy", "Normal", "Hard" };

    private static void Tide(FluidRegistration registration, string name, string fluid, string startSound,
        (int chance, int cyclesWithout, int minDays, int maxDays)[] modes) {
      string tide = name + "Tide", weather = Owner + ".Weather." + tide, notification = Owner + ".Weather.Notification." + tide;
      registration.AddTide(tide, Owner + tide + "Weather", weather, weather + "Description");
      for (int i = 0; i < Modes.Length; i++) registration.SetTideMode(tide, Modes[i], modes[i].chance, modes[i].cyclesWithout, modes[i].minDays, modes[i].maxDays);
      registration.SetTideSourceEmission(tide, fluid, 1);
      registration.SetTideTexts(tide, notification + "Approaching", notification + "InProgress", weather + "StartedNotification", weather + "EndedNotification",
        weather + "ApproachingDescription", weather + "StartedDescription");
      string sprites = "Sprites/Weather/" + Owner + tide;
      registration.SetTideArt(tide, sprites + "Icon", sprites + "Progress", sprites + "Notification");
      registration.SetTideStartSound(tide, startSound);
    }

    private static void Metadata(FluidRegistration registration, string local, params (string key, string value)[] numbers) {
      foreach (var (key, value) in numbers) registration.AddMetadata(local, key, value);
    }

    public void Activate(FluidScene scene) {
      if (Scene != null) throw new InvalidOperationException("More Fluids is still attached to fluid scene " + Scene.Serial);
      Scene = scene ?? throw new ArgumentNullException(nameof(scene));
    }

    public void Unload(FluidScene scene) {
      if (!ReferenceEquals(Scene, scene)) throw new InvalidOperationException("More Fluids was not attached to fluid scene " + scene?.Serial);
      Scene = null;
    }

    /// <summary>A More Fluids number from a fluid's metadata; a missing or malformed value is a registration bug and throws.</summary>
    public static double Number(FluidDefinition fluid, string key) {
      if (fluid == null) throw new ArgumentNullException(nameof(fluid));
      if (!fluid.Metadata.TryGetValue(key, out string text)) throw new KeyNotFoundException(fluid.Id + " has no metadata " + key);
      if (!double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out double value) || double.IsNaN(value) || double.IsInfinity(value))
        throw new FormatException(fluid.Id + " metadata " + key + " is not a finite number: '" + text + "'");
      return value;
    }
  }
}
