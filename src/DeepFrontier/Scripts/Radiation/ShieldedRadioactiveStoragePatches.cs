#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.ModManagerScene;
using Timberborn.Stockpiles;

namespace DeepFrontier.Scripts.Radiation {
  internal sealed class ShieldedRadioactiveStorageModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) =>
      NativePatches.Install("DeepFrontier.ShieldedRadioactiveStorage", Verify, typeof(ShieldedStorageInventoryPatch), typeof(ShieldedStorageSelectionPatch));

    // Every private field the two patches bind by name, and their targets.
    private static void Verify() {
      const string feature = "Shielded radioactive storage";
      var initializer = typeof(InventoryInitializer);
      NativeMember.NotInlined(feature, NativeMember.Method(feature, initializer, nameof(InventoryInitializer.Initialize), typeof(void)));
      NativeMember.Field(feature, initializer, "_inventory", typeof(Inventory));
      NativeMember.Field(feature, initializer, "_storableGoodAmounts", typeof(List<StorableGoodAmount>));
      NativeMember.Field(feature, initializer, "_capacity", typeof(int));
      NativeMember.Field(feature, initializer, "_componentName", typeof(string));
      var dropdown = ShieldedStorageSelectionPatch.Target();
      NativeMember.Field(feature, dropdown.DeclaringType, "_inventory", typeof(Inventory));
      NativeMember.Field(feature, dropdown.DeclaringType, "_items", typeof(List<string>));
    }
  }

  // Native StockpileInventoryInitializer only selects by GoodType and offers
  // no per-template goods hook. Author the inventory before initialization;
  // neither its SingleGoodAllower nor the cryogenic intake gate is replaced.
  [HarmonyPatch(typeof(InventoryInitializer), nameof(InventoryInitializer.Initialize))]
  internal static class ShieldedStorageInventoryPatch {
    private static void Prefix(Inventory ____inventory, List<StorableGoodAmount> ____storableGoodAmounts,
        int ____capacity, string ____componentName) {
      var stockpile = ____inventory.GetComponent<StockpileSpec>();
      if (stockpile == null) return;
      if (____componentName != "Stockpile") return;
      ShieldedRadioactiveStorage.Configure(____storableGoodAmounts,
        ____inventory.GetComponent<ShieldedRadioactiveStorageSpec>() != null, ____capacity);
    }
  }

  // Native picker includes output-only goods too. Hide radioactive water where
  // it cannot be delivered; the saved contents remain in the inventory panel.
  [HarmonyPatch]
  internal static class ShieldedStorageSelectionPatch {
    internal static MethodBase Target() => AccessTools.Method(
      "Timberborn.StockpilesUI.StockpileDropdownProvider:InitializeEntity")
      ?? throw new InvalidOperationException("Timberborn 1.1 StockpileDropdownProvider.InitializeEntity missing");

    private static MethodBase TargetMethod() => Target();

    private static void Postfix(Inventory ____inventory, List<string> ____items) {
      if (!____inventory.Takes(RadiationTuning.SludgeGoodId))
        ____items.Remove(RadiationTuning.SludgeGoodId);
    }
  }
}
#endif
