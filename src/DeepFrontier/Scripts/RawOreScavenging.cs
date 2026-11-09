#if !UNITY_EDITOR
using System.Reflection;
using HarmonyLib;
using Timberborn.BaseComponentSystem;
using Timberborn.Ruins;
using Timberborn.Yielding;

namespace DeepFrontier.Scripts {
  // Native scavenging already handles walking, reservations, extraction,
  // carrying and output storage. Its retriever accepts only Ruin components;
  // extend that one selection point for our ore outcrop, leaving stone pits alone.
  // No native alternative (Timberborn 1.1.2.8): RuinsConfigurator decorates
  // ScavengerYielderRetriever on ScavengerSpec and InRangeYielders reads the
  // single IYielderRetriever with GetComponent, so a second retriever on the
  // Scavenger Flag cannot be added. The target is reached through the
  // IYielderRetriever interface (never inlined).
  [HarmonyPatch]
  internal static class RawOreScavenging {
    private const string Feature = "Raw ore scavenging";
    private const string RetrieverType = "Timberborn.Ruins.ScavengerYielderRetriever";

    internal static void Apply() {
      NativePatches.Install("DeepFrontier.RawOreScavenging", Verify, typeof(RawOreScavenging));
      UnityEngine.Debug.Log("[DeepFrontier] Scavenger Flag raw-ore selection enabled.");
    }

    private static void Verify() {
      var target = Target();
      NativeMember.Parameters(Feature, target, "component", "yielder");
      if (!typeof(IYielderRetriever).IsAssignableFrom(target.DeclaringType)) throw NativePatches.Changed(Feature, RetrieverType + " : IYielderRetriever");
    }

    private static MethodInfo Target() => NativeMember.Method(Feature, NativeMember.Type(Feature, typeof(Ruin), RetrieverType), "TryGetYielder",
      typeof(bool), typeof(BaseComponent), typeof(Yielder).MakeByRefType());

    private static MethodBase TargetMethod() => Target();

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
