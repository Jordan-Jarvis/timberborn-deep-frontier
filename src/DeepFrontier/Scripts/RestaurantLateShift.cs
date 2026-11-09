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
  // The getter is 22 IL bytes, above the Mono inline limit of 20; Verify
  // keeps it there, so callers cannot inline past the postfix.
  [HarmonyPatch(typeof(WorkerWorkingHours),nameof(WorkerWorkingHours.AreWorkingHours),MethodType.Getter)]
  internal static class RestaurantLateShift {
    private const string Feature="Restaurant late shift";
    // 1.1.2.8 WorkingHoursManager.AreWorkingHours, which IsLateShift extends.
    private const string ManagerHoursIl="30a6f14c866b0828c34caf0d63c9980c28e8a70a4f568e15e47676a73d0f463f";
    // Resolved by Verify at mod start, before the postfix can run.
    private static AccessTools.FieldRef<WorkerWorkingHours,WorkingHoursManager> Manager;
    private static AccessTools.FieldRef<WorkingHoursManager,IDayNightCycle> Clock;

    // Called once per process from DeepFrontierModStarter.
    internal static void Apply()=>NativePatches.Install("DeepFrontier.RestaurantLateShift",Verify,typeof(RestaurantLateShift));

    private static void Verify() {
      var getter=AccessTools.PropertyGetter(typeof(WorkerWorkingHours),nameof(WorkerWorkingHours.AreWorkingHours))
        ??throw NativePatches.Changed(Feature,"WorkerWorkingHours.AreWorkingHours getter");
      NativeMember.NotInlined(Feature,getter);
      NativeMember.Field(Feature,typeof(WorkerWorkingHours),"_workingHoursManager",typeof(WorkingHoursManager));
      NativeMember.Field(Feature,typeof(WorkingHoursManager),"_dayNightCycle",typeof(IDayNightCycle));
      NativeIl.RequireBody(Feature,AccessTools.PropertyGetter(typeof(WorkingHoursManager),nameof(WorkingHoursManager.AreWorkingHours)),ManagerHoursIl);
      Manager=AccessTools.FieldRefAccess<WorkerWorkingHours,WorkingHoursManager>("_workingHoursManager");
      Clock=AccessTools.FieldRefAccess<WorkingHoursManager,IDayNightCycle>("_dayNightCycle");
    }

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
