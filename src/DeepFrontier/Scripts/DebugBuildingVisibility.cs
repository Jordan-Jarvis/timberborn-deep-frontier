#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using Bindito.Core;
using HarmonyLib;
using Timberborn.BuildingsUI;
using Timberborn.SingletonSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class DebugBuildingVisibilityConfigurator : Configurator {
    protected override void Configure() { Bind<DebugBuildingVisibility>().AsSingleton(); }
  }

  // 1.1.2.8's developer command disables model GameObjects, taking native
  // TransformSlots/PatrollingSlots out of service without changing Enterable
  // reservations. Restaurant guests and charging bots can then crash on entry.
  // Replace only this command's two SetActive calls. Keep native selection of
  // finished/unfinished models and hide rendering, not simulation objects.
  internal sealed class DebugBuildingVisibility : ILoadableSingleton,IUnloadableSingleton {
    private const string Owner="DeepFrontier.DebugBuildingVisibility";
    private static readonly MethodInfo Target=AccessTools.DeclaredMethod(typeof(BuildingsModelToggler),"ToggleBuildingModel");
    private static DebugBuildingVisibility _current;
    private readonly Harmony _harmony=new(Owner);
    private readonly Dictionary<GameObject,List<(Renderer Renderer,bool WasForcedOff)>> _hidden=new();
    public void Load() {
      if(_current!=null)throw new InvalidOperationException("Debug building visibility already has a scene owner");
      if(Target==null)throw new MissingMethodException(typeof(BuildingsModelToggler).FullName,"ToggleBuildingModel");
      _current=this;
      _harmony.Patch(Target,transpiler:new HarmonyMethod(typeof(DebugBuildingVisibility),nameof(ReplaceModelActivation)));
      Debug.Log("[DeepFrontier] Debug building visibility hides rendering without disabling native slots (two 1.1.2.8 calls verified).");
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
      if(_current==null)throw new InvalidOperationException("Debug building visibility has no scene owner");
      if(visible) {
        // A building constructed while debug hiding was on was never hidden.
        if(_current._hidden.TryGetValue(model,out var previous)) {
          Restore(previous);_current._hidden.Remove(model);
        }
      } else {
        var previous=model.GetComponentsInChildren<Renderer>(true)
          .Select(r=>(Renderer:r,WasForcedOff:r.forceRenderingOff)).ToList();
        _current._hidden.Add(model,previous);
        foreach(var item in previous)item.Renderer.forceRenderingOff=true;
      }
    }
    private static void Restore(List<(Renderer Renderer,bool WasForcedOff)> previous) {
      foreach(var item in previous)if(item.Renderer)item.Renderer.forceRenderingOff=item.WasForcedOff;
    }
    public void Unload() {
      _harmony.Unpatch(Target,HarmonyPatchType.Transpiler,Owner);
      foreach(var previous in _hidden.Values)Restore(previous);
      _hidden.Clear();_current=null;
    }
  }
}
#endif
