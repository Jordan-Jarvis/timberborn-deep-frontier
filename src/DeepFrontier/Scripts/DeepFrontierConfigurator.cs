using Bindito.Core;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class DeepFrontierConfigurator : Configurator {
    protected override void Configure() {
      Bind<DeepFrontierRuntime>().AsSingleton();
    }
  }
}
