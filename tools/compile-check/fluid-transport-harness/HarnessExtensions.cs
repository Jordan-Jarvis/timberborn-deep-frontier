/// <summary>
/// Scenario areas in their own files (HarnessExtensions.&lt;Area&gt;.cs), so parallel work never edits Program.cs:
/// each area implements its partial method; an area without a file runs nothing.
/// </summary>
internal static partial class HarnessExtensions {
  internal static void Run(Action<bool, string> check, Action<string, Action> scenario, string managed, string specification, Dictionary<string, object> observations) {
    RunModdableFluids(check, scenario, managed, specification, observations);
    RunTides(check, scenario, managed, specification, observations);
    RunDeepFrontier(check, scenario, managed, specification, observations);
    RunMoreFluids(check, scenario, managed, specification, observations);
  }
  static partial void RunModdableFluids(Action<bool, string> check, Action<string, Action> scenario, string managed, string specification, Dictionary<string, object> observations);
  static partial void RunTides(Action<bool, string> check, Action<string, Action> scenario, string managed, string specification, Dictionary<string, object> observations);
  static partial void RunDeepFrontier(Action<bool, string> check, Action<string, Action> scenario, string managed, string specification, Dictionary<string, object> observations);
  static partial void RunMoreFluids(Action<bool, string> check, Action<string, Action> scenario, string managed, string specification, Dictionary<string, object> observations);
}
