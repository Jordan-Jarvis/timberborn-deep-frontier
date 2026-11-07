using System;
using System.Collections.Generic;
using System.Linq;
using Bindito.Unity;
using Timberborn.BaseComponentSystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.SingletonSystem;
using Timberborn.Stockpiles;
using Timberborn.StockpilesUI;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.ModularStorage {
  // Data adapter only. The game's existing floating controller owns the picker,
  // its controls, positioning, updates, input and dismissal without replacement.
  // Native picker input is a Stockpile with a SingleGoodAllower and dropdown
  // provider. This UI-only component cache represents one selected slot; it is
  // never registered as a world entity, inventory or hauling destination.
  internal sealed class WarehouseSlotSelection : IUnloadableSingleton {
    readonly OverlayGoodSelectionController _picker;
    readonly IInstantiator _instantiator;
    readonly SerializedGoodValueSerializer _serializer;
    readonly StockpileOptionsService _options;
    GameObject _data;
    SingleGoodAllower _selection;
    ModularWarehouse _warehouse;
    VisualElement _anchor;
    int _slot;

    public WarehouseSlotSelection(OverlayGoodSelectionController picker,IInstantiator instantiator,
        SerializedGoodValueSerializer serializer,StockpileOptionsService options) {
      _picker=picker;_instantiator=instantiator;_serializer=serializer;_options=options;
    }

    public void Toggle(ModularWarehouse warehouse,int slot,VisualElement anchor) {
      bool close=_picker.SelectedItem==anchor;
      Hide();
      if(close)return;
      _warehouse=warehouse;_slot=slot;_anchor=anchor;
      _data=new GameObject("ModularWarehouseSlotSelection");
      var stockpile=new Stockpile();
      _selection=new SingleGoodAllower(_serializer);
      var provider=new StockpileDropdownProvider(_options);
      var cache=_instantiator.AddComponent<ComponentCache>(_data);
      cache.Initialize(new List<object>{stockpile,_selection,provider},_data.name,new TypeIndexMap());
      stockpile.InitializeInventory(warehouse.Inventory);
      _selection.Initialize(warehouse.Inventory);
      _selection.Allow(warehouse.GoodIn(slot));
      provider.Awake();
      provider.InitializeEntity();
      // Filter the native data provider, not the picker: other slots already
      // reserve their goods. No second inventory or stockpile is registered.
      var allowed=warehouse.SelectableGoods(slot).ToHashSet();
      provider._items.RemoveAll(g=>g!=StockpileOptionsService.NothingSelectedLocKey&&!allowed.Contains(g));
      _selection.DisallowedGoodsChanged+=OnSelectionChanged;
      _picker.ToggleGoodSelection(stockpile,anchor);
    }

    void OnSelectionChanged(object sender,DisallowedGoodsChangedEventArgs e) {
      // Native Allow first disallows the old value, then publishes the new one.
      // Clearing a slot remains the native row's separate Unselect button.
      if(_selection.HasAllowedGood)_warehouse.SetGood(_slot,_selection.AllowedGood);
    }
    public void Hide() {
      if(_anchor!=null&&_picker.SelectedItem==_anchor)_picker.HideBox();
      if(_selection!=null)_selection.DisallowedGoodsChanged-=OnSelectionChanged;
      if(_data)UnityEngine.Object.Destroy(_data);
      _data=null;_selection=null;_warehouse=null;_anchor=null;
    }
    public void Unload()=>Hide();
  }
}
