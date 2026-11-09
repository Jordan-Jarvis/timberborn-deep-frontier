using ModdableFluids;
using ModdableFluids.Native.Prototype;
using ModdableFluids.Transport.Prototype;
using ModdableFluids.World.Prototype;
using static RegistryScenarios;

/// <summary>The world fluid service core: completed-tick sampling, addition matching and source overrides.</summary>
internal static class WorldScenarios {
  internal static void Run(Action<bool, string> check, Action<string, Action> scenario, string managed, string specification, Dictionary<string, object> observations) {
    void Rejects<T>(Action action, string name) where T : Exception {
      Exception? caught = null;
      try { action(); } catch (Exception e) { caught = e; }
      check(caught is T, name + $": expected {typeof(T).Name}, got {caught?.GetType().Name ?? "no exception"}");
    }
    scenario("world service samples whole completed ticks, matches fluid additions and allows one source override", () => {
      var log = new List<string>();
      var host = new ModdableFluidsHost();
      host.RegisterProvider(new PlainProvider("DeepFrontier.Radiation", "DeepFrontier", log, new Fluid("RadioactiveWater", "DeepFrontier.RadioactiveWater", .7f, .8f, .1f, .8f)));
      host.RegisterProvider(new PlainProvider("MoreFluids.Liquids", "MoreFluids", log, new Fluid("Coffee", "MoreFluids.Coffee", .16f, .11f, .09f, .85f)));
      var registry = host.Freeze();
      var radioactive = registry.GetHandle("DeepFrontier.RadioactiveWater"); var coffee = registry.GetHandle("MoreFluids.Coffee");
      using var native = new NativeWaterFixture(managed, specification);
      native.AddColumn(1, 1, 1.5f, 0, 2); native.AddColumn(1, 1, .5f, 4, 12, 1); native.AddColumn(0, 0, 0);
      var session = new NativeFluidTransportSession(native.CreateAdapter(), registry.Count, FluidRegistry.BadwaterIndex);
      var values = new double[registry.Count]; values[FluidRegistry.WaterIndex] = .9; values[FluidRegistry.BadwaterIndex] = .3; values[radioactive.Index] = .3;
      session.SeedComposition(native.Indices[0], new FluidVolumes(values));
      var world = new FluidWorldState(registry, NativeWaterFixture.Stride);
      Rejects<InvalidOperationException>(() => world.TrySample(1, 1, 0, out _), "Sampling before any published tick");
      world.Publish(session);
      check(world.TrySample(1, 1, 1, out var lower) && lower.Floor == 0 && lower.Ceiling == 2 && Math.Abs(lower.GetShare(radioactive) - .2) < 1e-12, "Lower reservoir sample");
      check(lower.Covers(1) && !lower.Covers(2), "Submerged heights");
      check(world.TrySample(1, 1, 6, out var upper) && upper.Floor == 4 && upper.GetVolume(radioactive) == 0, "Upper reservoir in the same cell");
      check(!world.TrySample(1, 1, 3, out _) && !world.TrySample(2, 2, 0, out _), "Solid interval or missing column");
      check(Math.Abs(world.TotalVolume(radioactive) - .3) < 1e-12, "Total radioactive volume");
      session.BeginTick(1);
      Rejects<InvalidOperationException>(() => world.Publish(session), "Publishing mid-tick");
      check(world.TrySample(1, 1, 1, out var during) && during.TotalVolume == lower.TotalVolume, "Readers keep the last completed tick during a tick");
      world.RecordAddition(1, 1, 1, coffee, .25); world.RecordAddition(1, 1, 1, radioactive, .5);
      check(!world.TryResolveAddition(1, 1, 1, .5, out _), "A different volume matched the oldest request");
      check(world.TryResolveAddition(1, 1, 1, .25, out var first) && first.GetVolume(coffee.Index) == .25 && first.TotalVolume == .25, "First recorded addition");
      check(world.TryResolveAddition(1, 1, 1, .5, out var second) && second.GetVolume(radioactive.Index) == .5 && world.PendingAdditions == 0, "Second recorded addition");
      check(!world.TryResolveAddition(1, 1, 1, .5, out _), "An ordinary native addition resolved as a fluid");
      Rejects<ArgumentException>(() => world.RecordAddition(1, 1, 1, registry.Badwater, .1), "Badwater addition through the fluid ledger");
      Rejects<ArgumentOutOfRangeException>(() => world.RecordAddition(1, 1, 1, coffee, -1), "Negative addition");
      world.SetSourceComposition("DeepFrontier.RadioactiveTide", new Dictionary<string, double> { ["DeepFrontier.RadioactiveWater"] = 1 });
      Rejects<InvalidOperationException>(() => world.SetSourceComposition("MoreFluids.CoffeeTide", new Dictionary<string, double> { ["MoreFluids.Coffee"] = 1 }), "Two source composition owners");
      world.SetSourceComposition("DeepFrontier.RadioactiveTide", null);
      world.SetSourceComposition("MoreFluids.CoffeeTide", new Dictionary<string, double> { ["MoreFluids.Coffee"] = 1 });
      check(world.ActiveSourceComposition!["MoreFluids.Coffee"] == 1, "Override after release");
      Rejects<ArgumentException>(() => { world.SetSourceComposition("MoreFluids.CoffeeTide", null); world.SetSourceComposition("X.Tide", new Dictionary<string, double> { ["Timberborn.Water"] = .5 }); }, "Override naming a built-in fluid");
      observations["worldSampleRadioactiveShare"] = lower.GetShare(radioactive);
    });
  }
}
