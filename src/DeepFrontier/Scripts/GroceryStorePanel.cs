#if !UNITY_EDITOR
using Bindito.Core;
using System.Collections.Generic;
using Timberborn.BaseComponentSystem;
using Timberborn.Buildings;
using Timberborn.EntityPanelSystem;
using Timberborn.InventorySystemUI;
using Timberborn.WorkSystem;
using TimberUi.CommonUi;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts {
  internal sealed class GroceryStorePanel : BaseEntityPanelFragment<GroceryStore> {
    private readonly InformationalRowsFactory _inventoryRows;
    private readonly List<InformationalRow> _stock=new List<InformationalRow>();
    private VisualElement _stockRoot;
    private Label _staff,_assortment,_service;
    public GroceryStorePanel(InformationalRowsFactory inventoryRows) {_inventoryRows=inventoryRows;}
    protected override void InitializePanel() {
      panel.AddGameLabel("Grocery store",bold:true);
      _staff=panel.AddGameLabel();_assortment=panel.AddGameLabel();
      _service=panel.AddGameLabel();_service.style.whiteSpace=WhiteSpace.Normal;
      _stockRoot=new VisualElement();panel.Add(_stockRoot);
    }
    public override void ShowFragment(BaseComponent entity) {
      base.ShowFragment(entity);
      if(component) {
        // Native InventoryFragment enumerates only exclusively givable/takeable goods.
        // Grocery foods are both: clerks deliver them and residents eat them here.
        foreach(var good in component.Inventory.AllowedGoods)
          _stock.Add(_inventoryRows.CreateInputRowWithLimit(good.StorableGood,component.Inventory,_stockRoot));
      }
      UpdateFragment();
    }
    public override void ClearFragment() {_stockRoot.Clear();_stock.Clear();base.ClearFragment();}
    public override void UpdateFragment() {
      if(!component)return;
      foreach(var row in _stock)row.ShowUpdated();
      var spec=component.GetComponent<GroceryStoreSpec>();
      _staff.text=$"Clerks attending: {component.AttendingStaff} / {component.GetComponent<WorkplaceSpec>().MaxWorkers}";
      _assortment.text=$"Stocked foods: {component.StockedFoodTypes} / {spec.Foods.Length}";
      if(!component.Enabled)_service.text="Under construction";
      else if(component.ProvidesNeighborhoodService)_service.text="Neighborhood groceries active (+2 wellbeing)";
      else if(component.GetComponent<PausableBuilding>().Paused)_service.text="Restocking and neighborhood service paused\nStored food remains available";
      else if(!component.IsOperating)_service.text="Neighborhood service needs power\nStored food remains available";
      else if(component.StockedFoodTypes<spec.MinimumStockedFoodTypes)_service.text=$"Neighborhood service needs {spec.MinimumStockedFoodTypes} stocked food types";
      else _service.text="Waiting for a clerk to attend the store";
    }
  }
  [Context("Game")]
  public sealed class GroceryStorePanelConfigurator : Configurator {
    protected override void Configure() {this.BindFragment<GroceryStorePanel>();}
  }
}
#endif
