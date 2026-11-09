using ModdableFluids.Native.Prototype;
using ModdableFluids.Transport.Prototype;

internal static class SourceRegressionScenarios {
  internal static void Run(Action<bool, string> check, Action<string, Action> scenario,
      string managed, string specification, Dictionary<string, object> observations) {
    FluidVolumes Mix(params double[] values) => new(values);
    void Close(double actual, double expected, string message, double scale = 1) =>
      check(Math.Abs(actual - expected) <= 4e-12 * scale, message + $": actual {actual:R}, expected {expected:R}");
    void Balanced(FluidVolumes before, FluidRemovalResult result, string message) {
      double shares = 0;
      for (int c = 0; c < before.ComponentCount; c++) {
        check(result.Remaining.GetVolume(c) >= 0 && result.Remaining.GetShare(c) <= 1, message + " valid remaining component");
        check(result.Removed.GetVolume(c) >= 0 && result.Removed.GetVolume(c) <= before.GetVolume(c), message + " bounded withdrawal");
        Close(result.Remaining.GetVolume(c) + result.Removed.GetVolume(c), before.GetVolume(c), message + " conservation", before.TotalVolume);
        shares += result.Remaining.GetShare(c);
      }
      Close(shares, result.Remaining.TotalVolume > 0 ? 1 : 0, message + " valid share sum");
    }
    scenario("negative source reproducer preserves pure custom fluid instead of exceeding 100 percent", () => {
      float drained = 1f - 1f / 1.068215f;
      double legacy = 1 / (1d - drained);
      check(legacy > 1.06, "Legacy negative control must reproduce the reported >100% share");
      var before = Mix(0, 0, 1, 0);
      var result = FluidTransportPrototype.RemoveSource(before, 1, drained, 1);
      Balanced(before, result, "negative badwater source without badwater");
      Close(result.Remaining.TotalVolume, 1 - (double)drained, "Negative source drains actual fluid");
      Close(result.Remaining.GetShare(2), 1, "Pure custom fluid remains pure");
      observations["legacyNegativeSourceShare"] = legacy;
      observations["jointNegativeSourceShare"] = result.Remaining.GetShare(2);
    });
    scenario("negative sources match native total and badwater changes while retaining custom cohort ratios", () => {
      foreach (var before in new[] { Mix(.5, 1, .25, .25), Mix(0, 0, 1, 0), Mix(0, 1, 0, 0), Mix(.25, .25, .25, .25) })
        foreach (float bad in new[] { 0f, .25f, 1f })
          foreach (float amount in new[] { 0f, .125f, .5f, 3f }) {
            using var native = new NativeWaterFixture(managed, specification);
            native.AddColumn(1, 1, (float)before.TotalVolume);
            native.SetContamination(0, before.GetShare(1));
            native.ApplyNativeSource(0, -amount / NativeWaterFixture.DeltaTime, bad);
            var result = FluidTransportPrototype.RemoveSource(before, 1, amount, bad);
            Balanced(before, result, "native negative source");
            check(Math.Abs(result.Remaining.TotalVolume - native.PhysicalVolume(0)) < 2e-6, "Native source drainage parity");
            check(Math.Abs(result.Remaining.GetShare(1) - native.Contamination(0)) < 2e-6, "Native source badwater parity");
            double beforeNonBad = before.TotalVolume - before.GetVolume(1);
            double afterNonBad = result.Remaining.TotalVolume - result.Remaining.GetVolume(1);
            for (int c = 0; c < before.ComponentCount; c++) if (c != 1)
              Close(result.Remaining.GetVolume(c) * beforeNonBad, before.GetVolume(c) * afterNonBad, "Custom cohort ratio");
          }
    });
    scenario("generated source withdrawals conserve up to 64 components near empty and across exhausted cohorts", () => {
      var random = new Random(2918173);
      for (int sample = 0; sample < 2000; sample++) {
        int count = sample % 3 == 0 ? 64 : sample % 3 == 1 ? 16 : 4;
        var before = new FluidVolumes(Enumerable.Range(0, count).Select(_ => Math.Exp(random.NextDouble() * 24 - 24)).ToArray());
        int bad = random.Next(count);
        double amount = sample % 5 == 0 ? Math.BitDecrement(before.TotalVolume) : before.TotalVolume * random.NextDouble() * 2;
        double badShare = sample % 3 == 0 ? 0 : sample % 3 == 1 ? 1 : random.NextDouble();
        var result = FluidTransportPrototype.RemoveSource(before, bad, amount, badShare);
        Balanced(before, result, "generated source " + sample);
        Close(result.Remaining.TotalVolume, Math.Max(0, before.TotalVolume - amount), "Requested source withdrawal", before.TotalVolume);
      }
      bool rejected = false;
      try { FluidTransportPrototype.RemoveSource(Mix(1, 0), 1, 1, double.NaN); } catch (ArgumentOutOfRangeException) { rejected = true; }
      check(rejected, "Nonfinite withdrawal composition must fail");
    });
    scenario("source operations retain native order and account for drainage in the source stage", () => {
      double Run(bool withdrawFirst) {
        using var fixture = new NativeWaterFixture(managed, specification);
        fixture.AddColumn(1, 1, 1);
        var session = new NativeFluidTransportSession(fixture.CreateAdapter(), 4, 1);
        int index = fixture.Indices[0];
        session.BeginTick(1); fixture.RunAdapterSubstep(session, fixture.ClearRawFlows, new double[1], false);
        if (withdrawFirst) session.RemoveSource(index, 1, 1);
        session.AddSource(index, Mix(0, 0, 1, 0));
        if (!withdrawFirst) session.RemoveSource(index, 1, 1);
        session.FinishSubstep(); session.EndTick();
        Close(session.Removed.TotalVolume, 1, "Source withdrawal ledger");
        Close(session.Sample(index).TotalVolume, 1, "Ordered source final physical volume");
        Close(session.Sample(index).GetVolume(0) + session.Removed.GetVolume(0), 1, "Ordered fresh component conservation");
        Close(session.Sample(index).GetVolume(2) + session.Removed.GetVolume(2), 1, "Ordered custom component conservation");
        return session.Sample(index).GetShare(2);
      }
      Close(Run(false), .5, "Addition before drainage mixes existing fresh fluid");
      Close(Run(true), 1, "Drainage before addition leaves only the new fluid");
    });
    scenario("pressure-blocked sources mix only admitted volume and never replace resident components", () => {
      using var fixture = new NativeWaterFixture(managed, specification);
      fixture.AddColumn(1, 1, 1, 0, 1, 0, .5f);
      var session = new NativeFluidTransportSession(fixture.CreateAdapter(), 4, 1);
      int index = fixture.Indices[0];
      var initial = Mix(.5, .5, .5, 0);
      session.SeedComposition(index, initial);
      session.BeginTick(1); fixture.RunAdapterSubstep(session, fixture.ClearRawFlows, new double[1], false);
      session.AddSource(index, Mix(0, 0, 2, 0));
      var admitted = session.Sample(index);
      Close(admitted.GetVolume(0), .5, "Source cap retains existing fresh water");
      Close(admitted.GetVolume(1), .5, "Source cap retains existing badwater");
      Close(admitted.GetVolume(2), 1.875, "Source cap admits only available capacity");
      session.AddSource(index, Mix(0, 20, 0, 0));
      session.AddSource(index, Mix(0, 0, 0, 1e30));
      for (int c = 0; c < 4; c++) {
        Close(session.Sample(index).GetVolume(c), admitted.GetVolume(c), "Fully blocked source cannot recolor a reservoir");
        Close(session.Sample(index).GetVolume(c) + session.PressureLoss.GetVolume(c), initial.GetVolume(c) + session.Added.GetVolume(c),
          "Rejected source component accounting", Math.Max(1, session.Added.GetVolume(c)));
      }
      Close(session.PressureLoss.GetVolume(1), 20, "Rejected badwater remains rejected emission");
      session.FinishSubstep(); session.EndTick();
      bool rejected = false;
      try { session.RemoveSource(index, 1, 0); } catch (InvalidOperationException) { rejected = true; }
      check(rejected, "Source withdrawal outside source stage must fail");
    });
  }
}
