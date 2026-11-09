#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using HarmonyLib;
using Timberborn.Attractions;
using Timberborn.Buildings;
using Timberborn.Effects;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.Goods;
using Timberborn.ModManagerScene;
using Timberborn.TimeSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Native 1.1.2.8 GoodConsumingBuilding has only whole-building consumption toggles.
  // Its CanUse gates every attraction effect, even while consumption is paused.
  // Hospital-only extension: medicine is optional for ordinary care, and is consumed
  // only for admitted contamination/radiation cases. Keep the native inventory,
  // supply order, fractional-dose list, save format, hauling and stock UI unchanged.
  internal sealed class HospitalMedicalSuppliesModStarter : IModStarter {
    public void StartMod(IModEnvironment environment) {
      NativePatches.Install("DeepFrontier.HospitalMedicalSupplies", HospitalMedicalSupplies.Verify,
        typeof(HospitalSupplyAvailability), typeof(HospitalSupplyAcquisition), typeof(HospitalSupplyConsumption), typeof(HospitalMedicalEffects));
      Debug.Log("[DeepFrontier] Hospital condition-specific medicine patches applied.");
    }
  }

  internal static class HospitalMedicalSupplies {
    // 1.1.2.8 bodies the hospital prefixes replace (for Hospitals only).
    private static readonly (string Method, string Sha256)[] ReplacedIl = {
      ("CanUseInternal", "f61735c92b0266cee9b95ba72e6d75e8d8fae19bbbb31a09461487426a9273d1"),
      ("HasSupplies", "efef6905eb4b18ca4293f645aa36520ee8f1739b3c1fda9b79d0e64d11edb0ac"),
      ("ConsumeSupplies", "2d59876335e72cf7be5c43db15a3f197febdd18dc43d92b01a748b30d8e64a67"),
    };
    private const string EffectsIl = "a518660aa4bdf982609fc84000f22d96f54141959c006a18aa2dc49dc1996931";

    internal static void Verify() {
      var type = typeof(GoodConsumingBuilding);
      foreach (var name in new[] { "CanUseInternal", "HasSupplies" })
        Require(AccessTools.Method(type, name, Type.EmptyTypes)?.ReturnType == typeof(bool), name);
      Require(AccessTools.Method(type, "ConsumeSupplies", Type.EmptyTypes)?.ReturnType == typeof(void), "ConsumeSupplies");
      foreach (var (name, sha) in ReplacedIl) NativeIl.RequireBody("Hospital medical supplies", AccessTools.Method(type, name, Type.EmptyTypes), sha);
      NativeIl.RequireBody("Hospital medical supplies", AccessTools.Method(typeof(Attraction), nameof(Attraction.GetEfficiencyAdjustedEffects),
        new[] { typeof(List<ContinuousEffect>) }), EffectsIl);
      Require(AccessTools.Field(type, "_suppliesLeft")?.FieldType == typeof(List<float>), "_suppliesLeft");
      Require(AccessTools.Field(type, "_dayNightCycle")?.FieldType == typeof(IDayNightCycle), "_dayNightCycle");
      Require(AccessTools.Method(typeof(Attraction), nameof(Attraction.GetEfficiencyAdjustedEffects),
        new[] { typeof(List<ContinuousEffect>) })?.ReturnType == typeof(void), "Attraction.GetEfficiencyAdjustedEffects");
      Require(AccessTools.Field(typeof(Attraction), "_efficiencyProviders")?.FieldType == typeof(List<IBuildingEfficiencyProvider>),
        "Attraction._efficiencyProviders");
    }
    private static void Require(bool condition, string member) {
      if (!condition) throw new InvalidOperationException("Timberborn 1.1.2.8 hospital supply contract changed: " + member);
    }
  }

  [HarmonyPatch(typeof(GoodConsumingBuilding), "CanUseInternal")]
  internal static class HospitalSupplyAvailability {
    private static bool Prefix(GoodConsumingBuilding __instance, List<float> ____suppliesLeft, ref bool __result) {
      if (!__instance.GetComponent<Hospital>()) return true;
      __result = true;
      for (int i = 0; i < __instance.ConsumedGoods.Length; i++) {
        var good = __instance.ConsumedGoods[i];
        if (good.GoodId != Hospital.MedicineGoodId && ____suppliesLeft[i] <= 0
            && __instance.Inventory.UnreservedAmountInStock(good.GoodId) == 0) __result = false;
      }
      return false;
    }
  }

  [HarmonyPatch(typeof(GoodConsumingBuilding), "HasSupplies")]
  internal static class HospitalSupplyAcquisition {
    private static bool Prefix(GoodConsumingBuilding __instance, List<float> ____suppliesLeft, ref bool __result) {
      var hospital = __instance.GetComponent<Hospital>();
      if (!hospital) return true;
      __result = __instance.CanUse;
      if (!__result) return false;
      var medicalPatients = hospital.CanUse && hospital.HasMedicalPatients;
      for (int i = 0; i < __instance.ConsumedGoods.Length; i++) {
        var good = __instance.ConsumedGoods[i];
        if (____suppliesLeft[i] > 0) continue;
        if (good.GoodId == Hospital.MedicineGoodId && (!medicalPatients
            || __instance.Inventory.UnreservedAmountInStock(good.GoodId) == 0)) continue;
        __instance.Inventory.TakeConsumed(new GoodAmount(good.GoodId, 1));
        ____suppliesLeft[i] = 1;
      }
      return false;
    }
  }

  [HarmonyPatch(typeof(GoodConsumingBuilding), "ConsumeSupplies")]
  internal static class HospitalSupplyConsumption {
    private static bool Prefix(GoodConsumingBuilding __instance, List<float> ____suppliesLeft, IDayNightCycle ____dayNightCycle) {
      var hospital = __instance.GetComponent<Hospital>();
      if (!hospital) return true;
      if (!__instance.IsConsuming) return false;
      var medicalPatients = hospital.CanProvideMedicalTreatment && hospital.HasMedicalPatients;
      for (int i = 0; i < __instance.ConsumedGoods.Length; i++) {
        var good = __instance.ConsumedGoods[i];
        if (good.GoodId == Hospital.MedicineGoodId && !medicalPatients) continue;
        ____suppliesLeft[i] -= ____dayNightCycle.FixedDeltaTimeInHours * good.GoodPerHour;
      }
      return false;
    }
  }

  [HarmonyPatch(typeof(Attraction), nameof(Attraction.GetEfficiencyAdjustedEffects))]
  internal static class HospitalMedicalEffects {
    private static bool Prefix(Attraction __instance, List<ContinuousEffect> continuousEffects,
        List<IBuildingEfficiencyProvider> ____efficiencyProviders) {
      var hospital = __instance.GetComponent<Hospital>();
      if (!hospital) return true;
      float efficiency = 1;
      foreach (var provider in ____efficiencyProviders) efficiency *= provider.Efficiency;
      var medicalCare = hospital.CanProvideMedicalTreatment;
      foreach (var effect in __instance.Effects) {
        if (Hospital.NeedsMedicineFor(effect.NeedId) && !medicalCare) continue;
        continuousEffects.Add(new ContinuousEffect(effect.NeedId, effect.PointsPerHour * efficiency));
      }
      return false;
    }
  }
}
#endif
