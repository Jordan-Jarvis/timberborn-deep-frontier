using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BehaviorSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.Carrying;
using Timberborn.Common;
using Timberborn.Effects;
using Timberborn.Emptying;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.Goods;
using Timberborn.Hauling;
using Timberborn.InventoryNeedSystem;
using Timberborn.InventorySystem;
using Timberborn.MechanicalSystem;
using Timberborn.NeedBehaviorSystem;
using Timberborn.NeedSpecs;
using Timberborn.NeedSystem;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.SlotSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.TimbermeshAnimations;
using Timberborn.WalkingSystem;
using Timberborn.WorkSystem;
using Timberborn.Workshops;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts {
  internal record RestaurantSeatSpec {
    [Serialize] public string Name { get; init; }
    [Serialize] public Vector3 ServicePosition { get; init; }
  }
  internal record RestaurantSpec : ComponentSpec {
    [Serialize] public ImmutableArray<string> Foods { get; init; }
    [Serialize] public ImmutableArray<string> OptionalGoods { get; init; }
    [Serialize] public string DrinkingWater { get; init; }
    [Serialize] public ImmutableArray<RestaurantStockSpec> Stock { get; init; }
    [Serialize] public Vector3 KitchenPosition { get; init; }
    [Serialize] public int MealsCapacity { get; init; }
    [Serialize] public float ServiceHours { get; init; }
    [Serialize] public float EatingHours { get; init; }
    [Serialize] public ImmutableArray<RestaurantSeatSpec> Seats { get; init; }
    [Serialize] public Vector3 StaffIdlePosition { get; init; }
    [Serialize] public ImmutableArray<ContinuousEffectSpec> VisitEffects { get; init; }
  }
  internal record RestaurantStockSpec {
    [Serialize] public string GoodId { get; init; }
    [Serialize] public int Capacity { get; init; }
    [Serialize] public bool AlwaysStocked { get; init; }
  }

  // One native inventory. A transaction is committed only by a waiter beside
  // the diner's table who carried the dish there from the kitchen pass, after
  // the service time. Waiting itself grants no effects. See RestaurantService.cs.
  internal sealed class Restaurant : BaseComponent, IAwakableComponent, IFinishedStateListener {
    private readonly IGoodService _goods;
    private readonly EventBus _events;
    private readonly IDayNightCycle _clock;
    private BlockableObject _blockable;
    private MechanicalBuilding _power;
    private IAnimator _sign;
    private InstantEffectSpec _waterEffect;
    public RestaurantSpec Spec { get; private set; }
    public Inventory Inventory { get; private set; }
    public Enterable Visitors { get; private set; }
    public Workplace Workplace { get; private set; }
    public int MealsServedThisSession { get; private set; }
    public event Action<RestaurantDiner,IReadOnlyList<string>> MealServed;
    public event Action<RestaurantDeliveryEvent> DeliveryChanged;
    public bool IsOperating => Enabled && _blockable.IsUnblocked && _power.ActiveAndPowered;
    // Unreserved stock: meals already claimed by waiters hold native reservations.
    // A meal is every main food in stock, so it may be partial; a full meal
    // (one of each) also grants Fine Dining (the RestaurantDining need).
    public bool HasMeal => Spec.Foods.Any(id=>Inventory.UnreservedAmountInStock(id)>=1);
    public bool HasFullMeal => Spec.Foods.All(id=>Inventory.UnreservedAmountInStock(id)>=1);
    public const string FineDiningNeed="RestaurantDining";
    public bool StaffOnDuty => Workplace.AssignedWorkers.Any(w=>w.GetComponent<WorkerWorkingHours>().AreWorkingHours);
    public bool AcceptsGuests => IsOperating && HasMeal && StaffOnDuty;
    // Unemployment cancels or returns an order, so assigned staff hold all open orders.
    public IEnumerable<RestaurantWaiter> OpenOrders => Workplace.AssignedWorkers.Select(w=>w.GetComponent<RestaurantWaiter>()).Where(o=>o.HasOpenOrder(this));
    public bool HasOrderFor(RestaurantDiner diner) => OpenOrders.Any(o=>o.Diner==diner);
    public Vector3 KitchenPassPosition => Transform.TransformPoint(Spec.KitchenPosition);
    internal void NotifyDelivery(RestaurantDeliveryEvent delivery) => DeliveryChanged?.Invoke(delivery);
    public Restaurant(IGoodService goods,EventBus events,IDayNightCycle clock) { _goods=goods;_events=events;_clock=clock; }
    public void InitializeInventory(Inventory inventory) { Inventory=inventory; }
    public void Awake() {
      Spec=GetComponent<RestaurantSpec>(); Visitors=GetComponent<Enterable>();
      Workplace=GetComponent<Workplace>(); _blockable=GetComponent<BlockableObject>(); _power=GetComponent<MechanicalBuilding>();
      var finished=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      // AnimationInitializer attaches the one animator to the imported model
      // root; the sign node owns the track, not the animator component.
      _sign=finished.GetComponentsInChildren<MonoBehaviour>(true).OfType<IAnimator>().Single();
      if(Spec.Foods.Length==0 || Spec.Foods.Distinct().Count()!=Spec.Foods.Length || Spec.MealsCapacity<=0 || Spec.ServiceHours<=0)
        throw new InvalidOperationException("Invalid authored restaurant menu/capacity/service duration");
      foreach(var id in Spec.Foods) if(!_goods.GetGood(id).ConsumptionEffects.Any(e=>e.NeedId=="Hunger"&&e.Points>0))
        throw new InvalidOperationException("Restaurant menu must use edible native goods: "+id);
      _waterEffect=_goods.GetGood(Spec.DrinkingWater).ConsumptionEffects.Single(e=>e.NeedId=="Thirst"&&e.Points>0);
      if(Spec.Foods.Contains(Spec.DrinkingWater)||Spec.OptionalGoods.Contains(Spec.DrinkingWater))
        throw new InvalidOperationException("Drinking water must be conditional, not an unconditional meal item");
      DisableComponent();
    }
    // The shared inventory belongs to the native Manufactory (RestaurantKitchenInventory),
    // whose own OnEnter/ExitFinishedState enables/disables it. Enabling it here
    // too registered it twice in the district (DistrictInventoryAssigner keeps a
    // list) and doubled the district goods statistics.
    public void OnEnterFinishedState() {
      if(!GetComponent<Manufactory>().NeedsInventory)throw new InvalidOperationException("Restaurant kitchen recipes must make the native Manufactory own the shared inventory");
      _sign.Enabled=true;_sign.Play("Default");EnableComponent();
    }
    public void OnExitFinishedState() { _sign.Stop();DisableComponent(); }
    // A restaurant's own staff never dine at their own tables: a seated waiter
    // cannot serve, yet would keep StaffOnDuty true and stall the dining room.
    public bool IsOwnStaff(BaseComponent beaver) { var worker=beaver.GetComponent<Worker>(); return worker && worker.Workplace==Workplace; }
    // Staff switch between serving and cooking every decision (each kitchen
    // stint is a 0.25 h ProduceExecutor): RestaurantWorkBehavior runs before
    // RestaurantKitchenBehavior, so anyone with no guest to serve cooks. Half
    // the assigned staff (rounded down) are cooks, who keep cooking even while
    // guests wait. So 4 staff: 4 cooks with an empty dining room, 2 when busy.
    // Without cooks a full dining room kept every worker serving and no batch
    // ever progressed. A single worker serves first and cooks between guests.
    public bool IsCook(Worker worker) {
      var staff=Workplace.AssignedWorkers;
      for(int i=0;i<staff.Count/2;i++)if(staff[i]==worker)return true;
      return false;
    }
    public bool Serve(RestaurantWaiter waiter) {
      var diner=waiter.Diner;var worker=waiter.GetComponent<Worker>();
      if(!IsOperating || !StaffOnDuty || worker.Workplace!=Workplace || !worker.JobRunning || !diner || diner.Restaurant!=this || diner.Served || diner.GetComponent<Enterer>().CurrentBuilding!=Visitors || !waiter.IsDelivering(this,diner)) return false;
      // All inputs are checked before any debit. The native simulation executes
      // this synchronous transaction without yielding to a hauler or another job.
      // The carried dish and the order's reserved menu items form the meal.
      var needs=diner.GetComponent<NeedManager>();
      var served=waiter.HandOverMeal();
      // Native Thirst is non-wastable. Serve a unit when the diner can use its
      // complete native effect, without consuming water for a hydrated guest.
      if(needs.NeedPointsToMax(_waterEffect.NeedId)>=_waterEffect.Points && Inventory.UnreservedAmountInStock(Spec.DrinkingWater)>=1) {
        Inventory.TakeConsumed(new GoodAmount(Spec.DrinkingWater,1));served.Add(Spec.DrinkingWater);
      }
      foreach(var id in served) {
        foreach(var effect in _goods.GetGood(id).ConsumptionEffects) needs.ApplyEffect(InstantEffect.FromSpec(effect,1));
        _events.Post(new GoodConsumedEvent(id));
      }
      // Only a full meal adds Fine Dining; a partial meal gives just its foods' own effects.
      if(Spec.Foods.All(served.Contains))needs.ApplyEffect(new InstantEffect(FineDiningNeed,1f,1));
      diner.MarkServed(_clock.PartialDayNumber); MealsServedThisSession++;
      NotifyDelivery(new RestaurantDeliveryEvent(waiter,RestaurantDelivery.Served,served[0],diner,waiter.Transform.position));
      MealServed?.Invoke(diner,served);
      return true;
    }
  }

  // Native TransformSlots still own sitting and animation. Retaining their
  // public ISlot handles lets a server find the assigned table without reflection.
  internal sealed class RestaurantSeats : SlotInitializer {
    private readonly TransformSlotFactory _factory;
    private readonly Dictionary<string,ISlot> _slots=new();
    private readonly Dictionary<string,Transform> _transforms=new();
    public RestaurantSeats(TransformSlotFactory factory) { _factory=factory; }
    public override IEnumerable<ISlot> InitializeSlots() {
      if(_slots.Count!=0) throw new InvalidOperationException("Restaurant seats already initialized");
      var finished=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      var transforms=finished.GetComponentsInChildren<Transform>(true);
      foreach(var seat in GetComponent<RestaurantSpec>().Seats) {
        var transform=transforms.Single(t=>t.name==seat.Name);
        _transforms.Add(seat.Name,transform);
        _slots.Add(seat.Name,_factory.Create(transform,new TransformSlotSpec {SlotKeyword="Seat",Animation="Sitting",Inanimate=false,RandomizeYRotation=false,WaterSlot=false}));
      }
      return _slots.Values;
    }
    public IEnumerable<RestaurantDiner> SeatedDiners => _slots.Values.Where(s=>s.AssignedEnterer).Select(s=>s.AssignedEnterer.GetComponent<RestaurantDiner>());
    public Transform SeatTransform(string seat) => _transforms[seat];
    public RestaurantDiner DinerAt(string seat) { var enterer=_slots[seat].AssignedEnterer; return enterer?enterer.GetComponent<RestaurantDiner>():null; }
    public string SeatOf(RestaurantDiner diner) => _slots.Single(s=>s.Value.AssignedEnterer==diner.GetComponent<Enterer>()).Key;
    public Vector3 ServicePosition(RestaurantDiner diner) {
      var slot=_slots.Single(s=>s.Value.AssignedEnterer==diner.GetComponent<Enterer>());
      return Transform.TransformPoint(GetComponent<RestaurantSpec>().Seats.Single(s=>s.Name==slot.Key).ServicePosition);
    }
  }

  // Absence of this saved component means no dining visit has begun. A saved
  // visit requires every field; malformed state is never silently repaired.
  internal sealed class RestaurantDiner : BaseComponent, IAwakableComponent, IPersistentEntity {
    private static readonly ComponentKey Key=new("DeepFrontierRestaurantDiner");
    private static readonly PropertyKey<Restaurant> RestaurantKey=new("Restaurant");
    private static readonly PropertyKey<bool> ServedKey=new("Served");
    private static readonly PropertyKey<float> ServedAtKey=new("ServedAt");
    private readonly ReferenceSerializer _references;
    public Restaurant Restaurant { get; private set; }
    public bool Served { get; private set; }
    public float ServedAt { get; private set; }
    public RestaurantDiner(ReferenceSerializer references) { _references=references; }
    public void Awake() { GetComponent<Enterer>().ExitedEnterable+=OnExit; }
    public void BeginVisit(Restaurant restaurant) {
      if(Restaurant==restaurant)return;
      if(Restaurant!=null)throw new InvalidOperationException("Restaurant visit changed without exiting");
      Restaurant=restaurant;Served=false;ServedAt=0;
    }
    public void MarkServed(float timestamp) { if(Served)throw new InvalidOperationException("Duplicate restaurant meal"); Served=true;ServedAt=timestamp; }
    private void OnExit(object sender,EventArgs args) { Restaurant=null;Served=false;ServedAt=0; }
    public void Save(IEntitySaver saver) {
      if(Restaurant==null)return;
      var data=saver.GetComponent(Key);data.Set(RestaurantKey,Restaurant,_references.Of<Restaurant>());data.Set(ServedKey,Served);data.Set(ServedAtKey,ServedAt);
    }
    public void Load(IEntityLoader loader) {
      if(!loader.TryGetComponent(Key,out var data))return;
      Restaurant=data.Get(RestaurantKey,_references.Of<Restaurant>());Served=data.Get(ServedKey);ServedAt=data.Get(ServedAtKey);
    }
  }

  internal sealed class RestaurantVisitBehavior : NeedBehavior, IAwakableComponent, IFinishedStateListener {
    private readonly IDayNightCycle _clock;
    private Restaurant _restaurant;
    private DistrictBuilding _district;
    private DistrictNeedBehaviorService _needs;
    public RestaurantVisitBehavior(IDayNightCycle clock) { _clock=clock; }
    public void Awake() { _restaurant=GetComponent<Restaurant>();_district=GetComponent<DistrictBuilding>();DisableComponent(); }
    public override Vector3? ActionPosition(NeedManager needManager) {
      var diner=needManager.GetComponent<RestaurantDiner>();
      if(!Enabled || _restaurant.IsOwnStaff(needManager) || !_restaurant.AcceptsGuests || diner.Served || (!_restaurant.Visitors.CanReserveSlot&&needManager.GetComponent<Enterer>().CurrentBuilding!=_restaurant.Visitors))return null;
      return GetComponent<BuildingAccessible>().Accessible.UnblockedSingleAccess;
    }
    public override Decision Decide(BehaviorAgent agent) {
      var diner=agent.GetComponent<RestaurantDiner>();
      var enterer=agent.GetComponent<Enterer>();
      // Also leaves when a seated guest is employed here meanwhile (unemployed
      // beavers are assigned to workplaces automatically).
      if(!Enabled || !_restaurant.IsOperating || !_restaurant.StaffOnDuty || _restaurant.IsOwnStaff(agent)) {enterer.UnreserveSlotAndExit();return Decision.ReleaseNextTick();}
      var walk=agent.GetComponent<WalkInsideExecutor>();
      switch(walk.Launch(_restaurant.Visitors)) {
        case ExecutorStatus.Running:return Decision.ReturnWhenFinished(walk);
        case ExecutorStatus.Failure:enterer.UnreserveSlotAndExit();return Decision.ReleaseNextTick();
        case ExecutorStatus.Success:break;
        default:throw new ArgumentOutOfRangeException();
      }
      diner.BeginVisit(_restaurant);
      if(diner.Served && (_clock.PartialDayNumber-diner.ServedAt)*24>=_restaurant.Spec.EatingHours) {
        enterer.Exit();return Decision.ReleaseNextTick();
      }
      // A claimed meal is held by native reservations, so HasMeal may be false
      // while this diner's own order is in the kitchen or on its way.
      if(!diner.Served && !_restaurant.HasMeal && !_restaurant.HasOrderFor(diner)) {enterer.Exit();return Decision.ReleaseNextTick();}
      var wait=agent.GetComponent<WaitExecutor>();wait.LaunchForSpecifiedTime(.05f);return Decision.ReturnWhenFinished(wait);
    }
    public void OnEnterFinishedState() { _district.ReassignedDistrict+=OnDistrict;EnableComponent(); }
    public void OnExitFinishedState() { _district.ReassignedDistrict-=OnDistrict;RemoveDistrict();DisableComponent(); }
    private void OnDistrict(object sender,EventArgs args) {
      RemoveDistrict();if(!_district.District)return;
      _needs=_district.District.GetComponent<DistrictNeedBehaviorService>();_needs.AddNeedBehavior(_restaurant.Spec.VisitEffects,this);
    }
    private void RemoveDistrict() { if(_needs!=null){_needs.RemoveNeedBehavior(_restaurant.Spec.VisitEffects,this);_needs=null;} }
  }

  // Waiters fetch each meal from the kitchen pass and carry it to the table.
  // The order, its reserved stock and the dish in hands all persist natively;
  // this behavior holds no in-memory claims (see RestaurantWaiter).
  internal sealed class RestaurantWorkBehavior : WorkplaceBehavior, IAwakableComponent {
    private Restaurant _restaurant;
    private RestaurantSeats _seats;
    private Manufactory _kitchen;
    public void Awake() { _restaurant=GetComponent<Restaurant>();_seats=GetComponent<RestaurantSeats>();_kitchen=GetComponent<Manufactory>(); }
    public override Decision Decide(BehaviorAgent agent) {
      var waiter=agent.GetComponent<RestaurantWaiter>();
      if(waiter.Stage==RestaurantOrderStage.Returning)return Return(agent,waiter);
      if(waiter.Stage==RestaurantOrderStage.None) {
        if(waiter.JustServed){waiter.JustServed=false;return Decision.ReleaseNextTick();}
        if(agent.GetComponent<Worker>().Workplace!=_restaurant.Workplace || !_restaurant.IsOperating || !_restaurant.HasMeal || !agent.GetComponent<WorkerWorkingHours>().AreWorkingHours)return Decision.ReleaseNow();
        // Cooks leave new orders to the others while the kitchen can produce (RestaurantKitchenBehavior runs next).
        if(_restaurant.IsCook(agent.GetComponent<Worker>()) && _kitchen.IsReadyToProduce)return Decision.ReleaseNow();
        // Native carrying (CarryRootBehavior) owns any goods or reservations first.
        var reserver=agent.GetComponent<GoodReserver>();
        if(agent.GetComponent<GoodCarrier>().IsCarrying || reserver.HasReservedStock || reserver.HasReservedCapacity)return Decision.ReleaseNow();
        var guest=_seats.SeatedDiners.FirstOrDefault(d=>!d.Served && d.Restaurant==_restaurant && d.GetComponent<Enterer>().CurrentBuilding==_restaurant.Visitors && !_restaurant.HasOrderFor(d));
        if(!guest)return Decision.ReleaseNow();
        waiter.Claim(_restaurant,guest);
      } else if(waiter.Restaurant!=_restaurant || !waiter.OrderWanted()) {
        return waiter.BeginReturn()?Return(agent,waiter):Decision.ReleaseNextTick();
      }
      var walk=agent.GetComponent<RestaurantWaiterWalkExecutor>();
      if(waiter.Stage==RestaurantOrderStage.Fetching) {
        switch(walk.Launch(_restaurant.KitchenPassPosition)) {
          case ExecutorStatus.Running:return Decision.ReturnWhenFinished(walk);
          case ExecutorStatus.Failure:waiter.BeginReturn();return Decision.ReleaseNextTick();
          case ExecutorStatus.Success:waiter.PickUp();break;
          default:throw new ArgumentOutOfRangeException();
        }
      }
      switch(walk.Launch(_seats.ServicePosition(waiter.Diner))) {
        case ExecutorStatus.Running:return Decision.ReturnWhenFinished(walk);
        case ExecutorStatus.Failure:return waiter.BeginReturn()?Return(agent,waiter):Decision.ReleaseNextTick();
        case ExecutorStatus.Success:
          var service=agent.GetComponent<RestaurantServeExecutor>();service.Launch(_restaurant,waiter.Diner);return Decision.ReturnWhenFinished(service);
        default:throw new ArgumentOutOfRangeException();
      }
    }
    // An undelivered dish goes back to the kitchen pass, even outside working
    // hours, exactly like a native hauler finishing its carry. If that is not
    // possible, releasing leaves the dish to native CarryRootBehavior, which
    // delivers it to the reserved restaurant capacity.
    private static Decision Return(BehaviorAgent agent,RestaurantWaiter waiter) {
      if(!waiter.CanCompleteReturn)return Decision.ReleaseNextTick();
      var walk=agent.GetComponent<WalkToPositionExecutor>();
      switch(walk.Launch(waiter.Restaurant.KitchenPassPosition)) {
        case ExecutorStatus.Running:return Decision.ReturnWhenFinished(walk);
        case ExecutorStatus.Failure:return Decision.ReleaseNextTick();
        case ExecutorStatus.Success:waiter.CompleteReturn();return Decision.ReleaseNextTick();
        default:throw new ArgumentOutOfRangeException();
      }
    }
  }
  // Service time at the table while holding the dish; the meal is committed at
  // its end. Saved Restaurant/Diner/RemainingHours keep the build-41 save format.
  internal sealed class RestaurantServeExecutor : BaseComponent, IExecutor {
    private static readonly ComponentKey Key=new("DeepFrontierRestaurantService");
    private static readonly PropertyKey<Restaurant> RestaurantKey=new("Restaurant");
    private static readonly PropertyKey<RestaurantDiner> DinerKey=new("Diner");
    private static readonly PropertyKey<float> RemainingKey=new("RemainingHours");
    private readonly ReferenceSerializer _references;
    private Restaurant _restaurant;
    private RestaurantDiner _diner;
    public RestaurantDiner Diner => _diner;
    private float _remaining;
    public RestaurantServeExecutor(ReferenceSerializer references) { _references=references; }
    public void Launch(Restaurant restaurant,RestaurantDiner diner) { _restaurant=restaurant;_diner=diner;_remaining=restaurant.Spec.ServiceHours; }
    public ExecutorStatus Tick(float deltaTimeInHours) {
      var waiter=GetComponent<RestaurantWaiter>();
      if(!_restaurant || !_diner || !waiter.IsDelivering(_restaurant,_diner) || !waiter.OrderWanted())return ExecutorStatus.Failure;
      var target=_restaurant.GetComponent<RestaurantSeats>().ServicePosition(_diner);
      if(Vector3.Distance(Transform.position,target)>.3f)return ExecutorStatus.Failure;
      _remaining-=deltaTimeInHours;
      if(_remaining>0)return ExecutorStatus.Running;
      return _restaurant.Serve(waiter)?ExecutorStatus.Success:ExecutorStatus.Failure;
    }
    public void Save(IEntitySaver saver) {
      var data=saver.GetComponent(Key);data.Set(RestaurantKey,_restaurant,_references.Of<Restaurant>());data.Set(DinerKey,_diner,_references.Of<RestaurantDiner>());data.Set(RemainingKey,_remaining);
    }
    public void Load(IEntityLoader loader) {
      var data=loader.GetComponent(Key);_restaurant=data.Get(RestaurantKey,_references.Of<Restaurant>());_diner=data.Get(DinerKey,_references.Of<RestaurantDiner>());_remaining=data.Get(RemainingKey);
    }
  }
  internal sealed class RestaurantIdleBehavior : WorkplaceBehavior {
    public override Decision Decide(BehaviorAgent agent) {
      var walk=agent.GetComponent<WalkToPositionExecutor>();
      switch(walk.Launch(Transform.TransformPoint(GetComponent<RestaurantSpec>().StaffIdlePosition))) {
        case ExecutorStatus.Running:return Decision.ReleaseWhenFinished(walk);
        case ExecutorStatus.Failure:return Decision.ReleaseNextTick();
        case ExecutorStatus.Success:var wait=agent.GetComponent<WaitExecutor>();wait.LaunchForIdleTime();return Decision.ReleaseWhenFinished(wait);
        default:throw new ArgumentOutOfRangeException();
      }
    }
  }

  // Cooking uses the original ProduceExecutor and Manufactory. Staff reach a
  // kitchen work point without reserving one of the fourteen guest chairs.
  internal sealed class RestaurantKitchenBehavior : WorkplaceBehavior {
    public override Decision Decide(BehaviorAgent agent) {
      var restaurant=GetComponent<Restaurant>();
      if(!restaurant.IsOperating || !GetComponent<Manufactory>().IsReadyToProduce)return Decision.ReleaseNow();
      var walk=agent.GetComponent<WalkToPositionExecutor>();
      switch(walk.Launch(Transform.TransformPoint(restaurant.Spec.KitchenPosition))) {
        case ExecutorStatus.Running:return Decision.ReleaseWhenFinished(walk);
        case ExecutorStatus.Failure:return Decision.ReleaseNextTick();
        case ExecutorStatus.Success:
          var produce=agent.GetComponent<ProduceExecutor>();
          return produce.Launch(.25f)?Decision.ReleaseWhenFinished(produce):Decision.ReleaseNextTick();
        default:throw new ArgumentOutOfRangeException();
      }
    }
  }

  internal enum RestaurantKitchenReason { None, LowestStock, TakingTurns, OnlyCookable, Waiting, Stocked }

  // The kitchen picks its own recipe; the player never selects one. Native
  // AutomaticRecipeManufactory (decorated on the Restaurant) hides the native
  // ManufactoryFragment recipe picker and NoRecipeStatus, as Timberborn
  // 1.1.2.8 does for code-driven manufactories.
  //
  // It drives the native Manufactory with SetRecipe, which resets production
  // progress and the consumed-ingredients flag. Each recipe keeps its own
  // batch: haulers also deliver the dishes the kitchen cooks, so a batch's
  // products can stop fitting mid-way, and native IncreaseProductionProgress
  // then stalls. Such a batch is set aside with its progress (its ingredients
  // are already consumed) while another recipe cooks, and resumes with that
  // progress once its products fit. Set-aside batches are saved here; the
  // native Manufactory saves the batch cooking now. Nothing is discarded.
  // A choice is made after every finished batch (Manufactory.ProductionFinished),
  // whenever the current recipe is missing or cannot start, and whenever the
  // current batch's products no longer fit:
  // - cookable: a set-aside batch whose products fit, or a recipe with every
  //   ingredient (and fuel) in unreserved stock and room for every product,
  //   the native IsReadyToProduce inputs;
  // - preferred: the dish with the lowest stock relative to its authored
  //   RestaurantSpec stock capacity;
  // - ties: the next recipe after the current one, in the authored order.
  // With nothing cookable the current recipe stays, so the native
  // LackOfResources status appears only then. Moddable Recipes' rebuild never
  // runs for the Restaurant (RestaurantKitchenRecipeCompatibility), so a switch
  // keeps every recipe's ingredients in the one inventory.
  internal sealed class RestaurantKitchenChooser : TickableComponent, IAwakableComponent, IFinishedStateListener, IPersistentEntity {
    private static readonly ComponentKey Key=new("DeepFrontierRestaurantKitchen");
    private static readonly ListKey<string> SetAsideRecipesKey=new("SetAsideRecipes");
    private static readonly ListKey<float> SetAsideProgressKey=new("SetAsideProgress");
#if !UNITY_EDITOR
    private static readonly Action<Manufactory,float> SetProgress=HarmonyLib.AccessTools.MethodDelegate<Action<Manufactory,float>>(
      HarmonyLib.AccessTools.PropertySetter(typeof(Manufactory),nameof(Manufactory.ProductionProgress)));
    private static readonly HarmonyLib.AccessTools.FieldRef<Manufactory,bool> IngredientsConsumed=
      HarmonyLib.AccessTools.FieldRefAccess<Manufactory,bool>("_ingredientsConsumed");
    private static readonly Action<Manufactory> UpdateGoodRegistry=HarmonyLib.AccessTools.MethodDelegate<Action<Manufactory>>(
      HarmonyLib.AccessTools.Method(typeof(Manufactory),"UpdateGoodRegistry"));
#endif
    private readonly Dictionary<RecipeSpec,float> _setAside=new();
    private Manufactory _kitchen;
    private Restaurant _restaurant;
    private bool _batchFinished;
    public RestaurantKitchenReason Reason { get; private set; }
    public RecipeSpec Cooking => _kitchen.CurrentRecipe;
    public int Switches { get; private set; }
    // Real progress of each recipe's batch: the native one cooking now, or a set-aside one.
    public float Progress(RecipeSpec recipe)=>recipe==_kitchen.CurrentRecipe?_kitchen.ProductionProgress:_setAside.GetValueOrDefault(recipe);

    public void Awake() {
      _kitchen=GetComponent<Manufactory>();_restaurant=GetComponent<Restaurant>();
      if(!_kitchen||!_restaurant||!GetComponent<AutomaticRecipeManufactory>())
        throw new InvalidOperationException("Restaurant kitchen chooser requires the native Manufactory and AutomaticRecipeManufactory");
      _kitchen.ProductionFinished+=(_,_)=>_batchFinished=true;
      DisableComponent();
    }
    public void OnEnterFinishedState() {EnableComponent();}
    public void OnExitFinishedState() {DisableComponent();}

    public override void Tick() {
      var current=_kitchen.CurrentRecipe;
      if(_kitchen.ProductionProgress>0f) {
        // Mid-batch: keep cooking while its products fit; otherwise set it aside for a recipe that can cook.
        if(_kitchen.HasUnreservedCapacityForCurrentProducts())return;
        var others=_kitchen.ProductionRecipes.Where(r=>r!=current&&Cookable(r)).ToList();
        if(others.Count==0)return;
        _setAside.Add(current,_kitchen.ProductionProgress);
        Switch(Choose(others,current,out var setAsideReason));Reason=setAsideReason;
        return;
      }
      if(!_batchFinished&&current!=null&&Cookable(current))return;
      var cookable=_kitchen.ProductionRecipes.Where(Cookable).ToList();
      if(cookable.Count==0) {
        Reason=_kitchen.ProductionRecipes.Any(HasIngredients)?RestaurantKitchenReason.Stocked:RestaurantKitchenReason.Waiting;
        // A new kitchen holds the neediest recipe, so the native ingredient checks and LackOfResources apply to it.
        if(current==null&&_kitchen.ProductionRecipes.Length>0)Switch(Choose(_kitchen.ProductionRecipes.ToList(),null,out _));
        return;
      }
      _batchFinished=false;
      var pick=Choose(cookable,current,out var reason);
      Reason=reason;
      if(pick!=current)Switch(pick);
    }

    // SetRecipe starts the recipe afresh; a set-aside batch then gets back its
    // progress and its consumed ingredients, so native production resumes it.
    private void Switch(RecipeSpec recipe) {
      _kitchen.SetRecipe(recipe);Switches++;
      if(!_setAside.Remove(recipe,out var progress))return;
#if !UNITY_EDITOR
      SetProgress(_kitchen,progress);IngredientsConsumed(_kitchen)=true;UpdateGoodRegistry(_kitchen);
#endif
    }

    internal bool HasIngredients(RecipeSpec recipe) {
      if(_setAside.ContainsKey(recipe))return true;
      var inventory=_restaurant.Inventory;
      foreach(var ingredient in recipe.Ingredients)if(!inventory.HasUnreservedStock(ingredient.ToGoodAmount()))return false;
      if(recipe.ConsumesFuel&&inventory.UnreservedAmountInStock(recipe.Fuel)<=0&&!(recipe==_kitchen.CurrentRecipe&&_kitchen.FuelRemaining>0f))return false;
      return true;
    }

    internal bool Cookable(RecipeSpec recipe) {
      if(!HasIngredients(recipe))return false;
      foreach(var product in recipe.Products)if(!_restaurant.Inventory.HasUnreservedCapacity(product.ToGoodAmount()))return false;
      return true;
    }

    // Lowest product stock relative to its authored capacity.
    internal float Shortness(RecipeSpec recipe)=>recipe.Products.Min(p=>{
      var stock=_restaurant.Spec.Stock.SingleOrDefault(s=>s.GoodId==p.Id)
        ?? throw new InvalidOperationException("Restaurant kitchen product "+p.Id+" has no authored stock capacity");
      return (float)_restaurant.Inventory.AmountInStock(p.Id)/stock.Capacity;
    });

    private RecipeSpec Choose(List<RecipeSpec> cookable,RecipeSpec current,out RestaurantKitchenReason reason) {
      if(cookable.Count==1){reason=RestaurantKitchenReason.OnlyCookable;return cookable[0];}
      var recipes=_kitchen.ProductionRecipes;
      int start=current==null?0:recipes.IndexOf(current)+1;
      // Authored order rotated to start after the current recipe: ties go to the next one.
      var order=cookable.OrderBy(r=>(recipes.IndexOf(r)-start+recipes.Length)%recipes.Length).ToList();
      float best=order.Min(Shortness);
      var tied=order.Where(r=>Shortness(r)-best<1e-6f).ToList();
      reason=tied.Count>1?RestaurantKitchenReason.TakingTurns:RestaurantKitchenReason.LowestStock;
      return tied[0];
    }

    public void Save(IEntitySaver saver) {
      if(_setAside.Count==0)return;
      var data=saver.GetComponent(Key);
      data.Set(SetAsideRecipesKey,_setAside.Keys.Select(r=>r.Id).ToList());
      data.Set(SetAsideProgressKey,_setAside.Values.ToList());
    }
    public void Load(IEntityLoader loader) {
      if(!loader.TryGetComponent(Key,out var data))return;
      var ids=data.Get(SetAsideRecipesKey);var progress=data.Get(SetAsideProgressKey);
      if(ids.Count!=progress.Count)throw new InvalidOperationException("Saved restaurant kitchen batches are malformed");
      for(int i=0;i<ids.Count;i++) {
        var recipe=_kitchen.ProductionRecipes.SingleOrDefault(r=>r.Id==ids[i])
          ?? throw new InvalidOperationException("Saved restaurant kitchen batch has an unknown recipe "+ids[i]);
        if(!(progress[i]>0f&&progress[i]<1f))throw new InvalidOperationException("Saved restaurant kitchen batch progress out of range for "+ids[i]);
        _setAside.Add(recipe,progress[i]);
      }
    }
  }

  [Context("Game")]
  public sealed class RestaurantConfigurator : Configurator {
    protected override void Configure() {
      Bind<Restaurant>().AsTransient();Bind<RestaurantDiner>().AsTransient();Bind<RestaurantSeats>().AsTransient();
      Bind<RestaurantVisitBehavior>().AsTransient();Bind<RestaurantWorkBehavior>().AsTransient();Bind<RestaurantIdleBehavior>().AsTransient();
      Bind<RestaurantServeExecutor>().AsTransient();
      Bind<RestaurantKitchenBehavior>().AsTransient();Bind<RestaurantKitchenChooser>().AsTransient();
      MultiBind<TemplateModule>().ToProvider<ModuleProvider>().AsSingleton();
    }
    private sealed class ModuleProvider : IProvider<TemplateModule> {
      public TemplateModule Get() {
        var b=new TemplateModule.Builder();b.AddDecorator<RestaurantSpec,Restaurant>();
        b.AddDecorator<RestaurantSpec,InventoryGoodConsumptionBlocker>();
        b.AddDecorator<Enterer,RestaurantDiner>();b.AddDecorator<Worker,RestaurantServeExecutor>();b.AddDecorator<Restaurant,RestaurantSeats>();b.AddDecorator<Restaurant,RestaurantVisitBehavior>();
        b.AddDecorator<Restaurant,AutoEmptiable>();b.AddDecorator<Restaurant,Emptiable>();b.AddDecorator<Restaurant,FillInputHaulBehaviorProvider>();
        b.AddDecorator<Restaurant,RestaurantWorkBehavior>();b.AddDecorator<Restaurant,RestaurantKitchenBehavior>();b.AddDecorator<Restaurant,FillInputWorkplaceBehavior>();
        b.AddDecorator<Restaurant,EmptyOutputWorkplaceBehavior>();
        b.AddDecorator<Restaurant,EmptyInventoriesWorkplaceBehavior>();b.AddDecorator<Restaurant,RemoveUnwantedStockWorkplaceBehavior>();
        b.AddDecorator<Restaurant,RestaurantIdleBehavior>();
        // Automatic kitchen: native AutomaticRecipeManufactory hides the recipe picker; the chooser cooks every recipe.
        b.AddDecorator<Restaurant,AutomaticRecipeManufactory>();b.AddDecorator<Restaurant,RestaurantKitchenChooser>();
        return b.Build();
      }
    }
  }
}
