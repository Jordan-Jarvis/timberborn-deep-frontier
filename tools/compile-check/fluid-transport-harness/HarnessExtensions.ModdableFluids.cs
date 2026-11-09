using ModdableFluids;
using ModdableFluids.Native.Prototype;
using ModdableFluids.Transport.Prototype;
using ModdableFluids.World.Prototype;
using static RegistryScenarios;

/// <summary>
/// Moddable Fluids 0.1.4 core: per-tick loss reports, extraction requests, water-intake and irrigation policies,
/// the guard and moisture decisions, and the exception-save snapshot (pure parts; native types run in the Mono probe).
/// </summary>
internal static partial class HarnessExtensions {
  static partial void RunModdableFluids(Action<bool, string> check, Action<string, Action> scenario, string managed, string specification, Dictionary<string, object> observations) {
    void Close(double actual, double expected, string name, double tolerance = 2e-10) =>
      check(Math.Abs(actual - expected) <= tolerance * Math.Max(Math.Abs(actual), Math.Abs(expected)) + 1e-28, name + $": actual {actual:R}, expected {expected:R}");
    void Rejects<T>(Action action, string name, string? message = null) where T : Exception {
      Exception? caught = null;
      try { action(); } catch (Exception e) { caught = e; }
      check(caught is T && (message == null || caught.Message.Contains(message)),
        name + $": expected {typeof(T).Name}{(message == null ? "" : " containing '" + message + "'")}, got {caught?.GetType().Name ?? "no exception"}: {caught?.Message}");
    }
    FluidVolumes Mix(params double[] volumes) => new(volumes);
    FluidRegistry CoffeeRegistry(Action<FluidRegistration>? extra = null) {
      var host = new ModdableFluidsHost();
      host.RegisterProvider(new PlainProvider("MoreFluids.Liquids", "MoreFluids", new List<string>(), new Fluid("Coffee", "MoreFluids.Coffee")) { Extra = extra });
      return host.Freeze();
    }
    int SlotOf(NativeFluidTransportSession session, int x, int y, int z) =>
      Enumerable.Range(0, session.ColumnCount).Single(s => { var g = session.GetGeometry(s); return g.CellIndex == (y + 1) * NativeWaterFixture.Stride + x + 1 && z >= g.Floor && z < g.Ceiling; });
    bool FindColumn(NativeFluidTransportSession session, int x, int y, int z, out int nativeIndex) {
      for (int s = 0; s < session.ColumnCount; s++) {
        var g = session.GetGeometry(s);
        if (g.CellIndex == (y + 1) * NativeWaterFixture.Stride + x + 1 && z >= g.Floor && z < g.Ceiling) { nativeIndex = g.NativeIndex; return true; }
      }
      nativeIndex = -1; return false;
    }
    double LedgerTotal(NativeFluidTransportSession s, int c) => s.Removed.GetVolume(c) + s.Evaporated.GetVolume(c) + s.Discharged.GetVolume(c)
      + s.PressureLoss.GetVolume(c) + s.GeometryLoss.GetVolume(c) + s.Extracted.GetVolume(c);
    void Conserve(NativeFluidTransportSession session, FluidVolumes[] initial, string name) {
      for (int c = 0; c < initial[0].ComponentCount; c++) {
        double actual = LedgerTotal(session, c);
        for (int i = 0; i < session.ColumnCount; i++) actual += session.Sample(session.GetGeometry(i).NativeIndex).GetVolume(c);
        Close(actual, initial.Sum(m => m.GetVolume(c)) + session.Added.GetVolume(c), name + " conservation of component " + c);
      }
    }

    scenario("per-tick losses name every place, reason and fluid that lost volume", () => {
      var registry = CoffeeRegistry();
      var coffee = registry.GetHandle("MoreFluids.Coffee");
      using var fixture = new NativeWaterFixture(managed, specification);
      int a = fixture.AddColumn(0, 1, 2), b = fixture.AddColumn(1, 1, 1, 0, 6), c = fixture.AddColumn(2, 1, 1, 0, 1, 0, .5f);
      var session = new NativeFluidTransportSession(fixture.CreateAdapter(), registry.Count, FluidRegistry.BadwaterIndex);
      var initial = new[] { Mix(1, .5, .5), Mix(.5, 0, .5), Mix(.5, .5, .5) };
      for (int i = 0; i < 3; i++) session.SeedComposition(fixture.Indices[i], initial[i]);
      check(new FluidColumnEditor(session, registry, NativeWaterFixture.Stride).Losses.Count == 0, "Losses before the first completed tick");
      session.BeginTick(1);
      fixture.RunAdapterSubstep(session, () => { fixture.ClearRawFlows(); fixture.SetRawEdgeFlow(a, "Left", .25f); }, new[] { 0, .1, 0 }, false);
      session.AddSource(fixture.Indices[c], Mix(0, 0, 2));
      session.RemoveSource(fixture.Indices[b], 0, .2, 0);
      Rejects<ArgumentOutOfRangeException>(() => session.RemoveSource(fixture.Indices[b], 6, .1, 0), "Withdrawal at a height outside its column");
      session.FinishSubstep();
      session.AddQueued(fixture.Indices[b], Mix(.25, 0, 0));
      session.RemoveQueued(fixture.Indices[b], 3, .3, 0);
      double extracted = session.Extract(fixture.Indices[a], 1, coffee.Index, .1, .1, "MoreFluids.Test", out double share);
      Close(extracted, .1, "Extracted coffee"); check(share > .1, "Coffee share before the extraction");
      session.RecordDroppedAddition((2 + 1) * NativeWaterFixture.Stride + 1 + 1, 0, Mix(0, 0, .3));
      Rejects<InvalidOperationException>(() => session.RecordDroppedAddition((1 + 1) * NativeWaterFixture.Stride + 1 + 1, 0, Mix(0, 0, .3)), "A dropped addition where a column is open");
      session.EndTick();
      Conserve(session, initial, "loss tick");
      var editor = new FluidColumnEditor(session, registry, NativeWaterFixture.Stride);
      var losses = editor.Losses;
      check(ReferenceEquals(losses, editor.Losses), "The loss list is built once per editor");
      FluidLoss One(FluidLossKind kind) {
        var matching = losses.Where(l => l.Kind == kind).ToArray();
        check(matching.Length == 1, kind + ": expected one entry, found " + matching.Length);
        return matching[0];
      }
      var evaporation = One(FluidLossKind.Evaporation);
      check(evaporation.X == 1 && evaporation.Y == 1 && evaporation.Z == 0 && evaporation.Column == SlotOf(session, 1, 1, 0) && evaporation.RequesterId == null, "Evaporation place");
      Close(evaporation.TotalVolume, session.Evaporated.TotalVolume, "Evaporation volume"); check(evaporation.TotalVolume > .09, "Native evaporation ran");
      var discharge = One(FluidLossKind.Discharge);
      check(discharge.X == 0 && discharge.Y == 1 && discharge.Z == 0 && discharge.Column == SlotOf(session, 0, 1, 0), "Discharge place");
      Close(discharge.TotalVolume, .25, "Discharged volume", 1e-6); Close(discharge.GetVolume(coffee), discharge.TotalVolume * .25, "Discharge carries the donor's coffee share");
      var pressure = One(FluidLossKind.Pressure);
      check(pressure.X == 2 && pressure.Y == 1 && pressure.Column == SlotOf(session, 2, 1, 0), "Pressure place");
      Close(pressure.GetVolume(coffee), .625, "A blocked source loses only its own emission"); Close(pressure.GetVolume(registry.Water), 0, "Resident water kept");
      var withdrawal = One(FluidLossKind.SourceWithdrawal);
      check(withdrawal.X == 1 && withdrawal.Z == 0, "Withdrawal place"); Close(withdrawal.TotalVolume, .2, "Withdrawn volume");
      var removal = One(FluidLossKind.NativeRemoval);
      check(removal.X == 1 && removal.Y == 1 && removal.Z == 3 && removal.Column == SlotOf(session, 1, 1, 3), "Native removal keeps the requested cell height");
      Close(removal.TotalVolume, .3, "Native removal volume"); check(removal.GetVolume(coffee) > 0, "A clean-water removal drew coffee");
      var extraction = One(FluidLossKind.Extraction);
      check(extraction.RequesterId == "MoreFluids.Test" && extraction.X == 0 && extraction.Z == 1, "Extraction place and requester");
      Close(extraction.GetVolume(coffee), .1, "Extraction removed coffee"); Close(extraction.TotalVolume, .1, "Extraction removed nothing else");
      var dropped = One(FluidLossKind.DroppedAddition);
      check(dropped.X == 1 && dropped.Y == 2 && dropped.Z == 0 && dropped.Column == -1, "Dropped addition place"); Close(dropped.GetVolume(coffee), .3, "Dropped coffee");
      check(losses.Select(l => (int)l.Kind).SequenceEqual(losses.Select(l => (int)l.Kind).OrderBy(k => k)), "Losses ordered by kind");
      for (int k = 0; k < registry.Count; k++) {
        var handle = k == 0 ? registry.Water : k == 1 ? registry.Badwater : coffee;
        Close(losses.Sum(l => l.GetVolume(handle)), LedgerTotal(session, k) + session.Dropped.GetVolume(k), "Losses add up to the session ledgers, component " + k);
      }
      editor.Close();
      Rejects<InvalidOperationException>(() => _ = editor.Losses, "Reading losses after the rules returned");
      // Rules see the same report on the completed tick (Deep Frontier's deposition pattern).
      var host = new ModdableFluidsHost();
      var reader = new LossReader();
      host.RegisterProvider(new PlainProvider("MoreFluids.Liquids", "MoreFluids", new List<string>(), new Fluid("Coffee", "MoreFluids.Coffee")));
      host.RegisterProvider(reader);
      var rulesRegistry = host.Freeze();
      var scene = host.ActivateScene();
      var rulesEditor = new FluidColumnEditor(session, rulesRegistry, NativeWaterFixture.Stride);
      host.ApplyColumnRules(scene, rulesEditor); rulesEditor.Close();
      Close(reader.Deposited, 10 * (evaporation.GetVolume(coffee) + dropped.GetVolume(coffee)), "A rule read evaporated and dropped coffee from the report");
      observations["lossKindsInOneTick"] = losses.Count;
    });

    scenario("geometry losses keep the old column's place and belong to the tick they start", () => {
      var registry = CoffeeRegistry();
      var coffee = registry.GetHandle("MoreFluids.Coffee");
      using var fixture = new NativeWaterFixture(managed, specification);
      fixture.AddColumn(1, 1, 4, 0, 6);
      var session = new NativeFluidTransportSession(fixture.CreateAdapter(), registry.Count, FluidRegistry.BadwaterIndex);
      var initial = new[] { Mix(1, 1, 2) };
      session.SeedComposition(fixture.Indices[0], initial[0]);
      fixture.ApplyQueuedNativeObstacle("AddFullObstacle", 0, 1);
      session.ReconcileGeometry(fixture.CreateAdapter());
      session.BeginTick(1); fixture.RunAdapterSubstep(session, fixture.ClearRawFlows, new double[session.ColumnCount], false);
      session.FinishSubstep(); session.EndTick();
      Conserve(session, initial, "geometry tick");
      var losses = new FluidColumnEditor(session, registry, NativeWaterFixture.Stride).Losses;
      var geometry = losses.Single(l => l.Kind == FluidLossKind.Geometry);
      check(geometry.X == 1 && geometry.Y == 1 && geometry.Z == 0 && geometry.Column == -1, "Geometry loss at the old column's (x, y, floor)");
      Close(geometry.TotalVolume, 1, "One solid layer displaced"); Close(geometry.GetVolume(coffee), .5, "Displaced in proportion");
      session.BeginTick(1); fixture.RunAdapterSubstep(session, fixture.ClearRawFlows, new double[session.ColumnCount], false);
      session.FinishSubstep(); session.EndTick();
      check(new FluidColumnEditor(session, registry, NativeWaterFixture.Stride).Losses.All(l => l.Kind != FluidLossKind.Geometry), "A geometry loss repeated in the next tick");
      // Merging into a smaller pressure capacity reports pressure on the new column; a vanished column loses everything.
      var merged = FluidGeometryTransport.Remap(new[] { new FluidColumnGeometry(12, 12, 0, 2, 2.5), new FluidColumnGeometry(37, 12, 3, 6, 4) },
        new[] { Mix(0, 0, 2.5), Mix(1, 1, 2) }, new[] { new FluidColumnGeometry(12, 12, 0, 6, 6) }, 3);
      Close(merged.GetPressureLoss(0).TotalVolume, .5, "Merge pressure on the new column"); Close(merged.GetGeometryLoss(0).TotalVolume + merged.GetGeometryLoss(1).TotalVolume, 0, "No merge displacement");
      var vanished = FluidGeometryTransport.Remap(new[] { new FluidColumnGeometry(12, 12, 0, 2, 2.5) }, new[] { Mix(.5, 0, 1) }, Array.Empty<FluidColumnGeometry>(), 3);
      Close(vanished.GetGeometryLoss(0).GetVolume(2), 1, "A vanished column loses all its coffee");
      var step = FluidTransportPrototype.Advect(new[] { Mix(1, 0, 1), Mix(1, 0, 0) }, new[] { new FluidTransfer(0, -1, .5), new FluidTransfer(1, 0, .5) }, new double[2]);
      check(step.GetDischarged(1) == null && Math.Abs(step.GetDischarged(0).GetVolume(2) - .25) < 1e-15, "Per-column discharge from the donor's snapshot");
    });

    scenario("extraction requests remove only their fluid and report what they drew", () => {
      var registry = CoffeeRegistry();
      var coffee = registry.GetHandle("MoreFluids.Coffee");
      var queue = new FluidExtractionQueue(registry, NativeWaterFixture.Width, NativeWaterFixture.Height);
      var delivered = new List<IFluidExtractionRequest>();
      void Take(IFluidExtractionRequest r) => delivered.Add(r);
      Rejects<ArgumentException>(() => queue.Request("Extractor", 0, 1, 0, coffee, .1, 0, Take), "Requester outside a namespace");
      Rejects<ArgumentOutOfRangeException>(() => queue.Request("MoreFluids.X", 3, 1, 0, coffee, .1, 0, Take), "Cell outside the map");
      Rejects<ArgumentOutOfRangeException>(() => queue.Request("MoreFluids.X", 0, 1, 0, coffee, 0, 0, Take), "Zero volume");
      Rejects<ArgumentOutOfRangeException>(() => queue.Request("MoreFluids.X", 0, 1, 0, coffee, double.PositiveInfinity, 0, Take), "Infinite volume");
      Rejects<ArgumentOutOfRangeException>(() => queue.Request("MoreFluids.X", 0, 1, 0, coffee, .1, double.NaN, Take), "NaN minimum share");
      Rejects<ArgumentNullException>(() => queue.Request("MoreFluids.X", 0, 1, 0, coffee, .1, 0, null!), "No result callback");
      Rejects<ArgumentException>(() => queue.Request("MoreFluids.X", 0, 1, 0, CoffeeRegistry(r => r.AddFluid("Tea", "MoreFluids.Tea", .5f, .5f, .5f, 1)).GetHandle("MoreFluids.Coffee"), .1, 0, Take), "A handle from a registry with other content");
      using var fixture = new NativeWaterFixture(managed, specification);
      int a = fixture.AddColumn(0, 1, 2), b = fixture.AddColumn(1, 1, 1), c = fixture.AddColumn(2, 1, 1);
      var session = new NativeFluidTransportSession(fixture.CreateAdapter(), registry.Count, FluidRegistry.BadwaterIndex);
      var initial = new[] { Mix(1, .5, .5), Mix(.95, 0, .05), Mix(.5, .25, .25) };
      for (int i = 0; i < 3; i++) session.SeedComposition(fixture.Indices[i], initial[i]);
      var first = queue.Request("MoreFluids.FluidExtractor", 0, 1, 0, coffee, .1, .1, Take);
      var all = queue.Request("MoreFluids.FluidExtractor", 0, 1, 1, coffee, 5, 0, Take);
      var dilute = queue.Request("MoreFluids.FluidExtractor", 1, 1, 0, coffee, .1, .1, Take);
      var closed = queue.Request("MoreFluids.FluidExtractor", 2, 2, 0, coffee, .1, 0, Take);
      var water = queue.Request("MoreFluids.Desalinator", 2, 1, 0, registry.Water, .2, 0, Take);
      check(first.Outcome == FluidExtractionOutcome.Pending && first.ResolvedTick == 0, "Pending before the change stage");
      Rejects<InvalidOperationException>(() => _ = first.ExtractedVolume, "Reading a pending result");
      var batch = queue.TakeBatch();
      var later = queue.Request("MoreFluids.FluidExtractor", 0, 1, 0, coffee, .1, 0, Take);
      check(batch.Length == 5 && queue.Queued == 1, "A request after the tick was scheduled waits for the next tick");
      session.BeginTick(1); fixture.RunAdapterSubstep(session, fixture.ClearRawFlows, new double[3], false); session.FinishSubstep();
      queue.Resolve(batch, session, (int x, int y, int z, out int index) => FindColumn(session, x, y, z, out index));
      session.EndTick();
      check(delivered.Count == 0 && queue.AwaitingDelivery == 5, "Results wait for the main-thread delivery");
      check(queue.DeliverResolved() == 5 && delivered.SequenceEqual(new IFluidExtractionRequest[] { first, all, dilute, closed, water }), "Delivered once each, in request order");
      check(queue.DeliverResolved() == 0, "Delivered twice");
      check(first.Outcome == FluidExtractionOutcome.Extracted && first.ResolvedTick == 1, "First extraction resolved in tick 1");
      Close(first.ExtractedVolume, .1, "First extraction volume"); Close(first.ShareAtResolution, .25, "Share before the first extraction");
      Close(all.ExtractedVolume, .4, "An oversized request takes all the coffee there is");
      var columnA = session.Sample(fixture.Indices[a]);
      check(columnA.GetVolume(coffee.Index) == 0, "Taking all the coffee leaves exactly zero");
      Close(columnA.GetVolume(0), 1, "Extraction left the water"); Close(columnA.GetVolume(1), .5, "Extraction left the badwater");
      Close(fixture.PhysicalVolume(a), 1.5, "Native depth follows the extraction", 1e-6);
      check(dilute.Outcome == FluidExtractionOutcome.BelowMinimumShare && dilute.ExtractedVolume == 0, "Too dilute: nothing removed");
      Close(session.Sample(fixture.Indices[b]).GetVolume(coffee.Index), .05, "Too dilute column kept its coffee");
      check(closed.Outcome == FluidExtractionOutcome.NoColumn && closed.ExtractedVolume == 0 && closed.ShareAtResolution == 0, "No column: nothing removed");
      check(water.Outcome == FluidExtractionOutcome.Extracted && water.Fluid.Equals(registry.Water), "Water extraction");
      Close(water.ExtractedVolume, .2, "Water extracted"); Close(session.Sample(fixture.Indices[c]).GetVolume(coffee.Index), .25, "Water extraction left the coffee");
      Close(session.Extracted.TotalVolume, .7, "Extraction ledger");
      Conserve(session, initial, "extraction tick");
      var report = new FluidColumnEditor(session, registry, NativeWaterFixture.Stride).Losses.Where(l => l.Kind == FluidLossKind.Extraction).ToArray();
      check(report.Length == 3 && report.Select(l => l.RequesterId).SequenceEqual(new[] { "MoreFluids.FluidExtractor", "MoreFluids.FluidExtractor", "MoreFluids.Desalinator" }),
        "One extraction loss per place and requester");
      queue.Close();
      check(queue.Queued == 0 && later.Outcome == FluidExtractionOutcome.Pending, "Unload dropped the unresolved request without a result");
      Rejects<InvalidOperationException>(() => queue.Request("MoreFluids.X", 0, 1, 0, coffee, .1, 0, Take), "A request after unload");
      observations["extractionCoffeeShareBefore"] = first.ShareAtResolution;
    });

    scenario("an exception save writes the last published tick and its load takes native water as authoritative", () => {
      var registry = CoffeeRegistry();
      var coffee = registry.GetHandle("MoreFluids.Coffee");
      using var saved = new NativeWaterFixture(managed, specification);
      saved.AddColumn(0, 1, 2); saved.AddColumn(1, 1, 1);
      var session = new NativeFluidTransportSession(saved.CreateAdapter(), registry.Count, FluidRegistry.BadwaterIndex);
      session.SeedComposition(saved.Indices[0], Mix(1, .5, .5)); session.SeedComposition(saved.Indices[1], Mix(.5, 0, .5));
      var world = new FluidWorldState(registry, NativeWaterFixture.Stride);
      check(!world.TryGetPublished(out _, out _, out _), "Nothing published before the first substep");
      world.Publish(session);
      session.BeginTick(1);
      saved.RunAdapterSubstep(session, () => { saved.ClearRawFlows(); saved.SetRawFlow(0, 1, .5f); }, new double[2], false);
      // Mid-tick: the session moved on, the published tick did not.
      check(world.TryGetPublished(out var layout, out var mixtures, out int ticks) && ticks == 0, "The published tick during a running tick");
      Close(mixtures[0].GetVolume(coffee.Index), .5, "Published mixture unchanged mid-tick");
      var document = ModdableFluids.Persistence.Prototype.FluidWorldPersistence.Capture(registry, layout, mixtures, NativeWaterFixture.Stride, Array.Empty<FluidProviderState>());
      check(document.ColumnCount == 2, "Snapshot document columns");
      Rejects<ArgumentException>(() => ModdableFluids.Persistence.Prototype.FluidWorldPersistence.Capture(registry, layout, mixtures.Take(1).ToArray(), NativeWaterFixture.Stride, Array.Empty<FluidProviderState>()), "Mismatched snapshot arrays");
      // The native arrays were saved mid-tick: A grew and holds badwater, B is unchanged, C is new.
      using var native = new NativeWaterFixture(managed, specification);
      native.AddColumn(0, 1, 2.5f); native.AddColumn(1, 1, 1); native.AddColumn(2, 1, .5f);
      native.SetContamination(0, .3); native.SetContamination(2, .5);
      var strict = new NativeFluidTransportSession(native.CreateAdapter(), registry.Count, FluidRegistry.BadwaterIndex);
      var nativeLayout = Enumerable.Range(0, strict.ColumnCount).Select(strict.GetGeometry).ToArray();
      var restored = ModdableFluids.Persistence.Prototype.FluidWorldPersistence.Restore(document, registry, nativeLayout, NativeWaterFixture.Stride, NativeWaterFixture.Height);
      Rejects<FluidSaveException>(() => ModdableFluids.Persistence.Prototype.FluidWorldPersistence.Apply(strict, registry, restored, NativeWaterFixture.Stride), "A normal load of a mid-tick native save");
      var lenient = new NativeFluidTransportSession(native.CreateAdapter(), registry.Count, FluidRegistry.BadwaterIndex);
      var adjustment = ModdableFluids.Persistence.Prototype.FluidWorldPersistence.ApplySnapshot(lenient, registry, restored, NativeWaterFixture.Stride);
      check(adjustment.AdjustedColumns.SequenceEqual(new[] { "(0, 1, floor 0)", "(2, 1, floor 0)" }), "Adjusted columns reported: " + string.Join("; ", adjustment.AdjustedColumns));
      var a = lenient.Sample(native.Indices[0]);
      Close(a.TotalVolume, 2.5, "Native volume wins", 1e-6); Close(a.GetVolume(1), .75, "Native badwater share wins", 1e-6);
      Close(a.GetVolume(coffee.Index) / a.GetVolume(0), .5, "The snapshot's non-bad composition is kept");
      var b = lenient.Sample(native.Indices[1]);
      Close(b.GetVolume(coffee.Index), .5, "An unchanged column is the snapshot's"); Close(b.GetVolume(0), .5, "Unchanged column water");
      var c = lenient.Sample(native.Indices[2]);
      Close(c.GetVolume(0), .25, "A column the snapshot lacks is native fresh water", 1e-6); Close(c.GetVolume(coffee.Index), 0, "No coffee invented");
      Close(adjustment.AbsoluteDifference.GetVolume(1), (.75 - .5) + .25, "Reported badwater change", 1e-6);
      observations["snapshotAdjustedColumns"] = adjustment.AdjustedColumns.Count;
    });

    scenario("water-intake and irrigation policies are registered, validated and required before a game attaches", () => {
      void Policies(FluidRegistration r) {
        r.AddFluid("Saltwater", "MoreFluids.Saltwater", .15f, .45f, .55f, .35f);
        r.SetWaterIntakePolicy("Coffee", .5, "MoreFluids.CoffeeDrunkAsWater", "MoreFluids.Coffee.IntakeRefused", "MoreFluids.Coffee.IntakeRefusedAlert");
        r.SetIrrigatesLikeWater("Coffee");
        r.SetWaterIntakePolicy("Saltwater", .1, "MoreFluids.BrackishDrawnAsWater", "MoreFluids.Saltwater.IntakeRefused", "MoreFluids.Saltwater.IntakeRefusedAlert");
        r.SetBlocksMoisture("Saltwater", .1);
      }
      var registry = CoffeeRegistry(Policies);
      var coffee = registry.Get(registry.GetHandle("MoreFluids.Coffee")); var salt = registry.Get(registry.GetHandle("MoreFluids.Saltwater"));
      check(coffee.WaterIntake!.RefuseAtShare == .5 && coffee.WaterIntake.DrawnAsWater == "MoreFluids.CoffeeDrunkAsWater" && coffee.WaterIntake.RefusedAlertLocKey == "MoreFluids.Coffee.IntakeRefusedAlert",
        "Coffee water-intake policy");
      check(coffee.Irrigation!.Effect == FluidMoistureEffect.IrrigatesLikeWater && coffee.Irrigation.BlocksAtShare == 0, "Coffee irrigates");
      check(salt.Irrigation!.Effect == FluidMoistureEffect.BlocksLikeBadwater && salt.Irrigation.BlocksAtShare == .1 && salt.WaterIntake!.RefuseAtShare == .1, "Saltwater policies");
      check(registry.Get(registry.Water).WaterIntake == null && registry.Get(registry.Badwater).Irrigation == null, "The game's fluids keep native behaviour");
      check(registry.UndeclaredPolicies().Count == 0 && registry.HasExtraFluids, "Every fluid declared");
      var bare = CoffeeRegistry();
      var missing = bare.UndeclaredPolicies();
      check(missing.Count == 1 && missing[0].Contains("MoreFluids.Coffee") && missing[0].Contains("provider MoreFluids.Liquids") && missing[0].Contains("mod MoreFluids")
        && missing[0].Contains("water-intake policy") && missing[0].Contains("irrigation policy"), "Undeclared policies named: " + string.Join("; ", missing));
      check(!new ModdableFluidsHost().Freeze().HasExtraFluids, "Water and badwater alone");
      void Refused(Action<FluidRegistration> extra, string expected, string name) =>
        Rejects<FluidRegistryException>(() => CoffeeRegistry(extra), name, expected);
      Refused(r => r.SetWaterIntakePolicy("Coffee", 0, "MoreFluids.A", "a", "b"), "refuse at a share in (0, 1]", "Refusal share zero");
      Refused(r => r.SetWaterIntakePolicy("Coffee", 1.5, "MoreFluids.A", "a", "b"), "refuse at a share in (0, 1]", "Refusal share above one");
      Refused(r => r.SetWaterIntakePolicy("Coffee", double.NaN, "MoreFluids.A", "a", "b"), "refuse at a share in (0, 1]", "NaN refusal share");
      Refused(r => r.SetWaterIntakePolicy("Coffee", .5, "DeepFrontier.CoffeeDrunk", "a", "b"), "outside its owner's namespace", "Transformation outside the namespace");
      Refused(r => r.SetWaterIntakePolicy("Coffee", .5, "MoreFluids.A", "", "b"), "localization keys", "Missing status key");
      Refused(r => { r.SetWaterIntakePolicy("Coffee", .5, "MoreFluids.A", "a", "b"); r.SetWaterIntakePolicy("Coffee", .4, "MoreFluids.B", "a", "b"); }, "two water-intake policies", "Two intake policies");
      Refused(r => r.SetWaterIntakePolicy("Tea", .5, "MoreFluids.A", "a", "b"), "which it has not registered", "Policy on an unregistered fluid");
      Refused(r => r.SetBlocksMoisture("Coffee", 0), "moisture is blocked at a share in (0, 1]", "Blocking share zero");
      Refused(r => { r.SetIrrigatesLikeWater("Coffee"); r.SetBlocksMoisture("Coffee", .5); }, "two irrigation policies", "Two irrigation policies");
      Refused(r => { r.AddFluid("Tea", "MoreFluids.Tea", 1, 1, 1, 1); r.SetWaterIntakePolicy("Coffee", .5, "MoreFluids.Drunk", "a", "b"); r.SetWaterIntakePolicy("Tea", .5, "MoreFluids.Drunk", "a", "b"); },
        "both name the water-intake transformation MoreFluids.Drunk", "One transformation for two fluids");
      var host = new ModdableFluidsHost();
      host.RegisterProvider(new PlainProvider("MoreFluids.Liquids", "MoreFluids", new List<string>(), new Fluid("Coffee", "MoreFluids.Coffee")) { Extra = Policies });
      host.RegisterReflectedProvider(new ReflectedPolicies());
      var both = host.Freeze();
      string described = host.DescribeRuntime();
      check(described.Contains("water intakes: refused at 0.5, drawn as water by MoreFluids.CoffeeDrunkAsWater; moisture: irrigates like water")
        && described.Contains("moisture: blocks moisture at 0.1"), "Runtime description lists the policies");
      var syrup = both.Get(both.GetHandle("Reflected.Syrup"));
      check(syrup.WaterIntake!.DrawnAsWater == "Reflected.SyrupDrawnAsWater" && syrup.Irrigation!.BlocksAtShare == .25 && both.UndeclaredPolicies().Count == 0,
        "The reflection route declares both policies with primitives");
    });

    scenario("the intake guard refuses from the share and the moisture input raises contamination like badwater", () => {
      var registry = CoffeeRegistry(r => {
        r.AddFluid("Saltwater", "MoreFluids.Saltwater", .15f, .45f, .55f, .35f); r.AddFluid("Glow", "MoreFluids.Glow", 1, 1, 0, 1);
        r.SetWaterIntakePolicy("Coffee", .5, "MoreFluids.CoffeeDrunkAsWater", "a", "b"); r.SetIrrigatesLikeWater("Coffee");
        r.SetWaterIntakePolicy("Saltwater", .1, "MoreFluids.BrackishDrawnAsWater", "a", "b"); r.SetBlocksMoisture("Saltwater", .1);
        r.SetWaterIntakePolicy("Glow", .005, "MoreFluids.GlowDrawnAsWater", "a", "b"); r.SetBlocksMoisture("Glow", .53);
      });
      int c = registry.GetHandle("MoreFluids.Coffee").Index, s = registry.GetHandle("MoreFluids.Saltwater").Index, g = registry.GetHandle("MoreFluids.Glow").Index;
      FluidColumnSample Sample(double water, double coffee = 0, double salt = 0, double glow = 0, double bad = 0) {
        var v = new double[registry.Count]; v[0] = water; v[1] = bad; v[c] = coffee; v[s] = salt; v[g] = glow;
        return new FluidColumnSample(0, 4, v);
      }
      check(FluidIntakeRefusal.Refusing(registry, Sample(.51, coffee: .49)).Count == 0, "Coffee under half is drawn");
      check(FluidIntakeRefusal.Refusing(registry, Sample(.5, coffee: .5)).SequenceEqual(new[] { c }), "Coffee at half refuses");
      check(FluidIntakeRefusal.Refusing(registry, Sample(.9, salt: .1)).SequenceEqual(new[] { s }), "Saltwater at 10% refuses");
      check(FluidIntakeRefusal.Refusing(registry, Sample(.991, salt: .004, glow: .005)).SequenceEqual(new[] { g }), "Glow at its detection limit refuses alone");
      check(FluidIntakeRefusal.Refusing(registry, Sample(.3, coffee: .5, salt: .2)).SequenceEqual(new[] { c, s }), "Two refusing fluids, in registry order");
      check(FluidIntakeRefusal.Refusing(registry, Sample(0)).Count == 0 && FluidIntakeRefusal.Refusing(registry, Sample(.2, bad: .8)).Count == 0, "Dry or badwater-only columns");
      Rejects<InvalidOperationException>(() => FluidIntakeRefusal.Refusing(CoffeeRegistry(), new FluidColumnSample(0, 4, new double[] { 1, 0, .1 })), "A fluid without a policy");
      const double M = .53;
      var shadow = new FluidMoistureShadow(registry, M, NativeWaterFixture.Stride, NativeWaterFixture.VerticalStride);
      FluidVolumes V(double water, double salt = 0, double glow = 0, double coffee = 0, double bad = 0) {
        var v = new double[registry.Count]; v[0] = water; v[1] = bad; v[c] = coffee; v[s] = salt; v[g] = glow; return new FluidVolumes(v);
      }
      check(shadow.HasBlockingFluids, "Saltwater and glow block moisture");
      Close(shadow.Contribution(V(.9, salt: .1)), M, "Saltwater at 10% gives no moisture");
      Close(shadow.Contribution(V(.8, glow: .2)), .2, "Glow blocking at M is exactly badwater-like");
      Close(shadow.Contribution(V(.5, coffee: .5)), 0, "Coffee irrigates like water");
      Close(shadow.Contribution(V(.75, salt: .05, glow: .1, bad: .1)), .05 * M / .1 + .1, "Blocking fluids add up; badwater is native");
      int Cell(int x, int y) => (y + 1) * NativeWaterFixture.Stride + x + 1;
      const int VS = NativeWaterFixture.VerticalStride;
      var layout = new[] {
        new FluidColumnGeometry(Cell(0, 0), Cell(0, 0), 0, 4, 5),
        new FluidColumnGeometry(Cell(1, 0), Cell(1, 0), 0, 4, 5),
        new FluidColumnGeometry(Cell(2, 0), Cell(2, 0), 0, 6, 7),
        new FluidColumnGeometry(Cell(0, 1), Cell(0, 1), 0, 2, 3),
        new FluidColumnGeometry(Cell(0, 1) + VS, Cell(0, 1), 3, 6, 4) };
      // An unchanged column with 5% saltwater, a column without blocking fluid, a column an obstacle split after the
      // published tick, and two columns merged into one.
      var mixtures = new[] { V(1.9, salt: .1), V(2), V(3.6, salt: .4), V(1.8, salt: .2), V(1) };
      var threadSafe = new Dictionary<int, (int Floor, int Ceiling)> {
        [Cell(0, 0)] = (0, 4), [Cell(1, 0)] = (0, 4), [Cell(2, 0)] = (0, 2), [Cell(2, 0) + VS] = (3, 6), [Cell(0, 1)] = (0, 6) };
      int Count(int cell) => threadSafe.Keys.Count(k => k % VS == cell);
      void Read(int index, out int floor, out int ceiling) { (floor, ceiling) = threadSafe[index]; }
      var additions = new List<KeyValuePair<int, double>>();
      check(shadow.Compute(layout, mixtures, Count, Read, additions) == 4, "Four thread-safe columns raised: " + string.Join(", ", additions.Select(a => a.Key + "=" + a.Value)));
      var added = additions.ToDictionary(a => a.Key, a => a.Value);
      Close(added[Cell(0, 0)], .05 * M / .1, "Unchanged column takes its own shares");
      check(!added.ContainsKey(Cell(1, 0)), "A column without a blocking fluid stays native");
      Close(added[Cell(2, 0)], .1 * M / .1, "Lower part of a split column"); Close(added[Cell(2, 0) + VS], .1 * M / .1, "Upper part of a split column");
      Close(added[Cell(0, 1)], (2 * (.1 * M / .1) + 1 * 0) / 3, "A merged column weights its parents' wet intervals");
      var none = new FluidMoistureShadow(CoffeeRegistry(r => { r.SetWaterIntakePolicy("Coffee", .5, "MoreFluids.A", "a", "b"); r.SetIrrigatesLikeWater("Coffee"); }), M,
        NativeWaterFixture.Stride, NativeWaterFixture.VerticalStride);
      check(!none.HasBlockingFluids && none.Compute(Array.Empty<FluidColumnGeometry>(), Array.Empty<FluidVolumes>(), Count, Read, additions) == 0, "Nothing blocks: the native input stays untouched");
      Rejects<ArgumentOutOfRangeException>(() => new FluidMoistureShadow(registry, 0, NativeWaterFixture.Stride, NativeWaterFixture.VerticalStride), "No native maximum contamination");
      Rejects<InvalidOperationException>(() => new FluidMoistureShadow(CoffeeRegistry(), M, NativeWaterFixture.Stride, NativeWaterFixture.VerticalStride), "A fluid without an irrigation policy");
      observations["moistureMergedContribution"] = added[Cell(0, 1)];
    });

    scenario("a declared visibility curve hides a fluid below its share and blends with the others", () => {
      var registry = CoffeeRegistry(r => {
        r.AddFluid("Glow", "MoreFluids.Glow", .68f, .74f, .06f, .85f);
        r.SetVisibilityCurve("Glow", .005, .12);
      });
      var glow = registry.Get(registry.GetHandle("MoreFluids.Glow")).Visibility!;
      check(registry.Get(registry.GetHandle("MoreFluids.Coffee")).Visibility == null, "No curve: visibility is the share");
      Close(glow.At(.0049), 0, "Hidden below the curve's share"); Close(glow.At(.005), .12, "Visibility where the curve starts");
      Close(glow.At(1), 1, "Pure column fully visible");
      // Deep Frontier's RadioactiveWaterSurface.Encode: 0.12 + 0.88 * log10(r / 0.005) / -log10(0.005).
      foreach (double r in new[] { .005, .01, .05, .2, .73 })
        Close(glow.At(r), .12 + .88 * Math.Log10(r / .005) / -Math.Log10(.005), "Deep Frontier's visibility at " + r, 1e-12);
      var resolver = new ModdableFluids.Rendering.Prototype.FluidAppearanceResolver(registry);
      int c = registry.GetHandle("MoreFluids.Coffee").Index, g = registry.GetHandle("MoreFluids.Glow").Index;
      FluidVolumes M(double water, double coffee, double glowVolume) { var v = new double[registry.Count]; v[0] = water; v[c] = coffee; v[g] = glowVolume; return new FluidVolumes(v); }
      byte Q(double value) => (byte)Math.Round(value * 255, MidpointRounding.AwayFromZero);
      check(resolver.Resolve(M(.996, 0, .004)).Strength == 0, "A trace below the curve stays invisible");
      check(resolver.Resolve(M(.995, 0, .005)).Strength == Q(.85f * .12), "At the detection share the tint is alpha times 0.12");
      double wg = .85f * glow.At(.5), wc = .5 * 1f; // coffee: grey at alpha 1, visible by share
      var blended = resolver.Resolve(M(0, .5, .5));
      check(blended.Strength == Q(1 - (1 - wg) * (1 - wc)) && blended.Red == Q((wg * .68f + wc * .5f) / (wg + wc)), "A curved and a linear fluid blend: " + blended);
      Rejects<FluidRegistryException>(() => CoffeeRegistry(r => r.SetVisibilityCurve("Coffee", 0, .1)), "Curve from share zero", "starts at a share in (0, 1)");
      Rejects<FluidRegistryException>(() => CoffeeRegistry(r => r.SetVisibilityCurve("Coffee", 1, .1)), "Curve from share one", "starts at a share in (0, 1)");
      Rejects<FluidRegistryException>(() => CoffeeRegistry(r => r.SetVisibilityCurve("Coffee", .1, 0)), "No visibility at the start", "is in (0, 1]");
      Rejects<FluidRegistryException>(() => CoffeeRegistry(r => { r.SetVisibilityCurve("Coffee", .1, .2); r.SetVisibilityCurve("Coffee", .2, .2); }), "Two curves", "two visibility curves");
      var host = new ModdableFluidsHost();
      host.RegisterProvider(new PlainProvider("MoreFluids.Liquids", "MoreFluids", new List<string>(), new Fluid("Coffee", "MoreFluids.Coffee")) { Extra = r => r.SetVisibilityCurve("Coffee", .01, .2) });
      host.Freeze();
      check(host.DescribeRuntime().Contains("visible from 0.01 at 0.2, log-scaled to 1"), "Runtime description lists the curve");
      observations["visibilityOneDecadeAboveDetection"] = glow.At(.05);
    });

    scenario("an addition is resolved against the native layout of its change stage, not the published tick", () => {
      var registry = CoffeeRegistry();
      var coffee = registry.GetHandle("MoreFluids.Coffee");
      using var fixture = new NativeWaterFixture(managed, specification);
      fixture.AddColumn(0, 1, 1);
      var session = new NativeFluidTransportSession(fixture.CreateAdapter(), registry.Count, FluidRegistry.BadwaterIndex);
      var world = new FluidWorldState(registry, NativeWaterFixture.Stride);
      world.Publish(session);
      check(!world.TrySample(1, 1, 0, out _), "The published tick has no column at (1, 1)");
      // Requested on the main thread while the published tick has no column there; the native map opens one this tick.
      world.RecordAddition(1, 1, 0, coffee, .25); world.RecordAddition(2, 2, 0, coffee, .5);
      fixture.AddColumn(1, 1, .25f);
      session.ReconcileGeometry(fixture.CreateAdapter());
      session.BeginTick(1); fixture.RunAdapterSubstep(session, fixture.ClearRawFlows, new double[2], false); session.FinishSubstep();
      check(world.TryResolveAddition(1, 1, 0, .25, out var opened), "The new column's addition resolved");
      session.AddQueued(fixture.Indices[1], opened);
      // (2, 2) is still closed: the record is consumed and the addition reported as dropped.
      check(world.TryResolveAddition(2, 2, 0, .5, out var dropped) && world.PendingAdditions == 0, "The closed cell's record consumed");
      session.RecordDroppedAddition((2 + 1) * NativeWaterFixture.Stride + 2 + 1, 0, dropped);
      session.EndTick();
      Close(session.Sample(fixture.Indices[1]).GetVolume(coffee.Index), .25, "Coffee reached the column that appeared this tick");
      var report = new FluidColumnEditor(session, registry, NativeWaterFixture.Stride).Losses.Single(l => l.Kind == FluidLossKind.DroppedAddition);
      check(report.X == 2 && report.Y == 2 && Math.Abs(report.GetVolume(coffee) - .5) < 1e-15, "Dropped coffee reported at its cell");
    });
  }

  /// <summary>A reflected provider declaring both 0.1.4 policies with primitive calls only.</summary>
  public sealed class ReflectedPolicies {
    public string ProviderId => "Reflected.Syrups";
    public string OwnerModId => "Reflected";
    public string MinimumApiVersion => "0.1.3";
    public string[] RequiredCapabilities => new[] { "ModdableFluids.Discovery.Reflection" };
    public void Register(object registration) {
      var type = registration.GetType();
      type.GetMethod("AddFluid")!.Invoke(registration, new object[] { "Syrup", "Reflected.Syrup", .5f, .3f, .1f, 1f });
      type.GetMethod("SetWaterIntakePolicy")!.Invoke(registration, new object[] { "Syrup", .3, "Reflected.SyrupDrawnAsWater", "Reflected.Refused", "Reflected.RefusedAlert" });
      type.GetMethod("SetBlocksMoisture")!.Invoke(registration, new object[] { "Syrup", .25 });
    }
  }

  private sealed class LossReader : IFluidProvider, IFluidColumnRules {
    public string ProviderId => "DeepFrontier.Radiation";
    public string OwnerModId => "DeepFrontier";
    public string MinimumApiVersion => "0.1.3";
    public IReadOnlyCollection<string> RequiredCapabilities { get; } = new[] { "ModdableFluids.World.Rules" };
    public double Deposited { get; private set; }
    public void Register(FluidRegistration registration) { }
    public void ApplyRules(FluidScene scene, IFluidColumnEditor columns) {
      var coffee = scene.Registry.GetHandle("MoreFluids.Coffee");
      foreach (var loss in columns.Losses)
        if (loss.Kind == FluidLossKind.Evaporation || loss.Kind == FluidLossKind.Geometry || loss.Kind == FluidLossKind.DroppedAddition)
          Deposited += 10 * loss.GetVolume(coffee);
    }
  }
}
