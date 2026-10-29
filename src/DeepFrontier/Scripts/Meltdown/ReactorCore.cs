using System;
using System.Collections.Generic;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.Localization;
using Timberborn.MechanicalSystem;
using Timberborn.NotificationSystem;
using Timberborn.Persistence;
using Timberborn.StatusSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WorkSystem;
using Timberborn.Workshops;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.Meltdown {
  // Automatic is a legacy value: saves from before 0.6.0 may hold an automatic
  // SCRAM, which loads as None (the reactor no longer trips by itself).
  internal enum ReactorScram { None = 0, Automatic = 1, Manual = 2 }

  internal enum ReactorMode { UnderConstruction, ColdShutdown, Running, Scrammed, Idle, MeltingDown }

  // Core heat of the Nuclear Reactor (0..1 of meltdown), decorated on
  // ReactorMeltdownSpec. Production, inventory, workers and power output stay
  // native (Manufactory, Workshop, Workplace, WorkshopPoweredGenerator); the
  // generator scales its full output by OutputFactor, 1 - heat.
  //
  // Heat per game hour, evaluated every tick (user direction 2026-10-29: power
  // falls as the core heats, and it cools as slowly as it heats, so a reactor
  // short of coolant more than half the time ends in a meltdown):
  // - Blocked (native pause or automation Off, PausableBuildingTerminal):
  //   cold shutdown, heat falls at CoolingPerHour whatever the coolant. A
  //   blocked manufactory is natively auto-emptied (AutoEmptiable) and gets no
  //   hauling (ManufactoryHaulBehaviorProvider), so a dry-core rule here would
  //   make pausing or automation a meltdown trap.
  // - Otherwise, an uncooled core (coolant dry: less than one cycle in stock;
  //   or waste full: no unreserved room for one more cycle of a product, the
  //   radioactive waste or sludge, user direction 2026-10-29) adds
  //   HeatPerFaultPerHour: full waste always, dry coolant while running or
  //   while the core holds any heat. A hot core keeps heating whether it
  //   runs, idles or is shut down by SCRAM. (Waste fills only by running, and
  //   the cycle that fills it leaves no room for the next, so full waste never
  //   waits for heat.)
  //   While running, fewer than MinOperators working and overdue maintenance
  //   each add HeatPerFaultPerHour below FaultHeatLimit, so they cost power
  //   but never melt the core on their own. With no heating it cools at
  //   CoolingPerHour if it has coolant (a dry, cold core stays cold).
  // WarningHeat warns; 1 melts down (MeltdownService destroys the reactor).
  //
  // SCRAM is a player action and this IManufactoryLimiter returning 0, not
  // BlockableObject.Block: the crew stays and haulers keep delivering coolant.
  internal sealed class ReactorCore : TickableComponent, IAwakableComponent, IInitializableEntity,
      IFinishedStateListener, IPersistentEntity, IManufactoryLimiter, IGeneratorOutputFactor {
    private static readonly ComponentKey Key = new("DeepFrontier.ReactorCore");
    private static readonly PropertyKey<float> HeatKey = new("Heat");
    private static readonly PropertyKey<int> ScramKey = new("Scram");
    private static readonly PropertyKey<float> RunHoursKey = new("RunHoursSinceMaintenance");
    private static readonly PropertyKey<float> IdleHoursKey = new("IdleHours");

    private readonly MeltdownService _meltdowns;
    private readonly RecipeSpecService _recipes;
    private readonly IDayNightCycle _cycle;
    private readonly NotificationBus _notifications;
    private readonly ILoc _loc;
    private readonly IGoodService _goods;

    private Manufactory _manufactory;
    private Workshop _workshop;
    private BlockableObject _blockable;
    private StatusToggle _overheatStatus, _scramStatus, _coolantDryStatus, _wasteFullStatus, _coolantLowStatus, _crewStatus,
      _maintenanceDueStatus, _maintenanceOverdueStatus, _maintenanceGoodsStatus;
    private readonly List<string> _productIds = new();

    private float _heat;
    private ReactorScram _scram;
    private float _runHoursSinceMaintenance;
    private float _idleHours;
    private bool _meltdownRequested;
    private bool _warningPosted, _coolantDryPosted, _wasteFullPosted, _imminentPosted, _maintenancePosted;

    public ReactorCore(MeltdownService meltdowns, RecipeSpecService recipes, IDayNightCycle cycle,
        NotificationBus notifications, ILoc loc, IGoodService goods) {
      _meltdowns = meltdowns; _recipes = recipes; _cycle = cycle; _notifications = notifications; _loc = loc; _goods = goods;
    }

    public ReactorMeltdownSpec Spec { get; private set; }
    public int CoolantPerCycle { get; private set; }
    public float CycleHours { get; private set; }
    public int NominalPowerHp { get; private set; }
    public float Heat => _heat;
    public ReactorScram Scram => _scram;
    public bool MeltdownRequested => _meltdownRequested;

    // Last tick's evaluation, for the panel and statuses.
    public ReactorMode Mode { get; private set; } = ReactorMode.UnderConstruction;
    public float HeatRatePerHour { get; private set; }
    public int CoolantStock { get; private set; }
    public bool CoolantDry { get; private set; }
    public bool WasteFull { get; private set; }
    public bool Uncooled { get; private set; }
    public int OperatorsOnDuty { get; private set; }
    public bool CrewShort { get; private set; }
    public bool MaintenanceOverdue { get; private set; }
    // A maintenance stop is long enough but its repair materials are missing.
    public bool MaintenanceGoodsShort { get; private set; }
    public float IdleHours => _idleHours;
    // Every product of the reactor recipes (radioactive waste and sludge), for the panel.
    public IReadOnlyList<string> ProductIds => _productIds;
    public int ProductStock(string goodId) => _manufactory.Inventory.AmountInStock(goodId);
    public int ProductCapacity(string goodId) => _manufactory.Inventory.LimitedAmount(goodId);
    public float CoolantReserveHours => CoolantStock / (float)CoolantPerCycle * CycleHours;
    public float RunHoursUntilMaintenance => Spec.MaintenanceIntervalHours - _runHoursSinceMaintenance;
    public bool CanScram => Enabled && !_meltdownRequested && _scram == ReactorScram.None;
    public bool CanRestart => Enabled && !_meltdownRequested && _scram != ReactorScram.None && _heat <= Spec.RestartHeat;

    // Share of the full PowerOutput while producing: falls linearly to 0 at meltdown.
    public float OutputFactor => _scram != ReactorScram.None || _meltdownRequested ? 0f : 1f - _heat;

    public void Awake() {
      Spec = GetComponent<ReactorMeltdownSpec>();
      _manufactory = GetComponent<Manufactory>();
      _workshop = GetComponent<Workshop>();
      _blockable = GetComponent<BlockableObject>();
      var workplace = GetComponent<WorkplaceSpec>();
      var manufactory = GetComponent<ManufactorySpec>();
      var node = GetComponent<MechanicalNodeSpec>();
      if (!_manufactory || !_workshop || !_blockable || workplace == null || manufactory == null || node == null
          || !GetComponent<WorkshopPoweredGenerator>() || !GetComponent<Enterable>() || !GetComponent<BlockObject>())
        throw new InvalidOperationException($"{Name}: ReactorMeltdownSpec needs a native powered-generator workshop building (Manufactory, Workshop, Workplace, MechanicalNode, WorkshopPoweredGenerator, Enterable, BlockObject)");
      Validate(Spec, workplace.MaxWorkers);
      NominalPowerHp = node.PowerOutput;
      ReadCoolantRecipe(manufactory);
      DisableComponent();
    }

    private static void Validate(ReactorMeltdownSpec s, int maxWorkers) {
      void Fail(string reason) => throw new InvalidOperationException("Invalid ReactorMeltdownSpec: " + reason);
      static bool Positive(float v) => v > 0f && !float.IsInfinity(v);
      static bool Fraction(float v) => v > 0f && v < 1f;
      if (string.IsNullOrEmpty(s.CoolantGoodId)) Fail("CoolantGoodId is empty");
      if (s.MinOperators < 1 || s.MinOperators > maxWorkers) Fail($"MinOperators {s.MinOperators} outside 1..{maxWorkers}");
      foreach (var (name, value) in new[] {
          ("CoolantReserveWarningHours", s.CoolantReserveWarningHours), ("MaintenanceIntervalHours", s.MaintenanceIntervalHours),
          ("MaintenanceWarningHours", s.MaintenanceWarningHours), ("MaintenanceOutageHours", s.MaintenanceOutageHours),
          ("HeatPerFaultPerHour", s.HeatPerFaultPerHour), ("CoolingPerHour", s.CoolingPerHour),
          ("MeltdownInstantSludge", s.MeltdownInstantSludge),
          ("MeltdownSourceSludgePerHour", s.MeltdownSourceSludgePerHour), ("MeltdownSourceHours", s.MeltdownSourceHours),
          ("MeltdownFootprintWaterRadiation", s.MeltdownFootprintWaterRadiation), ("MeltdownEdgeWaterRadiation", s.MeltdownEdgeWaterRadiation) })
        if (!Positive(value)) Fail($"{name} must be positive");
      if (!(Fraction(s.RestartHeat) && s.RestartHeat < s.WarningHeat && s.WarningHeat < s.FaultHeatLimit && Fraction(s.FaultHeatLimit)))
        Fail("thresholds must satisfy 0 < RestartHeat < WarningHeat < FaultHeatLimit < 1");
      if (s.MaintenanceWarningHours >= s.MaintenanceIntervalHours) Fail("MaintenanceWarningHours must be shorter than the interval");
      if (!(s.MeltdownFootprintSoilRadiation <= 1f && s.MeltdownEdgeSoilRadiation > 0f && s.MeltdownEdgeSoilRadiation <= s.MeltdownFootprintSoilRadiation))
        Fail("soil radiation must satisfy 0 < edge <= footprint <= 1");
      if (s.MeltdownEdgeWaterRadiation > s.MeltdownFootprintWaterRadiation) Fail("edge water radiation exceeds the footprint value");
      if (!(s.MeltdownKillRadius >= 0 && s.MeltdownKillRadius < s.MeltdownIrradiationRadius && s.MeltdownRadius >= 1))
        Fail("radii must satisfy 0 <= kill < irradiation and contamination >= 1");
      if (!(s.MeltdownIrradiationDose > 1f) || float.IsInfinity(s.MeltdownIrradiationDose)) Fail("MeltdownIrradiationDose must exceed 1");
    }

    // Every reactor recipe must burn the same coolant amount per cycle and
    // take every maintenance good as an ingredient with room for its amount.
    private void ReadCoolantRecipe(ManufactorySpec manufactory) {
      if (manufactory.ProductionRecipeIds.IsDefaultOrEmpty)
        throw new InvalidOperationException($"{Name}: the reactor has no recipes");
      foreach (var id in manufactory.ProductionRecipeIds) {
        var recipe = _recipes.GetRecipe(id);
        int amount = 0;
        foreach (var ingredient in recipe.Ingredients)
          if (ingredient.Id == Spec.CoolantGoodId) amount = ingredient.Amount;
        if (amount <= 0) throw new InvalidOperationException($"{Name}: reactor recipe {id} does not consume coolant {Spec.CoolantGoodId}");
        if (CoolantPerCycle != 0 && (amount != CoolantPerCycle || recipe.CycleDurationInHours != CycleHours))
          throw new InvalidOperationException($"{Name}: reactor recipes disagree on coolant per cycle or cycle length");
        CoolantPerCycle = amount;
        CycleHours = recipe.CycleDurationInHours;
        foreach (var good in Spec.MaintenanceGoods) {
          int perCycle = 0;
          foreach (var ingredient in recipe.Ingredients)
            if (ingredient.Id == good.Id) perCycle = ingredient.Amount;
          if (good.Amount <= 0 || perCycle <= 0 || perCycle * recipe.CyclesCapacity < good.Amount)
            throw new InvalidOperationException($"{Name}: maintenance good {good.Id} x{good.Amount} must be an ingredient of reactor recipe {id} with room for it");
        }
        foreach (var product in recipe.Products)
          if (!_productIds.Contains(product.Id)) _productIds.Add(product.Id);
      }
    }

    public void InitializeEntity() {
      _overheatStatus = StatusToggle.CreatePriorityStatusWithAlertAndFloatingIcon(MeltdownSprites.Overheating,
        _loc.T(MeltdownLoc.StatusOverheating), _loc.T(MeltdownLoc.StatusOverheatingShort));
      _scramStatus = StatusToggle.CreatePriorityStatusWithAlertAndFloatingIcon(MeltdownSprites.Scram,
        _loc.T(MeltdownLoc.StatusScram, Pct(Spec.RestartHeat)), _loc.T(MeltdownLoc.StatusScramShort));
      _coolantDryStatus = StatusToggle.CreatePriorityStatusWithAlertAndFloatingIcon(MeltdownSprites.CoolantDry,
        _loc.T(MeltdownLoc.StatusCoolantDry), _loc.T(MeltdownLoc.StatusCoolantDryShort));
      _wasteFullStatus = StatusToggle.CreatePriorityStatusWithAlertAndFloatingIcon(MeltdownSprites.WasteFull,
        _loc.T(MeltdownLoc.StatusWasteFull), _loc.T(MeltdownLoc.StatusWasteFullShort));
      _coolantLowStatus = StatusToggle.CreateNormalStatus(MeltdownSprites.CoolantLow,
        _loc.T(MeltdownLoc.StatusCoolantLow, Hours(Spec.CoolantReserveWarningHours)));
      _crewStatus = StatusToggle.CreateNormalStatus(MeltdownSprites.Crew, _loc.T(MeltdownLoc.StatusCrew, Spec.MinOperators));
      _maintenanceDueStatus = StatusToggle.CreateNormalStatus(MeltdownSprites.Maintenance,
        _loc.T(MeltdownLoc.StatusMaintenanceDue, Hours(Spec.MaintenanceOutageHours)));
      _maintenanceOverdueStatus = StatusToggle.CreateNormalStatusWithFloatingIcon(MeltdownSprites.Maintenance,
        _loc.T(MeltdownLoc.StatusMaintenanceOverdue, Hours(Spec.MaintenanceOutageHours)));
      _maintenanceGoodsStatus = StatusToggle.CreateNormalStatus(MeltdownSprites.Maintenance,
        _loc.T(MeltdownLoc.StatusMaintenanceGoods, MaintenanceGoodsText()));
      var subject = GetComponent<StatusSubject>();
      foreach (var status in Statuses()) subject.RegisterStatus(status);
    }

    private IEnumerable<StatusToggle> Statuses() {
      yield return _overheatStatus; yield return _scramStatus; yield return _coolantDryStatus; yield return _wasteFullStatus;
      yield return _coolantLowStatus;
      yield return _crewStatus; yield return _maintenanceDueStatus; yield return _maintenanceOverdueStatus; yield return _maintenanceGoodsStatus;
    }

    public void OnEnterFinishedState() {
      // Latches start from the loaded state so a reload does not repeat alerts.
      _warningPosted = _heat >= Spec.WarningHeat;
      _imminentPosted = _heat >= Spec.FaultHeatLimit;
      _coolantDryPosted = _wasteFullPosted = _heat > 0f;
      _maintenancePosted = _runHoursSinceMaintenance >= Spec.MaintenanceIntervalHours;
      EnableComponent();
    }

    public void OnExitFinishedState() {
      foreach (var status in Statuses()) status.Deactivate();
      Mode = ReactorMode.UnderConstruction;
      DisableComponent();
    }

    // ---- IManufactoryLimiter: SCRAM stops production, nothing else ----
    public float ProductionEfficiency() => _scram != ReactorScram.None || _meltdownRequested ? 0f : 1f;
    public float MaxProductionProgressChange(float expectedProductionProgressChange) => expectedProductionProgressChange;

    // ---- player controls (ReactorCorePanel) ----
    public void ManualScram() {
      if (!CanScram) throw new InvalidOperationException($"{Name}: cannot SCRAM in its current state");
      _scram = ReactorScram.Manual;
      UpdateStatuses();
    }

    public void Restart() {
      if (!CanRestart) throw new InvalidOperationException($"{Name}: restart needs core heat at or below {Pct(Spec.RestartHeat)}%");
      _scram = ReactorScram.None;
      UpdateStatuses();
    }

    public override void Tick() {
      if (_meltdownRequested) return;
      float hours = _cycle.FixedDeltaTimeInHours;
      bool blocked = !_blockable.IsUnblocked;
      bool running = !blocked && _scram == ReactorScram.None && _workshop.CurrentlyWorking && _manufactory.IsReadyToProduce;

      CoolantStock = _manufactory.Inventory.UnreservedAmountInStock(Spec.CoolantGoodId);
      CoolantDry = CoolantStock < CoolantPerCycle;
      WasteFull = OutputFull();
      OperatorsOnDuty = _workshop.NumberOfWorkersWorking;
      CrewShort = running && OperatorsOnDuty < Spec.MinOperators;

      if (running) {
        _runHoursSinceMaintenance += hours;
        _idleHours = 0f;
      } else {
        _idleHours += hours;
        bool stopLongEnough = _idleHours >= Spec.MaintenanceOutageHours && _runHoursSinceMaintenance > 0f;
        MaintenanceGoodsShort = stopLongEnough && !HasMaintenanceGoods();
        if (stopLongEnough && !MaintenanceGoodsShort) CompleteMaintenance();
      }
      MaintenanceOverdue = _runHoursSinceMaintenance >= Spec.MaintenanceIntervalHours;
      Uncooled = !blocked && (WasteFull || CoolantDry && (running || _heat > 0f));

      if (blocked) {
        Mode = ReactorMode.ColdShutdown;
        HeatRatePerHour = -Spec.CoolingPerHour;
      } else {
        Mode = running ? ReactorMode.Running : _scram != ReactorScram.None ? ReactorMode.Scrammed : ReactorMode.Idle;
        float rate = Uncooled ? Spec.HeatPerFaultPerHour : 0f;
        if (running && _heat < Spec.FaultHeatLimit)
          rate += ((CrewShort ? 1 : 0) + (MaintenanceOverdue ? 1 : 0)) * Spec.HeatPerFaultPerHour;
        HeatRatePerHour = rate > 0f ? rate : CoolantDry || WasteFull ? 0f : -Spec.CoolingPerHour;
      }
      _heat = Mathf.Clamp01(_heat + HeatRatePerHour * hours);

      if (_heat >= 1f) {
        _meltdownRequested = true;
        Mode = ReactorMode.MeltingDown;
        _meltdowns.Request(this);
        return;
      }
      PostAlerts();
      UpdateStatuses();
    }

    // No unreserved room for one more cycle of a product of the current recipe
    // (the WasteLeak OutputBlocked test): the core cannot shed its waste heat.
    private bool OutputFull() {
      if (!_manufactory.HasCurrentRecipe) return false;
      foreach (var product in _manufactory.CurrentRecipe.Products)
        if (!_manufactory.Inventory.HasUnreservedCapacity(new GoodAmount(product.Id, product.Amount))) return true;
      return false;
    }

    private bool HasMaintenanceGoods() {
      foreach (var good in Spec.MaintenanceGoods)
        if (_manufactory.Inventory.UnreservedAmountInStock(good.Id) < good.Amount) return false;
      return true;
    }

    // "20 High-Grade Steel, 40 Concrete", for statuses and the panel.
    internal string MaintenanceGoodsText() {
      var parts = new List<string>();
      foreach (var good in Spec.MaintenanceGoods) parts.Add($"{good.Amount} {_goods.GetGood(good.Id).PluralDisplayName.Value}");
      return string.Join(", ", parts);
    }

    private void CompleteMaintenance() {
      foreach (var good in Spec.MaintenanceGoods) _manufactory.Inventory.TakeConsumed(new GoodAmount(good.Id, good.Amount));
      MaintenanceGoodsShort = false;
      bool wasDue = _runHoursSinceMaintenance >= Spec.MaintenanceIntervalHours - Spec.MaintenanceWarningHours;
      _runHoursSinceMaintenance = 0f;
      _maintenancePosted = false;
      if (wasDue) _notifications.Post(_loc.T(MeltdownLoc.NotificationMaintenanceDone), this);
    }

    // Escalating alerts: the first uncooled heating from dry coolant or full
    // waste (each latched until the core is cold again, since an intermittent
    // supply or hauler toggles them every cycle), the warning heat, then an
    // uncooled core past FaultHeatLimit.
    private void PostAlerts() {
      if (_heat >= Spec.WarningHeat && !_warningPosted && HeatRatePerHour > 0f) {
        _warningPosted = true;
        _notifications.Post(_loc.T(MeltdownLoc.NotificationWarning, Pct(_heat), Causes(), Pct(OutputFactor)), this);
      } else if (_heat <= Spec.RestartHeat) _warningPosted = false;

      if (Uncooled && CoolantDry && !_coolantDryPosted) {
        _coolantDryPosted = true;
        _notifications.Post(_loc.T(MeltdownLoc.NotificationCoolantDry, Pct(_heat), Rate(HeatRatePerHour), Hours((1f - _heat) / HeatRatePerHour)), this);
      } else if (_heat <= 0f) _coolantDryPosted = false;

      if (Uncooled && WasteFull && !_wasteFullPosted) {
        _wasteFullPosted = true;
        _notifications.Post(_loc.T(MeltdownLoc.NotificationWasteFull, Pct(_heat), Rate(HeatRatePerHour), Hours((1f - _heat) / HeatRatePerHour)), this);
      } else if (_heat <= 0f) _wasteFullPosted = false;

      if (Uncooled && _heat >= Spec.FaultHeatLimit && !_imminentPosted) {
        _imminentPosted = true;
        _notifications.Post(_loc.T(MeltdownLoc.NotificationImminent, Pct(_heat), Hours((1f - _heat) / HeatRatePerHour)), this);
      } else if (_heat < Spec.FaultHeatLimit) _imminentPosted = false;

      if (MaintenanceOverdue && !_maintenancePosted) {
        _maintenancePosted = true;
        _notifications.Post(_loc.T(MeltdownLoc.NotificationMaintenanceOverdue, Hours(Spec.MaintenanceOutageHours)), this);
      }
    }

    // Comma-separated causes of the current heating, for the warning notification.
    public string Causes() {
      var causes = new List<string>();
      if (Uncooled && CoolantDry) causes.Add(_loc.T(MeltdownLoc.CauseCoolant));
      if (Uncooled && WasteFull) causes.Add(_loc.T(MeltdownLoc.CauseWaste));
      if (Mode == ReactorMode.Running && _heat < Spec.FaultHeatLimit) {
        if (CrewShort) causes.Add(_loc.T(MeltdownLoc.CauseCrew, Spec.MinOperators));
        if (MaintenanceOverdue) causes.Add(_loc.T(MeltdownLoc.CauseMaintenance));
      }
      return string.Join(", ", causes);
    }

    private void UpdateStatuses() {
      if (!Enabled) return;
      _overheatStatus.Toggle(_heat >= Spec.WarningHeat && _scram == ReactorScram.None);
      _scramStatus.Toggle(_scram != ReactorScram.None);
      _coolantDryStatus.Toggle(Uncooled && CoolantDry);
      _wasteFullStatus.Toggle(Uncooled && WasteFull);
      _coolantLowStatus.Toggle(!CoolantDry && CoolantReserveHours < Spec.CoolantReserveWarningHours);
      _crewStatus.Toggle(CrewShort);
      _maintenanceOverdueStatus.Toggle(MaintenanceOverdue);
      _maintenanceDueStatus.Toggle(!MaintenanceOverdue && RunHoursUntilMaintenance <= Spec.MaintenanceWarningHours);
      _maintenanceGoodsStatus.Toggle(MaintenanceGoodsShort);
    }

    internal static int Pct(float fraction) => Mathf.RoundToInt(fraction * 100f);
    internal static int Hours(float hours) => Mathf.CeilToInt(hours);
    internal static string Rate(float perHour) => (perHour * 100f).ToString("0.#");

    public void Save(IEntitySaver entitySaver) {
      var saver = entitySaver.GetComponent(Key);
      saver.Set(HeatKey, _heat);
      saver.Set(ScramKey, (int)_scram);
      saver.Set(RunHoursKey, _runHoursSinceMaintenance);
      saver.Set(IdleHoursKey, _idleHours);
    }

    public void Load(IEntityLoader entityLoader) {
      // A reactor saved before the meltdown system existed starts cold. Saves
      // from before 0.6.0 also hold AutoRestart and LastRunDay, now unused.
      if (!entityLoader.TryGetComponent(Key, out var loader)) return;
      _heat = loader.Get(HeatKey);
      int scram = loader.Get(ScramKey);
      _runHoursSinceMaintenance = loader.Get(RunHoursKey);
      _idleHours = loader.Get(IdleHoursKey);
      if (!(_heat >= 0f && _heat <= 1f) || !Enum.IsDefined(typeof(ReactorScram), scram) || !(_runHoursSinceMaintenance >= 0f)
          || !(_idleHours >= 0f))
        throw new InvalidOperationException($"{Name}: saved reactor core state is invalid");
      _scram = scram == (int)ReactorScram.Automatic ? ReactorScram.None : (ReactorScram)scram;
    }
  }
}
