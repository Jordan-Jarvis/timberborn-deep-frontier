#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using Bindito.Core;
using HarmonyLib;
using Timberborn.BaseComponentSystem;
using Timberborn.Characters;
using Timberborn.SingletonSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class TeleporterCitizenRecoveryConfigurator : Configurator {
    protected override void Configure() {
      if(AppDomain.CurrentDomain.GetAssemblies().Any(a=>a.GetName().Name=="TeleporterStation"))
        Bind<TeleporterCitizenRecovery>().AsSingleton();
    }
  }

  // Teleporter Station 0.5.1 restores district membership after loading by
  // scanning all entities, including corpses. Native Citizen.AssignDistrict
  // registers their Worker in the hiring pool; the global population rightly
  // excludes them. Fix eligibility in the two teleporter recovery scans,
  // before movement or registration, not in the employment counter.
  internal sealed class TeleporterCitizenRecovery : ILoadableSingleton,IUnloadableSingleton {
    const string Owner="DeepFrontier.TeleporterCitizenRecovery";
    readonly Harmony _harmony=new(Owner);
    readonly List<MethodInfo> _targets=new();
    public void Load() {
      var assembly=AppDomain.CurrentDomain.GetAssemblies().Single(a=>a.GetName().Name=="TeleporterStation");
      var type=assembly.GetType("TeleporterStation.TeleporterNetwork",throwOnError:true);
      foreach(var name in new[]{"SafeRestoreStrandedDistricts","LandOffMeshCharacters"}) {
        var method=AccessTools.DeclaredMethod(type,name,Type.EmptyTypes)
          ??throw new MissingMethodException(type.FullName,name);
        _harmony.Patch(method,transpiler:new HarmonyMethod(typeof(TeleporterCitizenRecovery),nameof(SelectLivingCharacters)));
        _targets.Add(method);
      }
      Debug.Log("[DeepFrontier] Teleporter recovery excludes dead characters before district registration and landing.");
    }
    static IEnumerable<CodeInstruction> SelectLivingCharacters(IEnumerable<CodeInstruction> instructions) {
      var code=instructions.ToList();
      var calls=code.Where(i=>i.operand is MethodInfo m && m.DeclaringType==typeof(BaseComponent)
        &&m.Name==nameof(BaseComponent.GetComponent)&&m.IsGenericMethod
        &&m.GetGenericArguments().SequenceEqual(new[]{typeof(Character)})&&m.GetParameters().Length==0).ToList();
      if(calls.Count!=1)throw new InvalidOperationException("Teleporter recovery contract changed: expected one Character lookup; found "+calls.Count);
      calls[0].opcode=OpCodes.Call;
      calls[0].operand=AccessTools.DeclaredMethod(typeof(TeleporterCitizenRecovery),nameof(GetLivingCharacter));
      return code;
    }
    static Character GetLivingCharacter(BaseComponent entity) {
      var character=entity.GetComponent<Character>();
      return character&&character.Alive?character:null;
    }
    public void Unload() {
      foreach(var target in _targets)_harmony.Unpatch(target,HarmonyPatchType.Transpiler,Owner);
      _targets.Clear();
    }
  }
}
#endif
