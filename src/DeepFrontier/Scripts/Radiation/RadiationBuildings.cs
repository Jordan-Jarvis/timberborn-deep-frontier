using System;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.EntitySystem;
using Timberborn.Localization;
using Timberborn.MapStateSystem;
using Timberborn.Persistence;
using Timberborn.StatusSystem;
using Timberborn.WaterBuildings;
using Timberborn.Workshops;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.Radiation {
  // Marker: the building must occupy at least one cell on the outer ring of the
  // terrain (the map edge) so its cargo can leave the map. Used by the
  // Radioactive Waste Export; its native Manufactory recipes consume the
  // RadioactiveSludge / ContaminatedWater delivered by pipes or haulers, which
  // removes them from the game.
  internal record MapEdgeSiteSpec : ComponentSpec { }

  // Placement rule only (decorated on MapEdgeSiteSpec). An automation Off
  // signal needs no extra handling: the export's consumption is the native
  // Manufactory, which stops when PausableBuildingTerminal blocks it.
  internal sealed class MapEdgeSite : BaseComponent, IAwakableComponent {
    private readonly MapSize _mapSize;
    private BlockObject _block;

    public MapEdgeSite(MapSize mapSize) { _mapSize = mapSize; }

    public void Awake() => _block = GetComponent<BlockObject>();

    public bool TouchesMapEdge() {
      // Runs in MapEdgeSiteValidator for every preview frame: no allocation.
      var size = _mapSize.TerrainSize;
      foreach (var block in _block.PositionedBlocks.GetAllBlocks()) {
        if (!block.IsOccupied) continue;
        var c = block.Coordinates;
        if (c.x == 0 || c.y == 0 || c.x == size.x - 1 || c.y == size.y - 1) return true;
      }
      return false;
    }
  }

  internal sealed class MapEdgeSiteValidator : IBlockObjectValidator {
    private readonly ILoc _loc;

    public MapEdgeSiteValidator(ILoc loc) { _loc = loc; }

    public bool IsValid(BlockObject blockObject, out string errorMessage) {
      errorMessage = null;
      if (!blockObject.IsPreview) return true;
      var site = blockObject.GetComponent<MapEdgeSite>();
      if (site == null || site.TouchesMapEdge()) return true;
      errorMessage = _loc.T(RadiationLoc.NotAtMapEdge);
      return false;
    }
  }

  // Deliberate dumping: each unit of recipe progress releases radioactive
  // water (r = 1) at OutputCoordinates (local block coordinates, transformed by
  // the building's placement) through the native water add path. The outlet
  // must be an open fluid cell; otherwise the manufactory does not run and
  // shows "Outlet blocked".
  internal record RadioactiveSludgeOutfallSpec : ComponentSpec {
    [Serialize] public Vector3Int OutputCoordinates { get; init; }
    [Serialize] public float RadioactiveVolumePerCycle { get; init; }
  }

  internal sealed class RadioactiveSludgeOutfall : BaseComponent, IAwakableComponent, IInitializableEntity, IManufactoryLimiter {
    private readonly RadiationSimulation _radiation;
    private readonly ILoc _loc;
    private RadioactiveSludgeOutfallSpec _spec;
    private BlockObject _block;
    private Manufactory _manufactory;
    private BlockableObject _blockable;
    private StatusToggle _blockedStatus;

    public RadioactiveSludgeOutfall(RadiationSimulation radiation, ILoc loc) { _radiation = radiation; _loc = loc; }

    private Vector3Int Outlet => _block.TransformCoordinates(_spec.OutputCoordinates);

    public void Awake() {
      _spec = GetComponent<RadioactiveSludgeOutfallSpec>();
      if (!(_spec.RadioactiveVolumePerCycle > 0f)) throw new InvalidOperationException("RadioactiveSludgeOutfallSpec.RadioactiveVolumePerCycle must be positive");
      _block = GetComponent<BlockObject>();
      _manufactory = GetComponent<Manufactory>();
      _blockable = GetComponent<BlockableObject>();
      if (_manufactory == null || _blockable == null) throw new InvalidOperationException("RadioactiveSludgeOutfall requires native Manufactory and BlockableObject");
      _blockedStatus = StatusToggle.CreateNormalStatus(RadiationSprites.OutletBlocked, _loc.T(RadiationLoc.OutletBlocked));
    }

    public void InitializeEntity() {
      GetComponent<StatusSubject>().RegisterStatus(_blockedStatus);
      _manufactory.ProductionProgressed += OnProductionProgressed;
    }

    // Automation Off (PausableBuildingTerminal) blocks the BlockableObject:
    // no recipe progress, so the outfall releases nothing.
    public float ProductionEfficiency() {
      if (!_blockable.IsUnblocked) return 0f;
      bool open = _radiation.IsOpenCell(Outlet);
      if (open) _blockedStatus.Deactivate(); else _blockedStatus.Activate();
      return open ? 1f : 0f;
    }

    public float MaxProductionProgressChange(float expectedProductionProgressChange) => expectedProductionProgressChange;

    private void OnProductionProgressed(object sender, ProductionProgressedEventArgs e) {
      if (e.ProductionProgressChange > 0f) _radiation.AddRadioactiveWater(Outlet, _spec.RadioactiveVolumePerCycle * e.ProductionProgressChange);
    }
  }

  // Recovery pump: pumps water through its native intake pipe (WaterInput,
  // the native pump path: DemandCleanWaterAmount removes non-bad water and
  // WaterInputService credits what was removed) and turns the radioactive part
  // into RadioactiveSludge goods, RadioactiveVolumePerCycle per good. Fresh
  // water pumped with it is used up. RadiationSimulation credits the
  // radioactive volume the replayed native water change actually removed at
  // the intake cell to a saved buffer; recipe progress consumes the buffer, so
  // world radioactive volume + buffer + progress * RadioactiveVolumePerCycle is
  // conserved. The buffer returns to the world when the building is deleted.
  internal record RadioactiveSludgeIntakeSpec : ComponentSpec {
    [Serialize] public float RadioactiveVolumePerCycle { get; init; }
    [Serialize] public float MaxWaterPerCycle { get; init; }
  }

  internal sealed class RadioactiveSludgeIntake : BaseComponent, IAwakableComponent, IInitializableEntity, IManufactoryLimiter,
      IFinishedStateListener, IPersistentEntity, IDeletableEntity {
    private static readonly ComponentKey IntakeKey = new ComponentKey("DeepFrontier.RadioactiveSludgeIntake");
    private static readonly PropertyKey<float> BufferKey = new PropertyKey<float>("Buffer");

    private readonly RadiationSimulation _radiation;
    private readonly ILoc _loc;
    private RadioactiveSludgeIntakeSpec _spec;
    private WaterInput _intake;
    private Manufactory _manufactory;
    private BlockableObject _blockable;
    private StatusToggle _noRadiationStatus;
    private Vector3Int _registeredAt;
    private bool _registered;
    private float _buffer;          // radioactive volume removed from the world, not yet turned into progress
    // Read-only, for the all-buildings acceptance's radiation balance (AllBuildingsSites.cs).
    internal float BufferedVolume => _buffer;

    public RadioactiveSludgeIntake(RadiationSimulation radiation, ILoc loc) { _radiation = radiation; _loc = loc; }

    public void Awake() {
      _spec = GetComponent<RadioactiveSludgeIntakeSpec>();
      if (!(_spec.RadioactiveVolumePerCycle > 0f) || !(_spec.MaxWaterPerCycle >= _spec.RadioactiveVolumePerCycle))
        throw new InvalidOperationException("RadioactiveSludgeIntakeSpec needs RadioactiveVolumePerCycle > 0 and MaxWaterPerCycle >= it");
      _intake = GetComponent<WaterInput>();
      _manufactory = GetComponent<Manufactory>();
      _blockable = GetComponent<BlockableObject>();
      if (_intake == null || _manufactory == null || _blockable == null)
        throw new InvalidOperationException("RadioactiveSludgeIntake requires native WaterInput (intake pipe), Manufactory and BlockableObject");
      _noRadiationStatus = StatusToggle.CreateNormalStatus(RadiationSprites.NoRadiation, _loc.T(RadiationLoc.NoRadiation));
    }

    public void InitializeEntity() {
      GetComponent<StatusSubject>().RegisterStatus(_noRadiationStatus);
      _manufactory.ProductionProgressed += OnProductionProgressed;
    }

    public void OnEnterFinishedState() {
      _registeredAt = _intake.Coordinates;
      _radiation.RegisterIntake(_registeredAt, this);
      _registered = true;
    }

    public void OnExitFinishedState() => Unregister();

    private void Unregister() {
      if (!_registered) return;
      _radiation.UnregisterIntake(_registeredAt, this);
      _registered = false;
    }

    // Automation Off (PausableBuildingTerminal) blocks the BlockableObject.
    public float ProductionEfficiency() {
      if (!_blockable.IsUnblocked) return 0f;
      bool available = _buffer > 0f || _radiation.IsColumnContaminated(_intake.Coordinates);
      if (available) _noRadiationStatus.Deactivate(); else _noRadiationStatus.Activate();
      return available ? 1f : 0f;
    }

    // Progress is limited to the buffered radioactive volume. Water for the
    // shortfall is demanded through the native intake: shortfall over the
    // radioactive share of the non-bad water, at most MaxWaterPerCycle per cycle.
    public float MaxProductionProgressChange(float expectedProductionProgressChange) {
      float wanted = expectedProductionProgressChange * _spec.RadioactiveVolumePerCycle;
      if (wanted > _buffer) {
        var sample = _radiation.Sample(_intake.Coordinates);
        float clean = 1f - sample.BadwaterShare;
        float share = clean > 0f ? sample.WaterRadiation / clean : 0f;
        float limit = expectedProductionProgressChange * _spec.MaxWaterPerCycle;
        if (share > 0f) _intake.DemandCleanWaterAmount(Mathf.Min((wanted - _buffer) / share, limit));
      }
      // Pumped water is used up; its radioactive part arrives in OnRadioactiveRemoved.
      float pumped = _intake.DemandCleanWaterAmount(0f);
      if (pumped > 0f) _intake.RemoveCleanWater(pumped);
      float possible = _buffer / _spec.RadioactiveVolumePerCycle;
      return possible < expectedProductionProgressChange ? possible : expectedProductionProgressChange;
    }

    // Main thread, RadiationSimulation's late tick.
    internal void OnRadioactiveRemoved(float volume) {
      if (!(volume >= 0f) || float.IsInfinity(volume)) throw new ArgumentOutOfRangeException(nameof(volume), volume, "Removed radioactive volume must be finite and non-negative");
      _buffer += volume;
    }

    private void OnProductionProgressed(object sender, ProductionProgressedEventArgs e) {
      if (!(e.ProductionProgressChange > 0f)) return;
      float used = e.ProductionProgressChange * _spec.RadioactiveVolumePerCycle;
      // MaxProductionProgressChange bounded the change by _buffer / volume; only rounding can exceed it.
      if (used > _buffer * 1.0001f + 1e-7f)
        throw new InvalidOperationException($"Sludge recovery progressed by {used} radioactive volume with only {_buffer} buffered");
      _buffer = used < _buffer ? _buffer - used : 0f;
    }

    public void DeleteEntity() {
      Unregister();
      if (_buffer <= 0f) return;
      var at = _intake.Coordinates;
      if (!_radiation.TryFindOpenCell(new Vector2Int(at.x, at.y), at.z, out var cell))
        throw new InvalidOperationException($"No open fluid cell at or above the sludge intake {at} to return {_buffer} buffered radioactive water");
      _radiation.AddRadioactiveWater(cell, _buffer);
      _buffer = 0f;
    }

    public void Save(IEntitySaver entitySaver) {
      if (_buffer <= 0f) return;
      entitySaver.GetComponent(IntakeKey).Set(BufferKey, _buffer);
    }

    public void Load(IEntityLoader entityLoader) {
      if (entityLoader.TryGetComponent(IntakeKey, out var loader)) _buffer = loader.Get(BufferKey);
    }
  }
}
