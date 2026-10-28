using System;
using System.Reflection;
#if !UNITY_EDITOR
using HarmonyLib;
#endif
using Timberborn.Common;
using Timberborn.MapIndexSystem;
using Timberborn.Multithreading;
using Timberborn.WaterSystem;

namespace DeepFrontier.Scripts.Radiation {
  // Hooks that keep the radioactive share r in lockstep with the native water
  // (Timberborn 1.1.2.8):
  // - postfix of WaterSimulationTaskStarter.ScheduleSimulationSteps (once per
  //   substep, SubstepCount = 2): appends shadow copy -> native
  //   SimulateContaminationTask -> native UpdateContaminationTask -> harvest,
  //   on a shadow column array whose Contamination slot holds r, using the
  //   substep's own native columns and outflows, and returns the tail handle so
  //   the next native substep waits for it;
  // - prefix of UpdateWaterSourcesTask.Run: records the source cells before the
  //   sources add water (the chain restores them for the kernels and mixes the
  //   source water in afterwards, the native order);
  // - prefix and postfix of UpdateWaterChangesTask.Run: dumps, pumps and
  //   AddRadioactiveWater change r the way they change contamination;
  // - postfix of WaterChangeService.Tick: radioactive adds are promoted with the
  //   native water change queue they were enqueued with.
  // The native simulation's data is never written. Verify() resolves every
  // native member used and throws if 1.1.2.8's signatures changed.
#if !UNITY_EDITOR
  internal static class RadiationLockstep {
    internal const string HarmonyId = "DeepFrontier.RadiationLockstep";
    private const BindingFlags Fields = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
    private static bool _patched;

    internal static RadiationSimulation Simulation { get; private set; }

    internal static void Attach(RadiationSimulation simulation) {
      if (Simulation != null) throw new InvalidOperationException("A radiation simulation is already attached to the water lockstep");
      if (!_patched) {
        Verify();
        var harmony = new Harmony(HarmonyId);
        foreach (var patch in new[] { typeof(SubstepPatch), typeof(SourcesPatch), typeof(ChangesPatch), typeof(ChangeQueuePatch) })
          harmony.CreateClassProcessor(patch).Patch();
        _patched = true;
      }
      Simulation = simulation;
    }

    internal static void Detach(RadiationSimulation simulation) {
      if (Simulation == simulation) Simulation = null;
    }

    private static void Verify() {
      var starter = typeof(WaterSimulationTaskStarter);
      var parameters = typeof(WaterSimulationTaskStarter.SimulationParameters);
      var method = AccessTools.Method(starter, nameof(WaterSimulationTaskStarter.ScheduleSimulationSteps),
        new[] { typeof(ParallelizerHandle), parameters.MakeByRefType() });
      Require(method != null && method.ReturnType == typeof(ParallelizerHandle),
        "WaterSimulationTaskStarter.ScheduleSimulationSteps(ParallelizerHandle, in SimulationParameters) : ParallelizerHandle");
      foreach (var (name, type) in new[] {
          ("WaterColumns", typeof(WaterColumn[])), ("Outflows", typeof(ColumnOutflows[])),
          ("WaterColumnCounts", typeof(ReadOnlyArray<byte>)), ("LimitedDirections", typeof(ReadOnlyArray<int>)),
          ("HeightLimits", typeof(ReadOnlyArray<float>)), ("EvaporationModifiers", typeof(ReadOnlyArray<float>)) })
        Require(parameters.GetProperty(name)?.PropertyType == type, $"SimulationParameters.{name} : {type.Name}");
      RequireFields(starter, ("_deltaTime", typeof(float)), ("_overflowPressureFactor", typeof(float)), ("_diffusionOutflowLimit", typeof(double)),
        ("_diffusionDepthLimit", typeof(double)), ("_diffusionRate", typeof(float)), ("_flowLimitCalculator", typeof(FlowLimitCalculator)),
        ("_waterFlowRetriever", typeof(WaterFlowRetriever)));
      Require(WaterSimulationTaskStarter.SubstepCount == 2, "WaterSimulationTaskStarter.SubstepCount == 2");
      foreach (var task in new[] { typeof(UpdateWaterSourcesTask), typeof(UpdateWaterChangesTask) }) {
        Require(AccessTools.Method(task, "Run", Type.EmptyTypes)?.ReturnType == typeof(void), $"{task.Name}.Run() : void");
        RequireFields(task, ("_mapIndexService", typeof(MapIndexService)), ("_waterColumns", typeof(WaterColumn[])),
          ("_waterColumnCounts", typeof(ReadOnlyArray<byte>)), ("_verticalStride", typeof(int)));
      }
      RequireFields(typeof(UpdateWaterSourcesTask), ("_waterSources", typeof(ReadOnlyList<ThreadSafeWaterSource>)), ("_deltaTime", typeof(float)));
      RequireFields(typeof(UpdateWaterChangesTask), ("_waterChanges", typeof(ReadOnlyList<WaterChange>)));
      RequireFields(typeof(ThreadSafeWaterSource), ("_waterSource", typeof(IWaterSource)));
      Require(AccessTools.Method(typeof(WaterChangeService), nameof(WaterChangeService.Tick), Type.EmptyTypes) != null, "WaterChangeService.Tick()");
      Require(AccessTools.Method(typeof(WaterService), nameof(WaterService.AddCleanWater)) != null, "WaterService.AddCleanWater enqueues a clean water change");
    }

    private static void RequireFields(Type type, params (string Name, Type Type)[] fields) {
      foreach (var (name, fieldType) in fields)
        Require(type.GetField(name, Fields)?.FieldType == fieldType, $"{type.Name}.{name} : {fieldType.Name}");
    }

    private static void Require(bool condition, string member) {
      if (!condition) throw new InvalidOperationException($"Radiation lockstep: native water API changed; expected {member} (Timberborn 1.1.2.8)");
    }

    [HarmonyPatch(typeof(WaterSimulationTaskStarter), nameof(WaterSimulationTaskStarter.ScheduleSimulationSteps))]
    private static class SubstepPatch {
      private static void Postfix(WaterSimulationTaskStarter __instance, in WaterSimulationTaskStarter.SimulationParameters parameters,
          ref ParallelizerHandle __result) {
        var simulation = Simulation;
        if (simulation != null) __result = simulation.ScheduleLockstepSubstep(__instance, in parameters, __result);
      }
    }

    [HarmonyPatch(typeof(UpdateWaterSourcesTask), nameof(UpdateWaterSourcesTask.Run))]
    private static class SourcesPatch {
      private static void Prefix(ref UpdateWaterSourcesTask __instance) =>
        Simulation?.RecordSourceCells(__instance._mapIndexService, __instance._waterColumns, __instance._waterColumnCounts,
          __instance._waterSources, __instance._verticalStride, __instance._deltaTime);
    }

    [HarmonyPatch(typeof(UpdateWaterChangesTask), nameof(UpdateWaterChangesTask.Run))]
    private static class ChangesPatch {
      private static void Prefix(ref UpdateWaterChangesTask __instance) =>
        Simulation?.RecordChangedColumns(__instance._mapIndexService, __instance._waterColumns, __instance._waterColumnCounts,
          __instance._waterChanges, __instance._verticalStride);

      private static void Postfix(ref UpdateWaterChangesTask __instance) =>
        Simulation?.MixWaterChanges(__instance._mapIndexService, __instance._waterColumns, __instance._waterColumnCounts,
          __instance._waterChanges, __instance._verticalStride);
    }

    [HarmonyPatch(typeof(WaterChangeService), nameof(WaterChangeService.Tick))]
    private static class ChangeQueuePatch {
      private static void Postfix() => Simulation?.PromoteRadioactiveAdds();
    }
  }
#endif

  internal readonly struct RadiationShadowCopyTask : IParallelizerLoopTask {
    private readonly RadiationSimulation _simulation;
    private readonly WaterColumn[] _native;
    private readonly ReadOnlyArray<float> _evaporation;
    private readonly float _deltaTime;

    public RadiationShadowCopyTask(RadiationSimulation simulation, WaterColumn[] native, ReadOnlyArray<float> evaporation, float deltaTime) {
      _simulation = simulation; _native = native; _evaporation = evaporation; _deltaTime = deltaTime;
    }

    // index = y + 1 (row including the padding rows 0 and YSize + 1)
    public void Run(int row) => _simulation.CopyRow(row, _native, _evaporation, _deltaTime);
  }

  internal readonly struct RadiationHarvestTask : IParallelizerLoopTask {
    private readonly RadiationSimulation _simulation;
    private readonly WaterColumn[] _native;
    public RadiationHarvestTask(RadiationSimulation simulation, WaterColumn[] native) { _simulation = simulation; _native = native; }
    public void Run(int y) => _simulation.HarvestRow(y, _native);
  }

  internal readonly struct RadiationSourceStateTask : IParallelizerSingleTask {
    private readonly RadiationSimulation _simulation;
    private readonly WaterColumn[] _native;
    private readonly bool _restore;

    public RadiationSourceStateTask(RadiationSimulation simulation, WaterColumn[] native, bool restore) {
      _simulation = simulation; _native = native; _restore = restore;
    }

    public void Run() {
      if (_restore) _simulation.RestoreSourceCells();
      else _simulation.MixSourceCells(_native);
    }
  }
}
