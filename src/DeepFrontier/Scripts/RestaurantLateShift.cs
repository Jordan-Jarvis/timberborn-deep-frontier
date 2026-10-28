#if !UNITY_EDITOR
using HarmonyLib;
using Timberborn.TimeSystem;
using Timberborn.WorkSystem;

namespace DeepFrontier.Scripts {
  // Beavers dine in their free time: during working hours native beavers leave
  // work only for critical needs. Restaurant staff therefore work late: their
  // shift starts with the colony's working hours and runs on for half of the
  // off-work time (16 h working hours: 4 h more), leaving the rest of the
  // night for sleep. Only WorkerWorkingHours.AreWorkingHours changes, the
  // native value WorkerRootBehavior and Restaurant.StaffOnDuty read; bots,
  // which ignore working hours, are unchanged.
  [HarmonyPatch(typeof(WorkerWorkingHours),nameof(WorkerWorkingHours.AreWorkingHours),MethodType.Getter)]
  internal static class RestaurantLateShift {
    private static readonly AccessTools.FieldRef<WorkerWorkingHours,WorkingHoursManager> Manager=
      AccessTools.FieldRefAccess<WorkerWorkingHours,WorkingHoursManager>("_workingHoursManager");
    private static readonly AccessTools.FieldRef<WorkingHoursManager,IDayNightCycle> Clock=
      AccessTools.FieldRefAccess<WorkingHoursManager,IDayNightCycle>("_dayNightCycle");

    // Called once per process from DeepFrontierModStarter.
    internal static void Apply()=>new Harmony("DeepFrontier.RestaurantLateShift").CreateClassProcessor(typeof(RestaurantLateShift)).Patch();

    private static void Postfix(WorkerWorkingHours __instance,ref bool __result) {
      if(__result)return;
      var workplace=__instance.GetComponent<Worker>().Workplace;
      if(!workplace||!workplace.GetComponent<Restaurant>())return;
      __result=IsLateShift(Manager(__instance));
    }

    // Native WorkingHoursManager.AreWorkingHours, with the end moved later by half the off-work time.
    internal static bool IsLateShift(WorkingHoursManager manager) {
      float working=manager.WorkedPartOfDay*24f;
      if(working<=0f)return false;
      float end=manager.EndHours,start=end-working,hour=Clock(manager).HoursPassedToday;
      return hour>=start&&hour<end+(24f-working)/2f;
    }
  }
}
#endif
