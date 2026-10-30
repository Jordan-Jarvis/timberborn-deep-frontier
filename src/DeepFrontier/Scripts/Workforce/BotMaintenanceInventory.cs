#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using HarmonyLib;
using Timberborn.Goods;
using Timberborn.InventoryNeedSystem;
using Timberborn.InventorySystem;
using Timberborn.ModManagerScene;
using Timberborn.Workshops;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Why Harmony (Timberborn 1.1.2.8; Moddable Recipes 11.x): a workplace must
  // keep exactly one enabled Inventory (see BotMaintenance), so its bot
  // maintenance oils (FrontierBotMaintenanceSpec) and workplace upkeep goods
  // (FrontierWorkplaceUpkeepSpec, WorkplaceUpkeep.cs) join the native
  // Manufactory inventory as extra goods (ManufactoryExtraGood).
  // - Native ManufactoryInventoryInitializer.Initialize builds that inventory
  //   from the recipes only and Inventory takes its allowed goods once, in
  //   Initialize. A prefix builds the same inventory (same component name
  //   "Manufactory", so saved stock loads unchanged; same public output and
  //   native inventory need behaviour) with the extra goods added, and wraps
  //   the native RecipeGoodDisallower in ManufactoryExtraStock, for templates
  //   with either spec only. Every other manufactory, the Restaurant kitchen
  //   included, runs its own path.
  // - Moddable Recipes (a required mod) rebuilds a manufactory's allowed goods
  //   on Load and SetRecipe (ManufactoryPatches.InitInventoryForRecipe): only
  //   the selected recipe's goods stay, everything else becomes a takeable
  //   leftover to be hauled out. A postfix restores the extra goods exactly as
  //   the initializer authored them for the selected recipe.
  // Verify() resolves every member first and throws if a game or Moddable
  // Recipes update changed one.
  internal sealed class BotMaintenanceInventoryModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      BotMaintenanceInventory.Verify();
      var harmony=new Harmony(BotMaintenanceInventory.HarmonyId);
      harmony.CreateClassProcessor(typeof(BotMaintenanceInventory)).Patch();
      harmony.CreateClassProcessor(typeof(BotMaintenanceRecipeCompatibility)).Patch();
      Debug.Log("[DeepFrontier] Bot maintenance and workplace upkeep inventory patches applied (ManufactoryInventoryInitializer.Initialize, ModdableRecipes InitInventoryForRecipe).");
    }
  }

  [HarmonyPatch(typeof(ManufactoryInventoryInitializer),nameof(ManufactoryInventoryInitializer.Initialize))]
  internal static class BotMaintenanceInventory {
    internal const string HarmonyId="DeepFrontier.BotMaintenanceInventory";
    private const string NativeInventoryName="Manufactory";
    private static readonly AccessTools.FieldRef<Inventory,StorableGoodRegistry> AllowedGoods=AccessTools.FieldRefAccess<Inventory,StorableGoodRegistry>("_allowedGoods");
    private static readonly AccessTools.FieldRef<StorableGoodRegistry,List<StorableGoodAmount>> RegistryGoods=AccessTools.FieldRefAccess<StorableGoodRegistry,List<StorableGoodAmount>>("_storableGoods");
    private static readonly AccessTools.FieldRef<StorableGoodRegistry,HashSet<string>> RegistryInputs=AccessTools.FieldRefAccess<StorableGoodRegistry,HashSet<string>>("_inputGoods");
    private static readonly AccessTools.FieldRef<StorableGoodRegistry,HashSet<string>> RegistryOutputs=AccessTools.FieldRefAccess<StorableGoodRegistry,HashSet<string>>("_outputGoods");

    internal static void Verify() {
      var type=typeof(ManufactoryInventoryInitializer);
      Require(AccessTools.Method(type,nameof(ManufactoryInventoryInitializer.Initialize),new[]{typeof(Manufactory),typeof(Inventory)})?.ReturnType==typeof(void),
        "ManufactoryInventoryInitializer.Initialize(Manufactory, Inventory) : void");
      Require(AccessTools.Field(type,"_inventoryInitializerFactory")?.FieldType==typeof(InventoryInitializerFactory),"ManufactoryInventoryInitializer._inventoryInitializerFactory");
      Require(AccessTools.Field(type,"_inventoryNeedBehaviorInitializer")?.FieldType==typeof(InventoryNeedBehaviorInitializer),"ManufactoryInventoryInitializer._inventoryNeedBehaviorInitializer");
      Require(AccessTools.Field(type,"_recipeGoodsProcessor")?.FieldType==typeof(RecipeGoodsProcessor),"ManufactoryInventoryInitializer._recipeGoodsProcessor");
      Require(AccessTools.Field(type,"InventoryComponentName")?.GetValue(null) as string==NativeInventoryName,"ManufactoryInventoryInitializer.InventoryComponentName == \"Manufactory\"");
      Require(AccessTools.Field(typeof(Inventory),"_allowedGoods")?.FieldType==typeof(StorableGoodRegistry),"Inventory._allowedGoods : StorableGoodRegistry");
      foreach(var (name,fieldType) in new[]{("_storableGoods",typeof(List<StorableGoodAmount>)),("_inputGoods",typeof(HashSet<string>)),("_outputGoods",typeof(HashSet<string>))})
        Require(AccessTools.Field(typeof(StorableGoodRegistry),name)?.FieldType==fieldType,$"StorableGoodRegistry.{name}");
      Require(AccessTools.Method(typeof(ModdableRecipes.Patches.ManufactoryPatches),nameof(ModdableRecipes.Patches.ManufactoryPatches.InitInventoryForRecipe),
        new[]{typeof(Manufactory),typeof(RecipeSpec)})!=null,"ModdableRecipes ManufactoryPatches.InitInventoryForRecipe(Manufactory, RecipeSpec)");
    }

    private static void Require(bool condition,string member) {
      if(!condition)throw new InvalidOperationException("Timberborn 1.1.2.8 / Moddable Recipes contract changed: "+member);
    }

    private static bool Prefix(Manufactory subject,Inventory decorator,InventoryInitializerFactory ____inventoryInitializerFactory,
        InventoryNeedBehaviorInitializer ____inventoryNeedBehaviorInitializer,RecipeGoodsProcessor ____recipeGoodsProcessor) {
      var maintenance=subject.GetComponent<FrontierBotMaintenanceSpec>();
      var upkeep=subject.GetComponent<FrontierWorkplaceUpkeepSpec>();
      if(maintenance==null&&upkeep==null)return true;
      if(subject.GetComponent<Restaurant>())throw new InvalidOperationException("Bot maintenance or workplace upkeep and the Restaurant kitchen both customize one Manufactory inventory");
      var extras=ManufactoryExtraGood.Of(maintenance,upkeep);
      var recipes=subject.GetComponent<ManufactorySpec>();
      var goods=WithExtraGoods(____recipeGoodsProcessor.ProcessRecipes(recipes.ProductionRecipeIds).Select(p=>new StorableGoodAmount(p.Key,p.Value)),extras);
      var stock=new ManufactoryExtraStock(subject.GetComponent<RecipeGoodDisallower>(),extras);
      // Native order: allowed goods, recipe disallower, public output.
      var initializer=____inventoryInitializerFactory.Create(decorator,goods.Sum(g=>g.Amount),NativeInventoryName);
      initializer.AddAllowedGoods(goods);
      initializer.AddGoodDisallower(stock);
      initializer.HasPublicOutput();
      initializer.Initialize();
      subject.InitializeInventory(decorator);
      ____inventoryNeedBehaviorInitializer.AddNeedBehavior(decorator);
      return false;
    }

    // Recipe goods plus the extra goods: one that is already a recipe good
    // gets its Capacity added to its native entries; otherwise it is a givable
    // entry of its Capacity.
    internal static List<StorableGoodAmount> WithExtraGoods(IEnumerable<StorableGoodAmount> recipeGoods,ImmutableArray<ManufactoryExtraGood> extras) {
      var goods=recipeGoods.ToList();
      foreach(var extra in extras) {
        bool found=false;
        for(int i=0;i<goods.Count;i++) {
          if(goods[i].StorableGood.GoodId!=extra.GoodId)continue;
          goods[i]=new StorableGoodAmount(goods[i].StorableGood,goods[i].Amount+extra.Capacity);
          found=true;
        }
        if(!found)goods.Add(new StorableGoodAmount(StorableGood.CreateAsGivable(extra.GoodId),extra.Capacity));
      }
      return goods;
    }

    // After Moddable Recipes' rebuild for the selected recipe: drop its extra
    // good entries (the recipe's own and the takeable leftovers) and re-add
    // them as the initializer authors them for that recipe alone.
    internal static void RestoreExtraGoods(Manufactory manufactory,RecipeSpec selectedRecipe,ImmutableArray<ManufactoryExtraGood> extras) {
      var inventory=manufactory.Inventory;
      bool enabled=inventory.Enabled;
      if(enabled)inventory.Disable();
      var registry=AllowedGoods(inventory);
      var extraIds=extras.Select(g=>g.GoodId).ToHashSet();
      RegistryGoods(registry).RemoveAll(g=>extraIds.Contains(g.StorableGood.GoodId));
      RegistryInputs(registry).ExceptWith(extraIds);
      RegistryOutputs(registry).ExceptWith(extraIds);
      var recipeExtras=new List<StorableGoodAmount>();
      if(selectedRecipe!=null) {
        foreach(var ingredient in selectedRecipe.Ingredients.Where(g=>extraIds.Contains(g.Id)))
          recipeExtras.Add(new StorableGoodAmount(StorableGood.CreateAsGivable(ingredient.Id),selectedRecipe.GetCapacity(ingredient.ToGoodAmount())));
        if(selectedRecipe.ConsumesFuel&&extraIds.Contains(selectedRecipe.Fuel))
          recipeExtras.Add(new StorableGoodAmount(StorableGood.CreateAsGivable(selectedRecipe.Fuel),selectedRecipe.FuelCapacity));
        foreach(var product in selectedRecipe.Products.Where(g=>extraIds.Contains(g.Id)))
          recipeExtras.Add(new StorableGoodAmount(StorableGood.CreateAsTakeable(product.Id),selectedRecipe.GetCapacity(product.ToGoodAmount())));
      }
      registry.Add(WithExtraGoods(recipeExtras,extras));
      if(enabled)inventory.Enable();
    }
  }

  [HarmonyPatch(typeof(ModdableRecipes.Patches.ManufactoryPatches),nameof(ModdableRecipes.Patches.ManufactoryPatches.InitInventoryForRecipe))]
  internal static class BotMaintenanceRecipeCompatibility {
    private static void Postfix(Manufactory __0,RecipeSpec __1) {
      var maintenance=__0.GetComponent<FrontierBotMaintenanceSpec>();
      var upkeep=__0.GetComponent<FrontierWorkplaceUpkeepSpec>();
      if(maintenance!=null||upkeep!=null)BotMaintenanceInventory.RestoreExtraGoods(__0,__1,ManufactoryExtraGood.Of(maintenance,upkeep));
    }
  }
}
#endif
