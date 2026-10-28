using Bindito.Core;
using Timberborn.BlockSystem;

namespace DeepFrontier.Scripts {
  // Discovered like the mod's other per-feature configurators. Specs need no
  // decorators: the validator reads AnchoredDeckSpec/AnchoredDeckAnchorSpec
  // directly from the blueprint components.
  [Context("Game")]
  public sealed class AnchoredDeckConfigurator : Configurator {
    protected override void Configure() {
      Bind<AnchoredDeckValidator>().AsSingleton();
      MultiBind<IBlockObjectValidator>().ToExisting<AnchoredDeckValidator>();
    }
  }
}
