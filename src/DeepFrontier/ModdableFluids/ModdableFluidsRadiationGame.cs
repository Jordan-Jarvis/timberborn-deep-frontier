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
using Timberborn.SettingsSystem;
using Timberborn.SingletonSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>
  /// Registers Deep Frontier's radioactive water and its irradiated-soil terrain overlay with Moddable Fluids at mod start
  /// (flagged build only).
  /// </summary>
  internal sealed class DeepFrontierFluidsModStarter : IModStarter {
    internal static DeepFrontierRadioactiveWater Provider { get; private set; }
    internal static FluidTerrainOverlay SoilOverlay { get; private set; }
    public void StartMod(IModEnvironment modEnvironment) {
      if (Provider != null) throw new InvalidOperationException("Deep Frontier registered its radioactive water twice");
      if (!ModdableFluidsEntry.Capabilities.Contains(FluidTerrainOverlays.Capability))
        throw new InvalidOperationException("Deep Frontier draws irradiated ground with Moddable Fluids' terrain overlay (" + FluidTerrainOverlays.Capability
          + "), which Moddable Fluids " + ModdableFluidsEntry.ApiVersion + " does not offer; update Moddable Fluids");
      Provider = new DeepFrontierRadioactiveWater(Tide(), ImportTide, ImportStation);
      ModdableFluidsEntry.RegisterProvider(Provider);
      var color = SoilColor();
      SoilOverlay = IrradiatedSoilOverlay.Register(ModdableFluidsEntry.Host, new FluidTerrainOverlayColor(color.r, color.g, color.b));
      Debug.Log("[DeepFrontier] Radioactive water, the radioactive tide and the irradiated-soil overlay (" + SoilOverlay + ") registered with Moddable Fluids "
        + ModdableFluidsEntry.ApiVersion + ".");
    }

    // IrradiatedSoilSurface.SoilColor (RadiationShading.cs), unchanged; the harness compares the two bodies. The native soil
    // contamination texture (veins, sRGB mean NativeSoilVeinColor) times this material colour gives SoilVeinColor.
    private static Color SoilColor() {
      var target = RadiationMaterials.SoilVeinColor; var native = RadiationMaterials.NativeSoilVeinColor;
      if (QualitySettings.activeColorSpace == ColorSpace.Gamma)
        return new Color(target.r / native.r, target.g / native.g, target.b / native.b, 1f);
      var linear = new Color(Mathf.GammaToLinearSpace(target.r) / Mathf.GammaToLinearSpace(native.r),
        Mathf.GammaToLinearSpace(target.g) / Mathf.GammaToLinearSpace(native.g),
        Mathf.GammaToLinearSpace(target.b) / Mathf.GammaToLinearSpace(native.b), 1f);
      return linear.gamma;   // Material.SetColor linearises colours in a linear project
    }

    // RadioactiveTideService's singleton (same keys): the state of a save played under Deep Frontier's own tide.
    private static readonly SingletonKey TideStateKey = new SingletonKey("DeepFrontier.RadioactiveTide");
    private static readonly PropertyKey<bool> CurrentCycleIsTideKey = new PropertyKey<bool>("CurrentCycleIsTide");
    private static readonly PropertyKey<int> LastTideCycleKey = new PropertyKey<int>("LastTideCycle");
    private static readonly PropertyKey<int> LastTideDurationKey = new PropertyKey<int>("LastTideDuration");

    // A save played with Deep Frontier's Moddable Weathers bridge keeps the tide in Moddable Weathers' singletons (Moddable
    // Weathers 11.0.0 BaseWeatherSettingsService and WeatherHistoryRegistry) and the game's position in GameCycleService.
    private static readonly SingletonKey ModdableWeathersSettingsKey = new SingletonKey(RadioactiveTideModdableWeathersSave.SettingsSingleton);
    private static readonly PropertyKey<string> ModdableWeathersSettingsJsonKey = new PropertyKey<string>(RadioactiveTideModdableWeathersSave.SettingsProperty);
    private static readonly SingletonKey ModdableWeathersHistoryKey = new SingletonKey(RadioactiveTideModdableWeathersSave.HistorySingleton);
    private static readonly ListKey<string> ModdableWeathersCyclesKey = new ListKey<string>(RadioactiveTideModdableWeathersSave.HistoryList);
    private static readonly SingletonKey GameCycleKey = new SingletonKey("GameCycleService");
    private static readonly PropertyKey<int> GameCycleCycleKey = new PropertyKey<int>("Cycle");
    private static readonly PropertyKey<int> GameCycleDayKey = new PropertyKey<int>("CycleDay");

    // Moddable Fluids' tide service asks once for a loaded save without its tide state: the save's DeepFrontier.RadioactiveTide
    // and its settings (saved copy, else the former mod settings of 0.8.3 and older), as RadioactiveTideImport maps them; or,
    // for a save played with Deep Frontier's Moddable Weathers bridge, the state its Moddable Weathers history gives and the
    // bridge's settings (RadioactiveTideModdableWeathersSave), checked by the same rules.
    private static FluidTideImport ImportTide(FluidTideImportContext context) {
      var loader = context.NativeSingletonLoader as ISingletonLoader
        ?? throw new InvalidOperationException("Moddable Fluids passed no native singleton loader to Deep Frontier's tide import");
      var settings = context.NativeSettings as ISettings
        ?? throw new InvalidOperationException("Moddable Fluids passed no native settings to Deep Frontier's tide import (needed for saves from 0.8.3 and older)");
      bool hasState = loader.TryGetSingleton(TideStateKey, out var saved);
      var bridge = RadioactiveTideModdableWeathersSave.Read(RadioactiveTideTuning.WeatherId, hasState || loader.TryGetSingleton(RadioactiveTideStartingValues.SavedKey, out _),
        loader.TryGetSingleton(ModdableWeathersSettingsKey, out var weatherSettings) ? weatherSettings.Get(ModdableWeathersSettingsJsonKey) : null,
        loader.TryGetSingleton(ModdableWeathersHistoryKey, out var weatherHistory) ? weatherHistory.Get(ModdableWeathersCyclesKey) : null,
        loader.TryGetSingleton(GameCycleKey, out var gameCycle) ? (gameCycle.Get(GameCycleCycleKey), gameCycle.Get(GameCycleDayKey)) : ((int, int)?)null);
      if (bridge != null) {
        var bridgeValues = new RadioactiveTideValues(bridge.Enabled, bridge.CyclesWithoutTide, bridge.ChancePercent, bridge.MinDurationDays, bridge.MaxDurationDays,
          RadioactiveTideModdableWeathersSave.Source);
        RadioactiveTideSettingsCheck.Validate(bridgeValues, bridgeValues.Source);
        var bridgeImport = RadioactiveTideImport.Map(bridge.State, bridgeValues.Enabled, bridgeValues.CyclesWithoutTide, bridgeValues.ChancePercent,
          bridgeValues.MinDurationDays, bridgeValues.MaxDurationDays);
        Debug.Log("[DeepFrontier] Radioactive tide of Deep Frontier's Moddable Weathers weather imported into Moddable Fluids: " + bridge + "; settings " + bridgeValues + "; "
          + bridgeImport + ".");
        return bridgeImport;
      }
      RadioactiveTideSavedState state = null;
      if (hasState)
        state = new RadioactiveTideSavedState(saved.Get(CurrentCycleIsTideKey), saved.Get(LastTideCycleKey), saved.Get(LastTideDurationKey));
      var values = RadioactiveTideStartingValues.ForLoadedSave(loader, settings);
      var import = RadioactiveTideImport.Map(state, values.Enabled, values.CyclesWithoutTide, values.ChancePercent, values.MinDurationDays, values.MaxDurationDays);
      Debug.Log("[DeepFrontier] Radioactive tide imported into Moddable Fluids: settings " + values + "; " + import + ".");
      return import;
    }

    // WeatherStationRadioactiveTide's component (same keys): whether the station signalled the radioactive tide.
    private static readonly ComponentKey StationKey = new ComponentKey("DeepFrontier.WeatherStationRadioactiveTide");
    private static readonly PropertyKey<bool> StationSignalsKey = new PropertyKey<bool>("SignalsRadioactiveTide");

    private static bool? ImportStation(object nativeEntityLoader) {
      var loader = nativeEntityLoader as IEntityLoader
        ?? throw new InvalidOperationException("Moddable Fluids passed no native entity loader to Deep Frontier's Weather Station import");
      return loader.TryGetComponent(StationKey, out var station) ? station.Get(StationSignalsKey) : (bool?)null;
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
        MarkSavedState();
        int version = loader.Get(VersionKey);
        var ids = loader.Get(SourceIdsKey); var cells = loader.Get(SourceCellsKey); var rates = loader.Get(SourceRatesKey); var hours = loader.Get(SourceHoursKey);
        if (cells.Count != ids.Count || rates.Count != ids.Count || hours.Count != ids.Count) throw new InvalidOperationException("Radiation source save lists have different lengths");
        var sources = Enumerable.Range(0, ids.Count).Select(k => new RadiationSourceRecord(ids[k], cells[k], rates[k], hours[k])).ToArray();
        var pendingSoil = Pairs(loader, PendingSoilCellsKey, PendingSoilAmountsKey, version == RadiationFacadeRecord.Version);
        var earlyWater = Pairs(loader, EarlyWaterCellsKey, EarlyWaterVolumesKey, version == RadiationFacadeRecord.Version);
        if (version == RadiationFacadeRecord.Version) {
          new RadiationFacadeRecord(loader.Get(CellsKey), loader.Get(SoilKey), sources, loader.Get(NextSourceIdKey), loader.Get(HourAccumulatorKey),
            pendingSoil, earlyWater).Restore(this);
        } else {
          legacy = new RadiationLegacyRecord(version, loader.Has(SnapshotKey) && loader.Get(SnapshotKey), loader.Get(CellsKey), loader.Get(WaterRadiationKey),
            loader.Get(SoilKey), version == RadiationLegacyRecord.SludgeVersion ? loader.Get(SludgeKey) : null, sources, loader.Get(NextSourceIdKey), loader.Get(HourAccumulatorKey));
          // Soil lies under the same column cells; it stays Deep Frontier's. Requests a write-back kept come with it.
          field.Load(legacy.Cells, legacy.Soil, legacy.HourAccumulator, legacy.Snapshot);
          LoadSources(legacy.Sources, legacy.NextSourceId);
          foreach (var (cell, amount) in pendingSoil) field.RequestSoil(cell, amount);
          LoadEarlyAdditions(earlyWater);
        }
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
      _bank.Field = Soil;
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

    // A normal save arrives at a completed tick (GameSaver finishes it); the native exception saver may arrive mid-tick,
    // and then writes the last published pass, which is what Capture reads in either case.
    public void Save(ISingletonSaver singletonSaver) {
      var saver = singletonSaver.GetSingleton(RadiationKey);
      var record = RadiationFacadeRecord.Capture(this);
      var pending = _provider.PendingRecord;
      if (pending != null) WriteLegacy(saver, pending);
      else {
        saver.Set(VersionKey, RadiationFacadeRecord.Version);
        saver.Set(CellsKey, record.SoilCells.ToArray()); saver.Set(SoilKey, record.Soil.ToArray());
        saver.Set(HourAccumulatorKey, record.HourAccumulator);
      }
      saver.Set(SourceIdsKey, record.Sources.Select(s => s.Id).ToArray()); saver.Set(SourceCellsKey, record.Sources.Select(s => s.Cell).ToArray());
      saver.Set(SourceRatesKey, record.Sources.Select(s => s.VolumePerHour).ToArray()); saver.Set(SourceHoursKey, record.Sources.Select(s => s.RemainingHours).ToArray());
      saver.Set(NextSourceIdKey, record.NextSourceId);
      saver.Set(PendingSoilCellsKey, record.PendingSoil.Select(r => r.Cell).ToArray()); saver.Set(PendingSoilAmountsKey, record.PendingSoil.Select(r => r.Amount).ToArray());
      saver.Set(EarlyWaterCellsKey, record.EarlyWater.Select(r => r.Cell).ToArray()); saver.Set(EarlyWaterVolumesKey, record.EarlyWater.Select(r => r.Volume).ToArray());
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

  /// <summary>
  /// Irradiated ground in the Moddable Fluids build. Moddable Fluids draws it: Deep Frontier's irradiated-soil terrain
  /// overlay (<see cref="IrradiatedSoilOverlay"/>, registered at mod start) on Moddable Fluids' per-scene copies of the
  /// native terrain materials, so no Deep Frontier shader touches a native material. This writes the bank layer's view
  /// (soil field and bank layer) into the overlay when a new soil pass is published, in the late tick after
  /// ModdableFluidsRadiation (bound and created after it); before the first pass, the loaded soil is written from the
  /// update. Moddable Fluids applies the native update rule (a change interpolates over the next tick, then settles).
  /// </summary>
  public sealed class ModdableFluidsSoilRenderer : IPostLoadableSingleton, ITickableSingleton, ILateTickable, IUpdatableSingleton {
    private readonly ModdableFluidsRadiation _radiation;
    private readonly ModdableFluidsBankLayer _bank;
    private IrradiatedSoilOverlayWriter _soil;
    private int _lastPass = -1;

    public ModdableFluidsSoilRenderer(ModdableFluidsRadiation radiation, ModdableFluidsBankLayer bank) {
      _radiation = radiation; _bank = bank;
    }

    // Moddable Fluids attaches the scene's overlay surface in its terrain renderer's Load.
    public void PostLoad() {
      var overlay = DeepFrontierFluidsModStarter.SoilOverlay ?? throw new InvalidOperationException("Deep Frontier's irradiated-soil overlay was not registered at mod start");
      if (!overlay.IsAttached) throw new InvalidOperationException("Moddable Fluids attached no terrain overlay surface to this scene; irradiated ground cannot be drawn");
      _soil = new IrradiatedSoilOverlayWriter(overlay);
    }

    public void Tick() => Refresh();

    // A loaded game starts paused: until the first soil pass the loaded soil is written from here.
    public void UpdateSingleton() {
      if (!_radiation.Soil.HasPass) Refresh();
    }

    private void Refresh() {
      if (_soil == null) throw new InvalidOperationException("Irradiated soil renderer refreshed before PostLoad");
      int pass = _radiation.Soil.Published.Pass;
      if (pass == _lastPass) return;
      _lastPass = pass;
      _soil.Update(_bank);
    }
  }

  /// <summary>
  /// IrradiatedSoilSurface.Update's cell loop with the overlay as its target: per cell, the highest soil of the columns
  /// standing on each terrain floor (building tops, at or above the terrain height, are not terrain), written to that
  /// floor; cells that had soil and lost it are written back to 0. Rows visited: the view's visible rows and the rows
  /// that held soil at the last update. The overlay curve is Encode's, and the level of the highest soil is the highest
  /// level, so what is drawn is what IrradiatedSoilSurface drew.
  /// </summary>
  internal sealed class IrradiatedSoilOverlayWriter {
    private readonly FluidTerrainOverlay _overlay;
    private readonly int _width, _height, _depth;
    private readonly bool[] _hasData;    // per cell: soil written at the last update
    private readonly float[] _target;    // per terrain z, scratch
    private RadiationSimulation.RowRange _rowsWithData = RadiationSimulation.RowRange.None;

    internal IrradiatedSoilOverlayWriter(FluidTerrainOverlay overlay) {
      _overlay = overlay; _width = overlay.Width; _height = overlay.Height; _depth = overlay.Depth;
      _hasData = new bool[_width * _height];
      _target = new float[_depth];
    }

    internal void Update(IIrradiatedSoilView view) {
      if (view.XSize != _width || view.YSize != _height)
        throw new InvalidOperationException("Moddable Fluids' terrain overlay and the radiation soil disagree on the map size");
      var rows = RadiationSimulation.RowRange.Union(view.VisibleRows, _rowsWithData).Clamp(0, _height - 1);
      var withData = RadiationSimulation.RowRange.None;
      var curve = _overlay.Curve;
      int stride = view.Stride, vs = view.VerticalStride;
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        bool rowData = false;
        int rowStart = (y + 1) * stride + 1;
        for (int x = 0; x < _width; x++) {
          int i = rowStart + x, p = x + y * _width, count = view.ColumnCount(i);
          bool any = false;
          for (int j = 0; j < count; j++) {
            int idx = j * vs + i;
            // Persistent soil or the bank layer (RadiationSimulation.SoilAt).
            float soil = view.SoilAt(idx);
            if (curve.Encode(soil) == 0) continue;
            int z = view.ColumnFloor(idx);
            if (z >= _depth) continue;
            if (soil > _target[z]) _target[z] = soil;
            any = true;
          }
          if (!any && !_hasData[p]) continue;
          for (int z = 0; z < _depth; z++) {
            _overlay.Set(x, y, z, _target[z]);
            _target[z] = 0f;
          }
          _hasData[p] = any;
          rowData |= any;
        }
        if (rowData) withData.Include(y);
      }
      _rowsWithData = withData;
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
