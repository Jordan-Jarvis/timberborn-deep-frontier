#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockObjectTools;
using Timberborn.BlockSystem;
using Timberborn.CameraSystem;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.EntitySystem;
using Timberborn.NaturalResources;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TerrainSystem;
using Timberborn.UILayoutSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.MapSetup {
  // Explicit test launch only, on a new game (-deepFrontierLoadAcceptance -deepFrontierNewGame
  // "builtin:<map>" -deepFrontierSiteProbe "<checks>" -deepFrontierSiteProbeLabel <label>;
  // tools/start_builtin_site_probe.ps1; "user:<map>" works too). After the built-in map setup has placed its objects, each check
  // "Template@x,y,z,Orientation,mode" removes the trees and bushes in its footprint (as the player cuts
  // them; MapLoopAcceptance does the same), then takes a native preview (PreviewFactory, as the build tool) at that
  // placement and records the native block rules and every IBlockObjectValidator:
  //   place  the preview must be valid; the building is then created finished there.
  //   fill   the preview must be refused; one finished Concrete Block is put under every foundation block
  //          with neither terrain nor an object below it, and the preview must then be valid.
  // Then the camera (UI hidden) captures every check site and every "-deepFrontierSiteProbeShots"
  // target "label@x,y,z" into outputs/site-probe/<label>/. Nothing is saved.
  [Context("Game")]
  public sealed class BuiltinSiteProbeConfigurator : Configurator {
    protected override void Configure() {
      if (!Environment.GetCommandLineArgs().Contains(BuiltinSiteProbe.Flag)) return;
      if (MemoryLoadProbe.NewGameMap() == null) throw new InvalidOperationException(BuiltinSiteProbe.Flag + " requires -deepFrontierLoadAcceptance with -deepFrontierNewGame");
      Bind<BuiltinSiteProbe>().AsSingleton();
    }
  }

  internal sealed class BuiltinSiteProbe : IUpdatableSingleton {
    internal const string Flag = "-deepFrontierSiteProbe";
    private const string ShotsFlag = "-deepFrontierSiteProbeShots", LabelFlag = "-deepFrontierSiteProbeLabel";
    private const string Tag = "[DeepFrontier SiteProbe]";
    private const string Block = "ConcreteBlock.IronTeeth";
    private const int StartFrame = 300, SettleFrames = 90;
    private readonly TemplateService _templates;
    private readonly PreviewFactory _previews;
    private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _validation;
    private readonly BlockObjectFactory _factory;
    private readonly EntityService _entityService;
    private readonly IBlockService _blocks;
    private readonly ITerrainService _terrain;
    private readonly CameraService _camera;
    private readonly UIVisibilityManager _ui;
    private readonly Queue<(string name, Vector3 target)> _shots = new();
    private int _frame, _next, _fails;
    private (string name, Vector3 target)? _current;
    private string _folder;

    public BuiltinSiteProbe(TemplateService templates, PreviewFactory previews, BlockValidator validator, BlockObjectValidationService validation,
        BlockObjectFactory factory, EntityService entityService, IBlockService blocks, ITerrainService terrain, CameraService camera, UIVisibilityManager ui) {
      _templates = templates; _previews = previews; _validator = validator; _validation = validation; _factory = factory; _entityService = entityService;
      _blocks = blocks; _terrain = terrain; _camera = camera; _ui = ui;
    }

    private static string Argument(string flag) {
      var args = Environment.GetCommandLineArgs();
      int i = Array.IndexOf(args, flag);
      if (i < 0) return null;
      if (i + 1 >= args.Length) throw new InvalidOperationException(flag + " needs a value");
      return args[i + 1].Trim('"');
    }

    // Natural resources (trees, bushes) standing on the terrain of the footprint's columns.
    private int ClearNature(IEnumerable<Vector3Int> cells) {
      int removed = 0;
      foreach (var column in cells.Select(c => new Vector2Int(c.x, c.y)).Distinct().ToList()) {
        int h = _terrain.GetTerrainHeight(new Vector3Int(column.x, column.y, 0));
        foreach (var b in _blocks.GetObjectsAt(new Vector3Int(column.x, column.y, h)).ToList()) {
          var e = b.GetComponent<EntityComponent>();
          if (e && e.HasComponent<NaturalResource>()) { _entityService.Delete(e); removed++; }
        }
      }
      return removed;
    }

    private (bool valid, string detail, List<Vector3Int> foundations) Preview(string template, Placement placement) {
      var preview = _previews.Create(_templates.GetAll<TemplateSpec>().Single(x => x.TemplateName == template).Blueprint.GetSpec<PlaceableBlockObjectSpec>());
      try {
        var block = preview.BlockObject;
        block.Reposition(placement);
        bool blocks = _validator.BlocksValid(block.PositionedBlocks);
        bool validators = _validation.AreValid(new BaseComponent[] { block }, out var message);
        return (blocks && validators, "native blocks " + (blocks ? "valid" : "invalid") + ", validators " + (validators ? "valid" : "rejected: " + message),
          block.PositionedBlocks.GetFoundationCoordinates().ToList());
      } finally {
        UnityEngine.Object.Destroy(preview.GameObject);
      }
    }

    private void Record(string subject, string check, bool ok, string detail) {
      if (!ok) _fails++;
      Debug.Log($"{Tag} {(ok ? "PASS" : "FAIL")} {subject} {check}: {detail}");
    }

    private BlockObject CreateFinished(string template, Placement placement) =>
      _factory.CreateFinished(new EntitySetup.Builder(_templates.GetAll<TemplateSpec>().Single(x => x.TemplateName == template).Blueprint)
        .AddInitComponent(new FinishedConstructionSiteInit()), placement);

    private static Vector3Int Cell(string text) {
      var p = text.Split(',').Select(s => int.Parse(s.Trim())).ToArray();
      return new Vector3Int(p[0], p[1], p[2]);
    }

    private void RunChecks() {
      _folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "TimberbornModding", "outputs", "site-probe",
        Argument(LabelFlag) ?? throw new InvalidOperationException(LabelFlag + " is required"));
      Directory.CreateDirectory(_folder);
      // "none": screenshots only (an empty command-line value is dropped by the launcher's shell).
      var checks = Argument(Flag) ?? throw new InvalidOperationException(Flag + " needs a value");
      foreach (var check in checks == "none" ? new string[0] : checks.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries)) {
        var at = check.Split('@');
        var template = at[0].Trim();
        var parts = at[1].Split(',').Select(s => s.Trim()).ToArray();
        if (parts.Length != 5) throw new InvalidOperationException(Tag + " check must be Template@x,y,z,Orientation,mode: " + check);
        var placement = new Placement(new Vector3Int(int.Parse(parts[0]), int.Parse(parts[1]), int.Parse(parts[2])),
          (Orientation)Enum.Parse(typeof(Orientation), parts[3]), new FlipMode(false));
        string mode = parts[4], subject = template + " at " + placement.Coordinates + " " + placement.Orientation;
        int cleared = ClearNature(Preview(template, placement).foundations);
        var before = Preview(template, placement);
        Debug.Log($"{Tag} {subject}: {cleared} trees and bushes removed from the footprint");
        if (mode == "place") {
          Record(subject, "native preview accepts the site", before.valid, before.detail);
          if (before.valid) {
            var b = CreateFinished(template, placement);
            Record(subject, "placed finished", b && _validation.IsValid(b), "finished at " + b.Coordinates);
          }
        } else if (mode == "fill") {
          Record(subject, "native preview refuses the site without support", !before.valid, before.detail);
          var low = before.foundations.Select(c => c + Vector3Int.back)
            .Where(c => !_terrain.Underground(c) && !_blocks.GetObjectsAt(c).Any()).Distinct().ToList();
          foreach (var c in low) CreateFinished(Block, new Placement(c, Orientation.Cw0, new FlipMode(false)));
          var after = Preview(template, placement);
          Record(subject, "native preview accepts the site on " + low.Count + " " + Block, after.valid && low.Count > 0,
            after.detail + "; blocks at " + string.Join(" ", low));
        } else throw new InvalidOperationException(Tag + " unknown mode " + mode);
        var f = before.foundations;
        _shots.Enqueue((template.Split('.')[0], new Vector3((float)f.Average(c => c.x) + .5f, (float)f.Average(c => c.z), (float)f.Average(c => c.y) + .5f)));
      }
      foreach (var shot in (Argument(ShotsFlag) ?? "").Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries)) {
        var at = shot.Split('@');
        var c = Cell(at[1]);
        _shots.Enqueue((at[0].Trim(), new Vector3(c.x + .5f, c.z, c.y + .5f)));
      }
      if (_ui.GUIVisible) typeof(UIVisibilityManager).GetMethod("ToggleGUIVisibility", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(_ui, null);
    }

    public void UpdateSingleton() {
      if (++_frame < StartFrame || _frame < _next) return;
      if (_frame == StartFrame) { RunChecks(); _next = _frame + 10; return; }
      if (_current is { } shot) {
        ScreenCapture.CaptureScreenshot(Path.Combine(_folder, shot.name + ".png"));
        Debug.Log($"{Tag} captured {shot.name} at {shot.target}");
        _current = null; _next = _frame + 10;
        return;
      }
      if (_shots.Count == 0) {
        if (_next != int.MaxValue) Debug.Log($"{Tag} COMPLETE {_fails} failed checks; screenshots in {_folder}");
        _next = int.MaxValue;
        return;
      }
      var aim = _shots.Dequeue();
      _camera.MoveTargetTo(aim.target);
      _camera.VerticalAngle = 40f; _camera.HorizontalAngle = 35f;
      _camera.ZoomLevel = ZoomFor(34f);
      _current = aim; _next = _frame + SettleFrames;
    }

    // Native CameraService distance: ZoomBase ^ ZoomLevel * BaseDistance (as ShowcaseCapture).
    private float ZoomFor(float distance) {
      var spec = typeof(CameraService).GetField("_cameraServiceSpec", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(_camera);
      float zoomBase = (float)spec.GetType().GetProperty("ZoomBase").GetValue(spec);
      float baseDistance = (float)spec.GetType().GetProperty("BaseDistance").GetValue(spec);
      return Mathf.Log(distance / baseDistance) / Mathf.Log(zoomBase);
    }
  }
}
#endif
