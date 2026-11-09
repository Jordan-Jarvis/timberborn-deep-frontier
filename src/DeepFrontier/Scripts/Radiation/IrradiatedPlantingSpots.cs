using Timberborn.BaseComponentSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.Radiation {
  // Planters skip irradiated ground, as they skip badwater-contaminated soil
  // (user report 2026-11-02: farmers replanted dead crops on irradiated ground,
  // the crop died at once, and they replanted it again, forever).
  //
  // Native planting (Timberborn 1.1.2.8, decompiled Timberborn.Planting):
  // every planter (farmhouses, the aquatic and efficient farmhouses, foresters)
  // picks its next spot with PlantingSpotFinder.FindClosest (from
  // PlanterWorkplaceBehavior.Decide and PlantBehavior.StartPlanting), which
  // keeps a marked spot only if the private CanPlantAt(PlantingSpot,
  // PlantableSpec) passes:
  //   prioritized plantable, PlantingSoilValidator.Validate (soil moist, or dry
  //   for arid plants; !ISoilContaminationService.SoilIsContaminated), the
  //   building's IPlantingSpotValidator, FloodableNaturalResourceService
  //   water depth, SpawnValidationService.IsUnobstructed.
  // Contaminated or dry soil therefore stays marked (the planting tool's
  // PlantingAreaValidator checks only obstruction) and planting resumes by
  // itself when the soil recovers. Irradiated ground gets exactly that rule.
  //
  // Why a patch: the soil rule is hard-coded. PlantingSoilValidator is an
  // internal singleton with a non-virtual Validate; IPlantingSpotValidator is
  // the planter building's own single component (FarmHouse, Forester), read
  // with GetComponent, which throws when a second component implements it;
  // ISoilContaminationService is the badwater soil field every native system
  // reads (contamination deaths, spreading, the soil tint), so it cannot carry
  // radiation. ISpawnValidator (IrradiatedGroundSpawnValidator) is consulted
  // only by natural spreading, not by planting. One postfix on CanPlantAt adds
  // the irradiated-ground test next to the native soil test
  // (IrradiatedPlantingSpotsPatch below).
  //
  // The test is RadiationSimulation.IsIrradiatedGround, the same call that
  // kills a plant planted there (IrradiatedGroundDeath.PostInitializeEntity),
  // so a spot is skipped exactly when its plant would die at once: one
  // threshold (RadiationTuning.IrradiatedGroundThreshold), soil and bank
  // layer, Radioactive Tide water included.
  //
  // Decorated on PlantablePrioritizer, the component native PlantingSpotFinder
  // is decorated on, so every entity with a PlantingSpotFinder has one. The
  // postfix reaches it through the planter building; nothing static.
  internal sealed class IrradiatedPlantingSpots : BaseComponent {
    private readonly RadiationSimulation _simulation;

    public IrradiatedPlantingSpots(RadiationSimulation simulation) { _simulation = simulation; }

    internal bool CanPlantAt(Vector3Int coordinates) => !_simulation.IsIrradiatedGround(coordinates);
  }
}

#if !UNITY_EDITOR
namespace DeepFrontier.Scripts.Radiation {
  using System;
  using System.Linq;
  using System.Reflection;
  using HarmonyLib;
  using Timberborn.ModManagerScene;
  using Timberborn.Planting;
  using Timberborn.SoilContaminationSystem;
  using Timberborn.SoilMoistureSystem;
  using Timberborn.TemplateInstantiation;

  // Every IModStarter in the mod assembly runs at mod start (ModCodeStarter).
  internal sealed class IrradiatedPlantingModStarter : IModStarter {
    internal const string HarmonyId = "DeepFrontier.IrradiatedPlantingSpots";

    public void StartMod(IModEnvironment modEnvironment) {
      NativePatches.Install(HarmonyId, IrradiatedPlantingNative.Verify, typeof(IrradiatedPlantingSpotsPatch));
      Debug.Log("[DeepFrontier] Irradiated planting patch applied (PlantingSpotFinder.CanPlantAt postfix: planters skip irradiated ground).");
    }
  }

  // Checked at mod start; a changed game throws instead of patching.
  internal static class IrradiatedPlantingNative {
    private const BindingFlags Any = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly;

    public static MethodInfo CanPlantAt() {
      var method = typeof(PlantingSpotFinder).GetMethod("CanPlantAt", Any, null, new[] { typeof(PlantingSpot), typeof(PlantableSpec) }, null);
      if (method == null || method.IsStatic || method.ReturnType != typeof(bool))
        throw Changed("PlantingSpotFinder.CanPlantAt(PlantingSpot, PlantableSpec) : bool");
      return method;
    }

    public static void Verify() {
      var canPlantAt = CanPlantAt();
      // An inlined CanPlantAt would bypass the postfix (Mono INLINE_LENGTH_LIMIT).
      if (NativeIl.Inlinable(canPlantAt)) throw Changed($"PlantingSpotFinder.CanPlantAt larger than the Mono inline limit (IL {NativeIl.Size(canPlantAt)} bytes)");
      // The native soil rule the irradiated-ground test stands beside.
      var soilValidate = Method(typeof(PlantingSoilValidator), nameof(PlantingSoilValidator.Validate), typeof(bool), typeof(PlantingSpot));
      Require(canPlantAt, soilValidate);
      Require(soilValidate, Method(typeof(ISoilContaminationService), nameof(ISoilContaminationService.SoilIsContaminated), typeof(bool), typeof(UnityEngine.Vector3Int)),
        Method(typeof(ISoilMoistureService), nameof(ISoilMoistureService.SoilIsMoist), typeof(bool), typeof(UnityEngine.Vector3Int)));
      // Every planter decision reaches CanPlantAt through FindClosest.
      var findClosest = Method(typeof(PlantingSpotFinder), nameof(PlantingSpotFinder.FindClosest), typeof(PlantingSpot?), typeof(UnityEngine.Vector3));
      var closestOrDefault = typeof(PlantingSpotFinder).GetMethods(Any).SingleOrDefault(m => m.Name == "GetClosestOrDefault")
        ?? throw Changed("PlantingSpotFinder.GetClosestOrDefault");
      Require(closestOrDefault, canPlantAt);
      Require(Method(typeof(PlanterWorkplaceBehavior), nameof(PlanterWorkplaceBehavior.Decide), typeof(Timberborn.BehaviorSystem.Decision),
        typeof(Timberborn.BehaviorSystem.BehaviorAgent)), findClosest);
      Require(Method(typeof(PlantBehavior), "ReserveCoordinates", typeof(void), typeof(Timberborn.BehaviorSystem.BehaviorAgent)), findClosest);
      // PlantingSpotFinder is decorated on PlantablePrioritizer, where
      // IrradiatedPlantingSpots is decorated (RadiationConfigurator).
      var module = Method(typeof(PlantingConfigurator), "ProvideTemplateModule", typeof(TemplateModule));
      if (!NativeIl.Callees(module).Any(m => m.Name == nameof(TemplateModule.Builder.AddDecorator) && m.IsGenericMethod
          && m.GetGenericArguments().SequenceEqual(new[] { typeof(PlantablePrioritizer), typeof(PlantingSpotFinder) })))
        throw Changed("PlantingConfigurator decorates PlantingSpotFinder on PlantablePrioritizer");
    }

    private static MethodInfo Method(Type type, string name, Type returnType, params Type[] parameters) {
      var method = type.GetMethod(name, Any, null, parameters, null);
      if (method == null || method.ReturnType != returnType)
        throw Changed($"{type.Name}.{name}({string.Join(", ", parameters.Select(p => p.Name))}) : {returnType.Name}");
      return method;
    }

    private static void Require(MethodBase caller, params MethodBase[] callees) {
      foreach (var callee in callees)
        if (!NativeIl.Calls(caller, callee)) throw Changed($"{caller.DeclaringType?.Name}.{caller.Name} calls {callee.DeclaringType?.Name}.{callee.Name}");
    }

    private static InvalidOperationException Changed(string member) =>
      new InvalidOperationException($"Irradiated planting: native planting API changed; expected {member} (Timberborn 1.1.2.8)");
  }

  // Adds "not irradiated ground" to the native planting-spot test. Runs only
  // when every native condition passed.
  [HarmonyPatch]
  internal static class IrradiatedPlantingSpotsPatch {
    private static MethodBase TargetMethod() => IrradiatedPlantingNative.CanPlantAt();

    private static void Postfix(BaseComponent __instance, PlantingSpot __0, ref bool __result) {
      if (!__result) return;
      var spots = __instance.GetComponent<IrradiatedPlantingSpots>();
      if (!spots) throw new InvalidOperationException($"Planter {__instance.Name} has no IrradiatedPlantingSpots decorator");
      __result = spots.CanPlantAt(__0.Coordinates);
    }
  }
}
#endif
