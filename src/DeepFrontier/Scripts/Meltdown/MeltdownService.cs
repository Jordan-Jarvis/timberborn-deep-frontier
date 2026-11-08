using System;
using System.Collections.Generic;
using System.Linq;
using DeepFrontier.Scripts.Radiation;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.CameraSystem;
using Timberborn.Characters;
using Timberborn.Common;
using Timberborn.CoreUI;
using Timberborn.DeconstructionSystem;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.Explosions;
using Timberborn.Localization;
using Timberborn.MapStateSystem;
using Timberborn.MortalSystem;
using Timberborn.Navigation;
using Timberborn.NotificationSystem;
using Timberborn.TerrainPhysics;
using Timberborn.TerrainSystem;
using Timberborn.TickSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.Meltdown {
  // Executes reactor meltdowns in its singleton tick, the same place native
  // ExplosionService.DestroyEverythingAffected removes terrain and deletes
  // block objects (entity ticks are not the place to delete the ticking
  // entity). A reactor whose core reached 1 requests it; if the game is saved
  // first, the saved heat of 1 requests it again on the first tick after load.
  // Everything below happens in one tick, and GameSaver finishes the tick
  // before it saves, so a save holds either the standing reactor or the whole
  // meltdown, never part of it.
  //
  // Order:
  // 1. Geometry, read before anything changes: the open fluid cells around the
  //    footprint (fails before any effect if no footprint column is open), the
  //    crater and the blast, gathered as one native explosion outcome:
  //    ExplosionOutcomeGatherer.GetAffectedTerrainAndObjects on the crater
  //    tiles (their terrain, objects in them and on the removed ground, and the
  //    native terrain-physics stack), plus every building within the blast
  //    radius, then ITerrainPhysicsService.GetTerrainAndBlockObjectStack for
  //    everything standing on those buildings or left unsupported.
  // 2. Casualties (as native ExplosionService: characters first, then
  //    terrain and objects).
  // 3. Contamination through IRadiationService, at cells that are open now and
  //    stay open (removing terrain and buildings only opens cells): the
  //    footprint release, the continuous source, the crater flood and the
  //    fallout on soil and water.
  // 4. Destruction in the native ExplosionService order: ITerrainService.
  //    UnsetTerrain, EntityService.Delete for every object (its
  //    EntityDeletedEvent drives the native deconstruction particles and goods
  //    recovery), DeconstructionParticleFactory on the removed terrain. Bodies
  //    then drop to the ground below, as native CharacterExploder does. Sound,
  //    notification and dialog.
  //
  // Buildings are not water obstacles in 1.1.2.8 (only WaterObstacle /
  // FinishableWaterObstacle add them), so the footprint columns are already
  // open fluid cells while the reactor still stands.
  internal sealed class MeltdownService : ITickableSingleton {
    private readonly IRadiationService _radiation;
    private readonly EntityService _entities;
    private readonly CharacterPopulation _population;
    private readonly NotificationBus _notifications;
    private readonly DialogBoxShower _dialogs;
    private readonly ExplosionSoundPlayer _explosionSound;
    private readonly CameraService _camera;
    private readonly MapSize _mapSize;
    private readonly ILoc _loc;
    private readonly ITerrainService _terrainService;
    private readonly IBlockService _blocks;
    private readonly ExplosionOutcomeGatherer _explosionOutcome;
    private readonly ITerrainPhysicsService _terrainPhysics;
    private readonly DeconstructionParticleFactory _particles;
    private readonly List<ReactorCore> _pending = new();
    private readonly HashSet<Vector3Int> _craterTiles = new(), _terrain = new(), _extraTerrain = new();
    private readonly HashSet<BlockObject> _objects = new(), _extraObjects = new();

    public MeltdownService(IRadiationService radiation, EntityService entities, CharacterPopulation population,
        NotificationBus notifications, DialogBoxShower dialogs, ExplosionSoundPlayer explosionSound,
        CameraService camera, MapSize mapSize, ILoc loc, ITerrainService terrainService, IBlockService blocks,
        ExplosionOutcomeGatherer explosionOutcome, ITerrainPhysicsService terrainPhysics, DeconstructionParticleFactory particles) {
      _radiation = radiation; _entities = entities; _population = population; _notifications = notifications;
      _dialogs = dialogs; _explosionSound = explosionSound; _camera = camera; _mapSize = mapSize; _loc = loc;
      _terrainService = terrainService; _blocks = blocks; _explosionOutcome = explosionOutcome;
      _terrainPhysics = terrainPhysics; _particles = particles;
    }

    public void Request(ReactorCore core) {
      if (!_pending.Contains(core)) _pending.Add(core);
    }

    public void Tick() {
      if (_pending.Count == 0) return;
      var batch = _pending.ToArray();
      _pending.Clear();
      foreach (var core in batch)
        // EntityService.Delete removes blocks immediately but defers Unity's
        // GameObject destruction. An earlier blast in this batch can therefore
        // leave a truthy component whose reactor is already gone from the map.
        if (core && !core.GetComponent<EntityComponent>().Deleted) Execute(core);
    }

    private void Execute(ReactorCore core) {
      var spec = core.Spec;
      var reactor = core.GetComponent<BlockObject>();
      var site = BuildingSite.Of(reactor, _mapSize);
      var area = site.OpenCellsWithin(_radiation, spec.MeltdownRadius);
      var footprint = area.Where(c => c.Distance == 0f).Select(c => c.Cell).ToList();
      if (footprint.Count == 0)
        throw new InvalidOperationException($"{core.Name}: meltdown found no open fluid column in the reactor footprint");
      var source = site.NearestToCenter(footprint);

      // Crater and blast, as one native explosion outcome. The bowl is cut
      // below the ground the reactor stood on and never takes the bottom layer
      // (z 0); the gatherer keeps only tiles that are terrain.
      int ground = GroundUnder(site);
      var crater = site.CraterColumns(spec.MeltdownCraterRim, spec.MeltdownCraterDepth);
      _craterTiles.Clear(); _terrain.Clear(); _objects.Clear(); _extraTerrain.Clear(); _extraObjects.Clear();
      foreach (var (column, depth) in crater)
        for (int z = Math.Max(1, ground - depth); z < ground; z++) _craterTiles.Add(new Vector3Int(column.x, column.y, z));
      _explosionOutcome.GetAffectedTerrainAndObjects(_craterTiles.AsReadOnlyHashSet(), _terrain, _objects);
      CollectBlast(site, spec.MeltdownBlastRadius, _objects);
      _terrainPhysics.GetTerrainAndBlockObjectStack(_terrain, _objects, _extraTerrain, _extraObjects);
      _terrain.UnionWith(_extraTerrain);
      _objects.UnionWith(_extraObjects);
      if (!_objects.Contains(reactor))
        throw new InvalidOperationException($"{core.Name}: the reactor is not among the objects its meltdown destroys");

      // Crater flood: each crater column gets MeltdownCraterFloodFactor
      // radioactive water per terrain block its floor drops, so the bowl fills
      // and the rest spills over the rim. Columns closed to the sky are skipped,
      // as everywhere else in the meltdown.
      var flood = new List<(Vector3Int Cell, float Volume)>();
      foreach (var (column, _) in crater) {
        if (!_radiation.TryFindOpenCell(column, ground, out var cell)) continue;
        int drop = FloorDrop(cell);
        if (drop > 0) flood.Add((cell, drop * spec.MeltdownCraterFloodFactor));
      }

      // Casualties: everyone inside, and every mortal character within the
      // kill radius (which covers the crater), dies; beavers within the
      // irradiation radius receive a dose that irradiates them (10 days of
      // hospital care, else fatal). Characters inside destroyed buildings are
      // put out by the native deletion and share the fate of their distance.
      var inside = new HashSet<Character>(core.GetComponent<Enterable>().EnterersInside.Select(e => e.GetComponent<Character>()));
      var dead = new List<Character>();
      int irradiated = 0;
      foreach (var character in _population.Characters.ToList()) {
        if (!character.Alive) continue;
        var cell = NavigationCoordinateSystem.WorldToGridInt(character.Transform.position);
        var mortal = character.GetComponent<Mortal>();
        if (mortal && (inside.Contains(character) || site.Within(cell.x, cell.y, spec.MeltdownKillRadius))) {
          mortal.DieInstantly(_loc.T(MeltdownLoc.DeathMessage, character.FirstName));
          dead.Add(character);
        } else if (site.Within(cell.x, cell.y, spec.MeltdownIrradiationRadius)) {
          var exposure = character.GetComponent<RadiationExposure>();
          if (!exposure) continue;   // bots have no radiation need
          exposure.AddDose(spec.MeltdownIrradiationDose);
          irradiated++;
        }
      }

      // Contamination: the core's radioactive water (spec volumes are
      // radioactive volume, one sludge good = 0.2) spreads over the footprint
      // and keeps pouring from its centre; the crater flood; fallout irradiates
      // soil and adds radioactive water, falling linearly with the circular
      // distance from the footprint value to the edge value at the radius.
      // Ground the crater removes gets no fallout: its new floor lies under the
      // flood, whose radioactive water irradiates it (soil exchange and banks).
      foreach (var cell in footprint) _radiation.AddRadioactiveWater(cell, spec.MeltdownInstantSludge / footprint.Count);
      _radiation.AddContinuousSource(source, spec.MeltdownSourceSludgePerHour, spec.MeltdownSourceHours);
      foreach (var (cell, volume) in flood) _radiation.AddRadioactiveWater(cell, volume);
      foreach (var (cell, distance) in area) {
        float t = Mathf.Min(1f, distance / spec.MeltdownRadius);
        if (FloorDrop(cell) == 0)
          _radiation.AddSoilRadiation(cell, Mathf.Lerp(spec.MeltdownFootprintSoilRadiation, spec.MeltdownEdgeSoilRadiation, t));
        if (_radiation.Sample(cell).Submerged)
          _radiation.AddRadioactiveWater(cell, Mathf.Lerp(spec.MeltdownFootprintWaterRadiation, spec.MeltdownEdgeWaterRadiation, t));
      }

      var position = core.Transform.position;
      int structures = _objects.Count(o => o != reactor && o.HasComponent<BuildingSpec>());
      _explosionSound.PlayGlobal(core.GameObject);
      _notifications.Post(_loc.T(MeltdownLoc.NotificationMeltdown, dead.Count, irradiated, structures), core);
      _terrainService.UnsetTerrain(_terrain);
      foreach (var blockObject in _objects) _entities.Delete(blockObject);
      _particles.AddPausableParticles(_terrain);
      foreach (var character in dead) {
        var at = character.Transform.position;
        int height = _terrainService.GetTerrainHeightBelow(NavigationCoordinateSystem.WorldToGridInt(at));
        character.Transform.position = new Vector3(at.x, height, at.z);
      }
      int days = Mathf.CeilToInt(spec.MeltdownSourceHours / 24f);
      _dialogs.Create()
        .SetMessage(_loc.T(MeltdownLoc.DialogTitle) + "\n\n"
          + string.Format(_loc.T(MeltdownLoc.DialogCasualties), dead.Count, irradiated, spec.MeltdownBlastRadius, structures)
          + "\n\n" + _loc.T(MeltdownLoc.DialogContamination, days, spec.MeltdownRadius))
        .SetConfirmButton(() => _camera.MoveTargetTo(position), _loc.T(MeltdownLoc.DialogShowSite))
        .SetDefaultCancelButton()
        .Show();
    }

    // The ground the reactor stood on: the highest terrain top under its
    // footprint at or below its base (the base itself on the ground; the
    // ground under its supports when it stands on platforms).
    private int GroundUnder(BuildingSite site) {
      int ground = 0;
      for (int x = site.MinX; x <= site.MaxX; x++)
        for (int y = site.MinY; y <= site.MaxY; y++)
          ground = Math.Max(ground, _terrainService.GetTerrainHeightBelow(new Vector3Int(x, y, site.BaseZ)));
      return ground;
    }

    // Every building and structure (BuildingSpec, where native
    // DeconstructionSystemConfigurator decorates Deconstructible: everything
    // placed with the construction tools, finished or under construction) with
    // a block in a column within the blast radius, at any height. Natural
    // resources, ruins and map objects are not buildings; they go only if
    // they stand on removed ground (the native outcome above).
    private void CollectBlast(BuildingSite site, int radius, HashSet<BlockObject> objects) {
      int height = _blocks.Size.z;
      foreach (var (column, _) in site.ColumnsWithin(radius))
        for (int z = 0; z < height; z++)
          foreach (var blockObject in _blocks.GetObjectsAt(new Vector3Int(column.x, column.y, z)))
            if (blockObject.HasComponent<BuildingSpec>()) objects.Add(blockObject);
    }

    // How many terrain blocks the destruction removes straight under the floor
    // of this open cell's column (read before the terrain changes).
    private int FloorDrop(Vector3Int cell) {
      int floor = _terrainService.GetTerrainHeightBelow(cell);
      int drop = 0;
      while (floor - drop > 0 && _terrain.Contains(new Vector3Int(cell.x, cell.y, floor - drop - 1))) drop++;
      return drop;
    }
  }

  // Footprint rectangle of a building and the map columns around it.
  // Distance is circular: the straight-line distance in tiles from a column
  // to the nearest footprint column (0 inside). A column is within R tiles
  // when that distance rounds to R or less (dx² + dy² <= R² + R), so every
  // radius is a rounded outline around the footprint (an exact tile circle
  // around a 1x1 footprint), never a square.
  internal readonly struct BuildingSite {
    public readonly int MinX, MaxX, MinY, MaxY, BaseZ;
    private readonly Vector2Int _mapSize;

    private BuildingSite(int minX, int maxX, int minY, int maxY, int baseZ, Vector2Int mapSize) {
      MinX = minX; MaxX = maxX; MinY = minY; MaxY = maxY; BaseZ = baseZ; _mapSize = mapSize;
    }

    public static BuildingSite Of(BlockObject block, MapSize mapSize) {
      var coordinates = block.PositionedBlocks.GetAllCoordinates().ToList();
      if (coordinates.Count == 0) throw new InvalidOperationException($"{block.Name}: building has no blocks");
      var size = mapSize.TerrainSize;
      return new BuildingSite(coordinates.Min(c => c.x), coordinates.Max(c => c.x), coordinates.Min(c => c.y),
        coordinates.Max(c => c.y), coordinates.Min(c => c.z), new Vector2Int(size.x, size.y));
    }

    private void Gap(int x, int y, out int dx, out int dy) {
      dx = x < MinX ? MinX - x : x > MaxX ? x - MaxX : 0;
      dy = y < MinY ? MinY - y : y > MaxY ? y - MaxY : 0;
    }

    public float Distance(int x, int y) {
      Gap(x, y, out int dx, out int dy);
      return Mathf.Sqrt(dx * dx + dy * dy);
    }

    public bool Within(int x, int y, int radius) {
      Gap(x, y, out int dx, out int dy);
      return dx * dx + dy * dy <= radius * radius + radius;
    }

    // Every map column within `radius` tiles, with its distance.
    public List<(Vector2Int Column, float Distance)> ColumnsWithin(int radius) {
      var columns = new List<(Vector2Int, float)>();
      for (int x = Math.Max(0, MinX - radius); x <= Math.Min(_mapSize.x - 1, MaxX + radius); x++)
        for (int y = Math.Max(0, MinY - radius); y <= Math.Min(_mapSize.y - 1, MaxY + radius); y++)
          if (Within(x, y, radius)) columns.Add((new Vector2Int(x, y), Distance(x, y)));
      return columns;
    }

    // The lowest open fluid cell at or above the building's base in every map
    // column within `radius` tiles; columns closed to the sky are skipped.
    public List<(Vector3Int Cell, float Distance)> OpenCellsWithin(IRadiationService radiation, int radius) {
      var cells = new List<(Vector3Int, float)>();
      foreach (var (column, distance) in ColumnsWithin(radius))
        if (radiation.TryFindOpenCell(column, BaseZ, out var cell)) cells.Add((cell, distance));
      return cells;
    }

    // Meltdown crater: the columns inside the ellipse centred on the footprint
    // whose semi-axes are the footprint's half-extents plus `rim` tiles (tile
    // centres, and only columns within `rim` tiles), with the bowl's depth in
    // layers: `depth` at the centre falling to 1 at the rim, depth x (1 - u)
    // rounded up, where u is the column's squared elliptical radius (0..1).
    public List<(Vector2Int Column, int Depth)> CraterColumns(int rim, int depth) {
      float cx = (MinX + MaxX + 1) * 0.5f, cy = (MinY + MaxY + 1) * 0.5f;
      float a = (MaxX - MinX + 1) * 0.5f + rim, b = (MaxY - MinY + 1) * 0.5f + rim;
      var columns = new List<(Vector2Int, int)>();
      foreach (var (column, _) in ColumnsWithin(rim)) {
        float ex = (column.x + 0.5f - cx) / a, ey = (column.y + 0.5f - cy) / b;
        float u = ex * ex + ey * ey;
        if (u <= 1f) columns.Add((column, Math.Max(1, Mathf.CeilToInt(depth * (1f - u)))));
      }
      return columns;
    }

    public Vector3Int NearestToCenter(List<Vector3Int> cells) {
      float cx = (MinX + MaxX) * 0.5f, cy = (MinY + MaxY) * 0.5f;
      return cells.OrderBy(c => (c.x - cx) * (c.x - cx) + (c.y - cy) * (c.y - cy)).ThenBy(c => c.x).ThenBy(c => c.y).First();
    }
  }
}
