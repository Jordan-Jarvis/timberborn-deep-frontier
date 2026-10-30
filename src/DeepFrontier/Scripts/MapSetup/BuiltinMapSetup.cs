#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockObjectTools;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Coordinates;
using Timberborn.CoreUI;
using Timberborn.EntitySystem;
using Timberborn.GameSceneLoading;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.Localization;
using Timberborn.MapStateSystem;
using Timberborn.Persistence;
using Timberborn.SceneLoading;
using Timberborn.SingletonSystem;
using Timberborn.Stockpiles;
using Timberborn.TemplateSystem;
using Timberborn.UILayoutSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.MapSetup {
  [Context("Game")]
  public sealed class MapSetupConfigurator : Configurator {
    protected override void Configure() {
      Bind<BuiltinMapSetup>().AsSingleton();
    }
  }

  // Places the Deep Frontier objects of the built-in map a new game starts on (docs/maps.md
  // "Built-in maps: new-game setup"). It runs exactly once per settlement: the outcome is saved in
  // the DeepFrontierMapSetup singleton, and a world that has it (or that was loaded from a save
  // without it) is never set up again.
  //   - New game: GameSceneParameters.NewGame, the same test native MapNameService.Load and
  //     GameLoader.LoadNew use; the map is NewGameConfiguration.MapFileReference (Resource = built-in,
  //     Name = the asset name MapNameService saves).
  //   - Placement, on the first frame (GameStarter spawns the starting building on its first frame;
  //     the placements never overlap the starting location, which the static validation checks): the
  //     map editor's own path. A native preview (PreviewFactory, as the BlockObjectTool's
  //     PreviewPlacer) must be valid at the placement: BlockObject.IsValid = BlockValidator.BlocksValid
  //     and every IBlockObjectValidator. Then BlockObjectPlacerService.GetMatchingPlacer(...).Place
  //     with a new EntitySetup.Builder, as BlockObjectTool.Place: BuildingPlacer for the Deep Ore
  //     Source (BuildingSpec.PlaceFinished, so finished), DefaultBlockObjectPlacer for the others.
  //     A stockpile then gets its fixed good and amount as the map editor's
  //     FixedStockpileInventorySetter does (SingleGoodAllower.Allow, FixedStockpile.SetFixedGood,
  //     Inventory.GiveExisting).
  //   - A placement that fails is not moved or skipped silently: it is logged as an error and
  //     reported in a dialog.
  //   - Small maps (BuiltinMapSpec.Small: below the area threshold, or no Deep Mine site) and maps
  //     with unmet loop items get a one-time dialog.
  internal sealed class BuiltinMapSetup : ILoadableSingleton, ISaveableSingleton, IUpdatableSingleton {
    private const string Tag = "[DeepFrontier MapSetup]";
    private static readonly SingletonKey Key = new("DeepFrontierMapSetup");
    private static readonly PropertyKey<string> MapKey = new("Map");
    private static readonly PropertyKey<string> OutcomeKey = new("Outcome");
    private static readonly PropertyKey<int> PlacedKey = new("Placed");
    private static readonly PropertyKey<int> FailedKey = new("Failed");

    // Saved outcomes.
    private const string Applied = "Applied";               // every placement placed
    private const string AppliedWithErrors = "AppliedWithErrors";
    private const string UserMap = "UserMap";               // new game on a map file: nothing to do
    private const string DevMap = "DevMap";
    private const string NoSetup = "NoSetup";               // built-in map without an entry (an error)
    private const string SavedBeforeSetup = "SavedBeforeSetup"; // a save from before this system: never touched

    private readonly ISingletonLoader _singletonLoader;
    private readonly ISceneLoader _sceneLoader;
    private readonly ISpecService _specs;
    private readonly MapSize _mapSize;
    private readonly TemplateNameMapper _templates;
    private readonly PreviewFactory _previews;
    private readonly BlockObjectPlacerService _placers;
    private readonly BlockValidator _blockValidator;
    private readonly BlockObjectValidationService _validation;
    private readonly IBlockService _blocks;
    private readonly DialogBoxShower _dialogs;
    private readonly ILoc _loc;
    private readonly EventBus _eventBus;

    private string _map = "";
    private string _outcome;
    private int _placed, _failed;
    private BuiltinMapSpec _entry;
    private bool _placePending;
    private readonly List<string> _dialogTexts = new();

    public BuiltinMapSetup(ISingletonLoader singletonLoader, ISceneLoader sceneLoader, ISpecService specs, MapSize mapSize,
        TemplateNameMapper templates, PreviewFactory previews, BlockObjectPlacerService placers, BlockValidator blockValidator,
        BlockObjectValidationService validation, IBlockService blocks, DialogBoxShower dialogs, ILoc loc, EventBus eventBus) {
      _singletonLoader = singletonLoader; _sceneLoader = sceneLoader; _specs = specs; _mapSize = mapSize;
      _templates = templates; _previews = previews; _placers = placers; _blockValidator = blockValidator;
      _validation = validation; _blocks = blocks; _dialogs = dialogs; _loc = loc; _eventBus = eventBus;
    }

    public void Load() {
      if (_singletonLoader.TryGetSingleton(Key, out var saved)) {
        _map = saved.Get(MapKey);
        _outcome = saved.Get(OutcomeKey);
        _placed = saved.Get(PlacedKey);
        _failed = saved.Get(FailedKey);
        return;
      }
      var parameters = _sceneLoader.GetSceneParameters<GameSceneParameters>();
      if (!parameters.NewGame) { _outcome = SavedBeforeSetup; return; }
      var map = parameters.NewGameConfiguration.MapFileReference;
      _map = map.Name;
      if (!map.Resource) { _outcome = UserMap; return; }
      _eventBus.Register(this);
      var setup = _specs.GetSingleSpec<BuiltinMapSetupSpec>();
      _entry = setup.Find(map.Name);
      if (_entry == null) {
        if (setup.DevMaps.Contains(map.Name)) {
          _outcome = DevMap;
          Debug.Log(Tag + " " + map.Name + " is a developer test map: no Deep Frontier setup");
          _dialogTexts.Add(_loc.T(MapSetupLoc.DevMap, map.Name));
        } else {
          _outcome = NoSetup;
          Debug.LogError(Tag + " built-in map " + map.Name + " has no entry in Configurations/DeepFrontierMapSetup; nothing was placed");
          _dialogTexts.Add(_loc.T(MapSetupLoc.NoSetup, map.Name));
        }
        return;
      }
      var vanilla = _specs.GetSingleSpec<MapSizeSpec>();
      int terrainLayers = vanilla.MaxGameTerrainHeight + 1;
      if (_mapSize.TotalSize.z != _entry.TotalHeight || _mapSize.TerrainSize.z != terrainLayers) {
        Debug.LogError(Tag + " " + map.Name + ": expected terrain " + terrainLayers + " / total " + _entry.TotalHeight
          + " layers, the map has " + _mapSize.TerrainSize.z + " / " + _mapSize.TotalSize.z + " (Map Transformer applies MapHeight)");
        _dialogTexts.Add(_loc.T(MapSetupLoc.HeightFailed, _entry.TotalHeight, DisplayName(), _mapSize.TotalSize.z));
      }
      var size = _mapSize.TerrainSize2D;
      if (size.x != _entry.Width || size.y != _entry.Height)
        throw new InvalidOperationException(Tag + " " + map.Name + " is " + size.x + " x " + size.y + ", its setup entry says " + _entry.Width + " x " + _entry.Height);
      _placePending = true;
    }

    public void UpdateSingleton() {
      if (!_placePending) return;
      _placePending = false;
      PlaceAll();
    }

    public void Save(ISingletonSaver singletonSaver) {
      var saver = singletonSaver.GetSingleton(Key);
      saver.Set(MapKey, _map);
      saver.Set(OutcomeKey, _outcome ?? throw new InvalidOperationException(Tag + " saved before the setup ran"));
      saver.Set(PlacedKey, _placed);
      saver.Set(FailedKey, _failed);
    }

    [OnEvent]
    public void OnShowPrimaryUI(ShowPrimaryUIEvent showPrimaryUIEvent) {
      _eventBus.Unregister(this);
      if (_dialogTexts.Count > 0) _dialogs.Create().SetMessage(string.Join("\n\n", _dialogTexts)).Show();
      _dialogTexts.Clear();
    }

    private void PlaceAll() {
      Debug.Log(Tag + " new game on built-in " + _entry.MapName + " (variant " + _entry.VariantId + "): placing "
        + _entry.Placements.Length + " objects, total height " + _mapSize.TotalSize.z);
      foreach (var placement in _entry.Placements) {
        var problem = Place(placement);
        if (problem == null) {
          _placed++;
          Debug.Log(Tag + " placed " + Describe(placement));
        } else {
          _failed++;
          Debug.LogError(Tag + " FAILED " + Describe(placement) + ": " + problem);
        }
      }
      _outcome = _failed == 0 ? Applied : AppliedWithErrors;
      Debug.Log(Tag + " " + _entry.MapName + ": " + _placed + " placed, " + _failed + " failed");
      if (_failed > 0) _dialogTexts.Insert(0, _loc.T(MapSetupLoc.SetupFailedTitle, DisplayName()) + "\n" + _loc.T(MapSetupLoc.SetupFailed, _failed, DisplayName()));
      if (_entry.Small) _dialogTexts.Add(SmallMapWarning());
      else if (_entry.UnmetLocKeys.Length > 0) _dialogTexts.Add(UnmetNotice());
    }

    // null when placed; otherwise why not.
    private string Place(MapPlacementSpec p) {
      if (!_templates.TryGetTemplate(p.Template, out var template)) return "template " + p.Template + " is not loaded";
      var blueprint = template.Blueprint;
      var placeable = blueprint.GetSpec<PlaceableBlockObjectSpec>();
      var blockSpec = blueprint.GetSpec<BlockObjectSpec>();
      var orientation = (Orientation)Enum.Parse(typeof(Orientation), p.Orientation);
      var coordinates = new Vector3Int(p.X, p.Y, p.Z);
      var placement = new Placement(coordinates, orientation, FlipMode.Unflipped);
      var preview = _previews.Create(placeable);
      try {
        var block = preview.BlockObject;
        block.Reposition(placement);
        if (!block.IsValid()) {
          bool blocksValid = _blockValidator.BlocksValid(block.PositionedBlocks);
          _validation.AreValid(new BaseComponent[] { block }, out var message);
          return "native preview rejected: blocks " + (blocksValid ? "valid" : "invalid") + ", validators " + (string.IsNullOrEmpty(message) ? "valid" : message);
        }
      } finally {
        UnityEngine.Object.Destroy(preview.GameObject);
      }
      _placers.GetMatchingPlacer(blockSpec).Place(new EntitySetup.Builder(blueprint), placement);
      var placed = _blocks.GetObjectsAt(coordinates)
        .Where(b => b.Coordinates == coordinates && b.GetComponent<TemplateSpec>()?.TemplateName == p.Template).ToList();
      if (placed.Count != 1) return placed.Count + " " + p.Template + " objects at " + coordinates + " after placing";
      var stockpile = placed[0].GetComponent<Stockpile>();
      if (stockpile == null) return p.Good == "" ? null : "placement names good " + p.Good + " but " + p.Template + " has no stockpile";
      if (p.Good == "" || p.Amount <= 0) return p.Template + " is a stockpile but the placement names no good and amount";
      // FixedStockpileInventorySetter.ResetInventoryGood + SetAmount (Timberborn.MapEditorStockpilesUI).
      placed[0].GetComponent<SingleGoodAllower>().Allow(p.Good);
      placed[0].GetComponent<FixedStockpile>().SetFixedGood(p.Good);
      stockpile.Inventory.GiveExisting(new GoodAmount(p.Good, p.Amount));
      int stock = stockpile.Inventory.AmountInStock(p.Good);
      return stock == p.Amount ? null : "stockpile holds " + stock + " " + p.Good + ", expected " + p.Amount;
    }

    private string SmallMapWarning() {
      var vanilla = _specs.GetSingleSpec<MapSizeSpec>();
      int vanillaTotal = vanilla.MaxGameTerrainHeight + 1 + vanilla.MaxHeightAboveTerrain;
      var setup = _specs.GetSingleSpec<BuiltinMapSetupSpec>();
      var lines = new List<string> { _loc.T(MapSetupLoc.SmallTitle, DisplayName()) };
      if (_entry.SmallArea) {
        lines.Add("- " + _loc.T(MapSetupLoc.SmallIntro, DisplayName(), _entry.Width + " x " + _entry.Height + " = " + (_entry.Width * _entry.Height), setup.SmallMapMaxArea));
        lines.Add("- " + _loc.T(MapSetupLoc.SmallSpace, setup.ReferenceSiteArea));
        lines.Add("- " + _loc.T(MapSetupLoc.SmallHeight, _mapSize.TotalSize.z, vanillaTotal));
      }
      if (_entry.NoDeepMineSite) lines.Add("- " + _loc.T(MapSetupLoc.SmallNoDeepMine));
      if (_entry.UnmetLocKeys.Length > 0) {
        lines.Add(_loc.T(MapSetupLoc.SmallReasonsHeader));
        lines.AddRange(_entry.UnmetLocKeys.Select(k => "- " + _loc.T(k)));
      } else {
        lines.Add(_loc.T(MapSetupLoc.SmallNoUnmet));
      }
      return string.Join("\n", lines);
    }

    private string UnmetNotice() =>
      _loc.T(MapSetupLoc.UnmetTitle, DisplayName()) + "\n" + string.Join("\n", _entry.UnmetLocKeys.Select(k => "- " + _loc.T(k)));

    // The new-game list's name of a built-in map (OfficialMapItemFactory: MapMetadata.<Name>.Name).
    private string DisplayName() => _loc.T("MapMetadata." + _entry.MapName + ".Name");

    private static string Describe(MapPlacementSpec p) =>
      p.Template + " '" + p.Label + "' at (" + p.X + ", " + p.Y + ", " + p.Z + ") " + p.Orientation + (p.Good == "" ? "" : ", " + p.Amount + " " + p.Good);
  }

  internal static class MapSetupLoc {
    private const string Prefix = "DeepFrontier.MapSetup.";
    public const string SmallTitle = Prefix + "SmallTitle";
    public const string SmallIntro = Prefix + "SmallIntro";
    public const string SmallReasonsHeader = Prefix + "SmallReasonsHeader";
    public const string SmallSpace = Prefix + "SmallSpace";
    public const string SmallHeight = Prefix + "SmallHeight";
    public const string SmallNoDeepMine = Prefix + "SmallNoDeepMine";
    public const string SmallNoUnmet = Prefix + "SmallNoUnmet";
    public const string UnmetTitle = Prefix + "UnmetTitle";
    public const string SetupFailedTitle = Prefix + "SetupFailedTitle";
    public const string SetupFailed = Prefix + "SetupFailed";
    public const string HeightFailed = Prefix + "HeightFailed";
    public const string NoSetup = Prefix + "NoSetup";
    public const string DevMap = Prefix + "DevMap";
  }
}
#endif
