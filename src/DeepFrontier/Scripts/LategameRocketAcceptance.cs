#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using ConveyorBelt.Algorithm;
using ConveyorBelt.Components;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using TimberPipes.Components;
using TimberPipes.Models;
using TimberPipes.Specs;
using Timberborn.Automation;
using Timberborn.AutomationBuildings;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.BuildingsReachability;
using Timberborn.CameraSystem;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.CoreUI;
using Timberborn.Effects;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.GameWonderCompletion;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.MechanicalSystem;
using Timberborn.NaturalResources;
using Timberborn.NeedSystem;
using Timberborn.NotificationSystem;
using Timberborn.PathSystem;
using Timberborn.RangedEffectSystem;
using Timberborn.ScienceSystem;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TerrainSystem;
using Timberborn.TimbermeshAnimations;
using Timberborn.TimeSystem;
using Timberborn.UnderstructureSystem;
using Timberborn.WaterSystem;
using Timberborn.Workshops;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Records shared by the late-game survey (Scripts/PowerLines/LategameAcceptance.cs, in the optional
  // DeepFrontier.PowerLines assembly because it tests Power Lines cables) and the rocket run below.
  [Serializable] internal sealed class LategameEntityRecord {
    public string Id,Template,Subject,Role,Orientation,Direction,State;
    public bool Flipped,LeverOn;
    public string InputId;
    public Vector3Int Coordinates,Port;
  }
  [Serializable] internal sealed class LategameSaveRecord {
    public string[] Subjects;
    public int RegionX,RegionY,RegionWidth,RegionHeight;
    public LategameEntityRecord[] Entities;
  }
  [Serializable] internal sealed class LategameCheckRecord {
    public string Building,Check,Status,Detail;
    public string Phase;
  }

  // ===================== Rocket program =====================
  // Explicit run on the saved late-game layout ("Lategame acceptance - main"):
  //   -deepFrontierLategameRocket                main sequence; writes three checkpoint saves
  //   -deepFrontierLategameRocketPreparing       fresh-process reload of the preparation checkpoint
  //   -deepFrontierLategameRocketFlight          fresh-process reload of the (failing) flight checkpoint
  //   -deepFrontierLategameRocketRefurbishing    fresh-process reload of the refurbishment checkpoint
  [Context("Game")]
  public sealed class LategameRocketAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(LategameRocketAcceptance.Mode()!=null)Bind<LategameRocketAcceptance>().AsSingleton();
    }
  }
  [Serializable] internal sealed class RocketCheckpointRecord {
    public string Checkpoint,PadId,Stage,RecipeId,FlightMission,LastMission;
    public float Progress,FlightProgress,FlightFailureChance,RefurbishHoursLeft,LastFailureChance,PartialDay;
    public bool Stacked,InFlight,FlightFails,Refurbishing,LastSucceeded,StoryCompleted;
    public int ProcessedGoods,LaunchAttempts,FailedLaunches;
    public string[] CompletedMissions;
    public Dictionary<string,int> Stock;
  }
  internal sealed class LategameRocketAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private const string Tag="[DeepFrontier Rocket]";
    private const string Marker="Deep Frontier Acceptance Fixture";
    private const string Telemetry="GuidanceTelemetry";
    private const string Observatory="RocketMission.OrbitalObservatory";
    private const string Probe="RocketMission.RecoveryProbe";
    private const string Beacon="RocketMission.LongRangeBeacon";
    private static readonly string Outputs=Path.Combine(
      Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding","outputs");
    private static readonly string[] BasicNeeds={"Hunger","Thirst","Sleep"};
    private static readonly string[] Checkpoints={"preparing","flight","refurbishing"};
    // Check 12 completes the native wonder, which also writes the player's profile outside the save.
    private static bool Ending=>Environment.GetCommandLineArgs().Contains("-deepFrontierRocketEnding");
    public static string Mode() {
      var args=Environment.GetCommandLineArgs();
      if(args.Contains("-deepFrontierLategameRocket"))return "main";
      foreach(var c in Checkpoints)if(args.Contains("-deepFrontierLategameRocket"+char.ToUpper(c[0])+c.Substring(1)))return c;
      return null;
    }
    private sealed class Step {
      public string Name;public Func<bool> Until;public Action Then;public float TimeoutHours;
    }

    private readonly EntityRegistry _entities;
    private readonly TemplateService _templates;
    private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock;
    private readonly WorkingHoursManager _hours;
    private readonly GameSaver _saver;
    private readonly GameLoader _loader;
    private readonly RocketProgramService _program;
    private readonly ScienceService _science;
    private readonly NotificationBus _notifications;
    private readonly WonderCompletionCountdownStarter _wonder;
    private readonly PanelStack _panels;
    private readonly CameraService _camera;
    private readonly string _mode=Mode();
    private readonly List<LategameCheckRecord> _results=new();
    private readonly Queue<Step> _steps=new();
    private readonly List<Worker> _workers=new();
    private readonly List<string> _posted=new();
    private readonly Dictionary<MechanicalNode,float> _supplies=new();
    private readonly System.Reflection.FieldInfo _flightFailsField=
      typeof(RocketLaunchPad).GetField("_flightFails",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
    private BlockObject _padBlock,_controlBlock,_lever;
    private RocketLaunchPad _pad;
    private Manufactory _manufactory;
    private RocketLaunchVisual _visual;
    private Worker _controller;
    private Step _step;
    private float _stepStart,_stepReal,_lastNeeds,_holdStart,_mark,_scienceAtLiftoff,_legacyPoints,_lastHeight;
    private float _progressMark;
    private Dictionary<string,int> _stockMark=new();
    private int _frame;
    private bool _finished,_saved,_rose,_freezing;
    private float _storyDay=-1;
    private Worker _legacyBeaver;
    private RocketCheckpointRecord _checkpoint;

    public LategameRocketAcceptance(EntityRegistry entities,TemplateService templates,SpeedManager speed,IDayNightCycle clock,
      WorkingHoursManager hours,GameSaver saver,GameLoader loader,RocketProgramService program,ScienceService science,
      NotificationBus notifications,WonderCompletionCountdownStarter wonder,PanelStack panels,CameraService camera) {
      _entities=entities;_templates=templates;_speed=speed;
      _clock=clock;_hours=hours;_saver=saver;_loader=loader;_program=program;_science=science;_notifications=notifications;
      _wonder=wonder;_panels=panels;_camera=camera;
    }
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private void Record(string check,bool ok,string detail) {
      _results.Add(new LategameCheckRecord{Building="LaunchPad",Check=check,Status=ok?"PASS":"FAIL",Detail=detail,Phase=_step?.Name??_mode});
      var line=Tag+" "+(ok?"PASS ":"FAIL ")+check+": "+detail;
      if(ok)Debug.Log(line);else Debug.LogWarning(line);
    }
    private void Skip(string check,string reason) {
      _results.Add(new LategameCheckRecord{Building="LaunchPad",Check=check,Status="SKIP",Detail=reason,Phase=_step?.Name??_mode});
      Debug.Log(Tag+" SKIP "+check+": "+reason);
    }
    private static bool Near(float a,float b,float tolerance=.0001f)=>Math.Abs(a-b)<=tolerance;
    private float Hours=>(_clock.PartialDayNumber-_stepStart)*24;
    private void Then(string name,Func<bool> until,Action then,float timeoutHours=12)=>
      _steps.Enqueue(new Step{Name=name,Until=until,Then=then,TimeoutHours=timeoutHours});
    private void After(string name,float hours,Action then)=>Then(name,()=>Hours>=hours,then,hours+2);

    // ---------- helpers ----------
    private RocketMissionSpec Mission(string recipe)=>_pad.Missions.Single(m=>m.RecipeId==recipe);
    private RecipeSpec Recipe(string id)=>_manufactory.ProductionRecipes.Single(r=>r.Id==id);
    private void Select(string id) {if(!_manufactory.HasCurrentRecipe||_manufactory.CurrentRecipe.Id!=id)_manufactory.SetRecipe(Recipe(id));}
    private Dictionary<string,int> Stock(string recipe)=>
      Recipe(recipe).Ingredients.ToDictionary(g=>g.Id,g=>_manufactory.Inventory.AmountInStock(g.Id));
    // Mission recipes share goods with different limits; leftovers of the previous mission
    // would otherwise stay above the new limits. Clear the pad's mission goods first.
    private void ClearPadInventory() {
      var inventory=_manufactory.Inventory;
      foreach(var id in _manufactory.ProductionRecipes.SelectMany(r=>r.Ingredients.Select(g=>g.Id).Concat(r.Products.Select(g=>g.Id))).Distinct()) {
        int amount=inventory.AmountInStock(id);
        if(amount==0)continue;
        Require(inventory.UnreservedAmountInStock(id)==amount,"Pad stock of "+id+" is reserved; it cannot be cleared between missions");
        inventory.TakeExisting(new GoodAmount(id,amount));
      }
    }
    private void StockFully(string recipe) {
      ClearPadInventory();
      foreach(var g in Recipe(recipe).Ingredients) {
        int missing=_manufactory.Inventory.LimitedAmount(g.Id)-_manufactory.Inventory.AmountInStock(g.Id);
        if(missing>0)_manufactory.Inventory.GiveExisting(new GoodAmount(g.Id,missing));
      }
    }
    private static string Show(Dictionary<string,int> stock)=>string.Join(",",stock.Select(p=>p.Key+"="+p.Value));
    private Workplace PadWorkplace=>_padBlock.GetComponent<Workplace>();
    private readonly List<Worker> _crew=new();
    // The pad is specialist-only (FrontierSpecialistWorkplaceSpec): SpecialistStaffing releases
    // anyone without its discipline. Mission Control is ordinary. Untrained adults are graduated
    // through SpecialistTrait.Graduate; a specialist of another discipline (e.g. the late-game
    // pass's Nuclear crew) runs Mission Control instead.
    private void ChooseCrew() {
      var discipline=_padBlock.GetComponent<FrontierSpecialistWorkplaceSpec>()?.Discipline;
      SpecialistTrait Trait(Worker w)=>w.GetComponent<SpecialistTrait>();
      _controller=_workers.FirstOrDefault(w=>Trait(w).IsSpecialist&&!Trait(w).Has(discipline))
        ??_workers.Last();
      var candidates=_workers.Where(w=>w!=_controller&&(discipline==null||Trait(w).Has(discipline)||!Trait(w).IsSpecialist))
        .OrderBy(w=>Trait(w).Has(discipline)?0:1).ToList();
      int count=Math.Min(PadWorkplace.MaxWorkers,candidates.Count);
      _crew.AddRange(candidates.Take(count));
      int graduated=0;
      if(discipline!=null)foreach(var w in _crew.Where(w=>!Trait(w).IsSpecialist)){Trait(w).Graduate(discipline);graduated++;}
      Record("staffing",count==8&&_controller,_crew.Count+" pad crew ("+(discipline??"no discipline")+", "+graduated+
        " graduated by SpecialistTrait.Graduate) and one Mission Control worker from "+_workers.Count+" adults");
    }
    private void Staff() {
      var pad=PadWorkplace;
      while(pad.DesiredWorkers<_crew.Count)pad.IncreaseDesiredWorkers();
      while(pad.DesiredWorkers>_crew.Count)pad.DecreaseDesiredWorkers();
      foreach(var w in _crew)if(w.Workplace!=pad){w.Unemploy();w.EmployAt(pad);}
      StaffControl(true);
    }
    private void StaffControl(bool staffed) {
      var control=_controlBlock.GetComponent<Workplace>();
      if(staffed) {
        while(control.DesiredWorkers<1)control.IncreaseDesiredWorkers();
        if(_controller.Workplace!=control){_controller.Unemploy();_controller.EmployAt(control);}
      } else {
        while(control.DesiredWorkers>0)control.DecreaseDesiredWorkers();
        foreach(var w in control.AssignedWorkers.ToList())w.Unemploy();
      }
    }
    private void TopUpNeeds() {
      foreach(var w in _workers) {
        var needs=w.GetComponent<NeedManager>();
        foreach(var id in BasicNeeds)needs.ApplyEffect(new InstantEffect(id,needs.GetNeedSpec(id).MaximumValue-needs.GetNeedPoints(id),1));
      }
    }
    private void SetSupply(bool full) {
      var node=_padBlock.GetComponent<MechanicalNode>();
      if(_supplies.Count==0)foreach(var g in node.Graph.Generators)_supplies[g]=g.OutputMultiplier;
      foreach(var g in _supplies.Keys)g.SetOutputMultiplier(full?_supplies[g]:0);
      if(!full) {
        // The whole dev-generator outputs just below the launch load (27,000 hp: 20,000 hp from one generator).
        var dev=_supplies.Keys.First(g=>g.GetComponent<TemplateSpec>().TemplateName=="DevPowerGenerator");
        int rated=dev.GetComponent<MechanicalNodeSpec>().PowerOutput;
        int below=AcceptancePower.Units(_padBlock.GetComponent<MechanicalNodeSpec>().PowerInput,rated)-1;
        Require(below>0,"The launch load is within one dev generator's output; no underpowered supply is possible");
        dev.SetOutputMultiplier(below);
      }
    }
    // Native dialogs lock game speed; the success dialog is closed so simulation continues.
    private bool CloseDialogs() {
      bool closed=false;
      var field=typeof(PanelStack).GetField("_stack",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
      Require(field!=null,"PanelStack._stack not found");
      foreach(var stacked in ((System.Collections.IEnumerable)field.GetValue(_panels)).Cast<object>().ToList()) {
        var controller=stacked.GetType().GetProperty("PanelController")?.GetValue(stacked);
        if(controller is DialogBox dialog){dialog.Close();closed=true;Debug.Log(Tag+" closed a native dialog");}
      }
      if(closed&&!_freezing)_speed.ChangeSpeed(3);
      return closed;
    }
    private void ForceOutcome(bool fails) {
      Require(_flightFailsField!=null,"RocketLaunchPad._flightFails field not found");
      _flightFailsField.SetValue(_pad,fails);
      Require(_pad.FlightFails==fails,"Forced flight outcome did not apply");
    }
    private void CheckVisual(string label,bool rocket,bool exhaust) {
      if(_visual==null)return;
      Record("visual "+label,_visual.RocketVisible==rocket&&_visual.ExhaustVisible==exhaust,
        "rocket shown="+_visual.RocketVisible+" exhaust shown="+_visual.ExhaustVisible+" height="+_visual.RocketHeight.ToString("0.###"));
    }
    private void Unchanged(string label,string recipe) {
      var now=Stock(recipe);
      Record(label+" holds progress and stock",Near(_manufactory.ProductionProgress,_progressMark)&&now.All(p=>_stockMark[p.Key]==p.Value),
        "progress "+_progressMark.ToString("0.####")+"->"+_manufactory.ProductionProgress.ToString("0.####")+" stock "+Show(now));
    }
    private void Mark(string recipe){_progressMark=_manufactory.ProductionProgress;_stockMark=Stock(recipe);}
    private bool Working=>_padBlock.GetComponent<Workshop>().CurrentlyWorking;

    // ---------- lifecycle ----------
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName==Marker),
        "Rocket acceptance requires the marked disposable settlement");
      _speed.ChangeSpeed(0);
      var layout=JsonConvert.DeserializeObject<LategameSaveRecord>(File.ReadAllText(Path.Combine(Outputs,"lategame-reload-expectations.json")));
      var byId=_entities.Entities.ToDictionary(e=>e.EntityId.ToString());
      BlockObject Saved(string subject,string role) {
        var r=layout.Entities.SingleOrDefault(x=>x.Subject==subject&&x.Role==role);
        return r!=null&&byId.TryGetValue(r.Id,out var e)?e.GetComponent<BlockObject>():null;
      }
      _padBlock=Saved("LaunchPad","building");_controlBlock=Saved("MissionControl","building");_lever=Saved("LaunchPad","lever");
      // Never throw here: an exception in PostLoad aborts the scene load. Setup records it.
      if(!_padBlock||!_controlBlock)return;
      _pad=_padBlock.GetComponent<RocketLaunchPad>();_manufactory=_padBlock.GetComponent<Manufactory>();
      _visual=_padBlock.GetComponent<RocketLaunchVisual>();
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60)Setup();
        if(_frame<60)return;
        if((_clock.PartialDayNumber-_lastNeeds)*24>2){TopUpNeeds();_lastNeeds=_clock.PartialDayNumber;}
        if(_frame%30==0)CloseDialogs();
        if(_storyDay<0&&_program.StoryCompleted)_storyDay=_clock.PartialDayNumber;
        if(_visual!=null&&_pad.InFlight) {
          _rose|=_visual.RocketHeight>_lastHeight+.0001f&&_visual.ExhaustVisible;_lastHeight=_visual.RocketHeight;
        }
        if(_step==null) {
          if(_steps.Count==0){Finish(true);return;}
          _step=_steps.Dequeue();_stepStart=_clock.PartialDayNumber;_stepReal=Time.unscaledTime;
          Debug.Log(Tag+" STEP "+_step.Name);
        }
        if(_step.Until()) {var s=_step;_step=null;s.Then();}
        else if(Hours>_step.TimeoutHours||Time.unscaledTime-_stepReal>3600) {
          Record(_step.Name,false,"timed out after "+_step.TimeoutHours+" h; stage="+_pad.Stage+" progress="+
            _manufactory.ProductionProgress.ToString("0.###")+" working="+Working+" workers="+PadWorkplace.NumberOfAssignedWorkers+
            " power="+_padBlock.GetComponent<MechanicalNode>().PowerEfficiency.ToString("0.##"));
          Finish(false);
        }
      } catch(Exception error) {
        _finished=true;_speed.ChangeSpeed(0);WriteResults();
        Debug.LogError(Tag+" FAILED: "+error);
      }
    }

    private void Setup() {
      if(!_padBlock||!_controlBlock) {
        Record("saved layout",false,"Lategame acceptance - main lacks "+(!_padBlock?"the LaunchPad ":"")+(!_controlBlock?"MissionControl":"")+
          "; the late-game pass must place both");
        Finish(false);return;
      }
      if(!_pad){Record("setup components",false,"LaunchPad has no RocketLaunchPad component");Finish(false);return;}
      var dropped=AcceptanceLoadingIssues.DroppedObjects;
      Record("save loading issues",AcceptanceLoadingIssues.Reported,dropped.Count==0?"loaded without dropped objects":
        "tolerated "+dropped.Count+" dropped objects (the pad, Mission Control and their attachments are bound by id): "+
        string.Join("; ",dropped.Select(d=>d.Name+" "+d.Coordinates)));
      if(_mode!="main")VerifyCheckpoint();
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>()&&
          e.GetComponent<BlockObject>()!=_padBlock&&e.GetComponent<BlockObject>()!=_controlBlock))
        e.GetComponent<PausableBuilding>().Pause();
      foreach(var b in new[]{_padBlock,_controlBlock}) {
        var p=b.GetComponent<PausableBuilding>();if(p.Paused)p.Resume();
      }
      _hours.WorkedPartOfDay=1;
      _workers.AddRange(_entities.Entities.Where(e=>e.HasComponent<Worker>()&&e.GetComponent<Worker>().WorkerType=="Beaver")
        .Select(e=>e.GetComponent<Worker>()));
      Require(_workers.Count>=2,"Rocket acceptance needs adult beaver workers");
      ChooseCrew();
      _notifications.NotificationPosted+=(sender,args)=>{
        if(args.Notification.Subject==_padBlock.GetComponent<EntityComponent>().EntityId)_posted.Add(args.Notification.Description);
      };
      _camera.MoveTargetTo(_padBlock.Transform.position);_camera.SetZoomLevel(25,0);
      TopUpNeeds();_lastNeeds=_clock.PartialDayNumber;
      if(_mode=="main")PlanMain();else PlanReload();
      _speed.ChangeSpeed(3);
    }

    // ---------- main sequence ----------
    private void PlanMain() {
      // 1. setup
      // The legacy bonus is driven by RocketLaunchPad itself (LegacyRadius); the pad carries no RangedEffectBuilding.
      var legacyRadius=_pad?_pad.Spec.LegacyRadius:-1;
      Record("setup components",_pad&&_manufactory&&legacyRadius==40&&!_padBlock.HasComponent<RangedEffectBuilding>()&&_controlBlock.HasComponent<RocketMissionControl>(),
        "RocketLaunchPad="+(bool)_pad+" Manufactory="+(bool)_manufactory+" LegacyRadius="+legacyRadius+" RangedEffectBuilding="+_padBlock.HasComponent<RangedEffectBuilding>()+
        " RocketMissionControl="+_controlBlock.HasComponent<RocketMissionControl>());
      var recipes=_manufactory.ProductionRecipes.Select(r=>r.Id).ToArray();
      Record("setup recipes",recipes.SequenceEqual(new[]{Telemetry,Observatory,Probe,Beacon}),string.Join(",",recipes));
      Record("setup program",_program.LaunchAttempts==0&&_program.FailedLaunches==0&&_program.CompletedMissions.Count==0,
        "attempts="+_program.LaunchAttempts+" failures="+_program.FailedLaunches+" completed="+_program.CompletedMissions.Count);
      Record("setup workers",PadWorkplace.MaxWorkers==8,"pad MaxWorkers="+PadWorkplace.MaxWorkers);
      Record("spec timings",Near(_pad.Spec.FlightHours,.75f)&&Near(_pad.Spec.FlightHours*_pad.Spec.FailurePointFraction,.3f)&&
        Near(_pad.Spec.RefurbishmentHours,72)&&_pad.Spec.LaunchHoldProgress>=.99f&&_pad.Spec.LaunchHoldProgress<1,
        "flight "+_pad.Spec.FlightHours+" h, failure point "+(_pad.Spec.FlightHours*_pad.Spec.FailurePointFraction)+" h, refurbishment "+
        _pad.Spec.RefurbishmentHours+" h, hold "+_pad.Spec.LaunchHoldProgress);
      Require(recipes.Contains(Observatory)&&recipes.Contains(Probe)&&recipes.Contains(Beacon),"Mission recipes are not installed");
      AddLaunchPower();
      // 2. staging
      Select(Observatory);
      var limits=Recipe(Observatory).Ingredients.Select(g=>_manufactory.Inventory.LimitedAmount(g.Id)).ToArray();
      Record("staging limits",limits.SequenceEqual(new[]{24,12,4,2,200,200}),string.Join("/",limits));
      Record("staging stage",_pad.Stage==RocketPadStage.Staging&&!_pad.RocketStacked,"stage="+_pad.Stage+" stacked="+_pad.RocketStacked);
      CheckVisual("hidden while staging",false,false);
      // 3. locked
      Select(Probe);StockFully(Probe);Staff();
      Then("locked: staffed and powered",()=>PadWorkplace.NumberOfAssignedWorkers>0&&_padBlock.GetComponent<MechanicalNode>().Powered,()=>{
        Record("locked stage",_pad.Stage==RocketPadStage.MissionLocked&&_pad.ProductionEfficiency()==0,
          "stage="+_pad.Stage+" efficiency="+_pad.ProductionEfficiency());
        Mark(Probe);
      });
      After("locked: 4 staffed powered hours",4.1f,()=>{
        Record("locked staffing",PadWorkplace.NumberOfAssignedWorkers>0&&_padBlock.GetComponent<MechanicalNode>().Powered,
          "workers="+PadWorkplace.NumberOfAssignedWorkers+" powered="+_padBlock.GetComponent<MechanicalNode>().Powered);
        Unchanged("locked",Probe);
        // 4. paused
        Select(Observatory);StockFully(Observatory);_padBlock.GetComponent<PausableBuilding>().Pause();Mark(Observatory);
        Record("paused stage",_pad.Stage==RocketPadStage.Blocked&&_pad.ProductionEfficiency()==0,"stage="+_pad.Stage+" efficiency="+_pad.ProductionEfficiency());
      });
      After("paused: 1 hour",1,()=>{
        Unchanged("paused",Observatory);
        _padBlock.GetComponent<PausableBuilding>().Resume();
        if(_lever) {
          _lever.GetComponent<Lever>().SwitchState(false);
        } else {Skip("automation Off","no saved lever on the LaunchPad");Staff();}
      });
      if(_lever) {
        After("automation Off: settle",.25f,()=>{
          Record("automation Off stage",_pad.Stage==RocketPadStage.Blocked&&_pad.ProductionEfficiency()==0,
            "input="+_padBlock.GetComponent<Automatable>().State+" stage="+_pad.Stage+" efficiency="+_pad.ProductionEfficiency());
          Mark(Observatory);
        });
        After("automation Off: 1 hour",1,()=>{Unchanged("automation Off",Observatory);_lever.GetComponent<Lever>().SwitchState(true);Staff();});
      }
      // 5. loading
      Then("resume: preparation starts",()=>_manufactory.ProductionProgress>0,()=>{
        Record("resume progress",_manufactory.ProductionProgress>0,"progress="+_manufactory.ProductionProgress.ToString("0.####"));
        var now=Stock(Observatory);
        var expected=Recipe(Observatory).Ingredients.ToDictionary(g=>g.Id,g=>_stockMark[g.Id]-g.Amount);
        Record("loading consumes recipe",now.All(p=>expected[p.Key]==p.Value)&&_manufactory.ProcessedGoods.Count==6&&_pad.RocketStacked,
          "stock "+Show(now)+" processed="+_manufactory.ProcessedGoods.Count+" stacked="+_pad.RocketStacked);
        CheckVisual("shown while preparing",true,false);
      });
      Then("loading: launch load",()=>Working,()=>{
        var node=_padBlock.GetComponent<MechanicalNode>();
        int load=_padBlock.GetComponent<MechanicalNodeSpec>().PowerInput;
        Record("launch load",node.Actuals.PowerInput==load,"native input "+node.Actuals.PowerInput+" of "+load+" hp, graph supply "+node.Graph.PowerSupply);
      },6);
      FreezeAndSave("preparing");
      // 6. scrub
      Then("scrub",()=>true,()=>{
        _posted.Clear();Select(Telemetry);
        var now=Stock(Observatory);
        Record("scrub restores",Recipe(Observatory).Ingredients.All(g=>now[g.Id]==g.Amount)&&Near(_manufactory.ProductionProgress,0)&&!_pad.RocketStacked,
          "stock "+Show(now)+" progress="+_manufactory.ProductionProgress+" stacked="+_pad.RocketStacked);
        Record("scrub notification",_posted.Any(t=>t.StartsWith("Launch scrubbed",StringComparison.Ordinal)),string.Join(" | ",_posted));
        // 7. power hold
        Select(Observatory);SetSupply(false);
      });
      Then("power hold",()=>_pad.Stage==RocketPadStage.HoldingForPower,()=>{_holdStart=_clock.PartialDayNumber;},12);
      After("power hold: 1 hour",1,()=>{
        float p=_manufactory.ProductionProgress;
        Record("power hold",p>=.99f&&p<1&&_pad.Stage==RocketPadStage.HoldingForPower&&!_pad.InFlight&&_program.LaunchAttempts==0,
          "progress="+p.ToString("0.#####")+" stage="+_pad.Stage+" inFlight="+_pad.InFlight+" supply="+
          _padBlock.GetComponent<MechanicalNode>().Graph.PowerSupply+"/"+_padBlock.GetComponent<MechanicalNode>().Graph.PowerDemand);
        // 8. odds with and without Mission Control
        float with=_pad.FailureChance(Mission(Observatory));
        StaffControl(false);
        float without=_pad.FailureChance(Mission(Observatory));
        Record("odds",Near(with,.15f)&&Near(without,.30f)&&_program.LaunchAttempts==0,"with Mission Control "+with+", without "+without);
        StaffControl(true);
      });
      Then("odds: Mission Control operating again",()=>_program.OperatingMissionControls>0,()=>SetSupply(true));
      Liftoff(Observatory,false);
      // 9. success
      After("success after 0.75 h",.8f,()=>{
        var m=Mission(Observatory);
        Record("success",!_pad.InFlight&&_program.IsCompleted(m.Id)&&_program.LaunchAttempts==1&&
          _science.SciencePoints-_scienceAtLiftoff==100000,"inFlight="+_pad.InFlight+" completed="+_program.IsCompleted(m.Id)+
          " attempts="+_program.LaunchAttempts+" science +"+(_science.SciencePoints-_scienceAtLiftoff));
        CheckVisual("hidden after success",false,false);
        CloseDialogs();
        Select(Observatory);
        Record("reselect completed",_pad.Stage==RocketPadStage.MissionCompleted&&_pad.ProductionEfficiency()==0,
          "stage="+_pad.Stage+" efficiency="+_pad.ProductionEfficiency());
        Select(Probe);
        Record("next mission unlocked",_pad.Stage==RocketPadStage.Staging,"stage="+_pad.Stage);
      });
      After("legacy: 1 hour in range",1,()=>{
        var need=Mission(Observatory).LegacyEffect.NeedId;
        if(!_legacyBeaver){Record("legacy wellbeing",false,"no beaver within 40 tiles of the pad");return;}
        float now=_legacyBeaver.GetComponent<NeedManager>().GetNeedPoints(need);
        Record("legacy wellbeing",now>_legacyPoints&&_padBlock.GetComponent<MechanicalNode>().Powered&&
          Vector3.Distance(_legacyBeaver.Transform.position,_padBlock.Transform.position)<40,
          need+" "+_legacyPoints.ToString("0.###")+" (at liftoff) -> "+now.ToString("0.###")+" at "+
          Vector3.Distance(_legacyBeaver.Transform.position,_padBlock.Transform.position).ToString("0.#")+" tiles");
        // 10. failure
        StockFully(Probe);
      });
      Then("probe preparation starts",()=>_pad.RocketStacked,()=>{},8);
      Liftoff(Probe,true);
      FreezeAndSave("flight");
      After("failure after 0.3 h",.35f,()=>{
        var m=Mission(Probe);var stock=Stock(Probe);
        Record("failure",!_pad.InFlight&&!_program.IsCompleted(m.Id)&&_program.FailedLaunches==1,
          "inFlight="+_pad.InFlight+" completed="+_program.IsCompleted(m.Id)+" failures="+_program.FailedLaunches);
        Record("refurbishing",_pad.Refurbishing&&Math.Abs(_pad.RefurbishHoursLeft-72)<.5f,
          "refurbishing="+_pad.Refurbishing+" hours left="+_pad.RefurbishHoursLeft.ToString("0.##"));
        Record("no parts returned",stock.All(p=>_stockMark[p.Key]==p.Value),"stock "+Show(stock)+" at liftoff "+Show(_stockMark));
        var efficiencies=new List<string>();
        foreach(var r in _manufactory.ProductionRecipes){Select(r.Id);efficiencies.Add(r.Id+"="+_pad.ProductionEfficiency());}
        Select(Probe);
        Record("refurbishing stops all recipes",efficiencies.All(e=>e.EndsWith("=0",StringComparison.Ordinal)),string.Join(",",efficiencies));
        CheckVisual("hidden after failure",false,false);
        CloseDialogs();
      });
      FreezeAndSave("refurbishing");
      Then("refurbishment ends",()=>!_pad.Refurbishing,()=>{
        float next=_pad.FailureChance(Mission(Probe));
        Record("refurbished",!_pad.Refurbishing&&Near(next,_program.LastFailureChance-.05f),
          "next chance "+next+" vs last "+_program.LastFailureChance+"; elapsed "+Hours.ToString("0.#")+" h");
        StockFully(Probe);
      },76);
      // 12. ending
      Then("probe again",()=>_pad.RocketStacked,()=>{},8);
      Liftoff(Probe,false);
      After("probe success",.8f,()=>{
        Record("probe success",_program.IsCompleted(Mission(Probe).Id),"completed="+string.Join(",",_program.CompletedMissions));
        CloseDialogs();Select(Beacon);
        if(!Ending) {
          // Default stop: the final mission is selected (staged) but never stocked or launched.
          var pad=PadWorkplace;
          while(pad.DesiredWorkers>0)pad.DecreaseDesiredWorkers();
          foreach(var w in pad.AssignedWorkers.ToList())w.Unemploy();
          Record("final mission staged, not launched",_pad.Stage==RocketPadStage.Staging&&!_pad.RocketStacked&&!_pad.InFlight&&
            !_program.StoryCompleted,"stage="+_pad.Stage+" stacked="+_pad.RocketStacked+" story="+_program.StoryCompleted);
          Skip("story ending and wonder countdown","opt-in: writes player profile (native wonder completion records a first-time map completion); "+
            "run with -Ending / -deepFrontierRocketEnding");
          return;
        }
        StockFully(Beacon);
      });
      if(!Ending)return;
      Then("beacon preparation starts",()=>_pad.RocketStacked,()=>{},8);
      Liftoff(Beacon,false);
      After("beacon success",.8f,()=>{
        Record("story completed",_program.StoryCompleted&&_program.IsCompleted(Mission(Beacon).Id),
          "story="+_program.StoryCompleted+" completed="+string.Join(",",_program.CompletedMissions));
        CloseDialogs();
      });
      Then("wonder countdown",()=>_wonder.CountdownFinished,()=>{
        float elapsed=(_clock.PartialDayNumber-_storyDay)*24;
        Record("wonder countdown finished",_storyDay>=0&&Math.Abs(elapsed-.5f)<.1f,"native countdown finished "+elapsed.ToString("0.###")+
          " h after the story completed");
        CloseDialogs();
      },2);
    }
    private void AddLaunchPower() {
      var node=_padBlock.GetComponent<MechanicalNode>();
      // The layout run's test generator (AcceptancePower) is loaded at strength 1; it is raised by whole
      // rated outputs until the graph supplies the pad's data load plus 2,000 hp for the rest of its graph.
      var source=node.Graph.Generators.FirstOrDefault(g=>g.GetComponent<TemplateSpec>().TemplateName=="DevPowerGenerator");
      Require(source,"LaunchPad graph has no native dev generator from the layout run");
      int missing=_padBlock.GetComponent<MechanicalNodeSpec>().PowerInput+2000-node.Graph.PowerSupply;
      if(missing>0)source.SetOutputMultiplier(source.OutputMultiplier+AcceptancePower.Units(missing,source.GetComponent<MechanicalNodeSpec>().PowerOutput));
    }
    private void Liftoff(string recipe,bool fails) {
      Then("liftoff "+recipe,()=>_pad.InFlight,()=>{
        ForceOutcome(fails);
        _scienceAtLiftoff=_science.SciencePoints;_stockMark=Stock(recipe);_lastHeight=0;_rose=false;
        var m=Mission(recipe);
        Record("liftoff "+m.Id,_pad.InFlight&&_pad.FlightMission==m&&Near(_pad.FlightFailureChance,_pad.FailureChance(m)),
          "flight chance "+_pad.FlightFailureChance+" (forced outcome: "+(fails?"failure":"success")+")");
        if(recipe==Observatory) {
          Record("liftoff odds",Near(_pad.FlightFailureChance,.15f),"chance at liftoff "+_pad.FlightFailureChance);
          // Legacy baseline before the mission succeeds, so the new effect is not already at the need's maximum.
          _legacyBeaver=_workers.OrderBy(w=>Vector3.Distance(w.Transform.position,_padBlock.Transform.position))
            .FirstOrDefault(w=>Vector3.Distance(w.Transform.position,_padBlock.Transform.position)<40);
          if(_legacyBeaver)_legacyPoints=_legacyBeaver.GetComponent<NeedManager>().GetNeedPoints(m.LegacyEffect.NeedId);
        }
      },10);
      if(_visual!=null)After("flight visual "+recipe,.2f,()=>Record("visual rises with exhaust",_rose,
        "height="+_visual.RocketHeight.ToString("0.###")+" exhaust="+_visual.ExhaustVisible));
      else if(recipe==Observatory)Skip("visual","LaunchPad.Rocket and LaunchPad.RocketExhaust nodes are not exported yet (no RocketLaunchVisual)");
    }
    private void FreezeAndSave(string checkpoint) {
      Then("checkpoint "+checkpoint,()=>true,()=>{
        _freezing=true;_speed.ChangeSpeed(0);_saved=false;
        var record=Capture(checkpoint);
        File.WriteAllText(Path.Combine(Outputs,"lategame-rocket-"+checkpoint+".json"),JsonConvert.SerializeObject(record,Formatting.Indented));
        _saver.QueueSave(new SaveReference("Lategame rocket - "+checkpoint,_loader.LoadedSave.SettlementReference),()=>{
          _saved=true;Debug.Log(Tag+" CHECKPOINT "+checkpoint+" SAVED");
        });
      });
      Then("checkpoint "+checkpoint+" saved",()=>_saved,()=>{_freezing=false;_speed.ChangeSpeed(3);},1);
    }
    private RocketCheckpointRecord Capture(string checkpoint)=>new RocketCheckpointRecord{
      Checkpoint=checkpoint,PadId=_padBlock.GetComponent<EntityComponent>().EntityId.ToString(),Stage=_pad.Stage.ToString(),
      RecipeId=_manufactory.CurrentRecipe?.Id,Progress=_manufactory.ProductionProgress,Stacked=_pad.RocketStacked,
      ProcessedGoods=_manufactory.ProcessedGoods.Count,InFlight=_pad.InFlight,FlightMission=_pad.FlightMission?.Id,
      FlightFails=_pad.FlightFails,FlightFailureChance=_pad.FlightFailureChance,FlightProgress=_pad.FlightProgress,
      Refurbishing=_pad.Refurbishing,RefurbishHoursLeft=_pad.RefurbishHoursLeft,PartialDay=_clock.PartialDayNumber,
      CompletedMissions=_program.CompletedMissions.ToArray(),LaunchAttempts=_program.LaunchAttempts,FailedLaunches=_program.FailedLaunches,
      LastMission=_program.LastMission,LastSucceeded=_program.LastSucceeded,LastFailureChance=_program.LastFailureChance,
      StoryCompleted=_program.StoryCompleted,
      Stock=_manufactory.CurrentRecipe==null?new Dictionary<string,int>():Stock(_manufactory.CurrentRecipe.Id)};

    // ---------- reload ----------
    private void VerifyCheckpoint() {
      _checkpoint=JsonConvert.DeserializeObject<RocketCheckpointRecord>(File.ReadAllText(Path.Combine(Outputs,"lategame-rocket-"+_mode+".json")));
      Require(_checkpoint!=null&&_checkpoint.Checkpoint==_mode,"Missing rocket checkpoint record "+_mode);
      var now=Capture(_mode);
      Record("reload pad identity",now.PadId==_checkpoint.PadId,"pad "+now.PadId);
      Record("reload "+_mode+" pad state",now.Stage==_checkpoint.Stage&&now.RecipeId==_checkpoint.RecipeId&&Near(now.Progress,_checkpoint.Progress,.00001f)&&
        now.Stacked==_checkpoint.Stacked&&now.ProcessedGoods==_checkpoint.ProcessedGoods&&now.InFlight==_checkpoint.InFlight&&
        now.FlightMission==_checkpoint.FlightMission&&now.FlightFails==_checkpoint.FlightFails&&
        Near(now.FlightFailureChance,_checkpoint.FlightFailureChance)&&Near(now.FlightProgress,_checkpoint.FlightProgress,.001f)&&
        now.Refurbishing==_checkpoint.Refurbishing&&Near(now.RefurbishHoursLeft,_checkpoint.RefurbishHoursLeft,.01f)&&
        now.Stock.Count==_checkpoint.Stock.Count&&now.Stock.All(p=>_checkpoint.Stock.TryGetValue(p.Key,out var v)&&v==p.Value),
        "stage="+now.Stage+" recipe="+now.RecipeId+" progress="+now.Progress.ToString("0.####")+" stacked="+now.Stacked+
        " processed="+now.ProcessedGoods+" inFlight="+now.InFlight+"/"+now.FlightMission+" fails="+now.FlightFails+
        " flight progress="+now.FlightProgress.ToString("0.###")+" refurbishing="+now.Refurbishing+" left="+now.RefurbishHoursLeft.ToString("0.##")+
        " stock "+Show(now.Stock));
      Record("reload program state",now.CompletedMissions.SequenceEqual(_checkpoint.CompletedMissions)&&now.LaunchAttempts==_checkpoint.LaunchAttempts&&
        now.FailedLaunches==_checkpoint.FailedLaunches&&now.LastMission==_checkpoint.LastMission&&now.LastSucceeded==_checkpoint.LastSucceeded&&
        Near(now.LastFailureChance,_checkpoint.LastFailureChance)&&now.StoryCompleted==_checkpoint.StoryCompleted,
        "completed="+string.Join(",",now.CompletedMissions)+" attempts="+now.LaunchAttempts+" failures="+now.FailedLaunches+
        " last="+now.LastMission+"/"+now.LastSucceeded+"/"+now.LastFailureChance+" story="+now.StoryCompleted);
    }
    private void PlanReload() {
      Staff();
      if(_mode=="preparing")
        After("preparation continues",.5f,()=>Record("preparation continues after reload",_pad.RocketStacked&&!_pad.InFlight&&
          _manufactory.ProductionProgress>_checkpoint.Progress,"progress "+_checkpoint.Progress.ToString("0.####")+"->"+
          _manufactory.ProductionProgress.ToString("0.####")));
      else if(_mode=="flight")
        Then("saved failing flight resolves",()=>!_pad.InFlight,()=>{
          Record("saved flight outcome after reload",_program.FailedLaunches==_checkpoint.FailedLaunches+1&&_pad.Refurbishing,
            "failures "+_checkpoint.FailedLaunches+"->"+_program.FailedLaunches+" refurbishing="+_pad.Refurbishing);
          CloseDialogs();
        },2);
      else
        After("refurbishment continues",.5f,()=>Record("refurbishment continues after reload",_pad.Refurbishing&&
          _pad.ProductionEfficiency()==0&&Math.Abs(_pad.RefurbishHoursLeft-(_checkpoint.RefurbishHoursLeft-Hours))<.1f,
          "hours left "+_checkpoint.RefurbishHoursLeft.ToString("0.##")+"->"+_pad.RefurbishHoursLeft.ToString("0.##")));
    }

    private void WriteResults() {
      Directory.CreateDirectory(Outputs);
      File.WriteAllText(Path.Combine(Outputs,"lategame-rocket-"+_mode+"-results.json"),JsonConvert.SerializeObject(new {
        mode=_mode,passed=_results.Count(r=>r.Status=="PASS"),failed=_results.Count(r=>r.Status=="FAIL"),
        skipped=_results.Count(r=>r.Status=="SKIP"),results=_results},Formatting.Indented));
    }
    private void Finish(bool complete) {
      _finished=true;_speed.ChangeSpeed(0);WriteResults();
      int passed=_results.Count(r=>r.Status=="PASS"),failed=_results.Count(r=>r.Status=="FAIL"),skipped=_results.Count(r=>r.Status=="SKIP");
      Debug.Log(Tag+" "+(complete?"COMPLETE":"INCOMPLETE")+" "+_mode.ToUpperInvariant()+" passed="+passed+" failed="+failed+" skipped="+skipped);
    }
  }

  internal static class Direction3DEnumeratorExtensions {
    public static IEnumerable<Direction3D> AsEnumerable(this Direction3DEnumerator enumerator) {
      var list=new List<Direction3D>();
      while(enumerator.MoveNext())list.Add(enumerator.Current);
      return list;
    }
  }
}
#endif
