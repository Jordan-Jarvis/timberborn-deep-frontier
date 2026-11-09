using System;
using System.Collections.Generic;
using System.Linq;
using DeepFrontier.Scripts.Radiation;
using UnityEngine;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>Soil radiation under open water columns, keyed by (x, y, column floor) as RadiationSimulation keys it.</summary>
  public interface IRadiationSoil {
    float SoilAt(Vector3Int columnCell);
    void AddSoilRadiation(Vector3Int columnCell, float amount);
  }

  /// <summary>
  /// The persistent soil of the Moddable Fluids build: values per column cell with Deep Frontier's soil half-life,
  /// applied once per in-game hour as HourlySoilPass does. Groundwork only: the soil-water exchange, the
  /// native-pattern bank layer, spread and deposition of evaporated water stay in RadiationSoil and
  /// RadiationSimulation until they move onto Moddable Fluids rules and loss reports.
  /// </summary>
  public sealed class RadiationSoilLedger : IRadiationSoil {
    private readonly Dictionary<Vector3Int, float> _soil = new Dictionary<Vector3Int, float>();
    public int Count => _soil.Count;

    public float SoilAt(Vector3Int columnCell) => _soil.TryGetValue(columnCell, out float value) ? value : 0f;

    public void AddSoilRadiation(Vector3Int columnCell, float amount) {
      if (!(amount > 0f) || float.IsInfinity(amount)) throw new ArgumentOutOfRangeException(nameof(amount), amount, "Soil radiation additions are positive and finite");
      _soil[columnCell] = SoilAt(columnCell) + amount;
    }

    /// <summary>Soil decay over <paramref name="hours"/>, clamped to 1 as HourlySoilPass does; values below MinSoilRadiation are gone.</summary>
    public void Decay(float hours) {
      if (!(hours > 0f)) throw new ArgumentOutOfRangeException(nameof(hours), hours, "Decay runs over a positive time");
      float keep = 1f - RadiationTuning.DecayPerHour(RadiationTuning.SoilHalfLifeDays) * hours;
      foreach (var cell in _soil.Keys.ToArray()) {
        float value = _soil[cell] * keep;
        if (value < RadiationTuning.MinSoilRadiation) _soil.Remove(cell); else _soil[cell] = value > 1f ? 1f : value;
      }
    }

    public void Load(IReadOnlyList<Vector3Int> cells, IReadOnlyList<float> values) {
      if (_soil.Count > 0) throw new InvalidOperationException("Soil radiation was loaded twice");
      for (int k = 0; k < cells.Count; k++) if (values[k] > 0f) AddSoilRadiation(cells[k], values[k]);
    }

    public (Vector3Int[] Cells, float[] Values) Save() {
      var cells = _soil.Keys.OrderBy(c => c.y).ThenBy(c => c.x).ThenBy(c => c.z).ToArray();
      return (cells, cells.Select(c => _soil[c]).ToArray());
    }
  }
}
