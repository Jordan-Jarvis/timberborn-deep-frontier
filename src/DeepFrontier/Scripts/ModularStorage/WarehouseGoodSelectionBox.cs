using System.Collections.Generic;
using System.Linq;
using Timberborn.CoreUI;
using Timberborn.Goods;
using Timberborn.InputSystem;
using Timberborn.ResourceCountingSystemUI;
using Timberborn.StockpilesUI;
using Timberborn.TooltipSystem;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.ModularStorage {
  // The native warehouse good picker for one slot: StockpileGoodSelectionBox,
  // StockpileGoodSelectionBoxItemsFactory, GoodSelectionBoxRowFactory and
  // GoodSelectionBoxItemFactory (decompiled 1.1.2.8, internal there) rebuilt
  // from their public views and services. One row per good group in group
  // order, one button per good (icon, district fill, native stockpile tooltip);
  // goods selected in another slot are left out. A click outside closes it.
  internal sealed class WarehouseGoodSelectionBox : IInputProcessor {
    private const string NoMarginClass = "good-selection-box-row--no-margin";
    private const string SelectedItemClass = "selected-item";
    private readonly InputService _input;
    private readonly VisualElementLoader _loader;
    private readonly StockpileOptionsService _options;
    private readonly GoodsGroupSpecService _groups;
    private readonly IGoodService _goods;
    private readonly ContextualResourceCountingService _counts;
    private readonly ITooltipRegistrar _tooltips;
    private readonly GoodStockpilesTooltipFactory _goodTooltips;
    private readonly VisualElement _selection;
    private readonly List<(string Good, VisualElement Root, VisualElement Fill)> _items = new List<(string, VisualElement, VisualElement)>();
    private ModularWarehouse _warehouse;
    private int _slot;
    private bool _mouseOver, _ignoreInput;

    public WarehouseGoodSelectionBox(InputService input, VisualElementLoader loader, StockpileOptionsService options, GoodsGroupSpecService groups,
        IGoodService goods, ContextualResourceCountingService counts, ITooltipRegistrar tooltips, GoodStockpilesTooltipFactory goodTooltips) {
      _input = input; _loader = loader; _options = options; _groups = groups; _goods = goods; _counts = counts; _tooltips = tooltips; _goodTooltips = goodTooltips;
      Root = _loader.LoadVisualElement("Game/StockpileGoodSelectionBox");
      _selection = Root.Q<VisualElement>("GoodSelection");
      Root.ToggleDisplayStyle(visible: false);
      Root.RegisterCallback<MouseEnterEvent>(_ => _mouseOver = true);
      Root.RegisterCallback<MouseLeaveEvent>(_ => _mouseOver = false);
    }

    public VisualElement Root { get; }
    private bool IsShown => Root.IsDisplayed();

    public void Toggle(ModularWarehouse warehouse, int slot) {
      if (IsShown) Hide();
      else Show(warehouse, slot);
    }

    public void DisableInput() => _ignoreInput = true;
    public void EnableInput() => _ignoreInput = false;

    public bool ProcessInput() {
      if (_input.UICancel || (_input.MainMouseButtonDown && !_mouseOver && !_ignoreInput)) {
        Hide();
        return _input.UICancel;
      }
      return false;
    }

    public void Update() {
      if (!IsShown) return;
      var selected = _warehouse.GoodIn(_slot);
      foreach (var (good, root, fill) in _items) {
        var count = _counts.GetContextualResourceCount(good);
        fill.SetHeightAsPercent(count.FillRate);
        fill.parent.ToggleDisplayStyle(count.AvailableStock > 0);
        root.EnableInClassList(SelectedItemClass, selected == good);
      }
    }

    public void Hide() {
      if (!IsShown) return;
      Root.ToggleDisplayStyle(visible: false);
      _input.RemoveInputProcessor(this);
      _selection.Clear();
      _items.Clear();
      _warehouse = null;
    }

    private void Show(ModularWarehouse warehouse, int slot) {
      _warehouse = warehouse; _slot = slot;
      _ignoreInput = true; _mouseOver = false;
      var rows = new Dictionary<string, (int Order, VisualElement Root, VisualElement Icons)>();
      foreach (var good in warehouse.SelectableGoods(slot)) {
        var groupId = _goods.GetGood(good).GoodGroupId;
        if (!rows.TryGetValue(groupId, out var row)) {
          var spec = _groups.GetSpec(groupId);
          var rowRoot = _loader.LoadVisualElement("Game/EntityPanel/GoodSelectionBoxRow");
          rowRoot.Q<Image>("HeaderIcon").sprite = spec.Icon.Asset;
          rows[groupId] = row = (spec.Order, rowRoot, rowRoot.Q<VisualElement>("Icons"));
        }
        var item = _loader.LoadVisualElement("Game/EntityPanel/StockpileInventoryFragmentItem");
        var id = good;
        item.Q<Button>("GoodSelectionBoxItem").RegisterCallback<ClickEvent>(_ => Select(id));
        item.Q<Image>("Icon").sprite = _options.GetItemIcon(id);
        _tooltips.Register(item, () => _goodTooltips.Create(id));
        row.Icons.Add(item);
        _items.Add((id, item, item.Q<VisualElement>("Fill")));
      }
      var ordered = rows.Values.OrderBy(r => r.Order).ToList();
      foreach (var row in ordered) _selection.Add(row.Root);
      if (ordered.Count > 0) ordered.Last().Root.AddToClassList(NoMarginClass);
      Root.ToggleDisplayStyle(visible: true);
      _input.AddInputProcessor(this);
      Update();
    }

    private void Select(string good) {
      var warehouse = _warehouse;
      int slot = _slot;
      Hide();
      warehouse.SetGood(slot, good);
    }
  }

  internal sealed class WarehouseGoodSelectionBoxFactory {
    private readonly InputService _input;
    private readonly VisualElementLoader _loader;
    private readonly StockpileOptionsService _options;
    private readonly GoodsGroupSpecService _groups;
    private readonly IGoodService _goods;
    private readonly ContextualResourceCountingService _counts;
    private readonly ITooltipRegistrar _tooltips;
    private readonly GoodStockpilesTooltipFactory _goodTooltips;

    public WarehouseGoodSelectionBoxFactory(InputService input, VisualElementLoader loader, StockpileOptionsService options, GoodsGroupSpecService groups,
        IGoodService goods, ContextualResourceCountingService counts, ITooltipRegistrar tooltips, GoodStockpilesTooltipFactory goodTooltips) {
      _input = input; _loader = loader; _options = options; _groups = groups; _goods = goods; _counts = counts; _tooltips = tooltips; _goodTooltips = goodTooltips;
    }

    public WarehouseGoodSelectionBox Create() =>
      new WarehouseGoodSelectionBox(_input, _loader, _options, _groups, _goods, _counts, _tooltips, _goodTooltips);
  }
}
