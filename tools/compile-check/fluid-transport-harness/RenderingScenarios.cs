using ModdableFluids;
using ModdableFluids.Native.Prototype;
using ModdableFluids.Rendering.Prototype;
using ModdableFluids.Transport.Prototype;
using static RegistryScenarios;

/// <summary>Shared rendering, CPU side: resolved appearance and its native-layout texel field.</summary>
internal static class RenderingScenarios {
  internal static void Run(Action<bool, string> check, Action<string, Action> scenario, string managed, string specification, Dictionary<string, object> observations) {
    void Rejects<T>(Action action, string name) where T : Exception {
      Exception? caught = null;
      try { action(); } catch (Exception e) { caught = e; }
      check(caught is T, name + $": expected {typeof(T).Name}, got {caught?.GetType().Name ?? "no exception"}");
    }
    var log = new List<string>();
    FluidRegistry Registry(bool reversed) {
      var providers = new List<IFluidProvider> {
        new PlainProvider("MoreFluids.Drinks", "MoreFluids", log, new Fluid("Coffee", "MoreFluids.Coffee", .3f, .2f, .1f, .9f)),
        new PlainProvider("ExampleCreator.Juices", "ExampleCreator", log, new Fluid("Juice", "ExampleCreator.Juice", .9f, .5f, .1f, .8f))
      };
      if (reversed) providers.Reverse();
      var host = new ModdableFluidsHost();
      foreach (var provider in providers) host.RegisterProvider(provider);
      return host.Freeze();
    }
    byte Q(double value) => (byte)Math.Round(value * 255, MidpointRounding.AwayFromZero);

    scenario("resolved appearance keeps native water and weights extra fluids by share and alpha", () => {
      var registry = Registry(false);
      var resolver = new FluidAppearanceResolver(registry);
      int coffee = registry.GetHandle("MoreFluids.Coffee").Index, juice = registry.GetHandle("ExampleCreator.Juice").Index;
      FluidVolumes Mix(double water, double bad, double coffeeVolume, double juiceVolume) {
        var values = new double[registry.Count];
        values[FluidRegistry.WaterIndex] = water; values[FluidRegistry.BadwaterIndex] = bad; values[coffee] = coffeeVolume; values[juice] = juiceVolume;
        return new FluidVolumes(values);
      }
      check(resolver.Resolve(Mix(1, .5, 0, 0)).Equals(default(FluidAppearance)), "Water and badwater changed the native look");
      check(resolver.Resolve(Mix(0, 0, 0, 0)).Equals(default(FluidAppearance)), "A dry column has a tint");
      check(resolver.Resolve(Mix(0, 0, 2, 0)).Equals(new FluidAppearance(Q(.3f), Q(.2f), Q(.1f), Q(.9f))), "Pure coffee appearance");
      check(resolver.Resolve(Mix(1, 0, 1, 0)).Equals(new FluidAppearance(Q(.3f), Q(.2f), Q(.1f), Q(.5 * .9f))), "Diluted coffee strength");
      double wc = .25 * .9f, wj = .25 * .8f;
      check(resolver.Resolve(Mix(1.5, .5, 1, 1)).Equals(new FluidAppearance(Q((wc * .3f + wj * .9f) / (wc + wj)), Q((wc * .2f + wj * .5f) / (wc + wj)),
        Q((wc * .1f + wj * .1f) / (wc + wj)), Q(1 - (1 - wc) * (1 - wj)))), "Two extra fluids blend by weighted colour; each covers what the other leaves");
      var reversed = Registry(true);
      check(reversed.Fingerprint == registry.Fingerprint, "Registration order changed the registry");
      var reverseResolver = new FluidAppearanceResolver(reversed);
      check(reverseResolver.Resolve(Mix(.3, .1, .7, .2)).Equals(resolver.Resolve(Mix(.3, .1, .7, .2))), "Registration order changed the appearance");
      Rejects<ArgumentException>(() => resolver.Resolve(new FluidVolumes(new double[] { 1, 0, 0 })), "Mixture with another layout");
      // Many fluids: strength never exceeds one and matches the direct formula.
      var host = new ModdableFluidsHost();
      var random = new Random(4412);
      var many = Enumerable.Range(0, 62).Select(i => new Fluid("F" + i, "Many.F" + i, (float)random.NextDouble(), (float)random.NextDouble(), (float)random.NextDouble(), (float)random.NextDouble())).ToArray();
      host.RegisterProvider(new PlainProvider("Many.Pack", "Many", log, many));
      var large = host.Freeze();
      var largeResolver = new FluidAppearanceResolver(large);
      for (int sample = 0; sample < 500; sample++) {
        var volumes = Enumerable.Range(0, large.Count).Select(_ => random.NextDouble() * random.NextDouble()).ToArray();
        var mixture = new FluidVolumes(volumes);
        var appearance = largeResolver.Resolve(mixture);
        double uncovered = 1;
        for (int c = 2; c < large.Count; c++) uncovered *= 1 - volumes[c] / mixture.TotalVolume * large.Definitions[c].Color.Alpha;
        check(appearance.Strength == Q(1 - uncovered), "64-component strength");
      }
      observations["appearancePureCoffee"] = resolver.Resolve(Mix(0, 0, 2, 0)).ToString();
    });

    scenario("appearance texels follow native column layers, clear dried columns and report changed rows", () => {
      using var native = new NativeWaterFixture(managed, specification);
      native.AddColumn(0, 0, 1); native.AddColumn(0, 1, .5f, 0, 2); native.AddColumn(0, 1, .75f, 4, 12, 1); native.AddColumn(2, 2, .25f);
      var registry = Registry(false);
      int coffee = registry.GetHandle("MoreFluids.Coffee").Index, juice = registry.GetHandle("ExampleCreator.Juice").Index;
      var session = new NativeFluidTransportSession(native.CreateAdapter(), registry.Count, FluidRegistry.BadwaterIndex);
      FluidVolumes Split(int slot, int component, double share) {
        double total = native.PhysicalVolume(slot);
        var values = new double[registry.Count];
        values[component] = total * share; values[FluidRegistry.WaterIndex] = total - values[component];
        return new FluidVolumes(values);
      }
      session.SeedComposition(native.Indices[0], Split(0, coffee, .5));
      session.SeedComposition(native.Indices[2], Split(2, juice, 1));
      var resolver = new FluidAppearanceResolver(registry);
      var field = new FluidAppearanceField(NativeWaterFixture.Width, NativeWaterFixture.Height);
      field.Update(session, resolver, NativeWaterFixture.Stride);
      check(field.Layers == 2, "The upper reservoir did not add a texture layer");
      check(field.Get(0, 0, 0).Equals(resolver.Resolve(session.Sample(native.Indices[0]))) && field.Get(0, 0, 0).Strength == Q(.5 * .9f), "Lower coffee column texel");
      check(field.Get(0, 1, 1).Equals(resolver.Resolve(session.Sample(native.Indices[2]))) && field.Get(0, 1, 1).Strength == Q(.8f), "Upper juice column texel on layer 1");
      check(field.Get(0, 1, 0).Strength == 0 && field.Get(2, 2, 0).Strength == 0, "Water-only columns are tinted");
      check(field.DirtyRows().SequenceEqual(new[] { (0, 0), (1, 1) }), "First update rows: " + string.Join(" ", field.DirtyRows()));
      field.Update(session, resolver, NativeWaterFixture.Stride);
      check(field.DirtyRows().Count == 0, "An unchanged state reported changed rows");
      session.SeedComposition(native.Indices[0], Split(0, coffee, 0));
      field.Update(session, resolver, NativeWaterFixture.Stride);
      check(field.Get(0, 0, 0).Equals(default(FluidAppearance)) && field.DirtyRows().SequenceEqual(new[] { (0, 0) }), "A column that lost its coffee was not cleared alone");
      Rejects<ArgumentException>(() => field.Update(session, resolver, NativeWaterFixture.Stride + 1), "Mismatched native stride");
      session.BeginTick(1);
      Rejects<InvalidOperationException>(() => field.Update(session, resolver, NativeWaterFixture.Stride), "Appearance update during a tick");
      check(field.CopyTexels().Length == NativeWaterFixture.Width * NativeWaterFixture.Height * 4 * 2, "Texel buffer size");
      observations["appearanceFieldUpdates"] = field.Updates;
    });
  }
}
