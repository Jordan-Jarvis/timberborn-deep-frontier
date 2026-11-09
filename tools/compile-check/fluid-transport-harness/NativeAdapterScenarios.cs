using ModdableFluids.Native.Prototype;
using ModdableFluids.Transport.Prototype;

internal static class NativeAdapterScenarios {
  internal static void Run(Action<bool, string> check, Action<string, Action> scenario,
      string managed, string specification, Dictionary<string, object> observations) {
    void Close(double actual, double expected, string name, double tolerance = 2e-10) =>
      check(Math.Abs(actual - expected) <= tolerance * Math.Max(Math.Abs(actual), Math.Abs(expected)) + 1e-28,
        name + $": actual {actual:R}, expected {expected:R}");
    void Reject(Action action, string name) {
      bool rejected = false;
      try { action(); } catch (Exception e) when (e is ArgumentException || e is InvalidOperationException) { rejected = true; }
      check(rejected, name + " was accepted");
    }
    FluidVolumes Mix(params double[] volumes) => new(volumes);
    void Balance(NativeFluidTransportSession session, FluidVolumes[] initial, string name) {
      for (int c = 0; c < initial[0].ComponentCount; c++) {
        double actual = session.Removed.GetVolume(c) + session.Evaporated.GetVolume(c) + session.Discharged.GetVolume(c)
          + session.PressureLoss.GetVolume(c) + session.GeometryLoss.GetVolume(c);
        for (int i = 0; i < session.ColumnCount; i++) {
          var mixture = session.Sample(session.GetGeometry(i).NativeIndex);
          check(mixture.GetVolume(c) >= 0 && mixture.GetShare(c) <= 1, name + " invalid component");
          actual += mixture.GetVolume(c);
        }
        Close(actual, initial.Sum(m => m.GetVolume(c)) + session.Added.GetVolume(c), name + " component balance");
      }
    }
    scenario("native adapter enforces two substeps, source stages and queued-change order", () => {
      using var fixture = new NativeWaterFixture(managed, specification);
      fixture.AddColumn(0, 1, 2); fixture.AddColumn(1, 1, 1);
      var session = new NativeFluidTransportSession(fixture.CreateAdapter(), 4, 1);
      var initial = new[] { Mix(1, .5, .5, 0), Mix(.5, 0, 0, .5) };
      for (int i = 0; i < initial.Length; i++) session.SeedComposition(fixture.Indices[i], initial[i]);
      Reject(() => session.AddSource(fixture.Indices[0], Mix(1, 0, 0, 0)), "Source outside native source stage");
      session.BeginTick(2);
      Reject(() => session.RemoveQueued(fixture.Indices[0], 1, 0), "Early queued pump");
      for (int substep = 0; substep < 2; substep++) {
        fixture.RunAdapterSubstep(session, () => { fixture.ClearRawFlows(); fixture.SetRawFlow(0, 1, .25f); }, new double[2], false);
        session.AddSource(fixture.Indices[0], Mix(0, 0, 0, .125));
        Reject(session.EndTick, "End tick before queued changes");
        session.FinishSubstep();
      }
      session.AddQueued(fixture.Indices[1], Mix(.25, 0, 0, 0));
      var removed = session.RemoveQueued(fixture.Indices[1], .5, .125);
      check(removed.Removed.TotalVolume > .5, "Selective pump did not report its actual removal");
      session.EndTick();
      check(session.CompletedTicks == 1 && session.Phase == "Ready", "Native adapter did not finish exactly one tick");
      Balance(session, initial, "two-substep adapter");
      for (int i = 0; i < fixture.Indices.Count; i++) Close(fixture.Contamination(i), session.Sample(fixture.Indices[i]).GetShare(1), "Badwater publication", 2e-6);
    });
    scenario("native adapter uses physical pressure volume and journals capacity loss", () => {
      using var fixture = new NativeWaterFixture(managed, specification);
      fixture.AddColumn(1, 1, 1, 0, 1, 0, .5f);
      var session = new NativeFluidTransportSession(fixture.CreateAdapter(), 4, 1);
      var initial = new[] { Mix(.5, .5, .5, 0) };
      int native = fixture.Indices[0]; session.SeedComposition(native, initial[0]);
      session.BeginTick(1);
      fixture.RunAdapterSubstep(session, fixture.ClearRawFlows, new double[1], false);
      session.AddSource(native, Mix(0, 0, 2, 0));
      Close(session.Sample(native).TotalVolume, 2.875, "Physical pressure capacity");
      Close(session.PressureLoss.TotalVolume, .625, "Measured pressure loss");
      Close(session.Sample(native).GetShare(1), .5 / 2.875, "Only admitted source volume mixes");
      session.FinishSubstep();
      var pump = session.RemoveQueued(native, .75, .25);
      Close(pump.Removed.TotalVolume, 1, "Pressure pump uses physical units");
      session.EndTick(); Balance(session, initial, "pressure source and pump");
      Close(fixture.PhysicalVolume(0), session.Sample(native).TotalVolume, "Physical pressure writeback", 2e-6);
      Close(fixture.Contamination(0), session.Sample(native).GetShare(1), "Pressure badwater writeback", 2e-6);
      observations["adapterPressureLoss"] = session.PressureLoss.TotalVolume;
      using var legacy = new NativeWaterFixture(managed, specification);
      legacy.AddColumn(1, 1, 1, 0, 1, 0, .5f); legacy.SetContamination(0, 1d / 3);
      legacy.ApplyNativeSource(0, 8, 0);
      observations["legacyPressureSourceBadShare"] = legacy.Contamination(0);
      observations["jointPressureSourceBadShare"] = .5 / 2.875;
    });
    scenario("native adapter bounds actual generated full-drain requests at the producer", () => {
      var random = new Random(9017);
      double unmet = 0, largestRepresentation = 0;
      for (int sample = 0; sample < 200; sample++) {
        using var fixture = new NativeWaterFixture(managed, specification);
        float depth = (float)Math.Exp(-random.NextDouble() * 18);
        fixture.AddColumn(1, 1, depth, 4);
        fixture.AddColumn(0, 1, (float)random.NextDouble() * .1f);
        fixture.AddColumn(2, 1, (float)random.NextDouble() * .1f);
        fixture.AddColumn(1, 2, (float)random.NextDouble() * .1f);
        var backend = fixture.CreateAdapter();
        var session = new NativeFluidTransportSession(backend, 4, 1);
        var initial = fixture.Indices.Select((index, i) => {
          double volume = fixture.PhysicalVolume(i);
          var mixture = Mix(volume / 4, volume / 4, volume / 4, volume / 4);
          session.SeedComposition(index, mixture); return mixture;
        }).ToArray();
        session.BeginTick(1);
        fixture.RunAdapterSubstep(session, () => { fixture.ClearRawFlows(); fixture.GenerateNativeFlows(); }, new double[4], false);
        session.FinishSubstep(); session.EndTick();
        Balance(session, initial, "native generated drain " + sample);
        unmet += backend.LastUnfulfilledFlowDemand;
        largestRepresentation = Math.Max(largestRepresentation, session.MaxRepresentationDifference);
      }
      check(unmet > 0, "Generated flows did not exercise the physical donor limiter");
      observations["fullDrainUnfulfilledDemand"] = unmet;
      observations["fullDrainMaxFloatRepresentationDifference"] = largestRepresentation;
    });
    scenario("native adapter publishes conservative diffusion instead of overfull native shares", () => {
      using var fixture = new NativeWaterFixture(managed, specification);
      fixture.AddColumn(1, 1, 1); fixture.AddColumn(0, 1, 1); fixture.AddColumn(2, 1, 1); fixture.AddColumn(1, 2, 1);
      var session = new NativeFluidTransportSession(fixture.CreateAdapter(), 4, 1);
      var initial = new[] { Mix(0, .5, .5, 0), Mix(0, 1, 0, 0), Mix(0, 1, 0, 0), Mix(0, 1, 0, 0) };
      for (int i = 0; i < initial.Length; i++) session.SeedComposition(fixture.Indices[i], initial[i]);
      session.BeginTick(1);
      fixture.RunAdapterSubstep(session, () => {
        fixture.ClearRawFlows(); for (int i = 1; i < 4; i++) fixture.SetRawFlow(0, i, 1f / 65536);
      }, new double[4], true);
      session.FinishSubstep(); session.EndTick(); Balance(session, initial, "adapter diffusion");
      for (int i = 0; i < 4; i++) Close(fixture.Contamination(i), session.Sample(fixture.Indices[i]).GetShare(1), "Joint share overwrote independent native result", 2e-6);
    });
    scenario("geometry projection handles splits, merges, floors and pressure storage", () => {
      var before = new[] { new FluidColumnGeometry(12, 12, 0, 6, 7) };
      var original = new[] { Mix(1, 1, 2, 0) };
      var split = FluidGeometryTransport.Remap(before, original, new[] {
        new FluidColumnGeometry(12, 12, 0, 2, 3), new FluidColumnGeometry(37, 12, 3, 6, 4)
      }, 4);
      Close(split.GeometryLoss.TotalVolume, 1, "Full obstacle displaced exactly one layer");
      Close(split.GetColumn(0).TotalVolume, 2, "Lower split volume"); Close(split.GetColumn(1).TotalVolume, 1, "Upper split volume");
      var merged = FluidGeometryTransport.Remap(new[] {
        new FluidColumnGeometry(12, 12, 0, 2, 3), new FluidColumnGeometry(37, 12, 3, 6, 4)
      }, new[] { Mix(0, 0, 0, 2.5), Mix(1, 1, 0, 1.5) }, new[] { new FluidColumnGeometry(12, 12, 0, 6, 7) }, 4);
      Close(merged.GetColumn(0).TotalVolume, 6, "Merge retained both parents' pressure storage");
      Close(merged.GetColumn(0).GetVolume(3), 4, "Merge composition");
      Close(merged.GeometryLoss.TotalVolume, 0, "Merge geometry loss");
      var raised = FluidGeometryTransport.Remap(before, original, new[] { new FluidColumnGeometry(12, 12, 1, 6, 6) }, 4);
      Close(raised.GeometryLoss.TotalVolume, 1, "Raised floor displacement");
      var tiny = FluidGeometryTransport.Remap(new[] { new FluidColumnGeometry(12, 12, 100, 101, 2) }, new[] { Mix(1e-35, 0, 0, 0) },
        new[] { new FluidColumnGeometry(12, 12, 100, 101, 2) }, 4);
      Close(tiny.GetColumn(0).TotalVolume, 1e-35, "Tiny film at a high floor retained");
      Reject(() => FluidGeometryTransport.Remap(before, original, new[] { new FluidColumnGeometry(12, 12, 0, 4, 5), new FluidColumnGeometry(37, 12, 3, 6, 4) }, 4), "Overlapping geometry");
    });
    scenario("native adapter reconciles changed arrays and prevents unannounced geometry changes", () => {
      using var fixture = new NativeWaterFixture(managed, specification);
      fixture.AddColumn(1, 1, 4, 0, 6);
      var session = new NativeFluidTransportSession(fixture.CreateAdapter(), 4, 1);
      var initial = new[] { Mix(1, 1, 2, 0) };
      session.SeedComposition(fixture.Indices[0], initial[0]);
      fixture.SetColumnGeometry(0, 0, 2, 2, 0); fixture.AddColumn(1, 1, 1, 3, 6, 1);
      Reject(() => session.BeginTick(1), "Unannounced native split");
      var remap = session.ReconcileGeometry(fixture.CreateAdapter());
      Close(remap.GeometryLoss.TotalVolume, 1, "Reconciled split displacement"); Balance(session, initial, "native array split");
      for (int i = 0; i < 2; i++) Close(session.Sample(fixture.Indices[i]).TotalVolume, fixture.PhysicalVolume(i), "Reconciled native split depth", 2e-6);
      fixture.SetColumnGeometry(0, 0, 6, 3, 0); fixture.SetColumnGeometry(1, 6, 6, 0, 0);
      session.ReconcileGeometry(fixture.CreateAdapter()); Balance(session, initial, "native array merge");
      Close(session.Sample(fixture.Indices[0]).TotalVolume, 3, "Merged volume");
      fixture.SetColumnGeometry(0, 6, 6, 0, 0);
      session.ReconcileGeometry(fixture.CreateAdapter()); Balance(session, initial, "fully blocked cell");
      check(session.ColumnCount == 0, "Fully blocked cell retained an open fluid column");
    });
    scenario("native adapter faults visibly on a failed native task", () => {
      using var fixture = new NativeWaterFixture(managed, specification);
      fixture.AddColumn(1, 1, 1);
      var session = new NativeFluidTransportSession(fixture.CreateAdapter(), 4, 1);
      session.BeginTick(1);
      Reject(() => session.RunSubstep(() => throw new InvalidOperationException("fixture task failed"), () => new double[1],
        () => Array.Empty<FluidDiffusionLink>(), .25, 0), "Failed task");
      check(session.Phase == "Faulted", "Failed native task did not fault the session");
      Reject(session.FinishSubstep, "Continue after failed task");
    });
    scenario("physical capacity retains small reservoirs after very large additions", () => {
      var limited = FluidTransportPrototype.LimitCapacity(Mix(0, 0, 1e30, 0), 2.875);
      Close(limited.Remaining.TotalVolume, 2.875, "Direct retained pressure capacity");
      Close(limited.Removed.TotalVolume + limited.Remaining.TotalVolume, 1e30, "Large addition accounting");
      using var fixture = new NativeWaterFixture(managed, specification);
      fixture.AddColumn(1, 1, 1, 0, 1);
      var session = new NativeFluidTransportSession(fixture.CreateAdapter(), 4, 1);
      session.BeginTick(1); fixture.RunAdapterSubstep(session, fixture.ClearRawFlows, new double[1], false);
      session.AddSource(fixture.Indices[0], Mix(0, 0, 1e30, 0));
      session.FinishSubstep(); session.EndTick();
      Close(session.Sample(fixture.Indices[0]).TotalVolume, 2.875, "Native bounded large source");
      Close(fixture.PhysicalVolume(0), 2.875, "Native capacity publication after large source");
      var random = new Random(909);
      var geometry = new[] { new FluidColumnGeometry(12, 12, 0, 1, 2.875) };
      for (int i = 0; i < 100; i++) {
        var input = new FluidVolumes(Enumerable.Range(0, 64).Select(_ => random.NextDouble() * 100).ToArray());
        var capped = FluidTransportPrototype.LimitCapacity(input, 2.875).Remaining;
        var remapped = FluidGeometryTransport.Remap(geometry, new[] { capped }, geometry, 64);
        Close(remapped.GetColumn(0).TotalVolume + remapped.PressureLoss.TotalVolume, capped.TotalVolume, "64-component capacity and remap accounting");
      }
    });
    scenario("actual native queued obstacle mutations drive composition remapping", () => {
      using var fixture = new NativeWaterFixture(managed, specification);
      fixture.AddColumn(1, 1, 4, 0, 6);
      var session = new NativeFluidTransportSession(fixture.CreateAdapter(), 4, 1);
      var initial = new[] { Mix(1, 1, 2, 0) };
      session.SeedComposition(fixture.Indices[0], initial[0]);
      fixture.ApplyQueuedNativeObstacle("AddHorizontalObstacle", 0, 2);
      check(fixture.Indices.Count == 2, "Native queued horizontal obstacle did not split the column");
      session.ReconcileGeometry(fixture.CreateAdapter()); Balance(session, initial, "queued native horizontal split");
      Close(session.GeometryLoss.TotalVolume, 0, "Horizontal obstacle has no physical thickness");
      fixture.ApplyQueuedNativeObstacle("RemoveHorizontalObstacle", 0, 2);
      check(fixture.Indices.Count == 1, "Native queued horizontal removal did not merge columns");
      session.ReconcileGeometry(fixture.CreateAdapter()); Balance(session, initial, "queued native horizontal merge");
      fixture.ApplyQueuedNativeObstacle("AddFullObstacle", 0, 1);
      session.ReconcileGeometry(fixture.CreateAdapter()); Balance(session, initial, "queued native full split");
      Close(session.GeometryLoss.TotalVolume, 1, "Queued solid displaced one physical layer");
      fixture.ApplyQueuedNativeObstacle("RemoveFullObstacle", 0, 1);
      session.ReconcileGeometry(fixture.CreateAdapter()); Balance(session, initial, "queued native full merge");
      Close(session.Sample(fixture.Indices[0]).TotalVolume, 3, "Removing solid did not create fluid");
    });
    scenario("native merge preserves upper pressure water through shared geometry authority", () => {
      using var fixture = new NativeWaterFixture(managed, specification);
      fixture.AddColumn(1, 1, 2, 0, 2, 0, .5f); fixture.AddColumn(1, 1, 3, 3, 6, 1, .5f);
      var session = new NativeFluidTransportSession(fixture.CreateAdapter(), 4, 1);
      var initial = new[] { Mix(0, 0, 0, 2.5), Mix(1, 1, 0, 1.5) };
      session.SeedComposition(fixture.Indices[0], initial[0]); session.SeedComposition(fixture.Indices[1], initial[1]);
      fixture.ApplyQueuedNativeObstacle("RemoveFullObstacle", 0, 2);
      double nativeBeforeRemap = fixture.PhysicalVolume(0);
      session.ReconcileGeometry(fixture.CreateAdapter());
      Balance(session, initial, "native pressure merge");
      Close(session.Sample(fixture.Indices[0]).TotalVolume, 6, "Shared geometry retained upper pressure storage");
      observations["nativePressureMergeBeforeRemap"] = nativeBeforeRemap;
      observations["jointPressureMergeAfterRemap"] = session.Sample(fixture.Indices[0]).TotalVolume;
      check(nativeBeforeRemap < 6, "Native pressure merge did not exercise lost upper overflow");
    });
  }
}
