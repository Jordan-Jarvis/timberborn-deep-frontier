#if !UNITY_EDITOR
using System;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using Timberborn.BlockObjectTools;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.BuildingTools;
using Timberborn.ModManagerScene;
using UnityEngine;

namespace DeepFrontier.Scripts.SteelStructures {
  // Why Harmony (Timberborn 1.1.2.8, decompiled Timberborn.BlockObjectTools and
  // Timberborn.BuildingTools): a tool's placer comes from
  // BlockObjectPlacerService.GetMatchingPlacer, which takes
  //   _blockObjectPlacers.SingleOrDefault(placer => placer.CanHandle(spec))
  // and native BuildingPlacer.CanHandle claims every template with a
  // BuildingSpec. The steel deck tools need a BuildingSpec (native science
  // unlock, cost panel, building model and preview), so with SteelDeckPlacer
  // registered through the native IBlockObjectPlacer multibinding two placers
  // would match and SingleOrDefault would throw. This postfix makes
  // BuildingPlacer give up exactly the templates with SteelDeckToolSpec; every
  // other template is matched as before. It changes no saved data: the tool is
  // never an entity, and what it places are ordinary buildings.
  //
  // Checked at mod start; a changed game throws instead of patching:
  // CanHandle(BlockObjectSpec) : bool still only asks HasSpec<BuildingSpec>,
  // and GetMatchingPlacer still selects with SingleOrDefault. CanHandle is a
  // 7-byte method, but it is reached only through the IBlockObjectPlacer
  // interface (an interface call is never inlined), so the patch always runs.
  internal sealed class SteelStructuresModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      SteelDeckPlacerClaim.Apply();
      Debug.Log("[DeepFrontier] Steel deck placer claim applied (BuildingPlacer.CanHandle postfix).");
    }
  }

  internal static class SteelDeckPlacerClaim {
    private static MethodInfo _canHandle;

    internal static void Apply()=>NativePatches.Install("DeepFrontier.SteelDeckPlacerClaim",Verify,harmony=>harmony.Patch(_canHandle,
      postfix:new HarmonyMethod(typeof(SteelDeckPlacerClaim),nameof(CanHandlePostfix))));

    private static void Verify() {
      const string prefix="[DeepFrontier SteelDeckPlacerClaim] ";
      var canHandle=AccessTools.Method(typeof(BuildingPlacer),nameof(BuildingPlacer.CanHandle),new[] {typeof(BlockObjectSpec)});
      if(canHandle==null||canHandle.ReturnType!=typeof(bool)||canHandle.IsStatic)
        throw new InvalidOperationException(prefix+"BuildingPlacer.CanHandle(BlockObjectSpec) : bool changed");
      var callees=NativeIl.Callees(canHandle);
      if(callees.Count!=1||callees[0].Name!="HasSpec"||!callees[0].IsGenericMethod||
         callees[0].GetGenericArguments().Single()!=typeof(BuildingSpec))
        throw new InvalidOperationException(prefix+"BuildingPlacer.CanHandle no longer only asks HasSpec<BuildingSpec>");
      var match=AccessTools.Method(typeof(BlockObjectPlacerService),nameof(BlockObjectPlacerService.GetMatchingPlacer),new[] {typeof(BlockObjectSpec)});
      if(match==null||match.ReturnType!=typeof(IBlockObjectPlacer)||
         !NativeIl.Callees(match).Any(m=>m.Name=="SingleOrDefault"&&m.DeclaringType==typeof(Enumerable)))
        throw new InvalidOperationException(prefix+"BlockObjectPlacerService.GetMatchingPlacer no longer selects one placer with SingleOrDefault");
      _canHandle=canHandle;
    }

    private static void CanHandlePostfix(BlockObjectSpec __0,ref bool __result) {
      if(__result&&__0.HasSpec<SteelDeckToolSpec>())__result=false;
    }
  }
}
#endif
