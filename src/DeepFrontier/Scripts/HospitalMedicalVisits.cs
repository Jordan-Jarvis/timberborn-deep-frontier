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
  // is full. Ordinary hospital care no longer requires medicine
  // (HospitalMedicalSupplies), so without medical treatment the ward stayed
  // usable for beavers needing only decontamination or radiation care: they
  // were drawn away from Decontamination Pods and held, untreated, in its
  // thirty beds. While the hospital cannot treat those needs it neither offers
  // itself to a beaver that has no ordinary-care need nor keeps a patient for
  // them; injury and tooth care, and every native rule, are unchanged.
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
      if (hospital && !hospital.CanProvideMedicalTreatment && !hospital.HasOrdinaryCareNeed(needManager)) __result = null;
    }
  }

  // true releases the visitor on its next decision (native Decide).
  [HarmonyPatch(typeof(AttractionNeedBehavior), "MaxValueNeedsAreActive")]
  internal static class HospitalMedicalStay {
    private static void Postfix(AttractionNeedBehavior __instance, BehaviorAgent agent, ref bool __result) {
      if (__result) return;
      var hospital = __instance.GetComponent<Hospital>();
      if (hospital && !hospital.CanProvideMedicalTreatment && !hospital.HasOrdinaryCareNeed(agent.GetComponent<NeedManager>())) __result = true;
    }
  }
}
#endif
