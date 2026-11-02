using System.Collections.Generic;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BehaviorSystem;
using Timberborn.Carrying;
using Timberborn.Hauling;
using Timberborn.InventorySystem;
using Timberborn.StockpilePrioritySystem;
using Timberborn.WorkSystem;

namespace DeepFrontier.Scripts.ModularStorage {
  // Haulers at a hauling post serve the Obtain and Supply slots the way they
  // serve a native stockpile's GoodObtainer and GoodSupplier (decompiled
  // 1.1.2.8 Timberborn.StockpilePrioritySystem): the provider offers the
  // behavior while the warehouse is finished and unblocked, weighted by fill
  // (Obtain 1 - fill of its emptiest slot, Supply the fill of its fullest), and
  // the behavior reserves one carry through the native CarrierInventoryFinder.
  // As the native filters never take from an obtaining stockpile nor give to a
  // supplying one, these skip native GoodObtainer/GoodSupplier stockpiles in
  // that mode and any Modular Warehouse slot of the same good in that mode, and
  // never this warehouse's own inventory.
  internal sealed class ModularWarehouseObtainBehavior : WorkplaceBehavior, IAwakableComponent {
    private ModularWarehouse _warehouse;
    public void Awake() { _warehouse = GetComponent<ModularWarehouse>(); }

    public override Decision Decide(BehaviorAgent agent) {
      if (!_warehouse.Operating) return Decision.ReleaseNow();
      var finder = agent.GetComponent<CarrierInventoryFinder>();
      var own = _warehouse.Inventory;
      foreach (int slot in _warehouse.SlotsIn(WarehouseSlotMode.Obtain).ToList()) {
        var good = _warehouse.GoodIn(slot);
        if (own.UnreservedCapacity(good) <= 0) continue;
        if (finder.TryCarryFromAnyInventory(good, own, source => CanObtainFrom(source, good, own))) return Decision.ReleaseNextTick();
      }
      return Decision.ReleaseNow();
    }

    private static bool CanObtainFrom(Inventory source, string good, Inventory own) {
      if (source == own) return false;
      var obtainer = source.GetComponent<GoodObtainer>();
      if (obtainer && obtainer.IsObtaining) return false;
      var warehouse = source.GetComponent<ModularWarehouse>();
      return !warehouse || !warehouse.HasSlot(good, WarehouseSlotMode.Obtain);
    }
  }

  internal sealed class ModularWarehouseSupplyBehavior : WorkplaceBehavior, IAwakableComponent {
    private ModularWarehouse _warehouse;
    public void Awake() { _warehouse = GetComponent<ModularWarehouse>(); }

    public override Decision Decide(BehaviorAgent agent) {
      if (!_warehouse.Operating) return Decision.ReleaseNow();
      var finder = agent.GetComponent<CarrierInventoryFinder>();
      var own = _warehouse.Inventory;
      foreach (int slot in _warehouse.SlotsIn(WarehouseSlotMode.Supply).Reverse().ToList()) {
        var good = _warehouse.GoodIn(slot);
        if (own.UnreservedAmountInStock(good) <= 0) continue;
        if (finder.TryCarryToAnyInventory(good, own, target => CanGiveTo(target, good, own))) return Decision.ReleaseNextTick();
      }
      return Decision.ReleaseNow();
    }

    private static bool CanGiveTo(Inventory target, string good, Inventory own) {
      if (target == own) return false;
      var supplier = target.GetComponent<GoodSupplier>();
      if (supplier && supplier.IsSupplying) return false;
      var warehouse = target.GetComponent<ModularWarehouse>();
      return !warehouse || !warehouse.HasSlot(good, WarehouseSlotMode.Supply);
    }
  }

  internal sealed class ModularWarehouseObtainHaulProvider : BaseComponent, IAwakableComponent, IHaulBehaviorProvider {
    private ModularWarehouse _warehouse;
    private ModularWarehouseObtainBehavior _behavior;
    public void Awake() {
      _warehouse = GetComponent<ModularWarehouse>();
      _behavior = GetComponent<ModularWarehouseObtainBehavior>();
    }

    public void GetWeightedBehaviors(IList<WeightedBehavior> weightedBehaviors) {
      if (!_warehouse.Operating) return;
      float lowest = 1f;
      bool any = false;
      foreach (int slot in _warehouse.SlotsIn(WarehouseSlotMode.Obtain)) { lowest = System.Math.Min(lowest, _warehouse.Fill(slot)); any = true; }
      if (any) weightedBehaviors.Add(new WeightedBehavior(1f - lowest, _behavior));
    }
  }

  internal sealed class ModularWarehouseSupplyHaulProvider : BaseComponent, IAwakableComponent, IHaulBehaviorProvider {
    private ModularWarehouse _warehouse;
    private ModularWarehouseSupplyBehavior _behavior;
    public void Awake() {
      _warehouse = GetComponent<ModularWarehouse>();
      _behavior = GetComponent<ModularWarehouseSupplyBehavior>();
    }

    public void GetWeightedBehaviors(IList<WeightedBehavior> weightedBehaviors) {
      if (!_warehouse.Operating) return;
      float highest = 0f;
      bool any = false;
      foreach (int slot in _warehouse.SlotsIn(WarehouseSlotMode.Supply)) { highest = System.Math.Max(highest, _warehouse.Fill(slot)); any = true; }
      if (any) weightedBehaviors.Add(new WeightedBehavior(highest, _behavior));
    }
  }
}
