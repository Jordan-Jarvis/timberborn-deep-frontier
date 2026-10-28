#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using ConveyorBelt.Components;
using ConveyorBelt.Services;
using Newtonsoft.Json;
using PowerLines.Components;
using PowerLines.Services;
using TimberPipes.Components;
using TimberPipes.Models;
using TimberPipes.Specs;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.CameraSystem;
using Timberborn.CharacterControlSystem;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.Effects;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.MechanicalSystem;
using Timberborn.NeedSystem;
using Timberborn.SingletonSystem;
using Timberborn.Stockpiles;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using Timberborn.Workshops;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class FactoryTransportAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierFactoryTransport")
        ||Environment.GetCommandLineArgs().Contains("-deepFrontierFactoryTransportReload")
        ||Environment.GetCommandLineArgs().Contains("-deepFrontierFactoryPowerLines")
        ||Environment.GetCommandLineArgs().Contains("-deepFrontierFactoryPowerLinesReload"))
        Bind<FactoryTransportAcceptance>().AsSingleton();
    }
  }
  [Serializable] internal sealed class FactoryTransportRecord {
    public string MixerId,TankId,RemoteSourceId;
    public GroceryStockRecord[] MixerStock;
    public GroceryBeltStockRecord[] Stores;
    public GroceryBeltRecord[] Belts;
    public AquaculturePipeRecord[] Pipes;
    public float Progress,TankVolume,WaterTotal;
    public int TankStock;
    public Dictionary<string,int> SolidTotals;
  }
  // Explicit disposable fixture only; normal play uses the dependencies'
  // native inventory connections and the authored intake face.
  internal sealed class FactoryTransportAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private const string RecordPath="C:/Users/Jordan/Documents/TimberbornModding/outputs/factory-transport-expectations.json";
    private const string PowerRecordPath="C:/Users/Jordan/Documents/TimberbornModding/outputs/factory-power-lines-expectations.json";
    private static readonly string[] Solids={"Aggregate","Cement","Concrete"};
    private static readonly Vector3Int MixerIntake=new(6,4,0);
    private static readonly string[] MixerGoods={"Aggregate","Cement","Water","Concrete"};
    private readonly EntityRegistry _entities;
    private readonly BlockObjectFactory _factory;
    private readonly TemplateService _templates;
    private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _objects;
    private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock;
    private readonly WorkingHoursManager _hours;
    private readonly CameraService _camera;
    private readonly GameSaver _saver;
    private readonly GameLoader _loader;
    private readonly BeltGoodService _beltGoods;
    private readonly PowerLineConnectionService _lines;
    private readonly List<ControllableCharacter> _observers=new();
    private readonly List<Inventory> _disabled=new();
    private readonly List<BeltCarrier> _belts=new();
    private readonly List<Inventory> _stores=new();
    private readonly Dictionary<MechanicalNode,float> _supplies=new();
    private readonly Dictionary<string,int> _consumed=MixerGoods.ToDictionary(g=>g,g=>0);
    private readonly Dictionary<string,int> _baseline=new();
    private readonly bool _reload=Environment.GetCommandLineArgs().Contains("-deepFrontierFactoryTransportReload");
    private readonly bool _power=Environment.GetCommandLineArgs().Contains("-deepFrontierFactoryPowerLines")
      ||Environment.GetCommandLineArgs().Contains("-deepFrontierFactoryPowerLinesReload");
    private readonly bool _powerReload=Environment.GetCommandLineArgs().Contains("-deepFrontierFactoryPowerLinesReload");
    private BlockObject _building;
    private Manufactory _mixer;
    private PipeTank _tank;
    private BuildingPipe[] _pipes;
    private ExtractionPipe _valve;
    private HeadliftPipe _pump;
    private MechanicalNode _remoteSource;
    private bool _loadObserved;
    private int _frame,_phase,_batches;
    private float _phaseTime,_normalHours,_waterBaseline;
    private bool _finished,_outputPaused;
    public FactoryTransportAcceptance(EntityRegistry entities,BlockObjectFactory factory,TemplateService templates,
      BlockValidator validator,BlockObjectValidationService objects,SpeedManager speed,IDayNightCycle clock,
      WorkingHoursManager hours,CameraService camera,GameSaver saver,GameLoader loader,BeltGoodService beltGoods,
      PowerLineConnectionService lines) {
      _entities=entities;_factory=factory;_templates=templates;_validator=validator;_objects=objects;
      _speed=speed;_clock=clock;_hours=hours;_camera=camera;_saver=saver;_loader=loader;_beltGoods=beltGoods;
      _lines=lines;
    }
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private static void Pass(string message) {Debug.Log("[DeepFrontier Factory Transport] PASS "+message);}
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"),
        "Factory transport acceptance requires the marked disposable settlement");
      _speed.ChangeSpeed(0);
    }
    private BlockObject Create(string id,int x,int y,int z,Orientation orientation=Orientation.Cw0) {
      var template=_templates.GetAll<TemplateSpec>().Single(s=>s.TemplateName==id);
      var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
      var placement=new Placement(new Vector3Int(x,y,z),orientation,FlipMode.Unflipped);
      Require(_validator.BlocksValid(spec,placement),"Native placement rejected "+id+" "+placement.Coordinates);
      var result=_factory.CreateFinished(new EntitySetup.Builder(template.Blueprint)
        .AddInitComponent(new FinishedConstructionSiteInit()),placement);
      Require(_objects.IsValid(result),"Native requirements rejected "+id);
      Debug.Log("[DeepFrontier Factory Transport] PLACED "+id+" "+placement.Coordinates);
      return result;
    }
    private void Setup() {
      _building=_entities.Entities.Single(e=>e.HasComponent<TemplateSpec>()
        &&e.GetComponent<TemplateSpec>().TemplateName=="ConcreteMixer.IronTeeth").GetComponent<BlockObject>();
      Require(_building.Coordinates==new Vector3Int(159,160,3),"Unexpected mixer fixture position");
      // 7x5 mixer (2026-10-22, footprint at the walls; local frame unchanged). Its outward
      // ground-layer shaft faces (outputs/connection-faces/ConcreteMixer.json, flatness rule) are
      // the west wall x 0 rows 0..3 facing Left, (0,3,0) facing Up into the open corner cell
      // (0,4,0), and (0,0,0)/(2,0,0) facing the road or the open front cells. The braced rear
      // tank tower (6,4) offers no shaft face. Its water intake is the first pipe port (6,4,0)
      // facing Right and its cable anchor PowerLineSpec (6.9,4.9,3.8). The lanes and the shaft
      // line below meet those faces, so belts and pump share the mixer's mechanical graph.
      var mixerSpec=_building.GetComponent<BlockObjectSpec>();
      // The tested intake is the first port; the generated ports on the mixer's
      // other flat exterior faces follow it (tools/connection_content.mjs).
      var intake=_building.GetComponent<BuildingPipeTargetPortsSpec>().Ports[0];
      Require(mixerSpec.Size==new Vector3Int(7,5,7)&&intake.Coordinates==MixerIntake&&intake.Directions.ToString()=="Right",
        "Installed mixer is "+mixerSpec.Size+" with intake "+intake.Coordinates+" "+intake.Directions+
        "; this fixture's lanes and pipe line encode the 7x5x7 mixer with its intake at "+MixerIntake+" Right");
      var faces=_building.GetComponent<TransputProviderSpec>().Transputs;
      bool Offers(Vector3Int cell,string direction)=>faces.Any(t=>t.Coordinates==cell
        &&t.Directions.ToString().Split(',').Select(d=>d.Trim()).Contains(direction));
      Require(Offers(new Vector3Int(0,1,0),"Left")&&Offers(new Vector3Int(0,2,0),"Left")&&Offers(new Vector3Int(0,3,0),"Left")
        &&Offers(new Vector3Int(0,3,0),"Up")&&!Offers(new Vector3Int(6,4,0),"Up"),
        "Installed mixer shaft faces differ from the west wall rows 1..3 Left and (0,3,0) Up that this fixture's lanes and shaft line use");
      Require(_building.GetComponent<PausableBuilding>().Paused,"Expected saved paused mixer");
      _mixer=_building.GetComponent<Manufactory>();
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>()))
        e.GetComponent<PausableBuilding>().Pause();
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<ControllableCharacter>())) {
        var character=e.GetComponent<ControllableCharacter>();
        string idle=e.GetComponent<TemplateSpec>().TemplateName+"_idle";
        Require(character.GetAnimationNames().Contains(idle),"Missing native idle animation "+idle);
        character.ChangeAnimation(idle);
        character.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(character.Transform.position));
        _observers.Add(character);
      }
      if(_reload||_power)Load();
      else {
        foreach(var good in MixerGoods) {
          int stock=_mixer.Inventory.AmountInStock(good);
          Require(_mixer.Inventory.UnreservedAmountInStock(good)==stock,"Reserved starting mixer stock");
          if(good!="Concrete"&&stock>0)_mixer.Inventory.TakeExisting(new GoodAmount(good,stock));
        }
        Require(_mixer.Inventory.AmountInStock("Concrete")==12&&_mixer.ProductionProgress==0,
          "Expected main mixer acceptance checkpoint");
        // West lanes on the wall faces of rows 1..3 (row 0 holds the mixer's saved shaft):
        // Cw270 belts run east into the mixer, the Cw90 Concrete lane runs west out of it.
        // Each warehouse faces its lane (entrance on the belt), as the former rear lanes did.
        for(int lane=0;lane<3;lane++) {
          int y=161+lane;
          var orientation=lane==2?Orientation.Cw90:Orientation.Cw270;
          for(int x=158;x>=157;x--)
            _belts.Add(Create("ConveyorBeltSp1.IronTeeth",x,y,3,orientation).GetComponent<BeltCarrier>());
          var store=Create("SmallWarehouse.IronTeeth",156,y,3,Orientation.Cw270);
          store.GetComponent<SingleGoodAllower>().Allow(Solids[lane]);
          var inventory=store.GetComponent<Stockpile>().Inventory;
          _stores.Add(inventory);
          if(lane<2)inventory.GiveExisting(new GoodAmount(Solids[lane],lane==0?30:12));
        }
        // Pipe line east of the intake (6,4,0) Right, world (165,164,3).
        var valve=Create("HorizontalPipeValve.IronTeeth",166,164,3,Orientation.Cw270);
        var pipe=Create("HorizontalPipe.IronTeeth",167,164,3,Orientation.Cw90);
        var pump=Create("HorizontalPipePump.IronTeeth",168,164,3,Orientation.Cw270);
        var tank=Create("MediumTank.IronTeeth",169,164,3);
        Create("DevPowerGenerator",168,163,3);
        // Vanilla shaft line from the mixer's (0,3,0) Up face: the open corner cell (0,4,0),
        // world (159,164,3), then north to (159,165,3) and east along the freed former rear
        // row y 165 to the pump's north face at (168,165,3). Pump, its generator and the tank
        // line share the mixer's graph through it.
        Create("PowerShaft.IronTeeth",159,164,3);
        for(int x=159;x<=168;x++)Create("PowerShaft.IronTeeth",x,165,3);
        tank.GetComponent<SingleGoodAllower>().Allow("Water");
        tank.GetComponent<Stockpile>().Inventory.GiveExisting(new GoodAmount("Water",300));
        _tank=tank.GetComponent<PipeTank>();_pump=pump.GetComponent<HeadliftPipe>();
        _valve=valve.GetComponent<ExtractionPipe>();_valve.InletEnabled=true;_valve.OutletEnabled=false;
        _pipes=new[]{valve.GetComponent<BuildingPipe>(),pipe.GetComponent<BuildingPipe>(),pump.GetComponent<BuildingPipe>()};
        _baseline.Add("Aggregate",30);_baseline.Add("Cement",12);_baseline.Add("Concrete",12);
        _waterBaseline=300;
      }
      if(_power&&!_powerReload) {
        // Additional declared donor stock allows both cable runs to finish
        // with native full buffers and real incoming items still queued.
        _stores[0].GiveExisting(new GoodAmount("Aggregate",24));_baseline["Aggregate"]+=24;
        _stores[1].GiveExisting(new GoodAmount("Cement",8));_baseline["Cement"]+=8;
        _remoteSource=Create("DevPowerGenerator",169,168,3).GetComponent<MechanicalNode>();
      }
      // Isolate unrelated factory outputs at their supply source. The three
      // new stores have no road connection, and idle test beavers cannot haul.
      foreach(var inventory in _entities.Entities.Where(e=>e.HasComponent<Inventories>())
        .SelectMany(e=>e.GetComponent<Inventories>().AllInventories)
        .Where(i=>i!=_mixer.Inventory&&!_stores.Contains(i)&&i.Enabled&&i.PublicOutput
          &&Solids.Any(g=>i.OutputGoods.Contains(g)))) {
        inventory.Disable();_disabled.Add(inventory);
      }
      _mixer.Inventory.InventoryStockChanged+=(sender,args)=>{
        if(args.StockChangeType==StockChangeType.Consumed&&args.GoodAmount.Amount<0
          &&_consumed.ContainsKey(args.GoodAmount.GoodId))
          _consumed[args.GoodAmount.GoodId]-=args.GoodAmount.Amount;
      };
      _mixer.ProductionFinished+=(sender,args)=>{
        _batches++;Debug.Log("[DeepFrontier Factory Transport] BATCH "+_batches);
        // Stop at the native batch boundary so checkpoint ingredients are not
        // prepaid by another production tick before the observer updates.
        if(_batches==2)_building.GetComponent<PausableBuilding>().Pause();
      };
      _normalHours=_hours.WorkedPartOfDay;_hours.WorkedPartOfDay=1;
      _camera.MoveTargetTo(new Vector3(162,5,163));_camera.SetZoomLevel(23,0);
      _camera.HorizontalAngle=205;_camera.VerticalAngle=35;
      // BeltRegistry wires physical lanes during native simulation Prepare.
      // Exact saved-state checks above run before this first simulation step.
      _speed.ChangeSpeed(1);
    }
    private EntityComponent Entity(string id)=>_entities.Entities.Single(e=>e.EntityId.ToString()==id);
    private static void CheckStock(Inventory inventory,GroceryStockRecord[] records) {
      Require(records!=null&&inventory.TotalAmountInStock==records.Sum(s=>s.Amount),"Saved inventory total changed");
      foreach(var s in records)Require(inventory.AmountInStock(s.Name)==s.Amount,"Saved stock changed: "+s.Name);
    }
    private void Load() {
      var saved=JsonConvert.DeserializeObject<FactoryTransportRecord>(File.ReadAllText(_powerReload?PowerRecordPath:RecordPath));
      Require(saved!=null&&saved.Stores.Length==3&&saved.Belts.Length==6&&saved.Pipes.Length==3,
        "Incomplete factory transport save expectations");
      Require(_building.GetComponent<EntityComponent>().EntityId.ToString()==saved.MixerId,"Saved mixer identity changed");
      CheckStock(_mixer.Inventory,saved.MixerStock);
      Require(Math.Abs(_mixer.ProductionProgress-saved.Progress)<.00001f,"Saved progress changed");
      foreach(var store in saved.Stores) {
        var inventory=Entity(store.EntityId).GetComponent<Stockpile>().Inventory;
        CheckStock(inventory,store.Stocks);_stores.Add(inventory);
      }
      foreach(var item in saved.Belts) {
        var belt=Entity(item.EntityId).GetComponent<BeltCarrier>();
        Require(belt.Sim.Items.Select(g=>g.Serialize()).SequenceEqual(item.Items),"Saved belt queue changed");
        _belts.Add(belt);
      }
      Require(saved.Belts.Take(4).Sum(b=>b.Items.Length)>0,"Expected saved incoming belt items");
      _tank=Entity(saved.TankId).GetComponent<PipeTank>();
      Require(_tank.GetComponent<Stockpile>().Inventory.AmountInStock("Water")==saved.TankStock
        &&Math.Abs(_tank.VolumeM3-saved.TankVolume)<.00001f,"Saved tank stock/fraction changed");
      _pipes=saved.Pipes.Select(p=>Entity(p.EntityId).GetComponent<BuildingPipe>()).ToArray();
      for(int i=0;i<3;i++)
        Require(_pipes[i].FluidGoodId==saved.Pipes[i].GoodId&&Math.Abs(_pipes[i].FluidHeight-saved.Pipes[i].Volume)<.00001f,
          "Saved pipe liquid changed");
      _valve=_pipes[0].GetComponent<ExtractionPipe>();_pump=_pipes[2].GetComponent<HeadliftPipe>();
      Require(_valve.InletEnabled&&!_valve.OutletEnabled,"Saved valve settings changed");
      if(_powerReload) {
        Require(!string.IsNullOrEmpty(saved.RemoteSourceId),"Missing saved cable source identity");
        _remoteSource=Entity(saved.RemoteSourceId).GetComponent<MechanicalNode>();
        var partners=_lines.GetConnectedPowerLines(_remoteSource.GetComponent<PowerLineComponent>()).ToArray();
        Require(partners.Length==1&&partners[0]==_building.GetComponent<PowerLineComponent>(),
          "Saved Power Lines endpoints changed");
        Pass("fresh process restored the native Power Lines connection and exact remote source identity");
      }
      foreach(var good in Solids)_baseline.Add(good,saved.SolidTotals[good]);
      _waterBaseline=saved.WaterTotal;
      Pass("fresh process restored exact inventories, recipe progress, six belt queues, pipe volumes and tank fraction");
    }
    private void Start() {
      if(!_power)Require(_belts.All(b=>b.Running),"A factory belt has no native power");
      Require(_belts[0].OutPort.Target==new Vector3Int(159,161,3)
        &&_belts[2].OutPort.Target==new Vector3Int(159,162,3)
        &&_belts[4].InPort.Target==new Vector3Int(159,163,3),"Belt endpoint orientation differs");
      Require(_belts.All(b=>b.Sim.Output!=null)
        &&_belts[1].Sim.Input!=null&&_belts[3].Sim.Input!=null&&_belts[4].Sim.Input!=null,
        "Disconnected factory belt inventory endpoint");
      // BeltLink reports CanAccept separately from its target identity. A full
      // saved lane remains connected even when it cannot accept another item.
      _belts[1].Sim.Output.TryGetTarget("Aggregate",out var aggregateNext);
      _belts[3].Sim.Output.TryGetTarget("Cement",out var cementNext);
      _belts[4].Sim.Output.TryGetTarget("Concrete",out var concreteNext);
      Require(ReferenceEquals(aggregateNext,_belts[0].Sim)
        &&ReferenceEquals(cementNext,_belts[2].Sim)
        &&ReferenceEquals(concreteNext,_belts[5].Sim),"Native belt-to-belt lane connection differs");
      var inventories=_building.GetComponent<Inventories>();
      Require(!_beltGoods.TryGive(_building,inventories,"Log")&&!_beltGoods.TryGive(_building,inventories,"Water"),
        "Factory belt accepts a wrong solid or liquid");
      var target=_valve.FindInletTarget();
      Require(target!=null&&target.Target.BlockObject==_building,"Pipe missed the authored mixer intake");
      Require(!target.TryTransfer("Badwater",1),"Mixer intake accepted Badwater");
      var pipeTarget=_building.GetComponent<BuildingPipeTarget>();
      var port=_building.TransformCoordinates(MixerIntake);
      Require(pipeTarget.TryConnecting(_valve.Pipe,new PipePortDefinition(port,Direction3D.Right),false)==null
        &&pipeTarget.TryConnecting(_valve.Pipe,new PipePortDefinition(port,Direction3D.Left),true)==null,
        "Mixer inlet permits withdrawal or a wrong face");
      foreach(var graph in _belts.Select(b=>b.GetComponent<MechanicalNode>().Graph)
        .Append(_pump.GetComponent<MechanicalNode>().Graph).Distinct()) {
        Require(graph.BatteryCapacity==0,"Transport power-cut test must not include flywheel charge");
        foreach(var generator in graph.Generators) {
          Require(generator.GetComponent<TemplateSpec>().TemplateName=="DevPowerGenerator","Uncontrolled power source in fixture");
          if(generator!=_remoteSource)_supplies.Add(generator,generator.OutputMultiplier);
        }
      }
      Require(_supplies.Count>0,"No native transport power supply");
      CheckConservation();
      Pass("native belt input/output connections and intake-only water face resolve; wrong goods and faces are rejected");
      if(_powerReload) {
        // The exact checkpoint stock was verified above. The 30-unit receiving
        // warehouse needs room for the next eight units; explicitly export one
        // prior two-batch lot, recording that withdrawal in conservation.
        Require(_stores[2].AmountInStock("Concrete")>=8,"No previous Concrete lot to export");
        _stores[2].TakeExisting(new GoodAmount("Concrete",8));
        _baseline["Concrete"]-=8;
        CheckConservation();
        Pass("fixture exported eight previously received Concrete after exact reload verification");
      }
      if(_power) {
        foreach(var generator in _supplies.Keys)generator.SetOutputMultiplier(0);
        _remoteSource.SetOutputMultiplier(0);
        var location=_building.TransformCoordinates(new Vector3(6.9f,4.9f,3.8f));
        Require(_building.GetComponent<PowerLineComponent>().ConnectionLocations.Length==1
          &&Vector3.Distance(_building.GetComponent<PowerLineComponent>().ConnectionLocations[0],location)<.00001f,
          "Mixer cable anchor is not on the authored rear frame");
        if(!_powerReload)Require(_remoteSource.Graph!=_building.GetComponent<MechanicalNode>().Graph
          &&_remoteSource.Graph!=_pump.GetComponent<MechanicalNode>().Graph,"Remote power source already has a shaft connection");
        Phase(10);_speed.ChangeSpeed(3);return;
      }
      Phase(_reload?6:1);
      if(_reload)StartProduction();
      _speed.ChangeSpeed(3);
    }
    private int SolidTotal(string good)=>_mixer.Inventory.AmountInStock(good)
      +_stores.Sum(i=>i.AmountInStock(good))+_belts.Sum(b=>b.Sim.Items.Count(g=>g.Id==good));
    private float WaterTotal()=>_mixer.Inventory.AmountInStock("Water")
      +5f*(_tank.VolumeM3+_pipes.Sum(p=>p.FluidHeight));
    private bool Full()=>_mixer.Inventory.AmountInStock("Aggregate")==12
      &&_mixer.Inventory.AmountInStock("Cement")==4&&_mixer.Inventory.AmountInStock("Water")==8;
    private void CheckConservation() {
      foreach(var good in Solids) {
        int expected=_baseline[good]+(good=="Concrete"?4*_batches:-_consumed[good]);
        Require(SolidTotal(good)==expected,"Solid conservation failed: "+good+" actual="+SolidTotal(good)+" expected="+expected);
      }
      Require(Math.Abs(WaterTotal()+_consumed["Water"]-_waterBaseline)<.02f,
        "Water conservation failed: actual="+WaterTotal()+" consumed="+_consumed["Water"]+" baseline="+_waterBaseline);
      Require(_belts.Take(2).All(b=>b.Sim.Items.All(g=>g.Id=="Aggregate"))
        &&_belts.Skip(2).Take(2).All(b=>b.Sim.Items.All(g=>g.Id=="Cement"))
        &&_belts.Skip(4).All(b=>b.Sim.Items.All(g=>g.Id=="Concrete")),"Belt lane contains a wrong good");
      Require(_mixer.Inventory.AmountInStock("Aggregate")<=12&&_mixer.Inventory.AmountInStock("Cement")<=4
        &&_mixer.Inventory.AmountInStock("Water")<=8,"Delivery exceeded native recipe capacity");
      var visual=_building.GetComponent<WorkshopReservoir>();
      Require(visual.StoredAmount==_mixer.Inventory.AmountInStock("Water"),"Pipe-fed tank visual differs from native Water stock");
    }
    private void Phase(int value) {_phase=value;_phaseTime=_clock.PartialDayNumber;}
    private void StartProduction() {
      Require(_stores[2].HasUnreservedCapacity(new GoodAmount("Concrete",8)),
        "Receiving warehouse lacks capacity for the two declared production batches");
      var workers=_entities.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>())
        .Where(w=>w.WorkerType=="Beaver").Take(2).ToArray();
      Require(workers.Length==2,"Fixture requires two beaver workers");
      _building.GetComponent<PausableBuilding>().Resume();
      foreach(var worker in workers) {
        // The disposable long-running test settlement has no food economy.
        // Seed only basic needs once, before assigning these two test workers.
        var needs=worker.GetComponent<NeedManager>();
        foreach(var id in new[]{"Hunger","Thirst","Sleep"})
          needs.ApplyEffect(new InstantEffect(id,needs.GetNeedSpec(id).MaximumValue-needs.GetNeedPoints(id),1));
        var character=worker.GetComponent<ControllableCharacter>();
        character.ReleaseControl();_observers.Remove(character);
        worker.Unemploy();worker.EmployAt(_building.GetComponent<Workplace>());
      }
      Phase(6);
    }
    private void ConnectPowerLines() {
      var remote=_remoteSource.GetComponent<PowerLineComponent>();
      var target=_building.GetComponent<PowerLineComponent>();
      Require(_lines.EvaluateConnection(remote,target).CanConnect,"Authored cable route is out of range or occupied");
      _lines.Connect(remote,target);
      Require(!_lines.EvaluateConnection(remote,target).CanConnect,"Duplicate cable was accepted");
      Require(!_lines.EvaluateConnection(remote,remote).CanConnect,"Self cable was accepted");
    }
    private void EnableRemotePower() {
      Require(_remoteSource.GetComponent<MechanicalNodeSpec>().PowerOutput==10000,"Unexpected native test generator");
      _remoteSource.SetOutputMultiplier(.035f); // Exactly 350 hp in this isolated fixture.
    }
    private static GroceryStockRecord[] Stock(Inventory inventory,IEnumerable<string> goods)
      =>goods.Select(g=>new GroceryStockRecord{Name=g,Amount=inventory.AmountInStock(g)}).ToArray();
    private void Finish() {
      CheckConservation();
      Require(_belts.Take(4).Sum(b=>b.Sim.Items.Count)>0,"Checkpoint needs incoming goods queued behind full buffers");
      _speed.ChangeSpeed(0);_hours.WorkedPartOfDay=_normalHours;_finished=true;
      if((!_reload&&!_power)||(_power&&!_powerReload)) {
        var record=new FactoryTransportRecord {
          MixerId=_building.GetComponent<EntityComponent>().EntityId.ToString(),
          MixerStock=Stock(_mixer.Inventory,MixerGoods),Progress=_mixer.ProductionProgress,
          Stores=_stores.Select(i=>new GroceryBeltStockRecord {
            EntityId=i.GetComponent<EntityComponent>().EntityId.ToString(),Stocks=Stock(i,Solids)}).ToArray(),
          Belts=_belts.Select(b=>new GroceryBeltRecord {
            EntityId=b.GetComponent<EntityComponent>().EntityId.ToString(),Items=b.Sim.Items.Select(g=>g.Serialize()).ToArray()}).ToArray(),
          Pipes=_pipes.Select(p=>new AquaculturePipeRecord {
            EntityId=p.GetComponent<EntityComponent>().EntityId.ToString(),GoodId=p.FluidGoodId,Volume=p.FluidHeight}).ToArray(),
          TankId=_tank.GetComponent<EntityComponent>().EntityId.ToString(),
          TankStock=_tank.GetComponent<Stockpile>().Inventory.AmountInStock("Water"),
          TankVolume=_tank.VolumeM3,WaterTotal=WaterTotal(),
          SolidTotals=Solids.ToDictionary(g=>g,g=>SolidTotal(g)),
          RemoteSourceId=_power?_remoteSource.GetComponent<EntityComponent>().EntityId.ToString():null,
        };
        File.WriteAllText(_power?PowerRecordPath:RecordPath,JsonConvert.SerializeObject(record,Formatting.Indented));
      }
      foreach(var inventory in _disabled)inventory.Enable();_disabled.Clear();
      foreach(var observer in _observers)observer.ReleaseControl();_observers.Clear();
      if(_power)Require(_loadObserved,"Cable run never observed the actual complete factory demand");
      var name=_power?(_powerReload?"Factory power lines continuity - verified":"Factory power lines - verified"):
        (_reload?"Factory transport continuity - verified":"Factory transport - verified");
      _saver.QueueSave(new SaveReference(name,_loader.LoadedSave.SettlementReference),
        ()=>Debug.Log("[DeepFrontier Factory Transport] ALL "+((_reload||_powerReload)?"RELOAD AND ":"")
          +(_power?"POWER LINES, ":"")+"TRANSPORT AND PRODUCTION CHECKS PASSED AND SAVED"));
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60)Setup();if(_frame==240)Start();if(_frame<=240)return;
        float elapsed=(_clock.PartialDayNumber-_phaseTime)*24;
        if(_power&&_phase==6) {
          var node=_building.GetComponent<MechanicalNode>();
          if(node.Actuals.PowerInput==250) {
            Require(node.Graph==_remoteSource.Graph&&_pump.GetComponent<MechanicalNode>().Graph==node.Graph,
              "Cable supply does not join the factory and pump graphs");
            Require(node.Graph.PowerSupply==350&&node.Graph.PowerDemand==312,
              "Cable network must supply 350 hp and demand 250 + 12 + 50 = 312 hp; actual "
              +node.Graph.PowerSupply+"/"+node.Graph.PowerDemand);
            if(!_loadObserved)Pass("native cable graph supplies 350 hp against exactly 312 hp demand: mixer 250, six belts 12, pump 50");
            _loadObserved=true;
          }
        }
        if(_frame%600==0)Debug.Log("[DeepFrontier Factory Transport] STATUS phase="+_phase
          +" batches="+_batches+" A="+_mixer.Inventory.AmountInStock("Aggregate")+" C="+_mixer.Inventory.AmountInStock("Cement")
          +" W="+_mixer.Inventory.AmountInStock("Water")+" received="+_stores[2].AmountInStock("Concrete"));
        if(_phase==10&&elapsed>.3f) {
          Require(_belts.All(b=>!b.Running)&&_building.GetComponent<MechanicalNode>().Graph.PowerSupply==0
            &&_pump.GetComponent<MechanicalNode>().Graph.PowerSupply==0,"Isolated power cut left a supply active");
          if(!_powerReload)ConnectPowerLines();
          EnableRemotePower();Phase(11);
        } else if(_phase==11&&elapsed>.3f) {
          Require(_belts.All(b=>b.Running)&&_pump.GetComponent<MechanicalNode>().Powered,"Cable power did not reach transport");
          var remote=_remoteSource.GetComponent<PowerLineComponent>();
          var mixer=_building.GetComponent<PowerLineComponent>();
          _lines.DisconnectConnection(_lines.GetConnections(remote).Single(c=>c.A==mixer||c.B==mixer));
          Phase(12);
        } else if(_phase==12&&elapsed>.3f) {
          Require(_belts.All(b=>!b.Running)&&_building.GetComponent<MechanicalNode>().Graph.PowerSupply==0,
            "Factory remains powered after its only cable is removed");
          Require(!_pump.GetComponent<MechanicalNode>().Powered,"Connected pump remains powered with the cable disconnected");
          Require(_remoteSource.Graph!=_building.GetComponent<MechanicalNode>().Graph,"Disconnected factory graph remained joined");
          _lines.Connect(_remoteSource.GetComponent<PowerLineComponent>(),_building.GetComponent<PowerLineComponent>());
          Pass("disconnecting the only cable splits the remote source from the factory and stops the belts and pump");
          StartProduction();
        } else if(_phase==1&&Full()&&_stores[2].AmountInStock("Concrete")==12) {
          CheckConservation();Pass("real conveyors filled both ingredient buffers and collected all twelve Concrete; pipe filled eight Water");
          foreach(var generator in _supplies.Keys)generator.SetOutputMultiplier(0);Phase(2);
        } else if(_phase==2&&elapsed>.3f) {
          Require(_belts.All(b=>!b.Running),"Unpowered factory belts kept running");
          _mixer.Inventory.TakeExisting(new GoodAmount("Aggregate",6));_baseline["Aggregate"]-=6;
          _mixer.Inventory.TakeExisting(new GoodAmount("Cement",2));_baseline["Cement"]-=2;
          Phase(3);
        } else if(_phase==3&&elapsed>.6f) {
          Require(_mixer.Inventory.AmountInStock("Aggregate")==6&&_mixer.Inventory.AmountInStock("Cement")==2,
            "Ingredient delivery continued without power");
          CheckConservation();foreach(var supply in _supplies)supply.Key.SetOutputMultiplier(supply.Value);
          Pass("power loss stopped both ingredient lanes without losing stock");Phase(4);
        } else if(_phase==4&&Full()) {
          _valve.InletEnabled=false;_mixer.Inventory.TakeExisting(new GoodAmount("Water",4));_waterBaseline-=4;Phase(5);
        } else if(_phase==5&&elapsed>.6f) {
          Require(_mixer.Inventory.AmountInStock("Water")==4,"Closed valve still delivers water");
          CheckConservation();_valve.InletEnabled=true;Pass("closed valve stops water while powered solid delivery remains available");
          StartProduction();
        } else if(_phase==6&&_batches==2) {
          Require(_consumed["Aggregate"]>0&&_consumed["Cement"]>0&&_consumed["Water"]>0,"No new pipe/belt-fed recipe consumption");
          _building.GetComponent<PausableBuilding>().Pause();_outputPaused=true;Phase(7);
        } else if(_phase==7&&Full()&&_mixer.Inventory.AmountInStock("Concrete")==0
          &&_belts.Skip(4).All(b=>b.Sim.Items.Count==0)) {
          Require(_outputPaused&&_stores[2].AmountInStock("Concrete")==_baseline["Concrete"]+4*_batches,
            "Produced concrete did not reach its real warehouse");
          Pass("native workers consumed conveyor ingredients and piped water; all new Concrete reached the output warehouse");
          Finish();
        }
        Require(elapsed<36,"Factory transport exceeded its per-phase time limit");
      } catch(Exception error) {
        _finished=true;_speed.ChangeSpeed(0);
        foreach(var supply in _supplies)supply.Key.SetOutputMultiplier(supply.Value);
        foreach(var inventory in _disabled)inventory.Enable();_disabled.Clear();
        Debug.LogError("[DeepFrontier Factory Transport] FAILED: "+error);
      }
    }
  }
}
#endif
