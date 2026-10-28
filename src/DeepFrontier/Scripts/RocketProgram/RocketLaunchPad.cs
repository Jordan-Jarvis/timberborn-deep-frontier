using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.CoreUI;
using Timberborn.EntitySystem;
using Timberborn.Explosions;
using Timberborn.GameSound;
using Timberborn.GameWonderCompletion;
using Timberborn.Goods;
using Timberborn.Localization;
using Timberborn.MechanicalSystem;
using Timberborn.NeedSpecs;
using Timberborn.NotificationSystem;
using Timberborn.Persistence;
using Timberborn.RangedEffectSystem;
using Timberborn.ScienceSystem;
using Timberborn.StatusSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.Workshops;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts {
  internal enum RocketPadStage {
    UnderConstruction, NoMission, Telemetry, InFlight, Refurbishing, Blocked,
    MissionCompleted, MissionInFlightElsewhere, MissionLocked, Staging, Preparing, HoldingForPower,
  }

  // Launch sequencing on the native Launch Pad workshop.
  // - Mission = native recipe; haulers stage the rocket and fuel, the recipe
  //   selector chooses the mission, workers + 25,000 hp run the preparation.
  // - Ingredients are consumed natively when preparation starts (rocket
  //   stacked). Changing the recipe before liftoff destacks the rocket and
  //   returns its parts and fuel to the pad inventory.
  // - This IManufactoryLimiter stops all work while the pad is blocked
  //   (pause/automation), refurbishing or flying, and stops a mission recipe
  //   that is completed or locked. It holds preparation just below liftoff
  //   until the pad's grid delivers full power.
  // - Liftoff (recipe completion) rolls the outcome once and persists it;
  //   success records the mission, adds science, a permanent ranged wellbeing
  //   effect and story text; failure loses the rocket and fuel and puts the
  //   pad into refurbishment.
  internal sealed class RocketLaunchPad : TickableComponent, IAwakableComponent, IInitializableEntity,
      IPostLoadableEntity, IFinishedStateListener, IPersistentEntity, IManufactoryLimiter, IRegisteredComponent {
    private static readonly ComponentKey Key=new("DeepFrontier.RocketLaunchPad");
    private static readonly PropertyKey<string> FlightMissionKey=new("FlightMission");
    private static readonly PropertyKey<float> FlightStartKey=new("FlightStartDay");
    private static readonly PropertyKey<bool> FlightFailsKey=new("FlightFails");
    private static readonly PropertyKey<float> FlightChanceKey=new("FlightFailureChance");
    private static readonly PropertyKey<float> RefurbishEndKey=new("RefurbishEndDay");

    private readonly RocketProgramService _program;
    private readonly RecipeSpecService _recipes;
    private readonly IDayNightCycle _cycle;
    private readonly ScienceService _science;
    private readonly NotificationBus _notifications;
    private readonly DialogBoxShower _dialogs;
    private readonly ILoc _loc;
    private readonly WonderCompletionCountdownStarter _wonder;
    private readonly ExplosionSoundPlayer _explosionSound;
    private readonly GameUISoundController _uiSound;

    private Manufactory _manufactory;
    private BlockableObject _blockable;
    private MechanicalNode _power;
    // Legacy wellbeing is applied through the native ranged-effect applier
    // (the same coordinate registry and RangedEffectSubject delivery that
    // RangedEffectBuilding uses), driven here so its only condition is a
    // powered grid. RangedEffectBuilding would also switch it off while the
    // pad is paused or automation-blocked and scale it by power efficiency.
    private RangedEffectApplier _legacyApplier;
    private BlockObjectRange _legacyArea;
    private RecipeGoodDisallower _goodDisallower;
    private bool _legacyActive;
    private readonly Dictionary<string,RocketMissionSpec> _byRecipe=new();
    private readonly Dictionary<string,RocketMissionSpec> _byId=new();
    private readonly Dictionary<string,StatusToggle> _lockedStatus=new();
    private readonly Dictionary<string,StatusToggle> _completedStatus=new();
    private StatusToggle _refurbishStatus;
    private readonly List<ContinuousEffectSpec> _appliedLegacy=new();
    private string _stackedRecipeId;
    private string _flightMissionId="";
    private float _flightStartDay;
    private bool _flightFails;
    private float _flightFailureChance;
    private float _refurbishEndDay;

    public RocketLaunchPadSpec Spec { get; private set; }
    public Manufactory Manufactory=>_manufactory;
    public IEnumerable<RocketMissionSpec> Missions=>Spec.Missions;
    public RocketMissionSpec CurrentMission=>
      _manufactory.HasCurrentRecipe&&_byRecipe.TryGetValue(_manufactory.CurrentRecipe.Id,out var m)?m:null;
    public bool RocketStacked=>_stackedRecipeId!=null;
    public bool InFlight=>_flightMissionId.Length>0;
    public RocketMissionSpec FlightMission=>InFlight?_byId[_flightMissionId]:null;
    public bool FlightFails=>_flightFails;
    public float FlightFailureChance=>_flightFailureChance;
    public float FlightProgress=>InFlight?(_cycle.PartialDayNumber-_flightStartDay)*24f/Spec.FlightHours:0f;
    public bool Refurbishing=>_refurbishEndDay>0f;
    public float RefurbishHoursLeft=>Refurbishing?Mathf.Max(0f,(_refurbishEndDay-_cycle.PartialDayNumber)*24f):0f;
    public bool FullPower=>_power.PowerEfficiency>=1f;

    public RocketLaunchPad(RocketProgramService program,RecipeSpecService recipes,IDayNightCycle cycle,
      ScienceService science,NotificationBus notifications,DialogBoxShower dialogs,ILoc loc,
      WonderCompletionCountdownStarter wonder,ExplosionSoundPlayer explosionSound,GameUISoundController uiSound) {
      _program=program;_recipes=recipes;_cycle=cycle;_science=science;_notifications=notifications;
      _dialogs=dialogs;_loc=loc;_wonder=wonder;_explosionSound=explosionSound;_uiSound=uiSound;
    }

    public void Awake() {
      Spec=GetComponent<RocketLaunchPadSpec>();
      _manufactory=GetComponent<Manufactory>();_blockable=GetComponent<BlockableObject>();
      _power=GetComponent<MechanicalNode>();_legacyApplier=GetComponent<RangedEffectApplier>();
      _legacyArea=GetComponent<BlockObjectRange>();_goodDisallower=GetComponent<RecipeGoodDisallower>();
      if(!_manufactory||!_blockable||!_power||!_legacyApplier||!_legacyArea||!_goodDisallower)
        throw new InvalidOperationException("Launch Pad requires a native Manufactory, MechanicalNode, RangedEffectApplier and BlockObjectRange");
      if(GetComponent<RangedEffectBuilding>())
        throw new InvalidOperationException("Launch Pad legacy wellbeing must not use RangedEffectBuilding (it gates on pause/automation)");
      Validate();
      foreach(var mission in Spec.Missions) {
        if(mission.PrerequisiteMissionId.Length>0)
          _lockedStatus[mission.Id]=StatusToggle.CreateNormalStatusWithFloatingIcon("UnspecifiedRecipe",
            _loc.T("RocketProgram.Status.Locked",_loc.T(_byId[mission.PrerequisiteMissionId].DisplayNameLocKey)));
        _completedStatus[mission.Id]=StatusToggle.CreateNormalStatusWithFloatingIcon("UnspecifiedRecipe",
          _loc.T("RocketProgram.Status.Completed",_loc.T(mission.DisplayNameLocKey)));
      }
      _refurbishStatus=StatusToggle.CreateNormalStatusWithFloatingIcon("NothingToDo",_loc.T("RocketProgram.Status.Refurbishing"));
      _manufactory.ProductionProgressed+=OnProductionProgressed;
      _manufactory.ProductionFinished+=OnProductionFinished;
      _manufactory.RecipeChanged+=OnRecipeChanged;
      DisableComponent();
    }

    private void Validate() {
      void Fail(string reason)=>throw new InvalidOperationException("Invalid Launch Pad rocket program: "+reason);
      if(Spec.Missions.IsDefaultOrEmpty)Fail("no missions");
      if(Spec.MinimumFailureChance<0f||Spec.MinimumFailureChance>=1f)Fail("minimum failure chance outside [0,1)");
      if(Spec.MissionControlFailureReduction<0f||Spec.HeritageFailureReductionPerLaunch<0f||Spec.MaxHeritageFailureReduction<0f)
        Fail("negative failure reduction");
      if(!(Spec.LaunchHoldProgress>0f&&Spec.LaunchHoldProgress<1f))Fail("launch hold must lie inside (0,1)");
      if(!(Spec.FlightHours>0f)||!(Spec.RefurbishmentHours>0f))Fail("flight and refurbishment durations must be positive");
      if(Spec.LegacyRadius<=0)Fail("legacy radius must be positive");
      if(!(Spec.FailurePointFraction>0f&&Spec.FailurePointFraction<1f))Fail("failure point must lie inside (0,1)");
      var recipeIds=GetComponent<ManufactorySpec>().ProductionRecipeIds;
      for(int i=0;i<Spec.Missions.Length;i++) {
        var m=Spec.Missions[i];
        if(string.IsNullOrEmpty(m.Id)||_byId.ContainsKey(m.Id))Fail($"missing or duplicate mission id '{m.Id}'");
        if(string.IsNullOrEmpty(m.RecipeId)||_byRecipe.ContainsKey(m.RecipeId)||!recipeIds.Contains(m.RecipeId))
          Fail($"{m.Id}: recipe '{m.RecipeId}' is missing, duplicated or not a Launch Pad recipe");
        var recipe=_recipes.GetRecipe(m.RecipeId);
        if(recipe.Ingredients.Any(g=>recipe.GetCapacity(new GoodAmount(g.Id,g.Amount))!=g.Amount)||recipe.ProducesProducts||recipe.ProducesSciencePoints||recipe.ConsumesFuel||!recipe.ConsumesIngredients)
          Fail($"{m.Id}: a mission recipe holds exactly one rocket, consumes ingredients and has no products, science or fuel");
        if(m.PrerequisiteMissionId==null||(i==0)!=(m.PrerequisiteMissionId.Length==0)
          ||(i>0&&m.PrerequisiteMissionId!=Spec.Missions[i-1].Id))
          Fail($"{m.Id}: missions form one ordered chain; each requires the previous one");
        if(!(m.BaseFailureChance>=Spec.MinimumFailureChance&&m.BaseFailureChance<1f))Fail($"{m.Id}: base failure chance");
        if(m.ScienceReward<0||m.LegacyWellbeing<=0||m.LegacyEffect==null||string.IsNullOrEmpty(m.LegacyEffect.NeedId)
          ||!(m.LegacyEffect.PointsPerHour>0f))Fail($"{m.Id}: rewards");
        if(m.CompletesStory!=(i==Spec.Missions.Length-1))Fail("only the final mission completes the story");
        foreach(var key in new[]{m.DisplayNameLocKey,m.DescriptionLocKey,m.SuccessLocKey,m.FailureLocKey})
          if(string.IsNullOrEmpty(key))Fail($"{m.Id}: missing localization key");
        _byId[m.Id]=m;_byRecipe[m.RecipeId]=m;
      }
    }

    public void InitializeEntity() {
      var subject=GetComponent<StatusSubject>();
      foreach(var status in _lockedStatus.Values.Concat(_completedStatus.Values))subject.RegisterStatus(status);
      subject.RegisterStatus(_refurbishStatus);
    }

    public void PostLoadEntity() {
      // Manufactory persists whether ingredients were consumed; its processed
      // goods are exactly the stacked rocket.
      var mission=CurrentMission;
      _stackedRecipeId=mission!=null&&_manufactory.ProcessedGoods.Count>0?mission.RecipeId:null;
    }

    public void OnEnterFinishedState() {
      EnableComponent();
      _appliedLegacy.Clear();_legacyActive=LegacyPowered;
      SyncLegacyEffects();EnableLegacyApplier();
      UpdateStatuses();
    }
    public void OnExitFinishedState() {
      if(_legacyApplier.Enabled)_legacyApplier.Disable();
      _appliedLegacy.Clear();_legacyActive=false;
      foreach(var status in _lockedStatus.Values.Concat(_completedStatus.Values))status.Deactivate();
      _refurbishStatus.Deactivate();
      DisableComponent();
    }

    public void Save(IEntitySaver saver) {
      var data=saver.GetComponent(Key);
      data.Set(FlightMissionKey,_flightMissionId);data.Set(FlightStartKey,_flightStartDay);
      data.Set(FlightFailsKey,_flightFails);data.Set(FlightChanceKey,_flightFailureChance);
      data.Set(RefurbishEndKey,_refurbishEndDay);
    }
    public void Load(IEntityLoader loader) {
      // A pad saved before the rocket program existed has no launch state.
      if(!loader.TryGetComponent(Key,out var data))return;
      _flightMissionId=data.Get(FlightMissionKey);_flightStartDay=data.Get(FlightStartKey);
      _flightFails=data.Get(FlightFailsKey);_flightFailureChance=data.Get(FlightChanceKey);
      _refurbishEndDay=data.Get(RefurbishEndKey);
      if(_flightMissionId.Length>0&&!_byId.ContainsKey(_flightMissionId))
        throw new InvalidOperationException($"Saved flight references unknown mission {_flightMissionId}");
    }

    // ---- odds ----
    public float MissionControlReduction=>_program.OperatingMissionControls>0?Spec.MissionControlFailureReduction:0f;
    public float HeritageReduction=>Mathf.Min(Spec.MaxHeritageFailureReduction,_program.LaunchAttempts*Spec.HeritageFailureReductionPerLaunch);
    public float FailureChance(RocketMissionSpec mission)=>
      Mathf.Max(Spec.MinimumFailureChance,mission.BaseFailureChance-MissionControlReduction-HeritageReduction);
    // One mission flies from one pad at a time.
    public bool FlownElsewhere(RocketMissionSpec mission)=>_program.IsInFlight(mission.Id,this);
    public bool IsLocked(RocketMissionSpec mission)=>
      mission.PrerequisiteMissionId.Length>0&&!_program.IsCompleted(mission.PrerequisiteMissionId);

    public RocketPadStage Stage {
      get {
        if(!Enabled)return RocketPadStage.UnderConstruction;
        if(InFlight)return RocketPadStage.InFlight;
        if(Refurbishing)return RocketPadStage.Refurbishing;
        if(!_blockable.IsUnblocked)return RocketPadStage.Blocked;
        if(!_manufactory.HasCurrentRecipe)return RocketPadStage.NoMission;
        var mission=CurrentMission;
        if(mission==null)return RocketPadStage.Telemetry;
        if(_program.IsCompleted(mission.Id))return RocketPadStage.MissionCompleted;
        if(FlownElsewhere(mission))return RocketPadStage.MissionInFlightElsewhere;
        if(IsLocked(mission))return RocketPadStage.MissionLocked;
        if(!RocketStacked)return RocketPadStage.Staging;
        return !FullPower&&_manufactory.ProductionProgress>=Spec.LaunchHoldProgress
          ?RocketPadStage.HoldingForPower:RocketPadStage.Preparing;
      }
    }

    // ---- IManufactoryLimiter ----
    public float ProductionEfficiency() {
      if(!Enabled||InFlight||Refurbishing||!_blockable.IsUnblocked)return 0f;
      var mission=CurrentMission;
      if(mission!=null&&(_program.IsCompleted(mission.Id)||IsLocked(mission)||FlownElsewhere(mission)))return 0f;
      return 1f;
    }
    public float MaxProductionProgressChange(float expectedProductionProgressChange) {
      if(CurrentMission==null||FullPower)return 1f;
      return Mathf.Max(0f,Spec.LaunchHoldProgress-_manufactory.ProductionProgress);
    }

    // ---- native production events ----
    private void OnProductionProgressed(object sender,ProductionProgressedEventArgs e) {
      var mission=CurrentMission;
      if(mission!=null&&_manufactory.ProductionProgress>0f&&_manufactory.ProcessedGoods.Count>0)
        _stackedRecipeId=mission.RecipeId;
    }

    private void OnRecipeChanged(object sender,EventArgs e) {
      if(_stackedRecipeId==null)return;
      // SetRecipe has already reset progress and forgotten the consumed
      // ingredients; return the stacked rocket so haulers can reuse it.
      // The returned rocket can exceed the new recipe's limits (and the
      // inventory total when a second set was already delivered), so it goes
      // in ignoring capacity and the native disallower is re-applied: that
      // raises DisallowedGoodsChanged, Inventory re-checks unwanted stock and
      // native haulers carry the overflow out. SetRecipe ran the same update
      // before RecipeChanged, i.e. before these goods existed.
      var scrubbed=_byRecipe[_stackedRecipeId];
      foreach(var ingredient in _recipes.GetRecipe(scrubbed.RecipeId).Ingredients)
        _manufactory.Inventory.GiveExistingIgnoringCapacity(new GoodAmount(ingredient.Id,ingredient.Amount));
      _goodDisallower.UpdateAllowedAmounts(_manufactory.CurrentRecipe);
      _stackedRecipeId=null;
      _notifications.Post(_loc.T("RocketProgram.Notification.Scrubbed",_loc.T(scrubbed.DisplayNameLocKey)),this);
    }

    private void OnProductionFinished(object sender,EventArgs e) {
      var mission=CurrentMission;
      if(mission==null)return;
      if(_stackedRecipeId!=mission.RecipeId||InFlight)
        throw new InvalidOperationException($"Launch of {mission.Id} finished without a stacked rocket");
      _stackedRecipeId=null;
      var chance=FailureChance(mission);
      _flightMissionId=mission.Id;_flightStartDay=_cycle.PartialDayNumber;
      _flightFailureChance=chance;_flightFails=UnityEngine.Random.value<chance;
      _uiSound.PlayWonderLaunchSound();
      _notifications.Post(_loc.T("RocketProgram.Notification.Liftoff",_loc.T(mission.DisplayNameLocKey),
        Mathf.RoundToInt(chance*100f)),this);
    }

    public override void Tick() {
      UpdateLegacy();
      if(InFlight) {
        var progress=FlightProgress;
        if(_flightFails&&progress>=Spec.FailurePointFraction)ResolveFlight(false);
        else if(!_flightFails&&progress>=1f)ResolveFlight(true);
      }
      if(Refurbishing&&_cycle.PartialDayNumber>=_refurbishEndDay) {
        _refurbishEndDay=0f;
        _notifications.Post(_loc.T("RocketProgram.Notification.Refurbished"),this);
      }
      UpdateStatuses();
    }

    private void ResolveFlight(bool success) {
      var mission=_byId[_flightMissionId];
      var chance=_flightFailureChance;
      _flightMissionId="";_flightStartDay=0f;_flightFails=false;_flightFailureChance=0f;
      _program.RecordLaunch(mission,success,chance);
      var name=_loc.T(mission.DisplayNameLocKey);
      if(success) {
        _science.AddPoints(mission.ScienceReward);
        UpdateLegacy();
        var reward=_loc.T("RocketProgram.Reward",mission.ScienceReward,mission.LegacyWellbeing,
          Spec.LegacyRadius);
        _notifications.Post(_loc.T("RocketProgram.Notification.Success",name),this);
        _dialogs.Create().SetMessage($"{_loc.T("RocketProgram.Notification.Success",name)}\n\n{_loc.T(mission.SuccessLocKey)}\n\n{reward}").Show();
        if(mission.CompletesStory)_wonder.BeginUnlockCountdown();
      } else {
        _refurbishEndDay=_cycle.DayNumberHoursFromNow(Spec.RefurbishmentHours);
        _explosionSound.Play(GameObject);
        _notifications.Post(_loc.T("RocketProgram.Notification.Failure",name,Mathf.RoundToInt(chance*100f),
          Mathf.RoundToInt(Spec.RefurbishmentHours))+" "+_loc.T(mission.FailureLocKey),this);
      }
    }

    // ---- permanent legacy wellbeing ----
    public bool LegacyPowered=>_power.Powered;
    public bool LegacyApplied=>_legacyApplier.Enabled&&_legacyApplier.Active;
    public IReadOnlyList<ContinuousEffectSpec> AppliedLegacy=>_appliedLegacy;

    // Returns whether a newly completed mission's effect was added.
    private bool SyncLegacyEffects() {
      var added=false;
      foreach(var mission in Spec.Missions) {
        if(!_program.IsCompleted(mission.Id)||_appliedLegacy.Contains(mission.LegacyEffect))continue;
        _appliedLegacy.Add(mission.LegacyEffect);added=true;
      }
      return added;
    }
    private void EnableLegacyApplier() {
      if(_legacyApplier.Enabled)_legacyApplier.Disable();
      _legacyApplier.Enable(_appliedLegacy,_legacyArea.GetBlocksInRectangularRadius(Spec.LegacyRadius),_legacyActive);
      _legacyApplier.UpdateEfficiency(1f);
    }
    private void UpdateLegacy() {
      if(SyncLegacyEffects())EnableLegacyApplier();
      var powered=LegacyPowered;
      if(powered!=_legacyActive) {_legacyActive=powered;_legacyApplier.UpdateActiveState(powered);}
    }

    private void UpdateStatuses() {
      var stage=Stage;var current=CurrentMission;
      foreach(var mission in Spec.Missions) {
        if(_lockedStatus.TryGetValue(mission.Id,out var locked))
          locked.Toggle(stage==RocketPadStage.MissionLocked&&current==mission);
        _completedStatus[mission.Id].Toggle(stage==RocketPadStage.MissionCompleted&&current==mission);
      }
      _refurbishStatus.Toggle(stage==RocketPadStage.Refurbishing);
    }
  }
}
