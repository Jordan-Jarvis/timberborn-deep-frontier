using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.Common;
using Timberborn.CameraSystem;
using Timberborn.Carrying;
using Timberborn.CharacterControlSystem;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.Effects;
using Timberborn.EnterableSystem;
using Timberborn.BehaviorSystem;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.MechanicalSystem;
using Timberborn.Navigation;
using Timberborn.PathSystem;
using Timberborn.NeedSystem;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using Timberborn.WorkSystem;
using Timberborn.Workshops;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class RestaurantAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierRestaurantAcceptance") || Environment.GetCommandLineArgs().Contains("-deepFrontierRestaurantReload"))
        Bind<RestaurantAcceptance>().AsSingleton();
    }
  }
  // This fixture can only mutate the explicitly marked, disposable settlement.
  // Placement, inventory, employment, guest choice and saving use native APIs.
  internal sealed class RestaurantAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private readonly EntityRegistry _registry;
    private readonly BlockObjectFactory _factory;
    private readonly TemplateService _templates;
    private readonly BlockValidator _blocks;
    private readonly BlockObjectValidationService _objects;
    private readonly IBlockService _blockService;
    private readonly SpeedManager _speed;
    private readonly CameraService _camera;
    private readonly GameSaver _saver;
    private readonly GameLoader _loader;
    private readonly IDayNightCycle _clock;
    private readonly WorkingHoursManager _workingHours;
    private readonly INavMeshService _nav;
    private readonly INavigationService _navigation;
    private readonly EntityService _entityService;
    private readonly List<MechanicalNode> _powerProbes=new();
    private BlockObject _railTestPath;
    private BlockObject _rightRailTestPath;
    // A free stretch north of the fixture map's road row; everything around the restaurant is
    // derived from its installed blueprint in Setup.
    private static readonly Vector3Int Origin=new(160,161,3);
    private string _leftSeam,_rightSeam,_shutSeam;
    private Vector3Int _leftSeamCell,_rightSeamCell;
    private List<Vector3Int> _stairCells;
    private readonly List<Vector3Int> _deckWalk=new();
    private bool _deckChecksPassed;
    private ControllableCharacter _walker;
    private readonly Queue<Vector3> _walkTargets=new();
    private Vector3 _walkTarget;
    private int _walks;
    private float _walkStarted;
    private Restaurant _restaurant;
    private BlockObject _building;
    private int _frame;
    private bool _failed,_reload,_saved;
    private int _lastMeals;
    private readonly Dictionary<string,int> _consumed=new();
    private readonly Dictionary<string,int> _served=new();
    private readonly Dictionary<string,int> _ingredients=new();
    private Manufactory _kitchen;
    private bool _cycleStarted;
    private int _cakesProduced;
    // Automatic kitchen: finished batches in order; the test never sets a recipe.
    private readonly List<string> _batches=new();
    private bool _kitchenAlternated,_kitchenKeptCooking;
    private bool _mealWithoutCoffee;
    private RestaurantDiner _waterTestDiner;
    private int _waterCases;
    private float _waterBeforeService;
    private readonly HashSet<RestaurantDiner> _alreadyServed=new();
    private readonly HashSet<RestaurantDiner> _resumingService=new();
    private enum Phase { Reload, Paused, Resumed, Unpowered, Repowered, OffDuty, OnDuty, Complete }
    private Phase _phase;
    private float _phaseTime;
    private int _phaseMeals;
    private MechanicalNode _generator;
    private float _normalWorkingHours;
    // Table service: every meal's lead dish is collected at the kitchen pass in
    // native GoodCarrier hands and either served at that diner's table or
    // returned. The ledger proves no dish is duplicated or lost across reloads.
    private string _dish;
    private RestaurantTableService _table;
    private readonly Dictionary<RestaurantWaiter,RestaurantDiner> _pickups=new();
    private readonly HashSet<RestaurantWaiter> _resumedCarriers=new();
    private readonly HashSet<RestaurantDiner> _tableSeen=new();
    private readonly Dictionary<string,int> _tableMismatchSince=new();
    private int _dishesPickedUp,_dishesServed,_dishesReturned,_dishesAtLoad,_tableDishesShown,_deliveryCaptureFrame=-1;
    private string _deliveryFailure;
    private int _staffSeatedSince=-1;
    private bool _staffExclusionLogged;
    public RestaurantAcceptance(EntityRegistry registry,BlockObjectFactory factory,TemplateService templates,BlockValidator blocks,BlockObjectValidationService objects,IBlockService blockService,SpeedManager speed,CameraService camera,GameSaver saver,GameLoader loader,IDayNightCycle clock,WorkingHoursManager workingHours,INavMeshService nav,EntityService entityService,INavigationService navigation) {
      _registry=registry;_factory=factory;_templates=templates;_blocks=blocks;_objects=objects;_blockService=blockService;_speed=speed;_camera=camera;_saver=saver;_loader=loader;
      _clock=clock;_workingHours=workingHours;
      _nav=nav;_entityService=entityService;_navigation=navigation;
    }
    public void PostLoad() {
      if(!_registry.Entities.Any(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"))throw new InvalidOperationException("Restaurant test requires marked disposable fixture");
      _reload=Environment.GetCommandLineArgs().Contains("-deepFrontierRestaurantReload");
    }
    public void UpdateSingleton() {
      if(_failed)return;
      try {
        ++_frame;
        if(_frame==60)Setup();
        if(_frame==240) {
          var power=_restaurant.GetComponent<MechanicalNode>();
          if(power.PowerEfficiency!=1 || power.Graph.PowerSupply<=0)throw new InvalidOperationException("Restaurant must have native shaft power");
          Debug.Log("[DeepFrontier Restaurant] PASS power efficiency=1, supply="+power.Graph.PowerSupply+" hp");
          _phaseTime=_clock.PartialDayNumber;
          _speed.ChangeSpeed(3);
        }
        if(!_reload)CheckPlatformDeck();
        if(_walker) {
          if(Vector3.Distance(_walker.Transform.position,_walkTarget)<.18f) {
            ++_walks;Debug.Log("[DeepFrontier Restaurant] PASS actual beaver reached "+_walkTarget);NextWalk();
          } else if((_clock.PartialDayNumber-_walkStarted)*24>24)throw new InvalidOperationException("Beaver failed to reach deck target "+_walkTarget);
        }
        if(_frame>240 && _frame%300==0)Report();
        if(!_reload && _frame>240 && _waterCases<2)PrepareWaterCase();
        if(_frame==270)Capture("restaurant-in-game");
        if(_frame>240 && _restaurant.MealsServedThisSession>_lastMeals) {
          _lastMeals=_restaurant.MealsServedThisSession;
          Debug.Log("[DeepFrontier Restaurant] ACTUAL MEAL COMMITTED "+_lastMeals);
          Capture("restaurant-serving");
          foreach(var id in _restaurant.Spec.Foods)if(_served[id]!=_lastMeals)throw new InvalidOperationException("Menu receipts differ from committed meals for "+id);
          Debug.Log("[DeepFrontier Restaurant] PASS one actual menu serving per served meal");
        }
        if(_deliveryFailure!=null)throw new InvalidOperationException(_deliveryFailure);
        // Every served good, including the carried lead dish, must emit a native
        // Consumed stock change from the restaurant inventory (the district goods
        // balance records only those).
        if(_frame>240)foreach(var id in _consumed.Keys)
          if(_consumed[id]!=_served[id]+_ingredients[id])throw new InvalidOperationException("Consumption differs from actual meals and native cooking for "+id);
        if(_frame>240 && !_saved && _frame%30==0) {CheckDeliveryLedger();AssertOrderReservations();AssertSingleInventoryRegistration();CheckStaffNotDining();}
        // Served diners stay only EatingHours; sample the table display often.
        if(_frame>240 && !_saved && _frame%5==0)CheckTableDishes();
        if(_frame==_deliveryCaptureFrame)Capture("restaurant-dish-carried");
        if(!_reload && !_saved && _deckChecksPassed && _walks==5 && _waterCases==2 && _cakesProduced==4 && _kitchenAlternated && _kitchenKeptCooking && _served["SweetBerryCake"]>0 && _served["Coffee"]==2 && _mealWithoutCoffee && HasActiveService() && _restaurant.GetComponent<RestaurantSeats>().SeatedDiners.Any(d=>d.Served)
          && _dishesPickedUp>0 && _dishesServed>0 && _tableDishesShown>0 && _restaurant.OpenOrders.Any(o=>o.Stage==RestaurantOrderStage.Carrying&&o.CarriesDish)) {
          Debug.Log("[DeepFrontier Restaurant] PASS table service: "+_dishesPickedUp+" dishes collected at the kitchen pass in native hands, "+_dishesServed+" served at diners' tables, "+_dishesReturned+" returned, "+_tableDishesShown+" table dishes shown; saving with a dish in a waiter's hands");
          Debug.Log("[DeepFrontier Restaurant] PASS native kitchen baked four cakes; cake and coffee effects served at tables; service continued without coffee; thirsty and hydrated water cases passed");
          _saved=true;_speed.ChangeSpeed(0);
          _saver.QueueSave(new SaveReference("Restaurant acceptance - verified",_loader.LoadedSave.SettlementReference),()=>Debug.Log("[DeepFrontier Restaurant] SAVED dining fixture"));
        }
        if(_reload && _frame>240 && !_saved)CheckReloadAndInterruptions();
      } catch(Exception e) {_failed=true;_speed.ChangeSpeed(0);Debug.LogError("[DeepFrontier Restaurant] FAILED frame="+_frame+": "+e);}
    }
    private BlockObject Create(string name,int x,int y,int z,Orientation orientation=Orientation.Cw0) {
      var t=_templates.GetAll<TemplateSpec>().Single(s=>s.TemplateName==name);
      var setup=new EntitySetup.Builder(t.Blueprint).AddInitComponent(new FinishedConstructionSiteInit());
      var placement=new Placement(new Vector3Int(x,y,z),orientation,FlipMode.Unflipped);
      var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==t.Blueprint);
      if(!_blocks.BlocksValid(spec,placement))throw new InvalidOperationException("Native placement rejected "+name+" at "+placement.Coordinates);
      var b=_factory.CreateFinished(setup,placement);
      if(!_objects.IsValid(b))throw new InvalidOperationException("Native object requirements rejected "+name);
      Debug.Log("[DeepFrontier Restaurant] PLACED "+name+" "+placement.Coordinates);return b;
    }
    private BlockObject Local(string name,Vector3Int local,Orientation orientation=Orientation.Cw0) {
      var c=_building.TransformCoordinates(local);return Create(name,c.x,c.y,c.z,orientation);
    }
    private void Setup() {
      _speed.ChangeSpeed(1);
      if(_reload) {
        _restaurant=_registry.Entities.Where(e=>e.HasComponent<Restaurant>()).Single().GetComponent<Restaurant>();
        _building=_restaurant.GetComponent<BlockObject>();
        foreach(var d in _restaurant.GetComponent<RestaurantSeats>().SeatedDiners) {
          Debug.Log("[DeepFrontier Restaurant] RELOADED seated diner: served="+d.Served+", timestamp="+d.ServedAt);
          if(d.Served) {
            _alreadyServed.Add(d);
            d.GetComponent<Enterer>().ExitedEnterable+=(sender,args)=>_alreadyServed.Remove(d);
          }
        }
        foreach(var w in _restaurant.Workplace.AssignedWorkers.Where(w=>w.GetComponent<BehaviorManager>().IsRunningExecutor<RestaurantServeExecutor>()))
          _resumingService.Add(w.GetComponent<RestaurantServeExecutor>().Diner);
        if(_alreadyServed.Count==0 || _resumingService.Count==0)throw new InvalidOperationException("Reload fixture must contain served diners and an active service executor");
        foreach(var w in _restaurant.OpenOrders.Where(o=>o.Stage==RestaurantOrderStage.Carrying)) {
          if(!w.CarriesDish || w.GetComponent<GoodCarrier>().CarriedGood.Type!=CarriedGoodType.Unavailable)throw new InvalidOperationException("Reload lost the dish from a carrying waiter's native hands");
          if(w.GetComponent<GoodReserver>().CapacityReservation.Inventory!=_restaurant.Inventory)throw new InvalidOperationException("Reload lost the carried dish's native return reservation");
          _resumedCarriers.Add(w);
        }
        if(_restaurant.Workplace.AssignedWorkers.Any(w=>w.GetComponent<BehaviorManager>().IsRunningExecutor<RestaurantServeExecutor>()&&!_resumedCarriers.Contains(w.GetComponent<RestaurantWaiter>())))
          throw new InvalidOperationException("Reloaded table service is not holding its carried dish");
        if(_resumedCarriers.Count==0)throw new InvalidOperationException("Reload fixture must contain a dish carried in a waiter's hands");
        AssertOrderReservations();
        Debug.Log("[DeepFrontier Restaurant] PASS reload restored "+_resumedCarriers.Count+" dish(es) in native waiter hands with return reservations and every open order's stock reservation");
        // The saved shaft line's generator: the one dev generator on the restaurant's graph.
        _generator=_restaurant.GetComponent<MechanicalNode>().Graph.Generators
          .Single(g=>g.GetComponent<TemplateSpec>().TemplateName=="DevPowerGenerator").GetComponent<MechanicalNode>();
        _normalWorkingHours=_workingHours.WorkedPartOfDay;
      } else {
        if(_registry.Entities.Any(e=>e.HasComponent<Restaurant>()))throw new InvalidOperationException("Initial restaurant fixture must contain no restaurants");
        foreach(var e in _registry.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>()))e.GetComponent<PausableBuilding>().Pause();
        // The restaurant stands at the fixture origin; its road, deck paths, stairs, shaft line and
        // test seams below follow the installed blueprint (CivicFixtureGeometry), not a size literal
        // (9x7x5 since the 2026-10-30 compaction: dining balconies at layers 1 and 2, roof deck at 3).
        _building=Create("Restaurant.IronTeeth",Origin.x,Origin.y,Origin.z);_restaurant=_building.GetComponent<Restaurant>();
        // Freed ground inside the bounds (validate_freed_cells.py): the service-counter row under
        // the dining balcony, checked before the fixture builds on it.
        FreedCellProbe.Require(_templates,_blocks,_building,FreedCellProbe.Rect(1,5,0,0),
          "Restaurant",message=>Debug.Log("[DeepFrontier Restaurant] PASS "+message));
        // Seed this disposable fixture before workers or haulers can reserve its
        // intake. Live service still uses native stock and respects reservations.
        if(_restaurant.HasMeal)throw new InvalidOperationException("Empty restaurant reported a meal");
        foreach(var id in _restaurant.Spec.Foods.Take(3))_restaurant.Inventory.GiveExisting(new GoodAmount(id,32));
        if(!_restaurant.HasMeal||_restaurant.HasFullMeal)throw new InvalidOperationException("Partial menu must report a partial meal, not a full one");
        Debug.Log("[DeepFrontier Restaurant] PASS empty/partial menu prevents service");
        _restaurant.Inventory.GiveExisting(new GoodAmount(_restaurant.Spec.Foods[3],32));
        _kitchen=_restaurant.GetComponent<Manufactory>();
        // Automatic kitchen: no recipe is selected. Two recipes are stocked: two Fermented Cassava
        // batches and one Sweet Berry Cake batch (Corn 2; Berries and Water come with the menu).
        if(!_restaurant.GetComponent<AutomaticRecipeManufactory>()||!_restaurant.GetComponent<RestaurantKitchenChooser>())
          throw new InvalidOperationException("Restaurant must carry native AutomaticRecipeManufactory and the kitchen chooser");
        if(_kitchen.HasCurrentRecipe)throw new InvalidOperationException("A new automatic kitchen must not start with a selected recipe");
        _restaurant.Inventory.GiveExisting(new GoodAmount("Cassava",8));
        _restaurant.Inventory.GiveExisting(new GoodAmount("Corn",2));
        _restaurant.Inventory.GiveExisting(new GoodAmount("Water",16));
        _restaurant.Inventory.GiveExisting(new GoodAmount("Coffee",2));
        var spec=_building.GetComponent<BlockObjectSpec>();var deck=_building.GetComponent<PlatformDeckSpec>();
        var blocks=CivicFixtureGeometry.Blocks(spec);
        var pathSpec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName=="Path").Blueprint);
        bool TakesPath(Vector3Int local)=>_blocks.BlocksValid(pathSpec,new Placement(_building.TransformCoordinates(local),Orientation.Cw0,FlipMode.Unflipped));
        CivicFixtureGeometry.Place place=(id,c,o)=>Create(id,c.x,c.y,c.z,o);
        var levels=deck.Openings.Select(o=>o.Inside.z).Distinct().OrderBy(z=>z).ToArray();
        if(levels.Length<3)throw new InvalidOperationException("Restaurant deck has layers ["+string.Join(",",levels)+"]; this fixture needs a lower and an upper dining balcony and a roof deck");
        // Ordinary player Path entities on every exterior deck: every rail's deck cell and every
        // upper door step, and the cells of their layer that take a Path, except one roof cell
        // that carries a stacked platform tower instead.
        var region=CivicFixtureGeometry.DeckRegion(spec,deck.Openings.Select(o=>o.Inside).Concat(deck.Doors.Select(d=>d.Exterior).Where(c=>c.z>0)),TakesPath,"Restaurant");
        var tower=region.Where(c=>c.z==levels[2]&&deck.Openings.All(o=>o.Inside!=c)&&deck.Doors.All(d=>d.Exterior!=c)).ToArray();
        if(tower.Length==0)throw new InvalidOperationException("Restaurant roof deck has no cell besides rail and door cells for the platform tower");
        CivicFixtureGeometry.Road(place,c=>_blockService.GetPathObjectAt(c),_building.TransformCoordinates(spec.Entrance.Coordinates));
        foreach(var c in region.Where(c=>c!=tower[0]))Local("Path",c);
        Local("DoublePlatform.IronTeeth",tower[0]);Local("Platform.IronTeeth",tower[0]+new Vector3Int(0,0,2));Local("Path",tower[0]+new Vector3Int(0,0,3));
        // Shaft line out of the ground wall face whose outward cell stays free on the most storeys
        // that repeat the face; a probe shaft on a platform beside each upper storey's face.
        var faces=CivicFixtureGeometry.Faces(_building.GetComponent<TransputProviderSpec>());
        int Storeys((Vector3Int Cell,Vector3Int Out) f) {
          int z=0;
          while(faces.Contains((new Vector3Int(f.Cell.x,f.Cell.y,z),f.Out))&&CivicFixtureGeometry.Free(blocks,f.Cell+f.Out+new Vector3Int(0,0,z)))++z;
          return z;
        }
        var ground=faces.Where(f=>f.Cell.z==0&&Enumerable.Range(1,3).All(s=>CivicFixtureGeometry.Free(blocks,f.Cell+f.Out*s))).OrderByDescending(Storeys).ToArray();
        if(ground.Length==0||Storeys(ground[0])<levels.Length)
          throw new InvalidOperationException("Restaurant has no ground shaft face repeated with a free outward cell on its "+levels.Length+" storeys");
        var power=ground[0];
        _generator=CivicFixtureGeometry.ShaftLine(place,_building,power,1)[0];
        var probe=power.Cell+power.Out;
        for(int z=1;z<Storeys(power);z++) {
          Local("Platform.IronTeeth",new Vector3Int(probe.x,probe.y,z-1));
          _powerProbes.Add(Local("PowerShaft.IronTeeth",new Vector3Int(probe.x,probe.y,z)).GetComponent<MechanicalNode>());
        }
        // External vanilla stairs climb to the middle rear rail of the lower dining balcony.
        var rear=deck.Openings.Where(o=>o.Inside.z==levels[0]&&o.Outside-o.Inside==new Vector3Int(0,1,0)
          &&CivicFixtureGeometry.FreeColumn(blocks,o.Outside)).ToArray();
        if(rear.Length==0)throw new InvalidOperationException("Restaurant lower balcony has no rear rail with a free column outside it for the stairs");
        _stairCells=CivicFixtureGeometry.Flight(place,_building.TransformCoordinates(rear[rear.Length/2].Outside),new Vector3Int(0,1,0),Origin.z);
        // Rail seams of the upper balcony: platform stacks outside its first left and first right
        // rails with a free column (the test toggles a Path on each); the next right rail along
        // has no platform outside and must stay closed and unlinked.
        WalkwayOpeningSpec Seam(Vector3Int dir)=>deck.Openings.FirstOrDefault(o=>o.Inside.z==levels[1]&&o.Outside-o.Inside==dir&&CivicFixtureGeometry.FreeColumn(blocks,o.Outside));
        var left=Seam(new Vector3Int(-1,0,0));var right=Seam(new Vector3Int(1,0,0));
        var shut=right==null?null:deck.Openings.FirstOrDefault(o=>o.Inside.z==levels[1]&&o.Outside==right.Outside+new Vector3Int(0,1,0));
        if(left==null||right==null||shut==null)
          throw new InvalidOperationException("Restaurant upper balcony lacks a left rail and a right rail with free columns outside them and a right rail beside the latter");
        _leftSeam=left.Id;_rightSeam=right.Id;_shutSeam=shut.Id;
        _leftSeamCell=_building.TransformCoordinates(left.Outside);_rightSeamCell=_building.TransformCoordinates(right.Outside);
        for(int z=0;z<levels[1];z++) {
          Local("Platform.IronTeeth",new Vector3Int(left.Outside.x,left.Outside.y,z));
          Local("Platform.IronTeeth",new Vector3Int(right.Outside.x,right.Outside.y,z));
        }
        // Walk: stair foot and head, the left seam, a roof door step, the ground Entrance.
        var roofStep=deck.Doors.Select(d=>d.Exterior).Where(c=>c.z==levels[2]).ToArray();
        if(roofStep.Length==0)throw new InvalidOperationException("Restaurant roof deck has no door");
        _deckWalk.AddRange(new[]{_stairCells[0],_stairCells[_stairCells.Count-1],_leftSeamCell,_building.TransformCoordinates(roofStep[0]),
          _building.TransformCoordinates(spec.Entrance.Coordinates)});
        var room=_building.TransformCoordinates(CivicFixtureGeometry.RoomCell(spec,"Restaurant"));
        if(_blocks.BlocksValid(pathSpec,new Placement(room,Orientation.Cw0,FlipMode.Unflipped)))throw new InvalidOperationException("Path can overlap restaurant enclosed room at "+room);
        Debug.Log("[DeepFrontier Restaurant] PASS player deck paths, stacked roof platforms, vanilla stairs, multi-storey shaft line and solid-room rejection through native placement");
        var workers=_registry.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>()).Where(w=>w.WorkerType=="Beaver").ToArray();
        foreach(var w in workers)w.Unemploy();
        foreach(var w in workers.Take(4))w.EmployAt(_restaurant.Workplace);
      }
      _kitchen=_restaurant.GetComponent<Manufactory>();
      _cycleStarted=_kitchen.ProductionProgress>0;
      foreach(var stock in _restaurant.Spec.Stock) {_consumed.Add(stock.GoodId,0);_served.Add(stock.GoodId,0);_ingredients.Add(stock.GoodId,0);}
      _restaurant.MealServed+=OnMealServed;
      _dish=_restaurant.Spec.Foods[0];
      _table=_restaurant.GetComponent<RestaurantTableService>();
      if(!_table)throw new InvalidOperationException("Restaurant blueprint lacks RestaurantTableServiceSpec; table dishes cannot be verified");
      _dishesAtLoad=DishesOut();
      if(!_reload && _dishesAtLoad!=0)throw new InvalidOperationException("A new restaurant cannot start with dishes in hands");
      _restaurant.DeliveryChanged+=OnDelivery;
      _kitchen.ProductionProgressed+=OnProductionProgressed;
      _kitchen.ProductionFinished+=OnBatchFinished;
      _restaurant.Inventory.InventoryStockChanged+=OnStockChanged;
      if(_restaurant.Inventory.PublicOutput || _restaurant.Inventory.IsOutput)throw new InvalidOperationException("Restaurant dishes must not be exportable");
      Debug.Log("[DeepFrontier Restaurant] PASS table-only inventory has no public or worker output");
      AssertSingleInventoryRegistration();
      Debug.Log("[DeepFrontier Restaurant] PASS shared kitchen inventory enabled once (single district registration)");
      var centre=_building.TransformCoordinates(_building.GetComponent<BlockObjectSpec>().Size/2);
      _camera.MoveTargetTo(new Vector3(centre.x,7,centre.y));_camera.SetZoomLevel(25,0);_camera.HorizontalAngle=25;_camera.VerticalAngle=35;
      Report();
    }
    private void AssertRail(string id,bool open,bool floorConnected) {
      var o=_building.GetComponent<PlatformDeckSpec>().Openings.Single(o=>o.Id==id);
      var a=_building.TransformCoordinates(o.Inside);var b=_building.TransformCoordinates(o.Outside);
      bool linked=_nav.AreConnectedInstant(a,b)&&_nav.AreConnectedInstant(b,a);
      var transforms=_building.GameObject.FindChildIfNameNotEmpty(_building.GetComponent<BuildingModelSpec>().FinishedModelName).GetComponentsInChildren<Transform>(true);
      bool hidden=o.HiddenNodes.All(name=>!transforms.Single(t=>t.name==name).gameObject.activeSelf);
      var outsidePath=_blockService.GetPathObjectAt(b);
      bool neighborPath=outsidePath&&outsidePath.IsFinished&&outsidePath.HasComponent<PathSpec>();
      // The two supported test seams retain their floor connections without
      // roads. The next panel has no outside platform and remains disconnected.
      // Decorative rail visibility follows actual player paths independently.
      if(linked!=floorConnected||neighborPath!=open||hidden!=open)throw new InvalidOperationException("Platform rail/path differs: "+id+" floorLinked="+linked+" expectedFloor="+floorConnected+" neighborPath="+neighborPath+" hidden="+hidden+" expectedOpen="+open);
      Debug.Log("[DeepFrontier Restaurant] PASS platform rail "+id+" open="+open);
    }
    private void CheckPlatformDeck() {
      if(_frame==240) {
        foreach(var shaft in _powerProbes)if(shaft.Graph!=_restaurant.GetComponent<MechanicalNode>().Graph)throw new InvalidOperationException("Multi-level shaft is disconnected from restaurant");
        Debug.Log("[DeepFrontier Restaurant] PASS actual shaft graphs connect at ground, middle and upper room faces");
        AssertRail(_leftSeam,false,true);AssertRail(_rightSeam,false,true);
        _railTestPath=Create("Path",_leftSeamCell.x,_leftSeamCell.y,_leftSeamCell.z);
        _rightRailTestPath=Create("Path",_rightSeamCell.x,_rightSeamCell.y,_rightSeamCell.z);
      }
      if(_frame==330) {
        AssertRail(_leftSeam,true,true);AssertRail(_rightSeam,true,true);AssertRail(_shutSeam,false,false);
        _entityService.Delete(_railTestPath.GetComponent<EntityComponent>());
        _entityService.Delete(_rightRailTestPath.GetComponent<EntityComponent>());
      }
      if(_frame==420) {
        AssertRail(_leftSeam,false,true);AssertRail(_rightSeam,false,true);
        _railTestPath=Create("Path",_leftSeamCell.x,_leftSeamCell.y,_leftSeamCell.z);
        _rightRailTestPath=Create("Path",_rightSeamCell.x,_rightSeamCell.y,_rightSeamCell.z);
      }
      if(_frame==510) {
        AssertRail(_leftSeam,true,true);AssertRail(_rightSeam,true,true);AssertRail(_shutSeam,false,false);
        foreach(var door in _building.GetComponent<PlatformDeckSpec>().Doors) {
          var a=_building.TransformCoordinates(door.Interior);var b=_building.TransformCoordinates(door.Exterior);
          if(!_nav.AreConnectedInstant(a,b)||!_nav.AreConnectedInstant(b,a))throw new InvalidOperationException("Enclosed door lacks native deck-path connection: "+door.Interior);
        }
        var stairCells=_stairCells;
        for(int i=1;i<stairCells.Count;i++)if(!_nav.AreConnectedInstant(stairCells[i-1],stairCells[i])||!_nav.AreConnectedInstant(stairCells[i],stairCells[i-1]))throw new InvalidOperationException("Vanilla stair edge disconnected "+stairCells[i-1]+" to "+stairCells[i]);
        Debug.Log("[DeepFrontier Restaurant] PASS both directions across two native stairs to player deck path");
        _deckChecksPassed=true;Debug.Log("[DeepFrontier Restaurant] ALL PLATFORM DECK CHECKS PASSED");
        var worker=_registry.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>()).First(w=>w.WorkerType=="Beaver"&&!_restaurant.Workplace.AssignedWorkers.Contains(w));
        worker.Unemploy();_walker=worker.GetComponent<ControllableCharacter>();_walker.ChangeAnimation("BeaverAdult_idle");
        foreach(var cell in _deckWalk)_walkTargets.Enqueue(NavigationCoordinateSystem.GridToWorld(cell));
        NextWalk();
      }
    }
    private void NextWalk() {
      if(_walkTargets.Count==0){_walker.ReleaseControl();_walker=null;return;}
      _walkTarget=_walkTargets.Dequeue();_walkStarted=_clock.PartialDayNumber;
      if(!_navigation.FindPathUnlimitedRange(_walker.Transform.position,_walkTarget,new List<PathCorner>(),out var distance))throw new InvalidOperationException("No native route to restaurant deck target "+_walkTarget);
      _walker.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(_walkTarget));
    }
    private void OnMealServed(RestaurantDiner diner,IReadOnlyList<string> foods) {
      if(_alreadyServed.Contains(diner))throw new InvalidOperationException("Reload charged a served guest for a second meal before exit");
      _resumingService.Remove(diner);
      foreach(var id in foods)_served[id]++;
      if(!foods.Contains("Coffee"))_mealWithoutCoffee=true;
      if(diner==_waterTestDiner) {
        bool thirsty=_waterCases==0;
        if(foods.Contains("Water")!=thirsty)throw new InvalidOperationException("Conditional water receipt differs from fixture thirst state");
        float gained=diner.GetComponent<NeedManager>().GetNeedPoints("Thirst")-_waterBeforeService;
        if(Math.Abs(gained-(thirsty?.33f:0))>.02f)throw new InvalidOperationException("Native thirst effect did not match water receipt: "+gained);
        Debug.Log("[DeepFrontier Restaurant] PASS "+(thirsty?"thirsty diner received one water and native +0.33 thirst effect":"hydrated diner consumed no water")+", measured change="+gained);
        ++_waterCases;_waterTestDiner=null;
      }
      Debug.Log("[DeepFrontier Restaurant] SERVICE receipt diner="+diner.GetComponent<EntityComponent>().EntityId+", phase="+_phase+", foods="+string.Join(",",foods));
    }
    private void PrepareWaterCase() {
      if(!_waterTestDiner) {
        var staff=_restaurant.Workplace.AssignedWorkers.FirstOrDefault(w=>w.GetComponent<BehaviorManager>().IsRunningExecutor<RestaurantServeExecutor>());
        if(!staff)return;
        _waterTestDiner=staff.GetComponent<RestaurantServeExecutor>().Diner;
        var needs=_waterTestDiner.GetComponent<NeedManager>();
        // Only this marked disposable fixture changes a diner's need to exercise
        // both branches. Actual service still uses the native inventory/effects.
        float target=_waterCases==0?.2f:1f;
        needs.ApplyEffect(new InstantEffect("Thirst",target-needs.GetNeedPoints("Thirst"),1));
        Debug.Log("[DeepFrontier Restaurant] WATER CASE "+(_waterCases==0?"thirsty":"hydrated"));
      }
      _waterBeforeService=_waterTestDiner.GetComponent<NeedManager>().GetNeedPoints("Thirst");
    }
    private void OnProductionProgressed(object sender,ProductionProgressedEventArgs args) {
      if(args.ProductionProgressChange==0) {_cycleStarted=false;return;}
      if(_cycleStarted)return;
      _cycleStarted=true;
      foreach(var ingredient in _kitchen.CurrentRecipe.Ingredients)_ingredients[ingredient.Id]+=ingredient.Amount;
      Debug.Log("[DeepFrontier Restaurant] NATIVE COOKING started "+_kitchen.CurrentRecipe.Id);
    }
    // ProductionFinished fires after the native reset and before the chooser picks the next batch, so
    // CurrentRecipe is the batch that finished.
    private void OnBatchFinished(object sender,EventArgs args) {
      _batches.Add(_kitchen.CurrentRecipe.Id);
      var chooser=_restaurant.GetComponent<RestaurantKitchenChooser>();
      Debug.Log("[DeepFrontier Restaurant] KITCHEN finished "+_kitchen.CurrentRecipe.Id+"; batches ["+string.Join(",",_batches)+"]; reason "+chooser.Reason+"; switches "+chooser.Switches);
      if(_reload)return;
      if(_batches.Count==2) {
        if(_batches[0]==_batches[1]||!_batches.Contains("FermentedCassava")||!_batches.Contains("SweetBerryCake"))
          throw new InvalidOperationException("Automatic kitchen did not alternate between the two stocked recipes by need: "+string.Join(",",_batches));
        _kitchenAlternated=true;
        Debug.Log("[DeepFrontier Restaurant] PASS automatic kitchen cooked Fermented Cassava and Sweet Berry Cake, alternating by need, with no recipe selected");
      } else if(_batches.Count>2&&_kitchenAlternated&&!_kitchenKeptCooking&&_restaurant.Inventory.AmountInStock("Corn")<2) {
        if(_batches[_batches.Count-1]!="FermentedCassava")throw new InvalidOperationException("Without cake ingredients the kitchen must keep cooking Fermented Cassava: "+string.Join(",",_batches));
        _kitchenKeptCooking=true;
        Debug.Log("[DeepFrontier Restaurant] PASS with the cake's Corn used up the kitchen kept cooking Fermented Cassava");
      }
    }
    private void StartPhase(Phase phase) {
      _phase=phase;_phaseTime=_clock.PartialDayNumber;_phaseMeals=_restaurant.MealsServedThisSession;
      Debug.Log("[DeepFrontier Restaurant] TEST PHASE "+phase);
    }
    private bool HasActiveService() => _restaurant.Workplace.AssignedWorkers.Any(w=>w.GetComponent<BehaviorManager>().IsRunningExecutor<RestaurantServeExecutor>());
    private void CheckNoService(string reason) {
      if(_restaurant.MealsServedThisSession!=_phaseMeals || _restaurant.AcceptsGuests)throw new InvalidOperationException("Service continued while "+reason);
      if(_restaurant.GetComponent<RestaurantSeats>().SeatedDiners.Any())throw new InvalidOperationException("Guests remained trapped while "+reason);
      if(_restaurant.OpenOrders.Any())throw new InvalidOperationException("Restaurant orders remained open while "+reason);
      if(DishesOut()!=0)throw new InvalidOperationException("A carried dish was not returned to the kitchen while "+reason);
      AssertOrderReservations();CheckDeliveryLedger();
      Debug.Log("[DeepFrontier Restaurant] PASS "+reason+": zero meal debits and all guests released");
    }
    private void CheckReloadAndInterruptions() {
      var hours=(_clock.PartialDayNumber-_phaseTime)*24;
      // The restored 16-hour schedule can legitimately leave staff off duty
      // until morning; guests also need time to become hungry again.
      if(hours>30)throw new InvalidOperationException("Restaurant regression phase timed out: "+_phase);
      switch(_phase) {
        case Phase.Reload:
          if(_alreadyServed.Count!=0 || _resumingService.Count!=0 || _resumedCarriers.Count!=0 || !HasActiveService())return;
          Debug.Log("[DeepFrontier Restaurant] PASS fresh reload: served guests exited without duplicate receipts; saved service finished");
          _restaurant.GetComponent<PausableBuilding>().Pause();StartPhase(Phase.Paused);break;
        case Phase.Paused:
          if(hours<.5f)return;
          CheckNoService("paused");_restaurant.GetComponent<PausableBuilding>().Resume();StartPhase(Phase.Resumed);break;
        case Phase.Resumed:
          if(_restaurant.MealsServedThisSession<=_phaseMeals || !HasActiveService())return;
          _generator.SetOutputMultiplier(0);StartPhase(Phase.Unpowered);break;
        case Phase.Unpowered:
          if(hours<.5f)return;
          CheckNoService("unpowered");_generator.SetOutputMultiplier(.5f);StartPhase(Phase.Repowered);break;
        case Phase.Repowered:
          if(_restaurant.MealsServedThisSession<=_phaseMeals || !HasActiveService())return;
          _workingHours.WorkedPartOfDay=0;StartPhase(Phase.OffDuty);break;
        case Phase.OffDuty:
          if(hours<.5f)return;
          CheckNoService("staff off duty");_workingHours.WorkedPartOfDay=_normalWorkingHours;
          StartPhase(Phase.OnDuty);break;
        case Phase.OnDuty:
          if(_restaurant.MealsServedThisSession<=_phaseMeals)return;
          StartPhase(Phase.Complete);_saved=true;_speed.ChangeSpeed(0);Capture("restaurant-reload-verified");
          _saver.QueueSave(new SaveReference("Restaurant regression - verified",_loader.LoadedSave.SettlementReference),()=>Debug.Log("[DeepFrontier Restaurant] RELOAD AND INTERRUPTION CHECKS COMPLETE; native save written"));break;
        case Phase.Complete:break;
        default:throw new ArgumentOutOfRangeException();
      }
    }
    // Native Inventories lists an inventory once per Enable; two entries mean it
    // was also registered twice with the district (DistrictInventoryAssigner).
    private void AssertSingleInventoryRegistration() {
      var enabled=_restaurant.Inventory.GetComponent<Inventories>().EnabledInventories;
      int count=0;
      for(int i=0;i<enabled.Count;i++)if(enabled[i]==_restaurant.Inventory)++count;
      if(count!=1)throw new InvalidOperationException("Restaurant inventory enabled "+count+" times; district registration and goods statistics would be wrong");
    }
    // Own staff must never take a diner seat: the visit is not offered to them,
    // and a guest who becomes staff while seated leaves within one visit tick.
    private void CheckStaffNotDining() {
      var visit=_restaurant.GetComponent<RestaurantVisitBehavior>();
      foreach(var w in _restaurant.Workplace.AssignedWorkers)
        if(visit.ActionPosition(w.GetComponent<NeedManager>())!=null)throw new InvalidOperationException("Restaurant offered its own diner seat to its staff");
      bool seated=_restaurant.GetComponent<RestaurantSeats>().SeatedDiners.Any(d=>_restaurant.IsOwnStaff(d));
      if(!seated){_staffSeatedSince=-1;if(!_staffExclusionLogged && _restaurant.AcceptsGuests){_staffExclusionLogged=true;Debug.Log("[DeepFrontier Restaurant] PASS own staff are not offered or holding diner seats while the restaurant accepts guests");}return;}
      if(_staffSeatedSince<0)_staffSeatedSince=_frame;
      else if(_frame-_staffSeatedSince>120)throw new InvalidOperationException("Restaurant staff remained seated as diners");
    }
    private int DishesOut() => _registry.Entities.Where(e=>e.HasComponent<RestaurantWaiter>()).Count(e=>{var w=e.GetComponent<RestaurantWaiter>();return w.Restaurant==_restaurant&&w.CarriesDish;});
    private void CheckDeliveryLedger() {
      int outNow=DishesOut();
      if(_dishesPickedUp+_dishesAtLoad!=_dishesServed+_dishesReturned+outNow)
        throw new InvalidOperationException($"Carried dish ledger differs: picked={_dishesPickedUp}, atLoad={_dishesAtLoad}, served={_dishesServed}, returned={_dishesReturned}, inHands={outNow}");
    }
    // Native Inventory reservations for menu goods come only from open orders
    // (menu goods are always stocked, so nothing else reserves them here).
    private void AssertOrderReservations() {
      var orders=_restaurant.OpenOrders.ToArray();
      foreach(var id in _restaurant.Spec.Foods.Concat(_restaurant.Spec.OptionalGoods)) {
        int reserved=_restaurant.Inventory.AmountInStock(id)-_restaurant.Inventory.UnreservedAmountInStock(id);
        int expected=orders.Sum(o=>o.ReservedGoods.Count(g=>g==id));
        if(reserved!=expected)throw new InvalidOperationException($"Native stock reservations for {id} ({reserved}) differ from open orders ({expected})");
      }
    }
    private void CheckTableDishes() {
      var seats=_restaurant.GetComponent<RestaurantSeats>();
      foreach(var seat in _restaurant.Spec.Seats) {
        var d=seats.DinerAt(seat.Name);
        bool expected=d && d.Served && d.Restaurant==_restaurant && d.GetComponent<Enterer>().CurrentBuilding==_restaurant.Visitors;
        bool shown=_table.IsDishShown(seat.Name);
        if(expected!=shown) {
          if(!_tableMismatchSince.TryGetValue(seat.Name,out var since))_tableMismatchSince[seat.Name]=_frame;
          else if(_frame-since>120)throw new InvalidOperationException("Table dish display differs from served diner at "+seat.Name+": expected="+expected+", shown="+shown);
          continue;
        }
        _tableMismatchSince.Remove(seat.Name);
        if(shown && _tableSeen.Add(d)) {
          ++_tableDishesShown;
          Debug.Log("[DeepFrontier Restaurant] PASS served dish shown on the table at "+seat.Name);
          if(_tableDishesShown==1)Capture("restaurant-table-dish");
        }
      }
    }
    // Handlers run inside native simulation calls; failures are reported from
    // UpdateSingleton instead of being thrown into the behavior tick.
    private void OnDelivery(RestaurantDeliveryEvent e) {
      if(_deliveryFailure!=null)return;
      var w=e.Waiter;
      switch(e.Kind) {
        case RestaurantDelivery.PickedUp:
          if(e.Dish!=_dish){_deliveryFailure="Waiter collected "+e.Dish+" instead of the lead dish "+_dish;return;}
          if(Vector3.Distance(e.Position,_restaurant.KitchenPassPosition)>.5f){_deliveryFailure="Dish was collected away from the kitchen pass at "+e.Position;return;}
          if(!w.CarriesDish || w.GetComponent<GoodCarrier>().CarriedGood.Type!=CarriedGoodType.Unavailable){_deliveryFailure="Collected dish is not in native GoodCarrier hands";return;}
          if(w.GetComponent<GoodReserver>().CapacityReservation.Inventory!=_restaurant.Inventory){_deliveryFailure="Carried dish lacks its native return reservation";return;}
          _pickups[w]=e.Diner;++_dishesPickedUp;
          Debug.Log("[DeepFrontier Restaurant] DISH collected at kitchen pass by "+w.GetComponent<EntityComponent>().EntityId+" for diner "+e.Diner.GetComponent<EntityComponent>().EntityId);
          if(_deliveryCaptureFrame<0)_deliveryCaptureFrame=_frame+90;
          break;
        case RestaurantDelivery.Served:
          bool resumed=_resumedCarriers.Remove(w);
          if(!resumed && (!_pickups.TryGetValue(w,out var ordered) || ordered!=e.Diner)){_deliveryFailure="Meal served without this waiter carrying that diner's dish from the kitchen pass";return;}
          _pickups.Remove(w);
          if(e.Dish!=_dish || w.GetComponent<GoodCarrier>().IsCarrying){_deliveryFailure="Served meal did not hand over the carried lead dish";return;}
          if(Vector3.Distance(e.Position,_restaurant.GetComponent<RestaurantSeats>().ServicePosition(e.Diner))>.3f){_deliveryFailure="Dish handed over away from the diner's table";return;}
          ++_dishesServed;
          Debug.Log("[DeepFrontier Restaurant] PASS carried dish served at the diner's table"+(resumed?" (delivery resumed from save)":""));
          break;
        case RestaurantDelivery.Returned:
          _pickups.Remove(w);_resumedCarriers.Remove(w);
          if(Vector3.Distance(e.Position,_restaurant.KitchenPassPosition)>.5f || w.GetComponent<GoodCarrier>().IsCarrying){_deliveryFailure="Undelivered dish was not returned at the kitchen pass";return;}
          ++_dishesReturned;
          Debug.Log("[DeepFrontier Restaurant] PASS undelivered dish returned to the kitchen pass, phase="+_phase);
          break;
        case RestaurantDelivery.LeftService:
          _deliveryFailure="A carried dish left restaurant service outside table delivery or kitchen return";break;
        default:_deliveryFailure="Unknown delivery event "+e.Kind;break;
      }
    }
    private void OnStockChanged(object sender,InventoryStockChangedEventArgs args) {
      if(args.StockChangeType==StockChangeType.Consumed)_consumed[args.GoodAmount.GoodId]-=args.GoodAmount.Amount;
      if(args.StockChangeType==StockChangeType.Produced && args.GoodAmount.GoodId=="SweetBerryCake") {
        _cakesProduced+=args.GoodAmount.Amount;
        Debug.Log("[DeepFrontier Restaurant] NATIVE PRODUCED SweetBerryCake "+args.GoodAmount.Amount);
      }
    }
    private void Report() {
      Debug.Log("[DeepFrontier Restaurant] STATUS workers="+_restaurant.Workplace.NumberOfAssignedWorkers+", onDuty="+_restaurant.StaffOnDuty+", operating="+_restaurant.IsOperating+", seated="+_restaurant.GetComponent<RestaurantSeats>().SeatedDiners.Count()+", meals="+_restaurant.MealsServedThisSession+", orders="+_restaurant.OpenOrders.Count()+", dishesOut="+DishesOut()+", pickedUp="+_dishesPickedUp+", servedFromHands="+_dishesServed+", returned="+_dishesReturned+", stock="+string.Join(",",_restaurant.Spec.Foods.Select(id=>id+":"+_restaurant.Inventory.AmountInStock(id))));
      foreach(var w in _restaurant.Workplace.AssignedWorkers) {
        var behavior=w.GetComponent<Timberborn.BehaviorSystem.BehaviorManager>();
        Debug.Log("[DeepFrontier Restaurant] STAFF "+w.Transform.position+" behavior="+behavior.RunningBehavior.Name+" executor="+behavior.RunningExecutor.Name);
      }
    }
    private static void Capture(string name) {
      var folder=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding/docs/art/reviews/2026-10-21-exterior-repair-runtime");
      Directory.CreateDirectory(folder);ScreenCapture.CaptureScreenshot(Path.Combine(folder,name+".png"));
    }
  }
}
