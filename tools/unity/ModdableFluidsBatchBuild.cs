using System;
using System.IO;
using System.Linq;
using Timberborn.ModdingTools.Common;
using UnityEditor;
using UnityEngine;

namespace Timberborn.ModdingTools.ModBuilding {
  public static class ModdableFluidsBatchBuild {
    private static readonly string[] ApiAssemblies = { "ModdableFluids", "ModdableFluids.TransportPrototype", "ModdableFluids.GamePrototype", "ModdableFluids.RuntimePrototype" };
    private static readonly string[] Fixtures = { "ModdableFluidsSyntheticReflection", "ModdableFluidsSyntheticCompiled" };

    /// <summary>Builds only the Moddable Fluids package (code and its Windows/macOS shader bundles).</summary>
    public static void Build() => BuildMods(new[] { "ModdableFluids" });

    /// <summary>
    /// Builds the API and the two flag-gated synthetic consumer fixtures in one official build.
    /// tools/build_moddable_fluids.ps1 moves every package out of the Mods folder immediately afterwards.
    /// </summary>
    public static void BuildWithSyntheticFixtures() => BuildMods(new[] { "ModdableFluids" }.Concat(Fixtures).ToArray());

    /// <summary>The API and the More Fluids package (public API only, provisional data).</summary>
    public static void BuildWithMoreFluids() => BuildMods(new[] { "ModdableFluids", "MoreFluids" });

    /// <summary>The API, both fixtures and More Fluids.</summary>
    public static void BuildWithSyntheticFixturesAndMoreFluids() => BuildMods(new[] { "ModdableFluids" }.Concat(Fixtures).Concat(new[] { "MoreFluids" }).ToArray());

    private static void BuildMods(string[] names) {
      foreach (var target in new[] { BuildTarget.StandaloneWindows64, BuildTarget.StandaloneOSX })
        if (!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, target))
          throw new InvalidOperationException("Install Unity build support for " + target + " before building Moddable Fluids bundles.");
      var all = new ModFinder().GetAllMods().ToArray();
      foreach (string name in names) {
        var mod = all.Single(value => value.Name == name);
        // Only the API has assets: the shared-rendering shader variants.
        bool bundles = name == "ModdableFluids";
        var settings = new ModBuilderSettings(buildCode: true, buildWindowsAssetBundle: bundles,
          buildMacAssetBundle: bundles, deleteFiles: true, buildZipArchive: false, compatibilityVersion: "1.1");
        if (!new ModBuilder(new[] { mod }, settings).Build()) throw new InvalidOperationException("Official Moddable Fluids build failed for " + name);
        var directory = Path.Combine(ModDirectories.ModsDirectory, name, "version-1.1");
        var expected = name == "ModdableFluids" ? ApiAssemblies : new[] { name };
        foreach (string assembly in expected)
          if (!File.Exists(Path.Combine(directory, "Scripts", assembly + ".dll"))) throw new InvalidOperationException("Official package " + name + " lacks " + assembly);
        // The official bundle builder does not propagate a failed BuildAssetBundles result.
        if (bundles)
          foreach (var platform in new[] { "win", "mac" }) {
            var bundle = Path.Combine(directory, "AssetBundles", "moddablefluids_" + platform);
            if (!File.Exists(bundle) || new FileInfo(bundle).Length == 0) throw new InvalidOperationException("The official build produced no asset bundle: " + bundle);
          }
      }
      Debug.Log("[ModdableFluids] Official Mod Builder completed: " + string.Join(", ", names));
    }
  }
}
