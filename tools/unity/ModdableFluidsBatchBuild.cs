using System;
using System.IO;
using System.Linq;
using Timberborn.ModdingTools.Common;
using UnityEngine;

namespace Timberborn.ModdingTools.ModBuilding {
  public static class ModdableFluidsBatchBuild {
    private static readonly string[] ApiAssemblies = { "ModdableFluids", "ModdableFluids.TransportPrototype", "ModdableFluids.GamePrototype", "ModdableFluids.RuntimePrototype" };
    private static readonly string[] Fixtures = { "ModdableFluidsSyntheticReflection", "ModdableFluidsSyntheticCompiled" };

    /// <summary>Builds only the Moddable Fluids package.</summary>
    public static void Build() => BuildMods(new[] { "ModdableFluids" });

    /// <summary>
    /// Builds the API and the two flag-gated synthetic consumer fixtures in one official build.
    /// tools/build_moddable_fluids.ps1 moves the fixtures out of the Mods folder immediately afterwards.
    /// </summary>
    public static void BuildWithSyntheticFixtures() => BuildMods(new[] { "ModdableFluids" }.Concat(Fixtures).ToArray());

    private static void BuildMods(string[] names) {
      var all = new ModFinder().GetAllMods().ToArray();
      var mods = names.Select(name => all.Single(value => value.Name == name)).ToArray();
      var settings = new ModBuilderSettings(buildCode: true, buildWindowsAssetBundle: false,
        buildMacAssetBundle: false, deleteFiles: true, buildZipArchive: false, compatibilityVersion: "1.1");
      if (!new ModBuilder(mods, settings).Build()) throw new InvalidOperationException("Official Moddable Fluids build failed for " + string.Join(", ", names));
      foreach (string name in names) {
        var directory = Path.Combine(ModDirectories.ModsDirectory, name, "version-1.1", "Scripts");
        var expected = name == "ModdableFluids" ? ApiAssemblies : new[] { name };
        foreach (string assembly in expected)
          if (!File.Exists(Path.Combine(directory, assembly + ".dll"))) throw new InvalidOperationException("Official package " + name + " lacks " + assembly);
      }
      Debug.Log("[ModdableFluids] Official Mod Builder completed: " + string.Join(", ", names));
    }
  }
}
