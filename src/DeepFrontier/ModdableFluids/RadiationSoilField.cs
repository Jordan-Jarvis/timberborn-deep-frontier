using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using DeepFrontier.Scripts.Radiation;
using ModdableFluids;
using UnityEngine;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>The native-pattern bank layer next to radioactive water (RadiationSoil's kernels), read on the main thread.</summary>
  public interface IRadiationBankLayer {
    /// <summary>The bank level under the column with floor <c>columnCell.z</c> at (x, y); 0 where none.</summary>
    float BankAt(Vector3Int columnCell);
  }

  /// <summary>What one completed pass left, for main-thread readers. Never changed after it is published.</summary>
  public sealed class RadiationFieldSnapshot {
    /// <summary>Completed passes (0: loaded state, before the first fluid tick).</summary>
    public int Pass { get; }
    /// <summary>Stored soil radiation above 0, by (x, y, column floor).</summary>
    public IReadOnlyDictionary<Vector3Int, float> Soil { get; }
    /// <summary>Radioactive share r above 0 after this pass's cutoff, by (x, y, column floor); a share still growing below DetectionLimit is included.</summary>
    public IReadOnlyDictionary<Vector3Int, float> Water { get; }
    public float HourAccumulator { get; }
    internal RadiationFieldSnapshot(int pass, Dictionary<Vector3Int, float> soil, Dictionary<Vector3Int, float> water, float hourAccumulator) {
      Pass = pass; Soil = soil; Water = water; HourAccumulator = hourAccumulator;
    }
  }

  /// <summary>
  /// Deep Frontier's soil radiation and its water rules in the Moddable Fluids build. <see cref="ApplyRules"/> runs on
  /// the native worker after every completed fluid tick (DeepFrontierRadioactiveWater is its IFluidColumnRules) and
  /// does, in RadiationSimulation.Tick's order and with its formulas and constants:
  /// <list type="number">
  /// <item>geometry: soil follows the ground when a cell's columns change (Reconcile's rule);</item>
  /// <item>deposition: radioactive volume that evaporated, was deleted by geometry or was added into a closed cell goes
  /// into the soil (x SoilPerDepositedVolume), from the tick's Moddable Fluids losses; pumped radioactive volume is
  /// credited to the sludge intake at that cell (CreditIntakes);</item>
  /// <item>soil requests (AddSoilRadiation), into the column containing the cell or the lowest one above it;</item>
  /// <item>per column: decay of the radioactive share (RunInteraction), the soil-water exchange or rinsing
  /// (RadiationSoil.Exchange, <see cref="RadiationSoilFormulas"/>), and the 0.5% cutoff for a share that stopped
  /// growing (Rescan). The share changes become volume conversions between radioactive and fresh water;</item>
  /// <item>once per accumulated game hour, soil decay and lateral spread (HourlySoilPass).</item>
  /// </list>
  /// The result is published at once, so main-thread readers see whole passes. Differences from the one-fluid
  /// simulation are named where they occur. The depth d of the exchange is the column's physical volume (Moddable
  /// Fluids' unit), and b is everything in the column that is neither fresh nor radioactive water.
  /// </summary>
  public sealed class RadiationSoilField {
    private readonly object _gate = new object();
    private readonly int _width, _height;
    private readonly float _hoursPerTick;
    private float _washoutPerHour = float.NaN;
    private volatile RadiationFieldSnapshot _published;
    private bool _validated, _lenientLoad;
    // Main thread -> worker.
    private List<(Vector3Int Cell, float Amount)> _requests = new List<(Vector3Int, float)>();
    // Worker -> main thread.
    private readonly Dictionary<Vector3Int, float> _credits = new Dictionary<Vector3Int, float>();
    private readonly HashSet<Vector2Int> _changedCells = new HashSet<Vector2Int>();
    private readonly List<string> _loadCorrections = new List<string>();
    // Worker state: the columns of every cell holding soil at the end of the last pass, (floor, ceiling) pairs.
    private readonly Dictionary<Vector2Int, int[]> _soilGeometry = new Dictionary<Vector2Int, int[]>();
    // Per-pass column index (worker; arrays reused).
    private int _columns;
    private int[] _x = new int[0], _y = new int[0], _floor = new int[0], _ceiling = new int[0], _sorted = new int[0], _cellStart = new int[0], _fill = new int[0];
    private double[] _vr = new double[0], _total = new double[0];
    private float[] _columnSoil = new float[0];

    public IRadiationBankLayer Bank { get; set; }

    /// <param name="width">Map width in cells.</param>
    /// <param name="height">Map height in cells.</param>
    /// <param name="hoursPerTick">In-game hours per native water tick (IDayNightCycle.FixedDeltaTimeInHours).</param>
    public RadiationSoilField(int width, int height, float hoursPerTick) {
      if (width < 1 || height < 1) throw new ArgumentOutOfRangeException(nameof(width), "The map has no cells");
      if (!(hoursPerTick > 0f) || float.IsInfinity(hoursPerTick)) throw new ArgumentOutOfRangeException(nameof(hoursPerTick), hoursPerTick, "Hours per tick are positive");
      _width = width; _height = height; _hoursPerTick = hoursPerTick;
      _published = new RadiationFieldSnapshot(0, new Dictionary<Vector3Int, float>(), new Dictionary<Vector3Int, float>(), 0f);
    }

    public float HoursPerTick => _hoursPerTick;
    public RadiationFieldSnapshot Published => _published;
    /// <summary>Whether a completed fluid tick has run the rules (until then the loaded state is pending).</summary>
    public bool HasPass => _published.Pass > 0;

    /// <summary>
    /// The native washout rate of soil under clean water, per game hour: native ContaminationNegativeEqualizationRate
    /// per tick over the hours per tick (RadiationSoil.PostLoad). Set by the game side before the first fluid tick.
    /// </summary>
    public void SetWashoutPerHour(float washoutPerHour) {
      if (!(washoutPerHour > 0f) || float.IsInfinity(washoutPerHour)) throw new ArgumentOutOfRangeException(nameof(washoutPerHour), washoutPerHour, "The washout rate is positive");
      _washoutPerHour = washoutPerHour;
    }

    // ------------------------------------------------------------- main thread

    /// <summary>
    /// Saved soil by (x, y, column floor) and the hour counter, before the first fluid tick. Each cell must match a
    /// column floor at the first pass; with <paramref name="lenient"/> (an exception snapshot, as RadiationSimulation's
    /// ApplyLoaded treats it) a cell without one is dropped and reported instead.
    /// </summary>
    public void Load(IReadOnlyList<Vector3Int> cells, IReadOnlyList<float> values, float hourAccumulator, bool lenient) {
      if (cells == null || values == null || cells.Count != values.Count) throw new ArgumentException("Saved soil lists differ in length");
      if (_published.Pass > 0 || _published.Soil.Count > 0) throw new InvalidOperationException("Soil radiation was loaded twice or after a pass");
      if (!(hourAccumulator >= 0f) || float.IsInfinity(hourAccumulator)) throw new ArgumentOutOfRangeException(nameof(hourAccumulator), hourAccumulator, "Saved hour counter");
      var soil = new Dictionary<Vector3Int, float>();
      for (int k = 0; k < cells.Count; k++) {
        float value = values[k];
        if (float.IsNaN(value) || value < 0f || value > 1f) throw new InvalidOperationException("Saved soil radiation " + value + " at " + cells[k] + " is not within 0..1");
        RequireInMap(cells[k].x, cells[k].y);
        if (soil.ContainsKey(cells[k])) throw new InvalidOperationException("Saved soil radiation lists " + cells[k] + " twice");
        if (value > 0f) soil.Add(cells[k], value);
      }
      _lenientLoad = lenient;
      _published = new RadiationFieldSnapshot(0, soil, new Dictionary<Vector3Int, float>(), hourAccumulator);
    }

    /// <summary>AddSoilRadiation: applied in the next pass to the column containing the cell, or the lowest one above it.</summary>
    public void RequestSoil(Vector3Int cell, float amount) {
      if (!(amount > 0f) || float.IsInfinity(amount)) throw new ArgumentOutOfRangeException(nameof(amount), amount, "Soil radiation additions are positive and finite");
      RequireInMap(cell.x, cell.y);
      lock (_gate) _requests.Add((cell, amount));
    }

    /// <summary>Requests not yet applied by a pass (saved with the soil).</summary>
    public IReadOnlyList<(Vector3Int Cell, float Amount)> PendingRequests { get { lock (_gate) return _requests.ToArray(); } }

    /// <summary>Stored soil, or the bank layer, whichever is higher (RadiationSimulation.SoilAt), at the last completed pass.</summary>
    public float SoilAt(Vector3Int columnCell) {
      float soil = _published.Soil.TryGetValue(columnCell, out float value) ? value : 0f;
      var bank = Bank;
      return bank == null ? soil : Mathf.Max(soil, bank.BankAt(columnCell));
    }

    /// <summary>Main thread: the radioactive volume removed by native removals at each cell since the last call (CreditIntakes).</summary>
    public Dictionary<Vector3Int, float> TakeRemovedRadioactive() {
      lock (_gate) {
        var result = new Dictionary<Vector3Int, float>(_credits);
        _credits.Clear();
        return result;
      }
    }

    /// <summary>Main thread: cells whose columns changed since the last call (their ground is checked for plants again).</summary>
    public Vector2Int[] TakeChangedCells() {
      lock (_gate) {
        var result = _changedCells.ToArray();
        _changedCells.Clear();
        return result;
      }
    }

    /// <summary>Main thread: soil cells a lenient (exception snapshot) load dropped at the first pass.</summary>
    public string[] TakeLoadCorrections() {
      lock (_gate) {
        var result = _loadCorrections.ToArray();
        _loadCorrections.Clear();
        return result;
      }
    }

    // ------------------------------------------------------------------ worker

    /// <summary>One completed fluid tick (native worker thread). See the class summary for the order.</summary>
    public void ApplyRules(IFluidColumnEditor columns, FluidHandle radioactive, FluidHandle water) {
      if (columns == null) throw new ArgumentNullException(nameof(columns));
      if (float.IsNaN(_washoutPerHour)) throw new InvalidOperationException("Radiation soil: the native washout rate was not set before the first fluid tick");
      var previous = _published;
      var soil = new Dictionary<Vector3Int, float>(previous.Soil);
      List<(Vector3Int Cell, float Amount)> requests;
      lock (_gate) { requests = _requests; _requests = new List<(Vector3Int, float)>(); }
      IndexColumns(columns, radioactive);
      var changed = new List<Vector2Int>();
      if (!_validated) ValidateLoaded(soil);
      else SyncGeometry(soil, changed);
      var credits = Deposit(columns.Losses, radioactive, soil);
      foreach (var (cell, amount) in requests) {
        int c = ContainingColumn(cell.x, cell.y, cell.z);
        if (c < 0) c = LowestAbove(cell.x, cell.y, cell.z);
        if (c < 0) throw new InvalidOperationException("Soil radiation at " + cell + " has no fluid column at or above it");
        var key = Key(c);
        soil[key] = Mathf.Min(1f, Get(soil, key) + amount);
      }
      var waterShares = ApplyWaterRules(columns, radioactive, water, soil, previous.Water);
      float accumulator = previous.HourAccumulator;
      // RadiationSimulation counts hours only while something radioactive is tracked (its envelope).
      if (soil.Count > 0 || waterShares.Count > 0 || requests.Count > 0 || credits > 0) {
        accumulator += _hoursPerTick;
        if (accumulator >= 1f) {
          if (soil.Count > 0) HourlySoilPass(soil, accumulator);
          accumulator = 0f;
        }
      }
      TrackSoilGeometry(soil);
      _published = new RadiationFieldSnapshot(previous.Pass + 1, soil, waterShares, accumulator);
      if (changed.Count > 0) lock (_gate) foreach (var cell in changed) _changedCells.Add(cell);
    }

    private void IndexColumns(IFluidColumnEditor columns, FluidHandle radioactive) {
      int n = _columns = columns.ColumnCount;
      if (_x.Length < n) {
        int size = Math.Max(n, _x.Length * 2);
        Array.Resize(ref _x, size); Array.Resize(ref _y, size); Array.Resize(ref _floor, size); Array.Resize(ref _ceiling, size);
        Array.Resize(ref _sorted, size); Array.Resize(ref _vr, size); Array.Resize(ref _total, size); Array.Resize(ref _columnSoil, size);
      }
      int cells = _width * _height;
      if (_cellStart.Length != cells + 1) { _cellStart = new int[cells + 1]; _fill = new int[cells]; }
      else { Array.Clear(_cellStart, 0, _cellStart.Length); Array.Clear(_fill, 0, _fill.Length); }
      for (int c = 0; c < n; c++) {
        int x = _x[c] = columns.X(c), y = _y[c] = columns.Y(c);
        RequireInMap(x, y);
        _floor[c] = columns.Floor(c); _ceiling[c] = columns.Ceiling(c);
        _vr[c] = columns.GetVolume(c, radioactive); _total[c] = columns.TotalVolume(c); _columnSoil[c] = 0f;
        _cellStart[y * _width + x + 1]++;
      }
      for (int i = 0; i < cells; i++) _cellStart[i + 1] += _cellStart[i];
      for (int c = 0; c < n; c++) {
        int cell = _y[c] * _width + _x[c];
        _sorted[_cellStart[cell] + _fill[cell]++] = c;
      }
      // Floors ascending within a cell, as the native column order.
      for (int cell = 0; cell < cells; cell++) {
        int lo = _cellStart[cell], hi = _cellStart[cell + 1];
        for (int i = lo + 1; i < hi; i++) {
          int c = _sorted[i], j = i - 1;
          while (j >= lo && _floor[_sorted[j]] > _floor[c]) { _sorted[j + 1] = _sorted[j]; j--; }
          _sorted[j + 1] = c;
        }
      }
    }

    private Vector3Int Key(int c) => new Vector3Int(_x[c], _y[c], _floor[c]);
    private static float Get(Dictionary<Vector3Int, float> map, Vector3Int key) => map.TryGetValue(key, out float value) ? value : 0f;
    private int CellLo(int x, int y) => _cellStart[y * _width + x];
    private int CellHi(int x, int y) => _cellStart[y * _width + x + 1];

    private int ColumnWithFloor(int x, int y, int floor) {
      for (int i = CellLo(x, y); i < CellHi(x, y); i++) if (_floor[_sorted[i]] == floor) return _sorted[i];
      return -1;
    }

    private int ContainingColumn(int x, int y, int z) {
      for (int i = CellLo(x, y); i < CellHi(x, y); i++) { int c = _sorted[i]; if (z >= _floor[c] && z < _ceiling[c]) return c; }
      return -1;
    }

    // RadiationSimulation.LowestSlotAbove.
    private int LowestAbove(int x, int y, int z) {
      for (int i = CellLo(x, y); i < CellHi(x, y); i++) { int c = _sorted[i]; if (_floor[c] > z) return c; }
      return -1;
    }

    // First pass after a load: every saved soil cell must sit on a column floor (RadiationSimulation.ApplyLoaded).
    private void ValidateLoaded(Dictionary<Vector3Int, float> soil) {
      var problems = new List<string>();
      foreach (var key in soil.Keys.ToArray()) {
        if (ColumnWithFloor(key.x, key.y, key.z) >= 0) continue;
        if (_lenientLoad) { soil.Remove(key); lock (_gate) _loadCorrections.Add("dropped soil at " + key + ": no column with that floor"); continue; }
        problems.Add(key.ToString());
      }
      if (problems.Count > 0) throw new InvalidOperationException("Saved soil radiation does not match a native water column floor after load: " + string.Join(", ", problems));
      _validated = true;
    }

    // RadiationSimulation.Reconcile's soil rule, for every cell holding soil whose columns changed: the soil of an
    // old floor moves to the new column with that floor, else to a new floor raised directly above it (each old
    // surface to at most one new column); the rest is gone with the ground it lay on.
    private void SyncGeometry(Dictionary<Vector3Int, float> soil, List<Vector2Int> changed) {
      foreach (var pair in _soilGeometry.ToArray()) {
        var cell = pair.Key; var old = pair.Value;
        int lo = CellLo(cell.x, cell.y), hi = CellHi(cell.x, cell.y);
        bool same = old.Length == 2 * (hi - lo);
        for (int i = lo; same && i < hi; i++) same = old[2 * (i - lo)] == _floor[_sorted[i]] && old[2 * (i - lo) + 1] == _ceiling[_sorted[i]];
        if (same) continue;
        changed.Add(cell);
        int oldCount = old.Length / 2;
        var oldSoil = new float[oldCount]; var moved = new bool[oldCount];
        for (int o = 0; o < oldCount; o++) {
          var key = new Vector3Int(cell.x, cell.y, old[2 * o]);
          oldSoil[o] = Get(soil, key);
          soil.Remove(key);
        }
        var next = new Dictionary<int, float>();
        for (int i = lo; i < hi; i++) {
          int floor = _floor[_sorted[i]];
          for (int o = 0; o < oldCount; o++) if (old[2 * o] == floor) { next[floor] = oldSoil[o]; moved[o] = true; }
        }
        for (int i = lo; i < hi; i++) {
          int floor = _floor[_sorted[i]];
          bool sameFloor = false;
          for (int o = 0; o < oldCount; o++) sameFloor |= old[2 * o] == floor;
          int raised = -1;
          if (!sameFloor) for (int o = 0; o < oldCount && raised < 0; o++) if (floor - 1 >= old[2 * o] && floor - 1 < old[2 * o + 1]) raised = o;
          if (raised < 0 || moved[raised]) continue;
          next[floor] = oldSoil[raised];
          moved[raised] = true;
        }
        foreach (var moving in next) if (moving.Value > 0f) soil[new Vector3Int(cell.x, cell.y, moving.Key)] = moving.Value;
        _soilGeometry.Remove(cell);
      }
    }

    // CopyRow (evaporation), Reconcile (geometry) and CreditIntakes (closed-cell additions) deposit lost radioactive
    // volume into the soil, x SoilPerDepositedVolume. Native removals are credited to the sludge intake at their cell.
    // Discharge off the map, pressure losses, source withdrawals and other mods' extractions leave nothing behind, as
    // in the one-fluid simulation. Returns the number of deposits and credits.
    private int Deposit(IReadOnlyList<FluidLoss> losses, FluidHandle radioactive, Dictionary<Vector3Int, float> soil) {
      int count = 0;
      var geometryLost = new Dictionary<Vector2Int, double>();
      Dictionary<Vector3Int, float> credits = null;
      foreach (var loss in losses) {
        double volume = loss.GetVolume(radioactive);
        if (!(volume > 0)) continue;
        switch (loss.Kind) {
          case FluidLossKind.Evaporation: {
            int c = ColumnWithFloor(loss.X, loss.Y, loss.Z);
            if (c < 0) throw new InvalidOperationException("Evaporation reported at " + loss.X + ", " + loss.Y + ", " + loss.Z + " without that column");
            DepositInto(soil, Key(c), (float)volume); count++;
            break;
          }
          case FluidLossKind.DroppedAddition: {
            int above = LowestAbove(loss.X, loss.Y, loss.Z);
            if (above < 0) throw new InvalidOperationException("Radioactive water at closed cell (" + loss.X + ", " + loss.Y + ", " + loss.Z + ") has no fluid column above it");
            DepositInto(soil, Key(above), (float)volume); count++;
            break;
          }
          case FluidLossKind.Geometry: {
            var cell = new Vector2Int(loss.X, loss.Y);
            geometryLost[cell] = (geometryLost.TryGetValue(cell, out double sum) ? sum : 0) + volume;
            break;
          }
          case FluidLossKind.NativeRemoval: {
            credits ??= new Dictionary<Vector3Int, float>();
            var cell = new Vector3Int(loss.X, loss.Y, loss.Z);
            credits[cell] = (credits.TryGetValue(cell, out float sum) ? sum : 0f) + (float)volume; count++;
            break;
          }
        }
      }
      // Reconcile deposits the radioactive volume a geometry change deleted into the lowest open column of the cell.
      foreach (var pair in geometryLost) {
        if (!(pair.Value > RadiationTuning.MinWaterRadiation)) continue;
        int lo = CellLo(pair.Key.x, pair.Key.y);
        if (lo == CellHi(pair.Key.x, pair.Key.y)) continue;
        DepositInto(soil, Key(_sorted[lo]), (float)pair.Value); count++;
      }
      if (credits != null) lock (_gate) foreach (var pair in credits) _credits[pair.Key] = (_credits.TryGetValue(pair.Key, out float sum) ? sum : 0f) + pair.Value;
      return count;
    }

    // RadiationSimulation.Deposit.
    private static void DepositInto(Dictionary<Vector3Int, float> soil, Vector3Int key, float radioactiveVolume) {
      float value = Get(soil, key) + radioactiveVolume * RadiationTuning.SoilPerDepositedVolume;
      soil[key] = value > 1f ? 1f : value;
    }

    private Dictionary<Vector3Int, float> ApplyWaterRules(IFluidColumnEditor columns, FluidHandle radioactive, FluidHandle water,
        Dictionary<Vector3Int, float> soil, IReadOnlyDictionary<Vector3Int, float> previousShares) {
      foreach (var pair in soil) {
        int c = ColumnWithFloor(pair.Key.x, pair.Key.y, pair.Key.z);
        if (c < 0) throw new InvalidOperationException("Soil radiation at " + pair.Key + " lies under no column");
        _columnSoil[c] = pair.Value;
      }
      float hours = _hoursPerTick;
      float decay = RadiationTuning.DecayPerHour(RadiationTuning.RadiationHalfLifeDays) * hours;
      float rise = RadiationTuning.SoilRiseFromWaterPerHour * hours, wash = _washoutPerHour * hours;
      var shares = new Dictionary<Vector3Int, float>();
      for (int c = 0; c < _columns; c++) {
        double vr = _vr[c], total = _total[c];
        float s = _columnSoil[c];
        if (!(vr > 0) && !(s > 0f)) continue;
        var key = Key(c);
        float r = total > 0 ? (float)(vr / total) : 0f;
        // RunInteraction: decay of the radioactive share.
        if (r > 0f) {
          r -= r * decay;
          if (r < RadiationTuning.MinWaterRadiation) r = 0f;
        }
        // RadiationSoil.Exchange: ground under standing water.
        double vw = 0;
        if (total > 0 && (s > 0f || r > 0f)) {
          vw = columns.GetVolume(c, water);
          float b = (float)((total - vw - vr) / total), d = (float)total;
          float delta = 0f, share = r;
          bool exchanged = false;
          if (RadiationTuning.Detected(r) == 0f) {
            if (s > 0f) { delta = RadiationSoilFormulas.Rinse(s, r, b, d, wash, out share); exchanged = true; }
          } else {
            delta = RadiationSoilFormulas.SoilWaterExchange(s, r, b, d, rise, wash);
            if (delta != 0f) {
              share = r - delta * RadiationSoilFormulas.VolumePerSoil / d;
              // Float rounding only; anything larger is a broken exchange.
              if (share < 0f) {
                if (share < -RadiationTuning.ShareTolerance) throw new InvalidOperationException("Radiation soil: exchange left a negative radioactive share " + share + " at " + key);
                share = 0f;
              }
              exchanged = true;
            }
          }
          if (exchanged) {
            if (b + share > 1f + RadiationTuning.ShareTolerance) throw new InvalidOperationException("Radiation soil: the soil washout left b + r = " + (b + share) + " at " + key);
            s += delta;
            r = share;
            if (s > 0f) soil[key] = s; else soil.Remove(key);
          }
        }
        // Rescan: the cutoff for a share below DetectionLimit that did not grow since the last pass.
        if (r > 0f && !(total > 0)) r = 0f;
        else if (r > 0f && r < RadiationTuning.DetectionLimit && !(r > (previousShares.TryGetValue(key, out float before) ? before : 0f))) r = 0f;
        if (r > 0f) shares[key] = r;
        Convert(columns, c, radioactive, water, vr, r == 0f ? 0 : r * total, vw, total, key);
      }
      return shares;
    }

    // The share change as volume: radioactive water becomes fresh water (decay, uptake, cutoff) or fresh water becomes
    // radioactive (rinsing), so the column's physical volume and its badwater never change.
    private static void Convert(IFluidColumnEditor columns, int c, FluidHandle radioactive, FluidHandle water, double vr, double target, double vw, double total, Vector3Int key) {
      double change = target - vr;
      if (change < 0) { columns.Convert(c, radioactive, water, Math.Min(-change, vr)); return; }
      if (!(change > 0)) return;
      if (vw <= 0) vw = columns.GetVolume(c, water);
      // The float shares may exceed the fresh water by ShareTolerance of the column, as RadiationMixing.RequireShares
      // lets b + r exceed 1 by it; volume cannot, so the rinse takes the water there is. More is a broken rinse.
      if (change > vw) {
        if (change > vw + RadiationTuning.ShareTolerance * total) throw new InvalidOperationException("Radiation soil: rinsing at " + key + " needs " + change + " fresh water, the column holds " + vw);
        change = vw;
      }
      if (change > 0) columns.Convert(c, water, radioactive, change);
    }

    // RadiationSimulation.HourlySoilPass: soil spread to the neighbouring column whose floor is within one level
    // (NeighborSlot), then decay, clamped to [MinSoilRadiation, 1]. Neighbours in native order: y - 1, x - 1, y + 1, x + 1.
    private void HourlySoilPass(Dictionary<Vector3Int, float> soil, float hours) {
      float spread = RadiationTuning.SoilSpreadPerHour * hours;
      float decay = RadiationTuning.DecayPerHour(RadiationTuning.SoilHalfLifeDays) * hours;
      // Every column of a soil cell or a neighbouring cell; the others stay 0 (no soil within reach).
      var cells = new HashSet<Vector2Int>();
      foreach (var key in soil.Keys) {
        cells.Add(new Vector2Int(key.x, key.y));
        foreach (var (dx, dy) in Neighbours) if (InMap(key.x + dx, key.y + dy)) cells.Add(new Vector2Int(key.x + dx, key.y + dy));
      }
      var next = new List<(Vector3Int Key, float Value)>();
      foreach (var cell in cells) {
        for (int i = CellLo(cell.x, cell.y); i < CellHi(cell.x, cell.y); i++) {
          int c = _sorted[i];
          var key = Key(c);
          float value = Get(soil, key), exchange = 0f;
          foreach (var (dx, dy) in Neighbours) {
            if (!InMap(cell.x + dx, cell.y + dy)) continue;
            int neighbor = NeighborSlot(cell.x + dx, cell.y + dy, _floor[c]);
            if (neighbor >= 0) exchange += Get(soil, Key(neighbor)) - value;
          }
          float result = value + spread * exchange;
          result -= result * decay;
          next.Add((key, result < RadiationTuning.MinSoilRadiation ? 0f : result > 1f ? 1f : result));
        }
      }
      foreach (var (key, value) in next) { if (value > 0f) soil[key] = value; else soil.Remove(key); }
    }

    private static readonly (int Dx, int Dy)[] Neighbours = { (0, -1), (-1, 0), (0, 1), (1, 0) };

    private int NeighborSlot(int x, int y, int floor) {
      int best = -1, bestDiff = 2;
      for (int i = CellLo(x, y); i < CellHi(x, y); i++) {
        int c = _sorted[i];
        int diff = Math.Abs(_floor[c] - floor);
        if (diff < bestDiff && _ceiling[c] > _floor[c]) { best = c; bestDiff = diff; }
      }
      return best;
    }

    private void TrackSoilGeometry(Dictionary<Vector3Int, float> soil) {
      var holding = new HashSet<Vector2Int>();
      foreach (var key in soil.Keys) holding.Add(new Vector2Int(key.x, key.y));
      foreach (var cell in _soilGeometry.Keys.ToArray()) if (!holding.Contains(cell)) _soilGeometry.Remove(cell);
      foreach (var cell in holding) {
        if (_soilGeometry.ContainsKey(cell)) continue;
        int lo = CellLo(cell.x, cell.y), hi = CellHi(cell.x, cell.y);
        var geometry = new int[2 * (hi - lo)];
        for (int i = lo; i < hi; i++) { geometry[2 * (i - lo)] = _floor[_sorted[i]]; geometry[2 * (i - lo) + 1] = _ceiling[_sorted[i]]; }
        _soilGeometry.Add(cell, geometry);
      }
    }

    private bool InMap(int x, int y) => x >= 0 && y >= 0 && x < _width && y < _height;

    private void RequireInMap(int x, int y) {
      if (!InMap(x, y)) throw new ArgumentOutOfRangeException(nameof(x), "Cell (" + x + ", " + y + ") lies outside the " + _width + "x" + _height + " map");
    }
  }
}
