#if !UNITY_EDITOR
using System;
using HarmonyLib;
using Timberborn.BaseComponentSystem;
using Timberborn.GameDistrictsUI;
using Timberborn.ModManagerScene;
using UnityEngine;

namespace DeepFrontier.Scripts.Radiation {
  // Why Harmony (Timberborn 1.1.2.8, decompiled Timberborn.GameDistrictsUI and
  // Timberborn.Characters): a beaver's tint is the native CharacterTint
  // (_TintColor / _TintEnabled on the beaver shader), and native CitizenTint is
  // its only writer: CitizenTint.UpdateTint sets the colour named by the
  // beaver's or its district's name, or disables the tint. It runs on district
  // assignment, district rename and beaver rename (CitizenDistrictTintChanger,
  // CitizenNameTintChanger) with no event or layering hook. A postfix puts the
  // zombie yellow back after each update; on cure, RestoreNative asks
  // CitizenTint for the native tint again. Every IModStarter in the mod
  // assembly runs at mod start (ModCodeStarter), before any game scene loads.
  internal sealed class RadioactiveZombieModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      RadioactiveZombieTint.Patch();
      Debug.Log("[DeepFrontier] Radioactive zombie tint patch applied (CitizenTint.UpdateTint).");
    }
  }

  internal static class RadioactiveZombieTint {
    internal const string HarmonyId = "DeepFrontier.RadioactiveZombieTint";

    internal static void Patch() {
      var method = AccessTools.Method(typeof(CitizenTint), nameof(CitizenTint.UpdateTint), Type.EmptyTypes);
      if (method == null || method.ReturnType != typeof(void))
        throw new InvalidOperationException("Timberborn 1.1.2.8 contract changed: CitizenTint.UpdateTint() : void not found");
      new Harmony(HarmonyId).CreateClassProcessor(typeof(CitizenTintUpdatePatch)).Patch();
    }

    internal static void RestoreNative(BaseComponent beaver) {
      var citizenTint = beaver.GetComponent<CitizenTint>();
      if (citizenTint == null) throw new InvalidOperationException("Beaver has no native CitizenTint (decorated on Citizen)");
      citizenTint.UpdateTint();
    }
  }

  [HarmonyPatch(typeof(CitizenTint), nameof(CitizenTint.UpdateTint))]
  internal static class CitizenTintUpdatePatch {
    private static void Postfix(BaseComponent __instance) => __instance.GetComponent<RadioactiveZombie>()?.ReapplyTint();
  }
}
#endif
