using System;
using System.Collections.Immutable;
using System.Linq;
using Bindito.Core;
using Timberborn.Attractions;
using Timberborn.BaseComponentSystem;
using Timberborn.BehaviorSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.Common;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.InventorySystem;
using Timberborn.MechanicalSystem;
using Timberborn.NeedSpecs;
using Timberborn.NeedSystem;
using Timberborn.Localization;
using Timberborn.StatusSystem;
using Timberborn.RangedEffectSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.TimbermeshAnimations;
using Timberborn.WalkingSystem;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  internal record HospitalSpec : ComponentSpec {
    [Serialize] public Vector3 WardWorkPosition { get; init; }
    [Serialize] public int RequiredStaff { get; init; }
    [Serialize] public ContinuousEffectSpec NeighborhoodEffect { get; init; }
    // The good each supplied treatment consumes (GoodConsumingBuildingSpec
    // ConsumedGoods, one each); every other attraction effect needs none.
    [Serialize] public ImmutableArray<HospitalTreatmentSupplySpec> TreatmentSupplies { get; init; }
  }

  internal record HospitalTreatmentSupplySpec {
    [Serialize] public string NeedId { get; init; }
    [Serialize] public string GoodId { get; init; }
  }

  // Native Attraction owns condition recovery, Enterable owns the thirty
  // patient reservations, and GoodConsumingBuilding owns/persists supplies.
  // This component contributes the ward crew, staff attendance and
  // neighborhood care; HospitalPantry feeds admitted patients.
  //
  // Admission and stay (Timberborn 1.1.2.8): native Attraction.IsUsable is
  // every IBuildingEfficiencyProvider's CanUse, and AttractionNeedBehavior
  // releases a patient on its next decision once it is false. Every effect has
  // SatisfyToMaxValue, so patients stay until all four conditions are cured;
  // CanUse therefore holds while the ward has an assigned crew (on call day and
  // night), not only while staff stand at the ward, or every patient would be
  // sent out at the end of each working day. It closes for meals only when an
  // admitted patient is starving or dehydrated and the pantry is out of what
  // it needs (HospitalPantry.MealsShort); admission never waits for a
  // delivery, although admitted patients cannot leave to eat. Treatment runs at the
  // crew's strength, around the clock. Staff still attend the ward during
  // working hours; their attendance drives neighborhood care.
  //
  // Supplies are per treatment (user 2026-11-09; HospitalSpec.TreatmentSupplies):
  // injuries and chipped teeth need none (as the vanilla Medical Bed and Teeth
  // Grindstone), decontamination consumes Extract (as the Decontamination Pod)
  // and radiation care consumes Medicine. A treatment is supplied while its good
  // is in the ward (a native fractional dose or unreserved stock).
  // HospitalMedicalSupplies consumes each good only while an admitted patient
  // needs its treatment, applies only supplied effects and reports per-treatment
  // hours; HospitalMedicalVisits neither admits nor keeps a patient for
  // unsupplied treatments alone. Each missing supply has its own status, shown
  // as native LackOfResourcesStatus would be (open, none in the district).
  internal sealed class Hospital : TickableComponent, IAwakableComponent,
      IFinishedStateListener, IInitializableEntity, IBuildingEfficiencyProvider {
    // Native AttractionNeedBehavior.MaxValueTolerance (1.1.2.8): a need closer to
    // its maximum is satisfied.
    internal const float NeedTolerance = 0.001f;
    private readonly ILoc _loc;
    private HospitalSpec _spec;
    private Workplace _workplace;
    private BlockableObject _blockable;
    private MechanicalBuilding _power;
    private GoodConsumingBuilding _supplies;
    private GoodConsumingToggle _staffToggle;
    private RangedEffectBuilding _range;
    private Attraction _attraction;
    private HospitalPantry _pantry;
    private Enterable _ward;
    private DistrictBuilding _district;
    private IAnimator _banners;
    private bool _areaEffectAdded;
    // Per native consumed good, in ConsumedGoods order: its treatment, good and status.
    private string[] _supplyNeeds;
    private string[] _supplyGoods;
    private StatusToggle[] _supplyStatuses;
    public Hospital(ILoc loc) { _loc = loc; }
    public Vector3 WardPosition => Transform.TransformPoint(_spec.WardWorkPosition);
    public bool IsOperating => Enabled && _blockable.IsUnblocked && _power.ActiveAndPowered;
    public int AttendingStaff => _workplace.AssignedWorkers.Count(w=>
      w.JobRunning && w.GetComponent<WorkerWorkingHours>().AreWorkingHours
      && w.GetComponent<BehaviorManager>().IsRunningBehavior<HospitalWorkBehavior>()
      && Vector3.Distance(w.Transform.position,WardPosition)<.3f);
    public int CrewAssigned => Math.Min(_workplace.NumberOfAssignedWorkers,_spec.RequiredStaff);
    public bool Attended => IsOperating && AttendingStaff>0;
    public bool CanUse => IsOperating && CrewAssigned>0 && _pantry.Enabled && !_pantry.MealsShort;
    public float Efficiency => (float)CrewAssigned/_spec.RequiredStaff;
    public bool ProvidesNeighborhoodCare => _areaEffectAdded;
    public HospitalPantry Pantry => _pantry;
    public int SupplyCount => _supplyNeeds.Length;
    public string SupplyNeed(int index) => _supplyNeeds[index];
    public string SupplyGood(int index) => _supplyGoods[index];

    // Index of the native consumed good a treatment uses; -1 when it needs none.
    public int SupplyIndex(string needId) {
      for (int i = 0; i < _supplyNeeds.Length; i++) if (_supplyNeeds[i] == needId) return i;
      return -1;
    }

    // Its good is in the ward: a native fractional dose (ProcessedGoods) or unreserved stock.
    public bool SupplyAvailable(int index) {
      var good = _supplyGoods[index];
      if (_supplies.Inventory.UnreservedAmountInStock(good) > 0) return true;
      var dosed = _supplies.ProcessedGoods;
      for (int i = 0; i < dosed.Count; i++) if (dosed[i].GoodId == good) return true;
      return false;
    }

    public bool TreatmentSupplied(string needId) {
      int index = SupplyIndex(needId);
      return index < 0 || SupplyAvailable(index);
    }

    // The ward treats this condition now: open (CanUse) and its supply, if any, available.
    public bool CanTreat(string needId) => CanUse && TreatmentSupplied(needId);

    // The beaver has a condition the ward can treat with its current supplies.
    internal bool HasTreatableNeed(NeedManager needs) {
      var effects = _attraction.Effects;
      for (int i = 0; i < effects.Count; i++) {
        var id = effects[i].NeedId;
        if (needs.NeedPointsToMax(id) > NeedTolerance && TreatmentSupplied(id)) return true;
      }
      return false;
    }

    // An admitted patient needs the treatment of consumed good `index`.
    internal bool SupplyInUse(int index) {
      var need = _supplyNeeds[index];
      foreach (var patient in _ward.EnterersInside)
        if (patient.GetComponent<NeedManager>().NeedPointsToMax(need) > NeedTolerance) return true;
      return false;
    }

    public void Awake() {
      _pantry=GetComponent<HospitalPantry>(); _ward=GetComponent<Enterable>();
      if(_pantry==null||_ward==null)throw new InvalidOperationException("Hospital requires its HospitalPantry and patient Enterable");
      _spec=GetComponent<HospitalSpec>(); _workplace=GetComponent<Workplace>();
      _blockable=GetComponent<BlockableObject>(); _power=GetComponent<MechanicalBuilding>();
      _supplies=GetComponent<GoodConsumingBuilding>(); _staffToggle=_supplies.GetGoodConsumingToggle();
      _attraction=GetComponent<Attraction>();
      if(_attraction==null)throw new InvalidOperationException("Hospital requires its native Attraction");
      _range=GetComponent<RangedEffectBuilding>();
      _district=GetComponent<DistrictBuilding>();
      if(_district==null)throw new InvalidOperationException("Hospital requires the native DistrictBuilding");
      if(_spec.RequiredStaff<=0 || GetComponent<WorkplaceSpec>().MaxWorkers!=_spec.RequiredStaff)
        throw new InvalidOperationException("Hospital staffing must match the authored workplace capacity");
      ReadTreatmentSupplies();
      var finished=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      _banners=finished.GetComponentsInChildren<MonoBehaviour>(true).OfType<IAnimator>().Single();
      _staffToggle.PauseConsumption(); DisableComponent();
    }
    // Every consumed good serves exactly one treatment of the attraction, and
    // every supplied treatment names a consumed good (generated by
    // tools/hospital_building_content.mjs; checked by validate_radiation_content).
    private void ReadTreatmentSupplies() {
      var consumed = GetComponent<GoodConsumingBuildingSpec>().ConsumedGoods;
      var effects = GetComponent<AttractionSpec>().Effects;
      var supplies = _spec.TreatmentSupplies;
      if (supplies.IsDefault || supplies.Length != consumed.Length)
        throw new InvalidOperationException("Hospital: every consumed good must be the supply of one treatment (HospitalSpec.TreatmentSupplies)");
      _supplyNeeds = new string[consumed.Length];
      _supplyGoods = new string[consumed.Length];
      for (int i = 0; i < consumed.Length; i++) {
        var good = consumed[i].GoodId;
        var matches = supplies.Where(s => s.GoodId == good).ToList();
        if (matches.Count != 1) throw new InvalidOperationException($"Hospital: consumed good {good} must supply exactly one treatment");
        var need = matches[0].NeedId;
        if (!effects.Any(e => e.NeedId == need)) throw new InvalidOperationException($"Hospital: supplied treatment {need} is not an attraction effect");
        if (_supplyNeeds.Contains(need)) throw new InvalidOperationException($"Hospital: treatment {need} has two supplies");
        _supplyNeeds[i] = need;
        _supplyGoods[i] = good;
      }
    }

    public void InitializeEntity() {
      _supplyStatuses = new StatusToggle[_supplyGoods.Length];
      var subject = GetComponent<StatusSubject>();
      for (int i = 0; i < _supplyGoods.Length; i++) {
        var key = "DeepFrontier.Hospital.Status." + _supplyGoods[i];
        _supplyStatuses[i] = StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon("LackOfResources", _loc.T(key), _loc.T(key + ".Short"));
        subject.RegisterStatus(_supplyStatuses[i]);
      }
    }
    public void OnEnterFinishedState() {
      EnableComponent(); _banners.Enabled=true; _banners.Play("Default");
    }
    public void OnExitFinishedState() {
      SetNeighborhoodCare(false); _staffToggle.PauseConsumption();
      foreach (var status in _supplyStatuses) status.Deactivate();
      _banners.Stop(); DisableComponent();
    }
    public override void Tick() {
      var attended=Attended;
      // Supplies are used while staff attend or patients are treated.
      if(attended || (CanUse && _ward.NumberOfEnterersInside>0))_staffToggle.ResumeConsumption();else _staffToggle.PauseConsumption();
      // Neighborhood care uses no supplies, as no ward treatment requires one by itself.
      SetNeighborhoodCare(attended);
      // As native LackOfResourcesStatus: the ward open, its good missing here and in the district.
      var district = _district.District;
      var stock = district ? district.GetComponent<DistrictInventoryRegistry>() : null;
      for (int i = 0; i < _supplyGoods.Length; i++)
        _supplyStatuses[i].Toggle(CanUse && stock != null && !SupplyAvailable(i) && stock.ActiveInventoriesWithStock(_supplyGoods[i]).Count == 0);
    }
    private void SetNeighborhoodCare(bool active) {
      if(active==_areaEffectAdded)return;
      if(active)_range.AddEffect(_spec.NeighborhoodEffect);else _range.RemoveEffect(_spec.NeighborhoodEffect);
      _areaEffectAdded=active;
    }
  }

  // Staff use native walking/waiting without reserving a patient place.
  // Native supply-hauling workplace behaviors run before this ward activity.
  internal sealed class HospitalWorkBehavior : WorkplaceBehavior {
    public override Decision Decide(BehaviorAgent agent) {
      var hospital=GetComponent<Hospital>();
      if(!hospital.IsOperating)return Decision.ReleaseNow();
      var walk=agent.GetComponent<WalkToPositionExecutor>();
      switch(walk.Launch(hospital.WardPosition)) {
        case ExecutorStatus.Running:return Decision.ReleaseWhenFinished(walk);
        case ExecutorStatus.Failure:return Decision.ReleaseNextTick();
        case ExecutorStatus.Success:
          var wait=agent.GetComponent<WaitExecutor>();wait.LaunchForSpecifiedTime(.05f);
          return Decision.ReleaseWhenFinished(wait);
        default:throw new ArgumentOutOfRangeException();
      }
    }
  }

  [Context("Game")]
  public sealed class HospitalConfigurator : Configurator {
    protected override void Configure() {
      Bind<Hospital>().AsTransient(); Bind<HospitalWorkBehavior>().AsTransient();
      MultiBind<TemplateModule>().ToProvider<ModuleProvider>().AsSingleton();
    }
    private sealed class ModuleProvider : IProvider<TemplateModule> {
      public TemplateModule Get() {
        var builder=new TemplateModule.Builder();
        builder.AddDecorator<HospitalSpec,Hospital>();
        builder.AddDecorator<Hospital,HospitalWorkBehavior>();
        return builder.Build();
      }
    }
  }
}
