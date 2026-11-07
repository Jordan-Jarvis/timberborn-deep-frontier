using System.Collections;
using System.Collections.Immutable;
using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;
using FluidsApi.Transport.Prototype;
using FluidsApi.Native.Prototype;

// Invokes the installed, unmodified game tasks by reflection. The fixture supplies
// arrays and explicit parameters; it contains no copied implementation of native tasks.
internal sealed class NativeWaterFixture : IDisposable {
  private const BindingFlags Members = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
  private readonly Assembly _water;
  private readonly Assembly _common;
  private readonly JsonElement _spec;
  private readonly Func<AssemblyLoadContext, AssemblyName, Assembly?> _resolver;
  private readonly object _mapIndex, _flowLimits, _retriever, _depthSetter, _overflowCalculator;
  private readonly Array _columns, _outflows, _baseFlows, _directed, _baseDiffusions, _targetedDiffusions;
  private readonly byte[] _counts, _diffusionCounts;
  private readonly float[] _buffer, _heightLimits, _inflowLimits, _evaporationModifiers;
  private readonly int[] _limitedDirections;
  private readonly Dictionary<int, int> _slots = new();
  private object? _geometrySimulator;
  public const int Width = 3, Height = 3, Stride = Width + 2, VerticalStride = Stride * (Height + 2);
  public const float DeltaTime = .25f;
  public List<int> Indices { get; } = new();
  public int LastDiffusionPairCount { get; private set; }

  public NativeWaterFixture(string managed, string specification) {
    _resolver = (context, name) => {
      string path = Path.Combine(managed, name.Name + ".dll");
      return File.Exists(path) ? context.LoadFromAssemblyPath(path) : null;
    };
    AssemblyLoadContext.Default.Resolving += _resolver;
    _water = Assembly.LoadFrom(Path.Combine(managed, "Timberborn.WaterSystem.dll"));
    _common = Assembly.LoadFrom(Path.Combine(managed, "Timberborn.Common.dll"));
    _spec = JsonDocument.Parse(File.ReadAllText(specification)).RootElement.GetProperty("WaterSimulatorSpec").Clone();
    var mapType = Assembly.LoadFrom(Path.Combine(managed, "Timberborn.MapIndexSystem.dll")).GetType("Timberborn.MapIndexSystem.MapIndexService", true)!;
    _mapIndex = Activator.CreateInstance(mapType, new object?[] { null })!;
    mapType.GetProperty("Stride")!.SetValue(_mapIndex, Stride);
    mapType.GetProperty("VerticalStride")!.SetValue(_mapIndex, VerticalStride);
    _flowLimits = New("FlowLimitCalculator", _mapIndex);
    _retriever = New("WaterFlowRetriever");
    var overflow = New("WaterOverflowCalculator", _mapIndex, null);
    _overflowCalculator = overflow;
    Set(overflow, "_maxPressure", 16f);
    Set(overflow, "_overflowPressureFactorInverted", 1 / Spec("OverflowPressureFactor"));
    _depthSetter = New("WaterDepthSetter", overflow);
    int length = VerticalStride * 3;
    _columns = Array.CreateInstance(Type("WaterColumn"), length);
    _outflows = Array.CreateInstance(Type("ColumnOutflows"), length);
    _baseFlows = Array.CreateInstance(Type("WaterFlow"), VerticalStride);
    _directed = Lists("DirectedFlow", VerticalStride);
    _targetedDiffusions = Lists("TargetedDiffusion", VerticalStride);
    _baseDiffusions = Array.CreateInstance(Type("Diffusions"), VerticalStride);
    _counts = new byte[VerticalStride]; _diffusionCounts = new byte[length];
    _buffer = new float[length]; _heightLimits = Enumerable.Repeat(-1f, VerticalStride * 16).ToArray();
    _inflowLimits = Enumerable.Repeat(float.MaxValue, VerticalStride * 16).ToArray();
    _limitedDirections = new int[VerticalStride * 16]; _evaporationModifiers = new float[length];
  }

  private float Spec(string name) => _spec.GetProperty(name).GetSingle();
  private Type Type(string name) => _water.GetType("Timberborn.WaterSystem." + name, true)!;
  private object New(string name, params object?[] arguments) => Activator.CreateInstance(Type(name), Members, null, arguments, null)!;
  private static void Set(object target, string name, object value) => target.GetType().GetField(name, Members)!.SetValue(target, value);
  private static T Get<T>(object target, string name) => (T)target.GetType().GetField(name, Members)!.GetValue(target)!;
  private Array Lists(string element, int length) {
    var listType = typeof(List<>).MakeGenericType(Type(element));
    var result = Array.CreateInstance(listType, length);
    for (int i = 0; i < length; i++) result.SetValue(Activator.CreateInstance(listType), i);
    return result;
  }
  private object ReadOnly(Array array) => Activator.CreateInstance(
    _common.GetType("Timberborn.Common.ReadOnlyArray`1", true)!.MakeGenericType(array.GetType().GetElementType()!), new object[] { array })!;
  private object ReadOnlyList(IList list) => Activator.CreateInstance(
    _common.GetType("Timberborn.Common.ReadOnlyList`1", true)!.MakeGenericType(list.GetType().GetGenericArguments()[0]), Members, null, new object[] { list }, null)!;
  private static void RunRows(object task) {
    var run = task.GetType().GetMethod("Run", Members, null, new[] { typeof(int) }, null)!;
    for (int y = 0; y < Height; y++) run.Invoke(task, new object[] { y });
  }

  public int AddColumn(int x, int y, float depth, int floor = 0, int ceiling = 12, int ordinal = 0, float overflow = 0) {
    int index = (y + 1) * Stride + x + 1;
    if (_counts[index] != ordinal) throw new ArgumentException("Add lower columns first");
    _counts[index]++;
    int index3D = index + ordinal * VerticalStride;
    var column = New("WaterColumn", floor, ceiling);
    Set(column, "WaterDepth", depth); Set(column, "Overflow", overflow);
    _columns.SetValue(column, index3D);
    _slots.Add(index3D, Indices.Count); Indices.Add(index3D);
    return Indices.Count - 1;
  }

  public double PhysicalVolume(int slot) {
    object column = _columns.GetValue(Indices[slot])!;
    return (double)Get<float>(column, "WaterDepth") + Get<float>(column, "Overflow");
  }
  public NativeWaterArrayAdapter CreateAdapter() => new(_columns, _counts, _baseFlows, _directed,
    Width, Height, Stride, VerticalStride, _depthSetter, _overflowCalculator);
  public void ClearRawFlows() {
    Array.Clear(_baseFlows);
    foreach (IList flows in _directed) flows.Clear();
  }
  public void SetColumnGeometry(int slot, byte floor, byte ceiling, float depth, float overflow) {
    object column = _columns.GetValue(Indices[slot])!;
    Set(column, "Floor", floor); Set(column, "Ceiling", ceiling); Set(column, "WaterDepth", depth); Set(column, "Overflow", overflow);
    _columns.SetValue(column, Indices[slot]);
  }
  public void ApplyQueuedNativeObstacle(string operation, int slot, int height) {
    if (_geometrySimulator == null) {
      var tick = Assembly.LoadFrom(Path.Combine(Path.GetDirectoryName(_water.Location)!, "Timberborn.TickSystem.dll"));
      var lifecycleInterface = tick.GetType("Timberborn.TickSystem.ITickableSingletonService", true)!;
      var lifecycle = DispatchProxy.Create(lifecycleInterface, typeof(FixtureWaterSource));
      ((FixtureWaterSource)lifecycle).Values.Add("get_ParalleTicklIsFinished", false);
      var arraysType = tick.GetType("Timberborn.TickSystem.TickOnlyArrayService", true)!;
      object arrays = Activator.CreateInstance(arraysType, lifecycle)!;
      // Use the native load phase, which explicitly permits geometry initialization.
      // Do not disable TickOnlyArray's guards or fabricate a singleton Tick flag.
      arraysType.GetMethod("Load")!.Invoke(arrays, null);
      object Wrap(Array data) {
        var type = tick.GetType("Timberborn.TickSystem.TickOnlyArray`1", true)!.MakeGenericType(data.GetType().GetElementType()!);
        object wrapper = Activator.CreateInstance(type, data.Length, arrays)!;
        Set(wrapper, "_array", data); return wrapper;
      }
      var constructor = Type("WaterSimulator").GetConstructors(Members).Single();
      object?[] arguments = constructor.GetParameters().Select(parameter => parameter.Name switch {
        "mapIndexService" => _mapIndex,
        "mutableWaterColumnRetriever" => New("MutableWaterColumnRetriever"),
        "tickOnlyArrayService" => arrays,
        _ => null
      }).ToArray();
      _geometrySimulator = constructor.Invoke(arguments);
      Set(_geometrySimulator, "_stride", Stride); Set(_geometrySimulator, "_verticalStride", VerticalStride);
      Set(_geometrySimulator, "_maxColumnHeight", 16);
      Set(_geometrySimulator, "_columnCounts", Wrap(_counts)); Set(_geometrySimulator, "_waterColumns", Wrap(_columns));
      Set(_geometrySimulator, "_outflows", Wrap(_outflows)); Set(_geometrySimulator, "_horizontalObstacles", Wrap(new byte[VerticalStride * 16]));
      Type("WaterSimulator").GetProperty("MaxColumnCount")!.SetValue(_geometrySimulator, 3);
    }
    object point = Coordinates(slot);
    int index = Indices[slot] % VerticalStride;
    point = Activator.CreateInstance(point.GetType(), index % Stride - 1, index / Stride - 1, height)!;
    if (operation is not ("AddFullObstacle" or "RemoveFullObstacle" or "AddHorizontalObstacle" or "RemoveHorizontalObstacle"))
      throw new ArgumentException("Unknown fixture obstacle operation");
    Type("WaterSimulator").GetMethod(operation, Members)!.Invoke(_geometrySimulator, new[] { point });
    Type("WaterSimulator").GetMethod("ProcessModifications", Members)!.Invoke(_geometrySimulator, null);
    Indices.Clear(); _slots.Clear();
    for (int y = 1; y <= Height; y++) for (int x = 1; x <= Width; x++) {
      int cell = y * Stride + x;
      for (int ordinal = 0; ordinal < _counts[cell]; ordinal++) {
        int native = cell + ordinal * VerticalStride;
        object column = _columns.GetValue(native)!;
        if (Get<byte>(column, "Floor") == Get<byte>(column, "Ceiling")) continue;
        _slots.Add(native, Indices.Count); Indices.Add(native);
      }
    }
  }
  public void RunAdapterSubstep(NativeFluidTransportSession session, Action generateFlows, double[] evaporation, bool diffuse) {
    var before = Indices.Select(session.Sample).ToArray();
    var ordinal = Enumerable.Range(0, session.ColumnCount).ToDictionary(i => session.GetGeometry(i).NativeIndex);
    session.RunSubstep(generateFlows, () => {
      var actual = UpdateNativeDepths(evaporation);
      return Enumerable.Range(0, session.ColumnCount).Select(i => actual[_slots[session.GetGeometry(i).NativeIndex]]).ToArray();
    }, () => {
      if (!diffuse) return Array.Empty<FluidDiffusionLink>();
      RunIndependentNativeContamination(before);
      return ReadNativeDiffusionLinks().Select(link => new FluidDiffusionLink(ordinal[Indices[link.First]], ordinal[Indices[link.Second]])).ToArray();
    }, DeltaTime, diffuse ? DiffusionFraction : 0);
  }

  public void SetContamination(int slot, double share) {
    object column = _columns.GetValue(Indices[slot])!;
    Set(column, "Contamination", (float)share); _columns.SetValue(column, Indices[slot]);
  }
  public double Contamination(int slot) => Get<float>(_columns.GetValue(Indices[slot])!, "Contamination");
  private object Coordinates(int slot) {
    int index = Indices[slot] % VerticalStride;
    var vector = _mapIndex.GetType().Assembly.GetReferencedAssemblies().Single(a => a.Name == "UnityEngine.CoreModule");
    var type = Assembly.Load(vector).GetType("UnityEngine.Vector3Int", true)!;
    int floor = Get<byte>(_columns.GetValue(Indices[slot])!, "Floor");
    return Activator.CreateInstance(type, index % Stride - 1, index / Stride - 1, floor)!;
  }

  public void ApplyNativeChange(int slot, float change, float badShare) {
    var list = (IList)Activator.CreateInstance(typeof(List<>).MakeGenericType(Type("WaterChange")))!;
    object cell = Coordinates(slot);
    list.Add(New("WaterChange", cell, change, badShare));
    var removed = Activator.CreateInstance(typeof(Dictionary<,>).MakeGenericType(cell.GetType(), Type("WaterAmountChange")))!;
    var task = New("UpdateWaterChangesTask", _mapIndex, _depthSetter, New("MutableWaterColumnRetriever"), removed,
      _columns, ReadOnly(_counts), ReadOnlyList(list), VerticalStride, Spec("OverflowPressureFactor"), Spec("MaxWaterContamination"));
    task.GetType().GetMethod("Run", Members, null, System.Type.EmptyTypes, null)!.Invoke(task, null);
  }

  public void ApplyNativeSource(int slot, float strength, float badShare) {
    object cell = Coordinates(slot);
    var coordinates = Array.CreateInstance(cell.GetType(), 1); coordinates.SetValue(cell, 0);
    var immutableCreate = typeof(ImmutableArray).GetMethods().Single(m => m.Name == "Create" && m.IsGenericMethodDefinition &&
      m.GetParameters().Length == 1 && m.GetParameters()[0].ParameterType.IsArray);
    object coordinateArray = immutableCreate.MakeGenericMethod(cell.GetType()).Invoke(null, new object[] { coordinates })!;
    var source = DispatchProxy.Create(Type("IWaterSource"), typeof(FixtureWaterSource));
    ((FixtureWaterSource)source).Values.Add("get_Coordinates", coordinateArray);
    ((FixtureWaterSource)source).Values.Add("get_CurrentStrength", strength);
    ((FixtureWaterSource)source).Values.Add("get_Contamination", badShare);
    var list = (IList)Activator.CreateInstance(typeof(List<>).MakeGenericType(Type("ThreadSafeWaterSource")))!;
    list.Add(New("ThreadSafeWaterSource", source));
    var task = New("UpdateWaterSourcesTask", _mapIndex, _depthSetter, New("MutableWaterColumnRetriever"), _columns,
      ReadOnly(_counts), ReadOnlyList(list), VerticalStride, DeltaTime, Spec("OverflowPressureFactor"), Spec("MaxWaterContamination"));
    task.GetType().GetMethod("Run", Members, null, System.Type.EmptyTypes, null)!.Invoke(task, null);
  }

  public double SummaryNetVolume(int source, int destination) {
    double Rate(int from, int to) {
      double total = 0;
      object summary = _outflows.GetValue(Indices[from])!;
      foreach (string field in new[] { "BottomFlow", "LeftFlow", "TopFlow", "RightFlow" }) {
        object flow = summary.GetType().GetField(field)!.GetValue(summary)!;
        if (Get<int>(flow, "Index3D") == Indices[to]) total += Get<float>(flow, "Flow");
      }
      if (summary.GetType().GetField("Outflows")!.GetValue(summary) is IEnumerable extra)
        foreach (object flow in extra) if (Get<int>(flow, "Index3D") == Indices[to]) total += Get<float>(flow, "Flow");
      return total;
    }
    return (Rate(source, destination) - Rate(destination, source)) * DeltaTime;
  }

  // Prescribed, representative raw flow rates; generated cases below use native OutflowsUpdateTask.
  public void SetRawFlow(int source, int destination, float volume) => SetRawRate(source, destination, volume / DeltaTime);
  private void SetRawRate(int source, int destination, float rate) {
    int from = Indices[source], to = Indices[destination], offset = to % VerticalStride - from % VerticalStride;
    if (from < VerticalStride && to < VerticalStride) {
      string direction = offset switch { -Stride => "Bottom", -1 => "Left", Stride => "Top", 1 => "Right", _ => throw new ArgumentException("Non-neighbor raw flow") };
      object flows = _baseFlows.GetValue(from)!;
      Set(flows, direction, Get<float>(flows, direction) + rate); _baseFlows.SetValue(flows, from);
    } else {
      if (Math.Abs(offset) != 1 && Math.Abs(offset) != Stride) throw new ArgumentException("Non-neighbor raw flow");
      ((IList)_directed.GetValue(from % VerticalStride)!).Add(New("DirectedFlow", rate, to, from));
    }
  }

  public void GenerateNativeFlows() {
    var task = New("OutflowsUpdateTask", _flowLimits, _retriever, _directed, _baseFlows, ReadOnly(_counts), ReadOnly(_columns),
      ReadOnly(_limitedDirections), ReadOnly(_heightLimits), ReadOnly(_inflowLimits), ReadOnly(_outflows), Width, Stride, VerticalStride,
      DeltaTime, Spec("OverflowPressureFactor"), Spec("MaxHardDamDecrease"), Spec("HardDamSmoothingFactor"), Spec("MinHardDamSmoothing"),
      Spec("MaxHardDamSmoothing"), Spec("HardDamOffset"), Spec("SoftDamOffset"), Spec("WaterSpillThreshold"), Spec("WaterFlowFactor") * DeltaTime);
    RunRows(task);
  }

  public FluidTransfer[] ReadRawTransfers() {
    var result = new List<FluidTransfer>();
    foreach (int from in Indices) {
      if (from < VerticalStride) {
        object flows = _baseFlows.GetValue(from)!;
        foreach (var (field, offset) in new[] { ("Bottom", -Stride), ("Left", -1), ("Top", Stride), ("Right", 1) }) {
          float rate = Get<float>(flows, field);
          if (rate > 0) result.Add(new FluidTransfer(_slots[from], _slots[from + offset], (double)rate * DeltaTime));
        }
      }
      foreach (object flow in (IEnumerable)_directed.GetValue(from % VerticalStride)!) {
        if (Get<int>(flow, "OriginIndex3D") != from) continue;
        result.Add(new FluidTransfer(_slots[from], _slots[Get<int>(flow, "TargetIndex3D")], (double)Get<float>(flow, "Flow") * DeltaTime));
      }
    }
    return result.ToArray();
  }

  public double[] UpdateNativeDepths(double[] requestedEvaporation) {
    var evaporation = new double[Indices.Count];
    for (int i = 0; i < Indices.Count; i++) {
      float speed = Get<float>(_columns.GetValue(Indices[i])!, "WaterDepth") < Spec("FastEvaporationDepthThreshold") ? Spec("FastEvaporationSpeed") : Spec("NormalEvaporationSpeed");
      float modifier = (float)(requestedEvaporation[i] / (speed * DeltaTime));
      _evaporationModifiers[Indices[i]] = modifier;
      evaporation[i] = (double)(speed * modifier) * DeltaTime;
    }
    var task = New("WaterParametersUpdateTask", _depthSetter, _columns, _outflows, ReadOnly(_counts),
      ImmutableArray.Create(-Stride, -1, Stride, 1), ReadOnly(_baseFlows), ReadOnly(_evaporationModifiers), ReadOnly(_directed),
      Width, Stride, VerticalStride, DeltaTime, Spec("OutflowBalancingScaler"), Spec("FastEvaporationDepthThreshold"), Spec("FastEvaporationSpeed"), Spec("NormalEvaporationSpeed"));
    RunRows(task);
    return evaporation;
  }

  public double[][] RunIndependentNativeContamination(FluidVolumes[] initial) {
    var result = initial.Select(c => new double[c.ComponentCount]).ToArray();
    for (int c = 0; c < initial[0].ComponentCount; c++) {
      Array.Clear(_buffer); Array.Clear(_diffusionCounts); Array.Clear(_baseDiffusions);
      for (int i = 0; i < Indices.Count; i++) {
        object column = _columns.GetValue(Indices[i])!;
        Set(column, "Contamination", (float)initial[i].GetShare(c)); _columns.SetValue(column, Indices[i]);
      }
      var simulate = New("SimulateContaminationTask", _flowLimits, _retriever, _buffer, _baseDiffusions, _diffusionCounts, _targetedDiffusions,
        ReadOnly(_counts), ReadOnly(_columns), ReadOnly(_outflows), ReadOnly(_limitedDirections), ReadOnly(_heightLimits), Width, Stride, VerticalStride,
        DeltaTime, Spec("OverflowPressureFactor"), Spec("MaxWaterContamination"), _spec.GetProperty("DiffusionOutflowLimit").GetDouble(), _spec.GetProperty("DiffusionDepthLimit").GetDouble());
      RunRows(simulate);
      var update = New("UpdateContaminationTask", _columns, ReadOnly(_counts), ReadOnly(_buffer), ReadOnly(_baseDiffusions), ReadOnly(_diffusionCounts),
        ReadOnly(_targetedDiffusions), Width, Stride, VerticalStride, DeltaTime, Spec("MaxWaterContamination"), Spec("DiffusionRate"));
      RunRows(update);
      for (int i = 0; i < Indices.Count; i++) result[i][c] = Get<float>(_columns.GetValue(Indices[i])!, "Contamination");
    }
    return result;
  }

  public FluidDiffusionLink[] ReadNativeDiffusionLinks() {
    var pairs = new HashSet<(int, int)>();
    void Add(int from, int to) {
      int a = _slots[from], b = _slots[to];
      pairs.Add((Math.Min(a, b), Math.Max(a, b)));
    }
    foreach (int index in Indices) {
      if (index < VerticalStride) {
        object flags = _baseDiffusions.GetValue(index)!;
        foreach (var (field, offset) in new[] { ("Bottom", -Stride), ("Left", -1), ("Top", Stride), ("Right", 1) })
          if (Get<bool>(flags, field)) Add(index, index + offset);
      }
      foreach (object pair in (IEnumerable)_targetedDiffusions.GetValue(index % VerticalStride)!)
        if (Get<int>(pair, "OriginIndex3D") == index) Add(index, Get<int>(pair, "TargetIndex3D"));
    }
    LastDiffusionPairCount = pairs.Count;
    return pairs.OrderBy(p => p.Item1).ThenBy(p => p.Item2).Select(p => new FluidDiffusionLink(p.Item1, p.Item2)).ToArray();
  }
  public double DiffusionFraction => Spec("DiffusionRate") * (double)DeltaTime;
  public void Dispose() => AssemblyLoadContext.Default.Resolving -= _resolver;
}

// A legitimate fixture implementation of native IWaterSource, generated without a
// compiled game reference. Physics still runs inside the installed source task.
public class FixtureWaterSource : DispatchProxy {
  public Dictionary<string, object> Values { get; } = new();
  protected override object? Invoke(MethodInfo? targetMethod, object?[]? args) =>
    Values.TryGetValue(targetMethod!.Name, out var value) ? value : throw new NotSupportedException(targetMethod.Name);
}
