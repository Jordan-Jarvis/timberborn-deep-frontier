using System;
using System.Collections.Generic;
using System.Linq;
using DeepFrontier.Scripts.Radiation;
using Timberborn.BlockSystem;
using Timberborn.CameraSystem;
using Timberborn.Characters;
using Timberborn.CoreUI;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.Explosions;
using Timberborn.Localization;
using Timberborn.MapStateSystem;
using Timberborn.MortalSystem;
using Timberborn.Navigation;
using Timberborn.NotificationSystem;
using Timberborn.TickSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.Meltdown {
  // Executes reactor meltdowns in its singleton tick, the same place native
  // ExplosionService.DestroyEverythingAffected deletes block objects (entity
  // ticks are not the place to delete the ticking entity). A reactor whose
  // core reached 1 requests it; if the game is saved first, the saved heat of
  // 1 requests it again on the first tick after load.
  //
  // Order: geometry (fails before any effect if the footprint has no open
  // fluid column), casualties (as native ExplosionService: characters first,
  // then the building), contamination through IRadiationService, then native
  // EntityService.Delete (its EntityDeletedEvent drives the native
  // deconstruction particles), sound, notification and dialog.
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
    private readonly List<ReactorCore> _pending = new();

    public MeltdownService(IRadiationService radiation, EntityService entities, CharacterPopulation population,
        NotificationBus notifications, DialogBoxShower dialogs, ExplosionSoundPlayer explosionSound,
        CameraService camera, MapSize mapSize, ILoc loc) {
      _radiation = radiation; _entities = entities; _population = population; _notifications = notifications;
      _dialogs = dialogs; _explosionSound = explosionSound; _camera = camera; _mapSize = mapSize; _loc = loc;
    }

    public void Request(ReactorCore core) {
      if (!_pending.Contains(core)) _pending.Add(core);
    }

    public void Tick() {
      if (_pending.Count == 0) return;
      var batch = _pending.ToArray();
      _pending.Clear();
      foreach (var core in batch)
        if (core) Execute(core);   // a reactor deleted since its request has nothing left to melt
    }

    private void Execute(ReactorCore core) {
      var spec = core.Spec;
      var site = BuildingSite.Of(core.GetComponent<BlockObject>(), _mapSize);
      var area = site.OpenCellsWithin(_radiation, spec.MeltdownRadius);
      var footprint = area.Where(c => c.Distance == 0).Select(c => c.Cell).ToList();
      if (footprint.Count == 0)
        throw new InvalidOperationException($"{core.Name}: meltdown found no open fluid column in the reactor footprint");
      var source = site.NearestToCenter(footprint);

      // Casualties: everyone inside, and every mortal character within the
      // kill radius, dies; beavers within the irradiation radius receive a
      // dose that irradiates them (10 days of hospital care, else fatal).
      var inside = new HashSet<Character>(core.GetComponent<Enterable>().EnterersInside.Select(e => e.GetComponent<Character>()));
      int killed = 0, irradiated = 0;
      foreach (var character in _population.Characters.ToList()) {
        if (!character.Alive) continue;
        var cell = NavigationCoordinateSystem.WorldToGridInt(character.Transform.position);
        int distance = site.Distance(cell.x, cell.y);
        var mortal = character.GetComponent<Mortal>();
        if (mortal && (inside.Contains(character) || distance <= spec.MeltdownKillRadius)) {
          mortal.DieInstantly(_loc.T(MeltdownLoc.DeathMessage, character.FirstName));
          killed++;
        } else if (distance <= spec.MeltdownIrradiationRadius) {
          var exposure = character.GetComponent<RadiationExposure>();
          if (!exposure) continue;   // bots have no radiation need
          exposure.AddDose(spec.MeltdownIrradiationDose);
          irradiated++;
        }
      }

      // Contamination: the core's radioactive water (spec volumes are
      // radioactive volume, one sludge good = 0.2) spreads over the footprint
      // and keeps pouring from its centre; fallout irradiates soil and adds
      // radioactive water, falling linearly from the footprint value to the
      // edge value at the radius.
      foreach (var cell in footprint) _radiation.AddRadioactiveWater(cell, spec.MeltdownInstantSludge / footprint.Count);
      _radiation.AddContinuousSource(source, spec.MeltdownSourceSludgePerHour, spec.MeltdownSourceHours);
      foreach (var (cell, distance) in area) {
        float t = distance / (float)spec.MeltdownRadius;
        _radiation.AddSoilRadiation(cell, Mathf.Lerp(spec.MeltdownFootprintSoilRadiation, spec.MeltdownEdgeSoilRadiation, t));
        if (_radiation.Sample(cell).Submerged)
          _radiation.AddRadioactiveWater(cell, Mathf.Lerp(spec.MeltdownFootprintWaterRadiation, spec.MeltdownEdgeWaterRadiation, t));
      }

      var position = core.Transform.position;
      _explosionSound.PlayGlobal(core.GameObject);
      _notifications.Post(_loc.T(MeltdownLoc.NotificationMeltdown, killed, irradiated), core);
      _entities.Delete(core);
      int days = Mathf.CeilToInt(spec.MeltdownSourceHours / 24f);
      _dialogs.Create()
        .SetMessage(_loc.T(MeltdownLoc.DialogTitle) + "\n\n" + _loc.T(MeltdownLoc.DialogCasualties, killed, irradiated)
          + "\n\n" + _loc.T(MeltdownLoc.DialogContamination, days, spec.MeltdownRadius))
        .SetConfirmButton(() => _camera.MoveTargetTo(position), _loc.T(MeltdownLoc.DialogShowSite))
        .SetDefaultCancelButton()
        .Show();
    }
  }

  // Footprint rectangle of a building and the open fluid cells around it.
  // Distances are Chebyshev tiles from the footprint (0 inside it).
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

    public int Distance(int x, int y) {
      int dx = x < MinX ? MinX - x : x > MaxX ? x - MaxX : 0;
      int dy = y < MinY ? MinY - y : y > MaxY ? y - MaxY : 0;
      return Math.Max(dx, dy);
    }

    // The lowest open fluid cell at or above the building's base in every map
    // column within `radius` tiles; columns closed to the sky are skipped.
    public List<(Vector3Int Cell, int Distance)> OpenCellsWithin(IRadiationService radiation, int radius) {
      var cells = new List<(Vector3Int, int)>();
      for (int x = Math.Max(0, MinX - radius); x <= Math.Min(_mapSize.x - 1, MaxX + radius); x++)
        for (int y = Math.Max(0, MinY - radius); y <= Math.Min(_mapSize.y - 1, MaxY + radius); y++) {
          int distance = Distance(x, y);
          if (distance > radius) continue;
          if (radiation.TryFindOpenCell(new Vector2Int(x, y), BaseZ, out var cell)) cells.Add((cell, distance));
        }
      return cells;
    }

    public Vector3Int NearestToCenter(List<Vector3Int> cells) {
      float cx = (MinX + MaxX) * 0.5f, cy = (MinY + MaxY) * 0.5f;
      return cells.OrderBy(c => (c.x - cx) * (c.x - cx) + (c.y - cy) * (c.y - cy)).ThenBy(c => c.x).ThenBy(c => c.y).First();
    }
  }
}
