using System;
using System.Collections.Generic;
using System.Reflection;
using ModdableFluids;

namespace ModdableFluids.Tides.Prototype {
  /// <summary>
  /// The Game scene's tide owner as the parts both weather systems share see it: the strength modifier, the Weather Station
  /// decorator and its patches, and the development module. Two bindings implement it:
  /// <list type="bullet">
  /// <item>the native one, <see cref="FluidTideService"/>, which patches the native hazardous weather;</item>
  /// <item>the Moddable Weathers one, in the optional assembly <c>ModdableFluids.ModdableWeathers</c> (loaded only with
  /// Moddable Weathers), which registers one Moddable Weathers weather per tide and patches no native weather method.</item>
  /// </list>
  /// Exactly one is bound per scene (<see cref="FluidTidesConfigurator"/>), and it attaches itself to
  /// <see cref="FluidTideScenes"/> for the static Harmony patches.
  /// </summary>
  public interface IFluidTideScene {
    FluidTideRegistry Tides { get; }
    /// <summary>The game's tide settings (<c>ModdableFluids.TideSettings</c>), read on first use.</summary>
    FluidTideSaveSettings Settings { get; }
    /// <summary>
    /// The cycle's tide, forecast or in progress: the tide whose native weather ID is the native
    /// HazardousWeatherService.CurrentCycleHazardousWeather. The Weather Station samples it.
    /// </summary>
    FluidTideDefinition CurrentCycleTide { get; }
    /// <summary>The tide in progress, whose source emission and strength apply now; null outside a tide.</summary>
    FluidTideDefinition EmittingTide { get; }
    /// <summary>Development: the next cycle gets this tide, ignoring cycles without, the budget and the cooldown.</summary>
    void ForceNextCycle(string tideId);
  }

  /// <summary>The tide owner of the current Game scene, for the static Harmony patches; set by its constructor, cleared on unload.</summary>
  public static class FluidTideScenes {
    public static IFluidTideScene Current { get; private set; }

    /// <summary>Refuses a second owner while another is attached (a Game scene that did not unload, or two bindings).</summary>
    public static void Attach(IFluidTideScene scene) {
      if (scene == null) throw new ArgumentNullException(nameof(scene));
      if (Current != null) throw new InvalidOperationException("Moddable Fluids tides: a tide service (" + Current.GetType().Name + ") is already active; the previous Game scene was not unloaded");
      Current = scene;
    }

    public static void Detach(IFluidTideScene scene) {
      if (Current == scene) Current = null;
    }

    internal static IFluidTideScene RequireCurrent() =>
      Current ?? throw new InvalidOperationException("Moddable Fluids tides: the native weather was used outside a Game scene with a tide service");
  }

  /// <summary>
  /// The Weather Station part of the tide patches alone (WeatherStation.Sample and UpdateOutputState, the panel's
  /// InitializeFragment and UpdateFragment; owner <c>ModdableFluids.Tides</c>), after the same startup contract check as
  /// the native binding. The Moddable Weathers binding installs these: Moddable Weathers replaces the native hazardous
  /// weather but leaves the station native, and its HazardousWeatherService returns the cycle's current or next
  /// hazardous weather, which the station samples. Installed per scene and removed on unload; another owner on a
  /// target is refused, naming it.
  /// </summary>
  public sealed class FluidTideStationPatches {
    private readonly FluidTidePatchSet _patches = new FluidTidePatchSet(FluidTideService.OwnerId);

    public IReadOnlyList<MethodBase> Install() {
      var targets = FluidTideNative.VerifyStationGame();
      _patches.Install(targets, FluidTidePatches.ApplyStation);
      return targets;
    }

    public void Uninstall() => _patches.Uninstall();
    public bool Installed => _patches.Installed;
  }
}
