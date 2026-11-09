#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // The one way Deep Frontier changes native game code with Harmony
  // (docs/native-safety-audit.md lists every patch and why no native
  // extension point covers it). Rules, enforced by
  // tools/validate_native_safety.mjs:
  // - Install runs at mod start (an IModStarter, once per process), never
  //   from a scene's Load, PostLoad, Awake or constructor, so no patch
  //   depends on singleton order or scene re-entry.
  // - verify runs first. It resolves every native member the patch targets,
  //   reads or replaces (signatures, private fields, IL facts) and throws if
  //   the game no longer matches 1.1.2.8. Nothing is patched then.
  // - An id is installed once per process; installing it again does nothing.
  // - A failure is rethrown naming Deep Frontier and the patch. ModCodeStarter
  //   does not catch it, so the game stops at the mod screen with that message
  //   instead of running with a patch that no longer fits.
  // No other code creates a Harmony instance (the validator allows only the
  // -deepFrontierMemoryTrace diagnostic, which patches nothing in normal play).
  public static class NativePatches {
    public const string GameVersion = "1.1.2.8";
    private const string IdPrefix = "DeepFrontier.";
    private static readonly HashSet<string> Installed = new();

    // Patch classes declared with [HarmonyPatch] attributes.
    public static void Install(string id, Action verify, params Type[] patchClasses) {
      if (patchClasses == null || patchClasses.Length == 0) throw new ArgumentException($"Deep Frontier patch {id}: no patch classes");
      Install(id, verify, harmony => {
        foreach (var patchClass in patchClasses) harmony.CreateClassProcessor(patchClass).Patch();
      });
    }

    // Patches applied with Harmony.Patch on targets verify resolved.
    public static void Install(string id, Action verify, Action<Harmony> apply) {
      if (id == null || !id.StartsWith(IdPrefix, StringComparison.Ordinal))
        throw new ArgumentException($"Deep Frontier patch ids start with {IdPrefix}: {id}");
      if (verify == null) throw new ArgumentNullException(nameof(verify), $"Deep Frontier patch {id} has no startup check");
      if (apply == null) throw new ArgumentNullException(nameof(apply));
      if (Installed.Contains(id)) return;
      try {
        verify();
      } catch (Exception exception) {
        throw Failure($"its patch {id}", "its check of the game failed", exception);
      }
      try {
        apply(new Harmony(id));
      } catch (Exception exception) {
        throw Failure($"its patch {id}", "Harmony could not apply it", exception);
      }
      Installed.Add(id);
    }

    internal static bool IsInstalled(string id) => Installed.Contains(id);

    // The exception a verify throws for a changed native member.
    public static InvalidOperationException Changed(string feature, string member) =>
      new InvalidOperationException($"{feature}: native API changed; expected {member} (Timberborn {GameVersion})");

    internal static InvalidOperationException Failure(string subject, string what, Exception inner) {
      var cause = inner is TypeInitializationException { InnerException: { } typeInit } ? typeInit : inner;
      return new InvalidOperationException(
        $"Deep Frontier {DeepFrontierRuntime.VerticalSliceVersion} cannot start: {subject} does not fit this game ({what}: {cause.Message}). " +
        $"This Deep Frontier build supports Timberborn {GameVersion}; the game reports {Application.version}. Disable Deep Frontier or install a version made for this game.",
        cause);
    }
  }

  // Member checks for the verify methods: each resolves exactly what a patch
  // or a reflected handle uses and throws NativePatches.Changed otherwise.
  public static class NativeMember {
    private const BindingFlags Declared = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly;

    public static MethodInfo Method(string feature, Type type, string name, Type returnType, params Type[] parameters) {
      var method = type.GetMethod(name, Declared, null, parameters, null);
      if (method == null || method.ReturnType != returnType)
        throw NativePatches.Changed(feature, $"{type.Name}.{name}({string.Join(", ", parameters.Select(p => p.Name))}) : {returnType.Name}");
      return method;
    }

    public static FieldInfo Field(string feature, Type type, string name, Type fieldType) {
      var field = type.GetField(name, Declared);
      if (field == null || field.FieldType != fieldType) throw NativePatches.Changed(feature, $"{type.Name}.{name} : {fieldType.Name}");
      return field;
    }

    // A type the game does not expose, from the assembly of a public anchor type.
    public static Type Type(string feature, Type anchor, string fullName) =>
      anchor.Assembly.GetType(fullName, throwOnError: false) ?? throw NativePatches.Changed(feature, $"type {fullName} in {anchor.Assembly.GetName().Name}");

    // Harmony binds patch arguments to native parameters by name.
    public static void Parameters(string feature, MethodBase method, params string[] names) {
      var actual = method.GetParameters().Select(p => p.Name).ToArray();
      if (!actual.SequenceEqual(names))
        throw NativePatches.Changed(feature, $"{method.DeclaringType?.Name}.{method.Name}({string.Join(", ", names)}), found ({string.Join(", ", actual)})");
    }

    // Mono inlines bodies of at most NativeIl.MonoInlineLimit IL bytes into
    // their callers, which then never reach the patch. Interface and virtual
    // calls are never inlined; use this for targets reached by direct calls.
    public static void NotInlined(string feature, MethodBase method) {
      if (NativeIl.Inlinable(method))
        throw NativePatches.Changed(feature, $"{method.DeclaringType?.Name}.{method.Name} larger than the Mono inline limit (IL {NativeIl.Size(method)} bytes)");
    }
  }
}
#endif
