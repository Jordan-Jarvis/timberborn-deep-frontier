#if !UNITY_EDITOR
using System;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using Timberborn.AutomationBuildings;
using Timberborn.Common;
using Timberborn.ModManagerScene;
using Timberborn.WaterSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.Sensors {
  // Why a patch (Timberborn 1.1.2.8, decompiled Timberborn.AutomationBuildings):
  // ContaminationSensor.Sample() is
  //   SampledContamination = HasWaterBelow(out floor) ? GetContamination(floor) : null;
  //   UpdateOutputState();
  // and GetContamination(floor) returns
  //   Numbers.RoundToPrecision(_threadSafeWaterMap.ColumnContamination((x, y, floor)), Precision).
  // The measured value has no extension point (no spec, provider or binding),
  // so one postfix on the private GetContamination substitutes the selected
  // substance's value. Everything else stays native: the water-below test,
  // SampledContamination, UpdateOutputState (Mode.Evaluate against the rounded
  // Threshold, Automator.SetState), the save keys and the panel fragment.
  //
  // Every IModStarter in the mod assembly runs at mod start. Verify() resolves
  // every native member the patch relies on and throws if a game update
  // changed one.
  internal sealed class ContaminationSensorModStarter : IModStarter {
    internal const string HarmonyId = "DeepFrontier.ContaminationSensor";

    public void StartMod(IModEnvironment modEnvironment) {
      ContaminationSensorNative.Verify();
      new Harmony(HarmonyId).CreateClassProcessor(typeof(ContaminationSensorMeasurementPatch)).Patch();
      Debug.Log("[DeepFrontier] Contamination sensor measurement patch applied (badwater, radiation, any contamination).");
    }
  }

  internal static class ContaminationSensorNative {
    private const BindingFlags Instance = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
    // Mono inlines methods with at most this many IL bytes into their callers
    // (INLINE_LENGTH_LIMIT), which would bypass a patch.
    private const int MonoInlineLimit = 20;

    public static MethodInfo Measurement() => Method("GetContamination", typeof(float), BindingFlags.Instance | BindingFlags.NonPublic,
      typeof(int));

    public static void Verify() {
      var type = typeof(ContaminationSensor);
      var measurement = Measurement();
      if (measurement.GetParameters()[0].Name != "floor") throw Changed("ContaminationSensor.GetContamination(floor)");
      int size = measurement.GetMethodBody()?.GetILAsByteArray()?.Length ?? 0;
      if (size <= MonoInlineLimit) throw Changed($"ContaminationSensor.GetContamination larger than the Mono inline limit (IL {size} bytes)");
      RequireCalls(measurement, typeof(IThreadSafeWaterMap).GetMethod(nameof(IThreadSafeWaterMap.ColumnContamination), new[] { typeof(Vector3Int) }),
        typeof(Numbers).GetMethod(nameof(Numbers.RoundToPrecision), new[] { typeof(float), typeof(float) }));

      var sample = Method(nameof(ContaminationSensor.Sample), typeof(void), BindingFlags.Instance | BindingFlags.Public);
      var hasWaterBelow = Method("HasWaterBelow", typeof(bool), BindingFlags.Instance | BindingFlags.NonPublic,
        typeof(int).MakeByRefType());
      var setSampled = type.GetProperty(nameof(ContaminationSensor.SampledContamination), Instance);
      if (setSampled?.PropertyType != typeof(float?) || setSampled.GetSetMethod(true) == null)
        throw Changed("ContaminationSensor.SampledContamination : float? with a setter");
      var update = Method("UpdateOutputState", typeof(void), BindingFlags.Instance | BindingFlags.NonPublic);
      RequireCalls(sample, hasWaterBelow, measurement, setSampled.GetSetMethod(true), update);

      RequireField(type, "_sensorCoordinates", typeof(Vector3Int));
      RequireField(type, "_threadSafeWaterMap", typeof(IThreadSafeWaterMap));
      var precision = type.GetField(nameof(ContaminationSensor.Precision), BindingFlags.Static | BindingFlags.Public);
      if (precision?.FieldType != typeof(float) || !Mathf.Approximately((float)precision.GetValue(null), 0.01f))
        throw Changed("ContaminationSensor.Precision = 0.01");
      if (typeof(ContaminationSensorSpec).GetProperty(nameof(ContaminationSensorSpec.SensorCoordinates), Instance)?.PropertyType != typeof(Vector3Int))
        throw Changed("ContaminationSensorSpec.SensorCoordinates : Vector3Int");
    }

    // Methods named by call/callvirt operands in the caller's IL. Only the
    // method token tables (MethodDef 0x06, MemberRef 0x0A) are resolved.
    private static void RequireCalls(MethodBase caller, params MethodBase[] callees) {
      var il = caller.GetMethodBody()?.GetILAsByteArray() ?? throw Changed($"{caller.Name} with an IL body");
      var called = new System.Collections.Generic.List<MethodBase>();
      for (int i = 0; i + 4 < il.Length; i++) {
        if (il[i] != 0x28 && il[i] != 0x6F) continue;
        int token = BitConverter.ToInt32(il, i + 1);
        if (token >> 24 != 0x06 && token >> 24 != 0x0A) continue;
        MethodBase method;
        try { method = caller.Module.ResolveMethod(token); } catch (ArgumentException) { continue; }
        called.Add(method);
      }
      foreach (var callee in callees) {
        if (callee == null || !called.Any(method => method.Module == callee.Module && method.MetadataToken == callee.MetadataToken))
          throw Changed($"{caller.DeclaringType?.Name}.{caller.Name} calls {callee?.DeclaringType?.Name}.{callee?.Name}");
      }
    }

    private static MethodInfo Method(string name, Type returnType, BindingFlags flags, params Type[] parameters) {
      var method = typeof(ContaminationSensor).GetMethod(name, flags | BindingFlags.DeclaredOnly, null, parameters, null);
      if (method == null || method.ReturnType != returnType)
        throw Changed($"ContaminationSensor.{name}({string.Join(", ", parameters.Select(p => p.Name))}) : {returnType.Name}");
      return method;
    }

    private static void RequireField(Type type, string name, Type fieldType) {
      if (type.GetField(name, Instance)?.FieldType != fieldType) throw Changed($"{type.Name}.{name} : {fieldType.Name}");
    }

    private static InvalidOperationException Changed(string member) =>
      new InvalidOperationException($"Contamination sensor: native sensor API changed; expected {member} (Timberborn 1.1.2.8)");
  }

  // Substitutes the selected substance's measurement (Badwater returns the
  // native value unchanged). Runs only when the native sensor found water
  // below its arm; a dry sensor stays SampledContamination = null natively.
  [HarmonyPatch]
  internal static class ContaminationSensorMeasurementPatch {
    private static MethodBase TargetMethod() => ContaminationSensorNative.Measurement();

    private static void Postfix(ContaminationSensor __instance, int floor, Vector3Int ____sensorCoordinates, ref float __result) {
      var substance = __instance.GetComponent<ContaminationSensorSubstance>();
      if (!substance) throw new InvalidOperationException($"Contamination sensor {__instance.Name} has no ContaminationSensorSubstance decorator");
      __result = substance.Measure(new Vector3Int(____sensorCoordinates.x, ____sensorCoordinates.y, floor), __result);
    }
  }
}
#endif
