using System.Runtime.CompilerServices;
using System.Text.RegularExpressions;
using DeepFrontier.ModdableFluidsMigration;
using DeepFrontier.Scripts.Radiation;
using ModdableFluids;
using UnityEngine;

/// <summary>
/// The Deep Frontier migration's soil rules on Moddable Fluids (RadiationSoilField), against references transcribed
/// from the shipped one-fluid code: RadiationSimulation.RunInteraction, RadiationSoil.Exchange and Rescan per column,
/// HourlySoilPass with NeighborSlot, Reconcile's soil rule, Deposit, ApplyPendingSoil and CreditIntakes. The soil
/// formulas themselves are checked to be the same source text as RadiationSoil.cs. Unity types are used only after
/// the native fixture's resolver is installed (the scenarios run after the native fixtures).
/// </summary>
internal static partial class HarnessExtensions {
  static partial void RunDeepFrontier(Action<bool, string> check, Action<string, Action> scenario, string managed, string specification, Dictionary<string, object> observations) {
    scenario("Deep Frontier soil formulas are RadiationSoil's source text", () => DeepFrontierSoil.FormulaText(check));
    scenario("Deep Frontier soil rules match RadiationSimulation's decay, exchange, rinse and cutoff per column", () => DeepFrontierSoil.WaterRules(check, observations));
    scenario("Deep Frontier hourly soil pass matches HourlySoilPass and NeighborSlot", () => DeepFrontierSoil.Hourly(check, observations));
    scenario("Deep Frontier soil follows geometry changes as Reconcile moves it", () => DeepFrontierSoil.Geometry(check));
    scenario("Deep Frontier deposits lost radioactive water from Moddable Fluids losses and credits intakes", () => DeepFrontierSoil.Losses(check, observations));
    scenario("Deep Frontier soil requests, load validation, publication and the bank layer", () => DeepFrontierSoil.RequestsAndLoad(check));
    scenario("Deep Frontier radioactive tide registers on Moddable Fluids with RadioactiveTideTuning's values and keeps its draws alone", () => DeepFrontierSoil.Tide(check, observations));
  }
}

internal static class DeepFrontierSoil {
  internal const float Washout = .006f / (1f / 32f);   // native 0.01/s x 0.6 s per tick, over 1/32 game hour per tick
  private const float TickHours = 1f / 32f;

  private static (FluidRegistry Registry, FluidHandle Radioactive) Registry() {
    var host = new ModdableFluidsHost();
    host.RegisterProvider(new DeepFrontierRadioactiveWater());
    var registry = host.Freeze();
    return (registry, registry.GetHandle(DeepFrontierRadioactiveWater.FluidId));
  }

  private static void Rejects<T>(Action<bool, string> check, Action action, string name, string? contains = null) where T : Exception {
    Exception? caught = null;
    try { action(); } catch (Exception e) { caught = e; }
    check(caught is T && (contains == null || caught.Message.Contains(contains)), name + $": expected {typeof(T).Name}{(contains != null ? " naming " + contains : "")}, got {caught?.GetType().Name ?? "no exception"}{(caught != null ? " (" + caught.Message + ")" : "")}");
  }

  /// <summary>Columns in memory: (x, y, floor, ceiling, volume per fluid slot), with the tick's losses.</summary>
  internal sealed class MemoryColumns : IFluidColumnEditor {
    private readonly FluidRegistry _registry;
    public List<(int X, int Y, int Floor, int Ceiling, double[] V)> Columns { get; } = new();
    public List<FluidLoss> LossList { get; } = new();
    public MemoryColumns(FluidRegistry registry) { _registry = registry; }
    public int Add(int x, int y, int floor, int ceiling, double water = 0, double bad = 0, double radioactive = 0) {
      var v = new double[_registry.Count];
      v[FluidRegistry.WaterIndex] = water; v[FluidRegistry.BadwaterIndex] = bad; v[_registry.GetHandle(DeepFrontierRadioactiveWater.FluidId).Index] = radioactive;
      Columns.Add((x, y, floor, ceiling, v));
      return Columns.Count - 1;
    }
    public int ColumnCount => Columns.Count;
    public int CompletedTicks => 1;
    public int X(int column) => Columns[column].X;
    public int Y(int column) => Columns[column].Y;
    public int Floor(int column) => Columns[column].Floor;
    public int Ceiling(int column) => Columns[column].Ceiling;
    public double GetVolume(int column, FluidHandle fluid) => Columns[column].V[fluid.Index];
    public double TotalVolume(int column) => Columns[column].V.Sum();
    public IReadOnlyList<FluidLoss> Losses => LossList;
    public void Convert(int column, FluidHandle from, FluidHandle to, double volume) {
      if (from.Index == to.Index || from.Index == FluidRegistry.BadwaterIndex || to.Index == FluidRegistry.BadwaterIndex) throw new ArgumentException("Invalid conversion");
      var v = Columns[column].V;
      if (!(volume > 0) || volume > v[from.Index]) throw new ArgumentOutOfRangeException(nameof(volume), volume, "Converts a positive volume the column holds (" + v[from.Index] + ")");
      v[from.Index] -= volume; v[to.Index] += volume;
    }
    public FluidLoss Loss(FluidLossKind kind, int x, int y, int z, int column, double radioactive) {
      var v = new double[_registry.Count]; v[_registry.GetHandle(DeepFrontierRadioactiveWater.FluidId).Index] = radioactive;
      var loss = new FluidLoss(_registry, kind, x, y, z, column, kind == FluidLossKind.Extraction ? "OtherMod.Extractor" : null, v);
      LossList.Add(loss);
      return loss;
    }
  }

  internal static RadiationSoilField Field(int width, int height, float hours = TickHours) {
    var field = new RadiationSoilField(width, height, hours);
    field.SetWashoutPerHour(Washout);
    return field;
  }

  // ---------------------------------------------------------------- formulas

  private static string RepositoryRoot() {
    var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", ".."));
    if (!File.Exists(Path.Combine(root, "src", "DeepFrontier", "Scripts", "Radiation", "RadiationSoil.cs")))
      throw new FileNotFoundException("The harness runs from tools/compile-check/fluid-transport-harness/bin/<configuration>/net8.0 of a repository checkout; RadiationSoil.cs not found under " + root);
    return root;
  }

  /// <summary>The text of a member from its name to the end of its body (or of its expression), without the modifiers before it.</summary>
  private static string Member(string source, string declaration) {
    int start = source.IndexOf(declaration, StringComparison.Ordinal);
    if (start < 0 || source.IndexOf(declaration, start + 1, StringComparison.Ordinal) >= 0) throw new InvalidOperationException("Expected one declaration " + declaration);
    int open = source.IndexOf('{', start), arrow = source.IndexOf("=>", start, StringComparison.Ordinal), semicolon = source.IndexOf(';', start);
    if (open < 0) open = int.MaxValue;
    int end;
    if (arrow >= 0 && arrow < open && (semicolon < 0 || arrow < semicolon) || (semicolon >= 0 && semicolon < open)) end = semicolon + 1;
    else {
      int depth = 0; end = -1;
      for (int i = open; i < source.Length; i++) {
        if (source[i] == '{') depth++;
        else if (source[i] == '}' && --depth == 0) { end = i + 1; break; }
      }
    }
    return Regex.Replace(source.Substring(start, end - start).Replace("\r\n", "\n"), @"[ \t]+", " ");
  }

  internal static void FormulaText(Action<bool, string> check) {
    string root = RepositoryRoot();
    string shipped = File.ReadAllText(Path.Combine(root, "src", "DeepFrontier", "Scripts", "Radiation", "RadiationSoil.cs"));
    string copy = File.ReadAllText(Path.Combine(root, "src", "DeepFrontier", "ModdableFluids", "RadiationSoilFormulas.cs"));
    foreach (var declaration in new[] { "static float Rinse(", "static float SoilWaterExchange(", "static float KernelContamination(", "const float VolumePerSoil", "const float RinseShareCap" })
      check(Member(shipped, declaration) == Member(copy, declaration), "RadiationSoilFormulas" + declaration.Split(' ').Last().TrimEnd('(') + " is RadiationSoil's text");
    // The comments above each formula are copied too; a changed formula changes its member text.
    check(RadiationSoilFormulas.VolumePerSoil == 1f / RadiationTuning.SoilPerDepositedVolume && RadiationSoilFormulas.RinseShareCap == .5f * RadiationTuning.DetectionLimit, "Constants");
  }

  // ------------------------------------------------------------ water rules

  /// <summary>
  /// RadiationSimulation.RunInteraction, RadiationSoil.Exchange and Rescan for one column, transcribed. The inputs are
  /// the port's: r, b and d from the column's volumes (b: everything neither fresh nor radioactive water).
  /// </summary>
  internal static (float Soil, float Share) Reference(float s, double water, double bad, double radioactive, float previous, float hours) {
    double total = water + bad + radioactive;
    float decay = RadiationTuning.DecayPerHour(RadiationTuning.RadiationHalfLifeDays) * hours;
    float rise = RadiationTuning.SoilRiseFromWaterPerHour * hours, wash = Washout * hours;
    float r = total > 0 ? (float)(radioactive / total) : 0f;
    if (r > 0f) { r -= r * decay; if (r < RadiationTuning.MinWaterRadiation) r = 0f; }
    if (total > 0 && (s > 0f || r > 0f)) {
      float b = (float)((total - water - radioactive) / total), d = (float)total, share;
      if (RadiationTuning.Detected(r) == 0f) {
        if (s > 0f) { float delta = RadiationSoilFormulas.Rinse(s, r, b, d, wash, out share); s += delta; r = share; }
      } else {
        float delta = RadiationSoilFormulas.SoilWaterExchange(s, r, b, d, rise, wash);
        if (delta != 0f) {
          share = r - delta * RadiationSoilFormulas.VolumePerSoil / d;
          if (share < 0f) share = 0f;
          s += delta; r = share;
        }
      }
    }
    if (r > 0f && r < RadiationTuning.DetectionLimit && !(r > previous)) r = 0f;
    return (s, r);
  }

  [MethodImpl(MethodImplOptions.NoInlining)]
  internal static void WaterRules(Action<bool, string> check, Dictionary<string, object> observations) {
    var (registry, radioactive) = Registry();
    var waterHandle = registry.Water;
    // Named cases: uptake toward the equilibrium, washout above it, rinsing under clean water, saturation,
    // the cutoff of a share that stopped growing below the limit, a growing one kept, a dry column.
    var cases = new (string Name, float Soil, double Water, double Bad, double Radioactive)[] {
      ("uptake", .1f, 1.5, .2, .3), ("washout above the equilibrium", .9f, 2.5, .1, .02), ("rinsing under clean water", .6f, 3, 0, .001),
      ("rinse capped by badwater", .6f, .004, 3, .0001), ("saturated soil under strong water", 1f, .2, 0, 1.8), ("no soil, radioactive water", 0f, 2, .5, .5),
      ("share below the limit with soil", .3f, 4, 0, .012), ("dry ground keeps its soil", .4f, 0, 0, 0),
    };
    var rng = new System.Random(20261109);
    var all = cases.ToList();
    for (int k = 0; k < 400; k++) {
      double depth = rng.NextDouble() < .1 ? 0 : Math.Pow(10, -3 + 4 * rng.NextDouble());
      double bad = rng.NextDouble() < .3 ? 0 : rng.NextDouble(), rad = rng.NextDouble() < .2 ? 0 : Math.Pow(10, -4 * rng.NextDouble());
      double sum = 1 + bad + rad;
      float soil = rng.NextDouble() < .2 ? 0f : (float)rng.NextDouble();
      all.Add(("random " + k, soil, depth / sum, depth * bad / sum, depth * rad / sum));
    }
    // Columns two cells apart, so the hourly pass only decays them (the hourly scenario covers spread).
    int width = 2 * all.Count;
    var field = Field(width, 1);
    var columns = new MemoryColumns(registry);
    var soilCells = new List<Vector3Int>(); var soilValues = new List<float>();
    for (int k = 0; k < all.Count; k++) {
      columns.Add(2 * k, 0, 0, 8, all[k].Water, all[k].Bad, all[k].Radioactive);
      if (all[k].Soil > 0) { soilCells.Add(new Vector3Int(2 * k, 0, 0)); soilValues.Add(all[k].Soil); }
    }
    field.Load(soilCells, soilValues, 0f, lenient: false);
    var expected = all.Select(c => (Soil: c.Soil, Previous: 0f)).ToArray();
    int mismatches = 0, passes = 70, cut = 0, rinsed = 0, exhaustedRinses = 0;
    float hourCounter = 0f;
    for (int pass = 0; pass < passes; pass++) {
      for (int k = 0; k < all.Count; k++) {
        var v = columns.Columns[k].V;
        var (s, r) = Reference(expected[k].Soil, v[FluidRegistry.WaterIndex], v[FluidRegistry.BadwaterIndex], v[radioactive.Index], expected[k].Previous, TickHours);
        if (expected[k].Previous > 0 && r == 0) cut++;
        if (r > (float)(v[radioactive.Index] / v.Sum())) rinsed++;
        expected[k] = (s, r);
      }
      // RadiationSimulation.Tick's hour counter and HourlySoilPass without neighbours: decay only.
      hourCounter += TickHours;
      if (hourCounter >= 1f) {
        float soilDecay = RadiationTuning.DecayPerHour(RadiationTuning.SoilHalfLifeDays) * hourCounter;
        for (int k = 0; k < all.Count; k++) {
          float next = expected[k].Soil + RadiationTuning.SoilSpreadPerHour * hourCounter * 0f;
          next -= next * soilDecay;
          expected[k].Soil = next < RadiationTuning.MinSoilRadiation ? 0f : next > 1f ? 1f : next;
        }
        hourCounter = 0f;
      }
      field.ApplyRules(columns, radioactive, waterHandle);
      var published = field.Published;
      for (int k = 0; k < all.Count; k++) {
        var key = new Vector3Int(2 * k, 0, 0);
        float soil = published.Soil.TryGetValue(key, out float sv) ? sv : 0f, share = published.Water.TryGetValue(key, out float rv) ? rv : 0f;
        var v = columns.Columns[k].V;
        double total = v.Sum();
        // A rinse whose float shares overrun the fresh water by less than ShareTolerance takes all the water there is.
        bool exhausted = v[FluidRegistry.WaterIndex] == 0 && share * total - v[radioactive.Index] <= RadiationTuning.ShareTolerance * total;
        bool volume = (Math.Abs(v[radioactive.Index] - share * total) <= 1e-15 * Math.Max(1, total) || exhausted)
          && Math.Abs(total - (all[k].Water + all[k].Bad + all[k].Radioactive)) <= 1e-12 * Math.Max(1, total) && v[FluidRegistry.BadwaterIndex] == all[k].Bad;
        if (exhausted) exhaustedRinses++;
        if (soil != expected[k].Soil || share != expected[k].Previous || !volume) {
          if (mismatches++ < 5) check(false, $"pass {pass} {all[k].Name}: soil {soil:R}/{expected[k].Soil:R}, share {share:R}/{expected[k].Previous:R}, volume kept {volume}");
        }
      }
    }
    check(mismatches == 0, $"{all.Count} columns x {passes} passes (two hourly passes) equal the transcribed one-fluid sequence bit for bit ({mismatches} mismatches)");
    check(cut > 0 && rinsed > 0 && exhaustedRinses > 0, $"The cases reach the cutoff ({cut}), rinsing ({rinsed}) and a rinse that takes all fresh water ({exhaustedRinses})");
    check(field.Published.Pass == passes && field.HasPass, "Every pass is published");
    // A column with badwater, soil and radioactive water.
    var mixed = new MemoryColumns(registry);
    mixed.Add(0, 0, 0, 8, .5, .5, .5);
    var mixedField = Field(1, 1);
    mixedField.Load(new[] { new Vector3Int(0, 0, 0) }, new[] { .2f }, 0, false);
    mixedField.ApplyRules(mixed, radioactive, waterHandle);
    var reference = Reference(.2f, .5, .5, .5, 0, TickHours);
    check(mixedField.Published.Soil[new Vector3Int(0, 0, 0)] == reference.Soil, "Badwater counts as b");
    Rejects<InvalidOperationException>(check, () => new RadiationSoilField(1, 1, TickHours).ApplyRules(mixed, radioactive, waterHandle), "Rules before the washout rate is set");
    observations["deepFrontierSoilRuleColumns"] = all.Count;
    observations["deepFrontierSoilRulePasses"] = passes;
  }

  // ------------------------------------------------------------------ hourly

  [MethodImpl(MethodImplOptions.NoInlining)]
  internal static void Hourly(Action<bool, string> check, Dictionary<string, object> observations) {
    var (registry, radioactive) = Registry();
    var rng = new System.Random(7);
    int width = 7, height = 6, checkedColumns = 0, mismatches = 0;
    for (int world = 0; world < 30; world++) {
      var columns = new MemoryColumns(registry);
      var geometry = new Dictionary<(int, int), List<(int Floor, int Ceiling)>>();
      for (int y = 0; y < height; y++) for (int x = 0; x < width; x++) {
        if (rng.NextDouble() < .1) continue;   // a solid cell
        var list = new List<(int, int)>();
        int floor = rng.Next(0, 3);
        int ceiling = floor + 1 + rng.Next(0, 4);
        list.Add((floor, ceiling));
        if (rng.NextDouble() < .3) { int upper = ceiling + 1 + rng.Next(0, 2); list.Add((upper, upper + 2 + rng.Next(0, 3))); }
        geometry[(x, y)] = list;
        foreach (var (f, c) in list) columns.Add(x, y, f, c);   // dry: only the hourly pass changes the soil
      }
      var soil = new Dictionary<(int, int, int), float>();
      foreach (var pair in geometry) foreach (var (f, _) in pair.Value) if (rng.NextDouble() < .35) soil[(pair.Key.Item1, pair.Key.Item2, f)] = rng.NextDouble() < .1 ? 1f : (float)rng.NextDouble();
      var field = Field(width, height, 1f);
      field.Load(soil.Keys.Select(k => new Vector3Int(k.Item1, k.Item2, k.Item3)).ToList(), soil.Values.ToList(), 0f, false);
      for (int pass = 0; pass < 3; pass++) {
        // HourlySoilPass transcribed: every column, its four neighbours in native order, NeighborSlot.
        float spread = RadiationTuning.SoilSpreadPerHour * 1f, decay = RadiationTuning.DecayPerHour(RadiationTuning.SoilHalfLifeDays) * 1f;
        var next = new Dictionary<(int, int, int), float>();
        foreach (var pair in geometry) {
          foreach (var (f, _) in pair.Value) {
            var key = (pair.Key.Item1, pair.Key.Item2, f);
            float value = soil.TryGetValue(key, out float sv) ? sv : 0f, exchange = 0f;
            foreach (var (dx, dy) in new[] { (0, -1), (-1, 0), (0, 1), (1, 0) }) {
              if (!geometry.TryGetValue((pair.Key.Item1 + dx, pair.Key.Item2 + dy), out var neighbours)) continue;
              int best = -1, bestDiff = 2;
              for (int j = 0; j < neighbours.Count; j++) { int diff = Math.Abs(neighbours[j].Floor - f); if (diff < bestDiff && neighbours[j].Ceiling > neighbours[j].Floor) { best = j; bestDiff = diff; } }
              if (best >= 0) exchange += (soil.TryGetValue((pair.Key.Item1 + dx, pair.Key.Item2 + dy, neighbours[best].Floor), out float nv) ? nv : 0f) - value;
            }
            float result = value + spread * exchange;
            result -= result * decay;
            result = result < RadiationTuning.MinSoilRadiation ? 0f : result > 1f ? 1f : result;
            if (result > 0f) next[key] = result;
          }
        }
        soil = next;
        field.ApplyRules(columns, radioactive, registry.Water);
        var published = field.Published.Soil;
        foreach (var pair in geometry) foreach (var (f, _) in pair.Value) {
          checkedColumns++;
          float want = soil.TryGetValue((pair.Key.Item1, pair.Key.Item2, f), out float w) ? w : 0f;
          float got = published.TryGetValue(new Vector3Int(pair.Key.Item1, pair.Key.Item2, f), out float g) ? g : 0f;
          if (want != got && mismatches++ < 5) check(false, $"world {world} pass {pass} ({pair.Key.Item1}, {pair.Key.Item2}, {f}): {got:R}, HourlySoilPass gives {want:R}");
        }
        check(published.Count == soil.Count, $"world {world} pass {pass}: no extra soil entries");
        check(field.Published.HourAccumulator == 0f, "The hour counter restarts after the pass");
      }
    }
    check(mismatches == 0, $"{checkedColumns} column-hours equal HourlySoilPass bit for bit ({mismatches} mismatches)");
    // The counter: a pass every accumulated hour, and only while something radioactive is tracked.
    var quiet = new MemoryColumns(registry); quiet.Add(0, 0, 0, 4);
    var counting = Field(1, 1, .4f);
    counting.ApplyRules(quiet, radioactive, registry.Water);
    check(counting.Published.HourAccumulator == 0f, "No soil and no radioactive water: the hour counter stands still");
    counting = Field(1, 1, .4f);
    counting.Load(new[] { new Vector3Int(0, 0, 0) }, new[] { .5f }, .5f, false);
    counting.ApplyRules(quiet, radioactive, registry.Water);
    check(Math.Abs(counting.Published.HourAccumulator - .9f) < 1e-6 && counting.Published.Soil[new Vector3Int(0, 0, 0)] == .5f, "Below an hour nothing decays");
    counting.ApplyRules(quiet, radioactive, registry.Water);
    float hours = .5f; hours += .4f; hours += .4f;
    float decayed = .5f; decayed -= decayed * (RadiationTuning.DecayPerHour(RadiationTuning.SoilHalfLifeDays) * hours);
    check(counting.Published.HourAccumulator == 0f && counting.Published.Soil[new Vector3Int(0, 0, 0)] == decayed, "At an hour the pass runs over the accumulated hours");
    observations["deepFrontierHourlyColumnHours"] = checkedColumns;
  }

  // ---------------------------------------------------------------- geometry

  [MethodImpl(MethodImplOptions.NoInlining)]
  internal static void Geometry(Action<bool, string> check) {
    var (registry, radioactive) = Registry();
    var field = Field(4, 1);
    var before = new MemoryColumns(registry);
    before.Add(0, 0, 0, 6);            // a platform will be built at z = 0: the floor rises to 1
    before.Add(1, 0, 2, 9);            // unchanged floor, lower ceiling
    before.Add(2, 0, 0, 3); before.Add(2, 0, 4, 9);   // two columns merge into one
    before.Add(3, 0, 1, 5);            // filled solid: no column left
    field.Load(new[] { new Vector3Int(0, 0, 0), new Vector3Int(1, 0, 2), new Vector3Int(2, 0, 0), new Vector3Int(2, 0, 4), new Vector3Int(3, 0, 1) },
      new[] { .4f, .3f, .2f, .6f, .9f }, 0f, false);
    field.ApplyRules(before, radioactive, registry.Water);
    check(field.TakeChangedCells().Length == 0, "No change on the first pass");
    var after = new MemoryColumns(registry);
    after.Add(0, 0, 1, 6); after.Add(1, 0, 2, 7); after.Add(2, 0, 0, 9);
    field.ApplyRules(after, radioactive, registry.Water);
    var soil = field.Published.Soil;
    check(soil.TryGetValue(new Vector3Int(0, 0, 1), out float raised) && raised == .4f && !soil.ContainsKey(new Vector3Int(0, 0, 0)), "Soil moves to the floor raised directly above it");
    check(soil.TryGetValue(new Vector3Int(1, 0, 2), out float kept) && kept == .3f, "Soil stays on an unchanged floor");
    check(soil.TryGetValue(new Vector3Int(2, 0, 0), out float merged) && merged == .2f && !soil.ContainsKey(new Vector3Int(2, 0, 4)), "A merge keeps the surviving floor's soil; the upper surface is gone");
    check(!soil.Keys.Any(k => k.x == 3), "A filled cell loses its soil");
    var changed = field.TakeChangedCells();
    check(changed.Length == 4 && field.TakeChangedCells().Length == 0, "Changed cells are reported once for the plant check");
    // One old surface moves to at most one new column (Reconcile's _oldSoilMoved).
    var split = Field(1, 1);
    var one = new MemoryColumns(registry); one.Add(0, 0, 0, 10);
    split.Load(new[] { new Vector3Int(0, 0, 0) }, new[] { .5f }, 0, false);
    split.ApplyRules(one, radioactive, registry.Water);
    var two = new MemoryColumns(registry); two.Add(0, 0, 1, 4); two.Add(0, 0, 5, 10);
    split.ApplyRules(two, radioactive, registry.Water);
    check(split.Published.Soil.Count == 1 && split.Published.Soil[new Vector3Int(0, 0, 1)] == .5f, "A split moves the old surface once, to the floor above it");
  }

  // ------------------------------------------------------------------ losses

  [MethodImpl(MethodImplOptions.NoInlining)]
  internal static void Losses(Action<bool, string> check, Dictionary<string, object> observations) {
    var (registry, radioactive) = Registry();
    var field = Field(4, 2);
    var columns = new MemoryColumns(registry);
    int a = columns.Add(0, 0, 0, 5);
    columns.Add(1, 0, 0, 2); columns.Add(1, 0, 4, 9);
    int c = columns.Add(2, 0, 3, 8);
    columns.Add(3, 0, 0, 4);
    field.Load(new[] { new Vector3Int(0, 0, 0) }, new[] { .95f }, 0f, false);
    columns.Loss(FluidLossKind.Evaporation, 0, 0, 0, a, .004);           // .95 + .04 = .99
    columns.Loss(FluidLossKind.Evaporation, 0, 0, 0, a, .004);           // capped at 1 by the second deposit
    columns.Loss(FluidLossKind.DroppedAddition, 1, 0, 3, -1, .02);       // closed cell (1, 0, 3): the lowest column above has floor 4
    columns.Loss(FluidLossKind.Geometry, 2, 0, 1, -1, .01);              // deleted water of an old column at (2, 0, 1)
    columns.Loss(FluidLossKind.Geometry, 2, 0, 2, -1, .015);
    columns.Loss(FluidLossKind.Geometry, 3, 0, 0, -1, 5e-7);             // below MinWaterRadiation: Reconcile deposits nothing
    columns.Loss(FluidLossKind.NativeRemoval, 0, 0, 2, a, .3);
    columns.Loss(FluidLossKind.NativeRemoval, 0, 0, 2, a, .1);
    columns.Loss(FluidLossKind.Discharge, 0, 0, 0, a, 1);
    columns.Loss(FluidLossKind.Pressure, 0, 0, 0, a, 1);
    columns.Loss(FluidLossKind.SourceWithdrawal, 0, 0, 2, a, 1);
    columns.Loss(FluidLossKind.Extraction, 0, 0, 2, a, 1);
    field.ApplyRules(columns, radioactive, registry.Water);
    var soil = field.Published.Soil;
    float first = .95f + .004f * RadiationTuning.SoilPerDepositedVolume;
    float second = first + .004f * RadiationTuning.SoilPerDepositedVolume;
    check(soil[new Vector3Int(0, 0, 0)] == (second > 1f ? 1f : second), "Evaporated radioactive volume x SoilPerDepositedVolume, capped at 1 per deposit");
    check(soil[new Vector3Int(1, 0, 4)] == .02f * RadiationTuning.SoilPerDepositedVolume && !soil.ContainsKey(new Vector3Int(1, 0, 0)),
      "A dropped addition deposits into the lowest column above its cell");
    check(soil[new Vector3Int(2, 0, 3)] == (float)(.01 + .015) * RadiationTuning.SoilPerDepositedVolume, "Geometry losses of a cell deposit into its lowest column");
    check(!soil.ContainsKey(new Vector3Int(3, 0, 0)), "A geometry loss below MinWaterRadiation deposits nothing");
    var credits = field.TakeRemovedRadioactive();
    check(credits.Count == 1 && credits[new Vector3Int(0, 0, 2)] == .3f + .1f && field.TakeRemovedRadioactive().Count == 0,
      "Native removals at a cell are credited once (CreditIntakes); discharge, pressure, withdrawals and extractions leave nothing");
    check(soil.Count == 3, "Nothing else was deposited");
    var closed = new MemoryColumns(registry); closed.Add(0, 0, 0, 2);
    closed.Loss(FluidLossKind.DroppedAddition, 0, 0, 5, -1, .1);
    var strict = Field(1, 1);
    Rejects<InvalidOperationException>(check, () => strict.ApplyRules(closed, radioactive, registry.Water), "Radioactive water dropped with no column above it", "no fluid column above");
    observations["deepFrontierDepositedEvaporation"] = soil[new Vector3Int(0, 0, 0)];
    _ = c;
  }

  // -------------------------------------------------------------------- tide

  /// <summary>The registration the flagged game builds, from RadioactiveTideTuning.cs and RadioactiveTideLoc as written.</summary>
  internal static RadioactiveTideRegistration TideFromSource() {
    string root = RepositoryRoot();
    string tuning = File.ReadAllText(Path.Combine(root, "src", "DeepFrontier", "Scripts", "RadioactiveTide", "RadioactiveTideTuning.cs"));
    string Constant(string name) => Regex.Match(tuning, "const (?:string|float) " + name + @" = ""?([^"";]+)""?;").Groups[1].Value;
    var modes = Regex.Matches(tuning, @"new RadioactiveTideCurvePoint\(""(\w+)"",((?:\s*\d+,){9})\s*(\d+), (\d+)\)").Select(m => {
      var numbers = m.Groups[2].Value.Split(',', StringSplitOptions.RemoveEmptyEntries).Select(t => int.Parse(t.Trim())).ToArray();
      // temperate min/max, drought min/max, badtide min/max, badtide %, cycles without, chance %; then the durations.
      return (m.Groups[1].Value, numbers[8], numbers[7], int.Parse(m.Groups[3].Value), int.Parse(m.Groups[4].Value));
    }).ToArray();
    if (modes.Length != 3) throw new InvalidOperationException("RadioactiveTideTuning.GameModeCurve: expected Easy, Normal and Hard, found " + modes.Length);
    return new RadioactiveTideRegistration(Constant("WeatherId"), Constant("Name"), Constant("ModdableDescription"), modes,
      float.Parse(Constant("SourceRadioactiveShare").TrimEnd('f'), System.Globalization.CultureInfo.InvariantCulture),
      new[] { Constant("Approaching"), Constant("InProgress"), Constant("Started"), Constant("Ended"), Constant("ApproachingDescription"), Constant("StartedDescription") },
      new[] { Constant("IconSpritePath"), Constant("ProgressSpritePath"), Constant("NotificationSpritePath") }, FluidTideRules.BadtideSound);
  }

  private sealed class TideRandom : IFluidTideRandom {
    private readonly System.Random _random;
    public int Calls;
    public TideRandom(int seed) { _random = new System.Random(seed); }
    public bool CheckProbability(float normalizedProbability) { Calls++; return _random.NextDouble() < normalizedProbability; }
    public int Range(int inclusiveMin, int exclusiveMax) { Calls++; return _random.Next(inclusiveMin, exclusiveMax); }
  }

  [MethodImpl(MethodImplOptions.NoInlining)]
  internal static void Tide(Action<bool, string> check, Dictionary<string, object> observations) {
    var registration = TideFromSource();
    check(registration.WeatherId == "RadioactiveTideWeather" && registration.SourceShare == 1 && registration.Texts.All(t => t.StartsWith("DeepFrontier.Weather."))
      && registration.Art.All(a => a.StartsWith("Sprites/Weather/RadioactiveTide")), "Weather ID, emission, texts and art from RadioactiveTideTuning");
    check(registration.Modes.Select(m => m.Mode + ":" + m.ChancePercent + "/" + m.CyclesWithoutTide + "/" + m.MinDays + "-" + m.MaxDays).SequenceEqual(
      new[] { "Easy:15/24/2-4", "Normal:25/14/3-6", "Hard:35/9/5-10" }), "Per-mode values as GameModeCurve states them (docs/radiation.md)");
    var host = new ModdableFluidsHost();
    var provider = new DeepFrontierRadioactiveWater(registration);
    host.RegisterProvider(provider);
    var registry = host.Freeze();
    check(provider.RegistersTide && provider.RequiredCapabilities.Contains(FluidTideRules.RegistrationCapability), "The provider requires tide registration");
    bool listed = host.Tides.TryGetByWeather("RadioactiveTideWeather", out var tide);
    check(host.Tides.Count == 1 && listed && tide.Id == RadioactiveTideRegistration.TideId
      && tide.SourceEmission.Count == 1 && tide.SourceEmission[DeepFrontierRadioactiveWater.FluidId] == 1 && tide.SourceStrengthMultiplier == 1
      && tide.Presentation.StartSound == FluidTideRules.BadtideSound, "Moddable Fluids lists the tide by its native weather ID with its emission");
    foreach (var (mode, chance, without, min, max) in registration.Modes) {
      var values = tide.GetMode(mode);
      check(values.ChancePercent == chance && values.CyclesWithoutTide == without && values.MinDurationDays == min && values.MaxDurationDays == max, mode + " values registered");
    }
    // The vanilla presets get the registered values back as their save defaults: budget = weight = the chance.
    foreach (var (weather, index) in new[] { (FluidTideModeWeather.VanillaEasy, 0), (FluidTideModeWeather.VanillaNormal, 1), (FluidTideModeWeather.VanillaHard, 2) }) {
      var defaults = FluidTideModes.Defaults(host.Tides, weather, out _);
      var settings = defaults.Get(RadioactiveTideRegistration.TideId);
      var m = registration.Modes[index];
      check(defaults.BudgetPercent == m.ChancePercent && settings.Enabled && settings.Weight == m.ChancePercent && settings.CyclesWithoutTide == m.CyclesWithoutTide
        && settings.MinDurationDays == m.MinDays && settings.MaxDurationDays == m.MaxDays, m.Mode + ": a new game's defaults are Deep Frontier's");
    }
    // With Deep Frontier's tide alone, the C′ rule draws exactly as RadioactiveTideService.Choose (transcribed below).
    int differences = 0, tides = 0, cycles = 0;
    foreach (var (_, chance, without, _, _) in registration.Modes) {
      var settings = new FluidTideSaveSettings(chance, new[] { new FluidTideSettings(RadioactiveTideRegistration.TideId, true, chance, without, 1, 1) });
      var a = new TideRandom(chance); var b = new TideRandom(chance);
      int lastA = 0, lastB = 0;
      for (int cycle = 1; cycle <= 4000; cycle++) {
        cycles++;
        bool selected = FluidTideSelection.Select(cycle, lastA, settings, null, a) == RadioactiveTideRegistration.TideId;
        bool choose = !(cycle < 2) && !(cycle <= without) && !(lastB > 0 && cycle - lastB <= 1) && b.CheckProbability(chance / 100f);
        if (selected != choose || a.Calls != b.Calls) differences++;
        if (selected) { lastA = cycle; tides++; }
        if (choose) lastB = cycle;
      }
    }
    check(differences == 0 && tides > 0, $"{cycles} cycles: the same tides and the same random draws as RadioactiveTideService.Choose ({differences} differences)");
    observations["deepFrontierTideCyclesCompared"] = cycles;
    _ = registry;
  }

  // -------------------------------------------------------- requests and load

  private sealed class TestBank : IRadiationBankLayer {
    public Dictionary<Vector3Int, float> Levels { get; } = new();
    public float BankAt(Vector3Int columnCell) => Levels.TryGetValue(columnCell, out float v) ? v : 0f;
  }

  [MethodImpl(MethodImplOptions.NoInlining)]
  internal static void RequestsAndLoad(Action<bool, string> check) {
    var (registry, radioactive) = Registry();
    var columns = new MemoryColumns(registry);
    columns.Add(0, 0, 0, 3); columns.Add(0, 0, 5, 9);
    var field = Field(2, 1);
    field.RequestSoil(new Vector3Int(0, 0, 1), .3f);      // inside the lower column
    field.RequestSoil(new Vector3Int(0, 0, 4), .2f);      // solid: the lowest column above
    field.RequestSoil(new Vector3Int(0, 0, 1), .9f);      // capped at 1
    check(field.PendingRequests.Count == 3 && !field.HasPass, "Requests wait for the next pass");
    Rejects<ArgumentOutOfRangeException>(check, () => field.RequestSoil(new Vector3Int(2, 0, 0), .1f), "A request outside the map");
    Rejects<ArgumentOutOfRangeException>(check, () => field.RequestSoil(new Vector3Int(0, 0, 0), 0f), "A request of nothing");
    field.ApplyRules(columns, radioactive, registry.Water);
    check(field.PendingRequests.Count == 0 && field.Published.Soil[new Vector3Int(0, 0, 0)] == 1f && field.Published.Soil[new Vector3Int(0, 0, 5)] == .2f,
      "ApplyPendingSoil: the containing column, else the lowest above; capped at 1");
    field.RequestSoil(new Vector3Int(0, 0, 9), .1f);
    Rejects<InvalidOperationException>(check, () => field.ApplyRules(columns, radioactive, registry.Water), "A request with no column at or above it", "no fluid column at or above");
    // Load: strict saves name every cell without a column floor; an exception snapshot drops them and reports it.
    var strict = Field(2, 1);
    strict.Load(new[] { new Vector3Int(0, 0, 1), new Vector3Int(1, 0, 0), new Vector3Int(0, 0, 5) }, new[] { .1f, .2f, .3f }, 0f, lenient: false);
    Rejects<InvalidOperationException>(check, () => strict.ApplyRules(columns, radioactive, registry.Water), "A normal save with soil off the column floors", "(1, 0, 0)");
    var lenient = Field(2, 1);
    lenient.Load(new[] { new Vector3Int(0, 0, 1), new Vector3Int(0, 0, 5) }, new[] { .1f, .3f }, 0f, lenient: true);
    lenient.ApplyRules(columns, radioactive, registry.Water);
    var corrections = lenient.TakeLoadCorrections();
    check(corrections.Length == 1 && corrections[0].Contains("(0, 0, 1)") && lenient.Published.Soil.Count == 1 && lenient.Published.Soil[new Vector3Int(0, 0, 5)] == .3f,
      "An exception snapshot drops soil off the column floors and reports it");
    Rejects<InvalidOperationException>(check, () => lenient.Load(new[] { new Vector3Int(0, 0, 0) }, new[] { .1f }, 0f, false), "Loading after a pass");
    Rejects<InvalidOperationException>(check, () => Field(2, 1).Load(new[] { new Vector3Int(0, 0, 0), new Vector3Int(0, 0, 0) }, new[] { .1f, .2f }, 0f, false), "A cell saved twice");
    Rejects<InvalidOperationException>(check, () => Field(2, 1).Load(new[] { new Vector3Int(0, 0, 0) }, new[] { 1.5f }, 0f, false), "Soil above 1");
    // Readers: stored soil or the bank layer, whichever is higher (RadiationSimulation.SoilAt).
    var bank = new TestBank();
    lenient.Bank = bank;
    bank.Levels[new Vector3Int(0, 0, 5)] = .7f; bank.Levels[new Vector3Int(0, 0, 0)] = .05f;
    check(lenient.SoilAt(new Vector3Int(0, 0, 5)) == .7f && lenient.SoilAt(new Vector3Int(0, 0, 0)) == .05f && lenient.SoilAt(new Vector3Int(1, 0, 0)) == 0f, "SoilAt = max(soil, bank)");
    // Published passes are never changed afterwards.
    var snapshot = lenient.Published;
    lenient.RequestSoil(new Vector3Int(0, 0, 6), .1f);
    lenient.ApplyRules(columns, radioactive, registry.Water);
    check(snapshot.Soil.Count == 1 && snapshot.Soil[new Vector3Int(0, 0, 5)] == .3f && lenient.Published.Pass == snapshot.Pass + 1, "A published pass stays as it was");
  }
}
