using Bindito.Core;
using Timberborn.EnterableSystem;
using Timberborn.Growing;
using Timberborn.TemplateInstantiation;

namespace DeepFrontier.Scripts {
  // Discovered like the mod's other per-feature configurators; no edit to
  // DeepFrontierConfigurator is needed.
  //
  // Native decorators that apply automatically (TemplateInstantiator decorates
  // a component's interfaces too): IBuildingWithRange ->
  // BuildingWithRangePreviewUpdater (placement range preview). The native
  // RangeEnterableHighlighter (bound by EnterableSystemConfigurator) is added
  // here to outline enterable buildings inside a polluter's or scrubber's
  // range, as RangedEffectSystemConfigurator does for RangedEffectBuilding.
  [Context("Game")]
  public sealed class SmogConfigurator : Configurator {
    protected override void Configure() {
      Bind<SmogService>().AsSingleton();
      Bind<SmogEmitter>().AsTransient();
      Bind<SmogScrubber>().AsTransient();
      Bind<SmogExposure>().AsTransient();
      Bind<SmogGrowth>().AsTransient();
      Bind<SmogBuildingDescriber>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var b=new TemplateModule.Builder();
      b.AddDecorator<SmogEmitterSpec,SmogEmitter>();
      b.AddDecorator<SmogEmitter,RangeEnterableHighlighter>();
      b.AddDecorator<SmogScrubberSpec,SmogScrubber>();
      b.AddDecorator<SmogScrubber,RangeEnterableHighlighter>();
      b.AddDecorator<Enterer,SmogExposure>();
      b.AddDecorator<Growable,SmogGrowth>();
      b.AddDecorator<Enterable,SmogBuildingDescriber>();
      return b.Build();
    }
  }
}
