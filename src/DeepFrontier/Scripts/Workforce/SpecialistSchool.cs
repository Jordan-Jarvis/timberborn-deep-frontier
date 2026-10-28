using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Timberborn.Attractions;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.Localization;
using Timberborn.NeedBehaviorSystem;
using Timberborn.NeedSpecs;
using Timberborn.Persistence;
using Timberborn.StatusSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts {
  // Technical School: free-time study, no staff (staff would work the shift
  // during which the students are at work). The school is a native
  // goods-consuming attraction (vanilla Detailer pattern): it uses up its
  // supplies while anyone studies inside, and native Attraction.IsUsable turns
  // students away without supplies or power. It teaches one discipline, chosen
  // in its panel: its native AttractionSpec lists every study need, and only
  // the taught discipline's need stays in Attraction.Effects, so the native
  // district need behaviours send only beavers whose study need for it is low.
  // A beaver holding the discipline keeps that need full (SpecialistTrait), so
  // it never comes. Each hour inside adds one study hour; StudyHours graduates.
  internal sealed class SpecialistSchool : TickableComponent, IAwakableComponent, IInitializableEntity,
      IFinishedStateListener, IPersistentEntity, IBuildingEfficiencyProvider {
    private static readonly ComponentKey Key=new("DeepFrontier.SpecialistSchool");
    private static readonly PropertyKey<string> DisciplineKey=new("Discipline");
    // Native members without a public writer (Timberborn 1.1.2.8); missing ones fail at load.
    private static readonly PropertyInfo EffectsProperty=Require(typeof(Attraction).GetProperty(nameof(Attraction.Effects)),"Attraction.Effects");
    private static readonly PropertyInfo ToMaxProperty=Require(typeof(Attraction).GetProperty(nameof(Attraction.SatisfiesAnyNeedToMaxValue)),"Attraction.SatisfiesAnyNeedToMaxValue");
    private static readonly FieldInfo DistrictServiceField=Require(typeof(AttractionNeedBehavior).GetField("_districtNeedBehaviorService",
      BindingFlags.Instance|BindingFlags.NonPublic),"AttractionNeedBehavior._districtNeedBehaviorService");

    private readonly WorkforceSettings _settings;
    private readonly IDayNightCycle _cycle;
    private readonly ILoc _loc;
    private readonly Dictionary<string, float> _programs=new Dictionary<string, float>();
    private IReadOnlyList<ContinuousEffectSpec> _allEffects;
    private Attraction _attraction;
    private AttractionNeedBehavior _behavior;
    private Enterable _enterable;
    private StatusToggle _noProgramStatus;

    // null: no discipline chosen; nobody studies.
    public string Discipline { get; private set; }
    public IReadOnlyCollection<string> Disciplines=>_programs.Keys;
    public float StudyHours=>Discipline==null?0f:_programs[Discipline];
    public bool CanUse=>Discipline!=null;
    public float Efficiency=>1f;
    public IEnumerable<SpecialistTrait> Students=>_enterable.EnterersInside
      .Select(e=>e.GetComponent<SpecialistTrait>()).Where(t=>t&&!t.Has(Discipline));

    public SpecialistSchool(WorkforceSettings settings, IDayNightCycle cycle, ILoc loc) {
      _settings=settings;_cycle=cycle;_loc=loc;
    }

    private static T Require<T>(T member, string name) where T : MemberInfo=>
      member??throw new InvalidOperationException($"Technical School: native {name} was not found");

    public void Awake() {
      _attraction=GetComponent<Attraction>();
      _behavior=GetComponent<AttractionNeedBehavior>();
      _enterable=GetComponent<Enterable>();
      if(!_attraction||!_behavior||!_enterable)
        throw new InvalidOperationException($"{Name}: a specialist school must be a native enterable attraction");
      foreach(var program in GetComponent<FrontierSpecialistSchoolSpec>().Programs)
        if(!_programs.TryAdd(program.Discipline,program.StudyHours))
          throw new InvalidOperationException($"{Name}: discipline {program.Discipline} is taught twice");
      DisableComponent();
    }

    public void Save(IEntitySaver saver) {
      if(Discipline!=null)saver.GetComponent(Key).Set(DisciplineKey,Discipline);
    }

    public void Load(IEntityLoader loader) {
      // Schools saved before free-time study (staffed courses) have no discipline yet.
      if(!loader.TryGetComponent(Key,out var data)||!data.Has(DisciplineKey))return;
      Discipline=data.Get(DisciplineKey);
      if(!_programs.ContainsKey(Discipline))throw new InvalidOperationException($"{Name}: saved discipline {Discipline} is not taught here");
    }

    public void InitializeEntity() {
      foreach(var discipline in _programs.Keys) {
        _settings.Discipline(discipline);
        var need=SpecialistTrait.StudyNeedId(discipline);
        if(_attraction.Effects.Count(e=>e.NeedId==need)!=1)
          throw new InvalidOperationException($"{Name}: the AttractionSpec must list the study need {need} once");
      }
      _allEffects=_attraction.Effects.ToList();
      ApplyEffects();
      _noProgramStatus=StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon("NoUnemployed",
        _loc.T("DeepFrontier.Workforce.Status.NoProgram"),_loc.T("DeepFrontier.Workforce.Status.NoProgram.Short"));
      GetComponent<StatusSubject>().RegisterStatus(_noProgramStatus);
    }

    public void OnEnterFinishedState() {
      EnableComponent();
      UpdateStatus();
    }

    public void OnExitFinishedState() {
      _noProgramStatus.Deactivate();
      DisableComponent();
    }

    public void Teach(string discipline) {
      if(discipline!=null&&!_programs.ContainsKey(discipline))
        throw new InvalidOperationException($"{Name}: {discipline} is not taught here");
      if(discipline==Discipline)return;
      Discipline=discipline;
      ApplyEffects();
      UpdateStatus();
    }

    public override void Tick() {
      if(Discipline==null||!_attraction.IsUsable)return;
      var hours=_cycle.FixedDeltaTimeInHours;
      foreach(var student in Students.ToList())student.AddStudyHours(Discipline,hours,StudyHours);
    }

    // Keeps only the taught discipline's study need, re-registering the native
    // need behaviour with its district under the new effects.
    private void ApplyEffects() {
      var need=Discipline==null?null:SpecialistTrait.StudyNeedId(Discipline);
      var effects=_allEffects.Where(e=>e.NeedId==need).ToList();
      var district=(DistrictNeedBehaviorService)DistrictServiceField.GetValue(_behavior);
      if(district&&_attraction.Effects.Count>0)district.RemoveNeedBehavior(_attraction.Effects,_behavior);
      EffectsProperty.SetValue(_attraction,effects);
      ToMaxProperty.SetValue(_attraction,effects.Any(e=>e.SatisfyToMaxValue));
      if(district&&effects.Count>0)district.AddNeedBehavior(_attraction.Effects,_behavior);
    }

    private void UpdateStatus() {
      if(_noProgramStatus==null)return;
      if(Discipline==null)_noProgramStatus.Activate();else _noProgramStatus.Deactivate();
    }
  }
}
