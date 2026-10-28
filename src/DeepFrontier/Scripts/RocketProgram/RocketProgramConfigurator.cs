using Bindito.Core;
using Timberborn.RangedEffectSystem;
using Timberborn.TemplateInstantiation;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class RocketProgramConfigurator : Configurator {
    protected override void Configure() {
      Bind<RocketProgramService>().AsSingleton();
      Bind<RocketLaunchPad>().AsTransient();
      Bind<RocketLaunchVisual>().AsTransient();
      Bind<RocketMissionControl>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var builder=new TemplateModule.Builder();
      builder.AddDecorator<RocketLaunchPadSpec,RocketLaunchPad>();
      // Legacy wellbeing applier, driven by RocketLaunchPad (powered grid only).
      builder.AddDecorator<RocketLaunchPad,RangedEffectApplier>();
      builder.AddDecorator<RocketLaunchVisualSpec,RocketLaunchVisual>();
      builder.AddDecorator<RocketMissionControlSpec,RocketMissionControl>();
      return builder.Build();
    }
  }
}
