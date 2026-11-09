using System;
using Timberborn.BaseComponentSystem;
using Timberborn.BlueprintSystem;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.MapStateSystem;
using Timberborn.Persistence;
using Timberborn.TimeSystem;
using Timberborn.WorldPersistence;
using Timberborn.Yielding;

namespace DeepFrontier.Scripts {
  // The native Yielder owns quantities, reservations, extraction time and saving.
  internal record MineralDepositSpec : ComponentSpec, IYielderDecorable, IOrderableYielder {
    [Serialize] public YielderSpec Yielder { get; init; }
    [Serialize] public int RechargeAmount { get; init; }
    [Serialize] public float RechargeTimeInDays { get; init; }
    public string GoodId => Yielder.Yield.Id;
    public int Capacity => Yielder.Yield.Amount;
    public bool PersistYield => true;
    public int Order => 0;
  }

  internal sealed class MineralDeposit : BaseComponent, IAwakableComponent, IInitializableEntity, IDeletableEntity, IPersistentEntity {
    private static readonly ComponentKey Key = new("DeepFrontier.MineralDeposit");
    private static readonly ComponentKey OldOreKey = new("DeepFrontier.DeepOreDeposit");
    private static readonly PropertyKey<int> AmountKey = new("Amount");
    private static readonly PropertyKey<float> ProgressKey = new("RechargeProgress");
    private readonly ITimeTriggerFactory _triggers;
    private readonly MapEditorMode _editor;
    private readonly GoodRegistryValueSerializer _registrySerializer;
    private readonly IGoodService _goods;
    private ITimeTrigger _recharge;
    private int? _migratedAmount;
    private float? _savedProgress;
    private bool _settingYield;
    public Yielder Yielder { get; private set; }
    public MineralDepositSpec Spec { get; private set; }
    // Native YielderInitializer starts a yielder whose good is not loaded at 0
    // (these minerals are Iron Teeth goods, DeepFrontierFaction: another
    // faction's GoodService lacks them). Such a deposit has no stock to set,
    // take or recover.
    public bool GoodLoaded { get; private set; }
    public int Amount => Yielder.Yield.Amount;
    public bool IsRecharging => Amount == 0;
    public float RechargeProgress => _recharge.Progress;
    public float RechargeDaysLeft => _recharge.DaysLeft;

    public MineralDeposit(ITimeTriggerFactory triggers, MapEditorMode editor, GoodRegistryValueSerializer registrySerializer, IGoodService goods) {
      _triggers = triggers; _editor = editor; _registrySerializer = registrySerializer; _goods = goods;
    }

    public void Awake() {
      Yielder = GetComponent<Yielder>();
      Spec = GetComponent<MineralDepositSpec>();
      if (Spec.Capacity <= 0 || Spec.RechargeAmount <= 0 || Spec.RechargeAmount > Spec.Capacity || !(Spec.RechargeTimeInDays > 0))
        throw new InvalidOperationException($"{Name}: invalid mineral capacity or recovery rule");
      _recharge = _triggers.Create(Recharge, Spec.RechargeTimeInDays);
      GoodLoaded = _goods.HasGood(Spec.GoodId);
    }

    public void InitializeEntity() {
      Yielder.Enable();
      if (!GoodLoaded) return;
      // All native components have loaded before InitializeEntity: migrate only
      // the old district-pool/stockpile save formats, never overwrite native yield.
      if (_migratedAmount.HasValue) SetAmount(_migratedAmount.Value);
      Yielder.YieldDecreased += OnYieldDecreased;
      if (_savedProgress.HasValue) {
        if (Amount != 0) throw new InvalidOperationException($"{Name}: recovery progress on a nonempty deposit");
        // A migrated empty deposit's SetAmount(0) has already resumed the clock;
        // native FastForwardProgress resumes a running trigger after it finishes,
        // which would start a second recovery on the refilled deposit.
        _recharge.Pause();
        _recharge.FastForwardProgress(_savedProgress.Value);
      }
      if (IsRecharging && !_editor.IsMapEditor) _recharge.Resume();
    }

    private void OnYieldDecreased(object sender, System.EventArgs args) {
      if (!_settingYield && Yielder.IsYieldRemoved) StartRecharge();
    }

    public void SetAmount(int amount) {
      if (!GoodLoaded) throw new InvalidOperationException($"{Name}: {Spec.GoodId} is not a good of this settlement (Iron Teeth content)");
      if (amount < 0 || amount > Spec.Capacity) throw new ArgumentOutOfRangeException(nameof(amount));
      _recharge.Reset();
      _settingYield = true;
      try {
        Yielder.ResetYield();
        if (amount != Spec.Capacity) Yielder.DecreaseYield(new GoodAmount(Spec.GoodId, Spec.Capacity - amount));
      } finally { _settingYield = false; }
      if (amount == 0) StartRecharge();
    }

    private void StartRecharge() { _recharge.Reset(); if (!_editor.IsMapEditor) _recharge.Resume(); }
    private void Recharge() => SetAmount(Spec.RechargeAmount);
    public void DeleteEntity() { Yielder.YieldDecreased -= OnYieldDecreased; _recharge.Pause(); }
    public void Save(IEntitySaver saver) {
      // Native Yielder saves the stock; only the recovery clock belongs here.
      var component = saver.GetComponent(Key);
      if (IsRecharging) component.Set(ProgressKey, _recharge.Progress);
    }
    public void Load(IEntityLoader loader) {
      if (loader.TryGetComponent(Key, out var current)) {
        if (current.Has(ProgressKey)) _savedProgress = current.Get(ProgressKey);
        return;
      }
      if (Spec.GoodId != "RawDeepOre") return;
      if (loader.TryGetComponent(OldOreKey, out var old)) {
        _migratedAmount = old.Get(AmountKey);
        if (old.Has(ProgressKey)) _savedProgress = old.Get(ProgressKey);
      } else if (!loader.TryGetComponent(new ComponentKey("Yielder"), Spec.Yielder.YielderComponentName, out _)) {
        // Before 0.8.6, DeepOreSource was a fixed stockpile. Empty native
        // inventories omit Storage; that format explicitly means zero ore.
        _migratedAmount = 0;
        if (loader.TryGetComponent(new ComponentKey("Inventory"), "Stockpile", out var inventory)) {
          var storage = new PropertyKey<GoodRegistry>("Storage");
          if (inventory.Has(storage)) {
            foreach (var good in inventory.Get(storage, _registrySerializer).Goods) {
              if (good.GoodId != "DeepOre") throw new InvalidOperationException($"{Name}: unexpected legacy source good {good.GoodId}");
              _migratedAmount = good.Amount;
            }
          }
        }
      }
    }
  }

  internal record MineralPitSpec : ComponentSpec {
    [Serialize] public string GoodId { get; init; }
  }

  internal sealed class MineralYielderRetriever : BaseComponent, IYielderRetriever {
    public bool TryGetYielder(BaseComponent component, out Yielder yielder) {
      var deposit = component.GetComponent<MineralDeposit>();
      if (deposit != null && deposit.Yielder.YielderSpec.Yield.Id == GetComponent<MineralPitSpec>().GoodId) {
        yielder = deposit.Yielder;
        return true;
      }
      yielder = null;
      return false;
    }
  }
}
