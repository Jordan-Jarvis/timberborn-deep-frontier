#if !UNITY_EDITOR
using System.Collections.Generic;
using Bindito.Core;
using ConveyorBelt.Algorithm;
using ConveyorBelt.Models;
using Timberborn.BaseComponentSystem;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.TemplateInstantiation;

namespace DeepFrontier.Scripts {
  // The dependency's generic target reads IsOutput, not PublicOutput.
  // A grocery therefore owns an explicit intake-only belt connection.
  public sealed class GroceryBeltIntake : BaseComponent,IAwakableComponent,IBeltConnectionProvider {
    private FoodIntake _intake;
    public int Priority=>100;
    public void Awake() {_intake=new FoodIntake(GetComponent<GroceryStore>());}
    public bool TryProvide(BeltApproach approach,SimBelt upstream,out ISimLink link) {
      link=upstream!=null&&upstream.Plain ? _intake : SimLinks.None;
      return true;
    }
    private sealed class FoodIntake : ISimLink,ISimTarget {
      private readonly GroceryStore _shop;
      public FoodIntake(GroceryStore shop) {_shop=shop;}
      public bool CanAccept(string goodId) {
        var inventory=_shop.Inventory;
        return _shop.Enabled&&inventory.Enabled&&inventory.IsInput&&inventory.Takes(goodId)
          &&inventory.HasUnreservedCapacity(new GoodAmount(goodId,1));
      }
      public bool CanTarget(string goodId)=>CanAccept(goodId);
      public bool TryGetTarget(string goodId,out ISimTarget target) {
        target=this;return CanAccept(goodId);
      }
      public bool TryAccept(string goodId,float leftoverHours,float spentHours) {
        if(!CanAccept(goodId))return false;
        _shop.Inventory.GiveExisting(new GoodAmount(goodId,1));return true;
      }
      public void Commit() {}
      public void CollectDownstream(List<SimBelt> into) {}
    }
  }
  [Context("Game")]
  public sealed class GroceryBeltIntakeConfigurator : Configurator {
    protected override void Configure() {
      Bind<GroceryBeltIntake>().AsTransient();
      MultiBind<TemplateModule>().ToProvider<ModuleProvider>().AsSingleton();
    }
    private sealed class ModuleProvider : IProvider<TemplateModule> {
      public TemplateModule Get() {
        var builder=new TemplateModule.Builder();
        builder.AddDecorator<GroceryStoreSpec,GroceryBeltIntake>();
        return builder.Build();
      }
    }
  }
}
#endif
