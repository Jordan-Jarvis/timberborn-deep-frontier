#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using TimberPipes.Components;
using TimberPipes.Models;
using TimberPipes.Specs;
using Timberborn.Attractions;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockObjectTools;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.BuildingsNavigation;
using Timberborn.BuildingsReachability;
using Timberborn.BuildingStatuses;
using Timberborn.CameraSystem;
using Timberborn.CoreUI;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.Effects;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.Localization;
using Timberborn.MapIndexSystem;
using Timberborn.MechanicalSystem;
using Timberborn.NaturalResources;
using Timberborn.NeedSystem;
using Timberborn.SingletonSystem;
using Timberborn.SlotSystem;
using Timberborn.StatusSystem;
using Timberborn.Stockpiles;
using Timberborn.TemplateSystem;
using Timberborn.TerrainSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using Timberborn.Workshops;
using Timberborn.WorkSystem;
using UnityEngine;
using DeepFrontier.Scripts.Radiation;

namespace DeepFrontier.Scripts {
  // Explicit disposable test only: -deepFrontierLoadAcceptance -deepFrontierNewGame "user:<map>"
  // -deepFrontierAllBuildings [-deepFrontierAllBuildingsLabel <label>] (tools/start_all_buildings.ps1).
  [Context("Game")]
  public sealed class AllBuildingsAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      var args=Environment.GetCommandLineArgs();
      if(!args.Contains(AllBuildingsAcceptance.Flag))return;
      if(!args.Contains("-deepFrontierLoadAcceptance")||MemoryLoadProbe.NewGameMap()==null)
        throw new InvalidOperationException(AllBuildingsAcceptance.Flag+" requires -deepFrontierLoadAcceptance with -deepFrontierNewGame");
      Bind<AllBuildingsAcceptance>().AsSingleton();
    }
  }

  // Functional survey of every building Deep Frontier introduces (TemplateCollection.Buildings.IronTeeth),
  // the vanilla templates its blueprints patch, and vanilla references, on a new game. Buildings are
  // placed finished by native services on a cleared, levelled pad next to the starting district centre,
  // in batches that are removed again. Per building, as it applies:
  //   placement and registered occupancy; entrance reachable (district, unblocked access);
  //   unpowered: native NoPower status visible in the panel and as a floating icon; status icon height;
  //   with a worker but no inputs: the native missing-input status (LackOfResources);
  //   exactly one enabled Inventory, accepting the building's goods; Enterable open; native slot nodes;
  //   workplace accepts a worker; manufactory has a recipe and makes progress; power node joins a graph
  //   with the right demand (consumer) or supply (generator);
  //   Timber Pipes: tank -> powered pump -> pipe -> valve (Inlet on) against a generated side-face port,
  //   liquid arrives in the building's inventory;
  //   attraction usable and visited by beavers whose matching needs were lowered.
  // On a map with the sites of tools/all_buildings_sites.json (tools/create_all_buildings_sites_map.py),
  // the buildings that need a site run last in one sites batch on those sites (AllBuildingsSites.cs).
  // Results: outputs/all-buildings-<label>.json and "[DeepFrontier AllBuildings]" log lines. Individual
  // findings are recorded and the run continues; harness errors fail explicitly.
  internal sealed partial class AllBuildingsAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    internal const string Flag="-deepFrontierAllBuildings";
    private const string LabelFlag="-deepFrontierAllBuildingsLabel";
    private const string Tag="[DeepFrontier AllBuildings]";
    private static readonly string Root=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding");
    private static readonly string Outputs=Path.Combine(Root,"outputs");
    private static readonly string[] VanillaPatched={"GathererFlag.IronTeeth","PowerShaft.IronTeeth","VerticalPowerShaft.IronTeeth",
      "ImpermeablePowerShaft.IronTeeth","BotAssembler.IronTeeth"};
    private static readonly string[] VanillaReference={"Smelter.IronTeeth","MudBath.IronTeeth","DoubleShower.IronTeeth","SwimmingPool.IronTeeth",
      "Campfire.IronTeeth","LargeTank.IronTeeth","DeepWaterPump.IronTeeth"};
    // Tested first (user priority 2026-10-23): GoodConsuming and merged-pantry pipe targets, a Manufactory control.
    private static readonly string[] First={"Bathhouse.IronTeeth","Hospital.IronTeeth","Restaurant.IronTeeth","MudBath.IronTeeth","Smelter.IronTeeth"};
    // Specs whose native placement needs a site a dry flat pad cannot offer (water, map edge, seams,
    // understructure, terrain side). A rejected placement of these is SITE, not FAIL.
    private static readonly string[] SiteSpecs={"WaterInputSpec","WaterObstacleSpec","FinishableWaterObstacleSpec","FinishableHorizontalWaterObstacleSpec",
      "MapEdgeSiteSpec","WaterDepthWorkCellsSpec","UnderstructureConstraintSpec","ShoreFishingSpec","RadioactiveWaterSourceSpec","HydroTurbineSpec",
      "YieldRemovingBuildingSpec","MineralPitSpec","WaterSourceSpec"};
    private static readonly string[] BasicNeeds={"Hunger","Thirst","Sleep"};
    private const int Margin=2,PipeStrip=7,PadW=100,PadH=84,SearchRadius=70;
    private const float SettleHours=.5f,MissingInputHours=3.4f,WorkHours=10f,PipeHours=2f,AttractionHours=6f,NoPowerHours=.4f;

    private sealed class Check {public string Name,Status,Detail;}
    // Automatic kitchen (Restaurant, RestaurantKitchenChooser): two recipes' ingredients are stocked and
    // the kitchen must cook both, alternating by need, with no recipe ever set by the test; then one
    // recipe's ingredients are taken away and it must keep cooking the other.
    private sealed class KitchenRun {
      public RecipeSpec First,Second;
      public readonly List<string> Batches=new();
      public string Removed;public int BatchesAtRemoval=-1;public bool Done;
    }
    private sealed class Subject {
      public string Template,Kind,Batch;
      public Blueprint Blueprint;
      public BlockObjectSpec Spec;
      public BlockObject Building,EntrancePath;
      public readonly List<BlockObject> Attached=new();
      public readonly List<Check> Checks=new();
      public RectInt Allocation;
      public Vector3Int Anchor;
      public bool Placed,Powered,Seeded,Released;
      public Worker Worker;
      public float MaxProgress,MaxInput,MaxOutput;
      public bool Worked,Finished;
      public string PipeLiquid;public Vector3Int PipePort;public Direction3D PipeDirection;
      public BlockObject Valve,Tank;public int PipeBaseline;public bool PipeChecked;
      public readonly HashSet<Enterer> Visitors=new();public int MaxInside;
      public JObject Icon;
      public JObject Site;public Orientation Orientation=Orientation.Cw0;public int Produced;
      public int Reemployed;public float LastReemploy;public bool InputRechecked;public bool InputRetry;public bool Entered;public float AccessDistance=float.MaxValue;public readonly List<string> Refusals=new();
      public KitchenRun Kitchen;
      public MechanicalNode Node=>Building?Building.GetComponent<MechanicalNode>():null;
      public MechanicalNodeSpec NodeSpec=>Blueprint.HasSpec<MechanicalNodeSpec>()?Blueprint.GetSpec<MechanicalNodeSpec>():null;
      public bool IsConsumer=>NodeSpec!=null&&NodeSpec.PowerInput>0;
      public bool IsGenerator=>NodeSpec!=null&&NodeSpec.PowerOutput>0;
      public Workplace Workplace=>Building?Building.GetComponent<Workplace>():null;
      public Manufactory Manufactory=>Building?Building.GetComponent<Manufactory>():null;
      public bool IsAttraction=>Building&&Building.HasComponent<Attraction>();
      public bool HasPipes=>Blueprint.HasSpec<BuildingPipeTargetPortsSpec>();
      public string Id=>Template.EndsWith(".IronTeeth",StringComparison.Ordinal)?Template.Substring(0,Template.Length-10):Template;
    }

    private readonly EntityRegistry _entities;
    private readonly EntityService _entityService;
    private readonly TemplateService _templates;
    private readonly BlockObjectFactory _factory;
    private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _validation;
    private readonly IBlockService _blocks;
    private readonly ITerrainService _terrain;
    private readonly IThreadSafeWaterMap _water;
    private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock;
    private readonly WorkingHoursManager _hours;
    private readonly CameraService _camera;
    private readonly ILoc _loc;
    private readonly PanelStack _panels;
    private readonly IWaterService _waterService;
    private readonly IRadiationService _radiation;
    private readonly MapIndexService _indices;
    private readonly PreviewFactory _previews;
    // The build tool's cursor-to-placement picker (AllBuildingsSites.CursorPreview).
    private readonly Timberborn.BlockObjectPickingSystem.BlockObjectPreviewPicker _picker;
    private IPanelController _lastPanel;
    private int _panelFrames;
    private readonly string _label;
    private readonly List<Subject> _subjects=new();
    private readonly List<Subject> _batch=new();
    private readonly List<Subject> _wave=new();
    private readonly Queue<Subject> _waveQueue=new();
    private readonly List<Worker> _workers=new();
    private readonly List<BlockObject> _batchObjects=new();
    private readonly HashSet<Vector3Int> _network=new();
    private readonly List<string> _harness=new();
    private DistrictCenter _district;
    private BlockObjectSpec _path,_shaft,_generator,_station,_valve,_pipe,_pump,_tank,_platform;
    private RectInt _pad,_routeArea;
    private int _ground,_frame,_phase,_batchNumber;
    private float _phaseTime,_normalHours,_lastRefresh,_lastDay;
    private bool _finished,_started;
    private string _noPower,_lackOfResources,_notConnected;
    private DateTime _startedAt;

    public AllBuildingsAcceptance(EntityRegistry entities,EntityService entityService,TemplateService templates,BlockObjectFactory factory,
        BlockValidator validator,BlockObjectValidationService validation,IBlockService blocks,ITerrainService terrain,IThreadSafeWaterMap water,
        SpeedManager speed,IDayNightCycle clock,WorkingHoursManager hours,CameraService camera,ILoc loc,PanelStack panels,
        IWaterService waterService,IRadiationService radiation,MapIndexService indices,PreviewFactory previews,
        Timberborn.BlockObjectPickingSystem.BlockObjectPreviewPicker picker,
        // Contamination and weather consumer probes (AllBuildingsHazardProbes.cs).
        IEnumerable<Timberborn.Debugging.IDevModule> devModules,Timberborn.HazardousWeatherSystem.HazardousWeatherService hazardousWeather,
        Timberborn.WeatherSystem.WeatherService weather,Timberborn.GameCycleSystem.GameCycleService cycles) {
      _entities=entities;_entityService=entityService;_templates=templates;_factory=factory;_validator=validator;_validation=validation;
      _blocks=blocks;_terrain=terrain;_water=water;_speed=speed;_clock=clock;_hours=hours;_camera=camera;_loc=loc;_panels=panels;
      _waterService=waterService;_radiation=radiation;_indices=indices;_previews=previews;_picker=picker;
      _devModules=devModules;_hazardousWeather=hazardousWeather;_weather=weather;_cycles=cycles;
      var args=Environment.GetCommandLineArgs();
      int i=Array.IndexOf(args,LabelFlag);
      _label=i>=0&&i+1<args.Length?args[i+1].Trim('"'):"run";
      if(_label.IndexOfAny(Path.GetInvalidFileNameChars())>=0)throw new InvalidOperationException(LabelFlag+" is not a valid file name part: "+_label);
    }

    // ---------- recording ----------
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private void Record(Subject s,string check,bool ok,string detail)=>Add(s,check,ok?"PASS":"FAIL",detail);
    private void Skip(Subject s,string check,string reason)=>Add(s,check,"SKIP",reason);
    private void Add(Subject s,string check,string status,string detail) {
      s.Checks.Add(new Check{Name=check,Status=status,Detail=detail});
      var line=Tag+" "+status+" "+s.Id+" "+check+": "+detail;
      if(status=="FAIL")Debug.LogWarning(line);else Debug.Log(line);
    }
    private bool Guard(Subject s,string check,Action action) {
      try {action();return true;}
      catch(Exception error) {Record(s,check,false,"exception: "+error.GetType().Name+": "+error.Message);return false;}
    }

    // ---------- helpers ----------
    private TemplateSpec Template(string name)=>_templates.GetAll<TemplateSpec>().SingleOrDefault(t=>t.TemplateName==name);
    private BlockObjectSpec Spec(string name) {
      var t=Template(name);
      Require(t!=null,"Template not loaded: "+name);
      return t.Blueprint.GetSpec<BlockObjectSpec>();
    }
    private static Placement At(Vector3Int c,Orientation o=Orientation.Cw0)=>new(c,o,new FlipMode(false));
    private BlockObject Create(BlockObjectSpec spec,Placement p) {
      Require(_validator.BlocksValid(spec,p),"native placement rejected "+spec.Blueprint.Name+" at "+p.Coordinates+" "+p.Orientation);
      var b=_factory.CreateFinished(new EntitySetup.Builder(spec.Blueprint).AddInitComponent(new FinishedConstructionSiteInit()),p);
      if(!_validation.IsValid(b)) {
        _entityService.Delete(b.GetComponent<EntityComponent>());
        throw new InvalidOperationException("native object requirements rejected "+spec.Blueprint.Name+" at "+p.Coordinates);
      }
      _batchObjects.Add(b);
      return b;
    }
    private bool Free(BlockObjectSpec spec,Vector3Int c,Orientation o=Orientation.Cw0)=>_validator.BlocksValid(spec,At(c,o));
    private bool IsRoad(Vector3Int c)=>_blocks.GetObjectsAt(c).Any(b=>b.GetComponent<TemplateSpec>()?.TemplateName=="Path");
    private static readonly Orientation[] Rotations={Orientation.Cw0,Orientation.Cw90,Orientation.Cw180,Orientation.Cw270};
    private static Direction2D To2D(Direction3D d) {Require(d.IsHorizontal(),"Not a horizontal direction: "+d);return (Direction2D)(int)d;}
    private static Orientation Facing(Direction2D local,Direction2D wanted)=>Rotations.Single(o=>o.Transform(local)==wanted);
    private static HashSet<Vector3Int> Occupied(BlockObject b)=>new(b.PositionedBlocks.GetOccupiedBlocks().Select(k=>k.Coordinates));
    private static RectInt Bounds(BlockObjectSpec spec,Placement p) {
      var blocks=spec.GetBlocks(p).ToArray();
      int x0=blocks.Min(b=>b.Coordinates.x),y0=blocks.Min(b=>b.Coordinates.y);
      return new RectInt(x0,y0,blocks.Max(b=>b.Coordinates.x)-x0+1,blocks.Max(b=>b.Coordinates.y)-y0+1);
    }
    private float Hours=>(_clock.PartialDayNumber-_phaseTime)*24f;
    private void Phase(int phase,string name) {
      _phase=phase;_phaseTime=_clock.PartialDayNumber;_inputRecheck=false;_inputSnapshot=false;
      Debug.Log(Tag+" Phase "+phase+" "+name+" (batch "+_batchNumber+")");
    }
    private List<string> VisibleStatuses(BaseComponent b) {
      var subject=b.GetComponent<StatusSubject>();
      if(!subject)return new List<string>();
      return subject.ActiveStatuses.Where(s=>s.IsVisible()).Select(s=>s.StatusDescription+(s.IsPriorityStatus?" [priority]":"")+(s.ShowFloatingIcon?" [icon]":"")).ToList();
    }

    // ---------- lifecycle ----------
    public void PostLoad() {
      _speed.ChangeSpeed(0);
      _startedAt=DateTime.Now;
      _noPower=_loc.T("Status.Mechanical.NoPower");
      _lackOfResources=_loc.T("Status.Work.LackOfResources");
      _notConnected=_loc.T(PowerConnectionLoc.NotConnected);
    }

    public void UpdateSingleton() {
      if(_finished)return;
      try {
        // Startup panels are dismissed before frame 60 (AcceptanceStartupPanels).
        if(++_frame==90){Setup();_started=true;}
        if(!_started)return;
        DismissPanels();
        if(_probeFrame>0&&_frame>=_probeFrame)ProbeDeleted();
        // Work phases count working hours only: outside them (night, or a working-hours mod such as
        // Second Shift overriding WorkedPartOfDay) workers leave their workplace natively.
        float day=_clock.PartialDayNumber;
        if((_phase==3||_phase==6)&&!_hours.AreWorkingHours&&_lastDay>0)_phaseTime+=day-_lastDay;
        _lastDay=day;
        // Keep every beaver fed, watered and rested, so needs never pull a worker or visitor away.
        if((_clock.PartialDayNumber-_lastRefresh)*24f>3f){RefreshBeavers();_lastRefresh=_clock.PartialDayNumber;}
        if(_speed.CurrentSpeed<=0f&&_phase>0)_speed.ChangeSpeed(3);
        if(_siteBatch)SiteTick();
        if(_phase==2||_phase==3||_phase==6)foreach(var s in _wave)KeepWorker(s);
        foreach(var s in _wave)Observe(s);
        if(_current!=null)ObserveVisitors(_current);
        if(_phase>=4)foreach(var s in ServiceSubjects().Where(s=>s.Node!=null))
          {s.MaxInput=Math.Max(s.MaxInput,s.Node.Actuals.PowerInput);s.MaxOutput=Math.Max(s.MaxOutput,s.Node.Actuals.PowerOutput);}
        switch(_phase) {
          case 10: if(Hours>SiteFillDelayHours){FillSites();Phase(1,"unpowered settle");} break;
          case 11: if(_frame>=_reproFrame)DeleteConstructionRepro(); break;
          case 12: if(_frame>=_reproFrame){ProbeConstructionRepro();StartBatch();} break;
          case 1: if(Hours>SettleHours){foreach(var s in Placed())Guard(s,"unpowered snapshot",()=>Unpowered(s));
                    foreach(var s in Placed())Guard(s,"static checks",()=>StaticChecks(s));
                    foreach(var s in Placed())Guard(s,"roof deck",()=>RoofDeck(s));
                    // The sites batch builds on the side-platform decks only after the roof-deck probe has
                    // sampled the same slab cells empty (b173: built first, the probe found them taken).
                    if(_siteBatch)foreach(var s in Placed().Where(s=>s.Blueprint.HasSpec<AnchoredDeckSpec>()))Guard(s,"site: building on the deck",()=>BuildOnDeck(s));
                    if(_siteBatch)foreach(var s in Placed())Guard(s,"site snapshot",()=>SiteSnapshot(s));
                    foreach(var s in Placed().Where(s=>s.Workplace))Idle(s);
                    PrepareWaves();NextWave();} break;
          case 2: if(!_inputRecheck&&Hours>MissingInputHours-InputRecheckHours){_inputRecheck=true;foreach(var s in _wave)RecheckInputs(s);}
                  // A missing status is re-checked once more after another native worker event (b175: the
                  // quarries' Water stock or the district changed inside the first window).
                  if(!_inputSnapshot&&Hours>MissingInputHours){_inputSnapshot=true;foreach(var s in _wave)Guard(s,"missing-input snapshot",()=>MissingInputs(s,false));}
                  if(_inputSnapshot&&Hours>MissingInputHours+(_wave.Any(s=>s.InputRetry)?InputRetryHours:0f)){
                    foreach(var s in _wave.Where(s=>s.InputRetry))Guard(s,"missing-input snapshot",()=>MissingInputs(s,true));
                    foreach(var s in _wave)Guard(s,"supply without power",()=>SupplyUnpowered(s));Phase(6,"wave supplied, unpowered");} break;
          case 6: foreach(var s in _wave.Where(s=>s.Valve&&!s.PipeChecked&&Hours>PipeHours))Guard(s,"pipe liquid arrives",()=>CheckPipeArrival(s));
                  if(Hours>PipeHours+NoPowerHours){foreach(var s in _wave)Guard(s,"supplied unpowered snapshot",()=>SuppliedUnpowered(s));
                    foreach(var s in _wave)Guard(s,"power",()=>AttachPower(s));Phase(3,"working");} break;
          case 3: foreach(var s in _wave.Where(s=>s.Valve&&!s.PipeChecked&&Hours>PipeHours))Guard(s,"pipe liquid arrives",()=>CheckPipeArrival(s));
                  if(_wave.All(s=>(s.Finished||!s.Worker||!s.Manufactory)&&(!s.Valve||s.PipeChecked))||Hours>WorkHours){EvaluateWave();NextWave();} break;
          case 4: foreach(var s in ServiceSubjects().Where(s=>s.Valve&&!s.PipeChecked&&Hours>PipeHours))Guard(s,"pipe liquid arrives",()=>CheckPipeArrival(s));
                  if(Hours>PipeHours+NoPowerHours){foreach(var s in ServiceSubjects())Guard(s,"supplied unpowered snapshot",()=>SuppliedUnpowered(s));
                    foreach(var s in ServiceSubjects())Guard(s,"power",()=>AttachPower(s));Phase(7,"services powered");} break;
          case 7: if(Hours>.3f){StartAttractions();} break;
          case 9: if(Inside()==0&&Hours>.1f||Hours>3f)DeleteBatch(); break;
          case 5: if(_current==null||_current.Visitors.Count>0||Hours>AttractionHours){if(_current!=null)EvaluateAttraction(_current);
                    if(!NextAttraction()){EvaluateServices();EndBatch();}} break;
          case ProbePhase: ProbeTick(); break;
        }
        if(_frame%1800==0)Debug.Log(Tag+" STATUS phase="+_phase+" batch="+_batchNumber+" hours="+Hours.ToString("0.0")+" wave="+
          string.Join(",",_wave.Select(s=>s.Id+(s.Worked?"(worked)":"")+" progress="+s.MaxProgress.ToString("0.00")+WorkerState(s))));
      } catch(Exception error) {
        _finished=true;_speed.ChangeSpeed(0);
        _harness.Add("FAILED: "+error);
        if(_normalHours>0)_hours.WorkedPartOfDay=_normalHours;
        WriteResults(false);
        Debug.LogError(Tag+" FAILED: "+error);
      }
    }

    // A panel opened during the run (Frontier Journal discoveries, notifications) locks the game
    // speed (OverlayPanelSpeedLocker); it is closed as the native Escape key does and recorded.
    private void DismissPanels() {
      var stacked=AcceptancePanels.Stacked(_panels);
      if(stacked.Count==0){_lastPanel=null;_panelFrames=0;return;}
      var top=stacked[0];
      if(ReferenceEquals(top,_lastPanel)) {
        if(++_panelFrames>120)throw new InvalidOperationException("Panel did not close on Escape: "+AcceptancePanels.Describe(top));
        return;
      }
      _lastPanel=top;_panelFrames=0;
      var description=AcceptancePanels.Describe(top);
      top.OnUICancelled();
      _harness.Add("dismissed panel: "+description);
      Debug.Log(Tag+" dismissed panel with native Escape: "+description);
    }

    private static string WorkerState(Subject s) {
      var w=s.Worker;
      if(!w)return "";
      var manager=w.GetComponent<Timberborn.BehaviorSystem.BehaviorManager>();
      return " [worker employed="+(w.Workplace==s.Workplace)+" behavior="+manager.RunningBehavior.Name+" executor="+manager.RunningExecutor.Name+
        " d="+Vector3.Distance(w.Transform.position,s.Building.Transform.position).ToString("0")+"]";
    }

    // ---------- setup ----------
    private void Setup() {
      _path=Spec("Path");_shaft=Spec("PowerShaft.IronTeeth");_generator=Spec("DevPowerGenerator");_station=Spec("ChargingStation.IronTeeth");
      _valve=Spec("HorizontalPipeValve.IronTeeth");_pipe=Spec("HorizontalPipe.IronTeeth");_pump=Spec("HorizontalPipePump.IronTeeth");
      _tank=Spec("MediumTank.IronTeeth");_platform=Spec("Platform.IronTeeth");
      var centres=_entities.Entities.Select(e=>e.GetComponent<DistrictCenter>()).Where(d=>d).ToList();
      Require(centres.Count==1,"A new game must have exactly one district centre, found "+centres.Count);
      _district=centres[0];
      var dc=_district.GetComponent<BlockObject>();
      Require(dc.HasEntrance,"District centre has no entrance");
      _ground=dc.Coordinates.z;
      // Adults only: a child carries a Worker but cannot work, so an employed child just wanders.
      var beaverWorkers=_entities.Entities.Select(e=>e.GetComponent<Worker>()).Where(w=>w&&w.WorkerType=="Beaver").ToList();
      _workers.AddRange(beaverWorkers.Where(w=>!w.GetComponent<Timberborn.Beavers.Child>()));
      Debug.Log(Tag+" workers: "+_workers.Count+" adults of "+beaverWorkers.Count+" beaver Worker components");
      Require(_workers.Count>=2,"The new game needs at least two adult beaver workers, found "+_workers.Count);
      _normalHours=_hours.WorkedPartOfDay;_hours.WorkedPartOfDay=1;
      LoadSites();
      ChoosePad(dc);
      PreparePad();
      ResolveSubjects();
      Debug.Log(Tag+" START label="+_label+" subjects="+_subjects.Count+" workers="+_workers.Count+" pad="+_pad+" ground="+_ground);
      _camera.MoveTargetTo(new Vector3(_pad.center.x,_ground,_pad.center.y));_camera.SetZoomLevel(38,0);
      StartConstructionRepro();
    }

    // A dry pad of PadW x PadH next to the district centre whose terrain is within one layer of the
    // centre's ground and that holds only natural resources, blockages or ruins.
    private void ChoosePad(BlockObject dc) {
      var dcBounds=Bounds(dc.GetComponent<BlockObjectSpec>(),dc.Placement);
      var candidates=new List<RectInt>();
      for(int dx=-SearchRadius;dx<=SearchRadius;dx+=4)for(int dy=-SearchRadius;dy<=SearchRadius;dy+=4)
        candidates.Add(new RectInt(dcBounds.center.x.Round()+dx-PadW/2,dcBounds.center.y.Round()+dy-PadH/2,PadW,PadH));
      var size=_terrain.Size;
      foreach(var r in candidates.OrderBy(r=>(r.center-dcBounds.center).sqrMagnitude)) {
        if(r.xMin<2||r.yMin<2||r.xMax>size.x-2||r.yMax>size.y-2)continue;
        var gap=new RectInt(dcBounds.xMin-3,dcBounds.yMin-3,dcBounds.width+6,dcBounds.height+6);
        if(r.Overlaps(gap))continue;
        int x0=Math.Min(r.xMin,dcBounds.xMin-3),y0=Math.Min(r.yMin,dcBounds.yMin-3);
        int x1=Math.Max(r.xMax,dcBounds.xMax+3),y1=Math.Max(r.yMax,dcBounds.yMax+3);
        var route=new RectInt(x0,y0,x1-x0,y1-y0);
        // The pad and the corridor it levels must not touch the prepared sites.
        if(_sitesAvailable&&route.Overlaps(_siteZone))continue;
        if(!PadUsable(r))continue;
        _pad=r;_routeArea=route;
        return;
      }
      throw new InvalidOperationException("No dry "+PadW+"x"+PadH+" pad within "+SearchRadius+" cells of the district centre at "+dc.Coordinates);
    }
    private bool PadUsable(RectInt r) {
      for(int x=r.xMin;x<r.xMax;x++)for(int y=r.yMin;y<r.yMax;y++) {
        int h=_terrain.GetTerrainHeight(new Vector3Int(x,y,0));
        if(Math.Abs(h-_ground)>1)return false;
        if(_water.WaterDepth(new Vector3Int(x,y,h))>0)return false;
        foreach(var b in _blocks.GetObjectsAt(new Vector3Int(x,y,h)).Concat(_blocks.GetObjectsAt(new Vector3Int(x,y,h-1)))) {
          if(!Clearable(b.GetComponent<EntityComponent>()))return false;
        }
      }
      return true;
    }
    private static bool Clearable(EntityComponent e) {
      if(e.HasComponent<NaturalResource>())return true;
      var t=e.GetComponent<TemplateSpec>()?.TemplateName??"";
      return t=="Blockage"||t.StartsWith("RuinColumn",StringComparison.Ordinal)||t.StartsWith("Ruin",StringComparison.Ordinal);
    }
    // Clears and levels the pad and the corridor to the district centre (cells without other objects).
    private void PreparePad() {
      var doomed=new HashSet<EntityComponent>();
      foreach(var e in _entities.Entities.ToList()) {
        var b=e.GetComponent<BlockObject>();
        if(!b||!b.Positioned||!Clearable(e))continue;
        if(b.PositionedBlocks.GetAllBlocks().Any(k=>_routeArea.Contains(new Vector2Int(k.Coordinates.x,k.Coordinates.y))))doomed.Add(e);
      }
      foreach(var e in doomed)_entityService.Delete(e);
      int levelled=0;
      for(int x=_routeArea.xMin;x<_routeArea.xMax;x++)for(int y=_routeArea.yMin;y<_routeArea.yMax;y++) {
        var cell=new Vector2Int(x,y);
        int h=_terrain.GetTerrainHeight(new Vector3Int(x,y,0));
        // Natural objects deleted above may stay registered until the end of the frame.
        if(_blocks.GetObjectsAt(new Vector3Int(x,y,h)).Concat(_blocks.GetObjectsAt(new Vector3Int(x,y,_ground)))
            .Any(b=>!Clearable(b.GetComponent<EntityComponent>())))continue;
        if(_water.WaterDepth(new Vector3Int(x,y,h))>0){if(_pad.Contains(cell))throw new InvalidOperationException("Pad cell is wet at "+cell);continue;}
        var surfaces=_terrain.GetAllHeightsInCell(cell).Where(c=>c.z>_ground).OrderByDescending(c=>c.z).ToArray();
        foreach(var top in surfaces)_terrain.UnsetTerrain(new Vector3Int(x,y,top.z-1),top.z-_ground);
        h=_terrain.GetTerrainHeight(new Vector3Int(x,y,0));
        if(h<_ground)_terrain.SetTerrain(new Vector3Int(x,y,h),_ground-h);
        if(_pad.Contains(cell))Require(_terrain.GetTerrainHeight(new Vector3Int(x,y,0))==_ground,"Pad not level at "+cell);
        levelled++;
      }
      Debug.Log(Tag+" pad "+_pad+" cleared of "+doomed.Count+" natural objects; "+levelled+" cells levelled to "+_ground+" in "+_routeArea);
    }

    private void ResolveSubjects() {
      var collection=JObject.Parse(File.ReadAllText(Path.Combine(Root,"src","DeepFrontier","Data","TemplateCollections","TemplateCollection.Buildings.IronTeeth.blueprint.json")));
      var paths=collection["TemplateCollectionSpec"]?["Blueprints#append"]?.ToObject<string[]>();
      Require(paths!=null&&paths.Length>0,"TemplateCollection.Buildings.IronTeeth lists no blueprints");
      var names=new List<(string Name,string Kind)>();
      names.AddRange(paths.Select(p=>(Path.GetFileName(p).Replace(".blueprint",""),"DeepFrontier")));
      names.AddRange(VanillaPatched.Select(n=>(n,"VanillaPatched")));
      names.AddRange(VanillaReference.Select(n=>(n,"VanillaReference")));
      foreach(var (name,kind) in names) {
        var t=Template(name);
        var s=new Subject{Template=name,Kind=kind};
        _subjects.Add(s);
        if(t==null){Record(s,"template loaded",false,"no "+name+" template in the game context");continue;}
        s.Blueprint=t.Blueprint;s.Spec=t.Blueprint.GetSpec<BlockObjectSpec>();
        if(t.Blueprint.Specs.Any(c=>c.GetType().Name=="RadioactiveWaterSourceSpec"))
          Skip(s,"placement","map-authored radioactive spring: placing it would contaminate the shared test pad");
      }
      AssignSites();
      // Priority subjects first, then the largest footprints (they pack first). Subjects with a prepared
      // site run in the sites batch instead.
      var order=_subjects.Where(s=>s.Spec!=null&&s.Site==null&&!s.Checks.Any(c=>c.Name=="placement")).OrderBy(s=>{int i=Array.IndexOf(First,s.Template);return i<0?99:i;})
        .ThenByDescending(s=>s.Spec.Size.x*s.Spec.Size.y).ToList();
      _pending.Clear();foreach(var s in order)_pending.Enqueue(s);
    }
    private readonly Queue<Subject> _pending=new();

    // ---------- batches ----------
    private IEnumerable<Subject> Placed()=>_batch.Where(s=>s.Placed);
    private void StartBatch() {
      _siteBatch=false;
      _batch.Clear();_batchObjects.Clear();_network.Clear();_batchNumber++;
      var allocated=new List<RectInt>();
      var deferred=new List<Subject>();
      while(_pending.Count>0) {
        var s=_pending.Dequeue();
        var probe=Bounds(s.Spec,At(Vector3Int.zero));
        int north=s.HasPipes?PipeStrip:0;
        bool done=false;
        for(int y=_pad.yMin+Margin;y+probe.height+Margin+north<=_pad.yMax&&!done;y++)
          for(int x=_pad.xMin+Margin;x+probe.width+Margin<=_pad.xMax&&!done;x++) {
            var rect=new RectInt(x-Margin,y-Margin,probe.width+2*Margin,probe.height+2*Margin+north);
            if(allocated.Any(a=>a.Overlaps(rect)))continue;
            s.Allocation=rect;s.Anchor=new Vector3Int(x-probe.xMin,y-probe.yMin,_ground-s.Spec.BaseZ);allocated.Add(rect);done=true;
          }
        if(done){s.Batch="batch "+_batchNumber;_batch.Add(s);}
        else if(_batch.Count==0)Record(s,"placement",false,"footprint "+probe.width+"x"+probe.height+" does not fit the "+PadW+"x"+PadH+" pad");
        else deferred.Add(s);
        if(_batch.Count>=16)break;
      }
      foreach(var s in deferred)_pending.Enqueue(s);
      if(_batch.Count==0) {
        if(_sitesAvailable&&!_siteDone&&_siteSubjects.Count>0){_batchNumber--;StartSiteBatch();return;}
        // Contamination and weather consumer probes (AllBuildingsHazardProbes.cs), then the results.
        if(StartProbes()){_batchNumber--;return;}
        Finish();return;
      }
      Debug.Log(Tag+" BATCH "+_batchNumber+": "+string.Join(", ",_batch.Select(s=>s.Id)));
      foreach(var s in _batch)Guard(s,"placement",()=>Place(s));
      foreach(var s in Placed())Guard(s,"entrance path",()=>PlaceEntrancePath(s));
      RouteAll();
      foreach(var s in Placed().Where(s=>s.Manufactory))Guard(s,"recipe",()=>ChooseRecipe(s));
      _speed.ChangeSpeed(3);
      Phase(1,"unpowered settle");
    }
    // A beaver inside a building that is deleted is left in a broken behavior state (observed in
    // builds 154-158: workers of earlier batches never decided again). The batch is emptied first:
    // workplaces paused (workers released) and every attraction blocked, then the run waits until
    // no beaver is inside any batch building before deleting it.
    private void EndBatch() {
      if(_siteBatch)SiteEndChecks();
      foreach(var s in _batch.Where(s=>s.Placed&&s.Workplace))Idle(s);
      foreach(var s in _batch.Where(s=>s.Placed)) {
        var blockable=s.Building.GetComponent<BlockableObject>();
        if(blockable&&blockable.IsUnblocked)blockable.Block(this);
      }
      Phase(9,"emptying batch");
    }
    private int Inside()=>_batch.Where(s=>s.Placed&&s.Building).Sum(s=>s.Building.GetComponent<Enterable>()?.NumberOfEnterersInside??0);
    private void DeleteBatch() {
      RememberDeleted();
      int inside=Inside();
      if(inside>0)_harness.Add("batch "+_batchNumber+": "+inside+" beavers still inside after "+Hours.ToString("0.0")+" h; deleting anyway");
      foreach(var b in _batchObjects.Where(b=>b).ToList()) {
        var e=b.GetComponent<EntityComponent>();
        if(e)_entityService.Delete(e);
      }
      _batchObjects.Clear();
      WriteResults(false);
      StartBatch();
    }

    private void Place(Subject s) {
      var p=At(s.Anchor,s.Orientation);
      if(s.Site!=null&&_siteBatch){PlaceOnSite(s,p);return;}
      bool site=s.Blueprint.Specs.Any(c=>SiteSpecs.Contains(c.GetType().Name)||c.GetType().Name.StartsWith("Water",StringComparison.Ordinal))||
        s.Blueprint.HasSpec<PlaceableBlockObjectSpec>()&&s.Blueprint.GetSpec<PlaceableBlockObjectSpec>().CanBeAttachedToTerrainSide;
      if(!_validator.BlocksValid(s.Spec,p)) {
        if(site){Add(s,"placement","SITE","native validator rejects a dry flat pad (site-specific building: "+
          string.Join("/",s.Blueprint.Specs.Select(c=>c.GetType().Name).Where(n=>SiteSpecs.Contains(n)||n.StartsWith("Water",StringComparison.Ordinal)))+")");return;}
        if(s.Spec.BaseZ>0){Add(s,"placement","SITE","native validator rejects a flat pad for a raised base (BaseZ "+s.Spec.BaseZ+": a terrain step or water below)");return;}
        Record(s,"placement",false,"native BlockValidator rejected flat pad at "+p.Coordinates);return;
      }
      try {s.Building=Create(s.Spec,p);}
      catch(Exception error) {
        if(site){Add(s,"placement","SITE",error.Message+" (site-specific building)");return;}
        throw;
      }
      s.Placed=true;
      var expected=s.Spec.GetBlocks(s.Building.Placement).Where(k=>k.IsOccupied).Select(k=>k.Coordinates).ToList();
      Record(s,"placement",Occupied(s.Building).SetEquals(expected)&&expected.All(c=>_blocks.GetObjectsAt(c).Contains(s.Building)),
        "finished at "+s.Building.Coordinates+"; "+expected.Count+" occupied cells registered");
    }
    private void PlaceEntrancePath(Subject s) {
      if(!s.Building.HasEntrance)return;
      var c=s.Building.PositionedEntrance.Coordinates;
      if(c.z==_ground+1) {
        // Raised entrance (vanilla MudBath): native Platform with a Path on top, and native Stairs up to
        // it from the pad, as the civic acceptance fixtures build them.
        var e=s.Building.PositionedEntrance;
        var outward=e.Direction2D.ToOffset();
        var below=new Vector3Int(c.x,c.y,_ground);
        var stairs=below+new Vector3Int(outward.x,outward.y,0);
        var foot=stairs+new Vector3Int(outward.x,outward.y,0);
        var climb=Facing(Direction2D.Down,e.Direction2D.Across());
        Create(_platform,At(below));Create(_path,At(c));Create(Spec("Stairs.IronTeeth"),At(stairs,climb));
        s.EntrancePath=IsRoad(foot)?_blocks.GetObjectsAt(foot).First(b=>b.GetComponent<TemplateSpec>()?.TemplateName=="Path"):Create(_path,At(foot));
        Record(s,"raised entrance path",true,"Platform and Path at "+c+", Stairs at "+stairs+", path foot "+foot);
        return;
      }
      if(c.z!=_ground){Skip(s,"entrance path","entrance "+c+" is not on the pad layer");return;}
      if(IsRoad(c)){s.EntrancePath=_blocks.GetObjectsAt(c).First(b=>b.GetComponent<TemplateSpec>()?.TemplateName=="Path");return;}
      // A player reaches a building with an ordinary Path on its native Entrance cell, as in vanilla
      // (tools/native_entrance.mjs, validate_building_entrances.mjs). No special access is built: an
      // Entrance on the building's own block (FisheryWorks and FishHatchery before 2026-10-26) fails.
      if(_blocks.GetObjectsAt(c).Contains(s.Building)){Record(s,"entrance takes a plain player Path",false,"entrance "+c+" is the building's own block: a player's Path cannot be laid there");return;}
      if(!Free(_path,c)){Record(s,"entrance takes a plain player Path",false,"native Path rejected at entrance "+c);return;}
      s.EntrancePath=Create(_path,At(c));
      Record(s,"entrance takes a plain player Path",true,"native Path on the entrance "+c+" in front of the doorstep "+s.Building.PositionedEntrance.DoorstepCoordinates);
    }
    private void RouteAll() {
      var start=_district.GetComponent<BlockObject>().PositionedEntrance.Coordinates;
      if(!IsRoad(start)) {
        Require(Free(_path,start),"No path at the district centre entrance "+start+" and none can be placed");
        _factory.CreateFinished(new EntitySetup.Builder(_path.Blueprint).AddInitComponent(new FinishedConstructionSiteInit()),At(start));
      }
      _network.Add(start);
      foreach(var s in Placed().Where(s=>s.EntrancePath).OrderBy(s=>Vector3Int.Distance(s.EntrancePath.Coordinates,start)).ToList()) {
        var route=Route(s.EntrancePath.Coordinates);
        if(route==null){Record(s,"road route",false,"no native Path route from the entrance to the district centre");continue;}
        foreach(var c in route)if(!IsRoad(c))Create(_path,At(c));
        foreach(var c in route)_network.Add(c);
      }
    }
    private List<Vector3Int> Route(Vector3Int from) {
      var parent=new Dictionary<Vector3Int,Vector3Int>{[from]=from};
      var queue=new Queue<Vector3Int>();queue.Enqueue(from);
      while(queue.Count>0) {
        var c=queue.Dequeue();
        if(c!=from&&_network.Contains(c)) {
          var route=new List<Vector3Int>();
          for(var p=c;p!=from;p=parent[p])route.Add(p);
          route.Add(from);return route;
        }
        foreach(var d in new[]{Vector3Int.left,Vector3Int.right,Vector3Int.up,Vector3Int.down}) {
          var n=c+d;
          if(parent.ContainsKey(n)||!_routeArea.Contains(new Vector2Int(n.x,n.y)))continue;
          if(!(IsRoad(n)||Free(_path,n)))continue;
          // Keep each building's pipe strip free.
          if(_batch.Any(s=>s.Placed&&s.HasPipes&&InPipeStrip(s,n)))continue;
          parent[n]=c;queue.Enqueue(n);
        }
      }
      return null;
    }
    private bool InPipeStrip(Subject s,Vector3Int c) {
      var r=Bounds(s.Spec,s.Building.Placement);
      return c.x>=r.xMin&&c.x<r.xMax&&c.y>=r.yMax&&c.y<r.yMax+PipeStrip-1;
    }
    private void ChooseRecipe(Subject s) {
      var m=s.Manufactory;
      if(s.Template=="BotAssembler.IronTeeth")Record(s,"patched recipe IndustrialBot present",m.ProductionRecipes.Any(r=>r.Id=="IndustrialBot"),
        "recipes "+string.Join(",",m.ProductionRecipes.Select(r=>r.Id)));
      Record(s,"manufactory has recipes",m.ProductionRecipes.Length>0,m.ProductionRecipes.Length+" recipes: "+string.Join(",",m.ProductionRecipes.Select(r=>r.Id)));
      if(m.ProductionRecipes.Length==0)return;
      if(s.Building.GetComponent<AutomaticRecipeManufactory>()) {
        Record(s,"automatic kitchen: native recipe picker hidden",s.Building.GetComponent<RestaurantKitchenChooser>()!=null,
          "AutomaticRecipeManufactory present (native ManufactoryFragment hides the picker); chooser "+(s.Building.GetComponent<RestaurantKitchenChooser>()!=null));
        return;
      }
      if(!m.HasCurrentRecipe)m.SetRecipe(m.ProductionRecipes.First());
    }
    // Native Workplace.DecreaseDesiredWorkers stops at 1 (1.1.2.8), so a workplace is idled by the
    // native pause (PausableBuilding releases its workers) and resumed for its wave.
    private void Idle(Subject s) {
      var w=s.Workplace;
      foreach(var worker in w.AssignedWorkers.ToList())worker.Unemploy();
      var pausable=s.Building.GetComponent<PausableBuilding>();
      if(pausable&&!pausable.Paused)pausable.Pause();
    }

    // ---------- unpowered snapshot and static checks ----------
    private void Unpowered(Subject s) {
      var statuses=VisibleStatuses(s.Building);
      var subject=s.Building.GetComponent<StatusSubject>();
      var cycler=s.Building.GetComponent<StatusIconCycler>();
      if(s.IsConsumer) {
        // Moddable Timberborn 11.1.3 (required) reports a graph with zero demand as powered, so an
        // idle, unsupplied consumer shows no NoPower; recorded for reference, asserted when supplied.
        Add(s,"unpowered idle: statuses","INFO",(statuses.Any(t=>t.StartsWith(_noPower,StringComparison.Ordinal))?"NoPower shown; ":"no NoPower; ")+
          "visible ["+string.Join("; ",statuses)+"]"+(subject&&subject.InPriorityMode?" (priority mode)":"")+PowerDiagnostics(s));
        // Deep Frontier's own status (Scripts/PowerConnectionStatus.cs): shown on an idle, unconnected consumer.
        bool notConnected=statuses.Any(t=>t.StartsWith(_notConnected,StringComparison.Ordinal));
        bool icon=notConnected&&statuses.Any(t=>t.StartsWith(_notConnected,StringComparison.Ordinal)&&t.Contains("[icon]"))&&cycler&&cycler.VisibleAndActive;
        if(s.Blueprint.Specs.Any(c=>c.GetType().Name=="PowerConnectionStatusSpec")) {
          Record(s,"unconnected: 'Not connected to a power source' in panel",notConnected,"visible ["+string.Join("; ",statuses)+"]");
          Record(s,"unconnected: 'Not connected' floating icon",icon,"StatusIconCycler.VisibleAndActive="+(cycler&&cycler.VisibleAndActive));
        } else if(s.Kind!="DeepFrontier")Record(s,"vanilla: no Deep Frontier power status",!notConnected,"visible ["+string.Join("; ",statuses)+"]");
        else Record(s,"unconnected: 'Not connected to a power source' in panel",false,"Deep Frontier consumer without PowerConnectionStatusSpec");
      }
      var offsetter=s.Building.GetComponent<BuildingStatusIconOffsetter>();
      if(offsetter) {
        var occupied=s.Building.PositionedBlocks.GetOccupiedBlocks().Select(b=>b.Coordinates).ToList();
        int baseZ=s.Building.Coordinates.z;
        int top=occupied.Max(c=>c.z)+1-baseZ;
        var perLayer=occupied.GroupBy(c=>c.z).ToDictionary(g=>g.Key,g=>g.Count());
        int widest=perLayer.Values.Max();
        int mainRoof=perLayer.Where(kv=>kv.Value>=.3f*widest).Max(kv=>kv.Key)+1-baseZ;
        float icon=offsetter.FinishedTopBound-baseZ;
        s.Icon=new JObject{["iconHeight"]=Math.Round(icon,2),["occupiedTop"]=top,["mainRoof"]=mainRoof,["aboveMainRoof"]=Math.Round(icon-mainRoof,2)};
        Add(s,"status icon height","INFO","icon at "+icon.ToString("0.0")+" layers above base; occupied top "+top+"; main roof "+mainRoof+
          " ("+(icon-mainRoof).ToString("0.0")+" above the main roof)");
        var anchor=s.Building.GetComponent<StatusIconAnchorSpec>();
        if(anchor!=null) {
          s.Icon["anchor"]=anchor.Height;
          Record(s,"status icon anchored",icon<=anchor.Height+.01f&&icon>0f,"icon "+icon.ToString("0.00")+" layers above layer 0, anchor "+anchor.Height.ToString("0.00"));
        } else if(s.Kind=="DeepFrontier")Record(s,"status icon anchored",false,"Deep Frontier building without StatusIconAnchorSpec");
      }
    }
    // Platformable flat roofs (tools/roof_decks.json, tools/roof_deck_content.mjs): on up to
    // three listed roof cells (first, middle, last), the native BlockValidator accepts a Path,
    // a 1x1 decoration (FreedCellProbe: Shrub or Brazier) and a Platform in the cell above.
    private JObject _roofDecks;
    private void RoofDeck(Subject s) {
      _roofDecks??=(JObject)JObject.Parse(File.ReadAllText(Path.Combine(Root,"tools","roof_decks.json")))["buildings"];
      var cells=(_roofDecks[s.Id]?["platformable"] as JArray)?.Select(c=>new Vector3Int((int)c[0],(int)c[1],(int)c[2])).ToList();
      if(cells==null||cells.Count==0)return;
      // Cells above the roof that this test's own fixtures already hold (the sites batch's divider dam rests
      // on the hydro turbine's roof, b173) are left out of the samples and reported.
      var held=cells.Where(c=>_blocks.GetObjectsAt(s.Building.TransformCoordinates(c+new Vector3Int(0,0,1))).Any(o=>o!=s.Building)).ToList();
      var free=cells.Except(held).ToList();
      if(free.Count==0){Skip(s,"roof deck takes a Path, a 1x1 decoration and a Platform","all "+cells.Count+" platformable roof cells hold this test's fixtures");return;}
      if(held.Count>0)Add(s,"roof deck fixtures","INFO",held.Count+" of "+cells.Count+" platformable roof cells hold this test's fixtures and are not sampled: "+
        string.Join(" ",held.Take(6).Select(c=>c+" ("+_blocks.GetObjectsAt(s.Building.TransformCoordinates(c+new Vector3Int(0,0,1))).First(o=>o!=s.Building).GetComponent<TemplateSpec>()?.TemplateName+")")));
      cells=free;
      var samples=new[]{cells[0],cells[cells.Count/2],cells[cells.Count-1]}.Distinct().Select(c=>c+new Vector3Int(0,0,1)).ToList();
      var failures=FreedCellProbe.Check(_templates,_validator,s.Building,samples,out var accepted);
      var platform=samples.Where(c=>!_validator.BlocksValid(_platform,At(s.Building.TransformCoordinates(c)))).ToList();
      Record(s,"roof deck takes a Path, a 1x1 decoration and a Platform",failures.Count==0&&platform.Count==0,
        cells.Count+" platformable roof cells; samples above "+string.Join(" ",samples)+": "+
        (failures.Count==0?"Path and decoration fit ("+accepted+")":string.Join("; ",failures))+
        (platform.Count==0?"; Platform fits":"; Platform rejected at "+string.Join(" ",platform)));
    }
    private void StaticChecks(Subject s) {
      var b=s.Building;
      var inventories=b.GetComponent<Inventories>();
      if(inventories&&inventories.AllInventories.Any(i=>i.ComponentName!="ConstructionSite")) {
        var listed=inventories.EnabledInventories.Where(i=>i.ComponentName!="ConstructionSite").ToList();
        var enabled=listed.Distinct().ToList();
        Record(s,"exactly one enabled inventory",enabled.Count==1,enabled.Count+" enabled: "+string.Join(", ",enabled.Select(i=>i.ComponentName+"(in "+
          Goods(i.InputGoods)+"; out "+Goods(i.OutputGoods)+"; capacity "+i.Capacity+")")));
        // Moddable Recipes 11.0.0 ManufactoryPatches.InitInventoryForRecipe (SetRecipe prefix) calls
        // Inventory.Disable()/Enable() before the native finished-state Enable of a single-recipe
        // manufactory; native Inventory.Enable is unguarded, so without InventoryEnableGuard the
        // inventory is listed (and registered with the district) twice.
        Record(s,"enabled inventory listed once",listed.Count==enabled.Count,listed.Count+" EnabledInventories entries for "+enabled.Count+
          " inventory (InventoryEnableGuard skipped "+InventoryEnableGuard.Skipped+" repeated Enable calls so far)");
        if(enabled.Count==1)Guard(s,"inventory accepts goods",()=>AcceptsGoods(s,enabled[0]));
        // Native DistrictInventoryPicker.InventoryIsTaking reads IInventoryValidator and BlockableObject of
        // every public inventory a hauler or emptying worker considers (b163: the Grocery had no Emptiable).
        foreach(var i in inventories.AllInventories.Where(i=>i.ComponentName!="ConstructionSite"&&(i.PublicInput||i.PublicOutput)))
          Record(s,"public inventory meets the native picker contract",i.GetComponent<IInventoryValidator>()!=null&&i.GetComponent<BlockableObject>(),
            i.ComponentName+": IInventoryValidator "+(i.GetComponent<IInventoryValidator>()!=null?"present":"missing")+", BlockableObject "+(i.GetComponent<BlockableObject>()?"present":"missing"));
      }
      var enterable=b.GetComponent<Enterable>();
      if(enterable)Record(s,"enterable open",enterable.Enabled,
        "enabled="+enterable.Enabled+" canReserve="+enterable.CanReserveSlot+" capacity="+enterable.Capacity);
      // TransformSlotInitializerSpec is internal to Timberborn.SlotSystem (1.1.2.8): read its keywords by reflection.
      var slotSpec=s.Blueprint.Specs.SingleOrDefault(c=>c.GetType().Name=="TransformSlotInitializerSpec");
      if(slotSpec!=null) {
        var all=b.GameObject.GetComponentsInChildren<Transform>(true);
        var slots=(System.Collections.IEnumerable)(slotSpec.GetType().GetProperty("Slots")?.GetValue(slotSpec)
          ??throw new InvalidOperationException("TransformSlotInitializerSpec.Slots not found; recheck the 1.1.2.8 contract"));
        foreach(var slot in slots.Cast<TransformSlotSpec>()) {
          int n=all.Count(t=>t.name.StartsWith("#Slot#"+slot.SlotKeyword,StringComparison.Ordinal));
          bool fixedSlots=s.Blueprint.Specs.Any(c=>c.GetType().Name=="FixedSlotManagerSpec");
          // A patrolling (water) slot shares the capacity with the transform slots (vanilla SwimmingPool).
          bool patrolling=s.Blueprint.Specs.Any(c=>c.GetType().Name=="PatrollingSlotInitializerSpec");
          int needed=fixedSlots&&enterable&&!patrolling?enterable.Capacity:1;
          Record(s,"slot nodes #Slot#"+slot.SlotKeyword,n>=needed,n+" transforms in the instance"+(fixedSlots?" (FixedSlotManager needs "+needed+")":""));
        }
      }
      if(b.HasEntrance) {
        var district=b.GetComponent<DistrictBuilding>();
        Record(s,"district connection",district&&district.District,"native district "+(district&&district.District?"assigned":"none"));
        var accessible=b.GetComponent<BuildingAccessible>();
        if(accessible)Record(s,"entrance reachable",accessible.Accessible.UnblockedSingleAccess.HasValue,"unblocked single access "+accessible.Accessible.UnblockedSingleAccess);
        var blockable=b.GetComponent<BlockableEntranceBuilding>();
        if(blockable)Record(s,"entrance not blocked",!blockable.IsEntranceBlocked()&&!blockable.IsEntranceInaccessible(),
          "blocked="+blockable.IsEntranceBlocked()+" inaccessible="+blockable.IsEntranceInaccessible());
      }
      if(s.HasPipes)Guard(s,"pipe valve target",()=>CheckValveTarget(s));
    }
    private void AcceptsGoods(Subject s,Inventory inventory) {
      var expected=new List<string>();
      var m=s.Manufactory;
      if(m&&m.HasCurrentRecipe) {
        expected.AddRange(m.CurrentRecipe.Ingredients.Select(g=>g.Id));
        if(m.CurrentRecipe.ConsumesFuel)expected.Add(m.CurrentRecipe.Fuel);
      }
      var gc=s.Building.GetComponent<GoodConsumingBuilding>();
      if(gc)expected.AddRange(gc.ConsumedGoods.Select(g=>g.GoodId));
      var pantry=s.Building.GetComponent<HospitalPantrySpec>();
      if(pantry!=null)expected.Add(pantry.WaterGoodId);
      var upkeep=s.Building.GetComponent<FrontierWorkplaceUpkeepSpec>();
      if(upkeep!=null)expected.AddRange(upkeep.Goods.Select(g=>g.GoodId));
      // Maintenance oils are accepted only while bots work there (BotMaintenanceStock); without bots
      // they must still be registered input goods.
      var maintenance=s.Building.GetComponent<FrontierBotMaintenanceSpec>();
      var oils=maintenance!=null?maintenance.Goods.Select(g=>g.GoodId).ToList():new List<string>();
      var grocery=s.Building.GetComponent<GroceryStoreSpec>();
      if(grocery!=null)expected.AddRange(grocery.Foods);
      var restaurant=s.Building.GetComponent<RestaurantSpec>();
      // Automatic kitchen: every recipe's ingredients are accepted at once, besides the menu.
      if(restaurant!=null)expected.AddRange(restaurant.Stock.Select(g=>g.GoodId));
      expected=expected.Distinct().ToList();
      if(expected.Count==0&&oils.Count==0){Skip(s,"inventory accepts goods","no input goods to check ("+inventory.ComponentName+")");return;}
      // LimitedAmount: what the inventory may hold (haulers' reservations do not count against it).
      var missing=expected.Where(g=>!inventory.InputGoods.Contains(g)||inventory.LimitedAmount(g)<=0)
        .Select(g=>g+(inventory.InputGoods.Contains(g)?"(registered, limit "+inventory.LimitedAmount(g)+")":"(not an input good)")).ToList();
      missing.AddRange(oils.Where(g=>!inventory.InputGoods.Contains(g)).Select(g=>g+"(maintenance oil not registered)"));
      Record(s,"inventory accepts goods",missing.Count==0,(missing.Count==0?"accepts ":"missing ["+string.Join(",",missing)+"] of ")+string.Join(",",expected.Concat(oils))+
        " in "+inventory.ComponentName+(m&&m.HasCurrentRecipe?" (recipe "+m.CurrentRecipe.Id+")":""));
    }

    // ---------- pipes ----------
    private IEnumerable<(Vector3Int Cell,Direction3D Dir,PipePortState State,int Index)> Ports(Subject s) {
      var ports=s.Blueprint.GetSpec<BuildingPipeTargetPortsSpec>().Ports;
      for(int i=0;i<ports.Length;i++)
        foreach(var local in ports[i].Directions.GetEnumerator().AsEnumerable())
          yield return (s.Building.TransformCoordinates(ports[i].Coordinates),s.Building.TransformDirection(local),ports[i].State,i);
    }
    private void CheckValveTarget(Subject s) {
      var target=s.Building.GetComponent<BuildingPipeTarget>();
      Require(target,"building has BuildingPipeTargetPortsSpec but no BuildingPipeTarget");
      var all=Ports(s).ToList();
      Record(s,"pipe ports horizontal only",all.All(p=>p.Dir.IsHorizontal()),all.Count+" port faces; vertical: "+all.Count(p=>!p.Dir.IsHorizontal()));
    }
    // Native runs 76 and 81: valve (Inlet on, outlet into the building) <- pipe <- powered pump <- tank.
    // The line runs outward from a generated side-face port at pad level; the first free one is used.
    private void PlacePipeLine(Subject s) {
      var m=s.Manufactory;
      bool automatic=s.Building.GetComponent<AutomaticRecipeManufactory>();
      var recipes=m&&!automatic?m.ProductionRecipes.ToList():new List<RecipeSpec>{null};
      foreach(var port in Ports(s).Where(p=>p.Index>0&&p.Dir.IsHorizontal()&&p.Cell.z==_ground&&(p.State&PipePortState.OpenIn)!=PipePortState.Closed)
          .OrderBy(p=>p.Dir==Direction3D.Up?0:1)) {
        var d=port.Dir;var step=d.ToOffset();
        var valveAt=port.Cell+step;var pipeAt=valveAt+step;var pumpAt=pipeAt+step;
        var side=new Vector3Int(-step.y,step.x,0);
        var tankAt=pumpAt+step;
        if(step.x<0)tankAt+=step;
        if(step.y<0)tankAt+=step;
        var genAt=pumpAt+side;
        var oValve=Facing(Direction2D.Down,To2D(d));var oPipe=Facing(Direction2D.Up,To2D(d));
        if(!(Free(_valve,valveAt,oValve)&&Free(_pipe,pipeAt,oPipe)&&Free(_pump,pumpAt,oValve)&&Free(_tank,tankAt)&&Free(_generator,genAt)))continue;
        if(_batch.Any(o=>o!=s&&o.Placed&&o.Building.HasEntrance&&Vector3Int.Distance(o.Building.PositionedEntrance.Coordinates,valveAt)<2))continue;
        var created=new List<BlockObject>();
        try {
          created.Add(Create(_valve,At(valveAt,oValve)));created.Add(Create(_pipe,At(pipeAt,oPipe)));
          created.Add(Create(_pump,At(pumpAt,oValve)));created.Add(Create(_tank,At(tankAt)));created.Add(Create(_generator,At(genAt)));
        } catch(Exception) {
          foreach(var b in created)_entityService.Delete(b.GetComponent<EntityComponent>());
          continue;
        }
        var valve=created[0].GetComponent<ExtractionPipe>();
        string liquid=null;RecipeSpec chosen=null;var tried=new List<string>();
        var oils=new HashSet<string>(s.Building.GetComponent<FrontierBotMaintenanceSpec>()?.Goods.Select(g=>g.GoodId)??Enumerable.Empty<string>());
        foreach(var recipe in recipes) {
          if(recipe!=null&&m.CurrentRecipe!=recipe)m.SetRecipe(recipe);
          valve.InvalidateIoTargets();
          var connection=valve.FindInletTarget();
          var liquids=connection!=null&&connection.Target.BlockObject==s.Building?connection.GetLiquidIds().ToList():new List<string>();
          tried.Add((recipe?.Id??"-")+"=>"+(connection==null?"none":connection.Target.BlockObject==s.Building?"["+string.Join("/",liquids)+"]":"other"));
          var stock=created[3].GetComponent<Stockpile>().Inventory;
          var usable=liquids.Where(l=>stock.AllowedGoods.Any(g=>g.StorableGood.GoodId==l)).ToList();
          var used=usable.FirstOrDefault(l=>recipe!=null&&(recipe.Ingredients.Any(i=>i.Id==l)||recipe.ConsumesFuel&&recipe.Fuel==l));
          if(used!=null){liquid=used;chosen=recipe;break;}
          if(liquid==null){liquid=usable.FirstOrDefault(l=>!oils.Contains(l));chosen=recipe;}
        }
        if(chosen!=null&&m.CurrentRecipe!=chosen)m.SetRecipe(chosen);
        Record(s,"valve resolves the building",liquid!=null,"HorizontalPipeValve at "+valveAt+" facing the port "+port.Cell+" "+d+": "+string.Join("; ",tried));
        if(liquid==null)return;
        created[3].GetComponent<SingleGoodAllower>().Allow(liquid);
        var tankInventory=created[3].GetComponent<Stockpile>().Inventory;
        tankInventory.GiveExisting(new GoodAmount(liquid,Math.Min(200,tankInventory.UnreservedCapacity(liquid))));
        valve.InletEnabled=true;valve.OutletEnabled=false;
        s.Valve=created[0];s.Tank=created[3];s.PipeLiquid=liquid;s.PipePort=port.Cell;s.PipeDirection=d;
        // Haulers may already have filled the building with this liquid from the district centre (b164:
        // SandstoneQuarry Water 16 of 16, so nothing could arrive); room is made so arrival is measurable.
        var target=PipeTargetInventory(s);
        int limit=target.LimitedAmount(liquid),room=limit-target.AmountInStock(liquid),spare=target.UnreservedAmountInStock(liquid);
        if(room<Math.Max(1,limit/2)&&spare>0) {
          target.TakeExisting(new GoodAmount(liquid,spare));
          Add(s,"pipe line","INFO","took "+spare+" "+liquid+" already delivered by haulers out of "+target.ComponentName+" (limit "+limit+") so the pipe's delivery is measurable");
        }
        s.PipeBaseline=target.AmountInStock(liquid);
        s.Attached.AddRange(created);
        return;
      }
      Skip(s,"pipe liquid arrives","no generated pad-level OpenIn side-face port with free cells for valve, pipe, pump, tank and generator");
    }
    private Inventory PipeTargetInventory(Subject s)=>s.Building.GetComponent<Inventories>().EnabledInventories
      .First(i=>i.ComponentName!="ConstructionSite"&&i.InputGoods.Contains(s.PipeLiquid));
    private void CheckPipeArrival(Subject s) {
      s.PipeChecked=true;
      int now=PipeTargetInventory(s).AmountInStock(s.PipeLiquid);
      var tank=s.Tank.GetComponent<Stockpile>().Inventory.AmountInStock(s.PipeLiquid);
      Record(s,"pipe liquid arrives",now>s.PipeBaseline,s.PipeLiquid+" in "+PipeTargetInventory(s).ComponentName+" "+s.PipeBaseline+" -> "+now+
        " after "+PipeHours+" h; tank "+tank+"; valve at "+s.Valve.Coordinates+" to port "+s.PipePort+" "+s.PipeDirection);
      TopUpPipeLiquid(s);
    }

    // ---------- power ----------
    private void AttachPower(Subject s) {
      if(s.NodeSpec==null||s.Powered)return;
      s.Powered=true;
      var occupied=Occupied(s.Building);
      // The building's own placement level: BlockObject.Coordinates is its layer 0, BaseZ layers below
      // the level it stands on (the Fish Hatchery, BaseZ 1, stands on the bank at layer 1).
      int level=s.Building.Coordinates.z+s.Building.BaseZ;
      // The target may be one of the building's own cells a shaft fits in (the hatchery porch's Floor);
      // the loop below asks the native validator for each.
      var faces=s.Node.Transputs.Where(t=>t.Direction.IsHorizontal()&&occupied.Contains(t.Coordinates)&&t.Target.z==level).ToList();
      if(faces.Count==0){Record(s,"power connects",false,"no horizontal transput face at the building's level "+level+" ("+s.Node.Transputs.Length+" transputs)");return;}
      foreach(var t in faces) {
        var n=t.Target;var beyond=n+t.Direction.ToOffset();
        if(s.Valve&&(n-s.Valve.Coordinates).sqrMagnitude<=2)continue;
        if(!Free(_shaft,n))continue;
        BlockObjectSpec source=s.IsGenerator?_station:_generator;
        var o=s.IsGenerator?Facing(Direction2D.Up,To2D(t.Direction.Across())):Orientation.Cw0;
        if(!Free(source,beyond,o))continue;
        var shaft=Create(_shaft,At(n));var src=Create(source,At(beyond,o));
        s.Attached.Add(shaft);s.Attached.Add(src);
        if(!s.IsGenerator)AcceptancePower.Cover(src,s.NodeSpec);
        var shaftNode=shaft.GetComponent<MechanicalNode>();
        bool linked=s.Node.Transputs.Any(x=>x.ConnectedNode==shaftNode);
        Record(s,"power connects",linked&&shaftNode.Graph==s.Node.Graph,"vanilla PowerShaft at "+n+" link="+linked+" same graph="+(shaftNode.Graph==s.Node.Graph)+
          " ("+faces.Count+" offered faces at level "+level+")");
        // The native gear socket where the shaft meets the wall (MechanicalConnectorTargetSpec; b176: the
        // FishHatchery and Greenhouse joined the graph but drew no socket).
        if(s.IsConsumer&&linked)Record(s,"power socket shown",FlipPlacementProbe.ConnectorShown(s.Building,t,out var socket),socket+" on "+t.Coordinates+" "+t.Direction);
        return;
      }
      Record(s,"power connects",false,faces.Count+" offered faces, none with free cells for a shaft and "+(s.IsGenerator?"consumer":"DevPowerGenerator"));
    }

    // ---------- waves ----------
    private IEnumerable<Subject> ServiceSubjects()=>Placed().Where(s=>!s.Workplace);
    private void PrepareWaves() {
      _waveQueue.Clear();
      foreach(var s in Placed().Where(s=>s.Workplace))_waveQueue.Enqueue(s);
    }
    private void NextWave() {
      foreach(var s in _wave)Release(s);
      _wave.Clear();
      if(_waveQueue.Count==0){StartServices();return;}
      RefreshBeavers();
      var free=_workers.Where(w=>w).ToList();
      while(_waveQueue.Count>0&&_wave.Count<free.Count)_wave.Add(_waveQueue.Dequeue());
      foreach(var s in _wave) {
        var w=s.Workplace;
        Record(s,"workplace accepts workers",w.MaxWorkers>0,"MaxWorkers="+w.MaxWorkers);
        if(w.MaxWorkers==0)continue;
        var pausable=s.Building.GetComponent<PausableBuilding>();
        if(pausable&&pausable.Paused)pausable.Resume();
        while(w.DesiredWorkers>1)w.DecreaseDesiredWorkers();
        while(w.DesiredWorkers<1)w.IncreaseDesiredWorkers();
        var worker=CrewMember(s,free);
        if(!worker){Skip(s,"worker assigned","no free adult beaver");continue;}
        free.Remove(worker);
        worker.Unemploy();worker.EmployAt(w);s.Worker=worker;
        Record(s,"worker assigned",w.NumberOfAssignedWorkers>0&&w.AssignedWorkers.Contains(worker),"assigned "+w.NumberOfAssignedWorkers+" of max "+w.MaxWorkers);
      }
      if(_siteBatch)SiteWaveStarted();
      Phase(2,"wave unpowered with workers: "+string.Join(",",_wave.Select(s=>s.Id)));
    }
    private Worker CrewMember(Subject s,List<Worker> free) {
      var discipline=s.Building.GetComponent<FrontierSpecialistWorkplaceSpec>()?.Discipline;
      if(discipline==null)return free.FirstOrDefault(w=>!w.GetComponent<SpecialistTrait>().IsSpecialist)??free.FirstOrDefault();
      var trained=free.FirstOrDefault(w=>w.GetComponent<SpecialistTrait>().Has(discipline));
      if(trained)return trained;
      var untrained=free.FirstOrDefault(w=>!w.GetComponent<SpecialistTrait>().IsSpecialist);
      if(untrained)untrained.GetComponent<SpecialistTrait>().Graduate(discipline);
      return untrained;
    }
    private void RefreshBeavers() {
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<NeedManager>()&&e.HasComponent<Enterer>()).ToList())Restore(e.GetComponent<NeedManager>());
    }
    // Basic needs, and every need that natively prevents work when critical (Deep Frontier's industrial
    // injuries and fatigue, NeedPreventingWorkSpec): the survey tests buildings, not the workforce risks.
    private static void Restore(NeedManager needs) {
      foreach(var id in BasicNeeds)if(needs.HasNeed(id))
        needs.ApplyEffect(new InstantEffect(id,needs.GetNeedSpec(id).MaximumValue-needs.GetNeedPoints(id),1));
      foreach(var spec in needs.NeedSpecs)if(spec.HasSpec<NeedPreventingWorkSpec>()&&needs.GetNeedPoints(spec.Id)<spec.MaximumValue)
        needs.ApplyEffect(new InstantEffect(spec.Id,spec.MaximumValue-needs.GetNeedPoints(spec.Id),1));
    }
    // An industrial injury or fatigue makes the native WorkRefuser unemploy the wave's worker (b161:
    // DeepProcessor's worker wandered with refuses=True). The worker is restored and employed again.
    private void KeepWorker(Subject s) {
      var w=s.Worker;
      if(!w||s.Released||!s.Workplace)return;
      var refuser=w.GetComponent<WorkRefuser>();
      bool refuses=refuser&&refuser.RefusesWork;
      if(!refuses&&w.Workplace==s.Workplace)return;
      if((_clock.PartialDayNumber-s.LastReemploy)*24f<.1f)return;
      s.LastReemploy=_clock.PartialDayNumber;
      var needs=w.GetComponent<NeedManager>();
      var critical=needs.NeedSpecs.Where(n=>n.HasSpec<NeedPreventingWorkSpec>()&&needs.NeedIsInCriticalState(n.Id)).Select(n=>n.Id).ToList();
      s.Refusals.Add((refuses?"refused work":"left the workplace")+(critical.Count>0?" ("+string.Join(",",critical)+" critical)":"")+" at "+(_clock.PartialDayNumber*24f).ToString("0.0")+" h");
      Restore(needs);
      if(w.Workplace!=s.Workplace){w.Unemploy();w.EmployAt(s.Workplace);}
      s.Reemployed++;
    }
    // Native ManufactoryInputAvailabilityChecker re-evaluates only on the building's inventory, worker or
    // district events, so a district that runs out of an ingredient after the last event leaves the status
    // stale (b169: the district's Water ran out after the workers were assigned). Just before the snapshot
    // every wave manufactory's worker is assigned again (a native worker event), so the snapshot reads a
    // fresh native verdict (b171: a building's own stock changed inside a 0.2 h window).
    private const float InputRecheckHours=.05f;
    private bool _inputRecheck;
    private void RecheckInputs(Subject s) {
      var m=s.Manufactory;var w=s.Worker;
      if(!m||!w||!m.HasCurrentRecipe||w.Workplace!=s.Workplace)return;
      w.Unemploy();w.EmployAt(s.Workplace);s.InputRechecked=true;
    }
    private const float InputRetryHours=.1f;
    private bool _inputSnapshot;
    // The native ManufactoryInputChecker verdict (internal type; read for the report only).
    private static string NativeInputVerdict(Subject s) {
      try {
        var type=typeof(Manufactory).Assembly.GetType("Timberborn.Workshops.ManufactoryInputChecker");
        var get=typeof(BaseComponent).GetMethods().First(x=>x.Name=="GetComponent"&&x.IsGenericMethodDefinition&&x.GetParameters().Length==0).MakeGenericMethod(type);
        var checker=get.Invoke(s.Building,null);
        var field=type.GetField("_inputUnavailable",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic);
        return checker==null||field==null?"native checker not readable":"native inputUnavailable="+field.GetValue(checker);
      } catch(Exception error){return "native checker not readable ("+error.GetType().Name+")";}
    }
    private void MissingInputs(Subject s,bool final) {
      var statuses=VisibleStatuses(s.Building);
      var m=s.Manufactory;
      if(m&&m.HasCurrentRecipe&&s.Worker) {
        var registry=_district.GetComponent<DistrictInventoryRegistry>();
        var unavailable=m.CurrentRecipe.Ingredients.Select(g=>g.Id).Concat(m.CurrentRecipe.ConsumesFuel?new[]{m.CurrentRecipe.Fuel}:new string[0])
          .Where(g=>registry.ActiveInventoriesWithStock(g).Count==0).ToList();
        // Native LackOfResources (CreateNormalStatusWithAlert(..., 3f)) becomes visible 3 h after it activates;
        // after the worker re-assignment just before this snapshot it is active and still in that delay (b173).
        var statusSubject=s.Building.GetComponent<StatusSubject>();
        bool visible=statuses.Any(t=>t.StartsWith(_lackOfResources,StringComparison.Ordinal));
        bool pending=!visible&&statusSubject&&statusSubject.ActiveStatuses.Any(st=>st.StatusDescription.StartsWith(_lackOfResources,StringComparison.Ordinal));
        bool shown=visible||pending;
        if(pending)statuses.Add(_lackOfResources+" [active, in the native 3 h show delay]");
        string stock="; building stock ["+string.Join(",",m.Inventory.Stock.Select(g=>g.GoodId+" "+g.Amount))+"]";
        // Native ManufactoryInputAvailabilityChecker asks the district only while the building itself lacks an
        // ingredient (!HasAllIngredients): a building already holding one cycle's inputs shows no status
        // (b169: haulers had filled the mine and quarries with Water before the district ran out).
        // Native checks the fuel first (FuelIsUnavailable), then the ingredients.
        bool holds=m.HasAllIngredients&&(!m.CurrentRecipe.ConsumesFuel||m.HasFuel);
        if(unavailable.Count>0&&holds)Skip(s,"no inputs: LackOfResources status","district lacks ["+string.Join(",",unavailable)+
          "] but the building holds every ingredient and its fuel for "+m.CurrentRecipe.Id+stock+"; visible ["+string.Join("; ",statuses)+"]");
        else if(unavailable.Count>0&&!shown&&!final){s.InputRetry=true;RecheckInputs(s);return;}
        else if(unavailable.Count>0)Record(s,"no inputs: LackOfResources status",shown,"district lacks ["+string.Join(",",unavailable)+"]"+stock+
          (s.InputRechecked?" (worker assigned again "+InputRecheckHours+" h before, native re-check"+(final?", and again "+InputRetryHours+" h before this second look":"")+")":"")+
          "; "+NativeInputVerdict(s)+"; HasAllIngredients="+m.HasAllIngredients+"; visible ["+string.Join("; ",statuses)+"]");
        else Skip(s,"no inputs: LackOfResources status","the district stocks every ingredient of "+m.CurrentRecipe.Id+"; visible ["+string.Join("; ",statuses)+"]");
      }

    }
    private static string Goods(Timberborn.Common.ReadOnlyHashSet<string> set) {
      var list=new List<string>();
      foreach(var g in set)list.Add(g);
      return string.Join("/",list);
    }
    private static string PowerDiagnostics(Subject s) {
      var n=s.Node;
      if(n==null)return "";
      var g=n.Graph;
      return " [node consumer="+n.IsConsumer+" active="+n.Active+" input="+n.Actuals.PowerInput+" graph generators="+(g?.NumberOfGenerators.ToString()??"none")+
        " supply="+g?.PowerSupply+" demand="+g?.PowerDemand+" powered="+n.Powered+"]";
    }
    // Inputs given (the pipe line supplies its liquid), workers assigned, no power: the native
    // NoPower status must show in the panel and as a floating icon.
    private void SupplyUnpowered(Subject s) {
      if(s.HasPipes&&!s.Valve)Guard(s,"pipe line",()=>PlacePipeLine(s));
      Seed(s);
    }
    private void SuppliedUnpowered(Subject s) {
      TopUpPipeLiquidNow(s);
      if(!s.IsConsumer)return;
      var statuses=VisibleStatuses(s.Building);
      var cycler=s.Building.GetComponent<StatusIconCycler>();
      // Native NoPower (with Moddable Timberborn) needs actual demand: a building whose worker is not
      // working draws nothing. Deep Frontier's own "Not connected" status covers that case.
      bool dfStatus=s.Blueprint.Specs.Any(c=>c.GetType().Name=="PowerConnectionStatusSpec");
      bool notConnected=statuses.Any(t=>t.StartsWith(_notConnected,StringComparison.Ordinal));
      if(dfStatus)Record(s,"supplied, unpowered: 'Not connected' in panel",notConnected,"visible ["+string.Join("; ",statuses)+"]");
      if(s.Node.Actuals.PowerInput==0) {
        Skip(s,"supplied, unpowered: NoPower status in panel","not drawing power (no worker working or no consumption) so native NoPower is not expected"+PowerDiagnostics(s));
        return;
      }
      bool panel=statuses.Any(t=>t.StartsWith(_noPower,StringComparison.Ordinal));
      Record(s,"supplied, unpowered: NoPower status in panel",panel,"visible ["+string.Join("; ",statuses)+"]"+PowerDiagnostics(s));
      bool floating=cycler&&cycler.VisibleAndActive&&statuses.Any(t=>t.StartsWith(_noPower,StringComparison.Ordinal)&&t.Contains("[icon]"));
      Record(s,"supplied, unpowered: NoPower floating icon",floating,"StatusIconCycler.VisibleAndActive="+(cycler&&cycler.VisibleAndActive));
    }
    private void TopUpPipeLiquidNow(Subject s) {if(s.PipeLiquid!=null&&s.PipeChecked)TopUpPipeLiquid(s);}
    private void Seed(Subject s) {
      s.Seeded=true;
      var m=s.Manufactory;
      if(m&&s.Building.GetComponent<AutomaticRecipeManufactory>())SeedKitchen(s);
      else if(m&&m.HasCurrentRecipe) {
        var r=m.CurrentRecipe;
        foreach(var g in r.Ingredients) {
          if(g.Id==s.PipeLiquid)continue;   // the pipe line supplies it
          int amount=Math.Min(g.Amount*3,m.Inventory.UnreservedCapacity(g.Id));
          if(amount>0)m.Inventory.GiveExisting(new GoodAmount(g.Id,amount));
        }
        if(r.ConsumesFuel){int amount=Math.Min(12,m.Inventory.UnreservedCapacity(r.Fuel));if(amount>0)m.Inventory.GiveExisting(new GoodAmount(r.Fuel,amount));}
      }
      var gc=s.Building.GetComponent<GoodConsumingBuilding>();
      if(gc)foreach(var g in gc.ConsumedGoods) {
        if(g.GoodId==s.PipeLiquid)continue;
        int amount=Math.Min((int)Math.Ceiling(g.GoodPerHour*24),gc.Inventory.UnreservedCapacity(g.GoodId));
        if(amount>0)gc.Inventory.GiveExisting(new GoodAmount(g.GoodId,amount));
      }
      var maintenance=s.Building.GetComponent<FrontierBotMaintenanceSpec>();
      if(maintenance!=null&&m)foreach(var g in maintenance.Goods) {
        int amount=Math.Min(maintenance.CapacityPerGood,m.Inventory.UnreservedCapacity(g.GoodId));
        if(amount>0)m.Inventory.GiveExisting(new GoodAmount(g.GoodId,amount));
      }
      // Workplace upkeep (drill bits): production stops without them.
      var upkeep=s.Building.GetComponent<FrontierWorkplaceUpkeepSpec>();
      if(upkeep!=null&&m)foreach(var g in upkeep.Goods) {
        int amount=Math.Min(upkeep.CapacityPerGood,m.Inventory.UnreservedCapacity(g.GoodId));
        if(amount>0)m.Inventory.GiveExisting(new GoodAmount(g.GoodId,amount));
      }
    }
    private void SeedKitchen(Subject s) {
      var m=s.Manufactory;
      var recipes=m.ProductionRecipes.Where(r=>r.Ingredients.Length>0&&r.Ingredients.All(g=>g.Id!=s.PipeLiquid)).ToList();
      var first=recipes.FirstOrDefault();
      var second=first==null?null:recipes.FirstOrDefault(r=>r!=first&&!r.Ingredients.Any(g=>first.Ingredients.Any(f=>f.Id==g.Id)));
      if(second==null){Skip(s,"automatic kitchen cooks every stocked recipe","no two recipes with separate ingredients outside the pipe liquid");return;}
      s.Kitchen=new KitchenRun{First=first,Second=second};
      foreach(var r in new[]{first,second})GiveIngredients(m,r,2);
      m.ProductionFinished+=(_,_)=>KitchenBatchFinished(s);
      Add(s,"automatic kitchen","INFO","stocked two batches each of "+first.Id+" and "+second.Id+"; the test never sets a recipe");
    }
    private static void GiveIngredients(Manufactory m,RecipeSpec r,int batches) {
      foreach(var g in r.Ingredients) {
        int amount=Math.Min(g.Amount*batches,m.Inventory.UnreservedCapacity(g.Id));
        if(amount>0)m.Inventory.GiveExisting(new GoodAmount(g.Id,amount));
      }
    }
    // ProductionFinished fires after the native reset, before the chooser's next choice: CurrentRecipe is
    // the batch that finished.
    private void KitchenBatchFinished(Subject s) {
      var k=s.Kitchen;var m=s.Manufactory;
      if(k==null||!m||k.Done)return;
      k.Batches.Add(m.CurrentRecipe.Id);
      if(k.Removed==null&&k.Batches.Contains(k.First.Id)&&k.Batches.Contains(k.Second.Id)) {
        foreach(var g in k.Second.Ingredients) {int held=m.Inventory.UnreservedAmountInStock(g.Id);if(held>0)m.Inventory.TakeExisting(new GoodAmount(g.Id,held));}
        GiveIngredients(m,k.First,2);
        k.Removed=k.Second.Id;k.BatchesAtRemoval=k.Batches.Count;
        Add(s,"automatic kitchen","INFO","took away every unreserved "+string.Join("/",k.Second.Ingredients.Select(g=>g.Id))+" after batches ["+string.Join(",",k.Batches)+"]");
      } else if(k.Removed!=null&&m.CurrentRecipe==k.First)k.Done=true;
    }
    // Liquid the pipe was meant to deliver, when it did not arrive: give it so the rest still runs.
    private void TopUpPipeLiquid(Subject s) {
      if(s.PipeLiquid==null)return;
      var inventory=PipeTargetInventory(s);
      // Enough for one production cycle (a recipe can need more than a pipe has delivered so far).
      var m=s.Manufactory;
      int needed=Math.Max(1,m&&m.HasCurrentRecipe?m.CurrentRecipe.Ingredients.Where(g=>g.Id==s.PipeLiquid).Sum(g=>g.Amount):1);
      int stock=inventory.AmountInStock(s.PipeLiquid);
      if(stock>=needed)return;
      int amount=Math.Min(Math.Max(20,needed)-stock,inventory.UnreservedCapacity(s.PipeLiquid));
      if(amount>0)inventory.GiveExisting(new GoodAmount(s.PipeLiquid,amount));
    }
    private void Observe(Subject s) {
      // Sites batch: unpowered site workplaces (pumps) produce from the start of their wave.
      if(_phase!=3&&_phase!=6&&!(_siteBatch&&_phase==2)||!s.Building)return;
      var m=s.Manufactory;
      if(m){s.MaxProgress=Math.Max(s.MaxProgress,m.ProductionProgress);}
      var workshop=s.Building.GetComponent<Workshop>();
      if(workshop&&workshop.CurrentlyWorking)s.Worked=true;
      if(s.Worker&&s.Worker.GetComponent<Enterer>().CurrentBuilding==s.Building.GetComponent<Enterable>())s.Entered=true;
      // Workplaces whose workers work at stations rather than inside the Enterable (Hospital, Restaurant,
      // GroceryStore, b175) are reached when the worker comes to the building's access on its entrance.
      var accessible=s.Building.GetComponent<BuildingAccessible>();
      if(s.Worker&&accessible&&accessible.Accessible.UnblockedSingleAccess.HasValue)
        s.AccessDistance=Math.Min(s.AccessDistance,Vector3.Distance(s.Worker.Transform.position,accessible.Accessible.UnblockedSingleAccess.Value));
      if(m&&m.ProductionProgress>0)s.Worked=true;
      if(s.Node!=null){s.MaxInput=Math.Max(s.MaxInput,s.Node.Actuals.PowerInput);s.MaxOutput=Math.Max(s.MaxOutput,s.Node.Actuals.PowerOutput);}
      if(s.PipeChecked&&!s.Released)TopUpPipeLiquid(s);
      // A site subject that must produce is finished once a native production cycle completed.
      bool mustProduce=_siteBatch&&s.Site?["produces"]!=null;
      if(s.Worked&&(mustProduce?s.Produced>0:s.MaxProgress>.05f))s.Finished=true;
      if(s.Kitchen!=null)s.Finished=s.Kitchen.Done;
    }
    private void EvaluateWave() {
      foreach(var s in _wave) {
        if(s.Valve&&!s.PipeChecked)Guard(s,"pipe liquid arrives",()=>CheckPipeArrival(s));
        var m=s.Manufactory;var w=s.Workplace;
        var blockable=s.Building.GetComponent<BlockableObject>();
        string diag=" working hours="+_hours.AreWorkingHours+" unblocked="+(blockable?blockable.IsUnblocked.ToString():"n/a")+" paused="+(s.Building.GetComponent<PausableBuilding>()?.Paused.ToString()??"n/a")+
          " assigned="+w.NumberOfAssignedWorkers+" working="+(s.Building.GetComponent<Workshop>()?.NumberOfWorkersWorking.ToString()??"n/a")+
          " power="+(s.Node!=null?s.Node.PowerEfficiency.ToString("0.##"):"n/a")+(s.Node!=null?" graph powered="+s.Node.Powered+" demand="+s.Node.Graph?.PowerDemand:"")+
          " workplace behaviors ["+string.Join(",",w.WorkplaceBehaviors.Select(x=>x.GetType().Name+(x.Enabled?"":"(disabled)")))+"]"+
          (s.Worker?" worker "+s.Worker.GetComponent<Timberborn.Characters.Character>().FirstName+
            (s.Worker.GetComponent<SpecialistTrait>().IsSpecialist?" ("+string.Join("/",s.Worker.GetComponent<SpecialistTrait>().Disciplines)+" specialist)":"")+
            " refuses="+s.Worker.GetComponent<WorkRefuser>().RefusesWork:"")+
          (s.Worker?" worker inside="+(s.Worker.GetComponent<Enterer>().CurrentBuilding==s.Building.GetComponent<Enterable>())+
           " behaviors ["+string.Join(" | ",s.Worker.GetComponent<Timberborn.BehaviorSystem.BehaviorManager>().TimestampedBehaviorLog.Reverse().Take(5))+"]":"")+
          " worker distance="+(s.Worker?Vector3.Distance(s.Worker.Transform.position,s.Building.Transform.position).ToString("0.#"):"-")+
          " statuses ["+string.Join("; ",VisibleStatuses(s.Building))+"]";
        if(m&&m.HasCurrentRecipe)Record(s,"manufactory makes progress",s.Worked&&s.MaxProgress>0,"recipe "+m.CurrentRecipe.Id+" max progress "+
          s.MaxProgress.ToString("0.###")+" ready="+m.IsReadyToProduce+" fuel="+m.FuelRemaining.ToString("0.##")+" stock ["+
          string.Join(",",m.Inventory.Stock.Select(g=>g.GoodId+" "+g.Amount))+"] needs ["+string.Join(",",m.CurrentRecipe.Ingredients.Select(g=>g.Id+" "+g.Amount))+
          (m.CurrentRecipe.ConsumesFuel?"; fuel "+m.CurrentRecipe.Fuel:"")+"]"+diag);
        else if(!m)Skip(s,"manufactory makes progress","workplace without a Manufactory;"+diag);
        if(s.Kitchen!=null) {
          var k=s.Kitchen;var chooser=s.Building.GetComponent<RestaurantKitchenChooser>();
          string sequence="batches ["+string.Join(",",k.Batches)+"] chooser reason "+chooser.Reason+", "+chooser.Switches+" switches;"+diag;
          int beforeRemoval=k.BatchesAtRemoval<0?k.Batches.Count:k.BatchesAtRemoval;
          Record(s,"automatic kitchen cooks every stocked recipe",k.Batches.Take(beforeRemoval).Contains(k.First.Id)&&k.Batches.Take(beforeRemoval).Contains(k.Second.Id)
            &&k.Batches.Count>=2&&k.Batches[0]!=k.Batches[1],sequence);
          Record(s,"automatic kitchen keeps cooking without one recipe's ingredients",k.Done,
            (k.Removed==null?"ingredients were never removed (both recipes not yet cooked); ":"removed "+k.Removed+" after "+k.BatchesAtRemoval+" batches; ")+sequence);
        }
        PowerVerdict(s);
        // The worker walked the player's road to the entrance and went in (no special access exists).
        if(s.Worker&&s.Building.GetComponent<Enterable>())Record(s,"a beaver reached the building through its entrance",s.Entered||s.AccessDistance<=1.5f,
          (s.Entered?"worker inside the building":"worker never inside the Enterable")+"; closest to the entrance access "+
          (s.AccessDistance<float.MaxValue?s.AccessDistance.ToString("0.0"):"-")+"; entrance "+(s.Building.HasEntrance?s.Building.PositionedEntrance.Coordinates.ToString():"-"));
        if(s.Reemployed>0)Add(s,"worker kept","INFO",s.Reemployed+" times restored and employed again: "+string.Join("; ",s.Refusals.Take(5)));
        if(_siteBatch&&s.Site!=null)Guard(s,"site verdict",()=>SiteWaveVerdict(s));
      }
    }
    private void ConnectedVerdict(Subject s) {
      if(!s.Powered||!s.IsConsumer||!s.Blueprint.Specs.Any(c=>c.GetType().Name=="PowerConnectionStatusSpec"))return;
      var statuses=VisibleStatuses(s.Building);
      bool generator=s.Node.Graph!=null&&s.Node.Graph.NumberOfGenerators>0;
      if(!generator){Skip(s,"connected: 'Not connected' cleared","no generator joined the building graph");return;}
      Record(s,"connected: 'Not connected' cleared",!statuses.Any(t=>t.StartsWith(_notConnected,StringComparison.Ordinal)),
        "graph generators="+s.Node.Graph.NumberOfGenerators+"; visible ["+string.Join("; ",statuses)+"]");
    }
    private void PowerVerdict(Subject s) {
      ConnectedVerdict(s);
      if(s.NodeSpec==null)return;
      var g=s.Node.Graph;
      if(s.IsConsumer)Record(s,"power demand",s.MaxInput==s.NodeSpec.PowerInput&&s.Node.Powered,"spec input "+s.NodeSpec.PowerInput+" hp; peak actual "+s.MaxInput+
        " hp; graph supply "+g?.PowerSupply+" demand "+g?.PowerDemand+" powered="+s.Node.Powered);
      if(s.IsGenerator&&s.Blueprint.Specs.Any(c=>c.GetType().Name=="HydroTurbineSpec")) {
        if(_siteBatch&&s.Site!=null)HydroVerdict(s);
        else Add(s,"power supply","SITE","water turbine: needs flowing water");
        return;
      }
      if(s.IsGenerator)Record(s,"power supply",s.MaxOutput>=s.NodeSpec.PowerOutput,"spec output "+s.NodeSpec.PowerOutput+" hp; peak actual "+s.MaxOutput+" hp; graph supply "+g?.PowerSupply);
    }
    private void Release(Subject s) {
      if(s.Released)return;
      s.Released=true;
      Idle(s);
    }

    // ---------- services and attractions ----------
    private void StartServices() {
      if(_siteBatch)OpenTurbine();
      foreach(var s in ServiceSubjects())Guard(s,"supply without power",()=>SupplyUnpowered(s));
      Phase(4,"services supplied and piped, unpowered");
    }
    // Attractions are tested one at a time: every other attraction of the batch is blocked (native
    // BlockableObject, so Attraction.IsUsable is false) and the adult beavers' needs this attraction
    // satisfies are lowered, so a visit can only go to it.
    private readonly Queue<Subject> _attractions=new();
    private Subject _current;
    private void StartAttractions() {
      foreach(var s in ServiceSubjects())TopUpPipeLiquid(s);
      _attractions.Clear();
      foreach(var s in ServiceSubjects().Where(s=>s.IsAttraction))_attractions.Enqueue(s);
      _current=null;
      if(!NextAttraction()){EvaluateServices();EndBatch();}
    }
    private bool NextAttraction() {
      if(_attractions.Count==0){Unblock();_current=null;return false;}
      _current=_attractions.Dequeue();
      foreach(var other in Placed().Where(o=>o!=_current&&o.IsAttraction)) {
        var blockable=other.Building.GetComponent<BlockableObject>();
        if(blockable&&_blocked.Add(blockable))blockable.Block(this);
      }
      if(_blocked.Remove(_current.Building.GetComponent<BlockableObject>()))_current.Building.GetComponent<BlockableObject>().Unblock(this);
      RefreshBeavers();
      TopUpPipeLiquid(_current);
      var a=_current.Building.GetComponent<Attraction>();var en=_current.Building.GetComponent<Enterable>();
      var acc=_current.Building.GetComponent<BuildingAccessible>();var behavior=_current.Building.GetComponent<AttractionNeedBehavior>();
      // Open (Enterable enabled): every slot may already be reserved by beavers walking to it (b165: the
      // DoubleShower's two slots), which is demand, not a fault.
      Record(_current,"attraction appealing",a.IsUsable&&en.Enabled&&acc&&acc.Accessible.UnblockedSingleAccess.HasValue&&behavior&&behavior.Enabled,
        "IsUsable="+a.IsUsable+" open="+en.Enabled+" canReserve="+en.CanReserveSlot+" inside="+en.NumberOfEnterersInside+" access="+(acc?acc.Accessible.UnblockedSingleAccess?.ToString():"none")+
        " needBehavior="+(behavior&&behavior.Enabled)+" effects "+string.Join(",",a.Effects.Select(e=>e.NeedId))+"; statuses ["+string.Join("; ",VisibleStatuses(_current.Building))+"]");
      int lowered=0;
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<NeedManager>()&&e.HasComponent<Enterer>()&&e.HasComponent<Worker>()).ToList()) {
        var needs=e.GetComponent<NeedManager>();
        foreach(var id in a.Effects.Select(x=>x.NeedId).Distinct())if(needs.HasNeed(id)) {
          var spec=needs.GetNeedSpec(id);
          float target=spec.MinimumValue+.1f*(spec.MaximumValue-spec.MinimumValue);
          needs.ApplyEffect(new InstantEffect(id,target-needs.GetNeedPoints(id),1));lowered++;
        }
      }
      Phase(5,"attraction "+_current.Id+" ("+lowered+" needs lowered; "+_blocked.Count+" other attractions blocked)");
      return true;
    }
    private readonly HashSet<BlockableObject> _blocked=new();
    private void Unblock() {
      foreach(var b in _blocked.Where(b=>b))b.Unblock(this);
      _blocked.Clear();
    }
    private void ObserveVisitors(Subject s) {
      if(_phase!=5||!s.Building)return;
      var en=s.Building.GetComponent<Enterable>();
      foreach(var e in en.EnterersInside)s.Visitors.Add(e);
      s.MaxInside=Math.Max(s.MaxInside,en.NumberOfEnterersInside);
    }
    private void EvaluateAttraction(Subject s) {
      Record(s,"attraction visited",s.Visitors.Count>0,s.Visitors.Count+" distinct visitors, at most "+s.MaxInside+" inside within "+
        Hours.ToString("0.0")+" h; statuses ["+string.Join("; ",VisibleStatuses(s.Building))+"]");
    }
    private void EvaluateServices() {
      foreach(var s in ServiceSubjects()) {
        if(s.Valve&&!s.PipeChecked)Guard(s,"pipe liquid arrives",()=>CheckPipeArrival(s));
        ConnectedVerdict(s);
        if(s.IsConsumer)Record(s,"power demand",s.Node.Powered&&s.MaxInput==s.NodeSpec.PowerInput,
          "spec input "+s.NodeSpec.PowerInput+" hp; peak actual "+s.MaxInput+" hp; graph supply "+s.Node.Graph?.PowerSupply+" powered="+s.Node.Powered);
        if(s.IsGenerator)PowerVerdict(s);
      }
    }

    // ---------- deleted buildings leave no district inventory behind ----------
    // Exact repro of the b161 crash (Moddable Recipes 11.0.0 double Enable, InventoryEnableGuard.cs): a
    // deleted single-recipe manufactory stayed registered, and a worker emptying a good it accepted reached
    // it through the native DistrictInventoryPicker. After each batch is deleted, every good its buildings'
    // inventories accepted or held is looked up through that same native picker (from the district centre),
    // and the district registry must not list a destroyed or deleted inventory. The next batch's workers
    // then empty their outputs through the same path for real.
    private readonly List<(Subject Subject,List<Inventory> Inventories,List<string> Goods)> _deleted=new();
    private int _probeFrame;
    private void RememberDeleted() {
      _deleted.Clear();
      foreach(var s in _batch.Where(s=>s.Placed&&s.Building)) {
        var inventories=s.Building.GetComponent<Inventories>();
        if(!inventories)continue;
        var list=inventories.AllInventories.Where(i=>i.ComponentName!="ConstructionSite").ToList();
        if(list.Count==0)continue;
        var goods=new List<string>();
        foreach(var i in list){foreach(var g in i.InputGoods)goods.Add(g);foreach(var g in i.OutputGoods)goods.Add(g);}
        _deleted.Add((s,list,goods.Distinct().ToList()));
      }
      _probeFrame=_frame+3;
    }
    private void ProbeDeleted() {
      _probeFrame=0;
      var registry=_district.GetComponent<DistrictInventoryRegistry>();
      var picker=_district.GetComponent<DistrictInventoryPicker>();
      var start=_district.GetComponent<BuildingAccessible>().Accessible;
      foreach(var (s,inventories,goods) in _deleted) {
        var (stale,errors)=LeftBehind(inventories,goods);
        Record(s,"deleted: no district inventory left behind",stale.Count==0&&errors.Count==0,goods.Count+" goods looked up through the native DistrictInventoryPicker after deletion"+
          (stale.Count>0?"; still registered: "+string.Join(", ",stale.Take(6)):"")+(errors.Count>0?"; picker failed: "+string.Join(", ",errors.Take(6)):""));
      }
      _deleted.Clear();
    }
    // Goods of deleted inventories looked up as an emptying worker does: registry entries that are
    // destroyed or belong to the deleted inventories, and native picker failures.
    private (List<string> Stale,List<string> Errors) LeftBehind(List<Inventory> inventories,List<string> goods) {
      var registry=_district.GetComponent<DistrictInventoryRegistry>();
      var picker=_district.GetComponent<DistrictInventoryPicker>();
      var start=_district.GetComponent<BuildingAccessible>().Accessible;
      var stale=new List<string>();var errors=new List<string>();
      foreach(var g in goods) {
        var listed=new List<Inventory>();
        foreach(var i in registry.ActiveInventoriesWithCapacity(g))listed.Add(i);
        foreach(var i in registry.ActiveInventoriesWithStock(g))listed.Add(i);
        foreach(var i in listed)
          if(!i||inventories.Any(d=>ReferenceEquals(d,i)))stale.Add(g+(i?" (deleted building's inventory)":" (destroyed inventory)"));
        try {picker.ClosestInventoryWithCapacity(start,new GoodAmount(g,1),_=>true,out _);}
        catch(Exception error){errors.Add(g+": "+error.GetType().Name);}
      }
      return (stale.Distinct().ToList(),errors);
    }

    // Construction-site repro of the same bug (Moddable Recipes 11.0.0 enables a manufactory inventory on
    // SetRecipe even on an unfinished site; ModdableRecipesEnabledState restores the state). Before the
    // first batch: a vanilla single-recipe Smelter is placed as an unfinished native site, a recipe is
    // selected, the site is deleted, and every good it accepted is looked up through the native picker.
    private const string ReproTemplate="Smelter.IronTeeth";
    private int _reproFrame;
    private BlockObject _reproSite;
    private List<Inventory> _reproInventories;
    private List<string> _reproGoods;
    private Subject ReproSubject=>_subjects.First(s=>s.Template==ReproTemplate);
    private void StartConstructionRepro() {
      var s=ReproSubject;
      try {
        var spec=Spec(ReproTemplate);
        var p=At(new Vector3Int(_pad.xMin+Margin,_pad.yMin+Margin,_ground)-new Vector3Int(Bounds(spec,At(Vector3Int.zero)).xMin,Bounds(spec,At(Vector3Int.zero)).yMin,spec.BaseZ));
        Require(_validator.BlocksValid(spec,p),"native placement rejected the repro site at "+p.Coordinates);
        _reproSite=_factory.CreateUnfinished(new EntitySetup.Builder(spec.Blueprint),p);
        var m=_reproSite.GetComponent<Manufactory>();
        var inventory=m.Inventory;
        bool before=inventory.Enabled;
        Require(m.ProductionRecipes.Length==1,ReproTemplate+" is expected to have a single recipe");
        m.SetRecipe(m.ProductionRecipes[0]);
        bool after=inventory.Enabled;
        _reproInventories=_reproSite.GetComponent<Inventories>().AllInventories.Where(i=>i.ComponentName!="ConstructionSite").ToList();
        _reproGoods=new List<string>();
        foreach(var i in _reproInventories){foreach(var g in i.InputGoods)_reproGoods.Add(g);foreach(var g in i.OutputGoods)_reproGoods.Add(g);}
        _reproGoods=_reproGoods.Distinct().ToList();
        var (registered,_)=LeftBehind(_reproInventories,_reproGoods);
        Record(s,"construction site: recipe leaves the inventory disabled and unregistered",!_reproSite.IsFinished&&!after&&registered.Count==0,
          "unfinished native site at "+p.Coordinates+"; manufactory inventory enabled before SetRecipe="+before+", after="+after+
          "; registered for "+(registered.Count>0?string.Join(", ",registered):"none")+" of "+string.Join("/",_reproGoods)+
          " (ModdableRecipesEnabledState restored "+ModdableRecipesEnabledState.Restored+" so far)");
      } catch(Exception error) {
        Record(s,"construction site: recipe leaves the inventory disabled and unregistered",false,"exception: "+error.GetType().Name+": "+error.Message);
      }
      _reproFrame=_frame+3;
      _speed.ChangeSpeed(3);
      Phase(11,"construction-site repro: delete the unfinished site");
    }
    private void DeleteConstructionRepro() {
      if(_reproSite)_entityService.Delete(_reproSite.GetComponent<EntityComponent>());
      _reproFrame=_frame+3;
      Phase(12,"construction-site repro: look up its goods after deletion");
    }
    private void ProbeConstructionRepro() {
      var s=ReproSubject;
      if(_reproInventories==null){Skip(s,"construction site deleted: no district inventory left behind","the repro site was not created");return;}
      var (stale,errors)=LeftBehind(_reproInventories,_reproGoods);
      Record(s,"construction site deleted: no district inventory left behind",stale.Count==0&&errors.Count==0,
        _reproGoods.Count+" goods ("+string.Join("/",_reproGoods)+") looked up through the native DistrictInventoryPicker after deleting the site"+
        (stale.Count>0?"; still registered: "+string.Join(", ",stale):"")+(errors.Count>0?"; picker failed: "+string.Join(", ",errors):""));
    }

    // ---------- results ----------
    private void Finish() {
      if(_probeFrame>0)ProbeDeleted();
      _finished=true;_speed.ChangeSpeed(0);
      if(_normalHours>0)_hours.WorkedPartOfDay=_normalHours;
      WriteResults(true);
      int fails=_subjects.Sum(s=>s.Checks.Count(c=>c.Status=="FAIL"));
      Debug.Log(Tag+" COMPLETE "+_subjects.Count+" subjects, "+fails+" failed checks; results outputs/all-buildings-"+_label+".json");
    }
    private void WriteResults(bool complete) {
      Directory.CreateDirectory(Outputs);
      var result=new JObject{
        ["label"]=_label,["complete"]=complete,["startedAt"]=_startedAt.ToString("o"),["writtenAt"]=DateTime.Now.ToString("o"),
        ["pad"]=_pad.ToString(),["ground"]=_ground,["workers"]=_workers.Count,["harness"]=new JArray(_harness),["sites"]=_siteReport,["inventoryEnableGuardSkipped"]=InventoryEnableGuard.Skipped,["moddableRecipesStatesRestored"]=ModdableRecipesEnabledState.Restored,
        ["buildings"]=new JArray(_subjects.Select(s=>new JObject{
          ["template"]=s.Template,["kind"]=s.Kind,["batch"]=s.Batch,
          ["verdict"]=s.Checks.Any(c=>c.Status=="FAIL")?"FAIL":s.Checks.Any(c=>c.Status=="SITE")?"SITE":s.Checks.Count==0?"NOT RUN":"PASS",
          ["icon"]=s.Icon,
          ["checks"]=new JArray(s.Checks.Select(c=>new JObject{["check"]=c.Name,["status"]=c.Status,["detail"]=c.Detail}))}))
      };
      File.WriteAllText(Path.Combine(Outputs,"all-buildings-"+_label+".json"),result.ToString(Formatting.Indented));
    }
  }

  internal static class AllBuildingsMath {
    public static int Round(this float value)=>Mathf.RoundToInt(value);
  }

  // Test power supply sized from data (AllBuildings and Lategame runs): one native DevPowerGenerator
  // per consumer, its output multiplier set to the whole number of rated outputs (MechanicalNodeSpec.PowerOutput)
  // that covers the consumer's MechanicalNodeSpec.PowerInput. Native 1.1.2.8 (decompiled):
  // AdjustableStrengthPowerGenerator.InitializeEntity starts a new generator at 0.5, MechanicalNode
  // outputs ceil(PowerOutput x OutputMultiplier) with no upper clamp, and the multiplier is not saved
  // (a loaded generator runs at 1), so callers size it after creating and after loading.
  internal static class AcceptancePower {
    public static int Units(int power,int ratedOutput)=>(power+ratedOutput-1)/ratedOutput;
    public static void Cover(BlockObject generator,MechanicalNodeSpec consumer) {
      var node=generator.GetComponent<MechanicalNode>();
      node.SetOutputMultiplier(Units(consumer.PowerInput,generator.GetComponent<MechanicalNodeSpec>().PowerOutput));
    }
  }
}
#endif
