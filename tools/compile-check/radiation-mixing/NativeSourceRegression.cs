using System.Collections;
using System.Collections.Immutable;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.Loader;

// Exercise the real RecordSourceCells -> native UpdateWaterSourcesTask.Run ->
// MixSourceCells path. No Unity scene, replacement physics or source-task stubs.
internal static class NativeSourceRegression {
  const BindingFlags Members = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
  public static void Run(Assembly mod, string managed, Action<bool, string> check) {
    Assembly? Resolve(AssemblyLoadContext context, AssemblyName name) {
      var path = Path.Combine(managed, name.Name + ".dll");
      return File.Exists(path) ? context.LoadFromAssemblyPath(path) : null;
    }
    AssemblyLoadContext.Default.Resolving += Resolve;
    try {
      var water = Assembly.LoadFrom(Path.Combine(managed, "Timberborn.WaterSystem.dll"));
      var common = Assembly.LoadFrom(Path.Combine(managed, "Timberborn.Common.dll"));
      Type W(string name) => water.GetType("Timberborn.WaterSystem." + name, true)!;
      object New(string name, params object?[] values) => Activator.CreateInstance(W(name), Members, null, values, null)!;
      object ReadOnly(Array values) => Activator.CreateInstance(common.GetType("Timberborn.Common.ReadOnlyArray`1", true)!
        .MakeGenericType(values.GetType().GetElementType()!), new object[] { values })!;
      var simulationType = mod.GetType("DeepFrontier.Scripts.Radiation.RadiationSimulation", true)!;
      var mapType = Assembly.LoadFrom(Path.Combine(managed, "Timberborn.MapIndexSystem.dll"))
        .GetType("Timberborn.MapIndexSystem.MapIndexService", true)!;
      var map = Activator.CreateInstance(mapType, new object?[] { null })!;
      mapType.GetProperty("Stride")!.SetValue(map, 3);
      mapType.GetProperty("VerticalStride")!.SetValue(map, 9);
      var vectorType = Assembly.LoadFrom(Path.Combine(managed, "UnityEngine.CoreModule.dll")).GetType("UnityEngine.Vector3Int", true)!;
      var createImmutable = typeof(ImmutableArray).GetMethods().Single(m => m.Name == "Create" && m.IsGenericMethodDefinition &&
        m.GetParameters().Length == 1 && m.GetParameters()[0].ParameterType.IsArray);

      void Case(string name, float depth, float bad, float radioactive, float overflow, int ceiling,
          float expected, params (float Amount, float Bad)[] operations) {
        const float pressure = .1f;
        var columns = Array.CreateInstance(W("WaterColumn"), 9);
        var column = New("WaterColumn", 0, ceiling);
        Set(column, "WaterDepth", depth); Set(column, "Overflow", overflow); Set(column, "Contamination", bad);
        columns.SetValue(column, 4);
        var counts = ReadOnly(new byte[] { 0, 0, 0, 0, 1, 0, 0, 0, 0 });
        var sources = (IList)Activator.CreateInstance(typeof(List<>).MakeGenericType(W("ThreadSafeWaterSource")))!;
        foreach (var operation in operations) {
          var coordinates = Array.CreateInstance(vectorType, 1);
          coordinates.SetValue(Activator.CreateInstance(vectorType, 0, 0, 0), 0);
          var source = DispatchProxy.Create(W("IWaterSource"), typeof(RadiationFixtureSource));
          var values = ((RadiationFixtureSource)source).Values;
          values.Add("get_Coordinates", createImmutable.MakeGenericMethod(vectorType).Invoke(null, new object[] { coordinates })!);
          values.Add("get_CurrentStrength", operation.Amount);
          values.Add("get_Contamination", operation.Bad);
          sources.Add(New("ThreadSafeWaterSource", source));
        }
        var readOnlySources = Activator.CreateInstance(common.GetType("Timberborn.Common.ReadOnlyList`1", true)!
          .MakeGenericType(W("ThreadSafeWaterSource")), Members, null, new object[] { sources }, null)!;
        var overflowCalculator = New("WaterOverflowCalculator", map, null);
        Set(overflowCalculator, "_maxPressure", 16f);
        Set(overflowCalculator, "_overflowPressureFactorInverted", 1f / pressure);
        var task = New("UpdateWaterSourcesTask", map, New("WaterDepthSetter", overflowCalculator), New("MutableWaterColumnRetriever"),
          columns, counts, readOnlySources, 9, 1f, pressure, 1f);
        var simulation = RuntimeHelpers.GetUninitializedObject(simulationType);
        Set(simulation, "_layers", 1);
        Set(simulation, "_publishedTideShare", 1f);
        Set(simulation, "_publishedSprings", Activator.CreateInstance(typeof(Dictionary<,>).MakeGenericType(W("IWaterSource"), typeof(float)))!);
        foreach (var field in new[] { "_sourceCells", "_sourceSteps" }) {
          var member = simulationType.GetField(field, Members)!;
          member.SetValue(simulation, Activator.CreateInstance(member.FieldType));
        }
        var spec = RuntimeHelpers.GetUninitializedObject(W("WaterSimulatorSpec"));
        W("WaterSimulatorSpec").GetProperty("OverflowPressureFactor")!.SetValue(spec, pressure);
        Set(simulation, "_spec", spec);
        var radiation = new float[9]; radiation[4] = radioactive;
        Set(simulation, "_radiation", radiation);
        Set(simulation, "_water", Array.CreateInstance(W("WaterColumn"), 9));
        Set(simulation, "_isSourceCell", new bool[9]);
        simulationType.GetMethod("RecordSourceCells", Members)!.Invoke(simulation,
          new object[] { map, columns, counts, readOnlySources, 9, 1f, task });
        task.GetType().GetMethod("Run", Members)!.Invoke(task, null);
        simulationType.GetMethod("RestoreSourceCells", Members)!.Invoke(simulation, null);
        simulationType.GetMethod("MixSourceCells", Members)!.Invoke(simulation, new object[] { columns });
        float afterBad = Get<float>(columns.GetValue(4)!, "Contamination");
        check(radiation[4] >= 0 && radiation[4] + afterBad <= 1.000001f, name + ": invalid final shares");
        check(Math.Abs(radiation[4] - expected) < .000002f, $"{name}: expected {expected:R}, got {radiation[4]:R}");
      }

      // The old formula retains all old radiation when a nonradioactive source
      // drains the column. This reaches the reported 1.068215 from valid inputs.
      float drained = 1f - 1f / 1.068215f;
      float legacy = 1f / (1f - drained);
      check(legacy > 1.06f, "negative control must reproduce >100% without invalid input");
      Case("negative badwater source in radioactive water", 1, 0, 1, 0, 12, 1, (-drained, 1));
      Case("negative fresh source removes mixed clean water", 2, .5f, .25f, 0, 12, 1f/6f, (-.5f, 0));
      Case("negative badwater source concentrates clean mix", 2, .5f, .25f, 0, 12, 1f/3f, (-.5f, 1));
      Case("complete drainage", 1, 0, 1, 0, 12, 0, (-2, 0));
      Case("fresh source during radioactive tide", 1, 0, 0, 0, 12, .5f, (1, 0));
      Case("overlapping addition and withdrawal", 1, 0, 0, 0, 12, .5f, (1, 0), (-1, 1));
      Case("reversed operations", 1, 0, 0, 0, 12, 1, (-1, 1), (1, 0));
      Case("zero source", 1, .2f, .4f, 0, 12, .4f, (0, 0));
      // Ceiling 4, overflow 120: native pressure cap is reached. A second
      // source retains no water and must not dilute the first source's share.
      Case("pressure-limited overlapping sources", 4, 0, 0, 110, 4, 1f/16f, (10, 0), (20, 1));
      Case("pressure-limited reversed sources", 4, 0, 0, 110, 4, 0, (10, 1), (20, 0));
      var random = new Random(8173);
      for (int i = 0; i < 250; i++) {
        float depth = .1f + (float)random.NextDouble() * 5;
        float share = (float)random.NextDouble();
        float removed = depth * (float)random.NextDouble();
        Case("withdrawal " + i, depth, 0, share, 0, 12, share, (-removed, 0));
      }
    } finally { AssemblyLoadContext.Default.Resolving -= Resolve; }
  }
  static void Set(object target, string name, object value) => target.GetType().GetField(name, Members)!.SetValue(target, value);
  static T Get<T>(object target, string name) => (T)target.GetType().GetField(name, Members)!.GetValue(target)!;
}

public class RadiationFixtureSource : DispatchProxy {
  public Dictionary<string, object> Values { get; } = new();
  protected override object? Invoke(MethodInfo? method, object?[]? arguments) => Values[method!.Name];
}
