#if !UNITY_EDITOR
using System;
using HarmonyLib;
using Timberborn.Attractions;
using Timberborn.BehaviorSystem;
using Timberborn.ModManagerScene;
using Timberborn.NeedSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Native 1.1.2.8 AttractionNeedBehavior offers its building for every need
  // in the static AttractionSpec effect list (DistrictNeedBehaviorService
  // groups behaviors by those effects) whenever Attraction.IsUsable, and
  // MaxValueNeedsAreActive keeps a visitor until every SatisfyToMaxValue need
  // is full. Hospital supplies are per treatment (HospitalMedicalSupplies), so
  // the ward stays usable while one treatment's supply is out: without these
  // postfixes, beavers needing only that treatment (decontamination without
  // Extract, radiation care without Medicine) were drawn away from other care
  // and held, untreated, in its thirty beds. The hospital neither offers
  // itself to a beaver with no condition it can treat now nor keeps a patient
  // for unsupplied treatments alone; every native rule is otherwise unchanged.
  internal sealed class HospitalMedicalVisitsModStarter : IModStarter {
    public void StartMod(IModEnvironment environment) {
      NativePatches.Install("DeepFrontier.HospitalMedicalVisits", Verify, typeof(HospitalMedicalOffer), typeof(HospitalMedicalStay));
      Debug.Log("[DeepFrontier] Hospital medical-visit patches applied (AttractionNeedBehavior.ActionPosition, MaxValueNeedsAreActive).");
    }

    private static void Verify() {
      var type = typeof(AttractionNeedBehavior);
      Require(AccessTools.DeclaredMethod(type, nameof(AttractionNeedBehavior.ActionPosition), new[] { typeof(NeedManager) })?.ReturnType == typeof(Vector3?),
        "AttractionNeedBehavior.ActionPosition(NeedManager)");
      var stay = AccessTools.DeclaredMethod(type, "MaxValueNeedsAreActive", new[] { typeof(BehaviorAgent) });
      Require(stay?.ReturnType == typeof(bool), "AttractionNeedBehavior.MaxValueNeedsAreActive(BehaviorAgent)");
      // A private callee small enough for Mono to inline would bypass the postfix.
      Require(!NativeIl.Inlinable(stay), "AttractionNeedBehavior.MaxValueNeedsAreActive is small enough to be inlined");
    }

    private static void Require(bool condition, string member) {
      if (!condition) throw new InvalidOperationException("Timberborn 1.1.2.8 hospital visit contract changed: " + member);
    }
  }

  [HarmonyPatch(typeof(AttractionNeedBehavior), nameof(AttractionNeedBehavior.ActionPosition))]
  internal static class HospitalMedicalOffer {
    private static void Postfix(AttractionNeedBehavior __instance, NeedManager needManager, ref Vector3? __result) {
      if (!__result.HasValue) return;
      var hospital = __instance.GetComponent<Hospital>();
      if (hospital && !hospital.HasTreatableNeed(needManager)) __result = null;
    }
  }

  // true releases the visitor on its next decision (native Decide).
  [HarmonyPatch(typeof(AttractionNeedBehavior), "MaxValueNeedsAreActive")]
  internal static class HospitalMedicalStay {
    private static void Postfix(AttractionNeedBehavior __instance, BehaviorAgent agent, ref bool __result) {
      if (__result) return;
      var hospital = __instance.GetComponent<Hospital>();
      if (hospital && !hospital.HasTreatableNeed(agent.GetComponent<NeedManager>())) __result = true;
    }
  }
}
#endif
