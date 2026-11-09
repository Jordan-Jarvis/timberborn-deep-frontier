using System.Reflection;
using System.Reflection.Emit;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;

namespace NativeAccess;

// Input code that uses a reference: a label for the report and the input type it belongs to (nil for
// assembly-level metadata and unattributed references).
readonly record struct Owner(string Label, TypeDefinitionHandle Type);

// Checks one input assembly: every TypeRef and MemberRef (fields and methods, also on generic instantiations
// through TypeSpec parents) against its definition in the shipped assembly, and attributes each reference to the
// input methods that use it (IL tokens, locals, signatures). MethodSpecs are covered through their method (a
// MemberRef or the input's own MethodDef) and their instantiation's TypeRefs.
sealed class ReferenceScanner {
  public const string Metadata = "(metadata)";

  static readonly Dictionary<ushort, OperandType> Operands = typeof(OpCodes)
    .GetFields(BindingFlags.Public | BindingFlags.Static)
    .Select(field => (OpCode)field.GetValue(null)!)
    .ToDictionary(opcode => unchecked((ushort)opcode.Value), opcode => opcode.OperandType);

  readonly LoadedAssembly input;
  readonly MetadataReader reader;
  readonly AssemblyResolver resolver;
  readonly Findings findings;
  readonly SignatureNames names = new();
  readonly Dictionary<EntityHandle, HashSet<Owner>> users = new();

  public ReferenceScanner(LoadedAssembly input, AssemblyResolver resolver, Findings findings) {
    this.input = input;
    reader = input.Reader;
    this.resolver = resolver;
    this.findings = findings;
  }

  public void Run() {
    Attribute();
    foreach (var handle in reader.TypeReferences) CheckType(handle);
    foreach (var handle in reader.MemberReferences) CheckMember(handle);
  }

  IReadOnlyCollection<Owner> Users(EntityHandle handle) =>
    users.TryGetValue(handle, out var owners) ? owners : [new Owner(Metadata, default)];

  IEnumerable<string> ReferencedBy(EntityHandle handle) => Users(handle).Select(owner => owner.Label);

  void CheckType(TypeReferenceHandle handle) {
    var lookup = resolver.ResolveTypeReference(input, handle);
    switch (lookup.Kind) {
      case LookupKind.Own:
        return;
      case LookupKind.Unresolved:
        resolver.CountUnchecked(lookup.AssemblyName);
        return;
      case LookupKind.Missing:
        findings.Missing(new("type", lookup.AssemblyName, lookup.TypeName, null, null), input.Name, ReferencedBy(handle));
        return;
    }
    var assembly = lookup.Assembly!;
    var definition = assembly.Reader.GetTypeDefinition(lookup.Handle);
    var own = Visibility.Type(definition.Attributes);
    var enclosing = definition.GetDeclaringType();
    var enclosingIssue = enclosing.IsNil ? null : Visibility.NonPublicChain(assembly.Reader, enclosing);
    var visibility = Visibility.Describe(own, enclosingIssue);
    if (visibility == null) return;
    // A protected nested type is reachable from types derived from its enclosing type.
    bool fromSubclass = Visibility.IsProtected(own) && enclosingIssue == null
      && FromSubclass(handle, assembly.Name, TypeNames.Definition(assembly.Reader, enclosing));
    findings.NonPublic(new("type", lookup.AssemblyName, lookup.TypeName, null, null), visibility, fromSubclass,
      assembly.GrantsInternalsTo(input.Name), input.Name, ReferencedBy(handle));
  }

  void CheckMember(MemberReferenceHandle handle) {
    var reference = reader.GetMemberReference(handle);
    var name = reader.GetString(reference.Name);
    var parent = reference.Parent;
    TypeLookup owner;
    switch (parent.Kind) {
      case HandleKind.TypeDefinition:
      case HandleKind.MethodDefinition:
        return; // The input's own type, or a vararg call site of its own method.
      case HandleKind.TypeReference:
        owner = resolver.ResolveTypeReference(input, (TypeReferenceHandle)parent);
        break;
      case HandleKind.TypeSpecification:
        var head = AssemblyResolver.SpecificationHead(reader, (TypeSpecificationHandle)parent);
        if (head is not { } generic) return; // Multi-dimensional array Get/Set/Address/.ctor: provided by the runtime.
        if (generic.Kind == HandleKind.TypeDefinition) return;
        owner = resolver.ResolveTypeReference(input, (TypeReferenceHandle)generic);
        break;
      default:
        throw new NotSupportedException($"{input.Name}: member reference {name} has a {parent.Kind} parent");
    }
    if (owner.Kind == LookupKind.Own) return;
    if (owner.Kind == LookupKind.Unresolved) {
      resolver.CountUnchecked(owner.AssemblyName);
      return;
    }

    string kind, signature;
    Func<LoadedAssembly, TypeDefinitionHandle, string?> find; // the matching definition's access, or null
    if (reference.GetKind() == MemberReferenceKind.Field) {
      kind = "field";
      signature = TypeNames.Field(name, reference.DecodeFieldSignature(names, null));
      find = (assembly, type) => {
        var definitions = assembly.Reader;
        foreach (var field in definitions.GetTypeDefinition(type).GetFields()) {
          var definition = definitions.GetFieldDefinition(field);
          if (definitions.GetString(definition.Name) == name && TypeNames.Field(name, definition.DecodeSignature(names, null)) == signature)
            return Visibility.Member((int)(definition.Attributes & FieldAttributes.FieldAccessMask));
        }
        return null;
      };
    } else {
      kind = "method";
      signature = TypeNames.Method(name, reference.DecodeMethodSignature(names, null));
      find = (assembly, type) => {
        var definitions = assembly.Reader;
        foreach (var method in definitions.GetTypeDefinition(type).GetMethods()) {
          var definition = definitions.GetMethodDefinition(method);
          if (definitions.GetString(definition.Name) == name && TypeNames.Method(name, definition.DecodeSignature(names, null)) == signature)
            return Visibility.Member((int)(definition.Attributes & MethodAttributes.MemberAccessMask));
        }
        return null;
      };
    }

    if (owner.Kind == LookupKind.Missing) {
      findings.Missing(new(kind, owner.AssemblyName, owner.TypeName, name, signature), input.Name, ReferencedBy(handle));
      return;
    }
    // As Mono (and Cecil's MetadataResolver) resolve a MemberRef: the named type, then its base types.
    var current = owner;
    for (int depth = 0; ; depth++) {
      if (depth > 64) throw new InvalidDataException($"Base type chain of {owner.TypeName} is deeper than 64");
      var assembly = current.Assembly!;
      if (find(assembly, current.Handle) is { } access) {
        var enclosingIssue = Visibility.NonPublicChain(assembly.Reader, current.Handle);
        var visibility = Visibility.Describe(access, enclosingIssue);
        if (visibility == null) return;
        bool fromSubclass = Visibility.IsProtected(access) && enclosingIssue == null && FromSubclass(handle, current.AssemblyName, current.TypeName);
        findings.NonPublic(new(kind, current.AssemblyName, current.TypeName, name, signature), visibility, fromSubclass,
          assembly.GrantsInternalsTo(input.Name), input.Name, ReferencedBy(handle));
        return;
      }
      var baseType = assembly.Reader.GetTypeDefinition(current.Handle).BaseType;
      if (baseType.IsNil) {
        findings.Missing(new(kind, owner.AssemblyName, owner.TypeName, name, signature), input.Name, ReferencedBy(handle));
        return;
      }
      current = resolver.ResolveTypeHandle(assembly, baseType);
      switch (current.Kind) {
        case LookupKind.Unresolved:
          resolver.CountUnchecked(current.AssemblyName);
          return;
        case LookupKind.Missing:
          findings.Missing(new("type", current.AssemblyName, current.TypeName, null, null), input.Name, ReferencedBy(handle));
          return;
        case LookupKind.Own:
          throw new InvalidDataException($"Base type {current.TypeName} of {owner.TypeName} resolves to a module-local reference");
      }
    }
  }

  // True when every input type using the reference (or a type enclosing it) derives from the given type. This
  // is a fact about the referencing types, not proof the C# access rule holds: a protected instance member must
  // also be accessed through an instance of the deriving type, which this metadata scan does not check.
  bool FromSubclass(EntityHandle handle, string assemblyName, string typeName) =>
    Users(handle).All(owner => !owner.Type.IsNil && Derives(owner.Type, assemblyName, typeName));

  bool Derives(TypeDefinitionHandle type, string assemblyName, string typeName) {
    for (var outer = type; !outer.IsNil; outer = reader.GetTypeDefinition(outer).GetDeclaringType()) {
      var assembly = input;
      var baseType = reader.GetTypeDefinition(outer).BaseType;
      for (int depth = 0; !baseType.IsNil; depth++) {
        if (depth > 64) throw new InvalidDataException($"Base type chain of {TypeNames.Definition(reader, outer)} is deeper than 64");
        var lookup = resolver.ResolveTypeHandle(assembly, baseType);
        if (lookup.Kind != LookupKind.Found) break;
        if (lookup.AssemblyName.Equals(assemblyName, StringComparison.OrdinalIgnoreCase) && lookup.TypeName == typeName) return true;
        assembly = lookup.Assembly!;
        baseType = assembly.Reader.GetTypeDefinition(lookup.Handle).BaseType;
      }
    }
    return false;
  }

  // ---- Attribution: which input methods (or type metadata) use each TypeRef and MemberRef.

  void Attribute() {
    foreach (var typeHandle in reader.TypeDefinitions) {
      var type = reader.GetTypeDefinition(typeHandle);
      var typeName = TypeNames.Definition(reader, typeHandle);
      var typeOwner = new Owner(typeName + "::" + Metadata, typeHandle);
      Use(typeOwner, type.BaseType);
      foreach (var interfaceHandle in type.GetInterfaceImplementations()) {
        var implementation = reader.GetInterfaceImplementation(interfaceHandle);
        Use(typeOwner, implementation.Interface);
        Attributes(typeOwner, implementation.GetCustomAttributes());
      }
      GenericParameters(typeOwner, type.GetGenericParameters());
      Attributes(typeOwner, type.GetCustomAttributes());
      foreach (var fieldHandle in type.GetFields()) {
        var field = reader.GetFieldDefinition(fieldHandle);
        Signature(typeOwner, collector => field.DecodeSignature(collector, null));
        Attributes(typeOwner, field.GetCustomAttributes());
      }
      foreach (var propertyHandle in type.GetProperties()) {
        var property = reader.GetPropertyDefinition(propertyHandle);
        Signature(typeOwner, collector => property.DecodeSignature(collector, null));
        Attributes(typeOwner, property.GetCustomAttributes());
      }
      foreach (var eventHandle in type.GetEvents()) {
        var definition = reader.GetEventDefinition(eventHandle);
        Use(typeOwner, definition.Type);
        Attributes(typeOwner, definition.GetCustomAttributes());
      }
      foreach (var methodHandle in type.GetMethods()) Method(MethodOwner(typeName, typeHandle, methodHandle), methodHandle);
      foreach (var implementationHandle in type.GetMethodImplementations()) {
        // Explicit interface implementations name the implemented method, often a MemberRef.
        var implementation = reader.GetMethodImplementation(implementationHandle);
        Use(MethodOwner(typeName, typeHandle, implementation.MethodBody), implementation.MethodDeclaration);
      }
    }
    var assemblyOwner = new Owner(Metadata, default);
    Attributes(assemblyOwner, reader.GetAssemblyDefinition().GetCustomAttributes());
    Attributes(assemblyOwner, reader.GetModuleDefinition().GetCustomAttributes());
  }

  Owner MethodOwner(string typeName, TypeDefinitionHandle type, EntityHandle method) => new(method.Kind == HandleKind.MethodDefinition
    ? typeName + "::" + reader.GetString(reader.GetMethodDefinition((MethodDefinitionHandle)method).Name)
    : typeName + "::" + Metadata, type);

  void Method(Owner owner, MethodDefinitionHandle handle) {
    var method = reader.GetMethodDefinition(handle);
    Signature(owner, collector => method.DecodeSignature(collector, null));
    GenericParameters(owner, method.GetGenericParameters());
    Attributes(owner, method.GetCustomAttributes());
    foreach (var parameter in method.GetParameters()) Attributes(owner, reader.GetParameter(parameter).GetCustomAttributes());
    if (method.RelativeVirtualAddress == 0) return;
    var body = input.PE.GetMethodBody(method.RelativeVirtualAddress);
    if (!body.LocalSignature.IsNil) Use(owner, body.LocalSignature);
    foreach (var region in body.ExceptionRegions) Use(owner, region.CatchType);
    var il = body.GetILReader();
    while (il.RemainingBytes > 0) {
      int offset = il.Offset;
      int code = il.ReadByte();
      if (code == 0xFE) code = 0xFE00 | il.ReadByte();
      if (!Operands.TryGetValue((ushort)code, out var operand))
        throw new BadImageFormatException($"{input.Name}: {owner.Label} has unknown IL opcode 0x{code:X} at IL_{offset:X4}");
      switch (operand) {
        case OperandType.InlineNone:
          break;
        case OperandType.ShortInlineBrTarget:
        case OperandType.ShortInlineI:
        case OperandType.ShortInlineVar:
          il.ReadByte();
          break;
        case OperandType.InlineVar:
          il.ReadUInt16();
          break;
        case OperandType.InlineBrTarget:
        case OperandType.InlineI:
        case OperandType.ShortInlineR:
        case OperandType.InlineString:
          il.ReadInt32();
          break;
        case OperandType.InlineI8:
        case OperandType.InlineR:
          il.ReadInt64();
          break;
        case OperandType.InlineSwitch:
          for (int targets = il.ReadInt32(); targets > 0; targets--) il.ReadInt32();
          break;
        // call/callvirt/newobj/jmp/ldftn/ldvirtftn, ldfld/ldflda/stfld/ldsfld/ldsflda/stsfld, ldtoken, every type
        // operand (box, castclass, isinst, newarr, initobj, constrained., ...) and calli's StandAloneSig.
        case OperandType.InlineMethod:
        case OperandType.InlineField:
        case OperandType.InlineType:
        case OperandType.InlineTok:
        case OperandType.InlineSig:
          Use(owner, MetadataTokens.EntityHandle(il.ReadInt32()));
          break;
        default:
          throw new BadImageFormatException($"{input.Name}: {owner.Label} has IL operand type {operand} at IL_{offset:X4}");
      }
    }
  }

  void GenericParameters(Owner owner, GenericParameterHandleCollection parameters) {
    foreach (var parameterHandle in parameters) {
      var parameter = reader.GetGenericParameter(parameterHandle);
      Attributes(owner, parameter.GetCustomAttributes());
      foreach (var constraintHandle in parameter.GetConstraints()) {
        var constraint = reader.GetGenericParameterConstraint(constraintHandle);
        Use(owner, constraint.Type);
        Attributes(owner, constraint.GetCustomAttributes());
      }
    }
  }

  // Attribute constructors only: typeof() and enum arguments are stored as type-name strings in the blob, not as
  // TypeRefs, so [HarmonyPatch(typeof(T), "name")] targets are not visible to this scan.
  void Attributes(Owner owner, CustomAttributeHandleCollection attributes) {
    foreach (var attribute in attributes) Use(owner, reader.GetCustomAttribute(attribute).Constructor);
  }

  void Signature(Owner owner, Action<SignatureNames> decode) {
    var used = new HashSet<EntityHandle>();
    decode(new SignatureNames(used));
    Record(owner, used);
  }

  void Use(Owner owner, EntityHandle handle) {
    if (handle.IsNil) return;
    var used = new HashSet<EntityHandle>();
    Expand(handle, used);
    Record(owner, used);
  }

  void Record(Owner owner, IEnumerable<EntityHandle> used) {
    foreach (var handle in used) {
      if (!users.TryGetValue(handle, out var owners)) users[handle] = owners = new();
      owners.Add(owner);
    }
  }

  // The TypeRefs and MemberRefs a token or handle depends on.
  void Expand(EntityHandle handle, HashSet<EntityHandle> used) {
    var collector = new SignatureNames(used);
    switch (handle.Kind) {
      case HandleKind.TypeDefinition:
      case HandleKind.MethodDefinition:
      case HandleKind.FieldDefinition:
        return;
      case HandleKind.TypeReference:
        TypeNames.AddWithEnclosing(reader, (TypeReferenceHandle)handle, used);
        return;
      case HandleKind.TypeSpecification:
        reader.GetTypeSpecification((TypeSpecificationHandle)handle).DecodeSignature(collector, null);
        return;
      case HandleKind.MemberReference: {
        if (!used.Add(handle)) return;
        var reference = reader.GetMemberReference((MemberReferenceHandle)handle);
        Expand(reference.Parent, used);
        if (reference.GetKind() == MemberReferenceKind.Field) reference.DecodeFieldSignature(collector, null);
        else reference.DecodeMethodSignature(collector, null);
        return;
      }
      case HandleKind.MethodSpecification: {
        var specification = reader.GetMethodSpecification((MethodSpecificationHandle)handle);
        Expand(specification.Method, used);
        specification.DecodeSignature(collector, null);
        return;
      }
      case HandleKind.StandaloneSignature: {
        var signature = reader.GetStandaloneSignature((StandaloneSignatureHandle)handle);
        if (signature.GetKind() == StandaloneSignatureKind.LocalVariables) signature.DecodeLocalSignature(collector, null);
        else signature.DecodeMethodSignature(collector, null);
        return;
      }
      default:
        throw new NotSupportedException($"{input.Name}: unexpected {handle.Kind} token");
    }
  }
}
