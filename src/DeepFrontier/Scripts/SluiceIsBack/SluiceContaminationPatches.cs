#if !UNITY_EDITOR
using System;
using System.Linq;
using System.Reflection;
using DeepFrontier.Scripts;
using HarmonyLib;
using SluiceIsBack.Components;
using Timberborn.ModManagerScene;
using Timberborn.WaterSystem;
using UnityEngine;

namespace DeepFrontier.SluiceIsBackContamination {
  // Why patches (Sluice is Back! 11.0.0, SluiceIsBack.dll decompiled):
  // Sluice.Tick -> UpdateAutoMode -> IsAutoClosedByContamination() compares
  //   GetContamination() > SluiceState.OnAboveLimit   (AutoCloseOnAbove)
  //   GetContamination() < SluiceState.OnBelowLimit   (AutoCloseOnBelow)
  // and the private GetContamination() returns
  //   (float)Math.Round(_threadSafeWaterMap.ColumnContamination(_sourceCoordinates), 2).
  // The mod offers no extension point for the measured value, so one postfix
  // on GetContamination substitutes the selected substance's value
  // (SluiceMeasurementPatch); the toggles, limits, panel, save keys and
  // obstacle logic stay the mod's. A second postfix on the public
  // SluiceState.SetState(neighbor, minLimit), through which the mod copies
  // every setting between synchronized sluices, copies the choice
  // (SluiceStateSynchronizationPatch).
  //
  // Moddable Timberborn's OptionalModsLoader starts every IModStarter of this
  // optional assembly. Verify() resolves every Sluice is Back! member the
  // patches and the panel rely on and throws if a mod update changed one.
  internal sealed class SluiceContaminationModStarter : IModStarter {
    internal const string HarmonyId = "DeepFrontier.SluiceIsBack";

    public void StartMod(IModEnvironment modEnvironment) {
      SluiceIsBackNative.Verify();
      var harmony = new Harmony(HarmonyId);
      harmony.CreateClassProcessor(typeof(SluiceMeasurementPatch)).Patch();
      harmony.CreateClassProcessor(typeof(SluiceStateSynchronizationPatch)).Patch();
      Debug.Log($"[DeepFrontier] Sluice is Back! {typeof(Sluice).Assembly.GetName().Version} contamination measurement patch applied (badwater, radiation, any contamination).");
    }
  }

  internal static class SluiceIsBackNative {
    private const BindingFlags Instance = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly;
    private static AccessTools.FieldRef<Sluice, Vector3Int> _sourceCoordinates;

    public static MethodInfo Measurement() => Method(typeof(Sluice), "GetContamination", typeof(float));
    public static MethodInfo SetState() => Method(typeof(SluiceState), nameof(SluiceState.SetState), typeof(void), typeof(SluiceState), typeof(int));

    // The column the sluice measures (Sluice.InitializeEntity: one cell upstream).
    public static Vector3Int SourceCoordinates(Sluice sluice) => _sourceCoordinates(sluice);

    public static void Verify() {
      var measurement = Measurement();
      if (measurement.IsPublic) throw Changed("Sluice.GetContamination() private");
      if (NativeIl.Inlinable(measurement)) throw Changed($"Sluice.GetContamination larger than the Mono inline limit (IL {NativeIl.Size(measurement)} bytes)");
      RequireCalls(measurement, typeof(IThreadSafeWaterMap).GetMethod(nameof(IThreadSafeWaterMap.ColumnContamination), new[] { typeof(Vector3Int) }),
        typeof(Math).GetMethod(nameof(Math.Round), new[] { typeof(double), typeof(int) }));
      var autoClosed = Method(typeof(Sluice), "IsAutoClosedByContamination", typeof(bool));
      RequireCalls(autoClosed, measurement,
        Getter(typeof(SluiceState), nameof(SluiceState.AutoCloseOnAbove), typeof(bool)), Getter(typeof(SluiceState), nameof(SluiceState.OnAboveLimit), typeof(float)),
        Getter(typeof(SluiceState), nameof(SluiceState.AutoCloseOnBelow), typeof(bool)), Getter(typeof(SluiceState), nameof(SluiceState.OnBelowLimit), typeof(float)));
      RequireCalls(Method(typeof(Sluice), "UpdateAutoMode", typeof(void)), autoClosed);
      RequireField(typeof(Sluice), "_sourceCoordinates", typeof(Vector3Int));
      RequireField(typeof(Sluice), "_threadSafeWaterMap", typeof(IThreadSafeWaterMap));
      _sourceCoordinates = AccessTools.FieldRefAccess<Sluice, Vector3Int>("_sourceCoordinates");
      Getter(typeof(Sluice), nameof(Sluice.MinHeight), typeof(int));
      Getter(typeof(Sluice), nameof(Sluice.MaxHeight), typeof(int));

      var setState = SetState();
      if (!setState.IsPublic) throw Changed("SluiceState.SetState(SluiceState, int) public");
      if (!setState.GetParameters().Select(p => p.Name).SequenceEqual(new[] { "neighbor", "minLimit" })) throw Changed("SluiceState.SetState(neighbor, minLimit)");
      if (NativeIl.Inlinable(setState)) throw Changed($"SluiceState.SetState larger than the Mono inline limit (IL {NativeIl.Size(setState)} bytes)");
      var andSynchronize = Method(typeof(SluiceState), nameof(SluiceState.SetStateAndSynchronize), typeof(void), typeof(SluiceState), typeof(int));
      if (!andSynchronize.IsPublic) throw Changed("SluiceState.SetStateAndSynchronize(SluiceState, int) public");
      RequireCalls(andSynchronize, setState);
      RequireCalls(Method(typeof(Sluice), nameof(Sluice.DuplicateFrom), typeof(void), typeof(Sluice)), andSynchronize);
      Getter(typeof(SluiceState), nameof(SluiceState.IsSynchronized), typeof(bool));
    }

    private static void RequireCalls(MethodBase caller, params MethodBase[] callees) {
      foreach (var callee in callees)
        if (!NativeIl.Calls(caller, callee)) throw Changed($"{caller.DeclaringType?.Name}.{caller.Name} calls {callee?.DeclaringType?.Name}.{callee?.Name}");
    }

    private static MethodInfo Method(Type type, string name, Type returnType, params Type[] parameters) {
      var method = type.GetMethod(name, Instance, null, parameters, null);
      if (method == null || method.ReturnType != returnType)
        throw Changed($"{type.Name}.{name}({string.Join(", ", parameters.Select(p => p.Name))}) : {returnType.Name}");
      return method;
    }

    private static MethodInfo Getter(Type type, string name, Type propertyType) {
      var property = type.GetProperty(name, Instance);
      var getter = property?.GetGetMethod();
      if (property?.PropertyType != propertyType || getter == null) throw Changed($"{type.Name}.{name} : {propertyType.Name} with a public getter");
      return getter;
    }

    private static void RequireField(Type type, string name, Type fieldType) {
      if (type.GetField(name, Instance)?.FieldType != fieldType) throw Changed($"{type.Name}.{name} : {fieldType.Name}");
    }

    private static InvalidOperationException Changed(string member) =>
      new InvalidOperationException($"Sluice is Back! contamination measurement: the mod's API changed; expected {member} (Sluice is Back! 11.0.0)");
  }

  // Substitutes the selected substance's measurement (Badwater returns the
  // mod's value unchanged).
  [HarmonyPatch]
  internal static class SluiceMeasurementPatch {
    private static MethodBase TargetMethod() => SluiceIsBackNative.Measurement();

    private static void Postfix(Sluice __instance, Vector3Int ____sourceCoordinates, ref float __result) {
      var substance = __instance.GetComponent<SluiceContaminationSubstance>();
      if (!substance) throw new InvalidOperationException($"Sluice {__instance.Name} has no SluiceContaminationSubstance decorator");
      __result = substance.Measure(____sourceCoordinates, __result);
    }
  }

  // Copies the choice wherever the mod copies a sluice's settings.
  [HarmonyPatch]
  internal static class SluiceStateSynchronizationPatch {
    private static MethodBase TargetMethod() => SluiceIsBackNative.SetState();

    private static void Postfix(SluiceState __instance, SluiceState neighbor) {
      if (ReferenceEquals(__instance, neighbor)) return;
      var target = __instance.GetComponent<SluiceContaminationSubstance>();
      var source = neighbor.GetComponent<SluiceContaminationSubstance>();
      if (!target || !source) throw new InvalidOperationException($"Sluice {__instance.Name} or {neighbor.Name} has no SluiceContaminationSubstance decorator");
      target.CopyFrom(source);
    }
  }
}
#endif
