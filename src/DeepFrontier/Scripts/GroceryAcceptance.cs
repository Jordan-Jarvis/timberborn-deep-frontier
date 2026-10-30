using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.CameraSystem;
using Timberborn.CharacterControlSystem;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.Effects;
using Timberborn.EnterableSystem;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.MechanicalSystem;
using Timberborn.Navigation;
using Timberborn.NeedSystem;
using Timberborn.SingletonSystem;
using Timberborn.Stockpiles;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class GroceryAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierGroceryAcceptance"))Bind<GroceryAcceptance>().AsSingleton();
    }
  }
  internal sealed class GroceryAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private readonly EntityRegistry _entities; private readonly BlockObjectFactory _factory;
    private readonly TemplateService _templates; private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _objects; private readonly IBlockService _blocks;
    private readonly SpeedManager _speed; private readonly CameraService _camera;
    private readonly GameSaver _saver; private readonly GameLoader _loader;
    private readonly IDayNightCycle _clock; private readonly WorkingHoursManager _hours;
    private readonly INavMeshService _nav; private readonly INavigationService _navigation; private readonly IGoodService _goods;
    private GroceryStore _shop; private BlockObject _building; private MechanicalNode _generator;
    private Worker[] _staff; private ControllableCharacter _observer; private NeedManager _needs;
    private readonly List<Inventory> _donors=new(); private readonly Queue<Vector3Int> _walkTargets=new();
    private int _frame,_phase,_cornBefore; private float _start,_phaseTime,_normalHours,_baseline,_foodBefore;
    private bool _finished,_entered; private Vector3 _target; private Vector3Int _localTarget;
    public GroceryAcceptance(EntityRegistry entities,BlockObjectFactory factory,TemplateService templates,
      BlockValidator validator,BlockObjectValidationService objects,IBlockService blocks,SpeedManager speed,CameraService camera,
      GameSaver saver,GameLoader loader,IDayNightCycle clock,WorkingHoursManager hours,INavMeshService nav,
      INavigationService navigation,IGoodService goods) {
      _entities=entities;_factory=factory;_templates=templates;_validator=validator;_objects=objects;_blocks=blocks;
      _speed=speed;_camera=camera;_saver=saver;_loader=loader;_clock=clock;_hours=hours;_nav=nav;_navigation=navigation;_goods=goods;
    }
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private static void Pass(string message) {Debug.Log("[DeepFrontier Grocery] PASS "+message);}
    private void Phase(int phase) {_phase=phase;_phaseTime=_clock.PartialDayNumber;}
    private static void SetNeed(NeedManager needs,string id,float points) {
      needs.ApplyEffect(new InstantEffect(id,points-needs.GetNeedPoints(id),1));
    }
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"),
        "Grocery acceptance requires the marked disposable settlement");
    }
    private BlockObject Create(string id,int x,int y,int z,Orientation orientation=Orientation.Cw0) {
      var template=_templates.GetAll<TemplateSpec>().Single(s=>s.TemplateName==id);
      var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
      var placement=new Placement(new Vector3Int(x,y,z),orientation,FlipMode.Unflipped);
      Require(_validator.BlocksValid(spec,placement),"Native placement rejected "+id+" "+placement.Coordinates);
      var b=_factory.CreateFinished(new EntitySetup.Builder(template.Blueprint).AddInitComponent(new FinishedConstructionSiteInit()),placement);
      Require(_objects.IsValid(b),"Native building requirements rejected "+id);
      Debug.Log("[DeepFrontier Grocery] PLACED "+id+" "+placement.Coordinates);return b;
    }
    private void Setup() {
      _speed.ChangeSpeed(0);
      Require(!_entities.Entities.Any(e=>e.HasComponent<GroceryStore>()),"Grocery fixture must start without a shop");
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>()))e.GetComponent<PausableBuilding>().Pause();
      RequireMarketBlueprint(_templates);
      _building=Create("GroceryStore.IronTeeth",159,160,3);_shop=_building.GetComponent<GroceryStore>();
      // Freed ground (2026-10-22): the former rear row y 6 (loading dock, its goods and the
      // water tower) left the 9x6 bounds; nothing inside the bounds was freed.
      var size=_building.GetComponent<BlockObjectSpec>().Size;
      FreedCellProbe.Require(_templates,_validator,_building,FreedCellProbe.Outside(0,8,0,6,size),"GroceryStore",Pass);
      for(int y=157;y<=159;y++)if(!_blocks.GetPathObjectAt(new Vector3Int(173,y,3)))Create("Path",173,y,3);
      for(int x=161;x<173;x++)Create("Path",x,159,3);
      foreach(var c in MarketPaths)Local("Path",c);
      // Shafts meet authored walls only: the rear wall face (0,5,0) Up, world (159,166,3).
      Local("PowerShaft.IronTeeth",new Vector3Int(0,6,0));
      _generator=Local("DevPowerGenerator",new Vector3Int(0,7,0)).GetComponent<MechanicalNode>();
      // Stair bay x 8, y 2..3: two vanilla Cw0 stairs (climbing toward -y) from the ground at
      // y 4 to the balcony deck at layer 2, the first on the ground, the second on a platform.
      Local("Stairs.IronTeeth",new Vector3Int(8,3,0),Orientation.Cw0);
      Local("Platform.IronTeeth",new Vector3Int(8,2,0));
      Local("Stairs.IronTeeth",new Vector3Int(8,2,1),Orientation.Cw0);
      foreach(var c in BalconyPaths)Local("Path",c);
      var foods=_shop.GetComponent<GroceryStoreSpec>().Foods;
      Require(_shop.Inventory.IsEmpty&&_shop.Inventory.Capacity==600,"Grocery must start with an empty native 600-unit inventory");
      Require(_shop.Inventory.PublicInput&&!_shop.Inventory.PublicOutput&&_shop.Inventory.IsOutput,"Shopper takeable stock/public input contract differs");
      for(int i=0;i<foods.Length;i++) {
        var warehouse=Create("SmallWarehouse.IronTeeth",161+i,158,3,Orientation.Cw180);
        warehouse.GetComponent<SingleGoodAllower>().Allow(foods[i]);
        var inventory=warehouse.GetComponent<Stockpile>().Inventory;
        inventory.GiveExisting(new GoodAmount(foods[i],30));_donors.Add(inventory);
      }
      Pass("native placement, door approach, balcony stairs and deck paths, wall-face shaft and six separate food donors");
      // Begin with actual food only in the native donor warehouses. Every unit
      // reaching the empty grocery must be carried through normal hauling.
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<NeedManager>())) {
        var n=e.GetComponent<NeedManager>();
        foreach(var id in new[]{"Hunger","Thirst","Sleep"})SetNeed(n,id,n.GetNeedSpec(id).MaximumValue);
        foreach(var effect in foods.SelectMany(id=>_goods.GetGood(id).ConsumptionEffects))
          SetNeed(n,effect.NeedId,n.GetNeedSpec(effect.NeedId).MaximumValue);
      }
      _normalHours=_hours.WorkedPartOfDay;_hours.WorkedPartOfDay=1;
      _camera.MoveTargetTo(new Vector3(164,7,164));_camera.SetZoomLevel(25,0);_camera.HorizontalAngle=25;_camera.VerticalAngle=35;
      _speed.ChangeSpeed(1);
    }
    private void Start() {
      Require(_building.GetComponent<MechanicalNode>().PowerEfficiency==1,"Grocery lacks its full 3,900 hp");
      RequireMarketAccess(_building,_nav);
      Pass("road, main-door entrance, stair foot and balcony deck paths form one native navigation network");
      var workers=_entities.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>()).Where(w=>w.WorkerType=="Beaver").ToArray();
      Require(workers.Length>=3,"Grocery fixture needs two clerks and a shopper");
      foreach(var worker in workers)worker.Unemploy();
      _staff=workers.Take(2).ToArray();foreach(var worker in _staff)worker.EmployAt(_building.GetComponent<Workplace>());
      _observer=workers[2].GetComponent<ControllableCharacter>();_needs=_observer.GetComponent<NeedManager>();
      Require(_observer.GetAnimationNames().Contains("BeaverAdult_idle"),"Missing native adult idle animation");
      _observer.ChangeAnimation("BeaverAdult_idle");
      MoveTo(new Vector3Int(163,159,3));_start=_clock.PartialDayNumber;Phase(1);_speed.ChangeSpeed(3);
      Capture("grocery-native");
    }
    private void MoveTo(Vector3Int cell) {
      _target=NavigationCoordinateSystem.GridToWorld(cell);
      Require(_navigation.FindPathUnlimitedRange(_observer.Transform.position,_target,new List<PathCorner>(),out var distance),"No native observer path");
      _observer.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(_target));
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60)Setup();if(_frame==240)Start();if(_frame<=240)return;
        float elapsed=(_clock.PartialDayNumber-_phaseTime)*24;
        if(_frame%600==0)Debug.Log($"[DeepFrontier Grocery] STATUS phase={_phase}, staff={_shop.AttendingStaff}, types={_shop.StockedFoodTypes}, stock={_shop.Inventory.TotalAmountInStock}, area={_shop.ProvidesNeighborhoodService}, observer={_observer.Transform.position}, target={_target}");
        if(_phase==1&&_shop.StockedFoodTypes==6&&_shop.AttendingStaff==2&&_shop.ProvidesNeighborhoodService
          &&Vector3.Distance(_observer.Transform.position,_target)<.18f) {
          foreach(var id in _shop.GetComponent<GroceryStoreSpec>().Foods)
            Require(_shop.Inventory.AmountInStock(id)>0,"Missing natively hauled food "+id);
          Pass("two real clerks hauled all six foods from warehouses into the initially empty store");
          // Close only the disposable donors now; ordinary shoppers must use
          // the actual grocery stock for the following consumption check.
          foreach(var donor in _donors)donor.Disable();
          SetNeed(_needs,"NeighborhoodGroceries",0);_baseline=0;Phase(2);
        } else if(_phase==2&&elapsed>=.6f) {
          Require(_needs.GetNeedPoints("NeighborhoodGroceries")>_baseline+.06f,"Nearby shopper receives no actual grocery wellbeing need");
          Pass("stocked, staffed grocery supplies actual neighborhood need points");
          _generator.SetOutputMultiplier(0);Phase(3);
        } else if(_phase==3&&elapsed>=.6f) {
          Require(!_shop.ProvidesNeighborhoodService&&_shop.Inventory.Enabled,"Power loss must stop the area bonus while preserving food access");
          SetNeed(_needs,"Hunger",.3f);SetNeed(_needs,"CornRation",0);
          _foodBefore=_needs.GetNeedPoints("CornRation");_cornBefore=_shop.Inventory.AmountInStock("CornRation");
          _observer.ReleaseControl();Phase(4);
          Pass("power loss disables neighborhood service while native food stock remains available");
        } else if(_phase==4) {
          if(_observer.GetComponent<Enterer>().CurrentBuilding==_building.GetComponent<Enterable>())_entered=true;
          if(_shop.Inventory.AmountInStock("CornRation")<_cornBefore&&_needs.GetNeedPoints("CornRation")>_foodBefore+.1f) {
            Require(_entered,"No actual shopper entry was observed");
            Pass("unpowered shopper entered, consumed native corn rations and gained their real food need");
            _generator.SetOutputMultiplier(1);Phase(5);
          }
        } else if(_phase==5&&_shop.ProvidesNeighborhoodService) {
          Pass("power restoration resumes the stocked neighborhood service");
          _building.GetComponent<PausableBuilding>().Pause();Phase(6);
        } else if(_phase==6&&elapsed>=.6f) {
          Require(!_shop.ProvidesNeighborhoodService&&_shop.Inventory.Enabled,"Paused shop must retain food access but stop neighborhood service");
          Pass("workplace pause stops service without locking stored food");
          _building.GetComponent<PausableBuilding>().Resume();
          foreach(var worker in _staff){worker.Unemploy();worker.EmployAt(_building.GetComponent<Workplace>());}
          foreach(var id in _shop.GetComponent<GroceryStoreSpec>().Foods.Where(id=>id!="CornRation")) {
            int stock=_shop.Inventory.AmountInStock(id);
            Require(stock==_shop.Inventory.UnreservedAmountInStock(id),"Stock shortage fixture encountered a shopper reservation");
            _shop.Inventory.TakeConsumed(new GoodAmount(id,stock));
          }
          Phase(7);
        } else if(_phase==7&&elapsed>=.6f) {
          Require(_shop.StockedFoodTypes<3&&!_shop.ProvidesNeighborhoodService,"Sparse shelves still grant the neighborhood bonus");
          Pass("less than three stocked foods removes the neighborhood effect");
          foreach(var donor in _donors)donor.Enable();
          _donors[0].GiveExisting(new GoodAmount("CannedFish",_donors[0].UnreservedCapacity("CannedFish")));
          _donors[1].GiveExisting(new GoodAmount("PackagedFood",_donors[1].UnreservedCapacity("PackagedFood")));
          Phase(8);
        } else if(_phase==8&&_shop.ProvidesNeighborhoodService) {
          Pass("native restocking restores the neighborhood bonus");
          _building.GetComponent<PausableBuilding>().Pause();
          _observer.GetComponent<Worker>().Unemploy();
          // Market access cells (all player paths): main-door approach and Entrance, the stair
          // foot, the balcony at the stair head and at the balcony door, then the road.
          foreach(var c in new[]{new Vector3Int(4,0,0),new Vector3Int(4,1,0),new Vector3Int(8,4,0),
            new Vector3Int(8,1,2),new Vector3Int(6,1,2),new Vector3Int(7,-1,0)})_walkTargets.Enqueue(c);
          Phase(9);NextWalk();
        } else if(_phase==9&&Vector3.Distance(_observer.Transform.position,_target)<.18f) {
          Pass("actual shopper reached "+_localTarget);
          if(_walkTargets.Count>0)NextWalk();
          else {
            _observer.ReleaseControl();_hours.WorkedPartOfDay=_normalHours;_speed.ChangeSpeed(0);_finished=true;
            Capture("grocery-care-and-access");
            _saver.QueueSave(new SaveReference("Grocery acceptance - verified",_loader.LoadedSave.SettlementReference),
              ()=>Debug.Log("[DeepFrontier Grocery] ALL STOCK, SHOPPING, SERVICE AND ACCESS CHECKS PASSED AND SAVED"));
          }
        }
        Require(_clock.PartialDayNumber-_start<4,"Grocery acceptance exceeded four simulation days");
      } catch(Exception e) {_finished=true;_speed.ChangeSpeed(0);Debug.LogError("[DeepFrontier Grocery] FAILED: "+e);}
    }
    // Grocery Market (outputs/lategame-studies/GroceryMarket-registration.json "access", blueprint
    // regenerated 2026-10-22 at 9x6x8): native Entrance (4,1,0) at the end of the open door
    // walk x 4, y 0..1; balcony deck layer 2, x 6..8, y 1 (player paths on the Stackable
    // layer-1 support, BalconyDoor at (6,1,2)); open stair bay x 8, y 2..3 entered from the
    // ground at y 4..5. No built-in walkway, no deck spec and no stackable roof. Local cells.
    internal static readonly Vector3Int[] MarketPaths={new(4,0,0),new(4,1,0),
      new(9,0,0),new(9,1,0),new(9,2,0),new(9,3,0),new(9,4,0),new(9,5,0),new(8,5,0),new(8,4,0)};
    internal static readonly Vector3Int[] BalconyPaths={new(6,1,2),new(7,1,2),new(8,1,2)};
    internal static void RequireMarketBlueprint(TemplateService templates) {
      var blueprint=templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName=="GroceryStore.IronTeeth").Blueprint;
      var spec=blueprint.GetSpec<BlockObjectSpec>();
      if(spec.Size!=new Vector3Int(9,6,8)||spec.Entrance.Coordinates!=new Vector3Int(4,1,0)
        ||blueprint.HasSpec<BuildingWalkwaySpec>()||blueprint.HasSpec<PlatformDeckSpec>())
        throw new InvalidOperationException("Installed GroceryStore is "+spec.Size+" with entrance "+spec.Entrance.Coordinates+
          (blueprint.HasSpec<BuildingWalkwaySpec>()?" and a built-in walkway":"")+
          "; this fixture encodes the 9x6x8 Grocery Market with its entrance at (4,1,0) and player-path access only");
    }
    // Road, main-door Entrance, stair foot and both balcony ends in one native navigation network.
    internal static void RequireMarketAccess(BlockObject building,INavMeshService nav) {
      var road=building.TransformCoordinates(new Vector3Int(4,-1,0));
      foreach(var local in new[]{new Vector3Int(4,1,0),new Vector3Int(8,4,0),new Vector3Int(8,1,2),new Vector3Int(6,1,2)}) {
        var cell=building.TransformCoordinates(local);
        if(!nav.AreConnectedInstant(road,cell)||!nav.AreConnectedInstant(cell,road))
          throw new InvalidOperationException("Grocery Market access cell "+local+" (world "+cell+") is not connected to the road "+road);
      }
    }
    private BlockObject Local(string id,Vector3Int local,Orientation orientation=Orientation.Cw0) {
      var c=_building.TransformCoordinates(local);return Create(id,c.x,c.y,c.z,orientation);
    }
    private void NextWalk() {
      _localTarget=_walkTargets.Dequeue();
      _target=NavigationCoordinateSystem.GridToWorld(_building.TransformCoordinates(_localTarget));
      Require(_navigation.FindPathUnlimitedRange(_observer.Transform.position,_target,new List<PathCorner>(),out var distance),"No grocery route to "+_localTarget);
      _observer.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(_target));
    }
    private static void Capture(string name) {
      const string folder="C:/Users/Jordan/Documents/TimberbornModding/docs/art/reviews/2026-10-20-grocery-runtime";
      Directory.CreateDirectory(folder);ScreenCapture.CaptureScreenshot(Path.Combine(folder,name+".png"));
    }
  }
}
