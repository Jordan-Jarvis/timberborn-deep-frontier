using System;
using System.Collections.Generic;
using UnityEditor.Build;
using UnityEditor.Rendering;
using UnityEngine;
using UnityEngine.Rendering;

namespace Timberborn.ModdingTools.ModBuilding {
  /// <summary>
  /// Strips the variants of Deep Frontier's and Moddable Fluids' own shaders (names starting DeepFrontier/ or
  /// ModdableFluids/) that the game never draws; every other shader is left to Unity and URP. Rules and the game data
  /// behind them: docs/unity-build-performance.md. tools/asset-pipeline/check_bundle_shaders.py compares each built
  /// bundle with the installed game's own shaders, so a rule that strips something the game draws fails the build.
  /// Staged into the shared Unity project by tools/stage_deep_frontier.ps1 and tools/build_moddable_fluids.ps1; it runs
  /// after URP's stripping in player and asset bundle builds alike and logs each pass's variant count before and after.
  /// </summary>
  public sealed class ModShaderVariantStripping : IPreprocessShaders {
    private const string Tag = "[ModShaderVariantStripping]";
    // URP strips LightMode Universal2D passes when no renderer is a Renderer2DData (ShaderScriptableStripper
    // StripUnusedPass_2D), but it compares the pass name, and Shader Graph names that pass "Universal 2D". The game has no
    // Renderer2DData, so the pass is never drawn.
    private const string Universal2D = "Universal2D";
    private const string Outflows = "_CALCULATE_OUTFLOWS";
    private const string Triplanar = "_USE_TRIPLANAR_SPLATMAP";
    private const string Splatmap = "_SAMPLE_SPLATMAP";

    // After URP (callbackOrder 0), so the logged counts are what URP left.
    public int callbackOrder => 100;

    public void OnProcessShader(Shader shader, ShaderSnippetData snippet, IList<ShaderCompilerData> data) {
      string name = shader.name;
      if (!name.StartsWith("DeepFrontier/", StringComparison.Ordinal) && !name.StartsWith("ModdableFluids/", StringComparison.Ordinal)) return;
      Func<HashSet<string>, HashSet<string>, bool> keep = Rule(name);
      if (data.Count == 0) return;
      string lightMode = shader.FindPassTagValue((int)snippet.pass.SubshaderIndex, (int)snippet.pass.PassIndex, new ShaderTagId("LightMode")).name;
      string where = $"{name} | {snippet.passName} ({lightMode}) | {snippet.shaderType} | {data[0].shaderCompilerPlatform}";
      int before = data.Count;
      if (lightMode == Universal2D) {
        data.Clear();
        Debug.Log($"{Tag} {where}: {before} -> 0 (pass drawn only by the 2D renderer)");
        return;
      }
      var variants = new List<HashSet<string>>(before);
      var declared = new HashSet<string>(StringComparer.Ordinal);
      foreach (var variant in data) {
        var keywords = new HashSet<string>(StringComparer.Ordinal);
        foreach (var keyword in variant.shaderKeywordSet.GetShaderKeywords()) keywords.Add(keyword.name);
        variants.Add(keywords);
        declared.UnionWith(keywords);
      }
      var kept = variants.ConvertAll(keywords => keep(keywords, declared));
      if (!kept.Contains(true)) throw new InvalidOperationException($"{Tag} {where}: the rules would strip every variant of a drawn pass");
      for (int i = data.Count - 1; i >= 0; i--) {
        if (!kept[i]) data.RemoveAt(i);
      }
      Debug.Log($"{Tag} {where}: {before} -> {data.Count}");
    }

    // Each of our shaders is a variant of a native graph that the game draws only on its own materials (native water
    // materials, or copies of them, and the native terrain materials), whose material keywords the game never changes.
    private static Func<HashSet<string>, HashSet<string>, bool> Rule(string shader) {
      switch (shader) {
        // Every native water material enables _CALCULATE_OUTFLOWS.
        case "DeepFrontier/RadioactiveWaterURP_Opaque":
        case "DeepFrontier/RadioactiveWaterURP_Transparent":
        case "ModdableFluids/FluidWaterURP_Opaque":
        case "ModdableFluids/FluidWaterURP_Transparent":
          return (keywords, declared) => !declared.Contains(Outflows) || keywords.Contains(Outflows);
        // No native terrain material, and no variant of the game's own TerrainURP, has triplanar splatmapping without
        // the splatmap. Moddable Fluids' terrain overlay draws on scene copies of those materials, with their keywords.
        case "DeepFrontier/IrradiatedTerrainURP":
        case "ModdableFluids/FluidTerrainURP":
          return (keywords, declared) => !keywords.Contains(Triplanar) || keywords.Contains(Splatmap);
        default:
          throw new InvalidOperationException($"{Tag} {shader} has no stripping rule: add one with its evidence "
            + "(docs/unity-build-performance.md) here and in tools/asset-pipeline/check_bundle_shaders.py");
      }
    }
  }
}
