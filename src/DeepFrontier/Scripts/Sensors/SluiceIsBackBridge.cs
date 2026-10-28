using System;
using System.Linq;
using Bindito.Core;

namespace DeepFrontier.Scripts.Sensors {
  // The "Measures: Badwater / Radiation / Any contamination" choice for the
  // Sluice of the optional mod "Sluice is Back!" (Workshop 3677643870, mod id
  // SluiceIsBack, 11.0.0) lives in the optional assembly
  // DeepFrontier.SluiceIsBack (Scripts/SluiceIsBack, its own asmdef). It
  // derives from and patches Sluice is Back! types, so it cannot live in this
  // DLL: Timberborn calls Assembly.GetTypes() unguarded on every mod assembly,
  // which throws when a referenced assembly is absent (see
  // RadioactiveTideConfigurator for the same rule). The build packages it as
  // Scripts/DeepFrontier.SluiceIsBack.dll.SluiceIsBack.optional
  // (tools/unity/DeepFrontierBatchBuild.cs), which Moddable Timberborn's
  // OptionalModsLoader loads only when Sluice is Back! is enabled, before the
  // first context is configured.
  public static class SluiceIsBackBridge {
    public const string ModId = "SluiceIsBack";
    public const string ModAssembly = "SluiceIsBack";
    public const string BridgeAssembly = "DeepFrontier.SluiceIsBack";
    public const string Template = "Sluice.IronTeeth";

    public static bool AssemblyLoaded(string name) => AppDomain.CurrentDomain.GetAssemblies().Any(a => a.GetName().Name == name);
  }

  // A building's "Measures" choice, implemented by the optional bridge's
  // sluice decorator, so main-assembly code (the all-buildings acceptance)
  // can read and set it without referencing the optional assembly.
  public interface IContaminationSubstanceChoice {
    SensedSubstance Substance { get; }
    void SetSubstance(SensedSubstance substance);
  }

  // With Sluice is Back! loaded and the bridge missing, the package is broken:
  // its sluices would ignore radiation silently.
  [Context("Game")]
  public sealed class SluiceIsBackBridgeConfigurator : Configurator {
    protected override void Configure() {
      if (SluiceIsBackBridge.AssemblyLoaded(SluiceIsBackBridge.ModAssembly) && !SluiceIsBackBridge.AssemblyLoaded(SluiceIsBackBridge.BridgeAssembly))
        throw new InvalidOperationException($"Sluice is Back! is loaded but {SluiceIsBackBridge.BridgeAssembly} is not: the Deep Frontier package is missing its optional Scripts DLL");
    }
  }
}
