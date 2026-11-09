using System.Runtime.CompilerServices;
using DeepFrontier.ModdableFluidsMigration;
using DeepFrontier.Scripts.Radiation;
using ModdableFluids;
using ModdableFluids.Native.Prototype;
using ModdableFluids.Persistence.Prototype;
using ModdableFluids.Transport.Prototype;
using ModdableFluids.World.Prototype;
using UnityEngine;

/// <summary>
/// Moddable Fluids 0.1.3 (scene world, legacy import, column rules, whole-cell sampling) and the Deep Frontier
/// migration groundwork on it: radioactive water and springs, the DeepFrontier.Radiation import, decay and cutoff
/// rules, and the IRadiationService facade. Unity types are used only in methods called after the native fixture
/// installed its game assembly resolver.
/// </summary>
internal static class DeepFrontierFluidsScenarios {
  private const double Hours = 0.01;

  internal static void Run(Action<bool, string> check, Action<string, Action> scenario, string managed, string specification, Dictionary<string, object> observations) {
    scenario("Deep Frontier radioactive water registers with its springs on Moddable Fluids 0.1.3", () => Registration(check));
    scenario("Moddable Fluids imports a DeepFrontier.Radiation save once and runs Deep Frontier's decay and cutoff rules", () => {
      using var native = new NativeWaterFixture(managed, specification);
      ImportAndRules(check, native, observations);
    });
    scenario("legacy import variants: version 2 sludge, exception snapshot, strict normal save, competing importers", () => {
      using var native = new NativeWaterFixture(managed, specification);
      ImportVariants(check, native);
    });
    scenario("IRadiationService facade backed by the Moddable Fluids world", () => {
      using var native = new NativeWaterFixture(managed, specification);
      Facade(check, native, observations);
    });
  }

  private static void Rejects<T>(Action<bool, string> check, Action action, string name) where T : Exception {
    Exception? caught = null;
    try { action(); } catch (Exception e) { caught = e; }
    check(caught is T, name + $": expected {typeof(T).Name}, got {caught?.GetType().Name ?? "no exception"}{(caught != null ? " (" + caught.Message + ")" : "")}");
  }

  private static void Registration(Action<bool, string> check) {
    var host = new ModdableFluidsHost();
    host.RegisterProvider(new DeepFrontierRadioactiveWater());
    var registry = host.Freeze();
    check(registry.TryGet(DeepFrontierRadioactiveWater.FluidId, out var fluid) && fluid.OwnerModId == "DeepFrontier" && fluid.NativeRole == FluidNativeRole.Extra, "Radioactive water definition");
    check(fluid.Metadata["DeepFrontier.DetectionLimit"] == "0.005" && fluid.Metadata["DeepFrontier.Good"] == "RadioactiveSludge" && fluid.Metadata["DeepFrontier.VolumePerGood"] == "0.2", "Radioactive water metadata");
    foreach (string template in DeepFrontierRadioactiveWater.SpringTemplates) {
      check(registry.TryGetSourceTypeByTemplate(template, out var spring) && spring.Id == "DeepFrontier." + template && !spring.IsNative, template + " source type");
      check(spring.TileCount == 1 && spring.DefaultStrength == DeepFrontierRadioactiveWater.SpringStrength && spring.FollowsDrought && !spring.BadtideContamination && !spring.TideOverridable,
        template + " behaviour");
      check(spring.EmittedFluids.Count == 1 && spring.EmittedFluids[DeepFrontierRadioactiveWater.FluidId] == 1, template + " emits radioactive water only");
    }
    check(host.HasImporters, "The provider is an importer");
  }

  private static (ModdableFluidsHost Host, DeepFrontierRadioactiveWater Provider, FluidRegistry Registry) Host() {
    var host = new ModdableFluidsHost();
    var provider = new DeepFrontierRadioactiveWater();
    host.RegisterProvider(provider);
    return (host, provider, host.Freeze());
  }

  private static FluidNativeColumn[] Columns(NativeFluidTransportSession session) =>
    Enumerable.Range(0, session.ColumnCount).Select(session.GetGeometry).Select(g => {
      var mixture = session.Sample(g.NativeIndex);
      return new FluidNativeColumn(g.CellIndex % NativeWaterFixture.Stride - 1, g.CellIndex / NativeWaterFixture.Stride - 1, g.Floor, g.Ceiling, g.Capacity,
        mixture.TotalVolume, mixture.GetShare(FluidRegistry.BadwaterIndex));
    }).ToArray();

  // The scene owner's first-substep path: import, restore, apply.
  private static FluidSaveDocument? ImportInto(ModdableFluidsHost host, FluidScene scene, NativeFluidTransportSession session) {
    var document = host.ImportWorld(scene, Columns(session));
    if (document == null) return null;
    var layout = Enumerable.Range(0, session.ColumnCount).Select(session.GetGeometry).ToArray();
    var restored = FluidWorldPersistence.Restore(document, scene.Registry, layout, NativeWaterFixture.Stride, NativeWaterFixture.Height);
    FluidWorldPersistence.Apply(session, scene.Registry, restored, NativeWaterFixture.Stride);
    return document;
  }

  private static int Slot(NativeFluidTransportSession session, int x, int y, int floor) =>
    Enumerable.Range(0, session.ColumnCount).Single(s => {
      var g = session.GetGeometry(s);
      return g.CellIndex == (y + 1) * NativeWaterFixture.Stride + x + 1 && g.Floor == floor;
    });

  private static RadiationLegacyRecord Record(int version, bool snapshot, (int X, int Y, int Floor, float R, float Soil, float Sludge)[] cells) =>
    new RadiationLegacyRecord(version, snapshot, cells.Select(c => new Vector3Int(c.X, c.Y, c.Floor)).ToList(), cells.Select(c => c.R).ToList(),
      cells.Select(c => c.Soil).ToList(), version == RadiationLegacyRecord.SludgeVersion ? cells.Select(c => c.Sludge).ToList() : null,
      new List<RadiationSourceRecord>(), 1, 0f);

  [MethodImpl(MethodImplOptions.NoInlining)]
  private static void ImportAndRules(Action<bool, string> check, NativeWaterFixture native, Dictionary<string, object> observations) {
    int bad = native.AddColumn(0, 0, 2f, 0, 4); native.SetContamination(bad, .25);
    int low = native.AddColumn(1, 0, 1f, 0, 3);
    native.AddColumn(2, 0, 0f, 0, 3);
    int lower = native.AddColumn(1, 1, .5f, 0, 2);
    int upper = native.AddColumn(1, 1, 1f, 4, 12, 1);
    var (host, provider, registry) = Host();
    var radioactive = registry.GetHandle(DeepFrontierRadioactiveWater.FluidId);
    var session = new NativeFluidTransportSession(native.CreateAdapter(), registry.Count, FluidRegistry.BadwaterIndex);
    var scene = host.ActivateScene();
    Rejects<InvalidOperationException>(check, () => _ = scene.World, "A scene without native transport has no world service");
    Rejects<InvalidOperationException>(check, () => host.ApplyColumnRules(scene, new FluidColumnEditor(session, registry, NativeWaterFixture.Stride)), "Rules before Deep Frontier prepared the scene");
    provider.PrepareScene(Hours, Record(3, false, new[] { (0, 0, 0, .5f, .2f, 0f), (1, 0, 0, .004f, 0f, 0f), (2, 0, 0, .3f, 0f, 0f), (1, 1, 0, 0f, .3f, 0f), (1, 1, 4, .2f, 0f, 0f) }));
    check(provider.ImportPending && provider.PendingRecord!.Version == 3, "Legacy record waits for the first substep");
    var document = ImportInto(host, scene, session);
    check(document != null && !provider.ImportPending, "Import consumed the record");
    check(host.ImportWorld(scene, Columns(session)) == null, "A second import finds nothing");
    var result = provider.TakeImportResult()!;
    check(result != null && provider.TakeImportResult() == null, "Import result handed over once");
    double v0 = native.PhysicalVolume(bad), v1 = native.PhysicalVolume(low), v4 = native.PhysicalVolume(upper);
    check(Math.Abs(result!.CutoffVolume - .004f * v1) < 1e-12 && result.SludgeAdditions.Count == 0 && result.SnapshotCorrections.Count == 0, "Cutoff below the detection limit is reported");
    check(document!.FluidIds.SequenceEqual(new[] { FluidIds.Water, FluidIds.Badwater, DeepFrontierRadioactiveWater.FluidId }), "Saved fluid table");
    var m0 = session.Sample(native.Indices[bad]);
    check(Math.Abs(m0.GetVolume(radioactive.Index) - .5 * v0) < 1e-12 && Math.Abs(m0.GetShare(FluidRegistry.BadwaterIndex) - .25) < 1e-7
      && Math.Abs(m0.GetVolume(FluidRegistry.WaterIndex) - .25 * v0) < 1e-12, "Imported column with badwater");
    check(session.Sample(native.Indices[low]).GetVolume(radioactive.Index) == 0, "Share under the limit imported as fresh water");
    check(session.Sample(native.Indices[lower]).GetVolume(radioactive.Index) == 0, "Soil-only cell holds no radioactive water");
    check(Math.Abs(session.Sample(native.Indices[upper]).GetVolume(radioactive.Index) - .2f * v4) < 1e-9, "Upper reservoir imported by its floor");

    // Rules: decay converts radioactive water into fresh water in place.
    double decay = RadiationTuning.DecayPerHour(RadiationTuning.RadiationHalfLifeDays) * Hours;
    double total0 = m0.TotalVolume, badVolume = m0.GetVolume(FluidRegistry.BadwaterIndex);
    var editor = new FluidColumnEditor(session, registry, NativeWaterFixture.Stride);
    host.ApplyColumnRules(scene, editor);
    var d0 = session.Sample(native.Indices[bad]);
    check(Math.Abs(d0.GetShare(radioactive.Index) - (.5 - .5 * decay)) < 1e-12, "Decay over one tick");
    check(Math.Abs(d0.TotalVolume - total0) < 1e-15 && d0.GetVolume(FluidRegistry.BadwaterIndex) == badVolume, "Decay keeps volume and badwater");
    // Cutoff: a share below the limit survives while it grows, then is removed.
    var seeded = new double[registry.Count]; seeded[FluidRegistry.WaterIndex] = v1 * .997; seeded[radioactive.Index] = v1 * .003;
    session.SeedComposition(native.Indices[low], new FluidVolumes(seeded));
    host.ApplyColumnRules(scene, editor);
    double kept = session.Sample(native.Indices[low]).GetVolume(radioactive.Index);
    check(kept > 0 && kept < v1 * .003, "A growing share below the limit is kept (decayed)");
    host.ApplyColumnRules(scene, editor);
    var cut = session.Sample(native.Indices[low]);
    check(cut.GetVolume(radioactive.Index) == 0 && Math.Abs(cut.GetVolume(FluidRegistry.WaterIndex) - v1) < 1e-12, "A share below the limit that stopped growing becomes fresh water");
    // Editor limits.
    Rejects<ArgumentException>(check, () => editor.Convert(Slot(session, 0, 0, 0), registry.Badwater, registry.Water, .01), "Converting badwater");
    Rejects<ArgumentOutOfRangeException>(check, () => editor.Convert(Slot(session, 0, 0, 0), radioactive, registry.Water, 10), "Converting more than the column holds");
    check(editor.X(Slot(session, 1, 1, 4)) == 1 && editor.Y(Slot(session, 1, 1, 4)) == 1 && editor.Floor(Slot(session, 1, 1, 4)) == 4 && editor.Ceiling(Slot(session, 1, 1, 4)) == 12, "Editor geometry");
    editor.Close();
    Rejects<InvalidOperationException>(check, () => editor.GetVolume(0, radioactive), "A closed editor");
    session.BeginTick(1);
    Rejects<InvalidOperationException>(check, () => session.ConvertComponent(0, radioactive.Index, 0, .001), "Converting mid-tick");
    host.UnloadScene(scene);
    check(provider.Scene == null && !provider.ImportPending, "Unload detaches the provider");
    observations["deepFrontierImportCutoff"] = result.CutoffVolume;
    observations["deepFrontierDecayPerTick"] = decay;
  }

  private sealed class OtherImporter : IFluidProvider, IFluidWorldImporter {
    public string ProviderId => "OtherMod.Importer";
    public string OwnerModId => "OtherMod";
    public string MinimumApiVersion => "0.1.3";
    public IReadOnlyCollection<string> RequiredCapabilities { get; } = new[] { "ModdableFluids.World.Import" };
    public void Register(FluidRegistration registration) { }
    public FluidSaveDocument? Document { get; set; }
    public FluidSaveDocument ImportWorld(FluidScene scene, IReadOnlyList<FluidNativeColumn> columns) => Document!;
  }

  [MethodImpl(MethodImplOptions.NoInlining)]
  private static void ImportVariants(Action<bool, string> check, NativeWaterFixture native) {
    int a = native.AddColumn(0, 0, 2f, 0, 4); native.SetContamination(a, .5);
    int b = native.AddColumn(1, 0, 1f, 0, 3);
    var adapter = native.CreateAdapter();
    double va = native.PhysicalVolume(a);
    // Version 2: the share is of the non-bad water; sludge becomes radioactive additions.
    {
      var (host, provider, registry) = Host();
      var scene = host.ActivateScene();
      var session = new NativeFluidTransportSession(adapter, registry.Count, FluidRegistry.BadwaterIndex);
      provider.PrepareScene(Hours, Record(2, false, new[] { (0, 0, 0, .6f, 0f, 1.5f), (1, 0, 0, 0f, 0f, .4f) }));
      ImportInto(host, scene, session);
      var result = provider.TakeImportResult()!;
      check(Math.Abs(session.Sample(native.Indices[a]).GetVolume(registry.GetHandle(DeepFrontierRadioactiveWater.FluidId).Index) - .6f * .5 * va) < 1e-9, "Version 2 share of the non-bad water");
      check(result.SludgeAdditions.Count == 2 && result.SludgeAdditions[0] == (0, 0, 0, 1.5) && Math.Abs(result.SludgeAdditions[1].Volume - .4f) < 1e-12, "Version 2 sludge additions");
      host.UnloadScene(scene);
    }
    // A normal save whose share exceeds the column, or names a missing column, stops loading.
    {
      var (host, provider, registry) = Host();
      var scene = host.ActivateScene();
      var session = new NativeFluidTransportSession(adapter, registry.Count, FluidRegistry.BadwaterIndex);
      provider.PrepareScene(Hours, Record(3, false, new[] { (0, 0, 0, .7f, 0f, 0f), (2, 2, 0, .3f, 0f, 0f) }));
      Exception? caught = null;
      try { host.ImportWorld(scene, Columns(session)); } catch (Exception e) { caught = e; }
      var problems = (caught as FluidSaveException)?.Problems ?? Array.Empty<string>();
      check(problems.Count == 2 && problems.Any(p => p.Contains("exceeds")) && problems.Any(p => p.Contains("(2, 2, 0)")), "A normal save reports every inconsistent cell");
      host.UnloadScene(scene);
    }
    // An exception snapshot drops and caps, reporting each.
    {
      var (host, provider, registry) = Host();
      var scene = host.ActivateScene();
      var session = new NativeFluidTransportSession(adapter, registry.Count, FluidRegistry.BadwaterIndex);
      provider.PrepareScene(Hours, Record(3, true, new[] { (0, 0, 0, .7f, 0f, 0f), (2, 2, 0, .3f, 0f, 0f) }));
      ImportInto(host, scene, session);
      var result = provider.TakeImportResult()!;
      check(result.SnapshotCorrections.Count == 2 && Math.Abs(session.Sample(native.Indices[a]).GetVolume(registry.GetHandle(DeepFrontierRadioactiveWater.FluidId).Index) - .5 * va) < 1e-9,
        "Snapshot capped at 1 - b and dropped the moved cell");
      host.UnloadScene(scene);
    }
    // Two importers for one save stop loading; an importer's unknown fluid stops loading.
    {
      var host = new ModdableFluidsHost();
      var provider = new DeepFrontierRadioactiveWater();
      var other = new OtherImporter();
      host.RegisterProvider(provider); host.RegisterProvider(other);
      var registry = host.Freeze();
      var scene = host.ActivateScene();
      var session = new NativeFluidTransportSession(adapter, registry.Count, FluidRegistry.BadwaterIndex);
      provider.PrepareScene(Hours, Record(3, false, new[] { (0, 0, 0, .3f, 0f, 0f) }));
      var columns = Columns(session);
      var foreign = new FluidSaveDocument(1, "0.1.3", registry.Fingerprint, new[] { "OtherMod.Ink" }, new[] { "OtherMod" }, new[] { 0 }, new[] { 0 }, new[] { 0 }, new[] { 4 },
        new[] { FluidSaveDocument.EncodeQuantity(4) }, new[] { 0 }, new[] { 0 }, new[] { FluidSaveDocument.EncodeQuantity(1) }, Array.Empty<string>(), Array.Empty<string>(), Array.Empty<int>(), Array.Empty<string>());
      other.Document = foreign;
      Rejects<FluidSaveException>(check, () => host.ImportWorld(scene, columns), "Two importers for one save");
      provider.PrepareScene(Hours, null);
      Exception? caught = null;
      try { host.ImportWorld(scene, columns); } catch (Exception e) { caught = e; }
      check(caught is FluidSaveException fse && fse.Message.Contains("OtherMod.Ink"), "An imported unknown fluid is named");
      host.UnloadScene(scene);
    }
  }

  private sealed class TestWorld : IFluidWorld {
    public FluidWorldState State { get; }
    public List<(int X, int Y, int Z, FluidHandle Fluid, double Volume)> Additions { get; } = new();
    public TestWorld(FluidRegistry registry) { State = new FluidWorldState(registry, NativeWaterFixture.Stride); }
    public FluidRegistry Registry => State.Registry;
    public int CompletedTicks => State.CompletedTicks;
    public bool HasState => State.HasSnapshot;
    public bool TrySample(int x, int y, int z, out FluidColumnSample sample) => State.TrySample(x, y, z, out sample!);
    public IReadOnlyList<FluidColumnSample> SampleCell(int x, int y) => State.SampleCell(x, y);
    public double TotalVolume(FluidHandle fluid) => State.TotalVolume(fluid);
    public void QueueAddition(int x, int y, int z, FluidHandle fluid, double volume) {
      if (!State.TrySample(x, y, z, out _)) throw new ArgumentException("No open column");
      State.RecordAddition(x, y, z, fluid, volume);
      Additions.Add((x, y, z, fluid, volume));
    }
    public void SetSourceComposition(string ownerId, IReadOnlyDictionary<string, double> composition) => State.SetSourceComposition(ownerId, composition);
  }

  [MethodImpl(MethodImplOptions.NoInlining)]
  private static void Facade(Action<bool, string> check, NativeWaterFixture native, Dictionary<string, object> observations) {
    int bad = native.AddColumn(0, 0, 2f, 0, 4); native.SetContamination(bad, .25);
    native.AddColumn(1, 0, 1f, 0, 3);
    native.AddColumn(1, 1, .5f, 0, 2);
    native.AddColumn(1, 1, 1f, 4, 12, 1);
    var (host, provider, registry) = Host();
    var radioactive = registry.GetHandle(DeepFrontierRadioactiveWater.FluidId);
    var world = new TestWorld(registry);
    var other = new ModdableFluidsHost(); other.Freeze();
    Rejects<ArgumentException>(check, () => other.ActivateScene(world), "A world from another registry");
    var scene = host.ActivateScene(world);
    check(ReferenceEquals(scene.World, world) && scene.HasWorld, "The scene carries its world service");
    var soil = new RadiationSoilLedger();
    var facade = new ModdableFluidsRadiationService(provider, soil, () => 3f, () => new Vector2Int(NativeWaterFixture.Width, NativeWaterFixture.Height));
    provider.PrepareScene(Hours, Record(3, false, new[] { (0, 0, 0, .5f, .2f, 0f) }));
    // Before the first fluid tick: pending, nothing to sample, requests wait.
    check(facade.SavedStatePending && !facade.Sample(new Vector3Int(0, 0, 1)).HasColumn && !facade.TryFindOpenCell(new Vector2Int(0, 0), 0, out _), "Before the first tick");
    facade.AddRadioactiveWater(new Vector3Int(1, 0, 0), .25f);
    facade.AddSoilRadiation(new Vector3Int(1, 1, 5), .05f);
    check(facade.EarlyAdditions == 2 && world.Additions.Count == 0, "Requests before the first tick are kept");
    Rejects<ArgumentOutOfRangeException>(check, () => facade.AddRadioactiveWater(new Vector3Int(5, 0, 0), 1f), "Outside the map");
    Rejects<ArgumentOutOfRangeException>(check, () => facade.AddRadioactiveWater(new Vector3Int(0, 0, 0), 0f), "Zero volume");
    // First substep: import, then publish.
    var session = new NativeFluidTransportSession(native.CreateAdapter(), registry.Count, FluidRegistry.BadwaterIndex);
    ImportInto(host, scene, session);
    world.State.Publish(session);
    soil.Load(new[] { new Vector3Int(0, 0, 0) }, new[] { .2f });
    check(!facade.SavedStatePending, "State published and imported");
    facade.Tick((float)Hours);
    check(facade.EarlyAdditions == 0 && world.Additions.Count == 1 && world.Additions[0].Equals((1, 0, 0, radioactive, (double).25f)), "Early water added through the world service");
    check(Math.Abs(soil.SoilAt(new Vector3Int(1, 1, 4)) - .05f) < 1e-7, "Early soil lands under the column containing the cell");
    var sample = facade.Sample(new Vector3Int(0, 0, 1));
    check(sample.HasColumn && Math.Abs(sample.WaterRadiation - .5f) < 1e-6 && Math.Abs(sample.BadwaterShare - .25f) < 1e-6 && sample.Submerged && Math.Abs(sample.SoilRadiation - .2f) < 1e-7, "Sample");
    check(!facade.Sample(new Vector3Int(0, 0, 3)).Submerged && facade.Sample(new Vector3Int(0, 0, 3)).HasColumn, "Above the surface in an open column");
    check(Math.Abs(facade.GetRadiation(new Vector3Int(0, 0, 1)) - .5f) < 1e-6 && Math.Abs(facade.GetRadiation(new Vector3Int(0, 0, 3)) - .2f * RadiationTuning.SoilHazardWeight) < 1e-7, "GetRadiation");
    check(facade.IsColumnContaminated(new Vector3Int(0, 0, 2)) && !facade.IsColumnContaminated(new Vector3Int(1, 0, 0)), "IsColumnContaminated");
    check(facade.TryFindOpenCell(new Vector2Int(1, 1), 1, out var inside) && inside == new Vector3Int(1, 1, 1), "Open cell containing the height");
    check(facade.TryFindOpenCell(new Vector2Int(1, 1), 2, out var above) && above == new Vector3Int(1, 1, 4), "Lowest column above a solid height");
    check(!facade.TryFindOpenCell(new Vector2Int(1, 1), 12, out _) && !facade.TryFindOpenCell(new Vector2Int(2, 2), 0, out _), "No column above or none at all");
    Rejects<ArgumentOutOfRangeException>(check, () => facade.TryFindOpenCell(new Vector2Int(-1, 0), 0, out _), "TryFindOpenCell outside the map");
    Rejects<ArgumentException>(check, () => facade.AddRadioactiveWater(new Vector3Int(1, 1, 3), 1f), "Water into a solid cell");
    check(Math.Abs(facade.TotalWaterRadiation - (float)world.TotalVolume(radioactive)) < 1e-6 && facade.WaterPerStrengthHour == 3f, "Totals and source rate");
    // Timed sources: active hours capped by what remains, then removed.
    int id = facade.AddContinuousSource(new Vector3Int(0, 0, 0), 2f, 3f);
    check(id == 1 && facade.NextSourceId == 2, "Source id");
    facade.Tick(2f); facade.Tick(2f);
    var emitted = world.Additions.Skip(1).Select(s => s.Volume).ToArray();
    check(emitted.Length == 2 && Math.Abs(emitted[0] - 4) < 1e-6 && Math.Abs(emitted[1] - 2) < 1e-6 && facade.Sources.Count == 0, "Source emits for its duration only");
    Rejects<ArgumentException>(check, () => facade.RemoveContinuousSource(id), "Removing a finished source");
    // The tide share is the world's source composition, published on the next tick.
    facade.SetSourceRadioactiveShare(.4f);
    check(world.State.ActiveSourceComposition == null, "Tide share waits for the tick");
    facade.Tick((float)Hours);
    check(Math.Abs(world.State.ActiveSourceComposition![DeepFrontierRadioactiveWater.FluidId] - .4f) < 1e-7, "Tide share overrides sources");
    facade.SetSourceRadioactiveShare(0f); facade.Tick((float)Hours);
    check(world.State.ActiveSourceComposition == null, "Tide over");
    Rejects<ArgumentOutOfRangeException>(check, () => facade.SetSourceRadioactiveShare(1.5f), "Share above one");
    // Soil ledger: decay and limits.
    soil.Decay(24f * RadiationTuning.SoilHalfLifeDays);
    check(Math.Abs(soil.SoilAt(new Vector3Int(0, 0, 0)) - .2f * (1f - (float)Math.Log(2))) < 1e-4, "Soil decay");
    soil.Decay(24f * 3000f);
    check(soil.Count == 0, "Soil below the minimum is gone");
    host.UnloadScene(scene);
    observations["deepFrontierFacadeSampledShare"] = sample.WaterRadiation;
  }
}
