#if DEEP_FRONTIER_MODDABLE_FLUIDS
using System;
using System.Collections.Generic;
using System.Linq;
using DeepFrontier.Scripts.Radiation;
using DeepFrontier.Scripts.RadioactiveTide;
using ModdableFluids;
using Timberborn.BlockSystem;
using Timberborn.MapIndexSystem;
using Timberborn.ModManagerScene;
using Timberborn.NaturalResourcesLifecycle;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>Registers Deep Frontier's radioactive water with Moddable Fluids at mod start (flagged build only).</summary>
  internal sealed class DeepFrontierFluidsModStarter : IModStarter {
    internal static DeepFrontierRadioactiveWater Provider { get; private set; }
    public void StartMod(IModEnvironment modEnvironment) {
      if (Provider != null) throw new InvalidOperationException("Deep Frontier registered its radioactive water twice");
      Provider = new DeepFrontierRadioactiveWater(Tide());
      ModdableFluidsEntry.RegisterProvider(Provider);
      Debug.Log("[DeepFrontier] Radioactive water and the radioactive tide registered with Moddable Fluids " + ModdableFluidsEntry.ApiVersion + ".");
    }

    // RadioactiveTideTuning's Easy, Normal and Hard points; Moddable Fluids derives every other mode with Deep Frontier's
    // rule (FluidTideModes.Derive), and a tide alone keeps RadioactiveTideService's draws.
    private static RadioactiveTideRegistration Tide() => new RadioactiveTideRegistration(RadioactiveTideTuning.WeatherId, RadioactiveTideLoc.Name,
      RadioactiveTideLoc.ModdableDescription,
      RadioactiveTideTuning.GameModeCurve.Select(p => (p.Mode, p.ChancePercent, p.CyclesWithoutTide, p.MinDurationDays, p.MaxDurationDays)),
      RadioactiveTideTuning.SourceRadioactiveShare,
      new[] { RadioactiveTideLoc.Approaching, RadioactiveTideLoc.InProgress, RadioactiveTideLoc.Started, RadioactiveTideLoc.Ended,
        RadioactiveTideLoc.ApproachingDescription, RadioactiveTideLoc.StartedDescription },
      new[] { RadioactiveTideTuning.IconSpritePath, RadioactiveTideTuning.ProgressSpritePath, RadioactiveTideTuning.NotificationSpritePath },
      FluidTideRules.BadtideSound);
  }

  /// <summary>
  /// The Moddable Fluids build's radiation service: <see cref="ModdableFluidsRadiationService"/> on the native singleton
  /// lifecycle, with the <c>DeepFrontier.Radiation</c> save. Loading reads versions 2 and 3 (their water is imported by
  /// Moddable Fluids in the first fluid substep; their soil and sources stay here) and version 4. A save before that
  /// first substep writes the old record back with the current sources and requests, so nothing is lost or
  /// half-migrated. Its late tick does what RadiationSimulation.Tick does on the main thread after the soil rules ran
  /// on the worker: emit sources and the tide share, credit sludge intakes (CreditIntakes), turn the native kernels'
  /// levels into the bank layer, kill plants on newly irradiated ground (KillOnIrradiatedGround), and prepare the
  /// kernels' next run.
  /// </summary>
  public sealed class ModdableFluidsRadiation : ModdableFluidsRadiationService, IRadioactiveIntakes, IRadioactiveSprings,
      ILoadableSingleton, IPostLoadableSingleton, ISaveableSingleton, ITickableSingleton, ILateTickable {
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
    // Version 4 (and a version 2/3 record written back before its import): requests no fluid tick applied yet.
    private static readonly ListKey<Vector3Int> PendingSoilCellsKey = new ListKey<Vector3Int>("PendingSoilCells");
    private static readonly ListKey<float> PendingSoilAmountsKey = new ListKey<float>("PendingSoilAmounts");
    private static readonly ListKey<Vector3Int> EarlyWaterCellsKey = new ListKey<Vector3Int>("EarlyWaterCells");
    private static readonly ListKey<float> EarlyWaterVolumesKey = new ListKey<float>("EarlyWaterVolumes");

    private readonly ISingletonLoader _singletonLoader;
    private readonly MapIndexService _mapIndex;
    private readonly IDayNightCycle _dayNightCycle;
    private readonly IBlockService _blockService;
    private readonly ModdableFluidsBankLayer _bank;
    private readonly DeepFrontierRadioactiveWater _provider;
    private readonly Dictionary<Vector3Int, RadioactiveSludgeIntake> _intakes = new Dictionary<Vector3Int, RadioactiveSludgeIntake>();
    private HashSet<Vector3Int> _irradiated = new HashSet<Vector3Int>(), _irradiatedNext = new HashSet<Vector3Int>();
    private int _lastPass;

    public ModdableFluidsRadiation(ISingletonLoader singletonLoader, MapIndexService mapIndex, IThreadSafeWaterMap waterMap, ITickService tickService,
        IDayNightCycle dayNightCycle, IBlockService blockService, ModdableFluidsBankLayer bank)
      : this(singletonLoader, mapIndex, new NativeRadiationCellMap(mapIndex, waterMap), tickService, dayNightCycle, blockService, bank,
          DeepFrontierFluidsModStarter.Provider ?? throw new InvalidOperationException("Deep Frontier's radioactive water was not registered at mod start")) { }

    private ModdableFluidsRadiation(ISingletonLoader singletonLoader, MapIndexService mapIndex, IRadiationCellMap cells, ITickService tickService,
        IDayNightCycle dayNightCycle, IBlockService blockService, ModdableFluidsBankLayer bank, DeepFrontierRadioactiveWater provider)
      : base(provider, cells, () => tickService.TickIntervalInSeconds / dayNightCycle.FixedDeltaTimeInHours) {
      _singletonLoader = singletonLoader; _mapIndex = mapIndex; _dayNightCycle = dayNightCycle; _blockService = blockService; _bank = bank; _provider = provider;
    }

    public void Load() {
      var field = new RadiationSoilField(_mapIndex.TerrainSize.x, _mapIndex.TerrainSize.y, _dayNightCycle.FixedDeltaTimeInHours);
      AttachSoil(field);
      RadiationLegacyRecord legacy = null;
      if (_singletonLoader.TryGetSingleton(RadiationKey, out var loader)) {
        int version = loader.Get(VersionKey);
        var ids = loader.Get(SourceIdsKey); var cells = loader.Get(SourceCellsKey); var rates = loader.Get(SourceRatesKey); var hours = loader.Get(SourceHoursKey);
        if (cells.Count != ids.Count || rates.Count != ids.Count || hours.Count != ids.Count) throw new InvalidOperationException("Radiation source save lists have different lengths");
        var sources = Enumerable.Range(0, ids.Count).Select(k => new RadiationSourceRecord(ids[k], cells[k], rates[k], hours[k])).ToArray();
        var pendingSoil = Pairs(loader, PendingSoilCellsKey, PendingSoilAmountsKey, version == RadiationFacadeRecord.Version);
        var earlyWater = Pairs(loader, EarlyWaterCellsKey, EarlyWaterVolumesKey, version == RadiationFacadeRecord.Version);
        if (version == RadiationFacadeRecord.Version) {
          var record = new RadiationFacadeRecord(loader.Get(CellsKey), loader.Get(SoilKey), sources, loader.Get(NextSourceIdKey), loader.Get(HourAccumulatorKey),
            pendingSoil, earlyWater);
          field.Load(record.SoilCells, record.Soil, record.HourAccumulator, lenient: false);
          LoadSources(record.Sources, record.NextSourceId);
        } else {
          legacy = new RadiationLegacyRecord(version, loader.Has(SnapshotKey) && loader.Get(SnapshotKey), loader.Get(CellsKey), loader.Get(WaterRadiationKey),
            loader.Get(SoilKey), version == RadiationLegacyRecord.SludgeVersion ? loader.Get(SludgeKey) : null, sources, loader.Get(NextSourceIdKey), loader.Get(HourAccumulatorKey));
          // Soil lies under the same column cells; it stays Deep Frontier's.
          field.Load(legacy.Cells, legacy.Soil, legacy.HourAccumulator, legacy.Snapshot);
          LoadSources(legacy.Sources, legacy.NextSourceId);
        }
        foreach (var (cell, amount) in pendingSoil) field.RequestSoil(cell, amount);
        LoadEarlyAdditions(earlyWater);
      }
      _provider.PrepareScene(field, legacy);
    }

    private static List<(Vector3Int, float)> Pairs(IObjectLoader loader, ListKey<Vector3Int> cellsKey, ListKey<float> valuesKey, bool required) {
      var result = new List<(Vector3Int, float)>();
      if (!required && !loader.Has(cellsKey) && !loader.Has(valuesKey)) return result;
      var cells = loader.Get(cellsKey); var values = loader.Get(valuesKey);
      if (cells.Count != values.Count) throw new InvalidOperationException("Radiation save lists of pending requests have different lengths");
      for (int k = 0; k < cells.Count; k++) result.Add((cells[k], values[k]));
      return result;
    }

    // After the bank layer's PostLoad (it is created first, as this service's dependency): the native washout rate.
    public void PostLoad() {
      Soil.SetWashoutPerHour(_bank.WashoutPerHour);
      Soil.Bank = _bank;
    }

    // Late tick: after every non-late singleton (the tide sets its share, the bank layer takes its rows).
    public void Tick() {
      Tick(_dayNightCycle.FixedDeltaTimeInHours);
      foreach (var correction in Soil.TakeLoadCorrections()) Debug.LogWarning("[DeepFrontier] Radiation: the exception save's soil " + correction);
      foreach (var pair in Soil.TakeRemovedRadioactive())
        if (_intakes.TryGetValue(pair.Key, out var intake)) intake.OnRadioactiveRemoved(pair.Value);
      var pass = Soil.Published;
      if (pass.Pass == _lastPass) return;
      _lastPass = pass.Pass;
      _bank.Update();
      KillOnIrradiatedGround(pass);
      _bank.Prepare(pass);
    }

    // RadiationSimulation.KillOnIrradiatedGround: a column cell that turns irradiated (or whose cell's columns
    // changed) kills the plant standing on it through the native LivingNaturalResource.Die.
    private void KillOnIrradiatedGround(RadiationFieldSnapshot pass) {
      foreach (var cell in Soil.TakeChangedCells()) _irradiated.RemoveWhere(k => k.x == cell.x && k.y == cell.y);
      _irradiatedNext.Clear();
      foreach (var pair in pass.Soil) if (pair.Value >= RadiationTuning.IrradiatedGroundThreshold) _irradiatedNext.Add(pair.Key);
      _bank.CollectAtOrAbove(RadiationTuning.IrradiatedGroundThreshold, _irradiatedNext);
      foreach (var key in _irradiatedNext) {
        if (_irradiated.Contains(key)) continue;
        var plant = _blockService.GetBottomObjectComponentAt<LivingNaturalResource>(key);
        if (plant != null && !plant.IsDead) plant.Die();
      }
      (_irradiated, _irradiatedNext) = (_irradiatedNext, _irradiated);
    }

    public void Save(ISingletonSaver singletonSaver) {
      var saver = singletonSaver.GetSingleton(RadiationKey);
      var pending = _provider.PendingRecord;
      if (pending != null) WriteLegacy(saver, pending);
      else {
        var soil = Soil.Published;
        var cells = soil.Soil.Keys.OrderBy(c => c.y).ThenBy(c => c.x).ThenBy(c => c.z).ToArray();
        saver.Set(VersionKey, RadiationFacadeRecord.Version);
        saver.Set(CellsKey, cells); saver.Set(SoilKey, cells.Select(c => soil.Soil[c]).ToArray());
        saver.Set(HourAccumulatorKey, soil.HourAccumulator);
      }
      var sources = Sources.ToArray();
      saver.Set(SourceIdsKey, sources.Select(s => s.Id).ToArray()); saver.Set(SourceCellsKey, sources.Select(s => s.Cell).ToArray());
      saver.Set(SourceRatesKey, sources.Select(s => s.VolumePerHour).ToArray()); saver.Set(SourceHoursKey, sources.Select(s => s.RemainingHours).ToArray());
      saver.Set(NextSourceIdKey, NextSourceId);
      var requests = Soil.PendingRequests;
      saver.Set(PendingSoilCellsKey, requests.Select(r => r.Cell).ToArray()); saver.Set(PendingSoilAmountsKey, requests.Select(r => r.Amount).ToArray());
      saver.Set(EarlyWaterCellsKey, EarlyAdditions.Select(r => r.Cell).ToArray()); saver.Set(EarlyWaterVolumesKey, EarlyAdditions.Select(r => r.Volume).ToArray());
    }

    // The record as loaded: its water waits for the first fluid substep, so it is written back unchanged.
    private static void WriteLegacy(IObjectSaver saver, RadiationLegacyRecord record) {
      saver.Set(VersionKey, record.Version);
      saver.Set(CellsKey, record.Cells.ToArray()); saver.Set(WaterRadiationKey, record.WaterRadiation.ToArray()); saver.Set(SoilKey, record.Soil.ToArray());
      if (record.Sludge != null) saver.Set(SludgeKey, record.Sludge.ToArray());
      if (record.Snapshot) saver.Set(SnapshotKey, true);
      saver.Set(HourAccumulatorKey, record.HourAccumulator);
    }

    // RadiationSimulation.RegisterIntake: the radioactive volume the native removals at the intake cell drew is credited
    // to it once per tick, from the tick's Moddable Fluids losses (RadiationSoilField).
    void IRadioactiveIntakes.RegisterIntake(Vector3Int cell, RadioactiveSludgeIntake intake) {
      if (_intakes.ContainsKey(cell)) throw new InvalidOperationException("Two sludge recovery intakes share the cell " + cell);
      _intakes.Add(cell, intake ?? throw new ArgumentNullException(nameof(intake)));
    }

    void IRadioactiveIntakes.UnregisterIntake(Vector3Int cell, RadioactiveSludgeIntake intake) {
      if (!_intakes.TryGetValue(cell, out var registered) || registered != intake)
        throw new InvalidOperationException("Sludge recovery intake at " + cell + " was not registered");
      _intakes.Remove(cell);
    }

    // Springs are Moddable Fluids source types (DeepFrontierRadioactiveWater.Register): Moddable Fluids emits their
    // radioactive water. The spec's share must be the registered emission, or the two descriptions disagree.
    void IRadioactiveSprings.RegisterSpring(IWaterSource source, float share) {
      if (source == null) throw new ArgumentNullException(nameof(source));
      if (share != DeepFrontierRadioactiveWater.SpringShare)
        throw new InvalidOperationException("Radioactive spring share " + share + " differs from the registered source types' emission " + DeepFrontierRadioactiveWater.SpringShare);
    }

    void IRadioactiveSprings.UnregisterSpring(IWaterSource source) {
      if (source == null) throw new ArgumentNullException(nameof(source));
    }
  }

  /// <summary>Native water geometry, read exactly as RadiationSimulation reads it (TryFindOpenCell, IsOpenCell, Sample).</summary>
  internal sealed class NativeRadiationCellMap : IRadiationCellMap {
    private readonly MapIndexService _mapIndex;
    private readonly IThreadSafeWaterMap _waterMap;
    public NativeRadiationCellMap(MapIndexService mapIndex, IThreadSafeWaterMap waterMap) { _mapIndex = mapIndex; _waterMap = waterMap; }

    public Vector2Int Size => new Vector2Int(_mapIndex.TerrainSize.x, _mapIndex.TerrainSize.y);
    public bool IsOpenCell(Vector3Int cell) => _waterMap.TryGetColumnFloor(cell, out _);
    public bool IsSubmerged(Vector3Int cell) => _waterMap.CellIsUnderwater(cell);
    public float BadwaterShare(Vector3Int cell) => _waterMap.ColumnContamination(cell);

    public bool TryFindOpenCell(Vector2Int xy, int z, out Vector3Int cell) {
      int i = _mapIndex.CellToIndex(xy), vs = _mapIndex.VerticalStride;
      int best = int.MaxValue;
      for (int j = 0; j < _waterMap.ColumnCount(i); j++) {
        int idx = j * vs + i;
        int floor = _waterMap.ColumnFloor(idx), ceiling = _waterMap.ColumnCeiling(idx);
        if (floor >= ceiling) continue;
        if (z >= floor && z < ceiling) { cell = new Vector3Int(xy.x, xy.y, z); return true; }
        if (floor > z && floor < best) best = floor;
      }
      if (best != int.MaxValue) { cell = new Vector3Int(xy.x, xy.y, best); return true; }
      cell = default;
      return false;
    }
  }
}
#endif
