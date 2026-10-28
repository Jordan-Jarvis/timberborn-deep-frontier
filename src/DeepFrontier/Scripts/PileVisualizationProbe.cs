#if !UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using Bindito.Core;
using Timberborn.BlockSystem;
using Timberborn.CameraSystem;
using Timberborn.Coordinates;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.SingletonSystem;
using Timberborn.Stockpiles;
using Timberborn.TemplateSystem;
using Timberborn.TerrainSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Explicit disposable test only: -deepFrontierLoadAcceptance -deepFrontierNewGame "user:<map>"
  // -deepFrontierPileProbe (tools/start_memory_load.ps1 -PileProbe). After the new game loads it
  // places one finished SmallIndustrialPile.IronTeeth per Deep Frontier pile good (DeepOre,
  // DeepAlloy) beside the district centre, fills each, and checks the native pile visualization
  // shows a non-empty mesh built from the good's own GoodVisualization (tools/map_objects.json
  // goods). Logs "[DeepFrontier PileProbe] PASS|FAIL ..." and writes
  // outputs/pile-probe-<good>.png. Normal play binds nothing.
  [Context("Game")]
  public sealed class PileVisualizationProbeConfigurator : Configurator {
    protected override void Configure() {
      if (!Environment.GetCommandLineArgs().Contains(PileVisualizationProbe.Flag)) return;
      if (MemoryLoadProbe.NewGameMap() == null)
        throw new InvalidOperationException(PileVisualizationProbe.Flag + " requires -deepFrontierLoadAcceptance with -deepFrontierNewGame");
      Bind<PileVisualizationProbe>().AsSingleton();
    }
  }

  internal sealed class PileVisualizationProbe : IUpdatableSingleton {
    internal const string Flag = "-deepFrontierPileProbe";
    private const string Tag = "[DeepFrontier PileProbe]";
    private const string Pile = "SmallIndustrialPile.IronTeeth";
    private static readonly string[] Goods = { "DeepOre", "DeepAlloy" };
    private static readonly string Outputs = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "TimberbornModding", "outputs");
    private readonly EntityRegistry _entities;
    private readonly TemplateService _templates;
    private readonly BlockObjectFactory _factory;
    private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _validation;
    private readonly ITerrainService _terrain;
    private readonly CameraService _camera;
    private int _frame, _step = -1, _wait;
    private BlockObject[] _piles;

    public PileVisualizationProbe(EntityRegistry entities, TemplateService templates, BlockObjectFactory factory, BlockValidator validator,
        BlockObjectValidationService validation, ITerrainService terrain, CameraService camera) {
      _entities = entities; _templates = templates; _factory = factory; _validator = validator; _validation = validation; _terrain = terrain; _camera = camera;
    }

    public void UpdateSingleton() {
      if (++_frame < 120 || _step >= Goods.Length) return;
      if (_step < 0) { Place(); _step = 0; _wait = 0; return; }
      // Look at one pile, let the visualizer update and the frame render, then check and capture.
      var pile = _piles[_step];
      if (_wait == 0) {
        var c = pile.Coordinates;
        _camera.MoveTargetTo(new Vector3(c.x + 1f, c.z, c.y + 1f));
        _camera.SetZoomLevel(8, 0);
      }
      if (++_wait < 30) return;
      if (_wait == 30) { Check(Goods[_step], pile); ScreenCapture.CaptureScreenshot(Path.Combine(Outputs, $"pile-probe-{Goods[_step]}.png")); return; }
      if (_wait < 45) return;
      _step++; _wait = 0;
      if (_step == Goods.Length) Debug.Log($"{Tag} COMPLETE");
    }

    private void Place() {
      var template = _templates.GetAll<TemplateSpec>().Single(t => t.TemplateName == Pile);
      var spec = template.Blueprint.GetSpec<BlockObjectSpec>();
      var centre = _entities.Entities.Select(e => e.GetComponent<DistrictCenter>()).Single(d => d).GetComponent<BlockObject>().Coordinates;
      _piles = new BlockObject[Goods.Length];
      int placed = 0;
      for (int r = 4; r < 30 && placed < Goods.Length; r++) {
        for (int dx = -r; dx <= r && placed < Goods.Length; dx++) {
          foreach (int dy in new[] { -r, r }) {
            if (placed == Goods.Length) break;
            int x = centre.x + dx, y = centre.y + dy;
            var at = new Placement(new Vector3Int(x, y, _terrain.GetTerrainHeight(new Vector3Int(x, y, 0))), Orientation.Cw0, new FlipMode(false));
            if (!_validator.BlocksValid(spec, at)) continue;
            var pile = _factory.CreateFinished(new EntitySetup.Builder(spec.Blueprint).AddInitComponent(new Timberborn.ConstructionSites.FinishedConstructionSiteInit()), at);
            if (!_validation.IsValid(pile)) throw new InvalidOperationException($"{Tag} native object requirements rejected {Pile} at {at.Coordinates}");
            string good = Goods[placed];
            pile.GetComponent<SingleGoodAllower>().Allow(good);
            var inventory = pile.GetComponent<Stockpile>().Inventory;
            inventory.GiveExisting(new GoodAmount(good, Math.Min(30, inventory.UnreservedCapacity(good))));
            _piles[placed++] = pile;
            Debug.Log($"{Tag} placed {Pile} with {inventory.AmountInStock(good)} {good} at {at.Coordinates}");
          }
        }
      }
      if (placed != Goods.Length) throw new InvalidOperationException($"{Tag} no free spot for {Goods.Length} piles near {centre}");
    }

    private static void Check(string good, BlockObject pile) {
      var visual = pile.GameObject.GetComponentsInChildren<MeshFilter>(true).Where(f => f.gameObject.name == "GoodVisualization").ToArray();
      var mesh = visual.Length == 1 ? visual[0].sharedMesh : null;
      bool ok = mesh != null && mesh.vertexCount > 0 && visual[0].gameObject.activeInHierarchy;
      Debug.Log($"{Tag} {(ok ? "PASS" : "FAIL")} {good}: GoodVisualization objects {visual.Length}, mesh '{mesh?.name}' with {mesh?.vertexCount ?? 0} vertices, " +
        $"{mesh?.triangles.Length / 3 ?? 0} triangles; screenshot outputs/pile-probe-{good}.png");
    }
  }
}
#endif
