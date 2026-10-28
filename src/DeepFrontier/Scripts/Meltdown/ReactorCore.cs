using System;
using System.Collections.Generic;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.Localization;
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
  internal enum ReactorScram { None = 0, Automatic = 1, Manual = 2 }

  internal enum ReactorMode { UnderConstruction, ColdShutdown, Running, Scrammed, Idle, MeltingDown }

  // Core heat of the Nuclear Reactor (0..1 of meltdown), decorated on
  // ReactorMeltdownSpec. Production, inventory, workers and power output stay
  // native (Manufactory, Workshop, Workplace, WorkshopPoweredGenerator).
  //
  // Heat per game hour, evaluated every tick:
  // - Blocked (native pause or automation Off, PausableBuildingTerminal):
  //   cold shutdown, heat falls at ShutdownCoolingPerHour whatever the
  //   coolant. A blocked manufactory is natively auto-emptied (AutoEmptiable)
  //   and gets no hauling (ManufactoryHaulBehaviorProvider), so a decay-heat
  //   rule here would make pausing or automation a meltdown trap.
  // - Running (Workshop.CurrentlyWorking && Manufactory.IsReadyToProduce, the
  //   WorkshopPoweredGenerator output condition): each fault (coolant dry,
  //   fewer than MinOperators working, maintenance overdue) adds
  //   HeatPerFaultPerHour; with no fault it cools at RunningCoolingPerHour.
  // - Otherwise (night, no fuel, output full, SCRAM): within DecayHeatHours
  //   of the last production a dry core heats at DecayHeatPerHour; otherwise
  //   it cools at ShutdownCoolingPerHour.
  // Thresholds: WarningHeat warns, ScramHeat trips an automatic emergency
  // shutdown, 1 melts down (MeltdownService destroys the reactor).
  //
  // SCRAM is this IManufactoryLimiter returning 0, not BlockableObject.Block:
  // the crew stays and haulers keep delivering coolant to a tripped reactor.
  internal sealed class ReactorCore : TickableComponent, IAwakableComponent, IInitializableEntity,
      IFinishedStateListener, IPersistentEntity, IManufactoryLimiter {
    private static readonly ComponentKey Key = new("DeepFrontier.ReactorCore");
    private static readonly PropertyKey<float> HeatKey = new("Heat");
    private static readonly PropertyKey<int> ScramKey = new("Scram");
    private static readonly PropertyKey<bool> AutoRestartKey = new("AutoRestart");
    private static readonly PropertyKey<float> RunHoursKey = new("RunHoursSinceMaintenance");
    private static readonly PropertyKey<float> IdleHoursKey = new("IdleHours");
    private static readonly PropertyKey<float> LastRunDayKey = new("LastRunDay");
    private const float NeverRan = -1f;

    private readonly MeltdownService _meltdowns;
    private readonly RecipeSpecService _recipes;
    private readonly IDayNightCycle _cycle;
    private readonly NotificationBus _notifications;
    private readonly ILoc _loc;

    private Manufactory _manufactory;
    private Workshop _workshop;
    private BlockableObject _blockable;
    private StatusToggle _overheatStatus, _scramStatus, _coolantDryStatus, _coolantLowStatus, _crewStatus,
      _maintenanceDueStatus, _maintenanceOverdueStatus;

    private float _heat;
    private ReactorScram _scram;
    private bool _autoRestart = true;
    private float _runHoursSinceMaintenance;
    private float _idleHours;
    private float _lastRunDay = NeverRan;
    private bool _meltdownRequested;
    private bool _warningPosted, _coolantDryPosted, _imminentPosted, _maintenancePosted;

    public ReactorCore(MeltdownService meltdowns, RecipeSpecService recipes, IDayNightCycle cycle,
        NotificationBus notifications, ILoc loc) {
      _meltdowns = meltdowns; _recipes = recipes; _cycle = cycle; _notifications = notifications; _loc = loc;
    }

    public ReactorMeltdownSpec Spec { get; private set; }
    public int CoolantPerCycle { get; private set; }
    public float CycleHours { get; private set; }
    public float Heat => _heat;
    public ReactorScram Scram => _scram;
    public bool AutoRestart => _autoRestart;
    public bool MeltdownRequested => _meltdownRequested;

    // Last tick's evaluation, for the panel and statuses.
    public ReactorMode Mode { get; private set; } = ReactorMode.UnderConstruction;
    public float HeatRatePerHour { get; private set; }
    public int CoolantStock { get; private set; }
    public bool CoolantDry { get; private set; }
    public int OperatorsOnDuty { get; private set; }
    public bool CrewShort { get; private set; }
    public bool MaintenanceOverdue { get; private set; }
    public float DecayHoursLeft { get; private set; }
    public float IdleHours => _idleHours;
    public float CoolantReserveHours => CoolantStock / (float)CoolantPerCycle * CycleHours;
    public float RunHoursUntilMaintenance => Spec.MaintenanceIntervalHours - _runHoursSinceMaintenance;
    public bool DecayDanger => (Mode is ReactorMode.Idle or ReactorMode.Scrammed) && DecayHoursLeft > 0f && CoolantDry;
    public bool CanScram => Enabled && !_meltdownRequested && _scram == ReactorScram.None;
    public bool CanRestart => Enabled && !_meltdownRequested && _scram != ReactorScram.None && _heat <= Spec.RestartHeat;

    public void Awake() {
      Spec = GetComponent<ReactorMeltdownSpec>();
      _manufactory = GetComponent<Manufactory>();
      _workshop = GetComponent<Workshop>();
      _blockable = GetComponent<BlockableObject>();
      var workplace = GetComponent<WorkplaceSpec>();
      var manufactory = GetComponent<ManufactorySpec>();
      if (!_manufactory || !_workshop || !_blockable || workplace == null || manufactory == null
          || !GetComponent<WorkshopPoweredGenerator>() || !GetComponent<Enterable>() || !GetComponent<BlockObject>())
        throw new InvalidOperationException($"{Name}: ReactorMeltdownSpec needs a native powered-generator workshop building (Manufactory, Workshop, Workplace, WorkshopPoweredGenerator, Enterable, BlockObject)");
      Validate(Spec, workplace.MaxWorkers);
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
          ("HeatPerFaultPerHour", s.HeatPerFaultPerHour), ("RunningCoolingPerHour", s.RunningCoolingPerHour),
          ("ShutdownCoolingPerHour", s.ShutdownCoolingPerHour), ("DecayHeatHours", s.DecayHeatHours),
          ("DecayHeatPerHour", s.DecayHeatPerHour), ("MeltdownInstantSludge", s.MeltdownInstantSludge),
          ("MeltdownSourceSludgePerHour", s.MeltdownSourceSludgePerHour), ("MeltdownSourceHours", s.MeltdownSourceHours),
          ("MeltdownFootprintWaterRadiation", s.MeltdownFootprintWaterRadiation), ("MeltdownEdgeWaterRadiation", s.MeltdownEdgeWaterRadiation) })
        if (!Positive(value)) Fail($"{name} must be positive");
      if (!(Fraction(s.RestartHeat) && s.RestartHeat < s.WarningHeat && s.WarningHeat < s.ScramHeat && Fraction(s.ScramHeat)))
        Fail("thresholds must satisfy 0 < RestartHeat < WarningHeat < ScramHeat < 1");
      if (s.MaintenanceWarningHours >= s.MaintenanceIntervalHours) Fail("MaintenanceWarningHours must be shorter than the interval");
      if (!(s.MeltdownFootprintSoilRadiation <= 1f && s.MeltdownEdgeSoilRadiation > 0f && s.MeltdownEdgeSoilRadiation <= s.MeltdownFootprintSoilRadiation))
        Fail("soil radiation must satisfy 0 < edge <= footprint <= 1");
      if (s.MeltdownEdgeWaterRadiation > s.MeltdownFootprintWaterRadiation) Fail("edge water radiation exceeds the footprint value");
      if (!(s.MeltdownKillRadius >= 0 && s.MeltdownKillRadius < s.MeltdownIrradiationRadius && s.MeltdownRadius >= 1))
        Fail("radii must satisfy 0 <= kill < irradiation and contamination >= 1");
      if (!(s.MeltdownIrradiationDose > 1f) || float.IsInfinity(s.MeltdownIrradiationDose)) Fail("MeltdownIrradiationDose must exceed 1");
    }

    // Every reactor recipe must burn the same coolant amount per cycle.
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
      }
    }

    public void InitializeEntity() {
      _overheatStatus = StatusToggle.CreatePriorityStatusWithAlertAndFloatingIcon(MeltdownSprites.Overheating,
        _loc.T(MeltdownLoc.StatusOverheating, Pct(Spec.ScramHeat)), _loc.T(MeltdownLoc.StatusOverheatingShort));
      _scramStatus = StatusToggle.CreatePriorityStatusWithAlertAndFloatingIcon(MeltdownSprites.Scram,
        _loc.T(MeltdownLoc.StatusScram, Pct(Spec.RestartHeat)), _loc.T(MeltdownLoc.StatusScramShort));
      _coolantDryStatus = StatusToggle.CreatePriorityStatusWithAlertAndFloatingIcon(MeltdownSprites.CoolantDry,
        _loc.T(MeltdownLoc.StatusCoolantDry), _loc.T(MeltdownLoc.StatusCoolantDryShort));
      _coolantLowStatus = StatusToggle.CreateNormalStatus(MeltdownSprites.CoolantLow,
        _loc.T(MeltdownLoc.StatusCoolantLow, Hours(Spec.CoolantReserveWarningHours)));
      _crewStatus = StatusToggle.CreateNormalStatus(MeltdownSprites.Crew, _loc.T(MeltdownLoc.StatusCrew, Spec.MinOperators));
      _maintenanceDueStatus = StatusToggle.CreateNormalStatus(MeltdownSprites.Maintenance,
        _loc.T(MeltdownLoc.StatusMaintenanceDue, Hours(Spec.MaintenanceOutageHours)));
      _maintenanceOverdueStatus = StatusToggle.CreateNormalStatusWithFloatingIcon(MeltdownSprites.Maintenance,
        _loc.T(MeltdownLoc.StatusMaintenanceOverdue, Hours(Spec.MaintenanceOutageHours)));
      var subject = GetComponent<StatusSubject>();
      foreach (var status in Statuses()) subject.RegisterStatus(status);
    }

    private IEnumerable<StatusToggle> Statuses() {
      yield return _overheatStatus; yield return _scramStatus; yield return _coolantDryStatus; yield return _coolantLowStatus;
      yield return _crewStatus; yield return _maintenanceDueStatus; yield return _maintenanceOverdueStatus;
    }

    public void OnEnterFinishedState() {
      // Latches start from the loaded state so a reload does not repeat alerts.
      _warningPosted = _heat >= Spec.WarningHeat;
      _imminentPosted = _heat >= Spec.ScramHeat;
      _maintenancePosted = _runHoursSinceMaintenance >= Spec.MaintenanceIntervalHours;
      _coolantDryPosted = false;
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

    public void SetAutoRestart(bool value) => _autoRestart = value;

    public override void Tick() {
      if (_meltdownRequested) return;
      float hours = _cycle.FixedDeltaTimeInHours;
      float day = _cycle.PartialDayNumber;
      bool blocked = !_blockable.IsUnblocked;
      bool running = !blocked && _scram == ReactorScram.None && _workshop.CurrentlyWorking && _manufactory.IsReadyToProduce;

      CoolantStock = _manufactory.Inventory.UnreservedAmountInStock(Spec.CoolantGoodId);
      CoolantDry = CoolantStock < CoolantPerCycle;
      OperatorsOnDuty = _workshop.NumberOfWorkersWorking;
      CrewShort = running && OperatorsOnDuty < Spec.MinOperators;

      if (running) {
        _runHoursSinceMaintenance += hours;
        _idleHours = 0f;
        _lastRunDay = day;
      } else {
        _idleHours += hours;
        if (_idleHours >= Spec.MaintenanceOutageHours && _runHoursSinceMaintenance > 0f) CompleteMaintenance();
      }
      MaintenanceOverdue = _runHoursSinceMaintenance >= Spec.MaintenanceIntervalHours;
      DecayHoursLeft = _lastRunDay < 0f ? 0f : Mathf.Max(0f, Spec.DecayHeatHours - (day - _lastRunDay) * 24f);

      if (blocked) {
        Mode = ReactorMode.ColdShutdown;
        HeatRatePerHour = -Spec.ShutdownCoolingPerHour;
      } else if (running) {
        Mode = ReactorMode.Running;
        int faults = (CoolantDry ? 1 : 0) + (CrewShort ? 1 : 0) + (MaintenanceOverdue ? 1 : 0);
        HeatRatePerHour = faults > 0 ? faults * Spec.HeatPerFaultPerHour : -Spec.RunningCoolingPerHour;
      } else {
        Mode = _scram != ReactorScram.None ? ReactorMode.Scrammed : ReactorMode.Idle;
        HeatRatePerHour = DecayHoursLeft > 0f && CoolantDry ? Spec.DecayHeatPerHour : -Spec.ShutdownCoolingPerHour;
      }
      _heat = Mathf.Clamp01(_heat + HeatRatePerHour * hours);

      if (_heat >= 1f) {
        _meltdownRequested = true;
        Mode = ReactorMode.MeltingDown;
        _meltdowns.Request(this);
        return;
      }
      if (_scram == ReactorScram.None && _heat >= Spec.ScramHeat) {
        _scram = ReactorScram.Automatic;
        _notifications.Post(_loc.T(MeltdownLoc.NotificationScram, Pct(_heat), Pct(Spec.RestartHeat)), this);
      } else if (_scram == ReactorScram.Automatic && _autoRestart && !blocked && _heat <= Spec.RestartHeat && !MaintenanceOverdue && !CoolantDry) {
        _scram = ReactorScram.None;
        _notifications.Post(_loc.T(MeltdownLoc.NotificationRestarted, Pct(_heat)), this);
      }
      PostAlerts();
      UpdateStatuses();
    }

    private void CompleteMaintenance() {
      bool wasDue = _runHoursSinceMaintenance >= Spec.MaintenanceIntervalHours - Spec.MaintenanceWarningHours;
      _runHoursSinceMaintenance = 0f;
      _maintenancePosted = false;
      if (wasDue) _notifications.Post(_loc.T(MeltdownLoc.NotificationMaintenanceDone), this);
    }

    private void PostAlerts() {
      if (_heat >= Spec.WarningHeat && !_warningPosted && HeatRatePerHour > 0f) {
        _warningPosted = true;
        _notifications.Post(_loc.T(MeltdownLoc.NotificationWarning, Pct(_heat), Causes(), Pct(Spec.ScramHeat)), this);
      } else if (_heat <= Spec.RestartHeat) _warningPosted = false;

      if (DecayDanger && !_coolantDryPosted) {
        _coolantDryPosted = true;
        _notifications.Post(_loc.T(MeltdownLoc.NotificationCoolantDry, Pct(_heat), Hours(DecayHoursLeft)), this);
      } else if (!CoolantDry) _coolantDryPosted = false;

      if (DecayDanger && _heat >= Spec.ScramHeat && !_imminentPosted) {
        _imminentPosted = true;
        _notifications.Post(_loc.T(MeltdownLoc.NotificationImminent, Pct(_heat), Hours((1f - _heat) / Spec.DecayHeatPerHour)), this);
      } else if (!DecayDanger) _imminentPosted = false;

      if (MaintenanceOverdue && !_maintenancePosted) {
        _maintenancePosted = true;
        _notifications.Post(_loc.T(MeltdownLoc.NotificationMaintenanceOverdue, Hours(Spec.MaintenanceOutageHours)), this);
      }
    }

    // Comma-separated causes of the current heating, for the warning
    // notification: running faults while running, decay heat otherwise.
    public string Causes() {
      var causes = new List<string>();
      if (Mode == ReactorMode.Running) {
        if (CoolantDry) causes.Add(_loc.T(MeltdownLoc.CauseCoolant));
        if (CrewShort) causes.Add(_loc.T(MeltdownLoc.CauseCrew, Spec.MinOperators));
        if (MaintenanceOverdue) causes.Add(_loc.T(MeltdownLoc.CauseMaintenance));
      } else if (DecayDanger) causes.Add(_loc.T(MeltdownLoc.CauseDecayHeat));
      return string.Join(", ", causes);
    }

    private void UpdateStatuses() {
      if (!Enabled) return;
      _overheatStatus.Toggle(_heat >= Spec.WarningHeat && _scram == ReactorScram.None);
      _scramStatus.Toggle(_scram != ReactorScram.None);
      _coolantDryStatus.Toggle(DecayDanger || (Mode == ReactorMode.Running && CoolantDry));
      _coolantLowStatus.Toggle(!CoolantDry && CoolantReserveHours < Spec.CoolantReserveWarningHours);
      _crewStatus.Toggle(CrewShort);
      _maintenanceOverdueStatus.Toggle(MaintenanceOverdue);
      _maintenanceDueStatus.Toggle(!MaintenanceOverdue && RunHoursUntilMaintenance <= Spec.MaintenanceWarningHours);
    }

    internal static int Pct(float fraction) => Mathf.RoundToInt(fraction * 100f);
    internal static int Hours(float hours) => Mathf.CeilToInt(hours);

    public void Save(IEntitySaver entitySaver) {
      var saver = entitySaver.GetComponent(Key);
      saver.Set(HeatKey, _heat);
      saver.Set(ScramKey, (int)_scram);
      saver.Set(AutoRestartKey, _autoRestart);
      saver.Set(RunHoursKey, _runHoursSinceMaintenance);
      saver.Set(IdleHoursKey, _idleHours);
      saver.Set(LastRunDayKey, _lastRunDay);
    }

    public void Load(IEntityLoader entityLoader) {
      // A reactor saved before the meltdown system existed starts cold.
      if (!entityLoader.TryGetComponent(Key, out var loader)) return;
      _heat = loader.Get(HeatKey);
      int scram = loader.Get(ScramKey);
      _autoRestart = loader.Get(AutoRestartKey);
      _runHoursSinceMaintenance = loader.Get(RunHoursKey);
      _idleHours = loader.Get(IdleHoursKey);
      _lastRunDay = loader.Get(LastRunDayKey);
      if (!(_heat >= 0f && _heat <= 1f) || !Enum.IsDefined(typeof(ReactorScram), scram) || !(_runHoursSinceMaintenance >= 0f)
          || !(_idleHours >= 0f) || !(_lastRunDay >= 0f || _lastRunDay == NeverRan))
        throw new InvalidOperationException($"{Name}: saved reactor core state is invalid");
      _scram = (ReactorScram)scram;
    }
  }
}
