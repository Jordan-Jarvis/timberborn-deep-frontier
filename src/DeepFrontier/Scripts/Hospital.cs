using System;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BehaviorSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.Common;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.MechanicalSystem;
using Timberborn.NeedSpecs;
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
  // working hours; their attendance drives neighborhood care and supply use.
  internal sealed class Hospital : TickableComponent, IAwakableComponent,
      IFinishedStateListener, IBuildingEfficiencyProvider {
    private HospitalSpec _spec;
    private Workplace _workplace;
    private BlockableObject _blockable;
    private MechanicalBuilding _power;
    private GoodConsumingBuilding _supplies;
    private GoodConsumingToggle _staffToggle;
    private RangedEffectBuilding _range;
    private HospitalPantry _pantry;
    private Enterable _ward;
    private IAnimator _banners;
    private bool _areaEffectAdded;
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

    public void Awake() {
      _pantry=GetComponent<HospitalPantry>(); _ward=GetComponent<Enterable>();
      if(_pantry==null||_ward==null)throw new InvalidOperationException("Hospital requires its HospitalPantry and patient Enterable");
      _spec=GetComponent<HospitalSpec>(); _workplace=GetComponent<Workplace>();
      _blockable=GetComponent<BlockableObject>(); _power=GetComponent<MechanicalBuilding>();
      _supplies=GetComponent<GoodConsumingBuilding>(); _staffToggle=_supplies.GetGoodConsumingToggle();
      _range=GetComponent<RangedEffectBuilding>();
      if(_spec.RequiredStaff<=0 || GetComponent<WorkplaceSpec>().MaxWorkers!=_spec.RequiredStaff)
        throw new InvalidOperationException("Hospital staffing must match the authored workplace capacity");
      var finished=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      _banners=finished.GetComponentsInChildren<MonoBehaviour>(true).OfType<IAnimator>().Single();
      _staffToggle.PauseConsumption(); DisableComponent();
    }
    public void OnEnterFinishedState() {
      EnableComponent(); _banners.Enabled=true; _banners.Play("Default");
    }
    public void OnExitFinishedState() {
      SetNeighborhoodCare(false); _staffToggle.PauseConsumption();
      _banners.Stop(); DisableComponent();
    }
    public override void Tick() {
      var attended=Attended;
      // Supplies are used while staff attend or patients are treated.
      if(attended || (CanUse && _ward.NumberOfEnterersInside>0))_staffToggle.ResumeConsumption();else _staffToggle.PauseConsumption();
      SetNeighborhoodCare(attended && _supplies.CanUse);
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
