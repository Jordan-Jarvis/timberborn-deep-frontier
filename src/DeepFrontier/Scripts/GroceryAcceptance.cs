using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Newtonsoft.Json.Linq;
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
    private MarketLayout _layout;
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
      _layout=RequireMarketLayout(_templates);
      _building=Create("GroceryStore.IronTeeth",Origin.x,Origin.y,Origin.z);_shop=_building.GetComponent<GroceryStore>();
      // Freed ground (2026-10-22): the former rear row y 6 (loading dock, its goods and the
      // water tower) left the 9x6 bounds; nothing inside the bounds was freed.
      var size=_building.GetComponent<BlockObjectSpec>().Size;
      FreedCellProbe.Require(_templates,_validator,_building,FreedCellProbe.Outside(0,8,0,6,size),"GroceryStore",Pass);
      CivicFixtureGeometry.Place place=(id,c,o)=>Create(id,c.x,c.y,c.z,o);
      // The road and the open door walk to the Entrance, the ground walk to the stair approach,
      // one vanilla stair per balcony layer in the stair bay, then paths on the balcony deck.
      CivicFixtureGeometry.Road(place,c=>_blocks.GetPathObjectAt(c),_building.TransformCoordinates(_layout.Entrance));
      foreach(var c in _layout.EastWalk)Local("Path",c);
      CivicFixtureGeometry.Flight(place,_building.TransformCoordinates(_layout.StairHead),-_layout.Climb,Origin.z,pad:false);
      foreach(var c in _layout.Balcony)Local("Path",c);
      // Shafts meet authored walls only: a shaft line out of the lowest wall face clear of the
      // door walk, stair bay, ground walk and balcony.
      var access=new HashSet<Vector2Int>(_layout.DoorWalk.Concat(_layout.EastWalk).Concat(_layout.Bay).Concat(_layout.Balcony)
        .Append(_layout.StairFoot).Select(c=>new Vector2Int(c.x,c.y)));
      var face=CivicFixtureGeometry.ShaftFace(_building.GetComponent<BlockObjectSpec>(),_building.GetComponent<TransputProviderSpec>(),
        c=>access.Contains(new Vector2Int(c.x,c.y)),"GroceryStore");
      _generator=CivicFixtureGeometry.ShaftLine(place,_building,face,1)[0];
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
      var centre=_building.TransformCoordinates(size/2);
      _camera.MoveTargetTo(new Vector3(centre.x,7,centre.y));_camera.SetZoomLevel(25,0);_camera.HorizontalAngle=25;_camera.VerticalAngle=35;
      _speed.ChangeSpeed(1);
    }
    private void Start() {
      Require(_building.GetComponent<MechanicalNode>().PowerEfficiency==1,"Grocery lacks its full 3,900 hp");
      RequireMarketAccess(_building,_nav,_layout);
      Pass("road, main-door entrance, stair foot and balcony deck paths form one native navigation network");
      var workers=_entities.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>()).Where(w=>w.WorkerType=="Beaver").ToArray();
      Require(workers.Length>=3,"Grocery fixture needs two clerks and a shopper");
      foreach(var worker in workers)worker.Unemploy();
      _staff=workers.Take(2).ToArray();foreach(var worker in _staff)worker.EmployAt(_building.GetComponent<Workplace>());
      _observer=workers[2].GetComponent<ControllableCharacter>();_needs=_observer.GetComponent<NeedManager>();
      Require(_observer.GetAnimationNames().Contains("BeaverAdult_idle"),"Missing native adult idle animation");
      _observer.ChangeAnimation("BeaverAdult_idle");
      var door=_building.TransformCoordinates(_layout.Entrance);
      MoveTo(new Vector3Int(door.x,CivicFixtureGeometry.RoadY,door.z));_start=_clock.PartialDayNumber;Phase(1);_speed.ChangeSpeed(3);
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
          // Refill the first two stocked foods' donors (one donor per GroceryStoreSpec food, in order).
          foreach(var (donor,id) in _donors.Zip(_shop.GetComponent<GroceryStoreSpec>().Foods,(d,f)=>(d,f)).Take(2))
            donor.GiveExisting(new GoodAmount(id,donor.UnreservedCapacity(id)));
          Phase(8);
        } else if(_phase==8&&_shop.ProvidesNeighborhoodService) {
          Pass("native restocking restores the neighborhood bonus");
          _building.GetComponent<PausableBuilding>().Pause();
          _observer.GetComponent<Worker>().Unemploy();
          // Market access cells (all player paths): the main-door walk to the Entrance, the stair
          // foot, the balcony at the stair head and at the balcony door, then the road.
          foreach(var c in _layout.DoorWalk.OrderBy(c=>c.y).Concat(new[]{_layout.StairFoot,_layout.StairHead,_layout.BalconyDoor,
            _layout.Entrance+new Vector3Int(0,-_layout.Entrance.y-1,0)}))_walkTargets.Enqueue(c);
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
    // Fixture origin: a free stretch north of the map's road row. GroceryBeltAcceptance and the
    // continuity run load the saved shop here.
    internal static readonly Vector3Int Origin=new(159,160,3);
    // Grocery Market access in local cells, read from its registration (the "doors" and "access"
    // of outputs/lategame-studies/GroceryMarket-registration.json, from which
    // tools/grocery_building_content.mjs generates the blueprint) and checked against the
    // installed blueprint: the open door walk to the native Entrance, the balcony deck (player
    // paths on its Stackable support, BalconyDoor) and the open stair bay entered from the
    // ground. No built-in walkway and no deck spec.
    internal sealed class MarketLayout {
      public Vector3Int Entrance,BalconyDoor,StairHead,StairFoot,Climb;
      public Vector3Int[] DoorWalk,Balcony,Bay,EastWalk;
    }
    private static string RegistrationPath=>Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
      "TimberbornModding","outputs","lategame-studies","GroceryMarket-registration.json");
    internal static MarketLayout RequireMarketLayout(TemplateService templates) {
      var blueprint=templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName=="GroceryStore.IronTeeth").Blueprint;
      var spec=blueprint.GetSpec<BlockObjectSpec>();
      if(blueprint.HasSpec<BuildingWalkwaySpec>()||blueprint.HasSpec<PlatformDeckSpec>())
        throw new InvalidOperationException("Installed GroceryStore has a built-in walkway or deck spec; this fixture tests player-path access only");
      var reg=JObject.Parse(File.ReadAllText(RegistrationPath));
      int Whole(JToken t){float v=t.Value<float>();if(v!=Mathf.Round(v))throw new InvalidOperationException("Grocery registration value "+v+" is not a whole tile");return (int)v;}
      Vector3Int Cell(JToken t)=>new(Whole(t[0]),Whole(t[1]),t.Count()>2?Whole(t[2]):0);
      // Registration bounds are [x0,y0,x1,y1) in whole tiles.
      Vector3Int[] Rect(JToken b,int z) {
        var r=new List<Vector3Int>();
        for(int y=Whole(b[1]);y<Whole(b[3]);y++)for(int x=Whole(b[0]);x<Whole(b[2]);x++)r.Add(new Vector3Int(x,y,z));
        return r.ToArray();
      }
      JToken Door(string id)=>reg["doors"].Single(d=>(string)d["id"]==id);
      var access=reg["access"];
      var layout=new MarketLayout{Entrance=Cell(Door("MainDoor")["entrance"]),BalconyDoor=Cell(Door("BalconyDoor")["entrance"])};
      var footprint=reg["footprint"];
      if(Whole(footprint[0])!=spec.Size.x||Whole(footprint[1])!=spec.Size.y||layout.Entrance!=spec.Entrance.Coordinates)
        throw new InvalidOperationException("Installed GroceryStore is "+spec.Size+" with entrance "+spec.Entrance.Coordinates+
          "; its registration has footprint "+footprint.ToString(Newtonsoft.Json.Formatting.None)+" and MainDoor entrance "+layout.Entrance+". Regenerate the Grocery Store.");
      int layer=Whole(access["balcony"]["layer"]);
      layout.Balcony=Rect(access["balcony"]["bounds"],layer);
      layout.Bay=Rect(access["stairBay"]["bounds"],0);
      layout.DoorWalk=Rect(access["groundWalk"]["mainDoorApproach"],0);
      var foot=Rect(access["groundWalk"]["stairApproach"],0);
      // The stair head is the balcony cell beside the bay; one stair per layer leads away from it.
      var heads=layout.Balcony.Where(b=>layout.Bay.Any(s=>Math.Abs(s.x-b.x)+Math.Abs(s.y-b.y)==1)).ToArray();
      if(heads.Length!=1||layout.Bay.Length!=layer||foot.Length!=1)
        throw new InvalidOperationException("Grocery registration stair bay "+layout.Bay.Length+" cells, balcony layer "+layer+", "+heads.Length+" stair heads, "+foot.Length+" stair approach cells; this fixture needs one stair per layer from one approach cell to one balcony cell");
      layout.StairHead=heads[0];
      var first=layout.Bay.Single(s=>Math.Abs(s.x-heads[0].x)+Math.Abs(s.y-heads[0].y)==1);
      layout.Climb=new Vector3Int(heads[0].x-first.x,heads[0].y-first.y,0);
      layout.StairFoot=foot[0];
      var expectedFoot=heads[0]-layout.Climb*(layer+1);expectedFoot.z=0;
      if(layout.StairFoot!=expectedFoot)throw new InvalidOperationException("Grocery stair approach "+layout.StairFoot+" is not at the foot "+expectedFoot+" of a straight flight to "+heads[0]);
      // The open door walk is the road's column from the road row to the Entrance (CivicFixtureGeometry.Road).
      var column=Enumerable.Range(0,layout.Entrance.y+1).Select(y=>new Vector3Int(layout.Entrance.x,y,0));
      if(!new HashSet<Vector3Int>(layout.DoorWalk).SetEquals(column))
        throw new InvalidOperationException("Grocery main-door approach is not the straight walk from the front edge to the Entrance "+layout.Entrance);
      // Ground walk to the stair approach: up the first column east of it from the road row, which
      // must lie outside the footprint.
      int east=layout.StairFoot.x+1;
      if(east<spec.Size.x)throw new InvalidOperationException("Grocery stair approach "+layout.StairFoot+" has no free column east of it outside the footprint");
      layout.EastWalk=Enumerable.Range(0,layout.StairFoot.y+1).Select(y=>new Vector3Int(east,y,0)).ToArray();
      return layout;
    }
    // Road, main-door Entrance, stair foot, stair head and balcony door in one native navigation network.
    internal static void RequireMarketAccess(BlockObject building,INavMeshService nav,MarketLayout layout) {
      var road=building.TransformCoordinates(layout.Entrance+new Vector3Int(0,-layout.Entrance.y-1,0));
      foreach(var local in new[]{layout.Entrance,layout.StairFoot,layout.StairHead,layout.BalconyDoor}) {
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
