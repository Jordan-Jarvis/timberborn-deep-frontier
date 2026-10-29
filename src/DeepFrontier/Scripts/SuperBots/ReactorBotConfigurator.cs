using Bindito.Core;
using Timberborn.Bots;
using Timberborn.TemplateInstantiation;

namespace DeepFrontier.Scripts.SuperBots {
  // Discovered like the mod's other per-feature configurators.
  [Context("Game")]
  public sealed class ReactorBotConfigurator : Configurator {
    protected override void Configure() {
      Bind<ReactorBotSettings>().AsSingleton();
      Bind<ReactorBot>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    // Every bot carries the upgrade state; the template is the vanilla one.
    private static TemplateModule Provide() {
      var builder=new TemplateModule.Builder();
      builder.AddDecorator<BotSpec,ReactorBot>();
      return builder.Build();
    }
  }
}
