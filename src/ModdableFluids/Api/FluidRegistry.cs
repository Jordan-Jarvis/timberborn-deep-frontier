using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Security.Cryptography;
using System.Text;

namespace ModdableFluids {
  /// <summary>
  /// A runtime index into one frozen registry. Handles are derived from the registry's
  /// content, not from registration order, and are never persisted: saves store fluid IDs.
  /// A handle from a registry with different content is rejected.
  /// </summary>
  public readonly struct FluidHandle : IEquatable<FluidHandle> {
    /// <summary>The component slot of this fluid in the registry's transport layout.</summary>
    public int Index { get; }
    internal uint Stamp { get; }
    internal FluidHandle(int index, uint stamp) { Index = index; Stamp = stamp; }
    public bool Equals(FluidHandle other) => Index == other.Index && Stamp == other.Stamp;
    public override bool Equals(object obj) => obj is FluidHandle other && Equals(other);
    public override int GetHashCode() => unchecked((int)Stamp * 397) ^ Index;
    public override string ToString() => "FluidHandle(" + Index + ")";
  }

  /// <summary>
  /// The frozen, validated set of fluids. Slot 0 is <see cref="FluidIds.Water"/>, slot 1 is
  /// <see cref="FluidIds.Badwater"/>, then every extra fluid in ordinal ID order.
  /// </summary>
  public sealed class FluidRegistry {
    public const int WaterIndex = 0;
    public const int BadwaterIndex = 1;
    private readonly FluidDefinition[] _definitions;
    private readonly Dictionary<string, int> _indices = new Dictionary<string, int>(StringComparer.Ordinal);
    private readonly uint _stamp;

    public int Count => _definitions.Length;
    /// <summary>SHA-256 over every definition's ID, owner and native role in handle order (lowercase hex).</summary>
    public string Fingerprint { get; }
    public IReadOnlyList<FluidDefinition> Definitions { get; }
    public IReadOnlyList<FluidProviderInfo> Providers { get; }
    public FluidHandle Water => new FluidHandle(WaterIndex, _stamp);
    public FluidHandle Badwater => new FluidHandle(BadwaterIndex, _stamp);

    internal FluidRegistry(FluidDefinition[] definitions, FluidProviderInfo[] providers) {
      if (definitions.Length < 2 || definitions[WaterIndex].Id != FluidIds.Water || definitions[BadwaterIndex].Id != FluidIds.Badwater)
        throw new InvalidOperationException("Registry layout must begin with the game's water and badwater");
      _definitions = definitions;
      for (int i = 0; i < definitions.Length; i++) _indices.Add(definitions[i].Id, i);
      var text = new StringBuilder("ModdableFluids.Registry/1\n");
      foreach (var definition in definitions)
        text.Append(definition.Id).Append('\t').Append(definition.OwnerModId).Append('\t').Append((int)definition.NativeRole).Append('\n');
      byte[] hash;
      using (var sha = SHA256.Create()) hash = sha.ComputeHash(Encoding.UTF8.GetBytes(text.ToString()));
      var hex = new StringBuilder(hash.Length * 2);
      foreach (byte b in hash) hex.Append(b.ToString("x2"));
      Fingerprint = hex.ToString();
      _stamp = (uint)(hash[0] | hash[1] << 8 | hash[2] << 16 | hash[3] << 24);
      Definitions = new ReadOnlyCollection<FluidDefinition>(definitions);
      Providers = new ReadOnlyCollection<FluidProviderInfo>(providers);
    }

    public bool TryGetHandle(string id, out FluidHandle handle) {
      if (id != null && _indices.TryGetValue(id, out int index)) { handle = new FluidHandle(index, _stamp); return true; }
      handle = default;
      return false;
    }

    public FluidHandle GetHandle(string id) {
      if (TryGetHandle(id, out var handle)) return handle;
      throw new ArgumentException("Fluid '" + id + "' is not registered");
    }

    public FluidDefinition Get(FluidHandle handle) {
      if (handle.Stamp != _stamp || handle.Index < 0 || handle.Index >= _definitions.Length)
        throw new ArgumentException(handle + " does not belong to registry " + Fingerprint.Substring(0, 12));
      return _definitions[handle.Index];
    }

    public bool TryGet(string id, out FluidDefinition definition) {
      if (id != null && _indices.TryGetValue(id, out int index)) { definition = _definitions[index]; return true; }
      definition = null;
      return false;
    }
  }

  /// <summary>Diagnostic description of one accepted provider.</summary>
  public sealed class FluidProviderInfo {
    public string ProviderId { get; }
    public string OwnerModId { get; }
    public string MinimumApiVersion { get; }
    /// <summary>"Compiled" or "Reflected".</summary>
    public string Route { get; }
    public IReadOnlyList<string> RequiredCapabilities { get; }
    public bool HasSceneLifecycle { get; }
    public bool HasState { get; }
    public int StateSchemaVersion { get; }
    internal FluidProviderInfo(string providerId, string ownerModId, string minimumApiVersion, string route,
        string[] requiredCapabilities, bool scene, bool state, int stateSchema) {
      ProviderId = providerId; OwnerModId = ownerModId; MinimumApiVersion = minimumApiVersion; Route = route;
      RequiredCapabilities = new ReadOnlyCollection<string>(requiredCapabilities);
      HasSceneLifecycle = scene; HasState = state; StateSchemaVersion = stateSchema;
    }
  }

  /// <summary>Every validation problem found while freezing, each naming its provider, mod and fluid.</summary>
  public sealed class FluidRegistryException : InvalidOperationException {
    public IReadOnlyList<string> Problems { get; }
    internal FluidRegistryException(IList<string> problems)
      : base("Moddable Fluids registry rejected " + problems.Count + " problem(s):\n- " + string.Join("\n- ", problems)) {
      Problems = new ReadOnlyCollection<string>(new List<string>(problems));
    }
  }
}
