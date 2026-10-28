#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.CoreUI;
using Timberborn.EntityPanelSystem;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.Localization;
using Timberborn.MechanicalSystem;
using Timberborn.NotificationSystem;
using Timberborn.Persistence;
using Timberborn.StatusSystem;
using Timberborn.Stockpiles;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WorldPersistence;
using TimberPipes.Components;
using TimberPipes.Services;
using TimberPipes.Specs;

namespace DeepFrontier.Scripts.Cryogenics {
  // Powered cryogenic fuel storage (CryogenicTankSpec) on a native liquid
  // Stockpile that Timber Pipes 11.4.0 treats as an in-network PipeTank.
  //
  // Each tick: accepting = MechanicalBuilding.ActiveAndPowered (finished,
  // BlockableObject unblocked, and the shaft graph powered). Pause and
  // automation Off block that BlockableObject, so they count as power loss.
  // While not accepting, CryogenicIntakeGate closes intake immediately; after
  // BufferHours the tank vents VentPerHourOnPowerLoss units per hour of its
  // unreserved stock until power returns. Power restores intake and resets the
  // buffer. The outage clock, fractional vent and amount vented this outage are
  // saved; a notification is posted when an outage first vents fuel.
  //
  // Separate networks: Timber Pipes contaminates a pipe network whose fluid
  // differs from the tank's stock (PipeFluidSimulator.Simulate ->
  // PipeTank.ConflictsWith), with its own status and alert on the pipes. An
  // empty tank instead refuses a foreign fluid silently (no capacity for it);
  // this component's wrong-network status makes both cases visible at the tank.
  internal sealed class CryogenicTank : TickableComponent, IAwakableComponent, IInitializableEntity,
      IFinishedStateListener, IPersistentEntity, IEntityDescriber {
    private static readonly ComponentKey TankKey = new ComponentKey("DeepFrontier.CryogenicTank");
    private static readonly PropertyKey<float> UnpoweredHoursKey = new PropertyKey<float>("UnpoweredHours");
    private static readonly PropertyKey<float> VentRemainderKey = new PropertyKey<float>("VentRemainder");
    private static readonly PropertyKey<int> VentedThisOutageKey = new PropertyKey<int>("VentedThisOutage");
    private const string LiquidGoodType = "Liquid";

    private readonly IDayNightCycle _dayNightCycle;
    private readonly NotificationBus _notifications;
    private readonly IGoodService _goods;
    private readonly PipeRegistry _pipes;
    private readonly ILoc _loc;
    private CryogenicTankSpec _spec;
    private MechanicalBuilding _power;
    private SingleGoodAllower _allower;
    private BuildingPipe _pipe;
    private LabeledEntity _label;
    private CryogenicIntakeGate _gate;
    private StatusToggle _holdingStatus, _ventingStatus, _wrongGoodStatus, _wrongNetworkStatus;
    private bool _finished;
    private float _unpoweredHours, _ventRemainder;
    private int _ventedThisOutage;

    public CryogenicTank(IDayNightCycle dayNightCycle, NotificationBus notifications, IGoodService goods,
        PipeRegistry pipes, ILoc loc) {
      _dayNightCycle = dayNightCycle; _notifications = notifications; _goods = goods; _pipes = pipes; _loc = loc;
    }

    public CryogenicTankSpec Spec => _spec;
    public bool Accepting => _gate.Accepting;
    public float UnpoweredHours => _unpoweredHours;
    public int VentedThisOutage => _ventedThisOutage;
    public bool IsVenting => _finished && !_gate.Accepting && _unpoweredHours > _spec.BufferHours;

    public void Awake() {
      _spec = GetComponent<CryogenicTankSpec>();
      if (_spec.Goods.IsDefaultOrEmpty) throw new InvalidOperationException("CryogenicTankSpec.Goods is empty");
      if (!(_spec.VentPerHourOnPowerLoss > 0f) || !(_spec.BufferHours > 0f))
        throw new InvalidOperationException("CryogenicTankSpec needs positive VentPerHourOnPowerLoss and BufferHours");
      foreach (var id in _spec.Goods) {
        if (!_goods.HasGood(id)) throw new InvalidOperationException($"Cryogenic tank good {id} is not a registered good");
        if (_goods.GetGood(id).GoodType != LiquidGoodType) throw new InvalidOperationException($"Cryogenic tank good {id} must be a {LiquidGoodType} good");
      }
      _power = GetComponent<MechanicalBuilding>();
      if (!_power) throw new InvalidOperationException("Cryogenic tank needs MechanicalBuilding (a powered MechanicalNode)");
      if (!GetComponent<Stockpile>() || GetComponent<StockpileSpec>().WhitelistedGoodType != LiquidGoodType)
        throw new InvalidOperationException($"Cryogenic tank needs a native {LiquidGoodType} Stockpile");
      _allower = GetComponent<SingleGoodAllower>();
      // Without explicit sockets Timber Pipes' TankPipe opens every exposed face.
      var sockets = GetComponent<BuildingPipeSpec>();
      if (sockets == null || sockets.Ports.IsDefaultOrEmpty)
        throw new InvalidOperationException("Cryogenic tank needs explicit Timber Pipes sockets (BuildingPipeSpec.Ports)");
      _pipe = GetComponent<BuildingPipe>();
      if (!_pipe) throw new InvalidOperationException("Cryogenic tank has no Timber Pipes BuildingPipe");
      _label = GetComponent<LabeledEntity>();
      var goodNames = new List<string>();
      foreach (var id in _spec.Goods) goodNames.Add(_loc.T(_goods.GetGood(id).DisplayNameLocKey));
      _holdingStatus = StatusToggle.CreateNormalStatus(CryogenicSprites.Holding,
        _loc.T(CryogenicLoc.StatusHolding, Number(_spec.BufferHours)));
      _ventingStatus = StatusToggle.CreatePriorityStatusWithAlertAndFloatingIcon(CryogenicSprites.Venting,
        _loc.T(CryogenicLoc.StatusVenting, Number(_spec.VentPerHourOnPowerLoss)), _loc.T(CryogenicLoc.StatusVentingShort));
      _wrongGoodStatus = StatusToggle.CreateNormalStatusWithFloatingIcon(CryogenicSprites.WrongGood,
        _loc.T(CryogenicLoc.StatusWrongGood, string.Join(", ", goodNames)));
      _wrongNetworkStatus = StatusToggle.CreatePriorityStatusWithAlertAndFloatingIcon(CryogenicSprites.WrongNetwork,
        _loc.T(CryogenicLoc.StatusWrongNetwork), _loc.T(CryogenicLoc.StatusWrongNetworkShort));
      DisableComponent();
    }

    public void InitializeEntity() {
      _gate = CryogenicIntakeGate.For(_allower);
      GetComponent<StatusSubject>().RegisterStatuses(new[] {_holdingStatus, _ventingStatus, _wrongGoodStatus, _wrongNetworkStatus});
    }

    public void OnEnterFinishedState() {
      _finished = true;
      EnableComponent();
    }

    public void OnExitFinishedState() {
      _finished = false;
      _gate.SetAccepting(true);
      _holdingStatus.Deactivate(); _ventingStatus.Deactivate(); _wrongGoodStatus.Deactivate(); _wrongNetworkStatus.Deactivate();
      DisableComponent();
    }

    public override void Tick() {
      bool powered = _power.ActiveAndPowered;
      _gate.SetAccepting(powered);
      if (powered) {
        _unpoweredHours = 0f; _ventRemainder = 0f; _ventedThisOutage = 0;
      } else {
        float before = _unpoweredHours;
        _unpoweredHours += _dayNightCycle.FixedDeltaTimeInHours;
        float ventHours = _unpoweredHours - Math.Max(before, _spec.BufferHours);
        if (ventHours > 0f) Vent(ventHours);
      }
      bool holdsFuel = HoldsFuel();
      bool venting = !powered && _unpoweredHours > _spec.BufferHours;
      _holdingStatus.Toggle(!powered && !venting && holdsFuel);
      _ventingStatus.Toggle(venting && holdsFuel);
      string selected = _allower.AllowedGood;
      _wrongGoodStatus.Toggle(selected != null && !_gate.IsCryogenicGood(selected));
      _wrongNetworkStatus.Toggle(ConnectedToForeignNetwork(selected));
    }

    // Unreserved stock only: units a hauler or shopper already reserved leave
    // with them; the due amount for this tick is not carried over.
    private void Vent(float hours) {
      _ventRemainder += hours * _spec.VentPerHourOnPowerLoss;
      int due = (int)Math.Floor(_ventRemainder);
      if (due <= 0) return;
      _ventRemainder -= due;
      var inventory = _gate.Inventory;
      int vented = 0;
      foreach (var good in _gate.Goods) {
        if (due == 0) break;
        int amount = Math.Min(due, inventory.UnreservedAmountInStock(good));
        if (amount <= 0) continue;
        inventory.TakeExisting(new GoodAmount(good, amount));
        due -= amount;
        vented += amount;
      }
      if (vented == 0) return;
      if (_ventedThisOutage == 0) _notifications.Post(_loc.T(CryogenicLoc.NotificationVenting, _label.DisplayName), this);
      _ventedThisOutage += vented;
    }

    private bool HoldsFuel() {
      var inventory = _gate.Inventory;
      foreach (var good in _gate.Goods) if (inventory.AmountInStock(good) > 0) return true;
      return false;
    }

    // A pipe network attached at a socket that is contaminated, or carries a
    // fluid other than the selected good, cannot exchange fuel with this tank.
    private bool ConnectedToForeignNetwork(string selected) {
      var ports = _pipe.Ports;
      if (ports == null) return false;
      foreach (var port in ports.Values) {
        if (!port.IsConnected || !_pipes.TryGetConnectedBuilding(port, out var neighbour)) continue;
        var graph = neighbour.Graph;
        if (graph == null) continue;
        if (graph.Contaminated) return true;
        if (selected != null && graph.FluidGoodId != null && graph.FluidGoodId != selected) return true;
      }
      return false;
    }

    public IEnumerable<EntityDescription> DescribeEntity() {
      string text;
      if (!_finished || _gate.Accepting)
        text = _loc.T(CryogenicLoc.DescribeRules, Number(_spec.BufferHours), Number(_spec.VentPerHourOnPowerLoss));
      else if (_unpoweredHours <= _spec.BufferHours)
        text = _loc.T(CryogenicLoc.DescribeHolding, Number(_spec.BufferHours - _unpoweredHours));
      else
        text = _loc.T(CryogenicLoc.DescribeVenting, Number(_spec.VentPerHourOnPowerLoss), _ventedThisOutage);
      yield return EntityDescription.CreateTextSection(SpecialStrings.RowStarter + text, 1030);
    }

    private static string Number(float value) => value.ToString("0.#");

    public void Save(IEntitySaver entitySaver) {
      if (_unpoweredHours <= 0f && _ventRemainder <= 0f && _ventedThisOutage == 0) return;
      var saver = entitySaver.GetComponent(TankKey);
      saver.Set(UnpoweredHoursKey, _unpoweredHours);
      saver.Set(VentRemainderKey, _ventRemainder);
      saver.Set(VentedThisOutageKey, _ventedThisOutage);
    }

    public void Load(IEntityLoader entityLoader) {
      if (!entityLoader.TryGetComponent(TankKey, out var loader)) return;
      _unpoweredHours = loader.Get(UnpoweredHoursKey);
      _ventRemainder = loader.Get(VentRemainderKey);
      _ventedThisOutage = loader.Get(VentedThisOutageKey);
    }
  }

  // Native status icons (Sprites/StatusIcons, 1.1.2.8) plus Timber Pipes'
  // own PipeContamination icon (required dependency, version-1.1 package).
  internal static class CryogenicSprites {
    public const string Holding = "NoPower";
    public const string Venting = "Empty";
    public const string WrongGood = "UnspecifiedGood";
    public const string WrongNetwork = "PipeContamination";
  }

  // Keys of Localizations/enUS_cryogenics.csv (tools/cryogenic_content.mjs).
  internal static class CryogenicLoc {
    public const string StatusHolding = "DeepFrontier.Cryogenics.Status.Holding";
    public const string StatusVenting = "DeepFrontier.Cryogenics.Status.Venting";
    public const string StatusVentingShort = "DeepFrontier.Cryogenics.Status.Venting.Short";
    public const string StatusWrongGood = "DeepFrontier.Cryogenics.Status.WrongGood";
    public const string StatusWrongNetwork = "DeepFrontier.Cryogenics.Status.WrongNetwork";
    public const string StatusWrongNetworkShort = "DeepFrontier.Cryogenics.Status.WrongNetwork.Short";
    public const string NotificationVenting = "DeepFrontier.Cryogenics.Notification.Venting";
    public const string DescribeRules = "DeepFrontier.Cryogenics.Describe.Rules";
    public const string DescribeHolding = "DeepFrontier.Cryogenics.Describe.Holding";
    public const string DescribeVenting = "DeepFrontier.Cryogenics.Describe.Venting";
  }
}
#endif
