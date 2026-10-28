#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using HarmonyLib;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.Workshops;

namespace DeepFrontier.Scripts {
  // Native ManufactoryInventoryInitializer unconditionally exposes products
  // for collection and initializes counter eating. Its public spec has no
  // table-service option. Customize only this exact restaurant's initial
  // inventory definition; production, recipe selection and saves remain native.
  [HarmonyPatch(typeof(ManufactoryInventoryInitializer),nameof(ManufactoryInventoryInitializer.Initialize))]
  internal static class RestaurantKitchenInventory {
    private static bool Prefix(Manufactory subject,Inventory decorator,InventoryInitializerFactory ____inventoryInitializerFactory) {
      var restaurant=subject.GetComponent<Restaurant>();
      if(!restaurant)return true;
      var spec=subject.GetComponent<RestaurantSpec>();
      if(spec.Stock.Select(s=>s.GoodId).Distinct().Count()!=spec.Stock.Length || spec.Stock.Any(s=>s.Capacity<=0))
        throw new InvalidOperationException("Restaurant stock must have unique goods and positive capacities");
      var initializer=____inventoryInitializerFactory.Create(decorator,spec.Stock.Sum(s=>s.Capacity),"Restaurant");
      initializer.AddAllowedGoods(spec.Stock.Select(s=>new StorableGoodAmount(StorableGood.CreateAsGivable(s.GoodId),s.Capacity)));
      initializer.AddGoodDisallower(new RestaurantKitchenStock(subject,spec));
      initializer.HasPublicInput();initializer.Initialize();
      subject.InitializeInventory(decorator);restaurant.InitializeInventory(decorator);
      return false;
    }
  }
  // Moddable Recipes 11.0.0 rebuilds every manufactory's allowed goods on
  // SetRecipe/Load, turning the previous menu into takeable leftovers. This
  // restaurant owns one persistent menu across recipes. Exclude it at that
  // mutation's entry point, before stock permissions are changed.
  [HarmonyPatch(typeof(ModdableRecipes.Patches.ManufactoryPatches),nameof(ModdableRecipes.Patches.ManufactoryPatches.InitInventoryForRecipe))]
  internal static class RestaurantKitchenRecipeCompatibility {
    private static bool Prefix(Manufactory __0) => !__0.GetComponent<Restaurant>();
  }
  // The kitchen cooks every recipe as resources allow (RestaurantKitchenChooser),
  // so the one inventory accepts every recipe's ingredients at once, each up to
  // its authored stock capacity, independent of the recipe currently cooking.
  // A stocked good that is neither always stocked nor any recipe's ingredient
  // is an authoring error.
  internal sealed class RestaurantKitchenStock : IGoodDisallower {
    private readonly Manufactory _kitchen;
    private readonly RestaurantSpec _spec;
    private HashSet<string> _ingredients;
    // Allowed amounts never change at runtime; the event is required by IGoodDisallower.
#pragma warning disable CS0067
    public event EventHandler<DisallowedGoodsChangedEventArgs> DisallowedGoodsChanged;
#pragma warning restore CS0067
    public RestaurantKitchenStock(Manufactory kitchen,RestaurantSpec spec) {_kitchen=kitchen;_spec=spec;}
    public int AllowedAmount(string id) {
      // Native IGoodDisallower contract: any good id may be asked (haulers of a
      // recovered goods stack query every inventory); unstocked goods are disallowed.
      var stock=_spec.Stock.SingleOrDefault(s=>s.GoodId==id);
      if(stock==null)return 0;
      if(stock.AlwaysStocked)return stock.Capacity;
      if(_ingredients==null) {
        // Queried only once the Manufactory has woken (inventory use starts at the finished state).
        if(_kitchen.ProductionRecipes.IsDefault)throw new InvalidOperationException("Restaurant kitchen stock queried before its recipes were initialized");
        _ingredients=_kitchen.ProductionRecipes.SelectMany(r=>r.Ingredients.Select(i=>i.Id).Concat(r.ConsumesFuel?new[]{r.Fuel}:Array.Empty<string>())).ToHashSet();
        foreach(var entry in _spec.Stock)
          if(!entry.AlwaysStocked&&!_ingredients.Contains(entry.GoodId))
            throw new InvalidOperationException("Restaurant stock good "+entry.GoodId+" is neither always stocked nor a kitchen ingredient");
      }
      return _ingredients.Contains(id)?stock.Capacity:0;
    }
  }
}
#endif
