using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.Localization;
using Timberborn.StatusSystem;
using Timberborn.TickSystem;
using Timberborn.WorkSystem;

namespace DeepFrontier.Scripts {
  // A workplace only trained specialists of one discipline may staff. The
  // native district assigner never sees it (SpecialistWorkplaceRegistration
  // patches); SpecialistStaffing fills its native Workplace instead, so the
  // native desired-worker controls, priority, overstaffing release, work
  // refusal (injury), unreachable release and save/reload stay native.
  internal sealed class SpecialistWorkplace : BaseComponent, IAwakableComponent, IInitializableEntity, IFinishedStateListener {
    private readonly SpecialistStaffing _staffing;
    private readonly WorkforceSettings _settings;
    private readonly ILoc _loc;
    private StatusToggle _noneStatus;
    private StatusToggle _shortStatus;

    public string Discipline { get; private set; }
    public Workplace Workplace { get; private set; }
    public WorkplacePriority Priority { get; private set; }
    public DistrictBuilding DistrictBuilding { get; private set; }
    // Unassigned specialists of this discipline in the district after the last staffing pass.
    public int AvailableSpecialists { get; private set; }

    public SpecialistWorkplace(SpecialistStaffing staffing, WorkforceSettings settings, ILoc loc) {
      _staffing=staffing;_settings=settings;_loc=loc;
    }

    public void Awake() {
      Discipline=GetComponent<FrontierSpecialistWorkplaceSpec>().Discipline;
      Workplace=GetComponent<Workplace>();
      Priority=GetComponent<WorkplacePriority>();
      DistrictBuilding=GetComponent<DistrictBuilding>();
      var workplace=GetComponent<WorkplaceSpec>();
      if(!Workplace||!Priority||!DistrictBuilding||workplace==null)
        throw new InvalidOperationException($"{Name}: a specialist workplace must be a native district workplace");
      if(!workplace.DisallowOtherWorkerTypes||workplace.DefaultWorkerType!="Beaver"||workplace.WorkerTypeUnlockCosts.Length>0)
        throw new InvalidOperationException($"{Name}: specialists are beavers; the workplace must be beaver-only with no bot unlock");
    }

    public void InitializeEntity() {
      var spec=_settings.Discipline(Discipline);
      var plural=_loc.T(spec.PluralDisplayNameLocKey);
      _noneStatus=StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon("NoUnemployed",
        _loc.T("DeepFrontier.Workforce.Status.NoSpecialists",plural),
        _loc.T("DeepFrontier.Workforce.Status.NoSpecialists.Short",plural));
      _shortStatus=StatusToggle.CreateNormalStatus("NoUnemployed",_loc.T("DeepFrontier.Workforce.Status.FewSpecialists",plural));
      var subject=GetComponent<StatusSubject>();
      subject.RegisterStatus(_noneStatus);
      subject.RegisterStatus(_shortStatus);
    }

    public void OnEnterFinishedState() {_staffing.Register(this);}

    public void OnExitFinishedState() {
      _staffing.Unregister(this);
      _noneStatus.Deactivate();
      _shortStatus.Deactivate();
    }

    public bool Accepts(Worker worker) {
      var trait=worker.GetComponent<SpecialistTrait>();
      return trait&&trait.Has(Discipline);
    }

    internal void UpdateStatus(int available) {
      AvailableSpecialists=available;
      var shortfall=Workplace.Understaffed; // native: unblocked and below desired workers
      var none=shortfall&&Workplace.NumberOfAssignedWorkers==0;
      if(none)_noneStatus.Activate();else _noneStatus.Deactivate();
      if(shortfall&&!none)_shortStatus.Activate();else _shortStatus.Deactivate();
    }
  }

  // Fills specialist workplaces from the specialist roster, every tick, in
  // native priority order (VeryHigh first). A matching specialist is taken
  // unemployed first, otherwise from an ordinary job; specialists already on
  // another specialist crew are never moved. Native assignment of the freed
  // ordinary job then proceeds as usual.
  internal sealed class SpecialistStaffing : ITickableSingleton {
    private readonly SpecialistRoster _roster;
    private readonly List<SpecialistWorkplace> _workplaces=new List<SpecialistWorkplace>();
    private readonly List<Worker> _scratch=new List<Worker>();

    public SpecialistStaffing(SpecialistRoster roster) {_roster=roster;}

    public void Register(SpecialistWorkplace workplace) {
      if(!_workplaces.Contains(workplace))_workplaces.Add(workplace);
    }

    public void Unregister(SpecialistWorkplace workplace) {_workplaces.Remove(workplace);}

    public void Tick() {
      if(_workplaces.Count==0)return;
      foreach(var workplace in _workplaces.OrderByDescending(w=>w.Priority.Priority)) {
        ReleaseUnqualified(workplace);
        while(workplace.Workplace.Understaffed) {
          var candidate=FindCandidate(workplace);
          if(!candidate)break;
          if(candidate.Worker.Workplace)candidate.Worker.Unemploy();
          workplace.Workplace.AssignWorker(candidate.Worker);
        }
        workplace.UpdateStatus(CountAvailable(workplace));
      }
    }

    // Saves from before a workplace became specialist-only re-employ their old
    // crew natively after load; anyone without the discipline is released.
    private void ReleaseUnqualified(SpecialistWorkplace workplace) {
      _scratch.Clear();
      foreach(var worker in workplace.Workplace.AssignedWorkers)
        if(!workplace.Accepts(worker))_scratch.Add(worker);
      foreach(var worker in _scratch)workplace.Workplace.UnassignWorker(worker);
    }

    // 0 = unemployed, 1 = employed at an ordinary workplace, -1 = not available.
    private static int Rank(SpecialistTrait trait, SpecialistWorkplace workplace) {
      if(!trait.Alive||!trait.Has(workplace.Discipline))return -1;
      var district=workplace.DistrictBuilding.District;
      if(!district||trait.Citizen.AssignedDistrict!=district)return -1;
      if(trait.Worker.GetComponent<WorkRefuser>().RefusesWork)return -1;
      var current=trait.Worker.Workplace;
      if(!current)return 0;
      if(current.GetComponent<SpecialistWorkplace>())return -1;
      return 1;
    }

    private SpecialistTrait FindCandidate(SpecialistWorkplace workplace) {
      SpecialistTrait best=null;
      var bestRank=int.MaxValue;
      foreach(var trait in _roster.All) {
        var rank=Rank(trait,workplace);
        if(rank>=0&&rank<bestRank) {best=trait;bestRank=rank;}
      }
      return best;
    }

    private int CountAvailable(SpecialistWorkplace workplace) {
      var count=0;
      foreach(var trait in _roster.All)if(Rank(trait,workplace)>=0)count++;
      return count;
    }
  }
}
