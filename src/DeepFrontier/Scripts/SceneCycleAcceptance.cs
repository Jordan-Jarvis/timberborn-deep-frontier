using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Bindito.Core;
using DeepFrontier.Scripts.Radiation;
using Timberborn.BlueprintSystem;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSceneLoading;
using Timberborn.MainMenuSceneLoading;
using Timberborn.MapRepositorySystem;
using Timberborn.SingletonSystem;
using Timberborn.TimbermeshMaterials;
using Timberborn.WaterSystemRendering;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Explicit test launch only: -deepFrontierLoadAcceptance -deepFrontierSceneCycle "<step>;<step>;..."
  // with steps save:<full path of a .timber> (MemoryLoadProbe.Find: it must lie in the native save
  // repository) or builtin:<map> / user:<map> (an Iron Teeth new game in "Memory Test"), all in one
  // process, as a player who loads a save, returns to the main menu and starts another game.
  //   - Every main menu (IndustrialAcceptanceLoader, frame 30) reads the native water materials
  //     (WaterMeshSpec) and the TerrainURP materials of MaterialCollection Common through the menu's
  //     own ISpecService, records shader, keywords and every native shader property, and requires the
  //     first menu's record exactly (the first menu is before any game, so pristine). Then it starts
  //     the next step, or logs COMPLETE after the last.
  //   - Every game scene (frame 60, after the startup panels) requires the Deep Frontier radiation
  //     variants on those same materials, then returns to the main menu with native
  //     MainMenuSceneLoader.OpenMainMenu (no autosave). A failed game load crashes, which the watcher
  //     reports.
  internal static class SceneCycleAcceptance {
    internal const string Flag = "-deepFrontierSceneCycle";
    internal const string Tag = "[DeepFrontier SceneCycle]";
    private static string[] _steps;
    private static int _next, _games;
    private static List<MaterialRecord> _baseline;
    private static bool _failed;

    internal static bool Active => Environment.GetCommandLineArgs().Contains(Flag);

    private static string[] Steps() {
      if (_steps != null) return _steps;
      var args = Environment.GetCommandLineArgs();
      int index = Array.IndexOf(args, Flag);
      if (index < 0 || index == args.Length - 1) throw new InvalidOperationException(Flag + " must be followed by its steps");
      if (!args.Contains("-deepFrontierLoadAcceptance")) throw new InvalidOperationException(Flag + " requires -deepFrontierLoadAcceptance");
      _steps = args[index + 1].Trim('"').Split(';').Select(s => s.Trim()).Where(s => s != "").ToArray();
      if (_steps.Length == 0) throw new InvalidOperationException(Flag + " has no steps");
      return _steps;
    }

    internal static void MainMenu(ISpecService specs, GameSaveRepository saves, GameSceneLoader loader, MapRepository maps) {
      var steps = Steps();
      if (_failed) return;
      var records = MaterialRecord.ReadAll(specs, game: false);
      if (_baseline == null) {
        _baseline = records;
        foreach (var record in records) Debug.Log(Tag + " menu before any game: " + record);
      } else {
        for (int i = 0; i < records.Count; i++) {
          var now = records[i]; var before = _baseline[i];
          string problem = now.DifferenceFrom(before);
          if (problem != null) { Fail("main menu after game " + _games + ": " + now.Material + " " + problem); return; }
          Debug.Log(Tag + " menu after game " + _games + ": " + now.Material + " native as before any game ("
            + (ReferenceEquals(now.Object, before.Object) ? "same material object" : "material reloaded") + "): " + now.Summary);
        }
      }
      if (_next == steps.Length) {
        Debug.Log(Tag + " COMPLETE " + _games + " game scenes in one process (" + string.Join("; ", steps)
          + "); every main menu found the native water and terrain materials exactly as before the first game");
        return;
      }
      string step = steps[_next++];
      if (step.StartsWith("save:", StringComparison.Ordinal)) {
        var save = MemoryLoadProbe.Find(saves, System.IO.Path.GetFullPath(step.Substring(5)));
        Debug.Log(Tag + " step " + _next + "/" + steps.Length + ": loading " + save + " through native GameSceneLoader");
        loader.StartSaveGame(save);
      } else {
        var map = MemoryLoadProbe.Map(maps, step);
        Debug.Log(Tag + " step " + _next + "/" + steps.Length + ": Iron Teeth new game on " + map + " through native GameSceneLoader");
        loader.StartNewGameInstantly("IronTeeth", map, MemoryLoadProbe.TestSettlement);
      }
    }

    internal static void GameLoaded(ISpecService specs, MainMenuSceneLoader mainMenu) {
      _games++;
      foreach (var record in MaterialRecord.ReadAll(specs, game: true)) {
        if (record.ShaderName != record.VariantName) {
          Fail("game " + _games + ": " + record.Material + " draws with " + record.ShaderName + ", expected " + record.VariantName);
          return;
        }
        Debug.Log(Tag + " game " + _games + ": " + record.Material + " draws with " + record.ShaderName);
      }
      Debug.Log(Tag + " game " + _games + " loaded; returning to the main menu (native OpenMainMenu)");
      mainMenu.OpenMainMenu();
    }

    private static void Fail(string message) {
      _failed = true;
      Debug.LogError(Tag + " FAILED " + message);
    }

    private sealed class MaterialRecord {
      internal Material Object;
      internal string Material, ShaderName, NativeName, VariantName, Summary;
      private Shader _shader;
      private string _keywords, _properties;

      internal static List<MaterialRecord> ReadAll(ISpecService specs, bool game) {
        var water = specs.GetSingleSpec<WaterMeshSpec>();
        var list = new List<MaterialRecord> {
          Read(water.OpaqueMaterial.Asset, RadiationShading.WaterOpaqueNative, RadiationShading.WaterOpaqueVariantName, game),
          Read(water.TransparentMaterial.Asset, RadiationShading.WaterTransparentNative, RadiationShading.WaterTransparentVariantName, game),
        };
        var common = specs.GetSpecs<MaterialCollectionSpec>().Where(s => s.CollectionId == "Common")
          .SelectMany(s => s.Materials).Select(m => m.Asset).ToList();
        foreach (var name in RadiationShading.TerrainMaterials) {
          var matches = common.Where(m => m.name == name).Distinct().ToList();
          if (matches.Count != 1) throw new InvalidOperationException(Tag + " MaterialCollection Common has " + matches.Count + " materials named " + name);
          list.Add(Read(matches[0], RadiationShading.TerrainNative, RadiationShading.TerrainVariantName, game));
        }
        return list;
      }

      private static MaterialRecord Read(Material material, string native, string variant, bool game) {
        var shader = material.shader;
        var record = new MaterialRecord {
          Object = material, Material = material.name, ShaderName = shader.name, NativeName = native, VariantName = variant, _shader = shader,
          _keywords = string.Join(" ", material.enabledKeywords.Select(k => k.name).OrderBy(k => k, StringComparer.Ordinal)),
        };
        if (!game) {
          if (shader.name != native) throw new InvalidOperationException(Tag + " " + material.name + " draws with " + shader.name + " in the main menu, expected " + native);
          record._properties = Properties(material, shader);
        }
        record.Summary = "shader " + record.ShaderName + ", keywords [" + record._keywords + "], " + shader.GetPropertyCount() + " native properties";
        return record;
      }

      // Every property the native shader declares, with the material's value.
      private static string Properties(Material material, Shader shader) {
        var parts = new List<string>();
        for (int i = 0; i < shader.GetPropertyCount(); i++) {
          string name = shader.GetPropertyName(i);
          string value = shader.GetPropertyType(i) switch {
            UnityEngine.Rendering.ShaderPropertyType.Color => material.GetColor(name).ToString("R"),
            UnityEngine.Rendering.ShaderPropertyType.Vector => material.GetVector(name).ToString("R"),
            UnityEngine.Rendering.ShaderPropertyType.Float or UnityEngine.Rendering.ShaderPropertyType.Range => material.GetFloat(name).ToString("R", CultureInfo.InvariantCulture),
            UnityEngine.Rendering.ShaderPropertyType.Int => material.GetInteger(name).ToString(CultureInfo.InvariantCulture),
            UnityEngine.Rendering.ShaderPropertyType.Texture => material.GetTexture(name) is Texture t ? t.name : "none",
            _ => throw new InvalidOperationException(Tag + " " + material.name + "." + name + " has an unknown property type " + shader.GetPropertyType(i)),
          };
          parts.Add(name + "=" + value);
        }
        return string.Join("; ", parts);
      }

      internal string DifferenceFrom(MaterialRecord before) {
        if (_shader != before._shader) return "has shader " + ShaderName + " (" + (_shader == null ? "none" : "another object") + "), before any game " + before.ShaderName;
        if (_keywords != before._keywords) return "has keywords [" + _keywords + "], before any game [" + before._keywords + "]";
        if (_properties != before._properties) return "native property values changed: now " + _properties + "; before any game " + before._properties;
        return null;
      }

      public override string ToString() => Material + ": " + Summary;
    }
  }

  [Context("Game")]
  public sealed class SceneCycleProbeConfigurator : Configurator {
    protected override void Configure() {
      if (SceneCycleAcceptance.Active) Bind<SceneCycleProbe>().AsSingleton();
    }
  }

  public sealed class SceneCycleProbe : IUpdatableSingleton {
    private readonly ISpecService _specs;
    private readonly MainMenuSceneLoader _mainMenu;
    private int _frame;

    public SceneCycleProbe(ISpecService specs, MainMenuSceneLoader mainMenu) { _specs = specs; _mainMenu = mainMenu; }

    // Startup panels are dismissed before frame 60 (AcceptanceStartupPanels).
    public void UpdateSingleton() {
      if (++_frame == 60) SceneCycleAcceptance.GameLoaded(_specs, _mainMenu);
    }
  }
}
