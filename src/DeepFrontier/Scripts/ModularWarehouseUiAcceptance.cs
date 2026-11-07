#if !UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using Bindito.Core;
using DeepFrontier.Scripts.ModularStorage;
using Timberborn.CoreUI;
using Timberborn.StockpilesUI;
using Timberborn.EntitySystem;
using Timberborn.SelectionSystem;
using Timberborn.SingletonSystem;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class ModularWarehouseUiAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierWarehouseUiAcceptance"))
        Bind<ModularWarehouseUiAcceptance>().AsSingleton();
    }
  }

  // Exercises actual panel callbacks on a named disposable save. Never saves.
  internal sealed class ModularWarehouseUiAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    const string Tag="[DeepFrontier WarehouseUI] ";
    readonly EntityRegistry _entities;
    readonly EntitySelectionService _selection;
    readonly ModularWarehouseFragment _fragment;
    readonly OverlayGoodSelectionController _picker;
    ModularWarehouse _warehouse;
    VisualElement _root;
    int _frame,_slot;
    bool _opened,_done;
    public ModularWarehouseUiAcceptance(EntityRegistry entities,EntitySelectionService selection,ModularWarehouseFragment fragment,OverlayGoodSelectionController picker) {
      _entities=entities;_selection=selection;_fragment=fragment;_picker=picker;
    }
    static void Require(bool condition,string message) { if(!condition)throw new InvalidOperationException(Tag+message); }
    public void PostLoad() {
      Require(Path.GetFileName(MemoryLoadProbe.SavePath())=="modular-warehouse-ui-repro-copy.timber" &&
        !Environment.GetCommandLineArgs().Contains(MemoryLoadProbe.SaveAsFlag),"Requires its disposable save without SaveAs");
    }
    static void Click(Button button) {
      using(var e=ClickEvent.GetPooled()) { e.target=button;button.SendEvent(e); }
    }
    static void RequireClickable(Button button) {
      var hit=button.panel.Pick(button.worldBound.center);
      Require(hit==button||button.Contains(hit),"Button is clipped or obscured: "+button.name+" at "+button.worldBound);
    }
    public void UpdateSingleton() {
      if(++_frame<60||_done)return;
      if(_frame==60) {
        _warehouse=_entities.Entities.Select(e=>e.GetComponent<ModularWarehouse>()).Single(w=>w);
        _selection.SelectAndFocusOn(_warehouse);
        _root=(VisualElement)typeof(ModularWarehouseFragment).GetField("_root",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(_fragment);
        Require(_warehouse.Modules==0 && _warehouse.ActiveSlots==5,"Core must provide five slots without modules");
        Debug.Log(Tag+"selected native entity panel; five slots, capacity "+_warehouse.NetworkCapacity);
        return;
      }
      if(_frame%30!=0)return;
      var selectors=_root.Query<Button>("Selection").ToList();
      Require(selectors.Count==5,"Expected five native warehouse selection buttons");
      foreach(var button in selectors)Require(button.worldBound.width>0&&button.worldBound.height>0,"Selection button has no visible layout");
      if(_slot==5) {
        Require(Enumerable.Range(0,5).Select(_warehouse.GoodIn).Distinct().Count()==5,"Selections are not five distinct goods");
        var selected=Enumerable.Range(0,5).Select(_warehouse.GoodIn).ToArray();
        _warehouse.SetNetwork(1,1200);_warehouse.SetNetwork(0,600);
        Require(Enumerable.Range(0,5).Select(_warehouse.GoodIn).SequenceEqual(selected),"Module changes erased selections");
        foreach(var good in selected)Require(_warehouse.Inventory.LimitedAmount(good)==120,"Core slot capacity is not 120");
        Debug.Log(Tag+"PASS five native pickers opened, populated and selected distinct goods; module removal preserves selections and capacity limits");
        _done=true;return;
      }
      if(!_opened) {
        RequireClickable(selectors[_slot]);Click(selectors[_slot]);_opened=true;return;
      }
      var picker=_picker._stockpileGoodSelectionBox.Root;
      Require(_picker.SelectedItem!=null&&picker.IsDisplayed(),"Native floating picker did not open for slot "+_slot);
      var items=picker.Query<Button>("GoodSelectionBoxItem").ToList();
      Require(items.Count>0,"Native picker is blank for slot "+_slot);
      RequireClickable(items[0]);RequireClickable(items.Last());
      var viewport=picker.panel.visualTree.worldBound;
      Require(viewport.Contains(picker.worldBound.min)&&viewport.Contains(picker.worldBound.max),"Picker extends beyond the screen");
      Debug.Log(Tag+"slot "+_slot+": "+items.Count+" native goods; first/last items hit-test in native floating panel; popup "+picker.worldBound);
      Click(items[0]);
      Require(_warehouse.GoodIn(_slot)!=null,"Selecting a native item did not set the good");
      Require(_picker.SelectedItem==null,"Picker did not close after selection");
      _slot++;_opened=false;
    }
  }
}
#endif
