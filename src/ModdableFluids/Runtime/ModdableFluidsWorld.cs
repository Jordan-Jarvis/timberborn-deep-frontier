using System;
using System.Collections.Generic;
using System.Reflection;
using System.Threading;
using Timberborn.WaterSystem;
using ModdableFluids;
using ModdableFluids.Native.Prototype;
using ModdableFluids.Sources.Prototype;
using ModdableFluids.Transport.Prototype;
using ModdableFluids.World.Prototype;
using UnityEngine;

namespace ModdableFluids.Runtime.Prototype {
  /// <summary>
  /// The scene's <see cref="IFluidWorld"/>: sampling from the last published completed tick, additions as native
  /// clean-water changes that the change stage resolves to the requested fluid, and the source composition
  /// override applied to native sources. Additions and extractions are main-thread requests, like the native water
  /// service; extraction results are delivered by the scene owner on the main thread.
  /// </summary>
  public sealed class ModdableFluidsWorld : IFluidWorld, IFluidExtraction {
    private readonly IWaterService _water;
    private readonly int _mainThread;
    private readonly PropertyInfo _changeCoordinates;
    private readonly FluidSourceTypeDefinition _nativeSource;
    public FluidWorldState State { get; }
    public FluidExtractionQueue Extractions { get; }
    public FluidRegistry Registry => State.Registry;
    public int CompletedTicks => State.CompletedTicks;

    internal ModdableFluidsWorld(FluidRegistry registry, int stride, int height, IWaterService water, int mainThread) {
      State = new FluidWorldState(registry, stride);
      Extractions = new FluidExtractionQueue(registry, stride - 2, height);
      _water = water; _mainThread = mainThread;
      var change = typeof(IWaterService).Assembly.GetType("Timberborn.WaterSystem.WaterChange")
        ?? throw new InvalidOperationException("Native Timberborn.WaterSystem.WaterChange is missing (expected Timberborn 1.1.2.8)");
      _changeCoordinates = change.GetProperty("Coordinates", BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
      if (_changeCoordinates == null || _changeCoordinates.PropertyType != typeof(Vector3Int)) throw new MissingMemberException(change.FullName, "Coordinates : Vector3Int");
      if (!registry.TryGetSourceType(NativeFluidSourceTypes.WaterSource, out _nativeSource)) throw new InvalidOperationException("The native water source type is not registered");
    }

    public bool HasState => State.HasSnapshot;
    public bool TrySample(int x, int y, int z, out FluidColumnSample sample) => State.TrySample(x, y, z, out sample);
    public IReadOnlyList<FluidColumnSample> SampleCell(int x, int y) => State.SampleCell(x, y);
    public double TotalVolume(FluidHandle fluid) => State.TotalVolume(fluid);
    public void SetSourceComposition(string ownerId, IReadOnlyDictionary<string, double> composition) => State.SetSourceComposition(ownerId, composition);

    public void QueueAddition(int x, int y, int z, FluidHandle fluid, double volume) {
      if (Thread.CurrentThread.ManagedThreadId != _mainThread) throw new InvalidOperationException("Fluid additions are requested on the main thread, like native water changes");
      if (!State.TrySample(x, y, z, out _)) throw new ArgumentException("No open column at (" + x + ", " + y + ", " + z + ") for a fluid addition");
      State.RecordAddition(x, y, z, fluid, volume);
      _water.AddCleanWater(new Vector3Int(x, y, z), (float)volume);
    }

    public IFluidExtractionRequest RequestExtraction(string requesterId, int x, int y, int z, FluidHandle fluid, double volume, double minimumShare,
        Action<IFluidExtractionRequest> resolved) {
      if (Thread.CurrentThread.ManagedThreadId != _mainThread) throw new InvalidOperationException("Fluid extractions are requested on the main thread, like native water changes");
      return Extractions.Request(requesterId, x, y, z, fluid, volume, minimumShare, resolved);
    }

    /// <summary>The change stage's addition resolver: a recorded fluid, or the native water/badwater split.</summary>
    internal FluidVolumes ResolveAddition(object change, int nativeIndex, double volume, double badShare) {
      var c = (Vector3Int)_changeCoordinates.GetValue(change);
      if (badShare == 0 && State.TryResolveAddition(c.x, c.y, c.z, volume, out var mixture)) return mixture;
      return Native(volume, badShare);
    }

    /// <summary>The source stage's resolver: native contamination plus the active composition override.</summary>
    internal FluidVolumes ResolveSource(object source, int nativeIndex, double volume) =>
      FluidSourceEmission.Compose(Registry, _nativeSource, volume, ((IWaterSource)source).Contamination, State.ActiveSourceComposition);

    private FluidVolumes Native(double volume, double badShare) {
      var values = new double[Registry.Count];
      values[FluidRegistry.BadwaterIndex] = volume * badShare; values[FluidRegistry.WaterIndex] = volume - values[FluidRegistry.BadwaterIndex];
      return new FluidVolumes(values);
    }
  }
}
