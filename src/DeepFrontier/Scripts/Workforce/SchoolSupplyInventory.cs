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
  // Why Harmony (Timberborn 1.1.2.8): a Technical School accepts only the
  // supplies of the profession it teaches (SpecialistSchool). Inventory takes
  // its IGoodDisallower once, in Initialize, and the school's inventory is
  // built by internal GoodConsumingBuildingInventoryInitializer.Initialize,
  // which passes none. A prefix builds the same inventory (same goods,
  // capacities and component name "GoodConsumingBuilding", so saved stock
  // loads unchanged) with the school as its disallower, for templates with
  // FrontierSpecialistSchoolSpec only; every other GoodConsumingBuilding runs
  // native code. Same pattern as HospitalPantryInventory, whose prefix never
  // matches a school. Verify() resolves every member first and throws if the
  // game changed them.
  internal sealed class SchoolSupplyInventoryModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      SchoolSupplyInventory.Verify();
      new Harmony(SchoolSupplyInventory.HarmonyId).CreateClassProcessor(typeof(SchoolSupplyInventory)).Patch();
      Debug.Log("[DeepFrontier] Technical School supply inventory patch applied (GoodConsumingBuildingInventoryInitializer.Initialize).");
    }
  }

  [HarmonyPatch(typeof(GoodConsumingBuildingInventoryInitializer), nameof(GoodConsumingBuildingInventoryInitializer.Initialize))]
  internal static class SchoolSupplyInventory {
    internal const string HarmonyId = "DeepFrontier.SchoolSupplyInventory";
    // Native component name (GoodConsumingBuildingInventoryInitializer.InventoryComponentName).
    private const string NativeInventoryName = "GoodConsumingBuilding";

    internal static void Verify() {
      var method = AccessTools.Method(typeof(GoodConsumingBuildingInventoryInitializer), nameof(GoodConsumingBuildingInventoryInitializer.Initialize),
        new[] { typeof(GoodConsumingBuilding), typeof(Inventory) });
      Require(method != null && method.ReturnType == typeof(void), "GoodConsumingBuildingInventoryInitializer.Initialize(GoodConsumingBuilding, Inventory) : void");
      Require(AccessTools.Field(typeof(GoodConsumingBuildingInventoryInitializer), "_inventoryInitializerFactory")?.FieldType == typeof(InventoryInitializerFactory),
        "GoodConsumingBuildingInventoryInitializer._inventoryInitializerFactory : InventoryInitializerFactory");
      Require(AccessTools.Field(typeof(GoodConsumingBuildingInventoryInitializer), "InventoryComponentName")?.GetValue(null) as string == NativeInventoryName,
        "GoodConsumingBuildingInventoryInitializer.InventoryComponentName == \"GoodConsumingBuilding\"");
      Require(AccessTools.Method(typeof(InventoryInitializer), nameof(InventoryInitializer.AddGoodDisallower), new[] { typeof(IGoodDisallower) }) != null,
        "InventoryInitializer.AddGoodDisallower(IGoodDisallower)");
      Require(AccessTools.Method(typeof(GoodConsumingBuilding), nameof(GoodConsumingBuilding.InitializeInventory), new[] { typeof(Inventory) }) != null,
        "GoodConsumingBuilding.InitializeInventory(Inventory)");
    }

    private static void Require(bool condition, string member) {
      if (!condition) throw new InvalidOperationException("Timberborn 1.1.2.8 contract changed: " + member);
    }

    // Native body (1.1.2.8) plus AddGoodDisallower.
    private static bool Prefix(GoodConsumingBuilding subject, Inventory decorator, InventoryInitializerFactory ____inventoryInitializerFactory) {
      var schoolSpec = subject.GetComponent<FrontierSpecialistSchoolSpec>();
      if (schoolSpec == null) return true;
      var school = subject.GetComponent<SpecialistSchool>();
      if (!school) throw new InvalidOperationException($"{subject.Name}: FrontierSpecialistSchoolSpec without its SpecialistSchool");
      var spec = subject.GetComponent<GoodConsumingBuildingSpec>();
      var goods = spec.ConsumedGoods.Select(good => new StorableGoodAmount(StorableGood.CreateAsGivable(good.GoodId),
        Mathf.CeilToInt(good.GoodPerHour * spec.FullInventoryWorkHours))).ToList();
      var initializer = ____inventoryInitializerFactory.Create(decorator, goods.Sum(g => g.Amount), NativeInventoryName);
      initializer.AddAllowedGoods(goods);
      initializer.AddGoodDisallower(school);
      initializer.Initialize();
      subject.InitializeInventory(decorator);
      return false;
    }
  }
}
#endif
