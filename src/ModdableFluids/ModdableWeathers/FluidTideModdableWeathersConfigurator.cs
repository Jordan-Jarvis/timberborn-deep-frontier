using System;
using System.Linq;
using System.Runtime.CompilerServices;
using Bindito.Core;
using ModdableFluids;
using ModdableFluids.Tides.Prototype;
using ModdableWeathers.Helpers;

namespace ModdableFluids.Tides.ModdableWeathersAdapter {
  /// <summary>
  /// Moddable Fluids tides as Moddable Weathers 11.0.0 weathers: the optional assembly <c>ModdableFluids.ModdableWeathers</c>.
  /// <para>
  /// It ships as <c>Scripts/ModdableFluids.ModdableWeathers.dll.ModdableWeathers.optional</c>, so only Moddable
  /// Timberborn's OptionalModsLoader loads it, and only while Moddable Weathers is enabled (ModdableTimberborn 11.1.3,
  /// OptionalMods/OptionalModsLoader.cs). As a plain DLL the game would load it without Moddable Weathers, and enumerating
  /// its types, which derive from Moddable Weathers types, would fail. With Moddable Weathers loaded, the main assembly's
  /// FluidTidesConfigurator binds the shared parts and requires this assembly; this configurator binds the tide owner.
  /// </para>
  /// Under the same condition as the native binding (FluidTidesConfigurator.Binds), after checking Moddable Weathers'
  /// contract by name (FluidTideModdableWeathersContract), it binds:
  /// <list type="bullet">
  /// <item><see cref="FluidTideModdableWeathersService"/> as the scene's <see cref="IFluidTideScene"/>;</item>
  /// <item>one weather per registered tide through Moddable Weathers' own BindWeather&lt;T&gt; (classes
  /// FluidTideWeather0 … 7 for the first N tides; more tides than classes are refused).</item>
  /// </list>
  /// </summary>
  [Context("Game")]
  public sealed class FluidTideModdableWeathersConfigurator : Configurator {
    protected override void Configure() {
      if (!FluidTidesConfigurator.Binds(out var tides)) return;
      FluidTideModdableWeathersContract.Verify();
      if (tides.Count > FluidTideModdableWeather.Classes)
        throw new InvalidOperationException("Moddable Fluids tides: " + tides.Count + " tides are registered (" + string.Join(", ", tides.Tides.Select(t => t.Id))
          + "), but the Moddable Weathers adapter binds at most " + FluidTideModdableWeather.Classes + ". Disable Moddable Weathers or some of the mods that register tides for this game.");
      BindAdapter(tides.Count);
    }

    // Kept out of Configure, so that the Moddable Weathers members it names are resolved only after the contract check.
    [MethodImpl(MethodImplOptions.NoInlining)]
    private void BindAdapter(int count) {
      Bind<FluidTideModdableWeathersService>().AsSingleton();
      Bind<IFluidTideScene>().ToExisting<FluidTideModdableWeathersService>();
      if (count > 0) this.BindWeather<FluidTideWeather0>();
      if (count > 1) this.BindWeather<FluidTideWeather1>();
      if (count > 2) this.BindWeather<FluidTideWeather2>();
      if (count > 3) this.BindWeather<FluidTideWeather3>();
      if (count > 4) this.BindWeather<FluidTideWeather4>();
      if (count > 5) this.BindWeather<FluidTideWeather5>();
      if (count > 6) this.BindWeather<FluidTideWeather6>();
      if (count > 7) this.BindWeather<FluidTideWeather7>();
    }
  }
}
