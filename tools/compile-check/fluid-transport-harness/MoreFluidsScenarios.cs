using ModdableFluids;
using MoreFluids;

/// <summary>The More Fluids skeleton registers through the public API only.</summary>
internal static class MoreFluidsScenarios {
  internal static void Run(Action<bool, string> check, Action<string, Action> scenario, Dictionary<string, object> observations) {
    scenario("More Fluids registers its provisional liquids and source types through the public API only", () => {
      var host = new ModdableFluidsHost();
      host.RegisterProvider(new MoreFluidsLiquids());
      var registry = host.Freeze();
      string[] fluids = { "MoreFluids.Coffee", "MoreFluids.HealingWater", "MoreFluids.Saltwater" };
      check(registry.Definitions.Skip(2).Select(d => d.Id).SequenceEqual(fluids), "More Fluids definitions: " + string.Join(", ", registry.Definitions.Select(d => d.Id)));
      foreach (var id in fluids) check(registry.TryGet(id, out var d) && d.Metadata["MoreFluids.Provisional"] == "true", id + " is not flagged provisional");
      check(registry.TryGet("MoreFluids.Saltwater", out var salt) && salt.Metadata["MoreFluids.Potable"] == "false" && salt.Metadata["MoreFluids.WaterIntakeLimit"] == "0.1", "Saltwater provisional numbers");
      check(registry.TryGetSourceType("MoreFluids.Geyser", out var geyser) && !geyser.FollowsDrought && geyser.Schedule!.PeriodHours == 18 && geyser.EmittedFluids.Count == 0, "Proposed geyser");
      check(registry.TryGetSourceType("MoreFluids.HealingSpring", out var spring) && spring.EmittedFluids["MoreFluids.HealingWater"] == 1, "Healing spring emission");
      var references = typeof(MoreFluidsLiquids).Assembly.GetReferencedAssemblies().Select(a => a.Name).OrderBy(n => n, StringComparer.Ordinal).ToArray();
      check(references.SequenceEqual(new[] { "ModdableFluids", "Timberborn.ModManagerScene", "UnityEngine.CoreModule", "netstandard" }),
        "More Fluids must reference only the public API and the mod-start/log assemblies: " + string.Join(", ", references));
      observations["moreFluidsSourceTypes"] = registry.SourceTypes.Where(t => !t.IsNative).Select(t => t.ToString()).ToArray();
    });
  }
}
