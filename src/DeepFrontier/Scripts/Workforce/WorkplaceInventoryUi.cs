#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using Bindito.Core;
using HarmonyLib;
using Timberborn.BaseComponentSystem;
using Timberborn.Common;
using Timberborn.CoreUI;
using Timberborn.EntityPanelSystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.InventorySystemUI;
using Timberborn.Localization;
using Timberborn.NeedApplication;
using Timberborn.NeedSpecs;
using Timberborn.TemplateInstantiation;
using Timberborn.TooltipSystem;
using Timberborn.Workshops;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts {
  // 1.1.2.8's InventoryRowUpdater only recognizes recipe ingredients/fuel as inputs.
  // Extra operating supplies otherwise become untyped leftover rows below the products.
  // Extend that classification at row creation; retain the native row factory, sorting,
  // visibility, stock/capacity updates and handling of genuine leftovers.
  [HarmonyPatch(typeof(InventoryRowUpdater), "AddRecipeRows")]
  internal static class WorkplaceInventoryRows {
    internal static void Verify() {
      var type = typeof(InventoryRowUpdater);
      if (AccessTools.Method(type, "AddRecipeRows", new[] { typeof(ScrollView), typeof(Inventory),
          typeof(List<InformationalRow>), typeof(List<StorableGoodAmount>), typeof(RecipeSpec) })?.ReturnType != typeof(void)
          || AccessTools.Field(type, "_informationalRowsFactory")?.FieldType != typeof(InformationalRowsFactory))
        throw new InvalidOperationException("Timberborn 1.1.2.8 inventory UI contract changed: InventoryRowUpdater.AddRecipeRows");
    }

    private static bool Prefix(ScrollView inventoryContent, Inventory inventory, List<InformationalRow> rows,
        List<StorableGoodAmount> goods, RecipeSpec currentRecipe, InformationalRowsFactory ____informationalRowsFactory) {
      var stock = ManufactoryExtraStock.For(inventory);
      if (stock == null) return true;
      var details = inventory.GetComponent<WorkplaceSupplyTooltips>();
      foreach (var entry in goods) {
        var good = entry.StorableGood;
        if (!good.IsOnlyGivable || !(stock.Holds(good.GoodId)
            || currentRecipe.Ingredients.Any(g => g.Id == good.GoodId) || currentRecipe.Fuel == good.GoodId)) continue;
        var row = ____informationalRowsFactory.CreateInputRowWithLimit(good, inventory, inventoryContent);
        rows.Add(row);
        if (details) details.Register(row);
      }
      foreach (var entry in goods) {
        var good = entry.StorableGood;
        if (good.IsOnlyTakeable && currentRecipe.Products.Any(g => g.Id == good.GoodId))
          rows.Add(____informationalRowsFactory.CreateOutputRowWithLimit(good, inventory, inventoryContent));
      }
      return false;
    }
  }

  internal sealed class WorkplaceSupplyTooltips : BaseComponent, IAwakableComponent {
    private readonly ITooltipRegistrar _tooltips;
    private readonly ILoc _loc;
    private readonly IGoodService _goods;
    private WorkplaceUpkeep _upkeep;
    public WorkplaceSupplyTooltips(ITooltipRegistrar tooltips, ILoc loc, IGoodService goods) {
      _tooltips = tooltips; _loc = loc; _goods = goods;
    }
    public void Awake() { _upkeep = GetComponent<WorkplaceUpkeep>(); }
    public void Register(InformationalRow row) {
      for (int i = 0; i < _upkeep.Spec.Goods.Length; i++) {
        var index = i;
        var good = _upkeep.Spec.Goods[index];
        if (good.GoodId != row.GoodId) continue;
        _tooltips.Register(row.Root, () =>
          _loc.T("DeepFrontier.WorkplaceUpkeep.Panel.Good", _goods.GetGood(good.GoodId).PluralDisplayName.Value,
            _upkeep.Inventory.AmountInStock(good.GoodId), good.GoodPerHour.ToString("0.##")) + "\n" +
          _loc.T("DeepFrontier.WorkplaceUpkeep.Panel.Note", _upkeep.HoursInStock(index).ToString("0")));
        return;
      }
    }
  }

  // Same one-line, colored need description as native NeedEffectsSpecDescriber.
  // Does not add a second need applier or change the industrial accident rolls.
  internal sealed class IndustrialRiskDescriber : BaseComponent, IEntityDescriber {
    private readonly WorkforceSettings _settings;
    private readonly EffectProbabilityService _probabilities;
    private readonly NeedSpecFormatter _formatter;
    private readonly ILoc _loc;
    public IndustrialRiskDescriber(WorkforceSettings settings, EffectProbabilityService probabilities,
        NeedSpecFormatter formatter, ILoc loc) {
      _settings = settings; _probabilities = probabilities; _formatter = formatter; _loc = loc;
    }
    public IEnumerable<EntityDescription> DescribeEntity() {
      if (!_probabilities.CanApplyEffects) yield break;
      var spec = GetComponent<FrontierWorkforceRiskSpec>();
      var key = spec.Probability switch {
        EffectProbability.Low => "EffectProbability.Low",
        EffectProbability.Medium => "EffectProbability.Medium",
        EffectProbability.High => "EffectProbability.High",
        _ => throw new ArgumentOutOfRangeException(nameof(spec.Probability)),
      };
      yield return EntityDescription.CreateTextSection(SpecialStrings.RowStarter +
        _loc.T(key, _formatter.ColorizeNeedByEffect(_settings.InjuryNeed)), 3000);
    }
  }

  [Context("Game")]
  public sealed class WorkplaceInventoryUiConfigurator : Configurator {
    protected override void Configure() {
      Bind<WorkplaceSupplyTooltips>().AsTransient();
      Bind<IndustrialRiskDescriber>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<FrontierWorkplaceUpkeepSpec, WorkplaceSupplyTooltips>();
      builder.AddDecorator<FrontierWorkforceRiskSpec, IndustrialRiskDescriber>();
      return builder.Build();
    }
  }
}
#endif
