#if !UNITY_EDITOR
using Bindito.Core;
using Timberborn.TemplateInstantiation;

namespace DeepFrontier.Scripts.Cryogenics {
  // Discovered like the mod's other per-feature configurators; no edit to
  // DeepFrontierConfigurator is needed. The intake gate itself is installed by
  // CryogenicIntakeGatePatch when the stockpile inventory is initialized.
  [Context("Game")]
  public sealed class CryogenicsConfigurator : Configurator {
    protected override void Configure() {
      Bind<CryogenicTank>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<CryogenicTankSpec, CryogenicTank>();
      return builder.Build();
    }
  }
}
#endif
