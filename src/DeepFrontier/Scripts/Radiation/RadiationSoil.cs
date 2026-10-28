using System;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.InteropServices;
#if !UNITY_EDITOR
using HarmonyLib;
#endif
using Timberborn.BlueprintSystem;
using Timberborn.Common;
using Timberborn.MapIndexSystem;
using Timberborn.Multithreading;
using Timberborn.SingletonSystem;
using Timberborn.SoilBarrierSystem;
using Timberborn.SoilContaminationSystem;
using Timberborn.SoilMoistureSystem;
using Timberborn.TerrainSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.Radiation {
  // Radioactive water toward the soil, as the game treats badwater
  // (Timberborn 1.1.2.8, decompiled Timberborn.SoilMoistureSystem and
  // Timberborn.SoilContaminationSystem; outputs/soil-native-1.1.2.8):
  //
  // 1. Moisture. Native MoistureCalculationTask reads ReadOnlyWaterColumn
  //    .Contamination: water below MinimumWaterContamination (0.01) irrigates
  //    its full range 2 x cluster saturation (at most 16), water at or above
  //    MaximumWaterContamination (0.53) irrigates nothing, between them the
  //    range is (int)(range x (1 - c / 0.53)); a cell's moisture is finally
  //    multiplied by 1 - c of the water standing on it. In the one-fluid model
  //    the native columns carry only b, so radioactive water irrigated like
  //    fresh water. A prefix of SoilMoistureSimulationTaskStarter.StartTask
  //    hands the native moisture tasks a copy of the thread-safe water columns
  //    whose Contamination is b + r (<= 1). Only the moisture tasks see it.
  //
  // 2. Irradiated ground around radioactive water. The native soil
  //    contamination kernels (ContaminationCandidatesCountingTask,
  //    ContaminationsUpdateTask) run on shadow arrays whose water columns carry
  //    c = min + T / scaler with T = min(1, WaterToSoilFactor x r) (0 where
  //    r = 0), so the kernel's water term (c - min) x scaler is exactly the
  //    existing soil target T under radioactive water. The native rules then
  //    spread it: -1/MaxRangeFromSource per orthogonal step, -sqrt(2)/Max
  //    diagonally, -VerticalSpreadCostMultiplier/Max per level uphill, soil
  //    barriers block it, levels below ContaminationThreshold are 0. The level
  //    is the bank layer (BankAt): readers see max(soil, bank), and it rises
  //    and clears exactly like native contaminated banks (+0.035/s, -0.01/s
  //    after the water turns clean). It is never written into the soil.
  //
  // 3. Rinsing and washout (Exchange). Ground under clean water (the share
  //    reads 0), at any depth, falls at the native recovery rate (0.192 per
  //    game hour, 5.2 h from 1 to 0); the water takes the washed volume up to
  //    RinseShareCap and the rest is diluted away below the cutoff. Under
  //    radioactive water soil and share move toward s = T(r), conserving
  //    radioactive volume (VolumePerSoil per unit of soil). Dry ground only
  //    decays and spreads.
  //
  // The kernels run only on the rows that can hold a level (radiation rows +
  // FieldRowMargin, and rows whose banks are still clearing), with the native
  // per-tick parameters read from the native SoilContaminationSimulationTaskStarter.
  // The level arrays are transient (rebuilt from the water in about 1.5 game
  // hours after a load), so nothing new is saved.
  //
  // Threading: the shadows are built in RadiationSimulation's late Tick (main
  // thread, between parallel ticks, after ThreadSafeWaterMap.Tick copied the
  // native columns); the kernels run in this singleton's StartParallelTick
  // and are read in the next late Tick.
  public sealed class RadiationSoil : ILoadableSingleton, IPostLoadableSingleton, ITickableSingleton, IParallelTickableSingleton,
      IUnloadableSingleton {
    // Rows beyond the radiation rows (which already carry RangeMargin) that
    // the kernels run on; RangeMargin + FieldRowMargin must exceed the native
    // reach MaxRangeFromSource + 1 (PostLoad throws otherwise).
    internal const int FieldRowMargin = RadiationTuning.GeometrySyncMargin;
    // Submerged ground washes out at the native recovery rate of contaminated
    // soil (_washoutPerHour, set in PostLoad): native ContaminationsUpdateTask
    // lowers a level by ContaminationNegativeEqualizationRate (0.01/s) x
    // TickIntervalInSeconds (0.6 s) = 0.006 per tick once the water is clean;
    // 32 ticks per game hour gives 0.192 per hour, so fully irradiated ground
    // clears in 5.2 game hours (its tint fades from 2.6 h and is gone at 4.9 h).
    // Radioactive volume held per unit of soil radiation (inverse of the
    // existing RadiationTuning.SoilPerDepositedVolume, the evaporation rule).
    internal const float VolumePerSoil = 1f / RadiationTuning.SoilPerDepositedVolume;
    // Rinse water takes washed radioactivity up to this share, half the
    // detection limit, so rinsing never makes clean water read radioactive.
    internal const float RinseShareCap = 0.5f * RadiationTuning.DetectionLimit;

    private readonly MapIndexService _mapIndex;
    private readonly IThreadSafeWaterMap _waterMap;
    private readonly IThreadSafeColumnTerrainMap _terrainMap;
    private readonly ITerrainService _terrainService;
    private readonly SoilBarrierMap _barriers;
    private readonly SoilContaminationSimulationTaskStarter _nativeStarter;
    private readonly ISpecService _specService;
    private readonly IParallelizer _parallelizer;
    private readonly IDayNightCycle _dayNightCycle;

    private int _stride, _vs, _xSize, _ySize;
    private float _washoutPerHour;
    // Water-slot indexed native-pattern level (banks), rebuilt every late tick.
    private float[] _bank = new float[0];
    private RadiationSimulation.RowRange _bankRows = RadiationSimulation.RowRange.None;
    // Native per-tick parameters (SoilContaminationSimulationTaskStarter.Load).
    private WaterColumnRetriever _waterColumnRetriever;
    private CeilingRetriever _ceilingRetriever;
    private float _maximumSoilContamination, _regularSpreadCost, _diagonalSpreadCost, _decayRate, _spreadingRate,
      _minimumWaterContamination, _contaminationScaler, _verticalCostModifier, _threshold, _positiveRate, _negativeRate;

    // Terrain-column indexed, as the native SoilContaminationSimulator arrays.
    private float[] _levels, _candidates, _lastCandidates;
    private bool[] _changed;
    private int _terrainLayers;
    private readonly List<(TerrainAction Type, int Value)> _actions = new List<(TerrainAction, int)>();
    private readonly List<TerrainHeightChange> _heightChanges = new List<TerrainHeightChange>();

    // Water-column indexed shadows of the thread-safe water map.
    private ReadOnlyWaterColumn[] _soilWater = new ReadOnlyWaterColumn[0];
    private ReadOnlyWaterColumn[] _moistureWater = new ReadOnlyWaterColumn[0];
    private bool _moistureReady;

    // Rows whose level arrays may be non-zero; rows the next parallel tick
    // computes; rows the parallel tick that just finished computed.
    private RadiationSimulation.RowRange _fieldRows = RadiationSimulation.RowRange.None;
    private RadiationSimulation.RowRange _scheduledRows = RadiationSimulation.RowRange.None;
    private RadiationSimulation.RowRange _ranRows = RadiationSimulation.RowRange.None;
    private RadiationSimulation.RowRange _computedRows = RadiationSimulation.RowRange.None;

    public RadiationSoil(MapIndexService mapIndex, IThreadSafeWaterMap waterMap, IThreadSafeColumnTerrainMap terrainMap,
        ITerrainService terrainService, SoilBarrierMap barriers, SoilContaminationSimulationTaskStarter nativeStarter,
        ISpecService specService, IParallelizer parallelizer, IDayNightCycle dayNightCycle) {
      _mapIndex = mapIndex; _waterMap = waterMap; _terrainMap = terrainMap; _terrainService = terrainService;
      _barriers = barriers; _nativeStarter = nativeStarter; _specService = specService; _parallelizer = parallelizer;
      _dayNightCycle = dayNightCycle;
    }

    public void Load() {
      _stride = _mapIndex.Stride;
      _vs = _mapIndex.VerticalStride;
      _xSize = _mapIndex.TerrainSize.x;
      _ySize = _mapIndex.TerrainSize.y;
#if !UNITY_EDITOR
      RadiationSoilPatches.Attach(this);
#endif
    }

    // After every Load: the native starter has read its spec, the terrain map
    // its columns.
    public void PostLoad() {
      RadiationSoilNative.Verify();
      var s = _nativeStarter;
      if (s._stride != _stride || s._verticalStride != _vs || s._mapSize.x != _xSize || s._mapSize.y != _ySize)
        throw new InvalidOperationException("Radiation soil: native soil contamination starter uses another map layout");
      _waterColumnRetriever = s._waterColumnRetriever ?? throw new InvalidOperationException("Radiation soil: native WaterColumnRetriever missing");
      _ceilingRetriever = s._ceilingRetriever ?? throw new InvalidOperationException("Radiation soil: native CeilingRetriever missing");
      _maximumSoilContamination = s._maximumSoilContamination; _regularSpreadCost = s._regularSpreadCost;
      _diagonalSpreadCost = s._diagonalSpreadCost; _decayRate = s._contaminationDecayRate; _spreadingRate = s._contaminationSpreadingRate;
      _minimumWaterContamination = s._minimumWaterContamination; _contaminationScaler = s._contaminationScaler;
      _verticalCostModifier = s._verticalCostModifier; _threshold = s._contaminationThreshold;
      _positiveRate = s._contaminationPositiveEqualizationRate; _negativeRate = s._contaminationNegativeEqualizationRate;
      // The native per-tick fall of a contaminated level, per game hour.
      _washoutPerHour = _negativeRate / _dayNightCycle.FixedDeltaTimeInHours;
      if (!(_washoutPerHour > 0f) || float.IsInfinity(_washoutPerHour))
        throw new InvalidOperationException($"Radiation soil: native negative equalization rate {_negativeRate} gives no washout");
      if (!(_minimumWaterContamination >= 0f && _minimumWaterContamination < 1f) || !(_contaminationScaler > 0f))
        throw new InvalidOperationException($"Radiation soil: native MinimumWaterContamination {_minimumWaterContamination} leaves no contamination range");
      int maxRange = _specService.GetSingleSpec<SoilContaminationSimulatorSpec>().MaxRangeFromSource;
      if (RadiationTuning.RangeMargin + FieldRowMargin < maxRange + 1)
        throw new InvalidOperationException($"Radiation soil: rows RangeMargin + FieldRowMargin must cover the native reach {maxRange} + 1");
      _terrainLayers = _terrainMap.MaxColumnCount;
      int size = _terrainLayers * _vs;
      _levels = new float[size]; _candidates = new float[size]; _lastCandidates = new float[size]; _changed = new bool[size];
      // Same events and order as native SoilContaminationSimulator.Load.
      _terrainService.TerrainHeightChanged += (_, e) => _heightChanges.Add(e.Change);
      _terrainMap.MaxTerrainColumnCountChanged += (_, i) => _actions.Add((TerrainAction.Resize, i));
      _terrainMap.ColumnMovedUp += (_, i) => _actions.Add((TerrainAction.MovedUp, i));
      _terrainMap.ColumnMovedDown += (_, i) => _actions.Add((TerrainAction.MovedDown, i));
      _terrainMap.ColumnReset += (_, i) => _actions.Add((TerrainAction.Reset, i));
    }

    public void Unload() {
#if !UNITY_EDITOR
      RadiationSoilPatches.Detach(this);
#endif
    }

    // Before every late tick: what the parallel tick that just finished computed.
    public void Tick() {
      _computedRows = _ranRows;
      _ranRows = RadiationSimulation.RowRange.None;
    }

    public void StartParallelTick() {
      var rows = _scheduledRows;
      _scheduledRows = RadiationSimulation.RowRange.None;
      if (rows.Empty) return;
      _ranRows = rows;
      var counts = _waterMap.ColumnCounts;
      var terrainCounts = _terrainMap.ColumnCounts;
      var prepare = new RadiationSoilPreparationTask(this);
      var candidates = new ContaminationCandidatesCountingTask(_waterColumnRetriever, _ceilingRetriever, _candidates, counts,
        new ReadOnlyArray<ReadOnlyWaterColumn>(_soilWater), terrainCounts, _terrainMap.TerrainColumns, _barriers.ContaminationBarriers,
        _barriers.AboveMoistureBarriers, new ReadOnlyArray<float>(_lastCandidates), _xSize, _stride, _vs, _maximumSoilContamination,
        _regularSpreadCost, _diagonalSpreadCost, _decayRate, _spreadingRate, _minimumWaterContamination, _contaminationScaler, _verticalCostModifier);
      var update = new ContaminationsUpdateTask(_levels, _changed, terrainCounts, new ReadOnlyArray<float>(_candidates), _xSize, _stride, _vs,
        _threshold, _positiveRate, _negativeRate);
      // Native order and batch sizes (SoilContaminationSimulationTaskStarter.StartTask), on our rows.
      _parallelizer.Schedule(rows.Lo, rows.Hi + 1, 1, in prepare)
        .ContinueWith(rows.Lo, rows.Hi + 1, 1, in candidates)
        .ContinueWith(rows.Lo, rows.Hi + 1, 5, in update);
    }

    // Native ContaminationDataPreparationTask, one row: rows outside the field
    // rows are zero in both arrays, as the whole-array native copy would leave them.
    internal void PrepareRow(int y) {
      int start = (y + 1) * _stride;
      for (int layer = 0; layer < _terrainLayers; layer++) {
        int first = layer * _vs + start;
        Array.Copy(_candidates, first, _lastCandidates, first, _stride);
        Array.Clear(_changed, first, _stride);
      }
    }

    // ------------------------------------------------------- late tick (main)

    // RadiationSimulation.Tick, after decay and before Rescan.
    // 1. Banks: the native levels the parallel tick computed become the bank
    //    layer (RadiationSoil.BankAt; read as max(soil, bank)), which rises and
    //    clears exactly like native soil contamination and is never stored in
    //    the soil.
    // 2. Ground under water (any depth, as native contact):
    //    - clean water (the share reads 0 below DetectionLimit) rinses it at
    //      the native rate (Rinse);
    //    - radioactive water exchanges with it, conserved, toward the
    //      equilibrium soil = min(1, WaterToSoilFactor x r) (SoilWaterExchange):
    //      the ground rises at SoilRiseFromWaterPerHour drawing the radioactive
    //      volume from the water, and washes out at the native rate.
    // 3. Dry ground only decays and spreads (HourlySoilPass).
    internal void Exchange(RadiationSimulation simulation, float hours, RadiationSimulation.RowRange envelope) {
      ProcessTerrainActions();
      var map = envelope.Clamp(0, _ySize - 1);
      var counts = simulation.Counts; var water = simulation.WaterSnapshot;
      var radiation = simulation.WaterRadiation; var soil = simulation.SoilRadiation;
      if (_bank.Length != soil.Length) Array.Resize(ref _bank, soil.Length);
      UpdateBanks(counts, water, map);
      var rows = Intersect(simulation.VisibleRows, map);
      if (rows.Empty) return;
      var native = MemoryMarshal.Cast<ReadOnlyWaterColumn, WaterColumn>(_waterMap.WaterColumns.AsSpan);
      if (native.Length != simulation.Layers * _vs)
        throw new InvalidOperationException("Radiation soil: thread-safe water map layers differ from the mirrored radiation layers");
      float rise = RadiationTuning.SoilRiseFromWaterPerHour * hours, wash = _washoutPerHour * hours;
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        int rowStart = (y + 1) * _stride + 1;
        for (int x = 0; x < _xSize; x++) {
          int i = rowStart + x;
          for (int j = 0; j < counts[i]; j++) {
            int idx = j * _vs + i;
            ref readonly var column = ref water[idx];
            if (!(column.WaterDepth > 0f)) continue;
            float s = soil[idx], r = radiation[idx];
            if (!(s > 0f) && !(r > 0f)) continue;
            RequireSameColumn(in native[idx], in column);
            float bad = native[idx].Contamination, depth = simulation.EffectiveDepth(in column);
            float delta, share;
            if (RadiationTuning.Detected(r) == 0f) {
              if (!(s > 0f)) continue;
              delta = Rinse(s, r, bad, depth, wash, out share);
            } else {
              delta = SoilWaterExchange(s, r, bad, depth, rise, wash);
              if (delta == 0f) continue;
              share = r - delta * VolumePerSoil / depth;
              // Float rounding only; anything larger is a broken exchange.
              if (share < 0f) {
                if (share < -RadiationTuning.ShareTolerance) throw new InvalidOperationException($"Radiation soil: exchange left a negative radioactive share {share}");
                share = 0f;
              }
            }
            RadiationMixing.RequireShares(bad, share, "the soil washout");
            soil[idx] = s + delta;
            radiation[idx] = share;
          }
        }
      }
    }

    // Rinsing under clean water: the soil falls at the native rate whatever
    // the depth. The water takes the washed radioactive volume up to
    // RinseShareCap (below DetectionLimit, so rinse water never reads
    // radioactive); the rest counts as diluted below the cutoff and is gone,
    // as the cutoff removes it from flowing water anyway. Returns the soil
    // change (negative) and the new share.
    internal static float Rinse(float s, float r, float b, float d, float maxWash, out float share) {
      if (!(d > 0f)) throw new ArgumentOutOfRangeException(nameof(d), d, "Only ground under water is rinsed");
      if (RadiationTuning.Detected(r) != 0f) throw new ArgumentOutOfRangeException(nameof(r), r, "Rinsing needs clean water (a share below DetectionLimit)");
      float washed = Mathf.Min(s, maxWash);
      float room = Mathf.Max(0f, Mathf.Min(RinseShareCap - r, 1f - b - r)) * d;
      share = r + Mathf.Min(washed * VolumePerSoil, room) / d;
      return -washed;
    }

    // The bank layer: native levels from the parallel tick that just finished,
    // on _computedRows; zero elsewhere.
    private void UpdateBanks(byte[] counts, WaterColumn[] water, RadiationSimulation.RowRange map) {
      var computed = Intersect(_computedRows, map);
      for (int y = _bankRows.Lo; y <= _bankRows.Hi; y++)
        if (y < computed.Lo || y > computed.Hi) ClearBankRow(y);
      var bankRows = RadiationSimulation.RowRange.None;
      for (int y = computed.Lo; y <= computed.Hi; y++) {
        ClearBankRow(y);
        int rowStart = (y + 1) * _stride + 1;
        for (int x = 0; x < _xSize; x++) {
          int i = rowStart + x;
          for (int j = 0; j < counts[i]; j++) {
            int idx = j * _vs + i;
            if (!_terrainMap.TryGetIndexAtCeiling(i, water[idx].Floor, out int terrain)) continue;
            float level = _levels[terrain];
            if (!(level > 0f)) continue;
            _bank[idx] = level;
            bankRows.Include(y);
          }
        }
      }
      _bankRows = bankRows;
    }

    private void ClearBankRow(int y) {
      int start = (y + 1) * _stride;
      for (int first = start; first < _bank.Length; first += _vs) Array.Clear(_bank, first, _stride);
    }

    // Native-pattern level of the ground under water slot idx (0 where none).
    internal float BankAt(int idx) => idx < _bank.Length ? _bank[idx] : 0f;
    internal RadiationSimulation.RowRange BankRows => _bankRows;

    // Soil change (positive: the ground takes radiation from the water) for
    // soil s under water with radioactive share r, badwater share b and
    // effective depth d. Never crosses the equilibrium s = min(1, F x r)
    // (F = WaterToSoilFactor) after the exchange, never exceeds the rates,
    // never takes more radioactive water than there is, and keeps b + r <= 1.
    internal static float SoilWaterExchange(float s, float r, float b, float d, float maxRise, float maxWash) {
      if (!(d > 0f)) throw new ArgumentOutOfRangeException(nameof(d), d, "Soil exchanges radiation only with standing water");
      const float F = RadiationTuning.WaterToSoilFactor;
      float a = VolumePerSoil / d;                 // share change per unit of soil radiation
      // A share below DetectionLimit reads 0: the ground does not take it up,
      // but it still counts toward the washout equilibrium below.
      float target = Mathf.Min(1f, RadiationTuning.Detected(r) * F);
      if (s < target) {
        // Equilibrium after the exchange: saturated (1) while the water keeps
        // F x r' >= 1, else F x (r - a x delta) = s + delta.
        float equilibrium = (r - (1f - s) * a) * F >= 1f ? 1f - s : (r * F - s) / (1f + F * a);
        return Mathf.Min(maxRise, equilibrium);
      }
      if (s > target) {
        // s > F x r here, so the equilibrium is unsaturated: s - w = F x (r + a x w).
        float equilibrium = (s - r * F) / (1f + F * a);
        float headroom = (1f - b - r) / a;         // b + r' <= 1
        float washed = Mathf.Min(maxWash, Mathf.Min(equilibrium, headroom));
        return washed > 0f ? -washed : 0f;
      }
      return 0f;
    }

    // RadiationSimulation.Tick, after Rescan: the shadows and rows for the next
    // parallel tick.
    internal void Prepare(RadiationSimulation simulation, RadiationSimulation.RowRange envelope) {
      _moistureReady = false;
      // Radiation rows plus margin, and rows whose banks are still clearing
      // (native levels fall after the water turns clean).
      var rows = Intersect(RadiationSimulation.RowRange.Union(simulation.RadiationRows.Expand(FieldRowMargin, 0, _ySize - 1), _bankRows),
        envelope.Clamp(0, _ySize - 1));
      // The kernels carry their candidates from tick to tick; after a tick
      // without them, start the field from zero.
      bool continuous = !_computedRows.Empty;
      for (int y = _fieldRows.Lo; y <= _fieldRows.Hi; y++)
        if (!continuous || y < rows.Lo || y > rows.Hi) ClearRow(y);
      _fieldRows = rows;
      _computedRows = RadiationSimulation.RowRange.None;
      if (rows.Empty) return;
      int layers = simulation.Layers;
      var native = _waterMap.WaterColumns.AsSpan;
      // Both arrays only grow (ThreadSafeWaterMap.Update, RadiationSimulation.EnsureLayers).
      if (native.Length != layers * _vs)
        throw new InvalidOperationException("Radiation soil: thread-safe water map layers differ from the mirrored radiation layers");
      if (_soilWater.Length != native.Length) _soilWater = new ReadOnlyWaterColumn[native.Length];
      BuildSoilShadow(simulation, native, rows.Expand(1, -1, _ySize));
      _scheduledRows = rows;
      if (simulation.TotalWaterRadiation > 0f) BuildMoistureShadow(simulation, native);
    }

    private void BuildSoilShadow(RadiationSimulation simulation, ReadOnlySpan<ReadOnlyWaterColumn> native, RadiationSimulation.RowRange rows) {
      var shadow = MemoryMarshal.Cast<ReadOnlyWaterColumn, WaterColumn>(_soilWater.AsSpan());
      var source = MemoryMarshal.Cast<ReadOnlyWaterColumn, WaterColumn>(native);
      var radiation = simulation.WaterRadiation; var water = simulation.WaterSnapshot;
      int layers = simulation.Layers;
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        int start = (y + 1) * _stride;
        for (int layer = 0; layer < layers; layer++) {
          int first = layer * _vs + start;
          for (int idx = first; idx < first + _stride; idx++) {
            var column = source[idx];
            float r = RadiationTuning.Detected(radiation[idx]);
            if (r > 0f) {
              RequireSameColumn(in column, in water[idx]);
              column.Contamination = KernelContamination(r, _minimumWaterContamination, _contaminationScaler);
            } else {
              column.Contamination = 0f;
            }
            shadow[idx] = column;
          }
        }
      }
    }

    // Water contamination the native soil kernel turns into the existing soil
    // target: (c - min) x scaler = min(1, WaterToSoilFactor x r) for r > 0.
    internal static float KernelContamination(float r, float minimumWaterContamination, float contaminationScaler) =>
      minimumWaterContamination + Mathf.Min(1f, r * RadiationTuning.WaterToSoilFactor) / contaminationScaler;

    // The native thread-safe columns with Contamination b + r.
    private void BuildMoistureShadow(RadiationSimulation simulation, ReadOnlySpan<ReadOnlyWaterColumn> native) {
      if (_moistureWater.Length != native.Length) _moistureWater = new ReadOnlyWaterColumn[native.Length];
      native.CopyTo(_moistureWater);
      var shadow = MemoryMarshal.Cast<ReadOnlyWaterColumn, WaterColumn>(_moistureWater.AsSpan());
      var counts = simulation.Counts; var radiation = simulation.WaterRadiation; var water = simulation.WaterSnapshot;
      var rows = simulation.RadiationRows.Clamp(0, _ySize - 1);
      bool any = false;
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        int rowStart = (y + 1) * _stride + 1;
        for (int x = 0; x < _xSize; x++) {
          int i = rowStart + x;
          for (int j = 0; j < counts[i]; j++) {
            int idx = j * _vs + i;
            float r = RadiationTuning.Detected(radiation[idx]);
            if (!(r > 0f)) continue;
            ref var column = ref shadow[idx];
            RequireSameColumn(in column, in water[idx]);
            RadiationMixing.RequireShares(column.Contamination, r, "the soil moisture shadow");
            column.Contamination += r;
            any = true;
          }
        }
      }
      _moistureReady = any;
    }

    // Prefix of SoilMoistureSimulationTaskStarter.StartTask (RadiationSoilPatches).
    internal void SubstituteMoistureColumns(ref ReadOnlyArray<ReadOnlyWaterColumn> waterColumns) {
      if (!_moistureReady) return;
      _moistureReady = false;
      if (waterColumns.AsSpan != _waterMap.WaterColumns.AsSpan)
        throw new InvalidOperationException("Radiation soil: native soil moisture no longer reads the thread-safe water map");
      if (waterColumns.AsSpan.Length != _moistureWater.Length)
        throw new InvalidOperationException("Radiation soil: thread-safe water map changed size after the moisture shadow was built");
      waterColumns = new ReadOnlyArray<ReadOnlyWaterColumn>(_moistureWater);
    }

    // The thread-safe copy equals the native columns RadiationSimulation
    // mirrored in this late tick (WaterSimulator.Tick, then ThreadSafeWaterMap.Tick).
    private static void RequireSameColumn(in WaterColumn threadSafe, in WaterColumn mirrored) {
      if (threadSafe.Floor != mirrored.Floor || threadSafe.Ceiling != mirrored.Ceiling)
        throw new InvalidOperationException("Radiation soil: thread-safe water columns differ from the mirrored radiation columns");
    }

    private void ClearRow(int y) {
      int start = (y + 1) * _stride;
      for (int layer = 0; layer < _terrainLayers; layer++) {
        int first = layer * _vs + start;
        Array.Clear(_levels, first, _stride); Array.Clear(_candidates, first, _stride);
        Array.Clear(_lastCandidates, first, _stride); Array.Clear(_changed, first, _stride);
      }
    }

    // Native SoilContaminationSimulator.Tick: ProcessActions, then
    // ProcessTerrainHeightChanges, with the same rules.
    private void ProcessTerrainActions() {
      foreach (var (type, value) in _actions) {
        switch (type) {
          case TerrainAction.Resize: Resize(value); break;
          case TerrainAction.MovedUp: MoveColumn(value, value - _vs); break;
          case TerrainAction.MovedDown: MoveColumn(value, value + _vs); break;
          case TerrainAction.Reset: _levels[value] = 0f; _candidates[value] = 0f; _lastCandidates[value] = 0f; _changed[value] = true; break;
          default: throw new ArgumentOutOfRangeException(nameof(type), type, "Unknown terrain action");
        }
      }
      _actions.Clear();
      foreach (var change in _heightChanges) {
        int height = change.SetTerrain ? change.To + 1 : change.From;
        if (!_terrainMap.TryGetIndexAtOrAboveCeiling(_mapIndex.CellToIndex(change.Coordinates), height, out int index)) continue;
        _changed[index] = true;
        if (change.SetTerrain) _levels[index] = _candidates[index] = Math.Max(0f, _levels[index] - _verticalCostModifier * (height - change.From));
      }
      _heightChanges.Clear();
    }

    private void Resize(int maxColumnCount) {
      int size = maxColumnCount * _vs;
      Array.Resize(ref _levels, size); Array.Resize(ref _candidates, size);
      Array.Resize(ref _lastCandidates, size); Array.Resize(ref _changed, size);
      _terrainLayers = maxColumnCount;
    }

    private void MoveColumn(int target, int source) {
      _levels[target] = _levels[source];
      _candidates[target] = _candidates[source];
      _lastCandidates[target] = _lastCandidates[source];
      _changed[target] = true;
    }

    private static RadiationSimulation.RowRange Intersect(RadiationSimulation.RowRange a, RadiationSimulation.RowRange b) {
      if (a.Empty || b.Empty) return RadiationSimulation.RowRange.None;
      var range = new RadiationSimulation.RowRange(Math.Max(a.Lo, b.Lo), Math.Min(a.Hi, b.Hi));
      return range.Empty ? RadiationSimulation.RowRange.None : range;
    }

    private enum TerrainAction { Resize, MovedUp, MovedDown, Reset }
  }

  internal readonly struct RadiationSoilPreparationTask : IParallelizerLoopTask {
    private readonly RadiationSoil _soil;
    public RadiationSoilPreparationTask(RadiationSoil soil) { _soil = soil; }
    public void Run(int y) => _soil.PrepareRow(y);
  }

  // Native members RadiationSoil reads directly (publicized at compile time,
  // private or internal in the shipped 1.1.2.8 assemblies).
  internal static class RadiationSoilNative {
    private const BindingFlags Fields = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;

    internal static void Verify() {
      var starter = typeof(SoilContaminationSimulationTaskStarter);
      RequireField(starter, "_waterColumnRetriever", typeof(WaterColumnRetriever));
      RequireField(starter, "_ceilingRetriever", typeof(CeilingRetriever));
      RequireField(starter, "_mapSize", typeof(Vector3Int));
      RequireField(starter, "_stride", typeof(int));
      RequireField(starter, "_verticalStride", typeof(int));
      foreach (var name in new[] { "_maximumSoilContamination", "_regularSpreadCost", "_diagonalSpreadCost", "_contaminationDecayRate",
          "_contaminationSpreadingRate", "_minimumWaterContamination", "_contaminationScaler", "_verticalCostModifier",
          "_contaminationThreshold", "_contaminationPositiveEqualizationRate", "_contaminationNegativeEqualizationRate" })
        RequireField(starter, name, typeof(float));
      Require(typeof(ContaminationCandidatesCountingTask).GetConstructor(new[] {
          typeof(WaterColumnRetriever), typeof(CeilingRetriever), typeof(float[]), typeof(ReadOnlyArray<byte>), typeof(ReadOnlyArray<ReadOnlyWaterColumn>),
          typeof(ReadOnlyArray<byte>), typeof(ReadOnlyArray<ReadOnlyTerrainColumn>), typeof(ReadOnlyArray<bool>), typeof(ReadOnlyArray<bool>),
          typeof(ReadOnlyArray<float>), typeof(int), typeof(int), typeof(int), typeof(float), typeof(float), typeof(float), typeof(float),
          typeof(float), typeof(float), typeof(float), typeof(float) }) != null,
        "ContaminationCandidatesCountingTask(WaterColumnRetriever, CeilingRetriever, float[], counts, water, terrain counts, terrain, barriers, above barriers, last candidates, 3 x int, 8 x float)");
      Require(typeof(ContaminationsUpdateTask).GetConstructor(new[] {
          typeof(float[]), typeof(bool[]), typeof(ReadOnlyArray<byte>), typeof(ReadOnlyArray<float>), typeof(int), typeof(int), typeof(int),
          typeof(float), typeof(float), typeof(float) }) != null,
        "ContaminationsUpdateTask(float[], bool[], terrain counts, candidates, 3 x int, 3 x float)");
      Require(Marshal.SizeOf<WaterColumn>() == Marshal.SizeOf<ReadOnlyWaterColumn>(), "WaterColumn and ReadOnlyWaterColumn share one layout (ThreadSafeWaterMap.Update casts them)");
    }

    private static void RequireField(Type type, string name, Type fieldType) =>
      Require(type.GetField(name, Fields)?.FieldType == fieldType, $"{type.Name}.{name} : {fieldType.Name}");

    internal static void Require(bool condition, string member) {
      if (!condition) throw new InvalidOperationException($"Radiation soil: native soil API changed; expected {member} (Timberborn 1.1.2.8)");
    }
  }

#if !UNITY_EDITOR
  // Harmony: the native soil moisture tasks see b + r as the water's
  // contamination (RadiationSoil.SubstituteMoistureColumns).
  internal static class RadiationSoilPatches {
    internal const string HarmonyId = "DeepFrontier.RadiationSoil";
    private static bool _patched;
    private static RadiationSoil _soil;

    internal static void Attach(RadiationSoil soil) {
      if (_soil != null) throw new InvalidOperationException("A radiation soil is already attached to the soil moisture simulation");
      if (!_patched) {
        Verify();
        new Harmony(HarmonyId).CreateClassProcessor(typeof(MoisturePatch)).Patch();
        _patched = true;
      }
      _soil = soil;
    }

    internal static void Detach(RadiationSoil soil) {
      if (_soil == soil) _soil = null;
    }

    // SoilMoistureSimulator.StartParallelTick passes _threadSafeWaterMap.WaterColumns
    // by `in` from a local (IL: stloc.3; ldloca.s 3), so the prefix replaces that
    // local for this call only.
    private static void Verify() {
      var method = AccessTools.Method(typeof(SoilMoistureSimulationTaskStarter), nameof(SoilMoistureSimulationTaskStarter.StartTask));
      RadiationSoilNative.Require(method != null && method.ReturnType == typeof(void), "SoilMoistureSimulationTaskStarter.StartTask(...) : void");
      var parameter = Array.Find(method.GetParameters(), p => p.Name == "waterColumns");
      RadiationSoilNative.Require(parameter != null && parameter.ParameterType == typeof(ReadOnlyArray<ReadOnlyWaterColumn>).MakeByRefType(),
        "SoilMoistureSimulationTaskStarter.StartTask(..., in ReadOnlyArray<ReadOnlyWaterColumn> waterColumns, ...)");
      RadiationSoilNative.Require(AccessTools.Method(typeof(SoilMoistureSimulator), nameof(SoilMoistureSimulator.StartParallelTick)) != null,
        "SoilMoistureSimulator.StartParallelTick()");
    }

    [HarmonyPatch(typeof(SoilMoistureSimulationTaskStarter), nameof(SoilMoistureSimulationTaskStarter.StartTask))]
    private static class MoisturePatch {
      private static void Prefix(ref ReadOnlyArray<ReadOnlyWaterColumn> waterColumns) => _soil?.SubstituteMoistureColumns(ref waterColumns);
    }
  }
#endif
}
