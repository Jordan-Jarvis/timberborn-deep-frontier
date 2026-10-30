using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using System.Runtime.CompilerServices;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Common;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.Persistence;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WorkSystem;
using Timberborn.Workshops;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts {
  // Bot maintenance at a heavy-industry workplace (tools/workforce_risks.json
  // botMaintenance, written by tools/bot_upkeep_content.mjs onto every open
  // workplace with bot wear). Every value is authored; nothing has a default.
  internal record FrontierBotMaintenanceSpec : ComponentSpec {
    // In order of preference: a bot due for service takes the first good in stock.
    [Serialize] public ImmutableArray<FrontierBotMaintenanceGoodSpec> Goods { get; init; }
    [Serialize] public int CapacityPerGood { get; init; }
    // Hours of extra wear (inside a wearing workplace) that one dose covers.
    [Serialize] public float ServiceHours { get; init; }
  }

  internal record FrontierBotMaintenanceGoodSpec {
    [Serialize] public string GoodId { get; init; }
    // Multiplies the workplace's BotWearMultiplier while the dose lasts (never below 1x).
    [Serialize] public float WearFactor { get; init; }
  }

  // One inventory (Timberborn 1.1.2.8): native code assumes a building has at
  // most one enabled Inventory (InventoryDebugFragment uses SingleOrDefault;
  // build 145 crashed on "Modify Inventory" with a second one). The
  // maintenance oils are therefore extra allowed goods of the workplace's own
  // native Manufactory inventory (BotMaintenanceInventory.cs patches the
  // native ManufactoryInventoryInitializer and keeps them through Moddable
  // Recipes' rebuilds). ManufactoryExtraStock wraps the native
  // RecipeGoodDisallower: recipe goods keep their native per-recipe limits, and
  // each oil adds CapacityPerGood while at least one bot is assigned. Without
  // bots an oil's limit is frozen at the stock already held, so native fill
  // behaviours deliver none and native unwanted-stock cleanup hauls none out.
  // Native ManufactoryHaulBehaviorProvider and FillInputWorkplaceBehavior fill
  // the inventory's input goods, so haulers and the building's own workers
  // stock the oils. A bot inside whose dose has run out takes one unit
  // (TakeConsumed); BotWear keeps the dose (good, factor, hours left) and saves
  // it with the bot.
  //
  // An oil that is also one of the building's recipe goods shares its native
  // entry: CapacityPerGood is added to it, and it stays givable only if the
  // recipe makes it an input (a product is kept from the building's own output).
  //
  // Saves: builds up to 145 kept the oils in a second inventory, saved as
  // "Inventory" component "DeepFrontier.BotMaintenance" (save version 1). Its
  // stock moves into the production inventory after load, up to each oil's
  // capacity and the inventory's free space; the rest is dropped and logged.
  // Version 2 writes "DeepFrontier.BotMaintenanceStock".
  internal sealed class BotMaintenance : TickableComponent, IAwakableComponent, IFinishedStateListener,
      IPersistentEntity, IPostInitializableEntity {
    internal const string LegacyInventoryName = "DeepFrontier.BotMaintenance";
    private const int SaveVersion = 2;
    private static readonly ComponentKey StockKey = new ComponentKey("DeepFrontier.BotMaintenanceStock");
    private static readonly PropertyKey<int> VersionKey = new PropertyKey<int>("Version");
    private readonly IDayNightCycle _cycle;
    private readonly GoodRegistryValueSerializer _registrySerializer;
    private FrontierBotMaintenanceSpec _spec;
    private Workplace _workplace;
    private ManufactoryExtraStock _stock;
    private GoodRegistry _legacyStock;

    public Inventory Inventory { get; private set; }
    public IndustrialRisk Risk { get; private set; }
    public FrontierBotMaintenanceSpec Spec=>_spec;
    public int AssignedBots { get; private set; }
    public int ServicedBots { get; private set; }

    public BotMaintenance(IDayNightCycle cycle, GoodRegistryValueSerializer registrySerializer) {_cycle=cycle;_registrySerializer=registrySerializer;}

    public void Awake() {
      _spec=GetComponent<FrontierBotMaintenanceSpec>();
      if(_spec.Goods.IsDefaultOrEmpty||_spec.Goods.Select(g=>g.GoodId).Distinct().Count()!=_spec.Goods.Length
         ||_spec.Goods.Any(g=>string.IsNullOrEmpty(g.GoodId)||!(g.WearFactor>0f&&g.WearFactor<1f))
         ||_spec.CapacityPerGood<=0||!(_spec.ServiceHours>0f))
        throw new InvalidOperationException($"{Name}: invalid FrontierBotMaintenanceSpec");
      _workplace=GetComponent<Workplace>();
      Risk=GetComponent<IndustrialRisk>();
      if(!_workplace||!Risk||!GetComponent<Enterable>())
        throw new InvalidOperationException($"{Name}: bot maintenance needs a native Workplace and Enterable with industrial risk");
      if(!(Risk.BotWearMultiplier>1f))
        throw new InvalidOperationException($"{Name}: bot maintenance on a workplace without bot wear");
      var manufactory=GetComponent<Manufactory>();
      if(!manufactory||!manufactory.NeedsInventory)
        throw new InvalidOperationException($"{Name}: bot maintenance keeps its oils in the native Manufactory inventory, which this workplace does not have");
      Inventory=manufactory.Inventory;
      _stock=ManufactoryExtraStock.For(Inventory)
        ?? throw new InvalidOperationException($"{Name}: BotMaintenanceInventory did not add the maintenance oils to the Manufactory inventory");
      DisableComponent();
    }

    public void OnEnterFinishedState() {EnableComponent();}

    public void OnExitFinishedState() {
      _stock.SetBotsPresent(false);
      AssignedBots=ServicedBots=0;
      DisableComponent();
    }

    public void PostInitializeEntity() {
      if(_legacyStock==null)return;
      var moved=new List<string>();var dropped=new List<string>();
      foreach(var good in _legacyStock.Goods) {
        int amount=0;
        if(_spec.Goods.Any(g=>g.GoodId==good.GoodId))
          amount=Math.Max(0,Math.Min(good.Amount,Math.Min(_spec.CapacityPerGood-_stock.ExtraStock(good.GoodId),Inventory.Capacity-Inventory.TotalAmountInStock)));
        if(amount>0) {Inventory.GiveExistingIgnoringCapacity(new GoodAmount(good.GoodId,amount));moved.Add($"{amount} {good.GoodId}");}
        if(amount<good.Amount)dropped.Add($"{good.Amount-amount} {good.GoodId}");
      }
      UnityEngine.Debug.Log($"[DeepFrontier] {Name}: save version 1 maintenance inventory merged into the production inventory; moved [{string.Join(", ",moved)}], dropped (no capacity) [{string.Join(", ",dropped)}]");
      _legacyStock=null;
    }

    public void Save(IEntitySaver entitySaver)=>entitySaver.GetComponent(StockKey).Set(VersionKey,SaveVersion);

    public void Load(IEntityLoader entityLoader) {
      if(entityLoader.TryGetComponent(StockKey,out var stock)) {
        int version=stock.Get(VersionKey);
        if(version!=SaveVersion)UnityEngine.Debug.LogWarning($"[DeepFrontier] {Name}: bot maintenance save version {version} is not {SaveVersion}; its data is ignored");
        return;
      }
      if(entityLoader.TryGetComponent(Inventory.InventoryKey,LegacyInventoryName,out var legacy))
        _legacyStock=legacy.Get(Inventory.StorageKey,_registrySerializer);
    }

    public float ServicedMultiplier(FrontierBotMaintenanceGoodSpec good)=>BotWear.Serviced(Risk.BotWearMultiplier,good.WearFactor);

    public override void Tick() {
      var hours=_cycle.FixedDeltaTimeInHours;
      int bots=0,serviced=0;
      foreach(var worker in _workplace.AssignedWorkers) {
        var wear=worker.GetComponent<BotWear>();
        if(!wear)continue; // beavers
        bots++;
        if(wear.Wearing&&wear.Risk==Risk) {
          wear.ElapseService(hours);
          if(!wear.IsServiced)TryService(wear);
        }
        if(wear.IsServiced)serviced++;
      }
      AssignedBots=bots;ServicedBots=serviced;
      _stock.SetBotsPresent(bots>0);
    }

    private void TryService(BotWear wear) {
      foreach(var good in _spec.Goods) {
        if(Inventory.UnreservedAmountInStock(good.GoodId)<1)continue;
        Inventory.TakeConsumed(new GoodAmount(good.GoodId,1));
        wear.Service(good.GoodId,good.WearFactor,_spec.ServiceHours);
        return;
      }
    }
  }

  // One extra good of a Manufactory inventory: a bot maintenance oil (stocked
  // only while bots are assigned) or a workplace upkeep good (always stocked).
  internal readonly struct ManufactoryExtraGood {
    public readonly string GoodId;
    public readonly int Capacity;
    public readonly bool OnlyWithBots;
    public ManufactoryExtraGood(string goodId,int capacity,bool onlyWithBots) {GoodId=goodId;Capacity=capacity;OnlyWithBots=onlyWithBots;}

    // The extra goods a template's specs add (either may be null). A good may
    // be added once: an oil that is also an upkeep good has no defined limit.
    internal static ImmutableArray<ManufactoryExtraGood> Of(FrontierBotMaintenanceSpec maintenance,FrontierWorkplaceUpkeepSpec upkeep) {
      var goods=ImmutableArray.CreateBuilder<ManufactoryExtraGood>();
      if(maintenance!=null)foreach(var g in maintenance.Goods)goods.Add(new ManufactoryExtraGood(g.GoodId,maintenance.CapacityPerGood,true));
      if(upkeep!=null)foreach(var g in upkeep.Goods)goods.Add(new ManufactoryExtraGood(g.GoodId,upkeep.CapacityPerGood,false));
      var duplicate=goods.GroupBy(g=>g.GoodId).FirstOrDefault(g=>g.Count()>1);
      if(duplicate!=null)throw new InvalidOperationException($"Manufactory extra good {duplicate.Key} is both a bot maintenance oil and a workplace upkeep good, or listed twice");
      return goods.ToImmutable();
    }
  }

  // The Manufactory inventory's good disallower on workplaces with bot
  // maintenance or workplace upkeep: the native RecipeGoodDisallower's limits
  // plus the extra goods.
  internal sealed class ManufactoryExtraStock : IGoodDisallower, IInitializableGoodDisallower {
    private static readonly ConditionalWeakTable<Inventory,ManufactoryExtraStock> Stocks=new ConditionalWeakTable<Inventory,ManufactoryExtraStock>();
    private readonly RecipeGoodDisallower _recipe;
    private readonly ImmutableArray<ManufactoryExtraGood> _goods;
    private Inventory _inventory;
    private bool _botsPresent;

    public event EventHandler<DisallowedGoodsChangedEventArgs> DisallowedGoodsChanged;

    internal ManufactoryExtraStock(RecipeGoodDisallower recipe, ImmutableArray<ManufactoryExtraGood> goods) {
      _recipe=recipe??throw new InvalidOperationException("Workplace with extra Manufactory goods has no native RecipeGoodDisallower");
      _goods=goods;
      _recipe.DisallowedGoodsChanged+=(sender,args)=>DisallowedGoodsChanged?.Invoke(this,args);
    }

    internal static ManufactoryExtraStock For(Inventory inventory)=>Stocks.TryGetValue(inventory,out var stock)?stock:null;

    internal bool Holds(string goodId)=>_goods.Any(g=>g.GoodId==goodId);

    public void Initialize(Inventory inventory) {
      if(_inventory!=null)throw new InvalidOperationException("Manufactory extra stock is already initialized");
      _inventory=inventory;
      Stocks.Add(inventory,this);
    }

    public int AllowedAmount(string goodId) {
      int recipe=_recipe.AllowedAmount(goodId);
      foreach(var good in _goods) {
        if(good.GoodId!=goodId)continue;
        if(!good.OnlyWithBots||_botsPresent)return recipe+good.Capacity;
        // An oil without bots: hold what is in stock, deliver nothing more. A
        // product oil keeps its native recipe limit, so surplus output still
        // leaves natively.
        return _inventory.Takes(goodId)?Math.Max(recipe,_inventory.AmountInStock(goodId)):recipe;
      }
      return recipe;
    }

    // Extra good held beyond the current recipe's own allowance.
    internal int ExtraStock(string goodId)=>Math.Max(0,_inventory.AmountInStock(goodId)-_recipe.AllowedAmount(goodId));

    internal void SetBotsPresent(bool present) {
      if(present==_botsPresent)return;
      _botsPresent=present;
      foreach(var good in _goods)if(good.OnlyWithBots)DisallowedGoodsChanged?.Invoke(this,new DisallowedGoodsChangedEventArgs(good.GoodId));
    }
  }

  // Own configurator, so the workforce configurator stays untouched.
  [Context("Game")]
  public sealed class BotUpkeepConfigurator : Configurator {
    protected override void Configure() {
      Bind<BotMaintenance>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder=new TemplateModule.Builder();
      builder.AddDecorator<FrontierBotMaintenanceSpec,BotMaintenance>();
      return builder.Build();
    }
  }
}
