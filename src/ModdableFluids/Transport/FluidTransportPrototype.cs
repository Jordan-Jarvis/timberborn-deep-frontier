using System;
using System.Collections.Generic;

namespace ModdableFluids.Transport.Prototype {
  /// <summary>
  /// Experimental donor-volume transport of every component together. No Unity, Harmony,
  /// registration, or native state mutation. Input transfers must come from the same snapshot.
  /// </summary>
  public static class FluidTransportPrototype {
    /// <summary>
    /// Transfer from the old snapshot, then evaporate from each resulting mixture.
    /// Evaporation is a requested physical sink, limited by water actually present after flow.
    /// Invalid or overdrawn transfer batches fail before any state is produced.
    /// </summary>
    public static FluidStepResult Advect(FluidVolumes[] columns, FluidTransfer[] transfers, double[] requestedEvaporation) {
      int components = ValidateColumns(columns);
      if (transfers == null) throw new ArgumentNullException(nameof(transfers));
      if (requestedEvaporation == null || requestedEvaporation.Length != columns.Length)
        throw new ArgumentException("One evaporation request is required per column", nameof(requestedEvaporation));
      var outgoing = new double[columns.Length];
      foreach (var transfer in transfers) {
        RequireIndex(transfer.Source, columns.Length);
        if (transfer.Destination != -1) RequireIndex(transfer.Destination, columns.Length);
        if (transfer.Source == transfer.Destination) throw new ArgumentException("Self-transfer is not a flow edge");
        FluidVolumes.RequireQuantity(transfer.Volume, "transfer volume");
        outgoing[transfer.Source] += transfer.Volume;
      }
      var next = new double[columns.Length][];
      for (int i = 0; i < columns.Length; i++) {
        FluidVolumes.RequireQuantity(requestedEvaporation[i], "evaporation " + i);
        FluidVolumes.RequireQuantity(outgoing[i], "outgoing volume " + i);
        double available = columns[i].TotalVolume;
        if (outgoing[i] > available)
          throw new InvalidOperationException("Transfer batch overdraws column " + i + ": requested " + outgoing[i].ToString("R") + ", available " + available.ToString("R"));
        next[i] = new double[components];
        double retainedFraction = available > 0 ? (available - outgoing[i]) / available : 0;
        // Retain directly: subtracting several nearly equal moved component amounts
        // can produce a negative remainder when a column almost drains.
        for (int c = 0; c < components; c++) next[i][c] = columns[i].GetVolume(c) * retainedFraction;
      }
      var discharged = new double[components];
      foreach (var transfer in transfers) {
        var source = columns[transfer.Source];
        double fraction = source.TotalVolume > 0 ? transfer.Volume / source.TotalVolume : 0;
        double[] destination = transfer.Destination == -1 ? discharged : next[transfer.Destination];
        for (int c = 0; c < components; c++) destination[c] += source.GetVolume(c) * fraction;
      }
      var result = new FluidVolumes[columns.Length];
      var evaporated = new FluidVolumes[columns.Length];
      for (int i = 0; i < columns.Length; i++) {
        var removal = RemoveMixed(new FluidVolumes(next[i]), requestedEvaporation[i]);
        result[i] = removal.Remaining;
        evaporated[i] = removal.Removed;
      }
      return new FluidStepResult(result, evaporated, new FluidVolumes(discharged));
    }

    /// <summary>
    /// Symmetric exchanges calculated once per eligible pair from the same snapshot.
    /// Fraction = diffusion rate * timestep, in [0,1]. Pair degree budgets ensure
    /// all exports fit each donor without repairing component shares afterwards.
    /// </summary>
    public static FluidStepResult Diffuse(FluidVolumes[] columns, FluidDiffusionLink[] links, double fraction) {
      ValidateColumns(columns);
      FluidVolumes.RequireQuantity(fraction, nameof(fraction));
      if (fraction > 1) throw new ArgumentOutOfRangeException(nameof(fraction), "Split a diffusion step whose rate * timestep exceeds one");
      if (links == null) throw new ArgumentNullException(nameof(links));
      var degrees = new int[columns.Length];
      var pairs = new HashSet<long>();
      foreach (var link in links) {
        RequireIndex(link.First, columns.Length); RequireIndex(link.Second, columns.Length);
        if (link.First == link.Second) throw new ArgumentException("Self-diffusion is not a pair");
        int first = Math.Min(link.First, link.Second), second = Math.Max(link.First, link.Second);
        if (!pairs.Add(((long)first << 32) | (uint)second)) throw new ArgumentException("Duplicate diffusion pair");
        degrees[link.First]++; degrees[link.Second]++;
      }
      var transfers = new FluidTransfer[links.Length * 2];
      for (int i = 0; i < links.Length; i++) {
        var link = links[i];
        double a = columns[link.First].TotalVolume, b = columns[link.Second].TotalVolume;
        double combined = a + b;
        FluidVolumes.RequireQuantity(combined, "diffusion pair volume");
        // a*b/(a+b) written this way avoids overflowing the product.
        double exchange = a > 0 && b > 0
          ? (a / combined) * b * (fraction / Math.Max(degrees[link.First], degrees[link.Second])) : 0;
        transfers[2 * i] = new FluidTransfer(link.First, link.Second, exchange);
        transfers[2 * i + 1] = new FluidTransfer(link.Second, link.First, exchange);
      }
      return Advect(columns, transfers, new double[columns.Length]);
    }

    public static FluidVolumes Add(FluidVolumes column, FluidVolumes addition) {
      if (column == null || addition == null) throw new ArgumentNullException("mixture");
      if (column.ComponentCount != addition.ComponentCount) throw new ArgumentException("Component layouts differ");
      var result = column.CopyVolumes();
      for (int c = 0; c < result.Length; c++) result[c] += addition.GetVolume(c);
      return new FluidVolumes(result);
    }

    public static FluidRemovalResult RemoveMixed(FluidVolumes column, double requested) {
      if (column == null) throw new ArgumentNullException(nameof(column));
      FluidVolumes.RequireQuantity(requested, nameof(requested));
      double available = column.TotalVolume;
      double taken = Math.Min(requested, available);
      double retainedFraction = available > 0 ? (available - taken) / available : 0;
      var remaining = new double[column.ComponentCount];
      var removed = new double[column.ComponentCount];
      for (int c = 0; c < remaining.Length; c++) {
        remaining[c] = column.GetVolume(c) * retainedFraction;
        removed[c] = column.GetVolume(c) - remaining[c];
      }
      return new FluidRemovalResult(new FluidVolumes(remaining), new FluidVolumes(removed));
    }

    /// <summary>Retains at most the explicit physical capacity, without subtracting near-equal large volumes.</summary>
    public static FluidRemovalResult LimitCapacity(FluidVolumes column, double capacity) {
      if (column == null) throw new ArgumentNullException(nameof(column));
      FluidVolumes.RequireQuantity(capacity, nameof(capacity));
      double retained = Math.Min(capacity, column.TotalVolume);
      double fraction = column.TotalVolume > 0 ? retained / column.TotalVolume : 0;
      var remaining = new double[column.ComponentCount];
      var removed = new double[column.ComponentCount];
      for (int c = 0; c < remaining.Length; c++) {
        remaining[c] = column.GetVolume(c) * fraction;
        removed[c] = column.GetVolume(c) - remaining[c];
      }
      return new FluidRemovalResult(new FluidVolumes(remaining), new FluidVolumes(removed));
    }

    /// <summary>
    /// A negative native source always withdraws total volume. Its badwater share
    /// selects the preferred cohorts; an exhausted cohort cannot prevent drainage.
    /// Every custom non-bad component retains its ratio within that cohort.
    /// </summary>
    public static FluidRemovalResult RemoveSource(FluidVolumes column, int badwaterComponent, double requested, double badShare) {
      if (column == null) throw new ArgumentNullException(nameof(column));
      RequireIndex(badwaterComponent, column.ComponentCount);
      FluidVolumes.RequireQuantity(requested, nameof(requested));
      FluidVolumes.RequireQuantity(badShare, nameof(badShare));
      if (badShare > 1) throw new ArgumentOutOfRangeException(nameof(badShare));
      if (requested >= column.TotalVolume) return RemoveMixed(column, column.TotalVolume);
      double bad = column.GetVolume(badwaterComponent), nonBad = 0;
      for (int c = 0; c < column.ComponentCount; c++) if (c != badwaterComponent) nonBad += column.GetVolume(c);
      double badRequest = requested * badShare, nonBadRequest = requested - badRequest;
      // Budget the accepted withdrawal before removing anything. This is the
      // physical-volume equivalent of native source contamination's cohort limits.
      if (badRequest > bad) { badRequest = bad; nonBadRequest = requested - bad; }
      else if (nonBadRequest > nonBad) { nonBadRequest = nonBad; badRequest = requested - nonBad; }
      return RemoveNative(column, badwaterComponent, nonBadRequest, badRequest);
    }

    /// <summary>
    /// Replay native clean/non-bad and contaminated removal requests separately.
    /// All extra fluids occupy the non-bad cohort, matching the existing native add path.
    /// </summary>
    public static FluidRemovalResult RemoveNative(FluidVolumes column, int badwaterComponent, double requestedNonBad, double requestedBad) {
      if (column == null) throw new ArgumentNullException(nameof(column));
      RequireIndex(badwaterComponent, column.ComponentCount);
      FluidVolumes.RequireQuantity(requestedNonBad, nameof(requestedNonBad));
      FluidVolumes.RequireQuantity(requestedBad, nameof(requestedBad));
      double bad = column.GetVolume(badwaterComponent), nonBad = 0;
      for (int c = 0; c < column.ComponentCount; c++) if (c != badwaterComponent) nonBad += column.GetVolume(c);
      double retainedFraction = nonBad > 0 ? (nonBad - Math.Min(requestedNonBad, nonBad)) / nonBad : 0;
      var remaining = new double[column.ComponentCount];
      var removed = new double[column.ComponentCount];
      for (int c = 0; c < remaining.Length; c++) {
        remaining[c] = c == badwaterComponent ? bad - Math.Min(requestedBad, bad) : column.GetVolume(c) * retainedFraction;
        removed[c] = column.GetVolume(c) - remaining[c];
      }
      return new FluidRemovalResult(new FluidVolumes(remaining), new FluidVolumes(removed));
    }

    private static int ValidateColumns(FluidVolumes[] columns) {
      if (columns == null || columns.Length == 0) throw new ArgumentException("At least one column is required", nameof(columns));
      if (columns[0] == null) throw new ArgumentException("Null column");
      int components = columns[0].ComponentCount;
      foreach (var column in columns)
        if (column == null || column.ComponentCount != components) throw new ArgumentException("All columns need the same component layout");
      return components;
    }

    private static void RequireIndex(int index, int count) {
      if (index < 0 || index >= count) throw new ArgumentOutOfRangeException(nameof(index), index, "Index outside the supplied snapshot");
    }
  }
}
