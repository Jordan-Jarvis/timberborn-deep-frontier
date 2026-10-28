using Bindito.Core;
using Timberborn.BlockSystem;
using Timberborn.Rendering;
using Timberborn.TemplateInstantiation;

namespace DeepFrontier.Scripts {
  // Discovered like the mod's other per-feature configurators; no edit to
  // DeepFrontierConfigurator is needed.
  [Context("Game")]
  public sealed class WatersideConfigurator : Configurator {
    protected override void Configure() {
      Bind<WatersideSurvey>().AsSingleton();
      Bind<AdaptiveSupports>().AsTransient();
      Bind<WaterDepthWorkCells>().AsTransient();
      Bind<WaterDepthPreviewValidator>().AsTransient();
      Bind<WaterSitePreviewMarkers>().AsTransient();
      Bind<AdaptiveSupportsPlacementValidator>().AsSingleton();
      MultiBind<IBlockObjectValidator>().ToExisting<AdaptiveSupportsPlacementValidator>();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var b=new TemplateModule.Builder();
      b.AddDecorator<AdaptiveSupportsSpec,AdaptiveSupports>();
      // Native WaterInputPipe decorates EntityMaterials for its cloned segments;
      // singleton decorators are not duplicated if the entity already has one.
      b.AddDecorator<AdaptiveSupports,EntityMaterials>();
      b.AddDecorator<WaterDepthWorkCellsSpec,WaterDepthWorkCells>();
      b.AddDecorator<WaterDepthWorkCells,WaterDepthPreviewValidator>();
      b.AddDecorator<AdaptiveSupportsSpec,WaterSitePreviewMarkers>();
      b.AddDecorator<WaterDepthWorkCellsSpec,WaterSitePreviewMarkers>();
      return b.Build();
    }
  }
}
