using System;
using System.Collections.Generic;
using System.Linq;
using DeepFrontier.Scripts.Radiation;
using ModdableFluids;
using UnityEngine;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>
  /// Native water geometry as RadiationSimulation read it (IThreadSafeWaterMap in game): valid from load, before
  /// the first fluid tick, so open-cell checks and the submerged and badwater readings match Deep Frontier's.
  /// </summary>
  public interface IRadiationCellMap {
    Vector2Int Size { get; }
    bool IsOpenCell(Vector3Int cell);
    /// <summary>The lowest open cell at <paramref name="xy"/> whose column contains or lies above height <paramref name="z"/>.</summary>
    bool TryFindOpenCell(Vector2Int xy, int z, out Vector3Int cell);
    /// <summary>Native CellIsUnderwater.</summary>
    bool IsSubmerged(Vector3Int cell);
    /// <summary>Native ColumnContamination: the badwater share where the cell is under the surface, else 0.</summary>
    float BadwaterShare(Vector3Int cell);
  }

  /// <summary>
  /// <see cref="IRadiationService"/> backed by Moddable Fluids, so the reactor, bots, storage, tide and sensors can
  /// move one at a time (migration groundwork; flagged build and harness only). Water reads come from the world
  /// state published at the last completed fluid tick; radioactive water is added through the world service; the
  /// tide's radioactive share is the world's source composition override. Soil comes from <see cref="RadiationSoilField"/>
  /// (the last completed pass, with the bank layer). Timed sources, the tide share and water added before the first
  /// fluid tick are applied in <see cref="Tick"/> (main thread), as RadiationSimulation applies them at the start of its Tick.
  /// The semantics are RadiationSimulation's; differences are named where they occur.
  /// </summary>
  public class ModdableFluidsRadiationService : IRadiationService, IIrradiatedGround, IRadiationWaterCells {
    public const string TideOwner = "DeepFrontier.RadioactiveTide";
    private readonly DeepFrontierRadioactiveWater _provider;
    private RadiationSoilField _soil;
    private readonly Func<float> _waterPerStrengthHour;
    private readonly IRadiationCellMap _cells;
    private readonly List<RadiationSourceRecord> _sources = new List<RadiationSourceRecord>();
    private readonly List<(Vector3Int Cell, float Volume)> _early = new List<(Vector3Int, float)>();
    private float _tideShare, _publishedTideShare;
    private int _nextSourceId = 1;

    public ModdableFluidsRadiationService(DeepFrontierRadioactiveWater provider, RadiationSoilField soil, IRadiationCellMap cells, Func<float> waterPerStrengthHour)
      : this(provider, cells, waterPerStrengthHour) {
      AttachSoil(soil);
    }

    /// <summary>For the game, whose soil field needs the loaded map and clock: <see cref="AttachSoil"/> follows in Load.</summary>
    protected ModdableFluidsRadiationService(DeepFrontierRadioactiveWater provider, IRadiationCellMap cells, Func<float> waterPerStrengthHour) {
      _provider = provider ?? throw new ArgumentNullException(nameof(provider));
      _cells = cells ?? throw new ArgumentNullException(nameof(cells));
      _waterPerStrengthHour = waterPerStrengthHour ?? throw new ArgumentNullException(nameof(waterPerStrengthHour));
    }

    protected void AttachSoil(RadiationSoilField soil) {
      if (_soil != null) throw new InvalidOperationException("The radiation facade already has its soil field");
      _soil = soil ?? throw new ArgumentNullException(nameof(soil));
    }

    public IReadOnlyList<RadiationSourceRecord> Sources => _sources;
    public int NextSourceId => _nextSourceId;
    /// <summary>Radioactive water added before the first fluid tick published state (it waits for it, and is saved).</summary>
    public IReadOnlyList<(Vector3Int Cell, float Volume)> EarlyAdditions => _early;
    public RadiationSoilField Soil => _soil ?? throw new InvalidOperationException("The radiation facade has no soil field before Load");

    private IFluidWorld World => (_provider.Scene ?? throw new InvalidOperationException("Radiation has no active Moddable Fluids scene")).World;
    private bool HasState => _provider.Scene != null && _provider.Scene.HasWorld && World.HasState;

    // ------------------------------------------------------------------ state

    /// <summary>Radioactive water a save recorded as added before its first fluid tick (checked when it was added).</summary>
    public void LoadEarlyAdditions(IReadOnlyList<(Vector3Int Cell, float Volume)> additions) {
      if (_early.Count > 0) throw new InvalidOperationException("Early radioactive water was loaded twice");
      foreach (var (cell, volume) in additions) { RequirePositive(volume, nameof(additions)); RequireInMap(new Vector2Int(cell.x, cell.y)); _early.Add((cell, volume)); }
    }

    /// <summary>Sources and the counter from a save (version 4, or 2/3 before their water is imported).</summary>
    public void LoadSources(IReadOnlyList<RadiationSourceRecord> sources, int nextSourceId) {
      if (_sources.Count > 0 || _nextSourceId != 1) throw new InvalidOperationException("Radiation sources were loaded twice");
      if (sources.Any(s => s.Id >= nextSourceId)) throw new InvalidOperationException("Saved radiation source id is not below NextSourceId");
      _sources.AddRange(sources.Select(s => new RadiationSourceRecord(s.Id, s.Cell, s.VolumePerHour, s.RemainingHours)));
      _nextSourceId = nextSourceId;
    }

    /// <summary>
    /// Main thread, start of Deep Frontier's tick: version 2 sludge from an import, water added before the first
    /// fluid tick, the tide share, then timed sources over <paramref name="hours"/> (EmitSources).
    /// </summary>
    public void Tick(float hours) {
      if (!HasState) return;
      var imported = _provider.TakeImportResult();
      if (imported != null)
        foreach (var (x, y, floor, volume) in imported.SludgeAdditions) World.QueueAddition(x, y, floor, _provider.Radioactive, volume);
      var early = _early.ToArray();
      _early.Clear();
      foreach (var (cell, volume) in early) AddRadioactiveWater(cell, volume);
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
      ValidateOpenCell(cell);
      // Moddable Fluids takes additions once a fluid tick has published state; until then they wait.
      if (!HasState) { _early.Add((cell, radioactiveVolume)); return; }
      World.QueueAddition(cell.x, cell.y, cell.z, _provider.Radioactive, radioactiveVolume);
    }

    public int AddContinuousSource(Vector3Int cell, float volumePerHour, float durationHours) {
      RequirePositive(volumePerHour, nameof(volumePerHour));
      RequirePositive(durationHours, nameof(durationHours));
      ValidateOpenCell(cell);
      int id = _nextSourceId++;
      _sources.Add(new RadiationSourceRecord(id, cell, volumePerHour, durationHours));
      return id;
    }

    public void RemoveContinuousSource(int id) {
      int index = _sources.FindIndex(s => s.Id == id);
      if (index < 0) throw new ArgumentException("No radiation source with id " + id, nameof(id));
      _sources.RemoveAt(index);
    }

    /// <summary>Applied by the next pass of the soil rules (RadiationSimulation applies it in its next Tick).</summary>
    public void AddSoilRadiation(Vector3Int cell, float amount) {
      RequirePositive(amount, nameof(amount));
      ValidateOpenCell(cell);
      Soil.RequestSoil(cell, amount);
    }

    public void SetSourceRadioactiveShare(float share) {
      if (!(share >= 0f && share <= 1f)) throw new ArgumentOutOfRangeException(nameof(share), share, "Must be within 0..1");
      _tideShare = share;
    }

    public float WaterPerStrengthHour => _waterPerStrengthHour();

    public bool TryFindOpenCell(Vector2Int xy, int z, out Vector3Int cell) {
      RequireInMap(xy);
      return _cells.TryFindOpenCell(xy, z, out cell);
    }

    /// <summary>
    /// The fluid state of the last completed tick; submerged and badwater are native readings, as RadiationSimulation
    /// reports them (a cell above the surface reads badwater 0).
    /// </summary>
    public RadiationSample Sample(Vector3Int cell) {
      RequireInMap(new Vector2Int(cell.x, cell.y));
      if (!HasState || !World.TrySample(cell.x, cell.y, cell.z, out var column)) return default;
      float water = RadiationTuning.Detected((float)column.GetShare(_provider.Radioactive));
      return new RadiationSample(true, water, _cells.BadwaterShare(cell), _cells.IsSubmerged(cell), Soil.SoilAt(new Vector3Int(cell.x, cell.y, column.Floor)));
    }

    public float GetRadiation(Vector3Int cell) {
      var sample = Sample(cell);
      float value = sample.SoilRadiation * RadiationTuning.SoilHazardWeight;
      return sample.Submerged && sample.WaterRadiation > value ? sample.WaterRadiation : value;
    }

    public bool IsColumnContaminated(Vector3Int cell) => ColumnRadiation(cell) >= RadiationTuning.DetectionLimit;

    /// <summary>The detected radioactive share of the column containing the cell (0 before the first fluid tick).</summary>
    public float ColumnRadiation(Vector3Int cell) {
      RequireInMap(new Vector2Int(cell.x, cell.y));
      return HasState && World.TrySample(cell.x, cell.y, cell.z, out var column) ? RadiationTuning.Detected((float)column.GetShare(_provider.Radioactive)) : 0f;
    }

    public bool IsOpenCell(Vector3Int cell) {
      RequireInMap(new Vector2Int(cell.x, cell.y));
      return _cells.IsOpenCell(cell);
    }

    /// <summary>Soil (or the bank layer) at or above IrradiatedGroundThreshold; nothing before the first fluid tick applied the save.</summary>
    public bool IsIrradiatedGround(Vector3Int cell) {
      RequireInMap(new Vector2Int(cell.x, cell.y));
      if (SavedStatePending || !World.TrySample(cell.x, cell.y, cell.z, out var column)) return false;
      return Soil.SoilAt(new Vector3Int(cell.x, cell.y, column.Floor)) >= RadiationTuning.IrradiatedGroundThreshold;
    }

    /// <summary>Radioactive volume in all columns, overflow included (RadiationSimulation sums r x depth).</summary>
    public float TotalWaterRadiation => HasState ? (float)World.TotalVolume(_provider.Radioactive) : 0f;

    /// <summary>True until the first fluid tick has published state, imported a legacy save and run the soil rules.</summary>
    public bool SavedStatePending => !HasState || _provider.ImportPending || !Soil.HasPass;

    // ------------------------------------------------------------- internals

    private void ValidateOpenCell(Vector3Int cell) {
      if (!IsOpenCell(cell))
        throw new ArgumentException("Radiation cell " + cell + " is not inside an open fluid column; use TryFindOpenCell", nameof(cell));
    }

    private void RequireInMap(Vector2Int xy) {
      var size = _cells.Size;
      if (xy.x < 0 || xy.y < 0 || xy.x >= size.x || xy.y >= size.y)
        throw new ArgumentOutOfRangeException(nameof(xy), "Cell " + xy + " lies outside the " + size.x + "x" + size.y + " map");
    }

    private static void RequirePositive(float value, string name) {
      if (!(value > 0f) || float.IsInfinity(value)) throw new ArgumentOutOfRangeException(name, value, "Must be a positive finite amount");
    }
  }
}
