using System;
using System.Collections.Immutable;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BehaviorSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.Common;
using Timberborn.Emptying;
using Timberborn.Goods;
using Timberborn.InventoryNeedSystem;
using Timberborn.InventorySystem;
using Timberborn.MechanicalSystem;
using Timberborn.NeedSpecs;
using Timberborn.RangedEffectSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.TimbermeshAnimations;
using Timberborn.WalkingSystem;
using Timberborn.Workshops;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  internal record GroceryStoreSpec : ComponentSpec {
    [Serialize] public ImmutableArray<string> Foods { get; init; }
    [Serialize] public int CapacityPerFood { get; init; }
    [Serialize] public int MinimumStockedFoodTypes { get; init; }
    [Serialize] public Vector3 ClerkWorkPosition { get; init; }
    [Serialize] public ContinuousEffectSpec NeighborhoodEffect { get; init; }
  }

  // The native inventory owns all stock, reservations, hauling and persistence.
  // Native InventoryNeedBehavior lets shoppers choose and eat actual foods.
  internal sealed class GroceryStore : TickableComponent, IAwakableComponent, IFinishedStateListener {
    private GroceryStoreSpec _spec;
    private Workplace _workplace;
    private BlockableObject _blockable;
    private MechanicalBuilding _power;
    private RangedEffectBuilding _range;
    private IAnimator _sign;
    private bool _areaActive;
    public Inventory Inventory { get; private set; }
    public Vector3 ClerkPosition => Transform.TransformPoint(_spec.ClerkWorkPosition);
    public bool IsOperating => Enabled && _blockable.IsUnblocked && _power.ActiveAndPowered;
    public int StockedFoodTypes => _spec.Foods.Count(id=>Inventory.AmountInStock(id)>0);
    public int AttendingStaff => _workplace.AssignedWorkers.Count(w=>
      w.JobRunning && w.GetComponent<WorkerWorkingHours>().AreWorkingHours
      && w.GetComponent<BehaviorManager>().IsRunningBehavior<GroceryClerkBehavior>()
      && Vector3.Distance(w.Transform.position,ClerkPosition)<.3f);
    public bool ProvidesNeighborhoodService => _areaActive;
    public void InitializeInventory(Inventory inventory) {
      Asserts.FieldIsNull(this,Inventory,nameof(Inventory));Inventory=inventory;
    }
    public void Awake() {
      _spec=GetComponent<GroceryStoreSpec>();_workplace=GetComponent<Workplace>();
      _blockable=GetComponent<BlockableObject>();_power=GetComponent<MechanicalBuilding>();
      _range=GetComponent<RangedEffectBuilding>();
      if(_spec.Foods.Length==0||_spec.Foods.Distinct().Count()!=_spec.Foods.Length
        ||_spec.CapacityPerFood<=0||_spec.MinimumStockedFoodTypes<=0
        ||_spec.MinimumStockedFoodTypes>_spec.Foods.Length)
        throw new InvalidOperationException("Grocery assortment and stocking requirements must be explicitly valid");
      var finished=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      _sign=finished.GetComponentsInChildren<MonoBehaviour>(true).OfType<IAnimator>().Single();
      DisableComponent();
    }
    public void OnEnterFinishedState() {
      Inventory.Enable();EnableComponent();_sign.Enabled=true;_sign.Play("Default");
    }
    public void OnExitFinishedState() {
      SetNeighborhoodService(false);Inventory.Disable();_sign.Stop();DisableComponent();
    }
    public override void Tick() {
      SetNeighborhoodService(IsOperating && AttendingStaff>0 && StockedFoodTypes>=_spec.MinimumStockedFoodTypes);
    }
    private void SetNeighborhoodService(bool active) {
      if(active==_areaActive)return;
      if(active)_range.AddEffect(_spec.NeighborhoodEffect);else _range.RemoveEffect(_spec.NeighborhoodEffect);
      _areaActive=active;
    }
  }

  internal sealed class GroceryInventoryInitializer : IDedicatedDecoratorInitializer<GroceryStore,Inventory> {
    private readonly InventoryInitializerFactory _inventories;
    private readonly InventoryNeedBehaviorInitializer _consumption;
    private readonly IGoodService _goods;
    public GroceryInventoryInitializer(InventoryInitializerFactory inventories,InventoryNeedBehaviorInitializer consumption,IGoodService goods) {
      _inventories=inventories;_consumption=consumption;_goods=goods;
    }
    public void Initialize(GroceryStore subject,Inventory decorator) {
      var spec=subject.GetComponent<GroceryStoreSpec>();
      foreach(var id in spec.Foods)
        if(!_goods.GetGood(id).HasConsumptionEffects)throw new InvalidOperationException("Grocery good is not edible: "+id);
      var init=_inventories.Create(decorator,spec.Foods.Length*spec.CapacityPerFood,"GroceryStore");
      init.AddAllowedGoods(spec.Foods.Select(id=>new StorableGoodAmount(StorableGood.CreateGiveableAndTakeable(id),spec.CapacityPerFood)));
      init.HasPublicInput();init.Initialize();
      subject.InitializeInventory(decorator);_consumption.AddNeedBehavior(decorator);
    }
  }
  internal sealed class GroceryClerkBehavior : WorkplaceBehavior {
    public override Decision Decide(BehaviorAgent agent) {
      var shop=GetComponent<GroceryStore>();
      if(!shop.IsOperating)return Decision.ReleaseNow();
      var walk=agent.GetComponent<WalkToPositionExecutor>();
      switch(walk.Launch(shop.ClerkPosition)) {
        case ExecutorStatus.Running:return Decision.ReleaseWhenFinished(walk);
        case ExecutorStatus.Failure:return Decision.ReleaseNextTick();
        case ExecutorStatus.Success:
          var wait=agent.GetComponent<WaitExecutor>();wait.LaunchForSpecifiedTime(.05f);
          return Decision.ReleaseWhenFinished(wait);
        default:throw new ArgumentOutOfRangeException();
      }
    }
  }
  [Context("Game")]
  public sealed class GroceryStoreConfigurator : Configurator {
    protected override void Configure() {
      Bind<GroceryStore>().AsTransient();Bind<GroceryClerkBehavior>().AsTransient();
      Bind<GroceryInventoryInitializer>().AsSingleton();
      MultiBind<TemplateModule>().ToProvider<ModuleProvider>().AsSingleton();
    }
    private sealed class ModuleProvider : IProvider<TemplateModule> {
      private readonly GroceryInventoryInitializer _initializer;
      public ModuleProvider(GroceryInventoryInitializer initializer) {_initializer=initializer;}
      public TemplateModule Get() {
        var b=new TemplateModule.Builder();
        b.AddDecorator<GroceryStoreSpec,GroceryStore>();
        b.AddDedicatedDecorator(_initializer);
        b.AddDecorator<GroceryStore,InventoryNeedBehavior>();
        // The shop's inventory is a public input, so native DistrictInventoryPicker.InventoryIsTaking
        // reads its IInventoryValidator (Emptiable, as every native public-input building has). Without it
        // any worker emptying a food the shop takes hit a NullReferenceException that stopped the game
        // (all-buildings run b163, EmptyInventoriesLaborBehavior).
        b.AddDecorator<GroceryStore,Emptiable>();
        b.AddDecorator<GroceryStore,FillInputHaulBehaviorProvider>();
        b.AddDecorator<GroceryStore,FillInputWorkplaceBehavior>();
        b.AddDecorator<GroceryStore,GroceryClerkBehavior>();
        return b.Build();
      }
    }
  }
}
