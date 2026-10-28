#if !UNITY_EDITOR
using System;
using System.Reflection;
using HarmonyLib;
using Timberborn.DeteriorationSystem;
using Timberborn.GameDistricts;
using Timberborn.ModManagerScene;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Every IModStarter in the mod assembly is started (ModCodeStarter,
  // 1.1.2.8), so the workforce patches register here without touching the
  // shared DeepFrontierModStarter.
  internal sealed class WorkforceModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      var harmony=new Harmony("DeepFrontier.Workforce");
      harmony.CreateClassProcessor(typeof(BotWearDeteriorationPatch)).Patch();
      harmony.CreateClassProcessor(typeof(SpecialistWorkplaceRegistrationPatch)).Patch();
      harmony.CreateClassProcessor(typeof(SpecialistWorkplaceUnregistrationPatch)).Patch();
      Debug.Log("[DeepFrontier] Workforce risk patches applied (bot wear, specialist staffing).");
    }
  }

  // Deteriorable has no rate API (see BotWear). Fields are injected by name,
  // so the 1.1.2.8 private fields _currentDeterioration/_fixedDeltaTimeInDays
  // must exist or Harmony fails at patch time.
  [HarmonyPatch(typeof(Deteriorable),nameof(Deteriorable.Tick))]
  internal static class BotWearDeteriorationPatch {
    private static void Prefix(Deteriorable __instance,ref float ____currentDeterioration,float ____fixedDeltaTimeInDays) {
      if(____currentDeterioration<=0f)return;
      var wear=__instance.GetComponent<BotWear>();
      if(!wear||!wear.Wearing)return;
      ____currentDeterioration=Mathf.Max(0f,____currentDeterioration-____fixedDeltaTimeInDays*(wear.Multiplier-1f));
    }
  }

  // Specialist-only workplaces are staffed by SpecialistStaffing, never by
  // the native district assigner. The native assigner (internal
  // DistrictWorkplaceAssigner, 1.1.2.8) only knows worker types; left
  // registered it would hire any beaver into them and move their crews to
  // higher-priority ordinary jobs. Skipping both registration and
  // unregistration keeps its per-worker-type lists consistent.
  internal static class NativeWorkplaceAssigner {
    private const string TypeName="Timberborn.WorkSystem.DistrictWorkplaceAssigner";
    public static MethodBase Method(string name) {
      var type=AccessTools.TypeByName(TypeName)??throw new InvalidOperationException($"Workforce: {TypeName} not found; recheck the 1.1.2.8 contract");
      return AccessTools.Method(type,name)??throw new InvalidOperationException($"Workforce: {TypeName}.{name} not found; recheck the 1.1.2.8 contract");
    }
  }

  [HarmonyPatch]
  internal static class SpecialistWorkplaceRegistrationPatch {
    private static MethodBase TargetMethod()=>NativeWorkplaceAssigner.Method("OnFinishedBuildingRegistered");
    private static bool Prefix(FinishedBuildingRegisteredEventArgs finishedBuildingRegisteredEventArgs)=>
      !finishedBuildingRegisteredEventArgs.Building.GetComponent<SpecialistWorkplace>();
  }

  [HarmonyPatch]
  internal static class SpecialistWorkplaceUnregistrationPatch {
    private static MethodBase TargetMethod()=>NativeWorkplaceAssigner.Method("OnFinishedBuildingUnregistered");
    private static bool Prefix(FinishedBuildingUnregisteredEventArgs finishedBuildingUnregisteredEventArgs)=>
      !finishedBuildingUnregisteredEventArgs.Building.GetComponent<SpecialistWorkplace>();
  }
}
#endif
