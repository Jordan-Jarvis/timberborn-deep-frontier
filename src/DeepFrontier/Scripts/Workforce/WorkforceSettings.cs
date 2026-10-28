using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BlueprintSystem;
using Timberborn.GameFactionSystem;
using Timberborn.GameSceneLoading;
using Timberborn.NeedApplication;
using Timberborn.NeedSpecs;
using Timberborn.Persistence;
using Timberborn.SceneLoading;
using Timberborn.SingletonSystem;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts {
  internal sealed class WorkforceSettings : ILoadableSingleton, IPostLoadableSingleton {
    // EffectProbabilityService (1.1.2.8) keeps the game mode's injury
    // multiplier private; it loads it from this save singleton, else from the
    // new game's GameModeSpec. Read the same public sources for panel text.
    private static readonly SingletonKey EffectProbabilityKey=new("EffectProbabilityService");
    private static readonly PropertyKey<float> InjuryChanceModifierKey=new("InjuryChanceModifier");
    private readonly ISpecService _specs;
    private readonly FactionNeedService _needs;
    private readonly ISingletonLoader _singletons;
    private readonly ISceneLoader _scenes;
    private readonly EffectProbabilityService _probabilities;
    private readonly Dictionary<string, FrontierSpecialistDisciplineSpec> _disciplines =
      new Dictionary<string, FrontierSpecialistDisciplineSpec>();

    public FrontierWorkforceSettingsSpec Spec { get; private set; }
    public NeedSpec InjuryNeed { get; private set; }
    public IEnumerable<FrontierSpecialistDisciplineSpec> Disciplines => Spec.Disciplines;
    // The game mode's InjuryChance as applied to every injury roll.
    public float InjuryChanceModifier { get; private set; }

    public WorkforceSettings(ISpecService specs, FactionNeedService needs, ISingletonLoader singletons,
        ISceneLoader scenes, EffectProbabilityService probabilities) {
      _specs=specs;_needs=needs;_singletons=singletons;_scenes=scenes;_probabilities=probabilities;
    }

    public void Load() {
      Spec=_specs.GetSingleSpec<FrontierWorkforceSettingsSpec>();
      var s=Spec;
      if(string.IsNullOrEmpty(s.ProbabilityGroupId)||string.IsNullOrEmpty(s.InjuryNeedId)||string.IsNullOrEmpty(s.FatigueNeedId))
        throw new InvalidOperationException("FrontierWorkforceSettingsSpec needs a probability group, injury need and fatigue need");
      if(!(s.NativeLowChance>0f&&s.NativeLowChance<s.NativeMediumChance&&s.NativeMediumChance<s.NativeHighChance&&s.NativeHighChance<1f))
        throw new InvalidOperationException("FrontierWorkforceSettingsSpec native chances must rise strictly within (0, 1)");
      if(s.ExhaustedBelowWellbeing>=s.StrainedBelowWellbeing)
        throw new InvalidOperationException("FrontierWorkforceSettingsSpec: the exhausted wellbeing threshold must be below the strained one");
      if(s.StrainedRolls<2||s.ExhaustedRolls<=s.StrainedRolls)
        throw new InvalidOperationException("FrontierWorkforceSettingsSpec: rolls must rise from fit (1) to strained to exhausted");
      if(!(s.StrainedBelowFatiguePoints>0f))
        throw new InvalidOperationException("FrontierWorkforceSettingsSpec: StrainedBelowFatiguePoints must be positive");
      InjuryChanceModifier=_singletons.TryGetSingleton(EffectProbabilityKey,out var saved)
        ?saved.Get(InjuryChanceModifierKey)
        :_scenes.GetSceneParameters<GameSceneParameters>().NewGameConfiguration.GameMode.InjuryChance;
      if(s.Disciplines.IsDefaultOrEmpty)
        throw new InvalidOperationException("FrontierWorkforceSettingsSpec declares no specialist disciplines");
      foreach(var d in s.Disciplines) {
        if(string.IsNullOrEmpty(d.Id)||string.IsNullOrEmpty(d.DisplayNameLocKey)||string.IsNullOrEmpty(d.PluralDisplayNameLocKey))
          throw new InvalidOperationException("Every specialist discipline needs an id and singular/plural display names");
        if(!_disciplines.TryAdd(d.Id,d))
          throw new InvalidOperationException($"Specialist discipline {d.Id} is declared twice");
      }
    }

    // Faction needs are loaded by FactionNeedService.Load; read them after.
    public void PostLoad() {
      InjuryNeed=_needs.GetBeaverOrBotNeedById(Spec.InjuryNeedId);
      var fatigue=_needs.GetBeaverOrBotNeedById(Spec.FatigueNeedId);
      if(InjuryNeed.CharacterType!="Beaver"||fatigue.CharacterType!="Beaver")
        throw new InvalidOperationException("Workforce injury and fatigue needs must be beaver needs");
      if(InjuryNeed.MaximumValue!=0f||InjuryNeed.MinimumValue>=0f||InjuryNeed.DailyDelta<=0f)
        throw new InvalidOperationException($"Need {Spec.InjuryNeedId} is not a recovering never-positive injury need");
      // Exhausted = critical (points <= 0); tired = 0 < points < threshold.
      if(!fatigue.HasSpec<CriticalNeedSpec>()||fatigue.IsNeverPositive||Spec.StrainedBelowFatiguePoints>=fatigue.MaximumValue)
        throw new InvalidOperationException($"Fatigue need {Spec.FatigueNeedId} needs a critical state and a positive range above StrainedBelowFatiguePoints");
      if(_probabilities.CanApplyEffects!=(InjuryChanceModifier>0f))
        throw new InvalidOperationException("Workforce: the injury multiplier read for panels disagrees with EffectProbabilityService");
    }

    public bool IsDiscipline(string id)=>id!=null&&_disciplines.ContainsKey(id);

    public FrontierSpecialistDisciplineSpec Discipline(string id) {
      if(id==null||!_disciplines.TryGetValue(id,out var discipline))
        throw new InvalidOperationException($"Unknown specialist discipline '{id}'; declare it in FrontierWorkforceSettingsSpec");
      return discipline;
    }

    public float NativeChance(EffectProbability probability)=>probability switch {
      EffectProbability.Low=>Spec.NativeLowChance,
      EffectProbability.Medium=>Spec.NativeMediumChance,
      EffectProbability.High=>Spec.NativeHighChance,
      _=>throw new ArgumentOutOfRangeException(nameof(probability),probability,null),
    };

    public int Rolls(WorkerCondition condition)=>condition switch {
      WorkerCondition.Fit=>1,
      WorkerCondition.Strained=>Spec.StrainedRolls,
      WorkerCondition.Exhausted=>Spec.ExhaustedRolls,
      _=>throw new ArgumentOutOfRangeException(nameof(condition),condition,null),
    };
  }

  internal enum WorkerCondition { Fit, Strained, Exhausted }

  // Living specialists, registered by SpecialistTrait.
  internal sealed class SpecialistRoster {
    private readonly HashSet<SpecialistTrait> _specialists=new HashSet<SpecialistTrait>();
    public IReadOnlyCollection<SpecialistTrait> All=>_specialists;
    public void Add(SpecialistTrait trait) {_specialists.Add(trait);}
    public void Remove(SpecialistTrait trait) {_specialists.Remove(trait);}
    public int Count(string discipline)=>_specialists.Count(s=>s.Discipline==discipline);
  }
}
