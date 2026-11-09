using System;
using System.Collections.Generic;
using ModdableFluids.Transport.Prototype;

namespace ModdableFluids.Native.Prototype {
  /// <summary>
  /// Experimental native-stage coordinator. Hosts execute the actual native tasks at the
  /// documented callbacks. This class owns composition, source/change mixing and badwater
  /// publication; it does not attach patches or register a game singleton by itself.
  /// </summary>
  public sealed class NativeFluidTransportSession {
    private enum Stage { Ready, Hydraulics, Sources, Changes, Faulted }
    private Stage _stage;
    private NativeWaterArrayAdapter _backend;
    private FluidColumnGeometry[] _layout;
    private FluidVolumes[] _mixtures;
    private readonly Dictionary<int, int> _slots = new Dictionary<int, int>();
    private readonly int _components, _badwater;
    private int _substeps, _completed;
    public string Phase => _stage.ToString();
    public int ColumnCount => _layout.Length;
    public int ComponentCount => _components;
    public int BadwaterComponent => _badwater;
    public int CompletedTicks { get; private set; }
    public FluidVolumes Added { get; private set; }
    public FluidVolumes Removed { get; private set; }
    public FluidVolumes Evaporated { get; private set; }
    public FluidVolumes Discharged { get; private set; }
    public FluidVolumes PressureLoss { get; private set; }
    public FluidVolumes GeometryLoss { get; private set; }
    public double MaxRepresentationDifference { get; private set; }

    /// <summary>Explicit initialization from native fresh/bad water; no saved custom state is inferred.</summary>
    public NativeFluidTransportSession(NativeWaterArrayAdapter backend, int componentCount, int badwaterComponent) {
      if (backend == null) throw new ArgumentNullException(nameof(backend));
      if (componentCount < 2 || badwaterComponent <= 0 || badwaterComponent >= componentCount) throw new ArgumentException("Fresh water occupies slot zero; choose a distinct badwater slot");
      _backend = backend; _components = componentCount; _badwater = badwaterComponent;
      _layout = backend.CaptureGeometry(); _mixtures = new FluidVolumes[_layout.Length];
      for (int i = 0; i < _layout.Length; i++) {
        _slots.Add(_layout[i].NativeIndex, i);
        double volume = backend.PhysicalVolume(_layout[i].NativeIndex), bad = backend.BadwaterShare(_layout[i].NativeIndex);
        if (bad < 0 || bad > 1 || double.IsNaN(bad)) throw new InvalidOperationException("Invalid native badwater share");
        var values = new double[_components]; values[_badwater] = volume * bad; values[0] = volume - values[_badwater];
        _mixtures[i] = new FluidVolumes(values);
      }
      Added = Empty(); Removed = Empty(); Evaporated = Empty(); Discharged = Empty(); PressureLoss = Empty(); GeometryLoss = Empty();
    }
    private FluidVolumes Empty() => new FluidVolumes(new double[_components]);
    public FluidColumnGeometry GetGeometry(int slot) => _layout[slot];
    public FluidVolumes Sample(int nativeIndex) => _mixtures[Slot(nativeIndex)];
    public void SeedComposition(int nativeIndex, FluidVolumes mixture) {
      Require(Stage.Ready);
      int slot = Slot(nativeIndex); ValidateLayout(mixture);
      CheckRepresentation(_backend.PhysicalVolume(nativeIndex), mixture.TotalVolume, mixture.TotalVolume);
      if (mixture.TotalVolume - _layout[slot].Capacity > 4 * _components * 2.2204460492503131e-16 * Math.Max(mixture.TotalVolume, _layout[slot].Capacity))
        throw new ArgumentException("Seed exceeds column capacity");
      _mixtures[slot] = mixture;
      _backend.Publish(nativeIndex, mixture, _badwater, false);
    }
    public void BeginTick(int substepCount) {
      Require(Stage.Ready);
      if (substepCount < 1) throw new ArgumentOutOfRangeException(nameof(substepCount));
      RequireUnchangedGeometry(); _substeps = substepCount; _completed = 0; _stage = Stage.Hydraulics;
    }
    /// <summary>
    /// Order: native flow requests, shared donor budget, native depth update, joint
    /// advection/evaporation/capacity, native diffusion eligibility, joint diffusion,
    /// then publish the joint badwater share before any sources consume the result.
    /// The depth callback returns the evaporation requests used by that native task.
    /// </summary>
    public void RunSubstep(Action generateFlows, Func<double[]> updateDepths, Func<FluidDiffusionLink[]> diffusionLinks,
        double deltaTime, double diffusionFraction) {
      Require(Stage.Hydraulics);
      if (generateFlows == null || updateDepths == null || diffusionLinks == null) throw new ArgumentNullException("native task callbacks");
      try {
        RequireUnchangedGeometry();
        generateFlows();
        var transfers = _backend.BudgetFlowRequests(_layout, _mixtures, deltaTime);
        var evaporation = updateDepths();
        if (evaporation == null || evaporation.Length != _layout.Length) throw new ArgumentException("Depth callback must report one evaporation request per open column");
        RequireUnchangedGeometry();
        var step = _layout.Length > 0 ? FluidTransportPrototype.Advect(_mixtures, transfers, evaporation)
          : new FluidStepResult(new FluidVolumes[0], new FluidVolumes[0], Empty());
        var next = new FluidVolumes[_layout.Length];
        var scales = new double[_layout.Length];
        for (int i = 0; i < next.Length; i++) scales[i] = _mixtures[i].TotalVolume + evaporation[i];
        foreach (var transfer in transfers) {
          scales[transfer.Source] += transfer.Volume;
          if (transfer.Destination >= 0) scales[transfer.Destination] += transfer.Volume;
        }
        var evaporated = Empty(); var pressure = Empty();
        for (int i = 0; i < next.Length; i++) {
          var cap = Cap(i, step.GetColumn(i)); next[i] = cap.Remaining;
          evaporated = FluidTransportPrototype.Add(evaporated, step.GetEvaporated(i));
          pressure = FluidTransportPrototype.Add(pressure, cap.Removed);
          CheckRepresentation(_backend.PhysicalVolume(_layout[i].NativeIndex), next[i].TotalVolume, scales[i]);
        }
        // The host may run native concentration tasks to obtain the game's geometric
        // eligibility flags. Their independent concentration results are replaced here.
        var links = diffusionLinks();
        if (links == null || (next.Length == 0 && links.Length != 0)) throw new ArgumentException("Diffusion callback returned an invalid empty-domain layout");
        RequireUnchangedGeometry();
        var diffused = next.Length > 0 ? FluidTransportPrototype.Diffuse(next, links, diffusionFraction) : null;
        for (int i = 0; i < next.Length; i++) {
          next[i] = diffused.GetColumn(i);
          CheckRepresentation(_backend.PhysicalVolume(_layout[i].NativeIndex), next[i].TotalVolume, scales[i]);
          _backend.Publish(_layout[i].NativeIndex, next[i], _badwater, false);
        }
        _mixtures = next;
        Evaporated = FluidTransportPrototype.Add(Evaporated, evaporated);
        PressureLoss = FluidTransportPrototype.Add(PressureLoss, pressure);
        Discharged = FluidTransportPrototype.Add(Discharged, step.Discharged);
        _stage = Stage.Sources;
      } catch { _stage = Stage.Faulted; throw; }
    }
    public FluidVolumes AddSource(int nativeIndex, FluidVolumes addition) {
      Require(Stage.Sources); return AddPhysical(nativeIndex, addition, true);
    }
    public FluidRemovalResult RemoveSource(int nativeIndex, double requested, double badShare) {
      Require(Stage.Sources); int slot = Slot(nativeIndex);
      return RemovePhysical(nativeIndex, slot, FluidTransportPrototype.RemoveSource(_mixtures[slot], _badwater, requested, badShare));
    }
    public void FinishSubstep() {
      Require(Stage.Sources);
      _completed++;
      _stage = _completed == _substeps ? Stage.Changes : Stage.Hydraulics;
    }
    public FluidVolumes AddQueued(int nativeIndex, FluidVolumes addition) {
      Require(Stage.Changes); return AddPhysical(nativeIndex, addition, false);
    }
    private FluidVolumes AddPhysical(int nativeIndex, FluidVolumes addition, bool sourceAdmission) {
      ValidateLayout(addition); int slot = Slot(nativeIndex);
      try {
        double scale = _mixtures[slot].TotalVolume + addition.TotalVolume;
        FluidRemovalResult cap;
        FluidVolumes next;
        if (sourceAdmission) {
          // A pressure-blocked source cannot replace resident fluid. Mix only its
          // admitted volume; rejected emission remains in the pressure-loss ledger.
          double available = _mixtures[slot].TotalVolume < _layout[slot].Capacity
            ? _layout[slot].Capacity - _mixtures[slot].TotalVolume : 0;
          cap = FluidTransportPrototype.LimitCapacity(addition, available);
          next = FluidTransportPrototype.Add(_mixtures[slot], cap.Remaining);
        } else {
          cap = Cap(slot, FluidTransportPrototype.Add(_mixtures[slot], addition));
          next = cap.Remaining;
        }
        _backend.Publish(nativeIndex, next, _badwater, true);
        CheckRepresentation(_backend.PhysicalVolume(nativeIndex), next.TotalVolume, scale);
        _mixtures[slot] = next;
        Added = FluidTransportPrototype.Add(Added, addition);
        PressureLoss = FluidTransportPrototype.Add(PressureLoss, cap.Removed);
        return cap.Removed;
      } catch { _stage = Stage.Faulted; throw; }
    }
    public FluidRemovalResult RemoveQueued(int nativeIndex, double nonBadRequest, double badRequest) {
      Require(Stage.Changes); int slot = Slot(nativeIndex);
      var result = FluidTransportPrototype.RemoveNative(_mixtures[slot], _badwater, nonBadRequest, badRequest);
      return RemovePhysical(nativeIndex, slot, result);
    }
    private FluidRemovalResult RemovePhysical(int nativeIndex, int slot, FluidRemovalResult result) {
      try {
        _backend.Publish(nativeIndex, result.Remaining, _badwater, true);
        CheckRepresentation(_backend.PhysicalVolume(nativeIndex), result.Remaining.TotalVolume, _mixtures[slot].TotalVolume);
        _mixtures[slot] = result.Remaining;
        Removed = FluidTransportPrototype.Add(Removed, result.Removed);
        return result;
      } catch { _stage = Stage.Faulted; throw; }
    }
    public void EndTick() { Require(Stage.Changes); CompletedTicks++; _stage = Stage.Ready; }
    /// <summary>
    /// Converts <paramref name="volume"/> of one non-badwater component into another in layout slot <paramref name="slot"/>,
    /// at a completed tick. The column's physical volume and badwater are unchanged, so native water is not touched.
    /// </summary>
    public void ConvertComponent(int slot, int from, int to, double volume) {
      Require(Stage.Ready);
      if (slot < 0 || slot >= _layout.Length) throw new ArgumentOutOfRangeException(nameof(slot), slot, "No such column");
      if (from < 0 || from >= _components || to < 0 || to >= _components || from == to) throw new ArgumentException("A conversion needs two distinct components");
      if (from == _badwater || to == _badwater) throw new ArgumentException("Badwater is native contamination and cannot be converted");
      var values = _mixtures[slot].CopyVolumes();
      if (double.IsNaN(volume) || double.IsInfinity(volume) || volume <= 0 || volume > values[from])
        throw new ArgumentOutOfRangeException(nameof(volume), volume, "A conversion moves a positive volume the column holds (" + values[from].ToString("R") + ")");
      values[from] -= volume; values[to] += volume;
      _mixtures[slot] = new FluidVolumes(values);
    }
    public void AbortTick() { _stage = Stage.Faulted; }
    public FluidGeometryResult ReconcileGeometry(NativeWaterArrayAdapter updatedBackend) {
      Require(Stage.Ready);
      if (updatedBackend == null) throw new ArgumentNullException(nameof(updatedBackend));
      var next = updatedBackend.CaptureGeometry();
      var remapped = FluidGeometryTransport.Remap(_layout, _mixtures, next, _components);
      try {
        var mixtures = new FluidVolumes[next.Length];
        for (int i = 0; i < next.Length; i++) {
          mixtures[i] = remapped.GetColumn(i);
          updatedBackend.Publish(next[i].NativeIndex, mixtures[i], _badwater, true);
          CheckRepresentation(updatedBackend.PhysicalVolume(next[i].NativeIndex), mixtures[i].TotalVolume, mixtures[i].TotalVolume);
        }
        _backend = updatedBackend; _layout = next; _mixtures = mixtures;
        _slots.Clear(); for (int i = 0; i < next.Length; i++) _slots.Add(next[i].NativeIndex, i);
        GeometryLoss = FluidTransportPrototype.Add(GeometryLoss, remapped.GeometryLoss);
        PressureLoss = FluidTransportPrototype.Add(PressureLoss, remapped.PressureLoss);
        return remapped;
      } catch { _stage = Stage.Faulted; throw; }
    }
    private FluidRemovalResult Cap(int slot, FluidVolumes mixture) => FluidTransportPrototype.LimitCapacity(mixture, _layout[slot].Capacity);
    private void ValidateLayout(FluidVolumes mixture) {
      if (mixture == null || mixture.ComponentCount != _components) throw new ArgumentException("Component layouts differ");
    }
    private void CheckRepresentation(double native, double physical, double scale) {
      double difference = Math.Abs(native - physical);
      // Validate a float representation; never use its error as physical component volume.
      if (difference > 16 * 1.1920928955078125e-7 * scale + 1e-44)
        throw new InvalidOperationException("Native physical volume differs from the joint state: native " + native.ToString("R") + ", joint " + physical.ToString("R"));
      MaxRepresentationDifference = Math.Max(MaxRepresentationDifference, difference);
    }
    private int Slot(int nativeIndex) {
      if (_slots.TryGetValue(nativeIndex, out int slot)) return slot;
      throw new ArgumentOutOfRangeException(nameof(nativeIndex), nativeIndex, "No open native column");
    }
    private void Require(Stage stage) {
      if (_stage != stage) throw new InvalidOperationException("Expected fluid stage " + stage + ", actual " + _stage);
    }
    private void RequireUnchangedGeometry() {
      var geometry = _backend.CaptureGeometry();
      if (geometry.Length != _layout.Length) throw new InvalidOperationException("Reconcile native geometry before beginning a fluid tick");
      for (int i = 0; i < geometry.Length; i++) if (geometry[i].NativeIndex != _layout[i].NativeIndex || geometry[i].Floor != _layout[i].Floor || geometry[i].Ceiling != _layout[i].Ceiling)
        throw new InvalidOperationException("Reconcile native geometry before beginning a fluid tick");
    }
  }
}
