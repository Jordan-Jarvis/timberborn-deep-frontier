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
/// migration on it: radioactive water and springs, the DeepFrontier.Radiation import, the water rules through the
/// soil field (HarnessExtensions.DeepFrontier.cs covers the field itself), and the IRadiationService facade. Unity types are used only in methods called after the native fixture
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

  /// <summary>The real column editor with no losses (the runtime fills Moddable Fluids' loss reports; DeepFrontierSoil covers them).</summary>
  private sealed class LossFree : IFluidColumnEditor {
    private readonly IFluidColumnEditor _inner;
    public LossFree(IFluidColumnEditor inner) { _inner = inner; }
    public int ColumnCount => _inner.ColumnCount;
    public int CompletedTicks => _inner.CompletedTicks;
    public int X(int column) => _inner.X(column);
    public int Y(int column) => _inner.Y(column);
    public int Floor(int column) => _inner.Floor(column);
    public int Ceiling(int column) => _inner.Ceiling(column);
    public double GetVolume(int column, FluidHandle fluid) => _inner.GetVolume(column, fluid);
    public double TotalVolume(int column) => _inner.TotalVolume(column);
    public void Convert(int column, FluidHandle from, FluidHandle to, double volume) => _inner.Convert(column, from, to, volume);
    public IReadOnlyList<FluidLoss> Losses => Array.Empty<FluidLoss>();
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
    // Native policies (0.1.4): pumps refuse at the detection limit (RadiationIntakeGuard), moisture is blocked like badwater.
    check(fluid.WaterIntake != null && fluid.WaterIntake.RefuseAtShare == RadiationTuning.DetectionLimit && fluid.WaterIntake.DrawnAsWater == DeepFrontierRadioactiveWater.DrawnAsWater
      && fluid.WaterIntake.RefusedStatusLocKey == "DeepFrontier.Radiation.Status.PumpBlocked" && fluid.WaterIntake.RefusedAlertLocKey == "DeepFrontier.Radiation.Status.PumpBlocked.Short",
      "Water-intake policy: refused at 0.5%, Deep Frontier's pump status");
    check(fluid.Irrigation != null && fluid.Irrigation.Effect == FluidMoistureEffect.BlocksLikeBadwater && fluid.Irrigation.BlocksAtShare == .53f
      && .53f / fluid.Irrigation.BlocksAtShare == 1, "Irrigation policy: blocks at the native badwater limit, so the moisture tasks see b + r");
    check(registry.UndeclaredPolicies().Count == 0, "Every policy declared");
    // RadioactiveWaterSurface.Encode's visibility, transcribed: 0 below the limit, 0.12 there, 1 at r = 1, log-scaled.
    float Encoded(float r) => r < RadiationTuning.DetectionLimit ? 0f
      : Mathf.Min(1f, 0.12f + 0.88f * Mathf.Log10(r / RadiationTuning.DetectionLimit) / -Mathf.Log10(RadiationTuning.DetectionLimit));
    var shares = new[] { 0f, .001f, .00499f, RadiationTuning.DetectionLimit, .01f, .05f, .2f, .5f, .9f, 1f };
    check(fluid.Visibility != null && shares.All(r => Math.Abs(fluid.Visibility.At(r) - Encoded(r)) < 1e-6),
      "The water tint's visibility curve is RadioactiveWaterSurface.Encode's");
    check(fluid.DisplayNameLocKey == "Good.RadioactiveSludge.DisplayName" && registry.SourceTypes.Where(t => !t.IsNative).All(t => t.DisplayNameLocKey == "Building." + t.Template + ".DisplayName"),
      "Display names use Deep Frontier's existing localization keys");
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
    Rejects<InvalidOperationException>(check, () => host.ApplyColumnRules(scene, new LossFree(new FluidColumnEditor(session, registry, NativeWaterFixture.Stride))), "Rules before Deep Frontier prepared the scene");
    var field = DeepFrontierSoil.Field(NativeWaterFixture.Width, NativeWaterFixture.Height, (float)Hours);
    provider.PrepareScene(field, Record(3, false, new[] { (0, 0, 0, .5f, .2f, 0f), (1, 0, 0, .004f, 0f, 0f), (2, 0, 0, .3f, 0f, 0f), (1, 1, 0, 0f, .3f, 0f), (1, 1, 4, .2f, 0f, 0f) }));
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

    // Rules: decay and the soil's uptake convert radioactive water into fresh water in place (the one-fluid sequence).
    double decay = RadiationTuning.DecayPerHour(RadiationTuning.RadiationHalfLifeDays) * Hours;
    double total0 = m0.TotalVolume, badVolume = m0.GetVolume(FluidRegistry.BadwaterIndex);
    var expect0 = DeepFrontierSoil.Reference(0f, m0.GetVolume(FluidRegistry.WaterIndex), badVolume, m0.GetVolume(radioactive.Index), 0f, (float)Hours);
    var editor = new FluidColumnEditor(session, registry, NativeWaterFixture.Stride);
    var rules = new LossFree(editor);
    host.ApplyColumnRules(scene, rules);
    var d0 = session.Sample(native.Indices[bad]);
    check(Math.Abs(d0.GetShare(radioactive.Index) - expect0.Share) < 1e-12 && field.Published.Water[new Vector3Int(0, 0, 0)] == expect0.Share
      && field.Published.Soil[new Vector3Int(0, 0, 0)] == expect0.Soil && expect0.Soil > 0, "Decay and uptake over one tick");
    check(Math.Abs(d0.TotalVolume - total0) < 1e-15 && d0.GetVolume(FluidRegistry.BadwaterIndex) == badVolume, "The rules keep volume and badwater");
    // Cutoff: a share below the limit survives while it grows, then is removed.
    var seeded = new double[registry.Count]; seeded[FluidRegistry.WaterIndex] = v1 * .997; seeded[radioactive.Index] = v1 * .003;
    session.SeedComposition(native.Indices[low], new FluidVolumes(seeded));
    host.ApplyColumnRules(scene, rules);
    double kept = session.Sample(native.Indices[low]).GetVolume(radioactive.Index);
    check(kept > 0 && kept < v1 * .003, "A growing share below the limit is kept (decayed)");
    host.ApplyColumnRules(scene, rules);
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
      provider.PrepareScene(DeepFrontierSoil.Field(NativeWaterFixture.Width, NativeWaterFixture.Height, (float)Hours), Record(2, false, new[] { (0, 0, 0, .6f, 0f, 1.5f), (1, 0, 0, 0f, 0f, .4f) }));
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
      provider.PrepareScene(DeepFrontierSoil.Field(NativeWaterFixture.Width, NativeWaterFixture.Height, (float)Hours), Record(3, false, new[] { (0, 0, 0, .7f, 0f, 0f), (2, 2, 0, .3f, 0f, 0f) }));
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
      provider.PrepareScene(DeepFrontierSoil.Field(NativeWaterFixture.Width, NativeWaterFixture.Height, (float)Hours), Record(3, true, new[] { (0, 0, 0, .7f, 0f, 0f), (2, 2, 0, .3f, 0f, 0f) }));
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
      provider.PrepareScene(DeepFrontierSoil.Field(NativeWaterFixture.Width, NativeWaterFixture.Height, (float)Hours), Record(3, false, new[] { (0, 0, 0, .3f, 0f, 0f) }));
      var columns = Columns(session);
      var foreign = new FluidSaveDocument(1, "0.1.3", registry.Fingerprint, new[] { "OtherMod.Ink" }, new[] { "OtherMod" }, new[] { 0 }, new[] { 0 }, new[] { 0 }, new[] { 4 },
        new[] { FluidSaveDocument.EncodeQuantity(4) }, new[] { 0 }, new[] { 0 }, new[] { FluidSaveDocument.EncodeQuantity(1) }, Array.Empty<string>(), Array.Empty<string>(), Array.Empty<int>(), Array.Empty<string>());
      other.Document = foreign;
      Rejects<FluidSaveException>(check, () => host.ImportWorld(scene, columns), "Two importers for one save");
      provider.PrepareScene(DeepFrontierSoil.Field(NativeWaterFixture.Width, NativeWaterFixture.Height, (float)Hours), null);
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

  /// <summary>Native geometry for the facade, as the game's thread-safe water map reports it: (x, y, floor, ceiling, depth, badwater).</summary>
  private sealed class TestCells : IRadiationCellMap {
    private readonly List<(int X, int Y, int Floor, int Ceiling, float Depth, float Bad)> _columns;
    public TestCells(params (int, int, int, int, float, float)[] columns) { _columns = columns.ToList(); }
    public Vector2Int Size => new Vector2Int(NativeWaterFixture.Width, NativeWaterFixture.Height);
    private (int X, int Y, int Floor, int Ceiling, float Depth, float Bad)? Column(Vector3Int c) =>
      _columns.Where(k => k.X == c.x && k.Y == c.y && c.z >= k.Floor && c.z < k.Ceiling).Select(k => ((int, int, int, int, float, float)?)k).FirstOrDefault();
    public bool IsOpenCell(Vector3Int cell) => Column(cell) != null;
    public bool IsSubmerged(Vector3Int cell) => Column(cell) is { } k && Mathf.CeilToInt(k.Floor + k.Depth) > cell.z;
    public float BadwaterShare(Vector3Int cell) => Column(cell) is { } k && k.Floor + k.Depth > cell.z ? k.Bad : 0f;
    public bool TryFindOpenCell(Vector2Int xy, int z, out Vector3Int cell) {
      var at = _columns.Where(k => k.X == xy.x && k.Y == xy.y).OrderBy(k => k.Floor).ToList();
      foreach (var k in at) if (z >= k.Floor && z < k.Ceiling) { cell = new Vector3Int(xy.x, xy.y, z); return true; }
      foreach (var k in at) if (k.Floor > z) { cell = new Vector3Int(xy.x, xy.y, k.Floor); return true; }
      cell = default;
      return false;
    }
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
    var soil = DeepFrontierSoil.Field(NativeWaterFixture.Width, NativeWaterFixture.Height, (float)Hours);
    soil.Load(new[] { new Vector3Int(0, 0, 0) }, new[] { .2f }, 0f, lenient: false);
    var cells = new TestCells((0, 0, 0, 4, 2f, .25f), (1, 0, 0, 3, 1f, 0f), (1, 1, 0, 2, .5f, 0f), (1, 1, 4, 12, 1f, 0f));
    var facade = new ModdableFluidsRadiationService(provider, soil, cells, () => 3f);
    check(!facade.SavedStatePending && !facade.IsIrradiatedGround(new Vector3Int(0, 0, 0)) && !facade.Sample(new Vector3Int(0, 0, 1)).HasColumn,
      "A new game has nothing pending and reads no column before its first tick (sensors sample it)");
    facade.MarkSavedState();
    provider.PrepareScene(soil, Record(3, false, new[] { (0, 0, 0, .5f, .2f, 0f) }));
    // Before the first fluid tick: pending, nothing to sample, requests wait; native geometry already answers.
    check(facade.SavedStatePending && !facade.Sample(new Vector3Int(0, 0, 1)).HasColumn && facade.ColumnRadiation(new Vector3Int(0, 0, 1)) == 0
      && !facade.IsIrradiatedGround(new Vector3Int(0, 0, 0)), "Before the first tick");
    check(facade.TryFindOpenCell(new Vector2Int(0, 0), 0, out var early) && early == new Vector3Int(0, 0, 0) && facade.IsOpenCell(new Vector3Int(1, 1, 5)), "Native geometry before the first tick");
    Rejects<ArgumentException>(check, () => facade.AddSoilRadiation(new Vector3Int(1, 1, 3), .1f), "Soil under a solid cell is refused at once, as RadiationSimulation refuses it");
    facade.AddRadioactiveWater(new Vector3Int(1, 0, 0), .25f);
    facade.AddSoilRadiation(new Vector3Int(1, 1, 5), .05f);
    check(facade.EarlyAdditions.Count == 1 && soil.PendingRequests.Count == 1 && world.Additions.Count == 0, "Requests before the first tick are kept");
    Rejects<ArgumentOutOfRangeException>(check, () => facade.AddRadioactiveWater(new Vector3Int(5, 0, 0), 1f), "Outside the map");
    Rejects<ArgumentOutOfRangeException>(check, () => facade.AddRadioactiveWater(new Vector3Int(0, 0, 0), 0f), "Zero volume");
    // First substep: import, then publish.
    var session = new NativeFluidTransportSession(native.CreateAdapter(), registry.Count, FluidRegistry.BadwaterIndex);
    ImportInto(host, scene, session);
    world.State.Publish(session);
    check(facade.SavedStatePending, "Still pending until the soil rules ran once");
    // The first completed tick: the rules apply the soil request, then the one-fluid sequence per column.
    FluidVolumes At(int x, int y, int floor) => session.Sample(session.GetGeometry(Slot(session, x, y, floor)).NativeIndex);
    var c0 = At(0, 0, 0); var c4 = At(1, 1, 4);
    var expect0 = DeepFrontierSoil.Reference(.2f, c0.GetVolume(FluidRegistry.WaterIndex), c0.GetVolume(FluidRegistry.BadwaterIndex), c0.GetVolume(radioactive.Index), 0f, (float)Hours);
    var expect4 = DeepFrontierSoil.Reference(.05f, c4.GetVolume(FluidRegistry.WaterIndex), c4.GetVolume(FluidRegistry.BadwaterIndex), c4.GetVolume(radioactive.Index), 0f, (float)Hours);
    host.ApplyColumnRules(scene, new LossFree(new FluidColumnEditor(session, registry, NativeWaterFixture.Stride)));
    world.State.Publish(session);
    check(!facade.SavedStatePending && soil.PendingRequests.Count == 0, "State published, imported and the soil rules ran");
    facade.Tick((float)Hours);
    check(facade.EarlyAdditions.Count == 0 && world.Additions.Count == 1 && world.Additions[0].Equals((1, 0, 0, radioactive, (double).25f)), "Early water added through the world service");
    check(soil.SoilAt(new Vector3Int(1, 1, 4)) == expect4.Soil && expect4.Soil < .05f && expect4.Soil > 0f, "Early soil lands under the column containing the cell, then clean water rinses it");
    var sample = facade.Sample(new Vector3Int(0, 0, 1));
    check(sample.HasColumn && Math.Abs(sample.WaterRadiation - expect0.Share) < 1e-6 && Math.Abs(sample.BadwaterShare - .25f) < 1e-6 && sample.Submerged
      && sample.SoilRadiation == expect0.Soil, "Sample");
    check(!facade.Sample(new Vector3Int(0, 0, 3)).Submerged && facade.Sample(new Vector3Int(0, 0, 3)).HasColumn, "Above the surface in an open column");
    check(Math.Abs(facade.GetRadiation(new Vector3Int(0, 0, 1)) - expect0.Share) < 1e-6 && facade.GetRadiation(new Vector3Int(0, 0, 3)) == expect0.Soil * RadiationTuning.SoilHazardWeight, "GetRadiation");
    check(facade.IsColumnContaminated(new Vector3Int(0, 0, 2)) && !facade.IsColumnContaminated(new Vector3Int(1, 0, 0)), "IsColumnContaminated");
    check(Math.Abs(facade.ColumnRadiation(new Vector3Int(0, 0, 3)) - expect0.Share) < 1e-6 && facade.ColumnRadiation(new Vector3Int(1, 1, 3)) == 0, "ColumnRadiation in the column, 0 in a solid cell");
    check(facade.IsIrradiatedGround(new Vector3Int(0, 0, 0)) && facade.IsIrradiatedGround(new Vector3Int(0, 0, 2)) && !facade.IsIrradiatedGround(new Vector3Int(1, 0, 0)),
      "Irradiated ground at or above the threshold, by the column containing the cell");
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
    // The radioactive tide is a Moddable Fluids tide: its service owns the source composition, never the facade.
    facade.SetSourceRadioactiveShare(0f); facade.Tick((float)Hours);
    Rejects<InvalidOperationException>(check, () => facade.SetSourceRadioactiveShare(.4f), "A radioactive source share belongs to the tide service");
    check(world.State.ActiveSourceComposition == null, "The facade never sets a source composition");
    Rejects<ArgumentOutOfRangeException>(check, () => facade.SetSourceRadioactiveShare(1.5f), "Share above one");
    host.UnloadScene(scene);
    observations["deepFrontierFacadeSampledShare"] = sample.WaterRadiation;
  }
}
