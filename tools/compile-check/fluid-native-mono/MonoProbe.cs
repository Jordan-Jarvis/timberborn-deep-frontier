using System;
using System.Collections;
using System.Reflection;
using System.IO;
using FluidsApi.Native.Prototype;
using FluidsApi.Transport.Prototype;

namespace FluidsApi.Native.Acceptance {
  public static class MonoProbe {
    private const BindingFlags Members = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;
    public static string Run(string managed) {
      int checks = 0;
      void Check(bool condition, string name) { checks++; if (!condition) throw new InvalidOperationException(name); }
      var water = Assembly.LoadFrom(Path.Combine(managed, "Timberborn.WaterSystem.dll"));
      var common = Assembly.LoadFrom(Path.Combine(managed, "Timberborn.Common.dll"));
      Type Type(string name) => water.GetType("Timberborn.WaterSystem." + name, true);
      object New(string name, params object[] arguments) => Activator.CreateInstance(Type(name), Members, null, arguments, null);
      void Set(object target, string name, object value) => target.GetType().GetField(name, Members).SetValue(target, value);
      object ReadOnly(Array array) => Activator.CreateInstance(common.GetType("Timberborn.Common.ReadOnlyArray`1", true).MakeGenericType(array.GetType().GetElementType()), new object[] { array });
      var overflow = New("WaterOverflowCalculator", null, null);
      Set(overflow, "_maxPressure", 16f); Set(overflow, "_overflowPressureFactorInverted", .125f);
      var setter = New("WaterDepthSetter", overflow);
      var columns = Array.CreateInstance(Type("WaterColumn"), 75);
      object column = New("WaterColumn", 0, 1);
      Set(column, "WaterDepth", 1f); Set(column, "Overflow", .5f); Set(column, "Contamination", 1f / 3);
      columns.SetValue(column, 12);
      var counts = new byte[25]; counts[12] = 1;
      var baseFlows = Array.CreateInstance(Type("WaterFlow"), 25);
      var outflows = Array.CreateInstance(Type("ColumnOutflows"), 75);
      var lists = Array.CreateInstance(typeof(System.Collections.Generic.List<>).MakeGenericType(Type("DirectedFlow")), 25);
      for (int i = 0; i < 25; i++) lists.SetValue(Activator.CreateInstance(lists.GetType().GetElementType()), i);
      var backend = new NativeWaterArrayAdapter(columns, counts, baseFlows, lists, 3, 3, 5, 25, setter, overflow);
      var session = new NativeFluidTransportSession(backend, 4, 1);
      session.SeedComposition(12, new FluidVolumes(new[] { .5, .5, .5, 0 }));
      Check(session.Sample(12).TotalVolume == 1.5, "Mono physical pressure initialization");

      // Build the actual installed depth task; no game method bodies are copied here.
      var immutable = Assembly.Load("System.Collections.Immutable").GetType("System.Collections.Immutable.ImmutableArray", true);
      MethodInfo create = null;
      foreach (var method in immutable.GetMethods()) if (method.Name == "Create" && method.IsGenericMethodDefinition &&
          method.GetParameters().Length == 1 && method.GetParameters()[0].ParameterType.IsArray) create = method;
      if (create == null) throw new MissingMethodException("ImmutableArray.Create<T>(T[])");
      object offsets = create.MakeGenericMethod(typeof(int)).Invoke(null, new object[] { new[] { -5, -1, 5, 1 } });
      var task = New("WaterParametersUpdateTask", setter, columns, outflows, ReadOnly(counts), offsets,
        ReadOnly(baseFlows), ReadOnly(new float[75]), ReadOnly(lists), 3, 5, 25, .25f, .8f, .02f, .001f, .0001f);
      var run = task.GetType().GetMethod("Run", Members, null, new[] { typeof(int) }, null);
      session.BeginTick(2);
      for (int substep = 0; substep < 2; substep++) {
        session.RunSubstep(() => { }, () => {
          for (int y = 0; y < 3; y++) run.Invoke(task, new object[] { y });
          return new double[1];
        }, () => new FluidDiffusionLink[0], .25, 0);
        if (substep == 1) session.AddSource(12, new FluidVolumes(new[] { 0d, 0, 2, 0 }));
        session.FinishSubstep();
      }
      Check(Math.Abs(session.Sample(12).TotalVolume - 2.875) < 1e-12, "Mono pressure source capacity");
      Check(Math.Abs(session.PressureLoss.TotalVolume - .625) < 1e-12, "Mono pressure loss accounting");
      var removed = session.RemoveQueued(12, .75, .25);
      Check(Math.Abs(removed.Removed.TotalVolume - 1) < 1e-12, "Mono physical pump result");
      session.EndTick();
      Check(session.CompletedTicks == 1 && session.Phase == "Ready", "Mono native stage order");
      Check(Math.Abs(backend.PhysicalVolume(12) - session.Sample(12).TotalVolume) < 1e-6, "Mono native depth publication");
      Check(Math.Abs(backend.BadwaterShare(12) - session.Sample(12).GetShare(1)) < 1e-6, "Mono native badwater publication");
      Check(typeof(NativeFluidTransportSession).Assembly.GetTypes().Length > 0, "Mono reflected type enumeration");
      var sample = typeof(NativeFluidTransportSession).GetMethod("Sample");
      Check(((FluidVolumes)sample.Invoke(session, new object[] { 12 })).TotalVolume > 0, "Mono reflected invocation");
      counts[13] = 1; columns.SetValue(New("WaterColumn", 0, 1), 13);
      object demands = baseFlows.GetValue(12); Set(demands, "Right", 100f); baseFlows.SetValue(demands, 12);
      var transfers = backend.BudgetFlowRequests(backend.CaptureGeometry(), new[] { session.Sample(12), new FluidVolumes(new double[4]) }, .31);
      Check(transfers.Length == 1, "Mono raw native flow discovery");
      Check(transfers[0].Volume > 0 && transfers[0].Volume <= session.Sample(12).TotalVolume, "Mono float producer budget");
      Check(backend.LastUnfulfilledFlowDemand > 0, "Mono demand accounting");
      checks += SchedulerProbe.Run(managed);
      return "PASS " + checks + " Mono checks: native scheduler hooks, ordered signed sources, pressure admission, physical pump results, owner cleanup, producer budget and reflection";
    }
  }
}
