#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using HarmonyLib;
using Timberborn.BaseComponentSystem;
using Timberborn.Characters;
using Timberborn.ModManagerScene;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Teleporter Station 0.5.1 restores district membership after loading by
  // scanning all entities, including corpses. Native Citizen.AssignDistrict
  // registers their Worker in the hiring pool; the global population rightly
  // excludes them. Fix eligibility in the two teleporter recovery scans,
  // before movement or registration, not in the employment counter.
  //
  // Installed once at mod start, only while Teleporter Station is enabled
  // (ModCodeStarter loads every enabled mod's assemblies before starting any
  // mod). The transpiler keeps no state, so no scene owns it and no scene's
  // load order decides whether the scans run patched.
  internal sealed class TeleporterCitizenRecoveryModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      if (!OptionalIntegrations.AssemblyLoaded(TeleporterCitizenRecovery.AssemblyName)) return;
      TeleporterCitizenRecovery.Install();
      Debug.Log("[DeepFrontier] Teleporter recovery excludes dead characters before district registration and landing.");
    }
  }

  internal static class TeleporterCitizenRecovery {
    internal const string AssemblyName="TeleporterStation";
    private const string Feature="Teleporter Station recovery";
    private static readonly string[] Scans={"SafeRestoreStrandedDistricts","LandOffMeshCharacters"};
    private static readonly List<MethodInfo> Targets=new();

    internal static void Install()=>NativePatches.Install("DeepFrontier.TeleporterCitizenRecovery",Verify,harmony=>{
      foreach(var target in Targets)harmony.Patch(target,transpiler:new HarmonyMethod(typeof(TeleporterCitizenRecovery),nameof(SelectLivingCharacters)));
    });

    // Each scan looks its characters up exactly once (what the transpiler replaces).
    private static void Verify() {
      var assembly=AppDomain.CurrentDomain.GetAssemblies().Single(a=>a.GetName().Name==AssemblyName);
      var type=assembly.GetType("TeleporterStation.TeleporterNetwork",throwOnError:false)
        ??throw NativePatches.Changed(Feature,"TeleporterStation.TeleporterNetwork (Teleporter Station 0.5.1)");
      Targets.Clear();
      foreach(var name in Scans) {
        var method=AccessTools.DeclaredMethod(type,name,Type.EmptyTypes)
          ??throw NativePatches.Changed(Feature,$"TeleporterNetwork.{name}() (Teleporter Station 0.5.1)");
        int lookups=NativeIl.Callees(method).Count(IsCharacterLookup);
        if(lookups!=1)throw NativePatches.Changed(Feature,$"one Character lookup in TeleporterNetwork.{name}, found {lookups}");
        Targets.Add(method);
      }
    }

    private static bool IsCharacterLookup(MethodBase m)=>m is MethodInfo method&&method.DeclaringType==typeof(BaseComponent)
      &&method.Name==nameof(BaseComponent.GetComponent)&&method.IsGenericMethod
      &&method.GetGenericArguments().SequenceEqual(new[]{typeof(Character)})&&method.GetParameters().Length==0;

    static IEnumerable<CodeInstruction> SelectLivingCharacters(IEnumerable<CodeInstruction> instructions) {
      var code=instructions.ToList();
      var calls=code.Where(i=>i.operand is MethodInfo m&&IsCharacterLookup(m)).ToList();
      if(calls.Count!=1)throw new InvalidOperationException("Teleporter recovery contract changed: expected one Character lookup; found "+calls.Count);
      calls[0].opcode=OpCodes.Call;
      calls[0].operand=AccessTools.DeclaredMethod(typeof(TeleporterCitizenRecovery),nameof(GetLivingCharacter));
      return code;
    }

    static Character GetLivingCharacter(BaseComponent entity) {
      var character=entity.GetComponent<Character>();
      return character&&character.Alive?character:null;
    }
  }
}
#endif
