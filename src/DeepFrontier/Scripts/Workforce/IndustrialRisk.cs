using System;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.Characters;
using Timberborn.Common;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.Localization;
using Timberborn.MortalSystem;
using Timberborn.NeedApplication;
using Timberborn.NeedSystem;
using Timberborn.Persistence;
using Timberborn.StatusSystem;
using Timberborn.TimeSystem;
using Timberborn.Wellbeing;
using Timberborn.WorkSystem;
using Timberborn.Workshops;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts {
  // Industrial injuries on a heavy-industry workplace.
  //
  // Same contract as native WorkshopRandomNeedApplier (1.1.2.8): a time
  // trigger fires; while Workshop.CurrentlyWorking, every assigned worker
  // standing inside the building is rolled with
  // EffectProbabilityService.CanApply (native probability group times the game
  // mode's InjuryChance). Differences, all authored per template:
  // - the trigger interval is RollIntervalHours instead of a fixed hour;
  // - a strained worker (wellbeing below StrainedBelowWellbeing, or tired:
  //   fatigue need below StrainedBelowFatiguePoints) is rolled StrainedRolls
  //   times, an exhausted one (wellbeing below ExhaustedBelowWellbeing, or the
  //   fatigue need critical, i.e. Sleep at or below 0) ExhaustedRolls times;
  // - an accident applies InjuryPoints to the native Injury need (the
  //   Hospital/Medical Bed treat it) and is fatal with FatalAccidentChance.
  // Bots have no Injury need; they pay through BotWearMultiplier (BotWear).
  internal sealed class IndustrialRisk : BaseComponent, IAwakableComponent, IInitializableEntity,
      IFinishedStateListener, IPersistentEntity, IProbabilityGroupProvider {
    private static readonly ComponentKey Key=new("DeepFrontier.IndustrialRisk");
    private static readonly PropertyKey<float> ProgressKey=new("RollProgress");
    private static readonly PropertyKey<int> InjuriesKey=new("Injuries");
    private static readonly PropertyKey<int> FatalitiesKey=new("Fatalities");

    private readonly EffectProbabilityService _probabilities;
    private readonly ITimeTriggerFactory _triggers;
    private readonly IRandomNumberGenerator _random;
    private readonly WorkforceSettings _settings;
    private readonly ILoc _loc;
    private FrontierWorkforceRiskSpec _spec;
    private Workplace _workplace;
    private Workshop _workshop;
    private LabeledEntity _label;
    private ITimeTrigger _trigger;
    private NeedApplierEffectSpec _effect;
    private StatusToggle _exhaustedStatus;

    public Enterable Enterable { get; private set; }
    public FrontierWorkforceRiskSpec Spec=>_spec;
    public float BotWearMultiplier=>_spec.BotWearMultiplier;
    public int Injuries { get; private set; }
    public int Fatalities { get; private set; }
    public int FitWorkers { get; private set; }
    public int StrainedWorkers { get; private set; }
    public int ExhaustedWorkers { get; private set; }
    public bool InjuriesEnabled=>_probabilities.CanApplyEffects;
    public string ProbabilityGroupId=>_settings.Spec.ProbabilityGroupId;
    // Chance per worker-hour for a fit worker, including the game mode's
    // InjuryChance exactly as EffectProbabilityService applies it to the roll.
    public float FitChancePerHour=>_settings.NativeChance(_spec.Probability)*_settings.InjuryChanceModifier/_spec.RollIntervalHours;

    public IndustrialRisk(EffectProbabilityService probabilities, ITimeTriggerFactory triggers,
        IRandomNumberGenerator random, WorkforceSettings settings, ILoc loc) {
      _probabilities=probabilities;_triggers=triggers;_random=random;_settings=settings;_loc=loc;
    }

    public void Awake() {
      _spec=GetComponent<FrontierWorkforceRiskSpec>();
      if(string.IsNullOrEmpty(_spec.DangerTier)||!(_spec.RollIntervalHours>0f)||!(_spec.InjuryPoints<0f)
         ||_spec.FatalAccidentChance<0f||_spec.FatalAccidentChance>=1f||_spec.BotWearMultiplier<1f)
        throw new InvalidOperationException($"{Name}: invalid FrontierWorkforceRiskSpec");
      _workplace=GetComponent<Workplace>();
      _workshop=GetComponent<Workshop>();
      Enterable=GetComponent<Enterable>();
      _label=GetComponent<LabeledEntity>();
      if(!_workplace||!_workshop||!Enterable)
        throw new InvalidOperationException($"{Name}: industrial risk needs a native Workplace, Workshop and Enterable");
      _trigger=_triggers.Create(Roll,_spec.RollIntervalHours/24f);
      DisableComponent();
    }

    public void InitializeEntity() {
      _effect=new NeedApplierEffectSpec {
        NeedId=_settings.Spec.InjuryNeedId, Points=_spec.InjuryPoints, Probability=_spec.Probability,
      };
      _exhaustedStatus=StatusToggle.CreateNormalStatusWithFloatingIcon("Exhaustion",
        _loc.T("DeepFrontier.Workforce.Status.Exhausted",_settings.Spec.ExhaustedRolls));
      GetComponent<StatusSubject>().RegisterStatus(_exhaustedStatus);
    }

    public void OnEnterFinishedState() {
      EnableComponent();
      _trigger.Resume();
    }

    public void OnExitFinishedState() {
      _trigger.Pause();
      _exhaustedStatus.Deactivate();
      FitWorkers=StrainedWorkers=ExhaustedWorkers=0;
      DisableComponent();
    }

    public void Save(IEntitySaver saver) {
      var data=saver.GetComponent(Key);
      data.Set(ProgressKey,_trigger.Progress);
      data.Set(InjuriesKey,Injuries);
      data.Set(FatalitiesKey,Fatalities);
    }

    public void Load(IEntityLoader loader) {
      if(!loader.TryGetComponent(Key,out var data))return; // building saved before workforce risks existed
      _trigger.FastForwardProgress(data.Get(ProgressKey));
      Injuries=data.Get(InjuriesKey);
      Fatalities=data.Get(FatalitiesKey);
    }

    public WorkerCondition Condition(Worker worker) {
      var needs=worker.GetComponent<NeedManager>();
      var wellbeing=worker.GetComponent<WellbeingTracker>().Wellbeing;
      var fatigue=_settings.Spec.FatigueNeedId;
      return WorkerConditions.Classify(needs.NeedIsInCriticalState(fatigue),needs.GetNeedPoints(fatigue),wellbeing,_settings.Spec);
    }

    private void Roll() {
      int fit=0,strained=0,exhausted=0;
      if(_workshop.CurrentlyWorking) {
        // Copy: a fatal accident unemploys the worker during the loop.
        var workers=new Worker[_workplace.AssignedWorkers.Count];
        for(var i=0;i<workers.Length;i++)workers[i]=_workplace.AssignedWorkers[i];
        foreach(var worker in workers) {
          if(worker.GetComponent<Enterer>().CurrentBuilding!=Enterable)continue;
          var needs=worker.GetComponent<NeedManager>();
          if(!needs.HasNeed(_effect.NeedId))continue; // bots
          var condition=Condition(worker);
          if(condition==WorkerCondition.Fit)fit++;else if(condition==WorkerCondition.Strained)strained++;else exhausted++;
          if(needs.NeedIsInCriticalState(_effect.NeedId))continue; // already injured
          var rolls=_settings.Rolls(condition);
          for(var i=0;i<rolls;i++) {
            if(!_probabilities.CanApply(this,_effect))continue;
            Injure(worker,needs);
            break;
          }
        }
      }
      FitWorkers=fit;StrainedWorkers=strained;ExhaustedWorkers=exhausted;
      if(exhausted>0)_exhaustedStatus.Activate();else _exhaustedStatus.Deactivate();
      _trigger.Reset();
      _trigger.Resume();
    }

    private void Injure(Worker worker, NeedManager needs) {
      needs.ApplyEffect(_effect.ToInstantEffect());
      Injuries++;
      if(_spec.FatalAccidentChance>0f&&_random.CheckProbability(_spec.FatalAccidentChance)) {
        Fatalities++;
        var name=worker.GetComponent<Character>().FirstName;
        worker.GetComponent<Mortal>().DieTragicallyAsSoonAsPossible(
          _loc.T("DeepFrontier.Workforce.FatalAccident",name,_label.DisplayName));
      }
    }
  }

  // Pure condition rule. Exhaustion is tested first; native Sleep is critical
  // exactly when it is unfavorable (points <= 0), so "tired" is the separate
  // positive band below StrainedBelowFatiguePoints. tools/validate_workforce_risks.mjs
  // evaluates this exact body against a table of cases.
  internal static class WorkerConditions {
    public static WorkerCondition Classify(bool fatigueCritical, float fatiguePoints, int wellbeing, FrontierWorkforceSettingsSpec s) {
      if(fatigueCritical||wellbeing<s.ExhaustedBelowWellbeing)return WorkerCondition.Exhausted;
      if(fatiguePoints<s.StrainedBelowFatiguePoints||wellbeing<s.StrainedBelowWellbeing)return WorkerCondition.Strained;
      return WorkerCondition.Fit;
    }
  }
}
