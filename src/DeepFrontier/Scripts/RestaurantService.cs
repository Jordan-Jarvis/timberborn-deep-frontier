using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BehaviorSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.Carrying;
using Timberborn.Characters;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.Persistence;
using Timberborn.PrefabOptimization;
using Timberborn.Rendering;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.WalkingSystem;
using Timberborn.WorkSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Table service is physical. A waiter claims one seated diner and reserves
  // that meal in the restaurant's native inventory, walks to the kitchen pass,
  // takes the lead dish into native GoodCarrier hands, carries it to the table,
  // and only then commits the meal. The carried dish keeps a native GoodReserver
  // capacity reservation in the restaurant, so the vanilla CarryRootBehavior
  // returns it if this behavior ever loses control (unemployment, death of the
  // building). Saves contain: the order (here), the dish in hands (GoodCarrier)
  // and its return slot (GoodReserver); nothing is duplicated or regenerated.
  internal enum RestaurantOrderStage { None, Fetching, Carrying, Returning }
  internal enum RestaurantDelivery { PickedUp, Served, Returned, LeftService }

  internal sealed class RestaurantDeliveryEvent {
    public readonly RestaurantWaiter Waiter;
    public readonly RestaurantDelivery Kind;
    public readonly string Dish;
    public readonly RestaurantDiner Diner;
    public readonly Vector3 Position;
    public RestaurantDeliveryEvent(RestaurantWaiter waiter,RestaurantDelivery kind,string dish,RestaurantDiner diner,Vector3 position) {
      Waiter=waiter;Kind=kind;Dish=dish;Diner=diner;Position=position;
    }
  }

  internal sealed class RestaurantWaiter : BaseComponent, IAwakableComponent, IPersistentEntity, IPostLoadableEntity, IDeletableEntity {
    private static readonly ComponentKey Key=new("DeepFrontierRestaurantWaiter");
    private static readonly PropertyKey<Restaurant> RestaurantKey=new("Restaurant");
    private static readonly PropertyKey<RestaurantDiner> DinerKey=new("Diner");
    private static readonly PropertyKey<int> StageKey=new("Stage");
    private static readonly PropertyKey<string> DishKey=new("Dish");
    private static readonly ListKey<string> ReservedKey=new("ReservedGoods");
    private readonly ReferenceSerializer _references;
    private readonly List<string> _reserved=new();
    private GoodCarrier _carrier;
    private GoodReserver _reserver;
    private Worker _worker;
    private WorkerWorkingHours _hours;
    // Native Inventory does not save stock reservations; each reserver restores
    // its own after load (as GoodReserver does). Until then nothing is held.
    private bool _reservationsHeld;
    private bool _handling;
    public Restaurant Restaurant { get; private set; }
    public RestaurantDiner Diner { get; private set; }
    public RestaurantOrderStage Stage { get; private set; }
    public string Dish { get; private set; }
    public IReadOnlyList<string> ReservedGoods => _reserved;
    // Set by a committed meal so the work behavior releases control once, letting
    // native root behaviors (critical needs) be evaluated between meals.
    public bool JustServed { get; set; }
    public RestaurantWaiter(ReferenceSerializer references) { _references=references; }

    public void Awake() {
      _carrier=GetComponent<GoodCarrier>();_reserver=GetComponent<GoodReserver>();
      _worker=GetComponent<Worker>();_hours=GetComponent<WorkerWorkingHours>();
      _carrier.CarriedGoodsChanged+=OnHandsChanged;
      _worker.GotUnemployed+=OnUnemployed;
      GetComponent<Character>().Died+=OnDied;
    }

    public bool HasOpenOrder(Restaurant restaurant) => restaurant==Restaurant && (Stage==RestaurantOrderStage.Fetching || Stage==RestaurantOrderStage.Carrying);
    public bool CarriesDish => (Stage==RestaurantOrderStage.Carrying || Stage==RestaurantOrderStage.Returning) && _carrier.IsCarrying && _carrier.CarriedGoodId==Dish;
    public bool IsDelivering(Restaurant restaurant,RestaurantDiner diner) => Stage==RestaurantOrderStage.Carrying && Restaurant==restaurant && Diner==diner && CarriesDish;
    public bool CanCompleteReturn => Stage==RestaurantOrderStage.Returning && Alive(Restaurant) && Restaurant.Inventory.Enabled && CarriesDish && _reserver.CapacityReservation.Inventory==Restaurant.Inventory;

    // Every condition under which an open order may continue. Anything else turns
    // the waiter back: an unfetched order is released, a carried dish returned.
    public bool OrderWanted() {
      if(Stage!=RestaurantOrderStage.Fetching && Stage!=RestaurantOrderStage.Carrying)return false;
      if(!Alive(Restaurant) || !Alive(Diner))return false;
      if(Stage==RestaurantOrderStage.Carrying && !CarriesDish)return false;
      return Restaurant.IsOperating && _worker.Workplace==Restaurant.Workplace && _hours.AreWorkingHours
        && !Diner.Served && Diner.Restaurant==Restaurant && Diner.GetComponent<Enterer>().CurrentBuilding==Restaurant.Visitors;
    }

    public void Claim(Restaurant restaurant,RestaurantDiner diner) {
      if(Stage!=RestaurantOrderStage.None || _reserved.Count!=0)throw new InvalidOperationException("Waiter already has a restaurant order");
      if(_carrier.IsCarrying || _reserver.HasReservedStock || _reserver.HasReservedCapacity)throw new InvalidOperationException("Waiter must finish native carrying before taking an order");
      if(!restaurant.HasMeal)throw new InvalidOperationException("Restaurant order claimed without an unreserved main food");
      // Every main food and extra in unreserved stock; the first main food is the carried dish.
      var items=restaurant.Spec.Foods.Concat(restaurant.Spec.OptionalGoods).Where(id=>restaurant.Inventory.UnreservedAmountInStock(id)>=1).ToList();
      foreach(var id in items)restaurant.Inventory.ReserveStock(new GoodAmount(id,1));
      Restaurant=restaurant;Diner=diner;Dish=items[0];
      _reserved.AddRange(items);_reservationsHeld=true;Stage=RestaurantOrderStage.Fetching;
    }

    // At the kitchen pass: the reserved lead dish physically leaves the store
    // into the waiter's hands, with a native return slot kept in the restaurant.
    public void PickUp() {
      if(Stage!=RestaurantOrderStage.Fetching || !_reservationsHeld || !_reserved.Contains(Dish))throw new InvalidOperationException("Waiter picked up without a reserved order");
      if(_carrier.IsCarrying || _reserver.HasReservedCapacity)throw new InvalidOperationException("Waiter hands or return slot already in use");
      var dish=new GoodAmount(Dish,1);
      Restaurant.Inventory.UnreserveStock(dish);_reserved.Remove(Dish);
      Restaurant.Inventory.TakeExisting(dish);
      _carrier.PutGoodsInHands(new CarriedGood(dish,CarriedGoodType.Unavailable));
      _reserver.ReserveCapacity(Restaurant.Inventory,dish);
      Stage=RestaurantOrderStage.Carrying;
      Restaurant.NotifyDelivery(new RestaurantDeliveryEvent(this,RestaurantDelivery.PickedUp,Dish,Diner,Transform.position));
    }

    // Called only by Restaurant.Serve after all service checks. Returns every
    // good of this meal: the carried dish first, then the reserved menu items.
    // The dish is consumed through its reserved return slot in the same
    // synchronous commit (GiveExisting, then TakeConsumed), so the native
    // Consumed stock change that DistrictGoodsBalance records is emitted for it
    // exactly like the other menu items; the unit is never restockable between.
    public List<string> HandOverMeal() {
      if(Stage!=RestaurantOrderStage.Carrying || !CarriesDish || !_reservationsHeld)throw new InvalidOperationException("Meal handed over without a carried dish");
      var served=new List<string>{Dish};
      var dish=new GoodAmount(Dish,1);
      _handling=true;
      try {_reserver.UnreserveCapacity();Restaurant.Inventory.GiveExisting(dish);_carrier.EmptyHands();}
      finally {_handling=false;}
      Restaurant.Inventory.TakeConsumed(dish);
      foreach(var id in _reserved) {
        var good=new GoodAmount(id,1);
        Restaurant.Inventory.UnreserveStock(good);Restaurant.Inventory.TakeConsumed(good);served.Add(id);
      }
      _reserved.Clear();
      Clear();JustServed=true;
      return served;
    }

    // Returns true when a carried dish must be walked back to the kitchen pass.
    public bool BeginReturn() {
      switch(Stage) {
        case RestaurantOrderStage.Fetching:ReleaseItems();Clear();return false;
        case RestaurantOrderStage.Carrying:ReleaseItems();Diner=null;Stage=RestaurantOrderStage.Returning;return true;
        case RestaurantOrderStage.Returning:return true;
        default:return false;
      }
    }

    // Mirrors native CarryRootBehavior.CompleteDelivery at the kitchen pass.
    public void CompleteReturn() {
      if(!CanCompleteReturn)throw new InvalidOperationException("Waiter cannot return the dish to its reserved kitchen slot");
      var restaurant=Restaurant;var dish=Dish;var good=new GoodAmount(dish,1);
      _handling=true;
      try {_reserver.UnreserveCapacity();restaurant.Inventory.GiveExisting(good);_carrier.EmptyHands();}
      finally {_handling=false;}
      Clear();
      restaurant.NotifyDelivery(new RestaurantDeliveryEvent(this,RestaurantDelivery.Returned,dish,null,Transform.position));
    }

    // Hands emptied by something other than service or return: native death,
    // native fallback delivery, or a failed native reservation after load.
    private void OnHandsChanged(object sender,CarriedGoodsChangedEventArgs args) {
      if(_handling || _carrier.IsCarrying)return;
      if(Stage!=RestaurantOrderStage.Carrying && Stage!=RestaurantOrderStage.Returning)return;
      var restaurant=Restaurant;var dish=Dish;var diner=Diner;
      ReleaseItems();Clear();
      if(Alive(restaurant))restaurant.NotifyDelivery(new RestaurantDeliveryEvent(this,RestaurantDelivery.LeftService,dish,diner,Transform.position));
    }
    private void OnUnemployed(object sender,EventArgs args) {
      if(Stage==RestaurantOrderStage.Fetching || Stage==RestaurantOrderStage.Carrying)BeginReturn();
    }
    private void OnDied(object sender,EventArgs args) {
      if(Stage==RestaurantOrderStage.Fetching){ReleaseItems();Clear();}
    }
    public void DeleteEntity() {
      ReleaseItems();Clear();
    }

    private void ReleaseItems() {
      if(_reservationsHeld && Alive(Restaurant))
        foreach(var id in _reserved)Restaurant.Inventory.UnreserveStock(new GoodAmount(id,1));
      _reserved.Clear();
    }
    private void Clear() { Restaurant=null;Diner=null;Dish=null;Stage=RestaurantOrderStage.None;_reserved.Clear(); }
    private static bool Alive(BaseComponent component) => component && !component.GetComponent<EntityComponent>().Deleted;

    public void Save(IEntitySaver saver) {
      if(Stage==RestaurantOrderStage.None || !Alive(Restaurant))return;
      var data=saver.GetComponent(Key);
      data.Set(RestaurantKey,Restaurant,_references.Of<Restaurant>());
      data.Set(StageKey,(int)Stage);data.Set(DishKey,Dish);data.Set(ReservedKey,_reserved);
      // A diner that left or died since the last decision is saved as absent;
      // the next decision then returns the dish. Returning orders have no diner.
      if(Alive(Diner))data.Set(DinerKey,Diner,_references.Of<RestaurantDiner>());
    }
    public void Load(IEntityLoader loader) {
      if(!loader.TryGetComponent(Key,out var data))return;
      Restaurant=data.Get(RestaurantKey,_references.Of<Restaurant>());
      Stage=(RestaurantOrderStage)data.Get(StageKey);
      if(Stage==RestaurantOrderStage.None || !Enum.IsDefined(typeof(RestaurantOrderStage),Stage))throw new InvalidOperationException("Invalid saved restaurant order stage");
      Dish=data.Get(DishKey);_reserved.AddRange(data.Get(ReservedKey));
      Diner=data.Has(DinerKey)?data.Get(DinerKey,_references.Of<RestaurantDiner>()):null;
      if(Stage==RestaurantOrderStage.Returning && (Diner!=null || _reserved.Count!=0))throw new InvalidOperationException("A returning restaurant dish cannot hold a diner or reserved goods");
      _reservationsHeld=false;
    }
    public void PostLoadEntity() {
      if(Stage==RestaurantOrderStage.None)return;
      foreach(var id in _reserved)Restaurant.Inventory.ReserveStock(new GoodAmount(id,1));
      _reservationsHeld=true;
    }
  }

  // Native walking with one addition: the waiter turns back as soon as the order
  // is no longer wanted, instead of finishing the trip first.
  internal sealed class RestaurantWaiterWalkExecutor : BaseComponent, IAwakableComponent, IExecutor {
    private WalkToPositionExecutor _walk;
    private Walker _walker;
    private RestaurantWaiter _waiter;
    public void Awake() { _walk=GetComponent<WalkToPositionExecutor>();_walker=GetComponent<Walker>();_waiter=GetComponent<RestaurantWaiter>(); }
    public ExecutorStatus Launch(Vector3 destination) => _walk.Launch(destination);
    public ExecutorStatus Tick(float deltaTimeInHours) {
      if(!_waiter.OrderWanted()) {_walker.StopNextTick();return ExecutorStatus.Failure;}
      return _walk.Tick(deltaTimeInHours);
    }
    // The order lives in RestaurantWaiter and the route in the native Walker.
    public void Save(IEntitySaver saver) {}
    public void Load(IEntityLoader loader) {}
  }

  // Authored per seat: where a served dish rests, in the seat's native slot
  // frame (+Z faces the table, +Y up, +X the diner's right). The bottom-center
  // of the dish model is placed there.
  internal record RestaurantTableDishSpec {
    [Serialize] public string Seat { get; init; }
    [Serialize] public Vector3 Offset { get; init; }
  }
  internal record RestaurantTableServiceSpec : ComponentSpec {
    [Serialize] public ImmutableArray<RestaurantTableDishSpec> Dishes { get; init; }
  }

  // While a seated diner is served, the lead dish stands on their table as the
  // native single-good Box model (GoodStack's Environment/Common/Box mesh) with
  // the native good icon, as stockpiles and dropped goods display food.
  internal sealed class RestaurantTableService : TickableComponent, IAwakableComponent, IFinishedStateListener {
    private static readonly string GoodStackModelPath="Environment/GoodStack/GoodStackModel.blueprint";
    private static readonly string[] UnusedContainers={"#Barrel","#Log","#Bag"};
    private const float DishScale=.5f;
    private readonly ISpecService _specs;
    private readonly OptimizedPrefabInstantiator _instantiator;
    private readonly GoodIconVisualizer _icons;
    private readonly IGoodService _goods;
    private Restaurant _restaurant;
    private RestaurantSeats _seats;
    private RestaurantTableServiceSpec _spec;
    private readonly Dictionary<string,GameObject> _dishes=new();
    private readonly HashSet<string> _shown=new();
    public RestaurantTableService(ISpecService specs,OptimizedPrefabInstantiator instantiator,GoodIconVisualizer icons,IGoodService goods) {
      _specs=specs;_instantiator=instantiator;_icons=icons;_goods=goods;
    }
    public void Awake() {
      _restaurant=GetComponent<Restaurant>();_seats=GetComponent<RestaurantSeats>();_spec=GetComponent<RestaurantTableServiceSpec>();
      var seats=GetComponent<RestaurantSpec>().Seats.Select(s=>s.Name).ToArray();
      if(_spec.Dishes.Length!=seats.Length || !_spec.Dishes.Select(d=>d.Seat).OrderBy(n=>n).SequenceEqual(seats.OrderBy(n=>n)))
        throw new InvalidOperationException("Restaurant table dishes must cover each guest seat exactly once");
      foreach(var dish in _spec.Dishes)if(dish.Offset.y<=0 || dish.Offset.z<=0)throw new InvalidOperationException("Restaurant table dish must rest above and in front of its seat: "+dish.Seat);
      DisableComponent();
    }
    public void OnEnterFinishedState() { EnableComponent(); }
    public void OnExitFinishedState() {
      foreach(var seat in _shown)_dishes[seat].SetActive(false);
      _shown.Clear();DisableComponent();
    }
    public bool IsDishShown(string seat) => _shown.Contains(seat);
    public override void Tick() {
      foreach(var dish in _spec.Dishes) {
        var diner=_seats.DinerAt(dish.Seat);
        bool show=diner && diner.Served && diner.Restaurant==_restaurant && diner.GetComponent<Enterer>().CurrentBuilding==_restaurant.Visitors;
        if(show==_shown.Contains(dish.Seat))continue;
        Dish(dish).SetActive(show);
        if(show)_shown.Add(dish.Seat);else _shown.Remove(dish.Seat);
      }
    }
    private GameObject Dish(RestaurantTableDishSpec spec) {
      if(_dishes.TryGetValue(spec.Seat,out var existing))return existing;
      var anchor=_seats.SeatTransform(spec.Seat);
      var root=_instantiator.InstantiateInactive(_specs.GetBlueprint(GoodStackModelPath),anchor);
      root.name="DeepFrontierTableDish."+spec.Seat.Substring(spec.Seat.LastIndexOf('#')+1);
      var children=root.GetComponentsInChildren<Transform>(true);
      var box=children.Single(t=>t.name=="#Box");
      foreach(var name in UnusedContainers)children.Single(t=>t.name==name).gameObject.SetActive(false);
      root.transform.localRotation=Quaternion.identity;root.transform.localScale=Vector3.one*DishScale;root.transform.localPosition=spec.Offset;
      box.localPosition=Vector3.zero;box.localRotation=Quaternion.identity;
      GetComponent<EntityMaterials>().AddMaterials(root);
      var renderer=box.GetComponentInChildren<MeshRenderer>(true);
      _icons.ShowIcon(renderer.material,_goods.GetGood(_restaurant.Spec.Foods[0]));
      // Rest the mesh's actual bottom-center on the authored point. Transforms
      // are valid while inactive, so no visible frame is spent misplaced.
      var filter=box.GetComponentInChildren<MeshFilter>(true);
      var bounds=filter.sharedMesh.bounds;
      float bottom=float.MaxValue;
      for(int i=0;i<8;i++) {
        var corner=bounds.center+Vector3.Scale(bounds.extents,new Vector3((i&1)==0?-1:1,(i&2)==0?-1:1,(i&4)==0?-1:1));
        bottom=Mathf.Min(bottom,filter.transform.TransformPoint(corner).y);
      }
      var center=filter.transform.TransformPoint(bounds.center);
      var target=anchor.TransformPoint(spec.Offset);
      root.transform.position+=new Vector3(target.x-center.x,target.y-bottom,target.z-center.z);
      _dishes.Add(spec.Seat,root);
      return root;
    }
  }

  [Context("Game")]
  public sealed class RestaurantServiceConfigurator : Configurator {
    protected override void Configure() {
      Bind<RestaurantWaiter>().AsTransient();Bind<RestaurantWaiterWalkExecutor>().AsTransient();Bind<RestaurantTableService>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var b=new TemplateModule.Builder();
      b.AddDecorator<Worker,RestaurantWaiter>();b.AddDecorator<Worker,RestaurantWaiterWalkExecutor>();
      b.AddDecorator<RestaurantTableServiceSpec,RestaurantTableService>();
      return b.Build();
    }
  }
}
