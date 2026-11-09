using System;
using System.Linq;
using Bindito.Core;
using Timberborn.AutomationBuildings;
using Timberborn.BaseComponentSystem;
using Timberborn.Debugging;
using Timberborn.EntitySystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TemplateSystem;
using Timberborn.WaterSourceSystem;
using ModdableFluids;
using ModdableFluids.Runtime.Prototype;

namespace ModdableFluids.Tides.Prototype {
  /// <summary>
  /// Binds the tide system with the scene owner, under the same condition as <see cref="ModdableFluidsSceneConfigurator"/>
  /// (a mod registered a fluid, or the worker fixture), and only when at least one tide is registered. A tide always emits a
  /// registered extra fluid, so wherever a tide is registered the scene owner is bound. With no tide nothing is bound and
  /// no native method is patched. With Moddable Weathers loaded, registered tides refuse to run (FluidTideModdableWeathers).
  /// </summary>
  [Context("Game")]
  public sealed class FluidTidesConfigurator : Configurator {
    protected override void Configure() {
      // Every provider registered from IModStarter.StartMod before the first scene; freezing here gives the same registry the scene owner gets.
      var host = ModdableFluidsEntry.Host;
      var registry = host.Freeze();
      if (!WorkerAcceptanceRun.Enabled && !registry.HasExtraFluids) return;
      var tides = host.Tides;
      if (tides.Count == 0) return;
      FluidTideModdableWeathers.RequireAbsent(tides);
      Bind<FluidTideService>().AsSingleton();
      Bind<FluidTideUi>().AsSingleton();
      Bind<FluidTideStrengthModifier>().AsTransient();
      Bind<FluidTideWeatherStation>().AsTransient();
      MultiBind<IDevModule>().To<FluidTideDevModule>().AsSingleton();
      MultiBind<TemplateModule>().ToProvider(ProvideTemplateModule).AsSingleton();
    }

    // As the game attaches its own strength modifiers (WaterSourceSystemConfigurator: WaterSource -> DroughtWaterStrengthModifier).
    private static TemplateModule ProvideTemplateModule() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<WaterSource, FluidTideStrengthModifier>();
      builder.AddDecorator<WeatherStation, FluidTideWeatherStation>();
      return builder.Build();
    }
  }

  /// <summary>
  /// The native way to change a source's strength: an IWaterStrengthModifier added to the WaterSource, which multiplies
  /// its specified strength into CurrentStrength every tick (WaterSource.UpdateCurrentStrength), like the game's drought
  /// and hazardous-weather modifiers. While a tide is in progress a clean tide-overridable source returns the tide's
  /// multiplier (FluidTideDefinition.StrengthMultiplierFor); otherwise 1. Every placed source must have a registered
  /// source type, found by its template name.
  /// </summary>
  public sealed class FluidTideStrengthModifier : BaseComponent, IAwakableComponent, IInitializableEntity, IWaterStrengthModifier {
    private readonly FluidTideService _tides;
    private WaterSource _source;
    private FluidSourceTypeDefinition _type;

    public FluidTideStrengthModifier(FluidTideService tides) { _tides = tides; }

    public void Awake() {
      _source = GetComponent<WaterSource>();
      string template = GetComponent<TemplateSpec>()?.TemplateName
        ?? throw new InvalidOperationException("Moddable Fluids tides: a water source has no TemplateSpec, so its source type cannot be found");
      if (!ModdableFluidsEntry.Host.Registry.TryGetSourceTypeByTemplate(template, out _type))
        throw new InvalidOperationException("Moddable Fluids tides: water source template " + template + " has no registered source type; the mod that adds it must register one (FluidRegistration.AddSourceType)");
    }

    public void InitializeEntity() => _source.AddWaterStrengthModifier(this);

    public float GetStrengthModifier() => _tides.StrengthMultiplier(_type);

    public FluidSourceTypeDefinition SourceType => _type;
  }

  /// <summary>Development only: makes the next cycle's hazardous weather the chosen tide (in-game acceptance reaches it with "Jump to next season").</summary>
  internal sealed class FluidTideDevModule : IDevModule {
    private readonly FluidTideService _tides;
    public FluidTideDevModule(FluidTideService tides) { _tides = tides; }

    public DevModuleDefinition GetDefinition() {
      var builder = new DevModuleDefinition.Builder();
      foreach (var tide in _tides.Tides.Tides) {
        string id = tide.Id;
        builder.AddMethod(DevMethod.Create("Moddable Fluids: " + id + " next cycle", () => _tides.ForceNextCycle(id)));
      }
      return builder.Build();
    }
  }

  /// <summary>
  /// Moddable Weathers replaces the native hazardous weather system and transpiles the native methods this adapter patches
  /// into throws, so the native adapter cannot run beside it. A Moddable Weathers adapter (all registered tides converted to
  /// weights once, the same C′ shares) is not implemented yet; until it is, registered tides refuse to start with Moddable
  /// Weathers loaded, naming them. The check compares assembly names only: no Moddable Weathers type is referenced.
  /// </summary>
  internal static class FluidTideModdableWeathers {
    internal const string AssemblyName = "ModdableWeathers";

    internal static void RequireAbsent(FluidTideRegistry tides) {
      if (!AppDomain.CurrentDomain.GetAssemblies().Any(a => a.GetName().Name == AssemblyName)) return;
      throw new InvalidOperationException("Moddable Fluids tides cannot run with Moddable Weathers yet: it replaces the native hazardous weather that "
        + string.Join(", ", tides.Tides.Select(t => t.Id)) + " use. Disable Moddable Weathers, or the mods that register these tides, for this game.");
    }
  }
}
