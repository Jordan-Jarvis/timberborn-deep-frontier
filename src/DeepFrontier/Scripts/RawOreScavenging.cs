#if !UNITY_EDITOR
using System;
using System.Reflection;
using HarmonyLib;
using Timberborn.BaseComponentSystem;
using Timberborn.Yielding;

namespace DeepFrontier.Scripts {
  // Native scavenging already handles walking, reservations, extraction,
  // carrying and output storage. Its retriever accepts only Ruin components;
  // extend that one selection point for our ore outcrop, leaving stone pits alone.
  [HarmonyPatch]
  internal static class RawOreScavenging {
    internal static void Apply() {
      new Harmony("DeepFrontier.RawOreScavenging").CreateClassProcessor(typeof(RawOreScavenging)).Patch();
      UnityEngine.Debug.Log("[DeepFrontier] Scavenger Flag raw-ore selection enabled.");
    }
    private static MethodBase TargetMethod() =>
      AccessTools.Method("Timberborn.Ruins.ScavengerYielderRetriever:TryGetYielder")
      ?? throw new MissingMethodException("Timberborn.Ruins.ScavengerYielderRetriever.TryGetYielder");

    private static void Postfix(BaseComponent component, ref Yielder yielder, ref bool __result) {
      if (__result) return;
      var deposit = component.GetComponent<MineralDeposit>();
      if (!deposit || deposit.Spec.GoodId != "RawDeepOre") return;
      yielder = deposit.Yielder;
      __result = true;
    }
  }
}
#endif
