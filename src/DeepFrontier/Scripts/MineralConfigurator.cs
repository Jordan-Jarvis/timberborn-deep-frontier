using Bindito.Core;
using Timberborn.BlockObjectAccesses;
using Timberborn.BuildingRange;
using Timberborn.Demolishing;
using Timberborn.Emptying;
using Timberborn.Hauling;
using Timberborn.LaborSystem;
using Timberborn.Ruins;
using Timberborn.SimpleOutputBuildings;
using Timberborn.SimpleOutputBuildingsUI;
using Timberborn.TemplateInstantiation;
using Timberborn.WorkSystem;
using Timberborn.YielderFinding;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  [Context("MapEditor")]
  public sealed class MineralConfigurator : Configurator {
    protected override void Configure() {
      Bind<MineralDeposit>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(ProvideTemplateModule).AsSingleton();
    }

    private static TemplateModule ProvideTemplateModule() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<MineralDepositSpec, MineralDeposit>();
      return builder.Build();
    }
  }

  // Navigation, hauling and work behaviors are game services, not map-editor services.
  [Context("Game")]
  public sealed class MineralGameConfigurator : Configurator {
    protected override void Configure() {
      Bind<MineralYielderRetriever>().AsTransient();
      Bind<MineralPitAnimation>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(ProvideTemplateModule).AsSingleton();
    }

    private static TemplateModule ProvideTemplateModule() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<MineralDepositSpec, BlockObjectAccessible>();
      builder.AddDecorator<MineralDepositSpec, AccessibleDemolishableReacher>();
      builder.AddDecorator<MineralDepositSpec, RuinsRemoveYieldStrategy>();
      // Reuse the native scavenger work cycle, with our mineral-specific selector.
      builder.AddDecorator<MineralPitSpec, MineralYielderRetriever>();
      builder.AddDecorator<MineralPitAnimationSpec, MineralPitAnimation>();
      // Native scavenger work calls YieldStatus; RuinsUI supplies it for vanilla flags.
      builder.AddDecorator<MineralPitSpec, YieldStatus>();
      builder.AddDecorator<MineralPitSpec, SimpleOutputInventoryFragmentEnabler>();
      builder.AddDecorator<MineralPitSpec, BuildingWithTerrainRange>();
      builder.AddDecorator<MineralPitSpec, AutoEmptiable>();
      builder.AddDecorator<MineralPitSpec, Emptiable>();
      builder.AddDecorator<MineralPitSpec, HaulCandidate>();
      builder.AddDecorator<MineralPitSpec, SimpleOutputInventoryHaulBehaviorProvider>();
      builder.AddDecorator<MineralPitSpec, RemoveUnwantedStockWorkplaceBehavior>();
      builder.AddDecorator<MineralPitSpec, ScavengerWorkplaceBehavior>();
      builder.AddDecorator<MineralPitSpec, EmptyOutputWorkplaceBehavior>();
      builder.AddDecorator<MineralPitSpec, EmptyInventoriesWorkplaceBehavior>();
      builder.AddDecorator<MineralPitSpec, LaborWorkplaceBehavior>();
      builder.AddDecorator<MineralPitSpec, WaitInsideIdlyWorkplaceBehavior>();
      return builder.Build();
    }
  }

}
