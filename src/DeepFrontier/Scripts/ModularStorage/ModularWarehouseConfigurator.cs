using Bindito.Core;
using Timberborn.Emptying;
using Timberborn.EntityPanelSystem;
using Timberborn.InventoryNeedSystem;
using Timberborn.TemplateInstantiation;

namespace DeepFrontier.Scripts.ModularStorage {
  // Native decorators a warehouse gets from GameStockpilesConfigurator
  // (decompiled 1.1.2.8), on the ModularWarehouse core instead of Stockpile:
  // - Emptiable: the inventory's IInventoryValidator for native deliveries
  //   (DistrictInventoryPicker.InventoryIsTaking); EmptyingConfigurator then adds
  //   HaulCandidate (with HaulPrioritizable, the native haul-priority toggle),
  //   EmptiableHaulBehaviorProvider and UnwantedStockHaulBehaviorProvider;
  // - EmptyInventoriesWorkplaceBehavior and RemoveUnwantedStockWorkplaceBehavior,
  //   the behaviors those providers offer (Empty slots and leftovers are native
  //   unwanted stock; laborers also carry it out through the district registry);
  // - InventoryNeedBehavior: beavers use needs goods stored here;
  // plus the Obtain and Supply behaviors and providers of the slots.
  // Modules get only their WarehouseModule component; the network is a singleton.
  [Context("Game")]
  public sealed class ModularWarehouseConfigurator : Configurator {
    protected override void Configure() {
      Bind<ModularWarehouse>().AsTransient();
      Bind<WarehouseModule>().AsTransient();
      Bind<ModularWarehouseObtainBehavior>().AsTransient();
      Bind<ModularWarehouseSupplyBehavior>().AsTransient();
      Bind<ModularWarehouseObtainHaulProvider>().AsTransient();
      Bind<ModularWarehouseSupplyHaulProvider>().AsTransient();
      Bind<ModularWarehouseInventoryInitializer>().AsSingleton();
      Bind<ModularWarehouseNetwork>().AsSingleton();
      Bind<ModularWarehouseFragment>().AsSingleton();
      Bind<WarehouseSlotViewFactory>().AsSingleton();
      Bind<WarehouseGoodSelectionBoxFactory>().AsSingleton();
      MultiBind<TemplateModule>().ToProvider<TemplateModuleProvider>().AsSingleton();
      MultiBind<EntityPanelModule>().ToProvider<EntityPanelModuleProvider>().AsSingleton();
    }

    private sealed class TemplateModuleProvider : IProvider<TemplateModule> {
      private readonly ModularWarehouseInventoryInitializer _inventory;
      public TemplateModuleProvider(ModularWarehouseInventoryInitializer inventory) { _inventory = inventory; }

      public TemplateModule Get() {
        var builder = new TemplateModule.Builder();
        builder.AddDecorator<ModularWarehouseSpec, ModularWarehouse>();
        builder.AddDedicatedDecorator(_inventory);
        builder.AddDecorator<ModularWarehouse, Emptiable>();
        builder.AddDecorator<ModularWarehouse, EmptyInventoriesWorkplaceBehavior>();
        builder.AddDecorator<ModularWarehouse, RemoveUnwantedStockWorkplaceBehavior>();
        builder.AddDecorator<ModularWarehouse, InventoryNeedBehavior>();
        builder.AddDecorator<ModularWarehouse, ModularWarehouseObtainBehavior>();
        builder.AddDecorator<ModularWarehouse, ModularWarehouseObtainHaulProvider>();
        builder.AddDecorator<ModularWarehouse, ModularWarehouseSupplyBehavior>();
        builder.AddDecorator<ModularWarehouse, ModularWarehouseSupplyHaulProvider>();
        builder.AddDecorator<WarehouseModuleSpec, WarehouseModule>();
        return builder.Build();
      }
    }

    // Where the native StockpileInventoryFragment sits (StockpilesUIConfigurator).
    private sealed class EntityPanelModuleProvider : IProvider<EntityPanelModule> {
      private readonly ModularWarehouseFragment _fragment;
      public EntityPanelModuleProvider(ModularWarehouseFragment fragment) { _fragment = fragment; }

      public EntityPanelModule Get() {
        var builder = new EntityPanelModule.Builder();
        builder.AddBottomFragment(_fragment);
        return builder.Build();
      }
    }
  }
}
