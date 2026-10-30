using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.Localization;
using Timberborn.Persistence;
using Timberborn.StatusSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.WorkSystem;
using Timberborn.Workshops;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts {
  // Workplace upkeep (tools/workforce_risks.json workplaceUpkeep, written by
  // tools/bot_upkeep_content.mjs): goods a manufactory wears out while it
  // produces, such as the Deep Drill's and Deep Mine's drill bits. Every value
  // is authored; nothing has a default.
  internal record FrontierWorkplaceUpkeepSpec : ComponentSpec {
    [Serialize] public ImmutableArray<FrontierUpkeepGoodSpec> Goods { get; init; }
    // Stock kept of each good, on top of the recipe goods.
    [Serialize] public int CapacityPerGood { get; init; }
  }

  internal record FrontierUpkeepGoodSpec {
    [Serialize] public string GoodId { get; init; }
    // Units per hour of full-crew production (Workplace.MaxWorkers working at full efficiency).
    [Serialize] public float GoodPerHour { get; init; }
    // What the good is used as. Texts: DeepFrontier.WorkplaceUpkeep.<Role>.Name, .Status and .Status.Short.
    [Serialize] public string Role { get; init; }
  }

  internal static class WorkplaceUpkeepLoc {
    public const string Prefix = "DeepFrontier.WorkplaceUpkeep.";
    public static string Name(string role) => Prefix + role + ".Name";
    public static string Status(string role) => Prefix + role + ".Status";
    public static string StatusShort(string role) => Prefix + role + ".Status.Short";
  }

  // Use follows native recipe progress (Manufactory.ProductionProgressed): a
  // progress change p is p x CycleDurationInHours worker-hours at full
  // efficiency, so p x CycleDurationInHours / MaxWorkers full-crew hours. A
  // partial crew or low power uses proportionally less, an idle or paused
  // building none. Goods are whole units: one unit is taken from the
  // inventory (TakeConsumed) when the one in use is worn through, and the part
  // of it still left is saved.
  //
  // As a native IManufactoryLimiter (Manufactory collects them in Awake):
  // ProductionEfficiency is 0 while a good has nothing left in use and none in
  // stock, so Manufactory.IsReadyToProduce is false and the workers stop; and
  // MaxProductionProgressChange keeps progress within the unit in use when no
  // spare unit is in stock. While production is held up a status per missing
  // good shows ("Waiting for drill bits").
  //
  // The goods are extra allowed goods of the native Manufactory inventory
  // (ManufactoryExtraStock, BotMaintenanceInventory.cs): one enabled inventory
  // per building. Haulers and the building's own workers stock them through
  // the native fill behaviours, as the bot maintenance oils.
  internal sealed class WorkplaceUpkeep : TickableComponent, IAwakableComponent, IInitializableEntity, IFinishedStateListener,
      IPersistentEntity, IManufactoryLimiter {
    private static readonly ComponentKey Key = new("DeepFrontier.WorkplaceUpkeep");
    private static readonly ListKey<string> GoodsKey = new("Goods");
    private static readonly ListKey<float> RemainingKey = new("Remaining");
    // Float residue of a worn-through unit.
    private const float Worn = 1e-5f;
    private readonly ILoc _loc;
    private FrontierWorkplaceUpkeepSpec _spec;
    private Workplace _workplace;
    private Manufactory _manufactory;
    private BlockableObject _blockable;
    private BlockObject _blockObject;
    private float[] _remaining;
    private StatusToggle[] _statuses;
    private bool _finished;

    public WorkplaceUpkeep(ILoc loc) {_loc=loc;}

    public FrontierWorkplaceUpkeepSpec Spec=>_spec;
    public Inventory Inventory=>_manufactory.Inventory;
    // Part of the unit in use still left, 0..1.
    public float Remaining(int index)=>_remaining[index];
    public bool IsSupplied(int index)=>_remaining[index]>Worn||Inventory.UnreservedAmountInStock(_spec.Goods[index].GoodId)>=1;
    public bool IsSupplied() {
      for(int i=0;i<_remaining.Length;i++)if(!IsSupplied(i))return false;
      return true;
    }
    // Full-crew hours the stock (units in stock plus the part in use) lasts.
    public float HoursInStock(int index)=>(Inventory.AmountInStock(_spec.Goods[index].GoodId)+_remaining[index])/_spec.Goods[index].GoodPerHour;

    public void Awake() {
      _spec=GetComponent<FrontierWorkplaceUpkeepSpec>();
      if(_spec.Goods.IsDefaultOrEmpty||_spec.Goods.Select(g=>g.GoodId).Distinct().Count()!=_spec.Goods.Length
         ||_spec.Goods.Any(g=>string.IsNullOrEmpty(g.GoodId)||!(g.GoodPerHour>0f)||string.IsNullOrEmpty(g.Role))||_spec.CapacityPerGood<=0)
        throw new InvalidOperationException($"{Name}: invalid FrontierWorkplaceUpkeepSpec");
      _workplace=GetComponent<Workplace>();
      _manufactory=GetComponent<Manufactory>();
      _blockable=GetComponent<BlockableObject>();
      _blockObject=GetComponent<BlockObject>();
      if(!_workplace||!_manufactory||!_blockable||!_blockObject||!_manufactory.NeedsInventory||_workplace.MaxWorkers<1)
        throw new InvalidOperationException($"{Name}: workplace upkeep needs a native Workplace, BlockableObject and Manufactory with an inventory");
      var stock=ManufactoryExtraStock.For(_manufactory.Inventory)
        ?? throw new InvalidOperationException($"{Name}: BotMaintenanceInventory did not add the upkeep goods to the Manufactory inventory");
      foreach(var good in _spec.Goods)
        if(!stock.Holds(good.GoodId))throw new InvalidOperationException($"{Name}: upkeep good {good.GoodId} is not in the Manufactory inventory");
      _remaining=new float[_spec.Goods.Length];
      DisableComponent();
    }

    public void InitializeEntity() {
      _manufactory.ProductionProgressed+=OnProductionProgressed;
      if(_blockObject.IsPreview)return;
      _statuses=_spec.Goods.Select(g=>StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon("LackOfResources",
        _loc.T(WorkplaceUpkeepLoc.Status(g.Role)),_loc.T(WorkplaceUpkeepLoc.StatusShort(g.Role)))).ToArray();
      var subject=GetComponent<StatusSubject>();
      foreach(var status in _statuses)subject.RegisterStatus(status);
    }

    public void OnEnterFinishedState() {_finished=true;EnableComponent();Tick();}

    public void OnExitFinishedState() {
      _finished=false;
      if(_statuses!=null)foreach(var status in _statuses)status.Deactivate();
      DisableComponent();
    }

    public void Save(IEntitySaver entitySaver) {
      var saver=entitySaver.GetComponent(Key);
      saver.Set(GoodsKey,_spec.Goods.Select(g=>g.GoodId).ToList());
      saver.Set(RemainingKey,_remaining.ToList());
    }

    // A building saved before it had upkeep has no part unit in use.
    public void Load(IEntityLoader entityLoader) {
      if(!entityLoader.TryGetComponent(Key,out var loader))return;
      var goods=loader.Get(GoodsKey);var remaining=loader.Get(RemainingKey);
      if(goods.Count!=remaining.Count)throw new InvalidOperationException($"{Name}: saved workplace upkeep has {goods.Count} goods and {remaining.Count} amounts");
      var ids=_spec.Goods.Select(g=>g.GoodId).ToList();
      for(int i=0;i<goods.Count;i++) {
        int index=ids.IndexOf(goods[i]);
        if(index<0){UnityEngine.Debug.LogWarning($"[DeepFrontier] {Name}: saved upkeep good {goods[i]} is no longer used here; its part unit ({remaining[i]:0.###}) is dropped");continue;}
        if(!(remaining[i]>=0f&&remaining[i]<=1f))throw new InvalidOperationException($"{Name}: saved upkeep {goods[i]} remaining {remaining[i]} is outside 0..1");
        _remaining[index]=remaining[i];
      }
    }

    public override void Tick() {
      bool waiting=_finished&&_blockable.IsUnblocked&&_manufactory.HasCurrentRecipe;
      for(int i=0;i<_statuses.Length;i++) {
        if(waiting&&!IsSupplied(i))_statuses[i].Activate();
        else _statuses[i].Deactivate();
      }
    }

    public float ProductionEfficiency()=>IsSupplied()?1f:0f;

    public float MaxProductionProgressChange(float expectedProductionProgressChange) {
      float max=expectedProductionProgressChange;
      for(int i=0;i<_remaining.Length;i++) {
        if(Inventory.UnreservedAmountInStock(_spec.Goods[i].GoodId)>=1)continue;
        max=Math.Min(max,_remaining[i]/UnitsPerProgress(i));
      }
      return max;
    }

    private float UnitsPerProgress(int index)=>_spec.Goods[index].GoodPerHour*_manufactory.CurrentRecipe.CycleDurationInHours/_workplace.MaxWorkers;

    private void OnProductionProgressed(object sender,ProductionProgressedEventArgs e) {
      if(!(e.ProductionProgressChange>0f))return;
      for(int i=0;i<_remaining.Length;i++)Use(i,e.ProductionProgressChange*UnitsPerProgress(i));
    }

    // MaxProductionProgressChange keeps the use within the stock, up to float residue.
    private void Use(int index,float units) {
      while(units>Worn) {
        if(_remaining[index]<=Worn) {
          var good=_spec.Goods[index].GoodId;
          if(Inventory.UnreservedAmountInStock(good)<1)break;
          Inventory.TakeConsumed(new GoodAmount(good,1));
          _remaining[index]+=1f;
        }
        float used=Math.Min(units,_remaining[index]);
        _remaining[index]-=used;units-=used;
      }
    }
  }

  [Context("Game")]
  public sealed class WorkplaceUpkeepConfigurator : Configurator {
    protected override void Configure() {
      Bind<WorkplaceUpkeep>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder=new TemplateModule.Builder();
      builder.AddDecorator<FrontierWorkplaceUpkeepSpec,WorkplaceUpkeep>();
      return builder.Build();
    }
  }
}
