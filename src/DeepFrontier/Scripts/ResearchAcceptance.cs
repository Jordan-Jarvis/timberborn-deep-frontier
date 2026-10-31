using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Newtonsoft.Json;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.CameraSystem;
using Timberborn.CharacterControlSystem;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.MechanicalSystem;
using Timberborn.Navigation;
using Timberborn.PathSystem;
using Timberborn.ScienceSystem;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using Timberborn.Workshops;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class ResearchAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      var args=Environment.GetCommandLineArgs();
      if(args.Contains("-deepFrontierResearch")||args.Contains("-deepFrontierResearchReload"))
        Bind<ResearchAcceptance>().AsSingleton();
    }
  }
  internal sealed class ResearchSaveRecord {
    public string EntityId;
    public Dictionary<string,int> Stock;
    public float Progress;
    public int Science;
  }
  internal sealed class ResearchAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private readonly EntityRegistry _entities;
    private readonly BlockObjectFactory _factory;
    private readonly TemplateService _templates;
    private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _validation;
    private readonly IBlockService _blocks;
    private readonly INavMeshService _nav;
    private readonly INavigationService _navigation;
    private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock;
    private readonly WorkingHoursManager _hours;
    private readonly CameraService _camera;
    private readonly GameSaver _saver;
    private readonly GameLoader _loader;
    private readonly ScienceService _science;
    private readonly Queue<Vector3> _destinations=new();
    private readonly List<Inventory> _donors=new();
    private readonly Dictionary<string,int> _consumed=new(){{"Gear",0},{"Concrete",0},{"MetalBlock",0}};
    private readonly bool _reload=Environment.GetCommandLineArgs().Contains("-deepFrontierResearchReload");
    private BlockObject _building;
    private Manufactory _machine;
    private MechanicalNode _generator;
    private Transform _wheel,_ram,_screw;
    private Quaternion _initialWheel,_initialScrew,_stoppedWheel;
    private float _initialRam,_stoppedRam,_stoppedProgress,_phaseTime,_normalHours;
    private int _frame,_phase,_batches,_walks,_initialScience;
    private bool _finished,_wheelMoved,_ramMoved,_screwMoved;
    private ControllableCharacter _walker;
    private Vector3 _target;
    private string RecordPath=>Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
      "TimberbornModding","outputs","research-reload-expectations.json");
    public ResearchAcceptance(EntityRegistry entities,BlockObjectFactory factory,TemplateService templates,
      BlockValidator validator,BlockObjectValidationService validation,IBlockService blocks,
      INavMeshService nav,INavigationService navigation,SpeedManager speed,IDayNightCycle clock,
      WorkingHoursManager hours,CameraService camera,GameSaver saver,GameLoader loader,ScienceService science) {
      _entities=entities;_factory=factory;_templates=templates;_validator=validator;_validation=validation;
      _blocks=blocks;_nav=nav;_navigation=navigation;_speed=speed;_clock=clock;_hours=hours;
      _camera=camera;_saver=saver;_loader=loader;_science=science;
    }
    private static void Require(bool condition,string message) {if(!condition)throw new InvalidOperationException(message);}
    private static void Pass(string message)=>Debug.Log("[DeepFrontier Research] PASS "+message);
    private void Phase(int phase) {_phase=phase;_phaseTime=_clock.PartialDayNumber;}
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()&&
        e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"),"Disposable fixture marker missing");
      _speed.ChangeSpeed(0);
    }
    private BlockObject Create(string id,int x,int y,int z,Orientation rotation=Orientation.Cw0) {
      var template=_templates.GetAll<TemplateSpec>().Single(s=>s.TemplateName==id);
      var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
      var p=new Placement(new Vector3Int(x,y,z),rotation,FlipMode.Unflipped);
      Require(_validator.BlocksValid(spec,p),"Native placement rejected "+id+" "+p.Coordinates);
      var result=_factory.CreateFinished(new EntitySetup.Builder(template.Blueprint).AddInitComponent(new FinishedConstructionSiteInit()),p);
      Require(_validation.IsValid(result),"Native requirements rejected "+id);return result;
    }
    private void Setup() {
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<PausableBuilding>()
        &&(e.HasComponent<Workplace>()||e.HasComponent<Manufactory>())))e.GetComponent<PausableBuilding>().Pause();
      if(_reload) {
        _building=_entities.Entities.Single(e=>e.HasComponent<TemplateSpec>()&&
          e.GetComponent<TemplateSpec>().TemplateName=="MaterialsLaboratory.IronTeeth").GetComponent<BlockObject>();
        var generatorCell=ShaftCell(2);
        _generator=_entities.Entities.Where(e=>e.HasComponent<BlockObject>()).Select(e=>e.GetComponent<BlockObject>())
          .Single(b=>b.Coordinates==generatorCell&&b.GetComponent<TemplateSpec>().TemplateName=="DevPowerGenerator").GetComponent<MechanicalNode>();
      } else {
        _building=Create("MaterialsLaboratory.IronTeeth",159,160,3);
        _building.GetComponent<PausableBuilding>().Pause();
        // The fixture follows the installed laboratory blueprint, not a size
        // literal (10x8x5 since the 2026-10-30 compaction). Freed ground: every
        // open ground cell inside the bounds, plus the rear row the 2026-10-22
        // footprint pass dropped (the former footprint ended at local y 8).
        var spec=_building.GetComponent<BlockObjectSpec>();
        var size=spec.Size;
        var openGround=spec.GetBlocks(new Placement(Vector3Int.zero,Orientation.Cw0,FlipMode.Unflipped))
          .Where(b=>b.Coordinates.z==0&&!b.IsOccupied).Select(b=>b.Coordinates).ToArray();
        Require(openGround.Length>0,"Installed MaterialsLaboratory has no open ground cell inside its bounds");
        FreedCellProbe.Require(_templates,_validator,_building,
          openGround.Concat(FreedCellProbe.Outside(0,size.x-1,0,8,size)),"MaterialsLaboratory",Pass);
        // The road runs along the entrance row to the district path at x 173.
        var entrance=_building.PositionedEntrance.Coordinates;
        var deck=_building.GetComponent<PlatformDeckSpec>();
        var front=_building.TransformCoordinates(deck.Openings.Single(p=>p.Id=="Front0").Outside);
        var left=_building.TransformCoordinates(deck.Openings.Single(p=>p.Id=="Left1").Outside);
        Require(front.y==entrance.y&&front.z>entrance.z&&left.z==front.z,
          "Laboratory terrace openings Front0 "+front+" and Left1 "+left+" do not meet one deck above the entrance row "+entrance);
        for(int y=entrance.y-2;y<=entrance.y;y++)if(!_blocks.GetPathObjectAt(new Vector3Int(173,y,entrance.z)))Create("Path",173,y,entrance.z);
        for(int x=front.x-1;x<173;x++)Create("Path",x,entrance.y,entrance.z);
        // A stair flight climbs north to the Front0 rail's outside cell: one
        // stair per deck level, each on a platform stack, from a ground landing
        // that a path column west of the flight joins to the road.
        int levels=front.z-entrance.z;
        int landing=front.y-levels-1;
        for(int y=landing;y<front.y;y++)Create("Path",front.x-1,y,entrance.z);
        Create("Path",front.x,landing,entrance.z);
        for(int k=0;k<levels;k++) {
          int y=front.y-levels+k;
          for(int z=entrance.z;z<entrance.z+k;z++)Create("Platform.IronTeeth",front.x,y,z);
          Create("Stairs.IronTeeth",front.x,y,entrance.z+k,Orientation.Cw180);
        }
        // Each open rail's outside cell: a platform stack to the deck and a path on it.
        foreach(var pad in new[]{front,left}) {
          for(int z=entrance.z;z<pad.z;z++)Create("Platform.IronTeeth",pad.x,pad.y,z);
          Create("Path",pad.x,pad.y,pad.z);
        }
        // Stacked platforms on the terrace: Front1's deck cell (its rail stays closed).
        var stack=_building.TransformCoordinates(deck.Openings.Single(p=>p.Id=="Front1").Inside);
        Create("DoublePlatform.IronTeeth",stack.x,stack.y,stack.z);
        Create("Platform.IronTeeth",stack.x,stack.y,stack.z+2);Create("Path",stack.x,stack.y,stack.z+3);
        var shaft=ShaftCell(1);
        Create("PowerShaft.IronTeeth",shaft.x,shaft.y,shaft.z);
        var generator=ShaftCell(2);
        _generator=Create("DevPowerGenerator",generator.x,generator.y,generator.z).GetComponent<MechanicalNode>();
        // The terrace is a player-path deck (2026-10-30): the two open rails need a path on their deck cell.
        foreach(var id in new[]{"Front0","Left1"}) {
          var inside=_building.TransformCoordinates(deck.Openings.Single(p=>p.Id==id).Inside);
          if(!_blocks.GetPathObjectAt(inside))Create("Path",inside.x,inside.y,inside.z);
        }
        var pathTemplate=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName=="Path");
        var pathSpec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==pathTemplate.Blueprint);
        // An enclosed room: the footprint's centre ground cell, occupied in the blueprint.
        var room=new Vector3Int(size.x/2,size.y/2,0);
        Require(!openGround.Contains(room),"Laboratory centre ground cell "+room+" is open in the installed blueprint");
        var roomCell=_building.TransformCoordinates(room);
        Require(!_validator.BlocksValid(pathSpec,new Placement(roomCell,Orientation.Cw0,FlipMode.Unflipped)),
          "Enclosed laboratory accepts ground construction at "+roomCell);
        Pass("native building, stairs, stacked terrace platforms, shaft placement and enclosed-room collision");
      }
      _machine=_building.GetComponent<Manufactory>();
      foreach(var inventory in _entities.Entities.Where(e=>e.HasComponent<Inventories>())
        .SelectMany(e=>e.GetComponent<Inventories>().AllInventories)
        .Where(i=>i!=_machine.Inventory&&i.Enabled&&i.PublicOutput&&_consumed.Keys.Any(g=>i.OutputGoods.Contains(g)))) {
        inventory.Disable();_donors.Add(inventory);
      }
      var transforms=_building.GetComponent<BuildingModel>().FinishedModel.GetComponentsInChildren<Transform>(true);
      _wheel=transforms.Single(t=>t.name=="#MaterialsLaboratory.Flywheel");
      _ram=transforms.Single(t=>t.name=="#MaterialsLaboratory.TestRam");
      _screw=transforms.Single(t=>t.name=="#MaterialsLaboratory.PressScrew");
      _initialWheel=_wheel.localRotation;_initialScrew=_screw.localRotation;_initialRam=_ram.localPosition.y;
      _machine.ProductionFinished+=(sender,args)=>{_batches++;Debug.Log("[DeepFrontier Research] BATCH "+_batches);};
      _machine.Inventory.InventoryStockChanged+=(sender,args)=>{
        if(args.StockChangeType==StockChangeType.Consumed&&args.GoodAmount.Amount<0&&_consumed.ContainsKey(args.GoodAmount.GoodId))
          _consumed[args.GoodAmount.GoodId]-=args.GoodAmount.Amount;
      };
      _camera.MoveTargetTo(new Vector3(163,7,164));_camera.SetZoomLevel(19,0);
      _camera.HorizontalAngle=25;_camera.VerticalAngle=35;
      _normalHours=_hours.WorkedPartOfDay;_hours.WorkedPartOfDay=1;
    }
    // The shaft line leaves the first transput's first horizontal face: the
    // shaft one step out, its generator two.
    private Vector3Int ShaftCell(int steps) {
      var transput=_building.GetComponent<TransputProviderSpec>().Transputs[0];
      var step=transput.Directions.ToString().Split(',').Select(d=>d.Trim()).Select(d=>
        d=="Left"?Vector3Int.left:d=="Right"?Vector3Int.right:d=="Down"?Vector3Int.down:d=="Up"?Vector3Int.up:Vector3Int.zero)
        .FirstOrDefault(v=>v!=Vector3Int.zero);
      Require(step!=Vector3Int.zero,"Laboratory transput "+transput.Coordinates+" has no horizontal face: "+transput.Directions);
      return _building.TransformCoordinates(transput.Coordinates+step*steps);
    }
    // The ground door: the footprint cell the native Entrance stands in front of.
    private Vector3Int DoorCell() {
      var spec=_building.GetComponent<BlockObjectSpec>();var e=spec.Entrance.Coordinates;
      return _building.TransformCoordinates(new Vector3Int(Mathf.Clamp(e.x,0,spec.Size.x-1),Mathf.Clamp(e.y,0,spec.Size.y-1),e.z));
    }
    private void Inputs(int batches) {
      _machine.Inventory.GiveExisting(new GoodAmount("Gear",4*batches));
      _machine.Inventory.GiveExisting(new GoodAmount("Concrete",2*batches));
      _machine.Inventory.GiveExisting(new GoodAmount("MetalBlock",batches));
    }
    private void Port(string id,bool expected) {
      // Player-path terrace deck (PlatformDeck, 2026-10-30): the rail hides exactly
      // when actual player paths stand on the deck cell and its neighbour.
      var p=_building.GetComponent<PlatformDeckSpec>().Openings.Single(p=>p.Id==id);
      var a=_building.TransformCoordinates(p.Inside);var b=_building.TransformCoordinates(p.Outside);
      var transforms=_building.GetComponent<BuildingModel>().FinishedModel.GetComponentsInChildren<Transform>(true);
      bool connected=_nav.AreConnectedInstant(a,b)&&_nav.AreConnectedInstant(b,a);
      bool hidden=p.HiddenNodes.All(n=>!transforms.Single(t=>t.name==n).gameObject.activeSelf);
      bool paths=IsPlayerPath(a)&&IsPlayerPath(b);
      Require(paths==expected&&hidden==expected&&(!expected||connected),"Laboratory rail/path mismatch "+id);
    }
    private bool IsPlayerPath(Vector3Int c) {
      var o=_blocks.GetPathObjectAt(c);return o&&o.IsFinished&&o.HasComponent<PathSpec>();
    }
    private void Start() {
      Require(_building.GetComponent<BuildingSpec>().ScienceCost==12000,"Laboratory must unlock at 12,000 science");
      Require(_building.GetComponent<MechanicalNodeSpec>().PowerInput==6500,"Laboratory demand differs from 6,500 hp");
      Require(_building.GetComponent<MechanicalNode>().Graph==_generator.Graph&&_generator.Graph.PowerSupply>0,"Laboratory shaft does not connect");
      Port("Front0",true);Port("Front1",false);Port("Left1",true);Port("Left2",false);
      var entrance=_building.PositionedEntrance.Coordinates;
      Require(_nav.AreConnectedInstant(entrance,DoorCell()),"Ground door lacks its road connection");
      Pass("12,000-science unlock, 6,500 hp connected graph and selective rail openings");
      if(_reload) {
        var record=JsonConvert.DeserializeObject<ResearchSaveRecord>(File.ReadAllText(RecordPath));
        Require(_building.GetComponent<EntityComponent>().EntityId.ToString()==record.EntityId,"Research identity changed");
        Require(_science.SciencePoints==record.Science,"Saved science differs");
        Require(Math.Abs(_machine.ProductionProgress-record.Progress)<.00001f,"Saved research progress differs");
        foreach(var g in _consumed.Keys)Require(_machine.Inventory.AmountInStock(g)==record.Stock[g],"Saved research stock differs: "+g);
        Pass("fresh process restored identity, science, exact ingredient stocks and research progress");
      } else {Require(_machine.Inventory.IsEmpty,"New laboratory contains unexpected stock");Inputs(2);}
      _initialScience=_science.SciencePoints;
      var workers=_entities.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>())
        .Where(w=>w.WorkerType=="Beaver").Take(5).ToArray();
      Require(workers.Length==5,"Laboratory fixture requires four workers and a walker");
      foreach(var worker in workers)worker.Unemploy();
      _building.GetComponent<PausableBuilding>().Resume();
      for(int i=0;i<4;i++)workers[i].EmployAt(_building.GetComponent<Workplace>());
      _walker=workers[4].GetComponent<ControllableCharacter>();_walker.ChangeAnimation("BeaverAdult_idle");
      _destinations.Enqueue(NavigationCoordinateSystem.GridToWorld(entrance));
      // Terrace deck cells, walked as grid cells: the records-office doorstep,
      // the Left1 rail cell and the Front2 corner.
      var deck=_building.GetComponent<PlatformDeckSpec>();
      foreach(var cell in new[]{deck.Doors[0].Exterior,deck.Openings.Single(p=>p.Id=="Left1").Inside,deck.Openings.Single(p=>p.Id=="Front2").Inside})
        _destinations.Enqueue(NavigationCoordinateSystem.GridToWorld(_building.TransformCoordinates(cell)));
      _destinations.Enqueue(NavigationCoordinateSystem.GridToWorld(entrance));
      NextWalk();Phase(_reload?7:1);_speed.ChangeSpeed(3);
    }
    private void NextWalk() {
      if(_destinations.Count==0){_walker.ReleaseControl();_walker=null;return;}
      _target=_destinations.Dequeue();
      Require(_navigation.FindPathUnlimitedRange(_walker.Transform.position,_target,new List<PathCorner>(),out var distance),"No laboratory walk route to "+_target);
      _walker.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(_target));
    }
    private void CheckBatchTotals(int count) {
      Require(_consumed["Gear"]==4*count&&_consumed["Concrete"]==2*count&&_consumed["MetalBlock"]==count,"Research ingredient debits differ");
      Require(_science.SciencePoints-_initialScience==800*count,"Native science award differs: "+(_science.SciencePoints-_initialScience));
    }
    private void Finish() {
      Require(_walks==5&&_wheelMoved&&_screwMoved&&_ramMoved,"Incomplete research traversal/animation evidence");
      _building.GetComponent<PausableBuilding>().Pause();_speed.ChangeSpeed(0);_finished=true;
      _hours.WorkedPartOfDay=_normalHours;
      if(!_reload) {
        Require(_consumed.Keys.All(g=>_machine.Inventory.AmountInStock(g)==0),"Controlled research inputs replenished unexpectedly");
        Inputs(1);
        File.WriteAllText(RecordPath,JsonConvert.SerializeObject(new ResearchSaveRecord {
          EntityId=_building.GetComponent<EntityComponent>().EntityId.ToString(),
          Stock=_consumed.Keys.ToDictionary(g=>g,g=>_machine.Inventory.AmountInStock(g)),
          Progress=_machine.ProductionProgress,Science=_science.SciencePoints},Formatting.Indented));
      }
      foreach(var inventory in _donors)inventory.Enable();_donors.Clear();
      var review=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding","docs","art","reviews","2026-10-20-research");
      Directory.CreateDirectory(review);ScreenCapture.CaptureScreenshot(Path.Combine(review,_reload?"Laboratory-native-reload.png":"Laboratory-native.png"));
      _saver.QueueSave(new SaveReference(_reload?"Research continuity - verified":"Research acceptance - verified",_loader.LoadedSave.SettlementReference),
        ()=>Debug.Log("[DeepFrontier Research] "+(_reload?"ALL RELOAD CHECKS PASSED AND SAVED":"ALL MAIN CHECKS PASSED AND SAVED")));
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60)Setup();
        if(_frame==240)Start();
        if(_frame<=240)return;
        if(_walker&&Vector3.Distance(_walker.Transform.position,_target)<.18f){_walks++;Pass("actual beaver reached "+_target);NextWalk();}
        _wheelMoved|=Quaternion.Angle(_wheel.localRotation,_initialWheel)>.1f;
        _screwMoved|=Quaternion.Angle(_screw.localRotation,_initialScrew)>.1f;
        _ramMoved|=Math.Abs(_ram.localPosition.y-_initialRam)>.02f;
        float hours=(_clock.PartialDayNumber-_phaseTime)*24;
        if(_frame%900==0)Debug.Log("[DeepFrontier Research] STATUS phase="+_phase+", batches="+_batches+", progress="+_machine.ProductionProgress+", walks="+_walks);
        if(_phase==1&&_machine.ProductionProgress>.2f) {
          Require(_wheelMoved&&_ramMoved&&_screwMoved,"Research machinery did not animate");
          Require(_building.GetComponent<MechanicalNode>().PowerEfficiency==1,"Research lacks its full power supply");
          _generator.SetOutputMultiplier(0);Phase(2);
        } else if(_phase==2&&hours>.1f) {
          _stoppedProgress=_machine.ProductionProgress;_stoppedWheel=_wheel.localRotation;_stoppedRam=_ram.localPosition.y;Phase(3);
        } else if(_phase==3&&hours>.3f) {
          Require(Math.Abs(_machine.ProductionProgress-_stoppedProgress)<.00001f,"Unpowered research progressed");
          Require(Quaternion.Angle(_wheel.localRotation,_stoppedWheel)<.01f&&Math.Abs(_ram.localPosition.y-_stoppedRam)<.0001f,"Unpowered machinery kept moving");
          Require(_science.SciencePoints==_initialScience,"Unpowered unfinished research awarded science");
          _generator.SetOutputMultiplier(1);Pass("power loss stops research progress and visible machinery");Phase(4);
        } else if(_phase==4&&_batches==2) {CheckBatchTotals(2);Pass("two native batches consumed exact samples and awarded 1,600 science");Phase(5);
        } else if(_phase==5&&hours>.4f) {
          Require(_batches==2&&!_machine.IsReadyToProduce,"Research continued without samples");CheckBatchTotals(2);Inputs(1);Phase(6);
          Pass("exhausted inputs stop research; replenishment supplied one new batch");
        } else if(_phase==6&&_batches==3&&_walks==5) {CheckBatchTotals(3);Pass("three batches awarded 2,400 native science");Finish();
        } else if(_phase==7&&_batches==1&&_walks==5) {CheckBatchTotals(1);Pass("saved samples produced another 800 science after reload");Finish();}
        Require(hours<36,"Research phase exceeded native time limit");
      } catch(Exception error) {
        _finished=true;_speed.ChangeSpeed(0);foreach(var inventory in _donors)inventory.Enable();_donors.Clear();
        Debug.LogError("[DeepFrontier Research] FAILED: "+error);
      }
    }
  }
}
