using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;
using Timberborn.Common;
using Timberborn.MapIndexSystem;
using Timberborn.Multithreading;
using Timberborn.SoilMoistureSystem;
using Timberborn.TickSystem;
using Timberborn.WaterSystem;
using UnityEngine;
using ModdableFluids.Native.Prototype;
using ModdableFluids.Runtime.Prototype;
using ModdableFluids.Transport.Prototype;
using ModdableFluids.World.Prototype;

namespace ModdableFluids.Native.Acceptance {
  /// <summary>
  /// Moddable Fluids 0.1.4 native hooks under the installed Mono: every startup contract (intake guard, moisture input,
  /// placed sources, exception-save flag) passes against the installed assemblies, and the moisture prefix installs on
  /// the actual native SoilMoistureSimulationTaskStarter.StartTask, replaces the moisture tasks' water columns with
  /// contamination raised by a blocking fluid, rejects an argument that is not the thread-safe map's array, refuses a
  /// foreign owner and uninstalls cleanly.
  /// </summary>
  internal static class HooksProbe {
    private const BindingFlags Members = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;
    private static object _observed;

    internal static int Run() {
      int checks = 0;
      void Check(bool condition, string name) { checks++; if (!condition) throw new InvalidOperationException(name); }
      var guard = FluidWaterIntakeGuard.CheckContract(); var moistureContract = FluidMoistureInput.CheckContract(); var sources = FluidPlacedSource.CheckContract();
      Check(guard.Count == 0, "Installed intake-guard contract reported: " + string.Join("; ", guard));
      Check(moistureContract.Count == 0, "Installed moisture contract reported: " + string.Join("; ", moistureContract));
      Check(sources.Count == 0, "Installed placed-source contract reported: " + string.Join("; ", sources));
      Check(typeof(TickOnlyArrayService).GetField("_forceAllowAccess", BindingFlags.Instance | BindingFlags.NonPublic)?.FieldType == typeof(bool), "Exception-save flag");

      var host = new ModdableFluidsHost();
      host.RegisterProvider(new SaltProvider());
      var registry = host.Freeze();
      int salt = registry.GetHandle("Probe.Saltwater").Index;
      // Native session over two columns of a 3 by 3 map: (1, 1) holds 5% saltwater, (2, 1) none.
      var water = typeof(IWaterService).Assembly;
      Type Native(string name) => water.GetType("Timberborn.WaterSystem." + name, true);
      object New(string name, params object[] arguments) => Activator.CreateInstance(Native(name), Members, null, arguments, null);
      void Set(object target, string name, object value) => target.GetType().GetField(name, Members).SetValue(target, value);
      var overflow = New("WaterOverflowCalculator", null, null);
      Set(overflow, "_maxPressure", 16f); Set(overflow, "_overflowPressureFactorInverted", .125f);
      var setter = New("WaterDepthSetter", overflow);
      var columns = Array.CreateInstance(Native("WaterColumn"), 75);
      foreach (var (cell, depth) in new[] { (12, 2f), (13, 1f) }) {
        object column = New("WaterColumn", 0, 4); Set(column, "WaterDepth", depth); columns.SetValue(column, cell);
      }
      var counts = new byte[25]; counts[12] = 1; counts[13] = 1;
      var lists = Array.CreateInstance(typeof(List<>).MakeGenericType(Native("DirectedFlow")), 25);
      for (int i = 0; i < 25; i++) lists.SetValue(Activator.CreateInstance(lists.GetType().GetElementType()), i);
      var adapter = new NativeWaterArrayAdapter(columns, counts, Array.CreateInstance(Native("WaterFlow"), 25), lists, 3, 3, 5, 25, setter, overflow);
      var session = new NativeFluidTransportSession(adapter, registry.Count, FluidRegistry.BadwaterIndex);
      var seeded = new double[registry.Count]; seeded[0] = 1.9; seeded[salt] = .1;
      session.SeedComposition(12, new FluidVolumes(seeded));
      var state = new FluidWorldState(registry, 5);
      state.Publish(session);
      // The thread-safe map's copy of the same columns.
      var threadSafe = new ReadOnlyWaterColumn[50];
      ReadOnlyWaterColumn Column(byte floor, byte ceiling, float depth, float contamination) {
        object boxed = default(ReadOnlyWaterColumn);
        foreach (var (field, value) in new (string, object)[] { ("Floor", floor), ("Ceiling", ceiling), ("WaterDepth", depth), ("Contamination", contamination) })
          typeof(ReadOnlyWaterColumn).GetField("<" + field + ">k__BackingField", Members).SetValue(boxed, value);
        return (ReadOnlyWaterColumn)boxed;
      }
      threadSafe[12] = Column(0, 4, 2, .25f); threadSafe[13] = Column(0, 4, 1, 0);
      var map = new ProbeMap(threadSafe, counts);
      var index = (MapIndexService)Activator.CreateInstance(typeof(MapIndexService), new object[] { null });
      typeof(MapIndexService).GetProperty("Stride").SetValue(index, 5); typeof(MapIndexService).GetProperty("VerticalStride").SetValue(index, 25);
      var moisture = new FluidMoistureInput(map, null, index);
      Check(moisture.Prepare(registry, .53f).Count == 0, "No foreign owner on the native moisture input");
      moisture.Install(state);
      Check(moisture.Installed && moisture.HasOwnedPatch && FluidMoistureInput.HasActiveOwner, "Moisture prefix installed on the native method");
      moisture.Tick();
      var target = typeof(ISoilMoistureService).Assembly.GetType("Timberborn.SoilMoistureSystem.SoilMoistureSimulationTaskStarter", true).GetMethod("StartTask", Members);
      var observer = new Harmony("Probe.MoistureObserver");
      observer.Patch(target, prefix: new HarmonyMethod(typeof(HooksProbe), nameof(Observe)) { priority = Priority.Last });
      object starter = Activator.CreateInstance(target.DeclaringType, Members, null, new object[] { new StoppingParallelizer(), null, null, null, null, null }, null);
      object[] Arguments(ReadOnlyWaterColumn[] columnsArgument) => new object[] {
        new byte[50], new byte[50], new float[50], new bool[50], new float[50], new float[50], new ReadOnlyArray<bool>(new bool[50]), new ReadOnlyArray<bool>(new bool[50]),
        new ReadOnlyArray<byte>(counts), new ReadOnlyArray<ReadOnlyWaterColumn>(columnsArgument), new ReadOnlyArray<byte>(new byte[25]), null };
      bool Stopped(object[] arguments) {
        try { target.Invoke(starter, arguments); return false; }
        catch (TargetInvocationException e) { return e.InnerException is StoppedHere; }
      }
      try {
        _observed = null;
        Check(Stopped(Arguments(threadSafe)), "The native method ran past its moisture input");
        var seen = ((ReadOnlyArray<ReadOnlyWaterColumn>)_observed).AsSpan;
        Check(seen != threadSafe.AsSpan(), "The moisture tasks still received the thread-safe map's own array");
        Check(Math.Abs(seen[12].Contamination - (.25f + (float)(.05 * .53 / .1))) < 1e-6, "Saltwater at 5% raised contamination like badwater: " + seen[12].Contamination);
        Check(seen[13].Contamination == 0 && seen[13].WaterDepth == 1 && seen[12].Floor == 0 && seen[12].Ceiling == 4 && seen[12].WaterDepth == 2, "Other values and columns unchanged");
        Check(threadSafe[12].Contamination == .25f, "The thread-safe map itself was written");
        Check(moisture.Substitutions == 1 && moisture.LastRaisedColumns == 1, "One substitution, one raised column");
        bool foreignArray = false;
        try { target.Invoke(starter, Arguments((ReadOnlyWaterColumn[])threadSafe.Clone())); }
        catch (TargetInvocationException e) { foreignArray = e.InnerException is InvalidOperationException && e.InnerException.Message.Contains("thread-safe water map"); }
        Check(foreignArray, "An argument that is not the thread-safe map's array was accepted");
      } finally { observer.UnpatchAll("Probe.MoistureObserver"); }
      moisture.Uninstall();
      Check(!moisture.HasOwnedPatch && !FluidMoistureInput.HasActiveOwner, "Moisture prefix removed at unload");
      _observed = null;
      var plain = new Harmony("Probe.MoistureObserver");
      plain.Patch(target, prefix: new HarmonyMethod(typeof(HooksProbe), nameof(Observe)));
      try {
        Check(Stopped(Arguments(threadSafe)) && ((ReadOnlyArray<ReadOnlyWaterColumn>)_observed).AsSpan == threadSafe.AsSpan(), "After unload the native input is the map's own array");
        // Another owner on the same method: the next scene refuses before installing anything.
        var refused = new FluidMoistureInput(map, null, index);
        var conflicts = refused.Prepare(registry, .53f);
        Check(conflicts.Count == 1 && conflicts[0].Contains("Probe.MoistureObserver"), "A foreign owner on the moisture input was not reported");
        bool threw = false;
        try { refused.Install(state); } catch (InvalidOperationException e) { threw = e.Message.Contains("Probe.MoistureObserver"); }
        Check(threw && !refused.HasOwnedPatch && !FluidMoistureInput.HasActiveOwner, "A refused moisture input installed or left an owner");
      } finally { plain.UnpatchAll("Probe.MoistureObserver"); }
      return checks;
    }

    private static void Observe(ReadOnlyArray<ReadOnlyWaterColumn> waterColumns) => _observed = waterColumns;

    private sealed class StoppedHere : Exception { }

    private sealed class SaltProvider : IFluidProvider {
      public string ProviderId => "Probe.Liquids";
      public string OwnerModId => "Probe";
      public string MinimumApiVersion => "0.1.3";
      public IReadOnlyCollection<string> RequiredCapabilities { get; } = new[] { "ModdableFluids.Policies.Irrigation", "ModdableFluids.Policies.WaterIntakes" };
      public void Register(FluidRegistration registration) {
        registration.AddFluid("Saltwater", "Probe.Saltwater", .15f, .45f, .55f, .35f);
        registration.SetWaterIntakePolicy("Saltwater", .1, "Probe.BrackishDrawnAsWater", "Probe.Refused", "Probe.RefusedAlert");
        registration.SetBlocksMoisture("Saltwater", .1);
      }
    }

    // Stops the native method at its first scheduling call, after its prefixes ran: no native task executes.
    private sealed class StoppingParallelizer : IParallelizer {
      public long LastTaskTimestamp => 0;
      public int NumberOfThreads => 1;
      public ParallelizerHandle Schedule<T>(in T task) where T : struct, IParallelizerSingleTask => throw new StoppedHere();
      public ParallelizerHandle Schedule<T>(in T task, ParallelizerHandle dependency) where T : struct, IParallelizerSingleTask => throw new StoppedHere();
      public ParallelizerHandle Schedule<T>(in T task, ReadOnlySpan<ParallelizerHandle> dependencies) where T : struct, IParallelizerSingleTask => throw new StoppedHere();
      public ParallelizerHandle Schedule<T>(int from, int to, int batch, in T task) where T : struct, IParallelizerLoopTask => throw new StoppedHere();
      public ParallelizerHandle Schedule<T>(int from, int to, int batch, in T task, ParallelizerHandle dependency) where T : struct, IParallelizerLoopTask => throw new StoppedHere();
      public ParallelizerHandle Schedule<T>(int from, int to, int batch, in T task, ReadOnlySpan<ParallelizerHandle> dependencies) where T : struct, IParallelizerLoopTask => throw new StoppedHere();
      public void StartScheduling() { }
      public void StopScheduling() { }
      public void Wait() { }
      public void ThrowIfAnyPendingTasks() { }
    }

    private sealed class ProbeMap : IThreadSafeWaterMap {
      private readonly ReadOnlyWaterColumn[] _columns;
      private readonly byte[] _counts;
      internal ProbeMap(ReadOnlyWaterColumn[] columns, byte[] counts) { _columns = columns; _counts = counts; }
      public ReadOnlyArray<ReadOnlyWaterColumn> WaterColumns => new ReadOnlyArray<ReadOnlyWaterColumn>(_columns);
      public ReadOnlyArray<byte> ColumnCounts => new ReadOnlyArray<byte>(_counts);
      public int MaxColumnCount => 2;
      public bool AnyColumnChanged => false;
      public ReadOnlyArray<Vector2> FlowDirections => throw new NotSupportedException();
      public event EventHandler<int> MaxWaterColumnCountChanged { add { } remove { } }
      public int ColumnCount(int index2D) => _counts[index2D];
      public byte ColumnFloor(int index3D) => throw new NotSupportedException();
      public byte ColumnCeiling(int index3D) => throw new NotSupportedException();
      public byte ColumnCeiling(Vector3Int coordinates) => throw new NotSupportedException();
      public float WaterDepth(int index3D) => throw new NotSupportedException();
      public float WaterDepth(Vector3Int coordinates) => throw new NotSupportedException();
      public float ColumnContamination(Vector3Int coordinates) => throw new NotSupportedException();
      public float ColumnOverflow(Vector3Int coordinates) => throw new NotSupportedException();
      public Vector2 WaterFlowDirection(Vector3Int coordinates) => throw new NotSupportedException();
      public bool TryGetColumnFloor(Vector3Int coordinates, out int floor) => throw new NotSupportedException();
      public int CeiledWaterHeight(Vector3Int coordinates) => throw new NotSupportedException();
      public float WaterHeightOrFloor(Vector3Int coordinates) => throw new NotSupportedException();
      public bool CellIsUnderwater(Vector3Int coordinates) => throw new NotSupportedException();
      public bool IsWaterOnAnyHeight(Vector2Int coordinates) => throw new NotSupportedException();
    }
  }
}
