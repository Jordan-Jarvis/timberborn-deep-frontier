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
      HospitalMedicalSupplies.Verify();
      var harmony = new Harmony("DeepFrontier.HospitalMedicalSupplies");
      harmony.CreateClassProcessor(typeof(HospitalSupplyAvailability)).Patch();
      harmony.CreateClassProcessor(typeof(HospitalSupplyAcquisition)).Patch();
      harmony.CreateClassProcessor(typeof(HospitalSupplyConsumption)).Patch();
      harmony.CreateClassProcessor(typeof(HospitalMedicalEffects)).Patch();
      Debug.Log("[DeepFrontier] Hospital condition-specific medicine patches applied.");
    }
  }

  internal static class HospitalMedicalSupplies {
    internal static void Verify() {
      var type = typeof(GoodConsumingBuilding);
      foreach (var name in new[] { "CanUseInternal", "HasSupplies" })
        Require(AccessTools.Method(type, name, Type.EmptyTypes)?.ReturnType == typeof(bool), name);
      Require(AccessTools.Method(type, "ConsumeSupplies", Type.EmptyTypes)?.ReturnType == typeof(void), "ConsumeSupplies");
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
