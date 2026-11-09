using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using Timberborn.BlueprintSystem;
using Timberborn.Common;
using Timberborn.MapIndexSystem;
using Timberborn.SoilMoistureSystem;
using Timberborn.TickSystem;
using Timberborn.WaterSystem;
using ModdableFluids;
using ModdableFluids.Transport.Prototype;
using ModdableFluids.World.Prototype;

namespace ModdableFluids.Runtime.Prototype {
  /// <summary>
  /// Moddable Fluids' owner of the native soil-moisture input (capability <c>ModdableFluids.Policies.Irrigation</c>),
  /// the generalisation of Deep Frontier's RadiationSoilPatches. A Harmony prefix on
  /// <c>SoilMoistureSimulationTaskStarter.StartTask</c> replaces its <c>waterColumns</c> argument, for that call only, with
  /// a copy of the thread-safe water map in which each column's contamination is raised by the fluids that block
  /// moisture (<see cref="FluidMoistureShadow"/>). The native caller (<c>SoilMoistureSimulator.StartParallelTick</c>)
  /// passes the map's <c>WaterColumns</c> property value, a local, by <c>in</c>; the prefix checks on every call that the
  /// argument is the thread-safe map's own array. The composition comes from the fluid tick published before this
  /// parallel tick started (captured at the singleton tick on the main thread). Installed per scene by the scene owner,
  /// and only when a registered fluid blocks moisture; removed at scene unload after the native workers finished.
  /// Another Harmony owner on the same method is refused before anything is installed.
  /// </summary>
  public sealed class FluidMoistureInput : ITickableSingleton {
    public const string OwnerId = "ModdableFluids.SoilMoisture";
    private const string ContaminationField = "<Contamination>k__BackingField";
    private static readonly object Gate = new object();
    private static FluidMoistureInput _active;
    private readonly IThreadSafeWaterMap _waterMap;
    private readonly ISpecService _specs;
    private readonly MapIndexService _index;
    private readonly Harmony _harmony = new Harmony(OwnerId);
    private readonly List<KeyValuePair<int, double>> _additions = new List<KeyValuePair<int, double>>();
    private MethodInfo _target;
    private FieldInfo _contamination;
    private FluidMoistureShadow _shadow;
    private FluidWorldState _state;
    private FluidColumnGeometry[] _layout;
    private FluidVolumes[] _mixtures;
    private ReadOnlyWaterColumn[] _buffer = new ReadOnlyWaterColumn[0];
    public static bool HasActiveOwner { get { lock (Gate) return _active != null; } }
    /// <summary>Whether the prefix is installed (a registered fluid blocks moisture).</summary>
    public bool Installed { get; private set; }
    /// <summary>Calls whose water columns were replaced, and the columns raised in the last one.</summary>
    public int Substitutions { get; private set; }
    public int LastRaisedColumns { get; private set; }
    public double MaximumWaterContamination { get; private set; }

    public FluidMoistureInput(IThreadSafeWaterMap waterMap, ISpecService specs, MapIndexService index) { _waterMap = waterMap; _specs = specs; _index = index; }

    /// <summary>Every native member the moisture input uses; empty when the installed game matches 1.1.2.8.</summary>
    public static IReadOnlyList<string> CheckContract() => Inspect(out _, out _, out _);

    private static IReadOnlyList<string> Inspect(out MethodInfo target, out FieldInfo contamination, out Type spec) {
      const BindingFlags members = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
      var problems = new List<string>();
      var assembly = typeof(ISoilMoistureService).Assembly;
      var starter = assembly.GetType("Timberborn.SoilMoistureSystem.SoilMoistureSimulationTaskStarter");
      target = starter?.GetMethods(members).SingleOrDefault(m => m.Name == "StartTask");
      var columns = typeof(ReadOnlyArray<ReadOnlyWaterColumn>);
      var parameter = target?.GetParameters().SingleOrDefault(p => p.Name == "waterColumns");
      if (target == null || target.ReturnType != typeof(void) || parameter == null || parameter.ParameterType != columns.MakeByRefType() || !parameter.IsIn)
        problems.Add("SoilMoistureSimulationTaskStarter.StartTask(..., in ReadOnlyArray<ReadOnlyWaterColumn> waterColumns, ...) : void");
      var simulator = assembly.GetType("Timberborn.SoilMoistureSystem.SoilMoistureSimulator");
      if (simulator?.GetMethod("StartParallelTick", members, null, Type.EmptyTypes, null) == null) problems.Add("SoilMoistureSimulator.StartParallelTick()");
      spec = assembly.GetType("Timberborn.SoilMoistureSystem.SoilMoistureSimulatorSpec");
      if (spec?.GetProperty("MaximumWaterContamination", members)?.PropertyType != typeof(float)) problems.Add("SoilMoistureSimulatorSpec.MaximumWaterContamination : float");
      contamination = typeof(ReadOnlyWaterColumn).GetField(ContaminationField, members);
      if (contamination == null || contamination.FieldType != typeof(float)) problems.Add("ReadOnlyWaterColumn.Contamination's backing field " + ContaminationField + " : float");
      foreach (var property in new[] { "Floor", "Ceiling", "Contamination" })
        if (typeof(ReadOnlyWaterColumn).GetProperty(property) == null) problems.Add("ReadOnlyWaterColumn." + property);
      if (typeof(IThreadSafeWaterMap).GetProperty("WaterColumns")?.PropertyType != columns) problems.Add("IThreadSafeWaterMap.WaterColumns : ReadOnlyArray<ReadOnlyWaterColumn>");
      if (typeof(IThreadSafeWaterMap).GetProperty("ColumnCounts")?.PropertyType != typeof(ReadOnlyArray<byte>)) problems.Add("IThreadSafeWaterMap.ColumnCounts : ReadOnlyArray<byte>");
      return problems;
    }

    /// <summary>
    /// Main thread, scene PostLoad, before anything is installed: checks the native contract, reads the native maximum
    /// water contamination and decides whether any registered fluid blocks moisture. Returns other mods' patches on the
    /// native input that would conflict (empty when nothing will be installed).
    /// </summary>
    public IReadOnlyList<string> Prepare(FluidRegistry registry) {
      var problems = Inspect(out _target, out _contamination, out var spec);
      if (problems.Count > 0)
        throw new InvalidOperationException("Moddable Fluids cannot own this game's soil-moisture input (expected Timberborn 1.1.2.8). Changed native contract:\n- " + string.Join("\n- ", problems));
      var getSpec = typeof(ISpecService).GetMethods().Single(m => m.Name == "GetSingleSpec" && m.IsGenericMethodDefinition && m.GetParameters().Length == 0);
      object values = getSpec.MakeGenericMethod(spec).Invoke(_specs, null);
      MaximumWaterContamination = (float)spec.GetProperty("MaximumWaterContamination", BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic).GetValue(values);
      _shadow = new FluidMoistureShadow(registry, MaximumWaterContamination, _index.Stride, _index.VerticalStride);
      if (!_shadow.HasBlockingFluids) return Array.Empty<string>();
      var owners = Harmony.GetPatchInfo(_target)?.Owners.Where(owner => owner != OwnerId).Distinct().ToArray() ?? new string[0];
      return owners.Length == 0 ? (IReadOnlyList<string>)Array.Empty<string>()
        : new[] { "SoilMoistureSimulationTaskStarter.StartTask is patched by " + string.Join(", ", owners) };
    }

    /// <summary>Main thread, after the transport attached: installs the prefix when a fluid blocks moisture.</summary>
    public void Install(FluidWorldState state) {
      if (_shadow == null) throw new InvalidOperationException("Prepare the moisture input before installing it");
      _state = state ?? throw new ArgumentNullException(nameof(state));
      if (!_shadow.HasBlockingFluids) return;
      lock (Gate) {
        if (_active != null) throw new InvalidOperationException("Another scene still owns the soil-moisture input");
        var owners = Harmony.GetPatchInfo(_target)?.Owners.Where(owner => owner != OwnerId).Distinct().ToArray();
        if (owners != null && owners.Length > 0) throw new InvalidOperationException("SoilMoistureSimulationTaskStarter.StartTask is patched by " + string.Join(", ", owners));
        _active = this;
        try { _harmony.Patch(_target, prefix: new HarmonyMethod(typeof(FluidMoistureInput), nameof(Prefix))); Installed = true; }
        catch { _harmony.Unpatch(_target, HarmonyPatchType.All, OwnerId); _active = null; throw; }
      }
    }

    /// <summary>Scene unload, after the native workers finished: removes the prefix. Safe when nothing was installed.</summary>
    public void Uninstall() {
      lock (Gate) {
        if (Installed) { _harmony.Unpatch(_target, HarmonyPatchType.All, OwnerId); Installed = false; }
        if (ReferenceEquals(_active, this)) _active = null;
      }
      _state = null; _layout = null; _mixtures = null;
    }

    public bool HasOwnedPatch => _target != null && Harmony.GetPatchInfo(_target)?.Owners.Contains(OwnerId) == true;

    // Main thread, singleton tick: the last completed fluid tick, before this tick's parallel work is scheduled.
    public void Tick() {
      if (_state != null && _state.TryGetPublished(out var layout, out var mixtures, out _)) { _layout = layout; _mixtures = mixtures; }
    }

    private static void Prefix(ref ReadOnlyArray<ReadOnlyWaterColumn> waterColumns) {
      FluidMoistureInput active;
      lock (Gate) active = _active;
      active?.Substitute(ref waterColumns);
    }

    // Main thread, SoilMoistureSimulator.StartParallelTick.
    internal void Substitute(ref ReadOnlyArray<ReadOnlyWaterColumn> waterColumns) {
      if (_layout == null) return;
      var map = _waterMap.WaterColumns;
      if (waterColumns.AsSpan != map.AsSpan)
        throw new InvalidOperationException("Moddable Fluids: native soil moisture no longer reads the thread-safe water map (expected Timberborn 1.1.2.8)");
      var counts = _waterMap.ColumnCounts;
      void Read(int nativeIndex, out int floor, out int ceiling) { ref readonly var column = ref map[nativeIndex]; floor = column.Floor; ceiling = column.Ceiling; }
      LastRaisedColumns = _shadow.Compute(_layout, _mixtures, cell => counts[cell], Read, _additions);
      if (LastRaisedColumns == 0) return;
      var span = waterColumns.AsSpan;
      if (_buffer.Length != span.Length) _buffer = new ReadOnlyWaterColumn[span.Length];
      span.CopyTo(_buffer);
      foreach (var addition in _additions) {
        object boxed = _buffer[addition.Key];
        _contamination.SetValue(boxed, (float)(_buffer[addition.Key].Contamination + addition.Value));
        _buffer[addition.Key] = (ReadOnlyWaterColumn)boxed;
      }
      waterColumns = new ReadOnlyArray<ReadOnlyWaterColumn>(_buffer);
      Substitutions++;
    }
  }
}
