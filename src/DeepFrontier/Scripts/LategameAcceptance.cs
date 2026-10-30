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
using PowerLines.Components;
using PowerLines.Services;
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
  // Explicit disposable fixture only: -deepFrontierLoadAcceptance plus
  // -deepFrontierLategame (main) or -deepFrontierLategameReload (fresh process).
  [Context("Game")]
  public sealed class LategameAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      var args=Environment.GetCommandLineArgs();
      if(args.Contains("-deepFrontierLategame")||args.Contains("-deepFrontierLategameReload"))
        Bind<LategameAcceptance>().AsSingleton();
    }
  }

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

  // Data-driven survey of every installed late-game building (tools/lategame_batches.json),
  // GroceryStore, MaterialsLaboratory and any installed ConcreteSidePlatform*. Each
  // building is placed by native services in a cleared, levelled pad of the marked
  // settlement, then checked: placement variants and occupancy, entrance path and
  // district connection, shafts on offered faces (and not on unoffered faces),
  // Powered Tubeway, Power Lines, Conveyor Belt inventory ends, Timber Pipes ports,
  // native props, and workshop/ambient animation while working and idle. Individual
  // findings are recorded and the run continues; the harness itself fails explicitly.
  internal sealed class LategameAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private const string Tag="[DeepFrontier Lategame]";
    private const string Marker="Deep Frontier Acceptance Fixture";
    private static readonly string Root=Path.Combine(
      Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding");
    private static readonly string Outputs=Path.Combine(Root,"outputs");
    private static readonly string RecordPath=Path.Combine(Outputs,"lategame-reload-expectations.json");
    // Disposable pad east of the existing fixture road; it is cleared of natural
    // resources and map blockages and levelled to the fixture's ground height 3.
    // Disposable pad east of the fixture: x 189..252, from y 136 north. Its height is computed
    // from the installed blueprints' footprints (PlanLayout) and capped below the map's
    // water sources at y 243. Natural resources, map blockages and ruins inside are removed.
    private const int PadX=189,PadWidth=64,PadY=136,PadMaxY=240;
    private RectInt Region=new(PadX,PadY,PadWidth,1);
    // The road is rebuilt from the district center's own entrance, so dropped fixture paths
    // (see AcceptanceLoadingIssues) cannot disconnect the pad.
    private RectInt RouteArea=>new(118,128,Region.xMax-118,Math.Max(Region.yMax,180)-128);
    private static readonly Vector3Int Pad=new(190,137,3);
    private const int Ground=3;
    private static readonly Orientation[] Rotations={Orientation.Cw0,Orientation.Cw90,Orientation.Cw180,Orientation.Cw270};
    private static readonly string[] BasicNeeds={"Hunger","Thirst","Sleep"};

    private sealed class ValveTest {
      public BlockObject Valve;
      public Vector3Int Port;
      public Direction3D Direction;
      public PipePortState State;
    }
    private sealed class Subject {
      public string Id,Template,Skip;
      public Blueprint Blueprint;
      public BlockObjectSpec Spec;
      public BlockObject Building,Understructure,EntrancePath,Shaft,Source,Tubeway,NegShaft,CableGen,BeltIn,BeltOut,RoofShaft;
      public readonly List<ValveTest> Valves=new();
      public Orientation Orientation;
      public bool Flip;
      public int Margin;
      public RectInt Allocation;
      public Vector3Int Anchor;
      // Wave state.
      public Worker Worker;
      public bool Working,WorkSampled,IdleChecked;
      public float WorkRealStart,AnimTime,AnimRepeated;
      public IAnimator WorkAnimator;
      public float PeakReactorOutput;
      public bool StationPowered,CableConnected;
      public BlockObject Lever;
      public string AutomationRole;
      public bool Service,ServiceSeen,OffChecked,Returned;
      public MechanicalNode Node=>Building?Building.GetComponent<MechanicalNode>():null;
      public MechanicalNodeSpec NodeSpec=>Blueprint.HasSpec<MechanicalNodeSpec>()?Blueprint.GetSpec<MechanicalNodeSpec>():null;
      public bool IsGenerator=>NodeSpec!=null&&NodeSpec.PowerOutput>0;
      public bool IsConsumer=>NodeSpec!=null&&NodeSpec.PowerInput>0;
      public bool IsWorkshop=>Building&&Building.HasComponent<Workshop>()&&Building.HasComponent<Manufactory>();
      public bool IsServiceBuilding=>Building&&(Building.HasComponent<GroceryStore>()||Building.HasComponent<Hospital>()||Building.HasComponent<Restaurant>());
      public Automatable Automatable=>Building.GetComponent<Automatable>();
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
    private readonly IConnectionService _connections;
    private readonly PowerLineConnectionService _lines;
    private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock;
    private readonly WorkingHoursManager _hours;
    private readonly CameraService _camera;
    private readonly GameSaver _saver;
    private readonly GameLoader _loader;
    private readonly bool _reload=Environment.GetCommandLineArgs().Contains("-deepFrontierLategameReload");
    private readonly List<Subject> _subjects=new();
    private readonly List<LategameCheckRecord> _results=new();
    private readonly List<RectInt> _allocated=new();
    private readonly HashSet<Vector3Int> _network=new();
    private readonly List<Worker> _workers=new();
    private readonly List<Subject> _wave=new();
    private readonly Queue<Subject> _waveQueue=new();
    private readonly List<(Subject Subject,IAnimator Animator,float Time,float Repeated,string Name)> _staticAnimators=new();
    private DistrictCenter _district;
    private BlockObjectSpec _path,_shaft,_generator,_station,_valve,_belt,_tubeway,_platform,_lever;
    private JObject _automationRoles;
    private BlockObject _persistenceLever;
    private bool _tubewayPowered;
    private float _normalHours,_phaseTime,_phaseReal;
    private int _frame,_phase;
    private bool _finished,_started;
    private string _phaseName="setup";

    public LategameAcceptance(EntityRegistry entities,EntityService entityService,TemplateService templates,
      BlockObjectFactory factory,BlockValidator validator,BlockObjectValidationService validation,IBlockService blocks,
      ITerrainService terrain,IThreadSafeWaterMap water,IConnectionService connections,PowerLineConnectionService lines,
      SpeedManager speed,IDayNightCycle clock,WorkingHoursManager hours,CameraService camera,GameSaver saver,GameLoader loader) {
      _entities=entities;_entityService=entityService;_templates=templates;_factory=factory;_validator=validator;
      _validation=validation;_blocks=blocks;_terrain=terrain;_water=water;_connections=connections;_lines=lines;
      _speed=speed;_clock=clock;_hours=hours;_camera=camera;_saver=saver;_loader=loader;
    }

    // ---------- result recording ----------
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private void Record(string building,string check,bool ok,string detail) {
      _results.Add(new LategameCheckRecord{Building=building,Check=check,Status=ok?"PASS":"FAIL",Detail=detail,Phase=_phaseName});
      var line=Tag+" "+(ok?"PASS ":"FAIL ")+building+" "+check+": "+detail;
      if(ok)Debug.Log(line);else Debug.LogWarning(line);
    }
    private void Skip(string building,string check,string reason) {
      _results.Add(new LategameCheckRecord{Building=building,Check=check,Status="SKIP",Detail=reason,Phase=_phaseName});
      Debug.Log(Tag+" SKIP "+building+" "+check+": "+reason);
    }
    private bool Guard(Subject s,string check,Action action) {
      try {action();return true;}
      catch(Exception error) {Record(s.Id,check,false,"exception: "+error.Message);return false;}
    }

    // ---------- template helpers ----------
    private TemplateSpec Template(string name)=>_templates.GetAll<TemplateSpec>().SingleOrDefault(t=>t.TemplateName==name);
    private BlockObjectSpec Spec(string name) {
      var template=Template(name);
      Require(template!=null,"Template not loaded: "+name);
      return template.Blueprint.GetSpec<BlockObjectSpec>();
    }
    private static Placement At(Vector3Int c,Orientation o=Orientation.Cw0,bool flip=false)=>new(c,o,new FlipMode(flip));
    private BlockObject Create(BlockObjectSpec spec,Placement p) {
      Require(_validator.BlocksValid(spec,p),"Native placement rejected "+spec.Blueprint.Name+" at "+p.Coordinates+" "+p.Orientation);
      var block=_factory.CreateFinished(new EntitySetup.Builder(spec.Blueprint).AddInitComponent(new FinishedConstructionSiteInit()),p);
      Require(_validation.IsValid(block),"Native object requirements rejected "+spec.Blueprint.Name+" at "+p.Coordinates);
      return block;
    }
    private bool Free(BlockObjectSpec spec,Vector3Int c,Orientation o=Orientation.Cw0)=>
      InPad(c)&&_validator.BlocksValid(spec,At(c,o));
    private bool InPad(Vector3Int c)=>Region.Contains(new Vector2Int(c.x,c.y));
    // Attachments above ground stand on native platform stacks.
    private bool CanSupport(BlockObjectSpec spec,Vector3Int c,Orientation o=Orientation.Cw0) {
      if(!InPad(c))return false;
      for(int z=Ground;z<c.z;z++)if(!_validator.BlocksValid(_platform,At(new Vector3Int(c.x,c.y,z))))return false;
      if(c.z==Ground)return _validator.BlocksValid(spec,At(c,o));
      return !_blocks.GetObjectsAt(c).Any();
    }
    private BlockObject CreateSupported(BlockObjectSpec spec,Vector3Int c,Orientation o=Orientation.Cw0) {
      for(int z=Ground;z<c.z;z++)Create(_platform,At(new Vector3Int(c.x,c.y,z)));
      return Create(spec,At(c,o));
    }
    private bool IsRoad(Vector3Int c)=>_blocks.GetObjectsAt(c).Any(b=>b.GetComponent<TemplateSpec>()?.TemplateName=="Path");
    private static string Id(BaseComponent c)=>c.GetComponent<EntityComponent>().EntityId.ToString();
    private static Direction2D To2D(Direction3D d) {
      Require(d.IsHorizontal(),"Not a horizontal direction: "+d);
      return (Direction2D)(int)d;
    }
    private static Orientation Facing(Direction2D localDirection,Direction2D wanted)=>
      Rotations.Single(o=>o.Transform(localDirection)==wanted);
    private HashSet<Vector3Int> Occupied(BlockObject b)=>
      new(b.PositionedBlocks.GetOccupiedBlocks().Select(k=>k.Coordinates));

    // ---------- lifecycle ----------
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName==Marker),
        "Late-game acceptance requires the marked disposable settlement");
      _district=_entities.Entities.Single(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName==Marker)
        .GetComponent<DistrictCenter>();
      Require(_district,"Fixture marker is not a district center");
      _speed.ChangeSpeed(0);
    }

    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60) {Setup();_started=true;}
        if(!_started)return;
        float hours=(_clock.PartialDayNumber-_phaseTime)*24;
        float real=Time.unscaledTime-_phaseReal;
        foreach(var s in _wave)ObserveWave(s);
        switch(_phase) {
          case 1: if(hours>.25f){CheckNegativeShafts();PlaceConnectors();Phase(2,"connections");} break;
          case 2: if(hours>.3f){CheckConnections();ConnectCables();StartStaticAnimators();Phase(3,"cables");} break;
          case 3: if(hours>.25f&&real>3){CheckCables(true,"joined");CheckStaticAnimators();DisconnectCables();Phase(4,"cables");} break;
          case 4: if(hours>.25f){CheckCables(false,"split after disconnect");ReconnectCables();Phase(5,"cables");} break;
          case 5: if(hours>.25f){CheckCables(true,"rejoined");PrepareWaves();Phase(10,"animation waves");} break;
          case 10: StartWave();Phase(11,_phaseName);break;
          case 11:
            if(_wave.All(s=>s.WorkSampled)||hours>14) {EvaluateWorking(hours>14);LeverOff();Phase(13,_phaseName);}
            break;
          case 13:
            if(hours>.75f&&real>2&&_wave.All(s=>!s.Lever||s.Building.GetComponent<Workplace>().NumberOfAssignedWorkers==0)||hours>4)
              {EvaluateOff();LeverOn();Phase(14,_phaseName);}
            break;
          case 14:
            foreach(var s in _wave.Where(s=>s.Lever&&!s.Returned))s.Returned=Active(s)&&s.Building.GetComponent<Workplace>().NumberOfAssignedWorkers>0;
            if(_wave.All(s=>!s.Lever||s.Returned||!s.WorkSampled)||hours>10) {EvaluateOn();StopWave();Phase(12,_phaseName);}
            break;
          case 12:
            if(_wave.Where(s=>!s.Service).All(s=>!Active(s))&&real>2||hours>4) {
              EvaluateIdle();_wave.Clear();
              if(_waveQueue.Count>0)Phase(10,_phaseName);else Finish();
            }
            break;
        }
        Require(_phase>=10||hours<16,"Late-game connection phase "+_phase+" timed out");
        if(_phase>=10&&_frame%900==0)Debug.Log(Tag+" STATUS phase="+_phase+" wave="+string.Join(",",_wave.Select(s=>
          s.Id+(Active(s)?"(active)":"(idle)")+" workers="+s.Building.GetComponent<Workplace>().NumberOfAssignedWorkers)));
      } catch(Exception error) {
        _finished=true;_speed.ChangeSpeed(0);
        if(_normalHours>0)_hours.WorkedPartOfDay=_normalHours;
        WriteResults();
        Debug.LogError(Tag+" FAILED: "+error);
      }
    }
    private void Phase(int phase,string name) {
      _phase=phase;_phaseName=name;_phaseTime=_clock.PartialDayNumber;_phaseReal=Time.unscaledTime;
      Debug.Log(Tag+" Phase "+phase+" "+name);
    }

    // ---------- setup ----------
    private void Setup() {
      _path=Spec("Path");_shaft=Spec("PowerShaft.IronTeeth");_generator=Spec("DevPowerGenerator");
      _station=Spec("ChargingStation.IronTeeth");_valve=Spec("HorizontalPipeValve.IronTeeth");
      _belt=Spec("ConveyorBeltSp1.IronTeeth");_tubeway=Spec("Tubeway.IronTeeth");_platform=Spec("Platform.IronTeeth");
      _lever=Spec("Lever.IronTeeth");
      _automationRoles=(JObject)JObject.Parse(File.ReadAllText(Path.Combine(Root,"tools","automation_content.json")))["templates"];
      Require(_automationRoles!=null&&_automationRoles.Count>0,"tools/automation_content.json has no template roles");
      _tubewayPowered=_tubeway.Blueprint.HasSpec<TransputProviderSpec>();
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>()))
        e.GetComponent<PausableBuilding>().Pause();
      _normalHours=_hours.WorkedPartOfDay;_hours.WorkedPartOfDay=1;
      _workers.AddRange(_entities.Entities.Where(e=>e.HasComponent<Worker>()&&e.GetComponent<Worker>().WorkerType=="Beaver")
        .Select(e=>e.GetComponent<Worker>()));
      Require(_workers.Count>=2,"Late-game fixture requires at least two adult beaver workers");
      RecordLoadingIssues();
      if(_reload)BindSaved();
      else {
        ResolveSubjects();
        PlanLayout();
        PreparePad();
        foreach(var s in _subjects.Where(s=>s.Skip==null))TrialVariants(s);
        Layout();
        foreach(var s in Placed())PlaceEntrancePath(s);
        foreach(var s in Placed())PlaceValves(s);
        RouteAll();
      }
      foreach(var s in Placed())PlaceNegativeShaft(s);
      _camera.MoveTargetTo(new Vector3(Region.center.x,Ground,Region.center.y));_camera.SetZoomLevel(38,0);
      _camera.HorizontalAngle=200;_camera.VerticalAngle=50;
      Phase(1,"negative shafts");_speed.ChangeSpeed(1);
    }
    private IEnumerable<Subject> Placed()=>_subjects.Where(s=>s.Building);
    // Fixture saves written before blueprint regeneration lose objects that now collide with
    // grown footprints. This harness tolerates that explicitly: it needs only the marked
    // district center and adult beavers; the pad, its road (from the district center's
    // entrance) and every tested object are built by the run itself.
    private void RecordLoadingIssues() {
      Require(AcceptanceLoadingIssues.Reported,"Fixture loading issues were not captured completely; see acceptance-loading-issues.json");
      var dropped=AcceptanceLoadingIssues.DroppedObjects;
      Require(!dropped.Any(d=>d.Name.StartsWith("DistrictCenter",StringComparison.Ordinal)),"The fixture district center was dropped on load");
      Record("Fixture","fixture loading issues",true,dropped.Count==0?"loaded without dropped objects":
        "tolerated "+dropped.Count+" dropped fixture objects (not used by this harness): "+
        string.Join("; ",dropped.Select(d=>d.Name+" "+d.Coordinates)));
    }

    private void ResolveSubjects() {
      var batches=JsonConvert.DeserializeAnonymousType(File.ReadAllText(Path.Combine(Root,"tools","lategame_batches.json")),
        new {integrated=new string[0]});
      Require(batches?.integrated!=null&&batches.integrated.Length>0,"tools/lategame_batches.json has no integrated ids");
      var ids=batches.integrated.Concat(new[]{"GroceryStore","MaterialsLaboratory","Restaurant","Hospital"}).ToList();
      ids.AddRange(_templates.GetAll<TemplateSpec>().Select(t=>t.TemplateName)
        .Where(n=>n.StartsWith("ConcreteSidePlatform",StringComparison.Ordinal)&&n.EndsWith(".IronTeeth",StringComparison.Ordinal))
        .Select(n=>n.Substring(0,n.Length-".IronTeeth".Length)));
      foreach(var id in ids.Distinct()) {
        var template=Template(id+".IronTeeth");
        if(template==null){Skip(id,"installed","no "+id+".IronTeeth template in the loaded package");continue;}
        var s=new Subject{Id=id,Template=template.TemplateName,Blueprint=template.Blueprint,
          Spec=template.Blueprint.GetSpec<BlockObjectSpec>()};
        if(s.Blueprint.HasSpec<UnderstructureConstraintSpec>()) {
          var names=s.Blueprint.GetSpec<UnderstructureConstraintSpec>().UnderstructureTemplateNames;
          var available=names.Select(Template).FirstOrDefault(t=>t!=null);
          if(available==null)s.Skip="requires understructure "+string.Join("/",names)+
            ", whose template is not loaded in the Game context (map-authored object only)";
          else if(available.Blueprint.GetSpec<BlockObjectSpec>().Size.x!=s.Spec.Size.x||
                  available.Blueprint.GetSpec<BlockObjectSpec>().Size.y!=s.Spec.Size.y)
            s.Skip="understructure "+available.TemplateName+" footprint differs from the building footprint";
        }
        if(s.Skip!=null)Skip(id,"placement",s.Skip);
        _subjects.Add(s);
      }
      Require(_subjects.Any(s=>s.Skip==null),"No installed late-game subjects to test");
      Debug.Log(Tag+" SUBJECTS "+string.Join(", ",_subjects.Select(s=>s.Id+(s.Skip!=null?"(skip)":""))));
    }

    private void PreparePad() {
      var doomed=new List<EntityComponent>();
      foreach(var e in _entities.Entities.ToList()) {
        var b=e.GetComponent<BlockObject>();
        if(!b||!b.Positioned)continue;
        bool inside=b.PositionedBlocks.GetAllBlocks().Any(k=>Region.Contains(new Vector2Int(k.Coordinates.x,k.Coordinates.y)));
        if(!inside)continue;
        bool natural=e.HasComponent<NaturalResource>();
        var template=e.GetComponent<TemplateSpec>()?.TemplateName??"";
        bool blockage=template=="Blockage"||template.StartsWith("RuinColumn",StringComparison.Ordinal);
        Require(natural||blockage,"Late-game pad contains an unexpected object: "+e.GetComponent<TemplateSpec>()?.TemplateName+
          " at "+b.Coordinates);
        doomed.Add(e);
      }
      foreach(var e in doomed)_entityService.Delete(e);
      for(int x=Region.xMin;x<Region.xMax;x++)for(int y=Region.yMin;y<Region.yMax;y++) {
        var surfaces=_terrain.GetAllHeightsInCell(new Vector2Int(x,y)).Where(c=>c.z>Ground).OrderByDescending(c=>c.z).ToArray();
        foreach(var top in surfaces)_terrain.UnsetTerrain(new Vector3Int(x,y,top.z-1),top.z-Ground);
        int height=_terrain.GetTerrainHeight(new Vector3Int(x,y,0));
        if(height<Ground)_terrain.SetTerrain(new Vector3Int(x,y,height),Ground-height);
        Require(_terrain.GetTerrainHeight(new Vector3Int(x,y,0))==Ground&&
          !Enumerable.Range(Ground,_terrain.Size.z-Ground).Any(z=>_terrain.Underground(new Vector3Int(x,y,z))),
          "Native test terrain is not a clear level pad at "+x+","+y);
        Require(_water.WaterDepth(new Vector3Int(x,y,Ground))<=0,"Late-game pad is wet at "+x+","+y);
      }
      Debug.Log(Tag+" PASS pad cleared of "+doomed.Count+" natural resources, blockages and ruins and levelled to height "+Ground);
    }

    private IEnumerable<(Orientation O,bool F)> Variants(Subject s) {
      foreach(var o in Rotations) {
        yield return (o,false);
        if(s.Spec.Flippable)yield return (o,true);
      }
    }
    private static RectInt Bounds(BlockObjectSpec spec,Placement p) {
      var blocks=spec.GetBlocks(p).ToArray();
      int x0=blocks.Min(b=>b.Coordinates.x),y0=blocks.Min(b=>b.Coordinates.y);
      return new RectInt(x0,y0,blocks.Max(b=>b.Coordinates.x)-x0+1,blocks.Max(b=>b.Coordinates.y)-y0+1);
    }
    private BlockObjectSpec UnderstructureSpec(Subject s) {
      if(!s.Blueprint.HasSpec<UnderstructureConstraintSpec>())return null;
      return s.Blueprint.GetSpec<UnderstructureConstraintSpec>().UnderstructureTemplateNames.Select(Template)
        .First(t=>t!=null).Blueprint.GetSpec<BlockObjectSpec>();
    }
    private BlockObject CreateBuilding(Subject s,Placement p) {
      BlockObject under=null;
      var underSpec=UnderstructureSpec(s);
      if(underSpec!=null)under=Create(underSpec,p);
      try {
        var b=Create(s.Spec,p);
        if(under)s.Understructure=under;
        return b;
      } catch {
        if(under)_entityService.Delete(under);
        throw;
      }
    }
    private void CheckOccupancy(Subject s,BlockObject b,string variant) {
      var expected=s.Spec.GetBlocks(b.Placement).Where(k=>k.IsOccupied).Select(k=>k.Coordinates).ToList();
      var missing=expected.Where(c=>!_blocks.GetObjectsAt(c).Contains(b)).Take(6).ToList();
      Require(missing.Count==0,"occupied cells not registered "+string.Join(" ",missing)+" ("+variant+")");
      Require(Occupied(b).SetEquals(expected),"registered occupancy differs from blueprint ("+variant+")");
      if(s.Spec.Entrance.HasEntrance) {
        var entrance=b.TransformCoordinates(s.Spec.Entrance.Coordinates);
        Require(b.HasEntrance&&b.PositionedEntrance.Coordinates==entrance,"positioned entrance differs from blueprint ("+variant+")");
        if(entrance.z==Ground&&!IsRoad(entrance))
          Require(_validator.BlocksValid(_path,At(entrance)),"native Path cannot be placed on entrance "+entrance+" ("+variant+")");
      }
    }
    private void TrialVariants(Subject s) {
      int passed=0;var failures=new List<string>();
      foreach(var (o,f) in Variants(s)) {
        string variant=o+(f?" flipped":"");
        try {
          var probe=Bounds(s.Spec,At(Vector3Int.zero,o,f));
          var anchor=new Vector3Int(Pad.x-probe.xMin,Pad.y-probe.yMin,Ground);
          var b=CreateBuilding(s,At(anchor,o,f));
          try {CheckOccupancy(s,b,variant);passed++;}
          finally {
            _entityService.Delete(b);
            if(s.Understructure){_entityService.Delete(s.Understructure);s.Understructure=null;}
          }
        } catch(Exception error) {failures.Add(variant+": "+error.Message);}
      }
      Record(s.Id,"placement variants",failures.Count==0,passed+" native placements on flat ground with registered occupancy/entrance"+
        (failures.Count>0?"; failures: "+string.Join(" | ",failures):""));
    }

    // First-fit plan over the largest clearable pad using each installed blueprint's real
    // footprint, chosen variant and margin; the pad is then cleared only as far north as needed.
    private void PlanLayout() {
      var full=new RectInt(PadX,PadY,PadWidth,PadMaxY-PadY+1);
      int index=0,top=PadY+1;
      foreach(var s in _subjects.Where(s=>s.Skip==null).OrderByDescending(s=>s.Spec.Size.x*s.Spec.Size.y).ToList()) {
        var variants=Variants(s).ToList();
        (s.Orientation,s.Flip)=variants[index%variants.Count];index++;
        s.Margin=s.IsGenerator?3:2;
        var probe=Bounds(s.Spec,At(Vector3Int.zero,s.Orientation,s.Flip));
        int m=s.Margin;bool done=false;
        for(int y=full.yMin+m;y+probe.height+m<=full.yMax&&!done;y++)
          for(int x=full.xMin+m;x+probe.width+m<=full.xMax&&!done;x++) {
            var rect=new RectInt(x-m,y-m,probe.width+2*m,probe.height+2*m);
            if(_allocated.Any(a=>a.Overlaps(rect)))continue;
            s.Allocation=rect;s.Anchor=new Vector3Int(x-probe.xMin,y-probe.yMin,Ground);
            _allocated.Add(rect);top=Math.Max(top,rect.yMax);done=true;
          }
        if(!done) {
          s.Skip="no space even in the largest clearable pad "+full;
          Record(s.Id,"final placement",false,s.Skip+" for "+probe.width+"x"+probe.height+" plus margin "+m);
        }
      }
      // One spare row north of the last allocation for the persistence lever.
      Region=new RectInt(PadX,PadY,PadWidth,Math.Min(top+1,PadMaxY+1)-PadY);
      Debug.Log(Tag+" pad sized from installed footprints: x "+Region.xMin+".."+(Region.xMax-1)+", y "+Region.yMin+".."+(Region.yMax-1)+
        " ("+_allocated.Sum(a=>a.width*a.height)+" allocated of "+Region.width*Region.height+" cells)");
    }
    private void Layout() {
      foreach(var s in _subjects.Where(s=>s.Skip==null&&s.Allocation.width>0).ToList()) {
        var p=At(s.Anchor,s.Orientation,s.Flip);
        try {s.Building=CreateBuilding(s,p);}
        catch(Exception error){Record(s.Id,"final placement",false,error.Message);continue;}
        Guard(s,"final occupancy",()=>CheckOccupancy(s,s.Building,s.Orientation+(s.Flip?" flipped":"")));
        Guard(s,"freed cells",()=>CheckFreedCells(s));
        Record(s.Id,"final placement",true,"at "+s.Building.Coordinates+" "+s.Orientation+(s.Flip?" flipped":""));
        if(s.Building.HasComponent<Workplace>())Idle(s);
      }
    }
    // Ground the 2026-10-22 no-forced-decoration pass freed inside a building's new bounds
    // (tools/lategame_freed_cells.json insideCells, new local frame; its static check is
    // tools/validate_lategame_freed_cells.mjs) must take a native Path and a 1x1 decoration.
    // Checked by native placement validation right after the final placement, before the
    // harness lays entrance paths, valves, shafts or belts. Cells outside the new bounds are
    // plain pad ground here and need no building-specific check.
    private JObject _freedCells;
    private void CheckFreedCells(Subject s) {
      _freedCells??=(JObject)JObject.Parse(File.ReadAllText(Path.Combine(Root,"tools","lategame_freed_cells.json")))["buildings"];
      Require(_freedCells!=null,"tools/lategame_freed_cells.json has no buildings");
      if(!(_freedCells[s.Id] is JObject entry))return;
      var after=entry["footprintAfter"].ToObject<int[]>();
      Require(after.Length==3&&new Vector3Int(after[0],after[1],after[2])==s.Spec.Size,
        "installed footprint "+s.Spec.Size+" differs from the recorded "+string.Join("x",after));
      var cells=entry["insideCells"].ToObject<int[][]>().Select(c=>new Vector3Int(c[0],c[1],0)).ToArray();
      if(cells.Length==0){Skip(s.Id,"freed cells","no freed ground inside the "+string.Join("x",after.Take(2))+" bounds");return;}
      var failures=FreedCellProbe.Check(_templates,_validator,s.Building,cells,out var accepted);
      Record(s.Id,"freed cells accept Path and 1x1 decoration",failures.Count==0,failures.Count==0
        ?cells.Length+" cells (local cell decoration): "+accepted:string.Join("; ",failures));
    }
    private void Idle(Subject s) {
      var workplace=s.Building.GetComponent<Workplace>();
      while(workplace.DesiredWorkers>0)workplace.DecreaseDesiredWorkers();
      foreach(var w in workplace.AssignedWorkers.ToList())w.Unemploy();
    }

    private void PlaceEntrancePath(Subject s) {
      if(!s.Building.HasEntrance){Skip(s.Id,"entrance","blueprint has no entrance");return;}
      var c=s.Building.PositionedEntrance.Coordinates;
      if(c.z!=Ground){Record(s.Id,"entrance path",false,"entrance "+c+" is not on the fixture ground layer");return;}
      if(!Free(_path,c)){Record(s.Id,"entrance path",false,"native Path rejected at the entrance cell "+c);return;}
      s.EntrancePath=Create(_path,At(c));
      Record(s.Id,"entrance path",true,"native Path placed on entrance "+c+" facing "+s.Building.PositionedEntrance.Direction2D);
    }

    // The authored socket (Ports[0], the study/contract socket) is always
    // tested. connection_content.mjs appends a port on every other flat
    // exterior face; one of them, the first ground-level horizontal face with a
    // free valve cell, is tested as a sample (a valve on every face would wall
    // the building in).
    private void PlaceValves(Subject s) {
      if(!s.Blueprint.HasSpec<BuildingPipeTargetPortsSpec>())return;
      var ports=s.Blueprint.GetSpec<BuildingPipeTargetPortsSpec>().Ports;
      bool sampled=false;
      for(int i=0;i<ports.Length&&!(i>0&&sampled);i++) {
        var port=ports[i];
        foreach(var local in port.Directions.GetEnumerator().AsEnumerable()) {
          var cell=s.Building.TransformCoordinates(port.Coordinates);
          var dir=s.Building.TransformDirection(local);
          var test=new ValveTest{Port=cell,Direction=dir,State=port.State};
          string name=(i==0?"pipe port ":"generated pipe port ")+port.Coordinates+" "+local+" "+port.State;
          var at=cell+dir.ToOffset();
          if(i==0) {
            if(!dir.IsHorizontal()){Skip(s.Id,name,"vertical pipe ports are outside this fixture");continue;}
            var o0=Facing(Direction2D.Down,To2D(dir));
            if(!CanSupport(_valve,at,o0)){Record(s.Id,name,false,"no free native cell for a pipe valve at "+at);continue;}
            test.Valve=CreateSupported(_valve,at,o0);s.Valves.Add(test);
            continue;
          }
          if(sampled||!dir.IsHorizontal()||at.z!=Ground)continue;
          if(s.Valves.Any(v=>(v.Valve.Coordinates-at).sqrMagnitude<=1))continue;
          var o=Facing(Direction2D.Down,To2D(dir));
          if(!CanSupport(_valve,at,o))continue;
          test.Valve=CreateSupported(_valve,at,o);s.Valves.Add(test);sampled=true;
        }
      }
      if(ports.Length>1&&!sampled)Skip(s.Id,"generated pipe port","no generated ground-level horizontal port has a free valve cell");
    }

    // Native Path route from each entrance to the existing district road.
    private void RouteAll() {
      var center=_district.GetComponent<BlockObject>();
      Require(center.HasEntrance,"Fixture district center has no entrance");
      var start=center.PositionedEntrance.Coordinates;
      if(!IsRoad(start)) {
        Require(_validator.BlocksValid(_path,At(start)),"No path at the district center entrance "+start+" and none can be placed");
        Create(_path,At(start));
      }
      _network.Add(start);
      foreach(var s in Placed().Where(s=>s.EntrancePath).OrderBy(s=>Vector3Int.Distance(s.EntrancePath.Coordinates,start)).ToList()) {
        var route=Route(s.EntrancePath.Coordinates);
        if(route==null){Record(s.Id,"road route",false,"no native Path route from the entrance to the fixture road");continue;}
        int placed=0;
        foreach(var c in route)if(!IsRoad(c)){Create(_path,At(c));placed++;}
        foreach(var c in route)_network.Add(c);
        Record(s.Id,"road route",true,"joined the district center entrance road with "+placed+" new native Path tiles");
      }
    }
    private bool Routable(Vector3Int c)=>
      RouteArea.Contains(new Vector2Int(c.x,c.y))&&
      (IsRoad(c)||_validator.BlocksValid(_path,At(c)));
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
          if(parent.ContainsKey(n)||!Routable(n))continue;
          parent[n]=c;queue.Enqueue(n);
        }
      }
      return null;
    }

    // ---------- power ----------
    private IEnumerable<Transput> OfferedGroundFaces(Subject s) {
      var occupied=Occupied(s.Building);
      return s.Node.Transputs.Where(t=>t.Direction.IsHorizontal()&&occupied.Contains(t.Coordinates)&&!occupied.Contains(t.Target))
        .OrderBy(t=>t.Coordinates.z);
    }
    private void PlaceNegativeShaft(Subject s) {
      if(s.NodeSpec==null)return;
      var occupied=Occupied(s.Building);
      var targets=new HashSet<Vector3Int>(s.Node.Transputs.Select(t=>t.Target));
      foreach(var c in occupied.Where(c=>c.z==Ground).OrderBy(c=>c.x).ThenBy(c=>c.y))
        foreach(var d in new[]{Direction3D.Down,Direction3D.Left,Direction3D.Up,Direction3D.Right}) {
          var n=c+d.ToOffset();
          if(occupied.Contains(n)||targets.Contains(n)||!Free(_shaft,n))continue;
          if(new[]{Vector3Int.left,Vector3Int.right,Vector3Int.up,Vector3Int.down}.Select(o=>n+o)
              .Any(k=>!occupied.Contains(k)&&_blocks.GetObjectsWithComponentAt<MechanicalNode>(k).Any()))continue;
          s.NegShaft=Create(_shaft,At(n));
          return;
        }
      Skip(s.Id,"unoffered face rejects shaft","every free ground-level face is an offered transput");
    }
    private void CheckNegativeShafts() {
      foreach(var s in Placed().Where(s=>s.NegShaft)) {
        var shaft=s.NegShaft.GetComponent<MechanicalNode>();
        bool connected=s.Node.Transputs.Any(t=>t.ConnectedNode==shaft)||shaft.Graph==s.Node.Graph;
        Record(s.Id,"unoffered face rejects shaft",!connected,"vanilla shaft at "+s.NegShaft.Coordinates+
          (connected?" joined the building graph":" stayed outside the building graph"));
        _entityService.Delete(s.NegShaft);s.NegShaft=null;
      }
    }

    private void PlaceConnectors() {
      if(_reload)return;
      foreach(var s in Placed()) {
        if(s.NodeSpec!=null)Guard(s,"power attachment",()=>PlacePower(s));
        if(s.Building.HasComponent<Inventories>())Guard(s,"belt attachment",()=>PlaceBelts(s));
      }
      // Cable sources last, so none can end up beside a later shaft, belt or source.
      foreach(var s in Placed().Where(s=>s.NodeSpec!=null))Guard(s,"power line attachment",()=>PlaceCableGenerator(s));
      foreach(var s in Placed())Guard(s,"automation lever",()=>PlaceLever(s));
      // A separate unconnected lever left Off at the end proves lever state persistence.
      for(int x=Region.xMax-1;x>=Region.xMin&&!_persistenceLever;x--) {
        var c=new Vector3Int(x,Region.yMax-1,Ground);
        if(Free(_lever,c))_persistenceLever=Create(_lever,At(c));
      }
      Require(_persistenceLever,"No free cell for the persistence lever");
    }
    private void PlacePower(Subject s) {
      var faces=OfferedGroundFaces(s).ToList();
      Record(s.Id,"offered shaft faces",faces.Count>0,faces.Count+" horizontal TransputProviderSpec faces on occupied cells ("+
        s.Node.Transputs.Length+" transputs total)");
      if(faces.Count==0)return;
      var used=new HashSet<Vector3Int>();
      foreach(var t in faces) {
        var n=t.Target;var beyond=n+t.Direction.ToOffset();
        if(!CanSupport(_shaft,n))continue;
        if(s.IsGenerator) {
          var o=Facing(Direction2D.Up,To2D(t.Direction.Across()));
          if(!CanSupport(_station,beyond,o))continue;
          s.Shaft=CreateSupported(_shaft,n);s.Source=CreateSupported(_station,beyond,o);
        } else {
          if(!CanSupport(_generator,beyond))continue;
          s.Shaft=CreateSupported(_shaft,n);s.Source=CreateSupported(_generator,beyond);
        }
        used.Add(n);used.Add(beyond);break;
      }
      PlaceRoofShaft(s);
      if(!s.Shaft){Record(s.Id,"shaft placement",false,"no offered face has free cells for a shaft and its "+
        (s.IsGenerator?"consumer":"source"));return;}
      if(!_tubewayPowered){Skip(s.Id,"Powered Tubeway","Tubeway.IronTeeth has no TransputProviderSpec (Powered Tubeway inactive)");return;}
      foreach(var t in faces) {
        if(used.Contains(t.Target)||!CanSupport(_tubeway,t.Target))continue;
        if(new[]{Vector3Int.left,Vector3Int.right,Vector3Int.up,Vector3Int.down}.Any(o=>used.Contains(t.Target+o)))continue;
        s.Tubeway=CreateSupported(_tubeway,t.Target);return;
      }
      Skip(s.Id,"Powered Tubeway","no second offered face with a free, isolated cell");
    }
    // Roof faces (connection_content.mjs): a vanilla PowerShaft standing on a
    // Top transput's stackable roof block meets it with its Bottom transput.
    private void PlaceRoofShaft(Subject s) {
      var occupied=Occupied(s.Building);
      var tops=s.Node.Transputs.Where(t=>t.Direction==Direction3D.Top&&occupied.Contains(t.Coordinates)&&!occupied.Contains(t.Target)).ToList();
      if(tops.Count==0){Skip(s.Id,"roof shaft connects","no Top transput (no flat roof at a cell boundary)");return;}
      var top=tops.FirstOrDefault(t=>Free(_shaft,t.Target));
      if(top==null){Record(s.Id,"roof shaft placement",false,tops.Count+" Top transputs, none with a placeable PowerShaft above");return;}
      s.RoofShaft=Create(_shaft,At(top.Target));
    }
    private void PlaceBelts(Subject s) {
      var occupied=Occupied(s.Building);
      var mechanical=new HashSet<Vector3Int>(new[]{s.Shaft,s.Source,s.Tubeway,s.RoofShaft}.Where(b=>b).Select(b=>b.Coordinates));
      var cells=occupied.Where(c=>c.z==Ground).OrderBy(c=>c.y).ThenBy(c=>c.x).SelectMany(c=>
        new[]{Direction3D.Down,Direction3D.Left,Direction3D.Up,Direction3D.Right}.Select(d=>(c,d))).ToList();
      foreach(var role in new[]{"in","out"}) {
        foreach(var (c,d) in cells) {
          var n=c+d.ToOffset();
          if(occupied.Contains(n)||mechanical.Contains(n))continue;
          var toBuilding=To2D(d.Across());
          var o=role=="in"?Facing(Direction2D.Down,toBuilding):Facing(Direction2D.Up,toBuilding);
          if(!Free(_belt,n,o))continue;
          var belt=Create(_belt,At(n,o));mechanical.Add(n);
          if(role=="in")s.BeltIn=belt;else s.BeltOut=belt;
          break;
        }
      }
      if(!s.BeltIn||!s.BeltOut)Record(s.Id,"belt placement",false,"no free ground faces for both belt ends");
    }
    private void PlaceCableGenerator(Subject s) {
      var line=s.Building.GetComponent<PowerLineComponent>();
      if(!line){Skip(s.Id,"Power Lines","building has no PowerLineComponent");return;}
      var r=Bounds(s.Spec,s.Building.Placement);
      var best=(Cell:default(Vector3Int),Distance:float.MaxValue);
      for(int x=r.xMin-3;x<r.xMax+3;x++)for(int y=r.yMin-3;y<r.yMax+3;y++) {
        if(x>=r.xMin-1&&x<r.xMax+1&&y>=r.yMin-1&&y<r.yMax+1)continue;
        var c=new Vector3Int(x,y,Ground);
        if(!Free(_generator,c))continue;
        if(new[]{Vector3Int.left,Vector3Int.right,Vector3Int.up,Vector3Int.down}.Any(o=>
            _blocks.GetObjectsWithComponentAt<MechanicalNode>(c+o).Any()||
            _blocks.GetObjectsWithComponentAt<MechanicalNode>(c+o+Vector3Int.forward).Any()))continue;
        var anchor=new Vector3(x+.5f,y+.5f,Ground+1.98f);
        float distance=line.ConnectionLocations.Min(a=>Vector3.Distance(a,anchor));
        if(distance<best.Distance)best=(c,distance);
      }
      if(best.Distance==float.MaxValue){Record(s.Id,"Power Lines",false,"no isolated free cell for a cable source");return;}
      s.CableGen=Create(_generator,At(best.Cell));
      // Membership only: the cable source supplies no power, so it cannot mask shaft or reactor checks.
      s.CableGen.GetComponent<MechanicalNode>().SetOutputMultiplier(0);
    }

    // ---------- connection checks ----------
    private void CheckConnections() {
      foreach(var s in Placed()) {
        Guard(s,"entrance",()=>CheckEntrance(s));
        if(s.NodeSpec!=null)Guard(s,"power",()=>CheckPower(s));
        Guard(s,"pipes",()=>CheckPipes(s));
        if(s.Building.HasComponent<Inventories>())Guard(s,"belts",()=>CheckBelts(s));
        Guard(s,"native props",()=>CheckProps(s));
        Guard(s,"automation",()=>CheckAutomation(s));
      }
    }
    private void CheckEntrance(Subject s) {
      if(!s.Building.HasEntrance)return;
      var district=s.Building.GetComponent<DistrictBuilding>();
      Record(s.Id,"district connection",district&&district.District==_district,
        "native district "+(district&&district.District?district.District.GetComponent<NamedEntity>().EntityName:"none"));
      var accessible=s.Building.GetComponent<BuildingAccessible>();
      if(accessible)Record(s.Id,"native access",accessible.Accessible.UnblockedSingleAccess.HasValue,
        "unblocked single access "+accessible.Accessible.UnblockedSingleAccess);
      var blockable=s.Building.GetComponent<BlockableEntranceBuilding>();
      if(blockable)Record(s.Id,"entrance not blocked",!blockable.IsEntranceBlocked()&&!blockable.IsEntranceInaccessible(),
        "blocked="+blockable.IsEntranceBlocked()+" inaccessible="+blockable.IsEntranceInaccessible());
      var e=s.Building.PositionedEntrance;
      bool stub=_connections.CanConnectInDirection(e.Coordinates,e.Direction2D.Across());
      var path=s.EntrancePath?s.EntrancePath:_blocks.GetObjectsAt(e.Coordinates).FirstOrDefault(b=>b.GetComponent<TemplateSpec>()?.TemplateName=="Path");
      string model=path?string.Join(",",path.GameObject.GetComponentsInChildren<Transform>(false)
        .Where(t=>t.parent==path.Transform||t.parent&&t.parent.parent==path.Transform).Select(t=>t.name)):"no path";
      Record(s.Id,"door path stub",stub&&path,"DynamicPathModel connection toward the doorstep="+stub+"; active path parts "+model);
    }
    private void CheckPower(Subject s) {
      var node=s.Node;
      if(!s.Shaft){Skip(s.Id,"shaft connects","no shaft placed");return;}
      var shaft=s.Shaft.GetComponent<MechanicalNode>();
      bool linked=node.Transputs.Any(t=>t.ConnectedNode==shaft);
      Record(s.Id,"shaft connects",linked&&shaft.Graph==node.Graph,"vanilla PowerShaft at "+s.Shaft.Coordinates+
        " transput link="+linked+" same graph="+(shaft.Graph==node.Graph));
      var source=s.Source.GetComponent<MechanicalNode>();
      if(s.IsGenerator)Record(s.Id,"consumer on generator graph",source.Graph==node.Graph,
        "vanilla ChargingStation consumer joined the generator graph="+(source.Graph==node.Graph));
      else Record(s.Id,"consumer powered",source.Graph==node.Graph&&node.Powered&&node.Graph.PowerSupply>0,
        "DevPowerGenerator graph supply="+node.Graph?.PowerSupply+" demand="+node.Graph?.PowerDemand+" efficiency="+node.PowerEfficiency);
      if(s.RoofShaft) {
        var roof=s.RoofShaft.GetComponent<MechanicalNode>();
        bool onRoof=node.Transputs.Any(t=>t.Direction==Direction3D.Top&&t.ConnectedNode==roof);
        Record(s.Id,"roof shaft connects",onRoof&&roof.Graph==node.Graph,"vanilla PowerShaft on the roof at "+s.RoofShaft.Coordinates+
          " Top transput link="+onRoof+" same graph="+(roof.Graph==node.Graph));
      }
      if(s.Tubeway) {
        var tube=s.Tubeway.GetComponent<MechanicalNode>();
        bool direct=node.Transputs.Any(t=>t.ConnectedNode==tube);
        Record(s.Id,"Powered Tubeway connects",direct&&tube.Graph==node.Graph,"Tubeway at "+s.Tubeway.Coordinates+
          " direct link="+direct);
      }
    }
    private void CheckPipes(Subject s) {
      foreach(var v in s.Valves) {
        string name="pipe port "+v.Port+" "+v.Direction+" "+v.State;
        var valve=v.Valve.GetComponent<ExtractionPipe>();
        var target=s.Building.GetComponent<BuildingPipeTarget>();
        Require(target,"building has BuildingPipeTargetPortsSpec but no BuildingPipeTarget");
        bool give=(v.State&PipePortState.OpenIn)!=PipePortState.Closed;
        bool take=(v.State&PipePortState.OpenOut)!=PipePortState.Closed;
        var manufactory=s.Building.GetComponent<Manufactory>();
        var recipes=manufactory?manufactory.ProductionRecipes.ToList():new List<RecipeSpec>{null};
        string found=null;var tried=new List<string>();
        foreach(var recipe in recipes) {
          if(recipe!=null&&manufactory.CurrentRecipe!=recipe)manufactory.SetRecipe(recipe);
          valve.InvalidateIoTargets();
          var connection=give?valve.FindInletTarget():valve.FindOutletTarget();
          var liquids=connection!=null?connection.GetLiquidIds().ToList():new List<string>();
          tried.Add((recipe?.Id??"-")+"=>"+(connection==null?"none":connection.Target.BlockObject==s.Building?"["+string.Join("/",liquids)+"]":"other"));
          if(connection!=null&&connection.Target.BlockObject==s.Building&&liquids.Count>0){found=recipe?.Id??"-";break;}
        }
        Record(s.Id,name,found!=null,"Timber Pipes valve at "+v.Valve.Coordinates+(give?" inlet":" outlet")+" resolved: "+string.Join("; ",tried));
        var pipe=valve.Pipe;
        var declared=s.Valves.Where(x=>x.Port==v.Port).Select(x=>x.Direction).ToList();
        bool wrongFace=new[]{Direction3D.Down,Direction3D.Left,Direction3D.Up,Direction3D.Right}.Where(d=>!declared.Contains(d))
          .All(d=>target.TryConnecting(pipe,new PipePortDefinition(v.Port,d),give)==null&&
                  target.TryConnecting(pipe,new PipePortDefinition(v.Port,d),!give)==null);
        bool wrongFlow=give&&take||target.TryConnecting(pipe,new PipePortDefinition(v.Port,v.Direction),!give)==null;
        Record(s.Id,name+" rejects wrong face/flow",wrongFace&&wrongFlow,"wrong face rejected="+wrongFace+" opposite flow rejected="+wrongFlow);
      }
    }
    private void CheckBelts(Subject s) {
      var occupied=Occupied(s.Building);
      bool intakeOnly=s.Blueprint.HasSpec<GroceryStoreSpec>();
      if(s.BeltIn) {
        var belt=s.BeltIn.GetComponent<BeltCarrier>();
        bool ok=occupied.Contains(belt.OutPort.Target)&&belt.Sim.Output!=null&&!(belt.Sim.Output is SimBelt);
        Record(s.Id,"belt delivers into inventory",ok,"belt at "+s.BeltIn.Coordinates+" out->"+belt.OutPort.Target+
          " link="+(belt.Sim.Output==null?"none":belt.Sim.Output.GetType().Name));
      }
      if(s.BeltOut) {
        var belt=s.BeltOut.GetComponent<BeltCarrier>();
        bool linked=occupied.Contains(belt.InPort.Target)&&belt.Sim.Input!=null;
        Record(s.Id,intakeOnly?"belt outbound refused (intake-only)":"belt takes from inventory",intakeOnly?!linked:linked,
          "belt at "+s.BeltOut.Coordinates+" in<-"+belt.InPort.Target+" source="+(belt.Sim.Input==null?"none":belt.Sim.Input.GetType().Name));
      }
    }
    private static bool UnderProp(Transform t,Transform root,HashSet<string> props) {
      for(var p=t;p&&p!=root;p=p.parent)if(props.Contains(p.name))return true;
      return false;
    }
    private void CheckProps(Subject s) {
      var spec=s.Building.GetComponent<NativeBuildingPropsSpec>();
      if(spec==null)return;
      var finished=s.Building.GetComponent<BuildingModel>().FinishedModel.transform;
      var r=Bounds(s.Spec,s.Building.Placement);
      foreach(var prop in spec.Props) {
        var nodes=finished.GetComponentsInChildren<Transform>(true).Where(t=>t.name==prop.Node).ToArray();
        if(nodes.Length!=1){Record(s.Id,"prop "+prop.Node,false,nodes.Length+" transforms named "+prop.Node);continue;}
        var n=nodes[0];
        var grid=CoordinateSystem.WorldToGrid(n.position);
        bool placed=Vector3.Distance(n.localPosition,prop.Position)<.0005f&&Vector3.Distance(n.localScale,prop.Scale)<.0005f;
        bool inside=grid.x>=r.xMin-1&&grid.x<=r.xMax+1&&grid.y>=r.yMin-1&&grid.y<=r.yMax+1;
        var renderers=n.GetComponentsInChildren<Renderer>(true);
        bool visible=n.gameObject.activeInHierarchy&&renderers.Length>0&&renderers.Any(x=>x.enabled);
        var animators=n.GetComponentsInChildren<MonoBehaviour>(true).OfType<IAnimator>().ToArray();
        Record(s.Id,"prop "+prop.Node,placed&&inside&&visible,"local "+n.localPosition+" grid "+grid+" renderers="+renderers.Length+
          " active="+n.gameObject.activeInHierarchy+(animators.Length>0?" animators="+string.Join(",",animators.Select(a=>a.AnimationName+(a.Enabled?":on":":off"))):""));
      }
    }

    // ---------- power lines ----------
    private IEnumerable<Subject> Cabled()=>Placed().Where(s=>s.CableGen);
    private void ConnectCables() {
      foreach(var s in Cabled()) {
        var a=s.CableGen.GetComponent<PowerLineComponent>();var b=s.Building.GetComponent<PowerLineComponent>();
        if(_reload) {
          bool kept=_lines.GetConnectedPowerLines(a).Contains(b);
          s.CableConnected=kept;
          Record(s.Id,"Power Lines saved connection",kept,"saved cable source "+s.CableGen.Coordinates+" still connected="+kept);
          continue;
        }
        Record(s.Id,"Power Lines graph separate before cable",s.CableGen.GetComponent<MechanicalNode>().Graph!=s.Node.Graph,
          "cable source at "+s.CableGen.Coordinates+" not on the building graph before connecting");
        var check=_lines.EvaluateConnection(a,b);
        Record(s.Id,"Power Lines reach",check.CanConnect,"distance "+check.Distance.ToString("0.##")+" max "+check.MaxDistance.ToString("0.##")+
          " slots="+check.HasSlot+" anchors "+string.Join(" ",b.ConnectionLocations));
        if(check.CanConnect){_lines.Connect(a,b);s.CableConnected=true;}
      }
    }
    private void CheckCables(bool expected,string label) {
      foreach(var s in Cabled().Where(s=>s.CableConnected)) {
        var a=s.CableGen.GetComponent<PowerLineComponent>();var b=s.Building.GetComponent<PowerLineComponent>();
        bool linked=_lines.GetConnectedPowerLines(a).Contains(b);
        if(linked!=expected){Record(s.Id,"Power Lines "+label,false,"native cable link present="+linked);continue;}
        bool joined=s.CableGen.GetComponent<MechanicalNode>().Graph==s.Node.Graph;
        Record(s.Id,"Power Lines "+label,joined==expected,"cable source graph joined="+joined);
      }
    }
    private void DisconnectCables() {
      foreach(var s in Cabled().Where(s=>s.CableConnected)) {
        var a=s.CableGen.GetComponent<PowerLineComponent>();var b=s.Building.GetComponent<PowerLineComponent>();
        foreach(var c in _lines.GetConnections(a).Where(c=>c.A==b||c.B==b).ToList())_lines.DisconnectConnection(c);
      }
    }
    private void ReconnectCables() {
      foreach(var s in Cabled().Where(s=>s.CableConnected)) {
        var a=s.CableGen.GetComponent<PowerLineComponent>();var b=s.Building.GetComponent<PowerLineComponent>();
        if(_lines.EvaluateConnection(a,b).CanConnect)_lines.Connect(a,b);
      }
    }

    // ---------- animation ----------
    private static string PathOf(IAnimator a,Transform root) {
      var t=((MonoBehaviour)a).transform;var parts=new List<string>();
      for(var p=t;p&&p!=root;p=p.parent)parts.Insert(0,p.name);
      return string.Join("/",parts);
    }
    private void StartStaticAnimators() {
      foreach(var s in Placed()) {
        bool ambient=s.Building.HasComponent<AmbientAnimationSpec>();
        bool grocery=s.Building.HasComponent<GroceryStoreSpec>();
        if(!ambient&&!grocery)continue;
        var finished=s.Building.GetComponent<BuildingModel>().FinishedModel;
        foreach(var a in finished.GetComponentsInChildren<MonoBehaviour>(true).OfType<IAnimator>()) {
          if(UnderProp(((MonoBehaviour)a).transform,finished.transform,PropNodes(s)))continue;
          _staticAnimators.Add((s,a,a.Time,a.RepeatedTime,PathOf(a,finished.transform)));
        }
        if(!_staticAnimators.Any(x=>x.Subject==s))Record(s.Id,ambient?"ambient animation":"sign animation",false,"finished model has no animator");
      }
    }
    private void CheckStaticAnimators() {
      foreach(var group in _staticAnimators.GroupBy(x=>x.Subject)) {
        var s=group.Key;
        bool ok=group.All(x=>x.Animator.Enabled&&(x.Animator.Time!=x.Time||x.Animator.RepeatedTime!=x.Repeated));
        Record(s.Id,s.Building.HasComponent<GroceryStoreSpec>()?"sign animation":"ambient animation",ok,string.Join("; ",group.Select(x=>
          x.Name+" '"+x.Animator.AnimationName+"' enabled="+x.Animator.Enabled+" time "+x.Time.ToString("0.###")+"->"+x.Animator.Time.ToString("0.###"))));
      }
    }
    private static HashSet<string> PropNodes(Subject s) {
      var spec=s.Building.GetComponent<NativeBuildingPropsSpec>();
      return spec==null?new HashSet<string>():new HashSet<string>(spec.Props.Select(p=>p.Node));
    }
    private void PrepareWaves() {
      foreach(var s in Placed().Where(s=>s.IsWorkshop))_waveQueue.Enqueue(s);
      foreach(var s in Placed().Where(s=>!s.IsWorkshop&&s.IsServiceBuilding)){s.Service=true;_waveQueue.Enqueue(s);}
      foreach(var s in Placed().Where(s=>s.Building.HasComponent<Workplace>()&&!s.IsWorkshop&&!s.IsServiceBuilding))
        Skip(s.Id,"workshop animation","workplace without a native Workshop/Manufactory or civic service");
      // The coal and oil power plants are workerless native Steam Engine generators: no workshop wave.
      foreach(var s in Placed().Where(s=>s.Building.AllComponents.Any(c=>c.GetType().Name=="GoodPoweredGenerator")))
        Skip(s.Id,"workshop animation","workerless native GoodPoweredGenerator: its animator, smoke and output follow MechanicalNode.OutputMultiplier "+
          "(native GoodPoweredGeneratorAnimator); generation is checked by AllBuildingsAcceptance power supply");
      Skip("ShoreFishing","automation Off refuses work","needs a waterfront fixture; this dry pad cannot make ShoreFishing.CanWork true while On, "+
        "so an Off refusal would not isolate the automation gate");
      Debug.Log(Tag+" waves for "+_waveQueue.Count+" workplaces with "+_workers.Count+" adult workers");
    }
    // Workshops are active while natively working (a generator also while producing hp);
    // civic buildings while their native-tested service is on.
    private bool Active(Subject s) {
      if(!s.Service) {
        bool working=s.Building.GetComponent<Workshop>().CurrentlyWorking;
        return s.IsGenerator?working&&s.Node.Actuals.PowerOutput>0:working;
      }
      if(s.Building.HasComponent<GroceryStore>())return s.Building.GetComponent<GroceryStore>().ProvidesNeighborhoodService;
      if(s.Building.HasComponent<Hospital>())return s.Building.GetComponent<Hospital>().ProvidesNeighborhoodCare;
      return s.Building.GetComponent<Restaurant>().IsOperating;
    }
    private static string ServiceName(Subject s)=>!s.Service?"production":
      s.Building.HasComponent<GroceryStore>()?"neighborhood bonus":s.Building.HasComponent<Hospital>()?"neighborhood care":"serving";
    private void StartWave() {
      int size=Math.Min(_workers.Count,8);
      bool service=_waveQueue.Peek().Service;
      while(_waveQueue.Count>0&&_wave.Count<size&&_waveQueue.Peek().Service==service)_wave.Add(_waveQueue.Dequeue());
      _phaseName=(service?"service wave ":"animation wave ")+string.Join(",",_wave.Select(s=>s.Id));
      var free=_workers.ToList();
      foreach(var s in _wave) {
        s.Working=false;s.WorkSampled=false;s.IdleChecked=false;s.PeakReactorOutput=0;s.StationPowered=false;
        s.ServiceSeen=false;s.OffChecked=false;s.Returned=false;
        s.WorkAnimator=s.Service?null:s.Building.GetComponentInChildren<IAnimator>(true);
        Guard(s,"service inputs",()=>Seed(s));
        var pausable=s.Building.GetComponent<PausableBuilding>();
        if(pausable&&pausable.Paused)pausable.Resume();
        var workplace=s.Building.GetComponent<Workplace>();
        while(workplace.DesiredWorkers<1)workplace.IncreaseDesiredWorkers();
        while(workplace.DesiredWorkers>1)workplace.DecreaseDesiredWorkers();
        var worker=CrewMember(s,free);
        if(!worker)continue;
        free.Remove(worker);
        var needs=worker.GetComponent<NeedManager>();
        foreach(var id in BasicNeeds)needs.ApplyEffect(new InstantEffect(id,needs.GetNeedSpec(id).MaximumValue-needs.GetNeedPoints(id),1));
        worker.Unemploy();worker.EmployAt(workplace);s.Worker=worker;
      }
      _speed.ChangeSpeed(3);
    }
    // Specialist-only workplaces (FrontierSpecialistWorkplaceSpec) are staffed by SpecialistStaffing
    // only with beavers of their discipline; the fixture has none, so an untrained adult is
    // graduated through the native-persisted SpecialistTrait.Graduate. Ordinary workplaces get an
    // untrained adult where possible.
    private Worker CrewMember(Subject s,List<Worker> free) {
      var discipline=s.Building.GetComponent<FrontierSpecialistWorkplaceSpec>()?.Discipline;
      if(discipline==null)return free.FirstOrDefault(w=>!w.GetComponent<SpecialistTrait>().IsSpecialist)??free.First();
      var trained=free.FirstOrDefault(w=>w.GetComponent<SpecialistTrait>().Has(discipline));
      if(trained)return trained;
      var untrained=free.FirstOrDefault(w=>!w.GetComponent<SpecialistTrait>().IsSpecialist);
      if(!untrained){Record(s.Id,"specialist crew",false,"no "+discipline+" specialist or untrained adult available");return null;}
      untrained.GetComponent<SpecialistTrait>().Graduate(discipline);
      Record(s.Id,"specialist crew",true,untrained.GetComponent<Timberborn.Characters.Character>().FirstName+" graduated as "+discipline+
        " specialist (fixture has none)");
      return untrained;
    }
    private void Seed(Subject s) {
      var manufactory=s.Building.GetComponent<Manufactory>();
      if(manufactory) {
        if(!manufactory.HasCurrentRecipe)manufactory.SetRecipe(manufactory.ProductionRecipes.First());
        var recipe=manufactory.CurrentRecipe;
        foreach(var good in recipe.Ingredients) {
          int amount=Math.Min(good.Amount*2,manufactory.Inventory.UnreservedCapacity(good.Id));
          if(amount>0)manufactory.Inventory.GiveExisting(new GoodAmount(good.Id,amount));
        }
        if(recipe.ConsumesFuel) {
          int amount=Math.Min(2,manufactory.Inventory.UnreservedCapacity(recipe.Fuel));
          if(amount>0)manufactory.Inventory.GiveExisting(new GoodAmount(recipe.Fuel,amount));
        }
      }
      if(s.Building.HasComponent<GroceryStore>()) {
        var shop=s.Building.GetComponent<GroceryStore>();
        foreach(var food in s.Building.GetComponent<GroceryStoreSpec>().Foods) {
          int amount=shop.Inventory.UnreservedCapacity(food);
          if(amount>0)shop.Inventory.GiveExisting(new GoodAmount(food,amount));
        }
      }
      var supplies=s.Building.GetComponent<GoodConsumingBuilding>();
      if(supplies)foreach(var good in supplies.ConsumedGoods) {
        int amount=Math.Min((int)Math.Ceiling(good.GoodPerHour*24),supplies.Inventory.UnreservedCapacity(good.GoodId));
        if(amount>0)supplies.Inventory.GiveExisting(new GoodAmount(good.GoodId,amount));
      }
    }
    private void ObserveWave(Subject s) {
      if(_phase!=11||s.WorkSampled)return;
      if(s.IsGenerator&&s.Source) {
        s.PeakReactorOutput=Math.Max(s.PeakReactorOutput,s.Node.Actuals.PowerOutput);
        var station=s.Source.GetComponent<MechanicalNode>();
        s.StationPowered|=station.Graph==s.Node.Graph&&station.Powered&&s.Node.Actuals.PowerOutput>0;
      }
      bool active=s.Service?Active(s):s.Building.GetComponent<Workshop>().CurrentlyWorking;
      if(!active)return;
      if(!s.Working) {
        s.Working=true;s.WorkRealStart=Time.unscaledTime;
        if(s.WorkAnimator!=null){s.AnimTime=s.WorkAnimator.Time;s.AnimRepeated=s.WorkAnimator.RepeatedTime;}
        return;
      }
      if(Time.unscaledTime-s.WorkRealStart>3&&(!s.IsGenerator||s.StationPowered||Time.unscaledTime-s.WorkRealStart>20))s.WorkSampled=true;
    }
    private void EvaluateWorking(bool timedOut) {
      foreach(var s in _wave) {
        var workplace=s.Building.GetComponent<Workplace>();
        var district=s.Building.GetComponent<DistrictBuilding>();
        string diag="; district="+(district&&district.District?"yes":"no")+" assigned="+workplace.NumberOfAssignedWorkers+
          " power="+(s.Node!=null?s.Node.PowerEfficiency.ToString("0.##"):"n/a")+
          " worker distance="+(s.Worker?Vector3.Distance(s.Worker.Transform.position,s.Building.Transform.position).ToString("0.#"):"-");
        if(s.Service) {
          Record(s.Id,ServiceName(s)+" before automation",s.Working,(s.Working?"native service active with staff":"service never became active"+
            (timedOut?" within 14 h":""))+diag);
          continue;
        }
        var manufactory=s.Building.GetComponent<Manufactory>();
        if(!s.Working) {
          Record(s.Id,"worker reaches and works",false,"no native worker started working"+(timedOut?" within 14 h":"")+
            " ready="+manufactory.IsReadyToProduce+" recipe="+manufactory.CurrentRecipe?.Id+diag);
          continue;
        }
        Record(s.Id,"worker reaches and works",true,"native Workshop.CurrentlyWorking with "+s.Building.GetComponent<Workshop>().NumberOfWorkersWorking+" worker(s)");
        var finished=s.Building.GetComponent<BuildingModel>().FinishedModel.transform;
        var all=finished.GetComponentsInChildren<MonoBehaviour>(true).OfType<IAnimator>().ToList();
        if(s.WorkAnimator==null)Record(s.Id,"workshop animation plays while working",false,"no IAnimator anywhere in the building");
        else {
          var target=((MonoBehaviour)s.WorkAnimator).transform;
          bool inFinished=target.IsChildOf(finished);
          bool prop=UnderProp(target,finished,PropNodes(s));
          bool advancing=s.WorkAnimator.Time!=s.AnimTime||s.WorkAnimator.RepeatedTime!=s.AnimRepeated;
          string controller=s.Building.AllComponents.Any(c=>c.GetType().Name=="WorkshopAnimationController")?"native controller":"NO native controller";
          Record(s.Id,"workshop animation plays while working",inFinished&&!prop&&s.WorkAnimator.Enabled&&advancing,
            controller+"; animator "+PathOf(s.WorkAnimator,s.Building.Transform)+" '"+s.WorkAnimator.AnimationName+"' enabled="+s.WorkAnimator.Enabled+
            " time "+s.AnimTime.ToString("0.###")+"->"+s.WorkAnimator.Time.ToString("0.###")+
            (prop?" (bound to a native prop, not the building model)":"")+(!inFinished?" (outside the finished model)":"")+
            "; finished-model animators="+all.Count);
        }
        if(s.IsGenerator&&s.Source)
          Record(s.Id,"generator powers consumer",s.PeakReactorOutput>0&&s.StationPowered,"peak native output "+s.PeakReactorOutput+
            " hp; ChargingStation powered on the generator graph="+s.StationPowered);
      }
    }

    // ---------- automation ----------
    private void LeverOff() {
      foreach(var s in _wave.Where(s=>s.Lever&&s.Working))s.Lever.GetComponent<Lever>().SwitchState(false);
    }
    private void EvaluateOff() {
      foreach(var s in _wave.Where(s=>s.Lever&&s.Working)) {
        var a=s.Automatable;var blockable=s.Building.GetComponent<BlockableObject>();var pausable=s.Building.GetComponent<PausableBuilding>();
        int workers=s.Building.GetComponent<Workplace>().NumberOfAssignedWorkers;
        Record(s.Id,"automation Off",a.State==ConnectionState.Off&&!blockable.IsUnblocked&&!pausable.Paused&&workers==0,
          "input="+a.State+" blocked="+!blockable.IsUnblocked+" manually paused="+pausable.Paused+" workers="+workers);
        bool stopped=!Active(s);
        string detail=ServiceName(s)+" active="+!stopped;
        if(s.Building.HasComponent<Restaurant>()) {
          var restaurant=s.Building.GetComponent<Restaurant>();
          stopped&=!restaurant.AcceptsGuests;detail+=" acceptsGuests="+restaurant.AcceptsGuests;
        }
        if(s.IsGenerator){stopped&=s.Node.Actuals.PowerOutput==0;detail+=" native output="+s.Node.Actuals.PowerOutput+" hp";}
        if(s.WorkAnimator!=null){stopped&=!s.WorkAnimator.Enabled;detail+=" animator enabled="+s.WorkAnimator.Enabled;}
        Record(s.Id,"automation Off stops "+ServiceName(s),stopped,detail);
        s.OffChecked=true;
      }
    }
    private void LeverOn() {
      foreach(var s in _wave.Where(s=>s.OffChecked)) {
        Guard(s,"service inputs",()=>Seed(s)); // replace inputs consumed before the Off interval
        s.Lever.GetComponent<Lever>().SwitchState(true);
      }
    }
    private void EvaluateOn() {
      foreach(var s in _wave.Where(s=>s.OffChecked)) {
        var blockable=s.Building.GetComponent<BlockableObject>();
        int workers=s.Building.GetComponent<Workplace>().NumberOfAssignedWorkers;
        Record(s.Id,"automation On restores",s.Automatable.State==ConnectionState.On&&blockable.IsUnblocked&&s.Returned,
          "input="+s.Automatable.State+" unblocked="+blockable.IsUnblocked+" workers="+workers+" "+ServiceName(s)+" returned="+s.Returned+
          (s.IsGenerator?" native output="+s.Node.Actuals.PowerOutput+" hp":""));
      }
    }
    private void StopWave() {
      foreach(var s in _wave) {
        var workplace=s.Building.GetComponent<Workplace>();
        while(workplace.DesiredWorkers>0)workplace.DecreaseDesiredWorkers();
        foreach(var w in workplace.AssignedWorkers.ToList())w.Unemploy();
      }
    }
    private void EvaluateIdle() {
      foreach(var s in _wave.Where(s=>!s.Service)) {
        bool working=s.Building.GetComponent<Workshop>().CurrentlyWorking;
        if(s.WorkAnimator!=null&&s.Working)
          Record(s.Id,"workshop animation stops when idle",!working&&!s.WorkAnimator.Enabled,
            "working="+working+" animator enabled="+s.WorkAnimator.Enabled);
      }
    }
    private string Role(Subject s) {
      var key=_automationRoles.Properties().Select(p=>p.Name).SingleOrDefault(k=>k.EndsWith("/"+s.Template+".blueprint",StringComparison.Ordinal));
      return key==null?null:(string)_automationRoles[key]["role"];
    }
    private void CheckAutomation(Subject s) {
      s.AutomationRole=Role(s);
      var pausable=s.Building.GetComponent<PausableBuilding>();
      var automator=s.Building.GetComponent<Automator>();
      if(s.AutomationRole==null){Record(s.Id,"automation role",false,"no role for "+s.Template+" in tools/automation_content.json");return;}
      if(s.AutomationRole=="none") {
        Record(s.Id,"not automatable",!s.Automatable&&!(pausable&&pausable.IsPausable()),
          "Automatable="+(bool)s.Automatable+" pausable="+(pausable&&pausable.IsPausable()));
        return;
      }
      Record(s.Id,"automatable ("+s.AutomationRole+")",s.Automatable&&s.Building.HasComponent<PausableBuildingTerminal>()&&
        automator&&!automator.IsTransmitter&&pausable&&pausable.IsPausable(),
        "Automatable="+(bool)s.Automatable+" PausableBuildingTerminal="+s.Building.HasComponent<PausableBuildingTerminal>()+
        " automator="+(automator?(automator.IsTransmitter?"sensor/transmitter":"terminal"):"none")+" pausable="+(pausable&&pausable.IsPausable()));
      if(s.Lever)Record(s.Id,"automation input wired",s.Automatable&&s.Automatable.Input==s.Lever.GetComponent<Automator>()&&
        s.Automatable.State==(s.Lever.GetComponent<Lever>().IsOn?ConnectionState.On:ConnectionState.Off),
        "input "+(s.Automatable&&s.Automatable.Input?s.Automatable.Input.AutomatorName:"none")+" state="+(s.Automatable?s.Automatable.State.ToString():"-"));
    }
    private void PlaceLever(Subject s) {
      if(Role(s)=="none"||!s.Automatable)return;
      var r=Bounds(s.Spec,s.Building.Placement);
      for(int ring=2;ring<=3&&!s.Lever;ring++)
        for(int x=r.xMin-ring;x<r.xMax+ring&&!s.Lever;x++)for(int y=r.yMin-ring;y<r.yMax+ring&&!s.Lever;y++) {
          if(x>r.xMin-ring&&x<r.xMax+ring-1&&y>r.yMin-ring&&y<r.yMax+ring-1)continue;
          var c=new Vector3Int(x,y,Ground);
          if(!Free(_lever,c))continue;
          s.Lever=Create(_lever,At(c));
        }
      if(!s.Lever){Record(s.Id,"automation lever",false,"no free cell for a native Lever");return;}
      s.Lever.GetComponent<Lever>().SwitchState(true);
      s.Automatable.SetInput(s.Lever.GetComponent<Automator>());
    }

    // ---------- save / reload ----------
    private IEnumerable<LategameEntityRecord> Records(Subject s) {
      LategameEntityRecord R(BlockObject b,string role)=>new LategameEntityRecord{Id=Id(b),Template=b.GetComponent<TemplateSpec>().TemplateName,
        Subject=s.Id,Role=role,Coordinates=b.Coordinates,Orientation=b.Orientation.ToString(),Flipped=b.FlipMode.IsFlipped};
      var building=R(s.Building,"building");
      var automatable=s.Building.GetComponent<Automatable>();
      if(automatable&&automatable.Input)building.InputId=automatable.Input.AutomatorId;
      yield return building;
      if(s.Lever){var lever=R(s.Lever,"lever");lever.LeverOn=s.Lever.GetComponent<Lever>().IsOn;yield return lever;}
      if(s.Understructure)yield return R(s.Understructure,"understructure");
      foreach(var (b,role) in new[]{(s.EntrancePath,"entrance"),(s.Shaft,"shaft"),(s.RoofShaft,"roofShaft"),(s.Source,"source"),(s.Tubeway,"tubeway"),
          (s.CableGen,"cable"),(s.BeltIn,"beltIn"),(s.BeltOut,"beltOut")})
        if(b)yield return R(b,role);
      foreach(var v in s.Valves) {
        var r=R(v.Valve,"valve");r.Port=v.Port;r.Direction=v.Direction.ToString();r.State=v.State.ToString();yield return r;
      }
    }
    private void BindSaved() {
      var saved=JsonConvert.DeserializeObject<LategameSaveRecord>(File.ReadAllText(RecordPath));
      Require(saved?.Entities!=null&&saved.Entities.Length>0,"Empty late-game reload expectations");
      Require(saved.RegionWidth>0&&saved.RegionHeight>0,"Late-game reload expectations lack the pad region; rerun the main pass");
      Region=new RectInt(saved.RegionX,saved.RegionY,saved.RegionWidth,saved.RegionHeight);
      var byId=_entities.Entities.ToDictionary(e=>e.EntityId.ToString());
      foreach(var r in saved.Entities.Where(r=>r.Role=="persistenceLever")) {
        if(!byId.TryGetValue(r.Id,out var entity)){Record("Fixture","lever state persists",false,"saved persistence lever missing");continue;}
        _persistenceLever=entity.GetComponent<BlockObject>();
        bool on=_persistenceLever.GetComponent<Lever>().IsOn;
        Record("Fixture","lever state persists",on==r.LeverOn&&!on,"unconnected lever saved "+(r.LeverOn?"On":"Off")+", restored "+(on?"On":"Off"));
      }
      foreach(var group in saved.Entities.Where(r=>r.Role!="persistenceLever").GroupBy(r=>r.Subject)) {
        var first=group.Single(r=>r.Role=="building");
        var template=Template(first.Template);
        Require(template!=null,"Saved template no longer loaded: "+first.Template);
        var s=new Subject{Id=group.Key,Template=first.Template,Blueprint=template.Blueprint,Spec=template.Blueprint.GetSpec<BlockObjectSpec>()};
        foreach(var r in group) {
          if(!byId.TryGetValue(r.Id,out var entity)){Record(s.Id,"reload identity "+r.Role,false,"saved entity "+r.Id+" missing");continue;}
          var b=entity.GetComponent<BlockObject>();
          bool same=entity.GetComponent<TemplateSpec>().TemplateName==r.Template&&b.Coordinates==r.Coordinates&&
            b.Orientation.ToString()==r.Orientation&&b.FlipMode.IsFlipped==r.Flipped;
          if(!same)Record(s.Id,"reload identity "+r.Role,false,"template/coordinates/orientation changed: "+b.Coordinates+" "+b.Orientation);
          switch(r.Role) {
            case "building": s.Building=b;s.Orientation=b.Orientation;s.Flip=b.FlipMode.IsFlipped;break;
            case "understructure": s.Understructure=b;break;
            case "entrance": s.EntrancePath=b;break;
            case "shaft": s.Shaft=b;break;
            case "roofShaft": s.RoofShaft=b;break;
            case "source": s.Source=b;break;
            case "tubeway": s.Tubeway=b;break;
            case "cable": s.CableGen=b;break;
            case "beltIn": s.BeltIn=b;break;
            case "beltOut": s.BeltOut=b;break;
            case "lever":
              s.Lever=b;
              Record(s.Id,"reload lever state",b.GetComponent<Lever>().IsOn==r.LeverOn,"saved "+r.LeverOn+" restored "+b.GetComponent<Lever>().IsOn);
              break;
            case "valve": s.Valves.Add(new ValveTest{Valve=b,Port=r.Port,
              Direction=(Direction3D)Enum.Parse(typeof(Direction3D),r.Direction),State=(PipePortState)Enum.Parse(typeof(PipePortState),r.State)});break;
          }
        }
        _subjects.Add(s);
        if(s.Building) {
          Record(s.Id,"reload identity",true,"restored "+group.Count()+" saved entities at "+s.Building.Coordinates+" "+s.Orientation+(s.Flip?" flipped":""));
          var savedInput=group.Single(r=>r.Role=="building").InputId;
          if(savedInput!=null)Record(s.Id,"reload automation input",s.Automatable&&s.Automatable.Input&&s.Automatable.Input.AutomatorId==savedInput&&
            s.Lever&&s.Automatable.Input==s.Lever.GetComponent<Automator>(),"input "+(s.Automatable&&s.Automatable.Input?s.Automatable.Input.AutomatorId:"none")+
            " saved "+savedInput);
          Guard(s,"reload occupancy",()=>{CheckOccupancy(s,s.Building,"saved");Record(s.Id,"reload occupancy",true,"registered blocks and entrance match the blueprint");});
          if(s.Building.HasComponent<Workplace>())Idle(s);
          // Setup paused every saved workplace; subjects must stay unpaused for native inventory/power checks.
          var pausable=s.Building.GetComponent<PausableBuilding>();
          if(pausable&&pausable.Paused)pausable.Resume();
        }
      }
      foreach(var id in saved.Subjects??new string[0])
        if(_subjects.All(s=>s.Id!=id))Record(id,"reload identity",false,"subject absent from the saved record");
    }
    private void WriteResults() {
      Directory.CreateDirectory(Outputs);
      File.WriteAllText(Path.Combine(Outputs,_reload?"lategame-acceptance-reload.json":"lategame-acceptance-main.json"),
        JsonConvert.SerializeObject(new {
          mode=_reload?"reload":"main",
          scope="Marked disposable settlement; native placement, access, power, connectors, props and animation of installed late-game buildings",
          subjects=_subjects.Select(s=>new {s.Id,s.Template,placed=(bool)s.Building,coordinates=s.Building?s.Building.Coordinates.ToString():null,
            orientation=s.Orientation.ToString(),flipped=s.Flip,skip=s.Skip}),
          passed=_results.Count(r=>r.Status=="PASS"),failed=_results.Count(r=>r.Status=="FAIL"),skipped=_results.Count(r=>r.Status=="SKIP"),
          results=_results},Formatting.Indented));
    }
    private void Finish() {
      _speed.ChangeSpeed(0);_hours.WorkedPartOfDay=_normalHours;_finished=true;
      foreach(var s in Placed().Where(s=>s.Building.HasComponent<Workplace>()))Idle(s);
      if(!_reload) {
        _persistenceLever.GetComponent<Lever>().SwitchState(false);
        var persistence=new LategameEntityRecord{Id=Id(_persistenceLever),Template=_persistenceLever.GetComponent<TemplateSpec>().TemplateName,
          Subject="Fixture",Role="persistenceLever",Coordinates=_persistenceLever.Coordinates,Orientation=_persistenceLever.Orientation.ToString(),LeverOn=false};
        File.WriteAllText(RecordPath,JsonConvert.SerializeObject(new LategameSaveRecord {
          Subjects=_subjects.Where(s=>s.Building).Select(s=>s.Id).ToArray(),
          RegionX=Region.x,RegionY=Region.y,RegionWidth=Region.width,RegionHeight=Region.height,
          Entities=Placed().SelectMany(Records).Append(persistence).ToArray()},Formatting.Indented));
      }
      WriteResults();
      int failed=_results.Count(r=>r.Status=="FAIL"),passed=_results.Count(r=>r.Status=="PASS"),skipped=_results.Count(r=>r.Status=="SKIP");
      string mode=_reload?"RELOAD":"MAIN";
      _saver.QueueSave(new SaveReference(_reload?"Lategame acceptance - reload":"Lategame acceptance - main",_loader.LoadedSave.SettlementReference),
        ()=>Debug.Log(Tag+" COMPLETE "+mode+" passed="+passed+" failed="+failed+" skipped="+skipped+" AND SAVED"));
    }
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
    private readonly BlockObjectFactory _factory;
    private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _validation;
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

    public LategameRocketAcceptance(EntityRegistry entities,TemplateService templates,BlockObjectFactory factory,
      BlockValidator validator,BlockObjectValidationService validation,SpeedManager speed,IDayNightCycle clock,
      WorkingHoursManager hours,GameSaver saver,GameLoader loader,RocketProgramService program,ScienceService science,
      NotificationBus notifications,WonderCompletionCountdownStarter wonder,PanelStack panels,CameraService camera) {
      _entities=entities;_templates=templates;_factory=factory;_validator=validator;_validation=validation;_speed=speed;
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
        // Exactly 20,000 hp from two native dev generators: below the 27,000 hp launch load.
        foreach(var g in _supplies.Keys.Where(g=>g.GetComponent<MechanicalNodeSpec>().PowerOutput==10000).Take(2))g.SetOutputMultiplier(1);
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
      var generator=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName=="DevPowerGenerator").Blueprint;
      var spec=generator.GetSpec<BlockObjectSpec>();
      int needed=(int)Math.Ceiling((_padBlock.GetComponent<MechanicalNodeSpec>().PowerInput-node.Graph.PowerSupply+2000f)/10000f);
      var source=node.Graph.Generators.FirstOrDefault(g=>g.GetComponent<MechanicalNodeSpec>().PowerOutput==10000);
      Require(source,"LaunchPad graph has no native dev generator from the layout run");
      var origin=source.GetComponent<BlockObject>().Coordinates;
      foreach(var d in new[]{Vector3Int.left,Vector3Int.right,Vector3Int.up,Vector3Int.down}) {
        if(needed<=0)break;
        var c=origin+d;var p=new Placement(c,Orientation.Cw0,new FlipMode(false));
        if(!_validator.BlocksValid(spec,p))continue;
        var b=_factory.CreateFinished(new EntitySetup.Builder(generator).AddInitComponent(new FinishedConstructionSiteInit()),p);
        Require(_validation.IsValid(b),"Native requirements rejected an extra launch generator");
        needed--;
      }
      Require(needed<=0,"No room for extra launch generators beside the pad's source generator");
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
