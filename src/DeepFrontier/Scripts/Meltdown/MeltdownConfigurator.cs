using Bindito.Core;
using Timberborn.TemplateInstantiation;

namespace DeepFrontier.Scripts.Meltdown {
  // Reactor meltdown and radioactive waste leaks (docs/meltdown.md).
  // Discovered like the mod's other per-feature configurators.
  [Context("Game")]
  public sealed class MeltdownConfigurator : Configurator {
    protected override void Configure() {
      Bind<MeltdownService>().AsSingleton();
      Bind<ReactorCore>().AsTransient();
      Bind<WasteLeak>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<ReactorMeltdownSpec, ReactorCore>();
      builder.AddDecorator<WasteLeakSpec, WasteLeak>();
      return builder.Build();
    }
  }
}
