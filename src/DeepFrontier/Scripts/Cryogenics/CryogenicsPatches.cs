#if !UNITY_EDITOR
using HarmonyLib;
using Timberborn.InventorySystem;
using Timberborn.ModManagerScene;
using UnityEngine;

namespace DeepFrontier.Scripts.Cryogenics {
  // Every IModStarter in the mod assembly is started (ModCodeStarter,
  // 1.1.2.8), so this patch registers without touching DeepFrontierModStarter.
  internal sealed class CryogenicsModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      new Harmony("DeepFrontier.Cryogenics").CreateClassProcessor(typeof(CryogenicIntakeGatePatch)).Patch();
      Debug.Log("[DeepFrontier] Cryogenic intake gate patch applied (InventoryInitializer.Initialize).");
    }
  }

  // Extension gap: native 1.1.2.8 StockpileInventoryInitializer hands the
  // stockpile's SingleGoodAllower to InventoryInitializer as its only
  // IGoodDisallower. Just before InventoryInitializer.Initialize passes that
  // disallower to Inventory.Initialize, a stockpile carrying CryogenicTankSpec
  // gets CryogenicIntakeGate (which wraps the same SingleGoodAllower) instead.
  // Every other inventory is untouched. The private field _goodDisallower is
  // injected by name, so Harmony fails at patch time if 1.1.2.8 changes it.
  // Initialize is patched rather than the 7-byte AddGoodDisallower setter,
  // which Mono may inline into its caller.
  [HarmonyPatch(typeof(InventoryInitializer), nameof(InventoryInitializer.Initialize))]
  internal static class CryogenicIntakeGatePatch {
    private static void Prefix(ref IGoodDisallower ____goodDisallower) {
      if (!(____goodDisallower is SingleGoodAllower allower)) return;
      var spec = allower.GetComponent<CryogenicTankSpec>();
      if (spec == null) return;
      ____goodDisallower = CryogenicIntakeGate.Install(allower, spec);
    }
  }
}
#endif
