using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using ModdableFluids.Transport.Prototype;

if (args.Length != 4) throw new ArgumentException("Expected: installed Managed directory, imported WaterSimulator blueprint, report path, reflection-only consumer DLL");
string managed = Path.GetFullPath(args[0]), specification = Path.GetFullPath(args[1]), reportPath = Path.GetFullPath(args[2]), reflectionConsumer = Path.GetFullPath(args[3]);
int assertions = 0;
var scenarios = new List<string>();
var observations = new Dictionary<string, object>();

void Check(bool condition, string message) {
  assertions++;
  if (!condition) throw new InvalidOperationException(message);
}
void Close(double actual, double expected, string message, double tolerance = 2e-11) =>
  Check(Math.Abs(actual - expected) <= tolerance * Math.Max(Math.Abs(actual), Math.Abs(expected)) + 1e-29,
    message + $": actual {actual:R}, expected {expected:R}");
void Reject(Action action, string name) {
  bool rejected = false;
  try { action(); } catch (Exception e) when (e is ArgumentException || e is InvalidOperationException) { rejected = true; }
  Check(rejected, "Invalid input accepted: " + name);
}
FluidVolumes Mix(params double[] volumes) => new(volumes);
FluidVolumes Empty(int count = 4) => new(new double[count]);
FluidVolumes[] Output(FluidStepResult result) => Enumerable.Range(0, result.ColumnCount).Select(result.GetColumn).ToArray();
void Validate(FluidVolumes column, string name) {
  double sum = 0, shares = 0;
  for (int c = 0; c < column.ComponentCount; c++) {
    double v = column.GetVolume(c), share = column.GetShare(c);
    Check(double.IsFinite(v) && v >= 0 && share >= 0 && share <= 1, name + ": invalid component " + c);
    sum += v; shares += share;
  }
  Close(sum, column.TotalVolume, name + " component total");
  Close(shares, column.TotalVolume > 0 ? 1 : 0, name + " share total");
}
void Balance(FluidVolumes[] before, FluidStepResult result, string name) {
  foreach (var column in Output(result)) Validate(column, name);
  for (int c = 0; c < before[0].ComponentCount; c++) {
    double original = before.Sum(column => column.GetVolume(c));
    double final = result.Discharged.GetVolume(c);
    for (int i = 0; i < result.ColumnCount; i++) final += result.GetColumn(i).GetVolume(c) + result.GetEvaporated(i).GetVolume(c);
    Close(final, original, name + " conservation component " + c);
  }
}
void RemovalBalance(FluidVolumes before, FluidRemovalResult result, string name) {
  Validate(result.Remaining, name); Validate(result.Removed, name);
  for (int c = 0; c < before.ComponentCount; c++) Close(result.Remaining.GetVolume(c) + result.Removed.GetVolume(c), before.GetVolume(c), name + " conservation");
}
void Scenario(string name, Action test) { test(); scenarios.Add(name); Console.WriteLine("PASS " + name); }

try {
  Scenario("shared branching, simultaneous flow, evaporation and off-map discharge", () => {
    var before = new[] { Mix(1, 1, 1, 1), Mix(0, 0, 2, 0), Empty(), Empty() };
    var result = FluidTransportPrototype.Advect(before, new[] {
      new FluidTransfer(0, 1, 1), new FluidTransfer(0, 2, 2), new FluidTransfer(1, 2, 1), new FluidTransfer(0, -1, .5)
    }, new[] { 0d, .5, 0, 3 });
    Balance(before, result, "branching");
    Close(result.GetColumn(2).GetVolume(2), 1.5, "Snapshot donor composition");
    Close(result.GetEvaporated(3).TotalVolume, 0, "Dry-column evaporation");
    Close(result.Discharged.TotalVolume, .5, "Measured discharge");
  });
  Scenario("near-empty and selective native pumping", () => {
    var random = new Random(491);
    for (int i = 0; i < 2000; i++) {
      double clean = (float)Math.Exp(random.NextDouble() * 16 - 12);
      double r = clean * random.NextDouble(), coffee = (clean - r) * random.NextDouble();
      var before = Mix(clean - r - coffee, .2, r, coffee);
      double taken = clean * (.99 + random.NextDouble() * .01);
      var removed = FluidTransportPrototype.RemoveNative(before, 1, taken, 0);
      RemovalBalance(before, removed, "near-empty");
      Close(removed.Remaining.GetVolume(1), .2, "Clean pump retained badwater");
      Close(removed.Remaining.GetVolume(2), r * ((clean - taken) / clean), "Direct retained radioactive volume", 2e-10);
      var badRemoved = FluidTransportPrototype.RemoveNative(before, 1, 0, .149856851);
      RemovalBalance(before, badRemoved, "bad-only");
      Close(badRemoved.Remaining.GetVolume(2), r, "Badwater pump retained radioactivity");
    }
    var all = Mix(0, 2, 3, 4);
    var result = FluidTransportPrototype.RemoveNative(all, 1, 100, 100);
    RemovalBalance(all, result, "saturated request"); Close(result.Remaining.TotalVolume, 0, "Complete removal");
    // Original crash snapshots already contain more radioactivity than non-bad water.
    // A valid component vector must reject their negative fresh remainder.
    Reject(() => Mix(.031250011175870895f - .03125024959445f, 0, .03125024959445f, 0), "old near-empty surplus");
    Reject(() => Mix(3.97814256E-05f - 4.14364476E-05f, .206209153f, 4.14364476E-05f, 0), "crash cell 6412 surplus");
  });
  Scenario("measured source additions and ordered add/remove operations", () => {
    var original = Mix(2, 1, 1, 0);
    var added = FluidTransportPrototype.Add(original, Mix(0, 0, 0, 4));
    Close(added.TotalVolume, 8, "Source volume");
    var pumped = FluidTransportPrototype.RemoveNative(added, 1, 3.5, 0);
    RemovalBalance(added, pumped, "source then pump");
    Close(pumped.Remaining.GetVolume(3), 2, "Actual new-fluid recovery");
    Close(original.TotalVolume, 4, "Addition did not mutate snapshot");
  });
  Scenario("geometry split, merge and deleted-volume accounting", () => {
    var original = new[] { Mix(1, 1, 2, 0), Empty(), Empty() };
    var split = FluidTransportPrototype.Advect(original, new[] { new FluidTransfer(0, 1, 1), new FluidTransfer(0, 2, 2), new FluidTransfer(0, -1, 1) }, new double[3]);
    Balance(original, split, "geometry split");
    var merge = FluidTransportPrototype.Advect(Output(split), new[] { new FluidTransfer(1, 0, 1), new FluidTransfer(2, 0, 2) }, new double[3]);
    Balance(Output(split), merge, "geometry merge");
    for (int c = 0; c < 4; c++) Close(merge.GetColumn(0).GetVolume(c) + split.Discharged.GetVolume(c), original[0].GetVolume(c), "Retained plus geometry loss");
  });
  Scenario("symmetric diffusion with unequal degrees, depths and many components", () => {
    var random = new Random(714);
    foreach (int count in new[] { 2, 4, 16, 64 }) {
      var columns = Enumerable.Range(0, 8).Select(_ => new FluidVolumes(Enumerable.Range(0, count).Select(_ => random.NextDouble() * random.NextDouble()).ToArray())).ToArray();
      var links = new[] { new FluidDiffusionLink(0, 1), new FluidDiffusionLink(0, 2), new FluidDiffusionLink(0, 3), new FluidDiffusionLink(0, 4), new FluidDiffusionLink(4, 5), new FluidDiffusionLink(5, 6), new FluidDiffusionLink(6, 7) };
      for (int step = 0; step < 80; step++) {
        var result = FluidTransportPrototype.Diffuse(columns, links, .135);
        Balance(columns, result, "diffusion " + count);
        for (int i = 0; i < columns.Length; i++) Close(result.GetColumn(i).TotalVolume, columns[i].TotalVolume, "Diffusion preserved column depth");
        columns = Output(result);
      }
    }
  });
  Scenario("random simultaneous transport conserves each of sixteen components", () => {
    var random = new Random(831);
    for (int sample = 0; sample < 500; sample++) {
      var columns = Enumerable.Range(0, 8).Select(_ => new FluidVolumes(Enumerable.Range(0, 16).Select(_ => random.NextDouble()).ToArray())).ToArray();
      var transfers = new List<FluidTransfer>();
      for (int i = 0; i < columns.Length; i++) {
        double available = columns[i].TotalVolume;
        transfers.Add(new FluidTransfer(i, (i + 1) % columns.Length, available * random.NextDouble() * .45));
        transfers.Add(new FluidTransfer(i, -1, available * random.NextDouble() * .45));
      }
      var result = FluidTransportPrototype.Advect(columns, transfers.ToArray(), columns.Select(c => c.TotalVolume * random.NextDouble()).ToArray());
      Balance(columns, result, "random transport");
    }
  });
  Scenario("component and edge ordering independence", () => {
    var columns = new[] { Mix(1, 2, 3, 4), Mix(4, 3, 2, 1), Empty() };
    var transfers = new[] { new FluidTransfer(0, 1, 3), new FluidTransfer(1, 2, 2), new FluidTransfer(0, 2, 1) };
    var normal = FluidTransportPrototype.Advect(columns, transfers, new double[3]);
    var reversed = FluidTransportPrototype.Advect(columns.Select(c => Mix(c.CopyVolumes().Reverse().ToArray())).ToArray(), transfers.Reverse().ToArray(), new double[3]);
    for (int i = 0; i < 3; i++) for (int c = 0; c < 4; c++) Close(normal.GetColumn(i).GetVolume(c), reversed.GetColumn(i).GetVolume(3 - c), "Permutation changed transport");
  });
  Scenario("invalid requests fail without mutation or normalization", () => {
    var column = Mix(1, 0, 0, 0);
    Reject(() => Mix(double.NaN, 1), "NaN"); Reject(() => Mix(double.PositiveInfinity, 0), "infinity");
    Reject(() => Mix(-1, 2), "negative component");
    Reject(() => FluidTransportPrototype.Advect(new[] { column }, new[] { new FluidTransfer(0, -1, 2) }, new double[1]), "overdrawn donor");
    Reject(() => FluidTransportPrototype.Advect(new[] { column }, Array.Empty<FluidTransfer>(), new[] { -1d }), "negative evaporation");
    Reject(() => FluidTransportPrototype.Diffuse(new[] { column, column }, new[] { new FluidDiffusionLink(0, 1), new FluidDiffusionLink(1, 0) }, .5), "duplicate pair");
    Reject(() => FluidTransportPrototype.Diffuse(new[] { column }, Array.Empty<FluidDiffusionLink>(), 2), "oversized diffusion step");
    Reject(() => FluidTransportPrototype.Add(column, Mix(1, 0)), "different layouts");
    var copy = column.CopyVolumes(); copy[0] = 99;
    Close(column.GetVolume(0), 1, "External mutation leaked into snapshot");
  });
  Scenario("reflection can enumerate and invoke the standalone prototype", () => {
    var assembly = Assembly.LoadFrom(typeof(FluidVolumes).Assembly.Location);
    Check(assembly.GetTypes().Any(t => t.FullName == "ModdableFluids.Transport.Prototype.FluidVolumes"), "Type enumeration did not expose the mixture contract");
    var type = assembly.GetType("ModdableFluids.Transport.Prototype.FluidVolumes", true)!;
    object column = Activator.CreateInstance(type, new object[] { new[] { 1d, 2, 3 } })!;
    double total = (double)type.GetProperty("TotalVolume")!.GetValue(column)!;
    Close(total, 6, "Reflected construction and query");
    var removal = assembly.GetType("ModdableFluids.Transport.Prototype.FluidTransportPrototype", true)!.GetMethod("RemoveMixed", BindingFlags.Public | BindingFlags.Static)!;
    object result = removal.Invoke(null, new[] { column, (object)3d })!;
    object remaining = result.GetType().GetProperty("Remaining")!.GetValue(result)!;
    Close((double)type.GetProperty("TotalVolume")!.GetValue(remaining)!, 3, "Reflected operation");
  });

  Scenario("installed native depth task agrees with raw measured transfers", () => {
    using var native = new NativeWaterFixture(managed, specification);
    native.AddColumn(0, 1, 2); native.AddColumn(1, 1, 1);
    var before = new[] { Mix(1, .5, .5, 0), Mix(0, 0, 0, 1) };
    native.SetRawFlow(0, 1, .5f);
    var transfers = native.ReadRawTransfers();
    var evaporation = native.UpdateNativeDepths(new double[2]);
    var result = FluidTransportPrototype.Advect(before, transfers, evaporation);
    Balance(before, result, "native one-way");
    for (int i = 0; i < 2; i++) Close(result.GetColumn(i).TotalVolume, native.PhysicalVolume(i), "Native depth parity", 2e-6);
    var independent = native.RunIndependentNativeContamination(before);
    for (int i = 0; i < 2; i++) for (int c = 0; c < 4; c++) Close(result.GetColumn(i).GetShare(c), independent[i][c], "Native simple advection parity", 2e-6);
  });
  Scenario("installed native thin-film evaporation reproduces excess independent shares", () => {
    using var native = new NativeWaterFixture(managed, specification);
    native.AddColumn(0, 1, 1f / 1024); native.AddColumn(1, 1, 1f / 1024);
    var before = new[] { Mix(0, .5 / 1024, .5 / 1024, 0), Mix(.8 / 1024, .1 / 1024, .1 / 1024, 0) };
    native.SetRawFlow(0, 1, 1f / 1024);
    var transfers = native.ReadRawTransfers();
    var evaporation = native.UpdateNativeDepths(new[] { 0d, 1.5 / 1024 });
    var result = FluidTransportPrototype.Advect(before, transfers, evaporation);
    Balance(before, result, "native thin film");
    for (int i = 0; i < 2; i++) Close(result.GetColumn(i).TotalVolume, native.PhysicalVolume(i), "Thin-film native depth", 2e-6);
    var independent = native.RunIndependentNativeContamination(before);
    double sum = independent[1][1] + independent[1][2];
    Check(sum > 1.1, "Native thin-film regression did not reproduce");
    observations["thinFilmIndependentBadPlusRadioactive"] = sum;
    observations["thinFilmJointBadPlusRadioactive"] = result.GetColumn(1).GetShare(1) + result.GetColumn(1).GetShare(2);
  });
  Scenario("installed native unequal-neighbor diffusion reproduces excess independent shares", () => {
    using var native = new NativeWaterFixture(managed, specification);
    native.AddColumn(1, 1, 1); native.AddColumn(0, 1, 1); native.AddColumn(2, 1, 1); native.AddColumn(1, 2, 1);
    var before = new[] { Mix(0, .5, .5, 0), Mix(0, 1, 0, 0), Mix(0, 1, 0, 0), Mix(0, 1, 0, 0) };
    for (int i = 1; i < 4; i++) native.SetRawFlow(0, i, 1f / 65536);
    var transfers = native.ReadRawTransfers();
    var evaporation = native.UpdateNativeDepths(new double[4]);
    var advected = FluidTransportPrototype.Advect(before, transfers, evaporation);
    var independent = native.RunIndependentNativeContamination(before);
    double sum = independent[0][1] + independent[0][2];
    Check(sum > 1.01, "Native unequal-degree regression did not reproduce");
    var pairs = native.ReadNativeDiffusionLinks();
    Check(pairs.Length == 3, "Expected three native-eligible diffusion pairs");
    var diffused = FluidTransportPrototype.Diffuse(Output(advected), pairs, native.DiffusionFraction);
    Balance(Output(advected), diffused, "native eligible diffusion");
    for (int i = 0; i < 4; i++) Close(diffused.GetColumn(i).TotalVolume, native.PhysicalVolume(i), "Diffusion retained native depth", 2e-6);
    observations["unequalDegreeIndependentBadPlusRadioactive"] = sum;
    observations["unequalDegreeJointBadPlusRadioactive"] = diffused.GetColumn(0).GetShare(1) + diffused.GetColumn(0).GetShare(2);
  });
  Scenario("installed native pressure storage and multiple vertical columns", () => {
    using var native = new NativeWaterFixture(managed, specification);
    native.AddColumn(0, 1, 1, 0, 1, 0, .5f); native.AddColumn(0, 1, .5f, 3, 12, 1);
    native.AddColumn(1, 1, .5f, 0, 1); native.AddColumn(1, 1, .25f, 3, 12, 1);
    var before = new[] { Mix(.5, .5, .5, 0), Mix(0, 0, 0, .5), Mix(.5, 0, 0, 0), Mix(.25, 0, 0, 0) };
    native.SetRawFlow(0, 2, .25f); native.SetRawFlow(1, 3, .125f);
    var transfers = native.ReadRawTransfers();
    var evaporation = native.UpdateNativeDepths(new double[4]);
    var result = FluidTransportPrototype.Advect(before, transfers, evaporation);
    Balance(before, result, "pressure and upper reservoir");
    for (int i = 0; i < 4; i++) Close(result.GetColumn(i).TotalVolume, native.PhysicalVolume(i), "Stored-volume parity", 2e-6);
    Close(result.GetColumn(2).GetVolume(3), 0, "Upper fluid leaked into lower reservoir");
    Close(result.GetColumn(3).GetVolume(3), .125, "Upper-column target");
  });
  Scenario("installed native outflow generation drives joint transport", () => {
    using var native = new NativeWaterFixture(managed, specification);
    native.AddColumn(0, 1, 1.5f); native.AddColumn(1, 1, 1); native.AddColumn(2, 1, .5f);
    var before = new[] { Mix(.5, .5, .5, 0), Mix(.5, 0, 0, .5), Mix(0, .25, .25, 0) };
    native.GenerateNativeFlows();
    var transfers = native.ReadRawTransfers();
    Check(transfers.Length >= 2 && transfers.Sum(t => t.Volume) > 0, "Native generated no flow");
    var evaporation = native.UpdateNativeDepths(new double[3]);
    var result = FluidTransportPrototype.Advect(before, transfers, evaporation);
    Balance(before, result, "generated native flow");
    for (int i = 0; i < 3; i++) Close(result.GetColumn(i).TotalVolume, native.PhysicalVolume(i), "Generated native volume parity", 2e-6);
    observations["nativeGeneratedTransferCount"] = transfers.Length;
  });
  Scenario("native final outflow summary differs from actual depth-transfer inputs", () => {
    using var native = new NativeWaterFixture(managed, specification);
    native.AddColumn(0, 1, 1); native.AddColumn(1, 1, 1);
    var before = new[] { Mix(.5, .5, 0, 0), Mix(0, 0, .5, .5) };
    native.SetRawFlow(0, 1, .25f); native.SetRawFlow(1, 0, .125f);
    var raw = native.ReadRawTransfers();
    native.UpdateNativeDepths(new double[2]);
    var result = FluidTransportPrototype.Advect(before, raw, new double[2]);
    Balance(before, result, "opposing flows");
    Close(result.GetColumn(1).TotalVolume, native.PhysicalVolume(1), "Raw flux depth parity", 2e-6);
    double net = raw.Where(t => t.Source == 0).Sum(t => t.Volume) - raw.Where(t => t.Source == 1).Sum(t => t.Volume);
    double summary = native.SummaryNetVolume(0, 1);
    Check(Math.Abs(net - summary) > .01, "Expected summary/raw difference");
    observations["opposingRawNetVolume"] = net;
    observations["opposingSummaryNetVolume"] = summary;
  });
  Scenario("installed native sources, clean additions and selective pump changes", () => {
    using var native = new NativeWaterFixture(managed, specification);
    native.AddColumn(1, 1, 2);
    var current = Mix(.5, .5, .5, .5);
    native.SetContamination(0, current.GetShare(1));
    native.ApplyNativeSource(0, 2, .5f);
    current = FluidTransportPrototype.Add(current, Mix(.25, .25, 0, 0));
    Close(current.TotalVolume, native.PhysicalVolume(0), "Native source depth");
    Close(current.GetShare(1), native.Contamination(0), "Native source bad share", 2e-6);
    native.ApplyNativeChange(0, .5f, 0);
    current = FluidTransportPrototype.Add(current, Mix(0, 0, 0, .5));
    Close(current.TotalVolume, native.PhysicalVolume(0), "Native addition depth");
    Close(current.GetShare(1), native.Contamination(0), "Native addition bad share", 2e-6);
    native.ApplyNativeChange(0, -1.25f, 0);
    var removedClean = FluidTransportPrototype.RemoveNative(current, 1, 1.25, 0);
    RemovalBalance(current, removedClean, "Native clean pump"); current = removedClean.Remaining;
    Close(current.TotalVolume, native.PhysicalVolume(0), "Native clean removal depth", 2e-6);
    Close(current.GetShare(1), native.Contamination(0), "Native clean removal bad share", 2e-6);
    native.ApplyNativeChange(0, -.5f, 1);
    var removedBad = FluidTransportPrototype.RemoveNative(current, 1, 0, .5);
    RemovalBalance(current, removedBad, "Native bad pump"); current = removedBad.Remaining;
    Close(current.TotalVolume, native.PhysicalVolume(0), "Native bad removal depth", 2e-6);
    Close(current.GetShare(1), native.Contamination(0), "Native bad removal share", 2e-6);
    native.ApplyNativeSource(0, 0, 0);
    Close(current.TotalVolume, native.PhysicalVolume(0), "Zero-strength source emits nothing", 2e-6);
  });

  NativeAdapterScenarios.Run(Check, Scenario, managed, specification, observations);
  SourceRegressionScenarios.Run(Check, Scenario, managed, specification, observations);
  PersistenceScenarios.Run(Check, Scenario, managed, specification, observations);
  RegistryScenarios.Run(Check, Scenario, managed, reflectionConsumer, observations);

  Directory.CreateDirectory(Path.GetDirectoryName(reportPath)!);
  File.WriteAllText(reportPath, JsonSerializer.Serialize(new {
    status = "passed", assertions, scenarios, observations,
    runtime = System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription,
    nativeAssembly = new { path = Path.Combine(managed, "Timberborn.WaterSystem.dll"), sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(Path.Combine(managed, "Timberborn.WaterSystem.dll")))) },
    fixtureSpecification = new { path = specification, sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(specification))) },
    publicApi = new { assembly = typeof(ModdableFluids.ModdableFluidsEntry).Assembly.GetName().Name, version = ModdableFluids.ModdableFluidsEntry.ApiVersion, capabilities = ModdableFluids.ModdableFluidsEntry.Capabilities },
    limits = new[] { "Standalone .NET 8 harness; installed Mono and opt-in scheduler hooks are exercised by a separate probe report", "Registry, provider lifecycle and save round trips run outside the game; in-game save/reload remains pending", "No installed mod or save changed", "Native queued obstacle mutations are exercised in the native load phase; automatic scene-bound delivery is not installed", "Joint badwater transport intentionally differs from independent native contamination kernels, pressure-weighted mixing and upper-overflow merge loss", "The Mono scheduler fixture executes dependency jobs immediately; real worker barriers, registry, persistence and settlement acceptance remain pending" }
  }, new JsonSerializerOptions { WriteIndented = true }));
  Console.WriteLine($"{assertions} assertions passed across {scenarios.Count} scenarios. Report: {reportPath}");
  return 0;
} catch (Exception e) {
  Console.Error.WriteLine(e);
  return 1;
}
