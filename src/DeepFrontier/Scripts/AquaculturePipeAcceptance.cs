#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Newtonsoft.Json;
using TimberPipes.Components;
using TimberPipes.Models;
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
using Timberborn.SingletonSystem;
using Timberborn.Stockpiles;
using Timberborn.TemplateSystem;
using Timberborn.TerrainSystem;
using Timberborn.TimeSystem;
using Timberborn.Workshops;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class AquaculturePipeAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierAquaculturePipes")
        ||Environment.GetCommandLineArgs().Contains("-deepFrontierAquaculturePipesReload"))
        Bind<AquaculturePipeAcceptance>().AsSingleton();
    }
  }
  [Serializable] internal sealed class AquaculturePipeRecord {
    public string EntityId,GoodId;
    public float Volume;
  }
  [Serializable] internal sealed class AquacultureLineRecord {
    public string WorkshopId,TankId;
    public GroceryStockRecord[] Stocks;
    public AquaculturePipeRecord[] Pipes;
    public int TankWater;
    public float TankVolume;
  }
  internal sealed class AquaculturePipeAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private sealed class Line {
      public BlockObject Workshop;
      public Inventory Inventory;
      public PipeTank Tank;
      public ExtractionPipe Intake;
      public BuildingPipe[] Pipes;
      public HeadliftPipe Pump;
      public int Capacity;
      public int TotalWater;
      public int ConsumedWater,Batches,RequiredBatches;
      public bool ProductionChecked;
      public bool FlowObserved,WheelAdvanced;
      public float InitialWheelTime;
      public Vector3Int Port;
      public Direction3D Direction,WrongDirection;
    }
    private readonly EntityRegistry _entities;
    private readonly BlockObjectFactory _factory;
    private readonly TemplateService _templates;
    private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _objects;
    private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock;
    private readonly CameraService _camera;
    private readonly GameSaver _saver;
    private readonly GameLoader _loader;
    private readonly ITerrainService _terrain;
    private readonly List<ControllableCharacter> _observers=new();
    private readonly List<Line> _lines=new();
    private readonly bool _reload=Environment.GetCommandLineArgs().Contains("-deepFrontierAquaculturePipesReload");
    private int _frame,_phase;
    private float _start,_phaseTime;
    private bool _finished;
    public AquaculturePipeAcceptance(EntityRegistry entities,BlockObjectFactory factory,TemplateService templates,
      BlockValidator validator,BlockObjectValidationService objects,SpeedManager speed,IDayNightCycle clock,
      CameraService camera,GameSaver saver,GameLoader loader,ITerrainService terrain) {
      _entities=entities;_factory=factory;_templates=templates;_validator=validator;_objects=objects;
      _speed=speed;_clock=clock;_camera=camera;_saver=saver;_loader=loader;_terrain=terrain;
    }
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private static void Pass(string message) {Debug.Log("[DeepFrontier Aquaculture Pipes] PASS "+message);}
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"),
        "Pipe acceptance requires the marked disposable settlement");
      _speed.ChangeSpeed(0);
    }
    private BlockObject Find(string id) => _entities.Entities.Single(e=>e.HasComponent<TemplateSpec>()
      &&e.GetComponent<TemplateSpec>().TemplateName==id).GetComponent<BlockObject>();
    private BlockObject Create(string id,int x,int y,int z,Orientation orientation=Orientation.Cw0) {
      var template=_templates.GetAll<TemplateSpec>().Single(s=>s.TemplateName==id);
      var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
      var placement=new Placement(new Vector3Int(x,y,z),orientation,FlipMode.Unflipped);
      Require(_validator.BlocksValid(spec,placement),"Native placement rejected "+id+" "+placement.Coordinates);
      var result=_factory.CreateFinished(new EntitySetup.Builder(template.Blueprint)
        .AddInitComponent(new FinishedConstructionSiteInit()),placement);
      Require(_objects.IsValid(result),"Native requirements rejected "+id);
      Debug.Log("[DeepFrontier Aquaculture Pipes] PLACED "+id+" "+placement.Coordinates);
      return result;
    }
    private Line Workshop(string id,int capacity,Vector3Int localPort,Direction3D direction,Direction3D wrongDirection,bool clearWater) {
      var building=Find(id);
      Require(building.GetComponent<PausableBuilding>().Paused,"Expected saved paused workshop "+id);
      var inventory=building.GetComponent<Manufactory>().Inventory;
      int amount=inventory.AmountInStock("Water");
      Require(inventory.UnreservedAmountInStock("Water")==amount,"Water already reserved at "+id);
      if(clearWater&&amount>0)inventory.TakeConsumed(new GoodAmount("Water",amount));
      return new Line {Workshop=building,Inventory=inventory,Capacity=capacity,TotalWater=_reload?290:300,
        Port=building.TransformCoordinates(localPort),Direction=building.TransformDirection(direction),
        WrongDirection=building.TransformDirection(wrongDirection)};
    }
    private void Setup() {
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>()))
        e.GetComponent<PausableBuilding>().Pause();
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<ControllableCharacter>())) {
        var character=e.GetComponent<ControllableCharacter>();
        var idle=e.GetComponent<TemplateSpec>().TemplateName+"_idle";
        Require(character.GetAnimationNames().Contains(idle),"Missing native idle animation "+idle);
        character.ChangeAnimation(idle);
        character.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(character.Transform.position));_observers.Add(character);
      }
      // 11x8 Fishery (2026-10-22) at (159,162,3): its intake port is local (4,7,0) facing Up,
      // world (163,169,3), one cell west of the former 12x10 port (5,9,0) at (164,169,3).
      var fish=Workshop("FisheryWorks.IronTeeth",90,new Vector3Int(4,7,0),Direction3D.Up,Direction3D.Down,!_reload);
      Require(fish.Workshop.Coordinates==new Vector3Int(159,162,3),"Unexpected Fishery fixture position "+fish.Workshop.Coordinates);
      Require(fish.Port==new Vector3Int(163,169,3),"Fishery intake registration changed");
      // Compact 7x7 hatchery (2026-10-26): its canopy intake moved from (7,2,1) to (6,2,1).
      var nursery=Workshop("FishHatchery.IronTeeth",60,new Vector3Int(6,2,1),Direction3D.Right,Direction3D.Left,!_reload);
      Require(nursery.Port==new Vector3Int(193,158,3),"Hatchery intake must include its native BaseZ offset");
      _lines.Add(fish);_lines.Add(nursery);
      if(_reload) {
        LoadLines();
        SetCamera();return;
      }
      var fishValve=Create("HorizontalPipeValve.IronTeeth",163,170,3,Orientation.Cw180);
      var fishPipe=Create("HorizontalPipe.IronTeeth",163,171,3);
      var fishPump=Create("HorizontalPipePump.IronTeeth",163,172,3,Orientation.Cw180);
      var fishTank=Create("MediumTank.IronTeeth",163,173,3);
      Create("DevPowerGenerator",162,172,3);
      CompleteLine(fish,fishValve,fishPipe,fishPump,fishTank);
      PrepareNurseryPipePad();
      var hatchValve=Create("HorizontalPipeValve.IronTeeth",194,158,3,Orientation.Cw270);
      var hatchPipe=Create("HorizontalPipe.IronTeeth",195,158,3,Orientation.Cw90);
      var hatchPump=Create("HorizontalPipePump.IronTeeth",196,158,3,Orientation.Cw270);
      var hatchTank=Create("MediumTank.IronTeeth",197,158,3);
      Create("DevPowerGenerator",196,157,3);
      CompleteLine(nursery,hatchValve,hatchPipe,hatchPump,hatchTank);
      SetCamera();
    }
    private void PrepareNurseryPipePad() {
      Require(!_entities.Entities.Where(e=>e.HasComponent<BlockObject>()).Any(e=> {
        var c=e.GetComponent<BlockObject>().Coordinates;
        return c.x>=195&&c.x<=199&&c.y>=157&&c.y<=159;
      }),"Disposable nursery pipe pad contains an existing entity");
      // The earlier industrial fixture cleared terrain only through x=194.
      // Extend that explicit test pad with the native terrain service.
      for(int x=195;x<=199;x++)for(int y=157;y<=159;y++) {
        var surfaces=_terrain.GetAllHeightsInCell(new Vector2Int(x,y)).Where(c=>c.z>3).OrderByDescending(c=>c.z).ToArray();
        foreach(var top in surfaces)_terrain.UnsetTerrain(new Vector3Int(x,y,top.z-1),top.z-3);
        int height=_terrain.GetTerrainHeight(new Vector3Int(x,y,0));
        if(height<3)_terrain.SetTerrain(new Vector3Int(x,y,height),3-height);
        Require(_terrain.GetTerrainHeight(new Vector3Int(x,y,0))==3
          &&!Enumerable.Range(3,_terrain.Size.z-3).Any(z=>_terrain.Underground(new Vector3Int(x,y,z))),
          "Native test terrain is not clear at "+x+","+y);
      }
      Pass("prepared the marked settlement's nursery pipe pad through the native terrain service");
    }
    private void SetCamera() {
      _camera.MoveTargetTo(new Vector3(178,6,165));_camera.SetZoomLevel(37,0);
      _camera.HorizontalAngle=205;_camera.VerticalAngle=40;
    }
    private void LoadLines() {
      var records=JsonConvert.DeserializeObject<AquacultureLineRecord[]>(File.ReadAllText(
        "C:/Users/Jordan/Documents/TimberbornModding/outputs/aquaculture-pipe-reload-expectations.json"));
      Require(records!=null&&records.Length==2,"Expected both exact saved pipe lines");
      foreach(var line in _lines) {
        string id=line.Workshop.GetComponent<EntityComponent>().EntityId.ToString();
        var record=records.Single(r=>r.WorkshopId==id);
        Require(record.Stocks!=null&&record.Pipes!=null&&record.Pipes.Length==3,"Incomplete native pipe save record");
        Require(line.Inventory.TotalAmountInStock==record.Stocks.Sum(s=>s.Amount),"Saved workshop total changed");
        foreach(var stock in record.Stocks)
          Require(line.Inventory.AmountInStock(stock.Name)==stock.Amount,"Saved workshop stock changed: "+stock.Name);
        line.Tank=_entities.Entities.Single(e=>e.EntityId.ToString()==record.TankId).GetComponent<PipeTank>();
        var tankInventory=line.Tank.GetComponent<Stockpile>().Inventory;
        Require(tankInventory.AmountInStock("Water")==record.TankWater&&tankInventory.TotalAmountInStock==record.TankWater,
          "Saved tank stock changed");
        Require(Math.Abs(line.Tank.VolumeM3-record.TankVolume)<.00001f,"Saved tank fractional volume changed");
        line.Pipes=record.Pipes.Select(r=>_entities.Entities.Single(e=>e.EntityId.ToString()==r.EntityId).GetComponent<BuildingPipe>()).ToArray();
        for(int i=0;i<line.Pipes.Length;i++) {
          Require(Math.Abs(line.Pipes[i].FluidHeight-record.Pipes[i].Volume)<.00001f,"Saved in-pipe volume changed");
          Require(line.Pipes[i].FluidGoodId==record.Pipes[i].GoodId,"Saved in-pipe good changed");
        }
        line.Intake=line.Pipes[0].GetComponent<ExtractionPipe>();
        line.Pump=line.Pipes[2].GetComponent<HeadliftPipe>();
        Require(line.Intake.InletEnabled&&!line.Intake.OutletEnabled,"Saved input-only valve settings changed");
        Check(line,line.Capacity,line.TotalWater);
      }
      Pass("fresh process restored exact workshop/tank stocks, fractional tank volume, every pipe volume/good and valve settings");
    }
    private static void CompleteLine(Line line,BlockObject valve,BlockObject pipe,BlockObject pump,BlockObject tank) {
      tank.GetComponent<SingleGoodAllower>().Allow("Water");
      tank.GetComponent<Stockpile>().Inventory.GiveExisting(new GoodAmount("Water",300));
      line.Tank=tank.GetComponent<PipeTank>();
      line.Intake=valve.GetComponent<ExtractionPipe>();
      line.Intake.InletEnabled=true;line.Intake.OutletEnabled=false;
      line.Pipes=new[]{valve.GetComponent<BuildingPipe>(),pipe.GetComponent<BuildingPipe>(),pump.GetComponent<BuildingPipe>()};
      line.Pump=pump.GetComponent<HeadliftPipe>();
    }
    private void Start() {
      foreach(var line in _lines) {
        var target=line.Intake.FindInletTarget();
        Require(target!=null&&target.Target.BlockObject==line.Workshop,"Native valve did not find the authored intake face");
        Require(target.GetLiquidIds().Contains("Water"),"Native target has no Water recipe input");
        Require(!target.TryTransfer("Badwater",1),"Aquaculture accepted badwater into a clean-water recipe");
        var building=line.Workshop.GetComponent<BuildingPipeTarget>();
        Require(building.TryConnecting(line.Intake.Pipe,new PipePortDefinition(line.Port,line.Direction),false)==null,
          "Input-only machinery face exposes an outlet");
        Require(building.TryConnecting(line.Intake.Pipe,new PipePortDefinition(line.Port,line.WrongDirection),true)==null,
          "Unauthored machinery face accepted a pipe");
        Require(line.Pump.GetComponent<MechanicalNode>().GetComponent<MechanicalNodeSpec>().PowerInput==50,
          "Expected the installed pump's 50 hp demand");
        Require(line.Inventory.AmountInStock("Water")==(_reload?line.Capacity:0),"Workshop water changed before pipe simulation");
        if(_reload) {
          line.Inventory.TakeConsumed(new GoodAmount("Water",10));line.TotalWater-=10;
        }
      }
      Pass("native valves resolve both explicit intake faces, reject wrong faces/badwater and preserve native Water inventories");
      _start=_clock.PartialDayNumber;Phase(1);_speed.ChangeSpeed(3);
    }
    private void Phase(int phase) {_phase=phase;_phaseTime=_clock.PartialDayNumber;}
    private static void Check(Line line,int expected,int expectedTotal) {
      Require(line.Inventory.AmountInStock("Water")==expected,"Unexpected recipe Water stock");
      float total=line.Inventory.AmountInStock("Water")+5f*(line.Tank.VolumeM3+line.Pipes.Sum(p=>p.FluidHeight));
      Require(Math.Abs(total+line.ConsumedWater-expectedTotal)<.02f,"Water lost or duplicated between tank, pipes and workshop: "+total
        +" consumed="+line.ConsumedWater+" expected="+expectedTotal);
      var reservoir=line.Workshop.GetComponent<WorkshopReservoir>();
      Require(reservoir.StoredAmount==expected&&reservoir.SurfacesVisible==(expected>0),"Visible reservoir differs from real pipe-fed stock");
      Require(!reservoir.Flowing,"Paused factory must not show production circulation");
      Require(line.Pipes.All(p=>!p.IsContaminated),"Clean supply contaminated its pipe network");
    }
    private void StartProduction() {
      foreach(var observer in _observers)observer.ReleaseControl();
      _observers.Clear();
      var workers=_entities.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>())
        .Where(w=>w.WorkerType=="Beaver").Take(5).ToArray();
      Require(workers.Length==5,"Production fixture needs five native workers");
      int next=0;
      foreach(var line in _lines) {
        var manufactory=line.Workshop.GetComponent<Manufactory>();
        line.RequiredBatches=manufactory.CurrentRecipe.Id=="FreshFish"?2:1;
        var reservoir=line.Workshop.GetComponent<WorkshopReservoir>();
        if(manufactory.CurrentRecipe.Id=="FreshFish")line.InitialWheelTime=reservoir.WheelTimes.Single();
        manufactory.ProductionFinished+=(sender,args)=>line.Batches++;
        line.Inventory.InventoryStockChanged+=(sender,args)=> {
          if(args.GoodAmount.GoodId=="Water"&&args.StockChangeType==StockChangeType.Consumed) {
            Require(args.GoodAmount.Amount<0,"Production Water must be a debit");
            line.ConsumedWater-=args.GoodAmount.Amount;
          }
        };
        line.Workshop.GetComponent<PausableBuilding>().Resume();
        var workplace=line.Workshop.GetComponent<Workplace>();
        foreach(var assigned in workplace.AssignedWorkers.ToArray())assigned.Unemploy();
        int count=manufactory.CurrentRecipe.Id=="FreshFish"?3:2;
        for(int i=0;i<count;i++) {workers[next].Unemploy();workers[next++].EmployAt(workplace);}
      }
      Phase(4);
    }
    private void Finish() {
      foreach(var observer in _observers)observer.ReleaseControl();
      _speed.ChangeSpeed(0);_finished=true;
      var directory=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
        "TimberbornModding","docs","art","reviews","2026-10-20-aquaculture-transport");
      Directory.CreateDirectory(directory);
      ScreenCapture.CaptureScreenshot(Path.Combine(directory,_reload?"aquaculture-pipe-reload.png":"aquaculture-pipe-delivery.png"));
      _saver.QueueSave(new SaveReference(_reload?"Aquaculture pipe continuity - verified":"Aquaculture pipes - verified",_loader.LoadedSave.SettlementReference),
        ()=>Debug.Log("[DeepFrontier Aquaculture Pipes] "+(_reload?"ALL RELOAD, VOLUME AND PIPE-FED PRODUCTION CHECKS PASSED AND SAVED"
          :"ALL DELIVERY, CAPACITY, VALVE AND RESERVOIR CHECKS PASSED AND SAVED")));
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60)Setup();
        if(_frame==240)Start();
        if(_frame<=240)return;
        if(_frame%600==0)Debug.Log("[DeepFrontier Aquaculture Pipes] STATUS phase="+_phase+" water="
          +string.Join(",",_lines.Select(l=>l.Inventory.AmountInStock("Water"))));
        float hours=(_clock.PartialDayNumber-_phaseTime)*24;
        if(_phase==1&&_lines.All(l=>l.Inventory.AmountInStock("Water")==l.Capacity)&&hours>=.5f) {
          foreach(var line in _lines) {
            Require(line.Pump.WorkFactor>0,"Powered pump has no native headlift");
            Check(line,line.Capacity,line.TotalWater);
            line.Intake.InletEnabled=false;
            line.Inventory.TakeConsumed(new GoodAmount("Water",10));
            line.TotalWater-=10;
          }
          Pass("real tanks and pipes fill both factory buffers to capacity with conserved water and matching native surfaces");
          Phase(2);
        } else if(_phase==2&&hours>=.5f) {
          foreach(var line in _lines) {Check(line,line.Capacity-10,line.TotalWater);line.Intake.InletEnabled=true;}
          Pass("closing each valve stops replenishment while preserving water in the network");Phase(3);
        } else if(_phase==3&&_lines.All(l=>l.Inventory.AmountInStock("Water")==l.Capacity)&&hours>=.25f) {
          foreach(var line in _lines)Check(line,line.Capacity,line.TotalWater);
          Pass("reopened valves refill native factory inventories without overfilling or losing water");
          if(_reload)StartProduction();else Finish();
        } else if(_phase==4) {
          foreach(var line in _lines.Where(l=>!l.ProductionChecked)) {
            var reservoir=line.Workshop.GetComponent<WorkshopReservoir>();
            if(reservoir.Flowing&&reservoir.SurfacesVisible&&reservoir.StoredAmount>0)line.FlowObserved=true;
            if(line.Workshop.GetComponent<Manufactory>().CurrentRecipe.Id=="FreshFish"
              &&reservoir.WheelsEnabled&&reservoir.WheelTimes.Single()!=line.InitialWheelTime)line.WheelAdvanced=true;
          }
          foreach(var line in _lines.Where(l=>!l.ProductionChecked&&l.Batches>=l.RequiredBatches&&l.ConsumedWater>0)) {
            Require(line.FlowObserved,"Pipe-fed production never displayed native water flow");
            if(line.Workshop.GetComponent<Manufactory>().CurrentRecipe.Id=="FreshFish")
              Require(line.WheelAdvanced,"Pipe-fed Fishery never advanced its native water wheel");
            line.Workshop.GetComponent<PausableBuilding>().Pause();line.ProductionChecked=true;
            Pass(line.Workshop.GetComponent<TemplateSpec>().TemplateName+" completed "+line.Batches
              +" native batches using "+line.ConsumedWater+" pipe-fed Water");
          }
          if(_lines.All(l=>l.ProductionChecked))Phase(5);
        } else if(_phase==5&&hours>=.25f&&_lines.All(l=>l.Inventory.AmountInStock("Water")==l.Capacity)) {
          foreach(var line in _lines)Check(line,line.Capacity,line.TotalWater);
          Pass("pipe delivery replaced actual recipe consumption; saved water conservation includes every production debit");
          Finish();
        }
        Require(_phase>=4?hours<36:(_clock.PartialDayNumber-_start)*24<12,"Pipe acceptance exceeded its simulation time limit");
      } catch(Exception error) {_finished=true;_speed.ChangeSpeed(0);Debug.LogError("[DeepFrontier Aquaculture Pipes] FAILED: "+error);}
    }
  }
}
#endif
