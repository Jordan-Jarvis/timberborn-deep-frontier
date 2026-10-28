using System;
using System.Collections.Generic;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.Common;
using Timberborn.InventorySystem;
using Timberborn.TemplateInstantiation;
using UnityEngine;

namespace DeepFrontier.Scripts {
  internal record GroceryStockDisplaySpec : ComponentSpec {
    [Serialize] public int Stages { get; init; }
  }

  // The grocery's stands show what its native inventory actually holds. The
  // finished model carries static nodes GroceryStock.<Food>.<1..Stages> for
  // every food of GroceryStoreSpec. Stages add up: stage n is shown once the
  // food fills more than (n-1)/Stages of its capacity, so with three stages
  // 1-33 % shows stage 1, 34-66 % stages 1-2 and 67-100 % all three. An empty
  // food shows nothing; its trays, shelves and crates stay bare. The display
  // follows native InventoryStockChanged events; it changes no stock.
  internal sealed class GroceryStockDisplay : BaseComponent, IAwakableComponent, IFinishedStateListener {
    private const string Prefix = "GroceryStock.";
    private readonly Dictionary<string,GameObject[]> _nodes=new();
    private GroceryStockDisplaySpec _spec;
    private GroceryStoreSpec _store;
    private GroceryStore _shop;
    private Inventory _inventory;

    public int ShownStages(string food)=>_nodes[food].Count(n=>n.activeSelf);

    public void Awake() {
      _spec=GetComponent<GroceryStockDisplaySpec>();_store=GetComponent<GroceryStoreSpec>();_shop=GetComponent<GroceryStore>();
      if(_spec.Stages<1)throw new InvalidOperationException("Grocery stock display needs at least one stage");
      if(_store.CapacityPerFood<=0)throw new InvalidOperationException("Grocery stock display needs a positive capacity per food");
      var transforms=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName)
        .GetComponentsInChildren<Transform>(true);
      var expected=new HashSet<string>();
      foreach(var food in _store.Foods) {
        var stages=new GameObject[_spec.Stages];
        for(int n=1;n<=_spec.Stages;n++) {
          var name=$"{Prefix}{food}.{n}";
          var matches=transforms.Where(t=>t.name==name).ToArray();
          if(matches.Length!=1)
            throw new InvalidOperationException($"Grocery stock node must exist exactly once: {name} (found {matches.Length})");
          stages[n-1]=matches[0].gameObject;expected.Add(name);
        }
        _nodes.Add(food,stages);
      }
      var undeclared=transforms.Select(t=>t.name).Where(n=>n.StartsWith(Prefix)&&!expected.Contains(n)).ToArray();
      if(undeclared.Length>0)
        throw new InvalidOperationException("Grocery stock nodes for undeclared foods or stages: "+string.Join(", ",undeclared));
      HideAll();
    }

    public void OnEnterFinishedState() {
      _inventory=_shop.Inventory;
      if(_inventory==null)throw new InvalidOperationException("Grocery stock display found no grocery inventory");
      _inventory.InventoryStockChanged+=OnStockChanged;
      foreach(var food in _nodes.Keys)Show(food);
    }

    public void OnExitFinishedState() {
      if(_inventory!=null)_inventory.InventoryStockChanged-=OnStockChanged;
      _inventory=null;HideAll();
    }

    private void OnStockChanged(object sender,InventoryStockChangedEventArgs args) {
      var food=args.GoodAmount.GoodId;
      if(_nodes.ContainsKey(food))Show(food);
    }

    private void Show(string food) {
      var amount=_inventory.AmountInStock(food);
      var stages=_spec.Stages;
      var level=amount<=0?0:Math.Min(stages,(amount*stages+_store.CapacityPerFood-1)/_store.CapacityPerFood);
      var nodes=_nodes[food];
      for(int n=1;n<=stages;n++)nodes[n-1].SetActive(n<=level);
    }

    private void HideAll() {
      foreach(var nodes in _nodes.Values)
        foreach(var node in nodes)node.SetActive(false);
    }
  }

  [Context("Game")]
  public sealed class GroceryStockDisplayConfigurator : Configurator {
    protected override void Configure() {
      Bind<GroceryStockDisplay>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var b=new TemplateModule.Builder();
      b.AddDecorator<GroceryStockDisplaySpec,GroceryStockDisplay>();
      return b.Build();
    }
  }
}
