using System.Collections.Generic;
using Timberborn.BaseComponentSystem;
using Timberborn.CoreUI;
using Timberborn.EntityPanelSystem;
using Timberborn.Goods;
using Timberborn.Localization;
using Timberborn.SliderToggleSystem;
using Timberborn.StockpilesUI;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.ModularStorage {
  // One native warehouse box per open slot, built from the game's own views and
  // services as StockpileInventoryFragment, GoodSelectionController,
  // StockpileGoodSelectionBox and StockpilePriorityToggle build a warehouse's
  // (decompiled 1.1.2.8): the good button and its selection box, the unselect
  // button, the good name, the stock / share bar, the leftover good row, and the
  // four-way Accept / Obtain / Supply / Empty toggle with the native icons and
  // texts (tooltips carry the native long descriptions). One line above names
  // the attached modules and the capacity. Rows are built when the panel is
  // shown; InitializeFragment depends on no singleton's Load.
  internal sealed class ModularWarehouseFragment : IEntityPanelFragment {
    public const string NetworkLocKey = "DeepFrontier.ModularWarehouse.Network";
    private readonly WarehouseSlotViewFactory _views;
    private readonly ILoc _loc;
    private readonly WarehouseSlotSelection _box;
    private readonly List<WarehouseSlotView> _slots = new List<WarehouseSlotView>();
    private VisualElement _root, _rows;
    private Label _network;
    private ModularWarehouse _warehouse;

    public ModularWarehouseFragment(WarehouseSlotViewFactory views, ILoc loc,WarehouseSlotSelection box) { _views = views; _loc = loc; _box=box; }

    public VisualElement InitializeFragment() {
      _root = new VisualElement();
      _network = new Label();
      _network.AddToClassList("entity-panel__text");
      _root.Add(_network);
      _rows = new VisualElement();
      _root.Add(_rows);
      _root.ToggleDisplayStyle(visible: false);
      return _root;
    }

    public void ShowFragment(BaseComponent entity) {
      var warehouse = entity.GetComponent<ModularWarehouse>();
      if (!warehouse) return;
      _warehouse = warehouse;
      for (int i = 0; i < warehouse.MaxSlots; i++) _slots.Add(_views.Create(_rows, warehouse, i));
      _root.ToggleDisplayStyle(visible: true);
    }

    public void ClearFragment() {
      foreach (var slot in _slots) slot.Clear();
      _slots.Clear();
      _rows.Clear();
      _warehouse = null;
      _root.ToggleDisplayStyle(visible: false);
    }

    public void UpdateFragment() {
      if (!_warehouse) return;
      _network.text = _loc.T(NetworkLocKey, _warehouse.Modules, _warehouse.NetworkCapacity);
      foreach (var slot in _slots) slot.Update();
    }
  }

  internal sealed class WarehouseSlotViewFactory {
    private readonly VisualElementLoader _loader;
    private readonly SliderToggleFactory _toggles;
    private readonly StockpileOptionsService _options;
    private readonly IGoodService _goods;
    private readonly WarehouseSlotSelection _box;
    private readonly ILoc _loc;

    public WarehouseSlotViewFactory(VisualElementLoader loader, SliderToggleFactory toggles, StockpileOptionsService options,
        IGoodService goods, WarehouseSlotSelection box, ILoc loc) {
      _loader = loader; _toggles = toggles; _options = options; _goods = goods; _box = box; _loc = loc;
    }

    public WarehouseSlotView Create(VisualElement parent, ModularWarehouse warehouse, int slot) {
      var root = _loader.LoadVisualElement("Game/EntityPanel/StockpileInventoryFragment");
      parent.Add(root);
      // StockpilePriorityToggle's items, order and icon classes, below the good row.
      var toggle = _toggles.Create(root.Q<VisualElement>("StockpileInventoryFragment"),
        Item(warehouse, slot, WarehouseSlotMode.Accept, "accept"),
        Item(warehouse, slot, WarehouseSlotMode.Obtain, "obtain"),
        Item(warehouse, slot, WarehouseSlotMode.Supply, "supply"),
        Item(warehouse, slot, WarehouseSlotMode.Empty, "empty"));
      return new WarehouseSlotView(_options, _goods, root, _box, toggle, warehouse, slot);
    }

    private SliderToggleItem Item(ModularWarehouse warehouse, int slot, WarehouseSlotMode mode, string icon) =>
      SliderToggleItem.Create(() => _loc.T($"StockpilePriority.{mode}") + "\n" + _loc.T($"StockpilePriority.{mode}.Long"),
        $"stockpile-priority-toggle__icon--{icon}", () => warehouse.SetMode(slot, mode), () => warehouse.ModeOf(slot) == mode);
  }

  internal sealed class WarehouseSlotView {
    private const string NoIconClass = "icon--hidden";
    private readonly StockpileOptionsService _options;
    private readonly IGoodService _goods;
    private readonly VisualElement _root;
    private readonly WarehouseSlotSelection _box;
    private readonly SliderToggle _toggle;
    private readonly ModularWarehouse _warehouse;
    private readonly int _slot;
    private readonly Label _amount, _limit, _goodName, _leftoverName;
    private readonly Timberborn.CoreUI.ProgressBar _progress;
    private readonly Button _unselect;
    private readonly Image _goodIcon, _leftoverIcon;
    private readonly VisualElement _leftover;
    private string _shownGood = "";

    public WarehouseSlotView(StockpileOptionsService options, IGoodService goods, VisualElement root, WarehouseSlotSelection box,
        SliderToggle toggle, ModularWarehouse warehouse, int slot) {
      _options = options; _goods = goods; _root = root; _box = box; _toggle = toggle; _warehouse = warehouse; _slot = slot;
      _amount = root.Q<Label>("CapacityAmount");
      _limit = root.Q<Label>("CapacityLimit");
      _progress = root.Q<Timberborn.CoreUI.ProgressBar>("ProgressBar");
      _goodIcon = root.Q<Image>("GoodIcon");
      _goodName = root.Q<Label>("SelectionItem");
      _leftover = root.Q<VisualElement>("OutputGood");
      _leftoverIcon = _leftover.Q<Image>("Image");
      _leftoverName = _leftover.Q<Label>("Name");
      _unselect = root.Q<Button>("Unselect");
      _unselect.RegisterCallback<ClickEvent>(_ => _warehouse.SetGood(_slot, null));
      var select = root.Q<Button>("Selection");
      select.RegisterCallback<ClickEvent>(_ => _box.Toggle(_warehouse, _slot, root.Q<VisualElement>("StockpileInventoryFragment")));
    }

    public void Update() {
      bool open = _slot < _warehouse.ActiveSlots;
      _root.ToggleDisplayStyle(open);
      if (!open) {
        _box.Hide();
        return;
      }
      int share = _warehouse.SlotCapacity(_slot);
      int stock = _warehouse.StockIn(_slot) + _warehouse.LeftoverStockIn(_slot);
      _progress.SetProgress(share > 0 ? (float)stock / share : 0f);
      _amount.text = stock.ToString();
      _limit.text = share.ToString();
      var good = _warehouse.GoodIn(_slot);
      if (good != _shownGood) {
        _shownGood = good;
        _options.UpdateItem(_goodName, _goodIcon, good ?? StockpileOptionsService.NothingSelectedLocKey);
        _goodIcon.EnableInClassList(NoIconClass, good != null);
      }
      _unselect.ToggleDisplayStyle(good != null);
      var leftover = _warehouse.FirstLeftoverIn(_slot);
      _leftover.ToggleDisplayStyle(leftover != null);
      if (leftover != null) {
        var spec = _goods.GetGood(leftover);
        _leftoverIcon.sprite = spec.IconSmall.Value;
        _leftoverName.text = spec.PluralDisplayName.Value;
      }
      _toggle.Update();
    }

    public void Clear() {
      _box.Hide();
      _toggle.Clear();
    }
  }
}
