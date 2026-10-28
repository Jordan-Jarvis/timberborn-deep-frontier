using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using Timberborn.InventorySystem;

namespace DeepFrontier.Scripts.Cryogenics {
  // The cryogenic stockpile's IGoodDisallower: the native SingleGoodAllower
  // selection, restricted to CryogenicTankSpec.Goods, closed to new stock while
  // the tank is unpowered.
  //
  // Native 1.1.2.8 StockpileInventoryInitializer.Initialize passes its
  // SingleGoodAllower to InventoryInitializer.AddGoodDisallower, which keeps a
  // single disallower; there is no composition hook. CryogenicIntakeGatePatch
  // (InventoryInitializer.Initialize prefix) substitutes this gate for
  // stockpiles that carry CryogenicTankSpec only. The gate delegates to that
  // same SingleGoodAllower, so the native selection UI, saves and duplication
  // are unchanged.
  //
  // Closed means AllowedAmount equals the stock on hand. Inventory.GoodCapacity
  // and UnreservedCapacity become 0, so native haulers (DistrictInventoryPicker),
  // Timber Pipes tanks (PipeTank.FreeGoods/TryGive) and valves
  // (DefaultBuildingPipeConnection.TryGive) cannot add stock, while
  // UnwantedStockAmount stays 0 (haulers do not empty the tank) and withdrawal
  // is untouched.
  internal sealed class CryogenicIntakeGate : IInitializableGoodDisallower {
    private static readonly ConditionalWeakTable<SingleGoodAllower, CryogenicIntakeGate> Gates =
      new ConditionalWeakTable<SingleGoodAllower, CryogenicIntakeGate>();

    private readonly SingleGoodAllower _allower;
    private readonly HashSet<string> _goods;
    private readonly string[] _goodOrder;
    private Inventory _inventory;

    public event EventHandler<DisallowedGoodsChangedEventArgs> DisallowedGoodsChanged;

    public bool Accepting { get; private set; } = true;

    private CryogenicIntakeGate(SingleGoodAllower allower, CryogenicTankSpec spec) {
      if (spec.Goods.IsDefaultOrEmpty) throw new InvalidOperationException("CryogenicTankSpec.Goods is empty");
      _allower = allower;
      _goodOrder = spec.Goods.ToArray();
      _goods = new HashSet<string>(_goodOrder);
      if (_goods.Count != _goodOrder.Length) throw new InvalidOperationException("CryogenicTankSpec.Goods has duplicates");
      allower.DisallowedGoodsChanged += (sender, args) => DisallowedGoodsChanged?.Invoke(this, args);
    }

    public static CryogenicIntakeGate Install(SingleGoodAllower allower, CryogenicTankSpec spec) {
      var gate = new CryogenicIntakeGate(allower, spec);
      Gates.Add(allower, gate);
      return gate;
    }

    public static CryogenicIntakeGate For(SingleGoodAllower allower) {
      if (allower && Gates.TryGetValue(allower, out var gate)) return gate;
      throw new InvalidOperationException("Cryogenic tank inventory was initialized without CryogenicIntakeGate; "
        + "CryogenicIntakeGatePatch (InventoryInitializer.Initialize) did not run for this stockpile");
    }

    // Native InventoryInitializer.Initialize calls this after Inventory.Initialize.
    // The SingleGoodAllower was already initialized by StockpileInventoryInitializer.
    public void Initialize(Inventory inventory) {
      if (_inventory) throw new InvalidOperationException("CryogenicIntakeGate initialized twice");
      _inventory = inventory;
    }

    public Inventory Inventory => _inventory;

    public bool IsCryogenicGood(string goodId) => goodId != null && _goods.Contains(goodId);

    public IReadOnlyList<string> Goods => _goodOrder;

    public int AllowedAmount(string goodId) {
      int allowed = _allower.AllowedAmount(goodId);
      if (allowed == 0 || !_goods.Contains(goodId)) return 0;
      return Accepting ? allowed : _inventory.AmountInStock(goodId);
    }

    public void SetAccepting(bool accepting) {
      if (accepting == Accepting) return;
      Accepting = accepting;
      foreach (var good in _goodOrder) DisallowedGoodsChanged?.Invoke(this, new DisallowedGoodsChangedEventArgs(good));
    }
  }
}
