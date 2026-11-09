using System;
using System.Collections.Generic;
using System.Linq;
using DeepFrontier.Scripts.Radiation;
using ModdableFluids;
using UnityEngine;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>
  /// <see cref="IRadiationService"/> backed by Moddable Fluids, so the reactor, bots, storage, tide and sensors can
  /// move one at a time (migration groundwork; flagged build and harness only). Water reads come from the world
  /// state published at the last completed fluid tick; radioactive water is added through the world service; the
  /// tide's radioactive share is the world's source composition override. Soil comes from <see cref="IRadiationSoil"/>.
  /// Timed sources, the tide share and requests made before the first fluid tick are applied in <see cref="Tick"/>
  /// (main thread), as RadiationSimulation applies them at the start of its Tick.
  /// The semantics are RadiationSimulation's; differences are named where they occur.
  /// </summary>
  public class ModdableFluidsRadiationService : IRadiationService {
    public const string TideOwner = "DeepFrontier.RadioactiveTide";
    private readonly DeepFrontierRadioactiveWater _provider;
    private readonly IRadiationSoil _soil;
    private readonly Func<float> _waterPerStrengthHour;
    private readonly Func<Vector2Int> _mapSize;
    private readonly List<RadiationSourceRecord> _sources = new List<RadiationSourceRecord>();
    private readonly List<(Vector3Int Cell, float Volume)> _early = new List<(Vector3Int, float)>();
    private readonly List<(Vector3Int Cell, float Amount)> _earlySoil = new List<(Vector3Int, float)>();
    private float _tideShare, _publishedTideShare;
    private int _nextSourceId = 1;

    public ModdableFluidsRadiationService(DeepFrontierRadioactiveWater provider, IRadiationSoil soil, Func<float> waterPerStrengthHour, Func<Vector2Int> mapSize) {
      _provider = provider ?? throw new ArgumentNullException(nameof(provider));
      _soil = soil ?? throw new ArgumentNullException(nameof(soil));
      _waterPerStrengthHour = waterPerStrengthHour ?? throw new ArgumentNullException(nameof(waterPerStrengthHour));
      _mapSize = mapSize ?? throw new ArgumentNullException(nameof(mapSize));
    }

    public IReadOnlyList<RadiationSourceRecord> Sources => _sources;
    public int NextSourceId => _nextSourceId;
    /// <summary>Requests waiting for the first fluid tick (water and soil additions before any state is published).</summary>
    public int EarlyAdditions => _early.Count + _earlySoil.Count;

    private IFluidWorld World => (_provider.Scene ?? throw new InvalidOperationException("Radiation has no active Moddable Fluids scene")).World;
    private bool HasState => _provider.Scene != null && _provider.Scene.HasWorld && World.HasState;

    // ------------------------------------------------------------------ state

    /// <summary>Sources and the counter from a save (version 4, or 2/3 before their water is imported).</summary>
    public void LoadSources(IReadOnlyList<RadiationSourceRecord> sources, int nextSourceId) {
      if (_sources.Count > 0 || _nextSourceId != 1) throw new InvalidOperationException("Radiation sources were loaded twice");
      if (sources.Any(s => s.Id >= nextSourceId)) throw new InvalidOperationException("Saved radiation source id is not below NextSourceId");
      _sources.AddRange(sources.Select(s => new RadiationSourceRecord(s.Id, s.Cell, s.VolumePerHour, s.RemainingHours)));
      _nextSourceId = nextSourceId;
    }

    /// <summary>
    /// Main thread, start of Deep Frontier's tick: version 2 sludge from an import, requests from before the first
    /// fluid tick, the tide share, then timed sources over <paramref name="hours"/> (EmitSources).
    /// </summary>
    public void Tick(float hours) {
      if (!HasState) return;
      var imported = _provider.TakeImportResult();
      if (imported != null)
        foreach (var (x, y, floor, volume) in imported.SludgeAdditions) World.QueueAddition(x, y, floor, _provider.Radioactive, volume);
      foreach (var (cell, volume) in _early) AddRadioactiveWater(cell, volume);
      foreach (var (cell, amount) in _earlySoil) AddSoilRadiation(cell, amount);
      _early.Clear(); _earlySoil.Clear();
      if (_tideShare != _publishedTideShare) {
        World.SetSourceComposition(TideOwner, _tideShare > 0f ? new Dictionary<string, double> { [DeepFrontierRadioactiveWater.FluidId] = _tideShare } : null);
        _publishedTideShare = _tideShare;
      }
      for (int k = _sources.Count - 1; k >= 0; k--) {
        var source = _sources[k];
        float active = source.RemainingHours < hours ? source.RemainingHours : hours;
        if (active > 0f) AddRadioactiveWater(source.Cell, source.VolumePerHour * active);
        source.RemainingHours -= hours;
        if (source.RemainingHours <= 0f) _sources.RemoveAt(k);
      }
    }

    // -------------------------------------------------------------- service

    public void AddRadioactiveWater(Vector3Int cell, float radioactiveVolume) {
      RequirePositive(radioactiveVolume, nameof(radioactiveVolume));
      RequireInMap(new Vector2Int(cell.x, cell.y));
      // Before the first fluid tick nothing is published to check the cell against; checked when applied.
    // (RadiationSimulation checks it at once against the native map: a bad cell fails later here.)
      if (!HasState) { _early.Add((cell, radioactiveVolume)); return; }
      ValidateOpenCell(cell);
      World.QueueAddition(cell.x, cell.y, cell.z, _provider.Radioactive, radioactiveVolume);
    }

    public int AddContinuousSource(Vector3Int cell, float volumePerHour, float durationHours) {
      RequirePositive(volumePerHour, nameof(volumePerHour));
      RequirePositive(durationHours, nameof(durationHours));
      RequireInMap(new Vector2Int(cell.x, cell.y));
      if (HasState) ValidateOpenCell(cell);
      int id = _nextSourceId++;
      _sources.Add(new RadiationSourceRecord(id, cell, volumePerHour, durationHours));
      return id;
    }

    public void RemoveContinuousSource(int id) {
      int index = _sources.FindIndex(s => s.Id == id);
      if (index < 0) throw new ArgumentException("No radiation source with id " + id, nameof(id));
      _sources.RemoveAt(index);
    }

    public void AddSoilRadiation(Vector3Int cell, float amount) {
      RequirePositive(amount, nameof(amount));
      if (!HasState) { RequireInMap(new Vector2Int(cell.x, cell.y)); _earlySoil.Add((cell, amount)); return; }
      _soil.AddSoilRadiation(ColumnCell(cell), amount);
    }

    public void SetSourceRadioactiveShare(float share) {
      if (!(share >= 0f && share <= 1f)) throw new ArgumentOutOfRangeException(nameof(share), share, "Must be within 0..1");
      _tideShare = share;
    }

    public float WaterPerStrengthHour => _waterPerStrengthHour();

    public bool TryFindOpenCell(Vector2Int xy, int z, out Vector3Int cell) {
      RequireInMap(xy);
      cell = default;
      if (!HasState) return false;
      foreach (var column in World.SampleCell(xy.x, xy.y)) {
        if (z >= column.Floor && z < column.Ceiling) { cell = new Vector3Int(xy.x, xy.y, z); return true; }
        if (column.Floor > z) { cell = new Vector3Int(xy.x, xy.y, column.Floor); return true; }
      }
      return false;
    }

    public RadiationSample Sample(Vector3Int cell) {
      if (!HasState || !World.TrySample(cell.x, cell.y, cell.z, out var column)) return default;
      float water = RadiationTuning.Detected((float)column.GetShare(_provider.Radioactive));
      return new RadiationSample(true, water, (float)column.GetShare(World.Registry.Badwater), column.Covers(cell.z),
        _soil.SoilAt(new Vector3Int(cell.x, cell.y, column.Floor)));
    }

    public float GetRadiation(Vector3Int cell) {
      var sample = Sample(cell);
      float value = sample.SoilRadiation * RadiationTuning.SoilHazardWeight;
      return sample.Submerged && sample.WaterRadiation > value ? sample.WaterRadiation : value;
    }

    public bool IsColumnContaminated(Vector3Int cell) =>
      HasState && World.TrySample(cell.x, cell.y, cell.z, out var column) && column.GetShare(_provider.Radioactive) >= RadiationTuning.DetectionLimit;

    /// <summary>Radioactive volume in all columns, overflow included (RadiationSimulation sums r x depth).</summary>
    public float TotalWaterRadiation => HasState ? (float)World.TotalVolume(_provider.Radioactive) : 0f;

    /// <summary>True until the first fluid tick has published state (and imported a legacy save).</summary>
    public bool SavedStatePending => !HasState || _provider.ImportPending;

    // ------------------------------------------------------------- internals

    private Vector3Int ColumnCell(Vector3Int cell) {
      RequireInMap(new Vector2Int(cell.x, cell.y));
      if (!World.TrySample(cell.x, cell.y, cell.z, out var column))
        throw new ArgumentException("Radiation cell " + cell + " is not inside an open fluid column; use TryFindOpenCell", nameof(cell));
      return new Vector3Int(cell.x, cell.y, column.Floor);
    }

    private void ValidateOpenCell(Vector3Int cell) {
      if (!World.TrySample(cell.x, cell.y, cell.z, out _))
        throw new ArgumentException("Radiation cell " + cell + " is not inside an open fluid column; use TryFindOpenCell", nameof(cell));
    }

    private void RequireInMap(Vector2Int xy) {
      var size = _mapSize();
      if (xy.x < 0 || xy.y < 0 || xy.x >= size.x || xy.y >= size.y)
        throw new ArgumentOutOfRangeException(nameof(xy), "Cell " + xy + " lies outside the " + size.x + "x" + size.y + " map");
    }

    private static void RequirePositive(float value, string name) {
      if (!(value > 0f) || float.IsInfinity(value)) throw new ArgumentOutOfRangeException(name, value, "Must be a positive finite amount");
    }
  }
}
