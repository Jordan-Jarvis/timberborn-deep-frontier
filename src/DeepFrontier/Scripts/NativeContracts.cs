#if !UNITY_EDITOR
using System;
using System.Runtime.CompilerServices;
using DeepFrontier.Scripts.Radiation;
using Timberborn.ModManagerScene;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Startup check of the native members Deep Frontier reaches by reflection
  // outside its Harmony patches (whose checks run in NativePatches.Install).
  // Without it, a missing member surfaced only when the game first used the
  // feature: a static reflected handle failed inside the type initializer
  // while a save was loading (TypeInitializationException), or a scene's Load
  // threw. Each entry resolves the handles now, at the mod screen, and a
  // failure stops the game there naming Deep Frontier and the feature.
  // tools/validate_native_safety.mjs requires every source file that
  // reflects on native members by name to be covered here, by a
  // NativePatches.Install or by an IModStarter of its own.
  internal sealed class NativeContractsModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      NativeContracts.VerifyAll();
      Debug.Log($"[DeepFrontier] Native contracts checked at mod start ({NativeContracts.Checks.Length} reflected features, Timberborn {NativePatches.GameVersion}).");
    }
  }

  internal static class NativeContracts {
    internal static readonly (string Feature, Action Verify)[] Checks = {
      // Static reflected handles, resolved by each type's initializer.
      ("Technical School supplies (SpecialistSchool)", () => Initialize(typeof(SpecialistSchool))),
      ("Deep Well drill bits (DeepWell)", () => Initialize(typeof(DeepWell.DeepWell))),
      ("Restaurant kitchen (RestaurantKitchenChooser)", () => Initialize(typeof(RestaurantKitchenChooser))),
      // Explicit checks that ran only when a game loaded.
      ("Radiation shading", RadiationShading.Verify),
      ("Radiation soil", RadiationSoilNative.Verify),
#if !DEEP_FRONTIER_MODDABLE_FLUIDS
      // RadiationSimulation's exception-save check; the Moddable Fluids build does not use RadiationSimulation.
      ("Radiation simulation", RadiationSimulation.VerifyNative),
#endif
    };

    internal static void VerifyAll() {
      foreach (var (feature, verify) in Checks) {
        try {
          verify();
        } catch (Exception exception) {
          throw NativePatches.Failure($"its {feature} code", "its check of the game failed", exception);
        }
      }
    }

    private static void Initialize(Type type) => RuntimeHelpers.RunClassConstructor(type.TypeHandle);
  }
}
#endif
