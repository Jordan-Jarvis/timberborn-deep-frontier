#if DEEP_FRONTIER_MODDABLE_FLUIDS
using System;
using System.Linq;
using Bindito.Core;
using DeepFrontier.Scripts.Radiation;
using ModdableFluids;
using Timberborn.MapIndexSystem;
using Timberborn.ModManagerScene;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>Registers Deep Frontier's radioactive water with Moddable Fluids at mod start (flagged build only).</summary>
  internal sealed class DeepFrontierFluidsModStarter : IModStarter {
    internal static DeepFrontierRadioactiveWater Provider { get; private set; }
    public void StartMod(IModEnvironment modEnvironment) {
      if (Provider != null) throw new InvalidOperationException("Deep Frontier registered its radioactive water twice");
      Provider = new DeepFrontierRadioactiveWater();
      ModdableFluidsEntry.RegisterProvider(Provider);
      Debug.Log("[DeepFrontier] Radioactive water registered with Moddable Fluids " + ModdableFluidsEntry.ApiVersion + ".");
    }
  }

  /// <summary>
  /// The Moddable Fluids build's radiation service: <see cref="ModdableFluidsRadiationService"/> on the native
  /// singleton lifecycle, with the <c>DeepFrontier.Radiation</c> save. Loading reads versions 2 and 3 (their water
  /// is imported by Moddable Fluids in the first fluid substep; their soil and sources stay here) and version 4.
  /// A save before that first substep writes the old record back with the current sources (no tick has run, so
  /// they are the loaded ones unless a new source was added), so nothing is lost or half-migrated.
  /// </summary>
  public sealed class ModdableFluidsRadiation : ModdableFluidsRadiationService, ILoadableSingleton, ISaveableSingleton, ITickableSingleton {
    private static readonly SingletonKey RadiationKey = new SingletonKey("DeepFrontier.Radiation");
    private static readonly PropertyKey<int> VersionKey = new PropertyKey<int>("Version");
    private static readonly ListKey<Vector3Int> CellsKey = new ListKey<Vector3Int>("Cells");
    private static readonly ListKey<float> SludgeKey = new ListKey<float>("Sludge");
    private static readonly ListKey<float> WaterRadiationKey = new ListKey<float>("WaterRadiation");
    private static readonly ListKey<float> SoilKey = new ListKey<float>("Soil");
    private static readonly ListKey<int> SourceIdsKey = new ListKey<int>("SourceIds");
    private static readonly ListKey<Vector3Int> SourceCellsKey = new ListKey<Vector3Int>("SourceCells");
    private static readonly ListKey<float> SourceRatesKey = new ListKey<float>("SourceRates");
    private static readonly ListKey<float> SourceHoursKey = new ListKey<float>("SourceHours");
    private static readonly PropertyKey<int> NextSourceIdKey = new PropertyKey<int>("NextSourceId");
    private static readonly PropertyKey<float> HourAccumulatorKey = new PropertyKey<float>("HourAccumulator");
    private static readonly PropertyKey<bool> SnapshotKey = new PropertyKey<bool>("LastCompletedTickSnapshot");

    private readonly ISingletonLoader _singletonLoader;
    private readonly IDayNightCycle _dayNightCycle;
    private readonly DeepFrontierRadioactiveWater _provider;
    private readonly RadiationSoilLedger _soil;
    private float _hourAccumulator;

    public ModdableFluidsRadiation(ISingletonLoader singletonLoader, MapIndexService mapIndex, ITickService tickService, IDayNightCycle dayNightCycle)
      : this(singletonLoader, mapIndex, tickService, dayNightCycle, DeepFrontierFluidsModStarter.Provider
          ?? throw new InvalidOperationException("Deep Frontier's radioactive water was not registered at mod start"), new RadiationSoilLedger()) { }

    private ModdableFluidsRadiation(ISingletonLoader singletonLoader, MapIndexService mapIndex, ITickService tickService, IDayNightCycle dayNightCycle,
        DeepFrontierRadioactiveWater provider, RadiationSoilLedger soil)
      : base(provider, soil, () => tickService.TickIntervalInSeconds / dayNightCycle.FixedDeltaTimeInHours,
          () => new Vector2Int(mapIndex.TerrainSize.x, mapIndex.TerrainSize.y)) {
      _singletonLoader = singletonLoader; _dayNightCycle = dayNightCycle; _provider = provider; _soil = soil;
    }

    public void Load() {
      RadiationLegacyRecord legacy = null;
      if (_singletonLoader.TryGetSingleton(RadiationKey, out var loader)) {
        int version = loader.Get(VersionKey);
        var ids = loader.Get(SourceIdsKey); var cells = loader.Get(SourceCellsKey); var rates = loader.Get(SourceRatesKey); var hours = loader.Get(SourceHoursKey);
        if (cells.Count != ids.Count || rates.Count != ids.Count || hours.Count != ids.Count) throw new InvalidOperationException("Radiation source save lists have different lengths");
        var sources = Enumerable.Range(0, ids.Count).Select(k => new RadiationSourceRecord(ids[k], cells[k], rates[k], hours[k])).ToArray();
        if (version == RadiationFacadeRecord.Version) {
          var record = new RadiationFacadeRecord(loader.Get(CellsKey), loader.Get(SoilKey), sources, loader.Get(NextSourceIdKey), loader.Get(HourAccumulatorKey));
          _soil.Load(record.SoilCells, record.Soil);
          LoadSources(record.Sources, record.NextSourceId);
          _hourAccumulator = record.HourAccumulator;
        } else {
          legacy = new RadiationLegacyRecord(version, loader.Has(SnapshotKey) && loader.Get(SnapshotKey), loader.Get(CellsKey), loader.Get(WaterRadiationKey),
            loader.Get(SoilKey), version == RadiationLegacyRecord.SludgeVersion ? loader.Get(SludgeKey) : null, sources, loader.Get(NextSourceIdKey), loader.Get(HourAccumulatorKey));
          // Soil lies under the same column cells; it stays Deep Frontier's.
          _soil.Load(legacy.Cells, legacy.Soil);
          LoadSources(legacy.Sources, legacy.NextSourceId);
          _hourAccumulator = legacy.HourAccumulator;
        }
      }
      _provider.PrepareScene(_dayNightCycle.FixedDeltaTimeInHours, legacy);
    }

    public void Tick() {
      float hours = _dayNightCycle.FixedDeltaTimeInHours;
      Tick(hours);
      _hourAccumulator += hours;
      if (_hourAccumulator >= 1f) { _soil.Decay(_hourAccumulator); _hourAccumulator = 0f; }
    }

    public void Save(ISingletonSaver singletonSaver) {
      var saver = singletonSaver.GetSingleton(RadiationKey);
      var pending = _provider.PendingRecord;
      if (pending != null) { WriteLegacy(saver, pending); WriteSources(saver, Sources.ToArray(), NextSourceId, _hourAccumulator); return; }
      var (cells, soil) = _soil.Save();
      saver.Set(VersionKey, RadiationFacadeRecord.Version);
      saver.Set(CellsKey, cells); saver.Set(SoilKey, soil);
      WriteSources(saver, Sources.ToArray(), NextSourceId, _hourAccumulator);
    }

    private static void WriteLegacy(IObjectSaver saver, RadiationLegacyRecord record) {
      saver.Set(VersionKey, record.Version);
      saver.Set(CellsKey, record.Cells.ToArray()); saver.Set(WaterRadiationKey, record.WaterRadiation.ToArray()); saver.Set(SoilKey, record.Soil.ToArray());
      if (record.Sludge != null) saver.Set(SludgeKey, record.Sludge.ToArray());
      if (record.Snapshot) saver.Set(SnapshotKey, true);
    }

    private static void WriteSources(IObjectSaver saver, RadiationSourceRecord[] sources, int nextSourceId, float hourAccumulator) {
      saver.Set(SourceIdsKey, sources.Select(s => s.Id).ToArray()); saver.Set(SourceCellsKey, sources.Select(s => s.Cell).ToArray());
      saver.Set(SourceRatesKey, sources.Select(s => s.VolumePerHour).ToArray()); saver.Set(SourceHoursKey, sources.Select(s => s.RemainingHours).ToArray());
      saver.Set(NextSourceIdKey, nextSourceId); saver.Set(HourAccumulatorKey, hourAccumulator);
    }
  }
}
#endif
