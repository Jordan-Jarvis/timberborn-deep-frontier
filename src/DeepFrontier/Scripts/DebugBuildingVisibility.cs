#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using HarmonyLib;
using Timberborn.BuildingsUI;
using Timberborn.ModManagerScene;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // 1.1.2.8's developer command disables model GameObjects, taking native
  // TransformSlots/PatrollingSlots out of service without changing Enterable
  // reservations. Restaurant guests and charging bots can then crash on entry.
  // Replace only this command's two SetActive calls. Keep native selection of
  // finished/unfinished models and hide rendering, not simulation objects.
  //
  // No native alternative: BuildingsModelToggler has no hook between choosing
  // a model and activating it. Installed once at mod start; the hidden
  // renderers are kept per model GameObject in a weak table, so no scene owns
  // the patch and a scene change leaves nothing behind (the models die with
  // their scene).
  internal sealed class DebugBuildingVisibilityModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      DebugBuildingVisibility.Install();
      Debug.Log("[DeepFrontier] Debug building visibility hides rendering without disabling native slots (two 1.1.2.8 calls verified).");
    }
  }

  internal static class DebugBuildingVisibility {
    private const string Feature="Debug building visibility";
    private static MethodInfo _target;
    private static readonly ConditionalWeakTable<GameObject,List<(Renderer Renderer,bool WasForcedOff)>> Hidden=new();

    internal static void Install()=>NativePatches.Install("DeepFrontier.DebugBuildingVisibility",Verify,harmony=>
      harmony.Patch(_target,transpiler:new HarmonyMethod(typeof(DebugBuildingVisibility),nameof(ReplaceModelActivation))));

    private static void Verify() {
      _target=AccessTools.DeclaredMethod(typeof(BuildingsModelToggler),"ToggleBuildingModel")
        ??throw NativePatches.Changed(Feature,"BuildingsModelToggler.ToggleBuildingModel");
      var setActive=AccessTools.DeclaredMethod(typeof(GameObject),nameof(GameObject.SetActive),new[]{typeof(bool)});
      int calls=NativeIl.Callees(_target).Count(m=>m.Module==setActive.Module&&m.MetadataToken==setActive.MetadataToken);
      if(calls!=2)throw NativePatches.Changed(Feature,$"two GameObject.SetActive calls in BuildingsModelToggler.ToggleBuildingModel, found {calls}");
    }

    private static IEnumerable<CodeInstruction> ReplaceModelActivation(IEnumerable<CodeInstruction> instructions) {
      var code=instructions.ToList();
      var setActive=AccessTools.DeclaredMethod(typeof(GameObject),nameof(GameObject.SetActive),new[]{typeof(bool)});
      var replacement=AccessTools.DeclaredMethod(typeof(DebugBuildingVisibility),nameof(SetDebugVisibility));
      var calls=code.Where(i=>i.Calls(setActive)).ToList();
      if(calls.Count!=2)throw new InvalidOperationException($"Debug building visibility contract changed: expected two SetActive calls, found {calls.Count}");
      foreach(var call in calls) {call.opcode=OpCodes.Call;call.operand=replacement;}
      return code;
    }

    private static void SetDebugVisibility(GameObject model,bool visible) {
      if(visible) {
        // A building constructed while debug hiding was on was never hidden.
        if(Hidden.TryGetValue(model,out var previous)) {
          Restore(previous);Hidden.Remove(model);
        }
      } else {
        var previous=model.GetComponentsInChildren<Renderer>(true)
          .Select(r=>(Renderer:r,WasForcedOff:r.forceRenderingOff)).ToList();
        Hidden.Add(model,previous);
        foreach(var item in previous)item.Renderer.forceRenderingOff=true;
      }
    }

    private static void Restore(List<(Renderer Renderer,bool WasForcedOff)> previous) {
      foreach(var item in previous)if(item.Renderer)item.Renderer.forceRenderingOff=item.WasForcedOff;
    }
  }
}
#endif
