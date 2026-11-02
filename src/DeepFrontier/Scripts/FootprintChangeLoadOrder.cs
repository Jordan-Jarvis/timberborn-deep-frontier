#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using Timberborn.BlockSystem;
using Timberborn.TemplateSystem;

namespace DeepFrontier.Scripts {
  // Save/load order for Deep Frontier buildings whose footprint changed in a
  // released version (the 0.7.0 compaction, the 0.8.2 second shrink).
  //
  // Native 1.1.2.8 BlockObjectBatchLoader.AddToServices adds loaded block
  // objects ordered by CoordinatesAtBaseZ.z, then by GetHighestOccupation
  // (Floor 1, Path 2, Bottom 3, Middle 4, Corners 5, Top 6), and
  // BlockObject.AddToServiceAfterLoad deletes, with a loading issue, any object
  // that is not valid at that moment. A smaller building keeps its origin, but
  // its new blocks can lie on cells the old blueprint left free on its own
  // layer: the Grocery Store's old doorstep, the Town Plaza's open corner, the
  // strip behind a Greenhouse's left wing, and for a flipped building, which
  // mirrors across its new width, whatever the player built in the old
  // building's free strips. A path there ranks 2, the building 6, so the path
  // was added first and the building was deleted on load (seen in game on
  // build 239: a 0.6.0 save lost its Grocery Store, Town Plaza and flipped
  // Fishery Works to paths).
  //
  // These buildings are added before every native occupation class in their
  // layer (after StackableBaseLoadOrder's deck carriers), so the building
  // stays and the native loader removes the path, platform or other object
  // that now overlaps it, with its usual loading notice. That is always valid
  // for the building itself: every foundation block sits at or below its
  // BaseZ layer (validate_load_order.mjs checks the list against the
  // blueprints), so it rests on terrain or on lower layers, which the loader
  // has already added. Buildings that stand on an understructure (Deep Mine,
  // quarries) must load after their deposit in the same layer and are not
  // listed; MineFootprintSaveMigration.cs moves them instead.
  internal static class FootprintChangeLoadOrder {
    // After StackableBaseLoadOrder.SupportFirst (-1), before native Floor (1).
    internal const int Rank=0;

    // Deep Frontier buildings whose BlockObjectSpec differs between 0.6.0 and
    // the current blueprints, without understructure-constrained ones.
    internal static readonly HashSet<string> Templates=new(StringComparer.Ordinal) {
      "ArchiveExcavation.IronTeeth","Bathhouse.IronTeeth","CementKiln.IronTeeth","ChemicalWorks.IronTeeth",
      "CoalPowerPlant.IronTeeth","ConcreteMixer.IronTeeth","CryogenicLiquefactionPlant.IronTeeth","CryogenicTankFarm.IronTeeth",
      "DeepDrill.IronTeeth","DeepProcessor.IronTeeth","ElectrolysisPlant.IronTeeth","FertilizerWorks.IronTeeth",
      "FisheryWorks.IronTeeth","FoodPackagingWorks.IronTeeth","Greenhouse.IronTeeth","GroceryStore.IronTeeth",
      "Hospital.IronTeeth","LaunchPad.IronTeeth","LimestonePit.IronTeeth","MaterialsLaboratory.IronTeeth",
      "MissionControl.IronTeeth","NuclearReactor.IronTeeth","ObservationDeck.IronTeeth","OilPowerPlant.IronTeeth",
      "PrecisionMachineWorks.IronTeeth","PublicHealthLab.IronTeeth","RadioactiveSludgeOutfall.IronTeeth",
      "RadioactiveSludgeRecoveryPump.IronTeeth","RadioactiveWasteExport.IronTeeth","RadioactiveWasteRefinery.IronTeeth",
      "RadioactiveWasteVault.IronTeeth","ReinforcedHydroTurbine.IronTeeth","Restaurant.IronTeeth",
      "RocketAssemblyHangar.IronTeeth","SandstonePit.IronTeeth","SmogScrubber.IronTeeth","SteelMill.IronTeeth",
      "StoneCrusher.IronTeeth","TechnicalSchool.IronTeeth","TownPlaza.IronTeeth","UraniumProcessingPlant.IronTeeth",
      "WaterTreatmentPlant.IronTeeth",
    };

    internal static bool LoadsBeforeOccupants(BlockObject blockObject) {
      var template=blockObject.GetComponent<TemplateSpec>()?.TemplateName;
      return template!=null&&Templates.Contains(template);
    }
  }
}
#endif
