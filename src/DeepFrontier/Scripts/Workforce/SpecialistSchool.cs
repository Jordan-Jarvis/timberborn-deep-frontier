using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.Localization;
using Timberborn.Persistence;
using Timberborn.StatusSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WorkSystem;
using Timberborn.Workshops;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts {
  // Technical School training. Each programme is a native Manufactory recipe
  // without products (the native Bot Assembler pattern): haulers deliver its
  // supplies, workers run the course, and Manufactory.ProductionFinished
  // graduates one trainee in the programme's discipline. Workers who are not
  // specialists accumulate TrainingHours while the course runs; the one with
  // the most hours graduates. Specialists working here count as instructors
  // (they speed the course) and never retrain. A course that finishes with no
  // eligible trainee is kept as a pending graduation, never discarded.
  internal sealed class SpecialistSchool : TickableComponent, IAwakableComponent, IInitializableEntity,
      IFinishedStateListener, IPersistentEntity {
    private static readonly ComponentKey Key=new("DeepFrontier.SpecialistSchool");
    private static readonly ListKey<string> PendingKey=new("PendingGraduations");

    private readonly WorkforceSettings _settings;
    private readonly IDayNightCycle _cycle;
    private readonly ILoc _loc;
    private readonly Dictionary<string, string> _programs=new Dictionary<string, string>();
    private readonly List<string> _pending=new List<string>();
    private Workplace _workplace;
    private Workshop _workshop;
    private Manufactory _manufactory;
    private Enterable _enterable;
    private StatusToggle _noTraineeStatus;

    public IReadOnlyList<string> PendingGraduations=>_pending;
    public IReadOnlyDictionary<string, string> Programs=>_programs;
    public string CurrentDiscipline=>_manufactory.HasCurrentRecipe?_programs[_manufactory.CurrentRecipe.Id]:null;
    public Workplace Workplace=>_workplace;

    public SpecialistSchool(WorkforceSettings settings, IDayNightCycle cycle, ILoc loc) {
      _settings=settings;_cycle=cycle;_loc=loc;
    }

    public void Awake() {
      _workplace=GetComponent<Workplace>();
      _workshop=GetComponent<Workshop>();
      _manufactory=GetComponent<Manufactory>();
      _enterable=GetComponent<Enterable>();
      if(!_workplace||!_workshop||!_manufactory||!_enterable)
        throw new InvalidOperationException($"{Name}: a specialist school must be a native manufactory workplace");
      foreach(var program in GetComponent<FrontierSpecialistSchoolSpec>().Programs)
        if(!_programs.TryAdd(program.RecipeId,program.Discipline))
          throw new InvalidOperationException($"{Name}: training recipe {program.RecipeId} is declared twice");
      DisableComponent();
    }

    public void InitializeEntity() {
      foreach(var discipline in _programs.Values)_settings.Discipline(discipline);
      var recipes=_manufactory.ProductionRecipes.Select(r=>r.Id).ToHashSet();
      if(!recipes.SetEquals(_programs.Keys))
        throw new InvalidOperationException($"{Name}: production recipes [{string.Join(", ",recipes)}] must be exactly the training programmes [{string.Join(", ",_programs.Keys)}]");
      foreach(var recipe in _manufactory.ProductionRecipes)
        if(recipe.Products.Length>0)
          throw new InvalidOperationException($"{Name}: training recipe {recipe.Id} must not produce goods");
      _manufactory.ProductionFinished+=OnProductionFinished;
      _noTraineeStatus=StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon("NoUnemployed",
        _loc.T("DeepFrontier.Workforce.Status.NoTrainee"),_loc.T("DeepFrontier.Workforce.Status.NoTrainee.Short"));
      GetComponent<StatusSubject>().RegisterStatus(_noTraineeStatus);
    }

    public void OnEnterFinishedState() {EnableComponent();}

    public void OnExitFinishedState() {
      _noTraineeStatus.Deactivate();
      DisableComponent();
    }

    public void Save(IEntitySaver saver) {
      saver.GetComponent(Key).Set(PendingKey,_pending);
    }

    public void Load(IEntityLoader loader) {
      if(!loader.TryGetComponent(Key,out var data))return; // school saved before training existed
      foreach(var discipline in data.Get(PendingKey)) {
        if(!_programs.ContainsValue(discipline))
          throw new InvalidOperationException($"{Name}: saved pending graduation {discipline} has no training programme");
        _pending.Add(discipline);
      }
    }

    public override void Tick() {
      if(_workshop.CurrentlyWorking&&_manufactory.HasCurrentRecipe) {
        var hours=_cycle.FixedDeltaTimeInHours;
        foreach(var worker in _workplace.AssignedWorkers) {
          if(worker.GetComponent<Enterer>().CurrentBuilding!=_enterable)continue;
          var trait=Trait(worker);
          if(!trait.IsSpecialist)trait.AddTrainingHours(hours);
        }
      }
      while(_pending.Count>0&&TryGraduate(_pending[0]))_pending.RemoveAt(0);
      if(_pending.Count>0)_noTraineeStatus.Activate();else _noTraineeStatus.Deactivate();
    }

    public SpecialistTrait NextGraduate() {
      SpecialistTrait best=null;
      foreach(var worker in _workplace.AssignedWorkers) {
        var trait=Trait(worker);
        if(trait.IsSpecialist)continue;
        if(!best||trait.TrainingHours>best.TrainingHours)best=trait;
      }
      return best;
    }

    // The school is beaver-only, so every worker is an adult beaver.
    private SpecialistTrait Trait(Worker worker) {
      var trait=worker.GetComponent<SpecialistTrait>();
      if(!trait)throw new InvalidOperationException($"{Name}: {worker.Name} has no SpecialistTrait; the school must be beaver-only");
      return trait;
    }

    private bool TryGraduate(string discipline) {
      var trainee=NextGraduate();
      if(!trainee)return false;
      trainee.Graduate(discipline);
      return true;
    }

    private void OnProductionFinished(object sender, EventArgs e) {
      var discipline=_programs[_manufactory.CurrentRecipe.Id];
      if(!TryGraduate(discipline))_pending.Add(discipline);
    }
  }
}
