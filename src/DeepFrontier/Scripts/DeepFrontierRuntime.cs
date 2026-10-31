using UnityEngine;

namespace DeepFrontier.Scripts {
  // Content is registered by the blueprint importer. This service keeps the
  // first slice's identifiers in one place for adapters and future source-node
  // selection logic.
  public sealed class DeepFrontierRuntime {
    public const string VerticalSliceVersion = "0.7.1";
    public const string SourceMode = "FiniteStockpileAndPermanentVeinWithIndustrialExpansion";
    public const string DeepOreGoodId = "DeepOre";
    public const string DeepAlloyGoodId = "DeepAlloy";
    public const string DeepDrillTemplateId = "DeepDrill.IronTeeth";
    public const string DeepMineTemplateId = "DeepMine.IronTeeth";
    public const string DeepProcessorTemplateId = "DeepProcessor.IronTeeth";
    public const string DeepOreSourceTemplateId = "DeepOreSource";
    public const string DeepOreVeinTemplateId = "DeepOreVein";

    public static readonly string[] VerticalSliceBlueprints = {
      "Goods/Good.DeepOre.blueprint",
      "Goods/Good.DeepAlloy.blueprint",
      "Recipes/Recipe.DeepOre.blueprint",
      "Recipes/Recipe.DeepOre.Mine.blueprint",
      "Recipes/Recipe.DeepAlloy.blueprint",
      "Buildings/Metal/DeepDrill/DeepDrill.IronTeeth.blueprint",
      "Buildings/Metal/DeepMine/DeepMine.IronTeeth.blueprint",
      "Buildings/Metal/DeepProcessor/DeepProcessor.IronTeeth.blueprint",
      "MapEditor/Objects/DeepOreSource/DeepOreSource.blueprint",
      "MapEditor/Objects/DeepOreVein/DeepOreVein.blueprint",
      "Buildings/Food/FertilizerWorks/FertilizerWorks.IronTeeth.blueprint",
      "Buildings/Food/FishHatchery/FishHatchery.IronTeeth.blueprint",
      "Buildings/Food/FisheryWorks/FisheryWorks.IronTeeth.blueprint",
      "Buildings/Food/FoodPackagingWorks/FoodPackagingWorks.IronTeeth.blueprint",
      "Buildings/Wellbeing/PublicHealthLab/PublicHealthLab.IronTeeth.blueprint",
      "Buildings/Food/GroceryStore/GroceryStore.IronTeeth.blueprint",
      "Buildings/Food/Restaurant/Restaurant.IronTeeth.blueprint",
      "Buildings/Wellbeing/Hospital/Hospital.IronTeeth.blueprint",
      "Buildings/Food/Greenhouse/Greenhouse.IronTeeth.blueprint",
      "Buildings/Metal/ChemicalWorks/ChemicalWorks.IronTeeth.blueprint",
      "Buildings/Metal/PrecisionMachineWorks/PrecisionMachineWorks.IronTeeth.blueprint",
      "Buildings/Water/WaterTreatmentPlant/WaterTreatmentPlant.IronTeeth.blueprint",
      "Buildings/Science/TechnicalSchool/TechnicalSchool.IronTeeth.blueprint",
      "Buildings/Metal/UraniumProcessingPlant/UraniumProcessingPlant.IronTeeth.blueprint",
      "Buildings/Metal/RadioactiveWasteRefinery/RadioactiveWasteRefinery.IronTeeth.blueprint",
      "Buildings/Metal/ElectrolysisPlant/ElectrolysisPlant.IronTeeth.blueprint",
      "Buildings/Metal/CryogenicLiquefactionPlant/CryogenicLiquefactionPlant.IronTeeth.blueprint",
      "Buildings/Metal/RocketAssemblyHangar/RocketAssemblyHangar.IronTeeth.blueprint",
      "Buildings/Science/MissionControl/MissionControl.IronTeeth.blueprint",
      "Buildings/Metal/LaunchPad/LaunchPad.IronTeeth.blueprint",
      "Buildings/Power/NuclearReactor/NuclearReactor.IronTeeth.blueprint",
      "Buildings/Storage/RadioactiveWasteVault/RadioactiveWasteVault.IronTeeth.blueprint",
    };

    public bool IsVerticalSliceConfigured => true;

    public DeepFrontierRuntime() {
      Debug.Log($"[DeepFrontier] Content {VerticalSliceVersion} configured: {SourceMode}; surface factories, nuclear fuel, waste, and launch data enabled.");
    }
  }
}
