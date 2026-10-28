using Timberborn.BlueprintSystem;
#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using Timberborn.BuildingStatuses;
using Timberborn.Common;
using Timberborn.ModManagerScene;
using UnityEngine;
#endif

namespace DeepFrontier.Scripts {
  // Height (layers above the building's layer-0 cell, BlockObject.Coordinates.z) above which the
  // native status icon never floats. Written by tools/status_icon_content.mjs on every Deep Frontier
  // building: max(main roof, top of the occupied cells under the icon's footprint centre) + 0.7 (the
  // native FinishedOffset). Checked by tools/validate_status_icon_anchors.mjs.
  internal record StatusIconAnchorSpec : ComponentSpec {
    [Serialize] public float Height { get; init; }
  }

#if !UNITY_EDITOR
  // Why Harmony (Timberborn 1.1.2.8, decompiled Timberborn.BuildingStatuses): the native
  // BuildingStatusIconOffsetter puts a building's status icon 0.7 above the highest MeshRenderer of
  // its finished (or unfinished) model, with no spec or extension point. A Deep Frontier chimney,
  // mast or gantry lifts the icon 3-14 layers above the building's main body, off screen when zoomed
  // in (user report, build 146: no visible "no power" icon on the Bathhouse). A postfix of the two
  // private top-bound methods lowers the result to the StatusIconAnchorSpec height for entities that
  // carry the spec; it never raises it. Every other building (vanilla included) keeps the native
  // value. Verify() resolves the members first and throws if 1.1.2.8 changed them.
  internal sealed class StatusIconAnchorModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      StatusIconAnchor.Verify();
      var harmony=new Harmony(StatusIconAnchor.HarmonyId);
      var postfix=new HarmonyMethod(typeof(StatusIconAnchor).GetMethod("Postfix",BindingFlags.Static|BindingFlags.NonPublic));
      foreach(var method in StatusIconAnchor.Targets())harmony.Patch(method,postfix:postfix);
      Debug.Log("[DeepFrontier] Status icon anchor patch applied (BuildingStatusIconOffsetter top bounds, StatusIconAnchorSpec only).");
    }
  }

  internal static class StatusIconAnchor {
    internal const string HarmonyId="DeepFrontier.StatusIconAnchor";
    private const BindingFlags Instance=BindingFlags.Instance|BindingFlags.NonPublic|BindingFlags.DeclaredOnly;
    // Mono inlines methods of at most 20 IL bytes; an inlined target would ignore the patch.
    private const int MonoInlineLimit=20;

    internal static IEnumerable<MethodInfo> Targets()=>new[]{Method("GetFinishedTopBound"),Method("GetUnfinishedTopBound")};

    private static MethodInfo Method(string name) {
      var method=typeof(BuildingStatusIconOffsetter).GetMethod(name,Instance,null,Type.EmptyTypes,null);
      if(method==null||method.ReturnType!=typeof(float))throw Changed($"BuildingStatusIconOffsetter.{name}() : float");
      return method;
    }

    internal static void Verify() {
      var type=typeof(BuildingStatusIconOffsetter);
      foreach(var method in Targets()) {
        int size=method.GetMethodBody()?.GetILAsByteArray()?.Length??0;
        if(size<=MonoInlineLimit)throw Changed($"BuildingStatusIconOffsetter.{method.Name} larger than the Mono inline limit (IL {size} bytes)");
      }
      RequireCalls(Method("GetFinishedTopBound"),typeof(BoundsCalculator).GetMethod(nameof(BoundsCalculator.GetRendererYMaxBound),new[]{typeof(Transform)}));
      var refresh=type.GetMethod("RefreshTopBounds",Instance,null,Type.EmptyTypes,null)??throw Changed("BuildingStatusIconOffsetter.RefreshTopBounds()");
      RequireCalls(refresh,Method("GetFinishedTopBound"),Method("GetUnfinishedTopBound"));
      var topBound=type.GetProperty("TopBound",BindingFlags.Instance|BindingFlags.Public)?.GetGetMethod();
      if(topBound==null)throw Changed("BuildingStatusIconOffsetter.TopBound");
      var offset=type.GetField("FinishedOffset",BindingFlags.Static|BindingFlags.NonPublic);
      if(offset?.FieldType!=typeof(float)||!Mathf.Approximately((float)offset.GetValue(null),.7f))throw Changed("BuildingStatusIconOffsetter.FinishedOffset = 0.7");
      if(type.GetProperty(nameof(BuildingStatusIconOffsetter.BlockObject))?.PropertyType!=typeof(Timberborn.BlockSystem.BlockObject))
        throw Changed("BuildingStatusIconOffsetter.BlockObject : BlockObject");
    }

    private static void Postfix(BuildingStatusIconOffsetter __instance,ref float __result) {
      var spec=__instance.GetComponent<StatusIconAnchorSpec>();
      if(spec==null)return;
      if(!(spec.Height>0f))throw new InvalidOperationException($"{__instance.Name}: StatusIconAnchorSpec.Height must be positive, not {spec.Height}");
      var blockObject=__instance.BlockObject;
      if(!blockObject)throw new InvalidOperationException($"{__instance.Name}: status icon offsetter without its BlockObject");
      __result=Mathf.Min(__result,blockObject.Coordinates.z+spec.Height);
    }

    private static void RequireCalls(MethodBase caller,params MethodBase[] callees) {
      var il=caller.GetMethodBody()?.GetILAsByteArray()??throw Changed($"{caller.Name} with an IL body");
      var called=new List<MethodBase>();
      for(int i=0;i+4<il.Length;i++) {
        if(il[i]!=0x28&&il[i]!=0x6F)continue;
        int token=BitConverter.ToInt32(il,i+1);
        if(token>>24!=0x06&&token>>24!=0x0A)continue;
        MethodBase method;
        try {method=caller.Module.ResolveMethod(token);} catch(ArgumentException) {continue;}
        called.Add(method);
      }
      foreach(var callee in callees)
        if(callee==null||!called.Any(m=>m.Module==callee.Module&&m.MetadataToken==callee.MetadataToken))
          throw Changed($"{caller.DeclaringType?.Name}.{caller.Name} calls {callee?.DeclaringType?.Name}.{callee?.Name}");
    }

    private static InvalidOperationException Changed(string member)=>
      new InvalidOperationException($"Status icon anchor: native API changed; expected {member} (Timberborn 1.1.2.8)");
  }
#endif
}
