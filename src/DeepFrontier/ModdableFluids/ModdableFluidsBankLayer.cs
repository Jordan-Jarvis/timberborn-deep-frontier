#if DEEP_FRONTIER_MODDABLE_FLUIDS
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using DeepFrontier.Scripts.Radiation;
using Timberborn.BlueprintSystem;
using Timberborn.Common;
using Timberborn.MapIndexSystem;
using Timberborn.Multithreading;
using Timberborn.SingletonSystem;
using Timberborn.SoilBarrierSystem;
using Timberborn.SoilContaminationSystem;
using Timberborn.TerrainSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using UnityEngine;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>
  /// The bank layer of the Moddable Fluids build: RadiationSoil's part 2, unchanged in its rules. The native soil
  /// contamination kernels (ContaminationCandidatesCountingTask, ContaminationsUpdateTask) run on a shadow of the
  /// thread-safe water columns whose contamination is RadiationSoil.KernelContamination of the radioactive share, on
  /// the rows near radioactive water and the rows whose banks are still clearing, with the native per-tick parameters
  /// of SoilContaminationSimulationTaskStarter. The levels they compute are the bank layer: readers see the higher of
  /// stored soil and bank, and the bank is never written into the soil. The shares come from the soil field's
  /// published pass (Moddable Fluids state after Deep Frontier's rules) instead of RadiationSimulation's arrays.
  /// The native moisture shadow (RadiationSoil part 1) is not here: Moddable Fluids owns soil moisture and applies
  /// radioactive water's irrigation policy.
  ///
  /// Order, as in the shipped build: <see cref="Tick"/> (before the late tick) takes what the last parallel tick
  /// computed; <see cref="Update"/> (ModdableFluidsRadiation's late tick) turns it into the bank layer;
  /// <see cref="Prepare"/> (same late tick, after the kill check) builds the shadow; <see cref="StartParallelTick"/>
  /// runs the kernels.
  /// </summary>
  public sealed class ModdableFluidsBankLayer : IRadiationBankLayer, IPostLoadableSingleton, ITickableSingleton, IParallelTickableSingleton {
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
    private float[] _bank = new float[0];
    private RadiationSimulation.RowRange _bankRows = RadiationSimulation.RowRange.None;
    private WaterColumnRetriever _waterColumnRetriever;
    private CeilingRetriever _ceilingRetriever;
    private float _maximumSoilContamination, _regularSpreadCost, _diagonalSpreadCost, _decayRate, _spreadingRate,
      _minimumWaterContamination, _contaminationScaler, _verticalCostModifier, _threshold, _positiveRate, _negativeRate;
    private float[] _levels, _candidates, _lastCandidates;
    private bool[] _changed;
    private int _terrainLayers;
    private readonly List<(TerrainAction Type, int Value)> _actions = new List<(TerrainAction, int)>();
    private readonly List<TerrainHeightChange> _heightChanges = new List<TerrainHeightChange>();
    private ReadOnlyWaterColumn[] _soilWater = new ReadOnlyWaterColumn[0];
    private RadiationSimulation.RowRange _fieldRows = RadiationSimulation.RowRange.None;
    private RadiationSimulation.RowRange _scheduledRows = RadiationSimulation.RowRange.None;
    private RadiationSimulation.RowRange _ranRows = RadiationSimulation.RowRange.None;
    private RadiationSimulation.RowRange _computedRows = RadiationSimulation.RowRange.None;

    public ModdableFluidsBankLayer(MapIndexService mapIndex, IThreadSafeWaterMap waterMap, IThreadSafeColumnTerrainMap terrainMap,
        ITerrainService terrainService, SoilBarrierMap barriers, SoilContaminationSimulationTaskStarter nativeStarter,
        ISpecService specService, IParallelizer parallelizer, IDayNightCycle dayNightCycle) {
      _mapIndex = mapIndex; _waterMap = waterMap; _terrainMap = terrainMap; _terrainService = terrainService;
      _barriers = barriers; _nativeStarter = nativeStarter; _specService = specService; _parallelizer = parallelizer;
      _dayNightCycle = dayNightCycle;
    }

    /// <summary>The native fall of a contaminated level per game hour (RadiationSoil._washoutPerHour); set in PostLoad.</summary>
    public float WashoutPerHour { get; private set; } = float.NaN;

    // RadiationSoil.Load and PostLoad, without the moisture hook.
    public void PostLoad() {
      _stride = _mapIndex.Stride; _vs = _mapIndex.VerticalStride; _xSize = _mapIndex.TerrainSize.x; _ySize = _mapIndex.TerrainSize.y;
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
      WashoutPerHour = _negativeRate / _dayNightCycle.FixedDeltaTimeInHours;
      if (!(WashoutPerHour > 0f) || float.IsInfinity(WashoutPerHour))
        throw new InvalidOperationException("Radiation soil: native negative equalization rate " + _negativeRate + " gives no washout");
      if (!(_minimumWaterContamination >= 0f && _minimumWaterContamination < 1f) || !(_contaminationScaler > 0f))
        throw new InvalidOperationException("Radiation soil: native MinimumWaterContamination " + _minimumWaterContamination + " leaves no contamination range");
      int maxRange = _specService.GetSingleSpec<SoilContaminationSimulatorSpec>().MaxRangeFromSource;
      if (RadiationTuning.RangeMargin + RadiationSoil.FieldRowMargin < maxRange + 1)
        throw new InvalidOperationException("Radiation soil: rows RangeMargin + FieldRowMargin must cover the native reach " + maxRange + " + 1");
      _terrainLayers = _terrainMap.MaxColumnCount;
      int size = _terrainLayers * _vs;
      _levels = new float[size]; _candidates = new float[size]; _lastCandidates = new float[size]; _changed = new bool[size];
      _terrainService.TerrainHeightChanged += (_, e) => _heightChanges.Add(e.Change);
      _terrainMap.MaxTerrainColumnCountChanged += (_, i) => _actions.Add((TerrainAction.Resize, i));
      _terrainMap.ColumnMovedUp += (_, i) => _actions.Add((TerrainAction.MovedUp, i));
      _terrainMap.ColumnMovedDown += (_, i) => _actions.Add((TerrainAction.MovedDown, i));
      _terrainMap.ColumnReset += (_, i) => _actions.Add((TerrainAction.Reset, i));
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
      var prepare = new BankPreparationTask(this);
      var candidates = new ContaminationCandidatesCountingTask(_waterColumnRetriever, _ceilingRetriever, _candidates, counts,
        new ReadOnlyArray<ReadOnlyWaterColumn>(_soilWater), terrainCounts, _terrainMap.TerrainColumns, _barriers.ContaminationBarriers,
        _barriers.AboveMoistureBarriers, new ReadOnlyArray<float>(_lastCandidates), _xSize, _stride, _vs, _maximumSoilContamination,
        _regularSpreadCost, _diagonalSpreadCost, _decayRate, _spreadingRate, _minimumWaterContamination, _contaminationScaler, _verticalCostModifier);
      var update = new ContaminationsUpdateTask(_levels, _changed, terrainCounts, new ReadOnlyArray<float>(_candidates), _xSize, _stride, _vs,
        _threshold, _positiveRate, _negativeRate);
      _parallelizer.Schedule(rows.Lo, rows.Hi + 1, 1, in prepare)
        .ContinueWith(rows.Lo, rows.Hi + 1, 1, in candidates)
        .ContinueWith(rows.Lo, rows.Hi + 1, 5, in update);
    }

    internal void PrepareRow(int y) {
      int start = (y + 1) * _stride;
      for (int layer = 0; layer < _terrainLayers; layer++) {
        int first = layer * _vs + start;
        Array.Copy(_candidates, first, _lastCandidates, first, _stride);
        Array.Clear(_changed, first, _stride);
      }
    }

    /// <summary>Late tick (RadiationSoil.Exchange's first step): the levels the last parallel tick computed become the bank layer.</summary>
    public void Update() {
      ProcessTerrainActions();
      var counts = _waterMap.ColumnCounts.AsSpan; var water = _waterMap.WaterColumns.AsSpan;
      if (_bank.Length != water.Length) Array.Resize(ref _bank, water.Length);
      var computed = _computedRows.Clamp(0, _ySize - 1);
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

    public float BankAt(Vector3Int columnCell) {
      if (_bank.Length == 0) return 0f;
      int i = _mapIndex.CellToIndex(new Vector2Int(columnCell.x, columnCell.y));
      for (int j = 0; j < _waterMap.ColumnCount(i); j++) {
        int idx = j * _vs + i;
        if (_waterMap.ColumnFloor(idx) == columnCell.z) return idx < _bank.Length ? _bank[idx] : 0f;
      }
      return 0f;
    }

    /// <summary>Column cells (x, y, floor) whose bank level is at or above <paramref name="level"/>.</summary>
    public void CollectAtOrAbove(float level, HashSet<Vector3Int> into) {
      var counts = _waterMap.ColumnCounts.AsSpan; var water = _waterMap.WaterColumns.AsSpan;
      var rows = _bankRows.Clamp(0, _ySize - 1);
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        int rowStart = (y + 1) * _stride + 1;
        for (int x = 0; x < _xSize; x++) {
          int i = rowStart + x;
          for (int j = 0; j < counts[i]; j++) {
            int idx = j * _vs + i;
            if (idx < _bank.Length && _bank[idx] >= level) into.Add(new Vector3Int(x, y, water[idx].Floor));
          }
        }
      }
    }

    /// <summary>
    /// Late tick, after the kill check (RadiationSoil.Prepare): the rows and soil shadow for the next parallel tick,
    /// from the radioactive shares of the soil field's last pass.
    /// </summary>
    public void Prepare(RadiationFieldSnapshot pass) {
      var radiationRows = RadiationSimulation.RowRange.None;
      foreach (var key in pass.Water.Keys) radiationRows.Include(key.y);
      radiationRows = radiationRows.Expand(RadiationTuning.RangeMargin, 0, _ySize - 1);
      var rows = RadiationSimulation.RowRange.Union(radiationRows.Expand(RadiationSoil.FieldRowMargin, 0, _ySize - 1), _bankRows).Clamp(0, _ySize - 1);
      bool continuous = !_computedRows.Empty;
      for (int y = _fieldRows.Lo; y <= _fieldRows.Hi; y++)
        if (!continuous || y < rows.Lo || y > rows.Hi) ClearRow(y);
      _fieldRows = rows;
      _computedRows = RadiationSimulation.RowRange.None;
      if (rows.Empty) return;
      var native = _waterMap.WaterColumns.AsSpan;
      if (_soilWater.Length != native.Length) _soilWater = new ReadOnlyWaterColumn[native.Length];
      BuildSoilShadow(pass, native, rows.Expand(1, -1, _ySize));
      _scheduledRows = rows;
    }

    // RadiationSoil.BuildSoilShadow, with the share of the column with that floor in the pass.
    private void BuildSoilShadow(RadiationFieldSnapshot pass, ReadOnlySpan<ReadOnlyWaterColumn> native, RadiationSimulation.RowRange rows) {
      var shadow = MemoryMarshal.Cast<ReadOnlyWaterColumn, WaterColumn>(_soilWater.AsSpan());
      var source = MemoryMarshal.Cast<ReadOnlyWaterColumn, WaterColumn>(native);
      var counts = _waterMap.ColumnCounts.AsSpan;
      int layers = native.Length / _vs;
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        int start = (y + 1) * _stride;
        for (int layer = 0; layer < layers; layer++) {
          int first = layer * _vs + start;
          for (int idx = first; idx < first + _stride; idx++) {
            var column = source[idx];
            int i = idx - layer * _vs, x = i - start - 1;
            float r = 0f;
            if (y >= 0 && y < _ySize && x >= 0 && x < _xSize && layer < counts[i] && pass.Water.TryGetValue(new Vector3Int(x, y, column.Floor), out float share))
              r = RadiationTuning.Detected(share);
            column.Contamination = r > 0f ? RadiationSoil.KernelContamination(r, _minimumWaterContamination, _contaminationScaler) : 0f;
            shadow[idx] = column;
          }
        }
      }
    }

    private void ClearRow(int y) {
      int start = (y + 1) * _stride;
      for (int layer = 0; layer < _terrainLayers; layer++) {
        int first = layer * _vs + start;
        Array.Clear(_levels, first, _stride); Array.Clear(_candidates, first, _stride);
        Array.Clear(_lastCandidates, first, _stride); Array.Clear(_changed, first, _stride);
      }
    }

    // Native SoilContaminationSimulator.Tick: ProcessActions, then ProcessTerrainHeightChanges, with the same rules.
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

    private enum TerrainAction { Resize, MovedUp, MovedDown, Reset }

    private readonly struct BankPreparationTask : IParallelizerLoopTask {
      private readonly ModdableFluidsBankLayer _bank;
      public BankPreparationTask(ModdableFluidsBankLayer bank) { _bank = bank; }
      public void Run(int y) => _bank.PrepareRow(y);
    }
  }
}
#endif
