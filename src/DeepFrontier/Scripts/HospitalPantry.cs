using System;
using System.Collections.Generic;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlueprintSystem;
using Timberborn.BlockSystem;
using Timberborn.Effects;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.Goods;
using Timberborn.InventoryNeedSystem;
using Timberborn.InventorySystem;
using Timberborn.Localization;
using Timberborn.NeedBehaviorSystem;
using Timberborn.NeedSystem;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.StatusSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts {
  // Authored by tools/hospital_building_content.mjs.
  internal record HospitalPantrySpec : ComponentSpec {
    [Serialize] public int FoodCapacityPerGood { get; init; }
    [Serialize] public string WaterGoodId { get; init; }
    [Serialize] public int WaterCapacity { get; init; }
    [Serialize] public int LowStockUnits { get; init; }
  }

  internal static class HospitalPantryLoc {
    public const string Low = "DeepFrontier.Hospital.Status.MealsLow";
    public const string LowShort = "DeepFrontier.Hospital.Status.MealsLow.Short";
    public const string Out = "DeepFrontier.Hospital.Status.MealsOut";
    public const string OutShort = "DeepFrontier.Hospital.Status.MealsOut.Short";
    // Vanilla 1.1.2.8 status sprite of native LackOfResourcesStatus.
    public const string Sprite = "LackOfResources";
  }

  // Patient meals (Timberborn 1.1.2.8). Every Hospital effect has
  // SatisfyToMaxValue, so native AttractionNeedBehavior returns to the stay
  // (Decision.ReturnWhenFinished) until all four conditions are at their
  // maximum: BehaviorManager re-runs only that behaviour, so admitted patients
  // cannot leave for food or water.
  //
  // One inventory: native code assumes a building has at most one enabled
  // Inventory (InventoryDebugFragment uses SingleOrDefault; build 145 crashed
  // on "Modify Inventory" with a second, pantry inventory). The patient foods
  // and water are therefore extra allowed goods, with capacities, of the
  // Hospital's own native GoodConsumingBuilding inventory
  // (HospitalPantryInventory.cs). GoodConsumingBuilding consumes only its
  // ConsumedGoods from it; the foods and the extra water are givable only, so
  // native FillInputWorkplaceBehavior and FillInputHaulBehaviorProvider deliver
  // them and no other beaver can eat from it. Water is shared with the ward's
  // water supply (one good, one stock).
  //
  // Each tick, an admitted patient with room for a whole portion is fed the
  // stocked good native InventoryNeedBehavior.FindMostOptimalGood would pick:
  // the highest Appraiser.AppraiseEffects over the good's native
  // ConsumptionEffects (0 when a non-wastable need cannot take it whole). The
  // same effects are applied and GoodConsumedEvent is posted, as native
  // ConsumeGood does. Foods are every faction good native InventoryNeedBehavior
  // can carry (GoodType Box) with a positive Hunger effect, chosen at runtime
  // from the native IGoodService, so food variety and wellbeing stay native.
  // Zombies lose Hunger and Thirst twice as fast and so eat and drink twice as
  // much. With no food or no water left the Hospital stops admitting
  // (Hospital.CanUse) and native AttractionNeedBehavior releases its patients
  // to eat and drink; they are readmitted by native critical-need priority.
  //
  // Saves: builds up to 145 stored the pantry as a second inventory, saved as
  // "Inventory" component "HospitalPantry" (save version 1). Its stock moves
  // into the native inventory after load, up to free capacity; the rest is
  // dropped and logged. Version 2 writes "DeepFrontier.HospitalPantry".
  //
  // Admission never waits for meals: an empty pantry only closes the ward
  // (MealsShort) once an admitted patient's Hunger or Thirst is in its native
  // critical state with none of that left, so a newly built Hospital admits
  // before its first delivery. Build 146 regressed here: this class lost
  // IFinishedStateListener, stayed disabled, and CanFeed (then required for
  // admission) was never true.
  internal sealed class HospitalPantry : TickableComponent, IAwakableComponent, IInitializableEntity, IPostInitializableEntity,
      IPersistentEntity, IFinishedStateListener {
    internal const string LegacyInventoryName = "HospitalPantry";
    private const int SaveVersion = 2;
    private static readonly ComponentKey PantryKey = new ComponentKey("DeepFrontier.HospitalPantry");
    private static readonly PropertyKey<int> VersionKey = new PropertyKey<int>("Version");
    private const string HungerNeedId = "Hunger", ThirstNeedId = "Thirst";
    private readonly IGoodService _goods;
    private readonly EventBus _events;
    private readonly ILoc _loc;
    private readonly GoodRegistryValueSerializer _registrySerializer;
    private readonly Dictionary<string, List<InstantEffect>> _effects = new Dictionary<string, List<InstantEffect>>();
    private readonly List<string> _foods = new List<string>();
    private readonly List<Enterer> _patients = new List<Enterer>();
    private HospitalPantrySpec _spec;
    private GoodConsumingBuilding _supplies;
    private Enterable _ward;
    private StatusToggle _lowStatus, _outStatus;
    private GoodRegistry _legacyStock;
    private float _foodPortion, _waterPortion;

    public Inventory Inventory => _supplies.Inventory;
    public IReadOnlyList<string> Foods => _foods;
    public string WaterGoodId => _spec.WaterGoodId;
    public int FoodInStock => _foods.Sum(id => Inventory.UnreservedAmountInStock(id));
    public int WaterInStock => Inventory.UnreservedAmountInStock(_spec.WaterGoodId);
    public bool CanFeed => Enabled && FoodInStock > 0 && WaterInStock > 0;
    // An admitted patient is starving or dehydrated and the pantry has none of what it needs.
    public bool MealsShort { get; private set; }
    public bool StockLow => FoodInStock < _spec.LowStockUnits || WaterInStock < _spec.LowStockUnits;
    public int Patients { get; private set; }
    public int PatientsFed { get; private set; }

    public HospitalPantry(IGoodService goods, EventBus events, ILoc loc, GoodRegistryValueSerializer registrySerializer) {
      _goods = goods; _events = events; _loc = loc; _registrySerializer = registrySerializer;
    }

    internal static List<string> SelectFoods(IGoodService goods) {
      var foods = goods.Goods.Where(id => {
        var good = goods.GetGood(id);
        return good.GoodType == "Box" && good.ConsumptionEffects.Any(e => e.NeedId == HungerNeedId && e.Points > 0);
      }).OrderBy(id => id, StringComparer.Ordinal).ToList();
      if (foods.Count == 0) throw new InvalidOperationException("Hospital pantry: the faction has no carried food with a Hunger effect");
      return foods;
    }

    // The native GoodConsumingBuilding inventory goods plus the patient foods
    // and water (HospitalPantryInventory patches the native initializer).
    internal static List<StorableGoodAmount> InventoryGoods(GoodConsumingBuildingSpec supplies, HospitalPantrySpec pantry, IGoodService goods) {
      var amounts = new List<(string id, int amount)>();
      foreach (var consumed in supplies.ConsumedGoods)
        amounts.Add((consumed.GoodId, UnityEngine.Mathf.CeilToInt(consumed.GoodPerHour * supplies.FullInventoryWorkHours)));
      foreach (var food in SelectFoods(goods)) {
        if (amounts.Any(a => a.id == food)) throw new InvalidOperationException($"Hospital supply {food} is also a patient food");
        amounts.Add((food, pantry.FoodCapacityPerGood));
      }
      int water = amounts.FindIndex(a => a.id == pantry.WaterGoodId);
      if (water >= 0) amounts[water] = (pantry.WaterGoodId, amounts[water].amount + pantry.WaterCapacity);
      else amounts.Add((pantry.WaterGoodId, pantry.WaterCapacity));
      return amounts.Select(a => new StorableGoodAmount(StorableGood.CreateAsGivable(a.id), a.amount)).ToList();
    }

    public void Awake() {
      _spec = GetComponent<HospitalPantrySpec>();
      _ward = GetComponent<Enterable>();
      _supplies = GetComponent<GoodConsumingBuilding>();
      if (_ward == null || _supplies == null) throw new InvalidOperationException("Hospital pantry requires the native patient Enterable and GoodConsumingBuilding");
      if (_spec.FoodCapacityPerGood <= 0 || _spec.WaterCapacity <= 0 || _spec.LowStockUnits <= 0)
        throw new InvalidOperationException("Hospital pantry capacities and low-stock threshold must be positive");
      var water = _goods.GetGood(_spec.WaterGoodId);
      if (!water.ConsumptionEffects.Any(e => e.NeedId == ThirstNeedId && e.Points > 0) || water.ConsumptionEffects.Any(e => e.NeedId == HungerNeedId))
        throw new InvalidOperationException($"Hospital pantry water '{_spec.WaterGoodId}' must quench Thirst and not Hunger");
      _lowStatus = StatusToggle.CreateNormalStatusWithFloatingIcon(HospitalPantryLoc.Sprite, _loc.T(HospitalPantryLoc.Low));
      _outStatus = StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon(HospitalPantryLoc.Sprite, _loc.T(HospitalPantryLoc.Out), _loc.T(HospitalPantryLoc.OutShort));
      DisableComponent();
    }

    public void InitializeEntity() {
      _foods.AddRange(SelectFoods(_goods));
      foreach (var id in _foods.Append(_spec.WaterGoodId)) {
        if (!Inventory.Takes(id))
          throw new InvalidOperationException($"Hospital inventory does not take patient good {id}: HospitalPantryInventory did not initialize it");
        _effects[id] = _goods.GetGood(id).ConsumptionEffects.Select(e => InstantEffect.FromSpec(e, 1)).ToList();
      }
      _foodPortion = _foods.Min(id => _goods.GetGood(id).ConsumptionEffects.Where(e => e.NeedId == HungerNeedId).Max(e => e.Points));
      _waterPortion = _goods.GetGood(_spec.WaterGoodId).ConsumptionEffects.Where(e => e.NeedId == ThirstNeedId).Max(e => e.Points);
      var subject = GetComponent<StatusSubject>();
      subject.RegisterStatus(_lowStatus);
      subject.RegisterStatus(_outStatus);
    }

    public void PostInitializeEntity() {
      if (_legacyStock == null) return;
      var moved = new List<string>();
      var dropped = new List<string>();
      foreach (var good in _legacyStock.Goods) {
        int amount = Inventory.Takes(good.GoodId) ? Math.Min(good.Amount, Inventory.UnreservedCapacity(good.GoodId)) : 0;
        if (amount > 0) { Inventory.GiveExisting(new GoodAmount(good.GoodId, amount)); moved.Add($"{amount} {good.GoodId}"); }
        if (amount < good.Amount) dropped.Add($"{good.Amount - amount} {good.GoodId}");
      }
      UnityEngine.Debug.Log($"[DeepFrontier] Hospital {GetComponent<EntityComponent>().EntityId}: save version 1 pantry inventory merged into the native inventory; moved [{string.Join(", ", moved)}], dropped (no capacity) [{string.Join(", ", dropped)}]");
      _legacyStock = null;
    }

    public void Save(IEntitySaver entitySaver) => entitySaver.GetComponent(PantryKey).Set(VersionKey, SaveVersion);

    public void Load(IEntityLoader entityLoader) {
      if (entityLoader.TryGetComponent(PantryKey, out var pantry)) {
        int version = pantry.Get(VersionKey);
        if (version != SaveVersion) UnityEngine.Debug.LogWarning($"[DeepFrontier] Hospital pantry save version {version} is not {SaveVersion}; its data is ignored");
        return;
      }
      if (entityLoader.TryGetComponent(Inventory.InventoryKey, LegacyInventoryName, out var legacy))
        _legacyStock = legacy.Get(Inventory.StorageKey, _registrySerializer);
    }

    // The native GoodConsumingBuilding enables and disables the shared inventory.
    public void OnEnterFinishedState() => EnableComponent();

    public void OnExitFinishedState() {
      DisableComponent();
      MealsShort = false;
      _lowStatus.Deactivate(); _outStatus.Deactivate();
    }

    public override void Tick() {
      int fed = 0;
      bool mealsShort = false;
      // Copied first: applying need effects must not touch the live ward collection.
      _patients.Clear();
      _patients.AddRange(_ward.EnterersInside);
      foreach (var enterer in _patients) {
        var needs = enterer.GetComponent<NeedManager>();
        var appraiser = enterer.GetComponent<Appraiser>();
        if (needs == null || appraiser == null) throw new InvalidOperationException("Hospital patient lacks the native NeedManager/Appraiser");
        if (needs.NeedPointsToMax(HungerNeedId) >= _foodPortion) Feed(needs, appraiser, _foods);
        if (needs.NeedPointsToMax(ThirstNeedId) >= _waterPortion) Feed(needs, appraiser, new[] { _spec.WaterGoodId });
        if (needs.NeedIsFavorable(HungerNeedId) && needs.NeedIsFavorable(ThirstNeedId)) fed++;
        if ((needs.NeedIsInCriticalState(HungerNeedId) && FoodInStock == 0) || (needs.NeedIsInCriticalState(ThirstNeedId) && WaterInStock == 0)) mealsShort = true;
      }
      Patients = _patients.Count;
      _patients.Clear();
      PatientsFed = fed;
      MealsShort = mealsShort;
      bool empty = FoodInStock == 0 || WaterInStock == 0;
      _outStatus.Toggle(empty);
      _lowStatus.Toggle(!empty && StockLow);
    }

    private void Feed(NeedManager needs, Appraiser appraiser, IEnumerable<string> candidates) {
      string best = null;
      float bestPoints = 0f;
      foreach (var id in candidates) {
        if (Inventory.UnreservedAmountInStock(id) <= 0) continue;
        float points = appraiser.AppraiseEffects(_effects[id]);
        if (points > bestPoints) { bestPoints = points; best = id; }
      }
      if (best == null) return;
      Inventory.TakeConsumed(new GoodAmount(best, 1));
      foreach (var effect in _effects[best]) needs.ApplyEffect(effect);
      _events.Post(new GoodConsumedEvent(best));
    }
  }

  [Context("Game")]
  public sealed class HospitalPantryConfigurator : Configurator {
    protected override void Configure() {
      Bind<HospitalPantry>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<HospitalPantrySpec, HospitalPantry>();
      return builder.Build();
    }
  }
}
