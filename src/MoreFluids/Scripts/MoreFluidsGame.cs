using System;
using Bindito.Core;
using ModdableFluids;
using Timberborn.Beavers;
using Timberborn.TemplateInstantiation;

namespace MoreFluids {
  /// <summary>
  /// The game scene's view of More Fluids' fluids. Moddable Fluids activates the provider's scene before entities tick;
  /// a game without an active fluid scene cannot run More Fluids, so every access outside one throws.
  /// </summary>
  public sealed class MoreFluidsScene {
    private readonly MoreFluidsLiquids _provider = MoreFluidsStarter.Provider
      ?? throw new InvalidOperationException("More Fluids did not register its fluids at mod start");

    public FluidScene Scene => _provider.Scene
      ?? throw new InvalidOperationException("More Fluids has no active Moddable Fluids scene: Moddable Fluids did not attach to this game");

    public FluidDefinition Fluid(string id) => Scene.Registry.TryGet(id, out var fluid) ? fluid
      : throw new InvalidOperationException("Fluid " + id + " is not registered");

    public FluidHandle Handle(string id) => Scene.Registry.GetHandle(id);
  }

  [Context("Game")]
  public sealed class MoreFluidsConfigurator : Configurator {
    protected override void Configure() {
      Bind<MoreFluidsScene>().AsSingleton();
      Bind<HealingExposure>().AsTransient();
      Bind<HealingWellPump>().AsTransient();
      Bind<FluidExtractor>().AsTransient();
      Bind<Desalinator>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder = new TemplateModule.Builder();
      // Adults and kits; bots have neither need.
      builder.AddDecorator<BeaverSpec, HealingExposure>();
      builder.AddDecorator<MoreFluidsHealingWellSpec, HealingWellPump>();
      builder.AddDecorator<MoreFluidsFluidExtractorSpec, FluidExtractor>();
      builder.AddDecorator<MoreFluidsDesalinatorSpec, Desalinator>();
      return builder.Build();
    }
  }
}
