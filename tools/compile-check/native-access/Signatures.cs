using System.Collections.Immutable;
using System.Reflection;
using System.Reflection.Metadata;

namespace NativeAccess;

// Type and member names as strings. A referencing signature (MemberRef in the mod) and a candidate definition
// (MethodDefinition/FieldDefinition in the shipped assembly) are decoded by the same provider and compared as
// strings. Types are named by namespace, name and nesting ('+'), without their assembly: the referencing side
// names netstandard/mscorlib facades and forwarded types where the definition names the implementation, and
// Mono.Cecil's MetadataResolver compares references the same way. Generic parameters render as !0 (type) and
// !!0 (method).
static class TypeNames {
  public static string Definition(MetadataReader reader, TypeDefinitionHandle handle) {
    var type = reader.GetTypeDefinition(handle);
    var name = reader.GetString(type.Name);
    var outer = type.GetDeclaringType();
    if (!outer.IsNil) return Definition(reader, outer) + "+" + name;
    return Qualify(reader.GetString(type.Namespace), name);
  }

  public static string Reference(MetadataReader reader, TypeReferenceHandle handle) {
    var type = reader.GetTypeReference(handle);
    var name = reader.GetString(type.Name);
    if (type.ResolutionScope.Kind == HandleKind.TypeReference)
      return Reference(reader, (TypeReferenceHandle)type.ResolutionScope) + "+" + name;
    return Qualify(reader.GetString(type.Namespace), name);
  }

  // A nested TypeRef also uses every TypeRef that encloses it (its resolution scope chain).
  public static void AddWithEnclosing(MetadataReader reader, TypeReferenceHandle handle, ISet<EntityHandle> into) {
    while (true) {
      into.Add(handle);
      var scope = reader.GetTypeReference(handle).ResolutionScope;
      if (scope.Kind != HandleKind.TypeReference) return;
      handle = (TypeReferenceHandle)scope;
    }
  }

  static string Qualify(string ns, string name) => ns.Length == 0 ? name : ns + "." + name;

  public static string Method(string name, MethodSignature<string> signature) {
    var header = signature.Header;
    var prefix = (header.IsInstance ? "" : "static ") + (header.HasExplicitThis ? "explicit " : "")
      + (header.CallingConvention == SignatureCallingConvention.Default ? "" : header.CallingConvention.ToString().ToLowerInvariant() + " ");
    var generic = signature.GenericParameterCount > 0 ? "``" + signature.GenericParameterCount : "";
    // A vararg call site's MemberRef appends the passed extra arguments; the definition has only the required ones.
    var parameters = signature.ParameterTypes.Take(signature.RequiredParameterCount);
    return $"{prefix}{signature.ReturnType} {name}{generic}({string.Join(", ", parameters)})";
  }

  public static string Field(string name, string type) => $"{type} {name}";
}

// Renders signature types as strings. With a collect set it also records every TypeReference the decoded
// signature mentions (with its enclosing TypeRefs), which attributes TypeRefs to the members using them.
sealed class SignatureNames : ISignatureTypeProvider<string, object?> {
  readonly ISet<EntityHandle>? collect;

  public SignatureNames(ISet<EntityHandle>? collect = null) => this.collect = collect;

  public string GetPrimitiveType(PrimitiveTypeCode typeCode) => typeCode switch {
    PrimitiveTypeCode.Void => "void",
    PrimitiveTypeCode.Boolean => "bool",
    PrimitiveTypeCode.Char => "char",
    PrimitiveTypeCode.SByte => "sbyte",
    PrimitiveTypeCode.Byte => "byte",
    PrimitiveTypeCode.Int16 => "short",
    PrimitiveTypeCode.UInt16 => "ushort",
    PrimitiveTypeCode.Int32 => "int",
    PrimitiveTypeCode.UInt32 => "uint",
    PrimitiveTypeCode.Int64 => "long",
    PrimitiveTypeCode.UInt64 => "ulong",
    PrimitiveTypeCode.Single => "float",
    PrimitiveTypeCode.Double => "double",
    PrimitiveTypeCode.String => "string",
    PrimitiveTypeCode.Object => "object",
    PrimitiveTypeCode.IntPtr => "System.IntPtr",
    PrimitiveTypeCode.UIntPtr => "System.UIntPtr",
    PrimitiveTypeCode.TypedReference => "System.TypedReference",
    _ => throw new BadImageFormatException($"Unknown primitive type code {typeCode}"),
  };

  public string GetTypeFromDefinition(MetadataReader reader, TypeDefinitionHandle handle, byte rawTypeKind) =>
    TypeNames.Definition(reader, handle);

  public string GetTypeFromReference(MetadataReader reader, TypeReferenceHandle handle, byte rawTypeKind) {
    if (collect != null) TypeNames.AddWithEnclosing(reader, handle, collect);
    return TypeNames.Reference(reader, handle);
  }

  public string GetTypeFromSpecification(MetadataReader reader, object? genericContext, TypeSpecificationHandle handle, byte rawTypeKind) =>
    reader.GetTypeSpecification(handle).DecodeSignature(this, genericContext);

  public string GetSZArrayType(string elementType) => elementType + "[]";

  // As ildasm writes bounds: "lo..." (lower bound only), "n" (size only), "lo...hi" (both), "" (neither).
  public string GetArrayType(string elementType, ArrayShape shape) {
    var dimensions = new string[shape.Rank];
    for (int i = 0; i < shape.Rank; i++) {
      bool hasLower = i < shape.LowerBounds.Length, hasSize = i < shape.Sizes.Length;
      dimensions[i] = (hasLower, hasSize) switch {
        (false, false) => "",
        (false, true) => shape.Sizes[i].ToString(),
        (true, false) => shape.LowerBounds[i] + "...",
        (true, true) => shape.LowerBounds[i] + "..." + (shape.LowerBounds[i] + shape.Sizes[i] - 1),
      };
    }
    return elementType + "[" + string.Join(",", dimensions) + "]";
  }

  public string GetByReferenceType(string elementType) => elementType + "&";

  public string GetPointerType(string elementType) => elementType + "*";

  public string GetPinnedType(string elementType) => elementType + " pinned";

  public string GetGenericInstantiation(string genericType, ImmutableArray<string> typeArguments) =>
    genericType + "<" + string.Join(", ", typeArguments) + ">";

  public string GetGenericTypeParameter(object? genericContext, int index) => "!" + index;

  public string GetGenericMethodParameter(object? genericContext, int index) => "!!" + index;

  public string GetFunctionPointerType(MethodSignature<string> signature) => TypeNames.Method("*", signature);

  public string GetModifiedType(string modifier, string unmodifiedType, bool isRequired) =>
    $"{unmodifiedType} {(isRequired ? "modreq" : "modopt")}({modifier})";
}

static class Visibility {
  // ECMA-335 member access (FieldAttributes.FieldAccessMask / MethodAttributes.MemberAccessMask share the values).
  public static string Member(int access) => access switch {
    0 => "privatescope",
    1 => "private",
    2 => "private protected",
    3 => "internal",
    4 => "protected",
    5 => "protected internal",
    6 => "public",
    _ => throw new BadImageFormatException($"Unknown member access {access}"),
  };

  public static string Type(TypeAttributes attributes) => (attributes & TypeAttributes.VisibilityMask) switch {
    TypeAttributes.NotPublic => "internal",
    TypeAttributes.Public or TypeAttributes.NestedPublic => "public",
    TypeAttributes.NestedPrivate => "private",
    TypeAttributes.NestedFamily => "protected",
    TypeAttributes.NestedAssembly => "internal",
    TypeAttributes.NestedFamANDAssem => "private protected",
    TypeAttributes.NestedFamORAssem => "protected internal",
    var other => throw new BadImageFormatException($"Unknown type visibility {other}"),
  };

  // The innermost type in the nesting chain (starting at handle) that is not public, as "internal Ns.Type", or null.
  public static string? NonPublicChain(MetadataReader reader, TypeDefinitionHandle handle) {
    for (var current = handle; !current.IsNil; current = reader.GetTypeDefinition(current).GetDeclaringType()) {
      var access = Type(reader.GetTypeDefinition(current).Attributes);
      if (access != "public") return access + " " + TypeNames.Definition(reader, current);
    }
    return null;
  }

  // Access a type deriving from the declaring type is granted ("private protected" also needs the same assembly).
  public static bool IsProtected(string access) => access is "protected" or "protected internal";

  // Null when the reference is public all the way out; otherwise its own access, plus the enclosing type that
  // is not public when there is one ("public (in internal Ns.Outer)").
  public static string? Describe(string own, string? enclosing) =>
    own == "public" && enclosing == null ? null : enclosing == null ? own : $"{own} (in {enclosing})";
}
