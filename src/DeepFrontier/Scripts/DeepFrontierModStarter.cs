using Timberborn.ModManagerScene;
using UnityEngine;

namespace DeepFrontier.Scripts {
  internal sealed class DeepFrontierModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
#if !UNITY_EDITOR
      new HarmonyLib.Harmony("DeepFrontier.RestaurantKitchen").CreateClassProcessor(typeof(RestaurantKitchenInventory)).Patch();
      new HarmonyLib.Harmony("DeepFrontier.RestaurantKitchen").CreateClassProcessor(typeof(RestaurantKitchenRecipeCompatibility)).Patch();
      var fishing=new HarmonyLib.Harmony("DeepFrontier.ShoreFishing");
      fishing.CreateClassProcessor(typeof(ShoreFishingAllowedGoods)).Patch();
      fishing.CreateClassProcessor(typeof(ShoreFishingAllowance)).Patch();
      fishing.CreateClassProcessor(typeof(ShoreFishingJob)).Patch();
      // Hatchery deck paths/shafts/platforms must load after the deck slabs
      // they stand on (Waterside/StackableBaseLoadOrder.cs).
      StackableBaseLoadOrder.Apply();
      // Buildings on a stackable deck or roof don't block the building below
      // (StackableTopBlockExemption.cs).
      StackableTopBlockExemption.Apply();
      // The restaurant panel replaces the native inventory list and single-recipe progress (RestaurantPanel.cs).
      RestaurantNativeFragmentHider.Apply();
      // Restaurant staff work late, into the colony's free time (RestaurantLateShift.cs).
      RestaurantLateShift.Apply();
      // Coal/Oil Power Plants saved as staffed workshops load as generators (PowerPlantSaveMigration.cs).
      PowerPlantSaveMigration.Apply();
      // Touching buildings share their insides (BuildingPassages.cs); the patches are inert until the game binds it.
      BuildingPassagesPatches.Apply();
      // Moddable Recipes 11.0.0 double Enable workaround (InventoryEnableGuard.cs).
      InventoryEnableGuard.Apply();
      ModdableRecipesEnabledState.Apply();
      // New games on built-in maps get their total build height before MapSize.Load (MapSetup/BuiltinMapHeight.cs).
      MapSetup.BuiltinMapHeight.Apply();
#endif
      Debug.Log("[DeepFrontier] Mod shell loaded for Timberborn 1.1.2.8; vertical-slice blueprints are enabled.");
    }
  }
}
