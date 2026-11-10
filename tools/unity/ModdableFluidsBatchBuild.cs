using System;
using System.IO;
using System.Linq;
using Timberborn.ModdingTools.Common;
using UnityEditor;
using UnityEngine;

namespace Timberborn.ModdingTools.ModBuilding {
  public static class ModdableFluidsBatchBuild {
    private static readonly string[] ApiAssemblies = { "ModdableFluids", "ModdableFluids.TransportPrototype", "ModdableFluids.GamePrototype", "ModdableFluids.RuntimePrototype" };
    // The tides' Moddable Weathers adapter (src/ModdableFluids/ModdableWeathers): an optional assembly named
    // ModdableFluids.<ModId>, packaged as Scripts/ModdableFluids.<ModId>.dll.<ModId>.optional.
    private const string OptionalPrefix = "ModdableFluids.";
    private static readonly string[] OptionalAssemblies = { "ModdableFluids.ModdableWeathers" };
    private static readonly string[] Fixtures = { "ModdableFluidsSyntheticReflection", "ModdableFluidsSyntheticCompiled" };

    /// <summary>Builds only the Moddable Fluids package (code and its Windows/macOS shader bundles).</summary>
    public static void Build() => BuildMods(new[] { "ModdableFluids" });

    /// <summary>
    /// Builds the API and the two flag-gated synthetic consumer fixtures in one official build.
    /// tools/build_moddable_fluids.ps1 moves every package out of the Mods folder immediately afterwards.
    /// </summary>
    public static void BuildWithSyntheticFixtures() => BuildMods(new[] { "ModdableFluids" }.Concat(Fixtures).ToArray());

    /// <summary>The API and the More Fluids package: its code and its Data (blueprints, models, icons, sprites, localization).</summary>
    public static void BuildWithMoreFluids() => BuildMods(new[] { "ModdableFluids", "MoreFluids" });

    /// <summary>The API, both fixtures and More Fluids.</summary>
    public static void BuildWithSyntheticFixturesAndMoreFluids() => BuildMods(new[] { "ModdableFluids" }.Concat(Fixtures).Concat(new[] { "MoreFluids" }).ToArray());

    private static void BuildMods(string[] names) {
      foreach (var target in new[] { BuildTarget.StandaloneWindows64, BuildTarget.StandaloneOSX })
        if (!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, target))
          throw new InvalidOperationException("Install Unity build support for " + target + " before building Moddable Fluids bundles.");
      // -modBundles reuse: the API's bundle inputs match those of the last verified build (tools/UnityBundleCache.ps1),
      // whose bundles tools/build_moddable_fluids.ps1 installs after this one; only the code is built.
      bool buildBundles = BundlesRequested();
      var all = new ModFinder().GetAllMods().ToArray();
      foreach (string name in names) {
        var mod = all.Single(value => value.Name == name);
        // Only the API has Unity assets: the shared-rendering shader variants. More Fluids ships its Data, which the
        // official AssetsCopier copies as authored into the package root (tools/build_moddable_fluids.ps1 compares it file by file).
        bool bundles = buildBundles && name == "ModdableFluids";
        var settings = new ModBuilderSettings(buildCode: true, buildWindowsAssetBundle: bundles,
          buildMacAssetBundle: bundles, deleteFiles: true, buildZipArchive: false, compatibilityVersion: "1.1");
        if (!new ModBuilder(new[] { mod }, settings).Build()) throw new InvalidOperationException("Official Moddable Fluids build failed for " + name);
        var directory = Path.Combine(ModDirectories.ModsDirectory, name, "version-1.1");
        var expected = name == "ModdableFluids" ? ApiAssemblies : new[] { name };
        foreach (string assembly in expected)
          if (!File.Exists(Path.Combine(directory, "Scripts", assembly + ".dll"))) throw new InvalidOperationException("Official package " + name + " lacks " + assembly);
        if (name == "ModdableFluids")
          foreach (string assembly in OptionalAssemblies)
            PackageOptionalAssembly(directory, assembly + ".dll", assembly + ".dll." + assembly.Substring(OptionalPrefix.Length) + ".optional");
        // The official AssetsCopier copies Data's contents into the package root (as in Deep Frontier's package).
        if (name == "MoreFluids" && !File.Exists(Path.Combine(directory, "Localizations", "enUS.csv")))
          throw new InvalidOperationException("Official package MoreFluids lacks its Data (Localizations/enUS.csv at the package root)");
        // The official bundle builder does not propagate a failed BuildAssetBundles result.
        if (bundles)
          foreach (var platform in new[] { "win", "mac" }) {
            var bundle = Path.Combine(directory, "AssetBundles", "moddablefluids_" + platform);
            if (!File.Exists(bundle) || new FileInfo(bundle).Length == 0) throw new InvalidOperationException("The official build produced no asset bundle: " + bundle);
          }
        else if (Directory.Exists(Path.Combine(directory, "AssetBundles")))
          throw new InvalidOperationException("Asset bundles were not built for " + name + ", yet its package has an AssetBundles folder");
      }
      Debug.Log("[ModdableFluids] Official Mod Builder completed: " + string.Join(", ", names) + (buildBundles ? "" : " (code only; -modBundles reuse)"));
    }

    // As Deep Frontier's build (DeepFrontierBatchBuild.PackageOptionalAssembly): Moddable Timberborn's OptionalModsLoader
    // loads Scripts/<name>.dll.<ModId>.optional only while mod <ModId> is enabled. As a plain .dll the game would load it
    // unconditionally, and its types derive from the optional mod's types, so enumerating them fails without that mod.
    private static void PackageOptionalAssembly(string directory, string dll, string optionalName) {
      var scripts = Path.Combine(directory, "Scripts");
      var built = Path.Combine(scripts, dll);
      if (!File.Exists(built)) throw new InvalidOperationException("The official build produced no " + built);
      var optional = Path.Combine(scripts, optionalName);
      File.Copy(built, optional, true);
      File.Delete(built);
      Debug.Log("[ModdableFluids] Packaged " + dll + " as " + optionalName + ".");
    }

    // -modBundles build|reuse, required: tools/build_moddable_fluids.ps1 decides from the bundle inputs' fingerprint.
    private static bool BundlesRequested() {
      var args = Environment.GetCommandLineArgs();
      int index = Array.IndexOf(args, "-modBundles");
      string mode = index >= 0 && index + 1 < args.Length ? args[index + 1] : null;
      if (mode == "build") return true;
      if (mode == "reuse") return false;
      throw new InvalidOperationException("Pass -modBundles build or -modBundles reuse (tools/UnityBundleCache.ps1).");
    }
  }
}
