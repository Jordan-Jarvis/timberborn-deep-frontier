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
  /// no native method is patched.
  /// <list type="bullet">
  /// <item>Without Moddable Weathers: the native binding, <see cref="FluidTideService"/> (and FluidTideUi).</item>
  /// <item>With Moddable Weathers: the adapter in the optional assembly <c>ModdableFluids.ModdableWeathers</c>
  /// (FluidTideModdableWeathers), which binds its own <see cref="IFluidTideScene"/>; nothing here patches the native weather.</item>
  /// </list>
  /// Both share the strength modifier, the Weather Station decorator and the development module.
  /// </summary>
  [Context("Game")]
  public sealed class FluidTidesConfigurator : Configurator {
    protected override void Configure() {
      if (!Binds(out var tides)) return;
      if (FluidTideModdableWeathers.Loaded) FluidTideModdableWeathers.RequireAdapter(tides);
      else {
        Bind<FluidTideService>().AsSingleton();
        Bind<IFluidTideScene>().ToExisting<FluidTideService>();
        Bind<FluidTideUi>().AsSingleton();
      }
      Bind<FluidTideStrengthModifier>().AsTransient();
      Bind<FluidTideWeatherStation>().AsTransient();
      MultiBind<IDevModule>().To<FluidTideDevModule>().AsSingleton();
      MultiBind<TemplateModule>().ToProvider(ProvideTemplateModule).AsSingleton();
    }

    /// <summary>
    /// Whether this Game scene binds a tide system, and its tides: a mod registered a fluid (or the worker fixture runs)
    /// and at least one tide is registered. The Moddable Weathers adapter's configurator binds under the same condition.
    /// </summary>
    public static bool Binds(out FluidTideRegistry tides) {
      // Every provider registered from IModStarter.StartMod before the first scene; freezing here gives the same registry the scene owner gets.
      var host = ModdableFluidsEntry.Host;
      var registry = host.Freeze();
      tides = host.Tides;
      return (WorkerAcceptanceRun.Enabled || registry.HasExtraFluids) && tides.Count > 0;
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
  /// and hazardous-weather modifiers. While a tide is in progress (IFluidTideScene.EmittingTide) a clean tide-overridable
  /// source returns the tide's multiplier (FluidTideDefinition.StrengthMultiplierFor); otherwise 1. Every placed source
  /// must have a registered source type, found by its template name.
  /// </summary>
  public sealed class FluidTideStrengthModifier : BaseComponent, IAwakableComponent, IInitializableEntity, IWaterStrengthModifier {
    private readonly IFluidTideScene _tides;
    private WaterSource _source;
    private FluidSourceTypeDefinition _type;

    public FluidTideStrengthModifier(IFluidTideScene tides) { _tides = tides; }

    public void Awake() {
      _source = GetComponent<WaterSource>();
      string template = GetComponent<TemplateSpec>()?.TemplateName
        ?? throw new InvalidOperationException("Moddable Fluids tides: a water source has no TemplateSpec, so its source type cannot be found");
      if (!ModdableFluidsEntry.Host.Registry.TryGetSourceTypeByTemplate(template, out _type))
        throw new InvalidOperationException("Moddable Fluids tides: water source template " + template + " has no registered source type; the mod that adds it must register one (FluidRegistration.AddSourceType)");
    }

    public void InitializeEntity() => _source.AddWaterStrengthModifier(this);

    public float GetStrengthModifier() {
      var tide = _tides.EmittingTide;
      return tide != null ? (float)tide.StrengthMultiplierFor(_type) : 1f;
    }

    public FluidSourceTypeDefinition SourceType => _type;
  }

  /// <summary>Development only: makes the next cycle's hazardous weather the chosen tide (in-game acceptance reaches it with "Jump to next season").</summary>
  internal sealed class FluidTideDevModule : IDevModule {
    private readonly IFluidTideScene _tides;
    public FluidTideDevModule(IFluidTideScene tides) { _tides = tides; }

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
  /// Moddable Weathers replaces the native hazardous weather system (its HazardousWeatherService is a replacing subclass,
  /// and it transpiles the native methods the native binding patches), so with it loaded the tides run through the
  /// adapter in the optional assembly <c>ModdableFluids.ModdableWeathers</c>, shipped as
  /// <c>Scripts/ModdableFluids.ModdableWeathers.dll.ModdableWeathers.optional</c> and loaded by Moddable Timberborn's
  /// OptionalModsLoader only while Moddable Weathers is enabled. These checks compare assembly names only: this assembly
  /// references no Moddable Weathers type.
  /// </summary>
  internal static class FluidTideModdableWeathers {
    internal const string AssemblyName = "ModdableWeathers", AdapterAssemblyName = "ModdableFluids.ModdableWeathers";
    internal const string AdapterFile = "Scripts/" + AdapterAssemblyName + ".dll." + AssemblyName + ".optional";

    internal static bool Loaded => IsLoaded(AssemblyName);

    /// <summary>With Moddable Weathers loaded, the adapter must be too; its own configurator binds the tide owner.</summary>
    internal static void RequireAdapter(FluidTideRegistry tides) {
      if (IsLoaded(AdapterAssemblyName)) return;
      throw new InvalidOperationException("Moddable Fluids tides (" + string.Join(", ", tides.Tides.Select(t => t.Id)) + ") need their Moddable Weathers adapter with Moddable Weathers enabled, "
        + "but " + AdapterAssemblyName + " is not loaded. Moddable Timberborn loads it from the Moddable Fluids package file " + AdapterFile
        + " only while Moddable Weathers is enabled: reinstall Moddable Fluids, or disable Moddable Weathers or the mods that register these tides for this game.");
    }

    private static bool IsLoaded(string name) => AppDomain.CurrentDomain.GetAssemblies().Any(a => a.GetName().Name == name);
  }
}
