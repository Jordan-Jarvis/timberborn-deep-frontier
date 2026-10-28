using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.EntitySystem;
using Timberborn.GameFactionSystem;
using Timberborn.Goods;
using Timberborn.Localization;
using Timberborn.NotificationSystem;
using Timberborn.Persistence;
using Timberborn.QuickNotificationSystem;
using Timberborn.ScienceSystem;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TickSystem;
using Timberborn.Workshops;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts.Narrative {
  // One completed chapter or discovery, as presented to the player.
  internal sealed class NarrativeCompletion {
    public NarrativeStageSpec Stage { get; }
    public bool IsDiscovery { get; }
    // 1-based chapter number (0 for discoveries).
    public int ChapterNumber { get; }
    public NarrativeCompletion(NarrativeStageSpec stage,bool isDiscovery,int chapterNumber) {
      Stage=stage;IsDiscovery=isDiscovery;ChapterNumber=chapterNumber;
    }
  }

  // Staged story objectives advanced by native-observable events:
  // - buildings entering the native finished state (EnteredFinishedStateEvent,
  //   plus a PostLoad scan of already finished buildings);
  // - native Manufactory production (NarrativeProductionReporter decorates
  //   every Manufactory) and Human Record Cache surveys;
  // - rocket missions recorded by RocketProgramService;
  // - the colony's ending choice (journal UI).
  // Chapters complete strictly in order; discoveries in any order. Each
  // completion grants its science, posts a notification and raises Completed,
  // which the journal presenter turns into a story dialog. State is saved
  // under the singleton DeepFrontier.Narrative.
  internal sealed class NarrativeObjectiveService : ILoadableSingleton, IPostLoadableSingleton, ISaveableSingleton, ITickableSingleton {
    public const string BuildingFinished="BuildingFinished",GoodProduced="GoodProduced",RecipeCompleted="RecipeCompleted",
      MissionCompleted="MissionCompleted",EndingChosen="EndingChosen",CachesSurveyed="CachesSurveyed";
    public const string ChoiceText="Choice",EpilogueText="Epilogue";
    private static readonly string[] Kinds={BuildingFinished,GoodProduced,RecipeCompleted,MissionCompleted,EndingChosen,CachesSurveyed};

    private static readonly SingletonKey Key=new("DeepFrontier.Narrative");
    private static readonly ListKey<string> CompletedStagesKey=new("CompletedStages");
    private static readonly ListKey<string> CompletedDiscoveriesKey=new("CompletedDiscoveries");
    private static readonly ListKey<string> FinishedTemplatesKey=new("FinishedTemplates");
    private static readonly ListKey<string> CounterIdsKey=new("CounterIds");
    private static readonly ListKey<int> CounterAmountsKey=new("CounterAmounts");
    private static readonly PropertyKey<string> EndingChoiceKey=new("EndingChoice");
    private static readonly PropertyKey<int> CachesSurveyedKey=new("CachesSurveyed");

    private readonly ISpecService _specs;
    private readonly ISingletonLoader _loader;
    private readonly EventBus _events;
    private readonly FactionService _factions;
    private readonly EntityRegistry _entities;
    private readonly EntityComponentRegistry _registry;
    private readonly IGoodService _goods;
    private readonly RecipeSpecService _recipes;
    private readonly ScienceService _science;
    private readonly NotificationBus _notifications;
    private readonly QuickNotificationService _quickNotifications;
    private readonly ILoc _loc;
    private readonly RocketProgramService _program;

    private readonly List<string> _completedStages=new();
    private readonly HashSet<string> _completedDiscoveries=new();
    private readonly List<string> _completedDiscoveryOrder=new();
    // Templates ever finished, in the order the colony first finished them.
    private readonly List<string> _finishedTemplates=new();
    private readonly Dictionary<string,int> _counters=new();
    private readonly HashSet<string> _trackedTemplates=new();
    private readonly HashSet<string> _trackedGoods=new();
    private readonly HashSet<string> _trackedRecipes=new();
    // Most recent entity behind each counter or latch (not saved; notification subject only).
    private readonly Dictionary<string,(BaseComponent subject,long order)> _subjects=new();
    private long _subjectOrder;
    private int _observedStageCount;
    private bool _endingMissionSeen;

    public NarrativeSettingsSpec Spec { get; private set; }
    public bool Active { get; private set; }
    public string EndingChoice { get; private set; }="";
    public int CachesSurveyedCount { get; private set; }
    public IReadOnlyList<string> CompletedStageIds=>_completedStages;
    public IReadOnlyList<string> CompletedDiscoveryIds=>_completedDiscoveryOrder;
    public NarrativeStageSpec CurrentStage=>_completedStages.Count<Spec.Stages.Length?Spec.Stages[_completedStages.Count]:null;
    public bool AwaitingChoice=>CurrentStage?.EndingText==ChoiceText&&EndingChoice.Length==0;
    public NarrativeEndingSpec ChosenEnding=>EndingChoice.Length==0?null:Spec.Endings.Single(e=>e.Id==EndingChoice);

    public event Action<NarrativeCompletion> Completed;
    // The colony should now decide what the final launch carries.
    public event Action ChoiceRequested;

    public NarrativeObjectiveService(ISpecService specs,ISingletonLoader loader,EventBus events,FactionService factions,
      EntityRegistry entities,EntityComponentRegistry registry,IGoodService goods,RecipeSpecService recipes,ScienceService science,
      NotificationBus notifications,QuickNotificationService quickNotifications,ILoc loc,RocketProgramService program) {
      _specs=specs;_loader=loader;_events=events;_factions=factions;_entities=entities;_registry=registry;_goods=goods;
      _recipes=recipes;_science=science;_notifications=notifications;_quickNotifications=quickNotifications;_loc=loc;_program=program;
    }

    // ---- lifecycle ----
    public void Load() {
      Spec=_specs.GetSingleSpec<NarrativeSettingsSpec>();
      ValidateSpec();
      foreach(var r in Spec.Stages.Concat(Spec.Discoveries).SelectMany(s=>s.Requirements)) {
        var set=r.Kind switch {BuildingFinished=>_trackedTemplates,GoodProduced=>_trackedGoods,RecipeCompleted=>_trackedRecipes,_=>null};
        if(set!=null)foreach(var t in r.Targets)set.Add(t);
      }
      _events.Register(this);
      if(!_loader.TryGetSingleton(Key,out var data))return;
      _completedStages.AddRange(data.Get(CompletedStagesKey));
      for(int i=0;i<_completedStages.Count;i++)
        if(i>=Spec.Stages.Length||Spec.Stages[i].Id!=_completedStages[i])
          throw new InvalidOperationException($"Saved narrative chapters [{string.Join(", ",_completedStages)}] are not the start of the authored chapter order");
      foreach(var id in data.Get(CompletedDiscoveriesKey)) {
        if(!Spec.Discoveries.Any(d=>d.Id==id)||!_completedDiscoveries.Add(id))
          throw new InvalidOperationException($"Saved narrative discovery '{id}' is unknown or duplicated");
        _completedDiscoveryOrder.Add(id);
      }
      foreach(var t in data.Get(FinishedTemplatesKey)) {
        if(string.IsNullOrEmpty(t)||_finishedTemplates.Contains(t))
          throw new InvalidOperationException($"Saved narrative finished-building record '{t}' is empty or duplicated");
        _finishedTemplates.Add(t);
      }
      var ids=data.Get(CounterIdsKey);var amounts=data.Get(CounterAmountsKey);
      if(ids.Count!=amounts.Count)throw new InvalidOperationException("Saved narrative counters have mismatched id and amount lists");
      for(int i=0;i<ids.Count;i++) {
        if(string.IsNullOrEmpty(ids[i])||_counters.ContainsKey(ids[i])||amounts[i]<0)
          throw new InvalidOperationException($"Saved narrative counter '{ids[i]}' is empty, duplicated or negative");
        _counters[ids[i]]=amounts[i];
      }
      EndingChoice=data.Get(EndingChoiceKey);
      if(EndingChoice.Length>0&&!Spec.Endings.Any(e=>e.Id==EndingChoice))
        throw new InvalidOperationException($"Saved narrative ending '{EndingChoice}' is not an authored ending");
      CachesSurveyedCount=data.Get(CachesSurveyedKey);
      if(CachesSurveyedCount<0)throw new InvalidOperationException("Saved narrative cache survey count is negative");
    }

    public void PostLoad() {
      Active=_factions.Current.Id==Spec.FactionId;
      if(!Active)return;
      foreach(var good in _trackedGoods)
        if(!_goods.HasGood(good))throw new InvalidOperationException($"Narrative tracks good {good}, which this settlement does not have");
      foreach(var recipe in _trackedRecipes)_recipes.GetRecipe(recipe);
      // Buildings finished before this point (loaded saves) are latched here;
      // later ones arrive through EnteredFinishedStateEvent.
      foreach(var entity in _entities.Entities) {
        var template=entity.GetComponent<TemplateSpec>();
        if(template==null||!_trackedTemplates.Contains(template.TemplateName))continue;
        var block=entity.GetComponent<BlockObject>();
        if(block!=null&&block.IsFinished)Latch(template.TemplateName,block);
      }
      _observedStageCount=_completedStages.Count;
      _endingMissionSeen=_program.IsCompleted(Spec.EndingMissionId);
    }

    public void Save(ISingletonSaver saver) {
      if(!Active)return;
      var data=saver.GetSingleton(Key);
      data.Set(CompletedStagesKey,_completedStages);
      data.Set(CompletedDiscoveriesKey,_completedDiscoveryOrder);
      data.Set(FinishedTemplatesKey,_finishedTemplates);
      var ids=_counters.Keys.OrderBy(k=>k,StringComparer.Ordinal).ToList();
      data.Set(CounterIdsKey,ids);
      data.Set(CounterAmountsKey,ids.Select(k=>_counters[k]).ToList());
      data.Set(EndingChoiceKey,EndingChoice);
      data.Set(CachesSurveyedKey,CachesSurveyedCount);
    }

    public void Tick() {
      if(Active)Evaluate();
    }

    // ---- inputs ----
    [OnEvent]
    public void OnEnteredFinishedState(EnteredFinishedStateEvent finished) {
      var template=finished.BlockObject.GetComponent<TemplateSpec>();
      if(template!=null&&_trackedTemplates.Contains(template.TemplateName))Latch(template.TemplateName,finished.BlockObject);
    }

    public void ReportProduction(Manufactory manufactory,RecipeSpec recipe) {
      if(!Active)return;
      foreach(var product in recipe.Products)
        if(_trackedGoods.Contains(product.Id))Add("Good:"+product.Id,product.Amount,manufactory);
      if(_trackedRecipes.Contains(recipe.Id))Add("Recipe:"+recipe.Id,1,manufactory);
    }

    public void ReportBonusGoods(string goodId,int amount,BaseComponent subject) {
      if(amount<=0)throw new ArgumentOutOfRangeException(nameof(amount),"Bonus goods must be positive");
      if(Active&&_trackedGoods.Contains(goodId))Add("Good:"+goodId,amount,subject);
    }

    public void ReportCacheSurveyed(BaseComponent cache) {
      if(!Active)return;
      CachesSurveyedCount++;
      Remember("Cache",cache);
    }

    public void ChooseEnding(string endingId) {
      if(!AwaitingChoice)throw new InvalidOperationException("The narrative is not waiting for an ending choice");
      if(!Spec.Endings.Any(e=>e.Id==endingId))throw new ArgumentException($"Unknown ending {endingId}");
      EndingChoice=endingId;
      Evaluate();
    }

    // ---- progress ----
    public int Progress(NarrativeRequirementSpec r)=>r.Kind switch {
      BuildingFinished=>r.Targets.Any(_finishedTemplates.Contains)?1:0,
      GoodProduced=>r.Targets.Sum(t=>Counter("Good:"+t)),
      RecipeCompleted=>r.Targets.Sum(t=>Counter("Recipe:"+t)),
      MissionCompleted=>_program.IsCompleted(r.Targets[0])?1:0,
      EndingChosen=>EndingChoice.Length>0?1:0,
      CachesSurveyed=>CachesSurveyedCount,
      _=>throw new InvalidOperationException($"Unknown narrative requirement kind {r.Kind}"),
    };
    public bool IsMet(NarrativeRequirementSpec r)=>Progress(r)>=r.Amount;
    public bool IsMet(NarrativeStageSpec stage)=>stage.Requirements.All(IsMet);
    public bool IsDiscovered(NarrativeStageSpec discovery)=>_completedDiscoveries.Contains(discovery.Id);

    // The story line for the first target the colony finished, if the chapter has variants.
    public string VariantLocKey(NarrativeStageSpec stage) {
      foreach(var r in stage.Requirements) {
        if(r.VariantLocKeys.IsDefaultOrEmpty)continue;
        foreach(var template in _finishedTemplates) {
          int index=r.Targets.IndexOf(template);
          if(index>=0)return r.VariantLocKeys[index];
        }
      }
      return null;
    }

    // ---- evaluation ----
    private void Evaluate() {
      foreach(var discovery in Spec.Discoveries)
        if(!_completedDiscoveries.Contains(discovery.Id)&&IsMet(discovery))Complete(discovery,true,0);
      while(CurrentStage!=null&&IsMet(CurrentStage)) {
        var stage=CurrentStage;
        _completedStages.Add(stage.Id);
        Complete(stage,false,_completedStages.Count);
      }
      bool missionDone=_program.IsCompleted(Spec.EndingMissionId);
      bool stageChanged=_completedStages.Count!=_observedStageCount;
      bool missionChanged=missionDone&&!_endingMissionSeen;
      _observedStageCount=_completedStages.Count;_endingMissionSeen=missionDone;
      if(AwaitingChoice&&(stageChanged||missionChanged)) {
        if(missionChanged)_quickNotifications.SendNotification(_loc.T("Narrative.Notification.Choose"));
        ChoiceRequested?.Invoke();
      }
    }

    private void Complete(NarrativeStageSpec stage,bool discovery,int chapterNumber) {
      if(discovery) {_completedDiscoveries.Add(stage.Id);_completedDiscoveryOrder.Add(stage.Id);}
      if(stage.ScienceReward>0)_science.AddPoints(stage.ScienceReward);
      var text=_loc.T(discovery?"Narrative.Notification.Discovery":"Narrative.Notification.Chapter",_loc.T(stage.TitleLocKey));
      var subject=SubjectFor(stage);
      if(subject!=null)_notifications.Post(text,subject);
      else _quickNotifications.SendNotification(text);
      Completed?.Invoke(new NarrativeCompletion(stage,discovery,chapterNumber));
    }

    private BaseComponent SubjectFor(NarrativeStageSpec stage) {
      (BaseComponent subject,long order) best=(null,-1);
      foreach(var r in stage.Requirements) {
        IEnumerable<string> keys=r.Kind switch {
          BuildingFinished=>r.Targets.Select(t=>"Template:"+t),
          GoodProduced=>r.Targets.Select(t=>"Good:"+t),
          RecipeCompleted=>r.Targets.Select(t=>"Recipe:"+t),
          CachesSurveyed=>new[]{"Cache"},
          _=>Array.Empty<string>(),
        };
        foreach(var key in keys)
          if(_subjects.TryGetValue(key,out var entry)&&entry.order>best.order)best=entry;
        if(r.Kind==MissionCompleted&&best.subject==null) {
          var pad=_registry.GetEnabled<RocketLaunchPad>().FirstOrDefault();
          if(pad!=null)best=(pad,best.order);
        }
      }
      return best.subject;
    }

    private void Latch(string template,BaseComponent subject) {
      if(!_finishedTemplates.Contains(template))_finishedTemplates.Add(template);
      Remember("Template:"+template,subject);
    }

    private void Add(string key,int amount,BaseComponent subject) {
      _counters[key]=Counter(key)+amount;
      Remember(key,subject);
    }

    private void Remember(string key,BaseComponent subject)=>_subjects[key]=(subject,++_subjectOrder);
    private int Counter(string key)=>_counters.TryGetValue(key,out var value)?value:0;

    // ---- spec validation (explicit failure, nothing defaulted) ----
    private void ValidateSpec() {
      void Fail(string reason)=>throw new InvalidOperationException("Invalid Deep Frontier narrative spec: "+reason);
      if(string.IsNullOrEmpty(Spec.FactionId)||string.IsNullOrEmpty(Spec.EndingMissionId))Fail("faction and ending mission are required");
      if(Spec.Stages.IsDefaultOrEmpty)Fail("no chapters");
      if(Spec.Discoveries.IsDefault)Fail("discoveries list missing");
      if(Spec.Endings.IsDefaultOrEmpty)Fail("no endings");
      var endingIds=Spec.Endings.Select(e=>e.Id).ToList();
      if(endingIds.Any(string.IsNullOrEmpty)||endingIds.Distinct().Count()!=endingIds.Count)Fail("ending ids must be unique");
      foreach(var e in Spec.Endings)
        if(string.IsNullOrEmpty(e.TitleLocKey)||string.IsNullOrEmpty(e.DescriptionLocKey)||e.EpilogueLocKeys.IsDefaultOrEmpty
          ||e.EpilogueLocKeys.Any(string.IsNullOrEmpty))Fail($"ending {e.Id}: localization keys");
      var ids=new HashSet<string>();
      foreach(var (entry,discovery) in Spec.Stages.Select(s=>(s,false)).Concat(Spec.Discoveries.Select(d=>(d,true)))) {
        if(string.IsNullOrEmpty(entry.Id)||!ids.Add(entry.Id))Fail($"missing or duplicate id '{entry.Id}'");
        if(string.IsNullOrEmpty(entry.TitleLocKey)||string.IsNullOrEmpty(entry.ObjectiveLocKey)||entry.HintLocKey==null
          ||entry.StoryLocKeys.IsDefaultOrEmpty||entry.StoryLocKeys.Any(string.IsNullOrEmpty))Fail($"{entry.Id}: localization keys");
        if(!discovery&&entry.HintLocKey.Length==0)Fail($"{entry.Id}: chapters carry a hint");
        if(entry.ScienceReward<0)Fail($"{entry.Id}: negative science reward");
        if(entry.EndingText!=""&&entry.EndingText!=ChoiceText&&entry.EndingText!=EpilogueText)Fail($"{entry.Id}: ending text '{entry.EndingText}'");
        if(discovery&&entry.EndingText!="")Fail($"{entry.Id}: discoveries carry no ending text");
        if(entry.Requirements.IsDefaultOrEmpty)Fail($"{entry.Id}: no requirements");
        foreach(var r in entry.Requirements) {
          if(!Kinds.Contains(r.Kind))Fail($"{entry.Id}: unknown requirement kind '{r.Kind}'");
          if(r.Amount<1||string.IsNullOrEmpty(r.LabelLocKey)||r.Targets.IsDefault||r.VariantLocKeys.IsDefault)Fail($"{entry.Id}: requirement amount, label or lists");
          if((r.Kind==CachesSurveyed)!=r.Targets.IsEmpty||r.Targets.Any(string.IsNullOrEmpty))Fail($"{entry.Id}: {r.Kind} targets");
          if((r.Kind==BuildingFinished||r.Kind==MissionCompleted||r.Kind==EndingChosen)&&r.Amount!=1)Fail($"{entry.Id}: {r.Kind} amount must be 1");
          if(r.Kind==MissionCompleted&&r.Targets.Length!=1)Fail($"{entry.Id}: one mission per requirement");
          if(r.Kind==EndingChosen&&(discovery||entry.EndingText!=ChoiceText||!r.Targets.SequenceEqual(endingIds)))
            Fail($"{entry.Id}: only the Choice chapter asks for the ending, listing every ending");
          if(!r.VariantLocKeys.IsEmpty&&(r.Kind!=BuildingFinished||r.VariantLocKeys.Length!=r.Targets.Length||r.VariantLocKeys.Any(string.IsNullOrEmpty)))
            Fail($"{entry.Id}: variants are one key per BuildingFinished target");
        }
      }
      var choice=Spec.Stages.Where(s=>s.EndingText==ChoiceText).ToList();
      if(choice.Count!=1||!choice[0].Requirements.Any(r=>r.Kind==EndingChosen))Fail("exactly one Choice chapter with an EndingChosen requirement");
      var last=Spec.Stages[Spec.Stages.Length-1];
      if(Spec.Stages.Count(s=>s.EndingText==EpilogueText)!=1||last.EndingText!=EpilogueText)Fail("the last chapter, and only it, carries the epilogue");
      if(!last.Requirements.Any(r=>r.Kind==MissionCompleted&&r.Targets[0]==Spec.EndingMissionId))Fail($"the last chapter requires mission {Spec.EndingMissionId}");
      if(Spec.Stages.IndexOf(choice[0])>=Spec.Stages.Length-1)Fail("the choice comes before the final chapter");
    }
  }
}
