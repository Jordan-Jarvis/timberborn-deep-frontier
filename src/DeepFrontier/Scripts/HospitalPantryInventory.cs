#if !UNITY_EDITOR
using System;
using System.Linq;
using HarmonyLib;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.ModManagerScene;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Why Harmony (Timberborn 1.1.2.8): a Hospital must keep exactly one
  // enabled Inventory (see HospitalPantry), so its patient foods and water
  // join the native GoodConsumingBuilding inventory. That inventory is built
  // by internal GoodConsumingBuildingInventoryInitializer.Initialize from
  // GoodConsumingBuildingSpec.ConsumedGoods only, with no extension point,
  // and Inventory takes its allowed goods once, in Initialize. A prefix builds
  // the same inventory (same component name "GoodConsumingBuilding", so saved
  // supplies load unchanged) with the patient goods added, for templates with
  // HospitalPantrySpec only; every other GoodConsumingBuilding runs native
  // code. Same pattern as RestaurantKitchenInventory. Verify() resolves every
  // member first and throws if the game changed them.
  internal sealed class HospitalPantryModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      NativePatches.Install(HospitalPantryInventory.HarmonyId, HospitalPantryInventory.Verify, typeof(HospitalPantryInventory));
      Debug.Log("[DeepFrontier] Hospital patient-meal inventory patch applied (GoodConsumingBuildingInventoryInitializer.Initialize).");
    }
  }

  [HarmonyPatch(typeof(GoodConsumingBuildingInventoryInitializer), nameof(GoodConsumingBuildingInventoryInitializer.Initialize))]
  internal static class HospitalPantryInventory {
    internal const string HarmonyId = "DeepFrontier.HospitalPantryInventory";
    // Native component name (GoodConsumingBuildingInventoryInitializer.InventoryComponentName).
    private const string NativeInventoryName = "GoodConsumingBuilding";
    private static readonly AccessTools.FieldRef<InventoryInitializerFactory, IGoodService> FactoryGoods =
      AccessTools.FieldRefAccess<InventoryInitializerFactory, IGoodService>("_goodService");

    // 1.1.2.8 GoodConsumingBuildingInventoryInitializer.Initialize, the body the
    // prefix rebuilds (shared with SchoolSupplyInventory).
    internal const string InitializeIl = "c6235334fa3a6242b4fb5d2c4622b1598a3a7cf165afbebfcbc3755f69cb7dec";

    internal static void Verify() {
      var method = AccessTools.Method(typeof(GoodConsumingBuildingInventoryInitializer), nameof(GoodConsumingBuildingInventoryInitializer.Initialize),
        new[] { typeof(GoodConsumingBuilding), typeof(Inventory) });
      Require(method != null && method.ReturnType == typeof(void), "GoodConsumingBuildingInventoryInitializer.Initialize(GoodConsumingBuilding, Inventory) : void");
      NativeIl.RequireBody("Hospital pantry inventory", method, InitializeIl);
      Require(AccessTools.Field(typeof(GoodConsumingBuildingInventoryInitializer), "_inventoryInitializerFactory")?.FieldType == typeof(InventoryInitializerFactory),
        "GoodConsumingBuildingInventoryInitializer._inventoryInitializerFactory : InventoryInitializerFactory");
      Require(AccessTools.Field(typeof(GoodConsumingBuildingInventoryInitializer), "InventoryComponentName")?.GetValue(null) as string == NativeInventoryName,
        "GoodConsumingBuildingInventoryInitializer.InventoryComponentName == \"GoodConsumingBuilding\"");
      Require(AccessTools.Field(typeof(InventoryInitializerFactory), "_goodService")?.FieldType == typeof(IGoodService),
        "InventoryInitializerFactory._goodService : IGoodService");
      Require(AccessTools.Method(typeof(GoodConsumingBuilding), nameof(GoodConsumingBuilding.InitializeInventory), new[] { typeof(Inventory) }) != null,
        "GoodConsumingBuilding.InitializeInventory(Inventory)");
    }

    private static void Require(bool condition, string member) {
      if (!condition) throw new InvalidOperationException("Timberborn 1.1.2.8 contract changed: " + member);
    }

    private static bool Prefix(GoodConsumingBuilding subject, Inventory decorator, InventoryInitializerFactory ____inventoryInitializerFactory) {
      var pantry = subject.GetComponent<HospitalPantrySpec>();
      if (pantry == null) return true;
      var goods = HospitalPantry.InventoryGoods(subject.GetComponent<GoodConsumingBuildingSpec>(), pantry, FactoryGoods(____inventoryInitializerFactory));
      var initializer = ____inventoryInitializerFactory.Create(decorator, goods.Sum(g => g.Amount), NativeInventoryName);
      initializer.AddAllowedGoods(goods);
      initializer.Initialize();
      subject.InitializeInventory(decorator);
      return false;
    }
  }
}
#endif
