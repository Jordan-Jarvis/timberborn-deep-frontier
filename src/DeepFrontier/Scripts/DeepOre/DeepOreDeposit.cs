using System;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.Goods;
using Timberborn.MapStateSystem;
using Timberborn.Persistence;
using Timberborn.TemplateInstantiation;
using Timberborn.TimeSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.DeepOre {
  // A Deep Ore Source (tools/create_vertical_slice_content.mjs, docs/source-authoring.md): a deposit
  // of one good that Deep Drills in the same district bore out (DeepDrill.cs). It is not an
  // inventory: no hauler, district supply, pipe or storage mod can take from or add to it.
  //
  // Recharge (docs/progression.md "Deep Ore Source recharge"): once empty, the deposit regains
  // RechargeAmount after RechargeTimeInDays and holds no more than that until it is drilled empty
  // again, as a native bush regrows its yield after it is gathered (GatherableYieldGrower). The
  // timer is the native ITimeTrigger, saved as its progress like the bush's; it runs only while the
  // deposit is empty and never in the map editor.
  //
  // A deposit placed new holds Capacity, as the native map editor fills a new fixed stockpile to its
  // MaxCapacity (FixedStockpileInventorySetter); the new-game map setup and the map editor's amount
  // field set the amount (SetAmount).
  internal record DeepOreDepositSpec : ComponentSpec {
    [Serialize] public string GoodId { get; init; }
    [Serialize] public int Capacity { get; init; }
    [Serialize] public int RechargeAmount { get; init; }
    [Serialize] public float RechargeTimeInDays { get; init; }
  }

  internal sealed class DeepOreDeposit : BaseComponent, IAwakableComponent, IInitializableEntity, IDeletableEntity,
      IPersistentEntity, IRegisteredComponent {
    private static readonly ComponentKey Key = new("DeepFrontier.DeepOreDeposit");
    private static readonly PropertyKey<int> AmountKey = new("Amount");
    private static readonly PropertyKey<float> RechargeProgressKey = new("RechargeProgress");
    // Saved before 2026-11-03, when the source was a native fixed stockpile: its stock is the native
    // Inventory "Stockpile" component (Inventory.Save: "Inventory:Stockpile" / "Storage", a
    // GoodRegistry). An emptied stockpile saved nothing (Inventory.Save skips an empty inventory).
    private static readonly ComponentKey LegacyInventoryKey = new("Inventory");
    private const string LegacyInventoryName = "Stockpile";
    private static readonly PropertyKey<GoodRegistry> LegacyStorageKey = new("Storage");

    private readonly ITimeTriggerFactory _timeTriggers;
    private readonly MapEditorMode _mapEditorMode;
    private readonly GoodRegistryValueSerializer _goodRegistrySerializer;
    private DeepOreDepositSpec _spec;
    private ITimeTrigger _recharge;
    private DistrictBuilding _districtBuilding;
    private BuildingAccessible _accessible;

    public DeepOreDeposit(ITimeTriggerFactory timeTriggers, MapEditorMode mapEditorMode, GoodRegistryValueSerializer goodRegistrySerializer) {
      _timeTriggers = timeTriggers; _mapEditorMode = mapEditorMode; _goodRegistrySerializer = goodRegistrySerializer;
    }

    public DeepOreDepositSpec Spec => _spec;
    public int Amount { get; private set; }
    public bool IsRecharging => Amount == 0;
    // 0..1 while recharging (native TimeTrigger.Progress) and the days still to wait.
    public float RechargeProgress => _recharge.Progress;
    public float RechargeDaysLeft => _recharge.DaysLeft;
    // Game only: the native DistrictBuilding (decorates BuildingAccessible) and the building's
    // Accessible, as the native district inventory picker reaches a storage building.
    public DistrictCenter District => _districtBuilding.District;
    public BuildingAccessible Accessible => _accessible;

    public void Awake() {
      _spec = GetComponent<DeepOreDepositSpec>();
      if (string.IsNullOrEmpty(_spec.GoodId) || _spec.Capacity <= 0 || _spec.RechargeAmount <= 0 || _spec.RechargeAmount > _spec.Capacity
          || !(_spec.RechargeTimeInDays > 0f))
        throw new InvalidOperationException($"{Name}: DeepOreDepositSpec needs a good, a positive Capacity, 0 < RechargeAmount <= Capacity and a positive RechargeTimeInDays");
      _districtBuilding = GetComponent<DistrictBuilding>();
      _accessible = GetComponent<BuildingAccessible>();
      if (!_mapEditorMode.IsMapEditor && (!_districtBuilding || !_accessible))
        throw new InvalidOperationException($"{Name}: a Deep Ore deposit needs BuildingAccessible (and its native DistrictBuilding) so drills in its district reach it");
      _recharge = _timeTriggers.Create(Recharge, _spec.RechargeTimeInDays);
      Amount = _spec.Capacity;
    }

    // Resumes a loaded recharge where it was saved (Load fast-forwarded it), as
    // GatherableYieldGrower.InitializeEntity resumes the bush's growth.
    public void InitializeEntity() {
      if (Amount == 0 && !_mapEditorMode.IsMapEditor) _recharge.Resume();
    }

    public void DeleteEntity() {
      _recharge.Pause();
    }

    public void Save(IEntitySaver entitySaver) {
      var saver = entitySaver.GetComponent(Key);
      saver.Set(AmountKey, Amount);
      if (Amount == 0 && _recharge.Progress > 0f) saver.Set(RechargeProgressKey, _recharge.Progress);
    }

    public void Load(IEntityLoader entityLoader) {
      if (entityLoader.TryGetComponent(Key, out var loader)) {
        int amount = loader.Get(AmountKey);
        if (amount < 0 || amount > _spec.Capacity)
          throw new InvalidOperationException($"{Name}: saved deposit amount {amount} is outside 0..{_spec.Capacity}");
        Amount = amount;
        if (loader.Has(RechargeProgressKey)) {
          if (Amount != 0) throw new InvalidOperationException($"{Name}: saved recharge progress on a deposit holding {Amount}");
          // As GatherableYieldGrower.Load: a finished trigger recharges here.
          _recharge.FastForwardProgress(loader.Get(RechargeProgressKey));
        }
        return;
      }
      Amount = LegacyStockpileAmount(entityLoader);
    }

    // Takes units for one drill cycle; false (nothing taken) when the deposit holds fewer.
    public bool TryTake(int units) {
      if (units <= 0) throw new ArgumentOutOfRangeException(nameof(units), units, "a drill takes a positive number of units");
      if (Amount < units) return false;
      Amount -= units;
      if (Amount == 0) StartRecharge();
      return true;
    }

    // New-game map setup (BuiltinMapSetup) and the map editor's amount field.
    public void SetAmount(int amount) {
      if (amount < 0 || amount > _spec.Capacity)
        throw new ArgumentOutOfRangeException(nameof(amount), amount, $"{Name}: a deposit holds 0..{_spec.Capacity}");
      Amount = amount;
      _recharge.Reset();
      if (Amount == 0) StartRecharge();
    }

    private void StartRecharge() {
      _recharge.Reset();
      if (!_mapEditorMode.IsMapEditor) _recharge.Resume();
    }

    // Native TimeTrigger.Finish calls this once the delay has passed.
    private void Recharge() {
      Amount = _spec.RechargeAmount;
      _recharge.Reset();
    }

    private int LegacyStockpileAmount(IEntityLoader entityLoader) {
      if (!entityLoader.TryGetComponent(LegacyInventoryKey, LegacyInventoryName, out var inventory)) return 0;
      var storage = inventory.Get(LegacyStorageKey, _goodRegistrySerializer);
      int amount = 0;
      foreach (var good in storage.Goods) {
        if (good.GoodId == _spec.GoodId) amount = good.Amount;
        else Debug.LogWarning($"[DeepFrontier] {Name}: the saved source stockpile held {good.Amount} {good.GoodId}; a Deep Ore Source holds only {_spec.GoodId}, so it is dropped");
      }
      if (amount > _spec.Capacity)
        throw new InvalidOperationException($"{Name}: the saved source stockpile held {amount} {_spec.GoodId}, more than the deposit's {_spec.Capacity}");
      return amount;
    }
  }

  [Context("Game")]
  [Context("MapEditor")]
  public sealed class DeepOreDepositConfigurator : Configurator {
    protected override void Configure() {
      Bind<DeepOreDeposit>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<DeepOreDepositSpec, DeepOreDeposit>();
      return builder.Build();
    }
  }
}
