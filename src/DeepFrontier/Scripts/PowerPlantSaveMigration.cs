#if !UNITY_EDITOR
using System;
using HarmonyLib;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.TemplateSystem;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts {
  // Builds 193+: the Coal and Oil Power Plants are native Steam Engine generators
  // (GoodConsumingBuilding + GoodPoweredGenerator) instead of staffed workshops.
  // A plant saved before that has no GoodConsumingBuilding component, and native
  // GoodConsumingBuilding.Load reads it unconditionally (EntityLoader.GetComponent
  // throws), so the save failed to load. For exactly those two templates, a
  // missing component means the plant was saved as a workshop: it starts with
  // empty supplies, as a newly built plant does, and haulers refill it. Every
  // other building, and every plant saved by 193+, loads natively.
  [HarmonyPatch(typeof(GoodConsumingBuilding),nameof(GoodConsumingBuilding.Load))]
  internal static class PowerPlantSaveMigration {
    private static readonly ComponentKey Key=new("GoodConsumingBuilding");

    // Called once per process from DeepFrontierModStarter.
    internal static void Apply()=>new Harmony("DeepFrontier.PowerPlantSaveMigration").CreateClassProcessor(typeof(PowerPlantSaveMigration)).Patch();

    private static bool Prefix(GoodConsumingBuilding __instance,IEntityLoader entityLoader) {
      if(entityLoader.TryGetComponent(Key,out _))return true;
      var template=__instance.GetComponent<TemplateSpec>()?.TemplateName;
      if(template=="CoalPowerPlant.IronTeeth"||template=="OilPowerPlant.IronTeeth")return false;
      throw new InvalidOperationException("Saved "+template+" has no GoodConsumingBuilding component");
    }
  }
}
#endif
