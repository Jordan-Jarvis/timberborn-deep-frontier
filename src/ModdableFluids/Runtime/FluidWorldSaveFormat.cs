using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Timberborn.Persistence;
using Timberborn.WorldPersistence;
using ModdableFluids;

namespace ModdableFluids.Runtime.Prototype {
  /// <summary>
  /// The game-side envelope that stores one <see cref="FluidSaveDocument"/> in the native singleton
  /// <c>ModdableFluids.World</c>, using only native int, bool and string keys. <c>NativeOnly</c> marks a
  /// save written before the first fluid tick of a world that had no fluid state: its components equal
  /// the native water and badwater, and only provider state is stored. A missing or unknown envelope
  /// version fails loading; nothing is defaulted.
  /// </summary>
  public static class FluidWorldSaveFormat {
    public static readonly SingletonKey Key = new SingletonKey("ModdableFluids.World");
    private const int CurrentEnvelope = 1;
    private static readonly PropertyKey<int> EnvelopeKey = new PropertyKey<int>("EnvelopeVersion");
    private static readonly PropertyKey<bool> NativeOnlyKey = new PropertyKey<bool>("NativeOnly");
    private static readonly PropertyKey<int> SchemaKey = new PropertyKey<int>("SchemaVersion");
    private static readonly PropertyKey<string> ApiKey = new PropertyKey<string>("ApiVersion");
    private static readonly PropertyKey<string> FingerprintKey = new PropertyKey<string>("RegistryFingerprint");
    private static readonly ListKey<string> FluidIdsKey = new ListKey<string>("FluidIds"), FluidOwnersKey = new ListKey<string>("FluidOwners"),
      CapacityKey = new ListKey<string>("ColumnCapacity"), VolumeKey = new ListKey<string>("EntryVolume"),
      ProviderIdsKey = new ListKey<string>("ProviderIds"), ProviderOwnersKey = new ListKey<string>("ProviderOwners"), ProviderDataKey = new ListKey<string>("ProviderData");
    private static readonly ListKey<int> XKey = new ListKey<int>("ColumnX"), YKey = new ListKey<int>("ColumnY"), FloorKey = new ListKey<int>("ColumnFloor"),
      CeilingKey = new ListKey<int>("ColumnCeiling"), EntryColumnKey = new ListKey<int>("EntryColumn"), EntryFluidKey = new ListKey<int>("EntryFluid"),
      ProviderSchemasKey = new ListKey<int>("ProviderSchemas");

    public sealed class Loaded {
      public FluidSaveDocument Document { get; internal set; }
      public IReadOnlyList<FluidProviderState> ProviderStates { get; internal set; }
      public bool NativeOnly => Document == null;
    }

    public static void Write(IObjectSaver saver, FluidSaveDocument document) {
      saver.Set(EnvelopeKey, CurrentEnvelope);
      saver.Set(NativeOnlyKey, false);
      saver.Set(SchemaKey, document.SchemaVersion);
      saver.Set(ApiKey, document.ApiVersion);
      saver.Set(FingerprintKey, document.RegistryFingerprint);
      saver.Set(FluidIdsKey, document.FluidIds.ToArray()); saver.Set(FluidOwnersKey, document.FluidOwners.ToArray());
      saver.Set(XKey, document.ColumnX.ToArray()); saver.Set(YKey, document.ColumnY.ToArray());
      saver.Set(FloorKey, document.ColumnFloor.ToArray()); saver.Set(CeilingKey, document.ColumnCeiling.ToArray());
      saver.Set(CapacityKey, document.ColumnCapacity.ToArray());
      saver.Set(EntryColumnKey, document.EntryColumn.ToArray()); saver.Set(EntryFluidKey, document.EntryFluid.ToArray());
      saver.Set(VolumeKey, document.EntryVolume.ToArray());
      WriteProviders(saver, document.GetProviderStates());
    }

    public static void WriteNativeOnly(IObjectSaver saver, IReadOnlyList<FluidProviderState> states) {
      saver.Set(EnvelopeKey, CurrentEnvelope);
      saver.Set(NativeOnlyKey, true);
      WriteProviders(saver, states);
    }

    private static void WriteProviders(IObjectSaver saver, IReadOnlyList<FluidProviderState> states) {
      saver.Set(ProviderIdsKey, states.Select(s => s.ProviderId).ToArray());
      saver.Set(ProviderOwnersKey, states.Select(s => s.OwnerModId).ToArray());
      saver.Set(ProviderSchemasKey, states.Select(s => s.SchemaVersion).ToArray());
      saver.Set(ProviderDataKey, states.Select(s => s.Data).ToArray());
    }

    public static Loaded Read(IObjectLoader loader) {
      if (!loader.Has(EnvelopeKey)) throw new FluidSaveException(new[] { "The ModdableFluids.World save entry has no EnvelopeVersion" });
      int envelope = loader.Get(EnvelopeKey);
      if (envelope != CurrentEnvelope)
        throw new FluidSaveException(new[] { "The ModdableFluids.World save envelope " + envelope + " is not supported; this runtime reads " + CurrentEnvelope });
      var ids = loader.Get(ProviderIdsKey); var owners = loader.Get(ProviderOwnersKey); var schemas = loader.Get(ProviderSchemasKey); var data = loader.Get(ProviderDataKey);
      if (owners.Count != ids.Count || schemas.Count != ids.Count || data.Count != ids.Count) throw new FluidSaveException(new[] { "Saved provider state list lengths differ" });
      var states = Enumerable.Range(0, ids.Count).Select(i => new FluidProviderState(ids[i], owners[i], schemas[i], data[i])).ToArray();
      if (loader.Get(NativeOnlyKey)) return new Loaded { ProviderStates = states };
      var document = new FluidSaveDocument(loader.Get(SchemaKey), loader.Get(ApiKey), loader.Get(FingerprintKey),
        loader.Get(FluidIdsKey), loader.Get(FluidOwnersKey), loader.Get(XKey), loader.Get(YKey), loader.Get(FloorKey), loader.Get(CeilingKey),
        loader.Get(CapacityKey), loader.Get(EntryColumnKey), loader.Get(EntryFluidKey), loader.Get(VolumeKey), ids, owners, schemas, data);
      return new Loaded { Document = document, ProviderStates = states };
    }

    /// <summary>The loaded component state with new provider state (a save before the first tick).</summary>
    public static FluidSaveDocument WithProviderStates(FluidSaveDocument d, IReadOnlyList<FluidProviderState> states) =>
      new FluidSaveDocument(d.SchemaVersion, d.ApiVersion, d.RegistryFingerprint, d.FluidIds.ToArray(), d.FluidOwners.ToArray(),
        d.ColumnX.ToArray(), d.ColumnY.ToArray(), d.ColumnFloor.ToArray(), d.ColumnCeiling.ToArray(), d.ColumnCapacity.ToArray(),
        d.EntryColumn.ToArray(), d.EntryFluid.ToArray(), d.EntryVolume.ToArray(),
        states.Select(s => s.ProviderId).ToArray(), states.Select(s => s.OwnerModId).ToArray(), states.Select(s => s.SchemaVersion).ToArray(), states.Select(s => s.Data).ToArray());

    /// <summary>SHA-256 over the fluid table, columns and component entries (not provider state).</summary>
    public static string ContentDigest(FluidSaveDocument d) {
      var text = new StringBuilder();
      void Line<T>(string name, IEnumerable<T> values) => text.Append(name).Append('=').Append(string.Join(",", values)).Append('\n');
      Line("ids", d.FluidIds); Line("owners", d.FluidOwners); Line("x", d.ColumnX); Line("y", d.ColumnY); Line("floor", d.ColumnFloor);
      Line("ceiling", d.ColumnCeiling); Line("capacity", d.ColumnCapacity); Line("column", d.EntryColumn); Line("fluid", d.EntryFluid); Line("volume", d.EntryVolume);
      using (var sha = SHA256.Create())
        return string.Concat(sha.ComputeHash(Encoding.UTF8.GetBytes(text.ToString())).Select(b => b.ToString("x2")));
    }
  }
}
