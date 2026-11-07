using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.DuplicationSystem;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.InventoryNeedSystem;
using Timberborn.InventorySystem;
using Timberborn.Localization;
using Timberborn.Persistence;
using Timberborn.StatusSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts.ModularStorage {
  // Modular Warehouse: one core building that haulers use, plus Warehouse
  // Modules attached to it (beside it, or stacked on it and on each other;
  // ModularWarehouseNetwork). The core holds the network's only inventory, so
  // the district sees one storage point; modules hold no goods.
  //
  // Native storage (decompiled 1.1.2.8) is one Stockpile per entity
  // (Stockpile + SingleGoodAllower as the inventory's IGoodDisallower +
  // StockpilePriority over Emptiable/GoodObtainer/GoodSupplier), and native code
  // assumes one enabled Inventory per entity (InventoryDebugFragment
  // SingleOrDefault; tools/validate_single_inventory.mjs). So the core keeps ONE
  // native inventory of every GoodType good with public input and output (as
  // StockpileInventoryInitializer does, unlimited like the native
  // SimpleOutputInventory, since the limits come from the slots) and this
  // component is its good disallower, partitioned into slots:
  //   all MaxSlots selections are available; modules increase capacity only;
  //   network capacity = CoreCapacity + each attached module's Capacity, shared
  //   equally by the active slots;
  //   AllowedAmount(good) = its slot's share less the slot's leftovers, for the
  //   good selected in an active slot not set to Empty; 0 for every other good.
  // Native Inventory.LimitedAmount takes the minimum of that and the allowed
  // amount, so reservations, registries, unwanted stock, statistics, hauling
  // and needs stay native. Each slot has the four native stockpile priorities:
  //   Accept  takes deliveries up to the slot's share;
  //   Obtain  also has haulers fetch the good (native ObtainGoodWorkplaceBehavior);
  //   Supply  also has haulers take it to other storage (SupplyGoodWorkplaceBehavior);
  //   Empty   allows 0: the stock is native unwanted stock that laborers and
  //           haulers carry out, as a native warehouse empties a good it no
  //           longer allows.
  // A slot switched to another good keeps the old stock as leftovers until it
  // leaves; the new good fills the rest of the slot. Removing a module lowers the
  // capacity: stock above the new shares becomes native unwanted stock and is carried to
  // other storage. Goods never sit in a module, so removing one loses nothing;
  // deleting the core recovers its goods natively (RecoverableGoodProvider).
  internal record ModularWarehouseSpec : ComponentSpec {
    [Serialize] public int MaxSlots { get; init; }
    [Serialize] public int CoreCapacity { get; init; }
    [Serialize] public string GoodType { get; init; }
  }

  // Native StockpilePriority order: Accept, Obtain, Supply, Empty.
  internal enum WarehouseSlotMode { Accept, Obtain, Supply, Empty }

  internal sealed class WarehouseSlot {
    public string Good { get; set; }
    public WarehouseSlotMode Mode { get; set; } = WarehouseSlotMode.Accept;
    // Goods this slot held before its current good, still in stock (unwanted).
    public List<string> Leftovers { get; } = new List<string>();
  }

  internal sealed class ModularWarehouse : BaseComponent, IAwakableComponent, IInitializableEntity, IFinishedStateListener,
      IPersistentEntity, IGoodDisallower, IDuplicable<ModularWarehouse> {
    private static readonly ComponentKey WarehouseKey = new ComponentKey("DeepFrontier.ModularWarehouse");
    private static readonly PropertyKey<int> ModulesKey = new PropertyKey<int>("Modules");
    private static readonly PropertyKey<int> NetworkCapacityKey = new PropertyKey<int>("NetworkCapacity");
    // The native emptying status sprite and text (Timberborn.Emptying.Emptiable), as a normal
    // status: priority statuses are kept for hazards (tools/validate_priority_statuses.mjs).
    private const string EmptyingStatusSprite = "Empty";
    private const string EmptyingStatusLocKey = "Status.Emptying.EmptyingInProgress";

    private readonly SerializedGoodValueSerializer _goodSerializer;
    private readonly ILoc _loc;
    private readonly ModularWarehouseNetwork _network;
    private ModularWarehouseSpec _spec;
    private WarehouseSlot[] _slots;
    private BlockableObject _blockable;
    private StatusToggle _emptyingStatus;

    public ModularWarehouse(SerializedGoodValueSerializer goodSerializer, ILoc loc, ModularWarehouseNetwork network) {
      _goodSerializer = goodSerializer; _loc = loc; _network = network;
    }

    public event EventHandler<DisallowedGoodsChangedEventArgs> DisallowedGoodsChanged;
    public Inventory Inventory { get; private set; }
    public int MaxSlots => _slots.Length;
    // The attached network (ModularWarehouseNetwork.Update), saved so a load starts from it.
    public int Modules { get; private set; }
    public int NetworkCapacity { get; private set; }
    public int ActiveSlots => _slots.Length;
    // Finished and unblocked (automation and pause block it), as the native stockpile behaviors require.
    public bool Operating => Enabled && Inventory.Enabled && _blockable.IsUnblocked;

    // Called by ModularWarehouseInventoryInitializer before the native inventory
    // is initialized with this component as its good disallower.
    public void InitializeInventory(Inventory inventory, ModularWarehouseSpec spec) {
      if (Inventory != null) throw new InvalidOperationException("ModularWarehouse inventory is already initialized");
      _spec = spec;
      _slots = Enumerable.Range(0, spec.MaxSlots).Select(_ => new WarehouseSlot()).ToArray();
      NetworkCapacity = spec.CoreCapacity;
      Inventory = inventory;
    }

    public void Awake() {
      if (Inventory == null) throw new InvalidOperationException("ModularWarehouse has no inventory (ModularWarehouseInventoryInitializer)");
      _blockable = GetComponent<BlockableObject>();
      _emptyingStatus = StatusToggle.CreateNormalStatusWithFloatingIcon(EmptyingStatusSprite, _loc.T(EmptyingStatusLocKey));
      DisableComponent();
    }

    // After Load (stock and slots are loaded): native events and statuses.
    public void InitializeEntity() {
      GetComponent<StatusSubject>().RegisterStatus(_emptyingStatus);
      Inventory.InventoryStockChanged += OnInventoryStockChanged;
      foreach (var slot in _slots) slot.Leftovers.RemoveAll(good => Inventory.AmountInStock(good) == 0 || IsSelected(good));
    }

    public void OnEnterFinishedState() {
      EnableComponent();
      Inventory.Enable();
      UpdateEmptyingStatus();
      _network.Add(this);
    }

    public void OnExitFinishedState() {
      _network.Remove(this);
      Inventory.Disable();
      _emptyingStatus.Deactivate();
      DisableComponent();
    }

    // --- The attached modules (ModularWarehouseNetwork).
    public void SetNetwork(int modules, int capacity) {
      if (modules < 0 || capacity < _spec.CoreCapacity) throw new ArgumentException($"ModularWarehouse network of {modules} modules and {capacity} capacity");
      if (modules == Modules && capacity == NetworkCapacity) return;
      var changed = new HashSet<string>(_slots.SelectMany(s => s.Leftovers.Append(s.Good)).Where(g => g != null));
      Modules = modules;
      NetworkCapacity = capacity;
      // Modules change capacity, not the five good selections. Reduced limits
      // make excess stock unwanted through the native inventory system.
      foreach (var good in changed) InvokeDisallowedGoodsChanged(good);
      UpdateEmptyingStatus();
    }

    // --- Slots (entity panel and duplication).
    public string GoodIn(int slot) => _slots[slot].Good;
    public WarehouseSlotMode ModeOf(int slot) => _slots[slot].Mode;
    public int StockIn(int slot) => _slots[slot].Good == null ? 0 : Inventory.AmountInStock(_slots[slot].Good);
    public int LeftoverStockIn(int slot) => _slots[slot].Leftovers.Sum(Inventory.AmountInStock);
    public string FirstLeftoverIn(int slot) => _slots[slot].Leftovers.FirstOrDefault(good => Inventory.AmountInStock(good) > 0);
    // An active slot's share of the network capacity (the remainder goes to the first slots).
    public int SlotCapacity(int slot) {
      int active = ActiveSlots;
      if (slot >= active) return 0;
      return NetworkCapacity / active + (slot < NetworkCapacity % active ? 1 : 0);
    }
    // Goods a slot may select: the inventory's goods not selected in another slot.
    public IEnumerable<string> SelectableGoods(int slot) =>
      Inventory.AllowedGoods.Select(g => g.StorableGood.GoodId).Where(good => !IsSelectedElsewhere(good, slot));

    public void SetGood(int index, string good) {
      var slot = _slots[index];
      if (slot.Good == good) return;
      if (good != null) {
        if (index >= ActiveSlots) throw new ArgumentException($"ModularWarehouse slot {index} is closed ({ActiveSlots} open)");
        if (!Inventory.Takes(good)) throw new ArgumentException($"ModularWarehouse does not store {good}");
        if (IsSelectedElsewhere(good, index)) throw new ArgumentException($"ModularWarehouse already stores {good} in another slot");
      }
      var changed = new HashSet<string>();
      var previous = slot.Good;
      slot.Good = good;
      if (good != null) {
        changed.Add(good);
        // Leftovers of the newly selected good now count as this slot's stock.
        foreach (var other in _slots) if (other.Leftovers.Remove(good) && other.Good != null) changed.Add(other.Good);
      }
      if (previous != null) {
        changed.Add(previous);
        if (Inventory.AmountInStock(previous) > 0) slot.Leftovers.Add(previous);
      }
      foreach (var id in changed) InvokeDisallowedGoodsChanged(id);
    }

    public void SetMode(int index, WarehouseSlotMode mode) {
      var slot = _slots[index];
      if (slot.Mode == mode) return;
      if (index >= ActiveSlots) throw new ArgumentException($"ModularWarehouse slot {index} is closed ({ActiveSlots} open)");
      slot.Mode = mode;
      if (slot.Good != null) InvokeDisallowedGoodsChanged(slot.Good);
      UpdateEmptyingStatus();
    }

    // Active slots in a mode with their good selected, emptiest first (fill = stock / limit).
    public IEnumerable<int> SlotsIn(WarehouseSlotMode mode) =>
      Enumerable.Range(0, ActiveSlots).Where(i => _slots[i].Mode == mode && _slots[i].Good != null).OrderBy(Fill);
    public float Fill(int index) {
      var good = _slots[index].Good;
      int limit = good == null ? 0 : Inventory.LimitedAmount(good);
      return limit <= 0 ? 1f : Math.Min(1f, (float)Inventory.AmountInStock(good) / limit);
    }
    // Whether this warehouse's slot for a good is in a mode (haul filters between warehouses).
    public bool HasSlot(string good, WarehouseSlotMode mode) => _slots.Any(s => s.Good == good && s.Mode == mode);

    // --- IGoodDisallower: the per-slot partition of the native inventory.
    public int AllowedAmount(string goodId) {
      for (int i = 0; i < _slots.Length; i++) {
        var slot = _slots[i];
        if (slot.Good != goodId) continue;
        if (slot.Mode == WarehouseSlotMode.Empty) return 0;
        return Math.Max(0, SlotCapacity(i) - slot.Leftovers.Sum(Inventory.AmountInStock));
      }
      return 0;
    }

    private bool IsSelected(string good) => _slots.Any(s => s.Good == good);
    private bool IsSelectedElsewhere(string good, int index) {
      for (int i = 0; i < _slots.Length; i++) if (i != index && _slots[i].Good == good) return true;
      return false;
    }

    // A leftover leaving frees its slot for the slot's good.
    private void OnInventoryStockChanged(object sender, InventoryStockChangedEventArgs e) {
      var good = e.GoodAmount.GoodId;
      foreach (var slot in _slots) {
        if (!slot.Leftovers.Contains(good)) continue;
        if (Inventory.AmountInStock(good) == 0) slot.Leftovers.Remove(good);
        if (slot.Good != null) InvokeDisallowedGoodsChanged(slot.Good);
      }
    }

    private void UpdateEmptyingStatus() {
      if (!Enabled) return;
      _emptyingStatus.Toggle(_slots.Any(s => s.Mode == WarehouseSlotMode.Empty));
    }

    private void InvokeDisallowedGoodsChanged(string good) =>
      DisallowedGoodsChanged?.Invoke(this, new DisallowedGoodsChangedEventArgs(good));

    // --- Copy settings (native Duplicator): goods and modes of the open slots.
    public void DuplicateFrom(ModularWarehouse source) {
      for (int i = 0; i < ActiveSlots; i++) SetGood(i, null);
      for (int i = 0; i < ActiveSlots && i < source.ActiveSlots; i++) {
        SetGood(i, source.GoodIn(i));
        SetMode(i, source.ModeOf(i));
      }
    }

    // --- Persistence: the network last seen, and per slot its good (native
    // SerializedGood, so retired goods load as obsolete), mode name and leftovers.
    private static PropertyKey<SerializedGood> GoodKey(int i) => new PropertyKey<SerializedGood>("Good" + i);
    private static PropertyKey<string> ModeKey(int i) => new PropertyKey<string>("Mode" + i);
    private static ListKey<SerializedGood> LeftoversKey(int i) => new ListKey<SerializedGood>("Leftovers" + i);

    public void Save(IEntitySaver entitySaver) {
      var saver = entitySaver.GetComponent(WarehouseKey);
      saver.Set(ModulesKey, Modules);
      saver.Set(NetworkCapacityKey, NetworkCapacity);
      for (int i = 0; i < _slots.Length; i++) {
        var slot = _slots[i];
        if (slot.Good != null) saver.Set(GoodKey(i), new SerializedGood(slot.Good), _goodSerializer);
        saver.Set(ModeKey(i), slot.Mode.ToString());
        if (slot.Leftovers.Count > 0)
          saver.Set(LeftoversKey(i), slot.Leftovers.Select(g => new SerializedGood(g)).ToList(), _goodSerializer);
      }
    }

    public void Load(IEntityLoader entityLoader) {
      if (!entityLoader.TryGetComponent(WarehouseKey, out var loader)) return;
      Modules = loader.Get(ModulesKey);
      NetworkCapacity = loader.Get(NetworkCapacityKey);
      for (int i = 0; i < _slots.Length; i++) {
        var slot = _slots[i];
        // A good the inventory no longer takes is dropped, as native SingleGoodAllower.Load does.
        if (loader.Has(GoodKey(i)) && loader.GetObsoletable(GoodKey(i), _goodSerializer, out var good) && Inventory.Takes(good.Id)) {
          if (IsSelected(good.Id)) throw new InvalidOperationException($"ModularWarehouse save selects {good.Id} in two slots");
          slot.Good = good.Id;
        }
        var mode = loader.Get(ModeKey(i));
        if (!Enum.TryParse(mode, false, out WarehouseSlotMode parsed) || !Enum.IsDefined(typeof(WarehouseSlotMode), parsed))
          throw new InvalidOperationException($"ModularWarehouse save has an unknown slot mode '{mode}'");
        slot.Mode = parsed;
        if (loader.Has(LeftoversKey(i)))
          slot.Leftovers.AddRange(loader.Get(LeftoversKey(i), _goodSerializer).Select(g => g.Id).Where(Inventory.Takes).Distinct());
      }
    }
  }

  // One native inventory of every GoodType good with public input and output,
  // as StockpileInventoryInitializer builds a warehouse's, unlimited as the
  // native SimpleOutputInventoryInitializer and GoodStackInventoryInitializer
  // build theirs (the slots limit each good), with the warehouse as its good
  // disallower, and the native need behavior (beavers use needs goods stored here).
  internal sealed class ModularWarehouseInventoryInitializer : IDedicatedDecoratorInitializer<ModularWarehouse, Inventory> {
    private const string InventoryComponentName = "ModularWarehouse";
    private readonly InventoryInitializerFactory _inventories;
    private readonly InventoryNeedBehaviorInitializer _needs;
    private readonly IGoodService _goods;

    public ModularWarehouseInventoryInitializer(InventoryInitializerFactory inventories, InventoryNeedBehaviorInitializer needs, IGoodService goods) {
      _inventories = inventories; _needs = needs; _goods = goods;
    }

    public void Initialize(ModularWarehouse subject, Inventory decorator) {
      var spec = subject.GetComponent<ModularWarehouseSpec>();
      if (spec.MaxSlots <= 0 || spec.CoreCapacity <= 0)
        throw new InvalidOperationException("ModularWarehouseSpec needs positive MaxSlots and CoreCapacity");
      if (!_goods.Goods.Any(id => _goods.GetGood(id).GoodType == spec.GoodType))
        throw new InvalidOperationException($"ModularWarehouseSpec.GoodType {spec.GoodType} has no goods");
      var init = _inventories.CreateWithUnlimitedCapacity(decorator, InventoryComponentName);
      init.AddAllowedGoodType(spec.GoodType);
      init.HasPublicOutput();
      init.HasPublicInput();
      subject.InitializeInventory(decorator, spec);
      init.AddGoodDisallower(subject);
      init.Initialize();
      _needs.AddNeedBehavior(decorator);
    }
  }
}
