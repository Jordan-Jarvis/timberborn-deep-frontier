using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;

namespace ModdableFluids {
  /// <summary>Saved state of one stateful provider.</summary>
  public sealed class FluidProviderState {
    public string ProviderId { get; }
    public string OwnerModId { get; }
    public int SchemaVersion { get; }
    public string Data { get; }
    public FluidProviderState(string providerId, string ownerModId, int schemaVersion, string data) {
      FluidIds.RequireOwned(providerId, ownerModId, "saved provider ID");
      if (schemaVersion < 1) throw new ArgumentOutOfRangeException(nameof(schemaVersion), schemaVersion, "Provider " + providerId + " state schemas start at 1");
      ProviderId = providerId; OwnerModId = ownerModId; SchemaVersion = schemaVersion;
      Data = data ?? throw new ArgumentNullException(nameof(data), "Provider " + providerId + " saved null state");
    }
  }

  /// <summary>A save that cannot load as written. Problems name the mods and IDs involved.</summary>
  public sealed class FluidSaveException : InvalidOperationException {
    public IReadOnlyList<string> Problems { get; }
    public FluidSaveException(IList<string> problems)
      : base("This save's fluid state cannot be loaded:\n- " + string.Join("\n- ", problems)) {
      Problems = new ReadOnlyCollection<string>(new List<string>(problems));
    }
  }

  /// <summary>
  /// The world fluid save schema, made only of ints and strings so it maps directly onto native
  /// <c>ListKey&lt;int&gt;</c>/<c>ListKey&lt;string&gt;</c> entries. Fluids are saved by canonical ID with their
  /// owning mod; runtime handles are never saved. Columns are identified by unpadded map cell and
  /// open interval (floor, ceiling) with their physical capacity, so a reload can project them onto
  /// changed native geometry. Component volumes are positive doubles stored as exact IEEE-754 bit
  /// patterns (16 uppercase hex digits) so a round trip is bit-identical on .NET and Mono.
  /// The constructor validates the whole document and rejects it with every problem listed.
  /// </summary>
  public sealed class FluidSaveDocument {
    public const int CurrentSchemaVersion = 1;
    public int SchemaVersion { get; }
    public string ApiVersion { get; }
    public string RegistryFingerprint { get; }
    public IReadOnlyList<string> FluidIds { get; }
    public IReadOnlyList<string> FluidOwners { get; }
    public IReadOnlyList<int> ColumnX { get; }
    public IReadOnlyList<int> ColumnY { get; }
    public IReadOnlyList<int> ColumnFloor { get; }
    public IReadOnlyList<int> ColumnCeiling { get; }
    public IReadOnlyList<string> ColumnCapacity { get; }
    public IReadOnlyList<int> EntryColumn { get; }
    public IReadOnlyList<int> EntryFluid { get; }
    public IReadOnlyList<string> EntryVolume { get; }
    public IReadOnlyList<string> ProviderIds { get; }
    public IReadOnlyList<string> ProviderOwners { get; }
    public IReadOnlyList<int> ProviderSchemas { get; }
    public IReadOnlyList<string> ProviderData { get; }

    public FluidSaveDocument(int schemaVersion, string apiVersion, string registryFingerprint,
        IList<string> fluidIds, IList<string> fluidOwners,
        IList<int> columnX, IList<int> columnY, IList<int> columnFloor, IList<int> columnCeiling, IList<string> columnCapacity,
        IList<int> entryColumn, IList<int> entryFluid, IList<string> entryVolume,
        IList<string> providerIds, IList<string> providerOwners, IList<int> providerSchemas, IList<string> providerData) {
      SchemaVersion = schemaVersion; ApiVersion = apiVersion; RegistryFingerprint = registryFingerprint;
      FluidIds = Copy(fluidIds, "FluidIds"); FluidOwners = Copy(fluidOwners, "FluidOwners");
      ColumnX = Copy(columnX, "ColumnX"); ColumnY = Copy(columnY, "ColumnY"); ColumnFloor = Copy(columnFloor, "ColumnFloor");
      ColumnCeiling = Copy(columnCeiling, "ColumnCeiling"); ColumnCapacity = Copy(columnCapacity, "ColumnCapacity");
      EntryColumn = Copy(entryColumn, "EntryColumn"); EntryFluid = Copy(entryFluid, "EntryFluid"); EntryVolume = Copy(entryVolume, "EntryVolume");
      ProviderIds = Copy(providerIds, "ProviderIds"); ProviderOwners = Copy(providerOwners, "ProviderOwners");
      ProviderSchemas = Copy(providerSchemas, "ProviderSchemas"); ProviderData = Copy(providerData, "ProviderData");
      var problems = Validate();
      if (problems.Count > 0) throw new FluidSaveException(problems);
    }

    public int ColumnCount => ColumnX.Count;
    public double GetCapacity(int column) => DecodeQuantity(ColumnCapacity[column], "capacity");
    public double GetVolume(int entry) => DecodeQuantity(EntryVolume[entry], "volume");

    public IReadOnlyList<FluidProviderState> GetProviderStates() =>
      Enumerable.Range(0, ProviderIds.Count).Select(i => new FluidProviderState(ProviderIds[i], ProviderOwners[i], ProviderSchemas[i], ProviderData[i])).ToArray();

    /// <summary>Exact IEEE-754 bits of a finite nonnegative quantity.</summary>
    public static string EncodeQuantity(double value) {
      if (double.IsNaN(value) || double.IsInfinity(value) || value < 0) throw new ArgumentOutOfRangeException(nameof(value), value, "Saved quantities are finite and nonnegative");
      return BitConverter.DoubleToInt64Bits(value).ToString("X16", CultureInfo.InvariantCulture);
    }

    public static double DecodeQuantity(string text, string role) {
      if (text == null || text.Length != 16 || text.Any(c => !((c >= '0' && c <= '9') || (c >= 'A' && c <= 'F'))))
        throw new FormatException("Saved " + role + " '" + text + "' is not 16 uppercase hexadecimal digits");
      double value = BitConverter.Int64BitsToDouble(long.Parse(text, NumberStyles.AllowHexSpecifier, CultureInfo.InvariantCulture));
      if (double.IsNaN(value) || double.IsInfinity(value) || value < 0) throw new FormatException("Saved " + role + " " + text + " is not a finite nonnegative quantity");
      return value;
    }

    private static ReadOnlyCollection<T> Copy<T>(IList<T> values, string name) =>
      new ReadOnlyCollection<T>((values ?? throw new ArgumentNullException(name, "Fluid save list " + name + " is missing")).ToArray());

    private List<string> Validate() {
      var problems = new List<string>();
      if (SchemaVersion > CurrentSchemaVersion) {
        problems.Add("Fluid save schema " + SchemaVersion + " was written by a newer Moddable Fluids (" + ApiVersion + "); this runtime reads schema " + CurrentSchemaVersion + ". Update Moddable Fluids.");
        return problems;
      }
      if (SchemaVersion < 1) { problems.Add("Fluid save schema " + SchemaVersion + " is invalid"); return problems; }
      if (!ModdableFluidsHost.TryParseVersion(ApiVersion, out _, out _, out _)) problems.Add("Saved API version '" + ApiVersion + "' is not major.minor.patch");
      if (RegistryFingerprint == null || RegistryFingerprint.Length != 64) problems.Add("Saved registry fingerprint is not a SHA-256 hex string");
      if (FluidOwners.Count != FluidIds.Count) problems.Add("Fluid table lengths differ: " + FluidIds.Count + " IDs, " + FluidOwners.Count + " owners");
      if (new[] { ColumnY.Count, ColumnFloor.Count, ColumnCeiling.Count, ColumnCapacity.Count }.Any(n => n != ColumnX.Count)) problems.Add("Column list lengths differ");
      if (EntryFluid.Count != EntryColumn.Count || EntryVolume.Count != EntryColumn.Count) problems.Add("Component entry list lengths differ");
      if (new[] { ProviderOwners.Count, ProviderSchemas.Count, ProviderData.Count }.Any(n => n != ProviderIds.Count)) problems.Add("Provider state list lengths differ");
      if (problems.Count > 0) return problems;
      var ids = new HashSet<string>(StringComparer.Ordinal);
      for (int i = 0; i < FluidIds.Count; i++) {
        string id = FluidIds[i];
        if (!ModdableFluids.FluidIds.TrySplit(id, out string owner, out _)) { problems.Add("Saved fluid ID '" + id + "' is invalid"); continue; }
        if (owner != FluidOwners[i]) problems.Add("Saved fluid " + id + " lists owner " + FluidOwners[i]);
        if (!ids.Add(id)) problems.Add("Saved fluid " + id + " appears twice");
      }
      var capacities = new double[ColumnX.Count];
      var cells = new Dictionary<long, List<int>>();
      for (int c = 0; c < ColumnX.Count; c++) {
        if (ColumnX[c] < 0 || ColumnY[c] < 0 || ColumnFloor[c] < 0 || ColumnCeiling[c] <= ColumnFloor[c] || ColumnCeiling[c] > 255) {
          problems.Add("Saved column " + c + " has invalid geometry (" + ColumnX[c] + ", " + ColumnY[c] + ", " + ColumnFloor[c] + "-" + ColumnCeiling[c] + ")");
          continue;
        }
        try {
          capacities[c] = GetCapacity(c);
          if (capacities[c] < ColumnCeiling[c] - ColumnFloor[c]) problems.Add("Saved column " + c + " capacity is smaller than its open interval");
        } catch (FormatException e) { problems.Add("Saved column " + c + ": " + e.Message); }
        long cell = ((long)ColumnX[c] << 32) | (uint)ColumnY[c];
        if (!cells.TryGetValue(cell, out var others)) cells.Add(cell, others = new List<int>());
        foreach (int other in others)
          if (ColumnFloor[c] < ColumnCeiling[other] && ColumnFloor[other] < ColumnCeiling[c])
            problems.Add("Saved columns " + other + " and " + c + " overlap at (" + ColumnX[c] + ", " + ColumnY[c] + ")");
        others.Add(c);
      }
      var totals = new double[ColumnX.Count];
      var pairs = new HashSet<long>();
      for (int e = 0; e < EntryColumn.Count; e++) {
        int column = EntryColumn[e], fluid = EntryFluid[e];
        if (column < 0 || column >= ColumnX.Count || fluid < 0 || fluid >= FluidIds.Count) { problems.Add("Component entry " + e + " references a missing column or fluid"); continue; }
        if (!pairs.Add(((long)column << 32) | (uint)fluid)) problems.Add("Component entry " + e + " repeats " + FluidIds[fluid] + " in column " + column);
        try {
          double volume = GetVolume(e);
          if (volume <= 0) problems.Add("Component entry " + e + " stores a zero volume; only positive volumes are saved");
          totals[column] += volume;
        } catch (FormatException ex) { problems.Add("Component entry " + e + ": " + ex.Message); }
      }
      for (int c = 0; c < totals.Length; c++)
        if (capacities[c] > 0 && totals[c] - capacities[c] > 4 * FluidIds.Count * 2.2204460492503131e-16 * Math.Max(totals[c], capacities[c]))
          problems.Add("Saved column " + c + " holds " + totals[c].ToString("R", CultureInfo.InvariantCulture) + ", above its capacity " + capacities[c].ToString("R", CultureInfo.InvariantCulture));
      var providers = new HashSet<string>(StringComparer.Ordinal);
      for (int p = 0; p < ProviderIds.Count; p++) {
        try { new FluidProviderState(ProviderIds[p], ProviderOwners[p], ProviderSchemas[p], ProviderData[p]); }
        catch (ArgumentException e) { problems.Add("Saved provider state " + p + ": " + e.Message); }
        if (!providers.Add(ProviderIds[p] ?? "")) problems.Add("Saved provider " + ProviderIds[p] + " appears twice");
      }
      return problems;
    }

    /// <summary>
    /// Maps each saved fluid to its current component slot by canonical ID and owner. Every missing
    /// or moved fluid is reported together; unknown fluid is never converted to water.
    /// </summary>
    public int[] ResolveFluidSlots(FluidRegistry registry) {
      if (registry == null) throw new ArgumentNullException(nameof(registry));
      var slots = new int[FluidIds.Count];
      var missing = new List<string>();
      var problems = new List<string>();
      for (int i = 0; i < FluidIds.Count; i++) {
        if (!registry.TryGet(FluidIds[i], out var definition)) { missing.Add(FluidIds[i] + " (mod " + FluidOwners[i] + ")"); continue; }
        if (definition.OwnerModId != FluidOwners[i]) problems.Add("Fluid " + FluidIds[i] + " was saved from mod " + FluidOwners[i] + " but is now registered by " + definition.OwnerModId);
        slots[i] = registry.GetHandle(FluidIds[i]).Index;
      }
      if (missing.Count > 0)
        problems.Insert(0, "This save contains fluids that are not registered: " + string.Join(", ", missing)
          + ". Enable the mods that provide them; Moddable Fluids never replaces unknown fluid with water.");
      if (problems.Count > 0) throw new FluidSaveException(problems);
      return slots;
    }
  }
}
