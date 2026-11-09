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
  // Native 1.1.2.8 GoodConsumingBuilding consumes every good of the building
  // together and its CanUse gates every attraction effect. A Hospital's
  // supplies are per treatment instead (Hospital.cs, HospitalSpec.
  // TreatmentSupplies; user 2026-11-09): injuries and chipped teeth need none,
  // decontamination consumes Extract and radiation care consumes Medicine.
  // Hospital-only replacements:
  //   CanUseInternal       the ward needs no supply to be usable;
  //   HasSupplies          a dose of a good is taken only while an admitted
  //                        patient needs its treatment;
  //   ConsumeSupplies      each loaded dose is used only while one does;
  //   effects              a treatment applies only while supplied;
  //   HoursUntilNoSupply   (postfix) hours of the supplies treatments in progress
  //                        use, so the native supply bar does not read 0 h
  //                        because a good no admitted patient needs is out.
  // The native inventory, consumed-goods order, fractional-dose list, save
  // format, hauling and stock UI stay native.
  internal sealed class HospitalMedicalSuppliesModStarter : IModStarter {
    public void StartMod(IModEnvironment environment) {
      NativePatches.Install("DeepFrontier.HospitalMedicalSupplies", HospitalMedicalSupplies.Verify,
        typeof(HospitalSupplyAvailability), typeof(HospitalSupplyAcquisition), typeof(HospitalSupplyConsumption),
        typeof(HospitalMedicalEffects), typeof(HospitalSupplyHours));
      Debug.Log("[DeepFrontier] Hospital per-treatment supply patches applied.");
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
      Require(AccessTools.Method(type, nameof(GoodConsumingBuilding.HoursUntilNoSupply), Type.EmptyTypes)?.ReturnType == typeof(float),
        "HoursUntilNoSupply");
      foreach (var (name, sha) in ReplacedIl) NativeIl.RequireBody("Hospital supplies", AccessTools.Method(type, name, Type.EmptyTypes), sha);
      NativeIl.RequireBody("Hospital supplies", AccessTools.Method(typeof(Attraction), nameof(Attraction.GetEfficiencyAdjustedEffects),
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

  // No supply is required for the ward to be usable; each treatment checks its own.
  [HarmonyPatch(typeof(GoodConsumingBuilding), "CanUseInternal")]
  internal static class HospitalSupplyAvailability {
    private static bool Prefix(GoodConsumingBuilding __instance, ref bool __result) {
      if (!__instance.GetComponent<Hospital>()) return true;
      __result = true;
      return false;
    }
  }

  // Native: an empty dose takes one unit of its good from stock. Here only for a
  // treatment an admitted patient needs, while the ward is open.
  [HarmonyPatch(typeof(GoodConsumingBuilding), "HasSupplies")]
  internal static class HospitalSupplyAcquisition {
    private static bool Prefix(GoodConsumingBuilding __instance, List<float> ____suppliesLeft, ref bool __result) {
      var hospital = __instance.GetComponent<Hospital>();
      if (!hospital) return true;
      __result = true;
      if (!hospital.CanUse) return false;
      for (int i = 0; i < __instance.ConsumedGoods.Length; i++) {
        if (____suppliesLeft[i] > 0) continue;
        var good = __instance.ConsumedGoods[i].GoodId;
        if (!hospital.SupplyInUse(i) || __instance.Inventory.UnreservedAmountInStock(good) == 0) continue;
        __instance.Inventory.TakeConsumed(new GoodAmount(good, 1));
        ____suppliesLeft[i] = 1;
      }
      return false;
    }
  }

  // Native: every dose is used at its hourly rate while consuming. Here a dose is
  // used only while an admitted patient needs its treatment.
  [HarmonyPatch(typeof(GoodConsumingBuilding), "ConsumeSupplies")]
  internal static class HospitalSupplyConsumption {
    private static bool Prefix(GoodConsumingBuilding __instance, List<float> ____suppliesLeft, IDayNightCycle ____dayNightCycle) {
      var hospital = __instance.GetComponent<Hospital>();
      if (!hospital) return true;
      if (!__instance.IsConsuming || !hospital.CanUse) return false;
      for (int i = 0; i < __instance.ConsumedGoods.Length; i++) {
        if (____suppliesLeft[i] <= 0 || !hospital.SupplyInUse(i)) continue;
        ____suppliesLeft[i] -= ____dayNightCycle.FixedDeltaTimeInHours * __instance.ConsumedGoods[i].GoodPerHour;
      }
      return false;
    }
  }

  // Native body with one change: an effect whose treatment is unsupplied is left out.
  [HarmonyPatch(typeof(Attraction), nameof(Attraction.GetEfficiencyAdjustedEffects))]
  internal static class HospitalMedicalEffects {
    private static bool Prefix(Attraction __instance, List<ContinuousEffect> continuousEffects,
        List<IBuildingEfficiencyProvider> ____efficiencyProviders) {
      var hospital = __instance.GetComponent<Hospital>();
      if (!hospital) return true;
      float efficiency = 1;
      foreach (var provider in ____efficiencyProviders) efficiency *= provider.Efficiency;
      var effects = __instance.Effects;
      for (int i = 0; i < effects.Count; i++) {
        var effect = effects[i];
        if (!hospital.TreatmentSupplied(effect.NeedId)) continue;
        continuousEffects.Add(new ContinuousEffect(effect.NeedId, effect.PointsPerHour * efficiency));
      }
      return false;
    }
  }

  // The native supply bar (GoodConsumingBuildingFragment) shows the hours until
  // the first good runs out. For a Hospital: the hours of the supplies that
  // treatments in progress use (a dose plus unreserved stock, at its rate); the
  // full working time while none is in use, since the ward then needs none.
  // A missing supply has its own status (Hospital).
  [HarmonyPatch(typeof(GoodConsumingBuilding), nameof(GoodConsumingBuilding.HoursUntilNoSupply))]
  internal static class HospitalSupplyHours {
    private static void Postfix(GoodConsumingBuilding __instance, List<float> ____suppliesLeft, ref float __result) {
      var hospital = __instance.GetComponent<Hospital>();
      if (!hospital) return;
      float hours = __instance.MaximumWorkingTime;
      for (int i = 0; i < __instance.ConsumedGoods.Length; i++) {
        if (!hospital.SupplyInUse(i) || !hospital.SupplyAvailable(i)) continue;
        var good = __instance.ConsumedGoods[i];
        float left = (__instance.Inventory.UnreservedAmountInStock(good.GoodId) + Mathf.Max(0f, ____suppliesLeft[i])) / good.GoodPerHour;
        if (left < hours) hours = left;
      }
      __result = hours;
    }
  }
}
#endif
