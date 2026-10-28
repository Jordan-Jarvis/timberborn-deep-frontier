using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Common;
using Timberborn.MapIndexSystem;
using Timberborn.NaturalResourcesLifecycle;
using Timberborn.Multithreading;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.Radiation {
  // Radioactive water: one fluid with the native water. Every native column
  // holds fresh + bad + radioactive water; b is native Contamination, r is
  // _radiation[idx] (see RadiationMixing for every native path that changes
  // the shares). Soil radiation lies under each column.
  //
  // r moves in exact lockstep with the native water (RadiationLockstep): after
  // each native substep the native contamination kernels run on a shadow
  // column array whose Contamination slot carries r. Water the native adds
  // outside the kernels (sources, water changes) is mixed in by the same
  // formulas as contamination; AddRadioactiveWater adds r = 1 water through
  // the native water change path. Decay, soil uptake and geometry changes run
  // here in the late Tick, after FinishParallelTick.
  //
  // Native-safe points other than Tick: Save (after GameSaver's FinishFullTick,
  // which also applies queued geometry modifications) and UpdateSingleton,
  // which applies a loaded save before the first tick (saved games load paused).
  //
  // Internal native types and private members are compiled against the
  // publicized ModsBuild assemblies. Timberborn's Mono 6.13 allows that only
  // because DeepFrontier.asmdef has "allowUnsafeCode": true (SkipVerification;
  // outputs/radiation-mono-access-probe).
  public sealed class RadiationSimulation : IRadiationService, ILoadableSingleton, ITickableSingleton, ILateTickable,
      ISaveableSingleton, IUnloadableSingleton, IUpdatableSingleton {
    private static readonly SingletonKey RadiationKey = new SingletonKey("DeepFrontier.Radiation");
    private static readonly PropertyKey<int> VersionKey = new PropertyKey<int>("Version");
    private static readonly ListKey<Vector3Int> CellsKey = new ListKey<Vector3Int>("Cells");
    private static readonly ListKey<float> SludgeKey = new ListKey<float>("Sludge");                 // version 2 only
    private static readonly ListKey<float> WaterRadiationKey = new ListKey<float>("WaterRadiation");
    private static readonly ListKey<float> SoilKey = new ListKey<float>("Soil");
    private static readonly ListKey<int> SourceIdsKey = new ListKey<int>("SourceIds");
    private static readonly ListKey<Vector3Int> SourceCellsKey = new ListKey<Vector3Int>("SourceCells");
    private static readonly ListKey<float> SourceRatesKey = new ListKey<float>("SourceRates");
    private static readonly ListKey<float> SourceHoursKey = new ListKey<float>("SourceHours");
    private static readonly PropertyKey<int> NextSourceIdKey = new PropertyKey<int>("NextSourceId");
    private static readonly PropertyKey<float> HourAccumulatorKey = new PropertyKey<float>("HourAccumulator");
    // Present (true) only in a native exception save written mid-tick from the
    // last completed tick's snapshot (WriteSnapshot); optional, so version 3 stays.
    private static readonly PropertyKey<bool> SnapshotKey = new PropertyKey<bool>("LastCompletedTickSnapshot");
    // Version 3: one fluid. Version 2 (build 122, sludge as its own fluid) is
    // converted on load; version 1 never loaded (build 121 crashed on every
    // game-scene load, and builds up to 120 had no radiation).
    private const int SaveVersion = 3;
    private const int SludgeSaveVersion = 2;

    private readonly MapIndexService _mapIndex;
    private readonly WaterSimulator _waterSimulator;
    private readonly WaterSourceRegistry _waterSources;
    private readonly IWaterService _waterService;
    private readonly IThreadSafeWaterMap _waterMap;
    private readonly IParallelizer _parallelizer;
    private readonly ISpecService _specService;
    private readonly ITickService _tickService;
    private readonly IDayNightCycle _dayNightCycle;
    private readonly ITickableSingletonService _tickableSingletons;
    private readonly TickOnlyArrayService _tickOnlyArrays;
    private readonly ISingletonLoader _singletonLoader;
    private readonly IBlockService _blockService;
    private readonly RadiationSoil _soilExchange;   // soil vs water and the native-pattern field (RadiationSoil.cs)

    private WaterSimulatorSpec _spec;
    private ImmutableArray<int> _neighborOffsets;
    private int _stride, _vs, _maxIndex, _xSize, _ySize, _layers;

    private byte[] _counts;           // mirrored native column counts
    private WaterColumn[] _water;     // mirrored native columns (geometry each Tick, shadow during the parallel tick)
    private float[] _radiation, _radBuffer, _soil, _soilNext;
    private float[] _radPrevious;     // r after the last late tick's cutoff (Rescan); not saved
    private bool[] _irradiatedGround;  // slot already checked while irradiated (KillOnIrradiatedGround); not saved
    private RowRange _irradiatedRows = RowRange.None;
    private byte[] _radDiffCount;
    private bool[] _isSourceCell;
    private Diffusions[] _radBaseDiff;
    private List<TargetedDiffusion>[] _radTargeted;
    private OldColumn[] _oldColumns = new OldColumn[1];
    private bool[] _oldSoilMoved = new bool[1];

    private RowRange _radRows = RowRange.None, _soilRows = RowRange.None, _pendingRows = RowRange.None, _sourceRows = RowRange.None;
    // Rows where the last parallel tick mixed AddRadioactiveWater water in (MixWaterChanges). The next
    // Tick scans them, so radioactive water added where the envelope did not reach (a world without any
    // radiation yet) is tracked from then on instead of staying outside every scan (all-buildings run b164:
    // 20.8 radioactive volume added to two dry pools read 0).
    private RowRange _mixedRows = RowRange.None;
    private readonly WaterFlow[] _noFlows = new WaterFlow[0];
    private float _hourAccumulator;
    private readonly List<(Vector3Int Cell, float Amount)> _pendingSoil = new List<(Vector3Int, float)>();
    private readonly List<ContinuousSource> _sources = new List<ContinuousSource>();
    private int _nextSourceId = 1;
    private LoadedState _loaded;
    private bool _ticked;
    // Set when the native water simulation first schedules a substep. Native
    // ParalleTicklIsFinished stays false until the first parallel tick ends, so
    // before then it cannot tell "mid-tick" from "no tick yet".
    private bool _parallelTickScheduled;
    // True from the start of Tick until its snapshot is taken: an exception
    // thrown inside Tick leaves it set, so an exception save uses the snapshot.
    private bool _inTick;
    // The last completed tick's saved state (TakeSnapshot, end of every Tick,
    // main thread): cells with r or soil, and the main-thread values.
    private readonly List<Vector3Int> _snapCells = new List<Vector3Int>();
    private readonly List<float> _snapRadiation = new List<float>(), _snapSoil = new List<float>();
    private readonly List<ContinuousSource> _snapSources = new List<ContinuousSource>();
    private int _snapNextSourceId = 1;
    private float _snapHourAccumulator;
    private bool _snapTaken;

    // Radioactive water adds: queued with the native AddCleanWater call, and
    // promoted together with the native queue (postfix of WaterChangeService.Tick).
    private List<RadioactiveAdd> _queuedAdds = new List<RadioactiveAdd>(), _activeAdds = new List<RadioactiveAdd>();
    // Per-tick worker results, read in Tick after FinishParallelTick.
    private readonly Dictionary<Vector3Int, float> _removedRadioactive = new Dictionary<Vector3Int, float>();
    private readonly List<(Vector3Int Cell, float Volume)> _lostRadioactive = new List<(Vector3Int, float)>();
    private readonly Dictionary<Vector3Int, RadioactiveSludgeIntake> _intakes = new Dictionary<Vector3Int, RadioactiveSludgeIntake>();
    // Radioactive share per source: springs (main thread), published each Tick for the workers.
    private readonly Dictionary<IWaterSource, float> _springs = new Dictionary<IWaterSource, float>();
    private Dictionary<IWaterSource, float> _publishedSprings = new Dictionary<IWaterSource, float>();
    private bool _springsChanged;
    private float _tideShare, _publishedTideShare;
    // Worker-side scratch (tasks run one after another).
    private readonly List<SourceCell> _sourceCells = new List<SourceCell>();
    private readonly Dictionary<int, ChangeState> _changeStates = new Dictionary<int, ChangeState>();

    public float TotalWaterRadiation { get; private set; }
    public bool SavedStatePending => _loaded != null;
    public float WaterPerStrengthHour => _tickService.TickIntervalInSeconds / _dayNightCycle.FixedDeltaTimeInHours;
    // Columns where the native kernels pushed b + r over 1 (RadiationMixing.KernelExcess); for acceptance.
    private int _kernelCorrections;
    internal int KernelCorrections => _kernelCorrections;

    // Read-only views for the renderer (main thread).
    internal int Layers => _layers;
    internal int Stride => _stride;
    internal int VerticalStride => _vs;
    internal int XSize => _xSize;
    internal int YSize => _ySize;
    internal byte[] Counts => _counts;
    internal float[] SoilRadiation => _soil;   // persistent soil only (saved); readers use SoilAt
    // Soil radiation as everything sees it: the persistent soil or the
    // native-pattern bank layer next to radioactive water, whichever is higher.
    internal float SoilAt(int idx) => Mathf.Max(_soil[idx], _soilExchange.BankAt(idx));
    internal float[] WaterRadiation => _radiation;
    internal WaterColumn[] WaterSnapshot => _water;
    internal RowRange VisibleRows => RowRange.Union(_soilRows, _radRows);
    internal RowRange RadiationRows => _radRows;
    internal int StateVersion { get; private set; }
    internal bool HasTicked => _ticked;

    public RadiationSimulation(MapIndexService mapIndex, WaterSimulator waterSimulator, WaterSourceRegistry waterSources,
        IWaterService waterService, IThreadSafeWaterMap waterMap, IParallelizer parallelizer, ISpecService specService,
        ITickService tickService, IDayNightCycle dayNightCycle, ITickableSingletonService tickableSingletons, TickOnlyArrayService tickOnlyArrays,
        ISingletonLoader singletonLoader, IBlockService blockService, RadiationSoil soilExchange) {
      _mapIndex = mapIndex; _waterSimulator = waterSimulator; _waterSources = waterSources; _waterService = waterService;
      _waterMap = waterMap; _parallelizer = parallelizer; _specService = specService; _tickService = tickService;
      _dayNightCycle = dayNightCycle; _tickableSingletons = tickableSingletons; _singletonLoader = singletonLoader;
      _tickOnlyArrays = tickOnlyArrays;
      _blockService = blockService; _soilExchange = soilExchange;
    }

    public void Load() {
      // The native exception saver marks itself here (see Save); verify the member now, not mid-crash.
      if (typeof(TickOnlyArrayService).GetField("_forceAllowAccess", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public
          | System.Reflection.BindingFlags.NonPublic)?.FieldType != typeof(bool))
        throw new InvalidOperationException("Radiation: native TickOnlyArrayService._forceAllowAccess (bool) changed (Timberborn 1.1.2.8)");
      _spec = _specService.GetSingleSpec<WaterSimulatorSpec>();
      _stride = _mapIndex.Stride;
      _vs = _mapIndex.VerticalStride;
      _maxIndex = _mapIndex.MaxIndex;
      _xSize = _mapIndex.TotalSize.x;
      _ySize = _mapIndex.TotalSize.y;
      if (_xSize != _mapIndex.TerrainSize.x || _ySize != _mapIndex.TerrainSize.y || _stride != _xSize + 2 * MapIndexService.Margin)
        throw new InvalidOperationException("Radiation simulation expects the native padded map index layout of 1.1.2.8");
      _neighborOffsets = new[] { -_stride, -1, _stride, 1 }.ToImmutableArray();
      _counts = new byte[_maxIndex];
      _radBaseDiff = new Diffusions[_maxIndex];
      _radTargeted = new List<TargetedDiffusion>[_maxIndex];
      for (int i = 0; i < _maxIndex; i++) _radTargeted[i] = new List<TargetedDiffusion>(0);
      if (_singletonLoader.TryGetSingleton(RadiationKey, out var loader)) {
        _loaded = LoadedState.Read(loader);
        // Sources and counters do not depend on native geometry.
        _sources.AddRange(_loaded.Sources);
        _nextSourceId = _loaded.NextSourceId;
        _hourAccumulator = _loaded.HourAccumulator;
        foreach (var source in _sources)
          if (source.Id >= _nextSourceId) throw new InvalidOperationException("Saved radiation source id is not below NextSourceId");
      }
#if !UNITY_EDITOR
      RadiationLockstep.Attach(this);
#endif
    }

    public void Unload() {
#if !UNITY_EDITOR
      RadiationLockstep.Detach(this);
#endif
    }

    // ---------------------------------------------------------------- tick

    public void Tick() {
      _inTick = true;
      _ticked = true;
      float hours = _dayNightCycle.FixedDeltaTimeInHours;
      EnsureLayers(_waterSimulator.MaxColumnCount);
      var nativeCounts = _waterSimulator.ColumnCounts;
      var nativeColumns = _waterSimulator.WaterColumns;
      if (_loaded != null) ApplyLoaded(nativeCounts, nativeColumns);
      PublishSourceShares();
      EmitSources(hours);
      CreditIntakes();

      var envelope = Envelope();
      _pendingRows = RowRange.None;
      _mixedRows = RowRange.None;
      if (envelope.Empty) { TakeSnapshot(); return; }
      SyncGeometry(envelope, nativeCounts, nativeColumns);
      ApplyPendingSoil();
      if (!_radRows.Empty) RunInteraction(hours, nativeColumns);
      _soilExchange.Exchange(this, hours, envelope);
      Rescan(envelope, nativeColumns);
      KillOnIrradiatedGround();
      _soilExchange.Prepare(this, envelope);
      _hourAccumulator += hours;
      if (_hourAccumulator >= 1f) {
        if (!_soilRows.Empty) HourlySoilPass(_hourAccumulator);
        _hourAccumulator = 0f;
      }
      StateVersion++;
      TakeSnapshot();
    }

    // End of Tick: the state a save would write, kept for the native exception
    // saver, which can arrive while the lockstep tasks of the next parallel
    // tick are still writing _radiation and _soil (worker threads). Cells with
    // radiation or soil only; lists are reused.
    private void TakeSnapshot() {
      _snapCells.Clear(); _snapRadiation.Clear(); _snapSoil.Clear();
      var rows = RowRange.Union(_radRows, _soilRows).Clamp(0, _ySize - 1);
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        int rowStart = (y + 1) * _stride + 1;
        for (int x = 0; x < _xSize; x++) {
          int i = rowStart + x;
          for (int j = 0; j < _counts[i]; j++) {
            int idx = j * _vs + i;
            if (_radiation[idx] <= 0f && _soil[idx] <= 0f) continue;
            _snapCells.Add(new Vector3Int(x, y, _water[idx].Floor)); _snapRadiation.Add(_radiation[idx]); _snapSoil.Add(_soil[idx]);
          }
        }
      }
      _snapSources.Clear(); _snapSources.AddRange(_sources);
      _snapNextSourceId = _nextSourceId;
      _snapHourAccumulator = _hourAccumulator;
      _snapTaken = true;
      _inTick = false;
    }

    // Radioactive water sources are part of the envelope, so their columns are
    // mirrored and the lockstep runs where they add water.
    private RowRange Envelope() =>
      RowRange.Union(RowRange.Union(RowRange.Union(_radRows, _soilRows), RowRange.Union(_pendingRows, _sourceRows)), _mixedRows)
        .Expand(RadiationTuning.GeometrySyncMargin, -1, _ySize);

    // Saved games load paused; apply the saved cells on the first frame, after
    // every PostLoad (WaterSimulator.PostLoad has processed loaded obstacles).
    public void UpdateSingleton() {
      if (_loaded == null) return;
      if (_ticked) throw new InvalidOperationException("Loaded radiation state is still pending after the first tick");
      EnsureLayers(_waterSimulator.MaxColumnCount);
      var nativeColumns = _waterSimulator.WaterColumns;
      ApplyLoaded(_waterSimulator.ColumnCounts, nativeColumns);
      var envelope = Envelope();
      if (!envelope.Empty) Rescan(envelope, nativeColumns);
      StateVersion++;
      TakeSnapshot();   // the applied save is the last completed state until the first tick
    }

    // Decay of radioactive water (main thread). The soil exchange follows in
    // RadiationSoil.Exchange.
    private void RunInteraction(float hours, ReadOnlySpan<WaterColumn> nativeColumns) {
      var rows = _radRows.Clamp(0, _ySize - 1);
      float decay = RadiationTuning.DecayPerHour(RadiationTuning.RadiationHalfLifeDays) * hours;
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        int rowStart = (y + 1) * _stride + 1;
        for (int x = 0; x < _xSize; x++) {
          int i = rowStart + x;
          for (int j = 0; j < _counts[i]; j++) {
            int idx = j * _vs + i;
            float radiation = _radiation[idx];
            if (!(radiation > 0f)) continue;
            radiation -= radiation * decay;
            if (radiation < RadiationTuning.MinWaterRadiation) radiation = 0f;
            _radiation[idx] = radiation;
            RadiationMixing.RequireShares(nativeColumns[idx].Contamination, radiation, "the late tick");
          }
        }
      }
    }

    // ------------------------------------------------------------- lockstep

    // Called by RadiationLockstep inside the native StartParallelTick, once per
    // native substep, after the native substep's last task (the water sources).
    internal ParallelizerHandle ScheduleLockstepSubstep(WaterSimulationTaskStarter starter,
        in WaterSimulationTaskStarter.SimulationParameters native, ParallelizerHandle after) {
      _parallelTickScheduled = true;
      if (_layers == 0 || _radRows.Empty) return after;
      if (native.WaterColumns.Length != _layers * _vs || native.Outflows.Length != _layers * _vs)
        throw new InvalidOperationException("Radiation lockstep: native column arrays differ from the mirrored layer count");
      var rows = _radRows.Clamp(0, _ySize - 1);
      var outer = _radRows.Expand(1, 0, _ySize - 1);
      var copyRows = _radRows.Expand(2, -1, _ySize);
      var copy = new RadiationShadowCopyTask(this, native.WaterColumns, native.EvaporationModifiers, starter._deltaTime);
      var clear = new ClearBuffersTask(_radBuffer, _radDiffCount, _noFlows, _radBaseDiff);
      var simulate = new SimulateContaminationTask(starter._flowLimitCalculator, starter._waterFlowRetriever, _radBuffer, _radBaseDiff,
        _radDiffCount, _radTargeted, native.WaterColumnCounts, new ReadOnlyArray<WaterColumn>(_water),
        new ReadOnlyArray<ColumnOutflows>(native.Outflows), native.LimitedDirections, native.HeightLimits, _xSize, _stride, _vs,
        starter._deltaTime, starter._overflowPressureFactor, 1f, starter._diffusionOutflowLimit, starter._diffusionDepthLimit);
      var update = new UpdateContaminationTask(_water, native.WaterColumnCounts, new ReadOnlyArray<float>(_radBuffer),
        new ReadOnlyArray<Diffusions>(_radBaseDiff), new ReadOnlyArray<byte>(_radDiffCount),
        new ReadOnlyArray<List<TargetedDiffusion>>(_radTargeted), _xSize, _stride, _vs, starter._deltaTime, 1f, starter._diffusionRate);
      var harvest = new RadiationHarvestTask(this, native.WaterColumns);
      // Native order: kernels, then the sources mix in. This chain runs after
      // the sources, so source cells get their pre-source state back first.
      var restore = new RadiationSourceStateTask(this, native.WaterColumns, restore: true);
      var mix = new RadiationSourceStateTask(this, native.WaterColumns, restore: false);
      return _parallelizer.Schedule(copyRows.Lo + 1, copyRows.Hi + 2, 1, in copy, after)
        .ContinueWith(in restore)
        .ContinueWith(in clear)
        .ContinueWith(outer.Lo, outer.Hi + 1, 1, in simulate)
        .ContinueWith(rows.Lo, rows.Hi + 1, 3, in update)
        .ContinueWith(rows.Lo, rows.Hi + 1, 1, in harvest)
        .ContinueWith(in mix);
    }

    // Copy task, one row (padding rows included): radioactive volume the
    // native evaporation removed since the last copy goes into the soil, then
    // the shadow takes the native column with r in Contamination.
    internal void CopyRow(int row, WaterColumn[] native, ReadOnlyArray<float> evaporation, float deltaTime) {
      int start = row * _stride;
      for (int layer = 0; layer < _layers; layer++) {
        int first = layer * _vs + start;
        for (int idx = first; idx < first + _stride; idx++) {
          float radiation = _radiation[idx];
          if (radiation > 0f) {
            ref readonly var before = ref _water[idx];
            float evaporated = RadiationMixing.EvaporatedVolume(before.WaterDepth, before.Overflow, evaporation[idx], deltaTime,
              _spec.FastEvaporationDepthThreshold, _spec.FastEvaporationSpeed, _spec.NormalEvaporationSpeed);
            if (evaporated > 0f) Deposit(idx, radiation * evaporated);
          }
          var column = native[idx];
          column.Contamination = radiation;
          _water[idx] = column;
        }
      }
    }

    internal void HarvestRow(int y, WaterColumn[] native) {
      int rowStart = (y + 1) * _stride + 1;
      for (int x = 0; x < _xSize; x++) {
        int i = rowStart + x;
        for (int j = 0; j < _counts[i]; j++) {
          int idx = j * _vs + i;
          float radiation = _water[idx].Contamination;
          if (!_isSourceCell[idx] && radiation > 0f) {
            float bad = native[idx].Contamination;
            radiation = RadiationMixing.KernelExcess(bad, radiation, out float excess);
            if (excess > 0f) { Deposit(idx, excess * EffectiveDepth(in native[idx])); System.Threading.Interlocked.Increment(ref _kernelCorrections); }
            RadiationMixing.RequireShares(bad, radiation, "the contamination kernels");
          }
          _radiation[idx] = radiation;
        }
      }
    }

    internal float EffectiveDepth(in WaterColumn column) => column.WaterDepth + column.Overflow * _spec.OverflowPressureFactor;

    private void Deposit(int idx, float radioactiveVolume) {
      float soil = _soil[idx] + radioactiveVolume * RadiationTuning.SoilPerDepositedVolume;
      _soil[idx] = soil > 1f ? 1f : soil;
    }

    // Prefix of UpdateWaterSourcesTask.Run: each source cell before any source
    // adds water this substep, with the intended water and radioactive water.
    internal void RecordSourceCells(MapIndexService mapIndex, WaterColumn[] columns, ReadOnlyArray<byte> counts,
        ReadOnlyList<ThreadSafeWaterSource> sources, int verticalStride, float deltaTime) {
      _sourceCells.Clear();
      if (_layers == 0) return;
      for (int s = 0; s < sources.Count; s++) {
        var source = sources[s];
        float share = SourceShare(source);
        var coordinates = source.Coordinates;
        float water = deltaTime * source.CurrentStrength / coordinates.Length;
        for (int c = 0; c < coordinates.Length; c++) {
          var cell = coordinates[c];
          int idx = NativeColumnIndex(counts, columns, verticalStride, mapIndex.CellToIndex(new Vector2Int(cell.x, cell.y)), cell.z);
          if (idx < 0) continue;
          int k = _sourceCells.FindIndex(e => e.Index == idx);
          if (k < 0) { _sourceCells.Add(new SourceCell(idx, columns[idx])); k = _sourceCells.Count - 1; }
          var entry = _sourceCells[k];
          entry.Water += water;
          entry.Radioactive += water * share;
          _sourceCells[k] = entry;
        }
      }
    }

    private float SourceShare(in ThreadSafeWaterSource source) {
      float share = _publishedSprings.TryGetValue(source._waterSource, out var spring) ? spring : _publishedTideShare * (1f - source.Contamination);
      if (share > 0f) RadiationMixing.RequireShares(source.Contamination, share, "a water source");
      return share;
    }

    internal void RestoreSourceCells() {
      foreach (var entry in _sourceCells) {
        var column = entry.Before;
        column.Contamination = _radiation[entry.Index];
        _water[entry.Index] = column;
        _isSourceCell[entry.Index] = true;
      }
    }

    internal void MixSourceCells(WaterColumn[] native) {
      foreach (var entry in _sourceCells) {
        int idx = entry.Index;
        float before = EffectiveDepth(in entry.Before), after = EffectiveDepth(in native[idx]);
        float added = entry.Water > 0f ? entry.Radioactive / entry.Water * (after - before) : 0f;
        float radiation = RadiationMixing.MixSource(_radiation[idx], before, after, added);
        RadiationMixing.RequireShares(native[idx].Contamination, radiation, "the water sources");
        _radiation[idx] = radiation;
        var column = native[idx];
        column.Contamination = radiation;
        _water[idx] = column;
        _isSourceCell[idx] = false;
      }
    }

    // Prefix of UpdateWaterChangesTask.Run (after the second substep): the
    // state of every changed column before the native changes.
    internal void RecordChangedColumns(MapIndexService mapIndex, WaterColumn[] columns, ReadOnlyArray<byte> counts,
        ReadOnlyList<WaterChange> changes, int verticalStride) {
      _changeStates.Clear();
      _removedRadioactive.Clear();
      if (_layers == 0) return;
      for (int k = 0; k < changes.Count; k++) {
        var cell = changes[k].Coordinates;
        int idx = NativeColumnIndex(counts, columns, verticalStride, mapIndex.CellToIndex(new Vector2Int(cell.x, cell.y)), cell.z);
        if (idx < 0 || _changeStates.ContainsKey(idx)) continue;
        float num = EffectiveDepth(in columns[idx]), bad = columns[idx].Contamination;
        _changeStates[idx] = new ChangeState(num * (1f - bad), num * bad, num * _radiation[idx]);
      }
    }

    // Postfix of UpdateWaterChangesTask.Run: replay every change in order on
    // (clean, bad, radioactive); radioactive adds are the native clean adds
    // queued by AddRadioactiveWater.
    internal void MixWaterChanges(MapIndexService mapIndex, WaterColumn[] columns, ReadOnlyArray<byte> counts,
        ReadOnlyList<WaterChange> changes, int verticalStride) {
      if (_layers == 0) return;
      var adds = _activeAdds;
      var consumed = new bool[adds.Count];
      for (int k = 0; k < changes.Count; k++) {
        var change = changes[k];
        float share = 0f;
        if (change.ContaminationChange == 0f && change.DepthChange > 0f) {
          for (int a = 0; a < adds.Count; a++) {
            if (consumed[a] || adds[a].Cell != change.Coordinates || adds[a].Volume != change.DepthChange) continue;
            consumed[a] = true; share = 1f; _mixedRows.Include(change.Coordinates.y); break;
          }
        }
        int idx = NativeColumnIndex(counts, columns, verticalStride, mapIndex.CellToIndex(new Vector2Int(change.Coordinates.x, change.Coordinates.y)), change.Coordinates.z);
        if (idx < 0) {
          // Native drops a change into a closed cell; its radioactive water is buried.
          if (share > 0f) _lostRadioactive.Add((change.Coordinates, change.DepthChange));
          continue;
        }
        var state = _changeStates[idx];
        float removed = RadiationMixing.ReplayChange(ref state.Clean, ref state.Bad, ref state.Radioactive,
          change.DepthChange, change.ContaminationChange, share);
        _changeStates[idx] = state;
        if (removed > 0f) _removedRadioactive[change.Coordinates] = _removedRadioactive.TryGetValue(change.Coordinates, out var r) ? r + removed : removed;
      }
      for (int a = 0; a < adds.Count; a++)
        if (!consumed[a]) throw new InvalidOperationException($"Radioactive water add at {adds[a].Cell} was not among the native water changes");
      adds.Clear();
      foreach (var pair in _changeStates) {
        var state = pair.Value;
        float total = state.Clean + state.Bad;
        float radiation = total > 0f ? state.Radioactive / total : 0f;
        RadiationMixing.RequireShares(columns[pair.Key].Contamination, radiation, "the native water changes");
        _radiation[pair.Key] = radiation;
      }
    }

    // Postfix of WaterChangeService.Tick: the native queue became this tick's
    // thread-safe list; so do the radioactive adds queued with it.
    internal void PromoteRadioactiveAdds() {
      if (_activeAdds.Count > 0) throw new InvalidOperationException("Radioactive water adds of the previous tick were never applied");
      (_activeAdds, _queuedAdds) = (_queuedAdds, _activeAdds);
    }

    // Same lookup as native MutableWaterColumnRetriever.TryGetColumnIndex.
    private static int NativeColumnIndex(ReadOnlyArray<byte> counts, WaterColumn[] columns, int verticalStride, int index, int z) {
      for (int j = 0; j < counts[index]; j++) {
        int idx = j * verticalStride + index;
        if (z < columns[idx].Floor) break;
        if (z < columns[idx].Ceiling) return idx;
      }
      return -1;
    }

    // ------------------------------------------------------------------ API

    public void AddRadioactiveWater(Vector3Int cell, float radioactiveVolume) {
      RequirePositive(radioactiveVolume, nameof(radioactiveVolume));
      ValidateOpenCell(cell);
      _waterService.AddCleanWater(cell, radioactiveVolume);
      _queuedAdds.Add(new RadioactiveAdd(cell, radioactiveVolume));
      _pendingRows.Include(cell.y);
    }

    public void AddSoilRadiation(Vector3Int cell, float amount) {
      RequirePositive(amount, nameof(amount));
      ValidateOpenCell(cell);
      _pendingSoil.Add((cell, amount));
      _pendingRows.Include(cell.y);
    }

    public int AddContinuousSource(Vector3Int cell, float volumePerHour, float durationHours) {
      RequirePositive(volumePerHour, nameof(volumePerHour));
      RequirePositive(durationHours, nameof(durationHours));
      ValidateOpenCell(cell);
      int id = _nextSourceId++;
      _sources.Add(new ContinuousSource(id, cell, volumePerHour, durationHours));
      return id;
    }

    public void RemoveContinuousSource(int id) {
      int index = _sources.FindIndex(s => s.Id == id);
      if (index < 0) throw new ArgumentException($"No radiation source with id {id}", nameof(id));
      _sources.RemoveAt(index);
    }

    public void SetSourceRadioactiveShare(float share) {
      if (!(share >= 0f && share <= 1f)) throw new ArgumentOutOfRangeException(nameof(share), share, "Must be within 0..1");
      _tideShare = share;
    }

    internal void RegisterSpring(IWaterSource source, float share) {
      if (!(share > 0f && share <= 1f)) throw new ArgumentOutOfRangeException(nameof(share), share, "Radioactive spring share must be within (0, 1]");
      _springs.Add(source, share);
      _springsChanged = true;
    }

    internal void UnregisterSpring(IWaterSource source) {
      if (!_springs.Remove(source)) throw new InvalidOperationException("Radioactive spring was not registered");
      _springsChanged = true;
    }

    internal void RegisterIntake(Vector3Int cell, RadioactiveSludgeIntake intake) {
      if (_intakes.ContainsKey(cell)) throw new InvalidOperationException($"Two sludge recovery intakes share the cell {cell}");
      _intakes.Add(cell, intake);
    }

    internal void UnregisterIntake(Vector3Int cell, RadioactiveSludgeIntake intake) {
      if (!_intakes.TryGetValue(cell, out var registered) || registered != intake)
        throw new InvalidOperationException($"Sludge recovery intake at {cell} was not registered");
      _intakes.Remove(cell);
    }

    // Reads the native thread-safe column copy, valid from UI and entity code.
    public bool TryFindOpenCell(Vector2Int xy, int z, out Vector3Int cell) {
      RequireInMap(xy);
      int i = _mapIndex.CellToIndex(xy);
      int best = int.MaxValue;
      for (int j = 0; j < _waterMap.ColumnCount(i); j++) {
        int idx = j * _vs + i;
        int floor = _waterMap.ColumnFloor(idx), ceiling = _waterMap.ColumnCeiling(idx);
        if (floor >= ceiling) continue;
        if (z >= floor && z < ceiling) { cell = new Vector3Int(xy.x, xy.y, z); return true; }
        if (floor > z && floor < best) best = floor;
      }
      if (best != int.MaxValue) { cell = new Vector3Int(xy.x, xy.y, best); return true; }
      cell = default;
      return false;
    }

    internal bool IsOpenCell(Vector3Int cell) {
      RequireInMap(new Vector2Int(cell.x, cell.y));
      return _waterMap.TryGetColumnFloor(cell, out _);
    }

    public RadiationSample Sample(Vector3Int cell) {
      int idx = Slot(cell);
      if (idx < 0) return default;
      return new RadiationSample(true, RadiationTuning.Detected(_radiation[idx]), _waterMap.ColumnContamination(cell), _waterMap.CellIsUnderwater(cell), SoilAt(idx));
    }

    public float GetRadiation(Vector3Int cell) {
      var sample = Sample(cell);
      float value = sample.SoilRadiation * RadiationTuning.SoilHazardWeight;
      return sample.Submerged && sample.WaterRadiation > value ? sample.WaterRadiation : value;
    }

    public bool IsColumnContaminated(Vector3Int cell) {
      int idx = Slot(cell);
      return idx >= 0 && _radiation[idx] >= RadiationTuning.DetectionLimit;
    }

    // Irradiated ground (SoilAt >= IrradiatedGroundThreshold) kills plants at
    // once; see IrradiatedPlantWarning.cs. Before a loaded save is applied
    // nothing reads as irradiated: the first tick checks every slot.
    internal bool IsIrradiatedGround(Vector3Int cell) {
      if (_loaded != null) return false;
      int idx = Slot(cell);
      return idx >= 0 && SoilAt(idx) >= RadiationTuning.IrradiatedGroundThreshold;
    }

    internal float ColumnRadiation(Vector3Int cell) {
      int idx = Slot(cell);
      return idx < 0 ? 0f : RadiationTuning.Detected(_radiation[idx]);
    }

    // ------------------------------------------------------------ persistence

    public void Save(ISingletonSaver singletonSaver) {
      // GameSaver.Save finishes the tick first (Ticker.FinishFullTick). Only the
      // native exception saver (GameSceneExceptionStateSaver.CreateExceptionSave:
      // TickOnlyArrayService.ForceAllowAccess, then GameSaver.SaveWithoutFinishingTick)
      // can arrive mid-tick, while worker threads may still run (or, after a
      // worker exception, have abandoned) the lockstep tasks. The parallelizer
      // has no per-handle wait (Parallelizer.Wait waits for every task and
      // throws on worker exceptions), so that save writes the last completed
      // tick's snapshot and never throws.
      bool midTick = _parallelTickScheduled && (!_tickableSingletons.ParalleTicklIsFinished || _tickableSingletons.IsStartingParallelTick);
      bool exceptionSave = _tickOnlyArrays._forceAllowAccess;
      if (exceptionSave && (midTick || _inTick)) { WriteSnapshot(singletonSaver); return; }
      if (midTick)
        throw new InvalidOperationException("Radiation can only be saved between parallel ticks (GameSaver finishes the tick first)");
      if (exceptionSave) {
        try { WriteCurrent(singletonSaver); } catch (Exception e) {
          Debug.LogWarning($"Radiation: the exception save writes the last completed tick instead of the current state ({e.Message})");
          WriteSnapshot(singletonSaver);
        }
        return;
      }
      WriteCurrent(singletonSaver);
    }

    // Exception path only: the last completed tick (see Save). Before any tick
    // completed there is nothing in flight and the live lists are the state.
    // Loading it is lenient where the crashed tick could have moved native
    // state (ApplyLoaded).
    private void WriteSnapshot(ISingletonSaver singletonSaver) {
      var saver = singletonSaver.GetSingleton(RadiationKey);
      saver.Set(VersionKey, SaveVersion);
      saver.Set(SnapshotKey, true);
      saver.Set(NextSourceIdKey, _snapTaken ? _snapNextSourceId : _nextSourceId);
      saver.Set(HourAccumulatorKey, _snapTaken ? _snapHourAccumulator : _hourAccumulator);
      saver.Set(CellsKey, new List<Vector3Int>(_snapCells));
      saver.Set(WaterRadiationKey, new List<float>(_snapRadiation));
      saver.Set(SoilKey, new List<float>(_snapSoil));
      var sources = _snapTaken ? _snapSources : _sources;
      var ids = new List<int>(); var sourceCells = new List<Vector3Int>(); var rates = new List<float>(); var remaining = new List<float>();
      foreach (var source in sources) {
        ids.Add(source.Id); sourceCells.Add(source.Cell); rates.Add(source.VolumePerHour); remaining.Add(source.RemainingHours);
      }
      saver.Set(SourceIdsKey, ids);
      saver.Set(SourceCellsKey, sourceCells);
      saver.Set(SourceRatesKey, rates);
      saver.Set(SourceHoursKey, remaining);
    }

    private void WriteCurrent(ISingletonSaver singletonSaver) {
      // Mirror geometry the forced tick finish changed, so saved floors match
      // the native columns the save is reloaded with.
      EnsureLayers(_waterSimulator.MaxColumnCount);
      var nativeCounts = _waterSimulator.ColumnCounts;
      if (_loaded != null) ApplyLoaded(nativeCounts, _waterSimulator.WaterColumns);
      var envelope = Envelope();
      if (!envelope.Empty) { SyncGeometry(envelope, nativeCounts, _waterSimulator.WaterColumns); ApplyPendingSoil(); }
      var saver = singletonSaver.GetSingleton(RadiationKey);
      saver.Set(VersionKey, SaveVersion);
      saver.Set(NextSourceIdKey, _nextSourceId);
      saver.Set(HourAccumulatorKey, _hourAccumulator);
      var cells = new List<Vector3Int>(); var radiation = new List<float>(); var soil = new List<float>();
      var rows = RowRange.Union(RowRange.Union(_radRows, _soilRows), _pendingRows).Clamp(0, _ySize - 1);
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        int rowStart = (y + 1) * _stride + 1;
        for (int x = 0; x < _xSize; x++) {
          int i = rowStart + x;
          for (int j = 0; j < _counts[i]; j++) {
            int idx = j * _vs + i;
            if (_radiation[idx] <= 0f && _soil[idx] <= 0f) continue;
            cells.Add(new Vector3Int(x, y, _water[idx].Floor)); radiation.Add(_radiation[idx]); soil.Add(_soil[idx]);
          }
        }
      }
      saver.Set(CellsKey, cells);
      saver.Set(WaterRadiationKey, radiation);
      saver.Set(SoilKey, soil);
      var ids = new List<int>(); var sourceCells = new List<Vector3Int>(); var rates = new List<float>(); var remaining = new List<float>();
      foreach (var source in _sources) {
        ids.Add(source.Id); sourceCells.Add(source.Cell); rates.Add(source.VolumePerHour); remaining.Add(source.RemainingHours);
      }
      saver.Set(SourceIdsKey, ids);
      saver.Set(SourceCellsKey, sourceCells);
      saver.Set(SourceRatesKey, rates);
      saver.Set(SourceHoursKey, remaining);
    }

    private void ApplyLoaded(ReadOnlySpan<byte> nativeCounts, ReadOnlySpan<WaterColumn> nativeColumns) {
      var state = _loaded;
      _loaded = null;
      int droppedCells = 0, cappedCells = 0;
      SyncGeometry(new RowRange(-1, _ySize), nativeCounts, nativeColumns);
      for (int k = 0; k < state.Cells.Count; k++) {
        var cell = state.Cells[k];
        RequireInMap(new Vector2Int(cell.x, cell.y));
        int idx = SlotUnchecked(_mapIndex.CellToIndex(new Vector2Int(cell.x, cell.y)), cell.z);
        if (idx < 0 || _water[idx].Floor != cell.z) {
          // A snapshot exception save pairs the last completed tick with native
          // state written mid-tick: geometry queued during the crashed tick (a
          // building placed) can differ. Such cells are dropped and counted.
          if (state.Snapshot) { droppedCells++; continue; }
          throw new InvalidOperationException($"Saved radiation cell {cell} does not match a native water column floor after load");
        }
        float bad = nativeColumns[idx].Contamination;
        if (state.Version == SludgeSaveVersion) {
          // Version 2 conversion: sludge becomes radioactive water at the same
          // cell (native add, next tick); dissolved radiation becomes the
          // radioactive share of the column's non-bad water.
          if (state.Sludge[k] > 0f) AddRadioactiveWater(cell, state.Sludge[k]);
          _radiation[idx] = nativeColumns[idx].WaterDepth > 0f ? RadiationTuning.Detected(state.WaterRadiation[k] * (1f - bad)) : 0f;
        } else {
          _radiation[idx] = RadiationTuning.Detected(state.WaterRadiation[k]);
        }
        // Saves from before the 0.005 cutoff can hold smaller shares: gone on load.
        // A snapshot's r is from the last completed tick and native b from the
        // crashed one: r is capped at 1 - b there (the excess is dropped).
        if (state.Snapshot && bad + _radiation[idx] > 1f) { cappedCells++; _radiation[idx] = RadiationTuning.Detected(Mathf.Max(0f, 1f - bad)); }
        RadiationMixing.RequireShares(bad, _radiation[idx], "the loaded save");
        _soil[idx] = state.Soil[k];
        _pendingRows.Include(cell.y);
      }
      if (state.Snapshot)
        Debug.LogWarning($"Radiation: loaded an exception save holding the last completed tick ({state.Cells.Count} cells; "
          + $"{droppedCells} dropped for changed geometry, {cappedCells} capped at 1 - badwater)");
    }

    // --------------------------------------------------------------- internals

    private void PublishSourceShares() {
      if (_springsChanged) { _publishedSprings = new Dictionary<IWaterSource, float>(_springs); _springsChanged = false; }
      _publishedTideShare = _tideShare;
      _sourceRows = RowRange.None;
      if (_publishedSprings.Count == 0 && _publishedTideShare <= 0f) return;
      var sources = _waterSources.ThreadSafeWaterSources;
      for (int s = 0; s < sources.Count; s++) {
        if (!(sources[s].CurrentStrength > 0f) || !(_publishedSprings.ContainsKey(sources[s]._waterSource) || _publishedTideShare > 0f)) continue;
        foreach (var cell in sources[s].Coordinates) _sourceRows.Include(cell.y);
      }
    }

    private void EmitSources(float hours) {
      for (int k = _sources.Count - 1; k >= 0; k--) {
        var source = _sources[k];
        float active = source.RemainingHours < hours ? source.RemainingHours : hours;
        if (active > 0f) AddRadioactiveWater(source.Cell, source.VolumePerHour * active);
        source.RemainingHours -= hours;
        if (source.RemainingHours <= 0f) _sources.RemoveAt(k); else _sources[k] = source;
      }
    }

    private void CreditIntakes() {
      foreach (var pair in _removedRadioactive) {
        if (_intakes.TryGetValue(pair.Key, out var intake)) intake.OnRadioactiveRemoved(pair.Value);
      }
      _removedRadioactive.Clear();
      foreach (var (cell, volume) in _lostRadioactive) {
        int above = LowestSlotAbove(_mapIndex.CellToIndex(new Vector2Int(cell.x, cell.y)), cell.z);
        if (above < 0) throw new InvalidOperationException($"Radioactive water at closed cell {cell} has no fluid column above it");
        Deposit(above, volume);
        _pendingRows.Include(cell.y);
      }
      _lostRadioactive.Clear();
    }

    private void ApplyPendingSoil() {
      foreach (var (cell, amount) in _pendingSoil) {
        int i = _mapIndex.CellToIndex(new Vector2Int(cell.x, cell.y));
        int idx = SlotUnchecked(i, cell.z);
        if (idx < 0) idx = LowestSlotAbove(i, cell.z);
        if (idx < 0) throw new InvalidOperationException($"Soil radiation at {cell} has no fluid column at or above it");
        _soil[idx] = Mathf.Min(1f, _soil[idx] + amount);
      }
      _pendingSoil.Clear();
    }

    private void Rescan(RowRange envelope, ReadOnlySpan<WaterColumn> nativeColumns) {
      var radValues = RowRange.None; var soilValues = RowRange.None;
      float total = 0f;
      var rows = envelope.Clamp(0, _ySize - 1);
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        int rowStart = (y + 1) * _stride + 1;
        for (int x = 0; x < _xSize; x++) {
          int i = rowStart + x;
          for (int j = 0; j < _counts[i]; j++) {
            int idx = j * _vs + i;
            float radiation = _radiation[idx];
            if (radiation > 0f) {
              float depth = nativeColumns[idx].WaterDepth;
              if (!(depth > 0f)) radiation = 0f;   // dried: its radioactive volume left by evaporation (CopyRow)
              // The cutoff, after this tick's mixing, decay and washout: a
              // share below DetectionLimit that did not grow since the last
              // late tick is gone. Deliberately not conserved (design decision
              // 2026-10-22). A share still growing (a source, leak, outfall or
              // tide filling the column) keeps accumulating, reading 0 until it
              // reaches the limit; once it stops growing below it, it is removed.
              else if (radiation < RadiationTuning.DetectionLimit && !(radiation > _radPrevious[idx])) radiation = 0f;
              if (radiation > 0f) { radValues.Include(y); total += radiation * depth; }
              _radiation[idx] = radiation;
            }
            _radPrevious[idx] = radiation;
            if (_soil[idx] > 0f || _soilExchange.BankAt(idx) > 0f) soilValues.Include(y);
          }
        }
      }
      TotalWaterRadiation = total;
      var radRows = RowRange.Union(radValues, _sourceRows).Expand(RadiationTuning.RangeMargin, 0, _ySize - 1);
      if (radRows.Empty && !_radRows.Empty) for (int i = 0; i < _maxIndex; i++) _radTargeted[i].Clear();
      _radRows = radRows;
      _soilRows = soilValues.Expand(RadiationTuning.RangeMargin, 0, _ySize - 1);
    }

    private void EnsureLayers(int nativeLayers) {
      if (nativeLayers < 1) throw new InvalidOperationException("Native water simulation reports no column layers");
      if (nativeLayers <= _layers) return;
      int size = nativeLayers * _vs;
      Array.Resize(ref _water, size);
      Array.Resize(ref _radiation, size);
      Array.Resize(ref _radPrevious, size);
      Array.Resize(ref _irradiatedGround, size);
      Array.Resize(ref _radBuffer, size);
      Array.Resize(ref _radDiffCount, size);
      Array.Resize(ref _isSourceCell, size);
      Array.Resize(ref _soil, size);
      Array.Resize(ref _soilNext, size);
      _layers = nativeLayers;
      if (_oldColumns.Length < _layers) { _oldColumns = new OldColumn[_layers]; _oldSoilMoved = new bool[_layers]; }
    }

    // Mirrors native geometry for rows lo..hi (padding rows included) and moves
    // radiation and soil when a cell's column layout changed.
    private void SyncGeometry(RowRange rows, ReadOnlySpan<byte> nativeCounts, ReadOnlySpan<WaterColumn> nativeColumns) {
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        int rowStart = (y + 1) * _stride;
        for (int x = 0; x < _stride; x++) {
          int i = rowStart + x;
          if (!SameGeometry(i, nativeCounts, nativeColumns)) Reconcile(i, nativeCounts, nativeColumns);
          for (int j = 0; j < _counts[i]; j++) {
            int idx = j * _vs + i;
            var column = nativeColumns[idx];
            column.Contamination = _radiation[idx];
            _water[idx] = column;
          }
        }
      }
    }

    private bool SameGeometry(int i, ReadOnlySpan<byte> nativeCounts, ReadOnlySpan<WaterColumn> nativeColumns) {
      int count = nativeCounts[i];
      if (count != _counts[i]) return false;
      for (int j = 0; j < count; j++) {
        int idx = j * _vs + i;
        if (nativeColumns[idx].Floor != _water[idx].Floor || nativeColumns[idx].Ceiling != _water[idx].Ceiling) return false;
      }
      return true;
    }

    // Native geometry changes: a split copies contamination to both parts, a
    // merge averages it by depth, a raised floor or removed column deletes
    // water. r follows the same rules; radioactive volume in deleted water goes
    // into the soil of the lowest open column. Soil radiation belongs to the
    // ground at an old floor and moves to at most one new column: the one with
    // that floor, else the floor raised directly above it.
    private void Reconcile(int i, ReadOnlySpan<byte> nativeCounts, ReadOnlySpan<WaterColumn> nativeColumns) {
      int oldCount = _counts[i], newCount = nativeCounts[i];
      if (newCount > _layers) throw new InvalidOperationException("Native column count exceeds mirrored layers");
      float oldVolume = 0f, newVolume = 0f;
      for (int j = 0; j < oldCount; j++) {
        int idx = j * _vs + i;
        _oldColumns[j] = new OldColumn(_water[idx].Floor, _water[idx].Ceiling, _radiation[idx], _water[idx].WaterDepth, _soil[idx]);
        _oldSoilMoved[j] = false;
        oldVolume += _radiation[idx] * _water[idx].WaterDepth;
      }
      for (int j = 0; j < _layers; j++) { _radiation[j * _vs + i] = 0f; _soil[j * _vs + i] = 0f; _irradiatedGround[j * _vs + i] = false; }
      int open = -1;
      for (int n = 0; n < newCount; n++) {
        int idx = n * _vs + i;
        int floor = nativeColumns[idx].Floor, ceiling = nativeColumns[idx].Ceiling;
        float weighted = 0f, weight = 0f;
        for (int o = 0; o < oldCount; o++) {
          var old = _oldColumns[o];
          if (old.Floor < ceiling && floor < old.Ceiling) { weighted += old.Radiation * old.WaterDepth; weight += old.WaterDepth; }
          if (old.Floor == floor) { _soil[idx] = old.Soil; _oldSoilMoved[o] = true; }
        }
        _radiation[idx] = weight > 0f && nativeColumns[idx].WaterDepth > 0f ? weighted / weight : 0f;
        newVolume += _radiation[idx] * nativeColumns[idx].WaterDepth;
        if (open < 0 && ceiling > floor) open = idx;
      }
      for (int n = 0; n < newCount; n++) {
        int idx = n * _vs + i, floor = nativeColumns[idx].Floor;
        bool sameFloor = false;
        for (int o = 0; o < oldCount; o++) sameFloor |= _oldColumns[o].Floor == floor;
        int raised = sameFloor ? -1 : FindOldContaining(oldCount, floor - 1);
        if (raised < 0 || _oldSoilMoved[raised]) continue;
        _soil[idx] = _oldColumns[raised].Soil;
        _oldSoilMoved[raised] = true;
      }
      _counts[i] = (byte)newCount;
      if (oldVolume - newVolume > RadiationTuning.MinWaterRadiation && open >= 0) Deposit(open, oldVolume - newVolume);
    }

    private int FindOldContaining(int oldCount, int z) {
      for (int o = 0; o < oldCount; o++)
        if (z >= _oldColumns[o].Floor && z < _oldColumns[o].Ceiling) return o;
      return -1;
    }

    // Every tick, after Rescan, on the rows holding soil radiation or banks and
    // the rows irradiated last tick: a slot that turns irradiated (or whose
    // column geometry changed, Reconcile) kills the plant standing on it
    // through the native LivingNaturalResource.Die. Plants created later on
    // irradiated ground die in IrradiatedGroundDeath.PostInitializeEntity.
    private void KillOnIrradiatedGround() {
      var rows = RowRange.Union(_soilRows, _irradiatedRows).Clamp(0, _ySize - 1);
      var irradiatedRows = RowRange.None;
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        int rowStart = (y + 1) * _stride + 1;
        for (int x = 0; x < _xSize; x++) {
          int i = rowStart + x;
          for (int j = 0; j < _counts[i]; j++) {
            int idx = j * _vs + i;
            bool irradiated = SoilAt(idx) >= RadiationTuning.IrradiatedGroundThreshold;
            if (irradiated) {
              irradiatedRows.Include(y);
              if (!_irradiatedGround[idx]) {
                var plant = _blockService.GetBottomObjectComponentAt<LivingNaturalResource>(new Vector3Int(x, y, _water[idx].Floor));
                if (plant != null && !plant.IsDead) plant.Die();
              }
            }
            _irradiatedGround[idx] = irradiated;
          }
        }
      }
      _irradiatedRows = irradiatedRows;
    }

    // Soil decay and slow lateral spread, once per game hour.
    private void HourlySoilPass(float hours) {
      var rows = _soilRows.Clamp(0, _ySize - 1);
      float spread = RadiationTuning.SoilSpreadPerHour * hours;
      float decay = RadiationTuning.DecayPerHour(RadiationTuning.SoilHalfLifeDays) * hours;
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        int rowStart = (y + 1) * _stride + 1;
        for (int x = 0; x < _xSize; x++) {
          int i = rowStart + x;
          for (int j = 0; j < _counts[i]; j++) {
            int idx = j * _vs + i;
            float soil = _soil[idx], exchange = 0f;
            foreach (int offset in _neighborOffsets) {
              int neighbor = NeighborSlot(i + offset, _water[idx].Floor);
              if (neighbor >= 0) exchange += _soil[neighbor] - soil;
            }
            float next = soil + spread * exchange;
            next -= next * decay;
            _soilNext[idx] = next < RadiationTuning.MinSoilRadiation ? 0f : next > 1f ? 1f : next;
          }
        }
      }
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        int rowStart = (y + 1) * _stride + 1;
        for (int x = 0; x < _xSize; x++) {
          int i = rowStart + x;
          for (int j = 0; j < _counts[i]; j++) {
            int idx = j * _vs + i;
            _soil[idx] = _soilNext[idx];
          }
        }
      }
    }

    private int NeighborSlot(int i, int floor) {
      int best = -1, bestDiff = 2;
      for (int j = 0; j < _counts[i]; j++) {
        int idx = j * _vs + i;
        int diff = Math.Abs(_water[idx].Floor - floor);
        if (diff < bestDiff && _water[idx].Ceiling > _water[idx].Floor) { best = idx; bestDiff = diff; }
      }
      return best;
    }

    private int Slot(Vector3Int cell) {
      if (_layers == 0) return -1;
      RequireInMap(new Vector2Int(cell.x, cell.y));
      return SlotUnchecked(_mapIndex.CellToIndex(new Vector2Int(cell.x, cell.y)), cell.z);
    }

    private int SlotUnchecked(int i, int z) {
      for (int j = 0; j < _counts[i]; j++) {
        int idx = j * _vs + i;
        if (z >= _water[idx].Floor && z < _water[idx].Ceiling) return idx;
      }
      return -1;
    }

    private int LowestSlotAbove(int i, int z) {
      int best = -1, bestFloor = int.MaxValue;
      for (int j = 0; j < _counts[i]; j++) {
        int idx = j * _vs + i;
        ref readonly var c = ref _water[idx];
        if (c.Floor > z && c.Floor < c.Ceiling && c.Floor < bestFloor) { best = idx; bestFloor = c.Floor; }
      }
      return best;
    }

    private void ValidateOpenCell(Vector3Int cell) {
      if (!IsOpenCell(cell))
        throw new ArgumentException($"Radiation cell {cell} is not inside an open fluid column; use TryFindOpenCell", nameof(cell));
    }

    private void RequireInMap(Vector2Int xy) {
      if (xy.x < 0 || xy.y < 0 || xy.x >= _xSize || xy.y >= _ySize)
        throw new ArgumentOutOfRangeException(nameof(xy), $"Cell {xy} lies outside the {_xSize}x{_ySize} map");
    }

    private static void RequirePositive(float value, string name) {
      if (!(value > 0f) || float.IsInfinity(value)) throw new ArgumentOutOfRangeException(name, value, "Must be a positive finite amount");
    }

    // ----------------------------------------------------------------- types

    internal struct RowRange {
      public int Lo, Hi;
      public RowRange(int lo, int hi) { Lo = lo; Hi = hi; }
      public static RowRange None => new RowRange(int.MaxValue, int.MinValue);
      public bool Empty => Lo > Hi;
      public void Include(int y) { if (y < Lo) Lo = y; if (y > Hi) Hi = y; }
      public RowRange Expand(int margin, int min, int max) =>
        Empty ? None : new RowRange(Math.Max(min, Lo - margin), Math.Min(max, Hi + margin));
      public RowRange Clamp(int min, int max) {
        if (Empty) return None;
        var clamped = new RowRange(Math.Max(min, Lo), Math.Min(max, Hi));
        return clamped.Empty ? None : clamped;
      }
      public static RowRange Union(RowRange a, RowRange b) =>
        a.Empty ? b : b.Empty ? a : new RowRange(Math.Min(a.Lo, b.Lo), Math.Max(a.Hi, b.Hi));
    }

    private readonly struct RadioactiveAdd {
      public readonly Vector3Int Cell;
      public readonly float Volume;
      public RadioactiveAdd(Vector3Int cell, float volume) { Cell = cell; Volume = volume; }
    }

    private struct SourceCell {
      public readonly int Index;
      public readonly WaterColumn Before;
      public float Water, Radioactive;
      public SourceCell(int index, in WaterColumn before) { Index = index; Before = before; Water = 0f; Radioactive = 0f; }
    }

    private struct ChangeState {
      public float Clean, Bad, Radioactive;
      public ChangeState(float clean, float bad, float radioactive) { Clean = clean; Bad = bad; Radioactive = radioactive; }
    }

    private struct ContinuousSource {
      public readonly int Id;
      public readonly Vector3Int Cell;
      public readonly float VolumePerHour;
      public float RemainingHours;
      public ContinuousSource(int id, Vector3Int cell, float volumePerHour, float remainingHours) {
        Id = id; Cell = cell; VolumePerHour = volumePerHour; RemainingHours = remainingHours;
      }
    }

    private readonly struct OldColumn {
      public readonly int Floor, Ceiling;
      public readonly float Radiation, WaterDepth, Soil;
      public OldColumn(int floor, int ceiling, float radiation, float waterDepth, float soil) {
        Floor = floor; Ceiling = ceiling; Radiation = radiation; WaterDepth = waterDepth; Soil = soil;
      }
    }

    private sealed class LoadedState {
      public int Version;
      public readonly List<Vector3Int> Cells = new List<Vector3Int>();
      public readonly List<float> Sludge = new List<float>();
      public readonly List<float> WaterRadiation = new List<float>();
      public readonly List<float> Soil = new List<float>();
      public readonly List<ContinuousSource> Sources = new List<ContinuousSource>();
      public int NextSourceId = 1;
      public float HourAccumulator;
      public bool Snapshot;   // written by WriteSnapshot (native exception save, mid-tick)

      public static LoadedState Read(IObjectLoader loader) {
        int version = loader.Get(VersionKey);
        if (version != SaveVersion && version != SludgeSaveVersion)
          throw new InvalidOperationException($"Unsupported radiation save version {version} (supported: {SludgeSaveVersion} converted, {SaveVersion})");
        var state = new LoadedState { Version = version, NextSourceId = loader.Get(NextSourceIdKey), HourAccumulator = loader.Get(HourAccumulatorKey),
          Snapshot = loader.Has(SnapshotKey) && loader.Get(SnapshotKey) };
        state.Cells.AddRange(loader.Get(CellsKey));
        state.WaterRadiation.AddRange(loader.Get(WaterRadiationKey));
        state.Soil.AddRange(loader.Get(SoilKey));
        if (version == SludgeSaveVersion) state.Sludge.AddRange(loader.Get(SludgeKey));
        int n = state.Cells.Count;
        if (state.WaterRadiation.Count != n || state.Soil.Count != n || (version == SludgeSaveVersion && state.Sludge.Count != n))
          throw new InvalidOperationException("Radiation save lists have different lengths");
        var ids = loader.Get(SourceIdsKey); var cells = loader.Get(SourceCellsKey);
        var rates = loader.Get(SourceRatesKey); var hours = loader.Get(SourceHoursKey);
        if (cells.Count != ids.Count || rates.Count != ids.Count || hours.Count != ids.Count)
          throw new InvalidOperationException("Radiation source save lists have different lengths");
        for (int k = 0; k < ids.Count; k++) state.Sources.Add(new ContinuousSource(ids[k], cells[k], rates[k], hours[k]));
        return state;
      }
    }
  }
}
