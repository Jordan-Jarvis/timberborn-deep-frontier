using System;
using System.Collections.Generic;
using System.IO;
using Timberborn.ModdingTools.Common;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.Rendering;
using UnityEngine;

namespace Timberborn.ModdingTools.ModBuilding {
  /// <summary>
  /// The official Mod Builder builds a throwaway Windows player only for its script assemblies (ModBuilder.TryBuildProject;
  /// DllFilesCopier copies the mods' DLLs from its Managed folder, nothing else). Unity puts every Resources folder into a
  /// player, and every staged mod keeps its bundle assets under AssetBundles/Resources, so that player compiled every
  /// staged mod's shaders (Moddable Fluids' official build of 2026-11-09 compiled Deep Frontier's terrain and opaque water
  /// variants cold for it). While that player build runs, this strips every variant of every shader under Assets/Mods.
  ///
  /// It strips only between OnPreprocessBuild of a build whose BuildSummary.buildType is Player and whose output is the
  /// Mod Builder's throwaway player (ModDirectories.BuildDirectory/TimberbornModExamples) and the end of that build
  /// (OnPostprocessBuild, or the report's result leaving Unknown). ModBuilder.Build finishes the player build before it
  /// builds any bundle, and a bundle build is never of type Player, so bundles keep their variants; every built bundle is
  /// checked against the game's own shaders (tools/asset-pipeline/check_bundle_shaders.py). The script assemblies are
  /// compiled before the data build that compiles shaders, and the build scripts check that the packaged DLLs are the
  /// compiler's output (Library/Bee/PlayerScriptAssemblies). Unity's own shaders are left alone: they are cache hits
  /// (docs/unity-build-performance.md). Not a bundle input: tools/UnityBundleCache.ps1 leaves this file out of the
  /// fingerprint. Staged by tools/stage_deep_frontier.ps1 and tools/build_moddable_fluids.ps1.
  /// </summary>
  public sealed class PlayerBuildShaderStripping : IPreprocessBuildWithReport, IPostprocessBuildWithReport, IPreprocessShaders {
    private const string Tag = "[PlayerBuildShaderStripping]";
    private const string ModsFolder = "Assets/Mods/";
    // ModBuilder.BuildName, private in the official builder.
    private const string PlayerName = "TimberbornModExamples";
    private static BuildReport s_Build;
    private static int s_Variants;
    private static readonly SortedSet<string> s_Shaders = new SortedSet<string>(StringComparer.Ordinal);

    // Shader callbacks: after URP (0) and before ModShaderVariantStripping (100), which then has no variant to log.
    public int callbackOrder => 50;

    public void OnPreprocessBuild(BuildReport report) {
      s_Build = null;
      s_Variants = 0;
      s_Shaders.Clear();
      var summary = report.summary;
      if (summary.buildType != BuildType.Player || !IsModBuilderPlayer(summary.outputPath)) {
        Debug.Log($"{Tag} {summary.buildType} build to {summary.outputPath}: not the Mod Builder's throwaway player; no shader stripped");
        return;
      }
      s_Build = report;
      Debug.Log($"{Tag} player build: stripping every variant of the shaders under {ModsFolder} (only the player's script assemblies are used)");
    }

    public void OnPostprocessBuild(BuildReport report) {
      if (s_Build == null) return;
      Debug.Log($"{Tag} player build: stripped {s_Variants} variants of mod shaders ({s_Shaders.Count}: {string.Join(", ", s_Shaders)})");
      s_Build = null;
    }

    public void OnProcessShader(Shader shader, ShaderSnippetData snippet, IList<ShaderCompilerData> data) {
      if (data.Count == 0 || !PlayerBuildRunning()) return;
      if (!AssetDatabase.GetAssetPath(shader).StartsWith(ModsFolder, StringComparison.Ordinal)) return;
      s_Variants += data.Count;
      s_Shaders.Add(shader.name);
      data.Clear();
    }

    // A failed player build leaves the report's result Failed; a destroyed report compares equal to null.
    private static bool PlayerBuildRunning() => s_Build != null && s_Build.summary.result == BuildResult.Unknown;

    private static bool IsModBuilderPlayer(string outputPath) {
      if (string.IsNullOrEmpty(outputPath)) return false;
      string folder = Path.GetDirectoryName(Path.GetFullPath(outputPath));
      return string.Equals(folder, Path.GetFullPath(ModDirectories.BuildDirectory), StringComparison.OrdinalIgnoreCase)
        && Path.GetFileNameWithoutExtension(outputPath) == PlayerName;
    }
  }
}
