using System;
#if !UNITY_EDITOR
using HarmonyLib;
#endif
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.Workshops;

namespace DeepFrontier.Scripts {
  // Workaround for a Moddable Recipes 11.0.0 bug (required dependency; report upstream).
  //
  // Its Harmony prefix on Manufactory.SetRecipe (ModdableRecipes.Patches.ManufactoryPatches
  // .InitInventoryForRecipe) calls Inventory.Disable() and then Inventory.Enable(). A single-recipe
  // manufactory gets its recipe before it is finished, so the native finished-state Enable
  // (Manufactory.OnEnterFinishedState) then runs on an inventory that is already enabled. Native
  // Timberborn 1.1.2.8 Inventory.Enable is unguarded: every call starts assigning the inventory to the
  // district again (DistrictInventoryAssigner -> DistrictInventoryRegistry.Add, InventoryRegistered),
  // and Inventories lists it in EnabledInventories again. Deletion disables it once, so a deleted
  // manufactory stays in the district's inventories-with-capacity. The next worker that empties a good
  // that manufactory accepted (EmptyOutputWorkplaceBehavior -> DistrictInventoryPicker.InventoryIsTaking)
  // hits the destroyed inventory with a NullReferenceException and the game stops (all-buildings run
  // b161: DeepProcessor deleted, then the DeepDrill worker emptied DeepOre). The doubled registration
  // also doubles the goods-balance counts and Timber Pipes' stock and limit for that building.
  //
  // The guard makes Enable idempotent: a call on an inventory that is already enabled is skipped.
  // Native Inventory.Initialize ends with DisableComponent(), so the first Enable of every inventory
  // runs unchanged with all of its side effects. Disable is not touched.
#if !UNITY_EDITOR
  [HarmonyPatch(typeof(Inventory),nameof(Inventory.Enable))]
#endif
  internal static class InventoryEnableGuard {
    internal const string HarmonyId="DeepFrontier.InventoryEnableGuard";
    // Calls skipped since the game started (read by the all-buildings acceptance).
    internal static int Skipped { get; private set; }

#if !UNITY_EDITOR
    private static bool _patched;

    // Called once per process from DeepFrontierModStarter, before any game scene creates inventories.
    internal static void Apply() {
      if(_patched)return;
      var method=AccessTools.Method(typeof(Inventory),nameof(Inventory.Enable),Type.EmptyTypes);
      if(method==null||method.IsStatic||method.ReturnType!=typeof(void)||method.DeclaringType!=typeof(Inventory))
        throw new InvalidOperationException("Timberborn 1.1.2.8 instance void Inventory.Enable() changed");
      var enabled=AccessTools.PropertyGetter(typeof(Inventory),"Enabled");
      if(enabled==null||enabled.ReturnType!=typeof(bool))
        throw new InvalidOperationException("Timberborn 1.1.2.8 BaseComponent.Enabled (bool) on Inventory changed");
      if(AccessTools.Method(typeof(Inventory),nameof(Inventory.Disable),Type.EmptyTypes)==null)
        throw new InvalidOperationException("Timberborn 1.1.2.8 Inventory.Disable() changed");
      new Harmony(HarmonyId).CreateClassProcessor(typeof(InventoryEnableGuard)).Patch();
      _patched=true;
    }

    private static bool Prefix(Inventory __instance) {
      if(!__instance.Enabled)return true;
      Skipped++;
      return false;
    }
#endif
  }

  // The complete Moddable Recipes 11.0.0 fix (approved 2026-10-24): MR's InitInventoryForRecipe always
  // ends with Inventory.Enable(), also on a construction site whose manufactory inventory is natively
  // still disabled (Manufactory enables it in OnEnterFinishedState). Such an inventory was enabled and
  // registered with the district while the site existed, and a site deleted unfinished never reaches
  // OnExitFinishedState, so it stayed registered (the same crash as above). This restores the enabled
  // state MR found, for every manufactory: the prefix records it, and the postfix disables the inventory
  // again (native Disable, which unregisters it) when MR enabled an inventory that was disabled.
  //
  // Order with Deep Frontier's other hooks on the same MR method: this prefix runs first
  // (Priority.First), before RestaurantKitchenRecipeCompatibility's prefix, which skips MR for the
  // restaurant. Harmony runs postfixes when the original is skipped; there the state is unchanged and
  // this postfix does nothing. This postfix runs last (Priority.Last), after
  // BotMaintenanceRecipeCompatibility's postfix, which disables and re-enables an enabled inventory around
  // its own registry edit and so keeps whatever state it finds.
#if !UNITY_EDITOR
  [HarmonyPatch(typeof(ModdableRecipes.Patches.ManufactoryPatches),nameof(ModdableRecipes.Patches.ManufactoryPatches.InitInventoryForRecipe))]
#endif
  internal static class ModdableRecipesEnabledState {
    internal const string HarmonyId="DeepFrontier.ModdableRecipesEnabledState";
    // Inventories MR enabled that were disabled before it ran, disabled again (read by the acceptance).
    internal static int Restored { get; private set; }

#if !UNITY_EDITOR
    private static bool _patched;

    internal static void Apply() {
      if(_patched)return;
      var method=AccessTools.Method(typeof(ModdableRecipes.Patches.ManufactoryPatches),
        nameof(ModdableRecipes.Patches.ManufactoryPatches.InitInventoryForRecipe),new[]{typeof(Manufactory),typeof(RecipeSpec)});
      if(method==null||!method.IsStatic||method.ReturnType!=typeof(void))
        throw new InvalidOperationException("Moddable Recipes 11.0.0 static void ManufactoryPatches.InitInventoryForRecipe(Manufactory, RecipeSpec) changed");
      // Deep Frontier's other hooks on this method bind by position (__0, __1); keep their shapes in step.
      var restaurant=AccessTools.Method(typeof(RestaurantKitchenRecipeCompatibility),"Prefix");
      if(restaurant==null||restaurant.ReturnType!=typeof(bool)||restaurant.GetParameters().Length!=1||restaurant.GetParameters()[0].ParameterType!=typeof(Manufactory))
        throw new InvalidOperationException("RestaurantKitchenRecipeCompatibility.Prefix(Manufactory) : bool changed");
      var bots=AccessTools.Method(typeof(BotMaintenanceRecipeCompatibility),"Postfix");
      if(bots==null||bots.GetParameters().Length!=2||bots.GetParameters()[0].ParameterType!=typeof(Manufactory)||bots.GetParameters()[1].ParameterType!=typeof(RecipeSpec))
        throw new InvalidOperationException("BotMaintenanceRecipeCompatibility.Postfix(Manufactory, RecipeSpec) changed");
      if(AccessTools.PropertyGetter(typeof(Manufactory),nameof(Manufactory.Inventory))==null)
        throw new InvalidOperationException("Timberborn 1.1.2.8 Manufactory.Inventory changed");
      new Harmony(HarmonyId).CreateClassProcessor(typeof(ModdableRecipesEnabledState)).Patch();
      _patched=true;
    }

    [HarmonyPriority(Priority.First)]
    private static void Prefix(Manufactory __0,out bool? __state) {
      var inventory=__0?__0.Inventory:null;
      __state=inventory?inventory.Enabled:(bool?)null;
    }

    [HarmonyPriority(Priority.Last)]
    private static void Postfix(Manufactory __0,bool? __state) {
      if(__state!=false)return;
      var inventory=__0.Inventory;
      if(!inventory||!inventory.Enabled)return;
      inventory.Disable();
      Restored++;
    }
#endif
  }
}
