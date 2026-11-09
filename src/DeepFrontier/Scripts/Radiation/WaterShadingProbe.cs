#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Bindito.Core;
using Timberborn.CameraSystem;
using Timberborn.MapIndexSystem;
using Timberborn.SingletonSystem;
using Timberborn.TimeSystem;
using Timberborn.UILayoutSystem;
using Timberborn.WaterSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.Radiation {
  // In-game check of the radiation shader variants against the native water and terrain shaders
  // (tools/start_water_shading.ps1): -deepFrontierLoadAcceptance -deepFrontierLoadSave "<copy in
  // Memory Test>" -deepFrontierWaterShading <label>. Hides the UI, moves the clock to daytime, aims
  // the native camera at clean water and at badwater, and captures each view with
  //   df      the variants as the game runs them,
  //   native  the native shaders (every RadiationShading.ShaderSwap restored),
  //   dfon    the variants with both radiation keywords forced on (the path every water tile and
  //           terrain cell takes while any radiation is drawn anywhere on the map),
  // then puts the variants and keywords back. Last it adds radioactive water and soil radiation
  // beside the clean water and captures that view with the variants and with the native shaders.
  // Writes outputs/water-shading/<label>/*.png and logs each swapped material's shader, render queue,
  // keywords and property values, and the radiation textures. Its first runs (builds 232-234) found
  // the opaque water drawn at the variant's queue 2450 instead of its native 3000 (docs/radiation.md).
  [Context("Game")]
  public sealed class WaterShadingProbeConfigurator : Configurator {
    protected override void Configure() {
      if (WaterShadingProbe.Label() == null) return;
#if DEEP_FRONTIER_MODDABLE_FLUIDS
      // The probe compares Deep Frontier's own water shader variants with the native shaders; Moddable Fluids draws the water here.
      throw new InvalidOperationException(WaterShadingProbe.Flag + " checks Deep Frontier's water shader variants, which the Moddable Fluids build does not use");
#else
      if (MemoryLoadProbe.SavePath() == null) throw new InvalidOperationException(WaterShadingProbe.Flag + " requires -deepFrontierLoadAcceptance with -deepFrontierLoadSave");
      Bind<WaterShadingProbe>().AsSingleton();
#endif
    }
  }

  internal sealed class WaterShadingProbe : IUpdatableSingleton {
    internal const string Flag = "-deepFrontierWaterShading";
    private const string Tag = "[DeepFrontier WaterShading]";
    private const int StartFrame = 300, SettleFrames = 120, StateFrames = 10;
    private readonly RadiationRenderer _renderer;
    private readonly IRadiationService _radiation;
    private readonly IThreadSafeWaterMap _waterMap;
    private readonly MapIndexService _mapIndex;
    private readonly CameraService _camera;
    private readonly UIVisibilityManager _ui;
    private readonly IDayNightCycle _clock;
    private readonly Queue<(int frames, string what, Action action)> _steps = new();
    private string _folder;
    private int _frame, _next;
    private bool _waterKeyword, _soilKeyword, _done;

    public WaterShadingProbe(RadiationRenderer renderer, IRadiationService radiation, IThreadSafeWaterMap waterMap,
        MapIndexService mapIndex, CameraService camera, UIVisibilityManager ui, IDayNightCycle clock) {
      _renderer = renderer; _radiation = radiation; _waterMap = waterMap; _mapIndex = mapIndex;
      _camera = camera; _ui = ui; _clock = clock;
    }

    internal static string Label() {
      var args = Environment.GetCommandLineArgs();
      int i = Array.IndexOf(args, Flag);
      if (i < 0) return null;
      if (i + 1 >= args.Length || args[i + 1].StartsWith("-", StringComparison.Ordinal)) throw new InvalidOperationException(Flag + " must be followed by a label");
      return args[i + 1].Trim('"');
    }

    public void UpdateSingleton() {
      if (_done) return;
      if (++_frame == StartFrame) Plan();
      if (_frame < StartFrame || _frame < _next) return;
      if (_steps.Count == 0) {
        _done = true;
        Debug.Log($"{Tag} COMPLETE {_folder}");
        return;
      }
      var (frames, what, action) = _steps.Dequeue();
      action();
      if (what != null) Debug.Log($"{Tag} {what}");
      _next = _frame + frames;
    }

    private void Plan() {
      _folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "TimberbornModding", "outputs", "water-shading", Label());
      Directory.CreateDirectory(_folder);
      if (_ui.GUIVisible) typeof(UIVisibilityManager).GetMethod("ToggleGUIVisibility", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(_ui, null);
      // Native DayNightCycle: daytime runs from hour 0 for DaytimeLengthInHours. Aim for 40% into it.
      float target = _clock.DaytimeLengthInHours * 0.4f;
      float jump = (target - _clock.HoursPassedToday + 24f) % 24f;
      if (jump > 0.5f) _clock.JumpTimeInHours(jump);
      _waterKeyword = Shader.IsKeywordEnabled(RadiationShading.WaterKeyword);
      _soilKeyword = Shader.IsKeywordEnabled(RadiationShading.SoilKeyword);
      LogState("loaded");

      var clean = FindWater(c => c < 0.001f, "clean");
      var bad = FindWater(c => c > 0.6f, "badwater");
      foreach (var (name, cell) in new[] { ("clean", clean), ("badwater", bad) }) {
        if (cell == null) { Debug.LogWarning($"{Tag} no {name} water body found in this save"); continue; }
        Aim(name, cell.Value);
        Capture(name, "df", () => { });
        Capture(name, "native", () => Swap(false));
        Capture(name, "dfon", () => { Swap(true); Keywords(true, true); });
        Step(StateFrames, $"{name}: variants and keywords restored", () => Keywords(_waterKeyword, _soilKeyword));
        Capture(name, "df2", () => { });
      }
      if (clean is { } spot) {
        Step(1, "adding radioactive water and soil radiation beside the clean water", () => Irradiate(spot));
        Step(900, null, () => { });
        Aim("radioactive", spot);
        Step(1, null, () => LogState("after irradiation"));
        Capture("radioactive", "df", () => { });
        Capture("radioactive", "native", () => Swap(false));
        Step(StateFrames, "radioactive: variants restored", () => Swap(true));
      }
    }

    private void Step(int frames, string what, Action action) => _steps.Enqueue((frames, what, action));

    private void Aim(string name, Vector3Int cell) {
      float surface = _waterMap.WaterHeightOrFloor(cell);
      Step(SettleFrames, $"{name}: camera on {cell} (surface {surface:F2})", () => {
        _camera.MoveTargetTo(new Vector3(cell.x + 0.5f, surface, cell.y + 0.5f));
        _camera.VerticalAngle = 45f; _camera.HorizontalAngle = 35f;
        _camera.ZoomLevel = ZoomFor(28f);
      });
    }

    // State change, then the capture StateFrames later (ScreenCapture writes at the end of that frame).
    private void Capture(string name, string state, Action apply) {
      Step(StateFrames, null, apply);
      Step(StateFrames, null, () => {
        ScreenCapture.CaptureScreenshot(Path.Combine(_folder, $"{name}-{state}.png"));
        Debug.Log($"{Tag} captured {name}-{state} ({Describe()})");
      });
    }

    private void Swap(bool variant) {
      foreach (var swap in _renderer.Swaps) {
        if (variant) swap.Apply();
        else if (swap.Restore() is string problem) throw new InvalidOperationException(problem);
      }
    }

    private static void Keywords(bool water, bool soil) {
      RadiationShading.SetKeyword(RadiationShading.WaterKeyword, water);
      RadiationShading.SetKeyword(RadiationShading.SoilKeyword, soil);
    }

    private string Describe() {
      var swaps = _renderer.Swaps;
      return $"water shader {swaps[0].Material.shader.name} queue {swaps[0].Material.renderQueue}, terrain shader {swaps[2].Material.shader.name}, " +
        $"water keyword {Shader.IsKeywordEnabled(RadiationShading.WaterKeyword)}, soil keyword {Shader.IsKeywordEnabled(RadiationShading.SoilKeyword)}";
    }

    private void LogState(string when) {
      var global = Shader.enabledGlobalKeywords.Select(k => k.name).OrderBy(n => n);
      Debug.Log($"{Tag} {when}: global keywords [{string.Join(" ", global)}]; total water radiation {_radiation.TotalWaterRadiation:F3}");
      foreach (var swap in _renderer.Swaps) {
        var m = swap.Material;
        Debug.Log($"{Tag} {when}: {m.name} shader {m.shader.name} queue {m.renderQueue} (shader {m.shader.renderQueue}) MotionVectors pass {(m.GetShaderPassEnabled("MotionVectors") ? "enabled" : "disabled")} keywords [{string.Join(" ", m.enabledKeywords.Select(k => k.name))}]");
        Debug.Log($"{Tag} {when}: {m.name} properties {Properties(m)}");
      }
      foreach (var name in new[] { "_DFOldRadioactivity", "_DFNewRadioactivity", "_DFIrradiatedSoilMap", "_OldContaminations", "_NewContaminations", "_ContaminationMap" }) {
        var texture = Shader.GetGlobalTexture(name);
        Debug.Log($"{Tag} {when}: global {name} = {(texture == null ? "none" : $"{texture.name} {texture.width}x{texture.height} {texture.dimension}" + (texture is Texture2DArray a ? $" x{a.depth} {a.format}" : ""))}");
      }
    }

    // Every property of the material's current shader with the value the material holds.
    private static string Properties(Material material) {
      var shader = material.shader;
      var parts = new List<string>();
      for (int i = 0; i < shader.GetPropertyCount(); i++) {
        string name = shader.GetPropertyName(i);
        string value = shader.GetPropertyType(i) switch {
          UnityEngine.Rendering.ShaderPropertyType.Color => material.GetColor(name).ToString("F4"),
          UnityEngine.Rendering.ShaderPropertyType.Vector => material.GetVector(name).ToString("F4"),
          UnityEngine.Rendering.ShaderPropertyType.Float or UnityEngine.Rendering.ShaderPropertyType.Range => material.GetFloat(name).ToString("G6"),
          UnityEngine.Rendering.ShaderPropertyType.Int => material.GetInteger(name).ToString(),
          UnityEngine.Rendering.ShaderPropertyType.Texture => material.GetTexture(name) is Texture t ? $"{t.name}{material.GetTextureScale(name):F2}{material.GetTextureOffset(name):F2}" : "null",
          _ => "?"
        };
        parts.Add($"{name}={value}");
      }
      return string.Join("; ", parts);
    }

    // The deepest open water column of the given contamination whose 5x5 neighbourhood holds the
    // same kind of water at the same surface level.
    private Vector3Int? FindWater(Func<float, bool> contamination, string what) {
      var size = _mapIndex.TerrainSize;
      Vector3Int? best = null;
      float bestDepth = 0.4f;
      int found = 0;
      for (int y = 2; y < size.y - 2; y++) {
        for (int x = 2; x < size.x - 2; x++) {
          if (!Water(x, y, contamination, out var cell, out float depth, out float level)) continue;
          found++;
          if (depth <= bestDepth) continue;
          bool uniform = true;
          for (int dy = -2; dy <= 2 && uniform; dy++)
            for (int dx = -2; dx <= 2 && uniform; dx++)
              uniform = Water(x + dx, y + dy, contamination, out _, out _, out float other) && Mathf.Abs(other - level) < 0.3f;
          if (!uniform) continue;
          best = cell; bestDepth = depth;
        }
      }
      Debug.Log($"{Tag} {what} water: {found} columns; chosen {(best == null ? "none" : $"{best.Value} depth {bestDepth:F2}")}");
      return best;
    }

    private bool Water(int x, int y, Func<float, bool> contamination, out Vector3Int cell, out float depth, out float level) {
      int i = _mapIndex.CellToIndex(new Vector2Int(x, y));
      int count = _waterMap.ColumnCount(i);
      cell = default; depth = 0f; level = 0f;
      if (count == 0) return false;
      int top = (count - 1) * _mapIndex.VerticalStride + i;
      depth = _waterMap.WaterDepth(top);
      if (depth < 0.2f) return false;
      cell = new Vector3Int(x, y, _waterMap.ColumnFloor(top));
      level = cell.z + depth;
      return contamination(_waterMap.ColumnContamination(cell)) && _radiation.GetRadiation(cell) == 0f;
    }

    // Radioactive water into the 3x3 around the spot and soil radiation on the dry cells around it.
    private void Irradiate(Vector3Int spot) {
      for (int dy = -1; dy <= 1; dy++)
        for (int dx = -1; dx <= 1; dx++)
          _radiation.AddRadioactiveWater(new Vector3Int(spot.x + dx, spot.y + dy, spot.z), 1.5f);
      int soil = 0;
      for (int dy = -8; dy <= 8; dy++) {
        for (int dx = -8; dx <= 8; dx++) {
          var xy = new Vector2Int(spot.x + dx, spot.y + dy);
          if (xy.x < 0 || xy.y < 0 || xy.x >= _mapIndex.TerrainSize.x || xy.y >= _mapIndex.TerrainSize.y) continue;
          int i = _mapIndex.CellToIndex(xy);
          int count = _waterMap.ColumnCount(i);
          if (count == 0) continue;
          int top = (count - 1) * _mapIndex.VerticalStride + i;
          if (_waterMap.WaterDepth(top) > 0f) continue;
          _radiation.AddSoilRadiation(new Vector3Int(xy.x, xy.y, _waterMap.ColumnFloor(top)), 0.6f);
          soil++;
        }
      }
      Debug.Log($"{Tag} radioactive water added to 9 cells around {spot}, soil radiation 0.6 on {soil} dry cells");
    }

    // Native CameraService distance: ZoomBase ^ ZoomLevel * BaseDistance.
    private float ZoomFor(float distance) {
      var spec = typeof(CameraService).GetField("_cameraServiceSpec", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(_camera);
      float zoomBase = (float)spec.GetType().GetProperty("ZoomBase").GetValue(spec);
      float baseDistance = (float)spec.GetType().GetProperty("BaseDistance").GetValue(spec);
      return Mathf.Log(distance / baseDistance) / Mathf.Log(zoomBase);
    }
  }
}
#endif
