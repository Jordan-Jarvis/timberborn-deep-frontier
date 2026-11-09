using System.Text.Json;
using FluidsApi;
using FluidsApi.Native.Prototype;
using FluidsApi.Persistence.Prototype;
using FluidsApi.Transport.Prototype;
using static RegistryScenarios;

/// <summary>Persistent component identity: save schema, exact round trips and load failures.</summary>
internal static class PersistenceScenarios {
  /// <summary>Mutable copy of a document's primitive lists, as a native saver would hold them.</summary>
  private sealed class Lists {
    public int Schema; public string Api = "", Fingerprint = "";
    public List<string> Ids = new(), Owners = new(), Capacity = new(), Volume = new(), ProviderIds = new(), ProviderOwners = new(), ProviderData = new();
    public List<int> X = new(), Y = new(), Floor = new(), Ceiling = new(), EntryColumn = new(), EntryFluid = new(), ProviderSchemas = new();
    public static Lists From(FluidSaveDocument d) => new() {
      Schema = d.SchemaVersion, Api = d.ApiVersion, Fingerprint = d.RegistryFingerprint, Ids = d.FluidIds.ToList(), Owners = d.FluidOwners.ToList(),
      X = d.ColumnX.ToList(), Y = d.ColumnY.ToList(), Floor = d.ColumnFloor.ToList(), Ceiling = d.ColumnCeiling.ToList(), Capacity = d.ColumnCapacity.ToList(),
      EntryColumn = d.EntryColumn.ToList(), EntryFluid = d.EntryFluid.ToList(), Volume = d.EntryVolume.ToList(),
      ProviderIds = d.ProviderIds.ToList(), ProviderOwners = d.ProviderOwners.ToList(), ProviderSchemas = d.ProviderSchemas.ToList(), ProviderData = d.ProviderData.ToList()
    };
    public FluidSaveDocument Build() => new(Schema, Api, Fingerprint, Ids, Owners, X, Y, Floor, Ceiling, Capacity, EntryColumn, EntryFluid, Volume,
      ProviderIds, ProviderOwners, ProviderSchemas, ProviderData);
  }

  /// <summary>Serializes only ints and strings, like native ListKey storage, then rebuilds the document.</summary>
  private static FluidSaveDocument ThroughText(FluidSaveDocument document) {
    string json = JsonSerializer.Serialize(Lists.From(document), new JsonSerializerOptions { IncludeFields = true });
    return JsonSerializer.Deserialize<Lists>(json, new JsonSerializerOptions { IncludeFields = true })!.Build();
  }

  internal static void Run(Action<bool, string> check, Action<string, Action> scenario, string managed, string specification, Dictionary<string, object> observations) {
    void Rejects<T>(Action action, string name, string? mustMention = null) where T : Exception {
      Exception? caught = null;
      try { action(); } catch (Exception e) { caught = e; }
      check(caught is T, name + $": expected {typeof(T).Name}, got {caught?.GetType().Name ?? "no exception"} {caught?.Message}");
      if (mustMention != null && caught != null) check(caught.Message.Contains(mustMention, StringComparison.Ordinal), name + ": message lacks '" + mustMention + "': " + caught.Message);
    }
    var log = new List<string>();
    object[] Providers(bool withTracer, bool withEarly = false) {
      var providers = new List<object> {
        new PlainProvider("FluidsApiTest.Sea", "FluidsApiTest", log, new Fluid("Brine", "FluidsApiTest.Brine")),
        new PlainReflected()
      };
      if (withTracer) providers.Add(new PlainProvider("FluidsApiTest.Tracers", "FluidsApiTest", log, new Fluid("Tracer", "FluidsApiTest.Tracer")));
      if (withEarly) providers.Add(new PlainProvider("Aaa.Early", "Aaa", log, new Fluid("Early", "Aaa.Early")));
      return providers.ToArray();
    }
    FluidRegistry Registry(IEnumerable<object> providers) {
      var host = new FluidsApiHost();
      foreach (var p in providers) { if (p is IFluidProvider c) host.RegisterProvider(c); else host.RegisterReflectedProvider(p); }
      return host.Freeze();
    }
    FluidColumnGeometry[] Layout(NativeFluidTransportSession session) => Enumerable.Range(0, session.ColumnCount).Select(session.GetGeometry).ToArray();
    bool SameBits(double a, double b) => BitConverter.DoubleToInt64Bits(a) == BitConverter.DoubleToInt64Bits(b);

    scenario("saved quantities are exact IEEE-754 bit patterns", () => {
      var random = new Random(5521);
      var values = new List<double> { 0, double.Epsilon, double.MaxValue, 1.0 / 3, 2.875, 1e-300, 4.94e-324 };
      for (int i = 0; i < 5000; i++) values.Add(Math.Exp(random.NextDouble() * 80 - 60) * random.NextDouble());
      foreach (double value in values) {
        string text = FluidSaveDocument.EncodeQuantity(value);
        check(text.Length == 16 && SameBits(FluidSaveDocument.DecodeQuantity(text, "test"), value), "Quantity round trip " + value.ToString("R"));
      }
      foreach (double bad in new[] { double.NaN, double.PositiveInfinity, -1, -double.Epsilon })
        Rejects<ArgumentOutOfRangeException>(() => FluidSaveDocument.EncodeQuantity(bad), "Encode " + bad);
      foreach (string bad in new[] { "3ff0000000000000", "3FF000000000000", "3FF00000000000000", "7FF8000000000000", "7FF0000000000000", "BFF0000000000000", "3FF0 00000000000" })
        Rejects<FormatException>(() => FluidSaveDocument.DecodeQuantity(bad, "test"), "Decode " + bad);
      observations["exactQuantityRoundTrips"] = values.Count;
    });

    scenario("world fluid state round-trips bit for bit through saved fluid IDs", () => {
      using var native = new NativeWaterFixture(managed, specification);
      native.AddColumn(0, 0, 1.5f); native.AddColumn(1, 0, .75f);
      native.AddColumn(0, 1, 1, 0, 1, 0, .5f); native.AddColumn(0, 1, .5f, 3, 12, 1);
      native.AddColumn(2, 2, 0);
      var registry = Registry(Providers(withTracer: true));
      int components = registry.Count;
      check(components == 5, "Five registered components");
      var session = new NativeFluidTransportSession(native.CreateAdapter(), components, FluidRegistry.BadwaterIndex);
      var random = new Random(77);
      for (int slot = 0; slot < native.Indices.Count; slot++) {
        double total = native.PhysicalVolume(slot);
        if (total == 0) continue;
        var weights = Enumerable.Range(0, components).Select(_ => .05 + random.NextDouble()).ToArray();
        double sum = weights.Sum();
        session.SeedComposition(native.Indices[slot], new FluidVolumes(weights.Select(w => total * w / sum).ToArray()));
      }
      session.BeginTick(1);
      native.RunAdapterSubstep(session, () => { native.ClearRawFlows(); native.SetRawFlow(0, 1, .125f); }, new double[native.Indices.Count], false);
      session.FinishSubstep(); session.EndTick();
      Rejects<InvalidOperationException>(() => { session.BeginTick(1); FluidWorldPersistence.Capture(registry, session, NativeWaterFixture.Stride, Array.Empty<FluidProviderState>()); },
        "Capture during a tick", "completed-tick barrier");
      // The rejected capture faulted nothing but left the session mid-tick; rebuild it from native state to continue.
      var saved = new NativeFluidTransportSession(native.CreateAdapter(), components, FluidRegistry.BadwaterIndex);
      var expected = new Dictionary<int, FluidVolumes>();
      foreach (var g in Layout(session)) expected[g.NativeIndex] = session.Sample(g.NativeIndex);
      foreach (var (index, mixture) in expected) saved.SeedComposition(index, mixture);
      var states = new[] { new FluidProviderState("ExampleCreator.Juices", "ExampleCreator", 3, "orchard") };
      var document = FluidWorldPersistence.Capture(registry, saved, NativeWaterFixture.Stride, states);
      check(document.ColumnCount == 4 && document.FluidIds.Count == components, "Saved only wet columns and used fluids");
      check(document.RegistryFingerprint == registry.Fingerprint && document.ApiVersion == "0.1.0", "Document header");
      var text = ThroughText(document);

      var reversed = Registry(Providers(withTracer: true).Reverse());
      check(reversed.Fingerprint == registry.Fingerprint, "Reversed registration changed the registry");
      var restoredSession = new NativeFluidTransportSession(native.CreateAdapter(), reversed.Count, FluidRegistry.BadwaterIndex);
      var restored = FluidWorldPersistence.Restore(text, reversed, Layout(restoredSession), NativeWaterFixture.Stride, NativeWaterFixture.Height);
      check(restored.ExactColumns == 4 && restored.ProjectedColumns == 0 && restored.GeometryLoss.TotalVolume == 0, "Unchanged geometry restored exactly");
      FluidWorldPersistence.Apply(restoredSession, reversed, restored, NativeWaterFixture.Stride);
      int compared = 0;
      foreach (var (index, mixture) in expected)
        for (int c = 0; c < components; c++) { check(SameBits(restoredSession.Sample(index).GetVolume(c), mixture.GetVolume(c)), "Bitwise round trip at " + index + " component " + c); compared++; }
      for (int slot = 0; slot < native.Indices.Count; slot++)
        check(Math.Abs(native.Contamination(slot) - restoredSession.Sample(native.Indices[slot]).GetShare(FluidRegistry.BadwaterIndex)) < 2e-6, "Badwater republished after load");
      var again = Lists.From(FluidWorldPersistence.Capture(reversed, restoredSession, NativeWaterFixture.Stride, text.GetProviderStates()));
      var first = Lists.From(document);
      check(JsonSerializer.Serialize(again, new JsonSerializerOptions { IncludeFields = true }) == JsonSerializer.Serialize(first, new JsonSerializerOptions { IncludeFields = true }),
        "Saving the reloaded state changed the document");
      check(text.GetProviderStates().Single() is { ProviderId: "ExampleCreator.Juices", SchemaVersion: 3, Data: "orchard" }, "Provider state in the document");
      observations["roundTripComponentsCompared"] = compared;

      // Content added after the save: handles shift, saved fluids keep their IDs, the new fluid starts empty.
      var added = Registry(Providers(withTracer: true, withEarly: true));
      check(added.GetHandle("Aaa.Early").Index == 2 && added.GetHandle("ExampleCreator.Juice").Index != registry.GetHandle("ExampleCreator.Juice").Index, "Added fluid shifted handles");
      var addedSession = new NativeFluidTransportSession(native.CreateAdapter(), added.Count, FluidRegistry.BadwaterIndex);
      FluidWorldPersistence.Apply(addedSession, added, FluidWorldPersistence.Restore(text, added, Layout(addedSession), NativeWaterFixture.Stride, NativeWaterFixture.Height), NativeWaterFixture.Stride);
      foreach (var (index, mixture) in expected) {
        foreach (var definition in registry.Definitions)
          check(SameBits(addedSession.Sample(index).GetVolume(added.GetHandle(definition.Id).Index), mixture.GetVolume(registry.GetHandle(definition.Id).Index)), "Added content moved " + definition.Id);
        check(addedSession.Sample(index).GetVolume(added.GetHandle("Aaa.Early").Index) == 0, "New fluid invented volume");
      }

      // A provider whose fluid is in the save is missing: loading stops and names the mod.
      var missing = Registry(Providers(withTracer: false));
      Rejects<FluidSaveException>(() => document.ResolveFluidSlots(missing), "Missing provider", "FluidsApiTest.Tracer (mod FluidsApiTest)");
      Rejects<FluidSaveException>(() => FluidWorldPersistence.Restore(text, missing, Layout(restoredSession), NativeWaterFixture.Stride, NativeWaterFixture.Height), "Missing provider restore", "never replaces unknown fluid with water");

      // Native water that disagrees with the saved state faults the restored session.
      native.SetColumnGeometry(1, 0, 12, (float)(native.PhysicalVolume(1) + .25), 0);
      var disagreeing = new NativeFluidTransportSession(native.CreateAdapter(), registry.Count, FluidRegistry.BadwaterIndex);
      var restoreAgain = FluidWorldPersistence.Restore(text, registry, Layout(disagreeing), NativeWaterFixture.Stride, NativeWaterFixture.Height);
      Rejects<FluidSaveException>(() => FluidWorldPersistence.Apply(disagreeing, registry, restoreAgain, NativeWaterFixture.Stride), "Native disagreement", "disagrees with native water at (1, 0, floor 0)");
      check(disagreeing.Phase == "Faulted", "Disagreeing session was not discarded");
    });

    scenario("a save without extra fluid loads without the content mods", () => {
      using var native = new NativeWaterFixture(managed, specification);
      native.AddColumn(1, 1, 1.25f); native.SetContamination(0, .2);
      var full = Registry(Providers(withTracer: true));
      var session = new NativeFluidTransportSession(native.CreateAdapter(), full.Count, FluidRegistry.BadwaterIndex);
      var document = FluidWorldPersistence.Capture(full, session, NativeWaterFixture.Stride, Array.Empty<FluidProviderState>());
      check(document.FluidIds.SequenceEqual(new[] { FluidIds.Water, FluidIds.Badwater }), "Unused fluids were saved as requirements");
      var vanilla = new FluidsApiHost().Freeze();
      var reloaded = new NativeFluidTransportSession(native.CreateAdapter(), vanilla.Count, FluidRegistry.BadwaterIndex);
      FluidWorldPersistence.Apply(reloaded, vanilla, FluidWorldPersistence.Restore(document, vanilla, Layout(reloaded), NativeWaterFixture.Stride, NativeWaterFixture.Height), NativeWaterFixture.Stride);
      check(SameBits(reloaded.Sample(native.Indices[0]).GetVolume(1), session.Sample(native.Indices[0]).GetVolume(1)), "Vanilla-only reload");
    });

    scenario("changed geometry projects saved columns with explicit losses", () => {
      var registry = Registry(Providers(withTracer: true));
      int n = registry.Count;
      double Total(FluidVolumes v) => v.TotalVolume;
      // Saved: (0,0) wet to 1.5 in [0,12); (1,0) pressurized [0,1) holding 1.5; (2,2) [0,12) holding .5.
      var lists = new Lists {
        Schema = 1, Api = "0.1.0", Fingerprint = registry.Fingerprint, Ids = registry.Definitions.Select(d => d.Id).ToList(), Owners = registry.Definitions.Select(d => d.OwnerModId).ToList(),
        X = new() { 0, 1, 2 }, Y = new() { 0, 0, 2 }, Floor = new() { 0, 0, 0 }, Ceiling = new() { 12, 1, 12 },
        Capacity = new[] { 12.0, 2.875, 12 }.Select(FluidSaveDocument.EncodeQuantity).ToList()
      };
      var volumes = new[] { new[] { .5, .25, .25, .25, .25 }, new[] { .3, .3, .3, .3, .3 }, new[] { .1, .1, .1, .1, .1 } };
      for (int c = 0; c < 3; c++) for (int f = 0; f < n; f++) { lists.EntryColumn.Add(c); lists.EntryFluid.Add(f); lists.Volume.Add(FluidSaveDocument.EncodeQuantity(volumes[c][f])); }
      var document = lists.Build();
      const int stride = 5, height = 3;
      int Cell(int x, int y) => (y + 1) * stride + x + 1;
      var current = new[] {
        new FluidColumnGeometry(100, Cell(0, 0), 0, 1, 1), new FluidColumnGeometry(101, Cell(0, 0), 1, 12, 11),   // horizontal split at height 1
        new FluidColumnGeometry(102, Cell(1, 0), 0, 2, 3.5),                                                     // raised ceiling, new capacity
        new FluidColumnGeometry(103, Cell(2, 2), 0, 12, 12)                                                      // unchanged
      };
      var restored = FluidWorldPersistence.Restore(document, registry, current, stride, height);
      check(restored.ExactColumns == 1 && restored.ProjectedColumns == 2, "Exact versus projected columns");
      check(Math.Abs(Total(restored.GetColumn(0)) - 1) < 1e-12 && Math.Abs(Total(restored.GetColumn(1)) - .5) < 1e-12, "Split by wet interval");
      for (int f = 0; f < n; f++) {
        double before = volumes.Sum(v => v[f]);
        double after = Enumerable.Range(0, current.Length).Sum(i => restored.GetColumn(i).GetVolume(f)) + restored.GeometryLoss.GetVolume(f) + restored.PressureLoss.GetVolume(f);
        check(Math.Abs(after - before) < 1e-12, "Projection conservation for " + registry.Definitions[f].Id);
      }
      check(Math.Abs(Total(restored.GetColumn(2)) - 1.5) < 1e-12 && restored.PressureLoss.TotalVolume == 0, "Pressure storage kept by the raised column");
      Rejects<FluidSaveException>(() => FluidWorldPersistence.Restore(document, registry, current, stride, 2), "Column outside a smaller map", "outside the 3 by 2 map");
    });

    scenario("malformed or newer save documents are rejected with every problem", () => {
      var registry = Registry(Providers(withTracer: true));
      Lists Valid() => new() {
        Schema = 1, Api = "0.1.0", Fingerprint = registry.Fingerprint, Ids = new() { FluidIds.Water, "FluidsApiTest.Tracer" }, Owners = new() { "Timberborn", "FluidsApiTest" },
        X = new() { 0, 1 }, Y = new() { 0, 0 }, Floor = new() { 0, 0 }, Ceiling = new() { 4, 4 }, Capacity = new() { FluidSaveDocument.EncodeQuantity(4.5), FluidSaveDocument.EncodeQuantity(4.5) },
        EntryColumn = new() { 0, 0, 1 }, EntryFluid = new() { 0, 1, 1 }, Volume = new() { FluidSaveDocument.EncodeQuantity(1), FluidSaveDocument.EncodeQuantity(.5), FluidSaveDocument.EncodeQuantity(2) },
        ProviderIds = new() { "FluidsApiTest.Tracers" }, ProviderOwners = new() { "FluidsApiTest" }, ProviderSchemas = new() { 1 }, ProviderData = new() { "" }
      };
      check(Valid().Build().ColumnCount == 2, "Valid fixture document");
      var cases = new (Action<Lists> Mutate, string Mention)[] {
        (l => l.Schema = 2, "newer Fluids API"), (l => l.Schema = 0, "schema 0 is invalid"), (l => l.Owners.RemoveAt(1), "Fluid table lengths differ"),
        (l => l.Y.RemoveAt(1), "Column list lengths differ"), (l => l.Volume.RemoveAt(2), "Component entry list lengths differ"), (l => l.ProviderData.Clear(), "Provider state list lengths differ"),
        (l => l.Ids[1] = FluidIds.Water, "appears twice"), (l => l.Owners[1] = "Other", "lists owner Other"), (l => l.Ids[1] = "Tracer", "'Tracer' is invalid"),
        (l => l.X[1] = 0, "overlap"), (l => l.Ceiling[0] = 300, "invalid geometry"), (l => l.Capacity[0] = "40120000000000ab", "16 uppercase hexadecimal"),
        (l => l.Capacity[1] = "7FF8000000000000", "not a finite nonnegative"), (l => l.Volume[0] = "0000000000000000", "zero volume"),
        (l => l.EntryColumn[2] = 5, "missing column or fluid"), (l => { l.EntryColumn[2] = 0; l.EntryFluid[2] = 1; }, "repeats"),
        (l => l.Volume[2] = FluidSaveDocument.EncodeQuantity(5), "above its capacity"), (l => l.Capacity[0] = FluidSaveDocument.EncodeQuantity(3), "smaller than its open interval"),
        (l => l.ProviderSchemas[0] = 0, "Saved provider state 0"), (l => { l.ProviderIds.Add("FluidsApiTest.Tracers"); l.ProviderOwners.Add("FluidsApiTest"); l.ProviderSchemas.Add(1); l.ProviderData.Add(""); }, "appears twice"),
        (l => l.Fingerprint = "abc", "fingerprint"), (l => l.Api = "0.1", "major.minor.patch")
      };
      foreach (var (mutate, mention) in cases) {
        var lists = Valid(); mutate(lists);
        Rejects<FluidSaveException>(() => lists.Build(), "Malformed document: " + mention, mention);
      }
      var two = Valid(); two.Owners[1] = "Other"; two.Volume[0] = "0000000000000000";
      FluidSaveException? both = null;
      try { two.Build(); } catch (FluidSaveException e) { both = e; }
      check(both?.Problems.Count == 2, "Problems were not all reported together");
      var moved = Valid(); moved.Ids[1] = "FluidsApiTest.Tracer";
      var otherOwner = Registry(new object[] { new PlainProvider("FluidsApiTest.Sea", "FluidsApiTest", log, new Fluid("Brine", "x")) });
      Rejects<FluidSaveException>(() => moved.Build().ResolveFluidSlots(otherOwner), "Missing saved fluid", "FluidsApiTest.Tracer (mod FluidsApiTest)");
      observations["malformedDocumentCases"] = cases.Length;
    });
  }
}
