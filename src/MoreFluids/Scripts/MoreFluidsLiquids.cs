using System.Collections.Generic;
using System.Globalization;
using ModdableFluids;
using Timberborn.ModManagerScene;
using UnityEngine;

namespace MoreFluids {
  /// <summary>Registers More Fluids with Moddable Fluids at mod start (any mod order; see the API contract).</summary>
  public sealed class MoreFluidsStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      ModdableFluidsEntry.RegisterProvider(new MoreFluidsLiquids());
      Debug.Log("[MoreFluids] registered " + MoreFluidsLiquids.Id + " (provisional data) with Moddable Fluids " + ModdableFluidsEntry.ApiVersion);
    }
  }

  /// <summary>
  /// Coffee, saltwater and healing water, and their source types (docs/more-fluids-design.md). Every
  /// gameplay number is a proposal awaiting approval: each fluid carries <c>MoreFluids.Provisional = true</c>
  /// and its numbers as namespaced metadata, so later content reads them from the registry and nothing is
  /// duplicated in code. No buildings, tides or effects exist yet.
  /// </summary>
  public sealed class MoreFluidsLiquids : IFluidProvider {
    public const string Owner = "MoreFluids";
    public const string Id = Owner + ".Liquids";
    public string ProviderId => Id;
    public string OwnerModId => Owner;
    public string MinimumApiVersion => "0.1.1";
    public IReadOnlyCollection<string> RequiredCapabilities { get; } = new[] { "ModdableFluids.Registry.Definitions", "ModdableFluids.Sources.Types" };

    public void Register(FluidRegistration registration) {
      // Vanilla coffee barrel colour; native rate of 0.2 world volume per good.
      Fluid(registration, "Coffee", .161f, .110f, .090f, .85f, new Dictionary<string, string> {
        ["Good"] = "Coffee", ["VolumePerGood"] = "0.2", ["WaterIntakeLimit"] = "0.5", ["ExtractorMinimumShare"] = "0.1",
        ["Irrigates"] = "true", ["Potable"] = "true", ["TideChance"] = "0.10,0.15,0.20", ["TideCyclesWithout"] = "12,8,6",
        ["TideDays"] = "2-4,3-5,4-7", ["TideSourceStrength"] = "0.5" });
      Fluid(registration, "Saltwater", .15f, .45f, .55f, .35f, new Dictionary<string, string> {
        ["Good"] = "Water", ["DesalinationVolumePerWater"] = "0.3", ["WaterIntakeLimit"] = "0.1", ["IrrigationBlockShare"] = "0.1",
        ["Irrigates"] = "false", ["Potable"] = "false", ["TideChance"] = "0.10,0.15,0.20", ["TideCyclesWithout"] = "10,7,5",
        ["TideDays"] = "2-4,4-8,10-20", ["TideSourceStrength"] = "1" });
      Fluid(registration, "HealingWater", .55f, .95f, .75f, .5f, new Dictionary<string, string> {
        ["Good"] = "Antidote", ["VolumePerGood"] = "0.4", ["WaterIntakeLimit"] = "0.5", ["ExposureMinimumShare"] = "0.2",
        ["InjuryRecoveryPerDay"] = "0.25", ["BadwaterContaminationRecoveryPerDay"] = "0.25", ["Irrigates"] = "true", ["Potable"] = "true" });
      // Proposed geyser (for the user): erupts every 18 hours for 3, with half-hour ramps, at three times its
      // strength; ignores droughts and badtides (a deep source), so it is a bursty, drought-proof supply.
      registration.AddSourceType("Geyser", "MoreFluids.Geyser.DisplayName", "MoreFluidsGeyser", 1, 2f, false, false, false);
      registration.SetSourceSchedule("Geyser", 18, 3, .5, 3, 0);
      registration.AddSourceType("HealingSpring", "MoreFluids.HealingSpring.DisplayName", "MoreFluidsHealingSpring", 1, .4f, true, false, false);
      registration.SetSourceEmission("HealingSpring", Owner + ".HealingWater", 1);
    }

    private static void Fluid(FluidRegistration registration, string local, float r, float g, float b, float a, Dictionary<string, string> numbers) {
      registration.AddFluid(local, Owner + "." + local + ".DisplayName", r, g, b, a);
      registration.AddMetadata(local, Owner + ".Provisional", "true");
      foreach (var pair in numbers) registration.AddMetadata(local, Owner + "." + pair.Key, pair.Value.ToString(CultureInfo.InvariantCulture));
    }
  }
}
