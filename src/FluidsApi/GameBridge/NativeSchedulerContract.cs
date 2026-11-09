using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using FluidsApi.Native.Prototype;

namespace FluidsApi.GameBridge.Prototype {
  /// <summary>
  /// Every private native member the scheduler bridge touches, checked once before any patch is
  /// installed. A changed contract is reported in one message listing every difference, instead of
  /// failing later on a worker thread. Expected types are compared by their short display names
  /// (for example <c>ReadOnlyArray&lt;Byte&gt;</c>) and the constructor shapes are the exact argument
  /// types the substep job passes.
  /// </summary>
  public static class NativeSchedulerContract {
    private const BindingFlags Members = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
    /// <summary>Native tasks the bridge's substep replaces instead of running (loop tasks take the row).</summary>
    public static readonly string[] SkippedTasks = { "UpdateContaminationTask", "UpdateWaterSourcesTask", "UpdateWaterChangesTask" };
    private static readonly Type[][] SkippedRunParameters = { new[] { typeof(int) }, Type.EmptyTypes, Type.EmptyTypes };

    /// <summary>Problems with <paramref name="starter"/>; empty when the installed contract matches.</summary>
    public static IReadOnlyList<string> Check(Type starter) {
      var problems = new List<string>();
      Inspect(starter, problems);
      return problems;
    }

    /// <summary>Throws one exception with every problem, or returns the methods the bridge patches or skips.</summary>
    public static MethodInfo[] Require(Type starter) {
      var problems = new List<string>();
      var methods = Inspect(starter, problems);
      if (problems.Count > 0)
        throw new InvalidOperationException("Fluids API cannot attach to this game's water simulation (expected Timberborn 1.1.2.8). Changed native contract:\n- "
          + string.Join("\n- ", problems));
      return methods;
    }

    private static MethodInfo[] Inspect(Type starter, List<string> problems) {
      if (starter == null || starter.FullName != "Timberborn.WaterSystem.WaterSimulationTaskStarter") {
        problems.Add("Expected Timberborn.WaterSystem.WaterSimulationTaskStarter, got " + starter?.FullName);
        return null;
      }
      var parameters = starter.GetNestedType("SimulationParameters", BindingFlags.NonPublic | BindingFlags.Public);
      if (parameters == null) { problems.Add("WaterSimulationTaskStarter.SimulationParameters is missing"); return null; }
      var parallelizerHandle = typeof(Timberborn.Multithreading.ParallelizerHandle);
      var step = starter.GetMethod("ScheduleSimulationSteps", Members, null, new[] { parallelizerHandle, parameters.MakeByRefType() }, null);
      var changes = starter.GetMethod("ScheduleUpdateWaterChanges", Members, null, new[] { parallelizerHandle, parameters.MakeByRefType() }, null);
      if (step == null || step.ReturnType != parallelizerHandle) problems.Add("ScheduleSimulationSteps(ParallelizerHandle, in SimulationParameters) : ParallelizerHandle is missing");
      if (changes == null || changes.ReturnType != typeof(void)) problems.Add("ScheduleUpdateWaterChanges(ParallelizerHandle, in SimulationParameters) : void is missing");
      var substeps = starter.GetField("SubstepCount", BindingFlags.Static | BindingFlags.NonPublic);
      if (substeps == null || substeps.FieldType != typeof(int) || (int)substeps.GetValue(null) != 2) problems.Add("SubstepCount is not a static int equal to 2");

      var fields = new Dictionary<string, string> {
        ["_parallelizer"] = "IParallelizer", ["_stride"] = "Int32", ["_verticalStride"] = "Int32", ["_mapSize"] = "Vector3Int",
        ["_waterDepthSetter"] = "WaterDepthSetter", ["_flowLimitCalculator"] = "FlowLimitCalculator", ["_waterFlowRetriever"] = "WaterFlowRetriever",
        ["_neighborOffsets"] = "ImmutableArray<Int32>", ["_diffusionOutflowLimit"] = "Double", ["_diffusionDepthLimit"] = "Double"
      };
      foreach (string name in new[] { "_deltaTime", "_overflowPressureFactor", "_maxHardDamDecrease", "_hardDamSmoothingFactor", "_minHardDamSmoothing",
          "_maxHardDamSmoothing", "_hardDamOffset", "_softDamOffset", "_waterSpillThreshold", "_waterFlowFactor", "_outflowBalancingScaler",
          "_fastEvaporationDepthThreshold", "_fastEvaporationSpeed", "_normalEvaporationSpeed", "_maxWaterContamination", "_diffusionRate" })
        fields[name] = "Single";
      var starterFields = new Dictionary<string, Type>();
      foreach (var pair in fields) { var field = Field(starter, pair.Key, pair.Value, problems); if (field != null) starterFields[pair.Key] = field.FieldType; }
      var properties = new Dictionary<string, string> {
        ["DirectedFlows"] = "List<DirectedFlow>[]", ["BaseLevelFlows"] = "WaterFlow[]", ["WaterColumns"] = "WaterColumn[]", ["Outflows"] = "ColumnOutflows[]",
        ["ContaminationsBuffer"] = "Single[]", ["BaseLevelDiffusions"] = "Diffusions[]", ["TargetedDiffusionCount"] = "Byte[]",
        ["TargetedDiffusions"] = "List<TargetedDiffusion>[]", ["WaterColumnCounts"] = "ReadOnlyArray<Byte>", ["LimitedDirections"] = "ReadOnlyArray<Int32>",
        ["HeightLimits"] = "ReadOnlyArray<Single>", ["InflowLimits"] = "ReadOnlyArray<Single>", ["EvaporationModifiers"] = "ReadOnlyArray<Single>",
        ["WaterSources"] = "ReadOnlyList<ThreadSafeWaterSource>", ["WaterChanges"] = "ReadOnlyList<WaterChange>", ["RemovedWater"] = "Dictionary<Vector3Int, WaterAmountChange>"
      };
      var p = new Dictionary<string, Type>();
      foreach (var pair in properties) {
        var property = parameters.GetProperty(pair.Key, Members);
        if (property == null || Describe(property.PropertyType) != pair.Value || property.GetGetMethod(true) == null)
          problems.Add("SimulationParameters." + pair.Key + " is not a readable " + pair.Value + (property == null ? "" : " (found " + Describe(property.PropertyType) + ")"));
        else p[pair.Key] = property.PropertyType;
      }
      if (problems.Count > 0) return null;

      // Member shapes the jobs read.
      var readOnly = p["WaterColumnCounts"].GetGenericTypeDefinition();
      Field(p["WaterColumnCounts"], "_array", "Byte[]", problems);
      if (readOnly.MakeGenericType(typeof(byte)).GetConstructor(Members, null, new[] { typeof(byte[]) }, null) == null) problems.Add("ReadOnlyArray<T>(T[]) constructor is missing");
      Field(starterFields["_waterDepthSetter"], "_waterOverflowCalculator", "WaterOverflowCalculator", problems);
      var vector = starterFields["_mapSize"];
      foreach (string axis in new[] { "x", "y", "z" }) Property(vector, axis, "Int32", problems);
      var source = p["WaterSources"].GetGenericArguments()[0];
      Property(source, "CurrentStrength", "Single", problems); Property(source, "Contamination", "Single", problems);
      Property(source, "Coordinates", "ImmutableArray<Vector3Int>", problems); Field(source, "_waterSource", "IWaterSource", problems);
      var change = p["WaterChanges"].GetGenericArguments()[0];
      Property(change, "Coordinates", "Vector3Int", problems); Property(change, "DepthChange", "Single", problems); Property(change, "ContaminationChange", "Single", problems);
      foreach (var list in new[] { p["WaterSources"], p["WaterChanges"] })
        if (!typeof(IEnumerable).IsAssignableFrom(list)) problems.Add(Describe(list) + " is not enumerable");
      var amount = p["RemovedWater"].GetGenericArguments()[1];
      if (amount.GetConstructor(Members, null, new[] { typeof(float), typeof(float) }, null) == null) problems.Add("WaterAmountChange(float, float) constructor is missing");
      Property(amount, "CleanWaterChange", "Single", problems); Property(amount, "ContaminatedWaterChange", "Single", problems);
      var diffusions = p["BaseLevelDiffusions"].GetElementType();
      foreach (string side in new[] { "Bottom", "Left", "Top", "Right" }) Field(diffusions, side, "Boolean", problems);
      var targeted = p["TargetedDiffusions"].GetElementType().GetGenericArguments()[0];
      Field(targeted, "OriginIndex3D", "Int32", problems); Field(targeted, "TargetIndex3D", "Int32", problems);
      problems.AddRange(NativeWaterArrayAdapter.CheckContract(p["WaterColumns"].GetElementType(), p["BaseLevelFlows"].GetElementType(),
        p["DirectedFlows"].GetElementType().GetGenericArguments()[0], starterFields["_waterDepthSetter"], starter.Assembly.GetType("Timberborn.WaterSystem.WaterOverflowCalculator")));

      // The three native tasks the substep runs, with the exact argument types it passes.
      Type R(Type element) => readOnly.MakeGenericType(element);
      Type column = p["WaterColumns"].GetElementType(), outflow = p["Outflows"].GetElementType();
      Type i = typeof(int), f = typeof(float), d = typeof(double);
      Task(starter, "OutflowsUpdateTask", problems, starterFields["_flowLimitCalculator"], starterFields["_waterFlowRetriever"], p["DirectedFlows"], p["BaseLevelFlows"],
        p["WaterColumnCounts"], R(column), p["LimitedDirections"], p["HeightLimits"], p["InflowLimits"], R(outflow), i, i, i, f, f, f, f, f, f, f, f, f, f);
      Task(starter, "WaterParametersUpdateTask", problems, starterFields["_waterDepthSetter"], p["WaterColumns"], p["Outflows"], p["WaterColumnCounts"],
        starterFields["_neighborOffsets"], R(p["BaseLevelFlows"].GetElementType()), p["EvaporationModifiers"], R(p["DirectedFlows"].GetElementType()), i, i, i, f, f, f, f, f);
      Task(starter, "SimulateContaminationTask", problems, starterFields["_flowLimitCalculator"], starterFields["_waterFlowRetriever"], p["ContaminationsBuffer"],
        p["BaseLevelDiffusions"], p["TargetedDiffusionCount"], p["TargetedDiffusions"], p["WaterColumnCounts"], R(column), R(outflow), p["LimitedDirections"],
        p["HeightLimits"], i, i, i, f, f, f, d, d);
      var replaced = new List<MethodInfo> { step, changes };
      for (int t = 0; t < SkippedTasks.Length; t++) {
        var run = starter.Assembly.GetType("Timberborn.WaterSystem." + SkippedTasks[t])?.GetMethod("Run", Members, null, SkippedRunParameters[t], null);
        if (run == null) problems.Add(SkippedTasks[t] + ".Run(" + string.Join(", ", SkippedRunParameters[t].Select(Describe)) + ") is missing"); else replaced.Add(run);
      }
      return replaced.ToArray();
    }

    private static void Task(Type starter, string name, List<string> problems, params Type[] arguments) {
      var type = starter.Assembly.GetType("Timberborn.WaterSystem." + name);
      if (type == null) { problems.Add(name + " is missing"); return; }
      if (type.GetConstructor(Members, null, arguments, null) == null)
        problems.Add(name + "(" + string.Join(", ", arguments.Select(Describe)) + ") constructor is missing");
      if (type.GetMethod("Run", Members, null, new[] { typeof(int) }, null) == null) problems.Add(name + ".Run(int) is missing");
    }

    private static FieldInfo Field(Type owner, string name, string expected, List<string> problems) {
      var field = owner.GetField(name, Members);
      if (field != null && Describe(field.FieldType) == expected) return field;
      problems.Add(owner.Name + "." + name + " is not a " + expected + " field" + (field == null ? "" : " (found " + Describe(field.FieldType) + ")"));
      return null;
    }

    private static void Property(Type owner, string name, string expected, List<string> problems) {
      var property = owner.GetProperty(name, Members);
      if (property == null || Describe(property.PropertyType) != expected || property.GetGetMethod(true) == null)
        problems.Add(owner.Name + "." + name + " is not a readable " + expected + (property == null ? "" : " (found " + Describe(property.PropertyType) + ")"));
    }

    /// <summary>Short display name: <c>List&lt;DirectedFlow&gt;[]</c>, <c>ImmutableArray&lt;Int32&gt;</c>.</summary>
    public static string Describe(Type type) {
      if (type.IsArray) return Describe(type.GetElementType()) + "[]";
      if (!type.IsGenericType) return type.Name;
      string name = type.Name.Substring(0, type.Name.IndexOf('`'));
      return name + "<" + string.Join(", ", type.GetGenericArguments().Select(Describe)) + ">";
    }
  }
}
