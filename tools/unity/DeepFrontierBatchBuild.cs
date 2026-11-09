using System;
using System.IO;
using System.Linq;
using Timberborn.ModdingTools.Common;
using UnityEditor;
using UnityEngine;

namespace Timberborn.ModdingTools.ModBuilding {
  // Command-line entry point for the same builder used by ModBuilderWindow.
  public static class DeepFrontierBatchBuild {
    private const string OptionalPrefix = "DeepFrontier.";
    public static void Build() {
      foreach (var target in new[] { BuildTarget.StandaloneWindows64, BuildTarget.StandaloneOSX }) {
        if (!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, target))
          throw new InvalidOperationException("Install Unity build support for " + target + " before building Deep Frontier.");
      }
      if (!EditorApplication.ExecuteMenuItem("Deep Frontier/Create Materials")) {
        throw new InvalidOperationException("Deep Frontier material authoring menu is unavailable.");
      }
      var resources = "Assets/Mods/DeepFrontier/AssetBundles/Resources";
      // Pile meshes are AssetRef<Mesh>: each must have imported a Mesh sub-asset
      // (Create Materials sets the Timbermesh importer's _createMeshAsset). The
      // menu step's exceptions do not fail ExecuteMenuItem, so check the result.
      foreach (var pile in Directory.GetFiles(Path.Combine(resources, "StockpileGoodModels"), "*.timbermesh", SearchOption.AllDirectories)) {
        var assetPath = pile.Replace(Path.DirectorySeparatorChar, '/');
        if (AssetDatabase.LoadAllAssetsAtPath(assetPath).OfType<UnityEngine.Mesh>().Count() != 1)
          throw new InvalidOperationException("Pile mesh did not import as one Mesh asset: " + assetPath);
      }
      var duplicate = Directory.GetFiles(resources, "*", SearchOption.AllDirectories)
          .Where(path => !path.EndsWith(".meta"))
          .GroupBy(path => Path.Combine(Path.GetDirectoryName(path), Path.GetFileNameWithoutExtension(path)), StringComparer.OrdinalIgnoreCase)
          .FirstOrDefault(group => group.Count() > 1);
      if (duplicate != null) throw new InvalidOperationException("Bundled resource name collision: " + string.Join(", ", duplicate));
      var mod = new ModFinder().GetAllMods().Single(mod => mod.Name == "DeepFrontier");
      // -modBundles reuse: the bundle inputs match those of the last verified build (tools/UnityBundleCache.ps1), whose
      // bundles the build script installs after this one; only the code is built.
      bool buildBundles = BundlesRequested();
      var settings = new ModBuilderSettings(
          buildCode: true,
          buildWindowsAssetBundle: buildBundles,
          // macOS players load deepfrontier_mac; without it every bundled asset fails
          // ("Failed to load asset at Materials/DeepFrontierArt/DFArtTimber", player reports 2026-11-04).
          buildMacAssetBundle: buildBundles,
          deleteFiles: false,
          buildZipArchive: false,
          compatibilityVersion: "1.1");
      if (!new ModBuilder(new[] { mod }, settings).Build()) {
        throw new InvalidOperationException("The official Deep Frontier build failed. See the Unity build log.");
      }
      var bundles = Path.Combine(ModDirectories.ModsDirectory, mod.Name, "version-1.1", "AssetBundles");
      if (buildBundles) {
        // The official bundle builder does not propagate a failed BuildAssetBundles
        // return value. Reject an incomplete package before reporting success.
        foreach (var platform in new[] { "win", "mac" }) {
          var bundle = Path.Combine(bundles, "deepfrontier_" + platform);
          if (!File.Exists(bundle) || new FileInfo(bundle).Length == 0)
            throw new InvalidOperationException("The official build produced no asset bundle: " + bundle);
        }
      } else if (Directory.Exists(bundles)) {
        throw new InvalidOperationException("Asset bundles were not built (-modBundles reuse), yet the package has " + bundles);
      }
      // Every asmdef other than the main DeepFrontier one is an optional-mod integration named
      // DeepFrontier.<ModId> (tools/validate_mod_dependencies.mjs checks each ModId is in the
      // manifest's OptionalMods and that only its assembly uses that mod's types).
      foreach (var asmdef in Directory.GetFiles(Path.Combine(mod.AbsolutePath, "Scripts"), "*.asmdef", SearchOption.AllDirectories)) {
        var name = Path.GetFileNameWithoutExtension(asmdef);
        if (name == "DeepFrontier") continue;
        if (!name.StartsWith(OptionalPrefix, StringComparison.Ordinal))
          throw new InvalidOperationException("Optional assembly " + asmdef + " must be named " + OptionalPrefix + "<ModId>");
        PackageOptionalAssembly(mod.Name, name + ".dll", name + ".dll." + name.Substring(OptionalPrefix.Length) + ".optional");
      }
      Debug.Log("[DeepFrontier] Official Mod Builder completed successfully" + (buildBundles ? "." : " (code only; -modBundles reuse)."));
    }

    // -modBundles build|reuse, required: the build scripts decide from the bundle inputs' fingerprint.
    private static bool BundlesRequested() {
      var args = Environment.GetCommandLineArgs();
      int index = Array.IndexOf(args, "-modBundles");
      string mode = index >= 0 && index + 1 < args.Length ? args[index + 1] : null;
      if (mode == "build") return true;
      if (mode == "reuse") return false;
      throw new InvalidOperationException("Pass -modBundles build or -modBundles reuse (tools/UnityBundleCache.ps1).");
    }

    // Moddable Timberborn's OptionalModsLoader loads Scripts/<name>.dll.<ModId>.optional
    // only when mod <ModId> is enabled. As a plain .dll the game would load it
    // unconditionally, and its types implement the optional mod's types, so
    // Timberborn's unguarded Assembly.GetTypes() fails whenever that mod is absent.
    private static void PackageOptionalAssembly(string modName, string dll, string optionalName) {
      var scripts = Path.Combine(ModDirectories.ModsDirectory, modName, "version-1.1", "Scripts");
      var built = Path.Combine(scripts, dll);
      if (!File.Exists(built)) throw new InvalidOperationException("The official build produced no " + built);
      var optional = Path.Combine(scripts, optionalName);
      File.Copy(built, optional, true);
      File.Delete(built);
      Debug.Log("[DeepFrontier] Packaged " + dll + " as " + optionalName + ".");
    }
  }
}
