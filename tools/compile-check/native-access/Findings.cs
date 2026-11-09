namespace NativeAccess;

// What a reference names in the shipped assembly. Member and Signature are null for a type.
readonly record struct ReferenceKey(string Kind, string Assembly, string Type, string? Member, string? Signature);

// FromSubclass: every referencing input type (or a type enclosing it) derives from the declaring type of a
// protected member or protected nested type. InternalsVisibleTo: the defining assembly grants internal access to
// every referencing input (Deep Frontier to DeepFrontier.PowerLines). Both are facts for filtering the inventory,
// not proof the access compiles without publicizing.
sealed record NonPublicReference(string Assembly, string Type, string? Member, string Kind, string? Signature, string Visibility,
  bool FromSubclass, bool InternalsVisibleTo, IReadOnlyList<string> Inputs, IReadOnlyList<string> ReferencedBy);

sealed record MissingReference(string Assembly, string Type, string? Member, string Kind, string? Signature,
  IReadOnlyList<string> Inputs, IReadOnlyList<string> ReferencedBy);

// Merges references to the same definition across TypeRef/MemberRef rows and input assemblies.
sealed class Findings {
  sealed class Entry {
    public string? Visibility;
    public bool FromSubclass = true, InternalsVisibleTo = true;
    public readonly SortedSet<string> Inputs = new(StringComparer.Ordinal);
    public readonly SortedSet<string> ReferencedBy = new(StringComparer.Ordinal);
  }

  readonly Dictionary<ReferenceKey, Entry> nonPublic = new();
  readonly Dictionary<ReferenceKey, Entry> missing = new();

  public void NonPublic(ReferenceKey key, string visibility, bool fromSubclass, bool internalsVisibleTo, string input, IEnumerable<string> referencedBy) {
    var entry = Add(nonPublic, key, input, referencedBy);
    if (entry.Visibility != null && entry.Visibility != visibility)
      throw new InvalidDataException($"{key} resolved with two visibilities: {entry.Visibility} and {visibility}");
    entry.Visibility = visibility;
    entry.FromSubclass &= fromSubclass;
    entry.InternalsVisibleTo &= internalsVisibleTo;
  }

  public void Missing(ReferenceKey key, string input, IEnumerable<string> referencedBy) => Add(missing, key, input, referencedBy);

  static Entry Add(Dictionary<ReferenceKey, Entry> entries, ReferenceKey key, string input, IEnumerable<string> referencedBy) {
    if (!entries.TryGetValue(key, out var entry)) entries[key] = entry = new Entry();
    entry.Inputs.Add(input);
    entry.ReferencedBy.UnionWith(referencedBy);
    return entry;
  }

  static IEnumerable<KeyValuePair<ReferenceKey, Entry>> Sorted(Dictionary<ReferenceKey, Entry> entries) => entries
    .OrderBy(pair => pair.Key.Assembly, StringComparer.Ordinal)
    .ThenBy(pair => pair.Key.Type, StringComparer.Ordinal)
    .ThenBy(pair => pair.Key.Kind, StringComparer.Ordinal)
    .ThenBy(pair => pair.Key.Member ?? "", StringComparer.Ordinal)
    .ThenBy(pair => pair.Key.Signature ?? "", StringComparer.Ordinal);

  public IReadOnlyList<NonPublicReference> NonPublicEntries() => Sorted(nonPublic)
    .Select(pair => new NonPublicReference(pair.Key.Assembly, pair.Key.Type, pair.Key.Member, pair.Key.Kind, pair.Key.Signature,
      pair.Value.Visibility!, pair.Value.FromSubclass, pair.Value.InternalsVisibleTo, pair.Value.Inputs.ToList(), pair.Value.ReferencedBy.ToList()))
    .ToList();

  public IReadOnlyList<MissingReference> MissingEntries() => Sorted(missing)
    .Select(pair => new MissingReference(pair.Key.Assembly, pair.Key.Type, pair.Key.Member, pair.Key.Kind, pair.Key.Signature,
      pair.Value.Inputs.ToList(), pair.Value.ReferencedBy.ToList()))
    .ToList();
}
