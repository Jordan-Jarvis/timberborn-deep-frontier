using Bindito.Core;
using Timberborn.Debugging;
using Timberborn.SelectionSystem;
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
      MultiBind<IDevModule>().To<MeltdownDevModule>().AsSingleton();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<ReactorMeltdownSpec, ReactorCore>();
      builder.AddDecorator<WasteLeakSpec, WasteLeak>();
      return builder.Build();
    }
  }

  // Dev mode only: melts down the selected finished Nuclear Reactor on the
  // next tick, the same meltdown as at core heat 100% (for in-game checks of
  // the crater, the blast and the flood without starving a reactor for 40
  // hours). With anything else selected it does nothing.
  internal sealed class MeltdownDevModule : IDevModule {
    private readonly EntitySelectionService _selection;
    public MeltdownDevModule(EntitySelectionService selection) { _selection = selection; }

    public DevModuleDefinition GetDefinition() => new DevModuleDefinition.Builder()
      .AddMethod(DevMethod.Create("Deep Frontier: melt down selected reactor", MeltDownSelected))
      .Build();

    private void MeltDownSelected() {
      var selected = _selection.SelectedObject;
      var core = selected ? selected.GetComponent<ReactorCore>() : null;
      if (core && core.Enabled) core.ForceMeltdown();
    }
  }
}
