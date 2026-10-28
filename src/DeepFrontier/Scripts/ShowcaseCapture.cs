#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Bindito.Core;
using Timberborn.BlockSystem;
using Timberborn.CameraSystem;
using Timberborn.EntitySystem;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.UILayoutSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Workshop screenshots from a loaded save copy: -deepFrontierLoadAcceptance -deepFrontierLoadSave "<copy in
  // Memory Test>" -deepFrontierShowcase (tools/start_memory_load.ps1 -Showcase). Hides the game UI (native
  // UIVisibilityManager toggle), aims the native camera at the first of each listed Deep Frontier building in the
  // save from two angles, and captures outputs/showcase/<template>-<angle>.png. Nothing is placed or saved.
  [Context("Game")]
  public sealed class ShowcaseCaptureConfigurator : Configurator {
    protected override void Configure() {
      if (!Environment.GetCommandLineArgs().Contains(ShowcaseCapture.Flag)) return;
      if (MemoryLoadProbe.SavePath() == null) throw new InvalidOperationException(ShowcaseCapture.Flag + " requires -deepFrontierLoadAcceptance with -deepFrontierLoadSave");
      Bind<ShowcaseCapture>().AsSingleton();
    }
  }

  internal sealed class ShowcaseCapture : IUpdatableSingleton {
    internal const string Flag = "-deepFrontierShowcase";
    private const string Tag = "[DeepFrontier Showcase]";
    private const int SettleFrames = 90;
    private static readonly string[] Templates = {
      "Restaurant", "GroceryStore", "Hospital", "OilPowerPlant", "CoalPowerPlant", "NuclearReactor", "DeepProcessor", "SteelMill",
      "FisheryWorks", "FishHatchery", "Greenhouse", "Bathhouse", "TownPlaza", "CementKiln", "ConcreteMixer", "ChemicalWorks",
      "LaunchPad", "MissionControl", "DeepDrill", "DeepMine", "ReinforcedHydroTurbine", "PublicHealthLab" };
    private static readonly float[] Angles = { 35f, 215f };
    private readonly EntityRegistry _entities;
    private readonly CameraService _camera;
    private readonly UIVisibilityManager _ui;
    private readonly Queue<(string name, Vector3 target, float distance, float angle)> _shots = new();
    private string _folder;
    private int _frame, _next;
    private (string name, Vector3 target, float distance, float angle)? _current;

    public ShowcaseCapture(EntityRegistry entities, CameraService camera, UIVisibilityManager ui) { _entities = entities; _camera = camera; _ui = ui; }

    public void UpdateSingleton() {
      if (++_frame == 300) Plan();
      if (_frame < 300 || _frame < _next) return;
      if (_current is { } shot) {
        ScreenCapture.CaptureScreenshot(Path.Combine(_folder, $"{shot.name}-{shot.angle:0}.png"));
        Debug.Log($"{Tag} captured {shot.name} at {shot.angle:0} degrees");
        _current = null; _next = _frame + 10;
        return;
      }
      if (_shots.Count == 0) { if (_next != int.MaxValue) Debug.Log($"{Tag} COMPLETE"); _next = int.MaxValue; return; }
      var aim = _shots.Dequeue();
      _camera.MoveTargetTo(aim.target);
      _camera.VerticalAngle = 32f; _camera.HorizontalAngle = aim.angle;
      _camera.ZoomLevel = ZoomFor(aim.distance);
      _current = aim; _next = _frame + SettleFrames;
    }

    private void Plan() {
      _folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "TimberbornModding", "outputs", "showcase");
      Directory.CreateDirectory(_folder);
      if (_ui.GUIVisible) typeof(UIVisibilityManager).GetMethod("ToggleGUIVisibility", BindingFlags.Instance | BindingFlags.NonPublic)
        .Invoke(_ui, null);
      var buildings = _entities.Entities.Select(e => (e.GetComponent<TemplateSpec>()?.TemplateName, block: e.GetComponent<BlockObject>()))
        .Where(t => t.TemplateName != null && t.block && t.block.IsFinished).ToList();
      foreach (var name in Templates) {
        var found = buildings.FirstOrDefault(t => t.TemplateName == name + ".IronTeeth").block;
        if (!found) continue;
        var cells = found.PositionedBlocks.GetOccupiedCoordinates().ToList();
        var min = new Vector3(cells.Min(c => c.x), cells.Min(c => c.z), cells.Min(c => c.y));
        var max = new Vector3(cells.Max(c => c.x) + 1, cells.Max(c => c.z) + 1, cells.Max(c => c.y) + 1);
        var centre = (min + max) / 2f; centre.y = min.y + (max.y - min.y) * 0.35f;
        float size = Mathf.Max(max.x - min.x, max.y - min.y, max.z - min.z);
        foreach (var angle in Angles) _shots.Enqueue((name, centre, size * 2.2f + 6f, angle));
      }
      Debug.Log($"{Tag} {_shots.Count} shots planned into {_folder}");
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
