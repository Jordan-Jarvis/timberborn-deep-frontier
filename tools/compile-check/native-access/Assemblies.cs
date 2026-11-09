using System.Collections.Immutable;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;

namespace NativeAccess;

sealed class LoadedAssembly {
  public string Name { get; }
  public string Path { get; }
  public string Origin { get; }
  public PEReader PE { get; }
  public MetadataReader Reader { get; }
  Dictionary<(string Namespace, string Name), TypeDefinitionHandle>? topLevel;
  Dictionary<(string Namespace, string Name), AssemblyReferenceHandle>? forwarders;

  LoadedAssembly(string path, string origin, PEReader pe) {
    Path = path;
    Origin = origin;
    PE = pe;
    Reader = pe.GetMetadataReader();
    Name = Reader.GetString(Reader.GetAssemblyDefinition().Name);
  }

  // Reads the whole file so no handle stays open on the game's or a mod's files. Null when the file is not a
  // .NET assembly (Workshop folders also carry native libraries).
  public static LoadedAssembly? TryLoad(string path, string origin) {
    var pe = new PEReader(ImmutableArray.Create(File.ReadAllBytes(path)));
    if (!pe.HasMetadata || !pe.GetMetadataReader().IsAssembly) return null;
    return new LoadedAssembly(path, origin, pe);
  }

  public static LoadedAssembly Load(string path, string origin) =>
    TryLoad(path, origin) ?? throw new BadImageFormatException($"{path} is not a .NET assembly");

  public bool TryGetTopLevel(string ns, string name, out TypeDefinitionHandle handle) {
    topLevel ??= Reader.TypeDefinitions
      .Where(h => Reader.GetTypeDefinition(h).GetDeclaringType().IsNil)
      .ToDictionary(h => (Reader.GetString(Reader.GetTypeDefinition(h).Namespace), Reader.GetString(Reader.GetTypeDefinition(h).Name)));
    return topLevel.TryGetValue((ns, name), out handle);
  }

  // Assembly names this assembly's [InternalsVisibleTo] attributes grant internal access to.
  HashSet<string>? friends;

  public bool GrantsInternalsTo(string assemblyName) {
    if (friends == null) {
      friends = new(StringComparer.OrdinalIgnoreCase);
      foreach (var handle in Reader.GetAssemblyDefinition().GetCustomAttributes()) {
        var attribute = Reader.GetCustomAttribute(handle);
        if (AttributeTypeName(attribute.Constructor) != "System.Runtime.CompilerServices.InternalsVisibleToAttribute") continue;
        var value = Reader.GetBlobReader(attribute.Value);
        if (value.ReadUInt16() != 1) throw new BadImageFormatException($"{Path}: InternalsVisibleTo blob without prolog");
        var friend = value.ReadSerializedString() ?? throw new BadImageFormatException($"{Path}: InternalsVisibleTo(null)");
        friends.Add(friend.Split(',')[0].Trim()); // "Name, PublicKey=..." for strong-named friends.
      }
    }
    return friends.Contains(assemblyName);
  }

  string AttributeTypeName(EntityHandle constructor) => constructor.Kind switch {
    HandleKind.MemberReference => Reader.GetMemberReference((MemberReferenceHandle)constructor).Parent is var parent && parent.Kind == HandleKind.TypeReference
      ? TypeNames.Reference(Reader, (TypeReferenceHandle)parent) : "",
    HandleKind.MethodDefinition => TypeNames.Definition(Reader, Reader.GetMethodDefinition((MethodDefinitionHandle)constructor).GetDeclaringType()),
    _ => throw new BadImageFormatException($"{Path}: attribute constructor is a {constructor.Kind}"),
  };

  // Top-level type forwarders ([TypeForwardedTo], e.g. netstandard.dll to mscorlib.dll). Nested forwarded types
  // are found through their resolved enclosing type, so only top-level ones are indexed.
  public bool TryGetForwarder(string ns, string name, out AssemblyReferenceHandle target) {
    if (forwarders == null) {
      forwarders = new();
      foreach (var handle in Reader.ExportedTypes) {
        var exported = Reader.GetExportedType(handle);
        if (!exported.IsForwarder || exported.Implementation.Kind != HandleKind.AssemblyReference) continue;
        forwarders.Add((Reader.GetString(exported.Namespace), Reader.GetString(exported.Name)), (AssemblyReferenceHandle)exported.Implementation);
      }
    }
    return forwarders.TryGetValue((ns, name), out target);
  }
}

enum LookupKind { Found, Own, Missing, Unresolved }

// Where a type reference lands. Found: Assembly/Handle are the definition. Missing: AssemblyName is the assembly
// that should have defined TypeName. Unresolved: AssemblyName could not be located, so nothing under it is checked.
sealed record TypeLookup(LookupKind Kind, string AssemblyName, string TypeName, LoadedAssembly? Assembly = null, TypeDefinitionHandle Handle = default) {
  public static TypeLookup Own(string typeName) => new(LookupKind.Own, "", typeName);
}

sealed record UnresolvedAssembly(string Assembly, string Reason, IReadOnlyList<string> Candidates) {
  public int UncheckedReferences { get; set; }
}

// Locates a referenced assembly by simple name: an input DLL, an --assembly pin, the shipped Managed directory
// (top level only), then the Workshop content directory (recursive, by file name). Nothing is chosen between
// different files: several distinct Workshop candidates (mods ship one copy per game-version folder) make the
// assembly unresolved until an --assembly pin names the file.
sealed class AssemblyResolver {
  readonly string managed;
  readonly string? workshop;
  readonly Dictionary<string, LoadedAssembly> explicitAssemblies = new(StringComparer.OrdinalIgnoreCase);
  readonly Dictionary<string, LoadedAssembly?> resolved = new(StringComparer.OrdinalIgnoreCase);
  readonly Dictionary<string, UnresolvedAssembly> unresolved = new(StringComparer.OrdinalIgnoreCase);
  ILookup<string, string>? workshopFiles;

  public IReadOnlyList<LoadedAssembly> Inputs { get; }

  public AssemblyResolver(Options options) {
    managed = options.Managed;
    workshop = options.Workshop;
    Inputs = options.Inputs.Select(path => LoadedAssembly.Load(path, "input")).ToList();
    foreach (var assembly in Inputs.Concat(options.Pinned.Select(path => LoadedAssembly.Load(path, "assembly")))) {
      if (!explicitAssemblies.TryAdd(assembly.Name, assembly))
        throw new ArgumentException($"Assembly {assembly.Name} is given twice: {explicitAssemblies[assembly.Name].Path} and {assembly.Path}");
    }
  }

  public IEnumerable<LoadedAssembly> Resolved => resolved.Values.OfType<LoadedAssembly>();

  public IEnumerable<UnresolvedAssembly> Unresolved => unresolved.Values;

  public void CountUnchecked(string assemblyName) => unresolved[assemblyName].UncheckedReferences++;

  public LoadedAssembly? Resolve(string name) {
    if (!resolved.TryGetValue(name, out var assembly)) resolved[name] = assembly = Locate(name);
    return assembly;
  }

  LoadedAssembly? Locate(string name) {
    if (explicitAssemblies.TryGetValue(name, out var given)) return given;
    var fileName = name + ".dll";
    var managedPath = System.IO.Path.Combine(managed, fileName);
    if (File.Exists(managedPath)) {
      var assembly = LoadedAssembly.Load(managedPath, "managed");
      if (!assembly.Name.Equals(name, StringComparison.OrdinalIgnoreCase))
        throw new BadImageFormatException($"{managedPath} defines assembly {assembly.Name}, not {name}");
      return assembly;
    }
    if (workshop == null) return Fail(name, "not in the Managed directory, and no --workshop directory was given", []);
    workshopFiles ??= Directory.EnumerateFiles(workshop, "*.dll", SearchOption.AllDirectories)
      .ToLookup(path => System.IO.Path.GetFileName(path), StringComparer.OrdinalIgnoreCase);
    var candidates = workshopFiles[fileName]
      .Select(path => LoadedAssembly.TryLoad(path, "workshop"))
      .OfType<LoadedAssembly>()
      .Where(candidate => candidate.Name.Equals(name, StringComparison.OrdinalIgnoreCase))
      .OrderBy(candidate => candidate.Path, StringComparer.Ordinal)
      .ToList();
    var distinct = candidates.GroupBy(candidate => Convert.ToHexString(SHA256.HashData(candidate.PE.GetEntireImage().GetContent().AsSpan())))
      .Select(group => group.First())
      .ToList();
    return distinct.Count switch {
      0 => Fail(name, "not in the Managed directory or the Workshop directory", []),
      1 => distinct[0],
      _ => Fail(name, $"{distinct.Count} different files in the Workshop directory; pin one with --assembly", distinct.Select(candidate => candidate.Path).ToList()),
    };
  }

  LoadedAssembly? Fail(string name, string reason, IReadOnlyList<string> candidates) {
    unresolved[name] = new UnresolvedAssembly(name, reason, candidates);
    return null;
  }

  // Resolves a TypeReference made in `from` (an input, or a definition assembly while walking base types).
  public TypeLookup ResolveTypeReference(LoadedAssembly from, TypeReferenceHandle handle) {
    var reader = from.Reader;
    var reference = reader.GetTypeReference(handle);
    var scope = reference.ResolutionScope;
    var ns = reader.GetString(reference.Namespace);
    var name = reader.GetString(reference.Name);
    switch (scope.Kind) {
      case HandleKind.AssemblyReference:
        return FindTopLevel(reader.GetString(reader.GetAssemblyReference((AssemblyReferenceHandle)scope).Name), ns, name, TypeNames.Reference(reader, handle), 0);
      case HandleKind.TypeReference: {
        var outer = ResolveTypeReference(from, (TypeReferenceHandle)scope);
        if (outer.Kind != LookupKind.Found) return outer with { TypeName = TypeNames.Reference(reader, handle) };
        var outerReader = outer.Assembly!.Reader;
        foreach (var nested in outerReader.GetTypeDefinition(outer.Handle).GetNestedTypes()) {
          var definition = outerReader.GetTypeDefinition(nested);
          if (outerReader.GetString(definition.Name) == name && outerReader.GetString(definition.Namespace) == ns)
            return new TypeLookup(LookupKind.Found, outer.AssemblyName, TypeNames.Definition(outerReader, nested), outer.Assembly, nested);
        }
        return new TypeLookup(LookupKind.Missing, outer.AssemblyName, TypeNames.Reference(reader, handle));
      }
      case HandleKind.ModuleDefinition:
        return TypeLookup.Own(TypeNames.Reference(reader, handle));
      default:
        throw new NotSupportedException($"{from.Name}: type reference {TypeNames.Reference(reader, handle)} has a {scope.Kind} resolution scope");
    }
  }

  TypeLookup FindTopLevel(string assemblyName, string ns, string name, string typeName, int forwards) {
    var assembly = Resolve(assemblyName);
    if (assembly == null) return new TypeLookup(LookupKind.Unresolved, assemblyName, typeName);
    if (assembly.TryGetTopLevel(ns, name, out var definition))
      return new TypeLookup(LookupKind.Found, assembly.Name, TypeNames.Definition(assembly.Reader, definition), assembly, definition);
    if (assembly.TryGetForwarder(ns, name, out var target)) {
      if (forwards > 16) throw new InvalidDataException($"Type forwarding loop for {typeName} at {assembly.Path}");
      return FindTopLevel(assembly.Reader.GetString(assembly.Reader.GetAssemblyReference(target).Name), ns, name, typeName, forwards + 1);
    }
    return new TypeLookup(LookupKind.Missing, assembly.Name, typeName);
  }

  // A type handle inside `from`: its own definition, a reference, or a generic instantiation (its generic type).
  public TypeLookup ResolveTypeHandle(LoadedAssembly from, EntityHandle handle) => handle.Kind switch {
    HandleKind.TypeDefinition => new TypeLookup(LookupKind.Found, from.Name, TypeNames.Definition(from.Reader, (TypeDefinitionHandle)handle), from, (TypeDefinitionHandle)handle),
    HandleKind.TypeReference => ResolveTypeReference(from, (TypeReferenceHandle)handle),
    HandleKind.TypeSpecification => SpecificationHead(from.Reader, (TypeSpecificationHandle)handle) is { } head
      ? ResolveTypeHandle(from, head)
      : throw new NotSupportedException($"{from.Name}: array type specification used as a type definition"),
    _ => throw new NotSupportedException($"{from.Name}: {handle.Kind} used as a type"),
  };

  // The generic type of a generic instantiation TypeSpec; null for an array (whose methods the runtime provides).
  // Anything else as a member's parent or a base type is not something a C# compiler emits.
  public static EntityHandle? SpecificationHead(MetadataReader reader, TypeSpecificationHandle handle) {
    var blob = reader.GetBlobReader(reader.GetTypeSpecification(handle).Signature);
    var code = blob.ReadSignatureTypeCode();
    switch (code) {
      case SignatureTypeCode.GenericTypeInstance:
        if (blob.ReadSignatureTypeCode() != SignatureTypeCode.TypeHandle) throw new BadImageFormatException("Generic instantiation without a class or value type");
        return blob.ReadTypeHandle();
      case SignatureTypeCode.Array:
      case SignatureTypeCode.SZArray:
        return null;
      default:
        throw new NotSupportedException($"Type specification {reader.GetTypeSpecification(handle).DecodeSignature(new SignatureNames(), null)} ({code}) used as a member parent or base type");
    }
  }
}
