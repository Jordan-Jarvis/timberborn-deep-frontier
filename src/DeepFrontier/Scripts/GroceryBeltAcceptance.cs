#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using ConveyorBelt.Components;
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
using Timberborn.SingletonSystem;
using Timberborn.Stockpiles;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class GroceryBeltAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierGroceryBelts")
        ||Environment.GetCommandLineArgs().Contains("-deepFrontierGroceryBeltsReload"))
        Bind<GroceryBeltAcceptance>().AsSingleton();
    }
  }
  [Serializable] internal sealed class GroceryBeltRecord {
    public string EntityId;
    public string[] Items;
  }
  [Serializable] internal sealed class GroceryBeltStockRecord {
    public string EntityId;
    public GroceryStockRecord[] Stocks;
  }
  [Serializable] internal sealed class GroceryBeltReloadRecord {
    public GroceryBeltStockRecord Shop,Donor,Receiver;
    public string GeneratorId;
    public GroceryBeltRecord[] Incoming,Outgoing;
    public int CornTotal;
  }
  internal sealed class GroceryBeltAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private readonly EntityRegistry _entities; private readonly BlockObjectFactory _factory;
    private readonly TemplateService _templates; private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _objects; private readonly SpeedManager _speed;
    private readonly CameraService _camera; private readonly GameSaver _saver;
    private readonly GameLoader _loader; private readonly IDayNightCycle _clock;
    private readonly List<ControllableCharacter> _observers=new();
    private readonly List<BeltCarrier> _incoming=new(),_outgoing=new();
    private readonly Dictionary<MechanicalNode,float> _supplies=new();
    private GroceryStore _shop; private Inventory _donor,_receiver; private MechanicalNode _generator;
    private readonly bool _reload=Environment.GetCommandLineArgs().Contains("-deepFrontierGroceryBeltsReload");
    private int _reloadTotal,_eatenCorn,_reloadSupply,_deliveredCorn;
    private int _frame,_phase; private float _start,_phaseTime; private bool _finished;
    public GroceryBeltAcceptance(EntityRegistry entities,BlockObjectFactory factory,TemplateService templates,
      BlockValidator validator,BlockObjectValidationService objects,SpeedManager speed,CameraService camera,
      GameSaver saver,GameLoader loader,IDayNightCycle clock) {
      _entities=entities;_factory=factory;_templates=templates;_validator=validator;_objects=objects;
      _speed=speed;_camera=camera;_saver=saver;_loader=loader;_clock=clock;
    }
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private static void Pass(string message) {Debug.Log("[DeepFrontier Grocery Belts] PASS "+message);}
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"),
        "Belt acceptance requires the marked disposable settlement");
      _speed.ChangeSpeed(0);
    }
    private BlockObject Create(string id,int x,int y,int z,Orientation orientation=Orientation.Cw0) {
      var template=_templates.GetAll<TemplateSpec>().Single(s=>s.TemplateName==id);
      var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
      var placement=new Placement(new Vector3Int(x,y,z),orientation,FlipMode.Unflipped);
      Require(_validator.BlocksValid(spec,placement),"Native placement rejected "+id+" "+placement.Coordinates);
      var block=_factory.CreateFinished(new EntitySetup.Builder(template.Blueprint).AddInitComponent(new FinishedConstructionSiteInit()),placement);
      Require(_objects.IsValid(block),"Native building requirements rejected "+id);
      Debug.Log("[DeepFrontier Grocery Belts] PLACED "+id+" "+placement.Coordinates);return block;
    }
    private void Setup() {
      _shop=_entities.Entities.Single(e=>e.HasComponent<GroceryStore>()).GetComponent<GroceryStore>();
      Require(_shop.GetComponent<BlockObject>().Coordinates==new Vector3Int(159,160,3),"Wrong grocery fixture position");
      Require(_shop.GetComponent<GroceryBeltIntake>()!=null,"Missing explicit grocery belt intake");
      // 9x6 Grocery Market (2026-10-22): its rear wall is local y 5, world y 165; the lanes
      // end on the wall cells (5,5,0) and (6,5,0), world (164,165,3) and (165,165,3), on the
      // ground the former rear row y 6 freed.
      GroceryAcceptance.RequireMarketBlueprint(_templates);
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>()))
        e.GetComponent<PausableBuilding>().Pause();
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<ControllableCharacter>())) {
        var character=e.GetComponent<ControllableCharacter>();
        var idle=e.GetComponent<TemplateSpec>().TemplateName+"_idle";
        Require(character.GetAnimationNames().Contains(idle),"Missing authored idle animation "+idle);
        character.ChangeAnimation(idle);
        character.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(character.Transform.position));
        _observers.Add(character);
      }
      if(_reload) {
        LoadSavedLane();
        _camera.MoveTargetTo(new Vector3(164,5,166));_camera.SetZoomLevel(21,0);
        _camera.HorizontalAngle=205;_camera.VerticalAngle=35;
        _speed.ChangeSpeed(1);return;
      }
      for(int y=166;y<=167;y++) {
        _incoming.Add(Create("ConveyorBeltSp1.IronTeeth",164,y,3).GetComponent<BeltCarrier>());
        _outgoing.Add(Create("ConveyorBeltSp1.IronTeeth",165,y,3,Orientation.Cw180).GetComponent<BeltCarrier>());
      }
      _generator=Create("DevPowerGenerator",163,166,3).GetComponent<MechanicalNode>();
      var source=Create("SmallWarehouse.IronTeeth",164,168,3);
      source.GetComponent<SingleGoodAllower>().Allow("CornRation");_donor=source.GetComponent<Stockpile>().Inventory;
      var sink=Create("SmallWarehouse.IronTeeth",165,168,3);
      sink.GetComponent<SingleGoodAllower>().Allow("CornRation");_receiver=sink.GetComponent<Stockpile>().Inventory;
      _camera.MoveTargetTo(new Vector3(164,5,166));_camera.SetZoomLevel(21,0);_camera.HorizontalAngle=205;_camera.VerticalAngle=35;
      _speed.ChangeSpeed(1);
    }
    private static void CheckStocks(Inventory inventory,GroceryBeltStockRecord record) {
      Require(record.Stocks!=null,"Missing saved inventory stock list");
      Require(inventory.TotalAmountInStock==record.Stocks.Sum(g=>g.Amount),"Saved total stock differs for "+record.EntityId);
      foreach(var g in record.Stocks)Require(inventory.AmountInStock(g.Name)==g.Amount,"Saved stock differs: "+g.Name);
    }
    private void LoadSavedLane() {
      var saved=JsonConvert.DeserializeObject<GroceryBeltReloadRecord>(File.ReadAllText(
        "C:/Users/Jordan/Documents/TimberbornModding/outputs/grocery-belt-reload-expectations.json"));
      Require(saved!=null&&saved.Shop!=null&&saved.Donor!=null&&saved.Receiver!=null
        &&saved.Incoming!=null&&saved.Outgoing!=null,"Missing exact native belt reload expectations");
      Require(_shop.GetComponent<EntityComponent>().EntityId.ToString()==saved.Shop.EntityId,"Saved grocery identity differs");
      CheckStocks(_shop.Inventory,saved.Shop);
      _donor=_entities.Entities.Single(e=>e.EntityId.ToString()==saved.Donor.EntityId).GetComponent<Stockpile>().Inventory;
      _receiver=_entities.Entities.Single(e=>e.EntityId.ToString()==saved.Receiver.EntityId).GetComponent<Stockpile>().Inventory;
      CheckStocks(_donor,saved.Donor);CheckStocks(_receiver,saved.Receiver);
      _generator=_entities.Entities.Single(e=>e.EntityId.ToString()==saved.GeneratorId).GetComponent<MechanicalNode>();
      Require(saved.Incoming.Length==2&&saved.Outgoing.Length==2,"Saved fixture must contain both two-belt lanes");
      LoadBelts(saved.Incoming,_incoming);LoadBelts(saved.Outgoing,_outgoing);
      Require(saved.Incoming.Sum(b=>b.Items.Length)>0,"Save must contain real goods on incoming belts");
      Require(_shop.Inventory.AmountInStock("CornRation")==100,"Expected saved full corn shelf");
      CheckConservation(saved.CornTotal);_reloadTotal=saved.CornTotal;
      _reloadSupply=_donor.AmountInStock("CornRation")+_incoming.Sum(b=>b.Sim.Items.Count);
      Require(_reloadSupply>0&&_reloadSupply<30,"Reload fixture requires less than thirty queued/donor units");
      _shop.Inventory.InventoryStockChanged+=OnReloadStockChanged;
      Pass("fresh process restored exact native inventory stock and every queued belt good and position");
    }
    private void OnReloadStockChanged(object sender,InventoryStockChangedEventArgs args) {
      if(args.GoodAmount.GoodId!="CornRation")return;
      Debug.Log($"[DeepFrontier Grocery Belts] RELOAD STOCK {args.StockChangeType} corn={args.GoodAmount.Amount}");
      if(args.StockChangeType==StockChangeType.Consumed) {
        Require(args.GoodAmount.Amount<0,"Consumed event must debit grocery stock");
        _eatenCorn-=args.GoodAmount.Amount;
      } else if(args.GoodAmount.Amount>0) {
        _deliveredCorn+=args.GoodAmount.Amount;
      }
    }
    private void LoadBelts(GroceryBeltRecord[] records,List<BeltCarrier> destination) {
      foreach(var record in records) {
        var belt=_entities.Entities.Single(e=>e.EntityId.ToString()==record.EntityId).GetComponent<BeltCarrier>();
        Require(record.Items!=null&&belt.Sim.Items.Select(item=>item.Serialize()).SequenceEqual(record.Items),
          "Saved belt contents or positions differ for "+record.EntityId);
        destination.Add(belt);
      }
    }
    private void Start() {
      Require(_incoming[0].OutPort.Target==new Vector3Int(164,165,3),"Input belt orientation differs");
      Require(_outgoing[0].InPort.Target==new Vector3Int(165,165,3),"Output belt orientation differs");
      Require(_incoming.Concat(_outgoing).All(b=>b.Running),"Not all belts have native power");
      foreach(var graph in _incoming.Concat(_outgoing).Select(b=>b.GetComponent<MechanicalNode>().Graph).Distinct()) {
        Require(graph.BatteryCapacity==0,"Power-cut fixture must not include stored flywheel energy");
        Debug.Log($"[DeepFrontier Grocery Belts] NETWORK supply={graph.PowerSupply}hp demand={graph.PowerDemand}hp");
        foreach(var generator in graph.Generators) {
          Require(generator.GetComponent<TemplateSpec>().TemplateName=="DevPowerGenerator",
            "Power-cut fixture requires directly controlled native test generators");
          _supplies.Add(generator,generator.OutputMultiplier);
          Debug.Log("[DeepFrontier Grocery Belts] SUPPLY "+generator.GetComponent<BlockObject>().Coordinates
            +" output="+generator.Actuals.PowerOutput+"hp");
        }
      }
      Require(_supplies.Count>0,"Belt network has no native test supply");
      Require(_outgoing[0].Sim.Input==null,"Grocery still exposes an outgoing belt source");
      Require(_incoming[0].Sim.Output!=null&&_incoming[1].Sim.Input!=null,"Incoming belt lane has a disconnected endpoint");
      Require(!_incoming[0].Sim.Output.CanTarget("Log")&&!_incoming[0].Sim.Output.CanTarget("Water"),"Grocery accepts a non-food belt input");
      if(_reload) {
        CheckConservation(_reloadTotal);
        // Explicit fixture withdrawal, distinct from native shopper consumption.
        _shop.Inventory.TakeExisting(new GoodAmount("CornRation",30));_reloadTotal-=30;
        _start=_clock.PartialDayNumber;Phase(5);_speed.ChangeSpeed(3);
        Pass("saved intake reconnects without exposing an outgoing source; thirty shelf spaces reopened for the entire saved supply");return;
      }
      int previous=_shop.Inventory.AmountInStock("CornRation");
      Require(previous==_shop.Inventory.UnreservedAmountInStock("CornRation"),"Fixture has outstanding shopper reservations");
      _shop.Inventory.TakeConsumed(new GoodAmount("CornRation",previous));
      _shop.Inventory.GiveExisting(new GoodAmount("CornRation",97));
      _donor.GiveExisting(new GoodAmount("CornRation",30));
      _start=_clock.PartialDayNumber;Phase(1);_speed.ChangeSpeed(3);
      Pass("real powered belt lanes connect to the saved grocery; outbound lane has no source; wrong goods rejected");
    }
    private void Phase(int phase) {_phase=phase;_phaseTime=_clock.PartialDayNumber;}
    private void CheckConservation(int expected) {
      Require(_incoming.All(b=>b.Sim.Items.All(g=>g.Id=="CornRation")),"Unexpected incoming belt good");
      Require(_outgoing.All(b=>b.Sim.Items.Count==0)&&_receiver.IsEmpty,"Outgoing belt drained shopper stock");
      int actual=_shop.Inventory.AmountInStock("CornRation")+_donor.AmountInStock("CornRation")+_incoming.Sum(b=>b.Sim.Items.Count);
      Require(actual+_eatenCorn==expected,"Belt transfer lost or duplicated corn: stored/in-transit="+actual
        +" native-consumed="+_eatenCorn+" expected="+expected+" shop="+_shop.Inventory.AmountInStock("CornRation")
        +" donor="+_donor.AmountInStock("CornRation")+" queued="+_incoming.Sum(b=>b.Sim.Items.Count));
      Require(_shop.Inventory.AmountInStock("CornRation")<=100,"Belt exceeded the grocery's per-food limit");
    }
    private void Finish(string saveName,string message,string screenshotName) {
      foreach(var observer in _observers)observer.ReleaseControl();
      _speed.ChangeSpeed(0);_finished=true;
      string directory=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
        "TimberbornModding","docs","art","reviews","2026-10-20-grocery-runtime");
      ScreenCapture.CaptureScreenshot(Path.Combine(directory,screenshotName));
      _saver.QueueSave(new SaveReference(saveName,_loader.LoadedSave.SettlementReference),
        ()=>Debug.Log("[DeepFrontier Grocery Belts] "+message));
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60)Setup();if(_frame==240)Start();if(_frame<=240)return;
        float elapsed=(_clock.PartialDayNumber-_phaseTime)*24;
        if(_frame%600==0)Debug.Log($"[DeepFrontier Grocery Belts] STATUS phase={_phase}, store={_shop.Inventory.AmountInStock("CornRation")}, donor={_donor.AmountInStock("CornRation")}, inTransit={_incoming.Sum(b=>b.Sim.Items.Count)}");
        if(_phase==1&&_shop.Inventory.AmountInStock("CornRation")==100&&elapsed>=1) {
          CheckConservation(127);
          Pass("native belt delivery filled exactly to 100 with conserved stock and no outgoing withdrawal");
          foreach(var generator in _supplies.Keys)generator.SetOutputMultiplier(0);
          Phase(2);
        } else if(_phase==2&&elapsed>=.25f) {
          Require(_incoming.Concat(_outgoing).All(b=>!b.Running),"Belts did not stop at zero power");
          _shop.Inventory.TakeConsumed(new GoodAmount("CornRation",10));Phase(3);
        } else if(_phase==3&&elapsed>=.6f) {
          Require(_shop.Inventory.AmountInStock("CornRation")==90,"Unpowered belt delivered food");
          CheckConservation(117);Pass("power interruption stops actual delivery without losing queued food");
          foreach(var supply in _supplies)supply.Key.SetOutputMultiplier(supply.Value);
          Phase(4);
        } else if(_phase==4&&_shop.Inventory.AmountInStock("CornRation")==100) {
          CheckConservation(117);Pass("restored power resumes real deliveries; full shelves block further intake");
          Require(_incoming.Sum(b=>b.Sim.Items.Count)>0,"Reload fixture must retain actual goods on the belts");
          Finish("Grocery belts - verified","ALL DELIVERY, CAPACITY, POWER AND STOCK CUSTODY CHECKS PASSED AND SAVED",
            "grocery-belt-delivery.png");
        } else if(_phase==5&&_donor.IsEmpty&&_incoming.All(b=>b.Sim.Items.Count==0)&&elapsed>=.5f) {
          CheckConservation(_reloadTotal);
          Require(_deliveredCorn==_reloadSupply,"Saved donor/queue supply did not all arrive at the grocery");
          Pass("saved queued goods resumed delivery; exact conservation includes "+_eatenCorn
            +" native shopper consumption event(s); no outgoing belt withdrawal");
          Finish("Grocery belt continuity - verified","ALL RELOAD, QUEUE AND RESUMED DELIVERY CHECKS PASSED AND SAVED",
            "grocery-belt-reload.png");
        }
        Require(_clock.PartialDayNumber-_start<2,"Grocery belt test exceeded two simulation days");
      } catch(Exception error) {_finished=true;_speed.ChangeSpeed(0);Debug.LogError("[DeepFrontier Grocery Belts] FAILED: "+error);}
    }
  }
}
#endif
