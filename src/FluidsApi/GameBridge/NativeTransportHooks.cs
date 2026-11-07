using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using Timberborn.Multithreading;
using FluidsApi.Native.Prototype;
using FluidsApi.Transport.Prototype;

namespace FluidsApi.GameBridge.Prototype {
  /// <summary>
  /// Explicit development attachment for one native water starter. Does not auto-start,
  /// install content, or attach to another scene. Dispose only after its native jobs finish.
  /// This correctness prototype serializes each substep inside one dependent native job.
  /// </summary>
  public sealed class NativeTransportHooks : IDisposable {
    private const BindingFlags Members = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
    private const string OwnerId = "FluidsApi.Prototype.NativeTransport";
    private static volatile NativeTransportHooks _active;
    public static bool HasActiveOwner => _active != null;
    private static readonly object LifecycleGate = new object();
    private readonly object _starter;
    private readonly int _components, _badwater;
    private readonly Harmony _harmony;
    private readonly MethodInfo _stepMethod, _changesMethod;
    private bool _disposed;
    private bool _ownsPatches;
    public NativeFluidTransportSession Session { get; private set; }
    public int ScheduledSubsteps { get; private set; }
    public int ScheduledChangeBatches { get; private set; }
    public Action<NativeFluidTransportSession> SessionCreated { get; set; }
    public Func<object, int, double, FluidVolumes> ResolveSource { get; set; }
    public Func<object, int, double, double, FluidVolumes> ResolveAddition { get; set; }
    private bool AnyOwnedPatches() => new[] { _stepMethod, _changesMethod }.Any(method => Harmony.GetPatchInfo(method)?.Owners.Contains(OwnerId) == true);
    public bool HasInstalledPatches => _ownsPatches && AnyOwnedPatches();

    public NativeTransportHooks(object nativeStarter, int componentCount, int badwaterComponent) {
      if (nativeStarter == null || nativeStarter.GetType().FullName != "Timberborn.WaterSystem.WaterSimulationTaskStarter")
        throw new ArgumentException("Expected installed native WaterSimulationTaskStarter");
      if (componentCount < 2 || badwaterComponent <= 0 || badwaterComponent >= componentCount) throw new ArgumentException("Invalid component layout");
      _starter = nativeStarter; _components = componentCount; _badwater = badwaterComponent;
      var type = nativeStarter.GetType();
      var parameters = type.GetNestedType("SimulationParameters", BindingFlags.NonPublic | BindingFlags.Public)
        ?? throw new MissingMemberException("WaterSimulationTaskStarter.SimulationParameters");
      _stepMethod = type.GetMethod("ScheduleSimulationSteps", Members, null, new[] { typeof(ParallelizerHandle), parameters.MakeByRefType() }, null)
        ?? throw new MissingMethodException("ScheduleSimulationSteps(ParallelizerHandle, in SimulationParameters)");
      _changesMethod = type.GetMethod("ScheduleUpdateWaterChanges", Members, null, new[] { typeof(ParallelizerHandle), parameters.MakeByRefType() }, null)
        ?? throw new MissingMethodException("ScheduleUpdateWaterChanges(ParallelizerHandle, in SimulationParameters)");
      if (_stepMethod.ReturnType != typeof(ParallelizerHandle) || _changesMethod.ReturnType != typeof(void) ||
          (int)type.GetField("SubstepCount", BindingFlags.Static | BindingFlags.NonPublic).GetValue(null) != 2)
        throw new InvalidOperationException("Unsupported native scheduling contract; expected Timberborn 1.1.2.8");
      _harmony = new Harmony(OwnerId);
    }
    public void Attach() {
      lock (LifecycleGate) {
        if (_disposed || _active != null || AnyOwnedPatches()) throw new InvalidOperationException("A native fluid transport attachment already exists or was disposed");
        RequireNoLegacyRadiationOwner(); _active = this; _ownsPatches = true;
        try {
          _harmony.Patch(_stepMethod, prefix: new HarmonyMethod(typeof(NativeTransportHooks), nameof(StepPrefix)));
          _harmony.Patch(_changesMethod, prefix: new HarmonyMethod(typeof(NativeTransportHooks), nameof(ChangesPrefix)));
        } catch { try { RemoveOwnPatches(); } finally { _active = null; _ownsPatches = false; } throw; }
      }
    }
    private static bool StepPrefix(object __instance, object[] __args, ref ParallelizerHandle __result) {
      var owner = _active;
      if (owner == null || !ReferenceEquals(owner._starter, __instance)) return true;
      var job = new SubstepJob(owner, __args[1]);
      __result = ((IParallelizer)Field(__instance, "_parallelizer")).Schedule(in job, (ParallelizerHandle)__args[0]);
      owner.ScheduledSubsteps++;
      return false;
    }
    private static bool ChangesPrefix(object __instance, object[] __args) {
      var owner = _active;
      if (owner == null || !ReferenceEquals(owner._starter, __instance)) return true;
      var job = new ChangesJob(owner, __args[1]);
      ((IParallelizer)Field(__instance, "_parallelizer")).Schedule(in job, (ParallelizerHandle)__args[0]);
      owner.ScheduledChangeBatches++;
      return false;
    }
    private void RunSubstep(object parameters) {
      if (_disposed) throw new InvalidOperationException("Native jobs must finish before disposing fluid transport");
      RequireNoLegacyRadiationOwner();
      var water = (Array)Property(parameters, "WaterColumns");
      var counts = (byte[])Unwrap(Property(parameters, "WaterColumnCounts"));
      var flows = (Array)Property(parameters, "BaseLevelFlows");
      var directed = (Array)Property(parameters, "DirectedFlows");
      int stride = (int)Field(_starter, "_stride"), vertical = (int)Field(_starter, "_verticalStride");
      object size = Field(_starter, "_mapSize"); int width = Coordinate(size, "x"), height = Coordinate(size, "y");
      object setter = Field(_starter, "_waterDepthSetter");
      var backend = new NativeWaterArrayAdapter(water, counts, flows, directed, width, height, stride, vertical, setter, Field(setter, "_waterOverflowCalculator"));
      if (Session == null) { Session = new NativeFluidTransportSession(backend, _components, _badwater); SessionCreated?.Invoke(Session); }
      if (Session.Phase == "Ready") { Session.ReconcileGeometry(backend); Session.BeginTick(2); }
      var before = Enumerable.Range(0, Session.ColumnCount).Select(Session.GetGeometry).ToArray();
      var outflows = Property(parameters, "Outflows");
      object ReadOnly(object array) => Activator.CreateInstance(Property(parameters, "WaterColumnCounts").GetType().GetGenericTypeDefinition()
        .MakeGenericType(array.GetType().GetElementType()), new[] { array });
      float Value(string name) => (float)Field(_starter, name);
      double deltaTime = Value("_deltaTime");
      var nativeOutflow = Task(water, "OutflowsUpdateTask", Field(_starter, "_flowLimitCalculator"), Field(_starter, "_waterFlowRetriever"), directed, flows,
        Property(parameters, "WaterColumnCounts"), ReadOnly(water), Property(parameters, "LimitedDirections"), Property(parameters, "HeightLimits"),
        Property(parameters, "InflowLimits"), ReadOnly(outflows), width, stride, vertical, (float)deltaTime, Value("_overflowPressureFactor"),
        Value("_maxHardDamDecrease"), Value("_hardDamSmoothingFactor"), Value("_minHardDamSmoothing"), Value("_maxHardDamSmoothing"),
        Value("_hardDamOffset"), Value("_softDamOffset"), Value("_waterSpillThreshold"), Value("_waterFlowFactor"));
      var nativeDepth = Task(water, "WaterParametersUpdateTask", setter, water, outflows, Property(parameters, "WaterColumnCounts"), Field(_starter, "_neighborOffsets"),
        ReadOnly(flows), Property(parameters, "EvaporationModifiers"), ReadOnly(directed), width, stride, vertical, (float)deltaTime,
        Value("_outflowBalancingScaler"), Value("_fastEvaporationDepthThreshold"), Value("_fastEvaporationSpeed"), Value("_normalEvaporationSpeed"));
      var nativeSimulate = Task(water, "SimulateContaminationTask", Field(_starter, "_flowLimitCalculator"), Field(_starter, "_waterFlowRetriever"),
        Property(parameters, "ContaminationsBuffer"), Property(parameters, "BaseLevelDiffusions"), Property(parameters, "TargetedDiffusionCount"),
        Property(parameters, "TargetedDiffusions"), Property(parameters, "WaterColumnCounts"), ReadOnly(water), ReadOnly(outflows),
        Property(parameters, "LimitedDirections"), Property(parameters, "HeightLimits"), width, stride, vertical, (float)deltaTime, Value("_overflowPressureFactor"),
        Value("_maxWaterContamination"), Field(_starter, "_diffusionOutflowLimit"), Field(_starter, "_diffusionDepthLimit"));
      var evaporationModifiers = (float[])Unwrap(Property(parameters, "EvaporationModifiers"));
      double[] evaporation = new double[before.Length];
      for (int i = 0; i < before.Length; i++) {
        float depth = (float)Field(water.GetValue(before[i].NativeIndex), "WaterDepth");
        float speed = depth < Value("_fastEvaporationDepthThreshold") ? Value("_fastEvaporationSpeed") : Value("_normalEvaporationSpeed");
        evaporation[i] = (double)(speed * evaporationModifiers[before[i].NativeIndex]) * deltaTime;
      }
      Session.RunSubstep(() => Rows(nativeOutflow, height), () => { Rows(nativeDepth, height); return evaporation; },
        () => { Rows(nativeSimulate, height); return DiffusionLinks(parameters, before, stride, vertical); }, deltaTime, Value("_diffusionRate") * deltaTime);
      foreach (object source in (IEnumerable)Property(parameters, "WaterSources")) {
        float strength = (float)Property(source, "CurrentStrength");
        if (float.IsNaN(strength) || float.IsInfinity(strength)) throw new InvalidOperationException("Native source strength must be finite");
        if (strength == 0) continue;
        var coordinates = ((IEnumerable)Property(source, "Coordinates")).Cast<object>().ToArray();
        if (coordinates.Length == 0) throw new InvalidOperationException("Native source has no coordinates");
        double volume = (double)(float)((float)deltaTime * strength / coordinates.Length);
        if (double.IsNaN(volume) || double.IsInfinity(volume)) throw new InvalidOperationException("Native source volume must be finite");
        double bad = (float)Property(source, "Contamination");
        if (bad < 0 || bad > 1 || double.IsNaN(bad)) throw new InvalidOperationException("Invalid native source composition");
        foreach (object coordinate in coordinates) {
          int index = FindColumn(coordinate, stride);
          if (volume < 0) {
            // No fluid is emitted. Preserve the remaining non-bad mixture rather
            // than calling an emission provider with a negative addition.
            Session.RemoveSource(index, -volume, bad);
            continue;
          }
          var mixture = ResolveSource != null ? ResolveSource(Field(source, "_waterSource"), index, volume) : Vanilla(volume, bad);
          RequireVolume(mixture, volume);
          Session.AddSource(index, mixture);
        }
      }
      Session.FinishSubstep();
    }
    private void RunChanges(object parameters) {
      if (_disposed || Session == null) throw new InvalidOperationException("No completed fluid substeps for native water changes");
      int stride = (int)Field(_starter, "_stride");
      var removed = (IDictionary)Property(parameters, "RemovedWater"); removed.Clear();
      foreach (object change in (IEnumerable)Property(parameters, "WaterChanges")) {
        object coordinate = Property(change, "Coordinates");
        // Native UpdateWaterChangesTask.TryGetColumnIndex also applies zero when
        // a queued intake/dump loses its column before the changes are processed.
        if (!TryFindColumn(coordinate, stride, out int index)) continue;
        double volume = (float)Property(change, "DepthChange"), bad = (float)Property(change, "ContaminationChange");
        if (bad < 0 || bad > 1 || double.IsNaN(bad)) throw new InvalidOperationException("Invalid native water-change composition");
        if (volume >= 0) {
          var mixture = ResolveAddition != null ? ResolveAddition(change, index, volume, bad) : Vanilla(volume, bad);
          RequireVolume(mixture, volume); Session.AddQueued(index, mixture);
        } else {
          var result = Session.RemoveQueued(index, -volume * (1 - bad), -volume * bad);
          double contaminated = result.Removed.GetVolume(_badwater), clean = result.Removed.TotalVolume - contaminated;
          if (removed.Contains(coordinate)) {
            clean += (float)Property(removed[coordinate], "CleanWaterChange");
            contaminated += (float)Property(removed[coordinate], "ContaminatedWaterChange");
          }
          var amountType = change.GetType().Assembly.GetType("Timberborn.WaterSystem.WaterAmountChange", true);
          removed[coordinate] = Activator.CreateInstance(amountType, (float)clean, (float)contaminated);
        }
      }
      Session.EndTick();
    }
    private FluidVolumes Vanilla(double volume, double badShare) {
      var values = new double[_components]; values[_badwater] = volume * badShare; values[0] = volume - values[_badwater];
      return new FluidVolumes(values);
    }
    private void RequireVolume(FluidVolumes mixture, double expected) {
      if (expected < 0 || double.IsNaN(expected) || double.IsInfinity(expected) || mixture == null || mixture.ComponentCount != _components ||
          Math.Abs(mixture.TotalVolume - expected) > 4 * _components * 2.2204460492503131e-16 * expected)
        throw new InvalidOperationException("Fluid provider must preserve the requested physical addition volume and component layout");
    }
    private int FindColumn(object coordinate, int stride) {
      if (TryFindColumn(coordinate, stride, out int index)) return index;
      throw new InvalidOperationException("Native source has no open column at " + coordinate);
    }
    private bool TryFindColumn(object coordinate, int stride, out int index) {
      int cell = (Coordinate(coordinate, "y") + 1) * stride + Coordinate(coordinate, "x") + 1, z = Coordinate(coordinate, "z");
      object size = Field(_starter, "_mapSize");
      if (Coordinate(coordinate, "x") < -1 || Coordinate(coordinate, "x") > Coordinate(size, "x") ||
          Coordinate(coordinate, "y") < -1 || Coordinate(coordinate, "y") > Coordinate(size, "y"))
        throw new ArgumentOutOfRangeException(nameof(coordinate), "Native change lies outside the padded map");
      for (int i = 0; i < Session.ColumnCount; i++) {
        var geometry = Session.GetGeometry(i);
        if (geometry.CellIndex == cell && z >= geometry.Floor && z < geometry.Ceiling) { index = geometry.NativeIndex; return true; }
      }
      index = -1; return false;
    }
    private static FluidDiffusionLink[] DiffusionLinks(object parameters, FluidColumnGeometry[] columns, int stride, int vertical) {
      var slots = columns.Select((column, slot) => new { column.NativeIndex, Slot = slot }).ToDictionary(v => v.NativeIndex, v => v.Slot);
      var baseFlags = (Array)Property(parameters, "BaseLevelDiffusions");
      var targeted = (Array)Property(parameters, "TargetedDiffusions");
      var pairs = new HashSet<long>();
      void Add(int first, int second) {
        bool Boundary(int index) { int cell = index % vertical, x = cell % stride, y = cell / stride; return x == 0 || x == stride - 1 || y == 0 || y == vertical / stride - 1; }
        if (Boundary(first) || Boundary(second)) return;
        if (!slots.TryGetValue(first, out int a) || !slots.TryGetValue(second, out int b)) throw new InvalidOperationException("Native diffusion targets a missing interior column");
        int low = Math.Min(a, b), high = Math.Max(a, b); pairs.Add(((long)low << 32) | (uint)high);
      }
      foreach (var column in columns) {
        if (column.NativeIndex < vertical) {
          object flags = baseFlags.GetValue(column.NativeIndex);
          foreach (var pair in new[] { ("Bottom", -stride), ("Left", -1), ("Top", stride), ("Right", 1) })
            if ((bool)Field(flags, pair.Item1)) Add(column.NativeIndex, column.NativeIndex + pair.Item2);
        }
        foreach (object pair in (IEnumerable)targeted.GetValue(column.CellIndex)) if ((int)Field(pair, "OriginIndex3D") == column.NativeIndex)
          Add(column.NativeIndex, (int)Field(pair, "TargetIndex3D"));
      }
      return pairs.OrderBy(pair => pair).Select(pair => new FluidDiffusionLink((int)(pair >> 32), (int)(uint)pair)).ToArray();
    }
    private static void Rows(object task, int height) { var run = task.GetType().GetMethod("Run", Members); for (int y = 0; y < height; y++) run.Invoke(task, new object[] { y }); }
    private static object Task(Array water, string name, params object[] args) => Activator.CreateInstance(water.GetType().GetElementType().Assembly.GetType("Timberborn.WaterSystem." + name, true), Members, null, args, null);
    private static object Field(object value, string name) => (value.GetType().GetField(name, Members) ?? throw new MissingFieldException(value.GetType().FullName, name)).GetValue(value);
    private static object Property(object value, string name) => (value.GetType().GetProperty(name, Members) ?? throw new MissingMemberException(value.GetType().FullName, name)).GetValue(value);
    private static object Unwrap(object readOnly) => Field(readOnly, "_array");
    private static int Coordinate(object value, string name) => (int)Property(value, name);
    private static void RequireNoLegacyRadiationOwner() {
      var assembly = AppDomain.CurrentDomain.GetAssemblies().SingleOrDefault(value => value.GetName().Name == "DeepFrontier");
      var type = assembly?.GetType("DeepFrontier.Scripts.Radiation.RadiationLockstep", false);
      if (type?.GetProperty("Simulation", BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic)?.GetValue(null) != null)
        throw new InvalidOperationException("Deep Frontier's legacy radiation transport is active. Migrate it before attaching the shared transport owner.");
    }
    private void RemoveOwnPatches() {
      _harmony.Unpatch(_stepMethod, HarmonyPatchType.All, OwnerId);
      _harmony.Unpatch(_changesMethod, HarmonyPatchType.All, OwnerId);
    }
    public void Dispose() {
      lock (LifecycleGate) {
        if (_disposed) return;
        if (_ownsPatches) {
          if (Session != null && Session.Phase != "Ready" && Session.Phase != "Faulted") throw new InvalidOperationException("Finish native jobs before disposing fluid transport");
          RemoveOwnPatches(); _ownsPatches = false;
        }
        if (ReferenceEquals(_active, this)) _active = null;
        _disposed = true; SessionCreated = null; ResolveSource = null; ResolveAddition = null;
      }
    }
    private readonly struct SubstepJob : IParallelizerSingleTask {
      private readonly NativeTransportHooks _owner; private readonly object _parameters;
      internal SubstepJob(NativeTransportHooks owner, object parameters) { _owner = owner; _parameters = parameters; }
      public void Run() { try { _owner.RunSubstep(_parameters); } catch { _owner.Session?.AbortTick(); throw; } }
    }
    private readonly struct ChangesJob : IParallelizerSingleTask {
      private readonly NativeTransportHooks _owner; private readonly object _parameters;
      internal ChangesJob(NativeTransportHooks owner, object parameters) { _owner = owner; _parameters = parameters; }
      public void Run() { try { _owner.RunChanges(_parameters); } catch { _owner.Session?.AbortTick(); throw; } }
    }
  }
}
