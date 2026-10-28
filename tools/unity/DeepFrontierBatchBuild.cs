using System;
using System.IO;
using System.Linq;
using Timberborn.ModdingTools.Common;
using UnityEditor;
using UnityEngine;

namespace Timberborn.ModdingTools.ModBuilding {
  // Command-line entry point for the same builder used by ModBuilderWindow.
  public static class DeepFrontierBatchBuild {
    public static void Build() {
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
      var settings = new ModBuilderSettings(
          buildCode: true,
          buildWindowsAssetBundle: true,
          buildMacAssetBundle: false,
          deleteFiles: false,
          buildZipArchive: false,
          compatibilityVersion: "1.1");
      if (!new ModBuilder(new[] { mod }, settings).Build()) {
        throw new InvalidOperationException("The official Deep Frontier build failed. See the Unity build log.");
      }
      PackageOptionalAssembly(mod.Name, "DeepFrontier.ModdableWeathers.dll", "DeepFrontier.ModdableWeathers.dll.ModdableWeathers.optional");
      PackageOptionalAssembly(mod.Name, "DeepFrontier.SluiceIsBack.dll", "DeepFrontier.SluiceIsBack.dll.SluiceIsBack.optional");
      Debug.Log("[DeepFrontier] Official Mod Builder completed successfully.");
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
