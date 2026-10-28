using System;
using DeepFrontier.Scripts.Radiation;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.Localization;
using Timberborn.MapStateSystem;
using Timberborn.NotificationSystem;
using Timberborn.Persistence;
using Timberborn.StatusSystem;
using Timberborn.Stockpiles;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.Workshops;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.Meltdown {
  internal enum WasteLeakState { UnderConstruction, Contained, Warning, Full, Sealed }

  // Radioactive waste leaks, decorated on WasteLeakSpec.
  //
  // Trigger StorageFull (Radioactive Waste Vault, native Stockpile): full when
  // its stock of GoodId fills the whole stockpile capacity.
  // Trigger OutputBlocked (Waste Refinery, native Manufactory): full when the
  // current recipe produces GoodId and the inventory has no unreserved room
  // for one more cycle of it, while the building is unblocked. A paused or
  // automation-Off refinery (BlockableObject blocked) seals its tanks: no
  // leak, and native AutoEmptiable hauls the stock out.
  //
  // Hours spent full accumulate (and drain at the same rate while not full,
  // so a stock oscillating at the brim still leaks). Every LeakIntervalHours
  // GoodsPerLeak unreserved goods are destroyed and released at the footprint
  // centre as sludge (SludgeVolumePerGood each); the soil within SoilRadius
  // tiles of the footprint gains SoilRadiationPerLeak. Warnings, statuses and
  // notifications start at WarningFillFraction, before anything leaks.
  internal sealed class WasteLeak : TickableComponent, IAwakableComponent, IInitializableEntity,
      IFinishedStateListener, IPersistentEntity {
    private static readonly ComponentKey Key = new("DeepFrontier.WasteLeak");
    private static readonly PropertyKey<float> HoursFullKey = new("HoursFull");
    private static readonly PropertyKey<int> LeaksKey = new("Leaks");
    private static readonly PropertyKey<int> GoodsLeakedKey = new("GoodsLeaked");

    private readonly IRadiationService _radiation;
    private readonly IDayNightCycle _cycle;
    private readonly NotificationBus _notifications;
    private readonly MapSize _mapSize;
    private readonly ILoc _loc;

    private Stockpile _stockpile;
    private Manufactory _manufactory;
    private BlockableObject _blockable;
    private BlockObject _block;
    private StatusToggle _warningStatus, _leakingStatus;
    private float _hoursFull;
    private bool _warningPosted, _fullPosted;

    public WasteLeak(IRadiationService radiation, IDayNightCycle cycle, NotificationBus notifications, MapSize mapSize, ILoc loc) {
      _radiation = radiation; _cycle = cycle; _notifications = notifications; _mapSize = mapSize; _loc = loc;
    }

    public WasteLeakSpec Spec { get; private set; }
    public bool StorageTrigger => Spec.Trigger == WasteLeakTriggers.StorageFull;
    public WasteLeakState State { get; private set; } = WasteLeakState.UnderConstruction;
    public int Stock { get; private set; }
    public int Capacity { get; private set; }
    public float Fill => Capacity > 0 ? Stock / (float)Capacity : 0f;
    public float HoursUntilLeak => Mathf.Max(0f, Spec.LeakIntervalHours - _hoursFull);
    public int Leaks { get; private set; }
    public int GoodsLeaked { get; private set; }

    public void Awake() {
      Spec = GetComponent<WasteLeakSpec>();
      _blockable = GetComponent<BlockableObject>();
      _block = GetComponent<BlockObject>();
      var s = Spec;
      if (string.IsNullOrEmpty(s.GoodId) || !(s.WarningFillFraction > 0f && s.WarningFillFraction < 1f)
          || !(s.LeakIntervalHours > 0f) || s.GoodsPerLeak <= 0 || !(s.SludgeVolumePerGood > 0f)
          || !(s.SoilRadiationPerLeak > 0f && s.SoilRadiationPerLeak <= 1f) || s.SoilRadius < 0)
        throw new InvalidOperationException($"{Name}: invalid WasteLeakSpec");
      if (s.Trigger == WasteLeakTriggers.StorageFull) {
        _stockpile = GetComponent<Stockpile>();
        if (!_stockpile) throw new InvalidOperationException($"{Name}: WasteLeakSpec trigger StorageFull needs a native Stockpile");
      } else if (s.Trigger == WasteLeakTriggers.OutputBlocked) {
        _manufactory = GetComponent<Manufactory>();
        if (!_manufactory) throw new InvalidOperationException($"{Name}: WasteLeakSpec trigger OutputBlocked needs a native Manufactory");
      } else throw new InvalidOperationException($"{Name}: unknown WasteLeakSpec trigger '{s.Trigger}'");
      if (!_blockable || !_block) throw new InvalidOperationException($"{Name}: WasteLeakSpec needs a building");
      DisableComponent();
    }

    public void InitializeEntity() {
      var prefix = $"DeepFrontier.WasteLeak.{Spec.Trigger}";
      _warningStatus = StatusToggle.CreateNormalStatus(MeltdownSprites.LeakWarning,
        _loc.T(prefix + MeltdownLoc.LeakStatusWarning, ReactorCore.Hours(Spec.LeakIntervalHours)));
      _leakingStatus = StatusToggle.CreatePriorityStatusWithAlertAndFloatingIcon(MeltdownSprites.Leaking,
        _loc.T(prefix + MeltdownLoc.LeakStatusLeaking), _loc.T(prefix + MeltdownLoc.LeakStatusLeakingShort));
      var subject = GetComponent<StatusSubject>();
      subject.RegisterStatus(_warningStatus);
      subject.RegisterStatus(_leakingStatus);
    }

    public void OnEnterFinishedState() {
      EnableComponent();
      Measure(out bool full);
      _warningPosted = Fill >= Spec.WarningFillFraction;
      _fullPosted = full;
    }

    public void OnExitFinishedState() {
      _warningStatus.Deactivate();
      _leakingStatus.Deactivate();
      State = WasteLeakState.UnderConstruction;
      DisableComponent();
    }

    private Inventory Inventory => _stockpile ? _stockpile.Inventory : _manufactory.Inventory;

    // Stock and capacity of GoodId; `full` is the leak condition.
    private void Measure(out bool full) {
      var inventory = Inventory;
      Stock = inventory.AmountInStock(Spec.GoodId);
      if (StorageTrigger) {
        Capacity = inventory.Capacity;
        full = Stock >= Capacity;
        return;
      }
      int perCycle = ProductPerCycle();
      Capacity = perCycle > 0 ? inventory.LimitedAmount(Spec.GoodId) : 0;
      full = perCycle > 0 && _blockable.IsUnblocked && !inventory.HasUnreservedCapacity(new GoodAmount(Spec.GoodId, perCycle));
    }

    private int ProductPerCycle() {
      if (!_manufactory.HasCurrentRecipe) return 0;
      foreach (var product in _manufactory.CurrentRecipe.Products)
        if (product.Id == Spec.GoodId) return product.Amount;
      return 0;
    }

    public override void Tick() {
      float hours = _cycle.FixedDeltaTimeInHours;
      Measure(out bool full);
      bool sealedTanks = !StorageTrigger && !_blockable.IsUnblocked;
      if (full) _hoursFull += hours;
      else _hoursFull = Mathf.Max(0f, _hoursFull - hours);

      State = sealedTanks ? WasteLeakState.Sealed
        : full ? WasteLeakState.Full
        : Fill >= Spec.WarningFillFraction ? WasteLeakState.Warning
        : WasteLeakState.Contained;

      var prefix = $"DeepFrontier.WasteLeak.{Spec.Trigger}";
      if (Fill >= Spec.WarningFillFraction && !_warningPosted && !sealedTanks) {
        _warningPosted = true;
        _notifications.Post(_loc.T(prefix + MeltdownLoc.LeakNotificationWarning, ReactorCore.Pct(Fill)), this);
      } else if (Fill < Spec.WarningFillFraction * 0.95f) _warningPosted = false;
      if (full && !_fullPosted) {
        _fullPosted = true;
        _notifications.Post(_loc.T(prefix + MeltdownLoc.LeakNotificationFull, Spec.GoodsPerLeak, ReactorCore.Hours(HoursUntilLeak)), this);
      } else if (!full && _hoursFull <= 0f) _fullPosted = false;

      if (full && _hoursFull >= Spec.LeakIntervalHours) Leak(prefix);
      _warningStatus.Toggle(State == WasteLeakState.Warning);
      _leakingStatus.Toggle(State == WasteLeakState.Full);
    }

    private void Leak(string prefix) {
      var inventory = Inventory;
      int taken = Math.Min(Spec.GoodsPerLeak, inventory.UnreservedAmountInStock(Spec.GoodId));
      if (taken == 0) return;   // all reserved by haulers taking it away; wait
      var site = BuildingSite.Of(_block, _mapSize);
      var area = site.OpenCellsWithin(_radiation, Spec.SoilRadius);
      var footprint = area.FindAll(c => c.Distance == 0).ConvertAll(c => c.Cell);
      if (footprint.Count == 0) throw new InvalidOperationException($"{Name}: no open fluid column in the footprint to leak into");
      inventory.TakeConsumed(new GoodAmount(Spec.GoodId, taken));
      _radiation.AddRadioactiveWater(site.NearestToCenter(footprint), taken * Spec.SludgeVolumePerGood);
      foreach (var (cell, _) in area) _radiation.AddSoilRadiation(cell, Spec.SoilRadiationPerLeak);
      _hoursFull -= Spec.LeakIntervalHours;
      Leaks++;
      GoodsLeaked += taken;
      _notifications.Post(_loc.T(prefix + MeltdownLoc.LeakNotificationLeak, taken), this);
    }

    public void Save(IEntitySaver entitySaver) {
      var saver = entitySaver.GetComponent(Key);
      saver.Set(HoursFullKey, _hoursFull);
      saver.Set(LeaksKey, Leaks);
      saver.Set(GoodsLeakedKey, GoodsLeaked);
    }

    public void Load(IEntityLoader entityLoader) {
      // A building saved before leaks existed starts with no leak history.
      if (!entityLoader.TryGetComponent(Key, out var loader)) return;
      _hoursFull = loader.Get(HoursFullKey);
      Leaks = loader.Get(LeaksKey);
      GoodsLeaked = loader.Get(GoodsLeakedKey);
      if (!(_hoursFull >= 0f) || float.IsInfinity(_hoursFull) || Leaks < 0 || GoodsLeaked < 0)
        throw new InvalidOperationException($"{Name}: saved waste leak state is invalid");
    }
  }
}
