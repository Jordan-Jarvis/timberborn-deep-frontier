using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Reflection;
using System.IO;
using Timberborn.Multithreading;
using Timberborn.WaterSystem;
using UnityEngine;
using FluidsApi.GameBridge.Prototype;
using HarmonyLib;
using FluidsApi.Transport.Prototype;

namespace FluidsApi.Native.Acceptance {
  internal static class SchedulerProbe {
    private const BindingFlags Members = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;
    internal static int Run(string managed) {
      int checks = 0;
      void Check(bool condition, string name) { checks++; if (!condition) throw new InvalidOperationException(name); }
      var water = Assembly.LoadFrom(Path.Combine(managed, "Timberborn.WaterSystem.dll"));
      var common = Assembly.LoadFrom(Path.Combine(managed, "Timberborn.Common.dll"));
      Type Type(string name) => water.GetType("Timberborn.WaterSystem." + name, true);
      object New(string name, params object[] arguments) => Activator.CreateInstance(Type(name), Members, null, arguments, null);
      void Set(object target, string name, object value) => target.GetType().GetField(name, Members).SetValue(target, value);
      object ReadOnly(Array array) => Activator.CreateInstance(common.GetType("Timberborn.Common.ReadOnlyArray`1", true).MakeGenericType(array.GetType().GetElementType()), new object[] { array });
      object ReadOnlyList(IList list) => Activator.CreateInstance(common.GetType("Timberborn.Common.ReadOnlyList`1", true).MakeGenericType(list.GetType().GetGenericArguments()[0]), Members, null, new object[] { list }, null);
      Array Lists(string name, int length) {
        var listType = typeof(List<>).MakeGenericType(Type(name)); var array = Array.CreateInstance(listType, length);
        for (int i = 0; i < length; i++) array.SetValue(Activator.CreateInstance(listType), i); return array;
      }
      var mapType = Assembly.LoadFrom(Path.Combine(managed, "Timberborn.MapIndexSystem.dll")).GetType("Timberborn.MapIndexSystem.MapIndexService", true);
      object map = Activator.CreateInstance(mapType, new object[] { null });
      mapType.GetProperty("Stride").SetValue(map, 5); mapType.GetProperty("VerticalStride").SetValue(map, 25);
      var overflow = New("WaterOverflowCalculator", map, null);
      Set(overflow, "_maxPressure", 16f); Set(overflow, "_overflowPressureFactorInverted", .125f);
      var setter = New("WaterDepthSetter", overflow);
      var parallelizer = new ImmediateParallelizer();
      var starter = New("WaterSimulationTaskStarter", parallelizer, map, null, New("FlowLimitCalculator", map), New("WaterFlowRetriever"), setter, New("MutableWaterColumnRetriever"), null);
      Set(starter, "_mapSize", new Vector3Int(3, 3, 16)); Set(starter, "_stride", 5); Set(starter, "_verticalStride", 25);
      Set(starter, "_neighborOffsets", ImmutableArray.Create(-5, -1, 5, 1));
      foreach (var setting in new Dictionary<string, float> {
        ["_deltaTime"] = .25f, ["_overflowPressureFactor"] = 8, ["_maxHardDamDecrease"] = .02f, ["_hardDamSmoothingFactor"] = 2.25f,
        ["_minHardDamSmoothing"] = .5f, ["_maxHardDamSmoothing"] = 2, ["_hardDamOffset"] = .1f, ["_softDamOffset"] = .1f,
        ["_waterSpillThreshold"] = .1f, ["_waterFlowFactor"] = 2.25f * .25f, ["_outflowBalancingScaler"] = .8f,
        ["_fastEvaporationDepthThreshold"] = .02f, ["_fastEvaporationSpeed"] = .001f, ["_normalEvaporationSpeed"] = .0001f,
        ["_maxWaterContamination"] = 1, ["_diffusionRate"] = .45f
      }) Set(starter, setting.Key, setting.Value);
      Set(starter, "_diffusionOutflowLimit", .125d); Set(starter, "_diffusionDepthLimit", .1d);
      var columns = Array.CreateInstance(Type("WaterColumn"), 75);
      object first = New("WaterColumn", 0, 12), second = New("WaterColumn", 0, 12);
      Set(first, "WaterDepth", 2f); Set(second, "WaterDepth", 1f); columns.SetValue(first, 11); columns.SetValue(second, 12);
      var counts = new byte[25]; counts[11] = 1; counts[12] = 1;
      var sources = (IList)Activator.CreateInstance(typeof(List<>).MakeGenericType(Type("ThreadSafeWaterSource")));
      var sourceProvider = new Source();
      sources.Add(New("ThreadSafeWaterSource", sourceProvider));
      var changes = (IList)Activator.CreateInstance(typeof(List<>).MakeGenericType(Type("WaterChange")));
      var target = new Vector3Int(1, 1, 0);
      changes.Add(New("WaterChange", target, -.25f, 0f));
      changes.Add(New("WaterChange", new Vector3Int(2, 2, 0), -.5f, 0f));
      changes.Add(New("WaterChange", new Vector3Int(2, 2, 0), .5f, 0f));
      var removed = (IDictionary)Activator.CreateInstance(typeof(Dictionary<,>).MakeGenericType(typeof(Vector3Int), typeof(WaterAmountChange)));
      var limits = new float[400]; for (int i = 0; i < limits.Length; i++) limits[i] = -1;
      var inflows = new float[400]; for (int i = 0; i < inflows.Length; i++) inflows[i] = float.MaxValue;
      var hook = new NativeTransportHooks(starter, 4, 1);
      hook.SessionCreated = session => {
        session.SeedComposition(11, new FluidVolumes(new[] { 1d, .5, .5, 0 }));
        session.SeedComposition(12, new FluidVolumes(new[] { .5, 0, 0, .5 }));
      };
      hook.ResolveSource = (source, index, volume) => new FluidVolumes(new[] { 0d, 0, volume, 0 });
      try {
        hook.Attach(); Check(hook.HasInstalledPatches, "Native scheduler hooks were not installed");
        using (var duplicate = new NativeTransportHooks(starter, 4, 1)) {
          bool rejected = false;
          try { duplicate.Attach(); } catch (InvalidOperationException) { rejected = true; }
          Check(rejected, "Duplicate scheduler owner was accepted");
        }
        Check(hook.HasInstalledPatches, "Disposing a rejected owner removed active hooks");
        var simulate = starter.GetType().GetMethod("Simulate", Members);
        var arguments = new[] {
          Lists("DirectedFlow", 25), Array.CreateInstance(Type("WaterFlow"), 25), columns, Array.CreateInstance(Type("ColumnOutflows"), 75),
          new float[75], Array.CreateInstance(Type("Diffusions"), 25), new byte[75], Lists("TargetedDiffusion", 25), removed,
          ReadOnly(counts), ReadOnly(new int[400]), ReadOnly(limits), ReadOnly(inflows), ReadOnly(new float[75]), ReadOnlyList(sources), ReadOnlyList(changes)
        };
        simulate.Invoke(starter, arguments);
        Check(hook.ScheduledSubsteps == 2, "Actual native scheduler did not route both substeps through hooks");
        Check(hook.ScheduledChangeBatches == 1, "Actual native scheduler did not route its queued changes");
        Check(hook.Session.CompletedTicks == 1 && hook.Session.Phase == "Ready", "Hooked native tick did not complete");
        Check(Math.Abs(hook.Session.Added.TotalVolume - 1) < 1e-12, "Hooked source emission volume");
        Check(Math.Abs(hook.Session.Removed.TotalVolume - .25) < 1e-12, "Hooked native pump removal volume");
        Check(Math.Abs(hook.Session.Sample(11).TotalVolume + hook.Session.Sample(12).TotalVolume - 3.75) < 1e-9, "Hooked native tick volume balance");
        var reported = (WaterAmountChange)removed[target];
        Check(Math.Abs(reported.CleanWaterChange - .25) < 1e-6 && reported.ContaminatedWaterChange == 0, "Native removal dictionary did not receive physical intake results");
        Check(parallelizer.SingleJobs == 5, "Native clear/substep/change dependency jobs were not scheduled exactly once");
        Check(removed.Count == 1, "Closed queued targets should apply zero without creating removal results");
        simulate.Invoke(starter, arguments);
        Check(hook.Session.CompletedTicks == 2 && hook.ScheduledSubsteps == 4 && hook.ScheduledChangeBatches == 2, "Hooked scheduler did not preserve state across ticks");
        Check(Math.Abs(hook.Session.Sample(11).TotalVolume + hook.Session.Sample(12).TotalVolume - 4.5) < 1e-9, "Second hooked tick volume balance");
        Check(Math.Abs(((WaterAmountChange)removed[target]).CleanWaterChange - .25) < 1e-6, "Native removal results did not reset per tick");
        sourceProvider.Strength = float.NaN; sources.Clear(); sources.Add(New("ThreadSafeWaterSource", sourceProvider));
        hook.ResolveSource = (source, index, volume) => new FluidVolumes(new double[4]);
        bool invalidRejected = false;
        try { simulate.Invoke(starter, arguments); } catch (TargetInvocationException error) { invalidRejected = error.ToString().Contains("source strength"); }
        Check(invalidRejected, "A nonfinite native source was silently accepted by its custom provider");
        Check(hook.Session.Phase == "Faulted", "A failed source provider left a live partial tick");
      } finally { hook.Dispose(); }
      Check(!hook.HasInstalledPatches, "Scheduler cleanup left owned patches installed");
      void SourceCase(string name, FluidVolumes initial, FluidVolumes expected, int ceiling,
          (float Amount, float Bad)[] operations, string expectedError = null) {
        Array.Clear(columns, 0, columns.Length); Array.Clear(counts, 0, counts.Length);
        counts[12] = 1;
        object column = New("WaterColumn", 0, ceiling);
        Set(column, "WaterDepth", (float)Math.Min(initial.TotalVolume, ceiling));
        Set(column, "Overflow", (float)Math.Max(0, initial.TotalVolume - ceiling));
        columns.SetValue(column, 12);
        sources.Clear(); changes.Clear(); removed.Clear();
        foreach (var operation in operations)
          sources.Add(New("ThreadSafeWaterSource", new Source { Strength = operation.Amount * 4, BadShare = operation.Bad, Point = new Vector3Int(1, 1, 0) }));
        int providerCalls = 0;
        var owner = new NativeTransportHooks(starter, 4, 1);
        owner.SessionCreated = session => session.SeedComposition(12, initial);
        owner.ResolveSource = (source, index, volume) => {
          Check(volume > 0, name + ": withdrawal called an emission provider"); providerCalls++;
          double bad = ((Source)source).BadShare;
          return new FluidVolumes(new[] { 0d, volume * bad, volume * (1 - bad), 0 });
        };
        try {
          owner.Attach();
          var arguments = new[] {
            Lists("DirectedFlow", 25), Array.CreateInstance(Type("WaterFlow"), 25), columns, Array.CreateInstance(Type("ColumnOutflows"), 75),
            new float[75], Array.CreateInstance(Type("Diffusions"), 25), new byte[75], Lists("TargetedDiffusion", 25), removed,
            ReadOnly(counts), ReadOnly(new int[400]), ReadOnly(limits), ReadOnly(inflows), ReadOnly(new float[75]), ReadOnlyList(sources), ReadOnlyList(changes)
          };
          bool rejected = false;
          try { starter.GetType().GetMethod("Simulate", Members).Invoke(starter, arguments); }
          catch (TargetInvocationException error) when (expectedError != null && error.ToString().Contains(expectedError)) { rejected = true; }
          if (expectedError != null) {
            Check(rejected && owner.Session.Phase == "Faulted", name + ": malformed source did not fault visibly");
          } else {
            Check(owner.Session.Phase == "Ready" && owner.Session.CompletedTicks == 1, name + ": source tick did not complete");
            Check(removed.Count == 0, name + ": source withdrawal was reported as a queued pump");
            int emissions = 0; foreach (var operation in operations) if (operation.Amount > 0) emissions++;
            Check(providerCalls == 2 * emissions, name + ": zero/negative sources reached an emission provider");
            for (int c = 0; c < 4; c++) {
              double final = owner.Session.Sample(12).GetVolume(c);
              Check(Math.Abs(final - expected.GetVolume(c)) < 1e-9, name + ": final component " + c);
              double accounted = final + owner.Session.Removed.GetVolume(c) + owner.Session.PressureLoss.GetVolume(c);
              Check(Math.Abs(accounted - initial.GetVolume(c) - owner.Session.Added.GetVolume(c)) < 1e-9, name + ": conservation " + c);
            }
          }
        } finally { owner.Dispose(); }
        Check(!owner.HasInstalledPatches && !NativeTransportHooks.HasActiveOwner, name + ": leaked source-case owner");
      }
      FluidVolumes Mix(params double[] values) => new FluidVolumes(values);
      float drained = 1f - 1f / 1.068215f;
      SourceCase("reported negative badwater source", Mix(0, 0, 1, 0), Mix(0, 0, 1 - 2d * drained, 0), 12, new[] { (-drained, 1f) });
      SourceCase("clean source withdrawal", Mix(.5, 1, .25, .25), Mix(0, 1, 0, 0), 12, new[] { (-.5f, 0f) });
      SourceCase("bad source withdrawal", Mix(.5, 1, .25, .25), Mix(.5, 0, .25, .25), 12, new[] { (-.5f, 1f) });
      SourceCase("complete source drainage", Mix(0, 0, 1, 0), Mix(0, 0, 0, 0), 12, new[] { (-2f, 0f) });
      SourceCase("source addition then withdrawal", Mix(0, 0, 0, 0), Mix(0, 0, 0, 0), 12, new[] { (1f, 0f), (-1f, 1f) });
      SourceCase("source withdrawal then addition", Mix(0, 0, 0, 0), Mix(0, 0, 1, 0), 12, new[] { (-1f, 1f), (1f, 0f) });
      SourceCase("blocked overlapping sources", Mix(.5, .5, .5, 0), Mix(.5, .5, 1.875, 0), 1, new[] { (2f, 0f), (20f, 1f) });
      SourceCase("zero source", Mix(.5, .5, .5, .5), Mix(.5, .5, .5, .5), 12, new[] { (0f, 1f) });
      SourceCase("negative infinite source", Mix(0, 0, 1, 0), Mix(0, 0, 0, 0), 12, new[] { (float.NegativeInfinity, 0f) }, "source strength");
      SourceCase("invalid withdrawal composition", Mix(0, 0, 1, 0), Mix(0, 0, 0, 0), 12, new[] { (-.5f, float.NaN) }, "source composition");

      // Startup contract: the installed types pass, anything else is reported, never attached.
      var contract = NativeSchedulerContract.Check(starter.GetType());
      Check(contract.Count == 0, "Installed scheduler contract reported: " + string.Join("; ", contract));
      Check(NativeSchedulerContract.Check(typeof(ImmediateParallelizer)).Count == 1, "A wrong starter type was not reported");
      bool wrongType = false;
      try { new NativeTransportHooks(new ImmediateParallelizer(), 4, 1); } catch (ArgumentException e) { wrongType = e.Message.Contains("Expected installed native WaterSimulationTaskStarter"); }
      Check(wrongType, "Hooks accepted a non-native starter");

      // Another owner's patch on a task the bridge skips would silently stop running: refuse to attach.
      var foreign = new Harmony("Foreign.FluidTest");
      var skipped = Type("UpdateWaterSourcesTask").GetMethod("Run", Members, null, System.Type.EmptyTypes, null);
      foreign.Patch(skipped, postfix: new HarmonyMethod(typeof(SchedulerProbe), nameof(ForeignPostfix)));
      var blocked = new NativeTransportHooks(starter, 4, 1);
      bool conflict = false;
      try { blocked.Attach(); }
      catch (InvalidOperationException e) { conflict = e.Message.Contains("UpdateWaterSourcesTask.Run is patched by Foreign.FluidTest"); }
      finally { blocked.Dispose(); foreign.UnpatchAll("Foreign.FluidTest"); }
      Check(conflict, "A foreign patch on a skipped native task did not block attachment");
      Check(!blocked.HasInstalledPatches && !NativeTransportHooks.HasActiveOwner, "A refused attachment left patches or an owner");
      var clean = new NativeTransportHooks(starter, 4, 1);
      try { clean.Attach(); Check(clean.HasInstalledPatches, "Attachment failed after the foreign patch was removed"); } finally { clean.Dispose(); }
      Check(!clean.HasInstalledPatches, "Cleanup after the conflict test left patches");
      return checks;
    }
    private static void ForeignPostfix() { }
    private sealed class Source : IWaterSource {
      internal float Strength = 2;
      internal float BadShare;
      internal Vector3Int Point = new Vector3Int(0, 1, 0);
      public ImmutableArray<Vector3Int> Coordinates => ImmutableArray.Create(Point);
      public float SpecifiedStrength => Strength;
      public float CurrentStrength => Strength;
      public float Contamination => BadShare;
      public void SetSpecifiedStrength(float strength) => throw new NotSupportedException();
    }
    // An explicit deterministic fixture executor. The actual game starter and its
    // patched scheduling methods produce the jobs; production worker barriers are a
    // separate acceptance gate. No native parallelizer implementation is copied.
    private sealed class ImmediateParallelizer : IParallelizer {
      public long LastTaskTimestamp => 0;
      public int NumberOfThreads => 1;
      internal int SingleJobs;
      public ParallelizerHandle Schedule<T>(in T task) where T : struct, IParallelizerSingleTask { SingleJobs++; task.Run(); return default; }
      public ParallelizerHandle Schedule<T>(in T task, ParallelizerHandle dependency) where T : struct, IParallelizerSingleTask => Schedule(in task);
      public ParallelizerHandle Schedule<T>(in T task, ReadOnlySpan<ParallelizerHandle> dependencies) where T : struct, IParallelizerSingleTask => Schedule(in task);
      public ParallelizerHandle Schedule<T>(int from, int to, int batch, in T task) where T : struct, IParallelizerLoopTask { for (int i = from; i < to; i++) task.Run(i); return default; }
      public ParallelizerHandle Schedule<T>(int from, int to, int batch, in T task, ParallelizerHandle dependency) where T : struct, IParallelizerLoopTask => Schedule(from, to, batch, in task);
      public ParallelizerHandle Schedule<T>(int from, int to, int batch, in T task, ReadOnlySpan<ParallelizerHandle> dependencies) where T : struct, IParallelizerLoopTask => Schedule(from, to, batch, in task);
      public void StartScheduling() { }
      public void StopScheduling() { }
      public void Wait() { }
      public void ThrowIfAnyPendingTasks() { }
    }
  }
}
