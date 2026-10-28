#if !UNITY_EDITOR
using System.Collections.Generic;
using System.Linq;
using Bindito.Core;
using HarmonyLib;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.Buildings;
using Timberborn.CoreUI;
using Timberborn.EntityPanelSystem;
using Timberborn.InventorySystem;
using Timberborn.InventorySystemUI;
using Timberborn.Localization;
using Timberborn.MechanicalSystem;
using Timberborn.UIFormatters;
using Timberborn.Workshops;
using Timberborn.WorkshopsUI;
using TimberUi.CommonUi;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts {
  // The restaurant panel is made of the game's own entity-panel elements:
  // - native inventory rows (InformationalRowsFactory) grouped as the meal
  //   (one of each RestaurantSpec.Foods in stock; only a full meal adds Fine
  //   Dining), the extras served while in stock, and the kitchen ingredients;
  // - one native ProductionProgressFragment layout per kitchen recipe, filled
  //   by the native ManufactoryDescriber with the recipe's inputs, outputs
  //   and crafting time, and showing that recipe's real batch progress (the
  //   native batch cooking now, or one set aside by RestaurantKitchenChooser).
  // The native ManufactoryInventoryFragment and ProductionProgressFragment are
  // hidden for the restaurant (RestaurantNativeFragmentHider): they showed
  // only the current recipe's goods and progress, which changed with every
  // batch the automatic kitchen cooked.
  internal sealed class RestaurantPanel : BaseEntityPanelFragment<Restaurant> {
    private readonly InformationalRowsFactory _rows;
    private readonly VisualElementLoader _loader;
    private readonly ILoc _loc;
    private readonly Phrase _progressPhrase=Phrase.New().FormatPercentFloored();
    private Label _state,_seats,_service,_mealsReady;
    private VisualElement _meal,_extras,_ingredients,_recipes;
    private readonly List<InformationalRow> _goodRows=new();
    private readonly List<(RecipeSpec recipe,VisualElement root,Label progress)> _recipeRows=new();
    public RestaurantPanel(InformationalRowsFactory rows,VisualElementLoader loader,ILoc loc) {_rows=rows;_loader=loader;_loc=loc;}

    protected override void InitializePanel() {
      panel.AddGameLabel("Dining room",bold:true);
      _state=panel.AddGameLabel();_seats=panel.AddGameLabel();_service=panel.AddGameLabel();
      panel.AddGameLabel("Full meal (adds Fine dining)",bold:true).style.marginTop=6;
      _mealsReady=panel.AddGameLabel();_mealsReady.style.whiteSpace=WhiteSpace.Normal;
      _meal=panel.AddChild();
      panel.AddGameLabel("Extras served while in stock",bold:true).style.marginTop=6;
      _extras=panel.AddChild();
      panel.AddGameLabel("Kitchen ingredients",bold:true).style.marginTop=6;
      _ingredients=panel.AddChild();
      panel.AddGameLabel("Kitchen recipes",bold:true).style.marginTop=6;
      _recipes=panel.AddChild();
    }

    public override void ShowFragment(BaseComponent entity) {
      base.ShowFragment(entity);
      if(!component)return;
      var spec=component.Spec;var inventory=component.Inventory;
      var kitchen=component.GetComponent<Manufactory>();var describer=component.GetComponent<ManufactoryDescriber>();
      var served=spec.Foods.Concat(spec.OptionalGoods).Append(spec.DrinkingWater).ToHashSet();
      foreach(var id in spec.Foods)AddRow(_meal,id);
      foreach(var id in spec.OptionalGoods.Append(spec.DrinkingWater))AddRow(_extras,id);
      foreach(var id in kitchen.ProductionRecipes.SelectMany(r=>r.Ingredients).Select(i=>i.Id).Distinct().Where(id=>!served.Contains(id)))AddRow(_ingredients,id);
      foreach(var recipe in kitchen.ProductionRecipes) {
        var root=_loader.LoadVisualElement("Game/EntityPanel/ProductionProgressFragment");
        var (input,output)=describer.DescribeRecipe(recipe);
        root.Q<VisualElement>("InputWrapper").Add(input);root.Q<VisualElement>("OutputWrapper").Add(output);
        root.Q<Label>("CraftingTime").text=describer.GetCraftingTime(recipe,System.Math.Max(1,component.Workplace.DesiredWorkers));
        root.Q<Label>("FuelRemaining").ToggleDisplayStyle(false);
        _recipes.Add(root);
        _recipeRows.Add((recipe,root,root.Q<Label>("ProgressText")));
      }
      UpdateFragment();
    }

    public override void ClearFragment() {
      _meal.Clear();_extras.Clear();_ingredients.Clear();_recipes.Clear();
      _goodRows.Clear();_recipeRows.Clear();
      base.ClearFragment();
    }

    public override void UpdateFragment() {
      if(!component)return;
      _state.text=State();
      var diners=component.GetComponent<RestaurantSeats>().SeatedDiners.ToArray();
      _seats.text=$"Seated: {diners.Length} / {component.Spec.Seats.Length}   Waiting for service: {diners.Count(d=>!d.Served)}";
      var orders=component.OpenOrders.ToArray();
      _service.text=$"Orders at the kitchen pass: {orders.Count(o=>o.Stage==RestaurantOrderStage.Fetching)}   Carried to tables: {orders.Count(o=>o.Stage==RestaurantOrderStage.Carrying)}";
      _mealsReady.text=$"Full meals ready: {component.Spec.Foods.Min(id=>component.Inventory.UnreservedAmountInStock(id))}. Out-of-stock foods are left off a meal, without Fine dining.";
      foreach(var row in _goodRows)row.ShowUpdated();
      // Each recipe's real batch progress: cooking now, or set aside until its products fit.
      var chooser=component.GetComponent<RestaurantKitchenChooser>();
      foreach(var (recipe,root,progress) in _recipeRows) {
        float done=chooser.Progress(recipe);
        progress.text=_loc.T(_progressPhrase,done);
        root.EnableInClassList(ProductionProgressFragment.NoRecipeClass,chooser.Cooking!=recipe&&done<=0f);
      }
    }

    private void AddRow(VisualElement parent,string id) {
      var inventory=component.Inventory;
      var good=inventory.AllowedGoods.Single(g=>g.StorableGood.GoodId==id).StorableGood;
      _goodRows.Add(_rows.CreateInputRowWithLimit(good,inventory,parent));
    }

    private string State() {
      if(!component.Enabled)return "Under construction";
      if(component.GetComponent<PausableBuilding>().Paused)return "Paused";
      if(!component.GetComponent<MechanicalBuilding>().ActiveAndPowered)return "Requires shaft power";
      if(!component.GetComponent<BlockableObject>().IsUnblocked)return "Building blocked — check its warnings";
      if(component.Workplace.NumberOfAssignedWorkers==0)return "Waiting for staff";
      if(!component.StaffOnDuty)return "Closed outside working hours";
      if(!component.HasMeal)return "Closed: no main food in stock";
      return component.HasFullMeal?"Serving full meals":"Serving partial meals";
    }
  }

  internal static class RestaurantNativeFragmentHider {
    // Called once per process from DeepFrontierModStarter.
    internal static void Apply() {
      var harmony=new Harmony("DeepFrontier.RestaurantPanel");
      harmony.CreateClassProcessor(typeof(InventoryList)).Patch();
      harmony.CreateClassProcessor(typeof(Progress)).Patch();
    }
    [HarmonyPatch(typeof(ManufactoryInventoryFragment),nameof(ManufactoryInventoryFragment.UpdateFragment))]
    private static class InventoryList {
      private static void Postfix(ManufactoryInventoryFragment __instance) {
        if(__instance._manufactory&&__instance._manufactory.GetComponent<Restaurant>())__instance._root.ToggleDisplayStyle(false);
      }
    }
    [HarmonyPatch(typeof(ProductionProgressFragment),nameof(ProductionProgressFragment.UpdateFragment))]
    private static class Progress {
      private static void Postfix(ProductionProgressFragment __instance) {
        if(__instance._manufactory&&__instance._manufactory.GetComponent<Restaurant>())__instance._root.ToggleDisplayStyle(false);
      }
    }
  }

  [Context("Game")]
  public sealed class RestaurantPanelConfigurator : Configurator {
    protected override void Configure() {
      Bind<RestaurantPanel>().AsSingleton();
      MultiBind<EntityPanelModule>().ToProvider<ModuleProvider>().AsSingleton();
    }
    // Native WorkshopsUIConfigurator places ManufactoryInventoryFragment in the middle
    // section at order 20; the restaurant panel takes the place of that list.
    private sealed class ModuleProvider : IProvider<EntityPanelModule> {
      private readonly RestaurantPanel _panel;
      public ModuleProvider(RestaurantPanel panel) {_panel=panel;}
      public EntityPanelModule Get() {
        var builder=new EntityPanelModule.Builder();
        builder.AddMiddleFragment(_panel,20);
        return builder.Build();
      }
    }
  }
}
#endif
