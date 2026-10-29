using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using System.Reflection;
using Timberborn.Attractions;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.InventorySystem;
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
  // Each discipline has its own supplies. The template's native
  // GoodConsumingBuildingSpec lists every discipline's goods; the school gives
  // its GoodConsumingBuilding a copy listing only the taught discipline's (the
  // native consumer reads its spec field and supply list, with no setter), and
  // as the inventory's IGoodDisallower (SchoolSupplyInventory) it accepts only
  // those goods. Another discipline's stock stays inside for when it is taught
  // again.
  internal sealed class SpecialistSchool : TickableComponent, IAwakableComponent, IInitializableEntity,
      IFinishedStateListener, IPersistentEntity, IBuildingEfficiencyProvider, IGoodDisallower {
    private static readonly ComponentKey Key=new("DeepFrontier.SpecialistSchool");
    private static readonly PropertyKey<string> DisciplineKey=new("Discipline");
    // Native members without a public writer (Timberborn 1.1.2.8); missing ones fail at load.
    private static readonly PropertyInfo EffectsProperty=Require(typeof(Attraction).GetProperty(nameof(Attraction.Effects)),"Attraction.Effects");
    private static readonly PropertyInfo ToMaxProperty=Require(typeof(Attraction).GetProperty(nameof(Attraction.SatisfiesAnyNeedToMaxValue)),"Attraction.SatisfiesAnyNeedToMaxValue");
    private static readonly FieldInfo DistrictServiceField=Require(typeof(AttractionNeedBehavior).GetField("_districtNeedBehaviorService",
      BindingFlags.Instance|BindingFlags.NonPublic),"AttractionNeedBehavior._districtNeedBehaviorService");
    private static readonly FieldInfo ConsumerSpecField=RequireField(typeof(GoodConsumingBuilding),"_goodConsumingBuildingSpec",typeof(GoodConsumingBuildingSpec));
    private static readonly FieldInfo SuppliesLeftField=RequireField(typeof(GoodConsumingBuilding),"_suppliesLeft",typeof(List<float>));

    private readonly WorkforceSettings _settings;
    private readonly IDayNightCycle _cycle;
    private readonly ILoc _loc;
    private readonly Dictionary<string, float> _programs=new Dictionary<string, float>();
    private readonly Dictionary<string, ImmutableArray<ConsumedGoodSpec>> _supplies=new Dictionary<string, ImmutableArray<ConsumedGoodSpec>>();
    private GoodConsumingBuildingSpec _allSupplies;
    private GoodConsumingBuilding _consumer;
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
    public event EventHandler<DisallowedGoodsChangedEventArgs> DisallowedGoodsChanged;
    public IEnumerable<SpecialistTrait> Students=>_enterable.EnterersInside
      .Select(e=>e.GetComponent<SpecialistTrait>()).Where(t=>t&&!t.Has(Discipline));

    public SpecialistSchool(WorkforceSettings settings, IDayNightCycle cycle, ILoc loc) {
      _settings=settings;_cycle=cycle;_loc=loc;
    }

    private static T Require<T>(T member, string name) where T : MemberInfo=>
      member??throw new InvalidOperationException($"Technical School: native {name} was not found");

    private static FieldInfo RequireField(Type type, string name, Type fieldType) {
      var field=type.GetField(name,BindingFlags.Instance|BindingFlags.NonPublic);
      if(field==null||field.FieldType!=fieldType)
        throw new InvalidOperationException($"Technical School: native {type.Name}.{name} : {fieldType.Name} was not found");
      return field;
    }

    public void Awake() {
      _attraction=GetComponent<Attraction>();
      _behavior=GetComponent<AttractionNeedBehavior>();
      _enterable=GetComponent<Enterable>();
      _consumer=GetComponent<GoodConsumingBuilding>();
      _allSupplies=GetComponent<GoodConsumingBuildingSpec>();
      if(!_attraction||!_behavior||!_enterable||!_consumer||_allSupplies==null)
        throw new InvalidOperationException($"{Name}: a specialist school must be a native enterable goods-consuming attraction");
      foreach(var program in GetComponent<FrontierSpecialistSchoolSpec>().Programs) {
        if(!_programs.TryAdd(program.Discipline,program.StudyHours))
          throw new InvalidOperationException($"{Name}: discipline {program.Discipline} is taught twice");
        if(program.Supplies.IsDefaultOrEmpty)throw new InvalidOperationException($"{Name}: {program.Discipline} has no supplies");
        foreach(var supply in program.Supplies)
          if(!_allSupplies.ConsumedGoods.Any(g=>g.GoodId==supply.GoodId))
            throw new InvalidOperationException($"{Name}: {program.Discipline} supply {supply.GoodId} is not in the GoodConsumingBuildingSpec");
        _supplies.Add(program.Discipline,program.Supplies.Select(s=>new ConsumedGoodSpec{GoodId=s.GoodId,GoodPerHour=s.GoodPerHour}).ToImmutableArray());
      }
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
      // After Load: the native consumer loaded the taught discipline's saved supply list.
      ApplySupplies(keepSuppliesLeft:true);
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
      ApplySupplies(keepSuppliesLeft:false);
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

    // IGoodDisallower: only the taught discipline's supplies are delivered.
    public int AllowedAmount(string goodId)=>
      Discipline!=null&&_supplies[Discipline].Any(g=>g.GoodId==goodId)?int.MaxValue:0;

    // The native consumer uses up, and requires, only the taught discipline's
    // goods; its supply list (the part of a unit already taken from stock) is
    // kept in step. Without a discipline nobody studies and nothing is used.
    private void ApplySupplies(bool keepSuppliesLeft) {
      var goods=Discipline==null?ImmutableArray<ConsumedGoodSpec>.Empty:_supplies[Discipline];
      ConsumerSpecField.SetValue(_consumer,_allSupplies with {ConsumedGoods=goods});
      var left=(List<float>)SuppliesLeftField.GetValue(_consumer);
      if(!keepSuppliesLeft)left.Clear();
      if(left.Count>goods.Length)left.RemoveRange(goods.Length,left.Count-goods.Length);
      while(left.Count<goods.Length)left.Add(0f);
      foreach(var good in _allSupplies.ConsumedGoods)
        DisallowedGoodsChanged?.Invoke(this,new DisallowedGoodsChangedEventArgs(good.GoodId));
    }

    private void UpdateStatus() {
      if(_noProgramStatus==null)return;
      if(Discipline==null)_noProgramStatus.Activate();else _noProgramStatus.Deactivate();
    }
  }
}
